# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest_long.py
"""Runs the longer set of TESP test cases; 
SGIP1, NIST TE Challenge 2, ERCOT 8-Bus with PSST
"""
import os
import sys
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


def sgip_test():
    start_test('SGIP1 examples')
    os.chdir('analysis/sgip1')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_cases.py', shell=True).wait()
    if b_helics:
        run_test('ruhSGIP1a.sh', 'SGIP1a - HELICS')
        run_test('ruhSGIP1b.sh', 'SGIP1b - HELICS')
        run_test('ruhSGIP1c.sh', 'SGIP1c - HELICS')
        run_test('ruhSGIP1d.sh', 'SGIP1d - HELICS')
        run_test('ruhSGIP1e.sh', 'SGIP1e - HELICS')
        run_test('ruhSGIP1ex.sh', 'SGIP1ex - HELICS')
    else:
        run_test('runSGIP1a.sh', 'SGIP1a - FNCS')
        run_test('runSGIP1b.sh', 'SGIP1b - FNCS')
        run_test('runSGIP1c.sh', 'SGIP1c - FNCS')
        run_test('runSGIP1d.sh', 'SGIP1d - FNCS')
        run_test('runSGIP1e.sh', 'SGIP1e - FNCS')
        run_test('runSGIP1ex.sh', 'SGIP1ex - FNCS')
    os.chdir(tesp_path)


def ieee8500_base_test():
    start_test('IEEE8500 GridLAB-D example')
    os.chdir('capabilities/ieee8500')
    subprocess.Popen('./clean.sh', shell=True).wait()
    print('\n==  Run: IEEE8500 GridLAB-D')
    subprocess.Popen('gridlabd IEEE_8500.glm', shell=True).wait()
    print('\n==  Done IEEE8500 GridLAB-D')
    os.chdir(tesp_path)


def ieee8500_precool_test():
    start_test('IEEE8500 PNNL team examples')
    os.chdir('capabilities/ieee8500/PNNLteam')
    subprocess.Popen('./clean.sh', shell=True).wait()
    if b_helics:
        subprocess.Popen(pycall + ' prepare_cases.py', shell=True).wait()
        run_test('run30.sh', 'PNNL Team 30 - HELICS')
        run_test('runti30.sh', 'PNNL Team ti30 - HELICS')
        run_test('run8500.sh', 'PNNL Team 8500 - HELICS')
        run_test('run8500base.sh', 'PNNL Team 8500 Base - HELICS')
        run_test('run8500tou.sh', 'PNNL Team 8500 TOU - HELICS')
        run_test('run8500volt.sh', 'PNNL Team 8500 Volt - HELICS')
        run_test('run8500vvar.sh', 'PNNL Team 8500 VoltVar - HELICS')
        run_test('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt - HELICS')
    else:
        subprocess.Popen(pycall + ' prepare_cases.py', shell=True).wait()
        run_test('run30.sh', 'PNNL Team 30 - FNCS')
        run_test('runti30.sh', 'PNNL Team ti30 - FNCS')
        run_test('run8500.sh', 'PNNL Team 8500 - FNCS')
        run_test('run8500base.sh', 'PNNL Team 8500 Base - FNCS')
        run_test('run8500tou.sh', 'PNNL Team 8500 TOU - FNCS')
        run_test('run8500volt.sh', 'PNNL Team 8500 Volt - FNCS')
        run_test('run8500vvar.sh', 'PNNL Team 8500 VoltVar - FNCS')
        run_test('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt - FNCS')
    os.chdir(tesp_path)


def ercot_test():
    # ERCOT Case8 example
    start_test('ERCOT Case8 examples')
    os.chdir('capabilities/ercot/dist_system')
    subprocess.Popen(pycall + ' populate_feeders.py', shell=True).wait()
    os.chdir('../case8')
    subprocess.Popen(pycall + ' prepare_case.py', shell=True).wait()
    if b_helics:
        run_test('runh.sh', 'ERCOT 8-bus No Market - HELICS')
        run_test('runmarketh.sh', 'ERCOT 8-bus Market - HELICS')
    else:
        run_test('run.sh', 'ERCOT 8-bus No Market - FNCS')
        run_test('run_market.sh', 'ERCOT 8-bus Market - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    init_tests()

    tesp_path = os.path.expandvars('$TESPDIR/examples')
    os.chdir(tesp_path)
    b_helics = True

    block_test(sgip_test)
    # block_test(ieee8500_base_test)
    # block_test(ieee8500_precool_test)
    # block_test(ercot_test)

    print(report_tests())
