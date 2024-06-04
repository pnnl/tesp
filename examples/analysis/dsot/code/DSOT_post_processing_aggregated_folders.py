import os, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as md
from mpl_toolkits import mplot3d
import h5py
import json
import seaborn as sns
from datetime import datetime, timedelta
import math
import plotly.graph_objects as go
import plotly
import warnings
from warnings import simplefilter
import plotly.express as px
from matplotlib.ticker import PercentFormatter
import itertools
# import json


cache_output = {}
cache_df = {}


def get_date(dir_path, dso, day):
    """Utility to return start time (datetime format) of simulation day (str) in question"""
    # Determine first day of simulation and the date of the day requested
    case_config = load_json(dir_path, 'case_config_' + dso + '.json')
    sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')
    date = sim_start + timedelta(days=int(day) - 1)
    return date


def load_json(dir_path, file_name):
    """Utility to open Json files."""
    name = os.path.join(dir_path, file_name)
    try:
        cache = cache_output[name]
        return cache
    except:
        with open(name) as json_file:
            cache_output[name] = json.load(json_file)
    return cache_output[name]

def load_ercot_data(metadata_file, sim_start, day_range, outage=True):
    """Utility to open AMES csv file.
    Arguments:
        dir_path (str): path of directory where the case config files lives
        sim_start (datetime): start time of the simulation (from generate_case_config.json)
        day_range (range): range of simulation days for data to be returned
    Returns:
        data_df: dataframe of ERCOT 2016 fuel mix data
        """

    # name = os.path.join(metadata_file + '/2016_ERCOT_5min_Load_Data_Revised.csv')
    if not outage:
        metadata_file =  metadata_file.split('.csv')[0] + '_No_Outage.csv'
        
    try:
        data_df = cache_df[metadata_file]
    except:
        # Load Industrial load profiles data
        data_df = pd.read_csv(metadata_file, index_col='Seconds')
        cache_df[metadata_file] = data_df

    year_start = datetime(2021, 1, 1, 0)
    counter = year_start
    time_series = []
    for i in range(len(data_df)):
        time_series.append(counter)
        counter += timedelta(seconds=300)
    data_df.index = time_series
    data_df['datetime'] = time_series

    start_time = sim_start + timedelta(days=day_range[0] - 1)
    stop_time = start_time + timedelta(days=(day_range[-1] - (day_range[0] - 1))) - timedelta(minutes=5)
    data_df = data_df.loc[start_time:stop_time, :]
    return data_df

def load_indust_data(indust_file, day_range):
    """Utility to open industrial load csv file.
    Arguments:
        indust_file (str): path and filename where the industrial csv load lives
        day_range (range): range of simulation days for data to be returned
    Returns:
        data_df: dataframe of industrial loads per DSO bus
        """

    try:
        indust_df = cache_df[indust_file]
    except:
        # Load Industrial load profiles data
        indust_df = pd.read_csv(indust_file, index_col='seconds')
        cache_df[indust_file] = indust_df

    start_time = (day_range[0] - 1) * 300 * 288
    end_time = start_time + (day_range[-1] - day_range[0] + 1) * 300 * 288 -1

    # Updated to create dataframe even from source data that only has a few constant timesteps.
    index = np.array(range(start_time, end_time, 300))
    cols = indust_df.columns
    data = np.array([indust_df.loc[0,:].to_list()]*len(index))

    indust_loads_df = pd.DataFrame(data=data,
                            index=index,
                            columns=indust_df.columns)

    return indust_loads_df


def der_load_stack(dso, day_range, case, gld_prefix, metadata_path):
    """  For a specified dso and day range this function will load in the required data, process the data for the stacked
    DER loads and save the data to file.
    Arguments:
        dso (int): the DSO that the data should be plotted for (e.g. '1')
        day_range (range): the day range to plotted.
        case (str): folder extension of case of interest
        gld_prefix (str): folder extension for GridLab-D data
        metadata_path (str): path of folder containing metadata
    Returns:
        saves dso DER loads data to file
        """

    #     config_path = os.getcwd()
    # case_config = load_json(case, '..\system_case_config.json')
    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, day_range)

    if case_config['caseType']['batteryCase'] == 1:
        battery_case = True
    else:
        battery_case = False
    if case_config['caseType']['flexLoadCase'] == 1:
        flexload_case = True
    else:
        flexload_case = False
    if case_config['caseType']['pvCase'] == 1:
        pv_case = True
    else:
        pv_case = False

    # Load DSO MetaData
    DSOmetadata = load_json(metadata_path, case_config['dsoPopulationFile'])

    # Create Dataframe to collect and store all data reduced in this process
    dso_list = ['dso' + str(dso)]
    variables = ['Substation', 'Industrial Loads', 'Plug Loads',
     'HVAC Loads', 'WH Loads', 'Battery', 'EV', 'PV']
    der_index = pd.MultiIndex.from_product([ercot_df.index.to_list(), dso_list], names=['time', 'dso'])
    data = np.zeros((len(ercot_df.index.to_list() * len(dso_list)), len(variables)))
    der_loads_df = pd.DataFrame(data,
                                 index=der_index,
                                 columns=variables)

    industrial_file = os.path.join(metadata_path, case_config['indLoad'][5].split('/')[-1])
    indust_df = load_indust_data(industrial_file, day_range)
    indust_df = indust_df.set_index(ercot_df.index)

    # Calculate expected scaling factor
    scale_target = DSOmetadata['DSO_' + str(dso)]['scaling_factor']

    der_loads_df.loc[(slice(None), 'dso' + str(dso)), 'Industrial Loads'] = indust_df['Bus' + str(dso)].values

    for day in day_range:
        start_time = sim_start + timedelta(days=day - 1)
        stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
        ercot_load = ercot_df.loc[start_time:stop_time, ['Bus' + str(dso)]] / scale_target * 1e6

        print(f"processing residential load data for day {day} in range {day_range}")
        print(f"start_time {start_time} stop_time {stop_time}")

        meta_df, house_df = load_system_data(case, gld_prefix, str(dso), str(day), 'house')
        house_df = house_df.groupby('time').sum()
        house_df = house_df.set_index(ercot_load.index)
        der_loads_df.loc[(slice(house_df.index[0], house_df.index[-1]), 'dso' + str(dso)), 'Plug Loads'] = \
            (house_df['total_load_avg'].values - house_df['hvac_load_avg'].values -
             house_df['waterheater_load_avg'].values) * scale_target / 1e3

        der_loads_df.loc[(slice(house_df.index[0], house_df.index[-1]), 'dso' + str(dso)), 'HVAC Loads'] = \
                house_df['hvac_load_avg'].values * scale_target / 1e3

        der_loads_df.loc[(slice(house_df.index[0], house_df.index[-1]), 'dso' + str(dso)), 'WH Loads'] = \
                house_df['waterheater_load_avg'].values * scale_target / 1e3

        if battery_case:
            meta_df, battery_df = load_system_data(case, gld_prefix, str(dso), str(day), 'inverter')
            battery_df = battery_df[battery_df['name'].str.contains('ibat')]
            battery_df = battery_df.groupby('time').sum()
            battery_df = battery_df.set_index(ercot_load.index)
            der_loads_df.loc[(slice(battery_df.index[0], battery_df.index[-1]), 'dso' + str(dso)), 'Battery'] = \
                battery_df['real_power_avg'].values * scale_target / 1e6
        if pv_case:
            meta_df, inverter_df = load_system_data(case, gld_prefix, str(dso), str(day), 'inverter')
            inverter_df = inverter_df[inverter_df['name'].str.contains('isol')]
            inverter_df = inverter_df.groupby('time').sum()
            inverter_df = inverter_df.set_index(ercot_load.index)
            der_loads_df.loc[(slice(inverter_df.index[0], inverter_df.index[-1]), 'dso' + str(dso)), 'PV'] = \
                inverter_df['real_power_avg'].values * scale_target / 1e6

            meta_df, ev_df = load_system_data(case, gld_prefix, str(dso), str(day), 'evchargerdet')
            ev_df = ev_df.groupby('time').sum()
            ev_df = ev_df.set_index(ercot_load.index)
            der_loads_df.loc[(slice(ev_df.index[0], ev_df.index[-1]), 'dso' + str(dso)), 'EV'] = \
                ev_df['charge_rate_avg'].values * scale_target / 1e6

            # EV power appears to show up in home total load (unlike PV) so needs to be removed to find correct plug load.
            der_loads_df.loc[(slice(house_df.index[0], house_df.index[-1]), 'dso' + str(dso)), 'Plug Loads'] -= \
                der_loads_df.loc[(slice(ev_df.index[0], ev_df.index[-1]), 'dso' + str(dso)), 'EV']

        # Load in substation curve
        substation_meta_df, substation_df = load_system_data(case, gld_prefix, str(dso), str(day),
                                                             'substation')
        substation_df = substation_df.set_index(ercot_load.index)
        der_loads_df.loc[(slice(substation_df.index[0], substation_df.index[-1]), 'dso' + str(dso)), 'Substation'] = \
            substation_df['real_power_avg'].values * scale_target / 1e6

    der_loads_df.to_hdf(case + gld_prefix + str(dso) + '/DER_profiles.h5', key='DER_Profiles')
    der_loads_df.to_csv(path_or_buf=case + gld_prefix + str(dso) + '/DERstack_data.csv')
    
    
def load_system_data(dir_path, folder_prefix, dso_num, day_num, system_name):
    """Utility to open GLD created h5 files for systems' data.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        system_name (str): name of system data to load (e.g. 'house', 'substation', 'inverter' etc)
    Returns:
        system_meta_df : dataframe of system metadata
        system_df: dataframe of system timeseries data
        """
    daily_index=True
    os.chdir(dir_path + folder_prefix + dso_num)
    # print(f"loading the substation h5 file from --> {dir_path + folder_prefix + dso_num}")
    hdf5filenames = [f for f in os.listdir('.') if f.endswith('.h5') and system_name in f]
    filename = hdf5filenames[0]
    # reading data as pandas dataframe
    store = h5py.File(filename, "r")
    list(store.keys())
    system_meta_df = pd.read_hdf(filename, key='/Metadata', mode='r')

    # # to check keys in h5 file
    # f = h5py.File(filename, 'r')
    # print([key for key in f.keys()])

    if daily_index:
        system_df = pd.read_hdf(hdf5filenames[0], key='/index' + day_num, mode='r')
    # ----- The code below was used for when there was one index with multiple days
    else:
        system_df = pd.read_hdf(hdf5filenames[0], key='/index1', mode='r')
        start_time = (int(day_num) - 1) * 300 * 288
        end_time = start_time + 300 * (288 - 1)
        system_df = system_df[system_df['time'] >= start_time]
        system_df = system_df[system_df['time'] <= end_time]
        # start = 300
        # system_df = pd.read_hdf(hdf5filenames[0], key='/index1', mode='r', columns='time', where='time=start')
        # sim_start = date
        # start_time = sim_start + timedelta(days=int(day_num) - 1)
        # stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
        # system_df['date'] = system_df['date'].apply(pd.to_datetime)
        # system_df = system_df.set_index(['date'])
        # system_df = system_df.loc[start_time:stop_time]
    return system_meta_df, system_df


def load_weather_data(dir_path, folder_prefix, dso_num, day_num, data, check):
    """Utility to open weather dat files and find day of data
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '/DSO_')
        dso_num (str): number of the DSO folder to be opened
        day_num (str): simulation day number (1 = first day of simulation)
    Returns:
        weather_df : dataframe of weather data for simulation day requested
        """
    # Find weather location (city) associated with the DSO of interest
    file_name = 'Substation_' + dso_num + '_glm_dict.json'
    metadata = load_json(dir_path + folder_prefix + dso_num, file_name)
    weather_city = metadata["climate"]["name"]
    # Load data
#    data = pd.read_csv(dir_path + '\\' + weather_city + '\\weather.dat') 
    # testing with 2021 data


    if check == True:
        data = pd.read_csv(dir_path + '/' + weather_city + '/weather.dat')
        data['datetime'] = data['datetime'].apply(pd.to_datetime)
        data = data.set_index(['datetime'])
    #     data_original = data.copy(deep=True)
    # else:
    #     data = w_data.copy(deep=True)


    # Determine first day of simulation and resulting slice to take
    #case_config = load_json(dir_path, 'case_config_' + dso_num + '.json')
    # testing with new weather data
    case_config = load_json(dir_path, 'case_config_' + dso_num + '.json')

    sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')
    start_time = sim_start + timedelta(days=int(day_num) - 1)
    stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
    weather_df = data.loc[start_time:stop_time, :]
    # if check:
    #     return weather_df, data_original
    # else:
    return weather_df, data

def Load_substation_data(dso, day_range, base_case_list, plots_folder_name, plot_load= False, plot_weather=False):
    """  For a specified dso range and case this function will analyze the ratios of Res, Comm, and Industrial.
    Arguments:
        dso_range (range): the DSO range that the data should be analyzed
        case (str): folder extension of case of interest
        dso_metadata_file (str): folder extension and file name for DSO metadata
    Returns:
        dataframe with analysis values
        saves values to file
        """
    starting_load_dataframe = 1
    starting_weather_dataframe = 1
    dsoload_df = pd.DataFrame()
    #dsoload_df = None
    weather_df = pd.DataFrame()
    list_load_data=[]

                #################### Collecting Weather Data ####################
    for day in day_range:
        if plot_weather:
            print(f"Loading weather.dat --> {base_case_list[0]}/ day = {str(day)}")
            if starting_weather_dataframe == 1:
                weather_df, w_data = load_weather_data(base_case_list[0], '/DSO_', str(dso), str(day),[],True)
            else:
                temp_weather_df, w_data = load_weather_data(base_case_list[0], '/DSO_', str(dso), str(day), w_data, False)
                weather_df = pd.concat([weather_df, temp_weather_df], axis=0)
            starting_weather_dataframe += 1

    for case in base_case_list:
        print(f"loading substation h5 file ---> {case}")
        for day in day_range:
            print(f"Loading h5 --> day = {str(day)}. PS for future: h5 can be loaded once and for other days same h5 inside python memory could be used. Fixed a similar issue for weather.dat above.")
            substation_meta_df, substation_df = load_system_data(case, '/Substation_', str(dso), str(day), 'substation')
            if starting_load_dataframe == 1:
                temp_df = pd.DataFrame()
                temp_df['Substation Actual'] = substation_df['real_power_avg'].values /1000 # .values.tolist()
                temp_df['Substation Loss'] = substation_df['real_power_losses_avg'].values /1000
                temp_df.index = [datetime.strptime(date.split(' CDT')[0], "%Y-%m-%d %H:%M:%S") for date in substation_df.date]
                dsoload_df = temp_df
                list_load_data.append(dsoload_df)
                b=1
            else:
                temp_df = pd.DataFrame()
                temp_df['Substation Actual'] = substation_df['real_power_avg'].values /1000
                temp_df['Substation Loss'] = substation_df['real_power_losses_avg'].values /1000
                temp_df.index = [datetime.strptime(date.split(' CDT')[0], "%Y-%m-%d %H:%M:%S") for date in substation_df.date]
                dsoload_df = pd.concat([dsoload_df, temp_df], axis=0)
                list_load_data.append(dsoload_df)
            starting_load_dataframe += 1
    dsoload_df_sum = dsoload_df.groupby(dsoload_df.index).sum()
    peak_substation_load = dsoload_df_sum['Substation Actual'].max()
    directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
    if not os.path.exists(directory):
        os.makedirs(directory)

    if plot_load:
        fig, ax = plt.subplots(figsize=(12,6))
        fig.suptitle('DSO ' + str(dso) + ' Net Load from substation.h5')
        ax.set_xlabel('Time of day (hours)',  size=label_font)
        ax.set_ylabel('Substation Load (kW)', size=label_font)
        ax.plot( dsoload_df_sum.index[3:], dsoload_df_sum['Substation Actual'][3:], linewidth=2, label='Substation Load')
        ax.plot( dsoload_df_sum.index[3:], dsoload_df_sum['Substation Actual'][3:]-dsoload_df_sum['Substation Loss'][3:], linewidth=2, label='Subsation Load - loss')
        # Only label every 24th value (every 2 hours)
        ticks_to_use = dsoload_df.index[::24]
        # Set format of labels (note year not excluded as requested)
        labels = [i.strftime(":%M") for i in ticks_to_use]
        # Now set the ticks and labels
        #ax1.set_xticks(ticks_to_use)
        #ax1.set_xticklabels(labels)
        plt.legend(loc='upper left', prop={'size': legend_font})
        if plot_weather:
            ax2 = ax.twinx()  # instantiate a second axes that shares the same x-axis
            color = 'tab:red'
            ax2.set_ylabel('Temperature (F)', color=color, size=label_font)  # we already handled the x-label with ax1
            ax2.plot(weather_df['temperature'], color=color, linewidth=2, linestyle=':', label='Weather')
            ax2.tick_params(axis='y', labelcolor=color)
            #ax2.set_xticks(ticks_to_use)
            #ax1.set_xticklabels(labels)
        ax.grid()
        plt.legend(loc='lower left', prop={'size': legend_font})
        ax.tick_params(axis='both', which='major', labelsize=tick_font)
        # fig.tight_layout()
        # fig.show()
        fig.savefig(
            f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_Substation_plot.pdf",
            bbox_inches='tight')
    return dsoload_df,weather_df, peak_substation_load


def Load_substation_data_mod(dso, day_range, base_case_list, plots_folder_name, weather_df, controloruncontrol, plot_load= False):
    """  For a specified dso range and case this function will analyze the ratios of Res, Comm, and Industrial.
    Arguments:
        dso_range (range): the DSO range that the data should be analyzed
        case (str): folder extension of case of interest
        dso_metadata_file (str): folder extension and file name for DSO metadata
    Returns:
        dataframe with analysis values
        saves values to file
        """
    starting_load_dataframe = 1
    starting_weather_dataframe = 1
    dsoload_df = pd.DataFrame()
    #dsoload_df = None
    # weather_df = pd.DataFrame()
    list_load_data=[]

                #################### Collecting Weather Data ####################
    # for day in day_range:
    #     if plot_weather:
    #         print(f"Loading weather.dat --> {base_case_list[0]}/ day = {str(day)}")
    #         if starting_weather_dataframe == 1:
    #             weather_df, w_data = load_weather_data(base_case_list[0], '/DSO_', str(dso), str(day),[],True)
    #         else:
    #             temp_weather_df, w_data = load_weather_data(base_case_list[0], '/DSO_', str(dso), str(day), w_data, False)
    #             weather_df = pd.concat([weather_df, temp_weather_df], axis=0)
    #         starting_weather_dataframe += 1

    for case in base_case_list:
        print(f"loading substation h5 file ---> {case}")
        for day in day_range:
            print(
                f"Loading h5 --> day = {str(day)}. PS for future: h5 can be loaded once and for other days same h5 inside python memory could be used. Fixed a similar issue for weather.dat above.")
            substation_meta_df, substation_df = load_system_data(case, '/Substation_', str(dso), str(day), 'substation')
            if starting_load_dataframe == 1:
                temp_df = pd.DataFrame()
                temp_df['Substation Actual'] = substation_df['real_power_avg'].values /1000 # .values.tolist()
                temp_df['Substation Loss'] = substation_df['real_power_losses_avg'].values /1000
                temp_df.index = [datetime.strptime(date.split(' CDT')[0], "%Y-%m-%d %H:%M:%S") for date in substation_df.date]
                dsoload_df = temp_df
                list_load_data.append(dsoload_df)
                b=1
            else:
                temp_df = pd.DataFrame()
                temp_df['Substation Actual'] = substation_df['real_power_avg'].values /1000
                temp_df['Substation Loss'] = substation_df['real_power_losses_avg'].values /1000
                temp_df.index = [datetime.strptime(date.split(' CDT')[0], "%Y-%m-%d %H:%M:%S") for date in substation_df.date]
                dsoload_df = pd.concat([dsoload_df, temp_df], axis=0)
                list_load_data.append(dsoload_df)
            starting_load_dataframe += 1
    dsoload_df_sum = dsoload_df.groupby(dsoload_df.index).sum()
    peak_substation_load = dsoload_df_sum['Substation Actual'].max()



    directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
    if not os.path.exists(directory):
        os.makedirs(directory)

    if plot_load:
        fig, ax = plt.subplots(figsize=(12,6))
        fig.suptitle('DSO ' + str(dso) + ' Net Load from substation.h5')
        ax.set_xlabel('Time of day (hours)',  size=label_font)
        ax.set_ylabel('Substation Load (kW)', size=label_font)
        ax.plot( dsoload_df_sum.index[3:], dsoload_df_sum['Substation Actual'][3:], linewidth=2, label='Substation Load')
        ax.plot( dsoload_df_sum.index[3:], dsoload_df_sum['Substation Actual'][3:]-dsoload_df_sum['Substation Loss'][3:], linewidth=2, label='Subsation Load - loss')
        # Only label every 24th value (every 2 hours)
        ticks_to_use = dsoload_df.index[::24]
        # Set format of labels (note year not excluded as requested)
        labels = [i.strftime(":%M") for i in ticks_to_use]
        # Now set the ticks and labels
        #ax1.set_xticks(ticks_to_use)
        #ax1.set_xticklabels(labels)
        plt.legend(loc='upper left', prop={'size': legend_font})
        # if plot_weather:
        ax2 = ax.twinx()  # instantiate a second axes that shares the same x-axis
        color = 'tab:red'
        ax2.set_ylabel('Temperature (F)', color=color, size=label_font)  # we already handled the x-label with ax1
        ax2.plot(weather_df['temperature'], color=color, linewidth=2, linestyle=':', label='Weather')
        ax2.tick_params(axis='y', labelcolor=color)
        #ax2.set_xticks(ticks_to_use)
        #ax1.set_xticklabels(labels)
        ax.grid()
        plt.legend(loc='lower left', prop={'size': legend_font})
        ax.tick_params(axis='both', which='major', labelsize=tick_font)
        # fig.tight_layout()
        # fig.show()
        if controloruncontrol == "uncontrol":
            fig.savefig(
                f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_Substation_uncontrol_plot.pdf",
                bbox_inches='tight')
        else:
            fig.savefig(
                f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_Substation_control_plot.pdf",
                bbox_inches='tight')
    return dsoload_df,weather_df, peak_substation_load

def get_attributes_from_metrics_data(data_base_df, objects, attrib):

    data_att_df = pd.DataFrame(columns=['Datetime']+ objects)
    
    for obj in objects:
        idx = data_base_df.index[data_base_df['name'] == obj].tolist()
        data_att_df[obj] = data_base_df[attrib][idx].values
    data_att_df['Datetime'] = pd.to_datetime(data_base_df['date'][idx].values, format='%Y-%m-%d %H:%M:%S CDT')

    return data_att_df


def sum_all_csv_Files(path):
    # in VAs
    csv_files = [f for f in os.listdir(path) if f.endswith('.csv') and 'loads_power' in f][:3]
    df_1 = pd.read_csv(os.path.join(path, csv_files[0]), skiprows=8)
    df1 = df_1.iloc[:, 1:]
    df_2 = pd.read_csv(os.path.join(path, csv_files[1]), skiprows=8)
    df2 = df_2.iloc[:, 1:]
    df_3 = pd.read_csv(os.path.join(path, csv_files[2]), skiprows=8)
    df3 = df_3.iloc[:, 1:]

    df_final_fv = pd.concat([df1, df2, df3], axis=1)
    # df_final2 = df_final.iloc[:, 1:]
    df_final_fv = df_final_fv.groupby(df_final_fv.columns, axis=1).sum()
    df_final_fv = pd.concat([df_final_fv, df_1["# timestamp"].to_frame()], axis=1)
    return df_final_fv


def transformer_map(path_to_file):
    with open(path_to_file + 'model.json', 'r') as fp:
        model = json.load(fp)

    with open(path_to_file + 'com_loads.json', 'r') as fp:
        comm_loads = json.load(fp)

    with open(path_to_file + 'xfused.json', 'r') as fp:
        xfused = json.load(fp)

    transformer_name_connected_to_load = []
    transformer_config_list_type = []
    xfrmr_size = []

    load_to_xfrmr_config_map_dict = {}
    for k in comm_loads:
        parent_meter = comm_loads[k][0]
        for trfrmr_key, trfrmr_properties in model["transformer"].items():
            f_name = trfrmr_properties["from"]
            t_name = trfrmr_properties["to"]
            config_name = trfrmr_properties["configuration"]
            if (parent_meter == f_name) or (parent_meter == t_name):
                transformer_name_connected_to_load.append(trfrmr_key)
                transformer_config_list_type.append(config_name)
                load_to_xfrmr_config_map_dict[k+'_streetlights'] = config_name
                xfrmr_size.append(xfused[config_name][1])

    load_to_xfrmr_name = dict(zip(list(comm_loads.keys()), transformer_name_connected_to_load))
    # NOTE: transformer_name_connected_to_load are only commercial trasnformer since they are found suing comemrcial
    # loads conenctivity on the glm graph!!!!! very important when extending to residential transformers.
    xfrmr_name_to_size = dict(zip(transformer_name_connected_to_load, xfrmr_size))

    transformer_power_rating = []
    config_to_power_rating_map_dict = {}
    for item in transformer_config_list_type:

        try:
            transformer_power_rating.append(xfused[item][1])
            config_to_power_rating_map_dict[item] = xfused[item][1]
        except:
            print("Unable to find desired transformer config in json, exiting...")
            exit()

        # found = False
        # for key, value in model['transformer_configuration'].items():
        #     if item == re.sub(r'^feeder\d+_', '', key):
        #         transformer_power_rating.append(value['power_rating'])
        #         found = True
        #         break
        # if not found:
        #     transformer_power_rating.append(None)
    # transformer_rating_dct = dict(zip(transformer_name_connected_to_load, transformer_power_rating))
    return load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size

def flatten(xss):
    return [x for xs in xss for x in xs]

def overload_calculation(base_case_list,GLD_prefix, plots_folder_name):
    df_final_divided = pd.DataFrame()
    ct = 0
    for path_name in base_case_list:
        ct += 1
        path = path_name+GLD_prefix+'1/'
        print(f"Calculating percent overload data at location = {path}. Current folder progress = {ct}/{len(base_case_list)}.")
        df_final = sum_all_csv_Files(path)
        # df_final = pd.concat([df_final, df_final_fv], axis=0)
        load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = transformer_map(path)

        # if len(df_final.columns) != len(transformer_rating_dct):
        #     raise ValueError("DataFrame and dictionary have different numbers of columns.")
        comm_load_names0 = list(df_final.columns)
        comm_load_names = [x for x in comm_load_names0 if x != '# timestamp']
        df_divided = pd.DataFrame(data={
            col: (df_final[col] / (config_to_power_rating_map_dict[load_to_xfrmr_config_map_dict[col]] * 1000)) * 100
            for
            col in comm_load_names})
        df_final_divided = pd.concat([df_final_divided, df_divided], axis=0)
        df_divided2 = pd.concat([df_final_divided, df_final["# timestamp"].to_frame()], axis=1)

        # df_final_fv = sum_all_csv_Files(path)
        # df_final=pd.concat([df_final, df_final_fv], axis=0)
        # load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict = transformer_map(path)
        #
        # # if len(df_final.columns) != len(transformer_rating_dct):
        # #     raise ValueError("DataFrame and dictionary have different numbers of columns.")
        # comm_load_names0 = list(df_final.columns)
        # comm_load_names = [x for x in comm_load_names0 if x != '# timestamp']
        # df_divided = pd.DataFrame(data={col: (df_final[col] / (config_to_power_rating_map_dict[load_to_xfrmr_config_map_dict[col]]*1000))*100 for col in comm_load_names})
        # df_divided2 = pd.concat([df_divided, df_final["# timestamp"].to_frame()], axis= 1)
        # df_divided2.to_csv(path + 'transformer_overloading.csv', index=False)

    # # histogram based on overloading percentage (considering all transformers overloads)
    # data_toplot = flatten(df_final_divided.values.tolist())


    # fig = go.Figure()
    # fig.add_trace(go.Histogram(x=data_toplot,  histnorm='percent', marker_color='#330C73', opacity=0.75))
    # # fig.update_traces(histnorm= "probability density", selector = dict(type='histogram'))
    # fig.update_layout(
    #     title_text='Transformer overloading - probability density',  # title of plot
    #     xaxis_title_text='Transformer loading in percentage',  # xaxis label
    #     yaxis_title_text='Percent occurrence of transformer loading on grid',  # yaxis label
    #     font_family="Courier New",
    #     font_color="blue",
    #     font_size = 18,
    #     bargap=0.2,  # gap between bars of adjacent location coordinates
    #     bargroupgap=0.1  # gap between bars of the same location coordinates
    # )
    # plotly.offline.plot(fig, filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_HistogramOverloadPercent.html")
    # # fig.write_image(f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_HistogramOverloadPercent.png")
    # # print("frequency/count/percent of transformer loading histogram image saved.")
    return df_final_divided

def plots_residential_load_weather(hse_attr,day_range,houses,base_case,base_case_list,Load_House_data,weather_df):#
    if Load_House_data: 
        house_att_df = pd.DataFrame()
        for base_case in base_case_list:
            for day in day_range:
                meta_house_df_base, data_house_df_base = load_system_data(base_case, '/Substation_', str(dso), str(day), 'house') 
                b=1
                if house_att_df.empty:
                    house_att_df = get_attributes_from_metrics_data(data_house_df_base, houses, hse_attr)
                else:
                    temp1 = get_attributes_from_metrics_data(data_house_df_base, houses, hse_attr)
                    house_att_df = pd.concat([house_att_df, temp1])               
    simplefilter(action="ignore", category=pd.errors.PerformanceWarning) 
    pd.to_datetime(house_att_df['Datetime'])
    house_att_df.set_index('Datetime', inplace=True)
    house_att_df_sum = house_att_df.groupby(house_att_df.index).sum()
    house_att_df_sum['Total Residential load'] = house_att_df_sum.sum(axis=1)
    #house_att_df_sum.reset_index(inplace=True)
    fig, ax = plt.subplots(figsize=(12,6))
    fig.suptitle('Residential Load (Substation_1_house.h5) and Temperature Plot')
    ax.set_xlabel('Time of day (hours)',  size=label_font)
    ax.set_ylabel('Load (kW)', size=label_font)
    ax.plot(house_att_df_sum.index[3:],house_att_df_sum['Total Residential load'][3:], label='Residential Load')
    plt.legend(loc='upper left', prop={'size': legend_font})
    ax2 = ax.twinx() 
    color = 'tab:red'
    ax2.set_ylabel('Temperature (F)', color=color, size=label_font)
    ax2.plot(weather_df['temperature'], color=color, linewidth=2, linestyle=':', label='Weather')
    ax.grid()
    plt.legend(loc='lower left', prop={'size': legend_font})
    fig.savefig(
        f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_residential_load_plot.pdf",
        bbox_inches='tight')
    return house_att_df_sum


def plot_commercial_load_weather(weather_df,df_final):
    df_final.set_index('# timestamp', inplace=True)
    df_final_sum = df_final.groupby(df_final.index).sum()
    df_final_sum['Total Commercial load'] = df_final_sum.sum(axis=1)/1000
    df_final_sum.reset_index(inplace=True)
    df_v1 = df_final_sum[['# timestamp','Total Commercial load']]
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "tzname")
        df_v1.iloc[:, 0] = pd.to_datetime(df_v1.iloc[:, 0]).dt.tz_localize(None)
    fig, ax = plt.subplots(figsize=(12,6))
    fig.suptitle('Commercial Load (group recorder load_A_B_C.csv summed) and Temperature Plot')
    ax.set_xlabel('Time of day (hours)',  size=label_font)
    ax.set_ylabel('Load (kVA)', size=label_font)
    ax.plot(df_v1['# timestamp'][3:],df_v1['Total Commercial load'][3:], label='Commercial Load')
    plt.legend(loc='upper left', prop={'size': legend_font})
    ax2 = ax.twinx() 
    color = 'tab:red'
    ax2.set_ylabel('Temperature (F)', color=color, size=label_font)
    ax2.plot(weather_df['temperature'], color=color, linewidth=2, linestyle=':', label='Weather')
    ax.grid()
    plt.legend(loc='lower left', prop={'size': legend_font})
    fig.savefig(
        f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_commercial_load_plot.pdf",
        bbox_inches='tight')
    return df_v1

def plot_comm_res(house_att_df_sum,df_v1,weather_df):
    df_v1.set_index('# timestamp', inplace=True) 
    df_v1_resampled = df_v1.resample('5min').mean() 
    df_v1_resampled.reset_index(inplace=True)
    df_sum = pd.DataFrame()
    df_sum['sum'] = house_att_df_sum['Total Residential load'].values+ df_v1_resampled.iloc[:-1,1].values
    df_new = pd.merge(df_v1_resampled[['# timestamp']], df_sum[['sum']], left_index=True, right_index=True)
    fig, ax = plt.subplots(figsize=(12,6))
    fig.suptitle('Total Loads (residential from house.h5 & commercial load_A_B_C summed) and Temperature Plot')
    ax.set_xlabel('Time of day (hours)',  size=label_font)
    ax.set_ylabel('Loads (kWs)', size=label_font)
    ax.plot(df_new['# timestamp'],df_new['sum'],label='Commercial & Residential Load')
    plt.legend(loc='upper left', prop={'size': legend_font})
    ax2 = ax.twinx() 
    color = 'tab:red'
    ax2.set_ylabel('Temperature (F)', color=color, size=label_font)
    ax2.plot(weather_df['temperature'], color=color, linewidth=2, linestyle=':', label='Weather')
    ax.grid()
    plt.legend(loc='lower left', prop={'size': legend_font})
    fig.savefig(
            f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_loads_res_comm_plot.pdf",
            bbox_inches='tight')
    return None
    
def substation_plot(base_case_list,GLD_prefix,weather_df):
    df_substation = pd.DataFrame()
    temp = None
    for case in base_case_list:
        if temp is None:
            temp = pd.read_csv(case+GLD_prefix+'1/'+'substation_data.csv', skiprows=8)
            #df_substation = pd.concat([df_substation,temp])
            df_substation=temp
        else:
            temp2 = pd.read_csv(case+GLD_prefix+'1/'+'substation_data.csv', skiprows=8) 
            df_substation['avg(distribution_load.mag)_total'] = df_substation['avg(distribution_load.mag)'].values +temp2['avg(distribution_load.mag)'].values
    #df_substation = pd.read_csv(path, skiprows=8)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "tzname")
        df_substation['timestamp'] = pd.to_datetime(df_substation['# property.. timestamp']).dt.tz_localize(None)
    fig, ax = plt.subplots(figsize=(12,6))
    fig.suptitle('Substation Load (from object collector) and Temperature')
    ax.set_xlabel('Time of day (hours)',  size=label_font)
    ax.set_ylabel('Substation Loads (unit?)', size=label_font)
    ax.plot(df_substation['timestamp'],df_substation['avg(distribution_load.mag)_total'],label=' Substation Load (Commercial & Residential)')
    plt.legend(loc='upper left', prop={'size': legend_font})
    ax2 = ax.twinx() 
    color = 'tab:red'
    ax2.set_ylabel('Temperature (F)', color=color, size=label_font)
    ax2.plot(weather_df['temperature'], color=color, linewidth=2, linestyle=':', label='Weather')
    ax.grid()
    plt.legend(loc='lower left', prop={'size': legend_font})
    fig.savefig(
        f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_subloads_res_comm_plot.pdf",
        bbox_inches='tight')
    return None

def work_with_uncontrolled_and_controlled_ev_load(value, xfrmr_name_to_size, flag):
    # if extrafoldersexist:
    # load the vehicle uncontrolled data and controlled data

    # uncontrolled first
    current_size = value.split("_")[2]

    # find all years for current size grid
    my_main_loc = os.getcwd()
    os.chdir(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/")
    all_files = glob.glob('./*.xlsx')
    if randomsoc == True:
        size_list = [x.split("_")[2] for x in all_files if (current_size in x) and ("randmaxsoc" in x)]
        year_list = [x.split("_")[4].split(".")[0] for x in all_files if (current_size in x) and ("randmaxsoc" in x)]
    else:
        size_list = [x.split("_")[2] for x in all_files if current_size in x]
        year_list = [x.split("_")[4].split(".")[0] for x in all_files if current_size in x]
    os.chdir(my_main_loc)
    all_year_ev_uncontrolled_laod = pd.DataFrame()
    for each_year in year_list:
        # load the current years uncontrolled EV demand
        if flag == "uncontrolled":
            uncontroll_ev_file = f"Uncontrolled_results_{custom_suffix_sim_run_uncontrolled}/uncontrolled_{current_size}_Year_{each_year}.csv"
        if flag == "controlled":
            uncontroll_ev_file = f"Controlled_results_{custom_suffix_sim_run}/controlled_ev_{zone_name}_Year_{each_year}.csv"
            fail_xfrmr_info = f"Controlled_results_{custom_suffix_sim_run}/failed_xfrmr_SCM_info.csv"
            fail_xfrmr_info_df = pd.read_csv(fail_xfrmr_info)
            # pick xfrms from current year
            current_xfrmr_fails = fail_xfrmr_info_df[(fail_xfrmr_info_df["Zone and size"]==zone_name)& (fail_xfrmr_info_df["Year"]==int(each_year))]

            # info to copy from uncontrolled ev for failed xfrmr
            required_info = f"Uncontrolled_results_{custom_suffix_sim_run_uncontrolled}/uncontrolled_{current_size}_Year_{each_year}.csv"
            required_df = pd.read_csv(required_info)


        df_current_year_uncontrolled_ev = pd.read_csv(uncontroll_ev_file)
        # load the xfrmr mapping jason
        current_year_xfrmr_map_json = f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/xfrmr_map_{current_size}_Year_{each_year}.json"

        with open(current_year_xfrmr_map_json) as fd:
            current_year_xfrmr_map = json.load(fd)
        current_year_xfrmr_map_reversed = dict((str(v), k) for k, v in current_year_xfrmr_map.items())
        if flag == "controlled":
            current_year_xfrmr_map_reversed_k = dict((v, k) for k, v in current_year_xfrmr_map.items())

        df_current_year_uncontrolled_ev = df_current_year_uncontrolled_ev.rename(
            columns=current_year_xfrmr_map_reversed)

        if flag == "controlled":
            # change their dummy names to actual names
            current_xfrmr_fails = current_xfrmr_fails.replace({"Dummy name": current_year_xfrmr_map_reversed_k})
            # assign the uncontrolled info to controlled for failed xfrmrs
            for x in list(current_xfrmr_fails["Dummy name"]):
                if x in list(df_current_year_uncontrolled_ev.columns):
                    print("failed xfrmr found in controlled even before assignment, bug if found, exiting...")
                    exit()
                else:
                    df_current_year_uncontrolled_ev[x] = list(required_df[str(current_year_xfrmr_map[x])])

        df_current_year_uncontrolled_ev["Year"] = each_year
        all_year_ev_uncontrolled_laod = pd.concat(
            [all_year_ev_uncontrolled_laod, df_current_year_uncontrolled_ev])

        k = 1
    k = 1
    # there will be nans in "all_year_ev_uncontrolled_laod", thats because some transformers did not get assigned any EVs and hence they have no EV data.
    all_year_ev_uncontrolled_laod = all_year_ev_uncontrolled_laod.fillna(0)

    all_year_ev_uncontrolled_laod_in_kw = all_year_ev_uncontrolled_laod.copy(deep=True)

    all_columns = list(all_year_ev_uncontrolled_laod.columns)

    all_columns_to_use = [x for x in all_columns if ("Year" not in x) and ("day" not in x) and ("hour" not in x)]

    # load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = transformer_map(
    #     path)

    for col_each in all_columns_to_use:
        all_year_ev_uncontrolled_laod[col_each] = (all_year_ev_uncontrolled_laod[col_each] / xfrmr_name_to_size[
            col_each])*100

    return all_year_ev_uncontrolled_laod, current_size, year_list, all_year_ev_uncontrolled_laod_in_kw

def mergebaseload_uncontrolled_controlled_ev_data(df_final_divided_hourly, all_year_ev_uncontrolled_laod, year_list):
    df_final_divided_hourly["hour"] = df_final_divided_hourly["# timestamp"].dt.hour
    month = np.unique(list(df_final_divided_hourly["# timestamp"].dt.month))[0]
    start_Day = min(list(df_final_divided_hourly["# timestamp"].dt.day))
    df_final_divided_hourly["day"] = df_final_divided_hourly["# timestamp"].dt.day - start_Day




    # df_final_divided_hourly = df_final_divided_hourly.set_index(["hour", "day", "Year"])
    # all_year_ev_uncontrolled_laod["hour_i"] = all_year_ev_uncontrolled_laod["hour"].astype(int)
    # all_year_ev_uncontrolled_laod["day_i"] = all_year_ev_uncontrolled_laod["day"].astype(int)
    # all_year_ev_uncontrolled_laod["year_i"] = all_year_ev_uncontrolled_laod["Year"].astype(int)
    # all_year_ev_uncontrolled_laod.set_index(["hour", "day", "Year"])
    # check_df = pd.concat([df_final_divided_hourly, all_year_ev_uncontrolled_laod]).groupby(["hour", "day", "Year"]).sum()

    df_final_divided_hourly = df_final_divided_hourly.set_index(["hour", "day"])
    all_year_ev_uncontrolled_laod["year_i"] = 99999
    merged_df_hourly = pd.DataFrame()
    for each_year in year_list:
        # all_year_ev_uncontrolled_laod.loc[all_year_ev_uncontrolled_laod["Year"] == each_year, "year_i"] = each_year
        current_year_uncontrolled_ev_load_df = all_year_ev_uncontrolled_laod[
            all_year_ev_uncontrolled_laod["Year"] == each_year]

        current_year_uncontrolled_ev_load_df = current_year_uncontrolled_ev_load_df.set_index(["hour", "day"])

        check_df = pd.concat([df_final_divided_hourly, current_year_uncontrolled_ev_load_df]).groupby(["hour", "day"]).sum(numeric_only=True)

        check_df = check_df.reset_index()  # bring back the hour and day columns.

        check_df["year_i"] = int(each_year)

        merged_df_hourly = pd.concat([merged_df_hourly, check_df])  # merged data when both data are in percentage format. 0-100%

    merged_df_hourly["month"] = month
    merged_df_hourly["day"] = merged_df_hourly["day"] + start_Day
    # merged_df_hourly["hour"] = merged_df_hourly["hour"].astype(str)

    merged_df_hourly['# timestamp'] = merged_df_hourly[['year_i', 'month', 'day', 'hour']].apply(lambda s: datetime(*s), axis=1)
    return merged_df_hourly

def plot_percent_hit(name_to_save, basecase_transformer_loading_flatten_data):
    # plot hits percent plot

    fig = plt.figure()
    plt.hist(basecase_transformer_loading_flatten_data,
             weights=np.ones(len(basecase_transformer_loading_flatten_data)) / len(
                 basecase_transformer_loading_flatten_data), edgecolor='black', alpha=0.7,
             color='skyblue')
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    # adding details
    plt.title("Transformer loading - histpercent", fontsize=18, fontweight='bold')
    plt.xlabel("Transformer loading in percentage", fontsize=14)
    plt.ylabel("Percent of total transformers on grid", fontsize=14)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.gca().set_facecolor('#f9f9f9')  # Adding a background color
    # add more information - for instance: highlight the mean value
    mean_value = np.mean(basecase_transformer_loading_flatten_data)
    plt.axvline(mean_value, color='red', linestyle='--', label=f"Mean ({mean_value:.2f})")
    plt.legend(fontsize=12)
    # # annotate the mean value and automaticcaly positioning it on the plot
    # plt.annotate(f"Mean: {mean_value:.2f}", xy=(mean_value, 0.02), xytext=(mean_value + 2000, 0.05),
    #              arrowprops=dict(arrowstyle='->', color='black'), fontsize=12)
    # Add a subtle shadow effect
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['bottom'].set_linewidth(0.5)
    plt.gca().spines['left'].set_linewidth(0.5)
    # Show the plot
    plt.tight_layout()
    fig.savefig(name_to_save,
        bbox_inches='tight')
    # plt.show()
    # plt.figure.clear()
    # plt.close()
    # plt.cla()
    # plt.clf()

def plot_clustered_stacked(dfall, name_to_save, labels=None, title="multiple stacked bar plot",  H="/", **kwargs):
    """Given a list of dataframes, with identical columns and index, create a clustered stacked bar plot.
labels is a list of the names of the dataframe, used for the legend
title is a string for the title of the plot
H is the hatch used for identification of the different dataframe"""

    n_df = len(dfall)
    n_col = len(dfall[0].columns)
    n_ind = len(dfall[0].index)
    axe_h = plt.subplot(111)
    axe_h.clear()

    for df in dfall : # for each data frame
        axe_h = df.plot(kind="bar",
                      linewidth=0,
                      stacked=True,
                      ax=axe_h,
                      legend=False,
                      grid=False,
                        # color=[['#FF7F0E', '#2CA02C', '#D62728']],
                        color={"Base Load": '#FF7F0E', "EV Demand": '#2CA02C'},
                      **kwargs)  # make bar plots

    h,l = axe_h.get_legend_handles_labels() # get the handles we want to modify
    for i in range(0, n_df * n_col, n_col): # len(h) = n_col * n_df
        for j, pa in enumerate(h[i:i+n_col]):
            for rect in pa.patches: # for each index
                rect.set_x(rect.get_x() + 1 / float(n_df + 1) * i / float(n_col))
                rect.set_hatch(H * int(i / n_col)) #edited part
                rect.set_width(1 / float(n_df + 1))

    axe_h.set_xticks((np.arange(0, 2 * n_ind, 2) + 1 / float(n_df + 1)) / 2.)
    axe_h.set_xticklabels(df.index, rotation = 0)
    axe_h.set_title(title)

    # Add invisible data to add another legend
    n=[]
    for i in range(n_df):
        n.append(axe_h.bar(0, 0, color="gray", hatch=H * i))

    l1 = axe_h.legend(h[:n_col], l[:n_col], loc=[1.01, 0.5])
    if labels is not None:
        l2 = plt.legend(n, labels, loc=[1.01, 0.1])
    axe_h.add_artist(l1)


    plt.xticks(rotation=45)

    # plt.show()

    plt.savefig(name_to_save,
                bbox_inches='tight')
    # # plt.show()
    # plt.figure.clear()
    # plt.close()
    # plt.cla()
    # plt.clf()

    k = 1

    return axe_h

def plot1a_task_percentoverload(input_basecase_folder_name, GLD_prefix, sets_in_all_folders, plots_folder_name, extrafoldersexist, plot_plotly, replace_threshold):
    input_basecase_without_ev = input_basecase_folder_name + '_uncontrolled'
    input_basecase_with_ev = input_basecase_folder_name + '_controlled'
    # if extrafoldersexist:
    #     folder_list = [input_basecase_folder_name, input_basecase_without_ev, input_basecase_with_ev]
    # else:
    folder_list = [input_basecase_folder_name]

    # iterate through folders (3 cases)
    max_list = []
    std_list = []
    name_list = []
    cumm_vio_counts_list = []
    xfrmr_ratings_list = []
    list_data = []
    for idx, value in enumerate(folder_list):
        print(f"Current working on following scenario = {value}. Current scenario progress = {idx+1}/{len(folder_list)}.")
        #--------------------------------------------
        # uncontrolled first

        consolidated_df_in_va = pd.DataFrame()
        cnsolidated_xfrmr_to_size_map = dict()
        for x in range(sets_in_all_folders[idx]):
            path = r'/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/' + value + f"_{x+1}_fl" + GLD_prefix + '1/'
            # load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = transformer_map(
            #     path)
            print(f"extracting base load --> {path}")
            subfolder_df_in_VA, sub_xfrmr_tosize_map = extract_demand_forecast_from_gld(path, x + 1)
            cnsolidated_xfrmr_to_size_map.update(sub_xfrmr_tosize_map)
            if x == 0:
                consolidated_df_in_va = pd.concat([consolidated_df_in_va, subfolder_df_in_VA])
            else:
                subfolder_df_in_VA = subfolder_df_in_VA.drop('# timestamp', axis=1)
                consolidated_df_in_va = pd.concat([consolidated_df_in_va, subfolder_df_in_VA], axis=1)

        # base load has one extra time stamp at the end, need to drop it
        n = 1
        consolidated_df_in_va.drop(consolidated_df_in_va.tail(n).index, inplace=True)  # drop last n rows

        # make it hourly
        consolidated_df_in_va['# timestamp'] = pd.to_datetime(consolidated_df_in_va['# timestamp'])
        consolidated_df_in_va = consolidated_df_in_va.groupby(
            consolidated_df_in_va['# timestamp'].dt.to_period('H')).first()

        consolidated_df_in_kw = consolidated_df_in_va.copy(deep=True)

        for col_name in list(consolidated_df_in_kw.columns):
            if col_name != "# timestamp":
                consolidated_df_in_kw[col_name] = consolidated_df_in_kw[col_name]/1000 # converting va to kw/kva

        consolidated_df_in_percent = consolidated_df_in_kw.copy(deep=True)

        for col_name, factor in cnsolidated_xfrmr_to_size_map.items():
            consolidated_df_in_percent[col_name] = (consolidated_df_in_percent[col_name] / factor)*100

        #------------------------------------

        # path = r'/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/' + value + f"_1_fl" + GLD_prefix + '1/'
        # load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = transformer_map(
        #     path)

        all_year_ev_uncontrolled_laod, current_size, year_list, all_year_ev_uncontrolled_laod_in_kw =\
            work_with_uncontrolled_and_controlled_ev_load(value, cnsolidated_xfrmr_to_size_map, "uncontrolled")

        all_year_ev_controlled_laod, current_size_con, year_list_con, all_year_ev_controlled_laod_in_kw = \
            work_with_uncontrolled_and_controlled_ev_load(value, cnsolidated_xfrmr_to_size_map, "controlled")
        all_year_ev_controlled_laod["day"] = all_year_ev_controlled_laod["day"] - min(all_year_ev_controlled_laod["day"])
        all_year_ev_controlled_laod_in_kw["day"] = all_year_ev_controlled_laod_in_kw["day"] - min(
            all_year_ev_controlled_laod_in_kw["day"])

        # include failed xfrmr info in controlled with uncontrolled data
        # all_year_ev_controlled_laod[all_year_ev_controlled_laod["Year"] == "2040"][
        #     ["feeder1_R2_12_47_1_xfmr_101_set11", "Year"]]

        # Below code makes sure there are no additional xfrmrs in uncontrolled or controlled. This does not happen at
        # all or rarely happens, you can keep debug button to see if it really happens often, or use print statement.
        diff_colnames1 = list(np.setdiff1d(all_year_ev_uncontrolled_laod.columns, all_year_ev_controlled_laod.columns))
        diff_colnames2 = list(np.setdiff1d(all_year_ev_controlled_laod.columns, all_year_ev_uncontrolled_laod.columns))

        if len(diff_colnames1) > 0:
            all_year_ev_uncontrolled_laod = all_year_ev_uncontrolled_laod.drop(columns=diff_colnames1)
        if len(diff_colnames2) > 0:
            all_year_ev_controlled_laod = all_year_ev_controlled_laod.drop(columns=diff_colnames2)


        df_final_divided_hourly = consolidated_df_in_percent.copy(deep=True)
        df_final_divided_inkws_hourly = consolidated_df_in_kw.copy(deep=True)

        # merge Ev and base load data
        merged_df_uncontrolled = mergebaseload_uncontrolled_controlled_ev_data(df_final_divided_hourly.copy(deep=True), all_year_ev_uncontrolled_laod, year_list)

        merged_df_controlled = mergebaseload_uncontrolled_controlled_ev_data(df_final_divided_hourly.copy(deep=True),
                                                                               all_year_ev_controlled_laod, year_list)

        merged_df_uncontrolled_in_kws = mergebaseload_uncontrolled_controlled_ev_data(df_final_divided_inkws_hourly.copy(deep=True),
                                                                               all_year_ev_uncontrolled_laod_in_kw, year_list)

        merged_df_controlled_in_kws = mergebaseload_uncontrolled_controlled_ev_data(
            df_final_divided_inkws_hourly.copy(deep=True),
            all_year_ev_controlled_laod_in_kw, year_list)


        test_hourly = df_final_divided_hourly.drop(columns=["# timestamp"])
        # test = df_final_divided.drop(columns=["# timestamp"])
        test = test_hourly.copy(deep=True)
        max_values = list(test.max(axis=0))
        max_list.append(max_values)
        transformer_names = list(test.max(axis=0).index)
        # xfrmr_ratings = []
        # for x in transformer_names:
        #     a1 = temp_sav_json1[int(x.split("_set")[1])-1]
        #     a2 = temp_sav_json2[int(x.split("_set")[1])-1]
        #     xfrmr_ratings.append(a2[a1[x.split("_set")[0]]])
        # xfrmr_ratings_list.append(xfrmr_ratings)
        xfrmr_ratings = []
        for x in transformer_names:
            a1 = cnsolidated_xfrmr_to_size_map[x]
            xfrmr_ratings.append(a1)
        xfrmr_ratings_list.append(xfrmr_ratings)


        # xfrmr_ratings = [temp_sav_json2[x.split("_set")[1]][temp_sav_json1[x.split("_set")[1]][x.split("_set")[0]]] for x in transformer_names]
        name_list.append(transformer_names)
        std_values = list(test.std())  # I think the transformer_names order is same for both max and std values.
        # (assumption, 99.999% true)
        std_list.append(std_values)

        # go through all columns of test and find total count of violations for entire simulation time.
        cumm_vio_counts = []
        for h_idx, hh_value in enumerate(transformer_names):
            cumm_vio_counts.append(test[test[hh_value]>100].shape[0])
        cumm_vio_counts_list.append(cumm_vio_counts)

        list_data.append(flatten(test_hourly.values.tolist()))

    # # dummy placeholder data
    # if not extrafoldersexist:

    basecase_transformer_loading_flatten_data = list_data[0]

    # below code plots the pdf with percenthist, commenting it out since we are not using it.
    # if plot_plotly:
    #     name_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_percenthist_basecase.pdf"
    #     plot_percent_hit(name_to_save, basecase_transformer_loading_flatten_data)

    # below script has uncontrolled and controlled data which will need to be in a loop for several years


    total_basecase_xfrmrs_with_evs = []
    total_basecase_vios = []
    total_uncontrolled_vios = []
    total_controlled_vios = []
    total_xfrmrs_need_replacing_120 = []
    replace_df = pd.DataFrame()
    for each_year in year_list:
        merged_df_uncontrolled_y = merged_df_uncontrolled.copy(deep=True)
        merged_df_uncontrolled_y = merged_df_uncontrolled_y[merged_df_uncontrolled_y["year_i"] == int(each_year)]
        test_hourly_uncontrolled = merged_df_uncontrolled_y.drop(columns=["# timestamp", "month", "year_i", "day", "hour"])

        uncontrolled_transformer_loading_flatten_data = flatten(test_hourly_uncontrolled.values.tolist())
        # if plot_plotly:
        #     name_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_percenthist_uncontrolled_{each_year}.pdf"
        #     plot_percent_hit(name_to_save, uncontrolled_transformer_loading_flatten_data)

        merged_df_controlled_y = merged_df_controlled.copy(deep=True)
        merged_df_controlled_y = merged_df_controlled_y[merged_df_controlled_y["year_i"] == int(each_year)]
        test_hourly_controlled = merged_df_controlled_y.drop(
            columns=["# timestamp", "month", "year_i", "day", "hour"])

        controlled_transformer_loading_flatten_data = flatten(test_hourly_controlled.values.tolist())
        # if plot_plotly:
        #     name_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_percenthist_controlled_{each_year}.pdf"
        #     plot_percent_hit(name_to_save, controlled_transformer_loading_flatten_data)



        max_values_uncontrolled = list(test_hourly_uncontrolled.max(axis=0))
        # max_values_controlled = [x - 0.8*(x - max_values[idx]) if (x > max_values[idx]) else max_values[idx] for idx, x in enumerate(max_values_uncontrolled)]  # dummy
        max_values_controlled = list(test_hourly_controlled.max(axis=0))

        transformer_names_uncontrolled = list(test_hourly_uncontrolled.max(axis=0).index)
        transformer_names_controlled = list(test_hourly_controlled.max(axis=0).index)


        cumm_vio_counts_uncontrolled = []
        for h_idx, hh_value in enumerate(transformer_names_uncontrolled):
            cumm_vio_counts_uncontrolled.append(test_hourly_uncontrolled[test_hourly_uncontrolled[hh_value] > 100].shape[0])

        cumm_vio_counts_controlled = []
        for h_idx, hh_value in enumerate(transformer_names_controlled):
            cumm_vio_counts_controlled.append(
                test_hourly_controlled[test_hourly_controlled[hh_value] > 100].shape[0])

        # cumm_vio_counts_controlled = []  # dummy
        # for h_idx, hh_value in enumerate(transformer_names):
        #     basecase_count = test[test[hh_value]>100].shape[0]
        #     uncontrolled_count = test_hourly_uncontrolled[test_hourly_uncontrolled[hh_value] > 100].shape[0]
        #     if uncontrolled_count > basecase_count:
        #         desired_counts = uncontrolled_count - 0.8*(uncontrolled_count - basecase_count)
        #     else:
        #         desired_counts = basecase_count
        #     cumm_vio_counts_controlled.append(desired_counts)

        xfrmr_ratings_uncontrolled = []
        for x in transformer_names_uncontrolled:
            a1 = cnsolidated_xfrmr_to_size_map[x]
            xfrmr_ratings_uncontrolled.append(a1)

        xfrmr_ratings_controlled = []
        for x in transformer_names_controlled:
            a1 = cnsolidated_xfrmr_to_size_map[x]
            xfrmr_ratings_controlled.append(a1)

        # xfrmr_ratings_controlled = xfrmr_ratings_uncontrolled  # dummy





        std_values_uncontrolled = list(test_hourly_uncontrolled.std())  # I think the transformer_names order is same for both max and std values.
        # (assumption, 99.999% true)
        std_values_controlled = list(test_hourly_controlled.std())  #[x - 0.8*(x - std_values[idx]) if (x > std_values[idx]) else std_values[idx] for idx, x in enumerate(std_values_uncontrolled)]  #[0.8*x for x in std_values_uncontrolled]  # dummy

        # list_data.append(flatten(test_hourly_uncontrolled.values.tolist()))
        # list_data.append([x * 1.2 for x in flatten(test_hourly.values.tolist())])  # dummy



        # basecase_transformer_loading_flatten_data = list_data[0]
        # name_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_percenthist_basecase.pdf"
        # plot_percent_hit(name_to_save, basecase_transformer_loading_flatten_data)
        #
        # basecase_transformer_loading_flatten_data = list_data[0]
        # name_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_percenthist_basecase.pdf"
        # plot_percent_hit(name_to_save, basecase_transformer_loading_flatten_data)

        # make df
        # first add basecase
        df_to_plot1 = pd.DataFrame({'type': ["basecase"]*len(max_list[0]), 'name': name_list[0],
                                    'Maximum % loading of transformer': max_list[0],
                                    'Variability in % loading of transformer': std_list[0], 'Transformer overload periods as a % of total time': cumm_vio_counts_list[0], 'rating': xfrmr_ratings_list[0]})
        # add basecase with uncontrolled
        df_to_plot2 = pd.DataFrame(
            {'type': ["uncontrolled"] * len(max_values_uncontrolled), 'name': transformer_names_uncontrolled, 'Maximum % loading of transformer': max_values_uncontrolled, 'Variability in % loading of transformer': std_values_uncontrolled,
             'Transformer overload periods as a % of total time': cumm_vio_counts_uncontrolled, 'rating': xfrmr_ratings_uncontrolled})
        # add basecase with controlled
        df_to_plot3 = pd.DataFrame(
            {'type': ["controlled"] * len(max_values_controlled), 'name': transformer_names_controlled, 'Maximum % loading of transformer': max_values_controlled, 'Variability in % loading of transformer': std_values_controlled,
             'Transformer overload periods as a % of total time': cumm_vio_counts_controlled, 'rating': xfrmr_ratings_controlled})
        df_to_plot = pd.concat([df_to_plot1, df_to_plot2, df_to_plot3], axis=0)
        df_to_plot['Transformer overload periods as a % of total time'] = (df_to_plot['Transformer overload periods as a % of total time']/test_hourly_uncontrolled.shape[0])*100

        # below lines of code is used to find the transformer count that are > 100% loaded.
        total_transformers = df_to_plot1.shape[0]
        k_here = df_to_plot1[df_to_plot1['Maximum % loading of transformer'] > 100].shape[0]
        total_basecase_vios.append(k_here)
        h_here = all_year_ev_uncontrolled_laod.shape[1]-1
        total_basecase_xfrmrs_with_evs.append(h_here)
        xfrmr_cnt_uncontrolled_100 = df_to_plot2[df_to_plot2['Maximum % loading of transformer'] > 100].shape[0]
        total_uncontrolled_vios.append(xfrmr_cnt_uncontrolled_100)
        xfrmr_cnt_controlled_100 = df_to_plot3[df_to_plot3['Maximum % loading of transformer'] > 100.1].shape[0]
        total_controlled_vios.append(xfrmr_cnt_controlled_100)

        xfrmr_replace_df = df_to_plot2[df_to_plot2['Maximum % loading of transformer'] > replace_threshold]
        xfrmr_replace_df["Year"] = each_year
        replace_df = pd.concat([replace_df, xfrmr_replace_df], ignore_index=True)
        xfrmr_replace_120 = xfrmr_replace_df.shape[0]
        total_xfrmrs_need_replacing_120.append(xfrmr_replace_120)


        # if xfrmr_cnt_uncontrolled_100 < k_here:
        #     pass
        # if h_here != 443:
        #     pass

        # create unique ID for each transformer
        unique_id_counter = 0
        unique_id_map = {}
        names_to_map = list(df_to_plot[df_to_plot["type"]=="basecase"]["name"])
        for name in names_to_map:
            unique_id_counter += 1
            unique_id_map[name] = unique_id_counter

        df_to_plot["Transformer indices"] = df_to_plot["name"].map(unique_id_map)

        test_hourly_uncontrolled["type"] = "Uncontrolled scenario"
        test_hourly_controlled["type"] = "Controlled scenario"
        df_for_box_plot = pd.concat([test_hourly_uncontrolled, test_hourly_controlled], axis=0)

        # fig = px.box(df_to_plot, x="Transformer indices", y=,
        #              color="type")
        # fig.show()


        df_to_plot_backup = df_to_plot.copy(deep=True)

        df_max = df_to_plot_backup[df_to_plot_backup["type"]=="basecase"].copy(deep=True)
        df_std = df_to_plot_backup[df_to_plot_backup["type"] == "basecase"].copy(deep=True)
        df_cum = df_to_plot_backup[df_to_plot_backup["type"] == "uncontrolled"].copy(deep=True)  # used as reference to rank the transformer indices since base case has no cum violations////

        df_max = df_max.sort_values("Maximum % loading of transformer", ascending=False)
        df_max["Transformer indices"] = range(1, df_max.shape[0]+1)
        df_max_dict = df_max.groupby("name")["Transformer indices"].apply(lambda x: int(x.iloc[0]))
        df_max_dict = df_max_dict.to_dict()
        df_to_plot["Transformer indices"] = df_to_plot["name"].map(df_max_dict)

        # plotting script here.
        # fig = px.scatter(df.query("year==2007"), x="gdpPercap", y="lifeExp",
        #                  size="pop", color="continent",
        #                  hover_name="country", log_x=True, size_max=60)
        # fig = px.scatter(df_to_plot[df_to_plot["type"]=="basecase"], x="uniqueID", y="std",
        #                  size="rating", color="type",
        #                  hover_name="name", log_x=True, size_max=60)




        if plot_plotly:

            if each_year == "2040":
                k = 1


            for loop_i in range(2):
                var = "Maximum % loading of transformer"
                if loop_i == 1:
                    # NOTE: COMMENT BELOW TWO BLOCKS OF CODE  TO SEE ORIGINAL BUBBLE PLOTS!!!
                    info_info = "zoom_in"
                    # drop all xfrmrs which already have basecase violations greater than 100% (due to building loads).
                    # to remove them from ev plots
                    xfrmrs_with_base_violations = list(
                        df_to_plot[(df_to_plot["type"] == "basecase") & (df_to_plot[var] >= 100)]["name"])
                    fdkj = df_to_plot[df_to_plot["name"].isin(xfrmrs_with_base_violations)]
                    df_to_plot = df_to_plot.drop(fdkj.index)
                    df_to_plot.reset_index(drop=True, inplace=True)

                    # show only the xfrmrs whose violations are greater than 100%
                    xfrmrs_with_ev_violations = list(
                        df_to_plot[(df_to_plot["type"] == "uncontrolled") & (df_to_plot[var] >= 100)]["name"])
                    fdkj = df_to_plot[~df_to_plot["name"].isin(xfrmrs_with_ev_violations)]
                    df_to_plot = df_to_plot.drop(fdkj.index)
                    df_to_plot.reset_index(drop=True, inplace=True)

                    # remove basecase type data from plot df
                    mask_basecase_info = df_to_plot[df_to_plot["type"] == "basecase"]
                    df_to_plot = df_to_plot.drop(mask_basecase_info.index)
                    df_to_plot.reset_index(drop=True, inplace=True)

                    # do not include size of bubbles as rating
                    df_to_plot["rating"] = 1

                    color_pallate = px.colors.qualitative.Plotly[1:]

                    size_value = 12
                else:
                    info_info = "zoom_out"
                    # all ev xfrmrs
                    xfrmrs_with_ev_violations = list(df_to_plot[df_to_plot["type"] == "uncontrolled"]["name"])

                    color_pallate = px.colors.qualitative.Plotly

                    size_value = 60

                fig = px.scatter(df_to_plot, x="Transformer indices", y="Maximum % loading of transformer",
                                 size="rating", color="type",
                                 hover_name="name", size_max=size_value, color_discrete_sequence=color_pallate)  #  log_x=True,
                fig.add_hline(y=100, line_width=4, line_color="red")
                # fig.add_hrect(y0=100.5, y1=max(df_to_plot[var]) + 0.2 * max(df_to_plot[var]), line_width=0, fillcolor="red", opacity=0.2)
                if df_to_plot.empty:
                    pass
                else:
                    fig.update_layout(yaxis_range=[-1 * 0.1 * max(df_to_plot[var]), max(df_to_plot[var]) + 0.2 * max(df_to_plot[var])])
                fig.update_layout(
                    yaxis=dict(
                        titlefont_size=30,
                        tickfont_size=28,
                    ),
                    xaxis=dict(
                        titlefont_size=30,
                        tickfont_size=28,
                    ),
                    font=dict(
                        family="Courier New, monospace",
                        size=30,
                        color="RebeccaPurple"
                    ),
                    paper_bgcolor='rgba(255,255,255,1)',
                    plot_bgcolor='rgba(255,255,255,1)'
                )
                directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
                if not os.path.exists(directory):
                    os.makedirs(directory)
                fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
                fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
                # fig.update_yaxes(range=[98, max(df_to_plot[var])])
                plotly.offline.plot(fig,
                                    filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_max_bubble_{each_year}_{info_info}.html", auto_open=False)

                df_std = df_std.sort_values("Variability in % loading of transformer", ascending=False)
                df_std["Transformer indices"] = range(1, df_std.shape[0] + 1)
                df_std_dict = df_std.groupby("name")["Transformer indices"].apply(lambda x: int(x.iloc[0]))
                df_std_dict = df_std_dict.to_dict()
                df_to_plot["Transformer indices"] = df_to_plot["name"].map(df_std_dict)

                var = "Variability in % loading of transformer"
                fig = px.scatter(df_to_plot, x="Transformer indices", y="Variability in % loading of transformer",
                                 size="rating", color="type",
                                 hover_name="name", size_max=size_value, color_discrete_sequence=color_pallate)
                if df_to_plot.empty:
                    pass
                else:
                    fig.update_layout(yaxis_range=[-1*0.1*max(df_to_plot[var]), max(df_to_plot[var]) + 0.2*max(df_to_plot[var])])
                fig.update_layout(
                    yaxis=dict(
                        titlefont_size=30,
                        tickfont_size=28,
                    ),
                    xaxis=dict(
                        titlefont_size=30,
                        tickfont_size=28,
                    ),
                    font=dict(
                        family="Courier New, monospace",
                        size=30,
                        color="RebeccaPurple"
                    ),
                    paper_bgcolor='rgba(255,255,255,1)',
                    plot_bgcolor='rgba(255,255,255,1)'
                )
                fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
                fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
                # fig.update_yaxes(range=[100, None])
                plotly.offline.plot(fig,
                                    filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_std_bubble_{each_year}_{info_info}.html", auto_open=False)

                # plot box plot for std info
                # include only xfrmrs that have violations due to EVs
                if xfrmrs_with_ev_violations is None:
                    xfrmrs_with_ev_violations = []
                xfrmrs_with_ev_violations.append("type")
                df_for_box_plot = df_for_box_plot.drop(columns=[col for col in df_for_box_plot if col not in xfrmrs_with_ev_violations])
                df_for_box_plot = df_for_box_plot.rename(columns=unique_id_map)
                # clmn_lst = list(df_to_plot["Transformer indices"].unique())
                # clmn_lst.append("type")
                # df_for_box_to_plot = df_for_box_plot[clmn_lst]
                df_for_box_to_plot = df_for_box_plot.copy(deep=True)
                # find xfrmrs with large std
                my_series = df_for_box_to_plot.std()
                sorted_indicessss = my_series.argsort()
                top_10 = sorted_indicessss[sorted_indicessss < 10]
                fig = go.Figure()
                y_mega_list_unc = []
                x_mega_list_unc = []
                y_mega_list_c = []
                x_mega_list_c = []
                for col in list(top_10.index):
                    unc_dtf = df_for_box_to_plot[df_for_box_to_plot["type"] == "Uncontrolled scenario"]
                    c_dtf = df_for_box_to_plot[df_for_box_to_plot["type"] == "Controlled scenario"]
                    y_values = list(unc_dtf[col].values)
                    y_mega_list_unc.extend(y_values)
                    name_val = unc_dtf[col].name
                    x_mega_list_unc.extend(itertools.repeat(str(col), len(y_values)))
                    y_values = list(c_dtf[col].values)
                    y_mega_list_c.extend(y_values)
                    name_val = c_dtf[col].name
                    x_mega_list_c.extend(itertools.repeat(str(col), len(y_values)))

                fig.add_trace(
                    go.Box(y=y_mega_list_unc, x=x_mega_list_unc, name="Uncontrolled", marker_color='green'))
                fig.add_trace(go.Box(y=y_mega_list_c, x=x_mega_list_c, name="Controlled", marker_color='blue'))
                fig.update_layout(
                    # group together boxes of the different
                    # traces for each value of x
                    yaxis_title='Variability in % loading of transformer',
                    xaxis_title = 'Transformer Indices',
                    yaxis=dict(
                        titlefont_size=30,
                        tickfont_size=28,
                    ),
                    xaxis=dict(
                        titlefont_size=30,
                        tickfont_size=28,
                    ),
                    font=dict(
                        family="Courier New, monospace",
                        size=30,
                        color="RebeccaPurple"
                    ),
                    paper_bgcolor='rgba(255,255,255,1)',
                    plot_bgcolor='rgba(255,255,255,1)',
                    boxmode='group'
                )
                fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
                fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
                plotly.offline.plot(fig,
                                    filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_std_boxplot_{each_year}_{info_info}.html",
                                    auto_open=False)
                # fig.show()

                df_cum = df_cum.sort_values("Transformer overload periods as a % of total time", ascending=False)
                df_cum["Transformer indices"] = range(1, df_cum.shape[0] + 1)
                df_cum_dict = df_cum.groupby("name")["Transformer indices"].apply(lambda x: int(x.iloc[0]))
                df_cum_dict = df_cum_dict.to_dict()
                df_to_plot["Transformer indices"] = df_to_plot["name"].map(df_cum_dict)

                var = "Transformer overload periods as a % of total time"
                fig = px.scatter(df_to_plot, x="Transformer indices", y=var,
                                 size="rating", color="type",
                                 hover_name="name", size_max=size_value, color_discrete_sequence=color_pallate)
                if df_to_plot.empty:
                    pass
                else:
                    fig.update_layout(yaxis_range=[-1*0.1*max(df_to_plot[var]), max(df_to_plot[var]) + 0.2*max(df_to_plot[var])])
                fig.update_layout(
                    yaxis=dict(
                        titlefont_size=26,
                        tickfont_size=28,
                    ),
                    xaxis=dict(
                        titlefont_size=26,
                        tickfont_size=28,
                    ),
                    font=dict(
                        family="Courier New, monospace",
                        size=26,
                        color="RebeccaPurple"
                    ),
                    paper_bgcolor='rgba(255,255,255,1)',
                    plot_bgcolor='rgba(255,255,255,1)'
                )
                fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
                fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
                # fig.update_yaxes(range=[1, max(df_to_plot[var])])
                plotly.offline.plot(fig,
                                    filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_cum_bubble_{each_year}_{info_info}.html", auto_open=False)
                # fig.show()

    k = 1
    return year_list, total_basecase_xfrmrs_with_evs, total_uncontrolled_vios, total_controlled_vios, merged_df_uncontrolled, total_basecase_vios, merged_df_uncontrolled_in_kws, df_final_divided_inkws_hourly, all_year_ev_uncontrolled_laod_in_kw, merged_df_controlled_in_kws, all_year_ev_controlled_laod_in_kw, total_xfrmrs_need_replacing_120, replace_df


def plot1a_task_percentoverload_mod(input_basecase_folder_name, GLD_prefix, sets_in_all_folders):
    input_basecase_without_ev = input_basecase_folder_name + '_uncontrolled'
    input_basecase_with_ev = input_basecase_folder_name + '_controlled'
    folder_list = [input_basecase_folder_name, input_basecase_without_ev, input_basecase_with_ev]

    # iterate through folders (3 cases)
    max_list = []
    std_list = []
    name_list = []
    cumm_vio_counts_list = []
    xfrmr_ratings_list = []
    list_data = []
    for idx, value in enumerate(folder_list):
        print(f"Current working on following scenario = {value}. Current scenario progress = {idx+1}/{len(folder_list)}.")
        # read transformer data and calculate its percent overload
        df_final_divided = pd.DataFrame()
        # iterate through subsimulations/sets for each folder
        ct = 0
        temp_sav_json1 = []
        temp_sav_json2 = []
        for x in range(sets_in_all_folders[idx]):
            path = value + f"_{x+1}_fl" + GLD_prefix + '1/'
            ct += 1
            print(
                f"Calculating percent overload data at location = {path}. Current folder progress = {ct}/{sets_in_all_folders[idx]}.")
            df_final = sum_all_csv_Files(path)
            # df_final = pd.concat([df_final, df_final_fv], axis=0)
            load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = transformer_map(path)
            temp_sav_json1.append(load_to_xfrmr_config_map_dict)
            temp_sav_json2.append(config_to_power_rating_map_dict)
            # if len(df_final.columns) != len(transformer_rating_dct):
            #     raise ValueError("DataFrame and dictionary have different numbers of columns.")
            comm_load_names0 = list(df_final.columns)
            comm_load_names = [x for x in comm_load_names0 if x != '# timestamp']
            if idx == 0:
                tempval = 1
            elif idx == 1:
                tempval = 1.5
            elif idx == 2:
                tempval = 1.2
            df_divided = pd.DataFrame(data={
                col: (df_final[col] / (config_to_power_rating_map_dict[load_to_xfrmr_config_map_dict[col]] * 1000))*tempval * 100 for
                col in comm_load_names})
            df_divided2 = pd.concat([df_divided, df_final["# timestamp"].to_frame()], axis=1)
            col_name_map = dict()
            for val in comm_load_names:
                col_name_map[val] = val+f"_set{x+1}"
            df_divided2 = df_divided2.rename(columns=col_name_map)
            # df_final_divided = pd.concat([df_final_divided, df_divided], axis=0)
            if ct > 1:
                df_final_divided = df_final_divided.merge(df_divided2, on="# timestamp", how="outer")
            else:
                df_final_divided = df_divided2.copy(deep=True)

        # now what is aggregation choice to use to plot each transformer's associated y-axis value?
        # IMPORTANT NOTES BELOW
        # we will show peak overload (for completeness sake, people think of it)
        # we will also show the standard deviation of transformer loading. These will be two aggregation criteria.
        # standard deviation helps understand by much a transformer's loading changes for every hour (since the data
        # used will be at hourly) i.e., load shape variation. Note: we only have limited control over the load shape as
        # EV is not major part of load shape (at the moment).
        test = df_final_divided.drop(columns=["# timestamp"])
        max_values = list(test.max(axis=0))
        max_list.append(max_values)
        transformer_names = list(test.max(axis=0).index)
        xfrmr_ratings = []
        for x in transformer_names:
            a1 = temp_sav_json1[int(x.split("_set")[1])-1]
            a2 = temp_sav_json2[int(x.split("_set")[1])-1]
            xfrmr_ratings.append(a2[a1[x.split("_set")[0]]])
        xfrmr_ratings_list.append(xfrmr_ratings)
        # xfrmr_ratings = [temp_sav_json2[x.split("_set")[1]][temp_sav_json1[x.split("_set")[1]][x.split("_set")[0]]] for x in transformer_names]
        name_list.append(transformer_names)
        std_values = list(test.std())  # I think the transformer_names order is same for both max and std values.
        # (assumption, 99.999% true)
        std_list.append(std_values)

        # go through all columns of test and find total count of violations for entire simulation time.
        cumm_vio_counts = []
        for h_idx, hh_value in enumerate(transformer_names):
            cumm_vio_counts.append(test[test[hh_value]>100].shape[0])
        cumm_vio_counts_list.append(cumm_vio_counts)

        list_data.append(flatten(test.values.tolist()))


    # plt.hist(list_data[0], weights=np.ones(len(list_data[0])) / len(list_data[0]))
    # plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    # plt.show()

    # make df
    # first add basecase
    df_to_plot1 = pd.DataFrame({'type': ["basecase"]*len(max_list[0]), 'name': name_list[0],
                                'Maximum percentage loading of transformer': max_list[0],
                                'Variability in percentage loading of transformer': std_list[0], 'Transformer overload periods as a percentage of total time': cumm_vio_counts_list[0], 'rating': xfrmr_ratings_list[0]})
    # add basecase with uncontrolled
    df_to_plot2 = pd.DataFrame(
        {'type': ["uncontrolled"] * len(max_list[1]), 'name': name_list[1], 'Maximum percentage loading of transformer': max_list[1], 'Variability in percentage loading of transformer': std_list[1],
         'Transformer overload periods as a percentage of total time': cumm_vio_counts_list[1], 'rating': xfrmr_ratings_list[1]})
    # add basecase with controlled
    df_to_plot3 = pd.DataFrame(
        {'type': ["controlled"] * len(max_list[2]), 'name': name_list[2], 'Maximum percentage loading of transformer': max_list[2], 'Variability in percentage loading of transformer': std_list[2],
         'Transformer overload periods as a percentage of total time': cumm_vio_counts_list[2], 'rating': xfrmr_ratings_list[2]})
    df_to_plot = pd.concat([df_to_plot1, df_to_plot2, df_to_plot3], axis=0)
    df_to_plot['Transformer overload periods as a percentage of total time'] = df_to_plot['Transformer overload periods as a percentage of total time']/df_divided2.shape[0]

    total_transformers = df_to_plot1.shape[0]
    climate_zone = "2B"
    adaption_year = "2040"
    xfrmr_cnt_uncontrolled_100 = df_to_plot2[df_to_plot2['Maximum percentage loading of transformer'] > 100].shape[0]
    xfrmr_cnt_controlled_100 = df_to_plot3[df_to_plot3['Maximum percentage loading of transformer'] > 100].shape[0]

    # create unique ID for each transformer
    unique_id_counter = 0
    unique_id_map = {}
    names_to_map = list(df_to_plot[df_to_plot["type"]=="basecase"]["name"])
    for name in names_to_map:
        unique_id_counter += 1
        unique_id_map[name] = unique_id_counter

    df_to_plot["Transformer indices"] = df_to_plot["name"].map(unique_id_map)


    df_to_plot_backup = df_to_plot.copy(deep=True)

    df_max = df_to_plot_backup[df_to_plot_backup["type"]=="basecase"].copy(deep=True)
    df_std = df_to_plot_backup[df_to_plot_backup["type"] == "basecase"].copy(deep=True)
    df_cum = df_to_plot_backup[df_to_plot_backup["type"] == "uncontrolled"].copy(deep=True)

    df_max = df_max.sort_values("Maximum percentage loading of transformer", ascending=False)
    df_max["Transformer indices"] = range(1, df_max.shape[0]+1)
    df_max_dict = df_max.groupby("name")["Transformer indices"].apply(lambda x: int(x.iloc[0]))
    df_max_dict = df_max_dict.to_dict()
    df_to_plot["Transformer indices"] = df_to_plot["name"].map(df_max_dict)

    # plotting script here.
    # fig = px.scatter(df.query("year==2007"), x="gdpPercap", y="lifeExp",
    #                  size="pop", color="continent",
    #                  hover_name="country", log_x=True, size_max=60)
    # fig = px.scatter(df_to_plot[df_to_plot["type"]=="basecase"], x="uniqueID", y="std",
    #                  size="rating", color="type",
    #                  hover_name="name", log_x=True, size_max=60)

    var = "Maximum percentage loading of transformer"
    fig = px.scatter(df_to_plot, x="Transformer indices", y="Maximum percentage loading of transformer",
                     size="rating", color="type",
                     hover_name="name", size_max=60)  #  log_x=True,
    fig.add_hline(y=100, line_width=4, line_color="red")
    # fig.add_hrect(y0=100.5, y1=max(df_to_plot[var]) + 0.2 * max(df_to_plot[var]), line_width=0, fillcolor="red", opacity=0.2)
    fig.update_layout(yaxis_range=[-1 * 0.1 * max(df_to_plot[var]), max(df_to_plot[var]) + 0.2 * max(df_to_plot[var])])
    directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/dummycheckplot"
    if not os.path.exists(directory):
        os.makedirs(directory)
    plotly.offline.plot(fig,
                        filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/dummycheckplot/max_bubble.html")

    df_std = df_std.sort_values("Variability in percentage loading of transformer", ascending=False)
    df_std["Transformer indices"] = range(1, df_std.shape[0] + 1)
    df_std_dict = df_std.groupby("name")["Transformer indices"].apply(lambda x: int(x.iloc[0]))
    df_std_dict = df_std_dict.to_dict()
    df_to_plot["Transformer indices"] = df_to_plot["name"].map(df_std_dict)

    var = "Variability in percentage loading of transformer"
    fig = px.scatter(df_to_plot, x="Transformer indices", y="Variability in percentage loading of transformer",
                     size="rating", color="type",
                     hover_name="name", size_max=60)
    fig.update_layout(yaxis_range=[-1*0.1*max(df_to_plot[var]), max(df_to_plot[var]) + 0.2*max(df_to_plot[var])])
    plotly.offline.plot(fig,
                        filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/dummycheckplot/std_bubble.html")

    df_cum = df_cum.sort_values("Transformer overload periods as a percentage of total time", ascending=False)
    df_cum["Transformer indices"] = range(1, df_cum.shape[0] + 1)
    df_cum_dict = df_cum.groupby("name")["Transformer indices"].apply(lambda x: int(x.iloc[0]))
    df_cum_dict = df_cum_dict.to_dict()
    df_to_plot["Transformer indices"] = df_to_plot["name"].map(df_cum_dict)

    var = "Transformer overload periods as a percentage of total time"
    fig = px.scatter(df_to_plot, x="Transformer indices", y=var,
                     size="rating", color="type",
                     hover_name="name", size_max=60)
    fig.update_layout(yaxis_range=[-1*0.1*max(df_to_plot[var]), max(df_to_plot[var]) + 0.2*max(df_to_plot[var])])
    plotly.offline.plot(fig,
                        filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/dummycheckplot/cum_bubble.html")
    # fig.show()


    k = 1

def plot_histogram_plotly_1plot(plots_folder_name, basecase_peak_demand_all_folders, x_label_for_barplot, title, x_title, file_to_save, scenario):
    directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
    if not os.path.exists(directory):
        os.makedirs(directory)
    x_label_for_barplot = [str(x) for x in x_label_for_barplot]
    fig = go.Figure(
        go.Bar(x=x_label_for_barplot, y=[x for x in basecase_peak_demand_all_folders], name=scenario))

    fig.update_layout(
        yaxis=dict(
            title=title,
            titlefont_size=30,
            tickfont_size=28,
        ),
        xaxis=dict(
            title=x_title,
            titlefont_size=30,
            tickfont_size=28,
        ),
        font=dict(
            family="Courier New, monospace",
            size=30,
            color="RebeccaPurple"
        ),
        paper_bgcolor='rgba(255,255,255,1)',
        plot_bgcolor='rgba(255,255,255,1)'
    )
    fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
    plotly.offline.plot(fig,
                        filename=file_to_save, auto_open=False)

def plot_histogram_plotly(plots_folder_name, basecase_peak_demand_all_folders, uncontrolled_peak_demand_all_folders, controlled_peak_demand_all_folders, x_label_for_barplot, title, x_title, file_to_save, size_val, evxfrmrcount):
    directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
    if not os.path.exists(directory):
        os.makedirs(directory)
    x_label_for_barplot = [str(x) for x in x_label_for_barplot]
    position_val = "outside"
    # size_val = 28
    colot_val = "black"
    fig = go.Figure(
        go.Bar(x=x_label_for_barplot, y=[x for x in basecase_peak_demand_all_folders], name="Base case",
               text=[int(x) for x in basecase_peak_demand_all_folders], textposition=position_val,
               outsidetextfont=dict(size=size_val, color=colot_val), constraintext='none'))
    fig.add_trace(
        go.Bar(x=x_label_for_barplot, y=[x for x in uncontrolled_peak_demand_all_folders],
               name="Uncontrolled", text=[int(x) for x in uncontrolled_peak_demand_all_folders],
               textposition=position_val, outsidetextfont=dict(size=size_val, color=colot_val), constraintext='none'))
    fig.add_trace(
        go.Bar(x=x_label_for_barplot, y=[x for x in controlled_peak_demand_all_folders], name="Controlled",
               text=[int(x) for x in controlled_peak_demand_all_folders], textposition=position_val,
               outsidetextfont=dict(size=size_val, color=colot_val), constraintext='none'))

    if evxfrmrcount != 'dont care':
        if "Large" in plots_folder_name:
            tot_cm_xfmr = 2501
        elif "Medium" in plots_folder_name:
            tot_cm_xfmr = 1549
        elif "Small" in plots_folder_name:
            tot_cm_xfmr = 187
        else:
            print("something wrong hereeeeee....exiting...")
            exit()
        fig.add_annotation(x=5, y=max(uncontrolled_peak_demand_all_folders)+10,
                           text=f"Total EV transformers = {evxfrmrcount}/{tot_cm_xfmr}",
                           showarrow=False,
                           yshift=10)
    fig.update_layout(
        yaxis=dict(
            title=title,
            titlefont_size=30,
            tickfont_size=28,
        ),
        xaxis=dict(
            title=x_title,
            titlefont_size=30,
            tickfont_size=28,
        ),
        font=dict(
            family="Courier New, monospace",
            size=30,
            color="RebeccaPurple"
        ),
        paper_bgcolor='rgba(255,255,255,1)',
        plot_bgcolor='rgba(255,255,255,1)'
    )
    fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
    # fig.show()
    plotly.offline.plot(fig,
                        filename=file_to_save, auto_open=False)

    k = 1

def plot_stacked_plot_for_uncontrolled_ev(years_list, base_demand_list, ev_demand_list, size_val, file_to_save, grid_peak_demand_value, y_title, x_title):
    position_val = "auto"
    # size_val = 28
    colot_val = "black"
    fig = go.Figure(data=[
        go.Bar(name='Base Demand', x=years_list, y=base_demand_list, marker_color="grey",
               text=[int(x) for x in base_demand_list],
               textposition=position_val, outsidetextfont=dict(size=size_val, color=colot_val), constraintext='none'),
        go.Bar(name='Uncontrolled EV Demand', x=years_list, y=ev_demand_list, marker_color='#EF553B',
               text=[int(x) for x in ev_demand_list],
               textposition=position_val, outsidetextfont=dict(size=size_val, color=colot_val), constraintext='none')
    ])
    fig.add_hline(y=grid_peak_demand_value / 1000, line_width=4, line_color="black")
    # Change the bar mode
    fig.update_layout(barmode='stack',
                      yaxis=dict(
                          title=y_title,
                          titlefont_size=30,
                          tickfont_size=28,
                      ),
                      xaxis=dict(
                          title=x_title,
                          titlefont_size=30,
                          tickfont_size=28,
                      ),
                      font=dict(
                          family="Courier New, monospace",
                          size=30,
                          color="RebeccaPurple"
                      ),
                      paper_bgcolor='rgba(255,255,255,1)',
                      plot_bgcolor='rgba(255,255,255,1)'
                      )
    fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
    # fig.show()
    plotly.offline.plot(fig,
                        filename=file_to_save, auto_open=False)

def extract_demand_forecast_from_gld(path, subfolder_num):
    # config_to_power_rating_map_dict has ratings in kva!
    (load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name,
     xfrmr_name_to_size) = transformer_map(path)

    subfolder_xfrmr_name_to_size = {}  # xfrmr_name_to_size in kva
    for key, value in xfrmr_name_to_size.items():
        subfolder_xfrmr_name_to_size[key + f"_set{subfolder_num}"] = value

    u,c = np.unique(np.array(list(load_to_xfrmr_name.values())), return_counts=True)
    dup = u[c>1]

    if dup.size != 0:
        print("found multiple commercial loads at one transformer. this should not be possible as per tesp, exiting "
              "code...verify/debug..")
        exit()

    df_csv = sum_all_csv_Files(path)
    d = {}
    for key, value in load_to_xfrmr_name.items():
        d[key+'_streetlights'] = value
    df_replace_loadnames_with_xfrmr_names = df_csv.rename(columns=d)

    for i in range(df_replace_loadnames_with_xfrmr_names.columns.values.size):
        if df_replace_loadnames_with_xfrmr_names.columns.values[i] == '# timestamp':
            pass
        else:
            df_replace_loadnames_with_xfrmr_names.columns.values[i] = (df_replace_loadnames_with_xfrmr_names.columns.values[i] +
                                                               f"_set{subfolder_num}")

    # save the demand into a csv
    df_replace_loadnames_with_xfrmr_names.to_csv(path+'comm_xfrmr_load_inVA.csv', index=False)

    return df_replace_loadnames_with_xfrmr_names, subfolder_xfrmr_name_to_size

    # k = 1


if __name__ == '__main__':
    pd.set_option('display.max_columns', 50)
    day_range = range(1, 7)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    dso_range = range(1, 2)  # 1 = DSO 1 (end range should be last DSO +1)
    dso = 1
    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'
    curr_dir = os.getcwd()
    # / home / gudd172 / tesp / repository / tesp / examples / analysis / dsot / code / lean_aug_8_v3_fl_ev
    metadata_path = '/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/data'

    # updates for new metric plots.
    # 3 types of transformer metric plots below (each plot requires - basecase, basecase without EV, and basecase with
    # EV)
    # TODO: Finish plotting and come back to make them beautiful!

    # Plot type-1: pick the climate zone and grid size (to compare above 3 cases)
    # 1a) percent overload of each transformer
    # 1b) cummulative hours of violations for each transformer
    # 1c) "add more if something comes to mind" - work in progress

    # # 1a) starts here
    # input_1a = 'AZ_Tucson_Small_feb24_runs'  # selected a climate zone and grid size here. rest everything is processed
    # # inside a function. Nothing needs to be read here in the main.
    # sets_in_all_folders = [2]*3
    # plot1a_task_percentoverload_mod(input_1a, GLD_prefix, sets_in_all_folders)


    # We need one comparison plots between three grid sizes (for completeness)

    # We need one comparison between same grid size but different climate zones! (this needs to be figured out and plotted as well)



    # folder_name = 'small_grid_only_residential_fl'
    # folder_name = 'medium_grid_only_residential_fl'
    # folder_name = 'large_grid_only_residential_fl'
    # folder_name = 'medium_grid_try2_july_only_residential_fl'
    # folder_name = 'large_twogrids_final_fl'
    # folder_name = 'medium_final_withCommercial_fl'
    # folder_name = 'medium_final_withCommercial_outTempChng_fl'
    # folder_name = 'medium_final_withCommercial_inTempChng_fl'
    #folder_name = 'IA_Johnston_Large_Main_dataset_run_Bilal_fl'
    # MT_Greatfalls_Large_parallel_and_comm_overload_test2_13_fl, AK_Anchorage_Large_parallel_and_comm_overload_test2_{ji+1}_fl, AZ_Tucson_Large_parallel_and_comm_overload_test2_1_fl

    # zone_name = "AZ_Tucson_Large"
    # state = "az"
    # total_folders = 17
    # zone_name = "WA_Tacoma_Large"
    # state = "wa"
    # total_folders = 17
    # zone_name = "AL_Dothan_Large"
    # state = "al"
    # total_folders = 17
    # zone_name = "IA_Johnston_Large"
    # state = "ia"
    # total_folders = 17
    # zone_name = "LA_Alexandria_Large"
    # state = "la"
    # total_folders = 17
    # zone_name = "AK_Anchorage_Large"
    # state = "ak"
    # total_folders = 16
    # zone_name = "MT_Greatfalls_Large"
    # state = "mt"
    # total_folders = 16
    # zone_name_list = ["AZ_Tucson_Large", "WA_Tacoma_Large", "AL_Dothan_Large", "IA_Johnston_Large", "LA_Alexandria_Large", "AK_Anchorage_Large", "MT_Greatfalls_Large"]
    # state_list = ["az", "wa", "al", "ia", "la", "ak", "mt"]
    # folder_list = [17, 17, 17, 17, 17, 16, 16]
    # zone_name_list = ["MT_Greatfalls_Large"]  # , "AK_Anchorage_Large" and "IA_Johnston_Large" had problems....need to check gridlabd logs and fix any issues!
    # state_list = ["mt"]
    # folder_list = [16]

    # for first set of controlled results (end of March ppt)
    # sensitivity_suffix = "scm_tight"
    #
    # randomsoc = True
    # xfrmrrating_evshare = 70
    # EV_placement_on_grid = "ascen"
    # date_name = "mar31"
    # sens_flag = "tight"
    # custom_suffix_sim_run = (f"randsoc{randomsoc}_sensflag{sens_flag}_evongrid{xfrmrrating_evshare}"
    #                          f"{EV_placement_on_grid}_{date_name}")
    # custom_suffix_sim_run_uncontrolled = (f"randsoc{randomsoc}_evongrid{xfrmrrating_evshare}"
    #                                       f"{EV_placement_on_grid}_{date_name}")



    randomsoc = True
    xfrmrrating_evshare = 70


    # EV_placement_on_grid = "ascen"

    offset_evtimes_main_logic = True
    if offset_evtimes_main_logic:
        EV_placement_on_grid = "cyclic_evtimes_6pm8am"
    else:
        EV_placement_on_grid = "cyclic_nrel_fleet_data"

    sens_flag = "tight"
    sensitivity_suffix = f"scm_{sens_flag}"
    date_name = f"may22_{sens_flag}"  # f"april21_{sens_flag}"
    threshold_cutoff = 1
    custom_suffix_sim_run = (f"randsoc{randomsoc}_sensflag{sens_flag}_evongrid{xfrmrrating_evshare}"
                             f"{EV_placement_on_grid}_threshold{threshold_cutoff}_{date_name}")
    custom_suffix_sim_run_uncontrolled = (f"randsoc{randomsoc}_evongrid{xfrmrrating_evshare}"
                                          f"{EV_placement_on_grid}_{date_name}")

    customsuffix_l = "feb12_runs"
    customsuffix_m = "feb24_runs"
    customsuffix_s = "feb24_runs"
    size_name_l = "large"
    size_name_m = "medium"
    size_name_s = "small"
    # zone_name_list_l = ["AZ_Tucson_Large", "WA_Tacoma_Large", "AL_Dothan_Large", "LA_Alexandria_Large"]
    # zone_name_list_s = ["AZ_Tucson_Small", "WA_Tacoma_Small", "AL_Dothan_Small", "IA_Johnston_Small",
    #                   "LA_Alexandria_Small", "AK_Anchorage_Small", "MT_Greatfalls_Small"]
    # zone_name_list_m = ["AZ_Tucson_Medium", "WA_Tacoma_Medium", "AL_Dothan_Medium", "IA_Johnston_Medium", "LA_Alexandria_Medium", "AK_Anchorage_Medium", "MT_Greatfalls_Medium"]  # ["AZ_Tucson_Medium", "WA_Tacoma_Medium"]

    zone_name_list_l = ["AZ_Tucson_Large"]
    zone_name_list_s = ["AZ_Tucson_Small"]
    zone_name_list_m = ["AZ_Tucson_Medium"]

    # state_list_l = ["az", "wa", "al", "la"]
    # state_list_m = ["az", "wa", "al", "ia", "la", "ak", "mt"]
    # state_list_s = ["az", "wa", "al", "ia", "la", "ak", "mt"]

    state_list_l = ["az"]
    state_list_m = ["az"]
    state_list_s = ["az"]
    # folder_list_l = [17, 17, 17, 17]
    # folder_list_s = [2, 2, 2, 2, 2, 2, 2]
    # folder_list_m = [10, 10, 10, 10, 10, 10, 10]

    folder_list_l = [17]
    folder_list_s = [2]
    folder_list_m = [10]


    customsuffix_list = [customsuffix_l, customsuffix_m, customsuffix_s]
    size_name_list = [size_name_l, size_name_m, size_name_s]
    zone_name_list_list = [zone_name_list_l, zone_name_list_m, zone_name_list_s]
    state_list_list = [state_list_l, state_list_m, state_list_s]
    folder_list_list = [folder_list_l, folder_list_m, folder_list_s]

    for main_loop_idx, customsuffix in enumerate(customsuffix_list):

        size_name = size_name_list[main_loop_idx]
        zone_name_list = zone_name_list_list[main_loop_idx]
        state_list = state_list_list[main_loop_idx]
        folder_list = folder_list_list[main_loop_idx]


        extrafoldersexist = True

        # customsuffix = "feb12_runs"
        # # customsuffix = "feb24_runs"
        # size_name = "large"
        # # size_name = "medium"
        # # size_name = "small"
        # zone_name_list = ["AZ_Tucson_Large", "WA_Tacoma_Large", "AL_Dothan_Large", "LA_Alexandria_Large"]
        # # zone_name_list = ["AZ_Tucson_Small", "WA_Tacoma_Small", "AL_Dothan_Small", "IA_Johnston_Small",
        # #                   "LA_Alexandria_Small", "AK_Anchorage_Small", "MT_Greatfalls_Small"]
        # # zone_name_list = ["AZ_Tucson_Medium", "WA_Tacoma_Medium", "AL_Dothan_Medium", "IA_Johnston_Medium", "LA_Alexandria_Medium", "AK_Anchorage_Medium", "MT_Greatfalls_Medium"]  # ["AZ_Tucson_Medium", "WA_Tacoma_Medium"]
        # # NOTE: PS: The below variable should change to years if the input are folders with years as difference instead of climate zones
        # # AZ_Tucson_Large_Main_dataset_run3_fl - 2B
        # # AK_Anchorage_Large_Main_dataset_run3_fl - 7
        # # LA_Alexandria_Large_Main_dataset_run3_fl - 2A
        # # IA_Johnston_Large_Main_dataset_run3_fl - 5A
        # # AL_Dothan_Large_Main_dataset_run3_fl - 3A
        # # MT_Greatfalls_Large_Main_dataset_run3_fl - 6B
        # # WA_Tacoma_Large_Main_dataset_run3_fl - 5C
        # x_label_for_barplot = ["Zone 2B", "Zone 5C", "Zone 3A", "Zone 2A"]
        # # x_label_for_barplot = ["Zone 2B", "Zone 5C", "Zone 3A", "Zone 5A", "Zone 2A", "Zone 7", "Zone 6B"]
        # x_title = "Climate zones"  # "Years
        # state_list = ["az", "wa", "al", "la"]
        # # state_list = ["az", "wa", "al", "ia", "la", "ak", "mt"]
        # folder_list = [17, 17, 17, 17]
        # # folder_list = [2, 2, 2, 2, 2, 2, 2]
        # # folder_list = [10, 10, 10, 10, 10, 10, 10]
        # # sensitivity_suffix = "smallest_xfrmr_first"
        # sensitivity_suffix = "tempdelete"
        plot_plotly = True
        basecase_peak_demand_all_folders = []
        uncontrolled_peak_demand_all_folders = []
        controlled_peak_demand_all_folders = []
        for iiidxx, zone_name in enumerate(zone_name_list):
            state = state_list[iiidxx]
            total_folders = folder_list[iiidxx]
            folder_names = [f"{zone_name}_{customsuffix}_{ji+1}_fl" for ji in range(0, total_folders)]
            folder_name = f"aggregated_data_{zone_name}_{state}_{customsuffix}_{sensitivity_suffix}_threshold{threshold_cutoff}_{date_name}_v2"
            # folder_name = f"aggregated_data_{zone_name}_{state}_{customsuffix}_{sensitivity_suffix}"
            input_1a = f"{zone_name}_{customsuffix}"


            plots_folder_name = f"{folder_name}_plots_testingcode"
            base_case_list =[]
            for name in folder_names:

                os.chdir(r'/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/')

                base_case = r'/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/' + name
                base_case_list.append(base_case)
            case_config_name = 'generate_case_config.json'





            Load_House_data = False
            Load_Meter_data = True

            global tick_font, label_font, legend_font
            tick_font = 17
            label_font = 22
            legend_font = 17

            directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
            if not os.path.exists(directory):
                os.makedirs(directory)

            # directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{folder_name}_uncontrol_plots"
            # if not os.path.exists(directory):
            #     os.makedirs(directory)
            #
            # directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{folder_name}_control_plots"
            # if not os.path.exists(directory):
            #     os.makedirs(directory)

            ###########################################################################
            ####################### Transformer loading ###############################
            ##########################################################################

            (year_list, total_basecase_xfrmrs_with_evs, total_uncontrolled_vios, total_controlled_vios,
             merged_df_uncontrolled, total_basecase_vios, merged_df_uncontrolled_in_kws, df_final_divided_inkws_hourly,
             all_year_ev_uncontrolled_laod_in_kw, merged_df_controlled_in_kws, all_year_ev_controlled_laod_in_kw,
             total_xfrmrs_need_replacing_120, replace_df) =\
                plot1a_task_percentoverload(input_1a, GLD_prefix, [total_folders]*3,
                                                                                        plots_folder_name,
                                                                                        extrafoldersexist, plot_plotly,
                                            replace_threshold=120)

            # NOTE TO SELF AND PS: SAVE THE VARIABLE "replace_df" to csv and share with Christine!!! FIX THE RANDOM
            # EV ASSIGNMENT ISSUE AND RERUN STUDIES AND PLOTS AND GENERATE THIS SAID CSV FILE AND GIVE TO CHRISTINE
            # ASAP!!!!!!

            # to avoid mismatch of 100 and 100.1 logic. otherwise creates a plotting bug (results are accurate) - quick fix made for quick result generation
            total_controlled_vios = total_basecase_vios

            # df_final=overload_calculation(base_case_list,GLD_prefix,plots_folder_name)

            # Plot the xfrmr overloading here
            # (columns=["# timestamp", "month", "year_i", "day", "hour"])


            ###########################################################################
            ####################### Load DER stack data ###############################
            ###########################################################################
            # for dso in dso_range:
            #    der_load_stack(dso, day_range, base_case, GLD_prefix, metadata_path)


            ###########################################################################
            #################@###### Load Substation Data #############################
            ###########################################################################

            # extract substation data for base case
            substation_data_df,weather_df, peak_substation_load = Load_substation_data(dso, day_range, base_case_list, plots_folder_name, plot_load=True, plot_weather=True) #GOOD
            basecase_peak_demand_all_folders.append(peak_substation_load)

            # plot the count of EV transformers with violations for several years for a given climate zone
            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Multiyear_barplot_EVxfmrviolation_percent_{plots_folder_name}.html"
            total_basecase_vios_y = [(val/total_basecase_xfrmrs_with_evs[idx])*100 for idx, val in enumerate(total_basecase_vios)]
            total_uncontrolled_vios_y = [(val / total_basecase_xfrmrs_with_evs[idx]) * 100 for idx, val in
                                     enumerate(total_uncontrolled_vios)]
            total_controlled_vios_y = [(val / total_basecase_xfrmrs_with_evs[idx]) * 100 for idx, val in
                                     enumerate(total_controlled_vios)]
            title = "Percentage of EV transformers with violations"
            x_title = "Years"
            year_list = [int(x) for x in year_list]
            idx_sort = list(np.argsort(year_list))
            year_list = [year_list[x] for x in idx_sort]
            total_basecase_vios_y = [total_basecase_vios_y[x] for x in idx_sort]
            total_uncontrolled_vios_y = [total_uncontrolled_vios_y[x] for x in idx_sort]
            total_controlled_vios_y = [total_controlled_vios_y[x] for x in idx_sort]

            total_basecase_vios = [total_basecase_vios[x] for x in idx_sort]
            total_uncontrolled_vios = [total_uncontrolled_vios[x] for x in idx_sort]
            total_controlled_vios = [total_controlled_vios[x] for x in idx_sort]
            size_val = 28
            plot_histogram_plotly(plots_folder_name, total_basecase_vios_y,
                                      total_uncontrolled_vios_y, total_controlled_vios_y,
                                      year_list, title, x_title, file_to_save, size_val, total_basecase_xfrmrs_with_evs[0])
            # same plot as bove but the y-axis is count instead of percentage
            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Multiyear_barplot_EVxfmrviolation_count_{plots_folder_name}.html"
            title = "Count of EV transformers with overloads"
            x_title = "Years"
            year_list = [int(x) for x in year_list]
            size_val = 18


            plot_histogram_plotly(plots_folder_name, total_basecase_vios,
                                  total_uncontrolled_vios, total_controlled_vios,
                                  year_list, title, x_title, file_to_save, size_val, total_basecase_xfrmrs_with_evs[0])

            # below piece code of written to remove the base case violations from the plot results based on feedback
            # received.
            total_uncontrolled_vios = [x-total_basecase_vios[ixxx] for ixxx, x in enumerate(total_uncontrolled_vios)]
            total_controlled_vios = [x-total_basecase_vios[ixxx] for ixxx, x in enumerate(total_controlled_vios)]
            total_basecase_vios = [0]*len(total_uncontrolled_vios)
            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Multiyear_barplot_EVxfmrviolation_count_{plots_folder_name}_v2.html"
            plot_histogram_plotly(plots_folder_name, total_basecase_vios,
                                  total_uncontrolled_vios, total_controlled_vios,
                                  year_list, title, x_title, file_to_save, size_val, total_basecase_xfrmrs_with_evs[0])

            # plot time series substation demand for all years
            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Multiyear_lineplots_uncontrolled_in_kws_{plots_folder_name}.html"
            title = "Demand in KWs"
            x_title = "Timestamp"
            year_list = sorted(year_list)
            merged_df_uncontrolled_in_kws = merged_df_uncontrolled_in_kws.sort_values(by="# timestamp", ascending=True)
            # time_list = []
            # data_list = []
            df_here = pd.DataFrame()
            # for uncontrolled EV demand merged with base case for several years
            for x in year_list:
                line_to_plot = list(merged_df_uncontrolled_in_kws[merged_df_uncontrolled_in_kws["year_i"] == x].sum(axis=1, numeric_only=True))
                # data_list.append(line_to_plot)
                time_here = list(merged_df_uncontrolled_in_kws["# timestamp"].astype(str).str[5:].str[:-6])
                # time_list.append(time_here)
                current_df = pd.DataFrame(list(zip(time_here, line_to_plot)), columns=["time", "data"])
                current_df["category"] = str(x)
                df_here = pd.concat([df_here, current_df])
            # for base case info
            df_final_divided_inkws_hourly = df_final_divided_inkws_hourly.reset_index(drop=True)
            df_final_divided_inkws_hourly = df_final_divided_inkws_hourly.sort_values(by="# timestamp", ascending=True)
            base_data_in_kws = list(df_final_divided_inkws_hourly.sum(axis=1, numeric_only=True))
            time_stamp_info_basecase = list(df_final_divided_inkws_hourly["# timestamp"].astype(str).str[5:].str[:-6])
            current_df = pd.DataFrame(list(zip(time_stamp_info_basecase, base_data_in_kws)), columns=["time", "data"])
            current_df["category"] = "basecase_with_uncontrolled_EV"
            df_here = pd.concat([df_here, current_df])

            fig = px.line(df_here, x="time", y="data", color='category')
            fig.update_layout(
                yaxis=dict(
                    title=title,
                    titlefont_size=30,
                    tickfont_size=28,
                ),
                xaxis=dict(
                    title=x_title,
                    titlefont_size=30,
                    tickfont_size=28,
                ),
                font=dict(
                    family="Courier New, monospace",
                    size=30,
                    color="RebeccaPurple"
                ),
                paper_bgcolor='rgba(255,255,255,1)',
                plot_bgcolor='rgba(255,255,255,1)'
            )
            fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
            fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
            plotly.offline.plot(fig,
                                filename=file_to_save, auto_open=False)

            # plot time series substation demand for all years
            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Multiyear_lineplots_controlled_in_kws_{plots_folder_name}.html"
            title = "Demand in KWs"
            x_title = "Timestamp"
            year_list = sorted(year_list)
            merged_df_controlled_in_kws = merged_df_controlled_in_kws.sort_values(by="# timestamp", ascending=True)
            # time_list = []
            # data_list = []
            df_here = pd.DataFrame()
            # for uncontrolled EV demand merged with base case for several years
            for x in year_list:
                line_to_plot = list(
                    merged_df_controlled_in_kws[merged_df_controlled_in_kws["year_i"] == x].sum(axis=1,
                                                                                                    numeric_only=True))
                # data_list.append(line_to_plot)
                time_here = list(merged_df_controlled_in_kws["# timestamp"].astype(str).str[5:].str[:-6])
                # time_list.append(time_here)
                current_df = pd.DataFrame(list(zip(time_here, line_to_plot)), columns=["time", "data"])
                current_df["category"] = str(x)
                df_here = pd.concat([df_here, current_df])
            # for base case info
            df_final_divided_inkws_hourly = df_final_divided_inkws_hourly.reset_index(drop=True)
            df_final_divided_inkws_hourly = df_final_divided_inkws_hourly.sort_values(by="# timestamp", ascending=True)
            base_data_in_kws = list(df_final_divided_inkws_hourly.sum(axis=1, numeric_only=True))
            time_stamp_info_basecase = list(df_final_divided_inkws_hourly["# timestamp"].astype(str).str[5:].str[:-6])
            current_df = pd.DataFrame(list(zip(time_stamp_info_basecase, base_data_in_kws)), columns=["time", "data"])
            current_df["category"] = "basecase_with_Controlled_EV"
            df_here = pd.concat([df_here, current_df])

            fig = px.line(df_here, x="time", y="data", color='category')
            fig.update_layout(
                yaxis=dict(
                    title=title,
                    titlefont_size=30,
                    tickfont_size=28,
                ),
                xaxis=dict(
                    title=x_title,
                    titlefont_size=30,
                    tickfont_size=28,
                ),
                font=dict(
                    family="Courier New, monospace",
                    size=30,
                    color="RebeccaPurple"
                ),
                paper_bgcolor='rgba(255,255,255,1)',
                plot_bgcolor='rgba(255,255,255,1)'
            )
            fig.update_xaxes(showline=True, linewidth=4, linecolor='black')
            fig.update_yaxes(showline=True, linewidth=4, linecolor='black')
            plotly.offline.plot(fig,
                                filename=file_to_save, auto_open=False)

            # extract peak demad for uncontrolled and controlled cases for all years
            uncontrolled_peak_demand_all_years = []
            controlled_peak_demand_all_years = []
            basecase_peak_demand_all_years = []
            all_year_ev_uncontrolled_laod_in_kw = all_year_ev_uncontrolled_laod_in_kw.drop(columns=["year_i", "day",
                                                                                                    "hour"])
            all_year_ev_controlled_laod_in_kw = all_year_ev_controlled_laod_in_kw.drop(columns=["year_i", "day",
                                                                                                "hour"])
            df_lst_uncontrolled_scenario_base_EV_demand = []
            df_lst_controlled_scenario_base_EV_demand = []

            for x in year_list:
                mini_list1 = []
                mini_list2 = []
                k_df = all_year_ev_uncontrolled_laod_in_kw[all_year_ev_uncontrolled_laod_in_kw["Year"] == str(x)]
                k_df = k_df.drop(columns=["Year"])
                k = k_df.sum(axis=1).max()
                uncontrolled_peak_demand_all_years.append(k/1000)   # convert to MWs

                kc_df = all_year_ev_controlled_laod_in_kw[all_year_ev_controlled_laod_in_kw["Year"] == str(x)]
                kc_df = kc_df.drop(columns=["Year"])
                kc = kc_df.sum(axis=1).max()
                controlled_peak_demand_all_years.append(kc/1000)  # convert to MWs
                basecase_peak_demand_all_years.append(0)

                # extract required data for grouped stack bar plots
                # need to find coincident peak information and use that
                unc_df = k_df.sum(axis=1, numeric_only=True)
                idxmax_uncontrolled = unc_df.idxmax()
                max_uncontrolled = unc_df.max()
                # get max baseload at coinicdent peak of uncontrolled
                base_uncontrolled = base_data_in_kws[idxmax_uncontrolled]
                # mini_list1.append(x)
                mini_list1.append(base_uncontrolled / 1000)
                mini_list1.append(max_uncontrolled/1000)
                df_lst_uncontrolled_scenario_base_EV_demand.append(mini_list1)  # convert to mw

                c_df = kc_df.sum(axis=1, numeric_only=True)
                idxmax_controlled = c_df.idxmax()
                max_controlled = c_df.max()
                # get max baseload at coinicdent peak of controlled
                base_controlled = base_data_in_kws[idxmax_controlled]
                # mini_list2.append(x)
                mini_list2.append(base_controlled / 1000)
                mini_list2.append(max_controlled / 1000)
                df_lst_controlled_scenario_base_EV_demand.append(mini_list2)  # convert to mw
                # df_lst_controlled_scenario_EV_demand.append(max_controlled/1000)
                # df_lst_controlled_scenario_base_demand.append(base_controlled/1000) # convert to mw

            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Multiyear_barplot_EV_peak_demand_{plots_folder_name}.html"
            title = "Peak EV demand in MWs"
            x_title = "Years"
            year_list = [int(x) for x in year_list]
            # scenario = "Uncontrolled scenario"
            # plot_histogram_plotly_1plot(plots_folder_name, uncontrolled_peak_demand_all_years, year_list, title,
            #                             x_title, file_to_save, scenario)
            # peak ev demand
            plot_histogram_plotly(plots_folder_name, basecase_peak_demand_all_years,
                                  uncontrolled_peak_demand_all_years, controlled_peak_demand_all_years,
                                  year_list, title, x_title, file_to_save, size_val, 'dont care')

            scenario = ""
            title = "Transformer upgrades"
            x_title = "Years"
            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Multiyear_xfrmr_upgrade_{plots_folder_name}.html"
            total_xfrmrs_need_replacing_120_h = list(np.cumsum(total_xfrmrs_need_replacing_120))
            plot_histogram_plotly_1plot(plots_folder_name, total_xfrmrs_need_replacing_120_h, year_list, title,
                                        x_title, file_to_save, scenario)

            # plot grouped stack plot of base+ev demand for uncontrolled and controlled
            uncontrolled_np = np.array(df_lst_uncontrolled_scenario_base_EV_demand)
            controlled_np = np.array(df_lst_controlled_scenario_base_EV_demand)

            coincident_peak = False  # IMPORTANT FLAG TO MODIFYING THE BELOW PLOT
            df1_uncontrolled = pd.DataFrame(uncontrolled_np, index=[str(x) for x in year_list], columns=["Base Load", "EV Demand"])
            df2_controlled = pd.DataFrame(controlled_np, index=[str(x) for x in year_list], columns=["Base Load", "EV Demand"])
            base_building_peak_demand = df_final_divided_inkws_hourly.sum(axis=1).max()
            # bs_ld = [base_building_peak_demand]*controlled_np.shape[0]
            # ev_ld = [0]*controlled_np.shape[0]
            # desrd_np = np.column_stack((bs_ld, ev_ld))

            title = "Demand in MWs"
            x_title = "Years"
            file_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/Uncontrolled_stack_plot_with_baseload_line_{plots_folder_name}.html"
            plot_stacked_plot_for_uncontrolled_ev(year_list, list(df1_uncontrolled["Base Load"]), list(df1_uncontrolled["EV Demand"]), size_val, file_to_save,
                                                  base_building_peak_demand, title, x_title)

            if not coincident_peak:
                base_building_peak_demand = df_final_divided_inkws_hourly.sum(axis=1).max()
                # replace coincident building peak demand with the peak(across one week) value
                df1_uncontrolled["Base Load"] = base_building_peak_demand/1000  # in mw
                df2_controlled["Base Load"] = base_building_peak_demand/1000  # in mw

            name_to_save = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_grouped_stack_plot.pdf"
            plot_clustered_stacked([df1_uncontrolled, df2_controlled], name_to_save,["Uncontrolled scenario", "Controlled scenario"], cmap=plt.cm.viridis)

            k = 1
