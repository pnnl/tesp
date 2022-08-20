# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: plot_pp.py

import json

import matplotlib.pyplot as plt
import numpy as np


def bus_color(key):
    if key == '1':
        return 'b'
    if key == '2':
        return 'g'
    if key == '3':
        return 'r'
    if key == '4':
        return 'c'
    if key == '5':
        return 'm'
    if key == '6':
        return 'y'
    if key == '7':
        return 'k'
    if key == '8':
        return 'cadetblue'
    return 'k'


def unit_width(diction, key):
    if diction['generators'][key]['bustype'] == 'swing':
        return 2.0
    return 1.0


def unit_color(diction, key):
    genfuel = diction['generators'][key]['genfuel']
    if genfuel == 'wind':
        return 'g'
    if genfuel == 'nuclear':
        return 'r'
    if genfuel == 'coal':
        return 'k'
    if genfuel == 'gas':
        return 'b'
    return 'y'


def process_pypower(name_root, nhours):
    # first, read and print a dictionary of relevant PYPOWER objects
    lp = open(name_root + '_m_dict.json').read()
    diction = json.loads(lp)
    baseMVA = diction['baseMVA']
    gen_keys = list(diction['generators'].keys())
    gen_keys.sort()
    bus_keys = list(diction['dsoBuses'].keys())
    bus_keys.sort()
    print('\n\nFile', name_root, 'has baseMVA', baseMVA)
    print('\nGenerator Dictionary:')
    print('Unit Bus Type Fuel Pmin Pmax Costs[Start Stop C2 C1 C0]')
    for key in gen_keys:
        row = diction['generators'][key]
        print(key, row['bus'], row['bustype'], row['genfuel'], row['Pmin'], row['Pmax'], '[', row['StartupCost'],
              row['ShutdownCost'], row['c2'], row['c1'], row['c0'], ']')
    print('\nFNCS Bus Dictionary:')
    print('Bus Pnom Qnom ampFactor [GridLAB-D Substations]')
    for key in bus_keys:
        row = diction['dsoBuses'][key]
        print(key, row['Pnom'], row['Qnom'], row['ampFactor'], row['GLDsubstations'])  # TODO curveScale, curveSkew

    # read the bus metrics file
    lp_b = open('bus_' + name_root + '_metrics.json').read()
    lst_b = json.loads(lp_b)
    print('\nBus Metrics data starting', lst_b['StartTime'])

    # make a sorted list of the times, and NumPy array of times in hours
    lst_b.pop('StartTime')
    meta_b = lst_b.pop('Metadata')
    times = list(map(int, list(lst_b.keys())))
    times.sort()
    print('There are', len(times), 'sample times at', times[1] - times[0], 'second intervals')
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # parse the metadata for things of specific interest
    print('\nBus Metadata [Variable Index Units] for', len(lst_b[str(times[0])]), 'objects')
    for key, val in meta_b.items():
        print(key, val['index'], val['units'])
        if key == 'LMP_P':
            LMP_P_IDX = val['index']
            LMP_P_UNITS = val['units']
        elif key == 'LMP_Q':
            LMP_Q_IDX = val['index']
            LMP_Q_UNITS = val['units']
        elif key == 'PD':
            PD_IDX = val['index']
            PD_UNITS = val['units']
        elif key == 'QD':
            QD_IDX = val['index']
            QD_UNITS = val['units']
        elif key == 'Vang':
            VANG_IDX = val['index']
            VANG_UNITS = val['units']
        elif key == 'Vmag':
            VMAG_IDX = val['index']
            VMAG_UNITS = val['units']
        elif key == 'Vmax':
            VMAX_IDX = val['index']
            VMAX_UNITS = val['units']
        elif key == 'Vmin':
            VMIN_IDX = val['index']
            VMIN_UNITS = val['units']
        elif key == 'unresp':
            UNRESP_IDX = val['index']
            UNRESP_UNITS = val['units']
        elif key == 'resp_max':
            RESP_MAX_IDX = val['index']
            RESP_MAX_UNITS = val['units']
        elif key == 'c1':
            C1_IDX = val['index']
            C1_UNITS = val['units']
        elif key == 'c2':
            C2_IDX = val['index']
            C2_UNITS = val['units']

    # create a NumPy array of all bus metrics, display summary information
    data_b = np.empty(shape=(len(bus_keys), len(times), len(lst_b[str(times[0])][bus_keys[0]])), dtype=np.float)
    print('\nConstructed', data_b.shape, 'NumPy array for Buses')
    print('LMPavg,LMPmax,LMP1avg,LMP1std,Vmin,Vmax,Unresp_avg,RespMax_avg', 'C1_avg', 'C2_avg')
    last1 = int(3600 * nhours / (times[1] - times[0]))
    j = 0
    for key in bus_keys:
        i = 0
        for t in times:
            ary = lst_b[str(t)][bus_keys[j]]
            data_b[j, i, :] = ary
            i = i + 1
        print(key,
              '{:.4f}'.format(data_b[j, :, LMP_P_IDX].mean()),
              '{:.4f}'.format(data_b[j, :, LMP_P_IDX].max()),
              '{:.4f}'.format(data_b[j, 0:last1, LMP_P_IDX].mean()),
              '{:.4f}'.format(data_b[j, 0:last1, LMP_P_IDX].std()),
              '{:.4f}'.format(data_b[j, :, VMIN_IDX].min()),
              '{:.4f}'.format(data_b[j, :, VMAX_IDX].max()),
              '{:.4f}'.format(data_b[j, 0:last1, UNRESP_IDX].mean()),
              '{:.4f}'.format(data_b[j, 0:last1, RESP_MAX_IDX].mean()),
              '{:.4f}'.format(data_b[j, 0:last1, C1_IDX].mean()),
              '{:.4f}'.format(data_b[j, 0:last1, C2_IDX].mean()))
        j = j + 1

    # read the generator metrics file
    lp_g = open('gen_' + name_root + '_metrics.json').read()
    lst_g = json.loads(lp_g)
    print('\nGenerator Metrics data starting', lst_g['StartTime'])
    # make a sorted list of the times, and NumPy array of times in hours
    lst_g.pop('StartTime')
    meta_g = lst_g.pop('Metadata')
    print('\nGenerator Metadata [Variable Index Units] for', len(lst_g[str(times[0])]), 'objects')
    for key, val in meta_g.items():
        print(key, val['index'], val['units'])
        if key == 'Pgen':
            PGEN_IDX = val['index']
            PGEN_UNITS = val['units']
        elif key == 'Qgen':
            QGEN_IDX = val['index']
            QGEN_UNITS = val['units']
        elif key == 'LMP_P':
            GENLMP_IDX = val['index']
            GENLMP_UNITS = val['units']

    # create a NumPy array of all generator metrics
    data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[str(times[0])][gen_keys[0]])), dtype=np.float)
    print('\nConstructed', data_g.shape, 'NumPy array for Generators')
    print('Unit,Bus,Type,Fuel,CF,COV')
    j = 0
    for key in gen_keys:
        i = 0
        for t in times:
            ary = lst_g[str(t)][gen_keys[j]]
            data_g[j, i, :] = ary
            i = i + 1
        p_avg = data_g[j, :, PGEN_IDX].mean()
        p_std = data_g[j, :, PGEN_IDX].std()
        row = diction['generators'][key]
        p_max = float(row['Pmax'])
        print(key, row['bus'], row['bustype'], row['genfuel'],
              '{:.4f}'.format(p_avg / p_max),
              '{:.4f}'.format(p_std / p_avg))
        j = j + 1

    # display a plot 
    fig, ax = plt.subplots(2, 4, sharex='col')
    tmin = 0.0
    tmax = nhours
    xticks = []
    if nhours > 48:
        tstep = 24
    elif nhours > 24:
        tstep = 12
    elif nhours > 12:
        tstep = 6
    else:
        tstep = 2
    for tick in range(0, nhours + 1, tstep):
        xticks.append(tick)
    for i in range(2):
        for j in range(4):
            ax[i, j].grid(linestyle='-')
            ax[i, j].set_xlim(tmin, tmax)
            ax[i, j].set_xticks(xticks)

    ax[0, 0].set_title('Total Bus Loads')
    ax[0, 0].set_ylabel(PD_UNITS)
    for i in range(data_b.shape[0]):
        ax[0, 0].plot(hrs, data_b[i, :, PD_IDX], color=bus_color(bus_keys[i]))

    ax[1, 0].set_title('Generator Outputs')
    ax[1, 0].set_ylabel(PGEN_UNITS)
    for i in range(data_g.shape[0]):
        ax[1, 0].plot(hrs, data_g[i, :, PGEN_IDX], color=unit_color(diction, gen_keys[i]),
                      linewidth=unit_width(diction, gen_keys[i]))

    ax[0, 1].set_title('Bus Voltages')
    ax[0, 1].set_ylabel(VMAG_UNITS)
    for i in range(data_b.shape[0]):
        ax[0, 1].plot(hrs, data_b[i, :, VMAG_IDX], color=bus_color(bus_keys[i]))

    ax[1, 1].set_title('Locational Marginal Prices')
    ax[1, 1].set_ylabel(LMP_P_UNITS)
    for i in range(data_b.shape[0]):
        ax[1, 1].plot(hrs, data_b[i, :, LMP_P_IDX], color=bus_color(bus_keys[i]))

    ax[0, 2].set_title('Bus Unresp Load')
    ax[0, 2].set_ylabel(UNRESP_UNITS)
    for i in range(data_b.shape[0]):
        ax[0, 2].plot(hrs, data_b[i, :, UNRESP_IDX], color=bus_color(bus_keys[i]))

    ax[1, 2].set_title('Bus Max Resp Load')
    ax[1, 2].set_ylabel(RESP_MAX_UNITS)
    for i in range(data_b.shape[0]):
        ax[1, 2].plot(hrs, data_b[i, :, RESP_MAX_IDX], color=bus_color(bus_keys[i]))

    ax[0, 3].set_title('Bus Bid C1')
    ax[0, 3].set_ylabel(C1_UNITS)
    for i in range(data_b.shape[0]):
        ax[0, 3].plot(hrs, data_b[i, :, C1_IDX], color=bus_color(bus_keys[i]))

    ax[1, 3].set_title('Bus Bid C2')
    ax[1, 3].set_ylabel(C2_UNITS)
    for i in range(data_b.shape[0]):
        ax[1, 3].plot(hrs, data_b[i, :, C2_IDX], color=bus_color(bus_keys[i]))

    ax[1, 0].set_xlabel('Hours')
    ax[1, 1].set_xlabel('Hours')
    ax[1, 2].set_xlabel('Hours')
    ax[1, 3].set_xlabel('Hours')

    plt.show()


if __name__ == '__main__':
    process_pypower('ercot_8', 72)
