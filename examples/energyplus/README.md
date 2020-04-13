# EnergyPlus Example

This example simply verifies that EnergyPlus will run a building model,
and communicate over FNCS with an agent and message tracer. To run and plot it:

1. ./run.sh
2. python3 plots.py

In addition, traced FNCS messages will be written to tracer.out

### File Directory

- *clean.sh*; script that removes output and temporary files
- *eplus.yaml*; FNCS configuration for EnergyPlus
- *eplus_agent.yaml*; FNCS configuration for EnergyPlus agent
- *kill5570.sh*; helper script that stops processes listening on port 5570 (Linux/Mac)
- *NonGLDLoad.txt*; text file of non-responsive loads on transmission buses
- *plots.py*; makes 1 page of plots for a case; eg 'python plots.py'
- *prices.txt*; sample price changes, published over FNCS to the building's transactive agent
- *README.md*; this file
- *run.sh*; Linux/Mac script for the case
- *tracer.yaml*; FNCS configuration for the message tracing utility

Copyright (c) 2017-2020, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE

