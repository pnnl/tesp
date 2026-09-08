# Copyright (c) 2021-2025 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: helpers_dsot.py
""" Utility functions for use within tesp_support, including new agents.
This is DSO+T specific helper functions
"""

import platform
import subprocess
from copy import deepcopy
from enum import IntEnum
from os import environ, getcwd, path

import numpy as np

from ..api.helpers import HelicsMsg


def write_mircogrids_management_script(case_path, system_config=None, substation_config=None,
                                       weather_config=None):
    """ Write experiment management scripts from JSON configuration data,
    linux ans helics only

    Reads the simulation configuration file or dictionary and writes

    - run.{sh, bat}, simple run script to launch experiment
    - kill.{sh, bat}, simple run script to kill experiment
    - clean.{sh, bat}, simple run script to clean generated output files from the experiment

    Args:
        case_path (str): path to the experiment case
        system_config (dict): configuration of the system for the experiment case
        substation_config (dict): configuration of the substations in the experiment case
        weather_config (dict): configuration of the climates being used
    """

    out_folder = './' + case_path
    out_path = system_config['out_path']
    if out_path == "":
        out_path = "."
    dbg_options = ['', 'gdb -x ../../gdbinit --args ', 'valgrind --track-origins=yes ']
    dbg = dbg_options[system_config['gld_debug']]

    with open(out_folder + '/run.sh', 'w') as outfile:
        outfile.write('# !/bin/bash\n\n')

        outfile.write('with_market=1\n')
        outfile.write('if [ "$1" = "base" ]\n')
        outfile.write('then\n')
        outfile.write('  with_market=0\n')
        outfile.write('fi\n\n')

        # ## Monish Edits: Adding a PythonPath to point towards TESP_support directories
        tesp_path = getcwd() + ''
        outfile.write(f'export PYTHONPATH={tesp_path}:$PYTHONPATH;\n')

        outfile.write(
            '(helics_broker -t="zmq" --federates={} --name=mainbroker --loglevel=warning &> {}/broker.log &)\n'.format(str(len(substation_config) * 2 + sum(
                [len(substation_config[dso]['microgrids']) for dso in substation_config]) + sum(
                [len(substation_config[dso]['generators']) for dso in substation_config]) + len(
                weather_config)), out_path))

        for w_key in weather_config:
            outfile.write(f'cd {w_key}\n')
            outfile.write(f'(export WEATHER_CONFIG=weather_Config.json '
                          f'&& exec python3 -c "import tesp_support.consensus.weather_agent as tesp;'
                          f'tesp.startWeatherAgent(\'weather.dat\')" &> {out_path}/{w_key}_weather.log &)\n')
            outfile.write('cd ..\n')

        for sub_key, sub_val in substation_config.items():
            outfile.write(f'cd {sub_val["substation"]}\n')
            outfile.write(f'({dbg}gridlabd -D USE_HELICS -D METRICS_FILE="{out_path}/{sub_val["substation"]}_metrics_" '
                          f'{sub_val["substation"]}.glm &> {out_path}/{sub_val["substation"]}_gridlabd.log &)\n')
            outfile.write('cd ..\n')

            outfile.write(f'cd {sub_key}\n')
            outfile.write(f'(exec python3 -c "import tesp_support.consensus.dso_agent as DSO_agent;'
                          f'DSO_agent.substation_loop(\'{sub_val["substation"]}_agent_dict.json\',\'{sub_val["substation"]}\',$with_market)" &> '
                          f'{out_path}/{sub_key}_substation.log &)\n')
            outfile.write('cd ..\n')

            for microgrid_key in sub_val['microgrids']:
                outfile.write(f'cd {microgrid_key}\n')
                outfile.write(f'(exec python3 -c "import tesp_support.consensus.microgrid_agent as MG_agent;'
                              f'MG_agent.substation_loop(\'{microgrid_key}_agent_dict.json\',\'{microgrid_key}\',$with_market)" &> '
                              f'{out_path}/{microgrid_key}_substation.log &)\n')
                outfile.write('cd ..\n')

            for dg_key in sub_val['generators']:
                outfile.write(f'cd {dg_key}\n')
                outfile.write(f'(exec python3 -c "import tesp_support.consensus.dg_agent as DG_agent;'
                              f'DG_agent.substation_loop(\'{dg_key}_agent_dict.json\',\'{dg_key}\',$with_market)" &> '
                              f'{out_path}/{dg_key}_substation.log &)\n')
                outfile.write('cd ..\n')

    with open(out_folder + '/monitor.sh', 'w') as outfile:
        outfile.write('# !/bin/bash\n\n')
        outfile.write("""
# first add header, simultaneously creating/overwriting the file
top -w 512 cbn 1 | grep "PID" | egrep -v "top|grep" > stats.log 
# then, in background, run top in batch mode (this will not stop as is, unless in docker)
top -w 512 cbd 60 | egrep -v "top|Tasks|Cpu|Mem|Swap|PID|^$" >> stats.log & 

# manually run every so often a check to see if we can quit this script (i.e. once sim is over, mostly for docker)
while sleep 120; do
  echo "still running at $(TZ='America/Los_Angeles' date)"
  ps aux | grep python | grep -q -v grep | grep -q -v schedule
  PROCESS_1_STATUS=$?
  ps aux | grep gridlabd | grep -q -v grep
  PROCESS_2_STATUS=$?
  ps aux | grep helics_broker | grep -q -v grep
  PROCESS_3_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If all are not 0, then we are done with the main background processes, so the container can end
  if [ $PROCESS_1_STATUS -ne 0 ] && [ $PROCESS_2_STATUS -ne 0 ] && [ $PROCESS_3_STATUS -ne 0 ]; then
    echo "All processes (python, gridlabd, fncs_broker) have exited, so we are done."
    # TODO: kill top manually?
    # TODO: then, massage stats.log into slightly easier-to-read TSV with: sed -i 's/./&"/68;s/$/"/;$d' stats.log
    #  which wraps the commands in quotes and removes the last line which could be cut off
    exit 1
  fi
done                    
""")

    with open(out_folder + '/kill.sh', 'w') as outfile:
        if 'HELICS' in system_config:
            outfile.write('pkill -9 helics_broker\n')
        if 'FNCS' in system_config:
            outfile.write('pkill -9 fncs_broker\n')
        outfile.write('pkill -9 python\n')
        outfile.write('pkill -9 gridlab\n')

    with open(out_folder + '/clean.sh', 'w') as outfile:
        outfile.write('cd ' + out_path + '\n')
        outfile.write('find . -name \\*.log -type f -delete\n')
        outfile.write('find . -name \\*.csv -type f -delete\n')
        # outfile.write('find . -name \\*.out -type f -delete\n')
        # outfile.write('find . -name \\*metrics*.json* -type f -delete\n')
        # outfile.write('find . -name \\*metrics*.h5 -type f -delete\n')
        # outfile.write('find . -name \\*model_dict.json -type f -delete\n')
        outfile.write('find . -name \\*diagnostics.txt -type f -delete\n')
        outfile.write('find . -name \\*log.txt -type f -delete\n')
        outfile.write('cd -\n')

    subprocess.run(['chmod', '+x', out_folder + '/run.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/monitor.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/kill.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/clean.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/docker-run.sh'], check=False)
    try:
        subprocess.run(['chmod', '+x', out_folder + '/tesp_monitor.sh'], check=False)
    except FileNotFoundError:
        pass


def write_dsot_management_script(master_file, case_path, config=None, system_config=None, substation_config=None,
                                 weather_config=None):
    """ Write experiment management scripts from JSON configuration data,
    linux and helics only

    Reads the simulation configuration file or dictionary and writes

    - run.{sh, bat}, simple run script to launch experiment
    - kill.{sh, bat}, simple run script to kill experiment
    - clean.{sh, bat}, simple run script to clean generated output files from the experiment

    Args:
        master_file (str): name of the master file to the experiment case
        case_path (str): path to the experiment case
        config (dict): new configuration of the system for the experiment case
        system_config (dict): configuration of the system for the experiment case
        substation_config (dict): configuration of the substations in the experiment case
        weather_config (dict): configuration of the climates being used
    """
    out_folder = './' + case_path
    players = system_config["players"]
    tso = 1 + len(players)
    if master_file == '':
        tso = 0
    #out_path = system_config['out_path']
    #if out_path == "":
    out_path = "."
    try:
        archive_folder = config['archivePath']
    except TypeError:
        archive_folder = system_config['archivePath']

    try:
        config_file = config['data_path'] + '/' + config['schedule_server_file_' + str(config['nodes'])]
    except TypeError:
        config_file = system_config['dataPath'] + '/' + system_config['dsoScheduleServerFile']
    # count how many schedule servers we need
    ports = []
    for sub_key, sub_val in substation_config.items():
        if "DSO" not in sub_key:
            continue
        try:
            if not sub_val['used']:
                continue
        except Exception:
            pass
        bus = sub_val['bus_number']
        dm = divmod(bus, 20)
        if dm[0] not in ports:
            ports.append(dm[0])

    dbg_options = ['', 'gdb -x ../../gdbinit --args ', 'valgrind --track-origins=yes ']
    try:
        dbg = dbg_options[config['gld_debug']]
    except TypeError:
        dbg = dbg_options[system_config['gldDebug']]

    with open(out_folder + '/run.sh', 'w') as outfile:
        outfile.write('#!/bin/bash\n\n')
        if platform.system() == 'Darwin':
            # this is needed if you are not comfortable disabling System Integrity Protection
            dyld_path = environ.get('DYLD_LIBRARY_PATH')
            if dyld_path is not None:
                outfile.write(f'export DYLD_LIBRARY_PATH={dyld_path}\n\n')

        outfile.write('mkdir -p PyomoTempFiles\n\n')
        outfile.write('# To run agents set with_market=1 else set with_market=0\n')
        try:
            if config["market"]:
                outfile.write('with_market=1\n\n')
            else:
                outfile.write('with_market=0\n\n')
        except TypeError:
            if system_config["market"]:
                outfile.write('with_market=1\n\n')
            else:
                outfile.write('with_market=0\n\n')

        outfile.writelines(f'(exec python3 -c "import tesp_support.api.schedule_server as tesp;'
                           f'tesp.schedule_server(\'../{config_file}\', {5150 + ports[cnt]!s})" &> '
                           f'{out_path}/schedule.log &)\n' for cnt in range(len(ports)))
        outfile.write('# wait schedule server to populate\n')
        outfile.write('sleep 60\n')

        outfile.write(f'(helics_broker -f {len(weather_config) * 3 + tso!s} --loglevel=warning --name=mainbroker &> '
                      f'{out_path}/broker.log &)\n')

        for w_key in weather_config:
            outfile.write(f'cd {w_key}\n')
            outfile.write(f'(export WEATHER_CONFIG=weather_Config.json '
                          f'&& exec python3 -c "import tesp_support.weather.weather_agent as tesp;'
                          f'tesp.startWeatherAgent(\'weather.dat\')" &> {out_path}/{w_key}_weather.log &)\n')
            outfile.write('cd ..\n')

        for sub_key, sub_val in substation_config.items():
            if "DSO" not in sub_key:
                continue
            try:
                if not sub_val['used']:
                    continue
            except Exception:
                pass
            outfile.write(f'cd {sub_val["substation"]}\n')
            outfile.write(f'({dbg}gridlabd -D USE_HELICS -D METRICS_FILE="{out_path}/{sub_val["substation"]}_metrics_" '
                          f'{sub_val["substation"]}.glm &> '
                          f'{out_path}/{sub_val["substation"]}_gridlabd.log &)\n')
            outfile.write('cd ..\n')
            outfile.write(f'cd {sub_key}\n')
            outfile.write(f'(exec python3 -c "import tesp_support.dsot.substation as tesp;'
                          f'tesp.dso_loop(\'{sub_val["substation"]}\',$with_market)" &> '
                          f'{out_path}/{sub_key}_substation.log &)\n')
            outfile.write('cd ..\n')

        if master_file != '':
            outfile.write(f'(exec python3 -c "import tesp_support.api.tso_psst as tesp;'
                          f'tesp.tso_psst_loop(\'./{master_file}\')" &> {out_path}/tso.log &)\n')
            for plyr in range(len(players)):
                player = system_config[players[plyr]]
                if player[6] or player[7]:
                    outfile.write(f'(exec python3 -c "import tesp_support.api.player as tesp;'
                                  f'tesp.load_player_loop(\'./{master_file}\', \'{players[plyr]}\')" &> {out_path}/{player[0]}_player.log &)\n')

        outfile.write('tso_monitor.sh &\n')

    try:
        write_management_script(archive_folder, case_path, out_path, config['gld_debug'], 1)
    except TypeError:
        write_management_script(archive_folder, case_path, out_path, system_config['gldDebug'], 1)

    if config is not None and config.get('monitor'):
        with open(out_folder + '/tesp_monitor.sh', 'w') as outfile:
            outfile.write('python3 $TESPDIR/src/tesp_support/tesp_support/dsot/tesp_monitor.py')


def write_dsot_management_script_f(master_file, case_path, config=None, system_config=None, substation_config=None,
                                   weather_config=None):
    """ Write experiment management scripts from JSON configuration data,
    windows and linux, fncs only

    Reads the simulation configuration file or dictionary and writes

    - run.{sh, bat}, simple run script to launch experiment
    - kill.{sh, bat}, simple run script to kill experiment
    - clean.{sh, bat}, simple run script to clean generated output files from the experiment

    Args:
        master_file (str): name of the master file to the experiment case
        case_path (str): path to the experiment case
        config (dict): new configuration of the system for the experiment case
        system_config (dict): configuration of the system for the experiment case
        substation_config (dict): configuration of the substations in the experiment case
        weather_config (dict): configuration of the climates being used
    """
    out_folder = './' + case_path
    players = system_config["players"]
    tso = 1 + len(players)
    if master_file == '':
        tso = 0
    #out_path = system_config['out_path']
    #if out_path == "":
    out_path = "."

    try:
        archive_folder = config['archivePath']
    except TypeError:
        archive_folder = system_config['archivePath']

    try:
        config_file = config['data_path'] + '/' + config['schedule_server_file_' + str(config['nodes'])]
    except TypeError:
        config_file = system_config['dataPath'] + '/' + system_config['dsoScheduleServerFile']
    # count how many schedule servers we need
    ports = []
    for sub_key, sub_val in substation_config.items():
        if "DSO" not in sub_key:
            continue
        try:
            if not sub_val['used']:
                continue
        except Exception:
            pass
        bus = sub_val['bus_number']
        dm = divmod(bus, 20)
        if dm[0] not in ports:
            ports.append(dm[0])

    dbg_options = ['', 'gdb -x ../../gdbinit --args ', 'valgrind --track-origins=yes ']
    try:
        dbg = dbg_options[config['gld_debug']]
    except TypeError:
        dbg = dbg_options[system_config['gldDebug']]

    if platform.system() == 'Windows':
        print("Windows")
        with open(out_folder + '/run.bat', 'w') as outfile:
            outfile.write('set FNCS_FATAL=yes\n')
            outfile.write('set FNCS_LOG_STDOUT=yes\n')
            outfile.write('set FNCS_LOG_LEVEL=INFO\n')
            outfile.write('set FNCS_TRACE=yes\n')
            outfile.write('set WEATHER_CONFIG=weather_Config.json\n')
            # outfile.write('set FNCS_BROKER="tcp://*:' + str(system_config['port']) + '"\n')

            outfile.write('rem To run agents set with_market=1 else set with_market=0 \n')
            try:
                if config["market"]:
                    outfile.write('with_market=1\n\n')
                else:
                    outfile.write('with_market=0\n\n')
            except TypeError:
                if system_config["market"]:
                    outfile.write('with_market=1\n\n')
                else:
                    outfile.write('with_market=0\n\n')

            outfile.writelines(f'start /b cmd /c python -c "import tesp_support.api.schedule_server as tesp;'
                               f'tesp.schedule_server(\'..\\{config_file}\', {5150 + ports[cnt]!s})" ^> '
                               f'{out_path}\\schedule.log 2^>^&1\n' for cnt in range(len(ports)))
            outfile.write('rem wait schedule server to populate\n')
            outfile.write('sleep 60\n')

            outfile.write(f'start /b cmd /c fncs_broker {len(weather_config) * 3 + tso!s} ^>{out_path}\\broker.log 2^>^&1\n')

            for w_key in weather_config:
                outfile.write(f'set FNCS_CONFIG_FILE={w_key}.zpl\n')
                outfile.write(f'cd {w_key}\n')
                outfile.write(f'start /b cmd /c python -c "import tesp_support.weather.weather_agent_f as tesp;'
                              f'tesp.startWeatherAgent(\'weather.dat\')" ^> {out_path}\\{w_key}_weather.log 2^>^&1\n')
                outfile.write('cd ..\n')

            for sub_key, sub_val in substation_config.items():
                if "DSO" not in sub_key:
                    continue
                try:
                    if not sub_val['used']:
                        continue
                except Exception:
                    pass
                outfile.write(f'cd {sub_val["substation"]}\n')
                outfile.write(f'start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE="{sub_val["substation"]}_metrics_" '
                              f'{sub_val["substation"]}.glm ^> '
                              f'{out_path}\\{sub_val["substation"]}_gridlabd.log 2^>^&1\n')
                outfile.write(f'set FNCS_CONFIG_FILE={sub_val["substation"]}.yaml\n')
                outfile.write('cd ..\n')
                outfile.write(f'cd {sub_key}\n')
                outfile.write(f'start /b cmd /c python -c "import tesp_support.dsot.substation_f as tesp;'
                              f'tesp.dso_loop_f(\'{sub_val["substation"]}_agent_dict.json\',\'{sub_val["substation"]}\',%with_market%)" ^> '
                              f'{out_path}\\{sub_key}_substation.log 2^>^&1\n')
                outfile.write('cd ..\n')
            if master_file != '':
                outfile.write('set FNCS_CONFIG_FILE=tso.yaml\n')
                outfile.write(f'start /b cmd /c python -c "import tesp_support.original.tso_psst_f as tesp;'
                              f'tesp.tso_psst_loop_f(\'./{master_file}\')" ^> {out_path}\\tso.log 2^>^&1\n')
                outfile.write('start /b powershell -NoProfile -ExecutionPolicy Bypass -File watch_tso_log.ps1\n')

                for plyr in range(len(players)):
                    player = system_config[players[plyr]]
                    if player[6] or player[7]:
                        outfile.write(f'set FNCS_CONFIG_FILE={player[0]}_player.yaml\n')
                        outfile.write(f'start /b cmd /c python -c "import tesp_support.original.player_f as tesp;'
                                      f'tesp.load_player_loop_f(\'./{master_file}\', \'{players[plyr]}\')" ^> {out_path}\\{player[0]}_player.log 2^>^&1\n')

        with open(out_folder + '/kill.bat', 'w') as outfile:
            outfile.write('taskkill /F /IM fncs_broker.exe\n')
            outfile.write('taskkill /F /IM python.exe\n')
            outfile.write('taskkill /F /IM gridlabd.exe\n')

        with open(out_folder + '/watch_tso_log.ps1', 'w') as outfile:
            outfile.write('$log = ".\\tso.log"\n')
            outfile.write('$deadline = (Get-Date).AddSeconds(30)\n')
            outfile.write('while (-not (Test-Path $log)) {\n')
            outfile.write('    if ((Get-Date) -gt $deadline) { exit 0 }\n')
            outfile.write('    Start-Sleep -Seconds 300\n')
            outfile.write('}\n')
            outfile.write('$fs = [IO.File]::Open($log, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)\n')
            outfile.write('$fs.Seek(0, [IO.SeekOrigin]::End) | Out-Null\n')
            outfile.write('$sr = [IO.StreamReader]::new($fs)\n')
            outfile.write('while ($true) {\n')
            outfile.write('    $line = $sr.ReadLine()\n')
            outfile.write('    if ($null -ne $line) {\n')
            outfile.write('        if ($line -match "CRITICAL") {\n')
            outfile.write('            Write-Host "[log-watcher] CRITICAL error: $line" -ForegroundColor Red\n')
            outfile.write('            & .\\kill.bat\n')
            outfile.write('            $sr.Close(); $fs.Close()\n')
            outfile.write('            exit 1\n')
            outfile.write('        }\n')
            outfile.write('    } else {\n')
            outfile.write('        Start-Sleep -Milliseconds 250\n')
            outfile.write('    }\n')
            outfile.write('}\n')

        with open(out_folder + '/clean.bat', 'w') as outfile:
            outfile.write('del ' + out_path + '\\*.log /s\n')
            outfile.write('del ' + out_path + '\\*.csv /s\n')
            outfile.write('del ' + out_path + '\\*.out /s\n')
            outfile.write('del ' + out_path + '\\*rtm.dat /s\n')
            outfile.write('del ' + out_path + '\\*dam.dat /s\n')
            outfile.write('del ' + out_path + '\\*uc.dat /s\n')
            outfile.write('del ' + out_path + '\\*ames.dat /s\n')
            outfile.write('del ' + out_path + '\\*metrics*.json* /s\n')
            outfile.write('del ' + out_path + '\\*metrics*.h5 /s\n')
            outfile.write('del ' + out_path + '\\*model_dict.json /s\n')
            outfile.write('del broker_trace.txt\n')
    else:  # Unix
        with open(out_folder + '/run.sh', 'w') as outfile:
            outfile.write('#!/bin/bash\n\n')
            outfile.write('export FNCS_LOG_LEVEL=INFO\n')
            if platform.system() == 'Darwin':
                # this is needed if you are not comfortable disabling System Integrity Protection
                dyld_path = environ.get('DYLD_LIBRARY_PATH')
                if dyld_path is not None:
                    outfile.write(f'export DYLD_LIBRARY_PATH={dyld_path}\n\n')

            outfile.write('mkdir -p PyomoTempFiles\n\n')
            outfile.write('# To run agents set with_market=1 else set with_market=0 \n')
            try:
                if config["market"]:
                    outfile.write('with_market=1\n\n')
                else:
                    outfile.write('with_market=0\n\n')
            except TypeError:
                if system_config["market"]:
                    outfile.write('with_market=1\n\n')
                else:
                    outfile.write('with_market=0\n\n')

            outfile.writelines(f'(exec python3 -c "import tesp_support.api.schedule_server as tesp;'
                               f'tesp.schedule_server(\'../{config_file}\', {5150 + ports[cnt]!s})" &> '
                               f'{out_path}/schedule.log &)\n' for cnt in range(len(ports)))
            outfile.write('# wait schedule server to populate\n')
            outfile.write('sleep 60\n')

            try:
                outfile.write('(export FNCS_BROKER="tcp://*:' + str(system_config['port'])
                            + f'" && fncs_broker {len(weather_config) * 3 + tso!s} &> {out_path}/broker.log &)\n')
            except KeyError:
                outfile.write('(export FNCS_BROKER="tcp://*:' + str(config['port'])
                            + f'" && fncs_broker {len(weather_config) * 3 + tso!s} &> {out_path}/broker.log &)\n')

            for w_key in weather_config:
                outfile.write(f'cd {w_key}\n')
                outfile.write(f'(export FNCS_CONFIG_FILE={w_key}.zpl && export WEATHER_CONFIG=weather_Config.json '
                              f'&& exec python3 -c "import tesp_support.weather.weather_agent_f as tesp;'
                              f'tesp.startWeatherAgent(\'weather.dat\')" &> {out_path}/{w_key}_weather.log &)\n')
                outfile.write('cd ..\n')

            for sub_key, sub_val in substation_config.items():
                if "DSO" not in sub_key:
                    continue
                try:
                    if not sub_val['used']:
                        continue
                except Exception:
                    pass
                outfile.write(f'cd {sub_val["substation"]}\n')
                outfile.write(f'({dbg}gridlabd -D USE_FNCS -D METRICS_FILE="{out_path}/{sub_val["substation"]}_metrics_"'
                              f'{sub_val["substation"]}.glm &> {out_path}/{sub_val["substation"]}_gridlabd.log &)\n')
                outfile.write('cd ..\n')
                outfile.write(f'cd {sub_key}\n')
                outfile.write(f'(export FNCS_CONFIG_FILE={sub_val["substation"]}.yaml '
                              f'&& exec python3 -c "import tesp_support.dsot.substation_f as tesp;'
                              f'tesp.dso_loop_f(\'{sub_val["substation"]}_agent_dict.json\',\'{sub_val["substation"]}\',$with_market)" &> '
                              f'{out_path}/{sub_key}_substation.log &)\n')
                outfile.write('cd ..\n')

            if master_file != '':
                outfile.write(f'(export FNCS_CONFIG_FILE=tso.yaml '
                              f'&& exec python3 -c "import tesp_support.original.tso_psst_f as tesp;'
                              f'tesp.tso_psst_loop_f(\'./{master_file}\')" &> {out_path}/tso.log &)\n')
                for plyr in range(len(players)):
                    player = system_config[players[plyr]]
                    if player[6] or player[7]:
                        outfile.write(f'(export FNCS_CONFIG_FILE={player[0]}_player.yaml '
                                      f'&& exec python3 -c "import tesp_support.original.player_f as tesp;'
                                      f'tesp.load_player_loop_f(\'./{master_file}\', \'{players[plyr]}\')" &> {out_path}/{player[0]}_player.log &)\n')

                outfile.write('tso_monitor.sh &\n')

        try:
            write_management_script(archive_folder, case_path, out_path, config['gld_debug'], 1)
        except TypeError:
            write_management_script(archive_folder, case_path, out_path, system_config['gldDebug'], 1)

        if config is not None and config.get['monitor']:
            with open(out_folder + '/tesp_monitor.sh', 'w') as outfile:
                outfile.write('python3 $TESPDIR/src/tesp_support/tesp_support/dsot/tesp_monitor.py')


def write_management_script(archive_folder, case_path, out_path, gld_debug, run_post):
    out_folder = './' + case_path

    with open(out_folder + '/monitor.sh', 'w') as outfile:
        outfile.write('#!/bin/bash\n')
        outfile.write("""
# capture docker id so we can stop easily using stopSims.sh
cat /etc/hostname > docker_id            
# first add header, simultaneously creating/overwriting the file
top -w 512 cbn 1 | grep "PID" | egrep -v "top|grep" > stats.log 
# then, in background, run top in batch mode (this will not stop as is, unless in docker)
top -w 512 cbd 60 | egrep -v "top|Tasks|Cpu|Mem|Swap|PID|^$" >> stats.log & 

# manually run every so often a check to see if we can quit this script (i.e. once sim is over, mostly for docker)
while sleep 120; do
  echo "still running at $(TZ='America/Los_Angeles' date)"
  ps aux | grep python | grep -q -v grep | grep -q -v schedule
  PROCESS_1_STATUS=$?
  ps aux | grep gridlabd | grep -q -v grep
  PROCESS_2_STATUS=$?
  ps aux | grep helics_broker | grep -q -v grep
  PROCESS_3_STATUS=$?
  ps aux | grep fncs_broker | grep -q -v grep
  PROCESS_4_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If all are not 0, then we are done with the main background processes, so the container can end
  if [ $PROCESS_1_STATUS -ne 0 ] && [ $PROCESS_2_STATUS -ne 0 ] && [ $PROCESS_3_STATUS -ne 0 ]; then
    echo "All processes (python, gridlabd, fncs_broker) have exited, so we are done."
    # TODO: kill top manually?
    # TODO: then, massage stats.log into slightly easier-to-read TSV with: sed -i 's/./&"/68;s/$/"/;$d' stats.log
    #  which wraps the commands in quotes and removes the last line which could be cut off

    ./postprocess.sh

    exit 1
  fi
done                    
""")

    with open(out_folder + '/docker-run.sh', 'w') as outfile:
        gdb_extra = "" if gld_debug == 0 else \
            """
        --cap-add=SYS_PTRACE \\
        --security-opt seccomp=unconfined \\"""
        outfile.write(f"""
IMAGE="cosim-cplex:tesp_22.04.1"

git describe --tags > tesp_version
docker images -q ${{IMAGE}} > docker_version
hostname > hostname

CASE="{path.basename(out_folder)}"
CASEDIR="{path}"
SRCWORK_DIR="$CASEDIR/$CASE"
WORKING_DIR="$SIM_HOME/tesp/examples/analysis/$CASEDIR/code/$CASE"
ARCHIVE_DIR="{archive_folder}"

chown -fR ${{UID}}:${{SIM_GID}} "$TESPDIR"
chmod -fR 774 "$TESPDIR"

docker run \\
       -e LOCAL_UID=$UID \\
       -itd \\
       --rm \\
       --network=none \\{gdb_extra}
       --mount type=bind,source="$TESPDIR",destination="$SIM_HOME/tesp" \\
       -w=${{WORKING_DIR}} \\
       ${{IMAGE}} \\
       /bin/bash -c "./run.sh; ./monitor.sh"

        """)

    with open(out_folder + '/postprocess.sh', 'w') as outfile:
        if run_post == 1:
            outfile.write('python3 ../run_case_postprocessing.py > postprocessing.log\n')
        outfile.write(f'mkdir -p {archive_folder}/$(cat tesp_version)\n')
        outfile.write(f'rm -rf {archive_folder}/$(cat tesp_version)/{case_path}\n')
        outfile.write(f'mv -f ../{case_path} {archive_folder}/$(cat tesp_version)\n')

    with open(out_folder + '/tso_monitor.sh', 'w') as outfile:
        outfile.write('#!/bin/bash\n')
        outfile.write("""
# Watch tso.log for CRITICAL errors; kill the simulation if one is found

while sleep 300; do
    if cat tso.log | grep -q "CRITICAL" ; then
        ./kill.sh
        break
    fi
done

""")

    with open(out_folder + '/kill.sh', 'w') as outfile:
        outfile.write('pkill -9 fncs_broker\n')
        outfile.write('pkill -9 helics_broker\n')
        outfile.write('pkill -9 python\n')
        outfile.write('pkill -9 gridlabd\n')

    with open(out_folder + '/clean.sh', 'w') as outfile:
        outfile.write('cd ' + out_path + '\n')
        outfile.write('rm -rf PyomoTempFiles/*\n')
        outfile.write('find . -name \\*.log -type f -delete\n')
        outfile.write('find . -name \\*.csv -type f -delete\n')
        outfile.write('find . -name \\*.out -type f -delete\n')
        outfile.write('find . -name \\*rtm.dat -type f -delete\n')
        outfile.write('find . -name \\*dam.dat -type f -delete\n')
        outfile.write('find . -name \\*uc.dat -type f -delete\n')
        outfile.write('find . -name \\*ames.dat -type f -delete\n')
        outfile.write('find . -name \\*metrics*.json* -type f -delete\n')
        outfile.write('find . -name \\*metrics*.h5 -type f -delete\n')
        outfile.write('find . -name \\*model_dict.json -type f -delete\n')
        outfile.write('find . -name \\*diag.txt -type f -delete\n')
        outfile.write('find . -name \\*log.txt -type f -delete\n')
        outfile.write('cd -\n')

    subprocess.run(['chmod', '+x', out_folder + '/run.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/monitor.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/docker-run.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/postprocess.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/tso_monitor.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/kill.sh'], check=False)
    subprocess.run(['chmod', '+x', out_folder + '/clean.sh'], check=False)
    try:
        subprocess.run(['chmod', '+x', out_folder + '/tesp_monitor.sh'], check=False)
    except FileNotFoundError:
        pass


def write_players_msg(case_path, sys_config, dt):
    # write player helics message file for load and generator players

    dso_cnt = len(sys_config['DSO'])
    players = sys_config["players"]
    for idx in range(len(players)):
        player = sys_config[players[idx]]
        pf = HelicsMsg(player[0] + "player", dt)
        if player[8]:
            # load
            for i in range(dso_cnt):
                bs = str(i + 1)
                pf.pubs_n(False, player[0] + "_load_" + bs, "string")
                pf.pubs_n(False, player[0] + "_ld_hist_" + bs, "string")
        else:
            # power
            genfuel = sys_config["genfuel"]
            for i in range(len(genfuel)):
                if genfuel[i][0] in sys_config["renewables"]:
                    idx = str(genfuel[i][2])
                    if player[6]:
                        pf.pubs_n(False, player[0] + "_power_" + idx, "string")
                    if player[7]:
                        pf.pubs_n(False, player[0] + "_pwr_hist_" + idx, "string")
        pf.write_file(case_path + "/" + player[0] + "_player.json")


class MarketClearingType(IntEnum):
    """ Describes the market clearing type
    """
    UNCONGESTED = 0
    CONGESTED = 1
    FAILURE = 2


class HvacMode(IntEnum):
    """ Describes the operating mode of the HVAC
    """
    COOLING = 0
    HEATING = 1


class Curve:
    """ Accumulates a set of price, quantity bidding curves for later aggregation

    Args:
        pricecap (float): the maximum price that is allowed in the market, in $/kWh
        num_samples (int): the number of sampling points, describes how precisely the curve is sampled

    Attributes:
        prices ([float]): array of prices, in $/kWh
        quantities ([float]): array of quantities, in kW
        uncontrollable_only (bool): equals to 1 when there is only uncontrollable load demand bids in the market

    """

    def __init__(self, pricecap, num_samples):
        """ Initializes the class

        Args:
            pricecap (float): the maximum price that is allowed in the market, in $/kWh
            num_samples (int): the number of sampling points, describes how precisely the curve is sampled

        """
        self.num_samples = num_samples
        if isinstance(pricecap, list):
            self.price_cap = pricecap[0]
            self.L_price_cap = pricecap[1]
            self.prices = np.linspace(self.price_cap, self.L_price_cap, self.num_samples)
        else:
            self.price_cap = pricecap
            self.L_price_cap = 0.0
            self.prices = np.linspace(self.price_cap, self.L_price_cap, self.num_samples)
        self.quantities = np.zeros(self.num_samples)
        self.uncontrollable_only = True

    def curve_aggregator(self, identity, bid_curve):
        """
    Adding one more bid curve to the aggregated seller or buyer curve

        Args:
            identity (str): identifies whether the bid is collected from a "Buyer" or "Seller"
            bid_curve ([list]): a nested list with dimension (m, 2), with m equals 2 to 4

        """
        bid_curve = np.array(bid_curve)
        if np.size(bid_curve) == 0:  # do not add bid if empty
            return
        else:
            bid_curve = curve_bid_sorting(identity, bid_curve)

        if bid_curve[-1][1] < 0:  # if the last element is negative
            if bid_curve[0][1] < 0:  # do not add bid if all prices are negative
                return
            else:
                # replace negative points in bid
                bid_curve_orig = deepcopy(bid_curve)
                bid_curve = []
                for idx in range(len(bid_curve_orig)):
                    if bid_curve_orig[idx][1] < 0:
                        bid_curve.append([(bid_curve_orig[idx - 1][1] * bid_curve_orig[idx][0] -
                                           bid_curve_orig[idx - 1][0] * bid_curve_orig[idx][1]) /
                                          (bid_curve_orig[idx - 1][1] - bid_curve_orig[idx][1]), 0])
                        bid_curve = np.array(bid_curve)
                        break
                    else:
                        bid_curve.append(bid_curve_orig[idx])

        if bid_curve[0][1] > self.price_cap:  # if the first element is more than price cap
            # print('U inside cut-off price cap...')
            # print(bid_curve)
            if bid_curve[-1][1] > self.price_cap:  # do not add bid if all prices are above price cap
                return
            else:
                # cut-off prices above price cap points in bid
                bid_curve_orig = deepcopy(bid_curve)
                bid_curve = []
                for idx in range(-1, -len(bid_curve_orig) - 1, -1):
                    if bid_curve_orig[idx][1] > self.price_cap:
                        bid_curve.insert(0, [(bid_curve_orig[idx + 1][0] * bid_curve_orig[idx][1] -
                                              bid_curve_orig[idx][0] * bid_curve_orig[idx + 1][1] +
                                              self.price_cap * (bid_curve_orig[idx][0] - bid_curve_orig[idx + 1][0])) /
                                             (bid_curve_orig[idx][1] - bid_curve_orig[idx + 1][1]), self.price_cap])
                        bid_curve = np.array(bid_curve)
                        break
                    else:
                        bid_curve.insert(0, bid_curve_orig[idx])
            # print(bid_curve)
            bid_curve = deepcopy(bid_curve)
        if bid_curve[-1][1] < self.L_price_cap:  # if the last element is less than L price cap
            # print('L inside cut-off price cap...')
            # print(bid_curve)
            if bid_curve[0][1] < self.L_price_cap:  # do not add bid if all prices are below L price cap
                return
            else:
                # cut-off prices below L price cap points in bid
                bid_curve_orig = deepcopy(bid_curve)
                bid_curve = []
                for idx in range(len(bid_curve_orig)):
                    if bid_curve_orig[idx][1] < self.L_price_cap:
                        bid_curve.append([(bid_curve_orig[idx - 1][0] * bid_curve_orig[idx][1] -
                                           bid_curve_orig[idx][0] * bid_curve_orig[idx - 1][1] +
                                           self.L_price_cap * (bid_curve_orig[idx][0] - bid_curve_orig[idx - 1][0])) /
                                          (bid_curve_orig[idx][1] - bid_curve_orig[idx - 1][1]), self.L_price_cap])
                        bid_curve = np.array(bid_curve)
                        break
                    else:
                        bid_curve.append(bid_curve_orig[idx])
            # print(bid_curve)
        # Adding two points representing the two extreme price cases
        if bid_curve[0][1] < self.price_cap:
            bid_curve = np.insert(bid_curve, [0], [[bid_curve[0][0], self.price_cap]], axis=0)
        if bid_curve[-1][1] > self.L_price_cap:
            bid_curve = np.append(bid_curve, [[bid_curve[-1][0], self.L_price_cap]], axis=0)

        # Divide the curve into len(bid_curve)-1 segments for generating the sampling
        for idx in range(len(bid_curve) - 1):
            if bid_curve[idx, 1] == bid_curve[idx + 1, 1]:
                pass
            else:
                segment_start = int((self.price_cap - bid_curve[idx][1]) * (
                        self.num_samples / (self.price_cap - self.L_price_cap)))
                segment_end = int((self.price_cap - bid_curve[idx + 1][1]) * (
                        self.num_samples / (self.price_cap - self.L_price_cap)))
                len_segment = segment_end - segment_start
                # print('bid curve ...')
                # print(bid_curve)
                # print(self.price_cap)
                self.quantities[segment_start:segment_end] = np.add(self.quantities[segment_start:segment_end],
                                                                    np.linspace(bid_curve[idx][0],
                                                                                bid_curve[idx + 1][0], len_segment))
        if len(set(self.quantities)) > 1:
            self.uncontrollable_only = False

    def curve_aggregator_DSO(self, substation_demand_curve):
        """
    Adding one substation bid curve to the aggregated DSO bid curve,
        applied when then curve instance is a DSO demand curve

        Args:
            substation_demand_curve(Curve): a curve object representing the aggregated substation demand curve

        """
        self.prices = substation_demand_curve.prices
        self.quantities = np.add(self.quantities, substation_demand_curve.quantities)
        if len(set(self.quantities)) > 1:
            self.uncontrollable_only = False

    def update_price_caps(self):
        """ Update price caps based on the price points

        """
        self.price_cap = max(self.prices)
        self.L_price_cap = min(self.prices)


def curve_bid_sorting(identity, bid_curve):
    """ Sorting the 4-point curve bid primarily on prices and secondarily on quantities

    For "Buyer", the bid prices are ordered descendingly and bid quantities are ordered ascendingly;
    For "Seller", both the bid prices and the bid quantities are ordered descendingly;

    Args:
        identity (str): identifies whether the bid is collected from a "Buyer" or "Seller"
        bid_curve ([list]): unsorted curve bid

    Outputs:
        sorted_bid_curve ([list]): sorted curve bid

    """
    idx_start = 0
    value = bid_curve[0, 1]
    sorted_bid_curve = np.empty((0, 2))
    bid_curve = bid_curve[bid_curve[:, 1].argsort()[::-1]]
    for i in range(len(bid_curve)):
        if i == 0:
            pass
        elif i == len(bid_curve) - 1:
            idx_end = len(bid_curve)
            segment = bid_curve[idx_start: idx_end]
            if identity == 'Buyer':
                sorted_bid_curve = np.append(sorted_bid_curve, segment[segment[:, 0].argsort()], axis=0)
            else:
                sorted_bid_curve = np.append(sorted_bid_curve, segment[segment[:, 0].argsort()[::-1]], axis=0)
        else:
            if bid_curve[i, 1] == value:
                pass
            else:
                idx_end = i
                segment = bid_curve[idx_start: idx_end]
                if identity == 'Buyer':
                    sorted_bid_curve = np.append(sorted_bid_curve, segment[segment[:, 0].argsort()], axis=0)
                else:
                    sorted_bid_curve = np.append(sorted_bid_curve, segment[segment[:, 0].argsort()[::-1]], axis=0)
                value = bid_curve[i, 0]
                idx_start = i

    return sorted_bid_curve


def get_intersect(a1, a2, b1, b2):
    s = np.vstack([a1, a2, b1, b2])  # s for stacked
    h = np.hstack((s, np.ones((4, 1))))  # h for homogeneous
    l1 = np.cross(h[0], h[1])  # get first line
    l2 = np.cross(h[2], h[3])  # get second line
    x, y, z = np.cross(l1, l2)  # point of intersection
    if z == 0:  # lines are parallel
        return float('inf'), float('inf')
    return y / z, x / z


def resample_curve(x_vec, y_vec, min_q, max_q, num_samples):
    new_q = np.linspace(min_q, max_q, num_samples)
    new_p = []
    for val in new_q:
        new_p.append(np.interp(val, x_vec, y_vec))
    return new_q, new_p


def resample_curve_for_price_only(x_vec_1, x_vec_2, y_vec_2):
    new_p_2 = []
    for val in x_vec_1:
        new_p_2.append(np.interp(val, x_vec_2, y_vec_2))
    return new_p_2


def resample_curve_for_market(x_vec_1, y_vec_1, x_vec_2, y_vec_2):  # , min_q, max_q, num_samples):
    flat_list = [item for elem in [x_vec_1, x_vec_2] for item in elem]
    x = np.array(flat_list)
    x = np.sort(x)
    x = np.unique(x)
    new_p_1 = []
    new_p_2 = []
    for val in x:
        new_p_1.append(np.interp(val, x_vec_1, y_vec_1))
        new_p_2.append(np.interp(val, x_vec_2, y_vec_2))
    return x, new_p_1, new_p_2


def test():
    y_vec_1 = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
    x_vec_1 = [0.0, 1.5, 2.5, 5.5, 10, 11]
    x_vec_2 = [8.0, 9.0, 10.0, 12]
    y_vec_2 = [8.0, 9.0, 10.0, 12]  # ?
    flat_list = [item for elem in [x_vec_1, x_vec_2] for item in elem]
    x = np.array(flat_list)
    x = np.sort(x)
    x = np.unique(x)
    new_p_1 = []
    new_p_2 = []
    for val in x:
        new_p_1.append(np.interp(val, x_vec_1, y_vec_1))
        new_p_2.append(np.interp(val, x_vec_2, y_vec_2))


if __name__ == "__main__":
    test()
