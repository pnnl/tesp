# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
"""
import os
import subprocess
import sys

import tesp_support.api as tesp

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def sgip_test():
    tesp.start_test('SGIP1 examples')
    os.chdir('./examples/analysis/sgip1')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
    p1.wait()
    if bTryHELICS:
        tesp.run_test('ruhSGIP1a.sh', 'SGIP1a - HELICS')
        tesp.run_test('ruhSGIP1b.sh', 'SGIP1b - HELICS')
        tesp.run_test('ruhSGIP1c.sh', 'SGIP1c - HELICS')
        tesp.run_test('ruhSGIP1d.sh', 'SGIP1d - HELICS')
        tesp.run_test('ruhSGIP1e.sh', 'SGIP1e - HELICS')
        tesp.run_test('ruhSGIP1ex.sh', 'SGIP1ex - HELICS')
    else:
        tesp.run_test('runSGIP1a.sh', 'SGIP1a - FNCS')
        tesp.run_test('runSGIP1b.sh', 'SGIP1b - FNCS')
        tesp.run_test('runSGIP1c.sh', 'SGIP1c - FNCS')
        tesp.run_test('runSGIP1d.sh', 'SGIP1d - FNCS')
        tesp.run_test('runSGIP1e.sh', 'SGIP1e - FNCS')
        tesp.run_test('runSGIP1ex.sh', 'SGIP1ex - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    tesp.init_tests()

    tesp_path = os.path.expandvars('$TESPDIR/')
    os.chdir(tesp_path)
    bTryHELICS = True

    tesp.block_test(sgip_test)

    print(tesp.report_tests())
