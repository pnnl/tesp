# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: plots.py

# usage 'python plots metrics_root'
import os
import sys

import tesp_support.api.process_gld as gp
import tesp_support.api.process_inv as ip

rootname = sys.argv[1]

diction_name = rootname + '_glm_dict.json'
if not os.path.exists(diction_name):
    diction_name = 'inv8500_glm_dict.json'

gmetrics = gp.read_gld_metrics(os.getcwd(), rootname, diction_name)
gp.plot_gld(gmetrics)
# gp.process_gld (rootname, diction_name)
ip.process_inv(rootname, diction_name)
