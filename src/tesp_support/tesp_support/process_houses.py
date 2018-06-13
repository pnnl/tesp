#	Copyright (C) 2017-2018 Battelle Memorial Institute
# file: process_houses.py; focus on HVAC
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def process_houses(nameroot, dictname = ''):
	# first, read and print a dictionary of all the monitored GridLAB-D objects
	if len (dictname) > 0:
			lp = open (dictname).read()
	else:
			lp = open (nameroot + "_glm_dict.json").read()
	dict = json.loads(lp)
	sub_keys = list(dict['feeders'].keys())
	sub_keys.sort()
	inv_keys = list(dict['inverters'].keys())
	inv_keys.sort()
	hse_keys = list(dict['houses'].keys())
	hse_keys.sort()
	mtr_keys = list(dict['billingmeters'].keys())
	mtr_keys.sort()
	xfMVA = dict['transformer_MVA']
	matBus = dict['matpower_id']
	print ("\n\nFile", nameroot, "has substation", sub_keys[0], "at Matpower bus", matBus, "with", xfMVA, "MVA transformer")
	print("\nFeeder Dictionary:")
	for key in sub_keys:
		row = dict['feeders'][key]
	#	print (key, "has", row['house_count'], "houses and", row['inverter_count'], "inverters")
	print("\nBilling Meter Dictionary:")
	for key in mtr_keys:
		row = dict['billingmeters'][key]
	#	print (key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])
	print("\nHouse Dictionary:")
	for key in hse_keys:
		row = dict['houses'][key]
	#	print (key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'], "heating", row['wh_gallons'], "gal WH")
		# row['feeder_id'] is also available
	print("\nInverter Dictionary:")
	for key in inv_keys:
		row = dict['inverters'][key]
	#	print (key, "on", row['billingmeter_id'], "has", row['rated_W'], "W", row['resource'], "resource")
		# row['feeder_id'] is also available

	# parse the substation metrics file first; there should just be one entity per time sample
	# each metrics file should have matching time points
	lp_s = open ("substation_" + nameroot + "_metrics.json").read()
	lst_s = json.loads(lp_s)
	print ("\nMetrics data starting", lst_s['StartTime'])

	# make a sorted list of the sample times in hours
	lst_s.pop('StartTime')
	meta_s = lst_s.pop('Metadata')
	times = list(map(int,list(lst_s.keys())))
	times.sort()
	print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
	hrs = np.array(times, dtype=np.float)
	denom = 3600.0
	hrs /= denom

	time_key = str(times[0])

	# read the other JSON files; their times (hrs) should be the same
	lp_h = open ("house_" + nameroot + "_metrics.json").read()
	lst_h = json.loads(lp_h)

	# Houses 
	lst_h.pop('StartTime')
	meta_h = lst_h.pop('Metadata')
	print("\nHouse Metadata for", len(lst_h[time_key]), "objects")
	for key, val in meta_h.items():
	#	print (key, val['index'], val['units'])
		if key == 'air_temperature_avg':
			AIR_AVG_IDX = val['index']
		elif key == 'air_temperature_min':
			AIR_MIN_IDX = val['index']
		elif key == 'air_temperature_max':
			AIR_MAX_IDX = val['index']
		elif key == 'hvac_load_avg':
			HVAC_AVG_IDX = val['index']
		elif key == 'hvac_load_min':
			HVAC_MIN_IDX = val['index']
		elif key == 'hvac_load_max':
			HVAC_MAX_IDX = val['index']
		elif key == 'waterheater_load_avg':
			WH_AVG_IDX = val['index']
		elif key == 'waterheater_load_min':
			WH_MIN_IDX = val['index']
		elif key == 'waterheater_load_max':
			WH_MAX_IDX = val['index']
		elif key == 'total_load_avg':
			TOTAL_AVG_IDX = val['index']
		elif key == 'total_load_min':
			TOTAL_MIN_IDX = val['index']
		elif key == 'total_load_max':
			TOTAL_MAX_IDX = val['index']
		elif key == 'air_temperature_deviation_cooling':
			DEV_COOL_IDX = val['index']
		elif key == 'air_temperature_deviation_heating':
			DEV_HEAT_IDX = val['index']

	data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
	print ("\nConstructed", data_h.shape, "NumPy array for Houses")
	j = 0
	for key in hse_keys:
		i = 0
		for t in times:
			ary = lst_h[str(t)][hse_keys[j]]
			data_h[j, i,:] = ary
			i = i + 1
		j = j + 1

	# display a plot
	fig, ax = plt.subplots(2, 1, sharex = 'col')
	i = 0
	for key in hse_keys:
		ax[0].plot(hrs, data_h[i,:,AIR_AVG_IDX], color="blue")
		ax[1].plot(hrs, data_h[i,:,HVAC_AVG_IDX], color="red")
		i = i + 1
	ax[0].set_ylabel("Degrees")
	ax[1].set_ylabel("kW")
	ax[1].set_xlabel("Hours")
	ax[0].set_title ("HVAC at all Houses")

	plt.show()


