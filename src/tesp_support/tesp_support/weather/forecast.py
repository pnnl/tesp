# Copyright (C) 2019-2023 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: forecast.py

import random

import numpy
from scipy.stats import truncnorm


def convertTimeToSeconds(time):
    """ Convert time string with unit to integer in seconds

    Parses the unit in day, hour, minute and second. It will not recognize week, month, year, millisecond,
    microsecond or nanosecond, they can be added if needed.

    Args:
        time (str): time with unit
    Returns:
        int: represent the input time in second
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
        raise Exception("unrecognized time unit '" + unit + "' in " + time + ".")


def deltaTimeToResampleFreq(time):
    """ Convert time unit to a resampling frequency that can be recognized by pandas.DataFrame.resample()

    Parses unit in day, hour, minute and second. It won't recognize week, month, year, millisecond,
    microsecond or nanosecond, they can be added if needed.

    Args:
        time (str): time with unit
    Returns:
        str: time with resample frequency
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
    """ Find the multiplier to convert delta_time to seconds

    Parses unit in day, hour, minute and second. It won't recognize week, month, year, millisecond,
    microsecond or nanosecond, they can be added if needed.

    Args:
        time (str): time with unit
    Returns:
        int: the multiplier to convert delta_time to seconds
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
    """
    This object includes the error to a weather variable

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
        """ Initializes the class
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
        """
    Truncated normal distribution
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
        """ Include error to a known weather variable

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
