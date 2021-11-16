# Copyright (C) 2021 Battelle Memorial Institute
# file: prepare_cases.py

import tesp_support.api as tesp
tesp.glm_dict ('inv30',te30=True)
tesp.prep_precool ('inv30')
tesp.glm_dict ('invti30',te30=True)
tesp.prep_precool ('invti30')
tesp.glm_dict ('inv8500')
tesp.prep_precool ('inv8500', 15)

