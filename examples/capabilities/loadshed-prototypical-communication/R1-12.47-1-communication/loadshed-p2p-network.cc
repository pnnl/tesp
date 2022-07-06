/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
 /*
  * This program is free software; you can redistribute it and/or modify
  * it under the terms of the GNU General Public License version 2 as
  * published by the Free Software Foundation;
  *
  * This program is distributed in the hope that it will be useful,
  * but WITHOUT ANY WARRANTY; without even the implied warranty of
  * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  * GNU General Public License for more details.
  *
  * You should have received a copy of the GNU General Public License
  * along with this program; if not, write to the Free Software
  * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
  *
  */
 
 //
 // Simple example of OLSR routing over some point-to-point links
 //
 // Network topology
 //
 //  n0
 //    \ 5 Mb/s, 2ms
 //    \       1.5Mb/s, 10ms
 //     n2 -------------------------n3---------n4
 //    /
 //    / 5 Mb/s, 2ms
 //  n1
 //
 // - all links are point-to-point links with indicated one-way BW/delay
 // - CBR/UDP flows from n0 to n4, and from n3 to n1
 // - UDP packet size of 210 bytes, with per-packet interval 0.00375 sec.
 //  (i.e., DataRate of 448,000 bps)
 // - DropTail queues
 // - Tracing of queues and packet receptions to file "simple-point-to-point-olsr.tr"
 
 #include <iostream>
 #include <fstream>
 #include <string>
 #include <cassert>
 
 #include "ns3/core-module.h"
 #include "ns3/network-module.h"
 #include "ns3/internet-module.h"
 #include "ns3/point-to-point-module.h"
 #include "ns3/applications-module.h"
//#include "ns3/olsr-helper.h"
//#include "ns3/ipv4-global-routing-helper.h"
//#include "ns3/ipv4-static-routing-helper.h"
// #include "ns3/ipv4-nix-vector-helper.h"
#include "ns3/nix-vector-helper.h"
//#include "ns3/ipv4-list-routing-helper.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include <jsoncpp/json/json.h>
#include <jsoncpp/json/forwards.h>
#include <jsoncpp/json/writer.h>
#include "ns3/helics-helper.h"

using namespace ns3;
using namespace std;

void ReceivePacket(Ptr<Socket> socket) //, time_t t)
{
  //cout << "Received one packet!" << endl;
}

static void GenerateTraffic(Ptr<Socket> socket, uint32_t pktSize, uint32_t pktCount, Time pktInterval)
{
  if (pktCount > 0)
  {
   socket->Send(Create<Packet>(pktSize));
   Simulator::Schedule(pktInterval, &GenerateTraffic, socket, pktSize, pktCount - 1, pktInterval);
   // cout << "<<<<<< Generated traffic on socket at node ID: " << socket->GetNode()->GetId() << "; packet size: " << pktSize << ", packet count: " << pktCount << ", packet interval: " << pktInterval.GetSeconds() << "s, current time: " << Simulator::Now().GetSeconds() << "s. >>>>>>>>>>>>>>>>>" << endl;
  }
  else
  {
   //cout << "<<<<<<<<<<< Ended traffic. >>>>>>>>>>>>>>>" << endl;
   socket->Close();
  }
}

class P2PNode
{
public:
   P2PNode();
   string nclass;
   string phases;
   string nominalVoltage;
   string xval;
   string yval;
   string zval;
   string id;
};
//***************************************************************************************************************************************
class P2PLink
{
public:
   P2PLink();
   string eclass;
   string ename;
   string from;
   string to;
   string phases ;
   string length;
   string configuration;
   string source;
   string target;
};
//***************************************************************************************************************************************
P2PLink::P2PLink() :
   eclass(""),
   ename(""),
   from(""),
   to(""),
   phases(""),
   length("0.0"),
   configuration(""),
   source(""),
   target("")
{
}
//***************************************************************************************************************************************
void setP2PLinkData(vector<P2PLink>& p2plinks,Json::Value& configobj,map<string,P2PNode> nodes,vector<string>& missinglinks)
{
   uint32_t i;
   string mstring;
   for(i=0;i<configobj["links"].size();i++)
   {
      P2PLink tnode;
      tnode.eclass = configobj["links"][i]["eclass"].asString();
      tnode.ename = configobj["links"][i]["ename"].asString();
      tnode.from = configobj["links"][i]["edata"]["from"].asString();
      tnode.to = configobj["links"][i]["edata"]["to"].asString();
      tnode.phases = configobj["links"][i]["edata"]["phases"].asString();
      tnode.length = configobj["links"][i]["edata"]["length"].asString();
      tnode.configuration = configobj["links"][i]["edata"]["configuration"].asString();

      tnode.source = configobj["links"][i]["source"].asString();
      tnode.target = configobj["links"][i]["target"].asString();
      
      if(tnode.source == "" || tnode.target == "")
      {
           mstring = "Missing source and target: " + tnode.ename;
      }
      else if(nodes.find(tnode.source) == nodes.end())
      {
           mstring = "Missing source node: " + tnode.ename;
      }
      else if(nodes.find(tnode.target) == nodes.end())
      {
           mstring = "Missing target node: " + tnode.ename;
      }
      else
      {
           p2plinks.push_back(tnode);           
      }
   }
}
//***************************************************************************************************************************************
void WriteNetworkLinkFile(string fpath,vector<P2PLink>& p2plinks,map<string,P2PNode> nodes)
{
      uint32_t i;
      ofstream logfile;
      string ostring;
      P2PNode tsource;
      P2PNode ttarget;
      P2PLink tlink;
      logfile.open(fpath);
//      logfile << "Polyline" << endl;
      logfile << "Name,SourceNode,StartX,StartY,TargetNode,EndX,EndY" << endl;
      for(i=0;i<p2plinks.size();i++)
      {
           //logfile << i << " 0" << endl;
           tlink = p2plinks[i];
           //tsource = (P2PNode)nodes.find(tlink.source);
           //ttarget = (P2PNode)nodes.find(tlink.target);
           tsource = nodes[tlink.source];
           ttarget = nodes[tlink.target];
           logfile << tlink.ename << "," << tsource.id << "," << tsource.xval << "," << tsource.yval << ","  << ttarget.id << ","  << ttarget.xval << ","  << ttarget.yval << endl;
           //logfile << "0 " << tsource.xval << " " << tsource.yval << " 0 0" << endl;
           //logfile << "1 " << ttarget.xval << " " << ttarget.yval << " 0 0" << endl;
      }      
      logfile << "END" << endl;
      logfile.close();
}


void WriteNetworkLinkJsonFile(string fpath,vector<P2PLink> p2plinks, map<string,P2PNode> nodes)
{
      uint32_t i;
      ofstream logfile;
      string ostring;
      P2PNode tsource;
      P2PNode ttarget;
      P2PLink tlink;
      logfile.open(fpath);
      logfile << "Name,StartX,StartY,EndX,EndY" << endl;

      for(i=0;i<p2plinks.size();i++)
      {
           tlink = p2plinks[i];
           tsource = nodes[tlink.source];
           ttarget = nodes[tlink.target];
           logfile << tlink.ename << "," << tsource.xval << "," << tsource.yval << ","  << ttarget.xval << ","  << ttarget.yval << endl;
      }      
      logfile.close();
}

//***************************************************************************************************************************************
P2PNode::P2PNode() :
   nclass(""),
   phases(""),
   nominalVoltage(""),
   xval(""),
   yval(""),
   zval("0.0"),
   id("")
{
}
//***************************************************************************************************************************************
bool checkForNodeType(string nodetype,vector<string> nodetypes)
{
      uint32_t i;
      for(i=0;i<nodetypes.size();i++)
      {
           if(nodetype == nodetypes[i])
           {
                return true;
           }           
      }
      return false;
}
void writeNodeTypeList(string fpath,Json::Value configobj,vector<string>& nodetypes)
{
      uint32_t i;
      string nodetype;
      ofstream nodelistfile;
      nodelistfile.open(fpath);
      for(i=0;i<configobj["nodes"].size();i++)
      {
           nodetype = configobj["nodes"][i]["nclass"].asString();
           if(checkForNodeType(nodetype,nodetypes) == false)
           {
                nodetypes.push_back(nodetype);
           }
      }
      for(i=0;i<nodetypes.size();i++)
      {
           nodelistfile << nodetypes[i] << endl;
      }
      nodelistfile.close();
}

void selectNodeTypes(vector<string>& nodetypes)
{
      uint32_t i;
      string selectcheck;
      cout << "Select node types to simulate? (y/n)" << endl;
      cin >> selectcheck;
//      cout << selectcheck << endl;
      if(selectcheck == "y" || selectcheck == "Y")
      {
           for(i=nodetypes.size();i>0;i--)
           {
                cout << nodetypes[i-1] << " (y/n)" << endl;
                cin >> selectcheck;
                if(selectcheck == "n" || selectcheck == "N")
                {
                      //nodetypes.erase(nodetypes.end());
                      nodetypes.erase(nodetypes.begin() + (i - 1));
                }
           }
      }
      cout << "Node types selected for simulation:" << endl;
      for(i=0;i<nodetypes.size();i++)
      {
           cout << nodetypes[i] << endl;
      }
}

void selectNodeTypesLoadshed(vector<string> &nodetypes)
{
      uint32_t i;
      string selectcheck = "y";
      cout << "Selected node types are chosen to simulate for the LOADSHED use-case." << endl;
      if (selectcheck == "y" || selectcheck == "Y")
      {
           for (i = nodetypes.size(); i > 0; i--)
           {
                if (nodetypes[i - 1] == "solar" | nodetypes[i - 1] == "solar_meter" | nodetypes[i - 1] == "battery" | nodetypes[i - 1] == "battery_meter" | nodetypes[i - 1] == "inverter" | nodetypes[i - 1] == "house")
                {
                      nodetypes.erase(nodetypes.begin() + (i - 1));
                }
           }
      }
      cout << "Node types selected for LOADSHED use-case simulation:" << endl;
      for (i = 0; i < nodetypes.size(); i++)
      {
           cout << "\t" << nodetypes[i] << endl;
      }
}

void setP2PNodeData(map<string,P2PNode>& p2pnodedata,Json::Value& configobj,NodeContainer& p2pnodes,Ptr<ListPositionAllocator>& positionAlloc,vector<string>& missingnodes,string fpath,vector<string> nodetypes)
{
   uint32_t i;
   double xval,yval,zval;
   ofstream logfile;
   logfile.open(fpath);
   logfile << "Name,X,Y,Class" << endl;
   for(i=0;i<configobj["nodes"].size();i++)
   {
      P2PNode tnode;
      tnode.nclass = configobj["nodes"][i]["nclass"].asString();
      if(checkForNodeType(tnode.nclass,nodetypes))
      {
           //cout << checkForNodeType(tnode.nclass,nodetypes) << endl;
           tnode.phases = configobj["nodes"][i]["ndata"]["phases"].asString();
           tnode.nominalVoltage = configobj["nodes"][i]["ndata"]["nominal_voltage"].asString();
           tnode.xval = configobj["nodes"][i]["ndata"]["x"].asString();
           tnode.yval = configobj["nodes"][i]["ndata"]["y"].asString();
           tnode.id = configobj["nodes"][i]["id"].asString();
           //cout << tnode.id << "," << tnode.xval << "," << tnode.yval << endl;
           if(tnode.xval != "" && tnode.yval != "")
           {
                xval = stod(tnode.xval);
                yval = stod(tnode.yval);
                zval = 0.0;
                logfile << tnode.id << "," << xval << "," << yval << "," << tnode.nclass << endl;
                p2pnodedata.insert(pair<string, P2PNode>(tnode.id, tnode));
                Ptr<Node> tempnode = CreateObject<Node>();
                Names::Add(tnode.id, tempnode);
                positionAlloc->Add(Vector(xval, yval, zval));
                p2pnodes.Add(tempnode);
           }
           else
           {
                missingnodes.push_back(tnode.id);
           }
      }
   }
   logfile.close();
}
//***************************************************************************************************************************************
void listMissingNodesAndLinks(vector<string> mnodes, vector<string> mlinks)
{
      uint32_t i;
      string ostring;
      if(mnodes.size() > 0)
      {
           cout << "The following " << mnodes.size() << " nodes are missing location data: " << endl;
      }
      for(i=0;i<mnodes.size();i++)
      {
           ostring = mnodes[i];
           cout << ostring << endl;
      }
      if(mlinks.size() > 0)
      {
           cout << "The following " << mlinks.size() << " links are missing node data: " << endl;
      }
      for(i=0;i<mlinks.size();i++)
      {
           ostring = mlinks[i];
           cout << ostring << endl;
      }
}
//***************************************************************************************************************************************
void writeMissingNodesAndLinksFile(string fpath,vector<string> mnodes, vector<string> mlinks)
{
      uint32_t i;
      ofstream logfile;
      string ostring;
      logfile.open(fpath);
      cout << "Writing missing data log file" << fpath << endl;
      if(mnodes.size() > 0)
      {
           logfile << "The following " << mnodes.size() << " nodes are missing location data: " << endl;
      }
      for(i=0;i<mnodes.size();i++)
      {
           ostring = mnodes[i];
           logfile << ostring << endl;
      }
      if(mlinks.size() > 0)
      {
           logfile << "The following " << mlinks.size() << " links are missing node data: " << endl;
      }
      for(i=0;i<mlinks.size();i++)
      {
           ostring = mlinks[i];
           logfile << ostring << endl;
      }
      logfile.close();
}
//***************************************************************************************************************************************
void readMicroGridConfig(std::string fpath, Json::Value& configobj)
{
   ifstream tifs(fpath);
   Json::Reader configreader;
   configreader.parse(tifs, configobj);
   //cout << configobj << endl;
}

//***************************************************************************************************************************************
NS_LOG_COMPONENT_DEFINE("TESP-P2P-BIG-Network");
int main(int argc, char *argv[])
{
  Config::SetDefault ("ns3::Ipv4L3Protocol::DefaultTtl", UintegerValue (255));
  string simConfigFileName;
  string configFilePath;      // = "../../files/R1-12.47-1_ns3.json";
  string endPointConfigFilePath; // =  "./ns3_config.json";
  string animFileName;        // = "./Tesp_anim_P2P.xml";
  string routingFileName;      // = "./Tesp_route_P2P.xml";
  string errorLogFileName;     // = "./Tesp_P2P.log";
  //string configFileName = "Tesp_P2P.cfg";
  string nodesLocationFile; // = "./Tesp_P2P_nodes_reduced.txt";
  string linksLocationFile; // = "./Tesp_P2P_links.txt";
  string nodeListFileName;  // = "./Tesp_P2P.lst"
  string caseName;
  string checkstring;
  CommandLine cmd;
  Json::Value simConfigObject;
  Json::Value ns3ConfigObject;
  Json::Value endPointConfigObject;
  map<string, P2PNode> p2pNodes;
  vector<P2PLink> p2pLinks;
  vector<string> nodesMissingLocations;
  vector<string> linksMissingNodes;
  vector<string> nodeTypes;
  uint32_t i;
  bool verbose = true;
  Time simTime = Seconds(30.001);

  double tSimTime = -9999.99;
  string tVerbose = "";
  string tCaseName = "";
  string tTracePath = "";
  string tAnimName = "";
  string tRoutingFileName = "";
  string tEPConfig = "";
  string tNs3Config = "";
  string tErrLogFileName = "";
  string tNodeLocFileName = "";
  string tLinkLocFileName = "";
  string tNodeListFileName = "";
  string tConfigString = "";

  uint32_t packetSize = 1024; // bytes
  uint32_t numPackets = 100;
  double interval = 1;
  Time interPacketInterval = Seconds(interval);

  time_t start, end;
  double timeTaken;
  // -------------------------------------------------------------------------------
  // HELICS FILTER config file calling
  // -------------------------------------------------------------------------------
  cmd.AddValue("simTime", "Total duration of the simulation [s])", tSimTime);
  cmd.AddValue("verbose", "Tell echo applications to log if true", tVerbose);
  cmd.AddValue("caseName", "Case name", tCaseName);
  cmd.AddValue("configFilePath", "ns-3 network configuration/node file path", tNs3Config);  // the ns-3 network nodes
  cmd.AddValue("endPointConfigFilePath", "ns-3 HELICS configuration file path", tEPConfig); // the ns-3 HELICS configuration file
  cmd.AddValue("animFile", "ns-3 model animation output file name", tAnimName);
  cmd.AddValue("routingFile", "ns-3 model routing file name", tRoutingFileName);

  cmd.AddValue("errorLogFile", "Error logging file name", tErrLogFileName);
  cmd.AddValue("nodesLocationFile", "ns-3 model nodes location file name", tNodeLocFileName);
  cmd.AddValue("linksLocationFile", "ns-3 model links location file name", tLinkLocFileName);
  cmd.AddValue("nodeListFile", "Node list file name", tNodeListFileName);
  cmd.AddValue("simConfigFile", "Simulation configuration file", simConfigFileName);
  cmd.Parse(argc, argv);
  cout << "Reading simulation/scenario configuration file: " << configFilePath << endl;
  readMicroGridConfig(simConfigFileName, simConfigObject);
  if (tSimTime < 0)
  {
   tConfigString = simConfigObject["Simulation"]["Simulation_Duration"].asString();
   if (tConfigString != "")
   {
    simTime = Seconds(stod(tConfigString));
   }
  }
  if (tVerbose == "")
  {
   tConfigString = simConfigObject["Simulation"]["Verbose"].asString();
   if (tConfigString != "")
   {
    if (tConfigString == "true")
      verbose = true;
    else
      verbose = false;
   }
  }
  if (tCaseName == "")
  {
   tConfigString = simConfigObject["Simulation"]["Case_Name"].asString();
   if (tConfigString != "")
   {
    caseName = tConfigString;
   }
  }
  if (tNs3Config == "")
  {
   tConfigString = simConfigObject["Simulation"]["ns3_Network_Config"].asString();
   if (tConfigString != "")
   {
    configFilePath = tConfigString;
   }
  }
  if (tEPConfig == "")
  {
   tConfigString = simConfigObject["Simulation"]["ns3_EP_Config"].asString();
   if (tConfigString != "")
   {
    endPointConfigFilePath = tConfigString;
   }
  }
  if (tAnimName == "")
  {
   tConfigString = simConfigObject["Simulation"]["Anim_File"].asString();
   if (tConfigString != "")
   {
    animFileName = tConfigString;
   }
  }
  if (tRoutingFileName == "")
  {
   tConfigString = simConfigObject["Simulation"]["Routing_File"].asString();
   if (tConfigString != "")
   {
    routingFileName = tConfigString;
   }
  }
  if (tErrLogFileName == "")
  {
   tConfigString = simConfigObject["Simulation"]["Err_Log_File"].asString();
   if (tConfigString != "")
   {
    errorLogFileName = tConfigString;
   }
  }
  if (tNodeLocFileName == "")
  {
   tConfigString = simConfigObject["Simulation"]["Node_Loc_File"].asString();
   if (tConfigString != "")
   {
    nodesLocationFile = tConfigString;
   }
  }
  if (tLinkLocFileName == "")
  {
   tConfigString = simConfigObject["Simulation"]["Links_Loc_File"].asString();
   if (tConfigString != "")
   {
    linksLocationFile = tConfigString;
   }
  }
  if (tNodeListFileName == "")
  {
   tConfigString = simConfigObject["Simulation"]["Node_List_File"].asString();
   if (tConfigString != "")
   {
    nodeListFileName = tConfigString;
   }
  }
  std::cout << "Number of arguments for the command: " << argc << std::endl;
  cout << "This simulation setup:" << endl;
  cout << "\tSim configuration file: " << simConfigFileName << endl;
  cout << "\tCase name: " << caseName << endl;
  cout << "\tSimulation duration (default unit): " << simTime << endl;
  //Time::SetResolution (Time::S);
  //cout << "\tSimulation duration (after unit change): " << simTime << endl;
  cout << "\tLog components? This works only for debug version. -- " << verbose << endl;
  cout << "\tns-3 network configuration file path: " << configFilePath << endl;
  cout << "\tns-3 HELICS configuration file path: " << endPointConfigFilePath << endl;
  cout << "\tNETANIM diagram file: " << animFileName << endl;
  cout << "\tNETANIM routing file: " << routingFileName << endl;
  cout << "\tError logging file: " << errorLogFileName << endl;
  cout << "\tns-3 node location file: " << nodesLocationFile << endl;
  cout << "\tns-3 link location file: " << linksLocationFile << endl;
  cout << "\tNode list file: " << nodeListFileName << endl;
  HelicsHelper helicsHelper;

  if (verbose)
  {
   cout << "========= I SHOULD GET THE LOG MESSAGES ================" << endl;
   LogComponentEnable("TESP-P2P-BIG-Network", LOG_LEVEL_INFO);
   //LogComponentEnable ("HelicsSimulatorImpl", LOG_LEVEL_LOGIC);
   //LogComponentEnable ("HelicsStaticSinkApplication", LOG_LEVEL_LOGIC);
   //LogComponentEnable ("HelicsStaticSourceApplication", LOG_LEVEL_LOGIC);
   LogComponentEnable("HelicsApplication", LOG_LEVEL_ALL);     //LOGIC);
   LogComponentEnable("HelicsFilterApplication", LOG_LEVEL_ALL); //LOGIC);
  }
 
  //  Config::SetDefault ("ns3::OnOffApplication::PacketSize", UintegerValue (210));
  //  Config::SetDefault ("ns3::OnOffApplication::DataRate", StringValue ("448kb/s"));
  //  cmd.AddValue ("configFilePath", "Path to the configuration file", configFilePath);
  //DefaultValue::Bind ("DropTailQueue::m_maxPackets", 30);

  cout << "Reading configuration file: "<< configFilePath << endl;
  readMicroGridConfig(configFilePath, ns3ConfigObject); 

  writeNodeTypeList(nodeListFileName, ns3ConfigObject, nodeTypes);
  // selectNodeTypes(nodeTypes);
  selectNodeTypesLoadshed(nodeTypes);

  cout << "Reading endpoints configuration file" << endl;
  readMicroGridConfig(endPointConfigFilePath, endPointConfigObject);

  std::cout << "Calling Calling Message Federate Constructor" << std::endl;
  helicsHelper.SetupApplicationFederateWithConfig(endPointConfigFilePath);
  std::cout << "Getting Federate information" << std::endl;

  std::string ns3 = helics_federate->getName();
  std::cout << "Federate name: " << helics_federate->getName().c_str() << std::endl;

  int ep_count = helics_federate->getEndpointCount();
  for (int i = 0; i < ep_count; i++) {
    helics::Endpoint ep = helics_federate->getEndpoint(i);
    std::string epName = ep.getName();
    std::string ep_info = ep.getInfo();
    size_t pos = epName.find(ns3);
    if (pos != std::string::npos) {
       epName.erase(pos, ns3.length() + 1);
    }
    NS_LOG_INFO("============ Processing endpoint named: " << epName << " . ==================");
  }

  //cout << ns3ConfigObject << endl;
  cout << "Number of nodes = " << ns3ConfigObject["nodes"].size() << endl;
  cout << "Number of links = " << ns3ConfigObject["links"].size() << endl;
  NodeContainer p2pNodesCon;
  Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator>();

  cout << "Setting P2P nodes data" << endl;
  setP2PNodeData(p2pNodes,ns3ConfigObject,p2pNodesCon,positionAlloc,nodesMissingLocations,nodesLocationFile,nodeTypes);
  cout << "Number of p2p nodes = " << p2pNodes.size() << endl;
  cout << "Setting P2P links data" << endl;
  setP2PLinkData(p2pLinks,ns3ConfigObject,p2pNodes,linksMissingNodes);
  listMissingNodesAndLinks(nodesMissingLocations,linksMissingNodes);
  WriteNetworkLinkFile(linksLocationFile,p2pLinks,p2pNodes);
//  WriteNetworkLinkJsonFile(linksLocationFile,p2pLinks,p2pNodes);
//writeMissingNodesAndLinks(errorLogFileName,nodesMissingLocations,linksMissingNodes);
  writeMissingNodesAndLinksFile(errorLogFileName,nodesMissingLocations, linksMissingNodes);

  if(nodesMissingLocations.size() > 0 || linksMissingNodes.size() > 0)
  {
     cout << "Node or link information is missing. Would you like to continue? yes/no" << endl;
     getline(cin,checkstring);
     if(checkstring == "no" || checkstring == "NO" || checkstring =="No") exit(0);
  }

  cout << "Number of p2p links = " << p2pLinks.size() << endl;
  MobilityHelper mobility;
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel"); // These are all fixed entities, hence "constant mobility"
  mobility.SetPositionAllocator(positionAlloc);
  mobility.Install(p2pNodesCon);

  NS_LOG_INFO ("Create nodes.");

  vector<NodeContainer> p2pNodeContainers;
  string sourcename;
  string targetname;
  Ptr<Node> sourcenode;
  Ptr<Node> targetnode;
  P2PLink templink;
 
  for(i=0;i<p2pLinks.size();i++)
  {
    NodeContainer tempcontainer;
    templink = p2pLinks[i];
    sourcename = templink.source;
    //cout << "Source Name = " << sourcename << endl;
    targetname = templink.target;
    //cout << "Target Name = " << targetname << endl;
    sourcenode = Names::Find<Node>(sourcename);
    //cout << "Source Node = " << sourcenode << endl;
    targetnode = Names::Find<Node>(targetname);
    //cout << "Target Node = " << targetnode << endl;
    tempcontainer = NodeContainer(sourcenode,targetnode);
    p2pNodeContainers.push_back(tempcontainer);
  }
 
  // Enable OLSR
  //NS_LOG_INFO ("Enabling OLSR Routing.");
  //OlsrHelper olsr;
 
  //Ipv4StaticRoutingHelper staticRouting;
 
  //Ipv4ListRoutingHelper list;
  //list.Add (staticRouting, 0);
  //list.Add (olsr, 10);

  // Enable Nix-Vector routing
  time(&start);
  Ipv4NixVectorHelper nixRouting;
  Ipv4StaticRoutingHelper staticRouting;
  Ipv4ListRoutingHelper listRouting;
  listRouting.Add(staticRouting, 0);
  listRouting.Add(nixRouting, 10);
  time(&end);
  timeTaken = double(end - start);
  cout << "Time taken by Nix-Vector routing is: " << fixed << timeTaken << " sec." << endl;

  cout << "Installing Internet" << endl;
  InternetStackHelper internet;
  //internet.SetRoutingHelper (list); // has effect on the next Install ()
  internet.SetRoutingHelper (listRouting);
  internet.Install (p2pNodesCon);
  cout << "Number of nodes in container = " << p2pNodesCon.GetN() << endl;
 
  cout << "Creating Channels" << endl;
  // We create the channels first without any IP addressing information
  NS_LOG_INFO ("Create channels.");
  PointToPointHelper p2p;
  p2p.SetDeviceAttribute ("DataRate", StringValue ("5Gbps"));
  p2p.SetChannelAttribute ("Delay", StringValue ("100ms")); // 10us
  vector<NetDeviceContainer> netDevices;
  cout << "NodeContainers size = " << p2pNodeContainers.size() << endl;
  for(i=0;i<p2pNodeContainers.size();i++)
  {
    NetDeviceContainer tempdvc;
    NodeContainer tempnc;
    tempnc = p2pNodeContainers[i];
    //cout << "tempnc count = " << tempnc.GetN() << endl;
   // cout << "tempnc #1 = " << tempnc.Get(0) << endl;
    //cout << "tempnc #2 = " << tempnc.Get(1) << endl;
    if(tempnc.Get(0) != 0 && tempnc.Get(1) != 0)
    {
     tempdvc = p2p.Install(p2pNodeContainers[i]);
     //cout << "Hit here #1" << endl;
     netDevices.push_back(tempdvc);
     //cout << "Hit here #2" << endl;
    }
  }
  // Later, we add IP addresses.
  NS_LOG_INFO ("Assign IP Addresses.");
  cout << "Setting Addresses" << endl;
  Ipv4AddressHelper ipv4;
  vector<Ipv4InterfaceContainer> ipv4Addresses;
  uint32_t ipvcounter = 0;
  uint32_t basecounter = 1;
  string taddress;
  char* charaddress;

  for(i=0;i<netDevices.size();i++)
  {
    Ipv4InterfaceContainer ipv4Container;
    if(ipvcounter < 100)
    {
     ipvcounter++;
    }
    else
    {
     ipvcounter = 1;
     basecounter++;
    }
    taddress = "192." + to_string(168+basecounter) + "." + to_string(ipvcounter) + ".0";
    charaddress = const_cast<char*>(taddress.c_str());
    //cout << "Address #" << i+1 << "/" << netDevices.size() << ": " << charaddress << endl;
    ipv4.SetBase(charaddress, "255.255.255.0","0.0.0.1");
    ipv4Container = ipv4.Assign(netDevices[i]);
    //cout << ipv4Container.GetN() << endl;
    ipv4Addresses.push_back(ipv4Container);
  }
  cout << "Finished setting addresses" << endl;

  // Ipv4GlobalRoutingHelper::PopulateRoutingTables ();
  // Enable Nix-Vector routing
//   time(&start);
//   Ipv4NixVectorHelper nixRouting;
//   Ipv4StaticRoutingHelper staticRouting;
//   Ipv4ListRoutingHelper listRouting;
//   listRouting.Add(staticRouting, 0);
//   listRouting.Add(nixRouting, 10);
//   time(&end);
//   timeTaken = double(end - start);
  cout << "Time taken by Nix-Vector routing is: " << fixed << timeTaken << " sec." << endl;

  //  uint16_t port = 9;  // Discard port (RFC 863)
  //  cout << "Setting up onoff1" << endl;
  //  cout << ipv4Addresses.size() << endl;
  //  cout << ipv4Addresses[0].GetAddress(1) << endl;
  //  OnOffHelper onoff1("ns3::UdpSocketFactory",InetSocketAddress(ipv4Addresses[0].GetAddress(1),port));
  //  cout << "Setting up onoff2" << endl;
  //  OnOffHelper onoff2("ns3::UdpSocketFactory",InetSocketAddress(ipv4Addresses[1].GetAddress(1),port));
  //  onoff2.SetConstantRate (DataRate ("448kb/s"));
  //  ApplicationContainer onOffApp2 = onoff2.Install (p2pNodesCon.Get (2));
  //  onOffApp2.Start (Seconds (10.0));
  //  onOffApp2.Stop (Seconds (20.0));
  //  cout << "Setting up sink" << endl;
  //  PacketSinkHelper sink ("ns3::UdpSocketFactory",InetSocketAddress (Ipv4Address::GetAny (), port));
  //  NodeContainer sinks = NodeContainer (p2pNodesCon.Get (3), p2pNodesCon.Get (1));
  //  ApplicationContainer sinkApps = sink.Install (sinks);
  //  sinkApps.Start (Seconds (0.0));
  //  sinkApps.Stop (Seconds (21.0));

  // -------------------------------------------------------------------------------
  //  Helics federate
  // -------------------------------------------------------------------------------
  string enamestring;
  size_t tpos = 0;
  string token;
  NS_LOG_INFO("Number of filters " << endPointConfigObject["filters"].size());
  cout << "Number of filters " << endPointConfigObject["filters"].size() << endl;
  NS_LOG_INFO("Number of endpoints " << endPointConfigObject["endpoints"].size());
  cout << "Number of endpoints " << endPointConfigObject["endpoints"].size() << endl;

  std::vector<ApplicationContainer> helicsFilterApps;

  for (i = 0; i < endPointConfigObject["endpoints"].size(); i++)
  {
        tpos = 0;
        enamestring = endPointConfigObject["endpoints"][i]["name"].asString();
        while ((tpos = enamestring.find("/")) != std::string::npos)
        {
             token = enamestring.substr(0, tpos);
             enamestring.erase(0, tpos + 1);
        }

        NS_LOG_INFO("|NS_LOG_INFO| <<< enamestring : " << enamestring << ", filter " << helics_federate->getFilter(i).getName() << ", endpoint " << helics_federate->getEndpoint(i).getName());
        cout << "|cout| <<< enamestring : " << enamestring << ", filter " << helics_federate->getFilter(i).getName() << ", endpoint " << helics_federate->getEndpoint(i).getName() << endl;
        ApplicationContainer apps = helicsHelper.InstallFilter(Names::Find<Node>(enamestring), helics_federate->getFilter(i), helics_federate->getEndpoint(i));
        apps.Start(Seconds(0.0));
        apps.Stop(simTime);
        helicsFilterApps.push_back(apps);
        // cout << "\nNode name = " << Names::FindName(p2pNodesCon.Get(10)) << endl;
        // cout << "\nNode ID = " << p2pNodesCon.Get(10) -> GetId() << endl;
        // cout << "\nWhat's this = " << Names::Find(p2pNodesCon, enamestring) << endl;
        // p2p.EnablePcap("tesp_p2p_pcap", p2pNodesCon.Get(10)->GetId(), 1, false);
        for (int j = 0; j < p2pNodesCon.GetN(); j++)
        {
         if (Names::FindName(p2pNodesCon.Get(j)).compare(enamestring) == 0)
         {
           cout << "Setting up pcap files for " << enamestring << " devices." << endl;
           for (int k = 0; k < p2pNodesCon.Get(j)->GetNDevices(); k++)
           {
            p2p.EnablePcap("tespLoadshed_p2p_pcap", p2pNodesCon.Get(j)->GetDevice(k), false, false);
           }
         }
        }
  }
  //  p2p.EnablePcap("tesp_p2p_pcap", p2pNodesCon, false);
  //  AsciiTraceHelper ascii;
  //  cout << "Setting up Pcap files" << endl;
  //  p2p.EnableAsciiAll (ascii.CreateFileStream ("tesp_p2p.tr"));
  //  p2p.EnablePcapAll ("tesp_p2p");
  //  cout << "Finished setting up Pcap files" << endl;

  // AnimationInterface animate(animFileName);
  // animate.SetMobilityPollInterval (Seconds (30));
  // animate.SetMaxPktsPerTraceFile(99999999999999);
  // animate.EnableIpv4RouteTracking(routingFileName, Seconds(0.0), simTime);
  // for (i = 0; i < p2pNodesCon.GetN(); i++)
  // {
    // animate.UpdateNodeColor(p2pNodesCon.Get(i), 255, 0, 0);
    // animate.UpdateNodeSize(p2pNodesCon.Get(i)->GetId(), 2, 2);
    // cout << "Node name = " << Names::FindName(p2pNodesCon.Get(i)) << endl;
    // animate.UpdateNodeDescription(p2pNodesCon.Get(i), Names::FindName(p2pNodesCon.Get(i)));
  // }
  //   cout << "Setting up traffic" << endl;
  //   //   array<int, 3> trafficDestID = {46, 32, 49};
  //   array<int, 1> trafficSourceID = {58};
  //   array<int, 1> trafficDestID = {32};
  //   for (int iid = 0, jid = 0; iid < trafficSourceID.size() && jid < trafficDestID.size(); iid++, jid++)
  //   {
  //    TypeId tid = TypeId::LookupByName("ns3::UdpSocketFactory");
  //    Ptr<Socket> recvSink = Socket::CreateSocket(p2pNodesCon.Get(trafficDestID[iid]), tid);
  //    InetSocketAddress local = InetSocketAddress(Ipv4Address::GetAny(), 80);
  //    recvSink->Bind(local);
  //    recvSink->SetRecvCallback(MakeCallback(&ReceivePacket));

  //    Ptr<Socket> source = Socket::CreateSocket(p2pNodesCon.Get(trafficSourceID[jid]), tid);
  //    InetSocketAddress remote = InetSocketAddress(p2pNodesCon.Get(trafficDestID[iid])->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal(), 80);
  //    source->Connect(remote);
  //    Simulator::ScheduleWithContext(source->GetNode()->GetId(), Seconds(0.0), &GenerateTraffic, source, packetSize, numPackets, interPacketInterval);
  //   }
  cout << "Setting up simulation" << endl; 
  Simulator::Stop (simTime);
  NS_LOG_INFO ("Run Simulation. (from NS_LOG)");
  cout << "cout -- Run Simulation" << endl;
  time(&start);
  Simulator::Run ();
  Simulator::Destroy ();
  time(&end);
  timeTaken = double(end - start);
  // cout << "Time taken to run the ns-3 model is: " << fixed << timeTaken << setprecision(5) << " sec." << endl;
  cout << "Time taken to run the ns-3 model is: " << fixed << timeTaken << " sec." << endl;
  NS_LOG_INFO ("Done. (from NS_LOG)");
  cout << "cout -- Simulation Finished" << endl;
 
  return 0;
 }
