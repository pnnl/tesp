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
bReporting = False


def block(call):
    print('\n<!--', flush=True)
    call()
    print('--!>', flush=True)


def GetTestReports():
    global reports

    lines = '\n\n{:30s}   {:12s}\n'.format('Test Case(s)', 'Time Taken')
    lines += '===========================================\n'
    for row in reports:
        lines += '{:30s} {:12.6f}\n'.format(row['case'], row['elapsed'])
    return lines


def InitializeTestReports():
    global reports, bReporting

    reports = []
    bReporting = True


def ProcessLine(line, local_vars):
    #  print ('@@@@ input line to execute:', line)
    foreground = line.replace(' &)', ')').replace(' &>', ' >')
    exports = ''
    for var in local_vars:
        exports = exports + 'export ' + var['key'] + '=' + var['val'] + ' && '
    #  print (' line transformed to:', exports + foreground)
    return exports + foreground


def PrepareTest(casename=None):
    print('==  Prepare: ', casename, flush=True)


def RunTest(fname, casename=None):
    global reports, bReporting

    tStart = time.time()
    local_vars = []
    fp = open(fname, 'r')
    potherList = []
    pFNCSbroker = None
    pHELICSbroker = None
    print('\n==  Run: ', casename, flush=True)
    for ln in fp:
        line = ln.rstrip('\n')
        if ('#!/bin/bash' in line) or (len(line) < 1):
            continue
        if line[0] == '#':
            continue
        if line.startswith('declare'):
            toks = line.split()
            keyval = toks[2].split('=')
            local_vars.append({'key': keyval[0], 'val': keyval[1]})
        elif line.startswith('javac') or line.startswith('python') or \
                line.startswith('make') or line.startswith('chmod') or \
                line.startswith('gridlabd') or line.startswith('TMY3toTMY2_ansi'):
            jc = subprocess.Popen(ProcessLine(line, local_vars), shell=True)
            jc.wait()
        elif 'fncs_broker' in line:
            print('====  Fncs Broker Start in\n        ' + os.getcwd(), flush=True)
            pFNCSbroker = subprocess.Popen(ProcessLine(line, local_vars), shell=True)
        elif 'helics_broker' in line:
            print('====  Helics Broker Start in\n        ' + os.getcwd(), flush=True)
            pHELICSbroker = subprocess.Popen(ProcessLine(line, local_vars), shell=True)
        else:
            pother = subprocess.Popen(ProcessLine(line, local_vars), shell=True)
            potherList.append(pother)
    fp.close()
    if pFNCSbroker is not None:
        pFNCSbroker.wait()
        print('====  Fncs Broker Exit in\n        ' + os.getcwd(), flush=True)
    if pHELICSbroker is not None:
        pHELICSbroker.wait()
        print('====  Helics Broker Exit in\n        ' + os.getcwd(), flush=True)
    for p in potherList:
        p.wait()

    tEnd = time.time()
    if bReporting:
        tElapsed = tEnd - tStart
        if casename is None:
            casename = fname
        reports.append({'case': casename, 'elapsed': tElapsed})
    print('==  Done: ', casename, flush=True)
