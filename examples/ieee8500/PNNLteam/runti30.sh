#!/bin/bash
(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> brokerti30.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec gridlabd -D USE_FNCS invti30.glm &> gridlabdti30.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec fncs_player 48h prices.player &> playerti30.log &)
(export FNCS_CONFIG_FILE=invti30_precool.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python -c "import tesp_support.api as tesp;tesp.precool_loop(48,'invti30')" &> precoolti30.log &)

