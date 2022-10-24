# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_houses.py; focus on HVAC
"""Functions to plot house data from GridLAB-D

Public Functions:
    :process_houses: Reads the data and metadata, then makes the plot.  

"""
import logging
import json
import os

import numpy as np
import matplotlib.pyplot as plt

# Setting up logging
logger = logging.getLogger(__name__)


def read_houses_metrics(path, name_root, diction_name=''):
    gld_dict_path = os.path.join(path, f'{name_root}_glm_dict.json')
    house_dict_path = os.path.join(path, f'house_{name_root}_metrics.json')
    # first, read and print a dictionary of all the monitored GridLAB-D objects
    if len(diction_name) > 0:
        try:
            lp = open(diction_name).read()
        except:
            logger.error(f'Unable to open house metrics file {diction_name}')
    else:
        try:
            lp = open(gld_dict_path).read()
        except:
            logger.error(f'Unable to open house metrics file {gld_dict_path}')
    diction = json.loads(lp)
    hse_keys = list(diction['houses'].keys())
    hse_keys.sort()
    # print("\nHouse Dictionary:")
    # for key in hse_keys:
    #   row = diction['houses'][key]
    # # print (key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'], "heating", row['wh_gallons'], "gal WH")
    #   # row['feeder_id'] is also available

    # Houses
    lp_h = open(house_dict_path).read()
    lst_h = json.loads(lp_h)
    lst_h.pop('StartTime')
    meta_h = lst_h.pop('Metadata')
    times = list(map(int, list(lst_h.keys())))
    times.sort()
    print("There are", len(times), "sample times at", times[1] - times[0], "second intervals")
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    #  print("\nHouse Metadata for", len(lst_h[time_key]), "objects")
    idx_h = {}
    for key, val in meta_h.items():
        # print (key, val['index'], val['units'])
        if key == 'air_temperature_avg':
            idx_h['HSE_AIR_AVG_IDX'] = val['index']
        elif key == 'air_temperature_min':
            idx_h['HSE_AIR_MIN_IDX'] = val['index']
        elif key == 'air_temperature_max':
            idx_h['HSE_AIR_MAX_IDX'] = val['index']
        elif key == 'hvac_load_avg':
            idx_h['HSE_HVAC_AVG_IDX'] = val['index']
        elif key == 'hvac_load_min':
            idx_h['HSE_HVAC_MIN_IDX'] = val['index']
        elif key == 'hvac_load_max':
            idx_h['HSE_HVAC_MAX_IDX'] = val['index']
        elif key == 'waterheater_load_avg':
            idx_h['HSE_WH_AVG_IDX'] = val['index']
        elif key == 'waterheater_load_min':
            idx_h['HSE_WH_MIN_IDX'] = val['index']
        elif key == 'waterheater_load_max':
            idx_h['HSE_WH_MAX_IDX'] = val['index']
        elif key == 'total_load_avg':
            idx_h['HSE_TOTAL_AVG_IDX'] = val['index']
        elif key == 'total_load_min':
            idx_h['HSE_TOTAL_MIN_IDX'] = val['index']
        elif key == 'total_load_max':
            idx_h['HSE_TOTAL_MAX_IDX'] = val['index']
        elif key == 'air_temperature_setpoint_cooling':
            idx_h['HSE_SET_COOL_IDX'] = val['index']
        elif key == 'air_temperature_setpoint_heating':
            idx_h['HSE_SET_HEAT_IDX'] = val['index']

    time_key = str(times[0])
    data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
    print("\nConstructed", data_h.shape, "NumPy array for Houses")
    j = 0
    for _ in hse_keys:
        i = 0
        for t in times:
            ary = lst_h[str(t)][hse_keys[j]]
            data_h[j, i, :] = ary
            i = i + 1
        j = j + 1

    return {
        'hrs': hrs,
        'data_h': data_h,
        'keys_h': hse_keys,
        'idx_h': idx_h
    }


def plot_houses(diction, save_file=None, save_only=False):
    hrs = diction['hrs']
    data_h = diction['data_h']
    idx_h = diction['idx_h']
    keys_h = diction['keys_h']

    # display a plot
    fig, ax = plt.subplots(2, 1, sharex='col')
    i = 0
    for _ in keys_h:
        ax[0].plot(hrs, data_h[i, :, idx_h['HSE_AIR_AVG_IDX']], color='blue')
        ax[1].plot(hrs, data_h[i, :, idx_h['HSE_HVAC_AVG_IDX']], color='red')
        i = i + 1
    ax[0].set_ylabel('Degrees')
    ax[1].set_ylabel('kW')
    ax[1].set_xlabel('Hours')
    ax[0].set_title('HVAC at {:d} Houses'.format(len(keys_h)))

    if save_file is not None:
        plt.savefig(save_file)
    if not save_only:
        plt.show()


def process_houses(name_root, diction_name='', save_file=None, save_only=True):
    """ Plots the temperature and HVAC power for every house

    This function reads *substation_[name_root]_metrics.json* and
    *house_[name_root]_metrics.json* for the data;
    it reads *[name_root]_glm_dict.json* for the metadata.
    These must all exist in the current working directory.
    Makes one graph with 2 subplots:

    1. Average air temperature at every house
    2. Average HVAC power at every house

    Args:
      name_root (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
      diction_name (str): metafile name (with json extension) for a different GLM dictionary, if it's not *[name_root]_glm_dict.json*. Defaults to empty.
      save_file (str): name of a file to save plot, should include the *png* or *pdf* extension to determine type.
      save_only (Boolean): set True with *save_file* to skip the display of the plot. Otherwise, script waits for user keypress.
    """
    path = os.getcwd()
    diction = read_houses_metrics(path, name_root, diction_name)
    plot_houses(diction, save_file, save_only)
