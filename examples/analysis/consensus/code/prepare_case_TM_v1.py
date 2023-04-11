# Copyright (C) 2018-2019 Battelle Memorial Institute
# file: prepare_case_dsot_v1.py
""" Sets up a simple DSO+T use-case with one feeder

Public Functions:
    None
"""

import json
import os
import shutil

import numpy as np

import prep_microgrid_agent_v1 as prep
import tesp_support.commbldgenerator
import tesp_support.copperplateFeederGenerator_dsot
import tesp_support.consensus.feederGenerator_dsot
import tesp_support.consensus.glm_dict_TM as gd
import tesp_support.consensus.helpers_dsot as helpers
import tesp_support.consensus.case_merge as tesp


def prepare_case(mastercase):
    ######################################################
    # Simulation settings for the this case
    #    mastercase = "system_case_config"
    with open(mastercase + '.json', 'r', encoding='utf-8') as json_file:
        sys_config = json.load(json_file)

    port = str(sys_config['port'])
    caseName = sys_config['caseName']
    start_time = sys_config['StartTime']
    end_time = sys_config['EndTime']
    debug_mode = bool(True)
    fncs_flag = bool(False)
    helics_flag = bool(False)
    if 'FNCS' in sys_config:
        fncs_flag = bool(True)
        fncs_config = sys_config['FNCS']
    elif 'HELICS' in sys_config:
        helics_flag = bool(True)
        helics_config = sys_config['HELICS']
    # gen = sys_config['gen']
    # genFuel = sys_config['genfuel']
    data_Path = sys_config['dataPath']
    out_Path = sys_config['outputPath']

    # loading default agent data
    with open(os.path.join(data_Path, sys_config['dsoAgentFile']), 'r', encoding='utf-8') as json_file:
        def_config = json.load(json_file)

    sim = def_config['SimulationConfig']
    sim['caseType'] = sys_config['caseType']
    sim['agent_debug_mode'] = sys_config['agent_debug_mode']
    sim['metricsFullDetail'] = sys_config['metricsFullDetail']
    sim['port'] = sys_config['port']
    sim['solver'] = sys_config['solver']
    sim['CaseName'] = caseName
    sim['StartTime'] = start_time
    sim['EndTime'] = end_time
    sim['OutputPath'] = sys_config['caseName']  # currently only used for the experiment management scripts
    sim['SourceDirectory'] = '../../../../data'  # SourceDirectory is not used

    # loading building and DSO metadata
    with open(os.path.join(data_Path, sys_config['dsoPopulationFile']), 'r', encoding='utf-8') as json_file:
        dso_config = json.load(json_file)
    # loading residential metadata
    with open(os.path.join(data_Path, sys_config['dsoResBldgFile']), 'r', encoding='utf-8') as json_file:
        res_config = json.load(json_file)
    # loading commercial building metadata
    with open(os.path.join(data_Path, sys_config['dsoCommBldgFile']), 'r', encoding='utf-8') as json_file:
        comm_config = json.load(json_file)
    # loading battery metadata
    with open(os.path.join(data_Path, sys_config['dsoBattFile']), 'r', encoding='utf-8') as json_file:
        batt_config = json.load(json_file)

    sim.update({'dso': {}})
    sim.update({'weather': {}})
    [sim['dso'].update({key: dso_config[key]}) for key in dso_config.keys() if 'DSO' in key]

    substation_config = def_config['SimulationConfig']['dso']
    weather_config = def_config['SimulationConfig']['weather']
    case_config = def_config
    case_config['SimulationConfig']['simplifiedFeeders'] = sys_config['simplifiedFeeders']

    # loading hvac set point metadata
    # record aggregated hvac_setpoint_data from survey:
    # In this implementation individual house set point schedule may not
    # make sense but aggregated behavior will do.
    with open(os.path.join(data_Path, sys_config['hvacSetPoint']), 'r', encoding='utf-8') as json_file:
        hvac_setpt = json.load(json_file)

    # print(json.dumps(substation_config, sort_keys = True, indent = 2))
    # print(json.dumps(weather_config, sort_keys = True, indent = 2))
    # print(json.dumps(case_config, sort_keys = True, indent = 2))
    # print(json.dumps(res_config, sort_keys = True, indent = 2))
    # print(json.dumps(comm_config, sort_keys = True, indent = 2))
    # print(json.dumps(batt_config, sort_keys = True, indent = 2))
    # print(json.dumps(ev_model_config, sort_keys = True, indent = 2))
    # print(json.dumps(hvac_setpt, sort_keys = True, indent = 2))

    # We need to create the experiment folder. If it already exists we delete it and then create it
    if caseName != "" and caseName != ".." and caseName != ".":
        if os.path.isdir(caseName):
            print("experiment folder already exists, deleting and moving on...")
            shutil.rmtree(caseName)
        os.makedirs(caseName)
    else:
        print('Case name is blank or Case name is "." or ".." and could cause file deletion')
        exit(1)

    # We need to create the experiment out folder. If it already exists, we delete it and then create it
    if out_Path != "" and out_Path != ".." and out_Path != ".":
        if os.path.isdir(out_Path):
            print("experiment folder already exists, deleting and moving on...")
            shutil.rmtree(out_Path)
        os.makedirs(out_Path)
    else:
        out_Path = caseName

    # ======================= Laurentiu Marinovici - 12/13/2019 =======================
    # This is the part to initialize pieces for the copperplate feeder addition
    # Some things are added for testing purposes only
    need_copperplate_feeder = sim["CopperplateFeeder"]
    if need_copperplate_feeder:
        path_to_copperplate = os.path.abspath('../support/feeders/')
        copperplate_feeder_name = 'commercial_copperplate_feeder'
        # copperplate_feeder_name = 'commercial_populated_copperplate_feeder'
        copperplate_feeder_file = os.path.join(path_to_copperplate, copperplate_feeder_name + ".glm")
        print('Copperplate feeder taxonomy at {0:s}.\n'.format(copperplate_feeder_file))
    # ====================== end copperplate feeder initialization part ===============

    # First step is to create the dso folders and populate the feeders
    for dso_key, dso_val in substation_config.items():
        # print('dso ->', dso_key)
        # print('val ->', json.dumps(dso_val, sort_keys=True, indent=2))

        sub = dso_val['substation']
        bus = str(dso_val['bus_number'])
        os.makedirs(caseName + '/' + dso_key)

        for mg_key in dso_val['microgrids']:
            os.makedirs(caseName + '/' + mg_key)

        for gen_key in dso_val['generators']:
            os.makedirs(caseName + '/' + gen_key)

        # # seed the random number here instead of in feedergenerator_dsot_v1.py
        np.random.seed(dso_val['random_seed'])

        case_config['SimulationConfig']['OutputPath'] = caseName + '/' + dso_key
        case_config['SimulationConfig']['CaseName'] = dso_key
        case_config['SimulationConfig']['Substation'] = dso_val['substation']
        case_config['SimulationConfig']['BulkpowerBus'] = dso_val['bus_number']
        # case_config['BackboneFiles']['RandomSeed'] = dso_val['random_seed']
        case_config['SimulationConfig']['DSO'] = dso_key
        case_config['SimulationConfig']['DSO_type'] = dso_val['utility_type']

        for i in range(len(helics_config)):
            if bus == str(helics_config[i][0]):
                val = helics_config[i]

        case_config['MarketPrep']['DSO']['Bus'] = val[0]
        case_config['MarketPrep']['DSO']['Pnom'] = val[3]
        case_config['MarketPrep']['DSO']['Qnom'] = val[4]

        # This block now assigns scaling factors to each DSO
        case_config['MarketPrep']['DSO']['number_of_customers'] = dso_config[dso_key]['number_of_customers']
        case_config['MarketPrep']['DSO']['RCI customer count mix'] = dso_config[dso_key]['RCI customer count mix']
        case_config['MarketPrep']['DSO']['number_of_gld_homes'] = dso_config[dso_key]['number_of_gld_homes']
        # Weather is set per substation, with all feeders under the substation having the same weather profile
        # TODO: This needs to refer to the DSO weather data file name so there is a different weather file for each DSO.
        # substation_weather = dso_val['name'] # dso_val['weather']
        weather_agent_name = 'weather_' + dso_val['substation']
        case_config['WeatherPrep']['WeatherChoice'] = str.upper(
            os.path.splitext(dso_val['weather_file'])[1][1:])  # weather_config[substation_weather]['type']
        case_config['WeatherPrep']['Name'] = weather_agent_name
        # TODO: (Laurentiu Marinovici 11/07/2019) the path to where the weather data files are stored might change, so be careful with this hardcoded path
        case_config['WeatherPrep']['DataSourcePath'] = '../../../../data/weather/ERCOT_8_node_data/DAT formatted files/'
        case_config['WeatherPrep']['DataSource'] = dso_val[
            'weather_file']  # weather_config[substation_weather]['source']
        # TODO: (Laurentiu Marinovici 11/07/2019) check if the weather file name is going to stay as currently is incorporating
        # the location latitude and longitude; otherwise, a better way to provide these 2 measurements should be set
        case_config['WeatherPrep']['Latitude'] = dso_val[
            'latitude']  # dso_val['weather_file'].split('_')[3] # weather_config[substation_weather]['latitude']
        case_config['WeatherPrep']['Longitude'] = dso_val[
            'longitude']  # dso_val['weather_file'].split('_')[4] # weather_config[substation_weather]['longitude']
        case_config['WeatherPrep']['TimeZoneOffset'] = dso_val['time_zone_offset']

        weather_config.update({ \
            weather_agent_name: { \
                'type': case_config['WeatherPrep']['WeatherChoice'], \
                'source': case_config['WeatherPrep']['DataSource'], \
                'latitude': case_config['WeatherPrep']['Latitude'], \
                'longitude': case_config['WeatherPrep']['Longitude'], \
                'time_zone_offset': case_config['WeatherPrep']['TimeZoneOffset']}})

        # make weather agent folder
        try:
            os.makedirs(caseName + '/' + weather_agent_name)
        except:
            pass

        # (Laurentiu Marinovici 11/07/2019) but now, we are going to copy the .dat file from its location into the weather agent folder
        shutil.copy(
            os.path.join(os.path.abspath(case_config['WeatherPrep']['DataSourcePath']), dso_val['weather_file']),
            os.path.join(os.path.abspath(caseName), weather_agent_name, 'weather.dat'))

        # We need to generate the total population of commercial buildings by type and size
        num_res_customers = dso_val['number_of_gld_homes']
        # (Laurentiu Marinovici 11/18/2019) adding the residential metadata to case_config to be able to
        # eliminate the hardcoded path to the file in feederGenerator file
        case_config['BuildingPrep']['ResBldgMetaData'] = res_config
        case_config['BuildingPrep']['BattMetaData'] = batt_config

        num_comm_customers = round(num_res_customers * dso_val['RCI customer count mix']['commercial'] / \
                                   dso_val['RCI customer count mix']['residential'])
        num_comm_bldgs = num_comm_customers / dso_config['general']['comm_customers_per_bldg']
        comm_bldgs_pop = tesp_support.commbldgenerator.define_comm_bldg(comm_config, dso_val['utility_type'],
                                                                                  num_comm_bldgs)

        case_config['BuildingPrep']['ASHRAEZone'] = dso_val['ashrae_zone']
        case_config['BuildingPrep']['CommBldgMetaData'] = comm_config
        case_config['BuildingPrep']['CommBldgPopulation'] = comm_bldgs_pop

        # print(json.dumps(comm_bldgs_pop, sort_keys = True, indent = 2))
        print("\n!!!!! Initially, there are {0:d} commercial buildings !!!!!".format(
            len(case_config['BuildingPrep']['CommBldgPopulation'].keys())))

        # write out a configuration for each substation
        # WARNING!!!!! some fields in case_config are changed, yet not saved to the file,
        # in the subsequent part that processes each feeder;
        # the reason is the way the code was written for feeder generator
        # when only one feeder was expected
        with open(caseName + '/case_config_' + str(dso_val['bus_number']) + '.json', 'w') as outfile:
            json.dump(case_config, outfile, ensure_ascii=False, indent=2)
        feeders = dso_val['feeders']
        feedercnt = 1
        for feed_key, feed_val in feeders.items():
            print("\t<<<<< Chosen feeder -->> {0} >>>>>".format(feed_val['name']))
            if case_config['SimulationConfig']['simplifiedFeeders']:
                feed_val['name'] = 'sim_' + feed_val['name']
                print("\t<<<<< Going with the simplified feeders. >>>>>")
                print("\t<<<<< Feeder name changed to -->> {0} >>>>>".format(feed_val['name']))
            else:
                print("\t<<<<< Going with the full feeders. >>>>>")
            os.makedirs(caseName + '/' + feed_key)
            case_config['SimulationConfig']['OutputPath'] = caseName + '/' + feed_key
            case_config['SimulationConfig']['CaseName'] = feed_key
            case_config['BackboneFiles']['TaxonomyChoice'] = feed_val['name']
            tesp_support.consensus.feederGenerator_dsot.populate_feeder(fncs_flag, helics_flag, config=case_config)

            # Then we want to create a JSON dictionary with the Feeder information
            gd.glm_dict_with_microgrids(caseName + '/' + feed_key + '/' + feed_key, config=case_config,
                                        ercot=case_config['SimulationConfig']['simplifiedFeeders'])

            for microgrid_key in dso_val['microgrids']:
                shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_' + microgrid_key + '_glm_dict.json',
                            caseName + '/' + microgrid_key + '/' + feed_key + '_' + microgrid_key + '_glm_dict.json')

            shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                        caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

            # Next we create the agent dictionary along with the substation YAML file
            prep.prep_substation_with_microgrids(caseName + '/' + feed_key + '/' + feed_key,
                                                 caseName + '/' + dso_key + '/' + feed_key,
                                                 caseName + '/' + weather_agent_name + '/',
                                                 feedercnt,
                                                 dso_key,
                                                 config=case_config,
                                                 hvacSetpt=hvac_setpt)

            feedercnt += 1
            print("=== DONE WITH FEEDER {0:s} for {1:s}. ======\n".format(feed_key, dso_key))

        # =================== Laurentiu Marinovici 12/13/2019 - Copperplate feeder piece =======
        if need_copperplate_feeder:
            print("!!!!! There are {0:d} / {1:d} commercial buildings left !!!!!".format(
                len(case_config['BuildingPrep']['CommBldgPopulation'].keys()), len(comm_bldgs_pop)))
            if len(case_config['BuildingPrep']['CommBldgPopulation'].keys()) > 0:
                print("!!!!! We are going with the copperplate feeder now. !!!!!")
                feed_key = "copperplate_feeder"
                feed_val['name'] = feed_key
                substation_config[dso_key]['feeders'][feed_key] = feed_val
                os.makedirs(caseName + '/' + feed_key)
                case_config['SimulationConfig']['OutputPath'] = caseName + '/' + feed_key
                case_config['SimulationConfig']['CaseName'] = feed_key
                case_config['BackboneFiles']['TaxonomyChoice'] = copperplate_feeder_name
                case_config['BackboneFiles']['CopperplateFeederFile'] = copperplate_feeder_file
                tesp_support.consensus.copperplateFeederGenerator_dsot.populate_feeder(config=case_config)

                gd.glm_dict(caseName + '/' + feed_key + '/' + feed_key, config=case_config,
                            ercot=case_config['SimulationConfig']['simplifiedFeeders'])
                shutil.move(
                    caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                    caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

                # Next we create the agent dictionary along with the substation YAML file
                prep.prep_substation(caseName + '/' + feed_key + '/' + feed_key,
                                     caseName + '/' + dso_key + '/' + feed_key,
                                     caseName + '/' + weather_agent_name + '/',
                                     feedercnt,
                                     config=case_config,
                                     hvacSetpt=hvac_setpt)
                feedercnt += 1
                print("=== DONE WITH COPPERPLATE FEEDER {0:s} for {1:s}. ======\n".format(feed_key, dso_key))

        # ======================================================================================
        print("\n=== MERGING THE FEEDERS UNDER ONE SUBSTATION =====")
        os.makedirs(caseName + "/" + substation_config[dso_key]['substation'])
        tesp.merge_glm(os.path.abspath(
            caseName + '/' + substation_config[dso_key]['substation'] + '/' + substation_config[dso_key][
                'substation'] + '.glm'), list(substation_config[dso_key]['feeders'].keys()), 20)

        print("\n=== MERGING THE FNCS\HELICS CONFIGURATION FILES UNDER THE SUBSTATION FNCS CONFIGURATION =====")
        if helics_flag:
            tesp.merge_fncs_config(os.path.abspath(
                caseName + '/' + substation_config[dso_key]['substation'] + '/' + substation_config[dso_key][
                    'substation'] + '_HELICS_Config.json'), dso_key, list(substation_config[dso_key]['feeders'].keys()))
        elif fncs_flag:
            tesp.merge_fncs_config(os.path.abspath(
                caseName + '/' + substation_config[dso_key]['substation'] + '/' + substation_config[dso_key][
                    'substation'] + '_FNCS_Config.txt'), dso_key, list(substation_config[dso_key]['feeders'].keys()))

        print("\n=== MERGING THE FEEDERS GLM DICTIONARIES =====")
        tesp.merge_glm_dict(os.path.abspath(
            caseName + '/' + dso_key + '/' + substation_config[dso_key]['substation'] + '_glm_dict.json'),
                            list(substation_config[dso_key]['feeders'].keys()), 20)

        for microgrid_key in dso_val['microgrids']:

            print("\n=== MERGING THE FEEDERS GLM DICTIONARIES =====")
            tesp.merge_glm_dict(
                os.path.abspath(caseName + '/' + microgrid_key + '/' + microgrid_key + '_glm_dict.json'),
                list(key + '_' + microgrid_key for key in substation_config[dso_key]['feeders']), 20)

            print("\n=== MERGING THE MICROGRID AGENT DICTIONARIES =====")
            tesp.merge_agent_dict(
                os.path.abspath(caseName + '/' + microgrid_key + '/' + microgrid_key + '_agent_dict.json'),
                list(key + '_' + microgrid_key for key in substation_config[dso_key]['feeders']))

            print("\n=== MERGING THE MICROGRID YAML =====")
            if helics_flag:
                tesp.merge_substation_yaml(
                    os.path.abspath(caseName + '/' + microgrid_key + '/' + microgrid_key + '.json'),
                    list(key + '_' + microgrid_key for key in substation_config[dso_key]['feeders']))
            elif fncs_flag:
                tesp.merge_substation_yaml(
                    os.path.abspath(caseName + '/' + microgrid_key + '/' + microgrid_key + '.yaml'),
                    list(key + '_' + microgrid_key for key in substation_config[dso_key]['feeders']))

            # for dso_key, dso_val in substation_config.items():
            filesToDelete = [name for name in os.listdir(os.path.abspath(caseName + '/' + microgrid_key)) if
                             os.path.isfile(os.path.join(os.path.abspath(caseName + '/' + microgrid_key),
                                                         name)) and 'feeder' in name]
            print("=== Removing the following files: {0} for {1}. ===".format(filesToDelete, microgrid_key))
            [os.remove(os.path.join(os.path.abspath(caseName + '/' + microgrid_key), fileName)) for fileName in
             filesToDelete]

        for gen_key in dso_val['generators']:

            print("\n=== MERGING THE DG AGENT DICTIONARIES =====")
            tesp.merge_agent_dict(os.path.abspath(caseName + '/' + gen_key + '/' + gen_key + '_agent_dict.json'),
                                  list(key + '_' + gen_key for key in substation_config[dso_key]['feeders']))

            print("\n=== MERGING THE MICROGRID YAML =====")
            if helics_flag:
                tesp.merge_substation_yaml(os.path.abspath(caseName + '/' + gen_key + '/' + gen_key + '.json'),
                                           list(key + '_' + gen_key for key in substation_config[dso_key]['feeders']))
            elif fncs_flag:
                tesp.merge_substation_yaml(os.path.abspath(caseName + '/' + gen_key + '/' + gen_key + '.yaml'),
                                           list(key + '_' + gen_key for key in substation_config[dso_key]['feeders']))

            # for dso_key, dso_val in substation_config.items():
            filesToDelete = [name for name in os.listdir(os.path.abspath(caseName + '/' + gen_key)) if os.path.isfile(
                os.path.join(os.path.abspath(caseName + '/' + gen_key), name)) and 'feeder' in name]
            print("=== Removing the following files: {0} for {1}. ===".format(filesToDelete, gen_key))
            [os.remove(os.path.join(os.path.abspath(caseName + '/' + gen_key), fileName)) for fileName in filesToDelete]

        print("\n=== MERGING THE SUBSTATION AGENT DICTIONARIES =====")
        tesp.merge_agent_dict(os.path.abspath(
            caseName + '/' + dso_key + '/' + substation_config[dso_key]['substation'] + '_agent_dict.json'),
                              list(substation_config[dso_key]['feeders'].keys()))

        print("\n=== MERGING THE SUBSTATION YAML =====")
        if helics_flag:
            tesp.merge_substation_yaml(
                os.path.abspath(caseName + '/' + dso_key + '/' + substation_config[dso_key]['substation'] + '.json'),
                list(substation_config[dso_key]['feeders'].keys()))
        elif fncs_flag:
            tesp.merge_substation_yaml(
                os.path.abspath(caseName + '/' + dso_key + '/' + substation_config[dso_key]['substation'] + '.yaml'),
                list(substation_config[dso_key]['feeders'].keys()))

        # cleaning after feeders had been merged
        foldersToDelete = [name for name in os.listdir(os.path.abspath(caseName))
                           if os.path.isdir(os.path.join(os.path.abspath(caseName), name)) and 'feeder' in name]
        print("=== Removing the following folders: {0}. ===".format(foldersToDelete))
        [shutil.rmtree(os.path.join(os.path.abspath(caseName), folder)) for folder in foldersToDelete]

        # for dso_key, dso_val in substation_config.items():
        filesToDelete = [name for name in os.listdir(os.path.abspath(caseName + '/' + dso_key))
                         if os.path.isfile(os.path.join(os.path.abspath(caseName + '/' + dso_key), name)) and 'feeder' in name]
        print("=== Removing the following files: {0} for {1}. ===".format(filesToDelete, dso_key))
        [os.remove(os.path.join(os.path.abspath(caseName + '/' + dso_key), fileName)) for fileName in filesToDelete]

    # yp.close()

    # Also create the launch, kill and clean scripts for this case
    helpers.write_dsot_management_script_f_with_microgrids(master_file=mastercase,
                                                           case_path=caseName,
                                                           system_config=sys_config,
                                                           substation_config=substation_config,
                                                           weather_config=weather_config)

    # helpers.write_dsot_management_script_f(master_file=mastercase, case_path=caseName, system_config=sys_config,
    #                                            substation_config=substation_config, weather_config=weather_config)

    if debug_mode:
        for key in substation_config:
            folderPath = os.path.join(os.getcwd(), caseName, key)
            # shutil.copy(r'consensus.py', folderPath)
            shutil.copy(r'../../../../src/tesp_support/tesp_support/consensus/consensus_substation.py', folderPath)
            shutil.copy(r'../../../../src/tesp_support/tesp_support/consensus/DSO_Agent_Helics.py', folderPath)
            for microgrid_key in substation_config[key]['microgrids']:
                folderPath_mg = os.path.join(os.getcwd(), caseName, microgrid_key)
                shutil.copy(
                    r'../../../../src/tesp_support/tesp_support/consensus/Microgrid_Agent_Helics.py', folderPath_mg)
                shutil.copy(r'../../../../src/tesp_support/tesp_support/consensus/consensus_microgrid.py',
                            folderPath_mg)
            for dg_key in substation_config[key]['generators']:
                folderPath_dg = os.path.join(os.getcwd(), caseName, dg_key)
                shutil.copy(r'../../../../src/tesp_support/tesp_support/consensus/DG_Agent_Helics.py', folderPath_dg)
                shutil.copy(r'../../../../src/tesp_support/tesp_support/consensus/consensus_generator.py',
                            folderPath_dg)

        folderPath = os.path.join(os.getcwd(), caseName, weather_agent_name)
        shutil.copy(r'../../../../src/tesp_support/tesp_support/consensus/weatherAgent_Helics.py', folderPath)


if __name__ == "__main__":
    prepare_case("system_case_config_TM")
