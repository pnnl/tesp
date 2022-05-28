# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: tso_helpers.py
""" Helpers for PYPOWER, PSST, MOST solutions

Public Functions:
    print_matrix
    print_keyed_matrix
    load_json_case
    print_mod_load
    summarize_opf
    make_dictionary
    dist_slack
"""

import os
# import sys
import json
import numpy as np
from copy import deepcopy

#import cProfile
#import pstats

# if sys.platform != 'win32':
#     import resource


def print_matrix(lbl, A, fmt='{:8.4f}'):
    if A is None:
        print(lbl, 'is Empty!', flush=True)
    elif hasattr(A, '__iter__'):
        nrows = len(A)
        if (nrows > 1) and hasattr(A[0], '__iter__'):  # 2D array
            ncols = len(A[0])
            print('{:s} is {:d}x{:d}'.format(lbl, nrows, ncols))
            print('\n'.join([' '.join([fmt.format(item) for item in row]) for row in A]), flush=True)
        else:                          # 1D array, printed flat
            print('{:s} has {:d} elements'.format(lbl, nrows))
            print(' '.join(fmt.format(item) for item in A), flush=True)
    else:                              # single value
        print(lbl, '=', fmt.format(A), flush=True)


def print_keyed_matrix(lbl, D, fmt='{:8.4f}'):
    if D is None:
        print(lbl, 'is Empty!', flush=True)
        return
    nrows = len(D)
    ncols = 0
    for key, row in D.items():
        if ncols == 0:
            ncols = len(row)
            print('{:s} is {:d}x{:d}'.format(lbl, nrows, ncols))
        print('{:8s}'.format(key), ' '.join(fmt.format(item) for item in row), flush=True)


def load_json_case(fname):
    """ Helper function to load PYPOWER case from a JSON file

    Args:
      fname (str): the JSON file to open

    Returns:
      dict: the loaded PYPOWER case structure
    """
    lp = open(fname, encoding='utf-8').read()
    ppc = json.loads(lp)
    ppc['bus'] = np.array(ppc['bus'])
    ppc['gen'] = np.array(ppc['gen'])
    ppc['branch'] = np.array(ppc['branch'])
    ppc['areas'] = np.array(ppc['areas'])
    ppc['gencost'] = np.array(ppc['gencost'])
    ppc['DSO'] = np.array(ppc['DSO'])
    ppc['UnitsOut'] = np.array(ppc['UnitsOut'])
    ppc['BranchesOut'] = np.array(ppc['BranchesOut'])
    return ppc


def print_mod_load(bus, dso, model_load, msg, ts):
    print(msg, 'at', ts)
    print('bus, genidx, pbus, qbus, pcrv, qcrv, pgld, qgld, unresp, resp_max, c2, c1, c0, deg')
    for row in dso:
        bus_num = int(row[0])
        gld_scale = float(row[2])
        load = model_load[bus_num]
        genidx = -load['genidx']
        print('{:4d}'.format(bus_num),
              '{:4d}'.format(genidx),
              '{:8.2f}'.format(bus[bus_num - 1, 2]),
              '{:8.2f}'.format(bus[bus_num - 1, 3]),
              '{:8.2f}'.format(load['pcrv']),
              '{:8.2f}'.format(load['qcrv']),
              '{:8.2f}'.format(load['p'] * gld_scale),
              '{:8.2f}'.format(load['q'] * gld_scale),
              '{:8.2f}'.format(load['unresp'] * gld_scale),
              '{:8.2f}'.format(load['resp_max'] * gld_scale),
              '{:8.5f}'.format(load['c2'] / gld_scale),
              '{:8.5f}'.format(load['c1']),
              '{:8.5f}'.format(load['c0']),
              '{:3.1f}'.format(load['deg']))


def summarize_opf(mpc):
    """ Helper function to print optimal power flow solution (debugging)

    Args:
      mpc (dict): solved using PYPOWER case structure
    """
    bus = mpc['bus']
    gen = mpc['gen']

    Pload = bus[:, 2].sum()
    Pgen = gen[:, 1].sum()
    PctLoss = 100.0 * (Pgen - Pload) / Pgen

    print('success =', mpc['success'], 'in', '{:.3f}'.format(mpc['et']), 'seconds')
    print('Total Gen = {:.2f}'.format(Pgen), ' Load = {:.2f}'.format(Pload), ' Loss = {:.3f}'.format(PctLoss), '%')

    print('bus #       Pd       Qd       Vm     Vang    LMP_P    LMP_Q  MU_VMAX  MU_VMIN')
    for row in bus:
        print('{:4d}  {:8.2f} {:8.2f} {:8.4f} {:8.4f} {:8.5f} {:8.5f} {:8.5f} {:8.5f}'.
              format(int(row[0]), float(row[2]), float(row[3]), float(row[7]), float(row[8]),
                     float(row[13]), float(row[14]), float(row[15]), float(row[16])))

    print('gen # bus       Pg       Qg   MU_PMAX   MU_PMIN   MU_QMAX   MU_QMIN')
    idx = 1
    for row in gen:
        print('{:4d} {:4d} {:8.2f} {:8.2f} {:9.5f} {:9.5f} {:9.5f} {:9.5f}'.
              format(idx, int(row[0]), float(row[1]), float(row[2]), float(row[21]),
                     float(row[22]), float(row[23]), float(row[24])))
        ++idx


def make_dictionary(mpc):
    """ Helper function to write the JSON metafile for post-processing
        additions to DSO, and Pnom==>Pmin for generators

    Args:
      mpc (dict): PYPOWER case file structure
    """
    dsoBuses = {}
    generators = {}
    unitsout = []
    branchesout = []
    bus = mpc['bus']
    gen = mpc['gen']
    genCost = mpc['gencost']

    genFuel = None
    if 'genfuel' not in mpc:
        genFuel = "unknown"

    dso_buses = mpc['DSO']
    units = mpc['UnitsOut']
    branches = mpc['BranchesOut']

    output_Path = ''
    if 'output_Path' in mpc:
        output_Path = mpc['outputPath']

    for i in range(gen.shape[0]):
        if genFuel is None:
            genFuel = mpc['genfuel'][i][0]
        bus_num = int(gen[i, 0])
        bustype = bus[bus_num - 1, 1]
        if bustype == 1:
            bustypename = 'pq'
        elif bustype == 2:
            bustypename = 'pv'
        elif bustype == 3:
            bustypename = 'swing'
        else:
            bustypename = 'unknown'
        gentype = 'other'  # as opposed to simple cycle or combined cycle
        generators[str(i + 1)] = {'bus': int(bus_num), 'bustype': bustypename,
                                  'Pmin': float(gen[i, 9]), 'Pmax': float(gen[i, 8]),
                                  'genfuel': genFuel, 'gentype': gentype,
                                  'StartupCost': float(genCost[i, 1]), 'ShutdownCost': float(genCost[i, 2]),
                                  'c2': float(genCost[i, 4]), 'c1': float(genCost[i, 5]), 'c0': float(genCost[i, 6])}

    for i in range(dso_buses.shape[0]):
        bus_num = str(dso_buses[i, 0])
        busidx = int(bus_num) - 1
        dsoBuses[bus_num] = {'Pnom': float(bus[busidx, 2]), 'Qnom': float(bus[busidx, 3]),
                             'area': int(bus[busidx, 6]), 'zone': int(bus[busidx, 10]),
                             'ampFactor': float(dso_buses[i, 2]), 'GLDsubstations': [dso_buses[i, 1]]}
        if len(dso_buses[i]) > 5:
            dsoBuses[bus_num]['curveScale'] = float(dso_buses[i, 5])
            dsoBuses[bus_num]['curveSkew'] = int(dso_buses[i, 6])

    for i in range(units.shape[0]):
        unitsout.append({'unit': int(units[i, 0]), 'tout': int(units[i, 1]), 'tin': int(units[i, 2])})

    for i in range(branches.shape[0]):
        branchesout.append({'branch': int(branches[i, 0]), 'tout': int(branches[i, 1]), 'tin': int(branches[i, 2])})

    dp = open(os.path.join(output_Path, 'model_dict.json'), 'w')
    ppdict = {'baseMVA': mpc['baseMVA'], 'dsoBuses': dsoBuses, 'generators': generators,
              'UnitsOut': unitsout, 'BranchesOut': branchesout}
    print(json.dumps(ppdict), file=dp, flush=True)
    dp.close()


def dist_slack(mpc, prev_load):
    # this section will calculate the delta power from previous cycle using the prev_load
    # if previous load is equal to 0 we assume this is the first run and will
    # calculate delta power based on the difference between real power and real generation

    tot_load = sum(mpc['bus'][:, 2])

    if prev_load == 0:
        del_P = tot_load - sum(mpc['gen'][np.where(mpc['gen'][:, 7] == 1)[0], 1])
    else:
        del_P = tot_load - prev_load

    # if mpc.governor is not passed on then the governor assumes default parameters
    if 'governor' not in mpc:
        mpc['governor'] = {'coal': 0.00, 'gas': 0.05, 'nuclear': 0, 'hydro': 0.05}

    ramping_time = int(mpc["Period"]) / 60  # in minutes

    # .............Getting indexes of fuel type if not passed as an input argument......................................
    # checking fuel type to get index
    # checking generator status to make sure generator is active
    # checking generator regulation value to make sure generator participates in governor action
    # if fuel type matrix is not available we will assume all generators are gas turbines

    coal_idx = []
    hydro_idx = []
    nuclear_idx = []
    gas_idx = []
    governor_capacity = 0

    # Disabling (if mpc['gen'][i, 16] <= 0:) update of ramp rates and using the values already entered into the model
    if 'genfuel' in mpc:
        for i in range(len(mpc['genfuel'])):
            if (mpc['genfuel'][i][0] == "coal") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['coal'] != 0):
                coal_idx.append(i)
                if mpc['gen'][i, 16] <= 0:
                    mpc['gen'][i, 16] = 5 / 100 * mpc['gen'][i, 8]  # ramp_rate (%) * PG_max (MW) / 100  -> (MW)
                governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['coal'])
            elif (mpc['genfuel'][i][0] == "gas") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['gas'] != 0):
                gas_idx.append(i)
                if mpc['gen'][i, 16] <= 0:
                    if mpc['gen'][i, 8] < 200:
                        mpc['gen'][i, 16] = 2.79   # (MW)
                    elif mpc['gen'][i, 8] < 400:
                        mpc['gen'][i, 16] = 7.62   # (MW)
                    elif mpc['gen'][i, 8] < 600:
                        mpc['gen'][i, 16] = 4.8    # (MW)
                    elif mpc['gen'][i, 8] >= 600:
                        mpc['gen'][i, 16] = 26.66  # (MW)
                governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['gas'])
            elif (mpc['genfuel'][i][0] == "nuclear") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['nuclear'] != 0):
                nuclear_idx.append(i)
                if mpc['gen'][i, 16] <= 0:
                    mpc['gen'][i, 16] = 6.98  # (MW)
                governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['nuclear'])
            elif (mpc['genfuel'][i][0] == "hydro") & (mpc['gen'][i, 7] == 1) & (mpc['governor']['hydro'] != 0):
                hydro_idx.append(i)
                if mpc['gen'][i, 16] <= 0:
                    mpc['gen'][i, 16] = 5 / 100 * mpc['gen'][i, 8]  # ramp_rate (%) * PG_max (MW) / 100  -> (MW)
                governor_capacity = governor_capacity + mpc['gen'][i, 8] * (.05 / mpc['governor']['hydro'])
    else:
        gas_idx = np.where(mpc['gen'][:, 7] == 1)[0]
        governor_capacity = sum(mpc['gen'][gas_idx, 8] * (.05 / mpc['governor']['gas']))
        for i in range(len(mpc['gen'])):
            if mpc['gen'][i, 16] <= 0:
                if mpc['gen'][i, 8] < 200:
                    mpc['gen'][i, 16] = 2.79  # (MW)
                elif mpc['gen'][i, 8] < 400:
                    mpc['gen'][i, 16] = 7.62  # (MW)
                elif mpc['gen'][i, 8] < 600:
                    mpc['gen'][i, 16] = 4.8   # (MW)
                elif mpc['gen'][i, 8] >= 600:
                    mpc['gen'][i, 16] = 26.66  # (MW)
    ramping_capacity = mpc['gen'][:, 16] * ramping_time  # ramp rate (MW/min) * ramp time (min)  ->  (MW)

    # ........................Sorting the generators based on capacity..................................
    gov_R = np.array([])
    gov_idx = []
    if len(coal_idx) != 0:
        gov_idx.append(coal_idx)
        gov_R = np.append(gov_R, mpc['governor']['coal'] * np.ones(len(coal_idx)))
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
    try:
        capacity = mpc['gen'][gov_idx, 8][0]
    except:
        # log.info("Distribution governor idx length -> " + str(len(gov_idx)))
        # log.info("Distribution governor capacity failed, trying coal")
        for i in range(len(mpc['genfuel'])):
            if (mpc['genfuel'][i][0] == "coal") & (mpc['gen'][i, 7] == 1):
                coal_idx.append(i)
                if mpc['gen'][i, 16] <= 0:
                    mpc['gen'][i, 16] = 5 / 100 * mpc['gen'][i, 8]  # ramp_rate (%) * PG_max (MW) / 100  -> (MW)
                governor_capacity = governor_capacity + mpc['gen'][i, 8]
        gov_R = np.array([])
        gov_idx = []
        if len(coal_idx) != 0:
            gov_idx.append(coal_idx)
            gov_R = np.append(gov_R, 0.05 * np.ones(len(coal_idx)))
        gov_R = gov_R.tolist()
        capacity = mpc['gen'][gov_idx, 8][0]

    I = np.argsort(capacity)
    index = [gov_idx[0][i] for i in I]  # gov_idx[I]

    # ...........................................Governor Action........................................
    del_P_pu = del_P / governor_capacity
    del_f = .05 * del_P_pu
    del_P_new = del_P

    gen_update = deepcopy(mpc['gen'][:, 1])
    for i in range(len(index)):
        up_ramp_flag = 0
        max_flag = 0
        down_ramp_flag = 0
        min_flag = 0
        gen_update[index[i]] = mpc['gen'][index[i], 1] + mpc['gen'][index[i], 8] * del_f / gov_R[I[i]]  # P (MW) + del_P (MW)

        # .........................For Increasing Loads.............................
        # Checking Ramp Rates
        if mpc['gen'][index[i], 8] * del_f / gov_R[I[i]] > ramping_capacity[index[i]]:  # if del_P (MW) > del_P_max (MW)
            up_ramp_flag = 1
            gen_update[index[i]] = mpc['gen'][index[i], 1] + ramping_capacity[index[i]]  # P (MW) + del_P_max (MW)
            del_P_new = del_P_new - ramping_capacity[index[i]]
            governor_capacity = governor_capacity - mpc['gen'][index[i], 8] * .05 / gov_R[I[i]]  # total capacity (MW) - del_P_max MW) * del_P (pu) -> (MW)

        # Checking generation max Limits
        if gen_update[index[i]] > mpc['gen'][index[i], 8]:  # PG > PG_max (MW)
            max_flag = 1                                    # limit is reached
            # both the limits are reached
            if (up_ramp_flag == 1) & (max_flag == 1):
                gen_update[index[i]] = mpc['gen'][index[i], 8]
                del_P_new = del_P_new - (mpc['gen'][index[i], 8] - mpc['gen'][index[i], 1]) + ramping_capacity[index[i]]
                # Total_capacity already taken off in the ramp stage
                # only generation capacity limit is reached
            else:
                gen_update[index[i]] = mpc['gen'][index[i], 8]
                del_P_new = del_P_new - (mpc['gen'][index[i], 8] - mpc['gen'][index[i], 1])
                governor_capacity = governor_capacity - (mpc['gen'][index[i], 8] * (.05 / (gov_R[I[i]])))

        # ................................For Decreasing Loads.....................................
        # checking for negative ramping
        if mpc['gen'][index[i], 8] * del_f / gov_R[I[i]] < -1 * ramping_capacity[index[i]]:
            down_ramp_flag = 1
            gen_update[index[i]] = mpc['gen'][index[i], 1] - ramping_capacity[index[i]]
            del_P_new = del_P_new - (-1 * ramping_capacity[index[i]])
            governor_capacity = governor_capacity - mpc['gen'][index[i], 8] * .05 / gov_R[I[i]]

        # Checking generation min Limits
        if gen_update[index[i]] < mpc['gen'][index[i], 9]:
            min_flag = 1
            # both the limits are reached
            if (down_ramp_flag == 1) & (min_flag == 1):
                gen_update[index[i]] = mpc['gen'][index[i], 9]
                del_P_new = del_P_new - (mpc['gen'][index[i], 9] - mpc['gen'][index[i], 1]) + (-1 * ramping_capacity[index[i]])
            # Total_capacity already taken off in the ramp stage
            # only generation capacity limit is reached
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


