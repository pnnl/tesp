
import re
import os.path
import networkx as nx
#This is defined in helpers.py need to import the file instead of declaring it here
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

def is_edge_class(s):
    """Identify switch, fuse, recloser, regulator, transformer, overhead_line,
    underground_line and triplex_line instances

    Edge class is networkx terminology. In GridLAB-D, edge classes are called links.
    Args:
        s (str): the GridLAB-D class name
    Returns:
        Boolean: True if an edge class, False otherwise
    """
    if s == 'switch':
        return True
    if s == 'fuse':
        return True
    if s == 'recloser':
        return True
    if s == 'regulator':
        return True
    if s == 'transformer':
        return True
    if s == 'overhead_line':
        return True
    if s == 'underground_line':
        return True
    if s == 'triplex_line':
        return True
    return False

def is_node_class(s):
    """Identify node, load, meter, triplex_node or triplex_meter instances
    Args:
        s (str): the GridLAB-D class name
    Returns:
        Boolean: True if a node class, False otherwise
    """
    if s == 'node':
        return True
    if s == 'load':
        return True
    if s == 'meter':
        return True
    if s == 'triplex_node':
        return True
    if s == 'triplex_meter':
        return True
    return False


def obj(parent, model, line, itr, oidh, octr):
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
    if parent is not None:
        params['parent'] = parent
    while not oend:
        m = re.match('\s*(\S+) ([^;{]+)[;{]', line)
        if m:
            # found a parameter
            param = m.group(1)
            val = m.group(2)
            intobj = 0
            if param == 'name':
                oname = gld_strict_name(name_prefix + val)
            elif param == 'object':
                # found a nested object
                intobj += 1
                if oname is None:
                    print('ERROR: nested object defined before parent name')
                    quit()
                line, octr = obj(oname, model, line, itr, oidh, octr)
            elif re.match('object', val):
                # found an inline object
                intobj += 1
                line, octr = obj(None, model, line, itr, oidh, octr)
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
    for param in params:
        model[_type][oname][param] = params[param]
    return line, octr

#def ProcessTaxonomyFeeder(outname, rootname, vll, vln, avghouse, avgcommercial):
def readBackboneModel(rootname,feederspath):
    """Parse one backbone feeder, usually but not necessarily one of the PNNL taxonomy feeders

    This function:

        * reads and parses the backbone model from *rootname.glm*

    Args:
        rootname (str): the input (usually taxonomy) feeder model name
    """
    #global base_feeder_name

    solar_count = 0
    solar_kw = 0
    battery_count = 0
    ev_count = 0

    base_feeder_name = gld_strict_name(rootname)
    fname = feederspath + rootname + '.glm'
    rootname = gld_strict_name(rootname)
    rgn = 0
    if 'R1' in rootname:
        rgn = 1
    elif 'R2' in rootname:
        rgn = 2
    elif 'R3' in rootname:
        rgn = 3
    elif 'R4' in rootname:
        rgn = 4
    elif 'R5' in rootname:
        rgn = 5
    if os.path.isfile(fname):
        ip = open(fname, 'r')
        lines = []
        line = ip.readline()
        while line != '':
            while re.match('\s*//', line) or re.match('\s+$', line):
                # skip comments and white space
                line = ip.readline()
            lines.append(line.rstrip())
            line = ip.readline()
        ip.close()
        octr = 0
        model = {}
        h = {}  # OID hash
        itr = iter(lines)
        for line in itr:
            if re.search('object', line):
                line, octr = obj(None, model, line, itr, h, octr)
        # apply the nameing prefix if necessary
        #if len(name_prefix) > 0:
                #    for t in model:
                #for o in model[t]:
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
            if is_edge_class(t):
                for o in model[t]:
                    n1 = gld_strict_name(model[t][o]['from'])
                    n2 = gld_strict_name(model[t][o]['to'])
                    G.add_edge(n1, n2, eclass=t, ename=o, edata=model[t][o])

        # add the parent-child node links
        for t in model:
            if is_node_class(t):
                for o in model[t]:
                    if 'parent' in model[t][o]:
                        p = gld_strict_name(model[t][o]['parent'])
                        G.add_edge(o, p, eclass='parent', ename=o, edata={})

        # now we backfill node attributes
        for t in model:
            if is_node_class(t):
                for o in model[t]:
                    if o in G.nodes():
                        G.nodes()[o]['nclass'] = t
                        G.nodes()[o]['ndata'] = model[t][o]
                    else:
                        print('orphaned node', t, o)
        return G
#        sub_graphs = nx.connected_components(G)
#        seg_loads = {}  # [name][kva, phases]

class GLModel:
    in_file = ""
    out_file = ""
    network = nx()



    def read_glm(self, filepath):
        self.in_file = filepath
        path_parts = os.path.split(filepath)
        network = readBackboneModel(path_parts[1], path_parts[0])
        return True

    def write_glm(self, filepath):
        self_out_file = filepath
        return True

    def import_networkx_obj(self,inetwork):
        network = inetwork
        return True



