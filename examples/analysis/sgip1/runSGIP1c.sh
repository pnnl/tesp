#!/bin/bash

SCHED_PATH=$TESPDIR/data/schedules
EPLUS_PATH=$TESPDIR/data/energyplus

(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 6 &> broker1c.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $EPLUS_PATH/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r $EPLUS_PATH/SchoolDualController.idf &> eplus1c.log &)
(export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m SchoolDualController eplus_SGIP1c_metrics.json &> eplus_agent1c.log &)
(export FNCS_FATAL=YES && exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_FNCS -D METRICS_FILE=SGIP1c_metrics.json SGIP1c.glm &> gridlabd1c.log &)
(export FNCS_CONFIG_FILE=SGIP1c_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('SGIP1c_agent_dict.json','SGIP1c')" &> substation1c.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('sgip1_pp.json','SGIP1c')" &> pypower1c.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export WEATHER_CONFIG=SGIP1c_FNCS_Weather_Config.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" &> weather1c.log &)
