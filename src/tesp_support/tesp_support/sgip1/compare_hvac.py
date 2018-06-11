#	Copyright (C) 2017 Battelle Memorial Institute
# file: process_houses.py; focus on HVAC
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

casefiles = [['SGIP1a','red'],
						 ['SGIP1b','blue'],
						 ['SGIP1c','green']]
#						 ['SGIP1d','magenta'],
#						 ['SGIP1e','cyan'],
#						 ['SGIP1ex','orange']]

def MakePlotData(root):
	lp = open (root + "_glm_dict.json")
	dict = json.loads(lp.read())
	lp.close()

	sub_keys = list(dict['feeders'].keys())
	sub_keys.sort()
	lp_s = open ("substation_" + root + "_metrics.json")
	lst_s = json.loads(lp_s.read())
	lp_s.close()
	lst_s.pop('StartTime')
	meta_s = lst_s.pop('Metadata')

	hse_keys = list(dict['houses'].keys())
	hse_keys.sort()
	for key in hse_keys:
		row = dict['houses'][key]
	lp_h = open ("house_" + root + "_metrics.json")
	lst_h = json.loads(lp_h.read())
	lp_h.close()
	lst_h.pop('StartTime')
	meta_h = lst_h.pop('Metadata')

	times = list(map(int,list(lst_h.keys())))
	times.sort()
	hrs = np.array(times, dtype=np.float)
	denom = 3600.0
	hrs /= denom

	time_key = str(times[0])

	for key, val in meta_s.items():
		if key == 'real_power_avg':
			SUB_POWER_IDX = val['index']

	for key, val in meta_h.items():
		if key == 'air_temperature_avg':
			AIR_AVG_IDX = val['index']
		elif key == 'hvac_load_avg':
			HVAC_AVG_IDX = val['index']

	data_s = np.empty(shape=(len(sub_keys), len(times), len(lst_s[time_key][sub_keys[0]])), dtype=np.float)
	j = 0
	for key in sub_keys:
		i = 0
		for t in times:
			ary = lst_s[str(t)][sub_keys[j]]
			data_s[j, i,:] = ary
			i = i + 1
		j = j + 1
	sub_mw = 1.0e-6 * data_s[0,:,SUB_POWER_IDX]

	data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
	j = 0
	for key in hse_keys:
		i = 0
		for t in times:
			ary = lst_h[str(t)][hse_keys[j]]
			data_h[j, i,:] = ary
			i = i + 1
		j = j + 1

	hvac1 = (data_h[:,:,HVAC_AVG_IDX]).squeeze()
	hvac2 = 0.001 * hvac1.sum(axis=0)

	j = 0
	n = 0
	avg_temp = np.zeros(len(times), dtype=np.float)
	for key in hse_keys:
		cool = dict['houses'][key]['cooling']
		if cool == 'ELECTRIC':
			avg_temp += data_h[j,:,AIR_AVG_IDX]
			n += 1
		j = j + 1
	avg_temp /= n
	print(n,'HVACs')
	return hrs, avg_temp, hvac2, sub_mw

def compare_hvac():
	# display a plot
	tmin = 0.0
	tmax = 48.0
	xticks = [0,6,12,18,24,30,36,42,48]

	fig, ax = plt.subplots(3, 1, sharex = 'col')

	for root in casefiles:
		print ('Processing', root[0])
		hrs, avg_temp, hvac2, sub_mw = MakePlotData(root[0])
		ax[0].plot(hrs, avg_temp, color=root[1], label=root[0])
		ax[1].plot(hrs, hvac2, color=root[1], label=root[0])
		ax[2].plot(hrs, sub_mw, color=root[1], label=root[0])

	ax[0].set_title ("Temperature at all HVAC Houses")
	ax[0].set_ylabel("Average Degrees")

	ax[1].set_title ("HVAC Power")
	ax[1].set_ylabel("Total MW")

	ax[2].set_title ("Feeder Power")
	ax[2].set_ylabel("Total MW")

	ax[2].set_xlabel("Hours")

	ax[0].grid()
	ax[0].legend()
	ax[0].set_xlim(tmin,tmax)
	ax[0].set_xticks(xticks)

	ax[1].grid()
	ax[1].legend()
	ax[1].set_xlim(tmin,tmax)
	ax[1].set_xticks(xticks)

	ax[2].grid()
	ax[2].legend()
	ax[2].set_xlim(tmin,tmax)
	ax[2].set_xticks(xticks)

	plt.show()


