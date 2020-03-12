#!/bin/bash

declare -r TESP_SUPPORT=$TESP_INSTALL/share/support
declare -r SCHED_PATH=$TESP_SUPPORT/schedules

(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 6 &> broker0.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $TESP_SUPPORT/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r $TESP_SUPPORT/energyplus/SchoolDualController.idf &> eplus0.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m SchoolDualController eplus_TE_Challenge0_metrics.json &> eplus_json0.log &)
(export FNCS_FATAL=YES && exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_FNCS -D METRICS_FILE=TE_Challenge0_metrics.json TE_Challenge.glm &> gridlabd0.log &)
(export FNCS_CONFIG_FILE=TE_Challenge_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_Challenge0',flag='NoMarket')" &> substation0.log &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('te30_pp.json','TE_Challenge0')" &> pypower0.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export WEATHER_CONFIG=TE_Challenge_Weather_Config.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" &> weather0.log &)

