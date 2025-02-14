# Copyright (C) 2023 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: data.py
"""Path and Data functions for use within tesp_support.
"""

from os import path, chdir, environ
from importlib_resources import files
import argparse
import subprocess

"""
If your Python package needs to write to a file for shared data or configuration,
you can use standard platform/OS-specific system directories, such as 
~/.local/config/$appname or /usr/share/$appname/$version (Linux specific) [1]. 
A common approach is to add a read-only template file to the package directory 
that is then copied to the correct system directory if no pre-existing file is 
found.
"""

tesp_path = None
components = ["",
              "data",
              "examples",
              path.join("examples", "analysis"),
              path.join("examples", "capabilities"),
              "models",
              "scripts",
              "src",
              path.join("src", "tesp_support", "test")]

if 'TESPDIR' in environ:
    tesp_path = path.expanduser(environ['TESPDIR'])
else:
    tesp_path = path.join(path.expanduser('~'), "grid", "tesp")

# uncomment for debug
#print(tesp_path)
#tesp_path = path.join(path.expanduser('~'), '/tesp')
#chdir(tesp_path)
#tesp_path = path.join(path.expanduser('~'), '/tesp/tesp')

if path.isdir(tesp_path):
    for _dir in components:
        tmp = path.join(tesp_path, _dir)
        if path.isdir(tmp):
            #print(tmp + " directory has been installed for TESP")
            pass
        else:
            #print(tmp + " directory has NOT been installed for TESP")
            pass
else:
    # New instance
    try:
        chdir(path.expanduser('~/grid'))
        cmd = 'git clone --no-checkout https://github.com/pnnl/tesp'
        subprocess.Popen(cmd, shell=True).wait()
        chdir(tesp_path)
        cmd = 'git checkout HEAD scripts/tespPip.sh'
        subprocess.Popen(cmd, shell=True).wait()
        chdir('scripts')
        cmd = './tespPip.sh'
        subprocess.Popen(cmd, shell=True).wait()
    except FileExistsError:
        print("Can NOT write the TESP configure files -> " + tesp_path)
        pass


tesp_share = path.join(path.expandvars(tesp_path), 'data/')
comm_path = path.join(tesp_share, "comm/")
energyplus_path = path.join(tesp_share, "energyplus/")
feeders_path = path.join(tesp_share, "feeders/")
scheduled_path = path.join(tesp_share, "schedules/")
weather_path = path.join(tesp_share, "weather/")

tesp_model = path.join(path.expandvars(tesp_path), 'models/')
pypower_path = path.join(tesp_model, "pypower/")

tesp_test = path.join(path.expandvars(tesp_path),  'src', 'tesp_support', 'test/')

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

    parcel = ['git', 'checkout', 'HEAD']
    choice = int(args.component[0])
    if 9 > choice > 0:
        parcel.append(components[choice])
        print("Component ->", parcel[-1])
    else:
        print("Bad choice, choose 1 through 9")
        return

    component = path.join(tesp_path, components[choice])
    if path.isdir(component):
        print("It seems we have a copy of " + component)
        return

    # can proceed with the copy
    chdir(tesp_path)
    subprocess.Popen(parcel, shell=False).wait()
    print('Output directory: ', tesp_path + "/" + components[choice])
