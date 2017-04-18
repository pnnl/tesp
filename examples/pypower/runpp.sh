#!/bin/bash
(export FNCS_BROKER="tcp://*:5571" && export FNCS_LOG_LEVEL=DEBUG4 && export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> ppbroker.log &)
# (export FNCS_BROKER="tcp://*:5571" && exec fncs_broker 3 &> ppbroker.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_LOG_LEVEL=DEBUG4 && exec fncs_player 2d player.txt &> ppplayer.log &)
(export FNCS_CONFIG_FILE=pptracer.yaml && exec fncs_tracer 2d pptracer.out &> pptracer.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py &> pypower.log &)

