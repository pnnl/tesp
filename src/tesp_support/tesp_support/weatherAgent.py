"""Weather Agent

This weather agent needs an WEATHER_CONFIG environment variable to be set, which is a json file.
"""
import sys, os
import pandas as pd
import json
from datetime import datetime
from datetime import timedelta
# try:
#   import tesp_support.fncs as fncs;
# except:
#   pass
import random
import numpy
from scipy.stats import truncnorm
import time

def startWeatherAgent(file):
    """the weather agent publishes weather data as configured by the json file

    :param file: string
        the weather data file
    :return: nothing
    """
    # read the weather data file, arguments to mimic deprecated from_csv function
    weatherData = pd.read_csv(file, index_col=0, parse_dates=True)
    config = os.environ['WEATHER_CONFIG'] # read the weather config json file
    if os.path.isfile(config):
        with open(config, 'r') as stream:
            try:
                conf = json.load(stream)
                agentName = conf['name']
                broker = conf['broker']
                timeStop = conf['time_stop']
                StartTime = conf['StartTime']
                timeFormat = '%Y-%m-%d %H:%M:%S'
                dtStart = datetime.strptime (StartTime, timeFormat)
                timeDeltaStr = conf['time_delta']
                publishInterval = conf['publishInterval']
                forecast = conf['Forecast']
                addErrorToForecast = conf['AddErrorToForecast']
                forecastLength = conf['ForecastLength']
                publishTimeAhead = conf['PublishTimeAhead']
                forecastPeriod = conf['forecastPeriod']
                forecastParameters = conf['parameters']
            except json.JSONDecodeError as ex:
                print(ex)
    else:
        print('could not open FNCS_CONFIG_FILE for fncs')
        sys.exit()

    # convert some of the time in config file to seconds
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

    #write fncs.zpl file here
    #it actually worked now. # this config str won't work as an argument to fncs::initialize, so write fncs.zpl just in time
    zplstr = "name = {}\ntime_delta = {}s\ntime_stop = {}s\nbroker = {}".format(agentName, timeDeltaInSeconds, timeStopInSeconds, broker)

    # when doing resample(), use publishIntervalInSeconds to make it uniform
    # the reason for that is due to some of the units that we use for fncs, such as 'min',
    # is not recognized by the resample() function
    weatherData2 = weatherData.resample(rule=str(publishIntervalInSeconds)+"s",closed='left').first()
    weatherData2 = weatherData2.interpolate(method='quadratic')

    # find weather data on the hour for the hourly forecast
    hourlyWeatherData=weatherData.loc[(weatherData.index.minute == 0) & (weatherData.index.second == 0) & (weatherData.index.microsecond == 0) & (weatherData.index.nanosecond == 0)]
    # hourlyWeatherData=weatherData2.resample(rule='1H', how='mean') #average data within 1 hour
    # make sure time_stop and time_delta have the same unit by converting them to the uniform unit first

    # try:
    #     timeDeltaResample = deltaTimeToResmapleFreq(timeDeltaStr)
    # except Exception as ex:
    #     print("Error in time_delta", ex)
    # try:
    #     timeStopUniformUnit = deltaTimeToResmapleFreq(timeStop)
    # except Exception as ex:
    #     print("Error in time_stop", ex)
    # timeStopUnit = ''.join(filter(str.isalpha, timeStopUniformUnit))
    # timeStopNum = int(''.join(filter(str.isdigit, timeStopUniformUnit)))
    # timeDeltaUnit = ''.join(filter(str.isalpha, timeDeltaResample))
    # timeDeltaNum = int(''.join(filter(str.isdigit, timeDeltaResample)))
    # if timeStopUnit != timeDeltaUnit:
    #     print('time_stop and time_delta should have the same unit.')
    #     sys.exit()

    # find time_delta multiplier against second, so we can convert second back to the unit fncs uses
    # try:
    #     deltaTimeMultiplier = findDeltaTimeMultiplier(timeDeltaStr)
    # except Exception as ex:
    #     print("Error in time_delta", ex)

    # find all the time point that the data at that time need to be published
    timeNeedToPublishRealtime = [0]
    timeNeedToPublishForecast = [0]
    # real time need to publish
    numberOfRealtimeBroadcast = timeStopInSeconds // publishIntervalInSeconds + 1
    for i in range(1,numberOfRealtimeBroadcast):
        timeNeedToPublishRealtime.append(i * publishIntervalInSeconds)
    if forecast == 1:
        # time need to publish forecast, which is on the hour
        numberOfForecast = timeStopInSeconds // 3600 + 1
        for i in range(1,numberOfForecast):
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
    # zplName = agentName + '.zpl'
    # zpl = open(zplName, "w")
    # print(zplstr, file=zpl)
    # zpl.close()
    # print(zplName, 'file generated with:', flush=True)
    # print(zplstr, flush=True)

    # import platform
    # if platform.system() == "Windows":
    #     import ctypes, ctypes.util
    #     a = ctypes.util.find_library("msvcrt")
    #     b = ctypes.cdll[a]
    #     b._putenv(f"FNCS_CONFIG_FILE={zplName}")
    #     print(b._environ)
    #     #ctypes.cdll[ctypes.util.find_library("msvcrt")]._putenv(f"FNCS_CONFIG_FILE={zplName}")
    #     libc = ctypes.cdll.msvcrt
    #     libc._putenv(f"FNCS_CONFIG_FILE={zplName}")
    #     print(libc._environ)
    #     # error: ctypes.cdll[libc]._putenv(f"FNCS_CONFIG_FILE={zplName}")
    #
    # os.environ['FNCS_CONFIG_FILE'] = zplName
#    print (os.environ, flush=True)
    try:
        import tesp_support.fncs as fncs
    except:
        pass
    configstr = zplstr.encode('utf-8')
    fncs.initialize(configstr)
    #fncs.initialize()
    print('FNCS initialized', flush=True)
    # os.remove(zplName)
    # print(zplName, 'file deleted', flush=True)

    time_granted = 0
    #timeDeltaChanged = 0
    for i in range(len(timeNeedToPublish)):
        #print("i", i)
        if i > 0:
	    #     timeToRequest = timeNeedToPublish[i] - timeNeedToPublish[i-1]
	    # else:
            timeToRequest = timeNeedToPublish[i]
            #print("timeToRequest", timeToRequest)
            # if requested time is not multiple of time_delta, update time_delta to time requested
            # since fncs require requested time to be multiple of time_delta
            #if (timeToRequest - time_granted) % timeDeltaInSeconds != 0:
                # if timeToRequest % publishTimeAhead == 0:
                #     fncs.update_time_delta(publishTimeAhead)
                # else:
            #    fncs.update_time_delta(1)
            #    print("time delta updated to 1s.", flush=True)
            #    timeDeltaChanged = 1
            time_granted = fncs.time_request(timeToRequest)
            #print("time_granted", time_granted)
            #if timeDeltaChanged == 1:
            #    fncs.update_time_delta(timeDeltaInSeconds)
            #    print("time delta updated to " + str(timeDeltaInSeconds) + "s.", flush=True)
            #    timeDeltaChanged = 0
	# if the time need to be published is real time
        if timeNeedToBePublished[i] in timeNeedToPublishRealtime:
            # find the data by the time point and publish them
            row = weatherData2.loc[dtStart + timedelta(seconds=timeNeedToBePublished[i])]
            print('publishing at ' + str(dtStart + timedelta(seconds=timeNeedToPublish[i]))
                  + ' for weather at ' + str(dtStart + timedelta(seconds=timeNeedToBePublished[i])), flush=True)
            for key, value in row.iteritems():
                #remove the inproper value generated by interpolation
                if key != "temperature" and value < 1e-4:
                    value = 0
                fncs.publish(key, value)
        # if forecasting needed and the time is on the hour
        if forecast == 1 and timeNeedToBePublished[i] in timeNeedToPublishForecast:
            print('forecasting at ' + str(dtStart + timedelta(seconds=timeNeedToPublish[i])) + ' for weather starting from '
                  + str(dtStart + timedelta(seconds=timeNeedToBePublished[i])), flush=True)
            forecastStart = dtStart + timedelta(seconds=timeNeedToBePublished[i])
            forecastEnd = dtStart + timedelta(seconds=forecastLength) + timedelta(seconds=timeNeedToBePublished[i])
            # find the data by forecast starting and ending time, should be multiple data point for each weather factor
            rows = hourlyWeatherData.loc[(hourlyWeatherData.index >= forecastStart) & (hourlyWeatherData.index < forecastEnd)].copy()
            #rows.is_copy = None
            #remove the inproper value generated by interpolation
            #rows.solar_direct[rows.solar_direct<0]=0
            rows.solar_direct[rows.solar_direct<1e-4]=0
            #rows.solar_diffuse[rows.solar_diffuse<0]=0
            rows.solar_diffuse[rows.solar_diffuse<1e-4]=0
            #rows.wind_speed[rows.wind_speed<0]=0
            rows.wind_speed[rows.wind_speed<1e-4]=0
            rows.humidity[rows.humidity<1e-4]=0
            rows.pressure[rows.pressure<1e-4]=0
            for col in rows.columns:
                data = rows[col].values
                times = rows.index
                # if user wants to add error to the forecasted data to mimick weather forecast
                if addErrorToForecast == 1:
                    WF_obj = weather_forecast(col, forecastPeriod * 2, forecastParameters)  # make object
                    data = WF_obj.make_forecast(data, len(data))
                wd = dict()
                # convert data to a dictionary with time as the key so it can be published as json string
                for v in range(len(data)):
                    if col != "temperature" and data[v] < 1e-4:
                        data[v] = 0
                    wd[str(times[v])] = str(data[v])
                fncs.publish(col + '/forecast', json.dumps(wd))
    # if the last time step/stop time is not requested
    if timeStopInSeconds not in timeNeedToPublish:
        #if (timeStopInSeconds - time_granted) % timeDeltaInSeconds != 0:
        #    fncs.update_time_delta(1)
        #    timeDeltaChanged = 1
        time_granted = fncs.time_request(timeStopInSeconds)
        #if timeDeltaChanged == 1:
        #    fncs.update_time_delta(timeDeltaInSeconds)
        #    timeDeltaChanged == 0

    # # Jacob suggested implementation
    # tnext_publish = publishIntervalInSeconds - publishTimeAhead
    # print("before while, time_granted: ", time_granted, flush=True)
    # while time_granted < timeStopInSeconds:
    #     # determine the next FNCS time
    #     next_fncs_time = int(min([tnext_publish, timeStopInSeconds]))
    #     # with that new FNCS value update the delta time to ensure we only get returned at that time
    #     fncs.update_time_delta(next_fncs_time-time_granted)
    #     print("tnext_publish: ", tnext_publish, flush=True)
    #     print("next_fncs_time: ", next_fncs_time, flush=True)
    #     print("next_fncs_time-time_granted: ", next_fncs_time-time_granted, flush=True)
    #     # call time request to move to this new time
    #     time_granted = fncs.time_request(next_fncs_time)
    #     print("time_granted: ", time_granted, flush=True)
    #
    #     # update the next time to publish
    #     tnext_publish += publishIntervalInSeconds
    #     print("update tnext_publish", flush=True)

    print('finalizing FNCS', flush=True)
    fncs.finalize()

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
    if ("d" == unit or "day" == unit or "days" == unit):
        return 24 * 60 * 60 * timeNum
    elif ("h" == unit or "hour" == unit or "hours" == unit):
        return 60 * 60 * timeNum
    elif ("m" == unit or "min" == unit or "minute" == unit or "minutes" == unit):
        return 60 * timeNum
    elif ("s" == unit or "sec" == unit or "second" == unit or "seconds" == unit):
        return timeNum
    else:
        raise Exception("unrecognized time unit '" + unit + "'.")

def deltaTimeToResmapleFreq(time):
    """Convert time unit to a resampling frequency that can be recognized by pandas.DataFrame.resample()

    It only parse unit in day, hour, minute and second.
    It won't recognize week, month, year, millisecond, microsecond or nanosecond, they can be added if needed.

    :param time: str
        time with unit
    :return: str
        time with resample frequency
    """
    unit = ''.join(filter(str.isalpha, time))
    timeNum = int(''.join(filter(str.isdigit, time)))
    if ("d" == unit or "day" == unit or "days" == unit):
        return str(timeNum) + "d"
    elif ("h" == unit or "hour" == unit or "hours" == unit):
        return str(timeNum) + "h"
    elif ("m" == unit or "min" == unit or "minute" == unit or "minutes" == unit):
        return str(timeNum) + "T"
    elif ("s" == unit or "sec" == unit or "second" == unit or "seconds" == unit):
        return str(timeNum) + "s"
    else:
        raise Exception("unrecognized time unit '" + unit + "'.")

def findDeltaTimeMultiplier(time):
    """find the multiplier to convert delta_time to seconds

    It only parse unit in day, hour, minute and second.
    It won't recognize week, month, year, millisecond, microsecond or nanosecond, they can be added if needed.

    :param time: str
        time with unit
    :return: int
        the multiplier to convert delta_time to seconds
    """
    unit = ''.join(filter(str.isalpha, time))
    timeNum = int(''.join(filter(str.isdigit, time)))
    if ("d" == unit or "day" == unit or "days" == unit):
        return 24 * 60 * 60
    elif ("h" == unit or "hour" == unit or "hours" == unit):
        return 60 * 60
    elif ("m" == unit or "min" == unit or "minute" == unit or "minutes" == unit):
        return 60
    elif ("s" == unit or "sec" == unit or "second" == unit or "seconds" == unit):
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
        mean=(EL+EH)/2
        sd=(abs(EL)+abs(EH))/4 #95% of values are within bounds remaining is truncated
        if sd <= 0.0:
            return 0.0
        a = (EL - mean) / sd
        b = (EH - mean) / sd
        sample = truncnorm.rvs(a,b,loc=mean,scale=sd,size=1)[0]
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
