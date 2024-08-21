# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: create_helics_config.py
"""Reads in populated GridLAB-D model, finds the EV objects, and uses this
information to create HELICS configuration JSONs.

Co-simulation data exchange diagram:

                     ---  vehicle_location -- >
                     ----  battery_SOC ------ >
GridLAB-D EV models                              Charge manager 
                     <-- maximum_charge_rate ---

GridLAB-D/evcharger_det/battery_SOC
GridLAB-D/evcharger_det/vehicle_location
ChargeManager/EV/maximum_charge_rate

References:
    

Public Functions:


"""


import argparse
import logging
import pprint
import os
import sys
import networkx as nx
import json
import copy

from tesp_support.api.modify_GLM import GLMModifier
from tesp_support.api.data import feeders_path

# Setting up logging
logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4)

# Adding custom logging level "DATA" to use for putting
#  all the simulation data on. "DATA" is between "DEBUG"
#  and "NOTSET" in terms of priority.
DATA_LEVEL_NUM = 5
logging.addLevelName(DATA_LEVEL_NUM, "DATA")


def _open_file(file_path: str, type='r'):
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
     # ****** Make (most hard-coded) runner and write out to file **********
    federates = [
        {
            "directory": ".",
            "exec": "python -u UVM_EV_charge_manager.py",
            "host": "localhost",
            "name": "EV charger manager"
        },
        {
            "directory": ".",
            "exec": f"gridlabd {args.feeder_file}",
            "host": "localhost",
            "name": "gld"
        }
    ]
    runner = {
        "name": "UVM EV HELICS Demo",
        "broker": True,
        "federate": federates
    }
    runner_fh = _open_file(args.runner_config, 'w')
    try:
        json.dump(runner, runner_fh, indent=2)
        logger.debug(f"Wrote runner config file {args.runner_config}")
    except:
        raise ValueError(f"Unable to export runner dictionary to JSON file {args.runner_config}")



    # ********* Make HELICS config JSONs for the two federates ************
    gld_fed_name = "gld"
    ev_charge_fed_name = "ev_charge_manager"

    # Set up data object and read in file
    glmMod = GLMModifier()
    glm, success = glmMod.read_model(args.feeder_file)
    if not success:
        raise ValueError('Failed to parse GridLAB-D model file.')

    # Dictionaries for storing configuration
    gld_config = {
        "name": gld_fed_name,
        "log_level": "warning",
        "period": 300,
        "terminate_on_error": True,
        "uninterruptible": False,
        "publications": [],
        "subscriptions": []
    }
    charge_manager_config = {
        "name": ev_charge_fed_name,
        "log_level": "warning",
        "period": 300,
        "terminate_on_error": True,
        "uninterruptible": False,
        "publications": [],
        "subscriptions": []
    }

    pub_template = {
      "global": True,
      "key": None,
      "type": "double",
      "unit": None,
      "required": True
    }
    sub_template = {
      "global": True,
      "key": None,
      "type": "double",
    }
    gld_soc_pubs = []
    gld_location_pubs = []
    ev_charge_soc_subs = []
    ev_charge_location_subs = []

    # Get names of EV objects
    for ev_obj_name in list(glm.evcharger_det):
        # Add GridLAB-D SOC publication
        gld_pub_soc = copy.deepcopy(pub_template)
        gld_pub_soc["key"] = f"{gld_fed_name}/{ev_obj_name}/battery_SOC"
        gld_pub_soc["unit"] = "W"
        gld_soc_pubs.append(gld_pub_soc)

        # Add GridLAB-D location publication
        gld_pub_location = copy.deepcopy(pub_template)
        gld_pub_location["key"] = f"{gld_fed_name}/{ev_obj_name}/vehicle_location"
        gld_location_pubs.append(gld_pub_location)

        # Add GridLAB-D charging power subscription
        gld_sub_charging_power = copy.deepcopy(sub_template)
        gld_sub_charging_power["key"] = f"{ev_charge_fed_name}/{ev_obj_name}/maximum_charge_rate"
        gld_config["subscriptions"].append(gld_sub_charging_power)

        # Add EV charge manager SOC subscription
        ev_charge_sub_soc = copy.deepcopy(sub_template)
        ev_charge_sub_soc["key"] = f"{gld_fed_name}/{ev_obj_name}/battery_SOC"
        ev_charge_soc_subs.append(ev_charge_sub_soc)

        # Add EV charge manager location subscription
        ev_charge_sub_location = copy.deepcopy(sub_template)
        ev_charge_sub_location["key"] = f"{gld_fed_name}/{ev_obj_name}/vehicle_location"
        ev_charge_location_subs.append(ev_charge_sub_location)

        # Add EV charge manager charging power publication
        ev_charge_pub_charging_power = copy.deepcopy(pub_template)
        ev_charge_pub_charging_power["key"] = f"{ev_charge_fed_name}/{ev_obj_name}/maximum_charge_rate"
        charge_manager_config["publications"].append(ev_charge_pub_charging_power)

        logger.debug(f"Added pubs and subs for EV {ev_obj_name}")

    # Concatening pubs and subs list to put them in a convenient order
    # This makes writing the code in the ev_charge_manager slightly eaiser
    # as the index of the pubs and subs depends on the order they appear
    # in the HELICS config file.
    gld_config["publications"].append(gld_soc_pubs + gld_location_pubs)
    charge_manager_config["subscriptions"].append(ev_charge_soc_subs + ev_charge_location_subs)
    

    # Write out configuration JSONs
    gld_config_fh = _open_file(args.gld_helics_config, 'w')
    try:
        json.dump(gld_config, gld_config_fh, indent=2)
        logger.debug(f"Wrote GridLAB-D HELICS config file {args.gld_helics_config}")
    except:
        raise ValueError(f"Unable to export runner dictionary to JSON file {args.gld_helics_config}")
    
    ev_charge_config_fh = _open_file(args.charge_manager_helics_config, 'w')
    try:
        json.dump(charge_manager_config, ev_charge_config_fh, indent=2)
        logger.debug(f"Wrote EV charge manager HELICS config file {args.charge_manager_helics_config}")
    except:
        raise ValueError(f"Unable to export runner dictionary to JSON file {args.charge_manager_helics_config}")






if __name__ == "__main__":
        # This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in troubleshooting.
    fileHandle = logging.FileHandler("feeder_generator.log", mode="w")
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.DEBUG, handlers=[fileHandle, streamHandle])

    parser = argparse.ArgumentParser(description="GridLAB-D Feeder Generator")
    # script_path = os.path.dirname(os.path.realpath(__file__))
    parser.add_argument('-n',
                        '--feeder_file',
                        nargs='?',
                        default='South_D1_Alburgh_mod_tesp_v3_populated.glm')
    parser.add_argument('-og',
                        '--gld_helics_config',
                        nargs='?',
                        default='gld_config.json')
    parser.add_argument('-oc',
                        '--charge_manager_helics_config',
                        nargs='?',
                        default='charge_manager_congfig.json')
    parser.add_argument('-or',
                        '--runner_config',
                        nargs='?',
                        default='runner_config.json')
    _args = parser.parse_args()
    _auto_run(_args)