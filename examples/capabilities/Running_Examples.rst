.. _RunExamples:

..
    _ Copyright (C) 2021-2022 Battelle Memorial Institute
    _ file: Running_Examples.rst

Using Docker and the autotest.py script
---------------------------------------

After installing Docker on your platform, invoke the following from inside 
a Terminal or Command Prompt, replacing your own user name for *tom*:

First time, on Windows:

::

 docker pull temcderm/tesp_core:1.0.1
 cd c:\Users\tom
 md tesp
 docker run --name tesp -it --mount type=bind,source=c:\Users\tom\tesp,destination=/data temcderm/tesp_core:1.0.1

First time, on Mac OS X:

::

 docker pull temcderm/tesp_core:1.0.1
 cd /Users/tom
 mkdir tesp
 docker run --name tesp -it --mount type=bind,source=/Users/tom/tesp,destination=/data temcderm/tesp_core:1.0.1

After executing the last of these commands, you will be at a Linux-like command
prompt inside your Docker container. Simulations must be run inside the Docker container, with results
saved on a volume shared between the host file system and the container file system. To set up your
work space and try a quick example run:

::

 cd /data
 # tesp_to_current_dir.sh
 make_tesp_user_dir.sh work
 cd work/examples/loadshed
 ./run.sh

This launches process that should all finish within a second or two, leaving some
output files \*metrics.json. If you installed the Python 3 package tesp_support on the host
system, you can plot from the host system. Results would be found under either 
*C:\\Users\\tom\\tesp\\work* for Windows or */Users/tom/tesp/work* for Mac OS X.

To run all of the examples, which may take several hours, invoke the following within
your Docker container:

::

 cd /data/work
 python3 autotest.py

When you are finished with a Docker work session:

::

 exit
 docker stop tesp

And then close the Terminal or Command Prompt you were using to run the Docker container.

To start subsequent sessions of TESP on either Windows or Mac OS X:

::

  docker start tesp
  docker exec -it tesp /bin/bash
  cd data/work


Running Examples
----------------

TESP uses TCP/IP port 5570 for communication and requires Python 3. Simulations can start many processes, 
and take minutes or hours to complete. At this time, instructions are given only for the Linux package
or Docker version of TESP, which is installable. See below for advice on running TESP in native Mac OS X or Windows.

Some general tips for Linux:

- invoke **python3** instead of just *python*
- we recommend 16 GB of memory
- high-performance computing (HPC) should be considered if simulating more than one substation-week
- you may have to increase the number of processes and open file handles allowed
- **lsof -i :5570** will show all processes connected to port 5570 
- use **ls -al** or **cat** or **tail** on log files or csv filesto show progress of a case solution
- **./kill5570.sh** will terminate all processes connected to port 5570; if you have to do this, make sure **lsof -i :5570** shows nothing before attempting another case
- it is recommended that you append **&** to any python plot commands, so they run in the background.

The examples are contained in subdirectories:

- comm; assembling single-feeder and four-feeder substations for GridLAB-D and ns-3 simulations
- energyplus; a school building simulation with price-responsive load
- loadshed; a time-controlled disconnection of part of the IEEE 13-bus system
- pypower; a 9-bus transmission system and market simulation, with generator outage
- te30; a small system with 30 houses, 1 school, 9-bus bulk system, and no voltage issues
- sgip1; a practical feeder with 1594 houses, 1 school and 9-bus bulk system
- ieee8500; a larger feeder with high solar penetration, for NIST's TE Challenge
- weatherAgent; example of publishing and forecasting weather from custom data files

Some of the support files are also contained in subdirectories:

- players; real-time LMP and non-responsive load files for the te30 case

Prerequisite - Make a Local Copy of the Examples 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's assumed that TESP has been installed to /opt/tesp, and the TESP_INSTALL
environment variable points to that location. Before proceeding, make a personal
copy of the shared TESP examples to a location where you have read/write access.
Here, we'll assume the use of ~/tesp under your home directory. From a terminal:

::

 make_tesp_user_dir.sh ~/tesp

The script should be located in your $PATH at /opt/tesp/bin 

The example shown will replace any existing contents of ~/tesp.

loadshed - verify GridLAB-D and Python over HELICS 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Results should be identical to other versions of this example.
Before running, the *clean* command will remove any existing results.

::

 cd ~/tesp/examples/loadshed
 ./clean.sh
 ./runhpy.sh
 python3 plot_loadshed.py loadshed

For more details, see `Loadshed Example Readme`_

loadshed - verify GridLAB-D and Java over HELICS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Results should be identical to other versions of this example.
Before running, the *clean* command will remove any existing results.

::

 cd ~/tesp/examples/loadshed
 ./clean.sh
 ./runhjava.sh
 python3 plot_loadshed.py loadshed

For more details, see `Loadshed Example Readme`_

loadshed - verify GridLAB-D and Python over FNCS 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Results should be identical to other versions of this example.
Before running, the *clean* command will remove any existing results.

::

 cd ~/tesp/examples/loadshed
 ./clean.sh
 ./run.sh
 python3 plot_loadshed.py loadshed

For more details, see `Loadshed Example Readme`_

loadshed - verify GridLAB-D and Java over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Results should be identical to other versions of this example.
Before running, the *clean* command will remove any existing results.

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

comm
~~~~

This example tests the assembly of GridLAB-D feeders into a TESP case. For more details, see `Comm Example Readme`_

weatherAgent
~~~~~~~~~~~~

This example tests custom weather files. For more details, see `Weather Agent Example Readme`_

sgip1 (runs longer) - 1594 houses, 1 school, 4 generators over FNCS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Ubuntu, 16 GB of memory may be required.

::

 cd ~/tesp/examples/sgip1
 python3 prepare_cases.py
 # run and plot one of the six cases, with market but no DER
 # the simulation takes about 120 minutes, use "cat SGIP*.csv" to show progress up to 172800 seconds
 ./runSGIP1b.sh
 python3 plots.py SGIP1b

For more details, see `SGIP1 Example Readme`_

ieee8500 (runs longer)
~~~~~~~~~~~~~~~~~~~~~~

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

Advice for Windows and Mac OS X
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you must run TESP on native Windows or Mac OS X, the binaries must first be
built from source. Build instructions for both platforms have been archived to
GitHub, but they have not been maintained since December 2019 and no further maintenance
is planned. Each new version of the operating system or compiler typically requires
changes to the build instructions, so it's likely that the build instructions will
fall out of date as time goes by.

Many of the Linux instructions also apply to Mac OS X users. If using Windows:

- you don't invoke **python3** directly, but please verify that **python --version** actually reports a version of Python 3
- you still run from the command prompt, either MSYS2 or Windows
- the batch files have different extensions, for example **./run.sh** becomes **run.bat** or just **run**
- the root directory for TESP and the commands to change directory are different. For example, **cd ~/tesp** becomes **cd c:\tesp**
- batch files **list5570** and **kill5570** have been provided to list and kill processes on port 5570
- on Windows 7, edit **kill5570.bat** files to uncomment line 2, and comment lines 4-10
- as with Linux and Mac OS X, if you must invoke **kill5570**, make sure **list5570** shows nothing before you attempt another simulation

.. _`Comm Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/comm/README.md
.. _`EnergyPlus Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/energyplus/README.md
.. _`IEEE8500 Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/ieee8500/README.md
.. _`Loadshed Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/loadshed/README.md
.. _`PYPOWER Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/pypower/README.md
.. _`SGIP1 Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/sgip1/README.md
.. _`TE30 Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/te30/README.md
.. _`Weather Agent Example Readme`: https://github.com/pnnl/tesp/blob/develop/examples/weatherAgent/README.md

