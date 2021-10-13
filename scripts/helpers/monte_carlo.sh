#!/bin/bash
if [[ -z $1 ]]; then
  exit
fi
python3 "${TESPDIR}/scripts/helpers/monte_carlo.py" $1
