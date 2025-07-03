#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

echo
echo "Grid applications software installed are:"
echo

FILE="${INSTDIR}/bin/fncs_broker"
if [[ -f "${FILE}" ]]; then
  echo FNCS installed
else
  echo FNCS not installed
fi

if command -v helics_broker > /dev/null; then
  echo "HELICS $(helics_broker --version)"
else
  echo HELICS not installed
fi

"${BUILD_DIR}/test_helics_java.sh"

if command -v gridlabd > /dev/null; then
  gridlabd --version
else
  echo GridLabD not installed
fi

if command -v energyplus> /dev/null; then
  energyplus --version
else
  echo Energyplus not installed
fi

message="NS-3 not installed"
for file in "${INSTDIR}"/bin/ns3-dev-* ; do
  lst=( ${file// / } )
  for a in ${lst} ; do
    if [[ -f "${a}" ]]; then
      message="NS-3 installed"
      break
    fi
  done
done
echo "${message}"

if command -v ipopt > /dev/null; then
  ipopt --version
else
  echo ipopt not installed
fi
