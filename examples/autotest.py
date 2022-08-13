# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases, excluding the longer FNCS cases
MATPOWER/MOST example must be run after manual installation of Octave and MATPOWER
"""
import os
import sys
import shutil
import subprocess

from tesp_support.run_tesp_case import init_tests
from tesp_support.run_tesp_case import block_test
from tesp_support.run_tesp_case import start_test
from tesp_support.run_tesp_case import run_test
from tesp_support.run_tesp_case import report_tests

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def gld_player_test():
    start_test('GridLAB-D Player/Recorder example')
    os.chdir('capabilities/gld_player_recorder')
    run_test('run.sh', 'GridLAB-D Player/Recorder')
    os.chdir(tesp_path)


def loadshed_test():
    start_test('Loadshed examples')
    if b_helics:
        os.chdir('capabilities/loadshed')
        subprocess.Popen('./clean.sh', shell=True).wait()
        run_test('runhpy.sh', 'Loadshed - HELICS ns-3')
        run_test('runhpy0.sh', 'Loadshed - HELICS Python')
        run_test('runhjava.sh', 'Loadshed - HELICS Java')
    else:
        os.chdir('capabilities/loadshedf')
        subprocess.Popen('./clean.sh', shell=True).wait()
        run_test('run.sh', 'Loadshed - FNCS Python')
        run_test('runjava.sh', 'Loadshed - FNCS Java')
    os.chdir(tesp_path)


def houses_test():
    start_test('Houses example')
    os.chdir('capabilities/houses')
    subprocess.Popen('./clean.sh', shell=True).wait()
    run_test('run.sh', 'Houses')
    os.chdir(tesp_path)


def PYPOWER_test():
    start_test('PYPOWER example')
    os.chdir('capabilities/pypower')
    subprocess.Popen('./clean.sh', shell=True).wait()
    if b_helics:
        run_test('runhpp.sh', 'PYPOWER - HELICS')
    else:
        run_test('runpp.sh', 'PYPOWER - FNCS')
    os.chdir(tesp_path)


def EnergyPlus_test():
    start_test('EnergyPlus EMS/IDF examples')
    os.chdir('capabilities/energyplus')
    subprocess.Popen('./clean.sh', shell=True).wait()
    #  subprocess.Popen('./run_baselines.sh', shell=True).wait()
    #  subprocess.Popen('./make_all_ems.sh', shell=True).wait()
    if b_helics:
        run_test('runh.sh', 'EnergyPlus EMS - HELICS')
    #    run_test('batch_ems_case.sh', 'EnergyPlus Batch EMS')
    else:
        run_test('run.sh', 'EnergyPlus IDF - FNCS')
        run_test('run2.sh', 'EnergyPlus EMS - FNCS')
    os.chdir(tesp_path)


def weather_agent_test():
    start_test('Weather Agent example')
    os.chdir('capabilities/weatherAgent')
    subprocess.Popen('./clean.sh', shell=True).wait()
    if b_helics:
        run_test('runh.sh', 'Weather Agent - HELICS')
    else:
        run_test('run.sh', 'Weather Agent - FNCS')
    os.chdir(tesp_path)


def TE30_test():
    start_test('TE30 examples')
    os.chdir('capabilities/te30')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_case.py', shell=True).wait()
    if b_helics:
        run_test('runh.sh', 'TE30 - HELICS Market')
        run_test('runh0.sh', 'TE30 - HELICS No Market')
    else:
        run_test('run.sh', 'TE30 - FNCS Market')
        run_test('run0.sh', 'TE30 - FNCS No Market')
    os.chdir(tesp_path)


def make_comm_base_test():
    start_test('Communication Network examples')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' make_comm_base.py', shell=True).wait()

    # generated Nocomm_Base example
    os.chdir('Nocomm_Base')
    if b_helics:
        run_test('runh.sh', 'No Comm Base - HELICS')
    else:
        run_test('run.sh', 'No Comm Base - FNCS')

    # generated Eplus_Restaurant example
    os.chdir(tesp_path + '/capabilities/comm/Eplus_Restaurant')
    if b_helics:
        run_test('runh.sh', 'Eplus Restaurant - HELICS')
    else:
        run_test('run.sh', 'Eplus Restaurant - FNCS')

    # generated SGIP1c example
    os.chdir(tesp_path + '/capabilities/comm/SGIP1c')
    if b_helics:
        run_test('runh.sh', 'SGIP1c - HELICS')
    else:
        run_test('run.sh', 'SGIP1c - FNCS')
    os.chdir(tesp_path)


def make_comm_eplus_test():
    start_test('Eplus with Communication Network example')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' make_comm_eplus.py', shell=True).wait()
    os.chdir('Eplus_Comm')
    run_test('run.sh', 'Eplus w/Comm - HELICS')
    os.chdir(tesp_path)


def combine_feeders_test():
    start_test('Communication Network Combined Case example')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' combine_feeders.py', shell=True).wait()
    shutil.copy('runcombined.sh', 'CombinedCase')
    shutil.copy('runcombinedh.sh', 'CombinedCase')
    os.chdir('CombinedCase')
    if b_helics:
        run_test('runcombinedh.sh', '4 Feeders - HELICS')
    else:
        run_test('runcombined.sh', '4 Feeders - FNCS')
    os.chdir(tesp_path)


def dso_stub_test():
    start_test('DSO Stub example')
    if b_helics:
        os.chdir('capabilities/dsostub')
    else:
        os.chdir('capabilities/dsostubf')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen('./runstub.sh Test', shell=True).wait()
    os.chdir('./Test')
    if b_helics:
        run_test('run.sh', 'DSO Stub - HELICS')
    else:
        run_test('run.sh', 'DSO Stub - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    b_helics = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "FNCS":
            b_helics = False

    init_tests()

    tesp_path = os.path.expandvars('$TESPDIR/examples')
    os.chdir(tesp_path)
    b_helics = False

    block_test(gld_player_test)
    block_test(loadshed_test)
    block_test(PYPOWER_test)
    block_test(EnergyPlus_test)
    block_test(weather_agent_test)
    block_test(houses_test)
    block_test(TE30_test)
    block_test(make_comm_base_test)
    block_test(make_comm_eplus_test)
    block_test(combine_feeders_test)
    block_test(dso_stub_test)

    print(report_tests())
