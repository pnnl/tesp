# Copyright (C) 2017-2021 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases, excluding the longer FNCS cases
MATPOWER/MOST example must be run after manual installation of Octave and MATPOWER
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

  # loadshed examples
  print('start loadshed examples: ')
  os.chdir ('./examples/loadshed')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh', 'Loadshed FNCS Python')
  RunTestCase ('runjava.sh', 'Loadshed FNCS Java')
  if bTryHELICS:
    RunTestCase ('runhpy.sh', 'Loadshed HELICS ns-3')
    RunTestCase ('runhpy0.sh', 'Loadshed HELICS Python')
    RunTestCase ('runhjava.sh', 'Loadshed HELICS Java')
  os.chdir (basePath)

  # weatherAgent example
  print('start examples weatherAgent: ')
  os.chdir ('./examples/weatherAgent')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh', 'Weather Agent FNCS')
  if bTryHELICS:
    RunTestCase ('runh.sh', 'Weather Agent HELICS')
  os.chdir (basePath)

  # PYPOWER example
  print('start PYPOWER examples: ')
  os.chdir ('./examples/pypower')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('runpp.sh', 'PYPOWER FNCS')
  if bTryHELICS:
    RunTestCase ('runhpp.sh', 'PYPOWER HELICS')
  os.chdir (basePath)

  # EnergyPlus examples
  print('start EnergyPlus examples: ')
  os.chdir ('./examples/energyplus')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh', 'EnergyPlus FNCS IDF')
  RunTestCase ('run2.sh', 'EnergyPlus FNCS EMS')
#  p1 = subprocess.Popen ('./run_baselines.sh', shell=True)
#  p1.wait()
#  p1 = subprocess.Popen ('./make_all_ems.sh', shell=True)
#  p1.wait()
  if bTryHELICS:
    RunTestCase ('runh.sh', 'EnergyPlus HELICS EMS')
#    RunTestCase ('batch_ems_case.sh', 'EnergyPlus Batch EMS')
  os.chdir (basePath)

  # TE30 example
  print('start TE30 examples: ')
  os.chdir ('./examples/te30')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_case.py', shell=True)
  p1.wait()
  RunTestCase ('run.sh', 'TE30 FNCS Market')
  RunTestCase ('run0.sh', 'TE30 FNCS No Market')
  if bTryHELICS:
    RunTestCase ('runh.sh', 'TE30 HELICS Market')
    RunTestCase ('runh0.sh', 'TE30 HELICS No Market')
  os.chdir (basePath)

  # generated Nocomm_Base example
  print('start example generating Nocomm_Base: ')
  os.chdir ('./examples/comm')
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
  os.chdir ('./examples/comm/Eplus_Restaurant')
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
  os.chdir ('./examples/comm')
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

  # generated Eplus_Comm example with three buildings (HELICS only)
  print('start example generating Eplus_Comm: ')
  os.chdir ('./examples/comm')
  p1 = subprocess.Popen (pycall + ' make_comm_eplus.py', shell=True)
  p1.wait()
  os.chdir ('Eplus_Comm')
  st = os.stat ('run.sh')
  os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('run.sh', 'Eplus Comm HELICS')
  os.chdir (basePath)

  print (GetTestCaseReports())

