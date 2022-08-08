#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run.sh

declare -r EPLUS_PATH=$TESPDIR/data/energyplus
declare -r SCHED_PATH=$TESPDIR/data/schedules

(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 6 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w "$EPLUS_PATH/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw" -d output -r Merged.idf &> eplus.log &)
(export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m SchoolDualController eplus_TE_Challenge_metrics.json &> eplus_agent.log &)
(export FNCS_FATAL=YES && exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_FNCS -D METRICS_FILE=TE_Challenge_metrics.json TE_Challenge.glm &> gridlabd.log &)
(export FNCS_CONFIG_FILE=TE_Challenge_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_Challenge')" &> substation.log &)
(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.tso_pypower_loop_f('te30_pp.json','TE_Challenge')" &> pypower.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export WEATHER_CONFIG=TE_Challenge_FNCS_Weather_Config.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" &> weather.log &)
