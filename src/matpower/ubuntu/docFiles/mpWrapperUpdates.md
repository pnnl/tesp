# How to Install and Run MATPOWER with FNCS #
***************************************
_Author: **Laurentiu Dan Marinovici**_
***************************************

If MATPOWER is one of the simulators used as part of the FNCS (**F**ramework for **N**etwork **C**o-**S**imulation) environment, the following should be considered.

## Installation guide - Linux ##

MATPOWER power flow (PF) and optimal power flow (OPF) solvers reside as functions in a shared object named ```libMATPOWER.so```, after being compiled on a computer with a complete licensed version of Mathworks MATLAB installed. Running the MATPOWER functions and the dependent MATLAB functions requires that at least MATLAB Compiler Runtime (MCR) (downloaded for free from MATHWORKS webpage [here](https://www.mathworks.com/products/compiler/matlab-runtime.html)) is installed. The version of installed MCR has to match the version of the fully licensed version of MATLAB under which the files had been compiled. The compiler version should be listed at the beginning of the ```libMATPOWER.h``` file.

Files needed for deployment (for this case, at least, in order to be able to compile and run):
  - ```start_MATPOWER.cpp``` - the main wrapper around the MATPOWER functions that establishes the communication between MATPOWER and FNCS, reads any data input, arranges model data according to the MATLAB type, performs calculations and returns to FNCS the data needed to be available to other simulators;
  - ```libMATPOWER.h```, ```libMATPOWER.so``` - MATPOWER compiled object for deployment under Linux;
  - ```case9.m```, or any other - MATPOWER case file, that needs to have extra data added;
  - ```matpowerintegrator.h```, ```matpowerintegrator.cpp``` - define the functions that integrate MATPOWER within the FNCS environment;
  - ```read_load_profile.cpp``` - reads in an a-priori built load shape meant to align to a standard daily residential power consumption initialized to the values corresponding to the transmission structure of the MATPOWER model;
  - ```read_model_dim.cpp``` - reads in the MATPOWER model dimensions in order to be able to allocate the correct memory in the C++ wrapper (Observation: I went this route because I found it hard to make it work with dynamic allocation of memory; however, it seems to be able to compile under Linux using _gcc_ compiler; the Windows case needs to be revised);
  - ```read_model_data.cpp``` - reads the actual data that describes the transmission network in MATPOWER;
  - ```matpowerGeneratorMetrics.h```, ```matpowerGeneratorMetrics.cpp``` - functions to write generator metrics into JSON format;
  - ```matpowerLoadMetrics.h```, ```matpowerLoadMetrics.cpp``` - functions to write load metrics into JSON format.
  - ```logging.hpp``` - sets different level of messaging for debugging purposes;
  - ```Makefile``` - the script that guides the make utility to choose the appropriate program files that are to be compiled and linked together, also specifying the paths to MCR, FNCS and installation (should be modified accordingly);
  - an input file in yaml format (but really just a text file) with the simulator name and subscriptions, needed at runtime (see the example in the repository ```../inputFiles/``` folder).

To be able to save the metrics in the JSON format, the ```JsonCpp``` C++ library for interacting with JSON is used, and can be downloaded [here](https://github.com/open-source-parsers/jsoncpp). Download and follow the installation steps.

It is recommended that something similar to

```
echo "Setting up environment variables for MATPOWER"
MCRROOT="/usr/local/MATLAB/MATLAB_Runtime/v92"
echo "---------------------------------------------"
LD_LIBRARY_PATH=.:${MCRROOT}/runtime/glnxa64
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${MCRROOT}/bin/glnxa64
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${MCRROOT}/sys/java/jre/glnxa64/jre/lib/amd64/server/
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${MCRROOT}/sys/opengl/lib/glnxa64
echo "LD_LIBRARY_PATH is ${LD_LIBRARY_PATH}"
echo "---------------------------------------------"
```

be run to set up the paths to the MATLAB or MCR executables and libraries.

Example of how to set up and run the MATPOWER simulator (extracted from a shell script that starts a co-simulation scenario)
```
# ===================================================== setting up the MATPOWER environment ====================================================
# MATLAB Compile Runtime (MCR) set-up
echo "Setting up environment variables for MATPOWER"
MCRROOT="/usr/local/MATLAB/MATLAB_Runtime/v92"
echo "---------------------------------------------"
LD_LIBRARY_PATH=.:${MCRROOT}/runtime/glnxa64
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${MCRROOT}/bin/glnxa64
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${MCRROOT}/sys/java/jre/glnxa64/jre/lib/amd64/server/
# LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${MCRROOT}/sys/os/glnxa64
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${MCRROOT}/sys/opengl/lib/glnxa64
echo "LD_LIBRARY_PATH is ${LD_LIBRARY_PATH}"
echo "---------------------------------------------"
# MATPOWER installation folder
mpDir="/home/laurentiu/work/CoSimulation/CCSI28-MATPOWERinstall"
# FNCS broker setting for MATPOWER; this could also be set up in the ZPL file
fncsBrMP="tcp://localhost:5570"
# set FNCS to print or not at standard output for MATPOWER
mpSTDOUTlog="no"
# set FNCS to log or not the outputs for FNCS broker
mpFILElog="no"
# MATPOWER case
caseNum="9"
# Total number of substations; could be different than the number running under this scripts
gldTotalNum="1"
#mpCase="./caseFiles/case${caseNum}_${gldTotalNum}Subst_2GenAtBus2.m"
mpCase="./caseFiles/case${caseNum}_CCSI.m"
# real load profile file
realLoadFile="./inputFiles/real_power_demand_CCSI.txt"
# reactive load profile file
reactiveLoadFile="./inputFiles/reactive_power_demand_CCSI.txt"
# MATPOWER configuration file for FNCS
mpFNCSConfig="./inputFiles/matpowerConfig_CCSI.yaml"
# clearing market time/interval between OPF calculations
mpMarketTime=300
# stop time for MATPOWER simulation in seconds
mpStopTime=7200
# presumed starting time of simulation
# needs to be double quoted when used becase the string has spaces
mpStartTime="2012-01-01 00:00:00 PST"
# load metrics file output
mpLoadMetricsFile="./metricFiles/loadBus_case${caseNum}_metrics.json"
# dispatchable load metrics file output
mpDispLoadMetricsFile="./metricFiles/dispLoadBus_case${caseNum}_metrics.json"
# generator metrics file output
mpGeneratorMetricsFile="./metricFiles/generatorBus_case${caseNum}_metrics.json"
# output file
mpOutFile="./outputFiles/mp${gldTotalNum}Subst.out"
# MATPOWER logging level
# mpLOGlevel="DEBUG4"
mpLOGlevel="LMACTIME"

# ================================================ starting MATPOWER ==================================================================
export LD_LIBRARY_PATH && export FNCS_CONFIG_FILE=$mpFNCSConfig && export FNCS_LOG_STDOUT=$mpSTDOUTlog && export FNCS_LOG_FILE=$mpFILElog && export FNCS_LOG_LEVEL=$fncsLOGlevel && export MATPOWER_LOG_LEVEL=$mpLOGlevel && cd $mpDir && ./start_MATPOWER $mpCase $realLoadFile $reactiveLoadFile $mpStopTime $mpMarketTime "$mpStartTime" $mpLoadMetricsFile $mpDispLoadMetricsFile $mpGeneratorMetricsFile &> $mpOutFile &
```

## Installation guide - Windows ##

So far (that is by 2016/12/13), there haven't been any simulations done involving GridLAB-D and MATPOWER within FNCS environment in Windows. However, the following issues need to be addressed in order to be ale to do accomplish it.

  - Install the corresponding MCR for Windows.
  - Compile MATPOWER on a Windows platform with MATLAB installed, and including the compiler toolbox.
  - Compile the C++ wrapper with FNCS.


## MATPOWER wrapper update history ##
## Launching the MATPOWER Power Flow / Optimal Power Flow solver from a C++ wrapper ##
****************************************
```start_MATPOWER.cpp```  
_Copyright (c) 2013-2023 Battelle Memorial Institute_  
_Written by_ **Laurentiu Dan Marinovici**, Pacific Northwest National Laboratory  
_Additional updates by_ **Jacob Hansen**, Pacific Northwest National Laboratory
****************************************

Main purposes of the "wrapper", that is the code in the C++ file ```start_MATPOWER.cpp```:
  - Read the MATPOWER data file that resides in a ```.m``` file (the MATPOWER case file),
  - Create the data structure needed by the MATPOWER solvers, call the solver (```runpf``` or ```runopf``` functions) when necessary, return the results, and publish the required ones to FNCS.
  - Write metrics files into JSON files.

Due to the fact that the wrapper file "start_MATPOWER.cpp" has been going through many updates, I have taken out the updates
list from the actual source file and present them below.

  - [x] Update: 03/05/2014  
    Purpose:
      - Implement possibility of running it with multiple instances of GridLAB-D.
  - [x] Update: 03/21/2014  
    Purpose:
      - Added the possibility to change the generation/transmission topology, by making on generator go off-line.
      - Branches could also be set-up to go off-line. (not implemented yet though).
  - [x] Update: 04/08/2014  
    Purpose:
      - Ability to run both the regular power flow and the optimal power flow.
      - The optimal power flow is going to be solved 5 seconds before the end of every minute, to be able to communicate the newly calculated price to GLD in time.
  - [x] Update: 05/02/2014  
    Purpose:
      - Add the ability to receive a load profile as the "static load" at the feeder buses, profile that would simulate a real-life one day load profile.  
      **WARNING:** Currently, the code is written to accommodate the model used, that is there are only 6 load buses (out of a total of 9 buses), and only 3 out of these 6 have non-zero loads, where the profile is going to be modified such that it follows a 24h real-life-like shape.
  - [x] Update: 06/17/2014  
    Purpose:
      - Took out some functions to separate cpp files and created ```read_input_data.h``` header that includes all the functions required to read the simulation model
  - [x] Update: 07/02/2014  
    Purpose:
      - Modified the read load profile function in ```read_load_profile.cpp```, to be able to read as many profiles as necessary, depending on how many substations I have. Basically, the load profile data comes into a file containing 288 values per row (every 5-minute data for 24-hours), and a number of rows greater than or equal to the number of substations.
  - [x] Update: 07/23/2014  
    Purpose:
      - Added NS3_flag that allows to call the corresponding send-price function, depending on whether NS-3 is used ot not.
      - Got rid of it on 2015/09/25, due to using FNCS2.
  - [x] Update: 10/24/2014  
    Purpose:
      - Added the incentive calculator functionality.
  - [x] Update: 03/10/2015  
    Purpose:
      - Taking out the incentive calculation, and trying to make it compatible with FNCS2.
      - Got rid of it, since project did not go on.
  - [x] Update: 04/02/2015  
    Purpose:
      - Added a third parameter as input representing the final time of the MATPOWER simulator. Once the time returned by FNCS reaches this value, MATPOWER simulator sends a nice BYE signal to let broker know it ended. It will DIE if it cannot complete successfully.
  - [x] Update: 09/09/2015  ]
    Purpose:
      - While discussing scalability issue, the idea of having multiple distribution networks (GridLAB-D instances) connected to the same node/bus of a transmission network raised the question of correctly subscribing and aggregating the loads connected to the same bus. One idea is to create a map between generic subscription names and the corresponding location where they are to be placed. A map matrix has been created in the MATPOWER model in the form, similar to:

    | Subscriber name | Subscriber bus number |
    |:---------------:|:---------------------:|
    | SUBSTATIONCOM1  |           7           |
    | SUBSTATIONCOM2  |           7           |
    | SUBSTATIONCOM3  |           5           |
    | SUBSTATIONCOM4  |           5           |
    | SUBSTATIONCOM5  |           5           |

- [x] Update: 02/17/2017  
    Purpose:
      - For the Transactive Energy Systems Platform (TESP) project, a set of metrics are needed. They are to be saved in a JSON structure.
      - ```jsoncpplib``` is going to be used to accommodate for saving the necessary data into a file.
  - [x] Update: 04/18/2017  
    Purpose:
      - Compliance with the **MATPOWER V6**: the MATPOWER solve options are given as a structure in version 6.
      - Though there are backwards compatibilities, the option variable is now a structure rather than a matrix of doubles.
  - [x] Update: 06/26/2017  
    **Remember**: Now, MATPOWER is to be called through FNCS at a minimum rate of 30 seconds, or whatever desired and set in the ```.zpl``` file as ```time_delta```. That ensures the power flow calculation won't be forced to recalculate for just one single distribution change on a very large scale system.  
    Purpose:
      - First stage of CCSI 2.8 complexity adding to the simulation environment to test control algorithms:
        - change to AC power flow calculation as default
        - at market cycles, DC OPF is run to get the marginal prices, and immediately after, an AC PF is run with the newly dispatched generation to recalculate the bus voltages (in the out matrices for the AC PF only some entries are changed, so the price columns are not overwritten).
      - 2 functions and the corresponding variables have been added to the ```matpowerintegrator``` files and called in the wrapper, in order to be able to get the maximum dispatchable loads and the demand curve, that is
        - ```getMaxDispLoad``` - to extract the maximum dispatchable load at a bus that has dispatchable load (that is, it is listed under the generation matrix as negative generation)
        - ```getDLDemandCUrve``` - to extract the coefficients of the demand curve corresponding to the dispatchable loads inserted into the transmission MATPOWER model as negative loads; hence these coefficients need to be transformed into the coefficients of a negative supply curve.
  - [x] Update: 09/12/2017
    Purpose:
      - Wrapper code snippet timing to analyze which parts of the code might cause slow-downs, especially when running large-scale model simulations:
        - ```matpowerintegrator``` has a new function, aka ```GetTimeMs64()``` that would calculate the epoch time in milliseconds; requires ```#include <sys/time.h>``` for Linux
        - however, using the simple ```clock_t``` types and ```clock()``` functions in ```ctime``` proved to give the same results, and easier to implement; the timing is relative to the process start time, in this case
        - ```logging.hpp``` has also been modified to include an extra `debugging` level ```LMACTIME```, in order to only collect the corresponding messages in the output file.
      - Switch between AC power flow and DC power flow
        - MATPOWER is set up to perform AC powerflow to update the voltages for the distribution, every x-seconds. However, AC power flow fails to converge sometimes. Therefore, code has been added to run a DC power flow if that happens, such that we do not get bad results propagated. **REMEMBER**: We might need to rethink this, and/or add the same algorithm for the OPF calculation.
      - Correctly updating the load at the bus after OPF to prepare for PF (this is an update Jacob did a while back, but just got documented)
        - For the dispatchable loads, the aggregators will publish 2 quantities:
          - in ```dispLoadValue[0]```, the maximum available dispatchable load for the next cycle (goes as negative value in Pmin as negative generation limit), given from constructing the demand curve,
          - in ```dispLoadValue[1]```, the currently dispatched load (sum of power of all ON devices at that time), gets subtracted from the corresponding load at the bus before OPF calculation (thus, the bus PQ represents the non-flexible/fixed load), and gets added back after the OPF, such that the voltages are recalculated during PF for the newly dispatched generation; at the same time, the dispatched load/negative generation is expected to be obtained next cycle after the devices get broadcasted the new marginal costs.
        - 
