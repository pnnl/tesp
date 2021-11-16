#  Copyright (C) 2017-2021 Battelle Memorial Institute
# file: pprun.py
import json
import sys
import warnings
import numpy as np
import pypower.api as pp
import math

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

def load_json_case(fname):
	lp = open (fname).read()
	ppc = json.loads(lp)
	ppc['bus'] = np.array (ppc['bus'])
	ppc['gen'] = np.array (ppc['gen'])
	ppc['branch'] = np.array (ppc['branch'])
	ppc['areas'] = np.array (ppc['areas'])
	ppc['gencost'] = np.array (ppc['gencost'])
	ppc['FNCS'] = np.array (ppc['FNCS'])
	ppc['UnitsOut'] = np.array (ppc['UnitsOut'])
	ppc['BranchesOut'] = np.array (ppc['BranchesOut'])
	return ppc

ppc = load_json_case('./Case1/ppcase.json')
#print (ppc)
StartTime = ppc['StartTime']
tmax = int(ppc['Tmax'])
period = int(ppc['Period'])
dt = int(ppc['dt'])
gencost = ppc['gencost']
fncsBus = ppc['FNCS']
gen = ppc['gen']
ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'])
ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'])

print (ppc['UnitsOut'])
print (ppc['BranchesOut'])

for row in ppc['UnitsOut']:
  print ('unit  ', row[0], 'off from', row[1], 'to', row[2], flush=True)
for row in ppc['BranchesOut']:
  print ('branch', row[0], 'out from', row[1], 'to', row[2], flush=True)

res = pp.runopf(ppc, ppopt_market)
summarize_opf (res)

rpf = pp.runpf(ppc, ppopt_regular)
summarize_opf (rpf[0])

