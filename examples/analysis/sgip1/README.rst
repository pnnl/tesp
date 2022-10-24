The SGIP1 analysis example is one of the first analysis performed with TESP. In it, an integrated whole-sale/retail real-time energy market is implemented using a double-auction transactive mechanism. The mechanism is used to evaluate a contingency event in the bulk power system when a generator trips offline during a peak-load day. The systems is also evaluated in this same scenario under a variety of rooftop solar PV and energy storage installations.

A few publications have resulted from this analysis:

:cite:`Hammerstrom:2017ta` (http://www.osti.gov/servlets/purl/1379448/)

:cite:`Huang:2018kt` (https://ieeexplore.ieee.org/document/8360969/)

More comprehensive documentation can be found in the TESP ReadTheDocs (https://tesp.readthedocs.io/en/latest/).

Running the demonstration
.........................
From the `tesp/examples/analysis/sgip1/` folder do the following:

::

    python3 prepare_cases.py
    ./runSGIP1a.sh
    python3 plots.py SGIP1a
    
Depending on your hardware this is likely to take one to two hours to complete.
These steps are repeatable for SGIP1b, SGIP1c, SGIP1d, SGIP1e, and SGIP1ex.
After running all six cases, the compare*.py scripts may be used to plot
results from different cases on the same axes.


File Directory:
...............

* *clean.sh*: script that removes output and temporary files
* *compare_auction.py*: script that plots auction clearing results from all 6 cases on the same axes
* *compare_csv.py*: script that plots PYPOWER CSV results from all 6 cases on the same axes, see file for variable choices by index, e.g., 'python compare_csv.py 3 &' plots the (estimated) unresponsive load from all 6 cases on the same axes.
* *compare_hvac.py*: script that plots house temperature and results from all 6 cases on the same axes
* *compare_prices.py*: script that calculates and plots all bus LMP from one case on the same axes, e.g., 'python compare_prices.py SGIP1e &'
* *compare_pypower.py*: script that plots PYPOWER JSON results from all 6 cases on the same axes
* *eplus.yaml*: FNCS configuration for EnergyPlus
* *eplus_agent.yaml*: FNCS configuration for EnergyPlus agent
* *kill5570.sh*: helper script that stops processes listening on port 5570 (Linux/Mac)
* *NonGLDLoad.txt*: text file of non-responsive loads on transmission buses
* *NonGldLoad.xlsx*: spreadsheet with plots of non-responsive loads on transmission buses
* *outputs_sgip1.glm*: requests for CSV file outputs of GridLAB-D variables
* *plots.py*: makes 4 pages of plots for a case; eg 'python plots.py SGIP1a'
* *prepare_cases.py*: sets up the dictionaries and GLD/Agent FNCS configurations for all cases
* *pypower.yaml*: FNCS configuration for PYPOWER
* *README.md*: this file
* *runall.sh*: script that runs several cases in sequence, using 'sleep' between them
* *runSGIP1a.sh*: script for case A
* *runSGIP1b.sh*: script for case B
* *runSGIP1c.sh*: script for case C
* *runSGIP1d.sh*: script for case D
* *runSGIP1e.sh*: script for case E
* *runSGIP1ex.sh*: script for case Ex (case E without market)
* *sgip1_pp.json*: PYPOWER system definition
* *SGIP1a.glm*: GridLAB-D file for base case with no market and GridLAB-D built-in thermostat schedules
* *SGIP1b.glm*: GridLAB-D file for case B, with market, also used for case A with NoMarket flag
* *SGIP1c.glm*: GridLAB-D file for case C, with market, added PV
* *SGIP1d.glm*: GridLAB-D file for case D, with market, added PV
* *SGIP1e.glm*: GridLAB-D file for case E, with market, added PV

Copyright (c) 2017-2022, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/main/LICENSE