# Copyright (c) 2021-2023 Battelle Memorial Institute
# file: launch_pp.py

import tesp_support.original.tso_PYPOWER_f as pp

pp.tso_pypower_loop_f('TE_pp.json', 'TE')
