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

	bus[4,2] = 97.124  # column 2, bus loads at 165000 from the TXT file
	bus[8,2] = 134.89  # column 3
	csv_load = 110.28  # column 1

#	gen[outage[0],7] = 0 # unit 2 is out

	scale = float(fncsBus[0][2])
	# mimic the FNCS messages coming in at 165000 for MW, prep and scale for OPF
	unresp = 0.17470563 * scale
	resp_c0 = -0.0128 * scale
	resp_c1 = 50.12054761
	resp_c2 = -174.10683 / scale
	resp_max = 0.13305073 * scale

	fncsBus[0][3] = unresp

	bus[6,2] = csv_load + unresp

	gen[4][9] = -resp_max

	gencost[4][3] = 3
	gencost[4][4] = -resp_c2
	gencost[4][5] = resp_c1
	gencost[4][6] = -resp_c0 # should always be 0

	print('scaled unresp, max resp, c2, c1, c0', unresp, resp_max, resp_c2, resp_c1, resp_c0)
	print('dispatch load', gen[4])
	print('dispatch cost', gencost[4])
	print('dispatch bus', bus[6])

	res = pp.runopf(ppc, ppopt)
	bus = res['bus']
	gen = res['gen']
	resp = -gen[4,1]

	print (res['success'], bus[:,2].sum() + resp, bus[6,2], bus[6,7], bus[6,13], gen[0,1], gen[1,1], gen[2,1], gen[3,1], gen[4,1], sep=',')
#	summarize_opf(res)

#	res = pp.runpf(ppc, ppopt)
#	print (res[0]['success'])

