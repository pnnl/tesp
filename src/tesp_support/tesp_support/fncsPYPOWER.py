# Copyright (C) 2017-2020 Battelle Memorial Institute
# file: fncsPYPOWER.py
""" PYPOWER solutions under control of FNCS or HELICS for te30 and sgip1 examples

Public Functions:
    :pypower_loop: Initializes and runs the simulation.  
"""
import json
import sys
import warnings
import csv
try:
  import tesp_support.fncs as fncs
except:
  pass
try:
  import helics
except:
  pass
import numpy as np
import pypower.api as pp
from math import sqrt
import math
import re
from copy import deepcopy
import tesp_support.helpers as helpers
#import cProfile
#import pstats
if sys.platform != 'win32':
  import resource

def summarize_opf(res):
  """ Helper function to print optimal power flow solution (debugging)

  Args:
    res (dict): solved PYPOWER case structure
  """
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

def load_json_case(fname):
  """ Helper function to load PYPOWER case from a JSON file

  Args:
    fname (str): the JSON file to open

  Returns:
    dict: the loaded PYPOWER case structure
  """
  lp = open (fname, encoding='utf-8').read()
  ppc = json.loads(lp)
  ppc['bus'] = np.array (ppc['bus'])
  ppc['gen'] = np.array (ppc['gen'])
  ppc['branch'] = np.array (ppc['branch'])
  ppc['areas'] = np.array (ppc['areas'])
  ppc['gencost'] = np.array (ppc['gencost'])
  ppc['DSO'] = np.array (ppc['DSO'])
  ppc['UnitsOut'] = np.array (ppc['UnitsOut'])
  ppc['BranchesOut'] = np.array (ppc['BranchesOut'])
  return ppc

def make_dictionary(ppc, rootname):
  """ Helper function to write the JSON metafile for post-processing

  Args:
    ppc (dict): PYPOWER case file structure
    rootname (str): to write rootname_m_dict.json
  """
  dsoBuses = {}
  generators = {}
  unitsout = []
  branchesout = []
  bus = ppc['bus']
  gen = ppc['gen']
  cost = ppc['gencost']
  dsoBus = ppc['DSO']
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

  for i in range (dsoBus.shape[0]):
    busnum = int(dsoBus[i,0])
    busidx = busnum - 1
    dsoBuses[str(busnum)] = {'Pnom':float(bus[busidx,2]),'Qnom':float(bus[busidx,3]),'area':int(bus[busidx,6]),'zone':int(bus[busidx,10]),
      'ampFactor':float(dsoBus[i,2]),'GLDsubstations':[dsoBus[i,1]]}

  for i in range (units.shape[0]):
    unitsout.append ({'unit':int(units[i,0]),'tout':int(units[i,1]),'tin':int(units[i,2])})

  for i in range (branches.shape[0]):
    branchesout.append ({'branch':int(branches[i,0]),'tout':int(branches[i,1]),'tin':int(branches[i,2])})

  dp = open (rootname + "_m_dict.json", "w")
  ppdict = {'baseMVA':ppc['baseMVA'],'dsoBuses':dsoBuses,'generators':generators,'UnitsOut':unitsout,'BranchesOut':branchesout}
  json.dump (ppdict, dp, ensure_ascii=False, indent=2)
  dp.close()

def parse_mva(arg):
  """ Helper function to parse P+jQ from a FNCS value

  Args:
    arg (str): FNCS value in rectangular format

  Returns:
    float, float: P [MW] and Q [MVAR]
  """
  tok = arg.strip('; MWVAKdrij')
  bLastDigit = False
  bParsed = False
  vals = [0.0,0.0]
  for i in range(len(tok)):
    if tok[i] == '+' or tok[i] == '-':
      if bLastDigit:
        vals[0] = float(tok[:i])
        vals[1] = float(tok[i:])
        bParsed = True
        break
    bLastDigit = tok[i].isdigit()
  if not bParsed:
    vals[0] = float(tok)

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

def pypower_loop (casefile, rootname, helicsConfig=None):
  """ Public function to start PYPOWER solutions under control of FNCS or HELICS

  The time step, maximum time, and other data must be set up in a JSON file.
  This function will run the case under FNCS, manage the FNCS message traffic,
  and shutdown FNCS upon completion. Five files are written:

  - *rootname.csv*; intermediate solution results during simulation
  - *rootname_m_dict.json*; metadata for post-processing
  - *bus_rootname_metrics.json*; bus metrics for GridLAB-D connections, upon completion
  - *gen_rootname_metrics.json*; bulk system generator metrics, upon completion
  - *sys_rootname_metrics.json*; bulk system-level metrics, upon completion

  Args:
    casefile (str): the configuring JSON file name, without extension
    rootname (str): the root filename for metrics output, without extension
  """

  ppc = load_json_case (casefile)
  StartTime = ppc['StartTime']
  tmax = int(ppc['Tmax'])
  period = int(ppc['Period'])
  dt = int(ppc['dt'])
  make_dictionary (ppc, rootname)

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
  dsoBus = ppc['DSO']
  gen = ppc['gen']
  pf_dc = ppc['pf_dc']
  PswingSwitch = 180.0 # if Gen 2 gets close to the max, change swing bus
  if pf_dc > 0:
    PswingSwitch = 191.0
  ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'])
  ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'])
  loads = np.loadtxt(ppc['CSVFile'], delimiter=',')

  for row in ppc['UnitsOut']:
    print ('unit  ', row[0], 'off from', row[1], 'to', row[2], flush=True)
  for row in ppc['BranchesOut']:
    print ('branch', row[0], 'out from', row[1], 'to', row[2], flush=True)

  nloads = loads.shape[0]
  ts = 0
  tnext_opf = -dt

  # initializing for metrics collection
  tnext_metrics = 0
  loss_accum = 0
  conv_accum = True
  n_accum = 0
  bus_accum = {}
  gen_accum = {}
  for i in range (dsoBus.shape[0]):
    busnum = int(dsoBus[i,0])
    bus_accum[str(busnum)] = [0,0,0,0,0,0,0,99999.0]
  for i in range (gen.shape[0]):
    gen_accum[str(i+1)] = [0,0,0]

  op = open (rootname + '.csv', 'w')
  print ('t[s],Converged,Pload,P7 (csv),Unresp (opf),P7 (rpf),Resp (opf),GLD Pub,BID?,P7 Min,V7,LMP_P7,LMP_Q7,Pgen1,Pgen2,Pgen3,Pgen4,Pdisp,Deg,c2,c1', file=op, flush=True)

  hFed = None
  pub_lmp = None
  pub_volts = None
  sub_load = None
  sub_unresp = None
  sub_max = None
  sub_c2 = None
  sub_c1 = None
  sub_deg = None
  if helicsConfig is not None:
    hFed = helics.helicsCreateValueFederateFromConfig(helicsConfig)
    fedName = helics.helicsFederateGetName(hFed)
    pubCount = helics.helicsFederateGetPublicationCount(hFed)
    subCount = helics.helicsFederateGetInputCount(hFed)
    for i in range(pubCount):
      pub = helics.helicsFederateGetPublicationByIndex(hFed, i)
      key = helics.helicsPublicationGetKey (pub)
      print ('HELICS publication key', i, key)
      if 'LMP_' in key:
        pub_lmp = pub
      elif 'three_phase_voltage_' in key:
        pub_volts = pub
    for i in range(subCount):
      sub = helics.helicsFederateGetInputByIndex(hFed, i)
      key = helics.helicsInputGetKey(sub)
      target = helics.helicsSubscriptionGetKey(sub)
      print ('HELICS subscription key', i, key, 'target', target)
      upper_target = target.upper() # FNCS-compatible matching
      if 'RESPONSIVE_C2' in upper_target:
        sub_c2 = sub
      if 'RESPONSIVE_C1' in upper_target:
        sub_c1 = sub
      if 'RESPONSIVE_DEG' in upper_target:
        sub_deg = sub
      if 'RESPONSIVE_MAX_MW' in upper_target:
        sub_max = sub
      if 'UNRESPONSIVE_MW' in upper_target:
        sub_unresp = sub
      if 'distribution_load' in target:
        sub_load = sub
    helics.helicsFederateEnterExecutingMode(hFed)
  else:
    fncs.initialize()

  # transactive load components
  csv_load = 0     # from the file
  unresp = 0       # unresponsive load estimate from the auction agent
  resp = 0         # will be the responsive load as dispatched by OPF
  resp_deg = 0     # RESPONSIVE_DEG from DSO
  resp_c1 = 0      # RESPONSIVE_C1 from DSO
  resp_c2 = 0      # RESPONSIVE_C2 from DSO
  resp_max = 0     # RESPONSIVE_MAX_MW from DSO
  feeder_load = 0  # amplified feeder MW

  while ts <= tmax:
    # start by getting the latest inputs from GridLAB-D and the auction
    new_bid = False
    load_scale = float (dsoBus[0][2])
    # some notes on helicsInput timing
    #  1) initial values are garbage until the other federate actually publishes
    #  2) helicsInputIsValid checks the subscription pipeline for validity, but not the value
    #  3) helicsInputIsUpdated resets to False immediately after you read the value, will become True if value changes later
    #  4) helicsInputLastUpdateTime is > 0 only after the other federate published its first value
    if hFed is not None: # HELICS inputs
      if (sub_unresp is not None) and helics.helicsInputIsUpdated(sub_unresp):
        unresp = helics.helicsInputGetDouble(sub_unresp) * load_scale
        dsoBus[0][3] = unresp # to poke unresponsive estimate into the bus load slot
      if (sub_c2 is not None) and helics.helicsInputIsUpdated(sub_c2):
        resp_c2 = helics.helicsInputGetDouble(sub_c2) / load_scale
      if (sub_c1 is not None) and helics.helicsInputIsUpdated(sub_c1):
        resp_c1 = helics.helicsInputGetDouble(sub_c1)
      if (sub_deg is not None) and helics.helicsInputIsUpdated(sub_deg):
        resp_deg = helics.helicsInputGetInteger(sub_deg)
      if (sub_max is not None) and helics.helicsInputIsUpdated(sub_max):
#        print (ts,'resp_max updated before', helics.helicsInputIsUpdated(sub_max))
        resp_max = helics.helicsInputGetComplex(sub_max)[0] * load_scale
#        print (ts,'resp_max updated after', helics.helicsInputIsUpdated(sub_max))
        new_bid = True
      if (sub_load is not None) and helics.helicsInputIsUpdated(sub_load):
        gld_load = helics.helicsInputGetComplex(sub_load)
        feeder_load = gld_load[0] * load_scale / 1.0e6
#      print ('HELICS inputs at', ts, feeder_load, load_scale, unresp, resp_max, resp_c2, resp_c1, resp_deg, new_bid)
#      print ('HELICS resp_max', ts, resp_max, helics.helicsInputIsValid(sub_max), 
#        helics.helicsInputIsUpdated(sub_max), helics.helicsInputLastUpdateTime(sub_max))
    else:  # inputs coming from FNCS
      events = fncs.get_events()
      for topic in events:
        value = fncs.get_value(topic)
        if topic == 'UNRESPONSIVE_MW':
          unresp = load_scale * float(value)
          dsoBus[0][3] = unresp # to poke unresponsive estimate into the bus load slot
          new_bid = True
        elif topic == 'RESPONSIVE_MAX_MW':
          resp_max = load_scale * float(value)
          new_bid = True
        elif topic == 'RESPONSIVE_C2':
          resp_c2 = float(value) / load_scale
          new_bid = True
        elif topic == 'RESPONSIVE_C1':
          resp_c1 = float(value)
          new_bid = True
        elif topic == 'RESPONSIVE_DEG':
          resp_deg = int(value)
          new_bid = True
        else:
          gld_load = parse_mva (value) # actual value, may not match unresp + resp load
          feeder_load = float(gld_load[0]) * load_scale
    if new_bid == True:
      dummy = 2
#      print('**Bid', ts, unresp, resp_max, resp_deg, resp_c2, resp_c1)

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

    if resp_deg == 2:
      gencost[4][3] = 3
      gencost[4][4] = -resp_c2
      gencost[4][5] = resp_c1
    elif resp_deg == 1:
      gencost[4][3] = 2
      gencost[4][4] = resp_c1
      gencost[4][5] = 0.0
    else:
      gencost[4][3] = 1
      gencost[4][4] = 999.0
      gencost[4][5] = 0.0
    gencost[4][6] = 0.0

    if ts >= tnext_opf:  # expecting to solve opf one dt before the market clearing period ends, so GridLAB-D has time to use it
      # for OPF, the DSO bus load is CSV + Unresponsive estimate, with Responsive separately dispatchable
      bus = ppc['bus']
      gen = ppc['gen']
      bus[6,2] = csv_load
      for row in ppc['DSO']:
        unresp = float(row[3])
        newidx = int(row[0]) - 1
        if unresp >= feeder_load:
          bus[newidx,2] += unresp
        else:
          bus[newidx,2] += feeder_load
      gen[4][9] = -resp_max
      res = pp.runopf(ppc, ppopt_market)
      if res['success'] == False:
        conv_accum = False
      opf_bus = deepcopy (res['bus'])
      opf_gen = deepcopy (res['gen'])
      lmp = opf_bus[6,13]
      resp = -1.0 * opf_gen[4,1]
      if pub_lmp is not None:
        helics.helicsPublicationPublishDouble(pub_lmp, 0.001 * lmp)
      else:
        fncs.publish('LMP_B7', 0.001 * lmp) # publishing $/kwh
#     print ('  OPF', ts, csv_load, '{:.3f}'.format(unresp), '{:.3f}'.format(resp),
#            '{:.3f}'.format(feeder_load), '{:.3f}'.format(opf_bus[6,2]),
#            '{:.3f}'.format(opf_gen[0,1]), '{:.3f}'.format(opf_gen[1,1]), '{:.3f}'.format(opf_gen[2,1]),
#            '{:.3f}'.format(opf_gen[3,1]), '{:.3f}'.format(opf_gen[4,1]), '{:.3f}'.format(lmp))
      # if unit 2 (the normal swing bus) is dispatched at max, change the swing bus to 9
      if opf_gen[1,1] >= PswingSwitch:
        ppc['bus'][1,1] = 2
        ppc['bus'][8,1] = 3
        print ('  Switching to SWING Bus 9 (Gen 4) at {:d} and {:.2f} MW'.format (ts, opf_gen[1,1]))
      else:
        ppc['bus'][1,1] = 3
        ppc['bus'][8,1] = 1
        print ('  Keeping SWING Bus 2 (Gen 2) at {:d} and {:.2f} MW'.format (ts, opf_gen[1,1]))
      tnext_opf += period
    
    # always update the electrical quantities with a regular power flow
    bus = ppc['bus']
    gen = ppc['gen']
    bus[6,13] = lmp
    gen[0,1] = opf_gen[0, 1]
    gen[1,1] = opf_gen[1, 1]
    gen[2,1] = opf_gen[2, 1]
    gen[3,1] = opf_gen[3, 1]
    # during regular power flow, we use the actual CSV + feeder load, ignore dispatchable load and use actual
    bus[6,2] = csv_load + feeder_load
    gen[4,1] = 0 # opf_gen[4, 1]
    gen[4,9] = 0
    rpf = pp.runpf(ppc, ppopt_regular)
    if rpf[0]['success'] == False:
      conv_accum = False
    bus = rpf[0]['bus']
    gen = rpf[0]['gen']
    
    Pload = bus[:,2].sum()
    Pgen = gen[:,1].sum()
    Ploss = Pgen - Pload

    # update the metrics
    n_accum += 1
    loss_accum += Ploss
    for i in range (dsoBus.shape[0]):
      busnum = int(dsoBus[i,0])
      busidx = busnum - 1
      row = bus[busidx].tolist()
      # LMP_P, LMP_Q, PD, QD, Vang, Vmag, Vmax, Vmin: row[11] and row[12] are Vmax and Vmin constraints
      PD = row[2] + resp # the ERCOT version shows how to track scaled_resp separately for each DSO bus
      Vpu = row[7]
      bus_accum[str(busnum)][0] += row[13]*0.001
      bus_accum[str(busnum)][1] += row[14]*0.001
      bus_accum[str(busnum)][2] += PD
      bus_accum[str(busnum)][3] += row[3]
      bus_accum[str(busnum)][4] += row[8]
      bus_accum[str(busnum)][5] += Vpu
      if Vpu > bus_accum[str(busnum)][6]:
        bus_accum[str(busnum)][6] = Vpu
      if Vpu < bus_accum[str(busnum)][7]:
        bus_accum[str(busnum)][7] = Vpu
    for i in range (gen.shape[0]):
      row = gen[i].tolist()
      busidx = int(row[0] - 1)
      # Pgen, Qgen, LMP_P  (includes the responsive load as dispatched by OPF)
      gen_accum[str(i+1)][0] += row[1]
      gen_accum[str(i+1)][1] += row[2]
      gen_accum[str(i+1)][2] += float(opf_bus[busidx,13])*0.001

    # write the metrics
    if ts >= tnext_metrics:
      sys_metrics[str(ts)] = {rootname:[loss_accum / n_accum,conv_accum]}

      bus_metrics[str(ts)] = {}
      for i in range (dsoBus.shape[0]):
        busnum = int(dsoBus[i,0])
        busidx = busnum - 1
        row = bus[busidx].tolist()
        met = bus_accum[str(busnum)]
        bus_metrics[str(ts)][str(busnum)] = [met[0]/n_accum, met[1]/n_accum, met[2]/n_accum, met[3]/n_accum,
                                             met[4]/n_accum, met[5]/n_accum, met[6], met[7]]
        bus_accum[str(busnum)] = [0,0,0,0,0,0,0,99999.0]

      gen_metrics[str(ts)] = {}
      for i in range (gen.shape[0]):
        met = gen_accum[str(i+1)]
        gen_metrics[str(ts)][str(i+1)] = [met[0]/n_accum, met[1]/n_accum, met[2]/n_accum]
        gen_accum[str(i+1)] = [0,0,0]

      tnext_metrics += period
      n_accum = 0
      loss_accum = 0
      conv_accum = True

    volts = 1000.0 * bus[6,7] * bus[6,9] / sqrt(3.0)  # VLN for GridLAB-D
    if pub_volts is not None:
      helics.helicsPublicationPublishDouble(pub_volts, volts)
    else:
      fncs.publish('three_phase_voltage_B7', volts)

    # CSV file output
    print (ts, res['success'], 
           '{:.3f}'.format(Pload),          # Pload
           '{:.3f}'.format(csv_load),       # P7 (csv)
           '{:.3f}'.format(unresp),         # GLD Unresp
           '{:.3f}'.format(bus[6,2]),       # P7 (rpf)
           '{:.3f}'.format(resp),           # Resp (opf)
           '{:.3f}'.format(feeder_load),    # GLD Pub
           new_bid, 
           '{:.3f}'.format(gen[4,9]),       # P7 Min
           '{:.3f}'.format(bus[6,7]),       # V7
           '{:.3f}'.format(bus[6,13]),      # LMP_P7
           '{:.3f}'.format(bus[6,14]),      # LMP_Q7
           '{:.2f}'.format(gen[0,1]),       # Pgen1
           '{:.2f}'.format(gen[1,1]),       # Pgen2 
           '{:.2f}'.format(gen[2,1]),       # Pgen3
           '{:.2f}'.format(gen[3,1]),       # Pgen4
           '{:.2f}'.format(res['gen'][4, 1]), # Pdisp
           '{:.4f}'.format(resp_deg),       # degree
           '{:.8f}'.format(ppc['gencost'][4, 4]),  # c2
           '{:.8f}'.format(ppc['gencost'][4, 5]),  # c1 
           sep=',', file=op, flush=True)

    # request the next time step, if necessary
    if ts >= tmax:
      print ('breaking out at',ts,flush=True)
      break
    tRequest = min(ts + dt, tmax)
    if hFed is not None:
      ts = int (helics.helicsFederateRequestTime(hFed, tRequest))
    else:
      ts = fncs.time_request(tRequest)

  # ===================================
  print ('writing metrics', flush=True)
  print (json.dumps(sys_metrics), file=sys_mp, flush=True)
  print (json.dumps(bus_metrics), file=bus_mp, flush=True)
  print (json.dumps(gen_metrics), file=gen_mp, flush=True)
  print ('closing files', flush=True)
  bus_mp.close()
  gen_mp.close()
  sys_mp.close()
  op.close()
  if hFed is not None:
    helpers.stop_helics_federate (hFed)
  else:
    print ('finalizing DSO', flush=True)
    fncs.finalize()

  if sys.platform != 'win32':
    usage = resource.getrusage(resource.RUSAGE_SELF)
    RESOURCES = [
      ('ru_utime', 'User time'),
      ('ru_stime', 'System time'),
      ('ru_maxrss', 'Max. Resident Set Size'),
      ('ru_ixrss', 'Shared Memory Size'),
      ('ru_idrss', 'Unshared Memory Size'),
      ('ru_isrss', 'Stack Size'),
      ('ru_inblock', 'Block inputs'),
      ('ru_oublock', 'Block outputs')]
    print('Resource usage:')
    for name, desc in RESOURCES:
      print('  {:<25} ({:<10}) = {}'.format(desc, name, getattr(usage, name)))

# main_loop()
#  profiler = cProfile.Profile ()
#  profiler.runcall (main_loop)
#  stats = pstats.Stats(profiler)
#  stats.strip_dirs()
#  stats.sort_stats('cumulative')
#  stats.print_stats()
