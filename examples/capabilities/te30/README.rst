This example file comprises 30 houses and a school building on a small
stiff circuit. It provides a medium-level test case for multiple transactive
agents, with or without the double-auction market.

Using FNCS
To run and plot a case without the market, from the Terminal:
::

    python3 prepare_case.py
    ./run0.sh
    python3 plots.py TE_Challenge0


To run and plot a case with the market, from the Terminal:
::

    python3 prepare_case.py
    ./run.sh 
    python3 plots.py TE_Challenge

Using HELICS
To run and plot a case without the market, from the Terminal:
::

    python3 prepare_case.py
    ./runh0.sh
    python3 plots.py TE_ChallengeH0

To run and plot a case with the market, from the Terminal:
::

    python3 prepare_case.py
    ./runh.sh 
    python3 plots.py TE_ChallengeH


To run a FNCS case from the GUI monitor for market only:
::

    python3 prepare_case.py  # unless already done above
    ./gui.sh
    from the GUI, click **Open** to open the file tesp_monitor.json from this directory
    from the GUI, click **Start All** to launch the simulations
    from the GUI, click **Quit** to stop all simulations and exit the GUI

**File Directory:**

* *clean.sh*; script that removes output and temporary files
* *eplus.yaml*; FNCS configuration for EnergyPlus
* *eplus_agent.yaml*; FNCS configuration for EnergyPlus agent
* *gui.sh*; invoke "./gui.sh" to start a solution monitor
* *kill5570.sh*; helper script that stops processes listening on port 5570
* *launch_substation.py*; helper script that launches the Python substation agents from tesp_monitor
* *launch_pp.py*; helper script that launches PYPOWER from tesp_monitor
* *NonGLDLoad.txt*; text file of non-responsive loads on transmission buses
* *outputs_te.glm*; requests for CSV file outputs of GridLAB-D variables
* *phase_A.player*; player file for phase A
* *phase_B.player*; player file for phase B
* *phase_C.player*; player file for phase C
* *plots.py*; makes 5 pages of plots for a case; eg 'python plots.py TE_Challenge'
* *prepare_case.py*; sets up the dictionaries and GLD/Agent FNCS configurations for all cases
* *pypower30.yaml*; FNCS configuration for PYPOWER
* *README.md*; this file
* *run.sh*; script for the case with market
* *run0.sh*; script for the case without market
* *TE_Challenge.glm*; GridLAB-D system definition
* *te30_pp.json*; PYPOWER system definition
* *tesp_monitor.json*; commands for solution monitor to run a case with market
* *TESP_Monitor.yaml*; FNCS configuration for the solution monitor

Copyright (c) 2017-2020, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE

