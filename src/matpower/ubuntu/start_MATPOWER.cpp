/*
Launching the MATPOWER Power Flow / Optimal Power Flow solver
  - MATPOWER OPF resides as a shared object in libMATPOWER.so, after being compiled on a computer with a complete version of MATLAB intalled.
  - Running the MATPOWER functions requires that at least MATLAB Compiler Runtime (MCR) (downloaded for free from MATHWORKS webpage) is installed. Make sure the MCR is the same version as the MATLAB under which the compilation has been done.
  - The code below reads the data file that resides in a .m file (the MATPOWER case file).
  - It creates the data structure needed by the MATPOWER solvers, calls the solver, and returns the results.
  - Files needed for deployment (for this case, at least, in order to be able to compile): start_MATPOWER.cpp, libMATPOWER.h, libMATPOWER.so, case9.m, matpowerintegrator.h, matpowerintegrator.cpp.
==========================================================================================
Copyright (C) 2013, Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
Update: 03/05/2014
   Purpose: Implement possibility of running it with multiple instances of GridLAB-D.
Update: 03/21/2014
   Purpose: Added the possibility to change the generation/trsnmission topology, by making on generator go off-line.
            Branches could also be set-up to go off-line. (not implemented yet though).
Update: 04/08/2014
   Purpose: Ability to run both the regular power flow and the optimal power flow.
            The optimal power flow is going to be solved 5 seconds before the end of every minute,
            to be able to communicate the newly calculated price to GLD in time.
Update: 05/02/2014
   Purpose: Add the ability to receive a load profile as the "static load" at the feeder buses, profile that would simulate a real-life one day load profile
   WARNING: Currently, the code is written to accomodate the model used, that is there are only 6 load buses (out of a total of 9 buses), and only 3 out of these 6
            have non-zero loads, where the profile is going to be modified such that it follows a 24h real-life-like shape.
Update: 06/17/2014
   Purpose: Took out some of the functions to separate cpp files and created read_input_data.h header that includes all the functions required to read the simulation model
Update: 07/02/2014
   Purpose: Modified the read load profile function in read_load_profile.cpp, to be able to read as many profiles as neccessary, depending on how many substations I have.
            Basically, the load profile data comes into a file containing 288 values per row (every 5-minute data for 24 hours), and a number of rows greater than or equal to the number of substations.
Update: 07/23/2014
   Purpose: Added NS3_flag that allows to call the corresponding sendprice function, depending on whether NS-3 is used ot not
            Got rid of it on 2015/09/25, due to using FNCS2
Update: 10/24/2014
   Purpose: Added the incentive calculator functionality
Update: 03/10/2015
   Purpose: Taking out the incetive calculation, and trying to make it compatible with FNCS2
            Getting rid of it
Update: 04/02/2015
   Purpose: Added a third parameter as input representing the final time of the MATPOWER simulator. Once the time returned by FNCS reaches this value, MATPOWER simulator sends a nice BYE
            signal to let broker know it ended. It will DIE if cannot complete succesfully.
Update: 09/09/2015
   Purpose: While discussing scalability issue, the idea of having multiple distribution networks (GridLAB-D instances) connected to the same node/bus of a transimission network raised
            the question of correctly subscribe and aggregate the loads connected to the same bus. One idea is to create a map between generic subscription names and the corresponding
            location where they are to be placed. A map matrix has been created in the MATPOWER model in the form, i.e.
            Subscriber name | Subscriber bus number
            ===============   =====================
            SUBSTATIONCOM1              7           
            SUBSTATIONCOM2              7
            SUBSTATIONCOM3              5
            SUBSTATIONCOM4              5
            SUBSTATIONCOM5              5          
Update: 02/17/2017
    Purpose: For the Transactive Energy Systems Platform (TESP) project, a set of metrics are needed. They are to be saved in a JSON structure.
             jsoncpplib is going to be used to accomodate for saving the necessary data into a file.           
==========================================================================================
*/
#include <stdio.h>
#include <math.h>
// #include <windows.h>
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <sstream>
#include <string.h>
using namespace std;
//using namespace fncs;
// #include <shellapi.h>
#include "libMATPOWER.h"
#include "mclmcrrt.h"
#include "mclcppclass.h"
#include "matrix.h"
#include "fncs.hpp"

# define PI 3.14159265

#include "matpowerintegrator.h"
#include "read_input_data.h"

#include "matpowerLoadMetrics.h"
#include "matpowerGeneratorMetrics.h"

// Transposing matrices; we need this function becuase the way the file reading is done leads to the transpose of the necessary matrix
// Careful: it is 1-base indexing because we are working with MATLAB type array mwArray
mwArray mwArrayTranspose(int nrows, int ncolumns, mwArray matrix_in) {
   mwArray matrix_out(nrows, ncolumns, mxDOUBLE_CLASS);
   for (int ind_row = 1; ind_row <= nrows; ind_row++) {
   for (int ind_col = 1; ind_col <= ncolumns; ind_col++) {
      matrix_out(ind_row, ind_col) = matrix_in(ind_col, ind_row); } }
   return matrix_out; }


int run_main(int argc, char **argv) {
   if (!mclInitializeApplication(NULL, 0)) {
      cerr << "Could not initialize the application properly !!!" << endl;
      return -1;
      }
   if (!libMATPOWERInitialize()) {
      cerr << "Could not initialize one or more MATLAB/MATPOWER libraries properly !!!" << endl;
      return -1;
      }
   else {
      try {
// ================================ VARIABLE DECLARATION AND INITIALIZATION =============================================
         cout << "Just entered the MAIN function of the driver application." << endl;
         // Initialize the input parameters giving the MATPOWER model file, the load profile, and simulation stop time in seconds
         char *file_name; // {"case9.m"};
         file_name = argv[1];
         // char load_profile_file[] = {"real_power_demand.txt"};
         char *load_profile_file;
         load_profile_file = argv[2];
         double simStopTime;
         sscanf(argv[3], "%lf%*s", &simStopTime);
         string startTime;
         startTime = argv[4];
         cout << "Running MATPOWER ends after " << simStopTime << " seconds, supposing it starts on " << startTime << "." << endl;
// ================================ METRICS FOR TRANSACTIVE ENERGY VALUATION ============================================
// ================================ LOAD BUS METRICS ====================================================================
         const char *loadMetricsFile;
         loadMetricsFile = argv[5];
         ofstream loadMetricsOutput(loadMetricsFile, ofstream::out);
         loadBusMetrics mpLoadMetrics;
         loadMetadata mpLoadMetadata;
         loadBusValues mpLoadBusValues;
         mpLoadMetrics.setMetadata(mpLoadMetadata);
         mpLoadMetrics.setName(file_name);
         mpLoadMetrics.setStartTime(startTime);
// ================================ GENERATOR BUS METRICS ================================================================
         const char *generatorMetricsFile;
         generatorMetricsFile = argv[6];
         ofstream generatorMetricsOutput(generatorMetricsFile, ofstream::out);
         generatorBusMetrics mpGeneratorMetrics;
         generatorMetadata mpGeneratorMetadata;
         generatorBusValues mpGeneratorBusValues;
         mpGeneratorMetrics.setMetadata(mpGeneratorMetadata);
         mpGeneratorMetrics.setName(file_name);
         mpGeneratorMetrics.setStartTime(startTime);
         
// ======================================================================================================================
         // Read the MATPOWER transmission model file in order to get the suze of the system, that is number of busses, generators, etc.
         // These dimensions are needed to be able to create the model matrices later without dynamic allocation of memory.
         // Declaration of dimension variables.
         int nbrows = 0, nbcolumns = 0, ngrows = 0, ngcolumns = 0;
         int nbrrows = 0, nbrcolumns = 0, narows = 0, nacolumns = 0;
         int ncrows = 0, nccolumns = 0, nFNCSbuses = 0, nFNCSsubst = 0, noffgelem = 0;

         read_model_dim(file_name, &nbrows, &nbcolumns, &ngrows, &ngcolumns,
              &nbrrows, &nbrcolumns, &narows, &nacolumns,
              &ncrows, &nccolumns, &nFNCSbuses, &nFNCSsubst, &noffgelem);
         /*
         cout << nbrows << '\t' << nbcolumns << '\t' << ngrows << '\t' << ngcolumns << '\t' << endl;
         cout << nbrrows << '\t' << nbrcolumns << '\t' << narows << '\t' << nacolumns << endl;
         cout << ncrows << '\t' << nccolumns << '\t' << nFNCSSub << '\t' << noffGen << endl;
         */
// ========================================================================================================================
         // Load profile for the "static" load at all the buses.
         // The number of profiles should be at least equal to the number of feeders nFNCSbuses, which is given in the MATPOWER case file. Careful, though!!!
         // Each profile needs to start from the value that exists initially in the MATPOWER model at the specific bus.
         // Each profile consists of data for 24 hours every 5 minutes (288 values taken repeatedly every day)
         double real_power_demand[nFNCSbuses][288], reactive_power_demand[nFNCSbuses][288];
         for (int i = 0; i < sizeof(real_power_demand)/sizeof(real_power_demand[0]); i++) {
            for (int j = 0; j < sizeof(real_power_demand[0])/sizeof(real_power_demand[0][0]); j++) {
               real_power_demand[i][j] = 0;
               reactive_power_demand[i][j] = 0;
            }
         }
         // Get load profile data, to make the load evolution in time more realistic
         read_load_profile(load_profile_file, real_power_demand, nFNCSbuses);
         // Printing out the values just for the sake of testing. Uncomment the portion below if need be.
         /*
         for (int i = 0; i < sizeof(real_power_demand)/sizeof(real_power_demand[0]); i++){
            for (int j = 0; j < sizeof(real_power_demand[0])/sizeof(real_power_demand[0][0]); j++){
               cout << real_power_demand[i][j] << " ";
            }
            cout << endl;
         }
         */
// ========================================================================================================================
         // Rest of the variables declaration
         double baseMVA, nomfreq;
         double amp_fact; // amplification factor for the controlable load.
         // The powerflow solution is going to be calculated in the following variables
         mwArray mwMVAbase, mwBusOut, mwGenOut, mwBranchOut, f, success, info, et, g, jac, xr, pimul, mwGenCost;
         // Results from RUNPF or RUNOPF will be saved as in MATLAB in a mat file, and printed in a nice form in a file
         mwArray printed_results(mwArray("printed_results.txt"));
         mwArray saved_results(mwArray("saved_results.mat"));
//         double mwBusOut_copy[9];
         int repeat = 1;
         // matrix dimensions based on test case; they need to be revised if other case is used
         // for C code we need the total number of elements, while the matrices will be passed to MATLAB as mwArray with rows and columns
         // BUS DATA MATRIX DEFINITION
         // bus matrix dimensions, and total number of elements
         // int nbrows = 9, nbcolumns = 13, nbelem = nbrows * nbcolumns;
         int nbelem = nbrows * nbcolumns;
         double bus[nbelem];
         mwArray mwBusT(nbcolumns, nbrows, mxDOUBLE_CLASS); // given the way we read the file, we initially get the transpose of the matrix
         mwArray mwBus(nbrows, nbcolumns, mxDOUBLE_CLASS);
         // GENERATOR DATA MATRIX DEFINITION
         // generator matrix dimensions, and total number of elements
         // int ngrows = 3, ngcolumns = 21, ngelem = ngrows * ngcolumns;
         int ngelem = ngrows * ngcolumns;
         double gen[ngelem];
         mwArray mwGenT(ngcolumns, ngrows, mxDOUBLE_CLASS);
         mwArray mwGen(ngrows, ngcolumns, mxDOUBLE_CLASS);
         // BRANCH DATA MATRIX DEFINITION
         // branch matrix dimensions, and total number of elements
         // int nbrrows = 9, nbrcolumns = 13, nbrelem = nbrrows * nbrcolumns;
         int nbrelem = nbrrows * nbrcolumns;
         double branch[nbrelem];
         mwArray mwBranchT(nbrcolumns, nbrrows, mxDOUBLE_CLASS);
         mwArray mwBranch(nbrrows, nbrcolumns, mxDOUBLE_CLASS);
         // AREA DATA MATRIX DEFINITION
         // area matrix dimensions, and total number of elements
         // int narows = 1, nacolumns = 2, naelem = narows * nacolumns;
         int naelem = narows * nacolumns;
         double area[naelem];
         mwArray mwAreaT(nacolumns, narows, mxDOUBLE_CLASS);
         mwArray mwArea(narows, nacolumns, mxDOUBLE_CLASS);
         // GENERATOR COST DATA MATRIX DEFINTION
         // generator cost matrix dimensions, and total number of elements
         // int ncrows = 3, nccolumns = 7, ncelem = ncrows * nccolumns;
         int ncelem = ncrows * nccolumns;
         double costs[ncelem];
         mwArray mwCostsT(nccolumns, ncrows, mxDOUBLE_CLASS);
         mwArray mwCosts(ncrows, nccolumns, mxDOUBLE_CLASS);
         // BUS NUMBERS where the distribution networks are going to be connected
         int bus_num[nFNCSbuses];
         // SUBSTATION NAMES AND BUS NUMBERS FOR FNCS COMMUNICATION
         // the substation names and the value of the bus where the substations are connected to, and the corresponding real and imaginary power
         int sub_bus[nFNCSsubst];
         double sub_valueReal[nFNCSsubst], sub_valueIm[nFNCSsubst];
         // substation names
         char sub_name[nFNCSsubst][15];
         // static active and reactive power at the buses that are connected to substations
         double fixed_pd[nFNCSbuses], fixed_qd[nFNCSbuses];
         // calculated real and imaginary voltage at the buses that are connected to substations
         double sendValReal[nFNCSbuses], sendValIm[nFNCSbuses];
         // calculated LMP values at the buses that are connected to substations
         double realLMP[nFNCSbuses], imagLMP[nFNCSbuses];
         for (int i = 0; i < nFNCSbuses; i++) {
            realLMP[i] = 0;
            imagLMP[i] = 0;
         }
         // bus index in the MATPOWER bus matrix corresponding to the buses connected to substations
         int modified_bus_ind[nFNCSbuses];
         int mesgc[nFNCSsubst]; // synchronization only happens when at least one value is received
         bool mesg_rcv = false; // if at least one message is passed between simulators, set the message received flag to TRUE
         bool mesg_snt = false; // MATPOWER is now active, it will send a message that major changes happened at transmission level
         bool solved_opf = false; // activates only when OPF is solved to be able to control when price is sent to GLD
         bool topology_changed = false; // activates only if topology changed, like if a generator is turned off form on, or vice-versa, for example.
         // Generator bus matrix consisting of bus numbers corresponding to the generators that could become out-of service,
         // allowing us to set which generators get off-line, in order to simulate a reduction in generation capacity.
         // MATPOWER should reallocate different generation needs coming from the on-line generators to cover for the lost ones, since load stays constant
         // for MATPOWER: value >  0 means generator is in-service
         //                     <= 0 means generator is out-of-service
         // number of rows and columns in the MATPOWER structure, and the total number of buses
         // int noffgrows = 1, noffgcolumns = 1, noffgelem = noffgrows*noffgcolumns;
         int offline_gen_bus[noffgelem], offline_gen_ind[noffgelem];
         // times recorded for visualization purposes
         int curr_time = 0; // current time in seconds
         int curr_hours = 0, curr_minutes = 0, curr_seconds = 0; // current time in hours, minutes, seconds
         int delta_t[nFNCSsubst], prev_time[nFNCSsubst]; // for each substation we save the time between 2 consecutive received messages
         for (int i = 0; i < nFNCSsubst; i++) {
            delta_t[i] = 0;
            prev_time[i] = 0;
         }
         // For FNCS2 integration
         // Subscription - the lookup key is given by the substation name that is read from the model
         string actPowerUnit; // unit for active power
         string reactPowerUnit; // unit for reactive power
         // Publishing
         string pubVoltage[nFNCSbuses]; // topics under which MATPOWER publishes voltages
         string pubPrice[nFNCSbuses]; // topics under which MATPOWER publishes prices/LMPs
         // Temporary strings needed to transform ints or floats into a corresponding string for messages
         // tempBNumStr = string containing the bus number
         // tempLMPStr = string containing the LMP in $/MW
         stringstream tempBNumStr, tempLMPStr;

// ========================================================================================================================
         double *p_temp,*q_temp;
         int *pq_length,*receive_flag;
         // Creating the MPC structure that is going to be used as input for OPF function
         const char *fields[] = {"baseMVA", "bus", "gen", "branch", "areas", "gencost"}; 
         mwArray mpc(1, 1, 6, fields);
     
         // Creating the variable that would set the options for the OPF solver
         mwArray mpopt(124, 1, mxDOUBLE_CLASS); // there are 124 options that can be set
         mwArray mpoptNames(124, 18, mxCHAR_CLASS); // there are 124 option names and the maximum length is 18, but made it to 20
         cout << "=================================================" << endl;
         cout << "========= SETTING UP THE OPTIONS !!!!!===========" << endl;
         cout << "Setting initial options........" << endl;
         mpoption(2, mpopt, mpoptNames); // initialize powerflow options to DEFAULT ones
         cout << "Finished setting the initial options." << endl;
         // cout << "mpopt = " << mpopt << endl;
         // cout << "mpoptNames = " << mpoptNames << endl;
         mwArray optIn(1, 3, mxCELL_CLASS); // this holds the initial option vector, the property name that will be set up, and the new value for that property
         optIn.Get(1, 1).Set(mpopt);
         optIn.Get(1, 2).Set(mwArray("PF_DC")); // name of the option that could be modified, e.g. PF_DC
         optIn.Get(1, 3).Set(mwArray(1)); // value of the modified option, e.g. 0 or 1 for false or true
         mpoption(2, mpopt, mpoptNames, optIn); //, optionName, optionValue); // Setting up the DC Power Flow
         optIn.Get(1, 1).Set(mpopt); // Update the option vector to the one with one property changed. Problem is, we have to do this avery time we change one option.
         optIn.Get(1, 2).Set(mwArray("VERBOSE"));
         optIn.Get(1, 3).Set(mwArray(0)); // Setting the VERBOSE mode OFF, so we do not see all the steps on the terminal
         mpoption(2, mpopt, mpoptNames, optIn); //, optionName, optionValue);
         optIn.Get(1, 1).Set(mpopt); // Update the option vector to the one with one property changed. Problem is, we have to do this avery time we change one option.
         optIn.Get(1, 2).Set(mwArray("OUT_ALL"));
         optIn.Get(1, 3).Set(mwArray(0)); // Setting the OUT_APP mode OFF, so we do not see all the results printed at the terminal
         mpoption(2, mpopt, mpoptNames, optIn); //, optionName, optionValue);
         optIn.Get(1, 1).Set(mpopt); // Update the option vector to the one with one property changed. Problem is, we have to do this avery time we change one option.
// ================================ END OF VARIABLE DECLARATION AND INITIALIZATION =============================================
// =============================================================================================================================
         // get the MATPOWER model data
         read_model_data(file_name, nbrows, nbcolumns, ngrows, ngcolumns, nbrrows, nbrcolumns, narows, nacolumns,
                  ncrows, nccolumns, nFNCSbuses, nFNCSsubst, noffgelem, &baseMVA, bus, gen,
                  branch, area, costs, bus_num, sub_name, sub_bus, offline_gen_bus, &amp_fact);
         // output files for saving results
         // 2015-03-17 Turned off the file generation.
         
         char subst_output_file_name[nFNCSbuses][18]; // one file for each substation
         // char dem_curve_file_name[nFNCSsubst][25]; // names for files to save the forecast demand curves in
         char gen_output_file_name[noffgelem][17]; // one file for each generator that is turned off; for larger models we were getting too many files
         ofstream subst_output_file, gen_output_file; // , dem_curve_file; // output file streams
         for (int i = 0; i < sizeof(subst_output_file_name)/sizeof(subst_output_file_name[0]); i++) {
            snprintf(subst_output_file_name[i], sizeof(subst_output_file_name[i]), "Bus_%d.csv", bus_num[i]); // Bus_#.csv
            ofstream subst_output_file(subst_output_file_name[i], ios::out);
            subst_output_file << "Time (seconds), Real Power Demand - PD (MW), Reactive Power Demand (MVAr), Substation V real (V), Substation V imag (V), LMP ($/kWh), LMP ($/kVArh)" << endl;
            // snprintf(dem_curve_file_name[i], sizeof(dem_curve_file_name[i]), "dem_curve_subst_%d.csv", bus_num[i]);
            // ofstream dem_curve_file(dem_curve_file_name[i], ios::out);
         }
         
         
         // Turning off the Generator file creation for a while. Uncomment the lines below to have them created again.
         for (int i = 0; i < sizeof(gen_output_file_name)/sizeof(gen_output_file_name[0]); i++) {
            snprintf(gen_output_file_name[i], sizeof(gen_output_file_name[i]), "Generator_%d.csv", offline_gen_bus[i]); // Generator_BUS#.csv
            ofstream gen_output_file(gen_output_file_name[i], ios::out);
            gen_output_file << "Time (seconds), STATUS, PMAX (MW), PMIN (MW), Real power output - PG (MW), QMAX (MVAr), QMIN (MVAr), Reactive power output - QG (MVAr)" << endl;
         }
         
         mwBusT.SetData(bus, nbelem);
         // Transposing mwBusT to get the correct bus matrix
         // Careful: it is 1-base indexing because we are working with MATLAB type array mwArray
         mwBus = mwArrayTranspose(nbrows, nbcolumns, mwBusT);
         mwArray mwBusDim = mwBus.GetDimensions();
         
         mwGenT.SetData(gen, ngelem);
         mwGen = mwArrayTranspose(ngrows, ngcolumns, mwGenT);
         
         mwBranchT.SetData(branch, nbrelem);
         mwBranch = mwArrayTranspose(nbrrows, nbrcolumns, mwBranchT);
         
         mwAreaT.SetData(area, naelem);
         mwArea = mwArrayTranspose(narows, nacolumns, mwAreaT);
         
         mwCostsT.SetData(costs, ncelem);
         mwCosts = mwArrayTranspose(ncrows, nccolumns, mwCostsT);
         
         // Uncomment the part below, if need for inspecting results
         /*
         cout << "==================================" << endl;
         cout << "mpc.BusFNCS = ";
         for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++){
            cout << "\t" << bus_num[bus_ind];
         }
         cout << endl;
         cout << "==================================" << endl;
         */
         // Uncomment the part below, if need for inspecting results
         /*
         cout << "===========solvedcase=======================" << endl;
         cout << "mpc.SubNameFNCS = " << endl;
         for (int sub_ind = 0; sub_ind < sizeof(sub_bus)/sizeof(sub_bus[0]); sub_ind++){
            cout << "\t" << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind] << endl;
         }
         cout << endl;
         cout << "==================================" << endl;
         */
         // Uncomment the part below, if need for inspecting results
         /*
         cout << "==================================" << endl;
         cout << "mpc.offlineGenBus = ";
         for (int off_ind = 0; off_ind < sizeof(offline_gen_bus)/sizeof(offline_gen_bus[0]); off_ind++){
            cout << "\t" << offline_gen_bus[off_ind];
         }
         cout << endl;
         cout << "==================================" << endl;
         */
         // Uncomment the part below, if need for inspecting results
         /*
         cout << "==================================" << endl;
         cout << "mpc.ampFactor = " << amp_fact << endl;
         cout << "==================================" << endl;
         */

         // Initialize the MPC structure with the data read from the file
         mpc.Get("baseMVA", 1, 1).Set((mwArray) baseMVA);
         mpc.Get("bus", 1, 1).Set(mwBus);
         mpc.Get("gen", 1, 1).Set(mwGen);
         mpc.Get("branch", 1, 1).Set(mwBranch);
         mpc.Get("areas", 1, 1).Set(mwArea);
         mpc.Get("gencost", 1, 1).Set(mwCosts);
         // Uncomment the part below, if need for inspecting results
         /*      
         cout << "=========================================" << endl;
         cout << "===== Initial MPC structure created =====\n" << mpc << endl;
         cout << "=========================================" << endl;
         */
      	  
         // =====================================================================================================================
         // Setting the published topics - for each bus in the transmission network where distribution networks are connected to, we publish
         // voltage and LMP
         for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++) {
            // Temporary stream to help transforming ints into strings
            tempBNumStr.str(string()); // clearing the previous value from the temporary stream
            tempBNumStr << bus_num[bus_ind]; // copying the number into the temporary stream
         	  pubVoltage[bus_ind] = "three_phase_voltage_B" + tempBNumStr.str(); // bus voltage: it will have a complex number as value and V as unit
         	  pubPrice[bus_ind] = "LMP_B" + tempBNumStr.str(); // LMP at the bus
            // The index of the bus in the bus matrix could be different from the number of the bus
            // because buses do not have to be numbered consecutively, or be the same as the index
            for (int ind = 1; ind <= nbrows; ind++) {
               // ind is an index in MATLAB, that is it should start at 1
               // In mpc.Get("bus", 1, 1).Get(2, ind, 1), the 2 in the second Get represents the number of indeces the array has
               if ((int) mpc.Get("bus", 1, 1).Get(2, ind, 1) == bus_num[bus_ind]) {
                  modified_bus_ind[bus_ind] = ind;
                  fixed_pd[bus_ind] = mpc.Get("bus", 1, 1).Get(2, ind, 3);
                  fixed_qd[bus_ind] = mpc.Get("bus", 1, 1).Get(2, ind, 4);
                  cout << "Initially, the static ACTIVE power at bus " << bus_num[bus_ind] << " is " << fixed_pd[bus_ind] << "." << endl;
                  cout << "Initially, the static REACTIVE power at bus " << bus_num[bus_ind] << " is " << fixed_qd[bus_ind] << "." << endl;
               }
            }
         }

         // Find the index in the MATPOWER generator matrix corresponding to the buses with generators that could be turned off
         // The bus number and the actual index in the MATPOWER matrix may not coincide

         for (int off_ind = 0; off_ind < sizeof(offline_gen_bus)/sizeof(offline_gen_bus[0]); off_ind++){
            for (int gen_ind = 1; gen_ind <= ngrows; gen_ind++){ // in MATLAB indexes start from 1
               if((int) mpc.Get("gen", 1, 1).Get(2, gen_ind, 1) == offline_gen_bus[off_ind]){
                  offline_gen_ind[off_ind] = gen_ind; // index of the bus in the MATPOWER matrix
                  cout << "GENERATOR AT BUS " << mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 1) << " MIGHT BECOME OFF-LINE!!!!" << endl;
               }
            }
         }

          // ==========================================================================================================
          // Uncomment the line below when running with FNCS
          // initn(bus_num, &nFNCSbuses); // initialize the bus number for FNCS
          fncs::initialize();
          // ==========================================================================================================
         
          do {
            // Start every time assuming no message is received or sent
            mesg_rcv = false;
            mesg_snt = false;
            solved_opf = false;
            topology_changed = false;
            // ==========================================================================================================
            // Uncomment the line below when running with FNCS
            // startcalculation();
            // ==========================================================================================================
            // =============== CURRENT SIMULATION TIME ==================================================================
            // Uncomment the line below when running with FNCS
            curr_time = getCurrentTime();
            // ==========================================================================================================
            curr_hours = curr_time/3600;
            curr_minutes = (curr_time - 3600*curr_hours)/60;
            curr_seconds = curr_time - 3600*curr_hours - 60*curr_minutes;
			
            // Setting the load at the load buses based on the load profiles
            // In this case, the model has 6 load buses, out of which only 3 had non-zero values originally; so we stick to only those 
            // getting in a one-day long profile. WARNING: if the model is changed these need to be readjusted
            
            // if (curr_time % 300 == 0) { // DON NOT HAVE TO CHECK THIS, NOW THAT I'VE CHANGED THE SYNC FUNCTION
            /*
            cout << "\033[2J\033[1;1H"; // Just a trick to clear the screen before printing the new results at the terminal
            cout << "================== It has been " << curr_hours << " hours, " << curr_minutes << " minutes, and ";
            cout << curr_seconds << " seconds. ========================" << endl;
            cout << "index -->> " << 12 * (curr_hours % 24) + curr_minutes / 5 << endl;
            */
            for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++) {
               // Normally the load would be kept constant within the 5 min interval, as the load profile says. But, if GridLAB-D changes the load value, we do not want to change that back to the  profile value. That is why I have commented out the following line. Should probably take it out, but keeping it in here as a reminder.
               fixed_pd[bus_ind] = real_power_demand[bus_ind][12 * (curr_hours % 24) + curr_minutes / 5];
               for (int row_ind = 1; row_ind <= nbrows; row_ind++) {
                  if ((int) mpc.Get("bus", 1, 1).Get(2, row_ind, 1) == bus_num[bus_ind]) {
                     mpc.Get("bus", 1, 1).Get(2, row_ind, 3).Set((mwArray) fixed_pd[bus_ind]);
                     mpc.Get("bus", 1, 1).Get(2, row_ind, 4).Set((mwArray) fixed_qd[bus_ind]);
                     cout << "fixed active -->> " << fixed_pd[bus_ind] << "(" << mpc.Get("bus", 1, 1).Get(2, row_ind, 3) << ") at bus " << bus_num[bus_ind] << " (" << mpc.Get("bus", 1, 1).Get(2, row_ind, 1) << ")" << endl;
                     cout << "fixed reactive -->> " << fixed_qd[bus_ind] << "(" << mpc.Get("bus", 1, 1).Get(2, row_ind, 4) << ") at bus " << bus_num[bus_ind] << " (" << mpc.Get("bus", 1, 1).Get(2, row_ind, 1) << ")" << endl;
                  }
               } // end of FOR to scan the BUS matrix to find the right location of the currently processed bus
               // mpc.Get("bus", 1, 1).Get(2, modified_bus_ind[sub_ind], 4).Set((mwArray) reactive_power_demand[curr_hours % 24 + curr_minutes / 5][sub_ind]);
               // fixed_qd[sub_ind] = reactive_power_demand[curr_hours % 24 + curr_minutes / 5][sub_ind];
            } // end of FOR to scan the buses where distribution networks are connected to
            // }
            // Setting up the status of the generators, based on the current time
            // Turning some generators out-of-service between certain time preiods in the simulation 
            // every day between 6 and 7 or 18 and 19 !!! WARNING !!! These hours are hard coded assuming we run more than 24 hours
            if ((curr_hours % 24 >= 6 && curr_hours % 24 < 7) || (curr_hours % 24 >= 18 && curr_hours % 24 < 19)){ 
               for (int off_ind = 0; off_ind < sizeof(offline_gen_ind)/sizeof(offline_gen_ind[0]); off_ind++){
                  if ((double) mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8) == 1){ // if generator is ON
                     mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8).Set((mwArray) 0); // turn generator OFF, and set flag that topology has changed
                     topology_changed = topology_changed || true; // signal that at least one generator changed its state
//                     mesg_snt = mesg_snt || true; // signal that at least one generator changed its state
                     // Uncomment after testing the load profile loading correctly
                     cout << "============ Generator at bus " << mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 1);
                     cout << " is put OUT-OF-SERVICE. ==================" << endl;
                  }
               }
            }
            else {
               for (int off_ind = 0; off_ind < sizeof(offline_gen_ind)/sizeof(offline_gen_ind[0]); off_ind++){
                  if ((double) mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8) == 0){ // if generator is OFF
                     mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8).Set((mwArray) 1); // turn generator ON, and set flag that topology changed
                     topology_changed = topology_changed || true;// signal that at least one generator changed its state
//                     mesg_snt = mesg_snt || true; // signal that at least one generator changed its state
                     // Uncomment after testing the load profile loading correctly
                     cout << "============ Generator at bus " << mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 1);
                     cout << " is brought back IN-SERVICE. ==================" << endl;
                  }
               }
            }
            for (int sub_ind = 0; sub_ind < sizeof(sub_bus)/sizeof(sub_bus[0]); sub_ind++) {
               // ==========================================================================================================
               // Uncomment the line below when running with FNCS
               // cout << "==== BEFORE getpower ===== " << mesgc[sub_ind] << " VS " << (bool) mesgc[sub_ind];
               // cout << "==== for substation " << sub_name[sub_ind] << " at bus " << bus_num[sub_ind] << " ====" << endl;
               // cout << "==== BEFORE getpower ===== " << mesg_rcv << "==== for substation " << sub_name[sub_ind] << " at bus " << bus_num[sub_ind] << " ====" << endl;
               getpower(sub_name[sub_ind], &mesgc[sub_ind], &sub_valueReal[sub_ind], &sub_valueIm[sub_ind], actPowerUnit, reactPowerUnit);
               // ==========================================================================================================
               // Uncomment the line below when working off-line from FNCS
               // cout << "Simulate whether " << sub_name[sub_ind] << " received message or not. Enter 0 for NO, and 1 for YES." << endl;
               // cout << "YES [1] or NO [0]?\t";
               // cin >> mesgc[sub_ind];
               mesg_rcv =  mesg_rcv || (bool) mesgc[sub_ind];
               if (mesgc[sub_ind] == 1) { // if one substation publishes a change in load, then update the value in the BUS matrix for the transmission network power flow solver
                  delta_t[sub_ind] = curr_time - prev_time[sub_ind]; // number of seconds between 2 consecutive received messages
                  // It is assumed that the load at the bus consists of the non-controllable load from the predefined profiles plus a controllable load coming from distribution (GridLAB-D)
                  // To simulate the idea of having a more substantial change in load at the substantion level, consider we have amp_fact similar models at on node
                  // That is why I multiply by amp_fact below.
                  for (int row_ind = 1; row_ind <= nbrows; row_ind++) { // find the right location in the BUS matrix corresponding to the bus where the SUBSTATION that published a new value is
                     // row_ind is an index in a MATLAB matrix, and that is why it starts at 1
                     // In mpc.Get("bus", 1, 1).Get(2, ind, 1), the 2 in the second Get represents the number of dimensions the array has
                     if ((int) mpc.Get("bus", 1, 1).Get(2, row_ind, 1) == sub_bus[sub_ind]) {
                        mpc.Get("bus", 1, 1).Get(2, row_ind, 3).Set((mwArray) ((double) mpc.Get("bus", 1, 1).Get(2, row_ind, 3) + amp_fact*sub_valueReal[sub_ind]));
                        mpc.Get("bus", 1, 1).Get(2, row_ind, 4).Set((mwArray) ((double) mpc.Get("bus", 1, 1).Get(2, row_ind, 4) + amp_fact*sub_valueIm[sub_ind]));
                     }
                  } // end of FOR(row_ind) to locate the correct location in BUS matrix based on the bus number where SUBSTATION is connected to
               } // end IF(mesgc)
            } // end FOR(sub_ind)

            if (mesg_rcv){ // If at least one distribution network publishes
               // ==========================================================================================================
               // Uncomment after testing the load profile loading correctly
               // cout << "\033[2J\033[1;1H"; // Just a trick to clear the screen before pritning the new results at the terminal
               cout << "================== It has been " << curr_hours << " hours, " << curr_minutes << " minutes, and ";
               cout << curr_seconds << " seconds. ========================" << endl;
               cout << "====== New published values from the distribution networks exist. ==================" << endl;
               for (int sub_ind = 0; sub_ind < sizeof(sub_bus)/sizeof(sub_bus[0]); sub_ind++) {
                  if (mesgc[sub_ind] == 1) {
                     // Uncomment after testing the load profile loading correctly
                     cout << "====== New ACTIVE power from GRIDLab-D AT " << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind] << " is " << sub_valueReal[sub_ind] << " " << actPowerUnit << " ======" << endl;
                     cout << "====== New REACTIVE power from GRIDLab-D AT " << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind] << " is " << sub_valueIm[sub_ind] << " " << reactPowerUnit << " ======" << endl;
                     cout << "I've got the NEW POWER after " << delta_t[sub_ind] << " seconds." << endl;
                     prev_time[sub_ind] = curr_time;
                  }
                  else {
                     // Uncomment after testing the load profile loading correctly
                     cout << "===== NO LOAD CHANGE AT " << sub_name[sub_ind] << " AT BUS " << sub_bus[sub_ind] << " =====================" << endl;
                  } // end IF(mesgc)
               } // end FOR(sub_ind)
               for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++) { // only for printing/debugging purposes
                  for (int ind = 1; ind <= nbrows; ind++) {
                     if ((int) mpc.Get("bus", 1, 1).Get(2, ind, 1) == bus_num[bus_ind]) {
                        cout << "Total ACTIVE power required at bus: " << bus_num[bus_ind] << " is " << mpc.Get("bus", 1, 1).Get(2, ind, 3) << " MW." << endl;
                        cout << "Total REACTIVE power required at bus: " << bus_num[bus_ind] << " is " << mpc.Get("bus", 1, 1).Get(2, ind, 4) << " MVAR." << endl;
                     }
                  }
               } // end FOR(bus_ind)
            } // end IF(mesg_rcv)
            
            // Running the actual transmission simulator, by solving the power flow, or the optimal power flow
            if (curr_time % 300 == 295 || topology_changed){
               // Call OPF with nargout = 0 (first argument), and all results are going to be printed at the console
               // Call OPF with nargout = 7, and get all the output parameters up to et
               // Call OPF with nargout = 11, and get a freaking ERROR.... AVOID IT!
               // cout << "================= Solving the OPTIMAL POWER FLOW. ==================" << endl;
               runopf(7, mwMVAbase, mwBusOut, mwGenOut, mwGenCost, mwBranchOut, f, success, et, mpc, mpopt, printed_results, saved_results);
               mpc.Get("gen", 1, 1).Set(mwGenOut);
               mpc.Get("bus", 1, 1).Set(mwBusOut);
               mpc.Get("branch", 1, 1).Set(mwBranchOut);
               mpc.Get("gencost", 1, 1).Set(mwGenCost);
               solved_opf = true;
               mesg_snt = mesg_snt || true;
               // ============ GENERATOR METRICS ======================
               for (int genInd = 1; genInd <= ngrows; genInd++) { // indexing in a MATLAB matrix structure
                 mpGeneratorBusValues.clearBusValues();
                 mpGeneratorBusValues.setBusID((int) mwGenOut.Get(2, genInd, 1));
                 mpGeneratorBusValues.setBusPG((double) mwGenOut.Get(2, genInd, 2));
                 mpGeneratorBusValues.setBusQG((double) mwGenOut.Get(2, genInd, 3));
                 mpGeneratorBusValues.setBusStatus((double) mwGenOut.Get(2, genInd, 8));
                 for (int busInd = 1; busInd <= nbrows; busInd++) {
                   if ((int) mwGenOut.Get(2, genInd, 1) == (int) mwBusOut.Get(2, busInd, 1)) {
                     mpGeneratorBusValues.setBusLAMP((double) mwBusOut.Get(2, busInd, 14));
                     mpGeneratorBusValues.setBusLAMQ((double) mwBusOut.Get(2, busInd, 15));
                   }
                 }
                 mpGeneratorMetrics.setBusValues(mpGeneratorBusValues);
               }
            }            
            else {
               // cout << "================= Solving the POWER FLOW. ==================" << endl;
               runpf(6, mwMVAbase, mwBusOut, mwGenOut, mwBranchOut, success, et, mpc, mpopt, printed_results, saved_results);
               // Bring system in the new state by replacing the bus, generator, branch and generator cost matrices with the calculated ones
               mpc.Get("gen", 1, 1).Set(mwGenOut);
               mpc.Get("bus", 1, 1).Set(mwBusOut);
               mpc.Get("branch", 1, 1).Set(mwBranchOut);
            }

            if (mesg_rcv || mesg_snt) {
               if (mesg_snt) { // only cleaning the screen when MATPOWER initiates the message transfer; otherwise is cleaned when message is received
                  // Uncomment after testing the load profile loading correctly
                  // cout << "\033[2J\033[1;1H"; // Just a trick to clear the screen before pritning the new results at the terminal
                  if (curr_time % 300 == 295 && !topology_changed) {
                     cout << "================== It has been " << curr_hours << " hours, " << curr_minutes << " minutes, and ";
                     cout << curr_seconds << " seconds. ========================" << endl;
                     cout << "===== MATPOWER publishing voltage values after dispatching new generation profile. ==================" << endl;
                  }
                  else {
                     cout << "================== It has been " << curr_hours << " hours, " << curr_minutes << " minutes, and ";
                     cout << curr_seconds << " seconds. ========================" << endl;
                     cout << "===== MATPOWER publishing voltage new values due to topology change. ==================" << endl;
                  }
               }
               for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++) {
                  for (int ind = 1; ind <= nbrows; ind ++) { // need to find the corresponding bus row in the BUS matrix
                     if ((int) mwBusOut.Get(2, ind, 1) == bus_num[bus_ind]) {
                        sendValReal[bus_ind] =  (double) mwBusOut.Get(2, ind, 8)*cos((double) mwBusOut.Get(2, ind, 9) * PI / 180)*(double) mwBusOut.Get(2, ind, 10)*1000; // real voltage at the bus based on the magnitude (column 8 of the output bus matrix) and angle in degrees (column 9 of the output bus matrix), from pu to kV to V
                        sendValIm[bus_ind] = (double) mwBusOut.Get(2, ind, 8)*sin((double) mwBusOut.Get(2, ind, 9) * PI / 180)*(double) mwBusOut.Get(2, ind, 10)*1000; // imaginary voltage at the bus based on the magnitude (column 8 of the output bus matrix) and angle in degrees (column 9 of the output bus matrix), from pu to kV to V
                        if (solved_opf) {
                           realLMP[bus_ind] = (double) mwBusOut.Get(2, ind, 14)/1000; // local marginal price based on the Lagrange multiplier on real power mismatch (column 14 of the output bus matrix). price is in $/kWh
                           imagLMP[bus_ind] = (double) mwBusOut.Get(2, ind, 15)/1000; // local marginal price based on the Lagrange multiplier on reactive power mismatch (column 14 of the output bus matrix
                           
                           // ================== LOAD/DISTRIBUTION BUS VALUES METRICS =======================================
                           mpLoadBusValues.clearBusValues();
                           mpLoadBusValues.setBusID((int) mwBusOut.Get(2, ind, 1));
                           mpLoadBusValues.setBusLAMP((double) mwBusOut.Get(2, ind, 14));
                           mpLoadBusValues.setBusLAMQ((double) mwBusOut.Get(2, ind, 15));
                           mpLoadBusValues.setBusPD((double) mwBusOut.Get(2, ind, 3));
                           mpLoadBusValues.setBusQD((double) mwBusOut.Get(2, ind, 4));
                           mpLoadBusValues.setBusVA((double) mwBusOut.Get(2, ind, 9));
                           mpLoadBusValues.setBusVM((double) mwBusOut.Get(2, ind, 8));
                           mpLoadBusValues.setBusVMAX((double) mwBusOut.Get(2, ind, 12));
                           mpLoadBusValues.setBusVMIN((double) mwBusOut.Get(2, ind, 13));
                           mpLoadMetrics.setBusValues(mpLoadBusValues);
                        }
                     }
                  }
                  string voltUnit = "V"; // this could be taken out of the loop
                  string complexVoltage = makeComplexStr(&sendValReal[bus_ind], &sendValIm[bus_ind]);
                  fncs::publish(pubVoltage[bus_ind], complexVoltage + " " + voltUnit);
                  // =========================================================================================================================
                  // Price will be sent only when an OPF has been solved
                  if (solved_opf) {
                     tempLMPStr.str(string());
                     tempLMPStr << realLMP[bus_ind];
                     string priceUnit = "$/kWh"; // could be taken out of the loop
                     fncs::publish(pubPrice[bus_ind], tempLMPStr.str() + " " + priceUnit);
                  }
                  // this following loop is for testing purposes only, as it goes to find the substations corresponding to current bus and show how much voltage has just been calculated.
                  for (int sub_ind = 0; sub_ind < sizeof(sub_bus)/sizeof(sub_bus[0]); sub_ind++) {
                     if (sub_bus[sub_ind] == bus_num[bus_ind]) {
                        cout << "====== PUBLISHING NEW VOLTAGE " << pubVoltage[bus_ind] << " FOR " << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind] << endl;
                        if (solved_opf) {
                           cout << "====== MARKET CYCLE FINISHED WITH PUBLISHED LMP " << realLMP[bus_ind] << " $/kWh, FOR " << sub_name[sub_ind] << " at bus " << bus_num[bus_ind] << endl;
                        }
                     }
                  }
                  
               }
               // Saving the data of each time when at least one message had been exchanged to the corresponding CSV file for each distribution network/substation
               // Turning this off for a while
               
               for (int bus_ind = 0; bus_ind < nFNCSbuses; bus_ind++){
                  ofstream subst_output_file(subst_output_file_name[bus_ind], ios::app);
                  for (int ind = 1; ind <= nbrows; ind++) {
                     if ((int) mwBusOut.Get(2, ind, 1) == bus_num[bus_ind]) {
                        subst_output_file << curr_time << "," << (double) mwBusOut.Get(2, ind, 3) << "," << (double) mwBusOut.Get(2, ind, 4) << ", " << sendValReal[bus_ind] << ", " << sendValIm[bus_ind] <<  ", " << realLMP[bus_ind] << ", " << imagLMP[bus_ind] << endl;
                     }
                  }
               }

               for (int gen_ind = 0; gen_ind < sizeof(offline_gen_ind)/sizeof(offline_gen_ind[0]); gen_ind++){ // in C indexes start from 0, but from MATLAB variables index needs to start from 1; these refer only to the generators that might get offline
                  ofstream gen_output_file(gen_output_file_name[gen_ind], ios::app);
                  gen_output_file << curr_time << "," << (int) mwGenOut.Get(2, offline_gen_ind[gen_ind], 8) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 9) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 10) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 2) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 4) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 5) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 3) << endl;
               }
				
            }
            // Line Below is from when running off-line, without FNCS
            // curr_time = curr_time + 1;
            if (solved_opf) {
              mpLoadMetrics.setCurrentTimeBusValues(curr_time);
              mpGeneratorMetrics.setCurrentTimeBusValues(curr_time);
            }
         }while(synchronize(mesg_rcv || mesg_snt) && curr_time <= simStopTime);
          // use while(!mesg_rcv || !mesg_snt); // when running off-line from FNCS
          // OR
          // while(curr_time < 400);
          // use while(synchronize(!mesg_rcv || !mesg_snt)); // when involving FNCS

         cout << "Just finished executing MATPOWER as a shared library." << endl;
         cout << "Let's write some MATPOWER metrics in JSON format." << endl;
         mpLoadMetrics.jsonSave(loadMetricsFile);
         mpGeneratorMetrics.jsonSave(generatorMetricsFile);
         fncs::finalize();
         cout << "<<<<<<<<<<<<<<< IS THIS REALLY DONE??? >>>>>>>>>>>>>>>>>>>>>>" << endl;
         //matpowerMetric.jsonSave(metricsOutput);
         /*
         subst_output_file.close();
         gen_output_file.close();
         dem_curve_file.close();
         */
         // mxDestroyArray(data_file);
         //mxFree(file_name);
         //
         /*
         mwDestroyArray(mwBusOut);
         mxDestroyArray(mwGenOut);
         mxDestroyArray(mwBranchOut);
         mxDestroyArray(f);
         mxDestroyArray(success);
         mxDestroyArray(info);
         mxDestroyArray(et);
         mxDestroyArray(g);
         mxDestroyArray(jac);
         mxDestroyArray(xr);
         mxDestroyArray(pimul);
         */
         }
      catch (const mwException& e) {
         cerr << e.what() << endl;
         cout << "Caught an error!!!" << endl;
         cout << "================ FNCS FATALITY !!!!! ==================" << endl;
         fncs::die();
         return -2;
         }
      catch (...) {
         cerr << "Unexpected error thrown" << endl;
         cout << "================ FNCS FATALITY !!!!! ==================" << endl;
         fncs::die();
         return -3;
         }
   libMATPOWERTerminate();
   }
   mclTerminateApplication();
   // fncs::finalize();
   return 0;
}

/* ==================================================================================================================
====================== MAIN PART ====================================================================================
===================================================================================================================*/
int main(int argc, char **argv) {
	if (argc < 7 || argc >= 8){
      cout << "========================== ERROR ================================================" << endl;
      cout << "Six arguments need to be provided: MATPOWER case file, the load profile file,  " << endl;
      cout << "the simulation stop time in seconds, the presumed starting time, and the JSON output metric file." << endl;
      cout << "There were " << argc << " arguments given!" << endl;
      cout << "=================================================================================" << endl;
      exit(EXIT_FAILURE);
   }
   mclmcrInitialize();
   // return mclRunMain((mclMainFcnType) run_main, 0, NULL);
   cout << "Number of arguments: " << argc << endl;
   if (argc > 0) cout << "Running process...... <<-- " << argv[0] << endl;
   if (argc > 1) cout << "with MATPOWER case in...... <<-- " << argv[1] << endl;
   if (argc > 2) cout << "and daily load profile in...... <<-- " << argv[2] << endl;
   if (argc > 3) cout << "for a total simulation time of " << argv[3] << " seconds," << endl;
   if (argc > 4) cout << "starting on " << argv[4] << "," << endl;
   if (argc > 5) cout << "with load metrics in JSON format in file ...... <<-- " << argv[5] << endl;
   if (argc > 6) cout << "generator metrics in JSON format in file ...... <<-- " << argv[6] << endl;
   return mclRunMain((mclMainFcnType) run_main(argc, argv), 0, NULL);
}
