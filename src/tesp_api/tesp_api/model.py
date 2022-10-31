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

from data import entities_path
from entity import Entity


class GLModel:
# it seems to public for all GLMODEL class
    in_file = ""
    out_file = ""
    network = nx.Graph()
    header_lines = []
    inside_comments = dict()
    outside_comments = dict()
    inline_comments = dict()
    entities = {}
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
            self.conn = sqlite3.connect(entities_path + 'test.db')
            print("Opened database successfully")
        except:
            self.conn = None
            print("Database Sqlite3.db not formed")

        with open(entities_path + 'glm_objects.json', 'r', encoding='utf-8') as json_file:
            self.objects = json.load(json_file)

        for name in self.objects:
            self.entities[name] = Entity(name, self.objects[name])
            self.entities[name].toSQLite(self.conn)

    def entitiesToJson(self):
        diction = {}
        for name in self.entities:
            diction[name] = self.entities[name].toJson()
        return diction

    def instancesToGLM(self):
        diction = ""
        for name in self.entities:
            diction += self.entities[name].instanceToGLM()
        return diction

    def instancesToSQLite(self):
        for name in self.entities:
            self.entities[name].instanceToSQLite(self.conn)
        return

    def entitiesToHelp(self):
        diction = ""
        for name in self.entities:
            diction += self.entities[name].toHelp()
        return diction

    def set_instance(self, obj_name, obj_id, params):
        if type(obj_name) == str and type(obj_name) == str:
            try:
                entity = self.entities[obj_name]
                return entity.set_instance(obj_id, params)
            except:
                print("Unrecognized object and id ->", obj_name, obj_id)
                self.objects[obj_name] = {}
                entity = self.entities[obj_name] = Entity(obj_name, self.objects[obj_name])
                return entity.set_instance(obj_id, params)
        else:
            print("Object name and/or object id is not a string")
        return None

    def get_instance(self, obj_name, obj_id):
        if type(obj_name) == str and type(obj_name) == str:
            try:
                entity = self.entities[obj_name]
                return entity.get_instance(obj_id)
            except:
                print("Unrecognized GRIDLABD object and id ->", obj_name, obj_id)
        else:
            print("Object name and/or object id is not a string")
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
        line = next(itr)
        # Collect parameters
        oend = 0
        oname = None
        params = {}
        incomments = []
        objinlinecomments = dict()
        inlinecomments = {}

        if parent is not None:
            params['parent'] = parent
        while not oend:
            # if re.match('\s*//', line):
            if line.find("//") == 0:
                incomments.append(line)
            elif line.find("//") > 0:
                subindex = line.find("//")
                substring = line[subindex + 2:]
                tline = line.strip()
                tokens = tline.split(" ")
                objinlinecomments[tokens[0]] = substring

            m = re.match('\s*(\S+) ([^;{]+)[;{]', line)
            if m:
                # found a parameter
                param = m.group(1)
                val = m.group(2)
                intobj = 0
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

        # find and set entity
        # all incomment as object_comment type
        # params["object_comment"] = incomments

        model[_type][oname] = self.set_instance(_type, oname, params)
        # model[_type][oname] = params
        return line, octr, oname, incomments, objinlinecomments

    def readBackboneModel(self, rootname, feederspath):
        """Parse one backbone feeder, usually but not necessarily one of the PNNL taxonomy feeders

        This function:
                * reads and parses the backbone model from *rootname.glm*

        Args:
            rootname (str): the input (usually taxonomy) feeder model name
        """
        # global base_feeder_name

        solar_count = 0
        solar_kw = 0
        battery_count = 0
        ev_count = 0

        base_feeder_name = self.gld_strict_name(rootname)
        fname = feederspath + '/' + rootname  # + '.glm'
        rootname = self.gld_strict_name(rootname)
        headlines = []
        insidecomments = dict()
        outsidecomments = dict()
        if os.path.isfile(fname):
            ip = open(fname, 'r')
            lines = []
            line = ip.readline()
            headlines = []
            while line.find("};") < 0:
                headlines.append(line)
                line = ip.readline()
            headlines.append(line)
            line = ip.readline()
            while line != '':
                # while re.match('\s*//', line) or re.match('\s+$', line):
                while re.match('\s+$', line):
                    # skip white space
                    line = ip.readline()
                lines.append(line.rstrip())
                line = ip.readline()
            ip.close()
            octr = 0
            model = {}
            h = {}  # OID hash
            itr = iter(lines)
            outcomments = []
            incomments = []
            inlinecomments = dict()
            linecomments = dict()
            for line in itr:
                if re.match('\s*//', line):
                    outcomments.append(line)
                if re.search('clock', line):
                   clock = ""
                if re.search('module', line):
                   modules = ""
                if re.search('object', line):
                    line, octr, oname, incomments, linecomments = self.obj(None, model, line, itr, h, octr)
                    if len(outcomments) > 0:
                        outsidecomments[oname] = outcomments
                    if len(incomments) > 0:
                        insidecomments[oname] = incomments
                    if len(linecomments) > 0:
                        inlinecomments[oname] = linecomments
                    outcomments = []
            # apply the nameing prefix if necessary
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
            return G, headlines, outsidecomments, insidecomments, inlinecomments

    def read(self, filepath):
        self.header_lines = []
        self.in_file = filepath
        path_parts = os.path.split(filepath)
        readresults = self.readBackboneModel(path_parts[1], path_parts[0])
        self.network = readresults[0]
        self.header_lines = readresults[1]
        self.outside_comments = readresults[2]
        self.inside_comments = readresults[3]
        self.inline_comments = readresults[4]
        return self.network

    def write_header(self, op):
        for line in self.header_lines:
            try:
                print(line.rstrip(), file=op)
            except:
                print("unable to write to output file")
                return False

        return True

    def write(self, filepath):
        self_out_file = filepath
        try:
            op = open(filepath, "w+")
        except:
            print("Unable to open output file")
            return False
        self.write_header(op)

        # we can write using instance objects
        print(self.instancesToGLM(), file=op)

        op.close()
        return True

    def import_networkx_obj(self, inetwork):
        network = inetwork
        return True
