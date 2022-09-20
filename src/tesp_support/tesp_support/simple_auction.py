# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: simple_auction.py
"""Double-auction mechanism for the 5-minute markets in te30 and sgip1 examples

The substation_loop module manages one instance of this class per GridLAB-D substation.

Todo:
    * Initialize and update price history statistics
    * Allow for adjustment of clearing_scalar
    * Handle negative price bids from HVAC agents, currently they are discarded
    * Distribute marginal quantities and fractions; these are not currently applied to HVACs

2021-10-29 TDH: Key assumptions we need to refactor out of this:
- This is a retail market working under a wholesale market. We want
something more general that can operate at any market level.
- Load state is not necessary information to run a market. PNNL TSP has
traditionally had the construct of responsive and unresponsive loads and I
think the idea is crucial for being able to get good quadratic curve
fits on the demand curve (by lopping off the unresponsive portion) but
I think we should refactor this so that these assumptions are not so
tightly integrated with the formulation.

"""
from .helpers import ClearingType, curve, aggregate_bid


# Class definition
class simple_auction:
    """This class implements a simplified version of the double-auction market embedded in GridLAB-D.

    References:
        `Market Module Overview - Auction <http://gridlab-d.shoutwiki.com/wiki/Market_Auction>`_

    Args:
        diction (diction): a row from the agent configuration JSON file
        key (str): the name of this agent, which is the market key from the agent configuration JSON file

    Attributes:
        name (str): the name of this auction, also the market key from the configuration JSON file
        std_dev (float): the historical standard deviation of the price, in $/kwh, from diction
        mean (float): the historical mean price in $/kwh, from diction
        price_cap (float): the maximum allowed market clearing price, in $/kwh, from diction
        max_capacity_reference_bid_quantity (float): this market's maximum capacity, likely defined by a physical limitation in the circuit(s) being managed.
        statistic_mode (int): always 1, not used, from diction
        stat_mode (str): always ST_CURR, not used, from diction
        stat_interval (str): always 86400 seconds, for one day, not used, from diction
        stat_type (str): always mean and standard deviation, not used, from diction
        stat_value (str): always zero, not used, from diction
        curve_buyer (curve): data structure to accumulate buyer bids
        curve_seller (curve): data structure to accumulate seller bids
        refload (float): the latest substation load from GridLAB-D. This is initially assumed to be all unresponsive and using the load state parameter when adding demand bids (which are generally price_responsive) all loads that bid and are on are removed from the assumed unresponsive load value
        lmp (float): the latest locational marginal price from the bulk system market
        unresp (float): unresponsive load, i.e., total substation load less the bidding, running HVACs
        agg_unresp (float): aggregated unresponsive load, i.e., total substation load less the bidding, running HVACs
        agg_resp_max (float): total load of the bidding HVACs
        agg_deg (int): degree of the aggregate bid curve polynomial, should be 0 (zero or one bids), 1 (2 bids) or 2 (more bids)
        agg_c2 (float): second-order coefficient of the aggregate bid curve
        agg_c1 (float): first-order coefficient of the aggregate bid curve
        clearing_type (helpers.ClearingType): describes the solution type or boundary case for the latest market clearing
        clearing_quantity (float): quantity at the last market clearing
        clearing_price (float): price at the last market clearing
        marginal_quantity (float): quantity of a partially accepted bid
        marginal_frac (float): fraction of the bid quantity accepted from a marginal buyer or seller 
        clearing_scalar (float): used for interpolation at boundary cases, always 0.5
    """

    # ====================Define instance variables ===================================
    def __init__(self, diction, key):
        self.name = key
        self.std_dev = float(diction['init_stdev'])
        self.mean = float(diction['init_price'])
        self.period = float(diction['period'])
        self.price_cap = float(diction['pricecap'])
        self.max_capacity_reference_bid_quantity = float(diction['max_capacity_reference_bid_quantity'])
        self.statistic_mode = int(diction['statistic_mode'])
        self.stat_mode = diction['stat_mode']
        self.stat_interval = diction['stat_interval']
        self.stat_type = diction['stat_type']
        self.stat_value = diction['stat_value']

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

        self.clearing_scalar = 0.5

        self.consumerSurplus = 0.0
        self.averageConsumerSurplus = 0.0
        self.supplierSurplus = 0.0
        self.unrespSupplierSurplus = 0.0

        self.bid_offset = 1e-4  # for numerical checks
        self.unresponsive_sell = self.responsive_sell = self.unresponsive_buy = self.responsive_buy = 0

    def set_refload(self, kw):
        """Sets the refload attribute

        Args:
            kw (float): GridLAB-D substation load in kw
        """
        self.refload = kw

    def set_lmp(self, lmp):
        """Sets the lmp attribute

        Args:
            lmp (float): locational marginal price from the bulk system market
        """
        self.lmp = lmp

    def initAuction(self):
        """Sets the clearing_price and lmp to the mean price

        2021-10-29 TDH: TODO - Any reason we can't put this in constructor?
        """
        self.clearing_price = self.lmp = self.mean

    def update_statistics(self):
        """Update price history statistics - not implemented
        """
        sample_need = 0

    def clear_bids(self):
        """Re-initializes curve_buyer and curve_seller, sets the unresponsive load estimate to the total substation load.
        """
        self.curve_buyer = curve()
        self.curve_seller = curve()
        self.unresp = self.refload

    def supplier_bid(self, bid):
        """Gather supplier bids into curve_seller

        Use this to enter curves in step-wise blocks.

        Args:
            bid ([float, float]): price in $/kwh, quantity in kW
        """
        price = bid[0]
        quantity = bid[1]
        self.curve_seller.add_to_curve(price, quantity, False)

    def collect_bid(self, bid):
        """Gather HVAC bids into curve_buyer

        Also adjusts the unresponsive load estimate, by subtracting the HVAC power
        if the HVAC is on.

        Args:
            bid ([float, float, Boolean]): price in $/kwh, quantity in kW and the HVAC on state
        """
        price = bid[0]
        quantity = bid[1]
        is_on = bid[2]
        if is_on:
            self.unresp -= quantity
        if price > 0.0:
            self.curve_buyer.add_to_curve(price, quantity, is_on)

    def add_unresponsive_load(self, quantity):
        self.unresp += quantity

    def aggregate_bids(self):
        """Aggregates the unresponsive load and responsive load bids for submission to the bulk system market
        """
        if self.unresp > 0:
            self.curve_buyer.add_to_curve(self.price_cap, self.unresp, True)
        else:
            print('$$ flag,Unresp,BuyCount,BuyTotal,BuyOn,BuyOff', flush=True)
            print('$$ unresp < 0',
                  '{:.3f}'.format(self.unresp),
                  self.curve_buyer.count,
                  '{:.3f}'.format(self.curve_buyer.total),
                  '{:.3f}'.format(self.curve_buyer.total_on),
                  '{:.3f}'.format(self.curve_buyer.total_off),
                  sep=',', flush=True)
        if self.curve_buyer.count > 0:
            self.curve_buyer.set_curve_order('descending')
        self.agg_unresp, self.agg_resp_max, self.agg_deg, self.agg_c2, self.agg_c1 = aggregate_bid(self.curve_buyer)

    def clear_market(self, tnext_clear=0, time_granted=0):
        """Solves for the market clearing price and quantity

        Uses the current contents of curve_seller and curve_buyer.
        Updates clearing_price, clearing_quantity, clearing_type,
        marginal_quantity and marginal_frac.

        Args:
            tnext_clear (int): next clearing time in seconds, should be <= time_granted, for the log file only
            time_granted (int): the current time in seconds, for the log file only
        """

        if self.max_capacity_reference_bid_quantity > 0:
            self.curve_seller.add_to_curve(self.lmp, self.max_capacity_reference_bid_quantity, True)
        if self.curve_seller.count > 0:
            self.curve_seller.set_curve_order('ascending')

        self.unresponsive_sell = self.responsive_sell = self.unresponsive_buy = self.responsive_buy = 0

        if self.curve_buyer.count > 0 and self.curve_seller.count > 0:
            a = self.price_cap
            b = -self.price_cap
            check = 0
            demand_quantity = supply_quantity = 0
            for i in range(self.curve_seller.count):
                if self.curve_seller.price[i] == self.price_cap:
                    self.unresponsive_sell += self.curve_seller.quantity[i]
                else:
                    self.responsive_sell += self.curve_seller.quantity[i]
            for i in range(self.curve_buyer.count):
                if self.curve_buyer.price[i] == self.price_cap:
                    self.unresponsive_buy += self.curve_buyer.quantity[i]
                else:
                    self.responsive_buy += self.curve_buyer.quantity[i]
            # Calculate clearing quantity and price here
            # Define the section number of the buyer and the seller curves respectively as i and j
            i = j = 0
            self.clearing_type = ClearingType.NULL
            self.clearing_quantity = self.clearing_price = 0
            while i < self.curve_buyer.count and j < self.curve_seller.count and \
                    self.curve_buyer.price[i] >= self.curve_seller.price[j]:
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
                # No side exhausted
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
                        self.clearing_price = b  # use seller's price, not buyer's price
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
                    avg = (a + b) / 2.0
                    # Calculating clearing price limits:   
                    dHigh = a if i == self.curve_buyer.count else self.curve_buyer.price[i]
                    dLow = b if j == self.curve_seller.count else self.curve_seller.price[j]
                    # Needs to be just off such that it does not trigger any other bids
                    if a == self.price_cap and b != -self.price_cap:
                        if self.curve_buyer.price[i] > b:
                            self.clearing_price = self.curve_buyer.price[i] + self.bid_offset
                        else:
                            self.clearing_price = b
                    elif a != self.price_cap and b == -self.price_cap:
                        if self.curve_seller.price[j] < a:
                            self.clearing_price = self.curve_seller.price[j] - self.bid_offset
                        else:
                            self.clearing_price = a
                    elif a == self.price_cap and b == -self.price_cap:
                        if i == self.curve_buyer.count and j == self.curve_seller.count:
                            self.clearing_price = 0  # no additional bids on either side
                        elif j == self.curve_seller.count:  # buyers left
                            self.clearing_price = self.curve_buyer.price[i] + self.bid_offset
                        elif i == self.curve_buyer.count:  # sellers left
                            self.clearing_price = self.curve_seller.price[j] - self.bid_offset
                        else:  # additional bids on both sides, just no clearing
                            self.clearing_price = (dHigh + dLow) / 2
                    else:
                        if i != self.curve_buyer.count and self.curve_buyer.price[i] == a:
                            self.clearing_price = a
                        elif j != self.curve_seller.count and self.curve_seller.price[j] == b:
                            self.clearing_price = b
                        elif i != self.curve_buyer.count and avg < self.curve_buyer.price[i]:
                            self.clearing_price = dHigh + self.bid_offset
                        elif j != self.curve_seller.count and avg > self.curve_seller.price[j]:
                            self.clearing_price = dLow - self.bid_offset
                        else:
                            self.clearing_price = avg

                            # Check for zero demand but non-zero first unit sell price
            if self.clearing_quantity == 0:
                self.clearing_type = ClearingType.NULL
                if self.curve_seller.count > 0 and self.curve_buyer.count == 0:
                    self.clearing_price = self.curve_seller.price[0] - self.bid_offset
                elif self.curve_seller.count == 0 and self.curve_buyer.count > 0:
                    self.clearing_price = self.curve_buyer.price[0] + self.bid_offset
                else:
                    if self.curve_seller.price[0] == self.price_cap:
                        self.clearing_price = self.curve_buyer.price[0] + self.bid_offset
                    elif self.curve_seller.price[0] == -self.price_cap:
                        self.clearing_price = self.curve_seller.price[0] - self.bid_offset
                    else:
                        self.clearing_price = self.curve_seller.price[0] + (
                                self.curve_buyer.price[0] - self.curve_seller.price[0]) * self.clearing_scalar

            elif self.clearing_quantity < self.unresponsive_buy:
                self.clearing_type = ClearingType.FAILURE
                self.clearing_price = self.price_cap

            elif self.clearing_quantity < self.unresponsive_sell:
                self.clearing_type = ClearingType.FAILURE
                self.clearing_price = -self.price_cap

            elif self.clearing_quantity == self.unresponsive_buy and self.clearing_quantity == self.unresponsive_sell:
                # only cleared unresponsive loads
                self.clearing_type = ClearingType.PRICE
                self.clearing_price = 0.0

        # If the market mode MD_NONE and at least one side is not given
        else:
            if self.curve_seller.count > 0 and self.curve_buyer.count == 0:
                self.clearing_price = self.curve_seller.price[0] - self.bid_offset
            elif self.curve_seller.count == 0 and self.curve_buyer.count > 0:
                self.clearing_price = self.curve_buyer.price[0] + self.bid_offset
            elif self.curve_seller.count > 0 and self.curve_buyer.count > 0:
                self.clearing_price = self.curve_seller.price[0] + \
                                      (self.curve_buyer.price[0] - self.curve_seller.price[0]) * self.clearing_scalar
            elif self.curve_seller.count == 0 and self.curve_buyer.count == 0:
                self.clearing_price = 0.0
            self.clearing_quantity = 0
            self.clearing_type = ClearingType.NULL
            if self.curve_seller.count == 0:
                print('  Market %s fails to clear due to missing seller' % self.name, flush=True)
            elif self.curve_buyer.count == 0:
                print('  Market %s fails to clear due to missing buyer' % self.name, flush=True)

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
            self.marginal_quantity = self.clearing_quantity - marginal_subtotal
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
            self.marginal_quantity = self.clearing_quantity - marginal_subtotal
            for j in range(i, self.curve_seller.count):
                if self.curve_seller.price[i] == self.clearing_price:
                    marginal_total += self.curve_seller.quantity[i]
                else:
                    break
            if marginal_total > 0.0:
                self.marginal_frac = float(self.marginal_quantity) / marginal_total

        else:
            self.marginal_quantity = 0.0
            self.marginal_frac = 0.0
        # print ('##', time_granted, tnext_clear, self.clearing_type, self.clearing_quantity, 
        #        self.clearing_price,
        #        self.curve_buyer.count, self.unresponsive_buy, self.responsive_buy,
        #        self.curve_seller.count, self.unresponsive_sell, self.responsive_sell,
        #        self.marginal_quantity, self.marginal_frac, self.lmp, self.refload,
        #        self.consumerSurplus, self.averageConsumerSurplus, self.supplierSurplus,
        #        self.unrespSupplierSurplus, sep=',', flush=True)

    def surplusCalculation(self, tnext_clear=0, time_granted=0):
        """Calculates consumer surplus (and its average) and supplier surplus.

        This function goes through all the bids higher than clearing price from buyers to calculate consumer surplus,
        and also accumulates the quantities that will be cleared while doing so. Of the cleared quantities,
        the quantity for unresponsive loads are also collected. Then go through each seller to calculate supplier surplus.
        Part of the supplier surplus corresponds to unresponsive load are excluded and calculated separately.

        Args:
            tnext_clear (int): next clearing time in seconds, should be <= time_granted, for the log file only
            time_granted (int): the current time in seconds, for the log file only

        Returns:
            None
        """
        numberOfUnrespBuyerAboveClearingPrice = 0
        numberOfResponsiveBuyerAboveClearingPrice = 0
        self.supplierSurplus = 0.0
        self.averageConsumerSurplus = 0.0
        self.consumerSurplus = 0.0
        self.unrespSupplierSurplus = 0.0
        grantedRespQuantity = 0.0
        grantedUnrespQuantity = 0.0
        declinedQuantity = 0.0
        # assuming the buyers are ordered descending by price
        for i in range(self.curve_buyer.count):
            # if a buyer pays higher than clearing_price, the power is granted
            if self.curve_buyer.price[i] >= self.clearing_price:
                # unresponsive load, they pay infinite amount price, here it is set at self.price_cap
                if self.curve_buyer.price[i] == self.price_cap:
                    grantedUnrespQuantity += self.curve_buyer.quantity[i]
                    numberOfUnrespBuyerAboveClearingPrice += 1
                # responsive load, this is the part consumer surplus is calculated
                else:
                    grantedRespQuantity += self.curve_buyer.quantity[i]
                    numberOfResponsiveBuyerAboveClearingPrice += 1
                    self.consumerSurplus += \
                        (self.curve_buyer.price[i] - self.clearing_price) * self.curve_buyer.quantity[i]
            # if a buy pays lower than clearing_price, it does not get the quantity requested
            else:
                declinedQuantity += self.curve_buyer.quantity[i]
        if numberOfResponsiveBuyerAboveClearingPrice != 0:
            self.averageConsumerSurplus = self.consumerSurplus / numberOfResponsiveBuyerAboveClearingPrice
        # assuming the sellers are ordered ascending by their price
        for i in range(self.curve_seller.count):
            # if a seller has a wholesale price/base price lower than clearing_price, their power is used
            if self.curve_seller.price[i] <= self.clearing_price:
                # satisfy quantity requested by unresponsive load first since they pay infinite price
                # when the unresponsive load use up all power from the supplier
                if grantedUnrespQuantity >= self.curve_seller.quantity[i]:
                    self.unrespSupplierSurplus += (self.clearing_price - self.curve_seller.price[i]) * \
                                                  self.curve_seller.quantity[i]
                    grantedUnrespQuantity -= self.curve_seller.quantity[i]
                # when the unresponsive load use part of the power from the supplier
                elif grantedUnrespQuantity != 0.0:
                    self.unrespSupplierSurplus += (self.clearing_price - self.curve_seller.price[
                        i]) * grantedUnrespQuantity
                    leftOverQuantityFromSeller = self.curve_seller.quantity[i] - grantedUnrespQuantity
                    grantedUnrespQuantity = 0.0
                    # leftover quantity from this supplier will be used by responsive load
                    # when leftover quantity is used up by the responsive load
                    if grantedRespQuantity >= leftOverQuantityFromSeller:
                        self.supplierSurplus += (self.clearing_price - self.curve_seller.price[
                            i]) * leftOverQuantityFromSeller
                        grantedRespQuantity -= leftOverQuantityFromSeller
                    # when leftover quantity satisfies all the quantity the responsive load asked
                    else:
                        self.supplierSurplus += (self.clearing_price - self.curve_seller.price[i]) * grantedRespQuantity
                        grantedRespQuantity = 0.0
                        break
                # if the quantity requested by unresponsive load are satisfied, responsive load requests are considered
                # when supplier quantity is used up by the responsive load
                elif grantedRespQuantity >= self.curve_seller.quantity[i]:
                    self.supplierSurplus += (self.clearing_price - self.curve_seller.price[i]) * \
                                            self.curve_seller.quantity[i]
                    grantedRespQuantity -= self.curve_seller.quantity[i]
                # when supplier quantity satisfies all the quantity the responsive load requested
                else:
                    self.supplierSurplus += (self.clearing_price - self.curve_seller.price[i]) * grantedRespQuantity
                    grantedRespQuantity = 0.0
                    break
        if grantedRespQuantity != 0.0:
            print('cleared {:.4f} more quantity than supplied.'.format(grantedRespQuantity))
        print('##',
              time_granted,
              tnext_clear,
              self.clearing_type,
              '{:.3f}'.format(self.clearing_quantity),
              '{:.6f}'.format(self.clearing_price),
              self.curve_buyer.count,
              '{:.3f}'.format(self.unresponsive_buy),
              '{:.3f}'.format(self.responsive_buy),
              self.curve_seller.count,
              '{:.3f}'.format(self.unresponsive_sell),
              '{:.3f}'.format(self.responsive_sell),
              '{:.3f}'.format(self.marginal_quantity),
              '{:.6f}'.format(self.marginal_frac),
              '{:.6f}'.format(self.lmp),
              '{:.3f}'.format(self.refload),
              '{:.4f}'.format(self.consumerSurplus),
              '{:.4f}'.format(self.averageConsumerSurplus),
              '{:.4f}'.format(self.supplierSurplus),
              '{:.4f}'.format(self.unrespSupplierSurplus),
              sep=',', flush=True)


def _auto_run():
    """
    This method implements the basic functionalities offered by
    simple_auction and demonstrates a typical single-period market operation

    """
    # 2021-10-29 TDH: This is a subset of values from the
    #  "SGIP1b_agent_dict.json" "markets" object. Many of these are only
    #  used to initialize the simple_auction object but not used by any
    #  existing object methods. They may be market metadata that other
    #  entities need from it, so I won't delete them. The big ones that are
    #  used are 'clearing_scalar' and 'max_capacity_reference_bid_quantity'.
    market_name = 'test_market'
    market_config = {
        'unit': 'kW',
        'pricecap': 3.78,
        'period': 300,
        'clearing_scalar': 0.0,
        'init_price': 0.02078,
        'init_stdev': 0.01,
        'statistic_mode': 1,
        'max_capacity_reference_bid_quantity': 5000,
        'stat_mode': ['ST_CURR', 'ST_CURR'],
        'stat_interval': [84600, 84600],
        'stat_type': ['SY_MEAN', 'SY_STDEV'],
        'stat_value': [0, 0]
    }

    # 2021-10-29 TDH: More arbitrary values for testing/demonstration.
    wholesale_LMP = 3
    # 2021-10-29 TDH:
    refload = 1000
    # 2021-10-29 TDH: Bids take on the form [price, quantity, on_state] with
    #  units [$/kWh, kW, Boolean]
    #  I'll see once I fully implement this demonstration, but it feels to me
    #  that the auction object shouldn't need to know the state of the load
    #  bidding into the auction.
    #  These are retail demand bids
    dummy_buyers = [
        [3, 1, True],
        [2.98, 1, False],
        [2.8, 1, True],
        [2.75, 10, False],
        [2.5, 5, True],
        [2.4, 1, False],
        [2.1, 15, True],
        [2.0, 5, False],
        [1.9, 20, True],
        [1.8, 15, False],
        [1.75, 25, True],
        [1.7, 5, False],
        [1.5, 25, True],
        [1.4, 30, False],
        [1.3, 40, True],
        [1.1, 50, False],
        [1.0, 30, True],
        [0.95, 80, False],
        [0.9, 50, True],
        [0.70, 100, False],
        [0.6, 120, True],
        [0.5, 80, False],
        [0.4, 90, True],
        [0.3, 100, False],
        [0.2, 150, True],
        [0.1, 300, False]
    ]

    # 2021-10-29 TDH: For testing/demonstration purposes, we have to create
    #  dummy sellers so the market can operate. Bids are formatted
    #       [float price ($/kWh), float quantity (kW)]
    #  These are retail supply bids.
    dummy_sellers = [
        [0.1, 1],
        [0.3, 5],
        [0.5, 10],
        [0.9, 20],
        [1, 10],
        [1.2, 20],
        [1.4, 10],
        [1.5, 15],
        [1.9, 20],
        [2, 90],
        [2.1, 80],
        [2.2, 40],
        [2.5, 110],
        [2.6, 150],
        [2.8, 120],
        [2.9, 200],
        [3, 250]
    ]

    ######## Demonstration simple double-auction implementation ########
    aucObj = simple_auction(market_config, market_name)
    aucObj.initAuction()
    # Set wholesale LMP passed into this retail market
    aucObj.set_lmp(wholesale_LMP)
    # Set current load value corresponding to this value. Used to split
    # the load in the market into price-responsive and price-unresponsive
    # which makes the process of curve-fitting to the demand curve more
    # accurate.
    aucObj.set_refload(refload)
    aucObj.clear_bids()  # That is erased any leftover bids from last period
    # As it is used now in TESP, each bid corresponds to a load, and they are
    # added to the auction one at a time.
    for bid in dummy_buyers:
        aucObj.collect_bid(bid)
    # Adding sellers can be omitted. clear_market() adds the
    # max_capacity_reference_bid_quantity at the self.lmp to the retail
    # market modeled here.
    for bid in dummy_sellers:
        aucObj.supplier_bid(bid)
    aucObj.aggregate_bids()
    aucObj.clear_market()  # runs market to produce clear price and quantity
    aucObj.surplusCalculation()  # Optional


if __name__ == '__main__':
    _auto_run()
