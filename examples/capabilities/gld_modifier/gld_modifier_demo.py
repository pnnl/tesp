#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019-2023 Battelle Memorial Institute
"""
Created on Tue Jan 17 14:05:08 2023

This script attempts to demonstrate the usage of the new TESP API to modify 
GridLAB-D models.


@author: hard312
"""

import argparse
import json
import logging
import os
import pprint
import sys

import networkx as nx

from tesp_support.api.data import feeders_path
from tesp_support.api.modify_GLM import GLMModifier

# Setting up logging
logger = logging.getLogger(__name__)
# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4)

# Adding custom logging level "DATA" to use for all the simulation data. 
# "DATA" is between "DEBUG" and "NOTSET" in terms of priority.
DATA_LEVEL_NUM = 5
logging.addLevelName(DATA_LEVEL_NUM, "DATA")


def data(self, message, *args, **kws):
    if self.isEnabledFor(DATA_LEVEL_NUM):
        self._log(DATA_LEVEL_NUM, message, args, **kws)


logging.DATA = DATA_LEVEL_NUM
logging.Logger.data = data


def _auto_run(plot:bool, args):
    feeder_path = os.path.join(feeders_path, args.feeder_file)
    glmMod = GLMModifier()
    glm, success = glmMod.read_model(feeder_path)
    if not success:
        print('{feeder_path}} not found or file not supported; exiting')

    if hasattr(args, 'coords_file'):
        coords_file_path = os.path.join(feeders_path, args.coords_file)
        with open(coords_file_path) as fp:
            pos_data = json.load(fp)

    # Check to see if residential module is in the model now. If not, add it in.
    # The residential module is needed to simulate houses in GridLAB-D.
    if len(glmMod.model.module_entities["residential"].instances) == 0:
        print('Adding residential module to glm')
        glmMod.add_module("residential", {})


    # Houses have to be associated with triplex_meters so we ask for a list of meters
    # Returns a dictionary where the meter names are the keys and values are the
    # GridLAB-D parameter values.
    tp_meter_names = list(glm.triplex_meter.keys())
    num_houses_to_add = 11
    # Create dictionaries (with GridLAB-D parameter values) for new houses to be added
    for house_num in range(num_houses_to_add):
        # Adding billing meter to existing triplex meters in an arbitrary manner
        # The meter being defined I call a "billing meter" and  captures all energy
        # usage for this customer
        print('Adding billing meters')
        new_name = tp_meter_names[house_num]
        billing_meter_name = f"{new_name}_billing"
        meter_params = {
            "parent": new_name,
            "phases": glm.triplex_meter[f"{new_name}"]["phases"],
            "nominal_voltage": glm.triplex_meter[f"{new_name}"]["nominal_voltage"],
        }
        # Only adding print out for the first time through the loop, so I don't
        # flood the terminal with messages.
        if house_num == 0:
            print("Demonstrating addition of an object (triplex_meter in this case) to GridLAB-D model.")
            num_tp_meters = len(glm.triplex_meter.keys())
            print(f"\tNumber of triplex meters before adding one: {num_tp_meters}")
            print(f"\tAdding triplex_meter {billing_meter_name} to model.")
        glmMod.add_object("triplex_meter", billing_meter_name, meter_params)

        # Adding a new position element for the newly created billing meter
        if hasattr(args, 'coords_file'):
            pos_data[billing_meter_name] = pos_data[new_name]

        if house_num == 0:
            num_tp_meters = len(glm.triplex_meter.keys())
            print(f"\tNumber of triplex meters after adding one: {num_tp_meters}")

        # Add a meter to capture just the house energy consumption
        house_meter_name = f"{new_name}_house"
        meter_params = {
            "parent": billing_meter_name,
            "phases": glm.triplex_meter[billing_meter_name]["phases"],
            "nominal_voltage": glm.triplex_meter[billing_meter_name]["nominal_voltage"],
        }
        # Returns a dictionary of the object we just added;
        # in this case I don't do anything with that dictionary.
        house_meter = glmMod.add_object("triplex_meter", house_meter_name, meter_params)

        # Adding a new position element for the newly created house_meter
        if hasattr(args, 'coords_file'):
            pos_data[house_meter_name] = pos_data[billing_meter_name]

        # Add house object as a child of the house meter
        house_name = f"house_{house_num}"

        # Saving this house name for use later on when we're deleting stuff.
        if house_num == 0:
            house_to_delete = house_name

        # Ideally, these parameters for the house objects are not hard-coded like this. 
        # Good alternatives:
        #   - Make an external JSON that defines each house and reads them in
        #   - Use algorithms and data like RECS to define random values for each house. 
        #       This is what feeder_generator has historically done in the past.
        #       TESP provides this functionality through TODO.

        # Defining these parameters in a silly way just so each one is unique.
        # Option 1: Define house params and add the house object
        house_params = {
            "parent": new_name,
            "Rroof": 33.69 + house_num,
            "Rwall": 17.71 + house_num,
            "Rfloor": 17.02 + house_num,
            "Rwindows": 1.8 + house_num,
            "airchange_per_hour": 0.8 + house_num,
            "cooling_system_type": "ELECTRIC",
            "heating_system_type": "HEAT_PUMP",
            "cooling_COP": 4.5 + house_num,
        }
        house_obj = glmMod.add_object("house", house_name, house_params)

        # Option 2: Add the house directly with house.add
        house_obj = glm.house.add(house_name, {
            "parent": new_name,
            "Rroof": 33.69 + house_num,
            "Rwall": 17.71 + house_num,
            "Rfloor": 17.02 + house_num,
            "Rwindows": 1.8 + house_num,
            "airchange_per_hour": 0.8 + house_num,
            "cooling_system_type": "ELECTRIC",
            "heating_system_type": "HEAT_PUMP",
            "cooling_COP": 4.5 + house_num,
        })

        # Adding a new position element for the newly created house
        if hasattr(args, 'coords_file'):
            pos_data[house_name] = pos_data[new_name]

        # Can also modify the object parameters like this after the object has been created.
        if house_num == 0:
            print("\nDemonstrating editing of object properties after adding them "
                  "to the GridLAB-D model.")
            if "floor_area" in house_obj.keys():
                print(f'\t"Redefining floor_area" in {house_name}.')
                house_obj["floor_area"] = 2469
            else:
                print(f'\t"floor_area" not defined for house {house_name}, '
                      'adding it now.')
                house_obj["floor_area"] = 2469
            print(f'\t"floor_area" now defined in model with value {house_obj["floor_area"]}.')

            # You can get object parameters after the object has been created
            if house_num == 0:
                print("\nDemonstrating getting object parameters after they "
                      "have been added to the GridLAB-D model.")
                cooling_COP = house_obj["cooling_COP"]
                print(f"\tCooling COP for house {house_name} is {cooling_COP}.")

        # Add specific loads to the house object as ZIP model
        load_name = f"light_load_{house_num}"
        # Again, hard-coding this in the file is not a good idea. Do as I say, 
        # not as I do.
        ZIP_params = {
            "parent": house_name,
            "schedule_skew": -685,
            "base_power": 1.8752,
            "power_fraction": 0.600000,
            "impedance_fraction": 0.400000,
            "current_fraction": 0.000000,
            "power_pf": 0.780,
            "current_pf": 0.420,
            "impedance_pf": 0.880,
            "heat_fraction": 0.91,
        }
        load_obj = glmMod.add_object("ZIPload", load_name, ZIP_params)

    # You can delete specific parameter definitions (effectively making them
    # the default value defined in GridLAB-D)
    print("\nDemonstrating the deletion of a parameter from a GridLAB-D object "
          "in the model.")
    house_to_edit = glm.house[house_name]
    if "Rroof" in house_to_edit.keys():
        print(f'\t"Rroof" for house {house_name} is {house_to_edit["Rroof"]}.')
    else:
        print(f'\t"Rroof" for house {house_name} is undefined.')
    print(f"\tDeleting paramter Rroof from house {house_name}")
    house_to_edit["Rroof"] = None
    if "Rroof" in house_to_edit.keys():
        print(f'\tCurrent "Rroof" is {house_to_edit["Rroof"]}')
    else:
        print(f'\t"Rroof" for house {house_name} is undefined.\n')

    # You can also just remove an entire object instance from the model (if you
    # know the GLD object type and its name) To prevent electrical islands, 
    # this method also deletes all downstream objects associated through a
    #  parent-child relationship.
    print("Demonstrating the deletion of an entire object from GridLAB-D model.")
    print("\tZIPload is child of house and will be automatically deleted as well.")
    num_houses = len(glm.house.keys())
    print(f"\tNumber of houses: {num_houses}")
    num_zips = len(glm.ZIPload.keys())
    print(f"\tNumber of ZIPloads: {num_zips}")
    print(f"\tDeleting {house_to_delete} from model.")
    glmMod.del_object("house", house_to_delete)
    num_houses = len(glm.house.keys())
    print(f"\tNumber of houses: {num_houses}")
    num_zips = len(glm.ZIPload.keys())
    print(f"\tNumber of ZIPloads: {num_zips}")

    # Increase all the secondary/distribution transformer ratings by 15%
    print("\nDemonstrating modification of a GridLAB-D parameter for all "
          "objects of a certain type.")
    print("In this case, we're upgrading the rating of the "
          "secondary/distribution transformers by 15%.")
    transformer_config_objs = glm.transformer_configuration

    print("\tFinding all the split-phase transformers as these are the ones "
          "we're targeting for upgrade.")
    print(
        "\t(In GridLAB-D, the sizing information is stored in the "
        "transformer_configuration object.)")
    transformer_configs_to_upgrade = {"as": [], "bs": [], "cs": []}
    for transformer_name, transformer in glm.transformer.items():
        phases = transformer["phases"]
        config = transformer["configuration"]
        if phases.lower() == "as":
            if config not in transformer_configs_to_upgrade["as"]:
                transformer_configs_to_upgrade["as"].append(config)
        elif phases.lower() == "bs":
            if config not in transformer_configs_to_upgrade["bs"]:
                transformer_configs_to_upgrade["bs"].append(config)
        elif phases.lower() == "cs":
            if config not in transformer_configs_to_upgrade["cs"]:
                transformer_configs_to_upgrade["cs"].append(config)
    print(f'\tFound {len(transformer_configs_to_upgrade["as"])}'
          ' configurations with phase "AS" that will be upgraded.')
    print(f'\tFound {len(transformer_configs_to_upgrade["bs"])} '
          ' configurations with phase "BS" that will be upgraded.')
    print(f'\tFound {len(transformer_configs_to_upgrade["cs"])}'
          ' configurations with phase "CS" that will be upgraded.')

    # Assumes the model has the "powerX_rating" in the transformer configuration
    # to be used as the basis to determine the existing rating. This will not
    # be true for every feeder.
    for phase in transformer_configs_to_upgrade.keys():
        if phase == "as":
            rating_param = "powerA_rating"
        elif phase == "bs":
            rating_param = "powerB_rating"
        elif phase == "cs":
            rating_param = "powerC_rating"
        for config in transformer_configs_to_upgrade[phase]:
            old_rating = float(glm.transformer_configuration[config][rating_param])
            new_rating = 1.15 * old_rating
            # Both the "power_rating" and "powerX_rating" are defined in the model,
            # for some reason.
            glm.transformer_configuration[config][rating_param] = new_rating
            glm.transformer_configuration[config]["power_rating"] = new_rating
            upgraded_rating = str(
                round(glm.transformer_configuration[config][rating_param], 3))
            print(f'\tUpgraded configuration {config} from {old_rating} '
                  f'to {upgraded_rating}')

    # The model topology is stored as a networks graph, allowing you to do fancy
    # manipulations of the model more easily.

    # Looking for swing bus which is, by convention, the head of the feeder. From
    # there we're going to find the closest fuse and upgrade its rating for
    # arbitrary reasons

    # Starting out just looking for the swing bus using the non-networkx APIs we've
    # been using up to this point.
    print(f"\nDemonstrating the use of networkx to find the feeder head and "
          "the closest fuse")
    swing_bus = ""
    for gld_node_name in glm.node.keys():
        # Not every bus has the "bustype" parameter
        if "bustype" in glm.node[gld_node_name].keys():
            if glm.node[gld_node_name]["bustype"].lower() == "swing":
                swing_bus = gld_node_name
    print(f"\tFound feeder head (swing bus) as node {swing_bus}")

    # Find first fuse downstream of the feeder head. I'm guessing it is close-by
    # so doing a breadth-first search using the networkx API and the topology 
    # graph of our GridLAB-D model.
    graph = glmMod.model.draw_network()
    for edge in nx.bfs_edges(graph, swing_bus):
        edge_data = graph.get_edge_data(edge[0], edge[1])
        if edge_data["eclass"] == "fuse":
            feeder_head_fuse = edge_data["ename"]
            break
    print(f"\tUsing networkx traversal algorithms, found the closest fuse as "
          f"{feeder_head_fuse}.")

    # For demonstration purposes, increasing the rating on the fuse by 10%
    # (If you look at a visualization of the graph you'll see that this fuse
    # isn't really the feeder head fuse.
    # And that's what you get for making assumptions.
    # https://emac.berkeley.edu/gridlabd/taxonomy_graphs/R1-12.47-1.pdf )
    if len(glm.fuse.keys()) > 0:
        print(f"\tIncreasing fuse size by an arbitrary 10%")
        fuse_obj = glm.fuse[feeder_head_fuse]
        print(f'\t\tOld fuse current limit: {fuse_obj["current_limit"]} A')
        fuse_obj["current_limit"] = float(fuse_obj["current_limit"]) * 1.1
        print(f'\t\tNew fuse current limit: {fuse_obj["current_limit"]} A')

    max_transformer_power = 0
    max_transformer_name = ""
    for transformer_config_name in glm.transformer_configuration.keys():
        transformer_power_rating = float(
            glm.transformer_configuration[transformer_config_name]["power_rating"]
        )
        if transformer_power_rating > max_transformer_power:
            max_transformer_power = transformer_power_rating
            max_transformer_name = transformer_config_name

    # for node, nodedata in graph.nodes.items():
    #     dummy = 0
    #     print(node)
    #     print(pp.pformat(nodedata))
    #     dummy = 0

    # Use networkx to plot graph of model for exploration
    if plot:
        print("\nPlotting image of model")
        glmMod.model.plot_model(pos_data)
    glmMod.write_model(args.output_file)


def demo(plot:bool):
    # This slightly complex mess allows lower importance messages to be sent to 
    # the log file and ERROR messages to additionally be sent to the console as
    # well. Thus, when bad things happen the user will get an error message in
    # both places which, hopefully, will aid in troubleshooting.
    fileHandle = logging.FileHandler("gld_modifier.log", mode="w")
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.DEBUG, handlers=[fileHandle, streamHandle])

    parser = argparse.ArgumentParser(description="Demo GridLAB-D modifier using a defined feeder")
    # script_path = os.path.dirname(os.path.realpath(__file__))
    parser.add_argument('-n',
                        '--feeder_file',
                        nargs='?',
                        default='R1-12.47-2.glm')

    parser.add_argument('-c',
                        '--coords_file',
                        nargs='?',
                        default='R1_12_47_2_pos.json')

    parser.add_argument('-o',
                        '--output_file',
                        nargs='?',
                        default='R1-12.47-2_out.glm')
    _args = parser.parse_args()
    _auto_run(plot, _args)


if __name__ == "__main__":
    demo(True)
