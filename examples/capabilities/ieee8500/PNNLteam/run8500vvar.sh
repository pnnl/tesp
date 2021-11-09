#!/bin/bash

(exec gridlabd -D METRICS_ROOT=inv8500vvar -D INV_MODE=VOLT_VAR inv8500.glm &> gridlabd_vvar.log &)
