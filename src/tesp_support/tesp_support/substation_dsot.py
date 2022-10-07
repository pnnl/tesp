# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: substation_dsot.py
"""Manages the Transactive Control scheme for DSO+T implementation version 1

Public Functions:
    :dso_loop: initializes and runs the agents

"""
import sys
import time
import json
import logging as log
import numpy as np
from datetime import datetime, timedelta
from copy import deepcopy
from joblib import Parallel, delayed

from .helpers_dsot import enable_logging
from .hvac_dsot import HVACDSOT
from .water_heater_dsot import WaterHeaterDSOT
from .ev_dsot import EVDSOT
from .pv_dsot import PVDSOT
from .battery_dsot import BatteryDSOT
from .dso_market_dsot import DSOMarketDSOT
from .retail_market_dsot import RetailMarketDSOT
from .forecasting_dsot import Forecasting
from .metrics_collector import MetricsStore, MetricsCollector

try:
    import helics
except ImportError:
    # helics = None
    print('WARNING: unable to load HELICS module.', flush=True)

if sys.platform != 'win32':
    import resource


def inner_substation_loop(metrics_root, with_market):
    """Helper function that initializes and runs the DSOT agents

    Reads configfile. Writes *_metrics.json* upon completion.

    Args:
        metrics_root (str): base name of the case for input/output
        with_market (bool): flag that determines if we run with markets
    """

    def publish(name, val):
        pub = helics.helicsFederateGetPublication(hFed, name)
        if type(val) is str:
            helics.helicsPublicationPublishString(pub, val)
        elif type(val) is float or type(val) is np.float64:
            helics.helicsPublicationPublishDouble(pub, val)
        elif type(val) is int:
            helics.helicsPublicationPublishInteger(pub, val)
        elif type(val) is bool:
            helics.helicsPublicationPublishBoolean(pub, val)
        else:
            log.warning('Publish ' + name + ', type ' + str(type(val)) + ' not found!')

    def worker(arg):
        timing(arg.__class__.__name__, True)
        worker_results = arg.DA_optimal_quantities()
        timing(arg.__class__.__name__, False)
        return worker_results
        # return arg.DA_optimal_quantities()

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

    proc = ['init',
            'sim',
            'battRT',
            'hvacRT',
            'whRT',
            'evRT',
            'forecastBatt',
            'forecastHVAC',
            'forecastWH',
            'forecastEV',
            'forecastPV',
            'BatteryDSOT',
            'HVACDSOT',
            'WaterHeaterDSOT',
            'EVDSOT',
            'da_opt',
            'granted',
            'metrics']

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
        lp.close()
    with open(metrics_root + "_glm_dict.json", 'r', encoding='utf-8') as gp:
        config_glm = json.load(gp)
        gp.close()

    # enable logging
    level = config['LogLevel']
    enable_logging(level, 11)

    log.info('starting substation loop...')
    log.info('metrics root -> ' + metrics_root)
    log.info('with markets -> ' + str(with_market))

    scale = 1.0
    use_ref = True
    time_format = '%Y-%m-%d %H:%M:%S'
    start_time = config['StartTime']
    end_time = config['EndTime']
    solver = config['solver']
    priceSensLoad = config['priceSensLoad']
    port = config['serverPort']
    simulation_duration = int((datetime.strptime(end_time, time_format) -
                               datetime.strptime(start_time, time_format)).total_seconds())
    current_time = datetime.strptime(start_time, time_format)

    log.info('simulation start time -> ' + start_time)
    log.info('simulation end time -> ' + end_time)
    log.info('simulation duration in seconds -> ' + str(simulation_duration))

    # Supported backends are from joblib import Parallel:
    # “loky” used by default, can induce some communication and memory overhead when exchanging input and
    #    output data with the worker Python processes.
    # “multiprocessing” previous process-based backend based on multiprocessing.Pool. Less robust than loky.
    # “threading” is a very low-overhead backend but it suffers from the Python Global Interpreter Lock
    #    if the called function relies a lot on Python objects. “threading” is mostly useful when the execution
    #    bottleneck is a compiled extension that explicitly releases the GIL (for instance a Cython loop
    #    wrapped in a “with nogil” block or an expensive call to a library such as NumPy).
    # finally, you can register backends by calling register_parallel_backend.
    #   This will allow you to implement a backend of your liking.
    _backend = 'loky'
    # _backend = 'multiprocessing'   # had some problems
    _verbose = 10
    _NUM_CORE = config['numCore']
    # Document on joblib
    # https://joblib.readthedocs.io/en/latest/generated/joblib.Parallel.html#joblib.Parallel
    parallel = Parallel(n_jobs=_NUM_CORE, backend=_backend, verbose=_verbose)

    dso_config = {}
    topic_map = {}  # Map to dispatch incoming messages. Format [<key>][<receiving object function>]
    dso_market_obj = {}
    dso_unit = 'kW'  # default that will be overwritten by the market definition
    retail_market_obj = {}
    retail_period_da = 3600  # default that will be overwritten by the market definition
    retail_period_rt = 300  # default that will be overwritten by the market definition
    retail_unit = 'kW'  # default that will be overwritten by the market definition

    # instantiate the forecasting object and map their message input
    forecast_obj = Forecasting(port, config['markets']['Q_bid_forecast_correction'])  # make object
    # first, set the simulation year
    forecast_obj.set_sch_year(current_time.year)
    # All schedules are served up through schedule_server.py
    # For reference all schedules paths  [support_path+'name'+'csv']
    # appliance_sch = ['responsive_loads', 'unresponsive_loads']
    # wh_sch = ['small_1', 'small_2', 'small_3', 'small_4', 'small_5', 'small_6',
    #           'large_1', 'large_2', 'large_3', 'large_4', 'large_5', 'large_6']
    # comm_sch = ['retail_heating', 'retail_cooling', 'retail_lights', 'retail_plugs', 'retail_gas',
    #                  'retail_exterior', 'retail_occupancy',
    #                  'lowocc_heating', 'lowocc_cooling', 'lowocc_lights', 'lowocc_plugs', 'lowocc_gas',
    #                  'lowocc_exterior', 'lowocc_occupancy',
    #                  'office_heating', 'office_cooling', 'office_lights', 'office_plugs', 'office_gas',
    #                  'office_exterior', 'office_occupancy',
    #                  'alwaysocc_heating', 'alwaysocc_cooling', 'alwaysocc_lights', 'alwaysocc_plugs', 'alwaysocc_gas',
    #                  'alwaysocc_exterior', 'alwaysocc_occupancy',
    #                  'street_lighting'
    #                  ]
    #
    # pv_power path ('../../../../src/tesp_support/tesp_support/solar/auto_run/solar_pv_power_profiles/8-node_dist_hourly_forecast_power.csv

    topic_map['#solar_diffuse#forecast'] = [forecast_obj.set_solar_diffuse_forecast]
    topic_map['#solar_direct#forecast'] = [forecast_obj.set_solar_direct_forecast]
    topic_map['#temperature#forecast'] = [forecast_obj.set_temperature_forecast]

    market_keys = list(config['markets'].keys())
    for key in market_keys:
        if 'DSO' in key:
            dso_config = config['markets'][key]
            dso_name = key
            dso_market_obj = DSOMarketDSOT(dso_config, dso_name)

            # check the unit of the market
            dso_bus = config['markets'][key]['bus']
            dso_unit = config['markets'][key]['unit']
            dso_full_metrics = config['markets'][key]['full_metrics_detail']  # True for full

            # Update the supply curves for the wholesale. Only once as this will define a curve per day
            # might need to play around with the curve a,b,c here but for now let's run with the defaults
            dso_market_obj.update_wholesale_node_curve()

            if dso_market_obj.number_of_gld_homes > 0.1:  # this is the number when you don't have any feeders
                use_ref = False
                scale = (dso_market_obj.num_of_customers * dso_market_obj.customer_count_mix_residential / dso_market_obj.number_of_gld_homes)
            log.info('Use reference load -> ' + str(use_ref))

            # map topics
            topic_map['gld_load'] = [dso_market_obj.set_total_load]
            topic_map['ind_load_' + str(dso_bus)] = [dso_market_obj.set_ind_load]
            topic_map['ind_ld_hist_' + str(dso_bus)] = [dso_market_obj.set_ind_load_da]
            if use_ref:
                topic_map['ref_load_' + str(dso_bus)] = [dso_market_obj.set_ref_load]
                topic_map['ref_ld_hist_' + str(dso_bus)] = [dso_market_obj.set_ref_load_da]
            topic_map['lmp_da_' + str(dso_bus)] = [dso_market_obj.set_lmp_da]
            topic_map['lmp_rt_' + str(dso_bus)] = [dso_market_obj.set_lmp_rt]
            topic_map['cleared_q_da_' + str(dso_bus)] = [dso_market_obj.set_cleared_q_da]
            topic_map['cleared_q_rt_' + str(dso_bus)] = [dso_market_obj.set_cleared_q_rt]
            log.info('instantiated DSO market agent')

        if 'Retail' in key:
            retail_config = config['markets'][key]
            retail_name = key
            retail_config['basecase'] = not with_market
            retail_config['load_flexibility'] = priceSensLoad
            retail_market_obj = RetailMarketDSOT(retail_config, retail_name)
            retail_period_da = config['markets'][key]['period_da']
            retail_period_rt = config['markets'][key]['period_rt']

            # check the unit of the market
            retail_unit = config['markets'][key]['unit']
            retail_full_metrics = config['markets'][key]['full_metrics_detail']  # True for full
            log.info('instantiated Retail market agent')

    # instantiate the HVAC controller objects and map their message inputs
    hvac_agent_objs = {}
    hvac_keys = list(config['hvacs'].keys())
    for key in hvac_keys:
        row = config['hvacs'][key]
        gld_row = config_glm['houses'][key]
        hvac_agent_objs[key] = HVACDSOT(row, gld_row, key, 11, current_time, solver)

        if '#temperature' not in topic_map.keys():
            topic_map['#temperature'] = [hvac_agent_objs[key].set_temperature]
        else:
            topic_map['#temperature'].append(hvac_agent_objs[key].set_temperature)

        if '#temperature#forecast' not in topic_map.keys():
            topic_map['#temperature#forecast'] = [hvac_agent_objs[key].set_temperature_forecast]
        else:
            topic_map['#temperature#forecast'].append(hvac_agent_objs[key].set_temperature_forecast)

        if '#humidity' not in topic_map.keys():
            topic_map['#humidity'] = [hvac_agent_objs[key].set_humidity]
        else:
            topic_map['#humidity'].append(hvac_agent_objs[key].set_humidity)

        if '#humidity#forecast' not in topic_map.keys():
            topic_map['#humidity#forecast'] = [hvac_agent_objs[key].set_humidity_forecast]
        else:
            topic_map['#humidity#forecast'].append(hvac_agent_objs[key].set_humidity_forecast)

        if '#solar_direct' not in topic_map.keys():
            topic_map['#solar_direct'] = [hvac_agent_objs[key].set_solar_direct]
        else:
            topic_map['#solar_direct'].append(hvac_agent_objs[key].set_solar_direct)

        if '#solar_diffuse' not in topic_map.keys():
            topic_map['#solar_diffuse'] = [hvac_agent_objs[key].set_solar_diffuse]
        else:
            topic_map['#solar_diffuse'].append(hvac_agent_objs[key].set_solar_diffuse)

        # map topics
        topic_map[key + '#Tair'] = [hvac_agent_objs[key].set_air_temp]
        topic_map[key + '#V1'] = [hvac_agent_objs[key].set_voltage]
        topic_map[key + '#HvacLoad'] = [hvac_agent_objs[key].set_hvac_load]
        topic_map[key + '#TotalLoad'] = [hvac_agent_objs[key].set_house_load]
        topic_map[key + '#On'] = [hvac_agent_objs[key].set_hvac_state]
        # topic_map[key + '#Demand'] = [hvac_agent_objs[key].set_hvac_demand]
        # topic_map[key + '#whLoad'] = [hvac_agent_objs[key].set_wh_load]
    log.info('instantiated %s HVAC control agents' % (len(hvac_keys)))

    # instantiate the water heater controller objects and map their message inputs
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

                # map topics
                topic_map[wh_key + '#LTTemp'] = [water_heater_agent_objs[key].set_wh_lower_temperature]
                topic_map[wh_key + '#UTTemp'] = [water_heater_agent_objs[key].set_wh_upper_temperature]
                topic_map[wh_key + '#LTState'] = [water_heater_agent_objs[key].set_wh_lower_state]
                topic_map[wh_key + '#UTState'] = [water_heater_agent_objs[key].set_wh_upper_state]
                topic_map[wh_key + '#WHLoad'] = [water_heater_agent_objs[key].set_wh_load]
                topic_map[wh_key + '#WDRate'] = [water_heater_agent_objs[key].set_wh_wd_rate_val]
            except KeyError as e:
                log.info('Error {}, wh_name in key={}'.format(e, key))
    log.info('instantiated %s water heater control agents' % (len(water_heater_keys)))

    # instantiate the Battery controller objects and map their message inputs
    battery_agent_objs = {}
    battery_keys = list(config['batteries'].keys())
    for key in battery_keys:
        row = config['batteries'][key]
        gld_row = config_glm['inverters'][key]
        battery_agent_objs[key] = BatteryDSOT(row, gld_row, key, 11, current_time, solver)
        # map topics
        # key is the name of inverter resource,
        # but we need battery name, thus the replacement
        topic_map[key.replace('ibat', 'bat') + '#SOC'] = [battery_agent_objs[key].set_battery_SOC]
    log.info('instantiated %s battery control agents' % (len(battery_keys)))

    # instantiate the ev controller objects and map their message inputs
    ev_agent_objs = {}
    ev_keys = list(config['ev'].keys())
    for key in ev_keys:
        row = config['ev'][key]
        gld_row = config_glm['ev'][row['houseName']]
        ev_agent_objs[key] = EVDSOT(row, gld_row, key, 11, current_time, solver)
        # map topics
        topic_map[key + '#SOC'] = [ev_agent_objs[key].set_ev_SOC]
    log.info('instantiated %s electric vehicle control agents' % (len(ev_keys)))

    # instantiate the pv objects and map their message inputs
    pv_agent_objs = {}
    pv_keys = list(config['pv'].keys())
    for key in pv_keys:
        row = config['pv'][key]
        gld_row = config_glm['inverters'][key]
        pv_agent_objs[key] = PVDSOT(row, gld_row, key, 11, current_time)
        # nothing to map as topics
    log.info('instantiated %s solar control agents' % (len(pv_keys)))
    # read and store yearly pv forecast tape

    site_dictionary = config['site_agent']
    site_da_meter = []
    site_da_status = []
    for key, obj in site_dictionary.items():
        site_da_meter.append(key)
        if site_dictionary[key]['participating'] is True:
            site_da_status.append(1)
        else:
            site_da_status.append(0)
    log.info('instantiated site meter name and participating status')

    # adding the metrics collector object
    write_metrics = (config['MetricsInterval'] > 0)
    if write_metrics:
        write_h5 = (config['MetricsType'] == 'h5')
        collector = MetricsCollector.factory(start_time=start_time, write_hdf5=write_h5)

        dso_86400 = MetricsStore(
            name_units_pairs=[
                ('curve_a', ['a'] * 24),
                ('curve_b', ['b'] * 24),
                ('curve_c', ['c'] * 24),
                ('curve_ws_node_quantities', [[dso_unit] * dso_market_obj.num_samples] * 24),
                ('curve_ws_node_prices', [['$/' + dso_unit] * dso_market_obj.num_samples] * 24),
                ('Feqa_T', ['/hour']),  # TODO: double-check that this is correct
            ],
            file_string='dso_market_{}_86400'.format(metrics_root),
            collector=collector,
        )

        dso_tso_86400 = MetricsStore(
            name_units_pairs=[
                ('cleared_lmp_da', ['$/' + dso_unit] * int(dso_market_obj.windowLength/2)),
                ('unresponsive_da', [dso_unit] * int(dso_market_obj.windowLength/2)),
                ('cleared_quantities_da', [dso_unit] * int(dso_market_obj.windowLength/2)),
            ],
            file_string='dso_tso_{}_86400'.format(metrics_root),
            collector=collector,
        )

        dso_tso_300 = MetricsStore(
            name_units_pairs=[
                ('cleared_lmp_rt', '$/' + dso_unit),
                ('unresponsive_rt', dso_unit),
                ('cleared_quantities_rt', dso_unit),
            ],
            file_string='dso_tso_{}_300'.format(metrics_root),
            collector=collector,
        )

        dso_3600 = MetricsStore(
            name_units_pairs=[
                ('curve_dso_da_quantities', [[dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
                ('curve_dso_da_prices', [['$/' + dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
                ('trial_cleared_price_da', ['$/' + dso_unit] * dso_market_obj.windowLength),
                ('trial_cleared_quantity_da', [dso_unit] * dso_market_obj.windowLength),
                ('trial_clear_type_da', ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * dso_market_obj.windowLength),
            ],
            file_string='dso_market_{}_3600'.format(metrics_root),
            collector=collector,
        )

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
                    ('curve_buyer_da_quantities', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('curve_buyer_da_prices', [['$/' + retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('curve_seller_da_quantities', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('curve_seller_da_prices', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
                    ('cleared_price_da', ['$/' + retail_unit] * retail_market_obj.windowLength),
                    ('cleared_quantity_da', [retail_unit] * retail_market_obj.windowLength),
                    ('clear_type_da', ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * retail_market_obj.windowLength),
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
                    ('clear_type_da', ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * retail_market_obj.windowLength),
                    ('congestion_surcharge_DA', ['$/' + retail_unit] * retail_market_obj.windowLength),
                ],
                file_string='retail_market_{}_3600'.format(metrics_root),
                collector=collector,
            )

        if retail_full_metrics:
            retail_site_3600 = MetricsStore(
                name_units_pairs=[
                    ('meters', ['meterName'] * len(site_da_meter)),
                    ('status', ['[0..1]=[PARTICIPATION,NONPARTICIPATION]'] * len(site_da_meter)),
                    ('non_transactive_hvac', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                    ('non_transactive_wh', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                    ('non_transactive_zip', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                    ('non_transactive_quantities', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                    ('transactive_wh', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                    ('transactive_hvac', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                    ('transactive_batt', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                    ('transactive_cleared_quantity', [[retail_unit] * retail_market_obj.windowLength] * len(site_da_meter)),
                ],
                file_string='retail_site_{}_3600'.format(metrics_root),
                collector=collector,
            )
        else:
            retail_site_3600 = MetricsStore(
                name_units_pairs=[
                    ('meters', ['meterName'] * len(site_da_meter)),
                    ('status', ['[0..1]=[PARTICIPATION,NONPARTICIPATION]'] * len(site_da_meter)),
                    ('site_quantities', [[retail_unit] * int(dso_market_obj.windowLength / 2)] * len(site_da_meter)),
                ],
                file_string='retail_site_{}_3600'.format(metrics_root),
                collector=collector,
            )

        dso_ames_bid_3600 = MetricsStore(
            name_units_pairs=[
                ('unresponsive_bid_da', [[retail_unit] * int(dso_market_obj.windowLength / 2)]),
                ('responsive_bid_da', [[retail_unit] * int(dso_market_obj.windowLength / 2)]),
            ],
            file_string='dso_ames_bid_{}_3600'.format(metrics_root),
            collector=collector,
        )

        dso_ames_bid_300 = MetricsStore(
            name_units_pairs=[
                ('unresponsive_bid_rt', retail_unit),
                ('responsive_bid_rt', retail_unit),
                ('bid_received', retail_unit),
                ('bid_adjusted', retail_unit),
            ],
            file_string='dso_ames_bid_{}_300'.format(metrics_root),
            collector=collector,
        )

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
                    ('cleared_quantity_rt_unadj', retail_unit),
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
                    ('cleared_quantity_rt_unadj', retail_unit)
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
                ('DA_temp', 'F'),
                ('DA_price', '$'),
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
                ('RT_quantity', 'kWh'),
                ('DA_quantity', 'kWh'),
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

        ev_3600 = MetricsStore(
            name_units_pairs=[
                ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
            ],
            file_string='ev_agent_{}_3600'.format(metrics_root),
            collector=collector,
        )

        ev_300 = MetricsStore(
            name_units_pairs=[
                ('bid_four_point_rt', [[retail_unit, '$/' + retail_unit]] * 4),
                ('ev_charge', 'W'),
                ('battery_soc', '[0-1]'),
            ],
            file_string='ev_agent_{}_300'.format(metrics_root),
            collector=collector,
        )

    # flag to determine if billing is to be set
    billing_set_defaults = True

    # interval for metrics recording
    # HACK: gld will be typically be on an (even) hour,
    # so we will offset our frequency by 30 minutes (should be on the .5 hour)
    metrics_record_interval = 7200  # will actually be x2 after first round
    tnext_write_metrics_cnt = 1
    tnext_write_metrics = metrics_record_interval + 1800
    # interval for obtaining historical load data (ercot load for the basecase)
    historic_load_interval = 86400

    # for right now, check agent_dict.json for sure
    # retail_period_da = 3600
    # retail_period_rt = 300

    # specific timing tasks to do
    tnext_historic_load_da = 1
    tnext_water_heater_update = 65
    tnext_retail_bid_rt = retail_period_rt - 30 + retail_period_da * 1
    tnext_retail_bid_da = retail_period_da - 60
    tnext_dso_bid_rt = retail_period_rt - 30 + retail_period_da * 1
    tnext_dso_bid_da = retail_period_da - 30
    tnext_wholesale_bid_rt = retail_period_rt - 30 + 86100          # just before a whole day
    tnext_wholesale_bid_da = 36000 - 30  # 10AM minus 30 secs
    tnext_wholesale_clear_rt = retail_period_rt + 86100      # at a whole day + period
    tnext_wholesale_clear_da = 50400  # 2PM
    tnext_dso_clear_rt = retail_period_rt + retail_period_da * 1
    tnext_dso_clear_da = retail_period_da
    tnext_retail_clear_da = retail_period_da
    tnext_retail_clear_rt = retail_period_rt + retail_period_da * 1
    tnext_retail_adjust_rt = retail_period_rt + retail_period_da * 1
    tnext_write_metrics = metrics_record_interval + 1800

    time_granted = 0   # is midnite always
    time_last = 0
    load_base = 0
    load_base_unadjusted = 0.0
    delta_load_forecast_error = 0.0
    load_base_hourly = 0.0
    load_diff = 0
    retail_cleared_quantity_diff_observed = 0.0
    retail_cleared_quantity_diff_observed_last = 0.0
    retail_cleared_quantity_diff_applied = 0.0
    retail_cleared_quantity_RT = 0.0
    retail_cleared_quantity_RT_unadjusted = 0.0
    load_base_from_retail = 0.0
    load_base_for_wholesale = 0.0
    gld_load = []
    gld_load_rolling_mean = 0.0
    gld_load_scaled_mean = 0.0
    retail_day_ahead_diff_observed = 0.0
    ames_lmp = False
    timing(proc[0], False)

    log.info("Initialize HELICS dso federate")
    hFed = helics.helicsCreateValueFederateFromConfig("./" + metrics_root + ".json")
    fedName = helics.helicsFederateGetName(hFed)
    subCount = helics.helicsFederateGetInputCount(hFed)
    pubCount = helics.helicsFederateGetPublicationCount(hFed)
    log.info('Federate name: ' + fedName)
    log.info('Subscription count: ' + str(subCount))
    log.info('Publications count: ' + str(pubCount))
    log.info('Starting HELICS tso federate')
    helics.helicsFederateEnterExecutingMode(hFed)

    timing(proc[1], True)
    while time_granted < simulation_duration:
        # determine the next HELICS time
        timing(proc[16], True)
        next_time =\
            int(min([tnext_historic_load_da, tnext_water_heater_update,
                     tnext_retail_bid_rt, tnext_retail_bid_da, tnext_dso_bid_rt, tnext_dso_bid_da,
                     tnext_wholesale_bid_rt, tnext_wholesale_bid_da, tnext_wholesale_clear_rt, tnext_wholesale_clear_da,
                     tnext_dso_clear_rt, tnext_dso_clear_da, tnext_retail_clear_da, tnext_retail_clear_rt,
                     tnext_retail_adjust_rt, tnext_write_metrics, simulation_duration]))
        time_granted = int(helics.helicsFederateRequestTime(hFed, next_time))
        time_delta = time_granted - time_last
        time_last = time_granted
        timing(proc[16], False)

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
                publish(obj.name + '/bill_mode', 'HOURLY')
                publish(obj.name + '/monthly_fee', '0.0')
                publish(obj.name + '/thermostat_deadband', str(obj.deadband))
            billing_set_defaults = False

        # portion that sets the time-of-day thermostat schedule for HVACs
        for key, obj in hvac_agent_objs.items():
            obj.change_solargain(minute_of_hour, hour_of_day, day_of_week)  # need to be replaced by Qi and Qs calculations
            if obj.change_basepoint(minute_of_hour, hour_of_day, day_of_week, 11, current_time):
                # publish setpoint for participating and basepoint for non-participating
                if obj.participating and with_market:
                    publish(obj.name + '/cooling_setpoint', obj.cooling_setpoint)
                    publish(obj.name + '/heating_setpoint', obj.heating_setpoint)
                else:
                    publish(obj.name + '/cooling_setpoint', obj.basepoint_cooling)
                    publish(obj.name + '/heating_setpoint', obj.basepoint_heating)
                # else:
                #    continue

        # portion that updates the time in the water heater agents
        for key, obj in water_heater_agent_objs.items():
            obj.set_time(hour_of_day, minute_of_hour)

        for t in range(subCount):
            sub = helics.helicsFederateGetInputByIndex(hFed, t)
            key = helics.helicsSubscriptionGetTarget(sub)
            topic = key.split('/')[1]
            # log.info("HELICS subscription index: " + str(t) + ", key: " + key)
            if helics.helicsInputIsUpdated(sub):
                value = helics.helicsInputGetString(sub)
                log.debug(topic + ' -> ' + value)
                if topic in topic_map:
                    for itopic in range(len(topic_map[topic])):
                        if any(x in topic for x in ['#Tair', '#SOC', '#LTTemp', '#UTTemp']):
                            # these function has 2 additional inputs for logging
                            topic_map[topic][itopic](value, 11, current_time)
                        else:
                            # calls function to update the value in object. For details see topicMap
                            topic_map[topic][itopic](value)
                else:
                    log.warning('Unknown topic received from HELICS ({:s}), dropping it'.format(topic))

        # load_player sent this in MW, whereas the substation does everything in kW
        if use_ref:
            try:
                # log.info('Used ref load')
                forecast_obj.base_run_load = np.array(dso_market_obj.ref_load_da) * 1.0e3
            except:
                if tnext_historic_load_da == 1:
                    # log.info('Used forecast load')
                    forecast_obj.base_run_load = np.array(forecast_obj.base_run_load) * dso_market_obj.DSO_Q_max * 0.65

        # if we are running with markets perform certain control actions

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Historical Load Update -------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_historic_load_da:
            if use_ref:
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
            # since the current time is 30 seconds ahead of retail bidding time
            current_retail_time = current_time + timedelta(0, 30)  # timedelta(days, seconds)
            # store real-time distribution loads
            if dso_market_obj.number_of_gld_homes > 0.1:  # this is the number when you don't have any feeders
                gld_load.append(dso_market_obj.total_load)
            else:
                gld_load.append(0.0)
            if len(gld_load) == 12:
                gld_load.pop(-12)
            gld_load_rolling_mean = np.array(gld_load).mean()

            if with_market:
                # HVAC bidding
                timing(proc[3], True)
                for key, obj in hvac_agent_objs.items():
                    if obj.participating:
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
                    if obj.participating:
                        # formulate the real-time bid
                        bid = obj.formulate_bid_rt(11, current_time)
                        # add real-time bid to the retail market
                        retail_market_obj.curve_aggregator_RT('Buyer', bid, obj.name)
                timing(proc[4], False)

                # Battery bidding
                timing(proc[2], True)
                for key, obj in battery_agent_objs.items():
                    if obj.participating:
                        # formulate the real-time bid
                        bid = obj.formulate_bid_rt()
                        # add real-time bid to the retail market
                        retail_market_obj.curve_aggregator_RT('Buyer', bid, obj.name)
                timing(proc[2], False)

                # EV bidding
                timing(proc[5], True)
                for key, obj in ev_agent_objs.items():
                    if obj.participating:
                        # formulate the real-time bid
                        bid = obj.formulate_bid_rt()
                        # add real-time bid to the retail market
                        retail_market_obj.curve_aggregator_RT('Buyer', bid, obj.name)
                timing(proc[5], False)

            # collect agent only RT quantities and price
            # retail_market_obj.AMES_RT_agent_quantities = np.array( retail_market_obj.curve_buyer_RT.quantities )
            # retail_market_obj.AMES_RT_agent_prices = np.array( retail_market_obj.curve_buyer_RT.prices )
            # scaling RT agent only AMES bid before convert_2_AMES_quadratic_BID
            # retail_market_obj.AMES_RT_agent_quantities = retail_market_obj.AMES_RT_agent_quantities*scale
            # log.info("Real-time unscaled flexible bid min, max " +
            #          str(min(retail_market_obj.curve_buyer_RT.quantities)) + " , " +
            #          str(max(retail_market_obj.curve_buyer_RT.quantities)))

            # retail_market_obj.curve_buyer_RT.quantities = retail_market_obj.curve_buyer_RT.quantities * (
            #             dso_market_obj.num_of_customers * dso_market_obj.customer_count_mix_residential / dso_market_obj.number_of_gld_homes)

            # interpolate real time load_base to fix stair step effect from the hourly player
            load_base += load_diff
            # log.info("Real-time bid base after diff --> " + str(load_base / 1.0e3) + "MW")

            # load_base -= retail_cleared_quantity_diff_applied
            # log.info("Real-time bid after correction applied --> " + str(load_base / 1.0e3) + "MW")

            # load_base_unadjusted += load_diff
            # log.info("Real-time bid following previous method       --> " + str(load_base_unadjusted / 1.0e3) + "MW")
            # log.info("Real-time bid day-ahead diff                  --> " + str(load_diff / 1.0e3) + "MW")
            # log.info("Hour 0 day-ahead diff applied                 --> " + str(retail_day_ahead_diff_observed / 1.0e3) + "MW")
            # log.info("Real-time diff applied                        --> " + str(retail_cleared_quantity_diff_observed / 1.0e3) + "MW")
            log.info('<-------- Real Time Bid Formulation Done -------> ')

            # for the first step of real-time bid, we have recieved the correction from the zeroth hour day-ahead,
            # now we set it to zero so it doesn't keep adding
            # if abs(retail_day_ahead_diff_observed) > 0.0:
            #     retail_day_ahead_diff_observed = 0.0
            # log.info("Real-time uncontrollable predicted load --> " + str(load_base))
            # find the difference from the last recorded GLD load
            # log.info("Real-time load difference between predicted load and GLD --> " + str(load_diff_gld))

            # put the difference back in the prediction as the correction
            # load_base += load_diff_gld

            # log.info("Real-time scaled flexible bid min, max " +
            #          str(min(retail_market_obj.curve_buyer_RT.quantities)) + " , " +
            #          str(max(retail_market_obj.curve_buyer_RT.quantities)))

            retail_market_obj.curve_aggregator_RT('Buyer',
                                                  [[load_base, retail_market_obj.U_price_cap_CA],
                                                   [load_base, retail_market_obj.L_price_cap_CA]],
                                                  'uncontrollable load')
            # log.info("Real-time total bid min, max " +
            #          str(min(retail_market_obj.curve_buyer_RT.quantities)) + " , " +
            #          str(max(retail_market_obj.curve_buyer_RT.quantities)))

            tnext_retail_bid_rt += retail_period_rt

        if time_granted >= tnext_retail_bid_da:
            timing(proc[15], True)
            # resetting Qmax from the previous iterations
            dso_market_obj.DSO_Q_max = retail_market_obj.Q_max
            dso_market_obj.update_wholesale_node_curve()
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
            site_da_wh_uncntrl = np.zeros((len(site_da_meter), 48), dtype=np.float)
            site_da_zip_loads = np.zeros((len(site_da_meter), 48), dtype=np.float)
            site_da_hvac_uncntrl = np.zeros((len(site_da_meter), 48), dtype=np.float)
            site_da_ev_uncntrl = np.zeros((len(site_da_meter), 48), dtype=np.float)
            site_da_pv_uncntrl = np.zeros((len(site_da_meter), 48), dtype=np.float)
            timing(proc[15], False)

            # Battery bidding
            timing(proc[6], True)
            for key, obj in battery_agent_objs.items():
                if obj.participating and with_market:
                    P_age_DA.append(obj)
                # else:
            timing(proc[6], True)
            # print('uncontrolled battery ***')
            # print('no uncntrl load for battery)

            # HVAC bidding
            timing(proc[7], True)
            for key, obj in hvac_agent_objs.items():
                site_id = site_da_meter.index(config_glm['houses'][key]['billingmeter_id'])

                # update forecast quantities
                obj.set_solargain_forecast(forecast_solargain)
                skew_scalar = {'zip_skew': int(config_glm['houses'][key]['zip_skew']),
                               'zip_scalar': config_glm['houses'][key]['zip_scalar'],
                               'zip_heatgain_fraction': config_glm['houses'][key]['zip_heatgain_fraction'],
                               'zip_power_fraction': config_glm['houses'][key]['zip_power_fraction'],
                               'zip_power_pf': config_glm['houses'][key]['zip_power_pf']
                               }
                if len(obj.full_internalgain_forecast) < obj.windowLength:
                    forecast_ziploads, forecast_internalgain = \
                        forecast_obj.get_internal_gain_forecast(skew_scalar, forecast_start_time, forecast_obj.extra_forecast_hours)
                    # store extra forecast for future hours
                    obj.store_full_internalgain_forecast(forecast_internalgain)
                    obj.store_full_zipload_forecast(forecast_ziploads)
                obj.set_internalgain_forecast(obj.full_internalgain_forecast[0:48])
                obj.set_zipload_forecast(obj.full_forecast_ziploads[0:48])
                # remove the first entry to make next hour as the first entry
                obj.full_internalgain_forecast.pop(0)
                obj.full_forecast_ziploads.pop(0)
                if len(obj.internalgain_forecast) != 48:
                    raise ValueError("hvac internal gain forecast doesn't have 48 values for this hour!")
                zip_loads.append(obj.forecast_ziploads)
                if obj.participating and with_market:
                    obj.DA_model_parameters(minute_of_hour, hour_of_day, day_of_week)
                    P_age_DA.append(obj)
                else:
                    # if not participating, use hvac model equation without optimization to get forecast hvac load
                    temp = obj.get_uncntrl_hvac_load(minute_of_hour, hour_of_day, day_of_week)
                    # if opt=False, it wont run optimization and will estimate the inflexible load
                    uncntrl_hvac.append(temp)
                    site_da_hvac_uncntrl[site_id] += temp
                site_da_zip_loads[site_id] += obj.forecast_ziploads
            timing(proc[7], False)
            # print('uncontrolled zip ***')
            # print(zip_loads)
            # print('uncontrolled hvac ***')
            # print(uncntrl_hvac)

            # Water heater bidding
            timing(proc[8], True)
            uncntrl_wh = []  # list to store uncontrolled wh load
            for key, obj in water_heater_agent_objs.items():
                site_id = site_da_meter.index(config_glm['houses'][key]['billingmeter_id'])

                skew_scalar = {'wh_skew': int(config_glm['houses'][key]['wh_skew']),
                               'wh_scalar': config_glm['houses'][key]['wh_scalar'],
                               'wh_schedule_name': config_glm['houses'][key]['wh_schedule_name'],
                               }
                # to get the forecast from forecasting agent
                forecast_waterdrawSCH = forecast_obj.get_waterdraw_forecast(skew_scalar, forecast_start_time)
                # update forecast quantities
                obj.set_forecasted_schedule(forecast_waterdrawSCH)
                if obj.participating and with_market:
                    P_age_DA.append(obj)
                else:
                    # get waterheater base load through direct equations without optimization
                    temp1 = obj.get_uncntrl_wh_load()
                    uncntrl_wh.append(temp1)
                    site_da_wh_uncntrl[site_id] += temp1
            timing(proc[8], False)
            # print('uncontrolled wh ***')
            # print(uncntrl_wh)

            # Electrical Vehicle bidding
            timing(proc[9], True)
            uncntrl_ev = []  # list to store uncontrolled ev load
            for key, obj in ev_agent_objs.items():
                site_id = site_da_meter.index(config_glm['ev'][obj.houseName]['billingmeter_id'])
                if obj.participating and with_market:
                    # print('current_time before opt: ', current_time)
                    obj.DA_model_parameters(current_time)
                    P_age_DA.append(obj)
                else:
                    # get ev base load through direct equations without optimization
                    temp1 = obj.get_uncntrl_ev_load(current_time)
                    uncntrl_ev.append(temp1)
                    site_da_ev_uncntrl[site_id] += temp1
            timing(proc[9], False)
            # print('uncontrolled ev ***')
            # print(uncntrl_ev)

            # PV generation forecasting
            timing(proc[10], True)
            uncntrl_pv = []  # list to store uncontrolled pv generation
            if len(pv_agent_objs) > 0:
                # lets get the next 48-hours solar forecast from DSO level tape as it is same for all pv agents
                solar_f = forecast_obj.get_solar_forecast(forecast_start_time, dso_config['bus'])
                for key, obj in pv_agent_objs.items():
                    site_id = site_da_meter.index(config_glm['inverters'][key]['billingmeter_id'])
                    temp1 = obj.scale_pv_forecast(solar_f)
                    uncntrl_pv.append(temp1)
                    site_da_pv_uncntrl[site_id] += temp1
            timing(proc[10], False)
            # print('uncontrolled pv ***')
            # print(uncntrl_pv)

            timing(proc[15], True)
            # Sum all uncontrollable loads
            sum_uncntrl = np.array(zip_loads).sum(axis=0) + \
                                 np.array(uncntrl_wh).sum(axis=0) + \
                                 np.array(uncntrl_hvac).sum(axis=0) + \
                                 np.array(uncntrl_ev).sum(axis=0) - \
                                 np.array(uncntrl_pv).sum(axis=0)
            site_da_quantities = sum_uncntrl.tolist()
            site_da_total_quantities_uncntrl = site_da_wh_uncntrl + site_da_hvac_uncntrl + site_da_zip_loads \
                                               + site_da_ev_uncntrl - site_da_pv_uncntrl
            site_da_total_quantities_uncntrl = site_da_total_quantities_uncntrl.tolist()
            if site_da_quantities == 0.0:
                site_da_quantities = [0.0]*retail_market_obj.windowLength
            # print('uncontrolled total ***')
            # print(site_da_quantities)
            # print('uncontrolled total site load ***')
            # print(site_da_total_quantities_uncntrl)

            # formulating bid DA with multiprocessing library
            # created pyomo models in serial, but solves in parallel
            # (sending only the pyomo model, rather than whole batter object to the processes)
            if len(P_age_DA) > 0:
                log.info('About to solve {} parallel opts (over available processes)'.format(len(P_age_DA)))
                results = parallel(delayed(worker)(p) for p in P_age_DA)
            else:
                log.info('No opts need solving, skipping use of "parallel" obj!')
                results = []
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

            # collect agent only DA quantities and price
            # retail_market_obj.AMES_DA_agent_quantities=dict()
            # retail_market_obj.AMES_DA_agent_prices=dict()
            # for idx in range(retail_market_obj.windowLength):
            #     retail_market_obj.AMES_DA_agent_quantities[idx] = retail_market_obj.curve_buyer_DA[idx].quantities
            #     retail_market_obj.AMES_DA_agent_prices[idx]     = retail_market_obj.curve_buyer_DA[idx].prices
            # scaling DA agent only AMES bid before convert_2_AMES_quadratic_BID
            # for idx in range(retail_market_obj.windowLength):
            #     retail_market_obj.AMES_DA_agent_quantities[idx] = retail_market_obj.AMES_DA_agent_quantities[idx]*scale

            # log.info("Max Hour 22 unscaled flexible load " + str(max(retail_market_obj.curve_buyer_DA[22].quantities)))
            # log.info("Min Hour 22 unscaled flexible load " + str(min(retail_market_obj.curve_buyer_DA[22].quantities)))
            # log.info("Max Hour 21 unscaled flexible load " + str(min(retail_market_obj.curve_buyer_DA[21].quantities)))
            # log.info("Max Hour 21 unscaled flexible load " + str(max(retail_market_obj.curve_buyer_DA[21].quantities)))

            # if retail_market_obj.basecase is not True:
            #     for idx in range(retail_market_obj.windowLength):
            #         retail_market_obj.curve_buyer_DA[idx].quantities = retail_market_obj.curve_buyer_DA[idx].quantities * \
            #             (dso_market_obj.num_of_customers * dso_market_obj.customer_count_mix_residential / dso_market_obj.number_of_gld_homes)

            # if retail_market_obj.basecase is not True:
            #     for idx in range(retail_market_obj.windowLength):
            #         retail_market_obj.curve_buyer_DA[idx].quantities = retail_market_obj.curve_buyer_DA[idx].quantities * \
            #             (dso_market_obj.num_of_customers * dso_market_obj.customer_count_mix_residential / dso_market_obj.number_of_gld_homes)
            # log.info("Max Hour 10 scaled flexible load " + str(max(retail_market_obj.curve_buyer_DA[10].quantities)))
            # log.info("Max Hour 0 scaled flexible load " + str(max(retail_market_obj.curve_buyer_DA[0].quantities)))

            # log.info("Max Hour 10 scaled flexible load " + str(max(retail_market_obj.curve_buyer_DA[10].quantities)))
            # log.info("Max Hour 0 scaled flexible load " + str(max(retail_market_obj.curve_buyer_DA[0].quantities)))

            # add the uncontrollable load
            uncontrollable_load_bid_da = [[[0], [0]]] * retail_market_obj.windowLength
            # uncontrollable_load_bid_ind_da = [[[0], [0]]] * retail_market_obj.windowLength

            if use_ref:
                # here you got things from basecase so roll it please and add error
                forecast_load = np.roll(forecast_load, -1)
                forecast_load_error = forecast_load + 0.05 * forecast_load * np.random.normal()  # adding error
                forecast_load_ind = [0] * dso_market_obj.windowLength
            else:
                # getting industrial Load now
                forecast_load_ind = dso_market_obj.ind_load_da
                forecast_load_ind = forecast_load_ind.tolist()
                # forecast_load_ind = forecast_obj.get_substation_unresponsive_industrial_load_forecast(dso_market_obj.ind_load_da)

                # no rolling needed because stuff is in the right spot and doesn't need error
                # OPTION-1 Uses internal uncontrollable load forecast by site agent
                # forecast_load_uncontrollable = deepcopy(np.array(site_da_quantities)*(dso_market_obj.num_of_customers*dso_market_obj.customer_count_mix_residential/dso_market_obj.number_of_gld_homes))
                forecast_load_uncontrollable = deepcopy(np.array(site_da_quantities))
                # OPTION-2 Uses fixed peak load value --- has proven convergence
                # forecast_load = forecast_obj.get_substation_unresponsive_load_forecast(800)
                # forecast_load_error = forecast_load_uncontrollable + forecast_load_ind # no error
                forecast_load_error = forecast_load_uncontrollable  # no error
            load_diff = (forecast_load_error[1] - forecast_load_error[0]) / 12
            load_base_hourly = forecast_load_error
            load_base = forecast_load_error[0]
            #
            # #     print('uncontrolled load after scale without industrial ***')
            # #     print(forecast_load_uncontrollable)
            #
            # # print('total uncontrolled load after scale including industrial***')
            # # print(forecast_load_error)
            # # log.info("Hour 21 uncontrollable before scale" + str(site_da_quantities[21]))
            # # log.info("Hour 21 uncontrollable after scale" + str(forecast_load_uncontrollable[21]))
            # # log.info("Hour 21 industrial load  scale" + str(forecast_load_ind[21]))
            # # log.info("Hour 22 uncontrollable before scale" + str(site_da_quantities[22]))
            # # log.info("Hour 22 uncontrollable after scale" + str(forecast_load_uncontrollable[22]))
            # # log.info("Hour 22 industrial load  scale" + str(forecast_load_ind[22]))
            #
            # # print("DA load: ", forecast_load_error)
            #
            # # second hour day-ahead onwards we have adjusted "base bid" from our rt correction procedure (see retail_bid_rt), so we don't change that
            # # What we still want is:
            # # 1) the difference the day-ahead bid sees in the hour "load_diff"
            # # 2) and if there exists any day-ahead error in the uncontrollable load forecast and scaled gld load
            # if time_granted >= (retail_period_da + retail_period_rt):
            #     # retail_day_ahead_diff_observed = forecast_load_uncontrollable[0] - gld_load_scaled_mean
            #     # retail_day_ahead_diff_observed = 0.0
            #     load_diff = (forecast_load_error[1] - forecast_load_error[0]) / 12
            #     load_base_unadjusted = forecast_load_error[0]
            #     # if len(P_age_DA) > 0:
            #     #     # delta_load_forecast_error = forecast_load_error - np.array(forecast_load_error).mean()
            #     #     # load_base_hourly = load_base + delta_load_forecast_error
            #     # else:
            #     load_base_hourly = forecast_load_error
            #     # forecast_load_error[0] = load_base
            #     # correct the zeroth hour uncontrollable bid which is going to be passed to the real-time
            #     # this is because at the hour mark the load_base changes which is not reflected in the adjustment done prior to that hour
            #     # also notice that we are not subtracting the industrial load because in realtime we add it back.
            # else:
            #     # retail_day_ahead_diff_observed = 0.0
            #     load_diff = (forecast_load_error[1] - forecast_load_error[0])/12
            #     load_base = forecast_load_error[0]
            #     load_base_unadjusted = forecast_load_error[0]
            #     load_base_hourly = forecast_load_error
            for idx in range(retail_market_obj.windowLength):
                uncontrollable_load_bid_da[idx] = [[load_base_hourly[idx], retail_market_obj.price_cap],
                                                   [load_base_hourly[idx], 0]]

            retail_market_obj.curve_aggregator_DA('Buyer', uncontrollable_load_bid_da, 'uncontrollable load')

            # log.info("Scale " + str((dso_market_obj.num_of_customers*dso_market_obj.customer_count_mix_residential/dso_market_obj.number_of_gld_homes)))
            # log.info("Hour 10 total quantity after scale min, max " + str(min(retail_market_obj.curve_buyer_DA[10].quantities))+ ", " + str(max(retail_market_obj.curve_buyer_DA[10].quantities)))
            # log.info("Hour 0 total quantity after scale min, max " + str(min(retail_market_obj.curve_buyer_DA[0].quantities))+ ", " + str(max(retail_market_obj.curve_buyer_DA[0].quantities)))

            timing(proc[15], False)
            tnext_retail_bid_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ DSO bidding ---------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_dso_bid_rt:
            log.info("-- dso real-time bidding --")
            dso_market_obj.clean_bids_RT()
            retail_market_obj.curve_buyer_RT.quantities = retail_market_obj.curve_buyer_RT.quantities * scale + forecast_load_ind[0]
            dso_market_obj.curve_aggregator_DSO_RT(retail_market_obj.curve_buyer_RT, Q_max=dso_market_obj.DSO_Q_max)
            tnext_dso_bid_rt += retail_period_rt

        if time_granted >= tnext_dso_bid_da:
            log.info("-- dso day-ahead bidding --")
            dso_market_obj.clean_bids_DA()
            for idx in range(retail_market_obj.windowLength):
                retail_market_obj.curve_buyer_DA[idx].quantities = retail_market_obj.curve_buyer_DA[idx].quantities * scale + forecast_load_ind[0]
            dso_market_obj.curve_aggregator_DSO_DA(retail_market_obj.curve_buyer_DA, Q_max=dso_market_obj.DSO_Q_max)
            tnext_dso_bid_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Wholesale bidding ---------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_wholesale_bid_rt:
            gld_load_scaled_mean = gld_load_rolling_mean * scale
            log.info('AMES-RT-Bid-current real-time cleared bid -> ' + str(retail_cleared_quantity_RT / 1.0e3) + ' MW')
            log.info('AMES-RT-Bid-current real-time gld mean load scaled -> ' + str(gld_load_scaled_mean / 1.0e3) + ' MW')

            if not use_ref:
                log.info('AMES-RT-Bid-current current real-time gld mean load scaled + industrial load -> ' +
                         str((gld_load_scaled_mean + forecast_load_ind[0]) / 1.0e3) + ' MW')
                retail_cleared_quantity_diff_observed = retail_cleared_quantity_RT - gld_load_scaled_mean - forecast_load_ind[0]
            else:
                retail_cleared_quantity_diff_observed = 0.0

            log.info('AMES-RT-Bid-current real-time cleared quantity difference from actual GLD load -> ' + str(
                retail_cleared_quantity_diff_observed / 1.0e3) + ' MW')
            retail_cleared_quantity_RT_unadjusted = retail_cleared_quantity_RT
            log.info('current real-time quantity unadjusted -> ' +
                     str(retail_cleared_quantity_RT_unadjusted / 1.0e3) + ' MW')

            # retail_cleared_quantity_diff_applied = retail_cleared_quantity_diff_observed # + retail_day_ahead_diff_observed

            # load_base_for_wholesale = load_base_from_retail - retail_cleared_quantity_diff_applied
            retail_market_obj.curve_buyer_RT_for_AMES.prices = retail_market_obj.curve_buyer_RT.prices
            retail_market_obj.curve_buyer_RT_for_AMES.quantities = retail_market_obj.curve_buyer_RT.quantities - retail_cleared_quantity_diff_observed
            retail_market_obj.cleared_quantity_RT_for_AMES = retail_cleared_quantity_RT - retail_cleared_quantity_diff_observed
            # retail_cleared_quantity_RT -= load_base_for_wholesale
            log.info("-- wholesale AMES real-time bidding --")
            log.info('current real-time cleared quantities -> ' + str(retail_cleared_quantity_RT) + ' kW')
            log.info('current real-time corrected cleared quantities -> ' + str(retail_market_obj.cleared_quantity_RT_for_AMES) + ' kW')

            retail_market_obj.curve_aggregator_AMES_RT(retail_market_obj.curve_buyer_RT_for_AMES, dso_market_obj.DSO_Q_max,  retail_market_obj.cleared_quantity_RT_for_AMES, forecast_obj.retail_price_forecast[0])  # makes AMES_RT

            rt_bid = {'unresp_mw': retail_market_obj.AMES_RT[0],
                      'resp_max_mw': retail_market_obj.AMES_RT[1],
                      'resp_c2': retail_market_obj.AMES_RT[2],
                      'resp_c1': retail_market_obj.AMES_RT[3],
                      'resp_c0': retail_market_obj.AMES_RT[4],
                      'resp_deg': retail_market_obj.AMES_RT[5]}
            publish('rt_bid_' + str(dso_bus), json.dumps(rt_bid))

            print('Real-time bid at', time_granted, '=', retail_market_obj.AMES_RT, flush=True)
            log.info('Total RT bid to AMES unresponsive' + '=' + str(retail_market_obj.AMES_RT[0]) + 'MW')
            log.info('Total RT bid to AMES responsive max' + '=' + str(retail_market_obj.AMES_RT[1]) + 'MW')

            timing(proc[17], True)
            if write_metrics:
                dso_ames_bid_300.append_data(
                    time_granted,
                    dso_market_obj.name,
                    retail_market_obj.AMES_RT[0],
                    retail_market_obj.AMES_RT[1],
                    retail_cleared_quantity_RT,
                    retail_market_obj.cleared_quantity_RT_for_AMES,
                )
            timing(proc[17], False)
            tnext_wholesale_bid_rt += retail_period_rt

        if time_granted >= tnext_wholesale_bid_da:
            log.info("-- wholesale AMES day-ahead bidding --")
            log.info('current day-ahead cleared quantities -> ' + str(retail_cleared_quantity_DA) + ' kW')
            retail_market_obj.curve_aggregator_AMES_DA(retail_market_obj.curve_buyer_DA, dso_market_obj.DSO_Q_max, retail_cleared_quantity_DA, forecast_obj.retail_price_forecast)  # makes AMES_DA
            da_bid = {'unresp_mw': [], 'resp_max_mw': [], 'resp_c2': [], 'resp_c1': [], 'resp_c0': [], 'resp_deg': []}
            offset = 14
            for i in range(24):   # +14 to get to the midnight should be 15    array[0-47] at 9:59:30 0 = 9, 9+15 = 24
                idx = i + offset
                # if retail_market_obj.AMES_DA[i+15][3] == 0.0:
                #     retail_market_obj.AMES_DA[i+15][1] = 0.0  # indication that bid is not created so just sending an incensitive bid with sLmax = 0 so demand is not mistaken by AMES as flexible
                da_bid['unresp_mw'].append(retail_market_obj.AMES_DA[idx][0])
                da_bid['resp_max_mw'].append(retail_market_obj.AMES_DA[idx][1])
                da_bid['resp_c2'].append(retail_market_obj.AMES_DA[idx][2])
                da_bid['resp_c1'].append(retail_market_obj.AMES_DA[idx][3])
                da_bid['resp_c0'].append(retail_market_obj.AMES_DA[idx][4])
                da_bid['resp_deg'].append(retail_market_obj.AMES_DA[idx][5])
                log.info('DA Quantity sent at hour ' + str(i) +
                         ', unresponsive:' + str(retail_market_obj.AMES_DA[idx][0]) +
                         ', responsive max:' + str(retail_market_obj.AMES_DA[idx][1]))

            da_bid['unresp_mw'] = forecast_obj.correcting_Q_forecast_10_AM(da_bid['unresp_mw'], offset, day_of_week)
            
            publish('da_bid_' + str(dso_bus), json.dumps(da_bid))

            print('Day-Ahead bid at', time_granted, '=', retail_market_obj.AMES_DA, flush=True)

            temp = np.array(site_da_total_quantities_uncntrl) + np.array(site_da_total_quantities_cleared)
            site_total_quantities = []
            for idx in range(0, len(temp)):
                site_total_quantities.append(temp[idx][offset:offset+24].tolist())    # was 14:38, see line 1223

            timing(proc[17], True)
            if write_metrics:
                if retail_full_metrics:
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
                    retail_site_3600.append_data(
                        time_granted,
                        retail_market_obj.name,
                        site_da_meter,
                        site_da_status,
                        site_da_hvac_uncntrl.tolist(),
                        site_da_wh_uncntrl.tolist(),
                        site_da_zip_loads.tolist(),
                        site_da_total_quantities_uncntrl,
                        site_da_wh_cleared_quantities.tolist(),
                        site_da_hvac_cleared_quantities.tolist(),
                        site_da_batt_cleared_quantities.tolist(),
                        site_da_total_quantities_cleared,
                    )
                else:
                    retail_site_3600.append_data(
                        time_granted,
                        retail_market_obj.name,
                        site_da_meter,
                        site_da_status,
                        site_total_quantities,
                    )
            timing(proc[17], False)

            timing(proc[17], True)
            if write_metrics:
                dso_ames_bid_3600.append_data(
                    time_granted,
                    dso_market_obj.name,
                    da_bid['unresp_mw'],
                    da_bid['resp_max_mw'],
                )
            timing(proc[17], False)
            tnext_wholesale_bid_da += 86400

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Wholesale clearing --------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_wholesale_clear_rt:
            log.info("-- wholesale AMES real-time clearing --")

            # the actual load is the unresponsive load, plus a cleared portion of the responsive load
            try:
                lmp_rt = dso_market_obj.lmp_rt[0]   # TSO sends the price in $/MWh
                dso_market_obj.active_power_rt = (dso_market_obj.cleared_q_rt * 1.0e3) + retail_cleared_quantity_diff_observed_last  # TSO sends back the total quantity in MW
                ames_lmp = True
            except:
                dso_market_obj.active_power_rt = retail_market_obj.cleared_quantity_RT_for_AMES + retail_cleared_quantity_diff_observed_last  # TSO sends back the total quantity in MW
                lmp_rt = dso_market_obj.default_lmp * 1.0e3
                log.info("No AMES running -- assigned a default lmp using the lmp forecaster")

            c1 = retail_market_obj.AMES_RT[3]
            c2 = retail_market_obj.AMES_RT[2]
            resp_max = retail_market_obj.AMES_RT[1]
            unresp_rt = retail_market_obj.AMES_RT[0] * 1.0e3  # Retail agent had prepared bid in MW
            # resp_rt = (dso_market_obj.cleared_q_rt - retail_market_obj.AMES_RT[0]) * 1.0e3
            # dso_market_obj.active_power_rt = unresp_rt + resp_rt
            dso_market_obj.reactive_power_rt = (dso_market_obj.active_power_rt * dso_config['Qnom'] / dso_config['Pnom'])

            log.info('wholesale real-time cleared quantity  --> ' + str(dso_market_obj.active_power_rt / 1.0e3) + ' MW')
            log.info('wholesale real-time cleared price     --> ' + str(lmp_rt) + ' $/MWh')
            log.info('wholesale real-time cleared from AMES -->' + str(dso_market_obj.cleared_q_rt) + ' MW')
            log.info('wholesale real-time cleared corrected -->' + str(retail_cleared_quantity_diff_observed_last / 1.0e3) + ' MW')
            timing(proc[17], True)
            if write_metrics:
                # ('cleared_lmp_rt', '$/' + dso_unit),
                # ('unresponsive_rt', dso_unit),
                # ('cleared_quantities_rt', dso_unit),
                dso_tso_300.append_data(
                    time_granted,
                    dso_market_obj.name,
                    lmp_rt,
                    unresp_rt,
                    dso_market_obj.active_power_rt,
                )
            timing(proc[17], False)
            tnext_wholesale_clear_rt += retail_period_rt

        if time_granted >= tnext_wholesale_clear_da:
            log.info("-- wholesale day-ahead clearing --")
            # the actual load is the unresponsive load, plus a cleared portion of the responsive load
            dso_market_obj.active_power_total_da = []
            dso_market_obj.reactie_power_total_da = []
            lmp_da = []
            unresp_da = []
            resp_da = []
            qf = (dso_config['Qnom'] / dso_config['Pnom'])
            for ii in range(24):
                try:
                    lmp_da.append(dso_market_obj.lmp_da[ii] / 1.0e3)  # TSO sends the price in $/MWh
                except:
                    lmp_da.append(0.0)
                c1 = retail_market_obj.AMES_DA[ii][3]
                c2 = retail_market_obj.AMES_DA[ii][2]
                resp_max = retail_market_obj.AMES_DA[ii][1]
                unresp_da.append(retail_market_obj.AMES_DA[ii][0] * 1.0e3)  # Retail agent had prepared bid in MW)
                # resp_da.append((dso_market_obj.cleared_q_da[ii]-retail_market_obj.AMES_DA[ii][0]) * 1.0e3) # TSO sends the quantity back in MW
                # TODO: Fix this
                dso_market_obj.active_power_total_da.append(dso_market_obj.cleared_q_da[ii] * 1.0e3)  # active power
                dso_market_obj.reactie_power_total_da.append((dso_market_obj.cleared_q_da[ii] * 1.0e3) * qf)  # reactive power

            log.info('wholesale day-ahead cleared quantity -> ' + str(dso_market_obj.active_power_total_da) + ' MW')

            timing(proc[17], True)
            if write_metrics:
                curve_ws_node_quantities = []
                curve_ws_node_prices = []
                for i in range(24):
                    curve_ws_node_quantities.append(list(dso_market_obj.curve_ws_node[day_of_week][i].quantities))
                    curve_ws_node_prices.append(list(dso_market_obj.curve_ws_node[day_of_week][i].prices))

                # ('curve_a', ['a'] * 24),
                # ('curve_b', ['b'] * 24),
                # ('curve_c', ['c'] * 24),
                # ('curve_ws_node_quantities', [[dso_unit] * dso_market_obj.num_samples] * 24),
                # ('curve_ws_node_prices', [['$/' + dso_unit] * dso_market_obj.num_samples] * 24),
                # ('Feqa_T', ['/hour']),
                dso_86400.append_data(
                    time_granted,
                    dso_market_obj.name,
                    list(dso_market_obj.curve_a[day_of_week]),
                    list(dso_market_obj.curve_b[day_of_week]),
                    list(dso_market_obj.curve_c[day_of_week]),
                    curve_ws_node_quantities,
                    curve_ws_node_prices,
                    dso_market_obj.Feqa_T,
                )
                # ('cleared_lmp_da', ['$/' + dso_unit] * int(dso_market_obj.windowLength/2)),
                # ('unresponsive_da', [dso_unit] * int(dso_market_obj.windowLength/2)),
                # ('cleared_quantities_da', [dso_unit] * int(dso_market_obj.windowLength/2)),
                dso_tso_86400.append_data(
                    time_granted,
                    dso_market_obj.name,
                    list(lmp_da),
                    list(unresp_da),
                    list(dso_market_obj.active_power_total_da),
                )
            timing(proc[17], False)
            tnext_wholesale_clear_da += 86400

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ DSO clearing --------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_dso_clear_rt:
            log.info("-- dso real-time clearing --")
            # set the real-time clearing price (trial clearing using the supply curve)
            if ames_lmp is True:
                dso_market_obj.set_Pwclear_RT(hour_of_day, day_of_week, lmp=True)
                log.info("Current DSO price received from AMES-->" + str(lmp_rt / 1.0e3) + '$/kWh')
                log.info("Current DSO quantity received from AMES-->" + str(dso_market_obj.active_power_rt / 1.0e3) + 'MW')
                log.info("Current DSO projected price on curve -->" + str(dso_market_obj.Pwclear_RT) + '$/kWh')
                log.info("Current DSO projected quantity on curve -->" + str(dso_market_obj.trial_cleared_quantity_RT / 1.0e3) + 'MW')
                log.info("Current DSO Clear Type from AMES -->" + str(dso_market_obj.trial_clear_type_RT))
            else:
                dso_market_obj.set_Pwclear_RT(hour_of_day, day_of_week)
                log.info("Current DSO cleared price-->"+str(dso_market_obj.Pwclear_RT)+'$/kWh')
                log.info("Current DSO cleared quantity-->"+str(dso_market_obj.trial_cleared_quantity_RT / 1.0e3)+'MW')

            # create the supply curve that will be handed to the retail market
            retail_market_obj.curve_seller_RT = \
                deepcopy(dso_market_obj.substation_supply_curve_RT(retail_market_obj))
            log.info('supply curve min' + str(np.min(np.array(retail_market_obj.curve_seller_RT.quantities))))
            log.info('supply curve max' + str(np.max(np.array(retail_market_obj.curve_seller_RT.quantities))))
            timing(proc[17], True)
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
            timing(proc[17], False)
            tnext_dso_clear_rt += retail_period_rt

        if time_granted >= tnext_dso_clear_da:
            log.info("-- dso day-ahead clearing --")
            # set the day-ahead clearing price (trial clearing using the supply curve)
            dso_market_obj.set_Pwclear_DA(hour_of_day, day_of_week)
            # create the supply curve that will be handed to the retail market
            log.info("dso DA cleared prices: "+str(dso_market_obj.Pwclear_DA))
            retail_market_obj.curve_seller_DA = \
                deepcopy(dso_market_obj.substation_supply_curve_DA(retail_market_obj))

            timing(proc[17], True)
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
            timing(proc[17], False)
            tnext_dso_clear_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Retail clearing -----------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_retail_clear_rt:
            log.info("-- retail real-time clearing --")
            # clear the retail real-time market
            retail_market_obj.clear_market_RT(dso_market_obj.transformer_degradation, retail_market_obj.Q_max)
            retail_cleared_quantity_RT = retail_market_obj.cleared_quantity_RT
            retail_market_obj.cleared_quantity_RT_unscaled = (retail_market_obj.cleared_quantity_RT - forecast_load_ind[0])/scale

            log.info('current retail real-time cleared price -> ' + str(retail_market_obj.cleared_price_RT) + ' $/kWh')
            log.info('current retail real-time cleared type -->' + str(retail_market_obj.clear_type_RT))
            log.info('current retail real-time congestion charge -->' + str(retail_market_obj.congestion_surcharge_RT) + ' $/kWh')
            log.info('current retail real-time cleared quantity scaled -> ' + str(retail_market_obj.cleared_quantity_RT / 1.0e3) + ' MW')
            log.info('current retail real-time cleared quantity unscaled -> ' + str(retail_market_obj.cleared_quantity_RT_unscaled / 1.0e3) + ' MW')
            log.info('current gld load -> ' + str(dso_market_obj.total_load / 1.0e3) + ' MW')
            log.info('current gld load mean -> ' + str(gld_load_rolling_mean / 1.0e3) + ' MW')
            log.info('current diff (gld_mean minus cleared bid)' + str(-retail_market_obj.cleared_quantity_RT_unscaled+gld_load_rolling_mean) + ' kW')
            log.info('current diff (gld_inst minus cleared bid)' + str(-retail_market_obj.cleared_quantity_RT_unscaled+dso_market_obj.total_load) + ' kW')

            if with_market:
                for key, obj in hvac_agent_objs.items():
                    if obj.participating:
                        # inform HVAC agent about the cleared real-time price
                        obj.inform_bid(retail_market_obj.cleared_price_RT)

                for key, obj in water_heater_agent_objs.items():
                    if obj.participating:
                        # inform Water heater agent about the cleared real-time price
                        obj.inform_bid_rt(retail_market_obj.cleared_price_RT)

                for key, obj in battery_agent_objs.items():
                    if obj.participating:
                        # inform Battery agent about the cleared real-time price
                        obj.inform_bid(retail_market_obj.cleared_price_RT)

                for key, obj in ev_agent_objs.items():
                    if obj.participating:
                        # inform Electric Vehicle agent about the cleared real-time price
                        obj.inform_bid(retail_market_obj.cleared_price_RT)

            timing(proc[17], True)
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
                        retail_cleared_quantity_RT_unadjusted
                    )
                else:
                    retail_300.append_data(
                        time_granted,
                        retail_market_obj.name,
                        retail_market_obj.cleared_price_RT,
                        retail_market_obj.cleared_quantity_RT,
                        retail_market_obj.clear_type_RT,
                        retail_market_obj.congestion_surcharge_RT,
                        retail_cleared_quantity_RT_unadjusted
                    )
            timing(proc[17], False)
            tnext_retail_clear_rt += retail_period_rt

        if time_granted >= tnext_retail_clear_da:
            log.info("-- retail day-ahead clearing --")
            # clear the retail real-time market
            retail_market_obj.clear_market_DA(dso_market_obj.transformer_degradation, retail_market_obj.Q_max)
            retail_cleared_quantity_DA = retail_market_obj.cleared_quantity_DA
            # print("DA cleared price", retail_market_obj.cleared_price_DA)
            log.info('current day-ahead price -> ' + str(retail_market_obj.cleared_price_DA) + ' $/kWh')
            log.info('current day-ahead quantities -> ' + str(retail_cleared_quantity_DA) + ' kWh')

            retail_market_obj.cleared_quantity_DA_unscaled = []
            for idx in range(retail_market_obj.windowLength):
                retail_market_obj.cleared_quantity_DA_unscaled.append(
                    (retail_market_obj.cleared_quantity_DA[idx] - forecast_load_ind[0]) / scale)

            # log.info('current day-ahead quantity scaled -> ' +
            #          str(np.array(retail_market_obj.cleared_quantity_DA) / 1.0e3) + ' MW')
            # log.info('current day-ahead quantity unscaled -> ' +
            #          str(np.array(retail_market_obj.cleared_quantity_DA_unscaled) / 1.0e3) + ' MW')

            window_rmsd = np.sqrt(np.sum((np.array(retail_market_obj.cleared_price_DA) - np.array(
                retail_market_obj.cleared_price_DA).mean()) ** 2) / 48)
            log.info('current window RMSD --> ' + str(window_rmsd))

            forecast_obj.set_retail_price_forecast(retail_market_obj.cleared_price_DA)
            log.info("price_forecast: " + str(forecast_obj.retail_price_forecast))
            retail_market_obj.update_price_CA(forecast_obj.retail_price_forecast)
            site_da_wh_cleared_quantities = np.zeros([len(site_da_meter), 48], dtype=np.float)
            site_da_hvac_cleared_quantities = np.zeros([len(site_da_meter), 48], dtype=np.float)
            site_da_batt_cleared_quantities = np.zeros([len(site_da_meter), 48], dtype=np.float)
            site_da_ev_cleared_quantities = np.zeros([len(site_da_meter), 48], dtype=np.float)

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

                timing(proc[17], True)
                if write_metrics:
                    # ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
                    hvac_3600.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_da)
                timing(proc[17], False)

            for key, obj in water_heater_agent_objs.items():
                site_id = site_da_meter.index(config_glm['houses'][key]['billingmeter_id'])
                #TODO: In this case House participation was 0 whereas the waterheater participation was 1,
                # so it rightly picks up the cleared quantity,
                # but what to put in the site participation metrics, participating or not participating???
                if obj.participating and with_market:
                    # set the price forecast in the Water heater agent
                    obj.set_price_forecast(forecast_obj.retail_price_forecast)
                    da_cleared_quantity = []
                    for idx in range(obj.windowLength):
                        da_cleared_quantity.append(obj.set_da_cleared_quantity(obj.bid_da[idx], retail_market_obj.cleared_price_DA[idx]))
                    site_da_wh_cleared_quantities[site_id] += np.array(da_cleared_quantity)
                else:
                    site_da_wh_cleared_quantities[site_id] += np.zeros(48)

                timing(proc[17], True)
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
                timing(proc[17], False)

            for key, obj in battery_agent_objs.items():
                site_id = site_da_meter.index(config_glm['inverters'][key]['billingmeter_id'])
                if obj.participating and with_market:
                    # set the price forecast in the Battery agent
                    obj.set_price_forecast(forecast_obj.retail_price_forecast)
                    da_cleared_quantity = []
                    for idx in range(obj.windowLength):
                        da_cleared_quantity.append(obj.from_P_to_Q_battery(obj.bid_da[idx], retail_market_obj.cleared_price_DA[idx]))
                    site_da_batt_cleared_quantities[site_id] += np.array(da_cleared_quantity)
                else:
                    site_da_batt_cleared_quantities[site_id] += np.zeros(48)

                timing(proc[17], True)
                if write_metrics:
                    # ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
                    battery_3600.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_da,
                    )
                timing(proc[17], False)

            for key, obj in ev_agent_objs.items():
                site_id = site_da_meter.index(config_glm['ev'][obj.houseName]['billingmeter_id'])
                if obj.participating and with_market:
                    # set the price forecast in the EV agent
                    obj.set_price_forecast(forecast_obj.retail_price_forecast)
                    da_cleared_quantity = []
                    for idx in range(obj.windowLength):
                        da_cleared_quantity.append(obj.from_P_to_Q_ev(obj.bid_da[idx], retail_market_obj.cleared_price_DA[idx]))
                    site_da_ev_cleared_quantities[site_id] += np.array(da_cleared_quantity)
                else:
                    site_da_ev_cleared_quantities[site_id] += np.zeros(48)

                timing(proc[17], True)
                if write_metrics:
                    # ('bid_four_point_da', [[[retail_unit, '$/' + retail_unit]] * 4] * retail_market_obj.windowLength),
                    ev_3600.append_data(
                        time_granted,
                        obj.name,
                        obj.bid_da,
                    )
                timing(proc[17], False)

            site_da_total_quantities_cleared = site_da_wh_cleared_quantities + site_da_hvac_cleared_quantities + site_da_batt_cleared_quantities + site_da_ev_cleared_quantities
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

            timing(proc[17], True)
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
            timing(proc[17], False)

            tnext_retail_clear_da += retail_period_da

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Agent adjust --------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_retail_adjust_rt:
            if with_market:
                log.info("-- real-time adjusting --")

                for key, obj in hvac_agent_objs.items():
                    # publish the cleared real-time price to HVAC meter
                    publish(obj.name + '/price', retail_market_obj.cleared_price_RT)
                    if obj.participating and obj.bid_accepted(11, current_time):
                        # if HVAC real-time bid is accepted adjust the cooling setpoint in GridLAB-D
                        # if obj.thermostat_mode == 'Cooling':
                        publish(obj.name + '/cooling_setpoint', obj.cooling_setpoint)
                        # elif obj.thermostat_mode == 'Heating':
                        publish(obj.name + '/heating_setpoint', obj.heating_setpoint)
                        # else:
                        #    continue

                    timing(proc[17], True)
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
                            obj.temp_room[0],
                            obj.price_forecast_0
                        )
                    timing(proc[17], False)

                for key, obj in water_heater_agent_objs.items():
                    if obj.participating and obj.bid_accepted(11, current_time):
                        # if Water heater real-time bid is accepted adjust the thermostat setpoint in GridLAB-D
                        water_heater_name = obj.name.replace("hse", "wh")
                        # print("Water_heater name",water_heater_name)
                        publish(water_heater_name + '/lower_tank_setpoint', obj.Setpoint_bottom)
                        publish(water_heater_name + '/upper_tank_setpoint', obj.Setpoint_upper)
                        # print('My published setpoints',obj.Setpoint_bottom, obj.Setpoint_upper)

                    timing(proc[17], True)
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
                            obj.RT_cleared_quantity,
                            obj.bid_da[0][1][0]
                        )
                    timing(proc[17], False)

                for key, obj in battery_agent_objs.items():
                    # publish the cleared real-time price to Battery agent
                    if obj.participating and obj.bid_accepted(current_time):
                        # if Battery real-time bid is accepted adjust the P and Q in GridLAB-D
                        publish(obj.name + '/p_out', obj.inv_P_setpoint)
                        publish(obj.name + '/q_out', obj.inv_Q_setpoint)

                    timing(proc[17], True)
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
                            obj.Cinit/obj.batteryCapacity
                        )
                    timing(proc[17], False)

                for key, obj in ev_agent_objs.items():
                    # publish the cleared real-time price to ev agent
                    if obj.participating and obj.bid_accepted(current_time):
                        # if ev real-time bid is accepted adjust the P and Q in GridLAB-D
                        publish(obj.name + '/ev_out', obj.inv_P_setpoint)
                        # publish(obj.name + '/q_out', obj.inv_Q_setpoint)

                    timing(proc[17], True)
                    if write_metrics:
                        # ('bid_four_point_rt', [[retail_unit, '$/' + retail_unit]] * 4),
                        # ('inverter_p_setpoint', 'W'),
                        # ('battery_soc', '[0-1]'),
                        ev_300.append_data(
                            time_granted,
                            obj.name,
                            obj.bid_rt,
                            obj.inv_P_setpoint,
                            obj.Cinit/obj.evCapacity
                        )
                    timing(proc[17], False)

            tnext_retail_adjust_rt += retail_period_rt

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Write metrics -------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_write_metrics or time_granted >= simulation_duration:
            timing(proc[17], True)
            if write_metrics:
                log.info("-- writing metrics --")
                # write all known metrics to disk
                collector.write_metrics()
            tnext_write_metrics_cnt += 1
            tnext_write_metrics = (metrics_record_interval * tnext_write_metrics_cnt) + 1800
            timing(proc[17], False)

            timing(proc[1], False)
            timing(proc[1], True)
            op = open('timing.csv', 'w')
            print(proc_time, sep=', ', file=op, flush=True)
            print(wall_time, sep=', ', file=op, flush=True)
            op.close()

    log.info('finalizing metrics writing')
    #     # timing(arg.__class__.__name__, True)
    #     # worker_results = arg.DA_optimal_quantities()
    #     # timing(arg.__class__.__name__, False)
    timing(proc[17], True)
    collector.finalize_writing()
    timing(proc[17], False)
    log.info('finalizing HELICS dso federate')
    timing(proc[1], False)
    op = open('timing.csv', 'w')
    print(proc_time, sep=', ', file=op, flush=True)
    print(wall_time, sep=', ', file=op, flush=True)
    op.close()
    helics.helicsFederateDestroy(hFed)


def dso_loop(metrics_root, with_market):
    """Wrapper for *inner_substation_loop*

    When *inner_substation_loop* finishes, timing and memory metrics will be printed
    for non-Windows platforms.
    """
    market = True
    if with_market == 0:
        market = False

    inner_substation_loop(metrics_root, market)

# Code that can be used to profile the substation
#    import cProfile
#    command = """inner_substation_loop(metrics_root, with_market)"""
#    cProfile.runctx(command, globals(), locals(), filename="profile.stats")

    if sys.platform != 'win32':
        usage = resource.getrusage(resource.RUSAGE_SELF)
        resource_names = [
            ('ru_utime', 'User time'),
            ('ru_stime', 'System time'),
            ('ru_maxrss', 'Max. Resident Set Size'),
            ('ru_ixrss', 'Shared Memory Size'),
            ('ru_idrss', 'Unshared Memory Size'),
            ('ru_isrss', 'Stack Size'),
            ('ru_inblock', 'Block inputs'),
            ('ru_oublock', 'Block outputs')]
        print('Resource usage:')
        for name, desc in resource_names:
            print('  {:<25} ({:<10}) = {}'.format(desc, name, getattr(usage, name)))

# for debugging
# dso_loop('Substation_1', 1)