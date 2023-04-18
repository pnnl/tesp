# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: plots.py

# usage 'python plots metrics_root'
import os
import sys

import tesp_support.process_pypower as pp
import tesp_support.process_gld as pg
import tesp_support.process_houses as ph
import tesp_support.process_agents as pa
import tesp_support.process_eplus as pe

name_root = sys.argv[1]

pmetrics = pp.read_pypower_metrics(os.getcwd(), name_root)
pp.plot_pypower(pmetrics)

if os.path.exists('auction_' + name_root + '_metrics.json'):
    ametrics = pa.read_agent_metrics(os.getcwd(), name_root, 'TE_Challenge_agent_dict.json')
    pa.plot_agents(ametrics)

gmetrics = pg.read_gld_metrics(os.getcwd(), name_root, 'TE_Challenge_glm_dict.json')
pg.plot_gld(gmetrics)
ph.plot_houses(gmetrics)
pv.plot_voltages(gmetrics)

emetrics = pe.read_eplus_metrics(os.getcwd(), name_root)
pe.plot_eplus(emetrics)

# tesp.process_inv (name_root, 'TE_Challenge_glm_dict.json')
