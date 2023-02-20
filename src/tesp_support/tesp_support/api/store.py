# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: data.py
""" Path and Data functions for use within tesp_support, including new agents.
"""
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
#           "table": <identifier>
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
    def __init__(self, file, name, description, kind):
        self.file = file
        self.name = name
        self.description = description
        self.kind = kind
        return

    def get_tables(self):
        return

    def get_columns(self, table):
        return

    def get_data(self, table, column, range):
        return

    def toJSON(self):
        return


class Store:
    def __init__(self, file):
        self.store = []
        return

    def add_schema(self, scheme):
        if type(scheme) == Schema:
            self.store.append(scheme)
        return

    def del_schema(self, scheme):
        if type(scheme) == Schema:
            for i, msg in enumerate(self.store):
                if msg['name'] == scheme['name']:
                    del self.store[i]
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
        return




def register_store(file, name, description):
    return
