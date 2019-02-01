# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: helpers.py
import numpy as np
import math
import warnings
import re
import sys
from copy import deepcopy
from enum import IntEnum

class ClearingType (IntEnum):
    NULL = 0
    FAILURE = 1
    PRICE = 2
    EXACT = 3
    SELLER = 4
    BUYER = 5

class curve:
    def __init__(self):
        self.price = []
        self.quantity = []
        self.count = 0
        self.total = 0.0
        self.total_on = 0.0
        self.total_off = 0.0  

    def set_curve_order(self, flag):
        if flag == 'ascending':
            self.price.reverse()
            self.quantity.reverse()

    def add_to_curve(self, price, quantity, is_on):
        if quantity == 0:
            return
        self.total += quantity
        if is_on:
            self.total_on += quantity
        else:
            self.total_off += quantity
        value_insert_flag = 0
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

def parse_fncs_number (arg):
    return float(''.join(ele for ele in arg if ele.isdigit() or ele == '.'))

# strip out extra white space, units (deg, degF, V, MW, MVA, KW, KVA) and ;
def parse_fncs_magnitude (arg):
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
            vals = [tok[:kpos],tok[kpos:]]
            vals = [float(v) for v in vals]
            return vals[0]
        tok = arg.strip('; MWVAFKdegri').replace(" ", "") # rectangular form, including real only
        b = complex(tok)
        return abs (b) # b.real
    except:
        print ('parse_fncs_magnitude does not understand', arg)
        return 0

def parse_kw(arg):
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

        vals = [tok[:kpos],tok[kpos:]]
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
        print ('parse_kw does not understand', arg)
        return 0

# aggregates the buyer curve into a quadratic or straight-line fit with zero intercept, returned as
# [Qunresp, Qmaxresp, degree, c2, c1]
# scaled to MW instead of kW for the opf
def aggregate_bid (crv):
    unresp = 0
    idx = 0
    pInd = np.flip(np.argsort(np.array(crv.price)), 0)
    p = 1000.0 * np.array (crv.price)[pInd]  # $/MW
    q = 0.001 * np.array (crv.quantity)[pInd] # MWhr
    if p.size > 0:
        idx = np.argwhere (p == p[0])[-1][0]
        unresp = np.cumsum(q[:idx+1])[-1]
    c2 = 0
    c1 = 0
    deg = 0
    n = p.size - idx - 1

    if n < 1:
        qmax = 0
        deg = 0
    else:
        qresp = np.cumsum(q[idx+1:])
        presp = p[idx+1:]
        qmax = qresp[-1]
        cost = np.cumsum(np.multiply(presp, q[idx+1:]))
        if n <= 2:
            A = np.vstack([qresp, np.ones(len(qresp))]).T
            ret = np.linalg.lstsq(A[:, :-1],cost)[0]
            c1 = ret[0]
            deg = 1
        else:
            A = np.vstack([qresp**2, qresp, np.ones(len(qresp))]).T
            ret = np.linalg.lstsq(A[:, :-1],cost,rcond=None)[0]
            c2 = ret[0]
            c1 = ret[1]
            deg = 2
    bid = [unresp, qmax, deg, c2, c1]
    return bid

