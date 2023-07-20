# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: microgrid_agent.py
"""Manages the Transactive Control scheme for DSO+T implementation version 1

Public Functions:
    :substation_loop: initializes and runs the agents

"""

import json
import logging as log
import time
from copy import deepcopy
from datetime import datetime, timedelta

# import solve_RT_consensus as consenus
import helics as h
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from tesp_support.api.helpers import enable_logging
from tesp_support.api.metrics_collector import MetricsStore, MetricsCollector

from tesp_support.dsot.hvac_agent import HVACDSOT
from tesp_support.dsot.battery_agent import BatteryDSOT
from tesp_support.dsot.water_heater_agent import WaterHeaterDSOT

import tesp_support.consensus.microgrid as consensus
from .forecasting import Forecasting
from .dso_market import DSOMarket
from .retail_market import RetailMarket

# import multiprocessing as mp
NUM_CORE = 1

def register_federate(json_filename):
    print('register_federate -->', json_filename, flush=True)
    fed = h.helicsCreateCombinationFederateFromConfig(json_filename)
    federate_name = h.helicsFederateGetName(fed)
    print(" Federate {} has been registered".format(federate_name), flush=True)
    pubkeys_count = h.helicsFederateGetPublicationCount(fed)
    subkeys_count = h.helicsFederateGetInputCount(fed)
    endkeys_count = h.helicsFederateGetEndpointCount(fed)
    # ####################   Reference to Publications and Subscription form index  #############################
    pubid = {}
    subid = {}
    endid = {}
    for i in range(0, pubkeys_count):
        pubid["m{}".format(i)] = h.helicsFederateGetPublicationByIndex(fed, i)
        pub_type = h.helicsPublicationGetType(pubid["m{}".format(i)])
        pub_key = h.helicsPublicationGetName(pubid["m{}".format(i)])
        print('Registered Publication ---> {} - Type {}'.format(pub_key, pub_type))
    for i in range(0, subkeys_count):
        subid["m{}".format(i)] = h.helicsFederateGetInputByIndex(fed, i)
        status = h.helicsInputSetDefaultString(subid["m{}".format(i)], 'default')
        sub_key = h.helicsInputGetTarget(subid["m{}".format(i)])
        print('Registered Subscription ---> {}'.format(sub_key))
    for i in range(0, endkeys_count):
        endid["m{}".format(i)] = h.helicsFederateGetEndpointByIndex(fed, i)
        end_key = h.helicsEndpointGetName(endid["m{}".format(i)])
        print('Registered Endpoint ---> {}'.format(end_key))

    return fed, federate_name

def destroy_federate(fed):
    h.helicsFederateDisconnect(fed)
    h.helicsFederateFree(fed)
    h.helicsCloseLibrary()

def worker(arg):
    # timing(arg.__class__.__name__, True)
    # worker_results = arg.DA_optimal_quantities()
    # timing(arg.__class__.__name__, False)
    # return batt_da_solve(arg.DA_optimal_quantities_model())
    return arg.DA_optimal_quantities()

def inner_substation_loop(configfile, metrics_root, with_market):
    """ Helper function that initializes and runs the DSOT agents

    TODO: This needs to be updated
    Reads configfile. Writes *auction_metrics_root_metrics.json* and
    *controller_metrics_root_metrics.json* upon completion.

    Args:
        configfile (str): fully qualified path to the JSON agent configuration file
        metrics_root (str): base name of the case for metrics output
        with_market (bool): flag that determines if we run with markets
    """

    parallel = Parallel(n_jobs=NUM_CORE, backend='multiprocessing', verbose=10)

    def timing(agent_name, start_stop):
        if profile:
            if start_stop:
                proc_time0[agent_name] = time.perf_counter()
                wall_time0[agent_name] = time.time()
            else:
                proc_time[agent_name] += time.perf_counter() - proc_time0[agent_name]
                wall_time[agent_name] += time.time() - wall_time0[agent_name]

    profile = True
    proc_time0 = {}
    wall_time0 = {}
    proc_time = {}
    wall_time = {}
    proc = ['init', 'sim', 'battRT', 'hvacRT', 'whRT', 'forecastHVAC', 'forecastWH',
            'BatteryDSOT', 'HVACDSOT', 'WaterHeaterDSOT', 'granted', 'metrics', 'batt_opt', 'finalize_writing',
            'write_metrics']
    if profile:
        for p in proc:
            proc_time0[p] = 0.0
            wall_time0[p] = 0.0
            proc_time[p] = 0.0
            wall_time[p] = 0.0

    timing(proc[0], True)
    #    r = input("Ready")
    # load the JSON configurations
    with open(metrics_root + "_agent_dict.json", 'r', encoding='utf-8') as lp:
        config = json.load(lp)
    with open(metrics_root + "_glm_dict.json", 'r', encoding='utf-8') as gp:
        config_glm = json.load(gp)

    # enable logging
    level = config['LogLevel']
    enable_logging(level, 11)

    log.info('starting substation loop...')
    log.info('config file -> ' + configfile)
    log.info('metrics root -> ' + metrics_root)
    log.info('with markets -> ' + str(with_market))

    time_format = '%Y-%m-%d %H:%M:%S'
    start_time = config['StartTime']
    end_time = config['EndTime']
    solver = config['solver']
    simulation_duration = int((datetime.strptime(end_time, time_format) -
                               datetime.strptime(start_time, time_format)).total_seconds())
    current_time = datetime.strptime(start_time, time_format)

    log.info('simulation start time -> ' + start_time)
    log.info('simulation end time -> ' + end_time)
    log.info('simulation duration in seconds -> ' + str(simulation_duration))

    dso_config = {}
    topic_map = {}  # Map to dispatch incoming FNCS messages. Format [<key>][<receiving object function>]
    dso_market_obj = {}
    dso_unit = 'kW'  # default that will be overwritten by the market definition
    retail_market_obj = {}
    retail_period_da = 3600  # default that will be overwritten by the market definition
    retail_period_rt = 300  # default that will be overwritten by the market definition
    retail_unit = 'kW'  # default that will be overwritten by the market definition

    # instantiate the forecasting object and map their fncs input
    # forecast_obj = Forecasting(int(os.environ.get('SCHEDULE_PORT')))  # make object
    forecast_obj = Forecasting()
    weather_topic = config_glm['climate']['name']
    topic_map[weather_topic + '#SolarDiffuseForecast'] = [forecast_obj.set_solar_diffuse_forecast]
    topic_map[weather_topic + '#SolarDirectForecast'] = [forecast_obj.set_solar_direct_forecast]
    # Create schedule dataframes for schedule forecast for the whole simulation year
    # first, set the simulation year
    forecast_obj.set_sch_year(current_time.year)
    # Now, Let's read all schedules
    support_path = '../../../../../../support/schedules/'
    appliance_sch = ['responsive_loads', 'unresponsive_loads']
    wh_sch = ['small_1', 'small_2', 'small_3', 'small_4', 'small_5', 'small_6',
              'large_1', 'large_2', 'large_3', 'large_4', 'large_5', 'large_6']
    comm_sch = ['retail_heating', 'retail_cooling', 'retail_lights', 'retail_plugs', 'retail_gas',
                'retail_exterior', 'retail_occupancy',
                'lowocc_heating', 'lowocc_cooling', 'lowocc_lights', 'lowocc_plugs', 'lowocc_gas',
                'lowocc_exterior', 'lowocc_occupancy',
                'office_heating', 'office_cooling', 'office_lights', 'office_plugs', 'office_gas',
                'office_exterior', 'office_occupancy',
                'alwaysocc_heating', 'alwaysocc_cooling', 'alwaysocc_lights', 'alwaysocc_plugs', 'alwaysocc_gas',
                'alwaysocc_exterior', 'alwaysocc_occupancy',
                'street_lighting'
                ]
    # # # -----------option 1: Make schedule dataframe from schedule glm files ---------------------
    # # for sch in appliance_sch:
    # #     log.info("Reading and constructing 1 year dataframe for {} schedule".format(sch))
    # #     forecast_obj.make_dataframe_schedule(support_path + 'appliance_schedules.glm', sch)
    # #     forecast_obj.sch_df_dict[sch].to_csv('../../../dsot_data/schedule_df/' + sch + '.csv')
    # # for sch in wh_sch:
    # #     log.info("Reading and constructing 1 year dataframe for {} schedule".format(sch))
    # #     forecast_obj.make_dataframe_schedule(support_path + 'water_and_setpoint_schedule_v5.glm', sch)
    # #     forecast_obj.sch_df_dict[sch].to_csv('../../../dsot_data/schedule_df/' + sch + '.csv')
    # # for sch in comm_sch:
    # #     log.info("Reading and constructing 1 year dataframe for {} schedule".format(sch))
    # #     forecast_obj.make_dataframe_schedule(support_path + 'commercial_schedules.glm', sch)
    # #     forecast_obj.sch_df_dict[sch].to_csv('../../../dsot_data/schedule_df/' + sch + '.csv')
    #
    # # # -----------option 2: Read schedule dataframe from stored metadata and make index as datetime -------
    for sch in appliance_sch + wh_sch + comm_sch:
        forecast_obj.sch_df_dict[sch] = pd.read_csv('../../../usecase_data/schedule_df/' + sch + '.csv', index_col=0)
        forecast_obj.sch_df_dict[sch].index = pd.to_datetime(forecast_obj.sch_df_dict[sch].index)
    # # create a dataframe for constant schedule with all entries as 1.0. Copy it from any other dataframe
    forecast_obj.sch_df_dict['constant'] = forecast_obj.sch_df_dict['responsive_loads'].copy(deep=True)
    forecast_obj.sch_df_dict['constant']['data'] = 1.0

    market_keys = list(config['markets'].keys())
    for key in market_keys:
        if 'DSO' in key:
            dso_config = config['markets'][key]
            dso_name = key
            dso_market_obj = DSOMarket(dso_config, dso_name)

            # check the unit of the market
            dso_unit = config['markets'][key]['unit']
            dso_full_metrics = config['markets'][key]['full_metrics_detail']  # True for full

            # Update the supply curves for the wholesale. Only once as this will define a curve per day
            # might need to play around with the curve a,b,c here but for now let's run with the defaults
            dso_market_obj.update_wholesale_node_curve()

            # map topics
            # topic_map['gld_load'] = [dso_market_obj.set_total_load]
            # adding MG_load as net consumption for MG
            topic_map['MG_load'] = [dso_market_obj.set_total_load]
            if with_market:
                topic_map['ind_rt_load'] = [dso_market_obj.set_ind_load]
                topic_map['ind_load_history'] = [dso_market_obj.set_ind_load_da]
            else:
                topic_map['ref_rt_load'] = [dso_market_obj.set_ref_load]
                topic_map['ref_load_history'] = [dso_market_obj.set_ref_load_da]
            topic_map['lmp_da'] = [dso_market_obj.set_lmp_da]
            topic_map['lmp_rt'] = [dso_market_obj.set_lmp_rt]
            topic_map['cleared_q_da'] = [dso_market_obj.set_cleared_q_da]
            topic_map['cleared_q_rt'] = [dso_market_obj.set_cleared_q_rt]
            log.info('instantiated DSO market agent')

        if 'Retail' in key:
            retail_config = config['markets'][key]
            retail_name = key
            retail_market_obj = RetailMarket(retail_config, retail_name)
            if with_market == 0:
                retail_market_obj.basecase = True
            else:
                retail_market_obj.basecase = False
            retail_period_da = config['markets'][key]['period_da']
            retail_period_rt = config['markets'][key]['period_rt']

            # check the unit of the market
            retail_unit = config['markets'][key]['unit']
            retail_full_metrics = config['markets'][key]['full_metrics_detail']  # True for full
            log.info('instantiated Retail market agent')

    # instantiate the HVAC controller objects and map their FNCS inputs
    hvac_agent_objs = {}
    hvac_keys = list(config['hvacs'].keys())
    for key in hvac_keys:
        row = config['hvacs'][key]
        gld_row = config_glm['houses'][key]
        hvac_agent_objs[key] = HVACDSOT(row, gld_row, key, 11, current_time, solver)

        weather_topic = config_glm['climate']['name']
        if weather_topic + '#TempForecast' not in topic_map.keys():
            topic_map[weather_topic + '#TempForecast'] = [hvac_agent_objs[key].set_temperature_forecast]
        else:
            topic_map[weather_topic + '#TempForecast'].append(hvac_agent_objs[key].set_temperature_forecast)

        if weather_topic + '#Temperature' not in topic_map.keys():
            topic_map[weather_topic + '#Temperature'] = [hvac_agent_objs[key].set_temperature]
        else:
            topic_map[weather_topic + '#Temperature'].append(hvac_agent_objs[key].set_temperature)

        if weather_topic + '#Humidity' not in topic_map.keys():
            topic_map[weather_topic + '#Humidity'] = [hvac_agent_objs[key].set_humidity]
        else:
            topic_map[weather_topic + '#Humidity'].append(hvac_agent_objs[key].set_humidity)

        if weather_topic + '#HumidityForecast' not in topic_map.keys():
            topic_map[weather_topic + '#HumidityForecast'] = [hvac_agent_objs[key].set_humidity_forecast]
        else:
            topic_map[weather_topic + '#HumidityForecast'].append(hvac_agent_objs[key].set_humidity_forecast)

        if weather_topic + '#SolarDirect' not in topic_map.keys():
            topic_map[weather_topic + '#SolarDirect'] = [hvac_agent_objs[key].set_solar_direct]
        else:
            topic_map[weather_topic + '#SolarDirect'].append(hvac_agent_objs[key].set_solar_direct)
        if weather_topic + '#SolarDiffuse' not in topic_map.keys():
            topic_map[weather_topic + '#SolarDiffuse'] = [hvac_agent_objs[key].set_solar_diffuse]
        else:
            topic_map[weather_topic + '#SolarDiffuse'].append(hvac_agent_objs[key].set_solar_diffuse)

        # map FNCS topics
        topic_map[key + '#Tair'] = [hvac_agent_objs[key].set_air_temp]
        topic_map[key + '#V1'] = [hvac_agent_objs[key].set_voltage]
        topic_map[key + '#HvacLoad'] = [hvac_agent_objs[key].set_hvac_load]
        topic_map[key + '#TotalLoad'] = [hvac_agent_objs[key].set_house_load]
        topic_map[key + '#On'] = [hvac_agent_objs[key].set_hvac_state]
        # topic_map[key + '#Demand'] = [hvac_agent_objs[key].set_hvac_demand]
        topic_map[key + '#whLoad'] = [hvac_agent_objs[key].set_wh_load]

    log.info('instantiated %s HVAC control agents' % (len(hvac_keys)))

    # instantiate the water heater controller objects and map their FNCS inputs
    water_heater_agent_objs = {}
    water_heater_keys = []
    house_keys = list(config_glm['houses'].keys())  # each house will have a water heater
    for key in house_keys:
        if 'wh_name' in config_glm['houses'][key].keys():
            try:
                wh_key = config_glm['houses'][key]['wh_name']
                water_heater_keys.append(wh_key)
                row = config['water_heaters'][wh_key]
                gld_row = config_glm['houses'][key]
                water_heater_agent_objs[key] = WaterHeaterDSOT(row, gld_row, key, 11, current_time, solver)

                # map FNCS topics
                topic_map[wh_key + '#LTTEMP'] = [water_heater_agent_objs[key].set_wh_lower_temperature]
                topic_map[wh_key + '#UTTEMP'] = [water_heater_agent_objs[key].set_wh_upper_temperature]
                topic_map[wh_key + '#LTState'] = [water_heater_agent_objs[key].set_wh_lower_state]
                topic_map[wh_key + '#UTState'] = [water_heater_agent_objs[key].set_wh_upper_state]
                topic_map[wh_key + '#WHLoad'] = [water_heater_agent_objs[key].set_wh_load]
                topic_map[wh_key + '#WDRATE'] = [water_heater_agent_objs[key].set_wh_wd_rate_val]
            except KeyError as e:
                log.info('Error {}, wh_name in key={}'.format(e, key))
    log.info('instantiated %s water heater control agents' % (len(water_heater_keys)))

    # instantiate the Battery controller objects and map their FNCS inputs
    battery_agent_objs = {}
    battery_keys = list(config['batteries'].keys())
    for key in battery_keys:
        row = config['batteries'][key]
        gld_row = config_glm['inverters'][key]
        battery_agent_objs[key] = BatteryDSOT(row, gld_row, key, 11, current_time, solver)

        # map FNCS topics
        topic_map[key + '#SOC'] = [battery_agent_objs[key].set_battery_SOC]
    log.info('instantiated %s Battery control agents' % (len(battery_keys)))

    site_dictionary = config['site_agent']
    site_da_meter = []
    site_da_status = []
    for key, obj in site_dictionary.items():
        site_da_meter.append(key)
        site_da_status.append(site_dictionary[key]['participating'])
    log.info('instantiated site meter name and participating status')

    # adding the metrics collector object
    write_metrics = (config['MetricsInterval'] > 0)
    if write_metrics:
        write_h5 = (config['MetricsType'] == 'h5')
        collector = MetricsCollector.factory(start_time=start_time, write_hdf5=write_h5)

        # dso_86400 = MetricsStore(
        #     name_units_pairs=[
        #         ('curve_a', ['a'] * 24),
        #         ('curve_b', ['b'] * 24),
        #         ('curve_c', ['c'] * 24),
        #         ('curve_ws_node_quantities', [[dso_unit] * dso_market_obj.num_samples] * 24),
        #         ('curve_ws_node_prices', [['$/' + dso_unit] * dso_market_obj.num_samples] * 24),
        #         ('Feqa_T', ['/hour']),  # TODO: double-check that this is correct
        #     ],
        #     file_string='dso_market_{}_86400'.format(metrics_root),
        #     collector=collector,
        # )

        dso_3600 = MetricsStore(
            name_units_pairs=[
                ('curve_dso_da_quantities', [[dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
                ('curve_dso_da_prices', [['$/' + dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
                ('trial_cleared_price_da', ['$/' + dso_unit] * dso_market_obj.windowLength),
                ('trial_cleared_quantity_da', [dso_unit] * dso_market_obj.windowLength),
                ('trial_clear_type_da',
                 ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * dso_market_obj.windowLength),
            ],
            file_string='dso_market_{}_3600'.format(metrics_root),
            collector=collector,
        )
        #
        dso_300 = MetricsStore(
            name_units_pairs=[
                ('curve_dso_rt_quantities', [dso_unit] * dso_market_obj.num_samples),
                ('curve_dso_rt_prices', ['$/' + dso_unit] * dso_market_obj.num_samples),
                ('cleared_price_rt', '$/' + dso_unit),
                ('cleared_quantity_rt', dso_unit),
                ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
            ],
            file_string='dso_market_{}_300'.format(metrics_root),
            collector=collector,
        )
        #                 'dso_rt_gld_load': {'units': load_recording_unit, 'index': 5},
        #                 'dso_rt_industrial_load': {'units': load_recording_unit, 'index': 6},
        #                 'dso_rt_ercot_load': {'units': load_recording_unit, 'index': 7}}

        if retail_full_metrics:
            retail_3600 = MetricsStore(
                name_units_pairs=[
                    ('curve_buyer_da_quantities',
                     [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('curve_buyer_da_prices',
                     [['$/' + retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('curve_seller_da_quantities',
                     [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('curve_seller_da_prices',
                     [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('cleared_price_da', ['$/' + retail_unit] * retail_market_obj.windowLength),
                    ('cleared_quantity_da', [retail_unit] * retail_market_obj.windowLength),
                    ('clear_type_da',
                     ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * retail_market_obj.windowLength),
                    ('congestion_surcharge_DA', ['$/' + retail_unit] * retail_market_obj.windowLength),
                ],
                file_string='retail_market_{}_3600'.format(metrics_root),
                collector=collector,
            )
        else:
            retail_3600 = MetricsStore(
                name_units_pairs=[
                    ('cleared_price_da', ['$/' + retail_unit] * retail_market_obj.windowLength),
                    ('cleared_quantity_da', [retail_unit] * retail_market_obj.windowLength),
                    ('clear_type_da',
                     ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * retail_market_obj.windowLength),
                    ('congestion_surcharge_DA', ['$/' + retail_unit] * retail_market_obj.windowLength),
                ],
                file_string='retail_market_{}_3600'.format(metrics_root),
                collector=collector,
            )

        # retail_site_3600 = MetricsStore(
        #     name_units_pairs=[
        #         ('meters', ['meterName'] * len(site_da_meter)),
        #         ('status', ['[0..1]=[PARTICIPATION,NONPARTICIPATION]'] * len(site_da_meter)),
        #         ('non_transactive_hvac', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #         ('non_transactive_wh', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #         ('non_transactive_zip', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #         ('non_transactive_quantities', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #         ('transactive_wh', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #         ('transactive_hvac', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #         ('transactive_batt', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #         ('transactive_cleared_quantity', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
        #     ],
        #     file_string='retail_site_{}_3600'.format(metrics_root),
        #     collector=collector,
        # )

        # retail_site_3600 = MetricsStore(
        #     name_units_pairs=[
        #         ('meters', ['meterName'] * len(site_da_meter)),
        #         ('status', ['[0..1]=[PARTICIPATION,NONPARTICIPATION]'] * len(site_da_meter)),
        #         ('site_quantities', [[retail_unit] * int(dso_market_obj.windowLength / 2)] * len(site_da_meter)),
        #     ],
        #     file_string='retail_site_{}_3600'.format(metrics_root),
        #     collector=collector,
        # )

        if retail_full_metrics:
            retail_300 = MetricsStore(
                name_units_pairs=[
                    ('curve_buyer_rt_quantities', [retail_unit] * retail_market_obj.windowLength),
                    ('curve_buyer_rt_prices', ['$/' + retail_unit] * retail_market_obj.windowLength),
                    ('curve_seller_rt_quantities', [retail_unit] * retail_market_obj.windowLength),
                    ('curve_seller_rt_prices', ['$/' + retail_unit] * retail_market_obj.windowLength),
                    ('cleared_price_rt', '$/' + retail_unit),
                    ('cleared_quantity_rt', retail_unit),
                    ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
                    ('congestion_surcharge_RT', '$/' + retail_unit),
                ],
                file_string='retail_market_{}_300'.format(metrics_root),
                collector=collector,
            )
        else:
            retail_300 = MetricsStore(
                name_units_pairs=[
                    ('cleared_price_rt', '$/' + retail_unit),
                    ('cleared_quantity_rt', retail_unit),
                    ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
                    ('congestion_surcharge_RT', '$/' + retail_unit),
                ],
                file_string='retail_market_{}_300'.format(metrics_root),
                collector=collector,
            )

        hvac_3600 = MetricsStore(
            name_units_pairs=[
                ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
            ],
            file_string='hvac_agent_{}_3600'.format(metrics_root),
            collector=collector,
        )

        hvac_300 = MetricsStore(
            name_units_pairs=[
                ('cooling_setpoint', 'F'),
                ('heating_setpoint', 'F'),
                ('cooling_basepoint', 'F'),
                ('heating_basepoint', 'F'),
                ('agent_room_temperature', 'F'),
                ('GLD_air_temperature', 'F'),
                ('outdoor_temperature', 'F'),
                ('RT_bid_quantity', 'kW'),
                ('DA_bid_quantity', '$'),
                ('cleared_price', '$'),
                ('agent_RT_price', '$'),
            ],
            file_string='hvac_agent_{}_300'.format(metrics_root),
            collector=collector,
        )

        water_heater_3600 = MetricsStore(
            name_units_pairs=[
                ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
                # ('DAOptimizedQuantities', 'kWh'),
                # ('DAOptimizedSOHC', '%'),
            ],
            file_string='water_heater_agent_{}_3600'.format(metrics_root),
            collector=collector,
        )

        water_heater_300 = MetricsStore(
            name_units_pairs=[
                ('bid_four_point_rt', [[retail_unit, '$/' + retail_unit]] * 4),
                ('upper_tank_setpoint', 'F'),
                ('lower_tank_setpoint', 'F'),
                ('Energy_GLD', 'kWh'),
                ('SOHC_gld', 'kWh'),
                ('Waterdraw_gld', 'gpm'),
            ],
            file_string='water_heater_agent_{}_300'.format(metrics_root),
            collector=collector,
        )

        battery_3600 = MetricsStore(
            name_units_pairs=[
                ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
            ],
            file_string='battery_agent_{}_3600'.format(metrics_root),
            collector=collector,
        )

        battery_300 = MetricsStore(
            name_units_pairs=[
                ('bid_four_point_rt', [[retail_unit, '$/' + retail_unit]] * 4),
                ('inverter_p_setpoint', 'W'),
                ('inverter_q_setpoint', 'W'),
                ('battery_soc', '[0-1]'),
            ],
            file_string='battery_agent_{}_300'.format(metrics_root),
            collector=collector,
        )

    # initialize FNCS
    # fncs.initialize()

    # initialize HELICS
    fed, fed_name = register_federate(metrics_root + '.json')
    status = h.helicsFederateEnterInitializingMode(fed)
    status = h.helicsFederateEnterExecutingMode(fed)
    endkeys_count = h.helicsFederateGetEndpointCount(fed)
    endid = {}
    bid_info = {}
    for i in range(0, endkeys_count):
        endid["m{}".format(i)] = h.helicsFederateGetEndpointByIndex(fed, i)
        key = h.helicsEndpointGetName(endid["m{}".format(i)])
        [from_agent, to_agent, property] = key.split('/')
        if from_agent not in bid_info.keys():
            bid_info[from_agent] = {}
        if to_agent not in bid_info[from_agent].keys():
            bid_info[from_agent][to_agent] = {}
            bid_info[from_agent][to_agent]['DA'] = {}
            bid_info[from_agent][to_agent]['RT'] = {}
        if 'DA' in property:
            bid_info[from_agent][to_agent]['DA'][property] = np.zeros((dso_market_obj.windowLength)).tolist()
        if 'RT' in property:
            bid_info[from_agent][to_agent]['RT'][property] = 0

    dso_market_obj.market = {}
    dso_market_obj.market = bid_info

    # flag to determine if billing is to be set
    billing_set_defaults = True

    # interval for metrics recording
    # HACK: gld will be typically be on an (even) hour, so we will offset our frequency by 30 minutes (should be on the .5 hour)
    metrics_record_interval = 7200  # will actually be x2 after first round
    tnext_write_metrics_cnt = 1
    tnext_write_metrics = metrics_record_interval + 1800
    # interval for obtaining historical load data (ercot load for the basecase)
    historic_load_interval = 86400

    # for right now, check agent_dict.json for sure
    # retail_period_da = 3600
    # retail_period_rt = 900

    # specific tasks to do
    tnext_retail_bid_rt = retail_period_rt - 45 + retail_period_da * 1
    tnext_retail_bid_da = retail_period_da - 60
    tnext_dso_bid_rt = retail_period_rt - 15 + retail_period_da * 1
    tnext_dso_bid_da = retail_period_da - 30

    # tnext_dso_market_da = retail_period_da - 25
    # tnext_dso_market_rt = retail_period_rt - 25 + retail_period_da * 1

    tnext_wholesale_bid_rt = retail_period_rt - 30 + 86100  # just before a whole day
    tnext_wholesale_bid_da = 36000 - 30  # 10AM minus 30 secs
    tnext_wholesale_clear_rt = retail_period_rt + 86400  # at a whole day + period
    tnext_wholesale_clear_da = 50400  # 2PM
    tnext_dso_clear_rt = retail_period_rt + retail_period_da * 1
    tnext_dso_clear_da = retail_period_da
    tnext_retail_clear_da = retail_period_da
    tnext_retail_clear_rt = retail_period_rt + retail_period_da * 1
    tnext_retail_adjust_rt = retail_period_rt + retail_period_da * 1
    tnext_historic_load_da = 1
    tnext_water_heater_update = 65

    time_granted = 0  # is midnite always
    time_last = 0
    load_base = 0
    load_base_unadjusted = 0.0
    delta_load_forecast_error = 0.0
    load_base_hourly = 0.0
    load_diff = 0
    retail_cleared_quantity_diff_observed = 0.0
    retail_cleared_quantity_diff_applied = 0.0
    retail_cleared_quantity_RT = 0.0
    retail_cleared_quantity_RT_unadjusted = 0.0
    gld_load = []
    gld_load_rolling_mean = 0.0
    gld_load_scaled_mean = 0.0
    retail_day_ahead_diff_observed = 0.0
    timing(proc[0], False)

    timing(proc[1], True)
    Quanity_cleared_RT_previous = np.array([0, 0, 0])  ### For three agents
    while time_granted < simulation_duration:
        # determine the next HELICS time
        timing(proc[10], True)
        if with_market:
            # next_fncs_time = int(min([tnext_retail_bid_rt, tnext_retail_bid_da, tnext_dso_bid_rt, tnext_dso_bid_da,
            #                           tnext_wholesale_clear_rt, tnext_wholesale_clear_da, tnext_dso_clear_rt,
            #                           tnext_dso_clear_da, tnext_retail_clear_da, tnext_retail_clear_rt,
            #                           tnext_retail_adjust_rt, tnext_write_metrics, tnext_water_heater_update,
            #                           tnext_historic_load_da, simulation_duration]))

            next_fncs_time = int(
                min([tnext_retail_bid_rt, tnext_retail_bid_da, tnext_dso_bid_da, tnext_dso_bid_rt, tnext_dso_clear_rt,
                     tnext_retail_clear_rt, tnext_retail_adjust_rt, tnext_write_metrics, tnext_water_heater_update,
                     tnext_historic_load_da, simulation_duration]))

            while time_granted < next_fncs_time:
                time_granted = h.helicsFederateRequestTime(fed, next_fncs_time)
        else:
            time_granted = h.helicsFederateRequestTime(fed, simulation_duration)

        time_delta = time_granted - time_last
        time_last = time_granted
        timing(proc[10], False)

        current_time = current_time + timedelta(seconds=time_delta)
        day_of_week = current_time.weekday()
        hour_of_day = current_time.hour
        minute_of_hour = current_time.minute

        log.info('current time -> ' + str(current_time))
        log.debug('\t day of week -> ' + str(day_of_week))
        log.debug('\t hour of day -> ' + str(hour_of_day))
        log.debug('\t minute of hour -> ' + str(minute_of_hour))

        # portion that sets the initial billing information. Runs only once!
        if billing_set_defaults:
            for key, obj in hvac_agent_objs.items():
                pub_b = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/bill_mode'))
                status = h.helicsPublicationPublishString(pub_b, 'HOURLY')
                pub_m = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/monthly_fee'))
                status = h.helicsPublicationPublishDouble(pub_m, 0.0)
                pub_t = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/thermostat_deadband'))
                status = h.helicsPublicationPublishDouble(pub_t, obj.deadband)
            billing_set_defaults = False

        # portion that sets the time-of-day thermostat schedule for HVACs
        for key, obj in hvac_agent_objs.items():
            obj.change_solargain(minute_of_hour, hour_of_day,
                                 day_of_week)  # need to be replaced by Qi and Qs calculations
            if obj.change_basepoint(minute_of_hour, hour_of_day, day_of_week, 11, current_time):
                # publish setpoint for participating and basepoint for non-participating
                if obj.participating and with_market:
                    pub_csp = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/cooling_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_csp, obj.cooling_setpoint)
                    pub_hsp = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/heating_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_hsp, obj.heating_setpoint)
                else:
                    pub_csp = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/cooling_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_csp, obj.basepoint_cooling)
                    pub_hsp = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/heating_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_hsp, obj.basepoint_heating)
                # else:
                #    continue

        # portion that updates the time in the water heater agents
        for key, obj in water_heater_agent_objs.items():
            obj.set_time(hour_of_day, minute_of_hour)

        # portion that gets current events from HELICS.
        subkeys_count = h.helicsFederateGetInputCount(fed)
        subid = {}
        for i in range(0, subkeys_count):
            subid["m{}".format(i)] = h.helicsFederateGetInputByIndex(fed, i)
            topic = h.helicsInputGetInfo(subid["m{}".format(i)])
            if topic in topic_map:
                for itopic in range(len(topic_map[topic])):
                    value = h.helicsInputGetString(subid["m{}".format(i)])
                    log.debug(topic + ' -> ' + value)
                    if any(x in topic for x in ['#Tair', '#SOC', '#LTTEMP', '#UTTEMP']):
                        # these function has 2 additional inputs for logging
                        topic_map[topic][itopic](value, 11, current_time)
                    else:
                        # calls function to update the value in object. For details see topicMap
                        topic_map[topic][itopic](value)
            else:
                # As we have modified gld_load to be MG_load ## Market_status is for temporary fix
                if (topic != 'gld_load') and (topic != 'Market_status'):
                    log.warning('Unknown topic received from HELICS ({:s}), dropping it'.format(topic))

        # portion that gets current events from FNCS
        # events = fncs.get_events()
        # for topic in events:
        #     if topic in topic_map:
        #         for itopic in range(len(topic_map[topic])):
        #             value = fncs.get_value(topic)
        #             log.debug(topic + ' -> ' + value)
        #             if any(x in topic for x in ['#Tair','#SOC','#LTTEMP','#UTTEMP']):
        #                 # these function has 2 additional inputs for logging
        #                 topic_map[topic][itopic](value, 11, current_time)
        #             else:
        #                 topic_map[topic][itopic](value)  # calls function to update the value in object. For details see topicMap
        #     else:
        #         log.warning('Unknown topic received from FNCS ({:s}), dropping it'.format(topic))

        # load_player sent this in MW, whereas the substation does everything in kW
        if retail_market_obj.basecase:
            try:
                forecast_obj.base_run_load = np.array(dso_market_obj.ref_load_da) * 1000
            except:
                if tnext_historic_load_da == 1:
                    forecast_obj.base_run_load = np.array(forecast_obj.base_run_load) * dso_market_obj.DSO_Q_max

        # if we are running with markets perform certain control actions

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Historical Load Update -------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_historic_load_da:
            if retail_market_obj.basecase:
                forecast_load = forecast_obj.base_run_load
                dso_market_obj.DSO_Q_max = max(forecast_load)
                retail_market_obj.Q_max = max(forecast_load)

            # Update the supply curves for the wholesale. Only once as this will define a curve per day
            # might need to play around with the curve a,b,c here but for now let's run with the defaults
            dso_market_obj.update_wholesale_node_curve()
            tnext_historic_load_da += historic_load_interval

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Water heater update -------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_water_heater_update:
            # This will ensure that the water heaters can detect state changes at one minute intervals
            tnext_water_heater_update += 60

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Retail bidding ------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_retail_bid_rt:
            log.info("-- retail real-time bidding --")
            # clean the real-time bids
            retail_market_obj.clean_bids_RT()
            # since the current time is 45 seconds ahead of retail bidding time
            current_retail_time = current_time + timedelta(0, 45)  # timedelta(days, seconds)
            # store real-time distribution loads
            gld_load.append(dso_market_obj.total_load)
            if len(gld_load) == 12:
                gld_load.pop(-12)

            gld_load_rolling_mean = np.array(gld_load).mean()
            # gld_load_rolling_mean = np.array(gld_load)
            # HVAC bidding
            timing(proc[3], True)
            for key, obj in hvac_agent_objs.items():
                if obj.participating and with_market:
                    # set the nominal solargain
                    obj.solar_heatgain = obj.get_solargain(config_glm['climate'], current_retail_time)
                    # formulate the real-time bid
                    bid = obj.formulate_bid_rt(11, current_time)
                    # add real-time bid to the retail market
                    retail_market_obj.curve_aggregator_RT('Buyer', bid, obj.name)
            timing(proc[3], False)

            # Water heater bidding
            timing(proc[4], True)
            for key, obj in water_heater_agent_objs.items():
                if obj.participating and with_market:
                    # formulate the real-time bid
                    bid = obj.formulate_bid_rt(11, current_time)
                    # add real-time bid to the retail market
                    retail_market_obj.curve_aggregator_RT('Buyer', bid, obj.name)
            timing(proc[4], False)

            # Battery bidding
            timing(proc[2], True)
            for key, obj in battery_agent_objs.items():
                if obj.participating and with_market:
                    # formulate the real-time bid
                    bid = obj.formulate_bid_rt()
                    # add real-time bid to the retail market
                    retail_market_obj.curve_aggregator_RT('Buyer', bid, obj.name)
            timing(proc[2], False)

            log.info('<-------- Real Time Bid Formulation Started -------> ')

            if time_granted < (
                    retail_period_rt + retail_period_da * 1):  # first real-time clearing has not been observed
                retail_cleared_quantity_diff_applied = 0.0
            else:
                retail_cleared_quantity_diff_applied = retail_cleared_quantity_diff_observed + retail_day_ahead_diff_observed

            log.info("Real-time bid base from previous RT --> " + str(load_base / 1000.0) + "MW")

            # interpolate real time load_base to fix stair step effect from the hourly player
            load_base += load_diff
            log.info("Real-time bid base after diff --> " + str(load_base / 1000.0) + "MW")

            load_base -= retail_cleared_quantity_diff_applied
            # load_base -= 0.0
            log.info("Real-time bid after correction applied --> " + str(load_base / 1000.0) + "MW")

            load_base_unadjusted += load_diff
            log.info("Real-time bid following previous method       --> " + str(load_base_unadjusted / 1000.0) + "MW")
            log.info("Real-time bid day-ahead diff                  --> " + str(load_diff / 1000.0) + "MW")
            log.info("Hour 0 day-ahead diff applied                 --> " + str(
                retail_day_ahead_diff_observed / 1000.0) + "MW")
            log.info("Real-time diff applied                        --> " + str(
                retail_cleared_quantity_diff_observed / 1000.0) + "MW")
            log.info('<-------- Real Time Bid Formulation Done -------> ')

            if abs(retail_day_ahead_diff_observed) > 0.0:  # for the first step of real-time bid, we have recieved the correction from the zeroth hour day-ahead, now we set it to zero so it doesn't keep adding
                retail_day_ahead_diff_observed = 0.0

            # log.info("Real-time scaled flexible bid min, max " + str(min(retail_market_obj.curve_buyer_RT.quantities)) + " , " + str(max(retail_market_obj.curve_buyer_RT.quantities)))

            retail_market_obj.curve_aggregator_RT('Buyer',
                                                  [[load_base, retail_market_obj.price_cap],
                                                   [load_base, 0]], 'uncontrollable load')

            # log.info("Real-time total bid min, max " + str(min(retail_market_obj.curve_buyer_RT.quantities)) + " , " + str(max(retail_market_obj.curve_buyer_RT.quantities)))

            # plt.plot(dso_market_obj.curve_ws_node[day_of_week][hour_of_day].quantities,dso_market_obj.curve_ws_node[day_of_week][hour_of_day].prices)
            # plt.plot(retail_market_obj.curve_buyer_RT.quantities,retail_market_obj.curve_buyer_RT.prices)

            tnext_retail_bid_rt += retail_period_rt

        if time_granted >= tnext_retail_bid_da:
            # resetting Qmax from the previous iterations
            dso_market_obj.DSO_Q_max = retail_market_obj.Q_max
            dso_market_obj.update_wholesale_node_curve()
            forecast_rt = 0
            log.info("-- retail day-ahead bidding --")
            # clean the day-ahead bids
            retail_market_obj.clean_bids_DA()

            P_age_DA = list()

            uncntrl_hvac = []  # list to store uncontrolled hvac loads
            zip_loads = []  # list to store uncontrolled zip loads

            # since the current time is 60 seconds ahead of the actual day-ahead bidding hour,
            # we need to get the day-ahead bidding time as forecast start time
            forecast_start_time = current_time + timedelta(0, 60)  # (days, seconds)
            # Estimating nominal solargain forecast, it is same for all houses
            forecast_solargain = forecast_obj.get_solar_gain_forecast(config_glm['climate'], forecast_start_time)
            site_da_wh_uncntrl = np.zeros((len(site_da_meter), 48), dtype=float)
            site_da_zip_loads = np.zeros((len(site_da_meter), 48), dtype=float)
            site_da_hvac_uncntrl = np.zeros((len(site_da_meter), 48), dtype=float)

            # HVAC bidding
            timing(proc[5], True)
            for key, obj in hvac_agent_objs.items():
                site_id = site_da_meter.index(config_glm['houses'][key]['billingmeter_id'])

                # TODO: Estimate solar and internal gain
                # update forecast quantities
                obj.set_solargain_forecast(forecast_solargain)
                skew_scalar = {'zip_skew': int(config_glm['houses'][key]['zip_skew']),
                               'zip_scalar': config_glm['houses'][key]['zip_scalar'],
                               'zip_heatgain_fraction': config_glm['houses'][key]['zip_heatgain_fraction'],
                               'zip_power_fraction': config_glm['houses'][key]['zip_power_fraction'],
                               'zip_power_pf': config_glm['houses'][key]['zip_power_pf']
                               }
                forecast_ziploads, forecast_internalgain = \
                    forecast_obj.get_internal_gain_forecast(skew_scalar, forecast_start_time)
                obj.set_internalgain_forecast(forecast_internalgain)
                zip_loads.append(forecast_ziploads)
                if obj.participating and with_market:
                    obj.DA_model_parameters(minute_of_hour, hour_of_day, day_of_week)
                    P_age_DA.append(obj)
                    # formulate the day-ahead bid
                    # include time in DA bid call so HVAC agent can use schedule info
                    # bid = obj.formulate_bid_da(minute_of_hour, hour_of_day, day_of_week)
                    # add day-ahead bid to the retail market
                    # retail_market_obj.curve_aggregator_DA('Buyer', bid, obj.name)
                    site_da_status.append(1)
                else:
                    # if not participating, use hvac model equation without optimization to get forecast hvac load
                    temp = obj.get_uncntrl_hvac_load(minute_of_hour, hour_of_day, day_of_week)
                    # if opt=False, it wont run optimization and will estimate the inflexible load
                    uncntrl_hvac.append(temp)
                    site_da_hvac_uncntrl[site_id] += temp
                site_da_zip_loads[site_id] += forecast_ziploads
            timing(proc[5], False)
            #            print('uncontrolled hvac ***')
            #            print(uncntrl_hvac)

            # Water heater bidding
            timing(proc[6], True)
            uncntrl_wh = []  # list to store uncontrolled wh load
            for key, obj in water_heater_agent_objs.items():
                site_id = site_da_meter.index(config_glm['houses'][key]['billingmeter_id'])

                skew_scalar = {'wh_skew': int(config_glm['houses'][key]['wh_skew']),
                               'wh_scalar': config_glm['houses'][key]['wh_scalar'],
                               'wh_schedule_name': config_glm['houses'][key]['wh_schedule_name'],
                               }  #### update from to get the wh scalar
                # to get the forecast from forecasting agent
                forecast_waterdrawSCH = forecast_obj.get_waterdraw_forecast(skew_scalar, forecast_start_time)
                # update forecast quantities
                obj.set_forecasted_schedule(forecast_waterdrawSCH)
                if obj.participating and with_market:
                    P_age_DA.append(obj)
                    # formulate the day-ahead bid
                    # bid = obj.formulate_bid_da()
                    # add day-ahead bid to the retail market
                    # retail_market_obj.curve_aggregator_DA('Buyer', bid, obj.name)
                else:
                    # get waterheater base load through direct equations without optimization
                    temp1 = obj.get_uncntrl_wh_load()
                    uncntrl_wh.append(temp1)
                    site_da_wh_uncntrl[site_id] += temp1
            timing(proc[6], False)
            #            print('uncontrolled wh ***')
            #            print(uncntrl_wh)

            #            print('uncontrolled zip ***')
            #            print(zip_loads)

            # sum all uncontrollable load
            sum_uncntrl = np.array(zip_loads).sum(axis=0) + \
                          np.array(uncntrl_wh).sum(axis=0) + \
                          np.array(uncntrl_hvac).sum(axis=0)
            site_da_quantities = sum_uncntrl.tolist()
            site_da_total_quantities_uncntrl = site_da_wh_uncntrl + site_da_hvac_uncntrl + site_da_zip_loads
            site_da_total_quantities_uncntrl = site_da_total_quantities_uncntrl.tolist()
            if site_da_quantities == 0.0:
                site_da_quantities = [0.0] * retail_market_obj.windowLength
            # print('uncontrolled total ***')
            # print(site_da_quantities)
            # print('uncontrolled total site load ***')
            # print(site_da_total_quantities_uncntrl)
            # Battery bidding
            # for key, obj in battery_agent_objs.items():
            #     if obj.participating and with_market:
            #         P_age_DA.append(obj)
            #        # P_age_DA_id.append(obj.name)
            #        # formulate the day-ahead bid
            #         quantity = obj.DA_optimal_quantities()
            #         obj.optimized_Quantity = quantity
            #         bid = obj.formulate_bid_da()
            #        # add day-ahead bid to the retail market
            # #         retail_market_obj.curve_aggregator_DA('Buyer', bid, obj.name)
            #
            # formulating bid DA with multiprocessing library
            for key, obj in battery_agent_objs.items():
                if obj.participating and with_market:
                    P_age_DA.append(obj)
            # created pyomo models in serial, but solves in parallel (sending only the pyomo model, rather than whole batter object to the processes)
            timing('batt_opt', True)
            results = parallel(delayed(worker)(p) for p in P_age_DA)
            timing('batt_opt', False)
            print('Objects Parallelized (over {} processes) --> {}'.format(NUM_CORE, len(P_age_DA)))
            # add participating agents to day-ahead bid to the retail market
            for i, (res, p_age) in enumerate(zip(results, P_age_DA)):  # range(len(P_age_DA)):
                timing(p_age.__class__.__name__, True)
                # passing the optimization output to the agent
                if p_age.__class__.__name__ == "HVACDSOT":
                    p_age.optimized_Quantity = res[0][:]
                    p_age.temp_room = res[1][:]
                else:
                    p_age.optimized_Quantity = res[:]
                # formulate the day-ahead bid
                bid = p_age.formulate_bid_da()
                timing(p_age.__class__.__name__, False)
                retail_market_obj.curve_aggregator_DA('Buyer', bid, p_age.name)

            # add the uncontrollable load
            uncontrollable_load_bid_da = [[[0], [0]]] * retail_market_obj.windowLength
            # uncontrollable_load_bid_ind_da = [[[0], [0]]] * retail_market_obj.windowLength

            if retail_market_obj.basecase:
                # here you got things from basecase so roll it please and add error
                forecast_load = np.roll(forecast_load, -1)
                forecast_load_error = forecast_load + 0.05 * forecast_load * np.random.normal()  # adding error
            else:
                # getting industrial Load now
                # no industrial load added #Monish
                # forecast_load_ind = dso_market_obj.ind_load_da
                # forecast_load_ind = forecast_load_ind.tolist()

                # forecast_load_ind = forecast_obj.get_substation_unresponsive_industrial_load_forecast(dso_market_obj.ind_load_da)

                # no rolling needed because stuff is in the right spot and doesn't need error
                # OPTION-1 Uses internal uncontrollable load forecast by site agent
                # forecast_load_uncontrollable = deepcopy(np.array(site_da_quantities)*(dso_market_obj.num_of_customers*dso_market_obj.customer_count_mix_residential/dso_market_obj.number_of_gld_homes))
                forecast_load_uncontrollable = deepcopy(np.array(site_da_quantities))
                # OPTION-2 Uses fixed peak load value --- has proven convergence
                # forecast_load = forecast_obj.get_substation_unresponsive_load_forecast(800)
                # forecast_load_error = forecast_load_uncontrollable + forecast_load_ind # no error
                forecast_load_error = forecast_load_uncontrollable

            # log.info("Hour 10 uncontrollable before scale min, max " + str(min(site_da_quantities[10]))+ ", " + str(max(site_da_quantities[10])))
            # log.info("Hour 10 uncontrollable after scale min, max " + str(min(forecast_load_uncontrollable[10]))+ ", " + str(max(forecast_load_uncontrollable[10])))
            # log.info("Hour 0 industrial load  scale min, max " + str(min(forecast_load_ind[0]))+ ", " + str(max(forecast_load_ind[0])))
            # log.info("Hour 10 industrial load  scale min, max " + str(min(forecast_load_ind[10]))+ ", " + str(max(forecast_load_ind[10])))

            # second hour day-ahead onwards we have adjusted "base bid" from our rt correction procedure (see retail_bid_rt), so we don't change that
            # What we still want is:
            # 1) the difference the day-ahead bid sees in the hour "load_diff"
            # 2) and if there exists any day-ahead error in the uncontrollable load forecast and scaled gld load
            if time_granted >= (retail_period_da + retail_period_rt):
                # retail_day_ahead_diff_observed = forecast_load_uncontrollable[0] - gld_load_scaled_mean
                retail_day_ahead_diff_observed = 0.0
                load_diff = (forecast_load_error[1] - forecast_load_error[0]) / 12
                # load_base = forecast_load_error[0]
                load_base_unadjusted = forecast_load_error[0]
                if len(P_age_DA) > 0:
                    delta_load_forecast_error = forecast_load_error - np.array(forecast_load_error).mean()
                    # load_base_hourly = load_base + delta_load_forecast_error
                    load_base_hourly = forecast_load_error  ## added by Monish
                else:
                    load_base_hourly = forecast_load_error
                # forecast_load_error[0] = load_base
                # correct the zeroth hour uncontrollable bid which is going to be passed to the real-time
                # this is because at the hour mark the load_base changes which is not reflected in the adjustment done prior to that hour
                # also notice that we are not subtracting the industrial load because in realtime we add it back.
            else:
                retail_day_ahead_diff_observed = 0.0
                load_diff = (forecast_load_error[1] - forecast_load_error[0]) / 12
                load_base = forecast_load_error[0]
                load_base_unadjusted = forecast_load_error[0]
                load_base_hourly = forecast_load_error

            for idx in range(retail_market_obj.windowLength):
                uncontrollable_load_bid_da[idx] = [[load_base_hourly[idx], retail_market_obj.price_cap],
                                                   [load_base_hourly[idx], 0]]

            retail_market_obj.curve_aggregator_DA('Buyer', uncontrollable_load_bid_da, 'uncontrollable load')

            #### Extract Sample Bids into Jsons for Debugging #####
            # sample_bid_da = {}
            # for key in retail_market_obj.curve_buyer_DA:
            #     sample_bid_da[key] = {}
            #     sample_bid_da[key]['prices'] = {}
            #     sample_bid_da[key]['quantities'] = {}
            #     sample_bid_da[key]['prices'] = retail_market_obj.curve_buyer_DA[key].prices.tolist()
            #     sample_bid_da[key]['quantities'] = retail_market_obj.curve_buyer_DA[key].quantities.tolist()
            # json_file = json.dumps(sample_bid_da, indent=4, separators=(',', ': '))
            # fp = open('sample_bid_DA.json', 'w')
            # print(json_file, file=fp)
            # fp.close()
            ######  Plot Bids for check #####
            # hour_plt  = 1
            # fig, ax = plt.subplots()
            # ax.plot(retail_market_obj.curve_buyer_DA[hour_plt].quantities, retail_market_obj.curve_buyer_DA[hour_plt].prices)

            # log.info("Scale " + str((dso_market_obj.num_of_customers*dso_market_obj.customer_count_mix_residential/dso_market_obj.number_of_gld_homes)))
            # log.info("Hour 10 total quantity after scale min, max " + str(min(retail_market_obj.curve_buyer_DA[10].quantities))+ ", " + str(max(retail_market_obj.curve_buyer_DA[10].quantities)))
            # log.info("Hour 0 total quantity after scale min, max " + str(min(retail_market_obj.curve_buyer_DA[0].quantities))+ ", " + str(max(retail_market_obj.curve_buyer_DA[0].quantities)))

            tnext_retail_bid_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ DSO bidding ---------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_dso_bid_rt:
            log.info("-- dso real-time bidding --")
            dso_market_obj.cleared_q_rt = dso_market_obj.trial_cleared_quantity_RT
            dso_market_obj.clean_bids_RT()
            dso_market_obj.curve_aggregator_DSO_RT(retail_market_obj.curve_buyer_RT, Q_max=dso_market_obj.DSO_Q_max)

            # ----------------------------------------------------------------------------------------------------
            # ------------------------------------ Consensus Market RT -------------------------------------------
            # ----------------------------------------------------------------------------------------------------
            log.info("-- dso real-time market --")
            time_to_complete_market_RT = time_granted + 15
            dso_market_obj, time_granted = consensus.Consenus_dist_RT(dso_market_obj, fed, time_granted,
                                                                      time_to_complete_market_RT)
            tnext_dso_bid_rt += retail_period_rt

        if time_granted >= tnext_dso_bid_da:
            log.info("-- dso day-ahead bidding --")
            dso_market_obj.cleared_q_da = dso_market_obj.trial_cleared_quantity_DA
            dso_market_obj.clean_bids_DA()
            dso_market_obj.curve_aggregator_DSO_DA(retail_market_obj.curve_buyer_DA, Q_max=dso_market_obj.DSO_Q_max)
            # ----------------------------------------------------------------------------------------------------
            # ------------------------------------ Consensus Market DA -------------------------------------------
            # ----------------------------------------------------------------------------------------------------
            log.info("-- dso day-ahead market --")
            time_to_complete_market_DA = time_granted + 15
            dso_market_obj, time_granted = consensus.Consenus_dist_DA(dso_market_obj, 24, fed, time_granted,
                                                                      time_to_complete_market_DA)

            tnext_dso_bid_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ DSO clearing --------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_dso_clear_rt:
            log.info("-- dso real-time clearing --")

            # # Getting current cleared data from Substation via HELICS.
            # endpoint_count = h.helicsFederateGetEndpointCount(fed)
            # endid = {}
            # for i in range(0, endpoint_count):
            #     endid["m{}".format(i)] = h.helicsFederateGetEndpointByIndex(fed, i)
            #     if h.helicsEndpointHasMessage(endid["m{}".format(i)]):
            #         end_key = h.helicsEndpointGetName(endid["m{}".format(i)])
            #         property = end_key.split(fed_name + '/')[1].split('/')[1]
            #         if "cleared_price_RT" in property:
            #             dso_market_obj.Pwclear_RT = json.loads(h.helicsEndpointGetMessage(endid["m{}".format(i)]).data)
            #         elif "cleared_quantity_RT" in property:
            #             dso_market_obj.trial_cleared_quantity_RT = json.loads(h.helicsEndpointGetMessage(endid["m{}".format(i)]).data)
            #
            # dso_market_obj.trial_clear_type_RT = helpers_dsot.MarketClearingType.UNCONGESTED

            log.info(str(dso_market_obj.Pwclear_RT))
            # create the supply curve that will be handed to the retail market
            retail_market_obj.curve_seller_RT = \
                deepcopy(dso_market_obj.substation_supply_curve_RT(retail_market_obj))

            if write_metrics:
                # ('curve_dso_rt_quantities', [dso_unit] * dso_market_obj.windowLength),
                # ('curve_dso_rt_prices', ['$/' + dso_unit] * dso_market_obj.windowLength),
                # ('cleared_price_rt', '$/' + dso_unit),
                # ('cleared_quantity_rt', dso_unit),
                # ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
                dso_300.append_data(
                    time_granted,
                    dso_market_obj.name,
                    list(dso_market_obj.curve_DSO_RT.quantities),
                    list(dso_market_obj.curve_DSO_RT.prices),
                    dso_market_obj.Pwclear_RT,
                    dso_market_obj.trial_cleared_quantity_RT,
                    dso_market_obj.trial_clear_type_RT,
                )

            tnext_dso_clear_rt += retail_period_rt

        if time_granted >= tnext_dso_clear_da:
            log.info("-- dso day-ahead clearing --")

            # # Getting current cleared data from Substation via HELICS.
            # endpoint_count = h.helicsFederateGetEndpointCount(fed)
            # endid = {}
            # for i in range(0, endpoint_count):
            #     endid["m{}".format(i)] = h.helicsFederateGetEndpointByIndex(fed, i)
            #     if h.helicsEndpointHasMessage(endid["m{}".format(i)]):
            #         end_key = h.helicsEndpointGetName(endid["m{}".format(i)])
            #         property = end_key.split(fed_name + '/')[1].split('/')[1]
            #         if "cleared_price_DA" in property:
            #             dso_market_obj.Pwclear_DA = json.loads(h.helicsEndpointGetMessage(endid["m{}".format(i)]).data)
            #         elif "cleared_quantity_DA" in property:
            #             dso_market_obj.trial_cleared_quantity_DA = json.loads(h.helicsEndpointGetMessage(endid["m{}".format(i)]).data)
            #
            # for idx in range(dso_market_obj.windowLength):
            #     dso_market_obj.trial_clear_type_DA[idx] = helpers_dsot.MarketClearingType.UNCONGESTED
            #
            # # set the day-ahead clearing price (trial clearing using the supply curve)
            # #dso_market_obj.set_Pwclear_DA(hour_of_day, day_of_week)
            # # create the supply curve that will be handed to the retail market

            retail_market_obj.curve_seller_DA = \
                deepcopy(dso_market_obj.substation_supply_curve_DA(retail_market_obj))

            if write_metrics:
                dso_curve_da_quantities = []
                dso_curve_da_prices = []
                for i in range(dso_market_obj.windowLength):
                    dso_curve_da_quantities.append(list(dso_market_obj.curve_DSO_DA[i].quantities))
                    dso_curve_da_prices.append(list(dso_market_obj.curve_DSO_DA[i].prices))

                # ('curve_dso_da_quantities', [[dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
                # ('curve_dso_da_prices', [['$/' + dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
                # ('trial_cleared_price_da', ['$/' + dso_unit] * dso_market_obj.windowLength),
                # ('trial_cleared_quantity_da', [dso_unit] * dso_market_obj.windowLength),
                # ('trial_clear_type_da', ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * dso_market_obj.windowLength),
                dso_3600.append_data(
                    time_granted,
                    dso_market_obj.name,
                    dso_curve_da_quantities,
                    dso_curve_da_prices,
                    dso_market_obj.Pwclear_DA,
                    dso_market_obj.trial_cleared_quantity_DA,
                    dso_market_obj.trial_clear_type_DA,
                )

            tnext_dso_clear_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Retail clearing -----------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_retail_clear_rt:
            log.info("-- retail real-time clearing --")
            # clear the retail real-time market
            retail_market_obj.clear_market_RT(dso_market_obj.transformer_degradation, retail_market_obj.Q_max)

            retail_cleared_quantity_RT = retail_market_obj.cleared_quantity_RT
            log.info('<-------- Real Time Cleared Quantity Arrived -------> ')
            log.info('current real-time quantity cleared -> ' + str(retail_cleared_quantity_RT / 1000.0) + ' MW')
            log.info('current real-time gld load unscaled -> ' + str(dso_market_obj.total_load) + ' kW')

            gld_load_scaled_mean = gld_load_rolling_mean
            log.info('current real-time gld load scaled -> ' + str((gld_load_scaled_mean) / 1e3) + ' MW')
            log.info(
                'current real-time gld load scaled + industrial load -> ' + str((gld_load_scaled_mean) / 1e3) + ' MW')

            retail_cleared_quantity_RT_unadjusted = load_base_unadjusted
            log.info(
                'current real-time quantity unadjusted -> ' + str(retail_cleared_quantity_RT_unadjusted / 1e3) + ' MW')

            retail_cleared_quantity_diff_observed = retail_cleared_quantity_RT - gld_load_scaled_mean
            log.info('current real-time cleared quantity difference from actual GLD load -> ' + str(
                retail_cleared_quantity_diff_observed / 1e3) + ' MW')
            log.info('<-------- Real Time Cleared Quantity Difference Recorded -------> ')
            # publish the cleared real-time price to GridLAB-D
            # fncs.publish('clear_price', retail_market_obj.cleared_price_RT)   #no one is using this
            log.info('current real-time price -> ' + str(retail_market_obj.cleared_price_RT) + ' $/kWh')

            for key, obj in hvac_agent_objs.items():
                if obj.participating and with_market:
                    # inform HVAC agent about the cleared real-time price
                    obj.inform_bid(retail_market_obj.cleared_price_RT)

            for key, obj in water_heater_agent_objs.items():
                if obj.participating and with_market:
                    # inform Water heater agent about the cleared real-time price
                    obj.inform_bid_rt(retail_market_obj.cleared_price_RT)

            for key, obj in battery_agent_objs.items():
                if obj.participating and with_market:
                    # inform Battery agent about the cleared real-time price
                    obj.inform_bid(retail_market_obj.cleared_price_RT)

            if write_metrics:
                # ('curve_buyer_rt_quantities', [retail_unit] * retail_market_obj.windowLength),
                # ('curve_buyer_rt_prices', ['$/' + retail_unit] * retail_market_obj.windowLength),
                # ('curve_seller_rt_quantities', [retail_unit] * retail_market_obj.windowLength),
                # ('curve_seller_rt_prices', ['$/' + retail_unit] * retail_market_obj.windowLength),
                # ('cleared_price_rt', '$/' + retail_unit),
                # ('cleared_quantity_rt', retail_unit),
                # ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
                # ('congestion_surcharge_RT', '$/' + retail_unit)
                if retail_full_metrics:
                    retail_300.append_data(
                        time_granted,
                        retail_market_obj.name,
                        list(retail_market_obj.curve_buyer_RT.quantities),
                        list(retail_market_obj.curve_buyer_RT.prices),
                        list(retail_market_obj.curve_seller_RT.quantities),
                        list(retail_market_obj.curve_seller_RT.prices),
                        retail_market_obj.cleared_price_RT,
                        retail_market_obj.cleared_quantity_RT,
                        retail_market_obj.clear_type_RT,
                        retail_market_obj.congestion_surcharge_RT,
                    )
                else:
                    retail_300.append_data(
                        time_granted,
                        retail_market_obj.name,
                        retail_market_obj.cleared_price_RT,
                        retail_market_obj.cleared_quantity_RT,
                        retail_market_obj.clear_type_RT,
                        retail_market_obj.congestion_surcharge_RT,
                    )
            tnext_retail_clear_rt += retail_period_rt

        if time_granted >= tnext_retail_clear_da:
            log.info("-- retail day-ahead clearing --")
            # clear the retail real-time market
            retail_market_obj.clear_market_DA(dso_market_obj.transformer_degradation, retail_market_obj.Q_max)
            # print("DA cleared price", retail_market_obj.cleared_price_DA)
            log.info('current day-ahead price -> ' + str(retail_market_obj.cleared_price_DA) + ' $/kWh')
            log.info('current day-ahead current quantity -> ' + str(retail_market_obj.cleared_quantity_DA[0]) + ' kW')
            window_rmsd = np.sqrt(np.sum((np.array(retail_market_obj.cleared_price_DA) - np.array(
                retail_market_obj.cleared_price_DA).mean()) ** 2) / 48)
            log.info('current window RMSD --> ' + str(window_rmsd))
            # forecast_obj.set_retail_price_forecast(retail_market_obj.cleared_price_DA)
            forecast_obj.retail_price_forecast = deepcopy(
                retail_market_obj.cleared_price_DA)  ## Adding actual forecast prices
            site_da_wh_cleared_quantities = np.zeros([len(site_da_meter), 48], dtype=float)
            site_da_hvac_cleared_quantities = np.zeros([len(site_da_meter), 48], dtype=float)
            site_da_batt_cleared_quantities = np.zeros([len(site_da_meter), 48], dtype=float)
            for key, obj in hvac_agent_objs.items():
                site_id = site_da_meter.index(config_glm['houses'][key]['billingmeter_id'])
                if obj.participating and with_market:
                    # set the price forecast in the HVAC agent
                    obj.set_price_forecast(forecast_obj.retail_price_forecast)
                    da_cleared_quantity = []
                    for idx in range(obj.windowLength):
                        da_cleared_quantity.append(
                            obj.set_da_cleared_quantity(obj.bid_da[idx], retail_market_obj.cleared_price_DA[idx]))
                    site_da_hvac_cleared_quantities[site_id] += np.array(da_cleared_quantity)
                else:
                    site_da_hvac_cleared_quantities[site_id] += np.zeros(48)

                if write_metrics:
                    # ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
                    hvac_3600.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_da)

            for key, obj in water_heater_agent_objs.items():
                site_id = site_da_meter.index(config_glm['houses'][key]['billingmeter_id'])
                # TODO: In this case House participation was 0 whereas the waterheater participation was 1, so it rightly picks up the cleared quantity, but what to put in the site participation metrics, participating or not participating???
                if obj.participating and with_market:
                    # set the price forecast in the Water heater agent
                    obj.set_price_forecast(forecast_obj.retail_price_forecast)
                    da_cleared_quantity = []
                    for idx in range(obj.windowLength):
                        da_cleared_quantity.append(
                            obj.set_da_cleared_quantity(obj.bid_da[idx], retail_market_obj.cleared_price_DA[idx]))
                    site_da_wh_cleared_quantities[site_id] += np.array(da_cleared_quantity)
                else:
                    site_da_wh_cleared_quantities[site_id] += np.zeros(48)

                if write_metrics:
                    # ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
                    # ('DAOptimizedQuantities', 'kWh'),
                    # ('DAOptimizedSOHC', '%'),
                    water_heater_3600.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_da,
                        # obj.QTY_agent,
                        # obj.SOHC_agent,
                    )

            for key, obj in battery_agent_objs.items():
                site_id = site_da_meter.index(config_glm['inverters'][key]['billingmeter_id'])
                if obj.participating and with_market:
                    # set the price forecast in the Battery agent
                    obj.set_price_forecast(forecast_obj.retail_price_forecast)
                    da_cleared_quantity = []
                    for idx in range(obj.windowLength):
                        da_cleared_quantity.append(
                            obj.from_P_to_Q_battery(obj.bid_da[idx], retail_market_obj.cleared_price_DA[idx]))
                    site_da_batt_cleared_quantities[site_id] += np.array(da_cleared_quantity)
                else:
                    site_da_batt_cleared_quantities[site_id] += np.zeros(48)

                if write_metrics:
                    # ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
                    battery_3600.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_da,
                    )

            site_da_total_quantities_cleared = site_da_wh_cleared_quantities + site_da_hvac_cleared_quantities + site_da_batt_cleared_quantities
            site_da_total_quantities_cleared = site_da_total_quantities_cleared.tolist()

            # log metrics for retail
            retail_curve_buyer_da_quantities = []
            retail_curve_buyer_da_prices = []
            retail_curve_seller_da_quantities = []
            retail_curve_seller_da_prices = []
            for i in range(retail_market_obj.windowLength):
                retail_curve_buyer_da_quantities.append(list(retail_market_obj.curve_buyer_DA[i].quantities))
                retail_curve_buyer_da_prices.append(list(retail_market_obj.curve_buyer_DA[i].prices))
                retail_curve_seller_da_quantities.append(list(retail_market_obj.curve_seller_DA[i].quantities))
                retail_curve_seller_da_prices.append(list(retail_market_obj.curve_seller_DA[i].prices))

            if write_metrics:
                # ('curve_buyer_da_quantities', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                # ('curve_buyer_da_prices', [['$/' + retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                # ('curve_seller_da_quantities', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                # ('curve_seller_da_prices', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                # ('cleared_price_da', ['$/' + retail_unit] * retail_market_obj.windowLength),
                # ('cleared_quantity_da', [retail_unit] * retail_market_obj.windowLength),
                # ('clear_type_da', ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * retail_market_obj.windowLength),
                # (congestion_surcharge_DA', ['$/' + retail_unit] * retail_market_obj.windowLength)

                # log.info("Cleared Price DA --> " + str(np.array( retail_market_obj.cleared_price_DA)))
                # log.info("Cleared Quantity --> " + str(np.array( retail_market_obj.cleared_quantity_DA,)))
                # log.info("Congestion Surcharge --> " + str(np.array(retail_market_obj.congestion_surcharge_DA)))
                if retail_full_metrics:
                    retail_3600.append_data(
                        time_granted,
                        retail_market_obj.name,
                        retail_curve_buyer_da_quantities,
                        retail_curve_buyer_da_prices,
                        retail_curve_seller_da_quantities,
                        retail_curve_seller_da_prices,
                        retail_market_obj.cleared_price_DA,
                        retail_market_obj.cleared_quantity_DA,
                        retail_market_obj.clear_type_DA,
                        retail_market_obj.congestion_surcharge_DA
                    )
                else:
                    retail_3600.append_data(
                        time_granted,
                        retail_market_obj.name,
                        retail_market_obj.cleared_price_DA,
                        retail_market_obj.cleared_quantity_DA,
                        retail_market_obj.clear_type_DA,
                        retail_market_obj.congestion_surcharge_DA
                    )

                # ('meters', ['meterName'] * len(site_da_meter)),
                # ('status', ['[0..1]=[PARTICIPATION,NONPARTICIPATION]'] * len(site_da_meter)),
                # ('non_transactive_hvac', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # ('non_transactive_wh', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # ('non_transactive_zip', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # ('non_transactive_quantities', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # ('transactive_wh', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # ('transactive_hvac', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # ('transactive_batt', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # ('transactive_cleared_quantity', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                # retail_site_3600.append_data(
                #     time_granted,
                #     retail_market_obj.name,
                #     site_da_meter,
                #     site_da_status,
                #     site_da_hvac_uncntrl.tolist(),
                #     site_da_wh_uncntrl.tolist(),
                #     site_da_zip_loads.tolist(),
                #     site_da_total_quantities_uncntrl,
                #     site_da_wh_cleared_quantities.tolist(),
                #     site_da_hvac_cleared_quantities.tolist(),
                #     site_da_batt_cleared_quantities.tolist(),
                #     site_da_total_quantities_cleared,
                # )

            tnext_retail_clear_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Agent adjust --------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_retail_adjust_rt and with_market:
            log.info("-- real-time adjusting --")
            # ### Publish using HELICS ####
            for key, obj in hvac_agent_objs.items():
                # publish the cleared real-time price to HVAC meter
                pub_price = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/price'))
                status = h.helicsPublicationPublishDouble(pub_price, retail_market_obj.cleared_price_RT)
                if obj.participating and obj.bid_accepted(11, current_time):
                    # if HVAC real-time bid is accepted adjust the cooling setpoint in GridLAB-D
                    # if obj.thermostat_mode == 'Cooling':
                    pub_csp = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/cooling_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_csp, obj.cooling_setpoint)
                    # elif obj.thermostat_mode == 'Heating':
                    pub_hsp = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/heating_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_hsp, obj.heating_setpoint)

                # #### Publish using FNCS ####
                # for key, obj in hvac_agent_objs.items():
                #     # publish the cleared real-time price to HVAC meter
                #     fncs.publish(obj.name + '/price', retail_market_obj.cleared_price_RT)
                #     if obj.participating and obj.bid_accepted(11, current_time):
                #         # if HVAC real-time bid is accepted adjust the cooling setpoint in GridLAB-D
                #         #if obj.thermostat_mode == 'Cooling':
                #         fncs.publish(obj.name + '/cooling_setpoint', obj.cooling_setpoint)
                #         #elif obj.thermostat_mode == 'Heating':
                #         fncs.publish(obj.name + '/heating_setpoint', obj.heating_setpoint)
                #         #else:
                #         #    continue

                if write_metrics:
                    # ('cooling_setpoint', 'F'),
                    # ('heating_setpoint', 'F'),
                    # ('cooling_basepoint', 'F'),
                    # ('heating_basepoint', 'F'),
                    # ('agent_room_temperature', 'F'),
                    # ('GLD_air_temperature', 'F'),
                    # ('outdoor_temperature', 'F'),
                    # ('RT_bid_quantity', 'kW'),
                    # ('DA_bid_quantity', '$'),
                    # ('cleared_price', '$'),
                    # ('agent_RT_price', '$'),
                    hvac_300.append_data(
                        time_granted,
                        obj.name,
                        obj.cooling_setpoint,
                        obj.heating_setpoint,
                        obj.basepoint_cooling,
                        obj.basepoint_heating,
                        obj.air_temp_agent,
                        obj.air_temp,
                        obj.outside_air_temperature,
                        obj.bid_quantity,
                        obj.bid_da[0][1][0],
                        obj.cleared_price,
                        obj.bid_rt_price,
                    )
            # ### Publish using HELICS ####
            for key, obj in water_heater_agent_objs.items():
                if obj.participating and obj.bid_accepted(11, current_time):
                    # if Water heater real-time bid is accepted adjust the thermostat setpoint in GridLAB-D
                    water_heater_name = obj.name.replace("hse", "wh")
                    # print("Water_heater name",water_heater_name)
                    pub_lts = h.helicsFederateGetPublication(fed,
                                                             str(fed_name + '/' + water_heater_name + '/lower_tank_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_lts, obj.Setpoint_bottom)
                    pub_uts = h.helicsFederateGetPublication(fed,
                                                             str(fed_name + '/' + water_heater_name + '/upper_tank_setpoint'))
                    status = h.helicsPublicationPublishDouble(pub_uts, obj.Setpoint_upper)
                    print('My published setpoints', obj.Setpoint_bottom, obj.Setpoint_upper)

                # ### Publish using FNCS ####
                # for key, obj in water_heater_agent_objs.items():
                #     if obj.participating and obj.bid_accepted(11, current_time):
                #         # if Water heater real-time bid is accepted adjust the thermostat setpoint in GridLAB-D
                #         water_heater_name = obj.name.replace("hse", "wh")
                #         # print("Water_heater name",water_heater_name)
                #         fncs.publish(water_heater_name + '/lower_tank_setpoint', obj.Setpoint_bottom)
                #         fncs.publish(water_heater_name + '/upper_tank_setpoint', obj.Setpoint_upper)
                #         print('My published setpoints',obj.Setpoint_bottom, obj.Setpoint_upper)

                if write_metrics:
                    # ('bid_four_point_rt', [[retail_unit, '$/' + retail_unit]] * 4),
                    # ('upper_tank_setpoint', 'F'),
                    # ('lower_tank_setpoint', 'F'),
                    # ('Energy_GLD', 'kWh'),
                    # ('SOHC_gld', 'kWh'),
                    # ('Waterdraw_gld', 'gpm'),
                    water_heater_300.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_rt,
                        obj.Setpoint_upper,
                        obj.Setpoint_bottom,
                        obj.E_gld,
                        obj.SOHC,
                        obj.wd_rate,
                    )
            # ### Publish using HELICS ####
            for key, obj in battery_agent_objs.items():
                # publish the cleared real-time price to Battery agent
                if obj.participating and obj.bid_accepted(current_time):
                    # if Battery real-time bid is accepted adjust the P and Q in GridLAB-D
                    pub_po = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/p_out'))
                    status = h.helicsPublicationPublishDouble(pub_po, obj.inv_P_setpoint)
                    pub_qo = h.helicsFederateGetPublication(fed, str(fed_name + '/' + obj.name + '/q_out'))
                    status = h.helicsPublicationPublishDouble(pub_qo, obj.inv_Q_setpoint)
                # ### Publish using FNCS ####
                # for key, obj in battery_agent_objs.items():
                #     # publish the cleared real-time price to Battery agent
                #     if obj.participating and obj.bid_accepted(current_time):
                #         # if Battery real-time bid is accepted adjust the P and Q in GridLAB-D
                #         fncs.publish(obj.name + '/p_out', obj.inv_P_setpoint)
                #         fncs.publish(obj.name + '/q_out', obj.inv_Q_setpoint)

                if write_metrics:
                    # ('bid_four_point_rt', [[retail_unit, '$/' + retail_unit]] * 4),
                    # ('inverter_p_setpoint', 'W'),
                    # ('inverter_q_setpoint', 'W'),
                    # ('battery_soc', '[0-1]'),
                    battery_300.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_rt,
                        obj.inv_P_setpoint,
                        obj.inv_Q_setpoint,
                        obj.Cinit / obj.batteryCapacity
                    )

            tnext_retail_adjust_rt += retail_period_rt

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Write metrics -------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_write_metrics or time_granted >= simulation_duration:
            timing(proc[11], True)
            if write_metrics:
                log.info("-- writing metrics --")
                # write all known metrics to disk
                timing('write_metrics', True)
                collector.write_metrics()
                timing('write_metrics', False)
            tnext_write_metrics_cnt += 1
            tnext_write_metrics = (metrics_record_interval * tnext_write_metrics_cnt) + 1800
            timing(proc[11], False)

            timing(proc[1], False)
            timing(proc[1], True)
            op = open('timing.csv', 'w')
            print(proc_time, sep=', ', file=op, flush=True)
            print(wall_time, sep=', ', file=op, flush=True)
            op.close()

    log.info('finalizing metrics writing')
    timing('finalize_writing', True)
    collector.finalize_writing()
    timing('finalize_writing', False)
    log.info('finalizing HELICS')
    timing(proc[1], False)
    op = open('timing.csv', 'w')
    print(proc_time, sep=', ', file=op, flush=True)
    print(wall_time, sep=', ', file=op, flush=True)
    op.close()
    destroy_federate(fed)

def substation_loop(configfile, metrics_root, with_market=True):
    """ Wrapper for *inner_substation_loop*

    When *inner_substation_loop* finishes, timing and memory metrics will be printed
    for non-Windows platforms.
    """

    inner_substation_loop(configfile, metrics_root, with_market)
