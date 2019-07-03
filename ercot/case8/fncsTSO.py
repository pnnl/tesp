import numpy as np;
import scipy.interpolate as ip;
import pypower.api as pp;
import tesp_support.api as tesp;
import tesp_support.fncs as fncs
import json;
import math;
from copy import deepcopy;

# day-ahead market runs at noon every day
da_period = 86400
da_offset = 12 * 3600

casename = 'ercot_8'
wind_period = 3600

#for initial load_shape scale 1.3write_ames_base_case

load_shape = [0.6704, 
              0.6303, 
              0.6041, 
              0.5902, 
              0.5912, 
              0.6094, 
              0.6400, 
              0.6725, 
              0.7207, 
              0.7584, 
              0.7905, 
              0.8171, 
              0.8428, 
              0.8725, 
              0.9098, 
              0.9480, 
              0.9831, 
              1.0000, 
              0.9868, 
              0.9508, 
              0.9306, 
              0.8999, 
              0.8362, 
              0.7695, 
              0.6704]  # wrap to the next day


# from 'ARIMA-Based Time Series Model of Stochastic Wind Power Generation'
# return dict with rows like wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, p]
def make_wind_plants(): 
  plants = {}
  Pnorm = 165.6  
  for i in range(gen.shape[0]): 
    busnum = int(gen[i, 0])
    c2 = float(genCost[i, 4])
    if c2 < 2e-5:  # genfuel would be 'wind'
      MW = float(gen[i, 8])
      scale = MW / Pnorm
      Theta0 = 0.05 * math.sqrt(scale)
      Theta1 = -0.1 *(scale)
      StdDev = math.sqrt(1.172 * math.sqrt(scale))
      Psi1 = 1.0
      Ylim = math.sqrt(MW)
      alag = Theta0
      ylag = Ylim
      plants[str(i)] = [busnum, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, MW]
  return plants


# this differs from tesp_support because of additions to FNCS, and Pnom==>Pmin for generators
def make_dictionary(ppc, rootname): 
  fncsBuses = {}
  generators = {}
  unitsout = []
  branchesout = []
#  bus = ppc['bus']
#  gen = ppc['gen']
#  cost = ppc['gencost']
#  fncsBus = ppc['FNCS']
#  units = ppc['UnitsOut']
#  branches = ppc['BranchesOut']

  for i in range(gen.shape[0]): 
    busnum = int(gen[i, 0])
    bustype = bus[busnum-1, 1]
    if bustype == 1: 
      bustypename = 'pq'
    elif bustype == 2: 
      bustypename = 'pv'
    elif bustype == 3: 
      bustypename = 'swing'
    else: 
      bustypename = 'unknown'
    gentype = 'other'  # as opposed to simple cycle or combined cycle
    c2 = float(genCost[i, 4])
    c1 = float(genCost[i, 5])
    c0 = float(genCost[i, 6])
    if c2 < 2e-5:  # assign fuel types from the IA State default costs
      genfuel = 'wind'
    elif c2 < 0.0003: 
      genfuel = 'nuclear'
    elif c1 < 25.0: 
      genfuel = 'coal'
    else: 
      genfuel = 'gas'
    generators[str(i+1)] = {'bus': int(busnum), 'bustype': bustypename, 'Pmin': float(gen[i, 9]), 'Pmax': float(gen[i, 8]), 'genfuel': genfuel, 'gentype': gentype, 
      'StartupCost': float(genCost[i, 1]), 'ShutdownCost': float(genCost[i, 2]), 'c2': c2, 'c1': c1, 'c0': c0}

  for i in range(fncsBus.shape[0]): 
    busnum = int(fncsBus[i, 0])
    busidx = busnum - 1
    fncsBuses[str(busnum)] = {'Pnom': float(bus[busidx, 2]), 'Qnom': float(bus[busidx, 3]), 'area': int(bus[busidx, 6]), 'zone': int(bus[busidx, 10]), 
      'ampFactor': float(fncsBus[i, 2]), 'GLDsubstations': [fncsBus[i, 1]], 'curveScale': float(fncsBus[i, 5]), 'curveSkew': int(fncsBus[i, 6])}

  for i in range(units.shape[0]): 
    unitsout.append({'unit': int(units[i, 0]), 'tout': int(units[i, 1]), 'tin': int(units[i, 2])})

  for i in range(branches.shape[0]): 
    branchesout.append({'branch': int(branches[i, 0]), 'tout': int(branches[i, 1]), 'tin': int(branches[i, 2])})

  dp = open(rootname + '_m_dict.json', 'w')
  ppdict = {'baseMVA': ppc['baseMVA'], 'fncsBuses': fncsBuses, 'generators': generators, 'UnitsOut': unitsout, 'BranchesOut': branchesout}
  print(json.dumps(ppdict), file=dp, flush=True)
  dp.close()


def parse_mva(arg): 
  tok = arg.strip('; MWVAKdrij')
  bLastDigit = False
  bParsed = False
  vals = [0.0, 0.0]
  for i in range(len(tok)): 
    if tok[i] == '+' or tok[i] == '-': 
      if bLastDigit: 
        vals[0] = float(tok[: i])
        vals[1] = float(tok[i: ])
        bParsed = True
        break
    bLastDigit = tok[i].isdigit()
  if not bParsed: 
    vals[0] = float(tok)

  if 'd' in arg: 
    vals[1] *=(math.pi / 180.0)
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


def print_gld_load(ppc, gld_load, msg, ts): 
  print(msg, 'at', ts)
  print('bus, genidx, pbus, qbus, pcrv, qcrv, pgld, qgld, unresp, resp_max, c2, c1, deg')
  for row in ppc['FNCS']: 
    busnum = int(row[0])
    gld_scale = float(row[2])
    pbus = bus[busnum-1, 2]
    qbus = bus[busnum-1, 3]
    pcrv = gld_load[busnum]['pcrv']
    qcrv = gld_load[busnum]['qcrv']
    pgld = gld_load[busnum]['p'] * gld_scale
    qgld = gld_load[busnum]['q'] * gld_scale
    resp_max = gld_load[busnum]['resp_max'] * gld_scale
    unresp = gld_load[busnum]['unresp'] * gld_scale
    c2 = gld_load[busnum]['c2'] / gld_scale
    c1 = gld_load[busnum]['c1']
    deg = gld_load[busnum]['deg']
    genidx = gld_load[busnum]['genidx']
    print(busnum, genidx, 
           '{: .2f}'.format(pbus), 
           '{: .2f}'.format(qbus), 
           '{: .2f}'.format(pcrv), 
           '{: .2f}'.format(qcrv), 
           '{: .2f}'.format(pgld), 
           '{: .2f}'.format(qgld), 
           '{: .2f}'.format(unresp), 
           '{: .2f}'.format(resp_max), 
           '{: .8f}'.format(c2), 
           '{: .8f}'.format(c1), 
           '{: .1f}'.format(deg))


def write_ames_base_case(ppc, fname): 
  fp = open(fname, 'w')
  print('// UNIT SI', file=fp)
  print('BASE_S 100', file=fp)   #TODO
  print('BASE_V 10', file=fp)    #TODO
  print('', file=fp)

  print('// Simulation Parameters', file=fp)
  print('MaxDay', 2, file=fp)     #TODO
  print('RTMDuration 12', file=fp)    #TODO
  print('RandomSeed 695672061', file=fp)
  print('// ThresholdProbability 0.999', file=fp)
  print('ReserveDownSystemPercent 0.2', file=fp)
  print('ReserveUpSystemPercent 0.3', file=fp)
  print('', file=fp)

  print('// Bus Data', file=fp)
  print('NumberofBuses', bus.shape[0], file=fp)
  print('NumberOfReserveZones', len(zones), file=fp)
  print('', file=fp)

  print('#ZoneDataStart', file=fp)
  print('// ZoneName   Buses   ReserveDownZonalPercent    ReserveUpZonalPercent', file=fp)
  for j in range(len(zones)): 
    name = 'Zone' + str(j + 1)
    buses = ''
    for i in range(bus.shape[0]): 
      if zones[j][0] == bus[i, 10]: 
        if buses == '': 
          buses = str(i+1)
        else: 
          buses = buses + ', ' + str(i+1)
    print(name, buses, '{: .1f}'.format(zones[j][2]), '{: .1f}'.format(zones[j][3]), file=fp)
  print('#ZoneDataEnd', file=fp)
  print('', file=fp)

  print('#LineDataStart', file=fp)
  print('// Name   From    To    MaxCap    Reactance', file=fp)
  # branch: fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
  # AMES wants branch name, from bus(< to bus), to bus, capacity(MVA), total X(pu)
  for i in range(branch.shape[0]): 
    name = 'Line' + str(i+1)
    if branch[i, 1] > branch[i, 0]: 
      fbus = int(branch[i, 0])
      tbus = int(branch[i, 1])
    else: 
      fbus = int(branch[i, 1])
      tbus = int(branch[i, 0])
    print(name, fbus, tbus, '{: .2f}'.format(branch[i, 5]), '{: .6f}'.format(branch[i, 3]), file=fp)
  print('#LineDataEnd', file=fp)
  print('', file=fp)

  print('#GenDataStart', file=fp)
  # TODO: replace ppc['gencost'] with dictionary of hourly bids, collected from the
  #   GridLAB-D agents over FNCS
  # TODO check units
  # gen: bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin,(11 zeros)
  # gencost: 2, startup, shutdown, 3, c2, c1, c0
  # AMES wants name, ID, bus, c0, c1, c2, capL, capU, InitMoney
  for i in range(gen.shape[0]): 
    name = 'Gen' + str(i+1)
    fbus = int(gen[i, 0])
    Pmax = gen[i, 8]
    Pmin = gen[i, 9]
    c0 = genCost[i, 6]
    c1 = genCost[i, 5]
    c2 = genCost[i, 4]
    InitMoney = 10000.0
    if Pmin > 0: 
      print(name, str(i+1), fbus, '{: .2f}'.format(c0), '{: .2f}'.format(c1), 
            '{: .6f}'.format(c2), '{: .2f}'.format(Pmin), '{: .2f}'.format(Pmax), 
            '{: .2f}'.format(InitMoney), file=fp)
  print('#GenDataEnd', file=fp)
  print('', file=fp)

  print('#LSEDataFixedDemandStart', file=fp)
  # ppc arrays(bus type 1=load, 2 = gen(PV) and 3 = swing)
  # bus: bus_i, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin
  # AMES wants name, ID, bus, 8x hourly demands, in three blocks
  # Define a dictionary of hourly load forecasts, collected from ppc
  #    GridLAB-D via FNCS, to replace ppc['bus']
  # TODO check units
  lse = []
  for i in range(bus.shape[0]): 
    Pd = pforecast[i]
    fbus = int(bus[i, 0])
    lse.append([fbus, Pd])
  print('// Name ID atBus H-00 H-01 H-02 H-03 H-04 H-05 H-06 H-07', file=fp)
  for i in range(len(lse)): 
    Pd = lse[i][1]
    print('LSE'+str(i+1), str(i+1), lse[i][0], '{: .2f}'.format(Pd[0]), '{: .2f}'.format(Pd[1]), 
           '{: .2f}'.format(Pd[2]), '{: .2f}'.format(Pd[3]), '{: .2f}'.format(Pd[4]), 
           '{: .2f}'.format(Pd[5]), '{: .2f}'.format(Pd[6]), '{: .2f}'.format(Pd[7]), file=fp)
  print('// Name ID atBus H-08 H-09 H-10 H-11 H-12 H-13 H-14 H-15', file=fp)
  for i in range(len(lse)): 
    Pd = lse[i][1]
    print('LSE'+str(i+1), str(i+1), lse[i][0], '{: .2f}'.format(Pd[8]), '{: .2f}'.format(Pd[9]), 
           '{: .2f}'.format(Pd[10]), '{: .2f}'.format(Pd[11]), '{: .2f}'.format(Pd[12]), 
           '{: .2f}'.format(Pd[13]), '{: .2f}'.format(Pd[14]), '{: .2f}'.format(Pd[15]), file=fp)
  print('// Name ID atBus H-16 H-17 H-18 H-19 H-20 H-21 H-22 H-23', file=fp)
  for i in range(len(lse)): 
    Pd = lse[i][1]
    print('LSE'+str(i+1), str(i+1), lse[i][0], '{: .2f}'.format(Pd[16]), '{: .2f}'.format(Pd[17]), 
           '{: .2f}'.format(Pd[18]), '{: .2f}'.format(Pd[19]), '{: .2f}'.format(Pd[20]), 
           '{: .2f}'.format(Pd[21]), '{: .2f}'.format(Pd[22]), '{: .2f}'.format(Pd[23]), file=fp)
  print('#LSEDataFixedDemandEnd', file=fp)
  fp.close()

#Initialize the program
x = np.array(range(25))
y = np.array(load_shape)
l = len(x)
t = np.linspace(0, 1, l-2, endpoint=True)
t = np.append([0, 0, 0], t)
t = np.append(t, [1, 1, 1])
tck_load=[t, [x, y], 3]
u3=np.linspace(0, 1, num=86400/300 + 1, endpoint=True)
newpts = ip.splev(u3, tck_load)

ppc = tesp.load_json_case(casename + '.json')
ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'])
ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'], PF_MAX_IT=20, PF_ALG=1)

StartTime = ppc['StartTime']
tmax = int(ppc['Tmax'])
period = int(ppc['Period'])
dt = int(ppc['dt'])
swing_bus = int(ppc['swing_bus'])
# these can be aliased by PYPOWER in runopf or runpf
bus = ppc['bus']
branch = ppc['branch']
gen = ppc['gen']
genCost = ppc['gencost']
# these were added to ppc by PNNL, and won't be aliased in PYPOWER
zones = ppc['zones']
fncsBus = ppc['FNCS']
units = ppc['UnitsOut']
branches = ppc['BranchesOut']

# ppc arrays(bus type 1=load, 2 = gen(PV) and 3 = swing)
# bus: bus id, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin
# zones: zone id, name, ReserveDownZonalPercent, ReserveUpZonalPercent
# branch: from bus, to bus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
# gen: bus id, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin,(11 zeros)
# gencost: 2, startup, shutdown, 3, c2, c1, c0
# FNCS: bus id, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit
# UnitsOut: idx, time out[s], time back in[s]
# BranchesOut: idx, time out[s], time back in[s]

#period = 300
#dt = 15

# initialize for metrics collection
bus_mp = open('bus_' + casename + '_metrics.json', 'w')
gen_mp = open('gen_' + casename + '_metrics.json', 'w')
sys_mp = open('sys_' + casename + '_metrics.json', 'w')
bus_meta = {'LMP_P': {'units': 'USD/kwh', 'index': 0}, 'LMP_Q': {'units': 'USD/kvarh', 'index': 1}, 
  'PD': {'units': 'MW', 'index': 2}, 'QD': {'units': 'MVAR', 'index': 3}, 'Vang': {'units': 'deg', 'index': 4}, 
  'Vmag': {'units': 'pu', 'index': 5}, 'Vmax': {'units': 'pu', 'index': 6}, 'Vmin': {'units': 'pu', 'index': 7}, 
  'unresp': {'units': 'MW', 'index': 8}, 'resp_max': {'units': 'MW', 'index': 9}, 
  'c1': {'units': '$/MW', 'index': 10}, 'c2': {'units': '$/MW^2', 'index': 11}}
gen_meta = {'Pgen': {'units': 'MW', 'index': 0}, 'Qgen': {'units': 'MVAR', 'index': 1}, 'LMP_P': {'units': 'USD/kwh', 'index': 2}}
sys_meta = {'Ploss': {'units': 'MW', 'index': 0}, 'Converged': {'units': 'true/false', 'index': 1}}
bus_metrics = {'Metadata': bus_meta, 'StartTime': StartTime}
gen_metrics = {'Metadata': gen_meta, 'StartTime': StartTime}
sys_metrics = {'Metadata': sys_meta, 'StartTime': StartTime}
make_dictionary(ppc, casename)

# initialize for variable wind
tnext_wind = tmax + 2 * dt # by default, never fluctuate the wind plants
if wind_period > 0: 
  wind_plants = make_wind_plants()
  if len(wind_plants) < 1: 
    print('warning: wind power fluctuation requested, but there are no wind plants in this case')
  else: 
    tnext_wind = 0

# initialize for day-ahead, OPF and time stepping
ts = 0
tnext_opf = 0
tnext_da = da_offset
# we need to adjust Pmin downward so the OPF and PF can converge, or else implement unit commitment
for row in gen: 
  row[9] = 0.1 * row[8]

# listening to GridLAB-D and its auction objects
gld_load = {} # key on bus number
print('FNCS Connections: bus, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit')
print(fncsBus)

#orginal forecast
pforecast = [[0 for x in range(24)] for y in range(fncsBus.shape[0])]
for i in range(fncsBus.shape[0]): 
  for j in range(24): 
    pforecast[i][j] = bus[i][2] * load_shape[j]  # * scale for each bus

# TODO: this is hardwired for 8, more efficient to concatenate outside a loop
# for ? generator 
for i in range(8): 
  busnum = i+1
  genidx = gen.shape[0]
  gen = np.concatenate((gen, np.array([[busnum, 0, 0, 0, 0, 1, 250, 1, 0, -5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])))
  genCost = np.concatenate((genCost, np.array([[2, 0, 0, 3, 0.0, 0.0, 0.0]])))
  gld_scale = float(fncsBus[i, 2])
  gld_load[busnum] = {'pcrv': 0, 'qcrv': 0, 'p': float(fncsBus[i, 7])/gld_scale, 'q': float(fncsBus[i, 8])/gld_scale, 
    'unresp': 0, 'resp_max': 0, 'c2': 0, 'c1': 0, 'deg': 0, 'genidx': genidx}

#print(gld_load)
#print(gen)
#print(genCost)
tnext_metrics = 0
loss_accum = 0
conv_accum = True
n_accum = 0
bus_accum = {}
gen_accum = {}
for i in range(fncsBus.shape[0]): 
  busnum = int(fncsBus[i, 0])
  bus_accum[str(busnum)] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]
for i in range(gen.shape[0]): 
  gen_accum[str(i+1)] = [0, 0, 0]

#quit()
fncs.initialize()
op = open(casename + '_opf.csv', 'w')
vp = open(casename + '_pf.csv', 'w')
print('seconds, OPFconverged, TotalLoad, TotalGen, SwingGen, LMP1, LMP8, gas1, coal1, nuc1, gas2, coal2, nuc2, gas3, coal3, gas4, gas5, coal5, gas7, coal7, wind1, wind3, wind4, wind6, wind7', sep=', ', file=op, flush=True)
print('seconds, PFConverged, TotalLoad, TotalGen, TotalLoss, SwingGen, v1, v2, v3, v4, v5, v6, v7, v8', sep=', ', file=vp, flush=True)

write_ames_base_case(ppc, casename + '_ames.dat')

# MAIN LOOP starts here
while ts <= tmax: 
  # start by getting the latest inputs from GridLAB-D and the auction
  events = fncs.get_events()
  for topic in events: 
    val = fncs.get_value(topic)
    if 'UNRESPONSIVE_MW_' in topic: 
      busnum = int(topic[16: ])
      gld_load[busnum]['unresp'] = float(val)
    elif 'RESPONSIVE_MAX_MW_' in topic: 
      busnum = int(topic[18: ])
      gld_load[busnum]['resp_max'] = float(val)
    elif 'RESPONSIVE_C2_' in topic: 
      busnum = int(topic[14: ])
      gld_load[busnum]['c2'] = float(val)
    elif 'RESPONSIVE_C1_' in topic: 
      busnum = int(topic[14: ])
      gld_load[busnum]['c1'] = float(val)
    elif 'RESPONSIVE_DEG_' in topic: 
      busnum = int(topic[15: ])
      gld_load[busnum]['deg'] = int(val)
    elif 'SUBSTATION' in topic: 
      busnum = int(topic[10: ])
      p, q = parse_mva(val)
      gld_load[busnum]['p'] = float(p)
      gld_load[busnum]['q'] = float(q)
    elif 'DA_BID_' in topic:
      busnum = int(topic[7: ])
      da_bid = json.loads(val) # keys unresp_mw, resp_max_mw, resp_c2, resp_c1, resp_deg; each array[24]
      print ('Day Ahead Bid for Bus', busnum, 'at', ts, '=', da_bid, flush=True)

#  print(ts, 'FNCS inputs', gld_load, flush=True)
  # fluctuate the wind plants
  if ts >= tnext_wind: 
    for key, row in wind_plants.items(): 
      # return dict with rows like wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, p]
      wind_bus = row[0]
      MW = row[1]
      Theta0 = row[2]
      Theta1 = row[3]
      StdDev = row[4]
      Psi1 = row[5]
      Ylim = row[6]
      alag = row[7]
      ylag = row[8]
      p = row[9]
      if ts > 0: 
        a = np.random.normal(0.0, StdDev)
        y = Theta0 + a - Theta1 * alag + Psi1 * ylag
        alag = a
      else: 
        y = ylag
      if y > Ylim: 
        y = Ylim
      elif y < 0.0: 
        y = 0.0
      p = y * y
      if ts > 0: 
        ylag = y
      row[7] = alag
      row[8] = ylag
      row[9] = p
      # reset the unit capacity; this will 'stick' for the next wind_period
      gen[int(key), 8] = p
      if gen[int(key), 1] > p: 
        gen[int(key), 1] = p
    tnext_wind += wind_period

  # always baseline the loads from the curves
  for row in fncsBus: 
    busnum = int(row[0])
    Pnom = float(row[3])
    Qnom = float(row[4])
    curve_scale = float(row[5])
    curve_skew = int(row[6])
    sec =(ts + curve_skew) % 86400
    h = float(sec) / 3600.0
    val = ip.splev([h / 24.0], tck_load)
    gld_load[busnum]['pcrv'] = Pnom * curve_scale * float(val[1])
    gld_load[busnum]['qcrv'] = Qnom * curve_scale * float(val[1])

   # run SCED/SCUC in AMES to establish the next day's unit commmitment and dispatch
#  if ts >= tnext_da: 
#    write_ames_base_case(ppc, casename + '_ames.dat')
#    subprocess.call(['java', '-jar', '-Djava.library.path=/home/osboxes/grid/repository/fncs/java/build', '"/home/osboxes/grid/repository/ERCOTTESTSystem/AMES-V5.0/dist/AMES-V5.0.jar"', casename + '_ames.dat'])
#    collect AMES output and update the dispatch schedules in ppc
#    tnext_da += da_period

  # run OPF to establish the prices and economic dispatch
  if ts >= tnext_opf: 
    # update cost coefficients, set dispatchable load, put unresp+curve load on bus
    bus = ppc['bus'] # in case of aliasing
    for row in fncsBus: 
      busnum = int(row[0])
      gld_scale = float(row[2])
      resp_max = gld_load[busnum]['resp_max'] * gld_scale
      unresp = gld_load[busnum]['unresp'] * gld_scale
      c2 = gld_load[busnum]['c2'] / gld_scale
      c1 = gld_load[busnum]['c1']
      deg = gld_load[busnum]['deg']
      # track the latest bid in the metrics
      bus_accum[str(busnum)][8] = unresp
      bus_accum[str(busnum)][9] = resp_max
      bus_accum[str(busnum)][10] = c1
      bus_accum[str(busnum)][11] = c2
      genidx = gld_load[busnum]['genidx']
      gen[genidx, 9] = -resp_max
      if deg == 2: 
        genCost[genidx, 3] = 3
        genCost[genidx, 4] = -c2
        genCost[genidx, 5] = c1
      elif deg == 1: 
        genCost[genidx, 3] = 2
        genCost[genidx, 4] = c1
        genCost[genidx, 5] = 0.0
      else: 
        genCost[genidx, 3] = 1
        genCost[genidx, 4] = 999.0
        genCost[genidx, 5] = 0.0
      genCost[genidx, 6] = 0.0
      if ts > 0: 
        bus[busnum-1, 2] = gld_load[busnum]['pcrv'] + unresp
        bus[busnum-1, 3] = gld_load[busnum]['qcrv']
      else: # use the initial condition for GridLAB-D contribution, which may be non-zero
        bus[busnum-1, 2] = gld_load[busnum]['pcrv'] + gld_load[busnum]['p'] * gld_scale
        bus[busnum-1, 3] = gld_load[busnum]['qcrv'] + gld_load[busnum]['q'] * gld_scale
#    print_gld_load(ppc, gld_load, 'OPF', ts)
    ropf = pp.runopf(ppc, ppopt_market)
    if ropf['success'] == False: 
      conv_accum = False
    opf_bus = deepcopy(ropf['bus'])
    opf_gen = deepcopy(ropf['gen'])
    Pswing = 0
    for idx in range(opf_gen.shape[0]): 
      if opf_gen[idx, 0] == swing_bus: 
        Pswing += opf_gen[idx, 1]
    print(ts, ropf['success'], 
           '{: .2f}'.format(opf_bus[: , 2].sum()), 
           '{: .2f}'.format(opf_gen[: , 1].sum()), 
           '{: .2f}'.format(Pswing), 
           '{: .4f}'.format(opf_bus[0, 13]), 
           '{: .4f}'.format(opf_bus[7, 13]), 
           '{: .2f}'.format(opf_gen[0, 1]), 
           '{: .2f}'.format(opf_gen[1, 1]), 
           '{: .2f}'.format(opf_gen[2, 1]), 
           '{: .2f}'.format(opf_gen[3, 1]), 
           '{: .2f}'.format(opf_gen[4, 1]), 
           '{: .2f}'.format(opf_gen[5, 1]), 
           '{: .2f}'.format(opf_gen[6, 1]), 
           '{: .2f}'.format(opf_gen[7, 1]), 
           '{: .2f}'.format(opf_gen[8, 1]), 
           '{: .2f}'.format(opf_gen[9, 1]), 
           '{: .2f}'.format(opf_gen[10, 1]), 
           '{: .2f}'.format(opf_gen[11, 1]), 
           '{: .2f}'.format(opf_gen[12, 1]), 
           '{: .2f}'.format(opf_gen[13, 1]), 
           '{: .2f}'.format(opf_gen[14, 1]), 
           '{: .2f}'.format(opf_gen[15, 1]), 
           '{: .2f}'.format(opf_gen[16, 1]), 
           '{: .2f}'.format(opf_gen[17, 1]), 
           sep=', ', file=op, flush=True)
    tnext_opf += period

  # always run the regular power flow for voltages and performance metrics
  ppc['bus'][:, 13] = opf_bus[:, 13]  # set the lmp
  ppc['gen'][:, 1] = opf_gen[:, 1]   # set the economic dispatch
  bus = ppc['bus'] # in case of aliasing
  # add the actual scaled GridLAB-D loads to the baseline curve loads, turn off dispatchable loads
  for row in fncsBus: 
    busnum = int(row[0])
    gld_scale = float(row[2])
    Pgld = gld_load[busnum]['p'] * gld_scale
    Qgld = gld_load[busnum]['q'] * gld_scale
    bus[busnum-1, 2] = gld_load[busnum]['pcrv'] + Pgld
    bus[busnum-1, 3] = gld_load[busnum]['qcrv'] + Qgld
    genidx = gld_load[busnum]['genidx']
    gen[genidx, 1] = 0 # p
    gen[genidx, 2] = 0 # q
    gen[genidx, 9] = 0 # pmin
#  print_gld_load(ppc, gld_load, 'RPF', ts)
  rpf = pp.runpf(ppc, ppopt_regular)
  if rpf[0]['success'] == False: 
    conv_accum = False
    print('rpf did not converge at', ts)
#   pp.printpf(100.0, 
#               bus=rpf[0]['bus'], 
#               gen=rpf[0]['gen'], 
#               branch=rpf[0]['branch'], 
#               fd=sys.stdout, 
#               et=rpf[0]['et'], 
#               success=rpf[0]['success'])
  rBus = rpf[0]['bus']
  rGen = rpf[0]['gen']
  Pload = rBus[:, 2].sum()
  Pgen = rGen[:, 1].sum()
  Ploss = Pgen - Pload
  Pswing = 0
  for idx in range(rGen.shape[0]):
    if rGen[idx, 0] == swing_bus:
      Pswing += rGen[idx, 1]
  print(ts, rpf[0]['success'], 
         '{: .2f}'.format(Pload), 
         '{: .2f}'.format(Pgen), 
         '{: .2f}'.format(Ploss), 
         '{: .2f}'.format(Pswing), 
         '{: .3f}'.format(rBus[0, 7]),
         '{: .3f}'.format(rBus[1, 7]),
         '{: .3f}'.format(rBus[2, 7]),
         '{: .3f}'.format(rBus[3, 7]),
         '{: .3f}'.format(rBus[4, 7]),
         '{: .3f}'.format(rBus[5, 7]),
         '{: .3f}'.format(rBus[6, 7]),
         '{: .3f}'.format(rBus[7, 7]),
         sep=', ', file=vp, flush=True)

  # update the metrics
  n_accum += 1
  loss_accum += Ploss
  for i in range(fncsBus.shape[0]): 
    busnum = int(fncsBus[i, 0])
    busidx = busnum - 1
    row = rBus[busidx].tolist()
    # publish the bus VLN and LMP [$/kwh] for GridLAB-D
    bus_vln = 1000.0 * row[7] * row[9] / math.sqrt(3.0)
    fncs.publish('three_phase_voltage_Bus' + str(busnum), bus_vln)
    lmp = float(opf_bus[busidx, 13])*0.001
    fncs.publish('LMP_Bus' + str(busnum), lmp) # publishing $/kwh
    # LMP_P, LMP_Q, PD, QD, Vang, Vmag, Vmax, Vmin: row[11] and row[12] are Vmax and Vmin constraints
    PD = row[2] #  + resp # TODO, if more than one FNCS bus, track scaled_resp separately
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
  for i in range(rGen.shape[0]):
    row = rGen[i].tolist()
    busidx = int(row[0] - 1)
    # Pgen, Qgen, LMP_P (includes the responsive load as dispatched by OPF)
    gen_accum[str(i+1)][0] += row[1]
    gen_accum[str(i+1)][1] += row[2]
    gen_accum[str(i+1)][2] += float(opf_bus[busidx, 13])*0.001

  # write the metrics
  if ts >= tnext_metrics: 
    sys_metrics[str(ts)] = {casename: [loss_accum / n_accum, conv_accum]}

    bus_metrics[str(ts)] = {}
    for i in range(fncsBus.shape[0]): 
      busnum = int(fncsBus[i, 0])
      busidx = busnum - 1
      row = rBus[busidx].tolist()
      met = bus_accum[str(busnum)]
      bus_metrics[str(ts)][str(busnum)] = [met[0]/n_accum, met[1]/n_accum, met[2]/n_accum, met[3]/n_accum, 
                                           met[4]/n_accum, met[5]/n_accum, met[6], met[7], 
                                           met[8], met[9], met[10], met[11]]
      bus_accum[str(busnum)] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]

    gen_metrics[str(ts)] = {}
    for i in range(rGen.shape[0]):
      met = gen_accum[str(i+1)]
      gen_metrics[str(ts)][str(i+1)] = [met[0]/n_accum, met[1]/n_accum, met[2]/n_accum]
      gen_accum[str(i+1)] = [0, 0, 0]

    tnext_metrics += period
    n_accum = 0
    loss_accum = 0
    conv_accum = True

  # request the next time step, if necessary
  if ts >= tmax: 
    print('breaking out at', ts, flush=True)
    break
  ts = fncs.time_request(min(ts + dt, tmax))

# ======================================================
print('writing metrics', flush=True)
print(json.dumps(sys_metrics), file=sys_mp, flush=True)
print(json.dumps(bus_metrics), file=bus_mp, flush=True)
print(json.dumps(gen_metrics), file=gen_mp, flush=True)
print('closing files', flush=True)
bus_mp.close()
gen_mp.close()
sys_mp.close()
op.close()
vp.close()
print('finalizing FNCS', flush=True)
fncs.finalize()
