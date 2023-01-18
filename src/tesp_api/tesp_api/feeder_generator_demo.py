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

# Getting all the existing tesp_support stuff
#   Assumes were in the tesp_api folder
sys.path.append('../../tesp_support')

# Setting a few environment variables so the imports work smoothly
#   If you're working in a REAL TESP install you don't have to do this.
os.environ['TESPDIR'] = '/Users/hard312/src/TSP/tesp'

from entity import assign_defaults
from entity import assign_item_defaults
from entity import Entity
from model import GLModel
from modifier import GLMModifier

from data import entities_path
from data import feeders_path



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

    tp_meter_objs = glmMod.get_objects('triplex_meter')
    tp_meter_names = list(tp_meter_objs.instance.keys())

    num_houses_to_add = 11

    for house_num in range(num_houses_to_add):
        # Adding billing meter to existing triplex meters in an arbitrary manner
        # This meter captures all energy usage for this customer
        billing_meter_name = f'{tp_meter_names[house_num]}_billing'
        meter_params = {
            'name': billing_meter_name,
            'parent': tp_meter_names[house_num]
        }
        billing_meter = glmMod.add_object('triplex_meter', billing_meter_name, meter_params)

        # Add a meter just to capture the house energy consumption
        house_meter_name = f'{billing_meter_name}_house'
        meter_params = {
            'name': house_meter_name,
            'parent': billing_meter_name
        }
        house_meter = glmMod.add_object('triplex_meter', house_meter_name, meter_params)

        # Add house object as a child of the house meter
        house_name = f'house_{house_num}'
        # Ideally that these parameters for the house objects are not hard-coded like this. Good alternatives:
        #   - Make an external JSON that defines each house and reads them in
        #   - Use algorithms and data like RECS to define random values for each house. This is what feeder_generator
        #       has historically done in the past.
        house_params = {
            'name': house_name,
            'parent': billing_meter_name,
            'Rroof': 33.69 + house_num,
            'Rwall': 17.71 + house_num,
            'Rfloor': 17.02 + house_num,
            'Rwindow': 1.8 + house_num,
            'air_change_per_hour': 0.8 + house_num,
            'cooling_system_type': 'ELECTRIC',
            'heating_system_type': 'HEAT_PUMP',
            'cooling_COP': 4.5 + house_num
        }
        house_obj = glmMod.add_object('house', house_name, house_params)
        # Can also modify the object parameters like this after the object has been created.
        house_obj['floor_area'] = 2469
        # You can get at object parameters after the object has been created
        cooling_COP = house_obj['cooling_COP']
        print(f'Cooling COP for this house is {cooling_COP}.')

        # Add specific loads to the house object as ZIP model
        load_name = f'light_load_{house_num}'
        # Again, hard-coding this in the file is not a good idea. Do as I say, not as I do.
        ZIP_params = {
            "name": load_name,
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
            'name': house_meter_name,
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
    model_obj = glmMod.model.entities
    house_to_edit = glmMod.get_object_id('house', house_name)
    # if 'Rroof' in house_to_edit
    # glmMod.delete_obj_item(house_name, house_to_edit, 'Rroof')

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