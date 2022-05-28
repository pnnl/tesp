# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases, excluding the longer FNCS cases
MATPOWER/MOST example must be run after manual installation of Octave and MATPOWER
"""
import os
import sys
import stat
import shutil
import subprocess
from tesp_support.run_test_case import block
from tesp_support.run_test_case import RunTestCase
from tesp_support.run_test_case import InitializeTestCaseReports
from tesp_support.run_test_case import GetTestCaseReports

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def gld_player_test():
    print('==  Prepare: GridlabD Player/Recorder example', flush=True)
    os.chdir('./examples/capabilities/gld_player_recorder')
    RunTestCase('run.sh', 'GridlabD Player/Recorder')
    os.chdir(tesp_path)


def loadshed_test():
    print('==  Prepare: Loadshed examples', flush=True)
    if bTryHELICS:
        os.chdir('./examples/capabilities/loadshed')
        p1 = subprocess.Popen('./clean.sh', shell=True)
        p1.wait()
        RunTestCase('runhpy.sh', 'Loadshed - HELICS ns-3')
        RunTestCase('runhpy0.sh', 'Loadshed - HELICS Python')
        RunTestCase('runhjava.sh', 'Loadshed - HELICS Java')
    else:
        os.chdir('./examples/capabilities/loadshedf')
        p1 = subprocess.Popen('./clean.sh', shell=True)
        p1.wait()
        RunTestCase('run.sh', 'Loadshed - FNCS Python')
        RunTestCase('runjava.sh', 'Loadshed - FNCS Java')
    os.chdir(tesp_path)


def houses_test():
    print('==  Prepare: Houses example', flush=True)
    os.chdir('./examples/capabilities/houses')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    RunTestCase('run.sh', 'Houses')
    os.chdir(tesp_path)


def PYPOWER_test():
    print('==  Prepare: PYPOWER example', flush=True)
    os.chdir('./examples/capabilities/pypower')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTestCase('runhpp.sh', 'PYPOWER - HELICS')
    else:
        RunTestCase('runpp.sh', 'PYPOWER - FNCS')
    os.chdir(tesp_path)


def EnergyPlus_test():
    print('==  Prepare: EnergyPlus examples', flush=True)
    os.chdir('./examples/capabilities/energyplus')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    #  p1 = subprocess.Popen ('./run_baselines.sh', shell=True)
    #  p1.wait()
    #  p1 = subprocess.Popen ('./make_all_ems.sh', shell=True)
    #  p1.wait()
    if bTryHELICS:
        RunTestCase('runh.sh', 'EnergyPlus - HELICS EMS')
    #    RunTestCase ('batch_ems_case.sh', 'EnergyPlus Batch EMS')
    else:
        RunTestCase('run.sh', 'EnergyPlus - FNCS IDF')
        RunTestCase('run2.sh', 'EnergyPlus - FNCS EMS')
    os.chdir(tesp_path)


def weather_agent_test():
    print('==  Prepare: Weather Agent example', flush=True)
    os.chdir('./examples/capabilities/weatherAgent')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTestCase('runh.sh', 'Weather Agent - HELICS')
    else:
        RunTestCase('run.sh', 'Weather Agent - FNCS')
    os.chdir(tesp_path)


def TE30_test():
    print('==  Prepare: TE30 examples', flush=True)
    os.chdir('./examples/capabilities/te30')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_case.py', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTestCase('runh.sh', 'TE30 - HELICS Market')
        RunTestCase('runh0.sh', 'TE30 - HELICS No Market')
    else:
        RunTestCase('run.sh', 'TE30 - FNCS Market')
        RunTestCase('run0.sh', 'TE30 - FNCS No Market')
    os.chdir(tesp_path)


def make_comm_base_test():
    print('==  Prepare: Communication Network examples', flush=True)
    os.chdir('./examples/capabilities/comm')
    p1 = subprocess.Popen(pycall + ' make_comm_base.py', shell=True)
    p1.wait()

    # generated Nocomm_Base example
    os.chdir('Nocomm_Base')
    if bTryHELICS:
        st = os.stat('runh.sh')
        os.chmod('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('runh.sh', 'Nocomm Base - HELICS')
    else:
        st = os.stat('run.sh')
        os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('run.sh', 'Nocomm Base - FNCS')
    os.chdir(tesp_path)

    # generated Eplus_Restaurant example
    os.chdir('./examples/capabilities/comm/Eplus_Restaurant')
    if bTryHELICS:
        st = os.stat('runh.sh')
        os.chmod('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('runh.sh', 'Eplus Restaurant - HELICS')
    else:
        st = os.stat('run.sh')
        os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('run.sh', 'Eplus Restaurant - FNCS')
    os.chdir(tesp_path)

    # generated SGIP1c example
    os.chdir('./examples/capabilities/comm/SGIP1c')
    if bTryHELICS:
        st = os.stat('runh.sh')
        os.chmod('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('runh.sh', 'SGIP1c - HELICS')
    else:
        st = os.stat('run.sh')
        os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('run.sh', 'SGIP1c - FNCS')
    os.chdir(tesp_path)


def make_comm_eplus_test():
    print('==  Prepare: Eplus with Communication Network example', flush=True)
    os.chdir('./examples/capabilities/comm')
    p1 = subprocess.Popen(pycall + ' make_comm_eplus.py', shell=True)
    p1.wait()
    os.chdir('Eplus_Comm')
    st = os.stat('run.sh')
    os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTestCase('run.sh', 'EPLus comm HELICS')
    os.chdir(tesp_path)


def combine_feeders_test():
    print('==  Prepare: Communication Network Combined Case example', flush=True)
    os.chdir('./examples/capabilities/comm')
    p1 = subprocess.Popen(pycall + ' combine_feeders.py', shell=True)
    p1.wait()
    shutil.copy('runcombined.sh', 'Combined Case')
    shutil.copy('runcombinedh.sh', 'Combined Case')
    os.chdir('CombinedCase')
    if bTryHELICS:
        st = os.stat('runcombinedh.sh')
        os.chmod('runcombinedh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('runcombinedh.sh', '4 Feeders - HELICS')
    else:
        st = os.stat('runcombined.sh')
        os.chmod('runcombined.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTestCase('runcombined.sh', '4 Feeders - FNCS')
    os.chdir(tesp_path)


def dso_stub_test():
    print('==  Prepare: DSO Stub example', flush=True)
    if bTryHELICS:
        os.chdir('./examples/capabilities/dsostub')
    else:
        os.chdir('./examples/capabilities/dsostubf')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen('./runstub.sh Test', shell=True)
    p1.wait()
    os.chdir('./Test')
    RunTestCase('run.sh', 'DSO Stub')
    os.chdir(tesp_path)


if __name__ == '__main__':
    InitializeTestCaseReports()

    tesp_path = os.path.expandvars('$TESPDIR/')
    os.chdir(tesp_path)
    bTryHELICS = True

    block(gld_player_test)
    block(loadshed_test)
    block(PYPOWER_test)
    block(EnergyPlus_test)
    block(weather_agent_test)
    block(houses_test)
    block(TE30_test)
    block(make_comm_base_test)
    block(make_comm_eplus_test)
    block(combine_feeders_test)
    block(dso_stub_test)

    print(GetTestCaseReports())
