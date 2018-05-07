#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 3 &> broker.log &)
(export FNCS_FATAL=NO && exec gridlabd -D USE_FNCS -D METRICS_FILE=TE_Challenge0_metrics.json TE_Challenge.glm &> gridlabd0.log &)
(export FNCS_CONFIG_FILE=TE_Challenge_auction.yaml && export FNCS_FATAL=NO && exec python auction.py TE_Challenge_agent_dict.json TE_Challenge0 NoMarket &> auction0.log &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py TE_Challenge0 &> pypower0.log &)
