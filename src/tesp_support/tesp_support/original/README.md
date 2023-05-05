# original Python files

Copyright (c) 2017-2022, Battelle Memorial Institute

This is the original code repository for Python-based components of TESP, 
including the transactive agents, case configuration and post processing.  
Currently, there are three kinds of transactive agent implemented here: 

1. double-auction spot market, typically runs every 5 to 15 minutes
2. an electric cooling controller based on the Olympic Peninsula double-ramp method
3. an electric pre-cooling controller used to mitigate overvoltages in the NIST TE Challenge Phase 2

To develop a new agent, you may choose to copy an example Python file from 
this directory into your own test directory, to serve as a starting point.  
When finished, you should integrate the agent into this tesp_support 
package, so it will be available to other TESP developers and users.  In 
this re-integration process, you also need to modify api.py so that other 
Python code can call your new agent, and test it that way before 
re-deploying tesp_support to PyPi.  Also review setup.py in the parent 
directory to make sure you've included any new dependencies, including 
version updates.  
  
A second method is to create your new file(s) in this directory, which 
integrates your new agent from the start.  There will be some startup 
effort in modifying api.py and writing the script/batch files to call your 
agent from within your working test directory.  It may pay off in the end, 
by reducing the effort and uncertainty of code integration at the end.  

Suggested sequence of test cases for development:

1. 30-house example at https://github.com/pnnl/tesp/tree/master/examples/te30. This includes one large building, one connection to a 9-bus/4-generator bulk system, and a stiff feeder source. The model size is suited to manual adjustments, and testing the interactions of agents at the level of a feeder or lateral. There are effectively no voltage dependencies or overloads, except possibly in the substation transformer. This case runs on a personal computer in a matter of minutes.
2. 8-bus ERCOT example at https://github.com/pnnl/tesp/tree/master/ercot/case8. This includes 8 EHV buses and 8 distribution feeders, approximately 14 bulk system units, and several thousand houses. Use this for testing your agent configuration from the GridLAB-D metadata, for large-scale interactions and stability, and for interactions with other types of agent in a less controllable environment. This case runs on a personal computer in a matter of hours.
3. 200-bus ERCOT example, when available. This will have about 600 feeders with several hundred thousand houses, and it will probably have to run on a HPC. Make sure the code works on the 30-house and 8-bus examples first.

### File Directory
TODO: fill out descriptions for file

- *__init__.py*; boilerplate for a Python package
- *case_merge.py*;
- *commercial_feeder_glm.py*; from a PNNL taxonomy feeder as the backbone, populates it with commercial building, solar PV, batteries and smart inverters
- *copperplate_feeder_glm.py*; from a PNNL taxonomy feeder as the backbone, populates it with sudo copperplate
- *curve*; accumulates a set of price, quantity bids for later aggregation for a curve
- *glm_dictionary.py*; parses the GridLAB-D input (GLM) file and produces metafile data in JSON format, describing the houses, meters, DER, capacitors and regulators
- *hvac_agent.py*;
- *parse_msout.py*;
- *precool.py*; manages a set of house thermostats for NIST TE Challenge 2. There is no communication with a market. If the house experiences an overvoltage, the thermostat is turned down and locked for 4 hours, unless the house temperature violates comfort limits.
- *prep_eplus.py*;
- *prep_precool.py*; configures the agent metadata (JSON) and GridLAB-D FNCS subscriptions/publications for NIST TE Challenge 2 precooling
- *prep_substation.py*; configures the agent metadata (JSON) and GridLAB-D FNCS subscriptions/publications for the double-auction, double-ramp simulations
- *process_agents.py*; makes tabular and plotted summaries of agent results
- *README.md*; this file
- *residential_feeder_glm.py*; from a PNNL taxonomy feeder as the backbone, populates it with houses, solar PV, batteries and smart inverters
- *simple_auction.py*; implements the double-auction agent and the Olympic Peninsula cooling agent, as separate Python classes, called by auction.py
- *substation.py*;
- *tesp_case.py*; supervises the assembly of a TESP case with one feeder, one EnergyPlus building and one PYPOWER model. Reads the JSON file from tesp_config.py
- *tesp_config.py*; a GUI for creating the JSON file used to configure a TESP case
- *tesp_monitor.py*; a GUI for launching a TESP simulation, monitoring its progress, and terminating it early if necessary
- *tesp_monitor_ercot.py*; a GUI for launching a ERCOT simulation, monitoring its progress, and terminating it early if necessary
