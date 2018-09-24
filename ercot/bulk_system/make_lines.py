import json
import numpy as np
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt 
import networkx as nx
import math 

# units are kv, ohms and mvar per mile, amperes, MW
lineparameters = [
	{'kv':345.0, 'r1':0.070, 'x1':0.593, 'b1':0.8616, 'amps':1814.0, 'mw':1084.0},
	{'kv':138.0, 'r1':0.233, 'x1':0.789, 'b1':0.1039, 'amps':655.0, 'mw':157.0}]

fuels = ['Conventional Steam Coal',
				 'Natural Gas Fired Combined Cycle',
				 'Natural Gas Fired Combustion Engine',
				 'Natural Gas Internal Combustion Engine',
				 'Natural Gas Steam Turbine',
				 'Nuclear',
				 'Onshore Wind Turbine',
				 'Solar Photovoltaic']

# there will be a 138-kV line between each pair of buses in the Delaunay simplices
# 	Try a maximum 138-kV line length to automatically prune unrealistic 'slivers'
max138 = 100.0
# there will be a 345-kV line between each pair in a reduced set of buses that have
# 	a difference between bus load and bus generation of at least 'thresh' MW
thresh = 500.0

def printcsv (ln, n1, n2, xy, npar, kv, parmrow, fp):
	x1 = xy[n1][0]
	y1 = xy[n1][1]
	x2 = xy[n2][0]
	y2 = xy[n2][1]
	row = lineparameters[parmrow]
	print (ln, n1, n2, kv, '{:.2f}'.format(distance(y1, x1, y2, x2)), npar,
				 row['r1'], row['x1'], row['b1'], row['amps'], row['mw'], sep=',', file=fp)

# latitude is y, longitude is x
def distance (lat1, lon1, lat2, lon2):
	radius = 3959.0 # miles

	dlat = math.radians(lat2-lat1)
	dlon = math.radians(lon2-lon1)
	a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
			* math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
	d = radius * c
	return d

if __name__ == '__main__':
	lp = open ('200NodesData.json').read()
	busdict = json.loads(lp)
	nbus = len(busdict)
	xy = [None] * nbus
	pwr = [None] * nbus
	for row in busdict:
		load = 0.0
		gen = 0.0
		n = int(row['bus'])
		if 'weightdict' in row:
			for val in row['weightdict']:
				if 'Load' in val:
					load = load + float (val['Load'])
				for tok in fuels:
					if tok in val:
						gen = gen + float (val[tok])
		xy[n] = [float (row['coordinates'][1]), float (row['coordinates'][0])]
		pwr[n] = [load, gen, abs(load-gen)]

	load = 0.0
	gen = 0.0
	for n in range(nbus):
		load = load + pwr[n][0]
		gen = gen + pwr[n][1]
	print ('total load:', '{:.2f}'.format(load), 'generation:', '{:.2f}'.format(gen))

	# define the 138-kV lines
	p138 = np.array (xy)
	tri138 = Delaunay(p138, qhull_options = 'QJ')

	#define the 345-kV lines
	nehv = 0
	for n in range(nbus):
		if pwr[n][2] >= thresh:
			nehv = nehv + 1
	ehv = [None] * nehv
	ehvbus = [None] * nehv
	nehv = 0
	for n in range(nbus):
		if pwr[n][2] >= thresh:
			ehv[nehv] = [xy[n][0], xy[n][1]]
			ehvbus[nehv] = n
			nehv = nehv + 1
	p345 = np.array (ehv)
	tri345 = Delaunay(p345, qhull_options = 'QJ')

	plt.triplot(p138[:,0], p138[:,1], tri138.simplices.copy())
	plt.triplot(p345[:,0], p345[:,1], tri345.simplices.copy(), color = 'red')
	plt.plot(p138[:,0], p138[:,1], 'o')
	plt.plot(p345[:,0], p345[:,1], 'r+')
	plt.title ('Delaunay Tesselation of All Buses')
	plt.xlabel ('Longitude [deg]')
	plt.ylabel ('Latitude [deg N]')
	plt.grid(linestyle='dotted') 
	plt.show()

	print ('there are', nbus, 'hv buses and', len(tri138.simplices), 'hv triangles')
	print ('there are', nehv, 'ehv buses and', len(tri345.simplices), 'ehv triangles')

	# create a set for edges that are indexes of the points
	e138 = set() 
	n138 = set()
	for n in range(tri138.nsimplex): 
		n0 = tri138.simplices[n,0]
		n1 = tri138.simplices[n,1]
		n2 = tri138.simplices[n,2]
		n138.add(n0)
		n138.add(n1)
		n138.add(n2)
		# filter out the 138-kV lines that seem too long
		if distance (xy[n0][1], xy[n0][0], xy[n1][1], xy[n1][0]) <= max138:
			# sorting the vertices to avoid adding duplicate edges to the set
			edge = sorted([n0, n1]) 
			e138.add((edge[0], edge[1])) 
		if distance (xy[n0][1], xy[n0][0], xy[n2][1], xy[n2][0]) <= max138:
			edge = sorted([n0, n2]) 
			e138.add((edge[0], edge[1])) 
		if distance (xy[n1][1], xy[n1][0], xy[n2][1], xy[n2][0]) <= max138:
			edge = sorted([n1, n2]) 
			e138.add((edge[0], edge[1])) 

	e345 = set() 
	n345 = set()
	for n in range(tri345.nsimplex): 
		n0 = ehvbus [tri345.simplices[n,0]]
		n1 = ehvbus [tri345.simplices[n,1]]
		n2 = ehvbus [tri345.simplices[n,2]]
		# keep the lists of 138-kV and 345-kV buses mutually exclusive
		n138.discard (n0)
		n138.discard (n1)
		n138.discard (n2)
		n345.add (n0)
		n345.add (n1)
		n345.add (n2)
		edge = sorted([n0, n1]) 
		e345.add((edge[0], edge[1])) 
		edge = sorted([n0, n2]) 
		e345.add((edge[0], edge[1])) 
		edge = sorted([n1, n2]) 
		e345.add((edge[0], edge[1])) 

	# make a graph based on the Delaunay triangulation edges 
	graph = nx.Graph(list(e345))
	graph.add_edges_from (list(e138)) 
	print('there are', len(e138), 'HV lines and', len(e345), 'EHV lines retained')
	
	pos = dict(zip(range(nbus), xy))
#	labels = dict(zip(range(nbus), [str(x) for x in range(nbus)]))
	lbl138 = dict(zip([n for n in n138], [str(b) for b in n138]))
	lbl345 = dict(zip([n for n in n345], [str(b) for b in n345]))
	nx.draw_networkx_nodes (graph, pos, nodelist=list(n345), node_color='r', node_size=80, alpha=0.3) 
	nx.draw_networkx_edges (graph, pos, edgelist=list(e345), edge_color='r', width=2, alpha=0.8)
	nx.draw_networkx_nodes (graph, pos, nodelist=list(n138), node_color='b', node_size=20, alpha=0.3) 
	nx.draw_networkx_edges (graph, pos, edgelist=list(e138), edge_color='b', width=1, alpha=0.8)
	nx.draw_networkx_labels (graph, pos, lbl345, font_size=10, font_weight='bold')
	nx.draw_networkx_labels (graph, pos, lbl138, font_size=8)
	plt.title ('Graph of Retained EHV and HV Lines')
	plt.xlabel ('Longitude [deg]')
	plt.ylabel ('Latitude [deg N]')
	plt.grid(linestyle='dotted') 
	plt.show() 

	fp = open ('Buses.csv', 'w')
	print('bus', 'lon', 'lat', 'load', 'gen', 'diff', sep=',', file=fp)
	for n in range(nbus):
		print (n, xy[n][0], xy[n][1], '{:.2f}'.format(pwr[n][0]), '{:.2f}'.format(pwr[n][1]), 
					 '{:.2f}'.format(pwr[n][2]), sep=',', file=fp)
	fp.close ()

	fp = open ('Lines.csv', 'w')
	print('name', 'bus1', 'bus2', 'kV', 'length[miles]', '#parallel', 'r1[Ohms/mile]', 
				'x1[Ohms/mile]', 'b1[MVAR/mile]', 'ampacity', 'capacity[MW]', sep=',', file=fp)
	i = 1
	for e in e345:
		printcsv ('ehv' + str(i), e[0], e[1], xy, 1, 345.0, 0, fp)
		i = i + 1
	i = 1
	for e in e138:
		printcsv ('hv' + str(i), e[0], e[1], xy, 1, 138.0, 1, fp)
		i = i + 1
	fp.close ()




