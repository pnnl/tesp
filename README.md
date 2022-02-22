# Transactive Energy Simulation Platform (TESP)

Copyright (c) 2017-2022, Battelle Memorial Institute

Documentation: http://tesp.readthedocs.io

License: https://github.com/pnnl/tesp/blob/main/LICENSE

TESP provides a set of simulation tools and example implementations of transactive systems to provide a means of more easily developing and evaluating transactive systems. TESP utilizes the HELICS co-simulation framework to enable coordination between a number of simulation tools: GridLAB-D, EnergyPlus v9.3, AMES/PSST, PYPOWER and ns-3 (optimized build with logging enabled). TESP comes with several test cases, including the NIST TE Challenge 2, the SGIP use case 1, and an 8-bus test system for ERCOT. There are examples of the double-auction
real-time market in real-time and day-ahead modes, and a transactive consensus mechanism for large buildings. The intended use case for TESP is to focus on the development and testing
of transactive control agents, without having to build up a large system simulation infrastructure. There are sample agents provided in Python 3.6+, Java 11+, and C/C++.

TESP runs natively on Linux and can be installed by following a simple process [detailed in the documentation](https://tesp.readthedocs.io/en/latest/Installing_Building_TESP.html). The rest of the documentation can be found at [TESP's ReadTheDocs site](https://tesp.readthedocs.io/en/latest/index.html).


Change log:

- v0.1.2  Patch for tape shield / concentric neutral 
          cables with separate neutral conductor.
- v0.3.0  Refactored agent classes for DSO+T study
- v0.9.5  HELICS, MATPOWER/MOST, ERCOT and E+ 9.3 examples
- v1.0.0  Tested on Ubuntu 18.04 LTS and 20.04 LTS
- v1.0.1  Updates to consensus mechanism, HELICS 2.6.1
- v1.0.2  ns-3 has optimized build with logging enabled
- v1.1    Updated installation method and documentation
