#!/bin/bash

declare -r TESP_SUPPORT=$TESP_INSTALL/share/support
#declare -r SCHED_PATH=$TESP_SUPPORT/schedules
declare -r TMY_PATH=$TESP_SUPPORT/weather

export SCHED_PATH=$TESP_SUPPORT/schedules

python3 WriteHouses.py
python3 -c "import tesp_support.api as tesp;tesp.glm_dict('test_houses')"
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D TMY_PATH=$TMY_PATH -D METRICS_FILE=test_houses_metrics.json test_houses.glm &> gridlabd.log &)

