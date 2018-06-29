# PYPOWER Example

Copyright (c) 2017-18, Battelle Memorial Institute

This example simply verifies that EnergyPlus will run a building model,
and communicate over FNCS with an agent and message tracer. To run and plot it:

1. ./run.sh (Mac/Linux) or run (Windows)
2. python plots.py

In addition, traced FNCS messages will be written to tracer.out

### File Directory

- *clean.bat*; Windows batch file that removes output and temporary files
- *clean.sh*; Linux/Mac script that removes output and temporary files
- *eplus.yaml*; FNCS configuration for EnergyPlus
- *eplus_json.yaml*; FNCS configuration for EnergyPlus agent
- *kill5570.bat*; helper script that stops processes listening on port 5570 (Windows)
- *kill5570.sh*; helper script that stops processes listening on port 5570 (Linux/Mac)
- *list5570.bat*; helper script that lists processes listening on port 5570 (Windows)
- *NonGLDLoad.txt*; text file of non-responsive loads on transmission buses
- *plots.py*; makes 1 page of plots for a case; eg 'python plots.py'
- *prices.txt*; sample price changes, published over FNCS to the building's transactive agent
- *README.md*; this file
- *run.bat*; Windows script that runs the case
- *run.sh*; Linux/Mac script for the case
- *tracer.yaml*; FNCS configuration for the message tracing utility

