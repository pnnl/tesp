import string;
import sys;
import fncs;
import json;

time_stop = 3600 * int(sys.argv[1])
time_granted = 0
time_next = 1

lp = open (sys.argv[2] + "_agent_dict.json").read()
dict = json.loads(lp)

print ('run till', time_stop, 'period', dict['period'], 'mean', dict['mean'], 'stddev', dict['stddev'])
#print (dict['houses'])

fncs.initialize()

while time_granted < time_stop:
  time_granted = fncs.time_request(time_stop) # time_next
  events = fncs.get_events()
  for key in events:
    topic = key.decode()
    print (time_granted, key, topic, fncs.get_value(key), flush=True)
    value = fncs.get_value(key).decode()
#    if topic == 'sw_status':
#      fncs.publish('sw_status', value)
  time_next = time_granted + 1

print('finalizing FNCS', flush=True)
fncs.finalize()
print('done', flush=True)

