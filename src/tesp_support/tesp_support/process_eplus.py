#	Copyright (C) 2017-2018 Battelle Memorial Institute
# file: process_eplus.py
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def process_eplus(nameroot):
    # read the JSON file
    lp = open ("eplus_" + nameroot + "_metrics.json").read()
    lst = json.loads(lp)
    print ("Metrics data starting", lst['StartTime'])

    # make a sorted list of the times
    lst.pop('StartTime')
    meta = lst.pop('Metadata')
    times = list(map(int,list(lst.keys())))
    times.sort()
    print ("There are", len (times), "sample times at", times[1] - times[0], "seconds")

    # parse the metadata for 11 things of specific interest
    for key, val in meta.items():
        if key == 'electric_demand_power_avg':
            ELECTRIC_DEMAND_IDX = val['index']
            ELECTRIC_DEMAND_UNITS = val['units']
        elif key == 'occupants_total_avg':
            OCCUPANTS_IDX = val['index']
            OCCUPANTS_UNITS = val['units']
        elif key == 'kwhr_price_avg':
            PRICE_IDX = val['index']
            PRICE_UNITS = val['units']
        elif key == 'ashrae_uncomfortable_hours_avg':
            ASHRAE_HOURS_IDX = val['index']
            ASHRAE_HOURS_UNITS = val['units']
        elif key == 'cooling_desired_temperature_avg':
            COOLING_SETPOINT_IDX = val['index']
            COOLING_SETPOINT_UNITS = val['units']
        elif key == 'cooling_current_temperature_avg':
            COOLING_TEMPERATURE_IDX = val['index']
            COOLING_TEMPERATURE_UNITS = val['units']
        elif key == 'cooling_setpoint_delta_avg':
            COOLING_DELTA_IDX = val['index']
            COOLING_DELTA_UNITS = val['units']
        elif key == 'cooling_controlled_load_avg':
            COOLING_POWER_IDX = val['index']
            COOLING_POWER_UNITS = val['units']
        elif key == 'heating_desired_temperature_avg':
            HEATING_SETPOINT_IDX = val['index']
            HEATING_SETPOINT_UNITS = val['units']
        elif key == 'heating_current_temperature_avg':
            HEATING_TEMPERATURE_IDX = val['index']
            HEATING_TEMPERATURE_UNITS = val['units']
        elif key == 'heating_setpoint_delta_avg':
            HEATING_DELTA_IDX = val['index']
            HEATING_DELTA_UNITS = val['units']
        elif key == 'heating_controlled_load_avg':
            HEATING_POWER_IDX = val['index']
            HEATING_POWER_UNITS = val['units']

    # make sure we found the metric indices of interest
    ary = lst['3600']['SchoolDualController']
    print ("There are", len(ary), "metrics")
    print ("1st hour price =", ary[PRICE_IDX], PRICE_UNITS)

    # create a NumPy array of all metrics for the first building, 8760*39 doubles
    # we also want a NumPy array of times in hours
    data = np.empty(shape=(len(times),len(ary)), dtype=np.float)
    print ("Constructed", data.shape, "NumPy array")
    i = 0
    for t in times:
        ary = lst[str(t)]['SchoolDualController']
        data[i,:] = ary
        i = i + 1
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom
    print("Samples at", hrs, "hours")

    # display some averages
    print ("Average price =", data[:,PRICE_IDX].mean(), PRICE_UNITS)
    print ("Average demand =", data[:,ELECTRIC_DEMAND_IDX].mean(), ELECTRIC_DEMAND_UNITS)
    print ("Average uncomf =", data[:,ASHRAE_HOURS_IDX].mean(), ASHRAE_HOURS_UNITS)
    print ("Average people =", data[:,OCCUPANTS_IDX].mean(), OCCUPANTS_UNITS)
    print ("Average cooling power =", data[:,COOLING_POWER_IDX].mean(), COOLING_POWER_UNITS)
    print ("Average cooling temp  =", data[:,COOLING_TEMPERATURE_IDX].mean(), COOLING_TEMPERATURE_UNITS)
    print ("Average cooling setpt =", data[:,COOLING_SETPOINT_IDX].mean(), COOLING_SETPOINT_UNITS)
    print ("Average cooling delta =", data[:,COOLING_DELTA_IDX].mean(), COOLING_DELTA_UNITS)
    print ("Average heating power =", data[:,HEATING_POWER_IDX].mean(), HEATING_POWER_UNITS)
    print ("Average heating temp  =", data[:,HEATING_TEMPERATURE_IDX].mean(), HEATING_TEMPERATURE_UNITS)
    print ("Average heating setpt =", data[:,HEATING_SETPOINT_IDX].mean(), HEATING_SETPOINT_UNITS)
    print ("Average heating delta =", data[:,HEATING_DELTA_IDX].mean(), HEATING_DELTA_UNITS)

    # display a plot
    fig, ax = plt.subplots(3,1, sharex = 'col')

    ax[0].plot(hrs, data[:,COOLING_TEMPERATURE_IDX], color="blue", label="Actual")
    ax[0].plot(hrs, data[:,COOLING_SETPOINT_IDX], color="red", label="Setpoint")
    ax[0].plot(hrs, data[:,COOLING_DELTA_IDX], color="green", label="Delta")
    ax[0].set_ylabel(COOLING_TEMPERATURE_UNITS)
    ax[0].set_title ("Cooling System Temperatures")
    ax[0].legend(loc='best')

    ax[1].plot(hrs, data[:,HEATING_TEMPERATURE_IDX], color="blue", label="Actual")
    ax[1].plot(hrs, data[:,HEATING_SETPOINT_IDX], color="red", label="Setpoint")
    ax[1].plot(hrs, data[:,HEATING_DELTA_IDX], color="green", label="Delta")
    ax[1].set_ylabel(HEATING_TEMPERATURE_UNITS)
    ax[1].set_title ("Heating System Temperatures")
    ax[1].legend(loc='best')

    ax[2].plot(hrs, data[:,PRICE_IDX], color="blue", label="Actual")
    ax[2].set_xlabel("Hours")
    ax[2].set_ylabel(PRICE_UNITS)
    ax[2].set_title ("Real-time Price")

    plt.show()

