# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: data.py
""" Path and Data functions for use within tesp_support, including new agents.
"""
import csv
import json
import h5py
import sqlite3

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
#           "name": <identifier>
#           "columns": [<identifier>, ...]
#           "date": index
#           other attribute as needed
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
                raise Exception("Sorry, can read file type")

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

    def get_data(self, table, column, time, range):

        return

    def toJSON(self):
        diction = {"path": self.file,
                   "name": self.name,
                   "filetype": self.ext,
                   "description": self.description,
                   "schema": []}
        for tbl in self.get_tables():
            table = {"name": tbl, "columns": self.get_columns(tbl)}
            diction["schema"].append(table)
        return diction


class Store:
    def __init__(self, file):
        self.file = file
        self.store = []
        return

    def add_file(self, file, name="", description=""):
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

        with open(self.file, "w") as outfile:
            json.dump(diction, outfile, indent=2)

        return


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


if __name__ == "__main__":
    test_csv()
    test_sqlite()
