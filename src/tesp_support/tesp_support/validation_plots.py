#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017-2021 Battelle Memorial Institute
"""
Created on Wednesday Feb 24 14:09:43 2021

Reads in resulting data from SGIP1 co-simulation case runs and creates a set of
plots used to validate the performance of the models and co-simulation in
general.

Needs to be run from the same folder as the SGIP results data.

@author: hard312 (Trevor Hardy)
"""

import logging
import pprint
import argparse
import sys
import tesp_support.process_pypower as pp
import tesp_support.process_gld as gp
import tesp_support.process_eplus as ep
import matplotlib.pyplot as plt

# Setting up logging
logger = logging.getLogger(__name__)

# Setting up pretty printing, mostly for debugging.
ppt = pprint.PrettyPrinter(indent=4, )



def load_pypower_data(data, case, data_path):
    '''
    Loads data collected from PYPOWER into data dictionary

    :param data: dictionary of nparrays
    :param case: string case designator used as key in data dict
    :return:
        data: data dict with PYPOWER data added
    '''
    try:
        dict = pp.read_pypower_metrics(data_path, f'SGIP1{case}')
        found_data = True
    except:
        logger.error(f'\tUnable to load PYPOWER data for Case {case}.')
        found_data = False

    data[case]['pypower'] = {}
    data[case]['pypower']['found_data'] = found_data
    if found_data:
        data[case]['pypower']['hrs'] = dict['hrs']
        data[case]['pypower']['data_b'] = dict['data_b']
        data[case]['pypower']['data_g'] = dict['data_g']
        data[case]['pypower']['idx_b'] = dict['idx_b']
        data[case]['pypower']['idx_g'] = dict['idx_g']
        data[case]['pypower']['keys_b'] = dict['keys_b']
        data[case]['pypower']['keys_g'] = dict['keys_g']
        logger.info(f'\tLoaded PYPOWER data for Case {case}.')
    return data

def load_gld_data(data, case, data_path):
    '''
    Loads data collected from GridLAB-D into data dictionary. Not all
    GridLAB-D data is loaded into the dictionary, only that which is needed.

    :param data: dictionary of nparrays
    :param case: string case designator used as key in data dict
    :return:
        data: data dict with PYPOWER data added
    '''

    try:
        dict = gp.read_gld_metrics(data_path, f'SGIP1{case}')
        found_data = True
    except:
        logger.error(f'\tUnable to load GridLAB-D data for Case {case}.')
        found_data = False

    data[case]['gld'] = {}
    data[case]['gld']['found_data'] = found_data
    if found_data:
        data[case]['gld']['hrs'] = dict['hrs']
        data[case]['gld']['data_h'] = dict['data_h']
        data[case]['gld']['keys_h'] = dict['keys_h']
        data[case]['gld']['idx_h'] = dict['idx_h']
        data[case]['gld']['solar_kw'] = dict['solar_kw']
        data[case]['gld']['battery_kw'] = dict['battery_kw']
        logger.info(f'\tLoaded GridLAB-D data for Case {case}.')
    return data


def load_energy_plus_data(data, case, data_path):
    '''
    Loads data collected from Energy+ into data dictionary.

    :param data: dictionary of nparrays
    :param case: string case designator used as key in data dict
    :return:
        data: data dict with PYPOWER data added
    '''

    try:
        dict = ep.read_eplus_metrics(data_path, f'SGIP1{case}')
        found_data = True
    except:
        logger.error(f'\tUnable to load Energy+ data for Case {case}.')
        found_data = False

    data[case]['eplus'] = {}
    data[case]['eplus']['found_data'] = found_data
    if found_data:
        data[case]['eplus']['hrs'] = dict['hrs']
        data[case]['eplus']['data_e'] = dict['data_e']
        data[case]['eplus']['idx_e'] = dict['idx_e']
        logger.info(f'\tLoaded Energy+ data for Case {case}.')
    return data



def load_data(data_path):
    '''
     Loads data from a variety of sources to allow cross-case comparison

    :return:
        data: dictionary of nparrays for use in plotting functions
    '''

    logger.info('Loading processed metrics data')
    data = {}
    cases = ['a', 'b', 'c', 'd', 'e']
    for case in cases:
        data[case] = {}


    # Load PYPOWER data
    for case in cases:
        data = load_pypower_data(data, case, data_path)

    # Load GLD data
    for case in cases:
        data = load_gld_data(data, case, data_path)

    # Load Energy+ data
    for case in cases:
        data = load_energy_plus_data(data, case, data_path)


    return data



def plot_gen_comparison(data):
    '''
    SGIP1(a) output of individual generators vs time. Expect to see dramatic
    change in dispatch on day 2 as a generator goes out.

    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''


    if 'a' in data.keys():
        if 'pypower' in data['a'].keys():
            if data['a']['pypower']['found_data']:
                hrs = data['a']['pypower']['hrs']
                a_data_g = data['a']['pypower']['data_g']
                a_idx_g = data['a']['pypower']['idx_g']
                plt.plot(hrs, a_data_g[0, :, a_idx_g['PGEN_IDX']], color='blue',
                         label='unit 1')
                plt.plot(hrs, a_data_g[1, :, a_idx_g['PGEN_IDX']], color='red', label='unit 2')
                plt.plot(hrs, a_data_g[2, :, a_idx_g['PGEN_IDX']], color='green', label='unit 3')
                plt.plot(hrs, a_data_g[3, :, a_idx_g['PGEN_IDX']], color='magenta', label='unit 4')
                plt.plot(hrs, a_data_g[4, :, a_idx_g['PGEN_IDX']], color='gray', label='unit 5')
                plt.ylabel(a_idx_g['PGEN_UNITS'])
                plt.xlabel('Simulated time (hrs)')
                plt.title('Comparison of Generator Output')
                plt.legend(loc='center left')
                plt.show()
                logger.info('\tCompleted plot_gen_comparison.')
            else:
                logger.error('\tMissing PYPOWER data for Case (a); unable to create '
                             'plot_gen_comparison.')
        else:
            logger.error('\tNo PYPOWER data loaded for Case (a); unable to '
                         'create plot_gen_comparison.')
    else:
        logger.error('\tNo data loaded for Case (a); unable to create '
                     'plot_gen_comparison.')


def plot_transactive_bus_LMP(data):
    '''
    SGIP1(a) and (b) LMP for transactive bus vs time. Expect to see price
    spike on second day as generator goes out; should have lower prices for
    the transactive case (b)

    Bus 7 is the only bus for which data is recorded.
    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''

    if 'a' in data.keys() and 'b' in data.keys():
        if 'pypower' in data['a'].keys() and 'pypower' in data['b'].keys():
            if data['a']['pypower']['found_data'] and \
                    data['b']['pypower']['found_data']:

                a_hrs = data['a']['pypower']['hrs']
                a_data_b = data['a']['pypower']['data_b']
                a_idx_b = data['a']['pypower']['idx_b']
                b_hrs = data['b']['pypower']['hrs']
                b_data_b = data['b']['pypower']['data_b']
                b_idx_b = data['b']['pypower']['idx_b']

                plt.plot(a_hrs, a_data_b[0, :, a_idx_b['LMP_P_IDX']], color='blue',
                         label='Case (a) - Non-transactive', linewidth=1)
                plt.plot(b_hrs, b_data_b[0, :, b_idx_b['LMP_P_IDX']], color='red',
                         label='Case (b) - Transactive', linewidth=1)
                plt.ylabel(a_idx_b['LMP_P_UNITS'])
                plt.xlabel('Simulated time (hrs)')
                plt.title('Comparison of Marginal Price at Bus 7')
                plt.legend(loc='best')
                plt.show()
                logger.info('\tCompleted plot_transactive_bus_LMP.')
            else:
                logger.error('\tMissing PYPOWER data; unable to complete '
                             'plot_transactive_bus_LMP.')
                if (data['a']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (a)')
                if (data['b']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (b)')
        else:
            if 'pypower' not in data['a'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (a); unable '
                             'to complete plot_transactive_bus_LMP')
            if 'pypower' not in data['b'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (b); unable '
                             'to complete plot_transactive_bus_LMP')
    else:
        if 'a' not in data.keys():
            logger.error('\tNo data loaded for Case (a); unable to complete '
                         'plot_transactive_bus_LMP')
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to complete '
                         'plot_transactive_bus_LMP')


def plot_transactive_feeder_load(data):
    '''
    SGIP1(a), and (b) total feeder load vs time. (a) is base and (b) is
    transactive. Expect (b) to show peak-shaving, snapback, and
    valley-filling where (a) does not.

    Bus 7 is the only bus for which data is recorded.
    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''
    if 'a' in data.keys() and 'b' in data.keys():
        if 'pypower' in data['a'].keys() and 'pypower' in data['b'].keys():
            if data['a']['pypower']['found_data'] and data['b']['pypower'][
                'found_data']:

                a_hrs = data['a']['pypower']['hrs']
                a_data_b = data['a']['pypower']['data_b']
                a_idx_b = data['a']['pypower']['idx_b']
                b_hrs = data['b']['pypower']['hrs']
                b_data_b = data['b']['pypower']['data_b']
                b_idx_b = data['b']['pypower']['idx_b']
                fig, ax = plt.subplots()
                ax2 = ax.twinx()
                ln1 = ax.plot(b_hrs, b_data_b[0, :, b_idx_b['PD_IDX']],
                              color='red', label='Case (b) - Transactive')
                ln2 = ax.plot(a_hrs, a_data_b[0, :, a_idx_b['PD_IDX']],
                              color='blue', label='Case (a) - Non-transactive')
                ln3 = ax2.plot(b_hrs, b_data_b[0, :, b_idx_b['LMP_P_IDX']],
                               color='red',
                               label='Case (b) - Transactive Price',
                               linestyle='dashed', linewidth=1)
                ax.set_ylabel(a_idx_b['PD_UNITS'])
                ax2.set_ylabel(b_idx_b['LMP_P_UNITS'])
                ax.set_xlabel('Simulated time (hrs)')
                lns = ln1 + ln2 + ln3
                labels = [l.get_label() for l in lns]
                plt.title('Comparison of Total Load at Bus 7')
                ax.legend(lns, labels, loc='lower left')
                plt.show()
                logger.info('\tCompleted plot_transactive_feeder_load.')
            else:
                logger.error('\tMissing PYPOWER data; unable to complete '
                             'plot_transactive_feeder_load.')
                if (data['a']['pypower']['found_data']) == False:
                    logger.error('\tMissing data for Case (a)')
                if (data['b']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (b)')
        else:
            if 'pypower' not in data['a'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (a); unable '
                             'to complete plot_transactive_feeder_load.')
            if 'pypower' not in data['b'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (b); unable '
                             'to complete plot_transactive_feeder_load.')
    else:
        if 'a' not in data.keys():
            logger.error('\tNo data loaded for Case (a); unable to complete '
                         'plot_transactive_feeder_load.')
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to complete '
                         'plot_transactive_feeder_load.')

def plot_transactive_feeder_load_solar(data):
    '''
    SGIP1a, b, c, d, e transactive total feeder load vs time. (a) is base
    and (b)-(e) are transactive with increasing amounts of solar and energy
    storage systems. Expect to see decreasing daytime loads with increasing
    solar penetration ((b) to (e)).

    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''
    if 'b' in data.keys() and 'c' in data.keys() and 'd' in data.keys() and \
            'e' in data.keys():
        if 'pypower' in data['b'].keys() and 'pypower' in data['c'].keys() \
                and 'pypower' in data['d'].keys() and 'pypower' in data[
            'e'].keys():

            if data['b']['pypower']['found_data'] and \
                data['c']['pypower']['found_data'] and \
                data['d']['pypower']['found_data'] and \
                data['e']['pypower']['found_data']:

                b_hrs = data['b']['pypower']['hrs']
                b_data_b = data['b']['pypower']['data_b']
                b_idx_b = data['b']['pypower']['idx_b']
                c_hrs = data['c']['pypower']['hrs']
                c_data_b = data['c']['pypower']['data_b']
                c_idx_b = data['c']['pypower']['idx_b']
                d_hrs = data['d']['pypower']['hrs']
                d_data_b = data['d']['pypower']['data_b']
                d_idx_b = data['d']['pypower']['idx_b']
                e_hrs = data['e']['pypower']['hrs']
                e_data_b = data['e']['pypower']['data_b']
                e_idx_b = data['e']['pypower']['idx_b']

                plt.plot(b_hrs, b_data_b[0, :, b_idx_b['PD_IDX']], color='red',
                         label='Case (b) - 0 PV/ES systems')
                plt.plot(c_hrs, c_data_b[0, :, c_idx_b['PD_IDX']], color='green',
                         label='Case (c) - 159/82 PV/ES systems')
                plt.plot(d_hrs, d_data_b[0, :, d_idx_b['PD_IDX']], color='magenta',
                         label='Case (d) - 311/170 PV/ES systems')
                plt.plot(e_hrs, e_data_b[0, :, e_idx_b['PD_IDX']], color='gray',
                         label='Case (e) - 464/253 PV/ES systems')
                plt.ylabel(b_idx_b['PD_UNITS'])
                plt.xlabel('Simulated time (hrs)')
                plt.title('Comparison of Total Load at Bus 7')
                plt.legend(loc='lower left')
                plt.show()
                logger.info('\tCompleted plot_transactive_feeder_load_solar.')
            else:
                logger.error('\tMissing PYPOWER data; unable to complete '
                             'plot_transactive_feeder_load_solar')
                if (data['b']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (b)')
                if (data['c']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (c)')
                if (data['d']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (d)')
                if (data['e']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (e)')
        else:
            if 'pypower' not in data['b'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (b); unable '
                             'to '
                             'complete plot_transactive_feeder_load_solar.')
            if 'pypower' not in data['c'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (c); unable '
                             'to complete plot_transactive_feeder_load_solar.')
            if 'pypower' not in data['d'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (d); unable '
                             'to complete plot_transactive_feeder_load_solar.')
            if 'pypower' not in data['e'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (e); unable '
                             'to compelte plot_transactive_feeder_load_solar.')
    else:
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to '
                         'complete plot_transactive_feeder_load_solar.')
        if 'c' not in data.keys():
            logger.error('\tNo data loaded for Case (c); unable to complete '
                         'plot_transactive_feeder_load_solar.')
        if 'd' not in data.keys():
            logger.error('\tNo data loaded for Case (d); unable to complete '
                         'plot_transactive_feeder_load_solar.')
        if 'e' not in data.keys():
            logger.error('\tNo data loaded for Case (e); unable to complete '
                         'plot_transactive_feeder_load_solar.')


def plot_avg_indoor_air_temperature(data):
    '''
    SGIP1(a) and (b) all residential customer average indoor temperature
    vs time. SGIP1(a) is base and (b) is transactive. Expect to see
    constant temperatures for (a) and higher temperatures for (b) on the
    second day with the generator outage while (a) is unaffected.

    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''
    if 'a' in data.keys() and 'b' in data.keys():
        if 'gld' in data['a'].keys() and 'gld' in data['b'].keys() and \
                'pypower' in data['a'].keys():
            if data['a']['gld']['found_data'] and \
                data['b']['gld']['found_data']:

                a_hrs = data['a']['gld']['hrs']
                a_data_h = data['a']['gld']['data_h']
                a_keys_h = data['a']['gld']['keys_h']
                a_idx_h = data['a']['gld']['idx_h']

                b_hrs = data['b']['gld']['hrs']
                b_data_h = data['b']['gld']['data_h']
                b_keys_h = data['b']['gld']['keys_h']
                b_idx_h = data['b']['gld']['idx_h']

                bp_hrs = data['b']['pypower']['hrs']
                bp_data_b = data['b']['pypower']['data_b']
                bp_idx_b = data['b']['pypower']['idx_b']

                a_avg = (a_data_h[:,:,a_idx_h['HSE_AIR_AVG_IDX']]).squeeze()
                a_avg2 = a_avg.mean(axis=0)
                b_avg = (b_data_h[:,:,b_idx_h['HSE_AIR_AVG_IDX']]).squeeze()
                b_avg2 = b_avg.mean(axis=0)

                fig, ax = plt.subplots()
                ax2 = ax.twinx()
                ln1 = ax.plot(a_hrs, a_avg2, color='blue', label='Case (a) - '
                                                           'Non-Transactive')
                ln2 = ax.plot(b_hrs, b_avg2, color='red', label='Case (b) - '
                                                         'Transactive')
                ln3 = ax2.plot(bp_hrs, bp_data_b[0, :, bp_idx_b['LMP_P_IDX']],
                        color='red', label='Case (b) - Transactive Price',
                               linestyle='dashed', linewidth=1)
                ax.set_ylabel(a_idx_h['HSE_AIR_AVG_UNITS'])
                ax2.set_ylabel(bp_idx_b['LMP_P_UNITS'])
                ax.set_xlabel('Simulated time (hrs)')
                lns = ln1 + ln2 + ln3
                labels = [l.get_label() for l in lns]
                plt.title('Comparison of Residential Indoor Temperatures')
                ax.legend(lns, labels, loc='upper left')
                plt.show()
                logger.info('\tCompleted plot_avg_indoor_air_temperature.')
            else:
                logger.error('\tMissing GridLAB-D or PYPOWER data; unable to '
                             'complete plot_avg_indoor_air_temperature.')
                if (data['a']['gld']['found_data']) == False:
                    logger.error('\t\tMissing GridLAB-D data for Case (a)')
                if (data['b']['gld']['found_data']) == False:
                    logger.error('\t\tMissing GridLAB-D data for Case (b)')
                if (data['b']['pypower']['found_data']) == False:
                    logger.error('\t\tMissing PYPOWER data for Case (b)')
        else:
            if 'gld' not in data['a'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (a); '
                             'unable to complete '
                             'plot_avg_indoor_air_temperature.')
            if 'gld' not in data['b'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (b); '
                             'unable to complete '
                             'plot_avg_indoor_air_temperature.')
            if 'pypower' not in data['b'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (b); '
                             'unable to complete '
                             'plot_avg_indoor_air_temperature.')
    else:
        if 'a' not in data.keys():
            logger.error('\tNo data loaded for Case (a); unable to complete '
                         'plot_avg_indoor_air_temperature')
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to comlpete '
                         'plot_avg_indoor_air_temperature')


def plot_solar_output(data):
    '''
    SGIP1b-e total solar PV output vs time. Expect to see increasing total
    output in moving from (b) to (e).

    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''

    if 'b' in data.keys() and 'c' in data.keys() and 'd' in data.keys() and \
            'e' in data.keys():
        if 'gld' in data['b'].keys() and 'gld' in data['c'].keys() and \
             'gld' in data['d'].keys() and 'gld' in data['e'].keys():

            if data['b']['gld']['found_data'] and \
                data['c']['gld']['found_data'] and \
                data['d']['gld']['found_data'] and \
                data['e']['gld']['found_data']:

                b_hrs = data['b']['gld']['hrs']
                b_solar_kw = data['b']['gld']['solar_kw']
                c_hrs = data['c']['gld']['hrs']
                c_solar_kw = data['c']['gld']['solar_kw']
                d_hrs = data['d']['gld']['hrs']
                d_solar_kw = data['d']['gld']['solar_kw']
                e_hrs = data['e']['gld']['hrs']
                e_solar_kw = data['e']['gld']['solar_kw']

                plt.plot(b_hrs, b_solar_kw, color='red', label='Case (b) - 0 PV systems')
                plt.plot(c_hrs, c_solar_kw, color='green', label='Case (c) - 159 PV '
                                                                'systems')
                plt.plot(d_hrs, d_solar_kw, color='magenta', label='Case (d) - 311 PV '
                                                                  'systems')
                plt.plot(e_hrs, e_solar_kw, color='gray', label='Case (e) - 464 PV '
                                                                'systems')
                plt.ylabel('kW')
                plt.xlabel('Simulated time (hrs)')
                plt.title('Comparison of Total Residential PV Output')
                plt.legend(loc='lower left')
                plt.show()
                logger.info('\tCompleted plot_solar_output.')
            else:
                logger.error('\tMissing GridLAB-D data; unable to complete '
                             'plot_solar_output')
                if (data['b']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (b)')
                if (data['c']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (c)')
                if (data['d']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (d)')
                if (data['e']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (e)')
        else:
            if 'gld' not in data['b'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (b); unable '
                             'to complete plot_solar_output')
            if 'gld' not in data['c'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (c); unable '
                             'to complete plot_solar_output.')
            if 'gld' not in data['d'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (d); unable '
                             'to comeplete plot_solar_output.')
            if 'gld' not in data['e'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (e); unable '
                             'to complete plot_solar_output.')
    else:
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to complete '
                         'plot_solar_output;')
        if 'c' not in data.keys():
            logger.error('\tNo data loaded for Case (c); unable to complete '
                         'plot_solar_output.')
        if 'd' not in data.keys():
            logger.error('\tNo data loaded for Case (d); unable to complete '
                         'plot_solar_output.')
        if 'e' not in data.keys():
            logger.error('\tNo data loaded for Case (e); unable to complete '
                         'plot_solar_output.')

def plot_ES_output(data):
    '''
    SGIP1(a) and (b) Energy+ average indoor cooling temperature vs time.
    Expect to case (b) to show higher temperatures as it is
    price-responsive.

    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''
    if 'b' in data.keys() and 'c' in data.keys() and 'd' in data.keys() and \
            'e' in data.keys():
        if 'gld' in data['b'].keys() and 'gld' in data['c'].keys() and \
             'gld' in data['d'].keys() and 'gld' in data['e'].keys():

            if data['b']['gld']['found_data'] and \
                data['c']['gld']['found_data'] and \
                data['d']['gld']['found_data'] and \
                data['e']['gld']['found_data']:

                b_hrs = data['b']['gld']['hrs']
                b_battery_kw = data['b']['gld']['battery_kw']
                c_hrs = data['c']['gld']['hrs']
                c_battery_kw = data['c']['gld']['battery_kw']
                d_hrs = data['d']['gld']['hrs']
                d_battery_kw = data['d']['gld']['battery_kw']
                e_hrs = data['e']['gld']['hrs']
                e_battery_kw = data['e']['gld']['battery_kw']

                plt.plot(b_hrs, b_battery_kw, color='red', label='Case (b) - 0 ES '
                                                        'systems')
                plt.plot(c_hrs, c_battery_kw, color='green', label='Case (c) - 82 ES '
                                                        'systems')
                plt.plot(d_hrs, d_battery_kw, color='magenta', label='Case ('
                                                        'd) - 170 ES systems')
                plt.plot(e_hrs, e_battery_kw, color='gray', label='Case (e) '
                                                        '- 253 ES systems')
                plt.ylabel('kW')
                plt.xlabel('Simulated time (hrs)')
                plt.title('Comparison of Total Residential ES Output')
                plt.legend(loc='lower right')
                plt.show()
                logger.info('\tCompleted plot_ES_output.')
            else:
                logger.error('\tMissing GridLAB-D data; unable to complete '
                             'plot_ES_output')
                if (data['b']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (b)')
                if (data['c']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (c)')
                if (data['d']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (d)')
                if (data['e']['gld']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (e)')
        else:
            if 'gld' not in data['b'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (b); '
                             'unable to complete plot_ES_output.')
            if 'gld' not in data['c'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (c); '
                             'unable to complete plot_ES_output.')
            if 'gld' not in data['d'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (d) '
                             'unable to complete plot_ES_output.')
            if 'gld' not in data['e'].keys():
                logger.error('\tNo GridLAB-D data loaded for Case (e); '
                             'unable to complete plot_ES_output.')
    else:
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to complete '
                         'plot_ES_output.')
        if 'c' not in data.keys():
            logger.error('\tNo data loaded for Case (c); unable to complete '
                         'plot_ES_output.')
        if 'd' not in data.keys():
            logger.error('\tNo data loaded for Case (d); unable to complete '
                         'plot_ES_output.')
        if 'e' not in data.keys():
            logger.error('\tNo data loaded for Case (e); unable to complete '
                         'plot_ES_output.')

def plot_energy_plus_indoor_temperature(data):
    '''
    SGIP1b-e total solar PV output vs time. Expect to see increasing total
    output in moving from (b) to (e).

    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''
    if 'a' in data.keys() and 'b' in data.keys():
        if 'eplus' in data['a'].keys() and 'eplus' in data['b'].keys() and \
                'pypower' in data['b'].keys():
            if data['a']['eplus']['found_data'] and \
                data['b']['eplus']['found_data']:

                a_hrs = data['a']['eplus']['hrs']
                a_data = data['a']['eplus']['data_e']
                a_idx = data['a']['eplus']['idx_e']
                b_hrs = data['b']['eplus']['hrs']
                b_data = data['b']['eplus']['data_e']
                b_idx = data['b']['eplus']['idx_e']
                bp_hrs = data['b']['pypower']['hrs']
                bp_data_b = data['b']['pypower']['data_b']
                bp_idx_b = data['b']['pypower']['idx_b']

                fig, ax = plt.subplots()
                ax2 = ax.twinx()
                ln2 = ax.plot(b_hrs, b_data[:,b_idx[
                                                  'COOLING_TEMPERATURE_IDX']],
                         color='red', label='Case (b) - Transactive')
                ln1 = ax.plot(a_hrs, a_data[:,a_idx[
                                                  'COOLING_TEMPERATURE_IDX']],
                         color='blue', label='Case (a) - Non-transactive')
                ln3 = ax2.plot(bp_hrs, bp_data_b[0, :, bp_idx_b['LMP_P_IDX']],
                        color='red', label='Case (b) - Transactive Price',
                               linestyle='dashed', linewidth=1)
                ax.set_ylabel(a_idx['COOLING_TEMPERATURE_UNITS'])
                ax2.set_ylabel(bp_idx_b['LMP_P_UNITS'])
                ax.set_xlabel('Simulated time (hrs)')
                lns = ln1 + ln2 + ln3
                labels = [l.get_label() for l in lns]
                plt.title('Comparison of Commercial Building Indoor Temperature')
                ax.legend(lns, labels, loc='center left')
                plt.show()
                logger.info('\tCompleted plot_energy_plus_indoor_temperature.')
            else:
                logger.error('\tMissing Energy+ data; unable to complete '
                             'plot_energy_plus_indoor_temperature.')
                if (data['a']['eplus']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (a)')
                if (data['b']['eplus']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (b)')
        else:
            if 'eplus' not in data['a'].keys():
                logger.error('\tNo Energy+ data loaded for Case (a); unable '
                             'to complete '
                             'plot_energy_plus_indoor_temperature.')
            if 'eplus' not in data['b'].keys():
                logger.error('\tNo Energy+ data loaded for Case (b); unable '
                             'to complete '
                             'plot_energy_plus_indoor_temperature.')
            if 'pypower' not in data['b'].keys():
                logger.error('\tNo PYPOWER data loaded for Case (b); unable '
                             'to complete '
                             'plot_energy_plus_indoor_temperature.')
    else:
        if 'a' not in data.keys():
            logger.error('\tNo data loaded for Case (a); unable to complete '
                         'plot_energy_plus_indoor_temperature.')
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to complete '
                         'plot_energy_plus_indoor_temperature.')

def plot_energy_plus_prices(data):
    '''
    SGIP1b-e total solar PV output vs time. Expect to see increasing total
    output in moving from (b) to (e).

    :param data: Data dictionary with necessary data for creating plot
    :return:
    '''
    if 'a' in data.keys() and 'b' in data.keys():
        if 'eplus' in data['a'].keys() and 'eplus' in data['b'].keys():
            if data['a']['eplus']['found_data'] and \
                data['b']['eplus']['found_data']:

                a_hrs = data['a']['eplus']['hrs']
                a_data = data['a']['eplus']['data_e']
                a_idx = data['a']['eplus']['idx_e']
                b_hrs = data['b']['eplus']['hrs']
                b_data = data['b']['eplus']['data_e']
                b_idx = data['b']['eplus']['idx_e']

                plt.plot(a_hrs, a_data[:,a_idx['PRICE_IDX']], color='blue',
                         label='Case (a) - Non-transactive')
                plt.plot(a_hrs, b_data[:,b_idx['PRICE_IDX']], color='red',
                         label='Case (b) - Transactive')
                plt.ylabel(a_idx['PRICE_UNITS'])
                plt.xlabel('Simulated time (hrs)')
                plt.title('Comparison of Commercial Building Real-Time Energy Price')
                plt.legend(loc='best')
                plt.show()
                logger.info('\tCompleted plot_energy_plus_prices.')
            else:
                logger.error('\tMissing Energy+ data; unable to complete '
                             'plot_energy_plus_prices.')
                if (data['a']['eplus']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (a)')
                if (data['b']['eplus']['found_data']) == False:
                    logger.error('\t\tMissing data for Case (b)')
        else:
            if 'eplus' not in data['a'].keys():
                logger.error('\tNo Energy+ data loaded for Case (a); unable '
                             'to complete plot_energy_plus_prices.')
            if 'eplus' not in data['b'].keys():
                logger.error('\tNo Energy+ data loaded for Case (b); unable '
                             'to complete plot_energy_plus_prices.')
    else:
        if 'a' not in data.keys():
            logger.error('\tNo data loaded for Case (a); unable to complete '
                         'plot_energy_plus_prices.')
        if 'b' not in data.keys():
            logger.error('\tNo data loaded for Case (b); unable to complete '
                         'plot_energy_plus_prices.')

########################################################################
# SGIP1(a) and (b) Energy+ average indoor cooling temperature vs time.
# Expect to case (b) to show higher temperatures as it is
# price-responsive.
########################################################################

# try:
#     a_dict = ep.read_eplus_metrics('SGIP1a')
# except:
#     print('Energy+ data for SGIP1a not found.')
#
# hrs = a_dict['hrs']
#
# a_data = a_dict['data_e']
# a_idx = a_dict['idx_e']
#
# try:
#     b_dict = ep.read_eplus_metrics('SGIP1b')
# except:
#     print('Energy+ data for SGIP1b not found.')
#
# b_data = b_dict['data_e']
# b_idx = b_dict['idx_e']
#
# plt.plot(hrs, a_data[:,a_idx['COOLING_TEMPERATURE_IDX']], color='blue',
#          label='Case (a) - Non-transactive')
# plt.plot(hrs, b_data[:,b_idx['COOLING_TEMPERATURE_IDX']], color='red',
#          label='Case (b) - Transactive')
# plt.ylabel(a_idx['COOLING_TEMPERATURE_UNITS'])
# plt.title('Comparison of Commercial Building Indoor Temperature')
# plt.legend(loc='best')
# plt.show()
#
# plt.plot(hrs, a_data[:,a_idx['PRICE_IDX']], color='blue',
#          label='Case (a) - Non-transactive')
# plt.plot(hrs, b_data[:,b_idx['PRICE_IDX']], color='red',
#          label='Case (b) - Transactive')
# plt.ylabel(a_idx['PRICE_UNITS'])
# plt.title('Comparison of Commercial Building Real-Time Energy Price')
# plt.legend(loc='best')
# plt.show()



def create_validation_plots(data):
    logger.info('Creating plots')
    plot_gen_comparison(data)
    plot_transactive_bus_LMP(data)
    plot_transactive_feeder_load(data)
    plot_transactive_feeder_load_solar(data)
    plot_avg_indoor_air_temperature(data)
    plot_solar_output(data)
    plot_ES_output(data)
    plot_energy_plus_indoor_temperature(data)
    plot_energy_plus_prices(data)










########################################################################
# [SGIP1(b) LMP, SGIP1(b) average indoor temperature of responsive
# residential customers, SGIP1b average indoor temperature of unresponsive
# residential customers] vs time. Expect to see indoor temperature increase
# with increasing prices for price-responsive customers and stay largely
# unaffected for non-price-responsive customers.
#
# May not be possible due to lack of metadata about which customers are
#   participating
########################################################################








def _auto_run(args):
    data = load_data(args.data_path)
    create_validation_plots(data)

if __name__ == '__main__':
    # TDH: This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in trouble-shooting.
    fileHandle = logging.FileHandler("SGIP_validation.log", mode='w')
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.INFO,
                        handlers=[fileHandle, streamHandle])

    parser = argparse.ArgumentParser(description='data path.')
    parser.add_argument('-p',
                        '--data_path',
                        nargs='?',
                        default='/Users/hard312/testbeds/TESP_SGIP1_plots'
                                '/simulation data/sgip1 case 3')
    args = parser.parse_args()
    _auto_run(args)

