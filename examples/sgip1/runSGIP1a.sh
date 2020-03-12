#!/bin/bash

declare -r TESP_SUPPORT=$TESP_INSTALL/share/support
declare -r SCHED_PATH=$TESP_SUPPORT/schedules

(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 5 &> broker.log &)
# this is based on SGIP1b, writing to different metrics file and assuming the market clearing is disabled
(export FNCS_CONFIG_FILE=eplus.yaml && exec EnergyPlus -w ../../support/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf &> eplus1a.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m SchoolDualController eplus_SGIP1a_metrics.json &> eplus_json1a.log &)
(export FNCS_FATAL=YES && exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_FNCS -D METRICS_FILE=SGIP1a_metrics.json SGIP1b.glm &> gridlabd1a.log &)
(export FNCS_CONFIG_FILE=SGIP1b_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('SGIP1b_agent_dict.json','SGIP1a',flag='NoMarket')" &> substation1a.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('sgip1_pp.json','SGIP1a')" &> pypower1a.log &)

