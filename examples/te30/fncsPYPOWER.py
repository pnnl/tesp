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
#import cProfile
#import pstats

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

def main_loop():
	if len(sys.argv) == 6:
		rootname = sys.argv[1]
		StartTime = sys.argv[2]
		tmax = int(sys.argv[3])
		period = int(sys.argv[4])  # market clearing period
		dt = int(sys.argv[5])      # time step for bid and load updates
	else:
		print ('usage: python fncsPYPOWER.py [rootname StartTime tmax period dt]')
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
	ppopt = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=1)
	loads = np.loadtxt('NonGLDLoad.txt', delimiter=',')

	outage = ppc['UnitsOut'][0]
	print ('unit', outage[0], 'off from', outage[1], 'to', outage[2], flush=True)

	nloads = loads.shape[0]
	ts = 0
	tnext_opf = -dt

	op = open (rootname + '.csv', 'w')
	print ('t[s],Converged,Pload,P7,V7,LMP_P7,LMP_Q7,Pgen1,Pgen2,Pgen3,Pgen4,Pdisp', file=op, flush=True)
	fncs.initialize()

	# transactive load components
	csv_load = 0
	scaled_unresp = 0
	scaled_resp = 0
	resp_c0 = 0
	resp_c1 = 0
	resp_c2 = 0
	resp_max = 0
	gld_load = 0 # this is the actual

	while ts <= tmax:
		if ts >= tnext_opf:  # expecting to solve opf one dt before the market clearing period ends, so GridLAB-D has time to use it
			idx = int ((ts + dt) / period) % nloads
			bus = ppc['bus']
			gen = ppc['gen']
			csv_load = loads[idx,0]
			bus[4,2] = loads[idx,1]
			bus[8,2] = loads[idx,2]
			if ts >= outage[1] and ts <= outage[2]:
				gen[outage[0],7] = 0
			else:
				gen[outage[0],7] = 1
			bus[6,2] = csv_load
			for row in ppc['FNCS']:
				scaled_unresp = float(row[2]) * float(row[3])
				newidx = int(row[0]) - 1
				bus[newidx,2] += scaled_unresp
			res = pp.runopf(ppc, ppopt)
			bus = res['bus']
			gen = res['gen']
			Pload = bus[:,2].sum()
			Pgen = gen[:,1].sum()
			Ploss = Pgen - Pload
			scaled_resp = -1.0 * gen[4,1]
			print (ts, res['success'], bus[:,2].sum(), bus[6,2], bus[6,7], bus[6,13], bus[6,14], gen[0,1], gen[1,1], gen[2,1], gen[3,1], scaled_resp, sep=',', file=op, flush=True)
			fncs.publish('LMP_B7', 0.001 * bus[6,13])
			fncs.publish('three_phase_voltage_B7', 1000.0 * bus[6,7] * bus[6,9])
			print('**OPF', ts, csv_load, scaled_unresp, scaled_resp, bus[6,2], gld_load, 'LMP', 0.001 * bus[6,13])
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
			tnext_opf += period
			if tnext_opf > tmax:
				print ('breaking out at',tnext_opf,flush=True)
				break
		# apart from the OPF, keep loads updated
		ts = fncs.time_request(ts + dt)
		events = fncs.get_events()
		new_bid = False
		for key in events:
			topic = key.decode()
			if topic == 'UNRESPONSIVE_KW':
				unresp_load = 0.001 * float(fncs.get_value(key).decode())
				fncsBus[0][3] = unresp_load # poke unresponsive estimate into the bus load slot
				new_bid = True
			elif topic == 'RESPONSIVE_MAX_KW':
				resp_max = 0.001 * float(fncs.get_value(key).decode())
				new_bid = True
			elif topic == 'RESPONSIVE_M':
				resp_c2 = 1000.0 * 0.5 * float(fncs.get_value(key).decode())
				new_bid = True
			elif topic == 'RESPONSIVE_B':
				resp_c1 = 1000.0 * float(fncs.get_value(key).decode())
				new_bid = True
			elif topic == 'UNRESPONSIVE_PRICE': # not actually used
				unresp_price = float(fncs.get_value(key).decode())
				new_bid = True
			else:
				gld_load = parse_mva (fncs.get_value(key).decode()) # actual value, may not match unresp + resp load
				# actual_load = gld_load[0] * fncsBus[0][2]
				print('     ', ts, gld_load, 'vs', bus[6,2] - gen[4,1])
		# poke responsive bid into the dispatchable load and cost slots
		if new_bid == True:
			gen[4][9] = -resp_max
			gencost[4][3] = 3
			gencost[4][4] = resp_c2
			gencost[4][5] = resp_c1
			gencost[4][6] = resp_c0 # always 0
			print('**Bid', ts, unresp_load, resp_max, resp_c2, resp_c1)

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

main_loop()

#with warnings.catch_warnings():
#	warnings.simplefilter("ignore") # TODO - pypower is using NumPy doubles for integer indices

#	profiler = cProfile.Profile ()
#	profiler.runcall (main_loop)
#	stats = pstats.Stats(profiler)
#	stats.strip_dirs()
#	stats.sort_stats('cumulative')
#	stats.print_stats()
	


