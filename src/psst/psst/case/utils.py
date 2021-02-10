import logging
import os

import pandas as pd
import numpy as np

from pypower.makePTDF import makePTDF
from pypower.runpf import runpf
from pypower.rundcpf import rundcpf

logger = logging.getLogger(__name__)


def calculate_segments(case, number_of_segments=10):
    return sort_segments(generate_segments(case, number_of_segments))


def generate_segments(case, number_of_segments):
    segments = []
    for g in case.gen_name:
        pmin, pmax = case.gen.loc[g, ['PMIN', 'PMAX']]
        N = int(case.gencost.loc[g, 'NCOST'])
        cost = case.gencost.loc[g, ['COST_{}'.format(i) for i in range(0, N )]]
        x = np.linspace(pmin, pmax, number_of_segments+1)
        for i, p in enumerate(x[:-1]):
            # p = ( x[i] + x[i+1] ) / 2.0
            p_seg = dict()
            p_seg['slope'] = incremental_cost(p, cost, N)
            p_seg['segment'] = (x[i], x[i+1])
            p_seg['name'] = g
            segments.append(p_seg)
    return segments

def sort_segments(segments):
    minimum = sorted(segments, key=lambda x: x['slope'])[0]['segment'][0]
    for i, d in enumerate(sorted(segments, key=lambda x: x['slope'])):
        d['segment'] = (minimum, d['segment'][1] - d['segment'][0] + minimum)
        minimum = d['segment'][1]

    return sorted(segments, key=lambda x: x['slope'])


def incremental_cost(p, cost, N):
    return sum(cost['COST_{}'.format(i)] * i * p ** (i-1) for i in range(1, N))


def calculate_PTDF(case, precision=None, tolerance=None):
    bus = case.bus.copy(deep=True)
    branch = case.branch.copy(deep=True)
    value = [i + 1 for i in range(0, len(bus.index))]
    bus_name = bus.index
    bus.index = value
    bus.index = bus.index.astype(int)
    branch['F_BUS'] = branch['F_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    branch['T_BUS'] = branch['T_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    bus = np.array(bus.reset_index())
    branch = np.array(branch)
    ptdf = makePTDF(case.baseMVA, bus, branch, )
    if precision is not None:
        ptdf = ptdf.round(precision)
    if tolerance is not None:
        ptdf[abs(ptdf) < tolerance] = 0
    return ptdf


def solve_dcopf(case, hour=None,
        results=None,
        ppopt={'VERBOSE': False},
        fname='./runpf.log'):

    fname = os.path.abspath(fname)

    baseMVA = case.baseMVA
    bus = case.bus.copy(deep=True)
    branch = case.branch.copy(deep=True)
    gen = case.gen.copy(deep=True)
    gencost = case.gen.copy(deep=True)

    if hour is not None:
        logger.debug("Setting bus load based on case.load")
        bus['PD'] = case.load.loc[hour]
        bus = bus.fillna(0)

    if hour is not None and results is not None:
        logger.debug("Setting GEN_STATUS and PG")
        gen['GEN_STATUS'] = results.unit_commitment.loc[hour].astype(int)
        gen['PG'] = results.power_generated.loc[hour]

    value = [i + 1 for i in range(0, len(bus.index))]
    bus_name = bus.index
    bus.index = value
    bus.index = bus.index.astype(int)
    branch['F_BUS'] = branch['F_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    branch['T_BUS'] = branch['T_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    gen['GEN_BUS'] = gen['GEN_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)

    bus = np.array(bus.reset_index())
    branch = np.array(branch)
    gen = np.array(gen)
    gencost = np.array(gencost)

    casedata = {'baseMVA': baseMVA,
                'gencost': gencost,
                'gen': gen,
                'branch': branch,
                'bus': bus}

    return rundcpf(casedata, ppopt=ppopt, fname=fname)

def solve_dcpf(case, hour=None,
        results=None,
        ppopt={'VERBOSE': False},
        fname='./runpf.log'):

    fname = os.path.abspath(fname)

    baseMVA = case.baseMVA
    bus = case.bus.copy(deep=True)
    branch = case.branch.copy(deep=True)
    gen = case.gen.copy(deep=True)
    gencost = case.gen.copy(deep=True)

    if hour is not None:
        logger.debug("Setting bus load based on case.load")
        bus['PD'] = case.load.loc[hour]
        bus = bus.fillna(0)

    if hour is not None and results is not None:
        logger.debug("Setting GEN_STATUS and PG")
        gen['GEN_STATUS'] = results.unit_commitment.loc[hour].astype(int)
        gen['PG'] = results.power_generated.loc[hour]

    value = [i + 1 for i in range(0, len(bus.index))]
    bus_name = bus.index
    bus.index = value
    bus.index = bus.index.astype(int)
    branch['F_BUS'] = branch['F_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    branch['T_BUS'] = branch['T_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    gen['GEN_BUS'] = gen['GEN_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)

    bus = np.array(bus.reset_index())
    branch = np.array(branch)
    gen = np.array(gen)
    gencost = np.array(gencost)

    casedata = {'baseMVA': baseMVA,
                'gencost': gencost,
                'gen': gen,
                'branch': branch,
                'bus': bus}

    return rundcpf(casedata, ppopt=ppopt, fname=fname)

def solve_pf(case, hour=None,
        results=None,
        ppopt={'VERBOSE': False},
        set_generator_status=False,
        fname='./runpf.log'):

    fname = os.path.abspath(fname)

    baseMVA = case.baseMVA
    bus = case.bus.copy(deep=True)
    branch = case.branch.copy(deep=True)
    gen = case.gen.copy(deep=True)
    gencost = case.gen.copy(deep=True)

    if hour is not None:
        logger.debug("Setting bus load based on case.load")
        bus['PD'] = case.load.loc[hour]
        bus = bus.fillna(0)

    if hour is not None and results is not None:
        logger.debug("Setting GEN_STATUS and PG")
        if set_generator_status is True:
            gen['GEN_STATUS'] = results.unit_commitment.loc[hour].astype(int)
        gen['PG'] = results.power_generated.loc[hour]

    value = [i + 1 for i in range(0, len(bus.index))]
    bus_name = bus.index
    bus.index = value
    bus.index = bus.index.astype(int)
    branch['F_BUS'] = branch['F_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    branch['T_BUS'] = branch['T_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)
    gen['GEN_BUS'] = gen['GEN_BUS'].apply(lambda x: value[bus_name.get_loc(x)]).astype(int)

    bus = np.array(bus.reset_index())
    branch = np.array(branch)
    gen = np.array(gen)
    gencost = np.array(gencost)

    casedata = {'baseMVA': baseMVA,
                'gencost': gencost,
                'gen': gen,
                'branch': branch,
                'bus': bus}

    return runpf(casedata, ppopt=ppopt, fname=fname)


def find_violated_lines(original_case_branch, results_case_branch):
    s = (pd.Series(abs(results_case_branch[:, 13])) > original_case_branch['RATE_A']) & (original_case_branch['RATE_A'] != 0)
    return s[s==True].index
