


This example simply verifies that PYPOWER will run a 9-bus case and communicate
over FNCS. To run and plot it:

::

 ./runpp.sh
 python3 plots.py

In addition, traced FNCS messages will be written to pptracer.out

This example simply verifies that PYPOWER will run a 9-bus case and communicate
over HELICS. To run and plot it:

::

 ./runhpp.sh
 python3 plots.py

TODO: Player/Recorder comments


**Directory contents:**

* *clean.sh*; script that removes output and temporary files
* *helics_loads.txt*; HELICS player file for distribution loads system
* *helicsRecorder.txt*; HELICS recorder file for different system outputs
* *NonGLDLoad.txt*; text file of non-responsive loads on transmission buses
* *plots.py*; makes 1 page of plots for a case; eg 'python plots.py'
* *ppcase.json*; PYPOWER system definition
* *pptracer.yaml*; FNCS configuration for the message tracing utility
* *pypower.yaml*; FNCS configuration for PYPOWER
* *pypowerConfig.json*; HELICS configuration for PYPOWER
* *README.md*; this file
* *runhpp.sh*; script for running the case - HELICS
* *runpp.sh*; script for running the case - FNCS

Copyright (c) 2017-2022, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/main/LICENSE
