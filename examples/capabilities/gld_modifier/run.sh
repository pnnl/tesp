#!/bin/bash

# Copyright (C) 2021-2024 Battelle Memorial Institute
# file: run.py

(exec python3 feeder_generator_demo.py &)
(exec gridlabd R1-12.47-2_output.glm)
