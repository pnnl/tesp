# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: curve.py
""" Utility functions for use within tesp_support, including new agents.
"""

import numpy as np
from enum import IntEnum


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
