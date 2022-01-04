#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run.py

SCHED_PATH=$TESPDIR/data/schedules
TMY_PATH=$TESPDIR/data/weather

python3 WriteHouses.py
python3 -c "import tesp_support.api as tesp;tesp.glm_dict('test_houses')"
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D TMY_PATH=$TMY_PATH -D METRICS_FILE=test_houses_metrics.json test_houses.glm &> gridlabd.log &)
