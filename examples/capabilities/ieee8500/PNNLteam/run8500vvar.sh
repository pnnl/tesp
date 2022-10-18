#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run8500vvar.sh

(exec gridlabd -D METRICS_ROOT=inv8500_vvar -D INV_MODE=VOLT_VAR inv8500.glm &> gridlabd_vvar.log &)
