# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases, excluding the longer FNCS cases
MATPOWER/MOST example must be run after manual installation of Octave and MATPOWER
"""
import os
import sys
import shutil
import subprocess

import tesp_support.tesp_runner as tesp

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def gld_player_test():
    tesp.start_test('GridLAB-D Player/Recorder example')
    os.chdir('capabilities/gld_player_recorder')
    tesp.run_test('run.sh', 'GridLAB-D Player/Recorder')
    os.chdir(tesp_path)


def loadshed_test():
    tesp.start_test('Loadshed examples')
    if b_helics:
        os.chdir('capabilities/loadshed')
        subprocess.Popen('./clean.sh', shell=True).wait()
        tesp.run_test('runhpy.sh', 'Loadshed - HELICS ns-3')
        tesp.run_test('runhpy0.sh', 'Loadshed - HELICS Python')
        tesp.run_test('runhjava.sh', 'Loadshed - HELICS Java')
    else:
        os.chdir('capabilities/loadshedf')
        subprocess.Popen('./clean.sh', shell=True).wait()
        tesp.run_test('run.sh', 'Loadshed - FNCS Python')
        tesp.run_test('runjava.sh', 'Loadshed - FNCS Java')
    os.chdir(tesp_path)


def houses_test():
    tesp.start_test('Houses example')
    os.chdir('capabilities/houses')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tesp.run_test('run.sh', 'Houses')
    os.chdir(tesp_path)


def PYPOWER_test():
    tesp.start_test('PYPOWER example')
    os.chdir('capabilities/pypower')
    subprocess.Popen('./clean.sh', shell=True).wait()
    if b_helics:
        tesp.run_test('runhpp.sh', 'PYPOWER - HELICS')
    else:
        tesp.run_test('runpp.sh', 'PYPOWER - FNCS')
    os.chdir(tesp_path)


def EnergyPlus_test():
    tesp.start_test('EnergyPlus EMS/IDF examples')
    os.chdir('capabilities/energyplus')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tesp.exec_test('./run_baselines.sh > baselines.log', 'Baselines files')
    if b_helics:
        tesp.exec_test('./make_all_ems.sh True > all_ems.log', 'Generated all EMS/IDF files - HELICS')
        tesp.run_test('runh.sh', 'EnergyPlus EMS - HELICS')
    #    tesp.run_test('batch_ems_case.sh', 'EnergyPlus Batch EMS')
    else:
        tesp.exec_test('./make_all_ems.sh False > all_ems_f.log', 'Generated all EMS/IDF files - FNCS')
        tesp.run_test('run.sh', 'EnergyPlus IDF - FNCS')
        tesp.run_test('run2.sh', 'EnergyPlus EMS - FNCS')
    os.chdir(tesp_path)


def weather_agent_test():
    tesp.start_test('Weather Agent example')
    os.chdir('capabilities/weatherAgent')
    subprocess.Popen('./clean.sh', shell=True).wait()
    if b_helics:
        tesp.run_test('runh.sh', 'Weather Agent - HELICS')
    else:
        tesp.run_test('run.sh', 'Weather Agent - FNCS')
    os.chdir(tesp_path)


def TE30_test():
    tesp.start_test('TE30 examples')
    os.chdir('capabilities/te30')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_case.py', shell=True).wait()
    if b_helics:
        tesp.run_test('runh.sh', 'TE30 - HELICS Market')
        tesp.run_test('runh0.sh', 'TE30 - HELICS No Market')
    else:
        tesp.run_test('run.sh', 'TE30 - FNCS Market')
        tesp.run_test('run0.sh', 'TE30 - FNCS No Market')
    os.chdir(tesp_path)


def make_comm_base_test():
    tesp.start_test('Communication Network examples')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' make_comm_base.py', shell=True).wait()

    # generated Nocomm_Base example
    os.chdir('Nocomm_Base')
    if b_helics:
        tesp.run_test('runh.sh', 'No Comm Base - HELICS')
    else:
        tesp.run_test('run.sh', 'No Comm Base - FNCS')

    # generated Eplus_Restaurant example
    os.chdir(tesp_path + '/capabilities/comm/Eplus_Restaurant')
    if b_helics:
        tesp.run_test('runh.sh', 'Eplus Restaurant - HELICS')
    else:
        tesp.run_test('run.sh', 'Eplus Restaurant - FNCS')

    # generated SGIP1c example
    os.chdir(tesp_path + '/capabilities/comm/SGIP1c')
    if b_helics:
        tesp.run_test('runh.sh', 'SGIP1c - HELICS')
    else:
        tesp.run_test('run.sh', 'SGIP1c - FNCS')
    os.chdir(tesp_path)


def make_comm_eplus_test():
    tesp.start_test('Eplus with Communication Network example')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' make_comm_eplus.py', shell=True).wait()
    os.chdir('Eplus_Comm')
    tesp.run_test('run.sh', 'Eplus w/Comm - HELICS')
    os.chdir(tesp_path)


def combine_feeders_test():
    tesp.start_test('Communication Network Combined Case example')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' combine_feeders.py', shell=True).wait()
    shutil.copy('runcombined.sh', 'CombinedCase')
    shutil.copy('runcombinedh.sh', 'CombinedCase')
    os.chdir('CombinedCase')
    if b_helics:
        tesp.run_test('runcombinedh.sh', '4 Feeders - HELICS')
    else:
        tesp.run_test('runcombined.sh', '4 Feeders - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    b_helics = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "FNCS":
            b_helics = False

    tesp.init_tests()
    tesp_path = os.path.expandvars('$TESPDIR/examples')
    os.chdir(tesp_path)

    tesp.block_test(gld_player_test)
    tesp.block_test(loadshed_test)
    tesp.block_test(PYPOWER_test)
    tesp.block_test(EnergyPlus_test)
    tesp.block_test(weather_agent_test)
    tesp.block_test(houses_test)
    tesp.block_test(TE30_test)
    tesp.block_test(combine_feeders_test)
    tesp.block_test(make_comm_eplus_test)  # TODO May not be working correctly
    tesp.block_test(make_comm_base_test)  # there are 3 different runs, takes ~5min each

    print(tesp.report_tests())
