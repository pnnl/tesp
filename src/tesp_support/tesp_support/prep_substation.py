# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: prep_substation.py
""" Sets up the FNCS and agent configurations for te30 and sgip1 examples

This works for other TESP cases that have one GridLAB-D file, one EnergyPlus model,
and one PYPOWER model. Use *tesp_case* or *tesp_config* modules to specify
supplemental configuration data for these TESP cases, to be provided as the
optional *jsonfile* argument to *prep_substation*.

Public Functions:
    :prep_substation: processes a GridLAB-D file for one substation and one or more feeders
"""
import sys
import json
import numpy as np
import os
from datetime import datetime
import tesp_support.helpers as helpers

# write yaml for substation.py to subscribe meter voltages, house temperatures, hvac load and hvac state
# write txt for gridlabd to subscribe house setpoints and meter price; publish meter voltages
# write the json agent dictionary for post-processing, and run-time configuration of substation.py

# we want the same psuedo-random thermostat schedules each time, for repeatability
np.random.seed (0)

######################################################
# top-level data, not presently configurable from JSON
broker = 'tcp://localhost:5570'
network_node = 'network_node'
marketName = 'Market_1'
unit = 'kW'
control_mode = 'CN_RAMP' # 'CN_NONE'
use_predictive_bidding = 0
use_override = 'OFF'
price_cap = 3.78
special_mode = 'MD_NONE' #'MD_BUYERS'
use_future_mean_price = 0
clearing_scalar = 0.0
latency = 0
ignore_pricecap = 0
ignore_failedmarket = 0
statistic_mode = 1
stat_mode =  ['ST_CURR', 'ST_CURR']
interval = [86400, 86400]
stat_type = ['SY_MEAN', 'SY_STDEV']
#value = [0.02078, 0.01] # 0.00361]
capacity_reference_object = 'substation_transformer'
max_capacity_reference_bid_quantity = 5000
air_temperature = 78.0 # initial house air temperature

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
def ProcessGLM (fileroot):
    """Helper function that processes one GridLAB-D file

    Reads fileroot.glm and writes:

    - *fileroot_agent_dict.json*, contains configuration data for the simple_auction and hvac agents
    - *fileroot_substation.yaml*, contains FNCS subscriptions for the psimple_auction and hvac agents
    - *nameroot_FNCS_Config.txt*, a GridLAB-D include file with FNCS publications and subscriptions

    Args:
        fileroot (str): path to and base file name for the GridLAB-D file, without an extension
    """
    dirname = os.path.dirname (fileroot) + '/'
    basename = os.path.basename (fileroot)
    glmname = fileroot + '.glm'
    print (fileroot, dirname, basename, glmname)
    ip = open (glmname, 'r')

    # timings based on period and dt
    periodController = period
    bid_delay = 3.0 * dt # time controller bids before market clearing
    periodMarket = period

    controllers = {}
    auctions = {}
    ip.seek(0,0)
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

    houseName = ''
    meterName = ''
    FedName = 'gld1'
    climateName = ''
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
                houseClass = ''
                houseParent = ''
                inHouses = True
            if lst[1] == 'fncs_msg':
                inFNCSmsg = True
            if lst[1] == 'helics_msg':
                inHELICSmsg = True
            # Check for ANY object within the house, and don't use its name:
            if inHouses == True and lst[0] == 'object' and lst[1] != 'house':
                endedHouse = True
            if inClock == True:
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
            if inClimate == True:
                if lst[0] == 'name':
                    climateName = lst[1].strip(';')
                    inClimate = False
            if inHELICSmsg == True:
                if lst[0] == 'name':
                    FedName = lst[1].strip(';')
                    inHELICSmsg = False
            if inFNCSmsg == True:
                if lst[0] == 'name':
                    FedName = lst[1].strip(';')
                    inFNCSmsg = False
            if inTriplexMeters == True:
                if lst[0] == 'name':
                    meterName = lst[1].strip(';')
                    inTriplexMeters = False
            if inHouses == True:
                if lst[0] == 'name' and endedHouse == False:
                    houseName = lst[1].strip(';')
                if lst[0] == 'parent':
                    houseParent = lst[1].strip(';')
                if lst[0] == 'groupid':
                    houseClass = lst[1].strip(';')
                if lst[0] == 'air_temperature':
                    air_temperature = lst[1].strip(';')
                if lst[0] == 'cooling_system_type':
                    if (lst[1].strip(';') == 'ELECTRIC'):
                        isELECTRIC = True
        elif len(lst) == 1:
            inHELICSmsg = False
            if inHouses == True: 
                inHouses = False
                endedHouse = False
                if isELECTRIC == True:
                    if ('BIGBOX' in houseClass) or ('OFFICE' in houseClass) or ('STRIPMALL' in houseClass):
                        meterName = helpers.zoneMeterName (houseParent)
                    nAirConditioners += 1
                    if np.random.uniform (0, 1) <= agent_participation:
                        nControllers += 1
                        control_mode = 'CN_RAMP'
                    else:
                        control_mode = 'CN_NONE' # still follows the time-of-day schedule
                    controller_name = houseName + '_hvac'
                    wakeup_start = np.random.uniform (wakeup_start_lo, wakeup_start_hi)
                    daylight_start = np.random.uniform (daylight_start_lo, daylight_start_hi)
                    evening_start = np.random.uniform (evening_start_lo, evening_start_hi)
                    night_start = np.random.uniform (night_start_lo, night_start_hi)
                    wakeup_set = np.random.uniform (wakeup_set_lo, wakeup_set_hi)
                    daylight_set = np.random.uniform (daylight_set_lo, daylight_set_hi)
                    evening_set = np.random.uniform (evening_set_lo, evening_set_hi)
                    night_set = np.random.uniform (night_set_lo, night_set_hi)
                    weekend_day_start = np.random.uniform (weekend_day_start_lo, weekend_day_start_hi)
                    weekend_day_set = np.random.uniform (weekend_day_set_lo, weekend_day_set_hi)
                    weekend_night_start = np.random.uniform (weekend_night_start_lo, weekend_night_start_hi)
                    weekend_night_set = np.random.uniform (weekend_night_set_lo, weekend_night_set_hi)
                    deadband = np.random.uniform (deadband_lo, deadband_hi)
                    offset_limit = np.random.uniform (offset_limit_lo, offset_limit_hi)
                    ramp = np.random.uniform (ramp_lo, ramp_hi)
                    ctrl_cap = np.random.uniform (ctrl_cap_lo, ctrl_cap_hi)
                    controllers[controller_name] = {'control_mode': control_mode, 
                        'houseName': houseName,
                        'houseClass': houseClass, 
                        'meterName': meterName, 
                        'period': periodController,
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

    print ('configured', nControllers, 'participating controllers for', nAirConditioners, 'air conditioners')

    # Write market dictionary
    auctions[marketName] = {'market_id': 1, 
                            'unit': unit, 
                            'special_mode': special_mode, 
                            'use_future_mean_price': use_future_mean_price, 
                            'pricecap': price_cap, 
                            'clearing_scalar': clearing_scalar,
                            'period': periodMarket, 
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
                            'stat_value': [0 for i in range(len(stat_mode))]}

    # Close files
    ip.close()

    meta = {'markets':auctions,'controllers':controllers,'dt':dt,'GridLABD':FedName}
    dictfile = fileroot + '_agent_dict.json'
    dp = open (dictfile, 'w')
    json.dump (meta, dp, ensure_ascii=False, indent=2)
    dp.close()

    # write HELICS config file
    pubs = []
    pubs.append ({"key":"clear_price", "type":"double", "global": False})
    pubs.append ({"key":"unresponsive_mw", "type":"double", "global": False})
    pubs.append ({"key":"responsive_max_mw", "type":"double", "global": False})
    pubs.append ({"key":"responsive_c2", "type":"double", "global": False})
    pubs.append ({"key":"responsive_c1", "type":"double", "global": False})
    pubs.append ({"key":"responsive_deg", "type":"integer", "global": False})
    subs = []
    subs.append ({"key":"pypower/LMP_B7", "type":"double"})
    subs.append ({"key":"gld1/distribution_load", "type":"complex"})
    pubSubMeters = set()
    for key,val in controllers.items():
      meterName = val['meterName']
      houseName = val['houseName']
      subs.append ({"key":"gld1/"+houseName+"#air_temperature", "type":"double"}) #Tair
      subs.append ({"key":"gld1/"+houseName+"#hvac_load", "type":"double"}) #Load
      subs.append ({"key":"gld1/"+houseName+"#power_state", "type":"string"})   #On
      pubs.append ({"key":key+"/cooling_setpoint", "type":"double", "global": False})
      pubs.append ({"key":key+"/heating_setpoint", "type":"double", "global": False})
      pubs.append ({"key":key+"/thermostat_deadband", "type":"double", "global": False})
      if meterName not in pubSubMeters:
        pubSubMeters.add(meterName)
        subs.append ({"key":"gld1/"+meterName+"#measured_voltage_1", "type":"complex"})  #V1
        pubs.append ({"key":meterName+"/bill_mode", "type":"string", "global": False})
        pubs.append ({"key":meterName+"/price", "type":"double", "global": False})
        pubs.append ({"key":meterName+"/monthly_fee", "type":"double", "global": False})
    msg = {}
    msg["name"] = "sub1"
    msg["period"] = dt
    msg["publications"] = pubs
    msg["subscriptions"] = subs
    op = open (fileroot + '_HELICS_substation.json', 'w', encoding='utf-8')
    json.dump (msg, op, ensure_ascii=False, indent=2)
    op.close()

    # write YAML file
    yamlfile = fileroot + '_substation.yaml'
    yp = open (yamlfile, 'w')
    print ('name: sub1', file=yp)
    print ('time_delta: ' + str(dt) + 's', file=yp)
    print ('broker:', broker, file=yp)
    print ('aggregate_sub: true', file=yp)
    print ('aggregate_pub: true', file=yp)
    print ('values:', file=yp)
    print ('  LMP:', file=yp)
    print ('    topic: pypower/LMP_B7', file=yp)
    print ('    default: 0.1', file=yp)
    print ('    type: double', file=yp)
    print ('    list: false', file=yp)
    print ('  refload:', file=yp)
    print ('    topic: gld1/distribution_load', file=yp)
    print ('    default: 0', file=yp)
    print ('    type: complex', file=yp)
    print ('    list: false', file=yp)
    for key,val in controllers.items():
        houseName = val['houseName']
        meterName = val['meterName']
        print ('  ' + key + '#V1:', file=yp)
        print ('    topic: gld1/' + meterName + '/measured_voltage_1', file=yp)
        print ('    default: 120', file=yp)
        print ('  ' + key + '#Tair:', file=yp)
        print ('    topic: gld1/' + houseName + '/air_temperature', file=yp)
        print ('    default: 80', file=yp)
        print ('  ' + key + '#Load:', file=yp)
        print ('    topic: gld1/' + houseName + '/hvac_load', file=yp)
        print ('    default: 0', file=yp)
        print ('  ' + key + '#On:', file=yp)
        print ('    topic: gld1/' + houseName + '/power_state', file=yp)
        print ('    default: 0', file=yp)
    yp.close ()

    # write the weather agent's configuration file
    if len(climateName) > 0:
        time_fmt = '%Y-%m-%d %H:%M:%S'
        dt1 = datetime.strptime (StartTime, time_fmt)
        dt2 = datetime.strptime (EndTime, time_fmt)
        seconds = int ((dt2 - dt1).total_seconds())
        days = int(seconds / 86400)
        minutes = int(seconds / 60)
        hours = int(seconds / 3600)
#        print (days, seconds)
        wconfig = {'name':climateName,
                   'StartTime':StartTime,
                   'time_stop': str(minutes) + 'm',
                   'time_delta':'1s',
                   'publishInterval': '5m',
                   'Forecast':1,
                   'ForecastLength':'24h',
                   'PublishTimeAhead':'3s',
                   'AddErrorToForecast':1,
                   'broker':'tcp://localhost:5570',
                   'forecastPeriod':48,
                   'parameters':{}}
        for parm in ['temperature', 'humidity', 'pressure', 'solar_diffuse', 'solar_direct', 'wind_speed']:
            wconfig['parameters'][parm] = {'distribution': 2,
                                           'P_e_bias': 0.5,
                                           'P_e_envelope': 0.08,
                                           'Lower_e_bound': 0.5}

        wp = open (fileroot + '_FNCS_Weather_Config.json', 'w')
        json.dump (wconfig, wp, ensure_ascii=False, indent=2)
        wp.close()

        wp = open (fileroot + '_HELICS_Weather_Config.json', 'w')
        wconfig['broker'] = 'HELICS'
        json.dump (wconfig, wp, ensure_ascii=False, indent=2)
        wp.close()

    # write the GridLAB-D publications and subscriptions for HELICS
    pubs = []
    subs = []
    pubs.append ({"global":False, "key":"distribution_load", "type":"complex", "info":{"object":network_node,"property":"distribution_load"}})
    subs.append ({"key":"pypower/three_phase_voltage_B7", "type":"complex", "info":{"object":network_node,"property":"positive_sequence_voltage"}})
    if len(climateName) > 0:
      for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
        subs.append ({"key": climateName + '/' + wTopic, "type":"double", "info":{"object":climateName, "property":wTopic}})
    if len(Eplus_Bus) > 0: # hard-wired names for a single building
      subs.append ({"key": "eplus_agent/power_A", "type":"complex", "info":{"object":Eplus_Load, "property":"constant_power_A"}})
      subs.append ({"key": "eplus_agent/power_B", "type":"complex", "info":{"object":Eplus_Load, "property":"constant_power_B"}})
      subs.append ({"key": "eplus_agent/power_C", "type":"complex", "info":{"object":Eplus_Load, "property":"constant_power_C"}})
      subs.append ({"key": "eplus_agent/bill_mode", "type":"string", "info":{"object":Eplus_Meter, "property":"bill_mode"}})
      subs.append ({"key": "eplus_agent/price", "type":"double", "info":{"object":Eplus_Meter, "property":"price"}})
      subs.append ({"key": "eplus_agent/monthly_fee", "type":"double", "info":{"object":Eplus_Meter, "property":"monthly_fee"}})

    pubSubMeters = set()
    for key, val in controllers.items():
      houseName = val['houseName']
      houseClass = val['houseClass']
      meterName = val['meterName']
      for prop in ['power_state']:
        pubs.append ({"global":False, "key":houseName + "#" + prop, "type":"string", "info":{"object":houseName,"property":prop}})
      for prop in ['air_temperature', 'hvac_load']:
        pubs.append ({"global":False, "key":houseName + "#" + prop, "type":"double", "info":{"object":houseName,"property":prop}})
      for prop in ['cooling_setpoint', 'heating_setpoint', 'thermostat_deadband']:
        subs.append ({"key": "sub1/" + key + "/" + prop, "type":"double", "info":{"object":houseName, "property":prop}})
      if meterName not in pubSubMeters:
        pubSubMeters.add(meterName)
        prop = 'measured_voltage_1'
        if ('BIGBOX' in houseClass) or ('OFFICE' in houseClass) or ('STRIPMALL' in houseClass):
          prop = 'measured_voltage_A' # TODO: the HELICS substation always expects measured_voltage_1
        pubs.append ({"global":False, "key":meterName + "#measured_voltage_1", "type":"complex", "info":{"object":meterName,"property":prop}})
        for prop in ['bill_mode']:
          subs.append ({"key": "sub1/" + meterName + "/" + prop, "type":"string", "info":{"object":meterName, "property":prop}})
        for prop in ['price', 'monthly_fee']:
          subs.append ({"key": "sub1/" + meterName + "/" + prop, "type":"double", "info":{"object":meterName, "property":prop}})
    msg = {}
    msg["name"] = "gld1"
    msg["period"] = dt # 1.0 # TODO verify what should be done here to enforce minimum time step
    msg["publications"] = pubs
    msg["subscriptions"] = subs
    op = open (fileroot + '_HELICS_gld_msg.json', 'w', encoding='utf-8')
    json.dump (msg, op, ensure_ascii=False, indent=2)
    op.close()

    # write the GridLAB-D publications and subscriptions for FNCS
    op = open (fileroot + '_FNCS_Config.txt', 'w')
    print ('publish "commit:' + network_node + '.distribution_load -> distribution_load; 1000";', file=op)
    print ('subscribe "precommit:' + network_node + '.positive_sequence_voltage <- pypower/three_phase_voltage_B7";', file=op)
    if len(climateName) > 0:
        for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
            print ('subscribe "precommit:' + climateName + '.' + wTopic + ' <- ' + climateName + '/' + wTopic + '";', file=op)
    if len(Eplus_Bus) > 0: # hard-wired names for a single building
        print ('subscribe "precommit:{:s}.constant_power_A <- eplus_agent/power_A";'.format(Eplus_Load), file=op)
        print ('subscribe "precommit:{:s}.constant_power_B <- eplus_agent/power_B";'.format(Eplus_Load), file=op)
        print ('subscribe "precommit:{:s}.constant_power_C <- eplus_agent/power_C";'.format(Eplus_Load), file=op)
        print ('subscribe "precommit:{:s}.bill_mode <- eplus_agent/bill_mode";'.format(Eplus_Meter), file=op)
        print ('subscribe "precommit:{:s}.price <- eplus_agent/price";'.format(Eplus_Meter), file=op)
        print ('subscribe "precommit:{:s}.monthly_fee <- eplus_agent/monthly_fee";'.format(Eplus_Meter), file=op)
    pubSubMeters = set()
    for key, val in controllers.items():
        houseName = val['houseName']
        houseClass = val['houseClass']
        meterName = val['meterName']
        print ('publish "commit:' + houseName + '.air_temperature -> ' + houseName + '/air_temperature";', file=op)
        print ('publish "commit:' + houseName + '.power_state -> ' + houseName + '/power_state";', file=op)
        print ('publish "commit:' + houseName + '.hvac_load -> ' + houseName + '/hvac_load";', file=op)
        print ('subscribe "precommit:' + houseName + '.cooling_setpoint <- sub1/' + key + '/cooling_setpoint";', file=op)
        print ('subscribe "precommit:' + houseName + '.heating_setpoint <- sub1/' + key + '/heating_setpoint";', file=op)
        print ('subscribe "precommit:' + houseName + '.thermostat_deadband <- sub1/' + key + '/thermostat_deadband";', file=op)
        if meterName not in pubSubMeters:
            pubSubMeters.add(meterName)
            if ('BIGBOX' in houseClass) or ('OFFICE' in houseClass) or ('STRIPMALL' in houseClass):
                print ('publish "commit:' + meterName + '.measured_voltage_A -> ' + meterName + '/measured_voltage_1";', file=op)
            else:
                print ('publish "commit:' + meterName + '.measured_voltage_1 -> ' + meterName + '/measured_voltage_1";', file=op)
            print ('subscribe "precommit:' + meterName + '.bill_mode <- sub1/' + key + '/bill_mode";', file=op)
            print ('subscribe "precommit:' + meterName + '.price <- sub1/' + key + '/price";', file=op)
            print ('subscribe "precommit:' + meterName + '.monthly_fee <- sub1/' + key + '/monthly_fee";', file=op)
    op.close()

def prep_substation (gldfileroot, jsonfile = ''):
    """ Process a base GridLAB-D file with supplemental JSON configuration data

    Always reads gldfileroot.glm and writes:

    - *gldfileroot_agent_dict.json*, contains configuration data for the simple_auction and hvac agents
    - *gldfileroot_substation.yaml*, contains FNCS subscriptions for the psimple_auction and hvac agents
    - *gldfileroot_FNCS_Config.txt*, a GridLAB-D include file with FNCS publications and subscriptions
    - *gldfileroot_Weather_Config.json*, contains configuration data for the weather agent

    If provided, this function also reads jsonfile as created by *tesp_config* and used by *tesp_case*.
    This supplemental data includes time-scheduled thermostat setpoints (NB: do not use the scheduled
    setpoint feature within GridLAB-D, as the first FNCS messages will erase those schedules during
    simulation). The supplemental data also includes time step and market period, the load scaling
    factor to PYPOWER, ramp bidding function parameters and the EnergyPlus connection point. If not provided,
    the default values from te30 and sgip1 examples will be used.  

    Args:
        gldfileroot (str): path to and base file name for the GridLAB-D file, without an extension
        jsonfile (str): fully qualified path to an optional JSON configuration file 
                        (if not provided, an E+ connection to Eplus_load will be created)
    """
    global dt, period, Eplus_Bus, Eplus_Load, Eplus_Meter, agent_participation, max_capacity_reference_bid_quantity
    global wakeup_start_lo, wakeup_start_hi, wakeup_set_lo, wakeup_set_hi
    global daylight_start_lo, daylight_start_hi, daylight_set_lo, daylight_set_hi
    global evening_start_lo, evening_start_hi, evening_set_lo, evening_set_hi
    global night_start_lo, night_start_hi, night_set_lo, night_set_hi
    global weekend_day_start_lo, weekend_day_start_hi, weekend_day_set_lo, weekend_day_set_hi
    global weekend_night_start_lo, weekend_night_start_hi, weekend_night_set_lo, weekend_night_set_hi
    global ramp_lo, ramp_hi, deadband_lo, deadband_hi, offset_limit_lo, offset_limit_hi
    global ctrl_cap_lo, ctrl_cap_hi, initial_price, std_dev
    global latitude, longitude, name_prefix

    if len(jsonfile) > 1:
        lp = open (jsonfile).read()
        config = json.loads(lp)

        if 'NamePrefix' in config['BackboneFiles']:
          name_prefix = config['BackboneFiles']['NamePrefix']

        # overwrite the default auction and controller parameters
        dt = int (config['AgentPrep']['TimeStepGldAgents'])
        period = int (config['AgentPrep']['MarketClearingPeriod'])

        wakeup_start_lo = float (config['ThermostatSchedule']['WeekdayWakeStartLo'])
        wakeup_start_hi = float (config['ThermostatSchedule']['WeekdayWakeStartHi'])
        daylight_start_lo = float (config['ThermostatSchedule']['WeekdayDaylightStartLo'])
        daylight_start_hi = float (config['ThermostatSchedule']['WeekdayDaylightStartHi'])
        evening_start_lo = float (config['ThermostatSchedule']['WeekdayEveningStartLo'])
        evening_start_hi = float (config['ThermostatSchedule']['WeekdayEveningStartHi'])
        night_start_lo = float (config['ThermostatSchedule']['WeekdayNightStartLo'])
        night_start_hi = float (config['ThermostatSchedule']['WeekdayNightStartHi'])

        wakeup_set_lo = float (config['ThermostatSchedule']['WeekdayWakeSetLo'])
        wakeup_set_hi = float (config['ThermostatSchedule']['WeekdayWakeSetHi'])
        daylight_set_lo = float (config['ThermostatSchedule']['WeekdayDaylightSetLo'])
        daylight_set_hi = float (config['ThermostatSchedule']['WeekdayDaylightSetHi'])
        evening_set_lo = float (config['ThermostatSchedule']['WeekdayEveningSetLo'])
        evening_set_hi = float (config['ThermostatSchedule']['WeekdayEveningSetHi'])
        night_set_lo = float (config['ThermostatSchedule']['WeekdayNightSetLo'])
        night_set_hi = float (config['ThermostatSchedule']['WeekdayNightSetHi'])

        weekend_day_set_lo = float (config['ThermostatSchedule']['WeekendDaylightSetLo'])
        weekend_day_set_hi = float (config['ThermostatSchedule']['WeekendDaylightSetHi'])
        weekend_day_start_lo = float (config['ThermostatSchedule']['WeekendDaylightStartLo'])
        weekend_day_start_hi = float (config['ThermostatSchedule']['WeekendDaylightStartHi'])
        weekend_night_set_lo = float (config['ThermostatSchedule']['WeekendNightSetLo'])
        weekend_night_set_hi = float (config['ThermostatSchedule']['WeekendNightSetHi'])
        weekend_night_start_lo = float (config['ThermostatSchedule']['WeekendNightStartLo'])
        weekend_night_start_hi = float (config['ThermostatSchedule']['WeekendNightStartHi'])

        ramp_lo = float (config['AgentPrep']['ThermostatRampLo'])
        ramp_hi = float (config['AgentPrep']['ThermostatRampHi'])
        deadband_lo = float (config['AgentPrep']['ThermostatBandLo'])
        deadband_hi = float (config['AgentPrep']['ThermostatBandHi'])
        offset_limit_lo = float (config['AgentPrep']['ThermostatOffsetLimitLo'])
        offset_limit_hi = float (config['AgentPrep']['ThermostatOffsetLimitHi'])
        ctrl_cap_lo = float (config['AgentPrep']['PriceCapLo'])
        ctrl_cap_hi = float (config['AgentPrep']['PriceCapHi'])
        initial_price = float (config['AgentPrep']['InitialPriceMean'])
        std_dev = float (config['AgentPrep']['InitialPriceStdDev'])

        Eplus_Bus = config['EplusConfiguration']['EnergyPlusBus']
        if len (Eplus_Bus) > 0:
          Eplus_Bus = name_prefix + Eplus_Bus
          Eplus_Load = name_prefix + 'Eplus_load'
          Eplus_Meter = name_prefix + 'Eplus_meter'
        else:
          Eplus_Load = ''
          Eplus_Meter = ''
        agent_participation = 0.01 * float(config['FeederGenerator']['ElectricCoolingParticipation'])

        latitude = float (config['WeatherPrep']['Latitude'])
        longitude = float (config['WeatherPrep']['Longitude'])

        # use the forced oil, forced air as 1.67 * transformer rating in kVA
        max_capacity_reference_bid_quantity = 1.6667 * 1000.0 * float(config['PYPOWERConfiguration']['TransformerBase'])

    ProcessGLM (gldfileroot)


