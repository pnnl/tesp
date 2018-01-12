#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 760 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec EnergyPlus -w ../energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../energyplus/SchoolDualController.idf &> eplus.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_SGIP1d_metrics.json &> eplus_json.log &)
(exec ./launch_SGIP1d_agents.sh &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py SGIP1d &> pypower.log &)

