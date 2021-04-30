# usage 'python3 plots.py'
import sys
import os
import tesp_support.process_gld as gp
import tesp_support.process_houses as hp
import tesp_support.process_eplus as ep
import tesp_support.process_inv as ip
import tesp_support.process_voltages as vp

rootname = 'test_houses'

gmetrics = gp.read_gld_metrics (rootname)
gp.plot_gld (gmetrics)
#hp.plot_houses (gmetrics)
vp.plot_voltages (gmetrics)

