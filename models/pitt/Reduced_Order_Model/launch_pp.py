# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: launch_pp.py

import tesp_support.api.tso_PYPOWER_f as pp

pp.pypower_loop_f('TE_pp.json', 'TE')
