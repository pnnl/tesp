# Copyright (C) 2018-2022 Battelle Memorial Institute
# file: prep_ercot_substation_f.py

import json
import math
import os
import numpy as np
import utilities

# write yaml for substation.py to subscribe meter voltages, house temperatures, hvac load and hvac state
# write txt for gridlabd to subscribe house setpoints and meter price; publish meter voltages
# write the json agent dictionary for post-processing, and run-time configuration of substation.py

# we want the same psuedo-random thermostat schedules each time, for repeatability
np.random.seed(0)

######################################################
# top-level data, not presently configurable from JSON
broker = 'tcp://localhost:5570'
marketName = 'Market_1'
unit = 'kW'
control_mode = 'CN_RAMP'
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
max_capacity_reference_bid_quantity = 12000  # 5000
air_temperature = 78.0  # initial house air temperature

###################################################
# top-level data that can be reconfigured from JSON, defaults for ERCOT 8-bus Model
dt = 15
period = 300

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

initial_price = 0.0342
std_dev = 0.0279


#####################################################

def ProcessGLM(fileroot, weatherName):
    dirname = os.path.dirname(fileroot) + '/'
    basename = os.path.basename(fileroot)
    glmname = fileroot + '_glm_dict.json'
    aucSimName = 'substation' + fileroot
    ip = open(glmname).read()
    gd = json.loads(ip)
    gldSimName = gd['FedName']

    print(fileroot, dirname, basename, glmname, gldSimName, aucSimName, weatherName)

    # timings based on period and dt
    periodController = period
    bid_delay = 3.0 * dt  # time controller bids before market clearing
    periodMarket = period

    controllers = {}
    auctions = {}
    batteries = {}
    nAirConditioners = 0
    nControllers = 0
    nBatteries = 0

    # Obtain controller dictionary based on houses with electric cooling
    for key, val in gd['houses'].items():
        if val['cooling'] == 'ELECTRIC':
            nAirConditioners += 1
            if np.random.uniform(0, 1) <= agent_participation:
                nControllers += 1
                houseName = key
                meterName = val['billingmeter_id']
                houseClass = val['house_class']
                controller_name = houseName + '_hvac'

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
                                                'houseName': houseName,
                                                'meterName': meterName,
                                                'houseClass': houseClass,
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

    for key, val in gd['inverters'].items():
        if val['resource'] == 'battery':
            nBatteries += 1
            batName = key
            meterName = val['billingmeter_id']
            batteries[batName] = {'meterName': meterName,
                                  'capacity': val['bat_capacity'],
                                  'rating': val['rated_W'],
                                  'charge': val['bat_soc'] * val['bat_capacity'],
                                  'efficiency': float('{:.4f}'.format(val['inv_eta'] * math.sqrt(val['bat_eta'])))}

    print('controllers', nControllers, 'for', nAirConditioners, 'air conditioners and', nBatteries, 'batteries')
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
                            'stat_value': [0 for _ in range(len(stat_mode))]}

    dictfile = fileroot + '_agent_dict.json'
    dp = open(dictfile, 'w')
    meta = {'markets': auctions,
            'controllers': controllers,
            'batteries': batteries,
            'dt': dt,
            'GridLABD': gldSimName,
            'Weather': weatherName}
    print(json.dumps(meta), file=dp)
    dp.close()

    # write YAML file
    yamlfile = fileroot + '_substation.yaml'
    yp = open(yamlfile, 'w')
    print('name:', aucSimName, file=yp)
    print('time_delta: ' + str(dt) + 's', file=yp)
    print('broker:', broker, file=yp)
    print('aggregate_sub: true', file=yp)
    print('aggregate_pub: true', file=yp)
    print('values:', file=yp)
    print('  LMP:', file=yp)
    print('    topic: pypower/LMP_' + fileroot, file=yp)
    print('    default: 0.1', file=yp)
    print('    type: double', file=yp)
    print('    list: false', file=yp)
    print('  refload:', file=yp)
    print('    topic: ' + gldSimName + '/distribution_load', file=yp)
    print('    default: 0', file=yp)
    print('    type: complex', file=yp)
    print('    list: false', file=yp)
    for key, val in controllers.items():
        houseName = val['houseName']
        meterName = val['meterName']
        print('  ' + key + '#V1:', file=yp)
        print('    topic: ' + gldSimName + '/' + meterName + '/measured_voltage_1', file=yp)
        print('    default: 120', file=yp)
        print('  ' + key + '#Tair:', file=yp)
        print('    topic: ' + gldSimName + '/' + houseName + '/air_temperature', file=yp)
        print('    default: 80', file=yp)
        print('  ' + key + '#Load:', file=yp)
        print('    topic: ' + gldSimName + '/' + houseName + '/hvac_load', file=yp)
        print('    default: 0', file=yp)
        print('  ' + key + '#On:', file=yp)
        print('    topic: ' + gldSimName + '/' + houseName + '/power_state', file=yp)
        print('    default: 0', file=yp)
    yp.close()

    op = open(fileroot + '_gridlabd.txt', 'w')
    print('publish "commit:network_node.distribution_load -> distribution_load; 1000";', file=op)
    print('subscribe "precommit:network_node.positive_sequence_voltage <- pypower/three_phase_voltage_' + fileroot + '";', file=op)
    print('subscribe "precommit:localWeather.temperature <- ' + weatherName + '/temperature";', file=op)
    print('subscribe "precommit:localWeather.humidity <- ' + weatherName + '/humidity";', file=op)
    print('subscribe "precommit:localWeather.solar_direct <- ' + weatherName + '/solar_direct";', file=op)
    print('subscribe "precommit:localWeather.solar_diffuse <- ' + weatherName + '/solar_diffuse";', file=op)
    print('subscribe "precommit:localWeather.pressure <- ' + weatherName + '/pressure";', file=op)
    print('subscribe "precommit:localWeather.wind_speed <- ' + weatherName + '/wind_speed";', file=op)
    #	if len(Eplus_Bus) > 0: # hard-wired names for a single building
    #		print ('subscribe "precommit:Eplus_load.constant_power_A <- eplus_json/power_A";', file=op)
    #		print ('subscribe "precommit:Eplus_load.constant_power_B <- eplus_json/power_B";', file=op)
    #		print ('subscribe "precommit:Eplus_load.constant_power_C <- eplus_json/power_C";', file=op)
    #		print ('subscribe "precommit:Eplus_meter.bill_mode <- eplus_json/bill_mode";', file=op)
    #		print ('subscribe "precommit:Eplus_meter.price <- eplus_json/price";', file=op)
    #		print ('subscribe "precommit:Eplus_meter.monthly_fee <- eplus_json/monthly_fee";', file=op)
    for key, val in controllers.items():
        houseName = val['houseName']
        houseClass = val['houseClass']
        meterName = val['meterName']
        aucSimKey = aucSimName + '/' + key
        print('publish "commit:' + houseName + '.air_temperature -> ' + houseName + '/air_temperature";', file=op)
        print('publish "commit:' + houseName + '.power_state -> ' + houseName + '/power_state";', file=op)
        print('publish "commit:' + houseName + '.hvac_load -> ' + houseName + '/hvac_load";', file=op)
        if ('BIGBOX' in houseClass) or ('OFFICE' in houseClass) or ('STRIPMALL' in houseClass):
            print('publish "commit:' + meterName + '.measured_voltage_A -> ' + meterName + '/measured_voltage_1";',
                  file=op)
        else:
            print('publish "commit:' + meterName + '.measured_voltage_1 -> ' + meterName + '/measured_voltage_1";',
                  file=op)
        print('subscribe "precommit:' + houseName + '.cooling_setpoint <- ' + aucSimKey + '/cooling_setpoint";',
              file=op)
        print('subscribe "precommit:' + houseName + '.heating_setpoint <- ' + aucSimKey + '/heating_setpoint";',
              file=op)
        print('subscribe "precommit:' + houseName + '.thermostat_deadband <- ' + aucSimKey + '/thermostat_deadband";',
              file=op)
        print('subscribe "precommit:' + meterName + '.bill_mode <- ' + aucSimKey + '/bill_mode";', file=op)
        print('subscribe "precommit:' + meterName + '.price <- ' + aucSimKey + '/price";', file=op)
        print('subscribe "precommit:' + meterName + '.monthly_fee <- ' + aucSimKey + '/monthly_fee";', file=op)
    op.close()

    # write topics to the FNCS config yaml file that will be shown in the monitor
    utilities.write_FNCS_config_yaml_file_values(fileroot, controllers)


def prep_ercot_substation(gldfileroot, jsonfile='', weatherName=''):
    global dt, period, Eplus_Bus, agent_participation
    global wakeup_start_lo, wakeup_start_hi, wakeup_set_lo, wakeup_set_hi
    global daylight_start_lo, daylight_start_hi, daylight_set_lo, daylight_set_hi
    global evening_start_lo, evening_start_hi, evening_set_lo, evening_set_hi
    global night_start_lo, night_start_hi, night_set_lo, night_set_hi
    global weekend_day_start_lo, weekend_day_start_hi, weekend_day_set_lo, weekend_day_set_hi
    global weekend_night_start_lo, weekend_night_start_hi, weekend_night_set_lo, weekend_night_set_hi
    global ramp_lo, ramp_hi, deadband_lo, deadband_hi, offset_limit_lo, offset_limit_hi
    global ctrl_cap_lo, ctrl_cap_hi, initial_price, std_dev

    if len(jsonfile) > 1:
        lp = open(jsonfile).read()
        config = json.loads(lp)

        # overwrite the default auction and controller parameters - TODO weekend parameters
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

        agent_participation = 0.01 * float(config['FeederGenerator']['ElectricCoolingParticipation'])

    ProcessGLM(gldfileroot, weatherName)
