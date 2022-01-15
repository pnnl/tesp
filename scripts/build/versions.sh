#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

echo
echo "++++++++++++++  Compiling and Installing TESP software is complete!  ++++++++++++++"
echo

FILE="${INSTDIR}/bin/fncs_broker"
if [[ -f "${FILE}" ]]; then
  echo FNCS, installed
else
  echo FNCS, not installed
fi

echo 
echo "HELICS, $(helics_broker --version)"

echo
echo $(test_helics_java)

echo 
gridlabd --version

echo 
energyplus --version

echo
message="NS-3 not installed"
for f in ${INSTDIR}/bin/ns3*
do
  if [ -f "$f" ]; then
    message="NS-3, installed"
    break
  fi
done
echo "${message}"

echo
ipopt --version

echo
echo "++++++++++++++  TESP versions has been installed! That's all folks!  ++++++++++++++"
echo