# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: api.py
"""Functions intended for public access.

Example:
    To start PYPOWER for connection to FNCS::

        import tesp_support.tesp_api as tesp
        tesp.tso_pypower_loop_f('te30_pp.json','TE_Challenge')

    To start PYPOWER for connection to HELICS::

        import tesp_support.tesp_api as tesp
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

# metrics processing and plotting

# from DSOT


# from .matpower.matpower_dict import matpower_dict
# from .matpower.process_matpower import process_matpower

# from .sgip1.compare_auction import compare_auction
# from .sgip1.compare_csv import compare_csv
# from .sgip1.compare_hvac import compare_hvac
# from .sgip1.compare_prices import compare_prices
# from .sgip1.compare_pypower import compare_pypower

# from .valuation.TransmissionMetricsProcessor import TransmissionMetricsProcessor
