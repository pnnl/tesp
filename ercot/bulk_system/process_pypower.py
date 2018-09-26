#	Copyright (C) 2017-2018 Battelle Memorial Institute
# file: process_pypower.py
import json;
#import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def bus_color(i):
    if i == 0:
        return 'b'
    if i == 1:
        return 'g'
    if i == 2:
        return 'r'
    if i == 3:
        return 'c'
    if i == 4:
        return 'm'
    if i == 5:
        return 'y'
    if i == 6:
        return 'k'
    if i == 7:
        return 'cadetblue'
    return 'k'

def unit_width(dict, i):
    if dict['generators'][str(i+1)]['bustype'] == 'swing':
        return 2.0
    return 1.0

def unit_color(dict, i):
#    bustype = dict['generators'][str(i+1)]['bustype']
    genfuel = dict['generators'][str(i+1)]['genfuel']
#    print (i, bustype, genfuel)
    if genfuel == 'wind':
        return 'g'
    if genfuel == 'nuclear':
        return 'r'
    if genfuel == 'coal':
        return 'k'
    if genfuel == 'gas':
        return 'b'
    return 'y'

def process_pypower(nameroot):
    # first, read and print a dictionary of relevant PYPOWER objects
    lp = open (nameroot + '_m_dict.json').read()
    dict = json.loads(lp)
    baseMVA = dict['baseMVA']
    gen_keys = list(dict['generators'].keys())
    gen_keys.sort()
    bus_keys = list(dict['fncsBuses'].keys())
    bus_keys.sort()
    print ('\n\nFile', nameroot, 'has baseMVA', baseMVA)
    print('\nGenerator Dictionary:')
    print('Unit Bus Type Fuel Pmin Pmax Costs[Start Stop C2 C1 C0]')
    for key in gen_keys:
        row = dict['generators'][key]
        print (key, row['bus'], row['bustype'], row['genfuel'], row['Pmin'], row['Pmax'], '[', row['StartupCost'], row['ShutdownCost'], row['c2'], row['c1'], row['c0'], ']')
    print('\nFNCS Bus Dictionary:')
    print('Bus Pnom Qnom ampFactor [GridLAB-D Substations]')
    for key in bus_keys:
        row = dict['fncsBuses'][key]
        print (key, row['Pnom'], row['Qnom'], row['ampFactor'], row['GLDsubstations'])  #TODO curveScale, curveSkew

    # read the bus metrics file
    lp_b = open ('bus_' + nameroot + '_metrics.json').read()
    lst_b = json.loads(lp_b)
    print ('\nBus Metrics data starting', lst_b['StartTime'])

    # make a sorted list of the times, and NumPy array of times in hours
    lst_b.pop('StartTime')
    #lst_b.pop('System base MVA')
    #lst_b.pop('Number of buses')
    #lst_b.pop('Number of generators')
    #lst_b.pop('Network name')
    meta_b = lst_b.pop('Metadata')
    times = list(map(int,list(lst_b.keys())))
    times.sort()
    print ('There are', len (times), 'sample times at', times[1] - times[0], 'second intervals')
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # parse the metadata for things of specific interest
    print ('\nBus Metadata [Variable Index Units] for', len(lst_b[str(times[0])]), 'objects')
    for key, val in meta_b.items():
    #    print (key, val['index'], val['units'])
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

    # create a NumPy array of all bus metrics
    data_b = np.empty(shape=(len(bus_keys), len(times), len(lst_b[str(times[0])][bus_keys[0]])), dtype=np.float)
    print ('\nConstructed', data_b.shape, 'NumPy array for Buses')
    j = 0
    for key in bus_keys:
        i = 0
        for t in times:
            ary = lst_b[str(t)][bus_keys[j]]
            data_b[j, i,:] = ary
            i = i + 1
        j = j + 1

    # display some averages
    print ('Average real power LMP =', data_b[0,:,LMP_P_IDX].mean(), LMP_P_UNITS)
    print ('Maximum real power LMP =', data_b[0,:,LMP_P_IDX].max(), LMP_P_UNITS)
    print ('First day LMP mean/std dev=', data_b[0,0:25,LMP_P_IDX].mean(), data_b[0,0:25,LMP_P_IDX].std())
    print ('Maximum bus voltage =', data_b[0,:,VMAX_IDX].max(), VMAX_UNITS)
    print ('Minimum bus voltage =', data_b[0,:,VMIN_IDX].min(), VMIN_UNITS)

    # read the generator metrics file
    lp_g = open ('gen_' + nameroot + '_metrics.json').read()
    lst_g = json.loads(lp_g)
    print ('\nGenerator Metrics data starting', lst_g['StartTime'])
    # make a sorted list of the times, and NumPy array of times in hours
    lst_g.pop('StartTime')
    meta_g = lst_g.pop('Metadata')
    print ('\nGenerator Metadata [Variable Index Units] for', len(lst_g[str(times[0])]), 'objects')
    for key, val in meta_g.items():
        print (key, val['index'], val['units'])
        if key == 'Pgen':
            PGEN_IDX = val['index']
            PGEN_UNITS = val['units']
        elif key == 'Qgen':
            QGEN_IDX = val['index']
            QGEN_UNITS = val['units']
        elif key == 'LMP_P':
            GENLMP_IDX = val['index']
            GENLMP_UNITS = val['units']

    # create a NumPy array of all bus metrics
    data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[str(times[0])][gen_keys[0]])), dtype=np.float)
    print ('\nConstructed', data_g.shape, 'NumPy array for Generators')
    j = 0
    for key in gen_keys:
        i = 0
        for t in times:
            ary = lst_g[str(t)][gen_keys[j]]
            data_g[j, i,:] = ary
            i = i + 1
        j = j + 1

    # display a plot - hard-wired assumption of 3 generators from Case 9
    fig, ax = plt.subplots(2,2, sharex = 'col')
    tmin = 0.0
    tmax = 48.0
    xticks = [0,6,12,18,24,30,36,42,48]
    for i in range(2):
        for j in range(2):
            ax[i,j].grid (linestyle = '-')
            ax[i,j].set_xlim(tmin,tmax)
            ax[i,j].set_xticks(xticks)

    ax[0,0].set_title ('Total Bus Loads')
    ax[0,0].set_ylabel(PD_UNITS)
    for i in range(data_b.shape[0]):
        ax[0,0].plot(hrs, data_b[i,:,PD_IDX], color=bus_color(i))

    ax[1,0].set_title ('Generator Outputs')
    ax[1,0].set_ylabel(PGEN_UNITS)
    for i in range(data_g.shape[0]):
        ax[1,0].plot(hrs, data_g[i,:,PGEN_IDX], color=unit_color (dict, i), linewidth=unit_width (dict,i))

    ax[0,1].set_title ('Bus Voltages')
    ax[0,1].set_ylabel(VMAG_UNITS)
    for i in range(data_b.shape[0]):
        ax[0,1].plot(hrs, data_b[i,:,VMAG_IDX], color=bus_color(i))

    ax[1,1].set_title ('Locational Marginal Prices')
    ax[1,1].set_ylabel(LMP_P_UNITS)
    for i in range(data_b.shape[0]):
        ax[1,1].plot(hrs, data_b[i,:,LMP_P_IDX], color=bus_color(i))

    ax[1,0].set_xlabel('Hours')
    ax[1,1].set_xlabel('Hours')

    plt.show()

if __name__ == '__main__':
    process_pypower ('ercot_8')
