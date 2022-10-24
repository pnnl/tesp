# Copyright (C) 2018-2022 Battelle Memorial Institute
# file: prep_substation.py
""" Sets up the FNCS and agent configurations for te30 and sgip1 examples

This works for other TESP cases that have one GridLAB-D file, one EnergyPlus model,
and one PYPOWER model. Use *tesp_case* or *tesp_config* modules to specify
supplemental configuration data for these TESP cases, to be provided as the
optional *jsonfile* argument to *prep_substation*.

Public Functions:
    :prep_substation: processes a GridLAB-D file for one substation and one or more feeders
"""

import os
import json
import numpy as np
from datetime import datetime

from .helpers import zoneMeterName, HelicsMsg

# write yaml for substation.py to subscribe meter voltages, house temperatures, hvac load and hvac state
# write txt for gridlabd to subscribe house setpoints and meter price; publish meter voltages
# write the json agent dictionary for post-processing, and run-time configuration of substation.py

# we want the same psuedo-random thermostat schedules each time, for repeatability
np.random.seed(0)

######################################################
# top-level data, not presently configurable from JSON
broker = 'tcp://localhost:5570'
network_node = 'network_node'
marketName = 'Market_1'
unit = 'kW'
use_predictive_bidding = 0
use_override = 'OFF'
price_cap = 3.78
special_mode = 'MD_NONE'  # 'MD_BUYERS'
use_future_mean_price = 0
clearing_scalar = 0.0
latency = 0
ignore_pricecap = 0
ignore_failedmarket = 0
statistic_mode = 1
stat_mode = ['ST_CURR', 'ST_CURR']
interval = [86400, 86400]
stat_type = ['SY_MEAN', 'SY_STDEV']
# value = [0.02078, 0.01] # 0.00361]
capacity_reference_object = 'substation_transformer'
max_capacity_reference_bid_quantity = 5000
dso_substation_bus_id = 1

###################################################
# top-level data that can be reconfigured from JSON, defaults for TE30
dt = 15
period = 300

name_prefix = ''

# by default there will be an E+ connection, unless nulled in the JSON config file
Eplus_Bus = 'Eplus_load'
Eplus_Meter = 'Eplus_meter'
Eplus_Load = 'Eplus_load'

agent_participation = 1.0

wakeup_start_lo = 5.0
wakeup_start_hi = 6.5
daylight_start_lo = 8.0
daylight_start_hi = 9.0
evening_start_lo = 17.0
evening_start_hi = 18.5
night_start_lo = 22.0
night_start_hi = 23.5

wakeup_set_lo = 78.0
wakeup_set_hi = 80.0
daylight_set_lo = 84.0
daylight_set_hi = 86.0
evening_set_lo = 78.0
evening_set_hi = 80.0
night_set_lo = 72.0
night_set_hi = 74.0

weekend_day_start_lo = 8.0
weekend_day_start_hi = 9.0
weekend_day_set_lo = 76.0
weekend_day_set_hi = 84.0
weekend_night_start_lo = 22.0
weekend_night_start_hi = 24.0
weekend_night_set_lo = 72.0
weekend_night_set_hi = 74.0

ramp_lo = 0.5
ramp_hi = 3.0
deadband_lo = 2.0
deadband_hi = 3.0
offset_limit_lo = 2.0
offset_limit_hi = 4.0
ctrl_cap_lo = 1.0
ctrl_cap_hi = 3.0

initial_price = 0.02078
std_dev = 0.01

latitude = 30.0
longitude = -110.0


#####################################################
def ProcessGLM(fileroot):
    """Helper function that processes one GridLAB-D file

    Reads fileroot.glm and writes:

    - *[fileroot]_agent_dict.json*, contains configuration data for the simple_auction and hvac agents
    - *[fileroot]_substation.yaml*, contains FNCS subscriptions for the psimple_auction and hvac agents
    - *[fileroot]_gridlabd.txt*, a GridLAB-D include file with FNCS publications and subscriptions
    - *[fileroot]_substation.json*, contains HELICS subscriptions for the psimple_auction and hvac agents
    - *[fileroot]_gridlabd.json*, a GridLAB-D include file with HELICS publications and subscriptions

    Args:
        fileroot (str): path to and base file name for the GridLAB-D file, without an extension
    """
    dirname = os.path.dirname(fileroot) + '/'
    basename = os.path.basename(fileroot)
    glmname = fileroot + '.glm'
    print(fileroot, dirname, basename, glmname)
    ip = open(glmname, 'r')

    # timings based on period and dt
    bid_delay = 3.0 * dt  # time controller bids before market clearing
    controllers = {}
    auctions = {}
    ip.seek(0, 0)
    inFNCSmsg = False
    inHELICSmsg = False
    inHouses = False
    inTriplexMeters = False
    endedHouse = False
    isELECTRIC = False
    inClimate = False
    inClock = False
    nAirConditioners = 0
    nControllers = 0

    meter_name = ''
    house_name = ''
    house_class = ''
    house_parent = ''
    tso_federate = 'pypower'
    gld_federate = 'gld_' + str(dso_substation_bus_id)
    sub_federate = 'sub_' + str(dso_substation_bus_id)
    climate_name = ''
    StartTime = ''
    EndTime = ''

    # Obtain controller dictionary based on houses with electric cooling
    for line in ip:
        lst = line.split()
        if len(lst) > 1:
            if lst[0] == 'clock':
                inClock = True
            if lst[1] == 'climate':
                inClimate = True
            if lst[1] == 'triplex_meter':
                inTriplexMeters = True
            if lst[1] == 'house':
                inHouses = True
            if lst[1] == 'fncs_msg':
                inFNCSmsg = True
            if lst[1] == 'helics_msg':
                inHELICSmsg = True
            # Check for ANY object within the house, and don't use its name:
            if inHouses and lst[0] == 'object' and lst[1] != 'house':
                endedHouse = True
            if inClock:
                if lst[0] == 'starttime':
                    StartTime = lst[1].strip('\';')
                    if len(lst) > 2:
                        StartTime = StartTime + ' ' + lst[2].strip('\';')
                elif lst[0] == 'timestamp':
                    StartTime = lst[1].strip('\';')
                    if len(lst) > 2:
                        StartTime = StartTime + ' ' + lst[2].strip('\';')
                elif lst[0] == 'stoptime':
                    EndTime = lst[1].strip('\';')
                    if len(lst) > 2:
                        EndTime = EndTime + ' ' + lst[2].strip('\';')
                if len(StartTime) > 0 and len(EndTime) > 0:
                    inClock = False
            if inClimate:
                if lst[0] == 'name':
                    climate_name = lst[1].strip(';')
                    inClimate = False
            if inHELICSmsg:
                if lst[0] == 'name':
                    gld_federate = lst[1].strip(';')
                    inHELICSmsg = False
            if inFNCSmsg:
                if lst[0] == 'name':
                    gld_federate = lst[1].strip(';')
                    inFNCSmsg = False
            if inTriplexMeters:
                if lst[0] == 'name':
                    meter_name = lst[1].strip(';')
                    inTriplexMeters = False
            if inHouses:
                if lst[0] == 'name' and not endedHouse:
                    house_name = lst[1].strip(';')
                if lst[0] == 'parent':
                    house_parent = lst[1].strip(';')
                if lst[0] == 'groupid':
                    house_class = lst[1].strip(';')
                if lst[0] == 'cooling_system_type':
                    if lst[1].strip(';') == 'ELECTRIC':
                        isELECTRIC = True
        elif len(lst) == 1:
            inHELICSmsg = False
            if inHouses:
                inHouses = False
                endedHouse = False
                if isELECTRIC:
                    if ('BIGBOX' in house_class) or ('OFFICE' in house_class) or ('STRIPMALL' in house_class):
                        meter_name = zoneMeterName(house_parent)
                    nAirConditioners += 1
                    if np.random.uniform(0, 1) <= agent_participation:
                        nControllers += 1
                        control_mode = 'CN_RAMP'
                    else:
                        control_mode = 'CN_NONE'  # still follows the time-of-day schedule
                    controller_name = house_name + '_hvac'
                    wakeup_start = np.random.uniform(wakeup_start_lo, wakeup_start_hi)
                    daylight_start = np.random.uniform(daylight_start_lo, daylight_start_hi)
                    evening_start = np.random.uniform(evening_start_lo, evening_start_hi)
                    night_start = np.random.uniform(night_start_lo, night_start_hi)
                    wakeup_set = np.random.uniform(wakeup_set_lo, wakeup_set_hi)
                    daylight_set = np.random.uniform(daylight_set_lo, daylight_set_hi)
                    evening_set = np.random.uniform(evening_set_lo, evening_set_hi)
                    night_set = np.random.uniform(night_set_lo, night_set_hi)
                    weekend_day_start = np.random.uniform(weekend_day_start_lo, weekend_day_start_hi)
                    weekend_day_set = np.random.uniform(weekend_day_set_lo, weekend_day_set_hi)
                    weekend_night_start = np.random.uniform(weekend_night_start_lo, weekend_night_start_hi)
                    weekend_night_set = np.random.uniform(weekend_night_set_lo, weekend_night_set_hi)
                    deadband = np.random.uniform(deadband_lo, deadband_hi)
                    offset_limit = np.random.uniform(offset_limit_lo, offset_limit_hi)
                    ramp = np.random.uniform(ramp_lo, ramp_hi)
                    ctrl_cap = np.random.uniform(ctrl_cap_lo, ctrl_cap_hi)
                    controllers[controller_name] = {'control_mode': control_mode,
                                                    'meterName': meter_name,
                                                    'houseName': house_name,
                                                    'houseClass': house_class,
                                                    'period': period,
                                                    'wakeup_start': float('{:.3f}'.format(wakeup_start)),
                                                    'daylight_start': float('{:.3f}'.format(daylight_start)),
                                                    'evening_start': float('{:.3f}'.format(evening_start)),
                                                    'night_start': float('{:.3f}'.format(night_start)),
                                                    'wakeup_set': float('{:.3f}'.format(wakeup_set)),
                                                    'daylight_set': float('{:.3f}'.format(daylight_set)),
                                                    'evening_set': float('{:.3f}'.format(evening_set)),
                                                    'night_set': float('{:.3f}'.format(night_set)),
                                                    'weekend_day_start': float('{:.3f}'.format(weekend_day_start)),
                                                    'weekend_day_set': float('{:.3f}'.format(weekend_day_set)),
                                                    'weekend_night_start': float('{:.3f}'.format(weekend_night_start)),
                                                    'weekend_night_set': float('{:.3f}'.format(weekend_night_set)),
                                                    'deadband': float('{:.3f}'.format(deadband)),
                                                    'offset_limit': float('{:.3f}'.format(offset_limit)),
                                                    'ramp': float('{:.4f}'.format(ramp)),
                                                    'price_cap': float('{:.3f}'.format(ctrl_cap)),
                                                    'bid_delay': bid_delay,
                                                    'use_predictive_bidding': use_predictive_bidding,
                                                    'use_override': use_override}
                    isELECTRIC = False

    print('configured', nControllers, 'participating controllers for', nAirConditioners, 'air conditioners')

    # Write market dictionary
    auctions[marketName] = {'market_id': 1,
                            'unit': unit,
                            'special_mode': special_mode,
                            'use_future_mean_price': use_future_mean_price,
                            'pricecap': price_cap,
                            'clearing_scalar': clearing_scalar,
                            'period': period,
                            'latency': latency,
                            'init_price': initial_price,
                            'init_stdev': std_dev,
                            'ignore_pricecap': ignore_pricecap,
                            'ignore_failedmarket': ignore_failedmarket,
                            'statistic_mode': statistic_mode,
                            'capacity_reference_object': capacity_reference_object,
                            'max_capacity_reference_bid_quantity': max_capacity_reference_bid_quantity,
                            'stat_mode': stat_mode,
                            'stat_interval': interval,
                            'stat_type': stat_type,
                            'stat_value': [0 for _ in range(len(stat_mode))]}
    # Close files
    ip.close()

    meta = {'markets': auctions, 'controllers': controllers, 'dt': dt, 'GridLABD': gld_federate}
    dictfile = fileroot + '_agent_dict.json'
    dp = open(dictfile, 'w')
    json.dump(meta, dp, ensure_ascii=False, indent=2)
    dp.close()

    # write HELICS config file
    dso = HelicsMsg(sub_federate, dt)
    dso.pubs_n(False, "unresponsive_mw", "double")
    dso.pubs_n(False, "responsive_max_mw", "double")
    dso.pubs_n(False, "responsive_c2", "double")
    dso.pubs_n(False, "responsive_c1", "double")
    dso.pubs_n(False, "responsive_deg", "integer")
    dso.pubs_n(False, "clear_price", "double")
    dso.subs_n(tso_federate + "/LMP_" + str(dso_substation_bus_id), "double")
    dso.subs_n(gld_federate + "/distribution_load", "complex")
    pubSubMeters = set()
    for key, val in controllers.items():
        house_name = val['houseName']
        meter_name = val['meterName']
        dso.subs_n(gld_federate + "/" + house_name + "#air_temperature", "double")
        dso.subs_n(gld_federate + "/" + house_name + "#hvac_load", "double")
        dso.subs_n(gld_federate + "/" + house_name + "#power_state", "string")
        dso.pubs_n(False, key + "/cooling_setpoint", "double")
        dso.pubs_n(False, key + "/heating_setpoint", "double")
        dso.pubs_n(False, key + "/thermostat_deadband", "double")
        if meter_name not in pubSubMeters:
            pubSubMeters.add(meter_name)
            dso.subs_n(gld_federate + "/" + meter_name + "#measured_voltage_1", "complex")  # V1
            dso.pubs_n(False, key + "/" + meter_name + "/bill_mode", "string")
            dso.pubs_n(False, key + "/" + meter_name + "/price", "double")
            dso.pubs_n(False, key + "/" + meter_name + "/monthly_fee", "double")
    dso.write_file(fileroot + '_substation.json')

    # write YAML file
    yamlfile = fileroot + '_substation.yaml'
    yp = open(yamlfile, 'w')
    print('name: ' + sub_federate, file=yp)
    print('time_delta: ' + str(dt) + 's', file=yp)
    print('broker:', broker, file=yp)
    print('aggregate_sub: true', file=yp)
    print('aggregate_pub: true', file=yp)
    print('values:', file=yp)
    print('  LMP:', file=yp)
    print('    topic: ' + tso_federate + '/' + 'LMP_' + str(dso_substation_bus_id), file=yp)
    print('    default: 0.1', file=yp)
    print('    type: double', file=yp)
    print('    list: false', file=yp)
    print('  refload:', file=yp)
    print('    topic: ' + gld_federate + '/' + 'distribution_load', file=yp)
    print('    default: 0', file=yp)
    print('    type: complex', file=yp)
    print('    list: false', file=yp)
    for key, val in controllers.items():
        house_name = val['houseName']
        meter_name = val['meterName']
        print('  ' + key + '#V1:', file=yp)
        print('    topic: ' + gld_federate + '/' + meter_name + '/measured_voltage_1', file=yp)
        print('    default: 120', file=yp)
        print('  ' + key + '#Tair:', file=yp)
        print('    topic: ' + gld_federate + '/' + house_name + '/air_temperature', file=yp)
        print('    default: 80', file=yp)
        print('  ' + key + '#Load:', file=yp)
        print('    topic: ' + gld_federate + '/' + house_name + '/hvac_load', file=yp)
        print('    default: 0', file=yp)
        print('  ' + key + '#On:', file=yp)
        print('    topic: ' + gld_federate + '/' + house_name + '/power_state', file=yp)
        print('    default: 0', file=yp)
    yp.close()

    # write the weather agent's configuration file
    if len(climate_name) > 0:
        time_fmt = '%Y-%m-%d %H:%M:%S'
        dt1 = datetime.strptime(StartTime, time_fmt)
        dt2 = datetime.strptime(EndTime, time_fmt)
        seconds = int((dt2 - dt1).total_seconds())
        minutes = int(seconds / 60)
        # hours = int(seconds / 3600)
        # days = int(seconds / 86400)
        # print (days, hours, minutes, seconds)
        wconfig = {'name': climate_name,
                   'StartTime': StartTime,
                   'time_stop': str(minutes) + 'm',
                   'time_delta': '1s',
                   'publishInterval': '5m',
                   'Forecast': 1,
                   'ForecastLength': '24h',
                   'PublishTimeAhead': '3s',
                   'AddErrorToForecast': 1,
                   'broker': 'tcp://localhost:5570',
                   'forecastPeriod': 48,
                   'parameters': {}}
        for parm in ['temperature', 'humidity', 'pressure', 'solar_diffuse', 'solar_direct', 'wind_speed']:
            wconfig['parameters'][parm] = {'distribution': 2,
                                           'P_e_bias': 0.5,
                                           'P_e_envelope': 0.08,
                                           'Lower_e_bound': 0.5}

        wp = open(fileroot + '_weather_f.json', 'w')
        json.dump(wconfig, wp, ensure_ascii=False, indent=2)
        wp.close()

        wp = open(fileroot + '_weather.json', 'w')
        wconfig['broker'] = 'HELICS'
        json.dump(wconfig, wp, ensure_ascii=False, indent=2)
        wp.close()

    # write the GridLAB-D publications and subscriptions for HELICS
    gld = HelicsMsg(gld_federate, dt)
    gld.pubs(False, "distribution_load", "complex", network_node, "distribution_load")
    gld.subs(tso_federate + "/" + "three_phase_voltage_" + str(dso_substation_bus_id), "complex", network_node, "positive_sequence_voltage")
    if len(climate_name) > 0:
        for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
            gld.subs(climate_name + "/#" + wTopic, "double", climate_name, wTopic)
    if len(Eplus_Bus) > 0:  # hard-wired names for a single building
        gld.subs("eplus_agent/power_A", "complex", Eplus_Load, "constant_power_A")
        gld.subs("eplus_agent/power_B", "complex", Eplus_Load, "constant_power_B")
        gld.subs("eplus_agent/power_C", "complex", Eplus_Load, "constant_power_C")
        gld.subs("eplus_agent/bill_mode", "string", Eplus_Meter, "bill_mode")
        gld.subs("eplus_agent/price", "double", Eplus_Meter, "price")
        gld.subs("eplus_agent/monthly_fee", "double", Eplus_Meter, "monthly_fee")

    pubSubMeters = set()
    for key, val in controllers.items():
        meter_name = val['meterName']
        house_name = val['houseName']
        house_class = val['houseClass']
        sub_key = sub_federate + "/" + key + "/"
        gld.pubs(False, house_name + "#power_state", "string", house_name, "power_state")
        gld.pubs(False, house_name + "#air_temperature", "double", house_name, "air_temperature")
        gld.pubs(False, house_name + "#hvac_load", "double", house_name, "hvac_load")
        gld.subs(sub_key + "cooling_setpoint", "double", house_name, "cooling_setpoint")
        gld.subs(sub_key + "heating_setpoint", "double", house_name, "heating_setpoint")
        gld.subs(sub_key + "thermostat_deadband", "double", house_name, "thermostat_deadband")
        if meter_name not in pubSubMeters:
            pubSubMeters.add(meter_name)
            prop = 'measured_voltage_1'
            if ('BIGBOX' in house_class) or ('OFFICE' in house_class) or ('STRIPMALL' in house_class):
                prop = 'measured_voltage_A'  # TODO: the HELICS substation always expects measured_voltage_1
            gld.pubs(False, meter_name + "#measured_voltage_1", "complex", meter_name, prop)
            gld.subs(sub_key + meter_name + "/bill_mode", "string", meter_name, "bill_mode")
            gld.subs(sub_key + meter_name + "/price", "double", meter_name, "price")
            gld.subs(sub_key + meter_name + "/monthly_fee", "double", meter_name, "monthly_fee")
    # TODO verify what should be done here to enforce minimum time step
    gld.write_file(fileroot + '_gridlabd.json')

    # write the GridLAB-D publications and subscriptions for FNCS
    op = open(fileroot + '_gridlabd.txt', 'w')
    print('publish "commit:' + network_node + '.distribution_load -> distribution_load; 1000";', file=op)
    print('subscribe "precommit:' + network_node + '.positive_sequence_voltage <- pypower/three_phase_voltage_' + str(dso_substation_bus_id) + ';', file=op)
    if len(climate_name) > 0:
        for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
            print('subscribe "precommit:' + climate_name + '.' + wTopic + ' <- ' + climate_name + '/' + wTopic + '";', file=op)
    if len(Eplus_Bus) > 0:  # hard-wired names for a single building
        print('subscribe "precommit:{:s}.constant_power_A <- eplus_agent/power_A";'.format(Eplus_Load), file=op)
        print('subscribe "precommit:{:s}.constant_power_B <- eplus_agent/power_B";'.format(Eplus_Load), file=op)
        print('subscribe "precommit:{:s}.constant_power_C <- eplus_agent/power_C";'.format(Eplus_Load), file=op)
        print('subscribe "precommit:{:s}.bill_mode <- eplus_agent/bill_mode";'.format(Eplus_Meter), file=op)
        print('subscribe "precommit:{:s}.price <- eplus_agent/price";'.format(Eplus_Meter), file=op)
        print('subscribe "precommit:{:s}.monthly_fee <- eplus_agent/monthly_fee";'.format(Eplus_Meter), file=op)
    pubSubMeters = set()
    for key, val in controllers.items():
        meter_name = val['meterName']
        house_name = val['houseName']
        house_class = val['houseClass']
        print('publish "commit:' + house_name + '.air_temperature -> ' + house_name + '/air_temperature";', file=op)
        print('publish "commit:' + house_name + '.power_state -> ' + house_name + '/power_state";', file=op)
        print('publish "commit:' + house_name + '.hvac_load -> ' + house_name + '/hvac_load";', file=op)
        print('subscribe "precommit:' + house_name + '.cooling_setpoint <- ' + sub_federate + '/' + key + '/cooling_setpoint";', file=op)
        print('subscribe "precommit:' + house_name + '.heating_setpoint <- ' + sub_federate + '/' + key + '/heating_setpoint";', file=op)
        print('subscribe "precommit:' + house_name + '.thermostat_deadband <- ' + sub_federate + '/' + key + '/thermostat_deadband";', file=op)
        if meter_name not in pubSubMeters:
            pubSubMeters.add(meter_name)
            if ('BIGBOX' in house_class) or ('OFFICE' in house_class) or ('STRIPMALL' in house_class):
                print('publish "commit:' + meter_name + '.measured_voltage_A -> ' + meter_name + '/measured_voltage_1";', file=op)
            else:
                print('publish "commit:' + meter_name + '.measured_voltage_1 -> ' + meter_name + '/measured_voltage_1";', file=op)
            print('subscribe "precommit:' + meter_name + '.bill_mode <- ' + sub_federate + '/' + key + '/bill_mode";', file=op)
            print('subscribe "precommit:' + meter_name + '.price <- ' + sub_federate + '/' + key + '/price";', file=op)
            print('subscribe "precommit:' + meter_name + '.monthly_fee <- ' + sub_federate + '/' + key + '/monthly_fee";', file=op)
    op.close()


def prep_substation(gldfileroot, jsonfile='', bus_id=None):
    """ Process a base GridLAB-D file with supplemental JSON configuration data

    If provided, this function also reads jsonfile as created by *tesp_config* and used by *tesp_case*.
    This supplemental data includes time-scheduled thermostat set points (NB: do not use the scheduled
    set point feature within GridLAB-D, as the first FNCS messages will erase those schedules during
    simulation). The supplemental data also includes time step and market period, the load scaling
    factor to PYPOWER, ramp bidding function parameters and the EnergyPlus connection point. If not provided,
    the default values from te30 and sgip1 examples will be used.  

    Args:
        gldfileroot (str): path to and base file name for the GridLAB-D file, without an extension
        jsonfile (str): fully qualified path to an optional JSON configuration file 
                        (if not provided, an E+ connection to Eplus_load will be created)
        bus_id: substation bus identifier
    """
    global dt, period, Eplus_Bus, Eplus_Load, Eplus_Meter, agent_participation
    global max_capacity_reference_bid_quantity, dso_substation_bus_id
    global wakeup_start_lo, wakeup_start_hi, wakeup_set_lo, wakeup_set_hi
    global daylight_start_lo, daylight_start_hi, daylight_set_lo, daylight_set_hi
    global evening_start_lo, evening_start_hi, evening_set_lo, evening_set_hi
    global night_start_lo, night_start_hi, night_set_lo, night_set_hi
    global weekend_day_start_lo, weekend_day_start_hi, weekend_day_set_lo, weekend_day_set_hi
    global weekend_night_start_lo, weekend_night_start_hi, weekend_night_set_lo, weekend_night_set_hi
    global ramp_lo, ramp_hi, deadband_lo, deadband_hi, offset_limit_lo, offset_limit_hi
    global ctrl_cap_lo, ctrl_cap_hi, initial_price, std_dev
    global latitude, longitude, name_prefix

    if bus_id is not None:
        dso_substation_bus_id = bus_id

    if len(jsonfile) > 1:
        lp = open(jsonfile).read()
        config = json.loads(lp)

        if 'NamePrefix' in config['BackboneFiles']:
            name_prefix = config['BackboneFiles']['NamePrefix']

        # overwrite the default auction and controller parameters
        dt = int(config['AgentPrep']['TimeStepGldAgents'])
        period = int(config['AgentPrep']['MarketClearingPeriod'])

        wakeup_start_lo = float(config['ThermostatSchedule']['WeekdayWakeStartLo'])
        wakeup_start_hi = float(config['ThermostatSchedule']['WeekdayWakeStartHi'])
        daylight_start_lo = float(config['ThermostatSchedule']['WeekdayDaylightStartLo'])
        daylight_start_hi = float(config['ThermostatSchedule']['WeekdayDaylightStartHi'])
        evening_start_lo = float(config['ThermostatSchedule']['WeekdayEveningStartLo'])
        evening_start_hi = float(config['ThermostatSchedule']['WeekdayEveningStartHi'])
        night_start_lo = float(config['ThermostatSchedule']['WeekdayNightStartLo'])
        night_start_hi = float(config['ThermostatSchedule']['WeekdayNightStartHi'])

        wakeup_set_lo = float(config['ThermostatSchedule']['WeekdayWakeSetLo'])
        wakeup_set_hi = float(config['ThermostatSchedule']['WeekdayWakeSetHi'])
        daylight_set_lo = float(config['ThermostatSchedule']['WeekdayDaylightSetLo'])
        daylight_set_hi = float(config['ThermostatSchedule']['WeekdayDaylightSetHi'])
        evening_set_lo = float(config['ThermostatSchedule']['WeekdayEveningSetLo'])
        evening_set_hi = float(config['ThermostatSchedule']['WeekdayEveningSetHi'])
        night_set_lo = float(config['ThermostatSchedule']['WeekdayNightSetLo'])
        night_set_hi = float(config['ThermostatSchedule']['WeekdayNightSetHi'])

        weekend_day_set_lo = float(config['ThermostatSchedule']['WeekendDaylightSetLo'])
        weekend_day_set_hi = float(config['ThermostatSchedule']['WeekendDaylightSetHi'])
        weekend_day_start_lo = float(config['ThermostatSchedule']['WeekendDaylightStartLo'])
        weekend_day_start_hi = float(config['ThermostatSchedule']['WeekendDaylightStartHi'])
        weekend_night_set_lo = float(config['ThermostatSchedule']['WeekendNightSetLo'])
        weekend_night_set_hi = float(config['ThermostatSchedule']['WeekendNightSetHi'])
        weekend_night_start_lo = float(config['ThermostatSchedule']['WeekendNightStartLo'])
        weekend_night_start_hi = float(config['ThermostatSchedule']['WeekendNightStartHi'])

        ramp_lo = float(config['AgentPrep']['ThermostatRampLo'])
        ramp_hi = float(config['AgentPrep']['ThermostatRampHi'])
        deadband_lo = float(config['AgentPrep']['ThermostatBandLo'])
        deadband_hi = float(config['AgentPrep']['ThermostatBandHi'])
        offset_limit_lo = float(config['AgentPrep']['ThermostatOffsetLimitLo'])
        offset_limit_hi = float(config['AgentPrep']['ThermostatOffsetLimitHi'])
        ctrl_cap_lo = float(config['AgentPrep']['PriceCapLo'])
        ctrl_cap_hi = float(config['AgentPrep']['PriceCapHi'])
        initial_price = float(config['AgentPrep']['InitialPriceMean'])
        std_dev = float(config['AgentPrep']['InitialPriceStdDev'])

        Eplus_Bus = config['EplusConfiguration']['EnergyPlusBus']
        if len(Eplus_Bus) > 0:
            Eplus_Bus = name_prefix + Eplus_Bus
            Eplus_Load = name_prefix + 'Eplus_load'
            Eplus_Meter = name_prefix + 'Eplus_meter'
        else:
            Eplus_Load = ''
            Eplus_Meter = ''
        agent_participation = 0.01 * float(config['FeederGenerator']['ElectricCoolingParticipation'])

        latitude = float(config['WeatherPrep']['Latitude'])
        longitude = float(config['WeatherPrep']['Longitude'])

        # use the forced oil, forced air as 1.67 * transformer rating in kVA
        max_capacity_reference_bid_quantity = 1.6667 * 1000.0 * float(config['PYPOWERConfiguration']['TransformerBase'])
        dso_substation_bus_id = int(config['PYPOWERConfiguration']['GLDBus'])

    ProcessGLM(gldfileroot)
