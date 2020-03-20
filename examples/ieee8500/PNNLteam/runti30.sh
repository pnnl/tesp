#!/bin/bash
declare -r TESP_SUPPORT=$TESP_INSTALL/share/support
declare -r SCHED_PATH=$TESP_SUPPORT/schedules

(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> brokerti30.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec gridlabd -D SCHED_PATH=$SCHED_PATH -D INV_MODE=VOLT_VAR -D USE_FNCS invti30.glm &> gridlabdti30.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec fncs_player 48h prices.player &> playerti30.log &)
(export FNCS_CONFIG_FILE=invti30_precool.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.precool_loop(48,'invti30','invti30')" &> precoolti30.log &)

