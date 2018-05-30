import sys
import json
import subprocess
import os
import shutil
from datetime import datetime

cfgfile = 'test.json'

lp = open (cfgfile).read()
config = json.loads(lp)

tespdir = config['SimulationConfig']['SourceDirectory']
tespdir = '../../../../ptesp/'
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
glmroot = config['BackboneFiles']['TaxonomyChoice']
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

EpRef = config['EplusConfiguration']['ReferencePrice']
EpRamp = config['EplusConfiguration']['Slope']
EpLimHi = config['EplusConfiguration']['OffsetLimitHi']
EpLimLo = config['EplusConfiguration']['OffsetLimitLo']
EpWeather = config['EplusConfiguration']['EnergyPlusWeather']
EpStep = config['EplusConfiguration']['TimeStep'] # minutes
EpFile = config['BackboneFiles']['EnergyPlusFile']
EpAgentStop = str (seconds) + 's'
EpAgentStep = str (config['FeederGenerator']['MetricsInterval']) + 's'

weatherfile = weatherdir + config['WeatherPrep']['DataSource']
eplusfile = eplusdir + EpFile
eplusweather = eplusdir + EpWeather
ppfile = ppdir + config['BackboneFiles']['PYPOWERFile']
shutil.copy (weatherfile, casedir)
shutil.copy (eplusfile, casedir)
shutil.copy (eplusweather, casedir)
shutil.copy (ppfile, casedir)
shutil.copy (scheduledir + 'appliance_schedules.glm', casedir)
shutil.copy (scheduledir + 'commercial_schedules.glm', casedir)
#shutil.copy (scheduledir + 'fixed_rate_schedule_v2.glm', casedir)
#shutil.copy (scheduledir + 'water_and_setpoint_schedule_v3.glm', casedir)
shutil.copy (scheduledir + 'water_and_setpoint_schedule_v5.glm', casedir)

# write some YAML files - TODO time steps in each YAML file
op = open (casedir + '/eplus.yaml', 'w')
print ('name: eplus', file=op)
print ('time_delta:', str (EpStep) + 'm', file=op)
print ('broker: tcp://localhost:5570', file=op)
print ('values:', file=op)
print ('    COOL_SETP_DELTA:', file=op)
print ('        topic: eplus_json/cooling_setpoint_delta', file=op)
print ('        default: 0', file=op)
print ('    HEAT_SETP_DELTA:', file=op)
print ('        topic: eplus_json/heating_setpoint_delta', file=op)
print ('        default: 0', file=op)
op.close()

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

epjyamlstr = """name: eplus_json
time_delta: """ + EpAgentStep + """
broker: tcp://localhost:5570
values:
    kwhr_price:
        topic: auction/clear_price
        default: 0.10
    cooling_controlled_load:
        topic: eplus/EMS COOLING CONTROLLED LOAD
        default: 0
    cooling_desired_temperature:
        topic: eplus/EMS COOLING DESIRED TEMPERATURE
        default: 0
    cooling_current_temperature:
        topic: eplus/EMS COOLING CURRENT TEMPERATURE
        default: 0
    cooling_power_state:
        topic: eplus/EMS COOLING POWER STATE
        default: 0
    heating_controlled_load:
        topic: eplus/EMS HEATING CONTROLLED LOAD
        default: 0
    heating_desired_temperature:
        topic: eplus/EMS HEATING DESIRED TEMPERATURE
        default: 0
    heating_current_temperature:
        topic: eplus/EMS HEATING CURRENT TEMPERATURE
        default: 0
    heating_power_state:
        topic: eplus/EMS HEATING POWER STATE
        default: 0
    electric_demand_power:
        topic: eplus/WHOLE BUILDING FACILITY TOTAL ELECTRIC DEMAND POWER
        default: 0
    ashrae_uncomfortable_hours:
        topic: eplus/FACILITY FACILITY THERMAL COMFORT ASHRAE 55 SIMPLE MODEL SUMMER OR WINTER CLOTHES NOT COMFORTABLE TIME
        default: 0
    occupants_1:
        topic: eplus/BATH_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_2:
        topic: eplus/CAFETERIA_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_3:
        topic: eplus/COMPUTER_CLASS_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_4:
        topic: eplus/CORNER_CLASS_1_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_5:
        topic: eplus/CORNER_CLASS_1_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_6:
        topic: eplus/CORNER_CLASS_1_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_7:
        topic: eplus/CORNER_CLASS_2_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_8:
        topic: eplus/CORNER_CLASS_2_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_9:
        topic: eplus/CORNER_CLASS_2_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_10:
        topic: eplus/CORRIDOR_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_11:
        topic: eplus/CORRIDOR_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_12:
        topic: eplus/CORRIDOR_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_13:
        topic: eplus/GYM_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_14:
        topic: eplus/KITCHEN_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_15:
        topic: eplus/LIBRARY_MEDIA_CENTER_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_17:
        topic: eplus/MAIN_CORRIDOR_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_18:
        topic: eplus/MULT_CLASS_1_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_19:
        topic: eplus/MULT_CLASS_1_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_20:
        topic: eplus/MULT_CLASS_1_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_21:
        topic: eplus/MULT_CLASS_2_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_22:
        topic: eplus/MULT_CLASS_2_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_23:
        topic: eplus/MULT_CLASS_2_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_24:
        topic: eplus/OFFICES_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
"""
op = open (casedir + '/eplus_json.yaml', 'w')
print (epjyamlstr, file=op)
op.close()

p1 = subprocess.Popen ('python feederGenerator.py ' + cfgfile, shell=True)
p1.wait()
glmfile = casedir + '/' + casename
p2 = subprocess.Popen ('python glm_dict.py ' + glmfile, shell=True)
p2.wait()
p3 = subprocess.Popen ('python prep_auction.py ' + cfgfile + ' ' + glmfile, shell=True)
p3.wait()

if sys.platform == 'win32':
    batname = 'run.bat'
else:
    op = open (casedir + '/run.sh', 'w')
    print ('(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 5 &> broker.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=eplus.yaml && exec EnergyPlus -w ' 
           + EpWeather + ' -d output -r ' + EpFile + ' &> eplus.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json', EpAgentStop, EpAgentStep, 
           EpFile + ' eplus_' + casename + '_metrics.json', EpRef, EpRamp, EpLimHi, EpLimLo, '&> eplus_json.log &)', file=op)
    print ('(export FNCS_FATAL=NO && exec gridlabd -D USE_FNCS -D METRICS_FILE='
           + casename + '_metrics.json ' + casename + '.glm &> gridlabd.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=' + casename + '_auction.yaml && export FNCS_FATAL=NO && exec python auction.py '
           + casename + '_agent_dict.json ' + casename + ' &> auction.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py '
           + casename + ' &> pypower.log &)', file=op)
    op.close()


