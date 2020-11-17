# EnergyPlus Example

This example simply verifies that EnergyPlus will run a building model,
and communicate over HELICS with an agent and message tracer. To run and plot it:

1. ./runh.sh
2. python3 plots.py

In addition, traced messages will be written to recorder and log files.

### Subdirectories

- *eplusHelicsExample*; custom-built HELICS example for testing
- *forSchoolBase*; custom-built school dual controller EMS files for FNCS and HELICS
- *Windows*; helper scripts to run on Windows (no longer supported outside of Docker or VM)

### File Directory

- *archivedEms.idf*; original version of the custom-built school dual controller EMS (deprecated)
- *batch_ems_case.sh*; top-level script that simulates all reference buildings with EMS; calls run_seasonal_cases.sh
- *batch_plots.sh*; top-level script that plots all reference buildings with EMS; calls seasonal_plots.sh
- *bridge_eplus_agent.json*; configuration file for runfh_bridge.sh example (deprecated)
- *clean.sh*; script that removes output and temporary files
- *compile_png.py*; compiles all plots from batch_plots.sh into a Word document
- *eplus.yaml*; FNCS configuration for EnergyPlus
- *eplus_agent.yaml*; FNCS configuration for EnergyPlus agent
- *eplus_agentH.yaml*; HELICS configuration for EnergyPlus agent
- *eplusH.json*; HELICS configuration for EnergyPlus
- *helicsRecorder.json*; JSON configuration of the HELICS recorder
- *helicsRecorder.txt*; text configuration file for the HELICS recorder (deprecated)
- *kill23404.sh*; helper script that stops processes listening on port 23404 for HELICS (Linux/Mac)
- *kill5570.sh*; helper script that stops processes listening on port 5570 for FNCS (Linux/Mac)
- *make_all_ems.sh*; after run_baselines.sh, this script produces the EMS programs in separate IDF files
- *make_ems.sh*; makes a single EMS program from the contents of 'output', which typically comes from SchoolBase.idf
- *plots.py*; makes 1 page of plots for a case; eg 'python plots.py'
- *prices.txt*; sample price changes, published over FNCS to the building's transactive agent
- *README.md*; this file
- *run.sh*; Linux/Mac script for the case using FNCS (deprecated)
- *run2.sh*; FNCS version of the secondary school building the auto-generated EMS
- *run_baselines.sh*; simulate the reference buildings for one year, in preparation to make EMS programs
- *run_ems_case.sh*; runs a single HELICS-based reference building with given dates and price response
- *run_seasonal_cases.sh*; calls run_ems_case.sh for one reference building, summer and winter, with and without price response
- *runfh_bridge.sh*; runs FNCS EnergyPlus, bridged through a dual agent to HELICS federates (deprecated)
- *runh.sh*; Linux/Mac script for the case using HELICS
- *SchoolBase.idf*; custom-built school building without the EMS
- *seasonal_plots.sh*; 
- *tabulate_responses.py*; 
- *tracer.yaml*; FNCS configuration for the message tracing utility

Copyright (c) 2017-2020, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE

