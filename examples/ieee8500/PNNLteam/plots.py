# usage 'python plots metrics_root'
import sys
rootname = sys.argv[1]

import tesp_support.process_gld as gp
gp.process_gld (rootname)

import tesp_support.process_inv as gp
gp.process_inv (rootname)


