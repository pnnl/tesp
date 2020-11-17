# usage 'python plots metrics_root'
import sys
import os.path

rootname = sys.argv[1]
dictname = rootname + '_glm_dict.json'
if not os.path.exists(dictname):
  dictname = 'inv8500_glm_dict.json'

import tesp_support.process_gld as gp
gmetrics = gp.read_gld_metrics (rootname, dictname)
gp.plot_gld (gmetrics)
#gp.process_gld (rootname, dictname)

import tesp_support.process_inv as ip
ip.process_inv (rootname, dictname)

