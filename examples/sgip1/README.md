# SGIP1 Examples

Copyright (c) 2017-18, Battelle Memorial Institute

These example files are based on the *IEEE Transactions on Power Systems* paper by Qiuhua Huang 
et. al., "Simulation-Based Valuation of Transactive Energy Systems", in publication.

To run a case:

1. python prepare_cases.py
1. ./runSGIP1a.sh (Mac/Linux) or runSGIP1a (Windows)
1. python plots.py SGIP1a

These steps are repeatable for SGIP1b, SGIP1c, SGIP1d, SGIP1e, and SGIP1ex.
After running all six cases, the compare*.py scripts may be used to plot
results from different cases on the same axes.

### File Directory

- *clean.bat*; Windows batch file that removes output and temporary files
- *clean.sh*; Linux/Mac script that removes output and temporary files
- *compare_auction.py*; script that plots auction clearing results from all 6 cases on the same axes
- *compare_csv.py*; script that plots PYPOWER CSV results from all 6 cases on the same axes, see file for variable choices by index, e.g., 'python compare_csv.py 3 &' plots the (estimated) unresponsive load from all 6 cases on the same axes.
- *compare_hvac.py*; script that plots house temperature and results from all 6 cases on the same axes
- *compare_prices.py*; script that calculates and plots all bus LMP from one case on the same axes, e.g., 'python compare_prices.py SGIP1e &'
- *compare_pypower.py*; script that plots PYPOWER JSON results from all 6 cases on the same axes
- *eplus.yaml*; FNCS configuration for EnergyPlus
- *eplus_json.yaml*; FNCS configuration for EnergyPlus agent
- *kill5570.bat*; helper script that stops processes listening on port 5570 (Windows)
- *kill5570.sh*; helper script that stops processes listening on port 5570 (Linux/Mac)
- *list5570.bat*; helper script that lists processes listening on port 5570 (Windows)
- *NonGLDLoad.txt*; text file of non-responsive loads on transmission buses
- *NonGldLoad.xlsx*; spreadsheet with plots of non-responsive loads on transmission buses
- *outputs_sgip1.glm*; requests for CSV file outputs of GridLAB-D variables
- *plots.py*; makes 4 pages of plots for a case; eg 'python plots.py SGIP1a'
- *prepare_cases.py*; sets up the dictionaries and GLD/Agent FNCS configurations for all cases
- *pypower.yaml*; FNCS configuration for PYPOWER
- *README.md*; this file
- *runall.sh*; Linux/Mac script that runs several cases in sequence, using 'sleep' between them
- *runSGIP1a.bat*; Windows script for case A
- *runSGIP1a.sh*; Linux/Mac script for case A
- *runSGIP1b.bat*; Windows script for case B
- *runSGIP1b.sh*; Linux/Mac script for case B
- *runSGIP1c.bat*; Windows script for case C
- *runSGIP1c.sh*; Linux/Mac script for case C
- *runSGIP1d.bat*; Windows script for case D
- *runSGIP1d.sh*; Linux/Mac script for case D
- *runSGIP1e.bat*; Windows script for case E
- *runSGIP1e.sh*; Linux/Mac script for case E
- *runSGIP1ex.bat*; Windows script for case Ex (case E without market)
- *runSGIP1ex.sh*; Linux/Mac script for case Ex (case E without market)
- *sgip1_pp.json*; PYPOWER system definition
- *SGIP1a.glm*; GridLAB-D file for base case with no market and GridLAB-D built-in thermostat schedules
- *SGIP1b.glm*; GridLAB-D file for case B, with market, also used for case A with NoMarket flag
- *SGIP1c.glm*; GridLAB-D file for case C, with market, added PV
- *SGIP1d.glm*; GridLAB-D file for case D, with market, added PV
- *SGIP1e.glm*; GridLAB-D file for case E, with market, added PV

