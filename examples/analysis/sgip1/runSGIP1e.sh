#!/bin/bash
# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: runSGIP1e.sh

declare -r SCHED_PATH=$TESPDIR/data/schedules
declare -r EPLUS_PATH=$TESPDIR/data/energyplus

(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 6 &> broker1e.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $EPLUS_PATH/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r $EPLUS_PATH/SchoolDualController_f.idf &> eplus1e.log &)
(export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m SchoolDualController eplus_SGIP1e_metrics.json &> eplus_agent1e.log &)
(export FNCS_FATAL=YES && exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_FNCS -D METRICS_FILE=SGIP1e_metrics.json SGIP1e.glm &> gridlabd1e.log &)
(export FNCS_CONFIG_FILE=SGIP1b_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.substation as tesp;tesp.substation_loop('SGIP1e_agent_dict.json','SGIP1e')" &> substation1e.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api.tso_PYPOWER_f as tesp;tesp.tso_pypower_loop_f('sgip1_pp.json','SGIP1e')" &> pypower1e.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export WEATHER_CONFIG=SGIP1b_weather.json && exec python3 -c "import tesp_support.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')" &> weather1e.log &)
