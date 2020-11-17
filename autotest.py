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
from tesp_support.run_test_case import InitializeTestCaseReports
from tesp_support.run_test_case import GetTestCaseReports

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

if __name__ == '__main__':
  InitializeTestCaseReports()

  basePath = os.getcwd()
  bTryHELICS = True  # note: the loadshed and weatherAgent examples finish reliably in HELICS

  # loadshed examples
  print('start loadshed examples: ')
  os.chdir ('./examples/loadshed')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh', 'Loadshed FNCS Python')
  RunTestCase ('runjava.sh', 'Loadshed FNCS Java')
  # hpy requires 'make' and then 'sudo make install' if loadshedCommNetwork program has been updated
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

  # EnergyPlus example
  print('start EnergyPlus examples (excluding the reference building batch runs): ')
  os.chdir ('./examples/energyplus')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh', 'EnergyPlus FNCS IDF')
  RunTestCase ('run2.sh', 'EnergyPlus FNCS EMS')
  if bTryHELICS:
    RunTestCase ('runh.sh', 'EnergyPlus HELICS EMS')
    RunTestCase ('batch_ems_case.sh', 'EnergyPlus Batch EMS')
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

#  print (GetTestCaseReports())
#  quit()

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

  # SGIP1 examples (these take a few hours to run the set)
  print('start examples sgip1: ')
  os.chdir ('./examples/sgip1')
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
  os.chdir (basePath)

  # ieee8500 base example
  print('start examples ieee8500: ')
  os.chdir ('./examples/ieee8500')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen ('gridlabd IEEE_8500.glm', shell=True)
  p1.wait()
  os.chdir (basePath)

  # ieee8500 precool examples (these take a few hours to run the set)
  print('start examples ieee8500 PNNLteam: ')
  os.chdir ('./examples/ieee8500/PNNLteam')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
  p1.wait()
  RunTestCase ('run30.sh', 'PNNL Team 30')
  RunTestCase ('runti30.sh', 'PNNL Team ti30')
  RunTestCase ('run8500.sh', 'PNNL Team 8500')
  RunTestCase ('run8500base.sh', 'PNNL Team 8500 Base')
  RunTestCase ('run8500tou.sh', 'PNNL Team 8500 TOU')
  RunTestCase ('run8500volt.sh', 'PNNL Team 8500 Volt')
  RunTestCase ('run8500vvar.sh', 'PNNL Team 8500 VoltVar')
  RunTestCase ('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt')
  os.chdir (basePath)

  # ERCOT Case8 example
  print('start examples ERCOT Case8: ')
  os.chdir ('./ercot/dist_system')
  p1 = subprocess.Popen (pycall + ' populate_feeders.py', shell=True)
  p1.wait()
  os.chdir ('../case8')
  p1 = subprocess.Popen (pycall + ' prepare_case.py', shell=True)
  p1.wait()
  RunTestCase ('run.sh', 'ERCOT 8-bus No Market')
  RunTestCase ('run_market.sh', 'ERCOT 8-bus Market')
  os.chdir (basePath)

  print (GetTestCaseReports())

