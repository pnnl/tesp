# usage 'python plots metrics_root'
import sys

import tesp_support.api.process_pypower as pp
import tesp_support.api.process_gld as pg
import tesp_support.api.process_houses as ph
import tesp_support.process_agents as pa
import tesp_support.api.process_eplus as pe

rootname = sys.argv[1]

pp.process_pypower(rootname)
pg.process_gld(rootname)
ph.process_houses(rootname)
pa.process_agents(rootname)
pe.process_eplus(rootname)
