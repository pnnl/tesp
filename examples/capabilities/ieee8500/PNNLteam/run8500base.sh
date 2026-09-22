#!/bin/bash

# Copyright (c) 2021-2025 Battelle Memorial Institute
# file: run85000base.sh

gridlabd -D METRICS_ROOT=inv8500_base -D INV_MODE=CONSTANT_PF inv8500.glm > gridlabd8500_base.log
