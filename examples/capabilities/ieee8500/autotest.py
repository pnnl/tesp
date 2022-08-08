# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
"""
import os
import subprocess
import sys

from tesp_support.run_tesp_case import init_tests
from tesp_support.run_tesp_case import block_test
from tesp_support.run_tesp_case import start_test
from tesp_support.run_tesp_case import run_test
from tesp_support.run_tesp_case import report_tests

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def ieee8500_base_test():
    start_test('IEEE8500 GridLAB-D example')
    os.chdir('./examples/capabilities/ieee8500')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    print('\n==  Run: IEEE8500 GridLAB-D')
    p1 = subprocess.Popen('gridlabd IEEE_8500.glm', shell=True)
    p1.wait()
    print('\n==  Done IEEE8500 GridLAB-D')
    os.chdir(tesp_path)


def ieee8500_precool_test():
    start_test('ieee8500 PNNLteam examples')
    os.chdir('./examples/capabilities/ieee8500/PNNLteam')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    if bTryHELICS:
        p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
        p1.wait()
        run_test('run30.sh', 'PNNL Team 30 - HELICS')
        run_test('runti30.sh', 'PNNL Team ti30 - HELICS')
        run_test('run8500.sh', 'PNNL Team 8500 - HELICS')
        run_test('run8500base.sh', 'PNNL Team 8500 Base - HELICS')
        run_test('run8500tou.sh', 'PNNL Team 8500 TOU - HELICS')
        run_test('run8500volt.sh', 'PNNL Team 8500 Volt - HELICS')
        run_test('run8500vvar.sh', 'PNNL Team 8500 VoltVar - HELICS')
        run_test('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt - HELICS')
        os.chdir(tesp_path)
    else:
        p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
        p1.wait()
        run_test('run30.sh', 'PNNL Team 30 - FNCS')
        run_test('runti30.sh', 'PNNL Team ti30 - FNCS')
        run_test('run8500.sh', 'PNNL Team 8500 - FNCS')
        run_test('run8500base.sh', 'PNNL Team 8500 Base - FNCS')
        run_test('run8500tou.sh', 'PNNL Team 8500 TOU - FNCS')
        run_test('run8500volt.sh', 'PNNL Team 8500 Volt - FNCS')
        run_test('run8500vvar.sh', 'PNNL Team 8500 VoltVar - FNCS')
        run_test('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt - FNCS')
        os.chdir(tesp_path)


if __name__ == '__main__':
    init_tests()

    tesp_path = os.path.expandvars('$TESPDIR/')
    os.chdir(tesp_path)
    bTryHELICS = True

    block_test(ieee8500_base_test)
    block_test(ieee8500_precool_test)

    print(report_tests())
