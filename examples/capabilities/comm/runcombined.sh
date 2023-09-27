#!/bin/bash
# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: runcombinedh.sh

(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 4 &> broker_f.log &)
(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE=CombinedCase_metrics.json CombinedCase.glm &> gld_7_f.log &)
(export FNCS_CONFIG_FILE=CombinedCase_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.original.substation_f as tesp;tesp.substation_loop_f('CombinedCase_agent_dict.json','CombinedCase')"  &> sub_7_f.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.original.tso_PYPOWER_f as tesp;tesp.tso_pypower_loop_f('Feeder1_pp.json','CombinedCase')"  &> pypower_f.log &)
(export WEATHER_CONFIG=Feeder1_weather_f.json && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.weather.weather_agent_f as tesp;tesp.startWeatherAgent('weather.dat')"  &> weather_f.log &)
