#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run.sh

# start a FNCS federation for GridLAB-D, substation, weather, PYPOWER, E+ and E+ agent
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 6 &> broker_f.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w "USA_AZ_Tucson.Intl.AP.722740_TMY3.epw" -d output -r Merged_f.idf &> eplus_f.log &)
(export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m SchoolDualController eplus_TE_Challenge_metrics.json &> eplus_agent_f.log &)
(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE=TE_Challenge_metrics.json TE_Challenge.glm &> gridlabd_f.log &)
(export FNCS_CONFIG_FILE=TE_Challenge_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.substation as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_Challenge')" &> substation_f.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.tso_PYPOWER_f as tesp;tesp.tso_pypower_loop_f('te30_pp.json','TE_Challenge')" &> pypower_f.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export WEATHER_CONFIG=TE_Challenge_weather_f.json && exec python3 -c "import tesp_support.weatherAgent as tesp;tesp.startWeatherAgent('weather.dat')" &> weather_f.log &)
