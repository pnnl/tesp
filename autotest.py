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

  # loadshed examples
  print('start loadshed examples: ')
  os.chdir ('./examples/loadshed')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh')
  RunTestCase ('runjava.sh')
  # hpy requires 'make' and then 'sudo make install' if loadshedCommNetwork program has been updated
  RunTestCase ('runhpy.sh')
  RunTestCase ('runhpy0.sh')
  RunTestCase ('runhjava.sh')
  os.chdir (basePath)

  # weatherAgent example
  print('start examples weatherAgent: ')
  os.chdir ('./examples/weatherAgent')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh')
  RunTestCase ('runh.sh')
  os.chdir (basePath)

  # PYPOWER example
  print('start PYPOWER examples: ')
  os.chdir ('./examples/pypower')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('runpp.sh')
  if bTryHELICS:
    RunTestCase ('runhpp.sh')
  os.chdir (basePath)

  # EnergyPlus example
  print('start EnergyPlus examples (excluding the reference building batch runs): ')
  os.chdir ('./examples/energyplus')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh')
  RunTestCase ('run2.sh')
  if bTryHELICS:
    RunTestCase ('runh.sh')
#    RunTestCase ('batch_ems_case.sh')
  os.chdir (basePath)

  # TE30 example
  print('start TE30 examples: ')
  os.chdir ('./examples/te30')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_case.py', shell=True)
  p1.wait()
  RunTestCase ('run.sh')
  RunTestCase ('run0.sh')
  if bTryHELICS:
    RunTestCase ('runh.sh')
    RunTestCase ('runh0.sh')
  os.chdir (basePath)

  quit()

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

  # SGIP1 examples (these take a few hours to run the set)
  print('start examples sgip1: ')
  os.chdir ('./examples/sgip1')
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
  RunTestCase ('run30.sh')
  RunTestCase ('runti30.sh')
  RunTestCase ('run8500.sh')
  RunTestCase ('run8500base.sh')
  RunTestCase ('run8500tou.sh')
  RunTestCase ('run8500volt.sh')
  RunTestCase ('run8500vvar.sh')
  RunTestCase ('run8500vwatt.sh')
  os.chdir (basePath)

  # ERCOT Case8 example
  print('start examples ERCOT Case8: ')
  os.chdir ('./ercot/dist_system')
  p1 = subprocess.Popen (pycall + ' populate_feeders.py', shell=True)
  p1.wait()
  os.chdir ('../case8')
  p1 = subprocess.Popen (pycall + ' prepare_case.py', shell=True)
  p1.wait()
  RunTestCase ('run.sh')
  RunTestCase ('run_market.sh')
  os.chdir (basePath)

