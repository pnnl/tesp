# file: process_gld.py
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def plot_loadshed (nameroot):
	# first, read and print a dictionary of all the monitored GridLAB-D objects
	lp = open (nameroot + '_dict.json').read()
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
		print (key, "has", row['house_count'], "houses and", row['inverter_count'], "inverters")
	print("\nBilling Meter Dictionary:")
	for key in mtr_keys:
		row = dict['billingmeters'][key]
		print (key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])
	print("\nHouse Dictionary:")
	for key in hse_keys:
		row = dict['houses'][key]
		print (key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'], "heating", row['wh_gallons'], "gal WH")
		# row['feeder_id'] is also available
	print("\nInverter Dictionary:")
	for key in inv_keys:
		row = dict['inverters'][key]
		print (key, "on", row['billingmeter_id'], "has", row['rated_W'], "W", row['resource'], "resource")
		# row['feeder_id'] is also available

	lp_m = open ("billing_meter_" + nameroot + "_metrics.json").read()
	lst_m = json.loads(lp_m)
	# Billing Meters - both primary and triplex
	lst_m.pop('StartTime')
	meta_m = lst_m.pop('Metadata')

	times = list(map(int,list(lst_m.keys())))
	times.sort()
	print ("There are", len (times), "sample times beginning with", times[1] - times[0], "second intervals")
	hrs = np.array(times, dtype=np.float)
	denom = 3600.0
	hrs /= denom

	t1 = str(times[0])

	print("\nBilling Meter Metadata for", len(lst_m[t1]), "objects")
	for key, val in meta_m.items():
		print (key, val['index'], val['units'])
		if key == 'voltage_max':
			MTR_VOLT_MAX_IDX = val['index']
			MTR_VOLT_MAX_UNITS = val['units']
		elif key == 'voltage_min':
			MTR_VOLT_MIN_IDX = val['index']
			MTR_VOLT_MIN_UNITS = val['units']
		elif key == 'voltage12_max':
			MTR_VOLT12_MAX_IDX = val['index']
			MTR_VOLT12_MAX_UNITS = val['units']
		elif key == 'voltage12_min':
			MTR_VOLT12_MIN_IDX = val['index']
			MTR_VOLT12_MIN_UNITS = val['units']
	data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[t1][mtr_keys[0]])), dtype=np.float)
	print ("\nConstructed", data_m.shape, "NumPy array for Meters")
	j = 0
	for key in mtr_keys:
		i = 0
		for t in times:
			ary = lst_m[str(t)][mtr_keys[j]]
			data_m[j, i,:] = ary
			i = i + 1
		j = j + 1

	# parse the substation metrics file
	lp_s = open ("substation_" + nameroot + "_metrics.json").read()
	lst_s = json.loads(lp_s)
	lst_s.pop('StartTime')
	meta_s = lst_s.pop('Metadata')
	print ("\nSubstation Metadata for", len(lst_s[t1]), "objects")
	for key, val in meta_s.items():
		print (key, val['index'], val['units'])
		if key == 'real_power_avg':
			SUB_POWER_IDX = val['index']
			SUB_POWER_UNITS = val['units']
		elif key == 'real_power_losses_avg':
			SUB_LOSSES_IDX = val['index']
			SUB_LOSSES_UNITS = val['units']
	data_s = np.empty(shape=(len(sub_keys), len(times), len(lst_s[t1][sub_keys[0]])), dtype=np.float)
	print ("\nConstructed", data_s.shape, "NumPy array for Substations")
	j = 0
	for key in sub_keys:
		i = 0
		for t in times:
			ary = lst_s[str(t)][sub_keys[j]]
			data_s[j, i,:] = ary
			i = i + 1
		j = j + 1

	# display a plot
	fig, ax = plt.subplots(2, 1, sharex = 'col')

	ax[0].plot(hrs, data_m[0,:,MTR_VOLT_MAX_IDX], color="blue", label="Max LN")
	ax[0].plot(hrs, data_m[0,:,MTR_VOLT_MIN_IDX], color="red", label="Min LN")
	ax[0].plot(hrs, data_m[0,:,MTR_VOLT12_MAX_IDX], color="green", label="Max LL")
	ax[0].plot(hrs, data_m[0,:,MTR_VOLT12_MIN_IDX], color="magenta", label="Min LL")
	ax[0].set_ylabel(MTR_VOLT_MAX_UNITS)
	ax[0].set_title ("Meter Voltages at " + mtr_keys[0])
	ax[0].legend(loc='best')

	ax[1].plot(hrs, data_s[0,:,SUB_POWER_IDX] / 1.0e6, color="red", label="Total")
	ax[1].plot(hrs, data_s[0,:,SUB_LOSSES_IDX] / 1.0e6, color="blue", label="Losses")
	ax[1].set_ylabel('MW')
	ax[1].set_title("Real Power at Substation")
	ax[1].legend(loc='best')
	ax[1].set_xlabel("Hours")

	plt.show()


