"""
"""

import json
import sqlite3

from tesp_support.data import entities_path

# 'module climate;'
# 'module connection;'
# 'module generators;'
# 'module residential'


class Item:
    def __init__(self, datatype, label, unit, item, value=None):
        self.datatype = datatype
        self.label = label
        self.unit = unit
        self.item = item
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    def __repr__(self):
        return str(self.value)


class Entity:
    def __init__(self, name, config):
        self.name = name
        for row in config:
            tmp = Item(row[3], row[0], row[2], row[4], row[1])
            setattr(self, row[4], tmp)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    def print(self):
        # print(vars(self))
        for field in self.__dict__:
            val = self.__getattribute__(field)
            if type(val) == Item:
                print(field, "=", val)
        return ""

    def table(self, connection):
        # cursor object
        cursor_obj = connection.cursor()

        # Drop the named table if already exists.
        sql = """DROP TABLE IF EXISTS """ + self.name
        cursor_obj.execute(sql)

        # Creating table
        sql = """CREATE TABLE """ + self.name + """ (
                    label TEXT NOT NULL,
                    unit TEXT,
                    datatype TEXT NOT NULL,
                    item TEXT NOT NULL,
                    valu BLOB
                );"""
        cursor_obj.execute(sql)

        for field in self.__dict__:
            val = self.__getattribute__(field)
            if type(val) == Item:
                # print(field, "=", val.datatype)
                # Inter record into table
                record = (val.label, val.unit, val.datatype, val.item, val.value)
                sql = """INSERT INTO """ + self.name + """(label, unit, datatype, item, valu) VALUES(?,?,?,?,?);"""
                cursor_obj.execute(sql, record)
                conn.commit()

        return ""


if __name__ == "__main__":

    mylist = {}
    entities = ["SimulationConfig", "BackboneFiles",  "WeatherPrep", "FeederGenerator",
                "EplusConfiguration", "PYPOWERConfiguration", "AgentPrep", "ThermostatSchedule"]
    # , 'house', 'inverter', 'battery', 'object solar', 'waterheater' ...]

    try:
        conn = sqlite3.connect(entities_path + 'test.db')
        print("Opened database successfully")
    except:
        print("Database Sqlite3.db not formed.")

    with open(entities_path + 'master_settings.json', 'r', encoding='utf-8') as json_file:
        config = json.load(json_file)
    for name in entities:
        mylist[name] = Entity(name, config[name])
        mylist[name].print()
        mylist[name].table(conn)

