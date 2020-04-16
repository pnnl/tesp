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

pp.process_pypower (rootname)
gp.process_gld (rootname)
hp.process_houses (rootname)
vp.process_voltages (rootname)
ap.process_agents (rootname)

if os.path.exists ('eplus_' + rootname + '_metrics.json'):
  ep.process_eplus (rootname)

