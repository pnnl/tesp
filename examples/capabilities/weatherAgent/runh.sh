#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runh.sh

declare -r TMY_PATH=$TESPDIR/data/weather

# generate the weather text file
python3 -c "import tesp_support.TMY3toCSV as tesp;tesp.weathercsv('${TMY_PATH}/TX-Dallasfort_Worth_Intl_Ap.tmy3','weather.dat','2000-01-01 00:00:00','2000-01-07 00:00:00',2000)"

# run the TMY3 version
gridlabd -D TMY3_PATH="$TMY_PATH" weatherTester.glm > gridlabd_tmy3.log

# run the text file through HELICS
(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker_helics.log &)
(exec gridlabd -D USE_HELICS weatherTester.glm &> gridlabd_helics.log &)
(exec helics_recorder --input=helicsRecorder.txt --period 300s --stop 86401s &> recorder_helics.log &)
(export WEATHER_CONFIG=HelicsWeatherConfig.json && exec python3 -c "import tesp_support.weatherAgent as tesp;tesp.startWeatherAgent('weather.dat')" &> weather_helics.log &)
