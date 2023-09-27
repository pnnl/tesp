# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: weatherAgentTest.py

import sys
import tesp_support.weather.weather_agent as wa

if len(sys.argv) != 2:
    print("Please specify weather csv data file on the command line.")
    exit()
file = sys.argv[1]
wa.startWeatherAgent(file)
