# Copyright (C) 2018-2019 Battelle Memorial Institute
# file: prep_microgrid_agent_v1.py
""" Sets up the FNCS and agent configurations for DSOT ercot case 8 example

Public Functions:
    :prep_substation: processes a GridLAB-D file for one substation and one or more feeders
"""
import json
import numpy as np
import os
import math

from datetime import datetime
from tesp_support.helpers import random_norm_trunc

# write yaml for substation.py to subscribe meter voltages, house temperatures, hvac load and hvac state
# write txt for gridlabd to subscribe house setpoints and meter price; publish meter voltages
# write the json agent dictionary for post-processing, and run-time configuration of substation.py

# we want the same psuedo-random thermostat schedules each time, for repeatability
np.random.seed(0)


def select_setpt_occ(prob, mode):
    hdr = hvac_setpt['occ_' + mode][0]
    temp = hvac_setpt['occ_' + mode][1:]
    temp = (np.array(temp)).astype(np.float)
    total = 0
    for row in range(len(temp)):
        total += temp[row][1]
        if total >= prob * 100:
            if temp[row][0] == -2:  # means they dont use hvac unit
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
    temp = (np.array(temp)).astype(np.float)
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
    temp = (np.array(temp)).astype(np.float)
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


def process_glm_with_microgrids(gldfileroot, substationfileroot, weatherfileroot, feedercnt, dso_key):
    """Helper function that processes one GridLAB-D file

    Reads fileroot.glm and writes:

    - *fileroot_agent_dict.json*, contains configuration data for the simple_auction and hvac agents
    - *fileroot_substation.yaml*, contains FNCS subscriptions for the psimple_auction and hvac agents
    - *nameroot_FNCS_Config.txt*, a GridLAB-D include file with FNCS publications and subscriptions

    Args:
        gldfileroot (str): path to and base file name for the GridLAB-D file, without an extension
        substationfileroot (str): path to and base file name for the Substation file, without an extension
        weatherfileroot (str): path to the weather agent file location
    """
    dirname = os.path.dirname(gldfileroot) + '/'
    basename = os.path.basename(gldfileroot)
    glmname = substationfileroot + '_glm_dict.json'

    bus = str(case_config["MarketPrep"]["DSO"]["Bus"])
    #    substation_name = 'substation_' + basename
    substation_name = case_config['SimulationConfig']['Substation']  # 'Substation_' + bus
    ip = open(glmname).read()

    gld = json.loads(ip)
    gld_sim_name = gld['message_name']
    # write GridLAB-D HELICS configuration
    json_file_name_GLD = gldfileroot + '.json'
    config_gld = {'name': gld_sim_name,
                  'loglevel': "warning",
                  'coreType': str('zmq'),
                  'timeDelta': 0.001,
                  'uninterruptible': bool(True),
                  'publications': [],
                  'subscriptions': []}

    # write DSO HELICS configuration
    json_file_name_Sub = substationfileroot + '.json'
    config_Sub = {'name': substation_name,
                  'loglevel': "warning",
                  'coreType': str('zmq'),
                  'timeDelta': 0.001,
                  'uninterruptible': bool(True),
                  'publications': [],
                  'subscriptions': [],
                  'endpoints': []}


    ## Monish Edits:

    config_DG = {}
    for dg_key in case_config['SimulationConfig']['dso'][dso_key]['generators']:
        dg_name = case_config['SimulationConfig']['dso'][dso_key]['generators'][dg_key]['name']

        config_DG[dg_name] = {}
        config_DG[dg_name]['name'] = dg_name
        config_DG[dg_name]['loglevel'] = "warning"
        config_DG[dg_name]['coreType'] = str('zmq')
        config_DG[dg_name]['timeDelta'] = 0.001
        config_DG[dg_name]['uninterruptible'] = bool(True)
        config_DG[dg_name]['publications'] = []
        config_DG[dg_name]['subscriptions'] = []
        config_DG[dg_name]['endpoints'] = []
        config_DG[dg_name]['filters'] = []


    #microgrid_info = case_config['SimulationConfig']['dso'][dso_key]['microgrids']
    for microgrid_key in case_config['SimulationConfig']['dso'][dso_key]['microgrids']:
        microgrid_name = case_config['SimulationConfig']['dso'][dso_key]['microgrids'][microgrid_key]['name']
        microgrid_info = case_config['SimulationConfig']['dso'][dso_key]['microgrids'][microgrid_key]
        microgrid_file_root = substationfileroot.split(dso_key)[0] + microgrid_key + substationfileroot.split(dso_key)[1] + '_' + microgrid_key
        microgrid_file_name = microgrid_file_root  + '_glm_dict.json'

        mg = open(microgrid_file_name).read()
        gd = json.loads(mg)
        gld_sim_name = gd['message_name']

        print('\tgldfileroot -> {0:s}\n\tsubstationfileroot -> {1:s}\n\tdirname -> {2:s}\n\tbasename -> {3:s}\n\tglmname -> {4:s}\n\tgld_sim_name -> {5:s}\n\tsubstation_name -> {6:s}\n\tmicrogrid_name -> {7:s}\n\tmicrogridfileroot -> {8:s}\n\tmicrogridfilename -> {9:s}'.format(
            gldfileroot, substationfileroot, dirname, basename, glmname, gld_sim_name, substation_name, microgrid_name, microgrid_file_root, microgrid_file_name))

        # dictionaries with agents and counters
        markets = {}
        hvac_agents = {}
        battery_agents = {}
        water_heater_agents = {}
        num_hvacs = 0
        num_batteries = 0
        num_water_heaters = 0
        num_markets = 0
        num_hvac_agents_cooling = 0
        num_hvac_agents_heating = 0
        num_battery_agents = 0
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
        water_heater_agent_config = case_config['AgentPrep']['WaterHeater']
        site_map = {}

        if simulation_config['caseType']['flexLoadCase']:
            trans_cust_per = feeder_config['TransactiveHousePercentage']
        else:
            trans_cust_per = 0
        ineligible_cust = 0
        eligible_cust = 0
        # Customer Participation Strategy: Whether a customer (billing meter) will participate or not
        # 1. First find out the % of customers ineligible to participate:
        # % of customers without cooling and with gas fuel type
        if gd['billingmeters']:
            for key, val in gd['billingmeters'].items():
                if val['children']:
                    hse = gd['houses'][val['children'][0]]
                    if hse['cooling'] == 'NONE' and hse['fuel_type'] == 'gas':
                        ineligible_cust += 1
                    else:
                        eligible_cust += 1
            inelig_per = ineligible_cust / (ineligible_cust + eligible_cust) * 100

            # 2. Now check how much % is remaining of requested non participating (transactive) houses
            requested_non_trans_cust_per = (100 - trans_cust_per)
            rem_non_trans_cust_per = requested_non_trans_cust_per - inelig_per
            if rem_non_trans_cust_per < 0:
                rem_non_trans_cust_per = 0
                print("{} % customers are ineligible to participate in market, therefore only {} % of customers "
                      "will be able to participate rather than requested {} %!".format(inelig_per, 100 - inelig_per,
                                                                                       100 - requested_non_trans_cust_per))
            else:
                print("{} % of houses will be participating!".format(trans_cust_per))

            # 3. Find out % of houses that needs to be set non particpating out of total eligible houses
            # For example: if ineligible houses are 5% and requested non-transactive houses is 20%, we only need to set
            # participating as false in 15% of the total houses which means 15/95% houses of the total eligible houses
            eff_non_participating_per = rem_non_trans_cust_per / (100 - inelig_per)

        # Obtain site dictionary. We consider each billing meter to correspond to a site
        site_agent = {}
        for key, val in gd['billingmeters'].items():
            if val['children']:
                slider = np.random.uniform(0, 1)  # TODO: get this from agent prep
                for child in val['children']:
                    site_map[child] = {'slider_setting': slider}
                hse = gd['houses'][val['children'][0]]
                # if hse['cooling'] == 'ELECTRIC' or hse['fuel_type'] == 'electric': # only if hvac eligible house:
                cust_participating = np.random.uniform(0, 1) <= (1 - eff_non_participating_per)
                # else:
                #     cust_participating = False  # if hvac ineligible house
                site_agent[key] = {'slider_setting': slider, 'participating': cust_participating}

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
                json.dump(wconfig, wp, indent=2)
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
                    deadband = np.random.uniform(hvac_agent_config['ThermostatBandLo'],
                                                 hvac_agent_config['ThermostatBandHi'])

                    # TODO: this is only until we agree on the new schedule
                    if simulation_config['ThermostatScheduleVersion'] == 2:
                        # First Do commercial buildings
                        comm_bldg_list = ['OFFICE', 'STRIPMALL', 'BIGBOX', 'large_office', 'medium_small_office',
                                          'warehouse_storage', 'big_box', 'strip_mall', 'education', 'food_service',
                                          'food_sales', 'lodging', 'healthcare_inpatient', 'low_occupancy']
                        if val['house_class'] in comm_bldg_list:
                            # Commercial schedules:
                            if val['house_class'] in ['large_office', 'medium_small_office', 'warehouse_storage', 'education']:
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
                            # New schedule to implmement CBEC's data
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
                            wakeup_set_cool = select_setpt_occ(prob, 'cool')  # when home is occupied during day
                            daylight_set_cool = select_setpt_unocc(wakeup_set_cool,
                                                                   'cool')  # when home is not occupied during day
                            evening_set_cool = wakeup_set_cool  # when home is occupied during evening
                            night_set_cool = select_setpt_night(wakeup_set_cool, daylight_set_cool, 'cool')  # during night
                            # heating - CBEC's data individual behavior
                            wakeup_set_heat = select_setpt_occ(prob, 'heat')
                            daylight_set_heat = select_setpt_unocc(wakeup_set_heat, 'heat')
                            evening_set_heat = wakeup_set_heat
                            night_set_heat = select_setpt_night(wakeup_set_heat, daylight_set_heat, 'heat')
                            # highest heating setpoint must be less than (lowest cooling setpoint - margin of 3 degree)
                            if max(wakeup_set_heat, night_set_heat) > min(wakeup_set_cool, night_set_cool) - 3:
                                offset = max(wakeup_set_heat, night_set_heat) - (min(wakeup_set_cool, night_set_cool) - 3)
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
                        # # Schedule V2
                        # wakeup_start = random_norm_trunc(thermostat_schedule_config['WeekdayWakeStart'])
                        # daylight_start = wakeup_start + random_norm_trunc(
                        #     thermostat_schedule_config['WeekdayWakeToDaylightTime'])
                        # evening_start = random_norm_trunc(thermostat_schedule_config['WeekdayEveningStart'])
                        # night_start = evening_start + random_norm_trunc(thermostat_schedule_config['WeekdayEveningToNightTime'])
                        # weekend_day_start = random_norm_trunc(thermostat_schedule_config['WeekendDaylightStart'])
                        # weekend_night_start = random_norm_trunc(thermostat_schedule_config['WeekendNightStart'])
                        # temp_midpoint = random_norm_trunc(thermostat_schedule_config['TemperatureMidPoint'])
                        # schedule_scalar = random_norm_trunc(thermostat_schedule_config['ScheduleScalar'])
                        # weekday_schedule_offset = thermostat_schedule_config['WeekdayScheduleOffset']
                        # weekend_schedule_offset = thermostat_schedule_config['WeekendScheduleOffset']
                        #
                        # # cooling
                        # wakeup_set_cool = temp_midpoint + (deadband / 2) + schedule_scalar * weekday_schedule_offset['wakeup']
                        # daylight_set_cool = temp_midpoint + (deadband / 2) + \
                        #                     schedule_scalar * weekday_schedule_offset['daylight']
                        # evening_set_cool = temp_midpoint + (deadband / 2) + schedule_scalar * weekday_schedule_offset['evening']
                        # night_set_cool = temp_midpoint + (deadband / 2) + schedule_scalar * weekday_schedule_offset['night']
                        # weekend_day_set_cool = temp_midpoint + (deadband / 2) + \
                        #                        schedule_scalar * weekend_schedule_offset['daylight']
                        # weekend_night_set_cool = temp_midpoint + (deadband / 2) + \
                        #                          schedule_scalar * weekend_schedule_offset['night']
                        # # heating
                        # wakeup_set_heat = temp_midpoint - (deadband / 2) - schedule_scalar * weekday_schedule_offset['wakeup']
                        # daylight_set_heat = temp_midpoint - (deadband / 2) - \
                        #                     schedule_scalar * weekday_schedule_offset['daylight']
                        # evening_set_heat = temp_midpoint - (deadband / 2) - schedule_scalar * weekday_schedule_offset['evening']
                        # night_set_heat = temp_midpoint - (deadband / 2) - schedule_scalar * weekday_schedule_offset['night']
                        # weekend_day_set_heat = temp_midpoint - (deadband / 2) - \
                        #                        schedule_scalar * weekend_schedule_offset['daylight']
                        # weekend_night_set_heat = temp_midpoint - (deadband / 2) - \
                        #                          schedule_scalar * weekend_schedule_offset['night']
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

                    slider = site_map[house_name]['slider_setting']
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
                print('I got a KeyError. Reason - {0}. See: {1}'.format(str(keyErr), format_exc())) # sys.exc_info()[2].tb_))
                pass

        print('configured', num_hvacs, 'agents for air conditioners/heating in', microgrid_key, 'out of which', num_hvac_agents_cooling,
              'are participating in cooling and ', num_hvac_agents_heating, ' are participating in heating')

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
                slider = site_map[key]['slider_setting']
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
        print('configured', num_water_heaters, 'agents for water heaters in', microgrid_key, ' and', num_water_heater_agents, 'are participating')

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
                site_agent[meter_name]['participating'] = participating

                slider = site_map[inverter_name]['slider_setting']

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

                battery_agents[inverter_name] = {'batteryName': inverter_name.replace('ibat', 'bat'),
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

        print('configured', num_batteries, 'agents for batteries in', microgrid_key, ' and', num_battery_agents, 'are participating')
        # lets set random generator state same as before battery agent loop
        np.random.set_state(st0)

        # Obtain market agent dictionary based on markets
        for market in market_config:
            num_markets += 1
            if market == 'DSO':
                num_market_agents += 1
                # The same metricsDetail level basically provides the collection level for both DSO and Retail TODO: maybe make both of them independent.
                if simulation_config['metricsFullDetail'] is True:
                    full_metrics_detail = True
                else:
                    full_metrics_detail = False
                market_name = market_config['DSO']['Name']
                markets[market_name] = {
                    'bus': market_config['DSO']['Bus'],
                    'unit': market_config['DSO']['Unit'],
                    'pricecap': market_config['DSO']['PriceCap'],
                    'num_samples': market_config['DSO']['CurveSamples'],
                    'windowLength': market_config['DSO']['TimeWindowDA'],
                    #                'DSO_Q_max': market_config['DSO']['MaximumQuantity'],
                    'DSO_Q_max': market_config['DSO']['Pnom'] * 1000,
                    'transformer_degradation': market_config['DSO']['TransformerDegradation'],
                    'Pnom': market_config['DSO']['Pnom'],
                    'Qnom': market_config['DSO']['Qnom'],
                    'number_of_customers': market_config['DSO']['number_of_customers'],
                    'RCI_customer_count_mix': market_config['DSO']['RCI customer count mix'],
                    'number_of_gld_homes': market_config['DSO']['number_of_gld_homes'],
                    'distribution_charge_rate': market_config['DSO']['distribution_charge_rate'],
                    'dso_retail_scaling': market_config['DSO']['dso_retail_scaling'],
                    'full_metrics_detail': full_metrics_detail
                }

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
                    'full_metrics_detail': full_metrics_detail
                }
            else:
                print('WARNING: unknown market in configuration')


        print('configured', num_market_agents, 'agents for', num_markets, 'markets')

        #dictfile = substationfileroot + '_agent_dict.json'
        dictfile = microgrid_file_root + '_agent_dict.json'
        dp = open(dictfile, 'w')
        meta = {'markets': markets,
                'hvacs': hvac_agents,
                'batteries': battery_agents,
                'water_heaters': water_heater_agents,
                'site_agent': site_agent,
                'StartTime': simulation_config['StartTime'],
                'EndTime': simulation_config['EndTime'],
                'LogLevel': simulation_config['LogLevel'],
                'solver': simulation_config['solver'],
                'Metrics': feeder_config['Metrics'],
                'MetricsType': feeder_config['MetricsType'],
                'MetricsInterval': feeder_config['MetricsInterval']}
        print(json.dumps(meta), file=dp)
        dp.close()

        #Helics Configuration Scripts
        #json_file_name_Sub = substationfileroot + '.json'
        json_file_name_MG = microgrid_file_root + '.json'
        if feedercnt == 1:
            config_MG = {'name': microgrid_name,
                         'loglevel': "warning",
                         'coreType': str('zmq'),
                         'timeDelta': 0.001,
                         'uninterruptible': bool(True),
                         'publications': [],
                         'subscriptions': [],
                         'endpoints': [],
                         'filters': []}

            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str('gld_load'),
                                           'key': str(gld_sim_name + '/distribution_load'),
                                           'type': str('string'),
                                           'default': str(0)
                                            })

            ## endpoints for Helics Messaging
            config_MG['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_price_RT'),
                                           'name': str( microgrid_name + '/' + substation_name + '/cleared_price_RT'),
                                           'type': str('genmessage')
                                            })
            config_MG['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_quantity_RT'),
                                           'name': str( microgrid_name + '/' + substation_name + '/cleared_quantity_RT'),
                                           'type': str('genmessage')
                                            })
            config_MG['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_price_DA'),
                                           'name': str( microgrid_name + '/' + substation_name + '/cleared_price_DA'),
                                           'type': str('genmessage')
                                            })
            config_MG['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_quantity_DA'),
                                           'name': str( microgrid_name + '/' + substation_name + '/cleared_quantity_DA'),
                                           'type': str('genmessage')
                                            })

            ## endpoints for Helics Messaging
            config_Sub['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_price_RT'),
                                           'name': str( substation_name + '/' + microgrid_name +'/cleared_price_RT'),
                                           'type': str('genmessage')
                                            })
            config_Sub['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_quantity_RT'),
                                           'name': str( substation_name + '/' + microgrid_name + '/cleared_quantity_RT'),
                                           'type': str('genmessage')
                                           })
            config_Sub['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_price_DA'),
                                           'name': str( substation_name + '/' + microgrid_name +'/cleared_price_DA'),
                                           'type': str('genmessage')
                                            })
            config_Sub['endpoints'].append({'global': bool(True),
                                           'info': str('cleared_quantity_DA'),
                                           'name': str( substation_name + '/' + microgrid_name + '/cleared_quantity_DA'),
                                           'type': str('genmessage')
                                           })

            ########################################################################################################
            ################### Adding a  DSO-MG  PUB/SUB depenedency for HELICS Bug ###############################
            ########################################################################################################
            config_Sub['publications'].append({'global': bool(True),
                                              'key': str(substation_name + '/' + microgrid_name + '/Market_status'),
                                              'type': str('string')
                                              })

            config_MG['subscriptions'].append({'required': bool(True),
                                               'info': str('Market_status'),
                                               'key': str(substation_name + '/' + microgrid_name + '/Market_status'),
                                               'type': str('string')
                                               })
            ########################################################################################################

            ## Monish -- Adding endpoints for market data exchange from each MGs
            for mg_key in case_config['SimulationConfig']['dso'][dso_key]['microgrids']:
                mg_name = case_config['SimulationConfig']['dso'][dso_key]['microgrids'][mg_key]['name']
                if mg_name != microgrid_name:
                    config_MG['endpoints'].append({'global': bool(True),
                                                   'info': str('cleared_price_RT'),
                                                   'name': str(microgrid_name + '/' + mg_name + '/cleared_price_RT'),
                                                   'type': str('genmessage')
                                                   })
                    config_MG['endpoints'].append({'global': bool(True),
                                                   'info': str('cleared_quantity_RT'),
                                                   'name': str(microgrid_name + '/' + mg_name + '/cleared_quantity_RT'),
                                                   'type': str('genmessage')
                                                   })
                    config_MG['endpoints'].append({'global': bool(True),
                                                   'info': str('cleared_price_DA'),
                                                   'name': str(microgrid_name + '/' + mg_name + '/cleared_price_DA'),
                                                   'type': str('genmessage')
                                                   })
                    config_MG['endpoints'].append({'global': bool(True),
                                                   'info': str('cleared_quantity_DA'),
                                                   'name': str(microgrid_name + '/' + mg_name + '/cleared_quantity_DA'),
                                                   'type': str('genmessage')
                                                   })
                    ################################################################################################
                    ################### Adding a  MG-MG  PUB/SUB depenedency for HELICS Bug ########################
                    ################################################################################################
                    config_MG['publications'].append({'global': bool(True),
                                                               'key': str(microgrid_name + '/' + mg_name + '/Market_status'),
                                                               'type': str('string')
                                                               })

                    config_MG['subscriptions'].append({'required': bool(True),
                                                       'info': str('Market_status'),
                                                       'key': str(mg_name + '/' + microgrid_name + '/Market_status'),
                                                       'type': str('string')
                                                       })
                    ################################################################################################

            ## Monish -- Adding endpoints for market data exchange from each DGs
            for dg_key in case_config['SimulationConfig']['dso'][dso_key]['generators']:
                dg_name = case_config['SimulationConfig']['dso'][dso_key]['generators'][dg_key]['name']

                ## MG to DGs
                config_MG['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_price_RT'),
                                               'name': str(microgrid_name + '/' + dg_name + '/cleared_price_RT'),
                                               'type': str('genmessage')
                                               })
                config_MG['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_quantity_RT'),
                                               'name': str(microgrid_name + '/' + dg_name + '/cleared_quantity_RT'),
                                               'type': str('genmessage')
                                               })
                config_MG['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_price_DA'),
                                               'name': str(microgrid_name + '/' + dg_name + '/cleared_price_DA'),
                                               'type': str('genmessage')
                                               })
                config_MG['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_quantity_DA'),
                                               'name': str(microgrid_name + '/' + dg_name + '/cleared_quantity_DA'),
                                               'type': str('genmessage')
                                               })

                ## Dgs to MGs
                ####################################################################################################
                ###################### Adding a  MG-DG  PUB/SUB depenedency for HELICS Bug #########################
                ####################################################################################################
                config_MG['publications'].append({'global': bool(True),
                                                  'key': str(microgrid_name + '/' + dg_name + '/Market_status'),
                                                  'type': str('string')
                                                   })

                config_DG[dg_name]['subscriptions'].append({'required': bool(True),
                                                            'info': str('Market_status'),
                                                            'key': str(microgrid_name  + '/' + dg_name + '/Market_status'),
                                                            'type': str('string')
                                                            })
                ###################### Adding a  DG-MG  PUB/SUB depenedency for HELICS Bug #########################
                config_DG[dg_name]['publications'].append({'global': bool(True),
                                                  'key': str(dg_name + '/' + microgrid_name + '/Market_status'),
                                                  'type': str('string')
                                                  })

                config_MG['subscriptions'].append({'required': bool(True),
                                                            'info': str('Market_status'),
                                                            'key': str(dg_name + '/' + microgrid_name + '/Market_status'),
                                                            'type': str('string')
                                                            })
                ####################################################################################################

                config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                'info': str('cleared_price_RT'),
                                                'name': str(dg_name + '/' + microgrid_name + '/cleared_price_RT'),
                                                'type': str('genmessage')
                                                })
                config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                'info': str('cleared_quantity_RT'),
                                                'name': str(dg_name + '/' + microgrid_name + '/cleared_quantity_RT'),
                                                'type': str('genmessage')
                                                })
                config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                'info': str('cleared_price_DA'),
                                                'name': str(dg_name + '/' + microgrid_name + '/cleared_price_DA'),
                                                'type': str('genmessage')
                                                })
                config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                'info': str('cleared_quantity_DA'),
                                                'name': str(dg_name + '/' + microgrid_name + '/cleared_quantity_DA'),
                                                'type': str('genmessage')
                                                })



            ## endpoints for Helics Messaging
            # config_MG['endpoints'].append({'global': bool(True),
            #                                'info': str('price_bid_RT'),
            #                                'name': str(microgrid_name + '/' + substation_name + '/buyer_prices_RT'),
            #                                'type': str('genmessage')
            #                                })
            # config_MG['endpoints'].append({'global': bool(True),
            #                                'info': str('quantity_bid_RT'),
            #                                'name': str(microgrid_name + '/' + substation_name + '/buyer_quantities_RT'),
            #                                'type': str('genmessage')
            #                                })
            # config_MG['endpoints'].append({'global': bool(True),
            #                                'info': str('price_bid_DA'),
            #                                'name': str(microgrid_name + '/' + substation_name + '/buyer_prices_DA'),
            #                                'type': str('genmessage')
            #                                })
            # config_MG['endpoints'].append({'global': bool(True),
            #                                'info': str('quantity_bid_DA'),
            #                                'name': str(microgrid_name + '/' + substation_name + '/buyer_quantities_DA'),
            #                                'type': str('genmessage')
            #                                })
            # ## endpoints for Helics Messaging
            # config_Sub['endpoints'].append({'global': bool(True),
            #                                'info': str('price_bid_RT'),
            #                                'name': str( substation_name + '/' + microgrid_name + '/buyer_prices_RT'),
            #                                'type': str('genmessage')
            #                                 })
            # config_Sub['endpoints'].append({'global': bool(True),
            #                                'info': str('quantity_bid_RT'),
            #                                'name': str( substation_name + '/' + microgrid_name + '/buyer_quantities_RT'),
            #                                'type': str('genmessage')
            #                                 })
            # config_Sub['endpoints'].append({'global': bool(True),
            #                                'info': str('price_bid_DA'),
            #                                'name': str( substation_name + '/' + microgrid_name + '/buyer_prices_DA'),
            #                                'type': str('genmessage')
            #                                 })
            # config_Sub['endpoints'].append({'global': bool(True),
            #                                'info': str('quantity_bid_DA'),
            #                                'name': str( substation_name + '/' + microgrid_name + '/buyer_quantities_DA'),
            #                                'type': str('genmessage')
            #                                 })


            # if simulation_config['keyLoad'] == "refLoadMn":
            #     config_Sub['subscriptions'].append({'required': bool(True),
            #                                     'info': str('ref_rt_load'),
            #                                     'key': str('loadplayer/ref_load_' + bus),
            #                                     'type': str('complex'),
            #                                     'default': str(0)
            #                                     })
            #     config_Sub['subscriptions'].append({'required': bool(True),
            #                                     'info': str('ref_load_history'),
            #                                     'key': str('loadplayer/ref_load_history_' + bus),
            #                                     'type': str('complex'),
            #                                     'default': str(0)
            #                                     })
            # else:
            #     config_Sub['subscriptions'].append({'required': bool(True),
            #                                     'info': str('ind_rt_load'),
            #                                     'key': str('loadplayer/ind_load_' + bus),
            #                                     'type': str('complex'),
            #                                     'default': str(0)
            #                                     })
            #     config_Sub['subscriptions'].append({'required': bool(True),
            #                                     'info': str('ind_load_history_'),
            #                                     'key': str('loadplayer/ind_load_history_' + bus),
            #                                     'type': str('complex'),
            #                                     'default': str(0)
            #                                     })

        for key, val in hvac_agents.items():
            house_name = val['houseName']
            meter_name = val['meterName']

            config_MG['subscriptions'].append({'required': bool(True),
                                            'info': str(key + '#V1'),
                                            'key': str(gld_sim_name + '/' + meter_name + '/measured_voltage_1'),
                                            'type': str('string'),
                                            'default': str(120)
                                            })
            config_MG['subscriptions'].append({'required': bool(True),
                                            'info': str(key + '#Tair'),
                                            'key': str(gld_sim_name + '/' + house_name + '/air_temperature'),
                                            'type': str('string'),
                                            'default': str(80)
                                            })
            config_MG['subscriptions'].append({'required': bool(True),
                                            'info': str(key + '#HvacLoad'),
                                            'key': str(gld_sim_name + '/' + house_name + '/hvac_load'),
                                            'type': str('string'),
                                            'default': str(0)
                                            })
            config_MG['subscriptions'].append({'required': bool(True),
                                            'info': str(key + '#TotalLoad'),
                                            'key': str(gld_sim_name + '/' + house_name + '/total_load'),
                                            'type': str('string'),
                                            'default': str(0)
                                            })
            config_MG['subscriptions'].append({'required': bool(True),
                                            'info': str(key + '#On'),
                                            'key': str(gld_sim_name + '/' + house_name + '/power_state'),
                                            'type': str('string'),
                                            'default': str(0)
                                            })
        for key, val in water_heater_agents.items():
            wh_name = val['waterheaterName']
            config_MG['subscriptions'].append({'required': bool(True),
                                        'info': str(key + '#LTTEMP'),
                                        'key': str(gld_sim_name + '/' + wh_name + '/lower_tank_temperature'),
                                        'type': str('string'),
                                        'default': str(80)
                                        })
            config_MG['subscriptions'].append({'required': bool(True),
                                        'info': str(key + '#UTTEMP'),
                                        'key': str(gld_sim_name + '/' + wh_name + '/upper_tank_temperature'),
                                        'type': str('string'),
                                        'default': str(120)
                                        })
            config_MG['subscriptions'].append({'required': bool(True),
                                        'info': str(key + '#LTState'),
                                        'key': str(gld_sim_name + '/' + wh_name + '/lower_heating_element_state'),
                                        'type': str('string'),
                                        'default': str(0)
                                        })
            config_MG['subscriptions'].append({'required': bool(True),
                                        'info': str(key + '#UTState'),
                                        'key': str(gld_sim_name + '/' + wh_name + '/upper_heating_element_state'),
                                        'type': str('string'),
                                        'default': str(0)
                                        })
            config_MG['subscriptions'].append({'required': bool(True),
                                        'info': str(key + '#WHLoad'),
                                        'key': str(gld_sim_name + '/' + wh_name + '/heating_element_capacity'),
                                        'type': str('string'),
                                        'default': str(0)
                                        })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(key + '#WDRATE'),
                                           'key': str(gld_sim_name + '/' + wh_name + '/water_demand'),
                                           'type': str('string'),
                                           'default': str(0)
                                           })
        for key, val in battery_agents.items():
            battery_name = val['batteryName']
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(key + '#SOC'),
                                           'key': str(gld_sim_name + '/' + battery_name + '/state_of_charge'),
                                           'type': str('string'),
                                           'default': str(0.5)
                                           })
        # these messages are for weather agent used in DSOT agents
        if feedercnt == 1:
            weather_topic = gd['climate']['name']
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#Temperature'),
                                           'key': str(weather_topic + '/' + 'temperature'),
                                           'type': str('string'),
                                           'default': str(70)
                                           })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#TempForecast'),
                                           'key': str(weather_topic + '/' + 'temperature' + '/forecast'),
                                           'type': str('string'),
                                           'default': str(70)
                                           })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#Humidity'),
                                           'key': str(weather_topic + '/' + 'humidity'),
                                           'type': str('string'),
                                           'default': str(0.7)
                                           })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#HumidityForecast'),
                                           'key': str(weather_topic + '/' + 'humidity' + '/forecast'),
                                           'type': str('string'),
                                           'default': str(0.7)
                                           })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#SolarDirect'),
                                           'key': str(weather_topic + '/' + 'solar_direct'),
                                           'type': str('string'),
                                           'default': str(30.0)
                                           })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#SolarDirectForecast'),
                                           'key': str(weather_topic + '/' + 'solar_direct' + '/forecast'),
                                           'type': str('string'),
                                           'default': str(30.0)
                                           })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#SolarDiffuse'),
                                           'key': str(weather_topic + '/' + 'solar_diffuse'),
                                           'type': str('string'),
                                           'default': str(30.0)
                                           })
            config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str(weather_topic + '#SolarDiffuseForecast'),
                                           'key': str(weather_topic + '/' + 'solar_diffuse' + '/forecast'),
                                           'type': str('string'),
                                           'default': str(30.0)
                                           })

        # write GridLAB-D HELICS configuration
        for key, val in hvac_agents.items():
            house_name = val['houseName']
            meter_name = val['meterName']
            #substation_sim_key = substation_name + '/' + key
            substation_sim_key = microgrid_name + '/' + key
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ house_name + '/air_temperature'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + house_name + '\",' +
                                                           '\"property\" : \"' + 'air_temperature' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ house_name + '/power_state'),
                                               'type': str('string'),
                                               'info': str('{\"object\" : \"' + house_name + '\",' +
                                                           '\"property\" : \"' + 'power_state' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ house_name + '/hvac_load'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + house_name + '\",' +
                                                           '\"property\" : \"' + 'hvac_load' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ house_name + '/total_load'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + house_name + '\",' +
                                                           '\"property\" : \"' + 'total_load' + '\"}')
                                               })
            if val['houseClass'] in comm_bldg_list:
                config_gld['publications'].append({'global': bool(True),
                                                   'key': str(gld_sim_name + '/'+ meter_name + '/measured_voltage_1'),
                                                   'type': str('complex'),
                                                   'info': str('{\"object\" : \"' + meter_name + '\",' +
                                                               '\"property\" : \"' + 'measured_voltage_A' + '\"}')
                                                   })
            else:
                config_gld['publications'].append({'global': bool(True),
                                                   'key': str(gld_sim_name + '/'+ meter_name + '/measured_voltage_1'),
                                                   'type': str('complex'),
                                                   'info': str('{\"object\" : \"' + meter_name + '\",' +
                                                               '\"property\" : \"' + 'measured_voltage_1' + '\"}')
                                                   })

            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/cooling_setpoint'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + house_name + '\",' +
                                                           '\"property\" : \"' + 'cooling_setpoint' + '\"}')
                                               })
            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/heating_setpoint'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + house_name + '\",' +
                                                           '\"property\" : \"' + 'heating_setpoint' + '\"}')
                                               })
            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/thermostat_deadband'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + house_name + '\",' +
                                                           '\"property\" : \"' + 'thermostat_deadband' + '\"}')
                                               })
            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/bill_mode'),
                                               'type': str('string'),
                                               'info': str('{\"object\" : \"' + meter_name + '\",' +
                                                           '\"property\" : \"' + 'bill_mode' + '\"}')
                                               })
            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/price'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + meter_name + '\",' +
                                                           '\"property\" : \"' + 'price' + '\"}')
                                               })
            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/monthly_fee'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + meter_name + '\",' +
                                                           '\"property\" : \"' + 'monthly_fee' + '\"}')
                                               })

            #############    Adding those publications to the Substation Script ##################

            config_MG['publications'].append({'global': bool(True),
                                               'key': str(substation_sim_key + '/cooling_setpoint'),
                                               'type': str('double')
                                               })
            config_MG['publications'].append({'global': bool(True),
                                               'key': str(substation_sim_key + '/heating_setpoint'),
                                               'type': str('double')
                                               })
            config_MG['publications'].append({'global': bool(True),
                                               'key': str(substation_sim_key + '/thermostat_deadband'),
                                               'type': str('double')
                                               })
            config_MG['publications'].append({'global': bool(True),
                                               'key': str(substation_sim_key + '/bill_mode'),
                                               'type': str('string')
                                               })
            config_MG['publications'].append({'global': bool(True),
                                               'key': str(substation_sim_key + '/price'),
                                               'type': str('double')
                                               })
            config_MG['publications'].append({'global': bool(True),
                                               'key': str(substation_sim_key + '/monthly_fee'),
                                               'type': str('double')
                                               })
        for key, val in water_heater_agents.items():
            wh_name = key
            meter_name = val['meterName']
            #substation_sim_key = substation_name + '/' + key
            substation_sim_key = microgrid_name + '/' + key
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ wh_name + '/lower_tank_temperature'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'lower_tank_temperature' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ wh_name + '/upper_tank_temperature'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'upper_tank_temperature' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ wh_name + '/lower_heating_element_state'),
                                               'type': str('string'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'lower_heating_element_state' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ wh_name + '/upper_heating_element_state'),
                                               'type': str('string'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'upper_heating_element_state' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ wh_name + '/heating_element_capacity'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'heating_element_capacity' + '\"}')
                                               })
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ wh_name + '/water_demand'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'water_demand' + '\"}')
                                               })

            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/lower_tank_setpoint'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'lower_tank_setpoint' + '\"}')
                                               })
            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/upper_tank_setpoint'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + wh_name + '\",' +
                                                           '\"property\" : \"' + 'upper_tank_setpoint' + '\"}')
                                               })

            #############    Adding those publications to the Substation Script ##################

            config_MG['publications'].append({'global': bool(True),
                                            'key': str(substation_sim_key + '/lower_tank_setpoint'),
                                            'type': str('double')
                                            })
            config_MG['publications'].append({'global': bool(True),
                                            'key': str(substation_sim_key + '/upper_tank_setpoint'),
                                            'type': str('double')
                                            })

        for key, val in battery_agents.items():
            inverter_name = key
            battery_name = val['batteryName']
            meter_name = val['meterName']
            #substation_sim_key = substation_name + '/' + key
            substation_sim_key = microgrid_name + '/' + key
            config_gld['publications'].append({'global': bool(True),
                                               'key': str(gld_sim_name + '/'+ battery_name + '/state_of_charge'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + battery_name + '\",' +
                                                           '\"property\" : \"' + 'state_of_charge' + '\"}')
                                               })

            config_gld['subscriptions'].append({'required': bool(True),
                                               'key': str(substation_sim_key + '/p_out'),
                                               'type': str('double'),
                                               'info': str('{\"object\" : \"' + inverter_name + '\",' +
                                                           '\"property\" : \"' + 'P_Out' + '\"}')
                                               })
            config_gld['subscriptions'].append({'required': bool(True),
                                                'key': str(substation_sim_key + '/q_out'),
                                                'type': str('double'),
                                                'info': str('{\"object\" : \"' + inverter_name + '\",' +
                                                            '\"property\" : \"' + 'Q_Out' + '\"}')
                                                })

            #############    Adding those publications to the Substation Script ##################

            config_MG['publications'].append({'global': bool(True),
                                               'key': str(substation_sim_key + '/p_out'),
                                               'type': str('double')
                                               })
            config_MG['publications'].append({'global': bool(True),
                                                'key': str(substation_sim_key + '/q_out'),
                                                'type': str('double')
                                                })
        #### Adding the Subscription to get the Meter Load ####
        config_MG['subscriptions'].append({'required': bool(True),
                                           'info': str('MG_load'),
                                           'key': str(gld_sim_name + '/' + microgrid_key +'_load'),
                                           'type': str('string'),
                                           'default': str(0)
                                           })

        config_gld['publications'].append({'global': bool(True),
                                           'key': str(gld_sim_name + '/' + microgrid_key +'_load'),
                                           'type': str('complex'),
                                           'info': str('{\"object\" : \"' + microgrid_info['parent'] + '\",' +
                                                       '\"property\" : \"' + 'measured_power' + '\"}')
                                           })

        if "filters" in case_config['SimulationConfig']['dso'][dso_key]['microgrids'][microgrid_key]:
            for end_point in config_MG['endpoints']:
                config_MG['filters'].append({'name': end_point['name'] + '/filter',
                                                      'sourcetarget': end_point['name'],
                                                      'mode': 'source',
                                                      'operation': case_config['SimulationConfig']['dso'][dso_key]['microgrids'][microgrid_key]['filters']['operation'],
                                                      'properties': case_config['SimulationConfig']['dso'][dso_key]['microgrids'][microgrid_key]['filters']['properties']
                                                   })

        json_file_MG= json.dumps(config_MG, indent=4, separators = (',',': '))
        yp_helics = open(json_file_name_MG, 'w')
        print(json_file_MG, file = yp_helics)
        yp_helics.close()

        # json_file_GLD = json.dumps(config_gld, indent=4, separators = (',',': '))
        # op_h = open(json_file_name_GLD, 'w')
        # print(json_file_GLD, file = op_h)
        # op_h.close()

    # write GridLAB-D HELICS configuration
    # Required Once by GridLAB-D
    config_gld['publications'].append({'global': bool(True),
                                       'key': str(gld_sim_name + '/distribution_load'),
                                       'type': str('complex'),
                                       'info': str('{\"object\" : \"' + 'network_node' + '\",' +
                                                   '\"property\" : \"' + 'distribution_load' + '\"}')
                                       })
    if feedercnt == 1:
        if 'climate' in gld:
            for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
                config_gld['subscriptions'].append({'required': bool(True),
                                                    'key': str(gld['climate']['name'] + '/' + wTopic),
                                                    'type': str('double'),
                                                    'info': str('{\"object\" : \"' + gld['climate']['name'] + '\",' +
                                                                '\"property\" : \"' + wTopic + '\"}')
                                                    })

    #####  Adding configuration to send back generator outputs to GLD  #####
    try:
        for gen in case_config['SimulationConfig']['dso'][dso_key]['generators']:
            dg_name = case_config['SimulationConfig']['dso'][dso_key]['generators'][gen]['name']
            for wTopic in ['constant_power_A', 'constant_power_B', 'constant_power_C']:
                config_gld['subscriptions'].append({'required': bool(True),
                                                'key': str(case_config['SimulationConfig']['dso'][dso_key]['generators'][gen]['name'] + '/' + wTopic),
                                                'type': str('complex'),
                                                'info': str('{\"object\" : \"' + case_config['SimulationConfig']['dso'][dso_key]['generators'][gen]['name'] + '\",' +
                                                            '\"property\" : \"' + wTopic + '\"}')
                                                })

                config_DG[dg_name]['publications'].append({'global': bool(True),
                                                  'key': str(case_config['SimulationConfig']['dso'][dso_key]['generators'][gen]['name'] + '/' + wTopic),
                                                  'type': str('complex')
                                                  })


            ## DGs to DSO
            config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_price_RT'),
                                               'name': str(dg_name + '/' + substation_name + '/cleared_price_RT'),
                                               'type': str('genmessage')
                                               })
            config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_quantity_RT'),
                                               'name': str(dg_name + '/' + substation_name + '/cleared_quantity_RT'),
                                               'type': str('genmessage')
                                               })
            config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_price_DA'),
                                               'name': str(dg_name + '/' + substation_name + '/cleared_price_DA'),
                                               'type': str('genmessage')
                                               })
            config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_quantity_DA'),
                                               'name': str(dg_name + '/' + substation_name + '/cleared_quantity_DA'),
                                               'type': str('genmessage')
                                               })
            #### DSO to DG dummy Publication #####
            config_Sub['publications'].append({'global': bool(True),
                                              'key': str(substation_name + '/' + dg_name + '/Market_status'),
                                              'type': str('string')
                                              })
            config_DG[dg_name]['subscriptions'].append({'required': bool(True),
                                                        'info': str('Market_status'),
                                                        'key': str(substation_name + '/' + dg_name + '/Market_status'),
                                                        'type': str('string')
                                                        })

            ## DSO to DGs
            config_Sub['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_price_RT'),
                                               'name': str(substation_name + '/' + dg_name + '/cleared_price_RT'),
                                               'type': str('genmessage')
                                               })
            config_Sub['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_quantity_RT'),
                                               'name': str(substation_name + '/' + dg_name + '/cleared_quantity_RT'),
                                               'type': str('genmessage')
                                               })
            config_Sub['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_price_DA'),
                                               'name': str(substation_name + '/' + dg_name + '/cleared_price_DA'),
                                               'type': str('genmessage')
                                               })
            config_Sub['endpoints'].append({'global': bool(True),
                                               'info': str('cleared_quantity_DA'),
                                               'name': str(substation_name + '/' + dg_name + '/cleared_quantity_DA'),
                                               'type': str('genmessage')
                                               })

            ## DGs to other DGs
            for other_gen in case_config['SimulationConfig']['dso'][dso_key]['generators']:
                other_dg_name = case_config['SimulationConfig']['dso'][dso_key]['generators'][other_gen]['name']
                if dg_name != other_dg_name:
                    config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                       'info': str('cleared_price_RT'),
                                                       'name': str(dg_name + '/' + other_dg_name + '/cleared_price_RT'),
                                                       'type': str('genmessage')
                                                       })
                    config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                       'info': str('cleared_quantity_RT'),
                                                       'name': str(dg_name + '/' + other_dg_name + '/cleared_quantity_RT'),
                                                       'type': str('genmessage')
                                                       })
                    config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                       'info': str('cleared_price_DA'),
                                                       'name': str(dg_name + '/' + other_dg_name + '/cleared_price_DA'),
                                                       'type': str('genmessage')
                                                       })
                    config_DG[dg_name]['endpoints'].append({'global': bool(True),
                                                       'info': str('cleared_quantity_DA'),
                                                       'name': str(dg_name + '/' + other_dg_name + '/cleared_quantity_DA'),
                                                       'type': str('genmessage')
                                                       })

                    ####################################################################################################
                    ###################### Adding a  DG-DG  PUB/SUB depenedency for HELICS Bug #########################
                    ####################################################################################################
                    config_DG[dg_name]['publications'].append({'global': bool(True),
                                                      'key': str(dg_name + '/' + other_dg_name + '/Market_status'),
                                                      'type': str('string')
                                                      })
                    config_DG[dg_name]['subscriptions'].append({'global': bool(True),
                                                      'key': str(other_dg_name + '/' + dg_name + '/Market_status'),
                                                      'type': str('string')
                                                      })
                    ####################################################################################################


            ## Adding code exerpts that creates filters on helics endpoints
            if "filters" in case_config['SimulationConfig']['dso'][dso_key]['generators'][gen]:
                for end_point in config_DG[dg_name]['endpoints']:
                    config_DG[dg_name]['filters'].append({'name': end_point['name'] + '/filter',
                                                          'sourcetarget': end_point['name'],
                                                          'mode': 'source',
                                                          'operation': case_config['SimulationConfig']['dso'][dso_key]['generators'][gen]['filters']['operation'],
                                                          'properties': case_config['SimulationConfig']['dso'][dso_key]['generators'][gen]['filters']['properties']
                                                       })



            DG_file_root = substationfileroot.split(dso_key)[0] + gen +  substationfileroot.split(dso_key)[1] + '_' + gen
            json_file_name_DG = DG_file_root + '.json'

            dictfile = DG_file_root + '_agent_dict.json'
            dg_dso = open(dictfile, 'w')
            meta = {'markets': markets,
                    # 'hvacs': hvac_agents,
                    # 'batteries': battery_agents,
                    # 'water_heaters': water_heater_agents,
                    # 'site_agent': site_agent,
                    'size': case_config['SimulationConfig']['dso'][dso_key]['size'],
                    'generators': case_config['SimulationConfig']['dso'][dso_key]['generators'][gen],
                    'StartTime': simulation_config['StartTime'],
                    'EndTime': simulation_config['EndTime'],
                    'LogLevel': simulation_config['LogLevel'],
                    'solver': simulation_config['solver'],
                    'Metrics': feeder_config['Metrics'],
                    'MetricsType': feeder_config['MetricsType'],
                    'MetricsInterval': feeder_config['MetricsInterval']}
            print(json.dumps(meta), file=dg_dso)
            dg_dso.close()

            json_file_DG = json.dumps(config_DG[dg_name], indent=4, separators=(',', ': '))
            op_dg_helics = open(json_file_name_DG, 'w')
            print(json_file_DG, file=op_dg_helics)
            op_dg_helics.close()

    except:
        print("Something went wrong while creating connections with DGs in GridLAB-D")

    json_file_GLD = json.dumps(config_gld, indent=4, separators=(',', ': '))
    op_helics = open(json_file_name_GLD, 'w')
    print(json_file_GLD, file=op_helics)
    op_helics.close()

    dictfile = substationfileroot + '_agent_dict.json'
    dp_dso = open(dictfile, 'w')
    case_config['SimulationConfig']['dso'][dso_key]['microgrids']
    meta = {'markets': markets,
            # 'hvacs': hvac_agents,
            # 'batteries': battery_agents,
            # 'water_heaters': water_heater_agents,
            # 'site_agent': site_agent,
            'size': case_config['SimulationConfig']['dso'][dso_key]['size'],
            #'generators': case_config['SimulationConfig']['dso'][dso_key]['generators'],
            'StartTime': simulation_config['StartTime'],
            'EndTime': simulation_config['EndTime'],
            'LogLevel': simulation_config['LogLevel'],
            'solver': simulation_config['solver'],
            'Metrics': feeder_config['Metrics'],
            'MetricsType': feeder_config['MetricsType'],
            'MetricsInterval': feeder_config['MetricsInterval']}
    print(json.dumps(meta), file=dp_dso)
    dp_dso.close()

    json_file_Sub = json.dumps(config_Sub, indent=4, separators=(',', ': '))
    dp_dso_helics = open(json_file_name_Sub, 'w')
    print(json_file_Sub, file=dp_dso_helics)
    dp_dso_helics.close()


def prep_substation_with_microgrids(gldfileroot, substationfileroot, weatherfileroot, feedercnt, dso_key, config=None, jsonfile='', hvacSetpt=None):
    """ Process a base GridLAB-D file with supplemental JSON configuration data

    Always reads gldfileroot.glm and writes:

    - *gldfileroot_agent_dict.json*, contains configuration data for the all control agents
    - *gldfileroot_substation.yaml*, contains FNCS subscriptions for the all control agents
    - *gldfileroot_FNCS_Config.txt*, a GridLAB-D include file with FNCS publications and subscriptions

    Futhermore reads either the jsonfile or config dictionary.
    This supplemental data includes time-scheduled thermostat setpoints (NB: do not use the scheduled
    setpoint feature within GridLAB-D, as the first FNCS messages will erase those schedules during
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

    if config is not None or len(jsonfile) > 1:
        if len(jsonfile) > 1:
            lp = open(jsonfile).read()
            case_config = json.loads(lp)
        else:
            case_config = config
    else:
        print('WARNING: neither configuration dictionary or json file provided')

    hvac_setpt = hvacSetpt
    process_glm_with_microgrids(gldfileroot, substationfileroot, weatherfileroot, feedercnt, dso_key)