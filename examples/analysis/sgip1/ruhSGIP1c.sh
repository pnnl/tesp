#!/bin/bash
# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: ruhSGIP1c.sh

declare -r SCHED_PATH=$TESPDIR/data/schedules
declare -r EPLUS_PATH=$TESPDIR/data/energyplus
declare -r EPWFILE=$EPLUS_PATH/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw

(exec helics_broker -f 6 --loglevel=debug --name=mainbroker &> broker1c.log &)
# this is based on SGIP1b, writing to different metrics file and assuming the market clearing is disabled
(export HELICS_CONFIG_FILE=eplusH.json && exec energyplus -w $EPWFILE -d output -r $EPLUS_PATH/SchoolDualController_h.idf &> eplus1c.log &)
(exec eplus_agent_helics 172800s 5m SchoolDualController eplus_SGIP1c_metrics.json 0.10 25 4 4 eplus_agentH.json &> eplus_agent1c.log &)
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_HELICS -D METRICS_FILE=SGIP1c_metrics.json SGIP1c.glm &> gridlabd1c.log &)
(exec python3 -c "import tesp_support.substation as tesp;tesp.substation_loop('SGIP1c_agent_dict.json', 'SGIP1c', helicsConfig='SGIP1b_substation.json')" &> substation1c.log &)
(exec python3 -c "import tesp_support.tso_PYPOWER as tesp;tesp.tso_pypower_loop('sgip1_pp.json','SGIP1c','pypowerConfig.json')" &> pypower1c.log &)
(export WEATHER_CONFIG=SGIP1b_weather.json && exec python3 -c "import tesp_support.weatherAgent as tesp;tesp.startWeatherAgent('weather.dat')" &> weather1c.log &)
