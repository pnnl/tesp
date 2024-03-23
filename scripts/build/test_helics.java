// Copyright (C) 2021-2023 Battelle Memorial Institute
// file: test_helics.java


import com.java.helics.helics;

public class test_helics {
    public static void main(String[] args) {
    	System.loadLibrary ("helicsJava");
    	System.out.println ("HELICS Java, " + helics.helicsGetVersion());
    }
}