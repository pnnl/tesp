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
	lp = open (root + "_m_dict.json")
	dict = json.loads(lp.read())
	lp.close()

	gen_keys = list(dict['generators'].keys())
	gen_keys.sort()
	lp_g = open ('gen_' + root + '_metrics.json')
	lst_g = json.loads(lp_g.read())
	lp_g.close()
	lst_g.pop('StartTime')
	meta_g = lst_g.pop('Metadata')

	bus_keys = list(dict['fncsBuses'].keys())
	bus_keys.sort()
	lp_b = open ('bus_' + root + '_metrics.json')
	lst_b = json.loads(lp_b.read())
	lp_b.close()
	lst_b.pop('StartTime')
	meta_b = lst_b.pop('Metadata')

	times = list(map(int,list(lst_b.keys())))
	times.sort()
	hrs = np.array(times, dtype=np.float)
	denom = 3600.0
	hrs /= denom

	time_key = str(times[0])

	for key, val in meta_g.items():
		if key == 'Pgen':
			PGEN_IDX = val['index']
			PGEN_UNITS = val['units']
		elif key == 'Qgen':
			QGEN_IDX = val['index']
			QGEN_UNITS = val['units']
		elif key == 'LMP_P':
			GENLMP_IDX = val['index']
			GENLMP_UNITS = val['units']

	for key, val in meta_b.items():
		if key == 'LMP_P':
			LMP_P_IDX = val['index']
			LMP_P_UNITS = val['units']
		elif key == 'LMP_Q':
			LMP_Q_IDX = val['index']
			LMP_Q_UNITS = val['units']
		elif key == 'PD':
			PD_IDX = val['index']
			PD_UNITS = val['units']
		elif key == 'QD':
			QD_IDX = val['index']
			QD_UNITS = val['units']
		elif key == 'Vang':
			VANG_IDX = val['index']
			VANG_UNITS = val['units']
		elif key == 'Vmag':
			VMAG_IDX = val['index']
			VMAG_UNITS = val['units']
		elif key == 'Vmax':
			VMAX_IDX = val['index']
			VMAX_UNITS = val['units']
		elif key == 'Vmin':
			VMIN_IDX = val['index']
			VMIN_UNITS = val['units']

	data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[time_key][gen_keys[0]])), dtype=np.float)
	j = 0
	for key in gen_keys:
		i = 0
		for t in times:
			ary = lst_g[str(t)][gen_keys[j]]
			data_g[j, i,:] = ary
			i = i + 1
		j = j + 1

	data_b = np.empty(shape=(len(bus_keys), len(times), len(lst_b[time_key][bus_keys[0]])), dtype=np.float)
	j = 0
	for key in bus_keys:
		i = 0
		for t in times:
			ary = lst_b[str(t)][bus_keys[j]]
			data_b[j, i,:] = ary
			i = i + 1
		j = j + 1

	gen1 = (data_g[:,:,PGEN_IDX]).squeeze()
	tgen = gen1.sum(axis=0)
	pfncs = data_b[0,:,PD_IDX]
	lmp = data_b[0,:,LMP_P_IDX]
	return hrs, pfncs, tgen, lmp

def compare_pypower ():
	# display a plot
	tmin = 0.0
	tmax = 48.0
	xticks = [0,6,12,18,24,30,36,42,48]

	fig, ax = plt.subplots(3, 1, sharex = 'col')

	for root in casefiles:
		print ('Processing', root[0])
		hrs, pfncs, tgen, lmp = MakePlotData(root[0])
		ax[0].plot(hrs, pfncs, color=root[1], label=root[0])
		ax[1].plot(hrs, tgen, color=root[1], label=root[0])
		ax[2].plot(hrs, lmp, color=root[1], label=root[0])

	ax[0].set_title ('FNCS Bus Load')
	ax[0].set_ylabel ('MW')

	ax[1].set_title ('Total Generation')
	ax[1].set_ylabel ('MW')

	ax[2].set_title ('FNCS Bus LMP')
	ax[2].set_ylabel ('$/kwh')

	ax[2].set_xlabel ('Hours')

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


