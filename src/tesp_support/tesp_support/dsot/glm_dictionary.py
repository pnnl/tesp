# Copyright (c) 2021-2025 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: glm_dictionary.py
# tuned to feederGenerator_TSP.m for sequencing of objects and attributes
"""Functions to create metadata from a GridLAB-D input (GLM) file

Metadata is written to a JSON file, for convenient loading into a Python
dictionary.  It can be used for agent configuration, e.g., to initialize a
forecasting model based on some nominal data.  It's also used with metrics
output in post-processing.

Public Functions:
    :glm_dict: Writes the JSON metadata file.

"""

import os
import json
import math

from ..api.helpers import log


def ercotMeterName(objname):
    """ Enforces the meter naming convention for ERCOT

    Replaces anything after the last _ with *mtr*.

    Args:
        objname (str): the GridLAB-D name of a house or inverter

    Returns:
        str: The GridLAB-D name of upstream meter
    """
    k = objname.rfind('_')
    root1 = objname[:k]
    k = root1.rfind('_')
    return root1[:k] + '_mtr'


def ti_enumeration_string(tok):
    """ if thermal_integrity_level is an integer, convert to a string for the metadata
    """
    if tok == '0':
        return 'VERY_LITTLE'
    if tok == '1':
        return 'LITTLE'
    if tok == '2':
        return 'BELOW_NORMAL'
    if tok == '3':
        return 'NORMAL'
    if tok == '4':
        return 'ABOVE_NORMAL'
    if tok == '5':
        return 'GOOD'
    if tok == '6':
        return 'VERY_GOOD'
    if tok == '7':
        return 'UNKNOWN'
    return tok


def append_include_file(lines, fname):
    if os.path.isfile(fname):
        fp = open(fname, 'r')
        for line in fp:
            lines.append(line)
        fp.close()


def glm_dict(name_root, config=None, ercot=False):  # , te30=False):
    """ This version of glm_dict is deprecated as it does not utilize
    GLMModifier() and instead relies on the .glm to be written with serialized
    print statements that can be read and interpreted line-by-line. Modern .glm
    files are no longer written this way and therefore this dictionary method
    will be inaccurate if used with the new gld_feeder_generator.py or any
    modern .glm-writing script.

    This renamed glm_dict_line() was written to work with:
        - prepare_case_dsot.py
        - residential_feeder_glm.py
        - commercial_feeder_glm.py
        - copperplate_feeder_glm.py

    Writes the JSON metadata file from a GLM file

    This function reads *name_root.glm* and writes *[name_root]_glm_dict.json*
    The GLM file should have some meters and triplex_meters with the
    bill_mode attribute defined, which identifies them as billing meters
    that parent houses and inverters. If this is not the case, ERCOT naming
    rules can be applied to identify billing meters.

    Args:
        name_root (str): path and file name of the GLM file, without the extension
        config (dict):
        ercot (bool): request ERCOT billing meter naming. Defaults to false. --- THIS NEEDS TO LEAVE THIS PLACE
        te30 (bool): request hierarchical meter handling in the 30-house test harness. Defaults to false. --- THIS NEEDS TO LEAVE THIS PLACE
    """

    # first pass, collect first-level include files
    collected_lines = []
    ip = open(name_root + '.glm', 'r')
    for line in ip:
        if '#include' in line:
            lst = line.split()
            if len(lst) > 1:
                incfile = os.path.expandvars(lst[1].strip('\"'))
                append_include_file(collected_lines, incfile)
        else:
            collected_lines.append(line)
    ip.close()

    # second pass, look for the substation
    feeder_id = 'feeder'
    base_feeder = ''
    substationTransformerMVA = 12
    inSwing = False
    for line in collected_lines:
        lst = line.split()
        if len(lst) > 1:
            if lst[1] == 'substation':
                inSwing = True
            if inSwing:
                if lst[0] == 'name':
                    feeder_id = lst[1].strip(';')
                if lst[0] == 'groupid':
                    base_feeder = lst[1].strip(';')
                if lst[0] == 'base_power':
                    substationTransformerMVA = float(lst[1].strip(' ').strip('MVA;')) * 1.0e-6
                    if 'MVA' in line:
                        substationTransformerMVA *= 1.0e6
                    elif 'KVA' in line:
                        substationTransformerMVA *= 1.0e3
                    inSwing = False
                    break

    # third pass, process the other objects
    message_name = ''
    if config is not None:
        bulkpowerBus = config['SimulationConfig']['BulkpowerBus']
    else:
        bulkpowerBus = 'TBD'
    name = ''
    houses = {}
    waterheaters = {}
    ziploads = {}
    billingmeters = {}
    inverters = {}
    ev = {}
    feeders = {}
    capacitors = {}
    regulators = {}
    climateName = ''
    climateInterpolate = ''
    climateLatitude = ''
    climateLongitude = ''

    inHouses = False
    inWaterHeaters = False
    inZIPload = False
    inTriplexMeters = False
    inMeters = False
    inInverters = False
    inEV = False
    hasBattery = False
    hasSolar = False
    inCapacitors = False
    inRegulators = False
    inMessage = False
    inClimate = False
    for line in collected_lines:
        lst = line.split()
        if len(lst) > 1:  # terminates with a } or };
            if lst[1] == 'fncs_msg':
                inMessage = True
            if lst[1] == 'climate':
                inClimate = True
            if lst[1] == 'house':
                inHouses = True
                parent = ''
                inc_level = 'None'
                sqft = 2500.0
                cooling = 'NONE'
                heating = 'NONE'
                stories = 1
                thermal_integrity = 'UNKNOWN'
                doors = 4
                ceiling_height = 8
                Rroof = 30.0
                Rwall = 19.0
                Rfloor = 22.0
                Rdoors = 5.0
                glazing_layers = 2  # GL_TWO
                glass_type = 2  # GM_LOW_E_GLASS
                glazing_treatment = 1  # GT_CLEAR
                window_frame = 2  # WF_THERMAL_BREAK
                airchange_per_hour = 0.5
                cooling_COP = 3.5
                total_thermal_mass_per_floor_area = 2
                house_class = 'SINGLE_FAMILY'
            if inMessage:
                if lst[0] == 'name':
                    message_name = lst[1].strip(';')
                    inMessage = False
            if inClimate:
                if lst[0] == 'name':
                    climateName = lst[1].strip(';')
                if lst[0] == 'interpolate':
                    climateInterpolate = lst[1].strip(';')
                if lst[0] == 'latitude':
                    climateLatitude = lst[1].strip(';')
                if lst[0] == 'longitude':
                    climateLongitude = lst[1].strip(';')
                    inClimate = False
            if lst[1] == 'triplex_meter':
                inTriplexMeters = True
                vln = 120.0
                vll = 240.0
                phases = ''
            if lst[1] == 'meter':
                inMeters = True
                vln = 120.0
                vll = 240.0
                phases = 'ABC'
            if lst[1] == 'inverter':
                inInverters = True
                hasBattery = False
                hasSolar = False
                lastInverter = ''
                rating = 25000.0
                inv_eta = 0.9
                bat_eta = 0.8  # defaults without internal battery model
                soc = 1.0
                capacity = 300150.0  # 6 hr * 115 V * 435 A
            if lst[1] == 'capacitor':
                inCapacitors = True
            if lst[1] == 'regulator':
                inRegulators = True
            if lst[1] == 'waterheater':
                inWaterHeaters = True
            if lst[1] == 'ZIPload':
                inZIPload = True
            if lst[1] == 'evcharger_det':
                inEV = True
            if inCapacitors:
                if lst[0] == 'name':
                    lastCapacitor = lst[1].strip(';')
                    capacitors[lastCapacitor] = {'feeder_id': feeder_id}
                    inCapacitors = False
            if inRegulators:
                if lst[0] == 'name':
                    lastRegulator = lst[1].strip(';')
                    regulators[lastRegulator] = {'feeder_id': feeder_id}
                    inRegulators = False
            if inInverters:
                if lst[0] == 'name' and lastInverter == '':
                    lastInverter = lst[1].strip(';')
                if lst[1] == 'solar':
                    hasSolar = True
                    hasBattery = False
                if lst[1] == 'sol_inverter;':
                    hasSolar = True
                    hasBattery = False
                elif lst[1] == 'battery':
                    hasSolar = False
                    hasBattery = True
                if lst[0] == 'rated_power':
                    rating = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'max_charge_rate':
                    max_charge_rating = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'max_discharge_rate':
                    max_discharge_rating = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'inverter_efficiency':
                    inv_eta = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'round_trip_efficiency':
                    bat_eta = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'state_of_charge':
                    soc = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'battery_capacity':
                    capacity = float(lst[1].strip(' ').strip(';')) * 1.0
            if inEV:
                if lst[0] == 'name':
                    ev_name = lst[1].strip(';')
                if lst[0] == 'parent':
                    ev_parent = lst[1].strip(';')
                if lst[0] == 'battery_SOC':
                    ev_init_soc = float(lst[1].strip(';'))
                if lst[0] == 'work_charging_available':
                    ev_work_charging = (lst[1].strip(';'))
                if lst[0] == 'travel_distance':
                    ev_daily_miles = float(lst[1].strip(';'))
                if lst[0] == 'arrival_at_work':
                    ev_arr_work = int(lst[1].strip(';'))
                if lst[0] == 'arrival_at_home':
                    ev_arr_home = int(lst[1].strip(';'))
                if lst[0] == 'duration_at_work':
                    ev_dur_work = float(lst[1].strip(';'))
                if lst[0] == 'duration_at_home':
                    ev_dur_home = float(lst[1].strip(';'))
                if lst[0] == 'maximum_charge_rate':
                    ev_max_charge = float(lst[1].strip(';'))
                if lst[0] == 'mileage_efficiency':
                    ev_mileage = float(lst[1].strip(';'))
                if lst[0] == 'mileage_classification':
                    ev_range = float(lst[1].strip(';'))
                if lst[0] == 'charging_efficiency':
                    ev_charg_eff = float(lst[1].strip(';'))
                    ev[lastHouse] = {'name': ev_name,
                                     'feeder_id': feeder_id,
                                     'billingmeter_id': lastBillingMeter,
                                     'parent': ev_parent,
                                     'work_charging': ev_work_charging,
                                     'battery_SOC': ev_init_soc,
                                     'max_charge': ev_max_charge,
                                     'daily_miles': ev_daily_miles,
                                     'arrival_work': ev_arr_work,
                                     'arrival_home': ev_arr_home,
                                     'work_duration': ev_dur_work,
                                     'home_duration': ev_dur_home,
                                     'miles_per_kWh': ev_mileage,
                                     'range_miles': ev_range,
                                     'efficiency': ev_charg_eff}
            if inHouses:
                if lst[0] == 'name':
                    name = lst[1].strip(';')
                    if 'Low' in name:
                        inc_level = 'Low'
                    elif 'Middle' in name:
                        inc_level = 'Middle'
                    elif 'Upper' in name:
                        inc_level = 'Upper'
                    # else:
                    #     print('Income level not defined')
                if lst[0] == 'parent':
                    parent = lst[1].strip(';')
                if lst[0] == 'floor_area':
                    sqft = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'number_of_doors':
                    doors = int(lst[1].strip(' ').strip(';'))
                if lst[0] == 'number_of_stories':
                    stories = int(lst[1].strip(' ').strip(';'))
                if lst[0] == 'cooling_system_type':
                    cooling = lst[1].strip(';')
                if lst[0] == 'heating_system_type':
                    heating = lst[1].strip(';')
                if lst[0] == '//' and lst[1] == 'thermal_integrity_level':
                    thermal_integrity = ti_enumeration_string(lst[2].strip(';'))
                if lst[0] == 'groupid':
                    house_class = lst[1].strip(';')
                if lst[0] == 'ceiling_height':
                    ceiling_height = int(lst[1].strip(';'))
                if lst[0] == 'Rroof':
                    Rroof = float(lst[1].strip(';'))
                if lst[0] == 'Rwall':
                    Rwall = float(lst[1].strip(';'))
                if lst[0] == 'Rfloor':
                    Rfloor = float(lst[1].strip(';'))
                if lst[0] == 'Rdoors':
                    Rdoors = float(lst[1].strip(';'))
                if lst[0] == 'glazing_layers':
                    glazing_layers = int(lst[1].strip(';'))
                if lst[0] == 'glass_type':
                    glass_type = int(lst[1].strip(';'))
                if lst[0] == 'glazing_treatment':
                    glazing_treatment = int(lst[1].strip(';'))
                if lst[0] == 'window_frame':
                    window_frame = int(lst[1].strip(';'))
                if lst[0] == 'airchange_per_hour':
                    airchange_per_hour = float(lst[1].strip(';'))
                if lst[0] == 'cooling_COP':
                    cooling_COP = float(lst[1].strip(';'))
                if lst[0] == 'over_sizing_factor':
                    over_sizing_factor = float(lst[1].strip(';'))
                if lst[0] == 'total_thermal_mass_per_floor_area':
                    total_thermal_mass_per_floor_area = float(lst[1].strip(';'))
                if lst[0] == 'aspect_ratio':
                    aspect_ratio = float(lst[1].strip(';'))
                if lst[0] == 'window_exterior_transmission_coefficient':
                    WETC = float(lst[1].strip(';'))
                if lst[0] == 'exterior_wall_fraction':
                    EWR = float(lst[1].strip(';'))
                if lst[0] == 'exterior_floor_fraction':
                    EFR = float(lst[1].strip(';'))
                if lst[0] == 'exterior_ceiling_fraction':
                    ECR = float(lst[1].strip(';'))
                if (lst[0] == 'cooling_setpoint') or (lst[0] == 'heating_setpoint'):
                    # if ercot:
                    #    lastBillingMeter = ercotMeterName(name)
                    #  if ('BIGBOX' in house_class) or ('OFFICE' in house_class) or ('STRIPMALL' in house_class):
                    # TODO:  Need to make this more robust.
                    comm_bldg_list = ['OFFICE', 'STRIPMALL', 'BIGBOX', 'large_office', 'office',
                                      'warehouse_storage', 'big_box', 'strip_mall', 'education', 'food_service',
                                      'food_sales', 'lodging', 'healthcare_inpatient', 'low_occupancy']
                    # comm_bldg_list = ['OFFICE', 'STRIPMALL', 'BIGBOX', 'large', 'medium',
                    #                  'warehouse', 'big', 'strip', 'education', 'food',
                    #                   'food', 'lodging', 'healthcare', 'low']
                    if house_class in comm_bldg_list:
                        lastBillingMeter = parent

                    # report if the house uses gas or electricity as heating fuel type
                    fuel_type = 'electric'
                    if heating == 'GAS':
                        fuel_type = 'gas'
                    houses[name] = {'feeder_id': feeder_id, 'billingmeter_id': lastBillingMeter, 'income_level':inc_level, 'sqft': sqft,
                                    'stories': stories, 'doors': doors, 'thermal_integrity': thermal_integrity,
                                    'cooling': cooling, 'heating': heating, 'wh_gallons': 0,
                                    'house_class': house_class, 'Rroof': Rroof, 'Rwall': Rwall, 'Rfloor': Rfloor,
                                    'Rdoors': Rdoors, 'airchange_per_hour': airchange_per_hour,
                                    'ceiling_height': ceiling_height,
                                    'thermal_mass_per_floor_area': total_thermal_mass_per_floor_area,
                                    'aspect_ratio': aspect_ratio, 'exterior_wall_fraction': EWR,
                                    'exterior_floor_fraction': EFR, 'exterior_ceiling_fraction': ECR,
                                    'window_exterior_transmission_coefficient': WETC,
                                    'glazing_layers': glazing_layers, 'glass_type': glass_type,
                                    'window_frame': window_frame, 'glazing_treatment': glazing_treatment,
                                    'cooling_COP': cooling_COP, 'over_sizing_factor': over_sizing_factor,
                                    'fuel_type': fuel_type}
                    lastHouse = name
                    inHouses = False
            if inWaterHeaters:
                if lst[0] == 'name':
                    whname = lst[1].strip(' ').strip(';')
                    waterheaters[lastHouse] = {'name': whname, 'skew': 0, 'gallons': 0.0, 'tmix': 0.0, 'mlayer': False}
                if lst[0] == 'schedule_skew':
                    waterheaters[lastHouse]['skew'] = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'water_demand':
                    waterheaters[lastHouse]['scalar'] = float(lst[1].split('*')[1].strip(' ').strip(';')) * 1.0
                    waterheaters[lastHouse]['schedule_name'] = (lst[1].split('*')[0].strip(' ').strip(';'))
                if lst[0] == 'tank_volume':
                    waterheaters[lastHouse]['gallons'] = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'T_mixing_valve':
                    waterheaters[lastHouse]['tmix'] = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'waterheater_model':
                    if 'MULTILAYER' == lst[1].strip(' ').strip(';'):
                        waterheaters[lastHouse]['mlayer'] = True
            if inZIPload:
                if lastHouse not in ziploads:
                    hf = 1.0  # default heatgain_fraction = 1.0
                    pf = 1.0  # default power factor = 1.0
                    pfr = 1.0  # default power_fraction = 1.0
                    ziploads[lastHouse] = {'skew': 0, 'heatgain_fraction': {'constant': 1.0},
                                           'scalar': {'constant': 0.0}, 'power_pf': {'constant': 1.0},
                                           'power_fraction': {'constant': 1.0}
                                           }
                # We assume that skew remains same for al zip loads with in a house
                if lst[0] == 'schedule_skew':
                    ziploads[lastHouse]['skew'] = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'heatgain_fraction':
                    hf = float(lst[1].strip(' ').strip(';')) * 1.0  # store hf as we don't know load type yet
                if lst[0] == 'power_pf':
                    pf = float(lst[1].strip(' ').strip(';')) * 1.0  # store pf as we don't know load type yet
                if lst[0] == 'power_fraction':
                    pfr = float(lst[1].strip(' ').strip(';')) * 1.0  # store pfr as we don't know load type yet
                if lst[0] == 'base_power':
                    if '*' in lst[1]:  # if base power of zip load is set via schedule
                        ziploads[lastHouse]['scalar'][lst[1].split('*')[0]] = float(
                            lst[1].split('*')[1].strip(' ').strip(';')) * 1.0
                        ziploads[lastHouse]['heatgain_fraction'][lst[1].split('*')[0]] = hf
                        ziploads[lastHouse]['power_pf'][lst[1].split('*')[0]] = pf
                        ziploads[lastHouse]['power_fraction'][lst[1].split('*')[0]] = pfr
                    else:  # if base power of zip load is constant
                        # add all the constant loads under one label 'constant'
                        ziploads[lastHouse]['scalar']['constant'] = ziploads[lastHouse]['scalar']['constant'] + float(
                            lst[1].strip(' ').strip(';')) * 1.0
                        ziploads[lastHouse]['heatgain_fraction']['constant'] = hf
                        ziploads[lastHouse]['power_pf']['constant'] = pf
                        ziploads[lastHouse]['power_fraction']['constant'] = pfr

            if inTriplexMeters:
                if lst[0] == 'name':
                    name = lst[1].strip(';')
                if lst[0] == 'phases':
                    phases = lst[1].strip(';')
                if lst[0] == 'parent':
                    lastMeterParent = lst[1].strip(';')
                if lst[0] == 'bill_mode':
                    # if te30:
                    #    if 'flatrate' not in name:
                    #        billingmeters[name] = {'feeder_id': feeder_id, 'phases': phases, 'vll': vll, 'vln': vln,
                    #                               'children': [], 'building_type': 'UNKNOWN',
                    #                               'tariff_class': 'industrial'}
                    #        lastBillingMeter = name
                    # else:
                    billingmeters[name] = {'feeder_id': feeder_id, 'phases': phases, 'vll': vll, 'vln': vln,
                                           'children': [], 'building_type': 'UNKNOWN', 'tariff_class': 'industrial'}
                    lastBillingMeter = name
                    inTriplexMeters = False
            if inMeters:
                if lst[0] == 'name':
                    name = lst[1].strip(';')
                if lst[0] == 'phases':
                    phases = lst[1].strip(';')
                if lst[0] == 'parent':
                    lastMeterParent = lst[1].strip(';')
                if lst[0] == 'nominal_voltage':
                    vln = float(lst[1].strip(' ').strip(';')) * 1.0
                    vll = vln * math.sqrt(3.0)
                if lst[0] == 'bill_mode':
                    billingmeters[name] = {'feeder_id': feeder_id, 'phases': phases, 'vll': vll, 'vln': vln,
                                           'children': [], 'building_type': 'UNKNOWN'}
                    lastBillingMeter = name
                    inMeters = False
        elif len(lst) == 1:
            if hasSolar:
                # if ercot:
                #    lastBillingMeter = ercotMeterName(name)
                # elif te30:
                #    lastBillingMeter = lastMeterParent
                inverters[lastInverter] = {'feeder_id': feeder_id,
                                           'billingmeter_id': lastBillingMeter,
                                           'rated_W': rating,
                                           'resource': 'solar',
                                           'inv_eta': inv_eta}
            elif hasBattery:
                # if ercot:
                #    lastBillingMeter = ercotMeterName(name)
                # elif te30:
                #    lastBillingMeter = lastMeterParent
                inverters[lastInverter] = {'feeder_id': feeder_id,
                                           'billingmeter_id': lastBillingMeter,
                                           'rated_W': rating,
                                           'resource': 'battery',
                                           'inv_eta': inv_eta,
                                           'bat_eta': bat_eta,
                                           'bat_capacity': capacity,
                                           'bat_soc': soc}
            hasSolar = False
            hasBattery = False
            inHouses = False
            inWaterHeaters = False
            inZIPload = False
            inTriplexMeters = False
            inMeters = False
            inInverters = False
            inCapacitors = False
            inRegulators = False
            inMessage = False

    for key, val in houses.items():
        if key in waterheaters:
            val['wh_name'] = waterheaters[key]['name']
            val['wh_skew'] = waterheaters[key]['skew']
            val['wh_scalar'] = waterheaters[key]['scalar']
            val['wh_schedule_name'] = waterheaters[key]['schedule_name']
            val['wh_gallons'] = waterheaters[key]['gallons']
            val['wh_tmix'] = waterheaters[key]['tmix']
            val['wh_mlayer'] = waterheaters[key]['mlayer']
        if key in ziploads:
            val['zip_skew'] = ziploads[key]['skew']
            val['zip_heatgain_fraction'] = ziploads[key]['heatgain_fraction']
            val['zip_scalar'] = ziploads[key]['scalar']
            val['zip_power_fraction'] = ziploads[key]['power_fraction']
            val['zip_power_pf'] = ziploads[key]['power_pf']

        # Laurentiu Dan Marinovici 2019/10/22 -
        # turned out that the commercial buildings do not have a bill_mode field in their GLM objects,
        # which led to not have them added to the billing meters fields
        try:
            mtr = billingmeters[val['billingmeter_id']]
            mtr['children'].append(key)
            mtr['building_type'] = val['house_class']
            # Also add tariff customer class to meter meta data
            for bldg in comm_bldg_list:
                if bldg in mtr['building_type']:
                    mtr['tariff_class'] = 'commercial'
            for bldg in ['SINGLE_FAMILY', 'MOBILE_HOME', 'APARTMENTS', 'MULTI_FAMILY']:
                if bldg in mtr['building_type']:
                    mtr['tariff_class'] = 'residential'
        except KeyError as keyErr:
            log.debug(f"Got a KeyError. Reason - {keyErr}")
            pass

    for key, val in inverters.items():
        mtr = billingmeters[val['billingmeter_id']]
        mtr['children'].append(key)
    for key, val in ev.items():
        mtr = billingmeters[val['billingmeter_id']]
        mtr['children'].append(val['name'])

    climate = {'name': climateName, 'interpolation': climateInterpolate, 'latitude': climateLatitude,
               'longitude': climateLongitude}

    feeders[feeder_id] = {'house_count': len(houses), 'inverter_count': len(inverters), 'ev_count': len(ev)}
    substation = {'bulkpower_bus': bulkpowerBus, 'message_name': message_name,
                  'transformer_MVA': substationTransformerMVA,
                  'base_feeder': base_feeder, 'feeders': feeders,
                  'billingmeters': billingmeters, 'houses': houses, 'inverters': inverters, 'ev': ev,
                  'capacitors': capacitors, 'regulators': regulators, 'climate': climate}
    op = open(name_root + '_glm_dict.json', 'w')
    json.dump(substation, op, ensure_ascii=False, indent=2)
    op.close()

def glm_diction(case_name, feed_key):
    """Writes the JSON metadata file with the feeder information.
    Utilizes GLMModifier() to read and parse through the .glm

    Args:
        case_name (str): name of the test case
        feed_key (str): feeder number
    """
    import math
    from tesp_support.api.modify_GLM import GLMModifier

    glmMod = GLMModifier()
    glm, success = glmMod.read_model(case_name + '/' + feed_key + '/' + feed_key + '.glm')

    billingmeters = {}
    houses = {}
    inverters = {}
    ev = {}
    regulators = {}
    capacitors = {}
    weather = {}
    feeders = {}
    ziploads = {}
    waterheaters = {}

    for name, climate in glm.climate.items():
        weather = {'name': str(name),
                'interpolation': climate["interpolate"],
                'latitude': float(climate["latitude"]),
                'longitude': float(climate["longitude"])}

    for hs_name, house in glm.house.items():
        if 'Low' in hs_name:
            inc_level = 'Low'
        elif 'Middle' in hs_name:
            inc_level = 'Middle'
        elif 'Upper' in hs_name:
            inc_level = 'Upper'
        else:
            inc_level = ""
        building_type = house["groupid"]

        if house['heating_system_type'] == 'GAS':
            fuel_type = 'gas'
        else:
            fuel_type = 'electric'

        # Assign Residential vs C&I buildings parameters
        if building_type in ['SINGLE_FAMILY', 'MOBILE_HOME', 'APARTMENTS', 'MULTI_FAMILY']:
            tariff_class = 'residential'
            number_of_doors = 4 # GLD default, if unspecified
            number_of_stories = house["number_of_stories"]
            ceiling_height = house["ceiling_height"]
            window_exterior_transmission_coefficient = house["window_exterior_transmission_coefficient"]
            billingmeters[glm.triplex_meter.instances[house['parent']]['parent']] = {'feeder_id': feed_key,
                            'phases': glm.triplex_meter.instances[glm.triplex_meter.instances[house['parent']]['parent']]['phases'],
                            'vll': math.sqrt(3.0)*float(glm.triplex_meter.instances[glm.triplex_meter.instances[house['parent']]['parent']]['nominal_voltage']),
                            'vln': float(glm.triplex_meter.instances[glm.triplex_meter.instances[house['parent']]['parent']]['nominal_voltage']),
                            'children': [],
                            'building_type': building_type,
                            'tariff_class': tariff_class}
            houses[hs_name] = {'feeder_id': feed_key,
                'billingmeter_id': glm.triplex_meter.instances[house['parent']]['parent'],
                'income_level':inc_level,
                'sqft': house["floor_area"],
                'stories': int(number_of_stories),
                'doors': int(number_of_doors),
                'cooling': house['cooling_system_type'],
                'heating': house['heating_system_type'],
                'house_class': house['groupid'],
                'Rroof': float(house["Rroof"]),
                'Rwall': float(house["Rwall"]),
                'Rfloor': float(house["Rfloor"]),
                'Rdoors': float(house["Rdoors"]),
                'airchange_per_hour': float(house["airchange_per_hour"]),
                'ceiling_height': float(ceiling_height),
                'thermal_mass_per_floor_area': float(house["total_thermal_mass_per_floor_area"]),
                'aspect_ratio': float(house["aspect_ratio"]),
                'exterior_wall_fraction': float(house["exterior_wall_fraction"]),
                'exterior_floor_fraction': float(house["exterior_floor_fraction"]),
                'exterior_ceiling_fraction': float(house["exterior_ceiling_fraction"]),
                'window_exterior_transmission_coefficient': float(window_exterior_transmission_coefficient),
                'glazing_layers': int(house["glazing_layers"]),
                'glass_type': int(house["glass_type"]),
                'window_frame': int(house["window_frame"]),
                'glazing_treatment': int(house["glazing_treatment"]),
                'cooling_COP': float(house["cooling_COP"]),
                'over_sizing_factor': float(house["over_sizing_factor"]),
                'fuel_type': fuel_type,
                "zip_skew": 0,
                "zip_heatgain_fraction": {'constant': 1.0},
                "zip_scalar": {'constant': 0.0},
                "zip_power_fraction": {'constant': 1.0},
                "zip_power_pf": {'constant': 1.0}
                }

            wh_name = hs_name.replace(hs_name, f'{hs_name}_wh')
            try:
                wh_gallons = float(glm.waterheater.instances[wh_name]["tank_volume"])
                wh_skew = float(glm.waterheater.instances[wh_name]["schedule_skew"])
                wh_diameter = float(glm.waterheater.instances[wh_name]["tank_diameter"])
                wh_model = glm.waterheater.instances[wh_name]["waterheater_model"]
                if "*" in glm.waterheater.instances[wh_name]["water_demand"]:
                    # if base power is set via schedule, extract just the numeric part after the "*"
                    wh_scalar = glm.waterheater.instances[wh_name]["water_demand"].split("*")[-1].strip()
                    wh_schedule_name = glm.waterheater.instances[wh_name]["water_demand"].split("*")[0].strip()

                houses[hs_name]['wh_name'] = wh_name
                houses[hs_name]['wh_gallons'] = float(wh_gallons)
                houses[hs_name]['wh_skew'] = float(wh_skew)
                houses[hs_name]['wh_schedule_name'] = wh_schedule_name
                houses[hs_name]['wh_diameter'] = float(wh_diameter)
                houses[hs_name]['wh_model'] = wh_model
                houses[hs_name]['wh_scalar'] = float(wh_scalar)
                houses[hs_name]['wh_schedule_name'] = wh_schedule_name

                if wh_model == 'MULTILAYER':
                    wh_tmix = glm.waterheater.instances[wh_name]["T_mixing_valve"]
                    wh_setpoint = float(glm.waterheater.instances[wh_name]["lower_tank_setpoint"])

                    houses[hs_name]['wh_tmix'] = float(wh_tmix)
                    houses[hs_name]['wh_mlayer'] = True
                    houses[hs_name]['wh_setpoint'] = float(wh_setpoint)
                else:
                    wh_setpoint = float(glm.waterheater.instances[wh_name]["tank_setpoint"])
                    houses[hs_name]['wh_setpoint'] = float(wh_setpoint)

            except KeyError:
                # If the house doesn't have an electric water heater
                pass

            un_zip_name = hs_name.replace(hs_name, f'{hs_name}_unresponsive')
            re_zip_name = hs_name.replace(hs_name, f'{hs_name}_responsive')
            names = {re_zip_name, un_zip_name}
            strings = {'responsive', 'unresponsive'}
            for zip_name in names:
                scalar = {}
                hf = {}
                pf = {}
                p_pf = {}
                try:
                    zip_skew = glm.ZIPload.instances[zip_name]['schedule_skew']
                    hf[zip_name] = glm.ZIPload.instances[zip_name]['heatgain_fraction']
                    pf[zip_name] = glm.ZIPload.instances[zip_name]['power_fraction']
                    p_pf[zip_name] = glm.ZIPload.instances[zip_name]['power_pf']
                    if "*" in glm.ZIPload.instances[zip_name]['base_power']:
                        # if base power is set via schedule, extract just the numeric part after the "*"
                        zip_scalar = glm.ZIPload.instances[zip_name]['base_power'].split("*")[-1].strip()
                        scalar[zip_name] = zip_scalar
                    else:
                        scalar[zip_name] = glm.ZIPload.instances[zip_name]['base_power']
                    
                    for string in strings:
                        if string in zip_name:
                            houses[hs_name]["zip_skew"] = float(zip_skew)
                            houses[hs_name]["zip_heatgain_fraction"][f'{string}_loads'] = float(hf[zip_name])
                            houses[hs_name]["zip_scalar"][f'{string}_loads'] = float(scalar[zip_name])
                            houses[hs_name]["zip_power_fraction"][f'{string}_loads'] = float(pf[zip_name])
                            houses[hs_name]["zip_power_pf"][f'{string}_loads'] = float(p_pf[zip_name])

                except KeyError:
                    # Not every house has ziploads
                    pass

            billingmeters[glm.triplex_meter.instances[house['parent']]['parent']]['children'].append(hs_name)

        elif building_type in ['office', 'warehouse_storage', 'big_box', 'strip_mall', 'education', 'food_service', 'food_sales', 'lodging', 'healthcare_inpatient', 'low_occupancy']:
            tariff_class = 'commercial'
            number_of_doors = house["number_of_doors"]
            try:
                number_of_stories = house["number_of_stories"]
                ceiling_height = house["ceiling_height"]
                window_exterior_transmission_coefficient = house["window_exterior_transmission_coefficient"]
            except KeyError:
                number_of_stories = 1
                ceiling_height = 13
                window_exterior_transmission_coefficient = 0
            billingmeters[house['parent']] = {'feeder_id': feed_key,
                            'phases': glm.meter.instances[house['parent']]['phases'],
                            'vll': math.sqrt(3.0)*float(glm.meter.instances[house['parent']]['nominal_voltage']),
                            'vln': float(glm.meter.instances[house['parent']]['nominal_voltage']),
                            'children': [],
                            'building_type': building_type,
                            'tariff_class': tariff_class}
            try:
                houses[hs_name] = {'feeder_id': feed_key,
                    'billingmeter_id': house['parent'],
                    'income_level': inc_level,
                    'building_type': building_type,
                    'sqft': house["floor_area"],
                    'stories': int(number_of_stories),
                    'doors': int(number_of_doors),
                    'cooling': house['cooling_system_type'],
                    'heating': house['heating_system_type'],
                    'house_class': house['groupid'],
                    'Rroof': float(house["Rroof"]),
                    'Rwall': float(house["Rwall"]),
                    'Rfloor': float(house["Rfloor"]),
                    'Rdoors': float(house["Rdoors"]),
                    'airchange_per_hour': float(house["airchange_per_hour"]),
                    'ceiling_height': float(ceiling_height),
                    'thermal_mass_per_floor_area': float(house["total_thermal_mass_per_floor_area"]),
                    'aspect_ratio': float(house["aspect_ratio"]),
                    'exterior_wall_fraction': float(house["exterior_wall_fraction"]),
                    'exterior_floor_fraction': float(house["exterior_floor_fraction"]),
                    'exterior_ceiling_fraction': float(house["exterior_ceiling_fraction"]),
                    'window_exterior_transmission_coefficient': float(window_exterior_transmission_coefficient),
                    'glazing_layers': int(house["glazing_layers"]),
                    'glass_type': int(house["glass_type"]),
                    'window_frame': int(house["window_frame"]),
                    'glazing_treatment':  int(house["glazing_treatment"]),
                    'cooling_COP': float(house["cooling_COP"]),
                    'over_sizing_factor': float(house["over_sizing_factor"]),
                    'fuel_type': fuel_type,
                    "zip_skew": 0,
                    "zip_heatgain_fraction": {'constant': 1.0},
                    "zip_scalar": {'constant': 0.0},
                    "zip_power_fraction": {'constant': 1.0},
                    "zip_power_pf": {'constant': 1.0}
                    }
            except KeyError:
                houses[hs_name] = {'feeder_id': feed_key,
                    'billingmeter_id': house['parent'],
                    'income_level': inc_level,
                    'building_type': building_type,
                    'sqft': house["floor_area"],
                    'stories': int(number_of_stories),
                    'doors': int(number_of_doors),
                    'cooling': house['cooling_system_type'],
                    'heating': house['heating_system_type'],
                    'house_class': house['groupid'],
                    'Rroof': float(house["Rroof"]),
                    'Rwall': float(house["Rwall"]),
                    'Rfloor': float(house["Rfloor"]),
                    'Rdoors': float(house["Rdoors"]),
                    'airchange_per_hour': float(house["airchange_per_hour"]),
                    'ceiling_height': float(ceiling_height),
                    'thermal_mass_per_floor_area': float(house["total_thermal_mass_per_floor_area"]),
                    'aspect_ratio': float(house["aspect_ratio"]),
                    'exterior_wall_fraction': float(house["exterior_wall_fraction"]),
                    'exterior_floor_fraction': float(house["exterior_floor_fraction"]),
                    'exterior_ceiling_fraction': float(house["exterior_ceiling_fraction"]),
                    'window_exterior_transmission_coefficient': float(window_exterior_transmission_coefficient),
                    'cooling_COP': float(house["cooling_COP"]),
                    'over_sizing_factor': float(house["over_sizing_factor"]),
                    'fuel_type': fuel_type,
                    "zip_heatgain_fraction": {'constant': 1.0},
                    "zip_scalar": {'constant': 0.0},
                    "zip_power_fraction": {'constant': 1.0},
                    "zip_power_pf": {'constant': 1.0}
                    }

            wh_name = hs_name.replace(hs_name, f'{hs_name}_wh')
            try:
                wh_gallons = float(glm.waterheater.instances[wh_name]["tank_volume"])
                wh_skew = float(glm.waterheater.instances[wh_name]["schedule_skew"])
                wh_diameter = float(glm.waterheater.instances[wh_name]["tank_diameter"])
                wh_model = glm.waterheater.instances[wh_name]["waterheater_model"]
                if "*" in glm.waterheater.instances[wh_name]["water_demand"]:
                    # if base power is set via schedule, extract just the numeric part after the "*"
                    wh_scalar = glm.waterheater.instances[wh_name]["water_demand"].split("*")[-1].strip()
                    wh_schedule_name = glm.waterheater.instances[wh_name]["water_demand"].split("*")[0].strip()

                houses[hs_name]['wh_name'] = wh_name
                houses[hs_name]['wh_gallons'] = float(wh_gallons)
                houses[hs_name]['wh_skew'] = float(wh_skew)
                houses[hs_name]['wh_schedule_name'] = wh_schedule_name
                houses[hs_name]['wh_diameter'] = float(wh_diameter)
                houses[hs_name]['wh_model'] = wh_model
                houses[hs_name]['wh_scalar'] = float(wh_scalar)
                houses[hs_name]['wh_schedule_name'] = wh_schedule_name

                if wh_model == 'MULTILAYER':
                    wh_tmix = glm.waterheater.instances[wh_name]["T_mixing_valve"]
                    wh_setpoint = float(glm.waterheater.instances[wh_name]["lower_tank_setpoint"])

                    houses[hs_name]['wh_tmix'] = float(wh_tmix)
                    houses[hs_name]['wh_mlayer'] = True
                    houses[hs_name]['wh_setpoint'] = float(wh_setpoint)
                else:
                    wh_setpoint = float(glm.waterheater.instances[wh_name]["tank_setpoint"])
                    houses[hs_name]['wh_setpoint'] = float(wh_setpoint)
            except KeyError:
                # If the house doesn't have an electric water heater
                pass

            # For commercial buildings
            lights = hs_name.replace(hs_name, f'{hs_name}_lights')
            plugs = hs_name.replace(hs_name, f'{hs_name}_plug_loads')
            whs = hs_name.replace(hs_name, f'{hs_name}_gas_waterheater')
            ext_lights = hs_name.replace(hs_name, f'{hs_name}_exterior_lights')
            occ = hs_name.replace(hs_name, f'{hs_name}_occupancy')
            off_lights = hs_name.replace(hs_name, f'{hs_name}_office_lights')

            names = {lights, plugs, whs, ext_lights, occ, off_lights}
            strings = {'lights', 'plug_loads', 'gas_waterheater', 'exterior_lights', 'occupancy', 'office_lights'}
            for zip_name in names:
                scalar = {}
                hf = {}
                pf = {}
                p_pf = {}
                try:
                    zip_skew = glm.ZIPload.instances[zip_name]['schedule_skew']
                    hf[zip_name] = glm.ZIPload.instances[zip_name]['heatgain_fraction']
                    pf[zip_name] = glm.ZIPload.instances[zip_name]['power_fraction']
                    p_pf[zip_name] = glm.ZIPload.instances[zip_name]['power_pf']
                    if "*" in glm.ZIPload.instances[zip_name]['base_power']:
                        # if base power is set via schedule, extract just the numeric part after the "*"
                        zip_scalar = glm.ZIPload.instances[zip_name]['base_power'].split("*")[-1].strip()
                        scalar[zip_name] = zip_scalar
                        zip_schedule = glm.ZIPload.instances[zip_name]['base_power'].split("*")[0].strip()
                    else:
                        scalar[zip_name] = glm.ZIPload.instances[zip_name]['base_power']
                except KeyError:
                     # Not every building will have all six ZIPLoad types
                     pass

                try:
                    # Zipload parameters in house dictionary are named based on the schedule they use
                    houses[hs_name]["zip_heatgain_fraction"][zip_schedule] = float(hf[zip_name])
                    houses[hs_name]["zip_scalar"][zip_schedule] = float(scalar[zip_name])
                    houses[hs_name]["zip_power_fraction"][zip_schedule] = float(pf[zip_name])
                    houses[hs_name]["zip_power_pf"][zip_schedule] = float(p_pf[zip_name])
                except KeyError:
                #     # Not every building will have all six ZIPLoad types
                    pass

                # To assign zipload parameters in house dictionary to the name of the zipload types
                # for string in strings:
                #     if string in zip_name:
                #         try:
                #             houses[hs_name]["zip_heatgain_fraction"][zip_schedule] = float(hf[zip_name])
                #             houses[hs_name]["zip_scalar"][zip_schedule] = float(scalar[zip_name])
                #             houses[hs_name]["zip_power_fraction"][zip_schedule] = float(pf[zip_name])
                #             houses[hs_name]["zip_power_pf"][zip_schedule] = float(p_pf[zip_name])
                #         except KeyError:
                #             # Not every building will have all six ZIPLoad types
                #             pass

            #billingmeters[glm.meter.instances[house['parent']]['children']].append(hs_name)

            billingmeters[house['parent']]['children'].append(hs_name)


        # else:
        #     tariff_class = 'industrial'
        #     number_of_doors = house["number_of_doors"]
        #     number_of_stories = ''
        #     ceiling_height = ''
        #     window_exterior_transmission_coefficient = ''

    for cp_name, capacitors in glm.capacitor.items():
        capacitors[cp_name] = {'feeder_id': feed_key}

    for rg_name, regulators in glm.regulator.items():
        regulators[rg_name] = {'feeder_id': feed_key}

    for bt_name, battery in glm.battery.items():
        try:
            inverters[glm.battery.instances[bt_name]['parent']] = {'feeder_id': feed_key,
                            'billingmeter_id': glm.triplex_meter.instances[glm.inverter.instances[glm.battery.instances[bt_name]['parent']]['parent']]['parent'],
                            'rated_W': float(glm.inverter.instances[glm.battery.instances[bt_name]['parent']]["rated_power"]),
                            'resource': 'battery',
                            'inv_eta': float(glm.inverter.instances[glm.battery.instances[bt_name]['parent']]["inverter_efficiency"]),
                            'bat_eta': float(battery['round_trip_efficiency']),
                            'bat_capacity': float(battery['battery_capacity']),
                            'bat_soc': float(battery['state_of_charge'])}
            if billingmeters[glm.triplex_meter.instances[glm.inverter.instances[glm.battery.instances[bt_name]['parent']]['parent']]['parent']]:
                billingmeters[glm.triplex_meter.instances[glm.inverter.instances[glm.battery.instances[bt_name]['parent']]['parent']]['parent']]['children'].append(glm.battery.instances[bt_name]['parent'])
        except KeyError:
            inverters[glm.battery.instances[bt_name]['parent']] = {'feeder_id': feed_key,
                            'billingmeter_id': glm.meter.instances[glm.inverter.instances[glm.battery.instances[bt_name]['parent']]['parent']]['parent'],
                            'rated_W': float(glm.inverter.instances[glm.battery.instances[bt_name]['parent']]["rated_power"]),
                            'resource': 'battery',
                            'inv_eta': float(glm.inverter.instances[glm.battery.instances[bt_name]['parent']]["inverter_efficiency"]),
                            'bat_eta': float(battery['round_trip_efficiency']),
                            'bat_capacity': float(battery['battery_capacity']),
                            'bat_soc': float(battery['state_of_charge'])}
            if billingmeters[glm.meter.instances[glm.inverter.instances[glm.battery.instances[bt_name]['parent']]['parent']]['parent']]:
                billingmeters[glm.meter.instances[glm.inverter.instances[glm.battery.instances[bt_name]['parent']]['parent']]['parent']]['children'].append(glm.battery.instances[bt_name]['parent'])

    for inv_name, inverter in glm.inverter.items():
        if 'sol' in inv_name:
            try:
                inverters[inv_name] = {'feeder_id': feed_key,
                                'billingmeter_id': glm.triplex_meter.instances[inverter['parent']]['parent'],
                                'rated_W': float(inverter["rated_power"]),
                                'resource': 'solar',
                                'inv_eta': float(inverter["inverter_efficiency"])}
                if billingmeters[glm.triplex_meter.instances[inverter['parent']]['parent']]:
                    billingmeters[glm.triplex_meter.instances[inverter['parent']]['parent']]['children'].append(inv_name)
            except KeyError:
                inverters[inv_name] = {'feeder_id': feed_key,
                                'billingmeter_id': glm.meter.instances[inverter['parent']]['parent'],
                                'rated_W': float(inverter["rated_power"]),
                                'resource': 'solar',
                                'inv_eta': float(inverter["inverter_efficiency"])}
                if billingmeters[glm.meter.instances[inverter['parent']]['parent']]:
                    billingmeters[glm.meter.instances[inverter['parent']]['parent']]['children'].append(inv_name)

    for ev_name, evcharger_det in glm.evcharger_det.items():
        try:
            ev[ev_name] = {'name': ev_name,
                        'feeder_id': feed_key,
                        'billingmeter_id': glm.triplex_meter.instances[glm.house.instances[evcharger_det['parent']]['parent']]['parent'],
                        'parent': evcharger_det["parent"],
                        'work_charging': evcharger_det["work_charging_available"],
                        'battery_SOC': float(evcharger_det["battery_SOC"]),
                        'max_charge': float(evcharger_det["maximum_charge_rate"]),
                        'daily_miles': float(evcharger_det["travel_distance"]),
                        'arrival_work': float(evcharger_det["arrival_at_work"]),
                        'arrival_home': float(evcharger_det["arrival_at_home"]),
                        'work_duration': float(evcharger_det["duration_at_work"]),
                        'home_duration': float(evcharger_det["duration_at_home"]),
                        'miles_per_kWh': float(evcharger_det["mileage_efficiency"]),
                        'range_miles': float(evcharger_det["mileage_classification"]),
                        'efficiency': float(evcharger_det["charging_efficiency"])}
            if billingmeters[glm.triplex_meter.instances[glm.house.instances[evcharger_det['parent']]['parent']]['parent']]:
                billingmeters[glm.triplex_meter.instances[glm.house.instances[evcharger_det['parent']]['parent']]['parent']]['children'].append(ev_name)
        except KeyError:
            ev[ev_name] = {'name': ev_name,
                        'feeder_id': feed_key,
                        'billingmeter_id': glm.house.instances[evcharger_det['parent']]['parent'],
                        'parent': evcharger_det["parent"],
                        'work_charging': evcharger_det["work_charging_available"],
                        'battery_SOC': float(evcharger_det["battery_SOC"]),
                        'max_charge': float(evcharger_det["maximum_charge_rate"]),
                        'daily_miles': float(evcharger_det["travel_distance"]),
                        'arrival_work': float(evcharger_det["arrival_at_work"]),
                        'arrival_home': float(evcharger_det["arrival_at_home"]),
                        'work_duration': float(evcharger_det["duration_at_work"]),
                        'home_duration': float(evcharger_det["duration_at_home"]),
                        'miles_per_kWh': float(evcharger_det["mileage_efficiency"]),
                        'range_miles': float(evcharger_det["mileage_classification"]),
                        'efficiency': float(evcharger_det["charging_efficiency"])}
            if billingmeters[glm.house.instances[evcharger_det['parent']]['parent']]:
                billingmeters[glm.house.instances[evcharger_det['parent']]['parent']]['children'].append(ev_name)

    feeders[feed_key] = {'house_count': len(houses), 'inverter_count': len(inverters), 'ev_count': len(ev)}

    try:
        for name, helics_msg in glm.helics_msg.items():
            message_name = name
    except KeyError:
        pass
    try:
        for name, fncs_msg in glm.fncs_msg.items():
            message_name = name
    except KeyError:
        pass

    for sub_name, substations in glm.substation.items():
        substation = {'bulkpower_bus': 1,
                    'message_name': message_name,
                    'transformer_MVA': float(substations["base_power"].strip('MVA')) * 1.0e-6,
                    'base_feeder': substations["groupid"],
                    'feeders': feeders,
                    'billingmeters': billingmeters,
                    'houses': houses,
                    'inverters': inverters,
                    'ev': ev,
                    'capacitors': capacitors,
                    'regulators': regulators,
                    'climate': weather}

    op = open(case_name + '/' + feed_key + '/' + feed_key + '_glm_dict.json', 'w')
    json.dump(substation, op, ensure_ascii=False, indent=2)
    op.close()

if __name__ == "__main__":
    glm_dict("Test")
