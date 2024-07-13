# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 13:16:45 2019

@author: monish.mukherjee
"""

import json
import numpy as np

def createJson(feeder_name, model,clock,directives,modules,classes, basedir):
    
    feeder = {}
    feeder['directed'] = bool(1)
    feeder['graph'] = {}
    feeder['links'] = []
    feeder['multigraph'] = bool(1)
    feeder['nodes'] = []
    
   
    #######################    Feeder Links   #################################
    Link_models = ['overhead_line','underground_line', 'triplex_line', 'regulator', 'fuse', 'recloser','switch', 'fuse','transformer', 'sectionalizer']
    for item in range(len(Link_models)):
        if Link_models[item] in model:
            for link_item in model[Link_models[item]]:
                if Link_models[item] == 'transformer' or Link_models[item] == 'regulator':
                    feeder['links'].append({'eclass': Link_models[item],
                                        'edata': model[Link_models[item]][link_item],
                                        'ename': link_item,
                                        'source': model[Link_models[item]][link_item]['from'],
                                        'target': model[Link_models[item]][link_item]['to'],
                                        "weight": 1,
                                        'Transformer': 'True'})
                elif Link_models[item] == 'switch' or Link_models[item] == 'fuse' or Link_models[item] == 'recloser' :
                    if model[Link_models[item]][link_item]['status'] == 'CLOSED':
                        feeder['links'].append({'eclass': Link_models[item],
                                            'edata': model[Link_models[item]][link_item],
                                            'ename': link_item,
                                            'source': model[Link_models[item]][link_item]['from'],
                                            'target': model[Link_models[item]][link_item]['to'],
                                            "weight": 2,
                                            'Transformer': 'False'})
                else:
                    # print(model[Link_models[item]][link_item], item, link_item)
                    feeder['links'].append({'eclass': Link_models[item],
                                        'edata': model[Link_models[item]][link_item],
                                        'ename': link_item,
                                        'source': model[Link_models[item]][link_item]['from'],
                                        'target': model[Link_models[item]][link_item]['to'],
                                        "weight":  float(model[Link_models[item]][link_item]['length']),                            
                                        'Transformer': 'False'})
                    
                
           
 
    ################## feeder nodes, triplex_node and  substation #############
    ## update this list based on the assets that you want to capture in graph nodes
    # node_models = ['node', 'meter', 'load', 'inverter_dyn']
    # node_models = ['node', 'meter', 'load', 'triplex_node', 'triplex_meter'] 
    node_models = ['node', 'meter', 'load', 'triplex_node', 'triplex_meter', 'house'] 
    for it in range(len(node_models)):
    
        for node in model[node_models[it]]:
            # print(node_models[it], it, node)
            feeder['nodes'].append({'id': node,
                                    'nclass': node_models[it],
                                    'ndata': {}})
            if 'parent' in model[node_models[it]][node]:
                feeder['links'].append({'eclass': 'load-node',
                                        'edata': {},
                                        'ename': node + '_' + model[node_models[it]][node]['parent'],
                                        'source': model[node_models[it]][node]['parent'],
                                        'target': node,
                                        "weight": 2,
                                        'Transformer': 'False'})
 
    
            
    #################   Printing to Json  #####################
    Json_file = json.dumps(feeder, sort_keys=True, indent=4, separators=(',', ': '))    
    fp = open(basedir + feeder_name + '_networkx.json', 'w')
    print(Json_file, file=fp)
    fp.close()
    
    return feeder
    
                 
                
                
            
    
   
    
        
    
    
    
    
    
