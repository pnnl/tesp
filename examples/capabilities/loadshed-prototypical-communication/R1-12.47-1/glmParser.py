import json
import os.path
import re
import sys

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import seaborn as sns
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

current_palette = sns.xkcd_palette(sns.xkcd_rgb)  # color_palette('pastel')
sns.set_palette(current_palette)
# sns.palplot(current_palette)
nodeColorSpec = ['xkcd:royal blue', 'xkcd:purple', 'xkcd:orange',
                 'xkcd:red', 'xkcd:magenta', 'xkcd:violet', 'xkcd:light brown', 'xkcd:yellow', 'xkcd:green',
                 'xkcd:gunmetal']
lineStyles = ['solid', 'dashed', 'dashdot', 'dotted', (0, (3, 1, 1, 1, 1, 1)), (0, (3, 5, 1, 5, 1, 5)), 'dashed',
              (0, (3, 5, 1, 5, 1, 5))]
glmObjs = ['substation', 'node', 'triplex_node', 'meter', 'triplex_meter', 'load', 'house', 'solar', 'battery',
           'inverter']
glmLinks = ['overhead_line', 'parent', 'regulator', 'switch', 'transformer', 'triplex_line', 'underground_line']
edgeColorSpec = ['xkcd:black', 'xkcd:black', 'xkcd:black', 'xkcd:yellow', 'xkcd:bright light blue', 'xkcd:blood orange',
                 'xkcd:black']

showGraph = False

name_prefix = ''


def ProcessGLM(glmFile):
    fname = glmFile  # glmpath + rootname + '.glm'
    print(f'Parsing {fname}')
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

        # op = open (outpath + outname + '.glm', 'w')
        # print ('###### Writing to', outpath + outname + '.glm')
        octr = 0
        model = {}
        h = {}  # OID hash
        itr = iter(lines)
        for line in itr:
            if re.search('object', line):
                line, octr = obj(None, model, line, itr, h, octr)
            else:  # should be the pre-amble, need to replace timestamp and stoptime
                # if 'timestamp' in line:
                #     print ('  timestamp \'' + starttime + '\';', file=op)
                # elif 'stoptime' in line:
                #     print ('  stoptime \'' + endtime + '\';', file=op)
                # else:
                #     print (line, file=op)
                pass

        # apply the nameing prefix if necessary
        if len(name_prefix) > 0:
            for t in model:
                for o in model[t]:
                    elem = model[t][o]
                    for tok in ['name', 'parent', 'from', 'to', 'configuration', 'spacing',
                                'conductor_1', 'conductor_2', 'conductor_N',
                                'conductor_A', 'conductor_B', 'conductor_C']:
                        if tok in elem:
                            elem[tok] = name_prefix + elem[tok]

        # log_model (model, h)

        # construct a graph of the model, starting with known links
        G = nx.Graph()
        for t in model:
            if is_edge_class(t):
                for o in model[t]:
                    n1 = model[t][o]['from']
                    n2 = model[t][o]['to']
                    G.add_edge(n1, n2, eclass=t, ename=o, edata=model[t][o])

        # add the parent-child node links
        for t in model:
            if is_node_class(t):
                for o in model[t]:
                    if 'parent' in model[t][o]:
                        p = model[t][o]['parent']
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

        swing_node = ''
        for n1, data in G.nodes(data=True):
            if 'nclass' in data:
                if 'bustype' in data['ndata']:
                    if data['ndata']['bustype'] == 'SWING':
                        swing_node = n1
    return G


def is_node_class(s):
    """Identify node, load, meter, triplex_node or triplex_meter instances

    Args:
        s (str): the GridLAB-D class name

    Returns:
        Boolean: True if a node class, False otherwise
    """
    if s in ['substation', 'node', 'load', 'meter', 'triplex_node', 'triplex_meter', 'house', 'inverter', 'solar',
             'battery']:
        return True
    return False


def is_edge_class(s):
    """Identify switch, fuse, recloser, regulator, transformer, overhead_line, underground_line and triplex_line instances

    Edge class is networkx terminology. In GridLAB-D, edge classes are called links.

    Args:
        s (str): the GridLAB-D class name

    Returns:
        Boolean: True if an edge class, False otherwise
    """
    if s in ['switch', 'fuse', 'recloser', 'regulator', 'transformer', 'overhead_line', 'underground_line',
             'triplex_line']:
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
    octr += 1
    # Identify the object type
    m = re.search('object ([^:{\s]+)[:{\s]', line, re.IGNORECASE)
    type = m.group(1)
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
                oname = name_prefix + val
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
        if re.search('}', line) and not re.search('\${', line):
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
    if type not in model:
        # New object type
        model[type] = {}
    model[type][oname] = {}
    for param in params:
        model[type][oname][param] = params[param]
    return line, octr


def plotSaveGraph(G, fileName=None):
    dpiValue = 150
    pictureFormat = 'pdf'
    # pos = nx.planar_layout(G)
    pos = nx.kamada_kawai_layout(G, scale=5)
    #   pos = nx.spiral_layout(G)
    #   pos = nx.spring_layout(G, k = 0.01 / np.sqrt(G.number_of_nodes()), iterations = 100, seed = 39775)
    remNodeList = []
    for node in G.nodes():
        if 'nclass' not in G.nodes()[node].keys():
            remNodeList.append(node)
    if not remNodeList:
        print('All nodes seem to have an nclass.')
    else:
        print(f'The following set of nodes are not listed: {remNodeList}.')
    # The following 3 lines had been used to identify a certain triplex node load for diagraming only
    # for node in G.nodes():
    #   if 'tn' in node and 'l109' not in node:
    #     remNodeList.append(node)
    G.remove_nodes_from(remNodeList)
    nodeClasses = np.unique(
        np.array([G.nodes()[node]['nclass'] for node in G.nodes()]))  # if 'nclass' in G.nodes()[node].keys()]))
    print(nodeClasses)
    edgeClasses = np.unique(np.array([G.edges()[edge]['eclass'] for edge in G.edges()]))
    print(edgeClasses)
    nodeColorMap = {}
    edgeColorMap = {}
    nodeSizeMap = {}
    legendElements = []
    for cls in nodeClasses:
        nodeColorMap[cls] = nodeColorSpec[np.where(np.array(glmObjs) == cls)[0][0]]
        # print(np.where(np.array(glmObjs) == cls)[0][0])
        # nodeSizeMap[cls] = (np.where(np.array(glmObjs) == cls)[0][0] + 1) * 10
        elemNum = len([G.nodes()[node] for node in G.nodes() if G.nodes()[node]['nclass'] == cls])
        print(f'Number of {cls}: {elemNum}')
        if cls in ['house', 'solar', 'battery']:
            nodeSizeMap[cls] = 50
            legendElements.append(Line2D([0], [0], marker='o', color='white', label=f'{cls} ({elemNum})', markersize=16,
                                         markerfacecolor=nodeColorMap[cls]))
        elif cls in ['node']:
            nodeSizeMap[cls] = 40
            legendElements.append(
                Line2D([0], [0], marker='o', color='white', label=f'primary feeder node ({elemNum})', markersize=16,
                       markerfacecolor=nodeColorMap[cls]))
        elif cls in ['triplex_node']:
            nodeSizeMap[cls] = 40
            legendElements.append(
                Line2D([0], [0], marker='o', color='white', label=f'head of secondary feeders ({elemNum})',
                       markersize=16, markerfacecolor=nodeColorMap[cls]))
        else:
            nodeSizeMap[cls] = 30
            legendElements.append(Line2D([0], [0], marker='o', color='white', label=f'{cls}', markersize=16,
                                         markerfacecolor=nodeColorMap[cls]))
    for cls in edgeClasses:
        if cls in ['triplex_line', 'transformer', 'switch']:
            edgeColorMap[cls] = edgeColorSpec[np.where(np.array(glmLinks) == cls)[0][0]]
            legendElements.append(
                Line2D([0], [1], linestyle='solid', linewidth=2, color=edgeColorMap[cls], label=f'{cls}'))
        # elif cls == 'transformer':
        #   edgeColorMap[cls] = edgeColorSpec[np.where(np.array(glmLinks) == cls)[0][0]]
        #   legendElements.append(Line2D([0], [1], linestyle = 'solid', linewidth = 2, color = edgeColorMap[cls], label = f'{cls}'))
        else:
            edgeColorMap[cls] = 'xkcd:black'
    print(edgeColorMap)
    figWidth = 16
    figHeight = 8
    nCol = 1
    nRow = 1
    hFig = plt.figure(constrained_layout=True, figsize=(figWidth, figHeight))
    gs = GridSpec(nRow, nCol, figure=hFig)
    hAxis = hFig.add_subplot(gs[0, 0])
    nodeColorValues = [nodeColorMap.get(G.nodes()[node]['nclass'], nodeColorSpec[4]) for node in G.nodes()]
    sizeValues = [nodeSizeMap.get(G.nodes()[node]['nclass'], 100) for node in G.nodes()]
    edgeColorValues = [edgeColorMap.get(G.edges()[edge]['eclass'], edgeColorSpec[4]) for edge in G.edges()]
    nx.draw(G, pos=pos, node_color=nodeColorValues, edge_color=edgeColorValues, with_labels=False, node_size=sizeValues,
            width=2)  # cmap=plt.get_cmap('viridis')
    hAxis.legend(handles=legendElements, loc='upper left', ncol=3, fontsize=12)
    if fileName is not None:
        plt.savefig(f'{fileName}.{pictureFormat}', dpi=dpiValue, format=pictureFormat, bbox_inches='tight')


if __name__ == '__main__':
    spotLoadNums = [1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 16, 17, 19, 20, 22, 24, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39,
                    41, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52, 53, 55, 56, 58, 59, 60, 62, 63, 64, 65, 66, 68, 69, 70,
                    71, 73, 74, 75, 76, 77, 79, 80, 82, 83, 84, 85, 86, 87, 88, 90, 92, 94, 95, 96, 98, 99, 100, 102,
                    103, 104, 106, 107, 109, 111, 112, 113, 114]
    phases = ['A', 'B', 'C']
    # spotLoadPhases = [['A'], ['B'], ['C'], ['C'], ['C'], ['A'], ['A'], ['A'], ['A'], ['B'], ['C'], ['C'], ['A'],['A'],
    #                   ['B'], ['C'], ['A'], ['A'], ['C'], ['C'], ['C'], ['A'], ['C'], ['A'], ['A'], ['B'], ['B'],['C'],
    #                   ['A'], ['B'], ['A'], ['A'], ['A', 'B', 'C'], ['A', 'B', 'C'], ['A', 'B', 'C'], ['C'], ['A'],
    #                   ['A'], ['A'], ['A'], ['B'], ['B'], ['B'], ['A'], ['C'], ['A'], ['B'], ['A', 'B', 'C'], ['C'],
    #                   ['A'], ['A'], ['A'], ['A'], ['C'], ['C'], ['C'], ['A', 'B', 'C'], ['B'], ['A'], ['B'], ['A'],
    #                   ['C'], ['C'], ['C'], ['B'], ['B'], ['A'], ['B'], ['C'], ['A'], ['B'], ['B'], ['A'], ['B'],['C'],
    #                   ['C'], ['C'], ['C'], ['B'], ['B'], ['A'], ['A'], ['A'], ['A'], ['A']]
    spotLoads = {}
    for spot in spotLoadNums:
        ind = spotLoadNums.index(spot)
        spotLoads[spot] = {}
        for phase in phases:  # spotLoadPhases[ind]:
            spotLoads[spot][phase] = {'Houses': 0, 'PVs': 0, 'PV rating [kVA]': 0, 'Batteries': 0,
                                      'Battery rating [kVA]': 0, 'DER rating [kVA]': 0}
    id = 'eureica'
    version = '17-20220404'
    glmFolder = os.path.abspath(f'./')
    glmFile = f'R1-12.47-1_processed'
    G = ProcessGLM(os.path.abspath(os.path.join(glmFolder, f'{glmFile}.glm')))
    jsonGraph = nx.readwrite.json_graph.node_link_data(G)
    fileG = f'{glmFile}.json'
    jsonFp = open(os.path.abspath(os.path.join(glmFolder, fileG)), 'w')
    json.dump(jsonGraph, jsonFp)
    jsonFp.close()
    # nodeClasses = [G.nodes()[node]['nclass'] for node in G.nodes() if 'nclass' in G.nodes()[node].keys()]
    # print(np.unique(np.array(nodeClasses)))
    # Do not save figures
    plotSaveGraph(G)
    # Save figures
    # plotSaveGraph(G, fileName = glmFile)
    plt.show()
    sys.exit(2)
    # glmFolder = os.path.abspath('/Users/mari009/PNNL_Projects/GitRepositories/TESP_github/src/tesp_support/tesp_support/Dummy/')
    glmFile = f'ieee123_{id}-v{version}_processed'
    popG = ProcessGLM(os.path.abspath(os.path.join(glmFolder, f'{glmFile}.glm')))
    jsonGraph = nx.readwrite.json_graph.node_link_data(popG)
    filePopG = f'{glmFile}.json'
    jsonFp = open(os.path.abspath(os.path.join('./', filePopG)), 'w')
    json.dump(jsonGraph, jsonFp)
    jsonFp.close()
    ratedSol = 0
    ratedBat = 0
    numSol = 0
    numBat = 0
    numHouses = 0
    x = 0
    y = 0
    meas = ['Houses', 'DER rating [kVA]', 'PVs', 'PV rating [kVA]', 'Batteries', 'Battery rating [kVA]']
    mIndex = pd.MultiIndex.from_product([phases, meas], names=['Phase', 'Measurement'])
    spotLoadsDF = pd.DataFrame(np.zeros((len(spotLoadNums), len(phases) * len(meas))), index=spotLoadNums,
                               columns=mIndex)
    for node in jsonGraph['nodes']:
        if node['nclass'] == 'inverter' and 'isol' in node['id']:
            numSol += 1
            ratedSol += int(node['ndata']['rated_power'])
            nodeNum = int(node['id'].split('_')[1][1:])
            nodePhase = node['id'].split('_')[2]
            spotLoads[nodeNum][nodePhase]['PVs'] += 1
            spotLoadsDF.loc[nodeNum][nodePhase]['PVs'] += 1
            spotLoads[nodeNum][nodePhase]['PV rating [kVA]'] += float(node['ndata']['rated_power']) * 1e-3
            spotLoadsDF.loc[nodeNum][nodePhase]['PV rating [kVA]'] += float(node['ndata']['rated_power']) * 1e-3
        elif node['nclass'] == 'inverter' and 'ibat' in node['id']:
            numBat += 1
            ratedBat += int(node['ndata']['rated_power'])
            nodeNum = int(node['id'].split('_')[1][1:])
            nodePhase = node['id'].split('_')[2]
            spotLoads[nodeNum][nodePhase]['Batteries'] += 1
            spotLoadsDF.loc[nodeNum][nodePhase]['Batteries'] += 1
            spotLoads[nodeNum][nodePhase]['Battery rating [kVA]'] += float(node['ndata']['rated_power']) * 1e-3
            spotLoadsDF.loc[nodeNum][nodePhase]['Battery rating [kVA]'] += float(node['ndata']['rated_power']) * 1e-3
        elif node['nclass'] == 'house':
            numHouses += 1
            nodeNum = int(node['id'].split('_')[1][1:])
            nodePhase = node['id'].split('_')[2]
            spotLoads[nodeNum][nodePhase]['Houses'] += 1
            spotLoadsDF.loc[nodeNum][nodePhase]['Houses'] += 1

    print(f'{numSol} PVs totaling {ratedSol * 1e-3} kW rated power')
    print(f'{numBat} batteries totaling {ratedBat * 1e-3} kW rated power')
    for spot in spotLoads.keys():
        for phase in spotLoads[spot].keys():
            spotLoads[spot][phase]['DER rating [kVA]'] = spotLoads[spot][phase]['PV rating [kVA]'] + \
                                                         spotLoads[spot][phase]['Battery rating [kVA]']
    fileSpotLoads = f'spotLoads.json'
    jsonFp = open(os.path.abspath(os.path.join('./', fileSpotLoads)), 'w')
    json.dump(spotLoads, jsonFp)
    jsonFp.close()
    for spot in spotLoadsDF.index:
        for phase in phases:
            spotLoadsDF.loc[spot][phase]['DER rating [kVA]'] = spotLoadsDF.loc[spot][phase]['PV rating [kVA]'] + \
                                                               spotLoadsDF.loc[spot][phase]['Battery rating [kVA]']
            # meas = ['Houses', 'PVs', 'PV rating [kVA]', 'Batteries', 'Battery rating [kVA]', 'DER rating [kVA]']
    # mIndex = pd.MultiIndex.from_product([phases, meas], names = ['Phase', 'Measurement'])
    # mIndex = pd.MultiIndex.from_product([spotLoadNums, phases], names = ['Node', 'Phase'])
    # print(mIndex)
    # df = pd.DataFrame(np.zeros((len(spotLoadNums), len(phases) * len(meas))), index = spotLoadNums, columns = mIndex)
    # df = pd.DataFrame(index = mIndex, columns = meas)
    print(spotLoadsDF)
    spotLoadsDF.to_excel(os.path.abspath(os.path.join(glmFolder, f'spotLoads_V{version}.xlsx')))
    # print(spotLoads)
    # Do not save figures
    # plotSaveGraph(popG)
    # Save figures
    # plotSaveGraph(popG, fileName = glmFile)

    if showGraph:
        plt.show()

    # pos = nx.planar_layout(G)
    # # pos = nx.spectral_layout(G)
    # nx.draw(G, pos=pos, with_labels=True)
    # plt.show()
