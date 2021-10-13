#!/bin/bash

TMY3_PATH=$TESPDIR/data/weather

# generate the weather text file
python3 -c "import tesp_support.api as tesp;tesp.weathercsv('${TMY3_PATH}/TX-Dallasfort_Worth_Intl_Ap.tmy3','weather.dat','2000-01-01 00:00:00','2000-01-07 00:00:00',2000)"

# run the TMY3 version
gridlabd -D TMY3_PATH=$TMY3_PATH weatherTester.glm > gridlabd_tmy3.log

# run the text file through FNCS
(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec gridlabd -D USE_FNCS weatherTester.glm &> gridlabd_fncs.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 1d tracer.out &> tracer.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export WEATHER_CONFIG=WeatherConfig.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" &> weather.log &)
