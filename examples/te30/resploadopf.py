#	Copyright (C) 2017 Battelle Memorial Institute
import sys
import warnings
import csv
from ppcasefile import ppcasefile
import numpy as np
import pypower.api as pp
import math
import re

def summarize_opf(res):
	bus = res['bus']
	gen = res['gen']

	Pload = bus[:,2].sum()
	Pgen = gen[:,1].sum()
	PctLoss = 100.0 * (Pgen - Pload) / Pgen

	print('success =', res['success'], 'in', res['et'], 'seconds')
	print('Total Gen =', Pgen, ' Load =', Pload, ' Loss =', PctLoss, '%')

	print('bus #, Pd, Qd, Vm, LMP_P, LMP_Q, MU_VMAX, MU_VMIN')
	for row in bus:
		print(int(row[0]),row[2],row[3],row[7],row[13],row[14],row[15],row[16])

	print('gen #, bus, Pg, Qg, MU_PMAX, MU_PMIN, MU_PMAX, MU_PMIN')
	idx = 1
	for row in gen:
		print(idx,int(row[0]),row[1],row[2],row[21],row[22],row[23],row[24])
		++idx

with warnings.catch_warnings():
	ppc = ppcasefile()
	ppopt = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=1)

	gencost = ppc['gencost']
	bus = ppc['bus']
	gen = ppc['gen']
	fncsBus = ppc['FNCS']
	outage = ppc['UnitsOut'][0]

	bus[4,2] = 109.21  # bus loads at 129895 from the TXT file
	bus[8,2] = 151.67
	csv_load = 128.57

	gen[outage[0],7] = 0 # unit 2 is out

	# mimic the FNCS messages coming in at 129895
	unresp = 0.001 * 216.42547809924994
	resp_c0 = 0
	resp_c1 = 1000 * 0.13800244104838633
	resp_c2 = 500 * -0.001692562459244351
	resp_max = 0.001 * 8.8585219007500005
	fncsBus[0][3] = unresp

	# tweaks
	boost = 3.2
	resp_c2 = resp_c2 * boost
	resp_c1 = resp_c1 * boost
	resp_max = resp_max * 10

	# prep and scale for OPF
	scale = float(fncsBus[0][2])
	scaled_unresp = scale * float(fncsBus[0][3])
	bus[6,2] = csv_load + scaled_unresp

	gen[4][9] = -resp_max * scale

	gencost[4][3] = 3
	gencost[4][4] = resp_c2
	gencost[4][5] = resp_c1
	gencost[4][6] = resp_c0 # always 0

	print(gen[4])
	print(gencost[4])
	print(bus[6])

	res = pp.runopf(ppc, ppopt)
	bus = res['bus']
	gen = res['gen']
	print (res['success'], bus[:,2].sum(), bus[6,2], bus[6,7], bus[6,13], bus[6,14], gen[0,1], gen[1,1], gen[2,1], gen[3,1], gen[4,1], sep=',')
#	summarize_opf(res)


