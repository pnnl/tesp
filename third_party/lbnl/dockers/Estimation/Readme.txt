This folder contains

- Dockerfile which contains installation for E+, MPCPy and all dependencies
- makefile for installing the image
- Dockerfile.template which is used to generate the Dockerfile 
- runContainer.sh which is used for running the estimation parameter script.

The folder develop/w_energyplus contains the folder
- models --> A library of reduced order model library (TestModels.mo) as well as the BESTEST E+ model for case 600FF
- parameters --> Parameters which are used for the parameter estimation
- resources --> resources files for parameter estimation
