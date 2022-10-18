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
        
        billing_meter_MG_file = open(case + agent_prefix+ MG_num + "/" + agent_prefix+ MG_num + "_glm_dict.json").read()
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
def DSO_price_qunatity_rt(data_path, folder_prefix, object_name, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, day_num)
    stop_time = date + timedelta(days=1)
    os.chdir(data_path + folder_prefix + "/")
    filename = 'dso_market_' + object_name +'_300_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
    return data_df


###############################################################################
##################  retail object 300 min retail Metrics ##########################
###############################################################################
def retail_price_qunatity_rt(data_path, folder_prefix, object_name, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, day_num)
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)
    os.chdir(data_path + folder_prefix + "/")
    filename = 'retail_market_' + object_name + '_300_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
#    data_df1 = pd.read_hdf(filename, key='/metrics_df1', mode='r', where='index>=date and index<=stop_time')
    return data_df #data_df1

###############################################################################
####################  MG object 3600 min DSO Metrics ##########################
###############################################################################
    
def dso_price_qunatity_da(data_path, folder_prefix, object_name, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, str(day_num))
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)
    os.chdir(data_path + folder_prefix + "/")
    filename = 'dso_market_' + object_name + '_3600_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    data_df = pd.read_hdf(filename, key='/metrics_df2', mode='r', where='index>=date and index<=stop_time')
    data_df1 = pd.read_hdf(filename, key='/metrics_df1', mode='r', where='index>=date and index<=stop_time')
    #data_df = data_df.loc[data_df['j']==0]
    data_df1 = data_df1.loc[data_df1['i']==0]   ## cleared value every hour

    return data_df, data_df1

# ###############################################################################
# ####################  MG object 300 min DSO Metrics ##########################
# ###############################################################################
# def dso_MG_price_qunatity_rt(data_path, folder_prefix, MG_num, day_num):
#     """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
#     datetime when the energy will be consumed.
#     Arguments:
#         dir_path (str): path of parent directory where DSO folders live
#         folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
#         dso_num (str): number of the DSO folder to be opened
#     Returns:
#         retail_da_data_df : dataframe of cleared DA retail price
#         """
#     date = get_date(data_path, 1, str(day_num))
#     stop_time = date + timedelta(days=1) - timedelta(minutes=5)
#     os.chdir(data_path + agent_prefix + MG_num + "/")
#     filename = 'dso_market_Microgrid_' + MG_num + '_300_metrics.h5'
#     store = h5py.File(filename, 'r')
#     print(list(store.keys()))
#     data_df = pd.read_hdf(filename, key='/metrics_df1', mode='r', where='index>=date and index<=stop_time')
#     data_df1 = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')

    return data_df, data_df1

def hvac_quantity_price_rt(data_path, folder_prefix, object_name, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, str(day_num))
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)

    os.chdir(data_path + folder_prefix + "/")
    filename = 'hvac_agent_' + object_name + '_300_metrics.h5'
    store = h5py.File(filename, 'r')
    print(list(store.keys()))
    # bid_time = date - timedelta(hours=14)  # + timedelta(seconds=1)
    data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
    HVAC_RT_bid_quantity = data_df.groupby(data_df.index)['RT_bid_quantity'].sum().reset_index()
    HVAC_DA_bid_quantity = data_df.groupby(data_df.index)['DA_bid_quantity'].sum().reset_index()
    HVAC_agent_RT_price = data_df.groupby(data_df.index)['agent_RT_price'].mean().reset_index()
    HVAC_cleared_price = data_df.groupby(data_df.index)['cleared_price'].max().reset_index()

    return HVAC_RT_bid_quantity, HVAC_cleared_price


def water_heater_quantity_price_rt(data_path, folder_prefix, object_name, day_num):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(data_path, 1, str(day_num))
    stop_time = date + timedelta(days=1) - timedelta(minutes=5)

    os.chdir(data_path + folder_prefix + "/")
    filename = 'water_heater_agent_' + object_name + '_300_metrics.h5'
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
    
    # transactive_case = os.getcwd() + '\\IEEE-123_TE_async_random_robust_test\\'
    
    # transactive_case = os.getcwd() + '/IEEE-123_TE_async_constant_test/'
    transactive_case = os.getcwd() + '/IEEE-123_TE_async_uniform_test_v4/'
    
    case_eval = transactive_case
    #case_eval = base_case

    # ------------ Selection of DSO and Day  ---------------------------------
    day_num = '4'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    
    agent_prefix = 'Microgrid_'
 
    
    # Check if there is a plots folder - create if not.
    plot_path = os.getcwd() + '/plots'
    check_folder = os.path.isdir(plot_path)
    if not check_folder:
        os.makedirs(plot_path)
    
    case_name = plot_path + '/'+ case_eval.split('/')[-2].split('_')[1]
    
    date_start = get_date(transactive_case, day_num, str(day_num))
    gld_date = pd.date_range(date_start, date_start+timedelta(days=1)-timedelta(seconds=300), 288)
    case_config = load_json(case_eval, 'case_config_' + '1' + '.json')
    
    ###############   Getting Data from GridLAB-D metric collector ##################
        
    [time_gld, net_meter_load, net_hvac_load, net_wh_load, total_load, substation_load, substation_loss, no_of_meters, No_MGs, meter_loads] = get_gridlabd_outputs(case_eval, int(day_num))
    
    if gridlabd_plot:
        fig, ax = plt.subplots(1,1,figsize=(16,10), dpi= 160)
        ax.plot(gld_date, substation_load, linewidth=3, label='Substation')
        #ax.plot(gld_date, substation_load- Data_DSO_base['cleared_quantity_rt_DG_1'] - Data_DSO_base['cleared_quantity_rt_DG_2'] - Data_DSO_base['cleared_quantity_rt_DG_3'], label='Substation- after Market')
        for MG in range(2):
          MG_num = str(MG+1) 
          ax.plot(gld_date, net_meter_load[str(agent_prefix)+MG_num], linewidth=3,  label=str('Microgrid')+MG_num)
        # ax.legend(loc='upper left')
        # ax.set_xlabel('Time', size=12)
        # ax.set_ylabel('Entity\'s Net Consumption (kW)', size=12)
        # plt.grid(True)
        # plt.show()

        # fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 160)
        ax.plot(gld_date, meter_loads['n57'],  linewidth=3, label='n57')
        ax.plot(gld_date, meter_loads['n67'], linewidth=3, label='n67')
        ax.plot(gld_date, meter_loads['n97'], linewidth=3, label='n97')
        ax.plot(gld_date, meter_loads['n135'], linewidth=3, label='n135')
        # ax.plot(gld_date, meter_loads['n67']+ meter_loads['n135']+meter_loads['n97'] - Data_DSO_base['cleared_quantity_rt_DG_1'] - Data_DSO_base['cleared_quantity_rt_DG_2'] - Data_DSO_base['cleared_quantity_rt_DG_3'], label='n67+n135+n97-DGs')
        ax.legend(loc='upper left')
        ax.set_xlabel('Time of the Day', fontdict=dict(size=16, weight='bold'))
        ax.set_ylabel('Entity\'s Net Consumption (kW)', fontdict=dict(size=16, weight='bold'))
        plt.grid(True)
        # plt.show()
        fig.tight_layout()
        fig.savefig(case_name+'GridLAB_D_outputs.png', dpi=fig.dpi)
        
    ###############   Getting Data from Substation and Generator metric collector ##################    
    DSO_name = case_config['SimulationConfig']['dso']['DSO']['substation']
    Data_DSO_base = DSO_price_qunatity_rt(case_eval, "DSO", DSO_name,  day_num)
    fig, ax = plt.subplots(1,1,figsize=(16,10), dpi= 160)
    ax.plot(Data_DSO_base.index, Data_DSO_base['cleared_quantity_rt'],  linewidth=3, label='DSO')
    
    Data_DSO_gen = {}
    for gen in case_config['SimulationConfig']['dso']['DSO']['generators']:
        DG_Name = case_config['SimulationConfig']['dso']['DSO']['generators'][gen]['name']
        Data_DSO_gen[gen] = {}
        Data_DSO_gen[gen] = DSO_price_qunatity_rt(case_eval, gen, gen, day_num)   
        ax.plot(Data_DSO_gen[gen].index, Data_DSO_gen[gen]['cleared_quantity_rt'],  linewidth=3, label= DG_Name)
         

    ax.legend(loc='upper left')
    ax.set_xlabel('Time of the Day', fontdict=dict(size=16, weight='bold'))
    ax.set_ylabel('Cleared Quantity (kW)',fontdict=dict(size=16, weight='bold'))
    plt.grid(True)
    # plt.show()
    fig.tight_layout()
    fig.savefig(case_name+'Cleared_Quantity.png', dpi=fig.dpi)
   
    total_cost_base = {}
    total_cost_trans = {}
    avg_cost_base = {}
    avg_cost_trans = {}
    

    ###########   Microgrid Dispatch Characteristics  #############
    Data_DSO_MG = {} 
    Data_retail_MG = {}
    
    fig1, ax1 = plt.subplots(1,1,figsize=(16,8), dpi= 160)
    fig, ax = plt.subplots(1,1,figsize=(16,8), dpi= 160)
    for gen in case_config['SimulationConfig']['dso']['DSO']['generators']:
         ax1.plot(Data_DSO_gen[gen].index, Data_DSO_gen[gen]['cleared_price_rt'],  linewidth=3, label=  gen + 'cleared_RT')
    
    
    for MG in case_config['SimulationConfig']['dso']['DSO']['microgrids']:
        
        Data_DSO_MG[MG] = {}
        Data_DSO_MG[MG] = DSO_price_qunatity_rt(case_eval, MG, MG, day_num)  
        
        Data_retail_MG[MG] = {}
        Data_retail_MG[MG] = retail_price_qunatity_rt(case_eval, MG, MG, day_num) 
        
        [HVAC_RT_bid_quantity, HVAC_cleared_price] = hvac_quantity_price_rt(case_eval, MG, MG, day_num)
        water_heater_Energy_GLD = water_heater_quantity_price_rt(case_eval, MG, MG, day_num)
                
        dso_market_da_df_base, dso_market_da_df1_base = dso_price_qunatity_da(case_eval, MG, MG, day_num)
        
        
        ###############  Plotting Bids ######################
        if plot_sample_bid:
            hour_dso = 17
            date_start_bid = date_start + timedelta(hours = 17)
            dso_market_da_df_base_hour = dso_market_da_df_base.loc[dso_market_da_df_base['i']==0]
            dso_market_da_df_base_bid = dso_market_da_df_base_hour.loc[dso_market_da_df_base_hour.index==date_start_bid]
            dso_market_rt_df_base_hour = dso_market_rt_df_base.loc[dso_market_rt_df_base.index==date_start_bid]
            
            fig, ax = plt.subplots(1,1,figsize=(16,7), dpi= 160)
            ax.plot(dso_market_rt_df_base_hour.curve_dso_rt_quantities, dso_market_rt_df_base_hour.curve_dso_rt_prices, label='Bid RT ')
            ax.plot(dso_market_da_df_base_bid.curve_dso_da_quantities, dso_market_da_df_base_bid.curve_dso_da_prices, label='Bid DA')
            ax.plot(retail_market_rt_df_base.cleared_quantity_rt.loc[retail_market_rt_df_base.index==date_start_bid], retail_market_rt_df_base.cleared_price_rt.loc[retail_market_rt_df_base.index==date_start_bid], 'o', label='cleared RT')
            ax.plot(dso_market_da_df1_base.trial_cleared_quantity_da.loc[dso_market_da_df1_base.index==date_start_bid], dso_market_da_df1_base.trial_cleared_price_da.loc[dso_market_da_df1_base.index==date_start_bid], 'o', label='cleared DA')
            plt.title('Bids at {} - DA at 0th hour and RT '. format(date_start_bid))
            ax.legend(loc='upper left')
            plt.grid(True)
                

        ax1.plot(Data_retail_MG[MG].index, Data_retail_MG[MG].cleared_price_rt, linewidth=3, label= MG +'Price_RT')
        ax1.plot(dso_market_da_df1_base.index, dso_market_da_df1_base.trial_cleared_price_da, linewidth=3, label= MG + 'Price_LA')
        #ax.plot(HVAC_cleared_price['time'], HVAC_cleared_price['cleared_price'], label='HVAC')
        plt.title('Cleared Price DA at 0th hour and RT ')
        plt.grid(True)       
            

        ax.plot(Data_retail_MG[MG].index, Data_retail_MG[MG].cleared_quantity_rt, linewidth=3, label= MG + 'cleared_RT')
        ax.plot(dso_market_da_df1_base.index, dso_market_da_df1_base.trial_cleared_quantity_da, linewidth=3, label= MG + 'cleared_DA')
        ax.plot(gld_date, net_meter_load[MG], linewidth=3, label= MG +  'GridLAB-D')
        #ax.plot(gld_date, net_hvac_load[str(agent_prefix)+MG_num], label='HVAC meters')
        #ax.plot(retail_market_rt_df_base.index, substation_load, label='GridLAB-D substation_load meters')
        plt.grid(True)
        plt.title('Microgrid_'+MG_num +  ' -> Cleared vs Actual')

            
        
        rec_interval = len(net_meter_load[str(agent_prefix)+MG_num])
        time_interval = 86400/rec_interval 
       
        #total_cost_base[MG_num] = sum(net_meter_load[str(agent_prefix)+MG_num] * retail_market_rt_df_base.cleared_price_rt)*(time_interval/3600)
        #avg_cost_base[MG_num] = total_cost_base[MG_num]/no_of_meters[str(agent_prefix)+MG_num]
        #total_cost_trans[MG_num] = sum(net_meter_load_TM[str(agent_prefix)+MG_num] * retail_market_rt_df_TM.cleared_price_rt)*(time_interval/3600)
        #avg_cost_trans[MG_num] = total_cost_trans[MG_num]/no_of_meters_TM[str(agent_prefix)+MG_num]
            
    ax.grid(True)  
    ax.legend(loc='upper left')  
    fig.tight_layout()
    fig.savefig(case_name + MG + '.png', dpi=fig.dpi)
  
    ax1.grid(True)  
    ax1.legend(loc='upper left')
    fig1.tight_layout()
    fig1.savefig(case_name+'Cleared_Price.png', dpi=fig.dpi)         
           