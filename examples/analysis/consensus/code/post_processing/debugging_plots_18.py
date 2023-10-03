"""This file assists visual debugging analyses

    Develop only for debugging purposes 
        
    Intended for simple fast visual plots (works better on IDE so multiple plots can be compared)
    Does not save plots to file
"""
import itertools
import json
import warnings
from copy import deepcopy

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# #####################################################start conf plot

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


# #####################################################end conf plot

def get_metrics_full_multiple_KEY_Mdays_H(file_name, pre_file, pos_file):
    """ Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Returns:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    for n in range(days * 24):
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
    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float64)
    names = []
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

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual  # indovidual homes


def get_metrics_full_multiple_KEY_Mdays(file_name, pre_file, pos_file):
    """ Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Returns:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    for n in range(days * 24):
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
        orig_bid_rt_ind = meta_I_ver['bid_four_point_rt']['index']
        temp.update({'bid_four_point_rt_1': {'units': 'kW', 'index': 0}})
        temp.update({'bid_four_point_rt_2': {'units': '$', 'index': 1}})
        temp.update({'bid_four_point_rt_3': {'units': 'kW', 'index': 2}})
        temp.update({'bid_four_point_rt_4': {'units': '$', 'index': 3}})
        temp.update({'bid_four_point_rt_5': {'units': 'kW', 'index': 4}})
        temp.update({'bid_four_point_rt_6': {'units': '$', 'index': 5}})
        temp.update({'bid_four_point_rt_7': {'units': 'kW', 'index': 6}})
        temp.update({'bid_four_point_rt_8': {'units': '$', 'index': 7}})
        ind = 7
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i: {'units': meta_I_ver[i]['units'], 'index': ind + 1}})
                ind = ind + 1

    meta_I_ver = {}
    meta_I_ver = temp

    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float64)
    names = []
    j = 0
    for node in list(I_ver[times[0]].keys()):
        i = 0
        for t in times:
            # print (node,t)
            temp = I_ver[t][node]
            if 'bid_four_point_rt_1' in meta_I_ver.keys():
                temp = []
                for k in range(len(I_ver[t][node][orig_bid_rt_ind])):
                    for l in range(len(I_ver[t][node][orig_bid_rt_ind][0])):
                        temp.append(I_ver[t][node][orig_bid_rt_ind][k][l])
                for p in range(len(I_ver[t][node])):
                    if p == orig_bid_rt_ind:
                        pass
                    else:
                        temp.append(I_ver[t][node][p])
            data_I_ver[j, i, :] = temp
            i = i + 1
        names.append(node)
        j = j + 1
    meta_I_ver['names'] = names

    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    # Ip = pd.Panel(data_I_ver,major_axis=index)

    all_homes_I_ver = list()
    # all_homes_I_ver.append(Ip.min(axis=0))
    # all_homes_I_ver.append(Ip.mean(axis=0))
    # all_homes_I_ver.append(Ip.max(axis=0))
    # all_homes_I_ver.append(Ip.sum(axis=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual  # indovidual homes


def get_metrics_full_multiple_KEY(file_name, pre_file, pos_file, to_hour=True):
    """ Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Returns:
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

    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x, y, z), dtype=np.float64)
    names = []
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
        names.append(node)
        j = j + 1

    meta_I_ver['names'] = names
    if (int(times[1]) - int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    # Ip = pd.Panel(data_I_ver,major_axis=index)

    all_homes_I_ver = list()
    all_homes_I_ver.append(pd.DataFrame(data_I_ver.min(axis=0), index=index))
    all_homes_I_ver.append(pd.DataFrame(data_I_ver.mean(axis=0), index=index))
    all_homes_I_ver.append(pd.DataFrame(data_I_ver.max(axis=0), index=index))
    all_homes_I_ver.append(pd.DataFrame(data_I_ver.sum(axis=0), index=index))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual  # indovidual homes


def make_convergency_test(t, data_s, tf=47):
    """ Price convergency development

    Args:
        t (int): selects the number of DA run
        data_s (list of list 48 float): clear DA prices
        tf (int): selects hour to track the development

    Returns:
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
    """ Gets the first hour of DA prices (DSO and retail)

    Args:
        t (int): selects the number of DA run
        data_s (list of list 48 float): clear DA prices

    Returns:
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
    """ Read a defined number of days

    Args:
        V_analis (str): a portion of the file name
        days (int): number of days to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Returns:
        meta_I_ver (dic): Metadata of .json file
        start_time (str): Start time of the simulation
        Order (list of Metadata): list of matadata in proper time order

    """
    d1 = dict()
    for n in range(int(days * 12)):
        file_name = V_analis + str(n) + '_metrics'
        file = open(pre_file + file_name + pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')

        d1.update(I_ver)

    I_ver = d1

    times = list(I_ver.keys())
    times = list(map(float, times))
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
    """ Read a defined number of days

    Args:
        V_analis (str): a portion of the file name
        days (int): number of days to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Returns:
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


if __name__ == "__main__":
    pre_file_out = 'case1_w40perBatt_3days_json_latest/'  #
    pre_file_out = 'TMG_helics_1_agent/'  #
    pos_file = '.json'
    days = 1
    da_convergence_start = 24 * 0  # DA interaction to start looking for convergence
    N_convergence_hours = 24  # number of hours to visualize convergence (set to zero neglect)

    dso_num = '1'
    DSO = True  # plot DSO
    DSO_DA_curve = False
    DSO_RT_curve = True
    Retail = False  # plot Retail
    Retail_site = True
    Inverters = False  # plot inverters
    Homes = False  # read homes for HVAC and water heater
    Water = False  # plot water heater
    HVAC = False
    Water_agent = False
    HVAC_agent = False
    Water_agent_individual = False
    Water_agent_collective = False
    substation = False
    pre_file = pre_file_out + 'MG_Agent_{}/'.format(dso_num)

    # Current time for plotting of DSO curves
    hour_of_day = 14  # anywhere from 0 to 23
    day_of_sim = 0  # starts from 0. 0 means the 1st day of simulation
    # DSO
    if DSO:
        # V_file = 'dso_market_Substation_{}_3600'.format(dso_num)
        # meta_I_ver, start_time, Order = get_data_multiple_days(V_file,days,pre_file,pos_file)
        # V_analis = 'trial_cleared_price_da'
        # first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
        # Plot clear DSO
        # =============================================================================
        # plt.plot(first_h,marker='x')plt.ylabel('DSO price ($/kWh)')plt.xlabel('time (hours)')plt.grid(True)plt.show()
        # =============================================================================
        # Plot convergency of DSO market
        # =============================================================================
        # for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        #     convergency_max = make_convergency_test(data_s=Order[meta_I_ver[V_analis]['index']],t=i)
        #     plt.plot(convergency_max,marker='x')plt.ylabel('DSO price ($/kWh)')plt.xlabel('from time ahead to present (hours)')plt.title('hour 48 of t: '+str(i))plt.grid(True)plt.show()
        # =============================================================================
        if DSO_DA_curve:
            # #### code to plot the DSO DA quantities vs prices
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

            V_file = 'retail_market_Substation_{}_3600'.format(dso_num)
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

            V_file = 'dso_market_Substation_{}_86400'.format(dso_num)
            meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
            V_analis = 'curve_ws_node_quantities'
            supply_q = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_ws_node_prices'
            supply_p = Order[meta_I_ver[V_analis]['index']]

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
            # #### code to plot the DSO-RT quantities vs prices
            V_file = 'dso_market_Substation_{}_300'.format(dso_num)
            V_file = 'dso_market_Substation_300'
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

            V_file = 'retail_market_Substation_{}_300'.format(dso_num)
            V_file = 'retail_market_Substation_300'
            meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
            V_analis = 'curve_buyer_rt_quantities'
            # ret_q = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_buyer_rt_prices'
            # ret_p = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_seller_rt_quantities'
            # ret_seller_q = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'curve_seller_rt_prices'
            # ret_seller_p = Order[meta_I_ver[V_analis]['index']]
            V_analis = 'cleared_quantity_rt'
            ret_cleared_q = (Order[meta_I_ver[V_analis]['index']])
            V_analis = 'cleared_price_rt'
            ret_cleared_p = (Order[meta_I_ver[V_analis]['index']])
            V_analis = 'clear_type_rt'
            ret_cleared_type = (Order[meta_I_ver[V_analis]['index']])

            # V_file = 'dso_market_Substation_{}_86400'.format(dso_num)
            # meta_I_ver, start_time, Order = get_data_multiple_days(V_file,days,pre_file,pos_file)
            # V_analis = 'curve_ws_node_quantities'
            # supply_q = Order[meta_I_ver[V_analis]['index']]
            # V_analis = 'curve_ws_node_prices'
            # supply_p = Order[meta_I_ver[V_analis]['index']]

            plt.title('RT demand and supply curves for DSO')
            # plt.plot(supply_q[day_of_sim][hour_of_day], supply_p[day_of_sim][hour_of_day], label='wholesale node supply curve')
            # plt.plot((ret_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), (ret_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), label='RT Aggregated demand curve at retail level')
            plt.plot(dso_q[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1],
                     dso_p[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1],
                     label='RT Aggregated demand curve at DSO level')
            plt.ylabel('DSO price ($/kWh)')
            plt.xlabel('Quantity (kW)')
            plt.grid(True)
            plt.legend()
            plt.show()
            print("Wholesale RT cleared price: ", dso_cleared_p[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1])
            print("Wholesale RT cleared quantity: ", dso_cleared_q[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1])
            print("Wholesale RT clear type: ", dso_cleared_type[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1])

            # plt.title('RT demand and supply curves for Retail ')
            # plt.plot((ret_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), (ret_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), label='RT Aggregated demand curve')
            # plt.plot((ret_seller_q[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), (ret_seller_p[(day_of_sim + 1) * (hour_of_day + 1) * 12 - 1]), label='RT Substation supply curve')
            # plt.ylabel('Retail price ($/kWh)')
            # plt.xlabel('Quantity (kW)')
            # plt.grid(True)
            # plt.legend()
            # plt.show()
            print("Retail cleared price:", ret_cleared_p[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1])
            print("Retail cleared quantity:", ret_cleared_q[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1])
            print("Retail clear type:", ret_cleared_type[(day_of_sim + 1) * (hour_of_day + 1) * 4 - 1])
    # Retail
    if Retail:
        V_file = 'retail_market_Substation_{}_3600'.format(dso_num)
        V_file = 'retail_market_Substation_3600'
        # ## This comment by Monish
        #         meta_I_ver, start_time, Order = get_data_multiple_days(V_file,days,pre_file,pos_file)
        #         V_analis = 'cleared_price_da'
        #         first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
        #         # ## Plot clear DSO
        #         plt.plot(first_h,marker='x')
        #         plt.ylabel('retail price ($/kWh)')
        #         plt.xlabel('time (hours)')
        #         plt.grid(True)
        #         plt.show()
        #         # Plot convergency of DSO market
        #         markers = ['.','o','v','^','<','>','1','2','3','4','8','s','p','P','*','h','H','+','x','X','D','d','|','_']
        #         M_in=0
        #         ten_AM_price = []
        #         ten_AM_ind = []
        #         for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        #             convergency_max = make_convergency_test(data_s=Order[meta_I_ver[V_analis]['index']],t=i)
        #             reverse_hour = 47 - np.arange(0,len(convergency_max))
        #             plt.plot(reverse_hour,convergency_max,marker=markers[M_in],label=str(i)+'-h',linewidth=1,markersize=5)
        #             # find the index of the prediction corresponding to 10 AM previous day
        #             temp = 48 - (14 + i % 24)
        #             ten_AM_ind.append(temp)
        #             # print(len(convergency_max))
        #             ten_AM_price.append(convergency_max[temp])
        #             plt.ylabel('retail price ($/kWh)')
        #             plt.xlabel('from time ahead to present (hours)')#;plt.title('hour 48 of t: '+str(i))
        #             plt.grid(True)
        #             plt.show()
        #             M_in = M_in + 1
        #         print(ten_AM_ind)
        #         # Marking 10 AM prices on each hour plot
        #         plt.plot(47-np.array(ten_AM_ind),ten_AM_price, 'o', color='blue')
        #         plt.xlim(47, -2) # x-axis in decreasing order
        #         plt.grid(True)
        #         plt.legend(bbox_to_anchor=(1.1, 1.00))
        #         plt.show()
        #
        #         first_h_df = pd.DataFrame(first_h)
        #         first_h_df.index = pd.date_range(start_time,periods=len(first_h), freq='1H')
        #         first_h_df_rt = first_h_df.resample('5min').ffill()

        V_file = 'retail_market_Substation_{}_300'.format(dso_num)
        V_file = 'retail_market_Substation_300'
        meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
        V_analis = 'cleared_price_rt'
        first_h_rt = Order[meta_I_ver[V_analis]['index']]
        # plt.plot(np.array(range(len(first_h_df_rt)))/12, first_h_df_rt.values,label='DA')
        plt.plot(np.array(range(len(first_h_rt))) / 12, first_h_rt, label='RT')
        plt.legend()
        plt.ylabel('price ($/kWh)')
        plt.xlabel('time (hour)')
        plt.grid(True)
        plt.show()

        # first_h_rt = pd.DataFrame(first_h_rt)
        # first_h_rt.index = pd.date_range(pd.to_datetime(start_time) + pd.Timedelta('3900s'),periods=len(first_h_rt), freq='5min')

    if Retail_site:
        gld_pre_file = pre_file_out + 'Substation_{}/'.format(dso_num)
        gld_pre_file = pre_file_out + 'Substation/'
        # Lets get total substation load from gridlabd
        V_file = 'Substation_{}_metrics_substation'.format(dso_num)
        V_file = 'Substation_metrics_substation'.format(dso_num)
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file, gld_pre_file, pos_file)
        # # aggregated house load without battery
        V_analis = 'real_power_avg'
        sub_power = data_s[3][meta_S[V_analis]['index']]  # plots aggregated

        V_file = 'Substation_{}_metrics_inverter'.format(dso_num)
        V_file = 'Substation_metrics_inverter'
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file, gld_pre_file, pos_file)
        V_analis = 'real_power_avg'  # variable being analized
        inv_power = data_s[3][meta_S[V_analis]['index']]
        orig_power = inv_power + sub_power

        # get forecast uncontrollable load
        V_file = 'retail_site_Substation_{}_3600'.format(dso_num)
        meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
        V_analis = 'non_transactive_quantities'
        plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='total load')
        V_analis = 'non_transactive_zip'
        plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='zip load')
        V_analis = 'non_transactive_hvac'
        plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='hvac load')
        V_analis = 'non_transactive_wh'
        plt.plot(sum(np.array(Order[meta_I_ver[V_analis]['index']][(days - 1) * 24])), label='waterheater load')
        plt.legend()
        plt.ylabel('load (kW)')
        plt.xlabel('time (hour)')
        plt.grid(True)
        plt.title('Estimated non-participating load profiles')
        plt.show()

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
        # Plot clear DSO
        #        plt.plot(first_h,marker='x')
        #        plt.ylabel('retail price ($/kWh)')
        #        plt.xlabel('time (hours)')
        #        plt.grid(True)
        #        plt.show()
        # ## Plot convergency of DSO market
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
            plt.xlabel('from time ahead to present (hours)')
            # plt.title('hour 48 of t: '+str(i))
            # plt.grid(True)
            # plt.show()
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
        #     plt.xlabel('from time ahead to present (hours)')
        #     plt.title('hour 48 of t: '+str(i))
        #     plt.grid(True)
        #     plt.show()
        #     M_in = M_in + 1
        # plt.grid(True)
        # plt.legend(bbox_to_anchor=(1.1, 1.00))
        plt.show()
    # =============================================================================
    #    # #plot of retail da quantitites
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

    # #####################################################
    # #####################################################
    # #####################################################
    pre_file = pre_file_out + 'Substation_{}/'.format(dso_num)
    # Inverters
    if Inverters:
        V_file = 'Substation_{}_metrics_substation'.format(dso_num)
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
        # # aggregated house load without battery
        V_analis = 'real_power_avg'
        sub_power = data_s[3][meta_S[V_analis]['index']]  # plots aggregated

        V_file = 'Substation_{}_metrics_inverter'.format(dso_num)
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
        V_analis = 'real_power_avg'  # variable being analyzed
        inv_ind_power = data_individual[10][meta_S[V_analis]['index']]
        inv_power = data_s[3][meta_S[V_analis]['index']]
        inv_power_avg = data_s[1][meta_S[V_analis]['index']]
        inv_power_min = data_s[0][meta_S[V_analis]['index']]
        inv_power_max = data_s[2][meta_S[V_analis]['index']]
        orig_power = sub_power + inv_power
        to_kW = 1000

        plt.plot((orig_power.resample('60min').mean() / to_kW).values, label="base load profile")
        plt.plot((sub_power.resample('60min').mean() / to_kW).values, label='with battery participation')
        plt.ylabel('Aggregated power (kW)')
        plt.xlabel('time (hours)')
        plt.grid(True)
        plt.legend()
        plt.title("Impact of 40% battery participation on the substation load profile")
        # plt.show()

        fig1, ax1 = plt.subplots(2, 1, sharex='col')
        ax1[0].set_title("Retail cleared prices and corresponding aggregated inverter power")
        ax1[0].plot(np.array(range(len(inv_power))) / 12, (inv_power / 1000).values)
        ax1[0].plot([0, len(inv_power.resample('60min'))], [0, 0], 'k')
        ax1[0].set_ylabel('agregated inverter power (kW)')
        ax1[0].grid(True)
        ax1[1].plot(first_h, label='DA')
        ax1[1].plot(np.array(range(len(first_h_rt))) / 12, first_h_rt, label='RT')
        ax1[1].set_ylabel('Retail price ($/kWh)')
        ax1[1].set_xlabel('time (hours)')
        plt.legend()
        plt.grid(True)
        plt.show()

        # fig1, ax1 = plt.subplots(2, 1, sharex='col')
        # ax1[0].set_title("Retail cleared prices and corresponding individual inverter power")
        # ax1[0].plot(np.array(range(len(inv_ind_power)))/12, (inv_ind_power / 1000).values, label='One inverter unit')
        # # ax1[0].plot(np.array(range(len(inv_power_avg)))/12, (inv_power_avg / 1000).values, label='Average inverter power')
        # ax1[0].plot([0, len(inv_ind_power.resample('60min'))], [5, 5], 'k--', label='Inverter rating')
        # ax1[0].plot([0, len(inv_ind_power.resample('60min'))], [-5, -5], 'k--')
        # ax1[0].plot([0, len(inv_ind_power.resample('60min'))], [0, 0], 'k')
        # ax1[0].set_ylabel('individual inverter power (kW)')
        # ax1[0].legend()
        # ax1[0].grid(True)
        # ax1[1].plot(first_h, label='DA')
        # ax1[1].plot(np.array(range(len(first_h_rt))) / 12, first_h_rt, label='RT')
        # ax1[1].set_ylabel('Retail price ($/kWh)')
        # ax1[1].set_xlabel('time (hours)')
        # plt.legend()
        # plt.grid(True)
        # plt.show()

        # get DA cleared quantities at 10 AM
        # ten_am = day_of_sim*24 + 10
        pre_file = pre_file_out + 'DSO_{}/'.format(dso_num)
        V_file = 'retail_site_Substation_{}_3600'.format(dso_num)
        meta_I_ver, start_time, Order = get_data_multiple_days_10AM(V_file, days, pre_file, pos_file)
        # file = open(pre_file + V_file + pos_file, 'r')
        # text = file.read()
        # I_ver = json.loads(text)
        # meta_I_ver = I_ver.pop('Metadata')
        V_analis = 'transactive_batt'
        data = Order[meta_I_ver[V_analis]['index']]
        data_s_sum = []
        for i in data:
            # collect midnight to next 24 hrs data: 14th hour to 38th hour from each day 10 AM data
            data_s_sum.append(np.array(i).sum(axis=0).tolist()[14:14 + 24])
            # data_s_sum.append(i[0])
        # flatten the list to 1-D
        da_cleared_q = [j for sub in data_s_sum for j in sub]
        # remove the last 24 entries as they are forecast for non-exisiting day
        da_cleared_q = da_cleared_q[:-24]
        # get actual inverter power
        inv_power_hr = inv_power.resample('60min').mean().values
        fig2, ax2 = plt.subplots()
        # ax2 = ax1.twinx()
        ax2.plot((da_cleared_q), label='cleared DA bid')
        ax2.plot(inv_power_hr[24 + 1:] / 1000, label='actual consumption')  # remove 1st day
        ax2.set_ylabel('kW')
        ax2.grid(True)
        ax2.set_title(
            "Cleared DA bid and actual kW by battery agent ")  # ax1.set_ylabel('(F)')
        ax2.legend()
        plt.show()

        # Plotting agent parameters and optimal bids
        V_file = 'battery_agent_Substation_{}_3600'.format(dso_num)
        meta_da, start_time, data_da, da_bid_batt = get_metrics_full_multiple_KEY_Mdays_H(V_file, pre_file,
                                                                                          '_metrics' + pos_file)

        V_file = 'battery_agent_Substation_{}_300'.format(dso_num)
        meta_rt, start_time, data_rt, rt_bid_batt = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                        '_metrics' + pos_file)
        to_kW = 1

        agent_dict = "Substation_{}_agent_dict.json".format(dso_num)
        file = open(pre_file + agent_dict, 'r')
        text = file.read()
        file.close()
        batt_agent = json.loads(text)
        batt_agent = batt_agent['batteries']
        property = 'slider_setting'
        prop = []
        opt = []
        dev = []

        fig1, ax1 = plt.subplots(2, sharex='col')
        # ax2 = ax1.twinx()
        i = 1
        opt_bid = da_bid_batt[i][meta_da['bid_four_point_rt_3']['index']]
        ax1[0].plot((opt_bid.resample('60min').mean() / to_kW).values, label='optimal bid')
        actual = rt_bid_batt[i][meta_rt['inverter_p_setpoint']['index']]
        ax1[0].plot(-(actual.resample('60min').mean() / 1000).values, label='actual power')
        ax1[0].set_ylabel('kW')
        ax1[0].grid(True)
        ax1[0].set_title(
            "Optimal bid and actual kW by battery agent with slider setting {}".format(
                batt_agent[meta_da['names'][i]]['slider_setting']))  # ax1.set_ylabel('(F)')
        ax1[0].legend()

        i = 5
        opt_bid = da_bid_batt[i][meta_da['bid_four_point_rt_3']['index']]
        ax1[1].plot((opt_bid.resample('60min').mean() / to_kW).values, label='optimal bid')
        actual = rt_bid_batt[i][meta_rt['inverter_p_setpoint']['index']]
        ax1[1].plot(-(actual.resample('60min').mean() / 1000).values, label='actual power')
        ax1[1].set_ylabel('kW')
        ax1[1].grid(True)
        ax1[1].set_title(
            "Optimal bid and actual kW by battery agent with slider setting {}".format(
                batt_agent[meta_da['names'][i]]['slider_setting']))  # ax1.set_ylabel('(F)')
        ax1[1].legend()
        plt.xlabel('time (hours)')
        plt.show()

        actual = np.zeros(24 * days)
        actual_all = []
        soc = np.zeros(24 * days)
        soc_all = []
        for i in range(len(rt_bid_batt)):
            temp = rt_bid_batt[i][meta_rt['inverter_p_setpoint']['index']].resample('60min').mean().values
            soc_temp = rt_bid_batt[i][meta_rt['battery_soc']['index']].resample('60min').mean().values
            cap = batt_agent[meta_rt['names'][i]]['capacity'] / 1000
            if len(temp) != 24 * days:
                temp = np.append(temp, temp[-1])
            if len(soc_temp) != 24 * days:
                soc_temp = np.append(soc_temp, soc_temp[-1])
            actual = actual + temp / 1000
            soc = soc + soc_temp / cap
            soc_all.append(soc_temp / cap)
            actual_all.append(temp / 1000)
        actual = actual[0:]
        soc = soc[0:] / len(rt_bid_batt)

        # plot soc and setpoint and gridlabd output of individual battery
        figsoc, ax1soc = plt.subplots(2, sharex='col')
        ax1soc[0].plot(actual, label='real-time P set-point')
        ax1soc[0].plot(inv_power_hr[1:] / 1000, label='actual consumption (gridlabd)')
        ax1soc[1].plot(soc, label='soc')
        # for i in range(len(soc_all)):
        #     if i==114: # max(soc_all[i]) >= 1:
        #         print(i)
        #         j = meta_S['names'].index(meta_rt['names'][i])
        #         gld_ind = data_individual[j][meta_S['real_power_avg']['index']].resample('60min').mean().values
        #         ax1soc[0].plot(actual_all[i])
        #         ax1soc[0].plot(gld_ind[1:]/1000)
        #         ax1soc[1].plot(soc_all[i])
        ax1soc[0].legend()
        ax1soc[1].legend()
        plt.show()

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

        for key, value in batt_agent.items():
            ind = meta_da['names'].index(key)
            optimal_pt = da_bid_batt[ind][meta_da['bid_four_point_rt_3']['index']]
            optimal_pt = (optimal_pt.resample('60min').mean() / 1).values
            ind2 = meta_rt['names'].index(key)
            actual_p = rt_bid_batt[ind2][meta_rt['inverter_p_setpoint']['index']]
            actual_p = -(actual_p.resample('60min').mean() / 1000).values
            # if value[property] >= 0.95:
            #     print(ind)
            #     print(ind2)
            prop.append(value[property])
            opt.append(optimal_pt[20])
            dev.append((abs(optimal_pt[0:167] - actual_p)).mean())
        plt.scatter(prop, dev, label='deviation from optimal bid')
        plt.title('deviation from optimal bid')
        plt.ylabel('kW')
        plt.xlabel('Slider Setting')
        plt.show()

        # # Profit Calculation
        # V_analis = 'real_power_avg'  # variable being analized
        # first_h_rt_df = pd.DataFrame(first_h_rt)
        # first_h_rt_df.index = pd.date_range(pd.to_datetime(start_time) + pd.Timedelta('3900s'), periods=len(first_h_rt),
        #                                  freq='5min')
        # for i in range(len(rt_bid_batt)):
        #     actual = (rt_bid_batt[i][meta_rt['inverter_p_setpoint']['index']]/1000)
        #     actual.multiply(first_h_rt_df, fill_value=0)

        # fig = plt.figure()
        # ax1 = fig.add_subplot(111)
        # ax1.plot((inv_power.resample('60min').mean()/1000).values,marker='x',color='r')
        # ax1.set_xlabel('time (hours)')
        # ax1.set_ylabel('agregated inverter power (kW)',color='tab:red')
        # ax2 = ax1.twinx()
        # ax2.plot(first_h,marker='o',color='b')
        # ax2.set_ylabel('DA retail price ($/kWh)',color='tab:blue')
        # plt.grid(True)
        # plt.show()

    # Homes
    if Homes:
        V_file = 'Substation_{}_metrics_house'.format(dso_num)
        meta_S, start_time, data_house, data_individual = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
        # ## Water
        if Water:
            V_analis = 'waterheater_load_avg'
            AVG_power = data_house[1][meta_S[V_analis]['index']]  # plots mean
            to_kW = 1
            plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
            plt.ylabel('agregated mean water heater power (kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.show()
            for i in range(len(data_individual) * 0):
                AVG_power = data_individual[i][meta_S[V_analis]['index']]
                plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
                plt.ylabel('water heater power (kW)')
                plt.xlabel('time (hours)')
                plt.grid(True)
                plt.title('home: ' + str(i))
                plt.show()
            V_analis = 'waterheater_load_max'
            AVG_power = data_house[0][meta_S[V_analis]['index']]  # plots min
            plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
            plt.ylabel('min min water heater power (kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.show()
            AVG_power = data_house[2][meta_S[V_analis]['index']]  # plots max
            plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
            plt.ylabel('max max water heater power (kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.show()

        # HVAC
        if HVAC:
            V_analis = 'hvac_load_avg'
            AVG_power = data_house[1][meta_S[V_analis]['index']]  # plots mean
            to_kW = 1
            plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
            plt.ylabel('avg agregated hvac load (kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.show()
            for i in [14]:  # range(len(data_individual)):
                AVG_power = data_individual[i][meta_S[V_analis]['index']]
                plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
                plt.ylabel('hvac load (kW)')
                plt.xlabel('time (hours)')
                plt.grid(True)
                plt.title('home: ' + str(i))
                plt.show()
            V_analis = 'hvac_load_avg'
            AVG_power = data_house[0][meta_S[V_analis]['index']]  # plots min
            plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
            plt.ylabel('min min hvac_load (kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.show()
            AVG_power = data_house[2][meta_S[V_analis]['index']]  # plots max
            plt.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x')
            plt.ylabel('max max hvac_load_avg (kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.show()

    # new HVAC
    if HVAC_agent and 0:
        # for iday in range(3):
        pre_file = pre_file_out + 'dso_1/'
        iday = 0
        V_file = 'hvac_agent_Substation_{}_300_{:.0f}_metrics'.format(dso_num, iday)
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
        # meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
        V_analis = ['room_air_temperature', 'outdoor_temperature', 'thermostat_setpoint', 'cooling_basepoint',
                    'cleared_price']
        to_kW = 1
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        for i in range(14, 15):  # range(len(data_individual)):
            for ivar in range(len(V_analis) - 1):
                AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
                ax1.plot((AVG_power / to_kW).values, marker='x', label=V_analis[ivar])
                ax1.set_ylabel('(F)')
                plt.xlabel('time (hours)')
                plt.grid(True)
                plt.title('home ' + str(i) + ' - day {:.0f}'.format(iday))
            ax1.legend()
            AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
            ax2.plot((AVG_power / to_kW).values, '-', color='k', label=V_analis[-1])
            ax2.set_ylabel('price ($/kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            # ax2.legend()
            plt.show()

    if HVAC_agent and 0:
        pre_file = pre_file_out + 'dso_1/'
        V_file = 'hvac_agent_Substation_{}_3600_'.format(dso_num)
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                          '_metrics' + pos_file)
        V_analis = ['room_air_temperature', 'outdoor_temperature', 'thermostat_setpoint', 'cooling_basepoint',
                    'cleared_price']
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
            AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
            ax2.plot((AVG_power / to_kW).values, '-', color='k', label=V_analis[-1])
            ax2.set_ylabel('price ($/kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            # ax2.legend()
            plt.show()

    if HVAC_agent and 1:
        pre_file = pre_file_out + 'dso_{}/'.format(dso_num)
        V_file = 'hvac_agent_Substation_{}_300'.format(dso_num)
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                          '_metrics' + pos_file)
        V_analis = ['DA_quantity']
        to_kW = 1
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        for i in [14]:  # range(len(data_individual)):
            for ivar in range(len(V_analis)):
                AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
                ax1.plot((AVG_power.resample('60min').mean() / to_kW).values, marker='x', label=V_analis[ivar])
                plt.xlabel('time (hours)')
                plt.grid(True)
                plt.title('home ' + str(i))  # ax1.set_ylabel('(F)')
            ax1.legend()
            '''
            AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
            ax2.plot((AVG_power/to_kW).values,'-', color='k',label=V_analis[-1])
            ax2.set_ylabel('price ($/kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            #ax2.legend()
            '''
            plt.show()
    # new waterheater agent
    if Water_agent and 1:
        savefig = 1
        pre_file = pre_file_out + 'DSO_{}/'.format(dso_num)
        hour_to_5min = 12
        # index of houses with waterheaters - house 50, 1, 19 show nice variation selected
        idx = [50, 1, 19, 24]

        pre_file = pre_file_out + 'DSO_{}/'.format(dso_num)

        if Water_agent_collective:
            # DA data
            V_file = 'retail_market_Substation_{}_3600'.format(dso_num)
            meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
            V_analis = 'cleared_quantity_da'
            first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])

            first_h_df = pd.DataFrame(first_h)
            first_h_df.index = pd.date_range(start_time, periods=len(first_h), freq='1H')
            first_h_df_rt = first_h_df.resample('5min').ffill()

            V_file = 'retail_market_Substation_{}_300'.format(dso_num)
            meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
            V_analis = 'cleared_quantity_rt'
            first_h_rt = Order[meta_I_ver[V_analis]['index']]
            first_h_rt_df = pd.DataFrame(first_h_rt)
            first_h_rt_df.index = pd.date_range(start_time, periods=len(first_h_rt), freq='5min')

            figdim = (20, 20)
            fig, ax = plt.subplots(figsize=figdim)

            # ax.plot(first_h_df_rt.index, first_h_df_rt.values, 'k', label='DA Cleared Load')
            ax.plot(first_h_rt_df.index, first_h_rt_df.values, 'r', label='RT Cleared Load ')

            ax.legend()
            ax.set_ylabel('kW')
            ax.set_xlabel('time (hour)')
            ax.grid(True)
            ax.set_title('Cleared Load')

            if savefig:
                plt.savefig('Cleared_Load_' + str(days) + '_days.png')

            plt.show()

            V_file = 'retail_site_Substation_{}_3600'.format(dso_num)
            meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
            V_analis = 'quantities'

            first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
            first_h_quantities_df = pd.DataFrame(first_h)
            first_h_quantities_df.index = pd.date_range(start_time, periods=len(first_h), freq='1H')

            # V_analis = 'non_transactive_zip'
            # first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
            # first_h_non_transactive_zip_df = pd.DataFrame(first_h)
            # first_h_non_transactive_zip_df.index = pd.date_range(start_time, periods=len(first_h), freq='1H')
            #
            # V_analis = 'non_transactive_hvac'
            # first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
            # first_h_non_transactive_hvac_df = pd.DataFrame(first_h)
            # first_h_non_transactive_hvac_df.index = pd.date_range(start_time, periods=len(first_h), freq='1H')

            V_file = 'water_heater_agent_Substation_{}_300'.format(dso_num)
            meta_rt, start_time, data_rt, rt_bid_wh = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                          '_metrics' + pos_file)

            total_actual_consumption = np.zeros(rt_bid_wh[0].shape[0])
            for i in range(0, len(meta_rt['names'])):
                total_actual_consumption += rt_bid_wh[i][meta_rt['Energy_GLD']['index']].values

            total_actual_consumption_df = pd.DataFrame(total_actual_consumption)
            total_actual_consumption_df.index = pd.date_range(start_time, periods=len(total_actual_consumption),
                                                              freq='5min')
            total_actual_consumption_hourly = total_actual_consumption_df.resample('60min').mean().values * hour_to_5min

            figdim = (20, 20)
            fig, ax = plt.subplots(figsize=figdim)
            ax.plot(first_h_quantities_df.index, first_h_quantities_df.values, 'k', label='Uncontrollable Load')
            ax.legend(loc='northwest')
            ax.set_ylabel('load (kW)')
            ax.set_xlabel('time (hour)')
            ax.grid(True)
            ax1 = ax.twinx()
            ax1.plot(first_h_quantities_df.index[0:-1], total_actual_consumption_hourly, 'r', label='Transactive Load')
            ax1.legend(loc=0)
            ax1.set_ylabel('load (kW)')

            ax.set_title(' Hourly GLD Load ')
            if savefig:
                plt.savefig("Actual_Load_" + str(days) + "_days.png", dpi=fig.dpi)
            plt.show()

        if Water_agent_individual:

            V_file = 'water_heater_agent_Substation_{}_3600'.format(dso_num)
            meta_da, start_time, data_da, da_bid_wh = get_metrics_full_multiple_KEY_Mdays_H(V_file, pre_file,
                                                                                            '_metrics' + pos_file)

            V_file = 'water_heater_agent_Substation_{}_300'.format(dso_num)
            meta_rt, start_time, data_rt, rt_bid_wh = get_metrics_full_multiple_KEY_Mdays(V_file, pre_file,
                                                                                          '_metrics' + pos_file)

            agent_dict = "Substation_{}_agent_dict.json".format(dso_num)
            file = open(pre_file + agent_dict, 'r')
            text = file.read()
            file.close()
            wh_agent = json.loads(text)
            wh_agent = wh_agent['water_heaters']
            property = 'slider_setting'
            prop = []
            opt = []
            dev = []

            to_kW = 1

            for i in range(len(idx)):
                hse_name = meta_da['names'][idx[i]]
                wh_name = hse_name.replace('hse', 'wh')
                print(wh_name)
                setpoints = rt_bid_wh[idx[i]][meta_rt['upper_tank_setpoint']['index']]
                wd_rate = rt_bid_wh[idx[i]][meta_rt['Waterdraw_gld']['index']]
                consumption = rt_bid_wh[idx[i]][meta_rt['Energy_GLD']['index']]
                price = rt_bid_wh[idx[i]][meta_rt['bid_four_point_rt_4']['index']]
                quantity_rt = rt_bid_wh[idx[i]][meta_rt['bid_four_point_rt_3']['index']]
                SOHC = rt_bid_wh[idx[i]][meta_rt['SOHC_gld']['index']]

                quantity_da = da_bid_wh[idx[i]][meta_da['bid_four_point_rt_3']['index']]

                fig, ax1 = plt.subplots(3, figsize=(20, 20))

                ax1[0].set_title(
                    "Graphs for {} with slider setting {:.3f}".format(wh_name, wh_agent[wh_name][
                        'slider_setting']))
                # ax1.set_ylabel('(F)')
                ax1[0].plot(quantity_da.index, (quantity_da.resample('60min').mean()).values,
                            label='Day Ahead Bid Quantity')
                ax1[0].plot(quantity_da.index[0:len((quantity_rt.resample('60min').mean()).values)],
                            (quantity_rt.resample('60min').mean()).values, label='Real Time Bid Quantity (Average)')
                ax1[0].legend(loc='northwest')
                ax1[0].set_ylabel('kW')
                ax1[0].grid(True)
                # ax1[1].set_xlabel('Time Interval (1 hr)')

                cleared_price = da_bid_wh[i][meta_da['bid_four_point_rt_4']['index']]
                ax11 = ax1[0].twinx()
                ax11.plot(cleared_price.index, (cleared_price.resample('60min').mean()).values, 'r',
                          label='Day Ahead Cleared Price')
                ax11.grid(True)
                ax11.legend(loc='northeast')
                ax11.set_ylabel('$/kWh')

                ax1[1].plot(consumption.index, consumption.values * hour_to_5min, 'k--', label="Actual Consumption-GLD")
                ax1[1].legend(loc='northwest')
                ax1[1].set_ylabel('kW')
                ax1[1].grid(True)
                # ax1[1].set_xlabel('Time Interval (5 min)')

                ax22 = ax1[1].twinx()
                ax22.plot(SOHC.index, SOHC.values, 'r', label="SOHC")
                ax22.legend(loc='northeast')
                ax22.set_ylabel('-')
                ax22.grid(True)

                ax1[2].plot(setpoints.index, setpoints.values, 'm--', label="Setpoint")
                ax1[2].set_ylabel('degF')
                ax1[2].legend()
                ax1[2].grid(True)

                ax12 = ax1[2].twinx()
                ax12.plot(wd_rate.index, wd_rate.values, 'r', label="WaterDraw")
                ax12.legend(loc=0)
                ax12.set_ylabel('GallonPerMinute')
                ax12.grid(True)
                ax1[2].set_xlabel('Time Interval (5 min)')
                if savefig == 1:
                    plt.savefig('individual_plot_' + str(wh_name) + '_' + str(days) + '_days.png', dpi=fig.dpi)
                plt.show()

    if substation:
        gld_pre_file = pre_file_out + 'Substation_{}/'.format(dso_num)
        # Lets get total substation load from gridlabd
        V_file = 'Substation_{}_metrics_substation'.format(dso_num)
        meta_S, start_time, data_sub, data_individual = get_metrics_full_multiple_KEY(V_file, gld_pre_file, pos_file)
        # # aggregated house load without battery
        V_analis = 'real_power_avg'
        sub_power = data_sub[3][meta_S[V_analis]['index']]

        V_file = 'Substation_{}_metrics_house'.format(dso_num)
        meta_S, start_time, data_house, data_individual = get_metrics_full_multiple_KEY(V_file, gld_pre_file, pos_file)
        hvac_power = data_house[3][meta_S['hvac_load_avg']['index']]  # sum
        wh_power = data_house[3][meta_S['waterheater_load_avg']['index']]  # sum

        # total power of only residential houses
        res_total_load = np.array([0] * len(data_individual[0][meta_S['total_load_avg']['index']]))
        res_hvac_load = np.array([0] * len(data_individual[0][meta_S['hvac_load_avg']['index']]))
        res_wh_load = np.array([0] * len(data_individual[0][meta_S['waterheater_load_avg']['index']]))
        for i in range(len(data_individual)):
            if 'zone' not in meta_S['names'][i]:
                res_total_load = res_total_load + data_individual[i][meta_S['total_load_avg']['index']]
                res_hvac_load = res_hvac_load + data_individual[i][meta_S['hvac_load_avg']['index']]
                res_wh_load = res_wh_load + data_individual[i][meta_S['waterheater_load_avg']['index']]

        res_zip_load = res_total_load - res_hvac_load - res_wh_load

        gd_load = (sub_power.resample('60min').mean() / 1000).values
        plt.plot(sub_power.resample('60min').mean().values / 1000, label="Substation Net load")
        # plt.plot(hvac_power.resample('60min').mean().values, label="hvac load")
        # plt.plot(wh_power.resample('60min').mean().values, label="wh load")
        plt.plot(res_total_load.resample('60min').mean().values, label="Total residential load")
        plt.plot(res_hvac_load.resample('60min').mean().values, label="hvac residential load")
        plt.plot(res_zip_load.resample('60min').mean().values, label="ZIP residential load")
        plt.legend()
        plt.ylabel('load (kW)')
        plt.xlabel('time (hour)')
        plt.grid(True)
        plt.title('Residential Load Profile')
        plt.show()

        cset_avg = data_house[1][meta_S['air_temperature_deviation_cooling']['index']]
        hset_avg = data_house[1][meta_S['air_temperature_deviation_heating']['index']]
        # for i in range(len(data_individual)):
        #     cset_i = data_individual[i][meta_S['air_temperature_deviation_cooling']['index']]
        #     plt.plot(cset_i.values, color='k')
        # plt.plot(cset_avg.values, color='r', label='average cooling setpoint')
        # plt.show()
        # for i in range(len(data_individual)):
        #     hset_i = data_individual[i][meta_S['air_temperature_deviation_heating']['index']]
        #     plt.plot(hset_i.values, color='k')
        plt.plot(hset_avg.values, color='r', label='average heating setpoint')
        plt.show()
        # ax1[1, 0].plot(hrs, out_temp[hrs_start + 1:hrs_start + 1 + len(hrs)], label='outside air temp')
        # ax1[1, 0].set_title("Cooling setpoints for all HVAC units")
        # ax1[1, 0].set_ylabel("Farenhite")
        # ax1[1, 0].set_xlabel("hours")
        # ax1[1, 0].legend(loc='best')
