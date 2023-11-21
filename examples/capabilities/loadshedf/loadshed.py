# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: loadshed.py

import sys

import tesp_support.original.fncs as fncs

time_stop = int(sys.argv[1])
time_granted = 0

# requires yaml file specified in an environmental variable
fncs.initialize()

while time_granted < time_stop:
    time_granted = fncs.time_request(time_stop)
    events = fncs.get_events()
    for topic in events:
        value = fncs.get_value(topic)
        print(time_granted, topic, value, flush=True)
        if topic == 'sw_status':
            fncs.publish('sw_status', value)

fncs.finalize()
