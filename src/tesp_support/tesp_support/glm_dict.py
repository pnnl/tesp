#	Copyright (C) 2017-2019 Battelle Memorial Institute
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

import json;
import sys;

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

def glm_dict (nameroot, ercot=False, te30=False):
	""" Writes the JSON metadata file from a GLM file

	This function reads *nameroot.glm* and writes *nameroot_glm_dict.json* 
	The GLM file should have some meters and triplex_meters with the
	bill_mode attribute defined, which identifies them as billing meters
	that parent houses and inverters. If this is not the case, ERCOT naming
	rules can be applied to identify billing meters.

	Args:
	    nameroot (str): path and file name of the GLM file, without the extension
	    ercot (boolean): request ERCOT billing meter naming. Defaults to false.
	    te30 (boolean): request hierarchical meter handling in the 30-house test harness. Defaults to false.
	"""
	ip = open (nameroot + '.glm', 'r')
	op = open (nameroot + '_glm_dict.json', 'w')

	FNCSmsgName = ''
	feeder_id = 'feeder'
	name = ''
	bulkpowerBus = 'TBD'
	substationTransformerMVA = 12
	houses = {}
	waterheaters = {}
	billingmeters = {}
	inverters = {}
	feeders = {}
	capacitors = {}
	regulators = {}

	inSwing = False
	for line in ip:
		lst = line.split()
		if len(lst) > 1:
			if lst[1] == 'substation':
				inSwing = True
			if inSwing == True:
				if lst[0] == 'name':
					feeder_id = lst[1].strip(';')
				if lst[0] == 'base_power':
					substationTransformerMVA = float(lst[1].strip(' ').strip('MVA;')) * 1.0
					inSwing = False

	ip.seek(0,0)
	inHouses = False
	inWaterHeaters = False
	inTriplexMeters = False
	inMeters = False
	inInverters = False
	inCapacitors = False
	inRegulators = False
	inFNCSmsg = False
	for line in ip:
		lst = line.split()
		if len(lst) > 1:
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
			if inFNCSmsg == True:
				if lst[0] == 'name':
					FNCSmsgName = lst[1].strip(';')
					inFNCSmsg = False
			if lst[1] == 'triplex_meter':
				inTriplexMeters = True
				phases = ''
			if lst[1] == 'meter':
				inMeters = True
				phases = 'ABC'
			if lst[1] == 'inverter':
				inInverters = True
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
				gallons = 0.0
			if inCapacitors == True:
				if lst[0] == 'name':
					lastCapacitor = lst[1].strip(';')
					capacitors[lastCapacitor] = {'feeder_id':feeder_id}
					inCapacitors = False;
			if inRegulators == True:
				if lst[0] == 'name':
					lastRegulator = lst[1].strip(';')
					regulators[lastRegulator] = {'feeder_id':feeder_id}
					inRegulators = False;
			if inInverters == True:
				if lst[0] == 'name':
					lastInverter = lst[1].strip(';')
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
				if lst[1] == 'solar':
					if ercot:
						lastBillingMeter = ercotMeterName (name)
					elif te30:
						lastBillingMeter = lastMeterParent
					inverters[lastInverter] = {'feeder_id':feeder_id,'billingmeter_id':lastBillingMeter,'rated_W':rating,'resource':'solar','inv_eta':inv_eta}
					inInverters = False
				if lst[1] == 'SUPPLY_DRIVEN;':
					if ercot:
						lastBillingMeter = ercotMeterName (name)
					elif te30:
						lastBillingMeter = lastMeterParent
					inverters[lastInverter] = {'feeder_id':feeder_id,'billingmeter_id':lastBillingMeter,'rated_W':rating,'resource':'battery','inv_eta':inv_eta,
						'bat_eta':bat_eta,'bat_capacity':capacity,'bat_soc':soc}
					inInverters = False
			if inHouses == True:
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
				if lst[0] == 'thermal_integrity_level':
					thermal_integrity = lst[1].strip(';')
				if (lst[0] == 'cooling_setpoint') or (lst[0] == 'heating_setpoint'):
					if ercot:
						lastBillingMeter = ercotMeterName (name)
					houses[name] = {'feeder_id':feeder_id,'billingmeter_id':lastBillingMeter,'sqft':sqft,'stories':stories,'doors':doors,
						'thermal_integrity':thermal_integrity,'cooling':cooling,'heating':heating,'wh_gallons':0}
					lastHouse = name
					inHouses = False
			if inWaterHeaters == True:
				if lst[0] == 'tank_volume':
					gallons = float(lst[1].strip(' ').strip(';')) * 1.0
					waterheaters[lastHouse] = gallons
					inWaterHeaters = False
			if inTriplexMeters == True:
				if lst[0] == 'name':
					name = lst[1].strip(';')
				if lst[0] == 'phases':
					phases = lst[1].strip(';')
				if lst[0] == 'parent':
					lastMeterParent = lst[1].strip(';')
				if lst[0] == 'bill_mode':
					if te30 == True:
						if 'flatrate' not in name:
							billingmeters[name] = {'feeder_id':feeder_id,'phases':phases, 'children':[]}
							lastBillingMeter = name
					else:
						billingmeters[name] = {'feeder_id':feeder_id,'phases':phases, 'children':[]}
						lastBillingMeter = name
					inTriplexMeters = False
			if inMeters == True:
				if lst[0] == 'name':
					name = lst[1].strip(';')
				if lst[0] == 'phases':
					phases = lst[1].strip(';')
				if lst[0] == 'parent':
					lastMeterParent = lst[1].strip(';')
				if lst[0] == 'bill_mode':
					billingmeters[name] = {'feeder_id':feeder_id,'phases':phases, 'children':[]}
					lastBillingMeter = name
					inMeters = False
		elif len(lst) == 1:
			inHouses = False
			inWaterHeaters = False
			inTriplexMeters = False
			inMeters = False
			inInverters = False
			inCapacitors = False
			inRegulators = False
			inFNCSmsg = False

	for key, val in houses.items():
		if key in waterheaters:
			val['wh_gallons'] = waterheaters[key]
		mtr = billingmeters[val['billingmeter_id']]
		mtr['children'].append(key)

	for key, val in inverters.items():
		mtr = billingmeters[val['billingmeter_id']]
		mtr['children'].append(key)

	feeders[feeder_id] = {'house_count': len(houses),'inverter_count': len(inverters)}
	substation = {'bulkpower_bus':bulkpowerBus,'FNCS':FNCSmsgName,
		'transformer_MVA':substationTransformerMVA,'feeders':feeders, 
		'billingmeters':billingmeters,'houses':houses,'inverters':inverters,
		'capacitors':capacitors,'regulators':regulators}
	print (json.dumps(substation), file=op)

	ip.close()
	op.close()
