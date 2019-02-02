# TESP Examples for the NIST TE Challenge

Copyright (c) 2017-18, Battelle Memorial Institute

These example files are based on the IEEE 8500-node Feeder model, as adapted
for the SGIP-3 use case and the NIST TE Challenge 2. More information 
is available at https://pages.nist.gov/TEChallenge/library/ and panel 
presentations from IEEE ISGT 2018.  The backbone feeder model is documented at
https://ieeexplore.ieee.org/document/5484381/

To run the base case:

1. A current build of GridLAB-D from branch feature/1048 (or newer feature/1164) is required. A Windows binary has been released here: https://github.com/pnnl/tesp/releases/tag/v0.2

2. "gridlabd IEEE_8500.glm" runs the base case.  

In order to plot results from the JSON files, Python 3 and the matplotlib package can be used:

1. "python glm_dict.py IEEE_8500" will create circuit metadata for plotting.

2. "python process_gld.py IEEE_8500 &" will plot various metrics when the simulation finishes.

3. "python process_voltages.py IEEE_8500 &" will plot all meter voltages on the same graph.

Alternatively, you can insert "recorders" into IEEE_8500.glm, which will create CSV files
for plotting and post-processing. The simulation takes longer with CSV file output.

Notes on building or modifying the base case:

1. Weather CSV files were made from the adjust*.m files to create sunny and cloudy days from TMY data.

2. Feeder generator MATLAB scripts add houses, water heaters, air conditioners, solar panels and batteries to the 8500-node feeder base model in the backbone subdirectory. One produces IEEE_8500.glm for the base case, used by all teams. The other, found under PNNLteam subdirectory, produces inv8500.glm for PNNL simulations of smart inverters.

3. The house*.csv files contain equivalent thermal parameter (ETP) model parameters exported from GridLAB-D. These may be helpful if simulating houses on your own. See http://gridlab-d.shoutwiki.com/wiki/Residential_module_user%27s_guide for information about GridLAB-D's house model, including equivalent thermal parameters (ETP).

### Base File Directory

- *adjust_solar_direct.m*; MATLAB helper function that ramps the direct solar insulation during a postulated cloud transient
- *adjust_temperature.m*; MATLAB helper function that ramps the temperature during a postulated cloud transient
- *backbone*; the IEEE 8500-node model as defined by the original authors for OpenDSS
- *CAISO_DAM_and_RTP_SG_LNODE13A_20170706-07_data.xlsx*; optional day-ahead market and real-time locational marginal price (LMP) data
- *clean.bat*; Windows batch file that removes output and temporary files
- *clean.sh*; Linux/Mac script that removes output and temporary files
- *climate.csv*; hourly temperature, humidity, solar_direct, solar_diffuse, pressure, wind_speed read by IEEE_8500.glm; **copy either sunny.csv or cloudy.csv to this file, depending on which case you wish to run**
- *Cloudy_Day.png*; screen shot of process_gld.py plots for the cloudy day
- *Cloudy_Voltages.png*; screen shot of process_voltages.py plots for the cloudy day
- *cloudy.csv*; copy to *climate.csv* to simulate a day with afternoon cloud transient
- *Cloudy.fig*; MATLAB plot of the correlated cloudy day temperature and solar irradiance
- *estimate_ac_size.m*; MATLAB helper function that estimates the house HVAC load as determined by GridLAB-D's autosizing feature. These values are embedded as comments in *IEEE_8500.glm*, which may be useful if modeling the HVAC load as a ZIP load.
- *gld_strict_name.m*; MATLAB helper function to ensure GridLAB-D names don't start with a number, as they can with OpenDSS files under *backbone*, but is not allowed in GridLAB-D
- *glm_dict.py*; creates output metadata for a GridLAB-D input file; **python glm_dict.py IEEE_8500** before attempting to plot the JSON files
- *house_ca.csv*; house ETP parameters from the base case; may be useful for your own house models.
- *house_cm.csv*; house ETP parameters from the base case; may be useful for your own house models.
- *house_ua.csv*; house ETP parameters from the base case; may be useful for your own house models.
- *house_um.csv*; house ETP parameters from the base case; may be useful for your own house models.
- *IEEE_8500.glm*; base case feeder, populated with houses, PV and batteries.
- *IEEE_8500gener_whouses.m*; MATLAB script that produces *IEEE_8500.glm* from files under *backbone*
- *main_regulator.csv*; total feeder current in the base case; may be useful in benchmarking your own power flow solver.
- *PNNLteam*; subdirectory with PNNL's participation files; see next section.
- *process_gld.py*; sample Python script to plot feeder, capacitor, regulator, voltage, inverter and house variables
- *process_voltages.py*; sample Python script to plot all house voltages
- *README.md*; this file
- *schedules.glm*; cooling, heating, lighting and other end-use appliance schedules referenced by *IEEE_8500.glm*
- *substation_load.csv*; total feeder load and positive sequence voltage in the base case; may be useful in benchmarking your own power flow solver.
- *Sunny_Day.png*; screen shot of process_gld.py plots for the sunny day
- *Sunny_Voltages.png*; screen shot of process_voltages.py plots for the sunny day
- *sunny.csv*; copy to *climate.csv* to simulate a clear, sunny day
- *sunny.fig*; MATLAB plot of the correlated sunny day temperature and solar irradiance
- *TE_Challenge_Metrics.docx*; documentation of the use case metrics of interest to the entire NIST TE Challenge 2 team

### PNNL Team Files

The subdirectory *PNNLteam* contains files used only for the pre-cooling
thermostat and smart inverter simulations, as presented by PNNL at
IEEE ISGT 2018.  See the report on NIST TE Challenge 2 for more details.
To run these simulations, you will need to install TESP, which includes 
FNCS and the *tesp_support* Python package.These simulations require a 
recent build of GridLAB-D from the feature/1048 branch (newer than the 
version posted for the base case), which is included with TESP.  Please 
consult the TESP documentation for more information about customizations, 
including batch files to run on Windows.

inv30.glm is a small 30-house test case with smart inverters, and inv8500.glm 
is the larger feeder model with smart inverters. Both run over FNCS with the 
precooling agent in precool.py.  The Mac/Linux run files are run.sh and run8500.sh, 
respectively.  These simulations take up to 4 hours to run. Example steps are:

    a. "python prepare_cases.py"
    b. "./run8500.sh" (Mac/Linux) or "run8500" (Windows)
    c. "python plots.py inv8500" after the simulation completes
    d. "python bill.py inv8500"
    e. "python plot_invs.py inv8500"

There are three GridLAB-D definitions near the top of *inv30.glm* and 
*inv8500.glm*.  These determine the solar inverter control modes, and 
(only) one of them should be uncommented.  

- //#define INVERTER_MODE=CONSTANT_PF
- //#define INVERTER_MODE=VOLT_VAR
- //#define INVERTER_MODE=VOLT_WATT

*InvFeederGen.m* was adapted from *IEEE_8500gener_whouses.m* in the parent directory,
to populate *inv8500.glm* in a similar way, but with smart inverter functions added.
See the TESP documentation for guidance on interpreting the other files in this
directory.

- *bill.py*; calculates and plots a summary of meter bills
- *clean.bat*; Windows script to clean out log files and output files
- *clean.sh*; Linux/Mac script to clean out log files and output files
- *inv30.glm*; a 30-house test case with smart inverters
- *inv8500.glm*; the 8500-node test case with smart inverters
- *invFeederGen.m*; a MATLAB helper script that populates 8500-node with smart inverters, based on the ../backbone directory
- *kill5570.bat*; helper script that stops processes listening on port 5570 (Windows)
- *kill5570.sh*; helper script that stops processes listening on port 5570 (Linux/Mac)
- *list5570.bat*; helper script that lists processes listening on port 5570 (Windows)
- *parser.py*; testing script for parsing FNCS values
- *plot_invs.py*; tabulates and plots the meter with most overvoltage counts; not valid for the 30-house case because it includes a 480-volt load
- *plots.py*; plots the GridLAB-D and agent outputs using tesp_support functions
- *prepare_cases.py*; prepares the JSON dictionaries and FNCS configuration for both cases, using tesp_support functions
- *prices.player*; time-of-day rates to publish over FNCS
- *run30.bat*; Windows script that runs the 30-house case
- *run30.sh*; Linux/Mac script that runs the 30-house case
- *run8500.bat*; Windows script that runs the 8500-node case
- *run8500.sh*; Linux/Mac script that runs the 8500-node case