'''
.. module:: fnss_ns3_MatrixTopoEx

:platform: Unix, Windows
:synopsis: Call functions to build, visualize, and run the model.

.. note:: This is a simple note.

.. warning:: This is a warning

.. versionadded:: version

.. versionchanged:: version

.. seealso:: see this as well

.. moduleauthor:: Laurentiu Marinovici
'''

__license__ = "BSD"
__revision__ = " $Id: $ "
__docformat__ = 'reStructuredText'

import pprint
try:
  import ns.core
  import ns.flow_monitor
  from fnssTopology import *
  from ns3Model import *
except ImportError:
  pass
try:
  import ns.visualizer
except ImportError:
  pass

pp = pprint.PrettyPrinter(indent = 2)

def main(argv):
  '''
  This is the main function.

  Args:
    argv(str): just a fake argument for testing purposes

  '''
  SimTime = 20
  flowName = "n-node-ppp.xml"
  cmd = ns.core.CommandLine()
  cmd.ExampleType = None
  cmd.AddValue("ExampleType", "The type of example running.")
  cmd.Parse(argv)

  if cmd.ExampleType == None:
    print("\nRunning no argument case\n")
  elif cmd.ExampleType == "Type1":
    print("\nRunning Type 1\n")
  else:
    print("\nRunning any other\n")
  
  '''

  :buildFNSStopology: build network topology using FNSS

  '''
  topo = buildFNSStopology()
  plotTopology(topo)
  buildNS3model(topo)

  flowMon = ns.flow_monitor.FlowMonitor()
  flowMonHelper = ns.flow_monitor.FlowMonitorHelper()
  flowMon = flowMonHelper.InstallAll()

  ns.core.Simulator.Stop(ns.core.Seconds(SimTime))
  ns.core.Simulator.Run()
  flowMon.SerializeToXmlFile(flowName, True, True)
  ns.core.Simulator.Destroy()

if __name__ == "__main__":
  import sys
  main(sys.argv)