# Copyright (C) 2019-2023 Battelle Memorial Institute
# file: metrics_base_api.py

import pandas as pd
import numpy as np
import logging as log_msg


def get_node_ids(time_series, id_column_name):
    """ Function queries a list of unique values from a time series dataframe based upon a column id entered by the user

    Args:
        time_series (dataframe): time series dataframe that contains the values to be queried
        id_column_name (str): name of the dataframe column where the values are located
    Returns:
        list: list object containing the unique values found in the time series dataframe
    """
    feeder_ids = pd.unique(time_series[id_column_name])
    return feeder_ids


def get_node_data(time_series, node_id, id_column_name):
    """ Function queries the time series dataframe for the data set identified by the entered node id

    Args:
        time_series (dataframe): time series dataframe contains the node data to be queried
        node_id (str): the id of the node that is to be used in the query
        id_column_name (str): name of the time series dataframe column that contains
            the node ids to be queried against
    Returns:
        dataframe: time series dataframe containing data specific to a single node id
    """
    node_data = time_series.query('@id_column_name == @node_id')
    return node_data


def get_time_series_average(time_series, start_date, duration):
    """ Function calculates the average of each data column in the dataframe

    Args:
        time_series (dataframe): time series dataframe containing the data to be averaged
        start_date (str): the starting date and time that should be used in the calculation of the averages
        duration (int): the duration in hours that the averages should be calculated
    Returns:
        dataframe: dataframe containing the average value for each column in the input dataframe
    """
    begin_date = pd.to_datetime(start_date)
    end_date = begin_date + pd.offsets.Hour(duration)
    averaging_time_series = time_series.query('index >= @begin_date and index <= @end_date')
    return averaging_time_series.mean()


def get_avg_column_value(time_series, val_index):
    """ Function calculates the mean of the values in a data column of a dataframe

    Args:
        time_series (dataframe): time series dataframe containing the data to be averaged
        val_index (str): name of the column that contains the data to be averaged
    Returns:
        float: calculated average value for the column identified in the function arguments
    """
    avg_results = time_series.mean()
    return avg_results[val_index]


def get_max_column_value(time_series, val_index):
    """ Function searches a designated column in the time series dataframe and returns the maximum value found in the column

    Args:
        time_series (dataframe): time series dataframe containing the data to be searched for a maximum value
        val_index (str): name of the column where the data is located to calculate the maximum value
    Returns:
        float: the maximum data value found in the designated column
    """
    max_results = time_series.max()
    return max_results[val_index]


def get_min_column_value(time_series, val_index):
    """ Function searches a designated column in the time series dataframe and returns the minimum value found in the column

    Args:
        time_series (dataframe): time series dataframe containing the data to be searched for a minimum value
        val_index (str): name of the column where the data is located to calculate the minimum value
    Returns:
        dataframe: the minimum data value found in the designated column
    """
    min_results = time_series.min()
    return min_results[val_index]


def get_avg_data_value(time_series, column_id):
    """ Function calculates the average of a column in the time series dataframe and returns the average value of the column

    Args:
        time_series (dataframe): time series dataframe containing the data to be averaged
        column_id (str): name of the data column for which the average is to be calculated
    Returns:
        float: calculated average for the identified dataframe column
    """
    avg_results = time_series.mean()
    return avg_results[column_id]


def get_accuracy_ratio(input_df, actual_index, simulated_index):
    """ Function calculates the ratio of simulated data to actual data

    Args:
        input_df (dataframe): time series dataframe containing data columns for actual and simulated values
        actual_index (str): column id where the actual data is located
        simulated_index (str): column id where the simulated data is located
    Returns:
        dataframe: time series dataframe containing the calculated ratio values
    """
    df = input_df
    df['ratio'] = 100 * df[simulated_index] / df[actual_index]
    return df


def adjust_date_time(start_date, offset_type, offset_val):
    """ Function returns a date time object that is calculated by adding the offset_val to the entered start date

    Args:
        start_date: (datetime) the start date time
        offset_type (str): defines what interval of time is to be used. The following identifiers
            can be used "years", "months", "days", "hours", "minutes", "seconds", "nanoseconds"
        offset_val (int): the number of time intervals that are to be added to start_time
    Returns:
        dataframe: the modified date time
    """
    new_date = start_date
    if offset_type == "years":
        return start_date + pd.DateOffset(years=offset_val)
    elif offset_type == "months":
        return start_date + pd.DateOffset(months=offset_val)
    elif offset_type == "days":
        return start_date + pd.DateOffset(days=offset_val)
    elif offset_type == "hours":
        return start_date + pd.DateOffset(hours=offset_val)
    elif offset_type == "minutes":
        return start_date + pd.DateOffset(minutes=offset_val)
    elif offset_type == "seconds":
        return start_date + pd.DateOffset(seconds=offset_val)
    elif offset_type == "nanoseconds":
        return start_date + pd.DateOffset(nanoseconds=offset_val)
    return new_date


def check_for_full_year_data(time_series):
    """ Function checks if the input time series dataframe contains a full year's worth of data

    Args:
        time_series (dataframe): time series dataframe containing a year's worth of data
    Returns:
        bool: True if the time series contains a full year's worth of data
    """
    date_diff = time_series.index[-1] - time_series.index[0]
    date_diff = date_diff / np.timedelta64(1, 'Y')
    if round(date_diff, 2) != 1:
        log_msg.log(log_msg.ERROR, "actual dataframe does not contain a years worth of records")
        return False
    return True


def check_for_hourly_data(time_series):
    """ Function checks if the data in the time series is hourly

    Args:
        time_series (dataframe): time series dataframe containing hourly data
    Returns:
        bool: True if the data in the dataframe is hourly and False if it is not hourly
    """
    date_diff = time_series.index[1] - time_series.index[0]
    date_diff = date_diff / np.timedelta64(1, 'h')
    if round(date_diff, 2) != 1:
        log_msg.log(log_msg.ERROR, "actual dataframe does not contain hourly records")
        return False
    return True


def check_for_5_minute_data(time_series):
    """ Function checks if the data in the time series is 5-minute intervals

    Args:
        time_series (dataframe): time series dataframe containing 5-minute data records
    Returns:
        bool: True if the data in the dataframe is 5-minute and False if it is not
    """
    date_diff = time_series.index[1] - time_series.index[0]
    date_diff = pd.Timedelta(date_diff).seconds / 60.0
    if round(date_diff, 2) != 5:
        log_msg.log(log_msg.ERROR, "time series dataframe does not contain 5-minute data")
        return False
    return True


def get_time_series_max_value_under(time_series, column_id, compare_value):
    """ Function calculates the maximum value out of the number of values in a dataframe column that are less than
    a comparison value

    Args:
        time_series (dataframe): time series dataframe containing the data to be compared
        column_id (str): the name of the column in the dataframe where the data is located
        compare_value (str): the value the data is to be compared with
    Returns:
        int: the maximum of the values that are less than the compare value
    """
    vals_under_compare = time_series.loc[time_series[column_id] < compare_value]
    _max_value = vals_under_compare.max()[column_id]
    return _max_value


def get_time_series_max_value_over(time_series, column_id, compare_value):
    """ Function calculates the maximum value out of the number of values in a dataframe column that are greater than
    a comparison value

    Args:
        time_series (dataframe): time series dataframe containing the data to be compared
        column_id (str): the name of the column in the dataframe where the data is located
        compare_value (str): the value the data is to be compared with
    Returns:
        int: the maximum of the values that are greater than the compare value
    """
    _max_value = 0.0
    for _ts_row in time_series:
        if compare_value < _ts_row[column_id] > _max_value:
            _max_value = _ts_row[column_id]
    return _max_value


def get_column_total_value(time_series, column_id):
    """ Function returns the sum of the values in a dataframe column

    Args:
        time_series (dataframe): the time series dataframe which contains the data to be summed
        column_id (str): name of the column containing the values to be summed
    Returns:
        float: the sum of the values contained in the identified dataframe column
    """
    _total_value = 0.0
    summed_df = time_series.sum()
    return summed_df[column_id]


def get_time_series_difference_values(time_series, column_id, time_series2, column_id2):
    """ Function calculates the difference between data in a column of a dataframe with the data in
    a column of a second dataframe

    Args:
        time_series (dataframe): time series dataframe containing a data set to be used in the calculation
        column_id (str): name of the column where the data to be used is located
        time_series2 (dataframe): time series dataframe containing a data set to be used in the calculation
        column_id2 (str): name of the column where the data to be used is located
    Returns:
        float: the total value difference calculated as time_series2 - time_series1
    """
    _total_value = 0.0
    summed_df_1 = time_series.sum()
    summed_df_2 = time_series2.sum()
    return summed_df_2[column_id2] - summed_df_1[column_id]


def check_dataframe_synchronization(data_frame_1, data_frame_2):
    """ Function checks that two time series dataframes are synchronized by comparing size, starting time,
    and ending time of the data sets. If they are synchronized, the returns "Synchronized". If they are not,
    then the function will return an error message dependent upon what test failed.

    Args:
        data_frame_1 (dataframe): time series dataframe
        data_frame_2 (dataframe): time series dataframe
    Returns:
        str: a "Synchronized" message if the two dataframes are synchronized,
        if not, the function returns an error message
    """
    if len(data_frame_1.index) != len(data_frame_2.index):
        log_msg.log(log_msg.ERROR, "Dataframes have unequal number of rows")
        return "Dataframes have unequal number of rows"
    elif data_frame_1.index[0] != data_frame_2.index[0]:
        log_msg.log(log_msg.ERROR, "Starting indices of dataframes are not equal")
        return "Starting indices of dataframes are not equal"
    elif data_frame_1.index[-1] != data_frame_2.index[-1]:
        log_msg.log(log_msg.ERROR, "Starting indices of dataframes are not equal")
        return "Ending indices of dataframes are not equal"
    else:
        return "Synchronized"


def create_testing_dataframe(start_date, end_date, col_names, time_interval):
    """ Function creates a testing dataframe containing random values

    Args:
        start_date (str): the starting date of the time series
        end_date (str): then ending date of the time series
        col_names (list<string>): the names to be used as the column headers in the resultant dataframe
        time_interval (int): frequency of time intervals. These designations are the same as
            the designations used to define a pandas date_range e.g. "T", "5T", "H", "12H",...
    Returns:
        dataframe: time series dataframe containing random data values over the course of the defined time range
    """
    np.random.seed(0)
    rng = pd.date_range(start_date, end_date, freq=time_interval)
    df = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, len(col_names))), columns=col_names, index=rng)
    return df
