# Copyright (C) 2019-2023 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: weatherAgent.py

"""Weather Agent

This weather agent needs an WEATHER_CONFIG environment variable to be set, which is a json file.
"""
import json
import os
import sys
from datetime import datetime
from datetime import timedelta

import pandas as pd

import helics
from tesp_support.weather.forecast import convertTimeToSeconds, weather_forecast

def startWeatherAgent(file):
    """ The weather agent publishes weather data as configured by the json file

    Args:
        file (str): the weather data file
    """
    # read the weather data file, arguments to mimic deprecated from_csv function
    weatherData = pd.read_csv(file, index_col=0, parse_dates=True)
    broker_address = None
    config = os.environ['WEATHER_CONFIG']  # read the weather config json file
    if os.path.isfile(config):
        with open(config, 'r') as stream:
            try:
                conf = json.load(stream)
                agentName = conf['name']
                broker = conf['broker']
                timeStop = conf['time_stop']
                StartTime = conf['StartTime']
                timeFormat = '%Y-%m-%d %H:%M:%S'
                dtStart = datetime.strptime(StartTime, timeFormat)
                timeDeltaStr = conf['time_delta']
                publishInterval = conf['publishInterval']
                forecast = conf['Forecast']
                addErrorToForecast = conf['AddErrorToForecast']
                forecastLength = conf['ForecastLength']
                publishTimeAhead = conf['PublishTimeAhead']
                forecastPeriod = conf['forecastPeriod']
                forecastParameters = conf['parameters']
                broker_address = conf['broker_address']
            except:
                pass
    else:
        print('could not open WEATHER_CONFIG file for FNCS or HELICS')
        sys.exit()
    print('WEATHER_CONFIG file: ' + config, flush=True)

    # convert some time values in config file to seconds
    try:
        publishTimeAhead = convertTimeToSeconds(publishTimeAhead)
        timeDeltaInSeconds = convertTimeToSeconds(timeDeltaStr)
        publishIntervalInSeconds = convertTimeToSeconds(publishInterval)
        forecastLength = convertTimeToSeconds(forecastLength)
        timeStopInSeconds = convertTimeToSeconds(timeStop)
    except Exception as ex:
        print("Error in", ex)

    # when doing resample(), use publishIntervalInSeconds to make it uniform
    # the reason for that is due to some of the units that we use for fncs, such as 'min',
    # is not recognized by the resample() function
    weatherData2 = weatherData.resample(rule=str(publishIntervalInSeconds) + "s", closed='left').first()
    weatherData2 = weatherData2.interpolate(method='quadratic')

    # find weather data on the hour for the hourly forecast
    hourlyWeatherData = weatherData.resample('60min').mean()

    # find all the time point that the data at that time need to be published
    timeNeedToPublishRealtime = [0]
    timeNeedToPublishForecast = [0]
    # real time need to publish
    numberOfRealtimeBroadcast = timeStopInSeconds // publishIntervalInSeconds + 1
    for i in range(1, numberOfRealtimeBroadcast):
        timeNeedToPublishRealtime.append(i * publishIntervalInSeconds)
    if forecast == 1:
        # time need to publish forecast, which is on the hour
        numberOfForecast = timeStopInSeconds // 3600 + 1
        for i in range(1, numberOfForecast):
            timeNeedToPublishForecast.append(i * 3600)
        # combine real time and forecast time
        timeNeedToBePublished = list(set([0] + timeNeedToPublishRealtime + timeNeedToPublishForecast))
    else:
        timeNeedToBePublished = timeNeedToPublishRealtime
    timeNeedToBePublished.sort()

    # find all the time point that need to publish weather data,
    # each time point in this list pairs with each time point in timeNeedToBePublished list
    timeNeedToPublish = [(i - publishTimeAhead) if (i - publishTimeAhead) >= 0 else 0 for i in timeNeedToBePublished]

    # other weather agents could be initializing from FNCS.zpl, so we might have a race condition
    #  file locking didn't work, because fncs.initialize() doesn't return until broker hears from all other simulators
    hPubs = {}
    fedName = agentName  # 'weather'
    fedInfo = helics.helicsCreateFederateInfo()
    helics.helicsFederateInfoSetCoreName(fedInfo, fedName)
    helics.helicsFederateInfoSetCoreTypeFromString(fedInfo, 'zmq')
    helics.helicsFederateInfoSetCoreInitString(fedInfo, '--federates=1')
    if broker_address is not None:
        helics.helicsFederateInfoSetCoreInitString(fedInfo, '--broker_address=' + broker_address)
    helics.helicsFederateInfoSetTimeProperty(fedInfo, helics.helics_property_time_delta, timeDeltaInSeconds)
    hFed = helics.helicsCreateValueFederate(fedName, fedInfo)
    for col in weatherData.columns:
        pubName = fedName + '/#' + col
        hPubs[col] = helics.helicsFederateRegisterGlobalPublication(
                     hFed, pubName, helics.helics_data_type_string, "")
        pubName = pubName + '#forecast'
        hPubs[col + '/forecast'] = helics.helicsFederateRegisterGlobalPublication(
                                   hFed, pubName, helics.helics_data_type_string, "")
    helics.helicsFederateEnterExecutingMode(hFed)
    print('HELICS initialized to publish', hPubs, flush=True)

    time_granted = 0
    for i in range(len(timeNeedToPublish)):
        if i > 0:
            timeToRequest = timeNeedToPublish[i]
            time_granted = int(helics.helicsFederateRequestTime(hFed, timeToRequest))
        if timeNeedToBePublished[i] in timeNeedToPublishRealtime:
            # find the data by the time point and publish them
            row = weatherData2.loc[dtStart + timedelta(seconds=timeNeedToBePublished[i])]
            # print('publishing at ' + str(dtStart + timedelta(seconds=timeNeedToPublish[i])) +
            #       ' for weather at ' + str(dtStart + timedelta(seconds=timeNeedToBePublished[i])), flush=True)
            for key, value in row.items():
                # remove the improper value generated by interpolation
                if key != "temperature" and value < 1e-4:
                    value = 0
                helics.helicsPublicationPublishDouble(hPubs[key], value)
        # if forecasting needed and the time is on the hour
        if forecast == 1 and timeNeedToBePublished[i] in timeNeedToPublishForecast:
            print('forecasting at ' + str(dtStart + timedelta(seconds=timeNeedToPublish[i])) +
                  ' for weather starting from ' + str(dtStart + timedelta(seconds=timeNeedToBePublished[i])),
                  flush=True)
            forecastStart = dtStart + timedelta(seconds=timeNeedToBePublished[i])
            forecastEnd = dtStart + timedelta(seconds=forecastLength) + timedelta(seconds=timeNeedToBePublished[i])
            # find the data by forecast starting and ending time, should be multiple data point for each weather factor
            rows = hourlyWeatherData.loc[
                (hourlyWeatherData.index >= forecastStart) & (hourlyWeatherData.index < forecastEnd)].copy()
            rows.loc[rows.solar_direct < 1e-4, 'solar_direct'] = 0
            rows.loc[rows.solar_diffuse < 1e-4, 'solar_diffuse'] = 0
            rows.loc[rows.wind_speed < 1e-4, 'wind_speed'] = 0
            rows.loc[rows.humidity < 1e-4, 'humidity'] = 0
            rows.loc[rows.pressure < 1e-4, 'pressure'] = 0
            for col in rows.columns:
                data = rows[col].values
                times = rows.index
                # if user wants to add error to the forecasted data to mimic weather forecast
                if addErrorToForecast == 1:
                    WF_obj = weather_forecast(col, forecastPeriod * 2, forecastParameters)  # make object
                    data = WF_obj.make_forecast(data, len(data))
                wd = dict()
                # convert data to a dictionary with time as the key, so it can be published as json string
                for v in range(len(data)):
                    if col != "temperature" and data[v] < 1e-4:
                        data[v] = 0
                    wd[str(times[v])] = str(data[v])
#               print(col, json.dumps(wd))
                helics.helicsPublicationPublishString(hPubs[col + '/forecast'], json.dumps(wd))

    # if the last time step/stop time is not requested
    if timeStopInSeconds not in timeNeedToPublish:
        time_granted = int(helics.helicsFederateRequestTime(hFed, timeStopInSeconds))

    print('finalizing HELICS', flush=True)
    helics.helicsFederateDestroy(hFed)

def usage():
    print("usage: python weatherAgent.py <input weather file full path>")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit()
    inputFile = sys.argv[1]
    startWeatherAgent(inputFile)
