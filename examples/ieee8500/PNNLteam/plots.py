# usage 'python plots metrics_root'
import sys
import os.path

rootname = sys.argv[1]
dictname = rootname + '_glm_dict.json'
if not os.path.exists(dictname):
  dictname = 'inv8500_glm_dict.json'

import tesp_support.process_gld as gp
gp.process_gld (rootname, dictname)

import tesp_support.process_inv as gp
gp.process_inv (rootname, dictname)


