#!/bin/bash
if [[ -z $1 ]]; then
  exit
fi
python3 "${TESPDIR}/scripts/helpers/case.py" $1
