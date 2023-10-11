# Copyright (C) 2023 Battelle Memorial Institute
# file: data.py
"""Path and Data functions for use within tesp_support.
"""

from os import path
from sys import platform
import argparse
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
    t_path = "~/.config/tesp"
elif platform == "darwin":
    # OS X
    t_path = "~/.config/tesp"
elif platform == "win32":
    # Windows
    t_path = "~/.config/tesp"


def arguments(description="", args=""):

    parser = argparse.ArgumentParser(description=description)
    if 'p' in args:
        parser.add_argument('-p', '--port', nargs=1)
    if 'i' in args:
        parser.add_argument('-i', '--input_file', nargs=1)
    if 'o' in args:
        parser.add_argument('-o', '--output_file', nargs=1)
    _args = parser.parse_args()

    error = False
    if 'i' in args:
        if _args.input_file is None:
            print('ERROR-> Input file missing')
            error = True
        elif not path.isfile(_args.input_file[0]):
            print('ERROR-> Input file ' + _args.input_file[0] + ' not found')
            error = True
    if 'p' in args:
        if _args.port is None:
            print('ERROR-> Input port is missing')
            error = True
    if 'o' in args:
        if _args.output_file[0] is None:
            print('ERROR-> Output file missing')
            error = True
    if error:
        print('ERROR-> ' + description + " not loaded")
        print(parser.format_usage())

    return error, _args


def download_data():
    print("download data")


def download_analysis():
    print("download analysis")


def download_examples():
    print("download examples")
