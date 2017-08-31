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

	gencost = ppc['gencost']
	ppopt = pp.ppoption(VERBOSE=0, OUT_ALL=0) # , PF_DC=1)
	bus = ppc['bus']
	gen = ppc['gen']

	bid = [3.7799999999999998, 100.17391892147002, -0.00017606033522744592, 0.04777692038155331, 79.037081078529994]

	bus[4,2] = 117.49  # bus 5 and 9 loads at 56400 from the TXT file
	bus[8,2] = 163.18

	bus[6,2] = 272.97  # GLD at 56400

	unresp = bid[1] * 0.8  # UNRESP at 56400
	resp_a = bid[2] * 10 / 0.8
	resp_b = bid[3] * -10
	resp_max = bid[4] * 0.8
	print (unresp, resp_a, resp_b, resp_max)

	bus[6,2] = unresp
	gen[4,9] = -resp_max
	gencost[4,5] = 1000 * resp_a
	gencost[4,6] = 0 # resp_b
	print(gen)
	print(gencost)

	res = pp.runopf(ppc, ppopt)
	bus = res['bus']
	gen = res['gen']
	print (res['success'], bus[:,2].sum(), bus[6,2], bus[6,7], bus[6,13], bus[6,14], gen[0,1], gen[1,1], gen[2,1], gen[3,1], sep=',')
	summarize_opf(res)


