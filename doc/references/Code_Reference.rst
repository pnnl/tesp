..
    _ Copyright (c) 2021-2023 Battelle Memorial Institute
    _ file: Code_References.rst

.. _code-reference-label:

Code Reference
==============

TSO Case Data
-------------

The TSO schema was based on the MATPOWER formats for the network and generator cost data, supplemented with TESP data.
Code in *tso_PYPOWER.py and tso_psst.py* reads this data from a JSON file.

.. jsonschema:: tso_schema.json

src Directory Structure
-----------------------

This list shows **directories** and *Python files* under the **tesp/src** repository. On GitHub, each README contains a list of other files.

- **archive**

  - **pypower**; legacy files to patch PYPOWER; we have been able to incorporate these patches into the main PYPOWER distribution.

- **comms_metrics**; a Power Distribution System Model Analysis tool not yet public though pypi. Not only can it perform metric calculations, it also has the ability to plot the models as a network and parse different file formats as pre-processing for the data analysis.
- **energyplus**; C++ code to build a simple interface agent for EnergyPlus; this is part of the TESP distribution and used in the te30, sgip1 and energyplus examples.
- **gridlabd**; legacy files for the house populations and feeder growth model; these features are mostly subsumed into tesp_support
- **jupyter**; a prototype Jupyter notebook used for post-processing demonstrations and training
- **matpower**

  - **ubuntu**; legacy code that wraps MATPOWER for TESP, but only on Ubuntu. We now use PYPOWER. In 2017, the wrapping process was very difficult on Mac OS X, and unsuccessful on Windows using free compilers.

- **synComGraph**; graph algorithms to generate a synthetic communication network graph topology corresponding to a given feeder topology
- **tesp_support**; utilities for building and running using PYPOWER with or without FNCS/HELICS co-simulations

  - *setup.py*; contains the version number and dependencies for tesp_support package

  - **tesp_support**; Python code for agents, configuration and post-processing

    - **api**; code that configures new capabilities for TESP

        - *data.py*; the paths to data libraries
        - *entity.py*; utilities for assign json file to attribute in python script
        - *fncs.py*; the Python interface to FNCS, which is a C/C++ shared object library, or dynamic link library (Windows)
        - *helpers.py*; utility functions for use within tesp_support
        - *make_ems.py*; creates and merges the EMS for an EnergyPlus building model
        - *model.py*; GridLAB-D model I/O for TESP api
        - *modifier.py*; modify GridLAB-D model I/O for TESP api
        - *metric_api.py*; utility metric api functions for use in post-processing
        - *metric_collector.py*; utility metric collector functions for use within simulation or post process
        - *parse_helpers.py*; parse text for different types of numbers
        - *player.py*; configure and plays a files for a simulation
        - *process_eplus.py*; makes tabular and plotted summaries of EnergyPlus results
        - *process_gld.py*; makes tabular and plotted summaries of GridLAB-D results (substation power/losses, average and sample house temperatures, meter voltage min/max)
        - *process_houses.py*; plots the HVAC power and air temperature for all houses
        - *process_inv.py*; makes tabular and plotted summaries of results for NIST TE Challenge 2, including inverters, capacitor switching and tap changes
        - *process_pypower.py*; makes tabular and plotted summaries of PYPOWER results for the 9-bus model in te30 or sgip1
        - *process_voltages.py*; plots the minimum and maximum voltage for all houses
        - *test_runner.py*; auto test runner for TESP run* cases based on pre-existing shell script file.
        - *time_helpers.py*; utility time functions for use within tesp_support, including new agents
        - *tso_helpers.py*; helpers for PYPOWER, PSST, MOST solutions
        - *tso_PSST.py*; manages PSST solutions for the DSOT example, based on a 8-bus or 200-bus model. Note that the ERCOT cases use custom local versions of this code instead.
        - *tso_PYPOWER.py*; manages PYPOWER solutions for the te30 and sgip1 examples, based on a 9-bus textbook model. Note that the ERCOT cases use custom local versions of this code instead.

    - **original**; legacy code that configures most example/capabilities for TESP

        - *commercial_feeder_glm.py*; from a PNNL taxonomy feeder as the backbone, populates it with commercial building, solar PV, batteries and smart inverters
        - *copperplate_feeder_glm.py*; from a PNNL taxonomy feeder as the backbone, populates it with sudo copperplate
        - *curve*; accumulates a set of price, quantity bids for later aggregation for a curve
        - *glm_dict.py*; parses the GridLAB-D input (GLM) file and produces metafile data in JSON format, describing the houses, meters, DER, capacitors and regulators
        - *precool.py*; manages a set of house thermostats for NIST TE Challenge 2. There is no communication with a market. If the house experiences an overvoltage, the thermostat is turned down and locked for 4 hours, unless the house temperature violates comfort limits.
        - *prep_precool.py*; configures the agent metadata (JSON) and GridLAB-D HELICS subscriptions/publications for NIST TE Challenge 2 precooling
        - *prep_substation.py*; configures the agent metadata (JSON) and GridLAB-D HELICS subscriptions/publications for the double-auction, double-ramp simulations
        - *process_agents.py*; makes tabular and plotted summaries of agent results
        - *residential_feeder_glm.py*; from a PNNL taxonomy feeder as the backbone, populates it with houses, solar PV, batteries and smart inverters
        - *simple_auction.py*; implements the double-auction agent and the Olympic Peninsula cooling agent, as separate Python classes, called by auction.py
        - *tesp_case.py*; supervises the assembly of a TESP case with one feeder, one EnergyPlus building and one PYPOWER model. Reads the JSON file from tesp_config.py
        - *tesp_config.py*; a GUI for creating the JSON file used to configure a TESP case
        - *tesp_monitor.py*; a GUI for launching a TESP simulation, monitoring its progress, and terminating it early if necessary

    - **weather**; code that configures weather capabilities for TESP

        - *PSM_download.py*; simple script to download PSM weather files and convert them to DAT files
        - *PSMv3toDAT.py*; this code reads in PSM v3 csv files to converts weather DAT format for common use by agents
        - *README.md*; this file
        - *TMY3toCSV.py*; converts TMY3 weather data to CSV format for common use by agents
        - *TMYtoEPW.py*; command-line script that converts a TMY2 file to the EnergyPlus EPW format
        - *weather_Agent.py*; publishes weather and forecasts based on a CSV file

    - **consensus**;  custom code that for running the consensus mechanism on microgrid n DSOT co simulation using TSO and DSO DER agents.
    - **dsot**; custom code that for running the DSOT co simulation using TSO and DSO DER agents. Used for a 2021 journal paper on TESP and the DSOT example.
    - **sgip1**; custom code that plotted curves from different cases on the same graph. Used for a 2018 journal paper on TESP and the SGIP1 example.
    - **matpower**; legacy code that configures and post-processes MATPOWER v5+ for TESP. We now use PYPOWER and PSST instead.
    - **valuation**; custom code that post-processed SGIP1 outputs for the 2018 journal paper. May serve as an example, or use Jupyter notebooks instead.

  - **test**; scripts that support testing the package; not automated

Links to Dependencies
---------------------

* Docker_
* EnergyPlus_
* GridLAB-D_
* Matplotlib_
* MATPOWER_
* NetworkX_
* NumPy_
* Pandas_
* pip_
* PYPOWER_
* Python_
* SciPy_
* TESP_

.. _Docker: https://www.docker.com
.. _EnergyPlus: https://energyplus.net
.. _GridLAB-D: http://gridlab-d.shoutwiki.com
.. _Matplotlib: https://www.matplotlib.org
.. _MATPOWER: https://www.matpower.org
.. _NetworkX: https://www.networkx.org
.. _NumPy: https://www.numpy.org
.. _Pandas: https://pandas.pydata.org
.. _pip: https://pip.pypa.io/en/stable
.. _PYPOWER: https://github.com/rwl/PYPOWER
.. _Python: https://www.python.org
.. _SciPy: https://www.scipy.org
.. _TESP: https://tesp.readthedocs.io/en/latest

.. include:: ./tesp_support.inc
