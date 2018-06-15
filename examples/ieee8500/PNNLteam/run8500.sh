#!/bin/bash
(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
(export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec gridlabd -D USE_FNCS inv8500.glm &> gridlabd.log &)
(export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec fncs_player 24h prices.player &> player.log &)
(export FNCS_CONFIG_FILE=inv8500_precool.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python -c "import tesp_support.api as tesp;tesp.precool_loop(24,'inv8500')" &> precool.log &)

