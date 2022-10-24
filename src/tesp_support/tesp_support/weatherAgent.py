# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: weatherAgent.py

"""Weather Agent

This weather agent needs an WEATHER_CONFIG environment variable to be set, which is a json file.
"""
import json
import os
import random
import sys
from datetime import datetime
from datetime import timedelta

import numpy
import pandas as pd
from scipy.stats import truncnorm

if sys.platform != 'win32':
    import resource


def show_resource_consumption():
    if sys.platform != 'win32':
        usage = resource.getrusage(resource.RUSAGE_SELF)
        RESOURCES = [
            ('ru_utime', 'User time'),
            ('ru_stime', 'System time'),
            ('ru_maxrss', 'Max. Resident Set Size'),
            ('ru_ixrss', 'Shared Memory Size'),
            ('ru_idrss', 'Unshared Memory Size'),
            ('ru_isrss', 'Stack Size'),
            ('ru_inblock', 'Block inputs'),
            ('ru_oublock', 'Block outputs')]
        print('Resource usage:')
        for name, desc in RESOURCES:
            print('  {:<25} ({:<10}) = {}'.format(desc, name, getattr(usage, name)))


def startWeatherAgent(file):
    """the weather agent publishes weather data as configured by the json file

    :param file: string
        the weather data file
    :return: nothing
    """
    # read the weather data file, arguments to mimic deprecated from_csv function
    weatherData = pd.read_csv(file, index_col=0, parse_dates=True)
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
            except ValueError as ex:
                print(ex)
    else:
        print('could not open WEATHER_CONFIG file for FNCS or HELICS')
        sys.exit()
    print('WEATHER_CONFIG file: ' + config, flush=True)

    # convert some time values in config file to seconds
    try:
        publishTimeAhead = convertTimeToSeconds(publishTimeAhead)
    except Exception as ex:
        print("Error in PublishTimeAhead", ex)

    try:
        timeDeltaInSeconds = convertTimeToSeconds(timeDeltaStr)
    except Exception as ex:
        print("Error in time_delta", ex)

    try:
        publishIntervalInSeconds = convertTimeToSeconds(publishInterval)
    except Exception as ex:
        print("Error in publish Interval", ex)

    try:
        forecastLength = convertTimeToSeconds(forecastLength)
    except Exception as ex:
        print("Error in ForecastLength", ex)

    try:
        timeStopInSeconds = convertTimeToSeconds(timeStop)
    except Exception as ex:
        print("Error in time_stop", ex)

    # write fncs.zpl file here
    # this config str won't work as an argument to fncs::initialize, so write fncs.zpl just in time
    zplstr = "name = {}\ntime_delta = {}s\ntime_stop = {}s\nbroker = {}".format(
              agentName, timeDeltaInSeconds, timeStopInSeconds, broker)

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
    hFed = None
    hPubs = {}
    fedName = agentName  # 'weather'
    if broker == 'HELICS':
        try:
            import helics  # set the broker = HELICS in WEATHER_CONFIG
        except:
            pass
        fedInfo = helics.helicsCreateFederateInfo()
        helics.helicsFederateInfoSetCoreName(fedInfo, fedName)
        helics.helicsFederateInfoSetCoreTypeFromString(fedInfo, 'zmq')
        helics.helicsFederateInfoSetCoreInitString(fedInfo, '--federates=1')
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
    else:
        try:
            import tesp_support.fncs as fncs
        except:
            pass
        configstr = zplstr.encode('utf-8')
        fncs.initialize(configstr)
        print('FNCS initialized', flush=True)

    time_granted = 0
    for i in range(len(timeNeedToPublish)):
        if i > 0:
            timeToRequest = timeNeedToPublish[i]
            if hFed is not None:
                time_granted = int(helics.helicsFederateRequestTime(hFed, timeToRequest))
            else:
                time_granted = fncs.time_request(timeToRequest)
        if timeNeedToBePublished[i] in timeNeedToPublishRealtime:
            # find the data by the time point and publish them
            row = weatherData2.loc[dtStart + timedelta(seconds=timeNeedToBePublished[i])]
            # print('publishing at ' + str(dtStart + timedelta(seconds=timeNeedToPublish[i])) +
            #       ' for weather at ' + str(dtStart + timedelta(seconds=timeNeedToBePublished[i])), flush=True)
            for key, value in row.iteritems():
                # remove the improper value generated by interpolation
                if key != "temperature" and value < 1e-4:
                    value = 0
                if hFed is not None:
                    helics.helicsPublicationPublishDouble(hPubs[key], value)
                else:
                    fncs.publish(key, value)
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
            rows.solar_direct[rows.solar_direct < 1e-4] = 0
            rows.solar_diffuse[rows.solar_diffuse < 1e-4] = 0
            rows.wind_speed[rows.wind_speed < 1e-4] = 0
            rows.humidity[rows.humidity < 1e-4] = 0
            rows.pressure[rows.pressure < 1e-4] = 0
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
                if hFed is not None:
                    helics.helicsPublicationPublishString(hPubs[col + '/forecast'], json.dumps(wd))
                else:
                    fncs.publish(col + '/forecast', json.dumps(wd))

    # if the last time step/stop time is not requested
    if timeStopInSeconds not in timeNeedToPublish:
        if hFed is not None:
            time_granted = int(helics.helicsFederateRequestTime(hFed, timeStopInSeconds))
        else:
            time_granted = fncs.time_request(timeStopInSeconds)

    if hFed is not None:
        print('finalizing HELICS', flush=True)
        helics.helicsFederateDestroy(hFed)
    else:
        print('finalizing FNCS', flush=True)
        fncs.finalize()
    show_resource_consumption()


def usage():
    print("usage: python weatherAgent.py <input weather file full path>")


def convertTimeToSeconds(time):
    """Convert time string with unit to integer in seconds

    It only parse unit in day, hour, minute and second.
    It will not recognize week, month, year, millisecond, microsecond or nanosecond, they can be added if needed.

    :param time: str
        time with unit
    :return: int
        represent the input time in second
    """
    unit = ''.join(filter(str.isalpha, time))
    timeNum = int(''.join(filter(str.isdigit, time)))
    if "d" == unit or "day" == unit or "days" == unit:
        return 24 * 60 * 60 * timeNum
    elif "h" == unit or "hour" == unit or "hours" == unit:
        return 60 * 60 * timeNum
    elif "m" == unit or "min" == unit or "minute" == unit or "minutes" == unit:
        return 60 * timeNum
    elif "s" == unit or "sec" == unit or "second" == unit or "seconds" == unit:
        return timeNum
    else:
        raise Exception("unrecognized time unit '" + unit + "'.")


def deltaTimeToResmapleFreq(time):
    """Convert time unit to a resampling frequency that can be recognized by pandas.DataFrame.resample()

    It only parses unit in day, hour, minute and second.
    It won't recognize week, month, year, millisecond, microsecond or nanosecond, they can be added if needed.

    :param time: str
        time with unit
    :return: str
        time with resample frequency
    """
    unit = ''.join(filter(str.isalpha, time))
    timeNum = int(''.join(filter(str.isdigit, time)))
    if "d" == unit or "day" == unit or "days" == unit:
        return str(timeNum) + "d"
    elif "h" == unit or "hour" == unit or "hours" == unit:
        return str(timeNum) + "h"
    elif "m" == unit or "min" == unit or "minute" == unit or "minutes" == unit:
        return str(timeNum) + "T"
    elif "s" == unit or "sec" == unit or "second" == unit or "seconds" == unit:
        return str(timeNum) + "s"
    else:
        raise Exception("unrecognized time unit '" + unit + "'.")


def findDeltaTimeMultiplier(time):
    """find the multiplier to convert delta_time to seconds

    It only parses unit in day, hour, minute and second.
    It won't recognize week, month, year, millisecond, microsecond or nanosecond, they can be added if needed.

    :param time: str
        time with unit
    :return: int
        the multiplier to convert delta_time to seconds
    """
    unit = ''.join(filter(str.isalpha, time))
    timeNum = int(''.join(filter(str.isdigit, time)))
    if "d" == unit or "day" == unit or "days" == unit:
        return 24 * 60 * 60
    elif "h" == unit or "hour" == unit or "hours" == unit:
        return 60 * 60
    elif "m" == unit or "min" == unit or "minute" == unit or "minutes" == unit:
        return 60
    elif "s" == unit or "sec" == unit or "second" == unit or "seconds" == unit:
        return 1
    else:
        raise Exception("unrecognized time unit '" + unit + "'.")


"""Class that includes error to the known Weather data 

Implements the range of values the errors are randomly selected. The range is time
dependent, i.e., the next hour range of errors are smaller than other error ranges.
The error range is referred to as "envelope" (error envelope of possible variables).
The envelope increases linearly.

The class also possesses a time varying bias which will displace one side of the 
envelope. However, only one side, thus not changing the maximum possible errors.

All the variables utilize in the class are time dependent. Thus, arrays where 
element "0" is the next hour and so forth.   

"""


class weather_forecast:
    """This object includes the error to a weather variable

    Args:
        variable (str): Type of weather variable being forecasted
        period (int): period of the sinusoidal bias
        W_dict (dict): dictionary for specifying the generation of the error envelope

    Attributes:
        weather_variable (str): Type of weather variable being forecasted
        # Type of error insertion
        distribution (int): type of distribution --> 0 uniform;1 triangular;2 truncated normal the standard deviation is computed for 95% of values to be within bounds in a conventional normal distribution
        P_e_bias (float): pu maximum bias at first hour --> [0 to 1]
        P_e_envelope (float): pu maximum error from mean values --> [0 to 1]
        Lower_e_bound (float): pu of the maximum error at the first hour --> [0 to 1]
        # Bias variable
        biasM (float) (1 X period): sinusoidal bias for altering the error envelope
        Period_bias (int): period of the sinusoidal bias
    """

    def __init__(self, variable, period, W_dict):
        """Initializes the class
        """
        self.weather_variable = variable
        self.Period_bias = period
        ############## Including a bias to the envelope
        # sinusoidal with a period of two times the size of y
        self.biasM = numpy.sin(numpy.linspace(-numpy.pi, numpy.pi, (period + 1)))
        self.biasM = self.biasM[:-1]
        self.forecastParameters = W_dict
        self.distribution = W_dict[variable]["distribution"]
        self.P_e_bias = W_dict[variable]["P_e_bias"]
        self.P_e_envelope = W_dict[variable]["P_e_envelope"]
        self.Lower_e_bound = W_dict[variable]["Lower_e_bound"]

    def get_truncated_normal(self, EL, EH):
        """Truncated normal distribution
        """
        mean = (EL + EH) / 2
        sd = (abs(EL) + abs(EH)) / 4  # 95% of values are within bounds remaining is truncated
        if sd <= 0.0:
            return 0.0
        a = (EL - mean) / sd
        b = (EH - mean) / sd
        sample = truncnorm.rvs(a, b, loc=mean, scale=sd, size=1)[0]
        return sample

    def make_forecast(self, weather, t=0):
        """Include error to a known weather variable

        Args:
            weather (float) (1 x desired number of hours ahead): known weather variable
            t (int): time in hours

        Returns:
            weather_f (float) (1 x desired number of hours ahead): weather variable with included error
            ENV_U (float) (1 x desired number of hours ahead): envelope with bias upper bound
            ENV_l (float) (1 x desired number of hours ahead): envelope with bias lower bound

        """
        ############## Making the error envelope
        scale = numpy.linspace(self.Lower_e_bound, 1, num=len(weather))  # error increases true time
        envelope = scale * numpy.mean(weather) * self.P_e_envelope
        ############## Including a bias to the envelope
        bias = self.biasM * (min(envelope) * 2 * self.P_e_bias)
        bias = numpy.roll(bias, -t)
        ############## making the error array
        n = len(weather)
        error = numpy.zeros(n)
        ############## sampling the error distribution
        ENV_l = list()
        ENV_U = list()
        for i in range(n):
            if bias[i] > 0:
                EL = -envelope[i] + bias[i]
                EH = envelope[i]
            else:
                EL = -envelope[i]
                EH = envelope[i] + bias[i]
            ENV_l.append(EL)
            ENV_U.append(EH)
            if self.distribution == 0:  # uniform
                error[i] = random.uniform(EL, EH)
            elif self.distribution == 1:  # triangular
                error[i] = random.triangular(EL, EH)
            elif self.distribution == 2:  # truncated normal 95%
                error[i] = self.get_truncated_normal(EL, EH)

        weather_f = error + weather
        return weather_f


if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit()
    inputFile = sys.argv[1]
    startWeatherAgent(inputFile)
