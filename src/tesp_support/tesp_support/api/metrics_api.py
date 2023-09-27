# Copyright (C) 2019-2023 Battelle Memorial Institute
# file: metrics_api.py

import pandas as pd
import logging as log_msg

import tesp_support.api.metrics_base_api as bc


def synch_time_series(series_list, synch_interval, interval_unit):
    """ Function resamples the time steps of the dataframes contained in the input data frame list
    to match the time intervals specified in the inputs

    Args:
        series_list (list<dataframe>): List containing a set of pandas dataframes each representing a time series
        synch_interval (int): the size of the time step which should be used to resample the dataframe
        interval_unit (str): the measurement unit of the interval to be sampled. The options for this function
            include the following options "nanoseconds", "seconds", "minutes", "hours", "days", "months", "years"
    Returns:
        list<dataframe>: pandas dataframe time series containing the resampled columns of data
    """
    synchronized_series = []
    for df in series_list:
        synchronized_df = df.resample(str(synch_interval) + interval_unit).interpolate()
        synchronized_df = synchronized_df.dropna()
        synchronized_series.append(synchronized_df)
    return synchronized_series


def get_synch_date_range(time_series):
    """ Function returns the latest starting date/time and the earliest ending date/time
    of the time series data frames in the time series list

    Args:
        time_series (list<dataframe>): List containing a set of pandas dataframes each representing a time series
    Returns:
        datetime, datetime: the latest start and the earliest end times found in the list of data frames
    """
    t_start = time_series[0].index.min()
    t_end = time_series[0].index.max()
    for t_series in time_series:
        if t_series.index.min() > t_start:
            t_start = t_series.index.min()
        if t_series.index.max() < t_end:
            t_end = t_series.index.max()
    return t_start, t_end


def synch_series_lengths(time_series):
    """ Function clips each of the time series in the time_series list so
    that each time series data frame has the same start and ending times

    Args:
        time_series (list<dataframe>): List containing a set of pandas dataframes each representing a time series
    Returns:
        list<dataframe>: a list containing the clipped time series data frames
    """
    synchronized_series = []
    synch_start, synch_end = get_synch_date_range(time_series)
    for tseries in time_series:
        _synch_series = tseries.query('index > @synch_start and index < @synch_end')
        synchronized_series.append(_synch_series)
    return synchronized_series


def synch_series(time_series, synch_interval, interval_unit):
    """ Function synchronizes all the time series data frames in the time_series list, so they
    all have the same start and ending times and the same number of times based upon a shared
    sampling interval

    Args:
        time_series (list<dataframe>): time series dataframe
        synch_interval (int): the size of the time intervals to be used in the time series
        interval_unit (str): the unit of the time interval the time series is to be sampled "T", "H", "S"
    Returns:
        list<dataframe>: time series dataframe containing the resampled data of the original
    """
    synchronized_series = synch_time_series(time_series, 1, "T")
    clipped_series = synch_series_lengths(synchronized_series)
    sampled_series = synch_time_series(clipped_series, synch_interval, interval_unit)
    return sampled_series


def get_avg_customer_demand(time_series, start_date, val_col_id):
    """ This function calculates the average of customer demand based on 8,760 hours of the year

    Metric defined in VM_Average Customer Demand.docx

    Args:
        time_series (dataframe): time series dataframe representing a time series containing customer demand records
        start_date (datetime): the start date and time that should be used in the calculation
        val_col_id (str): id of the dataframe column which contains the customer demand data values
    Returns:
        float: the calculated yearly average customer demand
    """
    begin_date = pd.to_datetime(start_date)
    end_date = begin_date + pd.offsets.Hour(8760)
    averaging_time_series = time_series.query('index >= @begin_date and index <= @end_date')
    if len(averaging_time_series.index) < 8760:
        log_msg.log(log_msg.ERROR, "Time series entered is not valid. Number of records is less than 8760")
        return
    avg_results = bc.get_time_series_average(averaging_time_series, begin_date, 8760)
    return avg_results[val_col_id]


def get_under_voltage_count(time_series, val_col_id, minimum_value):
    """ Function calculates number of under-voltage violations during the year

    Metric defined in VM_Count of Transmission Under-Voltage Violation Events.docx

    Args:
        time_series (dataframe): dataframe containing a time series of transmission values
        val_col_id (str): The id of the dataframe column where the transmission values are located
        minimum_value (float): The value that is to be used to compare transmission values against
    Returns:
        dataframe: time series dataframe containing a column with the under voltage counts
    """
    st_time = time_series.index[0]
    ts_end_time = time_series.index[-1]
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_counts = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        count_dataframe = calc_dataframe.loc[calc_dataframe[val_col_id] < minimum_value]
        calc_counts.append(len(count_dataframe.index))
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(calc_counts), index=calc_times)
    return df


def get_valuation(time_series, start_date, column_index):
    """ Function calculates the average power generated by solar photovoltaic (PV) power generators
    aggregated by hour of day.

    Metric defined in document VM_Distribution of PV real power generation by hour.docx

    Args:
        time_series (dataframe): dataframe containing the timeseries data to be used to calculate the valuations
        start_date (datetime): the starting date when the calculations will be started
        column_index (str): the dataframe column id that is used to identify the location of the values in the dataframe
    Returns:
        dataframe, float, float: function returns a tuple containing the dataframe containing the valuation
            values as a time series, a float representing the 14th percentile of the values, and a float representing
            the 86th percentile of the values
    """
    time_indexes = []
    time_values = []
    val_df = []
    avg_start = pd.to_datetime(start_date)
    end_date = bc.adjust_date_time(avg_start, "hours", 24)
    averaging_time_series = time_series.query('index >= @avg_start and index < @end_date')
    while len(averaging_time_series.index) > 0:
        avg_df = averaging_time_series.mean()
        valuation = avg_df[column_index]
        time_indexes.append(end_date)
        time_values.append(valuation)
        avg_start = end_date
        end_date = bc.adjust_date_time(avg_start, "hours", 24)
        averaging_time_series = time_series.query('index >= @avg_start and index <= @end_date')
    if len(time_indexes) > 0:
        val_df = pd.DataFrame(time_values, index=time_indexes)
    percentile_14 = time_series[column_index].quantile(0.14)
    percentile_86 = time_series[column_index].quantile(0.86)
    return val_df, percentile_14, percentile_86


def get_pv_aep_valuation(solar_irradiation, pv_system_area, pv_system_efficiency):
    """ Function calculates and estimate of the total annual power output from a PV system in the units of kWh

    Metric defined in the document VM_PV Annual Energy Production.docx

    Args:
        solar_irradiation (float): total solar irradiation incident on PV surface in the units of kWh/sq.m.
        pv_system_area (float): PV System Area
        pv_system_efficiency (float): PV System Efficiency
    Returns:
        float: the product of the three input values
    """
    return solar_irradiation * pv_system_area * pv_system_efficiency


def actual_der_vs_projected_ratio(actual_der, actual_col_name, projected_col_name, projected_der=None):
    """ This function calculates the accuracy of the predictive model, by comparing predicted results with actual results

    Metric defined in the document VM_Actual Benefits_Predicted Benefits.docx

    Args:
        actual_der (dataframe): time series dataframe that contains the total benefits from DER, as observed ex post.
        actual_col_name (str): id of the dataframe column that contains the actual DER benefit values
        projected_col_name (str): id of the dataframe column that contains the projected DER benefit values
        projected_der (dataframe): time series dataframe that contains the projected benefits from DER,
            as observed ex post.
    Returns:
        dataframe: time series dataframe that contains the calculated ratios
    """
    if projected_der is not None:
        if len(actual_der.index) != len(projected_der.index):
            log_msg.log(log_msg.ERROR, "dataframes are not synchronized")
            return
        if actual_der.index[0] != projected_der.index[0]:
            log_msg.log(log_msg.ERROR, "dataframes are not synchronized")
            return
        if actual_der.index[1] != projected_der.index[1]:
            log_msg.log(log_msg.ERROR, "dataframes are not synchronized")
            return
        actual_der["ratio"] = 100 * (projected_der[projected_col_name] / actual_der[actual_col_name])
        return actual_der
    else:
        i = 0
        calc_times = []
        calc_ratios = []
        while i < len(actual_der.index):
            calc_times.append(actual_der.index[i])
            calc_ratios.append(actual_der[projected_col_name].iloc[i] / actual_der[actual_col_name].iloc[i])
            i += 1
        df = pd.DataFrame(list(zip(calc_ratios)), columns=["ratio"], index=calc_times)
        return df


def get_average_air_temp_deviation(actual_df, actual_col_name, set_point_col_name, set_points_df, start_date_time):
    """ Function calculates per device average deviation from desired indoor temperature set point in a year for each DSO

    Metric defined in document VM_Average Indoor Air Temp Deviation.docx

    Args:
        actual_df (dataframe): per-device average deviation from desired air temperature set point
        actual_col_name (str): dataframe column id for the location of actual temperatures
        set_point_col_name (str): dataframe column id for the location of set point data
        set_points_df (dataframe): time series data frame containing the set points data.
        start_date_time (str): the starting date and time when the calculation should start

    Returns:
        float: the average of the calculated differences between the average of actual
            indoor temperature deviation from set point over one year.
    """
    avg_df = []
    start_date = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(start_date, "years", 1)
    if bc.check_dataframe_synchronization(actual_df, set_points_df) != "Synchronized":
        return None
    actual_calc_dataframe = actual_df.query('index >= @start_date and index <= @end_time')
    set_point_calc_dataframe = set_points_df.query('index >= @start_date and index <= @end_time')
    if not bc.check_for_full_year_data(actual_calc_dataframe):
        return None
    if not bc.check_for_full_year_data(set_point_calc_dataframe):
        return None
    if not bc.check_for_5_minute_data(actual_calc_dataframe):
        return None
    if not bc.check_for_5_minute_data(set_point_calc_dataframe):
        return None
    i = 0
    calc_times = []
    calc_diffs = []
    while i < len(actual_df.index):
        calc_times.append(actual_df.index[i])
        calc_diffs.append(actual_df.iloc[i][actual_col_name] - set_points_df.iloc[i][set_point_col_name])
        i += 1
    df = pd.DataFrame(list(zip(calc_diffs)), columns=['difference'], index=calc_times)
    avg_df = df.mean()
    median_df = df.median()
    min_df = df.min()
    max_df = df.max()
    return avg_df["difference"], median_df["difference"], min_df["difference"], max_df["difference"]


def get_unserved_electric_load(supply_df, supply_col_id, demand_df, demand_col_id, start_date_time):
    """ Function calculates the demand that was not met by supply during the course of 8760 hours

    Metric defined in document VM_Unserved Electric Load.docx

    Args:
        supply_df (dataframe): hourly supply data per year
        supply_col_id (str): name of the dataframe column where the supply data is located
        demand_df (dataframe): hourly demand data per year
        demand_col_id (str): name of the dataframe column where the demand data is located
        start_date_time (str): the starting date and time when the calculation should start
    Returns:
        dataframe: time series dataframe containing the calculated unserved load data
    """
    start_date = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(start_date, "years", 1)
    if bc.check_dataframe_synchronization(supply_df, demand_df) != "Synchronized":
        return None
    if not bc.check_for_hourly_data(supply_df):
        return None
    if not bc.check_for_hourly_data(demand_df):
        return None
    supply_calc_dataframe = supply_df.query('index >= @start_date and index <= @end_time')
    demand_calc_dataframe = demand_df.query('index >= @start_date and index <= @end_time')
    i = 0
    calc_times = []
    calc_unserved = []
    while i < len(supply_calc_dataframe.index):
        calc_times.append(supply_calc_dataframe.index[i])
        calc_unserved.append(supply_calc_dataframe.iloc[i][supply_col_id] -
                             demand_calc_dataframe.iloc[i][demand_col_id])
        i += 1
    df = pd.DataFrame(list(zip(calc_unserved)), columns=["unserved"], index=calc_times)
    return df


def get_transmission_voltage_magnitude(time_series, column_id, start_date, duration):
    """ Function calculates the hourly min, max, and avg values from the five-minute data contained in
    the time_series dataframe

    Metric defined in document VM_Transmission Voltage Magnitude.docx

    Args:
        time_series (dataframe): time series dataframe containing the five-minute data
        column_id (str): the name of the dataframe column with contains the transmission voltage data
        start_date (datetime): the starting date and time when the calculations should take place
        duration (int): the duration in hours to calculate the ending date and time when the
            calculations should take place
    Returns:
        dataframe: the calculated hourly min, max, and average values in a time series dataframe
    """
    col_names = ["min", "max", "avg"]
    calc_times = []
    calc_mins = []
    calc_maxs = []
    calc_avgs = []
    st_time = pd.to_datetime(start_date)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_mins.append(calc_dataframe.min()[column_id])
        calc_maxs.append(calc_dataframe.max()[column_id])
        calc_avgs.append(calc_dataframe.mean()[column_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)

    df = pd.DataFrame(list(zip(calc_mins, calc_maxs, calc_avgs)), columns=col_names, index=calc_times)
    return df


def get_feeder_energy_losses(feeder_gen_df, gen_column_id, feeder_load_df, load_column_id, start_date_time, duration):
    """ Function calculates the impact of trans-active energy systems on feeder energy losses.
    Data records in the time series entered as input must be recorded at five minute intervals

    Metric defined in document VM_Feeder Energy Losses.docx

    Args:
        feeder_gen_df (dataframe): data frame containing the 5-min average total generation
            from bulk power system and DERs
        gen_column_id (str): name of the column in the feeder generation dataframe where the generation data is located
        feeder_load_df (dataframe): data frame containing the 5-min average total load
        load_column_id (str): name of the column in the feeder load dataframe where the load data is located
        start_date_time (str): calculation start date and time
        duration (int): the duration of time in hours that the calculations are to be performed
    Returns:
        dataframe: a dataframe object containing the generation, load, and losses data
    """
    calc_times = []
    calc_losses = []
    calc_gens = []
    calc_loads = []
    col_names = ['feeder_generation', 'feeder_load', 'energy_loss']
    check_string = bc.check_dataframe_synchronization(feeder_gen_df, feeder_load_df)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    total_loss = 0
    while end_time <= ts_end_time:
        gen_dataframe = feeder_gen_df.query('index >= @st_time and index <= @end_time')
        load_dataframe = feeder_load_df.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_gens.append(gen_dataframe.mean()[gen_column_id])
        calc_loads.append(load_dataframe.mean()[load_column_id])
        total_loss = 0
        total_loss = gen_dataframe.sum()[gen_column_id] - load_dataframe.sum()[load_column_id]
        calc_losses.append(total_loss / (len(gen_dataframe.index) - 1))
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_gens, calc_loads, calc_losses)), columns=col_names, index=calc_times)
    return df


def get_peak_demand(time_series, column_id, start_date_time):
    """ This function calculates the highest hourly electricity demand (MW) in the year of
    data contained in the dataframe

    This metric is defined in document VM_PeakDemand or PeakSupply.docx

    Args:
        time_series (dataframe): time series dataframe that contains the demand values over the course of a year
        column_id (str): name of the dataframe column where the demand data is located
        start_date_time (str): calculation start date and time
    Returns:
        float: maximum value identified in the dataframe column identified by column_id
    """
    st_time = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(st_time, "years", 1)
    calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
    if not bc.check_for_full_year_data(calc_dataframe):
        return -9999.99
    if not bc.check_for_hourly_data(calc_dataframe):
        return -9999.99
    return calc_dataframe.max()[column_id]


def get_peak_supply(time_series, column_id, start_date_time):
    """ This function calculates the highest hourly electricity supply (MW) in the year of
    data contained in the dataframe

    This metric is defined in document VM_PeakDemand or PeakSupply.docx

    Args:
        time_series (dataframe): time series dataframe that contains the supply values over the course of a year
        column_id (str): name of the dataframe column where the supply data is located
        start_date_time (str): calculation start date and time
    Returns:
        float: maximum value identified in the dataframe column identified by column_id
    """
    st_time = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(st_time, "years", 1)
    calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
    if not bc.check_for_full_year_data(calc_dataframe):
        return -9999.99
    if not bc.check_for_hourly_data(calc_dataframe):
        return -9999.99
    return calc_dataframe.max()[column_id]


def get_max_under_voltage(time_series, column_id, threshold_val, start_date_time, duration):
    """ Function calculates the maximum over-voltage deviation reported each hour in the feeder voltage data

    Metric is defined in document VM_Max Under-Voltage Violations.docx

    Args:
        time_series (dataframe): time series dataframe containing feeder voltage data in 5 minute intervals
        column_id (str): the name of the dataframe column where the voltage data is located
        threshold_val (float): the maximum threshold data that is used to compare against the voltage data
        start_date_time (str): calculation start date and time
        duration (int): the duration of time in hours that the calculations are to be performed
    Returns:
        dataframe: time series dataframe containing the calculated hourly over voltage maximum values
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_maxs = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_diffs = []
        calc_diffs_times = []
        i = 0
        while i < len(calc_dataframe.index):
            calc_diffs.append(abs(threshold_val - calc_dataframe.iloc[i][column_id]))
            calc_diffs_times.append(calc_dataframe.index[i])
            i += 1
        result_dataframe = pd.DataFrame(list(zip(calc_diffs)), columns=["max_under_voltage"], index=calc_diffs_times)
        calc_maxs.append(result_dataframe.max()["max_under_voltage"])
#        calc_dataframe["voltage_violation"] = abs(threshold_val - calc_dataframe[column_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_maxs)), columns=["minimums"], index=calc_times)
    return df


def get_max_over_voltage(time_series, column_id, threshold_val, start_date_time, duration):
    """ Function calculates the maximum over-voltage deviation reported each hour in the feeder voltage data

    Metric is defined in document VM_Max Over-Voltage Violations.docx

    Args:
        time_series (dataframe): time series dataframe containing feeder voltage data in 5 minute intervals
        column_id (str): the name of the dataframe column where the voltage data is located
        threshold_val (float): the maximum threshold data that is used to compare against the voltage data
        start_date_time (str): calculation start date and time
        duration (int): the duration of time in hours that the calculations are to be performed
    Returns:
        dataframe: time series dataframe containing the calculated hourly over voltage maximum values
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_maxs = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
#        calc_dataframe2 = calc_dataframe
#        calc_dataframe2.loc[:, "voltage_violation_max"] = abs(calc_dataframe[column_id] - threshold_val)
        calc_diffs = []
        calc_diffs_times = []
        i = 0
        while i < len(calc_dataframe.index):
            calc_diffs.append(abs(calc_dataframe.iloc[i][column_id] - threshold_val))
            calc_diffs_times.append(calc_dataframe.index[i])
            i += 1
        result_dataframe = pd.DataFrame(list(zip(calc_diffs)), columns=["max_violation"], index=calc_diffs_times)
        calc_maxs.append(result_dataframe.max()["max_violation"])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_maxs)), columns=["maximums"], index=calc_times)
    return df


def get_indoor_air_temp_deviation(time_series, column_id, set_point, start_date_time, duration):
    """ Function calculates the maximum actual indoor temperature deviation from set point over one year.

    Metric is defined in document VM_Max Indoor Air Temp Deviation.docx

    Args:
        time_series (dataframe): time series dataframe that contains 5 minute max deviation data for a year
        column_id (str): the name of the dataframe column where the deviation data is located
        set_point (float): The set point value that is to be used in the calculation
        start_date_time (str): the date and time that the calculations are to start
        duration (int): the time duration in hours for which the calculations should be performed
    Returns:
        dataframe: time series dataframe containing the maximum deviations calculated hourly from the input data
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_maxs = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_diffs = []
        calc_diffs_times = []
        i = 0
        while i < len(calc_dataframe.index):
            calc_diffs.append(abs(calc_dataframe.iloc[i][column_id] - set_point))
            calc_diffs_times.append(calc_dataframe.index[i])
            i += 1
        result_dataframe = pd.DataFrame(list(zip(calc_diffs)), columns=["max_deviation"], index=calc_diffs_times)
        calc_maxs.append(result_dataframe.max()["max_deviation"])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_maxs)), columns=["temp_deviations"], index=calc_times)
    return df


def get_max_duration_under_voltage(time_series, column_id, limit_val, start_date_time, duration):
    """ Function calculates the maximum duration of an under-voltage event reported at each feeder

    Metric defined in document VM_Max Duration of Under-Voltage Violations.docx

    Args:
        time_series (dataframe): time series dataframe that contains the 5-minute three-phase voltage data
        column_id (str): name of the dataframe column the voltage data is located
        limit_val (float): threshold value used to compare voltage values against
        start_date_time (str): calculation start date and time
        duration (int): the duration of time in hours that the calculations are to be performed
    Returns:
        dataframe: hourly time series dataframe containing the calculated maximum duration of voltage violating
        under-voltage limit
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_durations = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        duration_df = calc_dataframe.loc[calc_dataframe[column_id] < limit_val]
        calc_durations.append(duration_df.max()[column_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_durations)), columns=["max_durations"], index=calc_times)
    return df


def get_max_duration_over_voltage(time_series, column_id, limit_val, start_date_time, duration):
    """ Function calculates the maximum duration of an over-voltage event reported at each feeder

    Metric defined in document VM_Max Duration of Over-Voltage Violations.docx

    Args:
        time_series (dataframe): time series dataframe that contains the 5-minute three-phase voltage data
        column_id (str): name of the dataframe column the voltage data is located
        limit_val (float): threshold value used to compare voltage values against
        start_date_time (str): calculation start date and time
        duration (int): the duration of time in hours that the calculations are to be performed
    Returns:
        dataframe: hourly time series dataframe containing the calculated maximum duration of voltage violating
        under-voltage limit
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_durations = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        duration_df = calc_dataframe.loc[calc_dataframe[column_id] > limit_val]
        calc_durations.append(duration_df.max()[column_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_durations)), columns=["max_durations"], index=calc_times)
    return df


def get_average_unit_price(time_series, column_id, start_date_time):
    """ Function calculates the market average unit price (of electricity) over the course of 8,760 hours, in a specific
    service territory managed by an independent system operator

    Metric defined in document VM_Market Average Unit Price.docx

    Args:
        time_series (dataframe): time series dataframe that contains the hourly market electricity prices for a year
        column_id (str): name of the dataframe column that the price data is located
        start_date_time (str): the date and time that the calculations are to start at
    Returns:
        float: the average unit price for the year
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "years", 1)
    calc_dataframe = time_series.query('index >= @st_time and index <= @ts_end_time')
    if not bc.check_for_full_year_data(calc_dataframe):
        return -9999.99
    if not bc.check_for_hourly_data(calc_dataframe):
        return -9999.99
    return bc.get_avg_data_value(calc_dataframe, column_id)


def get_hot_water_deficit(water_temperatures, water_column_id, desired_temperatures,
                          desired_column_id, flow_rates, flow_column_id, delta_t, start_date_time, duration):
    """ Function calculates device energy deficit from desired hot water temperature set point in a year

    Metric defined in document VM_Hot Water Supply Deficit.docx

    Args:
        water_temperatures (dataframe): per device 5-min average hot water actual temperature
        water_column_id (str): name of the dataframe column where the temperature data is located
        desired_temperatures (dataframe): per device 5-min average hot water temperature set point
        desired_column_id (str): name of the dataframe column where the set point temperature data is located
        flow_rates (dataframe): per device 5-min average hot water flow rate
        flow_column_id (str): name of the dataframe column where the flow rate data is located
        delta_t (float): time difference
        start_date_time (str): the date and time that the calculations are to start at
        duration (int): the length of time which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the calculated deficit data
    """
    check_string = bc.check_dataframe_synchronization(water_temperatures, desired_temperatures)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    check_string = bc.check_dataframe_synchronization(desired_temperatures, flow_rates)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_durations = []
    while end_time <= ts_end_time:
        calc_dataframe = water_temperatures.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        i = 0
        hwsd = 0
        while i < len(calc_dataframe.index):
            flow_rate = flow_rates.loc[calc_dataframe.index[i]][flow_column_id]
            desired_temp = desired_temperatures.loc[calc_dataframe.index[i]][desired_column_id]
            water_temp = water_temperatures.loc[calc_dataframe.index[i]][water_column_id]
            hwsd += flow_rate * (desired_temp - water_temp) * delta_t
            i += 1
        calc_durations.append(hwsd)
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_durations)), columns=["water_deficits"], index=calc_times)
    return df


def get_max_market_price(time_series, column_id, start_date_time):
    """ Function calculates the highest market price (of electricity) over the course of 8,760 hours,
    in a specific service territory managed by an independent system operator

    Metric defined in document VM_Highest Market Price.docx

    Args:
        time_series (dataframe): time series dataframe containing the hourly market price for electricity
            within a territory served by an ISO or balancing authority, for each of the 8,760 hours per year.
        column_id (str): name of the dataframe column where the market price data is located
        start_date_time (str): the date and time that the calculations are to start at
    Returns:
        float: the maximum market price value found in the market price dataset
    """
    st_time = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(st_time, "hours", 8760)
    calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
    if not bc.check_for_full_year_data(calc_dataframe):
        return None
    if not bc.check_for_hourly_data(calc_dataframe):
        return None
    return bc.get_max_column_value(time_series, column_id)


def get_emergency_scarcity_sell(scarcity_power_df, scarcity_col_id, scarcity_price_df, price_col_id,
                                generation_capacity_df, gen_col_id, available_power_df, available_col_id):
    """ Function calculates the annual value of firm energy for Scarcity Conditions

    Metric is defined in the document VM_Emergency Scarcity Wholesales Sells.docx

    Args:
        scarcity_power_df (dataframe): time series dataframe that contains the power data used in calculation
        scarcity_col_id (str): name of the dataframe column where the power data is located
        scarcity_price_df (dataframe): time series dataframe that contains the price data used in calculation
        price_col_id (str): name of the dataframe column where the price data is located
        generation_capacity_df (dataframe): time series dataframe that contains the generation data used in calculation
        gen_col_id (str): name of the dataframe column where the generation data is located
        available_power_df (dataframe): time series dataframe that contains the available power data used in
            calculation
        available_col_id (str): name of the dataframe column where the available power data is located
    Returns:
        dataframe: time series dataframe containing the calculated scarcity values
    """
    scarcity_sell = []
    calc_times = []
    check_string = bc.check_dataframe_synchronization(scarcity_power_df, scarcity_price_df)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    check_string = bc.check_dataframe_synchronization(scarcity_power_df, generation_capacity_df)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    check_string = bc.check_dataframe_synchronization(scarcity_power_df, available_power_df)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    i = 0
    while i < len(scarcity_power_df.index):
        scarcity_pow = scarcity_power_df.iloc[i][scarcity_col_id]
        scarcity_price = scarcity_price_df.iloc[i][price_col_id]
        gen_cap = generation_capacity_df.iloc[i][gen_col_id]
        av_energy = available_power_df.iloc[i][available_col_id]
        calc_times.append(scarcity_power_df.index[i])
        if gen_cap > 0:
            scarcity_sell.append(scarcity_pow * scarcity_price * (av_energy / gen_cap))
        else:
            scarcity_sell.append(-9999.99)
        i += 1
    col_names = ['emergency_scarcity_sell']
    df = pd.DataFrame(list(zip(scarcity_sell)), columns=col_names, index=calc_times)
    return df


def get_max_comm_packet_size(time_series, size_column_id, start_date_time, duration):
    """ Function calculates the maximum size of a message sent in the communication channels

    Metric is defined in document VM_Maximum Communication Packet Size.docx

    Args:
        time_series (dataframe): time series dataframe that contains the communication network packet size Mbs
        size_column_id (str): name of the dataframe column that contains the packet size data
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time which the calculations should be executed
    Returns:
        float: the maximum communication packet size for the time period entered
    """
    st_time = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(st_time, "hours", duration)
    calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
    return bc.get_max_column_value(calc_dataframe, size_column_id)


def get_mean_absolute_percentage(actual_load_df, actual_col_id, forecasted_load_df, forecasted_col_id,
                                 start_date_time, duration):
    """ Function calculates the prediction accuracy of load forecasting methods.

    Metric is defined in document VM_Mean Absolute Percentage (Load) Error.docx

    Args:
        actual_load_df (dataframe): time series dataframe containing the actual load observed over a period of time
        actual_col_id (str): name of the column where actual load data is located
        forecasted_load_df (dataframe): time series dataframe containing the forecasted load observed
            over a period of time
        forecasted_col_id (str): name of the column where forecasted load data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
       dataframe, float: time series dataframe containing the calculated ratios, the calculated average value
    """
    calc_ratios = []
    calc_times = []
    check_string = bc.check_dataframe_synchronization(actual_load_df, forecasted_load_df)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    st_time = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(st_time, "hours", duration)
    calc_dataframe = actual_load_df.query('index >= @st_time and index <= @end_time')
    i = 0
    while i < len(calc_dataframe.index):
        actual_load = actual_load_df.loc[actual_load_df.index[i]][actual_col_id]
        forecasted_load = forecasted_load_df.loc[actual_load_df.index[i]][forecasted_col_id]
        if actual_load != 0:
            calc_ratio = 100 * ((actual_load - forecasted_load) / actual_load)
            calc_times.append(calc_dataframe.index[i])
            calc_ratios.append(calc_ratio)
        i += 1
    df = pd.DataFrame(list(zip(calc_ratios)), columns=["percentage_errors"], index=calc_times)
    mean_absolute_percentage_df = df.mean()
    return df, mean_absolute_percentage_df['percentage_errors']


def get_minimum_market_price(time_series, price_col_id, start_date_time):
    """ Function calculates the minimum market price (of electricity) over the course of 8,760 hours

    Metric defined in document VM_Minimum Market Price.docx

    Args:
        time_series (dataframe): Hourly market prices for electricity
        price_col_id (str): name of the dataframe column where the price data is located
        start_date_time (str): the starting date and time when the calculation should start
    Returns:
        float: the minimum market price found in the data over the course of a year
    """
    st_time = pd.to_datetime(start_date_time)
    end_time = bc.adjust_date_time(st_time, "years", 1)
    calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
    if not bc.check_for_full_year_data(calc_dataframe):
        return None
    if not bc.check_for_hourly_data(calc_dataframe):
        return None
    return bc.get_min_column_value(calc_dataframe, price_col_id)


def get_substation_peak_power(time_series, power_col_id, start_date_time, duration):
    """ Function calculates a substation's maximum real power flow

    Metric defined in document VM_Substation Peak Real Power Demand.docx

    Args:
        time_series (dataframe): time series containing substation real power flow (Mvar) at 5 minute intervals
        power_col_id (str): name of the dataframe column containing the power flow data
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the calculated hourly peak power flow
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_peaks = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_peaks.append(calc_dataframe.max()[power_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_peaks)), columns=["peak_power"], index=calc_times)
    return df


def get_reactive_power_demand(time_series, max_col_id, avg_col_id, start_date_time, duration):
    """ Function calculates the maximum and average substation reactive power flow reported each hour

    Metric is defined in document VM_Substation Reactive Power Demand.docx

    Args:
        time_series (dataframe): time series dataframe containing the 5-minute substation reactive power flow data
        max_col_id (str): name of the dataframe column containing the 5-minute maximum data
        avg_col_id (str): name of the dataframe column containing the 5-minute average data
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the hourly maximum and average values calculated
        by the function
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_maxs = []
    calc_avgs = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_maxs.append(calc_dataframe.max()[max_col_id])
        calc_avgs.append(calc_dataframe.mean()[avg_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_maxs, calc_avgs)), columns=["hourly_maximum", "hourly_average"], index=calc_times)
    return df


def get_system_energy_losses(feeder_generation_df, gen_col_id, feeder_load_df, feeder_col_id, start_date_time,
                             duration):
    """ Function calculates the total energy loss at a feeder

    Metric is defined in document VM_System Energy Losses.docx

    Args:
        feeder_generation_df (dataframe): time series dataframe containing the 5-minute total feeder generation data
        gen_col_id (str): name of the dataframe column where the generation data is located
        feeder_load_df (dataframe): time series dataframe containing the 5-minute total feeder load data
        feeder_col_id (str): name of the dataframe column where the load data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the calculated hourly energy losses
    """
    check_string = bc.check_dataframe_synchronization(feeder_generation_df, feeder_load_df)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_losses = []
    while end_time <= ts_end_time:
        generation_df = feeder_generation_df.query('index >= @st_time and index <= @end_time')
        load_df = feeder_load_df.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_losses.append(generation_df.sum()[gen_col_id] - load_df.sum()[feeder_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_losses)), columns=["energy_losses"], index=calc_times)
    return df


def get_total_pv_reactive_power(time_series, pv_col_id, start_date_time, duration):
    """ Function calculates the hourly total system reactive power generated from PV

    Metric defined in document VM_Total PV Reactive Power.docx

    Args:
        time_series (dataframe): time series dataframe that contains the 5-minute power data used in the calculations
        pv_col_id (str): name of the dataframe column where the power data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the calculated hourly total reactive power values
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_pv_power = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_pv_power.append(calc_dataframe.sum()[pv_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_pv_power)), columns=["pv_reactive_power"], index=calc_times)
    return df


def get_total_pv_real_power(time_series, pv_col_id, start_date_time, duration):
    """ Function calculates the hourly total system reactive power generated from PV

    Metric is defined in document VM_Total PV Real Power.docx

    Args:
        time_series (dataframe): time series dataframe that contains the 5-minute power data used in the calculations
        pv_col_id (str): name of the dataframe column where the power data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe:
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_pv_power = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_pv_power.append(calc_dataframe.sum()[pv_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_pv_power)), columns=["pv_real_power"], index=calc_times)
    return df


def get_system_energy_loss(energy_sold_df, sold_col_id, energy_purchased_df, purchased_col_id, start_date_time,
                           duration):
    """ Function calculates the energy losses inclusive of transmission and distribution losses

    Metric defined in document VM_Total System Losses.docx

    Args:
        energy_sold_df (dataframe): time series dataframe containing the 5-minute sold energy data
        sold_col_id (str): name of the dataframe column where the sold data is located
        energy_purchased_df (dataframe): time series dataframe containing the 5-minute purchased energy data
        purchased_col_id (str): name of the dataframe column where the purchased data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the calculated hourly energy loss
    """
    check_string = bc.check_dataframe_synchronization(energy_sold_df, energy_purchased_df)
    if check_string != "Synchronized":
        log_msg.log(log_msg.ERROR, check_string)
        return None
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    purchased_vals = []
    diffs = []
    while end_time <= ts_end_time:
        sold_dataframe = energy_sold_df.query('index >= @st_time and index <= @end_time')
        purchased_dataframe = energy_purchased_df.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        diffs.append(sold_dataframe.sum()[sold_col_id] - purchased_dataframe.sum()[purchased_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(diffs)), columns=["energy_loss"], index=calc_times)
    return df


def get_total_wind_reactive_power(time_series, power_col_id, start_date_time, duration):
    """ Function calculates the hourly total system reactive power generated from Wind

    Metric defined in document VM_Total Wind Reactive Power.docx

    Args:
        time_series (dataframe): time series dataframe containing the 5-minute wind reactive power data
        power_col_id (str): name of the dataframe column where the wind data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the hourly wind power results
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_wind_power = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_wind_power.append(calc_dataframe.sum()[power_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_wind_power)), columns=["wind_reactive_power"], index=calc_times)
    return df


def get_total_wind_real_power(time_series, power_col_id, start_date_time, duration):
    """ Function calculates the hourly total system real power generated from wind

    Metric defined in document VM_Total Wind Real Power.docx

    Args:
        time_series (dataframe): time series dataframe containing the 5-minute wind power data
        power_col_id (str): name of the dataframe column where the wind data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the hourly total wind data results
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_wind_power = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_wind_power.append(calc_dataframe.sum()[power_col_id])
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_wind_power)), columns=["real_wind_power"], index=calc_times)
    return df


def get_transmission_over_voltage(time_series, voltage_col_id, compare_val, start_date_time, duration):
    """ Function calculates the maximum over-voltage violations at the transmission node

    Metric defined in document VM_Transmission Over-Voltage Violation.docx

    Args:
        time_series (dataframe): time series dataframe containing the 3-phase transmission node voltage
        voltage_col_id (str): name of the dataframe column containing the voltage data
        compare_val (float): threshold value to compare the data against
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the hourly transmission over voltage results
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_over_voltage = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_over_voltage.append(bc.get_time_series_max_value_over(calc_dataframe, voltage_col_id, compare_val))
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_over_voltage)), columns=["max_over_voltages"], index=calc_times)
    return df


def get_transmission_under_voltage(time_series, voltage_col_id, compare_val, start_date_time, duration):
    """ Function calculates the maximum under-voltage violations at the transmission node

    Metric defined in document VM_Transmission Under-Voltage Violation.docx

    Args:
        time_series (dataframe): time series dataframe that contains the 5-minute voltage data
        voltage_col_id (str): name of the column where the voltage data is located
        compare_val (float): threshold value to compare the voltage data against
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the calculated hourly under voltage results
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_under_voltage = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_under_voltage.append(bc.get_time_series_max_value_under(calc_dataframe, voltage_col_id, compare_val))
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_under_voltage)), columns=["max_under_voltage"], index=calc_times)
    return df


def get_wind_energy_production(time_series, prod_col_id, start_date_time, duration):
    """ Function calculates the amount of energy produced by wind at a feeder

    Metric defined in document VM_Wind Energy Production.docx

    Args:
        time_series (dataframe): time series dataframe that contains the 5-minute wind energy production data
        prod_col_id (str): name of the column where the wind energy production data is located
        start_date_time (str): the starting date and time when the calculation should start
        duration (int): the length of time in hours which the calculations should be executed
    Returns:
        dataframe: time series dataframe containing the calculated hourly total wind energy results
    """
    st_time = pd.to_datetime(start_date_time)
    ts_end_time = bc.adjust_date_time(st_time, "hours", duration)
    end_time = bc.adjust_date_time(st_time, "minutes", 60)
    calc_times = []
    calc_production = []
    while end_time <= ts_end_time:
        calc_dataframe = time_series.query('index >= @st_time and index <= @end_time')
        calc_times.append(st_time)
        calc_production.append(bc.get_column_total_value(calc_dataframe, prod_col_id))
        st_time = end_time
        end_time = bc.adjust_date_time(st_time, "minutes", 60)
    df = pd.DataFrame(list(zip(calc_production)), columns=["total_production"], index=calc_times)
    return df
