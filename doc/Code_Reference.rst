.. _code-reference-label:

Code Reference
==============

TSO Case Data
-------------

The TSO schema was based on the MATPOWER formats for the network and generator cost data, supplemented with TESP data.
Code in *fncsTSO.py* reads this data from a JSON file.

.. jsonschema:: tso_schema.json

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

.. include:: ./tesp_support.inc

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

