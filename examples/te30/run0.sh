#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 5 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec EnergyPlus -w ../../support/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf &> eplus0.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m SchoolDualController eplus_TE_Challenge0_metrics.json &> eplus_json0.log &)
(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE=TE_Challenge0_metrics.json TE_Challenge.glm &> gridlabd0.log &)
(export FNCS_CONFIG_FILE=TE_Challenge_auction.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.auction_loop('TE_Challenge_agent_dict.json','TE_Challenge0','NoMarket')" &> auction0.log &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('te30_pp.json','TE_Challenge0')" &> pypower0.log &)
