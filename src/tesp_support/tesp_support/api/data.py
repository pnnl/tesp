# Copyright (C) 2023 Battelle Memorial Institute
# file: data.py
"""Path and Data functions for use within tesp_support.
"""

from os import path, chdir, mkdir, environ
from importlib_resources import files
import argparse
import subprocess

"""
If your Python package needs to write to a file for shared data
or configuration, you can use standard platform/OS-specific system directories, 
such as ~/.local/config/$appname or /usr/share/$appname/$version (Linux specific) [1]. 
A common approach is to add a read-only template file to the package directory 
that is then copied to the correct system directory if no pre-existing file is found.
"""

tesp_path = None
components = ["",
              "data",
              "examples",
              "examples/analysis",
              "examples/capabilities",
              "models",
              "scripts",
              "src",
              "src/tesp_support/test"]

if 'TESPDIR' in environ:
    tesp_path = environ['TESPDIR']
else:
    tesp_path = path.expanduser('~') + '/tesp'

# uncomment for debug
# tesp_path = path.expanduser('~') + '/tesp'

if path.isdir(tesp_path):
    for _dir in components:
        tmp = tesp_path + '/' + _dir
        if path.isdir(tmp):
            # print(tmp + " directory has been installed for TESP")
            pass
        else:
            # print(tmp + " directory has NOT been installed for TESP")
            pass
else:
    # New instance
    try:
        mkdir(tesp_path)
        # print("Writing the TESP setting config file -> " + tesp_path)
        # make_settings(tesp_path)
    except FileExistsError:
        print("Can NOT write the TESP setting config file -> " + tesp_path)
        pass


tesp_share = path.expandvars(tesp_path + '/data/')
comm_path = tesp_share + 'comm/'
energyplus_path = tesp_share + 'energyplus/'
feeders_path = tesp_share + 'feeders/'
scheduled_path = tesp_share + 'schedules/'
weather_path = tesp_share + 'weather/'

tesp_model = path.expandvars(tesp_path + '/models/')
pypower_path = tesp_model + 'pypower/'

tesp_test = path.expandvars(tesp_path + '/src/tesp_support/test/')

glm_entities_path = files('tesp_support.api.datafiles').joinpath('glm_classes.json')
piq_entities_path = files('tesp_support.api.datafiles').joinpath('grid_PIQ.json')
feeder_entities_path = files('tesp_support.api.datafiles').joinpath('feeder_defaults.json')


def arguments(description="", args=""):
    _parser = argparse.ArgumentParser(description=description)
    if 'p' in args:
        _parser.add_argument('-p', '--port', nargs=1)
    if 'i' in args:
        _parser.add_argument('-i', '--input_file', nargs=1)
    if 'c' in args:
        _parser.add_argument('-c', '--component', nargs=1)
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
    if 'c' in args:
        if _args.component is None:
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
        print(description + "\nNothing loaded, desired input needed")
        print(_parser.format_usage())

    return _error, _args


def tesp_component():
    description = ("Download TESP Component\n"
                   "  1 - Data Schedules, Feeder, Weather\n"
                   "  2 - All Examples and Autotest\n"
                   "  3 - Example Analysis\n"
                   "  4 - Example Capabilities\n"
                   "  5 - Power Models\n"
                   "  6 - Scripts\n"
                   "  7 - Source\n"
                   "  8 - Test\n")
    error, args = arguments(description=description, args='c')
    if error:
        return

    parcel = ["svn", "checkout", "https://github.com/pnnl/tesp/trunk/"]

    choice = int(args.component[0])
    if 9 > choice > 0:
        parcel[2] = parcel[2] + components[choice]
        print("Component ->", parcel[2])
    else:
        print("Bad choice, choose 1 through 9")
        return

    tmp = tesp_path + '/' + components[choice]
    if path.isdir(tmp):
        print("It seems we have a copy of " + tmp)
        return

    # can proceed with the copy
    chdir(tesp_path)
    p = subprocess.Popen(parcel, shell=False)
    p.wait()
    line = ["rm", "-rf", components[choice] + "/.svn"]
    p = subprocess.Popen(line, shell=False)
    p.wait()
    print('Output directory: ', tesp_path + "/" + components[choice])
