#	Copyright (C) 2017 Battelle Memorial Institute
# file: process_houses.py; focus on HVAC
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

casefiles = [['SGIP1a','red'],
						 ['SGIP1b','blue']]
#						 ['SGIP1c','green'],
#						 ['SGIP1d','magenta'],
#						 ['SGIP1e','cyan'],
#						 ['SGIP1ex','orange']]

def MakePlotData(root):
	lp = open (root + "_agent_dict.json")
	dict = json.loads(lp.read())
	lp.close()

	a_keys = list(dict['markets'].keys())
	a_keys.sort()
	lp_a = open ('auction_' + root + '_metrics.json')
	lst_a = json.loads(lp_a.read())
	lp_a.close()
	lst_a.pop('StartTime')
	meta_a = lst_a.pop('Metadata')

	times = list(map(int,list(lst_a.keys())))
	times.sort()
	hrs = np.array(times, dtype=np.float)
	denom = 3600.0
	hrs /= denom

	time_key = str(times[0])

	for key, val in meta_a.items():
		if key == 'clearing_price':
			CLEAR_IDX = val['index']
			CLEAR_UNITS = val['units']
		elif key == 'clearing_type':
			TYPE_IDX = val['index']


	data_a = np.empty(shape=(len(a_keys), len(times), len(lst_a[time_key][a_keys[0]])), dtype=np.float)
	j = 0
	for key in a_keys:
		i = 0
		for t in times:
			ary = lst_a[str(t)][a_keys[j]]
			data_a[j, i,:] = ary
			i = i + 1
		j = j + 1

	cprice = data_a[0,:,CLEAR_IDX]
	ctype = data_a[0,:,TYPE_IDX]
	return hrs, cprice, ctype

def compare_auction ():
	# display a plot
	tmin = 0.0
	tmax = 48.0
	xticks = [0,6,12,18,24,30,36,42,48]

	fig, ax = plt.subplots(2, 1, sharex = 'col')

	for root in casefiles:
		print ('Processing', root[0])
		hrs, cprice, ctype = MakePlotData(root[0])
		ax[0].plot(hrs, cprice, color=root[1], label=root[0])
		ax[1].plot(hrs, ctype, color=root[1], label=root[0])

	ax[0].set_title ('Cleared Price')
	ax[0].set_ylabel ('$')

	ax[1].set_title ('Cleared Type')

	ax[1].set_xlabel ('Hours')

	ax[0].grid()
	ax[0].legend()
	ax[0].set_xlim(tmin,tmax)
	ax[0].set_xticks(xticks)

	ax[1].grid()
	ax[1].legend()
	ax[1].set_xlim(tmin,tmax)
	ax[1].set_xticks(xticks)

	plt.show()


