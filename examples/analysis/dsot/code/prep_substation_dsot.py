# Copyright (C) 2018-2023 Battelle Memorial Institute
# file: prep_substation_dsot.py
""" Sets up the HELICS and agent configurations for DSOT ercot case 8 example

Public Functions:
    :prep_substation: processes a GridLAB-D file for one substation and one or more feeders
"""
import json
import math
import os
from datetime import datetime

import numpy as np

from tesp_support.api.helpers import HelicsMsg
from tesp_support.api.helpers import random_norm_trunc

# write yaml for substation.py to subscribe meter voltages, house temperatures, hvac load and hvac state
# write txt for gridlabd to subscribe house setpoints and meter price; publish meter voltages
# write the json agent dictionary for post-processing, and run-time configuration of substation.py

# we want the same pseudo-random thermostat schedules each time, for repeatability
np.random.seed(0)


def select_setpt_occ(prob, mode):
    hdr = hvac_setpt['occ_' + mode][0]
    temp = hvac_setpt['occ_' + mode][1:]
    temp = (np.array(temp)).astype(np.float64)
    total = 0
    for row in range(len(temp)):
        total += temp[row][1]
        if total >= prob * 100:
            if temp[row][0] == -2:  # means they do not use hvac unit
                if mode == 'cool':
                    return 100  # AC is off most of time for such houses
                elif mode == 'heat':
                    return 40  # Heater if off most of time for such houses
            else:
                return temp[row][0]
    # Need catch for cases where probability is very large (0.99999) and hvac_setpt probabilities add to less than unity
    if total < prob * 100:
        return temp[-1][0]


def select_setpt_unocc(wakeup_set, mode):
    hdr = hvac_setpt['unocc_' + mode][0]
    temp = hvac_setpt['unocc_' + mode][1:]
    temp = (np.array(temp)).astype(np.float64)
    # first get the column corresponding day_occ set-point
    if wakeup_set == 100 and mode == 'cool':
        return 100
    elif wakeup_set == 40 and mode == 'heat':
        return 40
    else:
        day_set = wakeup_set
        clm = hdr.index('HOME DAY TEMPERATURE ' + str(int(wakeup_set)))
        prob2 = np.random.uniform(0, 1)
        total = 0
        for row in range(len(temp)):
            total += temp[row][clm]
            if total >= prob2 * 100:
                day_set = temp[row][0]
                break
        # Need catch for cases where probability is very large (0.99999) and hvac_setpt probabilities add to less than unity
        if total < prob2 * 100:
            day_set = wakeup_set
        # Do not allow cooling setpt when home is unoccupied to be less than when occupied
        if mode == 'cool' and day_set < wakeup_set:
            day_set = wakeup_set
        # Do not allow heating setpt when home is unoccupied to be more than when occupied
        if mode == 'heat' and day_set > wakeup_set:
            day_set = wakeup_set
        return day_set


def select_setpt_night(wakeup_set, daylight_set, mode):
    hdr = hvac_setpt['night_' + mode][0]
    temp = hvac_setpt['night_' + mode][1:]
    temp = (np.array(temp)).astype(np.float64)
    # first get the column corresponding occ and unocc set-point pair
    if wakeup_set == 100 and mode == 'cool':
        return 100
    elif wakeup_set == 40 and mode == 'heat':
        return 40
    else:
        night_set = wakeup_set
        # clm = hdr.index('HOME AND GONE PAIR  ' + str(int(wakeup_set_cool)) + '&' + str(int(daylight_set_cool)) + '-%')
        clm = [i for i in range(len(hdr)) if str(int(wakeup_set)) + '&' + str(int(daylight_set)) in hdr[i]]
        prob2 = np.random.uniform(0, 1)
        total = 0
        for row in range(len(temp)):
            total += temp[row][clm]
            if total >= prob2 * 100:
                night_set = temp[row][0]
                break
        # Need catch for cases where probability is very large (0.99999) and hvac_setpt probabilities add to less than unity
        if total < prob2 * 100:
            night_set = wakeup_set
        # Do not allow cooling setpt at unoccupied home less than at night
        if mode == 'cool' and daylight_set < night_set:
            night_set = wakeup_set
        # Do not allow heating setpt at unoccupied home more than at night
        if mode == 'heat' and daylight_set > night_set:
            night_set = wakeup_set
        return night_set


def process_glm(gldfileroot, substationfileroot, weatherfileroot, feedercnt):
    """ Helper function that processes one GridLAB-D file

    Reads fileroot.glm and writes:

    - *[gldfileroot]_agent_dict.json*, contains configuration data for the simple_auction and hvac agents
    - *[gldfileroot]_substation.json*, contains HELICS subscriptions for the psimple_auction and hvac agents
    - *[gldfileroot]_gridlabd.json*, a GridLAB-D include file with HELICS publications and subscriptions

    Args:
        gldfileroot (str): path to and base file name for the GridLAB-D file, without an extension
        substationfileroot (str): path to and base file name for the Substation file, without an extension
        weatherfileroot (str): path to the weather agent file location
        feedercnt (int):  a count of feeders
    """
    dirname = os.path.dirname(gldfileroot) + '/'
    basename = os.path.basename(gldfileroot)
    glmname = substationfileroot + '_glm_dict.json'

    bus = str(case_config["MarketPrep"]["DSO"]["Bus"])
    #    substation_name = 'substation_' + basename
    substation_name = case_config['SimulationConfig']['Substation']  # 'Substation_' + bus
    ip = open(glmname).read()

    gd = json.loads(ip)
    gld_sim_name = gd['message_name']

    print('\tgldfileroot -> {0:s}\n\tsubstationfileroot -> {1:s}\n\tdirname -> {2:s}\n'
          '\tbasename -> {3:s}\n\tglmname -> {4:s}\n\tgld_sim_name -> {5:s}\n\tsubstation_name -> {6:s}'.
          format(gldfileroot, substationfileroot, dirname, basename, glmname, gld_sim_name, substation_name))

    # dictionaries with agents and counters
    markets = {}
    hvac_agents = {}
    battery_agents = {}
    water_heater_agents = {}
    ev_agents = {}
    pv_agents = {}
    num_hvacs = 0
    num_batteries = 0
    num_water_heaters = 0
    num_evs = 0
    num_pvs = 0
    num_markets = 0
    num_hvac_agents_cooling = 0
    num_hvac_agents_heating = 0
    num_battery_agents = 0
    num_ev_agents = 0
    num_pv_agents = 0
    num_water_heater_agents = 0
    num_market_agents = 0

    simulation_config = case_config['SimulationConfig']
    market_config = case_config['MarketPrep']
    feeder_config = case_config['FeederGenerator']
    # TODO: this is only until we agree on the new schedule
    if simulation_config['ThermostatScheduleVersion'] == 2:
        thermostat_schedule_config = case_config['ThermostatScheduleV2']
    else:
        thermostat_schedule_config = case_config['ThermostatSchedule']
    hvac_agent_config = case_config['AgentPrep']['HVAC']
    battery_agent_config = case_config['AgentPrep']['Battery']
    ev_agent_config = case_config['AgentPrep']['EV']
    water_heater_agent_config = case_config['AgentPrep']['WaterHeater']
    site_map = {}

    if simulation_config['caseType']['fl']:
        trans_cust_per = feeder_config['TransactiveHousePercentage']
    else:
        trans_cust_per = 0
    ineligible_cust = 0
    eligible_cust = 0
    # Customer Participation Strategy: Whether a customer (billing meter) will participate or not
    if gd['billingmeters']:
        # 1. First find out the % of customers ineligible to participate:
        # % of customers without cooling and with gas fuel type
        for key, val in gd['billingmeters'].items():
            if val['children']:
                hse = gd['houses'][val['children'][0]]
                if hse['cooling'] == 'NONE' and hse['fuel_type'] == 'gas':
                    ineligible_cust += 1
                else:
                    eligible_cust += 1
        inelig_per = ineligible_cust / (ineligible_cust + eligible_cust) * 100

        # 2. Now check how much % is remaining of requested non-participating (transactive) houses
        requested_non_trans_cust_per = (100 - trans_cust_per)
        rem_non_trans_cust_per = requested_non_trans_cust_per - inelig_per
        if rem_non_trans_cust_per < 0:
            rem_non_trans_cust_per = 0
            print("{} % customers are ineligible to participate in market, therefore only {} % of customers "
                  "will be able to participate rather than requested {} %!".format(inelig_per, 100 - inelig_per,
                                                                                   100 - requested_non_trans_cust_per))
        else:
            print("{} % of houses will be participating!".format(trans_cust_per))

        # 3. Find out % of houses that needs to be set non-participating out of total eligible houses
        # For example: if ineligible houses are 5% and requested non-transactive houses is 20%, we only need to set
        # participating as false in 15% of the total houses which means 15/95% houses of the total eligible houses
        eff_non_participating_per = rem_non_trans_cust_per / (100 - inelig_per)

    # Obtain site dictionary. We consider each billing meter to correspond to a site
    site_agent = {}
    slider_ranges = case_config['SimulationConfig']['slider_ranges']
    for key, val in gd['billingmeters'].items():
        if val['children']:
            sliders = {'customer': np.random.uniform(0.001, 1.0)}
            for _key, _val in slider_ranges.items():
                sliders[_key] = (sliders['customer'] * (_val['_UP'] - _val['_DOWN']) + _val['_DOWN'])
                if sliders[_key] < _val['_DOWN']:
                    sliders[_key] = _val['_DOWN']
            for child in val['children']:
                site_map[child] = {'slider_settings': sliders}
            cust_participating = np.random.uniform(0, 1) <= (1 - eff_non_participating_per)
            site_agent[key] = {'slider_settings': sliders, 'participating': cust_participating}

    # prepare inputs for weather agent
    # write the weather agent's configuration file
    if 'climate' in gd:
        # check if this weather agent is already implemented
        if not os.path.isfile(weatherfileroot + 'weather_Config.json'):
            time_fmt = '%Y-%m-%d %H:%M:%S'
            dt1 = datetime.strptime(simulation_config['StartTime'], time_fmt)
            dt2 = datetime.strptime(simulation_config['EndTime'], time_fmt)
            seconds = int((dt2 - dt1).total_seconds())
            minutes = int(seconds / 60)
            wconfig = {'name': gd['climate']['name'],
                       'StartTime': simulation_config['StartTime'],
                       'time_stop': str(minutes) + 'm',
                       'time_delta': '1s',
                       'publishInterval': '5m',
                       'Forecast': 1,
                       'ForecastLength': '48h',
                       'PublishTimeAhead': '3s',
                       'AddErrorToForecast': 0,
                       'broker': 'HELICS',
                       'forecastPeriod': 48,
                       'parameters': {}}
            for parm in ['temperature', 'humidity', 'pressure', 'solar_diffuse', 'solar_direct', 'wind_speed']:
                wconfig['parameters'][parm] = {'distribution': 2,
                                               'P_e_bias': 0.5,
                                               'P_e_envelope': 0.08,
                                               'Lower_e_bound': 0.5}

            wp = open(weatherfileroot + 'weather_Config.json', 'w')
            print(json.dumps(wconfig), file=wp)
            wp.close()

    # Obtain hvac agent dictionary based on houses with electric cooling or electric heating
    for key, val in gd['houses'].items():
        try:
            if val['cooling'] == 'ELECTRIC' or val['fuel_type'] == 'electric':
                num_hvacs += 1
                house_name = key
                house_class = val['house_class']
                controller_name = key
                meter_name = val['billingmeter_id']

                # hvac participation depends on whether house is participating or not
                cooling_participating = site_agent[meter_name]['participating'] and val['cooling'] == 'ELECTRIC'
                heating_participating = site_agent[meter_name]['participating'] and val['fuel_type'] == 'electric'

                # in agent debugging mode, we may need to avoid hvac participation for debugging waterheaters only
                if simulation_config['agent_debug_mode']['ON'] and not simulation_config['agent_debug_mode']['flex_hvac']:
                    cooling_participating = False
                    heating_participating = False

                if cooling_participating:
                    num_hvac_agents_cooling += 1
                if heating_participating:
                    num_hvac_agents_heating += 1

                period = hvac_agent_config['MarketClearingPeriod']
                deadband = 2.0

                # TODO: this is only until we agree on the new schedule
                if simulation_config['ThermostatScheduleVersion'] == 2:
                    # First Do commercial buildings
                    comm_bldg_list = ['OFFICE', 'STRIPMALL', 'BIGBOX', 'office',
                                      'warehouse_storage', 'big_box', 'strip_mall', 'education', 'food_service',
                                      'food_sales', 'lodging', 'healthcare_inpatient', 'low_occupancy']
                    if val['house_class'] in comm_bldg_list:
                        # Commercial schedules:
                        if val['house_class'] in ['office', 'warehouse_storage', 'education']:
                            weekday_start = 9
                            weekday_duration = 11
                            weekend_start = 9
                            weekend_duration = 11
                        elif val['house_class'] in ['big_box', 'strip_mall', 'food_service', 'food_sales']:
                            weekday_start = 9
                            weekday_duration = 14
                            weekend_start = 9
                            weekend_duration = 14
                        elif val['house_class'] in ['healthcare inpatient', 'lodging']:
                            weekday_start = 0
                            weekday_duration = 24
                            weekend_start = 0
                            weekend_duration = 24
                        elif val['house_class'] == 'low_occupancy':
                            weekday_start = 12
                            weekday_duration = 4
                            weekend_start = 12
                            weekend_duration = 4
                        else:
                            weekday_start = 9
                            weekday_duration = 11
                            weekend_start = 9
                            weekend_duration = 11
                        wakeup_start = 0.1
                        daylight_start = weekday_start + val['zip_skew'] / 60 / 60
                        evening_start = daylight_start + weekday_duration
                        night_start = 23.9
                        weekend_day_start = weekend_start + val['zip_skew'] / 60 / 60
                        weekend_night_start = weekend_day_start + weekend_duration

                        setback = 5 * np.random.uniform(0, 1)
                        occ_comm_cool_setpoint = 75
                        unocc_comm_cool_setpoint = occ_comm_cool_setpoint + setback
                        occ_comm_heat_setpoint = 70
                        unocc_comm_heat_setpoint = occ_comm_heat_setpoint + setback

                        wakeup_set_cool = unocc_comm_cool_setpoint
                        daylight_set_cool = occ_comm_cool_setpoint
                        evening_set_cool = unocc_comm_cool_setpoint
                        night_set_cool = unocc_comm_cool_setpoint
                        weekend_day_set_cool = occ_comm_cool_setpoint
                        weekend_night_set_cool = night_set_cool
                        wakeup_set_heat = unocc_comm_heat_setpoint
                        daylight_set_heat = occ_comm_heat_setpoint
                        evening_set_heat = unocc_comm_heat_setpoint
                        night_set_heat = unocc_comm_heat_setpoint
                        weekend_day_set_heat = occ_comm_heat_setpoint
                        weekend_night_set_heat = night_set_heat
                    else:
                        # New schedule to implement CBEC's data
                        wakeup_start = random_norm_trunc(thermostat_schedule_config['WeekdayWakeStart'])
                        daylight_start = wakeup_start + random_norm_trunc(
                            thermostat_schedule_config['WeekdayWakeToDaylightTime'])
                        evening_start = random_norm_trunc(thermostat_schedule_config['WeekdayEveningStart'])
                        night_start = evening_start + random_norm_trunc(
                            thermostat_schedule_config['WeekdayEveningToNightTime'])
                        weekend_day_start = random_norm_trunc(thermostat_schedule_config['WeekendDaylightStart'])
                        weekend_night_start = random_norm_trunc(thermostat_schedule_config['WeekendNightStart'])
                        # check if night_start_time is not beyond 24.0
                        night_start = min(night_start, 23.9)
                        weekend_night_start = min(weekend_night_start, 23.9)

                        # cooling - CBEC's data individual behavior
                        prob = np.random.uniform(0, 1)  # a random number
                        # when home is occupied during day
                        wakeup_set_cool = select_setpt_occ(prob, 'cool')
                        # when home is not occupied during day
                        daylight_set_cool = select_setpt_unocc(wakeup_set_cool, 'cool')
                        # when home is occupied during evening
                        evening_set_cool = wakeup_set_cool
                        # during night
                        night_set_cool = select_setpt_night(wakeup_set_cool, daylight_set_cool, 'cool')
                        # heating - CBEC's data individual behavior
                        wakeup_set_heat = select_setpt_occ(prob, 'heat')
                        daylight_set_heat = select_setpt_unocc(wakeup_set_heat, 'heat')
                        evening_set_heat = wakeup_set_heat
                        night_set_heat = select_setpt_night(wakeup_set_heat, daylight_set_heat, 'heat')
                        # highest heating setpoint must be less than (lowest cooling setpoint - margin of 6 degree)
                        if max(wakeup_set_heat, night_set_heat) > min(wakeup_set_cool, night_set_cool) - 6:
                            offset = max(wakeup_set_heat, night_set_heat) - (min(wakeup_set_cool, night_set_cool) - 6)
                            # shift the all cooling setpoints up and heating setpoints down to avoid this condition
                            wakeup_set_cool += offset / 2
                            daylight_set_cool += offset / 2
                            evening_set_cool += offset / 2
                            night_set_cool += offset / 2

                            wakeup_set_heat -= offset / 2
                            daylight_set_heat -= offset / 2
                            evening_set_heat -= offset / 2
                            night_set_heat -= offset / 2

                        weekend_day_set_cool = wakeup_set_cool
                        weekend_night_set_cool = night_set_cool
                        weekend_day_set_heat = wakeup_set_heat
                        weekend_night_set_heat = night_set_heat
                else:
                    wakeup_start = np.random.uniform(thermostat_schedule_config['WeekdayWakeStartLo'],
                                                     thermostat_schedule_config['WeekdayWakeStartHi'])
                    daylight_start = np.random.uniform(thermostat_schedule_config['WeekdayDaylightStartLo'],
                                                       thermostat_schedule_config['WeekdayDaylightStartHi'])
                    evening_start = np.random.uniform(thermostat_schedule_config['WeekdayEveningStartLo'],
                                                      thermostat_schedule_config['WeekdayEveningStartHi'])
                    night_start = np.random.uniform(thermostat_schedule_config['WeekdayNightStartLo'],
                                                    thermostat_schedule_config['WeekdayNightStartHi'])
                    wakeup_set_cool = np.random.uniform(thermostat_schedule_config['WeekdayWakeSetLo'],
                                                        thermostat_schedule_config['WeekdayWakeSetHi'])
                    daylight_set_cool = np.random.uniform(thermostat_schedule_config['WeekdayDaylightSetLo'],
                                                          thermostat_schedule_config['WeekdayDaylightSetHi'])
                    evening_set_cool = np.random.uniform(thermostat_schedule_config['WeekdayEveningSetLo'],
                                                         thermostat_schedule_config['WeekdayEveningSetHi'])
                    night_set_cool = np.random.uniform(thermostat_schedule_config['WeekdayNightSetLo'],
                                                       thermostat_schedule_config['WeekdayNightSetHi'])
                    weekend_day_set_cool = np.random.uniform(thermostat_schedule_config['WeekendDaylightSetLo'],
                                                             thermostat_schedule_config['WeekendDaylightSetHi'])
                    weekend_day_start = np.random.uniform(thermostat_schedule_config['WeekendDaylightStartLo'],
                                                          thermostat_schedule_config['WeekendDaylightStartHi'])
                    weekend_night_start = np.random.uniform(thermostat_schedule_config['WeekendNightStartLo'],
                                                            thermostat_schedule_config['WeekendNightStartHi'])
                    weekend_night_set_cool = np.random.uniform(thermostat_schedule_config['WeekendNightSetLo'],
                                                               thermostat_schedule_config['WeekendNightSetHi'])

                    wakeup_set_heat = 60
                    daylight_set_heat = 60
                    evening_set_heat = 60
                    night_set_heat = 60
                    weekend_day_set_heat = 60
                    weekend_night_set_heat = 60
                ramp_high = hvac_agent_config['ThermostatRampHi']
                ramp_low = hvac_agent_config['ThermostatRampLo']
                range_high = hvac_agent_config['ThermostatRangeHi']
                range_low = hvac_agent_config['ThermostatRangeLo']

                slider = site_map[house_name]['slider_settings']['hv']
                ctrl_cap = np.random.uniform(hvac_agent_config['PriceCapLo'], hvac_agent_config['PriceCapHi'])
                bid_delay = 3 * hvac_agent_config['TimeStepGldAgents']
                hvac_agents[controller_name] = {'houseName': house_name,
                                                'meterName': meter_name,
                                                'houseClass': house_class,
                                                'period': period,
                                                'wakeup_start': float('{:.3f}'.format(wakeup_start)),
                                                'daylight_start': float('{:.3f}'.format(daylight_start)),
                                                'evening_start': float('{:.3f}'.format(evening_start)),
                                                'night_start': float('{:.3f}'.format(night_start)),
                                                'weekend_day_start': float('{:.3f}'.format(weekend_day_start)),
                                                'weekend_night_start': float('{:.3f}'.format(weekend_night_start)),
                                                'wakeup_set_cool': float('{:.3f}'.format(wakeup_set_cool)),
                                                'daylight_set_cool': float('{:.3f}'.format(daylight_set_cool)),
                                                'evening_set_cool': float('{:.3f}'.format(evening_set_cool)),
                                                'night_set_cool': float('{:.3f}'.format(night_set_cool)),
                                                'weekend_day_set_cool': float('{:.3f}'.format(weekend_day_set_cool)),
                                                'weekend_night_set_cool': float('{:.3f}'.format(weekend_night_set_cool)),
                                                'wakeup_set_heat': float('{:.3f}'.format(wakeup_set_heat)),
                                                'daylight_set_heat': float('{:.3f}'.format(daylight_set_heat)),
                                                'evening_set_heat': float('{:.3f}'.format(evening_set_heat)),
                                                'night_set_heat': float('{:.3f}'.format(night_set_heat)),
                                                'weekend_day_set_heat': float('{:.3f}'.format(weekend_day_set_heat)),
                                                'weekend_night_set_heat': float('{:.3f}'.format(weekend_night_set_heat)),
                                                'deadband': float('{:.3f}'.format(deadband)),
                                                'ramp_high_limit': float('{:.4f}'.format(ramp_high)),
                                                'ramp_low_limit': float('{:.4f}'.format(ramp_low)),
                                                'range_high_limit': float('{:.4f}'.format(range_high)),
                                                'range_low_limit': float('{:.4f}'.format(range_low)),
                                                'slider_setting': float('{:.4f}'.format(slider)),
                                                'price_cap': float('{:.3f}'.format(ctrl_cap)),
                                                'bid_delay': bid_delay,
                                                'house_participating': site_agent[meter_name]['participating'],
                                                'cooling_participating': cooling_participating,
                                                'heating_participating': heating_participating}
        except KeyError as keyErr:
            # print('I got a KeyError. Reason - {0}. See: {1}'.format(str(keyErr), format_exc())) # sys.exc_info()[2].tb_))
            pass

    print('configured', num_hvacs, 'agents for air conditioners/heating out of which', num_hvac_agents_cooling,
          'are participating in cooling and', num_hvac_agents_heating, 'are participating in heating')

    # Obtain water heater agent dictionary based on water heaters
    for key, val in gd['houses'].items():
        # 2019/10/22 - turns out the commercial buildings do not have an actual water heater object in the GLM,
        # but rather they are modeled as ZIP loads, being gas water heaters
        try:
            water_heater_name = val['wh_name']
            meter_name = val['billingmeter_id']
            num_water_heaters += 1

            # will this device participate in market
            participating = hvac_agents[key]['house_participating']
            # in agent debugging mode, we may need to avoid wh participation for debugging hvacs only
            if simulation_config['agent_debug_mode']['ON'] and not simulation_config['agent_debug_mode']['flex_wh']:
                participating = False
            slider = site_map[key]['slider_settings']['wh']
            inlet_water_temperature = water_heater_agent_config['InletWaterTemperature']
            ambient_temperature = water_heater_agent_config['AmbientTemperature']
            desired_temperature = water_heater_agent_config['DesiredTemperature']
            maximum_temperature = water_heater_agent_config['MaximumTemperature']
            minimum_temperature = water_heater_agent_config['MinimumTemperature']
            memory_length = water_heater_agent_config['MemoryLength']
            water_draw_sensor = water_heater_agent_config['WaterDrawSensor']
            window_length = water_heater_agent_config['WindowLength']
            weight_sohc = water_heater_agent_config['WeightSOHC']
            weight_comfort = water_heater_agent_config['WeightComfort']
            profit_margin_intercept = water_heater_agent_config['ProfitMarginIntercept']
            profit_margin_slope = water_heater_agent_config['ProfitMarginSlope']
            price_cap = water_heater_agent_config['PriceCap']

            if participating:
                num_water_heater_agents += 1

            water_heater_agents[water_heater_name] = {'waterheaterName': water_heater_name,
                                                      'meterName': meter_name,
                                                      'participating': participating,
                                                      'Tcold': inlet_water_temperature,
                                                      'Tambient': ambient_temperature,
                                                      'Tdesired': desired_temperature,
                                                      'Tmax': maximum_temperature,
                                                      'Tmin': minimum_temperature,
                                                      'length_memory': memory_length,
                                                      'wd_sensor': water_draw_sensor,
                                                      'windowLength': window_length,
                                                      'weight_SOHC': weight_sohc,
                                                      'weight_comfort': weight_comfort,
                                                      'ProfitMargin_intercept': profit_margin_intercept,
                                                      'ProfitMargin_slope': profit_margin_slope,
                                                      'PriceCap': price_cap,
                                                      'slider_setting': slider
                                                      }
        except KeyError as keyErr:
            # print('I got a KeyError. Reason - {0}. See: {1}'.format(str(keyErr), format_exc())) # sys.exc_info()[2].tb_))
            pass
    print('configured', num_water_heaters, 'agents for water heaters and', num_water_heater_agents, 'are participating')

    # Obtain battery agent dictionary based on inverters
    # before go into battery agent, let's store the random generator state
    st0 = np.random.get_state()
    for key, val in gd['inverters'].items():
        if val['resource'] == 'battery':
            num_batteries += 1
            inverter_name = key
            meter_name = val['billingmeter_id']

            # will this device participate in market
            participating = np.random.uniform(0, 1) <= feeder_config['StorageParticipation'] / 100

            # we should also change site_agent participation if batteries are participating
            site_agent[meter_name]['participating'] = site_agent[meter_name]['participating'] or participating

            slider = site_map[inverter_name]['slider_settings']['bt']

            reserve_soc = np.random.uniform(battery_agent_config['BatteryReserveLo'] / 100,
                                            battery_agent_config['BatteryReserveHi'] / 100)
            degrad_fac = battery_agent_config['installed_system_first_cost($/kWh)'] / battery_agent_config[
                'lifetime_cycles']
            pm_lo = battery_agent_config['BatteryProfitMarginLo']
            pm_hi = battery_agent_config['BatteryProfitMarginHi']
            profit_margin = pm_hi - (pm_hi - pm_lo) * slider
            # profit_margin_slope = np.random.uniform(battery_agent_config['BatteryProfitMarginSlopeLo'],
            #                                         battery_agent_config['BatteryProfitMarginSlopeHi'])
            # profit_margin_intercept = np.random.uniform(battery_agent_config['BatteryProfitMarginInterceptLo'],
            #                                             battery_agent_config['BatteryProfitMarginInterceptHi'])
            #
            if participating:
                num_battery_agents += 1

            battery_name = inverter_name.replace('ibat', 'bat')
            battery_agents[inverter_name] = {'batteryName': battery_name,
                                             'meterName': meter_name,
                                             'capacity': val['bat_capacity'],
                                             'rating': val['rated_W'],
                                             'charge': val['bat_soc'] * val['bat_capacity'],
                                             'efficiency': float('{:.4f}'.format(val['inv_eta'] *
                                                                                 math.sqrt(val['bat_eta']))),
                                             'slider_setting': float('{:.4f}'.format(slider)),
                                             'reserved_soc': float('{:.4f}'.format(reserve_soc)),
                                             'profit_margin': float('{:.4f}'.format(profit_margin)),
                                             'degrad_factor': float('{:.4f}'.format(degrad_fac)),
                                             'participating': participating}

    print('configured', num_batteries, 'agents for batteries and', num_battery_agents, 'are participating')
    # lets set random generator state same as before battery agent loop
    np.random.set_state(st0)

    # Obtain ev agent dictionary based on inverters
    # before go into ev agent, let's store the random generator state
    st1 = np.random.get_state()
    for key, val in gd['ev'].items():
        num_evs += 1
        ev_name = val['name']
        meter_name = val['billingmeter_id']

        # will this device participate in market
        participating = np.random.uniform(0, 1) <= feeder_config['EVParticipation'] / 100
        # ev won't participate at all if caseType is not ev
        if not simulation_config['caseType']['ev']:
            participating = False

        # we should also change site_agent participation if evs are participating
        site_agent[meter_name]['participating'] = site_agent[meter_name]['participating'] or participating

        slider = site_map[key]['slider_settings']['ev']

        reserve_soc = np.random.uniform(ev_agent_config['EVReserveLo'] / 100, ev_agent_config['EVReserveHi'] / 100)
        degrad_fac = ev_agent_config['installed_system_first_cost($/kWh)'] / ev_agent_config['lifetime_cycles']
        pm_lo = ev_agent_config['EVProfitMarginLo']
        pm_hi = ev_agent_config['EVProfitMarginHi']
        profit_margin = pm_hi - (pm_hi - pm_lo) * slider
        if participating:
            num_ev_agents += 1

        ev_agents[ev_name] = {'evName': ev_name,
                              'houseName': key,
                              'meterName': meter_name,
                              'work_charging': val['work_charging'],
                              'boundary_cond': ev_agent_config['boundary_cond'],
                              'ev_mode': ev_agent_config['ev_mode'],
                              'initial_soc': val['battery_SOC'],
                              'max_charge': val['max_charge'],
                              'daily_miles': val['daily_miles'],
                              'arrival_work': val['arrival_work'],
                              'arrival_home': val['arrival_home'],
                              'work_duration': val['work_duration'],
                              'home_duration': val['home_duration'],
                              'miles_per_kwh': val['miles_per_kwh'],
                              'range_miles': val['range_miles'],
                              'efficiency': val['efficiency'],
                              'slider_setting': float('{:.4f}'.format(slider)),
                              'reserved_soc': float('{:.4f}'.format(reserve_soc)),
                              'profit_margin': float('{:.4f}'.format(profit_margin)),
                              'degrad_factor': float('{:.4f}'.format(degrad_fac)),
                              'participating': participating}

    print('configured', num_evs, 'agents for electric vehicles and', num_ev_agents, 'are participating')
    # lets set random generator state same as before battery agent loop
    np.random.set_state(st1)

    # Obtain PV agent dictionary based on inverters
    # before go into pv agent, let's store the random generator state
    st2 = np.random.get_state()
    for key, val in gd['inverters'].items():
        if val['resource'] == 'solar':
            num_pvs += 1
            inverter_name = key
            meter_name = val['billingmeter_id']

            # will this device participate in market: PV don't participate at all
            participating = False

            # we should also change site_agent participation if batteries are participating
            site_agent[meter_name]['participating'] = site_agent[meter_name]['participating'] or participating

            slider = site_map[inverter_name]['slider_settings']['pv']

            # scaling factor to multiply with player file MW generation
            # actual pv gen (watt) = pv_rating(W)/rooftop_pv_rating_MW * player_value_MW
            # actual pv gen (watt) = pv_scaling_fac * player_value_MW
            pv_scaling_fac = val['rated_W'] / simulation_config['rooftop_pv_rating_MW']

            if participating:
                num_pv_agents += 1

            pv_agents[inverter_name] = {'pvName': inverter_name,
                                        'meterName': meter_name,
                                        'rating': val['rated_W'],
                                        'scaling_factor': pv_scaling_fac,
                                        'slider_setting': float('{:.4f}'.format(slider)),
                                        'participating': participating}

    print('configured', num_pvs, 'agents for PVs and', num_pv_agents, 'are participating')
    # lets set random generator state same as before battery agent loop
    np.random.set_state(st2)

    # Including quadratic curves to agent_dict if possible
    try:
        with open(simulation_config["quadraticFile"]) as json_file:
            DSO_quadratic_curves = json.load(json_file)
    except:
        DSO_quadratic_curves = None

    # Obtain market agent dictionary based on markets
    for market in market_config:
        num_markets += 1
        if market == 'DSO':
            num_market_agents += 1
            market_name = market_config['DSO']['Name']
            markets[market_name] = {
                'bus': market_config['DSO']['Bus'],
                'unit': market_config['DSO']['Unit'],
                'pricecap': market_config['DSO']['PriceCap'],
                'num_samples': market_config['DSO']['CurveSamples'],
                'windowLength': market_config['DSO']['TimeWindowDA'],
                # 'DSO_Q_max': market_config['DSO']['MaximumQuantity'],
                'DSO_Q_max': market_config['DSO']['Pnom'] * 1000,
                'transformer_degradation': market_config['DSO']['TransformerDegradation'],
                'Pnom': market_config['DSO']['Pnom'],
                'Qnom': market_config['DSO']['Qnom'],
                'number_of_customers': market_config['DSO']['number_of_customers'],
                'RCI_customer_count_mix': market_config['DSO']['RCI customer count mix'],
                'number_of_gld_homes': market_config['DSO']['number_of_gld_homes'],
                'distribution_charge_rate': market_config['DSO']['distribution_charge_rate'],
                'dso_retail_scaling': market_config['DSO']['dso_retail_scaling'],
                'full_metrics_detail': simulation_config['metricsFullDetail'],
                'quadratic': simulation_config['quadratic']
            }
            if DSO_quadratic_curves:
                markets[market_name]['curve_c'] = DSO_quadratic_curves['da_lmp'+str(market_config['DSO']['Bus'])][0]['curve_c']
                markets[market_name]['curve_b'] = DSO_quadratic_curves['da_lmp'+str(market_config['DSO']['Bus'])][0]['curve_b']
                markets[market_name]['curve_a'] = DSO_quadratic_curves['da_lmp'+str(market_config['DSO']['Bus'])][0]['curve_a']

        elif market == 'Retail':
            num_market_agents += 1
            market_name = market_config['Retail']['Name']
            markets[market_name] = {
                'unit': market_config['Retail']['Unit'],
                'pricecap': market_config['Retail']['PriceCap'],
                'num_samples': market_config['Retail']['CurveSamples'],
                'windowLength': market_config['Retail']['TimeWindowDA'],
                #                'Q_max': market_config['Retail']['QMax'],
                'Q_max': market_config['DSO']['Pnom'] * 1000,
                'maxPuLoading': market_config['Retail']['MaxPuLoading'],
                'period_da': market_config['Retail']['period_da'],
                'period_rt': market_config['Retail']['period_rt'],
                'OperatingPeriod': market_config['Retail']['OperatingPeriod'],
                'timeStep': market_config['Retail']['timeStep'],
                'Tamb': market_config['Retail']['Tamb'],
                'delta_T_TO_init': market_config['Retail']['delta_T_TO_init'],
                'delta_T_W_init': market_config['Retail']['delta_T_W_init'],
                'BP': market_config['Retail']['BP'],
                'toc_A': market_config['Retail']['toc_A'],
                'toc_B': market_config['Retail']['toc_B'],
                'Base_Year': market_config['Retail']['Base_Year'],
                'P_Rated': market_config['Retail']['P_Rated'],
                'NLL_rate': market_config['Retail']['NLL_rate'],
                'LL_rate': market_config['Retail']['LL_rate'],
                'Sec_V': market_config['Retail']['Sec_V'],
                'TOU_TOR': market_config['Retail']['TOU_TOR'],
                'TOU_GR': market_config['Retail']['TOU_GR'],
                'Oil_n': market_config['Retail']['Oil_n'],
                'Wind_m': market_config['Retail']['Wind_m'],
                'delta_T_TOR': market_config['Retail']['delta_T_TOR'],
                'delta_T_ave_wind_R': market_config['Retail']['delta_T_ave_wind_R'],
                'full_metrics_detail': simulation_config['metricsFullDetail']
            }

        else:
            print('WARNING: unknown market in configuration')

    print('configured', num_market_agents, 'agents for', num_markets, 'markets')

    if Q_dso_key_g in list(Q_forecast_g.keys()):
        dso_Q_bid_forecast_correction = Q_forecast_g[Q_dso_key_g]
    else:
        dso_Q_bid_forecast_correction = Q_forecast_g['default']
        print('WARNING: utilizing default configuration for dso_Q_bid_forecast_correction')
    markets['Q_bid_forecast_correction'] = dso_Q_bid_forecast_correction

    dictfile = substationfileroot + '_agent_dict.json'
    dp = open(dictfile, 'w')
    meta = {'markets': markets,
            'hvacs': hvac_agents,
            'batteries': battery_agents,
            'water_heaters': water_heater_agents,
            'ev': ev_agents,
            'pv': pv_agents,
            'site_agent': site_agent,
            'StartTime': simulation_config['StartTime'],
            'EndTime': simulation_config['EndTime'],
            'rate': simulation_config['rate'],
            'LogLevel': simulation_config['LogLevel'],
            'solver': simulation_config['solver'],
            'numCore': simulation_config['numCore'],
            'priceSensLoad': simulation_config['priceSensLoad'],
            'serverPort': simulation_config['serverPort'],
            'Metrics': feeder_config['Metrics'],
            'MetricsType': feeder_config['MetricsType'],
            'MetricsInterval': feeder_config['MetricsInterval']}
    print(json.dumps(meta), file=dp)
    dp.close()

    # write the dso helics message configuration
    dso = HelicsMsg.dso
    if feedercnt == 1:
        dso.pubs_n(False, "da_bid_" + bus, "string")
        dso.pubs_n(False, "rt_bid_" + bus, "string")
        dso.subs_n(gld_sim_name + '/gld_load', "string")
        dso.subs_n("pypower/lmp_da_" + bus, "string")
        dso.subs_n("pypower/lmp_rt_" + bus, "string")
        dso.subs_n("pypower/cleared_q_da_" + bus, "string")
        dso.subs_n("pypower/cleared_q_rt_" + bus, "string")
        plyr = simulation_config['keyLoad']
        dso.subs_n(plyr + 'player/' + plyr + '_load_' + bus, "string")
        dso.subs_n(plyr + 'player/' + plyr + '_ld_hist_' + bus, "string")

    for key, val in hvac_agents.items():
        house_name = val["houseName"]
        meter_name = val["meterName"]
        dso.pubs_n(False, key + "/cooling_setpoint", "double")
        dso.pubs_n(False, key + "/heating_setpoint", "double")
        dso.pubs_n(False, key + "/thermostat_deadband", "double")
        dso.pubs_n(False, key + "/bill_mode", "string")
        dso.pubs_n(False, key + "/price", "double")
        dso.pubs_n(False, key + "/monthly_fee", "double")
        dso.subs_n(gld_sim_name + "/" + house_name + "#V1", "complex")
        dso.subs_n(gld_sim_name + "/" + house_name + "#Tair", "double")
        dso.subs_n(gld_sim_name + "/" + house_name + "#HvacLoad", "double")
        dso.subs_n(gld_sim_name + "/" + house_name + "#TotalLoad", "double")
        dso.subs_n(gld_sim_name + "/" + house_name + "#On", "string")

    for key, val in water_heater_agents.items():
        wh_name = val["waterheaterName"]
        dso.pubs_n(False, key + "/lower_tank_setpoint", "double")
        dso.pubs_n(False, key + "/upper_tank_setpoint", "double")
        dso.subs_n(gld_sim_name + "/" + wh_name + "#LTTemp", "string")
        dso.subs_n(gld_sim_name + "/" + wh_name + "#UTTemp", "string")
        dso.subs_n(gld_sim_name + "/" + wh_name + "#LTState", "string")
        dso.subs_n(gld_sim_name + "/" + wh_name + "#UTState", "string")
        dso.subs_n(gld_sim_name + "/" + wh_name + "#WHLoad", "string")
        dso.subs_n(gld_sim_name + "/" + wh_name + "#WDRate", "string")

    for key, val in battery_agents.items():
        # key is the name of inverter resource
        battery_name = val["batteryName"]
        dso.pubs_n(False, key + "/p_out", "double")
        dso.pubs_n(False, key + "/q_out", "double")
        dso.subs_n(gld_sim_name + "/" + battery_name + "#SOC", "double")

    for key, val in ev_agents.items():
        ev_name = val["evName"]
        dso.pubs_n(False, key + "/ev_out", "double")
        dso.subs_n(gld_sim_name + "/" + ev_name + "#SOC", "double")

    # these messages are for weather agent used in DSOT agents
    if feedercnt == 1:
        weather_topic = gd["climate"]["name"] + '/'
        dso.subs_n(weather_topic + "#temperature", "string")
        dso.subs_n(weather_topic + "#temperature#forecast", "string")
        dso.subs_n(weather_topic + "#humidity", "string")
        dso.subs_n(weather_topic + "#humidity#forecast", "string")
        dso.subs_n(weather_topic + "#solar_direct", "string")
        dso.subs_n(weather_topic + "#solar_direct#forecast", "string")
        dso.subs_n(weather_topic + "#solar_diffuse", "string")
        dso.subs_n(weather_topic + "#solar_diffuse#forecast", "string")

    # write GridLAB-D helics message configuration
    gld = HelicsMsg.gld
    if feedercnt == 1:
        gld.pubs(False, "gld_load", "complex", "network_node", "distribution_load")
        # JH says removed this line below when we do not have the TSO in the federation
        gld.subs("pypower/three_phase_voltage_" + bus, "complex", "network_node", "positive_sequence_voltage")
        if 'climate' in gd:
            for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
                gld.subs(gd['climate']['name'] + "/#" + wTopic, "double", gd['climate']['name'], wTopic)

    for key, val in hvac_agents.items():
        house_name = val['houseName']
        meter_name = val['meterName']
        substation_sim_key = "dso" + substation_name + '/' + key
        gld.pubs(False, house_name + "#Tair", "double", house_name, "air_temperature")
        gld.pubs(False, house_name + "#On", "string", house_name, "power_state")
        gld.pubs(False, house_name + "#HvacLoad", "double", house_name, "hvac_load")
        gld.pubs(False, house_name + "#TotalLoad", "double", house_name, "total_load")
        # Identify commercial buildings and map measured voltage correctly
        if val['houseClass'] in comm_bldg_list:
            gld.pubs(False, house_name + "#V1", "complex", meter_name, "measured_voltage_A")
        else:
            gld.pubs(False, house_name + "#V1", "complex", meter_name, "measured_voltage_1")
        gld.subs(substation_sim_key + "/cooling_setpoint", "double", house_name, "cooling_setpoint")
        gld.subs(substation_sim_key + "/heating_setpoint", "double", house_name, "heating_setpoint")
        gld.subs(substation_sim_key + "/thermostat_deadband", "double", house_name, "thermostat_deadband")
        gld.subs(substation_sim_key + "/bill_mode", "string", meter_name, "bill_mode")
        gld.subs(substation_sim_key + "/price", "double", meter_name, "price")
        gld.subs(substation_sim_key + "/monthly_fee", "double", meter_name, "monthly_fee")

    for key, val in water_heater_agents.items():
        wh_name = key
        substation_sim_key = "dso" + substation_name + '/' + key
        gld.pubs(False, wh_name + "#LTTemp", "double", wh_name, "lower_tank_temperature")
        gld.pubs(False, wh_name + "#UTTemp", "double", wh_name, "upper_tank_temperature")
        gld.pubs(False, wh_name + "#LTState", "string", wh_name, "lower_heating_element_state")
        gld.pubs(False, wh_name + "#UTState", "string", wh_name, "upper_heating_element_state")
        gld.pubs(False, wh_name + "#WHLoad", "double", wh_name, "heating_element_capacity")
        gld.pubs(False, wh_name + "#WDRate", "double", wh_name, "water_demand")
        gld.subs(substation_sim_key + "/lower_tank_setpoint", "double", wh_name, "lower_tank_setpoint")
        gld.subs(substation_sim_key + "/upper_tank_setpoint", "double", wh_name, "upper_tank_setpoint")

    for key, val in battery_agents.items():
        # key is the name of inverter resource
        inverter_name = key
        battery_name = val['batteryName']
        substation_sim_key = "dso" + substation_name + '/' + key
        gld.pubs(False, battery_name + "#SOC", "double", battery_name, "state_of_charge")
        gld.subs(substation_sim_key + "/p_out", "double", inverter_name, "P_Out")
        gld.subs(substation_sim_key + "/q_out", "double", inverter_name, "Q_Out")

    for key, val in ev_agents.items():
        ev_name = val['evName']
        substation_sim_key = "dso" + substation_name + '/' + key
        gld.pubs(False, ev_name + "#SOC", "double", ev_name, "battery_SOC")
        gld.subs(substation_sim_key + "/ev_out", "double", ev_name, "maximum_charge_rate")


def prep_substation(gldfileroot, substationfileroot, weatherfileroot, feedercnt,
                    config=None, hvacSetpt=None, jsonfile='', Q_forecast=None, Q_dso_key=None):
    """ Process a base GridLAB-D file with supplemental JSON configuration data

    Always reads gldfileroot.glm and writes:

    - *gldfileroot_agent_dict.json*, contains configuration data for the all control agents
    - *gldfileroot_substation.json*, contains HELICS subscriptions for the all control agents
    - *gldfileroot_gridlabd.json*, a GridLAB-D include file with HELICS publications and subscriptions

    Furthermore, reads either the jsonfile or config dictionary.
    This supplemental data includes time-scheduled thermostat setpoints (NB: do not use the scheduled
    setpoint feature within GridLAB-D, as the first messages will erase those schedules during
    simulation).

    Args:
        gldfileroot (str): path to and base file name for the GridLAB-D file, without an extension
        substationfileroot (str): path to and base file name for the Substation file, without an extension
        weatherfileroot (str): path to the weather agent file location
        config (dict): dictionary of feeder population data already read in, mutually exclusive with jsonfile
        jsonfile (str): fully qualified path to an optional JSON configuration file
    """
    global case_config
    global hvac_setpt

    global Q_forecast_g
    global Q_dso_key_g

    Q_forecast_g = Q_forecast
    Q_dso_key_g = Q_dso_key

    if config is not None or len(jsonfile) > 1:
        if len(jsonfile) > 1:
            lp = open(jsonfile).read()
            case_config = json.loads(lp)
        else:
            case_config = config
    else:
        print('WARNING: neither configuration dictionary or json file provided')

    hvac_setpt = hvacSetpt
    process_glm(gldfileroot, substationfileroot, weatherfileroot, feedercnt)
