# Communication Network Example

This example will compare a transactive case with and without an external
communication network. To run and plot the base case without comms on Mac/Linux:

1. python3 make_comm_base.py
2. cd Nocomm_Base
3. chmod +x *.sh
4. ./run.sh
5. python3 plots.py  # use pythonw on Mac

On Windows:

1. python make_comm_base.py
2. cd Nocomm_Base
3. run
4. python plots.py

In the copied boilerplate Nocomm_Base/plots.py script, the EnergyPlus plot
requests should be removed or commented out before use, because 
EnergyPlus is not used in this example.

### File Directory

- *make_comm_base.py*; script that reads Nocomm_Base.json and creates a self-contained TESP case in the Nocomm_Base subdirectory (creates and/or overwrites the subdirectory as needed)
- *Nocomm_Base.json*; case configuration for the R5-12.47-5 feeder with no large building and no communications network
- *show_config.py*; script that shows the case configuration GUI; use to open, edit and save Nocomm_Base.json

Copyright (c) 2017-2019, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE
