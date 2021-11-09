#!/bin/bash

(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 4 &> broker.log &)
(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE=CombinedCase_metrics.json CombinedCase.glm &> gridlabd.log &)
(export FNCS_CONFIG_FILE=CombinedCase_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('CombinedCase_agent_dict.json','CombinedCase')"  &> substation.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('Feeder1_pp.json','CombinedCase')"  &> pypower.log &)
(export WEATHER_CONFIG=Feeder1_FNCS_Weather_Config.json && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')"  &> weather.log &)
