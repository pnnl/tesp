import os
import pandas as pd
import numpy as np
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt
import h5py
import json
import seaborn as sns
from datetime import datetime, date, timedelta
import math


def load_json(dir_path, file_name):
    """Utility to open Json files."""
    with open(os.path.join(dir_path, file_name)) as json_file:
        data = json.load(json_file)
    return data


def get_date(dir_path, dso, day):
    """Utility to return start time (datetime format) of simulation day (str) in question"""
    # Determine first day of simulation and the date of the day requested
    dso = '1'
    case_config = load_json(dir_path, 'case_config_' + dso + '.json')
    sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')
    date = sim_start + timedelta(days=int(day) - 1)
    return date


def retail_price_qunatity_rt(data_path, folder_prefix, MG_num, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Args:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, str(day_num))
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)
    os.chdir(data_path + agent_prefix + MG_num + "/")
    filename = 'retail_market_Microgrid_' + MG_num + '_300_metrics.h5'
    store = h5py.File(filename, 'r')
    list(store.keys())
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')

    return data_df


def DSO_price_qunatity_rt(data_path, folder_prefix, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Args:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, str(day_num))
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)
    os.chdir(data_path + folder_prefix + "/")
    filename = 'dso_market_Substation_300_metrics.h5'
    store = h5py.File(filename, 'r')
    list(store.keys())
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')

    return data_df


def hvac_quantity_price_rt(data_path, folder_prefix, MG_num, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Args:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, str(day_num))
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)

    os.chdir(data_path + folder_prefix + MG_num + "/")
    filename = 'hvac_agent_Microgrid_' + MG_num + '_300_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    # bid_time = date - timedelta(hours=14)  # + timedelta(seconds=1)
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
    HVAC_RT_bid_quantity = data_df.groupby(data_df.index)['RT_bid_quantity'].sum().reset_index()
    HVAC_DA_bid_quantity = data_df.groupby(data_df.index)['DA_bid_quantity'].sum().reset_index()
    HVAC_agent_RT_price = data_df.groupby(data_df.index)['agent_RT_price'].mean().reset_index()
    HVAC_cleared_price = data_df.groupby(data_df.index)['cleared_price'].mean().reset_index()

    return HVAC_RT_bid_quantity, HVAC_cleared_price


def water_heater_quantity_price_rt(data_path, folder_prefix, MG_num, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Args:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, str(day_num))
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)

    os.chdir(data_path + folder_prefix + MG_num + "/")
    filename = 'water_heater_agent_Microgrid_' + MG_num + '_300_metrics.h5'
    store = h5py.File(filename, 'r')
    list(store.keys())
    # bid_time = date - timedelta(hours=14)  # + timedelta(seconds=1)
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
    water_heater_Energy_GLD = data_df.groupby(data_df.index)['Energy_GLD'].sum().reset_index()
    Waterdraw_gld = data_df.groupby(data_df.uid)['Waterdraw_gld'].sum().reset_index()
    return water_heater_Energy_GLD


if __name__ == '__main__':

    pd.set_option('display.max_columns', 50)
    # ------------ Selection of DSO and Day  ---------------------------------
    MG_num = '3'  # Needs to be non-zero integer
    day_num = '2'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    day_range = range(2, 3)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    dso_range = range(1, 2)  # 1 = DSO 1 (end range should be last DSO +1)

    #  ------------ Select folder locations for different cases ---------


    base_case = os.getcwd() + '/TMG_helics_3_agent_Base/'
    trans_case = os.getcwd() + '/TMG_helics_3_agent_price_maker/'
    config_path = '/home/mukh915/HELICS_plus/Transactive_MG/helics-uc-4.1-transactive-microgrids/examples/microgrid_v1/'
    agent_prefix = 'Microgrid_'
    GLD_prefix = 'Microgrid_'

    # Check if there is a plots folder - create if not.
    plot_path = trans_case + '/plots/'
    check_folder = os.path.isdir(plot_path)
    if not check_folder:
        os.makedirs(plot_path)

    Data_DSO_base = DSO_price_qunatity_rt(base_case, "DSO", day_num)
    Data_DSO_TM = DSO_price_qunatity_rt(trans_case, "DSO", day_num)

    fig1, ax2 = plt.subplots(1,1,figsize=(16,7), dpi= 80)
    ax2.plot(Data_DSO_base.index, Data_DSO_base.cleared_quantity_rt_DSO.astype('float64'), label='DSO_Dispatch', color='black', linestyle=':')
    ax2.plot(Data_DSO_TM.index, Data_DSO_TM.cleared_quantity_rt_DSO.astype('float64'), label='Community_Market', color='black', linestyle='dashdot')
    ax2.legend(loc='upper left')
    ax2.set_xlabel('Time', size=12)
    ax2.set_ylabel('Cleared Quantity (kW)', size=12)
    ax3 = ax2.twinx()
    ax3.plot(Data_DSO_base.index, Data_DSO_base.cleared_price_rt_DSO.astype('float64'), label='DSO_Dispatch', color='red', linestyle=':')
    ax3.plot(Data_DSO_TM.index, Data_DSO_TM.cleared_price_rt_DSO.astype('float64'), label='Community_Market', color='red', linestyle='dashdot')
    ax3.set_ylabel('Cleared price ($/kW)', size=12)
    ax3.legend(loc='upper right')
    plt.title('DSO')
    plt.grid(True)
    plt.savefig(plot_path + 'DSO.png', bbox_inches='tight')
    #plt.show()

    fig1, ax2 = plt.subplots(1,1,figsize=(16,7), dpi= 80)
    ax2.plot(Data_DSO_base.index, Data_DSO_base.cleared_quantity_rt_DG1.astype('float64'), label='DSO_Dispatch', color='black', linestyle=':')
    ax2.plot(Data_DSO_TM.index, Data_DSO_TM.cleared_quantity_rt_DG1.astype('float64'), label='Community_Market', color='black', linestyle='dashdot')
    ax2.legend(loc='upper left')
    ax2.set_xlabel('Time', size=12)
    ax2.set_ylabel('Cleared Quantity (kW)', size=12)
    ax3 = ax2.twinx()
    ax3.plot(Data_DSO_base.index, Data_DSO_base.cleared_price_rt_DG1.astype('float64'), label='DSO_Dispatch', color='red', linestyle=':')
    ax3.plot(Data_DSO_TM.index, Data_DSO_TM.cleared_price_rt_DG1.astype('float64'), label='Community_Market', color='red', linestyle='dashdot')
    ax3.set_ylabel('Cleared price ($/kW)', size=12)
    ax3.legend(loc='upper right')
    plt.title('DG1')
    plt.grid(True)
    plt.savefig(plot_path + 'DG1.png', bbox_inches='tight')
    #plt.show()

    fig1, ax2 = plt.subplots(1,1,figsize=(16,7), dpi= 80)
    ax2.plot(Data_DSO_base.index, Data_DSO_base.cleared_quantity_rt_DG2.astype('float64'), label='DSO_Dispatch', color='black', linestyle=':')
    ax2.plot(Data_DSO_TM.index, Data_DSO_TM.cleared_quantity_rt_DG2.astype('float64'), label='Community_Market', color='black', linestyle='dashdot')
    ax2.legend(loc='upper left')
    ax2.set_xlabel('Time', size=12)
    ax2.set_ylabel('Cleared Quantity (kW)', size=12)
    ax3 = ax2.twinx()
    ax3.plot(Data_DSO_base.index, Data_DSO_base.cleared_price_rt_DG2.astype('float64'), label='DSO_Dispatch', color='red', linestyle=':')
    ax3.plot(Data_DSO_TM.index, Data_DSO_TM.cleared_price_rt_DG2.astype('float64'), label='Community_Market', color='red', linestyle='dashdot')
    ax3.set_ylabel('Cleared price ($/kW)', size=12)
    ax3.legend(loc='upper right')
    plt.title('DG2')
    plt.grid(True)
    plt.savefig(plot_path + 'DG2.png', bbox_inches='tight')
    #plt.show()


    for i in range(3):
        MG_num = str(i+1)

        retail_market_rt_df_base = retail_price_qunatity_rt(base_case, agent_prefix, MG_num, day_num)
        [HVAC_RT_bid_quantity, HVAC_cleared_price] = hvac_quantity_price_rt(base_case, agent_prefix, MG_num, day_num)
        water_heater_Energy_GLD = water_heater_quantity_price_rt(base_case, agent_prefix, MG_num, day_num)

        billing_meter_MG_file_base = open(base_case + agent_prefix + MG_num + "//" + agent_prefix + MG_num + "_glm_dict.json").read()
        billing_meter_MG_base = json.loads(billing_meter_MG_file_base)['billingmeters']

        gld_Substation_file_base = open(base_case + "Substation/Substation_metrics_substation.json").read()
        gld_Substation = json.loads(gld_Substation_file_base)

        gld_all_meter_file_base = open(base_case + "Substation/Substation_metrics_billing_meter.json").read()
        gld_all_meter_base = json.loads(gld_all_meter_file_base)
        time_gld = np.linspace(86400, 172800 - 900, 96)

        net_meter_load_base = np.zeros((96))
        i = 0
        for time in time_gld:
            meter_load = 0
            for mtr_name in gld_all_meter_base[str(int(time))]:
                if mtr_name in billing_meter_MG_base.keys():
                    meter_load += gld_all_meter_base[str(int(time))][mtr_name][2] / 1000
            net_meter_load_base[i] = meter_load
            i = i + 1
        retail_market_rt_df_base['gld_meter'] = net_meter_load_base


        retail_market_rt_df_TM = retail_price_qunatity_rt(trans_case, agent_prefix, MG_num, day_num)
        [HVAC_RT_bid_quantity, HVAC_cleared_price] = hvac_quantity_price_rt(trans_case, agent_prefix, MG_num, day_num)
        water_heater_Energy_GLD = water_heater_quantity_price_rt(trans_case, agent_prefix, MG_num, day_num)

        billing_meter_MG_file_TM = open(trans_case + agent_prefix + MG_num + "//" + agent_prefix + MG_num + "_glm_dict.json").read()
        billing_meter_MG_TM = json.loads(billing_meter_MG_file_TM)['billingmeters']

        gld_all_meter_file_TM = open(trans_case + "Substation/Substation_metrics_billing_meter.json").read()
        gld_all_meter_TM = json.loads(gld_all_meter_file_TM)
        time_gld = np.linspace(86400, 172800 - 900, 96)

        net_meter_load_TM = np.zeros((96))
        i = 0
        for time in time_gld:
            meter_load = 0
            for mtr_name in gld_all_meter_TM[str(int(time))]:
                if mtr_name in billing_meter_MG_TM.keys():
                    meter_load += gld_all_meter_TM[str(int(time))][mtr_name][2] / 1000
            net_meter_load_TM[i] = meter_load
            i = i + 1
        retail_market_rt_df_TM['gld_meter'] = net_meter_load_TM


        # fig, ax = plt.subplots(1, 1, figsize=(16, 7), dpi=80)
        # ax.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.gld_meter, label='DSO_Dispatch', color='black', linestyle=':')
        # ax.plot(retail_market_rt_df_TM.index, retail_market_rt_df_TM.gld_meter, label='Community_Market', color='green', linestyle=':')
        # ax.legend(loc='upper left')
        # ax.set_xlabel('Time', size=12)
        # ax.set_ylabel('Cleared Quantity (kW)', size=12)
        # ax1 = ax.twinx()
        # ax1.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.cleared_price_rt, label='DSO_Dispatch', color='red',linestyle=':')
        # ax1.plot(retail_market_rt_df_TM.index, retail_market_rt_df_TM.cleared_price_rt, label='Community_Market',  color='red', linestyle=':')
        # ax1.set_ylabel('Cleared price ($/kW)', size=12)
        # ax1.legend(loc='upper right')
        # plt.title('Microgrid_' + MG_num)
        # plt.grid(True)
        # plt.savefig(plot_path + 'Microgrid_' + MG_num +'.png', bbox_inches='tight')

        fig, ax = plt.subplots(1, 1, figsize=(16, 7), dpi=80)
        ax.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.cleared_quantity_rt, label='cleared_quantity_rt',  color='black', linestyle=':')
        ax.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.gld_meter, label='cleared_quantity_rt', color='green',  linestyle=':')
        ax.legend(loc='upper left')
        ax.set_xlabel('Time', size=12)
        ax.set_ylabel('Cleared Quantity (kW)', size=12)
        ax1 = ax.twinx()
        ax1.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.cleared_price_rt, label='cleared_price_rt', color='red',linestyle=':')
        ax1.set_ylabel('Cleared price ($/kW)', size=12)
        ax1.legend(loc='upper right')
        plt.title('Microgrid_' + MG_num)
        plt.grid(True)
        plt.show()

        fig1, ax2 = plt.subplots(1, 1, figsize=(16, 7), dpi=80)
        ax2.plot(Data_DSO_base.index, Data_DSO_base.cleared_quantity_rt_DSO.astype('float64'), label='cleared_quantity_rt',  color='black', linestyle=':')
        ax2.plot(Data_DSO_base.index, Data_DSO_base.cleared_quantity_rt_DG1.astype('float64'), label='cleared_quantity_rt',   color='black', linestyle=':')
        ax2.legend(loc='upper left')
        ax2.set_xlabel('Time', size=12)
        ax2.set_ylabel('Cleared Quantity (kW)', size=12)
        ax3 = ax2.twinx()
        ax3.plot(Data_DSO_base.index, Data_DSO_base.cleared_price_rt_DSO, label='cleared_price_rt', color='red', linestyle=':')
        ax3.set_ylabel('Cleared price ($/kW)', size=12)
        ax3.legend(loc='upper right')
        plt.title('DSO')


