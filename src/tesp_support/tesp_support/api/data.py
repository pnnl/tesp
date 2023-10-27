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

    _parser = argparse.ArgumentParser(description=description)
    if 'p' in args:
        _parser.add_argument('-p', '--port', nargs=1)
    if 'i' in args:
        _parser.add_argument('-i', '--input_file', nargs=1)
    if 'o' in args:
        _parser.add_argument('-o', '--output_file', nargs=1)
    if 'd' in args:
        _parser.add_argument('-d', '--output_dir', nargs=1)
    _args = _parser.parse_args()

    _error = False
    if 'i' in args:
        if _args.input_file is None:
            _error = True
        elif not path.isfile(_args.input_file[0]):
            print('ERROR-> Input file ' + _args.input_file[0] + ' not found')
            _error = True
    if 'p' in args:
        if _args.port is None:
            _error = True
    if 'o' in args:
        if _args.output_file[0] is None:
            _error = True
    if 'd' in args:
        if _args.output_dir is None:
            _error = True
        elif not path.isdir(_args.output_dir[0]):
            print('ERROR-> Output directory ' + _args.output_dir[0] + ' not found')
            _error = True
    if _error:
        print(description + " not loaded, desired input needed")
        print(_parser.format_usage())

    return _error, _args


def tesp_download_data():
    description = "Download TESP Model, Schedules and Weather Data"
    error, args = arguments(description=description, args='d')
    if error:
        return

    print('Output directory: ', args.output_dir[0])


def tesp_download_analysis():
    description = "Download TESP Analysis Case Studies Data"
    error, args = arguments(description=description, args='d')
    if error:
        return

    print('Output directory: ', args.output_dir[0])


def tesp_download_examples():
    description = "Download TESP Examples Case Data"
    error, args = arguments(description=description, args='d')
    if error:
        return

    print('Output directory: ', args.output_dir[0])
