import numpy as np
import scipy.interpolate as ip
import pypower.api as pp
import tesp_support.api as tesp
import tesp_support.fncs as fncs
import json
import math
import subprocess
from copy import deepcopy
import sys
import os

casename = 'ercot_8'

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

def print_matrix (lbl, A, fmt='{:8.4f}'):
  if A is None:
    print (lbl, 'is Empty!', flush=True)
  elif hasattr(A, '__iter__'):
    nrows = len(A)
    if (nrows > 1) and hasattr(A[0], '__iter__'):  # 2D array
      ncols = len(A[0])
      print ('{:s} is {:d}x{:d}'.format (lbl, nrows, ncols))
      print ('\n'.join([' '.join([fmt.format(item) for item in row]) for row in A]), flush=True)
    else:              # 1D array, printed flat
      print ('{:s} has {:d} elements'.format (lbl, nrows))
      print (' '.join(fmt.format(item) for item in A), flush=True)
  else:                # single value
    print (lbl, '=', fmt.format(A), flush=True)
    
def print_keyed_matrix (lbl, D, fmt='{:8.4f}'):
  if D is None:
    print (lbl, 'is Empty!', flush=True)
    return
  nrows = len(D)
  ncols = 0
  for key, row in D.items():
    if ncols == 0:
      ncols = len(row)
      print ('{:s} is {:d}x{:d}'.format (lbl, nrows, ncols))
    print ('{:8s}'.format(key), ' '.join(fmt.format(item) for item in row), flush=True)

# from 'ARIMA-Based Time Series Model of Stochastic Wind Power Generation'
# return dict with rows like wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, p]
def make_wind_plants(ppc):
  gen = ppc['gen']
  genFuel = ppc['genfuel']
  plants = {}
  Pnorm = 165.6
  for i in range(gen.shape[0]):
    busnum = int(gen[i, 0])
    if "wind" in genFuel[i][0]:
      MW = float(gen[i, 8])
      scale = MW / Pnorm
      Theta0 = 0.05 * math.sqrt(scale)
      Theta1 = -0.1 * scale
      StdDev = math.sqrt(1.172 * math.sqrt(scale))
      Psi1 = 1.0
      Ylim = math.sqrt(MW)
      alag = Theta0
      ylag = Ylim
      unRespMW = [0] * 48
      genIdx = i
      plants[str(i)] = [busnum, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, unRespMW, genIdx]
  return plants

def shutoff_wind_plants (ppc):
  gen = ppc['gen']
  genFuel = ppc['genfuel']
  for i in range(gen.shape[0]):
    if "wind" in genFuel[i][0]:
      gen[i][7] = 0

# this differs from tesp_support because of additions to FNCS, and Pnom==>Pmin for generators
def make_dictionary(ppc, rootname):
  """ Helper function to write the JSON metafile for post-processing

  Args:
    ppc (dict): PYPOWER case file structure
    rootname (str): to write rootname_m_dict.json
  """
  fncsBuses = {}
  generators = {}
  unitsout = []
  branchesout = []
  bus = ppc['bus']
  gen = ppc['gen']
  genCost = ppc['gencost']
  genFuel = ppc['genfuel']
  fncsBus = ppc['DSO']
  units = ppc['UnitsOut']
  branches = ppc['BranchesOut']

  for i in range(gen.shape[0]):
    busnum = int(gen[i, 0])
    bustype = bus[busnum - 1, 1]
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
    generators[str(i + 1)] = {'bus': int(busnum), 'bustype': bustypename, 'Pmin': float(gen[i, 9]),
                  'Pmax': float(gen[i, 8]), 'genfuel': genFuel[i][0], 'gentype': gentype,
                  'StartupCost': float(genCost[i, 1]), 'ShutdownCost': float(genCost[i, 2]), 'c2': c2,
                  'c1': c1, 'c0': c0}

  for i in range(fncsBus.shape[0]):
    busnum = int(fncsBus[i, 0])
    busidx = busnum - 1
    fncsBuses[str(busnum)] = {'Pnom': float(bus[busidx, 2]), 'Qnom': float(bus[busidx, 3]),
                  'area': int(bus[busidx, 6]), 'zone': int(bus[busidx, 10]),
                  'ampFactor': float(fncsBus[i, 2]), 'GLDsubstations': [fncsBus[i, 1]],
                  'curveScale': float(fncsBus[i, 5]), 'curveSkew': int(fncsBus[i, 6])}

  for i in range(units.shape[0]):
    unitsout.append({'unit': int(units[i, 0]), 'tout': int(units[i, 1]), 'tin': int(units[i, 2])})

  for i in range(branches.shape[0]):
    branchesout.append({'branch': int(branches[i, 0]), 'tout': int(branches[i, 1]), 'tin': int(branches[i, 2])})

  dp = open(rootname + '_m_dict.json', 'w')
  ppdict = {'baseMVA': ppc['baseMVA'], 'fncsBuses': fncsBuses, 'generators': generators, 'UnitsOut': unitsout,
        'BranchesOut': branchesout}
  print(json.dumps(ppdict), file=dp, flush=True)
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
  vals = [0.0, 0.0]
  for i in range(len(tok)):
    if tok[i] == '+' or tok[i] == '-':
      if bLastDigit:
        vals[0] = float(tok[: i])
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

def print_gld_load(ppc, gld_load, msg, ts):
  bus = ppc['bus']
  fncsBus = ppc['DSO']
  print(msg, 'at', ts)
  print('bus, genidx, pbus, qbus, pcrv, qcrv, pgld, qgld, unresp, resp_max, c2, c1, deg')
  for row in fncsBus:
    busnum = int(row[0])
    gld_scale = float(row[2])
    pbus = bus[busnum - 1, 2]
    qbus = bus[busnum - 1, 3]
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

def print_bus_lmps (lbl, bus):
  print ('Bus LMPS', lbl)
  for i in range(bus.shape[0]):
    print (i, bus[i, 13])

def tso_loop():

  def read_matpower_array (fp):
    A = []
    while True:
      ln = fp.readline()
      if '];' in ln:
        break
      ln = ln.lstrip().rstrip(';\n')
      A.append (ln.split())
    return A

  def solve_most_case (fname):
    rGen = None
    rBus = None
    rBranch = None
    rGenCost = None
    cmdline = 'octave {:s}'.format(fname)
    proc = subprocess.Popen (cmdline, shell=True)
    proc.wait()
    fp = open ('solved.txt', 'r')
    while True:
      ln = fp.readline()
      if not ln:
        break
      elif 'mpc.gen =' in ln:
        rGen = read_matpower_array (fp)
      elif 'mpc.branch =' in ln:
        rBranch = read_matpower_array (fp)
      elif 'mpc.bus =' in ln:
        rBus = read_matpower_array (fp)
      elif 'mpc.gencost =' in ln:
        rGenCost = read_matpower_array (fp)
    fp.close()
    print ('Solved Base Case DC OPF in Matpower')
    print ('  rBus is {:d}x{:d}'.format (len(rBus), len(rBus[0])))
    print ('  rBranch is {:d}x{:d}'.format (len(rBranch), len(rBranch[0])))
    print ('  rGen is {:d}x{:d}'.format (len(rGen), len(rGen[0])))
    print ('  rGenCost is {:d}x{:d}'.format (len(rGenCost), len(rGenCost[0])))
    return rBus, rBranch, rGen, rGenCost

  def write_array_rows (A, fp):
    print (';\n'.join([' '.join([' {:s}'.format(str(item)) for item in row]) for row in A]), file=fp)
    
  def write_most_file(fname):
    print ('want to write', fname)
#    fp = open(fname, 'w')
#    print ('%% From PNNL TESP, fncsTSO2.py, case', casename, file=fp)
#    fp.close()

  def write_most_base_case(fname):
    fp = open(fname, 'w')
    print ('function mpc = basecase', file=fp)
    print ('%% MATPOWER base case from PNNL TESP, fncsTSO2.py, model name', casename, file=fp)
    print ("""mpc.version = '2';""", file=fp)
    print ("""mpc.baseMVA = 100;""", file=fp)
    print ("""%% bus_i  type  Pd  Qd  Gs  Bs  area  Vm  Va  baseKV  zone  Vmax  Vmin""", file=fp)
    print ("""mpc.bus = [""", file=fp)
    write_array_rows (bus, fp)
    print ("""];""", file=fp)
    print ("""%% bus  Pg  Qg  Qmax  Qmin  Vg  mBase status  Pmax  Pmin  Pc1 Pc2 Qc1min  Qc1max  Qc2min  Qc2max  ramp_agc  ramp_10 ramp_30 ramp_q  apf""", file=fp)
    print ("""mpc.gen = [""", file=fp)
    write_array_rows (gen, fp)
    print ("""];""", file=fp)
    print ("""%% bus  tbus  r x b rateA rateB rateC ratio angle status  angmin  angmax""", file=fp)
    print ("""mpc.branch = [""", file=fp)
    write_array_rows (branch, fp)
    print ("""];""", file=fp)
    print ("""%% either 1 startup shutdown n x1 y1  ... xn  yn""", file=fp)
    print ("""%%   or 2 startup shutdown n c(n-1) ... c0""", file=fp)
    print ("""mpc.gencost = [""", file=fp)
    write_array_rows (genCost, fp)
    print ("""];""", file=fp)
    fp.close()

  # update cost coefficients, set dispatchable load, put unresp+curve load on bus
  def update_cost_and_load():
    for row in fncsBus:
      busnum = int(row[0])
      gld_scale = float(row[2])
      resp_max = gld_load[busnum]['resp_max'] * gld_scale
      unresp = gld_load[busnum]['unresp'] * gld_scale
      c2 = gld_load[busnum]['c2'] / gld_scale * gld_scale
      c1 = gld_load[busnum]['c1'] / gld_scale
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
      bus[busnum - 1, 2] = gld_load[busnum]['pcrv']
      bus[busnum - 1, 3] = gld_load[busnum]['qcrv']
      if curve:
        bus[busnum - 1, 2] += unresp  # because the of the curve_scale

  # Initialize the program
  hours_in_a_day = 24
  secs_in_a_hr = 3600

  x = np.array(range(25))
  y = np.array(load_shape)
  l = len(x)
  t = np.linspace(0, 1, l - 2, endpoint=True)
  t = np.append([0, 0, 0], t)
  t = np.append(t, [1, 1, 1])
  tck_load = [t, [x, y], 3]

  ppc = tesp.load_json_case(casename + '.json')
  ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'], OPF_ALG_DC=200)  # dc for
  ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'], PF_MAX_IT=20, PF_ALG=1)  # ac for power flow

  if ppc['solver'] == 'GLPK': # 'cbc':
    ppc['gencost'][:, 4] = 0.0  # can't use quadratic costs with CBC solver
  # these have been aliased from case name .json file
  bus = ppc['bus']
  branch = ppc['branch']
  gen = ppc['gen']
  genCost = ppc['gencost']
  genFuel = ppc['genfuel']
  zones = ppc['zones']
  fncsBus = ppc['DSO']
  numGen = gen.shape[0]

  # set configurations case name from .json file
  priceSensLoad = 0
  if ppc['priceSensLoad']:
    priceSensLoad = 1

  wind_period = 0
  if ppc['windPower']:
    wind_period = secs_in_a_hr

  StartTime = ppc['StartTime']
  tmax = int(ppc['Tmax'])
  period = int(ppc['Period'])
  dt = int(ppc['dt'])
  swing_bus = int(ppc['swing_bus'])
  noScale = ppc['noScale']
  curve = ppc['curve']

  most = ppc['most']
  solver = ppc['solver']
  priceCap = 2 * ppc['priceCap']
  reserveDown = ppc['reserveDown']
  reserveUp = ppc['reserveUp']
  zonalReserves = ppc['zonalReserves']
  baseS = int(ppc['baseMVA'])   # base_S in ercot_8.json baseMVA
  baseV = int(bus[0, 9])      # base_V in ercot_8.json bus row 0-7, column 9, should be the same for all buses

  # ppc arrays(bus type 1=load, 2 = gen(PV) and 3 = swing)
  # bus: bus id, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin, LAM P, LAM Q
  # zones: zone id, name, ReserveDownZonalPercent, ReserveUpZonalPercent
  # branch: from bus, to bus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
  # gen: bus id, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin,(11 zeros)
  # gencost: 2, startup, shutdown, 3, c2, c1, c0
  # FNCS: bus id, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit
  # UnitsOut: idx, time out[s], time back in[s]
  # BranchesOut: idx, time out[s], time back in[s]

  # initialize for metrics collection
  bus_mp = open('bus_' + casename + '_metrics.json', 'w')
  gen_mp = open('gen_' + casename + '_metrics.json', 'w')
  sys_mp = open('sys_' + casename + '_metrics.json', 'w')
  bus_meta = {'LMP_P': {'units': 'USD/kwh', 'index': 0}, 'LMP_Q': {'units': 'USD/kvarh', 'index': 1},
        'PD': {'units': 'MW', 'index': 2}, 'QD': {'units': 'MVAR', 'index': 3},
        'Vang': {'units': 'deg', 'index': 4},
        'Vmag': {'units': 'pu', 'index': 5}, 'Vmax': {'units': 'pu', 'index': 6},
        'Vmin': {'units': 'pu', 'index': 7},
        'unresp': {'units': 'MW', 'index': 8}, 'resp_max': {'units': 'MW', 'index': 9},
        'c1': {'units': '$/MW', 'index': 10}, 'c2': {'units': '$/MW^2', 'index': 11}}
  gen_meta = {'Pgen': {'units': 'MW', 'index': 0}, 'Qgen': {'units': 'MVAR', 'index': 1},
        'LMP_P': {'units': 'USD/kwh', 'index': 2}}
  sys_meta = {'Ploss': {'units': 'MW', 'index': 0}, 'Converged': {'units': 'true/false', 'index': 1}}
  bus_metrics = {'Metadata': bus_meta, 'StartTime': StartTime}
  gen_metrics = {'Metadata': gen_meta, 'StartTime': StartTime}
  sys_metrics = {'Metadata': sys_meta, 'StartTime': StartTime}
  make_dictionary(ppc, casename)

  # initialize for variable wind
  wind_plants = {}
  tnext_wind = tmax + 2 * dt  # by default, never fluctuate the wind plants
  if wind_period > 0:
    wind_plants = make_wind_plants(ppc)
    if len(wind_plants) < 1:
      print('warning: wind power fluctuation requested, but there are no wind plants in this case')
    else:
      tnext_wind = 0
      ngen = []
      ngenCost = []
      ngenFuel = []
      for i in range(numGen):
        if "wind" in genFuel[i][0] and wind_period != 0:
          ngen.append(gen[i])
          ngenCost.append(genCost[i])
          ngenFuel.append(genFuel[i])
        else:
          ngen.append(gen[i])
          ngenCost.append(genCost[i])
          ngenFuel.append(genFuel[i])
      ppc['gen'] = np.array(ngen)
      ppc['gencost'] = np.array(ngenCost)
      ppc['genfuel'] = np.array(ngenFuel)
      gen = ppc['gen']
      genCost = ppc['gencost']
      genFuel = ppc['genfuel']
      numGen = gen.shape[0]
  else:
    print ('disabling all the wind plants')
    shutoff_wind_plants (ppc)

  # initialize for day-ahead, OPF and time stepping
  ts = 0
  Pload = 0
  tnext_opf = 0
  tnext_dam = 0
  wind_hour = -1
  mn = 0
  hour = -1
  day = 1
  lastDay = 1
  file_time = ''
  MaxDay = tmax // 86400  # days in simulation
  RTOPDur = period // 60  # in minutes
  RTDeltaT = 1      # in minutes
  da_bid = False
  da_schedule = {}
  da_lmps = {}
  da_dispatch = {}
  rt_lmps = {}
  rt_dispatch = {}
  # listening to GridLAB-D and its auction objects
  gld_load = {}  # key on bus number

  # we need to adjust Pmin downward so the OPF and PF can converge, or else implement unit commitment
#  if not ames:
#    for row in gen:
#      row[9] = 0.1 * row[8]

  # TODO: more efficient to concatenate outside a loop
  for i in range(fncsBus.shape[0]):
    busnum = i + 1
    genidx = ppc['gen'].shape[0]
    # I suppose a generator for a summing generators on a bus?
    ppc['gen'] = np.concatenate(
      (ppc['gen'], np.array([[busnum, 0, 0, 0, 0, 1, 250, 1, 0, -5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])))
    ppc['gencost'] = np.concatenate(
      (ppc['gencost'], np.array([[2, 0, 0, 3, 0.0, 0.0, 0.0]])))
    ppc['genfuel'] = np.concatenate(
      (ppc['genfuel'], np.array([['']])))
    gld_scale = float(fncsBus[i, 2])
    gld_load[busnum] = {'pcrv': 0, 'qcrv': 0,
              'p': float(fncsBus[i, 7]) / gld_scale, 'q': float(fncsBus[i, 8]) / gld_scale,
              'unresp': 0, 'resp_max': 0, 'c2': 0, 'c1': 0, 'deg': 0, 'genidx': genidx}
    if noScale:
      fncsBus[i, 2] = 1   # gld_scale

  # needed to be re-aliased after np.concatenate
  gen = ppc['gen']
  genCost = ppc['gencost']
  genFuel = ppc['genfuel']

  # print('FNCS Connections: bus, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit')
  # print(fncsBus)

  # print(gld_load)
  # print(gen)
  # print(genCost)

  # interval for metrics recording
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
    gen_accum[str(i + 1)] = [0, 0, 0]

  total_bus_num = fncsBus.shape[0]
  unRespMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
  respMaxMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
  respC2 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
  respC1 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
  respC0 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
  resp_deg = np.zeros([total_bus_num, hours_in_a_day], dtype=float)

  if most:
    write_most_base_case('basecase.m')
    print_bus_lmps ('before solving base case', bus)
    rBus, rBranch, rGen, rGenCost = solve_most_case('solvebasecase.m')
    for i in range(bus.shape[0]):  # starting LMP values
      bus[i, 13] = float (rBus[i][13])
    print_bus_lmps ('after solving base case', bus)
#  quit()
  fncs.initialize()

  # Set column header for output files
  line = "seconds, OPFconverged, TotalLoad, TotalGen, SwingGen"
  line2 = "seconds, PFConverged, TotalLoad, TotalGen, TotalLoss, SwingGen"
  for i in range(fncsBus.shape[0]):
    line += ", " + "LMP" + str(i+1)
    line2 += ", " + "v" + str(i + 1)
  w = 0;  n = 0;  c = 0;  g = 0
  for i in range(numGen):
    if "wind" in genFuel[i][0]:
      w += 1;  line += ", wind" + str(w)
    elif "nuclear" in genFuel[i][0]:
      n += 1;  line += ", nuc" + str(n)
    elif "coal" in genFuel[i][0]:
      c += 1;  line += ", coal" + str(c)
    else:
      g += 1;  line += ", gas" + str(g)
  line += ", TotalWindGen"

  op = open(casename + '_opf.csv', 'w')
  vp = open(casename + '_pf.csv', 'w')
  print(line, sep=', ', file=op, flush=True)
  print(line2, sep=', ', file=vp, flush=True)

  # MAIN LOOP starts here
  while ts <= tmax:
    # start by getting the latest inputs from GridLAB-D and the auction
    events = fncs.get_events()
    for topic in events:
      val = fncs.get_value(topic)
    # getting the latest inputs from DSO Real Time
      if 'UNRESPONSIVE_MW_' in topic:
        busnum = int(topic[16:])
        gld_load[busnum]['unresp'] = float(val)
      elif 'RESPONSIVE_MAX_MW_' in topic:
        busnum = int(topic[18:])
        gld_load[busnum]['resp_max'] = float(val)
      elif 'RESPONSIVE_C2_' in topic:
        busnum = int(topic[14:])
        gld_load[busnum]['c2'] = float(val)
      elif 'RESPONSIVE_C1_' in topic:
        busnum = int(topic[14:])
        gld_load[busnum]['c1'] = float(val)
      elif 'RESPONSIVE_C0_' in topic:
        busnum = int(topic[14:])
        gld_load[busnum]['c0'] = float(val)
      elif 'RESPONSIVE_DEG_' in topic:
        busnum = int(topic[15:])
        gld_load[busnum]['deg'] = int(val)
    # getting the latest inputs from GridlabD
      elif 'SUBSTATION' in topic:  # gld
        busnum = int(topic[10:])
        p, q = parse_mva(val)
        gld_load[busnum]['p'] = float(p)   # MW
        gld_load[busnum]['q'] = float(q)   # MW
    # getting the latest inputs from DSO day Ahead
      elif 'DA_BID_' in topic:
        da_bid = True
        busnum = int(topic[7:]) - 1
        day_ahead_bid = json.loads(val)
        # keys unresp_mw, resp_max_mw, resp_c2, resp_c1, resp_deg; each array[hours_in_a_day]
        unRespMW[busnum] = day_ahead_bid['unresp_mw']   # fix load
        respMaxMW[busnum] = day_ahead_bid['resp_max_mw']  # slmax
        respC2[busnum] = day_ahead_bid['resp_c2']
        respC1[busnum] = day_ahead_bid['resp_c1']
        respC0[busnum] = 0.0  # day_ahead_bid['resp_c0']
        resp_deg[busnum] = day_ahead_bid['resp_deg']
        # print('Day Ahead Bid for Bus', busnum, 'at', ts, '=', day_ahead_bid, flush=True)

    # fluctuate the wind plants
    if ts >= tnext_wind:
      wind_hour += 1
      if wind_hour == 24:
        wind_hour = 0
      if ts % (wind_period * 24) == 0:
        # copy next day to today
        for j in range(hours_in_a_day):
          for key, row in wind_plants.items():
            row[9][j] = row[9][j+24]
        # make next day forecast
        for j in range(hours_in_a_day):
          for key, row in wind_plants.items():
            # return dict with rows like wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, [24 hour p]]
            Theta0 = row[2]
            Theta1 = row[3]
            StdDev = row[4]
            Psi1 = row[5]
            Ylim = row[6]
            alag = row[7]
            ylag = row[8]
            if j > 0:
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
            if j > 0:
              ylag = y
            row[7] = alag
            row[8] = ylag
            #set the max and min
            if gen[int(key), 8] < p:
              gen[int(key), 8] = p
            if gen[int(key), 9] > p:
              gen[int(key), 9] = p
            row[9][j+24] = p
            if ts == 0:
              row[9][j] = p

      for key, row in wind_plants.items():
        # reset the unit capacity; this will 'stick' for the next wind_period
        gen[row[10], 1] = row[9][wind_hour]
      tnext_wind += wind_period

    # always baseline the loads from the curves
    for row in fncsBus:
      busnum = int(row[0])
      if curve:
        Pnom = float(row[3])
        Qnom = float(row[4])
        curve_scale = float(row[5])
        curve_skew = int(row[6])
        sec = (ts + curve_skew) % 86400
        h = float(sec) / 3600.0
        val = ip.splev([h / 24.0], tck_load)
        gld_load[busnum]['pcrv'] = Pnom * curve_scale * float(val[1])
        gld_load[busnum]['qcrv'] = Qnom * curve_scale * float(val[1])
      else:
        gld_scale = float(row[2])
        gld_load[busnum]['pcrv'] = gld_load[busnum]['p'] * gld_scale
        gld_load[busnum]['qcrv'] = gld_load[busnum]['q'] * gld_scale

    # run multi-period optimization in MOST to establish the next day's unit commitment and dispatch schedule
    if ts >= tnext_dam and most:
      if mn % 60 == 0:
        hour = hour + 1
        mn = 0
        if hour == 24:
          hour = 0
          day = day + 1

      file_time = 'd{:d}_h{:d}_m{:d}'.format (day, hour, mn)
      # update cost coefficients, set dispatchable load, put unresp+curve load on bus
      print_bus_lmps ('before DAM update_cost_and_load', bus)
      update_cost_and_load()
      print_bus_lmps ('after DAM update_cost_and_load', bus)

      # Run the day ahead
      if hour == 12 and mn == 0:

        most_DAM_case_file = "./" + file_time + "dam.dat"
        write_most_file (most_DAM_case_file)
#        da_schedule, da_dispatch, da_lmps = scucDAM(ames_DAM_case_file, file_time + "GenCoSchedule.dat", solver)
#        print ('$$$$ DAM finished [day_hour_min_', print_time, flush=True)
#        print_matrix ('DAM LMPs', da_lmps)
#        print_keyed_matrix ('DAM Dispatches', da_dispatch, fmt='{:8.2f}')
#        print_keyed_matrix ('DAM Schedule', da_schedule, fmt='{:8s}')
#
#     # Real time and update the dispatch schedules in ppc
#     if day > 1:
#       # Change the DA Schedule and the dispatchable generators
#       if day > lastDay:
#         schedule = deepcopy(da_schedule)
#         lastDay = day
#
#       if mn == 0:
#         # uptime and downtime in hour for each generator
#         # and are counted using commitment schedule for the day
#         for i in range(numGen):
#           if "wind" not in genFuel[i][0]:
#             name = "GenCo" + str(i + 1)
#             gen[i, 7] = int(schedule.at[hour, name])
#             if gen[i, 7] == 1:
#               if gen_ames[str(i)][0] > 0:
#                 gen_ames[str(i)][0] += 1
#               else:
#                 gen_ames[str(i)][0] = 1
#             else:
#               if gen_ames[str(i)][0] < 0:
#                 gen_ames[str(i)][0] -= 1
#               else:
#                 gen_ames[str(i)][0] = -1
#
#       # Run the real time and publish the LMP
#       ames_RTM_case_file = "./" + file_time + "rtm.dat"
#       write_psst_file(ames_RTM_case_file, False)
#       rtm_schedule = write_rtm_schedule(schedule, da_schedule)
#       rt_dispatch, rt_lmps = scedRTM(ames_RTM_case_file, rtm_schedule, file_time + "RTMResults.dat", solver)
#       print ('#### RTM finished [day_hour_min_', print_time, flush=True)
#       print_matrix ('RTM LMPs', rt_lmps)
#       print_keyed_matrix ('RTM Dispatches', rt_dispatch, fmt='{:8.2f}')
#       try:
#         for i in range(bus.shape[0]):
#           bus[i, 13] = rt_lmps[i][0]
#         for i in range(numGen):
#           name = "GenCo" + str(i + 1)
#           if "wind" not in genFuel[i][0]:
#             gen[i, 1] = rt_dispatch[name][0]
#       except:
#         print('  #### Exception: unable to obtain and dispatch from LMPs')
#         pass
#
#     # write OPF metrics
#     Pswing = 0
#     for i in range(numGen):
#       if gen[i, 0] == swing_bus:
#         Pswing += gen[i, 1]
#
#     sum_w = 0
#     for key, row in wind_plants.items():
#       sum_w += gen[row[10], 1]
#
#     line = str(ts) + ', ' + "True" + ','
#     line += '{: .2f}'.format(bus[:, 2].sum()) + ','
#     line += '{: .2f}'.format(gen[:, 1].sum()) + ','
#     line += '{: .2f}'.format(Pswing) + ','
#     for i in range(bus.shape[0]):
#       line += '{: .2f}'.format(bus[i, 13]) + ','
#     for i in range(numGen):
#       if numGen > i:
#         line += '{: .2f}'.format(gen[i, 1]) + ','
#     line += '{: .2f}'.format(sum_w)
#     print(line, sep=', ', file=op, flush=True)
#
#     mn = mn + RTOPDur  # period // 60
#     tnext_ames += period
#     # print  ('bus_after_opf = ', bus[:, 2].sum())
#     # print  ('gen_after_opf = ', gen[:, 1].sum())

    # run OPF to establish the prices and economic dispatch - currently period = 300s
    if ts >= tnext_opf:
      # print  ('bus_b4_opf = ', bus[:, 2].sum())
      # print  ('gen_b4_opf = ', gen[:, 1].sum())

      # update cost coefficients, set dispatchable load, put unresp+curve load on bus
      print_bus_lmps ('before OPF update_cost_and_load', bus)
      update_cost_and_load()
      print_bus_lmps ('after OPF update_cost_and_load', bus)

      #  print_gld_load(ppc, gld_load, 'OPF', ts)
      print_bus_lmps ('before runopf', bus)
      ropf = pp.runopf(ppc, ppopt_market)
      print_bus_lmps ('after runopf', bus)
      if ropf['success'] == False:
        conv_accum = False
      opf_bus = deepcopy(ropf['bus'])
      opf_gen = deepcopy(ropf['gen'])
      print_bus_lmps ('from OPF deepcopy', opf_bus)
      Pswing = 0
      for idx in range(opf_gen.shape[0]):
        if opf_gen[idx, 0] == swing_bus:
          Pswing += opf_gen[idx, 1]

      sum_w = 0
      for key, row in wind_plants.items():
        sum_w += gen[row[10], 1]

      line = str(ts) + ',' + "True" + ','
      line += '{: .2f}'.format(opf_bus[:, 2].sum()) + ','
      line += '{: .2f}'.format(opf_gen[:, 1].sum()) + ','
      line += '{: .2f}'.format(Pswing)
      for idx in range(opf_bus.shape[0]):
        line += ',' + '{: .4f}'.format(opf_bus[idx, 13])
      for idx in range(opf_gen.shape[0]):
        if numGen > idx:
          line += ',' + '{: .2f}'.format(opf_gen[idx, 1])
      line += ',{: .2f}'.format(sum_w)
      print(line, sep=', ', file=op, flush=True)

      tnext_opf += period

      # always run the regular power flow for voltages and performance metrics
      ppc['bus'][:, 13] = opf_bus[:, 13]  # set the lmp
      print_bus_lmps ('after setting the slice', bus)
      ppc['gen'][:, 1] = opf_gen[:, 1]  # set the economic dispatch
      bus = ppc['bus']  # needed to be re-aliased because of [:, ] operator
      gen = ppc['gen']  # needed to be re-aliased because of [:, ] operator
      print_bus_lmps ('after re-aliasing the slice', bus)

    # add the actual scaled GridLAB-D loads to the baseline curve loads, turn off dispatchable loads
    for row in fncsBus:
      busnum = int(row[0])
      gld_scale = float(row[2])
      bus[busnum - 1, 2] = gld_load[busnum]['pcrv']
      bus[busnum - 1, 3] = gld_load[busnum]['qcrv']
      if curve:
        bus[busnum - 1, 2] += gld_load[busnum]['p'] * gld_scale   # add the other half to load
        bus[busnum - 1, 3] += gld_load[busnum]['q'] * gld_scale
      idx = gld_load[busnum]['genidx']
      gen[idx, 1] = 0  # p
      gen[idx, 2] = 0  # q
      gen[idx, 9] = 0  # pmin

    rpf = pp.runpf(ppc, ppopt_regular)
    print_bus_lmps ('after runpf', bus)
    # TODO: add a check if does not converge, switch to DC
    if not rpf[0]['success']:
      conv_accum = False
      print('rpf did not converge at', ts)
    rBus = rpf[0]['bus']
    rGen = rpf[0]['gen']

    Pload = rBus[:, 2].sum()
    Pgen = rGen[:, 1].sum()
    Ploss = Pgen - Pload
    Pswing = 0
    for idx in range(rGen.shape[0]):
      if rGen[idx, 0] == swing_bus:
        Pswing += rGen[idx, 1]

    line = str(ts) + ', ' + "True" + ','
    line += '{: .2f}'.format(Pload) + ',' + '{: .2f}'.format(Pgen) + ','
    line += '{: .2f}'.format(Ploss) + ',' + '{: .2f}'.format(Pswing)
    for idx in range(rBus.shape[0]):
      line += ',' + '{: .2f}'.format(rBus[idx, 7])  # bus per-unit voltages
    print(line, sep=', ', file=vp, flush=True)

    # update the metrics
    n_accum += 1
    loss_accum += Ploss
    for i in range(fncsBus.shape[0]):
      busnum = fncsBus[i, 0]
      busidx = int(fncsBus[i, 0]) - 1
      row = rBus[busidx].tolist()
      # publish the bus VLN and LMP [$/kwh] for GridLAB-D
      bus_vln = 1000.0 * row[7] * row[9] / math.sqrt(3.0)
      fncs.publish('three_phase_voltage_Bus' + busnum, bus_vln)
      if most:
        lmp = float(bus[busidx, 13]) * 0.001
      else:
        lmp = float(opf_bus[busidx, 13]) * 0.001
      fncs.publish('LMP_Bus' + busnum, lmp)  # publishing $/kwh
      # LMP_P, LMP_Q, PD, QD, Vang, Vmag, Vmax, Vmin: row[11] and row[12] are Vmax and Vmin constraints
      PD = row[2]  # + resp # TODO, if more than one FNCS bus, track scaled_resp separately
      Vpu = row[7]
      bus_accum[busnum][0] += row[13] * 0.001
      bus_accum[busnum][1] += row[14] * 0.001
      bus_accum[busnum][2] += PD
      bus_accum[busnum][3] += row[3]
      bus_accum[busnum][4] += row[8]
      bus_accum[busnum][5] += Vpu
      if Vpu > bus_accum[busnum][6]:
        bus_accum[busnum][6] = Vpu
      if Vpu < bus_accum[busnum][7]:
        bus_accum[busnum][7] = Vpu

    for i in range(rGen.shape[0]):
      idx = str(i + 1)
      row = rGen[i].tolist()
      busidx = int(row[0] - 1)
      # Pgen, Qgen, LMP_P (includes the responsive load as dispatched by OPF)
      gen_accum[idx][0] += row[1]
      gen_accum[idx][1] += row[2]
      if most:
        gen_accum[idx][2] += float(bus[busidx, 13]) * 0.001
      else:
        gen_accum[idx][2] += float(opf_bus[busidx, 13]) * 0.001

    # write the metrics
    if ts >= tnext_metrics:
      m_ts = str(ts)
      sys_metrics[m_ts] = {casename: [loss_accum / n_accum, conv_accum]}

      bus_metrics[m_ts] = {}
      for i in range(fncsBus.shape[0]):
        busnum = fncsBus[i, 0]
        met = bus_accum[busnum]
        bus_metrics[m_ts][busnum] = [met[0] / n_accum, met[1] / n_accum,
                       met[2] / n_accum, met[3] / n_accum,
                       met[4] / n_accum, met[5] / n_accum,
                       met[6], met[7],
                       met[8], met[9],
                       met[10], met[11]]
        bus_accum[busnum] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]

      gen_metrics[m_ts] = {}
      for i in range(rGen.shape[0]):
        idx = str(i + 1)
        met = gen_accum[idx]
        gen_metrics[m_ts][idx] = [met[0] / n_accum, met[1] / n_accum, met[2] / n_accum]
        gen_accum[idx] = [0, 0, 0]

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

if __name__ == "__main__":
  tso_loop()
