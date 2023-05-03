# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: prepare_cases.py

import tesp_support.original.glm_dictionary as gd
import tesp_support.original.prep_precool as pp

gd.glm_dict('inv30', te30=True)
pp.prep_precool('inv30')
gd.glm_dict('invti30', te30=True)
pp.prep_precool('invti30')
gd.glm_dict('inv8500')
pp.prep_precool('inv8500', 15)
