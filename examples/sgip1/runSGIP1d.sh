#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 5 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w ../energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../energyplus/SchoolDualController.idf &> eplus1d.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_SGIP1d_metrics.json &> eplus_json1d.log &)
(export FNCS_FATAL=NO && exec gridlabd -D USE_FNCS -D METRICS_FILE=SGIP1d_metrics.json SGIP1d.glm &> gridlabd1d.log &)
(export FNCS_CONFIG_FILE=SGIP1b_auction.yaml && export FNCS_FATAL=NO && exec python auction.py SGIP1b_agent_dict.json SGIP1d &> auction1d.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py SGIP1d &> pypower1d.log &)

