#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

cd "${TESPDIR}/examples" || exit

clean_outputs
exec python3 autotest.py &> autotest.log &
#exec python3 autotest.py FNCS &> autotest_f.log &
