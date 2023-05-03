#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runh.sh

mkdir -p PyomoTempFiles

(exec helics_broker -f 20 --loglevel=warning --name=mainbroker &> helics_broker.log &)

(export WEATHER_CONFIG=weatherIAH.json && exec python3 -c "import tesp_support.api.weather_agent as tesp;tesp.startWeatherAgent('weatherIAH.dat')"  &> weatherIAH.log &)
(export WEATHER_CONFIG=weatherSPS.json && exec python3 -c "import tesp_support.api.weather_agent as tesp;tesp.startWeatherAgent('weatherSPS.dat')"  &> weatherSPS.log &)
(export WEATHER_CONFIG=weatherELP.json && exec python3 -c "import tesp_support.api.weather_agent as tesp;tesp.startWeatherAgent('weatherELP.dat')"  &> weatherELP.log &)

(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus1_metrics.json Bus1.glm &> Bus1.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus2_metrics.json Bus2.glm &> Bus2.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus3_metrics.json Bus3.glm &> Bus3.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus4_metrics.json Bus4.glm &> Bus4.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus5_metrics.json Bus5.glm &> Bus5.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus6_metrics.json Bus6.glm &> Bus6.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus7_metrics.json Bus7.glm &> Bus7.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus8_metrics.json Bus8.glm &> Bus8.log &)

(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus1_agent_dict.json', 'Bus1', 72, helicsConfig='./Bus1_substation.json')" &> substation1.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus2_agent_dict.json', 'Bus2', 72, helicsConfig='./Bus2_substation.json')" &> substation2.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus3_agent_dict.json', 'Bus3', 72, helicsConfig='./Bus3_substation.json')" &> substation3.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus4_agent_dict.json', 'Bus4', 72, helicsConfig='./Bus4_substation.json')" &> substation4.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus5_agent_dict.json', 'Bus5', 72, helicsConfig='./Bus5_substation.json')" &> substation5.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus6_agent_dict.json', 'Bus6', 72, helicsConfig='./Bus6_substation.json')" &> substation6.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus7_agent_dict.json', 'Bus7', 72, helicsConfig='./Bus7_substation.json')" &> substation7.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('Bus8_agent_dict.json', 'Bus8', 72, helicsConfig='./Bus8_substation.json')" &> substation8.log &)

(exec python3 fncsTSO.py &> bulk.log &)
