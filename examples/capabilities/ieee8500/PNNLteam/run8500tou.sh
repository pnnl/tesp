#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run85000tou.sh

(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker8500_tou.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec gridlabd -D USE_FNCS -D INV_MODE=CONSTANT_PF -D METRICS_ROOT=inv8500_tou inv8500.glm &> gridlabd8500_tou.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec fncs_player 24h prices.player &> player8500_tou.log &)
(export FNCS_CONFIG_FILE=inv8500_precool.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.precool_loop(24,'inv8500_tou','inv8500',response='Price')" &> precool8500_tou.log &)
