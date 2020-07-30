#   Copyright (C) 2017-2019 Battelle Memorial Institute
# file: process_eplus.py
"""Functions to plot data from the EnergyPlus agent

Public Functions:
        :process_eplus: Reads the data and metadata, then makes the plots.  

"""
import json;
import sys;
import numpy as np;
try:
  import matplotlib as mpl;
  import matplotlib.pyplot as plt;
except:
  pass

def process_eplus(nameroot, title=None, pngfile=None):
    """ Plots the min and max line-neutral voltages for every billing meter

    This function reads *eplus_nameroot_metrics.json* for both metadata and data. 
    This must exist in the current working directory.  
    One graph is generated with 3 subplots:

    1. Cooling system setpoint, actual temperature and the difference between them.
    2. Heating system setpoint, actual temperature and the difference between them.
    3. Price that the building controller responded to.

    Args:
        nameroot (str): name of the TESP case, not necessarily the same as the EnergyPlus case, without the extension
    """
    # read the JSON file
    try:
      lp = open ("eplus_" + nameroot + "_metrics.json").read()
      lst = json.loads(lp)
      print ("Metrics data starting", lst['StartTime'])
    except:
      print ('eplus metrics file could not be read')
      return

    # make a sorted list of the times
    lst.pop('StartTime')
    meta = lst.pop('Metadata')
    times = list(map(int,list(lst.keys())))
    times.sort()
    print ("There are", len (times), "sample times at", times[1] - times[0], "seconds")

    # parse the metadata for things of specific interest
    for key, val in meta.items():
        if key == 'electric_demand_power_avg':
            ELECTRIC_DEMAND_IDX = val['index']
            ELECTRIC_DEMAND_UNITS = val['units']
        elif key == 'hvac_demand_power_avg':
            HVAC_DEMAND_IDX = val['index']
            HVAC_DEMAND_UNITS = val['units']
        elif key == 'occupants_total_avg':
            OCCUPANTS_IDX = val['index']
            OCCUPANTS_UNITS = val['units']
        elif key == 'kwhr_price_avg':
            PRICE_IDX = val['index']
            PRICE_UNITS = val['units']
        elif key == 'ashrae_uncomfortable_hours_avg':
            ASHRAE_HOURS_IDX = val['index']
            ASHRAE_HOURS_UNITS = val['units']
        elif key == 'cooling_schedule_temperature_avg':
            COOLING_SCHEDULE_IDX = val['index']
            COOLING_SCHEDULE_UNITS = val['units']
        elif key == 'cooling_setpoint_temperature_avg':
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
        elif key == 'cooling_power_state_avg':
            COOLING_STATE_IDX = val['index']
            COOLING_STATE_UNITS = val['units']
        elif key == 'heating_schedule_temperature_avg':
            HEATING_SCHEDULE_IDX = val['index']
            HEATING_SCHEDULE_UNITS = val['units']
        elif key == 'heating_setpoint_temperature_avg':
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
        elif key == 'heating_power_state_avg':
            HEATING_STATE_IDX = val['index']
            HEATING_STATE_UNITS = val['units']
        elif key == 'outdoor_air_avg':
            OUTDOOR_AIR_IDX = val['index']
            OUTDOOR_AIR_UNITS = val['units']
        elif key == 'indoor_air_avg':
            INDOOR_AIR_IDX = val['index']
            INDOOR_AIR_UNITS = val['units']
        elif key == 'heating_volume_avg':
            HEATING_VOLUME_IDX = val['index']
            HEATING_VOLUME_UNITS = val['units']
        elif key == 'cooling_volume_avg':
            COOLING_VOLUME_IDX = val['index']
            COOLING_VOLUME_UNITS = val['units']


    # make sure we found the metric indices of interest
    building = list(lst['3600'].keys())[0]
    ary = lst['3600'][building]
    print ('There are', len(ary), 'metrics for', building)
    print ('1st hour price =', ary[PRICE_IDX], PRICE_UNITS)

    # create a NumPy array of all metrics for the first building, 8760*39 doubles
    # we also want a NumPy array of times in hours
    data = np.empty(shape=(len(times),len(ary)), dtype=np.float)
    print ('Constructed', data.shape, 'NumPy array')
    i = 0
    for t in times:
        ary = lst[str(t)][building]
        data[i,:] = ary
        i = i + 1
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # display some averages
    print ('Average price  = {:.5f}'.format (data[:,PRICE_IDX].mean()), PRICE_UNITS)
    print ('Average demand = {:.2f}'.format (data[:,ELECTRIC_DEMAND_IDX].mean()), ELECTRIC_DEMAND_UNITS)
    print ('Average HVAC   = {:.2f}'.format (data[:,HVAC_DEMAND_IDX].mean()), HVAC_DEMAND_UNITS)
    print ('Average uncomf = {:.5f}'.format (data[:,ASHRAE_HOURS_IDX].mean()), ASHRAE_HOURS_UNITS)
    print ('Average people = {:.2f}'.format (data[:,OCCUPANTS_IDX].mean()), OCCUPANTS_UNITS)

    print ('Average cooling power = {:9.2f}'.format (data[:,COOLING_POWER_IDX].mean()), COOLING_POWER_UNITS)
    print ('Average cooling temp  = {:9.2f}'.format (data[:,COOLING_TEMPERATURE_IDX].mean()), COOLING_TEMPERATURE_UNITS)
    print ('Average cooling sched = {:9.2f}'.format (data[:,COOLING_SCHEDULE_IDX].mean()), COOLING_SCHEDULE_UNITS)
    print ('Average cooling delta = {:9.2f}'.format (data[:,COOLING_DELTA_IDX].mean()), COOLING_DELTA_UNITS)
    print ('Average cooling setpt = {:9.2f}'.format (data[:,COOLING_SETPOINT_IDX].mean()), COOLING_SETPOINT_UNITS)
    print ('Average cooling vol   = {:9.2f}'.format (data[:,COOLING_VOLUME_IDX].mean()), COOLING_VOLUME_UNITS)

    print ('Average heating power = {:9.2f}'.format (data[:,HEATING_POWER_IDX].mean()), HEATING_POWER_UNITS)
    print ('Average heating temp  = {:9.2f}'.format (data[:,HEATING_TEMPERATURE_IDX].mean()), HEATING_TEMPERATURE_UNITS)
    print ('Average heating sched = {:9.2f}'.format (data[:,HEATING_SCHEDULE_IDX].mean()), HEATING_SCHEDULE_UNITS)
    print ('Average heating delta = {:9.2f}'.format (data[:,HEATING_DELTA_IDX].mean()), HEATING_DELTA_UNITS)
    print ('Average heating setpt = {:9.2f}'.format (data[:,HEATING_SETPOINT_IDX].mean()), HEATING_SETPOINT_UNITS)
    print ('Average heating vol   = {:9.2f}'.format (data[:,HEATING_VOLUME_IDX].mean()), HEATING_VOLUME_UNITS)

    print ('Average outdoor air   = {:9.2f}'.format (data[:,OUTDOOR_AIR_IDX].mean()), OUTDOOR_AIR_UNITS)
    print ('Average indoor air    = {:9.2f}'.format (data[:,INDOOR_AIR_IDX].mean()), INDOOR_AIR_UNITS)

    # display a plot
    width = 12.0
    height = 8.0
    fig, ax = plt.subplots(3,3, sharex = 'col', figsize=(width,height), constrained_layout=True)
    if title is not None:
      fig.suptitle (title)

    ax[0,0].plot(hrs, data[:,COOLING_TEMPERATURE_IDX], color='blue', label='Actual')
    ax[0,0].plot(hrs, data[:,COOLING_SETPOINT_IDX], color='red', label='Setpoint')
    ax[0,0].plot(hrs, data[:,COOLING_SCHEDULE_IDX], color='green', label='Schedule')
#    ax[0,0].plot(hrs, data[:,INDOOR_AIR_IDX], color='magenta', label='Indoor')
    ax[0,0].set_ylabel(COOLING_TEMPERATURE_UNITS)
    ax[0,0].set_title ('Volume Average Cooling')
    ax[0,0].legend(loc='best')

    ax[1,0].plot(hrs, data[:,HEATING_TEMPERATURE_IDX], color='blue', label='Actual')
    ax[1,0].plot(hrs, data[:,HEATING_SETPOINT_IDX], color='red', label='Setpoint')
    ax[1,0].plot(hrs, data[:,HEATING_SCHEDULE_IDX], color='green', label='Schedule')
#    ax[1,0].plot(hrs, data[:,INDOOR_AIR_IDX], color='magenta', label='Indoor')
    ax[1,0].set_ylabel(HEATING_TEMPERATURE_UNITS)
    ax[1,0].set_title ('Volume Average Heating')
    ax[1,0].legend(loc='best')

    ax[2,0].plot(hrs, data[:,OUTDOOR_AIR_IDX], color='blue', label='Outdoor')
    ax[2,0].plot(hrs, data[:,INDOOR_AIR_IDX], color='red', label='Indoor')
    ax[2,0].set_ylabel(OUTDOOR_AIR_UNITS)
    ax[2,0].set_title ('Average Temperatures')
    ax[2,0].legend(loc='best')

    ax[0,1].plot(hrs, data[:,PRICE_IDX], color='blue', label='Actual')
    ax[0,1].set_ylabel(PRICE_UNITS)
    ax[0,1].set_title ('Real-time Price')

    ax[1,1].plot(hrs, 0.001 * data[:,ELECTRIC_DEMAND_IDX], color='blue', label='Total')
    ax[1,1].plot(hrs, 0.001 * data[:,HVAC_DEMAND_IDX], color='red', label='HVAC')
    ax[1,1].set_ylabel('kW')
    ax[1,1].set_title ('Building Electrical Demand')
    ax[1,1].legend(loc='best')

#    ax[2,1].plot(hrs, data[:,COOLING_DELTA_IDX], color='blue', label='Cooling')
#    ax[2,1].plot(hrs, data[:,HEATING_DELTA_IDX], color='red', label='Heating')
#    ax[2,1].set_ylabel(HEATING_STATE_UNITS)
    ax[2,1].plot(hrs, 0.001 * data[:,COOLING_POWER_IDX], color='blue', label='Cooling')
    ax[2,1].plot(hrs, 0.001 * data[:,HEATING_POWER_IDX], color='red', label='Heating')
    ax[2,1].plot(hrs, 0.001 * data[:,HVAC_DEMAND_IDX], color='green', label='HVAC')
    ax[2,1].set_ylabel('kW')
    ax[2,1].set_title ('DX/Electrical Coil Demand')
    ax[2,1].legend(loc='best')

    ax[0,2].plot(hrs, data[:,OCCUPANTS_IDX], color='blue')
    ax[0,2].set_ylabel(OCCUPANTS_UNITS)
    ax[0,2].set_title ('Occupants')

    ax[1,2].plot(hrs, data[:,ASHRAE_HOURS_IDX], color='blue')
    ax[1,2].set_ylabel(ASHRAE_HOURS_UNITS)
    ax[1,2].set_title ('Uncomfortable Hours')

    ax[2,2].plot(hrs, 0.001 * data[:,HEATING_VOLUME_IDX] + 0.001 * data[:,COOLING_VOLUME_IDX], color='magenta', label='Total')
    ax[2,2].plot(hrs, 0.001 * data[:,COOLING_VOLUME_IDX], color='blue', label='Cooling')
    ax[2,2].plot(hrs, 0.001 * data[:,HEATING_VOLUME_IDX], color='red', label='Heating')
    ax[2,2].set_ylabel('thousand m^3')
    ax[2,2].set_title ('Sensible Zone Volumes')
    ax[2,2].legend(loc='best')

    ax[2,0].set_xlabel('Hours')
    ax[2,1].set_xlabel('Hours')
    ax[2,2].set_xlabel('Hours')

    if pngfile is not None:
      plt.savefig(pngfile)
    else:
      plt.show()

