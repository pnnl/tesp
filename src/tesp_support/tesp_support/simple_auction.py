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

def parse_kw(arg):
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

# Class definition
class simple_auction:
    # ====================Define instance variables ===================================
    def __init__(self,dict,key):
        self.name = key
        self.std_dev = float(dict['init_stdev'])
        self.mean = float(dict['init_price'])
        self.period = float(dict['period'])
        self.pricecap = float(dict['pricecap'])
        self.max_capacity_reference_bid_quantity = float(dict['max_capacity_reference_bid_quantity'])
        self.statistic_mode = float(dict['statistic_mode'])
        self.stat_mode = dict['stat_mode']
        self.stat_interval = dict['stat_interval']
        self.stat_type = dict['stat_type']
        self.stat_value = dict['stat_value']

        # updated in collect_agent_bids, used in clear_market
        self.curve_buyer = None
        self.curve_seller = None

        self.refload = 0.0
        self.lmp = self.mean
        self.unresp = 0.0
        self.agg_unresp = 0.0
        self.agg_resp_max = 0.0
        self.agg_deg = 0
        self.agg_c2 = 0.0
        self.agg_c1 = 0.0
        self.clearing_type = ClearingType.NULL
        self.clearing_quantity = 0
        self.clearing_price = self.mean
        self.marginal_quantity = 0.0
        self.marginal_frac = 0.0

        self.clearing_scalar = 0.5 # TODO - this used to be configurable

    def set_refload (self, kw):
        self.refload = kw

    def set_lmp (self, lmp):
        self.lmp = lmp
                
    def initAuction (self):
        # TODO: set up the statistical history
        self.clearing_price = self.lmp = self.mean

    def update_statistics (self): # TODO
        sample_need = 0

    def clear_bids (self):
        self.curve_buyer = curve ()
        self.curve_seller = curve ()
        self.unresp = self.refload
                       
    def collect_bid (self, bid):
        price = bid[0]
        quantity = bid[1]
        is_on = bid[2]
        if is_on:
            self.unresp -= quantity
        if price > 0.0:  # TODO: if bidding negative, this assumes the HVAC load will not respond
            self.curve_buyer.add_to_curve (price, quantity, is_on)

    def aggregate_bids (self):
        if self.unresp > 0:
            self.curve_buyer.add_to_curve (self.pricecap, self.unresp, True)
        else:
            print ('$$ flag,Unresp,BuyCount,BuyTotal,BuyOn,BuyOff', flush=True)
            print ('$$ unresp < 0', self.unresp, self.curve_buyer.count, 
                   self.curve_buyer.total, self.curve_buyer.total_on, self.curve_buyer.total_off, sep=',', flush=True)
        if self.curve_buyer.count > 0:
            self.curve_buyer.set_curve_order ('descending')
        self.agg_unresp, self.agg_resp_max, self.agg_deg, self.agg_c2, self.agg_c1 = aggregate_bid (self.curve_buyer)

    def clear_market (self, tnext_clear=0, time_granted=0):
        self.curve_seller.add_to_curve (self.lmp, self.max_capacity_reference_bid_quantity, True)
        if self.curve_seller.count > 0:
            self.curve_seller.set_curve_order ('ascending')

        self.unresponsive_sell = self.responsive_sell = self.unresponsive_buy = self.responsive_buy = 0

        if self.curve_buyer.count > 0 and self.curve_seller.count > 0:
            a = self.pricecap
            b = -self.pricecap
            check = 0
            demand_quantity = supply_quantity = 0
            for i in range(self.curve_seller.count):
                if self.curve_seller.price[i] == self.pricecap:
                    self.unresponsive_sell += self.curve_seller.quantity[i]
                else:
                    self.responsive_sell += self.curve_seller.quantity[i]
            for i in range(self.curve_buyer.count):
                if self.curve_buyer.price[i] == self.pricecap:
                    self.unresponsive_buy += self.curve_buyer.quantity[i]
                else:
                    self.responsive_buy += self.curve_buyer.quantity[i]
            # Calculate clearing quantity and price here
            # Define the section number of the buyer and the seller curves respectively as i and j
            i = j = 0
            self.clearing_type = ClearingType.NULL
            self.clearing_quantity = self.clearing_price = 0
            while i < self.curve_buyer.count and j < self.curve_seller.count and self.curve_buyer.price[i] >= self.curve_seller.price[j]:
                buy_quantity = demand_quantity + self.curve_buyer.quantity[i]
                sell_quantity = supply_quantity + self.curve_seller.quantity[j]
                # If marginal buyer currently:
                if buy_quantity > sell_quantity:
                    self.clearing_quantity = supply_quantity = sell_quantity
                    a = b = self.curve_buyer.price[i]
                    j += 1
                    check = 0
                    self.clearing_type = ClearingType.BUYER
                # If marginal seller currently:
                elif buy_quantity < sell_quantity:
                    self.clearing_quantity = demand_quantity = buy_quantity
                    a = b = self.curve_seller.price[j]
                    i += 1
                    check = 0
                    self.clearing_type = ClearingType.SELLER
                # Buy quantity equal sell quantity but price split  
                else:
                    self.clearing_quantity = demand_quantity = supply_quantity = buy_quantity
                    a = self.curve_buyer.price[i]
                    b = self.curve_seller.price[j]
                    i += 1
                    j += 1
                    check = 1
            # End of the curve comparison, and if EXACT, get the clear price
            if a == b:
                self.clearing_price = a 
            # If there was price agreement or quantity disagreement
            if check:
                self.clearing_price = a 
                if supply_quantity == demand_quantity:
                    # At least one side exhausted at same quantity
                    if i == self.curve_buyer.count or j == self.curve_seller.count:
                        if a == b:
                            self.clearing_type = ClearingType.EXACT
                        else:
                            self.clearing_type = ClearingType.PRICE
                    # Exhausted buyers, sellers unsatisfied at same price
                    elif i == self.curve_buyer.count and b == self.curve_seller.price[j]:
                        self.clearing_type = ClearingType.SELLER
                    # Exhausted sellers, buyers unsatisfied at same price
                    elif j == self.curve_seller.count and a == self.curve_buyer.price[i]:
                        self.clearing_type = ClearingType.BUYER
                    # Both sides satisfied at price, but one side exhausted  
                    else:
                        if a == b:
                            self.clearing_type = ClearingType.EXACT
                        else:
                            self.clearing_type = ClearingType.PRICE
                # No side exausted
                else:
                    # Price changed in both directions
                    if a != self.curve_buyer.price[i] and b != self.curve_seller.price[j] and a == b:
                        self.clearing_type = ClearingType.EXACT
                    # Sell price increased ~ marginal buyer since all sellers satisfied
                    elif a == self.curve_buyer.price[i] and b != self.curve_seller.price[j]:
                        self.clearing_type = ClearingType.BUYER
                    # Buy price increased ~ marginal seller since all buyers satisfied
                    elif a != self.curve_buyer.price[i] and b == self.curve_seller.price[j]:
                        self.clearing_type = ClearingType.SELLER
                        self.clearing_price = b # use seller's price, not buyer's price
                    # Possible when a == b, q_buy == q_sell, and either the buyers or sellers are exhausted
                    elif a == self.curve_buyer.price[i] and b == self.curve_seller.price[j]:
                        if i == self.curve_buyer.count and j == self.curve_seller.count:
                            self.clearing_type = ClearingType.EXACT
                        elif i == self.curve_buyer.count:
                            self.clearing_type = ClearingType.SELLER
                        elif j == self.curve_seller.count:
                            self.clearing_type = ClearingType.BUYER
                    else:
                        # Marginal price
                        self.clearing_type = ClearingType.PRICE
                
                # If ClearingType.PRICE, calculate the clearing price here
                dHigh = dLow = 0
                if self.clearing_type == ClearingType.PRICE:
                    avg = (a+b)/2.0
                    # Calculating clearing price limits:   
                    dHigh = a if i == self.curve_buyer.count else self.curve_buyer.price[i]
                    dLow = b if j == self.curve_seller.count else self.curve_seller.price[j]
                    # Needs to be just off such that it does not trigger any other bids
                    if a == self.pricecap and b != -self.pricecap:
                        if self.curve_buyer.price[i] > b:
                            self.clearing_price = self.curve_buyer.price[i] + bid_offset
                        else:
                            self.clearing_price = b 
                    elif a != self.pricecap and b == -self.pricecap:
                        if self.curve_seller.price[j] < a:
                            self.clearing_price = self.curve_seller.price[j] - bid_offset
                        else:
                            self.clearing_price = a 
                    elif a == self.pricecap and b == -self.pricecap:
                        if i == self.curve_buyer.count and j == self.curve_seller.count:
                            self.clearing_price = 0 # no additional bids on either side
                        elif j == self.curve_seller.count: # buyers left
                            self.clearing_price = self.curve_buyer.price[i] + bid_offset
                        elif i == self.curve_buyer.count: # sellers left
                            self.clearing_price = self.curve_seller.price[j] - bid_offset
                        else: # additional bids on both sides, just no clearing
                            self.clearing_price = (dHigh + dLow)/2
                    else:
                        if i != self.curve_buyer.count and self.curve_buyer.price[i] == a:
                            self.clearing_price = a 
                        elif j != self.curve_seller.count and self.curve_seller.price[j] == b:
                            self.clearing_price = b 
                        elif i != self.curve_buyer.count and avg < self.curve_buyer.price[i]:
                            self.clearing_price = dHigh + bid_offset
                        elif j != self.curve_seller.count and avg > self.curve_seller.price[j]:
                            self.clearing_price = dLow - bid_offset
                        else:
                            self.clearing_price = avg 
                                
            # Check for zero demand but non-zero first unit sell price
            if self.clearing_quantity == 0:
                self.clearing_type = ClearingType.NULL
                if self.curve_seller.count > 0 and self.curve_buyer.count == 0:
                    self.clearing_price = self.curve_seller.price[0] - bid_offset
                elif self.curve_seller.count == 0 and self.curve_buyer.count > 0:
                    self.clearing_price = self.curve_buyer.price[0] + bid_offset
                else:
                    if self.curve_seller.price[0] == self.pricecap:
                        self.clearing_price = self.curve_buyer.price[0] + bid_offset
                    elif self.curve_seller.price[0] == -self.pricecap:
                        self.clearing_price = self.curve_seller.price[0] - bid_offset  
                    else:
                        self.clearing_price = self.curve_seller.price[0] + (self.curve_buyer.price[0] - self.curve_seller.price[0]) * self.clearing_scalar
           
            elif self.clearing_quantity < self.unresponsive_buy:
                self.clearing_type = ClearingType.FAILURE
                self.clearing_price = self.pricecap
            
            elif self.clearing_quantity < self.unresponsive_sell:
                self.clearing_type = ClearingType.FAILURE
                self.clearing_price = -self.pricecap
            
            elif self.clearing_quantity == self.unresponsive_buy and self.clearing_quantity == self.unresponsive_sell:
                # only cleared unresponsive loads
                self.clearing_type = ClearingType.PRICE
                self.clearing_price = 0.0
            
        # If the market mode MD_NONE and at least one side is not given
        else:
            if self.curve_seller.count > 0 and self.curve_buyer.count == 0:
                self.clearing_price = self.curve_seller.price[0] - bid_offset
            elif self.curve_seller.count == 0 and self.curve_buyer.count > 0:
                self.clearing_price = self.curve_buyer.price[0] + bid_offset
            elif self.curve_seller.count > 0 and self.curve_buyer.count > 0:
                self.clearing_price = self.curve_seller.price[0] + (self.curve_buyer.price[0] - self.curve_seller.price[0]) * self.clearing_scalar
            elif self.curve_seller.count == 0 and self.curve_buyer.count == 0:
                self.clearing_price = 0.0
            self.clearing_quantity = 0
            self.clearing_type = ClearingType.NULL
            if self.curve_seller.count == 0 :
                missingBidder = "seller"
            elif self.curve_buyer.count == 0:
                missingBidder = "buyer"
            print ('  Market %s fails to clear due to missing %s' % (self.name, missingBidder), flush=True)
            
        # Calculation of the marginal 
        marginal_total = self.marginal_quantity = self.marginal_frac = 0.0
        if self.clearing_type == ClearingType.BUYER:
            marginal_subtotal = 0
            i = 0
            for i in range(self.curve_buyer.count):
                if self.curve_buyer.price[i] > self.clearing_price:
                    marginal_subtotal = marginal_subtotal + self.curve_buyer.quantity[i]
                else:
                    break
            self.marginal_quantity =  self.clearing_quantity - marginal_subtotal
            for j in range(i, self.curve_buyer.count):
                if self.curve_buyer.price[i] == self.clearing_price:
                    marginal_total += self.curve_buyer.quantity[i]
                else:
                    break
            if marginal_total > 0.0:
                self.marginal_frac = float(self.marginal_quantity) / marginal_total
       
        elif self.clearing_type == ClearingType.SELLER:
            marginal_subtotal = 0
            i = 0
            for i in range(0, self.curve_seller.count):
                if self.curve_seller.price[i] > self.clearing_price:
                    marginal_subtotal = marginal_subtotal + self.curve_seller.quantity[i]
                else:
                    break
            self.marginal_quantity =  self.clearing_quantity - marginal_subtotal
            for j in range(i, self.curve_seller.count):
                if self.curve_seller.price[i] == self.clearing_price:
                    marginal_total += self.curve_seller.quantity[i]
                else:
                    break
            if marginal_total > 0.0:
                self.marginal_frac = float (self.marginal_quantity) / marginal_total 
        
        else:
            self.marginal_quantity = 0.0
            self.marginal_frac = 0.0
        print ('##', time_granted, tnext_clear, self.clearing_type, self.clearing_quantity, self.clearing_price, 
               self.curve_buyer.count, self.unresponsive_buy, self.responsive_buy,
               self.curve_seller.count, self.unresponsive_sell, self.responsive_sell,
               self.marginal_quantity, self.marginal_frac, self.lmp, self.refload, sep=',', flush=True)

class hvac:
    def __init__(self,dict,key,aucObj):
        self.name = key
        self.control_mode = dict['control_mode']
        self.houseName = dict['houseName']
        self.meterName = dict['meterName']
        self.period = float(dict['period'])
        self.wakeup_start = float(dict['wakeup_start'])
        self.daylight_start = float(dict['daylight_start'])
        self.evening_start = float(dict['evening_start'])
        self.night_start = float(dict['night_start'])
        self.wakeup_set = float(dict['wakeup_set'])
        self.daylight_set = float(dict['daylight_set'])
        self.evening_set = float(dict['evening_set'])
        self.night_set = float(dict['night_set'])
        self.weekend_day_start = float(dict['weekend_day_start'])
        self.weekend_day_set = float(dict['weekend_day_set'])
        self.weekend_night_start = float(dict['weekend_night_start'])
        self.weekend_night_set = float(dict['weekend_night_set'])
        self.deadband = float(dict['deadband'])
        self.offset_limit = float(dict['offset_limit'])
        self.ramp = float(dict['ramp'])
        self.price_cap = float(dict['price_cap'])
        self.bid_delay = float(dict['bid_delay'])
        self.use_predictive_bidding = float(dict['use_predictive_bidding'])

        self.std_dev = aucObj.std_dev
        self.mean = aucObj.clearing_price

        self.Trange = abs (2.0 * self.offset_limit)

        self.air_temp = 78.0
        self.hvac_kw = 3.0
        self.mtr_v = 120.0
        self.hvac_on = False

        self.basepoint = 0.0
        self.setpoint = 0.0
        self.cleared_price = 0.0
        self.bid_price = 0.0

    def inform_bid (self,price):
        self.cleared_price = price

    # bid is always "accepted"; if I didn't bid high enough, I might have to turn the thermostat up
    def bid_accepted (self):
        if self.std_dev > 0.0:
            offset = (self.cleared_price - self.mean) * self.Trange / self.ramp / self.std_dev
            if offset < -self.offset_limit:
                offset = -self.offset_limit
            elif offset > self.offset_limit:
                offset = self.offset_limit
            self.setpoint = self.basepoint + offset
            return True
        return False

    def formulate_bid (self):
        p = self.mean + (self.air_temp - self.basepoint) * self.ramp * self.std_dev / self.Trange
        if p >= self.price_cap:
            self.bid_price = self.price_cap
        elif p <= 0.0:
            self.bid_price = 0.0
        else:
            self.bid_price = p
        return [self.bid_price, self.hvac_kw, self.hvac_on]

    def change_basepoint (self,hod,dow):
        if dow > 4: # a weekend
            val = self.weekend_night_set
            if hod >= self.weekend_day_start and hod < self.weekend_night_start:
                val = self.weekend_day_set
        else: # a weekday
            val = self.night_set
            if hod >= self.wakeup_start and hod < self.daylight_start:
                val = self.wakeup_set
            elif hod >= self.daylight_start and hod < self.evening_start:
                val = self.daylight_set
            elif hod >= self.evening_start and hod < self.night_start:
                val = self.evening_set
        if abs(self.basepoint - val) > 0.1:
            self.basepoint = val
            return True
        return False

    def set_hvac_load (self,str):
        val = parse_fncs_number (str)
        if val > 0.0:
            self.hvac_kw = val

    def set_hvac_state (self,str):
        if str == 'OFF':
            self.hvac_on = False
        else:
            self.hvac_on = True

    def set_air_temp (self,str):
        self.air_temp = parse_fncs_number (str)

    def set_voltage (self,str):
        self.mtr_v = parse_fncs_magnitude (str)

