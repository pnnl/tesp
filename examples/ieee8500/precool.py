import string;
import sys;
import fncs;
import json;
import math;

import re;

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

time_stop = 3600 * int(sys.argv[1])

lp = open (sys.argv[2] + "_agent_dict.json").read()
dict = json.loads(lp)
mp = open ("precool_" + sys.argv[2] + "_metrics.json", "w")
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
#print (dict['houses'])

fncs.initialize()

time_granted = 0
price = mean

# time_next = dt
voltages = {}
temperatures = {}

# set all of the house deadbands and initial setpoints
for house, row in dict['houses'].items():
  topic = house + '_thermostat_deadband'
  value = row['deadband']
  fncs.publish (topic, value)
  topic = house + '_cooling_setpoint'
  value = row['night_set']
  fncs.publish (topic, value)


while time_granted < time_stop:
  time_granted = fncs.time_request(time_stop) # time_next
  hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)
  events = fncs.get_events()
  for key in events:
    topic = key.decode()
    value = fncs.get_value(key).decode()
    if topic == 'price':
      price = float(value)
    else:
      pair = topic.split ('#')
      houseName = pair[0]
      if pair[1] == 'V1':
        voltages[houseName] = parse_fncs_magnitude (value)
      elif pair[1] == 'Tair':
        temperatures[houseName] = parse_fncs_magnitude (value)

#  print (time_granted, hour_of_day, price)
  # update all of the house setpoints
  count_temp_dev = 0
  sum_temp_dev = 0.0
  min_temp_dev = 10000.0
  max_temp_dev = 0.0
  for house, row in dict['houses'].items():
    topic = house + '_cooling_setpoint'
    if hour_of_day >= row['day_start_hour'] and hour_of_day <= row['day_end_hour']:
      value = row['day_set']
    else:
      value = row['night_set']
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
    # overvoltage response
#    if house in voltages:
#      if voltages[house] > row['vthresh']:
#        value += row['toffset']
    fncs.publish (topic, value)

  if count_temp_dev < 1:
    count_temp_dev = 1
    min_temp_dev = 0.0
  precool_metrics[str(time_granted)] = [min_temp_dev,max_temp_dev,sum_temp_dev/count_temp_dev]
  time_next = time_granted + dt

print('finalizing FNCS', flush=True)
fncs.finalize()
print ('writing metrics', flush=True)
print (json.dumps(precool_metrics), file=mp)
print ('done', flush=True)

