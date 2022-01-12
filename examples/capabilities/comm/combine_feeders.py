# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: combine_feeders.py

import tesp_support.api as tesp

tesp.make_tesp_case ('Feeder1.json')
tesp.add_tesp_feeder ('Feeder2.json')
tesp.add_tesp_feeder ('Feeder3.json')
tesp.add_tesp_feeder ('Feeder4.json')

case = 'CombinedCase'
feeders = ['Feeder1', 'Feeder2', 'Feeder3', 'Feeder4']

xfmva = 20.0

tesp.merge_glm (case, feeders, xfmva)
tesp.merge_glm_dict (case, feeders, xfmva)
tesp.merge_agent_dict (case, feeders, xfmva)
tesp.merge_substation_yaml (case, feeders)
tesp.merge_fncs_config (case, feeders)
tesp.merge_gld_msg (case, feeders)
tesp.merge_substation_msg (case, feeders)

