# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: entity.py

"""
"""

import json
import sqlite3


def assign_defaults(obj, file_name):
    """

    Args:
        obj:
        file_name:

    Returns:

    """
    with open(file_name, 'r', encoding='utf-8') as json_file:
        config = json.load(json_file)
        for attr in config:
            setattr(obj, attr, config[attr])
    return config


def assign_item_defaults(obj, file_name):
    """

    Args:
        obj:
        file_name:

    Returns:

    """
    with open(file_name, 'r', encoding='utf-8') as json_file:
        config = json.load(json_file)
        # config format -> label, value, unit, datatype, item
        for attr in config:
            # Item format -> datatype, label, unit, item, value
            tmp = Item(str(type(config[attr])), attr, "", attr, config[attr])
            setattr(obj, attr, tmp)
    return


class Item:
    def __init__(self, datatype, label, unit, item, value=None, range_check=None):
        self.datatype = datatype
        self.label = label
        self.unit = unit
        self.item = item
        self.value = value
        self.range_check = range_check

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    def __repr__(self):
        return str(self.value)

    # def __str__(self):
    #     return str(self.item)

    def toFrame(self):
        return [self.label, self.value, self.unit, self.datatype, self.item, self.range_check]

    def toJson(self):
        return [self.label, self.value, self.unit, self.datatype, self.item]

    def toJSON(self):
        tmp = '{ ' + self.item + ': {' \
              '"label": "' + self.label + ', ' \
              '"unit": "' + self.unit + ', ' \
              '"datatype": "' + self.datatype + ', ' \
              '"value": '
        if self.datatype in ["TEXT"]:
            tmp = tmp + '"' + self.value + '"}'
        else:  # self.datatype in ["REAL", "INTEGER"]:
            tmp = tmp + self.value + '}'
        return tmp


class Entity:
    def __init__(self, entity, config):
        self.item_cnt = 0
        self.entity = entity
        self.instance = {}
        try:
            if type(config[0]) is list:
                for attr in config:
                    # config format -> label=0, value=1, unit=2, datatype=3, item=4, range
                    # Item format -> datatype=3, label=0, unit=2, item=4, value=1, range
                    if len(attr) > 5:
                        tmp = Item(attr[3], attr[0], attr[2], attr[4], attr[1], attr[5])
                    else:
                        tmp = Item(attr[3], attr[0], attr[2], attr[4], attr[1])
                    setattr(self, attr[4], tmp)
                self.item_cnt = len(config)
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

    def count(self):
        """

        Returns (int): The number of defined Items in the Entity

        """
        return self.item_cnt

    def find_item(self, item):
        """

        Args:
            item:

        Returns (Item):

        """
        try:
            return self.__getattribute__(item)
        except:
            return None

    def set_instance(self, object_name, params):
        """

        Args:
            object_name:
            params:

        Returns:

        """
        if type(object_name) == str:
            try:
                instance = self.instance[object_name]
            except:
                self.instance[object_name] = {}
                instance = self.instance[object_name]

            for attr in params:
                item = self.find_item(attr)
                if type(item) == Item:
                    try:
                        item_instance = instance[attr]
                    except:
                        if type(attr) == str:
                            instance[attr] = {}
                        else:
                            print("Attribute id is not a string in", self.entity, "named", object_name)
                            continue
                else:
                    print("Unrecognized parameter", attr, "in", self.entity, "named", object_name)
                    # add to dictionary datatype, label, unit, item, value
                    self.add_attr("TEXT", attr, "", attr, "")
                instance[attr] = params[attr]
            return instance
        else:
            print("object_name is not a string in", self.entity)
        return None

    def get_instance(self, object_name):
        """

        Args:
            object_name:

        Returns:

        """
        if type(object_name) == str:
            try:
                return self.instance[object_name]
            except:
                self.instance[object_name] = {}
                return self.instance[object_name]
        else:
            print("object name is not a string in", self.entity)
        return None

    def del_instance(self, object_name):
        """

        Args:
            object_name:

        Returns:

        """
        if type(object_name) == str:
            try:
                del self.instance[object_name]
            except:
                # TODO: Need to add error message
                pass
        else:
            print("object name is not a string in", self.entity)
        return None

    def add_attr(self, datatype, label, unit, item, value=None):
        """

        Args:
            datatype:
            label:
            unit:
            item:
            value:

        Returns:

        """
        val = Item(datatype, label, unit, item, value)
        setattr(self, item, val)
        self.item_cnt += 1
        return self.__getattribute__(item)

    def del_attr(self, item):
        """

        Args:
            item:

        Returns:

        """
        if self.find_item(item):
            delattr(self, item)
        return None

    # def set_item_default(self, item, val):
    #     if self.find_item(item):
    #         setattr(self, item, val)
    #         return self.__getattribute__(item)
    #     return None
    #
    # def del_item_default(self, item):
    #     if self.find_item(item):
    #         _item = self.__getattribute__(item)
    #         if type(_item) == Item:
    #             setattr(self, _item, None)
    #             # remove all instances
    #             for object_name in self.instance:
    #                 del self.instance[object_name][_item]
    #     return None

    def set_item(self, object_name, item, val):
        """

        Args:
            object_name:
            item:
            val:

        Returns:

        """
        if self.find_item(item):
            _item = self.__getattribute__(item)
            if type(_item) == Item:
                self.instance[object_name][item] = val
        return None

    def del_item(self, object_name, item):
        """

        Args:
            object_name:
            item:

        Returns:

        """
        if self.find_item(item):
            _item = self.__getattribute__(item)
            if type(_item) == Item:
                del self.instance[object_name][item]
        return None

    def toList(self):
        """

        Returns:

        """
        diction = []
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction.append(attr)
        return diction

    def toJson(self):
        """

        Returns:

        """
        diction = []
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction.append(item.toJson())
        return diction

    def toHelp(self):
        """

        Returns:

        """
        diction = "\nEntity: " + self.entity
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction += "\n  " + item.label + ", code=" + item.item + ", type=" + item.datatype + ", default=" + str(item)
        return diction

    def toSQLite(self, connection):
        """

        Args:
            connection:

        Returns:

        """
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
        """

        Returns:

        """
        diction = ""
        for object_name in self.instance:
            diction += "object " + self.entity + " {\n  name " + object_name + ";\n"
            for item in self.instance[object_name].keys():
                diction += "  " + item + " " + self.instance[object_name][item] + ";\n"
            diction += "}\n"
        return diction

    def instanceToSQLite(self, connection):
        """

        Args:
            connection: A sqlite connection object

        Returns:

        """
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
            for object_name in self.instance:
                for item in self.instance[object_name].keys():
                    sql += multi_row + object_name + "', '" + item + "', '" + self.instance[object_name][item] + "')"
                    multi_row = ", ('"

            sql += ";"
            cursor_obj.execute(sql)
            connection.commit()

        return ""
