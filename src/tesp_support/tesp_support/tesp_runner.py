# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: run_test_case.py
"""Auto test runner for TESP run* cases
Runs a test case based on pre-existing shell script file.

If FNCS or HELICS broker exist the test waits for
 the broker process to finish before function returns.

This code has limited functionality as the 'run*' scripts
for the examples are written in a very specified way.
"""
import os
import sys
import time
import subprocess

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


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
    #  print ('@@@@ input line to execute:', line)
    foreground = line.replace(' &)', ')').replace(' &>', ' >')
    exports = ''
    for var in local_vars:
        exports = exports + 'export ' + var['key'] + '=' + var['val'] + ' && '
    #  print (' line transformed to:', exports + foreground)
    return exports + foreground


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


def report_tests():
    lines = '\n\n{:30s}   {:12s}\n'.format('Test Case(s)', 'Time Taken')
    lines += '===========================================\n'
    for row in reports:
        lines += '{:30s} {:12.6f}\n'.format(row['case'], row['elapsed'])
    return lines
