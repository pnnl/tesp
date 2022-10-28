# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: case_config.py

"""
"""

import json
import sqlite3

from data import entities_path

# 'module climate;'
# 'module connection;'
# 'module generators;'
# 'module residential'


class Values:
    def __init__(self, entity, item, value):
        self.entity = entity
        self.item = item
        self.value = value


class Item:
    def __init__(self, datatype, label, unit, item, value=None):
        self.datatype = datatype
        self.label = label
        self.unit = unit
        self.item = item
        self.value = value
        # self.value = Values(value)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    def __repr__(self):
        return str(self.value)

    def __str__(self):
        return str(self.item)

    def toJson(self):
        return [self.label, self.value, self.unit, self.datatype, self.item]


class Entity:
    def __init__(self, entity, config):
        self.entity = entity
        for row in config:
            tmp = Item(row[3], row[0], row[2], row[4], row[1])
            setattr(self, row[4], tmp)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    def __str__(self):
        return str(self.entity)

    def toJson(self):
        diction = []
        for field in self.__dict__:
            val = self.__getattribute__(field)
            if type(val) == Item:
                diction.append(val.toJson())
        return diction

    def toGLM(self):
        diction = "object " + self.entity + " {\n"
        for field in self.__dict__:
            val = self.__getattribute__(field)
            if type(val) == Item:
                diction += "  " + val.item + "  " + val.value + ";\n"
        diction += "}\n"
        return diction

    def find_item(self, item):
        try:
            return self.__getattribute__(item)
        except:
            return None

    def add_item(self, datatype, label, unit, item, value=None):
        val = Item(datatype, label, unit, item, value)
        setattr(self, item, val)
        return self.__getattribute__(item)

    def del_item(self, item):
        setattr(self, item, None)
        # val = self.__getattribute__(item)
        # val = None
        return None

    def table_print(self):
        print("\nEntity: " + self.entity)
        for item in self.__dict__:
            val = self.__getattribute__(item)
            if type(val) == Item:
                # todo deal with datatype later
                print(val.label + ", code=" + val.item + ", default=" + str(val))
        return None

    def table_diction(self, connection):
        # cursor object
        cursor_obj = connection.cursor()

        # Drop the named table if already exists.
        sql = """DROP TABLE IF EXISTS """ + self.entity
        cursor_obj.execute(sql)

        # Creating table
        # todo deal with datatype later
        sql = """CREATE TABLE """ + self.entity + """ (
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
                # Insert record into table
                record = (val.label, val.unit, val.datatype, val.item, val.value)
                sql = """INSERT INTO """ + self.entity + """(label, unit, datatype, item, valu) VALUES(?,?,?,?,?);"""
                cursor_obj.execute(sql, record)
                conn.commit()

        return ""

    def table_value(self, connection):
        # cursor object
        cursor_obj = connection.cursor()

        # Drop the named table if already exists.
        sql = """DROP TABLE IF EXISTS """ + self.name + """_value;"""
        cursor_obj.execute(sql)

        # Creating table

        # todo deal with datatype later
        #how to write for each each data type


        sql = """CREATE TABLE """ + self.name + """_value (
                    item TEXT NOT NULL,
                    valu """ + BLOB + """);"""
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
    # entity_names = ["SimulationConfig", "BackboneFiles",  "WeatherPrep", "FeederGenerator",
    #             "EplusConfiguration", "PYPOWERConfiguration", "AgentPrep", "ThermostatSchedule"]
    # entity_names = ['house', 'inverter', 'battery', 'object solar', 'waterheater']

    try:
        conn = sqlite3.connect(entities_path + 'test.db')
        print("Opened database successfully")
    except:
        print("Database Sqlite3.db not formed")

    with open(entities_path + 'glm_objects.json', 'r', encoding='utf-8') as json_file:
        entities = json.load(json_file)

    for name in entities:
        mylist[name] = Entity(name, entities[name])
        mylist[name].table_print()
        mylist[name].table_diction(conn)

