# tesp_support Python files

Copyright (c) 2017-2024 Battelle Memorial Institute

See LICENSE file at https://github.com/pnnl/tesp

This is the main code repository for Python-based components of TESP, 
including the transactive agents, case configuration and post-processing.  
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

- *__init__.py*; boilerplate for a Python package
- *README.md*; this file

### Subdirectories

- **api**; code that configures new capabilities for TESP
- **consensus**; custom code that for running the consensus mechanism on microgrid n DSOT co simulation using TSO and DSO DER agents.
- **dsot**; custom code that for running the DSOT co simulation using TSO and DSO DER agents. Used for a 2021 journal paper on TESP and the DSOT example.
- **matpower**; legacy code that configures and post-processes MATPOWER v5+ for TESP. We now use PYPOWER and AMES instead.
- **original**; legacy code that configures and creates most example/capabilities for TESP 
- **sgip1**; custom code that plotted curves from different cases on the same graph. Used for a 2018 journal paper on TESP and the SGIP1 example.
- **valuation**; custom code that post-processed SGIP1 outputs for the 2018 journal paper. May serve as an example, or use Jupyter notebooks instead.
- **weather**; code that configures weather capabilities for TESP
