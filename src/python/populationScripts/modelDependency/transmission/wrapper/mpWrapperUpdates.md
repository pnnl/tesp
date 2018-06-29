# How to Install and Run MATPOWER with FNCS #
***************************************
_Author: **Laurentiu Dan Marinovici**_
***************************************

If MATPOWER is one of the simulators used as part of the FNCS (**F**ramework for **N**etwork **C**o-**S**imulation) environment, the following should be considered.

  - MATPOWER OPF resides as a shared object in libMATPOWER.so, after being compiled on a computer with a complete version of MATLAB intalled.
  - Running the MATPOWER functions requires that at least MATLAB Compiler Runtime (MCR) (downloaded for free from MATHWORKS webpage) is installed. Make sure the MCR is the same version as the MATLAB under which the compilation has been done.

## Launching the MATPOWER Power Flow / Optimal Power Flow solver from a C++ wrapper ##
****************************************
```start_MATPOWER.cpp```  
_Copyright (C) 2013, Battelle Memorial Institute_  
_Written by_ **Laurentiu Dan Marinovici**, Pacific Northwest National Laboratory  
_Additional updates by_ **Jacob Hansen**, Pacific Northwest National Laboratory
****************************************

Main purposes of the "wrapper", that is the code in the C++ file ```start_MATPOWER.cpp```:
  - Read the MATPOWER data file that resides in a .m file (the MATPOWER case file),
  - Create the data structure needed by the MATPOWER solvers, calls the solver (runpf or runopf), and returns the results.

Files needed for deployment (for this case, at least, in order to be able to compile):
  - ```start_MATPOWER.cpp``` - main file,
  - ```libMATPOWER.h```, ```libMATPOWER.so``` - MATPOWER compiled object for deployment under Linux,
  - ```case9.m```, or any other - MATPOWER case file, that needs to have extra data added,
  - ```matpowerintegrator.h```, ```matpowerintegrator.cpp``` - files for MATPOWER-FNCS integration.
  
Due to the fact that the wrapper file "start_MATPOWER.cpp" has been going through many updates, I have taken out the updates
list from the actual source file and present them below.

  - [x] Update: 03/05/2014  
    Purpose:
      - Implement possibility of running it with multiple instances of GridLAB-D.
  - [x] Update: 03/21/2014  
    Purpose:
      - Added the possibility to change the generation/trsnmission topology, by making on generator go off-line.
      - Branches could also be set-up to go off-line. (not implemented yet though).
  - [x] Update: 04/08/2014  
    Purpose:
      - Ability to run both the regular power flow and the optimal power flow.
      - The optimal power flow is going to be solved 5 seconds before the end of every minute, to be able to communicate the newly calculated price to GLD in time.
  - [x] Update: 05/02/2014  
    Purpose:
      - Add the ability to receive a load profile as the "static load" at the feeder buses, profile that would simulate a real-life one day load profile.  
      **WARNING:** Currently, the code is written to accomodate the model used, that is there are only 6 load buses (out of a total of 9 buses), and only 3 out of these 6 have non-zero loads, where the profile is going to be modified such that it follows a 24h real-life-like shape.
  - [x] Update: 06/17/2014  
    Purpose:
      - Took out some of the functions to separate cpp files and created ```read_input_data.h``` header that includes all the functions required to read the simulation model
  - [x] Update: 07/02/2014  
    Purpose:
      - Modified the read load profile function in ```read_load_profile.cpp```, to be able to read as many profiles as neccessary, depending on how many substations I have. Basically, the load profile data comes into a file containing 288 values per row (every 5-minute data for 24 hours), and a number of rows greater than or equal to the number of substations.
  - [x] Update: 07/23/2014  
    Purpose:
      - Added NS3_flag that allows to call the corresponding sendprice function, depending on whether NS-3 is used ot not.
      - Got rid of it on 2015/09/25, due to using FNCS2.
  - [x] Update: 10/24/2014  
    Purpose:
      - Added the incentive calculator functionality.
  - [x] Update: 03/10/2015  
    Purpose:
      - Taking out the incetive calculation, and trying to make it compatible with FNCS2.
      - Got rid of it, since project did not go on.
  - [x] Update: 04/02/2015  
    Purpose:
      - Added a third parameter as input representing the final time of the MATPOWER simulator. Once the time returned by FNCS reaches this value, MATPOWER simulator sends a nice BYE signal to let broker know it ended. It will DIE if cannot complete succesfully.
  - [x] Update: 09/09/2015  ]
    Purpose:
      - While discussing scalability issue, the idea of having multiple distribution networks (GridLAB-D instances) connected to the same node/bus of a transimission network raised the question of correctly subscribing and aggregating the loads connected to the same bus. One idea is to create a map between generic subscription names and the corresponding location where they are to be placed. A map matrix has been created in the MATPOWER model in the form, similar to:  

      Subscriber name   | Subscriber bus number
      :---------------: | :---------------------:
      SUBSTATIONCOM1    |            7           
      SUBSTATIONCOM2    |            7
      SUBSTATIONCOM3    |            5
      SUBSTATIONCOM4    |            5
      SUBSTATIONCOM5    |            5  

  - [x] Update: 02/17/2017  
    Purpose:
      - For the Transactive Energy Systems Platform (TESP) project, a set of metrics are needed. They are to be saved in a JSON structure.
      - ```jsoncpplib``` is going to be used to accomodate for saving the necessary data into a file.
  - [x] Update: 04/18/2017  
    Purpose:
      - Compliance with the **MATPOWER V6**: the MATPOWER solve options are given as a structure in version 6.
      - Though there are backwards compatibilities, the option variable is now a structure rather than a matrix of doubles.
  - [x] Update: 06/26/2017  
    **Remember**: Now, MATPOWER is to be called through FNCS at a minimum rate of 30 seconds, or whatever desired and set in the ```.zpl``` file as ```time_delta```. That ensures the power flow calculation won't be forced to recalculate for just one single distribution change on a very large scale system.  
    Purpose:
      - First stage of CCSI 2.8 complexity adding to the simulation environment to test control algorithms:
        - change to AC power flow calculation as default
        - at market cycles, DC OPF is run to get the marginal prices, and immediately after, an AC PF is run with the newly disptached generation to recalculate the bus voltages (in the out matrices for the AC PF only some entries are changed, so the price columns are not overwritten).
      - 2 functions and the corresponding variables have been added to the ```matpowerintegrator``` files and called in the wrapper, in order to be able to get the maximum dispatchable loads and the demand curve, that is
        - ```getMaxDispLoad``` - to extract the maximum dispatchable load at a bus that has dispatchable load (that is, it is listed under the generation matrix as negative generation)
        - ```getDLDemandCUrve``` - to extract the coefficients of the demand curve corresponding to the dispatchable loads inserted into the transmission MATPOWER model as negative loads; hence these coefficients need to be transformed into the coefficients of a negative supply curve.
