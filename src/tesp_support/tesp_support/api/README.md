# api Python files

Copyright (c) 2017-2022, Battelle Memorial Institute

This is the api code repository for Python-based components of TESP, 
including the transactive agents, case configuration and post-processing.  

### File Directory
TODO: fill out descriptions for file

- *__init__.py*; boilerplate for a Python package
- *data.py*; the paths to data libraries
- *entity.py*; utilities for assign json file to attribute in python script
- *gridpiq.py*;
- *fncs.py*; the Python interface to FNCS, which is a C/C++ shared object library, or dynamic link library (Windows)
- *helpers.py*; utility functions for use within tesp_support
- *make_ems.py*;
- *metric_api.py*; utility metric api functions for use in post processing
- *metric_base_api.py*; utility metric base api functions for use in metric_api
- *metric_collector.py*; utility metric collector functions for use within simulation or post process
- *model.py*; GridLAB-D model I/O for TESP api
- *modifier.py*; modify GridLAB-D model I/O for TESP api
- *parse_helpers.py*; parse text for different types of numbers
- *player.py*; configure and plays a files for a simulation
- *player_f.py*; configure and plays a files for a simulation for FNCS
- *process_eplus.py*; makes tabular and plotted summaries of EnergyPlus results
- *process_gld.py*; makes tabular and plotted summaries of GridLAB-D results (substation power/losses, average and sample house temperatures, meter voltage min/max)
- *process_houses.py*; plots the HVAC power and air temperature for all houses
- *process_inv.py*; makes tabular and plotted summaries of results for NIST TE Challenge 2, including inverters, capacitor switching and tap changes
- *process_pypower.py*; makes tabular and plotted summaries of PYPOWER results for the 9-bus model in te30 or sgip1
- *process_voltages.py*; plots the minimum and maximum voltage for all houses
- *README.md*; this file
- *schedule_client.py*;
- *schedule_server.py*;
- *store.py*;
- *test_runner.py*; auto test runner for TESP run* cases based on pre-existing shell script file.
- *time_helpers.py*; utility time functions for use within tesp_support, including new agents
- *tso_helpers.py*; helpers for PYPOWER, PSST, MOST solutions
- *tso_PSST.py*; manages PSST solutions for the DSOT example, based on a 8-bus or 200-bus model. Note that the ERCOT cases use custom local versions of this code instead.
- *tso_PSST_f.py*; manages PSST solutions for the DSOT example, based on a 8-bus or 200-bus model for FNCS. Note that the ERCOT cases use custom local versions of this code instead.
- *tso_PYPOWER.py*; manages PYPOWER solutions for the te30 and sgip1 examples, based on a 9-bus textbook model. Note that the ERCOT cases use custom local versions of this code instead.
- *tso_PYPOWER_f.py*; manages PYPOWER solutions for the te30 and sgip1 examples, based on a 9-bus textbook model for FNCS. Note that the ERCOT cases use custom local versions of this code instead.
