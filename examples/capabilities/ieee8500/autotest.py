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

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

if __name__ == '__main__':
  basePath = os.getcwd()

  # ieee8500 base example
  print('start examples ieee8500: ')
#  os.chdir ('./examples/ieee8500')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen ('gridlabd IEEE_8500.glm', shell=True)
  p1.wait()
  os.chdir (basePath)

  # ieee8500 precool example
  print('start examples ieee8500 PNNLteam: ')
  os.chdir ('./PNNLteam')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
  p1.wait()
  RunTestCase ('run30.sh')
  RunTestCase ('runti30.sh')
  RunTestCase ('run8500.sh')
  RunTestCase ('run8500base.sh')
  RunTestCase ('run8500tou.sh')
  RunTestCase ('run8500volt.sh')
  RunTestCase ('run8500vvar.sh')
  RunTestCase ('run8500vwatt.sh')
  os.chdir (basePath)

