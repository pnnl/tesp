# Copyright (C) 2023 Battelle Memorial Institute
# file: entity.py
"""
"""

import json
import sqlite3

def assign_defaults(obj, file_name):
    """ Utilities that opens a JSON file and assigns the attributes to the specified object

    Args:
        obj (object): any object like module or class
        file_name (str): a JSON file fully qualified path and name
    Returns:
        dict: a dictionary of the JSON that has been loaded
    """
    with open(file_name, 'r', encoding='utf-8') as json_file:
        config = json.load(json_file)
        for attr in config:
            setattr(obj, attr, config[attr])
    return config

def assign_item_defaults(obj, file_name):
    """ Utilities that opens a JSON file and assigns the attributes Item to the specified object

    Args:
        obj (object): any object like module or class
        file_name (str): a JSON file fully qualified path and name
    Returns:
        dict: a dictionary of the JSON that has been loaded
    """
    with open(file_name, 'r', encoding='utf-8') as json_file:
        config = json.load(json_file)
        # config format -> label, value, unit, datatype, item
        for attr in config:
            # Item format -> datatype, label, unit, item, value
            tmp = Item(str(type(config[attr])), attr, "", attr, config[attr])
            setattr(obj, attr, tmp)
    return config

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
        """ List the attribute in the Items

        Returns:
            dist: with label, value, unit, datatype, name, range_check
        """
        return [self.label, self.value, self.unit, self.datatype, self.item, self.range_check]

    def toList(self):
        """ List the attribute in the Items

        Returns:
            dist: with label, value, unit, datatype, name
        """
        return [self.label, self.value, self.unit, self.datatype, self.item]

    def toJSON(self):
        """ Stringify the attribute in the Items to JSON

        Returns:
            str: JSON string with label, unit, datatype, value
        """
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
        self.instances = {}
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
    #     self.instances = None
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

        Returns:
             int: The number of defined Items in the Entity
        """
        return self.item_cnt

    def find_item(self, item):
        """ Find the Item from the Entity

        Args:
            item (str): name of the attribute in the entity
        Returns:
             Item:
        """
        try:
            return self.__getattribute__(item)
        except:
            return None

    def set_instance(self, object_name, params):
        """ Set the Entity instance the given set of parameters

        Args:
            object_name (str): the name of the instance
            params (list<list>): list of the attribute parameters
        Returns:
            Entity instance: an object with name and values
        """
        if type(object_name) == str:
            try:
                instance = self.instances[object_name]
            except:
                self.instances[object_name] = {}
                instance = self.instances[object_name]

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
                    # add to dictionary datatype, label, unit, item, value
                    if self.find_item("parent") or self.find_item("configuration"):
                        # todo lookup attr in parent, configuration if it exists, for now add it
                        self.add_attr("TEXT", attr, "", attr, "")
                    else:
                        print("Unrecognized parameter", attr, "in", self.entity, "named", object_name)
                instance[attr] = params[attr]
            return instance
        else:
            print("object_name is not a string in", self.entity)
        return None

    def get_instance(self, object_name):
        """ Get the Entity instance

        Args:
            object_name (str): the name of the instance
        Returns:
            Entity instance: an object with name and values or None when object_name is invalid
        """
        if type(object_name) == str:
            try:
                return self.instances[object_name]
            except:
                self.instances[object_name] = {}
                return self.instances[object_name]
        else:
            print("object name is not a string in", self.entity)
        return None

    def del_instance(self, object_name):
        """ Delete the Entity instance

        Args:
            object_name (str): the name of the instance
        """
        if type(object_name) == str:
            try:
                del self.instances[object_name]
            except:
                # TODO: Need to add error message
                pass
        else:
            print("object name is not a string in", self.entity)

    def add_attr(self, datatype, label, unit, item, value=None):
        """ Add the Item attribute to the Entity

        Args:
            datatype (str): Describes the datatype of the attribute
            label (str): Describes the attribute
            unit (str): The unit name of the attribute
            item (str): The name of the attribute
            value (any): The value of the item
        Returns:
            Item:
        """
        val = Item(datatype, label, unit, item, value)
        setattr(self, item, val)
        self.item_cnt += 1
        return self.__getattribute__(item)

    def del_attr(self, item):
        """ Delete the Item from the Entity

        Args:
            item (str): name of the attribute in the Entity
        """
        if self.find_item(item):
            delattr(self, item)

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
    #             for object_name in self.instances:
    #                 del self.instances[object_name][_item]
    #     return None

    def set_item(self, object_name, item, val):
        """ Set the value of the Entity instance for the Item

        Args:
            object_name (str): the name of the instance
            item (str): name of the Item
            val (any): value of the item
        Returns:
            any: the value or None when the value has not been set
        """
        if self.find_item(item):
            _item = self.__getattribute__(item)
            if type(_item) == Item:
                self.instances[object_name][item] = val
                return self.instances[object_name][item]
        return None

    def del_item(self, object_name, item):
        """ Delete the value of the Entity instance from the Item

        Args:
            object_name (str): the name of the instance
            item (str): name of the Item
        """
        if self.find_item(item):
            _item = self.__getattribute__(item)
            if type(_item) == Item:
                del self.instances[object_name][item]

    def toList(self):
        """ List the Item(s) in the Entity

        Returns:
            dict: list of Items in the Entity
        """
        diction = []
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction.append(attr)
        return diction

    def toJson(self):
        """ List the Item(s) in the Entity in json string format

        Returns:
            str: JSON string of the Items in the Entity
        """
        diction = []
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction.append(item.toList())
        return diction

    def toHelp(self):
        """ List the Item(s) in the Entity in help format
        with datatype, label, name, default value

        Returns:
            str: format list of the Items in the Entity
        """
        diction = "\nEntity: " + self.entity
        for attr in self.__dict__:
            item = self.__getattribute__(attr)
            if type(item) == Item:
                diction += "\n  " + item.label + ", code=" + item.item + ", type=" + item.datatype + ", default=" + str(item)
        return diction

    def toSQLite(self, connection):
        """ Create a sqlite table to store the Item(s) in the Entity
         with datatype, label, name, unit, default value

        Args:
            connection (Connection): A valid sqlite connection object
        """
        # cursor object
        cursor_obj = connection.cursor()

        # Drop the named table if already exists.
        sql = """DROP TABLE IF EXISTS """ + self.entity
        cursor_obj.execute(sql)

        # Creating table
        # todo deal with datatype later
        sql = """ CREATE TABLE """ + self.entity + """ (
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

    def instanceToJson(self):
        """ Stringify the instance(s) in the Entity to JSON

        Returns:
            str: JSON string of the instance(s) in the Entity
        """
        diction = ""
        for object_name in self.instances:
            diction += "object " + self.entity + " {\n  name " + object_name + ";\n"
            for item in self.instances[object_name].keys():
                diction += "  " + item + " " + self.instances[object_name][item] + ";\n"
            diction += "}\n"
        return diction

    def instanceToSQLite(self, connection):
        """ Commit the instance(s) in the Entity to SQLite

        Args:
            connection: A valid sqlite connection object
        """
        # cursor object
        cursor_obj = connection.cursor()

        # Drop the named table if already exists.
        sql = """DROP TABLE IF EXISTS """ + self.entity + """_values;"""
        cursor_obj.execute(sql)

        # Creating table
        # todo deal with datatype later
        # how to write for each each data type
        sql = """ CREATE TABLE """ + self.entity + """_values(
                    entity TEXT NOT NULL, 
                    item TEXT NOT NULL,
                    valu BLOB);"""
        cursor_obj.execute(sql)

        if self.instances:
            multi_row = " ('"
            # print(self.entity)
            sql = "INSERT INTO " + self.entity + "_values(entity, item, valu) VALUES"
            for name in self.instances:
                if len(self.instances[name].keys()) > 0:
                    for item in self.instances[name].keys():
                        sql += multi_row + name + "', '" + item + "', '" + self.instances[name][item] + "')"
                        multi_row = ", ('"
                    sql = sql.replace("''", "'")
                else:
                    sql += " ('', '', '')"

            sql += ";"
            # print(sql, flush=True)
            cursor_obj.execute(sql)
            connection.commit()

def _test():

    from .data import feeder_entities_path
    from .data import tesp_test

    class mytest:
        def test(self):
            return

    # entity_names = ["SimulationConfig", "BackboneFiles",  "WeatherPrep", "FeederGenerator",
    #             "EplusConfiguration", "PYPOWERConfiguration", "AgentPrep", "ThermostatSchedule"]
    # entity_names = ['house', 'inverter', 'battery', 'object solar', 'waterheater']

    try:
        conn = sqlite3.connect(tesp_test + 'api/test.db')
        print("Opened database successfully")
    except:
        print("Database Sqlite3.db not formed")

    # this a config  -- file probably going to be static json
    myEntity = mytest()
    assign_defaults(myEntity, feeder_entities_path)
    name = 'rgnPenResHeat'
    print(name)
    print(type(myEntity.__getattribute__(name)))
    print(myEntity.__getattribute__(name))

    # this a config  -- file probably going to be static
    myEntity = mytest()
    assign_item_defaults(myEntity, file_name)
    print(myEntity.rgnPenResHeat.datatype)
    print(myEntity.rgnPenResHeat.item)
    print(myEntity.rgnPenResHeat)
    print(myEntity.rgnPenResHeat.value)

    # Better to use Entity as subclass like substation for metrics
    # Better to use Entity as object models for editing and persistence like glm_model,

    # this a multiple config file a using dictionary list persistence
    file_name = 'glm_classes.json'
    with open(entities_path + file_name, 'r', encoding='utf-8') as json_file:
        entities = json.load(json_file)
        mylist = {}
        for name in entities:
            mylist[name] = Entity(name, entities[name])
            print(mylist[name].toHelp())
            mylist[name].toSQLite(conn)
            # mylist[name].instanceToSQLite(conn)
    conn.close()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    _test()
