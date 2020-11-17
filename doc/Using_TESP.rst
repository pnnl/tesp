Using the TESP
==============

TESP runs primarily on Linux (Ubuntu tested). Execution on Windows
and Mac OS X is available through a Linux virtual machine or Docker, 
both of which are free downloads. See this site and the repository 
at https://github.com/pnnl/tesp/ for more information. 

TESP comes with the following components:

-  Python packages for TEAgents, case configuration and post-processing.

-  GridLAB-D for electric power distribution systems, along with residential and small commercial buildings, built with HELICS and FNCS.

-  EnergyPlus v8.3 to simulate large buildings, built with FNCS and a bridge to HELICS.

-  PYPOWER for bulk system power flow and optimal power flow, with HELICS and FNCS wrappers.

-  ns-3 for communication system simulation, built with HELICS and in debug mode to enable logging.

-  A command-line version of OpenDSS, built with FNCS.

-  Examples of simple and unpackaged TEAgents in Python, Java and C++.

-  Examples from NIST TE Challenge II and other case studies.

-  An 8-bus test system based on public ERCOT data.

There are two ways of using the TESP:

-  Install TESP: this may require administrator privileges on the target
   computer and supplemental downloads. It will be possible to
   develop new TEAgents and valuation scripts by modifying or
   developing Python, Java or C++ code.

-  Build TESP: in addition to the skill set for installing TESP, users
   should be familiar with configuring environments and using C/C++
   compilers on the target computer. This approach enables the
   user to develop new TEAgents (as above), and also to replace or upgrade 
   co-simulation federates within TESP.

.. toctree::
   :maxdepth: 3

   Installing_Ubuntu_Link
   Installing_Windows_Link
   Installing_MacOSX_Link
   Running_Examples_Link

