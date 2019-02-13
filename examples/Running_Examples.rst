.. _RunExamples:

Running Examples
----------------

These examples run very much the same on all three supported platforms.
TESP Uses TCP/IP port 5570 for communication. Simulations can start many processes, 
and take minutes or hours to complete. We recommend 16 GB of memory.

All examples use Python 3:

- On Windows: please verify that **python --version** reports a version of Python 3
- On Linux: invoke **python3** instead of just *python*
- On Mac OS X: invoke **python3** for non-graphical scripts or **pythonw** for Matplotlib scripts, instead of just *python*

On Linux and Mac OS X:

- you may have to increase the number of processes and open file handles allowed
- **lsof -i :5570** will show all processes connected to port 5570 
- use **ls -al** or **cat** on log files or csv filesto show progress of a case solution
- **./kill5570.sh** will terminate all processes connected to port 5570; if you have to do this, make sure **lsof -i :5570** shows nothing before attempting another case
- it is recommended that you append **&** to any python plot commands, so they run in the background.

The instructions are given for Linux and Mac OS X. If using Windows:

- you still run from the command prompt, either MSYS2 or Windows
- the batch files have different extensions, for example **./run.sh** becomes **run.bat** or just **run**
- the root directory for TESP and the commands to change directory are different. For example, **cd ~/tesp** becomes **cd c:\tesp**
- batch files **list5570** and **kill5570** have been provided to list and kill processes on port 5570
- on Windows 7, edit **kill5570.bat** files to uncomment line 2, and comment lines 4-10
- as with Linux and Mac OS X, if you must invoke **kill5570**, make sure **list5570** shows nothing before you attempt another simulation

The examples are contained in subdirectories:

- loadshed; a time-controlled disconnection of part of the IEEE 13-bus system
- energyplus; a school building simulation with price-responsive load
- pypower; a 9-bus transmission system and market simulation, with generator outage
- te30; a small system with 30 houses, 1 school, 9-bus bulk system, and no voltage issues
- sgip1; a practical feeder with 1594 houses, 1 school and 9-bus bulk system
- ieee8500; a larger feeder with high solar penetration, for NIST's TE Challenge

Many of the support files are also contained in subdirectories:

- players; real-time LMP and non-responsive load files for the te30 case
- schedules; appliance schedules for GridLAB-D
- weather; TMY3 files for GridLAB-D

loadshed - verify GridLAB-D and Python over FNCS 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Results should be identical to the Java version of this example.
Before running, the *clean* command will remove any existing
Java results.

::

 cd ~/tesp/examples/loadshed
 ./clean.sh
 ./run.sh
 python3 plot_loadshed.py loadshed

For more details, see `Loadshed Example Readme`_

loadshed - verify GridLAB-D and Java over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Results should be identical to the Python version of this example.
Before running, the *clean* command will remove any existing
Python results.

::

 cd ~/tesp/examples/loadshed
 ./clean.sh
 ./runjava.sh
 python3 plot_loadshed.py loadshed

For more details, see `Loadshed Example Readme`_

energyplus - verifies EnergyPlus over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/tesp/examples/energyplus
 ./run.sh
 python3 plots.py

For more details, see `EnergyPlus Example Readme`_

pypower - verifies PYPOWER over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/tesp/examples/pypower
 ./runpp.sh
 python3 plots.py

For more details, see `PYPOWER Example Readme`_

te30 - 30 houses, 1 school, 4 generators over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/tesp/examples/te30
 python3 prepare_case.py
 # without market
 # a simulation takes about 10 minutes, use "cat TE*.csv" to show progress 
 # on the console up to 172800 seconds
 ./run0.sh
 python3 plots.py TE_Challenge0
 # with market
 ./run.sh    # runs with the market
 python3 plots.py TE_Challenge

For more details, see `TE30 Example Readme`_

sgip1 - 1594 houses, 1 school, 4 generators over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Ubuntu, 16 GB of memory may be required.

::

 cd ~/tesp/examples/sgip1
 python3 prepare_cases.py
 # run and plot one of the six cases, with market but no DER
 # the simulation takes about 120 minutes, use "cat SGIP*.csv" to show progress up to 172800 seconds
 ./runSGIP1b.sh
 python3 plots.py SGIP1b

For more details, see `SGIP1 Example Readme`_

ieee8500
~~~~~~~~

To run and plot the GridLAB-D base case, with no transactive agents:

::

 cd ~/tesp/examples/ieee8500
 python3 glm_dict.py IEEE_8500
 gridlabd IEEE_8500.glm
 python3 process_gld.py IEEE_8500
 python3 process_voltages.py IEEE_8500

To run and plot the PNNL variant with smart inverter functions and
precooling thermostat agents, use the following steps. There are
also two faster 30-house examples in this directory, one of them
with agent-based calculation of the house equivalent thermal parameters.

::

 cd ~/tesp/examples/ieee8500/PNNLteam
 python3 prepare_cases.py
 ./run8500.sh
 python3 plots.py inv8500
 python3 bill.py inv8500
 python3 plot_invs.py inv8500

For more details, see `IEEE8500 Example Readme`_

.. _`EnergyPlus Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/energyplus/README.md
.. _`Loadshed Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/loadshed/README.md
.. _`PYPOWER Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/pypower/README.md
.. _`TE30 Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/te30/README.md
.. _`SGIP1 Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/sgip1/README.md
.. _`IEEE8500 Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/ieee8500/README.md

