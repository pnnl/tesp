#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run85000base.sh

gridlabd -D METRICS_ROOT=inv8500base -D INV_MODE=CONSTANT_PF inv8500.glm > gridlabd_base.log
