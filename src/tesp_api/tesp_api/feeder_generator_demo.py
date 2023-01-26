#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019-2023 Battelle Memorial Institute
"""
Created on Tue Jan 17 14:05:08 2023

This script attempts to demonstrate the usage of the new TESP API to modify GridLAB-D models.


@author: hard312
"""




import json
import argparse
import logging
import pprint
import sys
import os
import sys
import networkx as nx

# Getting all the existing tesp_support stuff
#   Assumes were in the tesp_api folder
# sys.path.append('../../tesp_support')

# Setting a few environment variables so the imports work smoothly
#   If you're working in a REAL TESP install you don't have to do this.
# os.environ['TESPDIR'] = '/Users/hard312/src/TSP/tesp'

from entity import assign_defaults
from entity import assign_item_defaults
from entity import Entity
from model import GLModel
from modifier import GLMModifier

from store import entities_path
from store import feeders_path



# Setting up logging
logger = logging.getLogger(__name__)

pp = pprint.PrettyPrinter(indent=4)

# Adding custom logging level "DATA" to use for putting
#  all the simulation data on. "DATA" is between "DEBUG"
#  and "NOTSET" in terms of priority.
DATA_LEVEL_NUM = 5
logging.addLevelName(DATA_LEVEL_NUM, "DATA")
def data(self, message, *args, **kws):
    if self.isEnabledFor(DATA_LEVEL_NUM):
        self._log(DATA_LEVEL_NUM, message, args, **kws)
logging.DATA = DATA_LEVEL_NUM
logging.Logger.data = data

# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4, )


def _open_file(file_path, type='r'):
    """Utilty function to open file with reasonable error handling.

    Args:
        file_path (str) - Path to the file to be opened

        type (str) - Type of the open method. Default is read ('r')


    Returns:
        fh (file object) - File handle for the open file
    """
    try:
        fh = open(file_path, type)
    except IOError:
       logger.error('Unable to open {}'.format(file_path))
    else:
        return fh




def _auto_run(args):
    glmMod = GLMModifier()
    feeder_path = os.path.join(feeders_path, "R1-12.47-1.glm")
    glmMod.model.read(feeder_path)

    #tp_meter_objs = glmMod.get_objects('triplex_meter')
    #tp_meter_names = list(tp_meter_objs.instance.keys())
    tp_meter_names = glmMod.get_object_names('triplex_meter')


    num_houses_to_add = 11

    for house_num in range(num_houses_to_add):
        # Adding billing meter to existing triplex meters in an arbitrary manner
        # This meter captures all energy usage for this customer
        billing_meter_name = f'{tp_meter_names[house_num]}_billing'

        # The API adds the name in call as the GLD object name. Don't need to specify it as a parameter.
        meter_params = {
            'parent': tp_meter_names[house_num]
        }

        # Only adding print out for the first time through the loop so I don't flood the terminal.
        if house_num == 0:
            print('Demonstrating addition of an object (triplex_meter in this case) to GridLAB-D model.')
            #num_tp_meters = len(list(tp_meter_objs.instance.keys()))
            num_tp_meters = len(glmMod.get_object_names('triplex_meter'))
            print(f'\tNumber of triplex meters: {num_tp_meters}')
            print(f'\tAdding triplex_meter {billing_meter_name} to model.')
        billing_meter = glmMod.add_object('triplex_meter', billing_meter_name, meter_params)
        if house_num == 0:
            #num_tp_meters = len(list(tp_meter_objs.instance.keys()))
            num_tp_meters = len(glmMod.get_object_names('triplex_meter'))
            print(f'\tNumber of triplex meters: {num_tp_meters}')

        # Add a meter just to capture the house energy consumption
        house_meter_name = f'{billing_meter_name}_house'
        meter_params = {
            'parent': billing_meter_name
        }
        house_meter = glmMod.add_object('triplex_meter', house_meter_name, meter_params)

        # Add house object as a child of the house meter
        house_name = f'house_{house_num}'

        # Saving this house name for use later on when we're deleting stuff.
        if house_num == 0:
            house_to_delete = house_name

        # Ideally that these parameters for the house objects are not hard-coded like this. Good alternatives:
        #   - Make an external JSON that defines each house and reads them in
        #   - Use algorithms and data like RECS to define random values for each house. This is what feeder_generator
        #       has historically done in the past.

        # Defining these parameters in a silly way just so each one is unique.
        house_params = {
            'parent': billing_meter_name,
            'Rroof': 33.69 + house_num,
            'Rwall': 17.71 + house_num,
            'Rfloor': 17.02 + house_num,
            'Rwindows': 1.8 + house_num,
            'airchange_per_hour': 0.8 + house_num,
            'cooling_system_type': 'ELECTRIC',
            'heating_system_type': 'HEAT_PUMP',
            'cooling_COP': 4.5 + house_num
        }
        house_obj = glmMod.add_object('house', house_name, house_params)
        # Can also modify the object parameters like this after the object has been created.
        if house_num == 0:
            print('\nDemonstrating editing of object properties after adding them to the GridLAB-D model.')
            if 'floor_area' in house_obj.keys():
                print(f'\t"Redefining floor_area" in {house_name}.')
                house_obj['floor_area'] = 2469
            else:
                print(f'\t"floor_area" not defined for house {house_name}, adding it now.')
                house_obj['floor_area'] = 2469
            print(f'\t"floor_area" now defined in model with value {house_obj["floor_area"]}.')

            # You can get object parameters after the object has been created
            if house_num == 0:
                print('\nDemonstrating getting object parameters after they have been added to the GridLAB-D model.')
                cooling_COP = house_obj['cooling_COP']
                print(f'\tCooling COP for house {house_name} is {cooling_COP}.')

        # Add specific loads to the house object as ZIP model
        load_name = f'light_load_{house_num}'
        # Again, hard-coding this in the file is not a good idea. Do as I say, not as I do.
        ZIP_params = {
            "parent": house_name,
            "schedule_skew": -685,
            "base_power":  1.8752,
            "power_fraction": 0.600000,
            "impedance_fraction": 0.400000,
            "current_fraction": 0.000000,
            "power_pf": 0.780,
            "current_pf": 0.420,
            "impedance_pf": 0.880,
            "heat_fraction": 0.91
        }
        load_obj = glmMod.add_object('ZIPload', load_name, ZIP_params)

        # Add separate solar meter to track the solar power generation specifically
        solar_meter_name = f'{billing_meter_name}_solar'
        meter_params = {
            'parent': billing_meter_name
        }
        solar_meter = glmMod.add_object('triplex_meter', solar_meter_name, meter_params)
        solar_name = f'solar_{house_num}'
        # solar_params = {
        #
        # }

        dummy = 0

    # You can delete specific parameter definitions (effectively making them the default value defined in GridLAB-D)
    #   as well as deleting entire object instances.
    print('\nDemonstrating the deletion of a parameter from a GridLAB-D object in the model.')
    house_to_edit = glmMod.get_object_name('house', house_name)  # GLD object type, object name
    if 'Rroof' in house_to_edit.keys():
        print(f'\t"Rroof" for house {house_name} is {house_to_edit["Rroof"]}.')
    else:
        print(f'\t"Rroof" for house {house_name} is undefined.')
    print(f'\tDeleting paramter Rroof from house {house_name}')
    glmMod.del_object_attr('house', house_name, 'Rroof')
    if 'Rroof' in house_to_edit.keys():
        print(f'\tCurrent "Rroof" is {house_to_edit["Rroof"]}')
    else:
        print(f'\t"Rroof" for house {house_name} is undefined.')

    # You can also just remove an entire object instance from the model (if you know the GLD object type and its name)
    print('Demonstrating the deletion of an entire object from GridLAB-D model.')
    # house_objs = tp_meter_objs = glmMod.get_object('house')
    # num_houses = len(list(house_objs.instance.keys()))
    num_houses = len(glmMod.get_object_names('house'))
    print(f'\tNumber of houses: {num_houses}')
    print(f'\tDeleting {house_to_delete} from model.')
    glmMod.del_object('house', house_to_delete)
    num_houses = len(glmMod.get_object_names('house'))
    print(f'\tNumber of houses: {num_houses}')


    # Increase all the secondary/distribution transformer ratings by 15%
    print('\nDemonstrating modification of a GridLAB-D parameter for all objects of a certain type.')
    print("In this case, we're upgrading the rating of the secondary/distribution transformers by 15%.")
    transformer_objs = glmMod.get_object('transformer')
    #transformer_names = list(glmMod.get_objects('transformer').instance.keys())
    transformer_names = glmMod.get_object_names('transformer')
    transformer_config_objs = glmMod.get_object('transformer_configuration')


    print("\tFinding all the split-phase transformers as these are the ones we're targeting for upgrade.")
    print("\t(In GridLAB-D, the sizing information is stored in the transformer_configuration object.)")
    transformer_configs_to_upgrade = []
    for transformer in transformer_names:
        phases = transformer_objs.instance[transformer]['phases']
        if phases.lower() in ['as', 'bs', 'cs']:
            # This is a secondary/distribution transformer
            if transformer_objs.instance[transformer]['configuration'] not in transformer_configs_to_upgrade:
                transformer_configs_to_upgrade.append(transformer_objs.instance[transformer]['configuration'])
    print(f'\tFound {len(transformer_configs_to_upgrade)} configurations that will be upgraded.')

    # for config in transformer_configs_to_upgrade:
    #     old_rating = float(transformer_config_objs.instance[config]['power_rating'])
    #     transformer_config_objs.instance[config]['power_rating'] = 1.15 * old_rating
    #     upgraded_rating = str(round(transformer_config_objs.instance[config]["power_rating"],3))
    #     print(f'\tUpgraded configuration {config} from {old_rating} to {upgraded_rating}')

    # Getting the networkx topology data as a networkx graph
    graph = glmMod.model.network
    gld_node_objs = glmMod.get_object('node')
    #gld_node_names = list(gld_node_objs.instance.keys())
    gld_node_names = glmMod.get_object_names('node')

    # Looking for swing bus which is, by convention, the head of the feeder.
    print(f'\nDemonstrating the use of networkx to find the feeder head and the closest fuse')
    swing_bus = ''
    for gld_node_name in gld_node_names:
        if 'bustype' in gld_node_objs.instance[gld_node_name].keys(): # Not every bus has the "bustype" parameter
            if gld_node_objs.instance[gld_node_name]['bustype'].lower() == 'swing':
                swing_bus = gld_node_name
    print(f'\tFound feeder head (swing bus) as node {swing_bus}')

    # Find first fuse downstream of the feeder head. I'm guessing it is close-by so doing a breadth-first search
    for edge in nx.bfs_edges(graph, swing_bus):
        data = graph.get_edge_data(edge[0], edge[1])
        if data['eclass'] == 'fuse':
            feeder_head_fuse = data['ename']
            break
    print(f'\tUsing networkx traversal algorithms, found the closest fuse as {feeder_head_fuse}.')

    # For demonstration purposes, increasing the rating on the fuse by 10%
    #   (If you look at a visualization of the graph you'll see that this fuse isn't really the feeder head fuse.
    #       And that's what you get for making assumptions.
    #       https://emac.berkeley.edu/gridlabd/taxonomy_graphs/R1-12.47-1.pdf )
    print(f'\tIncreasing fuse size by an arbitrary 10%')
    fuse_obj = glmMod.get_object_name('fuse', feeder_head_fuse)
    print(f'\t\tOld fuse current limit: {fuse_obj["current_limit"]}A')
    fuse_obj['current_limit'] = float(fuse_obj['current_limit']) * 1.1
    print(f'\t\tNew fuse current limit: {fuse_obj["current_limit"]}A')
    dummy = 0

    # Unused code that works but doesn't show off the things I wanted to show off.
    # for gld_node in gld_node_names:
    #     neighbors = graph.neighbors(gld_node)
    #     for neighbor in neighbors:
    #         print(neighbor)
    #     print("\n")
    # Look for largest transformer configuration in the model under the assumption that its for the substation transformer
    # (Turns out, this is a bad assumption.)
    # max_transformer_power = 0
    # max_transformer_name = ''
    # for transformer_config_name in transformer_config_names:
    #     transformer_power_rating = float(transformer_config_objs.instance[transformer_config_name]['power_rating'])
    #     if transformer_power_rating > max_transformer_power:
    #         max_transformer_power = transformer_power_rating
    #         max_transformer_name = transformer_config_name
    # dummy = 0
    # for node, nodedata in graph.nodes.items():
    #     dummy = 0
    #     print(node)
    #     print(pp.pformat(nodedata))
    #     dummy = 0


    glmMod.write_model("trevor_test.glm")


if __name__ == '__main__':
    # TDH: This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in trouble-shooting.
    fileHandle = logging.FileHandler("feeder_generator.log", mode='w')
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.DEBUG,
                        handlers=[fileHandle, streamHandle])

    parser = argparse.ArgumentParser(description='GridLAB-D Feeder Generator')
    # TDH: Have to do a little bit of work to generate a good default
    # path for the auto_run folder (where the development test data is
    # held.
    script_path = os.path.dirname(os.path.realpath(__file__))
    auto_run_dir = os.path.join(script_path, 'auto_run')
    parser.add_argument('-f',
                        '--feeder_path',
                        nargs='?',
                        default='../../data/feeders')
    args = parser.parse_args()
    _auto_run(args)