#	Copyright (C) 2017 Battelle Memorial Institute
# file: process_houses.py; focus on HVAC
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

casefiles = [['SGIP1a','red'],
						 ['SGIP1b','blue'],
						 ['SGIP1c','green'],
						 ['SGIP1d','magenta'],
						 ['SGIP1e','cyan'],
						 ['SGIP1ex','orange']]

def MakePlotData(root):
	lp = open (root + "_glm_dict.json")
	dict = json.loads(lp.read())
	lp.close()
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

	for key, val in meta_h.items():
		if key == 'air_temperature_avg':
			AIR_AVG_IDX = val['index']
		elif key == 'hvac_load_avg':
			HVAC_AVG_IDX = val['index']

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
	hvac2 = hvac1.sum(axis=0)

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
	return hrs, avg_temp, hvac2

# display a plot
fig, ax = plt.subplots(2, 1, sharex = 'col')
for root in casefiles:
	print ('Processing', root[0])
	hrs, avg_temp, hvac2 = MakePlotData(root[0])
	ax[0].plot(hrs, avg_temp, color=root[1], label=root[0])
	ax[1].plot(hrs, hvac2, color=root[1], label=root[0])

ax[0].set_ylabel("Average Degrees")
ax[1].set_ylabel("Total kW")
ax[1].set_xlabel("Hours")
ax[0].set_title ("HVAC at all Houses")

ax[0].grid()
ax[1].grid()
ax[0].legend()
ax[1].legend()

plt.show()


