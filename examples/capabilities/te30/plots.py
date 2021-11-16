# Copyright (C) 2021 Battelle Memorial Institute
# file: plots.py

# usage 'python plots metrics_root'
import os
import sys

import tesp_support.process_agents as ap
import tesp_support.process_eplus as ep
import tesp_support.process_gld as gp
import tesp_support.process_houses as hp
import tesp_support.process_pypower as pp
import tesp_support.process_voltages as vp

rootname = sys.argv[1]

pmetrics = pp.read_pypower_metrics(os.getcwd(), rootname)
pp.plot_pypower(pmetrics)

if os.path.exists('auction_' + rootname + '_metrics.json'):
    ametrics = ap.read_agent_metrics(rootname, 'TE_Challenge_agent_dict.json')
    ap.plot_agents(ametrics)

gmetrics = gp.read_gld_metrics(rootname, 'TE_Challenge_glm_dict.json')
gp.plot_gld(gmetrics)
hp.plot_houses(gmetrics)
vp.plot_voltages(gmetrics)

emetrics = ep.read_eplus_metrics(os.getcwd(), rootname)
ep.plot_eplus(emetrics)

# ip.process_inv (rootname, 'TE_Challenge_glm_dict.json')
