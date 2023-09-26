# Copyright (C) 2023 Battelle Memorial Institute
# file: data.py
"""Path and Data functions for use within tesp_support.
"""
from os import path
from sys import platform
from importlib_resources import files

tesp_share = path.expandvars('$TESPDIR/data/')
comm_path = tesp_share + 'comm/'
energyplus_path = tesp_share + 'energyplus/'
feeders_path = tesp_share + 'feeders/'
scheduled_path = tesp_share + 'schedules/'
weather_path = tesp_share + 'weather/'

tesp_model = path.expandvars('$TESPDIR/models/')
pypower_path = tesp_model + 'pypower/'

tesp_test = path.expandvars('$TESPDIR/src/tesp_support/test/')

glm_entities_path = files('tesp_support.api.datafiles').joinpath('glm_classes.json')
piq_entities_path = files('tesp_support.api.datafiles').joinpath('grid_PIQ.json')
feeder_entities_path = files('tesp_support.api.datafiles').joinpath('feeder_defaults.json')

"""
If your Python package needs to write to a file for shared data
or configuration, you can use standard platform/OS-specific system directories, 
such as ~/.local/config/$appname or /usr/share/$appname/$version (Linux specific) [1]. 
A common approach is to add a read-only template file to the package directory 
that is then copied to the correct system directory if no pre-existing file is found.
"""


if platform == "linux" or platform == "linux2":
    # Linux
    path = "~/.config/tesp"
elif platform == "darwin":
    # OS X
    path = "~/.config/tesp"
elif platform == "win32":
    # Windows
    path = "~/.config/tesp"


def download_data():
    print("download data")


def download_analysis():
    print("download analysis")


def download_examples():
    print("download examples")
