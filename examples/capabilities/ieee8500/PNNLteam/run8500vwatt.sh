#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: run8500vwatt.sh

(exec gridlabd -D METRICS_ROOT=inv8500_vwatt -D INV_MODE=VOLT_WATT inv8500.glm &> gridlabd_vwatt.log &)
