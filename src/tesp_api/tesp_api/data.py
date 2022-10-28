# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: data.py
""" Path and Data functions for use within tesp_support, including new agents.
"""
from os import path

tesp_share = path.expandvars('$TESPDIR/data/')
comm_path = tesp_share + 'comm/'
entities_path = tesp_share + 'entities/'
energyplus_path = tesp_share + 'energyplus/'
feeders_path = tesp_share + 'feeders/'
scheduled_path = tesp_share + 'schedules/'
weather_path = tesp_share + 'weather/'

tesp_model = path.expandvars('$TESPDIR/models/')
pypower_path = tesp_model + 'pypower/'

