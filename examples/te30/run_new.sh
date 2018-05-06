#!/bin/bash
#(export FNCS_TRACE=yes && export FNCS_LOG_STDOUT=yes && export FNCS_LOG_LEVEL=DEBUG4 && exec fncs_broker 3 &> broker.log &)
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 3 &> broker.log &)
(exec ./launch_TE_Challenge_auction.sh &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py TE_Challenge &> pypower.log &)
