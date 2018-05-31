import string;
import sys;
import fncs;

time_stop = int(sys.argv[1])
time_granted = 0

# requires yaml specificied in an envar
fncs.initialize()

while time_granted < time_stop:
	time_granted = fncs.time_request(time_stop)
	events = fncs.get_events()
	for key in events:
		topic = key.decode()
		print (time_granted, key, topic, 
					 fncs.get_value(key), flush=True)
		value = fncs.get_value(key).decode()
		if topic == 'sw_status':
			fncs.publish('sw_status', value)

fncs.finalize()


