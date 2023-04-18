# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
"""
import os
import subprocess
import sys

import tesp_support.tesp_runner as tr

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def sgip_test():
    tr.start_test('SGIP1 examples')
    os.chdir('./examples/analysis/sgip1')
    p1 = subprocess.Popen('./clean.sh', shell=True)
    p1.wait()
    p1 = subprocess.Popen(pycall + ' prepare_cases.py', shell=True)
    p1.wait()
    if bTryHELICS:
        tr.run_test('ruhSGIP1a.sh', 'SGIP1a - HELICS')
        tr.run_test('ruhSGIP1b.sh', 'SGIP1b - HELICS')
        tr.run_test('ruhSGIP1c.sh', 'SGIP1c - HELICS')
        tr.run_test('ruhSGIP1d.sh', 'SGIP1d - HELICS')
        tr.run_test('ruhSGIP1e.sh', 'SGIP1e - HELICS')
        tr.run_test('ruhSGIP1ex.sh', 'SGIP1ex - HELICS')
    else:
        tr.run_test('runSGIP1a.sh', 'SGIP1a - FNCS')
        tr.run_test('runSGIP1b.sh', 'SGIP1b - FNCS')
        tr.run_test('runSGIP1c.sh', 'SGIP1c - FNCS')
        tr.run_test('runSGIP1d.sh', 'SGIP1d - FNCS')
        tr.run_test('runSGIP1e.sh', 'SGIP1e - FNCS')
        tr.run_test('runSGIP1ex.sh', 'SGIP1ex - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    tr.init_tests()

    tesp_path = os.path.expandvars('$TESPDIR/')
    os.chdir(tesp_path)
    bTryHELICS = True

    tr.block_test(sgip_test)

    print(tr.report_tests())
