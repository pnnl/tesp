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


def sgip_test():
    start_test('SGIP1 examples')
    os.chdir('./examples/analysis/sgip1')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
    p1.wait()
    if bTryHELICS:
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


if __name__ == '__main__':
    init_tests()

    tesp_path = os.path.expandvars('$TESPDIR/')
    os.chdir(tesp_path)
    bTryHELICS = True

    block_test(sgip_test)

    print(report_tests())
