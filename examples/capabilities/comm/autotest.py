# Copyright (C) 2017-2022 Battelle Memorial Institute
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

  basePath = os.getcwd()
  bTryHELICS = True

  # generated Nocomm_Base example
  print('start example generating Nocomm_Base: ')
  p1 = subprocess.Popen (pycall + ' make_comm_base.py', shell=True)
  p1.wait()
  os.chdir ('Nocomm_Base')
  st = os.stat ('run.sh')
  os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('run.sh', 'Nocomm Base FNCS')
  if bTryHELICS:
    st = os.stat ('runh.sh')
    os.chmod ('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTestCase ('runh.sh', 'Nocomm Base HELICS')
  os.chdir (basePath)

  # generated Eplus_Restaurant example
  print('start example of Eplus_Restaurant, generated with Nocomm_Base: ')
  os.chdir ('Eplus_Restaurant')
  st = os.stat ('run.sh')
  os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('run.sh', 'Eplus Restaurant FNCS')
  if bTryHELICS:
    st = os.stat ('runh.sh')
    os.chmod ('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTestCase ('runh.sh', 'Eplus Restaurant HELICS')
  os.chdir (basePath)

  # generated CombinedCase example
  print('start example generating CombinedCase: ')
  p1 = subprocess.Popen (pycall + ' combine_feeders.py', shell=True)
  p1.wait()
  shutil.copy ('runcombined.sh', 'CombinedCase')
  shutil.copy ('runcombinedh.sh', 'CombinedCase')
  os.chdir ('CombinedCase')
  st = os.stat ('runcombined.sh')
  os.chmod ('runcombined.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('runcombined.sh', '4 Feeders FNCS')
  if bTryHELICS:
    st = os.stat ('runcombinedh.sh')
    os.chmod ('runcombinedh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    RunTestCase ('runcombinedh.sh', '4 Feeders HELICS')
  os.chdir (basePath)

  print (GetTestCaseReports())
