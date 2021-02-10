# usage 'python3 tabulate_metrics.py'
import sys
import os
import shutil
import stat
import json
import copy
from datetime import datetime
import numpy as np
import tesp_support.process_eplus as ep
import tesp_support.api as tesp
from tesp_support.run_test_case import RunTestCase
from tesp_support.run_test_case import InitializeTestCaseReports
from tesp_support.run_test_case import GetTestCaseReports

templateDir = '../../support/comm'
eplusDir = '/opt/tesp/share/support/energyplus'

caseDir = './scratch'

StartTime = '2013-08-01 00:00:00'
EndTime = '2013-08-03 00:00:00'
EPWFile = '2A_USA_TX_HOUSTON.epw'

brkTemplate = """(exec helics_broker -f {nFed} --name=mainbroker &> broker.log &)"""
plyTemplate = """(exec helics_player --input=prices.txt --local --time_units=ns --stop {nSec}s &> player.log &)"""
recTemplate = """(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period {period}s --stop {nSec}s &> tracer.log &)"""
epTemplate = """(export HELICS_CONFIG_FILE={epcfg} && exec energyplus -w epWeather.epw -d {outdir} -r {idfname} &> {eplog} &)"""
agjTemplate = """(exec eplus_agent_helics {agjcfg} &> {aglog} &)"""

#bldgs = ['FullServiceRestaurant',
#         'Hospital',
#         'LargeHotel',
#         'LargeOffice',
#         'MediumOffice',
#         'MidriseApartment',
#         'OutPatient',
#         'PrimarySchool',
#         'QuickServiceRestaurant',
#         'SecondarySchool',
#         'SmallHotel',
#         'SmallOffice',
#         'StandaloneRetail',
#         'StripMall',
#         'SuperMarket',
#         'Warehouse']

bldgs = ['LargeOffice',
         'MidriseApartment',
         'StandaloneRetail']

def configure_building (bldg_id):
  oname = '{:s}/{:s}.idf'.format (caseDir, bldg_id)
  IDFName = '{:s}/{:s}.idf'.format (eplusDir, bldg_id)
  EMSName = '{:s}/emsHELICS/ems{:s}.idf'.format (eplusDir, bldg_id)
  tesp.merge_idf (IDFName, EMSName, StartTime, EndTime, oname, 12)

  fp = open (templateDir + '/eplusH.json').read()
  eplusTemplate = json.loads(fp)

  fp = open (templateDir + '/eplus_agentH.json').read()
  agentTemplate = json.loads(fp)

  agName = 'agent' + bldg_id
  epName = 'eplus' + bldg_id

  eDict = copy.deepcopy(eplusTemplate)
  eDict['name'] = epName
  for sub in eDict['subscriptions']:
    sub['key'] = sub['key'].replace ('eplus_agent', agName)
  oname = '{:s}/ep_{:s}.json'.format (caseDir, bldg_id)
  op = open (oname, 'w')
  json.dump (eDict, op, ensure_ascii=False, indent=2)
  op.close()

  aDict = copy.deepcopy(agentTemplate)
  aDict['name'] = agName
  for sub in aDict['subscriptions']:
    sub['key'] = sub['key'].replace ('energyPlus', epName)
  oname = '{:s}/ag_{:s}.json'.format (caseDir, bldg_id)
  op = open (oname, 'w')
  json.dump (aDict, op, ensure_ascii=False, indent=2)
  op.close()

def configure_case (bldg_id, tcap, base_price = 0.10, ramp = 25.0):
  seconds = 172800
  period = 300

  fname = '{:s}/run.sh'.format (caseDir)
  fp = open(fname, 'w')
  print (brkTemplate.format (nFed=4), file=fp)
  print (recTemplate.format (nSec=seconds, period=period), file=fp)
  print (plyTemplate.format (nSec=seconds), file=fp)
  idfname = bldg + '.idf'
  outdir = 'out' + bldg_id
  epcfg = 'ep_' + bldg_id + '.json'
  eplog = 'ep_' + bldg_id + '.log'
  agcfg = 'ag_' + bldg_id + '.json'
  agjcfg = 'agj_' + bldg_id + '.json'
  aglog = 'ag_' + bldg_id + '.log'
  print (epTemplate.format (epcfg=epcfg, outdir=outdir, idfname=idfname, eplog=eplog), file=fp)
  print (agjTemplate.format (agjcfg=agjcfg, aglog=aglog), file=fp)
  fp.close()
  st = os.stat (fname)
  os.chmod (fname, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

  oname = '{:s}/agj_{:s}.json'.format (caseDir, bldg_id)
  op = open (oname, 'w')
  aDict = {'StartTime': StartTime,
         'LoadScale': 1.0,
         'BuildingID': bldg_id,
         'MetricsFileName': 'eplus_{:s}_metrics.json'.format (bldg_id),
         'HelicsConfigFile': 'ag_{:s}.json'.format (bldg_id),
         'StopSeconds' : seconds,
         'MetricsPeriod': period,
         'BasePrice' : base_price,
         'RampSlope' : ramp,
         'MaxDeltaHeat' : tcap,
         'MaxDeltaCool': tcap,
         'UsePriceRamp': True}
  json.dump (aDict, op, ensure_ascii=False, indent=2)
  op.close()
  return bldg

def get_kw (rootname):  # TODO - we want the kW difference between 9 a.m. and 7 p.m.
  emetrics = ep.read_eplus_metrics (rootname, quiet=True)
  data = emetrics ['data_e']
  idx_e = emetrics ['idx_e']
  avg_kw = 0.001 * data[:,idx_e['ELECTRIC_DEMAND_IDX']].mean()
  idx1 = int (9 * 12)
  idx2 = int (19 * 12)
  avg_kw1 = 0.001 * data[idx1:idx2,idx_e['ELECTRIC_DEMAND_IDX']].mean()
  idx1 = int (33 * 12)
  idx2 = int (43 * 12)
  avg_kw2 = 0.001 * data[idx1:idx2,idx_e['ELECTRIC_DEMAND_IDX']].mean()
  return 0.5 * (avg_kw1 + avg_kw2) # avg_kw

def run_case (basePath, label, mfile):
  os.chdir (caseDir)
  RunTestCase ('run.sh', label)
  kw = get_kw (mfile)
  os.chdir (basePath)
  return kw

if __name__ == '__main__':
  print ('usage: python3 tabulate_responses.py')

  InitializeTestCaseReports()
  basePath = os.getcwd()

  if os.path.exists(caseDir):
    shutil.rmtree(caseDir)
  os.makedirs(caseDir)

  shutil.copy ('../../support/misc/clean.sh', caseDir)
  shutil.copy ('../../support/misc/kill23404.sh', caseDir)
  shutil.copy ('../../support/comm/eplots.py', caseDir)
  shutil.copy ('{:s}/{:s}'.format (eplusDir, EPWFile), '{:s}/{:s}'.format (caseDir, 'epWeather.epw'))
  shutil.copy ('../../support/comm/prices.txt', caseDir)
  shutil.copy ('../../support/comm/helicsRecorder.json', caseDir)

  for bldg in bldgs:
    configure_building (bldg)

  results = {}
  for bldg in bldgs:
    results[bldg] = {}
    for tcap in [0.01, 1.0, 2.0, 3.0, 5.0]:
      mfile = configure_case (bldg, tcap)
      kw = run_case (basePath, '{:s}_{:.2f}'.format (bldg, tcap), mfile)
      key = '{:.2f}'.format (tcap)
      results[bldg][key] = kw
  print (GetTestCaseReports())

  print ('Building                  Tcap   Avg kW')
  for bldg in bldgs:
    for tcap in [0.01, 1.0, 2.0, 3.0, 5.0]:
      key = '{:.2f}'.format (tcap)
      print ('{:25s} {:4.2f} {:8.2f}'.format (bldg, tcap, results[bldg][key]))

"""
Results obtained 1/29/2021

LoadScale is 1.0
LargeOffice_0.01                   5.729167
LargeOffice_1.00                   6.332680
LargeOffice_2.00                   6.501234
LargeOffice_3.00                   6.659761
LargeOffice_5.00                   7.108884
MidriseApartment_0.01             10.286237
MidriseApartment_1.00              8.758575
MidriseApartment_2.00              9.184352
MidriseApartment_3.00              8.618092
MidriseApartment_5.00              8.366942
StandaloneRetail_0.01              3.958328
StandaloneRetail_1.00              4.789432
StandaloneRetail_2.00              3.922260
StandaloneRetail_3.00              4.432790
StandaloneRetail_5.00              4.730973

Building                  Tcap   Avg kW
LargeOffice               0.01  1716.39
LargeOffice               1.00  1699.07
LargeOffice               2.00  1689.57
LargeOffice               3.00  1685.25
LargeOffice               5.00  1680.87
MidriseApartment          0.01    54.08
MidriseApartment          1.00    48.59
MidriseApartment          2.00    43.38
MidriseApartment          3.00    39.27
MidriseApartment          5.00    33.48
StandaloneRetail          0.01   135.49
StandaloneRetail          1.00   131.15
StandaloneRetail          2.00   126.82
StandaloneRetail          3.00   122.48
StandaloneRetail          5.00   114.35

"""
