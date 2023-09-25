# Copyright (C) 2023 Battelle Memorial Institute
# file: data.py
""" Path and Data functions for use within tesp_support, including new agents.
"""
import os
import re
import csv
import json
import h5py
import sqlite3
import pandas as pd
import numpy as np
import zipfile as zf

#  add empty json "file" store that holds
#  the directory and schemas classes for each file store
#
# {
#   "store": [
#     {
#       "path": <full qualified path and name>',
#       "name": <identifier>,
#       "filetype": <sql, h5, csv>
#       "description": <intent and description of the data file>,
#       "source": <>
#       "schema": [
#         {
#           "name": <identifier>,
#           "columns": [<identifier>, ...],
#           "date": <column identifier> | [<'%Y-%m-%d %H:%M:%S'>, <interval(using pandas freq names)>],
#            other attribute as needed
#         },
#         {...}
#       ],
#     },
#     {
#       "path": <full qualified path>',
#       "name": <identifier>,
#       "filetype": <dir>
#       "description": <intent and description of the data file>,
#       "source": <>
#       "files": [<identifier>, ...}],
#       "directory": [
#         {
#           "name": <identifier>,
#           "recurse": <bool>,
#           "include": [<identifier>, ...],
#         },
#         {...}
#       ],
#     },
#     {...}
#   ]
# }


class Directory:

    def __init__(self, file, description=None):
        """

        Args:
            file:
            description:
        """
        self.ext = "dir"
        self.description = None
        if os.path.isdir(file):
            root = os.path.split(file)
            if root[1] == "":
                root = os.path.split(root[0])
            self.file = file
            self.name = root[1]
        else:
            raise Exception("Sorry, can not read " + file)

        if description is not None:
            self.description = description

        self.recurse = {}
        self.include = {}
        return

    def set_includeDir(self, path, recurse=False):
        if os.path.isdir(os.path.join(self.file, path)):
            self.recurse[path] = recurse
            self.include[path] = []
            return path
        return ""

    def set_includeFile(self, path, mask):
        if os.path.isdir(os.path.join(self.file, path)):
            self.include[path].append(mask)
            return True
        return False

    def get_includeDirs(self):
        directories = []
        for path in self.include:
            directories.append = path
        return directories

    def get_includeFiles(self, path):
        if path in self.include:
            return self.include[path]
        return None

    def zip(self, zipfile):
        for path in self.include:
            zipfile.write(os.path.join(self.file, path), arcname=os.path.join("", path))
            for dir_name, sub_dirs, files in os.walk(os.path.join(self.file, path)):
                if len(self.include[path]) > 0:
                    for mask in self.include[path]:
                        for filename in files:
                            if re.match(mask, filename):
                                name = os.path.join(dir_name, filename)
                                zipfile.write(name, arcname=os.path.join(dir_name.replace(self.file, ""), filename))
                else:
                    for filename in files:
                        name = os.path.join(dir_name, filename)
                        zipfile.write(name, arcname=os.path.join(dir_name.replace(self.file, ""), filename))
                if self.recurse[path]:
                    for directory in sub_dirs:
                        name = os.path.join(dir_name, directory)
                        zipfile.write(name, arcname=os.path.join(dir_name.replace(self.file, ""), directory))
                else:
                    break

    def toJSON(self):
        diction = {"path": self.file,
                   "name": self.name,
                   "filetype": self.ext,
                   "description": self.description,
                   "directory": []}
        for path in self.include:
            sub_dir = {"name": path,
                       "recurse": self.recurse[path],
                       "include": self.include[path]}
            diction["directory"].append(sub_dir)
        return diction


class Schema:

    def __init__(self, file, name=None, description=None):
        """

        Args:
            file:
            name:
            description:
        """
        if os.path.isfile(file):
            root = os.path.split(file)
            ext = os.path.splitext(root[1])
            if ext[1] not in [".csv", ".json", ".db", ".h5"]:
                raise Exception("Sorry, can not read file type " + ext)
        else:
            raise Exception("Sorry, can not read " + file)

        self.file = file
        self.name = name
        self.description = description
        self.ext = ext[1]
        if name is not None:
            self.name = ext[0]
        if description is not None:
            self.description = description
        self.tables = None
        self.columns = {}
        self.dates = {}
        self.skip_rows = {}
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

            if self.ext in [".h5"]:
                f = h5py.File(self.file, 'r')
                self.tables = list(f.keys())
                f.close()
        return self.tables

    def get_columns(self, table, skip_rows=0):
        if not table in self.skip_rows:
            self.skip_rows[table] = skip_rows
        else:
            if skip_rows > 0:
                self.skip_rows[table] = skip_rows

        if table in self.tables:
            if self.ext == ".csv":
                with open(self.file, newline='') as csvfile:
                    for i in range(self.skip_rows[table]):
                        csvfile.readline()
                    reader = csv.DictReader(csvfile)
                    self.columns[table] = reader.fieldnames

            if self.ext in [".db"]:
                con = sqlite3.connect(self.file)
                sql_query = """SELECT * FROM '""" + table + """';"""
                cursor = con.cursor()
                data = cursor.execute(sql_query)
                self.columns[table] = []
                for column in data.description:
                    self.columns[table].append(column[0])
                con.close()

            if self.ext in [".h5"]:
                f = h5py.File(self.file, 'r')
                self.columns[table] = list(f.__getitem__(table).dtype.names)
                f.close()
        return self.columns[table]

    def set_date_bycol(self, table, name):
        if table in self.tables:
            if table in self.columns:
                if name in self.columns[table]:
                    self.dates[table] = name
                    return True
        return False

    # using pandas offset freq alias, H, S, D
    def set_date_byrow(self, table, start, interval):
        if table in self.tables:
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

        if table in self.dates:
            dt = self.dates[table]
        else:
            raise Exception("Sorry, can not read series, invalid dates")

        if table in self.tables:
            if table in self.columns:
                if self.ext == ".csv":
                    if type(dt) == list:
                        df = pd.read_csv(self.file, names=self.columns[table], skiprows=self.skip_rows[table])
                        df['dates'] = pd.date_range(start=dt[0], periods=len(df), freq=dt[1])
                        df[(start < df['dates']) & (df['dates'] < end)]
                    else:
                        df = pd.read_csv(self.file, names=self.columns[table], skiprows=self.skip_rows[table],
                                         parse_dates=True, keep_date_col=True)
                        df = df[(start < df[dt]) & (df[dt] < end)]
                    return df

                if self.ext in [".db"]:
                    con = sqlite3.connect(self.file)
                    sql_query = """SELECT * FROM '""" + table + """';"""
                    df = pd.read_sql_query(sql_query, con, parse_dates={dt: '%Y-%m-%d %H:%M:%S'})
                    df = df[(start < df[dt]) & (df[dt] < end)]
                    # cursor = con.cursor()
                    # data = cursor.execute(sql_query)
                    # for column in data.description:
                    #     self.columns[table].append(column[0])
                    con.close()
                    return df

                if self.ext in [".h5"]:
                    f = h5py.File(self.file, 'r')
                    tbl = np.array(f[table])
                    df = pd.DataFrame(tbl)
                    df[dt] = df[dt].astype('str')
                    pd.to_datetime(df[dt], format='%Y-%m-%d %H:%M:%S PDT')
                    df = df[(start < df[dt]) & (df[dt] < end)]
                    # self.tables = list(f.keys())
                    f.close()
                    return df

        return None

    def toJSON(self):
        diction = {"path": self.file,
                   "name": self.name,
                   "filetype": self.ext,
                   "description": self.description,
                   "schema": []}
        for tbl in self.get_tables():
            skip_rows = 0
            if tbl in self.skip_rows:
                skip_rows = self.skip_rows[tbl]
            table = {"name": tbl,
                     "columns": self.get_columns(tbl),
                     "skip_rows": skip_rows,
                     "date": self.get_date(tbl)}
            diction["schema"].append(table)
        return diction


def unzip(file, path):
    """
    This function unzip take name add .zip and unzip the file to specified path.
    Then finds the store json in that path and fixes the relative path for the stores work
    """
    root = os.path.split(file + ".zip")
    if root[1] == "":
        raise Exception("Sorry, " + file + " is not a file!")
    root = root[1]

    if os.path.isdir(path):
        cwd = os.path.split(path)
        if cwd[1] == "":
            cwd = cwd[0]
        else:
            raise Exception("Sorry, parameter " + path + " is a file!")

    if os.path.isfile(file + ".zip"):
        theZipfile = zf.ZipFile(file+".zip", 'r')
        theZipfile.extractall(cwd)

        # TODO fix up paths
        # if os.path.isfile(cwd + file + ".json"):
        #     meta = json.loads(cwd + file + ".json")
        #     #write(cwd + file + ".json")

    return


class Store:
    def __init__(self, file):
        self.root = file
        self.file = file + '.json'
        self.store = []
        self.read()
        return

    def add_path(self, path, description=""):
        for directory in self.store:
            if type(directory) == Directory:
                if path in directory.file:
                    return directory
        directory = Directory(path, description)
        self.add_directory(directory)
        return directory

    def add_directory(self, directory):
        if type(directory) == Directory:
            self.store.append(directory)
        return

    def del_directory(self, name):
        for i, directory in enumerate(self.store):
            if type(directory) == Directory:
                if directory['name'] == name:
                    del self.store[i]
        return

    def get_directory(self, name):
        if name is None:
            desc = []
            for directory in self.store:
                if type(directory) == Directory:
                    desc.append([directory['name'], directory['description']])
            return desc
        else:
            for i, directory in enumerate(self.store):
                if type(directory) == Directory:
                    if directory['name'] == name:
                        return self.store[i]
        return None

    def add_file(self, path, name="", description=""):
        for schema in self.store:
            if type(schema) == Schema:
                if path in schema.file:
                    return schema
        schema = Schema(path, name, description)
        self.add_schema(schema)
        return schema

    def add_schema(self, scheme):
        if type(scheme) == Schema:
            self.store.append(scheme)
        return

    def del_schema(self, name):
        for i, schema in enumerate(self.store):
            if type(schema) == Schema:
                if schema['name'] == name:
                    del self.store[i]
        return

    def get_schema(self, name=None):
        if name is None:
            desc = []
            for schema in self.store:
                if type(schema) == Schema:
                    desc.append([schema.name, schema.ext, schema.description])
            return desc
        else:
            for schema in self.store:
                if type(schema) == Schema:
                    if schema.name == name:
                        return schema
        return None

    def write(self):
        diction = {"store": []}
        for file in self.store:
            diction["store"].append(file.toJSON())

        with open(self.file, "w", encoding='utf-8') as outfile:
            json.dump(diction, outfile, indent=2)

        return

    def read(self):
        if os.path.isfile(self.file):
            with open(self.file, 'r', encoding='utf-8') as json_file:
                file = json.load(json_file)
                for tmp in file["store"]:
                    if tmp["filetype"] == "dir":
                        try:
                            directory = self.add_path(tmp["path"], tmp["description"])
                            directory.recurse = {}
                            directory.include = {}
                            for table in tmp["directory"]:
                                name = table["name"]
                                if "include" in table:
                                    directory.recurse[name] = table["recurse"]
                                    directory.include[name] = table["include"]
                        except:
                            pass
                    else:
                        try:
                            scheme = self.add_file(tmp["path"], tmp["name"], tmp["description"])
                            scheme.tables = []
                            for table in tmp["schema"]:
                                name = table["name"]
                                scheme.tables.append(name)
                                if "columns" in table:
                                    scheme.columns[name] = table["columns"]
                                if "skip_rows" in table:
                                    scheme.skip_rows[name] = table["skip_rows"]
                                if "date" in table:
                                    scheme.dates[name] = table["date"]
                        except:
                            pass

    def zip(self):
        theZipFile = zf.ZipFile(self.root + '.zip', 'w')
        theZipFile.write(self.file)
        for file in self.store:
            if type(file) == Directory:
                file.zip(theZipFile)
        theZipFile.close()


def _test_debug_resample():
    from .metrics_api import synch_series

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


def _test_csv():
    from .data import tesp_test

    my_store = Store(tesp_test + 'api/store.json')
    my_file = my_store.add_file(tesp_test + 'api/test.csv', "test_csv", "My test csv file")
    tables = my_file.get_tables()
    print(tables)
    columns = my_file.get_columns(tables[0])
    print(columns)
    my_store.write()


def _test_sqlite():
    from .data import tesp_test

    my_store = Store(tesp_test + 'api/store.json')
    my_file = my_store.add_file(tesp_test + 'api/test.db', "test_db", "My test sqlite file")
    tables = my_file.get_tables()
    print(tables)
    columns = my_file.get_columns(tables[0])
    print(columns)
    my_store.write()


def test_hdf5():
    from .data import tesp_test

    my_store = Store(tesp_test + 'api/store.json')
    # 14 houses
    my_file = my_store.add_file(tesp_test + 'api/test_houses_metrics_billing_meter.h5', "test_billing_meter", "My test h5 file")
    tables = my_file.get_tables()
    print(tables)
    columns = my_file.get_columns(tables[1])
    print(columns)
    my_file.set_date_bycol(tables[1], columns[1])
    my_file.set_date_bycol(tables[2], columns[1])

    # 14 houses
    f = h5py.File(my_file.file, 'r')
    n = f.__getitem__(tables[1])[0:13]
    print(n)


    my_store.write()


def _test_read():
    from .data import tesp_test
    from .metrics_api import get_synch_date_range

    my_store = Store(tesp_test + 'api/store.json')
    my_file = my_store.add_file(tesp_test + 'api/test.csv', "test_csv", "My test csv file")
    tables = my_file.get_tables()
    print(tables)
    columns = my_file.get_columns(tables[0])
    print(columns)
    my_store.write()

    my_file.set_date_bycol(tables[0], columns[0])
    my_store.write()
    data = my_file.get_series_data(tables[0], '2016-01-01 00:00', '2017-01-01 00:00')
    tseries = [data]
    print(get_synch_date_range(tseries))

    my_file.set_date_byrow(tables[0], '2016-01-01 00:00', 'H')
    my_store.write()
    data = my_file.get_series_data(tables[0], '2016-01-01 00:00', '2017-01-01 00:00',
                                   usecols=[columns[1], columns[2], columns[3]])
    tseries = [data]
    print(get_synch_date_range(tseries))


def _test_dir():
    from .data import tesp_share
    from .data import tesp_test

    my_store = Store(tesp_test + 'api/store.json')
    my_file = my_store.add_path(tesp_share, "My data directory")
    my_file.set_includeDir("energyplus")
    sub = my_file.set_includeDir("feeders", True)
    my_file.set_includeFile(sub, "IEE*")
    my_file.set_includeFile(sub, "comm*")
    my_file.set_includeFile(sub, ".gitignore")
    my_store.write()
    my_store.zip(tesp_test + 'api/store.zip')


def _test_change_gencost():
    file = os.path.join(os.path.expandvars('$TESPDIR'), 'examples/analysis/dsot/code/system_case_config.json')
    price = {
        "Steam Coal": 61.1,
        "Combined Cycle": 28.9,
        "Combustion Engine": 38.9,
        "Combustion Turbine": 38.9,
        "Steam Turbine": 38.9
    }
    with open(file, 'r', encoding='utf-8') as json_file:
        in_file = json.load(json_file)
        row = 0
        for tmp in in_file["genfuel"]:
            fuel = tmp[1]
            for name in price:
                if name in fuel:
                    in_file["gencost"][row][6] = price[name]
            row = row + 1

    with open(file, "w", encoding='utf-8') as outfile:
        json.dump(in_file, outfile, indent=2)


if __name__ == "__main__":
    _test_debug_resample()
    _test_csv()
    _test_sqlite()
    _test_read()
    _test_dir()
