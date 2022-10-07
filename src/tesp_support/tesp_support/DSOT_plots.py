# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: DSOT_plots.py
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
import copy

plt.switch_backend('Agg')
cache_output = {}
cache_df = {}


def TicTocGenerator():
    # Generator that returns time differences
    ti = 0           # initial time
    tf = datetime.now() # final time
    while True:
        ti = tf
        tf = datetime.now()
        yield tf-ti # returns the time difference


TicToc = TicTocGenerator()  # create an instance of the TicTocGen generator


# This will be the main function through which we define both tic() and toc()
def toc(tempBool=True):
    # Prints the time difference yielded by generator instance TicToc
    tempTimeInterval = next(TicToc)
    if tempBool:
        print("Elapsed time: %f seconds.\n" %tempTimeInterval.total_seconds())


def tic():
    # Records a time in TicToc, marks the beginning of a time interval
    toc(False)


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


def get_date(dir_path, dso, day):
    """Utility to return start time (datetime format) of simulation day (str) in question"""
    # Determine first day of simulation and the date of the day requested
    case_config = load_json(dir_path, 'case_config_' + dso + '.json')
    sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')
    date = sim_start + timedelta(days=int(day) - 1)
    return date


def customer_meta_data(glm_meta, agent_meta, dso_metadata_path):
    """Update GLM dictionary with information from agent dictionary needed for customer billing.
    Arguments:
        glm_meta (dict): dictionary of GridLAB-D information
        agent_meta (dict): dictionary of transactive agent information
        dso_metadata_path (str): location of metadata for commercial buildings
    Returns:
        glm_meta (dict): dictionary of GridLAB-D information

        """
    # Determine tariff rate class of each meter up front.
    commdata = load_json(dso_metadata_path, 'DSOT_commercial_metadata.json')
    commbldglist = []
    # TODO: this should be done in prepare case and read in.
    for bldg in commdata['building_model_specifics']:
        commbldglist.append(bldg)
    residbldglist = ['SINGLE_FAMILY', 'MOBILE_HOME', 'APARTMENTS', 'MULTI_FAMILY']

    for each in glm_meta['billingmeters']:
        glm_meta['billingmeters'][each]['tariff_class'] = None
        for bldg in commbldglist:
            if bldg in glm_meta['billingmeters'][each]['building_type']:
                glm_meta['billingmeters'][each]['tariff_class'] = 'commercial'
        for bldg in residbldglist:
            if bldg in glm_meta['billingmeters'][each]['building_type']:
                glm_meta['billingmeters'][each]['tariff_class'] = 'residential'
        if glm_meta['billingmeters'][each]['building_type'] == 'UNKNOWN':
            glm_meta['billingmeters'][each]['tariff_class'] = 'industrial'
        if glm_meta['billingmeters'][each]['tariff_class'] is None:
            raise Exception('Tariff class was not successfully determined for meter ' + each)

    for meter in glm_meta['billingmeters']:
        glm_meta['billingmeters'][meter]['num_zones'] = 0
        glm_meta['billingmeters'][meter]['sqft'] = 0
        glm_meta['billingmeters'][meter]['battery_capacity'] = 0
        glm_meta['billingmeters'][meter]['pv_capacity'] = 0
        glm_meta['billingmeters'][meter]['cust_participating'] = False
        glm_meta['billingmeters'][meter]['hvac_participating'] = False
        glm_meta['billingmeters'][meter]['wh_participating'] = False
        glm_meta['billingmeters'][meter]['batt_participating'] = False
        glm_meta['billingmeters'][meter]['ev_participating'] = False
        glm_meta['billingmeters'][meter]['pv_participating'] = False
        glm_meta['billingmeters'][meter]['slider_setting'] = None
        glm_meta['billingmeters'][meter]['cooling'] = 'N/A'
        glm_meta['billingmeters'][meter]['heating'] = 'N/A'
        glm_meta['billingmeters'][meter]['wh_gallons'] = 'N/A'

    # Determine PV ratings if any
    for inverter in glm_meta['inverters']:
        if 'isol' in inverter:
            meter = glm_meta['inverters'][inverter]['billingmeter_id']
            glm_meta['billingmeters'][meter]['pv_capacity'] = glm_meta['inverters'][inverter]['rated_W'] / 1000

    for meter in agent_meta['site_agent']:
        glm_meta['billingmeters'][meter]['cust_participating'] = agent_meta['site_agent'][meter]['participating']
        glm_meta['billingmeters'][meter]['slider_setting'] = agent_meta['site_agent'][meter]['slider_settings']['customer']

    for hvac in agent_meta['hvacs']:
        meter = agent_meta['hvacs'][hvac]['meterName']
        glm_meta['billingmeters'][meter]['hvac_participating'] = agent_meta['hvacs'][hvac]['cooling_participating'] or \
                                                                 agent_meta['hvacs'][hvac]['heating_participating']
        glm_meta['billingmeters'][meter]['num_zones'] += 1
        glm_meta['billingmeters'][meter]['sqft'] += glm_meta['houses'][hvac]['sqft']

    for house in glm_meta['houses']:
        meter = glm_meta['houses'][house]['billingmeter_id']
        glm_meta['billingmeters'][meter]['cooling'] = glm_meta['houses'][house]['cooling']
        glm_meta['billingmeters'][meter]['heating'] = glm_meta['houses'][house]['heating']
        glm_meta['billingmeters'][meter]['wh_gallons'] = glm_meta['houses'][house]['wh_gallons']

    for wh in agent_meta['water_heaters']:
        meter = agent_meta['water_heaters'][wh]['meterName']
        glm_meta['billingmeters'][meter]['wh_participating'] = agent_meta['water_heaters'][wh]['participating']

    for batt in agent_meta['batteries']:
        meter = agent_meta['batteries'][batt]['meterName']
        glm_meta['billingmeters'][meter]['battery_capacity'] = agent_meta['batteries'][batt]['capacity'] / 1000
        glm_meta['billingmeters'][meter]['batt_participating'] = agent_meta['batteries'][batt]['participating']

    return glm_meta


def load_gen_data(dir_path, gen_name, day_range):
    """Utility to open h5 files for agent data.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        agent_name (str): name of agent data to load (e.g. 'house', 'substation', 'inverter' etc)
    Returns:
        agent_meta_df : dataframe of system metadata
        agent_df: dataframe of agent timeseries data
        """
    os.chdir(dir_path)
    hdf5filenames = [f for f in os.listdir('.') if f.startswith(gen_name + '_') and f.endswith('.h5') ]
    if len(hdf5filenames) != 0:
        filename = hdf5filenames[0]
        store = h5py.File(filename, "r")
        list(store.keys())
        # # reading data as pandas dataframe
        data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r')
        # This update is to keep consistent data format
        data_df = data_df.set_index([data_df.index, data_df['uid']])
        data_df = data_df.drop(columns = ['uid'])

        # Determine first day of simulation and resulting slice to take

        case_config = load_json(dir_path, 'generate_case_config.json')
        sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
        start_time = sim_start + timedelta(days=int(day_range[0]) - 1)
        stop_time = start_time + (day_range[-1] - day_range[0] + 1) * timedelta(days=1) - timedelta(minutes=5)

        # For Day Ahead quantities need to layout 24-hour 10 am commitments to actual real time to match real time format.
        if gen_name in ['da_q', 'da_lmp', 'da_line']:
            clear_time = start_time - timedelta(hours=14)
            column_key = {'da_q': 'ClearQ_',
                          'da_lmp': 'LMP_',
                          'da_line': 'Line_'}
            dso_list = data_df.loc[(clear_time), :].index.tolist()
            # Reduce raw data to day range of interest and reshape/flatten
            data_df = data_df.loc[start_time:stop_time, :]
            frame_size = len(data_df) * len(data_df.columns)
            test = np.reshape(data_df.values, frame_size)

            # Create bespoke index arrays
            dates = []
            dsos = []
            for day in day_range:
                for dso in dso_list:
                    arr = np.array([sim_start + timedelta(days=1) * (day - 1) + timedelta(hours=i) for i in range(24)])
                    dates += arr.tolist()
                    dsos += np.array([dso for i in range(24)]).tolist()

            gen_data_df = pd.DataFrame(index=[dates, dsos], columns=[column_key[gen_name][:-1]])
            gen_data_df[column_key[gen_name][:-1]] = test

        else:
            gen_data_df = data_df.loc[start_time:stop_time, :]
    else:
        jsonfilenames = [f for f in os.listdir('.') if f.startswith(gen_name + '_') and f.endswith('.json')]
        if len(jsonfilenames) == 0:
            raise Exception('Could not find H5 or json file for ' + gen_name)
        filename = jsonfilenames[0]
        json_dict1 = load_json(dir_path, filename)

        json_dict = copy.copy(json_dict1)  # Seems to crash with multiple calls maybe because of loading cache.
        json_metadata = json_dict['Metadata']
        json_start_time = json_dict['StartTime']
        del json_dict['Metadata']
        del json_dict['StartTime']

        time_list = list(json_dict.keys())
        element_list = list(json_dict[time_list[0]].keys())
        if isinstance(json_dict[time_list[0]][element_list[0]], float):
            entries_per_step = 1
        elif isinstance(json_dict[time_list[0]][element_list[0]], list):
            entries_per_step = len(json_dict[time_list[0]][element_list[0]])

        time_step = (int(time_list[1]) - int(time_list[0])) / entries_per_step
        sim_start = datetime.strptime(json_start_time, '%Y-%m-%d %H:%M:%S')
        # Add additional calculations to the dataframe
        sim_end = sim_start + timedelta(seconds=time_step * entries_per_step * (len(time_list)) - 1)
        start_time = sim_start + timedelta(days=int(day_range[0]) - 1)
        stop_time = start_time + (day_range[-1] - day_range[0] + 1) * timedelta(days=1) - timedelta(minutes=5)

        time_index = pd.date_range(start=sim_start, end=sim_end, freq=str(time_step) + 'S')

        idx = pd.MultiIndex.from_product([time_index, element_list])
        gen_df = pd.DataFrame(index=idx,
                              columns=['Line'])

        for each in element_list:
            data = []
            for time in json_dict:
                if isinstance(json_dict[time_list[0]][element_list[0]], float):
                    data.append(json_dict[time][each])
                if isinstance(json_dict[time_list[0]][element_list[0]], list):
                    data.extend(json_dict[time][each])

            gen_df.loc[(slice(None), each), 'Line'] = data
        if gen_name in ['da_line', 'rt_line']:
            element_index = [ele.replace('Branch', gen_name) for ele in element_list]
        elif gen_name in ['da_lmp', 'rt_q', 'da_q', 'gen']:
            element_index = [gen_name + ele for ele in element_list]
            if gen_name == 'gen':
                gen_df = gen_df.rename(columns={'Line': 'Pgen'})
        idx = pd.MultiIndex.from_product([time_index, element_index])
        gen_df = gen_df.set_index(idx)
        gen_data_df = gen_df.loc[start_time:stop_time, :]

    return gen_data_df


def load_ames_data(dir_path, day_range):
    """Utility to open AMES csv file.
    Arguments:
        dir_path (str): path of directory where AMES data lives
        day_range (range): range of simulation days for data to be returned
    Returns:
        data_df : dataframe of AMES data
        """

    name = os.path.join(dir_path + '/opf.csv')
    try:
        data_df = cache_df[name]
    except:
        # Load AMES data
        data_df = pd.read_csv(name, index_col='seconds')
        cache_df[name] = data_df

    # If the opf file has already been read in and index changed, file saved and reloaded need to convert to date time
    # rather than create from scratch
    if isinstance(data_df.index[0], str):
        data_df.set_index(pd.to_datetime(data_df.index), inplace=True)
    elif isinstance(data_df.index[0], date):
        pass
    else:
        case_config = load_json(dir_path, 'generate_case_config.json')
        sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')

        # Add additional calculations to the dataframe
        sim_end = sim_start + timedelta(seconds=data_df.index.to_list()[-1])
        data_df['Time'] = pd.date_range(start=sim_start, end=sim_end, periods=len(data_df))
        start_time = (day_range[0] - 1) * 300 * 288
        end_time = day_range[-1] * 300 * 288 - 300
        data_df = data_df.loc[start_time:end_time]
        data_df = data_df.set_index('Time')

    return data_df


def load_ercot_data(metadata_file, sim_start, day_range):
    """Utility to open AMES csv file.
    Arguments:
        dir_path (str): path of directory where the case config files lives
        sim_start (datetime): start time of the simulation (from generate_case_config.json)
        day_range (range): range of simulation days for data to be returned
    Returns:
        data_df: dataframe of ERCOT 2016 fuel mix data
        """

    # name = os.path.join(metadata_file + '/2016_ERCOT_5min_Load_Data_Revised.csv')
    try:
        data_df = cache_df[metadata_file]
    except:
        # Load Industrial load profiles data
        data_df = pd.read_csv(metadata_file, index_col='Seconds')
        cache_df[metadata_file] = data_df

    year_start = datetime(2015, 12, 29, 0)
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


def load_ercot_fuel_mix(metadata_path, dir_path, day_range):
    """Utility to open AMES csv file.
    Arguments:
        dir_path (str): path of directory where AMES data lives
        day_range (range): range of simulation days for data to be returned
    Returns:
        data_df : dataframe of AMES data
        """
    case_config = load_json(dir_path, 'generate_case_config.json')

    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')

    ercot_fuel_df = pd.read_excel(metadata_path + '/ERCOTGenByFuel2016.xls', sheet_name='AllMonths')
#    ercot_fuel_df = pd.read_excel('ERCOTGenByFuel2016.xlsx', sheet_name='AllMonths')
    ercot_fuel_df['Time'] = ercot_fuel_df['Time'].dt.round(freq='s')  #  For some reason loading can add millisecond error
    ercot_fuel_df = ercot_fuel_df.set_index('Time')
    ercot_fuel_df = ercot_fuel_df*4  # Multiply by four to turn 15 minute MW-hr data to MW data.

    start_time = sim_start + timedelta(days=day_range[0] - 1)
    stop_time = start_time + timedelta(days=(day_range[-1] - (day_range[0] - 1))) - timedelta(minutes=5)
    ercot_fuel_df = ercot_fuel_df.loc[start_time:stop_time, :]

    return ercot_fuel_df


def load_da_retail_price(dir_path, folder_prefix, dso_num, day_num, retail=True):
    """Utility to return day ahead cleared retail price.  Data corresponds to 10am bid day before mapped to actual
    datetime when the energy will be consumed.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        retail_da_data_df : dataframe of cleared DA retail price
        """
    date = get_date(dir_path, dso_num, str(day_num))
    os.chdir(dir_path + folder_prefix + dso_num)
    if retail:
        filename = 'retail_market_Substation_' + dso_num + '_3600_metrics.h5'
        index = 5
    else:
        filename = 'dso_market_Substation_' + dso_num + '_3600_metrics.h5'
        index = 4
    store = h5py.File(filename, "r")
    list(store.keys())
    bid_time = date - timedelta(hours=14)  # + timedelta(seconds=1)
    retail_da_data_df = pd.read_hdf(filename, key='/metrics_df1', mode='r', where='index=bid_time')
    retail_da_data_df = retail_da_data_df.set_index([retail_da_data_df.index, retail_da_data_df['uid']])
    # Reduce data frame to the 10am day ahead clearance and the 24-hours for the next day.

    # retail_da_data_df = retail_da_data_df.loc[bid_time]
    retail_da_data_df = retail_da_data_df.loc[(retail_da_data_df['i'] >= 13) & (retail_da_data_df['i'] <= 36)]

    # Set up datetime index for actual time of next day that cleared Day Ahead bid relates to.
    time = []
    for i in range(len(retail_da_data_df)):
        time.append(bid_time + timedelta(hours=int(retail_da_data_df.iloc[i,index]+1)))
    retail_da_data_df['date'] = time
    retail_da_data_df = retail_da_data_df.set_index(['date'])

    return retail_da_data_df


def load_retail_data(dir_path, folder_prefix, dso_num, day_num, agent_name):
    """Utility to open h5 files for agent data.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        agent_name (str): name of agent data to load (e.g. 'house', 'substation', 'inverter' etc)
    Returns:
        agent_meta_df : dataframe of system metadata
        agent_df: dataframe of agent timeseries data
        """
    date = get_date(dir_path, dso_num, str(day_num))
    os.chdir(dir_path + folder_prefix + dso_num)
    hdf5filenames = [f for f in os.listdir('.') if ('_' + dso_num) in f and f.startswith(agent_name)]

    # TODO: - error message if more than one value in hdf5filenames
    filename = hdf5filenames[0]
    store = h5py.File(filename, "r")
    list(store.keys())
    # reading data as pandas dataframe
    retail_index_df = pd.read_hdf(filename, key='/metrics_df1', mode='r')
    # TODO: use where='index=bid_time' to slice h5 and eliminate need for loc below.
    retail_data_df = pd.read_hdf(filename, key='/metrics_df2', mode='r')

    # Reduce data frame to the 10am day ahead clearance and the 24-hours for the next day.
    bid_time = date - timedelta(hours=14) - timedelta(seconds=30)
    retail_data_df = retail_data_df.loc[bid_time]
    # retail_data_df = retail_data_df.loc[(retail_data_df['j'] >= 14) & (retail_data_df['j'] <= 37)]

    # Set up datetime index for actual time of next day that cleared Day Ahead bid relates to.
    time = []
    for i in range(len(retail_data_df)):
        time.append(bid_time + timedelta(seconds=30) + timedelta(hours=int(retail_data_df.iloc[i,3] + 14)))
    retail_data_df['date'] = time
    retail_data_df = retail_data_df.set_index(['date'])

    retail_data_df = retail_data_df.rename(columns={'site_quantities': 'total_cleared_quantity'})

    # Map customer names to dataframe
    customer_dict = retail_index_df.set_index('i').to_dict()['meters']
    retail_data_df['i'] = retail_data_df['i'].replace(customer_dict)
    retail_data_df = retail_data_df.rename(columns={'i': 'meter'})

    # Save to file
    retail_data_df.to_hdf('Retail_Quantities.h5', key='/index' + day_num)

    return retail_data_df, retail_index_df


def load_agent_data(dir_path, folder_prefix, dso_num, day_num, agent_name):
    """Utility to open h5 files for agent data.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        agent_name (str): name of agent data to load (e.g. 'house', 'substation', 'inverter' etc)
    Returns:
        agent_meta_df : dataframe of system metadata
        agent_df: dataframe of agent timeseries data
        """
    #os.chdir(dir_path + folder_prefix + dso_num)
    # daystr = '_' + str(int(day_num)) + '_'
    if agent_name in ['bill', 'energy', 'amenity']:
        os.chdir(dir_path)
        hdf5filenames = [f for f in os.listdir('.') if ('_'+ dso_num) in f and f.startswith(agent_name)]
    else:
        date = get_date(dir_path, dso_num, str(day_num))
        os.chdir(dir_path + folder_prefix + dso_num)
        if agent_name in ['retail_site']:
            hdf5filenames = [f for f in os.listdir('.') if ('_' + dso_num) in f and f.startswith(agent_name)]
        else:
            hdf5filenames = [f for f in os.listdir('.') if '300' in f and f.startswith(agent_name)]
    # TODO: - error message if more than one value in hdf5filenames
    filename = hdf5filenames[0]
    store = h5py.File(filename, "r")
    list(store.keys())
    # reading data as pandas dataframe
    if agent_name == 'energy':
        energy_data_df = pd.read_hdf(filename, key='energy_data', mode='r')
        energy_sums_df = pd.read_hdf(filename, key='energy_sums', mode='r')
        return energy_data_df, energy_sums_df
    elif agent_name == 'bill':
        agent_data_df = pd.read_hdf(filename, key='base_bill_data', mode='r')
        # TODO: update code once complete bill data is written out by rate case.
        agent_bid_df = None
        return agent_data_df, agent_bid_df
    elif agent_name == 'amenity':
        amenity_data_df = pd.read_hdf(filename, key='amenity_data', mode='r')
        return amenity_data_df
    else:
        #agent_data_df = pd.read_hdf(filename, key='/metrics' + daystr + 'df0', mode='r')
        # agent_data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r')
        stop_time = date + timedelta(days=1) - timedelta(minutes=5)
        agent_data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r', where='index>=date and index<=stop_time')
        # agent_data_df = agent_data_df.ix[date:(date + timedelta(days=1) - timedelta(minutes=5))]
        if agent_name in ['battery_agent', 'retail_market', 'water_heater_agent', 'dso_market']:
            # This update is to keep consistent data format
            agent_data_df = agent_data_df.set_index([agent_data_df.index, agent_data_df['uid']])
        #     agent_data_df.sort_index(ascending=True, inplace=True)
        #     agent_data_df = agent_data_df.loc(axis=0)[date:(date + timedelta(days=1) - timedelta(minutes=5)), :]
        #     # agent_data_df = agent_data_df.loc[date:(date + timedelta(days=1) - timedelta(minutes=5)), :]
        #     # start_time = (int(day_num) - 1) * 300 * 288
        #     # end_time = start_time + 300 * (288 - 1)
        #     # agent_data_df = agent_data_df.loc[start_time:end_time, :]
        # else:
        #     agent_data_df = agent_data_df.loc[date:(date + timedelta(days=1) - timedelta(minutes=5))]
        # TODO: waterheater agent writes bids to df2 - -need to make consistent
        if agent_name in ['dso_tso', 'water_heater_agent', 'hvac_agent']:
            agent_bid_df = None
        elif agent_name in ['retail_market', 'dso_market']:
            try:
                agent_bid_df = pd.read_hdf(filename, key='/metrics_df1', mode='r')
            except:
                agent_bid_df = None
        else:
            agent_bid_df = pd.read_hdf(filename, key='/metrics_df2', mode='r')
            # agent_bid_df = agent_bid_df.ix[date:(date + timedelta(days=1) - timedelta(minutes=5))]
            agent_data_df = agent_data_df.loc[date:(date + timedelta(days=1) - timedelta(minutes=5))]
        return agent_data_df, agent_bid_df


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


def get_house_schedules(agent_metadata, gld_metadata, house_name):
    """Utility to get schedules directly from the agent dictionary.  This allows evaluation of schedules prior to agent
    control.
    Arguments:
        agent_metadata (dict): dictionary of agent metadata
        gld_metadata (dict): dictionary of gld metadata
        house_name (str): name of GLD house object schedules are wanted for
    Returns:
        schedules (dict) : dictionary of schedules in list form
        """

    # agent_metadata = load_json(dir_path + folder_prefix + dso_num, 'Substation_' + dso_num + '_agent_dict.json')
    # gld_metadata = load_json(dir_path + folder_prefix + dso_num, 'Substation_' + dso_num + '_glm_dict.json')

    wh_temp = None
    cool_weekday = None
    cool_weekend = None
    heat_weekday = None
    heat_weekend = None

    for wh in agent_metadata['water_heaters'].keys():
        if agent_metadata['water_heaters'][wh]['meterName'] == gld_metadata['houses'][house_name]['billingmeter_id']:
            wh_temp = agent_metadata['water_heaters'][wh]['Tdesired']

    if gld_metadata['houses'][house_name]['cooling'] != 'NONE':

        hvac = agent_metadata['hvacs'][house_name]

        cool_weekday = []
        cool_weekend = []
        heat_weekday = []
        heat_weekend = []

        hour = [n*1/12 for n in range(24*12)]

        for time in hour:
            if time <= hvac['wakeup_start']:
                cool_weekday.append(hvac['night_set_cool'])
                heat_weekday.append(hvac['night_set_heat'])
            elif time <= hvac['daylight_start']:
                cool_weekday.append(hvac['wakeup_set_cool'])
                heat_weekday.append(hvac['wakeup_set_heat'])
            elif time <= hvac['evening_start']:
                cool_weekday.append(hvac['daylight_set_cool'])
                heat_weekday.append(hvac['daylight_set_heat'])
            elif time <= hvac['night_start']:
                cool_weekday.append(hvac['evening_set_cool'])
                heat_weekday.append(hvac['evening_set_heat'])
            else:
                cool_weekday.append(hvac['night_set_cool'])
                heat_weekday.append(hvac['night_set_heat'])

            if time <= hvac['weekend_day_start']:
                cool_weekend.append(hvac['weekend_night_set_cool'])
                heat_weekend.append(hvac['weekend_night_set_heat'])
            elif time <= hvac['weekend_night_start']:
                cool_weekend.append(hvac['weekend_day_set_cool'])
                heat_weekend.append(hvac['weekend_day_set_heat'])
            else:
                cool_weekend.append(hvac['weekend_night_set_cool'])
                heat_weekend.append(hvac['weekend_night_set_heat'])

    schedules = {'cool_weekday': cool_weekday,
                 'cool_weekend': cool_weekend,
                 'heat_weekday': heat_weekday,
                 'heat_weekend': heat_weekend,
                 'wh_Tdesired': wh_temp}

    return schedules


def load_weather_data(dir_path, folder_prefix, dso_num, day_num):
    """Utility to open weather dat files and find day of data
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\\DSO_')
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
    data = pd.read_csv(dir_path + '\\' + weather_city + '\\weather.dat')
    data['datetime'] = data['datetime'].apply(pd.to_datetime)
    data = data.set_index(['datetime'])
    # Determine first day of simulation and resulting slice to take
    case_config = load_json(dir_path, 'case_config_' + dso_num + '.json')
    sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')
    start_time = sim_start + timedelta(days=int(day_num) - 1)
    stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
    weather_df = data.loc[start_time:stop_time, :]

    return weather_df


def wind_diff(x):
    return max(x) - min(x)


def RCI_analysis(dso_range, case, data_path, metadata_path, dso_metadata_file, energybill=False):
    """  For a specified dso range and case this function will analyze the ratios of Res, Comm, and Industrial.
    Arguments:
        dso_range (range): the DSO range that the data should be analyzed
        case (str): folder extension of case of interest
        metadata_path (str): folder extension for DSO and Comm Building  metadata
    Returns:
        dataframe with analysis values
        saves values to file
        """

    os.chdir(data_path)
    # Determine tariff rate class of each meter up front.
    commdata = load_json(metadata_path, 'DSOT_commercial_metadata.json')
    dso_data = load_json(metadata_path, dso_metadata_file)

    commbldglist = []
    for bldg in commdata['building_model_specifics']:
        commbldglist.append(bldg)
    residbldglist = ['SINGLE_FAMILY', 'MOBILE_HOME', 'MULTI_FAMILY']

    dsolist = []
    sum_energy = []
    sum_cust = []
    rescount = []
    commcount = []
    resplan = []
    commplan = []
    resvar = []
    commvar = []
    RSales = []
    CSales = []
    ISales = []
    REngSim = []
    REngTarget = []
    CEngSim = []
    CEngTarget = []
    IEngSim = []
    IEngTarget = []
    reszero = []
    commzero = []
    zmeter_list = []
    HVACtot = []
    WHtot = []
    Batt_tot = []
    Battratingtot = []
    Battcapacitytot = []
    PVtot = []
    PVratingtot = []
    EVtot = []
    EVratingtot = []
    EVcapacitytot = []
    scaling_factor = []
    dsocommloadfactor = []
    dsoresloadfactor = []
    dsocommavgload = []
    dsoresavgload = []

    # Create dictionaries to record a list for sums type of commercial and residential building.
    csum = {}
    rsum = {}
    for bldg in commbldglist:
        csum.update({bldg: []})
    for bldg in residbldglist:
        rsum.update({bldg: []})

    for dso in dso_range:
        commloadfactor = []
        resloadfactor = []
        commavgload = []
        resavgload = []

        dsolist.append(dso)
        sum_energy.append(dso_data['DSO_'+ str(dso)]['RCI energy mix']['residential'] + \
                     dso_data['DSO_' + str(dso)]['RCI energy mix']['commercial'] + \
                     dso_data['DSO_' + str(dso)]['RCI energy mix']['industrial'])
        sum_cust.append(dso_data['DSO_'+ str(dso)]['RCI customer count mix']['residential'] + \
                     dso_data['DSO_' + str(dso)]['RCI customer count mix']['commercial'] + \
                     dso_data['DSO_' + str(dso)]['RCI customer count mix']['industrial'])
        print('DSO_' + str(dso) + ': energy sum: ' + str(sum_energy[-1]) + ', customer sum: ' + str(sum_cust[-1]))

        # TODO: deprecate once scaling factor is in all metadata files.
        scale_target = dso_data['DSO_' + str(dso)]['number_of_customers'] \
                       * dso_data['DSO_' + str(dso)]['RCI customer count mix']['residential'] \
                       / dso_data['DSO_' + str(dso)]['number_of_gld_homes']
        scaling_factor.append(scale_target)

        file_name = 'Substation_' + str(dso) + '_glm_dict.json'
        agent_prefix = '/DSO_'
        metadata = load_json(case + agent_prefix + str(dso), file_name)

        if energybill:
            energy_df, energysum_df = load_agent_data(data_path, agent_prefix, str(dso), '1', 'energy')
            filename = data_path + '/energy_dso_' + str(dso) + '_data.h5'
            store = h5py.File(filename)
            list(store.keys())
            annual_energy_df = pd.read_hdf(filename, key='energy_sums', mode='r')

            RSales.append(annual_energy_df.loc[('residential', 'kw-hr'), 'sum'])
            CSales.append(annual_energy_df.loc[('commercial', 'kw-hr'), 'sum'])
            ISales.append(annual_energy_df.loc[('industrial', 'kw-hr'), 'sum'])
            total = RSales[-1] + CSales[-1] + ISales[-1]
            REngSim.append(RSales[-1]/total)
            REngTarget.append(dso_data['DSO_' + str(dso)]['RCI energy mix']['residential'])
            CEngSim.append(CSales[-1]/total)
            CEngTarget.append(dso_data['DSO_' + str(dso)]['RCI energy mix']['commercial'])
            IEngSim.append(ISales[-1]/total)
            IEngTarget.append(dso_data['DSO_' + str(dso)]['RCI energy mix']['industrial'])

        HVACcount = 0
        WHcount = 0
        Battcount = 0
        Battrating = 0
        Battcapacity = 0
        PVcount = 0
        PVrating = 0
        EVcount = 0
        EVrating = 0
        EVcapacity = 0
        commbldgcount = 0
        resbldgcount = 0
        commzerometer = 0
        reszerometer = 0

        for house in metadata['houses']:
            if metadata['houses'][house]['cooling'] == 'ELECTRIC':
                HVACcount += 1
            if metadata['houses'][house]['heating'] != 'GAS' and \
                metadata['houses'][house]['house_class'] in ['SINGLE_FAMILY', 'MULTI_FAMILY', 'MOBILE_HOME']:
                WHcount += 1
        HVACtot.append(HVACcount)
        WHtot.append(WHcount)

        if 'ev' in metadata.keys():
            for ev in metadata['ev']:
                EVcount += 1
                EVrating += metadata['ev'][ev]['max_charge'] / 1000
                EVcapacity += metadata['ev'][ev]['range_miles'] / metadata['ev'][ev]['miles_per_kwh']
        EVtot.append(EVcount)
        EVratingtot.append(EVrating)
        EVcapacitytot.append(EVcapacity)

        # Determine count and ratings/capacities of inverter based technologies
        for inverter in metadata['inverters']:
            if 'ibat' in inverter:
                Battrating += metadata['inverters'][inverter]['rated_W'] / 1000
                Battcapacity += metadata['inverters'][inverter]['bat_capacity'] / 1000
                Battcount += 1
            elif 'isol' in inverter:
                PVrating += metadata['inverters'][inverter]['rated_W'] / 1000
                PVcount += 1
        Batt_tot.append(Battcount)
        Battratingtot.append(Battrating)
        Battcapacitytot.append(Battcapacity)
        PVtot.append(PVcount)
        PVratingtot.append(PVrating)

        # Create dictionaries to get a count for each type of commercial and residential building.
        c = {}
        r = {}
        for bldg in commbldglist:
            c.update({bldg: 0})
        for bldg in residbldglist:
            r.update({bldg: 0})

        # TODO: This code should go in GLD-dict at some stage.
        for each in metadata['billingmeters']:
            metadata['billingmeters'][each]['tariff_class'] = None
            for bldg in commbldglist:
                if bldg in metadata['billingmeters'][each]['building_type']:
                    metadata['billingmeters'][each]['tariff_class'] = 'commercial'
                    c[bldg] += 1
                    commbldgcount += 1
                    if energybill:
                        commloadfactor.append(energy_df.loc[(each, 'load_factor'), 'sum'])
                        commavgload.append(energy_df.loc[(each, 'avg_load'), 'sum'])
                        if energy_df.loc[(each, 'kw-hr'), 'sum'] == 0:
                            commzerometer += 1
                            zmeter_list.append('DSO ' + str(dso) + ' comm. meter ' + each + ' is zero!')
            for bldg in residbldglist:
                if bldg in metadata['billingmeters'][each]['building_type']:
                    metadata['billingmeters'][each]['tariff_class'] = 'residential'
                    r[bldg] += 1
                    resbldgcount += 1
                    if energybill:
                        resloadfactor.append(energy_df.loc[(each, 'load_factor'), 'sum'])
                        resavgload.append(energy_df.loc[(each, 'avg_load'), 'sum'])
                        if energy_df.loc[(each, 'kw-hr'), 'sum'] == 0:
                            reszerometer += 1
                            zmeter_list.append('DSO ' + str(dso) + ' res. meter ' + each + ' is zero!')
            if metadata['billingmeters'][each]['building_type'] == 'UNKNOWN':
                metadata['billingmeters'][each]['tariff_class'] = 'industrial'
            if metadata['billingmeters'][each]['tariff_class'] is None:
                raise Exception('Tariff class was not successfully determined for meter ' + each)

        rescount.append(resbldgcount)
        commcount.append(commbldgcount)
        reszero.append(reszerometer)
        commzero.append(commzerometer)
        dsoresloadfactor.append(np.mean(resloadfactor))
        dsocommloadfactor.append(np.mean(commloadfactor))
        dsoresavgload.append(np.mean(resavgload))
        dsocommavgload.append(np.mean(commavgload))

        for bldg in commbldglist:
            csum[bldg].append(c[bldg])
        for bldg in residbldglist:
            rsum[bldg].append(r[bldg])

        resplan.append(dso_data['DSO_' + str(dso)]['number_of_gld_homes'])
        commplan.append(round(resplan[-1] * dso_data['DSO_' + str(dso)]['RCI customer count mix']['commercial'] \
                           / dso_data['DSO_' + str(dso)]['RCI customer count mix']['residential']/
                              dso_data['general']['comm_customers_per_bldg']))
        # Calculate variance in building population from plan
        resvar.append(resbldgcount - resplan[-1])
        commvar.append(commbldgcount - commplan[-1])

        print("DSO " + str(dso) + ': ' + str(rescount[-1]) + ' Res, ' + str(commcount[-1]) + ' Comm')

    d = {'dso': dsolist,
         'RCI Energy Summation': sum_energy,
         'RCI Customer Summation': sum_cust,
         'Res Buildings (modeled)': rescount,
         'Res Buildings (expected)': resplan,
         'Res Buildings (variance)': resvar,
         'Comm Buildings (modeled)': commcount,
         'Comm Buildings (expected)': commplan,
         'Comm Buildings (variance)': commvar,
         'HVAC Count (cooling)': HVACtot,
         'WH count (residential)': WHtot,
         'Battery Count': Batt_tot,
         'Battery rating (kW)': Battratingtot,
         'Battery Capacity (kW-hr)': Battcapacitytot,
         'PV Count': PVtot,
         'PV Rating (kW)': PVratingtot,
         'EV Count': EVtot,
         'EV Rating (kW)': EVratingtot,
         'EV Capacity (kW-hr)': EVcapacitytot,
         'Scaling Factor': scaling_factor
    }
    # Add residential and commercial building counts by type:
    d.update(rsum)
    d.update(csum)

    if energybill:
        d['R Sales (Sim)'] = RSales
        d['C Sales (Sim)'] = CSales
        d['I Sales (Sim)'] = ISales
        d['R Energy Mix (Sim)'] = REngSim
        d['R Energy Mix (Target)'] = REngTarget
        d['C Energy Mix (Sim)'] = CEngSim
        d['C Energy Mix (Target)'] = CEngTarget
        d['I Energy Mix (Sim)'] = IEngSim
        d['I Energy Mix (Target)'] = IEngTarget
        d['R Avg Load'] = dsoresavgload
        d['C Avg Load'] = dsocommavgload
        d['R Load Factor'] = dsoresloadfactor
        d['C Load Factor'] = dsocommloadfactor
        d['Zero Meters (Res)'] = reszero
        d['Zero Meters (Comm)'] = commzero
        d['Zero Meters (Res)'] = reszero

    rci_df = pd.DataFrame(data=d,
                           index=dsolist)

    os.chdir(data_path)
    rci_df.to_csv(path_or_buf=data_path + '/RCI_check.csv')

    # Save log file of zero energy meters
    with open('Zero_meters_exception_log.txt', 'w') as f:
        for item in zmeter_list:
            f.write("%s\n" % item)

    return rci_df


def DSO_loadprofiles(dso_range, day_range, case, dso_metadata_file, metadata_path, plot_weather=True):
    """  For a specified dso range and case this function will analyze the ratios of Res, Comm, and Industrial.
    Arguments:
        dso_range (range): the DSO range that the data should be analyzed
        case (str): folder extension of case of interest
        dso_metadata_file (str): folder extension and file name for DSO metadata
    Returns:
        dataframe with analysis values
        saves values to file
        """
    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, day_range)

    case_config = load_json(case, 'case_config_' + dso_num + '.json')
    sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')

    # Load DSO MetaData
    with open(dso_metadata_file) as json_file:
        DSOmetadata = json.load(json_file)

    for dso in dso_range:
        # Calculate expected scaling factor
        scale_target = DSOmetadata['DSO_' + str(dso)]['number_of_customers'] \
                       * DSOmetadata['DSO_' + str(dso)]['RCI customer count mix']['residential'] \
                       / DSOmetadata['DSO_' + str(dso)]['number_of_gld_homes']
        # Calculate expected fraction of Residential and Commercial Energy Use
        RC_fraction = DSOmetadata['DSO_' + str(dso)]['RCI energy mix']['residential'] \
                      + DSOmetadata['DSO_' + str(dso)]['RCI energy mix']['commercial']

        for day in day_range:
            start_time = sim_start + timedelta(days=day-1)
            stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
            ercot_sum = ercot_df.loc[start_time:stop_time, ' Bus' + str(dso)].sum()
            ercot_load = ercot_df.loc[start_time:stop_time, [' Bus' + str(dso), 'datetime']] # .values.tolist()
            #del ercot_load[-1]

            # Load Industrial load profiles data
            indust_df = pd.read_csv(case + '\ind_load_p.csv', index_col='seconds')
            start_time = (day - 1) * 300 * 288
            end_time = start_time + 300 * (288-1)

            # Load DSO and TSO Load Data
            if plot_weather:
                weather_df = load_weather_data(case, '\\DSO_', str(dso), str(day))
            substation_meta_df, substation_df = load_system_data(case, '\\Substation_', str(dso), str(day), 'substation')

            scaling_factor = RC_fraction * ercot_sum / (substation_df['real_power_avg'].sum() / 1000000)
            scaling_error = scaling_factor / scale_target * 100
            dsoload_df = indust_df.loc[start_time:end_time, [' Bus' + str(dso)]]#.values.tolist()
            dsoload_df.index = ercot_load['datetime']
            dsoload_df = dsoload_df.rename(columns={' Bus' + str(dso): 'Industrial Scaled'})
            dsoload_df['Substation Scaled'] = substation_df['real_power_avg'].values.tolist()
            dsoload_df['Substation Scaled'] = dsoload_df['Substation Scaled'] / 1000 * scale_target/ 1000
            dsoload_df['Substation Target'] = substation_df['real_power_avg'].values.tolist()
            dsoload_df['Substation Target'] = dsoload_df['Substation Target'] / 1000 * scaling_factor / 1000
            dsoload_df['Ercot_load'] = ercot_load[' Bus' + str(dso)]
            dsoload_df['Industrial Target'] = dsoload_df['Ercot_load'] - dsoload_df['Substation Target']

            fig, ax1 = plt.subplots()
            fig.suptitle('DSO ' + str(dso) + ' (' + dsoload_df.index[0].strftime('%x') + ') scaling factor: ' + str(int(scaling_factor)) + ' (' \
                      + str(int(scaling_error)) + '% Target)')
            ax1.set_xlabel('Time of day (hours)')
            ax1.set_ylabel('Load (MW)')
            ax1.plot(dsoload_df)
            # Only label every 24th value (every 2 hours)
            ticks_to_use = dsoload_df.index[::24]
            # Set format of labels (note year not excluded as requested)
            labels = [i.strftime("%H") for i in ticks_to_use]
            # Now set the ticks and labels
            ax1.set_xticks(ticks_to_use)
            ax1.set_xticklabels(labels)
            ax1.legend(labels=dsoload_df.columns.tolist())
            if plot_weather:
                ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
                color = 'tab:red'
                ax2.set_ylabel('Temperature (F)', color=color)  # we already handled the x-label with ax1
                ax2.plot(weather_df['temperature'], color=color, linestyle=':')
                ax2.tick_params(axis='y', labelcolor=color)
                ax2.set_xticks(ticks_to_use)
                ax1.set_xticklabels(labels)
            plot_filename = datetime.now().strftime(
                '%Y%m%d') + 'Load_Profiles_DSO_' + str(dso) + '_' + dsoload_df.index[0].strftime('%m-%d') + '.png'
            file_path_fig = os.path.join(data_path, 'plots', plot_filename)
            fig.savefig(file_path_fig, bbox_inches='tight')
            #fig.close()


def find_edge_cases(dso, case, day_range, agent_prefix, gld_prefix):
    """  For a specified dso and case this function will return the day associated with a range of 'edge cases' (for
         example the hottest day or biggest swing in prices.
    Arguments:
        dso (str): the DSO that the data should be plotted for (e.g. '1')
        case (str): folder extension of case of interest
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        dataframe with values for each day
        dictionary of worst values.
        saves values to file
        """
#   Hottest day, coldest day, day with largest swing in temperature (inter day min and max as well as average for day)
#   Do we need to do the same for solar load?
#   Most expensive retail day, cheapest, largest change.  (inter day min and max as well as average for day)
#   Day with peak load, min load, and biggest change in load.  (inter day min and max as well as average for day)
#   Largest load ramp in X hour window?
#   Day with largest and smallest renewable energy contribution (absolute or as percent of all generation)?

    #  Find weather related values for each day within the day range.
    temp_min = []
    temp_max = []
    temp_ave = []
    solar_ave = []

    #  file_name = 'TE_Base_s' + dso + '_glm_dict.json'
    file_name = 'Substation_' + dso + '_glm_dict.json'
    metadata = load_json(case + agent_prefix + dso, file_name)
    weather_city = metadata["climate"]["name"]
    os.chdir(base_case + '\\' + weather_city)
    weather_data = pd.read_csv('weather.dat')
    # TODO: Need to pull out all weather loading into a standard approach and account for the fact weather file has all days.

    for day in day_range:
        start = (day - 1) * 288
        temp_df = weather_data.iloc[start:(start + 288), :]
        temp_min.append(temp_df['temperature'].min())
        temp_max.append(temp_df['temperature'].max())
        temp_ave.append(temp_df['temperature'].mean())
        solar_ave.append(temp_df['solar_direct'].mean())

    #  Find retail, dso, and substation related values for each day within the day range.
    price_rt_min = []
    price_rt_max = []
    price_rt_ave = []
    price_rt_ramp_max = []
    cost_rt_min = []
    cost_rt_max = []
    cost_rt_ave = []
    cost_rt_ramp_max = []
    load_min = []
    load_max = []
    load_ave = []
    load_ramp_max = []
    ramp_window = 3*12  # 3 hour ramp window
    #  consider adding day ahead values as well as bid quantities.

    for day in day_range:
        retail_data_df, retail_bid_df = load_agent_data(base_case, agent_prefix, dso, str(day), 'retail_market')
        price_rt_min.append(retail_data_df['cleared_price_rt'].min())
        price_rt_max.append(retail_data_df['cleared_price_rt'].max())
        price_rt_ave.append(retail_data_df['cleared_price_rt'].mean())
        price_rt_ramp_max.append(retail_data_df['cleared_price_rt'].rolling(window=ramp_window).apply(wind_diff).max())

        dsomarket_data_df, dsomarket_bid_df = load_agent_data(base_case, agent_prefix, dso_num, str(day), 'dso_market')
        cost_rt_min.append(dsomarket_data_df['cleared_price_rt'].min())
        cost_rt_max.append(dsomarket_data_df['cleared_price_rt'].max())
        cost_rt_ave.append(dsomarket_data_df['cleared_price_rt'].mean())
        cost_rt_ramp_max.append(dsomarket_data_df['cleared_price_rt'].rolling(window=ramp_window).apply(wind_diff).max())

        substation_meta_df, substation_df = load_system_data(base_case, GLD_prefix, dso_num, str(day), 'substation')
        load_min.append(substation_df['real_power_min'].min())
        load_max.append(substation_df['real_power_max'].max())
        load_ave.append(substation_df['real_power_avg'].mean())
        load_ramp_max.append(substation_df['real_power_avg'].rolling(window=ramp_window).apply(wind_diff).max())

    #  Create a dataframe to store the values created for each day.
    d = {'temperature_min': temp_min,
         'temperature_max': temp_max,
         'temperature_avg': temp_ave,
         'solar_direct_max': solar_ave,
         'rt_retail_price_min': price_rt_min,
         'rt_retail_price_max': price_rt_max,
         'rt_retail_price_avg': price_rt_ave,
         'rt_retail_price_ramp_max': price_rt_ramp_max,
         'rt_dso_cost_min': cost_rt_min,
         'rt_dso_cost_max': cost_rt_max,
         'rt_dso_cost_avg': cost_rt_ave,
         'rt_dso_cost_ramp_max': cost_rt_ramp_max,
         'substation_load_min': load_min,
         'substation_load_max': load_max,
         'substation_load_avg': load_ave,
         'substation_load_ramp_max': load_ramp_max}

    edge_df = pd.DataFrame(data=d,
                           index=day)

    # Create a dictionary with the select day for each case
    edge_dict = {}

    for var in list(d):
        if var.endswith('min'):
            edge_dict[var] = {'day': edge_df[var].idxmin(),
                              'value': edge_df.loc[edge_df[var].idxmin(), var]}
        elif var.endswith('avg'):
            # TODO: .ix is deprecated - need to replace.
            temp = edge_df.ix[(edge_df[var]-edge_df[var].median()).abs().argsort()[:1]].index.tolist()
            edge_dict[var] = {'day': temp[0],
                              'value': edge_df.loc[temp[0], var]}
        else:
            edge_dict[var] = {'day': edge_df[var].idxmax(),
                              'value': edge_df.loc[edge_df[var].idxmax(), var]}

    # Create list of edge days with no duplicates.
    edge_days = []
    for edge in list(edge_dict):
        if edge_dict[edge]['day'] not in edge_days:
            edge_days.append(edge_dict[edge]['day'])
    edge_days.sort()

    return edge_days, edge_dict, edge_df


def bldg_load_stack(dso, day_range, case, agent_prefix, gld_prefix, metadata_path, daily_dso_plots = False):
    """  For a specified dso, system, variable, and day this function will load in the required data, plot the daily
     profile and save the plot to file.
    Arguments:
        dso (int): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum', 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day (str): the day to plotted.
        case (str): folder extension of case of interest
        comp (str): folder extension of a comparison case of interest.  Optional - set to None to show just one case.
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        saves daily profile plot to file
        """

    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, day_range)

    industrial_file = os.path.join(metadata_path, case_config['indLoad'][5].split('/')[-1])
    indust_df = load_indust_data(industrial_file, day_range)
    indust_df = indust_df.set_index(ercot_df.index)

    # Load DSO MetaData
    DSOmetadata = load_json(metadata_path, case_config['dsoPopulationFile'])

    # Create Dataframe to collect and store all data reduced in this process
    dso_list = ['dso'+str(dso)]

    bldg_index = pd.MultiIndex.from_product([ercot_df.index.to_list(), dso_list], names=['time', 'dso'])
    data = np.zeros((len(ercot_df.index.to_list()*len(dso_list)), 1))
    bldg_loads_df = pd.DataFrame(data,
                            index=bldg_index,
                            columns=['Substation'])

    # Calculate expected scaling factor
    scale_target = DSOmetadata['DSO_' + str(dso)]['scaling_factor']

    file_name = 'Substation_' + str(dso) + '_glm_dict.json'
    metadata = load_json(case + agent_prefix + str(dso), file_name)

    for day in day_range:
        start_time = sim_start + timedelta(days=day-1)
        stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
        ercot_load = ercot_df.loc[start_time:stop_time, ['Bus' + str(dso)]] / scale_target * 1e6

        meta_df, bldg_df = load_system_data(case, gld_prefix, str(dso), str(day), 'billing_meter')

        # Load in substation curve
        substation_meta_df, substation_df = load_system_data(case, '/Substation_', str(dso), str(day), 'substation')

        replace_key = {}
        for meter in metadata['billingmeters']:
            replace_key.update({meter: metadata['billingmeters'][meter]['building_type']})

        bldg_df = bldg_df.replace({'name': replace_key})

        temp = bldg_df.groupby(['time','name'])[['real_power_avg']].sum().unstack()
        temp = temp.set_index(ercot_load.index)
        temp.columns = temp.columns.droplevel()

        y = []
        for col in temp.columns:
            y.append(temp[col].values.tolist())
            bldg_loads_df.loc[(slice(temp.index[0],temp.index[-1]), 'dso'+str(dso)), col] = \
                temp[col].values * scale_target /1e6

        bldg_loads_df.loc[(slice(temp.index[0], temp.index[-1]), 'dso' + str(dso)), 'Substation'] = \
            substation_df['real_power_avg'].values * scale_target /1e6

        bldg_loads_df.loc[(slice(temp.index[0], temp.index[-1]), 'dso' + str(dso)), 'Industrial'] = \
            indust_df.loc[start_time:stop_time, ['Bus' + str(dso)]].values

        if daily_dso_plots:
            # Plot Building Stacked Chart with ERCOT and Substation loads for reference
            plt.figure(figsize=(20, 10))
            plt.stackplot(temp.index, y, labels=temp.columns.tolist())
            plt.plot(temp.index, substation_df['real_power_avg'], label='Substation Load', color='black', linestyle=':')
            plt.plot(ercot_load.index, ercot_load['Bus' + str(dso)], label='ERCOT Load', color='red', linestyle='dashdot')

            plt.legend(loc='upper left')
            plt.xlabel('Time', size=12)
            plt.ylabel('Load (kW)', size=12)
            plt.title('DSO load profile by building type (DSO '+str(dso)+'; Day '+temp.index[0].strftime('%m-%d')+')')
            plot_filename = datetime.now().strftime(
                '%Y%m%d') + 'BuildingLoadStackGraph_DSO_' + str(dso) + '_' + temp.index[0].strftime('%m-%d') + '.png'
            file_path_fig = os.path.join(case, 'plots', plot_filename)
            plt.savefig(file_path_fig, bbox_inches='tight')

            # Plot individual building load profiles
            temp.plot(figsize=(20, 10))
            plt.legend(loc='upper left')
            plt.xlabel('Time', size=12)
            plt.ylabel('Load (kW)', size=12)
            plt.title('DSO load profile by building type (DSO '+str(dso)+'; Day '+temp.index[0].strftime('%m-%d')+')')
            plot_filename = datetime.now().strftime(
                '%Y%m%d') + 'BuildingLoadProfiles_DSO_' + str(dso) + '_' + temp.index[0].strftime('%m-%d') + '.png'
            file_path_fig = os.path.join(case, 'plots', plot_filename)
            plt.savefig(file_path_fig, bbox_inches='tight')

    bldg_loads_df = bldg_loads_df.rename(columns={"UNKNOWN": "Street lights"})
    bldg_loads_df.to_hdf(case + gld_prefix + str(dso) + '/Building_profiles.h5', key='Bldg_Profiles')
    bldg_loads_df.to_csv(path_or_buf=case + gld_prefix + str(dso) + '/buildingstack_data.csv')


def bldg_stack_plot(dso_range, day_range, case, metadata_path):
    """  For a specified dso, system, variable, and day this function will load in the required data, plot the daily
     profile and save the plot to file.
    Arguments:
        dso (str): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        case (str): folder extension of case of interest
        metadata_path (str): path of folder containing metadata
    Returns:
        saves daily profile plot to file
        """

    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, day_range)

    # Need to load data for each DSO and concatenate into one master dataframe
    for dso in dso_range:
        stack_df = pd.read_hdf(case+'/Substation_'+str(dso)+'/Building_profiles.h5', key='Bldg_Profiles', mode='r')
        if dso == dso_range[0]:
            bldg_loads_df = stack_df
        else:
            bldg_loads_df = pd.concat([bldg_loads_df, stack_df])

    # Create a plot of all buildings across all DSOs
    bldg_loads_df.to_hdf(case + '/Building_profiles.h5', key='Bldg_Profiles')
    bldg_loads_df.to_csv(path_or_buf=case + '/buildingstack_data.csv')

    temp = bldg_loads_df.groupby(['time']).sum()
    temp.to_csv(path_or_buf=case + '/buildingstack_data_allDSOs.csv')

    # temp = pd.read_csv(case + '/buildingstack_data_allDSOs.csv', index_col='time', parse_dates=True)

    start_time = sim_start + timedelta(days=day_range[0] - 1)
    stop_time = sim_start + timedelta(days=day_range[-1]) - timedelta(minutes=5)
    temp = temp.loc[start_time:stop_time, :]
    if temp.index[-1] < stop_time:
        raise Exception('DER stack plot data not available for ' + str(stop_time) + ".")

    label_list = temp.columns.tolist()
    label_list.insert(0, label_list.pop(label_list.index('Industrial')))
    # label_list = label_list[-1:] + label_list[:-1]
    temp = temp[label_list]  #

    y = []
    for col in temp.columns:
        if col != 'Substation':
            y.append(temp[col].values.tolist())

    # Plot Building Stacked Chart with ERCOT and Substation loads for reference
    plt.figure(figsize=(20, 10))
    label_list = temp.columns.tolist()
    label_list.remove('Substation')
    pal = ['grey'] + sns.color_palette("YlGn", 3) + ['grey'] + sns.color_palette("PuBu", 9)
    plt.stackplot(temp.index, y, labels=label_list, colors=pal)
    plt.plot(temp.index, temp['Substation']+temp['Industrial'], label='Total Simulation Load', color='black')
    bus_cols = [col for col in ercot_df.columns if 'Bus' in col]
    plt.plot(ercot_df.index, ercot_df[bus_cols].sum(axis=1), label='ERCOT Load', color='black', linestyle='--',
             linewidth=3)

    plt.legend(loc='upper left', prop={'size': 17})
    plt.xlabel('Time', size=25)
    plt.ylabel('Load (MW)', size=25)
    plt.ylim(top=80000, bottom=0)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    # plt.title('DSO load profile by building type (ALL DSOs)', size=20)
    plot_filename = datetime.now().strftime(
        '%Y%m%d') + 'BuildingLoadStackGraph_All_DSOs_' + temp.index[0].strftime('%m-%d') + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


def der_load_stack(dso, day_range, case, gld_prefix, metadata_path):
    """  For a specified dso and day range this function will load in the required data, process the data for the stacked
    DER loads and save the data to file.
    Arguments:
        dso (int): the DSO that the data should be plotted for (e.g. '1')
        day_range (range): the day range to plotted.
        case (str): folder extension of case of interest
        gld_prefix (str): folder extension for GridLAB-D data
        metadata_path (str): path of folder containing metadata
    Returns:
        saves dso DER loads data to file
        """

    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, day_range)

    if case_config['caseType']['bt'] == 1:
        battery_case = True
    else:
        battery_case = False
    if case_config['caseType']['fl'] == 1:
        flexload_case = True
    else:
        flexload_case = False
    if case_config['caseType']['pv'] == 1:
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


def der_stack_plot(dso_range, day_range, metadata_path, case, comp=None):
    """  For a specified dso range and day range this function will load in the required data, plot the stacked DER loads
    and save the plot to file.
    Arguments:
        dso_range (range): the DSO range that should be plotted.
        day_range (range): the day range to plotted.
        metadata_path (str): path of folder containing metadata
        case (str): folder extension of case of interest
        comp (str): folder extension for reference case to be plotted in comparison
    Returns:
        saves hdf and csv data files of combined dso data
        saves DER stack plot to file
        """

    # Load generate_case_config
    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, day_range)
    ames_rt_df = load_ames_data(case, day_range)
    ames_rt_df = ames_rt_df.set_index(ercot_df.index)

    if case_config['caseType']['bt'] == 1:
        battery_case = True
    else:
        battery_case = False
    if case_config['caseType']['fl'] == 1:
        flexload_case = True
    else:
        flexload_case = False
    if case_config['caseType']['pv'] == 1:
        pv_case = True
    else:
        pv_case = False

    # Need to load data for each DSO and concatenate into one master dataframe
    for dso in dso_range:
        der_df = pd.read_hdf(case + '/Substation_' + str(dso) + '/DER_profiles.h5', key='DER_Profiles', mode='r')
        if dso == dso_range[0]:
            der_loads_df = der_df
        else:
            der_loads_df = pd.concat([der_loads_df, der_df])

    # Save file of combined dso DER stack loads for later post processing.
    der_loads_df.to_hdf(case + '/DER_profiles.h5', key='DER_Profiles')
    der_loads_df.to_csv(path_or_buf=case + '/DERstack_data.csv')

    # Create a plot of all buildings across all DSOs
    temp = der_loads_df.groupby(['time']).sum()
    temp.to_csv(path_or_buf=case + '/der_stack_data_allDSOs.csv')

    # temp = pd.read_csv(case + '/der_stack_data_allDSOs.csv', index_col='time', parse_dates=True)

    start_time = sim_start + timedelta(days=day_range[0] - 1)
    stop_time = sim_start + timedelta(days=day_range[-1]) - timedelta(minutes=5)
    temp = temp.loc[start_time:stop_time, :]
    if temp.index[-1] < stop_time:
        raise Exception('DER stack plot data not available for ' + str(stop_time) + ".")

    if comp is not None:
        compare_df = pd.read_csv(comp + '/der_stack_data_allDSOs.csv', index_col='time', parse_dates=True)
        compare_df = compare_df.loc[start_time:stop_time, :]

    label_list = temp.columns.tolist()
    temp = temp[label_list]  #

    y = []
    for col in temp.columns:
        if pv_case:
            if col not in ['Substation', 'Battery', 'Substation Losses', 'PV']:
                y.append(temp[col].values.tolist())
        else:
            if col not in ['Substation', 'Battery', 'Substation Losses', 'PV', 'EV']:
                y.append(temp[col].values.tolist())

    # Plot Building Stacked Chart with ERCOT and Substation loads for reference
    plt.figure(figsize=(20, 10))
    label_list = temp.columns.tolist()
    label_list.remove('Substation')
    label_list.remove('Battery')
    label_list.remove('PV')
    # label_list.remove('Substation Losses')
    # if not battery_case:
    #     label_list.remove('Battery')
    pal = ['grey'] + ['darkseagreen'] + ['wheat'] + ['cornflowerblue'] + ['yellowgreen']
    plt.stackplot(temp.index, y, labels=label_list, colors=pal)
    plt.plot(temp.index, temp['Substation'] + temp['Industrial Loads'], label='Total Simulation Load', color='black')
    # if comp is None:
    #     plt.plot(temp.index, ames_rt_df[' TotalGen'] , label='Total Generation', color='green',
    #          linestyle='-')
    if battery_case:
        plt.plot(temp.index, temp[['Industrial Loads', 'Plug Loads', 'HVAC Loads', 'WH Loads', 'EV']].sum(axis=1) -temp['PV'] -temp['Battery']
                 , label='Battery Load', color='red', linestyle=':')
    if pv_case:
        plt.plot(temp.index, temp[['Industrial Loads', 'Plug Loads', 'HVAC Loads', 'WH Loads', 'EV']].sum(axis=1)
                -temp['PV'], label='Rooftop PV', color='brown', linestyle=':')
    if comp is not None:
        plt.plot(compare_df.index, compare_df['Substation'] + compare_df['Industrial Loads'], label='Reference Load',
                 color='grey', linestyle='--', linewidth=3)
        if flexload_case:
            plt.plot(compare_df.index, compare_df[['Industrial Loads', 'Plug Loads', 'HVAC Loads']].sum(axis=1)
                     , label='HVAC Reference', color='darkorange', linestyle='-.')
            plt.plot(compare_df.index, compare_df[['Industrial Loads', 'Plug Loads', 'HVAC Loads', 'WH Loads']].sum(axis=1)
                     , label='WH Reference', color='mediumblue', linestyle='-.')
    else:
        bus_cols = [col for col in ercot_df.columns if 'Bus' in col]
        plt.plot(ercot_df.index, ercot_df[bus_cols].sum(axis=1), label='ERCOT Load', color='black', linestyle='--', linewidth=3)

    plt.legend(loc='lower left', prop={'size': 17})
    plt.xlabel('Time', size=25)
    plt.ylabel('Load (MW)', size=25)
    plt.ylim(top=80000, bottom=0)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    # plt.title('DSO load profile by end-load type (ALL DSOs)', size=20)
    plot_filename = datetime.now().strftime(
        '%Y%m%d') + 'DERLoadStackGraph_All_DSOs_' + temp.index[0].strftime('%m-%d') + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


def daily_load_plots(dso, system, subsystem, variable, day, case, comp, agent_prefix, gld_prefix):
    """  For a specified dso, system, variable, and day this function will load in the required data, plot the daily
     profile and save the plot to file.
    Arguments:
        dso (str): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum', 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day (str): the day to plotted.
        case (str): folder extension of case of interest
        comp (str): folder extension of a comparison case of interest.  Optional - set to None to show just one case.
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        saves daily profile plot to file
        """
    plot_min_max = True
    if variable == 'air_temperature_avg':
        plot_weather = True
    else:
        plot_weather = False
    date = get_date(case, dso, str(day))
    case_df = get_day_df(dso, system, subsystem, variable, day, case, agent_prefix, gld_prefix)
    if plot_weather:
        weather_df = load_weather_data(case, '\\DSO_', str(dso), str(day))
        case_df = case_df.set_index(weather_df.index)
    if comp is not None:
        comp_df = get_day_df(dso, system, subsystem, variable, day, comp, agent_prefix, gld_prefix)
        if plot_weather:
            comp_df = comp_df.set_index(weather_df.index)
    # -------- Plot heatmap of variable for system for day range and DSO
    if subsystem is None:
        subsystem = ''
    plt.figure()
    plt.plot(case_df, label=case.split('\\')[-1], marker='.')
    if plot_min_max:
        if 'real_power_avg' in variable:
            min_df = get_day_df(dso, system, subsystem, variable.replace('avg','min'), day, case, agent_prefix, gld_prefix)
            max_df = get_day_df(dso, system, subsystem, variable.replace('avg','max'), day, case, agent_prefix, gld_prefix)
            plt.plot(min_df, label=case.split('\\')[-1]+'-Min', marker='.')
            plt.plot(max_df, label=case.split('\\')[-1]+'-Max', marker='.')

    if comp is not None:
        plt.plot(comp_df, label=comp.split('\\')[-1])

    if variable == 'air_temperature_avg':
        coolsetpoint_df = get_day_df(dso, system, subsystem, 'air_temperature_setpoint_cooling', day, case, agent_prefix, gld_prefix)
        heatsetpoint_df = get_day_df(dso, system, subsystem, 'air_temperature_setpoint_heating', day, case,
                                     agent_prefix, gld_prefix)
        if plot_weather:
            heatsetpoint_df = heatsetpoint_df.set_index(weather_df.index)
            coolsetpoint_df = coolsetpoint_df.set_index(weather_df.index)
        plt.plot(coolsetpoint_df, label='air_temperature_setpoint_cooling')
        plt.plot(heatsetpoint_df, label='air_temperature_setpoint_heating')
        if plot_weather:
            color = 'tab:red'
            plt.plot(weather_df['temperature'], color=color, linestyle=':', label='out door air temp')
    if variable == 'waterheater_temp_avg':
        setpoint_df = get_day_df(dso, system, subsystem, 'waterheater_setpoint_avg', day, case,
                                     agent_prefix, gld_prefix)
        plt.plot(setpoint_df, label='waterheater_setpoint_avg')
    plt.legend()
    plt.title(system + ' ' + subsystem + ': ' + variable + ' vs. Time (DSO ' + dso + '; Day '
              + date.strftime("%m-%d") + ')')
    plt.xlabel('Time')
    plt.ylabel(variable)
    plot_filename = datetime.now().strftime('%Y%m%d') + '_daily_load_profile_DSO ' + dso + '_day_' \
                    + date.strftime("%m-%d") + system + subsystem + variable + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


def load_duration_plot(dso, system, subsystem, variable, day, case, comp, agent_prefix, gld_prefix):
    """For a specified dso, system, variable, and day this function will load in the required data, plot the load
     duration profile and save the plot to file.  NOTE: currently for one day = should extend to a day-range.
    Arguments:
        dso (str): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum, 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day (str): the day to plotted.
        case (str): folder extension of case of interest
        comp (str): folder extension of a comparison case of interest.  Optional - set to None to show just one case.
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        saves load duration plot to file
        """
    case_df = get_day_df(dso, system, subsystem, variable, day, case, agent_prefix, gld_prefix)
    LDC_case_data = case_df[variable].values.tolist()
    LDC_case_data.sort(reverse=True)
    load_case_data = np.array(LDC_case_data)

    if comp is not None:
        comp_df = get_day_df(dso, system, subsystem, variable, day, comp, agent_prefix, gld_prefix)
        LDC_comp_data = comp_df[variable].values.tolist()
        LDC_comp_data.sort(reverse=True)
        load_comp_data = np.array(LDC_comp_data)

    l = len(load_case_data)
    index = np.array(range(0,l))*100/l

    if subsystem is None:
        subsystem = ''
    plt.clf()
    plt.plot(index, load_case_data, label=case.split('\\')[-1])
    if comp is not None:
        plt.plot(index, load_comp_data, label=comp.split('\\')[-1])
    plt.legend()

    plt.title('Duration vs. Load')
    plt.xlabel('Duration (%)', size = 12)
    plt.xlim(0, 100)
    plt.ylabel(variable, size = 12)
    plt.grid(b=True, which='major', color='k', linestyle='-')
    plt.minorticks_on()

    plot_filename = datetime.now().strftime('%Y%m%d') + system + subsystem + variable + 'Load_Duration_Curve_DSO' + dso + 'Day' + day + '.png'
    file_path_fig = os.path.join(data_path, 'plots',  plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


def dso_comparison_plot(dso_range, system, subsystem, variable, day, case, agent_prefix, gld_prefix):
    """For a specified dso range, system, variable, and day this function will load in the required data, plot the
     variable for all DSOs and save the plot to file.
    Arguments:
        dso_range (range): the DSO range that the data should be plotted for
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum, 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day (str): the day to plotted.
        case (str): folder extension of case of interest
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        saves dso comparison plot to file
        """

    dso_var= []

    plt.figure()

    for dso in dso_range:
        temp_df = get_day_df(str(dso), system, subsystem, variable, day, case, agent_prefix, gld_prefix)
        dso_var.append(temp_df.loc[:, variable])
        plt.plot(dso_var[-1], label='DSO' + str(dso))

    if subsystem is None:
        subsystem = ''
    plt.legend()
    plt.title(system + ' ' + subsystem + ' ' + variable + ' (Day' + day_num + ')')
    plt.xlabel('Time of Day')
    plt.ylabel(variable)

    # plt.suptitle('Day ' + day + ' ' + system + " " + subsystem + ": " + variable)
    plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_DSO_Comparison_Day' + day + system + subsystem + variable + '.png'

    # ------------Save figure to file  --------------------
    file_path_fig = os.path.join(data_path, 'plots',  plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


def dso_market_plot(dso_range, day, case, dso_metadata_file, ercot_dir):
    """For a specified dso range and day this function will load in the required data, plot standard market price and
    quantity values all for DSOs and save the plots to file.
    Arguments:
        dso_range (range): the DSO range that the data should be plotted for
        day (str): the day to plotted.
        case (str): folder extension of case of interest
        dso_metadata_file (str): path and file name of the dso metadata file
        ercot_dir (str): path location of the ercot and industial load metadata
    Returns:
        saves dso comparison plot to file
        """

    date = get_date(case, str(dso_range[0]), day)
    # Load generate_case_config
    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(ercot_dir, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, [int(day)])
    ames_rt_df = load_ames_data(case, range(int(day),int(day)+1))
    industrial_file = os.path.join(ercot_dir, case_config['indLoad'][5].split('/')[-1])
    indust_df = load_indust_data(industrial_file, range(int(day),int(day)+1))

    FNCS = case_config['DSO']

    # Load DSO MetaData
    DSOmetadata = load_json(ercot_dir, dso_metadata_file)

    for dso in dso_range:
        scale_target = DSOmetadata['DSO_' + str(dso)]['scaling_factor']

        # Load substation values
        temp_df = get_day_df(str(dso), 'substation', None, 'real_power_avg', day, case, '/DSO_', '/Substation_')
        temp_df = temp_df.rename(columns={'real_power_avg': 'DSO ' + str(dso)})
        indust_df = indust_df.rename(columns={'Bus' + str(dso): 'DSO ' + str(dso)})
        if dso == dso_range[0]:
            indust_df = indust_df.set_index(temp_df.index)
            substation_df = temp_df.mul(scale_target /1e6).add(indust_df[['DSO ' + str(dso)]])
        else:
            substation_df = substation_df.join(temp_df.mul(scale_target /1e6).add(indust_df[['DSO ' + str(dso)]]))

        # Load RT quantities values
        dsomarket_data_df, dsomarket_bid_df = load_agent_data(case, '/DSO_', str(dso), day, 'dso_market')
        dsomarket_data_df = dsomarket_data_df.droplevel(1, axis=0)
        RT_retail_df, RT_bid_df = load_agent_data(case, '/DSO_', str(dso), str(day), 'retail_market')
        RT_retail_df = RT_retail_df.droplevel(level=1)
        DA_retail_df = load_da_retail_price(case, '/DSO_', str(dso), day)
        DA_dso_df = load_da_retail_price(case, '/DSO_', str(dso), day, False)

        if dso == dso_range[0]:
            rt_q_df = dsomarket_data_df[['cleared_quantity_rt']] / 1e3
            rt_price_df = dsomarket_data_df[['cleared_price_rt']]
            rt_retail_price_df = RT_retail_df[['cleared_price_rt']]
            rt_retail_q_df = RT_retail_df[['cleared_quantity_rt']]/1e3
            rt_retail_q_unadj_df = RT_retail_df[['cleared_quantity_rt_unadj']]/1e3
            rt_retail_congest_df = RT_retail_df[['congestion_surcharge_RT']]
            da_retail_price_df = DA_retail_df[['cleared_price_da']]
            da_dso_price_df = DA_dso_df[['trial_cleared_price_da']]
            da_retail_q_df = DA_retail_df[['cleared_quantity_da']]/1e3
            da_retail_congest_df = DA_retail_df[['congestion_surcharge_DA']]

            q_max_df = pd.DataFrame(np.ones(len(da_retail_q_df.index)) * FNCS[dso-1][3],
                                        index=da_retail_q_df.index,
                                        columns=['DSO '+str(dso)])
        else:
            rt_q_df = rt_q_df.join(dsomarket_data_df[['cleared_quantity_rt']]/1e3)
            rt_price_df = rt_price_df.join(dsomarket_data_df[['cleared_price_rt']])
            rt_retail_price_df = rt_retail_price_df.join(RT_retail_df[['cleared_price_rt']])
            rt_retail_q_df = rt_retail_q_df.join(RT_retail_df[['cleared_quantity_rt']]/1e3)
            rt_retail_q_unadj_df = rt_retail_q_df.join(RT_retail_df[['cleared_quantity_rt_unadj']]/1e3)
            rt_retail_congest_df = rt_retail_congest_df.join(RT_retail_df[['congestion_surcharge_RT']])
            da_retail_price_df = da_retail_price_df.join(DA_retail_df[['cleared_price_da']])
            da_dso_price_df = da_dso_price_df.join(DA_dso_df[['trial_cleared_price_da']])
            da_retail_q_df = da_retail_q_df.join(DA_retail_df[['cleared_quantity_da']]/1e3)
            da_retail_congest_df = da_retail_congest_df.join(DA_retail_df[['congestion_surcharge_DA']])
            q_max_df['DSO '+str(dso)] = np.ones(len(q_max_df)) * FNCS[dso - 1][3]
        rt_q_df = rt_q_df.rename(columns={'cleared_quantity_rt': 'DSO '+str(dso)})
        rt_price_df = rt_price_df.rename(columns={'cleared_price_rt': 'DSO '+str(dso)})
        rt_retail_price_df = rt_retail_price_df.rename(columns={'cleared_price_rt': 'DSO '+str(dso)})
        rt_retail_q_df = rt_retail_q_df.rename(columns={'cleared_quantity_rt': 'DSO '+str(dso)})
        rt_retail_q_unadj_df = rt_retail_q_df.rename(columns={'cleared_quantity_rt_unadj': 'DSO '+str(dso)})
        rt_retail_congest_df = rt_retail_congest_df.rename(columns={'congestion_surcharge_RT': 'DSO '+str(dso)})
        da_retail_price_df = da_retail_price_df.rename(columns={'cleared_price_da': 'DSO '+str(dso)})
        da_dso_price_df = da_dso_price_df.rename(columns={'trial_cleared_price_da': 'DSO ' + str(dso)})
        da_retail_q_df = da_retail_q_df.rename(columns={'cleared_quantity_da': 'DSO '+str(dso)})
        da_retail_congest_df = da_retail_congest_df.rename(columns={'congestion_surcharge_DA': 'DSO '+str(dso)})

    # Load da_q and da_lmp
    ames_da_q_df = load_gen_data(case, 'da_q', range(int(day),int(day)+1))
    ames_da_q_df = ames_da_q_df.unstack(level=1)
    ames_da_q_df.columns = ames_da_q_df.columns.droplevel()

    ames_da_lmp_df = load_gen_data(case, 'da_lmp', range(int(day),int(day)+1))
    ames_da_lmp_df = ames_da_lmp_df.unstack(level=1)
    ames_da_lmp_df.columns = ames_da_lmp_df.columns.droplevel()
    # TODO: Need to check - think this is PyPower results.
    ames_da_gen_df = load_gen_data(case, 'gen', range(int(day), int(day) + 1))

    substation_df = substation_df.set_index(ercot_df.index)

    # ames_rt_df['diff'] = rt_q_df.sum(axis=1) - ames_rt_df[' TotalLoad']
    # # ames_rt_df['diffF'] = (rt_q_df.sum(axis=1) - ames_rt_df[' TotalLoad'])/ rt_q_df.sum(axis=1)
    # # ames_rt_df['diffW'] = (rt_q_df.sum(axis=1) - ames_rt_df[' TotalLoad']) / rt_q_df.sum(axis=1)
    # wind = ames_rt_df.loc[:,ames_rt_df.columns[ames_rt_df.columns.str.contains('wind')]].sum(axis = 1)
    #
    # plt.plot(ames_rt_df['diff'], label='DSO Market RT Q', marker='.')
    # plt.plot(wind, label='DSO Market RT Q', marker='.')

    # RT and DA Q Plot
    plt.figure()
    plt.plot(rt_q_df.sum(axis=1), label='DSO Market RT Q', marker='.')
    plt.plot(substation_df.sum(axis=1), label='Actual Substation+Ind. Power', marker='.')
    # plt.plot(ercot_df.sum(axis=1), label='ERCOT 2106 Load', marker='.')
    plt.plot(da_retail_q_df.sum(axis=1), label='DSO DA Retail Q', marker='.')
    plt.plot(ames_rt_df[' TotalLoad'], label='AMES RT Total Load', marker='.')
    plt.plot(ames_rt_df[' TotalGen'], label='AMES RT Total Gen', marker='.')
    plt.plot(ames_da_q_df.sum(axis=1), label='DA Cleared Q', marker='.')
    plt.plot(ames_da_gen_df.groupby(level=0)['Pgen'].sum(), label='PyPower Generation', marker='.')
    plt.legend()
    plt.title('DSO Market Quantity Comparison (all DSOs; Day ' + date.strftime("%m-%d") + ')')
    plt.xlabel('Time')
    plt.ylabel('Power Quantity (MW)')
    # TODO: work out how to apply the features below to plt.
    # plt.xaxis_date()
    # plt.autofmt_xdate()
    plot_filename = datetime.now().strftime('%Y%m%d') + '_All_DSOs_market_Quantity_Day '  \
                    + date.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # Subplots of quantity for each DSO in dso_range
    if len(dso_range) == 8:
        figw = 20
        figh = 10
        nrows = 2
        ncols = 4
    elif len(dso_range) == 40:
        figw = 40
        figh = 20
        nrows = 5
        ncols = 8
    else:
        raise Exception("dso_market_plots subplots not yet configured for "+len(dso_range)+' subplots.')
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
    fig.suptitle('Comparisons of DSO Quantities: Day'+ date.strftime("%m-%d"))
    for ax, dso in zip(axes.flatten(), dso_range):
        ax.plot(rt_q_df['DSO ' + str(dso)], label='DSO Market RT Q', marker='.')
        ax.plot(da_retail_q_df['DSO ' + str(dso)], label='DSO DA Retail Q', marker='.')
        ax.plot(rt_retail_q_df['DSO ' + str(dso)], label='DSO RT Retail Q', marker='.')
        ax.plot(rt_retail_q_unadj_df['DSO ' + str(dso)], label='DSO RT Retail Q (Unadjusted)', marker='.')
        ax.plot(substation_df['DSO ' + str(dso)], label='Actual Substation+Ind. Power', marker='.')
        ax.plot(ames_da_q_df['da_q'+str(dso)], label='DA Cleared Q', marker='.')
        ax.plot(q_max_df['DSO ' + str(dso)], label='Q Max',  linestyle=':')
        ax.set_title(label='DSO ' + str(dso), pad=-9, )
        ax.xaxis_date()
        ax.set_xlabel('Time')
        ax.set_ylabel('Quantity (MW)')
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right')
    fig.autofmt_xdate()
    plot_filename = datetime.now().strftime('%Y%m%d') + 'compare_DSO_market_Quantity_Day '  \
                    + date.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')

    # Subplots of price (LMP and retail) for each DSO in dso_range
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
    fig.suptitle('Comparisons of DSO Prices: Day'+ date.strftime("%m-%d"))
    for ax, dso in zip(axes.flatten(), dso_range):
        ax.plot(rt_price_df['DSO ' + str(dso)]*1000, label='DSO RT Cleared Price', marker='.')
        ax.plot(rt_retail_price_df['DSO ' + str(dso)]*1000, label='DSO RT Retail Price (w/ congestion)', marker='.')
        ax.plot(rt_retail_price_df['DSO ' + str(dso)] * 1000 - rt_retail_congest_df['DSO ' + str(dso)] * 1000,
                label='DSO RT Retail Price (w/o congestion)', marker='.', linestyle='-.')
        ax.plot(da_retail_price_df['DSO ' + str(dso)]*1000, label='DSO DA Retail Price (w/ congestion)', marker='.')
        ax.plot(da_retail_price_df['DSO ' + str(dso)] * 1000 - da_retail_congest_df['DSO ' + str(dso)] * 1000,
                label='DSO DA Retail Price (w/o congestion)', marker='.', linestyle='-.')
        ax.plot(da_dso_price_df['DSO ' + str(dso)]*1000, label='DSO DA WH Price', marker='.')
        ax.plot(ames_rt_df[' LMP' + str(dso)], label='AMES Realtime LMP', marker='.')
        ax.plot(ames_da_lmp_df['da_lmp'+str(dso)], label='AMES Day Ahead LMP', marker='.')
        ax.set_title(label='DSO ' + str(dso), pad=-9, )
        ax.xaxis_date()
        ax.set_xlabel('Time')
        ax.set_ylabel('Price ($/MW-hr)')
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right')
    fig.autofmt_xdate()
    plot_filename = datetime.now().strftime('%Y%m%d') + 'compare_DSO_market_Price_Day '  \
                    + date.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')


def dso_forecast_stats(dso_range, day_range, case, dso_metadata_file, ercot_dir):
    """For a specified dso range and day range this function will load in the required data, plot forecast errors for
     all for DSOs and save the plots to file.
    Arguments:
        dso_range (range): the DSO range that the data should be plotted for
        day_range (range): the day to plotted.
        case (str): folder extension of case of interest
        dso_metadata_file (str): path and file name of the dso metadata file
        ercot_dir (str): path location of the ercot and industial load metadata
    Returns:
        saves dso comparison plot to file
        """

    date_start = get_date(case, str(dso_range[0]), day_range[0])
    date_end = get_date(case, str(dso_range[0]), day_range[-1])

    # Load DSO MetaData
    DSOmetadata = load_json(ercot_dir, dso_metadata_file)

    # Load generate_case_config
    case_config = load_json(case, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(ercot_dir, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    industrial_file = os.path.join(ercot_dir, case_config['indLoad'][5].split('/')[-1])
    for day in day_range:

        ercot_df = load_ercot_data(metadata_file, sim_start, range(int(day), int(day) + 1))
        indust_df = load_indust_data(industrial_file, range(int(day), int(day) + 1))
        indust_df = indust_df.set_index(ercot_df.index)
        for dso in dso_range:
            scale_target = DSOmetadata['DSO_' + str(dso)]['scaling_factor']

            # Load substation values
            temp_df = get_day_df(str(dso), 'substation', None, 'real_power_avg', str(day), case, '/DSO_', '/Substation_')
            temp_df = temp_df.rename(columns={'real_power_avg': 'DSO ' + str(dso)})
            indust_df = indust_df.rename(columns={'Bus' + str(dso): 'DSO ' + str(dso)})
            temp_df = temp_df.set_index(ercot_df.index)
            if dso == dso_range[0]:
                substation_df = temp_df.mul(scale_target /1e6).add(indust_df[['DSO ' + str(dso)]])
            else:
                substation_df = substation_df.join(
                    temp_df.mul(scale_target / 1e6).add(indust_df[['DSO ' + str(dso)]]))

            # Load RT quantities values
            dsomarket_data_df, dsomarket_bid_df = load_agent_data(case, '/DSO_', str(dso), str(day), 'dso_market')
            dsomarket_data_df = dsomarket_data_df.droplevel(1, axis=0)
            RT_retail_df, RT_bid_df = load_agent_data(case, '/DSO_', str(dso), str(day), 'retail_market')
            RT_retail_df = RT_retail_df.droplevel(level=1)
            DA_retail_df = load_da_retail_price(case, '/DSO_', str(dso), str(day))
            DA_dso_df = load_da_retail_price(case, '/DSO_', str(dso), day, False)

            if dso == dso_range[0]:
                rt_q_df = dsomarket_data_df[['cleared_quantity_rt']] / 1e3
                rt_retail_q_df = RT_retail_df[['cleared_quantity_rt']]/1e3
                da_retail_q_df = DA_retail_df[['cleared_quantity_da']]/1e3
                rt_price_df = dsomarket_data_df[['cleared_price_rt']]
                da_dso_price_df = DA_dso_df[['trial_cleared_price_da']]
            else:
                rt_q_df = rt_q_df.join(dsomarket_data_df[['cleared_quantity_rt']]/1e3)
                rt_retail_q_df = rt_retail_q_df.join(RT_retail_df[['cleared_quantity_rt']]/1e3)
                da_retail_q_df = da_retail_q_df.join(DA_retail_df[['cleared_quantity_da']]/1e3)
                rt_price_df = rt_price_df.join(dsomarket_data_df[['cleared_price_rt']])
                da_dso_price_df = da_dso_price_df.join(DA_dso_df[['trial_cleared_price_da']])

            rt_q_df = rt_q_df.rename(columns={'cleared_quantity_rt': 'DSO '+str(dso)})
            rt_retail_q_df = rt_retail_q_df.rename(columns={'cleared_quantity_rt': 'DSO '+str(dso)})
            da_retail_q_df = da_retail_q_df.rename(columns={'cleared_quantity_da': 'DSO '+str(dso)})
            rt_price_df = rt_price_df.rename(columns={'cleared_price_rt': 'DSO '+str(dso)})
            da_dso_price_df = da_dso_price_df.rename(columns={'trial_cleared_price_da': 'DSO '+str(dso)})

        if day == day_range[0]:
            load = substation_df
            rt_q_forecast = rt_q_df
            da_q_forecast = da_retail_q_df
            rt_lmp_forecast = rt_price_df
            da_lmp_forecast = da_dso_price_df
        else:
            load = pd.concat([load, substation_df])
            rt_q_forecast = pd.concat([rt_q_forecast, rt_q_df])
            da_q_forecast = pd.concat([da_q_forecast, da_retail_q_df])
            rt_lmp_forecast = pd.concat([rt_lmp_forecast, rt_price_df])
            da_lmp_forecast = pd.concat([da_lmp_forecast, da_dso_price_df])

        # substation_df = substation_df.set_index(ercot_df.index)

    load['Total'] = load.sum(axis=1)
    rt_q_forecast['Total'] = rt_q_forecast.sum(axis=1)
    da_q_forecast['Total'] = da_q_forecast.sum(axis=1)


    ames_rt_df = load_ames_data(case, day_range)
    ames_da_lmp_df = load_gen_data(case, 'da_lmp', day_range)
    ames_da_lmp_df = ames_da_lmp_df.unstack(level=1)
    ames_da_lmp_df.columns = ames_da_lmp_df.columns.droplevel()

    cols = []
    for dso in dso_range:
        ames_rt_df = ames_rt_df.rename(columns={' LMP' + str(dso): 'DSO ' + str(dso)})
        ames_da_lmp_df = ames_da_lmp_df.rename(columns={'da_lmp' + str(dso): 'DSO ' + str(dso)})
        cols.append('DSO ' + str(dso))
    ames_rt_df = ames_rt_df[cols]
    ames_da_lmp_df = ames_da_lmp_df[cols]

    rt_q_error_df = rt_q_forecast.subtract(load).divide(load)
    da_q_error_df = da_q_forecast.subtract(load.groupby(pd.Grouper(freq='H')).mean()).divide(load.groupby(pd.Grouper(freq='H')).mean())
    rt_lmp_error_df = rt_lmp_forecast.subtract(ames_rt_df/1000).divide(ames_rt_df/1000)
    da_lmp_error_df = da_lmp_forecast.subtract(ames_da_lmp_df/1000).divide(ames_da_lmp_df/1000)

    # Save data to csv for later use (e.g. annual aggregation)
    rt_q_forecast.to_csv(path_or_buf=case + '/RT_Q_forecast.csv')
    rt_q_error_df.to_csv(path_or_buf=case + '/RT_Q_error.csv')
    rt_lmp_error_df.to_csv(path_or_buf=case + '/RT_LMP_error.csv')
    da_q_forecast.to_csv(path_or_buf=case + '/DA_Q_forecast.csv')
    da_q_error_df.to_csv(path_or_buf=case + '/DA_Q_error.csv')
    da_lmp_error_df.to_csv(path_or_buf=case + '/DA_LMP_error.csv')

    # AMES initialization can have zero LMPs so need to clean up infs
    rt_lmp_error_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    rt_lmp_error_df.dropna(inplace=True)
    da_lmp_error_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    da_lmp_error_df.dropna(inplace=True)

    stats = True

    # Subplots of quantity for each DSO in dso_range
    if len(dso_range) == 8:
        figw = 20
        figh = 10
        nrows = 2
        ncols = 4
        text_size = 10
    elif len(dso_range) == 40:
        figw = 40
        figh = 20
        nrows = 5
        ncols = 8
        text_size = 5
    else:
        raise Exception("dso_forecast_stats subplots not yet configured for "+len(dso_range)+' subplots.')
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
    fig.suptitle('Comparisons of DSO Realtime Quantity Relative Forecast Errors: '+ date_start.strftime("%m-%d") +' through ' + date_end.strftime("%m-%d"))
    for ax, dso in zip(axes.flatten(), dso_range):
        ax.hist(rt_q_error_df['DSO ' + str(dso)], label='DSO Market RT Q', bins=20)
        if stats:
            mean = np.format_float_positional(rt_q_error_df['DSO '+str(dso)].mean(), precision=3, unique=False, fractional=False, trim='k')
            std = np.format_float_positional(rt_q_error_df['DSO '+str(dso)].std(), precision=3, unique=False, fractional=False, trim='k')
            rms = np.format_float_positional((rt_q_error_df['DSO '+str(dso)]** 2).mean() ** .5, precision=3, unique=False, fractional=False, trim='k')
            ax.text(0.2, 0.95, "Mean = " + mean, size=text_size, horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.text(0.2, 0.88, "Stdev = " + std, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.text(0.2, 0.81, "RMS = " + rms, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
        ax.set_title(label='DSO ' + str(dso), pad=-9, )
        ax.set_xlabel('Relative Error')
    plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_realtime_quantity_forecast_error'  \
                    + date_start.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
    fig.suptitle('Comparisons of DSO Day-ahead Quantity Relative Forecast Errors: '+ date_start.strftime("%m-%d") +' through ' + date_end.strftime("%m-%d"))
    for ax, dso in zip(axes.flatten(), dso_range):
        ax.hist(da_q_error_df['DSO ' + str(dso)], label='DSO Market RT Q', bins=10)
        if stats:
            mean = np.format_float_positional(da_q_error_df['DSO '+str(dso)].mean(), precision=3, unique=False, fractional=False, trim='k')
            std = np.format_float_positional(da_q_error_df['DSO '+str(dso)].std(), precision=3, unique=False, fractional=False, trim='k')
            rms = np.format_float_positional((da_q_error_df['DSO '+str(dso)]** 2).mean() ** .5, precision=3, unique=False, fractional=False, trim='k')
            ax.text(0.2, 0.95, "Mean = " + mean , size=text_size, horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.text(0.2, 0.88, "Stdev = " + std, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.text(0.2, 0.81, "RMS = " + rms, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
        ax.set_title(label='DSO ' + str(dso), pad=-9, )
        ax.set_xlabel('Relative Error')
    plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_day_ahead_quantity_forecast_error'  \
                    + date_start.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
    fig.suptitle('Comparisons of DSO Realtime LMP Relative Forecast Errors: '+ date_start.strftime("%m-%d") +' through ' + date_end.strftime("%m-%d"))
    for ax, dso in zip(axes.flatten(), dso_range):
        ax.hist(rt_lmp_error_df['DSO ' + str(dso)], label='DSO Market RT Q', bins=20)
        if stats:
            mean = np.format_float_positional(rt_lmp_error_df['DSO '+str(dso)].mean(), precision=3, unique=False, fractional=False, trim='k')
            std = np.format_float_positional(rt_lmp_error_df['DSO '+str(dso)].std(), precision=3, unique=False, fractional=False, trim='k')
            rms = np.format_float_positional((rt_lmp_error_df['DSO '+str(dso)]** 2).mean() ** .5, precision=3, unique=False, fractional=False, trim='k')
            ax.text(0.2, 0.95, "Mean = " + mean, size=text_size, horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.text(0.2, 0.88, "Stdev = " + std, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.text(0.2, 0.81, "RMS = " + rms, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
        ax.set_title(label='DSO ' + str(dso), pad=-9, )
        ax.set_xlabel('Relative Error')
    plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_realtime_LMP_forecast_error'  \
                    + date_start.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(figw, figh))
    fig.suptitle('Comparisons of DSO Day-ahead LMP Relative Forecast Errors: '+ date_start.strftime("%m-%d") +' through ' + date_end.strftime("%m-%d"))
    for ax, dso in zip(axes.flatten(), dso_range):
        ax.hist(da_lmp_error_df['DSO ' + str(dso)], label='DSO Market RT Q', bins=10)
        if stats:
            mean = np.format_float_positional(da_lmp_error_df['DSO '+str(dso)].mean(), precision=3, unique=False, fractional=False, trim='k')
            std = np.format_float_positional(da_lmp_error_df['DSO '+str(dso)].std(), precision=3, unique=False, fractional=False, trim='k')
            rms = np.format_float_positional((da_lmp_error_df['DSO '+str(dso)]** 2).mean() ** .5, precision=3, unique=False, fractional=False, trim='k')
            ax.text(0.2, 0.95, "Mean = " + mean , size=text_size, horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            ax.text(0.2, 0.88, "Stdev = " + std, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.text(0.2, 0.81, "RMS = " + rms, size=text_size, horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
        ax.set_title(label='DSO ' + str(dso), pad=-9, )
        ax.set_xlabel('Relative Error')
    plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_day_ahead_LMP_forecast_error'  \
                    + date_start.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')

    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(11, 6))
    fig.suptitle('Comparisons of Total Relative Load Forecast Errors: '+ date_start.strftime("%m-%d") +' through ' + date_end.strftime("%m-%d"))
    axes[0].hist(da_q_error_df['Total'], label='DSO Total DA Q Error', bins=10)
    if stats:
        mean = np.format_float_positional(da_q_error_df['Total'].mean(), precision=3, unique=False, fractional=False, trim='k')
        std = np.format_float_positional(da_q_error_df['Total'].std(), precision=3, unique=False, fractional=False, trim='k')
        rms = np.format_float_positional((da_q_error_df['Total']** 2).mean() ** .5, precision=3, unique=False, fractional=False, trim='k')
        axes[0].text(0.2, 0.95, "Mean = " + mean , size=text_size, horizontalalignment='center', verticalalignment='center', transform=axes[0].transAxes)
        axes[0].text(0.2, 0.88, "Stdev = " + std, size=text_size, horizontalalignment='center', verticalalignment='center',
                transform=axes[0].transAxes)
        axes[0].text(0.2, 0.81, "RMS = " + rms, size=text_size, horizontalalignment='center', verticalalignment='center',
                transform=axes[0].transAxes)
    axes[0].set_title(label='Day Ahead', pad=-9, )
    axes[0].set_xlabel('Relative Error')
    axes[1].hist(rt_q_error_df['Total'], label='DSO Total RT Q Error', bins=20)
    if stats:
        mean = np.format_float_positional(rt_q_error_df['Total'].mean(), precision=3, unique=False, fractional=False, trim='k')
        std = np.format_float_positional(rt_q_error_df['Total'].std(), precision=3, unique=False, fractional=False, trim='k')
        rms = np.format_float_positional((rt_q_error_df['Total']** 2).mean() ** .5, precision=3, unique=False, fractional=False, trim='k')
        axes[1].text(0.2, 0.95, "Mean = " + mean , size=text_size, horizontalalignment='center', verticalalignment='center', transform=axes[1].transAxes)
        axes[1].text(0.2, 0.88, "Stdev = " + std, size=text_size, horizontalalignment='center', verticalalignment='center',
                transform=axes[1].transAxes)
        axes[1].text(0.2, 0.81, "RMS = " + rms, size=text_size, horizontalalignment='center', verticalalignment='center',
                transform=axes[1].transAxes)
    axes[1].set_title(label='Real Time', pad=-9, )
    axes[1].set_xlabel('Relative Error')
    plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_total_Q_forecast_error'  \
                    + date_start.strftime("%m-%d") + '.png'
    file_path_fig = os.path.join(case, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')


def dso_load_stats(dso_range, month_list, data_path, metadata_path, plot = False):
    """For a specified dso range and list of month path information this function will load in the required data,
    and summarize DSO loads for all months, plot comparisons, and find Qmax.
    Arguments:
        dso_range (range): the DSO range that the data should be plotted for
        month_list (list): list of lists.  Each sub list has month name (str), directory path (str)
        data_path (str): path of the location where output (plots, csv) should be saved
        metadata_path (str): location of ercot load data
    Returns:
        saves dso load comparison plots to file
        saves summary of Qmax for each DSO to file
        """
    # Aggregate all the monthly data
    # Load commesurate ERCOT Load data

    for i in range(len(month_list)):
        filename = (month_list[i][1] + '\\DER_profiles.h5')
        der_loads_df = pd.read_hdf(filename, key='DER_Profiles', mode='r')
        # Add data for loads by building type
        filename = (month_list[i][1] + '\\Building_profiles.h5')
        building_loads_df = pd.read_hdf(filename, key='Bldg_Profiles', mode='r')
        duplicate_cols = ['Substation', 'Industrial']
        comm_bldgs = ['office', 'warehouse_storage', 'big_box', 'strip_mall', 'education',
               'food_service', 'food_sales', 'lodging', 'low_occupancy']
        res_bldgs = ['MOBILE_HOME', 'MULTI_FAMILY', 'SINGLE_FAMILY']
        building_loads_df.drop(duplicate_cols, inplace=True, axis=1)
        building_loads_df['total_comm'] = building_loads_df[comm_bldgs].sum(axis=1)
        building_loads_df['total_res'] = building_loads_df[res_bldgs].sum(axis=1)
        der_loads_df = pd.merge(der_loads_df, building_loads_df, left_index=True, right_index=True)
       # Load generate_case_config
        case_config = load_json(month_list[i][1], 'generate_case_config.json')
        # Load ERCOT load profile data
        metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
        sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
        ercot_df = load_ercot_data(metadata_file, sim_start, range(month_list[i][2], month_list[i][3]))
        ercot_sum = ercot_df.loc[:, ercot_df.columns[ercot_df.columns.str.contains('Bus')]].sum(
            axis=1)
        ercot_sum_df = pd.DataFrame(ercot_sum)
        ercot_sum_df = ercot_sum_df.rename(columns={0: 'ERCOT Net Load'})

        # Slice data to ensure there is no overlap in monthly datasets
        generate_case_config = load_json(month_list[i][1], 'generate_case_config.json')

        start_time = datetime.strptime(generate_case_config['StartTime'], '%Y-%m-%d %H:%M:%S') + timedelta(days=month_list[i][2]-1)
        end_time = datetime.strptime(generate_case_config['StartTime'], '%Y-%m-%d %H:%M:%S') + timedelta(days=month_list[i][3]-1) - timedelta(minutes=5)
        if i != 0:
            start_time = max(start_time, previous_end_time + timedelta(minutes=5))
        der_loads_df.sort_index(inplace=True)
        der_loads_df = der_loads_df.loc[start_time:end_time, :]
        previous_end_time = end_time

        if i == 0:
            dso_loads_df = der_loads_df
            ercot_loads_df = ercot_sum_df
        else:
            dso_loads_df = pd.concat([dso_loads_df, der_loads_df])
            ercot_loads_df = pd.concat([ercot_loads_df, ercot_sum_df])
    dso_loads_df['Total Load'] = dso_loads_df['Substation'] + dso_loads_df['Industrial Loads']
    ercot_loads_df['Month'] = ercot_loads_df.index.month

    dso_total_df = dso_loads_df.groupby(level=0).sum()
    dso_total_df['Month'] = dso_total_df.index.month
    dso_total_df.to_csv(path_or_buf=data_path + '/DSO_Total_Loads.csv')

    # Merge to remove any duplicate dso timestamps.
    dso_total_df = pd.merge(ercot_loads_df['ERCOT Net Load'], dso_total_df, left_index=True, right_index=True)

    dso_load_stats = pd.DataFrame(index=['Average', 'Sum', 'Max', 'Min', 'Average Daily Range'],
                            columns=dso_total_df.columns)

    dso_daily_max_df = dso_total_df.groupby(pd.Grouper(freq='D')).max()
    dso_daily_min_df = dso_total_df.groupby(pd.Grouper(freq='D')).min()
    dso_daily_range_df = dso_total_df.groupby(pd.Grouper(freq='D')).max()-dso_total_df.groupby(pd.Grouper(freq='D')).min()
    dso_daily_range_df['Month'] = dso_daily_range_df.index.month

    dso_load_stats.loc['Average', :] = dso_total_df.mean()
    dso_load_stats.loc['Sum', :] = dso_total_df.sum()/12
    dso_load_stats.loc['Max', :] = dso_total_df.max()
    dso_load_stats.loc['Min', :] = dso_total_df.min()

    dso_load_stats.loc['Average Daily Range', :] = dso_daily_range_df.mean()
    dso_load_stats.loc['Max Daily Range', :] = dso_daily_range_df.max()
    dso_load_stats.loc['Min Daily Range', :] = dso_daily_range_df.min()
    dso_load_stats.loc['Average Daily Max', :] = dso_daily_max_df.mean()
    dso_load_stats.loc['Average Daily Min', :] = dso_daily_min_df.mean()

    for col in dso_load_stats.columns:
        dso_load_stats.loc['Max Index', col] = dso_total_df[col].idxmax()
        dso_load_stats.loc['Min Index', col] = dso_total_df[col].idxmin()
        dso_load_stats.loc['Max Daily Range Index', col] = dso_daily_range_df[col].idxmax()
        dso_load_stats.loc['Min Daily Range Index', col] = dso_daily_range_df[col].idxmin()

    # Find and save QMax for each DSO.
    Qmax = {}
    for dso in dso_range:
        Qmax['DSO_'+str(dso)] = [dso_loads_df.loc[(slice(None), 'dso'+str(dso)),'Total Load'].max(),
                                 dso_loads_df.loc[(slice(None), 'dso' + str(dso)), 'Total Load'].idxmax()[0]]

    Qmax_df = pd.DataFrame.from_dict(Qmax, orient='index', columns=['Qmax (MW)','Time of Peak'])

    os.chdir(data_path)
    Qmax_df.to_csv(path_or_buf=data_path + '/Qmax.csv')

    dso_load_stats.to_csv(path_or_buf=data_path + '/DSO_load_stats.csv')

    # Create summary of load statistics
    if plot:

        # Plot comparison of monthly loads versus ERCOT.

        fig, axes = plt.subplots(2, 1, figsize=(11, 10), sharex=True)

        upper_limit = 78000
        lower_limit = 0
        name = 'Total Load'
        sns.boxplot(data=dso_total_df, x='Month', y=name, ax=axes[0])
        axes[0].set_ylabel('MW')
        axes[0].set_title('Annual Load Variation: Simulation')
        axes[0].set_xlabel('')
        axes[0].set_ylim(top=upper_limit, bottom=lower_limit)

        sns.boxplot(data=dso_total_df, x='Month', y='ERCOT Net Load', ax=axes[1])
        axes[1].set_ylabel('MW')
        axes[1].set_title('Annual Load Variation: ERCOT 2016')
        axes[1].set_xlabel('')
        axes[1].set_ylim(top=upper_limit, bottom=lower_limit)

        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_Load_Box_Plots.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        #  Daily Load Range Box Plot
        fig, axes = plt.subplots(2, 1, figsize=(11, 10), sharex=True)

        upper_limit = 45000
        lower_limit = 0
        name = 'Total Load'
        sns.boxplot(data=dso_daily_range_df, x='Month', y=name, ax=axes[0])
        axes[0].set_ylabel('MW')
        axes[0].set_title('Annual Daily Load Range Variation: Simulation')
        axes[0].set_xlabel('')
        axes[0].set_ylim(top=upper_limit, bottom=lower_limit)

        sns.boxplot(data=dso_daily_range_df, x='Month', y='ERCOT Net Load', ax=axes[1])
        axes[1].set_ylabel('MW')
        axes[1].set_title('Annual Daily Load Range Variation: ERCOT 2016')
        axes[1].set_xlabel('')
        axes[1].set_ylim(top=upper_limit, bottom=lower_limit)

        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_Daily_Load_Range_Box_Plots.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        #  Daily Load Values and Range Box Plot (side-by-side comparison)
        comparison_df = dso_total_df[['Total Load', 'Month']]
        comparison_df['Case'] = 'DSO+T'
        compare2_df = dso_total_df[['ERCOT Net Load', 'Month']]
        compare2_df['Case'] = 'ERCOT'
        compare2_df.rename(columns={'ERCOT Net Load': 'Total Load'}, inplace=True)
        comparison_df = pd.concat([compare2_df, comparison_df])

        range_compare_df = dso_daily_range_df[['Total Load', 'Month']]
        range_compare_df['Case'] = 'DSO+T'
        range_compare2_df = dso_daily_range_df[['ERCOT Net Load', 'Month']]
        range_compare2_df['Case'] = 'ERCOT'
        range_compare2_df.rename(columns={'ERCOT Net Load': 'Total Load'}, inplace=True)
        range_compare_df = pd.concat([range_compare2_df, range_compare_df])

        fig, axes = plt.subplots(2, 1, figsize=(11, 10), sharex=True)
        pal = ["gold"] + ['skyblue']

        upper_limit = 45000
        lower_limit = 0
        name = 'Total Load'
        sns.boxplot(data=comparison_df, x='Month', y=name, hue='Case', ax=axes[0], palette = pal)
        axes[0].set_ylabel('MW')
        axes[0].set_title('Variation in Load over the Year')
        axes[0].set_xlabel('')
        axes[0].set_ylim(top=78000, bottom=lower_limit)
        handles, labels = axes[0].get_legend_handles_labels()
        axes[0].legend(handles=handles, labels=labels)

        sns.boxplot(data=range_compare_df, x='Month', y='Total Load', hue='Case', ax=axes[1], palette = pal)
        axes[1].set_ylabel('MW')
        axes[1].set_title('Variation in Daily Load Change over the Year')
        axes[1].set_xlabel('Month')
        axes[1].set_ylim(top=upper_limit, bottom=lower_limit)
        handles, labels = axes[1].get_legend_handles_labels()
        axes[1].legend(handles=handles, labels=labels)

        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_Daily_Load_SBS_Box_Plots.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')


def dso_lmp_stats(month_list, output_path, renew_forecast_file):
    """For a specified dso range and list of month path information this function will load in the required data,
    and summarize DSO LMPs versus loads for all months, and plot comparisons.
    Arguments:
        month_list (list): list of lists.  Each sub list has month name (str), directory path (str)
        output_path (str): path of the location where output (plots, csv) should be saved
        renew_forecast_file (str): path and name of ercot renewable generation forecast csv file
    Returns:
        saves dso load comparison plots to file
        saves csv of RT and DA loads and LMPs to file
        """
    # Aggregate all the monthly data for RT loads and LMPs
    for i in range(len(month_list)):
        ames_rt_q_df = load_gen_data(month_list[i][1], 'rt_q', range(month_list[i][2], month_list[i][3]))
        ames_rt_q_df = ames_rt_q_df.unstack(level=1)
        ames_rt_q_df.columns = ames_rt_q_df.columns.droplevel()

        ames_df = load_ames_data(month_list[i][1], range(month_list[i][2], month_list[i][3]))

        if i == 0:
            dso_lmps_df = ames_rt_q_df
            ames_lmps_df = ames_df
        else:
            dso_lmps_df = pd.concat([dso_lmps_df, ames_rt_q_df])
            ames_lmps_df = pd.concat([ames_lmps_df, ames_df])

    ames_lmps_df['NetLoad'] = ames_lmps_df[' TotalLoad'] - ames_lmps_df[' TotRenGen']
    lmp_cols = [col for col in ames_lmps_df.columns if 'LMP' in col]
    cols = [' TotalLoad', ' TotalGen', 'NetLoad'] + lmp_cols
    # dso_lmps_df = dso_lmps_df.join(ames_lmps_df[cols])
    dso_lmps_df = pd.merge(dso_lmps_df, ames_lmps_df[cols], left_index=True, right_index=True)
    dso_lmps_df.to_csv(path_or_buf=output_path + '\\Annual_RT_LMP_Load_data.csv')
    # Save out a multi-month (i.e. annual) opf file that can be used for generator plotting and statistics
    ames_lmps_df.index.set_names(['seconds'], inplace=True)
    ames_lmps_df.to_csv(path_or_buf=output_path + '\\opf.csv')

    # Aggregate all the monthly data for RT loads and LMPs
    for i in range(len(month_list)):
        # Load da_q and da_lmp
        ames_da_q_df = load_gen_data(month_list[i][1], 'da_q', range(month_list[i][2], month_list[i][3]))
        ames_da_q_df = ames_da_q_df.unstack(level=1)
        ames_da_q_df.columns = ames_da_q_df.columns.droplevel()

        ames_da_lmp_df = load_gen_data(month_list[i][1], 'da_lmp', range(month_list[i][2], month_list[i][3]))
        ames_da_lmp_df = ames_da_lmp_df.unstack(level=1)
        ames_da_lmp_df.columns = ames_da_lmp_df.columns.droplevel()

        if i == 0:
            da_loads_df = ames_da_q_df
            da_lmps_df = ames_da_lmp_df
        else:
            da_loads_df = pd.concat([da_loads_df, ames_da_q_df])
            da_lmps_df = pd.concat([da_lmps_df, ames_da_lmp_df])

    da_lmps_df = da_lmps_df.join(da_loads_df)

    da_load_cols = [col for col in da_lmps_df.columns if 'da_q' in col]
    da_lmps_df[' TotalLoad'] = da_lmps_df[da_load_cols].sum(axis=1)
    # renew_forecast_file = 'C:\\Users\\reev057\\PycharmProjects\TESP\src\examples\\data\\mod_renew_forecast.csv'
    renew_forecast = pd.read_csv(renew_forecast_file, index_col='time')
    renew_forecast['TotalRenewGen'] = renew_forecast.sum(axis=1)
    da_lmps_df = pd.merge(da_lmps_df, renew_forecast[['TotalRenewGen']], left_index=True, right_index=True)
    da_lmps_df['NetLoad'] = da_lmps_df[' TotalLoad'] - da_lmps_df['TotalRenewGen']
    da_lmps_df.to_csv(path_or_buf=output_path + '/Annual_DA_LMP_Load_data.csv')


def plot_lmp_stats(data_path, output_path, dso_num, month_index = 8):
    """Will plot LMPS by month, duration, and versus netloads loads (for select month), and save to file.
    Arguments:
        data_path (str): location of the data files to be used.
        output_path (str): path of the location where output (plots, csv) should be saved
        dso_num (str): bus number for LMP data to be plotted
    Returns:
        saves dso lmps plots to file
        """

    da_lmps_df = pd.read_csv(data_path + '/Annual_DA_LMP_Load_data.csv', index_col=[0])
    rt_lmps_df = pd.read_csv(data_path + '/Annual_RT_LMP_Load_data.csv', index_col=[0])

    da_lmps_df = da_lmps_df.set_index(pd.to_datetime(da_lmps_df.index))
    da_lmps_df['Month'] = da_lmps_df.index.month
    lmp_col = [col for col in da_lmps_df.columns if 'lmp' in col]
    da_lmps_df['LMP Delta'] = da_lmps_df[lmp_col].max(axis=1) - da_lmps_df[lmp_col].min(axis=1)

    rt_lmps_df = rt_lmps_df.set_index(pd.to_datetime(rt_lmps_df.index))
    rt_lmps_df['Month'] = rt_lmps_df.index.month

    da_lmps_daily_df = pd.Series.to_frame(da_lmps_df['da_lmp'+dso_num].groupby(pd.Grouper(freq='D')).max()
                                              - da_lmps_df['da_lmp'+dso_num].groupby(pd.Grouper(freq='D')).min())
    da_lmps_daily_df['stdev'] = da_lmps_df['da_lmp'+dso_num].groupby(pd.Grouper(freq='D')).std()
    da_lmps_daily_df['Month'] = da_lmps_daily_df.index.month
    da_lmps_daily_df.dropna(subset=['da_lmp'+dso_num], inplace=True)

    rt_lmps_daily_df = pd.Series.to_frame(rt_lmps_df[' LMP'+dso_num].groupby(pd.Grouper(freq='D')).max()
                                              - rt_lmps_df[' LMP'+dso_num].groupby(pd.Grouper(freq='D')).min())
    rt_lmps_daily_df['stdev'] = rt_lmps_df[' LMP'+dso_num].groupby(pd.Grouper(freq='D')).std()
    rt_lmps_daily_df['Month'] = rt_lmps_daily_df.index.month
    rt_lmps_daily_df.dropna(subset=[' LMP'+dso_num], inplace=True)


    # Create summary comparison plots of simulation LMP versus actual data.
    stats = True

    ERCOTDApricerange = pd.read_hdf(data_path + '\\ERCOT_LMP.h5', key='DADeltaLMP_data', mode='r')
    ERCOTDAPrices = pd.read_hdf(data_path + '\\ERCOT_LMP.h5', key='DALMP_data', mode='r')

    ERCOTRTpricerange = pd.read_hdf(data_path + '\\ERCOT_LMP.h5', key='RTDeltaLMP_data', mode='r')
    ERCOTRTPrices = pd.read_hdf(data_path + '\\ERCOT_LMP.h5', key='RTLMP_data', mode='r')

    CAISODApricerange = pd.read_hdf(data_path + '\\CAISO_LMP.h5', key='DADeltaLMP_data', mode='r')
    CAISODAPrices = pd.read_hdf(data_path + '\\CAISO_LMP.h5', key='DALMP_data', mode='r')

    PJMDApricerange = pd.read_hdf(data_path + '\\PJM_LMP.h5', key='DADeltaLMP_data', mode='r')
    PJMDAPrices = pd.read_hdf(data_path + '\\PJM_LMP.h5', key='DALMP_data', mode='r')

    PJMRTpricerange = pd.read_hdf(data_path + '\\PJM_LMP.h5', key='RTDeltaLMP_data', mode='r')
    PJMRTPrices = pd.read_hdf(data_path + '\\PJM_LMP.h5', key='RTLMP_data', mode='r')

    ERCOT_LMP_DELTA = pd.read_excel(data_path + '\\DAM_2016.xlsx', sheet_name='LMP Delta')

    # =========== Create box plots 1- DA spread ===========================

    label_size = 17
    num_size = 14
    #
    #
    # fig, axes = plt.subplots(4, 1, figsize=(11, 15), sharex=True)
    #
    # sns.boxplot(data=ERCOTDAPrices, x='Month', y='Houston $_mwh', ax=axes[0])
    # axes[0].set_ylabel('$/mw-hr', size=label_size)
    # axes[0].set_title('ERCOT DA LMP', size=label_size)
    # axes[0].set_xlabel('')
    # axes[0].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # sns.boxplot(data=CAISODAPrices, x='Month', y='LMP_PRC', ax=axes[1])
    # axes[1].set_ylabel('$/mw-hr', size=label_size)
    # axes[1].set_title('CAISO DA LMP', size=label_size)
    # axes[1].set_xlabel('')
    # axes[1].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # sns.boxplot(data=PJMDAPrices, x='Month', y='total_lmp_da', ax=axes[2])
    # axes[2].set_ylabel('$/mw-hr', size=label_size)
    # axes[2].set_title('PJM DA LMP', size=label_size)
    # axes[2].set_xlabel('')
    # axes[2].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # sns.boxplot(data=da_lmps_df, x='Month', y='da_lmp'+dso_num, ax=axes[3])
    # axes[3].set_ylabel('$/mw-hr', size=label_size)
    # axes[3].set_xlabel('Month', size=label_size)
    # axes[3].set_title('DSO+T Simulation', size=label_size)
    # axes[3].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # plot_filename = datetime.now().strftime(
    #     '%Y%m%d') + 'ISO_DA_LMP_Annual_Box_Plots.png'
    # file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    # plt.savefig(file_path_fig, bbox_inches='tight')
    #
    # LMP_plot_limit = 80
    # axes[0].set_ylim(top=LMP_plot_limit, bottom=0)
    # axes[1].set_ylim(top=LMP_plot_limit, bottom=0)
    # axes[2].set_ylim(top=LMP_plot_limit, bottom=0)
    # axes[3].set_ylim(top=LMP_plot_limit, bottom=0)
    #
    # plot_filename = datetime.now().strftime(
    #     '%Y%m%d') + 'ISO_DA_LMP_Annual_Box_Plots-focused.png'
    # file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    # plt.savefig(file_path_fig, bbox_inches='tight')
    #
    # # =========== Create box plots 2- DA daily range spread ===========================
    #
    # fig, axes = plt.subplots(4, 1, figsize=(11, 15), sharex=True)
    #
    # sns.boxplot(data=ERCOTDApricerange, x='Month', y='Houston $_mwh', ax=axes[0])
    # axes[0].set_ylabel('$/mw-hr', size=label_size)
    # axes[0].set_title('ERCOT Daily variation in DA LMP', size=label_size)
    # axes[0].set_xlabel('')
    # axes[0].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # sns.boxplot(data=CAISODApricerange, x='Month', y='LMP_PRC', ax=axes[1])
    # axes[1].set_ylabel('$/mw-hr', size=label_size)
    # axes[1].set_title('CAISO Daily variation in DA LMP', size=label_size)
    # axes[1].set_xlabel('')
    # axes[1].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # sns.boxplot(data=PJMDApricerange, x='Month', y='total_lmp_da', ax=axes[2])
    # axes[2].set_ylabel('$/mw-hr', size=label_size)
    # axes[2].set_xlabel(' ', size=label_size)
    # axes[2].set_title('PJM Daily variation in DA LMP', size=label_size)
    # axes[2].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # sns.boxplot(data=da_lmps_daily_df, x='Month', y='da_lmp'+dso_num, ax=axes[3])
    # axes[3].set_ylabel('$/mw-hr', size=label_size)
    # axes[3].set_xlabel('Month', size=label_size)
    # axes[3].set_title('DSO+T Daily variation in DA LMP', size=label_size)
    # axes[3].tick_params(axis='both', which='major', labelsize=num_size)
    #
    # plot_filename = datetime.now().strftime(
    #     '%Y%m%d') + 'ISO_Daily_variation_DA_LMP_Annual_Box_Plots.png'
    # file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    # plt.savefig(file_path_fig, bbox_inches='tight')
    #
    # LMP_plot_limit = 100
    # axes[0].set_ylim(top=LMP_plot_limit, bottom=0)
    # axes[1].set_ylim(top=LMP_plot_limit, bottom=0)
    # axes[2].set_ylim(top=LMP_plot_limit, bottom=0)
    # axes[3].set_ylim(top=LMP_plot_limit, bottom=0)
    #
    # plot_filename = datetime.now().strftime(
    #     '%Y%m%d') + 'ISO_Daily_variation_DA_LMP_Annual_Box_Plots-focused.png'
    # file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    # plt.savefig(file_path_fig, bbox_inches='tight')

    # =========== Create DA LMP value and range plot - all cases side by side ===========================

    lmp_comparison_df = da_lmps_df[['da_lmp' + dso_num, 'Month']]
    lmp_comparison_df.rename(columns={'da_lmp' + dso_num: 'DA LMP'}, inplace=True)
    lmp_comparison_df['Case'] = 'DSO+T'
    ERCOTcompare_df = ERCOTDAPrices[['Houston $_mwh', 'Month']]
    ERCOTcompare_df['Case'] = 'ERCOT'
    ERCOTcompare_df.rename(columns={'Houston $_mwh': 'DA LMP'}, inplace=True)
    PJMcompare_df = PJMDAPrices[['total_lmp_da', 'Month']]
    PJMcompare_df['Case'] = 'PJM'
    PJMcompare_df.rename(columns={'total_lmp_da': 'DA LMP'}, inplace=True)
    CALISOcompare_df = CAISODAPrices[['LMP_PRC', 'Month']]
    CALISOcompare_df['Case'] = 'CAISO'
    CALISOcompare_df.rename(columns={'LMP_PRC': 'DA LMP'}, inplace=True)
    lmp_comparison_df = pd.concat([CALISOcompare_df, PJMcompare_df, ERCOTcompare_df, lmp_comparison_df])

    rangelmp_comparison_df = da_lmps_daily_df[['da_lmp' + dso_num, 'Month']]
    rangelmp_comparison_df.rename(columns={'da_lmp' + dso_num: 'DA LMP'}, inplace=True)
    rangelmp_comparison_df['DA LMP STD'] = da_lmps_daily_df['stdev']
    rangelmp_comparison_df['Case'] = 'DSO+T'
    rangeERCOTcompare_df = ERCOTDApricerange[['Houston $_mwh', 'Month']]
    rangeERCOTcompare_df['DA LMP STD'] = ERCOTDApricerange['stdev']
    rangeERCOTcompare_df['Case'] = 'ERCOT'
    rangeERCOTcompare_df.rename(columns={'Houston $_mwh': 'DA LMP'}, inplace=True)
    rangePJMcompare_df = PJMDApricerange[['total_lmp_da', 'Month']]
    rangePJMcompare_df['DA LMP STD'] = PJMDApricerange['stdev']
    rangePJMcompare_df['Case'] = 'PJM'
    rangePJMcompare_df.rename(columns={'total_lmp_da': 'DA LMP'}, inplace=True)
    rangeCALISOcompare_df = CAISODApricerange[['LMP_PRC', 'Month']]
    rangeCALISOcompare_df['DA LMP STD'] = CAISODApricerange['stdev']
    rangeCALISOcompare_df['Case'] = 'CAISO'
    rangeCALISOcompare_df.rename(columns={'LMP_PRC': 'DA LMP'}, inplace=True)
    rangelmp_comparison_df = pd.concat([rangeCALISOcompare_df, rangePJMcompare_df, rangeERCOTcompare_df, rangelmp_comparison_df])

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    pal = ['violet'] + ['lightgreen'] + ["gold"] + ['skyblue']

    upper_limit = 100
    lower_limit = 0
    name = 'DA LMP'
    sns.boxplot(data=lmp_comparison_df, x='Month', y=name, hue='Case', ax=axes[0], palette=pal)
    axes[0].set_ylabel('$/MW-hr')
    axes[0].set_title('Variation in Day-Ahead LMP over the Year')
    axes[0].set_xlabel('')
    axes[0].set_ylim(top=100, bottom=lower_limit)
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles=handles, labels=labels, framealpha=1)

    sns.boxplot(data=rangelmp_comparison_df, x='Month', y=name, hue='Case', ax=axes[1], palette=pal)
    axes[1].set_ylabel('$/MW-hr')
    axes[1].set_title('Variation in Daily Change in Day-Ahead LMP over the Year')
    axes[1].set_xlabel('Month')
    axes[1].set_ylim(top=upper_limit, bottom=lower_limit)
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles=handles, labels=labels, framealpha=1)

    sns.boxplot(data=rangelmp_comparison_df, x='Month', y='DA LMP STD', hue='Case', ax=axes[2], palette=pal)
    axes[2].set_ylabel('$/MW-hr')
    axes[2].set_title('Standard Deviation of Daily Day-Ahead LMP over the Year')
    axes[2].set_xlabel('Month')
    axes[2].set_ylim(top=30, bottom=lower_limit)
    handles, labels = axes[2].get_legend_handles_labels()
    axes[2].legend(handles=handles, labels=labels, framealpha=1)

    plot_filename = datetime.now().strftime(
        '%Y%m%d') + 'ISO_DA_LMP_Annual_Box_Plots-focused-SBS.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


    # =========== Create RT LMP value and range plot - all cases side by side ===========================

    lmp_rt_comparison_df = rt_lmps_df[[' LMP' + dso_num, 'Month']]
    lmp_rt_comparison_df.rename(columns={' LMP' + dso_num: 'RT LMP'}, inplace=True)
    lmp_rt_comparison_df['Case'] = 'DSO+T'
    ERCOTRTcompare_df = ERCOTRTPrices[['Houston $_mwh', 'Month']]
    ERCOTRTcompare_df['Case'] = 'ERCOT'
    ERCOTRTcompare_df.rename(columns={'Houston $_mwh': 'RT LMP'}, inplace=True)
    PJMRTcompare_df = PJMRTPrices[['total_lmp_rt', 'Month']]
    PJMRTcompare_df['Case'] = 'PJM'
    PJMRTcompare_df.rename(columns={'total_lmp_rt': 'RT LMP'}, inplace=True)
    # NOTE CALISO RT LMP data not available for 2016 or 2017.
    lmp_rt_comparison_df = pd.concat([PJMRTcompare_df, ERCOTRTcompare_df, lmp_rt_comparison_df])

    range_rt_lmp_comparison_df = rt_lmps_daily_df[[' LMP' + dso_num, 'Month']]
    range_rt_lmp_comparison_df.rename(columns={' LMP' + dso_num: 'RT LMP'}, inplace=True)
    range_rt_lmp_comparison_df['RT LMP STD'] = rt_lmps_daily_df['stdev']
    range_rt_lmp_comparison_df['Case'] = 'DSO+T'
    range_rt_ERCOTcompare_df = ERCOTRTpricerange[['Houston $_mwh', 'Month']]
    range_rt_ERCOTcompare_df['Case'] = 'ERCOT'
    range_rt_ERCOTcompare_df['RT LMP STD'] = ERCOTRTpricerange['stdev']
    range_rt_ERCOTcompare_df.rename(columns={'Houston $_mwh': 'RT LMP'}, inplace=True)
    range_rt_PJMcompare_df = PJMRTpricerange[['total_lmp_rt', 'Month']]
    range_rt_PJMcompare_df['Case'] = 'PJM'
    range_rt_PJMcompare_df.rename(columns={'total_lmp_rt': 'RT LMP'}, inplace=True)
    range_rt_PJMcompare_df['RT LMP STD'] = PJMRTpricerange['stdev']
    range_rt_lmp_comparison_df = pd.concat([range_rt_PJMcompare_df, range_rt_ERCOTcompare_df, range_rt_lmp_comparison_df])

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    pal = ['lightgreen'] + ["gold"] + ['skyblue']

    upper_limit = 100
    lower_limit = 0
    name = 'RT LMP'
    sns.boxplot(data=lmp_rt_comparison_df, x='Month', y=name, hue='Case', ax=axes[0], palette=pal)
    axes[0].set_ylabel('$/MW-hr')
    axes[0].set_title('Variation in Real-Time LMP over the Year')
    axes[0].set_xlabel('')
    axes[0].set_ylim(top=100, bottom=lower_limit)
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles=handles, labels=labels)

    sns.boxplot(data=range_rt_lmp_comparison_df, x='Month', y=name, hue='Case', ax=axes[1], palette=pal)
    axes[1].set_ylabel('$/MW-hr')
    axes[1].set_title('Variation in Daily Change in Real-Time LMP over the Year')
    axes[1].set_xlabel('Month')
    axes[1].set_ylim(top=upper_limit, bottom=lower_limit)
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles=handles, labels=labels)

    sns.boxplot(data=range_rt_lmp_comparison_df, x='Month', y='RT LMP STD', hue='Case', ax=axes[2], palette=pal)
    axes[2].set_ylabel('$/MW-hr')
    axes[2].set_title('Standard Deviation in Daily Real-Time LMP over the Year')
    axes[2].set_xlabel('Month')
    axes[2].set_ylim(top=30, bottom=lower_limit)
    handles, labels = axes[2].get_legend_handles_labels()
    axes[2].legend(handles=handles, labels=labels)

    plot_filename = datetime.now().strftime(
        '%Y%m%d') + 'ISO_RT_LMP_Annual_Box_Plots-focused-SBS.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


    # =========== Create load duration plot 1 - DA spread ===========================

    #  Power generation load duration curve
    ERCOTLDC_data = ERCOTDApricerange['Houston $_mwh'].values.tolist()
    ERCOTLDC_data.sort(reverse=False)
    ERCOTLDC_data = np.array(ERCOTLDC_data)

    CAISOLDC_data = CAISODApricerange['LMP_PRC'].values.tolist()
    CAISOLDC_data.sort(reverse=False)
    CAISOLDC_data = np.array(CAISOLDC_data)

    PJMLDC_data = PJMDApricerange['total_lmp_da'].values.tolist()
    PJMLDC_data.sort(reverse=False)
    PJMLDC_data = np.array(PJMLDC_data)

    DSOT_data = da_lmps_daily_df['da_lmp' + dso_num].values.tolist()
    DSOT_data.sort(reverse=False)
    DSOT_data = np.array(DSOT_data)

    if stats:
        ERCOTmean = np.mean(ERCOTLDC_data)
        ERCOTmedian = np.median(ERCOTLDC_data)
        CAISOmean = np.mean(CAISOLDC_data)
        CAISOmedian = np.median(CAISOLDC_data)
        PJMmean = np.mean(PJMLDC_data)
        PJMmedian = np.median(PJMLDC_data)
        DSOTmean = np.mean(DSOT_data)
        DSOTmedian = np.median(DSOT_data)

    l = len(ERCOTLDC_data)
    index = np.array(range(0, l)) * 100 / l

    l = len(DSOT_data)
    dsot_index = np.array(range(0, l)) * 100 / l

    plt.clf()
    plt.plot(index, ERCOTLDC_data, label='ERCOT Delta DA LMP')
    plt.plot(dsot_index, DSOT_data, label='DSO+T Delta DA LMP')
    plt.plot(index, PJMLDC_data, label='PJM Delta DA LMP')
    plt.plot(index, CAISOLDC_data, label='CAISO Delta DA LMP')
    plt.legend()

    plt.title('Duration vs. Daily Variation in DA LMP', size=label_size)
    plt.xlabel('Duration (%)', size=label_size)
    plt.xlim(0, 100)
    plt.ylabel('$/Mw-hr', size=label_size)
    plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    plt.legend(loc='upper left', prop={'size': 17})

    if stats:
        text = "               Mean    Median \n" + \
               "ERCOT = " + str(round(ERCOTmean)) + "     " + str(round(ERCOTmedian)) + "\n" + \
               "DSO+T     = " + str(round(DSOTmean)) + "     " + str(round(DSOTmedian))+ "\n" + \
               "PJM      = " + str(round(PJMmean)) + "     " + str(round(PJMmedian)) + "\n" + \
               "CAISO  = " + str(round(CAISOmean)) + "     " + str(round(CAISOmedian))
        plt.text(0.3, 0.7, text, size=15, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_filename = datetime.now().strftime('%Y%m%d') + 'ISO_Daily_variation_DA_LMP_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # =========== Create load duration plot 1B - DA STDEV ===========================

    #  Power generation load duration curve
    ERCOTLDC_data = ERCOTDApricerange['stdev'].values.tolist()
    ERCOTLDC_data.sort(reverse=False)
    ERCOTLDC_data = np.array(ERCOTLDC_data)

    CAISOLDC_data = CAISODApricerange['stdev'].values.tolist()
    CAISOLDC_data.sort(reverse=False)
    CAISOLDC_data = np.array(CAISOLDC_data)

    PJMLDC_data = PJMDApricerange['stdev'].values.tolist()
    PJMLDC_data.sort(reverse=False)
    PJMLDC_data = np.array(PJMLDC_data)

    DSOT_data = da_lmps_daily_df['stdev'].values.tolist()
    DSOT_data.sort(reverse=False)
    DSOT_data = np.array(DSOT_data)

    if stats:
        ERCOTmean = np.mean(ERCOTLDC_data)
        ERCOTmedian = np.median(ERCOTLDC_data)
        CAISOmean = np.mean(CAISOLDC_data[~np.isnan(CAISOLDC_data)])
        CAISOmedian = np.median(CAISOLDC_data[~np.isnan(CAISOLDC_data)])
        PJMmean = np.mean(PJMLDC_data[~np.isnan(PJMLDC_data)])
        PJMmedian = np.median(PJMLDC_data[~np.isnan(PJMLDC_data)])
        DSOTmean = np.mean(DSOT_data)
        DSOTmedian = np.median(DSOT_data)

    l = len(ERCOTLDC_data)
    index = np.array(range(0, l)) * 100 / l

    l = len(DSOT_data)
    dsot_index = np.array(range(0, l)) * 100 / l

    plt.clf()
    plt.plot(index, ERCOTLDC_data, label='ERCOT STDEV DA LMP')
    plt.plot(dsot_index, DSOT_data, label='DSO+T STDEV DA LMP')
    plt.plot(index, PJMLDC_data, label='PJM Delta STDEV LMP')
    plt.plot(index, CAISOLDC_data, label='CAISO STDEV DA LMP')
    plt.legend()

    plt.title('Duration vs. Daily Standard Deviation in DA LMP', size=label_size)
    plt.xlabel('Duration (%)', size=label_size)
    plt.xlim(0, 100)
    plt.ylabel('$/Mw-hr', size=label_size)
    plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    plt.legend(loc='upper left', prop={'size': 17})

    if stats:
        text = "               Mean    Median \n" + \
               "ERCOT = " + str(round(ERCOTmean)) + "     " + str(round(ERCOTmedian)) + "\n" + \
               "DSO+T     = " + str(round(DSOTmean)) + "     " + str(round(DSOTmedian)) + "\n" + \
               "PJM      = " + str(round(PJMmean)) + "     " + str(round(PJMmedian)) + "\n" + \
               "CAISO  = " + str(round(CAISOmean)) + "     " + str(round(CAISOmedian))
        plt.text(0.3, 0.7, text, size=15, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_filename = datetime.now().strftime('%Y%m%d') + 'ISO_Daily_STDEV_DA_LMP_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


    # =========== Create load duration plot 2 - DA LMP ===========================

    #  Power generation load duration curve
    ERCOTLDC_data = ERCOTDAPrices['Houston $_mwh'].values.tolist()
    ERCOTLDC_data.sort(reverse=False)
    ERCOTLDC_data = np.array(ERCOTLDC_data)

    CAISOLDC_data = CAISODAPrices['LMP_PRC'].values.tolist()
    CAISOLDC_data.sort(reverse=False)
    CAISOLDC_data = np.array(CAISOLDC_data)

    PJMLDC_data = PJMDAPrices['total_lmp_da'].values.tolist()
    PJMLDC_data.sort(reverse=False)
    PJMLDC_data = np.array(PJMLDC_data)

    DSOT_data = da_lmps_df['da_lmp' + dso_num].values.tolist()
    DSOT_data.sort(reverse=False)
    DSOT_data = np.array(DSOT_data)

    if stats:
        ERCOTmean = np.mean(ERCOTLDC_data)
        ERCOTmedian = np.median(ERCOTLDC_data)
        CAISOmean = np.mean(CAISOLDC_data)
        CAISOmedian = np.median(CAISOLDC_data)
        PJMmean = np.mean(PJMLDC_data)
        PJMmedian = np.median(PJMLDC_data)
        DSOTmean = np.mean(DSOT_data)
        DSOTmedian = np.median(DSOT_data)

    Eindex = np.array(range(0, len(ERCOTLDC_data))) * 100 / len(ERCOTLDC_data)
    Cindex = np.array(range(0, len(CAISOLDC_data))) * 100 / len(CAISOLDC_data)
    Pindex = np.array(range(0, len(PJMLDC_data))) * 100 / len(PJMLDC_data)
    Dindex = np.array(range(0, len(DSOT_data))) * 100 / len(DSOT_data)

    plt.clf()
    plt.plot(Eindex, ERCOTLDC_data, label='ERCOT DA LMP')
    plt.plot(Dindex, DSOT_data, label='DSO+T DA LMP')
    plt.plot(Pindex, PJMLDC_data, label='PJM DA LMP')
    plt.plot(Cindex, CAISOLDC_data, label='CAISO DA LMP')
    plt.legend()

    plt.title('Duration vs. DA LMP', size=label_size)
    plt.xlabel('Duration (%)', size=label_size)
    plt.xlim(0, 100)
    plt.ylabel('$/Mw-hr', size=label_size)
    plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    plt.legend(loc='upper left', prop={'size': 17})
    if stats:
        text = "               Mean    Median \n" + \
               "ERCOT = " + str(round(ERCOTmean)) + "     " + str(round(ERCOTmedian)) + "\n" + \
               "DSO+T  = " + str(round(DSOTmean)) + "     " + str(round(DSOTmedian)) + "\n" + \
               "PJM      = " + str(round(PJMmean)) + "     " + str(round(PJMmedian)) + "\n" + \
               "CAISO  = " + str(round(CAISOmean)) + "     " + str(round(CAISOmedian))
        plt.text(0.3, 0.7, text, size=15, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_limit = 1
    ax.set_ylim(bottom=plot_limit)

    plot_filename = datetime.now().strftime('%Y%m%d') + 'ISO_DA_LMP_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


    # =========== Create load duration plot 3 - RT spread ===========================

    #  Power generation load duration curve
    ERCOTRTLDC_data = ERCOTRTpricerange['Houston $_mwh'].values.tolist()
    ERCOTRTLDC_data.sort(reverse=False)
    ERCOTRTLDC_data = np.array(ERCOTRTLDC_data)

    PJMRTLDC_data = PJMRTpricerange['total_lmp_rt'].values.tolist()
    PJMRTLDC_data.sort(reverse=False)
    PJMRTLDC_data = np.array(PJMRTLDC_data)

    DSOT_RT_data = da_lmps_daily_df['da_lmp' + dso_num].values.tolist()
    DSOT_RT_data.sort(reverse=False)
    DSOT_RT_data = np.array(DSOT_RT_data)

    if stats:
        ERCOTmean = np.mean(ERCOTRTLDC_data)
        ERCOTmedian = np.median(ERCOTRTLDC_data)
        PJMmean = np.mean(PJMRTLDC_data[~np.isnan(PJMRTLDC_data)])
        PJMmedian = np.median(PJMRTLDC_data[~np.isnan(PJMRTLDC_data)])
        DSOTmean = np.mean(DSOT_RT_data)
        DSOTmedian = np.median(DSOT_RT_data)

    l = len(ERCOTRTLDC_data)
    index = np.array(range(0, l)) * 100 / l

    l = len(DSOT_RT_data)
    dsot_index = np.array(range(0, l)) * 100 / l

    plt.clf()
    plt.plot(index, ERCOTRTLDC_data, label='ERCOT Delta RT LMP')
    plt.plot(dsot_index, DSOT_RT_data, label='DSO+T Delta RT LMP')
    plt.plot(index, PJMRTLDC_data, label='PJM Delta RT LMP')
    plt.legend()

    plt.title('Duration vs. Daily Variation in RT LMP', size=label_size)
    plt.xlabel('Duration (%)', size=label_size)
    plt.xlim(0, 100)
    plt.ylabel('$/Mw-hr', size=label_size)
    plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    plt.legend(loc='upper left', prop={'size': 17})

    if stats:
        text = "               Mean    Median \n" + \
               "ERCOT = " + str(round(ERCOTmean)) + "     " + str(round(ERCOTmedian)) + "\n" + \
               "DSO+T     = " + str(round(DSOTmean)) + "     " + str(round(DSOTmedian)) + "\n" + \
               "PJM      = " + str(round(PJMmean)) + "     " + str(round(PJMmedian))
        plt.text(0.3, 0.7, text, size=15, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_filename = datetime.now().strftime('%Y%m%d') + 'ISO_Daily_variation_RT_LMP_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # =========== Create load duration plot 2 - DA LMP ===========================

    #  Power generation load duration curve
    ERCOT_RTLMP_LDC_data = ERCOTRTPrices['Houston $_mwh'].values.tolist()
    ERCOT_RTLMP_LDC_data.sort(reverse=False)
    ERCOT_RTLMP_LDC_data = np.array(ERCOT_RTLMP_LDC_data)

    PJM_RTLMP_LDC_data = PJMRTPrices['total_lmp_rt'].values.tolist()
    PJM_RTLMP_LDC_data.sort(reverse=False)
    PJM_RTLMP_LDC_data = np.array(PJM_RTLMP_LDC_data)

    DSOT_RTLMP_data = rt_lmps_df[' LMP' + dso_num].values.tolist()
    DSOT_RTLMP_data.sort(reverse=False)
    DSOT_RTLMP_data = np.array(DSOT_RTLMP_data)

    if stats:
        ERCOTmean = np.mean(ERCOT_RTLMP_LDC_data)
        ERCOTmedian = np.median(ERCOT_RTLMP_LDC_data)
        PJMmean = np.mean(PJM_RTLMP_LDC_data[~np.isnan(PJM_RTLMP_LDC_data)])
        PJMmedian = np.median(PJM_RTLMP_LDC_data[~np.isnan(PJM_RTLMP_LDC_data)])
        DSOTmean = np.mean(DSOT_RTLMP_data)
        DSOTmedian = np.median(DSOT_RTLMP_data)

    Eindex = np.array(range(0, len(ERCOT_RTLMP_LDC_data))) * 100 / len(ERCOT_RTLMP_LDC_data)
    Dindex = np.array(range(0, len(DSOT_RTLMP_data))) * 100 / len(DSOT_RTLMP_data)
    Pindex = np.array(range(0, len(PJM_RTLMP_LDC_data))) * 100 / len(PJM_RTLMP_LDC_data)

    plt.clf()
    plt.plot(Eindex, ERCOT_RTLMP_LDC_data, label='ERCOT RT LMP')
    plt.plot(Dindex, DSOT_RTLMP_data, label='DSO+T RT LMP')
    plt.plot(Pindex, PJM_RTLMP_LDC_data, label='PJM RT LMP')
    plt.legend()

    plt.title('Duration vs. RT LMP', size=label_size)
    plt.xlabel('Duration (%)', size=label_size)
    plt.xlim(0, 100)
    plt.ylabel('$/Mw-hr', size=label_size)
    plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    plt.legend(loc='upper left', prop={'size': 17})
    if stats:
        text = "               Mean    Median \n" + \
               "ERCOT = " + str(round(ERCOTmean)) + "     " + str(round(ERCOTmedian)) + "\n" + \
               "DSO+T  = " + str(round(DSOTmean)) + "     " + str(round(DSOTmedian))  + "\n" + \
               "PJM      = " + str(round(PJMmean)) + "     " + str(round(PJMmedian))
        plt.text(0.3, 0.7, text, size=15, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_limit = 1
    ax.set_ylim(bottom=plot_limit)

    plot_filename = datetime.now().strftime('%Y%m%d') + 'ISO_RT_LMP_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


    # =========== Create load duration plot 1 - DA geographic spread ===========================

    #  LMP Geographic variation vs duration curve
    ERCOTGDC_data = ERCOT_LMP_DELTA['DeltaPer'].values.tolist()
    ERCOTGDC_data.sort(reverse=False)
    ERCOTGDC_data = np.array(ERCOTGDC_data)

    DSOT_data = da_lmps_df['LMP Delta'].values.tolist()
    DSOT_data.sort(reverse=False)
    DSOT_data = np.array(DSOT_data)

    if stats:
        ERCOTmax = np.max(ERCOTGDC_data)
        ERCOTmean = np.mean(ERCOTGDC_data)
        ERCOTmedian = np.median(ERCOTGDC_data)
        DSOTmax = np.max(DSOT_data)
        DSOTmean = np.mean(DSOT_data)
        DSOTmedian = np.median(DSOT_data)

    l = len(ERCOTGDC_data)
    index = np.array(range(0, l)) * 100 / l

    l = len(DSOT_data)
    dsot_index = np.array(range(0, l)) * 100 / l

    plt.clf()
    plt.plot(index, ERCOTGDC_data, label='ERCOT Delta DA LMP')
    plt.plot(dsot_index, DSOT_data, label='DSO+T Delta DA LMP')
    plt.legend()

    plt.title('Duration vs. Geographic Variation in LMP', size=label_size)
    plt.xlabel('Duration (%)', size=label_size)
    plt.xlim(0, 100)
    plt.ylabel('$/Mw-hr', size=label_size)
    plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    plt.legend(loc='upper left', prop={'size': 17})

    if stats:
        text = "               Max       Mean    Median \n" + \
               "ERCOT = " + str(round(ERCOTmax, 1)) + "     " + str(round(ERCOTmean, 1)) + "     " + str(round(ERCOTmedian, 1)) + "\n" + \
               "DSO+T     = " + str(round(DSOTmax, 1)) + "     " + str(round(DSOTmean, 1)) + "     " + str(round(DSOTmedian, 1))
        plt.text(0.3, 0.7, text, size=15, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_filename = datetime.now().strftime('%Y%m%d') + 'ISO_Geographic_variation_DA_LMP_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


    # ------ Plot of just LMPs versus net load  -------------

    month_list = ['2016-01', '2016-02', '2016-03', '2016-04', '2016-05', '2016-06', '2016-07', '2016-08', '2016-09',
                  '2016-10', '2016-11', '2016-12']

    place = 'Houston'
    month_to_plot = month_list[month_index]
    date = datetime.strptime(month_to_plot, "%Y-%m")
    month = datetime.date(date).strftime('%B')

    plt.figure(figsize=(11, 10))
    plt.scatter(ERCOTDAPrices.loc[month_to_plot, 'ERCOT Net Load'],
                ERCOTDAPrices.loc[month_to_plot, place + ' $_mwh'], label='ERCOT DA LMP', marker='o',
                linestyle='-', alpha=0.8)
    plt.scatter(ERCOTRTPrices.loc[month_to_plot, 'ERCOT Net Load'],
                ERCOTRTPrices.loc[month_to_plot, place + ' $_mwh'], label='ERCOT RT LMP', marker='o',
                linestyle='-', alpha=0.5)
    plt.scatter(rt_lmps_df.loc[month_to_plot, 'NetLoad'],
                rt_lmps_df.loc[month_to_plot, ' LMP'+dso_num], label='DSO+T RT LMP', marker='o',
                linestyle='-', alpha=0.5)
    plt.scatter(da_lmps_df.loc[month_to_plot, 'NetLoad'],
                da_lmps_df.loc[month_to_plot, 'da_lmp'+dso_num], label='DSO+T DA LMP', marker='o',
                linestyle='-', alpha=0.5)
    # axes[1].set_title(month + ' - Daily Delta Load')
    plt.legend(loc='upper left', fontsize=17)
    plt.ylabel('$/MW-hr', size=17)
    plt.xlabel('Net Load (MW)', size=17)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)

    plot_filename = datetime.now().strftime(
        '%Y%m%d') + ' ' + place + '_ERCOT_LMP_vs_netload' + month + '.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.ylim(top=80, bottom=0)
    plot_filename = datetime.now().strftime(
        '%Y%m%d') + ' ' + place + '_ERCOT_LMP_vs_netload' + month + '_focused.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    #  Plot comparison time series
    start_time = datetime.strptime("2016-08-03 00:00:00", '%Y-%m-%d %H:%M:%S')
    end_time = datetime.strptime("2016-08-17 00:00:00", '%Y-%m-%d %H:%M:%S')

    place = 'Houston'
    month_to_plot = month_list[month_index]
    date = datetime.strptime(month_to_plot, "%Y-%m")
    month = datetime.date(date).strftime('%B')

    plt.figure(figsize=(11, 8))
    # name = 'RT LMP'
    # sns.lineplot(data=lmp_rt_comparison_df, x='Month', y=name, hue='Case', palette=pal)
    plt.plot( ERCOTRTPrices.loc[start_time:end_time, place + ' $_mwh'], label='ERCOT RT LMP', marker='o',
                linestyle='-', alpha=0.5)
    plt.plot(rt_lmps_df.loc[start_time:end_time, ' LMP'+dso_num], label='DSO+T RT LMP', marker='o',
                linestyle='-', alpha=0.5)
    # axes[1].set_title(month + ' - Daily Delta Load')
    plt.legend(loc='upper left', fontsize=20)
    plt.ylabel('$/MW-hr', size=20)
    plt.xlabel('Time', size=20)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=13)

    plot_filename = datetime.now().strftime(
        '%Y%m%d') + ' ' + place + '_ERCOT_RT_LMP_vs_time' + month + '.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.ylim(top=80, bottom=0)
    plot_filename = datetime.now().strftime(
        '%Y%m%d') + ' ' + place + '_ERCOT_RT_LMP_vs_time' + month + '_focused.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.figure(figsize=(11, 8))
    # name = 'RT LMP'
    # sns.lineplot(data=lmp_rt_comparison_df, x='Month', y=name, hue='Case', palette=pal)
    plt.plot(ERCOTDAPrices.loc[start_time:end_time, place + ' $_mwh'], label='ERCOT DA LMP', marker='o',
                linestyle='-', alpha=0.5)
    plt.plot(da_lmps_df.loc[start_time:end_time, 'da_lmp'+dso_num], label='DSO+T DA LMP', marker='o',
                linestyle='-', alpha=0.5)
    # axes[1].set_title(month + ' - Daily Delta Load')
    plt.legend(loc='upper left', fontsize=20)
    plt.ylabel('$/MW-hr', size=20)
    plt.xlabel('Time', size=20)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=13)

    plot_filename = datetime.now().strftime(
        '%Y%m%d') + ' ' + place + '_ERCOT_DA_LMP_vs_time' + month + '.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.ylim(top=80, bottom=0)
    plot_filename = datetime.now().strftime(
        '%Y%m%d') + ' ' + place + '_ERCOT_DA_LMP_vs_time' + month + '_focused.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')



def heatmap_plots(dso, system, subsystem, variable, day_range, case, agent_prefix, gld_prefix):
    """  For a specified day, system, variable, and day_range this function will load in the required data, manipulate
    the dataframe into the required shape, plot the heatmap and save the heatmap to file.
    Arguments:
        dso (str): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum, 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day_range (range): range of the day indexes to be plotted.  Day 1 has an index of 0
        case (str): folder extension of case of interest
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        saves heatmap to file
        """

    # Since weather and generation files have all days in one file use different construction method
    if 'gen' in system:
        #TODO: Need to fix give that load_gen now uses day_range as input.
        data = load_gen_data(case, system)

        for day in day_range:
            start = (day-1)*288
            temp = data.loc[:, variable]
            temp_df = temp.to_frame()
            temp_df = temp_df.iloc[start:(start+287), :]
            temp_df = temp_df.set_index(pd.Index(np.arange(0, 24-1.1*(24/288), 24/288)))
            temp_df = temp_df.rename(columns={variable: str(day)})
            if i is 0:
                heat_map_df = temp_df
            else:
                heat_map_df = heat_map_df.join(temp_df)
    else:
        # =================   core code for agent and gld data  ================

        for day in day_range:
            temp_df = get_day_df(dso, system, subsystem, variable, str(day), case, agent_prefix, gld_prefix)
            temp_df = temp_df.set_index(pd.Index(np.arange(0, 24, 24/len(temp_df))))
            temp_df = temp_df.rename(columns={variable: str(day)})
            if day == day_range[0]:
                heat_map_df = temp_df
            else:
                heat_map_df = heat_map_df.join(temp_df)

    # -------- Plot heatmap of variable for system for day range and DSO
    fig, ax = plt.subplots(figsize=(16,6))
    cmap_obj = plt.cm.get_cmap('coolwarm', 20)
    heatmap = ax.pcolor(heat_map_df, cmap=cmap_obj, edgecolors='none')
    fig.colorbar(heatmap)
    ax.set_xlim(right=len(heat_map_df.columns))
    ax.set_ylim(len(heat_map_df.index), 0)
    # ax.set_ylim(top=len(heat_map_df.index))
    #ticks_to_use = dsoload_df.index[::24]
    ax.set_xlabel('day')
    ax.set_ylabel('time of day (hour)')
    ylabels_to_use = heat_map_df.index[::48]
    # Set format of labels (note year not excluded as requested)
    #labels = [i.strftime("%H") for i in ticks_to_use]
    # Now set the ticks and labels
    #ax.set_yticks(ticks_to_use)
    ax.set_yticklabels(ylabels_to_use)
    xlabels_to_use = []
    ax.set_xticks(np.arange(heat_map_df.shape[1]))
    for col in heat_map_df.columns.values:
        date = get_date(case,dso_num,col)
        xlabels_to_use.append(date.strftime("%m-%d"))
    ax.set_xticklabels(xlabels_to_use)
    if subsystem is None:
        fig.suptitle('DSO' + dso_num + ' ' + system + " " + ": " + variable)
        plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_HeatMap_DSO' + dso_num + system + variable + '.png'
    else:
        fig.suptitle('DSO' + dso_num + ' ' + system + " " + subsystem + ": " + variable)
        plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_HeatMap_DSO' + dso_num + system + subsystem + variable + '.png'

    # ------------Save figure to file  --------------------
    file_path_fig = os.path.join(data_path, 'plots',  plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')


def daily_summary_plots(dso, system, subsystem, variable, day_range, case, comp, oper, diff, denom,
                        agent_prefix, gld_prefix):
    """  For a specified day range, system, variable, and dso this function will load in the required data and
     plot the variable for each day based on the operator and compare it to another case (optional).
    Arguments:
        dso (str): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum, 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day_range (range): range of the day indexes to be plotted.  Day 1 has an index of 0
        case (str): folder extension of case of interest
        comp (str): folder extension of comparison case of interest
        oper (str): operator for selecting a scalar value to represent the daily range (e.g. 'min, 'max', 'mean')
        diff (bool): If True will plot the difference between the baseline (case) and comparison (comp)
        denom (value): denominator that values should be divided by before plotting
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        saves plots to file
        """
    var_case = []
    var_comp = []
    var_diff = []
    if denom is None:
        denom = 1

    xlabels_to_use = []
    for day in day_range:
        date = get_date(case, dso, str(day))
        xlabels_to_use.append(date.strftime("%m-%d"))
        #day[i] = (str(day_range[i]+1))
        temp_df = get_day_df(dso, system, subsystem, variable, str(day), case, agent_prefix, gld_prefix)
        if oper == 'max':
            var_case.append(temp_df[variable].max() / denom)
        elif oper == 'min':
            var_case.append(temp_df[variable].min() / denom)
        elif oper == 'mean':
            var_case.append(temp_df[variable].mean() / denom)
        if comp is not None:
            comp_df = get_day_df(dso, system, subsystem, variable, str(day), comp, agent_prefix, gld_prefix)
            if oper == 'max':
                var_comp.append(comp_df[variable].max() / denom)
            elif oper == 'min':
                var_comp.append(comp_df[variable].min() / denom)
            elif oper == 'mean':
                var_comp.append(comp_df[variable].mean() / denom)
        if diff:
            var_diff.append(var_case[-1] - var_comp[-1])

    if subsystem is None:
        subsystem = ''
    plt.figure()
    plt.plot(xlabels_to_use, var_case, label=case.split('\\')[-1])
    if comp is not None:
        plt.plot(xlabels_to_use, var_comp, label=comp.split('\\')[-1])
    plt.legend()
    plt.title(system + ' ' + subsystem + ' ' + oper + ' ' + variable + ' vs. Day (DSO' + dso +')')
    plt.xlabel('Day')
    plt.ylabel(variable)

    plot_filename = datetime.now().strftime('%Y%m%d') + 'Daily_Summary_' + system + subsystem + '_' + oper + '_' \
                    + variable + 'DSO_' + dso + '.png'
    file_path_fig = os.path.join(data_path, 'plots',  plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    if diff:
        plt.figure()
        plt.plot(xlabels_to_use, var_diff, label='Difference')
        plt.title(system + ' ' + subsystem + ' ' + oper + ' ' + variable + ' vs. Day (DSO' + dso +')')
        plt.xlabel('Day')
        plt.ylabel(variable)

        plot_filename = datetime.now().strftime('%Y%m%d') + 'Daily_Summary_Diff' + system + subsystem + '_' + oper +\
                        '_' + variable + 'DSO_' + dso + '.png'
        file_path_fig = os.path.join(data_path, 'plots',  plot_filename)

        plt.savefig(file_path_fig, bbox_inches='tight')


def generation_load_profiles(dir_path, metadata_path, data_path, day_range, use_ercot_fuel_mix_data = False, comp=None):
    """  For a specified day range this function plots the stacked profiles of all generators (by fuel type) along with
    load plots.
    Arguments:
        dir_path (str): path locating the AMES data file
        metadata_path (str): path locating the ERCOT load profile 5 minute data
        data_path (str): path to the folder containing the plots sub folder
        day_range (range): range of starting day and ending day of plot
        use_ercot_fuel_mix_data (bool): If True plots 2016 actual ERCOT data, if False plots AMES RT data.
        comp (str): folder path containing the generation data for the comparison case.  Set to None for no comparison
    Returns:
        saves plots to file
        """
    # Load generate_case_config
    case_config = load_json(dir_path, 'generate_case_config.json')
    # Load ERCOT load profile data
    metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
    sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
    ercot_df = load_ercot_data(metadata_file, sim_start, day_range)

    ercot_sum = ercot_df.loc[:, ercot_df.columns[ercot_df.columns.str.contains('Bus')]].sum(axis=1)
    ercot_sum_df = pd.DataFrame(ercot_sum)
    ercot_sum_df = ercot_sum_df.rename(columns={0:'Net Load'})
    # ames_df = ames_df.set_index(ercot_sum_df.index)

    fuel_list = ['nuc', 'coal', 'gas_CC', 'gas_CT', 'wind', 'solar']
    fuel_labels = ['Nuclear', 'Coal', 'Gas (CC)', 'Gas (CT)', 'Wind', 'Solar']
    colors = ['silver', 'black', 'darkorange', 'orange', 'blue', 'yellow']
    y = []

    if use_ercot_fuel_mix_data:
        fuel_df = load_ercot_fuel_mix(metadata_path, dir_path, day_range)
        ercot_sum_df = ercot_sum_df.resample('15T').mean()  # Need to match 15 min ERCOT load mix data
    else:
        fuel_df = load_ames_data(dir_path, day_range)
        ercot_sum_df['AMES Load'] = fuel_df[' TotalLoad']

        config_data = case_config

        fuel_key = {'nuc': 'Nuclear',
                    'coal': 'Coal',
                    'wind': 'Wind',
                    'gas': 'Gas',
                    'solar': 'Photovoltaic'}

        name_key = {}
        i = 0
        for gen in config_data['gen']:
            gen_type = config_data['genfuel'][i][1]
            for key in fuel_key:
                if fuel_key[key] in gen_type:
                    gen_fuel = key
            gen_id = ' ' + gen_fuel + str(config_data['genfuel'][i][2])

            if config_data['genfuel'][i][1] in ['Natural Gas Combined Cycle', 'Natural Gas Steam Turbine']:
                alias = ' ' + gen_fuel + '_CC' + str(config_data['genfuel'][i][2])
                name_key.update({gen_id: alias})
            elif config_data['genfuel'][i][1] in ['Natural Gas Internal Combustion Turbine', 'Natural Gas Internal Combustion Engine']:
                alias = ' ' + gen_fuel + '_CT' + str(config_data['genfuel'][i][2])
                name_key.update({gen_id: alias})
            i += 1
        fuel_df = fuel_df.rename(columns=name_key)

    for fuel in fuel_list:
        gen_cols = [col for col in fuel_df.columns if fuel in col]
        ercot_sum_df[fuel] = fuel_df[gen_cols].sum(axis=1)
        y.append(ercot_sum_df[fuel].values.tolist())


    plt.figure(figsize=(20, 10))
    plt.stackplot(ercot_sum_df.index, y, colors=colors, labels=fuel_labels)
    if comp is not None:
        compare_df = load_ames_data(comp, day_range)
        plt.plot(ercot_sum_df.index, compare_df[' TotalLoad'], label='Reference Load', color='grey', linestyle='--', linewidth=3)
    else:
        plt.plot(ercot_sum_df.index, ercot_sum_df['Net Load'], label='ERCOT Load', color='black', linestyle='--', linewidth=3)
    if not use_ercot_fuel_mix_data:
        plt.plot(ercot_sum_df.index, ercot_sum_df['AMES Load'], label='Total Load', color='black')
    plt.legend(loc='upper left', prop={'size': 17})
    plt.xlabel('Time', size=25)
    plt.ylabel('Generation (MW)', size=25)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=17)
    if use_ercot_fuel_mix_data:
        plot_filename = datetime.now().strftime('%Y%m%d') + '_ERCOT_fuelmix_profiles.png'
    else:
        plot_filename = datetime.now().strftime('%Y%m%d') + '_AMES_2016_fuelmix_profiles.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


def generation_statistics(dir_path, config_dir, config_file, day_range, use_gen_data = True):
    """  For a specified day range this function plots the stacked profiles of all generators (by fuel type) along with
    load plots.
    Arguments:
        dir_path (str): path locating the AMES data file
        config_dir (str): path locating the case config file
        config_file (str): name of the case config file
        day_range (range): range of starting day and ending day of plot
        use_gen_data (boolean): if True uses dispatched generator performance from PyPower.  If False uses dispatched
        AMES performance
    Returns:
        saves plots to file
        """

    # Load case config metadata to get generator metadata
    config_data = load_json(config_dir, config_file)

    # Load AMES results including RT LMP data
    ames_df = load_ames_data(dir_path, day_range)
    # Set up DataFrame structure for statistics output
    fuel_list = ['coal', 'gas', 'nuc', 'solar', 'wind']
    variables = ['Fuel', 'Gen Type', 'Capacity (MW)','Min Capacity (MW)', 'Capacity Factor (-)', 'Generation (MW-hrs)', 'Online Hours',
                 'Starts', 'Online hours per start', 'Fuel cost ($k)', 'Startup costs ($k)', 'Total revenue ($k)',
                 'Total production cost ($k)', 'Effective LMP', 'Ramp Limit (MW/min)', 'Max Ramp up (MW/min)',
                 'Max Ramp up (-)', 'Max Ramp down (MW/min)', 'Max Ramp down (-)', 'Ramp/Limit (-)', 'Min Frac On (-)']
    data = np.zeros((len(variables), len(fuel_list)))
    generator_df = pd.DataFrame(data,
                            index=variables,
                            columns=fuel_list)


    fuel_key = {'nuc': 'Nuclear',
                'coal': 'Coal',
                'wind': 'Wind',
                'gas': 'Gas',
                'solar': 'Photovoltaic'}

    gen_key = {}
    name_key = {}
    i = 0
    for gen in config_data['gen']:
        gen_id = 'gen' + str(config_data['genfuel'][i][2])
        gen_bus = gen[0]
        gen_type = config_data['genfuel'][i][1]
        gen_capacity = gen[8]
        gen_min_capacity = gen[9]
        ramp_rate_limit = gen[16]
        startup_cost = config_data['gencost'][i][1]
        C0 = config_data['gencost'][i][6]
        C1 = config_data['gencost'][i][5]
        C2 = config_data['gencost'][i][4]
        for key in fuel_key:
            if fuel_key[key] in gen_type:
                gen_fuel = key
        alias = ' ' + gen_fuel + str(config_data['genfuel'][i][2])
        gen_key.update({gen_id: [gen_fuel, gen_type, gen_capacity, startup_cost, C0, C1, C2,
                                 gen_min_capacity, ramp_rate_limit, gen_bus]})
        name_key.update({alias: gen_id})
        i += 1

    if use_gen_data:
        gen_df = load_gen_data(dir_path, 'gen', day_range)

        gen_transpose_df = pd.DataFrame(columns=['gen31'])
        for key in gen_key:
            gen_transpose_df[key] = gen_df.xs(key, level=1)['Pgen']
        data_df = gen_transpose_df
    else:
        # ames_df = load_ames_data(dir_path, day_range)
        gen_cols = []
        for fuel in fuel_list:
            gen_cols = gen_cols + ([col for col in ames_df.columns if fuel in col])
        data_df = ames_df[gen_cols]
        data_df = data_df.rename(columns=name_key)


    total_hours = len(day_range) * 24
    sum_df = pd.DataFrame(columns=fuel_list)
    for fuel in fuel_list:
        gen_cols = [col for col in data_df.columns if fuel in gen_key[col][0]]

        gen_list = gen_cols
        for gen in gen_list:
            generator_df.loc['Fuel', gen] = gen_key[gen][0]
            generator_df.loc['Gen Type', gen] = gen_key[gen][1]
            generator_df.loc['Capacity (MW)', gen] = gen_key[gen][2]
            generator_df.loc['Min Capacity (MW)', gen] = gen_key[gen][7]
            generator_df.loc['Generation (MW-hrs)', gen] = data_df[gen].sum() / 12
            generator_df.loc['Ramp Limit (MW/min)', gen] = gen_key[gen][8]
            generator_df.loc['Capacity Factor (-)', gen] = generator_df.loc['Generation (MW-hrs)', gen] / \
                                                           (generator_df.loc['Capacity (MW)', gen] * total_hours)
            generator_df.loc['Online Hours', gen] = (data_df[gen] != 0).sum() / 12
            Transitions = data_df[gen].where(data_df[gen] == 0, 1).diff()
            generator_df.loc['Starts', gen] = Transitions[Transitions>0].sum()
            if generator_df.loc['Starts', gen] != 0:
                generator_df.loc['Online hours per start', gen] = generator_df.loc['Online Hours', gen] \
                                                                  / generator_df.loc['Starts', gen]
            else:
                generator_df.loc['Online hours per start', gen] = generator_df.loc['Online Hours', gen]
            generator_df.loc['Fuel cost ($k)', gen] = (len(data_df[gen]) * gen_key[gen][4] + data_df[gen] * gen_key[gen][5]
                                                  + data_df[gen] * data_df[gen] * gen_key[gen][6]).sum()/12 / 1000
            generator_df.loc['Startup costs ($k)', gen] = generator_df.loc['Starts', gen] * gen_key[gen][3] / 1000
            #  TODO: Revise revenue once fully defined.
            generator_df.loc['Total revenue ($k)', gen] = (data_df[gen] * ames_df[' LMP'+str(gen_key[gen][9])]).sum() / 12 / 1000
            generator_df.loc['Total production cost ($k)', gen] = generator_df.loc['Fuel cost ($k)', gen] + generator_df.loc['Startup costs ($k)', gen]
            if generator_df.loc['Generation (MW-hrs)', gen] != 0:
                generator_df.loc['Effective LMP', gen] = 1000*generator_df.loc['Total production cost ($k)', gen] /generator_df.loc['Generation (MW-hrs)', gen]
            else:
                generator_df.loc['Effective LMP', gen] = 0
            # Need to fill in generator off time with min capacity to ensure ramp rate statistics do not count start up
            # and shut down discontinuties as max ramp rates
            generator_df.loc['Max Ramp up (MW/min)', gen] = data_df[gen].replace(0,generator_df.loc['Min Capacity (MW)', gen]).diff().max() / 5
            if generator_df.loc['Capacity (MW)', gen] > 0:
                generator_df.loc['Max Ramp up (-)', gen] = generator_df.loc['Max Ramp up (MW/min)', gen] / \
                                                         generator_df.loc['Capacity (MW)', gen]
                generator_df.loc['Max Ramp down (-)', gen] = generator_df.loc['Max Ramp down (MW/min)', gen] / \
                                                         generator_df.loc['Capacity (MW)', gen]
                generator_df.loc['Min Frac On (-)', gen] = data_df[data_df != 0].loc[:, gen].min() / \
                                                       generator_df.loc['Capacity (MW)', gen]
            generator_df.loc['Max Ramp down (MW/min)', gen] = data_df[gen].replace(0,generator_df.loc['Min Capacity (MW)', gen]).diff().min() / 5
            if generator_df.loc['Ramp Limit (MW/min)', gen] != 0:
                generator_df.loc['Ramp/Limit (-)', gen] = max(abs(generator_df.loc['Max Ramp down (MW/min)', gen]),
                                                              generator_df.loc['Max Ramp up (MW/min)', gen]) \
                                                          / generator_df.loc['Ramp Limit (MW/min)', gen]

        sum_df[fuel] = data_df[gen_cols].sum(axis=1)
        generator_df.loc['Fuel', fuel] = fuel
        generator_df.loc['Capacity (MW)', fuel] = generator_df.loc['Capacity (MW)', gen_cols].sum()
        generator_df.loc['Generation (MW-hrs)', fuel] = sum_df[fuel].sum() / 12
        generator_df.loc['Total revenue ($k)', fuel] = generator_df.loc['Total revenue ($k)', gen_cols].sum()
        generator_df.loc['Startup costs ($k)', fuel] = generator_df.loc['Startup costs ($k)', gen_cols].sum()
        generator_df.loc['Fuel cost ($k)', fuel] = generator_df.loc['Fuel cost ($k)', gen_cols].sum()
        generator_df.loc['Total production cost ($k)', fuel] = generator_df.loc['Total production cost ($k)', gen_cols].sum()
        generator_df.loc['Max Ramp up (MW/min)', fuel] = sum_df[fuel].diff().max() / 5
        generator_df.loc['Max Ramp down (MW/min)', fuel] = sum_df[fuel].diff().min() / 5
        if generator_df.loc['Capacity (MW)', fuel] == 0:
            generator_df.loc['Capacity Factor (-)', fuel] = '-'
            generator_df.loc['Max Ramp up (-)', fuel] = '-'
            generator_df.loc['Max Ramp down (-)', fuel] = '-'
        else:
            generator_df.loc['Capacity Factor (-)', fuel] = generator_df.loc['Generation (MW-hrs)', fuel] / \
                                                            (generator_df.loc['Capacity (MW)', fuel] * total_hours)
            generator_df.loc['Max Ramp up (-)', fuel] = generator_df.loc['Max Ramp up (MW/min)', fuel] / \
                                                        generator_df.loc['Capacity (MW)', fuel]
            generator_df.loc['Max Ramp down (-)', fuel] = generator_df.loc['Max Ramp down (MW/min)', fuel] / \
                                                       generator_df.loc['Capacity (MW)', fuel]
    if use_gen_data:
        file_name = '/generator_statistics_PYPower.csv'
    else:
        file_name = '/generator_statistics_AMES.csv'
    generator_df.to_csv(path_or_buf=dir_path + file_name)

    return generator_df


def transmission_statistics(metadata_file_path, case_config_path, data_path, day_range, sim_results = False):
    """  For a specified day range this function determines key transmission statistics (e.g. line lenght, max
    normalized line usage etc).
    Arguments:
        metadata_file_path (str): path and file name of the 8/200-bus metadata json file
        case_config_path (str): path and file name locating the system case config json file
        data_path (str): path to the folder containing the simulation results
        day_range (range): range of starting day and ending day of data to include
        sim_results (boolean): if True loads in simuation results.  If false skips simulation results.
    Returns:
        saves csv statistics to files
        """

    # Load case config metadata to get generator metadata
    with open(case_config_path) as json_file:
        config_data = json.load(json_file)

    with open(metadata_file_path) as json_file:
        dso_metadata = json.load(json_file)

    # Only open results file if true.
    if sim_results:
        rt_line_data_df = load_gen_data(data_path, 'rt_line', day_range)
        test_data_df = rt_line_data_df.unstack(level=1)
        test_data_df.columns = test_data_df.columns.droplevel()

    # Set up DataFrame structure for line statistics output
    line_list = [str(n+1) for n in range(len(config_data['branch']))]
    line_variables = ['Line ID', 'Length (miles)', 'Capacity (MVA)', 'Peak Loading (-)', 'Voltage (kV)', 'BLM Zone1',
                      'BLM Zone2', 'Bus1', 'Bus2', 'lat1', 'long1', 'lat2', 'long2', 'county1', 'county2',
                    'Taxonomy Climate1', 'Taxonomy Climate2', 'ASHRAE Climate1', 'ASHRAE Climate2']
    data = np.zeros((len(line_list), len(line_variables)))
    trans_line_df = pd.DataFrame(data,
                            index=line_list,
                            columns=line_variables)

    trans_line_df['Line ID'] = line_list

    i = 0
    for branch in config_data['branch']:
        for bus in config_data['bus']:
            if branch[0] == bus[0]:
                bus1 = bus
            elif branch[1] == bus[0]:
                bus2 = bus
        trans_line_df.loc[line_list[i], 'Bus1'] = bus1[0]
        trans_line_df.loc[line_list[i], 'Bus2'] = bus2[0]
        # Only output data for branches with end points with same voltage - should eliminate low to high voltage
        # 'branches' that are representing substations.
        if bus1[9] == bus2[9]:
            trans_line_df.loc[line_list[i], 'Capacity (MVA)'] = branch[5]
            if sim_results:
                # TODO - need to verify this works on 200 bus results.
                trans_line_df.loc[line_list[i], 'Peak Loading (-)'] = test_data_df['rt_line' + str(i+1)].abs().max()
            else:
                trans_line_df.loc[line_list[i], 'Peak Loading (-)'] = 'TBD'
            trans_line_df.loc[line_list[i], 'Voltage (kV)'] = bus1[9]
            # Determine line length based on assumptions for MVAR/Mile to get lengths cited in TESP:
            # https://github.com/pnnl/tesp/blob/master/ercot/bulk_system/Lines.csv
            if bus1[9] == 345:
                trans_line_df.loc[line_list[i], 'Length (miles)'] = branch[4]*100/0.8616*(1084 / branch[5])
            elif bus1[9] == 138:
                trans_line_df.loc[line_list[i], 'Length (miles)'] = branch[4]*100/0.1039*(157 / branch[5])
            else:
                raise Exception('Transmission line length equation not implemented for ' + str(bus1[9]) + " volts.")
            # Determine BLM Zone for costing input.
            if bus1[0] < 201:
                trans_line_df.loc[line_list[i], 'BLM Zone1'] = dso_metadata['DSO_'+str(bus1[0])]['blm_zone']
                trans_line_df.loc[line_list[i], 'lat1'] = dso_metadata['DSO_' + str(bus1[0])]['latitude']
                trans_line_df.loc[line_list[i], 'long1'] = dso_metadata['DSO_' + str(bus1[0])]['longitude']
                trans_line_df.loc[line_list[i], 'county1'] = dso_metadata['DSO_' + str(bus1[0])]['county']
                trans_line_df.loc[line_list[i], 'Taxonomy Climate1'] = dso_metadata['DSO_' + str(bus1[0])]['climate_zone']
                trans_line_df.loc[line_list[i], 'ASHRAE Climate1'] = dso_metadata['DSO_' + str(bus1[0])]['ashrae_zone']
            else:
                # For the high voltage buses in 200 bus case need to find associated low voltage bus to get metadata
                for branch2 in config_data['branch']:
                    if branch2[0] == bus1[0] and branch2[1] <201:
                        trans_line_df.loc[line_list[i], 'BLM Zone1'] = dso_metadata['DSO_' + str(branch2[1])]['blm_zone']
                        trans_line_df.loc[line_list[i], 'lat1'] = dso_metadata['DSO_' + str(branch2[1])]['latitude']
                        trans_line_df.loc[line_list[i], 'long1'] = dso_metadata['DSO_' + str(branch2[1])]['longitude']
                        trans_line_df.loc[line_list[i], 'county1'] = dso_metadata['DSO_' + str(branch2[1])]['county']
                        trans_line_df.loc[line_list[i], 'Taxonomy Climate1'] = dso_metadata['DSO_' + str(branch2[1])][
                            'climate_zone']
                        trans_line_df.loc[line_list[i], 'ASHRAE Climate1'] = dso_metadata['DSO_' + str(branch2[1])][
                            'ashrae_zone']
                    if branch2[1] == bus1[0] and branch2[0] <201:
                        trans_line_df.loc[line_list[i], 'BLM Zone1'] = dso_metadata['DSO_' + str(branch2[0])]['blm_zone']
                        trans_line_df.loc[line_list[i], 'lat1'] = dso_metadata['DSO_' + str(branch2[0])]['latitude']
                        trans_line_df.loc[line_list[i], 'long1'] = dso_metadata['DSO_' + str(branch2[0])]['longitude']
                        trans_line_df.loc[line_list[i], 'county1'] = dso_metadata['DSO_' + str(branch2[0])]['county']
                        trans_line_df.loc[line_list[i], 'Taxonomy Climate1'] = dso_metadata['DSO_' + str(branch2[0])][
                            'climate_zone']
                        trans_line_df.loc[line_list[i], 'ASHRAE Climate1'] = dso_metadata['DSO_' + str(branch2[0])][
                            'ashrae_zone']
            if bus2[0] < 201:
                trans_line_df.loc[line_list[i], 'BLM Zone2'] = dso_metadata['DSO_' + str(bus2[0])]['blm_zone']
                trans_line_df.loc[line_list[i], 'lat2'] = dso_metadata['DSO_' + str(bus2[0])]['latitude']
                trans_line_df.loc[line_list[i], 'long2'] = dso_metadata['DSO_' + str(bus2[0])]['longitude']
                trans_line_df.loc[line_list[i], 'county2'] = dso_metadata['DSO_' + str(bus2[0])]['county']
                trans_line_df.loc[line_list[i], 'Taxonomy Climate2'] = dso_metadata['DSO_' + str(bus2[0])]['climate_zone']
                trans_line_df.loc[line_list[i], 'ASHRAE Climate2'] = dso_metadata['DSO_' + str(bus2[0])]['ashrae_zone']
            else:
                # For the high voltage buses in 200 bus case need to find associated low voltage bus to get metadata
                for branch2 in config_data['branch']:
                    if branch2[0] == bus2[0] and branch2[1] < 201:
                        trans_line_df.loc[line_list[i], 'BLM Zone2'] = dso_metadata['DSO_' + str(branch2[1])][
                            'blm_zone']
                        trans_line_df.loc[line_list[i], 'lat2'] = dso_metadata['DSO_' + str(branch2[1])]['latitude']
                        trans_line_df.loc[line_list[i], 'long2'] = dso_metadata['DSO_' + str(branch2[1])]['longitude']
                        trans_line_df.loc[line_list[i], 'county2'] = dso_metadata['DSO_' + str(branch2[1])]['county']
                        trans_line_df.loc[line_list[i], 'Taxonomy Climate2'] = dso_metadata['DSO_' + str(branch2[1])][
                            'climate_zone']
                        trans_line_df.loc[line_list[i], 'ASHRAE Climate2'] = dso_metadata['DSO_' + str(branch2[1])][
                            'ashrae_zone']
                    if branch2[1] == bus2[0] and branch2[0] < 201:
                        trans_line_df.loc[line_list[i], 'BLM Zone2'] = dso_metadata['DSO_' + str(branch2[0])][
                            'blm_zone']
                        trans_line_df.loc[line_list[i], 'lat2'] = dso_metadata['DSO_' + str(branch2[0])]['latitude']
                        trans_line_df.loc[line_list[i], 'long2'] = dso_metadata['DSO_' + str(branch2[0])]['longitude']
                        trans_line_df.loc[line_list[i], 'county2'] = dso_metadata['DSO_' + str(branch2[0])]['county']
                        trans_line_df.loc[line_list[i], 'Taxonomy Climate2'] = dso_metadata['DSO_' + str(branch2[0])][
                            'climate_zone']
                        trans_line_df.loc[line_list[i], 'ASHRAE Climate2'] = dso_metadata['DSO_' + str(branch2[0])][
                            'ashrae_zone']
        i += 1

    file_name = '\\Transmission_Line_statistics.csv'
    trans_line_df.to_csv(path_or_buf=data_path + file_name)

    # Set up DataFrame structure for bus statistics output
    bus_list = [str(n+1) for n in range(len(config_data['bus']))]
    bus_variables = ['Bus ID', 'Voltage (kV)', 'Sum Line Capacity (MVA)', 'EHV Capacity (MVA)', 'DSO Peak Load (MW)',
                     'Sum Gen Ratings (MW)']
    data = np.zeros((len(bus_list), len(bus_variables)))
    trans_bus_df = pd.DataFrame(data,
                            index=bus_list,
                            columns=bus_variables)

    i = 0
    for bus in config_data['bus']:
        trans_bus_df.loc[bus_list[i], 'Bus ID'] = bus[0]
        trans_bus_df.loc[bus_list[i], 'Voltage (kV)'] = bus[9]
        # TODO: Using average load for now as stand in.  Need to replace with peak load from wholesale analysis.
        if bus[0] < 200:
            trans_bus_df.loc[line_list[i], 'DSO Peak Load (MW)'] = dso_metadata['DSO_' + str(bus[0])][
                'average_load_MW']

        gen_ratings = 0
        for gen in config_data['gen']:
            if gen[0] == bus[0]:
                gen_ratings += gen[6]
        trans_bus_df.loc[bus_list[i], 'Sum Gen Ratings (MW)'] = gen_ratings

        linecap_count = 0
        for branch in config_data['branch']:
    #             id += 1
            if branch[0] == bus[0]:
                # TODO - -add net peak capacity for both HV and EHV nodes.
                # test_data_df['nodeabs' + str(node)] += -test_data_df['rt_line' + str(id)] * branch[5]
                # test_data_df['nodeabnorm' + str(node)] += test_data_df['rt_line' + str(id)].abs() * branch[5]
                linecap_count += branch[5]
                # Identify branches that connect EHV and HV networks and record that branch capacity as a proxity
                # for substation capacity
                if bus[0] > 200 and branch[1] <=200:
                    trans_bus_df.loc[bus_list[i], 'EHV Capacity (MVA)'] = branch[5]
            elif branch[1] == bus[0]:
                # test_data_df['nodeabs' + str(node)] += test_data_df['rt_line' + str(id)] * branch[5]
                # test_data_df['nodeabnorm' + str(node)] += test_data_df['rt_line' + str(id)].abs() * branch[5]
                linecap_count += branch[5]
                # Identify branches that connect EHV and HV networks and record that branch capacity as a proxity
                # for substation capacity
                if bus[0] > 200 and branch[0] <=200:
                    trans_bus_df.loc[bus_list[i], 'EHV Capacity (MVA)'] = branch[5]
        trans_bus_df.loc[bus_list[i], 'Sum Line Capacity (MVA)'] = linecap_count
        i += 1


    file_name = '\\Transmission_Bus_statistics.csv'
    trans_bus_df.to_csv(path_or_buf=data_path + file_name)

#     # ercot_df = load_ercot_data(metadata_path, base_case, day_range)
#     # ercot_sum = ercot_df.loc[:, ercot_df.columns[ercot_df.columns.str.contains('Bus')]].sum(
#     #     axis=1)
#     # gen_df = load_gen_data(base_case, 'gen', day_range)
#     # gen_sum = gen_df.groupby(level=0)['Pgen'].sum()
#     #
#     # transmission_loss = (gen_sum - ercot_sum) / gen_sum
#     # transmission_loss.plot()
#     # Load Transmission Line Data
#     # case_config = load_json(config_path, 'system_case_config.json')
#
#     rt_line_data_df = load_gen_data(data_path, 'rt_line', day_range)
#     test_data_df = rt_line_data_df.unstack(level=1)
#     test_data_df.columns = test_data_df.columns.droplevel()
#
#     line_cols = [col for col in test_data_df.columns if 'line' in col]
#     for col in line_cols:
#         test_data_df[col] = pd.to_numeric(test_data_df[col])
#     fig = test_data_df.plot()

#
#     for node in range(1, 9):
#         id = 0
#         linecap_count = 0
#         test_data_df['nodeabs' + str(node)] = np.zeros_like(test_data_df[line_cols[0]])
#         test_data_df['nodeabnorm' + str(node)] = np.zeros_like(test_data_df[line_cols[0]])
#         for branch in case_config['branch']:
#             id += 1
#             if branch[0] == node:
#                 test_data_df['nodeabs' + str(node)] += -test_data_df['rt_line' + str(id)] * branch[5]
#                 test_data_df['nodeabnorm' + str(node)] += test_data_df['rt_line' + str(id)].abs() * branch[5]
#                 linecap_count += branch[5]
#             elif branch[1] == node:
#                 test_data_df['nodeabs' + str(node)] += test_data_df['rt_line' + str(id)] * branch[5]
#                 test_data_df['nodeabnorm' + str(node)] += test_data_df['rt_line' + str(id)].abs() * branch[5]
#                 linecap_count += branch[5]
#         test_data_df['nodenorm' + str(node)] = test_data_df['nodeabs' + str(node)] / linecap_count
#         test_data_df['nodeabnorm' + str(node)] = test_data_df['nodeabnorm' + str(node)] / linecap_count
#
#     nodeabs_cols = [col for col in test_data_df.columns if 'nodeabs' in col]
#     test_data_df['Node_sum'] = test_data_df[nodeabs_cols].sum(axis=1)
#
#     return transmission_df


def metadata_dist_plots(system, sys_class, variable, dso_range, case, data_path, metadata_path, agent_prefix):
    """  For a , system, class, and dso_range this function will load in the required data, and plot a
     histogram of the population distribution.
    Arguments:
        system (str): the system to be plotted (e.g. 'house')
        sys_class (str): the subclass to be plotted (e.g. 'SINGLE_FAMILY').  If system has no subsystems or you want to
            see the full population set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'sqft')
        dso_range (range): range of the DSOs to be plotted.  DSO 1 has an index of 0
        case (str): folder extension of case of interest
        agent_prefix (str): folder extension for agent data

    Returns:
        saves plot of population distribution to file
        """
    dist = []
    label = []
    day_num = 1
    for dso in dso_range:
        file_name = 'Substation_' + str(dso) + '_glm_dict.json'
        metadata = load_json(case + agent_prefix + str(dso), file_name)

        agent_file_name = 'Substation_' + str(dso) + '_agent_dict.json'
        agent_metadata = load_json(case + agent_prefix + str(dso), agent_file_name)

        metadata = customer_meta_data(metadata, agent_metadata, metadata_path)

        dist_var = []

        if variable in ['kw-hr', 'max_kw', 'avg_load', 'load_factor']:
            pop_df, sum_df = load_agent_data(data_path, agent_prefix, str(dso), day_num, 'energy')
        elif variable in ['HVAC_deg-hrs', 'WH_galF-hrs']:
            amenity_df = load_agent_data(data_path, agent_prefix, str(dso), day_num, 'amenity')
        elif variable in ['bill']:
            pop_df, sum_df = load_agent_data(data_path, agent_prefix, str(dso), day_num, 'bill')
            # TODO: need to fix hardwiring of base_case path


        # TO DO - currently pulling only houses - need to split by residential type once that data is available.
        for each in metadata[system]:
            if sys_class is not None:
                if system == 'houses':
                    if metadata[system][each]['house_class'] == sys_class:
                        if variable in ['HVAC_deg-hrs']:
                            if metadata[system][each]['cooling'] != 'NONE' \
                                    and metadata[system][each]['heating'] != 'NONE':
                                dist_var.append(amenity_df.loc[(each, variable), 'sum'])
                        elif variable in ['WH_galF-hrs']:
                            dist_var.append(amenity_df.loc[(each, variable), 'sum'])
                        else:
                            dist_var.append(metadata[system][each][variable])
                elif system == 'billingmeters':
                    if variable in ['kw-hr', 'max_kw', 'avg_load', 'load_factor']:
                        if sys_class in ['residential', 'commercial', 'industrial']:
                            #TODO: need to work out why some unknown loads are not getting a tariff class.
                            if metadata[system][each]['building_type'] != 'UNKNOWN':
                                if metadata[system][each]['tariff_class'] == sys_class:
                                    dist_var.append(pop_df.loc[(each, variable), 'sum'])
                        else:
                            if metadata[system][each]['building_type'] == sys_class:
                                dist_var.append(pop_df.loc[(each, variable), 'sum'])
                    elif variable in ['sqft']:
                        if sys_class in ['residential', 'commercial', 'industrial']:
                            # TODO: need to work out why some unknown loads are not getting a tariff class.
                            if metadata[system][each]['building_type'] != 'UNKNOWN':
                                if metadata[system][each]['tariff_class'] == sys_class:
                                    dist_var.append(metadata[system][each][variable])
                        else:
                            if metadata[system][each]['building_type'] == sys_class:
                                dist_var.append(metadata[system][each][variable])
                else:
                    raise Exception('Still need to integrate classes for ' + system)
            else:
                if variable in ['kw-hr', 'max_kw', 'avg_load', 'load_factor']:
                    dist_var.append(pop_df.loc[(each, variable),'sum'])
                elif variable == 'bill':
                    dist_var.append(pop_df.loc[(each, 'total'),'sum'])
                else:
                    dist_var.append(metadata[system][each][variable])
        # plt.hist(dist_var, bins=10, alpha=0.5, edgecolor='k', label='DSO ' + dso[i])

        dist.append(dist_var)
        label.append('DSO ' + str(dso))
    if sys_class is None:
        sys_class = ''
    stats = False
    if stats:
        # listofmeans = [np.mean(i) for i in dist]
        tot_list = [j for i in dist for j in i]
        mean = np.format_float_positional(np.mean(tot_list), precision=3, unique=False, fractional=False, trim='k')
        median = np.format_float_positional(np.median(tot_list), precision=3, unique=False, fractional=False, trim='k')
    plt.figure()
    plt.hist(dist, bins=20, alpha=0.5, edgecolor='k', label=label)
    plt.title(system + ': ' + sys_class + ' ' + variable + ' distribution', size=16)
    plt.legend(loc='upper right', prop={'size': 11})
    plt.xlabel(variable, size=13)
    plt.ylabel('Count', size=13)
    if stats:
        ax = plt.gca()
        plt.text(0.8, 0.4, "Mean = " + mean, size=13, horizontalalignment='center',
                 verticalalignment='center', transform=ax.transAxes)
        plt.text(0.8, 0.33, "Median = " + median, size=13, horizontalalignment='center',
                 verticalalignment='center', transform=ax.transAxes)

    plot_filename = datetime.now().strftime('%Y%m%d') + 'Meta_data_distribution' +system + sys_class + variable +  '.png'
    file_path_fig = os.path.join(data_path, 'plots', plot_filename)

    plt.savefig(file_path_fig, bbox_inches='tight')


def amenity_loss(gld_metadata, dir_path, folder_prefix, dso_num, day_range):
    """Determines the loss of amenity metrics (aka unmet hours) for HVAC and WH.
    Arguments:
        gld_metadata (dict): gld metadata structure for the DSO to be analyzed
        dir_path (str): directory path for the case to be analyzed
        folder_prefix (str): prefix of GLD folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        day_range (list): range of days to be summed (for example a month).
    Returns:
        amenity_df: dataframe of loss of amenity metrics for HVAC and WH
        """
    # Create empty dataframe structure for all meters.
    amenity = []
    variable = []
    month = []
    log_list = ['Date,Building,Unmet Hours']

    for each in gld_metadata['houses']:  # TODO: Should probably change this to meters (customers and average for multiple zones)
        amenity.append(each)
        variable.append('HVAC_setpoint_cool_deg-hrs')
        month.append(0)
        amenity.append(each)
        variable.append('HVAC_setpoint_heat_deg-hrs')
        month.append(0)
        amenity.append(each)
        variable.append('HVAC_cool_deg-hrs')
        month.append(0)
        amenity.append(each)
        variable.append('HVAC_heat_deg-hrs')
        month.append(0)
        amenity.append(each)
        variable.append('HVAC_deg-hrs')
        month.append(0)
        amenity.append(each)
        variable.append('WH_galF-hrs')
        month.append(0)

    amenity_df = pd.DataFrame(month,
                            index=[amenity, variable],
                            columns=['sum'])

    agent_metadata = load_json(dir_path + '/DSO_' + dso_num, 'Substation_' + dso_num + '_agent_dict.json')

    # load house data for each day
    for day in day_range:
        # Label columns of data frame by actual calendar date (not simulation day)
        date = get_date(dir_path,dso_num,str(day))
        day_name = date.strftime("%m-%d")
        amenity_df[day_name] = [0] * len(amenity_df)
        # Load meter data and index it based on time and name.
        house_meta_df, house_df = load_system_data(dir_path, folder_prefix, dso_num, str(day), 'house')
        house_df = house_df.set_index(['time', 'name'])
        dead_band = 1
        # Start calculating
        # house_df['cool_excursion'] = house_df['air_temperature_avg'] \
        #                              - (house_df['air_temperature_setpoint_cooling'] + dead_band)
        # house_df['heat_excursion'] = (house_df['air_temperature_setpoint_heating'] - dead_band) \
        #                              - house_df['air_temperature_avg']
        # house_df['WH_excursion'] = ((house_df['waterheater_setpoint_avg'] - dead_band)
        #                              - house_df['waterheater_temp_avg']) * house_df['waterheater_demand_avg']
        for each in gld_metadata['houses']:
            # if metadata['houses'][each]['cooling'] != 'NONE':

            temp_df = house_df.xs(each, level=1)[['air_temperature_avg', 'waterheater_temp_avg',
                                                  'air_temperature_setpoint_cooling', 'air_temperature_setpoint_heating',
                                                  'waterheater_setpoint_avg',
                                                  'waterheater_demand_avg']]
            # For houses that have agents get schedules from agent dictionary since these have not been altered by agent control
            schedules = get_house_schedules(agent_metadata, gld_metadata, each)
            if schedules['cool_weekday'] is not None:
                if date.weekday() < 5:
                    temp_df['cool_setpoint_excursion'] = temp_df['air_temperature_setpoint_cooling'] - schedules['cool_weekday']
                    temp_df['heat_setpoint_excursion'] = temp_df['air_temperature_setpoint_heating'] - schedules['heat_weekday']
                    temp_df['cool_excursion'] = temp_df['air_temperature_avg'] - [x+dead_band for x in schedules['cool_weekday']]
                    temp_df['heat_excursion'] = [x-dead_band for x in schedules['heat_weekday']] - temp_df['air_temperature_avg']
                else:
                    temp_df['cool_setpoint_excursion'] = temp_df['air_temperature_setpoint_cooling'] - schedules['cool_weekend']
                    temp_df['heat_setpoint_excursion'] = temp_df['air_temperature_setpoint_heating'] - schedules['heat_weekend']
                    temp_df['cool_excursion'] = temp_df['air_temperature_avg'] - [x+dead_band for x in schedules['cool_weekend']]
                    temp_df['heat_excursion'] = [x-dead_band for x in schedules['heat_weekend']] - temp_df['air_temperature_avg']
                cool_setpoint_ex_sum = temp_df.loc[
                                           temp_df['cool_setpoint_excursion'] > 0, 'cool_setpoint_excursion'].sum() / 12
                heat_setpoint_ex_sum = temp_df.loc[
                                           temp_df['heat_setpoint_excursion'] < 0, 'heat_setpoint_excursion'].sum() / 12
                cool_ex_sum = temp_df.loc[temp_df['cool_excursion'] > 0, 'cool_excursion'].sum() / 12
                heat_ex_sum = temp_df.loc[temp_df['heat_excursion'] > 0, 'heat_excursion'].sum() / 12
            else:
                cool_setpoint_ex_sum = 0
                heat_setpoint_ex_sum = 0
                cool_ex_sum = 0
                heat_ex_sum = 0
            if schedules['wh_Tdesired'] is not None:
                temp_df['waterheater_setpoint_avg'] = [schedules['wh_Tdesired'] for i in range(len(temp_df))]
                temp_df['WH_excursion'] = ((temp_df['waterheater_setpoint_avg'] - dead_band)
                                             - temp_df['waterheater_temp_avg']) * temp_df['waterheater_demand_avg']
                amenity_df.loc[(each, 'WH_galF-hrs'), day_name] = temp_df.loc[temp_df['WH_excursion'] > 0,
                                                                          'WH_excursion'].sum()/12
            else:
                amenity_df.loc[(each, 'WH_galF-hrs'), day_name] = 0

            sum_total = cool_ex_sum + heat_ex_sum
            amenity_df.loc[(each, 'HVAC_setpoint_cool_deg-hrs'), day_name] = cool_setpoint_ex_sum
            amenity_df.loc[(each, 'HVAC_setpoint_heat_deg-hrs'), day_name] = heat_setpoint_ex_sum
            amenity_df.loc[(each, 'HVAC_cool_deg-hrs'), day_name] = cool_ex_sum
            amenity_df.loc[(each, 'HVAC_heat_deg-hrs'), day_name] = heat_ex_sum
            amenity_df.loc[(each, 'HVAC_deg-hrs'), day_name] = sum_total

            if cool_ex_sum > 0 and heat_ex_sum > 0:
                log_list.append(day_name + ',' + each + ',' + str(sum_total))

    os.chdir(dir_path + folder_prefix + dso_num)
    with open('DSO' + dso_num + '_amenity_log.csv', 'w') as f:
        for item in log_list:
            f.write("%s\n" % item)

    amenity_df['sum'] = amenity_df.sum(axis=1)
    os.chdir(dir_path + folder_prefix + dso_num)
    amenity_df.to_hdf('amenity_data.h5', key='amenity_data')

    return amenity_df


def annual_amenity(metadata, month_list, folder_prefix, dso_num):
    """Creates a dataframe of monthly energy consumption values and annual sum based on monthly h5 files.
    Arguments:
        month_list (list): list of lists.  Each sub list has month name (str), directory path (str)
        folder_prefix (str): prefix of GLD folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
    Returns:
        year_meter_df: dataframe of energy consumption and max 15 minute power consumption for each month and total
        year_energysum_df: dataframe of energy consumption summations by customer class (res., commercial, and indust)
        """

    for i in range(len(month_list)):
        filename = (month_list[i][1] + folder_prefix + dso_num + '/amenity_data.h5')
        amenity_df = pd.read_hdf(filename, key='amenity_data', mode='r')

        if i == 0:
            year_amenity_df = amenity_df[['sum']]
            year_amenity_df = year_amenity_df.rename(columns={'sum':month_list[i][0]})
        else:
            year_amenity_df[month_list[i][0]] = amenity_df[['sum']]

    year_amenity_df['sum'] = year_amenity_df.sum(axis=1)

    year_amenity_df['cooling'] = None
    year_amenity_df['heating'] = None
    year_amenity_df['sqft'] = None
    year_amenity_df['house_class'] = None

    for each in metadata['houses']:
        year_amenity_df.loc[(each, 'HVAC_deg-hrs'), ['cooling']] = metadata['houses'][each]['cooling']
        year_amenity_df.loc[(each, 'HVAC_deg-hrs'), ['heating']] = metadata['houses'][each]['heating']
        year_amenity_df.loc[(each, 'HVAC_deg-hrs'), ['sqft']] = metadata['houses'][each]['sqft']
        year_amenity_df.loc[(each, 'HVAC_deg-hrs'), ['house_class']] = metadata['houses'][each]['house_class']

    return year_amenity_df


def customer_comparative_analysis(case_data, comp_data, case_path, comp_path, dso_num, dso_metadata_path, month='sum', slice=None):
    """Creates a comparison of change in energy consumption and anemities for all customers:
        case_data (str): path location for reference case with annual energy and amenity data
        comp_data (str): path location for comparison case with annual energy and amenity data
        case_path (str): path location for reference case with simulation metadata for agents/GLD etc.
        comp_path (str): path location for comparison case with simulation metadata for agents/GLD etc.
        dso_num (str): dso to be plotted
        dso_metadata_path (str): path to location of DSO metadata files
        month (str): month of annual analysis to be plotted.  set to 'sum' to plot aggregate of all data.
        slice (str): sub set of data to be plotted (e.g. 'residential', 'office', 'HVAC'
    Returns:
        saves plot to file.
        """
    base_metadata = load_json(case_path + '/DSO_' + dso_num, 'Substation_'+dso_num+'_glm_dict.json')
    metadata = load_json(comp_path + '/DSO_' + dso_num, 'Substation_'+dso_num+'_glm_dict.json')

    base_agent_metadata = load_json(case_path + '/DSO_' + dso_num, 'Substation_'+dso_num+'_agent_dict.json')
    agent_metadata = load_json(comp_path + '/DSO_' + dso_num, 'Substation_'+dso_num+'_agent_dict.json')

    base_metadata = customer_meta_data(base_metadata, base_agent_metadata, dso_metadata_path)
    metadata = customer_meta_data(metadata, agent_metadata, dso_metadata_path)

    case_energy_df, case_energy_sums_df = load_agent_data(case_data, None, dso_num, None, 'energy')
    comp_energy_df, comp_energy_sums_df = load_agent_data(comp_data, None, dso_num, None, 'energy')
    case_bill_df = pd.read_csv(case_data + '/cust_bill_dso_' + dso_num + '_data.csv', index_col=[0,1])
    comp_bill_df = pd.read_csv(comp_data + '/cust_bill_dso_' + dso_num + '_data.csv', index_col=[0,1])
    # case_bill_df, bill_junk_df = load_agent_data(case_data, None, dso_num, None, 'bill')
    # comp_bill_df, bill_junk_df = load_agent_data(comp_data, None, dso_num, None, 'bill')
    case_amenity_df = pd.read_csv(case_data + '/amenity_dso_' + dso_num + '_data.csv', index_col=[0,1])
    comp_amenity_df = pd.read_csv(comp_data + '/amenity_dso_' + dso_num + '_data.csv', index_col=[0,1])
    case_amenity_df = case_amenity_df.drop(axis = 1, labels=['cooling', 'heating', 'sqft', 'house_class'])
    comp_amenity_df = comp_amenity_df.drop(axis=1, labels=['cooling', 'heating', 'sqft', 'house_class'])
    # TODO: Need to fix bug onn why I can not reread amenity 5h files
    # case_amenity_df = load_agent_data(case_data, None, dso_num, None, 'amenity')
    # comp_amenity_df = load_agent_data(comp_data, None, dso_num, None, 'amenity')

    customer_diff_df = case_energy_df.subtract(comp_energy_df).divide(case_energy_df)
    bill_diff_df = case_bill_df.subtract(comp_bill_df).divide(case_bill_df)
    amenity_diff_df = comp_amenity_df.subtract(case_amenity_df)

    customer_diff_df = customer_diff_df.unstack(level=1)
    # amenity_diff_df = amenity_diff_df.unstack(level=1)

    for col in amenity_diff_df.columns.to_list():
        customer_diff_df[(col, 'HVAC_deg-hrs')] = 0
        customer_diff_df[(col, 'HVAC_cool_deg-hrs')] = 0
        customer_diff_df[(col, 'HVAC_setpoint_cool_deg-hrs')] = 0
        customer_diff_df[(col, 'WH_galF-hrs')] = None

    for house in metadata['houses']:
        meter_id = metadata['houses'][house]['billingmeter_id']
        if metadata['billingmeters'][meter_id]['num_zones'] == 0:
            metadata['billingmeters'][meter_id]['num_zones'] = 1
        for col in amenity_diff_df.columns.to_list():
            customer_diff_df.loc[meter_id, (col, 'HVAC_deg-hrs')] += amenity_diff_df.loc[(house, 'HVAC_deg-hrs'), col]/\
                                                                     metadata['billingmeters'][meter_id]['num_zones']
            customer_diff_df.loc[meter_id, (col, 'HVAC_setpoint_cool_deg-hrs')] += amenity_diff_df.loc[(house, 'HVAC_setpoint_cool_deg-hrs'), col]/\
                                                                     metadata['billingmeters'][meter_id]['num_zones']
            customer_diff_df.loc[meter_id, (col, 'HVAC_cool_deg-hrs')] += amenity_diff_df.loc[(house, 'HVAC_cool_deg-hrs'), col]/\
                                                                     metadata['billingmeters'][meter_id]['num_zones']
            customer_diff_df.loc[meter_id, (col, 'WH_galF-hrs')] = amenity_diff_df.loc[(house, 'WH_galF-hrs'), col]

    # customer_diff_df['cooling'] = None
    # customer_diff_df['heating'] = None
    # customer_diff_df['sqft'] = None
    # customer_diff_df['house_class'] = None
    customer_diff_df[('metadata','participating')] = None
    customer_diff_df[('metadata','slider_setting')] = None


    for each in metadata['billingmeters']:
        customer_diff_df.loc[(each), [('metadata','participating')]] = metadata['billingmeters'][each]['cust_participating']
        customer_diff_df.loc[(each), [('metadata','slider_setting')]] = metadata['billingmeters'][each]['slider_setting']

    # x = customer_diff_df.loc[(slice(None), ['kw-hr']), :]
    # x = customer_diff_df.loc(axis=0)[:, ['kw-hr']]

    customer_diff_df.to_csv(path_or_buf=case_path + '\\customer_diff_data_DSO'+dso_num+'.csv')
    participating = customer_diff_df.loc[customer_diff_df[('metadata','participating')] == True]

    plt.figure()
    plt.scatter(participating[('metadata','slider_setting')], -100*participating[(month,'kw-hr')])
    plt.title('Energy Savings (DSO '+dso_num+'): ' + case_path.split('\\')[-1] + ' Vs. '
              + comp_path.split('\\')[-1] + ' (' + month + ')', size=10)
    # plt.ylim(-30, 5)
    plt.xlabel('Slider Setting', size=13)
    plt.ylabel('Energy Savings (%)', size=13)
    # if stats:
    #     ax = plt.gca()
    #     plt.text(0.8, 0.4, "Mean = " + mean, size=13, horizontalalignment='center',
    #              verticalalignment='center', transform=ax.transAxes)
    #     plt.text(0.8, 0.33, "Median = " + median, size=13, horizontalalignment='center',
    #              verticalalignment='center', transform=ax.transAxes)
    plot_filename = datetime.now().strftime('%Y%m%d') + 'EnergySavingsVsSliderDSO' + dso_num +  '.png'
    file_path_fig = os.path.join(case_data, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.figure()
    plt.scatter(participating[('metadata','slider_setting')], 100*participating[(month,'max_kw')])
    plt.title('Max Load Reduction (DSO '+dso_num+'): ' + case_path.split('\\')[-1] + ' Vs. '
              + comp_path.split('\\')[-1] + ' (' + month + ')', size=10)
    plt.ylim(-5, 30)
    plt.xlabel('Slider Setting', size=13)
    plt.ylabel('Max Load Reduction (%)', size=13)
    plot_filename = datetime.now().strftime('%Y%m%d') + 'MaxLoadReductionVsSliderDSO' + dso_num +  '.png'
    file_path_fig = os.path.join(case_data, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.figure()
    plt.scatter(participating[('metadata', 'slider_setting')], -1 * participating[(month, 'HVAC_deg-hrs')], label='HVAC_deg-hrs')
    plt.scatter(participating[('metadata', 'slider_setting')], -1 * participating[(month, 'HVAC_cool_deg-hrs')], label='HVAC_deg-hrs (Cooling Only)')
    # plt.scatter(participating[('metadata', 'slider_setting')], -1 * participating[(month, 'HVAC_heat_deg-hrs')])
    plt.scatter(participating[('metadata', 'slider_setting')], -1 * participating[(month, 'HVAC_setpoint_cool_deg-hrs')], label='Cooling Setpoint Relaxation')
    # plt.scatter(participating[('metadata', 'slider_setting')], -1 * participating[(month, 'HVAC_setpoint_heat_deg-hrs')])
    plt.title('HVAC Amenity (DSO '+dso_num+'): ' + case_path.split('\\')[-1] + ' Vs. '
              + comp_path.split('\\')[-1] + ' (' + month + ')', size=10)
    plt.ylim(0, 250)
    plt.xlabel('Slider Setting', size=13)
    plt.ylabel('Indoor Air Comfort Reduction (deg-hrs)', size=13)
    plt.legend()
    plot_filename = datetime.now().strftime('%Y%m%d') + 'HVACAmenityVsSliderDSO' + dso_num +  '.png'
    file_path_fig = os.path.join(case_data, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.figure()
    plt.scatter(-100 * participating[(month,'kw-hr')], participating[(month, 'HVAC_deg-hrs')])
    plt.title('HVAC Amenity Vs Energy (DSO '+dso_num+'): ' + case_path.split('\\')[-1] + ' Vs. '
              + comp_path.split('\\')[-1] + ' (' + month + ')', size=10)
    # plt.ylim(0, 220)
    # plt.xlim(-25, 0)
    plt.xlabel('Energy Change (%)', size=13)
    plt.ylabel('Indoor Air Comfort Reduction (deg-hrs)', size=13)
    plot_filename = datetime.now().strftime('%Y%m%d') + 'HVACAmenityVsEnergyDSO' + dso_num +  '.png'
    file_path_fig = os.path.join(case_data, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    min_energy_house = metadata['billingmeters'][participating[(month,'kw-hr')].idxmin()]['children'][0]
    metadata['billingmeters'][participating[(month,'kw-hr')].idxmin()]
    metadata['houses'][min_energy_house]
    # base_house = base_metadata['billingmeters'][x['sum'].idxmin()[0]]['children'][0]

    max_energy_house = metadata['billingmeters'][participating[(month, 'kw-hr')].idxmax()]['children'][0]
    metadata['billingmeters'][participating[(month,'kw-hr')].idxmax()]
    metadata['houses'][max_energy_house]

    min_amenity_house = metadata['billingmeters'][participating[(month,'HVAC_deg-hrs')].idxmin()]['children'][0]
    metadata['billingmeters'][participating[(month,'HVAC_deg-hrs')].idxmin()]
    metadata['houses'][min_amenity_house]

    max_amenity_house = metadata['billingmeters'][participating[(month, 'HVAC_deg-hrs')].idxmax()]['children'][0]
    metadata['billingmeters'][participating[(month,'HVAC_deg-hrs')].idxmax()]
    metadata['houses'][max_amenity_house]

    #
    # metadata['houses'][house]
    #
    # base_house = base_metadata['billingmeters'][x['sum'].idxmin()[0]]['children'][0]
    # base_metadata['houses'][base_house]
    #
    #
    #
    # # customer_diff_df.loc[(slice(None), 'kw-hr'), ['sum']]
    # x['sum'].idxmin()[0]
    # x.loc[x['sum'].idxmin()]
    # metadata['billingmeters'][x['sum'].idxmin()[0]]
    #
    # case_energy_df.loc[('R4_25_00_1_tn_107_mtr_1','kw-hr'), 'sum']
    # comp_energy_df.loc[('R4_25_00_1_tn_107_mtr_1', 'kw-hr'), 'sum']
    #

    #
    # return year_amenity_df


def limit_check(log_list, dso_num, system, variable, day_range, case, agent_prefix, GLD_prefix, max_lim, min_lim):
    """  For a specified dso, system, variable, and day_range this function will the time and place of the value that
    most exceeds upper and lower limits.  A text description will be added to a log list and returned.
    Arguments:
        log_list (list): list of limit excursions that will be added to.
        dso_num (str): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be checked (e.g. 'substation', 'house', 'HVAC_agent')
        variable (str): variable to be checked from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day_range (range): range of the day indexes to be checked.  Day 1 has an index of 0
        case (str): folder extension of case of interest
        agent_prefix (str): folder extension for agent data
        GLD_prefix (str): folder extension for GridLAB-D data
        max_lim (float): upper value that variable should not exceed during simulation
        min_lim (float): lower value that variable should not exceed during simulation
    Returns:
        saves heatmap to file
        """
    day = [None] * len(day_range)

    if system in ['weather']:
        #  file_name = 'TE_Base_s' + dso_num + '_glm_dict.json'
        file_name = 'Substation_' + dso_num + '_glm_dict.json'
        metadata = load_json(case + agent_prefix + dso_num, file_name)
        weather_city = metadata["climate"]["name"]
        os.chdir(base_case + '\\' + weather_city)
        weather_data = pd.read_csv('weather.dat')

    # Just do all days for weather
        if max_lim <= weather_data[variable].max():
            suspect = weather_data.loc[weather_data[variable].idxmax()]
            log_list.append('Weather ' + variable + ' of ' + str(suspect[variable]) + ' is greater than limit of ' \
                + str(max_lim) + ' at time ' + suspect['datetime'])
        if min_lim >= weather_data[variable].min():
            suspect = weather_data.loc[weather_data[variable].idxmin()]
            log_list.append('Weather ' + variable + ' of ' + str(suspect[variable]) + ' is less than limit of ' \
                + str(min_lim) + ' at time ' + suspect['datetime'])

    else:
        # =================   core code for agent and gld data  ================

        for i in range(len(day_range)):
            day[i] = (str(day_range[i] + 1))
            if system in ['hvac_agent', 'battery_agent', 'retail_market', 'dso_market', 'water_heater_agent']:
                system_df, agent_bid_df = load_agent_data(case, agent_prefix, dso_num, day[i], system)
                if max_lim <= system_df[variable].max():
                    id = system_df[variable].idxmax()
                    suspect = system_df.loc[system_df[variable].idxmax()]
                    log_list.append(system + ' ' + variable + ' of ' + str(round(suspect[variable], 2)) + \
                                ' is greater than limit of ' + str(max_lim) + ' at time ' + str(id[0]) \
                                + ' in ' + id[1])
                if min_lim >= system_df[variable].min():
                    id = system_df[variable].idxmin()
                    suspect = system_df.loc[system_df[variable].idxmin()]
                    log_list.append(system + ' ' + variable + ' of ' + str(round(suspect[variable], 2)) +\
                            ' is less than limit of ' + str(min_lim) + ' at time ' + str(id[0]) \
                            + ' in ' + id[1])
            elif system in ['substation', 'house', 'billing_meter', 'inverter']:
                system_meta_df, system_df = load_system_data(case, GLD_prefix, dso_num, day[i], system)
                if max_lim <= system_df[variable].max():
                    suspect = system_df.loc[system_df[variable].idxmax()]
                    log_list.append(system + ' ' + variable + ' of ' + str(round(suspect[variable], 2)) + \
                            ' is greater than limit of ' + str(max_lim) + ' at time ' + str(suspect['time']) \
                            + ' in ' + suspect['name'])
                if min_lim >= system_df[variable].min():
                    suspect = system_df.loc[system_df[variable].idxmin()]
                    log_list.append(system + ' ' + variable + ' of ' + str(round(suspect[variable], 2)) + \
                            ' is less than limit of ' + str(min_lim) + ' at time ' + str(suspect['time']) \
                            + ' in ' + suspect['name'])
            else:
                raise Exception('Still need to limit_check integration for ' + system)
    return log_list


def house_check(dso_range, sourceCase, targetCase, houseProperties):
    """Main function of the module.

      Parameters
      ----------
      argv :
          Command line arguments given as:
          -d <Substation/DSO number to be analyzed> -s <source case folder name> -t <target case folder name> -p <property to compare by plots>

      Returns
      -------
      None

      """
    save_plots = True
    # substationNum = 6
    # houseProperty = 'Rdoors'

    log_list = []

    log_list.append('House Population Check: Exceptions List')

    for houseProperty in houseProperties:
        figWidth = 15
        figHeight = 8
        hFig, hAxes = plt.subplots(math.ceil(math.sqrt(int(len(dso_range)+1))),
                                   math.ceil(math.sqrt(int(len(dso_range)+1))), sharex=False, sharey=False,
                                   figsize=(figWidth, figHeight))

        # for substationNum in dsoRange:
        for dso in dso_range:
            # substationNum = dsoInd + 1
            agent_metadata_source = load_json(sourceCase + '/DSO_' + str(dso),
                                              'Substation_' + str(dso) + '_agent_dict.json')
            agent_metadata_target = load_json(targetCase + '/DSO_' + str(dso),
                                              'Substation_' + str(dso) + '_agent_dict.json')
            hAxis = hAxes[int((dso-1) / math.ceil(math.sqrt(int(len(dso_range)+1))))][
                int((dso-1) % math.ceil(math.sqrt(int(len(dso_range)+1))))]
            fileName = 'Substation_' + str(dso) + '_glm_dict.json'
            # filePath_noBatt = os.path.join(os.path.abspath('./'), sourceCase, 'DSO_' + str(substationNum), fileName)
            # filePath_wBatt = os.path.join(os.path.abspath('./'), targetCase, 'DSO_' + str(substationNum), fileName)

            data_noBatt = load_json(os.path.join(sourceCase, 'DSO_' + str(dso)), fileName)
            data_wBatt = load_json(os.path.join(targetCase, 'DSO_' + str(dso)), fileName)
            propData_noBatt = []
            propData_wBatt = []
            # propData_noBatt = np.zeros(len(data_noBatt['houses']))
            # propData_wBatt = np.zeros(len(data_wBatt['houses']))
            houseNum = 0
            for house in data_noBatt['houses'].keys():
                if house in data_wBatt['houses'].keys():

                    if dso == dso_range[0] and houseNum == 1:
                        print('You can check some of these properties:')
                        print(*data_noBatt['houses'][house].keys(), sep="\n")
                    if houseProperty in ['heating_setpoint', 'cooling_setpoint', 'wh_setpoint']:
                        schedule_noBatt = get_house_schedules(agent_metadata_source, data_noBatt, house)
                        schedule_wBatt = get_house_schedules(agent_metadata_target, data_wBatt, house)
                        if houseProperty == 'cooling_setpoint' and schedule_noBatt['cool_weekday'] is not None:
                            houseNum += 1
                            propData_noBatt.append(np.mean(schedule_noBatt['cool_weekday']))
                            propData_wBatt.append(np.mean(schedule_wBatt['cool_weekday']))
                        elif houseProperty == 'heating_setpoint' and schedule_noBatt['heat_weekday'] is not None:
                            houseNum += 1
                            propData_noBatt.append(np.mean(schedule_noBatt['heat_weekday']))
                            propData_wBatt.append(np.mean(schedule_wBatt['heat_weekday']))
                        elif houseProperty == 'wh_setpoint' and schedule_noBatt['wh_Tdesired'] is not None:
                            houseNum += 1
                            propData_noBatt.append(schedule_noBatt['wh_Tdesired'])
                            propData_wBatt.append(schedule_wBatt['wh_Tdesired'])
                    else:
                        # propData_noBatt[houseNum - 1] = data_noBatt['houses'][house][houseProperty]
                        # propData_wBatt[houseNum - 1] = data_wBatt['houses'][house][houseProperty]
                        houseNum += 1
                        propData_noBatt.append(data_noBatt['houses'][house][houseProperty])
                        propData_wBatt.append(data_wBatt['houses'][house][houseProperty])
                    if houseNum != 0 and propData_noBatt[houseNum - 1] != propData_wBatt[houseNum - 1]:
                        log_list.append(
                            'DSO ' + str(dso) + ': House ' + house + ' Property ' + houseProperty +
                            ' is inequal:' + str(propData_noBatt[houseNum - 1]) + ' vs. ' + str(
                                propData_wBatt[houseNum - 1]))

                else:
                    log_list.append('DSO ' + str(dso) + ': House ' + house + ' not present in target population')

            for house in data_wBatt['houses'].keys():
                if house not in data_noBatt['houses'].keys():
                    log_list.append('DSO ' + str(dso) + ': House ' + house + ' not present in source population')

            # fig, ax = plt.subplots()
            x = np.arange(1, houseNum + 1, 1)
            print('DSO {0}: Number of houses from data: {1}'.format(dso, len(data_noBatt['houses'])))
            print('DSO {0}: Number of counted houses: {1}'.format(dso, houseNum))
            hScatter1 = hAxis.scatter(x, propData_noBatt, 24, color='blue', alpha=1, marker='o')
            hScatter2 = hAxis.scatter(x, propData_wBatt, 18, color='red', alpha=0.5, marker='.')
            hAxis.set(title='DSO {0} - {1}'.format(dso, houseProperty))

        if save_plots:
            # plt.show()
            plot_filename = datetime.now().strftime('%Y%m%d') + 'House_Check' + houseProperty + '.png'
            file_path_fig = os.path.join(targetCase, 'plots', plot_filename)

            plt.savefig(file_path_fig, bbox_inches='tight')
        plt.clf()


    # Save log file
    os.chdir(targetCase)
    with open('House_Check_exception_log.txt', 'w') as f:
        for item in log_list:
            f.write("%s\n" % item)


    # return log_list


def get_day_df(dso, system, subsystem, variable, day, case, agent_prefix, gld_prefix):
    """  This utility loads and returns a dataframe for the desired variable for the day and dso in question.
    Arguments:
        dso (str): the DSO that the data should be plotted for (e.g. '1')
        system (str): the system to be plotted (e.g. 'substation', 'house', 'HVAC_agent')
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum, 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        day (str): the day to plotted.
        case (str): folder extension of case of interest
        agent_prefix (str): folder extension for agent data
        gld_prefix (str): folder extension for GridLAB-D data
    Returns:
        df (dataframe): reduced dataframe
        """
    # =================   core code for agent data  ================
    if system in ['hvac_agent', 'battery_agent', 'retail_market', 'dso_market', 'water_heater_agent']:
        system_df, agent_bid_df = load_agent_data(case, agent_prefix, dso, day, system)
    elif system in ['substation', 'house', 'billing_meter', 'inverter', 'evchargerdet']:
        system_meta_df, system_df = load_system_data(case, gld_prefix, dso, day, system)
    elif system == 'weather':
        system_df = load_weather_data(case, agent_prefix, dso, day)
    else:
        raise Exception('Still need to test integration for ' + system)

    if system in ['hvac_agent', 'battery_agent', 'retail_market', 'dso_market', 'water_heater_agent']:
        df = df_reduction(df=system_df, subsystem=subsystem, variable=variable, format='agent')
    elif system in ['house', 'billing_meter', 'inverter', 'evchargerdet']:
        df = df_reduction(df=system_df, subsystem=subsystem, variable=variable, format='gld')
    else:
        temp = system_df.loc[:, variable]
        df = temp.to_frame()

    return df


def df_reduction(df, subsystem, variable, format):
    """  This utility slices a dataframe based on the subsystem (or aggregation) of interest.  This is used for agent
    or house data where there is multiple house data per timestep and reduction is needed before plotting data.
    Arguments:
        df (dataframe): dataframe to be reduced
        subsystem (str): the individual house to be plotted (e.g. 'HousesA_hse_1') or the operator to be used if
                aggregating many houses (e.g. 'sum', 'mean').  If system has no subsystems set equal to None
        variable (str): variable to be plotted from system dataframe (e.g. 'cooling_setpoint' or 'real_power_avg')
        format (str): flag as to whether the data is GridLAB-D ('gld') or agent ('agent') as the format is slightly
                different.
    Returns:
        df (dataframe): reduced dataframe
        """
    # TODO: Index GLD H5 files to speed this up.

    if format is 'gld':
        # Infer house zip loads from total loads and HVAC and WH loads.
        if variable =='zip_loads':
            df[variable] = df['total_load_avg'] - df['hvac_load_avg'] - df['waterheater_load_avg']
        if subsystem in ['sum']:
            temp = df.groupby('time')[variable].sum()
        elif subsystem in ['mean']:
            temp = df.groupby('time')[variable].mean()
        elif subsystem in ['max']:
            temp = df.groupby('time')[variable].max()
        elif subsystem in ['min']:
            temp = df.groupby('time')[variable].min()
        else:
            #df = df[df['name'].str.contains(subsystem)]
            df = df[df.name == subsystem]
            temp = df.loc[:, variable]
    elif format is 'agent':
        if subsystem in ['sum']:
            temp = df.groupby(level=0)[variable].sum()
        elif subsystem in ['mean']:
            temp = df.groupby(level=0)[variable].mean()
        elif subsystem in ['max']:
            temp = df.groupby(level=0)[variable].max()
        elif subsystem in ['min']:
            temp = df.groupby(level=0)[variable].min()
        else:
            # temp = df.xs(subsystem, level=1)[variable]
            df = df[df.uid == subsystem]
            temp = df.loc[:, variable]

    df = temp.to_frame()
    return df


# ----------------------   MAIN  ------------------------

if __name__ == '__main__':
    pd.set_option('display.max_columns', 50)

    tic()
    # ------------ Selection of DSO and Day  ---------------------------------
    dso_num = '2'   # Needs to be non-zero integer
    day_num = '9'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    day_range = range(2, 3)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    dso_range = range(1, 9)  # 1 = DSO 1 (end range should be last DSO +1)

    #  ------------ Select folder locations for different cases ---------

    data_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\V1.1-1317-gfbf326a2\MR-Batt\lean_8_bt'
    # data_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2'
    metadata_path = 'C:\\Users\\reev057\\PycharmProjects\TESP\src\examples\analysis\dsot\data'
    ercot_path = 'C:\\Users\\reev057\\PycharmProjects\TESP\src\examples\analysis\dsot\data'
    base_case = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\V1.1-1317-gfbf326a2\MR-Batt\lean_8_bt'
    trans_case = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\V1.1-1317-gfbf326a2\MR-Flex\lean_8_fl'
    config_path = 'C:\\Users\\reev057\PycharmProjects\TESP\src\examples\dsot_v3'
    case_config_name = '200_system_case_config.json'


    case_config_file = config_path + '\\' + case_config_name
    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'
    case_config = load_json(config_path, case_config_name)
    metadata_file = case_config['dsoPopulationFile']
    dso_meta_file = metadata_path + '\\' + metadata_file

    # Check if there is a plots folder - create if not.
    check_folder = os.path.isdir(data_path + '\\plots')
    if not check_folder:
        os.makedirs(data_path + '\\plots')

    # List of month names, data paths, and day ranges to be used for energy bill and amenity score creation
    month_def = [
        ['Feb', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\May\Base_858c4e40\\2016_02', 2, 11],
        ['March', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\May\Base_858c4e40\\2016_03', 2, 11],
        ['May', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\May\Base_858c4e40\\2016_05', 2, 6],
        ['Aug', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\May\Base_858c4e40\\2016_08', 2, 6]]

    # month_def = [
    #             ['Jan', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_1', 2, 31],
    #             # ['Jan', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_1', 2, 31],
    #             # ['Feb', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_2', 2, 30],
    #             # ['March', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_3', 2, 31],
    #             # ['April', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_4', 2, 31],
    #             # ['May', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_5', 2, 31],
    #             # ['June', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_6', 2, 30],
    #             ['July', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_7', 2, 31]
    #             # ['August', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_8', 2, 7],
    #             # ['Sept', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_9', 2, 30],
    #             # ['Oct', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_10', 2, 31],
    #             # ['Nov', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_11', 2, 30],
    #             #['Dec', 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\\Slim2\\case_slim_12', 2, 7]
    #     ]

    # ---------- Flags to turn on and off plot types etc
    LoadExData = False # load example data frames of GLD and agent data
    DictUpdate = False
    EdgeCases = False
    DailyProfilePlots = False  # plot daily load profiles
    LoadDurationPlots = False   # plot load duration for substation loads (and other loads as desired)
    DailySummaryPlots = False  # plot single summary static for each day of a day range
    PlotDSOComp = False  # Plot daily profile of parameter across a range of DSOs
    PlotHeatMaps = False   # Plot heatmaps for key variables across a day range
    amenity = False  # Calculate the loss of amenity metrics for HVAC and WH etc.
    PlotPopDist = False  # Plot a histogram of a population distribution
    OutLierCheck = False   # Create log of values that exceed
    HouseCheck = False  # Calculate the loss of amenity metrics for HVAC and WH etc.
    gen_plots = False  # Plot generation
    transmission_plots = True  # Plot transmission
    LMP_check = False
    dso_plots = False  # Plot dso items such as RT and DA quantities and loads
    BidCurve3D = False  # Work in progress plot of bid and supply curves for an entire day.
    customer_analysis = False   # plot change in customer metrics between two cases.

    #  ---------------  List of key buildings to investigate for each DSO --------------------
    DSO_Houses = {
    'DSO_1': ['R4_12_47_1_load_9_bldg_20_zone_all', 'R4_12_47_1_tn_15_hse_2', 'R4_12_47_1_load_13_bldg_79_zone_all'],
    'DSO_2': ['R5_12_47_1_tn_40_hse_7', 'R5_12_47_1_tn_63_hse_4', 'R5_12_47_2_tn_11_hse_1'],
    'DSO_3': ['bldg_10_bldg_10_zone_all', 'R4_25_00_1_load_1_bldg_12_zone_all', 'bldg_7_bldg_7_zone_all', 'R4_25_00_1_tn_73_hse_4', 'bldg_9_bldg_9_zone_5'],
    'DSO_4': ['R4_12_47_1_load_9_bldg_20_zone_all', 'R4_12_47_1_tn_15_hse_2', 'R4_12_47_1_load_13_bldg_79_zone_all'],
    'DSO_5': ['R4_12_47_1_load_9_bldg_20_zone_all', 'R4_12_47_1_tn_15_hse_2', 'R4_12_47_1_load_13_bldg_79_zone_all'],
    'DSO_6': ['R4_12_47_1_load_9_bldg_20_zone_all', 'R4_12_47_1_tn_15_hse_2', 'R4_12_47_1_load_13_bldg_79_zone_all'],
    'DSO_7': ['bldg_36_bldg_36_zone_all', 'R5_12_47_1_load_8_bldg_47_floor_2_zone_3', 'R5_12_47_5_tn_185_hse_2'],
    'DSO_8': ['R3_12_47_3_tn_352_hse_1', 'bldg_69_bldg_69_zone_all', 'R3_12_47_3_tn_249_hse_1', 'R4_25_00_1_tn_107_hse_1']}

    # file_name = 'Substation_' + dso_num + '_glm_dict.json'
    # metadata = load_json(base_case + agent_prefix + dso_num, file_name)

    # DSO_meters = []
    # for house in DSO_Houses['DSO_' + dso_num]:
    #     DSO_meters.append(metadata['houses'][house]['billingmeter_id'])

    if LoadExData:
        # df = pd.read_csv(data_path+'\\stats.log', sep='\t', parse_dates=['time'])
        # t0 = df['time'].min()
        # df['time_hr'] = df['time'].map(lambda t: (t - t0).total_seconds() / 3600)
        # df.describe()

        # os.chdir(base_case)
        # filename = 'Building_profiles.h5'
        # store = h5py.File(filename)
        # list(store.keys())
        # bldg_stack_data_df = pd.read_hdf(filename, key='Bldg_Profiles', mode='r')
        # bldg_stack_data_df.to_csv(path_or_buf=data_path + '\\buildingstack_data.csv')
        # temp = bldg_stack_data_df.groupby(['time']).sum()
        # temp.to_csv(path_or_buf=data_path + '\\buildingstack_data_allDSOs.csv')
        # ------------- Load GLM DICT JSON METADATA Baseline ----------------------
        # file_name = 'TE_Base_s' + dso_num +'_glm_dict.json'
        day_range = range(3, 25)
        # da_q_data_df = load_gen_data(data_path, 'da_q', day_range)
        file_name = 'Substation_' + dso_num +'_glm_dict.json'
        metadata = load_json(base_case + agent_prefix + dso_num, file_name)
        # file_name = 'TE_Base_s' + dso_num + '_glm_dict.json'
        # metadata_TE = load_json(trans_case + agent_prefix + dso_num, file_name)
        # rci_df = RCI_analysis(dso_range, base_case, data_path, metadata_path, False)
        #agent_file_name = 'TE_Base_s' + dso_num +'_agent_dict.json'
        agent_file_name = 'Substation_' + dso_num + '_agent_dict.json'
        agent_metadata = load_json(base_case + agent_prefix + dso_num, agent_file_name)
        # da_q_data_df = load_gen_data(base_case, 'da_q', day_range)
        # rt_q_data_df = load_gen_data(base_case, 'rt_q', day_range)
        rt_line_data_df = load_gen_data(base_case, 'rt_line', day_range)
        da_line_data_df = load_gen_data(base_case, 'da_line', day_range)
        # house_name = 'R4_25_00_1_tn_137_hse_1'
        # test = get_house_schedules(base_case, agent_prefix, dso_num, house_name)
        # ----------- Examples of how to Load data --------------------------------
        # os.chdir(data_path + agent_prefix + dso_num)
        # filename = 'retail_market_Substation_' + dso_num + '_3600_metrics.h5'
        # store = h5py.File(filename)
        # list(store.keys())
        # retail_da_data_df = pd.read_hdf(filename, key='/metrics_df1', mode='r')
        # retail_da_price = load_da_retail_price(base_case, agent_prefix, dso_num, day_num)

        # ----------- DSO Curves --------------------------------
        os.chdir(data_path + agent_prefix + dso_num)
        DA_price_df = load_da_retail_price(base_case, '\\DSO_', dso_num, day_num)
        filename = 'dso_market_Substation_' + dso_num + '_86400_metrics.h5'
        store = h5py.File(filename)
        list(store.keys())
        dso_data_curve_df = pd.read_hdf(filename, key='/metrics_df2', mode='r')

        inverter_meta_df, inverter_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'inverter')
        # ev_meta_df, ev_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'evchargerdet')

        case_config = load_json(data_path, 'case_config_' + dso_num + '.json')
        sim_start = datetime.strptime(case_config['SimulationConfig']['StartTime'], '%Y-%m-%d %H:%M:%S')
        curve_time = sim_start + timedelta(days=int(day_num) - 1, hours=14, seconds=0)
        forecast_hour = 3
        real_time = curve_time + timedelta(hours=forecast_hour-3, minutes=30)

        retail_data_df, retail_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, 'retail_market')
        dso_data_df, dso_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, 'dso_market')
        dso_data_df = dso_data_df.droplevel(level=1)
        dso_bid_df = dso_bid_df.loc[real_time,:]
        dso_data_curve_df = dso_data_curve_df.loc[curve_time, :]
        dso_data_curve_df = dso_data_curve_df.loc[dso_data_curve_df['i'] == forecast_hour]

        plt.plot(dso_bid_df['curve_dso_rt_quantities'], dso_bid_df['curve_dso_rt_prices'], label='DSO RT')
        plt.plot(dso_data_curve_df['curve_ws_node_quantities'], dso_data_curve_df['curve_ws_node_prices'], label='Wholesale Supply Node')
        plt.legend()

        fig, ax = plt.subplots()
        ax.plot(dso_data_df.index, dso_data_df['cleared_quantity_rt'], label='DSO Cleared Quantity RT')
        ax2 = ax.twinx()
        ax2.plot(dso_data_df.index, dso_data_df['cleared_price_rt'], label='DSO Cleared Price RT', color='red')
        ax2.set_ylabel('Price ($/kW-hr)')
        ax.set_ylabel('Quantity (kW?)')
        ax.set_xlabel('Time')
        ax.set_title(label='DSO ' + str(dso_num), pad=-9, )
        ax.xaxis_date()
        fig.legend()
        fig.autofmt_xdate()

        # hvac_data_df, hvac_bid_df = load_agent_data(trans_case, agent_prefix, dso_num, day_num, 'hvac_agent')
        # battery_data_df, battery_bid_df = load_agent_data(trans_case, agent_prefix, dso_num, day_num, 'battery_agent')
        # dsomarket_data_df, dsomarket_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, 'dso_market')
        # inverter_meta_df, inverter_df = load_system_data(trans_case, GLD_prefix, dso_num, day_num, 'inverter')
        ev_meta_df, ev_df = load_system_data(trans_case, GLD_prefix, dso_num, day_num, 'evchargerdet')
        tso_data_df, tso_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, 'dso_tso')
        retail_data_df, retail_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, 'retail_market')
        retail_data_df, retail_index_df = load_retail_data(base_case, agent_prefix, dso_num, day_num, 'retail_site')
        DA_price_df = load_da_retail_price(trans_case, '\DSO_', dso_num, day_num)
        wh_data_df, wh_bid_df = load_agent_data(trans_case, agent_prefix, dso_num, day_num, 'water_heater_agent')
        house_meta_df, house_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'house')
        # test  = house_df[house_df.name == 'R5_12_47_3_tn_1000_hse_1']
        # meter_meta_df, meter_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'billing_meter')
        substation_meta_df, substation_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'substation')
        test =  substation_df['real_power_losses_avg']/substation_df['real_power_avg']
        test.plot()

        dso_num = '6'

        meter_data_df = get_day_df(dso_num, 'billing_meter', 'sum', 'real_power_avg', day_num, base_case, agent_prefix,
                                   GLD_prefix)
        sub_load_df = get_day_df(dso_num, 'substation', None, 'real_power_avg', day_num, base_case, agent_prefix,
                                   GLD_prefix)

        sub_losses_df = get_day_df(dso_num, 'substation', None, 'real_power_losses_avg', day_num, base_case, agent_prefix,
                                   GLD_prefix)
        meter_data_df = meter_data_df.set_index(sub_load_df.index)
        plt.plot(inverter_df.groupby('date').sum()['real_power_avg'])
        plt.plot(DA_price_df['cleared_price_da'])
        plt.plot(DA_price_df['cleared_quantity_da'])
        plt.plot(meter_data_df['real_power_avg'], label='DSO '+dso_num+' Meter Sum')
        plt.plot(sub_load_df['real_power_avg'], label='DSO ' + dso_num + ' Substation Total')
        plt.plot(sub_losses_df['real_power_losses_avg']+meter_data_df['real_power_avg'], label='DSO ' + dso_num + ' Substation Losses')
        plt.legend()


        weather_df = load_weather_data(base_case, agent_prefix, dso_num, day_num)
        #
        # plt.figure()
        # plt.plot(dsomarket_data_df.loc[(slice(None), 'DSO_'+dso_num), 'cleared_quantity_rt'], label='dso_market rt_q', marker='.')



        #zmeter_meta_df, zmeter_df = load_system_data('C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\zerometertest', GLD_prefix, '1', '2', 'billing_meter')
        #zhouse_meta_df, zhouse_df = load_system_data('C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\zerometertest',
        #                                             GLD_prefix, '1', '2', 'house')
        fuel_mix = load_ercot_fuel_mix(metadata_path, data_path, day_range)
        rt_gen_data_df = load_gen_data(base_case, 'gen', day_range)
        da_gen_data_df = load_gen_data(base_case, 'da_gen', day_range)
        # test = gen_data_df.xs('gen15', level=1)['Pgen']
        # test.plot()
        # bus_data_df = load_gen_data(base_case, 'bus', day_range)
        # sys_data_df = load_gen_data(base_case, 'sys', day_range)
        da_lmp_data_df = load_gen_data(base_case, 'da_lmp', day_range)

        da_q_data_df = load_gen_data(base_case, 'da_q', day_range)
        rt_q_data_df = load_gen_data(base_case, 'rt_q', day_range)
        rt_line_data_df = load_gen_data(base_case, 'rt_line', day_range)
        da_line_data_df = load_gen_data(base_case, 'da_line', day_range)
        ercot_df = load_ercot_data(metadata_file, base_case, day_range)
        os.chdir(base_case)
        ames_df = load_ames_data(base_case, day_range)
        ames_df[' LMP1'].plot(legend='RT LMP')
        da_lmp_data_df.xs('da_lmp1', level=1)['LMP'].plot(legend='DA LMP')
        ames_df[' coal14'].plot(legend='RT LMP')
        gen_data_df.xs('gen14', level=1)['Pgen'].plot(legend='DA LMP')
        ames_df[' gas53'].plot(legend='RT LMP')
        gen_data_df.xs('gen53', level=1)['Pgen'].plot(legend='DA LMP')

        # ames_df = pd.read_csv('opf.csv', index_col='seconds') # Has RT LMPs for each DSO
        # energy_df, energysum_df = load_agent_data(data_path, agent_prefix, dso_num, day_num, 'energy')
        # energy_df.loc[energy_df.loc[(slice(None), 'max_kw'), ['sum']].idxmax()]
        # regulator_meta_df, regulator_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'regulator')
        # capacitor_meta_df, capacitor_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'capacitor')
        # Reading energy bill -- NOTE THAT RATE CASE WILL NEED TO RUN FIRST FOR THIS TO WORK.

        # os.chdir(base_case)
        # filename = 'bus_case_slim_7_metrics.h5'
        # store = h5py.File(filename)
        # list(store.keys())
        # bus_data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r')
        # filename = 'gen_case_slim_7_metrics.h5'
        # store = h5py.File(filename)
        # list(store.keys())
        # gen_data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r')
        # filename = 'sys_case_slim_7_metrics.h5'
        # store = h5py.File(filename)
        # list(store.keys())
        # sys_data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r')


        # os.chdir(base_case + agent_prefix + dso_num)
        # daystr = '_' + str(int(day_num)-1) + '_'
        # hdf5filenames = [f for f in os.listdir('.') if '86400' in f and daystr in f and f.startswith('dso_market')]
        # # TO DO - error message if more than one value in hdf5filenames
        # filename = hdf5filenames[0]
        # store = h5py.File(filename)
        # list(store.keys())
        # # reading data as pandas dataframe
        # agent_data_df = pd.read_hdf(filename, key='/metrics_df0', mode='r')
        # agent_bid_df = pd.read_hdf(filename, key='/metrics_df1', mode='r')

    # 00 ----------- Dict Update ------------------
    #  Update GLD dict with customer information.
    if DictUpdate:
        for dso in dso_range:
            GLD_dict_file_name = 'Substation_' + str(dso) + '_glm_dict.json'
            GLD_metadata = load_json(base_case + agent_prefix + str(dso), GLD_dict_file_name)
            agent_file_name = 'Substation_' + str(dso) + '_agent_dict.json'
            agent_metadata = load_json(base_case + agent_prefix + str(dso), agent_file_name)

            GLM_metadata = customer_meta_data(GLD_metadata, agent_metadata, metadata_path)

            with open(os.path.join(base_case + agent_prefix + str(dso), GLD_dict_file_name), 'w') as out_file:
                json.dump(GLM_metadata, out_file)

    # 0 ----------- Find Edge Cases ------------------
    #  Identifies the days within a day range for certain edge cases.
    if EdgeCases:
        edge_days, edge_dict, edge_df = find_edge_cases(dso=dso_num, day_range=day_range, case=base_case,
                                                        agent_prefix=agent_prefix, gld_prefix=GLD_prefix)

    # 1 ----------- Daily Load Profiles Plots ------------------
    #  Provide parameters for system, subsystem, variable, base case, anc comparison case (optional)
    if DailyProfilePlots:
        params = [
        #     #['substation', None, 'real_power_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'air_temperature_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'total_load_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'hvac_load_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'zip_loads', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][1], 'total_load_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][1], 'hvac_load_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][1], 'zip_loads', base_case, None],
        #     ['house', DSO_Houses['DSO_'+dso_num][1], 'air_temperature_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_'+dso_num][2], 'air_temperature_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][2], 'zip_loads', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][2], 'total_load_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][2], 'hvac_load_avg', base_case, None]
            # ['billing_meter', DSO_meters[0], 'real_power_avg', base_case, None],
            # ['billing_meter', DSO_meters[1], 'real_power_avg', base_case, None],
            # ['billing_meter', DSO_meters[2], 'real_power_avg', base_case, None]
            # ['house', DSO_Houses['DSO_' + dso_num][4], 'zip_loads', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][4], 'air_temperature_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][4], 'total_load_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][4], 'hvac_load_avg', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][4], 'air_temperature_avg', base_case, None],
        #     #['house', DSO_Houses['DSO_' + dso_num][4], 'air_temperature_avg', base_case, None],
        #     # ['house', DSO_Houses['DSO_'+dso_num][2], 'air_temperature_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][3], 'air_temperature_avg', base_case, None]
        #     # ['house', DSO_Houses['DSO_' + dso_num][0], 'air_temperature_deviation_cooling', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][1], 'air_temperature_deviation_cooling', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][2], 'air_temperature_deviation_cooling', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][2], 'air_temperature_deviation_heating', base_case, None],
        #     # #['house', DSO_Houses['DSO_' + dso_num][3], 'air_temperature_deviation_cooling', base_case, None],
        #     # #['house', DSO_Houses['DSO_' + dso_num][3], 'air_temperature_deviation_heating', base_case, None],
        #     ['house', 'mean', 'air_temperature_deviation_cooling', base_case, trans_case],
        #     ['house', 'mean', 'waterheater_setpoint_avg', base_case, trans_case],
        #     # ['house', 'mean', 'air_temperature_avg', base_case, trans_case],
        #     ['house', 'sum', 'waterheater_load_avg', base_case, trans_case],
        #     ['house', 'sum', 'hvac_load_avg', base_case, trans_case],
        #     # ['house', DSO_Houses['DSO_'+dso_num][2], 'waterheater_load_avg', base_case, None],
        #     # ['billing_meter', 'R4_25_00_1_load_1_bldg_45_zone_all', 'real_power_avg', base_case, None]
        #     # #['house', DSO_Houses['DSO_' + dso_num][3], 'hvac_load_avg', base_case, None],
        #     # ['house', DSO_Houses['DSO_'+dso_num][2], 'hvac_load_avg', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][2], 'waterheater_load_avg', base_case, None],
        #     # ['house', DSO_Houses['DSO_'+dso_num][1], 'hvac_load_avg', base_case, None],
        #     # #['house', DSO_Houses['DSO_' + dso_num][3], 'total_load_avg', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][2], 'total_load_avg', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][2], 'zip_loads', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][1], 'zip_loads', base_case, None],
        #     # ['house', DSO_Houses['DSO_' + dso_num][1], 'total_load_avg', base_case, None]
        #     ['water_heater_agent', 'mean', 'temperature_setpoint', base_case, trans_case],
        #     ['water_heater_agent', 'sum', 'RT_quantity', base_case, None],
        #     ['water_heater_agent', 'sum', 'DA_quantity', base_case, None],
        #     ['hvac_agent', 'sum', 'RT_bid_quantity', base_case, None],
        #     ['hvac_agent', 'sum', 'DA_bid_quantity', base_case, None],
        #     ['hvac_agent', 'mean', 'cleared_price', base_case, None],
        #     ['hvac_agent', 'mean', 'DA_price', base_case, None],
        #     ['hvac_agent', 'mean', 'DA_temp', base_case, None],
        #     ['hvac_agent', 'mean', 'cooling_setpoint', base_case, None],
            ['house', DSO_Houses['DSO_' + dso_num][0], 'air_temperature_setpoint_cooling', base_case, trans_case],
            ['house', DSO_Houses['DSO_' + dso_num][0], 'hvac_load_avg', base_case, trans_case],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][0], 'RT_bid_quantity', base_case, None],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][0], 'DA_bid_quantity', base_case, None],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][0], 'cleared_price', base_case, None],
            ['house', DSO_Houses['DSO_' + dso_num][1], 'air_temperature_setpoint_cooling', base_case, trans_case],
            ['house', DSO_Houses['DSO_' + dso_num][1], 'hvac_load_avg', base_case, trans_case],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][1], 'RT_bid_quantity', base_case, None],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][1], 'DA_bid_quantity', base_case, None],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][1], 'cleared_price', base_case, None],
            ['house', DSO_Houses['DSO_' + dso_num][2], 'air_temperature_setpoint_cooling', base_case, trans_case],
            ['house', DSO_Houses['DSO_' + dso_num][2], 'hvac_load_avg', base_case, trans_case],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][2], 'RT_bid_quantity', base_case, None],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][2], 'DA_bid_quantity', base_case, None],
            ['hvac_agent', DSO_Houses['DSO_' + dso_num][2], 'cleared_price', base_case, None]
        ]

        # params = [
        #     ['substation', None, 'real_power_avg', base_case, None],
        #     ['house', 'mean', 'air_temperature_avg', base_case, trans_case],
        #     ['house', 'mean', 'air_temperature_deviation_cooling', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'hvac_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][1], 'hvac_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][2], 'hvac_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][3], 'hvac_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'air_temperature_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][1], 'air_temperature_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][2], 'air_temperature_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][3], 'air_temperature_avg', base_case, trans_case],
        # #     # ['house', DSO_Houses['DSO_'+dso_num][2], 'hvac_load_avg', base_case, None],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'waterheater_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][1], 'waterheater_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][2], 'waterheater_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][3], 'waterheater_load_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][0], 'waterheater_temp_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][1], 'waterheater_temp_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][2], 'waterheater_temp_avg', base_case, trans_case],
        #     ['house', DSO_Houses['DSO_' + dso_num][3], 'waterheater_temp_avg', base_case, trans_case],
        #     ['billing_meter', DSO_meters[3], 'real_power_avg', base_case, trans_case]
            # ['inverter', 'sum', 'real_power_avg', trans_case, None],
            # ['battery_agent', 'mean', 'battery_soc', trans_case, None]
            # ['house', 'sum', 'waterheater_load_avg', base_case, trans_case],
            # ['house', 'sum', 'hvac_load_avg', base_case, trans_case]
        # ]

        # params = [
        #     ['evchargerdet', 'sum', 'charge_rate_avg', base_case, None],
        #     ['evchargerdet', 'mean', 'charge_rate_avg', base_case, None],
        #     ['evchargerdet', 'mean', 'battery_SOC_avg', base_case, None],
        #     ['inverter', 'sum', 'real_power_avg', base_case, None]
        # ]
        # params = [
        # ['battery_agent', 'sum', 'inverter_p_setpoint', trans_case, None],
        # ['battery_agent', 'mean', 'battery_soc', trans_case, None],
        # ['inverter', 'sum', 'real_power_avg', trans_case, None]
        # ]

        for para in params:
            daily_load_plots(dso=dso_num, system=para[0], subsystem=para[1], variable=para[2], day=day_num,
                             case=para[3], comp=para[4], agent_prefix=agent_prefix, gld_prefix=GLD_prefix)

    # 2--------------------- Load Duration Plots ------------------
    if LoadDurationPlots:
        para = ['substation', None, 'real_power_avg', base_case, None]

        load_duration_plot(dso=dso_num, system=para[0], subsystem=para[1], variable=para[2], day=day_num,
                         case=para[3], comp=para[4], agent_prefix=agent_prefix, gld_prefix=GLD_prefix)

    # 3-------------------  Comparison of parameter over multiple days (e.g. transformer loading) ---
    if DailySummaryPlots:
        # params = [
        #   #['substation', None, 'real_power_avg', base_case, None, 'max', False, metadata["transformer_MVA"]*1e6/100],
        #   ['substation', None, 'real_power_avg', base_case, trans_case, 'max', False, metadata["transformer_MVA"]*1e6/100],
        #   ['weather', None, 'temperature', base_case, None, 'max', False, None],
        #   #['house', 'max', 'air_temperature_avg', base_case, None, 'max', False, None],
        #   #['house', 'min', 'air_temperature_avg', base_case, None, 'min', False, None],
        #   ['house', 'R3_12_47_2_load_16_bldg_410_zone_all', 'total_load_avg', base_case, None, 'mean', False, None],
        #   ['house', 'R5_12_47_3_tn_209_hse_2', 'hvac_load_avg', base_case, None, 'max', False, None],
        #   ['billing_meter', 'R5_12_47_3_tn_209_mtr_2', 'real_power_avg', base_case, None, 'max', False, None]
        #     ]

        params = [
          ['substation', None, 'real_power_avg', base_case, trans_case, 'max', False, None]
          # ['retail_market', 'Retail_1', 'congestion_surcharge_RT', trans_case, None, 'max', False, None]
            ]

        for para in params:
            for dso in dso_range:
                dso_num2 = str(dso)
                daily_summary_plots(day_range=day_range, system=para[0], subsystem=para[1], variable=para[2], dso=dso_num2,
                                   case=para[3], comp=para[4], oper=para[5], diff=para[6], denom=para[7],
                                   agent_prefix=agent_prefix, gld_prefix=GLD_prefix)

    # 4------------------ Comparison of variable across DSOs for a single day (e.g. weather) ----------------------
    if PlotDSOComp:
        params = [
            # ['weather', None, 'temperature', base_case],
            # ['substation', None, 'real_power_avg', trans_case],
            # ['retail_market', 'Retail_1', 'congestion_surcharge_RT', trans_case],
            # ['dso_market', 'DSO_1', 'cleared_quantity_rt', trans_case],
            # ['dso_market', 'DSO_1', 'cleared_price_rt', trans_case]
            # ['retail_market', 'Retail_1', 'cleared_quantity_rt', trans_case],
            ['battery_agent', 'mean', 'battery_soc', trans_case],
            ['retail_market', 'Retail_1', 'cleared_price_rt', trans_case]
            # ['house', 'mean', 'air_temperature_deviation_cooling', trans_case]
        ]

        for para in params:
            dso_comparison_plot(dso_range=dso_range, system=para[0], subsystem=para[1], variable=para[2], day=day_num,
                            case=para[3], agent_prefix=agent_prefix, gld_prefix=GLD_prefix)

    # 5-----------------   HEAT MAPS  ---------------------------------
    if PlotHeatMaps:
        # list of systems, subsystems, and variables to be plotted.
        params = [
            #['weather', None, 'temperature'],
            #['substation', None, 'real_power_avg'],
            # ['house', 'R3_12_47_2_load_16_bldg_410_zone_all', 'total_load_avg'],
            # ['house', 'R3_12_47_2_load_16_bldg_410_zone_all', 'hvac_load_avg'],
            # ['house', DSO_Houses['DSO_'+dso_num][4], 'air_temperature_avg'],
            # ['house', DSO_Houses['DSO_' + dso_num][4], 'total_load_avg']
            ['house', 'mean', 'air_temperature_avg'],
            ['house', 'mean', 'total_load_avg']
            # ['house', DSO_Houses['DSO_'+dso_num][1], 'zip_loads'],
            # ['house', DSO_Houses['DSO_'+dso_num][2], 'zip_loads'],
            # # ['house', 'R5_12_47_3_tn_209_hse_2', 'hvac_load_avg'],
            # # ['billing_meter', 'R5_12_47_3_tn_209_mtr_2', 'real_power_avg'],
            # ['house', 'sum', 'hvac_load_avg'],
            # ['house', 'mean', 'zip_loads'],
            # # ['gen1', None, 'Pgen'],
            # # ['gen1', None, 'LMP_P'],
            # ['house', 'mean', 'air_temperature_avg']
            # # ['hvac_agent', 'Houses_A_hse_1', 'cooling_setpoint'],
            # # ['hvac_agent', 'mean', 'cooling_setpoint'],
            #['dso_market', 'DSO_1', 'cleared_price_rt'],
            #['dso_market', 'DSO_1', 'cleared_quantity_rt']
        ]

        for para in params:
            heatmap_plots(dso=dso_num, system=para[0], subsystem=para[1], variable=para[2], day_range=day_range,
                          case=base_case, agent_prefix=agent_prefix, gld_prefix=GLD_prefix)

    # 5b -----------------   Loss of Amenity Metric Calculation   ---------------------------------
    if amenity:
        calc_amenity = True
        file_name = 'Substation_' + dso_num + '_glm_dict.json'
        metadata = load_json(base_case + agent_prefix + dso_num, file_name)
        if calc_amenity:
            for i in range(len(month_def)):
                tic()
                amenity_df = amenity_loss(metadata, month_def[i][1], '\\Substation_', dso_num,
                                          range(month_def[i][2], month_def[i][3]))
                print('Amenity calculation complete: DSO ' + str(dso_num) + ', Month ' + month_def[i][0])
                toc()

        annual_amenity_df = annual_amenity(metadata, month_def, GLD_prefix, dso_num)
        os.chdir(data_path)
        annual_amenity_df.to_hdf('amenity_dso_' + str(dso_num) + '_data.h5', key='amenity_data')
        annual_amenity_df.to_csv(path_or_buf=data_path + '\\amenity_dso_' + str(dso_num) + '_data.csv')

        annual_amenity_df.loc[annual_amenity_df['sum'].idxmax()]
        metadata['houses'][annual_amenity_df['sum'].idxmax()[0]]
        # year_energysum_df.to_hdf('energy_dso_' + str(dso_num) + '_data.h5', key='energy_sums')

    # 6-------------  Metadata histogram plots ------------
    # plots a histogram distribution of building metadata values
    if PlotPopDist:
        # list of systems, building classes, and variables to be plotted.
        params = [
            # ['houses', None, 'sqft'],
            # ['houses', None, 'cooling_COP'],
            # ['houses', None, 'over_sizing_factor'],
            # ['houses', None, 'thermal_mass_per_floor_area'],
            # ['houses', None, 'Rwall'],
            # ['houses', 'SINGLE_FAMILY', 'Rwall'],
            # ['houses', None, 'Rroof'],
            # ['houses', 'SINGLE_FAMILY', 'Rroof']
            # ['houses', 'SINGLE_FAMILY', 'Rwall']
            # ['houses', 'SINGLE_FAMILY', 'HVAC_deg-hrs'],
            # ['billingmeters', 'SINGLE_FAMILY', 'kw-hr'],
            # ['billingmeters', 'SINGLE_FAMILY', 'max_kw'],
            # ['billingmeters', 'SINGLE_FAMILY', 'avg_load'],
            # # ['billingmeters', 'SINGLE_FAMILY', 'load_factor'],
            # ['billingmeters', 'commercial', 'sqft'],
            # ['billingmeters', 'residential', 'sqft']
            ['billingmeters', 'residential', 'kw-hr'],
            ['billingmeters', 'residential', 'max_kw'],
            ['billingmeters', 'residential', 'avg_load'],
            ['billingmeters', 'residential', 'load_factor'],
            ['billingmeters', 'commercial', 'kw-hr'],
            ['billingmeters', 'commercial', 'max_kw'],
            ['billingmeters', 'commercial', 'avg_load'],
            ['billingmeters', 'commercial', 'load_factor']
            # ['billingmeters', 'MULTI_FAMILY', 'kw-hr'],
            # ['billingmeters', 'MULTI_FAMILY', 'max_kw'],
            # ['billingmeters', 'MULTI_FAMILY', 'avg_load'],
            # ['billingmeters', 'MULTI_FAMILY', 'load_factor'],
            # ['billingmeters', 'MOBILE_HOME', 'kw-hr'],
            # ['billingmeters', 'MOBILE_HOME', 'max_kw'],
            # ['billingmeters', 'MOBILE_HOME', 'avg_load'],
            # ['billingmeters', 'MOBILE_HOME', 'load_factor'],
            # ['billingmeters', None, 'kw-hr'],
            # ['billingmeters', None, 'max_kw'],
            # ['billingmeters', None, 'avg_load'],
            # ['billingmeters', None, 'load_factor']
            #['billingmeters', None, 'bill']
        ]

        for para in params:
            metadata_dist_plots(system=para[0], sys_class=para[1], variable=para[2], dso_range=dso_range,
                          case=base_case, agent_prefix=agent_prefix)

    # 7-------------  Outlier check  --------------------
    if OutLierCheck:
        params = [
            ['house', 'air_temperature_avg', 78 , 68],
            ['weather', 'temperature', 120, 0],
            #['dso_market', 'cleared_price_rt', 0.1, 0.04],
            #['retail_market', 'cleared_price_rt', 0.1, 0.04],
            ['billing_meter', 'above_RangeA_Count', 0.01, -1e-6],
            ['substation', 'real_power_max', 2e6, 0.1e6],
            ['substation', 'real_power_losses_max', 0.2e6, 0],
            # ['hvac_agent', 'room_air_temperature', 85, 55]
        ]

        log_list = []

        for para in params:
            log_list = limit_check(log_list, dso_num, para[0], para[1], day_range, base_case, agent_prefix, GLD_prefix,
                                   para[2], para[3])

        # Save log file
        os.chdir(base_case + agent_prefix + dso_num)
        with open('DSO' + dso_num + '_exception_log.txt', 'w') as f:
            for item in log_list:
                f.write("%s\n" % item)

    # 7b-------------  Check consistency between two house populations  --------------------
    if HouseCheck:
        params = ['over_sizing_factor', 'sqft', 'wh_gallons', 'Rroof', 'Rwall',
                  'thermal_mass_per_floor_area', 'cooling_COP', 'heating_setpoint', 'cooling_setpoint', 'wh_setpoint']
        house_check(dso_range, base_case, trans_case, params)


    # 8------------  PLOT TSO GENERATION AND AMES DATA
    if gen_plots:

        generation_load_profiles(base_case, metadata_path, data_path, day_range, True)

        generation_load_profiles(base_case, metadata_path, data_path, day_range, False)

        GenAMES_df = generation_statistics(base_case, config_path, case_config_name, day_range, False)

        GenPYPower_df = generation_statistics(base_case, config_path, case_config_name, day_range, True)


# ------------
    if transmission_plots:
        # sim_results = False
        # trans_df = transmission_statistics(dso_meta_file, case_config_file, data_path, day_range, sim_results)

        # ercot_df = load_ercot_data(metadata_file, base_case, day_range)
        # ercot_sum = ercot_df.loc[:, ercot_df.columns[ercot_df.columns.str.contains('Bus')]].sum(
        #     axis=1)
        gen_df = load_gen_data(base_case, 'gen', day_range)
        # gen_sum = gen_df.groupby(level=0)['Pgen'].sum()

        # transmission_loss = (gen_sum - ercot_sum) / gen_sum
        # transmission_loss.plot()

        # Load Transmission Line Data
        case_config = load_json(config_path, case_config_file)
        realtime = False
        if realtime:
            rt_line_data_df = load_gen_data(base_case, 'rt_line', day_range)
            test_data_df = rt_line_data_df.unstack(level=1)
            test_data_df.columns = test_data_df.columns.droplevel()
            test_data_df.columns = test_data_df.columns.str.replace("rt_line", "line")
        else:
            da_line_data_df = load_gen_data(base_case, 'da_line', day_range)
            test_data_df = da_line_data_df.unstack(level=1)
            test_data_df.columns = test_data_df.columns.droplevel()
            test_data_df.columns = test_data_df.columns.str.replace("da_line", "line")

        line_cols = [col for col in test_data_df.columns if 'line' in col]
        for col in line_cols:
            test_data_df[col] = pd.to_numeric(test_data_df[col])
        fig = test_data_df.plot()
        # fig.title('Fraction of Loading on each Transmission Line')

        # plot_filename = datetime.now().strftime(
        #     '%Y%m%d') + 'transmission_profile.png'
        # file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        # fig.savefig(file_path_fig, bbox_inches='tight')

        if len(case_config['bus']) > 200:
            bus_num = 200
        else:
            bus_num = 8

        for node in range(1,bus_num+1):
            # Todo: need to remove this once indexes are fixed.
            if realtime:
                id = 0
            else:
                id = -1
            linecap_count = 0
            test_data_df['nodeabs' + str(node)] = np.zeros_like(test_data_df[line_cols[0]])
            test_data_df['nodeabnorm' + str(node)] = np.zeros_like(test_data_df[line_cols[0]])
            for branch in case_config['branch']:
                id += 1
                if branch[0] == node:
                    test_data_df['nodeabs'+str(node)] += -test_data_df['line'+str(id-1)] * branch[5]
                    test_data_df['nodeabnorm' + str(node)] += test_data_df['line' + str(id)].abs() * branch[5]
                    linecap_count += branch[5]
                elif branch[1] == node:
                    test_data_df['nodeabs' + str(node)] += test_data_df['line' + str(id)] * branch[5]
                    test_data_df['nodeabnorm' + str(node)] += test_data_df['line' + str(id)].abs() * branch[5]
                    linecap_count += branch[5]
            test_data_df['nodenorm' + str(node)] = test_data_df['nodeabs' + str(node)] / linecap_count
            test_data_df['nodeabnorm' + str(node)] = test_data_df['nodeabnorm' + str(node)] / linecap_count

        nodeabs_cols = [col for col in test_data_df.columns if 'nodeabs' in col]
        test_data_df['Node_sum'] = test_data_df[nodeabs_cols].sum(axis=1)

        # fig = test_data_df[nodeabs_cols].plot()
        # fig = test_data_df[[col for col in test_data_df.columns if 'nodenorm' in col]].plot()
        # fig = test_data_df[[col for col in test_data_df.columns if 'nodeabnorm' in col]].plot()
        if realtime:
            market = 'realtime'
            lmp_df = load_ames_data(base_case, day_range)
        else:
            market = 'day_ahead'
            da_lmp_data_df = load_gen_data(base_case, 'da_lmp', day_range)
            lmp_df = da_lmp_data_df.unstack(level=1)
            # test_data_df.columns = test_data_df.columns.str.replace("da_line", "line")
            lmp_df.columns = lmp_df.columns.droplevel()
            lmp_df.columns = lmp_df.columns.str.replace("da_lmp", " LMP")
        # Plot key subplots together and save to file (this time including wind power)
        # fig = plt.figure()
        # ax1 = fig.add_subplot(311)
        # ax2 = fig.add_subplot(312)
        # ax3 = fig.add_subplot(313)
        # lmp_cols = [col for col in ames_df.columns if 'LMP' in col]
        # test_data_df[line_cols].plot(ax=ax1)
        # test_data_df[[col for col in test_data_df.columns if 'nodenorm' in col]].plot(ax=ax2)
        # ames_df[lmp_cols].plot(ax=ax3)
        #
        # plot_filename = datetime.now().strftime(
        #     '%Y%m%d') + '_Transmission.png'
        # file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        # fig.savefig(file_path_fig, bbox_inches='tight')

        fig, axes = plt.subplots(3, 1, sharex=False, figsize=(11, 10))
        for line in line_cols:
            axes[0].plot(test_data_df[line].abs(), label=line.replace('rt_line',''),
                        linestyle='-', alpha=0.8)
        axes[0].set_title('Normalized Line Capacity')
        # axes[0].legend(loc='upper left', fontsize=8, title = 'Line ID')
        axes[0].set_ylabel('Line Capacity (-)')
        axes[0].set_xticks([])

        node_col = [col for col in test_data_df.columns if 'nodenorm' in col]
        for node in node_col:
            axes[1].plot(test_data_df[node], label=node.replace('nodenorm',''),
                            # label=[col for col in test_data_df.columns if 'nodenorm' in col], marker='o',
                            linestyle='-', alpha=0.8)
        axes[1].set_title('Normalized Net Load Imports')
        # axes[1].legend(loc='upper left', fontsize=8, title='Bus ID')
        axes[1].set_ylabel('Net Imports (-)')
        axes[1].set_xticks([])

        LMP_col = [col for col in lmp_df.columns if 'LMP' in col]
        for LMP in LMP_col:
            axes[2].plot(lmp_df[LMP], label=LMP.replace(' LMP',''),
                            # label=[col for col in test_data_df.columns if 'nodenorm' in col], marker='o',
                            linestyle='-', alpha=0.8)
        axes[2].set_title('Bus Localized Margin Price')
        # axes[2].legend(loc='upper left', fontsize=8, title='Bus ID')
        axes[2].set_ylabel('LMP ($/MW-hr)')
        axes[2].set_xlabel('Time')

        plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_Transmission_master_plot_' + market + '.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        fig.savefig(file_path_fig, bbox_inches='tight')

        #  ---- OLD LMP versus load plots

        # Load AMES data
        ames_df = load_ames_data(base_case, day_range)

        ames_df['load_imbalance'] = ames_df[' TotalGen'] - ames_df[' TotalLoad']
        wind_list = [col for col in ames_df.columns if 'wind' in col]
        ames_df['total_wind'] = ames_df[wind_list].sum(axis=1)
        ames_df['wind_percent'] = 100 * ames_df['total_wind'] / ames_df[' TotalGen']

        # Plot key subplots together and save to file.
        fig = plt.figure()
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)
        lmp_cols = [col for col in ames_df.columns if 'LMP' in col]
        ames_df[lmp_cols].plot(ax=ax1)
        ames_df[[' TotalLoad', ' TotalGen']].plot(ax=ax2)
        ames_df[['load_imbalance']].plot(ax=ax3)

        plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_TSO_LMP_and_load_profile.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        fig.savefig(file_path_fig, bbox_inches='tight')

        # Plot key subplots together and save to file (this time including wind power)
        fig = plt.figure()
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)
        lmp_cols = [col for col in ames_df.columns if 'LMP' in col]
        ames_df[lmp_cols].plot(ax=ax1)
        ames_df[['total_wind']].plot(ax=ax2)
        ames_df[['load_imbalance']].plot(ax=ax3)

        plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_TSO_LMP_and_wind_profile.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        fig.savefig(file_path_fig, bbox_inches='tight')

        # fig = plt.figure()
        # ax = plt.gca()
        # ax.scatter(ames_df['load_imbalance'].abs(), ames_df[' LMP1'].abs(), c='blue', alpha=0.05, edgecolors='none')
        # ax.set_yscale('log')
        # ax.set_xscale('log')

        # Calculate total generation by fuel class, plot and save to file.
        all_gen = []
        for fuel in ['wind', 'gas', 'coal', 'nuc', 'solar']:
            if any(fuel in s for s in ames_df.columns.tolist()):
                gen_cols = [col for col in ames_df.columns if fuel in col]
                fig = ames_df[gen_cols].plot()
                all_gen += gen_cols
                plot_filename = datetime.now().strftime(
                    '%Y%m%d') + '_' + fuel + '_load_profile.png'
                file_path_fig = os.path.join(data_path, 'plots', plot_filename)
                plt.savefig(file_path_fig, bbox_inches='tight')

        #  Plot % of wind generation as fraction of total load
        fig = plt.figure()
        ames_df['wind_percent'].plot()

        ave_percent = ames_df['wind_percent'].mean()
        fig.suptitle('Wind Generation Penetration (%): Average = ' + str(int(ave_percent)))
        plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_wind_gen_percent.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        #  Power generation load duration curve
        LDC_case_data = ames_df['total_wind'].values.tolist()
        LDC_case_data.sort(reverse=False)
        load_case_data = np.array(LDC_case_data)

        l = len(load_case_data)
        index = np.array(range(0, l)) * 100 / l

        plt.clf()
        plt.plot(index, load_case_data, label='wind')
        plt.legend()

        plt.title('Duration vs. Load')
        plt.xlabel('Duration (%)', size=12)
        plt.xlim(0, 100)
        plt.ylabel('Wind Power', size=12)
        plt.grid(b=True, which='major', color='k', linestyle='-')
        plt.minorticks_on()

        plot_filename = datetime.now().strftime(
            '%Y%m%d') + 'Wind_power_ Load_Duration_Curve_.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

    # 8b-----------  LMP Plots
    if LMP_check:
        # Representative Houston Price Profile
        place_names = ['CPS', 'North', 'South', 'West', 'Houston']
        place = place_names[4]

        # Load in data from h5 dataframe (Load = True) or csv (False)
        load = True
        if load:
            store = h5py.File(data_path+'\\ERCOT_LMP.h5')
            list(store.keys())

            DAdailypricerange = pd.read_hdf(data_path+'\\ERCOT_LMP.h5', key='DADeltaLMP_data', mode='r')
            RTdailypricerange = pd.read_hdf(data_path + '\\ERCOT_LMP.h5', key='RTDeltaLMP_data', mode='r')
            DAPrices = pd.read_hdf(data_path + '\\ERCOT_LMP.h5', key='DALMP_data', mode='r')
            RTPrices = pd.read_hdf(data_path + '\\ERCOT_LMP.h5', key='RTLMP_data', mode='r')
        else:
            load_wind_data = pd.read_excel(data_path + '\\ERCOT_Hourly_Wind_2016.xlsx', sheet_name='numbers',
                                           usecols=['Total Wind Output, MW'])
            for scenario in ['RT', 'DA']:
                if scenario == 'DA':
                    prices_data = pd.read_excel(data_path + '\\DAM_2016.xlsx', sheet_name=place)
                else:
                    prices_data = pd.read_excel(data_path + '\\RTM_2016.xlsx', sheet_name=place)
                prices_data = prices_data.rename(columns={'Settlement Point Price': place+' $_mwh'})

                if scenario == 'DA':
                    date_rng = pd.date_range(start='1/1/2016', end='31/12/2016 23:00:00', freq='H')
                else:
                    date_rng = pd.date_range(start='1/1/2016-01-01 00:00:00', periods=len(prices_data), freq='15min')
                prices_data['Date'] = pd.to_datetime(date_rng)
                prices_data = prices_data.set_index('Date')
                if scenario == 'RT':
                    prices_data = prices_data.groupby(pd.Grouper(freq='H')).mean()
                prices_data['Year'] = prices_data.index.year
                prices_data['Month'] = prices_data.index.month
                prices_data['Week'] = prices_data.index.week
                prices_data['Day'] = prices_data.index.weekday_name
                prices_data['Hour'] = prices_data.index.hour
                temp = pd.read_csv(data_path+'\\2016_ERCOT_Hourly_Load_Data.csv', usecols=['ERCOT'])
                prices_data['ERCOT Load'] = temp['ERCOT'].tolist()
                prices_data['Wind Load'] = load_wind_data['Total Wind Output, MW'].tolist()
                prices_data['ERCOT Net Load'] = prices_data['ERCOT Load'] - prices_data['Wind Load']
                dailypricerange = pd.Series.to_frame(prices_data[place+' $_mwh'].groupby(pd.Grouper(freq='D')).max()
                                                     - prices_data[place+' $_mwh'].groupby(pd.Grouper(freq='D')).min())
                dailypricerange['Month'] = dailypricerange.index.month
                dailypricerange['ERCOT Load'] = pd.Series.to_frame(prices_data['ERCOT Load'].groupby(pd.Grouper(freq='D')).max())
                dailypricerange['ERCOT Net Load'] = pd.Series.to_frame(prices_data['ERCOT Net Load'].groupby(pd.Grouper(freq='D')).max())
                dailypricerange['ERCOT Daily High LMP'] = pd.Series.to_frame(prices_data[place+' $_mwh'].groupby(pd.Grouper(freq='D')).max())
                dailypricerange['ERCOT Daily Low LMP'] = pd.Series.to_frame(prices_data[place+' $_mwh'].groupby(pd.Grouper(freq='D')).min())
                dailypricerange['ERCOT Delta'] = pd.Series.to_frame(prices_data['ERCOT Load'].groupby(pd.Grouper(freq='D')).max()
                                                     - prices_data['ERCOT Load'].groupby(pd.Grouper(freq='D')).min())
                dailypricerange['ERCOT Net Delta'] = pd.Series.to_frame(prices_data['ERCOT Net Load'].groupby(pd.Grouper(freq='D')).max()
                                                     - prices_data['ERCOT Net Load'].groupby(pd.Grouper(freq='D')).min())

                os.chdir(data_path)
                dailypricerange.to_hdf('ERCOT_LMP.h5', key=scenario+'DeltaLMP_data')
                prices_data.to_hdf('ERCOT_LMP.h5', key=scenario+'LMP_data')
                dailypricerange.to_csv(path_or_buf=data_path + '\LMP_DailyRange'+place+'.csv')
                prices_data.to_csv(path_or_buf=data_path + '\LMP_Data'+place+'.csv')
                if scenario == 'DA':
                    DAdailypricerange = dailypricerange
                    DAPrices = prices_data
                elif scenario == 'RT':
                    RTdailypricerange = dailypricerange
                    RTPrices = prices_data

                    # Generate Box Plots for entire year.
        for scenario in ['RT', 'DA']:
            if scenario == 'DA':
                dailypricerange = DAdailypricerange
                prices_data = DAPrices
            elif scenario == 'RT':
                dailypricerange = RTdailypricerange
                prices_data = RTPrices

            fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)

            name = place + ' $_mwh'
            sns.boxplot(data=prices_data, x='Month', y=name, ax=axes[0])
            axes[0].set_ylabel('$/mw-hr')
            axes[0].set_title(place + ' ' + scenario + ' LMP')
            axes[0].set_xlabel('')

            sns.boxplot(data=dailypricerange, x='Month', y=name, ax=axes[1])
            axes[1].set_ylabel('$/mw-hr')
            axes[1].set_title(place + ' ' + scenario + ' daily max variation in LMP')
            axes[1].set_xlabel('')

            name = 'ERCOT Load'
            sns.boxplot(data=prices_data, x='Month', y=name, ax=axes[2])
            axes[2].set_ylabel('MW')
            axes[2].set_title('ERCOT hourly load')
            axes[2].set_xlabel('')

            name = 'ERCOT Delta'
            sns.boxplot(data=dailypricerange, x='Month', y=name, ax=axes[3])
            axes[3].set_ylabel('MW')
            axes[3].set_title('Daily max variation in ERCOT hourly load')

            plot_filename = datetime.now().strftime(
                '%Y%m%d') + 'ERCOT_' + scenario + '_'+place+'_LMP_Annual_Box_Plots.png'
            file_path_fig = os.path.join(data_path, 'plots', plot_filename)
            plt.savefig(file_path_fig, bbox_inches='tight')

            #  Power generation load duration curve
            DeltaLDC_data = dailypricerange[place+' $_mwh'].values.tolist()
            DeltaLDC_data.sort(reverse=False)
            DeltaLDC_data = np.array(DeltaLDC_data)

            LMPHighLDC_data = dailypricerange['ERCOT Daily High LMP'].values.tolist()
            LMPHighLDC_data.sort(reverse=False)
            LMPHighLDC_data = np.array(LMPHighLDC_data)

            LMPLowLDC_data = dailypricerange['ERCOT Daily Low LMP'].values.tolist()
            LMPLowLDC_data.sort(reverse=False)
            LMPLowLDC_data = np.array(LMPLowLDC_data)

            l = len(DeltaLDC_data)
            index_day = np.array(range(0, l)) * 100 / l

            PriceLDC_data = prices_data[place+' $_mwh'].values.tolist()
            PriceLDC_data.sort(reverse=False)
            PriceLDC_data = np.array(PriceLDC_data)

            if scenario == 'DA':
                DAPriceLDC = PriceLDC_data
                DADeltaLDC = DeltaLDC_data
                DAHighLDC = LMPHighLDC_data
                DALowLDC = LMPLowLDC_data
                l = len(DAPriceLDC)
                index_hr = np.array(range(0, l)) * 100 / l
            elif scenario == 'RT':
                RTPriceLDC = PriceLDC_data
                RTDeltaLDC = DeltaLDC_data
                RTHighLDC = LMPHighLDC_data
                RTLowLDC = LMPLowLDC_data
                l = len(RTPriceLDC)
                index_15min = np.array(range(0, l)) * 100 / l

        plt.clf()
        plt.plot(index_day, RTDeltaLDC, label='RT Delta LMP')
        plt.plot(index_15min, RTPriceLDC, label='RT LMP')
        plt.plot(index_day, DADeltaLDC, label='DA Delta LMP')
        plt.plot(index_hr, DAPriceLDC, label='DA LMP')
        plt.plot(index_day, RTHighLDC, label='RT Daily High LMP')
        plt.plot(index_day, RTLowLDC, label='RT Daily Low LMP')
        plt.plot(index_day, DAHighLDC, label='DA Daily High LMP')
        plt.plot(index_day, DALowLDC, label='DA Daily Low LMP')
        plt.legend()

        plt.title('Duration vs. LMP')
        plt.xlabel('Duration (%)', size=12)
        plt.xlim(0, 100)
        plt.ylabel('$/Mw-hr', size=12)
        plt.yscale('log')
        plt.grid(b=True, which='both', color='k', linestyle=':')
        plt.minorticks_on()

        plot_filename = datetime.now().strftime(
            '%Y%m%d') + 'ERCOT_'+place+'LMP_Duration_Curve.png'
        file_path_fig = os.path.join(data_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        ames_df = load_ames_data(base_case, day_range)
        ames_df['Net Load'] = ames_df[' TotalGen'] - ames_df[' TotalWindGen']
        da_lmp_data_df = load_gen_data(base_case, 'da_lmp', day_range)
        ames_df['DA LMP1'] = da_lmp_data_df.xs('da_lmp1', level=1)['LMP']

        ercot_df = load_ercot_data(metadata_file, base_case, day_range)
        # ames_df = ames_df.set_index(ercot_df.index)

        AMESdailypricerange = pd.Series.to_frame(ames_df[' LMP1'].groupby(pd.Grouper(freq='D')).max()
                                             - ames_df[' LMP1'].groupby(pd.Grouper(freq='D')).min())
        AMESdailypricerange['DA LMP1'] = pd.Series.to_frame(ames_df['DA LMP1'].groupby(pd.Grouper(freq='D')).max()
                                             - ames_df['DA LMP1'].groupby(pd.Grouper(freq='D')).min())
        AMESdailypricerange['ERCOT Load'] = pd.Series.to_frame(
            ames_df[' TotalGen'].groupby(pd.Grouper(freq='D')).max())
        AMESdailypricerange['Net Load'] = pd.Series.to_frame(
            ames_df['Net Load'].groupby(pd.Grouper(freq='D')).max())
        AMESdailypricerange['ERCOT Daily High LMP'] = pd.Series.to_frame(
            ames_df[' LMP1'].groupby(pd.Grouper(freq='D')).max())
        AMESdailypricerange['ERCOT Daily Low LMP'] = pd.Series.to_frame(
            ames_df[' LMP1'].groupby(pd.Grouper(freq='D')).min())
        AMESdailypricerange['ERCOT Delta'] = pd.Series.to_frame(
            ames_df[' TotalGen'].groupby(pd.Grouper(freq='D')).max()
            - ames_df[' TotalGen'].groupby(pd.Grouper(freq='D')).min())
        AMESdailypricerange['ERCOT Net Delta'] = pd.Series.to_frame(
            ames_df['Net Load'].groupby(pd.Grouper(freq='D')).max()
            - ames_df['Net Load'].groupby(pd.Grouper(freq='D')).min())

        # Gen_Cap = [2708.6, 5138.6, 6146.6, 6769, 7955.8, 9805.6, 12901.6, 12976.6, 13571.6, 13981.6, 14135.5, 15637.6, 16217.7, 22996.7, 23046.8, 23613.3, 25464.1, 26014.1, 29016.8, 29736.8, 32754.2, 34006.3, 35179.8, 35259.8, 37285.8, 38225.5, 40370.1, 41976.5, 42430, 44809.6, 46161.9, 47895.9, 48559.5, 50935.5, 53672.3, 55362.3, 55592.3, 56395.5, 57466.5, 58406.1, 60109.3, 61145.3, 62519.2, 63376.6, 63942.2, 65303.2, 66110.2, 66528.2, 67203.8, 67746.6, 67851.6, 68555, 68756.6, 70011.9, 72849.5, 72934.2, 72959.4, 75126.4, 75492.4, 75495.9, 75561.9, 75688.4, 75927.7, 75938.1, 76290.1, 76924.8, 78197.3, 78820.3, 79193.4, 80979.4, 81705.4, 81706.7, 81931.1, 81982.1, 81983.9, 81985.9]
        # Gen_LMPs = [7.155692159, 9.00297388, 15.82181007, 15.85026954, 15.85040038, 15.87024826, 16.52386515, 17.20002418, 17.2544183, 17.33679828, 17.4774944, 17.51585639, 17.52950998, 17.58267489, 17.85838609, 17.92369001, 17.98188442, 18.22532277, 18.23530996, 18.26098281, 18.52136604, 18.53626463, 18.55649184, 18.8597636, 18.88324771, 19.04915706, 19.14144303, 19.32117974, 19.48545838, 19.5958867, 20.08008232, 20.20531811, 20.2340118, 20.25432841, 20.40425686, 20.4129046, 20.43168712, 20.65397474, 20.73889624, 20.82747566, 21.12669256, 21.20945639, 21.24346855, 21.29345272, 21.31401001, 21.37852646, 21.48519681, 21.72858787, 22.28478885, 23.60566742, 23.88314149, 24.82137515, 25.30480033, 25.43372114, 25.52631423, 25.77557274, 26.67151067, 26.79184778, 26.96761661, 27.52584023, 27.89575108, 28.01158277, 28.75092274, 28.81303841, 29.4479482, 29.46830692, 29.73170395, 29.83355014, 29.92687798, 29.98868254, 30.43219404, 31.21024454, 31.75159778, 31.82680377, 32.22496, 32.6615139]

        Gen_Cap = [2430, 5138.6, 5592.1, 7968.1, 10704.9, 12394.9, 14244.7, 15431.5, 15841.5, 16463.9, 19559.9, 20279.9, 22424.5, 23676.6, 24684.6, 27064.2, 27218.1, 27293.1, 27373.1, 28734.1, 29805.1, 31157.4, 32659.5, 39438.5, 42441.2, 43380.9, 44987.3, 45037.4, 45587.4, 46527, 48261, 49434.5, 49800.5, 52638.1, 53233.1, 53317.8, 54121, 54687.5, 57704.9, 58740.9, 59547.9, 59777.9, 60441.5, 61007.1, 61864.5, 61969.5, 62171.1, 63874.3, 65900.3, 66318.3, 67044.3, 67417.4, 68791.3, 70577.3, 71252.9, 71833, 73683.8, 73687.3, 73753.3, 73977.7, 74612.4, 75235.4, 76490.7, 76842.7, 77385.5, 79552.5, 80825, 80827, 80837.4, 80862.6, 81566, 81692.5, 81694.3, 81933.6, 81984.6, 81985.9, 81933.6, 81984.6, 81985.9]
        Gen_LMPs = [8, 8, 10.94649052, 11.10393486, 11.18359907, 11.33275093, 11.8815071, 11.96806204, 12.12443527, 12.4303639, 12.9632542, 13.45769631, 13.88030294, 14.5785095, 14.72548203, 15.28432416, 16.81358459, 16.94767103, 17.24026386, 20.46574144, 21.78650812, 22.01409766, 23.94648992, 24.82077912, 26.34739007, 30.62034472, 30.78489477, 33.81384953, 33.82292221, 35.75003439, 36.29330568, 41.25270825, 42.02540054, 42.05994295, 42.80526699, 42.99620505, 44.65187353, 44.93284321, 45.04445407, 45.69359611, 45.8450914, 45.8492972, 47.27365244, 47.290314, 48.5703895, 49.2555182, 51.90450546, 53.46000596, 55.09083853, 56.11431955, 56.16984711, 56.36279423, 56.88211002, 57.48155677, 57.71455183, 59.03419197, 59.15989554, 61.50500235, 62.06553725, 64.27404519, 68.15610661, 68.7630067, 69.80960794, 71.45968432, 72.35129645, 72.41267171, 72.48144516, 75.6021543, 76.42675284, 76.79521665, 77.12879643, 77.20610957, 77.53529416, 79.40644793, 82.79703643, 82.83815342, 58.13515835, 60.44762914, 60.48052274]

        #Create scatter plots:
        # month_list = ['2016-01', '2016-02', '2016-03', '2016-04', '2016-05', '2016-06', '2016-07', '2016-08', '2016-09',
        #               '2016-10', '2016-11', '2016-12']
        month_list = ['2016-08']
        for month_to_plot in month_list:
            date = datetime.strptime(month_to_plot, "%Y-%m")
            month = datetime.date(date).strftime('%B')
            fig, axes = plt.subplots(3, 1, sharex=False, figsize=(11, 10))
            axes[0].scatter(DAdailypricerange.loc[month_to_plot, 'ERCOT Net Load'],
                            DAdailypricerange.loc[month_to_plot, place+' $_mwh'], label='DA LMP Daily Change vs Daily Max Net Load', marker='o',
                            linestyle='-', alpha=0.8)
            axes[0].scatter(RTdailypricerange.loc[month_to_plot, 'ERCOT Net Load'],
                            RTdailypricerange.loc[month_to_plot, place+' $_mwh'], label='RT LMP Daily Change vs Daily Max Net Load', marker='o',
                            linestyle='-', alpha=0.5)
            axes[0].scatter(AMESdailypricerange.loc[:, 'Net Load'],
                            AMESdailypricerange.loc[:, ' LMP1'], label='AMES RT LMP Daily Change vs Daily Max Net Load', marker='o',
                            linestyle='-', alpha=0.5)
            axes[0].scatter(AMESdailypricerange.loc[:, 'Net Load'],
                            AMESdailypricerange.loc[:, 'DA LMP1'], label='AMES DA LMP Daily Change vs Daily Max Net Load', marker='o',
                            linestyle='-', alpha=0.5)
            axes[0].set_title(month + ' - LMP:' + place)
            axes[0].legend(loc='upper left', fontsize=8)
            axes[0].set_ylabel('$/MW-hr')

            axes[0].set_ylim(top=60, bottom=0)
            axes[1].scatter(DAPrices.loc[month_to_plot, 'ERCOT Net Load'],
                            DAPrices.loc[month_to_plot, place+' $_mwh'], label='DA LMP vs Net Load', marker='o',
                            linestyle='-', alpha=0.8)
            axes[1].scatter(RTPrices.loc[month_to_plot, 'ERCOT Net Load'],
                            RTPrices.loc[month_to_plot, place+' $_mwh'], label='RT LMP vs Net Load', marker='o',
                            linestyle='-', alpha=0.5)
            axes[1].scatter(ames_df.loc[:, 'Net Load'],
                            ames_df.loc[:, ' LMP1'], label='AMES RT LMP vs Net Load', marker='o',
                            linestyle='-', alpha=0.5)
            axes[1].scatter(ames_df.loc[:, 'Net Load'],
                            ames_df.loc[:, 'DA LMP1'], label='AMES DA LMP vs Net Load', marker='o',
                            linestyle='-', alpha=0.5)
            axes[1].scatter(Gen_Cap,
                            Gen_LMPs, label='(Revised) Fuel LMP vs Net Load', marker='o',
                            linestyle='-', alpha=0.5)
            #axes[1].set_title(month + ' - Daily Delta Load')
            axes[1].legend(loc='upper left', fontsize=8)
            axes[1].set_ylabel('$/MW-hr')
            axes[1].set_ylim(top=60, bottom=0)
            #axes[2].set_yscale('log')
            axes[2].plot(DAPrices.loc[month_to_plot, [place+' $_mwh']], label='DA LMP', marker='o',
                            linestyle='-', alpha=0.8)
            axes[2].plot(RTPrices.loc[month_to_plot, [place+' $_mwh']], label='RT LMP', marker='o',
                            linestyle='-', alpha=0.5)
            axes[2].plot(ames_df.loc[:, [' LMP1']], label='AMES RT LMP', marker='o',
                       linestyle='-', alpha=0.5)
            axes[2].plot(ames_df.loc[:, ['DA LMP1']], label='AMES DA LMP', marker='o',
                       linestyle='-', alpha=0.5)
            axes2 = axes[2].twinx()
            axes2.plot(RTPrices.loc[month_to_plot, ['ERCOT Net Load']], label='ERCOT Net Load (MW)', marker='',
                         linestyle='-', alpha=0.5)
            axes2.set_ylabel('MW')

            #axes[2].set_title(month + ' - Daily Delta Load')
            axes[2].legend(loc='upper left', fontsize=8)
            axes[2].set_ylabel('$/MW-hr')

            plot_filename = datetime.now().strftime(
                '%Y%m%d') + ' ' + place + '_ERCOT_LMP_' + month + '.png'
            file_path_fig = os.path.join(data_path, 'plots', plot_filename)
            fig.savefig(file_path_fig, bbox_inches='tight')

            # ------ Plot of just LMPs versus net load  -------------

            plt.figure(figsize=(11, 10))
            plt.scatter(DAPrices.loc[month_to_plot, 'ERCOT Net Load'],
                            DAPrices.loc[month_to_plot, place + ' $_mwh'], label='ERCOT DA LMP', marker='o',
                            linestyle='-', alpha=0.8)
            plt.scatter(RTPrices.loc[month_to_plot, 'ERCOT Net Load'],
                            RTPrices.loc[month_to_plot, place + ' $_mwh'], label='ERCOT RT LMP', marker='o',
                            linestyle='-', alpha=0.5)
            plt.scatter(ames_df.loc[:, 'Net Load'],
                            ames_df.loc[:, ' LMP1'], label='AMES RT LMP', marker='o',
                            linestyle='-', alpha=0.5)
            plt.scatter(ames_df.loc[:, 'Net Load'],
                            ames_df.loc[:, 'DA LMP1'], label='AMES DA LMP', marker='o',
                            linestyle='-', alpha=0.5)
            # axes[1].set_title(month + ' - Daily Delta Load')
            plt.legend(loc='upper left', fontsize=17)
            plt.ylabel('$/MW-hr', size = 17)
            plt.xlabel('Net Load (MW)', size=17)
            plt.ylim(top=80, bottom=0)
            ax = plt.gca()
            ax.tick_params(axis='both', which='major', labelsize=17)

            plot_filename = datetime.now().strftime(
                '%Y%m%d') + ' ' + place + '_ERCOT_LMP_vs_netload' + month + '.png'
            file_path_fig = os.path.join(data_path, 'plots', plot_filename)
            plt.savefig(file_path_fig, bbox_inches='tight')


        # Create HeatMaps

        # axes = dailypricerange.plot(marker='.', alpha=0.5, linestyle='None', figsize=(11, 9),
        #                                            subplots=True)



        # prices_data = prices_data[~prices_data.index.duplicated(keep='first')]
        # # indices = load_wind_data.index
        # # d = {'Monday': 1, 'Tuesday': 1, 'Wednesday': 1, 'Thursday': 1, 'Friday': 1, 'Saturday': -1, 'Sunday': -1}
        # # prices_data_houston = prices_data_houston.replace(d)
        # prices_data_houston.head(5)
        #
        # cols_plot = [place+' $_kwh' for place in place_names]
        # #labels = col
        # axes = prices_data[cols_plot].plot(marker='.', alpha=0.5, linestyle='None', figsize=(11, 9),
        #                                            subplots=True)

    # 9-------------  Plot specific DSO plots ------------
    # plots a DSO-TSO curves - work in progress.
    if dso_plots:
        # Check population and ratios of Res Comm, and Indust customers and loads.
        # Bill = True if rate case has been run and energy df and bill df have been saved.
        bill = False
        rci_df = RCI_analysis(dso_range, base_case, data_path, metadata_path, dso_meta_file, bill)

        dso_forecast_stats(dso_range, day_range, base_case, dso_meta_file, metadata_path)

        der_load_stack(dso_range, day_range, base_case, agent_prefix, GLD_prefix, dso_meta_file, metadata_path)

        der_stack_plot(day_range, metadata_path, base_case)

        for day in day_range:
            dso_market_plot(dso_range, str(day), base_case, dso_meta_file, metadata_path, case_config_file)

        # dso_load_stats(dso_range, month_def, data_path)

        # bldg_load_stack(dso_range, day_range, base_case, agent_prefix, GLD_prefix, dso_meta_file, metadata_path)

        # DSO_loadprofiles(dso_range, day_range, base_case, dso_meta_file, metadata_path)

        # wholesale_price = ames_df.loc[start_time:end_time,' LMP'+dso_num].values.tolist()
        # dsomarket_data_df, dsomarket_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, 'dso_market')
        # retail_data_df, retail_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, 'retail_market')
        # substation_meta_df, substation_df = load_system_data(base_case, GLD_prefix, dso_num, day_num, 'substation')


        # Plot comparison of LMP prices for DSO
        # price_df = pd.DataFrame({'wholesale': wholesale_price}, index = dsomarket_data_df['time'])
        # price_df['DSO_RT'] = dsomarket_data_df['cleared_price_rt'].values.tolist()
        # price_df['Retail_RT'] = retail_data_df['cleared_price_rt'].values.tolist()
        # price_df.plot
        #
        # plt.figure()
        # plt.plot(price_df)
        # plt.plot(dsomarket_data_df['cleared_price_rt'], label='DSO RT Price')

    #     temp_df = get_day_df(dso[i], system, subsystem, variable, day, case, agent_prefix, gld_prefix)
    #     day_var.append(temp_df.loc[:, variable])
    # plt.plot(day_var[i], label='DSO' + dso[i])
    #
    # if subsystem is None:
    #     subsystem = ''
    # plt.legend()
    # plt.title(system + ' ' + subsystem + ' ' + variable + ' (Day' + day_num + ')')
    # plt.xlabel('Time of Day')
    # plt.ylabel(variable)
    #
    # # plt.suptitle('Day ' + day + ' ' + system + " " + subsystem + ": " + variable)
    # plot_filename = datetime.now().strftime(
    #     '%Y%m%d') + '_DSO_Comparison_Day' + day + system + subsystem + variable + '.png'
    #
    # # ------------Save figure to file  --------------------
    # file_path_fig = os.path.join(data_path, 'plots', plot_filename)
    # plt.savefig(file_path_fig, bbox_inches='tight')


    # 10-------------  Three dimensional bid curves and cleared quantities ------------
    # plots a 3D bid curve - work in progress.
    if BidCurve3D:
        system = 'retail_market'
        agent_df, agent_bid_df = load_agent_data(base_case, agent_prefix, dso_num, day_num, system)

        bidX = []
        bidY = []
        bidZ = []
        offerX = []
        offerY = []
        offerZ = []
        clearedX = []
        clearedY = []
        clearedZ = []

        for i in range(len(agent_bid_df)):
            bidX.append(math.floor(i/48)*5/60)
            bidY.append(agent_bid_df.iloc[i, 0])
            bidZ.append(agent_bid_df.iloc[i, 1])
            offerX.append(bidX[i])
            offerY.append(agent_bid_df.iloc[i, 2])
            offerZ.append(agent_bid_df.iloc[i, 3])

        for y in range(len(agent_df)):
            clearedX.append(math.floor(y)*5/60)
            clearedY.append(agent_df.iloc[y, 1])
            clearedZ.append(agent_df.iloc[y, 0])


        fig = plt.figure()

        # zline = np.linspace(0, 15, 1000)
        # xline = np.sin(zline)
        # yline = np.cos(zline)
        ax = plt.axes(projection='3d')
        ax.plot3D(clearedX, clearedY, clearedZ, c='b')
        ax.scatter3D(bidX, bidY, bidZ, c=bidZ, cmap='Greens')
        ax.scatter3D(offerX, offerY, offerZ, c=offerY, cmap='Reds')

        #ax.plot3D(xline, yline, zline, 'gray')
        # ax.contour3D(bidX, bidY, bidZ, 50, cmap='binary')

    toc()

    # 11 -----------  Customer performance analysis  -------------------------
    if customer_analysis:
        customer_comparative_analysis(base_case, trans_case, base_case, trans_case, dso_num, 'sum', None)

# =================================================================================

# Tasks to do:
# 1. extend load duration curves to take in a day range so the can be plotted for more than one day
# 2. plot transactive supply and demand quantity-price curves by DSO
# 3. Integrate outlier check on all key values
# 4. Consider restructuring code to be class-based.
# 5. Make data and plot saving paths generic.
# 6. Clean up graphs and put units on the graphs.
# 7. Create list of key houses per DSO to look at to make houses queried dynamic on DSO.
# fix path coding for weather information
# Per generator distribution of power outputs (for a day? a month? a year?). It may make sense to lump all the
# generators of a given type together. We expect that the different types of generators to behave differently and we
# should be able to compare this to real-world generators of that type to validate the model's performance. This may
# be best expressed as a change in output as a percentage of rated capacity.
# Heat map of solar PV profiles - Verify they look realistic. (This is probably low priority as we are supposed to be
# using unmanipulated data for the solar parameters. I guess this is more a check that we data was implemented
# correctly and looks reasonable.)
# RT and DA prices - Make sure these are similar and reasonable values. (Need to find where this data is).
# Comparison by DSO of cleared and actual quantities in both DA and RT markets.
# From Rob: Plot Lmp versus non wind-generation quantity to see if it makes sense.
# Add load duration curve for each class of power generation (e.g. wind)  (Compare with ERCOT wind load duration curve)
# Plot day ahead versus delivered differences for generation sources (particular day ahead non-curtailed wind).  Could
# have as scatter plot with error bounds at 5 and 10% as well as metric calculation and heat maps of differences.
# check that DSOs have somewhat different LMPs
# From Matt: Hayden, just a quick minor thought on the plots.  (Not sure if you’re doing this/tried this, but)
# Pandas should be able to read in data from the python-produced (agent?) h5 files and plot timestamps
# a bit more clearly than the integers you have in the attachments.  You might just have to parse the
# appropriate column so it recognizes the contents as timestamps (rather than strings).  Otherwise,
# these look great!