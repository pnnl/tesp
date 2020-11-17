# usage 'python plots metrics_root'
import sys
import os
import tesp_support.process_pypower as pp
import tesp_support.process_gld as gp
import tesp_support.process_houses as hp
import tesp_support.process_voltages as vp
import tesp_support.process_agents as ap
import tesp_support.process_eplus as ep

rootname = sys.argv[1]

if os.path.exists ('bus_' + rootname + '_metrics.json'):
  pmetrics = pp.read_pypower_metrics (rootname)
  pp.plot_pypower (pmetrics)

if os.path.exists ('substation_' + rootname + '_metrics.json'):
  gmetrics = gp.read_gld_metrics (rootname)
  gp.plot_gld (gmetrics)
  hp.plot_houses (gmetrics)
  vp.plot_voltages (gmetrics)

if os.path.exists ('auction_' + rootname + '_metrics.json'):
  ametrics = ap.read_agent_metrics (rootname)
  ap.plot_agents (ametrics)

if os.path.exists ('eplus_' + rootname + '_metrics.json'):
  emetrics = ep.read_eplus_metrics (rootname)
  ep.plot_eplus (emetrics)

