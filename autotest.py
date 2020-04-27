# Copyright (C) 2017-2020 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
"""
import sys
import subprocess
import os
import stat
import shutil

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

def ProcessLine(line, local_vars):
#  print ('@@@@ input line to execute:', line)
  foreground = line.replace (' &)', ')').replace(' &>', ' >')
  exports = ''
  for var in local_vars:
    exports = exports + 'export ' + var['key'] + '=' + var['val'] + ' && '
#  print (' line transformed to:', exports + foreground)
  return exports + foreground

"""Runs a test case based on pre-existing shell script file.

Waits for the FNCS or HELICS broker process to finish before function returns.

"""
def RunTestCase(fname):
  local_vars = []
  fp = open (fname, 'r')
  potherList=[]
  # if a HELICS case includes EnergyPlus, both brokers will instantiate
  pFNCSbroker = None
  pHELICSbroker = None
  for ln in fp:
    line = ln.rstrip('\n')
    if ('#!/bin/bash' in line) or (len(line) < 1):
      continue
    if line[0] == '#':
      continue
    if line.startswith('declare'):
      toks = line.split()
      keyval = toks[2].split('=')
      local_vars.append({'key':keyval[0],'val':keyval[1]})
    elif line.startswith('javac') or line.startswith('python') or line.startswith('gridlabd') or line.startswith('TMY3toTMY2_ansi'):
      jc = subprocess.Popen (ProcessLine (line, local_vars), shell=True)
      jc.wait()
    elif 'fncs_broker' in line:
      pFNCSbroker = subprocess.Popen (ProcessLine (line, local_vars), shell=True)
    elif 'helics_broker' in line:
      pHELICSbroker = subprocess.Popen (ProcessLine (line, local_vars), shell=True)
    else:
      pother = subprocess.Popen (ProcessLine (line, local_vars), shell=True)
      potherList.append(pother)
  fp.close()
  if pFNCSbroker is not None:
    pFNCSbroker.wait()
    print ('====   Fncs Broker Exit in', os.getcwd())
  if pHELICSbroker is not None:
    pHELICSbroker.wait()
    print ('==== Helics Broker Exit in', os.getcwd())
  for p in potherList:
    p.wait()
  print   ('================== Exit in', os.getcwd())

if __name__ == '__main__':
  basePath = os.getcwd()

  # loadshed examples
  print('start loadshed examples: ')
  os.chdir ('./examples/loadshed')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh')
  RunTestCase ('runjava.sh')
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
  RunTestCase ('runhpp.sh')
  os.chdir (basePath)

  # EnergyPlus example
  print('start EnergyPlus examples (excluding the reference building batch runs): ')
  os.chdir ('./examples/energyplus')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  RunTestCase ('run.sh')
  RunTestCase ('run2.sh')
  RunTestCase ('runh.sh')
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
  RunTestCase ('runh.sh')
  RunTestCase ('runh0.sh')
  os.chdir (basePath)

#  quit()

  # SGIP1 examples (a, b, c, d, e and ex also available)
  print('start examples sgip1: ')
  os.chdir ('./examples/sgip1')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
  p1.wait()
#  RunTestCase ('runSGIP1a.sh')
  RunTestCase ('runSGIP1b.sh')
#  RunTestCase ('runSGIP1c.sh')
#  RunTestCase ('runSGIP1d.sh')
#  RunTestCase ('runSGIP1e.sh')
#  RunTestCase ('runSGIP1ex.sh')
  os.chdir (basePath)

  # generated Nocomm_Base example
  print('start example generating Nocomm_Base: ')
  os.chdir ('./examples/comm')
  p1 = subprocess.Popen (pycall + ' make_comm_base.py', shell=True)
  p1.wait()
  os.chdir ('Nocomm_Base')
  st = os.stat ('run.sh')
  os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('run.sh')
  st = os.stat ('runh.sh')
  os.chmod ('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('runh.sh')
  os.chdir (basePath)

  # generated Eplus_Restaurant example
  print('start example generating Eplus_Restaurant: ')
  os.chdir ('./examples/comm')
  p1 = subprocess.Popen (pycall + ' make_comm_base.py', shell=True)
  p1.wait()
  os.chdir ('Eplus_Restaurant')
  st = os.stat ('run.sh')
  os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('run.sh')
  st = os.stat ('runh.sh')
  os.chmod ('runh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('runh.sh')
  os.chdir (basePath)

  # generated ombinedCase example
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
  st = os.stat ('runcombinedh.sh')
  os.chmod ('runcombinedh.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  RunTestCase ('runcombinedh.sh')
  os.chdir (basePath)

  # ieee8500 base example
  print('start examples ieee8500: ')
  os.chdir ('./examples/ieee8500')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen ('gridlabd IEEE_8500.glm', shell=True)
  p1.wait()
  os.chdir (basePath)

  # ieee8500 precool example
  print('start examples ieee8500 PNNLteam: ')
  os.chdir ('./examples/ieee8500/PNNLteam')
  p1 = subprocess.Popen ('./clean.sh', shell=True)
  p1.wait()
  p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
  p1.wait()
  RunTestCase ('run30.sh')
  RunTestCase ('runti30.sh')
#  RunTestCase ('run8500.sh')
#  RunTestCase ('run8500base.sh')
#  RunTestCase ('run8500tou.sh')
#  RunTestCase ('run8500volt.sh')
#  RunTestCase ('run8500vvar.sh')
#  RunTestCase ('run8500vwatt.sh')
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



