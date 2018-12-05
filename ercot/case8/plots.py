# usage 'python plots metrics_root'
import os
import sys
import tesp_support.process_gld as gp
import tesp_support.process_houses as hp
import tesp_support.process_agents as ap

rootname = sys.argv[1]

gp.process_gld (rootname)
hp.process_houses (rootname)

exists = os.path.isfile ('auction_' + rootname + '_metrics.json')
if exists:
  ap.process_agents (rootname)


