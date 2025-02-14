#!/bin/bash

# Copyright (C) 2021-2024 Battelle Memorial Institute
# file: run.py

python3 -c "import sys; sys.path.insert(1,'.'); import gld_modifier_demo; gld_modifier_demo.demo(False)" > gld_modifier_demo.log
gridlabd R1-12.47-2_out.glm > gridlabd.log
