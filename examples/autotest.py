# Copyright (c) 2017-2023 Battelle Memorial Institute
# file: autotest.py
"""Runs the set of TESP test cases, excluding the longer FNCS cases
MATPOWER/MOST example must be run after manual installation of Octave and MATPOWER
"""

import os
import shutil
import subprocess
import sys

import tesp_support.api.test_runner as tr

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def gld_player_test():
    tr.start_test('GridLAB-D Player/Recorder example')
    os.chdir('capabilities/gld_player_recorder')
    tr.run_test('run.sh', 'GridLAB-D Player/Recorder')
    os.chdir(tesp_path)


def loadshed_test():
    tr.start_test('Loadshed examples')
    if b_helics:
        os.chdir('capabilities/loadshed')
        subprocess.Popen('./clean.sh', shell=True).wait()
        subprocess.Popen('make clean > make.log', shell=True).wait()
        subprocess.Popen('make >> make.log', shell=True).wait()
        # tr.run_test('runhpy.sh', 'Loadshed - HELICS ns-3')  # works on linux
        tr.run_test('runhpy0.sh', 'Loadshed - HELICS Python')
        tr.run_test('runhjava.sh', 'Loadshed - HELICS Java')
    else:
        os.chdir('capabilities/loadshedf')
        subprocess.Popen('./clean.sh', shell=True).wait()
        tr.run_test('run.sh', 'Loadshed - FNCS Python')
        tr.run_test('runjava.sh', 'Loadshed - FNCS Java')
    os.chdir(tesp_path)


def loadshed_cli_test():
    if b_helics:
        tr.start_test('Loadshed examples for HELICS CLI')
        os.chdir('capabilities/loadshed-HELICS3-EPlus')
        subprocess.Popen('./clean.sh', shell=True).wait()
        subprocess.Popen('make clean > make.log', shell=True).wait()
        subprocess.Popen('make >> make.log', shell=True).wait()
        tr.run_test('run.sh', 'Loadshed - HELICS/EPlus')
        # tr.run_test('run_ns3.sh', 'Loadshed - HELICS/EPLUS/NS3')  # works in linux
        os.chdir(tesp_path)


def loadshed_proto_test():
    if b_helics:
        tr.start_test('Loadshed Prototypical Communication')
        os.chdir('capabilities/loadshed-prototypical-communication')
        subprocess.Popen('./clean.sh', shell=True).wait()
        os.chdir('R1-12.47-1-communication')
        subprocess.Popen('make clean > make.log', shell=True).wait()
        subprocess.Popen('make >> make.log', shell=True).wait()
        os.chdir('../R1-12.47-1')
        tr.exec_test('gridlabd R1-12.47-1_processed.glm > gridlabd.log', 'Establishing baseline results')
        os.chdir('..')
        tr.run_test('run.sh', 'Load shedding w/o comm network')
        # tr.run_test('run_ns3.sh', 'Load shedding over comm network')  # works in linux
        os.chdir(tesp_path)


def houses_test():
    tr.start_test('Houses example')
    os.chdir('capabilities/houses')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tr.run_test('run.sh', 'Houses')
    os.chdir(tesp_path)


def pypower_test():
    tr.start_test('PYPOWER example')
    os.chdir('capabilities/pypower')
    subprocess.Popen('./clean.sh', shell=True).wait()
    if b_helics:
        tr.run_test('runhpp.sh', 'PYPOWER - HELICS')
    else:
        tr.run_test('runpp.sh', 'PYPOWER - FNCS')
    os.chdir(tesp_path)


def energyplus_test():
    tr.start_test('EnergyPlus EMS/IDF examples')
    os.chdir('capabilities/energyplus')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tr.exec_test('./run_baselines.sh > baselines.log', 'Houston,TX Baselines build types')
    if b_helics:
        tr.exec_test('./make_all_ems.sh True > all_ems.log', 'Generated EMS/IDF files - HELICS')
        tr.run_test('runh.sh', 'EnergyPlus EMS - HELICS')
    #    tr.run_test('batch_ems_case.sh', 'EnergyPlus Batch EMS')
    else:
        tr.exec_test('./make_all_ems.sh False > all_ems_f.log', 'Generated EMS/IDF files - FNCS')
        tr.run_test('run.sh', 'EnergyPlus IDF - FNCS')
        tr.run_test('run2.sh', 'EnergyPlus EMS - FNCS')
    os.chdir(tesp_path)


def weather_agent_test():
    tr.start_test('Weather Agent example')
    os.chdir('capabilities/weatherAgent')
    subprocess.Popen('./clean.sh', shell=True).wait()
    if b_helics:
        tr.run_test('runh.sh', 'Weather Agent - HELICS')
    else:
        tr.run_test('run.sh', 'Weather Agent - FNCS')
    os.chdir(tesp_path)


def te30_test():
    tr.start_test('TE30 examples')
    os.chdir('capabilities/te30')
    subprocess.Popen('./clean.sh', shell=True).wait()
    subprocess.Popen(pycall + ' prepare_case.py', shell=True).wait()
    if b_helics:
        tr.run_test('runh.sh', 'TE30 - HELICS Market')
        tr.run_test('runh0.sh', 'TE30 - HELICS No Market')
    else:
        tr.run_test('run.sh', 'TE30 - FNCS Market')
        tr.run_test('run0.sh', 'TE30 - FNCS No Market')
    os.chdir(tesp_path)


def make_comm_base_test():
    tr.start_test('Communication Network examples')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' make_comm_base.py', shell=True).wait()

    # generated Nocomm_Base example
    os.chdir('Nocomm_Base')
    if b_helics:
        tr.run_test('runh.sh', 'No Comm Base - HELICS')
    else:
        tr.run_test('run.sh', 'No Comm Base - FNCS')

    # generated Eplus_Restaurant example
    os.chdir(tesp_path + '/capabilities/comm/Eplus_Restaurant')
    if b_helics:
        tr.run_test('runh.sh', 'Eplus Restaurant - HELICS')
    else:
        tr.run_test('run.sh', 'Eplus Restaurant - FNCS')

    # generated SGIP1c example
    os.chdir(tesp_path + '/capabilities/comm/SGIP1c')
    if b_helics:
        tr.run_test('runh.sh', 'SGIP1c - HELICS')
    else:
        tr.run_test('run.sh', 'SGIP1c - FNCS')
    os.chdir(tesp_path)


def make_comm_eplus_test():
    if b_helics:
        tr.start_test('Eplus with Communication Network example')
        os.chdir('capabilities/comm')
        subprocess.Popen(pycall + ' make_comm_eplus.py', shell=True).wait()
        os.chdir('Eplus_Comm')
        tr.run_test('run.sh', 'Eplus w/Comm - HELICS')
        os.chdir(tesp_path)


def combine_feeders_test():
    tr.start_test('Communication Network Combined Case example')
    os.chdir('capabilities/comm')
    subprocess.Popen(pycall + ' combine_feeders.py', shell=True).wait()
    shutil.copy('runcombined.sh', 'CombinedCase')
    shutil.copy('runcombinedh.sh', 'CombinedCase')
    os.chdir('CombinedCase')
    if b_helics:
        tr.run_test('runcombinedh.sh', '4 Feeders - HELICS')
    else:
        tr.run_test('runcombined.sh', '4 Feeders - FNCS')
    os.chdir(tesp_path)


def gld_modifier_test():
    tr.start_test('GLM Modifier example')
    os.chdir('capabilities/gld_modifier')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tr.run_test('run.sh', 'GLM Modifier')
    os.chdir(tesp_path)


def feeder_generator_test():
    tr.start_test('Feeder Generator example')
    os.chdir('capabilities/feeder-generator')
    subprocess.Popen('./clean.sh', shell=True).wait()
    tr.run_test('run.sh', 'Feeder generator')
    os.chdir(tesp_path)


def feeder_generator_comp_test():
    os.chdir(tesp_path)
    from tesp_support.api.gld_feeder_generator import _test2
    _test2()


if __name__ == '__main__':
    b_helics = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "FNCS":
            b_helics = False

    # tr.run_test = tr.run_docker_test

    tr.init_tests()
    tesp_path = os.path.expandvars('$TESPDIR/examples')
    os.chdir(tesp_path)

    tr.block_test(gld_player_test)
    tr.block_test(loadshed_test)
    tr.block_test(loadshed_cli_test)
    tr.block_test(loadshed_proto_test)
    tr.block_test(pypower_test)
    tr.block_test(energyplus_test)
    tr.block_test(weather_agent_test)
    tr.block_test(houses_test)
    tr.block_test(gld_modifier_test)
    tr.block_test(feeder_generator_test)
    # tr.block_test(feeder_generator_comp_test)
    tr.block_test(te30_test)
    tr.block_test(combine_feeders_test)
    tr.block_test(make_comm_eplus_test)
    tr.block_test(make_comm_base_test)  # there are 3 different runs, takes ~5min each

    print(tr.report_tests())
