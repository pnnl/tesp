# Copyright (C) 2017-2021 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
"""
import sys
import subprocess
import os
import stat
import shutil
from tesp_support.run_test_case import RunTestCase
from tesp_support.run_test_case import InitializeTestCaseReports
from tesp_support.run_test_case import GetTestCaseReports

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

if __name__ == '__main__':
  InitializeTestCaseReports()

  print('start examples sgip1: ')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
  p1.wait()
  RunTestCase ('runSGIP1a.sh', 'SGIP1a (FNCS)')
  RunTestCase ('runSGIP1b.sh', 'SGIP1b (FNCS)')
  RunTestCase ('runSGIP1c.sh', 'SGIP1c (FNCS)')
  RunTestCase ('runSGIP1d.sh', 'SGIP1d (FNCS)')
  RunTestCase ('runSGIP1e.sh', 'SGIP1e (FNCS)')
  RunTestCase ('runSGIP1ex.sh', 'SGIP1ex (FNCS)')

  print (GetTestCaseReports())

