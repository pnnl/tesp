#	Copyright (C) 2017-2018 Battelle Memorial Institute
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def process_voltages(nameroot, dictname = ''):
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

	# read the other JSON files; their times (hrs) should be the same
	lp_m = open ("billing_meter_" + nameroot + "_metrics.json").read()
	lst_m = json.loads(lp_m)

	# Billing Meters 
	lst_m.pop('StartTime')
	meta_m = lst_m.pop('Metadata')
	print("\nBilling Meter Metadata for", len(lst_m['3600']), "objects")
	for key, val in meta_m.items():
	#	print (key, val['index'], val['units'])
		if key == 'voltage_max':
			MTR_VOLT_MAX_IDX = val['index']
			MTR_VOLT_MAX_UNITS = val['units']
		elif key == 'voltage_min':
			MTR_VOLT_MIN_IDX = val['index']
			MTR_VOLT_MIN_UNITS = val['units']
		elif key == 'voltage_avg':
			MTR_VOLT_AVG_IDX = val['index']
			MTR_VOLT_AVG_UNITS = val['units']
		elif key == 'voltage12_max':
			MTR_VOLT12_MAX_IDX = val['index']
			MTR_VOLT12_MAX_UNITS = val['units']
		elif key == 'voltage12_min':
			MTR_VOLT12_MIN_IDX = val['index']
			MTR_VOLT12_MIN_UNITS = val['units']
		elif key == 'voltage_unbalance_max':
			MTR_VOLTUNB_MAX_IDX = val['index']
			MTR_VOLTUNB_MAX_UNITS = val['units']

	data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m['3600'][mtr_keys[0]])), dtype=np.float)
	print ("\nConstructed", data_m.shape, "NumPy array for Meters")
	j = 0
	for key in mtr_keys:
		i = 0
		for t in times:
			ary = lst_m[str(t)][mtr_keys[j]]
			data_m[j, i,:] = ary
			i = i + 1
		j = j + 1

	# display a plot
	fig, ax = plt.subplots(2, 1, sharex = 'col')
	i = 0
	for key in mtr_keys:
		ax[0].plot(hrs, data_m[i,:,MTR_VOLT_MIN_IDX], color="blue")
		ax[1].plot(hrs, data_m[i,:,MTR_VOLT_MAX_IDX], color="red")
		i = i + 1
	ax[0].set_ylabel("Min Volts")
	ax[1].set_ylabel("Max Volts")
	ax[1].set_xlabel("Hours")
	ax[0].set_title ("Voltage at all Meters")

	plt.show()


