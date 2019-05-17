'''
.. module:: ns3Model

:platform: Unix, Windows
:synopsis: 

.. moduleauthor:: Laurentiu Marinovici
'''
import random
import numpy as np
try:
  import ns.core
  import ns.applications
  import ns.internet
  import ns.network
  import ns.mobility
  #import ns.netanim
  import ns.point_to_point
  import ns.topology_read
  import ns.flow_monitor
except ImportError:
    pass
try:
    import ns.visualizer
except ImportError:
    pass
def buildNS3model(topo):
  '''
  The function builds an ns-3 model based on an FNSS topology.

  :param topo: FNSS topology in dictionary format
  :returns: nothing

  The function is structured as follows:

    * initialization of simulation/model parameters
    * network setup

      * load FNSS topology and create the nodes of the ns-3 model
      * create location matrix containing longitude and latitude of the nodes based on the FNSS topology
      * create adjacency matrix based on existence of edge between nodes according with the FNSS topology
      * create P2P (Point-To-Point) link attributes
      * install internet stack to nodes
      * assign addresses to nodes

    * allocate node positions for mobility and netanim
    * create CBR flows based on adjacency matrix

  '''
  # ---------- Simulation Variables ------------------------------------------

  # Change the variables and file names only in this block!
  portNum = 9
  SinkStartTime = 1.0001
  SinkStopTime = 2.90001
  AppStartTime = 2.0001
  AppStopTime = 2.80001

  AppPacketRate = "40Kbps"
  ns.core.Config.SetDefault("ns3::OnOffApplication::PacketSize", ns.core.StringValue("1000"))
  ns.core.Config.SetDefault("ns3::OnOffApplication::DataRate", ns.core.StringValue(AppPacketRate))
  # LinkRate = "10Mbps"
  # LinkDelay = "2ms"

  np.random.seed() # generate random seed every time for the random generators
  tracerName = "n-node-ppp.tr"
  animName = "n-node-ppp.anim.xml"
  # ---------- End of Simulation Variables ----------------------------------

  ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
  ns.core.LogComponentEnable("UdpEchoServerApplication", ns.core.LOG_LEVEL_INFO)

  # ---------- Network Setup ------------------------------------------------
  # load the FNSS topology
  nodeKeys = topo.__dict__["_node"].keys()
  numNodes = len(nodeKeys)
  nodes = ns.network.NodeContainer() # Declare nodes objects
  nodes.Create(numNodes)

  # node location matrix/coordinates array
  coordArray = np.zeros((numNodes, 2))
  for node in topo.__dict__["_node"]:
    coordArray[node][0] = topo.__dict__["_node"][node]["longitude"]
    coordArray[node][1] = topo.__dict__["_node"][node]["latitude"]
  # print(coordArray)

  # adjacency matrix
  adjMatrix = np.zeros((numNodes, numNodes))
  # link rate/capacity matrix
  linkRateMatrix = np.zeros((numNodes, numNodes))
  # link delay matrix
  linkDelayMatrix = np.zeros((numNodes, numNodes))
  for node in topo.__dict__["_adj"]:
    for adjNode in topo.__dict__["_adj"][node]:
      adjMatrix[node][adjNode] = 1
      linkRateMatrix[node][adjNode] = topo.__dict__["_adj"][node][adjNode]["capacity"]
      linkDelayMatrix[node][adjNode] = topo.__dict__["_adj"][node][adjNode]["delay"]

  # print(adjMatrix)

  print("======== Create P2P (Point-To-Point) Link Attributes ===========")
  pointToPoint = ns.point_to_point.PointToPointHelper()
  # pointToPoint.SetDeviceAttribute("DataRate", ns.core.StringValue(LinkRate))
  # pointToPoint.SetChannelAttribute("Delay", ns.core.StringValue(LinkDelay))
  
  #devices = pointToPoint.Install(nodes)
  print("========= Install Internet Stack to Nodes. ============")
  stack = ns.internet.InternetStackHelper()
  stack.Install(ns.network.NodeContainer.GetGlobal())

  print("========== Assign Addresses to Nodes. ==============")
  address = ns.internet.Ipv4AddressHelper()
  address.SetBase(ns.network.Ipv4Address("10.0.0.0"),
                  ns.network.Ipv4Mask("255.255.255.252"))

  linkCount = 0
  for iNode in range(len(adjMatrix)):
    for jNode in range(len(adjMatrix[iNode])):
      if adjMatrix[iNode][jNode] == 1:
        n1 = ns.network.NodeContainer(nodes.Get(iNode))
        n2 = ns.network.NodeContainer(nodes.Get(jNode))
        nLinks = ns.network.NodeContainer(n1, n2)
        pointToPoint.SetDeviceAttribute("DataRate", ns.core.StringValue(str(linkRateMatrix[iNode][jNode]) + topo.__dict__["graph"]["capacity_unit"]))
        pointToPoint.SetChannelAttribute("Delay", ns.core.StringValue(str(linkDelayMatrix[iNode][jNode]) + topo.__dict__["graph"]["delay_unit"]))
        nDevs = pointToPoint.Install(nLinks)
        address.Assign(nDevs)
        address.NewNetwork()
        linkCount += 1
        print("matrix element [", iNode, "][", jNode, "] is 1")
      else:
        print("matrix element [", iNode, "][", jNode, "] is 0")
  
  print("Number of links in the adjancency matrix is: ", linkCount)
  print("Number of all nodes is: ", nodes.GetN())
  print(ns.network.NodeContainer.GetGlobal())
  
  print("Initialize Global Routing.")
  ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()
  # ---------- End of Network Set-up ----------------------------------------

  # ---------- Allocate Node Positions --------------------------------------
  print("Allocate Positions to Nodes.")
  nodeMobility = ns.mobility.MobilityHelper()
  nodePositionAlloc = ns.mobility.ListPositionAllocator()
  for coordInd in range(len(coordArray)):
    nodePositionAlloc.Add(ns.core.Vector(coordArray[coordInd][0], coordArray[coordInd][1], 0))
    #print(ns.core.Vector(coordArray[coordInd][0], coordArray[coordInd][1], 0))
    n0 = nodes.Get(coordInd)
    nLoc = n0.GetObject(ns.mobility.ConstantPositionMobilityModel.GetTypeId())
    if nLoc == None:
      nLoc = ns.mobility.ConstantPositionMobilityModel()
      n0.AggregateObject(nLoc)
    nVec = ns.core.Vector(coordArray[coordInd][0], -coordArray[coordInd][1], 0)
    nLoc.SetPosition(nVec)
  nodeMobility.SetPositionAllocator(nodePositionAlloc)
  nodeMobility.Install(nodes)
  # ---------- End of Allocate Node Positions -------------------------------

  # ---------- Create CBR Flows based on adjacency matrix -------------------
  print("Setup Packet Sinks.")
  
  for nodeInd in range(numNodes):
    sink = ns.applications.PacketSinkHelper("ns3::UdpSocketFactory", ns.network.InetSocketAddress(ns.network.Ipv4Address.GetAny(), portNum))
    appsSink = sink.Install(nodes.Get(nodeInd)) # sink is installed on all nodes
    appsSink.Start(ns.core.Seconds(SinkStartTime))
    appsSink.Stop(ns.core.Seconds(SinkStopTime))

  print("Setup CBR Traffic Sources.")
  for iNode in range(numNodes):
    for jNode in range(numNodes):
      if (iNode != jNode) & (adjMatrix[iNode][jNode] == 1):
        # We needed to generate a random number (rn) to be used to eliminate
        # the artificial congestion caused by sending the packets at the
        # same time. This rn is added to AppStartTime to have the sources
        # start at different time, however they will still send at the same rate.
        rn = np.random.uniform()
        n = nodes.Get(jNode) # get the node
        ipv4 = n.GetObject(ns.internet.Ipv4.GetTypeId()) # get the device attached to node
        ipv4InterfaceAddr = ipv4.GetAddress(1, 0) # get the IP corresponding to each device
        #print(ipv4InterfaceAddr)
        ipAddr = ipv4InterfaceAddr.GetLocal() # local IP
        #print(ipAddr)
        OnOff = ns.applications.OnOffHelper("ns3::UdpSocketFactory", ns.network.InetSocketAddress(ipAddr, portNum))
        OnOff.SetConstantRate(ns.network.DataRate(AppPacketRate))
        apps = OnOff.Install(nodes.Get(iNode))
        #print(AppStartTime)
        #print(rn)
        apps.Start(ns.core.Seconds(AppStartTime + rn))
        apps.Stop(ns.core.Seconds(AppStopTime))
  # ---------- End of Create CBR Flows ------------------------------

  # ---------- Simulation Monitoring ----------------------------------------
  print("Configure Tracing.")
  asciiTr = ns.network.AsciiTraceHelper()
  pointToPoint.EnableAsciiAll(asciiTr.CreateFileStream(tracerName))
  
  #anim = ns.NetworkAnimation.AnimationInterface(animName)
  # ---------- End of Simulation Monitoring ---------------------------------