import string;
import sys;
import fncs;

time_stop = int(sys.argv[1])
time_granted = 0
time_next = 1

# requires the yaml file
fncs.initialize()

print("# time key value")

while time_granted < time_stop:
	time_granted = fncs.time_request(time_next)
	events = fncs.get_events()
	for key in events:
		topic = key.decode()
		value = fncs.get_value(key).decode()
		print (time_granted, topic, value)
		if topic == 'sw_status':
			fncs.publish('sw_status', value)
	time_next = time_granted + 1

fncs.finalize()


