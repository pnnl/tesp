#	Copyright (C) 2017-2018 Battelle Memorial Institute
# file: process_agents.py
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def process_agents(nameroot, dictname = ''):
    # first, read and print a dictionary of relevant agents
    if len (dictname) > 0:
        lp = open (dictname).read()
    else:
        lp = open (nameroot + '_agent_dict.json').read()
    dict = json.loads(lp)
    a_keys = list(dict['markets'].keys())
    a_keys.sort()
    c_keys = list(dict['controllers'].keys())
    c_keys.sort()
    print("\nMarket Dictionary:")
    print("ID Period Unit Init StDev")
    for key in a_keys:
        row = dict['markets'][key]
        print (key, row['period'], row['unit'], row['init_price'], row['init_stdev'])
    print("\nController Dictionary:")
    print("ID House Mode BaseDaylight Ramp Offset Cap")
    for key in c_keys:
        row = dict['controllers'][key]
        print (key, row['houseName'], row['control_mode'], row['daylight_set'], row['ramp'], row['offset_limit'], row['price_cap'])

    # read the auction metrics file
    lp_a = open ("auction_" + nameroot + "_metrics.json").read()
    lst_a = json.loads(lp_a)
    print ("\nAuction Metrics data starting", lst_a['StartTime'])

    # make a sorted list of the times, and NumPy array of times in hours
    lst_a.pop('StartTime')
    meta_a = lst_a.pop('Metadata')
    times = list(map(int,list(lst_a.keys())))
    times.sort()
    print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # parse the metadata for things of specific interest
    print ("\nAuction Metadata [Variable Index Units]")
    for key, val in meta_a.items():
        print (key, val['index'], val['units'])
        if key == 'clearing_price':
            CLEAR_IDX = val['index']
            CLEAR_UNITS = val['units']

    # create a NumPy array of all auction metrics
    data_a = np.empty(shape=(len(a_keys), len(times), len(lst_a[str(times[0])][a_keys[0]])), dtype=np.float)
    print ("\nConstructed", data_a.shape, "NumPy array for Auctions")
    j = 0
    for key in a_keys:
        i = 0
        for t in times:
            ary = lst_a[str(t)][a_keys[j]]
            data_a[j, i,:] = ary
            i = i + 1
        j = j + 1

    # read the controller metrics file
    lp_c = open ("controller_" + nameroot + "_metrics.json").read()
    lst_c = json.loads(lp_c)
    print ("\nController Metrics data starting", lst_c['StartTime'])

    # parse the metadata for things of specific interest
    # c_keys = ['house1_R1_12_47_1_tm_507_thermostat_controller']
    lst_c.pop('StartTime')
    meta_c = lst_c.pop('Metadata')
    print ("\nController Metadata [Variable Index Units]")
    for key, val in meta_c.items():
        print (key, val['index'], val['units'])
        if key == 'bid_price':
            BID_P_IDX = val['index']
            BID_P_UNITS = val['units']
        elif key == 'bid_quantity':
            BID_Q_IDX = val['index']
            BID_Q_UNITS = val['units']

    # create a NumPy array of all controller metrics - many are "missing" zero-bids
    data_c = np.empty(shape=(len(c_keys), len(times), len(meta_c.items())), dtype=np.float)
    print ("\nConstructed", data_c.shape, "NumPy array for Controllers")
    zary = np.zeros(len(meta_c.items()))
    j = 0
    for key in c_keys:
        i = 0
        for t in times:
            if c_keys[j] in lst_c[str(t)]:
                ary = lst_c[str(t)][c_keys[j]]
            else:
                ary = zary
            data_c[j, i,:] = ary
            i = i + 1
        j = j + 1

    # display a plot
    fig, ax = plt.subplots(2,1, sharex = 'col')

    ax[0].plot(hrs, data_a[0,:,CLEAR_IDX], color="blue", label="Cleared")
    ax[0].plot(hrs, data_c[0,:,BID_P_IDX], color="red", label="Bid")
    ax[0].set_ylabel(CLEAR_UNITS)
    ax[0].set_title ("Prices at " + a_keys[0] + ":" + c_keys[0])
    ax[0].legend(loc='best')

    ax[1].plot(hrs, data_c[0,:,BID_Q_IDX], color="red", marker="o", label="Quantity")
    ax[1].set_ylabel(BID_Q_UNITS)
    ax[1].set_title ("Bid Quantity at " + c_keys[0])
    ax[1].set_xlabel("Hours")

    plt.show()

