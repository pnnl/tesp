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


def load_weather_data(dir_path, folder_prefix, dso_num, day_num):
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
    data = pd.read_csv(dir_path + '/' + weather_city + '/weather.dat')

    data['datetime'] = data['datetime'].apply(pd.to_datetime)
    data = data.set_index(['datetime'])
    # Determine first day of simulation and resulting slice to take
    #case_config = load_json(dir_path, 'case_config_' + dso_num + '.json')
    # testing with new weather data
    case_config = load_json(dir_path, 'case_config_' + dso_num + '.json')

    sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')
    start_time = sim_start + timedelta(days=int(day_num) - 1)
    stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
    weather_df = data.loc[start_time:stop_time, :]

    return weather_df

def Load_substation_data(dso, day_range, case, plots_folder_name, plot_load= False, plot_weather=False):
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
    weather_df = pd.DataFrame()

    for day in day_range:
        # substation_meta_df, substation_df = load_system_data(case, '/Substation_', str(dso), str(day), 'transformer')
        substation_meta_df, substation_df = load_system_data(case, '/Substation_', str(dso), str(day), 'substation')
        if starting_load_dataframe == 1:
            temp_df = pd.DataFrame()
            temp_df['Substation Actual'] = substation_df['real_power_avg'].values /1000 # .values.tolist()
            temp_df['Substation Loss'] = substation_df['real_power_losses_avg'].values /1000
            temp_df.index = [datetime.strptime(date.split(' CDT')[0], "%Y-%m-%d %H:%M:%S") for date in substation_df.date]
            dsoload_df = temp_df
        else:
            temp_df = pd.DataFrame()
            temp_df['Substation Actual'] = substation_df['real_power_avg'].values /1000
            temp_df['Substation Loss'] = substation_df['real_power_losses_avg'].values /1000
            temp_df.index = [datetime.strptime(date.split(' CDT')[0], "%Y-%m-%d %H:%M:%S") for date in substation_df.date]
            dsoload_df = pd.concat([dsoload_df, temp_df], axis=0)
        starting_load_dataframe += 1

        #################### Collecting Weather Data ####################
        if plot_weather:
            if starting_weather_dataframe == 1:
                weather_df = load_weather_data(case, '/DSO_', str(dso), str(day))
            else:
                temp_weather_df = load_weather_data(case, '/DSO_', str(dso), str(day))
                weather_df = pd.concat([weather_df, temp_weather_df], axis=0)
            starting_weather_dataframe += 1

    directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
    if not os.path.exists(directory):
        os.makedirs(directory)

    if plot_load:
        fig, ax = plt.subplots(figsize=(12,6))
        fig.suptitle('DSO ' + str(dso) + ' Net Load')
        ax.set_xlabel('Time of day (hours)',  size=label_font)
        ax.set_ylabel('Substation Load (kW)', size=label_font)
        ax.plot( dsoload_df.index[3:], dsoload_df['Substation Actual'][3:], linewidth=2, label='Substation Load')
        ax.plot( dsoload_df.index[3:], dsoload_df['Substation Actual'][3:]-dsoload_df['Substation Loss'][3:], linewidth=2, label='Subsation Load - loss')
        # Only label every 24th value (every 2 hours)
        ticks_to_use = dsoload_df.index[::24]
        # Set format of labels (note year not excluded as requested)
        labels = [i.strftime(":%M") for i in ticks_to_use]
        # Now set the ticks and labels
        # ax1.set_xticks(ticks_to_use)
        # ax1.set_xticklabels(labels)
        plt.legend(loc='upper left', prop={'size': legend_font})
        if plot_weather:
            ax2 = ax.twinx()  # instantiate a second axes that shares the same x-axis
            color = 'tab:red'
            ax2.set_ylabel('Temperature (F)', color=color, size=label_font)  # we already handled the x-label with ax1
            ax2.plot(weather_df['temperature'], color=color, linewidth=2, linestyle=':', label='Weather')
            ax2.tick_params(axis='y', labelcolor=color)
            # ax2.set_xticks(ticks_to_use)
            # ax1.set_xticklabels(labels)
        ax.grid()
        plt.legend(loc='lower left', prop={'size': legend_font})
        # ax.tick_params(axis='both', which='major', labelsize=tick_font)
        # fig.tight_layout()
        # fig.show()
        fig.savefig(
            f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_Substation_plot.pdf",
            bbox_inches='tight')
    return dsoload_df

def get_attributes_from_metrics_data(data_base_df, objects, attrib):

    data_att_df = pd.DataFrame(columns=['Datetime']+ objects)
    
    for obj in objects:
        idx = data_base_df.index[data_base_df['name'] == obj].tolist()
        data_att_df[obj] = data_base_df[attrib][idx].values
    data_att_df['Datetime'] = pd.to_datetime(data_base_df['date'][idx].values, format='%Y-%m-%d %H:%M:%S CDT')

    return data_att_df


def sum_all_csv_Files(path):
    csv_files = [f for f in os.listdir(path) if f.endswith('.csv') and 'loads_power' in f][:3]
    df_1 = pd.read_csv(os.path.join(path, csv_files[0]), skiprows=8)
    df1 = df_1.iloc[:, 1:]
    df_2 = pd.read_csv(os.path.join(path, csv_files[1]), skiprows=8)
    df2 = df_2.iloc[:, 1:]
    df_3 = pd.read_csv(os.path.join(path, csv_files[2]), skiprows=8)
    df3 = df_3.iloc[:, 1:]

    df_final = pd.concat([df1, df2, df3], axis=1)
    # df_final2 = df_final.iloc[:, 1:]
    df_final = df_final.groupby(df_final.columns, axis=1).sum()
    df_final = pd.concat([df_final, df_1["# timestamp"].to_frame()], axis=1)
    return df_final


def transformer_map(path_to_file):
    with open(path_to_file + 'model.json', 'r') as fp:
        model = json.load(fp)

    with open(path_to_file + 'com_loads.json', 'r') as fp:
        comm_loads = json.load(fp)

    with open(path_to_file + 'xfused.json', 'r') as fp:
        xfused = json.load(fp)

    transformer_name_connected_to_load = []
    transformer_config_list_type = []

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
    return load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict

def flatten(xss):
    return [x for xs in xss for x in xs]

def overload_calculation(path, plots_folder_name):
    df_final = sum_all_csv_Files(path)
    load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict = transformer_map(path)
    # if len(df_final.columns) != len(transformer_rating_dct):
    #     raise ValueError("DataFrame and dictionary have different numbers of columns.")
    comm_load_names0 = list(df_final.columns)
    comm_load_names = [x for x in comm_load_names0 if x != '# timestamp']
    df_divided = pd.DataFrame(data={col: (df_final[col] / config_to_power_rating_map_dict[load_to_xfrmr_config_map_dict[col]])*100 for col in comm_load_names})
    df_divided2 = pd.concat([df_divided, df_final["# timestamp"].to_frame()], axis= 1)
    df_divided2.to_csv(path + 'transformer_overloading.csv', index=False)

    # histogram based on overloading percentage (considering all transformers overloads)
    data_list = flatten(df_divided.values.tolist())
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=data_list,  histnorm='percent', marker_color='#330C73', opacity=0.75))
    # fig.update_traces(histnorm= "probability density", selector = dict(type='histogram'))
    fig.update_layout(
        title_text='Transformer overloading - probability density',  # title of plot
        xaxis_title_text='Transformer loading in percentage',  # xaxis label
        yaxis_title_text='Percent of total transformers on grid',  # yaxis label
        font_family="Courier New",
        font_color="blue",
        font_size = 18,
        bargap=0.2,  # gap between bars of adjacent location coordinates
        bargroupgap=0.1  # gap between bars of the same location coordinates
    )
    plotly.offline.plot(fig, filename=f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/{plots_folder_name}_HistogramOverloadPercent.html")



if __name__ == '__main__':
    pd.set_option('display.max_columns', 50)
    day_range = range(1, 3)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    dso_range = range(1, 2)  # 1 = DSO 1 (end range should be last DSO +1)
    dso = 1
    
    curr_dir = os.getcwd()
    # / home / gudd172 / tesp / repository / tesp / examples / analysis / dsot / code / lean_aug_8_v3_fl_ev
    metadata_path = '/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/data'
    # folder_name = 'small_grid_only_residential_fl'
    # folder_name = 'medium_grid_only_residential_fl'
    # folder_name = 'large_grid_only_residential_fl'
    # folder_name = 'medium_grid_try2_july_only_residential_fl'
    # folder_name = 'large_twogrids_final_fl'
    # folder_name = 'medium_final_withCommercial_fl'
    # folder_name = 'medium_final_withCommercial_outTempChng_fl'
    # folder_name = 'medium_final_withCommercial_inTempChng_fl'
    folder_name = 'AK_Anchorage_Large_Main_dataset_run3_fl'
    # AZ_Tucson_Large_Main_dataset_run3_fl - 2B
    # AK_Anchorage_Large_Main_dataset_run3_fl - 7
    # LA_Alexandria_Large_Main_dataset_run3_fl - 2A
    # IA_Johnston_Large_Main_dataset_run3_fl - 5A
    # AL_Dothan_Large_Main_dataset_run3_fl - 3A
    # MT_Greatfalls_Large_Main_dataset_run3_fl - 6B
    # WA_Tacoma_Large_Main_dataset_run3_fl - 5C

    plots_folder_name = f"{folder_name}_plots"

    base_case = r'/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/' + folder_name
    case_config_name = 'generate_case_config.json'
     
     
    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'
    
    
    Load_House_data = False
    Load_Meter_data = True
    
    global tick_font, label_font, legend_font
    tick_font = 17
    label_font = 22
    legend_font = 17

    directory = f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}"
    if not os.path.exists(directory):
        os.makedirs(directory)

    ###########################################################################
    ####################### Transformer loading ###############################
    ##########################################################################
    overload_calculation(base_case+GLD_prefix+'1/', plots_folder_name)


    ###########################################################################
    ####################### Load DER stack data ###############################
    ###########################################################################
    # for dso in dso_range:
    #    der_load_stack(dso, day_range, base_case, GLD_prefix, metadata_path)
    
    
    ###########################################################################
    #################@###### Load Substation Data #############################
    ###########################################################################
    
    print("Processing metrics_substation.h5 data ....")
    substation_data_df = Load_substation_data(dso, day_range, base_case, plots_folder_name, plot_load=True, plot_weather=True)
    
    
    ###########################################################################
    ########################### Load Agent Data ###############################
    ###########################################################################
    agent_file = (base_case + agent_prefix + str(dso) + '/Substation_' +  str(dso) + '_agent_dict.json')
    f = open (agent_file, "r")
    # Reading from file
    agent_data = json.loads(f.read())
    houses = list(agent_data['hvacs'].keys())
    meters = list(agent_data['site_agent'].keys())

    ###########################################################################
    ########################### Load House Data ###############################
    ###########################################################################
    print("Processing metrics_house.h5 data ....")
    hse_attr = 'air_temperature_avg' ### Adjust the attribute that you want to collect
    if Load_House_data:
        house_att_df = pd.DataFrame()
        for day in day_range:
            meta_house_df_base, data_house_df_base = load_system_data(base_case, '/Substation_', str(dso), str(day), 'house')
            # print('List of Attributes in house.h5 data:  ... \n {}'.format(meta_house_df_base['name'].values))
            if house_att_df.empty:
                house_att_df = get_attributes_from_metrics_data(data_house_df_base, houses, hse_attr)
            else:
                temp1 = get_attributes_from_metrics_data(data_house_df_base, houses, hse_attr)
                # house_att_df = house_att_df.append(temp1)
                house_att_df = pd.concat([house_att_df, temp1])
    ###########################################################################
    ########################### Load Meter Data ###############################
    ###########################################################################
    print("Processing metrics_billing_meter.h5 data ....")
    meter_attr = 'real_power_avg' ### Adjust the attribute that you want to collect
    if Load_Meter_data:
        meter_att_df = pd.DataFrame()
        for day in day_range:
            meta_meter_df_base, data_meter_df_base = load_system_data(base_case, '/Substation_', str(dso), str(day), 'meter')
            print('List of Attributes in meter.h5 data:  ... \n {}'.format(meta_meter_df_base['name'].values))
            if meter_att_df.empty:
                meter_att_df = get_attributes_from_metrics_data(data_meter_df_base, meters, meter_attr)
            else:
                temp2 = get_attributes_from_metrics_data(data_meter_df_base, meters, meter_attr)
                # meter_att_df = meter_att_df.append(temp2)
                meter_att_df = pd.concat([meter_att_df, temp2], ignore_index=True)




    ###########################################################################
    ############################ Sample Plotting ##############################
    ###########################################################################
    #################### Plotting House Measurements ##########################
    # no_objs_plot = 3
    # fig, ax = plt.subplots(figsize=(12,6))
    # ax.plot( house_att_df['Datetime'], house_att_df.iloc[:, 1:no_objs_plot+1])
    # ax.set_xlabel('Time of day (hours)', size=label_font)
    # ax.set_ylabel('Temperature (${^\circ}F$)', size=label_font)
    # ax.tick_params(axis='both', which='major', labelsize=tick_font)
    # # plt.legend(loc='upper left', prop={'size': legend_font})
    # ax.grid()
    # fig.tight_layout()

    #################### Plotting Meter Measurements ##########################
    no_objs_plot = 3
    fig, ax = plt.subplots(figsize=(12,6))
    ax.plot( meter_att_df['Datetime'], meter_att_df.iloc[:, 1:no_objs_plot+1]/1000)
    ax.set_xlabel('Time of day (hours)', size=label_font)
    ax.set_ylabel('Meter Load (kW)', size=label_font)
    ax.tick_params(axis='both', which='major', labelsize=tick_font)
    # plt.legend(loc='upper left', prop={'size': legend_font})
    ax.grid()
    # fig.tight_layout()
    fig.savefig(f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/meter_load.pdf",
                bbox_inches='tight')

    no_objs_plot = 4
    fig, ax = plt.subplots(figsize=(12,6))
    for i in range(no_objs_plot):
        ax.plot(meter_att_df['Datetime'], meter_att_df.iloc[:, i+1]/max(meter_att_df.iloc[0:287, i+1]))
        ax.set_xlabel('Time of day (hours)', size=label_font)
        ax.set_ylabel('Meter Load Factor (pu)', size=label_font)
        ax.tick_params(axis='both', which='major', labelsize=tick_font)
        # ax.set_xlim([datetime(2021, 2, 16), datetime(2021, 2, 17)])
        # plt.legend(loc='upper left', prop={'size': legend_font})
        ax.grid()
        # fig.tight_layout()
        fig.savefig(f"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/{plots_folder_name}/meter_load_factor_fig_{i}.pdf", bbox_inches='tight')


