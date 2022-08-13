# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: helpers.py
""" Utility functions for use within tesp_support, including new agents.
"""
import re
import math
import json
import numpy as np
from enum import IntEnum


def idf_int(val):
    """Helper function to format integers for the EnergyPlus IDF input data file

    Args:
      val (int): the integer to format

    Returns:
       str: the integer in string format, padded with a comma and zero or one blanks, in order to fill three spaces
    """
    sval = str(val)
    if len(sval) < 2:
        return sval + ', '
    return sval + ','


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
    """Sanitizes a name for GridLAB-D publication to FNCS
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
            is_on (Boolean): True if the load is currently on, False if not
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
                # If the price is larger than the compared curve section price, price inserted before that section of the curve
                if price >= self.price[i]:
                    if i == 0:
                        # If the price is larger than that of all the curve sections, insert at the beginning of the curve
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


def parse_number(arg):
    """ Parse floating-point number from a FNCS message; must not have leading sign or exponential notation

    Args:
        arg (str): the FNCS string value

    Returns:
        float: the parsed number
    """
    try:
        return float(arg)
    except:
        return float(''.join(ele for ele in arg if ele.isdigit() or ele == '.'))


# strip out extra white space, units (deg, degF, V, MW, MVA, KW, KVA) and ;
def parse_magnitude_1(arg):
    """ Parse the magnitude of a possibly complex number from FNCS
    Args:
        arg (str): the FNCS string value
    Returns:
        float: the parsed number, or 0 if parsing fails
    """
    tok = arg.strip('+-; MWVAFKdegrij')
    vals = re.split(r'[\+-]+', tok)
    if len(vals) < 2:  # only a real part provided
        vals.append('0')
    vals = [float(v) for v in vals]

    if '-' in tok:
        vals[1] *= -1.0
    if arg.startswith('-'):
        vals[0] *= -1.0
    return vals[0]


def parse_magnitude_2(arg):
    """Helper function to find the magnitude of a possibly complex number from FNCS

    Args:
      arg (str): The FNCS value
    """
    tok = arg.strip('+-; MWVAFKdegrij')
    vals = re.split(r'[\+-]+', tok)
    if len(vals) < 2:  # only a real part provided
        vals.append('0')

    vals[0] = float(vals[0])
    if arg.startswith('-'):
        vals[0] *= -1.0
    return vals[0]


def parse_helic_input(arg):
    """Helper function to find the magnitude of a possibly complex number from Helics as a string

    Args:
      arg (str): The Helics value
    """
    try:

        tok = arg.strip('[]')
        vals = re.split(',', tok)
        if len(vals) < 2:  # only a real part provided
            vals.append('0')

        vals[0] = float(vals[0])
        return vals[0]
    except:
        print('parse_helic_input does not understand"' + arg + '"')
        return 0


def parse_magnitude(arg):
    """ Parse the magnitude of a possibly complex number from FNCS

    Args:
        arg (str): the FNCS string value

    Returns:
        float: the parsed number, or 0 if parsing fails
    """
    try:
        if ('d ' in arg) or ('r ' in arg):  # polar form
            tok = arg.strip('; MWVAKdrij')
            nsign = nexp = ndot = 0
            for i in range(len(tok)):
                if (tok[i] == '+') or (tok[i] == '-'):
                    nsign += 1
                elif (tok[i] == 'e') or (tok[i] == 'E'):
                    nexp += 1
                elif tok[i] == '.':
                    ndot += 1
                if nsign == 1:
                    kpos = i
                if nsign == 2 and nexp == 0:
                    kpos = i
                    break
                if nsign == 3:
                    kpos = i
                    break
            vals = [tok[:kpos], tok[kpos:]]
            vals = [float(v) for v in vals]
            return vals[0]
        tok = arg.strip('; MWVACFKdegri').replace(" ", "")  # rectangular form, including real only
        b = complex(tok)
        return abs(b)  # b.real
    except:
        try:
            return parse_helic_input(arg)
        except:
            print('parse_magnitude does not understand' + arg)
            return 0


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


def parse_kva(arg):  # this drops the sign of p and q
    """Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

    Args:
        arg (str): the GridLAB-D P+jQ value

    Returns:
        float: the parsed kva value
    """
    toks = list(filter(None, re.split('[\+j-]', arg)))
    p = float(toks[0])
    q = float(toks[1])
    return 0.001 * math.sqrt(p * p + q * q)


def parse_kva_old(arg):
    tok = arg.strip('; MWVAKdrij')
    nsign = nexp = ndot = 0
    for i in range(len(tok)):
        if (tok[i] == '+') or (tok[i] == '-'):
            nsign += 1
        elif (tok[i] == 'e') or (tok[i] == 'E'):
            nexp += 1
        elif tok[i] == '.':
            ndot += 1
        if nsign == 2 and nexp == 0:
            kpos = i
            break
        if nsign == 3:
            kpos = i
            break

    vals = [tok[:kpos], tok[kpos:]]
    vals = [float(v) for v in vals]

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
        p *= 1.0
        q *= 1.0
    elif 'MVA' in arg:
        p *= 1000.0
        q *= 1000.0
    else:  # VA
        p /= 1000.0
        q /= 1000.0
    return math.sqrt(p * p + q * q)


def parse_kw(arg):
    """ Parse the kilowatt load of a possibly complex number from FNCS

    Args:
        arg (str): the FNCS string value

    Returns:
        float: the parsed number in kW, or 0 if parsing fails
    """
    try:
        tok = arg.strip('; MWVAKdrij')
        nsign = nexp = ndot = 0
        for i in range(len(tok)):
            if (tok[i] == '+') or (tok[i] == '-'):
                nsign += 1
            elif (tok[i] == 'e') or (tok[i] == 'E'):
                nexp += 1
            elif tok[i] == '.':
                ndot += 1
            if nsign == 2 and nexp == 0:
                kpos = i
                break
            if nsign == 3:
                kpos = i
                break

        vals = [tok[:kpos], tok[kpos:]]
        vals = [float(v) for v in vals]

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
            p *= 1.0
            q *= 1.0
        elif 'MVA' in arg:
            p *= 1000.0
            q *= 1000.0
        else:  # VA
            p /= 1000.0
            q /= 1000.0

        return p
    except:
        try:
            return parse_helic_input(arg)/1000.0
        except:
            print('parse_kw does not understand', arg)
            return 0


def aggregate_bid(crv):
    """aggregates the buyer curve into a quadratic or straight-line fit with zero intercept

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
