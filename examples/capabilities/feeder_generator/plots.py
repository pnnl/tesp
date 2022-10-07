# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: plots.py

# usage 'python plots metrics_root'
import os
import sys


import tesp_support.process_agents as tesp_a
import tesp_support.process_gld as tesp_g
import tesp_support.process_houses as tesp_h
import tesp_support.process_voltages as tesp_v
# import tesp_support.process_eplus as tesp_e
# import tesp_support.process_pypower as tesp_p

if __name__ == '__main__':
    name_root = sys.argv[1]

    # Comment out if don't you want power metrics plot
    # pmetrics = tesp_p.read_pypower_metrics(os.getcwd(), name_root)
    # tesp_p.plot_pypower(pmetrics)

    if os.path.exists('auction_' + name_root + '_metrics.json'):
        ametrics = tesp_a.read_agent_metrics(os.getcwd(), name_root, f'{name_root}_agent_dict.json')
        tesp_a.plot_agents(ametrics)

    gmetrics = tesp_g.read_gld_metrics(os.getcwd(), name_root, f'{name_root}_glm_dict.json')
    tesp_g.plot_gld(gmetrics)
    tesp_h.plot_houses(gmetrics)
    tesp_v.plot_voltages(gmetrics)

    # Comment out if don't you want penerrrgyplus metrics plot
    # emetrics = tesp_e.read_eplus_metrics(os.getcwd(), name_root)
    # tesp_e.plot_eplus(emetrics)

    # tesp.process_inv (name_root, 'Test_Challenge_glm_dict.json')
