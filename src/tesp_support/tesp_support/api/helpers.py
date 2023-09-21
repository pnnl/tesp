# Copyright (C) 2017-2023 Battelle Memorial Institute
# file: helpers.py
""" Utility functions for use within tesp_support, including new agents.
"""

import logging
import json
import numpy as np
from enum import IntEnum
from scipy.stats import truncnorm


def enable_logging(level, model_diag_level):
    """ Enable logging for process

        Args:
            level (str): the logging level you want set for the process
            model_diag_level (int): initial value used to filter logging files
    """

    # Setting up main/standard debugging output
    logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)
    main_fh = logging.FileHandler('main_log.txt', mode='w')
    if level == 'DEBUG':
        main_fh.setLevel(logging.DEBUG)
    elif level == 'INFO':
        main_fh.setLevel(logging.INFO)
    elif level == 'WARNING':
        main_fh.setLevel(logging.WARNING)
    elif level == 'ERROR':
        main_fh.setLevel(logging.ERROR)
    elif level == 'CRITICAL':
        main_fh.setLevel(logging.CRITICAL)
    else:
        print('WARNING: unknown logging level specified, reverting to default INFO level')
        main_fh.setLevel(logging.INFO)
    main_format = logging.Formatter('%(levelname)s: %(module)s: %(lineno)d: %(message)s')
    main_fh.setFormatter(main_format)
    main_fh.addFilter(all_but_one_level(model_diag_level))
    logger.addHandler(main_fh)

    # Setting up model diagnostics logging output
    model_diag_fh = logging.FileHandler('model_diagnostics.txt', mode='w')
    model_diag_fh.setLevel(model_diag_level)
    model_diag_format = logging.Formatter('%(levelname)s: %(module)s: %(lineno)d: %(message)s')
    model_diag_fh.setFormatter(model_diag_format)
    model_diag_fh.addFilter(one_level_only(model_diag_level))
    logger.addHandler(model_diag_fh)


class one_level_only(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


class all_but_one_level(object):
    def __init__(self, level):
        self.__level = level

    @staticmethod
    def filter(logRecord):
        return logRecord.levelno != 11


def get_run_solver(name, pyo, model, solver):
    # prefer cplex over ipopt (for production runs)
    try:
        solver = pyo.SolverFactory(solver)
    except Exception as e:  # could be better/more specific
        print('Name {}\n Warning ' + solver + ' not present; got exception {}'.format(name, e))
        exit()
    results = solver.solve(model, tee=False)
    # TODO better solver handling
    #    if results.solver.status != SolverStatus.ok:
    #    print("The " + name + " solver status of: {}".format(results.solver.status))
    # exit()
    #    if results.solver.termination_condition != TerminationCondition.optimal:
    #    print("The " + name + " termination condition of: {}".format(results.solver.termination_condition))
    # exit()
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


def gld_strict_name(val):
    """ Sanitizes a name for GridLAB-D publication to FNCS
    GridLAB-D name should not begin with a number, or contain '-' for FNCS

    Args:
        val (str): the input name

    Returns:
        str: val with all '-' replaced by '_', and any leading digit replaced by 'gld\_'
    """
    if val[0].isdigit():
        val = "gld_" + val
    return val.replace('-', '_')


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
        # for object and property is for internal code interface for gridlabd
        self._pubs.append({"global": _g, "key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def pubs_n(self, _g, _k, _t):
        self._pubs.append({"global": _g, "key": _k, "type": _t})

    def pubs_e(self, _g, _k, _t, _u):
        # for object and property is for internal code interface for eplus
        self._pubs.append({"global": _g, "key": _k, "type": _t, "unit": _u})

    def subs(self, _k, _t, _o, _p):
        # for object and property is for internal code interface for gridlabd
        self._subs.append({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_e(self, _r, _k, _t, _i):
        # for object and property is for internal code interface for eplus
        self._subs.append({"key": _k, "type": _t, "require": _r, "info": _i})

    def subs_n(self, _k, _t):
        self._subs.append({"key": _k, "type": _t})
