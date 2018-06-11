#	Copyright (C) 2017 Battelle Memorial Institute
# file: matpower_dict.py
# tested on case9_9Subst.m
# it's assumed that whenever a section starts, eg mpc.buses, 
#    1) actual data begins on the next line
#    2) only one object entry per line
# further, only 2nd-order polynomial gencost models are parsed
import json;
import sys;

def matpower_dict (nameroot):
	ip = open (nameroot + ".m", "r")
	op = open (nameroot + "_m_dict.json", "w")

	baseMVA = 1
	ampFactor = 1
	fncsBuses = {}
	subBuses = {}
	# generators have their bus number
	generators = {}
	# gencosts have 1-1 correspondence to generators, but no direct input of bus number
	gencosts = {}
	idxGen = 1 # used as a key in Python, not an array index
	buses = {}
	inSubNameFNCS = False
	inBusFNCS = False
	inBus = False
	inGen = False
	inGencost = False

	for line in ip:
		lst = line.split()
		if inGencost == True and len(lst) > 6:
			startup = float(lst[1].strip(" ").strip(";").strip("]"))
			shutdown = float(lst[2].strip(" ").strip(";").strip("]"))
			c2 = float(lst[4].strip(" ").strip(";").strip("]"))
			c1 = float(lst[5].strip(" ").strip(";").strip("]"))
			c0 = float(lst[6].strip(" ").strip(";").strip("]"))
			gencosts[idxGen] = {'StartupCost':startup,'ShutdownCost':shutdown,'c2':c2,'c1':c1,'c0':c0}
			idxGen += 1
		if inGen == True and len(lst) > 8:
			bus = int(lst[0].strip(" ").strip(";").strip("]"))
			pnom = float(lst[1].strip(" ").strip(";").strip("]"))
			pmax = float(lst[8].strip(" ").strip(";").strip("]"))
			genfuel = "gas"
			gentype = "combinedcycle"
			generators[idxGen] = {'bus':bus,'bustype':'pv','Pnom':pnom,'Pmax':pmax,'StartupCost':0,'ShutdownCost':0,'c2':0,'c1':0,'c0':0,'genfuel':genfuel,'gentype':gentype}
			idxGen += 1
		if inBus == True and len(lst) > 3:
			bus = int(lst[0].strip(" ").strip(";").strip("]"))
			bustype = int(lst[1].strip(" ").strip(";").strip("]"))
			if bustype == 1:
				bustypename = 'pq'
			elif bustype == 2:
				bustypename = 'pv'
			elif bustype == 3:
				bustypename = 'swing'
			else:
				bustypename = 'unknown'
			pnom = float(lst[2].strip(" ").strip(";").strip("]"))
			qnom = float(lst[3].strip(" ").strip(";").strip("]"))
			busarea = float(lst[6].strip(" ").strip(";").strip("]"))
			buszone = float(lst[10].strip(" ").strip(";").strip("]"))
			buses[bus] = {'bustype':bustypename,'Pnom':pnom,'Qnom':qnom,'area':busarea,'zone':buszone}
		if inSubNameFNCS == True and len(lst) > 1:
			name = lst[0].strip(" ").strip(";").strip("]")
			bus = int(lst[1].strip(" ").strip(";").strip("]"))
			subBuses[name] = bus;
		if inBusFNCS == True:
			bus = int(lst[0].strip(" ").strip(";").strip("]"))
			fncsBuses[bus] = {'Pnom':0,'Qnom':0,'GLDsubstations':[]}
		if len(lst) > 2:
			if lst[0] == "mpc.SubNameFNCS":
				inSubNameFNCS = True
			if lst[0] == "mpc.BusFNCS":
				inBusFNCS = True
			if lst[0] == "mpc.bus":
				inBus = True
			if lst[0] == "mpc.gen":
				inGen = True
				idxGen = 1
			if lst[0] == "mpc.gencost":
				inGencost = True
				idxGen = 1
			if lst[0] == "mpc.baseMVA":
				baseMVA = float(lst[2].strip(" ").strip(";")) * 1.0
			if lst[0] == "mpc.ampFactor":
				ampFactor = float(lst[2].strip(" ").strip(";")) * 1.0
		if line.find("];") >= 0:
			inSubNameFNCS = False
			inBusFNCS = False
			inBus = False
			inGen = False
			inGencost = False

	# backfill the generators with gencosts and bustypes
	for key, val in generators.items():
		cost = gencosts[key]
		row = buses[key]
		val['bustype'] = row['bustype']
		val['StartupCost'] = cost['StartupCost']
		val['ShutdownCost'] = cost['ShutdownCost']
		val['c2'] = cost['c2']
		val['c1'] = cost['c1']
		val['c0'] = cost['c0']

	# backfill the fncsBuses with nominal loads and GridLAB-D substation names
	for key, val in fncsBuses.items():
		row = buses[key]
		val['Pnom'] = row['Pnom']
		val['Qnom'] = row['Qnom']
		val['area'] = row['area']
		val['zone'] = row['zone']
	for key, val in subBuses.items():
		(fncsBuses[val]['GLDsubstations']).append(key)

	matpower = {'baseMVA':baseMVA,'ampFactor':ampFactor,'fncsBuses':fncsBuses,'generators':generators}
	print (json.dumps(matpower), file=op)

	ip.close()
	op.close()
