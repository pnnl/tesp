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
3. *helicshed.py* is the same loadshedding agent, implemented in Python for HELICS. Test with *runhpy.sh*
4. *helicshed.java* is the same loadshedding agent, implemented in Java for HELICS. Test with *runhjava.sh*
5. *plot_loadshed.py* is a plotting program for the simulation results

For example, to run the simulations with HELICS Python agent:

    ./runhpy.sh

To plot the simulation results:

    python3 plot_loadshed.py loadshed

To clean up the simulation results:

    ./clean.sh

If you're interested in C++ agent development, the GitHub
source code for *eplus_json*, under *tesp/src/energyplus*,
may provide a useful starting point. *eplus_json* handles
time synchronization, FNCS publish, FNCS subscribe, and
generating JSON output files with metrics.

Copyright (c) 2017-2020, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE


