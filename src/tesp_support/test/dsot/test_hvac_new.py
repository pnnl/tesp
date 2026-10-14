# Copyright (C) 2025 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: hvac_new_agent_rt_testbed.py
"""This is a testbed for the restructured DSO+T HVAC agent. It is intended to
help understand the bidding behavior of the DSO+T HVAC agent as well as
start to verify the new class structure to see if it improves usability.

@author: Trevor Hardy
"""

from dataclasses import dataclass
import logging
import pprint
import argparse
import sys
from tesp_support.dsot import hvac_new_agent
import json5
import datetime as dt

# Setting up logging
logger = logging.getLogger(__name__)

# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4)


def _open_file(file_path: str, type="r"):
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
        logger.error("Unable to open {}".format(file_path))
    else:
        return fh


def _auto_run(args):
    config_fh = _open_file(args.config_json_file)
    config_dict = json5.load(config_fh)
    # convert sim_time string to datetime object
    date_string = config_dict["agent"]["sim_time"]
    date_format = "%Y-%m-%d %H:%M:%S"
    sim_time_dt = dt.datetime.strptime(date_string, date_format)
    config_dict["agent"]["sim_time"] = sim_time_dt

    ha = hvac_new_agent.HVACDSOTAgent(name="test_hvac_agent", attributes=config_dict)
    if args.real_time == True:
        ha.calc_capacites_and_all_heat_flows()
        ha.asset.asset_model.structure_model.calc_structure_ETP_parameters()
        rt_bid = ha.rt_bidding_strategy.form_rt_bid()
        dummy = 0


def test_hvac_new():
    class args:
        config_json_file = "hvac_agent_testbed_config.json5"
        real_time = False

    _auto_run(args)


if __name__ == "__main__":
    # This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in trouble-shooting.
    fileHandle = logging.FileHandler("hvac_agent_testbed.log", "w")
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.DEBUG, handlers=[fileHandle, streamHandle])
    parser = argparse.ArgumentParser(description="Runs HVAC DSOT agent in testbed")
    parser.add_argument(
        "-c",
        "--config_json_file",
        help="configuration JSON for the HVAC agnet",
        nargs="?",
        default="hvac_agent_testbed_config.json5",
    )
    parser.add_argument(
        "-r",
        "--real_time",
        help="flag to form real-time bid)",
        action=argparse.BooleanOptionalAction,
    )
    args = parser.parse_args()
    print(args)
    _auto_run(args)
