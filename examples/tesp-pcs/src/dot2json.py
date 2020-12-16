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
  main('../files/R1-12.47-1.dot', '../files/R1-12.47-1_dot.json')
