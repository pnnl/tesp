# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: pptest.py

import sys
import json
import subprocess
import os
import shutil
from datetime import datetime

cfgfile = 'test.json'

lp = open (cfgfile).read()
config = json.loads(lp)

tespdir = '../../../../ptesp/'
ppdir = tespdir + 'support/pypower/'
ppfile = ppdir + config['BackboneFiles']['PYPOWERFile']
ppcsv = ppdir + config['PYPOWERConfiguration']['CSVLoadFile']
print ('pypower backbone files from', ppdir)

casename = config['SimulationConfig']['CaseName']
workdir = config['SimulationConfig']['WorkingDirectory']
casedir = workdir + casename
print ('case files written to', casedir)

if os.path.exists(casedir):
    shutil.rmtree(casedir)
os.makedirs(casedir)

StartTime = config['SimulationConfig']['StartTime']
EndTime = config['SimulationConfig']['EndTime']
time_fmt = '%Y-%m-%d %H:%M:%S'
dt1 = datetime.strptime (StartTime, time_fmt)
dt2 = datetime.strptime (EndTime, time_fmt)
seconds = int ((dt2 - dt1).total_seconds())
days = seconds / 86400
print (days, seconds)

###################################
# dynamically import the base PYPOWER case
import importlib.util
spec = importlib.util.spec_from_file_location('ppbasecase', ppfile)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ppcase = mod.ppcasefile()
#print (ppcase)

# make ppcase JSON serializable
ppcase['bus'] = ppcase['bus'].tolist()
ppcase['gen'] = ppcase['gen'].tolist()
ppcase['branch'] = ppcase['branch'].tolist()
ppcase['areas'] = ppcase['areas'].tolist()
ppcase['gencost'] = ppcase['gencost'].tolist()
ppcase['FNCS'] = ppcase['FNCS'].tolist()
ppcase['UnitsOut'] = ppcase['UnitsOut'].tolist()
ppcase['BranchesOut'] = ppcase['BranchesOut'].tolist()

# update the case from config JSON
ppcase['StartTime'] = config['SimulationConfig']['StartTime']
ppcase['Tmax'] = int(seconds)
ppcase['Period'] = config['AgentPrep']['MarketClearingPeriod']
ppcase['dt'] = config['PYPOWERConfiguration']['PFStep']
ppcase['CSVFile'] = config['PYPOWERConfiguration']['CSVLoadFile']
if config['PYPOWERConfiguration']['ACOPF'] == 'AC':
	ppcase['opf_dc'] = 0
else:
	ppcase['opf_dc'] = 1
if config['PYPOWERConfiguration']['ACPF'] == 'AC':
	ppcase['pf_dc'] = 0
else:
	ppcase['pf_dc'] = 1
fncsBus = int (config['PYPOWERConfiguration']['GLDBus'])
fncsScale = float (config['PYPOWERConfiguration']['GLDScale'])
ppcase['FNCS'][0][0] = fncsBus
ppcase['FNCS'][0][2] = fncsScale
baseKV = float(config['PYPOWERConfiguration']['TransmissionVoltage'])
for row in ppcase['bus']:
	if row[0] == fncsBus:
		row[9] = baseKV

if len(config['PYPOWERConfiguration']['UnitOutStart']) > 0 and len(config['PYPOWERConfiguration']['UnitOutEnd']) > 0:
	dt3 = datetime.strptime (config['PYPOWERConfiguration']['UnitOutStart'], time_fmt)
	tout_start = int ((dt3 - dt1).total_seconds())
	dt3 = datetime.strptime (config['PYPOWERConfiguration']['UnitOutEnd'], time_fmt)
	tout_end = int ((dt3 - dt1).total_seconds())
	ppcase['UnitsOut'][0] = [int(config['PYPOWERConfiguration']['UnitOut']), tout_start, tout_end]
else:
	ppcase['UnitsOut'] = []

if len(config['PYPOWERConfiguration']['BranchOutStart']) > 0 and len(config['PYPOWERConfiguration']['BranchOutEnd']) > 0:
	dt3 = datetime.strptime (config['PYPOWERConfiguration']['BranchOutStart'], time_fmt)
	tout_start = int ((dt3 - dt1).total_seconds())
	dt3 = datetime.strptime (config['PYPOWERConfiguration']['BranchOutEnd'], time_fmt)
	tout_end = int ((dt3 - dt1).total_seconds())
	ppcase['BranchesOut'][0] = [int(config['PYPOWERConfiguration']['BranchOut']), tout_start, tout_end]
else:
	ppcase['BranchesOut'] = []

fp = open (casedir + '/ppcase.json', 'w')
json.dump (ppcase, fp, indent=2)
fp.close ()
shutil.copy (ppcsv, casedir)

ppyamlstr = """name: pypower
time_delta: """ + str(config['PYPOWERConfiguration']['PFStep']) + """s
broker: tcp://localhost:5570
values:
    SUBSTATION7:
        topic: gridlabdSimulator1/distribution_load
        default: 0
    UNRESPONSIVE_MW:
        topic: auction/unresponsive_mw
        default: 0
    RESPONSIVE_MAX_MW:
        topic: auction/responsive_max_mw
        default: 0
    RESPONSIVE_C2:
        topic: auction/responsive_c2
        default: 0
    RESPONSIVE_C1:
        topic: auction/responsive_c1
        default: 0
    RESPONSIVE_DEG:
        topic: auction/responsive_deg
        default: 0
"""
op = open (casedir + '/pypower.yaml', 'w')
print (ppyamlstr, file=op)
op.close()


