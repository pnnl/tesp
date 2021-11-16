// Copyright (C) 2021 Battelle Memorial Institute
// file: helicsshed.java


import com.java.helics.helics;
import com.java.helics.*;

public class helicshed {
    public static void main(String[] args) {
	System.loadLibrary ("helicsJava");
	System.out.println ("HELICS Version: " + helics.helicsGetVersion());
	SWIGTYPE_p_void fi = helics.helicsCreateFederateInfo();
	helics.helicsFederateInfoSetCoreTypeFromString (fi, "zmq");
	helics.helicsFederateInfoSetCoreInitString (fi, "--federates=1");
    	helics.helicsFederateInfoSetTimeProperty (fi, helics_properties.helics_property_time_delta.swigValue(), 1.0);
    	SWIGTYPE_p_void fed = helics.helicsCreateCombinationFederate ("shedfed", fi);

	SWIGTYPE_p_void pubid = helics.helicsFederateRegisterGlobalPublication (fed, 
		"loadshed/sw_status", helics_data_type.helics_data_type_string, "");

	helics.helicsFederateEnterInitializingMode (fed);
	helics.helicsFederateEnterExecutingMode (fed);

	int [][] switchings = {{0,1},{1800,0},{5400,1},{16200,0},{19800,1}};

    	int hours = 6;
    	int seconds = 60 * 60 * hours;
    	double grantedtime = -1;
    	for (int i = 0; i < switchings.length; i++) {
            int t = switchings[i][0];
            String val = Integer.toString (switchings[i][1]);
            System.out.println ("Requesting " + Integer.toString (t));
            while (grantedtime < t) {
                grantedtime = helics.helicsFederateRequestTime(fed, t);
	    }
	    System.out.println ("Sending " + val);
            helics.helicsPublicationPublishString (pubid, val);
	}

	helics.helicsFederateFinalize (fed);
	helics.helicsCloseLibrary ();
    }
}

