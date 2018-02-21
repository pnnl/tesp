# TESP Examples for the NIST TE Challenge

Copyright (c) 2017-18, Battelle Memorial Institute

These example files are based on the IEEE 8500-node Feeder model, as adapted for the SGIP-3 use case and the NIST TE Challenge 2. More information is available at https://pages.nist.gov/TEChallenge/library/ and panel presentations from IEEE ISGT 2018.

1. Weather CSV files were made from the two adjust*.m files to create sunny and cloudy days from TMY data.

2. The two feeder generator MATLAB scripts add houses, water heaters, air conditioners, solar panels and batteries to the 8500-node feeder base model in the backbone subdirectory. One produces IEEE_8500.glm for the base case, used by all teams. The other produces inv8500.glm for PNNL simulations of smart inverters.

3. The house*.csv files contain equivalent thermal parameter (ETP) model parameters exported from GridLAB-D. These may be helpful if simulating houses on your own.

4. To run the base case, a current build of GridLAB-D from feature/1048 is required. A Windows binary has been released here: https://github.com/pnnl/tesp/releases

5. "gridlabd IEEE_8500.glm" runs the base case.  "Python process_gld.py IEEE_8500 &" will plot various metrics when the simulation finishes.  "Python process_voltages.py IEEE_8500" will plot all meter voltages on the same graph.

6. inv30.glm is a small 30-house test case with smart inverters, and inv8500.glm is the larger feeder model with smart inverters. Both run over FNCS with the precooling agent in precool.py.  The Mac/Linux run files are run.sh and run8500.sh, respectively.  These simulations take up to 4 hours to run. Example steps are:

    a. "Python glm_dict.py inv8500"

    b. "Python prep_precool.py inv8500"

    c. "./run8500.sh"

    d. "Python process_inv.py inv8500" after the simulation completes

These simulations require a recent build of GridLAB-D from the feature/1048 (newer than the version posted for step 5), and also FNCS.  Please consult the TESP documentation for more information about customizations, including batch files to run on Windows.


