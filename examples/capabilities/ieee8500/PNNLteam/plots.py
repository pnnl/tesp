# Copyright (C) 2021 Battelle Memorial Institute
# file: plots.py

# usage 'python plots metrics_root'
import os
import sys

import tesp_support.process_gld as gp
import tesp_support.process_inv as ip

rootname = sys.argv[1]
dictname = rootname + '_glm_dict.json'
if not os.path.exists(dictname):
    dictname = 'inv8500_glm_dict.json'

gmetrics = gp.read_gld_metrics(os.getcwd(), rootname, dictname)
gp.plot_gld(gmetrics)
# gp.process_gld (rootname, dictname)
ip.process_inv(rootname, dictname)
