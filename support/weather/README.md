# TESP Weather Files

This directory contains 12 typical meteorological year version 3 (TMY3) weather files for 
use with TESP. They sample all 6 climate regions as defined for PNNL's taxonomy feeders:

1. Region 1 (Temperate) CA-Los Angeles and CA-San Francisco
1. Region 2 (Cold) IL-Chicago
1. Region 3 (Hot and Arid) AZ-Phoenix, AZ-Tucson and TX-El Paso
1. Region 4 (Hot and Cold) TN-Nashville, TX-Wichita Falls
1. Region 5 (Hot and Humid) FL-Miami, TX-Houston
1. Region 6 (Tropical) HI-Honolulu

These samples were chosen to include the same default weather locations available 
in earlier versions of PNNL's feeder generator, the NIST TE Challenge, the 2018 
transactive systems study set in Texas, and other PNNL research projects. 
WA-Yakima is also provided to represent PNNL's main campus; nominally, Yakima is 
located in Region 2, but it also displays characteristics of Region 3.

There are more than 1000 other TMY3 files available at https://sourceforge.net/p/gridlab-d/code/HEAD/tree/data/US/tmy3/US.zip.
To use any of those TMY3 files, or TMY3 files from another source, download or copy
the desired TMY3 files to this directory.

EnergyPlus uses TMY2 data. This directory includes a converter from TMY2 to TMY3, so
that both GridLAB-D and EnergyPlus will use the same weather data when running
under TESP.


    gcc -o Tmy3toTMY2_ansi TMY3toTMY2_ansi.c
    ./Tmy3toTMY2_ansi FL-Miami_Intl_Ap.tmy3 > FL-Miami_Intl_Ap.tmy2
    python TMY2EPW.py FL-Miami_Intl_Ap.tmy2

Copyright (c) 2017-2018, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE


