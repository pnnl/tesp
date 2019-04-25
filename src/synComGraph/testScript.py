"""
Test script for synComGraph.py. Saves the output communication graph topology
as a JSON in the same format as the input feeder topology.
"""
import synComGraph as scg
import json
from networkx.readwrite import json_graph

feedername='R5-12.47-5' #Name of JSON for feeder
perRew=0.2 #percent of the links to be rewired in communication graph
distThresh=1000 #maximum Euclidean distance between linked nodes allowed in rewiring
comG=scg.synFeederComGraph(feedername,
                          perRew=perRew,
                          distThresh=distThresh,
                          plotGraphs=True)

#save the output NetworkX communication graph as a JSON file
with open('commNet_'+ feedername + '.json', 'w') as outfile1:
	outfile1.write(json.dumps(json_graph.node_link_data(comG)))
