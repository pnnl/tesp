import csv;
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

# here are the columns, after ignore 'True/False' with usecols
plotvars = [[0, 't[s]', 'seconds'],
						[1, 'Pload', 'MW'],
						[2, 'P7 (csv)', 'MW'],
						[3, 'GLD Unresp', 'MW'],
						[4, 'P7 (opf)', 'MW'],
						[5, 'Resp (opf)', 'MW'],
						[6, 'GLD Pub', 'MW'],
						[7, 'P7 Min', 'MW'],
						[8, 'V7', 'pu'],
						[9, 'LMP_P7', '$/MWHR'],
						[10, 'LMP_Q7', '$/MWHR'],
						[11, 'Pgen1', 'MW'],
						[12, 'Pgen2', 'MW'],
						[13, 'Pgen3', 'MW'],
						[14, 'Pgen4', 'MW'],
						[15, 'Pdisp', 'MW'],
						[16, 'gencost2', '$'],
						[17, 'gencost1', '$'],
						[18, 'gencost0', '$']]

def MakePlotData(root, idx):
	d1 = np.loadtxt(root + '.csv', skiprows=1, delimiter=',',
									usecols=[0,2,3,4,5,6,7,9,10,11,12,13,14,15,16,17,18,19,20])
	hrs = d1[:,0] / 3600.0

	return hrs, d1[:,idx]

def compare_csv (idx):
	# display a plot - indexed to plotvars
	tmin = 0.0
	tmax = 48.0
	xticks = [0,6,12,18,24,30,36,42,48]

	fig, ax = plt.subplots(1, 1, sharex = 'col')

	for root in casefiles:
		print ('Processing', root[0])
		hrs, vals = MakePlotData(root[0],idx)
		ax.plot(hrs, vals, color=root[1], label=root[0])

	ax.set_title (plotvars[idx][1])
	ax.set_ylabel (plotvars[idx][2])
	ax.set_xlabel ('Hours')
	ax.grid()
	ax.legend()
	ax.set_xlim(tmin,tmax)
	ax.set_xticks(xticks)

	plt.show()


