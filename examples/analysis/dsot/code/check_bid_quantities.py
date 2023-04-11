import itertools
import json
from copy import deepcopy

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def get_first_h(data_st):
    """Gets the first hour of DA prices (DSO and retail)

    Args:
        data_st (list of list 48 float): clear DA prices

    Return:
        max_delta (int): worse hour in t
    """
    price = list()
    for m in range(len(data_st)):
        try:
            price.append(data_st[m][0])
        except:
            return price
    return price


def get_data_multiple_days(V_analis, days, pre_file, pos_file):
    """Read a defined number of days

    Args:
        V_analis (str): a portion of the file name
        days (int): number of days to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dic): Metadata of .json file
        start_time (str): Start time of the simulation
        Order (list of Metadata): list of matadata in proper time order

    """
    d1 = dict()
    for n in range(days * 12):
        file_name = V_analis + str(n) + '_metrics'
        file = open(pre_file + file_name + pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')

        d1.update(deepcopy(I_ver))

    I_ver = d1

    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    temp = [[]] * len(I_ver[times[0]].keys())
    j = 0
    for node in list(I_ver[times[0]].keys()):
        for t in times:
            temp[j].append(I_ver[t][node])
        j = j + 1

    Order = [[] for _ in range(len(meta_I_ver))]
    for m in meta_I_ver:
        index = meta_I_ver[m]['index']
        for t in range(len(temp[0])):
            Order[index].append(temp[0][t][index])

    return meta_I_ver, start_time, Order


def get_data_dso_bids_da(V_analis, days, pre_file, pos_file):
    """Read a defined number of days

    Args:
        V_analis (str): a portion of the file name
        days (int): number of days to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dic): Metadata of .json file
        start_time (str): Start time of the simulation
        Order (list of Metadata): list of matadata in proper time order

    """
    d1 = dict()
    for n in range(days * 12):
        file_name = V_analis + str(n) + '_metrics'
        file = open(pre_file + file_name + pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')

        d1.update(deepcopy(I_ver))

    I_ver = d1

    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    temp = [[]] * len(I_ver[times[0]].keys())
    j = 0
    for node in list(I_ver[times[0]].keys()):
        for t in times:
            temp[j].append(I_ver[t][node])
        j = j + 1

    Order = [[] for _ in range(len(meta_I_ver))]
    for m in meta_I_ver:
        index = meta_I_ver[m]['index']
        for t in range(len(temp[0])):
            Order[index].append(temp[0][t][index])

    return meta_I_ver, start_time, Order


def get_metrics_full_multiple_KEY(file_name, pre_file, pos_file):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys(i.e. "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    print(pre_file + file_name + pos_file)
    file = open(pre_file + file_name + pos_file, 'r')
    text = file.read()
    file.close()

    I_ver = json.loads(text)
    meta_I_ver = I_ver.pop('Metadata')

    temp = {}
    if 'bid_four_point_rt' in meta_I_ver.keys():
        temp.update({'bid_four_point_rt_1': {'units': 'kW', 'index': 0}})
        temp.update({'bid_four_point_rt_2': {'units': '$', 'index': 1}})
        temp.update({'bid_four_point_rt_3': {'units': 'kW', 'index': 2}})
        temp.update({'bid_four_point_rt_4': {'units': '$', 'index': 3}})
        temp.update({'bid_four_point_rt_5': {'units': 'kW', 'index': 4}})
        temp.update({'bid_four_point_rt_6': {'units': '$', 'index': 5}})
        temp.update({'bid_four_point_rt_7': {'units': 'kW', 'index': 6}})
        temp.update({'bid_four_point_rt_8': {'units': '$', 'index': 7}})
        for m in meta_I_ver.keys():
            if 'bid_four_point_rt' in m:
                pass
            else:
                temp.update({m: {'units': meta_I_ver[m]['units'], 'index': meta_I_ver[m]['index'] + 7}})

        meta_I_ver = temp

    start_time = I_ver.pop('StartTime')
    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))
    # print(times)
    # print(I_ver)
    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float)
    # print (x,y,z)
    j = 0
    for node in list(I_ver[times[0]].keys()):
        n = 0
        for t in times:
            temp = I_ver[t][node]

            try:
                len(I_ver[t][node][0])
                if len(I_ver[t][node][0]) > 1:
                    temp = []
                    for k in range(len(I_ver[t][node][0])):
                        for m in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][m])
                    for p in range(1, len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
                data_I_ver[j, n, :] = temp
            except TypeError:
                # print (data_I_ver[j,m,:])
                # print (I_ver[t][node])
                data_I_ver[j, n, :] = I_ver[t][node]
            n = n + 1
        j = j + 1

    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    Ip = pd.Panel(data_I_ver, major_axis=index)

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(axis=0))
    all_homes_I_ver.append(Ip.mean(axis=0))
    all_homes_I_ver.append(Ip.max(axis=0))
    all_homes_I_ver.append(Ip.sum(axis=0))

    data_individual = [pd.DataFrame(data_I_ver[m, :, :], index=index) for m in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual, list(I_ver[times[0]].keys())  # individual homes


def get_metrics_full_multiple_KEY_Mdays_H(file_name, pre_file, pos_file, days):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file
        days (int):

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys(i.e. "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    for n in range(days * 12):
        print(pre_file + file_name + str(n) + pos_file)
        file = open(pre_file + file_name + str(n) + pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')
        d1.update(deepcopy(I_ver))

    I_ver = d1

    temp = {}
    if 'bid_four_point_da' in meta_I_ver.keys():
        j = 0
        for m in range(48):
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': 'kW', 'index': j}})
            j = j + 1
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': '$', 'index': j}})
            j = j + 1
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': 'kW', 'index': j}})
            j = j + 1
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': '$', 'index': j}})
            j = j + 1
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': 'kW', 'index': j}})
            j = j + 1
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': '$', 'index': j}})
            j = j + 1
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': 'kW', 'index': j}})
            j = j + 1
            string_N = 'bid_four_point_rt_' + str(j + 1)
            temp.update({string_N: {'units': '$', 'index': j}})
            j = j + 1

    meta_I_ver = temp

    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float)
    names = []
    j = 0
    for node in list(I_ver[times[0]].keys()):
        n = 0
        for t in times:
            # print (node,t)
            temp = I_ver[t][node]
            if len(I_ver[t][node][0]) > 1:
                temp = []
                for k in range(len(I_ver[t][node][0])):
                    for m in range(len(I_ver[t][node][0][0])):
                        temp.append(I_ver[t][node][0][k][m])
                for p in range(1, len(I_ver[t][node])):
                    temp.append(I_ver[t][node][p])

            temp = list(itertools.chain.from_iterable(temp))
            data_I_ver[j, n, :] = temp
            n = n + 1
        names.append(node)
        j = j + 1
    meta_I_ver['names'] = names
    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    elif (int(times[1]) - int(times[0])) == 60 * 60:
        index = pd.date_range(start_time, periods=y, freq='60min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    # Ip = pd.Panel(data_I_ver,major_axis=index)
    #
    all_homes_I_ver = list()
    # all_homes_I_ver.append(Ip.min(axis=0))
    # all_homes_I_ver.append(Ip.mean(axis=0))
    # all_homes_I_ver.append(Ip.max(axis=0))
    # all_homes_I_ver.append(Ip.sum(axis=0))

    data_individual = [pd.DataFrame(data_I_ver[m, :, :], index=index) for m in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual  # individual homes


def get_metrics_full_multiple_KEY_Mdays(file_name, pre_file, pos_file, days):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file
        days (int):

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys(i.e. "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    # days = 1
    hours = days * 12
    for n in range(hours):
        print(pre_file + file_name + str(n) + pos_file)
        file = open(pre_file + file_name + str(n) + pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')
        d1.update(deepcopy(I_ver))

    I_ver = d1

    temp = {}
    if 'bid_four_point_rt' in meta_I_ver.keys():
        temp.update({'bid_four_point_rt_1': {'units': 'kW', 'index': 0}})
        temp.update({'bid_four_point_rt_2': {'units': '$', 'index': 1}})
        temp.update({'bid_four_point_rt_3': {'units': 'kW', 'index': 2}})
        temp.update({'bid_four_point_rt_4': {'units': '$', 'index': 3}})
        temp.update({'bid_four_point_rt_5': {'units': 'kW', 'index': 4}})
        temp.update({'bid_four_point_rt_6': {'units': '$', 'index': 5}})
        temp.update({'bid_four_point_rt_7': {'units': 'kW', 'index': 6}})
        temp.update({'bid_four_point_rt_8': {'units': '$', 'index': 7}})
        for m in meta_I_ver.keys():
            if 'bid_four_point_rt' in m:
                pass
            else:
                temp.update({m: {'units': meta_I_ver[m]['units'], 'index': meta_I_ver[m]['index'] + 7}})
    else:
        for m in meta_I_ver.keys():
            if 'bid_four_point_rt' in m:
                pass
            else:
                temp.update({m: {'units': meta_I_ver[m]['units'], 'index': meta_I_ver[m]['index']}})

    meta_I_ver = temp

    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)

    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float)

    j = 0
    for node in list(I_ver[times[0]].keys()):
        n = 0
        for t in times:
            # print (node,t)
            temp = I_ver[t][node]
            # print(I_ver[t])
            # print(node)
            # print(t)
            # print(I_ver[t][node][0])
            try:
                if len(I_ver[t][node][0]) > 1:
                    temp = []
                    for k in range(len(I_ver[t][node][0])):
                        for m in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][m])
                    for p in range(1, len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
            except TypeError:
                pass

            data_I_ver[j, n, :] = temp
            n = n + 1
        j = j + 1

    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    Ip = pd.Panel(data_I_ver, major_axis=index)

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(axis=0))
    all_homes_I_ver.append(Ip.mean(axis=0))
    all_homes_I_ver.append(Ip.max(axis=0))
    all_homes_I_ver.append(Ip.sum(axis=0))

    data_individual = [pd.DataFrame(data_I_ver[m, :, :], index=index) for m in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual, list(I_ver[times[0]].keys())  # individual homes


def get_substation_metrics_data(file_name, pre_file, pos_file):
    """Reads .json files with multiple Keys

        Args:
            file_name (str): name of json file to be read
            pre_file (str): pre-portion of the path to file
            pos_file (str): extension of the file

        Return:
            meta_I_ver (dict): with Key of the variable containing the index and units
            start_time (str): start time of simulation
            all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys(i.e. "agent")
            data_individual (list of DataFrame): variables for individual homes
        """
    print(pre_file + file_name + pos_file)
    file = open(pre_file + file_name + pos_file, 'r')
    text = file.read()
    file.close()

    I_ver = json.loads(text)
    meta_I_ver = I_ver.pop('Metadata')

    temp = {}
    if 'bid_four_point_rt' in meta_I_ver.keys():
        temp.update({'bid_four_point_rt_1': {'units': 'kW', 'index': 0}})
        temp.update({'bid_four_point_rt_2': {'units': '$', 'index': 1}})
        temp.update({'bid_four_point_rt_3': {'units': 'kW', 'index': 2}})
        temp.update({'bid_four_point_rt_4': {'units': '$', 'index': 3}})
        temp.update({'bid_four_point_rt_5': {'units': 'kW', 'index': 4}})
        temp.update({'bid_four_point_rt_6': {'units': '$', 'index': 5}})
        temp.update({'bid_four_point_rt_7': {'units': 'kW', 'index': 6}})
        temp.update({'bid_four_point_rt_8': {'units': '$', 'index': 7}})
        for m in meta_I_ver.keys():
            if 'bid_four_point_rt' in m:
                pass
            else:
                temp.update({m: {'units': meta_I_ver[m]['units'], 'index': meta_I_ver[m]['index'] + 7}})

        meta_I_ver = temp

    start_time = I_ver.pop('StartTime')
    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))
    # print(times)
    # print(I_ver)
    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float)
    # print (x,y,z)
    j = 0
    for node in list(I_ver[times[0]].keys()):
        n = 0
        for t in times:
            temp = I_ver[t][node]

            try:
                len(I_ver[t][node][0])
                if len(I_ver[t][node][0]) > 1:
                    temp = []
                    for k in range(len(I_ver[t][node][0])):
                        for m in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][m])
                    for p in range(1, len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
                data_I_ver[j, n, :] = temp
            except TypeError:
                # print (data_I_ver[j,n,:])
                # print (I_ver[t][node])
                data_I_ver[j, n, :] = I_ver[t][node]
            n = n + 1
        j = j + 1

    return data_I_ver, meta_I_ver


def get_substation_data(file_name, pre_file, pos_file):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys(i.e. "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    print(pre_file + file_name + pos_file)
    file = open(pre_file + file_name + pos_file, 'r')
    text = file.read()
    file.close()

    I_ver = json.loads(text)
    meta_I_ver = I_ver.pop('Metadata')

    temp = {}
    if 'bid_four_point_rt' in meta_I_ver.keys():
        temp.update({'bid_four_point_rt_1': {'units': 'kW', 'index': 0}})
        temp.update({'bid_four_point_rt_2': {'units': '$', 'index': 1}})
        temp.update({'bid_four_point_rt_3': {'units': 'kW', 'index': 2}})
        temp.update({'bid_four_point_rt_4': {'units': '$', 'index': 3}})
        temp.update({'bid_four_point_rt_5': {'units': 'kW', 'index': 4}})
        temp.update({'bid_four_point_rt_6': {'units': '$', 'index': 5}})
        temp.update({'bid_four_point_rt_7': {'units': 'kW', 'index': 6}})
        temp.update({'bid_four_point_rt_8': {'units': '$', 'index': 7}})
        for m in meta_I_ver.keys():
            if 'bid_four_point_rt' in m:
                pass
            else:
                temp.update({m: {'units': meta_I_ver[m]['units'], 'index': meta_I_ver[m]['index'] + 7}})

        meta_I_ver = temp

    start_time = I_ver.pop('StartTime')
    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))
    # print(times)
    # print(I_ver)
    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float)
    # print (x,y,z)
    j = 0
    for node in list(I_ver[times[0]].keys()):
        n = 0
        for t in times:
            temp = I_ver[t][node]

            try:
                len(I_ver[t][node][0])
                if len(I_ver[t][node][0]) > 1:
                    temp = []
                    for k in range(len(I_ver[t][node][0])):
                        for m in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][m])
                    for p in range(1, len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
                data_I_ver[j, n, :] = temp
            except TypeError:
                # print (data_I_ver[j,n,:])
                # print (I_ver[t][node])
                data_I_ver[j, n, :] = I_ver[t][node]
            n = n + 1
        j = j + 1

    return data_I_ver, meta_I_ver


pre_file_out = 'flexhvacwh3/'  #
pos_fle = '.json'
idays = 1
imonth = 8
iday = 19
Tday = 2
dso_num = 2

Water = 1
Water_agent = 1
pre_fle = pre_file_out + 'DSO_' + str(dso_num) + '/'
pre_file_sub = pre_file_out + 'Substation_' + str(dso_num) + '/'

# ### Current time for plotting of DSO curves
hour_of_day = 0  # anywhere from 0 to 23
day_of_sim = 0  # starts from 0. 0 means the 1st day of simulation

V_file = 'retail_market_Substation_2_3600'
meta_I_v, start_t, order = get_data_multiple_days(V_file, idays, pre_fle, pos_fle)
V_analis1 = 'cleared_quantity_da'
first_h = get_first_h(data_st=order[meta_I_v[V_analis1]['index']])

first_h_df = pd.DataFrame(first_h)
first_h_df.index = pd.date_range(start_t, periods=len(first_h), freq='1H')
first_h_df_rt = first_h_df.resample('5min').ffill()

V_file = 'retail_market_Substation_2_300'
meta_I_v, start_t, order = get_data_multiple_days(V_file, idays, pre_fle, pos_fle)
V_analis1 = 'cleared_quantity_rt'
V_analis2 = 'cleared_quantity_rt_unadj'
first_h_rt = order[meta_I_v[V_analis1]['index']]
first_h_rt_unadjusted = order[meta_I_v[V_analis2]['index']]

V_file = 'dso_ames_bid_Substation_2_3600'
meta_I_v, start_t, order = get_data_dso_bids_da(V_file, idays, pre_fle, pos_fle)
V_analis1 = 'unresponsive_bid_da'
V_analis2 = 'responsive_bid_da'
first_h_da = order[meta_I_v[V_analis1]['index']]
first_h_da2 = order[meta_I_v[V_analis2]['index']]
unresponsive_bid_da = np.array(first_h_da).reshape(24 * idays)
responsive_bid_da = np.array(first_h_da2).reshape(24 * idays)

unresponsive_bid_da_df = pd.DataFrame(unresponsive_bid_da)
unresponsive_bid_da_df.index = pd.date_range('2016-08-11 00:00:00', periods=len(unresponsive_bid_da), freq='1H')
unresponsive_bid_da_df_rt = unresponsive_bid_da_df.resample('5min').ffill()
responsive_bid_da_df = pd.DataFrame(responsive_bid_da)
responsive_bid_da_df.index = pd.date_range('2016-08-11 00:00:00', periods=len(responsive_bid_da), freq='1H')
responsive_bid_da_df_rt = responsive_bid_da_df.resample('5min').ffill()

V_file = 'dso_ames_bid_Substation_2_300'
meta_I_v, start_t, order = get_data_multiple_days(V_file, idays, pre_fle, pos_fle)
V_analis1 = 'unresponsive_bid_rt'
V_analis2 = 'responsive_bid_rt'
first_h_unr_rt = order[meta_I_v[V_analis1]['index']]
first_h_resp_rt = order[meta_I_v[V_analis2]['index']]

with open("flexhvacwh3/DSO_2/Substation_" + str(dso_num) + "_agent_dict.json", 'r', encoding='utf-8') as lp:
    config = json.load(lp)

dso_config = config['markets']['DSO_1']
num_of_customers = dso_config['number_of_customers']
customer_count_mix_residential = dso_config['RCI_customer_count_mix']['residential']
number_of_gld_homes = dso_config['number_of_gld_homes']
scale = (num_of_customers * customer_count_mix_residential / number_of_gld_homes)
V_file = 'Substation_{}_metrics_substation'.format(dso_num)
data_s, meta_S = get_substation_data(V_file, pre_file_sub, pos_fle)

# # aggregated house load without battery
V_analis1 = 'real_power_avg'
V_analis2 = 'real_power_min'
V_analis3 = 'real_power_max'
sub_power_avg = data_s[0, 12:, meta_S[V_analis1]['index']]
sub_power_min = data_s[0, 12:, meta_S[V_analis2]['index']]
sub_power_max = data_s[0, 12:, meta_S[V_analis3]['index']]

V_file = 'Substation_{}_metrics_house'.format(dso_num)

#
# wh_load_avg = data_s[0,12:,meta_S[V_analis1]['index']]
#
# pre_fle = pre_file_out + 'Substation_' + str(dso_num) + '/'
#
# meta_S, start_t, data_s, data_i, data_key = get_metrics_full_multiple_KEY(V_file, pre_fle, pos_fle)
data_s, meta_S = get_substation_metrics_data(V_file, pre_file_sub, pos_fle)
V_analis1 = 'waterheater_load_avg'
V_analis2 = 'waterheater_setpoint_avg'
V_analis3 = 'waterheater_temp_avg'
V_analis4 = 'waterheater_demand_avg'

wh_load_avg = data_s[0, 12:, meta_S[V_analis1]['index']]
wh_setp_avg = data_s[0, 12:, meta_S[V_analis2]['index']]
wh_temp_avg = data_s[0, 12:, meta_S[V_analis3]['index']]
wh_demand_avg = data_s[0, 12:, meta_S[V_analis4]['index']]

fig1, ax1 = plt.subplots(3, sharex='col')

ax1[0].plot(first_h_df_rt.values / 1e3, label='DA Cleared')
# print(len(first_h_df_rt.index[1:]),len(first_h_rt))
# plt.plot(first_h_rt,label='RT');plt.legend();plt.ylabel('price ($/kWh)');plt.xlabel('time (5-min)');plt.grid(True);
ax1[0].plot(np.array(first_h_rt) / 1e3, label='RT Cleared')
ax1[0].plot(np.array(first_h_rt_unadjusted) / 1e3, label='RT Bid from Previous Method')
ax1[0].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind', linewidth=0.75)

ax1[0].grid(True)
ax1[0].set_ylabel('MW')
ax1[0].legend(loc='best')
ax1[0].set_title("Retail Market Bids flexhvacwh3")

# ax1[1].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind')
ax1[1].plot(range(264, len(unresponsive_bid_da_df_rt) - 24),
            (unresponsive_bid_da_df_rt.values[288:] + responsive_bid_da_df_rt.values[288:]), label='DSO DA Bid to AMES')
ax1[1].plot(range(287, len(first_h_unr_rt) + 287), np.array(first_h_unr_rt) + np.array(first_h_resp_rt),
            label='DSO RT Bid to AMES')
plt.legend()
plt.ylabel('quantity (MW)')
ax1[1].grid(True)
ax1[1].set_ylabel('MW')
ax1[1].legend(loc='best')
ax1[1].set_title("DSO Bids flexhvacwh3")

# ax1[2].plot(np.array(first_h_rt)/1e3,label='RT Cleared')
ax1[2].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind', linewidth=2)
ax1[2].plot((3657.145492 + (sub_power_min * scale / 1e6)), label='Min GLD Load Scaled + Ind', linewidth=0.5)
ax1[2].plot((3657.145492 + (sub_power_max * scale / 1e6)), label='Max GLD Load Scaled + Ind', linewidth=0.5)
ax1[2].grid(True)
ax1[2].set_ylabel('MW')
ax1[2].legend(loc='best')
ax1[2].set_title("Bid to Load Comparison flexhvacwh3")

# plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
plt.show()
first_h_rt = pd.DataFrame(first_h_rt)

# ### new waterheater agent
if Water_agent and 1:
    pre_fle = pre_file_out + 'Substation_' + str(dso_num) + '/'
    V_file = 'Substation_2_metrics_house'
    meta_S, start_t, data_s, data_i, data_key = get_metrics_full_multiple_KEY(V_file, pre_fle, pos_fle)
    # print (data_key)

    agent_dict = "Substation_{}_agent_dict.json".format(dso_num)
    fle = open(pre_file_out + 'DSO_{}/'.format(dso_num) + agent_dict, 'r')
    txt = fle.read()
    fle.close()
    all_agent = json.loads(txt)
    hvac_agent = all_agent['hvacs']
    property_name = 'cooling_participating'
    # hvac_agent[meta_da['names'][i]][property_name]

    GLD_power = {}
    participating_hvac = {}
    for i in range(len(data_i)):
        AVG_power = data_i[i][meta_S[V_analis1]['index']]
        GLD_power.update({data_key[i]: AVG_power})
        AVG_power2 = data_i[i][meta_S[V_analis2]['index']]
        # if False:#not (data_key[i] == 'R5_12_47_2_tn_133_hse_1' or data_key[i] == 'R5_12_47_2_load_10_bldg_82_zone_all'):
        #     continue
        if data_key[i] not in hvac_agent.keys():
            continue
        elif hvac_agent[data_key[i]][property_name]:
            idx = data_i[i][meta_S[V_analis1]['index']].resample('60min').mean().index
            participating_hvac.update(
                {data_key[i]: data_i[i][meta_S[V_analis1]['index']].resample('60min').mean().values})
        # plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x')
        # plt.ylabel('hvac load (kW)');plt.xlabel('time (hours)')
        # plt.grid(True)
        # plt.title('home: '+str(data_key[i]))
        # plt.show()
        # plt.plot((AVG_power2).values,marker='x')
        # plt.ylabel('room temperature (F)')
        # plt.xlabel('time (hours)')
        # plt.grid(True)
        # plt.title('home: '+str(data_key[i]))
        # plt.show()
        # (data_i[i])
    participating_hvac_df = pd.DataFrame(data=participating_hvac, index=idx)
    participating_hvac_agg = participating_hvac_df.sum(axis=1)
    plt.plot(participating_hvac_agg.index, participating_hvac_agg.values)
    plt.show()

    pre_fle = pre_file_out + 'DSO_2/'
    V_file = 'water_heater_agent_Substation_2_3600'
    meta_da, start_t, data_da, da_bid_wh, data_keys_da = \
        get_metrics_full_multiple_KEY_Mdays_H(V_file, pre_fle, '_metrics' + pos_fle, idays)

    V_file = 'water_heater_agent_Substation_{}_300'.format(dso_num)
    meta_rt, start_t, data_rt, rt_bid_wh, data_keys = \
        get_metrics_full_multiple_KEY_Mdays(V_file, pre_fle, '_metrics' + pos_fle, idays)

    to_kW = 1
    agent_dict = "Substation_{}_agent_dict.json".format(dso_num)
    fle = open(pre_fle + agent_dict, 'r')
    txt = fle.read()
    fle.close()
    all_agent = json.loads(txt)
    hvac_agent = all_agent['waterheater']
    # hvac_agent[meta_da['names'][i]]['slider_setting']
    prop = []
    opt = []
    dev = []
    fig1, ax1 = plt.subplots(2, sharex='col')
    # ax2 = ax1.twinx()
    for i in range(len(rt_bid_wh)):
        if data_keys_da[i] == "R5_12_47_2_tn_133_hse_1":
            opt_bid = da_bid_wh[i][meta_da['bid_four_point_rt_3']['index']]
            # print(meta_da)
            # print(da_bid_hvac)
            # print(opt_bid)
            ax1[0].plot((opt_bid.resample('60min').mean() / to_kW).values, label='optimal bid')
            actual = participating_hvac_df[
                data_keys_da[i]]  # rt_bid_hvac[i][meta_rt['inverter_p_setpoint']['index']]
            # ax1[0].plot(-(actual.resample('60min').mean() / 1000).values, label='actual power')
            ax1[0].plot(actual.values, label='actual power')
            ax1[0].set_ylabel('kW')
            ax1[0].grid(True)
            ax1[0].set_title(
                "Optimal bid and actual kW by hvac agent with slider setting {}".format(
                    0.71))  # ax1.set_ylabel('(F)');
            ax1[0].legend()

            if data_keys_da[i] == "R5_12_47_2_tn_4_hse_3":  # "R5_12_47_2_tn_3_hse_5":
                # i = 5
                opt_bid = da_bid_hvac[i][meta_da['bid_four_point_rt_3']['index']]
            ax1[1].plot((opt_bid.resample('60min').mean() / to_kW).values, label='optimal bid')
            actual = participating_hvac_df[
                data_keys_da[i]]  # rt_bid_hvac[i][meta_rt['inverter_p_setpoint']['index']]
            # ax1[1].plot(-(actual.resample('60min').mean() / 1000).values, label='actual power')
            ax1[1].plot(actual.values, label='actual power')
            ax1[1].set_ylabel('kW')
            ax1[1].grid(True)
            ax1[1].set_title(
                "Optimal bid and actual kW by battery agent with slider setting {}".format(
                    0.1225))  # 0.0295
            ax1[1].legend()
            plt.xlabel('time (hours)')
            plt.show()

if Water:
    # plot for upper setpoints and lower setpoints
    pre_fle = pre_file_out + 'DSO_2/'
    V_file = 'water_heater_agent_Substation_2_300'
    # meta_I_v, start_t, order = get_data_multiple_days(V_file, idays, pre_fle, pos_fle)

    meta_S, start_t, data_s, data_i = \
        get_metrics_full_multiple_KEY_Mdays(V_file, pre_fle, '_metrics' + pos_fle, idays)
    # V_analis1 = 'upper_tank_setpoint'

    idx = [382]  # index that needs to be collected
    data_s_modified = data_s[3][idx].sort_index()  # sorts the data in interval of eighth bid

    # # AVG_power = order[2][meta_S[V_analis1]['index']]
    # AVG_power = order[meta_I_v[V_analis1]['index']]
    # to_kW = 1
    # plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x');
    # plt.ylabel('Upper tank setpoint (F)');
    # plt.xlabel('time (hours)');
    # plt.grid(True);
    # plt.show()
    # V_analis1 = 'lower_tank_setpoint'
    # AVG_power = data_s[1][meta_S[V_analis1]['index']]
    # plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x');
    # plt.ylabel('Lower tank setpoint (F)');
    # plt.xlabel('time (hours)');
    # plt.grid(True);
    # plt.show()
    # V_analis1 = 'upper_tank_setpoint'
    # for i in range(len(data_i)):
    #     AVG_power = data_i[i][meta_S[V_analis1]['index']]
    #     plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x');
    #     plt.ylabel('UPPER_SETPOINT(kW)');
    #     plt.xlabel('time (hours)');
    #     plt.grid(True);
    #     plt.title('home: ' + str(i));
    #     plt.show()
    #
    # V_analis1 = 'waterheater_load_avg'
    # AVG_power = data_s[1][meta_S[V_analis1]['index']]  # plots mean
    # to_kW = 1
    # plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x');
    # plt.ylabel('aggregated mean water heater power (kW)');
    # plt.xlabel('time (hours)');
    # plt.grid(True);
    # plt.show()
    # for i in range(len(data_i) * 0):
    #     AVG_power = data_i[i][meta_S[V_analis1]['index']]
    #     plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x');
    #     plt.ylabel('water heater power (kW)');
    #     plt.xlabel('time (hours)');
    #     plt.grid(True);
    #     plt.title('home: ' + str(i));
    #     plt.show()
    # V_analis1 = 'waterheater_load_max'
    # AVG_power = data_s[0][meta_S[V_analis1]['index']]  # plots min
    # plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x');
    # plt.ylabel('min min water heater power (kW)');
    # plt.xlabel('time (hours)');
    # plt.grid(True);
    # plt.show()
    # AVG_power = data_s[2][meta_S[V_analis1]['index']]  # plots max
    # plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x');
    # plt.ylabel('max max water heater power (kW)');
    # plt.xlabel('time (hours)');
    # plt.grid(True);
    # plt.show()
