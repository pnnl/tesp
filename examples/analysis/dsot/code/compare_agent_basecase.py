import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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

    Ip = pd.Panel(data_I_ver, major_axis=index)

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(axis=0))
    all_homes_I_ver.append(Ip.mean(axis=0))
    all_homes_I_ver.append(Ip.max(axis=0))
    all_homes_I_ver.append(Ip.sum(axis=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i, :, :], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual, list(I_ver[times[0]].keys())  # indovidual homes


cases = [44, 33]
labels = ['Transactive', 'BaseCase']
for i in range(len(cases)):
    pre_file_out = 'C:/Users/tbai440/tesp-private/examples/dsot_v3/GoodRuns/{}/case1/'.format(cases[i])  #
    pos_file = '.json'
    pre_file = pre_file_out + 'Substation_2/'
    V_file = 'house_Substation_2_metrics'
    if cases[i] == 44:
        V_file = 'Substation_2_metrics_house'
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
    V_analis = 'hvac_load_avg'
    AVG_power = data_s[3][meta_S[V_analis]['index']]  # plots min, mean, max, sum
    # greater than the start date and smaller than the end date
    # mask = (AVG_power.index >= '08-16-2016') & (AVG_power.index <= '08-18-2016')
    # AVG_power = AVG_power.loc[mask]
    V_analis2 = 'air_temperature_avg'
    AVG_power2 = data_s[1][meta_S[V_analis2]['index']]  # plots mean
    to_kW = 1
    plt.plot((AVG_power.resample('60min').mean() / to_kW).index, (AVG_power.resample('60min').mean() / to_kW).values,
             marker='x', label=labels[i])
    plt.ylabel('agregated hvac load (kW)')
    plt.xlabel('time (hours)')
plt.grid(True)
plt.legend()
plt.show()

houses = {"R5_12_47_2_tn_2_hse_1": 0.9776, "R5_12_47_2_load_10_bldg_82_zone_all": 0.71, "R5_12_47_2_tn_133_hse_1": 0.71,
          "R5_12_47_2_tn_1_hse_1": 0.1295, "R5_12_47_2_tn_3_hse_4": 0.3273, "R5_12_47_2_tn_3_hse_5": 0.0295,
          "R5_12_47_2_tn_4_hse_3": 0.1225}
# houses = {"R5_12_47_2_load_10_bldg_82_zone_all":0.71}

plot_data = {}
for ii in range(len(cases)):
    plot_data_case = {}
    pre_file_out = 'C:/Users/tbai440/tesp-private/examples/dsot_v3/GoodRuns/{}/case1/'.format(cases[ii])  #
    pos_file = '.json'
    pre_file = pre_file_out + 'Substation_2/'
    V_file = 'house_Substation_2_metrics'
    if cases[ii] == 44:
        V_file = 'Substation_2_metrics_house'
    meta_S, start_time, data_s, data_individual, data_key = get_metrics_full_multiple_KEY(V_file, pre_file, pos_file)
    V_analis = 'hvac_load_avg'

    for i in range(len(data_individual)):  # [0, 200]:  #
        # commercial with high slider 0.71 "R5_12_47_2_load_10_bldg_82_zone_all":
        # residential with 0.089 slider "R5_12_47_2_tn_1_hse_3":
        # residential with 0.71 slider "R5_12_47_2_tn_133_hse_1":
        # residential with 0.97 slider "R5_12_47_2_tn_2_hse_1"
        # residential with 0.1295 slider "R5_12_47_2_tn_1_hse_1::
        # residential with 0.3273 slider "R5_12_47_2_tn_3_hse_4":
        # residential with 0.0295 slider "R5_12_47_2_tn_3_hse_5":
        # residential with 0.1824 slider "R5_12_47_2_tn_4_hse_2":
        # residential with 0.1225 slider "R5_12_47_2_tn_4_hse_3":

        if data_key[i] in houses.keys():  # ihouse:
            AVG_power = data_individual[i][meta_S[V_analis]['index']]
            # greater than the start date and smaller than the end date
            mask = (AVG_power.index >= '08-20-2016') & (AVG_power.index <= '08-22-2016')
            AVG_power = AVG_power.loc[mask]
            plot_data_case.update({data_key[i]: [(AVG_power.resample('60min').mean()).index,
                                                 (AVG_power.resample('60min').mean()).values]})
        else:
            continue

        # if not (data_key[i] == 'R5_12_47_2_tn_133_hse_1' or data_key[i] == 'R5_12_47_2_load_10_bldg_82_zone_all'):
        #     continue

        if False:
            AVG_power = data_individual[i][meta_S[V_analis]['index']]
            # greater than the start date and smaller than the end date
            mask = (AVG_power.index >= '08-18-2016') & (AVG_power.index <= '08-20-2016')
            AVG_power = AVG_power.loc[mask]

            plt.plot((AVG_power.resample('60min').mean()).index, (AVG_power.resample('60min').mean()).values,
                     marker='x', label=labels[ii])
            print(AVG_power.sum())
            plt.ylabel('hvac load (kW)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.title('home:{} slider:{}'.format(str(data_key[i]), houses[data_key[i]]))
        elif False:
            V_analis2 = 'air_temperature_avg'
            AVG_power2 = data_individual[i][meta_S[V_analis2]['index']]
            mask = (AVG_power2.index >= '08-18-2016') & (AVG_power2.index <= '08-19-2016')
            AVG_power2 = AVG_power2.loc[mask]
            # plt.plot((AVG_power2.resample('60min').mean()).index,(AVG_power2.resample('60min').mean()).values, marker='x',label=labels[ii])
            plt.plot(AVG_power2.index, AVG_power2.values, marker='x', label=labels[ii])
            plt.ylabel('room temperature (F)')
            plt.xlabel('time (hours)')
            plt.grid(True)
            plt.title('home:{} slider:{}'.format(str(data_key[i]), houses[data_key[i]]))

    plot_data.update({cases[ii]: plot_data_case})

for ihouse in houses.keys():
    print(ihouse, houses[ihouse])
    for ii in range(len(cases)):
        plt.plot(plot_data[cases[ii]][ihouse][0], plot_data[cases[ii]][ihouse][1], marker='x',
                 label=labels[ii])
        print(labels[ii])
        print(plot_data[cases[ii]][ihouse][1].sum())
        plt.ylabel('hvac load (kW)')
        plt.xlabel('time (hours)')
        plt.grid(True)
        plt.title('home:{} slider:{}'.format(str(ihouse), houses[ihouse]))
    plt.legend()
    plt.show()
