# Copyright 1996-2015 PSERC. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Power flow data for 9 bus, 3 generator case.
"""

from numpy import array

def ppcasefile():
	"""Power flow data for 9 bus, 3 generator case.
	Please see L{caseformat} for details on the case file format.

	Based on data from Joe H. Chow's book, p. 70.

	@return: Power flow data for 9 bus, 3 generator case.
	"""
	ppc = {'version': '2'}

	##-----  Power Flow Data  -----##
	## system MVA base
	ppc['baseMVA'] = 100.0

	## bus data
	# bus_i type Pd Qd Gs Bs area Vm Va baseKV zone Vmax Vmin
	ppc['bus'] = array([
		[1, 2, 0,    0, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9],
		[2, 3, 0,    0, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9],
		[3, 2, 0,    0, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9],
		[4, 1, 0,    0, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9],
		[5, 1, 90,  30, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9],
		[6, 1, 0,    0, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9],
		[7, 1, 100, 35, 0, 0, 1, 1, 0, 230, 1, 1.05, 0.95],
		[8, 1, 0,    0, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9],
		[9, 1, 125, 50, 0, 0, 1, 1, 0, 230, 1, 1.1, 0.9]
	])

	## generator data - be careful that the lowest-cost generator is not the swing bus
	# bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, Pc1, Pc2,
	# Qc1min, Qc1max, Qc2min, Qc2max, ramp_agc, ramp_10, ramp_30, ramp_q, apf
	ppc['gen'] = array([
		[1, 163, 0, 300, -300, 1, 247, 1, 247,  10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
		[2,  0,  0, 300, -300, 1, 192, 1, 192,  10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
		[3, 85,  0, 300, -300, 1, 128, 1, 128,  10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
		[9,  0,  0, 300, -300, 1, 250, 1, 250,   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
		[7,  0,  0,   0,    0, 1, 250, 1,   0, -80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # responsive load
	])

	## branch data
	# fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
	ppc['branch'] = array([
		[1, 4, 0,      0.0576, 0,     250, 250, 250, 0, 0, 1, -360, 360],
		[4, 5, 0.017,  0.092,  0.158, 250, 250, 250, 0, 0, 1, -360, 360],
		[5, 6, 0.039,  0.17,   0.358, 150, 150, 150, 0, 0, 1, -360, 360],
		[3, 6, 0,      0.0586, 0,     300, 300, 300, 0, 0, 1, -360, 360],
		[6, 7, 0.0119, 0.1008, 0.209, 150, 150, 150, 0, 0, 1, -360, 360],
		[7, 8, 0.0085, 0.072,  0.149, 250, 250, 250, 0, 0, 1, -360, 360],
		[8, 2, 0,      0.0625, 0,     250, 250, 250, 0, 0, 1, -360, 360],
		[8, 9, 0.032,  0.161,  0.306, 250, 250, 250, 0, 0, 1, -360, 360],
		[9, 4, 0.01,   0.085,  0.176, 250, 250, 250, 0, 0, 1, -360, 360]
	])

	##-----  OPF Data  -----##
	## area data
	# area refbus
	ppc['areas'] = array([
		[1, 5]
	])

	## generator cost data
	# 1 startup shutdown n x1 y1 ... xn yn
	# 2 startup shutdown n c(n-1) ... c0
	ppc['gencost'] = array([
		[2,  500, 0, 3, 0.03,   1.3,   180], # hydro
		[2, 2000, 0, 3, 0.085,  3.0,   100], # gas combined cycle
		[2, 3000, 0, 3, 0.122,  5.0,   135], # gas simple cycle
		[2, 3000, 0, 3, 3.0,   50.0,  1500], # gas combined cycle (expensive)
		[2,    0, 0, 3, 0.0,    0.0,   0.0]  # responsive load
	])

	# bus, subscription topic, amplification factor, current value
	ppc['DSO'] = array([
		[7, 'SUBSTATION7', 20.0, 0.0]
	])

	# unit, time out, time back in
	ppc['UnitsOut'] = array([
		[2, 108000, 158400] # 128-MW unit at bus 3
#		[2, 108000, 118400], # 128-MW unit at bus 3
#		[1, 123000, 136000]  # 192-MW unit at bus 2
	])

	# branch, time out, time back in
	ppc['BranchesOut'] = array([
#		[3, 149000, 159000]  # GSU for 128-MW unit at bus 3
	])

	ppc['StartTime'] = '2013-07-01 00:00:00'
	ppc['Tmax'] = 172800
	ppc['Period'] = 300  # market clearing period
	ppc['dt'] = 15        # time step for bids
	ppc['CSVFile'] = 'NonGLDLoad.txt'
	ppc['opf_dc'] = 1
	ppc['pf_dc'] = 1

	return ppc
