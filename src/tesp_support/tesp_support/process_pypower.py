# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_pypower.py
"""Functions to plot bus and generator data from PYPOWER

Public Functions:
        :process_pypower: Reads the data and metadata, then makes the plots.  

"""
import logging
import json
import os

import numpy as np
import matplotlib.pyplot as plt

# Setting up logging
logger = logging.getLogger(__name__)


def read_pypower_metrics(path, name_root):
    m_dict_path = os.path.join(path, 'model_dict.json')
    b_dict_path = os.path.join(path, f'bus_{name_root}_metrics.json')
    g_dict_path = os.path.join(path, f'gen_{name_root}_metrics.json')

    # first, read and print a dictionary of relevant PYPOWER objects
    lp = open(m_dict_path).read()
    diction = json.loads(lp)
    baseMVA = diction['baseMVA']
    gen_keys = list(diction['generators'].keys())
    gen_keys.sort()
    bus_keys = list(diction['dsoBuses'].keys())
    bus_keys.sort()
    print('\n\nFile', m_dict_path, 'has baseMVA', baseMVA)
    print('\nGenerator Dictionary:')
    print('Unit Bus Type Pnom Pmax Costs[Start Stop C2 C1 C0]')
    for key in gen_keys:
        row = diction['generators'][key]
        print(key, row['bus'], row['bustype'], row['Pmin'], row['Pmax'],
              '[', row['StartupCost'], row['ShutdownCost'], row['c2'], row['c1'], row['c0'], ']')
    print('\nDSO Bus Dictionary:')
    print('Bus Pnom Qnom ampFactor [GridLAB-D Substations]')
    for key in bus_keys:
        row = diction['dsoBuses'][key]
        print(key, row['Pnom'], row['Qnom'], row['ampFactor'], row['GLDsubstations'])

    # read the bus metrics file
    lp_b = open(b_dict_path).read()
    lst_b = json.loads(lp_b)
    print('\nBus Metrics data starting', lst_b['StartTime'])

    # make a sorted list of the times, and NumPy array of times in hours
    lst_b.pop('StartTime')
    # lst_b.pop('System base MVA')
    # lst_b.pop('Number of buses')
    # lst_b.pop('Number of generators')
    # lst_b.pop('Network name')
    meta_b = lst_b.pop('Metadata')
    times = list(map(int, list(lst_b.keys())))
    times.sort()
    print('There are', len(times), 'sample times at', times[1] - times[0], 'second intervals')
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # parse the metadata for things of specific interest
    idx_b = {}
    print('\nBus Metadata [Variable Index Units] for', len(lst_b[str(times[0])]), 'objects')
    for key, val in meta_b.items():
        #    print (key, val['index'], val['units'])
        if key == 'LMP_P':
            idx_b['LMP_P_IDX'] = val['index']
            idx_b['LMP_P_UNITS'] = val['units']
        elif key == 'LMP_Q':
            idx_b['LMP_Q_IDX'] = val['index']
            idx_b['LMP_Q_UNITS'] = val['units']
        elif key == 'PD':
            idx_b['PD_IDX'] = val['index']
            idx_b['PD_UNITS'] = val['units']
        elif key == 'QD':
            idx_b['QD_IDX'] = val['index']
            idx_b['QD_UNITS'] = val['units']
        elif key == 'Vang':
            idx_b['VANG_IDX'] = val['index']
            idx_b['VANG_UNITS'] = val['units']
        elif key == 'Vmag':
            idx_b['VMAG_IDX'] = val['index']
            idx_b['VMAG_UNITS'] = val['units']
        elif key == 'Vmax':
            idx_b['VMAX_IDX'] = val['index']
            idx_b['VMAX_UNITS'] = val['units']
        elif key == 'Vmin':
            idx_b['VMIN_IDX'] = val['index']
            idx_b['VMIN_UNITS'] = val['units']

    # create a NumPy array of all bus metrics
    data_b = np.empty(shape=(len(bus_keys), len(times), len(lst_b[str(times[0])][bus_keys[0]])), dtype=np.float)
    print('\nConstructed', data_b.shape, 'NumPy array for Buses')
    j = 0
    for _ in bus_keys:
        i = 0
        for t in times:
            ary = lst_b[str(t)][bus_keys[j]]
            data_b[j, i, :] = ary
            i = i + 1
        j = j + 1

    # display some averages
    print('Average real power LMP = {:.5f} {:s}'.format(data_b[0, :, idx_b['LMP_P_IDX']].mean(), idx_b['LMP_P_UNITS']))
    print('Maximum real power LMP = {:.5f} {:s}'.format(data_b[0, :, idx_b['LMP_P_IDX']].max(), idx_b['LMP_P_UNITS']))
    print('First day LMP mean = {:.5f}'.format(data_b[0, 0:25, idx_b['LMP_P_IDX']].mean()))
    print('First day LMP std dev = {:.6f}'.format(data_b[0, 0:25, idx_b['LMP_P_IDX']].std()))
    print('Maximum bus voltage = {:.4f} {:s}'.format(data_b[0, :, idx_b['VMAX_IDX']].max(), idx_b['VMAX_UNITS']))
    print('Minimum bus voltage = {:.4f} {:s}'.format(data_b[0, :, idx_b['VMIN_IDX']].min(), idx_b['VMIN_UNITS']))

    # read the generator metrics file
    lp_g = open(g_dict_path).read()
    lst_g = json.loads(lp_g)
    print('\nGenerator Metrics data starting', lst_g['StartTime'])
    # make a sorted list of the times, and NumPy array of times in hours
    lst_g.pop('StartTime')
    meta_g = lst_g.pop('Metadata')
    idx_g = {}
    # print ('\nGenerator Metadata [Variable Index Units] for', len(lst_g[str(times[0])]), 'objects')
    for key, val in meta_g.items():
        # print (key, val['index'], val['units'])
        if key == 'Pgen':
            idx_g['PGEN_IDX'] = val['index']
            idx_g['PGEN_UNITS'] = val['units']
        elif key == 'Qgen':
            idx_g['QGEN_IDX'] = val['index']
            idx_g['QGEN_UNITS'] = val['units']
        elif key == 'LMP_P':
            idx_g['GENLMP_IDX'] = val['index']
            idx_g['GENLMP_UNITS'] = val['units']

    # create a NumPy array of all bus metrics
    data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[str(times[0])][gen_keys[0]])), dtype=np.float)
    print('\nConstructed', data_g.shape, 'NumPy array for Generators')
    j = 0
    for _ in gen_keys:
        i = 0
        for t in times:
            ary = lst_g[str(t)][gen_keys[j]]
            data_g[j, i, :] = ary
            i = i + 1
        j = j + 1

    return {
        'hrs': hrs,
        'data_b': data_b,
        'keys_b': bus_keys,
        'idx_b': idx_b,
        'data_g': data_g,
        'keys_g': gen_keys,
        'idx_g': idx_g
    }


def plot_pypower(diction, title=None, save_file=None, save_only=False):
    hrs = diction['hrs']
    data_b = diction['data_b']
    keys_b = diction['keys_b']
    idx_b = diction['idx_b']
    data_g = diction['data_g']
    keys_g = diction['keys_g']
    idx_g = diction['idx_g']

    # display a plot - hard-wired assumption of 3 generators from Case 9
    fig, ax = plt.subplots(4, 2, sharex='col')
    if title is not None:
        fig.suptitle(title)

    ax[0, 0].plot(hrs, data_b[0, :, idx_b['PD_IDX']], color='blue', label='Real')
    ax[0, 0].plot(hrs, data_b[0, :, idx_b['QD_IDX']], color='red', label='Reactive')
    ax[0, 0].set_ylabel(idx_b['PD_UNITS'] + '/' + idx_b['QD_UNITS'])
    ax[0, 0].set_title('Demands at ' + keys_b[0])
    ax[0, 0].legend(loc='best')

    ax[1, 0].plot(hrs, data_b[0, :, idx_b['LMP_P_IDX']], color='blue', label='Real')
    ax[1, 0].plot(hrs, data_b[0, :, idx_b['LMP_Q_IDX']], color='red', label='Reactive')
    ax[1, 0].set_ylabel(idx_b['LMP_P_UNITS'])
    ax[1, 0].set_title('Prices at ' + keys_b[0])
    ax[1, 0].legend(loc='best')

    ax[2, 0].plot(hrs, data_b[0, :, idx_b['VMAG_IDX']], color='blue', label='Magnitude')
    ax[2, 0].plot(hrs, data_b[0, :, idx_b['VMAX_IDX']], color='red', label='Vmax')
    ax[2, 0].plot(hrs, data_b[0, :, idx_b['VMIN_IDX']], color='green', label='Vmin')
    ax[2, 0].set_ylabel(idx_b['VMAG_UNITS'])
    ax[2, 0].set_title('Voltages at ' + keys_b[0])
    ax[2, 0].legend(loc='best')

    ax[3, 0].plot(hrs, data_g[0, :, idx_g['GENLMP_IDX']], color='blue', label='unit 1')
    ax[3, 0].plot(hrs, data_g[1, :, idx_g['GENLMP_IDX']], color='red', label='unit 2')
    ax[3, 0].plot(hrs, data_g[2, :, idx_g['GENLMP_IDX']], color='green', label='unit 3')
    ax[3, 0].plot(hrs, data_g[3, :, idx_g['GENLMP_IDX']], color='magenta', label='unit 4')
    ax[3, 0].set_ylabel(idx_g['GENLMP_UNITS'])
    ax[3, 0].set_title('Generator Prices')
    ax[3, 0].legend(loc='best')

    for i in range(0, 4):
        ax[i, 1].plot(hrs, data_g[i, :, idx_g['PGEN_IDX']], color='blue', label='P')
        ax[i, 1].plot(hrs, data_g[i, :, idx_g['QGEN_IDX']], color='red', label='Q')
        ax[i, 1].set_ylabel(idx_g['PGEN_UNITS'] + '/' + idx_g['QGEN_UNITS'])
        ax[i, 1].set_title('Output from unit ' + keys_g[i])
        ax[i, 1].legend(loc='best')

    ax[3, 0].set_xlabel('Hours')
    ax[3, 1].set_xlabel('Hours')

    if save_file is not None:
        plt.savefig(save_file)
    if not save_only:
        plt.show()


def process_pypower(name_root, title=None, save_file=None, save_only=True):
    """ Plots bus and generator quantities for the 9-bus system used in te30 or sgip1 examples

    This function reads *bus_[name_root]_metrics.json* and
    *gen_[name_root]_metrics.json* for the data, and
    *[name_root]_m_dict.json* for the metadata.
    These must all exist in the current working directory.
    One graph is generated with 8 subplots:

    1. Bus P and Q demands, at the single GridLAB-D connection
    2. Bus P and Q locational marginal prices (LMP), at the single GridLAB-D connection
    3. Bus Vmin, Vmax and Vavg, at the single GridLAB-D connection
    4. All 4 generator prices
    5. Generator 1 P and Q output
    6. Generator 2 P and Q output
    7. Generator 3 P and Q output
    8. Generator 4 P and Q output

    Args:
        name_root (str): file name of the TESP case, not necessarily the same as the PYPOWER case, w/out the JSON extension
        title (str): supertitle for the page of plots.
        save_file (str): name of a file to save plot, should include the *png* or *pdf* extension to determine type.
        save_only (Boolean): set True with *save_file* to skip the display of the plot. Otherwise, script waits for user keypress.
    """
    path = os.getcwd()
    diction = read_pypower_metrics(path, name_root)
    plot_pypower(diction, title, save_file, save_only)
