#!/bin/bash

# Copyright (C) 2021-2024 Battelle Memorial Institute
# file: run.py

python3 feeder_demo.py > feeder_demo.log
gridlabd test.glm > test.log
