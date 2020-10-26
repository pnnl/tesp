import tesp_support.api as tesp
import sys
import json
import os
import shutil
import stat
import math
import copy
from datetime import datetime
 
template_dir = './templates/'

def configure_eplus (caseConfig):
  StartDate = caseConfig['StartDate']
  EndDate = caseConfig['EndDate']
  time_fmt = '%Y-%m-%d %H:%M:%S'
  dt1 = datetime.strptime (StartDate, time_fmt)
  dt2 = datetime.strptime (EndDate, time_fmt)
  seconds = int ((dt2 - dt1).total_seconds())

  fp = open (template_dir + 'eplusH.json').read()
  eplusTemplate = json.loads(fp)

  fp = open (template_dir + 'eplus_agentH.json').read()
  agentTemplate = json.loads(fp)

  caseDir = caseConfig['CaseDir']
  caseName = caseConfig['CaseName']

  fedNodes = {}

  for bldg in caseConfig['Buildings']:
    if len(bldg['IDF']) > 0:
      fedRoot = '{:d}_{:s}'.format (bldg['ID'], bldg['Name'])
      fedNodes[fedRoot] = bldg['Node']
      print ('building configuration and merging IDF for', fedRoot)
      agName = 'agent' + fedRoot
      epName = 'eplus' + fedRoot

      eDict = copy.deepcopy(eplusTemplate)
      eDict['name'] = epName
      for sub in eDict['subscriptions']:
        sub['key'] = sub['key'].replace ('eplus_agent', agName)
      oname = '{:s}/ep_{:s}_{:s}.json'.format (caseDir, caseName, fedRoot)
      op = open (oname, 'w')
      json.dump (eDict, op, ensure_ascii=False, indent=2)
      op.close()

      aDict = copy.deepcopy(agentTemplate)
      aDict['name'] = agName
      for sub in aDict['subscriptions']:
        sub['key'] = sub['key'].replace ('energyPlus', epName)
      oname = '{:s}/ag_{:s}_{:s}.json'.format (caseDir, caseName, fedRoot)
      op = open (oname, 'w')
      json.dump (aDict, op, ensure_ascii=False, indent=2)
      op.close()

      oname = '{:s}/agj_{:s}_{:s}.json'.format (caseDir, caseName, fedRoot)
      op = open (oname, 'w')
      aDict = {'StartTime': caseConfig['StartDate'],
               'LoadScale': bldg['EpScale'],
               'BuildingID': fedRoot,
               'MetricsFileName': 'eplus_{:s}_metrics.json'.format (fedRoot),
               'HelicsConfigFile': 'ag_{:s}_{:s}.json'.format (caseName, fedRoot),
               'StopSeconds' : seconds,
               'MetricsPeriod': caseConfig['MetricsPeriod'],
               'BasePrice' : 0.02,
               'RampSlope' : 25.0,
               'MaxDeltaHeat' : 4.0,
               'MaxDeltaCool': 4.0}
      json.dump (aDict, op, ensure_ascii=False, indent=2)
      op.close()

      oname = '{:s}/{:s}.idf'.format (caseDir, fedRoot)
      tesp.merge_idf (bldg['IDF'], bldg['EMS'], caseConfig['StartDate'], caseConfig['EndDate'], 
                      oname, caseConfig['EpStepsPerHour'])
  return fedNodes


substationLines = """  object metrics_collector {
    interval ${METRICS_INTERVAL};
  };"""

billingMeterLines = """  bill_mode UNIFORM;
  price 0.11420;
  monthly_fee 25.00;
  bill_day 1;
  object metrics_collector {
    interval ${METRICS_INTERVAL};
  };"""

gldLines = """#set relax_naming_rules=1
#set profiler=1
#set minimum_timestep={gld_step}
clock {{
  timezone PST+8PDT;
  starttime '{sdate}';
  stoptime '{edate}';
}};
module powerflow {{
  solver_method NR;
  line_capacitance TRUE;
}};
module generators;
module tape;
module climate;
module connection;

#define METRICS_INTERVAL={metrics_interval}
#define METRICS_FILE={root}_metrics.json
object metrics_collector_writer {{
  interval ${{METRICS_INTERVAL}};
  filename ${{METRICS_FILE}};
}};

object climate {{
  name localWeather;
  tmyfile "gldWeather.tmy3";
  interpolate QUADRATIC;
}};

#define VSOURCE=69715.0
#include "{root}_net.glm";
#include "solar_pv.glm";
#ifdef USE_HELICS
object helics_msg {{
  configure gld_{root}.json;
}}
#endif
object recorder {{
  parent sourcebus;
  property distribution_power_A,distribution_power_B,distribution_power_C,distribution_load,positive_sequence_voltage;
  interval 60;
  file substation_load.csv;
}}
object recorder {{
  parent localWeather;
  property temperature,pressure,humidity,wind_speed,solar_direct,solar_diffuse;
  interval 60;
  file weather.csv;
}}"""

def writeGlmClass (theseLines, thisClass, op):
  print ('object', thisClass, '{', file=op)
  for i in range(1, len(theseLines)):
    print (theseLines[i], file=op)

# replace building node objects with a billing meter that collects metrics
# also make the substation collect metrics and configure itself to HELICS
def prepare_glm_file (caseConfig):
  iname = caseConfig['BaseGLMFile']
  oname = '{:s}/{:s}_net.glm'.format (caseConfig['CaseDir'], caseConfig['CaseName'])
  buses = []
  meters = []
  scale = caseConfig['LoadScale']
  xfmrLoadScales = {}
  xfscale = 1.0
  bPower = False
  bCurrent = False # TODO: not supported yet
  bImpedance = False
  if caseConfig['LoadType'] == 'ConstantPower':
    bPower = True
  elif caseConfig['LoadType'] == 'ConstantImpedance':
    bImpedance = True
  elif caseConfig['LoadType'] == 'ConstantCurrent':
    bCurrent = True

  for bldg in caseConfig['Buildings']:
    buses.append (bldg['Node'])
    loadname = 'ld_' + bldg['Node']
    xfmrLoadScales[loadname] = bldg['XfScale']
  print ('filtering', len(buses), 'buildings', iname, 'to', oname, 'load scale =', scale)

  thisClass = ''
  thisName = ''
  theseLines = []
  nomkW = 0.0
  nomV = 7200.0

  ip = open (iname, 'r')
  op = open (oname, 'w')
  for line in ip:
    ln = line.rstrip()
    lst = ln.strip().split()
    if len(lst) > 0:
      if lst[0] == '}':
        if thisClass == 'substation':
          theseLines.append (substationLines)
        theseLines.append (ln)
        writeGlmClass (theseLines, thisClass, op)
        thisClass = ''
        theseLines = []
        xfscale = 1.0
      else:
        if 'constant_power' in ln:
          scaledLoad = xfscale * scale * complex(lst[1].strip(';'))
          nomkW += 0.001 * scaledLoad.real
          if scaledLoad.imag < 0.0:
            print ('Reactive injection at', thisName)
          if bPower:
            theseLines.append ('  {:s} {:.2f}+{:.2f}j;'.format (lst[0], scaledLoad.real, scaledLoad.imag))
          elif bImpedance:
            zLoad = nomV * nomV / scaledLoad
            theseLines.append ('  {:s} {:.2f}+{:.2f}j;'.format (lst[0].replace ('power', 'impedance'), 
                                                              zLoad.real, -zLoad.imag)) # conjugate!
          elif bCurrent:
            iLoad = scaledLoad / nomV
            theseLines.append ('  {:s} {:.2f}{:.2f}j;'.format (lst[0].replace ('power', 'current'), 
                                                              iLoad.real, -iLoad.imag)) # conjugate
        else:
          theseLines.append (ln)
    if len(lst) > 1:
      if lst[0] == 'nominal_voltage':
        nomV = float (lst[1].strip(';'))
      if lst[0] == 'object':
        thisClass = lst[1]
      if lst[0] == 'name':
        thisName = lst[1].lstrip('"').rstrip('";')
        if (thisClass == 'load') and (thisName in xfmrLoadScales):
          xfscale = xfmrLoadScales[thisName]
        if thisName in buses:
          meters.append (lst[1])
          thisClass = 'meter'
          theseLines.append (billingMeterLines)

  if len(theseLines) > 0:
    writeGlmClass (theseLines, thisClass, op)

  ip.close()
  op.close()

  gname = '{:s}/{:s}.glm'.format (caseConfig['CaseDir'], caseConfig['CaseName'])
  gp = open (gname, 'w')
  print (gldLines.format (root=caseConfig['CaseName'], 
                          sdate=caseConfig['StartDate'], 
                          edate=caseConfig['EndDate'],
                          metrics_interval=caseConfig['MetricsPeriod'],
                          gld_step=caseConfig['GldStep']), file=gp)
  gp.close()
  print ('{:.3f} kW total load'.format (nomkW))

# dictionary of building meters and inverters
def prepare_glm_dict (caseConfig):
  oname = '{:s}/{:s}_glm_dict.json'.format (caseConfig['CaseDir'], caseConfig['CaseName'])
  print ('dictionary for meters to', oname)

  feeder_id = caseConfig['CaseName']
  inverters = {}
  meters = {}
  feeders = {}
  meters['pv_mtr'] = {'feeder_id':feeder_id,'phases':'ABC','vll':480.0,'vln':277.13,'children':['pv_inv']}
  inverters['pv_inv'] = {'feeder_id':feeder_id, 'billingmeter_id':'pv_mtr',
                         'rated_W':125000.0,'resource':'solar','inv_eta':1.0}
  for row in caseConfig['Buildings']:
    mtr_id = row['Node']
    mtr_load = 'ld_' + mtr_id
    vll = row['Vnom']
    vln = float('{:.3f}'.format(vll/math.sqrt(3.0)))
    meters[mtr_id] = {'feeder_id':feeder_id,'phases':'ABC','vll':vll,'vln':vln,'children':[mtr_load]}

  feeders[feeder_id] = {'house_count':0,'inverter_count':1,'base_feeder':'PNNL CoR'}
  dict = {'bulkpower_bus':'BPA','FedName':'gld1','transformer_MVA':32.0,'feeders':feeders, 
    'billingmeters':meters,'houses':{},'inverters':inverters,'capacitors':{},'regulators':{}}

  op = open (oname, 'w')
  json.dump (dict, op, ensure_ascii=False, indent=2)
  op.close()

def prepare_glm_helics (caseConfig, fedNodes):
  oname = '{:s}/gld_{:s}.json'.format (caseConfig['CaseDir'], caseConfig['CaseName'])
  print ('HELICS pub/sub for GridLAB-D to', oname)
  pubs = []
  subs = []
  pubs.append ({'global':False, 'key':'distribution_load', 'type':'complex', 'info':{'object':'sourcebus','property':'distribution_load'}})
  for bldg, meter in fedNodes.items():
    load = 'ld_' + meter
    agFed = 'agent' + bldg
    subs.append ({'key': agFed + '/power_A', 'type':'complex', 'info':{'object':load, 'property':'constant_power_A'}})
    subs.append ({'key': agFed + '/power_B', 'type':'complex', 'info':{'object':load, 'property':'constant_power_B'}})
    subs.append ({'key': agFed + '/power_C', 'type':'complex', 'info':{'object':load, 'property':'constant_power_C'}})
    subs.append ({'key': agFed + '/bill_mode', 'type':'string', 'info':{'object':meter, 'property':'bill_mode'}})
    subs.append ({'key': agFed + '/price', 'type':'double', 'info':{'object':meter, 'property':'price'}})
    subs.append ({'key': agFed + '/monthly_fee', 'type':'double', 'info':{'object':meter, 'property':'monthly_fee'}})
    for prop in ['measured_voltage_A']:
      pubs.append ({'global':False, 'key':meter + '/' + prop, 'type':'complex', 'info':{'object':meter,'property':prop}})
  msg = {}
  msg['name'] = 'gld1'
  msg['period'] = int (caseConfig['GldStep'])
  msg['publications'] = pubs
  msg['subscriptions'] = subs

  op = open (oname, 'w', encoding='utf-8')
  json.dump (msg, op, ensure_ascii=False, indent=2)
  op.close()

brkTemplate = """(exec helics_broker -f {nFed} --name=mainbroker &> broker.log &)"""
plyTemplate = """(exec helics_player --input=prices.txt --local --time_units=ns --stop {nSec}s &> player.log &)"""
recTemplate = """(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period {period}s --stop {nSec}s &> tracer.log &)"""
gldTemplate = """(exec gridlabd -D USE_HELICS {root}.glm &> gridlabd.log &)"""
epTemplate = """(export HELICS_CONFIG_FILE={epcfg} && exec energyplus -w epWeather.epw -d {outdir} -r {idfname} &> {eplog} &)"""
#agTemplate = """(exec eplus_agent_helics {nSec}s {period}s {bldg} eplus_{bldg}_metrics.json 0.02 25 4 4 {agcfg} &> {aglog} &)"""
agjTemplate = """(exec eplus_agent_helics {agjcfg} &> {aglog} &)"""

def prepare_run_script (caseConfig, fedNodes):
  StartDate = caseConfig['StartDate']
  EndDate = caseConfig['EndDate']
  time_fmt = '%Y-%m-%d %H:%M:%S'
  dt1 = datetime.strptime (StartDate, time_fmt)
  dt2 = datetime.strptime (EndDate, time_fmt)
  seconds = int ((dt2 - dt1).total_seconds())
  days = seconds / 86400
  WeatherYear = dt1.year
  nFeds = 2 * len(fedNodes) + 3  # 2 for each E+ building, plus GridLAB-D, recorder and player
  period = caseConfig['MetricsPeriod']
  caseName = caseConfig['CaseName']
  print ('run', nFeds, 'federates for', days, 'days or', seconds, 'seconds in weather year', WeatherYear)

  fname = '{:s}/run.sh'.format (caseConfig['CaseDir'])
  fp = open(fname, 'w')
  print (brkTemplate.format (nFed=nFeds), file=fp)
  print (recTemplate.format (nSec=seconds, period=period), file=fp)
  print (plyTemplate.format (nSec=seconds), file=fp)
  print (gldTemplate.format (root=caseName), file=fp)
  for bldg in fedNodes:
    idfname = bldg + '.idf'
    outdir = 'out' + bldg
    epcfg = 'ep_' + caseName + '_' + bldg + '.json'
    eplog = 'ep_' + bldg + '.log'
    agcfg = 'ag_' + caseName + '_' + bldg + '.json'
    agjcfg = 'agj_' + caseName + '_' + bldg + '.json'
    aglog = 'ag_' + bldg + '.log'
    print (epTemplate.format (epcfg=epcfg, outdir=outdir, idfname=idfname, eplog=eplog), file=fp)
    print (agjTemplate.format (agjcfg=agjcfg, aglog=aglog), file=fp)
#    print (agTemplate.format (agcfg=agcfg, nSec=seconds, period=period, bldg=bldg, aglog=aglog), file=fp)
  fp.close()
  st = os.stat (fname)
  os.chmod (fname, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

if __name__ == '__main__':
  print ('usage: python3 prepare_case.py casedef.json')

  fname = 'casedef.json'
  if len(sys.argv) > 1:
      fname = sys.argv[1]
  fp = open(fname, 'r').read()
  caseConfig = json.loads(fp)
  caseDir = caseConfig['CaseDir']
  if os.path.exists(caseDir):
    shutil.rmtree(caseDir)
  os.makedirs(caseDir)
  print ('read', len(caseConfig['Buildings']), 'buildings from', fname, 'writing to', caseDir)

  prepare_glm_file (caseConfig)
  prepare_glm_dict (caseConfig)
  fedNodes = configure_eplus (caseConfig)
  prepare_glm_helics (caseConfig, fedNodes)
  prepare_run_script (caseConfig, fedNodes)

  shutil.copy ('clean.sh', caseDir)
  shutil.copy ('kill23404.sh', caseDir)
  shutil.copy ('gplots.py', caseDir)
  shutil.copy ('eplots.py', caseDir)
  shutil.copy ('solar_pv.glm', caseDir)
  shutil.copy (caseConfig['EPWFile'], '{:s}/{:s}'.format (caseDir, 'epWeather.epw'))
  shutil.copy (caseConfig['TMYFile'], '{:s}/{:s}'.format (caseDir, 'gldWeather.tmy3'))
  shutil.copy ('prices.txt', caseDir)
  shutil.copy ('helicsRecorder.json', caseDir)

