# usage 'python plots metrics_root'
import sys

import tesp_support.api.process_pypower as pp
import tesp_support.api.process_gld as pg
import tesp_support.api.process_houses as ph
import tesp_support.original.process_agents as pa
import tesp_support.api.process_eplus as pe

root_name = sys.argv[1]

pp.process_pypower(root_name)
pg.process_gld(root_name)
ph.process_houses(root_name)
pa.process_agents(root_name)
pe.process_eplus(root_name)
