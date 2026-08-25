# Copyright (c) 2018-2025 Battelle Memorial Institute
# file: prepare_case_glm_dsot.py
""" Sets up a case folder of required files to run DSO+T use-case by populating
 a test feeder using gld_feeder_generator.py. 
 
 This 'prepare case' updates the original prepare_case_dsot.py by:
    - Utilizing the new gld_feeder_generator.py (feeder generator) that combines
      the functionality of the separate residential and commercial feeder gens. 
    - Updates the required configuration files, separating the monolithic 
      n_scenario_system_case_config.json files into case configs 
      (default_config.json5, rates_config.json5) and system configs
      (n_scenario_system_config.json5). System configs have been moved into the 
      dsot/data folder due to their relatively static nature.
    - Updates variable naming throughout dsot for clarity and consistency.
    - Utilizes .json5 for config files to make use of in-line comments for 
      improved user experience and understanding.

 Resulting case folder will contain:
    - DSO_n
        - Substation_n_agent_dict.json
        - Substation_n_glm_dict.json
        - Substation_n.json (dso_substation)
    - Substation_n
        - Substation_n.glm
        - Substation_n.json (gldSubstation_n)
    - weather_Substation_n
        - weather_Config.json
        - weather.dat
    - alt_player.json
    - case_config_n.json
    - clean.sh
    - docker-run.sh
    - gen_player.json
    - generate_case_config.json -> combines the case and system configs
    - gld_player.json
    - ind_player.json
    - kill.sh
    - model_dict.json
    - monitor.sh
    - postprocess.sh
    - ref_player.json
    - run.sh
    - tso_h.json


Public Functions:
    None
"""

import datetime
import json
import os
import shutil
import sys

import pandas as pd
import pyjson5
import tesp_support.api.gld_feeder_generator as gld_feeder
import tesp_support.dsot.case_merge as cm
import tesp_support.dsot.glm_dictionary as gd
import tesp_support.dsot.helpers_dsot as helpers
from tesp_support.api.data import feeder_entities_path as feeder_defaults
from tesp_support.api.helpers import HelicsMsg


# Configuration settings for the experimental case
def prepare_case(case:str):

    # We need to load in the case metadata (*config.json5)
    config_file = str('../data/' + case + '.json5')
    with open(config_file, 'r', encoding='utf-8') as json5_file:
        config = pyjson5.load(json5_file)

    # Define nodes, scenario and import required config files
    nodes = str(config["nodes"])
    if config["scenario"] == "hi":
        scenario = "_hi"
        config["renewables"] = ["wind", "solar"]
    else:
        scenario = ""
        config["renewables"] = ["wind"]
    
    # Use RECS metadata by default. [tesp_support/api/recs_gld_house_parameters.py]
    rcs = "RECS"
    sys.path.append('../')
    import prep_substation_recs as prep

    # Create empty list for glm dictionary files
    glm_dict_list = {}
    agent_dict_list = {}

    # Get path for other data
    data_path = config["data_path"]
    case_type = config["case_type"]

    if config["solver"] == 'cbc':
        config["quadratic"] = False

    pv = case_type["pv"]
    bt = case_type["bt"]
    ev = case_type["ev"]
    fl = case_type["fl"]

    config["market"] = False
    if pv is not None:
        case_type['pv'] = pv
        if pv > 0:
            config["caseName"] = config["caseName"] + "_pv"
    if bt is not None:
        case_type['bt'] = bt
        if bt > 0:
            config["caseName"] = config["caseName"] + "_bt"
            config["market"] = True
    if fl is not None:
        case_type["fl"] = fl
        if fl > 0:
            config["caseName"] = config["caseName"] + "_fl"
            config["market"] = True
    if ev is not None:
        case_type["ev"] = ev
        if ev > 0:
            config["caseName"] = config["caseName"] + "_ev"
            config["market"] = True

    system_config_file = os.path.join("../data/", config['system_file_' + nodes + scenario])
    if config["RECS"]:
        dso_config_file = os.path.join(data_path, config['population_file_' + rcs])
        res_config_file = os.path.join(data_path, config['residential_meta_file_' + rcs])
    else:
        dso_config_file = os.path.join(data_path, config['population_file_' + nodes + scenario])
        res_config_file = os.path.join(data_path, config['residential_meta_file_' + nodes + scenario])
    comm_config_file = os.path.join(data_path, config["commercial_meta_file"])
    batt_config_file = os.path.join(data_path, config["battery_meta_file"])
    ev_model_config_file = os.path.join(data_path, config["ev_meta_file"])
    ev_driving_config_file = os.path.join(data_path, config["ev_driving_meta_file"])
    hvac_setpt_file = os.path.join(data_path, config['hvac_' + rcs + '_set_point'])

    # load system config
    with open(system_config_file, 'r', encoding='utf-8') as json5_file:
        sys_config = pyjson5.load(json5_file)
    # load building and DSO metadata
    with open(dso_config_file, 'r', encoding='utf-8') as json_file:
        dso_config = json.load(json_file)
    # load residential metadata
    with open(res_config_file, 'r', encoding='utf-8') as json_file:
        res_config = json.load(json_file)
    # load commercial building metadata
    with open(comm_config_file, 'r', encoding='utf-8') as json_file:
        comm_config = json.load(json_file)
    # load battery metadata
    with open(batt_config_file, 'r', encoding='utf-8') as json_file:
        batt_config = json.load(json_file)
    # load ev model metadata
    with open(ev_model_config_file, 'r', encoding='utf-8') as json_file:
        ev_model_config = json.load(json_file)
    # load hvac set point metadata
    with open(hvac_setpt_file, 'r', encoding='utf-8') as json_file:
        hvac_setpt = json.load(json_file)
    # record aggregated hvac_setpoint_data from survey:
    # In this implementation individual house set point schedule may not
    # make sense but aggregated behavior will.
    # load feeder defaults
    with open(feeder_defaults, 'r', encoding='utf-8') as json_file:
        base_config = json.load(json_file)
    
    caseName = config["caseName"]
    StartTime = config["StartTime"]
    EndTime = config["EndTime"]

    # setting Tmax in seconds
    ep = datetime.datetime(1970, 1, 1)
    s = datetime.datetime.strptime(StartTime, '%Y-%m-%d %H:%M:%S')
    e = datetime.datetime.strptime(EndTime, '%Y-%m-%d %H:%M:%S')
    sIdx = (s - ep).total_seconds()
    eIdx = (e - ep).total_seconds()
    config["Tmax"] = int(eIdx - sIdx)

    gen = sys_config["gen"]
    genfuel = sys_config["genfuel"]
    tso_config = sys_config["DSO"]

    bldPrep = config["BuildingPrep"]
    mktPrep = config["MarketPrep"]
    weaPrep = config["WeatherPrep"]
    weather_config = {}

    # TODO: outputPath used and rewritten many times throughout this script
    outputPath = caseName # currently only used for the experiment management scripts

    # Remove 10 AM bid correction to AMES
    if not hasattr(config, "Q_bid_forecast_correction"):
            config["Q_bid_forecast_correction"] = {"default": {"correct": False}}
    if case_type['fl'] == 1:
        print('Correction of DSO bid for 10 AM AMES bid is performed')
    else:
        config["Q_bid_forecast_correction"] = {'default': config["Q_bid_forecast_correction"]['default']}
        print('NO 10 AM AMES bid correction')

    # Create the case folder. If it already exists, delete and create it
    if caseName != "" and caseName != ".." and caseName != ".":
        if os.path.isdir(caseName):
            print("experiment folder already exists, deleting and moving on...")
            shutil.rmtree(caseName)
        os.makedirs(caseName)
    else:
        print('Case name is blank or Case name is "." or ".." and could cause file deletion')

    # Create the output folder, if different. If it already exists, delete and create it
    if caseName != outputPath and outputPath != "" and outputPath != ".." and outputPath != ".":
        if os.path.isdir(outputPath):
            print("output folder already exists, deleting and moving on...")
            shutil.rmtree(outputPath)     
        os.makedirs(outputPath)

    # Record the case and system configs for this experiment in generate_case_config
    with open(os.path.join(caseName, 'generate_case_config.json'), 'w', encoding='utf-8') as json_file:
        json.dump(config | sys_config, json_file, indent=2)

    # write player helics config json file for load and generator players
    dt = config["dt"]
    sys_config["renewables"] = config["renewables"]

    if config["messenger"] == 'HELICS':
        helpers.write_players_msg(caseName, sys_config, dt)
        tso = HelicsMsg("pypower", dt)

    elif config["messenger"] == 'FNCS':
        # write player yaml(s) for load and generator players
        players = sys_config["players"]
        for idx in range(len(players)):
            player = sys_config[players[idx]]
            yaml_file = caseName + '/' + player[0] + '_player.yaml'
            yp = open(yaml_file, 'w')
            print('name: ' + player[0] + 'player', file=yp)
            print('time_delta: ' + str(dt) + 's', file=yp)
            print('broker: tcp://localhost:' + str(config["port"]), file=yp)
            print('aggregate_sub: true', file=yp)
            print('aggregate_pub: true', file=yp)
            yp.close()

        # write tso yaml beginning
        yaml_file = caseName + '/tso.yaml'
        yp = open(yaml_file, 'w')
        print('name: pypower', file=yp)
        print('time_delta: ' + str(dt) + 's', file=yp)
        print('broker: tcp://localhost:' + str(config["port"]), file=yp)
        print('values:', file=yp)

    # Config HELICS or FNCS subs/pubs. Running renewables: wind, solar
    if config["genPower"]:
        for i in range(len(gen)):
            if genfuel[i][0] in config["renewables"]:
                idx = str(genfuel[i][2])
                for plyr in ["genMn", "genForecastHr"]:
                    player = sys_config[plyr]
                    if player[6] and not player[8]:
                        if config["messenger"] == 'HELICS':
                            tso.subs_n(player[0] + "player/" + player[0] + "_power_" + idx, "string")
                        elif config["messenger"] == 'FNCS':
                            print('  ' + player[0].upper() + '_POWER_' + idx + ':', file=yp)
                            print('    topic: ' + player[0] + 'player/' + player[0] + '_power_' + idx, file=yp)
                            print('    default: 0', file=yp)
                    if player[7] and not player[8]:
                        if config["messenger"] == 'HELICS':
                            tso.subs_n(player[0] + "player/" + player[0] + "_pwr_hist_" + idx, "string")
                        elif config["messenger"] == 'FNCS':
                            print('  ' + player[0].upper() + '_PWR_HIST_' + idx + ':', file=yp)
                            print('    topic: ' + player[0] + 'player/' + player[0] + '_power_history_' + idx, file=yp)
                            print('    default: 0', file=yp)


    # Create the dso folders and populate the feeders
    for dso_key, dso_val in dso_config.items():
        # print('dso ->', dso_key)
        # print('val ->', json.dumps(dso_val, sort_keys=True, indent=2))

        if 'DSO' not in dso_key:
            continue

        sub_key = dso_val['substation']
        bus = str(dso_val['bus_number'])

        if config["messenger"] == 'HELICS':
            # Write the tso published connections for this substation
            tso.pubs_n(False, "cleared_q_rt_" + bus, "string")
            tso.pubs_n(False, "cleared_q_da_" + bus, "string")
            tso.pubs_n(False, "lmp_rt_" + bus, "string")
            tso.pubs_n(False, "lmp_da_" + bus, "string")
            tso.pubs_n(False, "three_phase_voltage_" + bus, "string")

            # Write the tso subscribe connections for this substation
            tso.subs_n("dso" + sub_key + "/rt_bid_" + bus, "string")
            tso.subs_n("dso" + sub_key + "/da_bid_" + bus, "string")

        elif config["messenger"] == 'FNCS':
            # Write the tso published connections for this substation
            print('  RT_BID_' + bus + ':', file=yp)
            print('    topic: ' + sub_key + '/rt_bid', file=yp)
            print('    default: 0', file=yp)
            print('  DA_BID_' + bus + ':', file=yp)
            print('    topic: ' + sub_key + '/da_bid', file=yp)
            print('    default: 0', file=yp)

        try:
            # Running reference load, using a player for the load reference for comparison
            player = sys_config['refLoadMn']
            if player[6] and player[8]:
                if config["messenger"] == 'HELICS':
                    tso.subs_n(player[0] + "player/" + player[0] + "_load_" + bus, "string")
                elif config["messenger"] == 'FNCS':
                    print('  ' + player[0].upper() + '_LOAD_' + bus + ':', file=yp)
                    print('    topic: ' + player[0] + 'player/' + player[0] + '_load_' + bus, file=yp)
                    print('    default: 0', file=yp)
            if player[7] and player[8]:
                if config["messenger"] == 'HELICS':
                    tso.subs_n(player[0] + "player/" + player[0] + "_ld_hist_" + bus, "string")
                elif config["messenger"] == 'FNCS':
                    print('  ' + player[0].upper() + '_LD_HIST_' + bus + ':', file=yp)
                    print('    topic: ' + player[0] + 'player/' + player[0] + '_load_history_' + bus, file=yp)
                    print('    default: 0', file=yp)
            if not dso_val['used']:
                # Running reference load res and ind, (no gridlabd instance, using a player for the load)
                player = sys_config['gldLoad']
                if player[6] and player[8]:
                    if config["messenger"] == 'HELICS':
                        tso.subs_n(player[0] + "player/" + player[0] + "_load_" + bus, "string")
                    elif config["messenger"] == 'FNCS':
                        print('  ' + player[0].upper() + '_LOAD_' + bus + ':', file=yp)
                        print('    topic: ' + player[0] + 'player/' + player[0] + '_load_' + bus, file=yp)
                        print('    default: 0', file=yp)
                if player[7] and player[8]:
                    if config["messenger"] == 'HELICS':
                        tso.subs_n(player[0] + "player/" + player[0] + "_ld_hist_" + bus, "string")
                    elif config["messenger"] == 'FNCS':
                        print('  ' + player[0].upper() + '_LD_HIST_' + bus + ':', file=yp)
                        print('    topic: ' + player[0] + 'player/' + player[0] + '_load_history_' + bus, file=yp)
                        print('    default: 0', file=yp)
                continue
        except Exception:
            pass

        os.makedirs(caseName + '/' + dso_key)

        # Copy dso default config
        config["DSO"] = dso_key
        config["dso_key"] = dso_val
        config["caseName"] = dso_key
        config["substation"] = sub_key
        config["outputPath"] = caseName + '/' + dso_key
        config["bulk_power_bus"] = dso_val['bus_number']
        config["DSO_type"] = dso_val['utility_type']
        if config["RECS"]:
            config["state"] = dso_val['state']
            config["income_level"] = dso_val['income_level']
        config["rooftop_pv_rating_MW"] = dso_val['rooftop_pv_rating_MW']
        config["scaling_factor"] = dso_val['scaling_factor']
        config["serverPort"] = 5150 + (int(bus) // 20)

        bldPrep['solar_data_path'] = config["solar_data_path"]
        prefix = ''
        if nodes == "8":
            prefix = '8-node '
        bldPrep['solar_P_player_file'] = prefix + dso_key + '/' + dso_key + '_' + config["solar_P_player_file"]
        bldPrep['solar_Q_player_file'] = prefix + dso_key + '/' + dso_key + '_' + config["solar_Q_player_file"]

        # For the copperplate feeder
        bldPrep['data_path'] = "../data/"
        bldPrep['CommBldgMetaData'] = comm_config
        bldPrep['ResBldgMetaData'] = res_config
        bldPrep['battery_meta_file'] = batt_config
        bldPrep['ev_meta_file'] = ev_model_config
        bldPrep['ev_driving_meta_file'] = config["ev_driving_meta_file"]
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
        mktPrep['DSO']['number_of_customers'] = dso_val['number_of_customers']
        mktPrep['DSO']['RCI customer count mix'] = dso_val['RCI customer count mix']
        mktPrep['DSO']['number_of_gld_homes'] = dso_val['number_of_gld_homes']

        # Weather is set per substation, with all feeders under the substation 
        # having the same weather profile. The values below need to refer to the 
        # DSO weather profile: choice/name/path/source/coordinates should match
        # coordinates (lat/long) for solar gain calcs and such.
        # NOTE: This can be misused
        weather_agent_name = 'weather_' + sub_key
        #WeatherChoice is not used
        #weaPrep['WeatherChoice'] = str.upper(os.path.splitext(dso_val['weather_file'])[1][1:])
        weaPrep['Name'] = weather_agent_name
        weaPrep['DataSource'] = dso_val['weather_file']
        weaPrep['Latitude'] = dso_val['latitude']
        weaPrep['Longitude'] = dso_val['longitude']
        weaPrep['TimeZoneOffset'] = dso_val['time_zone_offset']

        # Could eliminate code here by changing helpers_dsot.py, since only one 
        # weather for DSO.
        weather_config[weather_agent_name] = {
                #'type': weaPrep['WeatherChoice'],
                'source': weaPrep['DataSource'],
                'latitude': weaPrep['Latitude'],
                'longitude': weaPrep['Longitude'],
                'time_zone_offset': weaPrep['TimeZoneOffset']}

        # Make weather agent folder
        try:
            os.makedirs(caseName + '/' + weather_agent_name)
        except Exception:
            pass

        # Copy the .dat file from its location into the weather agent folder
        src = os.path.join(os.path.abspath(data_path + config["weather_data_source_path_" + nodes]), dso_val['weather_file'])
        dst = os.path.join(os.path.abspath(caseName), weather_agent_name, 'weather.dat')
        shutil.copy(src, dst)

        # Copy the case configs for each DSO
        def convert_sets_to_lists(obj):
            if isinstance(obj, dict):
                return {_k: convert_sets_to_lists(_v) for _k, _v in obj.items()}
            elif isinstance(obj, list):
                return [convert_sets_to_lists(element) for element in obj]
            elif isinstance(obj, set):
                return list(obj)
            else:
                return obj

        case_config_dump = convert_sets_to_lists(config)
        with open(caseName + '/case_config_' + str(dso_val['bus_number']) + '.json', 'w') as outfile:
            json.dump(case_config_dump, outfile, ensure_ascii=False, indent=2)

        if config["messenger"] == 'HELICS':
            HelicsMsg.gld = HelicsMsg("gld" + config["substation"], 30)
            HelicsMsg.dso = HelicsMsg("dso" + config["substation"], dt)
            HelicsMsg.dso.config("uninterruptible", True)
        else:
            pass

        feeders = dso_val['feeders']
        feedercnt = 1
        config["comm_count"] = 1
        for feed_key, feed_val in feeders.items():
            print("\t<<<<< Chosen feeder -->> {} >>>>>".format(feed_val['name']))
            config["taxonomy"] = feed_val['name']
            if config["simplifiedFeeders"]:
                feed_val['name'] = 'config_' + feed_val['name']
                print("\t<<<<< Going with the simplified feeders. >>>>>")
                print("\t<<<<< Feeder name changed to -->> {} >>>>>".format(feed_val['name']))
            else:
                print("\t<<<<< Going with the full feeders. >>>>>")
            os.makedirs(caseName + '/' + feed_key)
            config["outputPath"] = caseName + '/' + feed_key
            config["caseName"] = feed_key
            taxchoice = {item[0]: item[1:] for item in base_config["taxchoice"]}
            config["vll"] = taxchoice[feed_val['name']][0]
            config["vln"] = taxchoice[feed_val['name']][1]
            config["avg_house"] = taxchoice[feed_val['name']][2]
            config["avg_commercial"] = taxchoice[feed_val['name']][3]
            config["taxonomy"] = f"{feed_val['name']}.glm" 
            config["includes"] = [
                "${TESPDIR}/data/schedules/appliance_schedules.glm",
                "${TESPDIR}/data/schedules/water_and_setpoint_schedule_v5.glm",
                "${TESPDIR}/data/schedules/commercial_schedules.glm"
                ]
            config["sets"] = {
                "minimum_timestep": config["minimum_step"],
                "relax_naming_rules": 1,
                "warn": 0
                }
            config["defines"] = {"INVERTER_MODE": "CONSTANT_PQ",
                "INV_VBASE": 240.0,
                "INV_V1": 0.92,
                "INV_V2": 0.98,
                "INV_V3": 1.02,
                "INV_V4": 1.08,
                "INV_Q1": 0.44,
                "INV_Q2": 0.0,
                "INV_Q3": 0.0,
                "INV_Q4": -0.44,
                "INV_VIN": 200.0,
                "INV_IIN": 32.5,
                "INV_VVLOCKOUT": 300.0,
                "INV_VW_V1": 1.05,
                "INV_VW_V2": 1.1,
                "INV_VW_P1": 1.0,
                "INV_VW_P2": 0.0}
            config["use_solar_player"] = True
            config["rooftop_pv_rating_MW"] = dso_val['rooftop_pv_rating_MW']
            config["weather_name"] = 'weather_' + sub_key
            config["latitude"] = weaPrep['Latitude']
            config["longitude"] = weaPrep['Longitude']
            #config["weather"] = weaPrep['WeatherChoice']
            config["region"] = dso_val['climate_zone']
            config["state"] = dso_val['state']
            config["res_dso_type"] = 'No_DSO_Type'
            config["utility_type"] = dso_val['utility_type']
            config["number_of_gld_homes"] = dso_val['number_of_gld_homes']
            config["RCI_customer_count_mix"] = dso_val['RCI customer count mix']
            config["comm_customers_per_bldg"] = dso_val['comm_customers_per_bldg']
            config["income_level"] = dso_val['income_level']
            config["ev_reserved_soc"] = config["AgentPrep"]['EV']['EVReserveLo']
            config["climate"] = dso_val['ashrae_zone']
            config["outputPath"] = f'{config["outputPath"]}/{config["caseName"]}.glm'
            
            # Dump the modified config to json5 to be read in by feeder generator
            config_dump = pyjson5.dumps(config, indent=2)
            output_file = 'config_dump.json5'
            with open(os.path.join("../data/", output_file), 'w', encoding='utf-8') as file:
                file.write(config_dump)
            config_dump = gld_feeder.Config(os.path.join("../data/", output_file))
            gld_feeder.Feeder(config_dump, "full")
            config["BuildingPrep"]['CommBldgPopulation'] = gld_feeder.comm_bldgs_pop
            os.remove(os.path.join("../data/", output_file))
           
            # Write the glm_dictionary for each substation
            gd.glm_diction(caseName, feed_key)
            shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                        caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

            # Create the agent dictionary along with the substation YAML file
            prep.prep_substation(caseName + '/' + feed_key + '/' + feed_key,
                                 caseName + '/' + dso_key + '/' + feed_key,
                                 caseName + '/' + weather_agent_name + '/',
                                 feedercnt,
                                 config=config,
                                 hvacSetpt=hvac_setpt)

            # Save the position data for plotting
            if config["make_plot"]:
                if feedercnt == 1:
                    position = gld_feeder.position
                else:
                    pos = gld_feeder.position
                    position.update(pos)
            else:
                position = {}

            feedercnt += 1
            config["comm_count"] += 1
            print(f"====== DONE WITH FEEDER {feed_key:s} for {dso_key:s}. ======\n")

        # Copperplate feeder piece
        #bldPrep['CommBldgPopulation'] = gld_feeder.comm_bldgs_pop
        if config["copperplate_feeder"]:
            if len(bldPrep['CommBldgPopulation'].keys()) > 0:
                print("------We are going with the copperplate feeder now------")
                feed_key = "copperplate_feeder"
                feed_val['name'] = feed_key
                dso_val['feeders'][feed_key] = feed_val
                os.makedirs(caseName + '/' + feed_key)
                config["outputPath"] = caseName + '/' + feed_key
                config["caseName"] = feed_key
                config["outputPath"] = f'{config["outputPath"]}/{config["caseName"]}.glm'
                config['taxonomy'] = f'{config["copperplate_feeder_name"]}.glm'
                config["backbone_files"] = config["copperplate_feeder_file"]
                config["gis_file"] = False
                config_dump = pyjson5.dumps(config, indent=2)
                output_file = 'copper_config_dump.json5'
                with open(os.path.join("../data/", output_file), 'w', encoding='utf-8') as file:
                    file.write(config_dump)
                config_dump = gld_feeder.Config(os.path.join("../data/", output_file))
                gld_feeder.Feeder(config_dump, "copp")
                os.remove(os.path.join("../data/", output_file))

                gd.glm_diction(caseName, feed_key)
                shutil.move(caseName + '/' + feed_key + '/' + feed_key + '_glm_dict.json',
                            caseName + '/' + dso_key + '/' + feed_key + '_glm_dict.json')

                # Create the agent dictionary along with the substation YAML file
                prep.prep_substation(caseName + '/' + feed_key + '/' + feed_key,
                                     caseName + '/' + dso_key + '/' + feed_key,
                                     caseName + '/' + weather_agent_name + '/',
                                     feedercnt,
                                     config=config,
                                     hvacSetpt=hvac_setpt)

                # Save the position data for plotting
                if config["make_plot"]:
                    if feedercnt == 1:
                        position = gld_feeder.position
                    else:
                        pos = gld_feeder.position
                        # Manually scale and translate feeder position data to fit w/ taxonomy
                        pos = {key: [value[0]*1000, value[1]*1000] for key, value in pos.items()}
                        position.update(pos)
                else:
                    position = {}
                feedercnt += 1
                print(f"=== DONE WITH COPPERPLATE FEEDER {feed_key:s} for {dso_key:s}. ======\n")

        # ======================================================================
        print("\n=== MERGING THE FEEDERS UNDER ONE SUBSTATION =====")
        os.makedirs(caseName + "/" + sub_key)
        cm.glm_merge(os.path.abspath(caseName + '/' + sub_key + '/' + sub_key + '.glm'), list(dso_val['feeders'].keys()), 20, config["make_plot"], position)

        print("\n=== MERGING/WRITING THE SUBSTATION(GRIDLABD) MESSAGE FILE =====")
        if config["messenger"] == 'HELICS':
            HelicsMsg.gld.write_file(os.path.abspath(caseName + '/' + sub_key + '/' + sub_key + '.json'))
        elif config["messenger"] == 'FNCS':
            cm.merge_fncs_config(os.path.abspath(caseName + '/' + sub_key + '/' + sub_key + '_gridlabd.txt'), list(dso_val['feeders'].keys()))

        print("\n=== MERGING/WRITING THE FEEDERS GLM DICTIONARIES =====")
        cm.merge_glm_dict(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_glm_dict.json'), list(dso_val['feeders'].keys()), 20)
        if config["RECS"]:
            glm_dict_list[dso_key] = os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_glm_dict.json')

        print("\n=== MERGING/WRITING THE SUBSTATION AGENT DICTIONARIES =====")
        cm.merge_agent_dict(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_agent_dict.json'), list(dso_val['feeders'].keys()))
        if config["RECS"]:
            agent_dict_list[dso_key] = os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '_agent_dict.json')

        print("\n=== MERGING/WRITING THE DSO MESSAGE FILE =====")
        if config["messenger"] == 'HELICS':
            HelicsMsg.dso.write_file(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '.json'))
        elif config["messenger"] == 'FNCS':
            cm.merge_substation_yaml(os.path.abspath(caseName + '/' + dso_key + '/' + sub_key + '.yaml'), list(dso_val['feeders'].keys()))

        # Cleanup after feeders had been merged
        foldersToDelete = [name for name in os.listdir(os.path.abspath(caseName))
                           if os.path.isdir(os.path.join(os.path.abspath(caseName), name)) and 'feeder' in name]
        print(f"=== Removing the following folders: {foldersToDelete}. ===")
        [shutil.rmtree(os.path.join(os.path.abspath(caseName), folder)) for folder in foldersToDelete]

        filesToDelete = [name for name in os.listdir(os.path.abspath(caseName + '/' + dso_key))
                         if os.path.isfile(os.path.join(os.path.abspath(caseName + '/' + dso_key), name)) and 'feeder' in name]
        print(f"=== Removing the following files: {filesToDelete} for {dso_key}. ===")
        [os.remove(os.path.join(os.path.abspath(caseName + '/' + dso_key), fileName)) for fileName in filesToDelete]

        # Create the launch, kill and clean scripts for this case
        if config["messenger"] == 'HELICS':
            helpers.write_dsot_management_script(master_file="generate_case_config",
                                                case_path=caseName,
                                                config=config,
                                                system_config=sys_config,
                                                substation_config=dso_config,
                                                weather_config=weather_config)
        elif config["messenger"] == 'FNCS':
            helpers.write_dsot_management_script_f(master_file="generate_case_config",
                                    case_path=caseName,
                                    config=config,
                                    system_config=sys_config,
                                    substation_config=dso_config,
                                    weather_config=weather_config)
        
    if config["messenger"] == 'HELICS':
        tso.write_file(caseName + '/tso_h.json')
    elif config["messenger"] == 'FNCS':
        yp.close()

    # --------------------------------------------------------------------------
    # Provide user with relevant summary statistics to verify case preparation.
    # Residential population summary:
    # --------------------------------------------------------------------------
    if config["RECS"]:
        hse_df = pd.DataFrame()
        bldg_df = pd.DataFrame()
        hvac_agent_df = pd.DataFrame()
        # Get house parameters from each DSO glm_dict
        for dso_k, f_str in glm_dict_list.items():
            with open(f_str) as f:
                glm_dict = json.load(f)
            res_df = pd.DataFrame.from_dict(glm_dict['houses'], orient='index')
            res_df = res_df.reset_index()
            res_df['DSO'] = dso_k # add a column for DSO number
            # Add columns to distinguish houses and each DER
            for inc in ['Low', 'Middle', 'Upper', '']:
                for k, v in {'house':inc, 'battery':'bat', 'solar':'sol', 'ev':'chgr'}.items():
                    for val in glm_dict['billingmeters'].values():
                        children = val['children']
                        if len([s for s in children if inc in s]) > 0:
                            if len([s for s in children if v in s]) > 0:
                                res_df.loc[res_df['index']==[next(s for s in children if inc in s)],k] = 'Yes'
                            else:
                                res_df.loc[res_df['index']==[next(s for s in children if inc in s)],k] = 'No'
            # Merge all DSO house parameters into one dataframe
            hse_df = pd.concat([hse_df,res_df],ignore_index=True)
            bldg_df = hse_df
        # Get HVAC agent data
        for dso_k, f_str in agent_dict_list.items():
            with open(f_str) as f:
                agent_dict = json.load(f)
            temp_df2 = pd.DataFrame.from_dict(agent_dict['hvacs'],orient='index')
            temp_df2 = temp_df2.reset_index()
            temp_df2['DSO'] = dso_k # add a column for DSO number
            hvac_agent_df = pd.concat([hvac_agent_df,temp_df2],ignore_index=True)
        # Save for later analysis
        hse_df.to_csv(os.path.abspath(caseName + '/' + 'house_parameters.csv'))
        hvac_agent_df.to_csv(os.path.abspath(caseName + '/' + 'hvac_agents.csv'))
        # Get totals
        low_hses = len(hse_df.loc[(hse_df['income_level']=='Low')])
        middle_hses = len(hse_df.loc[(hse_df['income_level']=='Middle')])
        upper_hses = len(hse_df.loc[(hse_df['income_level']=='Upper')])
        com_bldgs = len(hse_df.loc[(hse_df['income_level']=='')])
        def get_total(bldg_name:str):
            """Returns the total number of buildings in the case population of 
            the given building type.

            Args:
                bldg_name (str): office, warehouse_storage, big_box, strip_mall
                    education, food_service, food_sales, lodging, 
                    healthcare_inpatient, and low_occupancy

            Returns:
                int: bldg_tot, the number of buildings of a given building type
            """
            bldg_tot = len(bldg_df.loc[(bldg_df['house_class']==bldg_name) & (bldg_df['house']!='')])
            return bldg_tot
        # Excluding commercial and industrial buildings where income_level = None:
        tot_hses = low_hses + middle_hses + upper_hses
        sol_hses = len(hse_df.loc[(hse_df['solar']=='Yes') & (hse_df['income_level'] !='')])
        sol_com = len(bldg_df.loc[(bldg_df['solar']=='Yes') & (hse_df['income_level'] =='')])
        ev_hses = len(hse_df.loc[(hse_df['ev']=='Yes') & (hse_df['income_level'] !='')])
        ev_com = len(bldg_df.loc[(bldg_df['ev']=='Yes')& (hse_df['income_level'] =='')])
        bat_hses = len(hse_df.loc[(hse_df['battery']=='Yes') & (hse_df['income_level'] !='')])
        bat_com = len(bldg_df.loc[(bldg_df['battery']=='Yes')& (hse_df['income_level'] =='')])
        elec_wh_hses = len(hse_df.loc[(hasattr(hse_df, 'wh_gallons')) & (hse_df['income_level'] !='')])
        elec_sh_hses = len(hse_df.loc[(hse_df['fuel_type']=='electric') & (hse_df['income_level'] !='')])
        print("=== RESIDENTIAL POPULATION SUMMARY ===")
        print(f"Number of residential homes {tot_hses}")
        print("=== Income (Percent of all homes) ===")
        print(f"=== Low: {round(100*low_hses/tot_hses,2)}%, Middle: {round(100*middle_hses/tot_hses,2)}%, Upper: {round(100*upper_hses/tot_hses,2)}%. ===")
        print("=== DERs (Percent of all homes) ===")
        print(f"=== Solar: {round(100*sol_hses/tot_hses,2)}%, EVs: {round(100*ev_hses/tot_hses,2)}%, Batteries: {round(100*bat_hses/tot_hses,2)}%. ===")
        print("=== Electric Water Heating/Space Heating (Percent of all homes) ===")
        print(f"=== Water Heating: {round(100*elec_wh_hses/tot_hses,2)}%, Space Heating: {round(100*elec_sh_hses/tot_hses,2)}%. ===")
        print(f"=== COMMERCIAL POPULATION SUMMARY for {caseName} ===")
        print(f"Number of commercial building zones: {com_bldgs}")
        print("=== DERs (Percent of all building zones) ===")
        print(f"=== Solar: {round(100*sol_com/com_bldgs,2)}%, EVs: {round(100*ev_com/com_bldgs,2)}%, Batteries: {round(100*bat_com/com_bldgs,2)}%. ===")
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prepare_case(sys.argv[1])
    else:
        #prepare_case('default_config')
        prepare_case('rates_config')