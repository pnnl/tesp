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

"""Runs a test case based on pre-existing shell script file.

Waits for the FNCS broker process to finish before function returns.

"""
def RunTestCase(fname):
	fp = open (fname, 'r')
	potherList=[]
	for ln in fp:
		line = ln.rstrip('\n')
		if ('#!/bin/bash' in line) or (len(line) < 1):
			continue
		if ('javac' in line):
			jc = subprocess.Popen (line, shell=True)
			jc.wait()
		if 'fncs_broker' in line:
			pbroker = subprocess.Popen (line.replace (' &)', ')').replace(' &>', ' >'), shell=True)
			#print("pbroker: ", pbroker)
		else:
			pother = subprocess.Popen (line.replace (' &)', ')').replace(' &>', ' >'), shell=True)
			potherList.append(pother)
			#print("pother: ", pother)
	fp.close()
	#print("waiting for broker")
	pbroker.wait()
	#print("Done waiting for broker")
	for p in potherList:
		#print("waiting for process: ", p)
		p.wait()
		#print("Done waiting for process: ", p)

if __name__ == '__main__':
	basePath = os.getcwd()

	# TE30 example
	print("start TE30 example: ")
	os.chdir ('./examples/te30')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	p1 = subprocess.Popen (pycall + ' prepare_case.py', shell=True)
	p1.wait()
	RunTestCase ('run.sh')
	RunTestCase ('run0.sh')
	os.chdir (basePath)

	# loadshed example, not including HELICS
	print("start loadshed example, not including HELICS: ")
	os.chdir ('./examples/loadshed')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	RunTestCase ('run.sh')
	RunTestCase ('runjava.sh')
	os.chdir (basePath)

	# EnergyPlus example
	print("start EnergyPlus example: ")
	os.chdir ('./examples/energyplus')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	RunTestCase ('run.sh')
	os.chdir (basePath)

	# PYPOWER example
	print("start PYPOWER example: ")
	os.chdir ('./examples/pypower')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	RunTestCase ('runpp.sh')
	os.chdir (basePath)

	# SGIP1a and SGIP1b examples (c, d, e and ex also available)
	print("start examples sgip1: ")
	os.chdir ('./examples/sgip1')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
	p1.wait()
	RunTestCase ('runSGIP1a.sh')
	RunTestCase ('runSGIP1b.sh')
	os.chdir (basePath)

	# weatherAgent example
	print("start examples weatherAgent: ")
	os.chdir ('./examples/weatherAgent')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	RunTestCase ('run.sh')
	os.chdir (basePath)

	# ieee8500 base example
	print("start examples ieee8500: ")
	os.chdir ('./examples/ieee8500')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	p1 = subprocess.Popen ('gridlabd --lock IEEE_8500.glm', shell=True)
	p1.wait()
	os.chdir (basePath)

	# ieee8500 precool example
	print("start examples ieee8500 PNNLteam: ")
	os.chdir ('./examples/ieee8500/PNNLteam')
	p1 = subprocess.Popen ('./clean.sh', shell=True)
	p1.wait()
	p1 = subprocess.Popen (pycall + ' prepare_cases.py', shell=True)
	p1.wait()
	RunTestCase ('run30.sh')
	RunTestCase ('runti30.sh')
	RunTestCase ('run8500.sh')
	os.chdir (basePath)

	# Nocomm_Base example
	print("start examples Nocomm_Base: ")
	os.chdir ('./examples/comm')
	p1 = subprocess.Popen (pycall + ' make_comm_base.py', shell=True)
	p1.wait()
	os.chdir ('Nocomm_Base')
	st = os.stat ('run.sh')
	os.chmod ('run.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
	RunTestCase ('run.sh')
	os.chdir (basePath)

	# CombinedCase example
	print("start examples CombinedCase: ")
	os.chdir ('./examples/comm')
	p1 = subprocess.Popen (pycall + ' combine_feeders.py', shell=True)
	p1.wait()
	shutil.copy ('runcombined.sh', 'CombinedCase')
	os.chdir ('CombinedCase')
	st = os.stat ('runcombined.sh')
	os.chmod ('runcombined.sh', st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
	RunTestCase ('runcombined.sh')
	os.chdir (basePath)

	# ERCOT Case8 example
	print("start examples ERCOT Case8: ")
	os.chdir ('./ercot/dist_system')
	p1 = subprocess.Popen (pycall + ' populate_feeders.py', shell=True)
	p1.wait()
	os.chdir ('../case8')
	p1 = subprocess.Popen (pycall + ' prepare_case.py', shell=True)
	p1.wait()
	RunTestCase ('run.sh')
	os.chdir (basePath)



