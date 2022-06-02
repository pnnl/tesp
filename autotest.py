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
from tesp_support.run_test_case import PrepareTest
from tesp_support.run_test_case import RunTest
from tesp_support.run_test_case import InitializeTestReports
from tesp_support.run_test_case import GetTestReports

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def gld_player_test():
    PrepareTest('GridlabD Player/Recorder example')
    os.chdir('./examples/capabilities/gld_player_recorder')
    RunTest('run.sh', 'GridlabD Player/Recorder')
    os.chdir(tesp_path)


def loadshed_test():
    PrepareTest('Loadshed examples')
    if bTryHELICS:
        os.chdir('./examples/capabilities/loadshed')
        p1 = subprocess.Popen('./clean.sh', shell=True)
        p1.wait()
        RunTest('runhpy.sh', 'Loadshed - HELICS ns-3')
        RunTest('runhpy0.sh', 'Loadshed - HELICS Python')
        RunTest('runhjava.sh', 'Loadshed - HELICS Java')
    else:
        os.chdir('./examples/capabilities/loadshedf')
        p1 = subprocess.Popen('./clean.sh', shell=True)
        p1.wait()
        RunTest('run.sh', 'Loadshed - FNCS Python')
        RunTest('runjava.sh', 'Loadshed - FNCS Java')
    os.chdir(tesp_path)


def houses_test():
    PrepareTest('Houses example')
    os.chdir('./examples/capabilities/houses')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    RunTest('run.sh', 'Houses')
    os.chdir(tesp_path)


def PYPOWER_test():
    PrepareTest('PYPOWER example')
    os.chdir('./examples/capabilities/pypower')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTest('runhpp.sh', 'PYPOWER - HELICS')
    else:
        RunTest('runpp.sh', 'PYPOWER - FNCS')
    os.chdir(tesp_path)


def EnergyPlus_test():
    PrepareTest('EnergyPlus EMS/IDF examples')
    os.chdir('./examples/capabilities/energyplus')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    #  p1 = subprocess.Popen ('./run_baselines.sh', shell=True)
    #  p1.wait()
    #  p1 = subprocess.Popen ('./make_all_ems.sh', shell=True)
    #  p1.wait()
    if bTryHELICS:
        RunTest('runh.sh', 'EnergyPlus EMS - HELICS')
    #    RunTest ('batch_ems_case.sh', 'EnergyPlus Batch EMS')
    else:
        RunTest('run.sh', 'EnergyPlus IDF - FNCS')
        RunTest('run2.sh', 'EnergyPlus EMS - FNCS')
    os.chdir(tesp_path)


def weather_agent_test():
    PrepareTest('Weather Agent example')
    os.chdir('./examples/capabilities/weatherAgent')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTest('runh.sh', 'Weather Agent - HELICS')
    else:
        RunTest('run.sh', 'Weather Agent - FNCS')
    os.chdir(tesp_path)


def TE30_test():
    PrepareTest('TE30 examples')
    os.chdir('./examples/capabilities/te30')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_case.py', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTest('runh.sh', 'TE30 - HELICS Market')
        RunTest('runh0.sh', 'TE30 - HELICS No Market')
    else:
        RunTest('run.sh', 'TE30 - FNCS Market')
        RunTest('run0.sh', 'TE30 - FNCS No Market')
    os.chdir(tesp_path)


def make_comm_base_test():
    PrepareTest('Communication Network examples')
    os.chdir('./examples/capabilities/comm')
    p1 = subprocess.Popen(pycall + ' make_comm_base.py', shell=True)
    p1.wait()

    # generated Nocomm_Base example
    os.chdir('Nocomm_Base')
    if bTryHELICS:
        st = os.stat('runh.sh')
        os.chmod('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('runh.sh', 'Nocomm Base - HELICS')
    else:
        st = os.stat('run.sh')
        os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('run.sh', 'Nocomm Base - FNCS')
    os.chdir(tesp_path)

    # generated Eplus_Restaurant example
    os.chdir('./examples/capabilities/comm/Eplus_Restaurant')
    if bTryHELICS:
        st = os.stat('runh.sh')
        os.chmod('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('runh.sh', 'Eplus Restaurant - HELICS')
    else:
        st = os.stat('run.sh')
        os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('run.sh', 'Eplus Restaurant - FNCS')
    os.chdir(tesp_path)

    # generated SGIP1c example
    os.chdir('./examples/capabilities/comm/SGIP1c')
    if bTryHELICS:
        st = os.stat('runh.sh')
        os.chmod('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('runh.sh', 'SGIP1c - HELICS')
    else:
        st = os.stat('run.sh')
        os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('run.sh', 'SGIP1c - FNCS')
    os.chdir(tesp_path)


def make_comm_eplus_test():
    PrepareTest('Eplus with Communication Network example')
    os.chdir('./examples/capabilities/comm')
    p1 = subprocess.Popen(pycall + ' make_comm_eplus.py', shell=True)
    p1.wait()
    os.chdir('Eplus_Comm')
    st = os.stat('run.sh')
    os.chmod('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTest('run.sh', 'EPLus comm HELICS')
    os.chdir(tesp_path)


def combine_feeders_test():
    PrepareTest('Communication Network Combined Case example')
    os.chdir('./examples/capabilities/comm')
    p1 = subprocess.Popen(pycall + ' combine_feeders.py', shell=True)
    p1.wait()
    shutil.copy('runcombined.sh', 'CombinedCase')
    shutil.copy('runcombinedh.sh', 'CombinedCase')
    os.chdir('CombinedCase')
    if bTryHELICS:
        st = os.stat('runcombinedh.sh')
        os.chmod('runcombinedh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('runcombinedh.sh', '4 Feeders - HELICS')
    else:
        st = os.stat('runcombined.sh')
        os.chmod('runcombined.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        RunTest('runcombined.sh', '4 Feeders - FNCS')
    os.chdir(tesp_path)


def dso_stub_test():
    PrepareTest('DSO Stub example')
    if bTryHELICS:
        os.chdir('./examples/capabilities/dsostub')
    else:
        os.chdir('./examples/capabilities/dsostubf')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen('./runstub.sh Test', shell=True)
    p1.wait()
    os.chdir('./Test')
    if bTryHELICS:
        RunTest('run.sh', 'DSO Stub - HELICS')
    else:
        RunTest('run.sh', 'DSO Stub - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    InitializeTestReports()

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

    print(GetTestReports())
