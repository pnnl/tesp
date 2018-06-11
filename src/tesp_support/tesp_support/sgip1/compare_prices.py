import csv;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

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

def UnitPrice (p, c2, c1, c0):
	lmp = p * 2.0 * c2 + c1
	return lmp

def MakePlotData(root):
	d1 = np.loadtxt(root + '.csv', skiprows=1, delimiter=',',
									usecols=[0,2,3,4,5,6,7,9,10,11,12,13,14,15,16,17,18,19,20])
	hrs = d1[:,0] / 3600.0
	lmp = d1[:,9]
	p1 = d1[:,11]
	p2 = d1[:,12]
	p3 = d1[:,13]
	p4 = d1[:,14]
	pdisp = d1[:,15]
	gc2 = d1[:,16]
	gc1 = d1[:,17]

	lmp1 = UnitPrice (p1, 0.030,  1.3,  180.0)
	lmp2 = UnitPrice (p2, 0.085,  3.0,  100.0)
	lmp3 = UnitPrice (p3, 0.122,  5.0,  135.0)
	lmp4 = UnitPrice (p4, 3.000, 50.0, 1500.0)
	lmp5 = 2.0 * pdisp * gc2 + gc1

	return hrs, lmp, lmp1, lmp2, lmp3, lmp4, lmp5

def compare_prices (rootname):
	# display a plot
	tmin = 0.0
	tmax = 48.0
	xticks = [0,6,12,18,24,30,36,42,48]

	fig, ax = plt.subplots(1, 1, sharex = 'col')

	hrs, lmp, lmp1, lmp2, lmp3, lmp4, lmp5 = MakePlotData (rootname)
	#ax.plot(hrs, lmp1, color='blue', label='LMP1')
	#ax.plot(hrs, lmp2, color='green', label='LMP2')
	#ax.plot(hrs, lmp3, color='magenta', label='LMP3')
	#ax.plot(hrs, lmp4, color='cyan', label='LMP4')
	ax.plot(hrs, lmp5, color='orange', label='LMP5')
	ax.plot(hrs, lmp, color='red', label='LMP')

	ax.set_title ('Price Comparison for ' + root)
	ax.set_ylabel ('$/MWHR')
	ax.set_xlabel ('Hours')
	ax.grid()
	ax.legend()
	ax.set_xlim(tmin,tmax)
	ax.set_xticks(xticks)

	plt.show()


