#!/bin/bash
# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: ruhSGIP1ex.sh

declare -r SCHED_PATH=$TESPDIR/data/schedules
declare -r EPLUS_PATH=$TESPDIR/data/energyplus
declare -r EPWFILE=$EPLUS_PATH/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw

(exec helics_broker -f 6 --loglevel=debug --name=mainbroker &> broker1ex.log &)
# this is based on SGIP1b, writing to different metrics file and assuming the market clearing is disabled
(export HELICS_CONFIG_FILE=eplusH.json && exec energyplus -w $EPWFILE -d output -r $EPLUS_PATH/SchoolDualController_h.idf &> eplus1ex.log &)
(exec eplus_agent_helics 172800s 5m SchoolDualController eplus_SGIP1ex_metrics.json 0.10 25 4 4 eplus_agentH.json &> eplus_agent1ex.log &)
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_HELICS -D METRICS_FILE=SGIP1ex_metrics.json SGIP1e.glm &> gridlabd1ex.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('SGIP1e_agent_dict.json', 'SGIP1ex',flag='NoMarket', helicsConfig='SGIP1b_substation.json')" &> substation1ex.log &)
(exec python3 -c "import tesp_support.api.tso_PYPOWER as tesp;tesp.tso_pypower_loop('sgip1_pp.json','SGIP1ex','pypowerConfig.json')" &> pypower1ex.log &)
(export WEATHER_CONFIG=SGIP1b_weather.json && exec python3 -c "import tesp_support.weather.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')" &> weather1ex.log &)
