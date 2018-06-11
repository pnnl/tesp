#	Copyright (C) 2017 Battelle Memorial Institute
# file: process_matpower.py
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def process_matpower (nameroot):
    # first, read and print a dictionary of relevant MATPOWER objects
    lp = open (nameroot + "_m_dict.json").read()
    dict = json.loads(lp)
    baseMVA = dict['baseMVA']
    ampFactor = dict['ampFactor']
    gen_keys = list(dict['generators'].keys())
    gen_keys.sort()
    bus_keys = list(dict['fncsBuses'].keys())
    bus_keys.sort()
    print ("\n\nFile", nameroot, "has baseMVA", baseMVA, "with GLD load scaling =", ampFactor)
    print("\nGenerator Dictionary:")
    print("Unit Bus Type Pnom Pmax Costs[Start Stop C2 C1 C0]")
    for key in gen_keys:
        row = dict['generators'][key]
        print (key, row['bus'], row['bustype'], row['Pnom'], row['Pmax'], "[", row['StartupCost'], row['ShutdownCost'], row['c2'], row['c1'], row['c0'], "]")
    print("\nFNCS Bus Dictionary:")
    print("Bus Pnom Qnom [GridLAB-D Substations]")
    for key in bus_keys:
        row = dict['fncsBuses'][key]
        print (key, row['Pnom'], row['Qnom'], row['GLDsubstations'])

    # read the bus metrics file
    lp_b = open ("bus_" + nameroot + "_metrics.json").read()
    lst_b = json.loads(lp_b)
    print ("\nBus Metrics data starting", lst_b['StartTime'])

    # make a sorted list of the times, and NumPy array of times in hours
    lst_b.pop('StartTime')
    #lst_b.pop('System base MVA')
    #lst_b.pop('Number of buses')
    #lst_b.pop('Number of generators')
    #lst_b.pop('Network name')
    meta_b = lst_b.pop('Metadata')
    times = list(map(int,list(lst_b.keys())))
    times.sort()
    print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # parse the metadata for things of specific interest
    print ("\nBus Metadata [Variable Index Units] for", len(lst_b[str(times[0])]), "objects")
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
        elif key == 'PQ':
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
    print ("\nConstructed", data_b.shape, "NumPy array for Buses")
    j = 0
    for key in bus_keys:
        i = 0
        for t in times:
            ary = lst_b[str(t)][bus_keys[j]]
            data_b[j, i,:] = ary
            i = i + 1
        j = j + 1

    # display some averages
    print ("Average real power LMP =", data_b[0,:,LMP_P_IDX].mean(), LMP_P_UNITS)
    print ("Maximum real power LMP =", data_b[0,:,LMP_P_IDX].max(), LMP_P_UNITS)
    print ("First day LMP mean/std dev=", data_b[0,0:287,LMP_P_IDX].mean(), data_b[0,0:287,LMP_P_IDX].std())
    print ("Maximum bus voltage =", data_b[0,:,VMAG_IDX].max(), VMAG_UNITS)
    print ("Minimum bus voltage =", data_b[0,:,VMIN_IDX].max(), VMIN_UNITS)

    # read the generator metrics file
    lp_g = open ("gen_" + nameroot + "_metrics.json").read()
    lst_g = json.loads(lp_g)
    print ("\nGenerator Metrics data starting", lst_g['StartTime'])
    # make a sorted list of the times, and NumPy array of times in hours
    lst_g.pop('StartTime')
    meta_g = lst_g.pop('Metadata')
    print ("\nGenerator Metadata [Variable Index Units] for", len(lst_g[str(times[0])]), "objects")
    for key, val in meta_g.items():
        print (key, val['index'], val['units'])
        if key == 'Pgen':
            PGEN_IDX = val['index']
            PGEN_UNITS = val['units']
        elif key == 'Qgen':
            QGEN_IDX = val['index']
            QGEN_UNITS = val['units']

    # create a NumPy array of all bus metrics
    data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[str(times[0])][gen_keys[0]])), dtype=np.float)
    print ("\nConstructed", data_g.shape, "NumPy array for Generators")
    j = 0
    for key in gen_keys:
        i = 0
        for t in times:
            ary = lst_g[str(t)][gen_keys[j]]
            data_g[j, i,:] = ary
            i = i + 1
        j = j + 1

    # display a plot - hard-wired assumption of 3 generators from Case 9
    fig, ax = plt.subplots(4,2, sharex = 'col')

    ax[0,0].plot(hrs, data_b[0,:,PD_IDX], color="blue", label="Real")
    ax[0,0].plot(hrs, data_b[0,:,QD_IDX], color="red", label="Reactive")
    ax[0,0].set_ylabel(PD_UNITS + "/" + QD_UNITS)
    ax[0,0].set_title ("Demands at " + bus_keys[0])
    ax[0,0].legend(loc='best')

    ax[1,0].plot(hrs, data_b[0,:,LMP_P_IDX], color="blue", label="Real")
    ax[1,0].plot(hrs, data_b[0,:,LMP_Q_IDX], color="red", label="Reactive")
    ax[1,0].set_ylabel(LMP_P_UNITS)
    ax[1,0].set_title ("Prices at " + bus_keys[0])
    ax[1,0].legend(loc='best')

    ax[2,0].plot(hrs, data_b[0,:,VMAG_IDX], color="blue", label="Magnitude")
    ax[2,0].plot(hrs, data_b[0,:,VMAX_IDX], color="red", label="Vmax")
    ax[2,0].plot(hrs, data_b[0,:,VMIN_IDX], color="green", label="Vmin")
    ax[2,0].set_xlabel("Hours")
    ax[2,0].set_ylabel(VMAG_UNITS)
    ax[2,0].set_title ("Voltages at " + bus_keys[0])
    ax[2,0].legend(loc='best')

    for i in range(0,4):
        ax[i,1].plot(hrs, data_g[i,:,PGEN_IDX], color="blue", label="P")
        ax[i,1].plot(hrs, data_g[i,:,QGEN_IDX], color="red", label="Q")
        ax[i,1].set_ylabel(PGEN_UNITS + "/" + QGEN_UNITS)
        ax[i,1].set_title ("Output from unit " + gen_keys[i])
        ax[i,1].legend(loc='best')
    ax[2,1].set_xlabel("Hours")

    plt.show()

