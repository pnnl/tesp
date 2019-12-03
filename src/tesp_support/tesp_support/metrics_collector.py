# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: metrics_collector.py
""" Utility functions for metrics collection within tesp_support, able to write to JSON and HDF5
"""
import numpy as np
import pandas as pd
import collections
import json
import os
import logging


class MetricsCollector(object):
    """ Metrics collector class that handles writing data to disk in either JSON or HDF5 format.

    Attributes:
        start_time (float): the start time of the simulation
        write_hdf5 (bool): flag to determine if we write to HDF5 (defaults to False)
        write_json (bool): flag to determine if we write to JSON (defaults to True)
        meta_data_dict (dict): dictionary that hold the meta data and file string for each metric

    """
    def __init__(self, start_time='1970-01-01 00:00:00', write_hdf5=False, write_json=True, meta_data_dict=None):
        """Initializes the class
        """
        self.start_time = start_time
        self.write_hdf5 = write_hdf5
        self.write_json = write_json
        # putting meta_data_dict=dict() as default with do something screwy like have the dictionary grow class-wide
        self.meta_data_dict = meta_data_dict if meta_data_dict is not None else dict()

    def add_metric(self, name, file_string, meta):
        """ Add another metrics to be collected

        Args:
            name (str): name of the metric to add
            file_string (str): flag to determine if we write to HDF5 (defaults to False)
            meta (dict): flag to determine if we write to JSON (defaults to True)

        """
        self.meta_data_dict[name] = {'meta': meta, 'file_string': file_string, 'data': {}}

    def add_data(self, name, time, data):
        """ Append data metrics already specified

        Args:
            name (str): name of the metric to add data to
            time (int): time stamp for the data
            data (dict): dictionary containing data to add

        """
        if name in self.meta_data_dict:
            self.meta_data_dict[name]['data'][str(time)] = deepish_copy(data)
        else:
            logging.error('unable to add metric data to ' + str(name) + ' as it does not exist')

    def write_metrics(self, cnt):
        """ Write all known metrics to disk

        """
        # TODO: turn into multiprocessed version
        for name in self.meta_data_dict:
            file_string = self.meta_data_dict[name]['file_string']
            meta = self.meta_data_dict[name]['meta']
            data = self.meta_data_dict[name]['data']

            # portion to write JSON
            if self.write_json:
                i = 0
                while os.path.isfile(file_string + str(i) + '_metrics.json'):
                    i += 1
                filename = file_string + str(i) + '_metrics'

                metric_data = {'Metadata': meta, 'StartTime': self.start_time}
                metric_data.update(data)

                write_json(filename, metric_data)

            # portion to write HDF5
            if self.write_hdf5:
                filename = file_string + 'metrics'

                metric_data = {'Metadata': meta, 'StartTime': self.start_time}
                metric_data.update(data)

                write_hdf5(filename, metric_data, cnt)

            # reset data
            self.meta_data_dict[name]['data'].clear()


def deepish_copy(org):
    """ Faster approach to deepcopy, for a dict of the simple python types.

    Args:
         org (dict): original dictionary to copy

    Returns:
         out (dict): copied dictionary
    """
    out = dict().fromkeys(org)
    for k, v in org.items():
        try:
            out[k] = v.copy()  # dicts, sets
        except AttributeError:
            try:
                out[k] = v[:]  # lists, tuples, strings, unicode
            except TypeError:
                out[k] = v  # ints
    return out


def write_json(filename, metric_data):
    """
     This function writes the metric data to a JSON files

     Args:
         filename (str): the filename to dump data to
         metric_data (dict): metrics data dictionary to dump
     """
    with open(filename + '.json', 'w') as outfile:
        json.dump(metric_data, outfile, ensure_ascii=False, indent=2)


def write_hdf5(filename, metric_data, cnt):
    """
    This function writes the metric data to a HDF5 files

    Args:
        filename (str): the filename to dump data to
        metric_data (dict): metrics data dictionary to dump
        cnt (int): interval counter
        mode (str): 'a' append to possibly already existing file (make sure to wipe clean if rerunning scripts)
                    'w' to write a clean new file
        append (bool): True if you want to append to a potentially already existing table of same key
                       (only works with mode='a'?). False if you want a clean new table
    """
    def get_starttime(dct):
        """Given a metrics dictionary 'dct', return sim start timestamp."""
        starttime = dct.get('StartTime')
        # insert checks/error handling?
        return pd.Timestamp(starttime)

    def get_columns(dct):
        """Given a metrics dictionary 'dct', return column names in same order as data."""
        metadata = dct.get('Metadata')
        # insert checks/error handling?
        columns = pd.DataFrame(metadata).T.sort_values('index').index.to_numpy()
        # insert checks/error handling?
        return columns

    def get_units(dct):
        """Given a metrics dictionary 'dct', return units in same shape/order as data."""
        metadata = dct.get('Metadata')
        # insert checks/error handling?
        units = pd.DataFrame(metadata).T.sort_values('index')['units']
        ret_units = []
        for u in units:
            try:
                # I don't think checking for brackets will work since we may have '[0..4] = xyz'
                elem = np.array(json.loads(u.replace("'", '"')))
            except Exception as e:
                logging.debug(str(e) + ' appending original u rather json.loads(u)')
                elem = u
            ret_units.append(elem)
        return ret_units

    def get_tablesize_map(units):
        """Given a metrics units vector (of vectors/scalars), return map of unique
        sizes to column indexes within."""
        ret_dct = collections.defaultdict(list)
        for ii, uu in enumerate(units):
            if hasattr(uu, 'shape'):  # rather than test if type is numpy.ndarray?
                ret_dct[uu.shape].append(ii)
            else:
                ret_dct[()].append(ii)
        return ret_dct

    def to_frame(dct, tablesize, col_indices, col_names, starttime):
        """Given a metrics dictionary, column indices we're focusing on (and tablesize
        each indexes elements are) return appropriate dataframe"""
        # remove all but the time->uid->vec maps (assuming you save these outside and pass in as starttime/cols)
        # WARNING: this manipulates original/incoming dct!
        dct.pop('StartTime', None)
        dct.pop('Metadata', None)

        # for timeseries x entity dataframe, now that metadata key is out of the picture
        # THIS WILL BE THE BOTTLENECK (TODO: speed up?)
        index_cols = ['time', 'uid'] + ['i', 'j', 'k', 'l'][0:len(tablesize)]
        logging.debug(str(tablesize))
        logging.debug(str(index_cols))
        logging.debug(str(col_indices))
        logging.debug(str(col_names))
        lsts = []
        if len(tablesize) == 0:
            #         lsts = [
            #             np.concatenate([
            #                 [starttime + pd.Timedelta(seconds=int(t)), e],
            #                 np.array(vec)[col_indices]
            #             ]) for t, subdct in dct.items() for e, vec in subdct.items()
            #         ]
            for t, subdct in dct.items():
                ts = starttime + pd.Timedelta(seconds=int(t))
                for e, vec in subdct.items():
                    lsts.append(np.concatenate([[ts, e], np.array(vec)[col_indices]]))
        elif len(tablesize) == 1:  # hardcoding until I figure out how to generalize
            for t, subdct in dct.items():
                ts = starttime + pd.Timedelta(seconds=int(t))
                for e, vec in subdct.items():
                    try:
                        subvec = np.array(vec)[col_indices]
                    except Exception as ex:
                        logging.debug('to_frame encountered error: ' + str(ex))
                        subvec = [vec[index] for index in col_indices]
                        subvec = np.array(subvec)
                    row = [ts, e]
                    for ii in range(tablesize[0]):
                        lsts.append(np.concatenate([row, [ii], [subveccol[ii] for subveccol in subvec]]))
        elif len(tablesize) == 2:  # hardcoding until I figure out how to generalize
            for t, subdct in dct.items():
                ts = starttime + pd.Timedelta(seconds=int(t))
                for e, vec in subdct.items():
                    try:
                        subvec = np.array(vec)[col_indices]
                    except Exception as ex:
                        logging.debug('to_frame encountered error: ' + str(ex))
                        subvec = [vec[index] for index in col_indices]
                        subvec = np.array(subvec)
                    row = [ts, e]
                    for ii in range(tablesize[0]):
                        for jj in range(tablesize[1]):
                            lsts.append(
                                np.concatenate([row, [ii, jj], [subveccol[ii][jj] for subveccol in subvec]]))
        elif len(tablesize) == 3:  # hardcoding until I figure out how to generalize
            for t, subdct in dct.items():
                ts = starttime + pd.Timedelta(seconds=int(t))
                for e, vec in subdct.items():
                    try:
                        subvec = np.array(vec)[col_indices]
                    except Exception as ex:
                        logging.debug('to_frame encountered error: ' + str(ex))
                        subvec = [vec[index] for index in col_indices]
                        subvec = np.array(subvec)
                    row = [ts, e]
                    for ii in range(tablesize[0]):
                        for jj in range(tablesize[1]):
                            for kk in range(tablesize[2]):
                                lsts.append(
                                    np.concatenate([row, [ii, jj, kk], [subveccol[ii][jj][kk]
                                                                        for subveccol in subvec]]))
        return pd.DataFrame(lsts, columns=np.concatenate([index_cols, col_names])).set_index(index_cols)

    idx = str(cnt)
    start_time = get_starttime(metric_data)
    logging.debug(str(start_time))

    data_units = get_units(metric_data)
    logging.debug(str(len(data_units)))

    data_columns = get_columns(metric_data)
    logging.debug(str(data_columns))

    table_size_map = get_tablesize_map(data_units)
    logging.debug(str(table_size_map))

    # TODO: write out units beforehand/once?
    # this can easily handle time partitioning/appending, just remember to clear metrics_dct
    for i, (table_size, column_indices) in enumerate(sorted(table_size_map.items())):
        df = to_frame(dct=metric_data,
                      tablesize=table_size,
                      col_indices=column_indices,
                      col_names=data_columns[column_indices],
                      starttime=start_time)
        # revisit mode/append depending on iterating over this with time partition
        # Mode can be 'a' as long as the enter metrics file is written in one shot (which it generally is, due to
        #  TESP conventions of writing all metrics during a metrics collection interval at the end of the interval,
        #  typcially daily.)
        #  More efficiently we could append to a file each day which would require changes to the call such that the
        #  write mode is not always 'w'.
        logging.debug('-----df examination----')
        logging.debug('------i: ' + str(i))
        logging.debug(str(df.head()))
        if idx == 1:
            df.to_hdf(filename + '.h5', key='metrics_' + idx + ' _df{}'.format(len(table_size)), mode='w', append=False, format='table',
                      complevel=9, index=False)
        else:
            df.to_hdf(filename + '.h5', key='metrics_' + idx + '_df{}'.format(len(table_size)), mode='a', append=False, format='table',
                      complevel=9, index=False)

    # once all appends done, run this to create index
    with pd.HDFStore(filename + '.h5', 'r+', complevel=9) as ostore:
        for g in ostore:
            try:
                ostore.create_table_index(g, optlevel=9, kind='full')
                logging.debug('successfully indexed {}'.format(g))
            except Exception as err:
                logging.error('tried, but failed to index {} (OK; but error message={})'.format(g, err))
