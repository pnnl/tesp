# Copyright (C) 2018-2022 Battelle Memorial Institute
# file: prep_precool.py
"""Writes the precooling agent and GridLAB-D metadata for NIST TE Challenge 2 example
 
Public Functions:
    :prep_precool: writes the JSON and YAML files 
"""
import json

import numpy as np

from .helpers import HelicsMsg


def prep_precool(name_root, time_step=15):
    """Sets up agent configurations for the NIST TE Challenge 2 example

    Reads the GridLAB-D data from name_root.glm; it should contain
    houses with thermal_integrity_level attributes. Writes:

    - *[name_root]_agent_dict.json*, contains configuration data for the precooler agents
    - *[name_root]_precool.yaml*, contains FNCS subscriptions for the precooler agents
    - *[name_root]_gridlabd.txt*, a GridLAB-D include file with FNCS publications and subscriptions

    Args:
        name_root (str): the name of the GridLAB-D file, without extension
        time_step (int): time step period
    """
    # we want the same psuedo-random thermostat schedules each time, for repeatability
    np.random.seed(0)

    # write yaml for precool.py to subscribe meter voltages and house set points
    # write txt for gridlabd to subscribe house set points and publish meter voltages

    dt = time_step
    period = 300  # not actually used
    mean_price = 0.1167
    std_dev_price = 0.0149
    k_slope = 1.0
    # autonomous precooling; if the meter voltage_1 exceeds vthresh, change the thermostat by toffset
    vthresh = 125.0
    toffset_min = -1.9
    toffset_max = -2.1

    gld_federate = 'gld_1'
    cool_federate = 'precool'

    # FNCS open and write preambles
    gp = open(name_root + '.glm', 'r')
    dp = open(name_root + '_agent_dict.json', 'w')
    yp = open(name_root + '_precool.yaml', 'w')
    cp = open(name_root + '_gridlabd.txt', 'w')

    print('name: ' + cool_federate, file=yp)
    print('time_delta: ' + str(dt) + 's', file=yp)
    print('broker: tcp://localhost:5570', file=yp)
    print('aggregate_sub: true', file=yp)
    print('aggregate_pub: true', file=yp)
    print('values:', file=yp)
    print('  price:', file=yp)
    print('    topic: player/price', file=yp)
    print('    default:', mean_price, file=yp)

    # HELICS open and write preambles
    gld = HelicsMsg(gld_federate, dt)
    cool = HelicsMsg(cool_federate, dt)
    cool.subs_n('player/price', "double")

    # find the house and meter names
    inHouses = False
    endedHouse = False
    isELECTRIC = False
    house_name = ''
    meter_name = ''
    houses = {}
    pubSubMeters = set()

    for line in gp:
        lst = line.split()
        if len(lst) > 1:
            if lst[1] == 'house':
                inHouses = True
            # Check for ANY object within the house, and don't use its name:
            if inHouses and lst[0] == 'object' and lst[1] != 'house':
                endedHouse = True
            # Check house object with controller inside
            if inHouses:
                if lst[0] == 'name' and not endedHouse:
                    house_name = lst[1].strip(';')
                if lst[0] == 'parent':
                    meter_name = lst[1].strip(';')
                if lst[0] == 'cooling_system_type':
                    if lst[1].strip(';') == 'ELECTRIC':
                        isELECTRIC = True
        elif len(lst) == 1:
            if inHouses:
                inHouses = False
                endedHouse = False
                if isELECTRIC:
                    night_set = np.random.uniform(70, 76)
                    day_set = np.random.uniform(78, 82)
                    day_start = np.random.uniform(6, 8)
                    day_end = np.random.uniform(17, 19)
                    deadband = np.random.uniform(1, 2)
                    toffset = np.random.uniform(toffset_min, toffset_max)
                    houses[house_name] = {'meter': meter_name,
                                          'night_set': float('{:.3f}'.format(night_set)),
                                          'day_set': float('{:.3f}'.format(day_set)),
                                          'day_start_hour': float('{:.3f}'.format(day_start)),
                                          'day_end_hour': float('{:.3f}'.format(day_end)),
                                          'deadband': float('{:.3f}'.format(deadband)),
                                          'vthresh': vthresh, 'toffset': toffset}
                    # FNCS messages
                    print('  ' + house_name + '#V1:', file=yp)
                    print('    topic: ' + gld_federate + '/' + meter_name + '/measured_voltage_1', file=yp)
                    print('    default: 120', file=yp)
                    print('  ' + house_name + '#Tair:', file=yp)
                    print('    topic: ' + gld_federate + '/' + house_name + '/air_temperature', file=yp)
                    print('    default: 80', file=yp)
                    print('publish \"commit:' + meter_name + '.measured_voltage_1 -> ' + meter_name + '/measured_voltage_1\";', file=cp)
                    print('publish \"commit:' + house_name + '.air_temperature -> ' + house_name + '/air_temperature\";', file=cp)
                    print('subscribe \"precommit:' + house_name + '.cooling_setpoint <- precool/' + house_name + '_cooling_setpoint\";', file=cp)
                    print('subscribe \"precommit:' + house_name + '.heating_setpoint <- precool/' + house_name + '_heating_setpoint\";', file=cp)
                    print('subscribe \"precommit:' + house_name + '.thermostat_deadband <- precool/' + house_name + '_thermostat_deadband\";', file=cp)

                    # HELICS messages
                    cool.subs_n(gld_federate + '/' + house_name + '#Tair', "double")
                    cool.pubs_n(False, house_name + "/cooling_setpoint", "double")
                    cool.pubs_n(False, house_name + "/heating_setpoint", "double")
                    cool.pubs_n(False, house_name + "/thermostat_deadband", "double")
                    gld.pubs(False, house_name + "#Tair", "double", house_name, "air_temperature")
                    gld.subs(cool_federate + "/" + house_name + "/cooling_setpoint", "double", house_name, "cooling_setpoint")
                    gld.subs(cool_federate + "/" + house_name + "/heating_setpoint", "double", house_name, "heating_setpoint")
                    gld.subs(cool_federate + "/" + house_name + "/thermostat_deadband", "double", house_name, "thermostat_deadband")
                    if house_name+meter_name not in pubSubMeters:
                        pubSubMeters.add(house_name+meter_name)
                        cool.subs_n(gld_federate + "/" + house_name + "#V1", "complex")
                        gld.pubs(False, house_name + "#V1", "complex", meter_name, "measured_voltage_1")

                    isELECTRIC = False

    meta = {
        'houses': houses, 'period': period, 'dt': dt,
        'mean': mean_price, 'stddev': std_dev_price,
        'k_slope': k_slope
    }
    print(json.dumps(meta), file=dp)

    dp.close()
    gp.close()
    yp.close()
    cp.close()

    cool.write_file(name_root + '_precool.json')
    gld.write_file(name_root + '_gridlabd.json')
