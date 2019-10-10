#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && export FNCS_LOG_STDOUT=yes && exec fncs_broker 2 &> broker.log &)
(export FNCS_CONFIG_FILE=dso8.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 fncsDSO.py &> dso8.log &)
#(export FNCS_CONFIG_FILE=tso8stub.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 ../fncsTSO.py &> tso8.log &)
