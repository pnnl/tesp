# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: glm_dict.py
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
from math import sqrt

from .helpers import zoneMeterName


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


def isCommercialHouse(house_class):
    if ('BIGBOX' in house_class) or ('OFFICE' in house_class) or ('STRIPMALL' in house_class):
        return True
    return False


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


def glm_dict(name_root, ercot=False, te30=False):
    """ Writes the JSON metadata file from a GLM file

    This function reads *name_root.glm* and writes *[name_root]_glm_dict.json*
    The GLM file should have some meters and triplex_meters with the
    bill_mode attribute defined, which identifies them as billing meters
    that parent houses and inverters. If this is not the case, ERCOT naming
    rules can be applied to identify billing meters.

    Args:
        name_root (str): path and file name of the GLM file, without the extension
        ercot (boolean): request ERCOT billing meter naming. Defaults to false.
        te30 (boolean): request hierarchical meter handling in the 30-house test harness. Defaults to false.
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
    gld_federate = 'gld_1'
    bulkpowerBus = 'TBD'
    name = ''
    houses = {}
    waterheaters = {}
    billingmeters = {}
    inverters = {}
    feeders = {}
    capacitors = {}
    regulators = {}
    loads = {}
    inHouses = False
    inWaterHeaters = False
    inTriplexMeters = False
    inMeters = False
    inInverters = False
    hasBattery = False
    hasSolar = False
    inCapacitors = False
    inRegulators = False
    inLoads = False
    inFNCSmsg = False
    inHELICSmsg = False
    for line in collected_lines:
        lst = line.split()
        if len(lst) > 1:  # terminates with a } or };
            if lst[1] == 'helics_msg':
                inHELICSmsg = True
            if lst[1] == 'fncs_msg':
                inFNCSmsg = True
            if lst[1] == 'house':
                inHouses = True
                parent = ''
                sqft = 2500.0
                cooling = 'NONE'
                heating = 'NONE'
                stories = 1
                thermal_integrity = 'UNKNOWN'
                doors = 4
                house_class = 'SINGLE_FAMILY'
            if inHELICSmsg:
                if lst[0] == 'name':
                    gld_federate = lst[1].strip(';')
                    inHELICSmsg = False
            if inFNCSmsg:
                if lst[0] == 'name':
                    gld_federate = lst[1].strip(';')
                    inFNCSmsg = False
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
            if lst[1] == 'load':
                inLoads = True
                parent = ''
            if inLoads:
                if lst[0] == 'name':
                    name = lst[1].strip(';')
                if lst[0] == 'parent':
                    parent = lst[1].strip(';')
                    loads[name] = {'parent': parent}
                    inLoads = False
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
                elif lst[1] == 'battery':
                    hasSolar = False
                    hasBattery = True
                if lst[0] == 'rated_power':
                    rating = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'inverter_efficiency':
                    inv_eta = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'round_trip_efficiency':
                    bat_eta = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'state_of_charge':
                    soc = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'battery_capacity':
                    capacity = float(lst[1].strip(' ').strip(';')) * 1.0
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
                if (lst[0] == 'cooling_setpoint') or (lst[0] == 'heating_setpoint'):
                    if ercot:
                        lastBillingMeter = ercotMeterName(name)
                    elif isCommercialHouse(house_class):
                        lastBillingMeter = zoneMeterName(parent)
                    houses[name] = {'feeder_id': feeder_id, 'billingmeter_id': lastBillingMeter, 'sqft': sqft,
                                    'stories': stories, 'doors': doors,
                                    'thermal_integrity': thermal_integrity, 'cooling': cooling, 'heating': heating,
                                    'wh_gallons': 0, 'house_class': house_class,
                                    'parent': parent}
                    lastHouse = name
                    inHouses = False
            if inWaterHeaters:
                if lst[0] == 'name':  # non-controlled WH won't have a name
                    whname = lst[1].strip(' ').strip(';')
                    waterheaters[lastHouse] = {'name': whname, 'gallons': 0.0, 'tmix': 0.0, 'mlayer': False}
                if lst[0] == 'tank_volume':
                    wh_gallons = float(lst[1].strip(' ').strip(';')) * 1.0
                    if lastHouse in waterheaters:
                        waterheaters[lastHouse]['gallons'] = wh_gallons
                    else:
                        waterheaters[lastHouse] = {'name': '', 'gallons': wh_gallons, 'tmix': 0.0, 'mlayer': False}
                if lst[0] == 'T_mixing_valve':
                    waterheaters[lastHouse]['tmix'] = float(lst[1].strip(' ').strip(';')) * 1.0
                if lst[0] == 'waterheater_model':
                    if 'MULTILAYER' == lst[1].strip(' ').strip(';'):
                        waterheaters[lastHouse]['mlayer'] = True
            if inTriplexMeters:
                if lst[0] == 'name':
                    name = lst[1].strip(';')
                if lst[0] == 'phases':
                    phases = lst[1].strip(';')
                if lst[0] == 'parent':
                    lastMeterParent = lst[1].strip(';')
                if lst[0] == 'bill_mode':
                    if te30:
                        if 'flatrate' not in name:
                            billingmeters[name] = {'feeder_id': feeder_id, 'phases': phases, 'vll': vll, 'vln': vln, 'children': []}
                            lastBillingMeter = name
                    else:
                        billingmeters[name] = {'feeder_id': feeder_id, 'phases': phases, 'vll': vll, 'vln': vln, 'children': []}
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
                    vll = vln * sqrt(3.0)
                if lst[0] == 'bill_mode':
                    billingmeters[name] = {'feeder_id': feeder_id, 'phases': phases, 'vll': vll, 'vln': vln,
                                           'children': []}
                    lastBillingMeter = name
                    inMeters = False
        elif len(lst) == 1:
            if hasSolar:
                if ercot:
                    lastBillingMeter = ercotMeterName(name)
                elif te30:
                    lastBillingMeter = lastMeterParent
                inverters[lastInverter] = {'feeder_id': feeder_id,
                                           'billingmeter_id': lastBillingMeter,
                                           'rated_W': rating,
                                           'resource': 'solar',
                                           'inv_eta': inv_eta}
            elif hasBattery:
                if ercot:
                    lastBillingMeter = ercotMeterName(name)
                elif te30:
                    lastBillingMeter = lastMeterParent
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
            inTriplexMeters = False
            inMeters = False
            inInverters = False
            inCapacitors = False
            inRegulators = False
            inFNCSmsg = False
            inHELICSmsg = False

    for key, val in houses.items():
        if key in waterheaters:
            val['wh_name'] = waterheaters[key]['name']
            val['wh_gallons'] = waterheaters[key]['gallons']
            val['wh_tmix'] = waterheaters[key]['tmix']
            val['wh_mlayer'] = waterheaters[key]['mlayer']
        if ercot and isCommercialHouse(val['house_class']):
            parent = val['parent']
            val['billingmeter_id'] = loads[parent]['parent']
        mtr = billingmeters[val['billingmeter_id']]
        mtr['children'].append(key)

    for key, val in inverters.items():
        mtr = billingmeters[val['billingmeter_id']]
        mtr['children'].append(key)

    feeders[feeder_id] = {'house_count': len(houses), 'inverter_count': len(inverters), 'base_feeder': base_feeder}
    substation = {'bulkpower_bus': bulkpowerBus, 'FedName': gld_federate,
                  'transformer_MVA': substationTransformerMVA, 'feeders': feeders,
                  'billingmeters': billingmeters, 'houses': houses, 'inverters': inverters,
                  'capacitors': capacitors, 'regulators': regulators}
    op = open(name_root + '_glm_dict.json', 'w')
    json.dump(substation, op, ensure_ascii=False, indent=2)
    op.close()


if __name__ == "__main__":
    glm_dict("Test")
