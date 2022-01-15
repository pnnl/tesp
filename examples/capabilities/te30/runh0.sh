#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runh0.sh

EPLUS_PATH=$TESPDIR/data/energyplus
SCHED_PATH=$TESPDIR/data/schedules

# start a HELICS federation for GridLAB-D, substation, weather, PYPOWER, E+ and E+ agent
(exec helics_broker -f 6 --loglevel=warning --name=mainbroker &> helics_broker.log &)
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_HELICS -D METRICS_FILE=TE_ChallengeH0_metrics.json TE_Challenge.glm &> helics_gridlabd0.log &)
(export WEATHER_CONFIG=TE_Challenge_HELICS_Weather_Config.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" &> helics_weather0.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('te30_pp.json','TE_ChallengeH0',helicsConfig='pypowerConfig.json')" &> helics_pypower0.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_ChallengeH0',helicsConfig='TE_Challenge_HELICS_substation.json',flag='NoMarket')" &> helics_substation0.log &)

(export HELICS_CONFIG_FILE=helics_eplus.json && exec energyplus -w "$EPLUS_PATH/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw" -d output -r MergedH.idf &> helics_eplus0.log &)
(exec eplus_agent_helics 172800s 300s SchoolDualController eplus_TE_ChallengeH0_metrics.json  0.02 25 4 4 helics_eplus_agent.json &> helics_eplus_agent0.log &)
#(exec helics_recorder rec.json --stop 5 &> rec.log &)