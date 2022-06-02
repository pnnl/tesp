# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
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


if __name__ == '__main__':
    InitializeTestReports()

    tesp_path = os.path.expandvars('$TESPDIR/')
    os.chdir(tesp_path)
    bTryHELICS = True

    block(sgip_test)

    print(GetTestReports())
