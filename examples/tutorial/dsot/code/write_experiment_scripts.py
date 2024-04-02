# -*- coding: utf-8 -*-
"""
Created on Sun Mar 31 16:47:47 2024

@author: mukh915
"""

import platform
import subprocess
from os import getcwd, path, environ

def write_dsot_management_script_h(master_file, case_path, system_config=None, substation_config=None,
                                   weather_config=None, HELICS_flag=False):
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
    run_post = True
    
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
            
            outfile.write('set TESPDIR=' + path.abspath("../../../../") + '\n')
            outfile.write('set WEATHER_CONFIG=weather_Config.json\n')
            # outfile.write('set FNCS_BROKER="tcp://*:' + str(system_config['port']) + '"\n')

            outfile.write('rem To run agents set with_market=1 else set with_market=0 \n')
            if system_config["market"]:
                outfile.write('set with_market=1\n')
            else:
                outfile.write('set with_market=0\n')

            # for cnt in range(len(ports)):
            #     outfile.write('start /b cmd /c python -c "import tesp_support.api.schedule_server as tesp;'
            #                   'tesp.schedule_server(\'..\\%s\', %s)" ^> %s\\schedule.log 2^>^&1\n'
            #                   % (config_file, str(5150 + ports[cnt]), outPath))
            # outfile.write('rem wait schedule server to populate\n')
            # outfile.write('sleep 60\n')
            if HELICS_flag:
                outfile.write('start /b cmd /c helics_broker -f %s --loglevel=warning --name=mainbroker ^>%s\\broker.log 2^>^&1\n'
                          % (str(len(weather_config) * 3 + tso), outPath))

                for w_key, w_val in weather_config.items():
                    outfile.write('set WEATHER_CONFIG=weather_Config.json \n')
                    outfile.write('cd %s\n' % w_key)
                    outfile.write('start /b cmd /c python -c "import tesp_support.weather.weather_agent as tesp;'
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
                if HELICS_flag:
                    outfile.write('start /b cmd /c gridlabd -D USE_HELICS -D METRICS_FILE="%s_metrics_" %s.glm ^> '
                                  '%s\\%s_gridlabd.log 2^>^&1\n'
                                  % (sub_val['substation'], sub_val['substation'], outPath, sub_val['substation']))
                else:
                    outfile.write('start /b cmd /c gridlabd -D METRICS_FILE="%s_metrics_" %s.glm ^> '
                                  '%s\\%s_gridlabd.log 2^>^&1\n'
                                  % (sub_val['substation'], sub_val['substation'], outPath, sub_val['substation']))
               
                outfile.write('cd ..\n')
                if HELICS_flag:
                    outfile.write('cd %s\n' % sub_key)
                    outfile.write('start /b cmd /c python -c "import tesp_support.dsot.substation as tesp;'
                                  'tesp.dso_loop(\'%s_agent_dict.json\',\'%s\',%%with_market%%)" ^> '
                                  '%s\\%s_substation.log 2^>^&1\n'
                                  % (sub_val['substation'], sub_val['substation'], outPath, sub_key))
                    outfile.write('cd ..\n')
            if master_file != '':
                if HELICS_flag:
                    outfile.write('set HELCIS_CONFIG_FILE=tso_h.json\n')
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
            outfile.write('taskkill /F /IM helics_broker.exe\n')
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
            
            
        with open(out_folder + '/postprocess.bat', 'w') as outfile:
            if run_post == 1:
                outfile.write('start /b cmd /c python -c ../run_case_postprocessing.py > postprocessing.log\n')
            # outfile.write('mkdir -p %s/$(cat tesp_version)\n' % (archive_folder))
            # outfile.write('rm -rf %s/$(cat tesp_version)/%s\n' % (archive_folder, case_path))
            # outfile.write('mv -f ../%s %s/$(cat tesp_version)\n' % (case_path, archive_folder))
    else:  # Unix
        with open(out_folder + '/run.sh', 'w') as outfile:
            outfile.write('#!/bin/bash\n\n')
            if platform.system() == 'Darwin':
                # this is needed if you are not comfortable disabling System Integrity Protection
                dyldPath = environ.get('DYLD_LIBRARY_PATH')
                if dyldPath is not None:
                    outfile.write('export DYLD_LIBRARY_PATH=%s\n\n' % dyldPath)
    
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
                        
        with open(out_folder + '/postprocess.sh', 'w') as outfile:
            if run_post == 1:
                outfile.write('python3 ../run_case_postprocessing.py > postprocessing.log\n')
            # outfile.write('mkdir -p %s/$(cat tesp_version)\n' % (archive_folder))
            # outfile.write('rm -rf %s/$(cat tesp_version)/%s\n' % (archive_folder, case_path))
            # outfile.write('mv -f ../%s %s/$(cat tesp_version)\n' % (case_path, archive_folder))
