#!/bin/bash

(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 33 &> broker.log &)
(export FNCS_FATAL=YES && exec gridlabd TE_Challenge.glm &> gridlabd.log &)
# launches 31 agents for the market and houses
(exec ./launch_TE_Challenge_agents.sh &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py TE_Challenge "2013-07-01 00:00:00" 86400 300 &> pypower.log &)
