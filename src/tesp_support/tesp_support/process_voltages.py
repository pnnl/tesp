# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_voltages.py
"""Functions to plot all billing meter voltages from GridLAB-D

Public Functions:
    :process_voltages: Reads the data and metadata, then makes the plot.  

"""
import logging
import json
import os

import numpy as np
import matplotlib.pyplot as plt

# Setting up logging
logger = logging.getLogger(__name__)


def read_voltages_metrics(path, name_root, diction_name=''):
    glm_dict_path = os.path.join(path, f'{name_root}_glm_dict.json')
    billing_dict_path = os.path.join(path, f'billing_meter_{name_root}_metrics.json')
    # first, read and print a dictionary of all the monitored GridLAB-D objects
    if len(diction_name) > 0:
        try:
            lp = open(diction_name).read()
        except:
            logger.error(f'Unable to open voltage metric file {diction_name}')
    else:
        try:
            lp = open(glm_dict_path).read()
        except:
            logger.error(f'Unable to open voltage metrics file {glm_dict_path}')
    diction = json.loads(lp)
    mtr_keys = list(diction['billingmeters'].keys())
    mtr_keys.sort()
    # print("\nBilling Meter Dictionary:")
    # for key in mtr_keys:
    #   row = diction['billingmeters'][key]
    # # print (key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])

    # make a sorted list of the sample times in hours
    lp_m = open(billing_dict_path).read()
    lst_m = json.loads(lp_m)
    lst_m.pop('StartTime')
    meta_m = lst_m.pop('Metadata')
    times = list(map(int, list(lst_m.keys())))
    times.sort()
    print("There are", len(times), "sample times at", times[1] - times[0], "second intervals")
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # print("\nBilling Meter Metadata for", len(lst_m['3600']), "objects")
    idx_m = {}
    for key, val in meta_m.items():
        # print (key, val['index'], val['units'])
        if key == 'voltage_max':
            idx_m['MTR_VOLT_MAX_IDX'] = val['index']
            idx_m['MTR_VOLT_MAX_UNITS'] = val['units']
        elif key == 'voltage_min':
            idx_m['MTR_VOLT_MIN_IDX'] = val['index']
            idx_m['MTR_VOLT_MIN_UNITS'] = val['units']
        elif key == 'voltage_avg':
            idx_m['MTR_VOLT_AVG_IDX'] = val['index']
            idx_m['MTR_VOLT_AVG_UNITS'] = val['units']
        elif key == 'voltage12_max':
            idx_m['MTR_VOLT12_MAX_IDX'] = val['index']
            idx_m['MTR_VOLT12_MAX_UNITS'] = val['units']
        elif key == 'voltage12_min':
            idx_m['MTR_VOLT12_MIN_IDX'] = val['index']
            idx_m['MTR_VOLT12_MIN_UNITS'] = val['units']
        elif key == 'voltage_unbalance_max':
            idx_m['MTR_VOLTUNB_MAX_IDX'] = val['index']
            idx_m['MTR_VOLTUNB_MAX_UNITS'] = val['units']

    time_key = str(times[0])
    data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
    print("\nConstructed", data_m.shape, "NumPy array for Meters")
    j = 0
    for _ in mtr_keys:
        i = 0
        for t in times:
            ary = lst_m[str(t)][mtr_keys[j]]
            data_m[j, i, :] = ary
            i = i + 1
        j = j + 1

    # normalize the meter voltages to 100 percent
    j = 0
    for key in mtr_keys:
        vln = diction['billingmeters'][key]['vln'] / 100.0
        vll = diction['billingmeters'][key]['vll'] / 100.0
        data_m[j, :, idx_m['MTR_VOLT_MIN_IDX']] /= vln
        data_m[j, :, idx_m['MTR_VOLT_MAX_IDX']] /= vln
        data_m[j, :, idx_m['MTR_VOLT_AVG_IDX']] /= vln
        data_m[j, :, idx_m['MTR_VOLT12_MIN_IDX']] /= vll
        data_m[j, :, idx_m['MTR_VOLT12_MAX_IDX']] /= vll
        j = j + 1

    return {
        'hrs': hrs,
        'data_m': data_m,
        'keys_m': mtr_keys,
        'idx_m': idx_m
    }


def plot_voltages(diction, save_file=None, save_only=False):
    hrs = diction['hrs']
    data_m = diction['data_m']
    keys_m = diction['keys_m']
    idx_m = diction['idx_m']
    # display a plot
    fig, ax = plt.subplots(2, 1, sharex='col')
    i = 0
    for _ in keys_m:
        ax[0].plot(hrs, data_m[i, :, idx_m['MTR_VOLT_MIN_IDX']], color='blue')
        ax[1].plot(hrs, data_m[i, :, idx_m['MTR_VOLT_MAX_IDX']], color='red')
        i = i + 1
    ax[0].set_ylabel('Min Voltage [%]')
    ax[1].set_ylabel('Max Voltage [%]')
    ax[1].set_xlabel('Hours')
    ax[0].set_title('Voltage at {:d} Meters'.format(len(keys_m)))

    if save_file is not None:
        plt.savefig(save_file)
    if not save_only:
        plt.show()


def process_voltages(name_root, diction_name='', save_file=None, save_only=True):
    """ Plots the min and max line-neutral voltages for every billing meter

    This function reads *substation_[name_root]_metrics.json* and
    *billing_meter_[name_root]_metrics.json* for the voltage data, and
    *[name_root]_glm_dict.json* for the meter names.
    These must all exist in the current working directory.
    One graph is generated with 2 subplots:

    1. The Min line-to-neutral voltage at each billing meter
    2. The Max line-to-neutral voltage at each billing meter

    Args:
      name_root (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
      diction_name (str): metafile name (with json extension) for a different GLM dictionary, if it's not *[name_root]_glm_dict.json*. Defaults to empty.
      save_file (str): name of a file to save plot, should include the *png* or *pdf* extension to determine type.
      save_only (Boolean): set True with *save_file* to skip the display of the plot. Otherwise, script waits for user keypress.
    """
    path = os.getcwd()
    diction = read_voltages_metrics(path, name_root, diction_name)
    plot_voltages(diction, save_file, save_only)
