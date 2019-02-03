# Copyright (C) 2018-2019 Battelle Memorial Institute
# file: precool.py
import string;
import sys;
try:
  import tesp_support.fncs as fncs;
except:
  pass
import json;
import math;
import re;
if sys.platform != 'win32':
  import resource

def parse_fncs_magnitude (arg):
  tok = arg.strip('+-; MWVAFKdegrij')
  vals = re.split(r'[\+-]+', tok)
  if len(vals) < 2: # only a real part provided
    vals.append('0')
#  vals = [float(v) for v in vals]
#
#  if '-' in tok:
#    vals[1] *= -1.0
  vals[0] = float(vals[0])
  if arg.startswith('-'):
    vals[0] *= -1.0
  return vals[0]

class precooler:
  def make_etp_model(self):
    self.UA = 0.0
    self.CA = 0.0
    self.UM = 0.0
    self.CM = 0.0
    print ('ETP model', self.name, self.ti, '{:.2f}'.format (self.sqft), str(self.stories), str(self.doors))
    print ('  UA', '{:.2f}'.format (self.UA))
    print ('  CA', '{:.2f}'.format (self.CA))
    print ('  UM', '{:.2f}'.format (self.UM))
    print ('  CM', '{:.2f}'.format (self.CM))

  def __init__(self,name,agentrow,gldrow,k,mean,stddev,lockout_time,precooling_quiet,precooling_off):
    self.name = name # house name
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
    self.k = k
    self.mean = mean
    self.stddev = stddev

    # voltage response
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

  def set_air_temp (self,str):
    self.air_temp = parse_fncs_magnitude (str)

  def set_voltage (self,str):
    self.mtr_v = parse_fncs_magnitude (str)

  def check_setpoint_change (self, hour_of_day, price, time_seconds):
    # time-scheduled changes to the basepoint
    if hour_of_day >= self.day_start_hour and hour_of_day <= self.day_end_hour:
      self.basepoint = self.day_set
    else:
      self.basepoint = self.night_set
    new_setpoint = self.basepoint
    # time-of-day price response
    tdelta = (price - self.mean) * self.deadband / self.k / self.stddev
    new_setpoint += tdelta
    # overvoltage checks
    if hour_of_day >= self.precooling_quiet and not self.precooling:
      if self.mtr_v > self.vthresh:
        self.precooling = True
    elif hour_of_day >= self.precooling_off:
      self.precooling = False
    # overvoltage response
    if self.precooling:
      new_setpoint += self.toffset
    if abs(new_setpoint - self.setpoint) > 0.1:
      if (time_seconds - self.lastchange) > self.lockout_time:
        self.setpoint = new_setpoint
        self.lastchange = time_seconds
        return True
    return False

  def get_temperature_deviation(self):
    return abs (self.air_temp - self.basepoint)

def precool_loop (nhours, metrics_root):
  time_stop = int (3600 * nhours)

  lp = open (metrics_root + "_agent_dict.json").read()
  dict = json.loads(lp)
  gp = open (metrics_root + "_glm_dict.json").read()
  glm_dict = json.loads(gp)

  precool_meta = {'temperature_deviation_min':{'units':'degF','index':0},
                  'temperature_deviation_max':{'units':'degF','index':1},
                  'temperature_deviation_avg':{'units':'degF','index':2}}
  StartTime = "2013-07-01 00:00:00 PST"
  precool_metrics = {'Metadata':precool_meta,'StartTime':StartTime}

  dt = dict['dt']

  # create and initialize a controller object for each house
  mean = dict['mean']
  stddev = dict['stddev']
  # period = dict['period'] # not used
  k = dict['k_slope']
  precooling_quiet = 4 # disabled before 4 a.m.
  precooling_off = 22 # disabled after 9 p.m.
  lockout_period = 360
  precoolerObjs = {}
  house_keys = list(dict['houses'].keys())
  for key in house_keys:
    row = dict['houses'][key]
    gldrow = glm_dict['houses'][key]
    precoolerObjs[key] = precooler (key, row, gldrow, k, mean, stddev, 
                                    lockout_period, precooling_quiet, precooling_off)

  print ('run till', time_stop, 'step', dt, 
         'mean', mean, 'stddev', stddev, 'k_slope', k,
         'lockout_period', lockout_period, 'precooling_quiet', precooling_quiet, 'precooling_off', precooling_off)

  fncs.initialize()
  time_granted = 0
  price = 0.11 # mean
  # time_next = dt
  bSetDeadbands = True
  setPrecoolers = set()

  while time_granted < time_stop:
    time_granted = fncs.time_request(time_stop) # time_next
    hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)
    events = fncs.get_events()
    for topic in events:
      value = fncs.get_value(topic)
      if topic == 'price':
        price = float(value)
      else:
        pair = topic.split ('#')
        houseName = pair[0]
        if pair[1] == 'V1':
          precoolerObjs[houseName].set_voltage (value)
        elif pair[1] == 'Tair':
          precoolerObjs[houseName].set_air_temp (value)

    if bSetDeadbands:
      bSetDeadbands = False
      print ('setting thermostat deadbands and heating setpoints at', time_granted)
      for key, obj in precoolerObjs.items():
        fncs.publish (key + '_thermostat_deadband', obj.deadband)
        fncs.publish (key + '_heating_setpoint', 60.0)

    # update all of the house setpoints and collect the temperature deviation metrics
    count_temp_dev = 0
    sum_temp_dev = 0.0
    min_temp_dev = 10000.0
    max_temp_dev = 0.0
    for key, obj in precoolerObjs.items():
      if obj.check_setpoint_change (hour_of_day, price, time_granted):
        print ('setting',key,'to',obj.setpoint,'at',time_granted,'precooling',obj.precooling)
        fncs.publish (key + '_cooling_setpoint', obj.setpoint)
        if obj.precooling:
          setPrecoolers.add (obj.name)
      temp_dev = obj.get_temperature_deviation()
      count_temp_dev += 1
      if temp_dev < min_temp_dev:
        min_temp_dev = temp_dev
      if temp_dev > max_temp_dev:
        max_temp_dev = temp_dev
      sum_temp_dev += temp_dev

    if count_temp_dev < 1:
      count_temp_dev = 1
      min_temp_dev = 0.0
    precool_metrics[str(time_granted)] = [min_temp_dev,max_temp_dev,sum_temp_dev/count_temp_dev]

    time_next = time_granted + dt

  print (len(setPrecoolers), 'houses participated in precooling')
  print ('writing metrics', flush=True)
  mp = open ("precool_" + metrics_root + "_metrics.json", "w")
  print (json.dumps(precool_metrics), file=mp)
  mp.close()
  print ('done', flush=True)

  print ('finalizing FNCS', flush=True)
  fncs.finalize()

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

