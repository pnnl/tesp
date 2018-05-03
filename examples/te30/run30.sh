#!/bin/bash
#(export FNCS_BROKER="tcp://*:5570" && export FNCS_LOG_LEVEL=DEBUG4 && export FNCS_LOG_STDOUT=yes && export FNCS_TRACE=yes && exec fncs_broker 36 &> broker.log &)
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 34 &> broker.log &)
#(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS TE_Challenge.glm &> gridlabd.log &)
#(export FNCS_CONFIG_FILE=eplus.yaml && exec EnergyPlus -w ../energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../energyplus/SchoolDualController.idf &> eplus.log &)
#(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_TE_Challenge_metrics.json &> eplus_json.log &)
(export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 2d tracer.out &> tracer.log &)
(exec ./launch_TE_Challenge_agents.sh &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py TE_Challenge &> pypower.log &)
