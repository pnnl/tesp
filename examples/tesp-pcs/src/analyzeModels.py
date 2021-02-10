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
  ids = np.unique(np.array([re.findall(pattern1, node['id']) for node in dotModel['nodes']]))
  print('The unique ids of the nodes are: {0} (total {1})'.format(ids, len(ids)))

  capNodes = [node for node in dotModel['nodes'] if ids[0] in node['id']]
  capNodes = sorted(capNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
  loadNodes = [node for node in dotModel['nodes'] if ids[1] in node['id']]
  loadNodes = sorted(loadNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
  meterNodes = [node for node in dotModel['nodes'] if ids[2] in node['id']]
  meterNodes = sorted(meterNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
  nodeNodes = [node for node in dotModel['nodes'] if ids[3] in node['id']]
  #print(np.array([int(re.findall(pattern2, node['id'])[0]) for node in dotModel['nodes']]))
  nodeNodes = sorted(nodeNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
  tmNodes = [node for node in dotModel['nodes'] if ids[4] in node['id']]
  tmNodes = sorted(tmNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))
  tnNodes = [node for node in dotModel['nodes'] if ids[5] in node['id']]
  tnNodes = sorted(tnNodes, key = lambda i: int(re.findall(pattern2, i['id'])[0]))

  houses = [node for node in dotModel['nodes'] if 'tn' in node['id'] and 'house' in node['shape']]
  print('In the DOT graph there are:')
  print('\tnodes: {0}, out of which'.format(len(dotModel['nodes'])))
  print('\t\tcap: {0} ({1} .. {2})'.format(len(capNodes), capNodes[0]['id'], capNodes[-1]['id']))
  print('\t\tload: {0} ({1} .. {2})'.format(len(loadNodes), loadNodes[0]['id'], loadNodes[-1]['id']))
  print('\t\tmeter: {0} ({1} .. {2})'.format(len(meterNodes), meterNodes[0]['id'], meterNodes[-1]['id']))
  print('\t\tnode: {0} ({1} .. {2})'.format(len(nodeNodes), nodeNodes[0]['id'], nodeNodes[-1]['id']))
  print('\t\ttm: {0} ({1} .. {2})'.format(len(tmNodes), tmNodes[0]['id'], tmNodes[-1]['id']))
  print('\t\ttn: {0} ({1} .. {2})'.format(len(tnNodes), tnNodes[0]['id'], tnNodes[-1]['id']))
  print('\t\t------------------------')
  print('\t\ttotal: {0}'.format(len(capNodes) +
                                len(loadNodes) + len(meterNodes) + len(nodeNodes) + len(tmNodes) + len(tnNodes)))
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
  glmMeterNodes = [node for node in glmModel['billingmeters'].keys() if bmIds[0].split('_')[0] in node]
  glmTnNodes = [node for node in glmModel['billingmeters'].keys() if bmIds[1].split('_')[0] in node]
  # GLM triplex nodes extracted, sorted and unique
  glmMeterNodesNum = np.unique(np.array(sorted([int(meter.split('_')[5]) for meter in glmMeterNodes])))
  glmTnNodesNum = np.unique(np.array(sorted([int(tn.split('_')[5]) for tn in glmTnNodes])))

  bmTnGkids = np.array([])
  for bm in glmTnNodes:
    bmTnGkids = np.append(bmTnGkids, np.array(glmModel['billingmeters'][bm]['children']))
  tnGkidId = np.unique(np.array(sorted([child.split('_')[4] + '_' + child.split('_')[6] for child in bmTnGkids])))
  bmHse = [bmGkid for bmGkid in bmTnGkids if tnGkidId[0].split('_')[1] in bmGkid]
  bmBat = [bmGkid for bmGkid in bmTnGkids if tnGkidId[1].split('_')[1] in bmGkid]
  bmSol = [bmGkid for bmGkid in bmTnGkids if tnGkidId[2].split('_')[1] in bmGkid]

  bmMeterGkids = np.array([])
  for bm in glmMeterNodes:
    bmMeterGkids = np.append(bmMeterGkids, np.array(glmModel['billingmeters'][bm]['children']))
  meterGkidId = np.unique(np.array(sorted([child.split('_')[4] + '_' + child.split('_')[6] for child in bmMeterGkids])))
  bmLoadZones = [bmGkid for bmGkid in bmMeterGkids if meterGkidId[0].split('_')[1] in bmGkid]

  hsIds = np.unique(sorted([hs.split('_')[4] + '_' + hs.split('_')[6] for hs in glmModel['houses'].keys()]))
  hsTnHses = [hs for hs in glmModel['houses'].keys() if hsIds[1].split('_')[0] in hs]
  hsLoadHses = [hs for hs in glmModel['houses'].keys() if hsIds[0].split('_')[0] in hs]
  
  hsTnHsesParent = np.array([])
  for hs in hsTnHses:
    hsTnHsesParent = np.append(hsTnHsesParent, np.array(glmModel['houses'][hs]['parent']))
  hsTnHsesParentIds = np.unique(np.array(sorted([parent.split('_')[4] + '_' + parent.split('_')[6] for parent in hsTnHsesParent])))

  hsLoadHsesParent = np.array([])
  for hs in hsLoadHses:
    hsLoadHsesParent = np.append(hsLoadHsesParent, np.array(glmModel['houses'][hs]['parent']))
  hsLoadHsesParentIds = np.unique(np.array(sorted([parent.split('_')[4] + '_' + parent.split('_')[6] if len(parent.split('_')) > 6 else parent.split('_')[4] for parent in hsLoadHsesParent])))

  print('The unique IDs of the billingmeters are: {0}'.format(bmIds))
  print('\tGrand kids to the billing meters `{0}` IDs: {1}'.format(bmIds[1], tnGkidId))
  print('\tGrand kids to the billing meters `{0}` IDs: {1}'.format(bmIds[0], meterGkidId))
  print('The unique IDs of the houses are: {0}'.format(hsIds))
  print('\tParent for `{0}` IDs: {1}'.format(hsIds[1], hsTnHsesParentIds))
  print('\tParent for `{0}` IDs: {1}'.format(hsIds[0], hsLoadHsesParentIds))
  print('In the populated GLM dict there are:')
  print('\tcapacitors: {0}'.format(len(glmModel['capacitors'])))
  print('\tbillingmeters: {0}'.format(len(glmModel['billingmeters'])))
  print('\t\ttriplex nodes: {0} (_tn_{1}_mtr_# .. _tn_{2}_mtr_#)'.format(len(glmTnNodesNum), glmTnNodesNum[0], glmTnNodesNum[-1]))
  print('\t\tmeters on triplex nodes (_tn_#_mtr_#): {0}'.format(len(glmTnNodes)))
  print('\t\t\thouses: {0}'.format(len(bmHse)))
  print('\t\t\tbatteries: {0}'.format(len(bmBat)))
  print('\t\t\tPVs: {0}'.format(len(bmSol)))
  print('\t\tmeters (_meter_#): {0}'.format(len(glmMeterNodes)))
  print('\t\tmeters: {0} (_meter_{1} .. _meter_{2})'.format(len(glmMeterNodesNum), glmMeterNodesNum[0], glmMeterNodesNum[-1]))
  print('\t\t\tload zones: {0}'.format(len(bmLoadZones)))
  print('\thouses: {0}'.format(len(glmModel['houses'])))
  print('\t\thse: {0}'.format(len(hsTnHses)))
  print('\t\tload: {0}'.format(len(hsLoadHses)))
  print('\tregulators: {0}'.format(len(glmModel['regulators'])))

  return glmTnNodes, glmTnNodesNum


def main(feederName):
  """
  This main function analyzes the DOT and GLM, and connects them to create the JSON needed for the ns-3 model

  Parameters
  ----------
  feederName : string
    The name of the prototypical taxonomy feeder to be analyzed.

  Returns
  -------
  **********

  """
  G = nx.Graph()
  feederRename = feederName.replace('-','_').replace('.', '_')
  dotJSONfile = os.path.abspath('../files/{0}_dot.json'.format(feederName))
  json_fp = open(os.path.abspath('./{0}'.format(dotJSONfile)), 'r')
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
                  'x': float(node['pos'].split(',')[0]),
                  'y': float(node['pos'].split(',')[1])
                }
  
  glmJSONfile = os.path.abspath('../files/{0}_processed_glm_dict.json'.format(feederName))
  json_fp = open(os.path.abspath('./{0}'.format(glmJSONfile)), 'r')
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
        'x': float(mtrDot['pos'].split(',')[0]),
        'y': float(mtrDot['pos'].split(',')[1])
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
          'x': G.nodes()[currBillMtr]['ndata']['x'],
          'y': G.nodes()[currBillMtr]['ndata']['y']
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
  taxRoot = ['R1-12.47-1', 'R1-12.47-2', 'R1-12.47-3', 'R1-12.47-4', 'R1-25.00-1', 'R2-12.47-1',
             'R2-12.47-2', 'R2-12.47-3', 'R2-25.00-1', 'R2-35.00-1', 'R3-12.47-1', 'R3-12.47-2',
             'R3-12.47-3', 'R4-12.47-1', 'R4-12.47-2', 'R4-25.00-1', 'R5-12.47-1', 'R5-12.47-2',
             'R5-12.47-3', 'R5-12.47-4', 'R5-12.47-5', 'R5-25.00-1', 'R5-35.00-1', 'GC-12.47-1']
  for feeder in taxRoot:
    print('\nAnalyzing feeder -->> {0}'.format(feeder))
    main(feeder)
