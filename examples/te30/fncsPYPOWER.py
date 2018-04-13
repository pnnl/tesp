#  Copyright (C) 2017 Battelle Memorial Institute
import json
import sys
import warnings
import csv
import fncs
from ppcasefile import ppcasefile
import numpy as np
import pypower.api as pp
#import scipy.io as spio
import math
import re
import copy
#import cProfile
#import pstats

def summarize_opf(res):
  bus = res['bus']
  gen = res['gen']

  Pload = bus[:,2].sum()
  Pgen = gen[:,1].sum()
  PctLoss = 100.0 * (Pgen - Pload) / Pgen

  print('success =', res['success'], 'in', res['et'], 'seconds')
  print('Total Gen =', Pgen, ' Load =', Pload, ' Loss =', PctLoss, '%')

  print('bus #, Pd, Qd, Vm, LMP_P, LMP_Q, MU_VMAX, MU_VMIN')
  for row in bus:
    print(int(row[0]),row[2],row[3],row[7],row[13],row[14],row[15],row[16])

  print('gen #, bus, Pg, Qg, MU_PMAX, MU_PMIN, MU_PMAX, MU_PMIN')
  idx = 1
  for row in gen:
    print(idx,int(row[0]),row[1],row[2],row[21],row[22],row[23],row[24])
    ++idx

def make_dictionary(ppc, rootname):
  fncsBuses = {}
  generators = {}
  unitsout = []
  branchesout = []
  bus = ppc['bus']
  gen = ppc['gen']
  cost = ppc['gencost']
  fncsBus = ppc['FNCS']
  units = ppc['UnitsOut']
  branches = ppc['BranchesOut']

  for i in range (gen.shape[0]):
    busnum = gen[i,0]
    bustype = bus[busnum-1,1]
    if bustype == 1:
      bustypename = 'pq'
    elif bustype == 2:
      bustypename = 'pv'
    elif bustype == 3:
      bustypename = 'swing'
    else:
      bustypename = 'unknown'
    generators[str(i+1)] = {'bus':int(busnum),'bustype':bustypename,'Pnom':float(gen[i,1]),'Pmax':float(gen[i,8]),'genfuel':'tbd','gentype':'tbd',
      'StartupCost':float(cost[i,1]),'ShutdownCost':float(cost[i,2]), 'c2':float(cost[i,4]), 'c1':float(cost[i,5]), 'c0':float(cost[i,6])}

  for i in range (fncsBus.shape[0]):
    busnum = int(fncsBus[i,0])
    busidx = busnum - 1
    fncsBuses[str(busnum)] = {'Pnom':float(bus[busidx,2]),'Qnom':float(bus[busidx,3]),'area':int(bus[busidx,6]),'zone':int(bus[busidx,10]),
      'ampFactor':float(fncsBus[i,2]),'GLDsubstations':[fncsBus[i,1]]}

  for i in range (units.shape[0]):
    unitsout.append ({'unit':int(units[i,0]),'tout':int(units[i,1]),'tin':int(units[i,2])})

  for i in range (branches.shape[0]):
    branchesout.append ({'branch':int(branches[i,0]),'tout':int(branches[i,1]),'tin':int(branches[i,2])})

  dp = open (rootname + "_m_dict.json", "w")
  ppdict = {'baseMVA':ppc['baseMVA'],'fncsBuses':fncsBuses,'generators':generators,'UnitsOut':unitsout,'BranchesOut':branchesout}
  print (json.dumps(ppdict), file=dp, flush=True)
  dp.close()

def parse_mva(arg):
  tok = arg.strip('+-; MWVAKdrij')
  vals = re.split(r'[\+-]+', tok)
  if len(vals) < 2: # only a real part provided
    vals.append('0')
  vals = [float(v) for v in vals]

  if '-' in tok:
    vals[1] *= -1.0
  if arg.startswith('-'):
    vals[0] *= -1.0

  if 'd' in arg:
    vals[1] *= (math.pi / 180.0)
    p = vals[0] * math.cos(vals[1])
    q = vals[0] * math.sin(vals[1])
  elif 'r' in arg:
    p = vals[0] * math.cos(vals[1])
    q = vals[0] * math.sin(vals[1])
  else:
    p = vals[0]
    q = vals[1]

  if 'KVA' in arg:
    p /= 1000.0
    q /= 1000.0
  elif 'MVA' in arg:
    p *= 1.0
    q *= 1.0
  else:  # VA
    p /= 1000000.0
    q /= 1000000.0

  return p, q

def main_loop():
  if len(sys.argv) == 2:
    rootname = sys.argv[1]
  else:
    print ('usage: python fncsPYPOWER.py rootname')
    sys.exit()

  ppc = ppcasefile()
  StartTime = ppc['StartTime']
  tmax = int(ppc['Tmax'])
  period = int(ppc['Period'])
  dt = int(ppc['dt'])
  make_dictionary(ppc, rootname)

  bus_mp = open ("bus_" + rootname + "_metrics.json", "w")
  gen_mp = open ("gen_" + rootname + "_metrics.json", "w")
  sys_mp = open ("sys_" + rootname + "_metrics.json", "w")
  bus_meta = {'LMP_P':{'units':'USD/kwh','index':0},'LMP_Q':{'units':'USD/kvarh','index':1},
    'PD':{'units':'MW','index':2},'QD':{'units':'MVAR','index':3},'Vang':{'units':'deg','index':4},
    'Vmag':{'units':'pu','index':5},'Vmax':{'units':'pu','index':6},'Vmin':{'units':'pu','index':7}}
  gen_meta = {'Pgen':{'units':'MW','index':0},'Qgen':{'units':'MVAR','index':1},'LMP_P':{'units':'USD/kwh','index':2}}
  sys_meta = {'Ploss':{'units':'MW','index':0},'Converged':{'units':'true/false','index':1}}
  bus_metrics = {'Metadata':bus_meta,'StartTime':StartTime}
  gen_metrics = {'Metadata':gen_meta,'StartTime':StartTime}
  sys_metrics = {'Metadata':sys_meta,'StartTime':StartTime}

  gencost = ppc['gencost']
  fncsBus = ppc['FNCS']
  ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=1)
  ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=0)
  loads = np.loadtxt('NonGLDLoad.txt', delimiter=',')

  for row in ppc['UnitsOut']:
    print ('unit  ', row[0], 'off from', row[1], 'to', row[2], flush=True)
  for row in ppc['BranchesOut']:
    print ('branch', row[0], 'out from', row[1], 'to', row[2], flush=True)

  nloads = loads.shape[0]
  ts = 0
  tnext_opf = -dt

  op = open (rootname + '.csv', 'w')
  print ('t[s],Converged,Pload,P7 (csv), GLD Unresp, P7 (opf), Resp (opf), GLD Pub, BID?, P7 Min, V7,LMP_P7,LMP_Q7,Pgen1,Pgen2,Pgen3,Pgen4,Pdisp, gencost2, gencost1, gencost0', file=op, flush=True)
  fncs.initialize()

  # transactive load components
  csv_load = 0
  scaled_unresp = 0
  scaled_resp = 0
  resp_c0 = 0
  resp_c1 = 0
  resp_c2 = 0
  resp_max = 0
  gld_load = 0 # this is the actual
  actual_load = 0

  while ts <= tmax:
    # start by getting the latest inputs from GridLAB-D and the auction
    events = fncs.get_events()
    new_bid = False
    for key in events:
      topic = key.decode()
      if topic == 'UNRESPONSIVE_KW':
        unresp_load = 0.001 * float(fncs.get_value(key).decode())
        fncsBus[0][3] = unresp_load # poke unresponsive estimate into the bus load slot
        new_bid = True
      elif topic == 'RESPONSIVE_MAX_KW':
        resp_max = 0.001 * float(fncs.get_value(key).decode()) # in MW
        new_bid = True
      elif topic == 'RESPONSIVE_M':
        resp_c2 = -1e6 * float(fncs.get_value(key).decode())
        new_bid = True
      elif topic == 'RESPONSIVE_B':
        resp_c1 = 1e3 * float(fncs.get_value(key).decode())
        new_bid = True
      elif topic == 'RESPONSIVE_BB':
        resp_c0 = -float(fncs.get_value(key).decode())
        new_bid = True
      elif topic == 'UNRESPONSIVE_PRICE': # not actually used
        unresp_price = float(fncs.get_value(key).decode())
        new_bid = True
      else:
        gld_load = parse_mva (fncs.get_value(key).decode()) # actual value, may not match unresp + resp load
        actual_load = float(gld_load[0]) * float(fncsBus[0][2])
    if new_bid == True:
      print('**Bid', ts, unresp_load, resp_max, resp_c2, resp_c1, resp_c0)

    # update the case for bids, outages and CSV loads
    idx = int ((ts + dt) / period) % nloads
    bus = ppc['bus']
    gen = ppc['gen']
    branch = ppc['branch']
    gencost = ppc['gencost']
    csv_load = loads[idx,0]
    bus[4,2] = loads[idx,1]
    bus[8,2] = loads[idx,2]
    # process the generator and branch outages
    for row in ppc['UnitsOut']:
      if ts >= row[1] and ts <= row[2]:
        gen[row[0],7] = 0
      else:
        gen[row[0],7] = 1
    for row in ppc['BranchesOut']:
      if ts >= row[1] and ts <= row[2]:
        branch[row[0],10] = 0
      else:
        branch[row[0],10] = 1
    bus[6,2] = csv_load
    for row in ppc['FNCS']:
      scaled_unresp = float(row[2]) * float(row[3])
      newidx = int(row[0]) - 1
      bus[newidx,2] += scaled_unresp
    gen[4][9] = -resp_max * float(fncsBus[0][2])
    gencost[4][3] = 3
    gencost[4][4] = resp_c2
    gencost[4][5] = resp_c1
    gencost[4][6] = resp_c0

    if ts >= tnext_opf:  # expecting to solve opf one dt before the market clearing period ends, so GridLAB-D has time to use it
      res = pp.runopf(ppc, ppopt_market)
      bus = res['bus']
      gen = res['gen']
      lmp = 0.001 * bus[6,13]
      pgen1 = gen[0,1]
      pgen2 = gen[1,1]
      pgen3 = gen[2,1]
      pgen4 = gen[3,1]
      fncs.publish('LMP_B7', lmp)
      print ("** OPF", ts, lmp, pgen1, pgen2, pgen3, pgen4, gen[4, 1])
      tnext_opf += period
    
    # always update the electrical quantities with a regular power flow
    bus = ppc['bus']
    gen = ppc['gen']
    bus[6,13] = 1000.0 * lmp
    gen[0,1] = pgen1
    gen[1,1] = pgen2
    gen[2,1] = pgen3
    gen[3,1] = pgen4
    rpf = pp.runpf(ppc, ppopt_regular)
    bus = rpf[0]['bus']
    gen = rpf[0]['gen']
    print ("    PF", ts, 0.001 * bus[6, 13], gen[0, 1], gen[1, 1], gen[2, 1], gen[3, 1], gen[4, 1])
    
    Pload = bus[:,2].sum()
    Pgen = gen[:,1].sum()
    Ploss = Pgen - Pload
    scaled_resp = -1.0 * gen[4,1]

#    if ts == 3597:
#      print (ts, '** OPF Gen =', res['gen'])
#      print (ts, '** OPF Bus =', res['bus'])
#      print (ts, '**  PF Gen =', rpf[0]['gen'])
#      print (ts, '**  PF Bus =', rpf[0]['bus'])
#      print (ts, 'LMP', lmp)

    # update the metrics
    sys_metrics[str(ts)] = {rootname:[Ploss,res['success']]}
    bus_metrics[str(ts)] = {}
    for i in range (fncsBus.shape[0]):
      busnum = int(fncsBus[i,0])
      busidx = busnum - 1
      row = bus[busidx].tolist()
      bus_metrics[str(ts)][str(busnum)] = [row[13]*0.001,row[14]*0.001,row[2],row[3],row[8],row[7],row[11],row[12]]
    gen_metrics[str(ts)] = {}
    for i in range (gen.shape[0]):
      row = gen[i].tolist()
      busidx = int(row[0] - 1)
      gen_metrics[str(ts)][str(i+1)] = [row[1],row[2],float(bus[busidx,13])*0.001]

    volts = 1000.0 * bus[6,7] * bus[6,9]
    fncs.publish('three_phase_voltage_B7', volts)

    # CSV file output
    print (ts, res['success'], 
           '{:.3f}'.format(bus[:,2].sum()), # Pload
           '{:.3f}'.format(csv_load),       # P7 (csv)
           '{:.3f}'.format(scaled_unresp),  # GLD Unresp
           '{:.3f}'.format(bus[6,2]),       # P7 (opf)
           '{:.3f}'.format(scaled_resp),    # Resp (opf)  0
           '{:.3f}'.format(actual_load),    # GLD Pub
           new_bid, 
           '{:.3f}'.format(gen[4,9]),       # P7 Min      0
           '{:.3f}'.format(bus[6,7]),       # V7
           '{:.3f}'.format(bus[6,13]),      # LMP_P7      0
           '{:.3f}'.format(bus[6,14]),      # LMP_Q7      0
           '{:.2f}'.format(gen[0,1]),       # Pgen1
           '{:.2f}'.format(gen[1,1]),       # Pgen2 
           '{:.2f}'.format(gen[2,1]),       # Pgen3
           '{:.2f}'.format(gen[3,1]),       # Pgen4       0
           '{:.2f}'.format(res['gen'][4, 1]),      # Pdisp   0
           '{:.6f}'.format(ppc['gencost'][4, 4]),  # gencost2
           '{:.4f}'.format(ppc['gencost'][4, 5]),  # gencost1 
           '{:.4f}'.format(ppc['gencost'][4, 6]),  # gencost0
           sep=',', file=op, flush=True)

    # request the next time step
    ts = fncs.time_request(ts + dt)
    if ts > tmax:
      print ('breaking out at',ts,flush=True)
      break

#  spio.savemat('matFile.mat', saveDataDict)
  # ===================================
  print ('writing metrics', flush=True)
  print (json.dumps(bus_metrics), file=bus_mp, flush=True)
  print (json.dumps(gen_metrics), file=gen_mp, flush=True)
  print (json.dumps(sys_metrics), file=sys_mp, flush=True)
  print ('closing files', flush=True)
  bus_mp.close()
  gen_mp.close()
  sys_mp.close()
  op.close()
  print ('finalizing FNCS', flush=True)
  fncs.finalize()

main_loop()

#with warnings.catch_warnings():
#  warnings.simplefilter("ignore") # TODO - pypower is using NumPy doubles for integer indices

#  profiler = cProfile.Profile ()
#  profiler.runcall (main_loop)
#  stats = pstats.Stats(profiler)
#  stats.strip_dirs()
#  stats.sort_stats('cumulative')
#  stats.print_stats()
