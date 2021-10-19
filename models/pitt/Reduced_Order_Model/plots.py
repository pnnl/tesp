# usage 'python plots metrics_root'
import sys
rootname = sys.argv[1]

import models.pitt.Reduced_Order_Model.tesp_support.process_pypower as pp
pp.process_pypower (rootname)

from models.pitt.Reduced_Order_Model import tesp_support as gp, tesp_support as ap

gp.process_gld (rootname)

import models.pitt.Reduced_Order_Model.tesp_support.process_houses as hp
hp.process_houses (rootname)

ap.process_agents (rootname)

import models.pitt.Reduced_Order_Model.tesp_support.process_eplus as ep
ep.process_eplus (rootname)


