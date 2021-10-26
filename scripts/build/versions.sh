#!/bin/bash

echo
echo "++++++++++++++  Compiling and Installing TESP software is complete!  ++++++++++++++"
echo

FILE="${INSTDIR}/bin/fncs_broker"
if [[ -f "$FILE" ]]; then
  echo FNCS broker installed
else
  echo FNCS broker not installed
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

echo
echo "++++++++++++++  TESP versions has been installed! That's all folks!  ++++++++++++++"
echo