# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases
"""

import os
import subprocess
import sys

import tesp_support.api.tesp_runner as tr

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def ieee8500_glm_test():
    tr.start_test('IEEE8500 GridLAB-D example')
    os.chdir('capabilities/ieee8500')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tr.run_test('runIEEE8500.sh', 'PNNL Team IEEE 8500')
    os.chdir(tesp_path)


def ieee8500_precool_test():
    tr.start_test('ieee8500 PNNLteam examples')
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
    tr.run_test('run8500vwatt.sh', 'PNNL Team 8500 VoltVatt')
    os.chdir(tesp_path)


if __name__ == '__main__':
    b_helics = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "FNCS":
            b_helics = False

    tr.init_tests()
    tesp_path = os.path.expandvars('$TESPDIR/examples')
    os.chdir(tesp_path)

    tr.block_test(ieee8500_glm_test)
    tr.block_test(ieee8500_precool_test)

    print(tr.report_tests())
