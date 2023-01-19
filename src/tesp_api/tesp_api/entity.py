# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: entity.py

"""
"""

import json
import sqlite3

from data import entities_path


def assign_defaults(obj, file_name):
    with open(entities_path + file_name, 'r', encoding='utf-8') as json_file:
        config = json.load(json_file)
        for attr in config:
            setattr(obj, attr, config[attr])
    return


def assign_item_defaults(obj, file_name):
    with open(entities_path + file_name, 'r', encoding='utf-8') as json_file:
        config = json.load(json_file)
        for attr in config:
            # Item format -> datatype, label, unit, item, value
            tmp = Item(str(type(config[attr])), attr, "", attr, config[attr])
            setattr(obj, attr, tmp)
    return


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

    # def __str__(self):
    #     return str(self.item)

    def toJson(self):
        return [self.label, self.value, self.unit, self.datatype, self.item]


class Entity:
    def __init__(self, entity, config):
        self.entity = entity
        self.instance = {}
        try:
            if type(config[0]) is list:
                for attr in config:
                    # config format -> label=0, value=1, unit=2, datatype=3, item=4
                    # Item format -> datatype=3, label=0, unit=2, item=4, value=1
                    tmp = Item(attr[3], attr[0], attr[2], attr[4], attr[1])
                    setattr(self, attr[4], tmp)
        except:
            pass

    # def __init__(self, config):
    #     self.entity = "static"
    #     self.instance = None
    #     for attr in config:
    #         # config format -> label=0, value=1, unit=2, datatype=3, item=4
    #         # Item format -> datatype=3, label=0, unit=2, item=4, value=1
    #         tmp = Item(str(type(config[attr])), attr, "", attr, config[attr])
    #         setattr(self, attr, tmp)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    def __str__(self):
        return str(self.entity)

    def find_item(self, item):
        try:
            return self.__getattribute__(item)
        except:
            return None

    def set_instance(self, obj_id, params):
        if type(obj_id) == str:
            try:
                instance = self.instance[obj_id]
            except:
                self.instance[obj_id] = {}
                instance = self.instance[obj_id]

            for attr in params:
                item = self.find_item(attr)
                if type(item) == Item:
                    try:
                        item_instance = instance[attr]
                    except:
                        if type(attr) == str:
                            instance[attr] = {}
                        else:
                            print("Attribute id is not a string")
                            continue
                else:
                    print("Unrecognized object parameter ->", attr)
                    # add to dictionary datatype, label, unit, item, value
                    self.add_item("TEXT", attr, "", attr, "")
                instance[attr] = params[attr]
            return instance
        else:
            print("Object id is not a string")
        return None

    def get_instance(self, obj_id):
        if type(obj_id) == str:
            try:
                return self.instance[obj_id]
            except:
                self.instance[obj_id] = {}
                return self.instance[obj_id]
        else:
            print("Object id is not a string")
        return None

    def del_instance(self, obj_id):
        if type(obj_id) == str:
            try:
                del self.instance[obj_id]
            except:
                # TODO: Need to add error message
                pass
        else:
            print("Object id is not a string")
        return None

    def add_item(self, datatype, label, unit, item, value=None):
        val = Item(datatype, label, unit, item, value)
        setattr(self, item, val)
        return self.__getattribute__(item)

    def set_item(self, item, val):
        #if self.find_item(item):
        setattr(self, item, val)
        return self.__getattribute__(item)
        #return None

    def del_item(self, obj_id, item):
        setattr(self, item, None)
        del self.instance[obj_id][item]
        return None

    def toJson(self):
        diction = []
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction.append(item.toJson())
        return diction

    def toHelp(self):
        diction = "\nEntity: " + self.entity
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction += "\n  " + item.label + ", code=" + item.item + ", type=" + item.datatype + ", default=" + str(item)
        return diction

    def toSQLite(self, connection):
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
                    valu BLOB);"""
        cursor_obj.execute(sql)

        for field in self.__dict__:
            val = self.__getattribute__(field)
            if type(val) == Item:
                # print(field, "=", val.datatype)
                # Insert record into table
                record = (val.label, val.unit, val.datatype, val.item, val.value)
                sql = """INSERT INTO """ + self.entity + """(label, unit, datatype, item, valu) VALUES(?,?,?,?,?);"""
                cursor_obj.execute(sql, record)
                connection.commit()
        return ""

    def instanceToJson(self):
        diction = ""
        for obj_id in self.instance:
            diction += "object " + self.entity + " {\n  name " + obj_id + ";\n"
            for item in self.instance[obj_id]:
                diction += "  " + item + " " + self.instance[obj_id][item] + ";\n"
            diction += "}\n"
        return diction

    def instanceToGLM(self):
        diction = ""
        for obj_id in self.instance:
            diction += "object " + self.entity + " {\n  name " + obj_id + ";\n"
            #for i in range(len(self.instance[obj_id])):
            for item in self.instance[obj_id].keys():
                diction += "  " + item + " " + self.instance[obj_id][item] + ";\n"
            diction += "}\n"
        return diction

    def instanceToSQLite(self, connection):
        # cursor object
        cursor_obj = connection.cursor()

        # Drop the named table if already exists.
        sql = """DROP TABLE IF EXISTS """ + self.entity + """_values;"""
        cursor_obj.execute(sql)

        # Creating table
        # todo deal with datatype later
        # how to write for each each data type
        sql = """CREATE TABLE """ + self.entity + """_values(
                    entity TEXT NOT NULL, 
                    item TEXT NOT NULL,
                    valu BLOB);"""
        cursor_obj.execute(sql)

        if self.instance:
            multi_row = "('"
            sql = "INSERT INTO " + self.entity + "_values(entity, item, valu) VALUES"
            for obj_id in self.instance:
                for item in self.instance[obj_id]:
                    sql += multi_row + obj_id + "', '" + item + "', '" + self.instance[obj_id][item] + "')"
                    multi_row = ", ('"

            sql += ";"
            cursor_obj.execute(sql)
            connection.commit()

        return ""

