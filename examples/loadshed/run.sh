#!/bin/bash
(export FNCS_TRACE=yes && export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
(export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec gridlabd loadshed.glm &> gridlabd.log &)
(export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec fncs_player 6h loadshed.player &> player.log &)
(export FNCS_CONFIG_FILE=loadshed.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python loadshed.py 21600 &> loadshed.log &)

