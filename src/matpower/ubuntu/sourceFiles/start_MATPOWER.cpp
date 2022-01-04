/*
Launching the MATPOWER Power Flow / Optimal Power Flow solver
==========================================================================================
Copyright (C) 2013-2022, Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
==========================================================================================
Due to the fact that the file has been going through many updates, I have taken out the updates
list and added it to the file ../docFiles/mpWrapperUpdates.md.
==========================================================================================
*/
#include <stdio.h>
#include <sys/resource.h>
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
#include "logging.hpp"
# define PI 3.14159265

#include "matpowerintegrator.h"
#include "read_input_data.h"

#include "matpowerLoadMetrics.h"
#include "matpowerGeneratorMetrics.h"

#include "json/json.h"

// set the definition for the logger
loglevel_e loglevel;

// Transposing matrices; we need this function becuase the way the file reading is done leads to the transpose of the necessary matrix
// Careful: it is 1-base indexing because we are working with MATLAB type array mwArray
mwArray mwArrayTranspose(int nrows, int ncolumns, mwArray matrix_in) {
  mwArray matrix_out(nrows, ncolumns, mxDOUBLE_CLASS);
  for (int ind_row = 1; ind_row <= nrows; ind_row++) {
    for (int ind_col = 1; ind_col <= ncolumns; ind_col++) {
      matrix_out(ind_row, ind_col) = matrix_in(ind_col, ind_row); 
    } 
  }
  return matrix_out; 
}


int run_main(int argc, char **argv) {
  const char *options[] = {"-nojvm","-nodisplay"};
  if (!mclInitializeApplication(options, 2)) {
    LERROR << "Could not initialize the application properly !!!" ;
    return -1;
  }
  if (!libMATPOWERInitialize()) {
    LERROR << "Could not initialize one or more MATLAB/MATPOWER libraries properly !!!" ;
    return -1;
    }
  else {
    try {
// ================================ VARIABLE DECLARATION AND INITIALIZATION =============================================
      LINFO << "Just entered the MAIN function of the driver application." ;
      // Initialize the input parameters giving the MATPOWER model file, the load profile, simulation stop time, market clearing time, and JSON files.
      char *file_name;
      file_name = argv[1];
      char *real_load_profile_file;
      real_load_profile_file = argv[2];
      char *reac_load_profile_file;
      reac_load_profile_file = argv[3];  
      int simStopTime;
      sscanf(argv[4], "%d%*s", &simStopTime);
      int marketTime;
      sscanf(argv[5], "%d%*s", &marketTime);
      string startTime;
      startTime = argv[6];
      LINFO << "Running MATPOWER ends after " << simStopTime << " seconds, supposing it starts on " << startTime << ".";
// ================================ METRICS FOR TRANSACTIVE ENERGY VALUATION ============================================
// ================================ LOAD BUS METRICS ====================================================================
      const char *loadMetricsFile;
      loadMetricsFile = argv[7];
      ofstream loadMetricsOutput(loadMetricsFile, ofstream::out);
      loadBusMetrics mpLoadMetrics;
      loadMetadata mpLoadMetadata;
      loadBusValues mpLoadBusValues;
      mpLoadMetrics.setMetadata(mpLoadMetadata);
      mpLoadMetrics.setName(file_name);
      mpLoadMetrics.setStartTime(startTime);
// ================================ DISPATCHABLE LOAD BUS METRICS ================================================================
      const char *dispLoadMetricsFile;
      dispLoadMetricsFile = argv[8];
      ofstream dispLoadMetricsOutput(dispLoadMetricsFile, ofstream::out);
      generatorBusMetrics mpDispLoadMetrics;
      generatorMetadata mpDispLoadMetadata;
      generatorBusValues mpDispLoadValues;
      mpDispLoadMetrics.setMetadata(mpDispLoadMetadata);
      mpDispLoadMetrics.setName(file_name);
      mpDispLoadMetrics.setStartTime(startTime);
// ================================ GENERATOR BUS METRICS ================================================================
      const char *generatorMetricsFile;
      generatorMetricsFile = argv[9];
      ofstream generatorMetricsOutput(generatorMetricsFile, ofstream::out);
      generatorBusMetrics mpGeneratorMetrics;
      generatorMetadata mpGeneratorMetadata;
      generatorBusValues mpGeneratorBusValues;
      mpGeneratorMetrics.setMetadata(mpGeneratorMetadata);
      mpGeneratorMetrics.setName(file_name);
      mpGeneratorMetrics.setStartTime(startTime);
// ======================================================================================================================
      // Read the MATPOWER transmission model file in order to get the size of the system, that is number of busses, generators, etc.
      // These dimensions are needed to be able to create the model matrices later without dynamic allocation of memory.
      // Declaration of dimension variables.
      int nbrows = 0, nbcolumns = 0, ngrows = 0, ngcolumns = 0;
      int nbrrows = 0, nbrcolumns = 0, narows = 0, nacolumns = 0;
      int ncrows = 0, nccolumns = 0, nFNCSbuses = 0, nFNCSsubst = 0, noffgelem = 0;
      // ========================================================
      // Laurentiu Dan Marinovici - 2017/09/08
      // Adding the code snippet execution time; similar code is going to be added throughout the wrapper
      // ========================================================
      clock_t tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      read_model_dim(file_name, &nbrows, &nbcolumns, &ngrows, &ngcolumns,
        &nbrrows, &nbrcolumns, &narows, &nacolumns,
        &ncrows, &nccolumns, &nFNCSbuses, &nFNCSsubst, &noffgelem);
      // ========================================================
      // Laurentiu Dan Marinovici - 2017/09/08
      // Adding the code snippet execution time
      // ========================================================
      clock_t tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      clock_t tElapsed = tAfter - tBefore;
      int tHours = tElapsed / 3600000;
      int tMins = (tElapsed - tHours * 3600000) / 60000;
      int tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      int tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Reading MPC structure dimensions took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
      /*
      cout << nbrows << '\t' << nbcolumns << '\t' << ngrows << '\t' << ngcolumns << '\t' << endl;
      cout << nbrrows << '\t' << nbrcolumns << '\t' << narows << '\t' << nacolumns << endl;
      cout << ncrows << '\t' << nccolumns << '\t' << nFNCSSub << '\t' << noffGen << endl;
      */
// ========================================================================================================================
      // Load profile for the "static" load at all the buses.
      // The number of profiles should be equal to exactly the amount of buses in the system. Careful, though!!!
      // Each profile needs to start from the value that exists initially in the MATPOWER model at the specific bus.
      // Each profile consists of data for 24 hours every 5 minutes (288 values taken repeatedly every day)
      double real_power_demand[nbrows][288], reactive_power_demand[nbrows][288];
      for (int i = 0; i < sizeof(real_power_demand)/sizeof(real_power_demand[0]); i++) {
        for (int j = 0; j < sizeof(real_power_demand[0])/sizeof(real_power_demand[0][0]); j++) {
          real_power_demand[i][j] = 0;
          reactive_power_demand[i][j] = 0;
        }
      }
      // Get load profile data, to make the load evolution in time more realistic
      tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      read_load_profile(real_load_profile_file, real_power_demand, nbrows);
      tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      tElapsed = tAfter - tBefore;
      tHours = tElapsed / 3600000;
      tMins = (tElapsed - tHours * 3600000) / 60000;
      tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Reading the real load profile took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
      tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      read_load_profile(reac_load_profile_file, reactive_power_demand, nbrows);
      tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      tElapsed = tAfter - tBefore;
      tHours = tElapsed / 3600000;
      tMins = (tElapsed - tHours * 3600000) / 60000;
      tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Reading the reactive load profile took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
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
      // double mwBusOut_copy[9];
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
      char sub_name[nFNCSsubst][25];
      // static active and reactive power at the buses that are connected to substations
      double fixed_pd[nbrows], fixed_qd[nbrows];
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
      bool fncs_time_request = false; // used to keep track of when to call fncs time request
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
      int curr_time = -2; // current time in seconds
      int next_OPF_time = -2; // next time we want to call the opf
      int next_FNCS_time = 0; // next time returned by FNCS for the simulator to run
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
      string voltUnit = "V"; // unit for the published voltage
      string pubPrice[nFNCSbuses]; // topics under which MATPOWER publishes prices/LMPs
      string priceUnit = "$/MWh"; // unit for the published price/LMP (the CCSI needs price in $/MWH)
      // ====================================================
      // Laurentiu Dan Marinovici - 2017/06/26
      int mesgDLc[nFNCSbuses];
      int mesgDCc[nFNCSbuses];
      string dispLoadKey[nFNCSbuses];
      string demandCurveKey[nFNCSbuses];
      double dispLoadValue[nFNCSbuses][2];
      double dispLoadDemandCurveCoeff[nFNCSbuses][3];
      // ====================================================
      // Temporary strings needed to transform ints or floats into a corresponding string for messages
      // tempBNumStr = string containing the bus number
      // tempLMPStr = string containing the LMP in $/MW
      stringstream tempBNumStr, tempLMPStr;

// ========================================================================================================================
      // Creating the MPC structure that is going to be used as input for OPF function
      tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      double *p_temp,*q_temp;
      int *pq_length,*receive_flag;
      const char *fields[] = {"baseMVA", "bus", "gen", "branch", "areas", "gencost"}; 
      mwArray mpc(1, 1, 6, fields);
     
      // Creating the variable that would set the options for the OPF solver
      const char *optFields[] = {"model", "pf", "cpf", "opf", "verbose", "out", "mips", "clp", "cplex", "fmincon", "glpk", "gurobi", "ipopt", "knitro", "minopf", "mosek", "pfipm", "tralm"};
      mwArray mpopt(1, 1, 18, optFields);
      LINFO << "=================================================";
      LINFO << "========= SETTING UP THE OPTIONS !!!!!===========";
      LINFO << "Setting initial options........";
      mpoption(1, mpopt); // initialize powerflow options to DEFAULT structure
      // Set amount of progress info to be printed during MATPOWER execution
      //   0 - print no progress info
      //   1 - print a little progress info
      //   2 - print a lot of progress info
      //   3 - print all progress info
      mpopt.Get("verbose", 1, 1).Set(mwArray(0));
      // Set up controls for pretty-printing of results
      //  -1 - individual flags control what is printed
      //   0 - do not print anything
      //   1 - print everything
      mpopt.Get("out", 1, 1).Get("all", 1, 1).Set(mwArray(0));
      // AC vs. DC modeling for power flow and OPF formulation
      //  'AC' - use AC formulation and corresponding algs/options
      //  'DC' - use DC formulation and corresponding algs/options
      mpopt.Get("model", 1, 1).Set(mwArray("AC")); // This should normally be AC power flow
      // Setting the DC OPF solver to MIPS, MATPOWER Interior Point Solver
      mpopt.Get("opf", 1, 1).Get("dc", 1, 1).Get("solver", 1, 1).Set(mwArray ("DEFAULT")); // "MIPS"
      LINFO << " <<<<<< The DC OPF solver is set to " << mpopt.Get("opf", 1, 1).Get("dc", 1, 1).Get("solver", 1, 1) << ". >>>>>>";
      LINFO << "===================================================";
      tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      tElapsed = tAfter - tBefore;
      tHours = tElapsed / 3600000;
      tMins = (tElapsed - tHours * 3600000) / 60000;
      tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Setting the MATPOWER solver options took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

      
// ================================ END OF VARIABLE DECLARATION AND INITIALIZATION =============================================
// =============================================================================================================================
      // get the MATPOWER model data
      tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      read_model_data(file_name, nbrows, nbcolumns, ngrows, ngcolumns, nbrrows, nbrcolumns, narows, nacolumns,
        ncrows, nccolumns, nFNCSbuses, nFNCSsubst, noffgelem, &baseMVA, bus, gen,
        branch, area, costs, bus_num, sub_name, sub_bus, offline_gen_bus, &amp_fact);
      tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      tElapsed = tAfter - tBefore;
      tHours = tElapsed / 3600000;
      tMins = (tElapsed - tHours * 3600000) / 60000;
      tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Reading the MPC case file took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

      // output files for saving results
      // 2015-03-17 Turned off the file generation.
    
      /* Turned off 06/07/2017
      char subst_output_file_name[nFNCSbuses][18]; // one file for each substation
      
      char gen_output_file_name[noffgelem][17]; // one file for each generator that is turned off; for larger models we were getting too many files
      ofstream subst_output_file, gen_output_file; // output file streams
      for (int i = 0; i < sizeof(subst_output_file_name)/sizeof(subst_output_file_name[0]); i++) {
        snprintf(subst_output_file_name[i], sizeof(subst_output_file_name[i]), "Bus_%d.csv", bus_num[i]); // Bus_#.csv
        ofstream subst_output_file(subst_output_file_name[i], ios::out);
        subst_output_file << "Time (seconds), Real Power Demand - PD (MW), Reactive Power Demand (MVAr), Substation V real (V), Substation V imag (V), LMP ($/kWh), LMP ($/kVArh)" << endl;
      }         
      
      // Turning off the Generator file creation for a while. Uncomment the lines below to have them created again.
      for (int i = 0; i < sizeof(gen_output_file_name)/sizeof(gen_output_file_name[0]); i++) {
        snprintf(gen_output_file_name[i], sizeof(gen_output_file_name[i]), "Generator_%d.csv", offline_gen_bus[i]); // Generator_BUS#.csv
        ofstream gen_output_file(gen_output_file_name[i], ios::out);
        gen_output_file << "Time (seconds), STATUS, PMAX (MW), PMIN (MW), Real power output - PG (MW), QMAX (MVAr), QMIN (MVAr), Reactive power output - QG (MVAr)" << endl;
      }
      */
      tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
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
      tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      tElapsed = tAfter - tBefore;
      tHours = tElapsed / 3600000;
      tMins = (tElapsed - tHours * 3600000) / 60000;
      tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Creating the MPC structurec took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
  
      // =====================================================================================================================
      // Setting the published topics - for each bus in the transmission network where distribution networks are connected to, we publish
      // voltage and LMP
      // ===================================================
      // Laurentiu Dan Marinovici - 2016/06/26
      // Also creating the look-up keys for the dispatchable load cases
      // ===================================================
      tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++) {
        // Temporary stream to help transforming ints into strings
        tempBNumStr.str(string()); // clearing the previous value from the temporary stream
        tempBNumStr << bus_num[bus_ind]; // copying the number into the temporary stream
        pubVoltage[bus_ind] = "three_phase_voltage_B" + tempBNumStr.str(); // bus voltage: it will have a complex number as value and V as unit
        pubPrice[bus_ind] = "LMP_B" + tempBNumStr.str(); // LMP at the bus
        dispLoadKey[bus_ind] = "Bus_" + tempBNumStr.str() + "_dispatchableLoad";
        demandCurveKey[bus_ind] = "Bus_" + tempBNumStr.str() + "_dlDemandCurveCoeff";
      }
      tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      tElapsed = tAfter - tBefore;
      tHours = tElapsed / 3600000;
      tMins = (tElapsed - tHours * 3600000) / 60000;
      tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Setting the published topics took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

      // The index of the bus in the bus matrix could be different from the number of the bus
      // because buses do not have to be numbered consecutively, or be the same as the index
      for (int ind = 0; ind < nbrows; ind++) {
        // ind is an index in MATLAB, that is it should start at 1
        // In mpc.Get("bus", 1, 1).Get(2, ind, 1), the 2 in the second Get represents the number of indeces the array has
        fixed_pd[ind] = mpc.Get("bus", 1, 1).Get(2, ind+1, 3);
        fixed_qd[ind] = mpc.Get("bus", 1, 1).Get(2, ind+1, 4);
        LDEBUG << "Initially, the static ACTIVE power at bus " << bus[ind*nbcolumns] << " is " << fixed_pd[ind] << "." ;
        LDEBUG << "Initially, the static REACTIVE power at bus " << bus[ind*nbcolumns] << " is " << fixed_qd[ind] << "." ;
      }

      // Find the index in the MATPOWER generator matrix corresponding to the buses with generators that could be turned off
      // The bus number and the actual index in the MATPOWER matrix may not coincide
      for (int off_ind = 0; off_ind < sizeof(offline_gen_bus)/sizeof(offline_gen_bus[0]); off_ind++){
        for (int gen_ind = 1; gen_ind <= ngrows; gen_ind++){ // in MATLAB indexes start from 1
          if((int) mpc.Get("gen", 1, 1).Get(2, gen_ind, 1) == offline_gen_bus[off_ind]){
            offline_gen_ind[off_ind] = gen_ind; // index of the bus in the MATPOWER matrix
            LDEBUG << "GENERATOR AT BUS " << mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 1) << " MIGHT BECOME OFF-LINE!!!!";
          }
        }
      }

      // ==========================================================================================================
      // Uncomment the line below when running with FNCS
      tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      fncs::initialize();
      tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
      tElapsed = tAfter - tBefore;
      tHours = tElapsed / 3600000;
      tMins = (tElapsed - tHours * 3600000) / 60000;
      tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
      tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
      LMACTIME << "Initializing FNCS took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

      // ==========================================================================================================
      
      // After FNCS is initialized we can adjust the start time to be one timestep earlier than when the OPF results
      // are needed in other applications. This time is dictated by the zpl file.
      next_FNCS_time = -1*fncs::get_time_delta();
      next_OPF_time = -1*fncs::get_time_delta();
      do {
        // Start every time assuming no message is received or sent
        mesg_rcv = false;
        mesg_snt = false;
        solved_opf = false;
        topology_changed = false;
        fncs_time_request = false;
        // ==========================================================================================================
        // =============== CURRENT SIMULATION TIME ==================================================================
        curr_time = next_FNCS_time;
        curr_hours = curr_time/3600;
        curr_minutes = (curr_time - 3600*curr_hours)/60;
        curr_seconds = curr_time - 3600*curr_hours - 60*curr_minutes;
        // ==========================================================================================================
        
        // Setting the load at the load buses based on a one-day long profile. WARNING: if the model is changed these need to be readjusted
        tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        for (int ind = 0; ind < nbrows; ind++) {
          // get the fixed_pd and fixed_qd from the load profiles
          fixed_pd[ind] = real_power_demand[ind][12 * (curr_hours % 24) + curr_minutes / 5];
          fixed_qd[ind] = reactive_power_demand[ind][12 * (curr_hours % 24) + curr_minutes / 5];
          LDEBUG << "fixed active -->> " << fixed_pd[ind] << "(" << mpc.Get("bus", 1, 1).Get(2, ind+1, 3) << ") at bus " << bus[ind*nbcolumns] << " (" << mpc.Get("bus", 1, 1).Get(2, ind+1, 1) << ")" ;
          LDEBUG << "fixed reactive -->> " << fixed_qd[ind] << "(" << mpc.Get("bus", 1, 1).Get(2, ind+1, 4) << ") at bus " << bus[ind*nbcolumns] << " (" << mpc.Get("bus", 1, 1).Get(2, ind+1, 1) << ")" ;  
          mpc.Get("bus", 1, 1).Get(2, ind+1, 3).Set((mwArray) fixed_pd[ind]);
          mpc.Get("bus", 1, 1).Get(2, ind+1, 4).Set((mwArray) fixed_qd[ind]);          
        }
        tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        tElapsed = tAfter - tBefore;
        tHours = tElapsed / 3600000;
        tMins = (tElapsed - tHours * 3600000) / 60000;
        tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
        tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
        LMACTIME << "Setting current loads according to their profile values took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
        
        // Setting up the status of the generators, based on the current time
        // Turning some generators out-of-service between certain time preiods in the simulation 
        // every day between 6 and 7 or 18 and 19 !!! WARNING !!! These hours are hard coded assuming we run more than 24 hours
        if ((curr_hours % 24 >= 6 && curr_hours % 24 < 7) || (curr_hours % 24 >= 18 && curr_hours % 24 < 19)){
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          for (int off_ind = 0; off_ind < sizeof(offline_gen_ind)/sizeof(offline_gen_ind[0]); off_ind++){
            if ((double) mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8) == 1){ // if generator is ON
              mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8).Set((mwArray) 0); // turn generator OFF, and set flag that topology has changed
              topology_changed = topology_changed || true; // signal that at least one generator changed its state
              //mesg_snt = mesg_snt || true; // signal that at least one generator changed its state
              // Uncomment after testing the load profile loading correctly
              LDEBUG << "============ Generator at bus " << mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 1);
              LDEBUG << " is put OUT-OF-SERVICE. ==================" ;
            }
          }
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Checking if generators are to be turned OFF took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
        }
        else {
          for (int off_ind = 0; off_ind < sizeof(offline_gen_ind)/sizeof(offline_gen_ind[0]); off_ind++){
            tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
            if ((double) mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8) == 0){ // if generator is OFF
              mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 8).Set((mwArray) 1); // turn generator ON, and set flag that topology changed
              topology_changed = topology_changed || true;// signal that at least one generator changed its state
              //mesg_snt = mesg_snt || true; // signal that at least one generator changed its state
              // Uncomment after testing the load profile loading correctly
              LDEBUG << "============ Generator at bus " << mpc.Get("gen", 1, 1).Get(2, offline_gen_ind[off_ind], 1);
              LDEBUG << " is brought back IN-SERVICE. ==================" ;
            }
          }
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Checking if generators are to be turned ON took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

        }
        
        tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
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
        tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        tElapsed = tAfter - tBefore;
        tHours = tElapsed / 3600000;
        tMins = (tElapsed - tHours * 3600000) / 60000;
        tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
        tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
        LMACTIME << "Getting power from all GLDs and setting it in MPC structure took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

        if (mesg_rcv){ // If at least one distribution network publishes
          // ==========================================================================================================
          // Uncomment after testing the load profile loading correctly
          // cout << "\033[2J\033[1;1H"; // Just a trick to clear the screen before pritning the new results at the terminal
          LINFO << "================== It has been " << curr_hours << " hours, " << curr_minutes << " minutes, and " << curr_seconds << " seconds. ========================" ;
          LINFO << "====== New published values from the distribution networks exist. ==================" ;
          for (int sub_ind = 0; sub_ind < sizeof(sub_bus)/sizeof(sub_bus[0]); sub_ind++) {
            if (mesgc[sub_ind] == 1) {
              // Uncomment after testing the load profile loading correctly
              LDEBUG << "====== New ACTIVE power from GRIDLab-D AT " << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind] << " is " << sub_valueReal[sub_ind] << " " << actPowerUnit << " ======" ;
              LDEBUG << "====== New REACTIVE power from GRIDLab-D AT " << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind] << " is " << sub_valueIm[sub_ind] << " " << reactPowerUnit << " ======" ;
              LDEBUG << "I've got the NEW POWER after " << delta_t[sub_ind] << " seconds." ;
              prev_time[sub_ind] = curr_time;
            }
            else {
              // Uncomment after testing the load profile loading correctly
              LDEBUG << "===== NO LOAD CHANGE AT " << sub_name[sub_ind] << " AT BUS " << sub_bus[sub_ind] << " =====================" ;
            } // end IF(mesgc)
          } // end FOR(sub_ind)
          for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++) { // only for printing/debugging purposes
            for (int ind = 1; ind <= nbrows; ind++) {
              if ((int) mpc.Get("bus", 1, 1).Get(2, ind, 1) == bus_num[bus_ind]) {
                LDEBUG << "Total ACTIVE power required at bus: " << bus_num[bus_ind] << " is " << mpc.Get("bus", 1, 1).Get(2, ind, 3) << " MW." ;
                LDEBUG << "Total REACTIVE power required at bus: " << bus_num[bus_ind] << " is " << mpc.Get("bus", 1, 1).Get(2, ind, 4) << " MVAR." ;
              }
            }
          } // end FOR(bus_ind)
        } // end IF(mesg_rcv)
        
        // Running the actual transmission simulator, by solving the power flow, or the optimal power flow
        if (curr_time == next_OPF_time || topology_changed){
          // ========================================================
          // Laurentiu Dan Marinovici - 2017/06/26
          // Adding the dispatchable load and bidding curve
          // ========================================================
          LINFO << "================= Trying to get the DISPATCHABLE LOAD PART, at current time. ================== " << curr_time;
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          for (int bus_ind = 0; bus_ind < sizeof(bus_num)/sizeof(bus_num[0]); bus_ind++) {
            for (int genRowInd = 1; genRowInd <= ngrows; genRowInd++) {
              // A distribution/load bus could be part of the generation matrix as negative generation
              // if it supplies controllable loads; however, there are times when no available controllable loads exist;
              // that is when those dispatchable load buses are set as disabled in the generation matrix, and do not participate in OPF.
              // Also, if it turns out that one of the generator buses also has load on it, and that load is dispatchable, the bus will
              // show up in the generator matrix twice, and hence a test to see if it is a normal or negative generation bus should be performed (see last
              // 2 tests in the following IF statement)              
              if ((int) mpc.Get("gen", 1, 1).Get(2, genRowInd, 1) == bus_num[bus_ind] && (double) mpc.Get("gen", 1, 1).Get(2, genRowInd, 9) <= 0 && (double) mpc.Get("gen", 1, 1).Get(2, genRowInd, 10) <= 0) {
                getDispLoad(dispLoadKey[bus_ind], &mesgDLc[bus_ind], &dispLoadValue[bus_ind][0], &dispLoadValue[bus_ind][1]);
                if (mesgDLc[bus_ind] == 1) {
                  if (dispLoadValue[bus_ind][0] == 0) { // that is, there are no available controllable loads
                    mpc.Get("gen", 1, 1).Get(2, genRowInd, 8).Set(mwArray (0));
                    LINFO << "** No available controllable loads at bus " << bus_num[bus_ind];
                    LINFO << "** so I am turning off the negative generation corresponding to this bus.";
                  }
                  else {
                    mpc.Get("gen", 1, 1).Get(2, genRowInd, 8).Set(mwArray (1));
                    // mpc.Get("gen", 1, 1).Get(2, genRowInd, 10).Set(mwArray (-amp_fact*dispLoadValue[bus_ind]));
                    // Jacob, in CCSI we can't have the amplification here
                    mpc.Get("gen", 1, 1).Get(2, genRowInd, 10).Set(mwArray (-dispLoadValue[bus_ind][0]));
                    for (int busRowInd = 1; busRowInd <= nbrows; busRowInd++) {
                      if ((int) mpc.Get("bus", 1, 1).Get(2, busRowInd, 1) == bus_num[bus_ind]) {
                        // mpc.Get("bus", 1, 1).Get(2, busRowInd, 3).Set((mwArray) ((double) mpc.Get("bus", 1, 1).Get(2, busRowInd, 3) - amp_fact*dispLoadValue[bus_ind]));
                        // Jacob, in CCSI we can't have the amplification here
                        mpc.Get("bus", 1, 1).Get(2, busRowInd, 3).Set((mwArray) ((double) mpc.Get("bus", 1, 1).Get(2, busRowInd, 3) -dispLoadValue[bus_ind][1]));
                      }
                    }
                    getDLDemandCurve(demandCurveKey[bus_ind], &mesgDCc[bus_ind], &dispLoadDemandCurveCoeff[bus_ind][0], &dispLoadDemandCurveCoeff[bus_ind][1], &dispLoadDemandCurveCoeff[bus_ind][2]);
                    mpc.Get("gencost", 1, 1).Get(2, genRowInd, 4).Set(mwArray (3));
                    mpc.Get("gencost", 1, 1).Get(2, genRowInd, 5).Set((mwArray) (-dispLoadDemandCurveCoeff[bus_ind][0]));
                    mpc.Get("gencost", 1, 1).Get(2, genRowInd, 6).Set((mwArray) (dispLoadDemandCurveCoeff[bus_ind][1]));
                    mpc.Get("gencost", 1, 1).Get(2, genRowInd, 7).Set((mwArray) (-dispLoadDemandCurveCoeff[bus_ind][2]));
                  }
                }
              }
            }
          }
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Setting the dispatchable loads (if any) took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

          // Call OPF with nargout = 0 (first argument), and all results are going to be printed at the console
          // Call OPF with nargout = 7, and get all the output parameters up to et
          // Call OPF with nargout = 11, and get a freaking ERROR.... AVOID IT!
          // cout << "================= Solving the OPTIMAL POWER FLOW. ==================" << endl;
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          LINFO << "== New generator matrix before DC OPF ==";
          LINFO << mpc.Get("gen", 1, 1);
          LINFO << "== New bus matrix before DC OPF ==";
          LINFO << mpc.Get("bus", 1, 1);
          LINFO << "== New gencost matrix before DC OPF ==";
          LINFO << mpc.Get("gencost", 1, 1);
          // mpopt.Get("model", 1, 1).Set(mwArray("DC"));
          runopf(8, mwMVAbase, mwBusOut, mwGenOut, mwGenCost, mwBranchOut, f, success, et, mpc, mpopt, printed_results, saved_results);
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Running OPF took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
          // ============ DISPATCHABLE LOAD (NEGATIVE GENERATOR) METRICS ======================
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          for (int genInd = 1; genInd <= ngrows; genInd++) { // indexing in a MATLAB matrix structure
            if ((double) mwGenOut.Get(2, genInd, 9) <= 0 && (double) mwGenOut.Get(2, genInd, 10) <= 0) { // only for dispatchable loads (negative generators)
              mpDispLoadValues.clearBusValues();
              mpDispLoadValues.setGenIndex((int) genInd);
              mpDispLoadValues.setBusID((int) mwGenOut.Get(2, genInd, 1));
              mpDispLoadValues.setBusPG((double) mwGenOut.Get(2, genInd, 2) * (-1));
              mpDispLoadValues.setBusQG((double) mwGenOut.Get(2, genInd, 3) * (-1));
              mpDispLoadValues.setBusStatus((double) mwGenOut.Get(2, genInd, 8));
              for (int busInd = 1; busInd <= nbrows; busInd++) {
                if ((int) mwGenOut.Get(2, genInd, 1) == (int) mwBusOut.Get(2, busInd, 1)) {
                  mpDispLoadValues.setBusLAMP((double) mwBusOut.Get(2, busInd, 14));
                  mpDispLoadValues.setBusLAMQ((double) mwBusOut.Get(2, busInd, 15));
                }
              }
              mpDispLoadMetrics.setBusValues(mpDispLoadValues);
            }
          }
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Creating dispatchable load metrics took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
          mpDispLoadMetrics.setCurrentTimeBusValues(curr_time);
          // Bring system in the new state by replacing the bus, generator, branch and generator cost matrices with the calculated ones
          mpc.Get("gen", 1, 1).Set(mwGenOut);
          mpc.Get("bus", 1, 1).Set(mwBusOut);
          mpc.Get("branch", 1, 1).Set(mwBranchOut);
          mpc.Get("gencost", 1, 1).Set(mwGenCost);
          LINFO << "== New generator matrix after DC OPF ==";
          LINFO << mpc.Get("gen", 1, 1);
          LINFO << "== New bus matrix after DC OPF ==";
          LINFO << mpc.Get("bus", 1, 1);
          LINFO << "== New gencost matrix after DC OPF ==";
          LINFO << mpc.Get("gencost", 1, 1);
          // With the new generation dispatch, run an AC PF to recalculate the bus voltages.
          // Active dispatchable loads/negative generations are turned off, and their values
          // are added to the load buses they belong to; thus, we avoid any redispatch while
          // accounting for the dispatched load when recalculating the power flow.
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          for (int busInd = 0; busInd < sizeof(bus_num)/sizeof(bus_num[0]); busInd++) {
            for (int genRowInd = 1; genRowInd <= ngrows; genRowInd++) {
              if ((int) mpc.Get("gen", 1, 1).Get(2, genRowInd, 1) == bus_num[busInd] && (int) mpc.Get("gen", 1, 1).Get(2, genRowInd, 8) == 1) {
                mpc.Get("gen", 1, 1).Get(2, genRowInd, 8).Set(mwArray (0));
                for (int busRowInd = 1; busRowInd <= nbrows; busRowInd++) {
                  if ((int) mpc.Get("bus", 1, 1).Get(2, busRowInd, 1) == (int) mpc.Get("gen", 1, 1).Get(2, genRowInd, 1)) {
                    // Jacob: Since the objective of the PF is to calculate voltages, 
                    //        which depends on the load, it is not appropiate using 
                    //        the expected load. The actual load should be used. This 
                    //      of couse could mean that the LMP calculated is wrong if 
                    //        two don't match but the PF should not concern itself with this
                    //mpc.Get("bus", 1, 1).Get(2, busRowInd, 3).Set(mwArray ((double) mpc.Get("bus", 1, 1).Get(2, busRowInd, 3) - (double) mpc.Get("gen", 1, 1).Get(2, genRowInd, 2)));
                    mpc.Get("bus", 1, 1).Get(2, busRowInd, 3).Set((mwArray) ((double) mpc.Get("bus", 1, 1).Get(2, busRowInd, 3) + dispLoadValue[busInd][1]));
                  }
                }
              }
            }
          }
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Turning off dispatchable loads to run PF after OPF took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
          LINFO << "== New generator matrix before AC PF @ market cycle ==";
          LINFO << mpc.Get("gen", 1, 1);
          LINFO << "== New bus matrix before AC PF @ market cycle ==";
          LINFO << mpc.Get("bus", 1, 1);
          LINFO << "== New gencost matrix before AC PF @ market cycle ==";
          LINFO << mpc.Get("gencost", 1, 1);
          mpopt.Get("model", 1, 1).Set(mwArray("AC")); // This should normally be AC power flow
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          runpf(6, mwMVAbase, mwBusOut, mwGenOut, mwBranchOut, success, et, mpc, mpopt, printed_results, saved_results);
          // Bring system in the new state by replacing the bus, generator, and branch matrices with the calculated ones
          mpc.Get("gen", 1, 1).Set(mwGenOut);
          mpc.Get("bus", 1, 1).Set(mwBusOut);
          mpc.Get("branch", 1, 1).Set(mwBranchOut);
          LINFO << "== New generator matrix after AC PF @ market cycle ==";
          LINFO << mpc.Get("gen", 1, 1);
          LINFO << "== New bus matrix after AC PF @ market cycle ==";
          LINFO << mpc.Get("bus", 1, 1);
          LINFO << "== New gencost matrix after AC PF @ market cycle ==";
          LINFO << mpc.Get("gencost", 1, 1);
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Running PF after OPF took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";

          solved_opf = true;
          mesg_snt = mesg_snt || true;
          fncs_time_request = true;
        }            
        else {
          // cout << "================= Solving the POWER FLOW. ==================" << endl;
          // Active dispatchable loads/negative generations are turned off, even though they should all
          // have been turned off before solving the AC PF at the market cycle; bust just making sure, I think.
          LINFO << "== New generator matrix before AC PF ==";
          LINFO << mpc.Get("gen", 1, 1);
          LINFO << "== New bus matrix before AC PF ==";
          LINFO << mpc.Get("bus", 1, 1);
          LINFO << "== New gencost matrix before AC PF ==";
          LINFO << mpc.Get("gencost", 1, 1);
          for (int busInd = 0; busInd < sizeof(bus_num)/sizeof(bus_num[0]); busInd++) {
            for (int genRowInd = 1; genRowInd <= ngrows; genRowInd++) {
              if ((int) mpc.Get("gen", 1, 1).Get(2, genRowInd, 1) == bus_num[busInd] && (int) mpc.Get("gen", 1, 1).Get(2, genRowInd, 8) == 1) {
                mpc.Get("gen", 1, 1).Get(2, genRowInd, 8).Set(mwArray (0));
              }
            }
          }
          mpopt.Get("model", 1, 1).Set(mwArray("AC")); // This should normally be AC power flow
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          runpf(6, mwMVAbase, mwBusOut, mwGenOut, mwBranchOut, success, et, mpc, mpopt, printed_results, saved_results);
          if ((int) success == 0) {
            LWARNING << "Failed to solve AC PF, reverting to DC PF (at time " << curr_time << ")";
            mpopt.Get("model", 1, 1).Set(mwArray("DC"));
            runpf(6, mwMVAbase, mwBusOut, mwGenOut, mwBranchOut, success, et, mpc, mpopt, printed_results, saved_results);
            mpopt.Get("model", 1, 1).Set(mwArray("AC"));
          }

          // Bring system in the new state by replacing the bus, generator, and branch matrices with the calculated ones
          mpc.Get("gen", 1, 1).Set(mwGenOut);
          mpc.Get("bus", 1, 1).Set(mwBusOut);
          mpc.Get("branch", 1, 1).Set(mwBranchOut);
          LINFO << "== New generator matrix after AC PF ==";
          LINFO << mpc.Get("gen", 1, 1);
          LINFO << "== New bus matrix after AC PF ==";
          LINFO << mpc.Get("bus", 1, 1);
          LINFO << "== New gencost matrix after AC PF ==";
          LINFO << mpc.Get("gencost", 1, 1);
          tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          tElapsed = tAfter - tBefore;
          tHours = tElapsed / 3600000;
          tMins = (tElapsed - tHours * 3600000) / 60000;
          tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
          tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
          LMACTIME << "Running regular PF took  " << tHours << " hours, "\
                   << tMins << " minutes, "\
                   << tSecs << " seconds, and "\
                   << tMSecs << " msecs.\n" << "=========================================================";
        }

        if (mesg_rcv || mesg_snt) {
          tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
          if (mesg_snt) { // only cleaning the screen when MATPOWER initiates the message transfer; otherwise is cleaned when message is received
            // Uncomment after testing the load profile loading correctly
            // cout << "\033[2J\033[1;1H"; // Just a trick to clear the screen before pritning the new results at the terminal
            if (curr_time == next_OPF_time && !topology_changed) {
              LINFO << "================== It has been " << curr_hours << " hours, " << curr_minutes << " minutes, and " << curr_seconds << " seconds. ========================" ;
              LINFO << "===== MATPOWER publishing voltage values after dispatching new generation profile. ==================" ;
            }
            else {
              LINFO << "================== It has been " << curr_hours << " hours, " << curr_minutes << " minutes, and " << curr_seconds << " seconds. ========================" ;
              LINFO << "===== MATPOWER publishing voltage new values due to topology change. ==================" ;
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
                  // =========================================================================================================================
                  // Price will be sent only when an OPF has been solved
                  tempLMPStr.str(string());
                  tempLMPStr << realLMP[bus_ind] * 1000; // turning LMP back into $/MWh for CCSI
                  fncs::publish(pubPrice[bus_ind], tempLMPStr.str() + " " + priceUnit);
                }
              }
            }
            string complexVoltage = makeComplexStr(&sendValReal[bus_ind], &sendValIm[bus_ind]);
            fncs::publish(pubVoltage[bus_ind], complexVoltage + " " + voltUnit);
            // this following loop is for testing purposes only, as it goes to find the substations corresponding to current bus and show how much voltage has just been calculated.
            /*
            for (int sub_ind = 0; sub_ind < sizeof(sub_bus)/sizeof(sub_bus[0]); sub_ind++) {
              if (sub_bus[sub_ind] == bus_num[bus_ind]) {
                LDEBUG << "====== PUBLISHING NEW VOLTAGE " << pubVoltage[bus_ind] << " FOR " << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind];
                if (solved_opf) {
                  LDEBUG << "====== MARKET CYCLE FINISHED WITH PUBLISHED LMP " << realLMP[bus_ind] << " $/kWh, FOR " << sub_name[sub_ind] << " at bus " << sub_bus[sub_ind];
                }
              }
            }
            */
            LDEBUG << "====== PUBLISHING NEW VOLTAGE " << complexVoltage << " " << voltUnit << " at bus " << bus_num[bus_ind];
            if (solved_opf) {
              LDEBUG << "====== MARKET CYCLE FINISHED WITH PUBLISHED LMP " << realLMP[bus_ind] << " $/kWh, FOR " << " at bus " << bus_num[bus_ind];
            }
          }
          
          // Saving the data of each time when at least one message had been exchanged to the corresponding CSV file for each distribution network/substation
          /* Turning this off for a while
           
          for (int bus_ind = 0; bus_ind < nFNCSbuses; bus_ind++){
            ofstream subst_output_file(subst_output_file_name[bus_ind], ios::app);
            for (int ind = 1; ind <= nbrows; ind++) {
              if ((int) mwBusOut.Get(2, ind, 1) == bus_num[bus_ind]) {
                subst_output_file << curr_time << "," << (double) mwBusOut.Get(2, ind, 3) << "," << (double) mwBusOut.Get(2, ind, 4) << ", " << sendValReal[bus_ind] << ", " << sendValIm[bus_ind] <<  ", " << realLMP[bus_ind] << ", " << imagLMP[bus_ind] << endl;
              }
            }
          }

          for (int gen_ind = 0; gen_ind < sizeof(offline_gen_ind)/sizeof(offline_gen_ind[0]); gen_ind++){ // in C indexes start from 0, but from MATLAB variables index needs to start from 1; these refer only to the generators that might get offlinec
            ofstream gen_output_file(gen_output_file_name[gen_ind], ios::app);
            gen_output_file << curr_time << "," << (int) mwGenOut.Get(2, offline_gen_ind[gen_ind], 8) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 9) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 10) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 2) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 4) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 5) << "," << (double) mwGenOut.Get(2, offline_gen_ind[gen_ind], 3) << endl;
          }
          */
        tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        tElapsed = tAfter - tBefore;
        tHours = tElapsed / 3600000;
        tMins = (tElapsed - tHours * 3600000) / 60000;
        tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
        tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
        LMACTIME << "Calculating and publishing voltages and/or prices took  " << tHours << " hours, "\
                 << tMins << " minutes, "\
                 << tSecs << " seconds, and "\
                 << tMSecs << " msecs.\n" << "=========================================================";
        }
        tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        // ================== LOAD/DISTRIBUTION BUS VALUES METRICS =======================================
        for (int busInd = 1; busInd <= nbrows; busInd ++) { // need to find the corresponding bus row in the BUS matrix
          if ((int) mwBusOut.Get(2, busInd, 2) != 2) { // collecting the metrics for all load buses, that is all PQ buses in bus matrix
            mpLoadBusValues.clearBusValues();
            mpLoadBusValues.setBusID((int) mwBusOut.Get(2, busInd, 1));
            mpLoadBusValues.setBusLAMP((double) mwBusOut.Get(2, busInd, 14));
            mpLoadBusValues.setBusLAMQ((double) mwBusOut.Get(2, busInd, 15));
            mpLoadBusValues.setBusPD((double) mwBusOut.Get(2, busInd, 3));
            mpLoadBusValues.setBusQD((double) mwBusOut.Get(2, busInd, 4));
            mpLoadBusValues.setBusVA((double) mwBusOut.Get(2, busInd, 9));
            mpLoadBusValues.setBusVM((double) mwBusOut.Get(2, busInd, 8));
            mpLoadBusValues.setBusVMAX((double) mwBusOut.Get(2, busInd, 12));
            mpLoadBusValues.setBusVMIN((double) mwBusOut.Get(2, busInd, 13));
            mpLoadMetrics.setBusValues(mpLoadBusValues);
          }
        }
        tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        tElapsed = tAfter - tBefore;
        tHours = tElapsed / 3600000;
        tMins = (tElapsed - tHours * 3600000) / 60000;
        tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
        tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
        LMACTIME << "Load metrics setup took  " << tHours << " hours, "\
                 << tMins << " minutes, "\
                 << tSecs << " seconds, and "\
                 << tMSecs << " msecs.\n" << "=========================================================";
        
        // ============ GENERATOR METRICS ======================
        tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        for (int genInd = 1; genInd <= ngrows; genInd++) { // indexing in a MATLAB matrix structure
          if ((double) mwGenOut.Get(2, genInd, 9) > 0 && (double) mwGenOut.Get(2, genInd, 10) >= 0) { // only for generator, and not dispatchable loads (negative generators)
            mpGeneratorBusValues.clearBusValues();
            mpGeneratorBusValues.setGenIndex((int) genInd);
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
        tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        tElapsed = tAfter - tBefore;
        tHours = tElapsed / 3600000;
        tMins = (tElapsed - tHours * 3600000) / 60000;
        tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
        tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
        LMACTIME << "Generator metrics setup took  " << tHours << " hours, "\
                 << tMins << " minutes, "\
                 << tSecs << " seconds, and "\
                 << tMSecs << " msecs.\n" << "=========================================================";
          
        // Line Below is from when running off-line, without FNCS
        // curr_time = curr_time + 1;
        tBefore = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        if (!fncs_time_request) {
          next_FNCS_time = fncs::time_request(next_OPF_time);
          //cout << "this was not an OPF round" << endl;
        }
        else {
          next_OPF_time = min(curr_time + marketTime, simStopTime);
          next_FNCS_time = fncs::time_request(next_OPF_time);
          //cout << "this was an OPF round" << endl;
        }
        tAfter = ((float) clock() / CLOCKS_PER_SEC) * 1000;
        tElapsed = tAfter - tBefore;
        tHours = tElapsed / 3600000;
        tMins = (tElapsed - tHours * 3600000) / 60000;
        tSecs = (tElapsed - tHours * 3600000 - tMins * 60000) / 1000;
        tMSecs = tElapsed - tHours * 3600000 - tMins * 60000 - tSecs * 1000;
        LMACTIME << "FNCS time request took  " << tHours << " hours, "\
                 << tMins << " minutes, "\
                 << tSecs << " seconds, and "\
                 << tMSecs << " msecs.\n" << "=========================================================";
        LINFO << "*************************** TIMING TIMING TIMING *********************************" ;
        LINFO << "current time = " << curr_time;
        LINFO << "next opf time = " << next_OPF_time;
        LINFO << "GLD published, so MATPOWER jump at next time = " << next_FNCS_time;
        LINFO << "**********************************************************************************" ;  
        
        //curr_time = next_FNCS_time;
        
        // setting current time for metric files
        mpLoadMetrics.setCurrentTimeBusValues(curr_time);
        mpGeneratorMetrics.setCurrentTimeBusValues(curr_time);
      }while(curr_time < simStopTime);
      
      LINFO << "Let's write some MATPOWER metrics in JSON format.";
      mpLoadMetrics.jsonSave(loadMetricsFile);
      mpDispLoadMetrics.jsonSave(dispLoadMetricsFile);
      mpGeneratorMetrics.jsonSave(generatorMetricsFile);
        }
    catch (const mwException& e) {
      LERROR << e.what();
      LERROR << "Caught an error!!!";
      LERROR << "================ FNCS FATALITY !!!!! ==================";
      fncs::die();
      return -2;
        }
    catch (...) {
      LERROR << "Unexpected error thrown";
      LERROR << "================ FNCS FATALITY !!!!! ==================";
      fncs::die();
      return -3;
        }
    
    LINFO << "Terminating Matlab libraries";   
    libMATPOWERTerminate();
  }
  
  LINFO << "Terminating Matlab Compiler Runtime";
  mclTerminateApplication();
  LINFO << "Terminating FNCS";
  fncs::finalize();
  return 0;
}

/* ==================================================================================================================
====================== MAIN PART ====================================================================================
===================================================================================================================*/
int main(int argc, char **argv) {
  // Setting up the logger based on user input
  char *log_level_export = NULL;
  log_level_export = getenv("MATPOWER_LOG_LEVEL");
  
  if (!log_level_export) {
    loglevel = logWARNING; 
  } else if (strcmp(log_level_export,"ERROR") == 0) {
    loglevel = logERROR;
  } else if (strcmp(log_level_export,"WARNING") == 0) {
    loglevel = logWARNING;
  } else if (strcmp(log_level_export,"INFO") == 0) {
    loglevel = logINFO;
  } else if (strcmp(log_level_export, "LMACTIME") == 0) {
    loglevel = logMACTIME;
  } else if (strcmp(log_level_export,"DEBUG") == 0) {
    loglevel = logDEBUG;
  } else if (strcmp(log_level_export,"DEBUG1") == 0) {
    loglevel = logDEBUG1;
  } else if (strcmp(log_level_export,"DEBUG2") == 0) {
    loglevel = logDEBUG2;
  } else if (strcmp(log_level_export,"DEBUG3") == 0) {
    loglevel = logDEBUG3;
  } else if (strcmp(log_level_export,"DEBUG4") == 0) {
    loglevel = logDEBUG4;
  }
  
  // increase the possible stack size for the application
  const rlim_t kStackSize = 1024L * 1024L * 1024L;   // min stack size = 1024 Mb
    struct rlimit rl;
    int result;

    result = getrlimit(RLIMIT_STACK, &rl);
    if (result == 0)
    {
        if (rl.rlim_cur < kStackSize)
        {
            rl.rlim_cur = kStackSize;
            result = setrlimit(RLIMIT_STACK, &rl);
            if (result != 0)
            {
                LERROR << "setrlimit returned result = " << result ;
            }
        }
    }  
  
  if (argc < 10 || argc >= 11){
    LERROR << "========================== ERROR ================================================";
    LERROR << "Nine arguments need to be provided: MATPOWER case file, real load profile file, ";
    LERROR << "reactive load profile file, simulation stop time (s), the market clear time (s), ";
    LERROR << "the presumed starting time, and the JSON output metric files.";
    LERROR << "There were " << argc << " arguments given!";
    LERROR << "=================================================================================";
    exit(EXIT_FAILURE);
  }
  mclmcrInitialize();
  LINFO << "Running process -> " << argv[0] ;
  LINFO << "with MATPOWER case -> " << argv[1];
  LINFO << "and daily real load profile -> " << argv[2];
  LINFO << "and daily reactive load profile -> " << argv[3];
  LINFO << "for a market clearing time of " << argv[5] << " seconds.";
  LINFO << "and a total simulation time of " << argv[4] << " seconds.";  
  LINFO << "starting on " << argv[6] << ", ";
  LINFO << "with load metrics in JSON format in file -> " << argv[7] << ", ";
  LINFO << "dispatchable load (as negative generation) metrics in JSON format in file -> " << argv[8] << ", and ";
  LINFO << "generator metrics in JSON format in file -> " << argv[9];  
   
  return mclRunMain((mclMainFcnType) run_main, argc, (const char**) argv);
}
