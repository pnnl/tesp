# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: glm_model.py
"""GridLAB-D model I/O for TESP api

Public Functions:
"""

import json
import os.path
import re
import sqlite3

import networkx as nx

from tesp_support.api.store import entities_path
from tesp_support.api.entity import Entity


class GLModel:
    # it seems to public for all GLMODEL class
    in_file = ""
    out_file = ""
    model = {}
    modules = None
    objects = None
    object_entities = {}
    module_entities = {}
    network = nx.Graph()
    set_lines = []
    define_lines = []
    include_lines = []
    inside_comments = dict()
    outside_comments = dict()
    inline_comments = dict()
    edge_class = ['switch', 'fuse', 'recloser', 'regulator', 'transformer',
                  'overhead_line', 'underground_line', 'triplex_line']
    node_class = ['node', 'load', 'meter', 'triplex_node', 'triplex_meter']

    """
        backbone file must follow order below 
            clock 
            set [profile,
            module ...
            objects ...

        Can be used any where    
            #define and #ifdef are black boxes 
            // are one line black boxes

    # clock {
    #   timezone EST + 5 EDT;
    #   starttime '2000-01-01 0:00:00';
    #   stoptime '2000-01-01 5:59:00';
    # }

    # set relax_naming_rules=1
    # set profiler=1
    # set minimum_timestep=1

    # module climate;
    # module connection;
    # module generators;
    # module residential;
    # module tape;

    # module powerflow {
    #   solver_method NR;
    #   line_capacitance true;
    # }

    # module reliability {
    #   maximum_event_length 18000;
    #   report_event_log true;
    # }

    """

    def __init__(self):
        # define objects that can be in a GLM file
        try:
            self.conn = sqlite3.connect(os.path.join(entities_path, 'testglm.db'))
            print("Opened database successfully")
        except:
            self.conn = None
            print("Database Sqlite3.db not formed")

        with open(os.path.join(entities_path, 'glm_modules.json'), 'r', encoding='utf-8') as json_file:
            self.modules = json.load(json_file)
        with open(os.path.join(entities_path, 'glm_objects.json'), 'r', encoding='utf-8') as json_file:
            self.objects = json.load(json_file)

        for name in self.modules:
            self.module_entities[name] = Entity(name, self.modules[name])
        for name in self.objects:
            self.object_entities[name] = Entity(name, self.objects[name])
            # self.object_entities[name].toSQLite(self.conn)

    def entitiesToJson(self):
        diction = {}
        for name in self.module_entities:
            diction[name] = self.module_entities[name].toJson()
        for name in self.object_entities:
            diction[name] = self.object_entities[name].toJson()
        return diction

    def entitiesToHelp(self):
        diction = ""
        for name in self.module_entities:
            diction += self.module_entities[name].toHelp()
        for name in self.object_entities:
            diction += self.object_entities[name].toHelp()
        return diction

    def get_InsideComments(self, object_name, item_id):
        """

        Args:
            object_name:
            item_id:

        Returns:

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

        """
        comment = ""
        if object_name in self.inline_comments:
            obj_dict = self.inline_comments[object_name]
            if item_id in obj_dict:
                comment = obj_dict[item_id]
                if comment != "":
                    comment = "  // " + comment
        return comment

    def get_diction(self, obj_entities, name, instanceTo):
        diction = ""
        ent_keys = obj_entities[name].instance.keys()
        if len(ent_keys) > 0:
            diction += instanceTo(obj_entities[name])
        return diction

    def instanceToModule(self, module):
        """
        instanceToModule adds the comments pulled from the backbone glm file
        to the new modified glm file.

        Args:
            module:

        Returns:

        """
        diction = ""
        if module.entity in self.outside_comments:
            out_comments = self.outside_comments[module.entity]
            for comment in out_comments:
                diction += comment + "\n"
        if len(module.instance) > 0:
            if module.entity in ["clock"]:
                diction = module.entity
            elif module.entity in ["player"]:
                diction = "class " + module.entity
            else:
                diction = "module " + module.entity
            keys = module.instance[module.entity].keys()
            if len(keys) > 0:
                diction += " {\n"
                diction += self.get_InsideComments(module.entity, 'name')
                for item in module.instance[module.entity].keys():
                    diction += self.get_InsideComments(module.entity, item)
                    comments = self.get_InlineComment(module.entity, item)
                    diction += "  " + item + " " + str(module.instance[module.entity][item]) + ";" + comments + "\n"
                diction += self.get_InsideComments(module.entity, "__last__")
                diction += "}\n"
            else:
                diction += ";\n"
        return diction

    def instanceToObject(self, object):
        """
        instanceToObject adds the comments pulled from the backbone glm file
        to the new modified glm file.

        Args:
            object:

        Returns:

        """
        diction = ""
        for object_name in object.instance:
            if object_name in self.outside_comments:
                out_comments = self.outside_comments[object_name]
                for comment in out_comments:
                    diction += comment + "\n"
            diction += "object " + object.entity + " {\n"
            diction += self.get_InsideComments(object_name, "name")
            diction += "  name " + object_name + ";\n"
            for item in object.instance[object_name].keys():
                diction += self.get_InsideComments(object_name, item)
                comments = self.get_InlineComment(object_name, item)
                diction += "  " + item + " " + str(object.instance[object_name][item]) + ";" + comments + "\n"
            diction += self.get_InsideComments(object_name, "__last__")
            diction += "}\n\n"
        return diction

    def instancesToGLM(self):
        diction = ""

        # Write the clock
        if self.module_entities["clock"]:
            diction += self.get_diction(self.module_entities, "clock", self.instanceToModule)
        diction += "\n"

        # Write the sets commands
        for name in self.set_lines:
            diction += name + "\n"
        diction += "\n"

        # Write the define commands
        for name in self.define_lines:
            diction += name + "\n"
        diction += "\n"

        # Write the includes
        for name in self.include_lines:
            diction += name + "\n"
        diction += "\n"

        # Write the modules
        for name in self.module_entities:
            if name not in ["clock"]:
                diction += self.get_diction(self.module_entities, name, self.instanceToModule)
        diction += "\n"

        # Write the objects
        for name in self.object_entities:
            diction += self.get_diction(self.object_entities, name, self.instanceToObject)

        # recorder, player, metrics_collector don't apply to the network, there are others
        # this work for the network (powerflow)
        # for name_1 in self.network:
        #     for object_name in self.model:
        #         for name_2 in self.object_entities[object_name].instance:
        #             if name_1 == name_2:
        #                 diction += self.get_diction(self.object_entities, object_name, self.instanceToObject)

        return diction

    def instancesToSQLite(self):
        for name in self.object_entities:
            self.object_entities[name].instanceToSQLite(self.conn)
        return

    def set_object_instance(self, obj_type, obj_name, params):
        if type(obj_type) == str and type(obj_name) == str:
            try:
                entity = self.object_entities[obj_type]
                return entity.set_instance(obj_name, params)
            except:
                print("Unrecognized GRIDLABD object and id ->", obj_type, obj_name)
                self.objects[obj_type] = {}
                entity = self.object_entities[obj_type] = Entity(obj_type, self.objects[obj_type])
                return entity.set_instance(obj_name, params)
        else:
            print("GRIDLABD object type and/or object name is not a string")
        return None

    def get_object_instance(self, obj_type, obj_name):
        if type(obj_type) == str and type(obj_type) == str:
            try:
                entity = self.object_entities[obj_type]
                return entity.get_instance(obj_name)
            except:
                print("Unrecognized GRIDLABD object and id ->", obj_type, obj_name)
        else:
            print("GRIDLABD object name and/or object id is not a string")
        return None

    def set_module_instance(self, mod_type, params):
        if type(mod_type) == str:
            try:
                entity = self.module_entities[mod_type]
                return entity.set_instance(mod_type, params)
            except:
                print("Unrecognized GRIDLABD module ->", mod_type)
                self.modules[mod_type] = {}
                entity = self.module_entities[mod_type] = Entity(mod_type, self.modules[mod_type])
                return entity.set_instance(mod_type, params)
        else:
            print("GRIDLABD module type is not a string")
        return None

    def get_module_instance(self, mod_type):
        if type(mod_type) == str:
            try:
                entity = self.module_entities[mod_type]
                return entity.get_instance(mod_type)
            except:
                print("Unrecognized GRIDLABD module ->", mod_type)
        else:
            print("GRIDLABD module is not a string")
        return None

    @staticmethod
    def gld_strict_name(val):
        """Sanitizes a name for GridLAB-D publication to FNCS

        Args:
            val (str): the input name

        Returns:
            str: val with all '-' replaced by '_', and any leading digit replaced by 'gld_'
        """
        if val[0].isdigit():
            val = 'gld_' + val
        return val.replace('-', '_')

    @staticmethod
    def get_region(s):
        region = 0
        if 'R1' in s:
            region = 1
        elif 'R2' in s:
            region = 2
        elif 'R3' in s:
            region = 3
        elif 'R4' in s:
            region = 4
        elif 'R5' in s:
            region = 5
        return region

    def is_edge_class(self, s):
        """Edge class is networkx terminology. In GridLAB-D, we will represent those edges with
        [switch, fuse, recloser, regulator, transformer, overhead_line,
        underground_line and triplex_line] instances

        Args:
            s (str): the GridLAB-D class name
        Returns:
            Boolean: True if an edge class, False otherwise
        """
        if s in self.edge_class:
            return True
        return False

    def is_node_class(self, s):
        """Node class is networkx terminology. In GridLAB-D, we will represent those nodes with
        [node, load, meter, triplex_node or triplex_meter] instances

        Node class is networkx terminology. In GridLAB-D, node classes are in node_class.
        Args:
            s (str): the GridLAB-D class name
        Returns:
            Boolean: True if a node class, False otherwise
        """
        if s in self.node_class:
            return True
        return False

    def module(self, mod, line, itr):
        """Store a clock/module/class in the model structure

        Args:
            mod (str): glm type [date, class, module]
            line (str): glm line containing the object definition
            itr (iter): iterator over the list of lines

        Returns:
            str, int: the current line and updated octr
        """

        # Collect parameters
        params = {}
        # Collect comments
        inside__comments = []
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
            inside__comments.append(substring)

        done = False
        line = next(itr).strip()
        while not done:
            # find a comment
            pos = line.find("//")
            if pos == 0:
                substring = line[pos + 2:].strip()
                inside__comments.append(substring)
                line = ";"
            elif pos > 0:
                substring = line[pos + 2:].strip()
                tokens = line.split(" ")
                inline_comments[tokens[0]] = substring

            # find a parameter
            m = re.match('\s*(\S+) ([^;]+);', line)
            if m:
                params[m.group(1)] = m.group(2)
                if len(inside__comments) > 0:
                    inside_comments[m.group(1)] = inside__comments
                    inside__comments = []
            if re.search('}', line):
                done = 1
            else:
                line = next(itr).strip()

        self.set_module_instance(_type, params)

        if len(inside__comments) > 0:
            inside_comments['__last__'] = inside__comments
        if len(inside__comments) > 0:
            self.inside_comments[_type] = inside_comments
        if len(inline_comments) > 0:
            self.inline_comments[_type] = inline_comments
        return _type

    def obj(self, parent, model, line, itr, oidh, octr):
        """Store an object in the model structure

        Args:
            parent (str): name of parent object (used for nested object defs)
            model (dict): dictionary model structure
            line (str): glm line containing the object definition
            itr (iter): iterator over the list of lines
            oidh (dict): hash of object id's to object names
            octr (int): object counter

        Returns:
            str, int: the current line and updated octr
        """
        # Identify the object type
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
        octr += 1
        name = None
        name_prefix = ''
        params = {}
        comments = []
        obj__comments = []
        inside__comments = []
        inside_comments = dict()
        inline_comments = dict()
        done = False

        pos = line.find("//")
        if pos > 0:
            substring = line[pos + 2:].strip()
            obj__comments.append(substring)

        line = next(itr)
        if len(parent):
            params['parent'] = parent
        while not done:
            pos = line.find("//")
            if pos == 0:
                substring = line[pos + 2:].strip()
                inside__comments.append(substring)
                line = ";"
            elif pos > 0:
                substring = line[pos + 2:].strip()
                tokens = line.split(" ")
                if tokens[0].lower() == 'object':
                    comments = substring
                    line = "object " + tokens[1] + " {"
                else:
                    inline_comments[tokens[0]] = substring

            intobj = 0
            m = re.match('\s*(\S+) ([^;{]+)[;{]', line)
            if m:
                # found a parameter
                param = m.group(1)
                val = m.group(2)
                if param == 'name':
                    name = self.gld_strict_name(name_prefix + val)
                    if len(obj__comments) > 0:
                        inside_comments['name'] = obj__comments
                        obj__comments = []
                elif param == 'object':
                    # found a nested object
                    intobj += 1
                    if name is None:
                        print('ERROR: nested object defined before parent name')
                        quit()
                    line, octr, lname = self.obj(name, model, line, itr, oidh, octr)
                    if len(comments):
                        if lname not in self.inside_comments:
                            self.inside_comments[lname] = {}
                            self.inside_comments[lname]['name'] = []
                        if 'name' in self.inside_comments[lname]:
                            self.inside_comments[lname]['name'].append(comments)
                        else:
                            self.inside_comments[lname]['name'] = comments
                        comments = ""
                else:
                    if val == "$":
                        # found $ directive
                        pos = line.find("{")
                        pos1 = line.find(";")
                        params[param] = val + line[pos:pos1]
                        line = ";"
                    params[param] = val
                    if len(inside__comments) > 0:
                        inside_comments[param] = inside__comments
                        inside__comments = []

            if re.search('}', line):
                if intobj:
                    intobj -= 1
                    line = next(itr)
                else:
                    done = True
            else:
                line = next(itr)
        # If undefined, use a default name
        if name is None:
            name = name_prefix + 'ID_' + str(octr)
        oidh[name] = name
        # Hash an object identifier to the object name
        if n:
            oidh[oid] = name
        # Add the object to the model
        if _type not in model:
            # New object type
            model[_type] = {}
        # find and set object entity instance
        model[_type][name] = {}
        model[_type][name] = self.set_object_instance(_type, name, params)

        if len(inside__comments) > 0:
            inside_comments['__last__'] = inside__comments
        if len(inside_comments) > 0:
            self.inside_comments[name] = inside_comments
        if len(inline_comments) > 0:
            self.inline_comments[name] = inline_comments
        return line, octr, name

    def readBackboneModel(self, rootname, feederspath):
        """Parse one backbone feeder, usually but not necessarily one of the PNNL taxonomy feeders

        This function:
                * reads and parses the backbone model from *rootname.glm*

        Args:
            rootname (str): the input (usually taxonomy) feeder model name
            feederspath (str):
        """
        # global base_feeder_name
        fname = os.path.join(feederspath, rootname)  # + '.glm'
        rootname = self.gld_strict_name(rootname)

        name = ""
        octr = 0
        h = {}  # OID hash
        lines = []
        model = {}
        self.set_lines = []
        self.define_lines = []
        self.include_lines = []
        outside_comments = []
        if os.path.isfile(fname):
            ip = open(fname, 'r')
            line = ip.readline()
            while line != '':
                # skip white space lines
                while re.match('\s+$', line):
                    line = ip.readline()
                line = line.strip()
                lines.append(line.replace("\t", " "))
                line = ip.readline()
            ip.close()

            itr = iter(lines)
            for line in itr:
                if re.match('\s*//', line):
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
                    name = self.module("date", line, itr)
                elif re.search('class', line):
                    name = self.module("class", line, itr)
                elif re.search('module', line):
                    name = self.module("module", line, itr)
                elif re.search('object', line):
                    line, octr, name = self.obj("", model, line, itr, h, octr)
                else:
                    print('Unparsed line\n', line)

                if name != "":
                    if len(outside_comments) > 0:
                        self.outside_comments[name] = outside_comments
                    outside_comments = []
                    name = ""

            # apply the naming prefix if necessary
            # if len(name_prefix) > 0:
            #    for t in model:
            # for o in model[t]:
            #    elem = model[t][o]
            #    for tok in ['name', 'parent', 'from', 'to', 'configuration', 'spacing',
            #                'conductor_1', 'conductor_2', 'conductor_N',
            #                'conductor_A', 'conductor_B', 'conductor_C']:
            #        if tok in elem:
            #            elem[tok] = name_prefix + elem[tok]

            #        log_model (model, h)

            # construct a graph of the model, starting with known links
            G = nx.Graph()
            for t in model:
                if self.is_edge_class(t):
                    for o in model[t]:
                        n1 = self.gld_strict_name(model[t][o]['from'])
                        n2 = self.gld_strict_name(model[t][o]['to'])
                        G.add_edge(n1, n2, eclass=t, ename=o, edata=model[t][o])

            # add the parent-child node links
            for t in model:
                if self.is_node_class(t):
                    for o in model[t]:
                        if 'parent' in model[t][o]:
                            p = self.gld_strict_name(model[t][o]['parent'])
                            G.add_edge(o, p, eclass='parent', ename=o, edata={})

            # now we backfill node attributes
            for t in model:
                if self.is_node_class(t):
                    for o in model[t]:
                        if o in G.nodes():
                            G.nodes()[o]['nclass'] = t
                            G.nodes()[o]['ndata'] = model[t][o]
                        else:
                            print('orphaned node', t, o)
            return model, G

    def read(self, filepath):
        self.in_file = filepath
        path_parts = os.path.split(filepath)
        results = self.readBackboneModel(path_parts[1], path_parts[0])
        self.model = results[0]
        self.network = results[1]
        return self.network

    def write(self, filepath):
        try:
            op = open(filepath, "w+")
        except:
            print("Unable to open output file")
            return False

        # we can write using instance objects
        print(self.instancesToGLM(), file=op)

        op.close()
        return True
