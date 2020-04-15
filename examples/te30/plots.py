# usage 'python plots metrics_root'
import sys
import os
import tesp_support.process_pypower as pp
import tesp_support.process_agents as ap
import tesp_support.process_gld as gp
import tesp_support.process_houses as hp
import tesp_support.process_eplus as ep

rootname = sys.argv[1]

pp.process_pypower (rootname)

if os.path.exists ('auction_' + rootname + '_metrics.json'):
  ap.process_agents (rootname, 'TE_Challenge_agent_dict.json')

gp.process_gld (rootname, 'TE_Challenge_glm_dict.json')

hp.process_houses (rootname, 'TE_Challenge_glm_dict.json')

ep.process_eplus (rootname)


