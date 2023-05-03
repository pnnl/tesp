#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runh.sh

# start a HELICS federation for GridLAB-D, substation, weather, PYPOWER, E+ and E+ agent
(exec helics_broker -f 6 --loglevel=warning --name=mainbroker &> broker.log &)
(export HELICS_CONFIG_FILE=eplus.json && exec energyplus -w "USA_AZ_Tucson.Intl.AP.722740_TMY3.epw" -d output -r Merged.idf &> eplus.log &)
(exec eplus_agent_helics 172800s 300s SchoolDualController eplus_TE_ChallengeH_metrics.json 0.02 25 4 4 eplus_agent.json &> eplus_agent.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=TE_ChallengeH_metrics.json TE_Challenge.glm &> gridlabd.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_ChallengeH',helicsConfig='TE_Challenge_substation.json')" &> substation.log &)
(exec python3 -c "import tesp_support.api.tso_PYPOWER as tesp;tesp.tso_pypower_loop('te30_pp.json','TE_ChallengeH',helicsConfig='pypower.json')" &> pypower.log &)
(export WEATHER_CONFIG=TE_Challenge_weather.json && exec python3 -c "import tesp_support.api.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')" &> weather.log &)
