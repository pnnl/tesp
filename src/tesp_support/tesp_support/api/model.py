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
    network = nx.Graph()
    header_lines = []
    set_lines = []
    include_lines = []
    inside_comments = dict()
    outside_comments = dict()
    inline_comments = dict()
    object_entities = {}
    module_entities = {}
    modules = None
    objects = None
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

    @staticmethod
    def get_InsideComments(object_name, in_comments):
        """

        Args:
            object_name:
            in_comments:

        Returns:

        """
        comments = ""
        if object_name in in_comments:
            temp_comments = in_comments[object_name]
            if len(temp_comments) > 0:
                for comment in temp_comments:
                    comments += "  " + comment + "\n"
        return comments

    @staticmethod
    def get_InlineComment(object_name, item_id, line_comments):
        """

        Args:
            object_name:
            item_id:
            line_comments:

        Returns:

        """
        comment = ""
        if object_name in line_comments:
            obj_dict = line_comments[object_name]
            if item_id in obj_dict:
                comment = obj_dict[item_id]
                if comment != "":
                    comment = " //" + comment
        return comment

    def get_diction(self, obj_entities, name, instanceTo):
        diction = ""
        ent_keys = obj_entities[name].instance.keys()
        if len(ent_keys) > 0:
            obj_name = list(ent_keys)[0]
            if obj_name in self.outside_comments:
                out_comments = self.outside_comments[obj_name]
                for comment in out_comments:
                    diction += comment + "\n"
            diction += instanceTo(obj_entities[name], self.inside_comments, self.inline_comments)
        return diction

    def instanceToModule(self, module, in_comments, line_comments):
        """
        instanceToModule adds the comments pulled from the backbone glm file
        to the new modified glm file.

        Args:
            module:
            in_comments:
            line_comments:

        Returns:

        """
        diction = ""
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
                diction += self.get_InsideComments(module.entity, in_comments)
                for item in module.instance[module.entity].keys():
                    comments = self.get_InlineComment(module.entity, item, line_comments)
                    diction += "  " + item + " " + str(module.instance[module.entity][item]) + ";" + comments + "\n"
                diction += "}\n"
            else:
                diction += ";\n"
        return diction

    def instanceToObject(self, object, in_comments, line_comments):
        """
        instanceToObject adds the comments pulled from the backbone glm file
        to the new modified glm file.

        Args:
            object:
            in_comments:
            line_comments:

        Returns:

        """
        diction = ""
        for object_name in object.instance:
            diction += "object " + object.entity + " {\n"
            diction += self.get_InsideComments(object_name, in_comments)
            diction += "  name " + object_name + ";\n"
            for item in object.instance[object_name].keys():
                comments = self.get_InlineComment(object_name, item, line_comments)
                diction += "  " + item + " " + str(object.instance[object_name][item]) + ";" + comments + "\n"
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
        inside_comments = []
        inline_comments = dict()

        # Set the clock to date module
        if mod in ["date"]:
            line = mod + " " + line

        # Identify the object type
        if line.find(";") > 0:
            m = re.search(mod + ' ([^;\s]+)[;\s]', line, re.IGNORECASE)
            _type = m.group(1)
            self.set_module_instance(_type, params)
            return inside_comments, inline_comments

        if line.find("{") > 0:
            m = re.search(mod + ' ([^{\s]+)[{\s]', line, re.IGNORECASE)
            _type = m.group(1)

        done = False
        line = next(itr).strip()
        while not done:
            # find a comment
            pos = line.find("//")
            if pos == 0:
                inside_comments.append(line)
            elif pos > 0:
                tokens = line.split(" ")
                inline_comments[tokens[0]] = line[pos + 2:]

            # find a parameter
            m = re.match('\s*(\S+) ([^;]+);', line)
            if m:
                params[m.group(1)] = m.group(2)
            if re.search('}', line):
                done = 1
            else:
                line = next(itr).strip()

        self.set_module_instance(_type, params)
        return inside_comments, inline_comments

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
        name_prefix = ''
        octr += 1
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

        line = next(itr)
        # Collect parameters
        oend = 0
        oname = None
        params = {}
        inside_comments = []
        inline_comments = dict()

        if parent is not None:
            params['parent'] = parent
        while not oend:
            pos = line.find("//")
            if pos == 0:
                inside_comments.append(line.strip())
            elif pos > 0:
                substring = line[pos + 2:]
                tokens = line.split(" ")
                inline_comments[tokens[0]] = substring

            intobj = 0
            m = re.match('\s*(\S+) ([^;{]+)[;{]', line)
            if m:
                # found a parameter
                param = m.group(1)
                val = m.group(2)
                if param == 'name':
                    oname = self.gld_strict_name(name_prefix + val)
                elif param == 'object':
                    # found a nested object
                    intobj += 1
                    if oname is None:
                        print('ERROR: nested object defined before parent name')
                        quit()
                    line, octr = self.obj(oname, model, line, itr, oidh, octr)
                elif re.match('object', val):
                    # found an inline object
                    intobj += 1
                    line, octr = self.obj(None, model, line, itr, oidh, octr)
                    params[param] = 'ID_' + str(octr)
                else:
                    params[param] = val
            if re.search('}', line):
                if intobj:
                    intobj -= 1
                    line = next(itr)
                else:
                    oend = 1
            else:
                line = next(itr)
        # If undefined, use a default name
        if oname is None:
            oname = name_prefix + 'ID_' + str(octr)
        oidh[oname] = oname
        # Hash an object identifier to the object name
        if n:
            oidh[oid] = oname
        # Add the object to the model
        if _type not in model:
            # New object type
            model[_type] = {}
        model[_type][oname] = {}

        # find and set entity instance
        model[_type][oname] = self.set_object_instance(_type, oname, params)
        return line, octr, oname, inside_comments, inline_comments

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

        octr = 0
        model = {}
        h = {}  # OID hash
        lines = []
        self.set_lines = []
        self.include_lines = []
        outsidecomments = []
        outside_comments = dict()
        inside_comments = dict()
        inline_comments = dict()
        if os.path.isfile(fname):
            ip = open(fname, 'r')
            line = ip.readline()
            while line != '':
                while re.match('\s+$', line):
                    # skip white space
                    line = ip.readline()
                lines.append(line.strip())
                line = ip.readline()
            ip.close()

            itr = iter(lines)
            for line in itr:
                if re.match('\s*//', line):
                    outsidecomments.append(line)
                if re.search('#set', line):
                    self.set_lines.append(line)
                if re.search('#include', line):
                    self.include_lines.append(line)
                if re.search('clock', line):
                    insidecomments, linecomments = self.module("date", line, itr)
                if re.search('class', line):
                    insidecomments, linecomments = self.module("class", line, itr)
                if re.search('module', line):
                    insidecomments, linecomments = self.module("module", line, itr)
                if re.search('object', line):
                    line, octr, oname, insidecomments, inlinecomments = self.obj(None, model, line, itr, h, octr)
                    if len(outsidecomments) > 0:
                        outside_comments[oname] = outsidecomments
                    if len(insidecomments) > 0:
                        inside_comments[oname] = insidecomments
                    if len(inlinecomments) > 0:
                        inline_comments[oname] = inlinecomments
                    outsidecomments = []
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
            return G, outside_comments, inside_comments, inline_comments

    def read(self, filepath):
        self.header_lines = []
        self.in_file = filepath
        path_parts = os.path.split(filepath)
        readresults = self.readBackboneModel(path_parts[1], path_parts[0])
        self.network = readresults[0]
        self.outside_comments = readresults[1]
        self.inside_comments = readresults[2]
        self.inline_comments = readresults[3]
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
