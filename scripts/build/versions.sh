#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

echo
echo "TESP software modules installed are:"
echo
echo "TESP $(cat ${TESPDIR}/scripts/version)"

FILE="${INSTDIR}/bin/fncs_broker"
if [[ -f "${FILE}" ]]; then
  echo FNCS installed
else
  echo FNCS not installed
fi

echo "HELICS $(helics_broker --version)"

echo $("${TESPBUILD}/test_helics_java")

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
