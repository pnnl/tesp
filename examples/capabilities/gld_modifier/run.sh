#!/bin/bash

# Copyright (C) 2021-2024 Battelle Memorial Institute
# file: run.py

(exec python3 -c "import sys; sys.path.insert(1,'.'); import gld_modifier_demo; gld_modifier_demo.demo(False)" > feeder_demo.log)
(exec gridlabd R1-12.47-2_out.glm > gridlabd.log)
