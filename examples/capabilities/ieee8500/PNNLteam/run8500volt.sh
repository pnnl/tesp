#!/bin/bash
(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec gridlabd -D USE_FNCS -D INV_MODE=CONSTANT_PF -D METRICS_ROOT=inv8500volt inv8500.glm &> gridlabd_volt.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec fncs_player 24h prices.player &> player.log &)
(export FNCS_CONFIG_FILE=inv8500_precool.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.precool_loop(24,'inv8500volt','inv8500',response='Voltage')" &> precool_volt.log &)

