# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: dso_agent.py
"""Manages the Transactive Control scheme for DSO+T implementation version 1

Public Functions:
    :substation_loop: initializes and runs the agents

"""

import json
import logging as log
import time
from datetime import datetime, timedelta

import helics as h
import numpy as np
from joblib import Parallel

import tesp_support.consensus.substation as consensus
from .dso_market import DSOMarket
from .retail_market import RetailMarket
from tesp_support.api.helpers import enable_logging
from tesp_support.api.metrics_collector import MetricsStore, MetricsCollector

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
    # with open(metrics_root + "_glm_dict.json", 'r', encoding='utf-8') as gp:
    #     config_glm = json.load(gp)

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
            topic_map['gld_load'] = [dso_market_obj.set_total_load]
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

    # adding the metrics collector object
    write_metrics = (config['MetricsInterval'] > 0)
    if write_metrics:
        write_h5 = (config['MetricsType'] == 'h5')
        collector = MetricsCollector.factory(start_time=start_time, write_hdf5=write_h5)

        name_units_pairs_da_list = [
            ('curve_dso_da_quantities', [[dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
            ('curve_dso_da_prices', [['$/' + dso_unit] * dso_market_obj.num_samples] * dso_market_obj.windowLength),
            ('trial_clear_type_da',
             ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * dso_market_obj.windowLength),
            ('trial_cleared_price_da', ['$/' + dso_unit] * dso_market_obj.windowLength),
            ('trial_cleared_quantity_da', [dso_unit] * dso_market_obj.windowLength),
        ]
        for gen in config['generators']:
            name_units_pairs_da_list.append(('trial_cleared_price_da_' + config['generators'][gen]['name'],
                                             ['$/' + dso_unit] * dso_market_obj.windowLength))
            name_units_pairs_da_list.append(('trial_cleared_quantity_da_' + config['generators'][gen]['name'],
                                             [dso_unit] * dso_market_obj.windowLength))

        dso_3600 = MetricsStore(
            name_units_pairs=name_units_pairs_da_list,
            file_string='dso_market_{}_3600'.format(metrics_root),
            collector=collector,
        )

        name_units_pairs_rt_list = [
            ('curve_dso_rt_quantities', [dso_unit] * dso_market_obj.num_samples),
            ('curve_dso_rt_prices', ['$/' + dso_unit] * dso_market_obj.num_samples),
            ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
            ('cleared_price_rt', '$/' + dso_unit),
            ('cleared_quantity_rt', dso_unit),
        ]
        for gen in config['generators']:
            name_units_pairs_rt_list.append(('cleared_price_rt_' + config['generators'][gen]['name'], '$/' + dso_unit))
            name_units_pairs_rt_list.append(('cleared_quantity_rt_' + config['generators'][gen]['name'], dso_unit))

        dso_300 = MetricsStore(
            name_units_pairs=name_units_pairs_rt_list,
            file_string='dso_market_{}_300'.format(metrics_root),
            collector=collector,
        )
        #                 'dso_rt_gld_load': {'units': load_recording_unit, 'index': 5},
        #                 'dso_rt_industrial_load': {'units': load_recording_unit, 'index': 6},
        #                 'dso_rt_ercot_load': {'units': load_recording_unit, 'index': 7}}

        # if retail_full_metrics:
        #     retail_3600 = MetricsStore(
        #         name_units_pairs=[
        #             ('curve_buyer_da_quantities', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
        #             ('curve_buyer_da_prices', [['$/' + retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
        #             ('curve_seller_da_quantities', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
        #             ('curve_seller_da_prices', [[retail_unit] * retail_market_obj.num_samples] * retail_market_obj.windowLength),
        #             ('cleared_price_da', ['$/' + retail_unit] * retail_market_obj.windowLength),
        #             ('cleared_quantity_da', [retail_unit] * retail_market_obj.windowLength),
        #             ('clear_type_da', ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * retail_market_obj.windowLength),
        #             ('congestion_surcharge_DA', ['$/' + retail_unit] * retail_market_obj.windowLength),
        #         ],
        #         file_string='retail_market_{}_3600'.format(metrics_root),
        #         collector=collector,
        #     )
        # else:
        #     retail_3600 = MetricsStore(
        #         name_units_pairs=[
        #             ('cleared_price_da', ['$/' + retail_unit] * retail_market_obj.windowLength),
        #             ('cleared_quantity_da', [retail_unit] * retail_market_obj.windowLength),
        #             ('clear_type_da', ['[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'] * retail_market_obj.windowLength),
        #             ('congestion_surcharge_DA', ['$/' + retail_unit] * retail_market_obj.windowLength),
        #         ],
        #         file_string='retail_market_{}_3600'.format(metrics_root),
        #         collector=collector,
        #     )

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

        # if retail_full_metrics:
        #     retail_300 = MetricsStore(
        #         name_units_pairs=[
        #             ('curve_buyer_rt_quantities', [retail_unit] * retail_market_obj.windowLength),
        #             ('curve_buyer_rt_prices', ['$/' + retail_unit] * retail_market_obj.windowLength),
        #             ('curve_seller_rt_quantities', [retail_unit] * retail_market_obj.windowLength),
        #             ('curve_seller_rt_prices', ['$/' + retail_unit] * retail_market_obj.windowLength),
        #             ('cleared_price_rt', '$/' + retail_unit),
        #             ('cleared_quantity_rt', retail_unit),
        #             ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
        #             ('congestion_surcharge_RT', '$/' + retail_unit),
        #         ],
        #         file_string='retail_market_{}_300'.format(metrics_root),
        #         collector=collector,
        #     )
        # else:
        #     retail_300 = MetricsStore(
        #         name_units_pairs=[
        #             ('cleared_price_rt', '$/' + retail_unit),
        #             ('cleared_quantity_rt', retail_unit),
        #             ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),
        #             ('congestion_surcharge_RT', '$/' + retail_unit),
        #         ],
        #         file_string='retail_market_{}_300'.format(metrics_root),
        #         collector=collector,
        #     )

    # initialize HELICS
    fed, fed_name = register_federate(metrics_root + '.json')
    status = h.helicsFederateEnterInitializingMode(fed)
    status = h.helicsFederateEnterExecutingMode(fed)
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

    tnext_wholesale_clear_rt = retail_period_rt + 86400  # at a whole day + period
    tnext_dso_clear_rt = retail_period_rt + retail_period_da * 1
    tnext_dso_clear_da = retail_period_da
    tnext_retail_clear_da = retail_period_da
    tnext_retail_clear_rt = retail_period_rt + retail_period_da * 1
    tnext_retail_adjust_rt = retail_period_rt + retail_period_da * 1
    consensus_DA_horizon = 24  # DA horizon in hours

    time_granted = -1  # is midnite always
    time_last = 0
    forecast_rt = 0  # this is a new realtime forecast, which is an interpolated value
    load_base = 0
    load_diff = 0
    timing(proc[0], False)

    timing(proc[1], True)

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

    dso_market_obj.Qmax = {}
    dso_market_obj.Qmax = config['size']

    # dso_market_obj.generators = {}
    # dso_market_obj.generators = config['generators']
    # for key in dso_market_obj.generators:
    #     dso_market_obj.generators[key]['cleared_price_DA'] = np.zeros((dso_market_obj.windowLength)).tolist()
    #     dso_market_obj.generators[key]['cleared_quantity_DA'] = np.zeros((dso_market_obj.windowLength)).tolist()
    #     dso_market_obj.generators[key]['cleared_price_RT'] = 0
    #     dso_market_obj.generators[key]['cleared_quantity_RT'] = 0

    while time_granted < simulation_duration:
        # determine the next HELICS time
        timing(proc[10], True)
        if with_market:
            next_fncs_time = int(
                min([tnext_dso_bid_da, tnext_dso_bid_rt, tnext_dso_clear_da, tnext_dso_clear_rt, tnext_retail_adjust_rt,
                     simulation_duration]))
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
            billing_set_defaults = False

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ DSO clearing --------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_dso_bid_rt:
            log.info("-- dso real-time bidding --")
            dso_market_obj.cleared_q_rt = dso_market_obj.trial_cleared_quantity_RT
            dso_market_obj.clean_bids_RT()
            # ----------------------------------------------------------------------------------------------------
            # ------------------------------------ Consensus Market RT -------------------------------------------
            # ----------------------------------------------------------------------------------------------------
            log.info("-- dso real-time market --")
            time_to_complete_market_RT = time_granted + 15
            dso_market_obj, time_granted = consensus.Consenus_dist_RT(dso_market_obj, fed, hour_of_day,
                                                                      time_granted, time_to_complete_market_RT)
            tnext_dso_bid_rt += retail_period_rt

        if time_granted >= tnext_dso_bid_da:
            log.info("-- dso day-ahead market --")
            dso_market_obj.cleared_q_da = dso_market_obj.trial_cleared_quantity_DA
            dso_market_obj.clean_bids_DA()
            # ----------------------------------------------------------------------------------------------------
            # ------------------------------------ Consensus Market DA -------------------------------------------
            # ----------------------------------------------------------------------------------------------------
            time_to_complete_market_DA = time_granted + 15
            dso_market_obj, time_granted = consensus.Consenus_dist_DA(dso_market_obj, 24, fed, hour_of_day,
                                                                      time_granted, time_to_complete_market_DA)
            tnext_dso_bid_da += retail_period_da

        if time_granted >= tnext_dso_clear_da:
            log.info("-- dso day-ahead clearing --")

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

                list_metric_data_da = [dso_curve_da_quantities,
                                       dso_curve_da_prices,
                                       dso_market_obj.trial_clear_type_DA,
                                       dso_market_obj.Pwclear_DA,
                                       dso_market_obj.trial_cleared_quantity_DA]

                # for gen in dso_market_obj.generators:
                #     list_metric_data_da.append(dso_market_obj.generators[gen]['cleared_price_DA'])
                #     list_metric_data_da.append(dso_market_obj.generators[gen]['cleared_quantity_DA'])

                dso_3600.append_data(time_granted, dso_market_obj.name, *list_metric_data_da)

                # dso_3600.append_data(
                #     time_granted,
                #     dso_market_obj.name,
                #     dso_curve_da_quantities,
                #     dso_curve_da_prices,
                #     dso_market_obj.Pwclear_DA,
                #     dso_market_obj.trial_cleared_quantity_DA,
                #     dso_market_obj.trial_clear_type_DA,
                # )

            tnext_dso_clear_da += retail_period_da

        if time_granted >= tnext_dso_clear_rt:
            log.info("-- dso real-time clearing --")

            log.info(str(dso_market_obj.Pwclear_RT))

            if write_metrics:
                # ('curve_dso_rt_quantities', [dso_unit] * dso_market_obj.windowLength),
                # ('curve_dso_rt_prices', ['$/' + dso_unit] * dso_market_obj.windowLength),
                # ('cleared_price_rt', '$/' + dso_unit),
                # ('cleared_quantity_rt', dso_unit),
                # ('clear_type_rt', '[0..3]=[UNCONGESTED,CONGESTED,INEFFICIENT,FAILURE]'),

                list_metric_data_rt = [dso_market_obj.curve_DSO_RT.quantities,
                                       dso_market_obj.curve_DSO_RT.prices,
                                       dso_market_obj.trial_clear_type_RT,
                                       dso_market_obj.Pwclear_RT,
                                       dso_market_obj.trial_cleared_quantity_RT]

                # for gen in dso_market_obj.generators:
                #     list_metric_data_rt.append(dso_market_obj.generators[gen]['cleared_price_RT'])
                #     list_metric_data_rt.append(dso_market_obj.generators[gen]['cleared_quantity_RT'])

                dso_300.append_data(time_granted, dso_market_obj.name, *list_metric_data_rt)

                # dso_300.append_data(
                #     time_granted,
                #     dso_market_obj.name,
                #     list(dso_market_obj.curve_DSO_RT.quantities),
                #     list(dso_market_obj.curve_DSO_RT.prices),
                #     dso_market_obj.Pwclear_RT[0],
                #     dso_market_obj.trial_cleared_quantity_RT[0],
                #     dso_market_obj.Pwclear_RT[1],
                #     dso_market_obj.trial_cleared_quantity_RT[1],
                #     dso_market_obj.Pwclear_RT[2],
                #     dso_market_obj.trial_cleared_quantity_RT[2],
                #     dso_market_obj.trial_clear_type_RT,
                # )

            tnext_dso_clear_rt += retail_period_rt

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Agent adjust --------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_retail_adjust_rt and with_market:
            log.info("-- real-time adjusting --")
            # ### Publish using HELICS ####
            pub_count = h.helicsFederateGetPublicationCount(fed)
            # Sending cleared values to all the GridLAB-D DGs via HELICS.
            # if pub_count>0:
            #     for key in dso_market_obj.generators:
            #         per_phase_generation = -1*dso_market_obj.generators[key]['cleared_quantity_RT']/3
            #         for wTopic in ['constant_power_A', 'constant_power_B', 'constant_power_C']:
            #             key_gen = dso_market_obj.generators[key]['name'] + '/' + wTopic
            #             pub_gen_quantity = h.helicsFederateGetPublication(fed, key_gen)
            #             status = h.helicsPublicationPublishComplex(pub_gen_quantity, per_phase_generation*1000, 0)
            # print(pub_gen_quantity, string_per_phase_generation)

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
