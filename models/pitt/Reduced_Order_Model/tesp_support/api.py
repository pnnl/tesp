# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: api.py
"""Functions intended for public access.

Example:
    To start PYPOWER for connection to FNCS::

        import tesp_support.api as tesp
        tesp.pypower_loop('te30_pp.json','TE_Challenge')

Public Functions:
    :substation_loop: Supervises FNCS messages and time steps for a GridLAB-D substation with one double-auction market and many HVAC controllers.  
    :pypower_loop: Supervises the FNCS messages, time steps, optimal power flow and power flow for PYPOWER.  
    :precool_loop: Supervises FNCS messages and time steps for a GridLAB-D substation with many price-taking and pre-cooling HVAC controllers.  
    :prep_substation: Writes agent metadata and FNCS subscriptions used in substation_loop.  
    :prep_precool: Writes agent metadata and FNCS subscriptions used in precool_loop.  
		:glm_dict: Writes the JSON metadata from a GridLAB-D file.
    :populate_feeder: Replaces the ZIP loads with houses in a GridLAB-D file.
    :make_tesp_case: Makes a subdirectory with all files needed to run a TESP simulation, as directed by a JSON file.
    :make_monte_carlo_cases: Makes a subdirectory with all files needed to run a Monte Carlo TESP simulation, as directed by a JSON file.
    :convert_tmy2_to_epw: Command line utility that converts TMY2 weather files to the EPW format for EnergyPlus.

"""

from __future__ import absolute_import

from .substation import substation_loop
from .feederGenerator import populate_feeder
from .fncsPYPOWER import pypower_loop 
from .glm_dict import glm_dict
from .precool import precool_loop
from .prep_precool import prep_precool
from .prep_substation import prep_substation
from .tesp_case import make_tesp_case
from .tesp_case import make_monte_carlo_cases
from .TMY2EPW import convert_tmy2_to_epw

from .fncsPYPOWER import load_json_case
from .fncsPYPOWER import summarize_opf

#from .process_agents import process_agents
#from .process_eplus import process_eplus
#from .process_gld import process_gld
#from .process_houses import process_houses
#from .process_inv import process_inv
#from .process_pypower import process_pypower
#from .process_voltages import process_voltages

#from .matpower.matpower_dict import matpower_dict
#from .matpower.process_matpower import process_matpower

#from .sgip1.compare_auction import compare_auction
#from .sgip1.compare_csv import compare_csv
#from .sgip1.compare_hvac import compare_hvac
#from .sgip1.compare_prices import compare_prices
#from .sgip1.compare_pypower import compare_pypower

#from .valuation.TransmissionMetricsProcessor import TransmissionMetricsProcessor


