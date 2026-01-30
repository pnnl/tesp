# Copyright (c) 2017-2025 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: helpers.py
""" Utility functions for use within tesp_support, including new agents.
"""

import logging
import json
from scipy.stats import truncnorm
from numpy import random

# Setting up main/standard logging with INFO level
log = logging.getLogger()
log.setLevel(logging.INFO)

def enable_logging(level, model_diag_level, name_prefix):
    """ Enable logging for process

        Args:
            level (str): the logging level you want set for the process
            model_diag_level (int): initial value used to filter logging files
            name_prefix (str): description prefix for the log file name
    """
    if level == 'DEBUG':
        log.setLevel(logging.DEBUG)
    elif level == 'INFO':
        log.setLevel(logging.INFO)
    elif level == 'WARNING':
        log.setLevel(logging.WARNING)
    elif level == 'ERROR':
        log.setLevel(logging.ERROR)
    elif level == 'CRITICAL':
        log.setLevel(logging.CRITICAL)
    else:
        print('WARNING: unknown logging level specified, reverting to default INFO level')
        log.setLevel(logging.INFO)

    main_fh = logging.FileHandler(name_prefix + '_log.txt', mode='w')
    main_format = logging.Formatter('%(levelname)s: %(module)s: %(lineno)d: %(message)s')
    main_fh.setFormatter(main_format)
    main_fh.addFilter(all_but_one_level(model_diag_level))
    log.addHandler(main_fh)

    # Setting up model diagnostics logging output
    model_diag_fh = logging.FileHandler(name_prefix + '_diag.txt', mode='w')
    model_diag_fh.setLevel(model_diag_level)
    model_diag_format = logging.Formatter('%(levelname)s: %(module)s: %(lineno)d: %(message)s')
    model_diag_fh.setFormatter(model_diag_format)
    model_diag_fh.addFilter(all_from_one_level_down(model_diag_level))
    log.addHandler(model_diag_fh)

    log.addHandler(logging.StreamHandler())
    return log


class all_from_one_level_down(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


class all_but_one_level(object):
    def __init__(self, level):
        self.__level = level

    @staticmethod
    def filter(log_record):
        return log_record.levelno != 11


def randomize_skew(value, skew_max):
    sk = value * random.randn()
    if sk < -skew_max:
        sk = -skew_max
    elif sk > skew_max:
        sk = skew_max
    return sk


def randomize_commercial_skew():
    commercial_skew_max = 5400
    commercial_skew_std = 1800
    return randomize_skew(commercial_skew_std, commercial_skew_max)


def randomize_residential_skew(wh_skew=False):
    residential_skew_max = 8100
    residential_skew_std = 2700
    if wh_skew:
        return randomize_skew(3*residential_skew_std, 6*residential_skew_max)
    else:
        return randomize_skew(residential_skew_std, residential_skew_max)


def get_run_solver(name:str, pyo, model, solver, params=None):
    """ Solve the pyomo model with the specified solver, checking that the
      solver is available and that the model solves.

    Args:
        name (str): name of the solver, ex: hvac_{house_name}
        pyo (module): the pyomo module (import pyomo.environ as pyo)
        model: the pyomo model instance to be solved (pyo.ConcreteModel())
        solver (str): choice of solver. Prefer cplex over ipopt for production runs

    Raises:
        RuntimeError: If the solver is not available, or if the solver does not
          complete with an acceptable status/termination condition. The 
          exception message includes the model name, solver name, and solver 
          status.

    Returns:
        results: solver results object
    """

    from pyomo.opt import SolverStatus, TerminationCondition
    opt = pyo.SolverFactory(solver)
    if opt is None or not opt.available():
        raise RuntimeError(f"[{name}] Solver '{solver}' not available")

    results = opt.solve(model, tee=False)

    status = results.solver.status
    term   = results.solver.termination_condition

    # Acceptable termination conditions
    acceptable_terms = {
        TerminationCondition.optimal,
        TerminationCondition.locallyOptimal,
        TerminationCondition.feasible,
    }

    if status != SolverStatus.ok or term not in acceptable_terms:
        # Optional, print more detail:
        if params:
            params["success"] = False
            params["termination"] = term

        # raise RuntimeError(f"[{name}] Solver '{solver}' failed: "
        #        f"status={status}, termination={term}")
        

    return results


def random_norm_trunc(dist_array):
    if 'standard_deviation' in dist_array:
        dist_array['std'] = dist_array['standard_deviation']
    return truncnorm.rvs((dist_array['min'] - dist_array['mean']) / dist_array['std'],
                         (dist_array['max'] - dist_array['mean']) / dist_array['std'],
                         loc=dist_array['mean'], scale=dist_array['std'], size=1)[0]
    # return np.random.uniform(dist_array['min'], dist_array['max'])


def zoneMeterName(ldname):
    """ Enforces the meter naming convention for commercial zones
    The commercial zones must be children of load objects
    This routine replaces "_load_" with "_meter".

    Args:
        ldname (str): the GridLAB-D name of a load, ends with _load_##

    Returns:
      str: The GridLAB-D name of upstream meter
    """
    return ldname.replace('_load_', '_meter_')


def gld_strict_name(name, prefix="gld_"):
    """ Sanitizes a name for GridLAB-D publication to FNCS
    GridLAB-D name should not begin with a number, or contain '-' for FNCS

    Args:
        name (str): the input name
        prefix (str): the prefix to be use if the name starts with a number

    Returns:
        str: name with all '-' replaced by '_', and any leading digit replaced by prefix
    """
    name = name.replace('"', '')
    if name[0].isdigit():
        name = prefix + name
    return name.replace('-', '_')


def get_region(s):
    region = 0
    if 'R1' in s:
        region = 1
    elif 'R2' in s:
        region = 2
    elif 'R3' in s:
        region = 3
    elif 'R4' in s:
        region = 4
    elif 'R5' in s:
        region = 5
    return region


class HelicsMsg(object):

    def __init__(self, name, period):
        # change logging to debug, warning, error
        self._subs = []
        self._pubs = []
        self._cnfg = {"name": name,
                      "period": period,
                      "logging": "warning",
                      }
        pass

    def write_file(self, _fn):
        self.config("publications", self._pubs)
        self.config("subscriptions", self._subs)
        op = open(_fn, 'w', encoding='utf-8')
        json.dump(self._cnfg, op, ensure_ascii=False, indent=2)
        op.close()

    def config(self, _n, _v):
        self._cnfg[_n] = _v

    def pubs(self, _g, _k, _t, _o, _p):
        # for object and property is for internal code interface for GridLAB-D
        self._pubs.append({"global": _g, "key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def pubs_n(self, _g, _k, _t):
        self._pubs.append({"global": _g, "key": _k, "type": _t})

    def pubs_e(self, _g, _k, _t, _u):
        # for object and property is for internal code interface for EnergyPlus
        self._pubs.append({"global": _g, "key": _k, "type": _t, "unit": _u})

    def subs(self, _k, _t, _o, _p):
        # for object and property is for internal code interface for GridLAB-D
        self._subs.append({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_e(self, _r, _k, _t, _i):
        # for object and property is for internal code interface for EnergyPlus
        self._subs.append({"key": _k, "type": _t, "require": _r, "info": _i})

    def subs_n(self, _k, _t):
        self._subs.append({"key": _k, "type": _t})
