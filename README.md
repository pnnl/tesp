# Transactive Energy Simulation Platform (TESP)

Copyright (c) 2017-2023 Battelle Memorial Institute

Documentation: http://tesp.readthedocs.io

License: https://github.com/pnnl/tesp/blob/main/LICENSE

TESP provides a set of simulation tools and example implementations of transactive systems to provide a means of more easily developing and evaluating transactive systems. TESP utilizes the HELICS co-simulation framework to enable coordination between a number of simulation tools: GridLAB-D, EnergyPlus v9.3, AMES/PSST, PYPOWER and ns-3 (optimized build with logging enabled). TESP comes with several test cases, including the NIST TE Challenge 2, the SGIP use case 1, and an 8-bus test system for ERCOT. There are examples of the double-auction
real-time market in real-time and day-ahead modes, and a transactive consensus mechanism for large buildings. The intended use case for TESP is to focus on the development and testing
of transactive control agents, without having to build up a large system simulation infrastructure. There are sample agents provided in Python 3.6+, Java 11+, and C/C++.

TESP runs natively on Linux and can be installed by following a simple process [detailed in the documentation](https://tesp.readthedocs.io/en/latest/Installing_Building_TESP.html). The rest of the documentation can be found at [TESP's ReadTheDocs site](https://tesp.readthedocs.io/en/latest/index.html).


Change log:

- v0.1.2  Patch for tape shield / concentric neutral cables with separate neutral conductor.
- v0.3.0  Refactored agent classes for DSO+T study.
- v0.9.5  HELICS, MATPOWER/MOST, ERCOT and E+ 9.3 examples.
- v1.0.0  There are examples of the double-auction real-time market in real-time and day-ahead modes, and a transactive consensus mechanism for large buildings. The intended use case for TESP is to focus on the development and testing of transactive control agents, without having to build up a large system simulation infrastructure. There are sample agents provided in Python 3.6+, Java 11+, and C/C++.
- v1.1.1  Updated installation method and documentation. Patches for SGIP1, consensus mechanism, standalone house generator. Updated examples from Helic2.8 to Helics3.0. Added DSO Stub case for agent testing.
- v1.1.3  Updated some documentation and build patches.
- v1.1.4  Updates to auto testing and minors bug fixes for Comm cases using HELICS3.0.
- v1.1.5  Updates to auto testing and minors bug fixes for install and a better loadshed example.
- v1.2.0  Updates to auto testing and minors bug fixes. Version changes for HELICS 3.3, GridLAB-D 5.0. Reorganize environment and updated documentation. Add more loadshed N3 examples.
- v1.2.1  Fixed python shell files, fixed complex python to use helics complex.
- v1.2.2  Fixed the installation for Ubuntu 22.04.
- v1.3.0  Refactor the TESP PyPI api. Upgrade all models(GridLAB-D, EnergyPlus, NS3) to work with HELICS 3.4. Add modifier.py for GridLAB-D models.
- v1.3.2  Updated model and modifier for GridLAB-D models, added readme for GLM modifier and Store examples.
- v1.3.3  Add tesp_component download in tesp_support pypi, change directory structure. Add dockerfile for each module getting ready for dockerize COSU Simulations