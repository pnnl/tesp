import tesp_support.weatherAgent as tesp
import sys

if len(sys.argv) != 2:
    print("Please specify weather csv data file on the command line.")
    exit()
file = sys.argv[1]
tesp.startWeatherAgent(file)
