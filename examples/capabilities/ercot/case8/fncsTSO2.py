#   Copyright (C) 2017-2022 Battelle Memorial Institute
# file: fncsTSO2.py

import json
import math
import subprocess
import sys
from copy import deepcopy
from datetime import timedelta

import numpy as np
import pypower.api as pp
import scipy.interpolate as ip

import tesp_support.api as tesp
import tesp_support.fncs as fncs
import tesp_support.tso_helpers as tso
from tesp_support.helpers import parse_mva

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


def shutoff_wind_plants(ppc):
    gen = ppc['gen']
    genFuel = ppc['genfuel']
    for i in range(gen.shape[0]):
        if "wind" in genFuel[i][0]:
            gen[i][7] = 0


def print_bus_lmps(lbl, bus):
    print('Bus LMPS', lbl)
    for i in range(bus.shape[0]):
        print('{:2d} {:9.5f}'.format(i, bus[i, 13]))


def read_matpower_array(fp):
    A = []
    while True:
        ln = fp.readline()
        if '];' in ln:
            break
        ln = ln.lstrip().rstrip(';\n')
        A.append(ln.split())
    return A


def solve_most_rtm_case(fprog, fname):
    rGen = None
    rBus = None
    rBranch = None
    rGenCost = None
    cmdline = '{:s} {:s}'.format(fprog, fname)
    proc = subprocess.Popen(cmdline, shell=True)
    proc.wait()
    fp = open('solved.txt', 'r')
    while True:
        ln = fp.readline()
        if not ln:
            break
        elif 'mpc.gen =' in ln:
            rGen = read_matpower_array(fp)
        elif 'mpc.branch =' in ln:
            rBranch = read_matpower_array(fp)
        elif 'mpc.bus =' in ln:
            rBus = read_matpower_array(fp)
        elif 'mpc.gencost =' in ln:
            rGenCost = read_matpower_array(fp)
    fp.close()
    print('Solved Base Case DC OPF in Matpower')
    print('  rBus is {:d}x{:d}'.format(len(rBus), len(rBus[0])))
    print('  rBranch is {:d}x{:d}'.format(len(rBranch), len(rBranch[0])))
    print('  rGen is {:d}x{:d}'.format(len(rGen), len(rGen[0])))
    print('  rGenCost is {:d}x{:d}'.format(len(rGenCost), len(rGenCost[0])))
    return rBus, rBranch, rGen, rGenCost


def solve_most_dam_case(fprog, froot):
    cmdline = '{:s} {:s}solve.m'.format(fprog, froot)
    proc = subprocess.Popen(cmdline, shell=True)
    proc.wait()
    f, nb, ng, nl, ns, nt, nj_max, Pg, Pd, Pf, u, lamP = tesp.read_most_solution('msout.txt')
    #  print ('f={:.2f} nb={:d} ng={:d} nl={:d} ns={:d} nt={:d} nj_max={:d}'.format (f, nb, ng, nl, ns, nt, nj_max))
    return f, Pg, Pd, Pf, u, lamP


# minup, mindown
def get_plant_min_up_down_hours(fuel, gencosts, gen):
    if fuel == 'nuclear':
        return 24, 24
    if fuel == 'coal':
        return 12, 12
    if fuel == 'gas':
        if gencosts[4] < 57.0:
            return 6, 6
    return 1, 1


# paPrice, naPrice, pdPrice, ndPrice, plfPrice, nlfPrice
def get_plant_prices(fuel, gencosts, gen):
    return 0.0001, 0.0001, 0.0001, 0.0001, 0.1, 0.1


def get_plant_reserve(fuel, gencosts, gen):
    if len(fuel) < 1:
        return 10000.0
    return abs(gen[8])


def get_plant_commit_key(fuel, gencosts, gen, usewind):
    if len(fuel) > 0:
        if fuel == 'wind':
            if usewind:
                return 1
            else:
                return -1
        else:
            return 1
    return 2


def write_array_rows(A, fp):
    print(';\n'.join([' '.join([' {:s}'.format(str(item)) for item in row]) for row in A]), file=fp)


def write_most_table_indices(fp):
    print("""  [PQ, PV, REF, NONE, BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, VM, ...
     VA, BASE_KV, ZONE, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN] = idx_bus;
  [CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, CT_TAREABUS, ...
    CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, CT_CHGTYPE, CT_REP, ...
    CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, CT_TAREALOAD, CT_LOAD_ALL_PQ, ...
    CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, CT_LOAD_ALL_P, CT_LOAD_FIX_P, ...
    CT_LOAD_DIS_P, CT_TGENCOST, CT_TAREAGENCOST, CT_MODCOST_F, ...
    CT_MODCOST_X] = idx_ct;
  [GEN_BUS, PG, QG, QMAX, QMIN, VG, MBASE, GEN_STATUS, PMAX, PMIN, ...
    MU_PMAX, MU_PMIN, MU_QMAX, MU_QMIN, PC1, PC2, QC1MIN, QC1MAX, ...
    QC2MIN, QC2MAX, RAMP_AGC, RAMP_10, RAMP_30, RAMP_Q, APF] = idx_gen;
  [PW_LINEAR, POLYNOMIAL, MODEL, STARTUP, SHUTDOWN, NCOST, COST] = idx_cost;""", file=fp)


def write_most_dam_files(ppc, bids, wind_plants, unit_state, froot):
    fp = open(froot + 'solve.m', 'w')
    print("""clear;""", file=fp)
    print("""define_constants;""", file=fp)
    print("""mpopt = mpoption('verbose', 0, 'out.all', 0, 'most.dc_model', 1, 'most.solver', '{:s}');""".format(
        ppc['solver']), file=fp)
    print("""mpopt = mpoption(mpopt, 'most.uc.run', 1);""", file=fp)
    print("""mpopt = mpoption(mpopt, 'glpk.opts.msglev', 3);""", file=fp)  # TODO: options for other solvers?
    print("""mpopt = mpoption(mpopt, 'glpk.opts.mipgap', 0);""", file=fp)
    print("""mpopt = mpoption(mpopt, 'glpk.opts.tolint', 1e-10);""", file=fp)
    print("""mpopt = mpoption(mpopt, 'glpk.opts.tolobj', 1e-10);""", file=fp)
    print("""mpc = loadcase ('{:s}case.m');""".format(froot), file=fp)
    print("""xgd = loadxgendata('{:s}xgd.m', mpc);""".format(froot), file=fp)
    print("""profiles = getprofiles('{:s}unresp.m');""".format(froot), file=fp)
    print("""profiles = getprofiles('{:s}resp.m', profiles);""".format(froot), file=fp)
    if len(wind_plants) > 0:
        print("""profiles = getprofiles('{:s}wind.m', profiles);""".format(froot), file=fp)
    print("""profiles = getprofiles('{:s}bids.m', profiles);""".format(froot), file=fp)
    print("""nt = size(profiles(1).values, 1);""", file=fp)
    print("""mdi = loadmd(mpc, nt, xgd, [], [], profiles);""", file=fp)
    print("""mdo = most(mdi, mpopt);""", file=fp)
    print("""ms = most_summary(mdo);""", file=fp)
    print("""save('-text', 'msout.txt', 'ms');""", file=fp)
    print("""mdo.results.SolveTime + mdo.results.SetupTime""", file=fp)
    fp.close()

    fp = open(froot + 'case.m', 'w')
    print('function mpc = {:s}case'.format(froot), file=fp)
    print('%% MATPOWER/MOST base case from PNNL TESP, fncsTSO2.py, model name', casename, file=fp)
    print("""mpc.version = '2';""", file=fp)
    print("""mpc.baseMVA = 100;""", file=fp)
    print("""%% bus_i  type  Pd  Qd  Gs  Bs  area  Vm  Va  baseKV  zone  Vmax  Vmin""", file=fp)
    print("""mpc.bus = [""", file=fp)
    write_array_rows(ppc['bus'], fp)
    print("""];""", file=fp)
    print ("""%% bus  Pg  Qg  Qmax  Qmin  Vg  mBase status  Pmax  Pmin  Pc1 Pc2 Qc1min  Qc1max  Qc2min  Qc2max  ramp_agc  ramp_10 ramp_30 ramp_q  apf""", file=fp)
    print("""mpc.gen = [""", file=fp)
    write_array_rows(ppc['gen'], fp)
    print("""];""", file=fp)
    print("""%% bus  tbus  r x b rateA rateB rateC ratio angle status  angmin  angmax""", file=fp)
    print("""mpc.branch = [""", file=fp)
    write_array_rows(ppc['branch'], fp)
    print("""];""", file=fp)
    print("""%% either 1 startup shutdown n x1 y1  ... xn  yn""", file=fp)
    print("""%%   or 2 startup shutdown n c(n-1) ... c0""", file=fp)
    print("""mpc.gencost = [""", file=fp)
    write_array_rows(ppc['gencost'], fp)
    print("""];""", file=fp)
    fp.close()

    fp = open(froot + 'xgd.m', 'w')
    print("""function [xgd_table] = {:s}xgd (mpc)
  xgd_table.colnames = {{
      'CommitKey', ...
      'InitialState',...
      'MinUp', ...
      'MinDown', ...
      'PositiveActiveReservePrice', ...
      'PositiveActiveReserveQuantity', ...
      'NegativeActiveReservePrice', ...
      'NegativeActiveReserveQuantity', ...
      'PositiveActiveDeltaPrice', ...
      'NegativeActiveDeltaPrice', ...
      'PositiveLoadFollowReservePrice', ...
      'PositiveLoadFollowReserveQuantity', ...
      'NegativeLoadFollowReservePrice', ...
      'NegativeLoadFollowReserveQuantity', ...
  }};
  xgd_table.data = [""".format(froot), file=fp)
    ngen = 0
    nwind = 0
    usewind = False
    if len(wind_plants) > 0:
        usewind = True
    for i in range(len(ppc['genfuel'])):
        fuel = ppc['genfuel'][i][0]
        if fuel == 'wind':
            nwind += 1
        elif len(fuel) > 0:
            ngen += 1
        commit = get_plant_commit_key(fuel, ppc['gencost'][i], ppc['gen'][i], usewind)
        reserve = get_plant_reserve(fuel, ppc['gencost'][i], ppc['gen'][i])
        minup, mindown = get_plant_min_up_down_hours(fuel, ppc['gencost'][i], ppc['gen'][i])
        paPrice, naPrice, pdPrice, ndPrice, plfPrice, nlfPrice = get_plant_prices(fuel, ppc['gencost'][i], ppc['gen'][i])
        print(' {:2d} {:4d} {:2d} {:2d} {:f} {:.2f} {:f} {:.2f} {:f} {:f} {:f} {:.2f} {:f} {:.2f};'
              .format(commit, int(unit_state[i]), minup, mindown, paPrice, reserve, naPrice, reserve,
                      pdPrice, ndPrice, plfPrice, reserve, nlfPrice, reserve), file=fp)
    print('];', file=fp)
    print('end', file=fp)
    fp.close()

    # write the load profile information
    rowlist = []
    for row in ppc['DSO']:
        rowlist.append(int(row[0]))

    fp = open(froot + 'unresp.m', 'w')
    print("""function unresp = {:s}unresp""".format(froot), file=fp)
    write_most_table_indices(fp)
    print("""  unresp = struct( ...
    'type', 'mpcData', ...
    'table', CT_TBUS, ...
    'rows', {:s}, ...
    'col', PD, ...
    'chgtype', CT_REP, ...
    'values', [] );""".format(str(rowlist)), file=fp)
    for row in ppc['DSO']:
        busnum = row[0]
        key = row[1]
        gld_scale = float(row[2]) * 3.0  # adds the "curve" load
        vals = str([round(gld_scale * v, 2) for v in bids[key]['unresp_mw']])
        mvals = vals.replace(',', ';')
        print("""  unresp.values(:, 1, {:s}) = {:s};""".format(busnum, mvals), file=fp)
    print("""end""", file=fp)
    fp.close()

    fp = open(froot + 'resp.m', 'w')
    print("""function resp = {:s}resp""".format(froot), file=fp)
    write_most_table_indices(fp)
    print("""  resp = struct( ...
    'type', 'mpcData', ...
    'table', CT_TLOAD, ...
    'rows', {:s}, ...
    'col', CT_LOAD_DIS_P, ...
    'chgtype', CT_REP, ...
    'values', [] );""".format(str(rowlist)), file=fp)
    for row in ppc['DSO']:
        busnum = row[0]
        key = row[1]
        gld_scale = float(row[2])
        vals = str([round(gld_scale * v, 2) for v in bids[key]['resp_max_mw']])
        mvals = vals.replace(',', ';')
        print("""  resp.values(:, 1, {:s}) = {:s};""".format(busnum, mvals), file=fp)
    print("""  unresp = {:s}unresp;""".format(froot), file=fp)
    print("""  resp.values = resp.values + unresp.values;""", file=fp)
    print("""end""", file=fp)
    fp.close()

    # write the load cost information
    rowlist = []
    for row in ppc['DSO']:
        rowlist.append(nwind + ngen + int(row[0]))

    fp = open(froot + 'bids.m', 'w')
    print("""function bids = {:s}bids""".format(froot), file=fp)
    write_most_table_indices(fp)
    print("""  bids = struct( ...
    'type', 'mpcData', ...
    'table', CT_TGENCOST, ...
    'rows', {:s}, ...
    'col', COST, ...
    'chgtype', CT_REP, ...
    'values', [] );""".format(str(rowlist)), file=fp)
    for row in ppc['DSO']:
        busnum = int(row[0])
        key = row[1]
        vals = str([round(v, 3) for v in bids[key]['resp_c1']])
        mvals = vals.replace(',', ';')
        print("""  bids.values(:, 1, {:d}) = {:s};""".format(busnum, mvals), file=fp)
    print("""end""", file=fp)
    fp.close()

    # write the wind plant information if applicable
    if len(wind_plants) < 1:
        return

    rowlist = []
    wind_vals = {}
    for i in range(len(ppc['genfuel'])):
        fuel = ppc['genfuel'][i][0]
        if fuel == 'wind':
            rowlist.append(i + 1)
            wind_vals[i + 1] = []

    # copy the next-day stochastic data into a perfect DAM forecast
    for j in range(24):
        for key, row in wind_plants.items():
            p = row[9][j + 24]
            wind_vals[int(key) + 1].append(p)

    fp = open(froot + 'wind.m', 'w')
    print("""function wind = {:s}wind""".format(froot), file=fp)
    write_most_table_indices(fp)
    print("""  wind = struct( ...
    'type', 'mpcData', ...
    'table', CT_TGEN, ...
    'rows', {:s}, ...
    'col', PMAX, ...
    'chgtype', CT_REP, ...
    'values', [] );""".format(str(rowlist)), file=fp)
    for key, wvals in wind_vals.items():
        rownum = key - ngen
        vals = str([round(v, 2) for v in wvals])
        mvals = vals.replace(',', ';')
        print("""  wind.values(:, 1, {:d}) = {:s};""".format(rownum, mvals), file=fp)
    print("""end""", file=fp)
    fp.close()


def write_most_base_case(ppc, fname):
    fp = open(fname, 'w')
    print('function mpc = basecase', file=fp)
    print('%% MATPOWER base case from PNNL TESP, fncsTSO2.py, model name', casename, file=fp)
    print("""mpc.version = '2';""", file=fp)
    print("""mpc.baseMVA = 100;""", file=fp)
    print("""%% bus_i  type  Pd  Qd  Gs  Bs  area  Vm  Va  baseKV  zone  Vmax  Vmin""", file=fp)
    print("""mpc.bus = [""", file=fp)
    write_array_rows(ppc['bus'], fp)
    print("""];""", file=fp)
    print ("""%% bus  Pg  Qg  Qmax  Qmin  Vg  mBase status  Pmax  Pmin  Pc1 Pc2 Qc1min  Qc1max  Qc2min  Qc2max  ramp_agc  ramp_10 ramp_30 ramp_q  apf""", file=fp)
    print("""mpc.gen = [""", file=fp)
    write_array_rows(ppc['gen'], fp)
    print("""];""", file=fp)
    print("""%% bus  tbus  r x b rateA rateB rateC ratio angle status  angmin  angmax""", file=fp)
    print("""mpc.branch = [""", file=fp)
    write_array_rows(ppc['branch'], fp)
    print("""];""", file=fp)
    print("""%% either 1 startup shutdown n x1 y1  ... xn  yn""", file=fp)
    print("""%%   or 2 startup shutdown n c(n-1) ... c0""", file=fp)
    print("""mpc.gencost = [""", file=fp)
    write_array_rows(ppc['gencost'], fp)
    print("""];""", file=fp)
    fp.close()


# update cost coefficients, set dispatchable load, put unresp+curve load on bus
def update_cost_and_load(ppc, for_optimization):
    bus = ppc['bus']
    gen = ppc['gen']
    gld_load = ppc['gld_load']
    genCost = ppc['gencost']
    bus_accum = ppc['bus_accum']
    curve = ppc['curve']
    if (for_optimization):
        for i in range(bus.shape[0]):  # erase the old LMP values
            bus[i, 13] = 0.0
    for row in ppc['DSO']:
        busnum = int(row[0])
        genidx = gld_load[busnum]['genidx']
        gld_scale = float(row[2])

        if (for_optimization):  # set up dispatchable loads for OPF or scheduling
            resp_max = gld_load[busnum]['resp_max'] * gld_scale
            unresp = gld_load[busnum]['unresp'] * gld_scale
            if ppc['solver'] == 'GLPK':
                c2 = 0.0
                c1 = gld_load[busnum]['c1']
                deg = 1
            else:
                c2 = gld_load[busnum]['c2']
                c1 = gld_load[busnum]['c1']
                deg = gld_load[busnum]['deg']
            # track the latest bid in the metrics
            bus_accum[str(busnum)][8] = unresp
            bus_accum[str(busnum)][9] = resp_max
            bus_accum[str(busnum)][10] = c1
            bus_accum[str(busnum)][11] = c2
            gen[genidx, 9] = -resp_max
            if deg == 2:
                genCost[genidx, 3] = 3
                genCost[genidx, 4] = 0.0
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
        else:  # turn off the dispatchable loads for regular power flow
            gen[genidx, 1] = 0  # p
            gen[genidx, 2] = 0  # q
            gen[genidx, 9] = 0  # pmin

        # setting the bus loads for OPF/MOST, or the regular power flow
        bus[busnum - 1, 2] = 0.0
        bus[busnum - 1, 3] = 0.0
        if curve:  # the baseline (curve) load component doesn't depend on GridLAB-D at all
            bus[busnum - 1, 2] += gld_load[busnum]['pcrv']
            bus[busnum - 1, 3] += gld_load[busnum]['qcrv']
        if for_optimization:  # only add the unresponsive load; resp_max is left dispatchable
            bus[busnum - 1, 2] += unresp
        else:  # for a regular power flow, use all of the actual GridLAB-D load
            bus[busnum - 1, 2] += gld_load[busnum]['p'] * gld_scale
            bus[busnum - 1, 3] += gld_load[busnum]['q'] * gld_scale


def tso_loop(bTestDAM=False, test_bids=None):
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

    ppc = tso.load_json_case(casename + '.json')
    ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'], OPF_ALG_DC=200)  # dc for
    ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'], PF_MAX_IT=20, PF_ALG=1)  # ac for power flow

    if ppc['solver'] == 'GLPK':  # can't use quadratic costs with GLPK solver
        ppc['gencost'][:, 3] = 2.0
        ppc['gencost'][:, 4] = ppc['gencost'][:, 5]
        ppc['gencost'][:, 5] = ppc['gencost'][:, 6]
        ppc['gencost'][:, 6] = 0.0

    numGen = ppc['gen'].shape[0]

    for col in range(16, 20):  # no physical constraint on ramping
        ppc['gen'][:, col] = np.inf

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
    baseS = int(ppc['baseMVA'])  # base_S in ercot_8.json baseMVA
    baseV = int(ppc['bus'][0, 9])  # base_V in ercot_8.json bus row 0-7, column 9, should be the same for all buses

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
    tso.make_dictionary(ppc)

    # initialize for variable wind
    wind_plants = {}
    tnext_wind = tmax + 2 * dt  # by default, never fluctuate the wind plants
    if wind_period > 0:
        wind_plants = make_wind_plants(ppc)
        if len(wind_plants) < 1:
            print('warning: wind power fluctuation requested, but there are no wind plants in this case')
        else:
            gen = ppc['gen']
            genCost = ppc['gencost']
            genFuel = ppc['genfuel']
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
            numGen = ppc['gen'].shape[0]
    else:
        print('disabling all the wind plants')
        shutoff_wind_plants(ppc)

    # initialize for day-ahead, OPF and time stepping
    ts = 0
    Pload = 0
    tnext_opf = 0
    wind_hour = -1
    # listening to GridLAB-D and its auction objects
    gld_load = {}  # key on bus number

    # TODO: more efficient to concatenate outside a loop
    dsoBus = ppc['DSO']
    for i in range(dsoBus.shape[0]):
        busnum = i + 1
        genidx = ppc['gen'].shape[0]
        # I suppose a generator for a summing generators on a bus?
        ppc['gen'] = np.concatenate(
            (ppc['gen'],
             np.array([[busnum, 0, 0, 0, 0, 1, 250, 1, 0, -5, 0, 0, 0, 0, 0, 0, np.inf, np.inf, np.inf, np.inf, 0]])))
        ppc['gencost'] = np.concatenate(
            (ppc['gencost'], np.array([[2, 0, 0, 2, 30.0, 0.0, 0.0]])))
        ppc['genfuel'] = np.concatenate(
            (ppc['genfuel'], np.array([['']])))
        gld_scale = float(dsoBus[i, 2])
        initial_load = 0.5 * float(dsoBus[i, 7]) / gld_scale
        gld_load[busnum] = {'pcrv': 0, 'qcrv': 0,
                            'p': float(dsoBus[i, 7]) / gld_scale, 'q': float(dsoBus[i, 8]) / gld_scale,
                            'unresp': initial_load, 'resp_max': initial_load, 'c2': 0, 'c1': 18.0, 'deg': 1,
                            'genidx': genidx}
        if noScale:
            dsoBus[i, 2] = 1  # gld_scale

    # set up the MOST UC/ED structures
    numResp = ppc['gen'].shape[0] - numGen
    # assuming all units will "run" through the first day
    unit_state = np.ones(numGen + numResp) * 24.0
    # set status (gen[7]) to this if bDAMValid
    unit_schedule = np.ones([numGen + numResp, hours_in_a_day])
    # set Pg (gen[1]) to this if bDAMValid and unit_schedule > 0
    unit_dispatch = np.zeros([numGen + numResp, hours_in_a_day])
    next_unit_schedule = None
    next_unit_dispatch = None
    # don't apply zero dispatch to the units on first day
    bDAMValid = False
    print('numGen = {:d}, numResp = {:d}'.format(numGen, numResp))
    print('starting unit_state', unit_state)
    print('starting unit_schedule', unit_schedule)
    print('starting unit_dispatch', unit_dispatch)

    # interval for metrics recording
    tnext_metrics = 0

    loss_accum = 0
    conv_accum = True
    n_accum = 0
    bus_accum = {}
    gen_accum = {}

    for row in ppc['DSO']:
        busnum = int(row[0])
        bus_accum[str(busnum)] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]

    for i in range(ppc['gen'].shape[0]):
        gen_accum[str(i + 1)] = [0, 0, 0]

    ppc['bus_accum'] = bus_accum
    ppc['gen_accum'] = gen_accum
    ppc['gld_load'] = gld_load

    total_bus_num = ppc['DSO'].shape[0]
    day_ahead_bid = {}  # keyed on bus number 1..nbus
    for row in ppc['DSO']:
        busnum = row[0]
        key = row[1]
        day_ahead_bid[key] = {'unresp_mw': np.zeros([hours_in_a_day], dtype=float),
                              'resp_max_mw': np.zeros([hours_in_a_day], dtype=float),
                              'resp_c2': np.zeros([hours_in_a_day], dtype=float),
                              'resp_c1': np.zeros([hours_in_a_day], dtype=float),
                              'resp_deg': np.zeros([hours_in_a_day], dtype=float)}

    if bTestDAM:
        write_most_dam_files(ppc, test_bids, wind_plants, unit_state, 'dam')
        f, Pg, Pd, Pf, u, lamP = solve_most_dam_case(ppc['MostCommand'], 'dam')
        print('Objective = ', f, 'u, Pg, Pd and lamP follow')
        print(u)
        print(Pg)
        print(Pd)
        print(lamP)
        return

    if most:
        write_most_base_case(ppc, 'basecase.m')
        rBus, rBranch, rGen, rGenCost = solve_most_rtm_case(ppc['MostCommand'], 'solvebasecase.m')
        bus = ppc['bus']
        for i in range(bus.shape[0]):  # starting LMP values
            bus[i, 13] = float(rBus[i][13])

    # Set column header for output files
    line = 'seconds, OPFconverged, TotalLoad, TotalGen, SwingGen, RespCleared'
    line2 = 'seconds, PFConverged, TotalLoad, TotalGen, TotalLoss, SwingGen'
    for i in range(ppc['DSO'].shape[0]):
        line += ', ' + 'LMP' + str(i + 1)
        line2 += ', ' + 'v' + str(i + 1)
    w = n = c = g = 0
    genFuel = ppc['genfuel']
    for i in range(numGen):
        fuel = genFuel[i][0]
        if 'wind' in fuel:
            w += 1
            line += ', wind' + str(w)
            line2 += ', wind' + str(w)
        elif 'nuclear' in fuel:
            n += 1
            line += ', nuc' + str(n)
            line2 += ', nuc' + str(n)
        elif 'coal' in fuel:
            c += 1
            line += ', coal' + str(c)
            line2 += ', coal' + str(c)
        else:
            g += 1
            line += ', gas' + str(g)
            line2 += ', gas' + str(g)
    line += ', TotalWindGen'
    line2 += ', TotalWindGen'

    op = open(casename + '_opf.csv', 'w')
    vp = open(casename + '_pf.csv', 'w')
    print(line, sep=', ', file=op, flush=True)
    print(line2, sep=', ', file=vp, flush=True)

    # MAIN LOOP starts here
    fncs.initialize()

    while ts <= tmax:
        # we have to know the day, minute and hour in order to time the market clearings
        ds = timedelta(seconds=ts)
        days = int(ds.days)
        quotient, remainder = divmod(ds.seconds, 60)
        minutes = int(quotient)
        seconds = int(remainder)
        quotient, remainder = divmod(minutes, 60)
        hours = int(quotient)
        minutes = int(remainder)

        # temporary references into ppc
        gen = ppc['gen']
        gld_load = ppc['gld_load']
        dsoBus = ppc['DSO']

        # start by getting the latest inputs from GridLAB-D and the auction
        events = fncs.get_events()
        for topic in events:
            val = fncs.get_value(topic)
            # getting the latest inputs from DSO Real Time bid
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
            # getting the latest inputs from GridlabD or DSO stub
            elif 'SUBSTATION' in topic:  # gld
                busnum = int(topic[10:])
                p, q = parse_mva(val)
                gld_load[busnum]['p'] = float(p)  # MW
                gld_load[busnum]['q'] = float(q)  # MW
            # getting the latest inputs from DSO day Ahead bid
            elif 'DA_BID_' in topic:
                new_da_bid = True
                substation = 'SUBSTATION' + topic[7:]
                bus_da_bid = json.loads(val)
                # each array[hours_in_a_day]
                for arrayName in ['unresp_mw', 'resp_max_mw', 'resp_c2', 'resp_c1', 'resp_deg']:
                    day_ahead_bid[substation][arrayName] = bus_da_bid[arrayName]

        # fluctuate the wind plants
        if ts >= tnext_wind:
            wind_hour += 1
            if wind_hour == 24:
                wind_hour = 0
            if ts % (wind_period * 24) == 0:
                # copy next day to today
                for j in range(hours_in_a_day):
                    for key, row in wind_plants.items():
                        row[9][j] = row[9][j + 24]
                # make next day forecast
                for j in range(hours_in_a_day):
                    for key, row in wind_plants.items():
                        # return dict with rows like
                        # wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, [24 hour p]]
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
                        # set the max and min
                        if gen[int(key), 8] < p:
                            gen[int(key), 8] = p
                        if gen[int(key), 9] > p:
                            gen[int(key), 9] = p
                        row[9][j + 24] = p
                        if ts == 0:
                            row[9][j] = p

            for key, row in wind_plants.items():
                # reset the unit capacity; this will 'stick' for the next wind_period
                gen[row[10], 1] = row[9][wind_hour]
                gen[row[10], 8] = row[9][wind_hour]
            tnext_wind += wind_period
            print('========================== Fluctuating Wind at', ts)
            for key, row in wind_plants.items():
                csvStr = ','.join('{:2f}'.format(item) for item in row[9])
                print('{:s}{:s}'.format(key, csvStr))
        #        print (key, row[9])

        # shape the baseline loads if using the curve
        for row in dsoBus:
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

        if most and bDAMValid:
            if (minutes == 0) and (seconds == 0):
                if hours == 0:
                    print('#### At midnight: ts = {:d}, to rotate UC/ED'.format(ts))
                    unit_schedule = deepcopy(next_unit_schedule)
                    unit_dispatch = deepcopy(next_unit_dispatch)
                    print('now unit_schedule =', unit_schedule)
                    print('now unit_dispatch =', unit_dispatch)
                if days > 0:  # we have DAM valid in the middle of first day, but don't use until day 1
                    print('  #### Top of the hour {:d}: ts = {:d}, to implement UC/ED'.format(hours, ts))
                    ppc['gen'][:, 7] = unit_schedule[:, hours]
                    for i in range(numGen):
                        fuel = genFuel[i][0]
                        print('   setting {:d} ({:s}) from {:.2f} to {:.2f}'
                              .format(i, fuel, ppc['gen'][i, 1], unit_dispatch[i, hours]))
                        if 'wind' not in fuel:
                            ppc['gen'][i, 1] = unit_dispatch[i, hours]
                    print(ppc['gen'])

        # run multi-period optimization in MOST to establish the next day's unit commitment and dispatch schedule
        # Run the day ahead market (DAM) at noon every day
        if most and (hours == 12) and (minutes == 0) and (seconds == 0):
            file_time = 'd{:d}_h{:d}_m{:d}_'.format(days, hours, minutes)
            most_DAM_case_file = file_time + 'dam'
            update_cost_and_load(ppc, True)
            print('Running MOST DAM at day {:d}'.format(days))
            print(day_ahead_bid)
            write_most_dam_files(ppc, day_ahead_bid, wind_plants, unit_state, most_DAM_case_file)
            f, Pg, Pd, Pf, u, lamP = solve_most_dam_case(ppc['MostCommand'], most_DAM_case_file)
            bDAMValid = True
            print('#### Objective = {:.2f}'.format(f))
            next_unit_schedule = u
            next_unit_dispatch = Pg
            print('next_unit_schedule', next_unit_schedule)
            print('next_unit_dispatch', next_unit_dispatch)
            for i in range(unit_state.shape[0]):
                hours_run = np.sum(unit_schedule[i])
                if (hours_run > 23.5) and (unit_state[i] > 0.0):
                    unit_state[i] += 24.0
                elif (hours_run < 0.5) and (unit_state[i] < 0.0):
                    unit_state[i] -= 24.0
                else:  # the unit turned ON or OFF sometime during the day
                    if unit_schedule[i][23] > 0.5:  # will end the day ON, how many hours will it have been ON?
                        unit_state[i] = 1.0
                        for j in range(22, -1, -1):
                            if unit_schedule[i][j] > 0.0:
                                unit_state[i] += 1.0
                            else:
                                break
                    else:  # will end the day OFF, how many hours will it have been OFF?
                        unit_state[i] = -1.0
                        for j in range(22, -1, -1):
                            if unit_schedule[i][j] < 0.5:
                                unit_state[i] -= 1.0
                            else:
                                break
            print('unit_state for next day DAM', unit_state)

        if ts >= tnext_opf:
            update_cost_and_load(ppc, True)

            if (ts == 21600) or (ts == 64800) or (ts == 75600):
                write_most_base_case(ppc, 'rtmcase_{:d}.m'.format(ts))
            #      rBus, rBranch, rGen, rGenCost = solve_most_rtm_case(ppc['MostCommand'], 'solvertmcase.m')
            ropf = pp.runopf(ppc, ppopt_market)
            if ropf['success'] == False:
                ropf['bus'][:, 13] = ppc['lmp_cap']
                conv_accum = False
            opf_bus = deepcopy(ropf['bus'])
            opf_gen = deepcopy(ropf['gen'])
            #      tso.print_mod_load(ppc['bus'], ppc['DSO'], gld_load, 'GLD Load after OPF', ts)
            #      print_bus_lmps ('### from OPF at {:d}'.format(ts), opf_bus)
            #      tso.summarize_opf(ropf)
            Pcleared = 0
            Pproduced = 0
            Pswing = 0
            for idx in range(opf_gen.shape[0]):
                punit = opf_gen[idx, 1]
                if opf_gen[idx, 0] == swing_bus:
                    Pswing += punit
                if punit > 0.0:
                    Pproduced += punit
                elif punit < 0.0:
                    Pcleared -= punit

            sum_w = 0
            for key, row in wind_plants.items():
                sum_w += gen[row[10], 1]

            line = str(ts) + ',' + str(ropf['success']) + ','
            line += '{: .2f}'.format(opf_bus[:, 2].sum()) + ','
            line += '{: .2f}'.format(Pproduced) + ','
            line += '{: .2f}'.format(Pswing) + ','
            line += '{: .2f}'.format(Pcleared)
            for idx in range(opf_bus.shape[0]):
                line += ',' + '{: .4f}'.format(opf_bus[idx, 13])
            for idx in range(opf_gen.shape[0]):
                if numGen > idx:
                    line += ',' + '{: .2f}'.format(opf_gen[idx, 1])
            line += ',{: .2f}'.format(sum_w)
            print(line, sep=', ', file=op, flush=True)

            tnext_opf += period

        # always run the regular power flow for voltages and performance metrics
        ppc['bus'][:, 13] = opf_bus[:, 13]  # set the lmp; INVALIDATES PREVIOUS ASSIGNMENT
        ppc['gen'][:, 1] = opf_gen[:, 1]  # set the economic dispatch; INVALIDATES PREVIOUS ASSIGNMENT

        update_cost_and_load(ppc, False)
        rpf = pp.runpf(ppc, ppopt_regular)
        # TODO: add a check if does not converge, switch to DC
        if not rpf[0]['success']:
            conv_accum = False
            print('rpf did not converge at', ts)
        rBus = rpf[0]['bus']
        rGen = rpf[0]['gen']
        #    tso.print_mod_load (ppc['bus'], ppc['DSO'], gld_load, 'GLD Load after PF', ts)
        #    tso.print_bus_lmps (' $$ from RPF at {:d}'.format(ts), rBus)
        #    tso.summarize_opf (rpf[0])

        Pload = rBus[:, 2].sum()
        Pgen = rGen[:, 1].sum()
        Ploss = Pgen - Pload
        Pswing = 0
        for idx in range(rGen.shape[0]):
            if rGen[idx, 0] == swing_bus:
                Pswing += rGen[idx, 1]

        line = str(ts) + ', ' + str(rpf[0]['success']) + ','
        line += '{: .2f}'.format(Pload) + ',' + '{: .2f}'.format(Pgen) + ','
        line += '{: .2f}'.format(Ploss) + ',' + '{: .2f}'.format(Pswing)
        for idx in range(rBus.shape[0]):
            line += ',' + '{: .2f}'.format(rBus[idx, 7])  # bus per-unit voltages
        for idx in range(numGen):
            line += ',' + '{: .2f}'.format(rGen[idx, 1])
        sum_w = 0
        for key, row in wind_plants.items():
            sum_w += rGen[row[10], 1]
        line += ',{: .2f}'.format(sum_w)
        print(line, sep=', ', file=vp, flush=True)

        # update the metrics
        dsoBus = ppc['DSO']
        bus_accum = ppc['bus_accum']
        gen_accum = ppc['gen_accum']
        bus = ppc['bus']
        gen = ppc['gen']
        gld_load = ppc['gld_load']
        n_accum += 1
        loss_accum += Ploss
        for i in range(dsoBus.shape[0]):
            busnum = dsoBus[i, 0]
            busidx = int(busnum) - 1
            genidx = gld_load[busidx + 1]['genidx']
            row = rBus[busidx].tolist()
            # publish the bus VLN and LMP [$/kwh] for GridLAB-D
            bus_vln = 1000.0 * row[7] * row[9] / math.sqrt(3.0)
            fncs.publish('three_phase_voltage_Bus' + busnum, bus_vln)
            if most:
                lmp = float(bus[busidx, 13]) * 0.001
                clr = -1.0 * float(opf_gen[genidx, 1])
            else:
                lmp = float(opf_bus[busidx, 13]) * 0.001
                clr = -1.0 * float(opf_gen[genidx, 1])
            fncs.publish('LMP_Bus' + busnum, lmp)  # publishing $/kwh
            fncs.publish('CLR_Bus' + busnum, clr)  # publishing cleared responsive load
            # print ('FNCS Published CLR_Bus' + busnum, clr)
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
            for i in range(dsoBus.shape[0]):
                busnum = dsoBus[i, 0]
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


if __name__ == '__main__':
    if len(sys.argv) > 1:
        fp = open(sys.argv[1], 'r')
        da_bids = json.load(fp)
        fp.close()
        tso_loop(True, da_bids)
        quit()
    tso_loop()
