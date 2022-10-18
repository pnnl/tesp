# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: glm_dict_dsot.py
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
    """ Writes the JSON metadata file from a GLM file

    This function reads *name_root.glm* and writes *[name_root]_glm_dict.json*
    The GLM file should have some meters and triplex_meters with the
    bill_mode attribute defined, which identifies them as billing meters
    that parent houses and inverters. If this is not the case, ERCOT naming
    rules can be applied to identify billing meters.

    Args:
        name_root (str): path and file name of the GLM file, without the extension
        config (dict):
        ercot (boolean): request ERCOT billing meter naming. Defaults to false. --- THIS NEEDS TO LEAVE THIS PLACE
        te30 (boolean): request hierarchical meter handling in the 30-house test harness. Defaults to false. --- THIS NEEDS TO LEAVE THIS PLACE
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
                                     'miles_per_kwh': ev_mileage,
                                     'range_miles': ev_range,
                                     'efficiency': ev_charg_eff}
            if inHouses:
                if lst[0] == 'name':
                    name = lst[1].strip(';')
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
                    houses[name] = {'feeder_id': feeder_id, 'billingmeter_id': lastBillingMeter, 'sqft': sqft,
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
            #	print('I got a KeyError. Reason - {0}. See: {1}'.format(str(keyErr), format_exc())) # sys.exc_info()[2].tb_)
            pass
        # except:
        #	print('Cannot find id {0} from {1} in the list of billing meters.'.format(val['billingmeter_id'], key))
        #	print('System returned error code: {0}.'.format(sys.exc_info()[0]))
        #	pass

    for key, val in inverters.items():
        mtr = billingmeters[val['billingmeter_id']]
        mtr['children'].append(key)
    for key, val in ev.items():
        mtr = billingmeters[val['billingmeter_id']]
        mtr['children'].append(key)

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


if __name__ == "__main__":
    glm_dict("Test")
