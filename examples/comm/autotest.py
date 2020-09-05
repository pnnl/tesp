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
  basePath = os.getcwd()
  bTryHELICS = True  # note: the loadshed and weatherAgent examples finish reliably in HELICS

  # generated Nocomm_Base example
  print('start example generating Nocomm_Base: ')
  os.chdir ('./examples/comm')
  p1 = subprocess.Popen (pycall + ' make_comm_base.py', shell=True)
  p1.wait()
  os.chdir ('Nocomm_Base')
  st = os.stat ('run.sh')
  os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('run.sh')
  if bTryHELICS:
    st = os.stat ('runh.sh')
    os.chmod ('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTestCase ('runh.sh')
  os.chdir (basePath)

  # generated Eplus_Restaurant example
  print('start example of Eplus_Restaurant, generated with Nocomm_Base: ')
  os.chdir ('./examples/comm/Eplus_Restaurant')
  st = os.stat ('run.sh')
  os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('run.sh')
  if bTryHELICS:
    st = os.stat ('runh.sh')
    os.chmod ('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTestCase ('runh.sh')
  os.chdir (basePath)

  # generated CombinedCase example
  print('start example generating CombinedCase: ')
  os.chdir ('./examples/comm')
  p1 = subprocess.Popen (pycall + ' combine_feeders.py', shell=True)
  p1.wait()
  shutil.copy ('runcombined.sh', 'CombinedCase')
  shutil.copy ('runcombinedh.sh', 'CombinedCase')
  os.chdir ('CombinedCase')
  st = os.stat ('runcombined.sh')
  os.chmod ('runcombined.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('runcombined.sh')
  if bTryHELICS:
    st = os.stat ('runcombinedh.sh')
    os.chmod ('runcombinedh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTestCase ('runcombinedh.sh')
  os.chdir (basePath)

