# Copyright (C) 2017-2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: test_runner.py
"""
Auto test runner for TESP run* cases
Runs a test case based on pre-existing shell script file.

If FNCS or HELICS broker exist the test waits for
the broker process to finish before function returns.

This code has limited functionality as the 'run*' scripts
for the examples are written in a very specified way.
"""

import os
import time
import subprocess

reports = []
b_reporting = False


def init_tests():
    global reports, b_reporting

    reports = []
    b_reporting = True


def block_test(call):
    print('\n<!--', flush=True)
    call()
    print('--!>', flush=True)


def start_test(case_name=None):
    print('==  Prepare: ', case_name, flush=True)


def process_line(line, local_vars):
    # print('@@@@ input line to execute:', line)
    exports = ''
    for var in local_vars:
        exports = exports + 'export ' + var['key'] + '=' + var['val'] + ' && '
    command = line.replace(' &)', ')').replace(' &>', ' >')
    # print(' line transformed to:', exports + command)
    return exports + command


def docker_line(line, local_vars):
    # print('@@@@ input line to execute:', line)
    exports = ''
    for var in local_vars:
        exports = exports + '      ' + var['key'] + ': "' + var['val'] + '"\n'
    command = line.replace(' &)', '').replace(' &>', ' >').replace('(ex', 'ex').replace('"', '\\"')
    # print('docker line transformed to:', exports + command)
    return exports, command


def exec_test(file_name, case_name=None):
    t_start = time.time()
    print('\n==  Run: ', case_name, flush=True)
    subprocess.Popen(file_name, shell=True).wait()
    t_end = time.time()
    if b_reporting:
        t_elapsed = t_end - t_start
        if case_name is None:
            case_name = file_name
        reports.append({'case': case_name, 'elapsed': t_elapsed})
        print('====  Time elapsed: {:12.6f}'.format(t_elapsed), flush=True)
    print('==  Done: ', case_name, flush=True)


def run_test(file_name, case_name=None):
    t_start = time.time()
    local_vars = []
    fp = open(file_name, 'r')
    p_list = []
    p_FNCS_broker = None
    p_HELICS_broker = None
    print('\n==  Run: ', case_name, flush=True)
    for ln in fp:
        line = ln.rstrip('\n')
        if ('#!/bin/bash' in line) or (len(line) < 1):
            continue
        if line[0] == '#':
            continue
        if line.startswith('declare'):
            tokens = line.split()
            keyval = tokens[2].split('=')
            local_vars.append({'key': keyval[0], 'val': keyval[1]})
        elif line.startswith('javac') or line.startswith('python') or \
                line.startswith('make') or line.startswith('chmod') or \
                line.startswith('gridlabd') or line.startswith('TMY3toTMY2_ansi'):
            jc = subprocess.Popen(process_line(line, local_vars), shell=True)
            jc.wait()
        elif 'fncs_broker' in line:
            print('====  Fncs Broker Start in\n        ' + os.getcwd(), flush=True)
            p_FNCS_broker = subprocess.Popen(process_line(line, local_vars), shell=True)
        elif 'helics_broker' in line:
            print('====  Helics Broker Start in\n        ' + os.getcwd(), flush=True)
            p_HELICS_broker = subprocess.Popen(process_line(line, local_vars), shell=True)
        else:
            pother = subprocess.Popen(process_line(line, local_vars), shell=True)
            p_list.append(pother)
    fp.close()
    if p_FNCS_broker is not None:
        p_FNCS_broker.wait()
        print('====  Fncs Broker Exit in\n        ' + os.getcwd(), flush=True)
    if p_HELICS_broker is not None:
        p_HELICS_broker.wait()
        print('====  Helics Broker Exit in\n        ' + os.getcwd(), flush=True)
    for p in p_list:
        p.wait()

    t_end = time.time()
    if b_reporting:
        t_elapsed = t_end - t_start
        if case_name is None:
            case_name = file_name
        reports.append({'case': case_name, 'elapsed': t_elapsed})
        print('====  Time elapsed: {:12.6f}'.format(t_elapsed), flush=True)
    print('==  Done: ', case_name, flush=True)


def services(name, image, env, cnt, outfile, depends=None):
    outfile.write("  " + name + ":\n")
    outfile.write("    image: \"" + image + "\"\n")
    if env[0] != '':
        outfile.write("    environment:\n")
        outfile.write(env[0])
    outfile.write("    working_dir: /home/worker/case\n")
    outfile.write("    volumes:\n")
    outfile.write("      - .:/home/worker/case\n")
    outfile.write("      - ../../../data:/home/worker/tesp/data\n")
    if depends is not None:
        outfile.write("    depends_on:\n")
        outfile.write("      - " + depends + "\n")
    outfile.write("    networks:\n")
    outfile.write("      cu_net:\n")
    outfile.write("        ipv4_address: 10.5.0." + str(cnt) + "\n")
    outfile.write("    command: sh -c \"" + env[1] + "\"\n")


"""
name = "fncs"
image = "tesp-fncs:latest"
f = ["fncs "]

name = "helics",
image = "tesp-helics:latest"
f = ["helics"]
line = line.replace(' -f', ' --ipv4 -f')

name = "tespapi_" + str(cnt)
image = "tesp-tespapi:latest"
f = [" python", " java"]

name = "gridlabd_" + str(cnt)
image = "tesp-gridlabd:latest"
f: ["gridlabd "]

name = "eplus_" + str(cnt)
image = "tesp-eplus:latest"
f = ["energyplus ", "eplus_agent"]

name = "eplus_" + str(cnt)
image = "tesp-ns3:latest"
f = ["energyplus ", "eplus_agent"]

name = "helics_" + str(cnt)
image = "tesp-helics:latest"
f = ["helics_recorder", "helics_player"]

# The master build, heavyweight docker
name = "build_" + str(cnt)
image = "tesp-build:latest"
f = []
"""


def run_docker_test(file_name, case_name=None):
    t_start = time.time()
    cnt = 1
    local_vars = []
    fp = open(file_name, 'r')
    op = open(file_name.replace("sh", "yaml"), 'w')
    op.write('version: "3.8"\n')
    op.write('services:\n')
    p_broker = None
    print('\n==  Run: ', case_name, flush=True)
    for ln in fp:
        line = ln.rstrip('\n')
        if ('#!/bin/bash' in line) or (len(line) < 1):
            continue
        if line[0] == '#':
            continue
        if line.startswith('declare'):
            tokens = line.split()
            keyval = tokens[2].split('=')
            local_vars.append({'key': keyval[0], 'val': keyval[1]})
        elif line.startswith('javac') or line.startswith('python') or \
                line.startswith('make') or line.startswith('chmod') or \
                line.startswith('gridlabd') or line.startswith('TMY3toTMY2_ansi'):
            jc = subprocess.Popen(process_line(line, local_vars), shell=True)
            jc.wait()
        else:
            name = None
            image = None
            depends = None
            if "fncs_broker" in line:
                p_broker = "Fncs"
                name = "fncs"
                image = "tesp-fncs:latest"
            elif "helics_broker" in line:
                p_broker = "Helics"
                line = line.replace(' -f', ' --ipv4 -f')
                name = "helics"
                image = "tesp-helics:latest"
            elif " python" in line or " java" in line:
                name = "tespapi_" + str(cnt)
                image = "tesp-tespapi:latest"
            elif "gridlabd " in line:
                name = "gridlabd_" + str(cnt)
                image = "tesp-gridlabd:latest"
            elif "energyplus " in line or "eplus_agent" in line:
                name = "eplus_" + str(cnt)
                image = "tesp-eplus:latest"
            elif "helics_recorder " in line or "helics_player" in line:
                name = "helics_" + str(cnt)
                image = "tesp-helics:latest"
            else:
                # The master build, heavyweight docker
                name = "build_" + str(cnt)
                image = "tesp-build:latest"
            cnt += 1
            services(name, image, docker_line(line, local_vars), cnt, op, depends)

    op.write('networks:\n')
    op.write('  cu_net:\n')
    op.write('    driver: bridge\n')
    op.write('    ipam:\n')
    op.write('      config:\n')
    op.write('        - subnet: 10.5.0.0/16\n')
    op.write('          gateway: 10.5.0.1\n')
    op.close()
    fp.close()

    if p_broker is not None:
        print('====  ' + p_broker + ' Broker Start in\n        ' + os.getcwd(), flush=True)
        docker_compose = "docker-compose -f " + file_name.replace("sh", "yaml")
        subprocess.Popen(docker_compose + " up", shell=True).wait()
        subprocess.Popen(docker_compose + " down", shell=True).wait()
        print('====  Broker Exit in\n        ' + os.getcwd(), flush=True)

    t_end = time.time()
    if b_reporting:
        t_elapsed = t_end - t_start
        if case_name is None:
            case_name = file_name
        reports.append({'case': case_name, 'elapsed': t_elapsed})
        print('====  Time elapsed: {:12.6f}'.format(t_elapsed), flush=True)
    print('==  Done: ', case_name, flush=True)


def report_tests():
    lines =  '\n\nTest Case(s)                Time(sec) Taken\n'
    lines += '===========================================\n'
    for row in reports:
        lines += '{:30s} {:12.6f}\n'.format(row['case'], row['elapsed'])
    return lines
