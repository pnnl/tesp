import json
import csv
import numpy as np
import matplotlib.pyplot as plt 
import networkx as nx
import math
 
# some of the system modeling assumptions 
load_pf = 0.98
load_qf = math.sqrt (1.0 - load_pf * load_pf)
#rxfpu = 0.01
#xxfpu = 0.10
ehv_bus_offset = 3000
dispatch = 49502.62 / 98869.50 

def find_bus(arr, n):
	for ln in arr:
		if ln[0] == n:
			return ln
	return None

def find_line(arr, n1, n2):
	for ln in arr:
		if '//' not in ln[0]:
			if int(ln[1]) == n1 and int(ln[2]) == n2:
				return ln
	return None

if __name__ == '__main__':
#   name,bus1,bus2,kV,length[miles],#parallel,r1[Ohms/mile],x1[Ohms/mile],b1[MVAR/mile],ampacity,capacity[MW]
	dlines = np.genfromtxt('RetainedLines.csv', dtype=str, skip_header=1, delimiter=',') # ['U',int,int,float,float,int,float,float,float,float,float], skip_header=1, delimiter=',')
#   bus,lon,lat,load,gen,diff,caps
	dbuses = np.genfromtxt('RetainedBuses.csv', dtype=[int, float, float, float, float, float, float], skip_header=1, delimiter=',')
# idx,bus,mvabase,pmin,qmin,qmax,c2,c1,c0
	dunits = np.genfromtxt('Units.csv', dtype=[int, int, float, float, float, float, float, float, float], skip_header=1, delimiter=',')
# hvbus,mvaxf,rpu,xpu,tap
	dxfmrs = np.genfromtxt('RetainedTransformers.csv', dtype=[int, float, float, float,float], skip_header=1, delimiter=',')

	lbl345 = {}
	lbl138 = {}
	e345 = set()
	e138 = set()
	n345 = set()
	n138 = set()
	lst345 = []
	lst138 = []
	w345 = []
	w138 = []
	graph = nx.Graph()
	for e in dlines:
		if '//' not in e[0]:
			n1 = int(e[1])
			n2 = int(e[2])
			npar = int(e[5])
			graph.add_edge (n1, n2)
			if float(e[3]) > 200.0:
				n138.discard (n1)
				n138.discard (n2)
				n345.add (n1)
				n345.add (n2)
				lbl345[(n1, n2)] = e[0]
				e345.add ((n1, n2))
				lst345.append ((n1, n2))
				w345.append (2.0 * npar)
			else:
				lbl138[(n1, n2)] = e[0]
				n138.add (n1)
				n138.add (n2)
				e138.add ((n1, n2))
				lst138.append ((n1, n2))
				w138.append (1.0 * npar)

	print('There are', len(n138), 'HV buses and', len(e138), 'HV lines retained; ratio=', len(e138) / len(n138))
	print('There are', len(n345), 'EHV buses and', len(e345), 'EHV lines retained; ratio=', len(e345) / len(n345))
	for e1 in e138:
		if e1 in e345:
			print ('HV line', lbl138[e1], 'in parallel with EHV line between', e1)

	# build the PYPOWER case
	swing_bus = -1
	ppcase = {}
	ppcase['version'] = 2
	ppcase['baseMVA'] = 100.0
	ppcase['pf_dc'] = 0
	ppcase['opf_dc'] = 1
	ppcase['bus'] = []
	ppcase['gen'] = []
	ppcase['branch'] = []
	ppcase['areas'] = []
	ppcase['gencost'] = []
	ppcase['FNCS'] = []
	ppcase['UnitsOut'] = []
	ppcase['BranchesOut'] = []
	for n in n345:
		ln = find_bus (dbuses, n)
		bus2 = int(ln[0])   # HV bus
		bus1 = ehv_bus_offset + bus2  # EHV bus
		Pg = float(ln[4])
		if Pg > 0.0:
			if Pg > 9000.0 and swing_bus < 0:  # this should pick up bus number 76, which has the largest generation
				bustype = 3
				swing_bus = bus1
			else:
				bustype = 2
		else:
			bustype = 1
		Pd = float(ln[3])
		Sd = Pd / load_pf
		Qd = Sd * load_qf
		Qs = float(ln[6])
#   	Sxf = math.ceil (Sd / 10.0) * 10.0
#   	rxf = rxfpu * 100.0 / Sxf
#   	xxf = xxfpu * 100.0 / Sxf
		ppcase['bus'].append ([bus1, bustype, 0, 0, 0, 0, 1, 1, 0, 345, 1, 1.1, 0.9]) # no load on 345 kV
		ppcase['bus'].append ([bus2, 1, Pd, Qd, 0, Qs, 1, 1, 0, 138, 1, 1.1, 0.9])
#   	ppcase['branch'].append ([bus1, bus2, rxf, xxf, 0.0, Sxf, Sxf, Sxf, 0.0, 0.0, 1, -360.0, 360.0]) # station transformer
	for n in n138:
		if n not in n345:
			ln = find_bus (dbuses, n)
			bus1 = int(ln[0])   # HV bus
			Pg = float(ln[4])
			if Pg > 0.0:
				bustype = 2
			else:
				bustype = 1
			Pd = float(ln[3])
			Sd = Pd / load_pf
			Qd = Sd * load_qf
			Qs = float(ln[6])
			ppcase['bus'].append ([bus1, bustype, Pd, Qd, 0, Qs, 1, 1, 0, 138, 1, 1.1, 0.9])
	Zbase = 345.0 * 345.0 / 100.0
	for (n1, n2) in e345:
		ln = find_line (dlines, n1, n2)
		bus1 = ehv_bus_offset + int(ln[1])
		bus2 = ehv_bus_offset + int(ln[2])
		dist = float(ln[4])
		npar = float(ln[5])
		r1 = dist * float(ln[6]) / Zbase / npar
		x1 = dist * float(ln[7]) / Zbase / npar
		b1 = dist * float(ln[8]) * npar / 100.0
		rated = npar * float(ln[10])  # this is MW, not amps
		ppcase['branch'].append ([bus1, bus2, r1, x1, b1, rated, rated, rated, 0.0, 0.0, 1, -360.0, 360.0])
	Zbase = 138.0 * 138.0 / 100.0
	for (n1, n2) in e138:
		ln = find_line (dlines, n1, n2)
		bus1 = int(ln[1])
		bus2 = int(ln[2])
		dist = float(ln[4])
		npar = float(ln[5])
		r1 = dist * float(ln[6]) / Zbase / npar
		x1 = dist * float(ln[7]) / Zbase / npar
		b1 = dist * float(ln[8]) * npar / 100.0
		rated = npar * float(ln[10])  # this is MW, not amps
		ppcase['branch'].append ([bus1, bus2, r1, x1, b1, rated, rated, rated, 0.0, 0.0, 1, -360.0, 360.0])
	for ln in dunits:
		idx = int(ln[0])
		n1 = int(ln[1])
		if n1 in n345:
			n1 = ehv_bus_offset + n1
		Sg = float(ln[2])
		Pg = Sg * dispatch
		Pmin = float(ln[3])
		if Pg < Pmin:
			Pg = Pmin
		if n1 == swing_bus:
			print ('setting Pg from', Pg, 'to 0 at swing bus', swing_bus)
			Pg = 0.0
		Qmin = float(ln[4])
		Qmax = float(ln[5])
		c2 = float(ln[6])
		c1 = float(ln[7])
		c0 = float(ln[8])
		ppcase['gen'].append ([n1, Pg, 0.0, Qmax, Qmin, 1.0, Sg, 1, Sg, Pmin, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
		ppcase['gencost'].append ([2, 0, 0, 3, c2, c1, c0])
	for ln in dxfmrs:
		bus1 = int(ln[0])
		bus2 = ehv_bus_offset + bus1
		Sxf = float(ln[1])
		rxf = float(ln[2]) * 100.0 / Sxf
		xxf = float(ln[3]) * 100.0 / Sxf
		tap = float(ln[4])
		ppcase['branch'].append ([bus1, bus2, rxf, xxf, 0.0, Sxf, Sxf, Sxf, tap, 0.0, 1, -360.0, 360.0]) # station transformer

	fp = open ('ercot_200.json', 'w')
	json.dump (ppcase, fp, indent=2)
	fp.close ()

	print ('swing bus is', swing_bus)

 # draw the retained HV/EHV network

	xy = {}
	lblbus345 = {}
	lblbus138 = {}
	for b in dbuses:
		xy[b[0]] = [b[1], b[2]]
		if b[0] in n345:
			lblbus345[b[0]] = str(b[0]) + ':' + str(int(b[5]))
		else:
			lblbus138[b[0]] = str(b[0]) + ':' + str(int(b[5]))

	nx.draw_networkx_nodes (graph, xy, nodelist=list(n345), node_color='k', node_size=80, alpha=0.3)
	nx.draw_networkx_nodes (graph, xy, nodelist=list(n138), node_color='b', node_size=20, alpha=0.3)
	nx.draw_networkx_edges (graph, xy, edgelist=lst345, edge_color='r', width=w345, alpha=0.8)
#   nx.draw_networkx_edges (graph, xy, edgelist=lst345, edge_color='r', width=1, alpha=0.3)
	nx.draw_networkx_edges (graph, xy, edgelist=lst138, edge_color='b', width=w138, alpha=0.8)
	nx.draw_networkx_labels (graph, xy, lblbus345, font_size=12, font_color='g')
	nx.draw_networkx_labels (graph, xy, lblbus138, font_size=12, font_color='g')
#   nx.draw_networkx_edge_labels (graph, xy, edge_labels=lbl345, label_pos=0.5, font_color='m', font_size=6)
#   nx.draw_networkx_edge_labels (graph, xy, edge_labels=lbl138, label_pos=0.5, font_color='k', font_size=6)

	plt.title ('Graph of Retained EHV and HV Lines')
	plt.xlabel ('Longitude [deg]')
	plt.ylabel ('Latitude [deg N]')
	plt.grid(linestyle='dotted')
	plt.show()


