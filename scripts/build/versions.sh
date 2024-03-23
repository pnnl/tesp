#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tespEnv in the $HOME directory"
  echo "Run 'source tespEnv' in that same directory"
  exit
fi

echo
echo "Grid applications software installed are:"
echo
echo "TESP $(cat ${TESPDIR}/src/tesp_support/version)"

FILE="${INSTDIR}/bin/fncs_broker"
if [[ -f "${FILE}" ]]; then
  echo FNCS installed
else
  echo FNCS not installed
fi

echo "HELICS $(helics_broker --version)"

echo $("${BUILD_DIR}/test_helics_java")

gridlabd --version

energyplus --version

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

ipopt --version
