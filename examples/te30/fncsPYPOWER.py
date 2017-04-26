#	Copyright (C) 2017 Battelle Memorial Institute
import json
import sys
import warnings
import csv
import fncs
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

def make_dictionary(ppc, rootname):
	fncsBuses = {}
	generators = {}
	unitsout = []
	branchesout = []
	bus = ppc['bus']
	gen = ppc['gen']
	cost = ppc['gencost']
	fncsBus = ppc['FNCS']
	units = ppc['UnitsOut']
	branches = ppc['BranchesOut']

	for i in range (gen.shape[0]):
		busnum = gen[i,0]
		bustype = bus[busnum-1,1]
		if bustype == 1:
			bustypename = 'pq'
		elif bustype == 2:
			bustypename = 'pv'
		elif bustype == 3:
			bustypename = 'swing'
		else:
			bustypename = 'unknown'
		generators[str(i+1)] = {'bus':int(busnum),'bustype':bustypename,'Pnom':float(gen[i,1]),'Pmax':float(gen[i,8]),'genfuel':'tbd','gentype':'tbd',
			'StartupCost':float(cost[i,1]),'ShutdownCost':float(cost[i,2]), 'c2':float(cost[i,4]), 'c1':float(cost[i,5]), 'c0':float(cost[i,6])}

	for i in range (fncsBus.shape[0]):
		busnum = int(fncsBus[i,0])
		busidx = busnum - 1
		fncsBuses[str(busnum)] = {'Pnom':float(bus[busidx,2]),'Qnom':float(bus[busidx,3]),'area':int(bus[busidx,6]),'zone':int(bus[busidx,10]),
			'ampFactor':float(fncsBus[i,2]),'GLDsubstations':[fncsBus[i,1]]}

	for i in range (units.shape[0]):
		unitsout.append ({'unit':int(units[i,0]),'tout':int(units[i,1]),'tin':int(units[i,2])})

	for i in range (branches.shape[0]):
		branchesout.append ({'branch':int(branches[i,0]),'tout':int(branches[i,1]),'tin':int(branches[i,2])})

	dp = open (rootname + "_m_dict.json", "w")
	ppdict = {'baseMVA':ppc['baseMVA'],'fncsBuses':fncsBuses,'generators':generators,'UnitsOut':unitsout,'BranchesOut':branchesout}
	print (json.dumps(ppdict), file=dp, flush=True)
	dp.close()

def parse_mva(arg):
	tok = arg.strip('+-; MWVAKdrij')
	vals = re.split(r'[\+-]+', tok)
	if len(vals) < 2: # only a real part provided
		vals.append('0')
	vals = [float(v) for v in vals]

	if '-' in tok:
		vals[1] *= -1.0
	if arg.startswith('-'):
		vals[0] *= -1.0

	if 'd' in arg:
		vals[1] *= (math.pi / 180.0)
		p = vals[0] * math.cos(vals[1])
		q = vals[0] * math.sin(vals[1])
	elif 'r' in arg:
		p = vals[0] * math.cos(vals[1])
		q = vals[0] * math.sin(vals[1])
	else:
		p = vals[0]
		q = vals[1]

	if 'KVA' in arg:
		p /= 1000.0
		q /= 1000.0
	elif 'MVA' in arg:
		p *= 1.0
		q *= 1.0
	else:  # VA
		p /= 1000000.0
		q /= 1000000.0

	return p, q

with warnings.catch_warnings():
	warnings.simplefilter("ignore") # TODO - pypower is using NumPy doubles for integer indices
	#warnings.filterwarnings("ignore",category=DeprecationWarning)

	if len(sys.argv) == 5:
		rootname = sys.argv[1]
		StartTime = sys.argv[2]
		tmax = int(sys.argv[3])
		dt = int(sys.argv[4])
	elif len(sys.argv) == 1:
		rootname = 'ppcase'
		StartTime = "2013-07-01 00:00:00"
		dt = 3600
		tmax = 2 * 24 * 3600
	else:
		print ('usage: python fncsPYPOWER.py [rootname StartTime tmax dt]')
		sys.exit()

	ppc = ppcasefile()
	make_dictionary(ppc, rootname)

	bus_mp = open ("bus_" + rootname + "_metrics.json", "w")
	gen_mp = open ("gen_" + rootname + "_metrics.json", "w")
	sys_mp = open ("sys_" + rootname + "_metrics.json", "w")
	bus_meta = {'LMP_P':{'units':'USD/kwh','index':0},'LMP_Q':{'units':'USD/kvarh','index':1},
		'PD':{'units':'MW','index':2},'QD':{'units':'MVAR','index':3},'Vang':{'units':'deg','index':4},
		'Vmag':{'units':'pu','index':5},'Vmax':{'units':'pu','index':6},'Vmin':{'units':'pu','index':7}}
	gen_meta = {'Pgen':{'units':'MW','index':0},'Qgen':{'units':'MVAR','index':1},'LMP_P':{'units':'USD/kwh','index':2}}
	sys_meta = {'Ploss':{'units':'MW','index':0},'Converged':{'units':'true/false','index':1}}
	bus_metrics = {'Metadata':bus_meta,'StartTime':StartTime}
	gen_metrics = {'Metadata':gen_meta,'StartTime':StartTime}
	sys_metrics = {'Metadata':sys_meta,'StartTime':StartTime}

	gencost = ppc['gencost']
	fncsBus = ppc['FNCS']
	ppopt = pp.ppoption(VERBOSE=0, OUT_ALL=0) # TODO - the PF_DC option doesn't seem to work
	loads = np.loadtxt('NonGLDLoad.txt', delimiter=',')

	outage = ppc['UnitsOut'][0]
	print ('unit', outage[0], 'off from', outage[1], 'to', outage[2], flush=True)

	nloads = loads.shape[0]
	ts = 0
	tnext = 0

	op = open (rootname + '.csv', 'w')
	print ('t[s],Converged,Pload,P7,V7,LMP_P7,LMP_Q7,Pgen1,Pgen2,Pgen3,Pgen4', file=op, flush=True)
	fncs.initialize()

#	ts = -dt
#	while ts <= tmax:
#		ts += dt

	while ts <= tmax:
		print ("looping", ts, tnext, tmax, flush=True)
		if ts >= tnext:
			idx = int (ts / 300) % nloads
			bus = ppc['bus']
			gen = ppc['gen']
			bus[6,2] = loads[idx,0]
			bus[4,2] = loads[idx,1]
			bus[8,2] = loads[idx,2]
			if ts >= outage[1] and ts <= outage[2]:
				gen[outage[0],7] = 0
			else:
				gen[outage[0],7] = 1
			for row in ppc['FNCS']:
				newload = float(row[2]) * float(row[3])
				newidx = int(row[0]) - 1
				print ('  GLD load', newload, 'at', newidx)
				bus[newidx,2] += newload
			res = pp.runopf(ppc, ppopt)
			bus = res['bus']
			gen = res['gen']
			Pload = bus[:,2].sum()
			Pgen = gen[:,1].sum()
			Ploss = Pgen - Pload
			print ('  ', res['success'], bus[:,2].sum(), flush=True)
			print (ts, res['success'], bus[:,2].sum(), bus[6,2], bus[6,7], bus[6,13], bus[6,14], gen[0,1], gen[1,1], gen[2,1], gen[3,1], sep=',', file=op, flush=True)
			fncs.publish('LMP_B7', 0.001 * bus[6,13])
			fncs.publish('three_phase_voltage_B7', 1000.0 * bus[6,7] * bus[6,9])
			print('  publishing LMP=', 0.001 * bus[6,13], 'vpos=', 1000.0 * bus[6,7] * bus[6,9], flush=True)
			# update the metrics
			sys_metrics[str(ts)] = {rootname:[Ploss,res['success']]}
			bus_metrics[str(ts)] = {}
			for i in range (fncsBus.shape[0]):
				busnum = int(fncsBus[i,0])
				busidx = busnum - 1
				row = bus[busidx].tolist()
				bus_metrics[str(ts)][str(busnum)] = [row[13]*0.001,row[14]*0.001,row[2],row[3],row[8],row[7],row[11],row[12]]
			gen_metrics[str(ts)] = {}
			for i in range (gen.shape[0]):
				row = gen[i].tolist()
				busidx = int(row[0] - 1)
				gen_metrics[str(ts)][str(i+1)] = [row[1],row[2],float(bus[busidx,13])*0.001]
			tnext += dt
			if tnext > tmax:
				print ('breaking out at',tnext,flush=True)
				break
		ts = fncs.time_request(tnext)
		events = fncs.get_events()
		for key in events:
			substation = key.decode()
			GLDload = parse_mva (fncs.get_value(key).decode())
#			print ('  **', ts, substation, GLDload)
			for row in fncsBus:
				if substation == row[1]:
#					print('    assigning',substation,GLDload)
					row[3] = GLDload[0]

#	summarize_opf(res)
	print ('writing metrics', flush=True)
	print (json.dumps(bus_metrics), file=bus_mp, flush=True)
	print (json.dumps(gen_metrics), file=gen_mp, flush=True)
	print (json.dumps(sys_metrics), file=sys_mp, flush=True)
	print ('closing files', flush=True)
	bus_mp.close()
	gen_mp.close()
	sys_mp.close()
	op.close()
	print ('finalizing FNCS', flush=True)
	fncs.finalize()

