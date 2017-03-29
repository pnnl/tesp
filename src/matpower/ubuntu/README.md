# How to Install and Run MATPOWER with FNCS #

*Author: Laurentiu Dan Marinovici*
***************************************

If MATPOWER is one of the simulators used as part of the FNCS (**F**ramework for **N**etwork **C**o-**S**imulation) environment, the following should be considered.

## Installation guide - Linux ##

In order to be able to integrate MATPOWER under Linux in FNCS, without the need of a MathWorks MATLAB full license, the free MATLAB Runtime (MCR) needs to be installed. All the MCR versions can be downloaded [here][linkMCR]. The installed MCR version needs to be the same as the MATLAB version under which the original MATPOWER code has been compiled in, and built into the deployable files *``libMATPOWER.h``* and *``libMATPOWER.so``* under *``./TESP/repos/rev0/browse/code/matpower``.

To access the MATPOWER functions and pass data back and forth from MATPOWER (transmission, generation, wholesale market simulator) to GridLAB-D (distribution simulator) through FNCS, a C++ wrapper has been written, consisting of:
  * *``start_MATPOWER.cpp``* - the main wrapper around the MATPOWER functions that establishes the communication between MATPOWER and FNCS, arranges data according to the type MATLAB requires it or FNCS needs it to make it available to other simulators;
  * *``matpowerintegrator.h``* and *``matpowerintegrator.cpp``* - define the functions that integrate MATPOWER within the FNCS environment;
  * *``read_input_data.h``* - includes all definitions of the functions that read and parse the input data, both the load profile that resides in a text file (created in MATLAB from an experimental set of data meant to model a standard daily load shape) and the MATPOWER model in order to construct the correct C++ counterparts for the matrices needed to solve the power flow;
  * *``read_loap_profile.cpp``* - reads in an a-priori built load shape meant to align to a standard daily residential power consumption initialized to the values corresponding to the transmission structure of the MATPOWER model, for the location where distribution models are connected to;
  * *``read_model_dim.cpp``* - reads in the MATPOWER model dimensions in order to be able to allocate the correct memory in the C++ wrapper (Observation. I went this route because I found it hard to make it work with dynamic allocation of memory);
  * *``read_model_data.cpp``* - reads the actual data that describes the transmission network in MATPOWER;
  * *``Makefile``* - the script that guides the make utility to choose the appropriate program files that are to be compiled and linked together, also specifying the paths to MCR and installation (should be modified accordingly)

## Running guide - Linux ##

To run MATPOWER simulator as part of the FNCS environment in Linux, use the ``make`` and ``make install`` utilities to compile the wrapper and deploy the executable files and the shared libraries to the installation folder. However, first, check that the paths in the ``Makefile`` are set correctly. Also, copy the MATPOWER model file and the load shape profile to the installation folder prior to running the simulation. Currently, the way of starting the simulation is through the command line

```
./start_MATPOWER <MATPOWER case file> <real power demand file> <running time in seconds followed by s>
```
, i.e.
```
./start_MATPOWER case9.m real_power_demand_case9_T.txt 1000s
```

## Installation guide - Windows ##

So far (that is by 2016/12/13), there haven't been any simulations done involving GridLAB-D and MATPOWER within FNCS environment in Windows. However, the following issues need to be addressed in order to be ale to do accomplish it.

<ol>
  <li>Install the corresponding MCR for Windows.</li>
  <li>Compile MATPOWER on a Windows platform with MATLAB installed, and including the compiler toolbox.</li>
  <li>Compile the C++ wrapper with FNCS.</li>
</ol>

[linkMCR]: https://www.mathworks.com/products/compiler/mcr.html