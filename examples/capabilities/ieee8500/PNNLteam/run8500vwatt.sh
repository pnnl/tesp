#!/bin/bash

(exec gridlabd -D METRICS_ROOT=inv8500vwatt -D INV_MODE=VOLT_WATT inv8500.glm &> gridlabd_vwatt.log &)
