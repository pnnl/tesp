#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 5 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w ../../support/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf &> eplus1e.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_SGIP1e_metrics.json &> eplus_json1e.log &)
(export FNCS_FATAL=NO && exec gridlabd -D USE_FNCS -D METRICS_FILE=SGIP1e_metrics.json SGIP1e.glm &> gridlabd1e.log &)
(export FNCS_CONFIG_FILE=SGIP1b_auction.yaml && export FNCS_FATAL=NO && exec python auction.py SGIP1b_agent_dict.json SGIP1e &> auction1e.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py SGIP1e &> pypower1e.log &)

