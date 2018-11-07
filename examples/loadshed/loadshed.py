import string;
import sys;
import fncs;
if sys.platform != 'win32':
	import resource

time_stop = int(sys.argv[1])
time_granted = 0

# requires yaml specificied in an envar
fncs.initialize()

while time_granted < time_stop:
	time_granted = fncs.time_request(time_stop)
	events = fncs.get_events()
	for topic in events:
		value = fncs.get_value(topic)
		print (time_granted, topic, value, flush=True)
		if topic == 'sw_status':
			fncs.publish('sw_status', value)

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
