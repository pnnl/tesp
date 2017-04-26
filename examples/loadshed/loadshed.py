import string;
import sys;
import fncs;

time_stop = int(sys.argv[1])
time_granted = 0
time_next = 1

# requires the yaml file
fncs.initialize()

print('# time key value till', time_stop, flush=True)

while time_granted < time_stop:
	time_granted = fncs.time_request(time_stop) # time_next
#	print('**', time_granted)
	events = fncs.get_events()
	for key in events:
		topic = key.decode()
		value = fncs.get_value(key).decode()
#		print (time_granted, topic, value, flush=True)
		if topic == 'sw_status':
			fncs.publish('sw_status', value)
	time_next = time_granted + 1

fncs.finalize()


