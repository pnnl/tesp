#!/bin/bash

ver=$(fncs_broker)
if [[ ${ver} == "ERROR: missing command line arg for number of simulators" ]]; then
  echo FNCS installed
else
  echo FNCS not installed
fi

echo Helics $(helics_broker --version)
gridlabd --version
energyplus --version
echo NS3 installed, $(ns3-dev-aodv-optimized --version)
ipopt --version