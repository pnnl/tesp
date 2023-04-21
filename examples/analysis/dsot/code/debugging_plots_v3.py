"""
    This file assists visual debugging analyses

    Develop only for debugging purposes 
        
    Intended for simple fast visual plots (works better on IDE so multiple plots can be compared)
    Does not save plots to file
"""
import datetime
import itertools
import json
import warnings
from copy import deepcopy

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt

# ####################################################start conf plot
plt.rcParams['figure.figsize'] = (4, 8)
plt.rcParams['figure.dpi'] = 100
SMALL_SIZE = 14
MEDIUM_SIZE = 16
BIGGER_SIZE = 16
plt.rcParams["font.family"] = "Times New Roman"
plt.rc('font', size=SMALL_SIZE)  # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)  # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title


# ####################################################end conf plot

def get_metrics_full_multiple_KEY_Mdays_H(file_name, pre_file, pos_file):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    for n in range(int(days * 24)):
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
        for i in range(48):
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
    #        for i in meta_I_ver.keys():
    #            if 'bid_four_point_rt' in i:
    #                pass
    #            else:
    #                temp.update({i:{'units':meta_I_ver[i]['units'],'index':meta_I_ver[i]['index']+7}})

    meta_I_ver = {}
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
        i = 0
        for t in times:
            # print (node,t)
            temp = I_ver[t][node]
            if len(I_ver[t][node][0]) > 1:
                temp = []
                for k in range(len(I_ver[t][node][0])):
                    for l in range(len(I_ver[t][node][0][0])):
                        temp.append(I_ver[t][node][0][k][l])
                for p in range(1, len(I_ver[t][node])):
                    temp.append(I_ver[t][node][p])

            temp = list(itertools.chain.from_iterable(temp))
            data_I_ver[j, i, :] = temp
            i = i + 1
        j = j + 1

    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    elif (int(times[1]) - int(times[0])) == 60 * 60:
        index = pd.date_range(start_time, periods=y, freq='60min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    # Ip = pd.Panel(data_I_ver,major_axis=index)
    data = data_I_ver.reshape(np.shape(data_I_ver)[2], np.shape(data_I_ver)[1] * np.shape(data_I_ver)[0]).T
    Ip = pd.DataFrame(data=data, index=pd.MultiIndex.from_product([index, range(np.shape(data_I_ver)[0])]),
                      columns=range(np.shape(data_I_ver)[2]))

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(level=0))  # use axis if using panel
    all_homes_I_ver.append(Ip.mean(level=0))
    all_homes_I_ver.append(Ip.max(level=0))
    all_homes_I_ver.append(Ip.sum(level=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual, list(I_ver[times[0]].keys())  # indovidual homes


def get_metrics_full_multiple_KEY_Mdays(file_name, pre_file, pos_file):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    # days = 1
    hours = int(days * 24)
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
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i: {'units': meta_I_ver[i]['units'], 'index': meta_I_ver[i]['index'] + 8}})
    else:
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i: {'units': meta_I_ver[i]['units'], 'index': meta_I_ver[i]['index']}})

    meta_I_ver = {}
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
        i = 0
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
                        for l in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][l])
                    for p in range(1, len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
            except TypeError:
                pass

            # temp = list(itertools.chain.from_iterable(temp))
            data_I_ver[j, i, :] = temp
            i = i + 1
        j = j + 1

    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    # Ip = pd.Panel(data_I_ver,major_axis=index)

    data = data_I_ver.reshape(np.shape(data_I_ver)[2], np.shape(data_I_ver)[1] * np.shape(data_I_ver)[0]).T
    Ip = pd.DataFrame(data=data, index=pd.MultiIndex.from_product([index, range(np.shape(data_I_ver)[0])]),
                      columns=range(np.shape(data_I_ver)[2]))

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(level=0))  # use axis if using panel
    all_homes_I_ver.append(Ip.mean(level=0))
    all_homes_I_ver.append(Ip.max(level=0))
    all_homes_I_ver.append(Ip.sum(level=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual, list(I_ver[times[0]].keys())  # indovidual homes


def get_metrics_full_multiple_KEY_Mdays_wh(file_name, pre_file, pos_file):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    # days = 1
    hours = int(days * 24)
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
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i: {'units': meta_I_ver[i]['units'], 'index': meta_I_ver[i]['index'] + 8}})
    else:
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i: {'units': meta_I_ver[i]['units'], 'index': meta_I_ver[i]['index']}})

    meta_I_ver = {}
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
        i = 0
        for t in times:
            # print (node,t)
            temp = I_ver[t][node]
            # print(I_ver[t])
            # print(node)
            # print(t)
            # print(I_ver[t][node][0])

            temp = []
            for x in range(0, len(I_ver[t][node])):
                try:
                    for k in range(len(I_ver[t][node][x])):
                        for l in range(len(I_ver[t][node][x][0])):
                            temp.append(I_ver[t][node][x][k][l])
                except:
                    temp.append(I_ver[t][node][x])

            data_I_ver[j, i, :] = temp
            i = i + 1
        j = j + 1

    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    # Ip = pd.Panel(data_I_ver,major_axis=index)

    data = data_I_ver.reshape(np.shape(data_I_ver)[2], np.shape(data_I_ver)[1] * np.shape(data_I_ver)[0]).T
    Ip = pd.DataFrame(data=data, index=pd.MultiIndex.from_product([index, range(np.shape(data_I_ver)[0])]),
                      columns=range(np.shape(data_I_ver)[2]))

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(level=0))  # use axis if using panel
    all_homes_I_ver.append(Ip.mean(level=0))
    all_homes_I_ver.append(Ip.max(level=0))
    all_homes_I_ver.append(Ip.sum(level=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual, list(I_ver[times[0]].keys())  # indovidual homes


def get_metrics_full_multiple_KEY(file_name, pre_file, pos_file, to_hour=True):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
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
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i: {'units': meta_I_ver[i]['units'], 'index': meta_I_ver[i]['index'] + 7}})

        meta_I_ver = {}
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
        i = 0
        for t in times:
            temp = I_ver[t][node]

            try:
                len(I_ver[t][node][0])
                if len(I_ver[t][node][0]) > 1:
                    temp = []
                    for k in range(len(I_ver[t][node][0])):
                        for l in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][l])
                    for p in range(1, len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
                data_I_ver[j, i, :] = temp
            except TypeError:
                # print (data_I_ver[j,i,:])
                # print (I_ver[t][node])
                data_I_ver[j, i, :] = I_ver[t][node]
            i = i + 1
        j = j + 1

    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    # pd.Panel has been depracated
    # Ip = pd.Panel(data_I_ver,major_axis=index)

    data = data_I_ver.reshape(np.shape(data_I_ver)[2], np.shape(data_I_ver)[1] * np.shape(data_I_ver)[0]).T
    Ip = pd.DataFrame(data=data, index=pd.MultiIndex.from_product([index, range(np.shape(data_I_ver)[0])]),
                      columns=range(np.shape(data_I_ver)[2]))

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(level=0))  # use axis if using panel
    all_homes_I_ver.append(Ip.mean(level=0))
    all_homes_I_ver.append(Ip.max(level=0))
    all_homes_I_ver.append(Ip.sum(level=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual, list(I_ver[times[0]].keys())  # indovidual homes


def make_convergency_test(t, data_s, tf=47):
    """Price convergency development

    Args:
        t (int): selects the number of DA run
        data_s (list of list 48 float): clear DA prices
        tf (int): selects hour to track the development

    Return:
        price (list): price convergency development
    """
    index = [tf - y for y in range(tf + 1)]
    price = []
    price = list()
    for i in index:
        try:
            #            oi = data_s[t][i]
            #            print(oi)
            price.append(data_s[t][i])
        except:
            return price
        t = t + 1
    return deepcopy(price)


def get_first_h(data_s):
    """Gets the first hour of DA prices (DSO and retail)

    Args:
        t (int): selects the number of DA run
        data_s (list of list 48 float): clear DA prices

    Return:
        max_delta (int): worse hour in t
    """
    price = list()
    for i in range(len(data_s)):
        try:
            price.append(data_s[i][0])
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
    for n in range(int(days * 24)):
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

    Order = [[] for i in range(len(meta_I_ver))]
    for i in meta_I_ver:
        index = meta_I_ver[i]['index']
        for t in range(len(temp[0])):
            Order[index].append(temp[0][t][index])

    return meta_I_ver, start_time, Order


def get_data_multiple_days_10AM(V_analis, days, pre_file, pos_file):
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
    for n in range(int(days)):
        file_name = V_analis + str(n * 24 + 10) + '_metrics'
        file = open(pre_file + file_name + pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')

        d1.update(I_ver)

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

    Order = [[] for i in range(len(meta_I_ver))]
    for i in meta_I_ver:
        index = meta_I_ver[i]['index']
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
    for n in range(int(days * 24)):
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

    Order = [[] for i in range(len(meta_I_ver))]
    for i in meta_I_ver:
        index = meta_I_ver[i]['index']
        for t in range(len(temp[0])):
            Order[index].append(temp[0][t][index])

    return meta_I_ver, start_time, Order


def get_substation_data(file_name, pre_file, pos_file, to_hour=True):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
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
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i: {'units': meta_I_ver[i]['units'], 'index': meta_I_ver[i]['index'] + 7}})

        meta_I_ver = {}
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
        i = 0
        for t in times:
            temp = I_ver[t][node]

            try:
                len(I_ver[t][node][0])
                if len(I_ver[t][node][0]) > 1:
                    temp = []
                    for k in range(len(I_ver[t][node][0])):
                        for l in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][l])
                    for p in range(1, len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
                data_I_ver[j, i, :] = temp
            except TypeError:
                # print (data_I_ver[j,i,:])
                # print (I_ver[t][node])
                data_I_ver[j, i, :] = I_ver[t][node]
            i = i + 1
        j = j + 1

    return data_I_ver, meta_I_ver


if __name__ == "__main__":
    pre_file_out = 'lean_8/'  #
    pos_file = '.json'
    days = 2  # *2 = 4
    imonth = 8
    iday = 8
    Tday = 2
    da_convergence_start = 24 * 0  # DA interaction to start looking for convergence
    N_convergence_hours = 24  # number of hours to visualize convergence (set to zero neglect)

    dso_num = 2
    DSO = False  # plot DSO
    DSO_DA_curve = False
    DSO_RT_curve = False
    Retail = False  # plot Retail
    Retail_site = False  # plot Retail_site
    Inverters = False  # plot inverters
    Homes = False  # read homes for HVAC and water heater
    Water = False  # plot water heater
    HVAC = False
    HVAC_comparisons = False
    Water_agent = False
    HVAC_agent = True
    bid_plots = True
    bid_adjusted = True
    figno = 0
    pre_file = pre_file_out + 'DSO_2/'

    # ### Current time for plotting of DSO curves
    hour_of_day = 10  # anywhere from 0 to 23
    day_of_sim = 3  # starts from 0. 0 means the 1st day of simulation
    # ### DSO
    if DSO:
        V_file = 'dso_market_Substation_2_3600'
        meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
        V_analis = 'trial_cleared_price_da'
        first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
        # ### Plot clear DSO
        # =============================================================================
        #         plt.plot(first_h,marker='x');plt.ylabel('DSO price ($/kWh)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
        # =============================================================================
        # ### Plot convergency of DSO market
        # =============================================================================
        #         for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        #             convergency_max = make_convergency_test(data_s=Order[meta_I_ver[V_analis]['index']],t=i)
        #             plt.plot(convergency_max,marker='x');plt.ylabel('DSO price ($/kWh)');plt.xlabel('from time ahead to present (hours)');plt.title('hour 48 of t: '+str(i));plt.grid(True);plt.show()
        # =============================================================================
        if DSO_DA_curve:
            ###### code to plot the DSO DA quantities vs prices
            V_analis = 'curve_dso_da_quantities'
            dso_q = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_dso_da_prices'
            dso_p = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'trial_cleared_quantity_da'
            dso_cleared_q = (Order[meta_I_ver[V_analis]['index']])
            V_analis = 'trial_cleared_price_da'
            dso_cleared_p = (Order[meta_I_ver[V_analis]['index']])
            V_analis = 'trial_clear_type_da'
            dso_cleared_type = (Order[meta_I_ver[V_analis]['index']])

            V_file = 'retail_market_Substation_2_3600'
            meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
            V_analis = 'curve_buyer_da_quantities'
            ret_q = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_buyer_da_prices'
            ret_p = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_seller_da_quantities'
            ret_seller_q = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_seller_da_prices'
            ret_seller_p = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'cleared_quantity_da'
            ret_cleared_q = (Order[meta_I_ver[V_analis]['index']])
            V_analis = 'cleared_price_da'
            ret_cleared_p = (Order[meta_I_ver[V_analis]['index']])
            V_analis = 'clear_type_da'
            ret_cleared_type = (Order[meta_I_ver[V_analis]['index']])

            V_file = 'dso_market_Substation_2_86400'
            meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
            V_analis = 'curve_ws_node_quantities'
            supply_q = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_ws_node_prices'
            supply_p = Order[meta_I_ver[V_analis]['index']]

            plt.figure(figsize=(16, 9))
            plt.title('DA demand and supply curves for DSO ')
            plt.plot(supply_q[day_of_sim][hour_of_day], supply_p[day_of_sim][hour_of_day],
                     label='wholesale node supply curve')
            plt.plot((ret_q[day_of_sim * 24 + hour_of_day][0]), (ret_p[day_of_sim * 24 + hour_of_day][0]),
                     label='DA Aggregated demand curve at retail level')

plt.plot(dso_q[day_of_sim * 24 + hour_of_day][0], dso_p[day_of_sim * 24 + hour_of_day][0],
         label='DA Aggregated demand curve at DSO level')
plt.ylabel('DSO price ($/kWh)')
plt.xlabel('Quantity (kW)')
plt.grid(True)
plt.legend()
plt.savefig('DA_curves_' + str(hour_of_day) + '_' + str(day_of_sim) + '.png')
plt.show()
print("Wholesale RT cleared price: ", dso_cleared_p[day_of_sim * 24 + hour_of_day])
print("Wholesale RT cleared quantity: ", dso_cleared_q[day_of_sim * 24 + hour_of_day])
print("Wholesale RT clear type: ", dso_cleared_type[day_of_sim * 24 + hour_of_day])

plt.title('DA demand and supply curves for retail ')
plt.plot((ret_q[day_of_sim * 24 + hour_of_day][0]), (ret_p[day_of_sim * 24 + hour_of_day][0]),
         label='DA Aggregated demand curve')
plt.plot((ret_seller_q[day_of_sim * 24 + hour_of_day][0]), (ret_seller_p[day_of_sim * 24 + hour_of_day][0]),
         label='DA Substation supply curve')
plt.ylabel('Retail price ($/kWh)')
plt.xlabel('Quantity (kW)')
plt.grid(True)
plt.legend()
plt.show()
print("Retail cleared price:", ret_cleared_p[day_of_sim * 24 + hour_of_day])
print("Retail cleared quantity:", ret_cleared_q[day_of_sim * 24 + hour_of_day])
print("Retail clear type:", ret_cleared_type[day_of_sim * 24 + hour_of_day])

if DSO_RT_curve:
    ###### code to plot the DSO-RT quantities vs prices
    V_file = 'dso_market_Substation_2_300'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'curve_dso_rt_quantities'
    dso_q = (Order[meta_I_ver[V_analis]['index']])
    V_analis = 'curve_dso_rt_prices'
    dso_p = (Order[meta_I_ver[V_analis]['index']])
    V_analis = 'cleared_quantity_rt'
    dso_cleared_q = (Order[meta_I_ver[V_analis]['index']])
    V_analis = 'cleared_price_rt'
    dso_cleared_p = (Order[meta_I_ver[V_analis]['index']])
    V_analis = 'clear_type_rt'
    dso_cleared_type = (Order[meta_I_ver[V_analis]['index']])

    V_file = 'retail_market_Substation_2_300'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'curve_buyer_rt_quantities'
    ret_q = Order[meta_I_ver[V_analis]['index']]
    V_analis = 'curve_buyer_rt_prices'
    ret_p = Order[meta_I_ver[V_analis]['index']]
    V_analis = 'curve_seller_rt_quantities'
    ret_seller_q = Order[meta_I_ver[V_analis]['index']]
    V_analis = 'curve_seller_rt_prices'
    ret_seller_p = Order[meta_I_ver[V_analis]['index']]
    V_analis = 'cleared_quantity_rt'
    ret_cleared_q = (Order[meta_I_ver[V_analis]['index']])
    V_analis = 'cleared_price_rt'
    ret_cleared_p = (Order[meta_I_ver[V_analis]['index']])
    V_analis = 'clear_type_rt'
    ret_cleared_type = (Order[meta_I_ver[V_analis]['index']])

    V_file = 'dso_market_Substation_2_86400'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'curve_ws_node_quantities'
    supply_q = Order[meta_I_ver[V_analis]['index']]
    V_analis = 'curve_ws_node_prices'
    supply_p = Order[meta_I_ver[V_analis]['index']]

    plt.title('RT demand and supply curves for DSO')
    plt.plot(supply_q[day_of_sim][hour_of_day], supply_p[day_of_sim][hour_of_day], label='wholesale node supply curve')
    plt.plot((ret_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]),
             (ret_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), label='RT Aggregated demand curve at retail level')
plt.plot(dso_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1], dso_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1],
         label='RT Aggregated demand curve at DSO level')
plt.ylabel('DSO price ($/kWh)')
plt.xlabel('Quantity (kW)')
plt.grid(True)
plt.legend()
plt.show()
print("Wholesale RT cleared price: ", dso_cleared_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1])
print("Wholesale RT cleared quantity: ", dso_cleared_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1])
print("Wholesale RT clear type: ", dso_cleared_type[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1])

plt.title('RT demand and supply curves for Retail ')
plt.plot((ret_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), (ret_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]),
         label='RT Aggregated demand curve')
plt.plot((ret_seller_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]),
         (ret_seller_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), label='RT Substation supply curve')
plt.ylabel('Retail price ($/kWh)')
plt.xlabel('Quantity (kW)')
plt.grid(True)
plt.legend()
plt.show()
print("Retail cleared price:", ret_cleared_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1])
print("Retail cleared quantity:", ret_cleared_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1])
print("Retail clear type:", ret_cleared_type[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1])

# ## Retail
if Retail:
    V_file = 'retail_market_Substation_2_3600'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'cleared_price_da'
    first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
    # ### Plot clear DSO
    #        plt.plot(first_h,marker='x');plt.ylabel('retail price ($/kWh)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
    # ### Plot convergency of DSO market
    markers = ['.', 'o', 'v', '^', '<', '>', '1', '2', '3', '4', '8', 's', 'p', 'P', '*', 'h', 'H', '+', 'x', 'X', 'D',
               'd', '|', '_']
    M_in = 0
    plt.figure(figsize=(16, 9))
    for i in range(da_convergence_start, da_convergence_start + N_convergence_hours):
        convergency_max = make_convergency_test(data_s=Order[meta_I_ver[V_analis]['index']], t=i)
        plt.plot(convergency_max, marker=markers[M_in], label=str(i) + '-h', linewidth=1, markersize=5)
        plt.ylabel('retail price ($/kWh)')
        plt.xlabel(
            'from time ahead to present (hours)')  # ;plt.title('hour 48 of t: '+str(i));plt.grid(True);plt.show()
        M_in = M_in + 1
    plt.grid(True)
    plt.legend(bbox_to_anchor=(1.1, 1.00))
    figno += 1
    plt.savefig(pre_file_out + "figure{}.png".format(figno))
    plt.show()

    first_h_df = pd.DataFrame(first_h)
    first_h_df.index = pd.date_range(start_time, periods=len(first_h), freq='1H')
    first_h_df_rt = first_h_df.resample('5min').ffill()

    V_file = 'retail_market_Substation_2_300'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'cleared_price_rt'
    first_h_rt = Order[meta_I_ver[V_analis]['index']]
    plt.figure(figsize=(16, 9))
    plt.plot(first_h_df_rt.values, label='DA')
    # print(len(first_h_df_rt.index[1:]),len(first_h_rt))
    plt.plot(first_h_rt, label='RT')
    plt.legend()
    plt.ylabel('price ($/kWh)')
    plt.xlabel('time (5-min)')
    plt.grid(True)
    # plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
    figno += 1
    plt.savefig(pre_file_out + "figure{}.png".format(figno))
    plt.show()
    first_h_rt = pd.DataFrame(first_h_rt)
    # first_h_rt.index = first_h_df_rt.index[0:len(first_h_rt)]

    # =============================================================================
    #    ###plot of retail da quantitites
    #     if Retail and 1:
    #         V_file = 'retail_market_Substation_2_3600_'
    #         meta_I_ver, start_time, Order = get_data_multiple_days(V_file,days,pre_file,pos_file)
    #         V_analis = 'cleared_quantity_da'
    #         first_h_da = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
    #
    #         first_h_da_q = pd.DataFrame(first_h_da)
    #         first_h_da_q.index = pd.date_range(start_time,periods=len(first_h), freq='1H')
    #         plt.plot(first_h_da_q.values,label='DA')
    # =============================================================================

    #######################################################
    #######################################################
    #######################################################
pre_file = pre_file_out + 'Substation_2/'
# ## Inverters
if Inverters:
    V_file = 'inverter_Substation_2_metrics'
    meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
    V_analis = 'real_power_avg'  # variable being analized
    AVG_power = data_s[3][meta_S[V_analis]['index']]
    # ### Plot
    plt.plot((AVG_power.resample('60min').mean() / 1000).values, marker='x')
    plt.ylabel('agregated inverter power (kW)')
    plt.xlabel('time (hours)')
    plt.grid(True)
    plt.show()

    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    ax1.plot((AVG_power.resample('60min').mean() / 1000).values, marker='x', color='r')
    ax1.set_xlabel('time (hours)')
    ax1.set_ylabel('agregated inverter power (kW)', color='tab:red')
    ax2 = ax1.twinx()
    ax2.plot(first_h, marker='o', color='b')
    ax2.set_ylabel('DA retail price ($/kWh)', color='tab:blue')
    plt.grid(True)
    plt.show()

    #        fig = plt.figure(); ax1 = fig.add_subplot(111);ax1.plot((AVG_power.resample('60min').mean()/1000).values,marker='x',color='r');ax1.set_xlabel('time (hours)');ax1.set_ylabel('agregated inverter power (kW)',color='tab:red')
    #        ax2 = ax1.twinx(); ax2.plot((first_h_rt.resample('60min').mean()).values,marker='o',color='b');ax2.set_ylabel('RT retail price ($/kWh)',color='tab:blue');plt.grid(True);plt.show()

    x = list(range(0, 108))
    plt.plot(x, (AVG_power / 1000).values[x], marker='x')
    plt.ylabel('agregated inverter power (kW)')
    plt.xlabel('time (5-min)')
    plt.grid(True)
    [plt.axvline(x=i * 12, color='k') for i in range(0, int(len(x) / 12))]
    plt.show()
# ## Homes
if Homes:
    V_file = 'Substation_2_metrics_house'
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
    # print (data_key)
    # ### Water
    if Water:
        to_kW = 1
        V_analis = 'waterheater_load_avg'
        AVG_power = data_s[1][meta_S[V_analis]['index']]  # plots min, mean, max, sum
        # plt.figure(figsize=(16, 8), dpi=100)
        # plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x',label='WH Load');plt.ylabel('(kW)');plt.xlabel('time (hours)');plt.legend();plt.grid(True)
        # # plt.savefig(pre_file_out + "_wh_load.png")
        # plt.savefig('flexhvacwh_setting_old_wh_load')
        plt.show()

        agent_dict = "Substation_{}_agent_dict.json".format(dso_num)
        file = open(pre_file_out + 'DSO_{}/'.format(dso_num) + agent_dict, 'r')
        text = file.read()
        file.close()
        all_agent = json.loads(text)
        hvac_agents = all_agent['hvacs']
        wh_agent = all_agent['water_heaters']
        property = 'participating'
        wh_meters = []
        for key, item in wh_agent.items():
            wh_meters.append(wh_agent[key]['meterName'])

        # site_agent = all_agent['site_agent']
        # house_meters = []
        # for key, item in site_agent.items():
        #     house_meters.append(key)

        # house_meters = []
        # for key, item in hvac_agents.items():
        #     house_meters.append(hvac_agents[key]['meterName'])

        number_of_waterheaters = 0
        GLD_power = {}
        participating_wh = {}
        V_analis2 = 'waterheater_temp_avg'
        for i in range(len(data_individual)):
            AVG_power = data_individual[i][meta_S[V_analis]['index']]
            GLD_power.update({data_key[i]: AVG_power})
            AVG_power2 = data_individual[i][meta_S[V_analis2]['index']]
            # if False:#not (data_key[i] == 'R5_12_47_2_tn_133_hse_1' or data_key[i] == 'R5_12_47_2_load_10_bldg_82_zone_all'):
            #     continue
            try:
                if hvac_agents[data_key[i]]['meterName'] not in wh_meters:
                    continue
                else:
                    number_of_waterheaters += 1
                    index = data_individual[i][meta_S[V_analis]['index']].resample('60min').mean().index
                    participating_wh.update(
                        {data_key[i]: data_individual[i][meta_S[V_analis]['index']].resample('60min').mean().values})
            except:
                print("{} not a house but made in the data collection function".format(data_key[i]))
                pass

        if number_of_waterheaters > 0:
            participating_wh_df = pd.DataFrame(data=participating_wh, index=index)
            participating_wh_agg = participating_wh_df.sum(axis=1)
            plt.figure(figsize=(16, 9))
            plt.plot(participating_wh_agg.index, participating_wh_agg.values)
            plt.ylabel('Energy Consumption kWh')
            plt.xlabel('time (days)')
            plt.grid(True)
            plt.title('Aggregated WH ')
            plt.ylim((0, 75))
            figno += 1
            plt.savefig(pre_file_out + 'flexhvacwh_setting_old_wh' + "figure{}.png".format(figno))
            plt.show()

    # ###### HVAC
    if HVAC:
        V_analis = 'hvac_load_avg'
        AVG_power = data_s[3][meta_S[V_analis]['index']]  # plots min, mean, max, sum
        V_analis2 = 'air_temperature_avg'
        AVG_power2 = data_s[1][meta_S[V_analis2]['index']]  # plots mean
        to_kW = 1
        # greater than the start date and smaller than the end date
        mask = (AVG_power.index >= '{}-{}-2016'.format(imonth, iday)) & (
                    AVG_power.index <= '{}-{}-2016'.format(imonth, iday + Tday))
        AVG_power = AVG_power.loc[mask]
        # plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('agregated hvac load (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()#plt.title("without commercial buildings")
        # plt.plot((AVG_power2.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('avg agregated room temperature (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()

        # We need to only pick the hvacs that are participating
        agent_dict = "Substation_{}_agent_dict.json".format(dso_num)
        file = open(pre_file_out + 'DSO_{}/'.format(dso_num) + agent_dict, 'r')
        text = file.read()
        file.close()
        all_agent = json.loads(text)
        hvac_agent = all_agent['hvacs']
        property = 'cooling_participating'
        # hvac_agent[meta_da['names'][i]][property]

        participating_hvacs = 0
        GLD_power = {}
        participating_hvac = {}
        for i in range(len(data_individual)):
            AVG_power = data_individual[i][meta_S[V_analis]['index']]
            GLD_power.update({data_key[i]: AVG_power})
            AVG_power2 = data_individual[i][meta_S[V_analis2]['index']]
            # if False:#not (data_key[i] == 'R5_12_47_2_tn_133_hse_1' or data_key[i] == 'R5_12_47_2_load_10_bldg_82_zone_all'):
            #     continue
            if data_key[i] not in hvac_agent.keys():
                continue
            else:
                # elif hvac_agent[data_key[i]][property]:
                participating_hvacs += 1
                index = data_individual[i][meta_S[V_analis]['index']].index  # resample('60min').mean().index
                participating_hvac.update({data_key[i]: data_individual[i][
                    meta_S[V_analis]['index']].values})  # resample('60min').mean().values})
            # plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('hvac load (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.title('home: '+str(data_key[i]));plt.show()
            # plt.plot((AVG_power2).values,marker='x');plt.ylabel('room temperature (F)');plt.xlabel('time (hours)');plt.grid(True);plt.title('home: '+str(data_key[i]));plt.show()
            # (data_individual[i])

        if participating_hvacs > 0:
            participating_hvac_df = pd.DataFrame(data=participating_hvac, index=index)
            participating_hvac_agg = participating_hvac_df.sum(axis=1)
            plt.figure(figsize=(16, 9))
            plt.plot(participating_hvac_agg.index, participating_hvac_agg.values)
            plt.ylabel('Energy Consumption')
            plt.xlabel('time (days)')
            plt.grid(True)
            plt.title("Aggregated HVAC")
            # plt.title('Aggregated Participating HVAC ')
            figno += 1
            plt.savefig(pre_file_out + "figure{}.png".format(figno))
            plt.show()

        if HVAC_comparisons:
            V_file = 'Substation_{}_metrics_substation'.format(dso_num)
            meta_S, start_time, data_s, data_individual, data_keys = get_metrics_full_multiple_KEY(V_file, pre_file,
                                                                                                   pos_file)
            # # aggregated house load without battery
            V_analis = 'real_power_avg'
            sub_power = data_s[3][meta_S[V_analis]['index']]  # plots aggregated

            # get DA cleared quantities at 10 AM
            # ten_am = day_of_sim*24 + 10
            pre_file = pre_file_out + 'DSO_{}/'.format(dso_num)
            V_file = 'retail_site_Substation_{}_3600'.format(dso_num)
            meta_I_ver, start_time, Order = get_data_multiple_days_10AM(V_file, days, pre_file, pos_file)
            # file = open(pre_file + V_file + pos_file, 'r')
            # text = file.read()
            # I_ver = json.loads(text)
            # meta_I_ver = I_ver.pop('Metadata')
            # V_analis = 'transactive_batt'
            V_analis = 'transactive_hvac'
            data = Order[meta_I_ver[V_analis]['index']]
            keys = Order[meta_I_ver['status']['index']]

            data_s_sum = []
            for i in range(len(data)):
                # print(keys[0][i])
                # if not keys[0][i]:
                #     continue
                # collect midnight to next 24 hrs data: 14th hour to 38th hour from each day 10 AM data
                # data_s_sum.append(np.array(i).sum(axis=0).tolist()[14:14 + 24])
                data_s_sum.append(np.array(data[i]).sum(axis=0).tolist()[14:14 + 24])
                # data_s_sum.append(i[0])
            # flatten the list to 1-D
            da_cleared_q = [j for sub in data_s_sum for j in sub]
            # remove the last 24 entries as they are forecast for non-exisiting day
            da_cleared_q = da_cleared_q[:-24]
            # get actual inverter power
            hvac_power_hr = participating_hvac_agg.values  # hvac_power.resample('60min').mean().values
            fig2, ax2 = plt.subplots()
            # ax2 = ax1.twinx()
            ax2.plot((da_cleared_q), label='cleared DA bid')
            ax2.plot(hvac_power_hr[24 + 1:] / 1.0, label='actual consumption')  # remove 1st day
            ax2.set_ylabel('kW')
            ax2.grid(True)
            ax2.set_title(
                "Cleared DA bid and actual kW by hvac agent ")  # ax1.set_ylabel('(F)')
            ax2.legend()
            plt.show()

            # Plotting agent parameters and optimal bids
            V_file = 'hvac_agent_Substation_{}_3600'.format(dso_num)
            meta_da, start_time, data_da, da_bid_hvac, data_keys_da = get_metrics_full_multiple_KEY_Mdays_H(V_file,
                                                                                                            pre_file,
                                                                                                            '_metrics' + pos_file)

            V_file = 'hvac_agent_Substation_{}_300'.format(dso_num)
            meta_rt, start_time, data_rt, rt_bid_hvac, data_keys = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                                       '_metrics' + pos_file)
            to_kW = 1

            agent_dict = "Substation_{}_agent_dict.json".format(dso_num)
            file = open(pre_file + agent_dict, 'r')
            text = file.read()
            file.close()
            all_agent = json.loads(text)
            hvac_agent = all_agent['hvacs']
            property = 'slider_setting'
            # hvac_agent[meta_da['names'][i]]['slider_setting']
            prop = []
            opt = []
            dev = []

            if False:
                fig1, ax1 = plt.subplots(2, sharex='col')
                # ax2 = ax1.twinx()
                i = 1
                opt_bid = da_bid_hvac[i][meta_da['bid_four_point_rt_3']['index']]
                # print(da_bid_hvac)
                # print(opt_bid)
                ax1[0].plot((opt_bid.resample('60min').mean() / to_kW).values, label='optimal bid')
                actual = participating_hvac_df[
                    data_keys_da[i]]  # rt_bid_hvac[i][meta_rt['inverter_p_setpoint']['index']]
                # ax1[0].plot(-(actual.resample('60min').mean() / 1000).values, label='actual power')
                ax1[0].plot(actual.values, label='actual power')
                ax1[0].set_ylabel('kW')
                ax1[0].grid(True)
                # ax1[0].set_title(
                #     "Optimal bid and actual kW by hvac agent with slider setting {}".format(
                #         hvac_agent[meta_da['names'][i]]['slider_setting']));  # ax1.set_ylabel('(F)')
                ax1[0].legend()

                i = 5
                opt_bid = da_bid_hvac[i][meta_da['bid_four_point_rt_3']['index']]
                ax1[1].plot((opt_bid.resample('60min').mean() / to_kW).values, label='optimal bid')
                actual = participating_hvac_df[
                    data_keys_da[i]]  # rt_bid_hvac[i][meta_rt['inverter_p_setpoint']['index']]
                # ax1[1].plot(-(actual.resample('60min').mean() / 1000).values, label='actual power')
                ax1[1].plot(actual.values, label='actual power')
                ax1[1].set_ylabel('kW')
                ax1[1].grid(True)
                # ax1[1].set_title(
                #     "Optimal bid and actual kW by battery agent with slider setting {}".format(
                #         hvac_agent[meta_da['names'][i]]['slider_setting']));  # ax1.set_ylabel('(F)')
                ax1[1].legend()
                plt.xlabel('time (hours)')
                plt.show()
            else:
                fig1, ax1 = plt.subplots(2, sharex='col')
                # ax2 = ax1.twinx()
                for i in range(len(da_bid_hvac)):
                    if data_keys_da[i] == "R5_12_47_2_tn_133_hse_1":
                        # i = 1
                        opt_bid = da_bid_hvac[i][meta_da['bid_four_point_rt_3']['index']]
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
                                0.71))  # ax1.set_ylabel('(F)')
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

            # ------------------------------------------------
            # for inverter plot - not sure if needed for hvac
            # ------------------------------------------------
            # actual = np.zeros(24 * days)
            # actual_all = []
            # soc = np.zeros(24 * days)
            # soc_all = []
            # for i in range(len(rt_bid_hvac)):
            #     temp = rt_bid_hvac[i][meta_rt['inverter_p_setpoint']['index']].resample('60min').mean().values
            #     soc_temp = rt_bid_hvac[i][meta_rt['battery_soc']['index']].resample('60min').mean().values
            #     cap = hvac_agent[meta_rt['names'][i]]['capacity'] / 1000
            #     if len(temp) != 24 * days:
            #         temp = np.append(temp, temp[-1])
            #     if len(soc_temp) != 24 * days:
            #         soc_temp = np.append(soc_temp, soc_temp[-1])
            #     actual = actual + temp / 1000
            #     soc = soc + soc_temp / cap
            #     soc_all.append(soc_temp / cap)
            #     actual_all.append(temp / 1000)
            # actual = actual[0:]
            # soc = soc[0:] / len(rt_bid_hvac)
            #
            # # plot soc and setpoint and gridlabd output of individual battery
            # figsoc, ax1soc = plt.subplots(2, sharex='col')
            # ax1soc[0].plot(actual, label='real-time P set-point')
            # ax1soc[0].plot(hvac_power_hr[1:] / 1000, label='actual consumption (gridlabd)')
            # ax1soc[1].plot(soc, label='soc')
            # # for i in range(len(soc_all)):
            # #     if i==114: # max(soc_all[i]) >= 1:
            # #         print(i)
            # #         j = meta_S['names'].index(meta_rt['names'][i])
            # #         gld_ind = data_individual[j][meta_S['real_power_avg']['index']].resample('60min').mean().values
            # #         ax1soc[0].plot(actual_all[i])
            # #         ax1soc[0].plot(gld_ind[1:]/1000)
            # #         ax1soc[1].plot(soc_all[i])
            # ax1soc[0].legend()
            # ax1soc[1].legend()
            # plt.show()

            # fig2, ax2 = plt.subplots()
            # # ax2 = ax1.twinx()
            # i = 1
            # opt_bid = da_bid_batt[i][meta_da['bid_four_point_rt_3']['index']]
            # ax2.plot((da_cleared_q), label='cleared DA bid')
            # # actual = rt_bid_batt[i][meta_rt['inverter_p_setpoint']['index']]
            # ax2.plot((actual), label='real-time P set-point')
            # ax2.plot(inv_power_hr[1:]/1000, label='actual consumption (gridlabd)')
            # ax2.set_ylabel('kW')
            # ax2.grid(True)
            # ax2.set_title(
            #     "Cleared DA bid and actual kW by battery agent with slider setting {}".format(
            #         batt_agent[meta_da['names'][i]]['slider_setting']))  # ax1.set_ylabel('(F)')
            # ax2.legend()
            # plt.show()

            # for key, value in hvac_agent.items():
            #     ind = meta_da['names'].index(key)
            #     optimal_pt = da_bid_hvac[ind][meta_da['bid_four_point_rt_3']['index']]
            #     optimal_pt = (optimal_pt.resample('60min').mean() / 1).values
            #     ind2 = meta_rt['names'].index(key)
            #     actual_p = rt_bid_hvac[ind2][meta_rt['inverter_p_setpoint']['index']]
            #     actual_p = -(actual_p.resample('60min').mean() / 1000).values
            #     # if value[property] >= 0.95:
            #     #     print(ind)
            #     #     print(ind2)
            #     prop.append(value[property])
            #     opt.append(optimal_pt[20])
            #     dev.append((abs(optimal_pt[0:167] - actual_p)).mean())
            # plt.scatter(prop, dev, label='deviation from optimal bid')
            # plt.title('deviation from optimal bid')
            # plt.ylabel('kW')
            # plt.xlabel('Slider Setting')
            # plt.show()

            # # Profit Calculation
            # V_analis = 'real_power_avg'  # variable being analized
            # first_h_rt_df = pd.DataFrame(first_h_rt)
            # first_h_rt_df.index = pd.date_range(pd.to_datetime(start_time) + pd.Timedelta('3900s'), periods=len(first_h_rt),
            #                                  freq='5min')
            # for i in range(len(rt_bid_batt)):
            #     actual = (rt_bid_batt[i][meta_rt['inverter_p_setpoint']['index']]/1000)
            #     actual.multiply(first_h_rt_df, fill_value=0)

            # fig = plt.figure(); ax1 = fig.add_subplot(111);ax1.plot((inv_power.resample('60min').mean()/1000).values,marker='x',color='r');ax1.set_xlabel('time (hours)');ax1.set_ylabel('agregated inverter power (kW)',color='tab:red')
            # ax2 = ax1.twinx(); ax2.plot(first_h,marker='o',color='b');ax2.set_ylabel('DA retail price ($/kWh)',color='tab:blue');plt.grid(True);plt.show()

if Retail_site:
    pre_file = pre_file_out + 'DSO_2/'
    gld_pre_file = pre_file_out + 'Substation_{}/'.format(dso_num)
    # Lets get total substation load from gridlabd
    V_file = 'Substation_{}_metrics_substation'.format(dso_num)
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY(V_file, gld_pre_file,
                                                                                          pos_file)
    # # aggregated house load without battery
    V_analis = 'real_power_avg'
    sub_power = data_s[3][meta_S[V_analis]['index']]  # plots aggregated

    # V_file = 'Substation_{}_metrics_inverter'.format(dso_num)
    # meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY(V_file, gld_pre_file, pos_file)
    # V_analis = 'real_power_avg'  # variable being analized
    # inv_power = data_s[3][meta_S[V_analis]['index']]
    # orig_power = inv_power + sub_power

    # get forecast uncontrollable load
    V_file = 'retail_site_Substation_{}_3600'.format(dso_num)
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    # V_analis = 'non_transactive_quantities'
    # plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='total load')
    # V_analis = 'non_transactive_zip'
    # plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='zip load')
    V_analis = 'non_transactive_hvac'
    plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='hvac load')
    plt.legend()
    plt.ylabel('load (kW)')
    plt.xlabel('time (hour)')
    plt.grid(True)
    plt.title('Estimated non-participating load profiles')
    plt.show()
    # print(len(Order[meta_I_ver['meters']['index']]))
    for i in range(50):  # len(Order[meta_I_ver['meters']['index']][0])):
        # print(Order[meta_I_ver[V_analis]['index']][0][i])
        if True:  # (Order[meta_I_ver['meters']['index']][0][i]).replace("mtr","hse") == "R5_12_47_2_tn_2_hse_2":
            plt.plot(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24][i], label='agent load')
            power = (GLD_power[(Order[meta_I_ver['meters']['index']][0][i]).replace("mtr", "hse")]).resample(
                '60min').mean()
            mask = (power.index >= '{}-{}-2016'.format(imonth, iday)) & (
                    power.index <= '{}-{}-2016'.format(imonth, iday + Tday))
            power = power.loc[mask]
            plt.plot(power.values, label='GLD load')
            # print(np.array(Order[meta_I_ver[V_analis]['index']][i][(days - 1) * 24]))

            # plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='hvac load')
            # V_analis = 'non_transactive_wh'
            # plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='waterheater load')
            plt.legend()
            plt.ylabel('load (kW)')
            plt.xlabel('time (hour)')
            plt.grid(True)
            plt.title('house ' + str(Order[meta_I_ver['meters']['index']][0][i]).replace("mtr", "hse"))
            # plt.show()

    if False:
        fr_load = np.zeros(days * 24)
        for i in range(0, days * 24, 24):  # iterate over 1st hour of each day
            temp = sum(np.array(Order[meta_I_ver['non_transactive_quantities']['index']][i]))
            fr_load[i:i + 24] = temp[0:24]
        gd_load = (orig_power.resample('60min').mean() / 1000)[0:days * 24].values
        # avoid day 1
        fr_load = fr_load[24:]
        gd_load = gd_load[24:]
        fr_err = abs((gd_load - fr_load) / gd_load)
        fr_err_avg = fr_err.mean()
        plt.plot(fr_load, label='load forecast')
        plt.plot(gd_load, label="gridlabd (true) load")
        plt.legend()
        plt.ylabel('load (kW)')
        plt.xlabel('time (hour)')
        plt.grid(True)
        plt.title('Non-participating forecast and true load; MAPE: {:.2f}'.format(fr_err_avg))
        plt.show()

        plt.plot(fr_err, marker='.')
        plt.ylabel('absolute error (F-A)/A')
        plt.xlabel('time (hour)')
        plt.grid(True)
        plt.title('Absolute Percentage Error of Non-participating load forecase; MAPE: {:.2f}'.format(fr_err_avg))
        plt.show()

        # first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
        #### Plot clear DSO
        #        plt.plot(first_h,marker='x');plt.ylabel('retail price ($/kWh)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
        #### Plot convergency of DSO market
        markers = ['.', 'o', 'v', '^', '<', '>', '1', '2', '3', '4', '8', 's', 'p', 'P', '*', 'h', 'H', '+', 'x',
                   'X', 'D', 'd', '|', '_']
        M_in = 0
        V_analis = 'non_transactive_quantities'
        data_s = Order[meta_I_ver[V_analis]['index']]
        data_s_sum = []
        for i in data_s:
            data_s_sum.append(np.array(i).sum(axis=0).tolist())
            # data_s_sum.append(i[0])
        for i in range(da_convergence_start, da_convergence_start + N_convergence_hours):
            convergency_max = make_convergency_test(data_s=data_s_sum, t=i)
            plt.plot(convergency_max, marker=markers[M_in], label=str(i) + '-h', linewidth=1, markersize=5)
            plt.title('Total non participating load convergence')
            plt.ylabel('load (kW)')
            plt.xlabel(
                'from time ahead to present (hours)')  # ;plt.title('hour 48 of t: '+str(i));plt.grid(True);plt.show()
            M_in = M_in + 1
        plt.grid(True)
        plt.legend(bbox_to_anchor=(1.1, 1.00))
        plt.show()

    # M_in = 0
    # V_analis = 'non_transactive_hvac'
    # data_s = Order[meta_I_ver[V_analis]['index']]
    # data_s_sum = []
    # for i in data_s:
    #     data_s_sum.append(np.array(i).sum(axis=0).tolist())
    #     # data_s_sum.append(i[0])
    # for i in range(da_convergence_start, da_convergence_start + N_convergence_hours):
    #     convergency_max = make_convergency_test(data_s=data_s_sum, t=i)
    #     plt.plot(convergency_max, marker=markers[M_in], label=str(i) + '-h', linewidth=1, markersize=5)
    #     plt.title('Total non participating hvac convergence')
    #     plt.ylabel('load (kW)')
    #     plt.xlabel(
    #         'from time ahead to present (hours)')  # ;plt.title('hour 48 of t: '+str(i));plt.grid(True);plt.show()
    #     M_in = M_in + 1
    # plt.grid(True)
    # plt.legend(bbox_to_anchor=(1.1, 1.00))
    # plt.show()

# ## new HVAC
if HVAC_agent and 1:
    # for iday in range(3):
    pre_file = pre_file_out + 'DSO_2/'
    # iday = 13
    ihour = 1
    V_file = 'hvac_agent_Substation_2_300'
    # meta_S, start_time, data_s, data_individual,data_key = get_metrics_full_multiple_KEY(V_file,pre_file,pos_file)
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                                '_metrics' + pos_file)
    # meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = ['agent_room_temperature', 'GLD_air_temperature', 'outdoor_temperature', 'cooling_setpoint',
                'cooling_basepoint', 'heating_setpoint', 'heating_basepoint', 'cleared_price']  #
    # V_analis = ['DA_bid_quantity','RT_bid_quantity','cleared_price']#,'heating_basepoint','cleared_price']
    to_kW = 1
    houses = {"R5_12_47_2_tn_2_hse_1": 0.9776, "R5_12_47_2_load_10_bldg_82_zone_all": 0.71,
              "R5_12_47_2_tn_133_hse_1": 0.71,
              "R5_12_47_2_tn_1_hse_1": 0.1295, "R5_12_47_2_tn_3_hse_4": 0.3273, "R5_12_47_2_tn_3_hse_5": 0.0295,
              "R5_12_47_2_tn_4_hse_3": 0.1225}
    for i in range(len(data_individual)):
        # if data_key[i] not in houses.keys():
        #     continue
        fig, ax1 = plt.subplots(figsize=(16, 9))
        ax2 = ax1.twinx()
        # print((AVG_power/to_kW).index,(AVG_power/to_kW).values)
        # print(GLD_power[data_key[i]].index,GLD_power[data_key[i]].values)
        for ivar in range(len(V_analis) - 1):
            AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
            ax1.plot((AVG_power.resample('5min').mean() / to_kW).index,
                     (AVG_power.resample('5min').mean() / to_kW).values, marker='x', label=V_analis[ivar])
            ax1.set_ylabel('(kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.title('home ' + str(data_key[i]) + ' - day {:.0f}'.format(ihour))
        # ax1.plot((GLD_power[data_key[i]].resample('60min').mean()/to_kW).index,(GLD_power[data_key[i]].resample('60min').mean()/to_kW).values,label = 'GLD power')
        ax1.legend()
        AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
        ax2.plot((AVG_power / to_kW).index, (AVG_power / to_kW).values, '-', color='k', label=V_analis[-1])
        ax2.set_ylabel('price ($/kW)')
        plt.xlabel('time (hours)')
        plt.grid(True)
        # ax2.legend()
        plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
        figno += 1
        plt.savefig(pre_file_out + "figure{}.png".format(figno))
        # plt.show()

if HVAC_agent and 1:
    # for iday in range(3):
    pre_file = pre_file_out + 'DSO_2/'
    # iday = 13
    ihour = 1
    V_file = 'hvac_agent_Substation_2_300'
    # meta_S, start_time, data_s, data_individual,data_key = get_metrics_full_multiple_KEY(V_file,pre_file,pos_file)
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                                '_metrics' + pos_file)
    # meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    # V_analis = ['agent_room_temperature','outdoor_temperature','cooling_setpoint','cooling_basepoint','cleared_price']
    V_analis = ['DA_bid_quantity', 'RT_bid_quantity', 'cleared_price']  # ,'heating_basepoint','cleared_price']
    to_kW = 1
    houses = {"R5_12_47_2_tn_2_hse_1": 0.9776, "R5_12_47_2_load_10_bldg_82_zone_all": 0.71,
              "R5_12_47_2_tn_133_hse_1": 0.71,
              "R5_12_47_2_tn_1_hse_1": 0.1295, "R5_12_47_2_tn_3_hse_4": 0.3273, "R5_12_47_2_tn_3_hse_5": 0.0295,
              "R5_12_47_2_tn_4_hse_3": 0.1225}
    for i in range(len(data_individual)):
        # if data_key[i] not in houses.keys():
        #     continue
        fig, ax1 = plt.subplots(figsize=(16, 9))
        ax2 = ax1.twinx()
        # print((AVG_power/to_kW).index,(AVG_power/to_kW).values)
        # print(GLD_power[data_key[i]].index,GLD_power[data_key[i]].values)
        for ivar in range(len(V_analis) - 1):
            AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
            ax1.plot((AVG_power.resample('60min').mean() / to_kW).index,
                     (AVG_power.resample('60min').mean() / to_kW).values, marker='x', label=V_analis[ivar])
            ax1.set_ylabel('(kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.title('home ' + str(data_key[i]) + ' - day {:.0f}'.format(ihour))
        ax1.plot((GLD_power[data_key[i]].resample('60min').mean() / to_kW).index,
                 (GLD_power[data_key[i]].resample('60min').mean() / to_kW).values, label='GLD power')
        ax1.legend()
        AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
        ax2.plot((AVG_power / to_kW).index, (AVG_power / to_kW).values, '-', color='k', label=V_analis[-1])
        ax2.set_ylabel('price ($/kW)')
        plt.xlabel('time (hours)')
        plt.grid(True)
        # ax2.legend()
        plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
        figno += 1
        plt.savefig(pre_file_out + "figure{}.png".format(figno))
        # plt.show()

if HVAC_agent and 0:
    pre_file = pre_file_out + 'DSO_2/'
    V_file = 'hvac_agent_Substation_2_3600'
    meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                      '_metrics' + pos_file)
    V_analis = ['GLD_air_temperature', 'outdoor_temperature',
                'thermostat_setpoint']  # ,'cooling_basepoint','cleared_price']
    to_kW = 1
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    for i in [14]:  # range(len(data_individual)):
        for ivar in range(len(V_analis) - 1):
            AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
            ax1.plot((AVG_power / to_kW).values, marker='x', label=V_analis[ivar])
            ax1.set_ylabel('(F)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.title('home ' + str(i))
        ax1.legend()
        # AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
        # ax2.plot((AVG_power/to_kW).values,'-', color='k',label=V_analis[-1]);ax2.set_ylabel('price ($/kW)');plt.xlabel('time (hours)');plt.grid(True)
        # ax2.legend()
        plt.show()

if HVAC_agent and 0:
    pre_file = pre_file_out + 'DSO_2/'
    V_file = 'hvac_agent_Substation_2_300'
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                                '_metrics' + pos_file)
    V_analis = ['GLD_air_temperature', 'outdoor_temperature', 'cooling_basepoint', 'cooling_setpoint',
                'agent_room_temperature', 'cleared_price']  # ,'thermostat_setpoint']
    # V_analis = ['GLD_air_temperature','outdoor_temperature','cooling_basepoint','cooling_setpoint','cleared_price']#,'thermostat_setpoint']
    to_kW = 1
    houses = {"R5_12_47_2_tn_2_hse_1": 0.9776, "R5_12_47_2_load_10_bldg_82_zone_all": 0.71,
              "R5_12_47_2_tn_133_hse_1": 0.71,
              "R5_12_47_2_tn_1_hse_1": 0.1295, "R5_12_47_2_tn_3_hse_4": 0.3273, "R5_12_47_2_tn_3_hse_5": 0.0295,
              "R5_12_47_2_tn_4_hse_3": 0.1225}
    import pickle

    with open('GLD_power_basecase.pkl', 'rb') as f:
        GLD_power = pickle.load(f)
    GLD_power = GLD_power[0]
    print(GLD_power)
    for i in range(len(data_individual)):
        if data_key[i] not in houses.keys():  # not (data_key[i] == 'R5_12_47_2_tn_3_hse_5' or data_key[i] == 'R5_12_47_2_tn_133_hse_1' or data_key[i] == 'R5_12_47_2_load_10_bldg_82_zone_all'):
            continue
        price = data_individual[i][meta_S[V_analis[-1]]['index']]
        mask = (price.index >= '{}-{}-2016'.format(imonth, iday)) & (
                    price.index <= '{}-{}-2016'.format(imonth, iday + Tday))
        price = price.loc[mask]
        power = GLD_power[data_key[i]]
        mask = (power.index >= '{}-{}-2016'.format(imonth, iday)) & (
                    power.index <= '{}-{}-2016'.format(imonth, iday + Tday))
        power = power.loc[mask]

        print(data_key[i])
        print(sum(power.values * price.values) / 60.0)

        fig, ax1 = plt.subplots(figsize=(16, 9))
        ax2 = ax1.twinx()
        lns = []
        for ivar in range(len(V_analis) - 1):
            # print(data_individual[i])
            # print(meta_S)
            # print(V_analis[ivar])
            # print(meta_S[V_analis[ivar]]['index'])
            AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
            # ax1.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x',label=V_analis[ivar]);plt.xlabel('time (hours)');plt.grid(True);plt.title('home '+str(data_key[i]));#ax1.set_ylabel('(F)')
            ln = ax1.plot(AVG_power.index, AVG_power.values, marker='x', label=V_analis[ivar])
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.title('home ' + str(data_key[i]))  # ax1.set_ylabel('(F)')
            lns += ln  # .append(ln)
        # ax1.legend()

        AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
        ln = ax2.plot(AVG_power.index, AVG_power.values, '-', color='k', label=V_analis[-1])
        ax2.set_ylabel('price ($/kW)')
        plt.xlabel('time (hours)')
        plt.grid(True)
        lns += ln  # .append(ln)
        # ax2.legend()
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs)
        plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
        figno += 1
        plt.savefig(pre_file_out + "figure{}.png".format(figno))
        plt.show()

# ## new waterheater agent
if Water_agent and 1:
    pre_file = pre_file_out + 'DSO_2/'
    # V_file = 'water_heater_agent_Substation_2_3600'
    # meta_S, start_time, data_s, data_individual, data_keys = get_metrics_full_multiple_KEY_Mdays_H(V_file,pre_file,'_metrics'+pos_file)
    #
    # # this code portion plots quantity with sliding window of an hour for an individual home
    # home_num = 45
    #
    # index =[382] #index thats needs to be collected
    # x = 382   #quantity bid to be plotted
    # for i in range(47):
    #     index.append(x-8)
    #     x = x - 8
    #
    # data_s_modified = data_s[3][index].sort_index()  # sorts the data in interval of eightth bid
    # data_plot = [] #slects data in hourly sliding window format
    # for i in range(len(index)):
    #     data_plot.append(data_individual[home_num][index].sort_index().values[i+(24*3)][i]) #plots for last two days
    # plt.plot(data_plot,marker='x'); plt.ylabel('Quantity bid'); plt.xlabel('time index');plt.grid(True);plt.show()
    #
    # data_plot = []
    # for i in range(len(index)):
    #     data_plot.append( data_s_modified.values[i+(24*3)][i]) #plots for last three days
    # plt.plot(data_plot,marker='x'); plt.ylabel('Quantity bid for all houses'); plt.xlabel('time index');plt.grid(True);plt.show()

    pre_file = pre_file_out + 'DSO_2/'
    V_file = 'water_heater_agent_Substation_2_300'
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY_Mdays_wh(V_file, pre_file,
                                                                                                   '_metrics' + pos_file)

    V_analis = ['upper_tank_setpoint', 'lower_tank_setpoint', 'Energy_GLD', 'SOHC_gld', 'Waterdraw_gld']
    to_kW = 1
    houses = {"R5_12_47_2_tn_2_hse_1": 0.9776, "R5_12_47_2_load_10_bldg_82_zone_all": 0.71,
              "R5_12_47_2_tn_133_hse_1": 0.71,
              "R5_12_47_2_tn_1_hse_1": 0.1295, "R5_12_47_2_tn_3_hse_4": 0.3273, "R5_12_47_2_tn_3_hse_5": 0.0295,
              "R5_12_47_2_tn_4_hse_3": 0.1225}
    import pickle

    with open('GLD_power_basecase.pkl', 'rb') as f:
        GLD_power = pickle.load(f)
    GLD_power = GLD_power[0]
    print(GLD_power)
    for i in range(len(data_individual)):
        if data_key[i] not in houses.keys():  # not (data_key[i] == 'R5_12_47_2_tn_3_hse_5' or data_key[i] == 'R5_12_47_2_tn_133_hse_1' or data_key[i] == 'R5_12_47_2_load_10_bldg_82_zone_all'):
            continue
        price = data_individual[i][meta_S[V_analis[-1]]['index']]
        mask = (price.index >= '{}-{}-2016'.format(imonth, iday)) & (
                    price.index <= '{}-{}-2016'.format(imonth, iday + Tday))
        price = price.loc[mask]
        power = GLD_power[data_key[i]]
        mask = (power.index >= '{}-{}-2016'.format(imonth, iday)) & (
                    power.index <= '{}-{}-2016'.format(imonth, iday + Tday))
        power = power.loc[mask]

        print(data_key[i])
        print(sum(power.values * price.values) / 60.0)

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        lns = []
        for ivar in range(len(V_analis) - 1):
            # print(data_individual[i])
            # print(meta_S)
            # print(V_analis[ivar])
            # print(meta_S[V_analis[ivar]]['index'])
            AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
            # ax1.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x',label=V_analis[ivar]);plt.xlabel('time (hours)');plt.grid(True);plt.title('home '+str(data_key[i]));#ax1.set_ylabel('(F)')
            ln = ax1.plot(AVG_power.index, AVG_power.values, marker='x', label=V_analis[ivar])
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.title('home ' + str(data_key[i]))  # ax1.set_ylabel('(F)')
            lns += ln  # .append(ln)
            # ax1.legend()

        AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
        ln = ax2.plot(AVG_power.index, AVG_power.values, '-', color='k', label=V_analis[-1])
        ax2.set_ylabel('price ($/kW)')
        plt.xlabel('time (hours)')
        plt.grid(True)
        lns += ln  # .append(ln)
        # ax2.legend()
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs)
        plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
        figno += 1
        plt.savefig(pre_file_out + "figure{}.png".format(figno))
        plt.show()

if bid_plots is False:
    # pre_file_out ='flexhvacwh_setting_old/'
    pos_file = '.json'
    # days = 5
    imonth = 8
    iday = 19
    Tday = 2
    dso_num = 2

    Water = 1
    Water_agent = 1
    pre_file = pre_file_out + 'DSO_' + str(dso_num) + '/'
    pre_file_sub = pre_file_out + 'Substation_' + str(dso_num) + '/'

    # ### Current time for plotting of DSO curves
    hour_of_day = 0  # anywhere from 0 to 23
    day_of_sim = 0  # starts from 0. 0 means the 1st day of simulation

    V_file = 'retail_market_Substation_2_3600'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'cleared_quantity_da'
    first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])

    first_h_df = pd.DataFrame(first_h)
    first_h_df.index = pd.date_range(start_time, periods=len(first_h), freq='1H')
    first_h_df_rt = first_h_df.resample('5min').ffill()

    V_file = 'retail_market_Substation_2_300'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'cleared_quantity_rt'
    V_analis2 = 'cleared_quantity_rt_unadj'
    first_h_rt = Order[meta_I_ver[V_analis]['index']]
    first_h_rt_unadjusted = Order[meta_I_ver[V_analis2]['index']]

    V_file = 'dso_ames_bid_Substation_2_3600'
    meta_I_ver, start_time, Order = get_data_dso_bids_da(V_file, days, pre_file, pos_file)
    V_analis = 'unresponsive_bid_da'
    V_analis2 = 'responsive_bid_da'
    first_h_da = Order[meta_I_ver[V_analis]['index']]
    first_h_da2 = Order[meta_I_ver[V_analis2]['index']]
    unresponsive_bid_da = np.array(first_h_da).reshape(int(24 * days * 2))
    responsive_bid_da = np.array(first_h_da2).reshape(int(24 * days * 2))

    unresponsive_bid_da_df = pd.DataFrame(unresponsive_bid_da)
    unresponsive_bid_da_df.index = pd.date_range('2016-08-11 00:00:00', periods=len(unresponsive_bid_da), freq='1H')
    unresponsive_bid_da_df_rt = unresponsive_bid_da_df.resample('5min').ffill()
    responsive_bid_da_df = pd.DataFrame(responsive_bid_da)
    responsive_bid_da_df.index = pd.date_range('2016-08-11 00:00:00', periods=len(responsive_bid_da), freq='1H')
    responsive_bid_da_df_rt = responsive_bid_da_df.resample('5min').ffill()

    V_file = 'dso_ames_bid_Substation_2_300'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis = 'unresponsive_bid_rt'
    V_analis2 = 'responsive_bid_rt'
    first_h_unr_rt = Order[meta_I_ver[V_analis]['index']]
    first_h_resp_rt = Order[meta_I_ver[V_analis2]['index']]

    V_file = 'dso_tso_Substation_2_300'
    meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
    V_analis2 = 'cleared_quantities_rt'
    V_analis1 = 'unresponsive_rt'
    first_h_fixed_rt = Order[meta_I_ver[V_analis1]['index']]
    first_h_cleared_rt = Order[meta_I_ver[V_analis2]['index']]

    with open(pre_file_out + "/DSO_2/Substation_" + str(dso_num) + "_agent_dict.json", 'r', encoding='utf-8') as lp:
        config = json.load(lp)

    dso_config = config['markets']['DSO_1']
    num_of_customers = dso_config['number_of_customers']
    customer_count_mix_residential = dso_config['RCI_customer_count_mix']['residential']
    number_of_gld_homes = dso_config['number_of_gld_homes']
    scale = (num_of_customers * customer_count_mix_residential / number_of_gld_homes)
    V_file = 'Substation_{}_metrics_substation'.format(dso_num)
    data_s, meta_S = get_substation_data(V_file, pre_file_sub, pos_file)

    # # aggregated house load without battery
    V_analis1 = 'real_power_avg'
    V_analis2 = 'real_power_min'
    V_analis3 = 'real_power_max'
    sub_power_avg = data_s[0, 12:, meta_S[V_analis1]['index']]
    sub_power_min = data_s[0, 12:, meta_S[V_analis2]['index']]
    sub_power_max = data_s[0, 12:, meta_S[V_analis3]['index']]

    V_file = 'Substation_{}_metrics_house'.format(dso_num)

    # fig1, ax1 = plt.subplots(3, sharex='col',figsize=(16, 8), dpi=100)
    #
    # ax1[0].plot(first_h_df_rt.values/1e3,label='DA Cleared')
    # #print(len(first_h_df_rt.index[1:]),len(first_h_rt))
    # # plt.plot(first_h_rt,label='RT');plt.legend();plt.ylabel('price ($/kWh)');plt.xlabel('time (5-min)');plt.grid(True)
    # ax1[0].plot(np.array(first_h_rt)/1e3,label='RT Cleared')
    # # if bid_adjusted is True:
    # #     ax1[0].plot(np.array(first_h_rt_unadjusted)/1e3,label='RT Bid from Previous Method')
    # ax1[0].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind',linewidth=0.75)
    #
    # ax1[0].grid(True)
    # ax1[0].set_ylabel('MW')
    # ax1[0].legend(loc='best')
    # ax1[0].set_title("Retail Market Bids")
    #
    # #ax1[1].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind')
    # ax1[1].plot(range(287-24,len(unresponsive_bid_da_df_rt)+287-24), (unresponsive_bid_da_df_rt.values + responsive_bid_da_df_rt.values), label='DSO DA Bid to AMES')
    # ax1[1].plot(range(287-12,len(first_h_unr_rt)+287-12), np.array(first_h_unr_rt)+np.array(first_h_resp_rt),label='DSO RT Bid to AMES');plt.legend();plt.ylabel('quantity (MW)')
    # ax1[1].plot(range(287 - 12, len(first_h_cleared_rt) + 287 - 12), np.array(first_h_cleared_rt) / 1e3,
    #             label='DSO Total Cleared Load AMES')
    # plt.legend()
    # plt.ylabel('quantity (MW)')
    # ax1[1].plot(range(287 - 12, len(first_h_fixed_rt) + 287 - 12), np.array(first_h_fixed_rt) / 1e3,
    #             label='DSO Inflexible Load AMES')
    # plt.legend()
    # plt.ylabel('quantity (MW)')
    #
    # ax1[1].grid(True)
    # ax1[1].set_ylabel('MW')
    # ax1[1].legend(loc='best')
    # ax1[1].set_title("Wholesale Market")
    #
    # # ax1[2].plot(np.array(first_h_rt)/1e3,label='RT Cleared')
    # ax1[2].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind',linewidth=2)
    # ax1[2].plot((3657.145492 + (sub_power_min * scale / 1e6)), label='Min GLD Load Scaled + Ind',linewidth=0.5)
    # ax1[2].plot((3657.145492 + (sub_power_max * scale / 1e6)), label='Max GLD Load Scaled + Ind',linewidth=0.5)
    # ax1[2].grid(True)
    # ax1[2].set_ylabel('MW')
    # ax1[2].legend(loc='best')
    # ax1[2].set_title("DSO GLD Load")
    #
    # #plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
    # plt.savefig("dso-ames-bid-single-bid-10days.png")
    #
    # plt.show()

    fig1, ax1 = plt.subplots(3, sharex='col', figsize=(16, 8), dpi=100)

    ax1[0].plot(first_h_df_rt.values / 1e3, label='DSO DA Cleared Local (hour 0)')
    ax1[0].plot(range(287 - 24, len(unresponsive_bid_da_df_rt) + 287 - 24),
                (unresponsive_bid_da_df_rt.values + responsive_bid_da_df_rt.values), label='DSO DA Bid to AMES')

    ax1[0].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind', linewidth=0.75)

    ax1[0].grid(True)
    ax1[0].set_ylabel('MW')
    ax1[0].legend(loc='best')
    ax1[0].set_title("Retail Market Bids")

    # ax1[1].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind')
    ax1[1].plot(np.array(first_h_rt) / 1e3, label='DSO RT Cleared Local')
    ax1[1].plot(range(287 - 12, len(first_h_unr_rt) + 287 - 12), np.array(first_h_unr_rt) + np.array(first_h_resp_rt),
                label='DSO RT Bid to AMES')
    plt.legend()
    plt.ylabel('quantity (MW)')
    ax1[1].plot(range(287 - 12, len(first_h_cleared_rt) + 287 - 12), np.array(first_h_cleared_rt) / 1e3,
                label='DSO RT Total Cleared Load AMES')
    plt.legend()
    plt.ylabel('quantity (MW)')
    ax1[1].plot(range(287 - 12, len(first_h_fixed_rt) + 287 - 12), np.array(first_h_fixed_rt) / 1e3,
                label='DSO RT Inflexible Cleared Load AMES')
    plt.legend()
    plt.ylabel('quantity (MW)')

    ax1[1].grid(True)
    ax1[1].set_ylabel('MW')
    ax1[1].legend(loc='best')
    ax1[1].set_title("Wholesale Market")

    # ax1[2].plot(np.array(first_h_rt)/1e3,label='RT Cleared')
    ax1[2].plot((3657.145492 + (sub_power_avg * scale / 1e6)), label='Avg GLD Load Scaled + Ind', linewidth=2)
    ax1[2].plot((3657.145492 + (sub_power_min * scale / 1e6)), label='Min GLD Load Scaled + Ind', linewidth=0.5)
    ax1[2].plot((3657.145492 + (sub_power_max * scale / 1e6)), label='Max GLD Load Scaled + Ind', linewidth=0.5)
    ax1[2].grid(True)
    ax1[2].set_ylabel('MW')
    ax1[2].legend(loc='best')
    ax1[2].set_title("DSO GLD Load")

    # plt.xlim([datetime.date(2016, imonth, iday), datetime.date(2016, imonth, iday + Tday)])
    plt.savefig("dso-ames-bid-single-bid-10days.png")

    plt.show()
