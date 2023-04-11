# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: plots.py

# usage 'python plots metrics_root'
import os
import sys

import tesp_support.tesp_api as tesp

name_root = sys.argv[1]

pmetrics = tesp.read_pypower_metrics(os.getcwd(), name_root)
tesp.plot_pypower(pmetrics)

if os.path.exists('auction_' + name_root + '_metrics.json'):
    ametrics = tesp.read_agent_metrics(os.getcwd(), name_root, 'TE_Challenge_agent_dict.json')
    tesp.plot_agents(ametrics)

gmetrics = tesp.read_gld_metrics(os.getcwd(), name_root, 'TE_Challenge_glm_dict.json')
tesp.plot_gld(gmetrics)
tesp.plot_houses(gmetrics)
tesp.plot_voltages(gmetrics)

emetrics = tesp.read_eplus_metrics(os.getcwd(), name_root)
tesp.plot_eplus(emetrics)

# tesp.process_inv (name_root, 'TE_Challenge_glm_dict.json')
