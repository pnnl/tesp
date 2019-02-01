.. _code-reference-label:

Code Reference
==============

This describes the source code base.

src Directory Structure
-----------------------

This list shows **directories** and *Python files* under the **tesp/src** repository. On GitHub, each README contains a list of other files.

- **archive**

  - **pypower**; legacy files to patch PYPOWER; we have been able to incorporate these patches into the main PYPOWER distribution.

- **energyplus**; C++ code to build a simple interface agent for EnergyPlus; this is part of the TESP distribution and used in the te30, sgip1 and energyplus examples.
- **gridlabd**; legacy files for the house populations and feeder growth model; these features are mostly subsumed into tesp_support
- **jupyter**; a prototype Jupyter notebook used for post-processing demonstrations and training
- **matpower**

  - **ubuntu**; legacy code that wraps MATPOWER for TESP, but only on Ubuntu. We now use PYPOWER. In 2017, the wrapping process was very difficult on Mac OS X, and unsuccessful on Windows using free compilers.

- **tesp_support**; runs PYPOWER without FNCS

  - *setup.py*; contains the version number and dependencies for tesp_support package
  - **tesp_support**; Python code for agents, configuration and post-processing.

    - *TMY2EPW.py*; command-line script that converts a TMY2 file to the EnergyPlus EPW format.
    - *__init__.py*; boilerplate for a Python package
    - *api.py*; collects Python import statements needed to use public functions from Python code outside of this directory.
    - *auction.py*; supervises one double-auction and multiple HVAC agents for a feeder; communicates via FNCS with GridLAB-D and PYPOWER/AMES
    - *feederGenerator.py*; from a PNNL taxonomy feeder as the backbone, populates it with houses, solar PV, batteries and smart inverters
    - *fncs.py*; the Python interface to FNCS, which is a C/C++ shared object library, or dynamic link library (Windows)
    - *fncsPYPOWER.py*; manages PYPOWER solutions for the te30 and sgip1 examples, based on a 9-bus textbook model. Note that the ERCOT cases use custom local versions of this code instead.
    - *glm_dict.py*; parses the GridLAB-D input (GLM) file and produces metafile data in JSON format, describing the houses, meters, DER, capacitors and regulators
    - *precool.py*; manages a set of house thermostats for NIST TE Challenge 2. There is no communication with a market. If the house experiences an overvoltage, the thermostat is turned down and locked for 4 hours, unless the house temperature violates comfort limits.
    - *prep_auction.py*; configures the agent metadata (JSON) and GridLAB-D FNCS subscriptions/publications for the double-auction, double-ramp simulations
    - *prep_precool.py*; configures the agent metadata (JSON) and GridLAB-D FNCS subscriptions/publications for NIST TE Challenge 2 precooling
    - *process_agents.py*; makes tabular and plotted summaries of agent results
    - *process_eplus.py*; makes tabular and plotted summaries of EnergyPlus results
    - *process_gld.py*; makes tabular and plotted summaries of GridLAB-D results (substation power/losses, average and sample house temperatures, meter voltage min/max)
    - *process_houses.py*; plots the HVAC power and air temperature for all houses
    - *process_inv.py*; makes tabular and plotted summaries of results for NIST TE Challenge 2, including inverters, capacitor switching and tap changes
    - *process_pypower.py*; makes tabular and plotted summaries of PYPOWER results for the 9-bus model in te30 or sgip1
    - *process_voltages.py*; plots the minimum and maximum voltage for all houses
    - *simple_auction.py*; implements the double-auction agent and the Olympic Peninsula cooling agent, as separate Python classes, called by auction.py
    - *tesp_case.py*; supervises the assembly of a TESP case with one feeder, one EnergyPlus building and one PYPOWER model. Reads the JSON file from tesp_config.py
    - *tesp_config.py*; a GUI for creating the JSON file used to configure a TESP case
    - *tesp_monitor.py*; a GUI for launching a TESP simulation, monitoring its progress, and terminating it early if necessary
    - *README.md*; this file
    - **matpower**; legacy code that configures and post-processes MATPOWER v5+ for TESP. We now use PYPOWER and AMES instead.
    - **sgip1**; custom code that plotted curves from different cases on the same graph. Used for a 2018 journal paper on TESP and the SGIP1 example.
    - **valuation**; custom code that post-processed SGIP1 outputs for the 2018 journal paper. May serve as an example, or use Jupyter notebooks instead.

  - **test**; scripts that support testing the package; not automated.

Links to Dependencies
---------------------

* Docker_
* EnergyPlus_
* GridLAB-D_
* Matplotlib_
* MATPOWER_
* NetworkX_
* NumPy_
* pip_
* PYPOWER_
* Python_
* SciPy_
* TESP_

tesp_support Package Design
---------------------------

|uml0|

Classes in the tesp_support package.

Development Work Flow for tesp_support
--------------------------------------

This is the main code repository for Python-based components of TESP, 
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

* From this directory, 'pip install -e .' points Python to this cloned repository for any calls to tesp_support functions
* See the https://github.com/pnnl/tesp/tree/master/src/tesp_support/tesp_support for a roadmap of existing Python source files, and some documentation.  Any changes or additions to the code need to be made in this directory.  
* Run tests from any other directory on this computer
* When ready, edit the tesp_support version number and dependencies in setup.py
* To deploy, 'python setup.py sdist upload' 
* Any user gets the changes with 'pip install tesp_support --upgrade'
* Use 'pip show tesp_support' to verify the version and location on your computer

.. include:: ./tesp_support.inc

.. |uml0| image:: ./media/tesp_support.png

.. _Docker: https://www.docker.com
.. _Python: http://www.python.org
.. _pip: https://pip.pypa.io
.. _NumPy: http://www.numpy.org
.. _SciPy: http://www.scipy.org
.. _Matplotlib: https://matplotlib.org
.. _NetworkX: http://networkx.github.io
.. _MATPOWER: http://www.pserc.cornell.edu/matpower/
.. _PYPOWER: https://github.com/rwl/PYPOWER
.. _GridLAB-D: http://gridlab-d.shoutwiki.com
.. _EnergyPlus: https://energyplus.net/
.. _TESP: http://tesp.readthedocs.io/en/latest/

