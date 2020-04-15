# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: prep_precool.py
"""Writes the precooling agent and GridLAB-D metadata for NIST TE Challenge 2 example
 
Public Functions:
    :prep_precool: writes the JSON and YAML files 
"""
import sys
import json
import numpy as np

def prep_precool (nameroot, time_step=15):
    """Sets up agent configurations for the NIST TE Challenge 2 example

    Reads the GridLAB-D data from nameroot.glm; it should contain 
    houses with thermal_integrity_level attributes. Writes:

    - *nameroot_agent_dict.json*, contains configuration data for the precooler agents
    - *nameroot_precool.yaml*, contains FNCS subscriptions for the precooler agents
    - *nameroot_FNCS_Config.txt*, a GridLAB-D include file with FNCS publications and subscriptions

    Args:
        nameroot (str): the name of the GridLAB-D file, without extension
    """
    # we want the same psuedo-random thermostat schedules each time, for repeatability
    np.random.seed (0)

    # write yaml for precool.py to subscribe meter voltages and house setpoints
    # write txt for gridlabd to subscribe house setpoints and publish meter voltages

    dt = time_step
    period = 300 # not actually used
    mean_price = 0.1167
    std_dev_price = 0.0149
    k_slope = 1.0
    # autonomous precooling; if the meter voltage_1 exceeds vthresh, change the thermostat by toffset
    vthresh = 125.0
    toffset_min = -1.9
    toffset_max = -2.1

    gp = open (nameroot + '.glm', 'r')
    dp = open (nameroot + '_agent_dict.json', 'w')
    yp = open (nameroot + '_precool.yaml', 'w')
    cp = open (nameroot + '_FNCS_Config.txt', 'w')

    # write preambles
    print ('name: precool', file=yp)
    print ('time_delta: ' + str(dt) + 's', file=yp)
    print ('broker: tcp://localhost:5570', file=yp)
    print ('aggregate_sub: true', file=yp)
    print ('aggregate_pub: true', file=yp)
    print ('values:', file=yp)
    print ('  price:', file=yp)
    print ('    topic: player/price', file=yp)
    print ('    default:', mean_price, file=yp)

    # find the house and meter names
    inHouses = False
    endedHouse = False
    isELECTRIC = False
    houseName = ''
    meterName = ''
    houses = {}

    for line in gp:
        lst = line.split()
        if len(lst) > 1:
            if lst[1] == 'house':
                inHouses = True
            # Check for ANY object within the house, and don't use its name:
            if inHouses == True and lst[0] == 'object' and lst[1] != 'house':
                endedHouse = True
            # Check house object with controller inside
            if inHouses == True:
                if lst[0] == 'name' and endedHouse == False:
                    houseName = lst[1].strip(';')
                if lst[0] == 'parent':
                    meterName = lst[1].strip(';')
                if lst[0] == 'cooling_system_type':
                    if (lst[1].strip(';') == 'ELECTRIC'):
                        isELECTRIC = True
        elif len(lst) == 1:
            if inHouses == True: 
                inHouses = False
                endedHouse = False
                if isELECTRIC == True:
                    night_set = np.random.uniform (70, 76)
                    day_set = np.random.uniform (78, 82)
                    day_start = np.random.uniform (6, 8)
                    day_end = np.random.uniform (17, 19)
                    deadband = np.random.uniform (1, 2)
                    toffset = np.random.uniform (toffset_min, toffset_max)
                    houses[houseName] = {'meter':meterName,'night_set':float('{:.3f}'.format(night_set)),
                        'day_set':float('{:.3f}'.format(day_set)),'day_start_hour':float('{:.3f}'.format(day_start)),
                        'day_end_hour':float('{:.3f}'.format(day_end)),'deadband':float('{:.3f}'.format(deadband)),
                        'vthresh':vthresh,'toffset':toffset}
                    print ('  ' + houseName + '#V1:', file=yp)
                    print ('    topic: gld1/' + meterName + '/measured_voltage_1', file=yp)
                    print ('    default: 120', file=yp)
                    print ('  ' + houseName + '#Tair:', file=yp)
                    print ('    topic: gld1/' + houseName + '/air_temperature', file=yp)
                    print ('    default: 80', file=yp)
                    print ('publish \"commit:' + meterName + '.measured_voltage_1 -> ' + meterName + '/measured_voltage_1\";', file=cp)
                    print ('publish \"commit:' + houseName + '.air_temperature -> ' + houseName + '/air_temperature\";', file=cp)
                    print ('subscribe \"precommit:' + houseName + '.cooling_setpoint <- precool/' + houseName + '_cooling_setpoint\";', file=cp)
                    print ('subscribe \"precommit:' + houseName + '.heating_setpoint <- precool/' + houseName + '_heating_setpoint\";', file=cp)
                    print ('subscribe \"precommit:' + houseName + '.thermostat_deadband <- precool/' + houseName + '_thermostat_deadband\";', file=cp)
                    isELECTRIC = False

    meta = {'houses':houses,'period':period,'dt':dt,'mean':mean_price,'stddev':std_dev_price,'k_slope':k_slope}
    print (json.dumps(meta), file=dp)

    dp.close()
    gp.close()
    yp.close()
    cp.close()



