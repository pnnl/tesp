import pandas as pd
import numpy as np


def get_node_ids(time_series, id_column_name):
    """

    :param time_series:
    :param id_column_name:
    :return:
    """
    feeder_ids = pd.unique(time_series[id_column_name])
    return feeder_ids


def get_node_data(time_series, node_id, id_column_name):
    """

    :param time_series:
    :param node_id:
    :param id_column_name:
    :return:
    """
    node_data = time_series.query('@id_column_name == @node_id')
    return node_data


def clip_time_series(time_series, start_date, end_date):
    """

    :param time_series:
    :param start_date:
    :param end_date:
    :return:
    """
    averaging_time_series = time_series.query('index >= @start_date and index <= @end_date')
    return averaging_time_series


def get_time_series_average(time_series, start_date, duration, time_interval):
    """
    :param time_series:
    :param start_date:
    :param duration:
    :param time_interval:
    :return:
    """
    begin_date = pd.to_datetime(start_date)
    end_date = begin_date + pd.offsets.Hour(duration)
    averaging_time_series = time_series.query('index >= @begin_date and index <= @end_date')
    return averaging_time_series.mean()


def get_avg_column_value(time_series, val_index):
    """
    VM_Substation Reactive Power Demand
    :param time_series:
    :param val_index:
    :return:
    """
    avg_results = time_series.mean()
    return avg_results[val_index]


def get_max_column_value(time_series, val_index):
    """
    VM_Substation Reactive Power Demand
    VM_Substation Peak Real Power Demand
    VM_maximum customer voltages
    VM_Maximum Communication Packet Size
    :param time_series:
    :param val_index:
    :return:
    """
    max_results = time_series.max()
    return max_results[val_index]


def get_min_column_value(time_series, val_index):
    """
    VM_Minimum Market Price
    VM_Minimum customer voltages

    :param time_series:
    :param val_index:
    :return:
    """
    min_results = time_series.min()
    return min_results[val_index]

def get_avg_data_value(time_series, column_id):
    """

    :param time_series:
    :param val_index:
    :return:
    """
    avg_results = time_series.mean()
    return avg_results[column_id]


def get_accuracy_ratio(input_df, actual_index, simulated_index):
    """
    VM_Mean Absolute Percentage (Load) Error
    :param input_df:
    :param actual_index:
    :param simulated_index:
    :return:
    """
    df = input_df
    df['ratio'] = 100 * df[simulated_index] / df[actual_index]
    return df


def adjust_date_time(start_date, offset_type, offset_val):
    """

    :param start_date:
    :param offset_type:
    :param offset_val:
    :return:
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


def get_time_series_max_value_under(time_series, column_id, compare_value):
    """
    VM_Transmission Under-Voltage Violation
    :param time_series:
    :param column_id:
    :param compare_value:
    """
    vals_under_compare = time_series.loc[time_series[column_id] < compare_value]
    _max_value = vals_under_compare.max()[column_id]
    return _max_value



def get_time_series_max_value_over(time_series,column_id,compare_value):
    """
    VM_Transmission Over-Voltage Violation
    :param time_series:
    :param column_id:
    :param compare_value:
    """
    _max_value = 0.0
    for _ts_row in time_series:
        if compare_value < _ts_row[column_id] > _max_value:
            _max_value = _ts_row[column_id]
    return _max_value


def get_column_total_value(time_series, column_id):
    """
    VM_Wind Energy Production
    VM_Total Wind Real Power
    Total PV Real Power
    VM_Total PV Reactive Power
    :param time_series:
    :param column_id:
    """
    _total_value = 0.0
    summed_df = time_series.sum()
    return summed_df[column_id]


def get_time_series_difference_values(time_series, column_id, time_series2, column_id2):
    """
    VM_Unserved Electric Load
    VM_Total Wind Reactive Power
    VM_Total System Losses
    VM_System Energy Losses

    :param time_series:
    :param column_id:
    :param compare_value:
    """
    _total_value = 0.0
    summed_df_1 = time_series.sum(axis=1)
    summed_df_2 = time_series2.sum(axis=1)
    return summed_df_2[column_id2] - summed_df_1[column_id]

def check_dataframe_synchronization(data_frame_1, data_frame_2):
    """

    :param data_frame_1:
    :param data_frame_2:
    :return:
    """
    if len(data_frame_1.index) != len(data_frame_2.index):
        return "Dataframes have unequal number of rows"
    elif data_frame_1.index[0] != data_frame_2.index[0]:
        return "Starting indices of dataframes are not equal"
    elif data_frame_1.index[-1] != data_frame_2.index[-1]:
        return "Ending indices of dataframes are not equal"
    else:
        return "Synchronized"


def create_testing_dataframe(start_date, end_date, col_names, time_interval):
    np.random.seed(0)
    rng = pd.date_range(start_date, end_date, freq=time_interval)
    df = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, len(col_names))), columns=col_names, index=rng)
    return df


