# Copyright (C) 2017-2022 Battelle Memorial Institute
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


class ClearingType(IntEnum):
    """ Describes the market clearing type
    """
    NULL = 0
    FAILURE = 1
    PRICE = 2
    EXACT = 3
    SELLER = 4
    BUYER = 5


class curve:
    """ Accumulates a set of price, quantity bids for later aggregation.
    The default order is descending by price.

    Attributes:
        price ([float]): array of prices, in $/kWh
        quantity ([float]): array of quantities, in kW
        count (int): the number of collected bids
        total (float): the total kW bidding
        total_on (float): the total kW bidding that are currently on
        total_off (float): the total kW bidding that are currently off
    """

    def __init__(self):
        self.price = []
        self.quantity = []
        self.count = 0
        self.total = 0.0
        self.total_on = 0.0
        self.total_off = 0.0

    def set_curve_order(self, flag):
        """ Set the curve order (by price) to ascending or descending

        Args:
            flag (str): 'ascending' or 'descending'
        """
        if flag == 'ascending':
            self.price.reverse()
            self.quantity.reverse()

    def add_to_curve(self, price, quantity, is_on):
        """ Add one point to the curve

        Args:
            price (float): the bid price, should be $/kWhr
            quantity (float): the bid quantity, should be kW
            is_on (bool): True if the load is currently on, False if not
        """
        if quantity == 0:
            return
        self.total += quantity
        if is_on:
            self.total_on += quantity
        else:
            self.total_off += quantity

        if self.count == 0:
            # Since it is the first time assigning values to the curve, define an empty array for the price and mean
            self.price = []
            self.quantity = []
            self.price.append(price)
            self.quantity.append(quantity)
            self.count += 1
        else:
            value_insert_flag = 0
            for i in range(0, self.count):
                # If the price is larger than the compared curve section price,
                # price inserted before that section of the curve
                if price >= self.price[i]:
                    if i == 0:
                        # If the price is larger than that of all the curve sections,
                        # insert at the beginning of the curve
                        self.price.insert(0, price)
                        self.quantity.insert(0, quantity)
                    else:
                        self.price.insert(i, price)
                        self.quantity.insert(i, quantity)
                    self.count += 1
                    value_insert_flag = 1
                    break

            # If the price is smaller than that of all the curve sections, insert at the end of the curve
            if value_insert_flag == 0:
                self.price.append(price)
                self.quantity.append(quantity)
                self.count += 1


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


def aggregate_bid(crv):
    """ Aggregates the buyer curve into a quadratic or straight-line fit with zero intercept

    Args:
        crv (curve): the accumulated buyer bids

    Returns:
        [float, float, int, float, float]: Qunresp, Qmaxresp, degree, c2 and c1 scaled to MW instead of kW. c0 is always zero.
    """
    unresp = 0
    idx = 0
    pInd = np.flip(np.argsort(np.array(crv.price)), 0)
    p = 1000.0 * np.array(crv.price)[pInd]  # $/MW
    q = 0.001 * np.array(crv.quantity)[pInd]  # MWhr
    if p.size > 0:
        idx = np.argwhere(p == p[0])[-1][0]
        unresp = np.cumsum(q[:idx + 1])[-1]
    c2 = 0
    c1 = 0
    deg = 0
    n = p.size - idx - 1

    if n < 1:
        qmax = 0
    else:
        qresp = np.cumsum(q[idx + 1:])
        presp = p[idx + 1:]
        qmax = qresp[-1]
        cost = np.cumsum(np.multiply(presp, q[idx + 1:]))
        if n <= 2:
            A = np.vstack([qresp, np.ones(len(qresp))]).T
            ret = np.linalg.lstsq(A[:, :-1], cost)[0]
            c1 = ret[0]
            deg = 1
        else:
            A = np.vstack([qresp ** 2, qresp, np.ones(len(qresp))]).T
            ret = np.linalg.lstsq(A[:, :-1], cost, rcond=None)[0]
            c2 = ret[0]
            c1 = ret[1]
            deg = 2
    bid = [unresp, qmax, deg, c2, c1]
    return bid
