#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

cd "${TESPDIR}/doc" || exit
if [[ $1 == "clean" ]]; then
  make clean
fi

./make_apidoc.sh
make html