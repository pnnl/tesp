# Copyright (C) 2017-2020 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
"""
import sys
import subprocess
import os
import stat
import shutil
from tesp_support.run_test_case import RunTestCase

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

if __name__ == '__main__':
  print('start examples sgip1: ')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
  p1.wait()
  RunTestCase ('runSGIP1a.sh')
  RunTestCase ('runSGIP1b.sh')
  RunTestCase ('runSGIP1c.sh')
  RunTestCase ('runSGIP1d.sh')
  RunTestCase ('runSGIP1e.sh')
  RunTestCase ('runSGIP1ex.sh')


