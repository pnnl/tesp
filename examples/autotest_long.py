# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest_long.py
"""Runs the longer set of TESP test cases; 
SGIP1, NIST TE Challenge 2, ERCOT 8-Bus with PSST
"""
import os
import sys
import subprocess

import tesp_support.api as tesp

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def sgip_test():
    tesp.start_test('SGIP1 examples')
    os.chdir('analysis/sgip1')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_cases.py', shell=True).wait()
    if b_helics:
        tesp.run_test('ruhSGIP1a.sh', 'SGIP1a - HELICS')
        tesp.run_test('ruhSGIP1b.sh', 'SGIP1b - HELICS')
        tesp.run_test('ruhSGIP1c.sh', 'SGIP1c - HELICS')
        tesp.run_test('ruhSGIP1d.sh', 'SGIP1d - HELICS')
        tesp.run_test('ruhSGIP1e.sh', 'SGIP1e - HELICS')
        tesp.run_test('ruhSGIP1ex.sh', 'SGIP1ex - HELICS')
    else:
        tesp.run_test('runSGIP1a.sh', 'SGIP1a - FNCS')
        tesp.run_test('runSGIP1b.sh', 'SGIP1b - FNCS')
        tesp.run_test('runSGIP1c.sh', 'SGIP1c - FNCS')
        tesp.run_test('runSGIP1d.sh', 'SGIP1d - FNCS')
        tesp.run_test('runSGIP1e.sh', 'SGIP1e - FNCS')
        tesp.run_test('runSGIP1ex.sh', 'SGIP1ex - FNCS')
    os.chdir(tesp_path)


def ieee8500_base_test():
    tesp.start_test('IEEE8500 GridLAB-D example')
    os.chdir('capabilities/ieee8500')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tesp.run_test('runIEEE8500.sh', 'PNNL Team IEEE8500')
    os.chdir(tesp_path)


def ieee8500_precool_test():
    tesp.start_test('IEEE8500 PNNL team examples')
    os.chdir('capabilities/ieee8500/PNNLteam')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_cases.py', shell=True).wait()
    if b_helics:
        tesp.run_test('ruh30.sh', 'PNNL Team 30 - HELICS')
        tesp.run_test('ruhti30.sh', 'PNNL Team ti30 - HELICS')
        tesp.run_test('ruh8500.sh', 'PNNL Team 8500 - HELICS')
        tesp.run_test('ruh8500tou.sh', 'PNNL Team 8500 TOU - HELICS')
        tesp.run_test('ruh8500volt.sh', 'PNNL Team 8500 Volt - HELICS')
    else:
        tesp.run_test('run30.sh', 'PNNL Team 30 - FNCS')
        tesp.run_test('runti30.sh', 'PNNL Team ti30 - FNCS')
        tesp.run_test('run8500.sh', 'PNNL Team 8500 - FNCS')
        tesp.run_test('run8500tou.sh', 'PNNL Team 8500 TOU - FNCS')
        tesp.run_test('run8500volt.sh', 'PNNL Team 8500 Volt - FNCS')
    tesp.run_test('run8500base.sh', 'PNNL Team 8500 Base')
    tesp.run_test('run8500vvar.sh', 'PNNL Team 8500 VoltVar')
    tesp.run_test('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt')
    os.chdir(tesp_path)


def ercot_test():
    # ERCOT Case8 example
    tesp.start_test('ERCOT Case8 examples')
    os.chdir('capabilities/ercot/dist_system')
    subprocess.Popen(pycall + ' populate_feeders.py', shell=True).wait()
    os.chdir('../case8')
    subprocess.Popen(pycall + ' prepare_case.py', shell=True).wait()
    if b_helics:
        tesp.run_test('runh.sh', 'ERCOT 8-bus No Market - HELICS')
        tesp.run_test('runmarketh.sh', 'ERCOT 8-bus Market - HELICS')
    else:
        tesp.run_test('run.sh', 'ERCOT 8-bus No Market - FNCS')
        tesp.run_test('run_market.sh', 'ERCOT 8-bus Market - FNCS')
    os.chdir(tesp_path)


def dso_stub_test():
    tesp.start_test('DSO Stub example')
    if b_helics:
        os.chdir('capabilities/dsostub')
    else:
        os.chdir('capabilities/dsostubf')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen('./runstub.sh Test', shell=True).wait()
    os.chdir('./Test')
    if b_helics:
        tesp.run_test('run.sh', 'DSO Stub - HELICS')
    else:
        tesp.run_test('run.sh', 'DSO Stub - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    b_helics = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "FNCS":
            b_helics = False

    tesp.init_tests()
    tesp_path = os.path.expandvars('$TESPDIR/examples')
    os.chdir(tesp_path)

    tesp.block_test(sgip_test)
    tesp.block_test(ieee8500_base_test)
    tesp.block_test(ieee8500_precool_test)
    # tesp.block_test(ercot_test)
    tesp.block_test(dso_stub_test)

    print(tesp.report_tests())
