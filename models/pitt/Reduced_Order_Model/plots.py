# usage 'python plots metrics_root'
import sys
rootname = sys.argv[1]

import tesp_support.process_pypower as pp
pp.process_pypower (rootname)

import tesp_support.process_gld as gp
gp.process_gld (rootname)

import tesp_support.process_houses as hp
hp.process_houses (rootname)

import tesp_support.process_agents as ap
ap.process_agents (rootname)

import tesp_support.process_eplus as ep
ep.process_eplus (rootname)


