#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

cd "${TESPDIR}/doc" || exit
if [[ $1 == "clean" ]]; then
  make clean
fi

./make_apidoc.sh
make html