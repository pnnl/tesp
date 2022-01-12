# Transactive Energy Simulation Platform (TESP)

Copyright (c) 2017-2022, Battelle Memorial Institute

Documentation: http://tesp.readthedocs.io

License: https://github.com/pnnl/tesp/blob/master/LICENSE

TESP includes two co-simulation frameworks, FNCS and HELICS,
along with several federates: GridLAB-D, EnergyPlus v9.3, AMES/PSST,
OpenDSSCmd, PYPOWER and ns-3 (optimized build with logging enabled).
The Octave 5.2+ deployment of MATPOWER/MOST v7.1 is supported, but must
be installed separately. TESP comes with several test cases,
including the NIST TE Challenge 2, the SGIP use case 1, and an
8-bus test system for ERCOT. There are examples of the double-auction
real-time market in real-time and day-ahead modes, and a
transactive consensus mechanism for large buildings. The intended
use case for TESP is to focus on the development and testing
of transactive control agents, without having to build up a large
system simulation infrastructure. There are sample agents provided
in Python 3.6+, Java 11+, and C/C++.

TESP runs natively on Linux. Earlier versions also ran on Windows and
Mac OS X natively, but the maintenance cost was significant. After
we noticed that simulations run faster in a Linux virtual machine than
in the native builds, on the same computer, we no longer maintain the
native Windows and Mac OS X builds. 

There are three options to install:

1. For Linux, download and run the installer from
   https://github.com/pnnl/tesp/releases. This takes
   1.3 GB, plus working space for output and your own cases.
2. For Windows, Mac OS X or Linux, use the Docker images
   installed from *docker pull temcderm/tesp_core:v1*
   The images total approximately 2 GB, and you will
   need working space for output and your own cases.
3. For Linux, **build** the components as directed at:
   https://tesp.readthedocs.io/en/latest/Linux_Build_Link.html
   This requires around 12 GB for builds, plus several
   more GB for output files.

Any of these three options will support agent development in TESP.
Option 3, the full build, is only necessary for those working on
the co-simulation frameworks or the large simulation federates.

After installing TESP, you can test it as follows:

1. First, log out and log back in. From a terminal, invoke _which gridlabd_ 
   to make sure the paths have been set up.
2. Second, if you've had PSST installed before, invoke _pip3 show psst_ 
   to make sure the version number is at least 0.1.9.  If not, use 
   _pip3 install psst --upgrade_ to make sure PSST has been upgraded.
   (The installer sometimes fails to upgrade PSST, and the reason
   is under investigation.)
3. Set up a working directory and manually run the quick loadshed examples:
   https://tesp.readthedocs.io/en/latest/Running_Examples_Link.html#prerequisite-make-a-local-copy-of-the-examples
   This verifies that FNCS, HELICS and GridLAB-D are all working
   with Python and Java.
4. Run a longer automated test suite by invoking
   *python3 autotest.py* from your working directory. This tests
   nearly all of the federates in different combinations, but it
   may take a few hours to complete.
5. The SGIP, NIST and ERCOT cases take many hours to run. They
   are in a separate automated test suite *python3 autotest_long.py*
   run from your working directory.
6. For MATPOWER/MOST, see the readme file at https://github.com/pnnl/tesp/tree/develop/ercot/case8/dsostub.

Change log:

- v0.1.2  Patch for tape shield / concentric neutral 
          cables with separate neutral conductor.
- v0.3.0  Refactored agent classes for DSO+T study
- v0.9.5  HELICS, MATPOWER/MOST, ERCOT and E+ 9.3 examples
- v1.0.0  Tested on Ubuntu 18.04 LTS and 20.04 LTS
- v1.0.1  Updates to consensus mechanism, HELICS 2.6.1
- v1.0.2  ns-3 has optimized build with logging enabled
