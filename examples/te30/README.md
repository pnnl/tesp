# TE30 Example

This example file comprises 30 houses and a school building on a small
stiff circuit. It provides a medium-level test case for multiple transactive
agents, with or without the double-auction market.

To run and plot a case without the market, from the Terminal:

1. python3 prepare_case.py
2. ./run0.sh
3. python3 plots.py TE_Challenge0

To run and plot a case with the market, from the Terminal:

1. python3 prepare_case.py
2. ./run.sh 
3. python3 plots.py TE_Challenge

To run a case from the GUI monitor:

1. python3 prepare_case.py  # unless already done above
2. ./gui.sh
3. from the GUI, click **Open** to open the file tesp_monitor.json from this directory
4. from the GUI, click **Start All** to launch the simulations
5. from the GUI, click **Quit** to stop all simulations and exit the GUI

### File Directory

- *clean.sh*; script that removes output and temporary files
- *eplus.yaml*; FNCS configuration for EnergyPlus
- *eplus_json.yaml*; FNCS configuration for EnergyPlus agent
- *gui.sh*; invoke "./gui.sh" to start a solution monitor
- *kill5570.sh*; helper script that stops processes listening on port 5570
- *launch_substation.py*; helper script that launches the Python substation agents from tesp_monitor
- *launch_pp.py*; helper script that launches PYPOWER from tesp_monitor
- *NonGLDLoad.txt*; text file of non-responsive loads on transmission buses
- *outputs_te.glm*; requests for CSV file outputs of GridLAB-D variables
- *plots.py*; makes 5 pages of plots for a case; eg 'python plots.py TE_Challenge'
- *prepare_case.py*; sets up the dictionaries and GLD/Agent FNCS configurations for all cases
- *pypower30.yaml*; FNCS configuration for PYPOWER
- *README.md*; this file
- *run.sh*; script for the case with market
- *run0.sh*; script for the case without market
- *TE_Challenge.glm*; GridLAB-D system definition
- *te30_pp.json*; PYPOWER system definition
- *tesp_monitor.json*; commands for solution monitor to run a case with market
- *TESP_Monitor.yaml*; FNCS configuration for the solution monitor

Copyright (c) 2017-2020, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE

