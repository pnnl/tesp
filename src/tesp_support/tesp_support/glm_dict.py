#	Copyright (C) 2017 Battelle Memorial Institute
# file: glm_dict.py
# tuned to feederGenerator_TSP.m for sequencing of objects and attributes
import json;
import sys;

def glm_dict (nameroot):
	ip = open (nameroot + ".glm", "r")
	op = open (nameroot + "_glm_dict.json", "w")

	feeder_id = "feeder"
	name = ""
	parent = ""
	sqft = ""
	cooling = ""
	heating = ""
	gallons = ""
	phases = ""
	rating = ""
	matpowerBus = "TBD"
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
			if lst[1] == "substation":
				inSwing = True
			if inSwing == True:
				if lst[0] == "name":
					feeder_id = lst[1].strip(";")
				if lst[0] == "base_power":
					substationTransformerMVA = float(lst[1].strip(" ").strip("MVA;")) * 1.0
					inSwing = False

	ip.seek(0,0)
	inHouses = False
	inWaterHeaters = False
	inTriplexMeters = False
	inMeters = False
	inInverters = False
	inCapacitors = False
	inRegulators = False
	for line in ip:
		lst = line.split()
		if len(lst) > 1:
			if lst[1] == "house":
				inHouses = True
			if lst[1] == "triplex_meter":
				inTriplexMeters = True
			if lst[1] == "meter":
				inMeters = True
				phases = "ABC"
			if lst[1] == "inverter":
				inInverters = True
			if lst[1] == "capacitor":
				inCapacitors = True
			if lst[1] == "regulator":
				inRegulators = True
			if lst[1] == "waterheater":
				inWaterHeaters = True
			if inCapacitors == True:
				if lst[0] == "name":
					lastCapacitor = lst[1].strip(";")
					capacitors[lastCapacitor] = {'feeder_id':feeder_id}
					inCapacitors = False;
			if inRegulators == True:
				if lst[0] == "name":
					lastRegulator = lst[1].strip(";")
					regulators[lastRegulator] = {'feeder_id':feeder_id}
					inRegulators = False;
			if inInverters == True:
				if lst[0] == "name":
					lastInverter = lst[1].strip(";")
				if lst[0] == "rated_power":
					rating = float(lst[1].strip(" ").strip(";")) * 1.0
				if lst[1] == "solar":
					inverters[lastInverter] = {'feeder_id':feeder_id,'billingmeter_id':lastBillingMeter,'rated_W':rating,'resource':'solar'}
					inInverters = False
				if lst[1] == "battery":
					inverters[lastInverter] = {'feeder_id':feeder_id,'billingmeter_id':lastBillingMeter,'rated_W':rating,'resource':'battery'}
					inInverters = False
			if inHouses == True:
				if lst[0] == "name":
					name = lst[1].strip(";")
				if lst[0] == "parent":
					parent = lst[1].strip(";")
				if lst[0] == "floor_area":
					sqft = float(lst[1].strip(" ").strip(";")) * 1.0
				if lst[0] == "cooling_system_type":
					cooling = lst[1].strip(";")
				if lst[0] == "heating_system_type":
					heating = lst[1].strip(";")
				if (lst[0] == "cooling_setpoint") or (lst[0] == "heating_setpoint"):
					houses[name] = {'feeder_id':feeder_id,'billingmeter_id':lastBillingMeter,'sqft':sqft,'cooling':cooling,'heating':heating,'wh_gallons':0}
					lastHouse = name
					inHouses = False
			if inWaterHeaters == True:
				if lst[0] == "tank_volume":
					gallons = float(lst[1].strip(" ").strip(";")) * 1.0
					waterheaters[lastHouse] = gallons
					inWaterHeaters = False
			if inTriplexMeters == True:
				if lst[0] == "name":
					name = lst[1].strip(";")
				if lst[0] == "phases":
					phases = lst[1].strip(";")
				if lst[0] == "parent":
					lastMeterParent = lst[1].strip(";")
				if lst[0] == "bill_mode":
					if "flatrate" not in name:
						billingmeters[name] = {'feeder_id':feeder_id,'phases':phases, 'children':[]}
						lastBillingMeter = name
					inTriplexMeters = False
			if inMeters == True:
				if lst[0] == "name":
					name = lst[1].strip(";")
				if lst[0] == "phases":
					phases = lst[1].strip(";")
				if lst[0] == "parent":
					lastMeterParent = lst[1].strip(";")
				if lst[0] == "bill_mode":
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

	for key, val in houses.items():
		if key in waterheaters:
			val['wh_gallons'] = waterheaters[key]
		mtr = billingmeters[val['billingmeter_id']]
		mtr['children'].append(key)

	for key, val in inverters.items():
		mtr = billingmeters[val['billingmeter_id']]
		mtr['children'].append(key)

	feeders[feeder_id] = {'house_count': len(houses),'inverter_count': len(inverters)}
	substation = {'matpower_id':matpowerBus,
		'transformer_MVA':substationTransformerMVA,'feeders':feeders, 
		'billingmeters':billingmeters,'houses':houses,'inverters':inverters,
		'capacitors':capacitors,'regulators':regulators}
	print (json.dumps(substation), file=op)

	ip.close()
	op.close()
