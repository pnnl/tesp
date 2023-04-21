import os, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d
import h5py
import json
import seaborn as sns
from datetime import datetime, timedelta
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

###############################################################################
############################  GridLABD Metrics ################################
###############################################################################
def get_gridlabd_outputs(case, day_num):
    
    ###### Getting Outputs from GridLAB-D Metric #####
    
    gld_substation_file = open(case + "Substation/Substation_metrics_substation.json").read()
    gld_substation_data = json.loads(gld_substation_file)  
    
    start_second = (day_num-1)*86400
    end_second =   (day_num)*86400 -300
    interval = 288
    
    #time_gld= np.linspace(300, 86400, 288)
    time_gld= np.linspace(start_second,end_second, interval)
    
    substation_load = np.zeros(len(time_gld))
    substation_loss = np.zeros(len(time_gld))

    gld_all_meter_file = open(case + "Substation/Substation_metrics_billing_meter.json").read()
    gld_all_meter = json.loads(gld_all_meter_file) 
    
    gld_all_house_file = open(case + "Substation/Substation_metrics_house.json").read()
    gld_all_house = json.loads(gld_all_house_file) 
   
    substation_load = np.zeros(len(time_gld))
    substation_loss = np.zeros(len(time_gld))
    meter_loads = {}
    meter_loads['n57']  =  np.zeros(len(time_gld))
    meter_loads['n67']  =  np.zeros(len(time_gld))
    meter_loads['n97']  =  np.zeros(len(time_gld))
    meter_loads['n135'] =  np.zeros(len(time_gld))
    i = 0 
    for time in time_gld:
        substation_load[i] = gld_substation_data[str(int(time))]['network_node'][2]/(1000)
        substation_loss[i] = gld_substation_data[str(int(time))]['network_node'][12]/(1000 * math.sqrt(3))  
        meter_loads['n57'][i] = gld_all_meter[str(int(time))]['n57'][2]/1000
        meter_loads['n67'][i] = gld_all_meter[str(int(time))]['n67'][2]/1000
        meter_loads['n97'][i] = gld_all_meter[str(int(time))]['n97'][2]/1000
        meter_loads['n135'][i] = gld_all_meter[str(int(time))]['n135'][2]/1000
        i = i+1
         
   
    No_Microgrids = 0
    for root, dirs, files in os.walk(case):
        for file in dirs:
            if "Microgrid" in file:
                No_Microgrids += 1
    
    net_meter_load = {}
    net_hvac_load = {}
    net_wh_load = {}
    no_of_meters = {}
    
    for mg in range(No_Microgrids):
        MG_num = str(mg+1)
        net_meter_load[str(agent_prefix)+MG_num] = np.zeros((len(time_gld)))
        net_hvac_load[str(agent_prefix)+MG_num] = np.zeros((len(time_gld)))
        net_wh_load[str(agent_prefix)+MG_num] = np.zeros((len(time_gld)))
        
        billing_meter_MG_file = open(case + agent_prefix+ MG_num + "//" + agent_prefix+ MG_num + "_glm_dict.json").read()
        billing_meter_MG = json.loads(billing_meter_MG_file)['billingmeters']
        no_of_meters[str(agent_prefix)+MG_num] = len(billing_meter_MG)
        
        i = 0
        for time in time_gld:
            meter_load = 0 
            hvac_load = 0
            wh_load = 0
            for mtr_name in gld_all_meter[str(int(time))]:
                if mtr_name in billing_meter_MG.keys():
                    meter_load += gld_all_meter[str(int(time))][mtr_name][2]/1000
                    house_name = billing_meter_MG[mtr_name]['children'][0]
                    hvac_load += gld_all_house[str(int(time))][house_name][5]
                    wh_load += gld_all_house[str(int(time))][house_name][14]
                    
            net_meter_load[str(agent_prefix)+MG_num][i] = meter_load
            net_hvac_load[str(agent_prefix)+MG_num][i] = hvac_load
            net_wh_load[str(agent_prefix)+MG_num][i] = wh_load
            
            i = i+1 
        
    
    total_load = np.zeros(len(time_gld))
    for i in range(len(time_gld)):
        for mg in range(No_Microgrids):
            MG_num = str(mg+1)
            total_load[i] += net_meter_load[str(agent_prefix)+MG_num][i] 

    return time_gld, net_meter_load, net_hvac_load, net_wh_load,  total_load, substation_load, substation_loss, no_of_meters, No_Microgrids, meter_loads

###############################################################################
##################  DSO object 300 min Metrics ################################
###############################################################################
def dso_DSO_price_qunatity_rt(data_path, folder_prefix, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Args:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, day_num)
    stop_time = date + timedelta(days=1)
    os.chdir(data_path + folder_prefix + "/")
    filename = 'dso_market_Substation_300_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
    return data_df


###############################################################################
##################  MG object 300 min retail Metrics ##########################
###############################################################################
def retail_MG_price_qunatity_rt(data_path, folder_prefix, MG_num, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Args:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, day_num)
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)
    os.chdir(data_path + agent_prefix + MG_num + "/")
    filename = 'retail_market_Microgrid_' + MG_num + '_300_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
    #data_df1 = pd.read_hdf(filename, key='/metrics_df1', mode='r', where='index>=date and index<=stop_time')
    return data_df #data_df1

###############################################################################
####################  MG object 3600 min DSO Metrics ##########################
###############################################################################
    
def dso_MG_price_qunatity_da(data_path, folder_prefix, MG_num, day_num):
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
    filename = 'dso_market_Microgrid_' + MG_num + '_3600_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    data_df = pd.read_hdf(filename, key='/metrics_df2', mode='r', where='index>=date and index<=stop_time')
    data_df1 = pd.read_hdf(filename, key='/metrics_df1', mode='r', where='index>=date and index<=stop_time')
    #data_df = data_df.loc[data_df['j']==0]
    data_df1 = data_df1.loc[data_df1['i']==0]   ## cleared value every hour

    return data_df, data_df1

###############################################################################
####################  MG object 300 min DSO Metrics ##########################
###############################################################################
def dso_MG_price_qunatity_rt(data_path, folder_prefix, MG_num, day_num):
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
    filename = 'dso_market_Microgrid_' + MG_num + '_300_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    data_df = pd.read_hdf(filename, key='/metrics_df1', mode='r', where='index>=date and index<=stop_time')
    data_df1 = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')

    return data_df, data_df1

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
    print(list(store.keys()))
    # bid_time = date - timedelta(hours=14)  # + timedelta(seconds=1)
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
    data_df2 = pd.read_hdf(filename, key='/metrics_df2', mode='r', where='index>=date and index<=stop_time')
    water_heater_Energy_GLD = data_df.groupby(data_df.index)['Energy_GLD'].sum().reset_index()
    Waterdraw_gld = data_df.groupby(data_df.uid)['Waterdraw_gld'].sum().reset_index()
    return water_heater_Energy_GLD



if __name__ == '__main__':

    #pd.set_option('display.max_columns', 50)
    
    gridlabd_plot = True
    Transactive_market_plot = True
    plot_sample_bid = False
    
    #  ------------ Select folder locations for different cases ---------
    # base_case = os.getcwd() + '\\TMG_IEEE-123\\'
    # base_case = os.getcwd() + '\\TMG_TE_Base_15_debug_base\\'
    # transactive_case = os.getcwd() + '\\TMG_TE_Base_15_debug\\'
    
    # base_case = os.getcwd() + '\\TMG_TE_Base_150_debug_base\\'
    # transactive_case = os.getcwd() + '\\TMG_TE_Base_150_debug_80\\'
    # transactive_case = os.getcwd() + '\\TMG_TE_Base_150_debug\\'
    

    base_case = os.getcwd() + '/TMG_IEEE-123_Base_flex_0/'
    transactive_case = os.getcwd() + '/TMG_IEEE-123_TMG_flex_50/'

    
    # ------------ Selection of DSO and Day  ---------------------------------
    day_num = '4'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    agent_prefix = 'Microgrid_'
 
    # Check if there is a plots folder - create if not.
    plot_path = os.getcwd() + '/plots'
    check_folder = os.path.isdir(plot_path)
    if not check_folder:
        os.makedirs(plot_path)
    
    case_name = plot_path + '/'+ base_case.split('/')[-2].split('_')[1] + '_compare'
    
    date_start = get_date(transactive_case, day_num, str(day_num))
    gld_date = pd.date_range(date_start, date_start+timedelta(days=1)-timedelta(seconds=300), 288)
    
    
    ###############   Getting Data from GridLAB-D metric collector ##################
        
    [time_gld_base, net_meter_load_base, net_hvac_load_base, net_wh_load_base, total_load_base, substation_load_base, substation_loss_base, no_of_meters_base, No_MGs_base, meter_loads_base] = get_gridlabd_outputs(base_case, int(day_num))
    Data_DSO_base = dso_DSO_price_qunatity_rt(base_case, "DSO", day_num)
    
    [time_gld_trans, net_meter_load_trans, net_hvac_load_trans, net_wh_load_trans, total_load_trans, substation_load_trans, substation_loss_trans, no_of_meters_trans, No_MGs_trans, meter_loads_trans] = get_gridlabd_outputs(transactive_case, int(day_num))
    Data_DSO_trans = dso_DSO_price_qunatity_rt(transactive_case, "DSO", day_num)
    
    if gridlabd_plot:
        fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 160)
        ax.plot(gld_date, substation_load_base, label='Substation-Base')
        ax.plot(gld_date, substation_load_trans, label='Substation-TMG')
        ax.plot(gld_date, meter_loads_base['n57'], label='l60-Base')
        ax.plot(gld_date, meter_loads_trans['n57'], label='l60-TMG')
        ax.legend(loc='upper left')
        ax.set_xlabel('Time', size=12)
        ax.set_ylabel('Entity\'s Net Consumption (kW)', size=12)
        plt.grid(True)
        #plt.show()
        fig.tight_layout()
        fig.savefig(case_name+'Substation.png', dpi=fig.dpi)
        
        fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 160)
        for MG in range(3):
          MG_num = str(MG+1) 
          ax.plot(gld_date, net_meter_load_base[str(agent_prefix)+MG_num], label=str(agent_prefix)+ MG_num + '-Base')
          ax.plot(gld_date, net_meter_load_trans[str(agent_prefix)+MG_num], label=str(agent_prefix)+ MG_num + '-TMG')  
        
        # ax.plot(gld_date, meter_loads_base['n67'], label='n67-Base')
        # ax.plot(gld_date, meter_loads_base['n97'], label='n97-Base')
        # ax.plot(gld_date, meter_loads_base['n135'], label='n135-Base')
        # ax.plot(gld_date, meter_loads_trans['n67'], label='n67-TMG')
        # ax.plot(gld_date, meter_loads_trans['n97'], label='n97-TMG')
        # ax.plot(gld_date, meter_loads_trans['n135'], label='n135-TMG')
        ax.legend(loc='upper left')
        ax.set_xlabel('Time', size=12)
        ax.set_ylabel('Entity\'s Net Consumption (kW)', size=12)
        plt.grid(True)
        #plt.show()
        fig.tight_layout()
        fig.savefig(case_name+'Microgrid.png', dpi=fig.dpi)
    
    fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 160)
    ax.plot(Data_DSO_base.index, Data_DSO_base['cleared_quantity_rt'], label='DSO')
    ax.plot(Data_DSO_base.index, Data_DSO_base['cleared_quantity_rt_DG_1'], label='DG1-Base')
    ax.plot(Data_DSO_base.index, Data_DSO_base['cleared_quantity_rt_DG_2'], label='DG2-Base')
    ax.plot(Data_DSO_base.index, Data_DSO_base['cleared_quantity_rt_DG_3'], label='DG3-Base')
    ax.plot(Data_DSO_base.index, Data_DSO_base['cleared_quantity_rt_DG_4'], label='DG4-Base')
   
    ax.plot(Data_DSO_trans.index, Data_DSO_trans['cleared_quantity_rt'], label='DSO')
    ax.plot(Data_DSO_trans.index, Data_DSO_trans['cleared_quantity_rt_DG_1'], label='DG1-TMG')
    ax.plot(Data_DSO_trans.index, Data_DSO_trans['cleared_quantity_rt_DG_2'], label='DG2-TMG')
    ax.plot(Data_DSO_trans.index, Data_DSO_trans['cleared_quantity_rt_DG_3'], label='DG3-TMG')
    ax.plot(Data_DSO_trans.index, Data_DSO_trans['cleared_quantity_rt_DG_4'], label='DG4-TMG')
    ax.legend(loc='upper left')
    ax.set_xlabel('Time', size=12)
    ax.set_ylabel('Cleared Quantity (Consensus)', size=12)
    plt.grid(True)
    #plt.show()
    fig.tight_layout()
    fig.savefig(case_name+'Cleared_Quantity.png', dpi=fig.dpi)
   
    MG_num = str(1)
    dso_market_da_df_base, dso_market_da_df1_base = dso_MG_price_qunatity_da(base_case, agent_prefix, MG_num, day_num)
    retail_market_rt_df_base = retail_MG_price_qunatity_rt(base_case, agent_prefix, MG_num, day_num)  
    
    dso_market_da_df_trans, dso_market_da_df1_trans = dso_MG_price_qunatity_da(transactive_case, agent_prefix, MG_num, day_num)
    retail_market_rt_df_trans = retail_MG_price_qunatity_rt(transactive_case, agent_prefix, MG_num, day_num)
    
    
    fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 160)
    ax.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.cleared_price_rt, label='cleared_price_rt-Base')
    ax.plot(dso_market_da_df1_base.index, dso_market_da_df1_base.trial_cleared_price_da, label='Cleared_price_DA-Base')
    ax.plot(retail_market_rt_df_trans.index, retail_market_rt_df_trans.cleared_price_rt, label='cleared_price_rt-TMG')
    ax.plot(dso_market_da_df1_trans.index, dso_market_da_df1_trans.trial_cleared_price_da, label='Cleared_price_DA-TMG')
    plt.title('Cleared Price DA at 0th hour and RT ')
    plt.grid(True)
    ax.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig(case_name+'Cleared_Price.png', dpi=fig.dpi)
    
    # total_cost_base = {}
    # total_cost_trans = {}
    # avg_cost_base = {}
    # avg_cost_trans = {}
    

    # ###########   Microgrid Dispatch Characteristics  #############
    
    # for MG in range(No_MGs):
    #     MG_num = str(MG+1) 
    
    #     if Transactive_market_plot and gridlabd_plot:
                
    #         dso_market_rt_df_base, dso_market_rt_df1_base = dso_MG_price_qunatity_rt(case_eval, agent_prefix, MG_num, day_num) 
    #         retail_market_rt_df_base = retail_MG_price_qunatity_rt(case_eval, agent_prefix, MG_num, day_num)            
    #         #[HVAC_RT_bid_quantity, HVAC_cleared_price] = hvac_quantity_price_rt(case_eval, agent_prefix, MG_num, day_num)
    #         #water_heater_Energy_GLD = water_heater_quantity_price_rt(case_eval, agent_prefix, MG_num, day_num)
                
    #         ###############  Plotting Bids ######################
    #         dso_market_da_df_base, dso_market_da_df1_base = dso_MG_price_qunatity_da(case_eval, agent_prefix, MG_num, day_num)
    #         if plot_sample_bid:
    #             hour_dso = 0
    #             date_start = date_start + timedelta(hours = 6)
    #             dso_market_da_df_base_hour = dso_market_da_df_base.loc[dso_market_da_df_base['i']==hour_dso]
    #             dso_market_da_df_base_bid = dso_market_da_df_base_hour.loc[dso_market_da_df_base_hour.index==date_start]
    #             dso_market_rt_df_base_hour = dso_market_rt_df_base.loc[dso_market_rt_df_base.index==date_start]
            
    #             fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 80)
    #             ax.plot(dso_market_rt_df_base_hour.curve_dso_rt_quantities, dso_market_rt_df_base_hour.curve_dso_rt_prices, label='Bid RT ')
    #             ax.plot(dso_market_da_df_base_bid.curve_dso_da_quantities, dso_market_da_df_base_bid.curve_dso_da_prices, label='Bid DA')
    #             ax.plot(retail_market_rt_df_base.cleared_quantity_rt.loc[retail_market_rt_df_base.index==date_start], retail_market_rt_df_base.cleared_price_rt.loc[retail_market_rt_df_base.index==date_start], 'o', label='cleared RT')
    #             ax.plot(dso_market_da_df1_base.trial_cleared_quantity_da.loc[dso_market_da_df1_base.index==date_start], dso_market_da_df1_base.trial_cleared_price_da.loc[dso_market_da_df1_base.index==date_start], 'o', label='cleared DA')
    #             plt.title('Bids at {} - DA at 0th hour and RT '. format(date_start))
    #             ax.legend(loc='upper left')
    #             plt.grid(True)
                
    #         fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 80)
    #         ax.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.cleared_price_rt, label='cleared_price_rt')
    #         ax.plot(dso_market_da_df1_base.index, dso_market_da_df1_base.trial_cleared_price_da, label='Cleared_price_DA')
    #         plt.title('Cleared Price DA at 0th hour and RT ')
    #         plt.grid(True)
    #         ax.legend(loc='upper left')
            
    #         fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 80)
    #         ax.plot(retail_market_rt_df_base.index, retail_market_rt_df_base.cleared_quantity_rt, label='cleared_quantity_rt')
    #         ax.plot(dso_market_da_df1_base.index, dso_market_da_df1_base.trial_cleared_quantity_da, label='Cleared_quantity_DA')
    #         ax.plot(gld_date, net_meter_load[str(agent_prefix)+MG_num], label='GridLAB-D meters')
    #         #ax.plot(retail_market_rt_df_base.index, substation_load, label='GridLAB-D substation_load meters')
    #         ax.legend(loc='upper left')
    #         plt.grid(True)
    #         plt.title('Microgrid_'+MG_num +  ' -> Cleared vs Actual')
            
    #         rec_interval = len(net_meter_load[str(agent_prefix)+MG_num])
    #         time_interval = 86400/rec_interval
    #         #total_cost_base[MG_num] = sum(net_meter_load[str(agent_prefix)+MG_num] * retail_market_rt_df_base.cleared_price_rt)*(time_interval/3600)
    #         #avg_cost_base[MG_num] = total_cost_base[MG_num]/no_of_meters[str(agent_prefix)+MG_num]
            
    #         #total_cost_trans[MG_num] = sum(net_meter_load_TM[str(agent_prefix)+MG_num] * retail_market_rt_df_TM.cleared_price_rt)*(time_interval/3600)
    #         #avg_cost_trans[MG_num] = total_cost_trans[MG_num]/no_of_meters_TM[str(agent_prefix)+MG_num]
            