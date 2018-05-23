import sys
import json
#import numpy as np
import os
import shutil

cfgfile = 'test.json'

lp = open (cfgfile).read()
config = json.loads(lp)

tespdir = config['SimulationConfig']['SourceDirectory']
tespdir = '../../../../tesp/'
feederdir = tespdir + 'src/gridlabd/feeder_generator/Input_feeders/'
scheduledir = tespdir + 'examples/schedules/'
weatherdir = tespdir + 'examples/weather/'
eplusdir = tespdir + 'examples/energyplus/'
ppdir = './'
print ('feeder backbone files from', feederdir)
print ('schedule files from', scheduledir)
print ('weather files from', weatherdir)
print ('E+ files from', eplusdir)
print ('pypower backbone files from', ppdir)

casename = config['SimulationConfig']['CaseName']
workdir = config['SimulationConfig']['WorkingDirectory']
casedir = workdir + casename
print ('case files written to', casedir)

if os.path.exists(casedir):
    shutil.rmtree(casedir)
os.makedirs(casedir)

weatherfile = weatherdir + config['WeatherPrep']['DataSource']
eplusfile = eplusdir + config['BackboneFiles']['EnergyPlusFile']
ppfile = ppdir + config['BackboneFiles']['PYPOWERFile']
shutil.copy (weatherfile, casedir)
shutil.copy (eplusfile, casedir)
shutil.copy (ppfile, casedir)
shutil.copy (scheduledir + 'appliance_schedules.glm', casedir)
shutil.copy (scheduledir + 'commercial_schedules.glm', casedir)
#shutil.copy (scheduledir + 'fixed_rate_schedule_v2.glm', casedir)
#shutil.copy (scheduledir + 'water_and_setpoint_schedule_v3.glm', casedir)
shutil.copy (scheduledir + 'water_and_setpoint_schedule_v5.glm', casedir)
