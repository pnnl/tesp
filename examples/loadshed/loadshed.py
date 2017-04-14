import string;
import sys;
import fncs;

time_stop = int(sys.argv[1])
time_granted = 0

# requires the yaml file
fncs.initialize()

print("# time key value")

while time_granted < time_stop:
	time_granted = fncs.time_request(time_stop)
	events = fncs.get_events()
	for key in events:
		topic = key.decode()
		value = fncs.get_value(key).decode()
		if topic == 'sw_status':
			print (time_granted, topic, value)
			fncs.publish('sw_status', value)

fncs.finalize()


