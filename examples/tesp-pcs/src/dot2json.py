# -*- coding: utf-8 -*-
"""
.dot to networkx graph to .json

.. module:: dot2json

:synopsis: This module load a DOT file (network graph) into a networkx graph to save it into a JSON structure

:platform: Unix

.. moduleauthor:: Laurentiu Marinovici (PNNL)

"""
__docformat__ = 'reStructuredText'
import networkx as nx
import json
import os

def main(dotFile, jsonFile):
  """
  Loads a .dot file representing the GridLAB-D taxonomy feeder graph and saves it as a JSON structure in a file.

  Parameters
  ----------
  dotFile : str
    Path to dotFile input file.

  Returns
  -------
  jsonFile : str
    Path to output JSON file.

  """
  dot_graph = nx.drawing.nx_agraph.read_dot(dotFile)
  json_graph = nx.readwrite.node_link_data(dot_graph)
  # print([json_graph['nodes'][x]['id'] for x in range(
  #    len(json_graph['nodes'])) if 'load' in json_graph['nodes'][x]['id']])
  json_fp = open(jsonFile, 'w')
  json.dump(json_graph, json_fp)
  json_fp.close()

if __name__ == '__main__':
  taxRoot = ['R1-12.47-1', 'R1-12.47-2', 'R1-12.47-3', 'R1-12.47-4', 'R1-25.00-1', 'R2-12.47-1',
             'R2-12.47-2', 'R2-12.47-3', 'R2-25.00-1', 'R2-35.00-1', 'R3-12.47-1', 'R3-12.47-2',
             'R3-12.47-3', 'R4-12.47-1', 'R4-12.47-2', 'R4-25.00-1', 'R5-12.47-1', 'R5-12.47-2',
             'R5-12.47-3', 'R5-12.47-4', 'R5-12.47-5', 'R5-25.00-1', 'R5-35.00-1', 'GC-12.47-1']
  for feeder in taxRoot:
    inFile = os.path.abspath('../files/{0}.dot'.format(feeder))
    outFile = os.path.abspath('../files/{0}_dot.json'.format(feeder))
    main(inFile, outFile)
