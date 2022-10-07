# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: api.py
"""Functions intended for public access.

Example:
    To start PYPOWER for connection to FNCS::

        import tesp_support.api as tesp
        tesp.tso_pypower_loop_f('te30_pp.json','TE_Challenge')

    To start PYPOWER for connection to HELICS::

        import tesp_support.api as tesp
        tesp.tso_pypower_loop('te30_pp.json','TE_Challenge', helicsConfig='tso.json')

Public Functions:
    :convert_tmy2_to_epw: Command line utility that converts TMY2 weather files to the EPW format for EnergyPlus.
    :glm_dict: Writes the JSON metadata from a GridLAB-D file.
    :make_ems: Creates the energy management system (EMS) for FNCS/HELICS to interface with EnergyPlus.
    :make_monte_carlo_cases: Makes a subdirectory with all files needed to run a Monte Carlo TESP simulation, as directed by a JSON file.
    :make_tesp_case: Makes a subdirectory with all files needed to run a TESP simulation, as directed by a JSON file.
    :populate_feeder: Replaces the ZIP loads with houses in a GridLAB-D file.
    :precool_loop: Supervises FNCS messages and time steps for a GridLAB-D substation with many price-taking and pre-cooling HVAC controllers.  
    :prep_precool: Writes agent metadata and FNCS subscriptions used in precool_loop.  
    :prep_substation: Writes agent metadata and FNCS subscriptions used in substation_loop.  
    :pypower_loop: Supervises the FNCS messages, time steps, optimal power flow and power flow for PYPOWER.  
    :startWeatherAgent: Publishes FNCS messages and forecasts from a weather CSV file.
    :substation_loop: Supervises FNCS messages and time steps for a GridLAB-D substation with one double-auction market and many HVAC controllers.  
    :summarize_opf: Print the OPF solution from PYPOWER (debugging).  
    :weathercsv: Converts TMY3 weather data to CSV format.
    :write_node_houses: Write a transformer, service drop, meters and houses connected to a node, replacing load.
    :write_node_house_configs: write the transformer, service drop and inverter configuration attributes for houses at a node.
"""

from __future__ import absolute_import

from .helpers_dsot import enable_logging
from .tso_helpers import load_json_case
from .tso_helpers import summarize_opf

from .player import load_player_loop
from .player_f import load_player_loop_f
from .feederGenerator import populate_feeder
from .feederGenerator import write_node_houses
from .feederGenerator import write_node_house_configs
from .tso_PYPOWER import tso_pypower_loop
from .tso_PYPOWER_f import tso_pypower_loop_f
from .tso_psst import tso_psst_loop
from .tso_psst_f import tso_psst_loop_f
from .glm_dict import glm_dict
from .precool import precool_loop
from .prep_precool import prep_precool
from .prep_substation import prep_substation
from .tesp_case import make_tesp_case
from .tesp_case import make_monte_carlo_cases
from .tesp_case import add_tesp_feeder
from .TMYtoEPW import convert_tmy2_to_epw
from .TMY3toCSV import weathercsv 
from .substation import substation_loop
from .substation_dsot import dso_loop
from .substation_dsot_f import dso_loop_f
from .weatherAgent import startWeatherAgent

from .case_merge import merge_glm
from .case_merge import merge_glm_dict
from .case_merge import merge_agent_dict
from .case_merge import merge_substation_yaml
from .case_merge import merge_fncs_config
from .case_merge import merge_gld_msg
from .case_merge import merge_substation_msg

from .make_ems import make_ems
from .make_ems import merge_idf

from .tesp_runner import init_tests
from .tesp_runner import block_test
from .tesp_runner import start_test
from .tesp_runner import run_test
from .tesp_runner import report_tests

from .tesp_config import show_tesp_config
from .tesp_case import make_tesp_case
from .tesp_monitor import show_tesp_monitor

from .prep_eplus import make_gld_eplus_case
from .parse_msout import read_most_solution

# metrics processing and plotting
from .process_agents import process_agents
from .process_agents import read_agent_metrics
from .process_agents import plot_agents
from .process_eplus import process_eplus
from .process_eplus import read_eplus_metrics
from .process_eplus import plot_eplus
from .process_gld import process_gld
from .process_gld import read_gld_metrics
from .process_gld import plot_gld
from .process_houses import process_houses
from .process_houses import read_houses_metrics
from .process_houses import plot_houses
from .process_inv import process_inv
from .process_inv import read_inv_metrics
from .process_inv import plot_inv
from .process_pypower import process_pypower
from .process_pypower import read_pypower_metrics
from .process_pypower import plot_pypower
from .process_voltages import process_voltages
from .process_voltages import read_voltages_metrics
from .process_voltages import plot_voltages

# from DSOT
from .hvac_dsot import HVACDSOT
from .water_heater_dsot import WaterHeaterDSOT
from .ev_dsot import EVDSOT
from .pv_dsot import PVDSOT
from .battery_dsot import BatteryDSOT
from .dso_market_dsot import DSOMarketDSOT
from .retail_market_dsot import RetailMarketDSOT
from .forecasting_dsot import Forecasting
from .metrics_collector import MetricsStore, MetricsCollector
from .schedule_server import schedule_server


# from .matpower.matpower_dict import matpower_dict
# from .matpower.process_matpower import process_matpower

# from .sgip1.compare_auction import compare_auction
# from .sgip1.compare_csv import compare_csv
# from .sgip1.compare_hvac import compare_hvac
# from .sgip1.compare_prices import compare_prices
# from .sgip1.compare_pypower import compare_pypower

# from .valuation.TransmissionMetricsProcessor import TransmissionMetricsProcessor

