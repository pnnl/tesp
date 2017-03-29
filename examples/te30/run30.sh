#!/bin/bash
# (export FNCS_BROKER="tcp://*:5571" && export FNCS_LOG_LEVEL=DEBUG4 && export FNCS_LOG_STDOUT=yes && exec fncs_broker 36 &> broker.log &)
(export FNCS_BROKER="tcp://*:5571" && exec fncs_broker 36 &> broker.log &)
#(export FNCS_BROKER="tcp://*:5571" && exec fncs_broker 7 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w ../energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../energyplus/SchoolDualController.idf &> eplus.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_TE_Challenge_metrics.json &> eplus_json.log &)
(export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 2d tracer.out &> tracer.log &)
(exec ./launch_TE_Challenge_agents.sh &)
#(exec ./launch_Eplusonly_agents.sh &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py TE_Challenge "2013-07-01 00:00:00" 172800 300 &> pypower.log &)

