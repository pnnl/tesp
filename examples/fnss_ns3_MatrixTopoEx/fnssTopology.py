'''
.. module:: fnssTopology

:platform: Unix, Windows
:synopsis: 

.. moduleauthor:: Laurentiu Marinovici
'''
# create topology and schedule using FNSS
import fnss
from fnss.util import geographical_distance
import networkx as nx
import matplotlib.pyplot as plt
from colorama import *
import random
import pprint
pp = pprint.PrettyPrinter(indent = 2)

def buildFNSStopology():
  '''
  This function invokes Fast Network Simulation Setup (`FNSS <http://fnss.github.io>`_) to build a network topology. 

  :param none: The function does not need an argument
  :returns: topo - FNSS topology in dictionary format

  >>> import pprint
  >>> pprint.pprint(topo.__dict__)
  {
  '_adj': {},
  '_node': {},
  'adjlist_inner_dict_factory': <class 'dict'>,
  'adjlist_outer_dict_factory': <class 'dict'>,
  'edge_attr_dict_factory': <class 'dict'>,
  'graph': {},
  'graph_attr_dict_factory': <class 'dict'>,
  'node_attr_dict_factory': <class 'dict'>,
  'node_dict_factory': <class 'dict'>,
  'nodes': NodeView((0, 1, 2)
  }

  This function:

    * uses FNSS :func:`k_ary_tree_topology` function to build a tree topology
    * assigns coordinates (longitude and latitude) to the nodes
    * uses the coordinates and FNSS :func:`geographical_distance` function to calculate distance between nodes and assigns these values as the lengths of the graph edges
    * sets random capacities to the graph edges using FNNS :func:`set_capacities_random_uniform` function
    * sets specific propagation delays using FNSS :func:`set_delays_geo_distance` function, based on the ropagation delay of light in an average optical fiber
      
      >>> specificDelay = fnss.PROPAGATION_DELAY_FIBER

    * sets the weights to links proportionally to their delay using FNSS :func:`set_weights_delays`
    * sets the buffer sizes proportionally to the product of link bandwidth and average network RTT using FNSS :func:`set_buffer_sizes_bw_delay_prod`
  
  .. note:: The function does assign applications and event schedules, but they are not used subsequently. At least not at this point.

  '''
  #G = nx.DiGraph()
  nodeCoord = dict()
  distanceUnit = 'Km'
  capacityUnit = "Mbps"
  leafNum = 2
  treeDepth = 1
  topo = fnss.k_ary_tree_topology(leafNum, treeDepth)
  topo.name = 'simple testing tree'
  topo.graph['distance_unit'] = distanceUnit
  topo.graph['capacity_unit'] = capacityUnit

  # topo = fnss.Topology(G, name = 'simple testing tree', distance_unit = distanceUnit, capacity_unit = capacityUnit)
  print(Fore.YELLOW + Back.BLUE + "===== Number of nodes ===== " + Style.RESET_ALL + str(topo.order()))
  nodeCoord = nx.nx_agraph.graphviz_layout(topo, prog = "dot")
  for node in topo.nodes():
    #lon = random.uniform(0, 20)
    #lat = random.uniform(0, 20)
    topo.add_node(node, longitude = nodeCoord[node][0], latitude = nodeCoord[node][1])
    #pos[node] = (lon, lat)

  print(Fore.YELLOW + Back.BLUE + "===== Number of edges ===== " + Style.RESET_ALL + str(topo.size()))
  for link in topo.edges():
    u = link[0]
    v = link[1]
    lon_u = topo.node[u]['longitude']
    lat_u = topo.node[u]['latitude']
    lon_v = topo.node[v]['longitude']
    lat_v = topo.node[v]['latitude']
    length = geographical_distance(lat_v, lon_v, lat_u, lon_u)
    topo.add_edge(u, v, length = length)

  capacities = [1, 2, 4]
  # fnss.set_capacities_edge_betweenness(topo, capacities, capacityUnit, weighted = True)
  print(Fore.YELLOW + Back.BLUE + "===== Assigning capacities randomly =====" + Style.RESET_ALL)
  fnss.set_capacities_random_uniform(topo, capacities)
  # pprint.pprint(fnss.get_capacities(topo))

  specificDelay = fnss.PROPAGATION_DELAY_FIBER
  print(Fore.YELLOW + Back.BLUE + "===== Setting delays based on geographical distance between nodes =====" + Style.RESET_ALL)
  fnss.set_delays_geo_distance(topo, specific_delay = specificDelay, default_delay = 2, delay_unit = 'ms')
  # pprint.pprint(fnss.get_delays(topo))

  print(Fore.YELLOW + Back.RED + "===== Setting the weights to links proportionally to their delay =====" + Style.RESET_ALL)
  fnss.set_weights_delays(topo)

  print(Fore.YELLOW + Back.BLUE + '===== Setting the buffer sizes proportionally to the product of link bandwidth and average network RTT =====' + Style.RESET_ALL)
  bufferUnit = 'bytes'
  fnss.set_buffer_sizes_bw_delay_prod(topo, buffer_unit = bufferUnit)

  nodeTypes = nx.get_node_attributes(topo, 'type')
  senders = [node for node in nodeTypes
             if nodeTypes[node] == 'root'
             or nodeTypes[node] == 'intermediate']
  receivers = [node for node in nodeTypes
               if nodeTypes[node] == 'intermediate'
               or nodeTypes[node] == 'leaf']
  for node in senders:
    fnss.add_application(topo, node, 'ns3::UdpEchoServer', {'StartTime': '1s', 'StopTime': '10s', 'Port': '2000'})

  for node in receivers:
    fnss.add_application(topo, node, 'ns3::UdpEchoClient', {'StartTime': '1s', 'StopTime': '10s', 'RemoteAddress': '3-4-0a:00:00:06', 'RemotePort': '2000'})

  def randRequest(senderNodes, receiverNodes):
    sender = random.choice(senderNodes)
    receiver = random.choice([u for u in receiverNodes if topo.has_edge(sender, u)])
    return {'sender': sender, 'receiver': receiver}

  eventSchedule = fnss.poisson_process_event_schedule(
                        avg_interval = 50,  # 50 ms
                        t_start = 0,  # starts at 0
                        duration = 10 * 1000,  # 10 sec
                        t_unit = 'ms',  # milliseconds
                        event_generator = randRequest,  # event gen function
                        senderNodes = senders,  # rand_request argument
                        receiverNodes = receivers  # rand_request argument
                        )

  fnss.write_topology(topo, 'treeTopologyExample-01.xml')
  fnss.write_event_schedule(eventSchedule, 'eventScheduleExample-01.xml')

  print(Fore.YELLOW + Back.BLUE + "===== ================== =====" + Style.RESET_ALL)
  pprint.pprint(topo.__dict__)
  #pprint.pprint(nx.nx_agraph.graphviz_layout(topo, prog = "dot"))
  print(Fore.YELLOW + Back.BLUE + "===== ================== =====" + Style.RESET_ALL)

  return topo

def plotTopology(topo):
  '''
  Plots the FNSS network topology usings :mod:`networkx`
  '''
  #for idx in range(len(nodes1)):
  #  G.add_edge(nodes1[idx], nodes2[idx], weight = edgeWeights[idx])
  fig, axes = plt.subplots(1, 1, figsize = (12, 5))
  plt.title("Test topology")

  # plt.subplot(122)
  nx.drawing.nx_pydot.write_dot(topo, "tree.dot")
  #pos = nx.nx_pydot.graphviz_layout(G)#, prog = "tree.dot")
  #pos = nx.nx_pydot.graphviz_layout(G)#, prog = "tree.dot")
  pos1 = nx.nx_agraph.graphviz_layout(topo, prog = "dot")
  #nx.draw(topo, pos = pos1, node_color = 'green', edge_color = 'blue', with_labels = True, arrows = False)
  nx.draw_networkx_nodes(topo, pos = pos1, node_color = 'green', label = 'string')
  #pprint.pprint(nx.get_edge_attributes(topo, 'capacity'))
  wid = nx.get_edge_attributes(topo, 'capacity').values()
  #print(wid)
  #print(list(wid))
  nx.draw_networkx_edges(topo, pos = pos1, edge_color = 'blue', width = list(wid), alpha = 1)
  '''
  plt.subplot(132)
  nx.draw(G, pos = nx.circular_layout(G), node_color = 'green', edge_color = 'blue', with_labels = True)

  plt.subplot(133)
  nx.draw(G, pos = nx.spectral_layout(G), node_color = 'magenta', edge_color = 'orange', with_labels = True)
  '''
  plt.show()