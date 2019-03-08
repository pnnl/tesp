"""Given a feeder graph as a JSON, generates a synthetic communication graph
corresponding to that feeder. Each node in the feeder with an (x,y) coordinate
has a corresponding node in the communication graph. The edge set of the
communication graph is obtained by applying the graph "rewiring" algorithm
(see https://en.wikipedia.org/wiki/Degree-preserving_randomization) to the edge
set of the feeder graph. Applying the rewiring procedure to generate synthetic
communication networks was suggested by Korkali et. al. in

"Reducing Cascading Failure Risk by Increasing Infrastructure Network
Interdependence" Scientific Reports volume 7, Article number: 44499 (2017)

However, we make two modifications to the rewiring scheme:
(1) rewiring is constrained to maintain the connectedness of the graph
(2) the user can optionally specify a maximum edge length which cannot be
exceeded when rewiring

The inputs are:

feedername -- name of JSON for feeder
perRew -- percent of the feeder edges to be rewired (default=10%)
distThresh -- maximum allowable edge length in the communication graph, as
			  given by the Euclidean distance between the edges endpoint nodes
			  (Default=1000)
plotGraphs -- Set to True if plots of the feeder and corresponding communicaiton
			  network are desired.

Note: the feeder parsing code is adapted from plot_feeder.py, located at:
https://github.com/GRIDAPPSD/Powergrid-Models/blob/develop/taxonomy/plot_feeder.py
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
#import math
import csv
import rewire_connNdist as rw
from networkx.readwrite import json_graph

def synFeederComGraph(feedername,perRew=0.1,distThresh=1000,plotGraphs=False):
	#if __name__ == '__main__':
	#feedername = 'R5-12.47-5'
	lp = open ('new_' + feedername + '.json').read()
	feeder = json.loads(lp)
	G = nx.readwrite.json_graph.node_link_graph(feeder)
	nbus = G.number_of_nodes()
	nbranch = G.number_of_edges()
	print ('read graph with', nbus, 'nodes and', nbranch, 'edges')

	# extract the XY coordinates available for plotting
	xy = {}
	plotnodes = set()
	for n in G.nodes():
		ndata = G.nodes()[n]['ndata']
		if 'x' in ndata:
			busx = float(ndata['x'])
			busy = float(ndata['y'])
			xy[n] = [busx, busy]
			plotnodes.add(n)

	# rewire the feeder topology to yield the communication network topology
	tmpG=G.subgraph(xy.keys())
	rewG=tmpG.copy()
	swapcount=rw.connected_double_edge_swap(rewG,
											xy,
											nswap=round(rewG.number_of_edges()*perRew),
	 										distThresh=distThresh,
											max_tries=5*rewG.number_of_edges())

	# extract the XY coordinates available for plotting (for rewired graph)
	rewxy = {}
	rewplotnodes = set()
	for n in rewG.nodes():
		ndata = G.nodes()[n]['ndata']
		if 'x' in ndata:
			busx = float(ndata['x'])
			busy = float(ndata['y'])
			rewxy[n] = [busx, busy]
			rewplotnodes.add(n)

	# only plot the edges that have XY coordinates at both ends
	plotedges = set()
	for e in G.edges():
		bFound = False
		if e[0] in xy:
			if e[1] in xy:
				plotedges.add(e)
				bFound = True

	# only plot the edges that have XY coordinates at both ends (for rewired g)
	rewplotedges = set()
	for e in rewG.edges():
		bFound = False
		if e[0] in xy:
			if e[1] in xy:
				rewplotedges.add(e)
				bFound = True

	if plotGraphs==True:
		f1 = plt.figure(1)
		list(xy.values())
		coorG=G.subgraph(list(plotnodes))
		nx.draw_networkx_nodes (G, xy, nodelist=list(plotnodes), node_size=1, node_color='r')
		nx.draw_networkx_edges (G, xy, edgelist=list(plotedges), edge_color='b')
		plt.title ('Layout of Feeder Power Components for ' + feedername)
		plt.xlabel ('X coordinate')
		plt.ylabel ('Y coordinate')
		plt.grid(linestyle='dotted')

		f2 = plt.figure(2)
		list(rewxy.values())
		rewcoorG=rewG.subgraph(list(rewplotnodes))
		nx.draw_networkx_nodes (rewG, rewxy, nodelist=list(rewplotnodes), node_size=1, node_color='r')
		nx.draw_networkx_edges (rewG, rewxy, edgelist=list(rewplotedges), edge_color='b')
		plt.title ('Synthetic Communication Network Topology for Feeder ' + feedername)
		plt.xlabel ('X coordinate')
		plt.ylabel ('Y coordinate')
		plt.grid(linestyle='dotted')
		plt.show()

	return rewG
