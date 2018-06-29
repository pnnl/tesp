# PYPOWER Example

Copyright (c) 2017-18, Battelle Memorial Institute

This example simply verifies that PYPOWER will run a 9-bus case and communicate
over FNCS. To run and plot it:

1. ./runpp.sh (Mac/Linux) or runpp (Windows)
2. python plots.py

In addition, traced FNCS messages will be written to pptracer.out

### File Directory

- *clean.bat*; Windows batch file that removes output and temporary files
- *clean.sh*; Linux/Mac script that removes output and temporary files
- *kill5570.bat*; helper script that stops processes listening on port 5570 (Windows)
- *kill5570.sh*; helper script that stops processes listening on port 5570 (Linux/Mac)
- *list5570.bat*; helper script that lists processes listening on port 5570 (Windows)
- *NonGLDLoad.txt*; text file of non-responsive loads on transmission buses
- *plots.py*; makes 1 page of plots for a case; eg 'python plots.py'
- *ppcase.json*; PYPOWER system definition
- *pptracer.yaml*; FNCS configuration for the message tracing utility
- *pypower.yaml*; FNCS configuration for PYPOWER
- *README.md*; this file
- *runpp.bat*; Windows script that runs the case
- *runpp.sh*; Linux/Mac script for the case

