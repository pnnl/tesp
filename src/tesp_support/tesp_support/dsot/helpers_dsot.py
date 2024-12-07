# Copyright (C) 2021-2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: helpers_dsot.py
""" Utility functions for use within tesp_support, including new agents.
This is DSO+T specific helper functions
"""

import platform
import subprocess
from os import getcwd, path, environ
from copy import deepcopy
from enum import IntEnum

import numpy as np

from tesp_support.api.helpers import HelicsMsg


def write_mircogrids_management_script(master_file, case_path, system_config=None, substation_config=None,
                                       weather_config=None):
    """ Write experiment management scripts from JSON configuration data,
    linux ans helics only

    Reads the simulation configuration file or dictionary and writes

    - run.{sh, bat}, simple run script to launch experiment
    - kill.{sh, bat}, simple run script to kill experiment
    - clean.{sh, bat}, simple run script to clean generated output files from the experiment

    Args:
        master_file (str): name of the master file to the experiment case
        case_path (str): path to the experiment case
        system_config (dict): configuration of the system for the experiment case
        substation_config (dict): configuration of the substations in the experiment case
        weather_config (dict): configuration of the climates being used
    """

    out_folder = './' + case_path
    outPath = system_config['outputPath']
    if outPath == "":
        outPath = "."
    dsoNum = len(substation_config.keys())  # the market agents/federates
    substNum = dsoNum  # the GridLAB-D federates
    weatherAgNum = len(weather_config.keys())  # the weather agents/federates
    dbgOptions = ['', 'gdb -x ../../gdbinit --args ', 'valgrind --track-origins=yes ']
    dbg = dbgOptions[system_config['gldDebug']]

    with open(out_folder + '/run.sh', 'w') as outfile:
        outfile.write('# !/bin/bash\n\n')

        outfile.write('with_market=1\n')
        outfile.write('if [ "$1" = "base" ]\n')
        outfile.write('then\n')
        outfile.write('  with_market=0\n')
        outfile.write('fi\n\n')

        # ## Monish Edits: Adding a PythonPath to point towards TESP_support directories
        tesp_path = getcwd() + ''
        outfile.write('export PYTHONPATH=%s:$PYTHONPATH;\n' % tesp_path)

        outfile.write(
            '(helics_broker -t="zmq" --federates=%s --name=mainbroker --loglevel=warning &> %s/broker.log &)\n'
            % (str(len(substation_config) * 2 + sum(
                [len(substation_config[dso]['microgrids']) for dso in substation_config]) + sum(
                [len(substation_config[dso]['generators']) for dso in substation_config]) + len(
                weather_config)), outPath))

        for w_key, w_val in weather_config.items():
            outfile.write('cd %s\n' % w_key)
            outfile.write('(export WEATHER_CONFIG=weather_Config.json '
                          '&& exec python3 -c "import tesp_support.consensus.weather_agent as tesp;'
                          'tesp.startWeatherAgent(\'weather.dat\')" &> %s/%s_weather.log &)\n'
                          % (outPath, w_key))
            outfile.write('cd ..\n')

        for sub_key, sub_val in substation_config.items():
            outfile.write('cd %s\n' % sub_val['substation'])
            outfile.write(
                '(%sgridlabd -D USE_HELICS -D METRICS_FILE="%s/%s_metrics_" %s.glm &> %s/%s_gridlabd.log &)\n'
                % (dbg, outPath, sub_val['substation'], sub_val['substation'], outPath, sub_val['substation']))
            outfile.write('cd ..\n')

            outfile.write('cd %s\n' % sub_key)
            outfile.write('(exec python3 -c "import tesp_support.consensus.dso_agent as DSO_agent;'
                          'DSO_agent.substation_loop(\'%s_agent_dict.json\',\'%s\',$with_market)" &> '
                          '%s/%s_substation.log &)\n'
                          % (sub_val['substation'], sub_val['substation'], outPath, sub_key))
            outfile.write('cd ..\n')

            for microgrid_key in sub_val['microgrids']:
                outfile.write('cd %s\n' % microgrid_key)
                outfile.write('(exec python3 -c "import tesp_support.consensus.microgrid_agent as MG_agent;'
                              'MG_agent.substation_loop(\'%s_agent_dict.json\',\'%s\',$with_market)" &> '
                              '%s/%s_substation.log &)\n'
                              % (microgrid_key, microgrid_key, outPath, microgrid_key))
                outfile.write('cd ..\n')

            for dg_key in sub_val['generators']:
                outfile.write('cd %s\n' % dg_key)
                outfile.write('(exec python3 -c "import tesp_support.consensus.dg_agent as DG_agent;'
                              'DG_agent.substation_loop(\'%s_agent_dict.json\',\'%s\',$with_market)" &> '
                              '%s/%s_substation.log &)\n'
                              % (dg_key, dg_key, outPath, dg_key))
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
        if 'HELICS' in system_config.keys():
            outfile.write('pkill -9 helics_broker\n')
        if 'FNCS' in system_config.keys():
            outfile.write('pkill -9 fncs_broker\n')
        outfile.write('pkill -9 python\n')
        outfile.write('pkill -9 gridlab\n')

    with open(out_folder + '/clean.sh', 'w') as outfile:
        outfile.write('cd ' + outPath + '\n')
        outfile.write('find . -name \\*.log -type f -delete\n')
        outfile.write('find . -name \\*.csv -type f -delete\n')
        # outfile.write('find . -name \\*.out -type f -delete\n')
        # outfile.write('find . -name \\*metrics*.json* -type f -delete\n')
        # outfile.write('find . -name \\*metrics*.h5 -type f -delete\n')
        # outfile.write('find . -name \\*model_dict.json -type f -delete\n')
        outfile.write('find . -name \\*diagnostics.txt -type f -delete\n')
        outfile.write('find . -name \\*log.txt -type f -delete\n')
        outfile.write('cd -\n')

    subprocess.run(['chmod', '+x', out_folder + '/run.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/monitor.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/kill.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/clean.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/docker-run.sh'])


def write_dsot_management_script(master_file, case_path, system_config=None, substation_config=None,
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
        system_config (dict): configuration of the system for the experiment case
        substation_config (dict): configuration of the substations in the experiment case
        weather_config (dict): configuration of the climates being used
    """
    out_folder = './' + case_path
    players = system_config["players"]
    tso = 1 + len(players)
    if master_file == '':
        tso = 0
    outPath = system_config['outputPath']
    if outPath == "":
        outPath = "."

    archive_folder = system_config['archivePath']

    config_file = system_config['dataPath'] + '/' + system_config['dsoScheduleServerFile']
    # count how many schedule servers we need
    ports = []
    for sub_key, sub_val in substation_config.items():
        if "DSO" not in sub_key:
            continue
        try:
            if not sub_val['used']:
                continue
        except:
            pass
        bus = sub_val['bus_number']
        dm = divmod(bus, 20)
        if dm[0] not in ports:
            ports.append(dm[0])

    dbgOptions = ['', 'gdb -x ../../gdbinit --args ', 'valgrind --track-origins=yes ']
    dbg = dbgOptions[system_config['gldDebug']]

    with open(out_folder + '/run.sh', 'w') as outfile:
        outfile.write('#!/bin/bash\n\n')
        if platform.system() == 'Darwin':
            # this is needed if you are not comfortable disabling System Integrity Protection
            dyldPath = environ.get('DYLD_LIBRARY_PATH')
            if dyldPath is not None:
                outfile.write('export DYLD_LIBRARY_PATH=%s\n\n' % dyldPath)

        outfile.write('(exec date &> ./debug.log &)\n')      
        outfile.write('mkdir -p PyomoTempFiles\n\n')
        outfile.write('# To run agents set with_market=1 else set with_market=0\n')
        if system_config["market"]:
            outfile.write('with_market=1\n\n')
        else:
            outfile.write('with_market=0\n\n')

        for cnt in range(len(ports)):
            outfile.write('(exec python3 -c "import tesp_support.api.schedule_server as tesp;'
                          'tesp.schedule_server(\'../%s\', %s)" &> %s/schedule.log &)\n'
                          % (config_file, str(5150 + ports[cnt]), outPath))
        outfile.write('# wait schedule server to populate\n')
        outfile.write('sleep 60\n')

        outfile.write('(helics_broker -f %s --loglevel=warning --name=mainbroker &> %s/broker.log &)\n'
                      % (str(len(weather_config) * 3 + tso), outPath))

        for w_key, w_val in weather_config.items():
            outfile.write('cd %s\n' % w_key)
            outfile.write('(export WEATHER_CONFIG=weather_Config.json '
                          '&& exec python3 -c "import tesp_support.weather.weather_agent as tesp;'
                          'tesp.startWeatherAgent(\'weather.dat\')" &> %s/%s_weather.log &)\n'
                          % (outPath, w_key))
            outfile.write('cd ..\n')

        for sub_key, sub_val in substation_config.items():
            if "DSO" not in sub_key:
                continue
            try:
                if not sub_val['used']:
                    continue
            except:
                pass
            outfile.write('cd %s\n' % sub_val['substation'])
            outfile.write(
                '(%sgridlabd -D USE_HELICS -D METRICS_FILE="%s/%s_metrics_" %s.glm &> %s/%s_gridlabd.log &)\n'
                % (dbg, outPath, sub_val['substation'], sub_val['substation'], outPath, sub_val['substation']))
            outfile.write('cd ..\n')
            outfile.write('cd %s\n' % sub_key)
            outfile.write('(exec python3 -c "import tesp_support.dsot.substation as tesp;'
                          'tesp.dso_loop(\'%s\',$with_market)" &> '
                          '%s/%s_substation.log &)\n'
                          % (sub_val['substation'], outPath, sub_key))
            outfile.write('cd ..\n')

        if master_file != '':
            outfile.write('(exec python3 -c "import tesp_support.api.tso_psst as tesp;'
                          'tesp.tso_psst_loop(\'./%s\')" &> %s/tso.log &)\n'
                          % (master_file, outPath))
            for plyr in range(len(players)):
                player = system_config[players[plyr]]
                if player[6] or player[7]:
                    outfile.write('(exec python3 -c "import tesp_support.api.player as tesp;'
                                  'tesp.load_player_loop(\'./%s\', \'%s\')" &> %s/%s_player.log &)\n'
                                  % (master_file, players[plyr], outPath, player[0]))
        outfile.write('(exec date &> ./debug.log &)\n')

    write_management_script(archive_folder, case_path, outPath, system_config['gldDebug'], 1)


def write_dsot_management_script_f(master_file, case_path, system_config=None, substation_config=None,
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
        system_config (dict): configuration of the system for the experiment case
        substation_config (dict): configuration of the substations in the experiment case
        weather_config (dict): configuration of the climates being used
    """
    out_folder = './' + case_path
    players = system_config["players"]
    tso = 1 + len(players)
    if master_file == '':
        tso = 0
    outPath = system_config['outputPath']
    if outPath == "":
        outPath = "."

    archive_folder = system_config['archivePath']

    config_file = system_config['dataPath'] + '/' + system_config['dsoScheduleServerFile']
    # count how many schedule servers we need
    ports = []
    for sub_key, sub_val in substation_config.items():
        if "DSO" not in sub_key:
            continue
        try:
            if not sub_val['used']:
                continue
        except:
            pass
        bus = sub_val['bus_number']
        dm = divmod(bus, 20)
        if dm[0] not in ports:
            ports.append(dm[0])

    dbgOptions = ['', 'gdb -x ../../gdbinit --args ', 'valgrind --track-origins=yes ']
    dbg = dbgOptions[system_config['gldDebug']]

    if platform.system() == 'Windows':
        with open(out_folder + '/run.bat', 'w') as outfile:
            outfile.write('set FNCS_FATAL=yes\n')
            outfile.write('set FNCS_LOG_STDOUT=yes\n')
            outfile.write('set FNCS_LOG_LEVEL=INFO\n')
            outfile.write('set FNCS_TRACE=yes\n')
            outfile.write('set WEATHER_CONFIG=weather_Config.json\n')
            # outfile.write('set FNCS_BROKER="tcp://*:' + str(system_config['port']) + '"\n')

            outfile.write('rem To run agents set with_market=1 else set with_market=0 \n')
            if system_config["market"]:
                outfile.write('set with_market=1\n')
            else:
                outfile.write('set with_market=0\n')

            for cnt in range(len(ports)):
                outfile.write('start /b cmd /c python -c "import tesp_support.api.schedule_server as tesp;'
                              'tesp.schedule_server(\'..\\%s\', %s)" ^> %s\\schedule.log 2^>^&1\n'
                              % (config_file, str(5150 + ports[cnt]), outPath))
            outfile.write('rem wait schedule server to populate\n')
            outfile.write('sleep 60\n')

            outfile.write('start /b cmd /c fncs_broker %s ^>%s\\broker.log 2^>^&1\n'
                          % (str(len(weather_config) * 3 + tso), outPath))

            for w_key, w_val in weather_config.items():
                outfile.write('set FNCS_CONFIG_FILE=%s.zpl\n' % w_key)
                outfile.write('cd %s\n' % w_key)
                outfile.write('start /b cmd /c python -c "import tesp_support.weather.weather_agent_f as tesp;'
                              'tesp.startWeatherAgent(\'weather.dat\')" ^> %s\\%s_weather.log 2^>^&1\n'
                              % (outPath, w_key))
                outfile.write('cd ..\n')

            for sub_key, sub_val in substation_config.items():
                if "DSO" not in sub_key:
                    continue
                try:
                    if not sub_val['used']:
                        continue
                except:
                    pass
                outfile.write('cd %s\n' % sub_val['substation'])
                outfile.write('start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE="%s_metrics_" %s.glm ^> '
                              '%s\\%s_gridlabd.log 2^>^&1\n'
                              % (sub_val['substation'], sub_val['substation'], outPath, sub_val['substation']))
                outfile.write('set FNCS_CONFIG_FILE=%s.yaml\n' % sub_val['substation'])
                outfile.write('cd ..\n')
                outfile.write('cd %s\n' % sub_key)
                outfile.write('start /b cmd /c python -c "import tesp_support.dsot.substation_f as tesp;'
                              'tesp.dso_loop_f(\'%s_agent_dict.json\',\'%s\',%%with_market%%)" ^> '
                              '%s\\%s_substation.log 2^>^&1\n'
                              % (sub_val['substation'], sub_val['substation'], outPath, sub_key))
                outfile.write('cd ..\n')
            if master_file != '':
                outfile.write('set FNCS_CONFIG_FILE=tso.yaml\n')
                outfile.write('start /b cmd /c python -c "import tesp_support.original.tso_psst_f as tesp;'
                              'tesp.tso_psst_loop_f(\'./%s\')" ^> %s\\tso.log 2^>^&1\n'
                              % (master_file, outPath))

                for plyr in range(len(players)):
                    player = system_config[players[plyr]]
                    if player[6] or player[7]:
                        outfile.write('set FNCS_CONFIG_FILE=%s_player.yaml\n' % (player[0]))
                        outfile.write('start /b cmd /c python -c "import tesp_support.original.player_f as tesp;'
                                      'tesp.load_player_loop_f(\'./%s\', \'%s\')" ^> %s\\%s_player.log 2^>^&1\n'
                                      % (master_file, players[plyr], outPath, player[0]))

        with open(out_folder + '/kill.bat', 'w') as outfile:
            outfile.write('taskkill /F /IM fncs_broker.exe\n')
            outfile.write('taskkill /F /IM python.exe\n')
            outfile.write('taskkill /F /IM gridlabd.exe\n')

        with open(out_folder + '/clean.bat', 'w') as outfile:
            outfile.write('del ' + outPath + '\\*.log /s\n')
            outfile.write('del ' + outPath + '\\*.csv /s\n')
            outfile.write('del ' + outPath + '\\*.out /s\n')
            outfile.write('del ' + outPath + '\\*rtm.dat /s\n')
            outfile.write('del ' + outPath + '\\*dam.dat /s\n')
            outfile.write('del ' + outPath + '\\*uc.dat /s\n')
            outfile.write('del ' + outPath + '\\*ames.dat /s\n')
            outfile.write('del ' + outPath + '\\*metrics*.json* /s\n')
            outfile.write('del ' + outPath + '\\*metrics*.h5 /s\n')
            outfile.write('del ' + outPath + '\\*model_dict.json /s\n')
            outfile.write('del broker_trace.txt\n')
    else:  # Unix
        with open(out_folder + '/run.sh', 'w') as outfile:
            outfile.write('#!/bin/bash\n\n')
            outfile.write('export FNCS_LOG_LEVEL=INFO\n')
            if platform.system() == 'Darwin':
                # this is needed if you are not comfortable disabling System Integrity Protection
                dyldPath = environ.get('DYLD_LIBRARY_PATH')
                if dyldPath is not None:
                    outfile.write('export DYLD_LIBRARY_PATH=%s\n\n' % dyldPath)

            outfile.write('mkdir -p PyomoTempFiles\n\n')
            outfile.write('# To run agents set with_market=1 else set with_market=0 \n')
            if system_config["market"]:
                outfile.write('with_market=1\n\n')
            else:
                outfile.write('with_market=0\n\n')

            for cnt in range(len(ports)):
                outfile.write('(exec python3 -c "import tesp_support.api.schedule_server as tesp;'
                              'tesp.schedule_server(\'../%s\', %s)" &> %s/schedule.log &)\n'
                              % (config_file, str(5150 + ports[cnt]), outPath))
            outfile.write('# wait schedule server to populate\n')
            outfile.write('sleep 60\n')

            outfile.write('(export FNCS_BROKER="tcp://*:' + str(system_config['port'])
                          + '" && fncs_broker %s &> %s/broker.log &)\n'
                          % (str(len(weather_config) * 3 + tso), outPath))

            for w_key, w_val in weather_config.items():
                outfile.write('cd %s\n' % w_key)
                outfile.write('(export FNCS_CONFIG_FILE=%s.zpl && export WEATHER_CONFIG=weather_Config.json '
                              '&& exec python3 -c "import tesp_support.weather.weather_agent_f as tesp;'
                              'tesp.startWeatherAgent(\'weather.dat\')" &> %s/%s_weather.log &)\n'
                              % (w_key, outPath, w_key))
                outfile.write('cd ..\n')

            for sub_key, sub_val in substation_config.items():
                if "DSO" not in sub_key:
                    continue
                try:
                    if not sub_val['used']:
                        continue
                except:
                    pass
                outfile.write('cd %s\n' % sub_val['substation'])
                outfile.write(
                    '(%sgridlabd -D USE_FNCS -D METRICS_FILE="%s/%s_metrics_" %s.glm &> %s/%s_gridlabd.log &)\n'
                    % (dbg, outPath, sub_val['substation'], sub_val['substation'], outPath, sub_val['substation']))
                outfile.write('cd ..\n')
                outfile.write('cd %s\n' % sub_key)
                outfile.write('(export FNCS_CONFIG_FILE=%s.yaml '
                              '&& exec python3 -c "import tesp_support.dsot.substation_f as tesp;'
                              'tesp.dso_loop_f(\'%s_agent_dict.json\',\'%s\',$with_market)" &> '
                              '%s/%s_substation.log &)\n'
                              % (sub_val['substation'], sub_val['substation'], sub_val['substation'], outPath, sub_key))
                outfile.write('cd ..\n')

            if master_file != '':
                outfile.write('(export FNCS_CONFIG_FILE=tso.yaml '
                              '&& exec python3 -c "import tesp_support.original.tso_psst_f as tesp;'
                              'tesp.tso_psst_loop_f(\'./%s\')" &> %s/tso.log &)\n'
                              % (master_file, outPath))
                for plyr in range(len(players)):
                    player = system_config[players[plyr]]
                    if player[6] or player[7]:
                        outfile.write('(export FNCS_CONFIG_FILE=%s_player.yaml '
                                      '&& exec python3 -c "import tesp_support.original.player_f as tesp;'
                                      'tesp.load_player_loop_f(\'./%s\', \'%s\')" &> %s/%s_player.log &)\n'
                                      % (player[0], master_file, players[plyr], outPath, player[0]))

        write_management_script(archive_folder, case_path, outPath, system_config['gldDebug'], 1)


def write_management_script(archive_folder, case_path, outPath, gld_Debug, run_post):
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
        gdb_extra = "" if gld_Debug == 0 else \
            """
                   --cap-add=SYS_PTRACE \\
                   --security-opt seccomp=unconfined\\"""
        outfile.write("""
IMAGE="cosim-cplex:tesp_22.04.1"

git describe --tags > tesp_version
docker images -q ${IMAGE} > docker_version
hostname > hostname

WORKING_DIR="$SIM_HOME/tesp/examples/analysis/dsot/code/%s"
ARCHIVE_DIR="%s"

docker run \\
       -e LOCAL_USER_ID=$SIM_UID \\
       -itd \\
       --rm \\
       --network=none \\%s
       --mount type=bind,source="$TESPDIR",destination="$SIM_HOME/tesp" \\
       -w=${WORKING_DIR} \\
       ${IMAGE} \\
       /bin/bash -c "./run.sh; ./monitor.sh"
        """ % (path.basename(out_folder), archive_folder, gdb_extra))

    with open(out_folder + '/postprocess.sh', 'w') as outfile:
        if run_post == 1:
            outfile.write('python3 ../run_case_postprocessing.py > postprocessing.log\n')
        outfile.write('mkdir -p %s/$(cat tesp_version)\n' % (archive_folder))
        outfile.write('rm -rf %s/$(cat tesp_version)/%s\n' % (archive_folder, case_path))
        outfile.write('mv -f ../%s %s/$(cat tesp_version)\n' % (case_path, archive_folder))

    with open(out_folder + '/kill.sh', 'w') as outfile:
        outfile.write('pkill -9 fncs_broker\n')
        outfile.write('pkill -9 helics_broker\n')
        outfile.write('pkill -9 python\n')
        outfile.write('pkill -9 gridlabd\n')

    with open(out_folder + '/clean.sh', 'w') as outfile:
        outfile.write('cd ' + outPath + '\n')
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

    subprocess.run(['chmod', '+x', out_folder + '/run.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/monitor.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/docker-run.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/postprocess.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/kill.sh'])
    subprocess.run(['chmod', '+x', out_folder + '/clean.sh'])


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
    flatList = [item for elem in [x_vec_1, x_vec_2] for item in elem]
    x = np.array(flatList)
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
    flatList = [item for elem in [x_vec_1, x_vec_2] for item in elem]
    x = np.array(flatList)
    x = np.sort(x)
    x = np.unique(x)
    new_p_1 = []
    new_p_2 = []
    for val in x:
        new_p_1.append(np.interp(val, x_vec_1, y_vec_1))
        new_p_2.append(np.interp(val, x_vec_2, y_vec_2))


if __name__ == "__main__":
    test()
