import string;
import sys;
import tesp_support.fncs as fncs;
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

def precool_loop (nhours, metrics_root):
  time_stop = int (3600 * nhours)

  lp = open (metrics_root + "_agent_dict.json").read()
  dict = json.loads(lp)
  precool_meta = {'temperature_deviation_min':{'units':'degF','index':0},
                  'temperature_deviation_max':{'units':'degF','index':1},
                  'temperature_deviation_avg':{'units':'degF','index':2}}
  StartTime = "2013-07-01 00:00:00 PST"
  precool_metrics = {'Metadata':precool_meta,'StartTime':StartTime}

  dt = dict['dt']
  mean = dict['mean']
  stddev = dict['stddev']
  period = dict['period']
  k = dict['k_slope']

  print ('run till', time_stop, 'period', period, 'step', dt, 'mean', mean, 'stddev', stddev, 'k_slope', k)

  fncs.initialize()

  time_granted = 0
  price = 0.11 # mean

  # time_next = dt
  voltages = {}
  temperatures = {}
  setpoints = {} # publish a new one only if changed
  lastchange = {}
  precooling_quiet = 4 * 3600
  precooling_off = 25 * 3600 # never turns off
  precooling_status = {}
  lockout_period = 360

  bSetDeadbands = True
  nPrecoolers = 0

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
          voltages[houseName] = parse_fncs_magnitude (value)
        elif pair[1] == 'Tair':
          temperatures[houseName] = parse_fncs_magnitude (value)

    if bSetDeadbands:
      bSetDeadbands = False
      print ('setting thermostat deadbands and heating setpoints at', time_granted)
      # set all of the house deadbands and initial setpoints
      for house, row in dict['houses'].items():
        topic = house + '_thermostat_deadband'
        value = row['deadband']
        fncs.publish (topic, value)
        setpoints[house] = 0.0
        lastchange[house] = -lockout_period
        precooling_status[house] = False
        fncs.publish (house + '_heating_setpoint', 60.0)

    # update all of the house setpoints
    count_temp_dev = 0
    sum_temp_dev = 0.0
    min_temp_dev = 10000.0
    max_temp_dev = 0.0
    for house, row in dict['houses'].items():
      # time-scheduled setpoints
      if hour_of_day >= row['day_start_hour'] and hour_of_day <= row['day_end_hour']:
        value = row['day_set']
      else:
        value = row['night_set']
      # comfort metrics
      if house in temperatures:
        temp_dev = abs (temperatures[house] - value)
        if temp_dev < min_temp_dev:
          min_temp_dev = temp_dev
        if temp_dev > max_temp_dev:
          max_temp_dev = temp_dev
        sum_temp_dev += temp_dev
        count_temp_dev += 1
      # time-of-day price response
      tdelta = (price - mean) * row['deadband'] / k / stddev
      value += tdelta
      # overvoltage checks
      if time_granted >= precooling_quiet and not precooling_status[house]:
        if house in voltages:
          if voltages[house] > row['vthresh']:
            precooling_status[house] = True
            nPrecoolers += 1
      elif time_granted >= precooling_off:
        precooling_status[house] = False
      # overvoltage response
      if precooling_status[house]:
        value += row['toffset']
      if abs(value - setpoints[house]) > 0.1:
        if (time_granted - lastchange[house]) > lockout_period:
          topic = house + '_cooling_setpoint'
          fncs.publish (topic, value)
          setpoints[house] = value
          lastchange[house] = time_granted
          print ('setting',house,'to',value,'at',time_granted,'precooling',precooling_status[house])

    if count_temp_dev < 1:
      count_temp_dev = 1
      min_temp_dev = 0.0
    precool_metrics[str(time_granted)] = [min_temp_dev,max_temp_dev,sum_temp_dev/count_temp_dev]

    time_next = time_granted + dt

  print (nPrecoolers, 'houses participated in precooling')
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

