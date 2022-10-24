# usage 'python plots metrics_root'
import sys
import tesp_support.api as tesp

rootname = sys.argv[1]

tesp.process_pypower(rootname)
tesp.process_gld(rootname)
tesp.process_houses(rootname)
tesp.process_agents(rootname)
tesp.process_eplus(rootname)
