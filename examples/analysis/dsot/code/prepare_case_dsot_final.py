# Copyright (C) 2018-2023 Battelle Memorial Institute
# file: prepare_case_dsot.py
""" Sets up a simple DSO+T use-case with one feeder

Public Functions:
    None
"""

import os
import sys
import json
import shutil
import datetime
import numpy as np
import math

import ingest_bld_data
from tesp_support.api.helpers import HelicsMsg
if os.path.abspath("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/original") not in sys.path:
    sys.path.append("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/original")
import commercial_feeder_glm_dod as com_FG_dod
import tesp_support.original.commercial_feeder_glm as com_FG
import tesp_support.original.copperplate_feeder_glm as cp_FG
import tesp_support.dsot.case_merge as cm
import tesp_support.dsot.glm_dictionary as gd
if os.path.abspath("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/dsot") not in sys.path:
    sys.path.append("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/dsot")
import helpers_dsot_dod as helpers
import residential_feeder_glm_dod as res_FG_dod
import tesp_support.dsot.residential_feeder_glm as res_FG
import prep_substation_dsot as prep
if os.path.abspath("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/weather") not in sys.path:
    sys.path.append("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/weather")
import PSMv3toDAT, EPWtoDAT


# Simulation settings for the experimental case
def prepare_case(node, mastercase, pv=None, bt=None, fl=None, ev=None):

    # We need to load in the master metadata (*system_case_config.json)
    with open(mastercase + '.json', 'r', encoding='utf-8') as json_file:
        sys_config = json.load(json_file)

    # Get path for other data
    data_Path = sys_config['dataPath']
    case_type = sys_config['caseType']
    sys_config['market'] = False
    if pv is not None:
        case_type['pv'] = pv
        if pv > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_pv"
    if bt is not None:
        case_type['bt'] = bt
        if bt > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_bt"
            sys_config['market'] = True
    if fl is not None:
        case_type["fl"] = fl
        if fl > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_fl"
            sys_config['market'] = True
    if ev is not None:
        case_type["ev"] = ev
        if ev > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_ev"
            sys_config['market'] = True

    # loading default agent data
    with open(os.path.join(data_Path, sys_config['dsoAgentFile']), 'r', encoding='utf-8') as json_file:
        case_config = json.load(json_file)
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
    # loading ev model metadata
    with open(os.path.join(data_Path, sys_config['dsoEvModelFile']), 'r', encoding='utf-8') as json_file:
        ev_model_config = json.load(json_file)
    # loading hvac set point metadata
    # record aggregated hvac_setpoint_data from survey:
    # In this implementation individual house set point schedule may not
    # make sense but aggregated behavior will do.
    with open(os.path.join(data_Path, sys_config['hvacSetPoint']), 'r', encoding='utf-8') as json_file:
        hvac_setpt = json.load(json_file)

    # print(json.dumps(sys_config, sort_keys = True, indent = 2))
    # print(json.dumps(dso_config, sort_keys = True, indent = 2))
    # print(json.dumps(case_config, sort_keys = True, indent = 2))
    # print(json.dumps(res_config, sort_keys = True, indent = 2))
    # print(json.dumps(comm_config, sort_keys = True, indent = 2))
    # print(json.dumps(batt_config, sort_keys = True, indent = 2))
    # print(json.dumps(ev_model_config, sort_keys = True, indent = 2))
    # print(json.dumps(hvac_setpt, sort_keys = True, indent = 2))

    caseName = sys_config['caseName']
    start_time = sys_config['StartTime']
    end_time = sys_config['EndTime']

    # setting Tmax in seconds
    ep = datetime.datetime(1970, 1, 1)
    s = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    e = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    sIdx = (s - ep).total_seconds()
    eIdx = (e - ep).total_seconds()
    sys_config['Tmax'] = int((eIdx - sIdx))

    dt = sys_config['dt']
    gen = sys_config['gen']
    genFuel = sys_config['genfuel']
    tso_config = sys_config['DSO']
    out_Path = sys_config['outputPath']

    sim = case_config['SimulationConfig']
    bldPrep = case_config['BuildingPrep']
    mktPrep = case_config['MarketPrep']
    weaPrep = case_config['WeatherPrep']
    weather_config = {}

    sim['CaseName'] = caseName
    sim['TimeZone'] = sys_config['TimeZone']
    sim['StartTime'] = start_time
    sim['EndTime'] = end_time
    sim['port'] = sys_config['port']
    sim['numCore'] = sys_config['numCore']
    sim['keyLoad'] = sys_config['keyLoad']
    # sim['players'] = sys_config['players']
    sim['caseType'] = sys_config['caseType']
    if 'Q_bid_forecast_correction' in list(sys_config.keys()):
        sim['Q_bid_forecast_correction'] = sys_config['Q_bid_forecast_correction']
    else:
        sim['Q_bid_forecast_correction'] = {"default": {"correct": False}}
    sim['agent_debug_mode'] = sys_config['agent_debug_mode']
    sim['metricsFullDetail'] = sys_config['metricsFullDetail']
    sim['simplifiedFeeders'] = sys_config['simplifiedFeeders']
    sim['OutputPath'] = sys_config['caseName']  # currently only used for the experiment management scripts
    sim['priceSensLoad'] = sys_config['priceSensLoad']
    sim['quadratic'] = sys_config['quadratic']
    sim['quadraticFile'] = sys_config['dsoQuadraticFile']

    # =================== fernando 2021/06/25 - removing 10 AM bid correction to AMES =======
    if case_type['fl'] == 1:
        print('Correction of DSO bid for 10 AM AMES bid is performed')
    else:
        sim['Q_bid_forecast_correction'] = {'default': sim['Q_bid_forecast_correction']['default']}
        print('NO 10 AM AMES bid correction')

    # We need to create the experiment folder. If it already exists, we delete it and then create it
    if caseName != "" and caseName != ".." and caseName != ".":
        if os.path.isdir(caseName):
            print("experiment folder already exists, deleting and moving on...")
            shutil.rmtree(caseName)
        os.makedirs(caseName)
        # copy system case config for this case
        with open(os.path.join(caseName, 'generate_case_config.json'), 'w', encoding='utf-8') as json_file:
            json.dump(sys_config, json_file, indent=2)
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

    # write player helics config json file for load and generator players
    helpers.write_players_msg(caseName, sys_config, dt)

    tso = HelicsMsg("pypower", dt)
    # config helics subs/pubs
    # Running renewables wind, solar
    if sys_config['genPower']:
        for i in range(len(gen)):
            if genFuel[i][0] in sys_config['renewables']:
                idx = str(genFuel[i][2])
                for plyr in ["genMn", "genForecastHr"]:
                    player = sys_config[plyr]
                    if player[6] and not player[8]:
                        tso.subs_n(player[0] + "player/" + player[0] + "_power_" + idx, "string")
                    if player[7] and not player[8]:
                        tso.subs_n(player[0] + "player/" + player[0] + "_pwr_hist_" + idx, "string")

    # First step is to create the dso folders and populate the feeders
    for dso_key, dso_val in dso_config.items():
        # print('dso ->', dso_key)
        # print('val ->', json.dumps(dso_val, sort_keys=True, indent=2))

        if 'DSO' not in dso_key:
            continue

        sub_key = dso_val['substation']
        bus = str(dso_val['bus_number'])

        # write the tso published connections for this substation
        tso.pubs_n(False, "cleared_q_rt_" + bus, "string")
        tso.pubs_n(False, "cleared_q_da_" + bus, "string")
        tso.pubs_n(False, "lmp_rt_" + bus, "string")
        tso.pubs_n(False, "lmp_da_" + bus, "string")
        tso.pubs_n(False, "three_phase_voltage_" + bus, "string")

        # write the tso subscribe connections for this substation
        tso.subs_n("dso" + sub_key + "/rt_bid_" + bus, "string")
        tso.subs_n("dso" + sub_key + "/da_bid_" + bus, "string")

        try:
            # running reference load, using a player for the load reference for comparison
            player = sys_config['refLoadMn']
            if player[6] and player[8]:
                tso.subs_n(player[0] + "player/" + player[0] + "_load_" + bus, "string")
            if player[7] and player[8]:
                tso.subs_n(player[0] + "player/" + player[0] + "_ld_hist_" + bus, "string")
            if not dso_val['used']:
                # running reference load res and ind, (no gridlabd instance, using a player for the load)
                player = sys_config['gldLoad']
                if player[6] and player[8]:
                    tso.subs_n(player[0] + "player/" + player[0] + "_load_" + bus, "string")
                if player[7] and player[8]:
                    tso.subs_n(player[0] + "player/" + player[0] + "_ld_hist_" + bus, "string")
                continue
        except:
            pass

        os.makedirs(caseName + '/' + dso_key)

        # seed the random number here instead of in feedergenerator_dsot.py
        np.random.seed(dso_val['random_seed'])

        # copy dso default config
        sim['DSO'] = dso_key
        sim[dso_key] = dso_val
        sim['CaseName'] = dso_key
        sim['Substation'] = sub_key
        sim['OutputPath'] = caseName + '/' + dso_key
        sim['BulkpowerBus'] = dso_val['bus_number']
        # case_config['BackboneFiles']['RandomSeed'] = dso_val['random_seed']
        sim['DSO_type'] = dso_val['utility_type']
        sim['rooftop_pv_rating_MW'] = dso_val['rooftop_pv_rating_MW']
        sim['scaling_factor'] = dso_val['scaling_factor']
        sim['serverPort'] = 5150 + (int(bus) // 20)

        bldPrep['SolarDataPath'] = sys_config['solarDataPath']
        prefix = ''
        if node == 8:
            prefix = '8-node '
        bldPrep['SolarPPlayerFile'] = prefix + dso_key+'/'+dso_key+'_'+sys_config['solarPPlayerFile']
        bldPrep['SolarQPlayerFile'] = prefix + dso_key+'/'+dso_key+'_'+sys_config['solarQPlayerFile']
        # (Laurentiu Marinovici 11/18/2019) adding the residential metadata to case_config to be able to
        # eliminate the hardcoded path to the file in feederGenerator file
        bldPrep['MetaDataPath'] = "../data/"
        bldPrep['CommBldgMetaData'] = comm_config
        bldPrep['ResBldgMetaData'] = res_config
        bldPrep['BattMetaData'] = batt_config
        bldPrep['EvModelMetaData'] = ev_model_config
        bldPrep['EvDrivingDataFile'] = sys_config['dsoEvDrivingFile']
        bldPrep['ASHRAEZone'] = dso_val['ashrae_zone']

        # Following block is for AMES:
        PQ_val = [0, 0, 0, 0]
        for i in range(len(tso_config)):
            if bus == str(tso_config[i][0]):
                PQ_val = tso_config[i]
        mktPrep['DSO']['Bus'] = PQ_val[0]
        mktPrep['DSO']['Pnom'] = PQ_val[3]
        mktPrep['DSO']['Qnom'] = PQ_val[4]
        # This block now assigns scaling factors to each DSO
        mktPrep['DSO']['number_of_customers'] = dso_config[dso_key]['number_of_customers']
        mktPrep['DSO']['RCI customer count mix'] = dso_config[dso_key]['RCI customer count mix']
        mktPrep['DSO']['number_of_gld_homes'] = dso_config[dso_key]['number_of_gld_homes']

        # Weather is set per substation, with all feeders under the substation having the same weather profile
        # The values below need to refer to the DSO weather profile
        # The weather profile choice/name/path/source/coordinates should match
        # Coordinates (lat/long/) for solar gain calcs and such
        # NOTE: This can be misused
        weather_agent_name = 'weather_' + sub_key
        weaPrep['WeatherChoice'] = str.upper(os.path.splitext(dso_val['weather_file'])[1][1:])
        weaPrep['Name'] = weather_agent_name
        weaPrep['DataSource'] = dso_val['weather_file']
        weaPrep['Latitude'] = dso_val['latitude']
        weaPrep['Longitude'] = dso_val['longitude']
        weaPrep['TimeZoneOffset'] = dso_val['time_zone_offset']

        # could eliminate code here by changing helpers_dsot.py, since only one weather for DSO
        weather_config[weather_agent_name] = {
                'type': weaPrep['WeatherChoice'],
                'source': weaPrep['DataSource'],
                'latitude': weaPrep['Latitude'],
                'longitude': weaPrep['Longitude'],
                'time_zone_offset': weaPrep['TimeZoneOffset']}

        # make weather agent folder
        try:
            os.makedirs(caseName + '/' + weather_agent_name)
        except:
            pass

        # (Laurentiu Marinovici 11/07/2019)
        # we are going to copy the .dat file from its location into the weather agent folder
        shutil.copy(os.path.join(os.path.abspath(sys_config['WeatherDataSourcePath']), dso_val['weather_file']),
                    os.path.join(os.path.abspath(caseName), weather_agent_name, 'weather.dat'))

        # We need to generate the total population of commercial buildings by type and size
        num_res_customers = dso_val['number_of_gld_homes']
        num_comm_customers = round(num_res_customers * dso_val['RCI customer count mix']['commercial'] /
                                   dso_val['RCI customer count mix']['residential'])
        num_comm_bldgs = num_comm_customers / dso_val['comm_customers_per_bldg']
        comm_bldgs_pop = com_FG.define_comm_bldg(comm_config, dso_val['utility_type'], num_comm_bldgs)
        bldPrep['CommBldgPopulation'] = comm_bldgs_pop

        # print(json.dumps(comm_bldgs_pop, sort_keys = True, indent = 2))
        print("\n!!!!! Initially, there are {0:d} commercial buildings !!!!!".format(
            len(bldPrep['CommBldgPopulation'].keys())))

        # write out a configuration for each substation
        # WARNING!!!!! some fields in case_config are changed, yet not saved to the file,
        # in the subsequent part that processes each feeder;
        # the reason is the way the code was written for feeder generator
        # when only one feeder was expected
        with open(caseName + '/case_config_' + str(dso_val['bus_number']) + '.json', 'w') as outfile:
            json.dump(case_config, outfile, ensure_ascii=False, indent=2)

        HelicsMsg.gld = HelicsMsg("gld" + case_config['SimulationConfig']['Substation'], 30)
        HelicsMsg.dso = HelicsMsg("dso" + case_config['SimulationConfig']['Substation'], dt)
        HelicsMsg.dso.config("uninterruptible", True)
        feeders = dso_val['feeders']
        feedercnt = 1
        for feed_key, feed_val in feeders.items():
            print("\t<<<<< Chosen feeder -->> {0} >>>>>".format(feed_val['name']))
            if sim['simplifiedFeeders']:
                feed_val['name'] = 'sim_' + feed_val['name']
                print("\t<<<<< Going with the simplified feeders. >>>>>")
                print("\t<<<<< Feeder name changed to -->> {0} >>>>>".format(feed_val['name']))
            else:
                print("\t<<<<< Going with the full feeders. >>>>>")
            os.makedirs(caseName + '/' + feed_key)
            sim['OutputPath'] = caseName + '/' + feed_key
            sim['CaseName'] = feed_key
            case_config['BackboneFiles']['TaxonomyChoice'] = feed_val['name']
            res_FG.populate_feeder(config=case_config)

            # Then we want to create a JSON dictionary with the Feeder information
            gd.glm_dict(caseName + '/' + feed_key + '/' + feed_key, config=case_config,
                        ercot=sim['simplifiedFeeders'])
            shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                        caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

            # Next we create the agent dictionary along with the substation YAML file
            prep.prep_substation(caseName + '/' + feed_key + '/' + feed_key,
                                 caseName + '/' + dso_key + '/' + feed_key,
                                 caseName + '/' + weather_agent_name + '/',
                                 feedercnt,
                                 config=case_config,
                                 hvacSetpt=hvac_setpt,
                                 Q_forecast=sim['Q_bid_forecast_correction'],
                                 Q_dso_key=dso_key)
            feedercnt += 1
            print("=== DONE WITH FEEDER {0:s} for {1:s}. ======\n".format(feed_key, dso_key))

        # =================== Laurentiu Marinovici 12/13/2019 - Copperplate feeder piece =======
        if sim["CopperplateFeeder"]:
            print("!!!!! There are {0:d} / {1:d} commercial buildings left !!!!!".format(
                len(bldPrep['CommBldgPopulation'].keys()), len(comm_bldgs_pop)))
            if len(bldPrep['CommBldgPopulation'].keys()) > 0:
                print("!!!!! We are going with the copperplate feeder now. !!!!!")
                feed_key = "copperplate_feeder"
                feed_val['name'] = feed_key
                dso_val['feeders'][feed_key] = feed_val
                os.makedirs(caseName + '/' + feed_key)
                sim['OutputPath'] = caseName + '/' + feed_key
                sim['CaseName'] = feed_key
                case_config['BackboneFiles']['TaxonomyChoice'] = sim['CopperplateFeederName']
                case_config['BackboneFiles']['CopperplateFeederFile'] = sim['CopperplateFeederFile']
                cp_FG.populate_feeder(config=case_config)

                gd.glm_dict(caseName + '/' + feed_key + '/' + feed_key, config=case_config,
                            ercot=sim['simplifiedFeeders'])
                shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                            caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

                # Next we create the agent dictionary along with the substation YAML file
                prep.prep_substation(caseName + '/' + feed_key + '/' + feed_key,
                                     caseName + '/' + dso_key + '/' + feed_key,
                                     caseName + '/' + weather_agent_name + '/',
                                     feedercnt,
                                     config=case_config,
                                     hvacSetpt=hvac_setpt,
                                     Q_forecast=sim['Q_bid_forecast_correction'],
                                     Q_dso_key=dso_key)
                feedercnt += 1
                print("=== DONE WITH COPPERPLATE FEEDER {0:s} for {1:s}. ======\n".format(feed_key, dso_key))

        # ======================================================================================
        print("\n=== MERGING THE FEEDERS UNDER ONE SUBSTATION =====")
        os.makedirs(caseName + "/" + sub_key)
        cm.merge_glm(os.path.abspath(caseName + '/' + sub_key + '/' + sub_key + '.glm'), list(dso_val['feeders'].keys()), 20)

        print("\n=== MERGING/WRITING THE SUBSTATION(GRIDLABD) MESSAGE FILE =====")
        HelicsMsg.gld.write_file(os.path.abspath(caseName + '/' + sub_key + '/' + sub_key + '.json'))

        print("\n=== MERGING/WRITING THE FEEDERS GLM DICTIONARIES =====")
        cm.merge_glm_dict(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_glm_dict.json'), list(dso_val['feeders'].keys()), 20)

        print("\n=== MERGING/WRITING THE SUBSTATION AGENT DICTIONARIES =====")
        cm.merge_agent_dict(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_agent_dict.json'), list(dso_val['feeders'].keys()))

        print("\n=== MERGING/WRITING THE DSO MESSAGE FILE =====")
        HelicsMsg.dso.write_file(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '.json'))

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

    tso.write_file(caseName + '/tso_h.json')

    # Also create the launch, kill and clean scripts for this case
    helpers.write_dsot_management_script(master_file="generate_case_config",
                                         case_path=caseName,
                                         system_config=sys_config,
                                         substation_config=dso_config,
                                         weather_config=weather_config)


def prepare_case_dod(node, mastercase, current_player_filenames, current_bldg_count_for_each_player, bldgs_per_feeder, current_weather_folder_name, each_grid_name, list_bldgs_assigned, climate_zone_count, pv=None, bt=None, fl=None, ev=None,unique_port_for_simulation=None):

    # We need to load in the master metadata (*system_case_config.json)
    with open(mastercase + '.json', 'r', encoding='utf-8') as json_file:
        sys_config = json.load(json_file)

    # Get path for other data
    data_Path = sys_config['dataPath']
    case_type = sys_config['caseType']
    sys_config['market'] = False
    if pv is not None:
        case_type['pv'] = pv
        if pv > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_pv"
    if bt is not None:
        case_type['bt'] = bt
        if bt > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_bt"
            sys_config['market'] = True
    if fl is not None:
        case_type["fl"] = fl
        if fl > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_fl"
            sys_config['market'] = True
    if ev is not None:
        case_type["ev"] = ev
        if ev > 0:
            sys_config['caseName'] = sys_config['caseName'] + "_ev"
            sys_config['market'] = True

    # loading default agent data
    with open(os.path.join(data_Path, sys_config['dsoAgentFile']), 'r', encoding='utf-8') as json_file:
        case_config = json.load(json_file)
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
    # loading ev model metadata
    with open(os.path.join(data_Path, sys_config['dsoEvModelFile']), 'r', encoding='utf-8') as json_file:
        ev_model_config = json.load(json_file)
    # loading hvac set point metadata
    # record aggregated hvac_setpoint_data from survey:
    # In this implementation individual house set point schedule may not
    # make sense but aggregated behavior will do.
    with open(os.path.join(data_Path, sys_config['hvacSetPoint']), 'r', encoding='utf-8') as json_file:
        hvac_setpt = json.load(json_file)

    # print(json.dumps(sys_config, sort_keys = True, indent = 2))
    # print(json.dumps(dso_config, sort_keys = True, indent = 2))
    # print(json.dumps(case_config, sort_keys = True, indent = 2))
    # print(json.dumps(res_config, sort_keys = True, indent = 2))
    # print(json.dumps(comm_config, sort_keys = True, indent = 2))
    # print(json.dumps(batt_config, sort_keys = True, indent = 2))
    # print(json.dumps(ev_model_config, sort_keys = True, indent = 2))
    # print(json.dumps(hvac_setpt, sort_keys = True, indent = 2))

    caseName = sys_config['caseName']
    start_time = sys_config['StartTime']
    end_time = sys_config['EndTime']

    # setting Tmax in seconds
    ep = datetime.datetime(1970, 1, 1)
    s = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    e = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    sIdx = (s - ep).total_seconds()
    eIdx = (e - ep).total_seconds()
    sys_config['Tmax'] = int((eIdx - sIdx))

    dt = sys_config['dt']
    gen = sys_config['gen']
    genFuel = sys_config['genfuel']
    tso_config = sys_config['DSO']
    out_Path = sys_config['outputPath']

    sim = case_config['SimulationConfig']
    bldPrep = case_config['BuildingPrep']
    mktPrep = case_config['MarketPrep']
    weaPrep = case_config['WeatherPrep']
    weather_config = {}

    sim['CaseName'] = caseName
    sim['TimeZone'] = sys_config['TimeZone']
    sim['StartTime'] = start_time
    sim['EndTime'] = end_time
    sim['port'] = sys_config['port']
    sim['numCore'] = sys_config['numCore']
    sim['keyLoad'] = sys_config['keyLoad']
    # sim['players'] = sys_config['players']
    sim['caseType'] = sys_config['caseType']
    if 'Q_bid_forecast_correction' in list(sys_config.keys()):
        sim['Q_bid_forecast_correction'] = sys_config['Q_bid_forecast_correction']
    else:
        sim['Q_bid_forecast_correction'] = {"default": {"correct": False}}
    sim['agent_debug_mode'] = sys_config['agent_debug_mode']
    sim['metricsFullDetail'] = sys_config['metricsFullDetail']
    sim['simplifiedFeeders'] = sys_config['simplifiedFeeders']
    sim['OutputPath'] = sys_config['caseName']  # currently only used for the experiment management scripts
    sim['priceSensLoad'] = sys_config['priceSensLoad']
    sim['quadratic'] = sys_config['quadratic']
    sim['quadraticFile'] = sys_config['dsoQuadraticFile']

    # =================== fernando 2021/06/25 - removing 10 AM bid correction to AMES =======
    if case_type['fl'] == 1:
        print('Correction of DSO bid for 10 AM AMES bid is performed')
    else:
        sim['Q_bid_forecast_correction'] = {'default': sim['Q_bid_forecast_correction']['default']}
        print('NO 10 AM AMES bid correction')

    # We need to create the experiment folder. If it already exists, we delete it and then create it
    if caseName != "" and caseName != ".." and caseName != ".":
        if os.path.isdir(caseName):
            print("experiment folder already exists, deleting and moving on...")
            shutil.rmtree(caseName)
        os.makedirs(caseName)
        # copy system case config for this case
        with open(os.path.join(caseName, 'generate_case_config.json'), 'w', encoding='utf-8') as json_file:
            json.dump(sys_config, json_file, indent=2)
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

    # write player helics config json file for load and generator players
    helpers.write_players_msg(caseName, sys_config, dt)

    tso = HelicsMsg("pypower", dt)
    # config helics subs/pubs
    # Running renewables wind, solar
    if sys_config['genPower']:
        for i in range(len(gen)):
            if genFuel[i][0] in sys_config['renewables']:
                idx = str(genFuel[i][2])
                for plyr in ["genMn", "genForecastHr"]:
                    player = sys_config[plyr]
                    if player[6] and not player[8]:
                        tso.subs_n(player[0] + "player/" + player[0] + "_power_" + idx, "string")
                    if player[7] and not player[8]:
                        tso.subs_n(player[0] + "player/" + player[0] + "_pwr_hist_" + idx, "string")

    # First step is to create the dso folders and populate the feeders
    for dso_key, dso_val in dso_config.items():
        # print('dso ->', dso_key)
        # print('val ->', json.dumps(dso_val, sort_keys=True, indent=2))

        if 'DSO' not in dso_key:
            continue

        sub_key = dso_val['substation']
        bus = str(dso_val['bus_number'])

        # write the tso published connections for this substation
        tso.pubs_n(False, "cleared_q_rt_" + bus, "string")
        tso.pubs_n(False, "cleared_q_da_" + bus, "string")
        tso.pubs_n(False, "lmp_rt_" + bus, "string")
        tso.pubs_n(False, "lmp_da_" + bus, "string")
        tso.pubs_n(False, "three_phase_voltage_" + bus, "string")

        # write the tso subscribe connections for this substation
        tso.subs_n("dso" + sub_key + "/rt_bid_" + bus, "string")
        tso.subs_n("dso" + sub_key + "/da_bid_" + bus, "string")

        try:
            # running reference load, using a player for the load reference for comparison
            player = sys_config['refLoadMn']
            if player[6] and player[8]:
                tso.subs_n(player[0] + "player/" + player[0] + "_load_" + bus, "string")
            if player[7] and player[8]:
                tso.subs_n(player[0] + "player/" + player[0] + "_ld_hist_" + bus, "string")
            if not dso_val['used']:
                # running reference load res and ind, (no gridlabd instance, using a player for the load)
                player = sys_config['gldLoad']
                if player[6] and player[8]:
                    tso.subs_n(player[0] + "player/" + player[0] + "_load_" + bus, "string")
                if player[7] and player[8]:
                    tso.subs_n(player[0] + "player/" + player[0] + "_ld_hist_" + bus, "string")
                continue
        except:
            pass

        os.makedirs(caseName + '/' + dso_key)

        # seed the random number here instead of in feedergenerator_dsot.py
        np.random.seed(dso_val['random_seed'])

        # copy dso default config
        sim['DSO'] = dso_key
        sim[dso_key] = dso_val
        sim['CaseName'] = dso_key
        sim['Substation'] = sub_key
        sim['OutputPath'] = caseName + '/' + dso_key
        sim['BulkpowerBus'] = dso_val['bus_number']
        # case_config['BackboneFiles']['RandomSeed'] = dso_val['random_seed']
        sim['DSO_type'] = dso_val['utility_type']
        sim['rooftop_pv_rating_MW'] = dso_val['rooftop_pv_rating_MW']
        sim['scaling_factor'] = dso_val['scaling_factor']
        sim['serverPort'] = 5150 + (int(bus) // 20)

        bldPrep['SolarDataPath'] = sys_config['solarDataPath']
        prefix = ''
        if node == 8:
            prefix = '8-node '
        bldPrep['SolarPPlayerFile'] = prefix + dso_key+'/'+dso_key+'_'+sys_config['solarPPlayerFile']
        bldPrep['SolarQPlayerFile'] = prefix + dso_key+'/'+dso_key+'_'+sys_config['solarQPlayerFile']
        # (Laurentiu Marinovici 11/18/2019) adding the residential metadata to case_config to be able to
        # eliminate the hardcoded path to the file in feederGenerator file
        bldPrep['MetaDataPath'] = "../data/"
        bldPrep['CommBldgMetaData'] = comm_config
        bldPrep['ResBldgMetaData'] = res_config
        bldPrep['BattMetaData'] = batt_config
        bldPrep['EvModelMetaData'] = ev_model_config
        bldPrep['EvDrivingDataFile'] = sys_config['dsoEvDrivingFile']
        bldPrep['ASHRAEZone'] = dso_val['ashrae_zone']

        # Following block is for AMES:
        PQ_val = [0, 0, 0, 0]
        for i in range(len(tso_config)):
            if bus == str(tso_config[i][0]):
                PQ_val = tso_config[i]
        mktPrep['DSO']['Bus'] = PQ_val[0]
        mktPrep['DSO']['Pnom'] = PQ_val[3]
        mktPrep['DSO']['Qnom'] = PQ_val[4]
        # This block now assigns scaling factors to each DSO
        mktPrep['DSO']['number_of_customers'] = dso_config[dso_key]['number_of_customers']
        mktPrep['DSO']['RCI customer count mix'] = dso_config[dso_key]['RCI customer count mix']
        mktPrep['DSO']['number_of_gld_homes'] = dso_config[dso_key]['number_of_gld_homes']

        # Weather is set per substation, with all feeders under the substation having the same weather profile
        # The values below need to refer to the DSO weather profile
        # The weather profile choice/name/path/source/coordinates should match
        # Coordinates (lat/long/) for solar gain calcs and such
        # NOTE: This can be misused
        weather_agent_name = 'weather_' + sub_key
        weaPrep['WeatherChoice'] = str.upper(os.path.splitext(dso_val['weather_file'])[1][1:])
        weaPrep['Name'] = weather_agent_name
        weaPrep['DataSource'] = dso_val['weather_file']
        weaPrep['Latitude'] = dso_val['latitude']
        weaPrep['Longitude'] = dso_val['longitude']
        weaPrep['TimeZoneOffset'] = dso_val['time_zone_offset']

        # could eliminate code here by changing helpers_dsot.py, since only one weather for DSO
        weather_config[weather_agent_name] = {
                'type': weaPrep['WeatherChoice'],
                'source': weaPrep['DataSource'],
                'latitude': weaPrep['Latitude'],
                'longitude': weaPrep['Longitude'],
                'time_zone_offset': weaPrep['TimeZoneOffset']}

        # make weather agent folder
        try:
            os.makedirs(caseName + '/' + weather_agent_name)
        except:
            pass

        # (Laurentiu Marinovici 11/07/2019)
        # we are going to copy the .dat file from its location into the weather agent folder
        shutil.copy(os.path.join(os.path.abspath(sys_config['WeatherDataSourcePath']), dso_val['weather_file']),
                    os.path.join(os.path.abspath(caseName), weather_agent_name, 'weather.dat'))

        # We need to generate the total population of commercial buildings by type and size
        num_res_customers = dso_val['number_of_gld_homes']
        num_comm_customers = round(num_res_customers * dso_val['RCI customer count mix']['commercial'] /
                                   dso_val['RCI customer count mix']['residential'])
        num_comm_bldgs = num_comm_customers / dso_val['comm_customers_per_bldg']
        comm_bldgs_pop = com_FG_dod.define_comm_bldg(comm_config, dso_val['utility_type'], num_comm_bldgs)
        bldPrep['CommBldgPopulation'] = comm_bldgs_pop

        # print(json.dumps(comm_bldgs_pop, sort_keys = True, indent = 2))
        print("\n!!!!! Initially, there are {0:d} commercial buildings !!!!!".format(
            len(bldPrep['CommBldgPopulation'].keys())))

        # write out a configuration for each substation
        # WARNING!!!!! some fields in case_config are changed, yet not saved to the file,
        # in the subsequent part that processes each feeder;
        # the reason is the way the code was written for feeder generator
        # when only one feeder was expected
        with open(caseName + '/case_config_' + str(dso_val['bus_number']) + '.json', 'w') as outfile:
            json.dump(case_config, outfile, ensure_ascii=False, indent=2)

        HelicsMsg.gld = HelicsMsg("gld" + case_config['SimulationConfig']['Substation'], 30, broker_port=unique_port_for_simulation)
        HelicsMsg.dso = HelicsMsg("dso" + case_config['SimulationConfig']['Substation'], dt, broker_port=unique_port_for_simulation)
        HelicsMsg.dso.config("uninterruptible", True)
        feeders = dso_val['feeders']
        feedercnt = 1
        previous_iteration_player_filenames = None
        model_list = []
        xfused_list = []
        comm_loads_list = []
        for feed_key, feed_val in feeders.items():
            print("\t<<<<< Chosen feeder -->> {0} >>>>>".format(feed_val['name']))
            if sim['simplifiedFeeders']:
                feed_val['name'] = 'sim_' + feed_val['name']
                print("\t<<<<< Going with the simplified feeders. >>>>>")
                print("\t<<<<< Feeder name changed to -->> {0} >>>>>".format(feed_val['name']))
            else:
                print("\t<<<<< Going with the full feeders. >>>>>")
            os.makedirs(caseName + '/' + feed_key)
            sim['OutputPath'] = caseName + '/' + feed_key
            sim['CaseName'] = feed_key
            case_config['BackboneFiles']['TaxonomyChoice'] = feed_val['name']
            # if feedercnt >= 2:
            #     current_bldg_count_for_each_player = {k: v for k, v in previous_iteration_player_filenames.items() if k not in players_added}
            current_bldg_count_for_each_player, list_bldgs_assigned, model, xfused, comm_loads = res_FG_dod.populate_feeder(climate_zone_count, feedercnt, current_player_filenames, current_bldg_count_for_each_player, bldgs_per_feeder, current_weather_folder_name, each_grid_name, list_bldgs_assigned, config=case_config)
            model_list.append(model)
            xfused_list.append(xfused)
            comm_loads_list.append(comm_loads)
            # previous_iteration_player_filenames = current_bldg_count_for_each_player
            # Then we want to create a JSON dictionary with the Feeder information
            gd.glm_dict(caseName + '/' + feed_key + '/' + feed_key, config=case_config,
                        ercot=sim['simplifiedFeeders'])
            shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                        caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

            # Next we create the agent dictionary along with the substation YAML file
            prep.prep_substation(caseName + '/' + feed_key + '/' + feed_key,
                                 caseName + '/' + dso_key + '/' + feed_key,
                                 caseName + '/' + weather_agent_name + '/',
                                 feedercnt,
                                 config=case_config,
                                 hvacSetpt=hvac_setpt,
                                 Q_forecast=sim['Q_bid_forecast_correction'],
                                 Q_dso_key=dso_key, unique_port_for_simulation=unique_port_for_simulation)
            feedercnt += 1
            print("=== DONE WITH FEEDER {0:s} for {1:s}. ======\n".format(feed_key, dso_key))



        # =================== Laurentiu Marinovici 12/13/2019 - Copperplate feeder piece =======
        if sim["CopperplateFeeder"]:
            print("!!!!! There are {0:d} / {1:d} commercial buildings left !!!!!".format(
                len(bldPrep['CommBldgPopulation'].keys()), len(comm_bldgs_pop)))
            if len(bldPrep['CommBldgPopulation'].keys()) > 0:
                print("!!!!! We are going with the copperplate feeder now. !!!!!")
                feed_key = "copperplate_feeder"
                feed_val['name'] = feed_key
                dso_val['feeders'][feed_key] = feed_val
                os.makedirs(caseName + '/' + feed_key)
                sim['OutputPath'] = caseName + '/' + feed_key
                sim['CaseName'] = feed_key
                case_config['BackboneFiles']['TaxonomyChoice'] = sim['CopperplateFeederName']
                case_config['BackboneFiles']['CopperplateFeederFile'] = sim['CopperplateFeederFile']
                cp_FG.populate_feeder(config=case_config)

                gd.glm_dict(caseName + '/' + feed_key + '/' + feed_key, config=case_config,
                            ercot=sim['simplifiedFeeders'])
                shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                            caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

                # Next we create the agent dictionary along with the substation YAML file
                prep.prep_substation(caseName + '/' + feed_key + '/' + feed_key,
                                     caseName + '/' + dso_key + '/' + feed_key,
                                     caseName + '/' + weather_agent_name + '/',
                                     feedercnt,
                                     config=case_config,
                                     hvacSetpt=hvac_setpt,
                                     Q_forecast=sim['Q_bid_forecast_correction'],
                                     Q_dso_key=dso_key, unique_port_for_simulation=unique_port_for_simulation)
                feedercnt += 1
                print("=== DONE WITH COPPERPLATE FEEDER {0:s} for {1:s}. ======\n".format(feed_key, dso_key))

        # ======================================================================================
        print("\n=== MERGING THE FEEDERS UNDER ONE SUBSTATION =====")
        os.makedirs(caseName + "/" + sub_key)
        cm.merge_glm(os.path.abspath(caseName + '/' + sub_key + '/' + sub_key + '.glm'), list(dso_val['feeders'].keys()), 20)

        print("\n=== MERGING/WRITING THE SUBSTATION(GRIDLABD) MESSAGE FILE =====")
        HelicsMsg.gld.write_file(os.path.abspath(caseName + '/' + sub_key + '/' + sub_key + '.json'))

        print("\n=== MERGING/WRITING THE FEEDERS GLM DICTIONARIES =====")
        cm.merge_glm_dict(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_glm_dict.json'), list(dso_val['feeders'].keys()), 20)

        print("\n=== MERGING/WRITING THE SUBSTATION AGENT DICTIONARIES =====")
        cm.merge_agent_dict(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_agent_dict.json'), list(dso_val['feeders'].keys()))

        print("\n=== MERGING/WRITING THE DSO MESSAGE FILE =====")
        HelicsMsg.dso.write_file(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '.json'))

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

    tso.write_file(caseName + '/tso_h.json')

    # Also create the launch, kill and clean scripts for this case
    helpers.write_dsot_management_script(master_file="generate_case_config",
                                         case_path=caseName,
                                         system_config=sys_config,
                                         substation_config=dso_config,
                                         weather_config=weather_config, portno=unique_port_for_simulation)

    d1 = model_list[0]['transformer_configuration']
    d1_t = model_list[0]['transformer']
    new_d1 = {}
    for k, v in d1.items():
        new_d1[f"feeder1_{k}"] = v

    new_d1_t = {}
    for k, v in d1_t.items():
        v["configuration"] = "feeder1_" + v["configuration"]
        new_d1_t[f"feeder1_{k}"] = v

    d2 = model_list[1]['transformer_configuration']
    d2_t = model_list[1]['transformer']
    new_d2 = {}
    for k, v in d2.items():
        new_d2[f"feeder2_{k}"] = v

    new_d2_t = {}
    for k, v in d2_t.items():
        v["configuration"] = "feeder2_" + v["configuration"]
        new_d2_t[f"feeder2_{k}"] = v

    d1 = {**new_d1, **new_d2}
    d2 = {**new_d1_t, **new_d2_t}

    combined_dict_model = {}
    combined_dict_model['transformer_configuration'] = d1
    combined_dict_model['transformer'] = d2

    with open(f"{os.getcwd()}/{caseName}/Substation_1/model.json", "w") as fp:
        json.dump(combined_dict_model,fp)

    xf_1 = {}
    for k, v in xfused_list[0].items():
        xf_1[f"feeder1_{k}"] = v

    xf_2 = {}
    for k, v in xfused_list[1].items():
        xf_2[f"feeder2_{k}"] = v

    xf_tot = {**xf_1, **xf_2}

    with open(f"{os.getcwd()}/{caseName}/Substation_1/xfused.json", "w") as fp:
        json.dump(xf_tot,fp)

    combined_dict_com = {}
    for i in comm_loads_list:
        combined_dict_com = {**combined_dict_com, **i}

    with open(f"{os.getcwd()}/{caseName}/Substation_1/com_loads.json", "w") as fp:
        json.dump(combined_dict_com, fp)

    return list_bldgs_assigned


def ChangeWeatherFilename(t1, sys_config, weatherdat_filenames, lati, longi):
    print(f"Handling climate zone name = {t1}.")

    # script to change weather filename in the json config.
    data_Path = sys_config['dataPath']
    with open(os.path.join(data_Path, sys_config['dsoPopulationFile']), 'r', encoding='utf-8') as json_file:
        dso_config = json.load(json_file)
    dso_config["DSO_1"]["weather_file"] = [x for x in weatherdat_filenames if t1 in x][0]

    dso_config["DSO_1"]["latitude"] = lati
    dso_config["DSO_1"]["longitude"] = longi

    return dso_config

def ChangeBaseFeederFilename(dso_config, feeder_list_basesytheticglms, sys_config):
    # script to add desired synthetic feeders
    # delete any existing keys
    data_Path = sys_config['dataPath']
    for key in list(dso_config["DSO_1"]["feeders"].keys()):
        del dso_config["DSO_1"]["feeders"][key]
    for idx, feeder_name in enumerate(feeder_list_basesytheticglms):
        dso_config["DSO_1"]["feeders"][f"feeder{idx + 1}"] = {}
        dso_config["DSO_1"]["feeders"][f"feeder{idx + 1}"]["name"] = feeder_name
        dso_config["DSO_1"]["feeders"][f"feeder{idx + 1}"]["ercot"] = False

    # update the modified information.
    # save and overwrite the existing 1-hi-metadata-lean.json
    with open(os.path.join(data_Path, sys_config['dsoPopulationFile']), 'w') as fp:
        json.dump(dso_config, fp, sort_keys=True, indent=4)

    return dso_config

def saveintojson(data_to_save, filename_to_be_saved_as, data_Path):
    with open(os.path.join(data_Path, filename_to_be_saved_as), 'w') as fp:
        json.dump(data_to_save, fp, sort_keys=True, indent=4)

def CountOccurrencesinAllbaseGLMS(filenames, search_prhase):
    from tesp_support.api.data import feeders_path

    counts_comm_bldg_in_each_baseglm = {}
    for each_baseglm in filenames:
        count = 0
        fname = feeders_path + each_baseglm + '.glm'
        with open(fname, 'r') as f:
            for line in f.readlines():
                if search_prhase in line:
                    count += 1

        counts_comm_bldg_in_each_baseglm[each_baseglm] = count
    total_occurrences = sum(list(counts_comm_bldg_in_each_baseglm.values()))
    return counts_comm_bldg_in_each_baseglm, total_occurrences

def calculate_feeder_sets_to_create(f1_r1, f2_r2, target_resi, f1_c1, f2_c2, target_comm):
    a1 = math.ceil(target_resi/(f1_r1+f2_r2))
    a2 = math.ceil(target_comm/(f1_c1+f2_c2))

    feeder_set_count = max(a1, a2)

    return feeder_set_count


if __name__ == "__main__":
    mastercase = "8_hi_system_case_config"
    with open(mastercase + '.json', 'r', encoding='utf-8') as json_file:
        sys_config = json.load(json_file)
    customsuffix = "jul14_runs"  # "parallel_and_comm_overload_test2"

    unique_port_for_simulation = 90000  # 60300

    DoD_flag = True
    # DoD_simulation_config = "DoD_simulation_config.json"
    # DoDbuildingInfoDict = dict()
    #
    #
    # DoDbuildingInfoDict["climatefiles"] = []
    largesite_house_count = 3197  # this value comes from Keith's excel sheet. For commercial load count, it comes from
    # FEDS and Bob must have made sure it matches with Keith's excel sheet - "total_commercial_bldg_count".
    f1 = "R2-12.47-1"
    f2 = "R4-12.47-1"
    resi_com_load_count_map = {f1: {"comm": 80, "resi": 176}, f2: {"comm": 75, "resi": 523}}


    # get the weather files information
    # bus_loc = {'AZ_Tucson': ['AZ_arizona-tuscon', '_']}#,
    #            # 'WA_Tacoma': ['WA_washington-tacoma-city', '_'],
    #            # 'MT_Greatfalls': ['MT_montana-greatfalls', '_']}  # ,
    #            # 'AL_Dothan': ['alabama-dothan', '_'],
    #            # 'LA_Alexandria': ['Louisiana-Alexandria', '_']}
    bus_loc = {'AZ_Tucson': ['AZ_file', '_'],
               'WA_Tacoma': ['WA_file', '_'],
               'AL_Dothan': ['AL_file', '_'],
               'IA_Johnston': ['IA_file', '_'],
               'LA_Alexandria': ['LA_file', '_'],
               'AK_Anchorage': ['AK_file', '_'],
               'MT_Greatfalls': ['MT_file', '_']}
    # bus_loc = {'MT_Greatfalls': ['MT_file', '_']}
    file_name_dict = {'AZ_Tucson': 'Largesite_az.xlsx',
                      'WA_Tacoma': 'Largesite_wa.xlsx',
                      'AL_Dothan': 'Largesite_al.xlsx',
                      'IA_Johnston': 'Largesite_ia.xlsx',
                      'LA_Alexandria': 'Largesite_la.xlsx',
                      'AK_Anchorage': 'Largesite_ak.xlsx',
                      'MT_Greatfalls': 'Largesite_mt.xlsx'}
    # file_name_dict = {'AZ_Tucson': 'Mediumsite_az.xlsx',
    #                   'WA_Tacoma': 'Mediumsite_wa.xlsx',
    #                   'AL_Dothan': 'Mediumsite_al.xlsx',
    #                   'IA_Johnston': 'Mediumsite_ia.xlsx',
    #                   'LA_Alexandria': 'Mediumsite_la.xlsx',
    #                   'AK_Anchorage': 'Mediumsite_ak.xlsx',
    #                   'MT_Greatfalls': 'Mediumsite_mt.xlsx'}
    # file_name_dict = {'AZ_Tucson': 'Smallsite_az.xlsx',
    #                   'WA_Tacoma': 'Smallsite_wa.xlsx',
    #                   'AL_Dothan': 'Smallsite_al.xlsx',
    #                   'IA_Johnston': 'Smallsite_ia.xlsx',
    #                   'LA_Alexandria': 'Smallsite_la.xlsx',
    #                   'AK_Anchorage': 'Smallsite_ak.xlsx',
    #                   'MT_Greatfalls': 'Smallsite_mt.xlsx'}
    # file_name_dict = {'MT_Greatfalls': 'Largesite_mt.xlsx'}
    latlong_dict = {'AZ_Tucson': [32.13, -110.95],
                      'WA_Tacoma': [47.15, -122.48],
                      'AL_Dothan': [31.27, -85.72],
                      'IA_Johnston': [41.53, -93.67],
                      'LA_Alexandria': [31.32, -92.55],
                      'AK_Anchorage': [61.25, -149.8],
                      'MT_Greatfalls': [47.47, -111.38]}
    # latlong_dict = {'MT_Greatfalls': [47.47, -111.38]}

    # not sure how to use below variable but we would need it maybe.
    grid_size_mapping = {'Altus': 'small', 'Dodge': 'medium', 'Bragg': 'large', 'FortLiberty': 'large'}
    feeder_list_basesytheticglms = {'AZ_Tucson': {'Large': [f1, f2]},
                      'WA_Tacoma': {'Large': [f1, f2]},
                      'AL_Dothan': {'Large': [f1, f2]},
                      'IA_Johnston': {'Large': [f1, f2]},
                      'LA_Alexandria': {'Large': [f1, f2]},
                                    'AK_Anchorage': {'Large': [f1, f2]},
                                    'MT_Greatfalls': {'Large': [f1, f2]}}
    # feeder_list_basesytheticglms = {'AZ_Tucson': {'Medium': [f1, f2]},
    #                                 'WA_Tacoma': {'Medium': [f1, f2]},
    #                                 'AL_Dothan': {'Medium': [f1, f2]},
    #                                 'IA_Johnston': {'Medium': [f1, f2]},
    #                                 'LA_Alexandria': {'Medium': [f1, f2]},
    #                                 'AK_Anchorage': {'Medium': [f1, f2]},
    #                                 'MT_Greatfalls': {'Medium': [f1, f2]}}
    # feeder_list_basesytheticglms = {'AZ_Tucson': {'Small': [f1, f2]},
    #                                 'WA_Tacoma': {'Small': [f1, f2]},
    #                                 'AL_Dothan': {'Small': [f1, f2]},
    #                                 'IA_Johnston': {'Small': [f1, f2]},
    #                                 'LA_Alexandria': {'Small': [f1, f2]},
    #                                 'AK_Anchorage': {'Small': [f1, f2]},
    #                                 'MT_Greatfalls': {'Small': [f1, f2]}}

    # feeder_list_basesytheticglms = {'MT_Greatfalls': {'Large': [f1, f2]}}
        # {'AZ_Tucson': {'Large': ["R5-12.47-1","R5-12.47-2"]}}#, # "R5-12.47-1",
                                    #'WA_Tacoma': {'Large': ["R5-12.47-1","R5-12.47-2"]},
                                    #'MT_Greatfalls': {'Large': ["R5-12.47-1","R5-12.47-2"]}}

    # feeder_list_basesytheticglms = {'AK_Anchorage': {'Large': [f1, f2]}}  # , "R1-12.47-3", "R1-12.47-4", "R1-25.00-1", "R2-12.47-1", "R2-12.47-2", "R2-12.47-3", "R2-25.00-1", "R2-35.00-1", "R3-12.47-1", "R3-12.47-2", "R3-12.47-3", "R4-12.47-1", "R4-12.47-2", "R4-25.00-1", "R5-12.47-1", "R5-12.47-2", "R5-12.47-3", "R5-12.47-4", "R5-12.47-5", "R5-25.00-1", "R5-35.00-1"]}}  # , "R4-12.47-1", "R4-12.47-2"]}}  #
    # feeder_list_basesytheticglms = {'AZ_Tucson': {'Altus': ["R5-12.47-1", "R5-12.47-2"],
    #                                               'Dodge': ["R4-12.47-1", "R4-12.47-1"],
    #                                               'Bragg': ["R4-12.47-1", "R4-12.47-1"],
    #                                               'FortLiberty': ["R4-12.47-1", "R4-12.47-1"]},
    #                                 'WA_Tacoma': {'Altus': ["R4-12.47-1", "R4-12.47-1"],
    #                                               'Dodge': ["R4-12.47-1", "R4-12.47-1"],
    #                                               'Bragg': ["R4-12.47-1", "R4-12.47-1"],
    #                                               'FortLiberty': ["R4-12.47-1", "R4-12.47-1"]}}
    weather_path_inputs = "/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/data/8-node data/"
    # weatherdat_filenames = PSMv3toDAT.main(weather_path_psm_inputs, bus_loc, extract=False, getnames=True)
    weatherdat_filenames = EPWtoDAT.main(weather_path_inputs, bus_loc, extract=True, getnames=True,
                                YYYY_MM_DD=sys_config['StartTime'].split(" ")[0])
    weather_folder_names = {}
    weather_mappings_bldg_name = {}
    weather_mappings_bldg_count = {}
    for weather_zone_idx, each_weather_zone in enumerate(weatherdat_filenames):
        t1 = each_weather_zone.split("_")[1] + "_" + each_weather_zone.split("_")[2]

        file_name = file_name_dict[t1]
        print(f"Handling conversion and mapping of player files (all grids i.e., small, medium, large) for climate "
              f"zone = {t1}.")
        site_folder_names, mappings_bldg_name, mappings_bldg_count = ingest_bld_data.main(sys_config['StartTime'].split(" ")[0],sys_config['EndTime'].split(" ")[0],
                                                                                          os.getcwd() + '/',
                                                                                          weather_loc='FilesfromFEDS',
                                                                                          file_name=file_name,
                                                      weather_header=t1, extract=True, mapping=True)
        weather_folder_names[t1] = site_folder_names
        weather_mappings_bldg_name[t1] = mappings_bldg_name
        weather_mappings_bldg_count[t1] = mappings_bldg_count

    # based on weather files, the corresponding commercial and industrial load profiles must be loaded (done)
    # obtain the location of player files and mapping of buildings. (done)
    # We fix the base glm feeder data so we move the exact same base to different locations in US (done)

    # start debugging the functions called in the code and add player object and assign appropriately rated transformers
    # based on csv peak demand.

    # save the building mappings and count for future post processing when needed
    saveintojson(weather_mappings_bldg_name, filename_to_be_saved_as='weather_mappings_bldg_name.json',
                 data_Path=sys_config["dataPath"])
    saveintojson(weather_mappings_bldg_count, filename_to_be_saved_as='weather_mappings_bldg_count.json',
                 data_Path=sys_config["dataPath"])


    if len(sys.argv) > 6:
        prepare_case(int(sys.argv[1]), sys.argv[2], pv=int(sys.argv[3]), bt=int(sys.argv[4]), fl=int(sys.argv[5]), ev=int(sys.argv[6]))
    else:
        # for DoD project studies
        if DoD_flag:

            climate_zone_count = 0
            # for every climate zone
            for current_weather_folder_name, gridname_basefeeder_maps in weather_folder_names.items():

                climate_zone_count += 1


                # for every grid (small, medium, large, or a bunch of similar sized grids)
                for each_grid_name_idx, each_grid_name in enumerate(gridname_basefeeder_maps):



                    # has dictionary with keys being dummy bldg names and values being their total count on grid
                    current_bldg_count_for_each_player = weather_mappings_bldg_count[current_weather_folder_name][
                        each_grid_name]

                    # tempval = 5
                    # current_bldg_count_for_each_player = {}
                    # for ihji in range(tempval):
                    #     current_bldg_count_for_each_player[f"bld_{ihji+1}"] = current_bldg_count_for_each_player_backup[f"bld_{ihji+1}"]



                    total_commercial_bldg_count1 = sum(list(current_bldg_count_for_each_player.values()))

                    feeder_set_count = calculate_feeder_sets_to_create(f1_r1=resi_com_load_count_map[f1]["resi"],
                                                                       f2_r2=resi_com_load_count_map[f2]["resi"],
                                                                       target_resi=largesite_house_count,
                                                                       f1_c1=resi_com_load_count_map[f1]["comm"],
                                                                       f2_c2=resi_com_load_count_map[f2]["comm"],
                                                                       target_comm=total_commercial_bldg_count1)
                    # # temp modification - make every count = 1
                    # # NOTE: If "max" is result of residential in "calculate_feeder_sets_to_create" then the below
                    # # logic "may" have a problem but for the selected taxonomy feeders, this looks okay!
                    # total_comm_loads = resi_com_load_count_map[f1]["comm"] + resi_com_load_count_map[f2]["comm"]
                    # bldgs_per_type = math.floor(total_comm_loads/len(current_bldg_count_for_each_player.keys()))
                    # for key, value in current_bldg_count_for_each_player.items():
                    #     current_bldg_count_for_each_player[key] = 6


                    # feeder_set_count = 2
                    for i_idx in range(feeder_set_count):
                        list_bldgs_assigned = None
                        unique_port_for_simulation = unique_port_for_simulation + 100

                        # change the folder name as per the specific run being executed for diff. climate and grid.
                        sys_config["caseName"] = f"{current_weather_folder_name}_{each_grid_name}_{customsuffix}_{i_idx+1}"



                        total_commercial_bldg_count = sum(list(current_bldg_count_for_each_player.values()))

                        # adjust climate .dat file, feedernames
                        feeders_list_for_current_grid = feeder_list_basesytheticglms[current_weather_folder_name][each_grid_name]
                        dso_config = ChangeWeatherFilename(current_weather_folder_name, sys_config, weatherdat_filenames, latlong_dict[current_weather_folder_name][0], latlong_dict[current_weather_folder_name][1])
                        dso_config = ChangeBaseFeederFilename(dso_config, feeders_list_for_current_grid, sys_config)

                        # current list of player files for commercial buildings - access
                        # has a dictionary with keys being dummy filenames and values being actual names of buildings
                        current_player_filenames = weather_mappings_bldg_name[current_weather_folder_name][each_grid_name]



                        # find the total commercial buildings that need to be added and verify if the user input baseglms
                        # can accommodate them or not.
                        print(f"Climate zone = {current_weather_folder_name}, Current grid name = {each_grid_name}, "
                              f"Unique commercial building profiles from FEDS= {len(current_player_filenames)}, "
                              f"Total commercial bldgs to add on grid = {total_commercial_bldg_count}")

                        counts_comm_bldg_in_each_baseglm, total_occurrences = (
                            CountOccurrencesinAllbaseGLMS(filenames=feeders_list_for_current_grid,
                                                          search_prhase='load_class C'))

                        bldgs_per_feeder = total_commercial_bldg_count  # Kishan: look at this later carefully
                        if total_commercial_bldg_count > total_occurrences:
                            print(f"There are not enough commercial loads in base glms. Info = "
                                  f"{current_weather_folder_name}, {each_grid_name}, {feeders_list_for_current_grid}. From"
                                  f" FEDS = {total_commercial_bldg_count}, from GridLAB-D base glms = {total_occurrences}.")
                        else:
                            bldgs_per_feeder = int(total_commercial_bldg_count/len(feeders_list_for_current_grid))
                            # TODO: feeder1 has 25 comm loads and feeder has 15 comm loads. Total 40 and from FED 32.
                            #  32/2 = 18 per feeder. but feeder2 cant accommodate it.


                        saveintojson(sys_config,
                                     filename_to_be_saved_as=mastercase+'.json',
                                     data_Path=os.getcwd()+'/')
                        total_cnt = 0
                        for k, v in current_bldg_count_for_each_player.items():
                            total_cnt += v
                        if total_cnt > 0:
                            list_bldgs_assigned = prepare_case_dod(8, mastercase, current_player_filenames, current_bldg_count_for_each_player, bldgs_per_feeder, current_weather_folder_name, each_grid_name, list_bldgs_assigned, climate_zone_count, pv=0, bt=0, fl=1, ev=0, unique_port_for_simulation=unique_port_for_simulation)

                            k = 1

        else:
            # if I set pv flag, ev is also coming on
            # Qinjection, needs to be fixed
            # add solar and let it take weather info
            prepare_case(8, "8_hi_system_case_config", pv=0, bt=0, fl=1, ev=0)

        # prepare_case(200, "200_system_case_config", pv=0, bt=0, fl=0, ev=0)
        # prepare_case(200, "200_system_case_config", pv=0, bt=1, fl=0, ev=0)
        # prepare_case(200, "200_system_case_config", pv=0, bt=0, fl=1, ev=0)
        # prepare_case(200, "200_hi_system_case_config", pv=1, bt=0, fl=0, ev=0)
        # prepare_case(200, "200_hi_system_case_config", pv=1, bt=1, fl=0, ev=1)
        # prepare_case(200, "200_hi_system_case_config", pv=1, bt=0, fl=1, ev=1)

        # prepare_case(8, "8_system_case_config", pv=0, bt=0, fl=0, ev=0)
        # prepare_case(8, "8_system_case_config", pv=0, bt=1, fl=0, ev=0)
        # prepare_case(8, "8_system_case_config", pv=0, bt=0, fl=1, ev=0)
        # prepare_case(8, "8_hi_system_case_config", pv=1, bt=0, fl=0, ev=0)
        # prepare_case(8, "8_hi_system_case_config", pv=1, bt=1, fl=0, ev=1)
        # prepare_case(8, "8_hi_system_case_config", pv=1, bt=0, fl=1, ev=1)
