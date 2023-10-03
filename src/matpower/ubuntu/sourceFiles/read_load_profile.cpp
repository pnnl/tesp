/*
==========================================================================================
Copyright (c) 2013-2023 Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
==========================================================================================
Launching the MATPOWER Optimal Power Flow solver
  - MATPOWER OPF resides as a shared object in libopf.so, after being compiled on a computer with MATLAB isntalled.
  - Running the MATPOWER OPF requires that at least Matlab Compiler Runtime (downloaded for free from MATHWORKS webpage) is installed.
  - The code below reads the data file that resides in a .m file (the MATPOWER case file).
  - It creates the data structure needed by the OPF solver, calls the solver, and returns whatever it is desired.
  - Files needed for deployment (for this case, at least, in order to be able to compile): start_MATPOWER.cpp, libopf.h, libopf.so, libmpoption.so, libmpoption.h, case9.m, matpowerintegrator.h, matpowerintegrator.c, and the newly added, librunpf.so, librunpf.h, librunopf.so, librunopf.h.
Update: 07/02/2014
   Purpose: Modified the read load profile function in read_load_profile.cpp, to be able to read as many profiles as neccessary, depending on how many substations I have.
            Basically, the load profile data comes into a file containing 288 values per row (every 5-minute data for 24-hours), and a number of rows greater than or equal to the number of substations.
Update: 07/02/2014
   Purpose: Modified the read load profile function in read_load_profile.cpp, to include some additional error information if the load fails. Also updated to include new logging features.
*/
#include<stdio.h>
#include<math.h>
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <sstream>
using namespace std;

#include "logging.hpp"

void read_load_profile(char *file_name, double load_profile[][288], int subst_num)
{
	ifstream data_file(file_name, ios::in);
	try {
	   if (data_file.is_open()){
			LDEBUG << "======== Starting reading the load profile data from file " << file_name << " for  " << subst_num << " substation(s)." ;
			
			for (int j = 0; j < subst_num; j++){
				for (int i = 0; i < 288; i++){
					if (!data_file.eof()) {
						data_file >> load_profile[j][i]; // extracts and parses characters sequentially from the stream created from the data file, 
														 // to interpret them as the representation of a value of the proper type, given by the type of load_profile, that is float
					}
					else {
						LDEBUG4 << "Row " << j+1 << " column " << i+1 ;
						throw 225;
					}
				}
			} 

			if (data_file.eof()) {
				LDEBUG << "Reached the end of the file!!!!!!!!" ;
				LDEBUG << "======== Done reading the load profile file!!!!!!!!! ====================" ;
				data_file.close();
			}	
			else {
				data_file.close();
				throw 226;
			}
			
	   }
	   else {
		  throw 227;	  
	   }
	}
   catch (int e) {
		if (e == 225) {
			LERROR << "Reached end of file too early" ;
		}
		else if (e == 226) {
			LERROR << "Did not reach end of file after completing load profiles" ;	
		}
		else if (e == 227) {
			LERROR << "Unable to open load profile file." ;	
		}
		else {
			LERROR << "Unknown error while reading the load profiles!!!!!!!!" ;
		}
	    
	 exit(EXIT_FAILURE);
   }
} // END OF get_load_profile function
