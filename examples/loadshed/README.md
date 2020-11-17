# TESP Loadshed Examples

This directory contains Python and Java versions of a
loadshed example on the 13-bus IEEE test feeder, modeled
in GridLAB-D. It differs from the other examples, in
not using the *tesp_support* Python package. Instead, three
local source files have been provided as possible starting
points in developing your own source files in Python or Java:

1. *loadshed.py* is a loadshedding agent, implemented in Python for FNCS. Test with *run.sh*. A local copy of *fncs.py* is provided, so this example runs
without importing the *tesp_support* package.
2. *loadshed.java* is the same loadshedding agent, implemented in Java for FNCS. Test with *runjava.sh*
3. *helicshed0.py* is the same loadshedding agent, implemented in Python for HELICS. Test with *runhpy0.sh*
4. *helicshed.java* is the same loadshedding agent, implemented in Java for HELICS. Test with *runhjava.sh*
5. *helicshed.py* is the same loadshedding agent, implemented in Python for HELICS with ns-3. Test with *runhpy.sh*
6. *plot_loadshed.py* is a plotting program for the simulation results
7. *kill5570.sh* is a helper script that shuts down a TESP federation
8. *kill23404.sh* is a helper script that shuts down a HELICS federation
9. Various JSON files are used to configure the HELICS federates for *runhpy0.sh* and *runhpy.sh* and *runhjava.sh*
10. Various TXT files are used to configure helics_recorder for tracing output
11. *Makefile* builds the ns-3 federate for *runhpy.sh*.
12. *loadshedCommNetwork.cc* is the ns-3 federate source code. Note that ns-3 logging is enabled only if ns-3 was built in debug mode.
13. *loadshed.glm* is the IEEE 13-bus model for GridLAB-D, configured to run as a FNCS or HELICS federate with various options
14. *loadshed_dict.json* supports plotting the GridLAB-D metrics
15. *killtesp.sh* is an alternative method of shutting down the TESP federation by process ID (pid) rather than by the port (5570 or 23404), Currently, only *runhpy.sh* captures pids to a file for use by this script.

For example, to run the simulations with HELICS Python agent and no ns-3 federate:

    ./runhpy0.sh

To run the simulation with HELICS Python and ns-3, you first have to build the ns-3 federate, then run the example:

    make
    sudo make install
    ./runhpy.sh

To plot the simulation results for any of the agent cases:

    python3 plot_loadshed.py loadshed

To clean up the simulation results from any of the agent cases:

    ./clean.sh

If you're interested in C++ agent development, the GitHub
source code for *eplus_json*, under *tesp/src/energyplus*,
may provide a useful starting point. *eplus_json* handles
time synchronization, FNCS publish, FNCS subscribe, and
generating JSON output files with metrics.

Copyright (c) 2017-2020, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE


