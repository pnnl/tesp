# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: combine_feeders.py

import tesp_support.original.case_merge as cm
import tesp_support.original.tesp_case as tc

tc.make_tesp_case('Feeder1.json')
tc.add_tesp_feeder('Feeder2.json')
tc.add_tesp_feeder('Feeder3.json')
tc.add_tesp_feeder('Feeder4.json')

case = 'CombinedCase'
feeders = ['Feeder1', 'Feeder2', 'Feeder3', 'Feeder4']

xfmva = 20.0

cm.merge_glm(case, feeders, xfmva)
cm.merge_glm_dict(case, feeders, xfmva)
cm.merge_agent_dict(case, feeders, xfmva)
cm.merge_substation_yaml(case, feeders)
cm.merge_fncs_config(case, feeders)
cm.merge_gld_msg(case, feeders)
cm.merge_substation_msg(case, feeders)
