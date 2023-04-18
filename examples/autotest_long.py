# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest_long.py
"""Runs the longer set of tesp test cases;
SGIP1, NIST TE Challenge 2, ERCOT 8-Bus with PSST
"""
import os
import sys
import subprocess

import tesp_support.tesp_runner as tr

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def sgip_test():
    tr.start_test('SGIP1 examples')
    os.chdir('analysis/sgip1')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_cases.py', shell=True).wait()
    if b_helics:
        tr.run_test('ruhSGIP1a.sh', 'SGIP1a - HELICS')
        tr.run_test('ruhSGIP1b.sh', 'SGIP1b - HELICS')
        tr.run_test('ruhSGIP1c.sh', 'SGIP1c - HELICS')
        tr.run_test('ruhSGIP1d.sh', 'SGIP1d - HELICS')
        tr.run_test('ruhSGIP1e.sh', 'SGIP1e - HELICS')
        tr.run_test('ruhSGIP1ex.sh', 'SGIP1ex - HELICS')
    else:
        tr.run_test('runSGIP1a.sh', 'SGIP1a - FNCS')
        tr.run_test('runSGIP1b.sh', 'SGIP1b - FNCS')
        tr.run_test('runSGIP1c.sh', 'SGIP1c - FNCS')
        tr.run_test('runSGIP1d.sh', 'SGIP1d - FNCS')
        tr.run_test('runSGIP1e.sh', 'SGIP1e - FNCS')
        tr.run_test('runSGIP1ex.sh', 'SGIP1ex - FNCS')
    os.chdir(tesp_path)


def ieee8500_base_test():
    tr.start_test('IEEE8500 GridLAB-D example')
    os.chdir('capabilities/ieee8500')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tr.run_test('runIEEE8500.sh', 'PNNL Team IEEE8500')
    os.chdir(tesp_path)


def ieee8500_precool_test():
    tr.start_test('IEEE8500 PNNL team examples')
    os.chdir('capabilities/ieee8500/PNNLteam')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_cases.py', shell=True).wait()
    if b_helics:
        tr.run_test('ruh30.sh', 'PNNL Team 30 - HELICS')
        tr.run_test('ruhti30.sh', 'PNNL Team ti30 - HELICS')
        tr.run_test('ruh8500.sh', 'PNNL Team 8500 - HELICS')
        tr.run_test('ruh8500tou.sh', 'PNNL Team 8500 TOU - HELICS')
        tr.run_test('ruh8500volt.sh', 'PNNL Team 8500 Volt - HELICS')
    else:
        tr.run_test('run30.sh', 'PNNL Team 30 - FNCS')
        tr.run_test('runti30.sh', 'PNNL Team ti30 - FNCS')
        tr.run_test('run8500.sh', 'PNNL Team 8500 - FNCS')
        tr.run_test('run8500tou.sh', 'PNNL Team 8500 TOU - FNCS')
        tr.run_test('run8500volt.sh', 'PNNL Team 8500 Volt - FNCS')
    tr.run_test('run8500base.sh', 'PNNL Team 8500 Base')
    tr.run_test('run8500vvar.sh', 'PNNL Team 8500 VoltVar')
    tr.run_test('run8500vwatt.sh', 'PNNL Team 8500 VoltWatt')
    os.chdir(tesp_path)


def ercot_test():
    # ERCOT Case8 example
    tr.start_test('ERCOT Case8 examples')
    os.chdir('capabilities/ercot/dist_system')
    subprocess.Popen(pycall + ' populate_feeders.py', shell=True).wait()
    os.chdir('../case8')
    subprocess.Popen(pycall + ' prepare_case.py', shell=True).wait()
    if b_helics:
        tr.run_test('runh.sh', 'ERCOT 8-bus No Market - HELICS')
        tr.run_test('runmarketh.sh', 'ERCOT 8-bus Market - HELICS')
    else:
        tr.run_test('run.sh', 'ERCOT 8-bus No Market - FNCS')
        tr.run_test('run_market.sh', 'ERCOT 8-bus Market - FNCS')
    os.chdir(tesp_path)


def dso_stub_test():
    tr.start_test('DSO Stub example')
    if b_helics:
        os.chdir('capabilities/dsostub')
    else:
        os.chdir('capabilities/dsostubf')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen('./runstub.sh Test', shell=True).wait()
    os.chdir('./Test')
    if b_helics:
        tr.run_test('run.sh', 'DSO Stub - HELICS')
    else:
        tr.run_test('run.sh', 'DSO Stub - FNCS')
    os.chdir(tesp_path)


if __name__ == '__main__':
    b_helics = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "FNCS":
            b_helics = False

    tr.init_tests()
    tesp_path = os.path.expandvars('$TESPDIR/examples')
    os.chdir(tesp_path)

    tr.block_test(sgip_test)
    tr.block_test(ieee8500_base_test)
    tr.block_test(ieee8500_precool_test)
    # tr.block_test(ercot_test)
    # tr.block_test(dso_stub_test)

    print(tr.report_tests())
