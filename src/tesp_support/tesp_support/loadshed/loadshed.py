import string;
import sys;
import tesp_support.fncs;

def loadshed_loop (timestop):
	time_granted = 0
	time_next = 1

	# requires the yaml file
	fncs.initialize()

	print('# time key value till', time_stop, flush=True)

	while time_granted < time_stop:
		time_granted = fncs.time_request(time_stop) # time_next
	#   print('**', time_granted)
		events = fncs.get_events()
		for key in events:
			topic = key.decode()
			print (time_granted, key, topic, fncs.get_value(key), flush=True)
			value = fncs.get_value(key).decode()
			if topic == 'sw_status':
				fncs.publish('sw_status', value)
		time_next = time_granted + 1

	print('finalizing FNCS', flush=True)
	fncs.finalize()
	print('done', flush=True)


