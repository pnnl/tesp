# -*- coding: utf-8 -*-
"""
DOT and GLM model analysis.

.. module:: analyzeModels

:synopsis: Analyze the DOT and GLM models, based on their JSON structures in order to place the GLM nodes at he locations supplied by the DOT file. In the end, a networkx JSON file is saved to describe the fedder nodes and their links, that is used later to populate an ns-3 model.

:platform: Unix

.. moduleauthor:: Laurentiu Marinovici (PNNL)

"""
__docformat__ = 'reStructuredText'
import networkx as nx
import json
import numpy as np
import re
import os
import matplotlib.pyplot as plt

def analyzeDOT(dotModel):
  """
  Loads a DOT model in its jSON structure, and returns the list of the triplex nodes and triplex meters.

  Parameters
  ----------
  dotModel : JSON structure
    The JSON coverted DOT model.

  Returns
  -------
  tnNodes, tmNodes : list
    Lists of triplex nodes and triplex meters.

  """
  shapes = np.unique(np.array([node['shape'] for node in dotModel['nodes']]))
  print('======================== DOT ==================================')
  print('The unique shapes of the nodes are: {0}'.format(shapes))

  pattern1 = '[a-zA-Z]+'
  pattern2 = '[0-9]+'
  types = [re.findall(pattern1, node['id']) for node in dotModel['nodes']]
  # For some reason, in some .dot files, some IDs are only numbers, which make previous call to find pattern1 to return an empty array.
  # One first fix is to consider those as 'node' ID.
  incCount = 0
  for i in range(len(types)):
    if types[i] == []:
      incCount += 1
      types[i] = 'node'
      dotModel['nodes'][i]['id'] = 'node' + dotModel['nodes'][i]['id']
      dotModel['nodes'][i]['xlabel'] = 'node' + dotModel['nodes'][i]['xlabel']
      print('{0} -- {1}\n'.format(dotModel['nodes'][i]['id'], types[i]))
      print(dotModel['nodes'][i])
  if incCount == 1:
    print('\t!!!!! There is {0} inconsistency in node naming.!!!!!'.format(incCount))
  else:
    print('\t!!!!! There are {0} inconsistencies in node naming.!!!!!'.format(incCount))
  ids = np.unique(np.array([re.findall(pattern1, node['id']) for node in dotModel['nodes']])) # .astype('string')
  print('The unique ids of the nodes are: {0} (total {1})'.format(ids, len(ids)))
  print('In the DOT graph there are:')
  print('\tnodes: {0}, out of which, for each id'.format(len(dotModel['nodes'])))
  
  total = 0 # counting all elements per id to verify
  for id in ids:
    if 'cap' in id:
      capNodes = [node for node in dotModel['nodes'] if id in node['id']]
      capNodes = sorted(capNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
      total += len(capNodes)
      print('\t\tcap: {0} ({1} .. {2})'.format(len(capNodes), capNodes[0]['id'], capNodes[-1]['id']))
    elif 'load' in id:
      loadNodes = [node for node in dotModel['nodes'] if id in node['id']]
      loadNodes = sorted(loadNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
      total += len(loadNodes)
      print('\t\tload: {0} ({1} .. {2})'.format(len(loadNodes), loadNodes[0]['id'], loadNodes[-1]['id']))
    elif 'meter' in id:
      meterNodes = [node for node in dotModel['nodes'] if id in node['id']]
      meterNodes = sorted(meterNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
      total += len(meterNodes)
      print('\t\tmeter: {0} ({1} .. {2})'.format(len(meterNodes), meterNodes[0]['id'], meterNodes[-1]['id']))
    elif 'node' in id:
      nodeNodes = [node for node in dotModel['nodes'] if id in node['id']]
      nodeNodes = sorted(nodeNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
      total += len(nodeNodes)
      print('\t\tnode: {0} ({1} .. {2}, {3})'.format(len(nodeNodes), nodeNodes[0]['id'], nodeNodes[-2]['id'], nodeNodes[-1]['id']))
    elif 'tm' in id:
      tmNodes = [node for node in dotModel['nodes'] if id in node['id']]
      tmNodes = sorted(tmNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
      total += len(tmNodes)
      print('\t\ttm: {0} ({1} .. {2})'.format(len(tmNodes), tmNodes[0]['id'], tmNodes[-1]['id']))
    elif 'tn' in id:
      tnNodes = [node for node in dotModel['nodes'] if id in node['id']]
      tnNodes = sorted(tnNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
      total += len(tnNodes)
      print('\t\ttn: {0} ({1} .. {2})'.format(len(tnNodes), tnNodes[0]['id'], tnNodes[-1]['id']))
      
  houses = [node for node in dotModel['nodes'] if 'tn' in node['id'] and 'house' in node['shape']]
  print('\t\t------------------------')
  print('\t\ttotal: {0}'.format(total))
  print('\tlinks: {0}'.format(len(dotModel['links'])))
  return tnNodes, tmNodes

def analyzeGLMdict(glmModel):
  """
  Loads a GLM model in its JSON structure, and returns the list of the billing meters and their numbers.

  Parameters
  ----------
  glmModel : JSON structure
    The JSON dict of the GLM model.

  Returns
  -------
  glmTnNodes, glmTnNodesNum : list
    Lists of billing meters and their unique numbers.

  """
  print('======================== GLM ==================================')
  print('The populated GLM dict has the following keys: {0}'.format(glmModel.keys()))
  bmIds = np.unique(sorted([bm.split('_')[4] + '_' + bm.split('_')[6] if len(
      bm.split('_')) > 6 else bm.split('_')[4] for bm in glmModel['billingmeters'].keys()]))
  print('The unique IDs of the billingmeters are: {0}'.format(bmIds))
  for bmId in bmIds:
    if 'meter' in bmId:
      glmMeterNodes = [node for node in glmModel['billingmeters'].keys() if bmId.split('_')[0] in node]
      glmMeterNodesNum = np.unique(np.array(sorted([int(meter.split('_')[5]) for meter in glmMeterNodes])))
      bmMeterGkids = np.array([])
      for bm in glmMeterNodes:
        bmMeterGkids = np.append(bmMeterGkids, np.array(glmModel['billingmeters'][bm]['children']))
      meterGkidIds = np.unique(np.array(sorted([child.split('_')[4] + '_' + child.split('_')[6] for child in bmMeterGkids])))
      for meterGkidId in meterGkidIds:
        if 'load_zone' in meterGkidId:
          bmLoadZones = [bmGkid for bmGkid in bmMeterGkids if meterGkidId.split('_')[1] in bmGkid]
        elif 'load_bldg' in meterGkidId:
          bmLoadBldgs = [bmGkid for bmGkid in bmMeterGkids if meterGkidId.split('_')[1] in bmGkid]
      print('\tGrand kids to the billing meters `{0}` IDs: {1}'.format(bmId, meterGkidId))
    elif 'tn_mtr' in bmId:
      glmTnNodes = [node for node in glmModel['billingmeters'].keys() if bmId.split('_')[0] in node]
      glmTnNodesNum = np.unique(np.array(sorted([int(tn.split('_')[5]) for tn in glmTnNodes])))
      bmTnGkids = np.array([])
      # GLM triplex nodes extracted, sorted and unique
      for bm in glmTnNodes:
        bmTnGkids = np.append(bmTnGkids, np.array(glmModel['billingmeters'][bm]['children']))
      tnGkidIds = np.unique(np.array(sorted([child.split('_')[4] + '_' + child.split('_')[6] for child in bmTnGkids])))
      for tnGkidId in tnGkidIds:
        if 'tn_hse' in tnGkidId:
          bmHse = [bmGkid for bmGkid in bmTnGkids if tnGkidId.split('_')[1] in bmGkid]
        elif 'tn_ibat' in tnGkidId:
          bmBat = [bmGkid for bmGkid in bmTnGkids if tnGkidId.split('_')[1] in bmGkid]
        elif 'tn_isol' in tnGkidId:
          bmSol = [bmGkid for bmGkid in bmTnGkids if tnGkidId.split('_')[1] in bmGkid]
      print('\tGrand kids to the billing meters `{0}` IDs: {1}'.format(bmId, tnGkidId))
  
  hsIds = np.unique(sorted([hs.split('_')[4] + '_' + hs.split('_')[6] for hs in glmModel['houses'].keys()]))
  print('The unique IDs of the houses are: {0}'.format(hsIds))
  for hsId in hsIds:
    if 'tn_hse' in hsId:
      hsTnHses = [hs for hs in glmModel['houses'].keys() if hsId.split('_')[0] in hs]
      hsTnHsesParent = np.array([])
      for hs in hsTnHses:
        hsTnHsesParent = np.append(hsTnHsesParent, np.array(glmModel['houses'][hs]['parent']))
      hsTnHsesParentIds = np.unique(np.array(sorted([parent.split('_')[4] + '_' + parent.split('_')[6] for parent in hsTnHsesParent])))
      print('\tParent for `{0}` IDs: {1}'.format(hsId, hsTnHsesParentIds))
    elif 'load_zone' in hsId:
      hsLoadHses = [hs for hs in glmModel['houses'].keys() if hsId.split('_')[0] in hs]
      hsLoadHsesParent = np.array([])
      for hs in hsLoadHses:
        hsLoadHsesParent = np.append(hsLoadHsesParent, np.array(glmModel['houses'][hs]['parent']))
      hsLoadHsesParentIds = np.unique(np.array(sorted([parent.split('_')[4] + '_' + parent.split('_')[6] if len(parent.split('_')) > 6 else parent.split('_')[4] for parent in hsLoadHsesParent])))
      print('\tParent for `{0}` IDs: {1}'.format(hsIds, hsLoadHsesParentIds))
  #hsTnHses = [hs for hs in glmModel['houses'].keys() if hsIds[1].split('_')[0] in hs]
  #hsLoadHses = [hs for hs in glmModel['houses'].keys() if hsIds[0].split('_')[0] in hs]
  
  print('In the populated GLM dict there are:')
  if 'capacitors' in glmModel.keys():
    print('\tcapacitors: {0}'.format(len(glmModel['capacitors'])))
  if 'billingmeters' in glmModel.keys():
    print('\tbillingmeters: {0}'.format(len(glmModel['billingmeters'])))
  if 'glmTnNodesNum' in locals():
    print('\t\ttriplex nodes: {0} (_tn_{1}_mtr_# .. _tn_{2}_mtr_#)'.format(len(glmTnNodesNum), glmTnNodesNum[0], glmTnNodesNum[-1]))
  if 'glmTnNodes' in locals():
    print('\t\tmeters on triplex nodes (_tn_#_mtr_#): {0}'.format(len(glmTnNodes)))
  if 'bmHse' in locals():
    print('\t\t\thouses: {0}'.format(len(bmHse)))
  if 'bmBat' in locals():
    print('\t\t\tbatteries: {0}'.format(len(bmBat)))
  if 'bmSol' in locals():
    print('\t\t\tPVs: {0}'.format(len(bmSol)))
  if 'glmMeterNodes' in locals():
    print('\t\tmeters (_meter_#): {0}'.format(len(glmMeterNodes)))
  if 'glmMeterNodesNum' in locals():
    print('\t\tmeters: {0} (_meter_{1} .. _meter_{2})'.format(len(glmMeterNodesNum), glmMeterNodesNum[0], glmMeterNodesNum[-1]))
  if 'bmLoadZones' in locals():
    print('\t\t\tload zones: {0}'.format(len(bmLoadZones)))
  if 'houses' in glmModel.keys():
    print('\thouses: {0}'.format(len(glmModel['houses'])))
  if 'hsTnHses' in locals():
    print('\t\thse: {0}'.format(len(hsTnHses)))
  if 'hsLoadHses' in locals():
    print('\t\tload: {0}'.format(len(hsLoadHses)))
  if 'regulators' in glmModel.keys():
    print('\tregulators: {0}'.format(len(glmModel['regulators'])))

  return glmTnNodes, glmTnNodesNum

def printerPoints2Feet(prtPtVal):
  """
  Translation from printer point value to real world feet
  
  Parameters
  ----------
  prtPtVal : float
    Value in printer's points

  Returns
  -------
  ftVal : float
    Value in real world feet
  """
  ftVal = 200 * prtPtVal / 72

  return ftVal

def createJSONforNS3model(feederName, deltaFt):
  """
  This main function analyzes the DOT and GLM, and connects them to create the JSON needed for the ns-3 model

  Parameters
  ----------
  feederName : string
    The name of the prototypical taxonomy feeder to be analyzed.
  
  deltaFt : float
    A value in Ft, used to randomize the positions of devices downstream from a triplex node, whose values are extracted from the DOT files

  Returns
  -------
  **********

  """
  rng = np.random.default_rng(12345)
  G = nx.Graph()
  feederRename = feederName.replace('-','_').replace('.', '_')
  dotJSONfile = os.path.abspath('../files/{0}_dot.json'.format(feederName))
  json_fp = open(dotJSONfile, 'r')
  dotModel = json.load(json_fp)
  json_fp.close()
  dotLinks = dotModel['links']
  [dotTns, dotTms] = analyzeDOT(dotModel)
  nodesLevel1 = [x for x in dotTns for y in dotLinks if x['id'] == y['source']]
  for node in nodesLevel1:
    nodeN = int(re.findall('[0-9]+', node['id'])[0])
    G.add_node('{0}_tn_{1}'.format(feederRename, nodeN))
    G.nodes()['{0}_tn_{1}'.format(feederRename, nodeN)]['nclass'] = 'node'
    G.nodes()['{0}_tn_{1}'.format(feederRename, nodeN)]['ndata'] = {
                  'x': printerPoints2Feet(float(node['pos'].split(',')[0])),
                  'y': printerPoints2Feet(float(node['pos'].split(',')[1]))
                }
  
  glmJSONfile = os.path.abspath('../files/{0}_processed_glm_dict.json'.format(feederName))
  json_fp = open(glmJSONfile, 'r')
  glmModel = json.load(json_fp)
  json_fp.close()
  # the billing meters connected to each triplex node
  [glmTnBillMtrs, glmTnNumBillMtrs] = analyzeGLMdict(glmModel)
  for mtrDot in dotTms:
    mtrN = int(re.findall('[0-9]+', mtrDot['id'])[0])
    currBillMtrs = [x for x in glmTnBillMtrs if int(x.split('_')[5]) == mtrN]
    for currBillMtr in currBillMtrs:
      G.add_node(currBillMtr)
      G.nodes()[currBillMtr]['nclass'] = 'billing_meter'
      G.nodes()[currBillMtr]['ndata'] = {
        'x': printerPoints2Feet(float(mtrDot['pos'].split(',')[0])) + rng.uniform(low = -deltaFt, high = deltaFt, size = 1)[0],
        'y': printerPoints2Feet(float(mtrDot['pos'].split(',')[1])) + rng.uniform(low = -deltaFt, high = deltaFt, size = 1)[0]
      }
      # edge/link from triplex node to each billing meter connected to it
      # The graph is not directed so the order of the arguments in add_edge does not necessarily mean (source, destination)
      edgeTnSource = '{0}_tn_{1}'.format(feederRename, mtrN)
      G.add_edge(edgeTnSource, currBillMtr,
                 ename = 'line_tn_{0}_mtr_{1}'.format(mtrN, currBillMtr.split('_')[-1]),
                 edata = {
                   'from': edgeTnSource,
                   'to': currBillMtr,
                   'length': 0
                 })
      for child in glmModel['billingmeters'][currBillMtr]['children']:
        G.add_node(child)
        G.nodes[child]['ndata'] = {
          'x': G.nodes()[currBillMtr]['ndata']['x'] + rng.uniform(low = -deltaFt/4, high = deltaFt/4, size = 1)[0],
          'y': G.nodes()[currBillMtr]['ndata']['y'] + rng.uniform(low = -deltaFt/4, high = deltaFt/4, size = 1)[0]
        }
        if child.split('_')[6] == 'hse':
          # Each house has a house meter between itself and the billing meter according to the GLM dict.
          G.nodes()[child]['nclass'] = 'house'
          if glmModel['houses'][child]['parent'].split('_')[6] == 'mhse':
            G.add_node(glmModel['houses'][child]['parent'])
            G.nodes()[glmModel['houses'][child]['parent']]['nclass'] = 'house meter'
            G.nodes()[glmModel['houses'][child]['parent']]['ndata'] = {
              'x': G.nodes()[child]['ndata']['x'],
              'y': G.nodes()[child]['ndata']['y']
            }
            # Edge/link from BILLING METER to HOUSE METER
            G.add_edge(currBillMtr, glmModel['houses'][child]['parent'],
                       ename = 'line_tn_{0}_mtr_{1}_mhse_{2}'.format(mtrN, currBillMtr.split('_')[-1], glmModel['houses'][child]['parent'].split('_')[-1]),
                       edata = {
                         'from': currBillMtr,
                         'to': glmModel['houses'][child]['parent'],
                         'length': 0
                       })
            # Edge/link from HOUSE METER to actual HOUSE
            G.add_edge(glmModel['houses'][child]['parent'], child,
                       ename = 'line_tn_{0}_mhse_{1}_hse_{2}'.format(mtrN, glmModel['houses'][child]['parent'].split('_')[-1], child.split('_')[-1]),
                       edata = {
                         'from': glmModel['houses'][child]['parent'],
                         'to': child,
                         'length': 0
                       })
        elif child.split('_')[6] == 'ibat' or child.split('_')[6] == 'isol':
          G.nodes()[child]['nclass'] = 'inverter'
          # Accordding to the GLM dict there are children or parents to the inverters. However, they do exist in the actual network configuration. Hence they are added to the network configuration for ns-3 model potentially.
          if child.split('_')[6] == 'ibat':
            parentName = '{0}_tn_{1}_mbat_{2}'.format(feederRename, mtrN, child.split('_')[-1])
            G.add_node(parentName)
            G.nodes()[parentName]['nclass'] = 'battery meter'
            G.nodes()[parentName]['ndata'] = {
              'x': G.nodes()[child]['ndata']['x'],
              'y': G.nodes()[child]['ndata']['y']
            }
            # Edge/link from BILLING METER to BATTERY METER
            G.add_edge(currBillMtr, parentName,
                       ename = 'line_tn_{0}_mtr_{1}_mbat_{2}'.format(mtrN, currBillMtr.split('_')[-1], parentName.split('_')[-1]),
                       edata = {
                         'from': currBillMtr,
                         'to': parentName,
                         'length': 0
                       })
            # Edge/link from BATTERY METER to BATTERY INVERTER
            G.add_edge(parentName, child,
                       ename = 'line_tn_{0}_mbat_{1}_ibat_{2}'.format(mtrN, parentName.split('_')[-1], child.split('_')[-1]),
                       edata = {
                         'from': parentName,
                         'to': child,
                         'length': 0
                       })
            gchildName = '{0}_tn_{1}_bat_{2}'.format(feederRename, mtrN, child.split('_')[-1])
            G.add_node(gchildName)
            G.nodes()[gchildName]['nclass'] = 'battery'
            G.nodes()[gchildName]['ndata'] = {
              'x': G.nodes()[child]['ndata']['x'],
              'y': G.nodes()[child]['ndata']['y']
            }
            # Edge/link from BATTERY INVERTER to BATTERY
            G.add_edge(child, gchildName,
                       ename = 'line_tn_{0}_ibat_{1}_bat_{2}'.format(mtrN, child.split('_')[-1], gchildName.split('_')[-1]),
                       edata = {
                         'from': child,
                         'to': gchildName,
                         'length': 0
                       })
          elif child.split('_')[6] == 'isol':
            parentName = '{0}_tn_{1}_msol_{2}'.format(feederRename, mtrN, child.split('_')[-1])
            G.add_node(parentName)
            G.nodes()[parentName]['nclass'] = 'solar meter'
            G.nodes()[parentName]['ndata'] = {
              'x': G.nodes()[child]['ndata']['x'],
              'y': G.nodes()[child]['ndata']['y']
            }
            # Edge/link from BILLING METER to SOLAR METER
            G.add_edge(currBillMtr, parentName,
                       ename = 'line_tn_{0}_mtr_{1}_msol_{2}'.format(mtrN, currBillMtr.split('_')[-1], parentName.split('_')[-1]),
                       edata = {
                         'from': currBillMtr,
                         'to': parentName,
                         'length': 0
                       })
            # Edge/link from SOLAR METER to SOLAR INVERTER
            G.add_edge(parentName, child,
                       ename = 'line_tn_{0}_msol_{1}_isol_{2}'.format(mtrN, parentName.split('_')[-1], child.split('_')[-1]),
                       edata = {
                         'from': parentName,
                         'to': child,
                         'length': 0
                       })
            gchildName = '{0}_tn_{1}_sol_{2}'.format(feederRename, mtrN, child.split('_')[-1])
            G.add_node(gchildName)
            G.nodes()[gchildName]['nclass'] = 'solar'
            G.nodes()[gchildName]['ndata'] = {
              'x': G.nodes()[child]['ndata']['x'],
              'y': G.nodes()[child]['ndata']['y']
            }
            # Edge/link from SOLAR INVERTER to SOLAR PV
            G.add_edge(child, gchildName,
                       ename = 'line_tn_{0}_isol_{1}_sol_{2}'.format(mtrN, child.split('_')[-1], gchildName.split('_')[-1]),
                       edata = {
                         'from': child,
                         'to': gchildName,
                         'length': 0
                       })
  jsonGraphNS3 = nx.readwrite.json_graph.node_link_data(G)
  jsonFp = open(os.path.abspath('../files/{0}_ns3.json'.format(feederName)), 'w')
  json.dump(jsonGraphNS3, jsonFp)
  jsonFp.close()
  # for key, value in nx.get_node_attributes(G, 'ndata').items():
  #   print(key)
  #   print(value)
  # pos = {key: (value['x'], value['y']) for key, value in nx.get_node_attributes(G, 'ndata').items()}
  # print(pos)
  # nx.draw(G, pos, with_labels = True, node_size = 120)
  # plt.show()

  # nodeNum = 150
  # tn = 'tn{0}'.format(nodeNum)
  # tm = 'tm{0}'.format(nodeNum)
  # tnChild = 'tn{0}'.format(nodeNum + 598)
  # print('-------------------- Analyze node {0} -----------------'.format(tn))
  # tnPos = [x['pos'] for x in dotModel['nodes'] if x['id'] == tn]
  # xtnPos = float(tnPos[0].split(',')[0])
  # ytnPos = float(tnPos[0].split(',')[1])
  # tmPos = [x['pos'] for x in dotModel['nodes'] if x['id'] == tm]
  # xtmPos = float(tmPos[0].split(',')[0])
  # ytmPos = float(tmPos[0].split(',')[1])
  # tnChildPos = [x['pos'] for x in dotModel['nodes'] if x['id'] == tnChild]
  # xtnChildPos = float(tnChildPos[0].split(',')[0])
  # ytnChildPos = float(tnChildPos[0].split(',')[1])
  # print('{0} position:\n\t({1:.2f}, {2:.2f}) printer points\n\t({3:.2f}, {4:.2f}) ft'.format(tn, xtnPos, ytnPos, xtnPos / 72 * 200, ytnPos / 72 * 200))
  # print('{0} position:\n\t({1:.2f}, {2:.2f}) printer points\n\t({3:.2f}, {4:.2f}) ft'.format(tm, xtmPos, ytmPos, xtmPos / 72 * 200, ytmPos / 72 * 200))
  # print('{0} position:\n\t({1:.2f}, {2:.2f}) printer points\n\t({3:.2f}, {4:.2f}) ft'.format(tnChild, xtnChildPos, ytnChildPos, xtnChildPos / 72 * 200, ytnChildPos / 72 * 200))

if __name__ == '__main__':

  # taxRoot = ['R3-12.47-2']
  # taxRoot = ['GC-12.47-1']
  taxRoot = ['R1-12.47-1', 'R1-12.47-2', 'R1-12.47-3', 'R1-12.47-4', 'R1-25.00-1',
             'R2-12.47-1', 'R2-12.47-2', 'R2-12.47-3', 'R2-25.00-1', 'R2-35.00-1',
             'R3-12.47-1', 'R3-12.47-3',
             'R4-12.47-1', 'R4-12.47-2', 'R4-25.00-1',
             'R5-12.47-1', 'R5-12.47-2', 'R5-12.47-3', 'R5-12.47-4', 'R5-12.47-5', 'R5-25.00-1', 'R5-35.00-1']
  # taxRoot = ['R1-12.47-1']
  deltaFt = 100
  for feeder in taxRoot:
    print('\nAnalyzing feeder -->> {0}'.format(feeder))
    createJSONforNS3model(feeder, deltaFt)
