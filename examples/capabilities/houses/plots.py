# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: plots.py

# usage 'python3 plots.py'
import os

import tesp_support.api.process_gld as gp
import tesp_support.api.process_houses as hp
import tesp_support.api.process_voltages as vp

rootname = 'test_houses'

gmetrics = gp.read_gld_metrics(os.getcwd(), rootname)
gp.plot_gld(gmetrics)
hp.plot_houses(gmetrics)
vp.plot_voltages(gmetrics)
