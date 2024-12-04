# Copyright (C) 2023-2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: glm_model.py
"""GridLAB-D model I/O for TESP api
"""

import pyjson5
import os.path
import re
import sqlite3

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx

from .data import feeders_path
from .data import glm_entities_path
from .entity import Entity
from .parse_helpers import parse_kva
from .helpers import gld_strict_name

class O_Entity(Entity):
    def __init__(self, model, entity, config):
        super().__init__(entity, config)
        self._m = model

    def add(self, name, params):
        return self._m.add_object(self.entity, name, params)

    def delete(self, name):
        self._m.del_object(self.entity, name)

    def items(self):
        return self.instances.items()
    
    def keys(self):
        return self.instances.keys()

    def __getitem__(self, key):
        return self.instances.get(key)

class GLM:
    pass

class GLMModel:
    """ GLMModel class

    Examples miscellaneous for set declarations::

    #set profiler=1
    #set pauseatexit=1
    #set relax_naming_rules=1
    #set suppress_repeat_messages=1

    Examples format value set declarations::

    #set double_format=%+.12lg
    #set complex_format=%+.12lg%+.12lg%c
    #set complex_output_format=RECT

    Example Deltamode set declarations::

    #set deltamode_timestep=100000000       //100 ms
    #set deltamode_maximumtime=60000000000  //1 minute
    #set deltamode_iteration_limit=10       //Iteration limit
    #set deltamode_forced_always=true

    Backbone file should follow order below::

        clock
        #set ...
        #define ...
        #include ...
        module ...
        objects ...
        schedule ...

    Can be used any where::

        #define -> are one line black boxes
        #include -> *.glm files are black boxes
        #ifdef / #endif -> are black boxes
    """

    edge_classes = {'switch': 'red',
                    'fuse': 'blue',
                    'recloser': 'green',
                    'regulator': 'yellow',
                    'transformer': 'orange',
                    'overhead_line': 'black',
                    'underground_line': 'gray',
                    'triplex_line': 'brown',
                    'parent': 'violet'}

    node_classes = {'substation': 'black',
                    'node': 'red',
                    'load': 'blue',
                    'meter': 'green',
                    'triplex_node': 'yellow',
                    'triplex_meter': 'orange',
                    'house': 'brown'}

    # are these edge or node (sectionalizer, series_reactor, capacitor)

    set_declarations = ['profiler', 'iteration_limit', 'randomseed',
                        'relax_naming_rules', 'minimum_timestep',
                        'suppress_repeat_messages', 'pauseatexit',
                        'double_format', 'complex_format', 'complex_output_format',
                        'deltamode_timestep', 'deltamode_maximumtime',
                        'deltamode_iteration_limit', 'deltamode_forced_always']

    def __init__(self):
        # with open(os.path.join(entities_path, 'glm_modules.json'), 'r', encoding='utf-8') as json_file:
        #     self.modules = pyjson5.load(json_file)
        #     for name in self.modules:
        #         self.module_entities[name] = Entity(name, self.modules[name])
        #
        # # define objects that can be in a GLM file
        # with open(os.path.join(entities_path, 'glm_objects.json'), 'r', encoding='utf-8') as json_file:
        #     self.objects = pyjson5.load(json_file)
        #     for name in self.objects:
        #         self.object_entities[name] = Entity(name, self.objects[name])
        self.hash = None
        self.root = None
        self.in_file = ""
        self.out_file = ""
        self.model = {}
        self.glm = GLM()
        self.conn = None
        self.modules = None
        self.objects = None
        self.schedule_types = {}
        self.module_types = []
        self.class_types = []
        self.module_entities = {}
        self.object_entities = {}
        self.set_lines = []
        self.define_lines = []
        self.include_lines = []
        self.inside_comments = dict()
        self.outside_comments = dict()
        self.inline_comments = dict()
        with open(glm_entities_path, 'r', encoding='utf-8') as json_file:
            self.classes = pyjson5.load(json_file)
            entity = Entity("clock", None)
            entity.add_attr("TEXT", "Time zone", "", "timezone", value=None)
            entity.add_attr("TEXT", "Start time", "", "timestamp", value=None)
            entity.add_attr("TEXT", "Start time", "", "starttime", value=None)
            entity.add_attr("TEXT", "Stop time", "", "stoptime", value=None)
            self.module_entities["clock"] = entity
            for module_name in self.classes:
                self.module_types.append(module_name)
                for object_name in self.classes[module_name]:
                    if object_name == "global_attributes":
                        obj = self.classes[module_name][object_name]
                        entity = Entity(module_name, None)
                        for attr in obj:
                            self._add_attr(entity, attr, obj[attr])
                        self.module_entities[module_name] = entity
                    else:
                        obj = self.classes[module_name][object_name]
                        entity = O_Entity(self, object_name, None)
                        entity.add_attr("OBJECT", "Parent", "", "parent", value=None)
                        for attr in obj:
                            self._add_attr(entity, attr, obj[attr])
                        self.object_entities[object_name] = entity
                        setattr(self.glm, object_name, entity)

            # for obj in self.object_entities:
            #     setattr(self.glm, obj, self.object_entities[obj].instances)

    @staticmethod
    def get_datatype(m_type:str):
        if m_type == "double":
            datatype = "REAL"
        elif m_type in ["char8", "char32", "char256", "char1024"]:
            datatype = "TEXT"
        elif m_type in ["int16", "int32", "int64"]:
            datatype = "INTEGER"
        elif m_type in ["enumeration", "set"]:
            datatype = "TEXT"
        elif m_type == "bool":
            datatype = "BOOLEAN"
            unit = "|true|false|"
        elif m_type == "timestamp":
            datatype = "TEXT"
        elif m_type == "complex":
            datatype = "TEXT"
        elif m_type == "complex_array":
            datatype = "TEXT"
        elif m_type == "double_array":
            datatype = "TEXT"
        elif m_type in ["enduse", "loadshape", "object", "parent"]:
            datatype = "OBJECT"
        else:
            datatype = ""
        return datatype

    @staticmethod
    def _add_attr(entity, name, attr):
        # define modules that can be in a GLM file
        # set (bit), enumeration, bool
        # char8, char32, char256, char1024,
        # double, int16, int32, int64,
        # timestamp, complex, complex_array, double_array
        # object(gen,mkt,pwr,res)  name of object
        # loadshape(res), enduse(pwr), function
        # parent classes
        #   pwr: line, link, load, node, powerflow_object, switch, triplex_node
        #   res: residential_enduse

        # unit with define unit or if "enumeration" or "set" use 'keywords' seperated by '|'
        unit = ""
        if "unit" in attr:
            unit = attr["unit"]
        # label with name otherwise the description
        label = name.replace("_", " ").replace(".", " ")
        if "description" in attr:
            label = attr["description"]

        # all attribute must have a type
        if "type" in attr:
            m_type = attr["type"]
            m_datatype = GLMModel.get_datatype(m_type)
            if m_type in ["enumeration", "set"]:
                unit = "|"
                for key in attr["keywords"]:
                    unit += key + "|"
            elif m_type == "bool":
                unit = "|true|false|"
            if m_datatype:
                entity.add_attr(m_datatype, label, unit, name, value=None)
            else:
                print(f"name: {name} type: {m_type}")

    def entitiesToJson(self):
        diction = {}
        for name in self.module_entities:
            diction[name] = self.module_entities[name].toList()
        for name in self.object_entities:
            diction[name] = self.object_entities[name].toList()
        return diction

    def entitiesToHelp(self):
        diction = ""
        for name in self.module_entities:
            diction += self.module_entities[name].toHelp()
        for name in self.object_entities:
            diction += self.object_entities[name].toHelp()
        return diction

    def entitiesToSQLite(self, filename):
        if os.path.isfile(filename):
            try:
                self.conn = sqlite3.connect(filename)
                print("Opened database successfully")
            except:
                raise FileNotFoundError(f"Unable to form database at {filename}")

            for name in self.module_entities:
                self.module_entities[name].toSQLite(self.conn)
            for name in self.object_entities:
                self.object_entities[name].toSQLite(self.conn)
            self.conn.close()
            self.conn = None
            return True
        return False

    def get_InsideComments(self, object_name, item_id):
        """

        Args:
            object_name:
            item_id:
        Returns:
            str: contain the lines that makes up the comment
        """
        comments = ""
        if object_name in self.inside_comments:
            obj_dict = self.inside_comments[object_name]
            if item_id in obj_dict:
                temp_comments = obj_dict[item_id]
                for comment in temp_comments:
                    comments += "  // " + comment + "\n"
        return comments

    def get_InlineComment(self, object_name, item_id):
        """

        Args:
            object_name:
            item_id:
        Returns:
            str: contain the line that makes up item and the comment
        """
        comment = ""
        if object_name in self.inline_comments:
            obj_dict = self.inline_comments[object_name]
            if item_id in obj_dict:
                comment = obj_dict[item_id]
                if comment != "":
                    comment = "  // " + comment
        return comment

    @staticmethod
    def get_diction(obj_entities, object_name, instanceTo, name):
        diction = ""
        ent_keys = obj_entities[object_name].instances.keys()
        if len(ent_keys) > 0:
            diction += instanceTo(obj_entities[object_name], name)
        return diction

    def instanceToModule(self, i_module, module_name):
        """ Adds the comments pulled from the glm file to the new/modified glm file.

        Args:
            i_module:
            module_name:
        Returns:
            str: contains the lines that make up the module
        """
        name = i_module.entity
        diction = ""
        if name in self.outside_comments:
            out_comments = self.outside_comments[i_module.entity]
            for comment in out_comments:
                diction += comment + "\n"
        if len(i_module.instances) > 0:
            if name in ["clock"]:
                diction = name
            elif name in self.module_types:
                diction = "module " + name
            else:
                diction = "class " + name
            keys = i_module.instances[name].keys()
            if len(keys) > 0:
                diction += " {\n"
                diction += self.get_InsideComments(name, 'name')
                for item in i_module.instances[name].keys():
                    diction += self.get_InsideComments(name, item)
                    if i_module.instances[name][item] is None:
                        continue
                    comments = self.get_InlineComment(name, item)
                    diction += "  " + item + " " + str(i_module.instances[name][item]) + ";" + comments + "\n"
                diction += self.get_InsideComments(name, "__last__")
                diction += "}\n"
            else:
                diction += ";\n"
        return diction

    def instanceToObject(self, i_object, object_name):
        """ Adds the comments pulled from the glm file to the new/modified glm file.

        Args:
            i_object:
            object_name:
        Returns:
            str: contains the lines that make up the object
        """
        diction = ""
        if object_name in self.outside_comments:
            out_comments = self.outside_comments[object_name]
            for comment in out_comments:
                diction += comment + "\n"
        diction += "object " + i_object.entity + " {\n"
        diction += self.get_InsideComments(object_name, "name")
        diction += "  name " + object_name + ";\n"
        for item in i_object.instances[object_name].keys():
            diction += self.get_InsideComments(object_name, item)
            if i_object.instances[object_name][item] is None:
                continue
            comments = self.get_InlineComment(object_name, item)
            diction += "  " + item + " " + str(i_object.instances[object_name][item]) + ";" + comments + "\n"
        diction += self.get_InsideComments(object_name, "__last__")
        diction += "}\n\n"
        return diction

    def instancesToGLM(self):
        diction = ""

        # Write the clock
        try:
            if self.module_entities["clock"]:
                diction += self.get_diction(self.module_entities, "clock", self.instanceToModule, "clock")
            diction += "\n"
        except:
            raise AttributeError("No 'clock' defined in model.")

        # Write the sets commands
        for name in self.set_lines:
            diction += name + "\n"
        if len(self.set_lines):
            diction += "\n"

        # Write the define commands
        for name in self.define_lines:
            diction += name + "\n"
        if len(self.define_lines):
            diction += "\n"

        # Write the includes
        for name in self.include_lines:
            diction += name + "\n"
        if len(self.include_lines):
            diction += "\n"

        # Write the modules
        for name in self.module_entities:
            if name not in ["clock"]:
                diction += self.get_diction(self.module_entities, name, self.instanceToModule, name)
        if len(self.module_entities):
            diction += "\n"

        # Write the objects
        # for object_name in self.object_entities:
        #     for name in self.object_entities[object_name].instances:
        #         diction += self.get_diction(self.object_entities, object_name, self.instanceToObject, name)

        # recorder, player, metrics_collector don't apply to the network, there are others
        # this work for the network (powerflow)
        G = self.draw_network()
        power_entities = []
        for node_name in G:
            for object_name in self.object_entities:
                for name in self.object_entities[object_name].instances:
                    if node_name == name:
                        if node_name in power_entities:
                            continue
                        diction += self.get_diction(self.object_entities, object_name, self.instanceToObject, name)
                        power_entities.append(name)

        # Write the objects
        for object_name in self.object_entities:
            for name in self.object_entities[object_name].instances:
                if name not in power_entities:
                    diction += self.get_diction(self.object_entities, object_name, self.instanceToObject, name)

        # Write the schedules
        for name in self.schedule_types:
            for line in self.schedule_types[name]:
                diction += line + "\n"
            diction += "\n"
        return diction

    def instancesToSQLite(self, filename):
        if os.path.isfile(filename):
            try:
                self.conn = sqlite3.connect(filename)
                print("Opened database successfully")
            except:
                raise FileNotFoundError(f"Unable to form database at {filename}")
            for name in self.module_entities:
                self.module_entities[name].instanceToSQLite(self.conn)
            for name in self.object_entities:
                self.object_entities[name].instanceToSQLite(self.conn)
            self.conn.close()
            self.conn = None
            return True
        return False

    def set_module_instance(self, mod_type, params):
        if type(mod_type) == str:
            try:
                entity = self.module_entities[mod_type]
                return entity.set_instance(mod_type, params)
            except:
                print("Unrecognized GRIDLABD module:", mod_type, "must be a new class")
                self.class_types.append(mod_type)
                entity = self.module_entities[mod_type] = Entity(mod_type, None)
                for items in params:
                    if items in ["integer", "double", "string"]:
                        entity.add_attr('TEXT', items[0], "", items[0], "")
                    return entity.set_instance(mod_type, params)
        else:
            raise TypeError(f"{mod_type} must be a string and is not.")
        return None

    def get_module_instance(self, mod_type):
        if type(mod_type) == str:
            try:
                entity = self.module_entities[mod_type]
                return entity.get_instance(mod_type)
            except:
                print("Unrecognized GRIDLABD module:", mod_type)
        else:
            raise TypeError(f"{mod_type} must be a string and is not.")
        return None

    def set_object_instance(self, obj_type, object_name, params):
        # for attr in params:
        #     item = entity.find_item(attr)
        #     self.instances = {}
        #     instance = self.instances[object_name]
        #     if type(item) == entity.Item:
        #         try:
        #             _ = instance[attr]
        #         except:
        #             if type(attr) == str:
        #                 instance[attr] = {}
        #             else:
        #                 print("Attribute id is not a string in", entity, "named", object_name)
        #                 continue
        if type(obj_type) == str and type(object_name) == str:
            try:
                entity = self.object_entities[obj_type]
            except:
                print("Unrecognized GRIDLABD object and id:", obj_type, object_name, ", must be a new object")
                if obj_type in self.class_types:
                    entity = self.object_entities[obj_type] = O_Entity(obj_type, self.objects[obj_type])
                    for items in params:
                        entity.add_attr('TEXT', items[0], "", items[0], "")
                else:
                    print("Unrecognized user class/object and id:", obj_type, object_name)
                    return None
            return entity.set_instance(object_name, params)
        else:
            raise TypeError("GRIDLABD object type and/or object name {obj_type} must be a string and is not.")

    def get_object_instance(self, obj_type, object_name):
        if type(obj_type) == str and type(obj_type) == str:
            try:
                entity = self.object_entities[obj_type]
                return entity.get_instance(object_name)
            except:
                print("Unrecognized GRIDLABD object and id:", obj_type, object_name)
        else:
            raise TypeError("GRIDLABD object type and/or object name {obj_type} must be a string and is not.")
        return None

    def is_edge_class(self, s):
        """ Edge class is networkx terminology. In GridLAB-D, we will represent those with
        the variable 'edge_classes' define in this model

        Args:
            s (str): the GridLAB-D class name
        Returns:
            bool: True if an edge class, False otherwise
        """
        if s in self.edge_classes.keys():
            return True
        return False

    def is_node_class(self, s):
        """Node class is networkx terminology. In GridLAB-D, we will represent those nodes with
        the variable 'node_classes' define in this model

        Node class is networkx terminology. In GridLAB-D, node classes are in node_class.
        Args:
            s (str): the GridLAB-D class name
        Returns:
            bool: True if a node class, False otherwise
        """
        if s in self.node_classes.keys():
            return True
        return False

    def add_class(self, class_name:str, value_type:str, value_name:str, static:bool, default:any):
        if class_name not in self.module_entities.keys():
            # don't add class_name to self.module_types
            # this makes 'this' a class' in the module_entities list
            entity = Entity(class_name, None)
            entity.add_attr("TEXT", value_type, "", value_type, value="value")
            self.module_entities[class_name] = entity
            setattr(self.glm, class_name, self.module_entities[class_name].instances)
            self.set_module_instance(class_name, {value_type: "value"})

            entity = Entity(class_name, None)
            entity.add_attr("TEXT", "name", "", "name", value=value_name)
            entity.add_attr("TEXT", "file", "", "file")
            entity.add_attr("TEXT", "value", "", "value")
            self.object_entities[class_name] = entity
            setattr(self.glm, class_name, self.object_entities[class_name].instances)
            if static:
                self.set_object_instance(class_name, value_name, {"value": default})
            else:
                self.set_object_instance(class_name, value_name, {"file": default})

    def add_object(self, _type, name, params):
        # add the new object type to the model
        if _type not in self.model:
            self.model[_type] = {}
        # add name and set object entity instance to model type
        # self.model[_type][name] = {}
        self.model[_type][name] = self.set_object_instance(_type, name, params)
        return self.model[_type][name]

    def del_object(self, _type, name):
        # del name and set object entity instance to model type
        del self.model[_type][name]

    def glm_schedule(self, line, itr):
        # This only grab the lines, real parsing of the schedule

        m_sched = re.search('schedule\W+(\w+)\s*([;{])', line, re.IGNORECASE)
        if m_sched:
            # schedule found
            self.schedule_types[m_sched.group(1)] = []
            self.schedule_types[m_sched.group(1)].append(line)
            if m_sched.group(2) == '{':
                # multi-line schedule
                oend = 1
                tab = ["  "]
                while oend:
                    line = next(itr)
                    if re.search('}', line):
                        # end of the schedule
                        tab.remove("  ")
                        oend -= 1
                    self.schedule_types[m_sched.group(1)].append(''.join(tab) + line)
                    if re.search('{', line):
                        # start of the sub schedule
                        tab.append("  ")
                        oend += 1
        return m_sched.group(1)

    def glm_module(self, mod, line, itr):
        """ Store a clock/module/class in the model structure

        Args:
            mod (str): glm type [date, class, module]
            line (str): glm line containing the object definition
            itr (iter): iterator over the list of lines
        Returns:
            str: the module type
        """

        # Collect parameters
        _type = ""
        params = {}
        # Collect comments
        comments = []
        inside_comments = dict()
        inline_comments = dict()

        # Set the clock to date module
        if mod in ["date"]:
            line = mod + " " + line

        # Identify the object type
        if line.find(";") > 0:
            m = re.search(mod + ' ([^;\s]+)[;\s]', line, re.IGNORECASE)
            _type = m.group(1)
            self.set_module_instance(_type, params)
            return _type

        if line.find("{") > 0:
            m = re.search(mod + ' ([^{\s]+)[{\s]', line, re.IGNORECASE)
            _type = m.group(1)

        pos = line.find("//")
        if pos > 0:
            substring = line[pos + 2:].strip()
            comments.append(substring)

        done = False
        line = next(itr).strip()
        while not done:
            # find a comment
            pos = line.find("//")
            if pos == 0:
                substring = line[pos + 2:].strip()
                comments.append(substring)
                line = ";"
            elif pos > 0:
                substring = line[pos + 2:].strip()
                tokens = line.split(" ")
                inline_comments[tokens[0]] = substring

            # find a parameter
            m = re.match('\s*(\S+) ([^;]+);', line)
            if m:
                params[m.group(1)] = m.group(2)
                if len(comments) > 0:
                    inside_comments[m.group(1)] = comments
                    comments = []
            if re.search('}', line):
                done = 1
            else:
                line = next(itr).strip()

        self.set_module_instance(_type, params)

        if len(comments) > 0:
            inside_comments['__last__'] = comments
        if len(inside_comments) > 0:
            self.inside_comments[_type] = inside_comments
        if len(inline_comments) > 0:
            self.inline_comments[_type] = inline_comments
        return _type

    def glm_object(self, parent, line, itr, oidh, counter):
        """ Store an object in the model structure

        Args:
            parent (str): name of parent object (used for nested object defs)
            line (str): glm line containing the object definition
            itr (iter): iterator over the list of lines
            oidh (dict): hash of object id's to object names
            counter (int): object counter
        Returns:
            str, int, str: the current line, counter, name
        """
        # Identify the object type
        oid = ""
        m = re.search('object ([^:{\s]+)[:{\s]', line, re.IGNORECASE)
        _type = m.group(1)
        # If the object has an id number, store it
        n = re.search('object ([^:]+:[^{\s]+)', line, re.IGNORECASE)
        if n:
            oid = n.group(1)
        # else:
        #     print("ERROR: Name defined for object " + _type)
            # quit()

        # Collect parameters
        counter += 1
        name = None
        name_prefix = ''
        params = {}
        # Collect comments
        comments = []
        object_comments = []
        inside_comments = dict()
        inline_comments = dict()
        done = False

        pos = line.find("//")
        if pos > 0:
            substring = line[pos + 2:].strip()
            object_comments.append(substring)

        line = next(itr)
        if len(parent):
            params['parent'] = parent
        while not done:
            pos = line.find("//")
            if pos == 0:
                substring = line[pos + 2:].strip()
                comments.append(substring)
                line = ";"
            elif pos > 0:
                substring = line[pos + 2:].strip()
                tokens = line.split(" ")
                if tokens[0].lower() != 'object':
                    inline_comments[tokens[0]] = substring

            intobj = 0
            m = re.match('\s*(\S+) ([^;{]+)[;{]', line)
            if m:
                param = m.group(1)
                val = m.group(2)
                if param == 'name':
                    # found a parameter name
                    name = gld_strict_name(name_prefix + val)
                    if len(object_comments) > 0:
                        inside_comments['name'] = object_comments
                        object_comments = []
                elif param == 'object':
                    # found a nested object
                    intobj += 1
                    if name is None:
                        raise RuntimeError("nested object defined before parent name")
                    line, counter, lname = self.glm_object(name, line, itr, oidh, counter)
                else:
                    # found a parameter val
                    if val == "$":
                        # found $ command
                        pos = line.find("{")
                        pos1 = line.find(";")
                        val = val + line[pos:pos1]
                        line = ""
                    if param in ["to", "from", "configuration", "parent"]:
                        val = gld_strict_name(name_prefix + val)
                    params[param] = val.strip()
                    if len(comments) > 0:
                        inside_comments[param] = comments
                        comments = []

            if re.search('}', line):
                if intobj:
                    intobj -= 1
                    line = next(itr)
                else:
                    done = True
            else:
                line = next(itr)
        # if undefined, use a default name
        if name is None:
            name = name_prefix + _type + "_" + str(counter)
            if len(object_comments) > 0:
                inside_comments['name'] = object_comments
        oidh[name] = name
        # hash an object identifier to the object name
        if n:
            oidh[oid] = name
        # add the new object type to the model
        self.add_object(_type, name, params)

        if len(comments) > 0:
            inside_comments['__last__'] = comments
        if len(inside_comments) > 0:
            self.inside_comments[name] = inside_comments
        if len(inline_comments) > 0:
            self.inline_comments[name] = inline_comments
        return line, counter, name

    def readModel(self, filename):
        """ Reads and parses the model from the provided filename.

        Args:
            filename (str): fully qualified model path/name

        Returns:
            bool: Indicates whether the model was read-in successfully.
        """

        name = ""
        counter = 0
        h = {}  # OID hash
        lines = []
        self.model = {}
        self.set_lines = []
        self.define_lines = []
        self.include_lines = []
        outside_comments = []
        if os.path.isfile(filename):
            ip = open(filename, 'r')
            line = ip.readline()
            while line != '':
                line = line.replace("\t", " ")
                # skip white space lines
                while re.match('\s+$', line):
                    line = ip.readline()
                line = line.strip()
                if len(line) > 0:
                    lines.append(line)
                line = ip.readline()
            ip.close()

            itr = iter(lines)
            for line in itr:
                if re.match('^//', line):
                    if re.search('#set', line):
                        self.set_lines.append(line)
                    elif re.search('#include', line):
                        self.include_lines.append(line)
                    elif re.search('#define', line):
                        self.define_lines.append(line)
                    else:
                        outside_comments.append(line)
                elif re.search('#set', line):
                    self.set_lines.append(line)
                elif re.search('#include', line):
                    self.include_lines.append(line)
                elif re.search('#define', line):
                    self.define_lines.append(line)
                elif re.search('clock', line):
                    name = self.glm_module("date", line, itr)
                elif re.search('class', line):
                    name = self.glm_module("class", line, itr)
                elif re.search('module', line):
                    name = self.glm_module("module", line, itr)
                elif re.search('schedule', line):
                    name = self.glm_schedule(line, itr)
                elif re.search('object', line):
                    line, counter, name = self.glm_object("", line, itr, h, counter)
                else:
                    print('Un-parsed line "' + line + '"')

                if name != "":
                    if len(outside_comments) > 0:
                        self.outside_comments[name] = outside_comments
                    outside_comments = []
                    name = ""
            self.hash = h
            return True
        else:
            raise FileNotFoundError(f"{filename} not found")

    def readBackboneModel(self, root_name):
        filename = os.path.join(feeders_path, root_name)
        if self.readModel(filename):
            self.root = root_name
            self.in_file = filename
            return self.glm, True
        self.in_file = filename
        self.model = {}
        return None, False

    def read(self, filename):
        if self.readModel(filename):
            root = os.path.split(filename)
            self.root = root[1]
            self.in_file = filename
            return self.glm, True
        self.in_file = filename
        self.model = {}
        return None, False

    def write(self, filepath):
        try:
            op = open(filepath, "w+")
        except:
            raise FileNotFoundError(f"{filepath} unable to be opened for writing")

        # we can write using instance objects
        print(self.instancesToGLM(), file=op)
        op.close()
        return True

    def draw_network(self):
        # construct a graph of the model, starting with known links
        G = nx.Graph()
        for t in self.model:
            # Grabs all nodes that have physical connections in the model
            # (e.g. line, transformer, switch, ...)
            if self.is_edge_class(t):
                for o in self.model[t]:
                    n1 = self.model[t][o]['from']
                    n2 = self.model[t][o]['to']
                    G.add_edge(n1, n2, eclass=t, ename=o, edata=self.model[t][o])

            # Creates edges for nodes that were associated via parent-child
            # relationships. These relationships have no edge data associate
            # with them as the connection is, as far as the GLD model is
            # concerned, virtual, rather than physical.
            if self.is_node_class(t):
                for o in self.model[t]:
                    if 'parent' in self.model[t][o]:
                        p = self.model[t][o]['parent']
                        G.add_edge(o, p, eclass='parent', ename=o, edata={})

        # now we back-fill the node attributes because 'add_edge' adds the nodes
        for t in self.model:
            if self.is_node_class(t):
                for o in self.model[t]:
                    if o in G.nodes():
                        G.nodes()[o]['nclass'] = t
                        G.nodes()[o]['ndata'] = self.model[t][o]
                    else:
                        print('orphaned node', t, o)
        return G

    def plot_model(self, pos=None, node_labels=False, edge_labels=False, node_legend=True, edge_legend=True):

        def update_annot(ind):
            _node_idx = ind["ind"][0]
            _node = idx_to_node_dict[_node_idx]
            _xy = pos[_node]
            annot.xy = _xy
            node_attr = {'node': _node}
            node_attr.update(G.nodes[_node])
            text = '\n'.join(f'{_k}: {_v}' for _k, _v in node_attr.items())
            text = text.replace(', ', '\n').replace('ndata: {', '').replace('}', '')
            text = text.replace('nclass', 'class').replace("'", '')
            annot.set_text(text)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = n1.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()

        def plot_node_legend():
            def make_node_proxy(nm, mappable, **kwargs):
                clr = self.node_classes[nm]
                return Line2D([], [], color="white", marker="o", markerfacecolor=clr, **kwargs)

            l_proxies = [make_node_proxy(nm, n1, lw=self.node_classes.__len__()) for nm in self.node_classes]
            l_labels = ["{}".format(nm) for nm in self.node_classes]
            legend1 = plt.legend(l_proxies, l_labels, loc="upper right", fontsize=8)
            plt.gca().add_artist(legend1)

        def plot_edge_legend():
            def make_edge_proxy(nm, mappable, **kwargs):
                clr = self.edge_classes[nm]
                return Line2D([], [], color="white", marker="s", markerfacecolor=clr, **kwargs)

            l_proxies = [make_edge_proxy(nm, e1, lw=self.edge_classes.__len__()) for nm in self.edge_classes]
            l_labels = ["{}".format(nm) for nm in self.edge_classes]
            legend1 = plt.legend(l_proxies, l_labels, loc="lower right", fontsize=8)
            plt.gca().add_artist(legend1)

        G = self.draw_network()

        # Nodes colors and labels
        nc = []
        nlb = {}
        for u, v in G.nodes(data=True):
            try:
                nc.append(self.node_classes[v['nclass']])
                nlb[u] = u
            except:
                continue

        # Edges colors and attributes
        ec = []
        elb = {}
        for u, v in G.edges():
            ec.append(self.edge_classes[G[u][v]['eclass']])
            elb[u, v] = G[u][v]['ename']

        # Draw
        fig, ax = plt.subplots(num=(self.root + " network"))
        if pos is None: ## If no coordinate data is provided
            pos = nx.kamada_kawai_layout(G)
        n1 = nx.draw_networkx_nodes(G, pos, ax=ax, node_size=20, node_color=nc)
        e1 = nx.draw_networkx_edges(G, pos, ax=ax, edge_color=ec)
        if node_labels:
            n2 = nx.draw_networkx_labels(G, pos, ax=ax, labels=nlb)
        if edge_labels:
            e2 = nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=elb)

        # Annotate and connect event handler
        annot = ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)
        idx_to_node_dict = {}
        for idx, node in enumerate(G.nodes):
            idx_to_node_dict[idx] = node
        fig.canvas.mpl_connect("motion_notify_event", hover)

        # Add legends
        if node_legend:
            plot_node_legend()
        if edge_legend:
            plot_edge_legend()

        plt.subplots_adjust(left=0.01, bottom=0.01, right=0.99, top=0.99)
        plt.show()

    def set_clock(self, starttime: str, stoptime: str, timezone: str):
        clock = self.module_entities['clock'].instances['clock']
        clock['starttime'] = "'" + starttime + "'"
        clock['stoptime'] = "'" + stoptime + "'"
        clock['timezone'] = timezone
        del clock['timestamp'] #remove timestamp, conflicts with starttime

    def add_include(self, file: str):
        self.include_lines.append(f"#include \"{file}\"")

    def del_include(self, file: str):
        self.include_lines.remove(f"#include \"{file}\"")

    def add_set(self, name: str, value: any):
        self.set_lines.append(f"#set {name}={value}")

    def del_set(self, name: str):
        find = f"#set {name}="
        for idx in range(len(self.set_lines)):
            if find in self.set_lines[idx]:
                del self.set_lines[idx]

    def add_define(self, name:str, value: any):
        self.define_lines.append(f"#define {name}={value}")

    def del_define(self, name:str):
        find = f"#define {name}="
        for idx in range(len(self.define_lines)):
            if find in self.define_lines[idx]:
                del self.define_lines[idx]

    @staticmethod
    def union_of_phases(phs1, phs2):
        """Collect all phases on both sides of a connection

        Args:
            phs1 (str): first phasing
            phs2 (str): second phasing

        Returns:
            str: union of phs1 and phs2
        """
        phases = ['A', 'B', 'C', 'S']
        phs = ''
        for phase_type in phases:
            if phase_type in phs1 or phase_type in phs2:
                phs += phase_type
        return phs

    @staticmethod
    def accumulate_load_kva(data: dict) -> float:
        """Add up the total kva in a load-bearing object instance

        Considers constant_power_A/B/C/1/2/12 and power_1/2/12 attributes

        Args:
            data (dict): dictionary of data for a selected GridLAB-D instance

        Returns:
            kva (float): total kva in a load-bearing object instance
        """
        power = ['constant_power_A', 'constant_power_B', 'constant_power_C',
                 'constant_power_1', 'constant_power_2', 'constant_power_12',
                 'power_1', 'power_2', 'power_12']
        kva = 0.0
        for power_type in power:
            if power_type in data:
                kva += parse_kva(data[power_type])
        return kva

    def identify_seg_loads(self):
        """Estimates loads on segments (i.e. lines, edges) in the model

        Iterates over all loads in the network and uses the networkx model of
        the network to identify the shortest path (the least number of edges or
        lines) between the load and the swing node (the source of the power).
        This method assumes that this is the path the power will flow over
        which is not generally true (especially in a meshed network), but 
        is likely to be true for radial models.

        Once the path of the power flow is identified, the power of the load
        is added to each line and stored in a dictionary along with
        the affected phases. In this manner an estimate of the loading on each
        line is found by inspecting the model without running a simulation.

        Args:
            self (GLMModel)

        Returns:
            dict: key - name of line in model 
                  value - list with members of
                            - accumulated load
                            - all affected phases
        """
        swing_node = ''
        G = self.draw_network()

        # Identify swing node in GridLAB-D model
        for n1, data in G.nodes(data=True):
            if 'nclass' in data:
                if 'bustype' in data['ndata']:
                    if data['ndata']['bustype'] == 'SWING':
                        swing_node = n1
                        break

        # Finds the load on each segment (i.e. edge, line) by iterating over all 
        # load definitions, identifying all affected lines and adding the load
        # to those lines.            
        seg_loads = {}  # [name][kva, phases]
        total_kva = 0.0
        for n1, data in G.nodes(data=True):
            if 'ndata' in data:
                kva = self.accumulate_load_kva(data['ndata'])
                # need to account for large-building loads added through transformer connections
                if kva > 0:
                    total_kva += kva
                    nodes = nx.shortest_path(G, n1, swing_node)
                    edges = zip(nodes[0:], nodes[1:])
                    for u, v in edges:
                        eclass = G[u][v]['eclass']
                        if self.is_edge_class(eclass):
                            ename = G[u][v]['ename']
                            if ename not in seg_loads:
                                seg_loads[ename] = [0.0, '']
                            seg_loads[ename][0] += kva
                            seg_loads[ename][1] = self.union_of_phases(seg_loads[ename][1], data['ndata']['phases'])

                            # Band-aid for poor accumulation of phase information for parrallel curcuits
                            # "ABCS" is not a valid phase set and should be "ABCN".
                            # seg_phs = seg_phs.replace('ABCS', 'ABCN')
                            seg_loads[ename][1] = seg_loads[ename][1].replace('ABCS', 'ABCN')
                        else:
                            print(f"Unknown edge class: {eclass}")
        # sub_graphs = nx.connected_components(G)
        # print(f"  swing node {swing_node}, with {len(list(sub_graphs))}, sub graphs and {:.2f}.format(total_kva)} total kva")
        
        return seg_loads





def _test1():
    from .data import tesp_test

    # Test model_GLM.py
    model_file = GLMModel()
    if model_file.readBackboneModel("R1-12.47-1.glm"):
    # if model_file.read(feeders_path + "GLD_three_phase_house.glm"):
        # Output json with new parameters
        model_file.write(tesp_test + "api/R1-12.47-1_out.glm")

    model_file = GLMModel()
    if model_file.readModel(tesp_test + "api/testing.glm"):
        model_file.write(tesp_test + "api/model_out.glm")

        model_file.instancesToSQLite(tesp_test + 'api/model_out.db')
        print(model_file.entitiesToHelp())
        print(model_file.instancesToGLM())

        op = open(tesp_test + 'api/model_out.json', 'w', encoding='utf-8')
        pyjson5.dump(model_file.entitiesToJson(), op, ensure_ascii=False, indent=2)
        op.close()


def _test2():
    testMod = GLMModel()
    if testMod.read(feeders_path + "R1-12.47-1.glm"):
        for name in testMod.module_entities:
            print(testMod.module_entities[name].toHelp())
        for name in testMod.object_entities:
            print(testMod.object_entities[name].toHelp())


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    _test1()
    _test2()
