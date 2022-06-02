# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest_long.py
"""Runs the longer set of TESP test cases; 
SGIP1, NIST TE Challenge 2, ERCOT 8-Bus with PSST
"""
import os
import subprocess
import sys

from tesp_support.run_test_case import GetTestReports
from tesp_support.run_test_case import InitializeTestReports
from tesp_support.run_test_case import PrepareTest
from tesp_support.run_test_case import RunTest
from tesp_support.run_test_case import block

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def sgip_test():
    PrepareTest('SGIP1 examples')
    os.chdir('./examples/analysis/sgip1')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTest('ruhSGIP1a.sh', 'SGIP1a - HELICS')
        RunTest('ruhSGIP1b.sh', 'SGIP1b - HELICS')
        RunTest('ruhSGIP1c.sh', 'SGIP1c - HELICS')
        RunTest('ruhSGIP1d.sh', 'SGIP1d - HELICS')
        RunTest('ruhSGIP1e.sh', 'SGIP1e - HELICS')
        RunTest('ruhSGIP1ex.sh', 'SGIP1ex - HELICS')
    else:
        RunTest('runSGIP1a.sh', 'SGIP1a - FNCS')
        RunTest('runSGIP1b.sh', 'SGIP1b - FNCS')
        RunTest('runSGIP1c.sh', 'SGIP1c - FNCS')
        RunTest('runSGIP1d.sh', 'SGIP1d - FNCS')
        RunTest('runSGIP1e.sh', 'SGIP1e - FNCS')
        RunTest('runSGIP1ex.sh', 'SGIP1ex - FNCS')
    os.chdir(tesp_path)


def ieee8500_base_test():
    PrepareTest('IEEE8500 GRIDLabD example')
    os.chdir('./examples/capabilities/ieee8500')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    print('\n==  Run: IEEE8500 GRIDLabD')
    p1 = subprocess.Popen('gridlabd IEEE_8500.glm', shell=True)
    p1.wait()
    print('\n==  Done IEEE8500 GRIDLabD')
    os.chdir(tesp_path)


def ieee8500_precool_test():
    PrepareTest('ieee8500 PNNLteam examples')
    os.chdir('./examples/capabilities/ieee8500/PNNLteam')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    if bTryHELICS:
        p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
        p1.wait()
        RunTest('run30.sh', 'PNNL Team 30 - HELICS')
        RunTest('runti30.sh', 'PNNL Team ti30 - HELICS')
        RunTest('run8500.sh', 'PNNL Team 8500 - HELICS')
        RunTest('run8500base.sh', 'PNNL Team 8500 Base - HELICS')
        RunTest('run8500tou.sh', 'PNNL Team 8500 TOU - HELICS')
        RunTest('run8500volt.sh', 'PNNL Team 8500 Volt - HELICS')
        RunTest('run8500vvar.sh', 'PNNL Team 8500 VoltVar - HELICS')
        RunTest('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt - HELICS')
        os.chdir(tesp_path)
    else:
        p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
        p1.wait()
        RunTest('run30.sh', 'PNNL Team 30 - FNCS')
        RunTest('runti30.sh', 'PNNL Team ti30 - FNCS')
        RunTest('run8500.sh', 'PNNL Team 8500 - FNCS')
        RunTest('run8500base.sh', 'PNNL Team 8500 Base - FNCS')
        RunTest('run8500tou.sh', 'PNNL Team 8500 TOU - FNCS')
        RunTest('run8500volt.sh', 'PNNL Team 8500 Volt - FNCS')
        RunTest('run8500vvar.sh', 'PNNL Team 8500 VoltVar - FNCS')
        RunTest('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt - FNCS')
        os.chdir(tesp_path)


def ercot_test():
    # ERCOT Case8 example
    PrepareTest('ERCOT Case8 examples')
    os.chdir('./examples/capabilities/ercot/dist_system')
    p1 = subprocess.Popen(pycall + ' populate_feeders.py', shell=True)
    p1.wait()
    os.chdir('../case8')
    p1 = subprocess.Popen(pycall + ' prepare_case.py', shell=True)
    p1.wait()
    if bTryHELICS:
        RunTest('runh.sh', 'ERCOT 8-bus No Market - HELICS')
        RunTest('runmarketh.sh', 'ERCOT 8-bus Market - HELICS')
    else:
        RunTest('run.sh', 'ERCOT 8-bus No Market - FNCS')
        RunTest('run_market.sh', 'ERCOT 8-bus Market - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    InitializeTestReports()

    tesp_path = os.path.expandvars('$TESPDIR/')
    os.chdir(tesp_path)
    bTryHELICS = True

    block(sgip_test)
    # block(ieee8500_base_test)
    # block(ieee8500_precool_test)
    # block(ercot_test)

    print(GetTestReports())
