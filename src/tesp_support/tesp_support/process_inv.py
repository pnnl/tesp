#	Copyright (C) 2017-2018 Battelle Memorial Institute
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def process_inv(nameroot, dictname = ''):
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
	cap_keys = list(dict['capacitors'].keys())
	cap_keys.sort()
	reg_keys = list(dict['regulators'].keys())
	reg_keys.sort()
	xfMVA = dict['transformer_MVA']
	matBus = dict['matpower_id']
	#print ("\n\nFile", nameroot, "has substation", sub_keys[0], "at Matpower bus", matBus, "with", xfMVA, "MVA transformer")
	#print("\nFeeder Dictionary:")
	#for key in sub_keys:
	#	row = dict['feeders'][key]
	#	print (key, "has", row['house_count'], "houses and", row['inverter_count'], "inverters")
	#print("\nBilling Meter Dictionary:")
	#for key in mtr_keys:
	#	row = dict['billingmeters'][key]
	#	print (key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])
	#print("\nHouse Dictionary:")
	#for key in hse_keys:
	#	row = dict['houses'][key]
	#	print (key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'], "heating", row['wh_gallons'], "gal WH")
	#	# row['feeder_id'] is also available
	#print("\nInverter Dictionary:")
	#for key in inv_keys:
	#	row = dict['inverters'][key]
	#	print (key, "on", row['billingmeter_id'], "has", row['rated_W'], "W", row['resource'], "resource")
	#	# row['feeder_id'] is also available

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

	# parse the substation metadata for 2 things of specific interest
	#print ("\nSubstation Metadata for", len(lst_s[time_key]), "objects")
	for key, val in meta_s.items():
	#	print (key, val['index'], val['units'])
		if key == 'real_power_avg':
			SUB_POWER_IDX = val['index']
			SUB_POWER_UNITS = val['units']
		elif key == 'real_power_losses_avg':
			SUB_LOSSES_IDX = val['index']
			SUB_LOSSES_UNITS = val['units']

	# create a NumPy array of all metrics for the substation
	data_s = np.empty(shape=(len(sub_keys), len(times), len(lst_s[time_key][sub_keys[0]])), dtype=np.float)
	#print ("\nConstructed", data_s.shape, "NumPy array for Substations")
	j = 0
	for key in sub_keys:
		i = 0
		for t in times:
			ary = lst_s[str(t)][sub_keys[j]]
			data_s[j, i,:] = ary
			i = i + 1
		j = j + 1

	# read the other JSON files; their times (hrs) should be the same
	lp_h = open ("house_" + nameroot + "_metrics.json").read()
	lst_h = json.loads(lp_h)
	lp_m = open ("billing_meter_" + nameroot + "_metrics.json").read()
	lst_m = json.loads(lp_m)
	lp_i = open ("inverter_" + nameroot + "_metrics.json").read()
	lst_i = json.loads(lp_i)
	lp_c = open ("capacitor_" + nameroot + "_metrics.json").read()
	lst_c = json.loads(lp_c)
	lp_r = open ("regulator_" + nameroot + "_metrics.json").read()
	lst_r = json.loads(lp_r)

	# houses
	lst_h.pop('StartTime')
	meta_h = lst_h.pop('Metadata')
	#print("\nHouse Metadata for", len(lst_h[time_key]), "objects")
	for key, val in meta_h.items():
	#	print (key, val['index'], val['units'])
		if key == 'air_temperature_max':
			HSE_AIR_MAX_IDX = val['index']
			HSE_AIR_MAX_UNITS = val['units']
		elif key == 'air_temperature_min':
			HSE_AIR_MIN_IDX = val['index']
			HSE_AIR_MIN_UNITS = val['units']
		elif key == 'air_temperature_avg':
			HSE_AIR_AVG_IDX = val['index']
			HSE_AIR_AVG_UNITS = val['units']
		elif key == 'air_temperature_median':
			HSE_AIR_MED_IDX = val['index']
			HSE_AIR_MED_UNITS = val['units']
		elif key == 'total_load_avg':
			HSE_TOTAL_AVG_IDX = val['index']
			HSE_TOTAL_AVG_UNITS = val['units']
		elif key == 'hvac_load_avg':
			HSE_HVAC_AVG_IDX = val['index']
			HSE_HVAC_AVG_UNITS = val['units']
		elif key == 'waterheater_load_avg':
			HSE_WH_AVG_IDX = val['index']
			HSE_WH_AVG_UNITS = val['units']

	data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
	#print ("\nConstructed", data_h.shape, "NumPy array for Houses")
	j = 0
	for key in hse_keys:
		i = 0
		for t in times:
			ary = lst_h[str(t)][hse_keys[j]]
			data_h[j, i,:] = ary
			i = i + 1
		j = j + 1

	# Billing Meters 
	lst_m.pop('StartTime')
	meta_m = lst_m.pop('Metadata')
	#print("\nBilling Meter Metadata for", len(lst_m[time_key]), "objects")
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
		elif key == 'real_energy':
			ENERGY_IDX = val['index']
		elif key == 'bill':
			MTR_BILL_IDX = val['index']
			MTR_BILL_UNITS = val['units']
		elif key == 'above_RangeA_Count':
			MTR_AHI_COUNT_IDX = val['index']
		elif key == 'above_RangeB_Count':
			MTR_BHI_COUNT_IDX = val['index']
		elif key == 'below_RangeA_Count':
			MTR_ALO_COUNT_IDX = val['index']
		elif key == 'below_RangeB_Count':
			MTR_BLO_COUNT_IDX = val['index']
		elif key == 'below_10_percent_NormVol_Count':
			MTR_OUT_COUNT_IDX = val['index']
		elif key == 'above_RangeA_Duration':
			MTR_AHI_DURATION_IDX = val['index']
		elif key == 'above_RangeB_Duration':
			MTR_BHI_DURATION_IDX = val['index']
		elif key == 'below_RangeA_Duration':
			MTR_ALO_DURATION_IDX = val['index']
		elif key == 'below_RangeB_Duration':
			MTR_BLO_DURATION_IDX = val['index']
		elif key == 'below_10_percent_NormVol_Duration':
			MTR_OUT_DURATION_IDX = val['index']

	data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
	#print ("\nConstructed", data_m.shape, "NumPy array for Meters")
	j = 0
	for key in mtr_keys:
		i = 0
		for t in times:
			ary = lst_m[str(t)][mtr_keys[j]]
			data_m[j, i,:] = ary
			i = i + 1
		j = j + 1

	# Inverters 
	lst_i.pop('StartTime')
	meta_i = lst_i.pop('Metadata')
	#print("\nInverter Metadata for", len(lst_i[time_key]), "objects")
	for key, val in meta_i.items():
	#	print (key, val['index'], val['units'])
		if key == 'real_power_avg':
			INV_P_AVG_IDX = val['index']
			INV_P_AVG_UNITS = val['units']
		elif key == 'reactive_power_avg':
			INV_Q_AVG_IDX = val['index']
			INV_Q_AVG_UNITS = val['units']

	data_i = np.empty(shape=(len(inv_keys), len(times), len(lst_i[time_key][inv_keys[0]])), dtype=np.float)
	print ("\nConstructed", data_i.shape, "NumPy array for Inverters")
	j = 0
	for key in inv_keys:
		i = 0
		for t in times:
			ary = lst_i[str(t)][inv_keys[j]]
			data_i[j, i,:] = ary
			i = i + 1
		j = j + 1

	# Precooling: won't necessarily have the same times?
	lp_p = open ("precool_" + nameroot + "_metrics.json").read()
	lst_p = json.loads(lp_p)
	lst_p.pop('StartTime')
	meta_p = lst_p.pop('Metadata')
	times_p = list(map(int,list(lst_p.keys())))
	times_p.sort()
	print ("There are", len (times_p), "agent sample times at", times_p[1] - times_p[0], "second intervals")
	hrs_p = np.array(times_p, dtype=np.float)
	denom = 3600.0
	hrs_p /= denom
	time_p_key = str(times_p[0])
	print("\nPrecooler Metadata for", len(lst_p[time_p_key]), "objects")
	for key, val in meta_p.items():
		print (key, val['index'], val['units'])
		if key == 'temperature_deviation_avg':
			TEMPDEV_AVG_IDX = val['index']
			TEMPDEV_AVG_UNITS = val['units']
		elif key == 'temperature_deviation_min':
			TEMPDEV_MIN_IDX = val['index']
			TEMPDEV_MIN_UNITS = val['units']
		elif key == 'temperature_deviation_max':
			TEMPDEV_MAX_IDX = val['index']
			TEMPDEV_MAX_UNITS = val['units']

	data_p = np.empty(shape=(1, len(times_p), len(lst_p[time_p_key])), dtype=np.float)
	print ("\nConstructed", data_p.shape, "NumPy array for Agents")
	i = 0
	for t in times_p:
		ary = lst_p[str(t)]
		data_p[0, i,:] = ary
		i = i + 1

	have_caps = False
	have_regs = False

	# Capacitors
	if len(cap_keys) > 0:
		have_caps = True
		lst_c.pop('StartTime')
		meta_c = lst_c.pop('Metadata')
		print("\nCapacitor Metadata for", len(lst_c[time_key]), "objects")
		for key, val in meta_c.items():
			if key == 'operation_count':
				CAP_COUNT_IDX = val['index']
				CAP_COUNT_UNITS = val['units']
		data_c = np.empty(shape=(len(cap_keys), len(times), len(lst_c[time_key][cap_keys[0]])), dtype=np.float)
		print ("\nConstructed", data_c.shape, "NumPy array for Capacitors")
		j = 0
		for key in cap_keys:
			i = 0
			for t in times:
				ary = lst_c[str(t)][cap_keys[j]]
				data_c[j, i,:] = ary
				i = i + 1
			j = j + 1

	# Regulators
	if len(reg_keys) > 0:
		have_regs = True
		lst_r.pop('StartTime')
		meta_r = lst_r.pop('Metadata')
		print("\nRegulator Metadata for", len(lst_r[time_key]), "objects")
		for key, val in meta_r.items():
			if key == 'operation_count':
				REG_COUNT_IDX = val['index']
				REG_COUNT_UNITS = val['units']
		data_r = np.empty(shape=(len(reg_keys), len(times), len(lst_r[time_key][reg_keys[0]])), dtype=np.float)
		print ("\nConstructed", data_r.shape, "NumPy array for Regulators")
		j = 0
		for key in reg_keys:
			i = 0
			for t in times:
				ary = lst_r[str(t)][reg_keys[j]]
				data_r[j, i,:] = ary
				i = i + 1
			j = j + 1

	## assemble the total solar and battery inverter power
	j = 0
	solar_kw = np.zeros(len(times), dtype=np.float)
	battery_kw = np.zeros(len(times), dtype=np.float)
	for key in inv_keys:
		res = dict['inverters'][key]['resource']
		if res == 'solar':
			solar_kw += 0.001 * data_i[j,:,INV_P_AVG_IDX]
		elif res == 'battery':
			battery_kw += 0.001 * data_i[j,:,INV_P_AVG_IDX]
		j = j + 1

	hour1 = 4.0
	for i in range(0, len(hrs)):
		if hrs[i] > hour1:
			ihour1 = i
			break

	for i in range(0, len(hrs_p)):
		if hrs_p[i] > hour1:
			ihour1_p = i
			break

	# display some averages
	print ("Maximum feeder power =", '{:.2f}'.format(0.001*data_s[0,:,SUB_POWER_IDX].max()), 'kW')
	print ("Average feeder power =", '{:.2f}'.format(0.001*data_s[0,:,SUB_POWER_IDX].mean()), 'kW')
	print ("Average feeder losses =", '{:.2f}'.format(0.001*data_s[0,:,SUB_LOSSES_IDX].mean()), 'kW')
	print ('Average all house temperatures Noon-8 pm day 1:', '{:.2f}'.format(data_h[:,144:240,HSE_AIR_AVG_IDX].mean()))
	#print ('Average all house temperatures Noon-8 pm day 2:', '{:.2f}'.format(data_h[:,432:528,HSE_AIR_AVG_IDX].mean()))
	print ("Average inverter P =", '{:.2f}'.format(data_i[:,:,INV_P_AVG_IDX].mean()), INV_P_AVG_UNITS)
	print ("Average inverter Q =", '{:.2f}'.format(data_i[:,:,INV_Q_AVG_IDX].mean()), INV_Q_AVG_UNITS)
	print ("A Range Hi Duration =", '{:.2f}'.format(data_m[:,:,MTR_AHI_DURATION_IDX].sum() / 3600.0), 
				 "count =", '{:.2f}'.format(data_m[:,:,MTR_AHI_COUNT_IDX].sum()))
	print ("A Range Lo Duration =", '{:.2f}'.format(data_m[:,:,MTR_ALO_DURATION_IDX].sum() / 3600.0), 
				 "count =", '{:.2f}'.format(data_m[:,:,MTR_ALO_COUNT_IDX].sum()))
	print ("B Range Hi Duration =", '{:.2f}'.format(data_m[:,:,MTR_BHI_DURATION_IDX].sum() / 3600.0), 
				 "count =", '{:.2f}'.format(data_m[:,:,MTR_BHI_COUNT_IDX].sum()))
	print ("B Range Lo Duration =", '{:.2f}'.format(data_m[:,:,MTR_BLO_DURATION_IDX].sum() / 3600.0), 
				 "count =", '{:.2f}'.format(data_m[:,:,MTR_BLO_COUNT_IDX].sum()))
	print ("Zero-Volts Duration =", '{:.2f}'.format(data_m[:,:,MTR_OUT_DURATION_IDX].sum() / 3600.0), 
				 "count =", '{:.2f}'.format(data_m[:,:,MTR_OUT_COUNT_IDX].sum()))
	if have_caps:
		print ("Total cap switchings =", '{:.2f}'.format(data_c[:,-1,CAP_COUNT_IDX].sum()))
	if have_regs:
		print ("Total tap changes =", '{:.2f}'.format(data_r[:,-1,REG_COUNT_IDX].sum()))

	final_bill = np.empty(shape=(len(times)), dtype=np.float)
	final_bill[0] = 0.0
	for i in range (1, len(hrs)):
		if hrs[i] > 15.0 and hrs[i] <= 19.0:
			price = 0.15
		else:
			price = 0.11
		kwh = 0.001 * data_m[:,i,ENERGY_IDX].sum()
		print ('adding', kwh, 'at', price)
		final_bill[i] = final_bill[i-1] + price * kwh

	print ("Initial meter bill =", '{:.2f}'.format(data_m[:,-1,MTR_BILL_IDX].sum() - 19770.0))
	print ("Final meter bill =", '{:.2f}'.format(final_bill[-1]))
	print ("Average Temperature Deviation =", '{:.2f}'.format(data_p[:,:,TEMPDEV_AVG_IDX].mean()))

	print ('Summarizing from', hour1, 'hours to begin at indices', ihour1, ihour1_p)
	print ("Interval A Range Hi Duration =", '{:.2f}'.format(data_m[:,ihour1:-1,MTR_AHI_DURATION_IDX].sum() / 3600.0))
	print ("Interval A Range Lo Duration =", '{:.2f}'.format(data_m[:,ihour1:-1,MTR_ALO_DURATION_IDX].sum() / 3600.0))
	print ("Interval B Range Hi Duration =", '{:.2f}'.format(data_m[:,ihour1:-1,MTR_BHI_DURATION_IDX].sum() / 3600.0))
	print ("Interval B Range Lo Duration =", '{:.2f}'.format(data_m[:,ihour1:-1,MTR_BLO_DURATION_IDX].sum() / 3600.0)) 
	print ("Interval Average Temperature Deviation =", '{:.2f}'.format(data_p[:,ihour1_p:-1,TEMPDEV_AVG_IDX].mean()))
	if have_caps:
		print ("Interval Cap Switchings =", '{:.2f}'.format(data_c[:,-1,CAP_COUNT_IDX].sum() - data_c[:,ihour1,CAP_COUNT_IDX].sum()))
	if have_regs:
		print ("Interval Tap Changes =", '{:.2f}'.format(data_r[:,-1,REG_COUNT_IDX].sum() - data_r[:,ihour1,REG_COUNT_IDX].sum()))


	# create summary arrays
	total1 = (data_h[:,:,HSE_TOTAL_AVG_IDX]).squeeze()
	total2 = total1.sum(axis=0)
	hvac1 = (data_h[:,:,HSE_HVAC_AVG_IDX]).squeeze()
	hvac2 = hvac1.sum(axis=0)
	wh1 = (data_h[:,:,HSE_WH_AVG_IDX]).squeeze()
	wh2 = wh1.sum(axis=0)
	subkw = 0.001 * data_s[0,:,SUB_POWER_IDX]
	losskw = 0.001 * data_s[0,:,SUB_LOSSES_IDX]
	pavg1 = (data_i[:,:,INV_P_AVG_IDX]).squeeze()
	pavg2 = 0.001 * pavg1.mean(axis=0)
	qavg1 = (data_i[:,:,INV_Q_AVG_IDX]).squeeze()
	qavg2 = 0.001 * qavg1.mean(axis=0)
	tavg1 = (data_h[:,:,HSE_AIR_AVG_IDX]).squeeze()
	tavg2 = tavg1.mean(axis=0)
	vscale = 100.0 / 120.0
	vavg = vscale * (data_m[:,:,MTR_VOLT_AVG_IDX]).squeeze().mean(axis=0)
	vmin = vscale * (data_m[:,:,MTR_VOLT_MIN_IDX]).squeeze().min(axis=0)
	vmax = vscale * (data_m[:,:,MTR_VOLT_MAX_IDX]).squeeze().max(axis=0)

	# display a plot

	tmin = 0.0
	tmax = 24.0
	xticks = [0,4,8,12,16,20,24]

	SMALL_SIZE = 10
	MEDIUM_SIZE = 12
	BIGGER_SIZE = 14

	plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
	plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
	plt.rc('axes', labelsize=SMALL_SIZE)    # fontsize of the x and y labels
	plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
	plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
	plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
	plt.rc('figure', titlesize=SMALL_SIZE)  # fontsize of the figure title

	if have_caps or have_regs:
		fig, ax = plt.subplots(2, 5, sharex = 'col', figsize=(14,7))
	else:
		fig, ax = plt.subplots(2, 4, sharex = 'col', figsize=(14,6))

	ax[0,0].plot(hrs, pavg2, color="blue", label="P")
	ax[0,0].plot(hrs, qavg2, color="red", label="Q")
	ax[0,0].set_ylabel("kVA")
	ax[0,0].set_title ("Average Inverter Power", size=MEDIUM_SIZE)
	ax[0,0].legend(loc='best')
	ax[0,0].set_xlim(tmin,tmax)
	ax[0,0].set_xticks(xticks)

	#vabase = dict['inverters'][inv_keys[0]]['rated_W']
	#print ("Inverter base power =", vabase)
	#ax[0,1].plot(hrs, data_i[0,:,INV_P_AVG_IDX] / vabase, color="blue", label="Real")
	#ax[0,1].plot(hrs, data_i[0,:,INV_Q_AVG_IDX] / vabase, color="red", label="Reactive")
	#ax[0,1].set_ylabel("perunit")
	#ax[0,1].set_title ("Inverter Power at " + inv_keys[0])
	#ax[0,1].legend(loc='best')

	ax[1,0].plot(hrs, vmax, color="blue", label="Max")
	ax[1,0].plot(hrs, vmin, color="red", label="Min")
	ax[1,0].plot(hrs, vavg, color="green", label="Avg")
	ax[1,0].set_xlabel("Hours")
	ax[1,0].set_ylabel("%")
	ax[1,0].set_title ("All Meter Voltages", size=MEDIUM_SIZE)
	ax[1,0].legend(loc='best')
	ax[1,0].set_xlim(tmin,tmax)
	ax[1,0].set_xticks(xticks)

	ax[0,1].plot(hrs, tavg2, color="red", label="Avg")
	ax[0,1].set_ylabel('degF')
	ax[0,1].set_title ('Average House Temperatures', size=MEDIUM_SIZE)
	ax[0,1].set_xlim(tmin,tmax)
	ax[0,1].set_xticks(xticks)

	ax[1,1].plot(hrs_p, data_p[0,:,TEMPDEV_AVG_IDX], color="blue", label="Mean")
	#ax[1,1].plot(hrs_p, data_p[0,:,TEMPDEV_MIN_IDX], color="red", label="Min")
	#ax[1,1].plot(hrs_p, data_p[0,:,TEMPDEV_MAX_IDX], color="green", label="Max")
	ax[1,1].set_xlabel("Hours")
	ax[1,1].set_ylabel(TEMPDEV_AVG_UNITS)
	ax[1,1].set_title ("Average Temperature Deviations", size=MEDIUM_SIZE)
	#ax[1,1].legend(loc='best')
	ax[1,1].set_xlim(tmin,tmax)
	ax[1,1].set_xticks(xticks)

	ax[0,2].plot(hrs, (data_m[:,:,MTR_AHI_COUNT_IDX]).squeeze().sum(axis=0), color="blue", label="Range A Hi")
	ax[0,2].plot(hrs, (data_m[:,:,MTR_BHI_COUNT_IDX]).squeeze().sum(axis=0), color="cyan", label="Range B Hi")
	ax[0,2].plot(hrs, (data_m[:,:,MTR_ALO_COUNT_IDX]).squeeze().sum(axis=0), color="green", label="Range A Lo")
	ax[0,2].plot(hrs, (data_m[:,:,MTR_BLO_COUNT_IDX]).squeeze().sum(axis=0), color="magenta", label="Range B Lo")
	ax[0,2].plot(hrs, (data_m[:,:,MTR_OUT_COUNT_IDX]).squeeze().sum(axis=0), color="red", label="No Voltage")
	ax[0,2].set_ylabel("")
	ax[0,2].set_title ("All Voltage Violation Counts", size=MEDIUM_SIZE)
	ax[0,2].legend(loc='best')
	ax[0,2].set_xlim(tmin,tmax)
	ax[0,2].set_xticks(xticks)

	scalem = 1.0 / 3600.0
	ax[1,2].plot(hrs, scalem * (data_m[:,:,MTR_AHI_DURATION_IDX]).squeeze().sum(axis=0), color="blue", label="Range A Hi")
	ax[1,2].plot(hrs, scalem * (data_m[:,:,MTR_BHI_DURATION_IDX]).squeeze().sum(axis=0), color="cyan", label="Range B Hi")
	ax[1,2].plot(hrs, scalem * (data_m[:,:,MTR_ALO_DURATION_IDX]).squeeze().sum(axis=0), color="green", label="Range A Lo")
	ax[1,2].plot(hrs, scalem * (data_m[:,:,MTR_BLO_DURATION_IDX]).squeeze().sum(axis=0), color="magenta", label="Range B Lo")
	ax[1,2].plot(hrs, scalem * (data_m[:,:,MTR_OUT_DURATION_IDX]).squeeze().sum(axis=0), color="red", label="No Voltage")
	ax[1,2].set_xlabel("Hours")
	ax[1,2].set_ylabel("Hours")
	ax[1,2].set_title ("All Voltage Violation Durations", size=MEDIUM_SIZE)
	ax[1,2].legend(loc='best')
	ax[1,2].set_xlim(tmin,tmax)
	ax[1,2].set_xticks(xticks)

	ax[0,3].plot(hrs, subkw, color="blue", label="Substation")
	ax[0,3].plot(hrs, losskw, color="red", label="Losses")
	ax[0,3].plot(hrs, total2, color="green", label="Houses")
	ax[0,3].plot(hrs, hvac2, color="magenta", label="HVAC")
	ax[0,3].plot(hrs, wh2, color="orange", label="WH")
	ax[0,3].set_ylabel('kW')
	ax[0,3].set_title ("Average Real Power", size=MEDIUM_SIZE)
	ax[0,3].legend(loc='best')
	ax[0,3].set_xlim(tmin,tmax)
	ax[0,3].set_xticks(xticks)

	#ax[1,3].plot(hrs, data_m[0,:,MTR_BILL_IDX], color="blue")
	ax[1,3].plot(hrs, (data_m[:,:,MTR_BILL_IDX]).squeeze().sum(axis=0) - 19770.0, color='blue', label='Tariff')
	ax[1,3].plot(hrs, final_bill, color='red', label='Dynamic')
	ax[1,3].set_xlabel("Hours")
	ax[1,3].set_ylabel(MTR_BILL_UNITS)
	ax[1,3].set_title ("Meter Bills", size=MEDIUM_SIZE)
	ax[1,3].legend(loc='best')
	ax[1,3].set_xlim(tmin,tmax)
	ax[1,3].set_xticks(xticks)

	if have_caps:
		ax[0,4].plot(hrs, data_c[0,:,CAP_COUNT_IDX], color="blue", label=cap_keys[0])
		ax[0,4].plot(hrs, data_c[1,:,CAP_COUNT_IDX], color="red", label=cap_keys[1])
		ax[0,4].plot(hrs, data_c[2,:,CAP_COUNT_IDX], color="green", label=cap_keys[2])
		ax[0,4].plot(hrs, data_c[3,:,CAP_COUNT_IDX], color="magenta", label=cap_keys[3])
		ax[0,4].set_ylabel("")
		ax[0,4].set_title ("Cap Switchings", size=MEDIUM_SIZE)
		ax[0,4].legend(loc='best')
		ax[0,4].set_xlim(tmin,tmax)
		ax[0,4].set_xticks(xticks)

	if have_regs:
		ax[1,4].plot(hrs, data_r[0,:,REG_COUNT_IDX], color="blue", label=reg_keys[0])
		ax[1,4].plot(hrs, data_r[1,:,REG_COUNT_IDX], color="red", label=reg_keys[1])
		ax[1,4].plot(hrs, data_r[2,:,REG_COUNT_IDX], color="green", label=reg_keys[2])
		ax[1,4].plot(hrs, data_r[3,:,REG_COUNT_IDX], color="magenta", label=reg_keys[3])
		ax[1,4].set_xlabel("Hours")
		ax[1,4].set_ylabel("")
		ax[1,4].set_title ("Tap Changes", size=MEDIUM_SIZE)
		ax[1,4].legend(loc='best')
		ax[1,4].set_xlim(tmin,tmax)
		ax[1,4].set_xticks(xticks)

	if have_caps or have_regs:
		ax[1,4].set_xlabel("Hours")

	plt.tight_layout(pad=1.0, w_pad=1.0, h_pad=2.0)
	plt.show()


