#!/bin/bash

EPLUS_PATH=$TESPDIR/data/energyplus
SCHED_PATH=$TESPDIR/data/schedules

# start a HELICS federation for GridLAB-D, substation, weather and PYPOWER; the E+ agent was already started as part of the FNCS federation
(exec helics_broker -f 6 --loglevel=warning --name=mainbroker &> helics_broker.log &)
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_HELICS -D METRICS_FILE=TE_ChallengeH_metrics.json TE_Challenge.glm &> helics_gridlabd.log &)
(export WEATHER_CONFIG=TE_Challenge_HELICS_Weather_Config.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" &> helics_weather.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('te30_pp.json','TE_ChallengeH',helicsConfig='pypowerConfig.json')" &> helics_pypower.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_ChallengeH',helicsConfig='TE_Challenge_HELICS_substation.json')" &> helics_substation.log &)

(export HELICS_CONFIG_FILE=helics_eplus.json && exec energyplus -w "$EPLUS_PATH/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw" -d output -r MergedH.idf &> helics_eplus.log &)
(exec eplus_agent_helics 172800s 300s SchoolDualController eplus_TE_ChallengeH_metrics.json  0.02 25 4 4 helics_eplus_agent.json &> helics_eplus_agent.log &)
