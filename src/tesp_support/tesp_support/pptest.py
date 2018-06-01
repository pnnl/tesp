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

fp = open ('ppcase.json', 'w')
json.dump (ppcase, fp, indent=2)
fp.close ()
###################################

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

shutil.copy (ppfile, casedir)
shutil.copy (ppcsv, casedir)

ppyamlstr = """name: pypower
time_delta: 15s
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


