#!/bin/bash

# Copyright (c) 2021-2025 Battelle Memorial Institute
# file: run.py

python3 feeder_demo.py > test_feeder.log
gridlabd -D METRICS_FILE=test_ test.glm > test_glm.log
