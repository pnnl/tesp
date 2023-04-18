#!/bin/bash
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runh.sh

mkdir -p PyomoTempFiles

(exec helics_broker -f 12 --loglevel=warning --name=mainbroker &> helics_broker.log &)
(export WEATHER_CONFIG=weatherIAH.json && exec python3 -c "import tesp_support.weather_agent as tesp;tesp.startWeatherAgent('weatherIAH.dat')"  &> weatherIAH.log &)
(export WEATHER_CONFIG=weatherSPS.json && exec python3 -c "import tesp_support.weather_agent as tesp;tesp.startWeatherAgent('weatherSPS.dat')"  &> weatherSPS.log &)
(export WEATHER_CONFIG=weatherELP.json && exec python3 -c "import tesp_support.weather_agent as tesp;tesp.startWeatherAgent('weatherELP.dat')"  &> weatherELP.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus1_metrics.json Bus1.glm &> Bus1.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus2_metrics.json Bus2.glm &> Bus2.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus3_metrics.json Bus3.glm &> Bus3.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus4_metrics.json Bus4.glm &> Bus4.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus5_metrics.json Bus5.glm &> Bus5.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus6_metrics.json Bus6.glm &> Bus6.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus7_metrics.json Bus7.glm &> Bus7.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=Bus8_metrics.json Bus8.glm &> Bus8.log &)
(exec python3 fncsTSO.py &> bulk.log &)
