.. _RunExamples:

Running Examples
----------------

These examples run very much the same on all three supported platforms.
TESP Uses TCP/IP port 5570 for communication. Simulations can start many processes, 
and take minutes or hours to complete. We recommend 16 GB of memory.

On Linux and Mac OS X:

- you may have to increase the number of processes and open file handles allowed
- **lsof -i :5570** will show all processes connected to port 5570 
- use **ls -al** or **cat** on log files or csv filesto show progress of a case solution
- **./kill5570.sh** will terminate all processes connected to port 5570; if you have to do this, make sure **lsof -i :5570** shows nothing before attempting another case
- it is recommended that you append **&** to any python plot commands, so they run in the background.

The instructions are given for Linux and Mac OS X. If using Windows:

- you still run from the command prompt, either MSYS or Windows
- the batch files have different extensions, for example **./run.sh** becomes **run.bat** or just **run**
- the root directory for TESP and the commands to change directory are different. For example, **cd ~/src/tesp** becomes **cd c:\tesp**
- batch files **list5570** and **kill5570** have been provided to list and kill processes on port 5570
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

::

 cd ~/src/tesp/examples/loadshed
 python glm_dict.py loadshed
 ./run.sh
 python plot_loadshed.py loadshed

loadshed - verify GridLAB-D and Java over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Results should be identical to the Python version of this example.

::

 cd ~/src/tesp/examples/loadshed
 python glm_dict.py loadshed
 ./runjava.sh
 python plot_loadshed.py loadshed

energyplus - verifies EnergyPlus over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/examples/energyplus
 ./run.sh
 python process_eplus.py eplus

pypower - verifies PYPOWER over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/examples/pypower
 ./runpp.sh
 python process_pypower.py ppcase

te30 - 30 houses, 1 school, 4 generators over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/examples/te30
 python prep_agents.py TE_Challenge
 python glm_dict.py TE_Challenge
 chmod +x launch_TE_Challenge_agents.sh
 ./run30.sh
 # the simulation takes about 10 minutes, use "cat TE*.csv" to show progress up to 172800 seconds
 python process_eplus.py te_challenge
 python process_pypower.py te_challenge
 python process_agents.py te_challenge
 python process_gld.py te_challenge

sgip1 - 1594 houses, 1 school, 4 generators over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Ubuntu, 16 GB of memory may be required.

::

 cd ~/src/tesp/examples/sgip1
 python prep_agents.py SGIP1b
 python glm_dict.py SGIP1b
 ./runSGIP1b.sh
 # the simulation takes about 120 minutes, use "cat SGIP*.csv" to show progress up to 172800 seconds
 python process_eplus.py SGIP1b
 python process_pypower.py SGIP1b
 python process_agents.py SGIP1b
 python process_gld.py SGIP1b

ieee8500
~~~~~~~~

To date, only a base case has been developed for GridLAB-D, with no market

::

 python glm_dict.py IEEE_8500
 gridlabd IEEE_8500.glm
 python process_gld.py IEEE_8500
 python process_voltages.py IEEE_8500


