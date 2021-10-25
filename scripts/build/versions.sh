#!/bin/bash

echo 
FILE="${INSTALL}/bin/fncs_broker"
if [[ -f "$FILE" ]]; then
  echo FNCS broker installed
else
  echo FNCS borker not installed
fi

echo 
echo Helics $(helics_broker --version)

echo 
gridlabd --version

echo 
energyplus --version

echo 
FILE="${INSTDIR}/bin/ns3-dev-bench-simulator-optimized"
if [[ -f "$FILE" ]]; then
  echo NS-3 installed
else
  echo NS-3 not installed
fi

echo 
ipopt --version