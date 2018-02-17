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
  vals = [float(v) for v in vals]

  if '-' in tok:
    vals[1] *= -1.0
  if arg.startswith('-'):
    vals[0] *= -1.0
  return vals[0]

time_stop = 3600 * int(sys.argv[1])

lp = open (sys.argv[2] + "_agent_dict.json").read()
dict = json.loads(lp)

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

# set all of the house deadbands
for house, row in dict['houses'].items():
  topic = house + '_thermostat_deadband'
  value = row['deadband']
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
  for house, row in dict['houses'].items():
    topic = house + '_cooling_setpoint'
    if hour_of_day >= row['day_start_hour'] and hour_of_day <= row['day_end_hour']:
      value = row['day_set']
    else:
      value = row['night_set']
    fncs.publish (topic, value)
  time_next = time_granted + dt

print('finalizing FNCS', flush=True)
fncs.finalize()
print ('final air temperatures', temperatures)
print ('final meter voltages', voltages)
print ('done', flush=True)

