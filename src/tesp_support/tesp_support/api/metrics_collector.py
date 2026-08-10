# Copyright (c) 2017-2025 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: metrics_collector.py
""" Utility functions for metrics collection within tesp_support, able to write to JSON and HDF5 """

import collections
import itertools
import json
import os.path

import numpy as np
import pandas as pd

from ..api.helpers import log

class MetricsTable(object):
    def __init__(self, columns, units):
        assert len(columns) == len(units), \
            ('len(columns) = {} should be equal to len(units) = {}'.
             format(len(columns), len(units)))
        self.columns = columns
        self.units = units
        self.data = list()

    def append_data(self, data):
        assert len(data) == len(self.columns), \
            ('len(data) = {} should be equal to len(columns) = {}'.
             format(len(data), len(self.columns)))
        self.data.append(data)

    def clear(self):
        # this is now compatible with python 2 and 3, as 'list.clear' did not exist pre-3.2
        del self.data[:]

    def to_frame(self, times, uids, shape, filename=''):
        log.info('entering to_frame, filename={}'.format(filename))
        log.debug('times {}'.format(times))
        log.debug('uids {}'.format(uids))
        log.debug('shape {}'.format(shape))
        log.debug('columns {}'.format(self.columns))
        log.debug('units {}'.format(self.units))
        log.debug('len(data) {}'.format(len(self.data)))
        assert len(times) == len(uids) == len(self.data), \
            ('len(times) = {} should be equal to len(uids) = {}, and len(self.data) = {}'.
             format(len(times), len(uids), len(self.data)))
        # assumes we never have > 5 dimensions, and if <, then zip takes min of both lists
        ijs_columns = ['i', 'j', 'k', 'l', 'm'][:len(shape)]
        idx_columns = ['time', 'uid'] + ijs_columns
        try:
            if len(self.data) > 0:
                data = np.asarray(self.data)
                log.debug('data.shape {}'.format(data.shape))
                log.debug('data (after asarray) {}'.format(data))
                assert len(data.shape) >= 2, \
                    ('len(data.shape) = {} should be >= 2'.
                     format(len(data.shape)))
                assert len(data.shape[2:]) == len(shape), \
                    ('len(data.shape[2:]) = {} should be == len(shape) = {}'.
                     format(len(data.shape[2:]), len(shape)))
                if data.shape[2:] != shape:
                    log.warning(
                        'file = {}, shape = {} (formed from units) '
                        'should equal data.shape[2:] = {} (taking this as shape now)'.
                        format(filename, shape, data.shape[2:]))
                    shape = data.shape[2:]
                # these are current rows and cols to be expanded based on higher dimension values in 'data' entries
                num_rows, num_cols = data.shape[:2]
                # some of this is redundant, yet still works for the simple case where entries are scalars
                # for each column, stack elements from row, i, j, ... (so, swap axes, and reshape with (num_cols, -1) to figure out resulting dim)
                df = pd.DataFrame(data.swapaxes(0, 1).reshape(num_cols, -1).T, columns=self.columns)
                # i, j, k, ... parts of the table, for one (time, uid) pair (to be repeated)
                ijs = np.asarray(list(itertools.product(*[range(n) for n in shape])))
                df['time'] = np.repeat(times, len(ijs))
                df['uid'] = np.repeat(uids, len(ijs))
                for k, v in zip(ijs_columns, np.tile(ijs, (num_rows, 1)).T):
                    df[k] = v
            else:  # len(data) == 0, i.e. no time/uids have been appended
                log.warning('data is empty {}, constructing empty dataframe for {}'.format(self.data, filename))
                df = pd.DataFrame(columns=np.concatenate([idx_columns, self.columns]))
        except AssertionError as e:
            log.error('got error: {}, setting df to be empty!'.format(e))
            df = pd.DataFrame(columns=np.concatenate([idx_columns, self.columns]))
        return df.set_index(['time'])  # , 'uid'])#.set_index(idx_columns)

    # TODO: enable forming similar units dataframe?


class MetricsStore(object):
    """
    This stores our metrics in appropriately sized tables, geared towards being ready to write to hdf5
    (so writing to JSON might take longer than if we kept things ready to write to JSON).

    Attributes:
        time_uid_pairs (list): an ongoing list of (time, uid) pairs incoming with data
        index_to_shapes (list): shapes of incoming column's units
        file_string (str): the file path (barring extension) which will be appended with "_metrics.{h5, JSON}"
        shape_to_tables (MetricsTable): a common store for these metrics, to ease writing out all metrics/tables
    """

    def __init__(self, name_units_pairs, file_string, collector):
        """
        Args:
            name_units_pairs (list of pairs): an ordered list of (name, units) pairs, where name is 
                the name of a column and units is the units (possibly non-scalar) of that column-name (if non-scalar, we expand)
            file_string (str): the file path (barring extension) which will be appended with "_metrics.{h5, JSON}"
            collector (MetricsCollectorBase): a common store for these metrics, to ease writing out all metrics/tables
        """
        # Note: this new format doesn't allow for extra metadata info to be stored/sent here, 
        # which I believe I saw in earlier JSON metadata outputs
        self.time_uid_pairs = list()
        self.index_to_shapes = list()
        shape_to_cols = collections.defaultdict(list)
        shape_to_units = collections.defaultdict(list)
        for i, (col, units) in enumerate(name_units_pairs):
            log.debug('getting shape for index {}, column {} with units {}'.format(i, col, units))
            # shape of np.array(x) is () if x itself does not have array-like shape (e.g. float/int/str), else (y,) or (y, z), or ...
            shape = np.array(units).shape
            self.index_to_shapes.append(shape)
            shape_to_cols[shape].append(col)
            shape_to_units[shape].append(units)
        # TODO: decide if we want to assert if file_string shouldn't already exist 
        #  (I don't think so, we may want to append after this metadata dict is wiped every 1-day or so)
        self.file_string = file_string
        collector.register_metrics_store(self)
        self.shape_to_tables = {s: MetricsTable(columns=shape_to_cols[s],
                                                units=shape_to_units[s]) for s in shape_to_cols.keys()}

    def append_data(self, time, uid, *args):
        """
        Appends a single (time, uid) pair's metrics to appropriate tables (depends on shape of each arg)

            time (str or int): time in seconds after start of simulation
            uid (str or int or ?): unique identifier of an object (e.g. a name)
            args (list): a list of length/order equal to name_units_pairs seen when constructing this store
        """
        self.time_uid_pairs.append([time, uid])
        # bin columns by shape, then update corresponding subtables
        dct = collections.defaultdict(list)
        assert len(args) == len(self.index_to_shapes), \
            ('len(args) = {} should be equal to len(index_to_shape) = {}'.
             format(len(args), len(self.index_to_shapes)))
        for s, v in zip(self.index_to_shapes, args):
            dct[s].append(deepish_copy(v))
        for s, vs in dct.items():
            self.shape_to_tables[s].append_data(vs)

    def clear(self):
        # this is now compatible with python 2 and 3, as 'list.clear' did not exist pre-3.2
        del self.time_uid_pairs[:]
        for t in self.shape_to_tables.values():
            t.clear()


class MetricsCollector(object):
    """
    Metrics collector base class that handles collecting and writing data to disk (.json).

    Attributes:
        start_time (pd.Timestamp): the start time of the simulation
        metrics_stores (list): list of MetricsStores holding/growing data

    """

    def __init__(self, start_time='1970-01-01 00:00:00'):
        self.start_time = pd.Timestamp(start_time)
        self.metrics_stores = list()

    @classmethod
    def factory(cls, start_time='1970-01-01 00:00:00', write_hdf5=False):
        """
        Args:
            start_time (str): start time of simulation in datetime string format
            write_hdf5 (bool): flag to determine if we write to .h5 (if True) or .json (if False; defaults to this)
        Returns:
            MetricsCollector: MetricsCollectorHDF or Base instance, depending on write_hdf5 flag
        """
        return MetricsCollectorHDF(start_time) if write_hdf5 else MetricsCollector(start_time)

    def register_metrics_store(self, metrics_store):
        """
        Args:
            metrics_store (MetricsStore): A store to be appended to our ongoing list
        """
        log.debug('registering metrics store with file_string {}'.format(metrics_store.file_string))
        self.metrics_stores.append(metrics_store)

    def write_metrics(self):
        """ Write all known metrics to disk (.json) and reset data within each metric."""
        log.debug('writing metrics (to json, in serial)')
        # TODO: look into 'ray' package?: https://towardsdatascience.com/10x-faster-parallel-python-without-python-multiprocessing-e5017c93cce1
        for m in self.metrics_stores:
            to_json(m, self.start_time)
            m.clear()

    def finalize_writing(self):
        pass


class MetricsCollectorHDF(MetricsCollector):
    def __init__(self, start_time='1970-01-01 00:00:00'):
        super(MetricsCollectorHDF, self).__init__(start_time=start_time)
        self.num_writes_counter = 0

    def write_metrics(self):
        """ Write all known metrics to disk (.h5)."""
        log.debug('writing metrics (to h5, in serial)')
        # TODO: look into 'ray' package?: https://towardsdatascience.com/10x-faster-parallel-python-without-python-multiprocessing-e5017c93cce1
        for m in self.metrics_stores:
            to_hdf(m, self.start_time, self.num_writes_counter)
            m.clear()
        self.num_writes_counter += 1

    def finalize_writing(self):
        for m in self.metrics_stores:
            finalize_hdf(m)


def deepish_copy(obj):
    """ Faster approach to deepcopy, for an object of the simple python types.

    Args:
        obj: original object to copy
    Returns:
        object: copy of obj
    """
    if hasattr(obj, 'copy'):
        return obj.copy()  # dicts, sets
    else:
        try:
            return obj[:]  # lists, tuples, strings, unicode
        except TypeError:
            return obj  # ints


def to_json(metrics_store, start_time):
    """ This function writes the metric data to JSON files (and clears the data)

    Args:
        metrics_store (MetricsStore): a store containing metrics tables to dump to file
        start_time (pd.Timestamp): start time of simulation times
    """
    i = 0
    while os.path.isfile('{}{}_metrics.json'.format(metrics_store.file_string, i)):
        i += 1
    filename = '{}{}_metrics.json'.format(metrics_store.file_string, i)
    log.debug('writing out metrics store to json {}'.format(filename))
    _, tables = zip(*sorted(metrics_store.shape_to_tables.items())) if len(metrics_store.shape_to_tables) > 0 else (
    None, [])
    # collect data
    dct = collections.defaultdict(dict)
    for row in zip(metrics_store.time_uid_pairs, *[t.data for t in tables]):
        t, uid = row[0]
        data = [v for subrow in row[1:] for v in subrow]
        dct[t][uid] = data
    # clear out before writing since I'm not sure how much memory is consumed by either (doesn't affect metadata!)
    # then collect metadata
    columns = [c for t in tables for c in t.columns]
    units = [u for t in tables for u in t.units]
    dct['Metadata'] = {c: {'units': json.dumps(us), 'index': i} for i, (c, us) in enumerate(zip(columns, units))}
    dct['StartTime'] = str(start_time)
    # write to file and clear stored data
    with open(filename, 'w') as f:
        json.dump(dct, f, ensure_ascii=False)


def to_hdf(metrics_store, start_time, num_writes_counter):
    """ This function writes the metric data to HDF5 files (and clears the data)

    Args:
        metrics_store (MetricsStore): a store containing metrics tables to dump to file
        start_time (pd.Timestamp): start time of simulation times
        num_writes_counter (int): interval counter
    """

    filename = '{}_metrics.h5'.format(metrics_store.file_string)
    log.debug('writing out metric table for {}th time to hdf {}'.format(num_writes_counter + 1, filename))
    # collect metadata first?
    times, uids = zip(*metrics_store.time_uid_pairs) if len(metrics_store.time_uid_pairs) > 0 else ([], [])
    times = start_time + pd.to_timedelta(times, unit='s')
    # times = start_time + np.asarray([pd.Timedelta(seconds=int(t)) for t in times])
    # it's possible some shape's len is repeated (e.g. shapes (4, 2) and (48, 100) would compete for same key...)
    shape_len_to_count = collections.Counter(map(len, metrics_store.shape_to_tables.keys()))
    log.debug('shape_len_to_count {} for filename {}'.format(shape_len_to_count, filename))
    shape_len_counters = {x: 0 for x in shape_len_to_count.keys()}
    # assumes we never visit this key in this file after this function after the next outer for loop
    # keys_to_index = []
    # now collect data
    for num_local_writes_counter, (shape, table) in enumerate(metrics_store.shape_to_tables.items()):
        num_dims = len(shape)
        df = table.to_frame(times=times, uids=uids, shape=shape, filename=filename)  # index is now ['time', 'uid']
        # write to file and clear stored data
        # revisit mode/append depending on iterating over this with time partition
        # Mode can be 'a' as long as the enter metrics file is written in one shot 
        #  (which it generally is, due to TESP conventions of writing all metrics 
        #  during a metrics collection interval at the end of the interval, typically daily.)
        # More efficiently we could append to a file each day which would require 
        #  changes to the call such that the write mode is not always 'w'.
        log.debug('-----df examination----')
        log.debug('len(shape) = {}, shape {}, df.shape {}, shape_len_counter[len(shape)] {}'.
                  format(num_dims, shape, df.shape, shape_len_counters[num_dims]))
        log.debug('df.head() {}'.format(df.head()))
        # log.debug('df.info() {}'.format(df.info()))

        # appends a letter to key if more than one shape of same len appears for that shape len
        extra = ['', 'a', 'b', 'c', 'd'][shape_len_counters[num_dims]]
        shape_len_counters[num_dims] += 1

        # why not just append to same growing table (by eliminating num_writes_counter)
        key = 'metrics_df{}{}'.format(num_dims, extra)
        if df.shape[0] > 0:
            try:
                df.to_hdf(filename,
                          key=key,
                          # overwrite possibly already existing file only at onset of sim
                          mode='w' if num_local_writes_counter == num_writes_counter == 0 else 'a',
                          # enabling appending to each possibly existing table (setting up for chunking)
                          append=True,  
                          # use 'table' (slower i/o) if indexing and want subsets of data retrievable (not indexing here, perhaps in post-processing
                          format='table',
                          data_columns=['time'],
                          # compress on the fly (can't do at end!)
                          complevel=9,
                          # don't index here (can only do so with 'table') since we may chunk first, then index (possibly in post-processing even)
                          index=False)
            except Exception as e:
                log.error('got error when attempting to write table to hdf {}: {}'.format(filename, e))
        else:
            log.debug('passing on trying to append an empty dataframe to file {}, key {}'.format(filename, key))
        # else:  # if try works, go here
        #     keys_to_index.append(key)
        # delete df before trying to construct next one and reassign to df, since I'm not sure when the old df will be cleared
        del df


def finalize_hdf(metrics_store):
    filename = '{}_metrics.h5'.format(metrics_store.file_string)
    # TODO: decide if we want to index (past time/uid?) and if we want such high levels of compression or indexing opt
    # # once all appends done, run this to create index
    if os.path.isfile(filename):
        log.debug('opening file {} to compress'.format(filename))
        with pd.HDFStore(filename, 'r+', complevel=9) as out_store:
            for key in out_store:
                if 'metrics_df' in key:
                    # 9 is highest; testing with low index?
                    out_store.create_table_index(key, columns=['time'], optlevel=9, kind='full')
                    log.debug('successfully indexed key {}'.format(key))
    else:
        log.warning('No file {} to try and compress at end of sim, passing!'.format(filename))
    # can now access with a simple pd.read_hdf(filename, key, where='time >= pd.Timestamp(...) and uid in [uid1, ...]')

# TODO: move these timeit-enabling functions?
# def setup_factory(n_times, n_uids, n_stores, write_hdf5):
#     def inner():
#         c = MetricsCollectorBase.factory(write_hdf5=write_hdf5)
#         ms = []
#         for i in range(n_stores):
#             ms.append(MetricsStore(
#                 name_units_pairs=[('a', 'foo'), ('b', 'bar'), ('c', [['u', 'u'], ['u', 'u']]), ('d', [['u', 'u'], ['u', 'u']])],
#                 file_string='something{}'.format(i),
#                 collector=c))
#         for t, u, m in itertools.product(range(n_times), range(n_uids), ms):
#             m.append_data(t, 'name{}'.format(u), 1, 2, [[t+u, 2.2], [1, 0]], [[t-u, -3], [5, -0.3]])
#         return c
#     return inner
#
#
# def write_factory(n_times, n_uids, n_stores, write_hdf5):
#     def inner():
#         c = MetricsCollectorBase.factory(write_hdf5=write_hdf5)
#         ms = []
#         for i in range(n_stores):
#             ms.append(MetricsStore(
#                 name_units_pairs=[('a', 'foo'), ('b', 'bar'), ('c', [['u', 'u'], ['u', 'u']]),
#                                   ('d', [['u', 'u'], ['u', 'u']])],
#                 file_string='something{}'.format(i),
#                 collector=c))
#         for t, u, m in itertools.product(range(n_times), range(n_uids), ms):
#             m.append_data(t, 'name{}'.format(u), 1, 2, [[t + u, 2.2], [1, 0]], [[t - u, -3], [5, -0.3]])
#         c.write_metrics()
#     return inner
#
#
# def read_factory(read_hdf5):
#     def inner_hdf5():
#         df0 = pd.read_hdf('something0_metrics.h5', 'metrics_0_df0')
#         df2 = pd.read_hdf('something0_metrics.h5', 'metrics_0_df2')
#         return df0, df2
#
#     def inner_json():
#         with open('something00_metrics.json', 'r') as f:
#             i = json.load(f)
#         return i
#     return inner_hdf5 if read_hdf5 else inner_json
