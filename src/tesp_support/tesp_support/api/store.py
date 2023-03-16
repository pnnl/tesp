# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: data.py
""" Path and Data functions for use within tesp_support, including new agents.
"""
import csv
import json
import h5py
import sqlite3
import pandas as pd
import numpy as np

from os import path

tesp_share = path.join(path.expandvars('$TESPDIR'), 'data', '')
comm_path = path.join(tesp_share, 'comm', '')
entities_path = path.join(tesp_share, 'entities', '')
energyplus_path = path.join(tesp_share, 'energyplus', '')
feeders_path = path.join(tesp_share, 'feeders', '')
scheduled_path = path.join(tesp_share, 'schedules', '')
weather_path = path.join(tesp_share, 'weather', '')

tesp_model = path.join(path.expandvars('$TESPDIR'), 'models', '')
pypower_path = path.join(tesp_model, 'pypower', '')


#  add empty json "file" store that holds
#  the files and schemas for each file in that store
#
# {
#   "store": [
#     {
#       "path": <full qualified path and name>',
#       "name": <identifier>,
#       "filetype": <sql, hdf5, csv>
#       "description": <intent and description of the data file>,
#       "schema": [
#         {
#           "name": <identifier>,
#           "columns": [<identifier>, ...],
#           "date": <column identifier> | [<'%Y-%m-%d %H:%M:%S'>, <interval(using pandas freq names)>],
#            other attribute as needed
#         }
#       ]
#     },
#     {...}
#   ]
# }


class Schema:
    def __init__(self, file, name=None, description=None):
        """

        Args:
            file:
            name:
            description:
        """
        ext = ""
        if path.isfile(file):
            root = path.split(file)
            ext = path.splitext(root[1])
            if ext[1] not in [".csv", ".json", ".db", ".hdf5"]:
                raise Exception("Sorry, can not read file type")
        else:
            raise Exception("Sorry, can not read file")

        self.file = file
        self.name = name
        self.ext = ext[1]
        self.description = ""
        if name is not None:
            self.name = ext[0]
        if description is not None:
            self.description = description

        self.tables = None
        self.columns = {}
        self.dates = {}
        return

    def get_tables(self):
        if self.tables is None:
            self.tables = []
            if self.ext in [".csv", ".json"]:
                self.tables.append(self.name)

            if self.ext in [".db"]:
                con = sqlite3.connect(self.file)
                sql_query = """SELECT name FROM sqlite_master WHERE type='table';"""
                cursor = con.cursor()
                cursor.execute(sql_query)
                tbls = cursor.fetchall()
                for tbl in tbls:
                    self.tables.append(tbl[0])
                con.close()

            if self.ext in [".hdf5"]:
                f = h5py.File(self.file, 'r')
                self.tables = list(f.keys())

        return self.tables

    def get_columns(self, table):
        if table in self.tables:
            if table not in self.columns:
                self.columns[table] = []
                if self.ext == ".csv":
                    with open(self.file, newline='') as csvfile:
                        reader = csv.DictReader(csvfile)
                        self.columns[table] = reader.fieldnames

                if self.ext in [".db"]:
                    con = sqlite3.connect(self.file)
                    sql_query = """SELECT * FROM '""" + table + """';"""
                    cursor = con.cursor()
                    data = cursor.execute(sql_query)
                    for column in data.description:
                        self.columns[table].append(column[0])
                    con.close()

                if self.ext in [".hdf5"]:
                    f = h5py.File(self.file, 'r')
                    self.tables = list(f.keys())
        return self.columns[table]

    def set_date_bycol(self, table, name):
        if table in self.tables:
            if table in self.columns:
                if name in self.columns[table]:
                    if table not in self.dates:
                        self.dates[table] = []
                    self.dates[table] = name
                    return True
        return False

    # using pandas offset freq alias, H, S, D
    def set_date_byrow(self, table, start, interval):
        if table in self.tables:
            if table not in self.dates:
                self.dates[table] = []
            self.dates[table] = [start, interval]
            return True
        return False

    def get_date(self, table):
        if table in self.dates:
            return self.dates[table]
        else:
            return ""

    # ┌───────────────────────────────────────────────────────┬────────────────────────────────────────────────────┐
    # │ pandas Implementation                                 │ Description                                        │
    # ├───────────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
    # │ pd.read_csv(..., sep=';')                             │ Read CSV with different separator¹                 │
    # │ pd.read_csv(..., delim_whitespace=True)               │ Read CSV with tab/whitespace separator             │
    # │ pd.read_csv(..., encoding='latin-1')                  │ Fix UnicodeDecodeError while reading²              │
    # │ pd.read_csv(..., header=False, names=['x', 'y', 'z']) │ Read CSV without headers³                          │
    # │ pd.read_csv(..., index_col=[0])                       │ Specify which column to set as the index⁴          │
    # │ pd.read_csv(..., usecols=['x', 'y'])                  │ Read subset of columns                             │
    # │ pd.read_csv(..., thousands='.', decimal=',')          │ Numeric data is in European format (eg., 1.234,56) │
    # └───────────────────────────────────────────────────────┴────────────────────────────────────────────────────┘
    def get_series_data(self, table, start, end, usecols=None, index_col=None):

        dt = None
        if table in self.dates:
            dt = self.dates[table]
        else:
            raise Exception("Sorry, can not read series, invalid dates")

        if table in self.tables:
            if table in self.columns:
                if self.ext == ".csv":
                    if type(dt) == list:
                        df = pd.read_csv(self.file, usecols=usecols, index_col=index_col)
                        df['dates'] = pd.date_range(start=dt[0], periods=len(df), freq=dt[1])
                        df[(start < df['dates']) & (df['dates'] < end)]
                    else:
                        df = pd.read_csv(self.file, usecols=usecols, index_col=index_col, parse_dates=[dt])
                        df = df[(start < df[dt]) & (df[dt] < end)]
                    return df

                if self.ext in [".db"]:
                    con = sqlite3.connect(self.file)
                    sql_query = """SELECT * FROM '""" + table + """';"""
                    cursor = con.cursor()
                    data = cursor.execute(sql_query)
                    for column in data.description:
                        self.columns[table].append(column[0])
                    con.close()

                if self.ext in [".hdf5"]:
                    f = h5py.File(self.file, 'r')
                    self.tables = list(f.keys())

        return None

    def toJSON(self):
        diction = {"path": self.file,
                   "name": self.name,
                   "filetype": self.ext,
                   "description": self.description,
                   "schema": []}
        for tbl in self.get_tables():
            table = {"name": tbl,
                     "columns": self.get_columns(tbl),
                     "date": self.get_date(tbl)}
            diction["schema"].append(table)
        return diction


class Store:
    def __init__(self, file):
        self.file = file
        self.store = []
        self.read()
        return

    def add_file(self, file, name="", description=""):
        for schema in self.store:
            if file in schema.file:
                return schema
        schema = Schema(file, name, description)
        self.add_schema(schema)
        return schema

    def add_schema(self, scheme):
        if type(scheme) == Schema:
            self.store.append(scheme)
        return

    def del_schema(self, name):
        for i, msg in enumerate(self.store):
            if msg['name'] == name:
                del self.store[i]
        return

    def get_schema(self, name):
        for i, msg in enumerate(self.store):
            if msg['name'] == name:
                return self.store[i]
        return None

    def write(self):
        diction = {"store": []}
        for file in self.store:
            diction["store"].append(file.toJSON())

        with open(self.file, "w", encoding='utf-8') as outfile:
            json.dump(diction, outfile, indent=2)

        return

    def read(self):
        with open(self.file, 'r', encoding='utf-8') as json_file:
            file = json.load(json_file)
            for tmp in file["store"]:
                scheme = self.add_file(tmp["path"], tmp["name"], tmp["description"])
                scheme.tables = []
                for table in tmp["schema"]:
                    name = table["name"]
                    scheme.tables.append(name)
                    scheme.columns[name] = []
                    if "columns" in table:
                        for column in table["columns"]:
                            scheme.columns[name].append(column)
                    scheme.dates[name] = []
                    if "date" in table:
                        scheme.dates[name] = table["date"]
            return


# Synchronizes a list of time series dataframes
# Synchronization includes resampling the time series based
# upon the synch_interval and interval_unit entered
def synch_time_series(series_list, synch_interval, interval_unit):
    synched_series = []

    for df in series_list:
        synched_df = df.resample(str(synch_interval) + interval_unit).interpolate()
        synched_series.append(synched_df)
    return synched_series


# Gets the latest start time and the earliest time from a list of time series
def get_synch_date_range(time_series):
    t_start = time_series[0].index[0]
    t_end = time_series[0].index[len(time_series[0].index)-1]
    for tserie in time_series:
        if tserie.index[0] > t_start:
            t_start = tserie.index[0]
        if tserie.index[len(tserie.index) - 1] < t_end:
            t_end = tserie.index[len(tserie.index) - 1]
    return t_start, t_end


# Clips the time series in the list to the same start and stop times
def synch_series_lengths(time_series):
    synched_series = []
    synch_start, synch_end = get_synch_date_range(time_series)
    for tseries in time_series:
        synch_series = tseries.query('index > @synch_start and index < @synch_end')
        synched_series.append(synch_series)
    return synched_series


# Sychronizes the length and time intervals of a list of time series dataframes
def synch_series(time_series, synch_interval, interval_unit):
    clipped_series = []
    synched_series = []
    sampled_series = []
    clipped_series = synch_series_lengths(time_series)
    synched_series = synch_time_series(clipped_series, 1, "T")
    sampled_series = synch_time_series(clipped_series, synch_interval, interval_unit)
    return sampled_series


def test_debug_resample():
    np.random.seed(0)
    tseries = []
    synched_series = []
    start, end = '2000-01-01 22:00:00', '2001-01-01 22:35:00'
    start1, end1 = '2000-01-01 22:05:00', '2001-01-01 22:40:00'
    start2, end2 = '2000-01-01 22:10:00', '2001-01-01 22:45:00'
    start3, end3 = '2000-01-01 22:15:00', '2001-01-01 22:30:00'
    rng = pd.date_range(start, end, freq='1min')
    ts = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    rng = pd.date_range(start1, end1, freq='1min')
    ts1 = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    rng = pd.date_range(start2, end2, freq='1min')
    ts2 = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    rng = pd.date_range(start3, end3, freq='1min')
    ts3 = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    tseries.append(ts1)
    tseries.append(ts2)
    tseries.append(ts3)
    tseries.append(ts)
    synched_series = synch_series(tseries, 2, "T")
    print(tseries[0])


def test_csv():
    my_store = Store(entities_path + 'store.json')
    my_file = my_store.add_file(entities_path + 'test.csv', "test_csv", "My test csv file")
    tables = my_file.get_tables()
    print(tables)
    columns = my_file.get_columns(tables[0])
    print(columns)
    my_store.write()


def test_sqlite():
    my_store = Store(entities_path + 'store.json')
    my_file = my_store.add_file(entities_path + 'test.db', "test_db", "My test sqlite file")
    tables = my_file.get_tables()
    print(tables)
    columns = my_file.get_columns(tables[0])
    print(columns)
    my_store.write()


def test_read():
    my_store = Store(entities_path + 'store.json')
    my_file = my_store.add_file(entities_path + 'test.csv', "test_csv", "My test csv file")
    tables = my_file.get_tables()
    print(tables)
    columns = my_file.get_columns(tables[0])
    print(columns)
    my_store.write()

    my_file.set_date_bycol(tables[0], columns[0])
    my_store.write()
    data = my_file.get_series_data(tables[0], '2016-01-01 00:00', '2017-01-01 00:00')
    tseries = []
    tseries.append(data)
    print(get_synch_date_range(tseries))

    my_file.set_date_byrow(tables[0], '2016-01-01 00:00', 'H')
    my_store.write()
    data = my_file.get_series_data(tables[0], '2016-01-01 00:00', '2017-01-01 00:00',
                                   usecols=[columns[1], columns[2], columns[3]])
    tseries = []
    tseries.append(data)
    print(get_synch_date_range(tseries))




if __name__ == "__main__":
    test_csv()
    test_sqlite()



