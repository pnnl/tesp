# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest_long.py
"""Runs the longer set of TESP test cases; 
SGIP1, NIST TE Challenge 2, ERCOT 8-Bus with PSST
"""
import sys
import subprocess
import os
from tesp_support.run_test_case import RunTestCase
from tesp_support.run_test_case import InitializeTestCaseReports
from tesp_support.run_test_case import GetTestCaseReports

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

if __name__ == '__main__':
    InitializeTestCaseReports()

    basePath = os.getcwd()

    # SGIP1 examples (these take a few hours to run the set)
    print('start examples sgip1: ')
    os.chdir('./examples/analysis/sgip1')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
    p1.wait()
    RunTestCase('runSGIP1a.sh', 'SGIP1a (FNCS)')
    RunTestCase('runSGIP1b.sh', 'SGIP1b (FNCS)')
    RunTestCase('runSGIP1c.sh', 'SGIP1c (FNCS)')
    RunTestCase('runSGIP1d.sh', 'SGIP1d (FNCS)')
    RunTestCase('runSGIP1e.sh', 'SGIP1e (FNCS)')
    RunTestCase('runSGIP1ex.sh', 'SGIP1ex (FNCS)')
    os.chdir(basePath)

    # ieee8500 base example
    print('start examples ieee8500: ')
    os.chdir('./examples/capabilities/ieee8500')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen('gridlabd IEEE_8500.glm', shell=True)
    p1.wait()
    os.chdir(basePath)

    # ieee8500 precool examples (these take a few hours to run the set)
    print('start examples ieee8500 PNNLteam: ')
    os.chdir('./examples/capabilities/ieee8500/PNNLteam')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
    p1.wait()
    RunTestCase('run30.sh', 'PNNL Team 30')
    RunTestCase('runti30.sh', 'PNNL Team ti30')
    RunTestCase('run8500.sh', 'PNNL Team 8500')
    RunTestCase('run8500base.sh', 'PNNL Team 8500 Base')
    RunTestCase('run8500tou.sh', 'PNNL Team 8500 TOU')
    RunTestCase('run8500volt.sh', 'PNNL Team 8500 Volt')
    RunTestCase('run8500vvar.sh', 'PNNL Team 8500 VoltVar')
    RunTestCase('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt')
    os.chdir(basePath)

    # ERCOT Case8 example
    print('start examples ERCOT Case8: ')
    os.chdir('./examples/capabilities/ercot/dist_system')
    p1 = subprocess.Popen(pycall + ' populate_feeders.py', shell=True)
    p1.wait()
    os.chdir('../case8')
    p1 = subprocess.Popen(pycall + ' prepare_case.py', shell=True)
    p1.wait()
    RunTestCase('run.sh', 'ERCOT 8-bus No Market')
    RunTestCase('run_market.sh', 'ERCOT 8-bus Market')
    os.chdir(basePath)

    print(GetTestCaseReports())
