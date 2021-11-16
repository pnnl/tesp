// Copyright (C) 2021 Battelle Memorial Institute
// file: helicstest.java


import com.java.helics.helics;

public class helicstest {
    public static void main(String[] args) {
	System.loadLibrary ("JNIhelics");
	System.out.println ("HELICS Version: " + helics.helicsGetVersion());
    }
}

