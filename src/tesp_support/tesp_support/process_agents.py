#   Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_agents.py
"""Functions to plot data from GridLAB-D substation agents

Public Functions:
        :process_agents: Reads the data and metadata, then makes the plots.  

"""
import json
import logging
import os

import numpy as np
import matplotlib.pyplot as plt

# Setting up logging
logger = logging.getLogger(__name__)


def read_agent_metrics(path, name_root, diction_name='', print_dictionary=False):
    agent_dict_path = os.path.join(path, f'{name_root}_agent_dict.json')
    auction_dict_path = os.path.join(path, f'auction_{name_root}_metrics.json')
    controller_dict_path = os.path.join(path, f'controller_{name_root}_metrics.json')

    # first, read and print a dictionary of relevant agents
    if len(diction_name) > 0:
        try:
            lp = open(diction_name).read()
        except:
            logger.error(f'Unable to open agent metrics file {diction_name}')
    else:
        try:
            lp = open(agent_dict_path).read()
        except:
            logger.error(f'Unable to open agent metrics file {agent_dict_path}')
    model = json.loads(lp)
    a_keys = list(model['markets'].keys())
    a_keys.sort()
    c_keys = list(model['controllers'].keys())
    c_keys.sort()
    if print_dictionary:
        print('\nMarket Dictionary:')
        print('ID Period Unit Init StDev')
        for key in a_keys:
            row = model['markets'][key]
            print(key, row['period'], row['unit'], row['init_price'], row['init_stdev'])
        print('\nController Dictionary:')
        print('ID House Mode BaseDaylight Ramp Offset Cap')
        for key in c_keys:
            row = model['controllers'][key]
            print(key, row['houseName'], row['control_mode'], row['daylight_set'], row['ramp'], row['offset_limit'],
                  row['price_cap'])

    # read the auction metrics file
    lp_a = open(auction_dict_path).read()
    lst_a = json.loads(lp_a)
    print('\nAuction Metrics data starting', lst_a['StartTime'])

    # make a sorted list of the times, and NumPy array of times in hours
    lst_a.pop('StartTime')
    meta_a = lst_a.pop('Metadata')
    times = list(map(int, list(lst_a.keys())))
    times.sort()
    print('There are', len(times), 'sample times at', times[1] - times[0], 'second intervals')
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # parse the metadata for things of specific interest
    # print ('\nAuction Metadata [Variable Index Units]')
    idx_a = {}
    for key, val in meta_a.items():
        # print (key, val['index'], val['units'])
        if key == 'clearing_price':
            idx_a['CLEAR_PRICE_IDX'] = val['index']
            idx_a['CLEAR_PRICE_UNITS'] = val['units']
        if key == 'clearing_type':
            idx_a['CLEAR_TYPE_IDX'] = val['index']
            idx_a['CLEAR_TYPE_UNITS'] = val['units']
        if key == 'consumer_surplus':
            idx_a['CONSUMER_SURPLUS_IDX'] = val['index']
            idx_a['CONSUMER_SURPLUS_UNITS'] = val['units']
        if key == 'average_consumer_surplus':
            idx_a['AVERAGE_CONSUMER_SURPLUS_IDX'] = val['index']
            idx_a['AVERAGE_CONSUMER_SURPLUS_UNITS'] = val['units']
        if key == 'supplier_surplus':
            idx_a['SUPPLIER_SURPLUS_IDX'] = val['index']
            idx_a['SUPPLIER_SURPLUS_UNITS'] = val['units']

    # create a NumPy array of all auction metrics
    data_a = np.empty(shape=(len(a_keys), len(times), len(lst_a[str(times[0])][a_keys[0]])), dtype=np.float)
    print('\nConstructed', data_a.shape, 'NumPy array for Auctions')
    j = 0
    for _ in a_keys:
        i = 0
        for t in times:
            ary = lst_a[str(t)][a_keys[j]]
            data_a[j, i, :] = ary
            i = i + 1
        j = j + 1

    # read the controller metrics file
    lp_c = open(controller_dict_path).read()
    lst_c = json.loads(lp_c)
    print('\nController Metrics data starting', lst_c['StartTime'])

    # parse the metadata for things of specific interest
    # c_keys = ['house1_R1_12_47_1_tm_507_thermostat_controller']
    lst_c.pop('StartTime')
    meta_c = lst_c.pop('Metadata')
    # print ('\nController Metadata [Variable Index Units]')
    idx_c = {}
    for key, val in meta_c.items():
        # print (key, val['index'], val['units'])
        if key == 'bid_price':
            idx_c['BID_P_IDX'] = val['index']
            idx_c['BID_P_UNITS'] = val['units']
        elif key == 'bid_quantity':
            idx_c['BID_Q_IDX'] = val['index']
            idx_c['BID_Q_UNITS'] = val['units']

    # create a NumPy array of all controller metrics - many are 'missing' zero-bids
    data_c = np.empty(shape=(len(c_keys), len(times), len(meta_c.items())), dtype=np.float)
    print('\nConstructed', data_c.shape, 'NumPy array for Controllers')
    zary = np.zeros(len(meta_c.items()))
    j = 0
    for _ in c_keys:
        i = 0
        for t in times:
            if c_keys[j] in lst_c[str(t)]:
                ary = lst_c[str(t)][c_keys[j]]
            else:
                ary = zary
            data_c[j, i, :] = ary
            i = i + 1
        j = j + 1

    # identify the controller that put in the highest bid
    cidx = 0
    nbidding = 0
    max_p = 0.0
    for i in range(len(c_keys)):
        this_max_p = np.amax(data_c[i, :, idx_c['BID_P_IDX']])
        if this_max_p > 0.0:
            nbidding += 1
        if this_max_p > max_p:
            max_p = this_max_p
            cidx = i
    print('Out of {:d} controllers, {:d} submitted bids and the highest bidder was {:s} [{:d}]'
          .format(len(c_keys), nbidding, c_keys[cidx], cidx))

    return {
        'hrs': hrs,
        'data_a': data_a,
        'data_c': data_c,
        'idx_a': idx_a,
        'idx_c': idx_c,
        'keys_a': a_keys,
        'keys_c': c_keys,
        'high_bid_idx': cidx
    }


def plot_agents(diction, save_file=None, save_only=False):
    hrs = diction['hrs']
    data_a = diction['data_a']
    data_c = diction['data_c']
    idx_a = diction['idx_a']
    idx_c = diction['idx_c']
    # keys_a = diction['keys_a']  # not used
    keys_c = diction['keys_c']
    cidx = diction['high_bid_idx']

    # display a plot
    fig, ax = plt.subplots(2, 2, sharex='col')

    ax[0, 0].plot(hrs, data_a[0, :, idx_a['CLEAR_PRICE_IDX']], color='blue', label='Cleared')
    ax[0, 0].plot(hrs, data_c[cidx, :, idx_c['BID_P_IDX']], color='red', label='Bid')
    ax[0, 0].set_ylabel(idx_a['CLEAR_PRICE_UNITS'])
    ax[0, 0].set_title('Prices at ' + keys_c[cidx])
    ax[0, 0].legend(loc='best')

    ax[1, 0].plot(hrs, data_c[cidx, :, idx_c['BID_Q_IDX']], color='red', marker='o', label='Quantity')
    ax[1, 0].set_ylabel(idx_c['BID_Q_UNITS'])
    ax[1, 0].set_title('Bid Quantity at ' + keys_c[cidx])
    ax[1, 0].set_xlabel('Hours')

    ax[0, 1].plot(hrs, data_a[0, :, idx_a['CONSUMER_SURPLUS_IDX']].cumsum(), color='blue', label='Consumer')
    ax[0, 1].plot(hrs, data_a[0, :, idx_a['SUPPLIER_SURPLUS_IDX']].cumsum(), color='red', label='Supplier')
    ax[0, 1].set_ylabel(idx_a['CONSUMER_SURPLUS_UNITS'])
    ax[0, 1].set_title('Surplus')
    ax[0, 1].legend(loc='best')

    q1 = (data_c[:, :, idx_c['BID_Q_IDX']]).squeeze()
    q2 = q1.sum(axis=0)
    ax[1, 1].plot(hrs, q2, color='red')
    ax[1, 1].set_ylabel(idx_c['BID_Q_UNITS'])
    ax[1, 1].set_title('Total Controller Bids')
    ax[1, 1].set_xlabel('Hours')

    if save_file is not None:
        plt.savefig(save_file)
    if not save_only:
        plt.show()


def process_agents(name_root, diction_name='', save_file=None, save_only=False, print_dictionary=False):
    """ Plots cleared price, plus bids from the first HVAC controller

    This function reads *auction_[name_root]_metrics.json* and
    *controller_[name_root]_metrics.json* for the data;
    it reads *[name_root]_glm_dict.json* for the metadata.
    These must all exist in the current working directory.
    Makes one graph with 2 subplots:

    1. Cleared price from the only auction, and bid price from the first controller
    2. Bid quantity from the first controller

    Args:
        name_root (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
        diction_name (str): metafile name (with json extension) for a different GLM dictionary, if it's not *[name_root]_glm_dict.json*. Defaults to empty.
        save_file (str): name of a file to save plot, should include the *png* or *pdf* extension to determine type.
        save_only (Boolean): set True with *save_file* to skip the display of the plot. Otherwise, script waits for user keypress.
        print_dictionary (Boolean): set True to print dictionary.
    """
    path = os.getcwd()
    diction = read_agent_metrics(path, name_root, diction_name, print_dictionary)
    plot_agents(diction, save_file, save_only)
