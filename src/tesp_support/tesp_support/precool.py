# Copyright (C) 2018-2022 Battelle Memorial Institute
# file: precool.py
"""Classes for NIST TE Challenge 2 example

The precool_loop class manages time stepping and FNCS messages
for the precooler agents, which adjust thermostat setpoints in 
response to time-of-use rates and overvoltages. The precooler agents
also estimate house equivalent thermal parameter (ETP) models based
on total floor area, number of stories, number of exterior doors and
and estiamted thermal integrity level. This ETP estimate serves as
an example for other agent developers; it's not actually used by the
precooler agent.

Public Functions:
    :precooler_loop: Initializes and runs the precooler agents.  
"""

import sys
import logging as log

try:
    import helics
except:
    pass
try:
    import tesp_support.fncs as fncs
except:
    pass

import json
import math

if sys.platform != 'win32':
    import resource

from .helpers import parse_number
from .helpers import parse_magnitude_2

thermalIntegrity = {
    'VERY_LITTLE':
        {'Rroof': 11.0, 'Rwall': 4.0, 'Rfloor': 4.0, 'Rdoors': 3.0, 'Rwindows': 1/1.27, 'airchange_per_hour': 1.5},
    'LITTLE':
        {'Rroof': 19.0, 'Rwall': 11.0, 'Rfloor': 4.0, 'Rdoors': 3.0, 'Rwindows': 1/0.81, 'airchange_per_hour': 1.5},
    'BELOW_NORMAL':
        {'Rroof': 19.0, 'Rwall': 11.0, 'Rfloor': 11.0, 'Rdoors': 3.0, 'Rwindows': 1/0.81, 'airchange_per_hour': 1.0},
    'NORMAL':
        {'Rroof': 30.0, 'Rwall': 11.0, 'Rfloor': 19.0, 'Rdoors': 3.0, 'Rwindows': 1/0.60, 'airchange_per_hour': 1.0},
    'ABOVE_NORMAL':
        {'Rroof': 30.0, 'Rwall': 19.0, 'Rfloor': 11.0, 'Rdoors': 3.0, 'Rwindows': 1/0.60, 'airchange_per_hour': 1.0},
    'GOOD':
        {'Rroof': 30.0, 'Rwall': 19.0, 'Rfloor': 22.0, 'Rdoors': 5.0, 'Rwindows': 1/0.47, 'airchange_per_hour': 0.5},
    'VERY_GOOD':
        {'Rroof': 48.0, 'Rwall': 22.0, 'Rfloor': 30.0, 'Rdoors': 11.0, 'Rwindows': 1/0.31, 'airchange_per_hour': 0.5},
    'UNKNOWN':
        {'Rroof': 30.0, 'Rwall': 19.0, 'Rfloor': 22.0, 'Rdoors': 5.0, 'Rwindows': 1/0.47, 'airchange_per_hour': 0.5}
}


class precooler:
    """This agent manages the house thermostat for time-of-use and overvoltage responses.

    References:
      `NIST TE Modeling and Simulation Challenge <https://www.nist.gov/engineering-laboratory/smart-grid/hot-topics/transactive-energy-modeling-and-simulation-challenge>`_

    Args:
      name (str): name of this agent
      agentrow (dict): row from the FNCS configuration dictionary for this agent
      gldrow (dict): row from the GridLAB-D metadata dictionary for this agent's house
      k (float): bidding function denominator, in multiples of stddev
      mean (float): mean of the price
      stddev (float): standard deviation of the price
      lockout_time (float): time in seconds between allowed changes due to voltage
      precooling_quiet (float): time of day in seconds when precooling is allowed
      precooling_off (float): time of day in seconds when overvoltage precooling is always turned off

    Attributes:
      name (str): name of this agent
      meterName (str):name of the corresponding triplex_meter in GridLAB-D, from agentrow
      night_set (float): preferred thermostat setpoint during nighttime hours, deg F, from agentrow
      day_set (float): preferred thermostat setpoint during daytime hours, deg F, from agentrow
      day_start_hour (float): hour of the day when daytime thermostat setting period begins, from agentrow
      day_end_hour (float): hour of the day when daytime thermostat setting period ends, from agentrow
      deadband (float): thermostat deadband in deg F, invariant, from agentrow, from agentrow
      vthresh (float): meter line-to-neutral voltage that triggers precooling, from agentrow
      toffset (float): temperature setpoint change for precooling, in deg F, from agentrow
      k (float): bidding function denominator, in multiples of stddev
      mean (float): mean of the price
      stddev (float): standard deviation of the price
      lockout_time (float): time in seconds between allowed changes due to voltage
      precooling_quiet (float): time of day in seconds when precooling is allowed
      precooling_off (float): time of day in seconds when overvoltage precooling is always turned off
      air_temp (float): current air temperature of the house in deg F
      mtr_v (float): current line-neutral voltage at the triplex meter
      basepoint (float): the preferred time-scheduled thermostat setpoint in deg F
      setpoint (float): the thermostat setpoint, including price response, in deg F
      lastchange (float): time of day in seconds when the setpoint was last changed
      precooling (Boolean): True if the house is precooling, False if not
      ti (int): thermal integrity level, as enumerated for GridLAB-D, from gldrow
      sqft (float: total floor area in square feet, from gldrow
      stories (int): number of stories, from gldrow
      doors (int): number of exterior doors, from gldrow
      UA (float): heat loss coefficient
      CA (float): total air thermal mass
      HM (float): interior mass surface conductance
      CM (float): total house thermal mass
    """

    def make_etp_model(self):
        """ Sets the ETP parameters from configuration data

        References:
            `Thermal Integrity Table Inputs and Defaults <http://gridlab-d.shoutwiki.com/wiki/Residential_module_user%27s_guide#Thermal_Integrity_Table_Inputs_and_Defaults>`_
        """
        Rc = thermalIntegrity[self.ti]['Rroof']
        Rw = thermalIntegrity[self.ti]['Rwall']
        Rf = thermalIntegrity[self.ti]['Rfloor']
        Rg = thermalIntegrity[self.ti]['Rwindows']  # g for glazing
        Rd = thermalIntegrity[self.ti]['Rdoors']
        I = thermalIntegrity[self.ti]['airchange_per_hour']
        # some hard-coded GridLAB-D defaults
        aspect = 1.5  # footprint x/y ratio
        A1d = 19.5  # area of one door
        h = 8.0  # ceiling height
        ECR = 1.0  # exterior ceiling fraction
        EFR = 1.0  # exterior floor fraction
        EWR = 1.0  # exterior wall fraction
        WWR = 0.15  # window to exterior wall ratio, 0.07 in the Wiki and 0.15 in GLD
        IWR = 1.5  # interior to exterior wall ratio
        mf = 2.0  # thermal mass per unit floor area, GridLAB-D default is 2 but the TE30 houses range from 3 to almost 5
        hs = 1.46  # interior heat transfer coefficient
        VHa = 0.018

        Ac = (self.sqft / self.stories) * ECR  # ceiling area
        Af = (self.sqft / self.stories) * EFR  # floor area
        perimeter = 2 * (1 + aspect) * math.sqrt(Ac / aspect)  # exterior perimeter
        Awt = self.stories * h * perimeter  # gross exterior wall area
        Ag = WWR * Awt * EWR  # gross window area
        Ad = self.doors * A1d  # total door area
        Aw = (Awt - Ag - Ad) * EWR  # net exterior wall area, taking EWR as 1s
        Vterm = self.sqft * h * VHa

        self.UA = (Ac / Rc) + (Ad / Rd) + (Af / Rf) + (Ag / Rg) + (Aw / Rw) + Vterm * I
        self.CA = 3 * Vterm
        self.HM = hs * (Aw / EWR + Awt * IWR + Ac * self.stories / ECR)
        self.CM = self.sqft * mf - 2 * Vterm

        print('ETP model', self.name, self.ti, '{:.2f}'.format(self.sqft), str(self.stories), str(self.doors))
        print('  UA', '{:.2f}'.format(self.UA))
        print('  CA', '{:.2f}'.format(self.CA))
        print('  HM', '{:.2f}'.format(self.HM))
        print('  CM', '{:.2f}'.format(self.CM))

    def __init__(self, name, agentrow, gldrow, k, mean, stddev, lockout_time, precooling_quiet, precooling_off, bPrice,
                 bVoltage):
        self.name = name  # house name
        self.sqft = gldrow['sqft']
        self.ti = gldrow['thermal_integrity']
        self.stories = gldrow['stories']
        self.doors = gldrow['doors']
        self.meterName = agentrow['meter']
        self.night_set = agentrow['night_set']
        self.day_set = agentrow['day_set']
        self.day_start_hour = agentrow['day_start_hour']
        self.day_end_hour = agentrow['day_end_hour']
        self.deadband = agentrow['deadband']
        self.vthresh = agentrow['vthresh']
        self.toffset = agentrow['toffset']

        # price response
        self.bPrice = bPrice
        self.k = k
        self.mean = mean
        self.stddev = stddev

        # voltage response
        self.bVoltage = bVoltage
        self.lockout_time = lockout_time
        self.precooling_quiet = precooling_quiet
        self.precooling_off = precooling_off
        self.mtr_v = 120.0
        self.air_temp = 78.0
        self.setpoint = 0.0
        self.basepoint = self.night_set
        self.lastchange = -lockout_time
        self.precooling = False

        self.make_etp_model()

    def set_air_temp(self, val):
        """Set the air_temp member variable

        Args:
            val (str): FNCS/HELICS message with temperature in degrees Fahrenheit
        """
        self.air_temp = parse_number(val)

    def set_voltage_f(self, val):
        """ Sets the mtr_v attribute

        Args:
            val (str): FNCS message with meter line-neutral voltage
        """
        self.mtr_v = parse_magnitude_2(val)

    def set_voltage(self, val):
        """ Sets the mtr_v attribute

        Args:
            val (str): HELICS message with meter line-neutral voltage
        """
        self.mtr_v = abs(val)

    def check_setpoint_change(self, hour_of_day, price, time_seconds):
        """Update the setpoint for time of day and price

        Args:
            hour_of_day (float): the current time of day, 0..24
            price (float): the current price in $/kwh
            time_seconds (long long): the current FNCS time in seconds

        Returns:
            Boolean: True if the setpoint changed, False if not
        """
        # time-scheduled changes to the basepoint
        if self.day_start_hour <= hour_of_day <= self.day_end_hour:
            self.basepoint = self.day_set
        else:
            self.basepoint = self.night_set
        new_setpoint = self.basepoint
        # time-of-day price response
        if self.bPrice:
            tdelta = (price - self.mean) * self.deadband / self.k / self.stddev
            new_setpoint += tdelta
        # overvoltage checks and response
        if self.bVoltage:
            if hour_of_day >= self.precooling_quiet and not self.precooling:
                if self.mtr_v > self.vthresh:
                    self.precooling = True
            elif hour_of_day >= self.precooling_off:
                self.precooling = False
            if self.precooling:
                new_setpoint += self.toffset
        # is the new setpoint different from the existing setpoint?
        if abs(new_setpoint - self.setpoint) > 0.1:
            if (time_seconds - self.lastchange) > self.lockout_time:
                self.setpoint = new_setpoint
                self.lastchange = time_seconds
                return True
        return False

    def get_temperature_deviation(self):
        """For metrics, find the difference between air temperature and time-scheduled (preferred) setpoint

        Returns:
            float: absolute value of deviation
        """
        return abs(self.air_temp - self.basepoint)


def helics_precool_loop(nhours, metrics_root, dict_root, response, helicsConfig):
    """Function that supervises FNCS messages and time stepping for precooler agents

    Opens metrics_root_agent_dict.json and metrics_root_glm_dict.json for configuration.
    Writes precool_metrics_root.json at completion.

    Args:
      nhours (float): number of hours to simulate
      metrics_root (str): name of the case, without file extension
      dict_root (str): repeat metrics_root, or the name of a shared case dictionary without file extension
      response (str): combination of Price and/or Voltage
      helicsConfig (str): name for HELICS message file
    """

    time_stop = int(3600 * nhours)

    lp = open(dict_root + '_agent_dict.json').read()
    diction = json.loads(lp)
    gp = open(dict_root + '_glm_dict.json').read()
    glm_dict = json.loads(gp)

    bPriceResponse = False
    bVoltageResponse = False
    if 'Price' in response:
        bPriceResponse = True
    if 'Voltage' in response:
        bVoltageResponse = True

    precool_meta = {'temperature_deviation_min': {'units': 'degF', 'index': 0},
                    'temperature_deviation_max': {'units': 'degF', 'index': 1},
                    'temperature_deviation_avg': {'units': 'degF', 'index': 2}}
    StartTime = '2013-07-01 00:00:00 PST'
    precool_metrics = {'Metadata': precool_meta, 'StartTime': StartTime}

    dt = diction['dt']

    # create and initialize a controller object for each house
    mean = diction['mean']
    stddev = diction['stddev']
    # period = diction['period'] # not used
    k = diction['k_slope']
    precooling_quiet = 4  # disabled before 4 a.m.
    precooling_off = 22  # disabled after 9 p.m.
    lockout_period = 360
    precoolerObjs = {}
    house_keys = list(diction['houses'].keys())
    n_houses = len(house_keys)
    for key in house_keys:
        row = diction['houses'][key]
        gldrow = glm_dict['houses'][key]
        precoolerObjs[key] = precooler(key, row, gldrow, k, mean, stddev,
                                       lockout_period, precooling_quiet, precooling_off,
                                       bPriceResponse, bVoltageResponse)

    print('run till', time_stop, 'step', dt,
          'mean', mean, 'stddev', stddev, 'k_slope', k,
          'lockout_period', lockout_period, 'precooling_quiet', precooling_quiet, 'precooling_off', precooling_off,
          'bVoltageResponse', bVoltageResponse, 'bPriceResponse', bPriceResponse)

    log.info("Initialize HELICS tso federate")
    hFed = helics.helicsCreateValueFederateFromConfig(helicsConfig)
    fedName = helics.helicsFederateGetName(hFed)
    subCount = helics.helicsFederateGetInputCount(hFed)
    pubCount = helics.helicsFederateGetPublicationCount(hFed)
    log.info('Federate name: ' + fedName)
    log.info('Subscription count: ' + str(subCount))
    log.info('Publications count: ' + str(pubCount))
    log.info('Starting HELICS tso federate')
    helics.helicsFederateEnterExecutingMode(hFed)

    time_granted = 0
    price = 0.11  # mean
    # time_next = dt
    bSetDeadbands = True
    setPrecoolers = set()

    while time_granted < time_stop:
        time_granted = int(helics.helicsFederateRequestTime(hFed, min(time_granted + dt, time_stop)))

        hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)

        # see another example for helics integration at tso_PYPOWER.py
        for t in range(subCount):
            sub = helics.helicsFederateGetInputByIndex(hFed, t)
            key = helics.helicsSubscriptionGetTarget(sub)
            log.debug("HELICS subscription index: " + str(t) + ", key: " + key)
            topic = key.split('/')[1]
            if helics.helicsInputIsUpdated(sub):
                val = helics.helicsInputGetString(sub)
                log.debug("at " + str(time_granted) + " " + topic + " " + val)

                if topic == 'price':
                    price = float(val)
                else:
                    pair = topic.split('#')
                    houseName = pair[0]
                    if pair[1] == 'V1':
                        cval = helics.helicsInputGetComplex(sub)
                        precoolerObjs[houseName].set_voltage(cval)
                    elif pair[1] == 'Tair':
                        precoolerObjs[houseName].set_air_temp(val)

        if bSetDeadbands:
            bSetDeadbands = False
            print('setting thermostat deadbands and heating set points at', time_granted)
            for key, obj in precoolerObjs.items():
                pub = helics.helicsFederateGetPublication(hFed, key + '/thermostat_deadband')
                helics.helicsPublicationPublishDouble(pub, obj.deadband)
                pub = helics.helicsFederateGetPublication(hFed, key + '/heating_setpoint')
                helics.helicsPublicationPublishDouble(pub, 60.0)

        # update all the house set points and collect the temperature deviation metrics
        count_temp_dev = 0
        sum_temp_dev = 0.0
        min_temp_dev = 10000.0
        max_temp_dev = 0.0
        n_changes = 0
        max_changes = 25
        for key, obj in precoolerObjs.items():
            if n_changes < max_changes:
                if obj.check_setpoint_change(hour_of_day, price, time_granted):
                    print('  setting {:s} to {:.3f} at {:d} and {:.2f} volts pre-cooling'
                          .format(key, obj.setpoint, time_granted, obj.mtr_v), obj.precooling)
                    n_changes += 1
                    pub = helics.helicsFederateGetPublication(hFed, key + '/cooling_setpoint')
                    helics.helicsPublicationPublishDouble(pub, obj.setpoint)
                    if obj.precooling:
                        setPrecoolers.add(obj.name)
            temp_dev = obj.get_temperature_deviation()
            count_temp_dev += 1
            if temp_dev < min_temp_dev:
                min_temp_dev = temp_dev
            if temp_dev > max_temp_dev:
                max_temp_dev = temp_dev
            sum_temp_dev += temp_dev

        if n_changes > 0:
            print('*** {:6.4f} hr, changing {:d} set points, {:d} out of {:d} are pre-cooling'
                  .format(hour_of_day, n_changes, len(setPrecoolers), n_houses))

        if count_temp_dev < 1:
            count_temp_dev = 1
            min_temp_dev = 0.0
        precool_metrics[str(time_granted)] = [min_temp_dev, max_temp_dev, sum_temp_dev / count_temp_dev]

        time_next = time_granted + dt

    print(len(setPrecoolers), 'houses participated in precooling')
    print('writing metrics', flush=True)
    mp = open('precool_' + metrics_root + '_metrics.json', 'w')
    print(json.dumps(precool_metrics), file=mp)
    mp.close()
    print('done', flush=True)

    log.info('finalizing HELICS tso federate')
    helics.helicsFederateDestroy(hFed)


def fncs_precool_loop(nhours, metrics_root, dict_root, response):
    """Function that supervises FNCS messages and time stepping for precooler agents

    Opens metrics_root_agent_dict.json and metrics_root_glm_dict.json for configuration.
    Writes precool_metrics_root.json at completion.

    Args:
      nhours (float): number of hours to simulate
      metrics_root (str): name of the case, without file extension
      dict_root (str): repeat metrics_root, or the name of a shared case dictionary without file extension
      response (str): combination of Price and/or Voltage
    """

    time_stop = int(3600 * nhours)

    lp = open(dict_root + '_agent_dict.json').read()
    diction = json.loads(lp)
    gp = open(dict_root + '_glm_dict.json').read()
    glm_dict = json.loads(gp)

    bPriceResponse = False
    bVoltageResponse = False
    if 'Price' in response:
        bPriceResponse = True
    if 'Voltage' in response:
        bVoltageResponse = True

    precool_meta = {'temperature_deviation_min': {'units': 'degF', 'index': 0},
                    'temperature_deviation_max': {'units': 'degF', 'index': 1},
                    'temperature_deviation_avg': {'units': 'degF', 'index': 2}}
    StartTime = '2013-07-01 00:00:00 PST'
    precool_metrics = {'Metadata': precool_meta, 'StartTime': StartTime}

    dt = diction['dt']

    # create and initialize a controller object for each house
    mean = diction['mean']
    stddev = diction['stddev']
    # period = diction['period'] # not used
    k = diction['k_slope']
    precooling_quiet = 4  # disabled before 4 a.m.
    precooling_off = 22  # disabled after 9 p.m.
    lockout_period = 360
    precoolerObjs = {}
    house_keys = list(diction['houses'].keys())
    n_houses = len(house_keys)
    for key in house_keys:
        row = diction['houses'][key]
        gldrow = glm_dict['houses'][key]
        precoolerObjs[key] = precooler(key, row, gldrow, k, mean, stddev,
                                       lockout_period, precooling_quiet, precooling_off,
                                       bPriceResponse, bVoltageResponse)

    print('run till', time_stop, 'step', dt,
          'mean', mean, 'stddev', stddev, 'k_slope', k,
          'lockout_period', lockout_period, 'precooling_quiet', precooling_quiet, 'precooling_off', precooling_off,
          'bVoltageResponse', bVoltageResponse, 'bPriceResponse', bPriceResponse)

    fncs.initialize()
    time_granted = 0
    price = 0.11  # mean
    # time_next = dt
    bSetDeadbands = True
    setPrecoolers = set()

    while time_granted < time_stop:
        time_granted = fncs.time_request(time_stop)  # time_next
        hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)
        events = fncs.get_events()
        for topic in events:
            value = fncs.get_value(topic)
            if topic == 'price':
                price = float(value)
            else:
                pair = topic.split('#')
                houseName = pair[0]
                if pair[1] == 'V1':
                    precoolerObjs[houseName].set_voltage_f(value)
                elif pair[1] == 'Tair':
                    precoolerObjs[houseName].set_air_temp(value)

        if bSetDeadbands:
            bSetDeadbands = False
            print('setting thermostat deadbands and heating setpoints at', time_granted)
            for key, obj in precoolerObjs.items():
                fncs.publish(key + '_thermostat_deadband', obj.deadband)
                fncs.publish(key + '_heating_setpoint', '60.0')

        # update all of the house setpoints and collect the temperature deviation metrics
        count_temp_dev = 0
        sum_temp_dev = 0.0
        min_temp_dev = 10000.0
        max_temp_dev = 0.0
        n_changes = 0
        max_changes = 25
        for key, obj in precoolerObjs.items():
            if n_changes < max_changes:
                if obj.check_setpoint_change(hour_of_day, price, time_granted):
                    print('  setting {:s} to {:.3f} at {:d} and {:.2f} volts precooling'
                          .format(key, obj.setpoint, time_granted, obj.mtr_v), obj.precooling)
                    n_changes += 1
                    fncs.publish(key + '_cooling_setpoint', obj.setpoint)
                    if obj.precooling:
                        setPrecoolers.add(obj.name)
            temp_dev = obj.get_temperature_deviation()
            count_temp_dev += 1
            if temp_dev < min_temp_dev:
                min_temp_dev = temp_dev
            if temp_dev > max_temp_dev:
                max_temp_dev = temp_dev
            sum_temp_dev += temp_dev

        if n_changes > 0:
            print('*** {:6.4f} hr, changing {:d} setpoints, {:d} out of {:d} are pre-cooling'
                  .format(hour_of_day, n_changes, len(setPrecoolers), n_houses))

        if count_temp_dev < 1:
            count_temp_dev = 1
            min_temp_dev = 0.0
        precool_metrics[str(time_granted)] = [min_temp_dev, max_temp_dev, sum_temp_dev / count_temp_dev]

        time_next = time_granted + dt

    print(len(setPrecoolers), 'houses participated in precooling')
    print('writing metrics', flush=True)
    mp = open('precool_' + metrics_root + '_metrics.json', 'w')
    print(json.dumps(precool_metrics), file=mp)
    mp.close()
    print('done', flush=True)

    print('finalizing FNCS', flush=True)
    fncs.finalize()


def precool_loop(nhours, metrics_root, dict_root, response='PriceVoltage', helicsConfig=None):
    """Wrapper for *inner_substation_loop*

    When *inner_substation_loop* finishes, timing and memory metrics will be printed
    for non-Windows platforms.
    """
    logger = log.getLogger()
    logger.setLevel(log.INFO)
    # logger.setLevel(log.WARNING)
    # logger.setLevel(log.DEBUG)


    if helicsConfig is not None:
        helics_precool_loop(nhours, metrics_root, dict_root, response, helicsConfig)
    else:
        fncs_precool_loop(nhours, metrics_root, dict_root, response)

    #    gc.enable()
    #    gc.set_debug(gc.DEBUG_LEAK)

    #    profiler = cProfile.Profile ()
    #    args = (configfile, metrics_root, hour_stop, flag)
    #    profiler.runcall (inner_substation_loop, *args)
    #    stats = pstats.Stats(profiler)
    #    stats.strip_dirs()
    #    stats.sort_stats('cumulative')
    #    stats.print_stats()

    #    print (gc.collect (), 'unreachable objects')
    #    for x in gc.garbage:
    #        s = str(x)
    #        print (type(x), ':', len(s), flush=True)
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


#if __name__ == '__main__':
    # precool_loop('', '', '', '')
    # precool_loop('', '', '', '', helicsConfig='Test_substation.json')
