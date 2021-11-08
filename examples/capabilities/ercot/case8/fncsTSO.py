#   Copyright (C) 2017-2020 Battelle Memorial Institute
import numpy as np
import scipy.interpolate as ip
import pypower.api as pp

# the order is important in python 3.8 for fncs and api in tesp_support
import tesp_support.fncs as fncs
import tesp_support.api as tesp

import json
import math
from copy import deepcopy
import psst.cli as pst
import pandas as pd
import sys, os

casename = 'ercot_8'
ames_DAM_case_file = './../DAMReferenceModel.dat'
ames_RTM_case_file = './../RTMReferenceModel.dat'
ames_base_case_file = os.path.expandvars('$TESPDIR/models/pypower/ames_base_case.m')

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
        else:                          # 1D array, printed flat
            print ('{:s} has {:d} elements'.format (lbl, nrows))
            print (' '.join(fmt.format(item) for item in A), flush=True)
    else:                              # single value
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
    ppdict = {'baseMVA': ppc['baseMVA'], 'dsoBuses': fncsBuses, 'generators': generators, 'UnitsOut': unitsout,
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


def dist_slack(mpc, prev_load):
  ## this section will calculate the delta power from previous cycle using the prev_load
  # if previous load is equal to 0 we assume this is the first run and will
  # calculate delta power based on the difference between real power and real
  # generation

  tot_load = sum(mpc['bus'][:, 2])

  if prev_load == 0:
    del_P = tot_load - sum(mpc['gen'][np.where(mpc['gen'][:, 7] == 1)[0], 1])
  else:
    del_P = tot_load - prev_load

  # if mpc.governor is not passed on then the governor assumes default parameters
  if 'governor' not in mpc:
    mpc['governor'] = {'coal': 0.00, 'gas':  0.05, 'nuclear': 0, 'hydro': 0.05}

  ramping_time = int(mpc["Period"])/60  # in minutes
  ramping_capacity = np.multiply(mpc['gen'][:, 16], (mpc['gen'][:, 8]))*(ramping_time / 100)

  ## .............Getting indexes of fuel type if not passed as an input argument.............................................
  # checking fuel type to get index
  # checking generator status to make sure generator is active
  # checking generator regulation value to make sure generator participates in governor action
  # if fuel type matrix is not available we will assume all generators are gas turbines

  coal_idx = []
  hydro_idx = []
  nuclear_idx = []
  gas_idx = []
  governor_capacity = 0

  if 'genfuel' in mpc:
    for i in range(len(mpc['genfuel'])):
      if (mpc['genfuel'][i, 0] == "coal") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['coal'] != 0):
        coal_idx.append(i)
        mpc['gen'][i, 16] = 5/100 * mpc['gen'][i, 8] # ramp_rate (%) * PG_max (MW) / 100  -> (MW)
        governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['coal'])
      elif (mpc['genfuel'][i, 0] == "gas") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['gas'] != 0):
        gas_idx.append(i)
        if mpc['gen'][i, 8] < 200:
          mpc['gen'][i, 16] = 2.79  # (MW)
        elif mpc['gen'][i, 8] < 400:
          mpc['gen'][i, 16] = 7.62  # (MW)
        elif mpc['gen'][i, 8] < 600:
          mpc['gen'][i, 16] = 4.8   # (MW)
        elif mpc['gen'][i, 8] >= 600:
          mpc['gen'][i, 16] = 26.66 # (MW)
        governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['gas'])
      elif (mpc['genfuel'][i, 0] == "nuclear") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['nuclear'] != 0):
        nuclear_idx.append(i)
        mpc['gen'][i, 16] = 6.98  # (%)
        governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['nuclear'])
      elif (mpc['genfuel'][i, 0] == "hydro") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['hydro'] != 0):
        hydro_idx.append(i)
        mpc['gen'][i, 16] = 5/100 * mpc['gen'][i, 8] # ramp_rate (%) * PG_max (MW) / 100  -> (MW)
        governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['hydro'])
  else:
    gas_idx = np.where(mpc['gen'][:, 7] == 1)[0]
    governor_capacity = sum(mpc['gen'][gas_idx, 8] * (.05 / mpc['governor']['gas']))
    for i in range(len(mpc['gen'])):
      if mpc['gen'][i, 8] < 200:
        mpc['gen'][i, 16] = 2.79  # (MW)
      elif mpc['gen'][i, 8] < 400:
        mpc['gen'][i, 16] = 7.62  # (MW)
      elif mpc['gen'][i, 8] < 600:
        mpc['gen'][i, 16] = 4.8  # (MW)
      elif mpc['gen'][i, 8] >= 600:
        mpc['gen'][i, 16] = 26.66  # (MW)
  ramping_capacity = mpc['gen'][:, 16]*(ramping_time)   #ramp rate (MW/min) * ramp time (min)  ->  (MW)


  ## ..........................Sorting the generators based on capacity..................................
  gov_R = []
  gov_idx =[]
  if len(coal_idx) != 0:
    gov_idx.append(coal_idx)
    gov_R = np.append(gov_R, mpc['governor']['coal']*np.ones(len(coal_idx)))
  if len(hydro_idx) != 0:
    gov_idx.append(hydro_idx)
    gov_R = np.append(gov_R, mpc['governor']['hydro'] * np.ones(len(hydro_idx)))
  if len(nuclear_idx) != 0:
    gov_idx.append(nuclear_idx)
    gov_R = np.append(gov_R, mpc['governor']['nuclear'] * np.ones(len(nuclear_idx)))
  if len(gas_idx) != 0:
    gov_idx.append(gas_idx)
    gov_R = np.append(gov_R, mpc['governor']['gas'] * np.ones(len(gas_idx)))

  gov_R = gov_R.tolist()
  capacity = mpc['gen'][gov_idx, 8][0]
  I = np.argsort(capacity)
  index = [gov_idx[0][i] for i in I]  #gov_idx[I]

  ## ...........................................Governor Action........................................

  del_P_pu = del_P / governor_capacity
  del_f = .05 * del_P_pu

  del_P_new = del_P

  k = 1
  l = 1
  m = 1
  gen_update = deepcopy(mpc['gen'][:, 1])
  for i in range(len(index)):
    up_ramp_flag = 0
    max_flag = 0
    down_ramp_flag = 0
    min_flag = 0
    gen_update[index[i]] = mpc['gen'][index[i], 1] + mpc['gen'][index[i], 8] * del_f/gov_R[I[i]]  # P (MW) + del_P (MW)

    # .........................For Increasing Loads.............................
    # Checking Ramp Rates
    if mpc['gen'][index[i], 8] * del_f / gov_R[I[i]] > ramping_capacity[index[i]]:   # if del_P (MW) > del_P_max (MW)
      up_ramp_flag = 1
      gen_update[index[i]] = mpc['gen'][index[i], 1] + ramping_capacity[index[i]];   # P (MW) + del_P_max (MW)
      del_P_new = del_P_new - ramping_capacity[index[i]]
      governor_capacity = governor_capacity - mpc['gen'][index[i], 8] * .05 / gov_R[I[i]]   # total capacity (MW) - del_P_max MW) * del_P (pu) -> (MW)

    # Checking generation Limits
    if gen_update[index[i]] > mpc['gen'][index[i], 8]:      # PG > PG_max (MW)
      max_flag = 1                                          # limit is reached
      # both the limits are reached
      if (up_ramp_flag == 1) & (max_flag == 1):
        gen_update[index[i]] = mpc['gen'][index[i], 8]
        del_P_new = del_P_new - (mpc['gen'][index[i], 8] - mpc['gen'][index[i], 1]) + ramping_capacity[index[i]]
        # Total_capacity already taken off in the ramp stage
        # only generationn capacity limit is reached
      else:
        gen_update[index[i]] = mpc['gen'][index[i], 8]
        del_P_new = del_P_new - (mpc['gen'][index[i], 8] - mpc['gen'][index[i], 1])
        governor_capacity = governor_capacity - (mpc['gen'][index[i], 8] * (.05 / (gov_R[I[i]])))


    # ................................For Decreasing Loads.....................................
    # checking for negative ramping

    if mpc['gen'][index[i], 8] * del_f / gov_R[I[i]] < -1 * ramping_capacity[index[i]]:
      down_ramp_flag = 1
      gen_update[index[i]] = mpc['gen'][index[i], 1] - ramping_capacity[index[i]];
      del_P_new = del_P_new - (-1 * ramping_capacity[index[i]])
      governor_capacity = governor_capacity - mpc['gen'][index[i], 8] * .05 / gov_R[I[i]]

    if (gen_update[index[i]] < mpc['gen'][index[i], 9]):
      min_flag = 1
      if (down_ramp_flag == 1) & (min_flag == 1):
        gen_update[index[i]] = mpc['gen'][index[i], 9]
        del_P_new = del_P_new - (mpc['gen'][index[i], 9] - mpc['gen'][index[i], 1]) + (-1 * ramping_capacity[index[i]])
      # Total_capacity already taken off in the ramp stage
      # only generationn capacity limit is reached
      else:
        gen_update[index[i]] = mpc['gen'][index[i], 9]
        del_P_new = del_P_new - (mpc['gen'][index[i], 9] - mpc['gen'][index[i], 1])
        governor_capacity = governor_capacity - mpc['gen'][index[i], 8] * .05 / gov_R[I[i]]

    if governor_capacity != 0:
      del_P_pu = del_P_new / governor_capacity
    else:
      del_P_pu = 0
    del_f = .05 * del_P_pu

  # updating the generators gen_update
  return gen_update


def tso_loop():

    def scucDAM(data, output, solver):
        c, ZonalDataComplete, priceSenLoadData = pst.read_model(data.strip("'"))
        if day > -1:
            model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData)
            model.solve(solver=solver)
            instance = model._model

            uc = "./" + file_time + "uc.dat"
            with open(uc, 'w') as outfile:
                results = {}
                for g in instance.Generators.data():
                    for t in instance.TimePeriods:
                        results[(g, t)] = instance.UnitOn[g, t]

                for g in sorted(instance.Generators.data()):
                    outfile.write("%s\n" % str(g).ljust(8))
                    for t in sorted(instance.TimePeriods):
                        outfile.write("% 1d \n" % (int(results[(g, t)].value + 0.5)))

            uc_df = pd.DataFrame(pst.read_unit_commitment(uc.strip("'")))
        else:
            uc_df = write_default_schedule()
        c.gen_status = uc_df.astype(int)

        model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData)
        model.solve(solver=solver)
        instance = model._model

        DA_LMPs = [[0 for x in range(hours_in_a_day)] for y in range(total_bus_num)]
        DA_LMPs_pub = [[0 for x in range(hours_in_a_day)] for y in range(total_bus_num)]
        for h, r in model.results.lmp.iterrows():
            for b, lmp in sorted(r.iteritems()):
                bn = int(b[3:])
                if lmp is None:
                    lmp = 0
                DA_LMPs[bn - 1][h] = abs(round(lmp, 2))  # publishing $/p.u.h
                DA_LMPs_pub[bn - 1][h] = abs(round(lmp / baseS, 4))  # publishing $/MWh

        for i in range(fncsBus.shape[0]):
            lmps = {'bus' + str(i + 1): [DA_LMPs_pub[i]]}
            fncs.publish('LMP_DA_Bus_' + str(i + 1), json.dumps(lmps))

#        print("DA line power")
#        print(model.results.line_power, flush=True)

        # with open(output, 'w') as outfile:  #dispatch
        #   results = {}
        #   resultsPowerGen = {}
        #   instance = model._model
        #   for g in instance.Generators.value:
        #     for t in instance.TimePeriods:
        #       results[(g, t)] = instance.UnitOn[g, t]
        #       resultsPowerGen[(g, t)] = instance.PowerGenerated[g, t]
        #
        #   for g in sorted(instance.Generators.value):
        #     outfile.write("%s\n" % str(g).ljust(8))
        #     for t in sorted(instance.TimePeriods):
        #       outfile.write("% 1d %6.3f %6.2f %6.2f\n" % (
        #       int(results[(g, t)].value + 0.5), resultsPowerGen[(g, t)].value, 0.0, 0.0))  # not sure why DK added 0.0, 0.0

        dispatch = {}
        try:
            for g in sorted(instance.Generators.data()):
                dispatch[g] = []
                for t in sorted(instance.TimePeriods):
                    dispatch[g].append(instance.PowerGenerated[g, t].value * baseS)
        except:
            return uc_df, {}, [[]]

        # with open('./SCUCSVPOutcomes.dat', 'w') as outfile:
        #   instance = model._model
        #   SlackVariablePower = {}
        #   for b in instance.Buses.value:
        #     for t in instance.TimePeriods:
        #       SlackVariablePower[(b, t)] = instance.LoadGenerateMismatch[b, t]
        #
        #   for b in sorted(instance.Buses.value):
        #     outfile.write("%s\n" % str(b).ljust(8))
        #     for t in sorted(instance.TimePeriods):
        #       outfile.write(" %6.2f \n" % (SlackVariablePower[(b, t)].value))
        #
        # if (len(priceSenLoadData) is not 0):
        #     with open('./SCUCPriceSensitiveLoad.dat', 'w') as outfile:
        #         instance = model._model
        #         PriceSenLoadDemand = {}
        #         for l in instance.PriceSensitiveLoads.value:
        #             for t in instance.TimePeriods:
        #                 PriceSenLoadDemand[(l, t)] = instance.PSLoadDemand[l, t].value
        #
        #         for l in sorted(instance.PriceSensitiveLoads.value):
        #             outfile.write("%s\n" % str(l).ljust(8))
        #             for t in sorted(instance.TimePeriods):
        #                 outfile.write(" %6.2f \n" % (PriceSenLoadDemand[(l, t)]))
            # print('PriceSenLoadDemand = \n', PriceSenLoadDemand)

        lseDispatch = {}
        if (len(priceSenLoadData) is not 0):
            for ld in sorted(instance.PriceSensitiveLoads.data()):
                lseDispatch[ld] = []
                for t in sorted(instance.TimePeriods):
                    lseDispatch[ld].append(instance.PSLoadDemand[ld, t].value)
                    # print(str(ld) + " cleared quantity for hour " + str(t) + " --> " + str(instance.PSLoadDemand[ld, t].value), flush=True)
            for i in range(fncsBus.shape[0]):
                gld_scale = float(fncsBus[i, 2])
                lse = 'LSE' + str(i + 1)
                try:
                    row = lseDispatch[lse]
                except:
                    # print("LSE "+str(i+1) + " is not price sensitive, so returning zero for it", flush=True)
                    row = np.zeros(24).tolist() # hard-coded to be 24
                for z in range(len(row)):
                   row[z] = row[z] / gld_scale * baseS
                fncs.publish('cleared_q_da_' + str(i + 1), json.dumps(row))
        else:
            for i in range(fncsBus.shape[0]):
                row = []
                for z in range(24):
                   row.append(respMaxMW[i][z] + unRespMW[i][z])
                fncs.publish('cleared_q_da_' + str(i + 1), json.dumps(row))

        return uc_df, dispatch, DA_LMPs

    def scedRTM(data, uc_df, output, solver):
        c, ZonalDataComplete, priceSenLoadData = pst.read_model(data.strip("'"))
        c.gen_status = uc_df.astype(int)

        model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData)
        model.solve(solver=solver)
        instance = model._model

        # with open('./SCEDSVPOutcomes.dat', 'w') as outfile:
        #   instance = model._model
        #   SlackVariablePower = {}
        #   for b in instance.Buses.value:
        #     for t in instance.TimePeriods:
        #       SlackVariablePower[(b, t)] = instance.LoadGenerateMismatch[b, t]
        #
        #   for b in sorted(instance.Buses.value):
        #     outfile.write("%s\n" % str(b).ljust(8))
        #     for t in sorted(instance.TimePeriods):
        #       outfile.write(" %6.2f \n" % (SlackVariablePower[(b, t)].value))

        RT_LMPs = [[0 for x in range(TAU)] for y in range(total_bus_num)]
        RT_LMPs_pub = [[0 for x in range(TAU)] for y in range(total_bus_num)]
        for h, r in model.results.lmp.iterrows():
            for b, lmp in sorted(r.iteritems()):
                bn = int(b[3:])
                if lmp is None:
                    lmp = 0
                RT_LMPs[bn - 1][h] = abs(round(lmp * 12, 2))  # publishing $/p.u.h
                RT_LMPs_pub[bn - 1][h] = abs(round(lmp * 12 / baseS, 4))  # publishing $/MWh
            if h == TAU:
                break

        for i in range(fncsBus.shape[0]):
            lmps = {'bus' + str(i + 1): [RT_LMPs_pub[i]]}
            fncs.publish('LMP_RT_Bus_' + str(i + 1), json.dumps(lmps))  # publishing $/kwh

        #print("RT line power")
        #print(model.results.line_power, flush=True)

        # with open(output.strip("'"), 'w') as f:
        #   f.write("LMP\n")
        #   # click.echo("..." + str(model.results.lmp))
        #   for h, r in model.results.lmp.iterrows():
        #     bn = 1
        #     for _, lmp in r.iteritems():
        #       if lmp is None:
        #         lmp = 0
        #       f.write(str(bn) + ' : ' + str(h + 1) + ' : ' + str(round(lmp, 2)) + "\n")
        #       bn = bn + 1
        #   f.write("END_LMP\n")
        #
        #   f.write("GenCoResults\n")
        #   instance = model._model
        #
        #   for g in instance.Generators.value:
        #     f.write("%s\n" % str(g).ljust(8))
        #     for t in instance.TimePeriods:
        #       f.write("Minute: {}\n".format(str(t + 1)))
        #       f.write("\tPowerGenerated: {}\n".format(round(instance.PowerGenerated[g, t].value, 3)))
        #       f.write("\tProductionCost: {}\n".format(round(instance.ProductionCost[g, t].value, 3)))
        #       f.write("\tStartupCost: {}\n".format(round(instance.StartupCost[g, t].value, 3)))
        #       f.write("\tShutdownCost: {}\n".format(round(instance.ShutdownCost[g, t].value, 3)))
        #   f.write("END_GenCoResults\n")
        #
        #   f.write("VOLTAGE_ANGLES\n")
        #   for bus in sorted(instance.Buses):
        #     for t in instance.TimePeriods:
        #       f.write('{} {} : {}\n'.format(str(bus), str(t + 1), str(round(instance.Angle[bus, t].value, 3))))
        #   f.write("END_VOLTAGE_ANGLES\n")
        #
        #   # Write out the Daily LMP
        #   # f.write("DAILY_BRANCH_LMP\n")
        #   # f.write("END_DAILY_BRANCH_LMP\n")
        #   # Write out the Daily Price Sensitive Demand
        #   # f.write("DAILY_PRICE_SENSITIVE_DEMAND\n")
        #   # f.write("END_DAILY_PRICE_SENSITIVE_DEMAND\n")
        #   # Write out which hour has a solution
        #
        #   f.write("HAS_SOLUTION\n")
        #   h = 0
        #   max_hour = 24  # FIXME: Hard-coded number of hours.
        #   while h < max_hour:
        #     f.write("1\t")  # FIXME: Hard-coded every hour has a solution.
        #     h += 1
        #   f.write("\nEND_HAS_SOLUTION\n")

        dispatch = {}
        try:
            for g in sorted(instance.Generators.data()):
                dispatch[g] = []
                for t in sorted(instance.TimePeriods):
                    dispatch[g].append(instance.PowerGenerated[g, t].value * baseS)
                    if t == TAU:
                        break
        except:
            return {}, []

        lseDispatch = {}
        if (len(priceSenLoadData) is not 0):
            for ld in sorted(instance.PriceSensitiveLoads.data()):
                lseDispatch[ld] = []
                for t in sorted(instance.TimePeriods):
                    lseDispatch[ld].append(instance.PSLoadDemand[ld, t].value)

            for i in range(fncsBus.shape[0]):
                gld_scale = float(fncsBus[i, 2])
                lse = 'LSE' + str(i + 1)
                try:
                    row = lseDispatch[lse]
                except:
                    # print("LSE "+str(i+1) + " is not price sensitive, so returning zero for it", flush=True)
                    row = np.zeros(TAU).tolist()

                for z in range(len(row)):
                    row[z] = row[z] / gld_scale * baseS
                    bus[i, 2] += row[z]
                    bus[i, 3] += row[z] * (float(fncsBus[i, 4]) / float(fncsBus[i, 3]))  # powerfactor
                fncs.publish('cleared_q_rt_' + str(i + 1), json.dumps(row))
        else:
            for i in range(fncsBus.shape[0]):
                busnum = i + 1
                gld_scale = float(fncsBus[i, 2])
                if curve:
                    ld = gld_load[busnum]['pcrv'] + (gld_load[busnum]['p'] * gld_scale)
                else:
                    ld = gld_load[busnum]['pcrv']
                bus[i, 2] = ld
                bus[i, 3] = ld * (float(fncsBus[i, 4]) / float(fncsBus[i, 3]))  # powerfactor
                row = []
                for z in range(TAU):
                   row.append(ld)
                fncs.publish('cleared_q_rt_' + str(i + 1), json.dumps(row))

        return dispatch, RT_LMPs

    def write_rtm_schedule(uc_df1, uc_df2):
        data = []
        mm = mn
        hh = hour
        uc = uc_df1
        for jj in range(TAU):
            rr = {}
            for ii in range(numGen):
                if "wind" not in genFuel[ii][0]:
                    name = "GenCo" + str(ii + 1)
                    rr[name] = uc.at[hh, name]
            data.append(rr)
            mm += RTOPDur
            if mm % 60 == 0:
                hh = hh + 1
                mm = 0
                if hh == 24:
                    hh = 0
                    uc = uc_df2
        df = pd.DataFrame(data)
        return df

    def write_default_schedule():
        data = []
        for jj in range(24):
            rr = {}
            for ii in range(numGen):
                if "wind" not in genFuel[ii][0]:
                    name = "GenCo" + str(ii + 1)
                    rr[name] = 1
            data.append(rr)
        df = pd.DataFrame(data)
        return df

    def write_psst_file(fname, dayahead):
        fp = open(fname, 'w')
        print('# Written by fncsTSO.py', file=fp)
        print('', file=fp)
        print('set StageSet := FirstStage SecondStage ;', file=fp)
        print('', file=fp)
        print('set CommitmentTimeInStage[FirstStage] := 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 ;',
            file=fp)
        print('set CommitmentTimeInStage[SecondStage] := ;', file=fp)
        print('', file=fp)
        print('set GenerationTimeInStage[FirstStage] := ;', file=fp)
        print('set GenerationTimeInStage[SecondStage] := 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 ;',
            file=fp)
        print('', file=fp)

        writeLine = 'set Buses :='
        for i in range(bus.shape[0]):
            writeLine = writeLine + ' Bus' + str(i + 1)
        writeLine = writeLine + ' ;'
        print(writeLine, file=fp)
        print('', file=fp)

        print('set TransmissionLines :=', file=fp)
        for i in range(branch.shape[0]):
            if branch[i, 1] > branch[i, 0]:
                fbus = int(branch[i, 0])
                tbus = int(branch[i, 1])
            else:
                fbus = int(branch[i, 1])
                tbus = int(branch[i, 0])
            writeLine = 'Bus' + str(fbus) + ' Bus' + str(tbus)
            print(writeLine, file=fp)
        print(';', file=fp)
        print('', file=fp)

        writeLine = 'param NumTransmissionLines := ' + str(branch.shape[0]) + ' ;'
        print(writeLine, file=fp)
        print('', file=fp)

        print('param: BusFrom BusTo ThermalLimit Reactance :=', file=fp)
        for i in range(branch.shape[0]):
            if branch[i, 1] > branch[i, 0]:
                fbus = int(branch[i, 0])
                tbus = int(branch[i, 1])
            else:
                fbus = int(branch[i, 1])
                tbus = int(branch[i, 0])
            #  // Convert  MaxCap  from SI to  PU
            limit = branch[i, 5] / baseS
            #  // Convert  reactance  from SI to  PU, x(pu) = x / Zo = x / (Vo ^ 2 / So) = (x * So) / Vo ^ 2
            reactance = (branch[i, 3] * baseS) / (baseV * baseV)
            writeLine = str(i + 1) + ' Bus' + str(fbus) + ' Bus' + str(tbus) + '{: .2f}'.format(limit) + '{: .2E}'.format(reactance)
            print(writeLine, file=fp)
        print(';', file=fp)
        print('', file=fp)

        writeLine = 'set ThermalGenerators :='
        for i in range(numGen):
            if "wind" not in genFuel[i][0]:
                writeLine = writeLine + ' GenCo' + str(i + 1)
        print(writeLine, ';', file=fp)
        print('', file=fp)
        for i in range(bus.shape[0]):
            writeLine = 'set ThermalGeneratorsAtBus[Bus' + str(i + 1) + '] :='
            for j in range(numGen):
                if int(gen[j, 0]) == i + 1 and "wind" not in genFuel[j][0]:
                    writeLine = writeLine + ' GenCo' + str(j + 1)
            print(writeLine, ';', file=fp)
        print('', file=fp)

        print('param BalPenPos := ' + str(priceCap) + " ;", file=fp)
        print('', file=fp)
        print('param BalPenNeg := ' + str(priceCap) + " ;", file=fp)
        print('', file=fp)

        if (dayahead):
            print('param TimePeriodLength := 1 ;', file=fp)
            print('', file=fp)
            print('param NumTimePeriods := ' + str(hours_in_a_day) + ' ;', file=fp)
            print('', file=fp)
        else:
            print('param TimePeriodLength := ' + str(period/secs_in_a_hr) + ' ;', file=fp)
            print('', file=fp)
            print('param NumTimePeriods := ' + str(TAU) + ' ;', file=fp)
            print('', file=fp)

        print(
            'param: PowerGeneratedT0 UnitOnT0State MinimumPowerOutput MaximumPowerOutput MinimumUpTime MinimumDownTime NominalRampUpLimit NominalRampDownLimit StartupRampLimit ShutdownRampLimit ColdStartHours ColdStartCost HotStartCost ShutdownCostCoefficient :=',
            file=fp)
        for i in range(numGen):
            if "wind" not in genFuel[i][0]:
                name = 'GenCo' + str(i + 1)
                Pmax = gen[i, 8] / baseS
                Pmin = gen[i, 9] / baseS

                #todo fill out gen parameters
                minDn = 0
                minUp = 0

                # powerT0
                if dayahead:
                    if len(da_dispatch) == 0:
                        powerT0 = Pmax * 0.5
                    else:
                        try:
                            powerT0 = da_dispatch[name][0] / baseS     # dispatch from before (yesterday)
                        except:
                            powerT0 = Pmax * 0.5                       # when no dispatch from before (yesterday)
                else:
                    if len(rt_dispatch) == 0:
                        powerT0 = Pmax * 0.5
                    else:
                        try:
                            powerT0 = rt_dispatch[name][0] / baseS     # from this time forward
                        except:
                            powerT0 = Pmax * 0.5  # when no dispatch from before (yesterday)
                # unitOnT0State
                unitOnT0 = gen_ames[str(i)][0]  # counter in hours set in day ahead
                #put ramp up and down to turn on generators
                if Pmin < Pmax:
                    writeLine = name + '{: .6f}'.format(powerT0) + ' ' + str(unitOnT0) + '{: .6f}'.format(Pmin) + \
                        '{: .6f}'.format(Pmax) + ' ' + str(minUp) + ' ' + str(minDn) + ' 0.000000 0.000000' + \
                        '{: .6f}'.format(Pmax) + '{: .6f}'.format(Pmax) + ' 0 0.000000 0.000000 0.000000'
                else:
                    # TODO: wtf should never happen but does
                    writeLine = name + '{: .6f}'.format(powerT0) + ' ' + str(unitOnT0) + '{: .6f}'.format(0.0) + \
                        '{: .6f}'.format(Pmax) + ' ' + str(minUp) + ' ' + str(minDn) + ' 0.000000 0.000000' + \
                        '{: .6f}'.format(Pmax) + '{: .6f}'.format(Pmax) + ' 0 0.000000 0.000000 0.000000'
                    print("Some thing is wrong with " + name + ' in ' + fname)
                print(writeLine, file=fp)
        print(' ;', file=fp)
        print('', file=fp)

        print(
            'param: ID atBus EndPointSoc MaximumEnergy NominalRampDownInput NominalRampUpInput NominalRampDownOutput NominalRampUpOutput MaximumPowerInput MinimumPowerInput MaximumPowerOutput MinimumPowerOutput MinimumSoc EfficiencyEnergy :=',
            file=fp)
        print(' ;', file=fp)
        print('', file=fp)

        print('param StorageFlag := 0.0 ;', file=fp)
        print('', file=fp)
        if da_bid:
            print('param PriceSenLoadFlag :=', str(priceSensLoad), ';', file=fp)
        else:
            print('param PriceSenLoadFlag := 0;', file=fp)
        print('', file=fp)
        print('param ReserveDownSystemPercent :=', str(reserveDown), ';', file=fp)
        print('', file=fp)
        print('param ReserveUpSystemPercent :=', str(reserveUp), ';', file=fp)
        print('', file=fp)
        print('param HasZonalReserves :=', str(zonalReserves), ';', file=fp)
        print('', file=fp)

        if zonalReserves:
            print('param NumberOfZones :=', str(len(zones)), ';', file=fp)
            print('', file=fp)

            writeLine = 'set Zones :='
            for j in range(len(zones)):
                writeLine = writeLine + ' Zone' + str(j + 1)
            print(writeLine, ';', file=fp)
            print('', file=fp)

            print('param: Buses ReserveDownZonalPercent ReserveUpZonalPercent :=', file=fp)
            for j in range(len(zones)):
                buses = ''
                for i in range(bus.shape[0]):
                    if zones[j][0] == bus[i, 10]:
                        if buses == '':
                            buses = 'Bus' + str(i + 1) + ','
                        else:
                            buses = buses + 'Bus' + str(i + 1) + ','
                writeLine = 'Zone' + str(j + 1) + ' ' + buses + '{: .1f}'.format(zones[j][2]) + '{: .1f}'.format(zones[j][3])
                print(writeLine, file=fp)
            print(';', file=fp)
            print('', file=fp)

        if da_bid:
            print('param: NetDemand :=', file=fp)
            for i in range(bus.shape[0]):
                busnum = i + 1
                gld_scale = float(fncsBus[i][2])
                if dayahead:                                      # 12am to 12am
                    for j in range(hours_in_a_day):
                        ndg = 0
                        for key, row in wind_plants.items():
                            if row[0] == busnum:
                                ndg += float(row[9][j+24])
                        net = ((respMaxMW[i][j] + unRespMW[i][j]) * gld_scale) - ndg
                        writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.5f}'.format(net / baseS)
                        print(writeLine, file=fp)
                else:                                             # real time
                    ndg = 0
                    for key, row in wind_plants.items():
                        if row[0] == busnum:
                            ndg += gen[row[10], 1]
                    net = ((gld_load[busnum]['resp_max'] + gld_load[busnum]['unresp']) * gld_scale) - ndg
                    for j in range(TAU):
                        writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.5f}'.format(net / baseS)
                        print(writeLine, file=fp)
                print('', file=fp)
            print(';', file=fp)
            print('', file=fp)

            if priceSensLoad:
                writeLine = 'set PricesSensitiveLoadNames :='
                for i in range(bus.shape[0] - 1):
                    writeLine = writeLine + ' LSE' + str(i + 1) + ','
                writeLine = writeLine + ' LSE' + str(i + 2)
                print(writeLine, ';', file=fp)
                print('', file=fp)

                print('param: Name ID atBus hourIndex BenefitCoefficientC0 BenefitCoefficientC1 BenefitCoefficientC2 SLMin SLMax :=', file=fp)
                for i in range(bus.shape[0]):
                    busnum = i + 1
                    gld_scale = float(fncsBus[i][2])
                    if (dayahead):                                # 12am to 12am
                        for j in range(hours_in_a_day):
                            if respMaxMW[i][j] > 1e-6:
                                writeLine = 'LSE' + str(busnum) + ' ' + str(busnum) + ' Bus' + str(busnum) + ' ' + str(j + 1) + \
                                            ' 0.0' + \
                                            ' {: .5f}'.format((respC1[i][j] * baseS) / gld_scale) + \
                                            ' {: .5f}'.format((respC2[i][j] * baseS * baseS) / (gld_scale * gld_scale)) + \
                                            ' 0.0' + ' {: .5f}'.format((respMaxMW[i][j] * gld_scale) / baseS)
                                print(writeLine, file=fp)
                        print('', file=fp)
                    else:                                         # real time
                        for j in range(TAU):
                            if gld_load[busnum]['resp_max'] > 1e-6:
                                writeLine = 'LSE' + str(busnum) + ' ' + str(busnum) + ' Bus' + str(busnum) + ' ' + str(j + 1) + \
                                            ' 0.0' + \
                                            ' {: .5f}'.format((gld_load[busnum]['c1'] * baseS) / gld_scale) + \
                                            ' {: .5f}'.format((gld_load[busnum]['c2'] * baseS * baseS) / (gld_scale * gld_scale)) + \
                                            ' 0.0' + ' {: .5f}'.format((gld_load[busnum]['resp_max'] * gld_scale) / baseS)
                                print(writeLine, file=fp)
                        print('', file=fp)
                print(';', file=fp)
                print('', file=fp)
        else:
            print('param: NetDemand :=', file=fp)
            for i in range(bus.shape[0]):
                busnum = i + 1
                gld_scale = float(fncsBus[i][2])
                if dayahead:
                    for j in range(hours_in_a_day):
                        ndg = 0
                        for key, row in wind_plants.items():
                            if row[0] == busnum:
                                ndg += float(row[9][j+24])
                        if curve:
                            net = (gld_load[busnum]['pcrv'] + (gld_load[busnum]['p'] * gld_scale)) - ndg
                        else:
                            net = gld_load[busnum]['pcrv'] - ndg
                        writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.4f}'.format(net / baseS)
                        print(writeLine, file=fp)
                else:
                    ndg = 0
                    for key, row in wind_plants.items():
                        if row[0] == busnum:
                            ndg += gen[row[10], 1]
                    if curve:
                        net = (gld_load[busnum]['pcrv'] + (gld_load[busnum]['p'] * gld_scale)) - ndg
                    else:
                        net = gld_load[busnum]['pcrv'] - ndg
                    for j in range(TAU):
                        writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.4f}'.format(net / baseS)
                        print(writeLine, file=fp)
                print('', file=fp)
            print(';', file=fp)
            print('', file=fp)

        print('param: ProductionCostA0 ProductionCostA1 ProductionCostA2 NS :=', file=fp)
        for i in range(numGen):
            if "wind" not in genFuel[i][0]:
                c0 = genCost[i, 6]
                c1 = genCost[i, 5]
                c2 = genCost[i, 4]
                ns = '1'
                if c0 > 0 and c1 > 0 and c2 > 0:
                    ns = str(NS)
                writeLine = 'GenCo' + str(i + 1) + '{: .5f}'.format(c0) + \
                            '{: .5f}'.format(c1) + '{: .5f}'.format(c2) + ' ' + ns
                print(writeLine, file=fp)
        print(';', file=fp)
        fp.close()

    def write_ames_base_case(fname):
        fp = open(fname, 'w')
        print('// Base SI', file=fp)
        print('BASE_S ', str(baseS), file=fp)
        print('// Base Voltage', file=fp)
        print('BASE_V ', str(baseV), file=fp)
        print('', file=fp)

        print('// Simulation Parameters', file=fp)
        print('MaxDay ' + str(MaxDay), file=fp)
        print('RTOPDur ' + str(RTOPDur), file=fp)
        print('RandomSeed 695672061', file=fp)
        print('// ThresholdProbability 0.999', file=fp)
        print('PriceSensitiveDemandFlag ' + str(priceSensLoad), file=fp)
        print('ReserveDownSystemPercent ' + str(reserveDown), file=fp)
        print('ReserveUpSystemPercent ' + str(reserveUp), file=fp)
        print('BalPenPos 1000', file=fp)
        print('BalPenNeg 1000', file=fp)
        print('NDGFlag 1', file=fp)

        print('// Bus Data', file=fp)
        print('NumberOfBuses', bus.shape[0], file=fp)
        print('NumberOfReserveZones', len(zones), file=fp)
        print('', file=fp)

        print('#ZoneDataStart', file=fp)
        print('// ZoneName   Buses   ReserveDownZonalPercent   ReserveUpZonalPercent', file=fp)
        for j in range(len(zones)):
            name = 'Zone' + str(j + 1)
            buses = ''
            for i in range(bus.shape[0]):
                if zones[j][0] == bus[i, 10]:
                    if buses == '':
                        buses = str(i + 1)
                    else:
                        buses = buses + ',' + str(i + 1)
            print(name, buses, '{: .1f}'.format(zones[j][2]), '{: .1f}'.format(zones[j][3]), file=fp)
        print('#ZoneDataEnd', file=fp)
        print('', file=fp)

        print('#LineDataStart', file=fp)
        print('// Name   From   To   MaxCap(MWs)   Reactance(ohms)', file=fp)
        # branch: fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
        # AMES wants branch name, from bus(< to bus), to bus, capacity(MVA), total X(pu)
        for i in range(branch.shape[0]):
            name = 'Line' + str(i + 1)
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
        print('// Name   ID   atBus   SCost($H)   a($/MWh)   b($MW^2h)   CapL(MW)   CapU(MW)   Segments   InitMoney',
              file=fp)
        # TODO: replace ppc['gencost'] with dictionary of hourly bids, collected from the GridLAB-D agents over FNCS
        # gen: bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin,(11 zeros)
        # gencost: 2, startup, shutdown, 3, c2, c1, c0
        # AMES wants name, ID, bus, c0, c1, c2, capL, capU, NS, InitMoney
        for i in range(numGen):
            if "wind" not in genFuel[i][0]:
                name = 'GenCo' + str(i + 1)
                fbus = int(gen[i, 0])
                Pmax = gen[i, 8]
                Pmin = gen[i, 9]
                c0 = genCost[i, 6]
                c1 = genCost[i, 5]
                c2 = genCost[i, 4]
                if Pmin > 0:
                    print(name, str(i + 1), fbus, '{: .2f}'.format(c0), '{: .2f}'.format(c1),
                          '{: .6f}'.format(c2), '{: .2f}'.format(Pmin), '{: .2f}'.format(Pmax),
                          NS, '{: .2f}'.format(100000.0), file=fp)
        print('#GenDataEnd', file=fp)
        print('', file=fp)

        print('#LSEDataFixedDemandStart', file=fp)
        # ppc arrays(bus type 1=load, 2 = gen(PV) and 3 = swing)
        # bus: bus_i, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin
        # AMES wants name, ID, bus, 8x hourly demands, in three blocks
        # Define a dictionary of hourly load forecasts, collected from ppc
        #    GridLAB-D via FNCS, to replace ppc['bus']
        lse = []
        for i in range(bus.shape[0]):
            Pd = unRespMW[i] + respMaxMW[i]
            fbus = int(bus[i, 0])
            lse.append([fbus, Pd])
        print('// Name ID atBus H-00 H-01 H-02 H-03 H-04 H-05 H-06 H-07', file=fp)
        for i in range(len(lse)):
            Pd = lse[i][1]
            print('LSE' + str(i + 1), str(i + 1), lse[i][0], '{: .2f}'.format(Pd[0]), '{: .2f}'.format(Pd[1]),
                  '{: .2f}'.format(Pd[2]), '{: .2f}'.format(Pd[3]), '{: .2f}'.format(Pd[4]),
                  '{: .2f}'.format(Pd[5]), '{: .2f}'.format(Pd[6]), '{: .2f}'.format(Pd[7]), file=fp)
        print('// Name ID atBus H-08 H-09 H-10 H-11 H-12 H-13 H-14 H-15', file=fp)
        for i in range(len(lse)):
            Pd = lse[i][1]
            print('LSE' + str(i + 1), str(i + 1), lse[i][0], '{: .2f}'.format(Pd[8]), '{: .2f}'.format(Pd[9]),
                  '{: .2f}'.format(Pd[10]), '{: .2f}'.format(Pd[11]), '{: .2f}'.format(Pd[12]),
                  '{: .2f}'.format(Pd[13]), '{: .2f}'.format(Pd[14]), '{: .2f}'.format(Pd[15]), file=fp)
        print('// Name ID atBus H-16 H-17 H-18 H-19 H-20 H-21 H-22 H-23', file=fp)
        for i in range(len(lse)):
            Pd = lse[i][1]
            print('LSE' + str(i + 1), str(i + 1), lse[i][0], '{: .2f}'.format(Pd[16]), '{: .2f}'.format(Pd[17]),
                  '{: .2f}'.format(Pd[18]), '{: .2f}'.format(Pd[19]), '{: .2f}'.format(Pd[20]),
                  '{: .2f}'.format(Pd[21]), '{: .2f}'.format(Pd[22]), '{: .2f}'.format(Pd[23]), file=fp)
        print('#LSEDataFixedDemandEnd', file=fp)
        print('', file=fp)

        # Wind Plants, AMES wants name, ID, bus, 8x hourly demands, in three blocks
        print('#NDGDataStart', file=fp)
        i = 1
        print('// Name ID atBus H-00 H-01 H-02 H-03 H-04 H-05 H-06 H-07', file=fp)
        for key, row in wind_plants.items():
            Pd = row[9]
            print('NDG' + str(i), str(i), row[0], '{: .2f}'.format(Pd[0]), '{: .2f}'.format(Pd[1]),
                  '{: .2f}'.format(Pd[2]), '{: .2f}'.format(Pd[3]), '{: .2f}'.format(Pd[4]),
                  '{: .2f}'.format(Pd[5]), '{: .2f}'.format(Pd[6]), '{: .2f}'.format(Pd[7]), file=fp)
            i += 1
        i = 1
        print('// Name ID atBus H-08 H-09 H-10 H-11 H-12 H-13 H-14 H-15', file=fp)
        for key, row in wind_plants.items():
            Pd = row[9]
            print('NDG' + str(i), str(i), row[0], '{: .2f}'.format(Pd[8]), '{: .2f}'.format(Pd[9]),
                  '{: .2f}'.format(Pd[10]), '{: .2f}'.format(Pd[11]), '{: .2f}'.format(Pd[12]),
                  '{: .2f}'.format(Pd[13]), '{: .2f}'.format(Pd[14]), '{: .2f}'.format(Pd[15]), file=fp)
            i += 1
        i = 1
        print('// Name ID atBus H-16 H-17 H-18 H-19 H-20 H-21 H-22 H-23', file=fp)
        for key, row in wind_plants.items():
            Pd = row[9]
            print('NDG' + str(i), str(i), row[0], '{: .2f}'.format(Pd[16]), '{: .2f}'.format(Pd[17]),
                  '{: .2f}'.format(Pd[18]), '{: .2f}'.format(Pd[19]), '{: .2f}'.format(Pd[20]),
                  '{: .2f}'.format(Pd[21]), '{: .2f}'.format(Pd[22]), '{: .2f}'.format(Pd[23]), file=fp)
            i += 1
        print('#NDGDataEnd', file=fp)
        print('', file=fp)

        print('#LSEDataPriceSensitiveDemandStart', file=fp)
        print('// Name   ID    atBus   hourIndex   d   e   f   pMin   pMax', file=fp);
        lse = []
        for i in range(bus.shape[0]):
            Pd = unRespMW[i]
            fbus = int(bus[i, 0])
            lse.append([fbus, Pd])

        for i in range(len(lse)):
            Pd = lse[i][1]
            for k in range(hours_in_a_day):
                print('LSE' + str(i + 1), str(i + 1), lse[i][0], str(k + 1),
                      '{: .2f}'.format(0), '{: .2f}'.format(0.1),
                      '{: .2f}'.format(0), '{: .2f}'.format(Pd[k]), file=fp)
        print('#LSEDataPriceSensitiveDemandEnd', file=fp)
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

    if ppc['solver'] == 'cbc':
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

    ames = ppc['ames']
    solver = ppc['solver']
    priceCap = 2 * ppc['priceCap']
    reserveDown = ppc['reserveDown']
    reserveUp = ppc['reserveUp']
    zonalReserves = ppc['zonalReserves']
    baseS = int(ppc['baseMVA'])     # base_S in ercot_8.json baseMVA
    baseV = int(bus[0, 9])          # base_V in ercot_8.json bus row 0-7, column 9, should be the same for all buses

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
    tnext_ames = 0
    wind_hour = -1
    mn = 0
    hour = -1
    day = 1
    lastDay = 1
    file_time = ''
    MaxDay = tmax // 86400  # days in simulation
    RTOPDur = period // 60  # in minutes
    RTDeltaT = 1            # in minutes
    TAU = RTOPDur // RTDeltaT
    NS = 4  # number of segments
    da_bid = False
    gen_ames = {}
    da_schedule = {}
    da_lmps = {}
    da_dispatch = {}
    rt_lmps = {}
    rt_dispatch = {}
    # listening to GridLAB-D and its auction objects
    gld_load = {}  # key on bus number

    # we need to adjust Pmin downward so the OPF and PF can converge, or else implement unit commitment
    if not ames:
        for row in gen:
            row[9] = 0.1 * row[8]

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
        gen_ames[str(i)] = [1]

    total_bus_num = fncsBus.shape[0]
    unRespMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
    respMaxMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
    respC2 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
    respC1 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
    respC0 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
    resp_deg = np.zeros([total_bus_num, hours_in_a_day], dtype=float)

    #if ames:
    #    write_ames_base_case('ames.dat')
    # quit()
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
            w += 1;    line += ", wind" + str(w)
        elif "nuclear" in genFuel[i][0]:
            n += 1;    line += ", nuc" + str(n)
        elif "coal" in genFuel[i][0]:
            c += 1;    line += ", coal" + str(c)
        else:
            g += 1;    line += ", gas" + str(g)
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
            #      print ('UNRESPONSIVE_MW_', busnum, 'at', ts, '=', val, flush=True)
            elif 'RESPONSIVE_MAX_MW_' in topic:
                busnum = int(topic[18:])
                gld_load[busnum]['resp_max'] = float(val)
            #      print ('RESPONSIVE_MAX_MW_', busnum, 'at', ts, '=', val, flush=True)
            elif 'RESPONSIVE_C2_' in topic:
                busnum = int(topic[14:])
                gld_load[busnum]['c2'] = float(val)
            #      print ('RESPONSIVE_C2_', busnum, 'at', ts, '=', val, flush=True)
            elif 'RESPONSIVE_C1_' in topic:
                busnum = int(topic[14:])
                gld_load[busnum]['c1'] = float(val)
            #      print ('RESPONSIVE_C1_', busnum, 'at', ts, '=', val, flush=True)
            elif 'RESPONSIVE_C0_' in topic:
                busnum = int(topic[14:])
                gld_load[busnum]['c0'] = float(val)
            #      print ('RESPONSIVE_C1_', busnum, 'at', ts, '=', val, flush=True)
            elif 'RESPONSIVE_DEG_' in topic:
                busnum = int(topic[15:])
                gld_load[busnum]['deg'] = int(val)
            #      print ('RESPONSIVE_DEG_', busnum, 'at', ts, '=', val, flush=True)
            #    elif 'wind_power' in topic:
            #      busnum = int(topic[15:])
            #      gld_load[busnum]['windpower'] = int(val)
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
                unRespMW[busnum] = day_ahead_bid['unresp_mw']     # fix load
                respMaxMW[busnum] = day_ahead_bid['resp_max_mw']  # slmax
                respC2[busnum] = day_ahead_bid['resp_c2']
                respC1[busnum] = day_ahead_bid['resp_c1']
                respC0[busnum] = 0.0  # day_ahead_bid['resp_c0']
                resp_deg[busnum] = day_ahead_bid['resp_deg']
                # print('Day Ahead Bid for Bus', busnum, 'at', ts, '=', day_ahead_bid, flush=True)

        #  print(ts, 'FNCS inputs', gld_load, flush=True)
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

        # run SCED/SCUC in AMES/PSST to establish the next day's unit commitment and dispatch
        if ts >= tnext_ames and ames:
            # print('bus_b4_opf = ', bus[:, 2].sum())
            # print('gen_b4_opf = ', gen[:, 1].sum())
            if mn % 60 == 0:
                hour = hour + 1
                mn = 0
                if hour == 24:
                    hour = 0
                    day = day + 1

            # un-comment file_time for multiple AMES files
            # file_time = str(day) + '_' + str(hour) + '_' + str(mn) + '_'
            print_time = str(day) + '_' + str(hour) + '_' + str(mn) + '_'

            # update cost coefficients, set dispatchable load, put unresp+curve load on bus
            update_cost_and_load()

            # Run the day ahead
            if hour == 12 and mn == 0:

                ames_DAM_case_file = "./" + file_time + "dam.dat"
                write_psst_file(ames_DAM_case_file, True)
                da_schedule, da_dispatch, da_lmps = scucDAM(ames_DAM_case_file, file_time + "GenCoSchedule.dat", solver)
                print ('$$$$ DAM finished [day_hour_min_', print_time, flush=True)
                print_matrix ('DAM LMPs', da_lmps)
                print_keyed_matrix ('DAM Dispatches', da_dispatch, fmt='{:8.2f}')
                print_keyed_matrix ('DAM Schedule', da_schedule, fmt='{:8s}')

            # Real time and update the dispatch schedules in ppc
            if day > 1:
                # Change the DA Schedule and the dispatchable generators
                if day > lastDay:
                    schedule = deepcopy(da_schedule)
                    lastDay = day

                if mn == 0:
                    # uptime and downtime in hour for each generator
                    # and are counted using commitment schedule for the day
                    for i in range(numGen):
                        if "wind" not in genFuel[i][0]:
                            name = "GenCo" + str(i + 1)
                            gen[i, 7] = int(schedule.at[hour, name])
                            if gen[i, 7] == 1:
                                if gen_ames[str(i)][0] > 0:
                                    gen_ames[str(i)][0] += 1
                                else:
                                    gen_ames[str(i)][0] = 1
                            else:
                                if gen_ames[str(i)][0] < 0:
                                    gen_ames[str(i)][0] -= 1
                                else:
                                    gen_ames[str(i)][0] = -1

                # Run the real time and publish the LMP
                ames_RTM_case_file = "./" + file_time + "rtm.dat"
                write_psst_file(ames_RTM_case_file, False)
                rtm_schedule = write_rtm_schedule(schedule, da_schedule)
                rt_dispatch, rt_lmps = scedRTM(ames_RTM_case_file, rtm_schedule, file_time + "RTMResults.dat", solver)
                print ('#### RTM finished [day_hour_min_', print_time, flush=True)
                print_matrix ('RTM LMPs', rt_lmps)
                print_keyed_matrix ('RTM Dispatches', rt_dispatch, fmt='{:8.2f}')
                try:
                    for i in range(bus.shape[0]):
                        bus[i, 13] = rt_lmps[i][0]
                    for i in range(numGen):
                        name = "GenCo" + str(i + 1)
                        if "wind" not in genFuel[i][0]:
                            gen[i, 1] = rt_dispatch[name][0]
                except:
                    print('  #### Exception: unable to obtain and dispatch from LMPs')
                    pass

            # write OPF metrics
            Pswing = 0
            for i in range(numGen):
                if gen[i, 0] == swing_bus:
                    Pswing += gen[i, 1]

            sum_w = 0
            for key, row in wind_plants.items():
                sum_w += gen[row[10], 1]

            line = str(ts) + ', ' + "True" + ','
            line += '{: .2f}'.format(bus[:, 2].sum()) + ','
            line += '{: .2f}'.format(gen[:, 1].sum()) + ','
            line += '{: .2f}'.format(Pswing) + ','
            for i in range(bus.shape[0]):
                line += '{: .2f}'.format(bus[i, 13]) + ','
            for i in range(numGen):
                if numGen > i:
                    line += '{: .2f}'.format(gen[i, 1]) + ','
            line += '{: .2f}'.format(sum_w)
            print(line, sep=', ', file=op, flush=True)

            mn = mn + RTOPDur  # period // 60
            tnext_ames += period
            # print  ('bus_after_opf = ', bus[:, 2].sum())
            # print  ('gen_after_opf = ', gen[:, 1].sum())

        # run OPF to establish the prices and economic dispatch - currently period = 300s
        if ts >= tnext_opf and not ames:
            # print  ('bus_b4_opf = ', bus[:, 2].sum())
            # print  ('gen_b4_opf = ', gen[:, 1].sum())

            # update cost coefficients, set dispatchable load, put unresp+curve load on bus
            update_cost_and_load()

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
            ppc['gen'][:, 1] = opf_gen[:, 1]  # set the economic dispatch
            bus = ppc['bus']  # needed to be re-aliased because of [:, ] operator
            gen = ppc['gen']  # needed to be re-aliased because of [:, ] operator
            # print  ('bus_after_opf = ', bus[:, 2].sum())
            # print  ('gen_after_opf = ', gen[:, 1].sum())


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

        #  print_gld_load(ppc, gld_load, 'RPF', ts)
        # print('bus_b4_dist_slack = ', bus[:, 2].sum())
        # print('gen_b4_dist_slack = ', gen[:, 1].sum())

        # update generation with consideration for distributed slack bus
        # ppc['gen'][:, 1] = dist_slack(ppc, Pload)

        # add the actual scaled GridLAB-D loads to the baseline curve loads, turn off dispatchable loads
        # print('bus_b4_pf = ', ppc['bus'][:, 2].sum())
        # print('gen_b4_pf = ', ppc['gen'][:, 1].sum())

        rpf = pp.runpf(ppc, ppopt_regular)
        # TODO: add a check if does not converge, switch to DC
        if not rpf[0]['success']:
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
        # print('bus_after_pf = ', rBus[:, 2].sum())
        # print('gen_after_pf = ', rGen[:, 1].sum())

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
            if ames:
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
            if ames:
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
