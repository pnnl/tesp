#!/bin/bash
#(export FNCS_BROKER="tcp://*:5570" && export FNCS_LOG_LEVEL=DEBUG4 && export FNCS_LOG_STDOUT=yes && export FNCS_TRACE=yes && exec fncs_broker 5 &> broker.log &)
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 4 &> broker.log &)
(export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 2d tracer.out &> tracer.log &)
(exec ./launch_0_agents.sh &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py TE_Challenge0 &> pypower.log &)
