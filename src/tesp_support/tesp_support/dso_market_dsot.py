# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: dso_market_dsot.py
"""Class that manages the operation of DSO agent

Functionalities include: 
Aggregate demand bids from different substations; 
Wholesale no da trial clearing;
Conversion between wholesale price and retail price;   
Generate substation supply curves with and without consideration of the transformer degradation.

"""
import json
import logging as log
import math
from copy import deepcopy

import numpy as np

from .helpers import parse_kw
from .helpers_dsot import curve, get_intersect, ClearingType


class DSOMarketDSOT:
    """This agent manages the DSO operating

    Args:
        dso_dict:
        key:
        
    Attributes:
        name (str): name of the DSO agent
        price_cap (float): the maximum price that is allowed in the market, in $/kWh
        num_samples (int): the number of sampling points, describes how precisely the curve is sampled
        windowLength (int): length of the planning horizon for the DA market, in hours
        DSO_Q_max (float): maximum limit of the DSO load capacity, in kWh
        transformer_degradation (boolean): flag variable, equals to 1 when transformer degradation effect is taken into account
        curve_a (array): array of second order coefficients for the wholesale node curve, indexed by day_of_sim and hour_of_day
        curve_b (array): array of first order coefficients of the wholesale node curve, indexed by day_of_sim and hour_of_day
        curve_c (array): array of intercepts of the wholesale node curve, indexed by day_of_sim and hour_of_day
        Pwclear_RT (float): cleared wholesale price by real-time wholesale node trial clearing, in $/kWh
        Pwclear_DA (list): list of cleared wholesale price by day-ahead wholesale node trial clearing, in $/kWh, indexed by hour
        trial_cleared_quantity_RT (float): trial cleared quantity by real-time wholesale node trial clearing, in kWh
        trial_cleared_quantity_DA (list): trial cleared quantity by day-ahead wholesale node trial clearing, in kWh
        curve_DSO_RT (curve): aggregated demand curve at DSO level from real-time retail market
        curve_DSO_DA (dict): dictionary of aggregated demand curves at DSO level from day-ahead retail market, indexed by hour
        curve_ws_node (dict): dictionary of wholesale node curves, indexed by day_of_sim and hour_of_day
        trial_clear_type_RT (int): trial cleared type of real-time wholesale node trial clearing
        trial_clear_type_DA (list): trial cleared type of day-ahead wholesale node trial clearing, indexed by hour
        hour_of_day (int): current hour of the day
        day_of_week (int): current day of the week
        customer_count_mix_residential: Residential percentage of the total customer count mix
        number_of_gld_homes: Total number of GLD homes for the DSO
    """

    def __init__(self, dso_dict, key):
        """ Initializes the class
        """
        self.name = key
        self.DSO_Q_max = dso_dict['DSO_Q_max']
        Q_max_scale = (70.0e6 / self.DSO_Q_max)

        # if true use quadratic curve dictionary, false use hard code
        quadratic = dso_dict['quadratic']
        if quadratic:
            try:
                self.curve_a = np.asarray(dso_dict['curve_a'])  # * Q_max_scale * Q_max_scale
                self.curve_b = np.asarray(dso_dict['curve_b'])  # * Q_max_scale
                self.curve_c = np.asarray(dso_dict['curve_c'])
            except:
                quadratic = False

        if not quadratic:
            # wholesale node curve coefficients obtained from ERCOT 2016 Price and Load data
            curve_c_weekday = np.full((5, 24), 0.024)
            curve_b_weekday = np.full((5, 24), -4.94365 * 1e-10 * Q_max_scale)
            curve_a_weekday = np.full((5, 24), 1.68315 * 1e-17 * Q_max_scale * Q_max_scale)
            curve_c_weekend = np.full((2, 24), 0.024)
            curve_b_weekend = np.full((2, 24), -3.994630 * 1e-10 * Q_max_scale)
            curve_a_weekend = np.full((2, 24), 1.67717 * 1e-17 * Q_max_scale * Q_max_scale)
            self.curve_a = np.concatenate((curve_a_weekday, curve_a_weekend), axis=0)
            self.curve_b = np.concatenate((curve_b_weekday, curve_b_weekend), axis=0)
            self.curve_c = np.concatenate((curve_c_weekday, curve_c_weekend), axis=0)
            print('Utilizing hard coded quadratic curves')
        # old coefficients
        # self.curve_a = np.full((7, 24), 0.00000007)  # 0.0000003 for v1
        # self.curve_b = np.full((7, 24), 0.00002)    # 0.000002 for v1
        # self.curve_c = np.full((7, 24), 0.0)

        # ------for agent-slim case (DSO_2: Qmax=3600)----------
        # --- uncomment line 60-63 and comment 66-68
        # self.curve_a = np.full((7, 24), 0.00000007)  # 0.0000003 for v1
        # self.curve_b = np.full((7, 24), 0.00002)    # 0.000002 for v1
        # self.curve_c = np.full((7, 24), 0.0)

        # #-------for revised-slim case (DSO_3: Qmax= 12000)-----------
        # #--- uncomment line 66-68 and comment line 60-63
        # self.curve_a = np.full((7, 24), 6.9) * 1e-9
        # self.curve_b = np.full((7, 24), 2) * 1e-10
        # self.curve_c = np.full((7, 24), 0.0)

        # Loading the dso agent configuration
        self.windowLength = dso_dict['windowLength']
        self.price_cap = dso_dict['pricecap']
        self.num_samples = dso_dict['num_samples']
        self.DSO_Q_max = dso_dict['DSO_Q_max']
        self.transformer_degradation = dso_dict['transformer_degradation']
        self.Pwclear_RT = 0.0
        self.Pwclear_DA = [0.0] * self.windowLength
        self.trial_cleared_quantity_RT = 0.0
        self.trial_cleared_quantity_DA = [0.0] * self.windowLength
        self.lmp_rt = None
        self.lmp_da = None
        self.ref_load_da = None
        self.ind_load = None
        self.ind_load_da = None
        self.cleared_q_da = [0.0] * self.windowLength
        self.cleared_q_rt = 0.0
        self.curve_DSO_RT = None
        self.curve_DSO_DA = dict()
        self.curve_ws_node = dict()
        self.trial_clear_type_RT = None
        self.trial_clear_type_DA = [None] * self.windowLength
        self.default_lmp = 0.0
        self.distribution_charge_rate = dso_dict['distribution_charge_rate']
        self.scale = dso_dict['dso_retail_scaling']
        self.dollarsPerKW = None

        self.hour_of_day = 0
        self.day_of_week = 0

        self.total_load = 0
        self.Feqa_T = [0.0]

        self.num_of_customers = dso_dict['number_of_customers']
        self.customer_count_mix_residential = dso_dict['RCI_customer_count_mix']['residential']
        self.number_of_gld_homes = dso_dict['number_of_gld_homes']

        self.last_unresponsive_load = 0.0
        self.last_bid_c2 = 0.0
        self.last_bid_c1 = 0.0
        self.last_bid_c0 = 0.0

    def update_wholesale_node_curve(self):
        """ Update the wholesale node curves according to the most updated curve coefficients, 
        may be updated every day

        """
        # Update the wholesale node curves according to the most updated curve coefficients
        for day in range(7):
            self.curve_ws_node[day] = dict()
            for hour in range(24):
                self.curve_ws_node[day][hour] = curve(self.price_cap, self.num_samples)
                self.curve_ws_node[day][hour].quantities = np.linspace(0, self.DSO_Q_max, self.num_samples)
                self.curve_ws_node[day][hour].prices = \
                    np.array(
                        [self.curve_a[day][hour] * quantity * quantity +
                         self.curve_b[day][hour] * quantity + self.curve_c[day][hour]
                         for quantity in self.curve_ws_node[day][hour].quantities.tolist()]
                    )

    def clean_bids_RT(self):
        """ Initialize the real-time wholesale node trial clearing
        """
        self.Pwclear_RT = 0.0
        self.trial_cleared_quantity_RT = 0.0
        self.curve_DSO_RT = None
        self.trial_clear_type_RT = None
        self.curve_DSO_RT = curve(self.price_cap, self.num_samples)

    def clean_bids_DA(self):
        """ Initialize the day-ahead wholesale node trial clearing
        """
        self.Pwclear_DA = [0.0] * self.windowLength
        self.trial_cleared_quantity_DA = [0.0] * self.windowLength
        self.curve_DSO_DA = dict()
        self.trial_clear_type_DA = [None] * self.windowLength
        for idx in range(self.windowLength):
            self.curve_DSO_DA[idx] = curve(self.price_cap, self.num_samples)

    def curve_aggregator_DSO_RT(self, demand_curve_RT, Q_max):
        """ Function used to aggregate the substation-level RT demand curves into a DSO-level RT demand curve

        Args:
            demand_curve_RT (curve): demand curve to be aggregated for real-time
            Q_max (float): maximum capacity of the substation, in kW

        """
        if max(demand_curve_RT.quantities) > Q_max:
            print("Demand Curve range exceeds beyond Q_max, " +
                  "changing the LMP forecaster's Q_max to reflect that and extending the supply curve")
            self.DSO_Q_max = max(demand_curve_RT.quantities)
            self.update_wholesale_node_curve()
        substation_curve = deepcopy(self.curve_preprocess(demand_curve_RT, self.DSO_Q_max))
        self.curve_DSO_RT.curve_aggregator_DSO(substation_curve)
        self.curve_DSO_RT.update_price_caps()

    def curve_aggregator_DSO_DA(self, demand_curve_DA, Q_max):
        """ Function used to aggregate the substation-level DA demand curves into a DSO-level DA demand curve

        Args:
            demand_curve_DA (dict): a collection of demand curves to be aggregated for day-ahead
            Q_max (float): maximum capacity of the substation, in kW

        """
        for idx in range(self.windowLength):
            if max(demand_curve_DA[idx].quantities) > Q_max:
                if max(demand_curve_DA[idx].quantities) > self.DSO_Q_max:
                    print("Hour " + str(idx) +
                          " Demand Curve range exceeds beyond Q_max," +
                          " changing the LMP forecaster's Q_max to reflect that and extending the supply curve")
                    self.DSO_Q_max = max(demand_curve_DA[idx].quantities)
                    self.update_wholesale_node_curve()
            substation_curve = deepcopy(self.curve_preprocess(demand_curve_DA[idx], self.DSO_Q_max))
            self.curve_DSO_DA[idx].curve_aggregator_DSO(substation_curve)
            self.curve_DSO_DA[idx].update_price_caps()

    def curve_preprocess(self, substation_demand_curve, Q_max):
        """ An internal shared function called by curve_aggregator_DSO_RT and curve_aggregator_DSO_DA functions to truncate
            the substation demand curve before aggregation as well as convert the retail prices into wholesale prices

        Args:
            substation_demand_curve (curve): substation demand curve to be preprocessed
            Q_max (float): maximum capacity of the substation, in kW

        Return:
            preprocessed_curve (curve): preprocessed demand curve

        """
        preprocessed_curve = curve(self.price_cap, self.num_samples)
        preprocessed_curve.prices = deepcopy(substation_demand_curve.prices)
        preprocessed_curve.quantities = deepcopy(substation_demand_curve.quantities)
        for i in range(self.num_samples):
            # Truncate the substation-level demand curve by maximum capacity of the substation
            if preprocessed_curve.quantities[i] >= Q_max:
                preprocessed_curve.quantities[i] = Q_max
            # Convert the retail price into wholesale price
            preprocessed_curve.prices[i] = self.retail_rate_inverse(preprocessed_curve.prices[i])
        return preprocessed_curve

    def retail_rate(self, Pw):
        """ Function used to convert the wholesale prices into retail prices

        Args:
            Pw (float): wholesale price, in $/kWh

        Return:
            Pr (float): retail price, in $/kWh
        """
        Pr = deepcopy(Pw * self.scale + self.distribution_charge_rate)
        return Pr

    def retail_rate_inverse(self, Pr):
        """ Function used to convert the retail prices into wholesale prices

        Args:
            Pr (float): retail price, in $/kWh

        Return:
            Pw (float): wholesale price, in $/kWh
        """
        Pw = deepcopy((Pr - self.distribution_charge_rate) / self.scale)
        return Pw

    def set_Pwclear_RT(self, hour_of_day, day_of_week, lmp=False):
        """ Function used to implement the RT trial wholesale node clearing and update the Pwclear_RT value

        Args:
            hour_of_day (int): current hour of the day
            day_of_week (int): current day of the week
            lmp:
        """
        if lmp is False:
            self.Pwclear_RT, self.trial_cleared_quantity_RT, self.trial_clear_type_RT = \
                self.trial_wholesale_clearing(self.curve_ws_node[day_of_week][hour_of_day], 
                                              self.curve_DSO_RT, day_of_week, hour_of_day)
            self.default_lmp = self.Pwclear_RT
        else:
            try:
                # flex_cleared = 0.0
                # check to see if the bids were accepted or not, very small LMPs mean the market didn't converge
                # if (self.last_bid_c1 > self.lmp_rt[0]) and (self.lmp_rt[0] > 1e-3):
                #     flex_cleared = 0.5*(self.last_bid_c1-self.lmp_rt[0])/(self.last_bid_c2)
                #     self.trial_cleared_quantity_RT = self.last_unresponsive_load*1e3 + flex_cleared*1e3
                # else:
                #     self.trial_cleared_quantity_RT = self.active_power_rt

                self.trial_cleared_quantity_RT = self.active_power_rt

                self.Pwclear_RT = \
                    self.curve_a[day_of_week][hour_of_day] * self.trial_cleared_quantity_RT * \
                    self.trial_cleared_quantity_RT + self.curve_b[day_of_week][hour_of_day] * \
                    self.trial_cleared_quantity_RT + self.curve_c[day_of_week][hour_of_day]

                if self.trial_cleared_quantity_RT > self.DSO_Q_max:
                    self.trial_clear_type_RT = ClearingType.CONGESTED
                else:
                    self.trial_clear_type_RT = ClearingType.UNCONGESTED
            except:
                self.Pwclear_RT, self.trial_cleared_quantity_RT, self.trial_clear_type_RT = \
                    self.trial_wholesale_clearing(self.curve_ws_node[day_of_week][hour_of_day],
                                                  self.curve_DSO_RT, day_of_week, hour_of_day)
                self.default_lmp = self.Pwclear_RT

    def set_Pwclear_DA(self, hour_of_day, day_of_week):
        """ Function used to implement the DA trial wholesale node clearing and update the Pwclear_DA value

        Args:
            hour_of_day (int): current hour of the day
            day_of_week (int): current day of the week
        """
        for idx in range(self.windowLength):
            day = (day_of_week + (idx + hour_of_day) // 24) % 7
            hour = (hour_of_day + idx) % 24
            self.Pwclear_DA[idx], self.trial_cleared_quantity_DA[idx], self.trial_clear_type_DA[
                idx] = self.trial_wholesale_clearing(self.curve_ws_node[day][hour], self.curve_DSO_DA[idx], day, hour)

    def get_prices_of_quantities(self, Q, day, hour):
        """ Returns the prices DSO quadratic curve cost for a list of quantities

        Args:
            Q (list of float): quantities
            day (int): day of the week
            hour (int): hour of the day

        Return:
            P (list of float): prices for the quantities
        """
        P = [self.curve_a[day][hour] * quantity * quantity +
             self.curve_b[day][hour] * quantity + self.curve_c[day][hour]
             for quantity in Q]
        return P

    def trial_wholesale_clearing(self, curve_ws_node, curve_DSO, day, hour):
        """ An internal shared function called by set_Pwclear_RT and 
        set_Pwclear_DA functions to implement the trial wholesale node clearing

        Args:
            curve_ws_node (curve): wholesale node curve
            curve_DSO (curve): aggregated demand curve at DSO level
            day: 
            hour: 

        Return:
            Pwclear (float): cleared price, in $/kWh
            cleared_quantity(float): cleared quantity, in kWh
            trial_clear_type (int): clear type
        """

        if curve_DSO.uncontrollable_only:
            temp = curve_DSO.quantities[0]
            if temp < 0.0:
                log.info("Warning quantities submitted to DSO are negative. " +
                         "The returns are price set to 0, first quantity of the curve," +
                         "and ClearingType.UNCONGESTED. BAU case.")
                return 0.0, temp, ClearingType.UNCONGESTED
            if min(curve_ws_node.quantities) <= temp <= max(curve_ws_node.quantities):
                cleared_quantity = temp
                for idx in range(1, self.num_samples):
                    if curve_ws_node.quantities[idx - 1] < cleared_quantity < curve_ws_node.quantities[idx]:
                        cleared_price = curve_ws_node.prices[idx - 1] + (
                                cleared_quantity - curve_ws_node.quantities[idx - 1]) * (
                                                curve_ws_node.prices[idx] - curve_ws_node.prices[idx - 1]) / (
                                                curve_ws_node.quantities[idx] - curve_ws_node.quantities[idx - 1])
                    elif curve_ws_node.quantities[idx - 1] == cleared_quantity:
                        cleared_price = curve_ws_node.prices[idx - 1]
                    elif curve_ws_node.quantities[idx] == cleared_quantity:
                        cleared_price = curve_ws_node.prices[idx]
                clear_type = ClearingType.UNCONGESTED
                if cleared_price > self.price_cap:
                    cleared_price = self.price_cap
                return cleared_price, cleared_quantity, clear_type
            else:
                log.info("dso quantities: curve_ws_node" + str(curve_ws_node.quantities))
                log.info("ERROR dso min: " + str(min(curve_ws_node.quantities)) + ", max: " +
                         str(max(curve_ws_node.quantities)) + " curve_DSO.quantities[0] " +
                         str(curve_DSO.quantities[0]))
                log.info("dso quantities: curve_DSO" + str(curve_DSO.quantities))
                return float('inf'), float('inf'), ClearingType.FAILURE
        else:

            max_q = min(max(curve_ws_node.quantities), max(curve_DSO.quantities))
            min_q = max(min(curve_ws_node.quantities), min(curve_DSO.quantities))
            if max_q <= min_q:
                log.info("ERROR dso min: " + str(min_q) + ", max: " + str(max_q))
                return float('inf'), float('inf'), ClearingType.FAILURE

            # x, buyer_prices, seller_prices = \
            #     resample_curve_for_market(curve_DSO.quantities, curve_DSO.prices,
            #                               curve_ws_node.quantities, curve_ws_node.prices)
            buyer_prices = curve_DSO.prices
            buyer_quantities = curve_DSO.quantities
            seller_quantities = buyer_quantities
            seller_prices = self.get_prices_of_quantities(buyer_quantities, day, hour)
            # seller_prices[0]=0.0
            seller_prices[-1] = self.price_cap
            # buyer_quantities, buyer_prices = resample_curve(curve_DSO.quantities, curve_DSO.prices,
            #                                                 min_q, max_q, self.num_samples)
            # seller_quantities, seller_prices = resample_curve(curve_ws_node.quantities, curve_ws_node.prices,
            #                                                   min_q, max_q, self.num_samples)
            for idx in range(len(buyer_quantities) - 1):
                if buyer_prices[idx] > seller_prices[idx] and buyer_prices[idx + 1] < seller_prices[idx + 1]:
                    idx_old = idx
                    index_delta = 1
                    if idx < self.num_samples and buyer_quantities[idx] == buyer_quantities[idx + index_delta]:
                        p1 = (buyer_quantities[idx], buyer_prices[idx])
                        p2 = (buyer_quantities[idx + index_delta], buyer_prices[idx + index_delta])
                        quantity_point = [buyer_quantities[idx] - 0.1, buyer_quantities[idx] + 0.1]
                        price_point = self.get_prices_of_quantities(quantity_point, day, hour)
                        p3 = (quantity_point[0], price_point[0])
                        p4 = (quantity_point[1], price_point[1])
                        Pwclear, cleared_quantity = get_intersect(p1, p2, p3, p4)
                    else:
                        p1 = (buyer_quantities[idx], buyer_prices[idx])
                        p2 = (buyer_quantities[idx + index_delta], buyer_prices[idx + index_delta])
                        p3 = (seller_quantities[idx], seller_prices[idx])
                        p4 = (seller_quantities[idx + index_delta], seller_prices[idx + index_delta])
                        Pwclear, cleared_quantity = get_intersect(p1, p2, p3, p4)
                    if Pwclear == float('inf'):
                        # if buyer_quantities[idx] == buyer_quantities[idx + index_delta]:
                        log.info(" Warning dso clearing problem points -- buyer_quantities[idx]: " + str(
                            buyer_quantities[idx]) +
                                 " buyer_quantities[idx + index_delta]: " + str(buyer_quantities[idx + index_delta]))
                        log.info(" Warning dso clearing problem points -- buyer_quantities: " + str(buyer_quantities) +
                                 " buyer_prices : " + str(buyer_prices) + " seller_prices: " + str(seller_prices) +
                                 " day: " + str(day) + " hour: " + str(hour))
                        for i in range(idx_old):
                            if buyer_quantities[idx] == buyer_quantities[idx + index_delta]:
                                idx = idx - 1
                                index_delta = index_delta + 1
                            else:
                                break  # break here
                            if i == idx_old - 1:
                                log.info(
                                    " Error dso clearing problem points -- buyer_quantities: " + str(buyer_quantities) +
                                    " buyer_prices : " + str(buyer_prices) + " seller_prices: " + str(seller_prices) +
                                    " day: " + str(day) + " hour: " + str(hour))
                        p1 = (buyer_quantities[idx], buyer_prices[idx])
                        p2 = (buyer_quantities[idx + index_delta], buyer_prices[idx + index_delta])
                        p3 = (seller_quantities[idx], seller_prices[idx])
                        p4 = (seller_quantities[idx + index_delta], seller_prices[idx + index_delta])
                        Pwclear, cleared_quantity = get_intersect(p1, p2, p3, p4)
                    if Pwclear == float('inf'):
                        log.info(" Error dso no intersection: " + str(buyer_quantities) +
                                 " buyer_prices : " + str(buyer_prices) + " seller_prices: " + str(seller_prices) +
                                 " day: " + str(day) + " hour: " + str(hour))
                    if cleared_quantity > self.DSO_Q_max:
                        trial_clear_type = ClearingType.CONGESTED
                    else:
                        trial_clear_type = ClearingType.UNCONGESTED
                    return Pwclear, cleared_quantity, trial_clear_type
            log.info("ERROR dso intersection not found (not supposed to happen). quantities: " + str(
                buyer_quantities) + ", buyer_prices: " + str(buyer_prices) + ", seller_prices: " + str(seller_prices))
            if buyer_prices[0] > seller_prices[0]:
                if max_q == max(curve_ws_node.quantities):
                    Pwclear = buyer_prices[-1]
                    cleared_quantity = buyer_quantities[-1]
                    trial_clear_type = ClearingType.CONGESTED
                elif max_q == max(curve_DSO.quantities):
                    Pwclear = seller_prices[-1]
                    cleared_quantity = seller_quantities[-1]
                    trial_clear_type = ClearingType.UNCONGESTED
            else:
                if min_q == min(curve_ws_node.quantities):
                    Pwclear = buyer_prices[0]
                    cleared_quantity = buyer_quantities[0]
                    trial_clear_type = ClearingType.UNCONGESTED
                elif min_q == min(curve_DSO.quantities):
                    Pwclear = seller_prices[0]
                    cleared_quantity = seller_quantities[0]
                    trial_clear_type = ClearingType.UNCONGESTED
            return Pwclear, cleared_quantity, trial_clear_type

    def substation_supply_curve_RT(self, retail_obj):
        """ Function used to generate the RT supply curve for each substation

        Args:

        Variables:
            FeederCongPrice (float): feeder congestion price, in $/kWh
            FeederPkDemandPrice (float): feeder peak demand price, in $/kWh
            FeederCongCapacity (float): feeder congestion capacity, in kWh
            FeederPkDemandCapacity (float): feeder peak demand, in kWh
            Q_max (float): substation limit, in kWh
            maxPuLoading (float): maximum pu loading factor
            TOC_dict (dict): configuration parameters for transformer

        Return:
            supply_curve_RT (curve): substation supply curve for real-time market clearing
        """

        FeederCongCapacity = retail_obj.FeederCongCapacity
        FeederPkDemandCapacity = retail_obj.FeederPkDemandCapacity
        Q_max_retail = retail_obj.Q_max
        Q_max_DSO = self.DSO_Q_max  # can change when the demand bid is higher than the original DSO limit
        maxPuLoading = retail_obj.maxPuLoading
        TOC_dict = retail_obj.TOC_dict
        Prclear_RT = self.retail_rate(self.Pwclear_RT)
        # price cap of the supply_curve has to be the retail price cap
        supply_curve_RT = curve(self.retail_rate(self.price_cap), self.num_samples)  
        max_buyer = retail_obj.curve_buyer_RT.quantities[0]
        max_retail = max(max_buyer, Q_max_retail)
        if self.transformer_degradation:
            supply_curve_RT.quantities, supply_curve_RT.prices = \
                self.supply_curve(Prclear_RT, FeederCongCapacity, FeederPkDemandCapacity,
                                  self.num_samples, Q_max_retail, maxPuLoading, TOC_dict)
        elif self.trial_cleared_quantity_RT > Q_max_retail:
            # the DSO's Q_max has been increased
            # after observing buyer bids to be higher than the substation Q max
            id_original_Q_max = int(Q_max_retail / (Q_max_DSO / self.num_samples))
            price_range_original_Q_max = np.array([Prclear_RT] * id_original_Q_max)
            range_congestion = self.num_samples - id_original_Q_max
            congestion_quantity = Q_max_DSO - Q_max_retail
            # placeholder for congestion surcharge
            price_max_congestion = congestion_quantity * retail_obj.FeederCongPrice
            price_range_congestion = np.linspace(Prclear_RT, Prclear_RT + price_max_congestion, range_congestion)
            price_range_congestion[price_range_congestion > self.price_cap] = self.price_cap
            supply_curve_RT.prices = np.concatenate((price_range_original_Q_max, price_range_congestion))
            supply_curve_RT.quantities = np.linspace(0, Q_max_DSO, self.num_samples)
        # if self.trial_cleared_quantity_RT > Q_max_DSO:
        #     id_original_Q_max = int(max_retail / (self.trial_cleared_quantity_RT / self.num_samples))
        #     price_range_original_Q_max = np.array([Prclear_RT] * id_original_Q_max)
        #     range_congestion = self.num_samples - id_original_Q_max
        #     congestion_quantity = self.trial_cleared_quantity_RT - max_retail
        #     # placeholder for congestion surcharge
        #     price_max_congestion = congestion_quantity * retail_obj.FeederCongPrice
        #     price_range_congestion = np.linspace(Prclear_RT, Prclear_RT + price_max_congestion, range_congestion)
        #     price_range_congestion[price_range_congestion > self.price_cap] = self.price_cap
        #     supply_curve_RT.prices = np.concatenate((price_range_original_Q_max, price_range_congestion))
        #     supply_curve_RT.quantities = np.linspace(0, self.trial_cleared_quantity_RT, self.num_samples)
        # elif self.trial_cleared_quantity_RT <= Q_max_DSO:
        #     id_original_Q_max = int(max_retail / (Q_max_DSO / self.num_samples))
        #     price_range_original_Q_max = np.array([Prclear_RT] * id_original_Q_max)
        #     range_congestion = self.num_samples - id_original_Q_max
        #     congestion_quantity = Q_max_DSO - max_retail
        #     # placeholder for congestion surcharge
        #     price_max_congestion = congestion_quantity * retail_obj.FeederCongPrice
        #     price_range_congestion = np.linspace(Prclear_RT, Prclear_RT + price_max_congestion, range_congestion)
        #     price_range_congestion[price_range_congestion > self.price_cap] = self.price_cap
        #     supply_curve_RT.prices = np.concatenate((price_range_original_Q_max, price_range_congestion))
        #     supply_curve_RT.quantities = np.linspace(0, Q_max_DSO, self.num_samples)
        else:
            # supply_curve_RT.quantities = np.linspace(0, max_retail, self.num_samples)
            supply_curve_RT.quantities = np.linspace(0, Q_max_DSO, self.num_samples)
            supply_curve_RT.prices = np.array([Prclear_RT] * self.num_samples)
        return supply_curve_RT

    def substation_supply_curve_DA(self, retail_obj):
        """ Function used to generate the DA supply curves for each substation

        Args:
            
        Variables:
            FeederCongPrice (float): feeder congestion price, in $/kWh
            FeederPkDemandPrice (float): feeder peak demand price, in $/kWh
            FeederCongCapacity (float): feeder congestion capacity, in kWh
            FeederPkDemandCapacity (float): feeder peak demand, in kWh
            Q_max (float): substation limit, in kWh
            maxPuLoading (float): maximum pu loading factor
            TOC_dict (dict): configuration parameters for transformer

        Return:
            supply_curve_DA (list): a collection of substation supply curves for day-ahead market clearing
        """
        FeederCongCapacity = retail_obj.FeederCongCapacity
        FeederPkDemandCapacity = retail_obj.FeederPkDemandCapacity
        Q_max_retail = retail_obj.Q_max
        # can change when the demand bid is higher than the original DSO limit
        Q_max_DSO = self.DSO_Q_max
        maxPuLoading = retail_obj.maxPuLoading
        TOC_dict = retail_obj.TOC_dict
        Prclear_DA = [0.0] * self.windowLength
        supply_curve_DA = dict()
        for idx in range(self.windowLength):
            Prclear_DA[idx] = self.retail_rate(self.Pwclear_DA[idx])
            # price cap of the supply_curve has to be the retail price cap
            supply_curve_DA[idx] = curve(self.retail_rate(self.price_cap), self.num_samples)

        if self.transformer_degradation:
            for idx in range(self.windowLength):
                supply_curve_DA[idx].quantities, supply_curve_DA[idx].prices = \
                    self.supply_curve(Prclear_DA[idx], FeederCongCapacity,
                                      FeederPkDemandCapacity, self.num_samples,
                                      Q_max_retail, maxPuLoading, TOC_dict)
        else:
            for idx in range(self.windowLength):
                if self.trial_cleared_quantity_DA[idx] > Q_max_retail:
                    # the DSO's Q_max has been increased 
                    # after observing buyer bids to be higher than the substation Q max
                    id_original_Q_max = int(Q_max_retail / (self.trial_cleared_quantity_DA[idx] / self.num_samples))
                    price_range_original_Q_max = np.array([Prclear_DA[idx]] * id_original_Q_max)
                    range_congestion = self.num_samples - id_original_Q_max
                    congestion_quantity = self.trial_cleared_quantity_DA[idx] - Q_max_retail
                    # placeholder for congestion surcharge
                    price_max_congestion = congestion_quantity * retail_obj.FeederCongPrice
                    price_range_congestion = np.linspace(Prclear_DA[idx], Prclear_DA[idx] + price_max_congestion,
                                                         range_congestion)
                    price_range_congestion[price_range_congestion > self.price_cap] = self.price_cap
                    supply_curve_DA[idx].prices = np.concatenate((price_range_original_Q_max, price_range_congestion))
                    supply_curve_DA[idx].quantities = np.linspace(0, self.trial_cleared_quantity_DA[idx],
                                                                  self.num_samples)
                else:
                    supply_curve_DA[idx].quantities = np.linspace(0, Q_max_retail, self.num_samples)
                    supply_curve_DA[idx].prices = np.array([Prclear_DA[idx]] * self.num_samples)
        return supply_curve_DA

    def supply_curve(self, Prclear, FeederCongCapacity, FeederPkDemandCapacity, num_samples, Q_max, maxPuLoading,
                     TOC_dict):
        """ An internal shared function called by substation_supply_curve_RT and substation_supply_curve_DA functions 
        to generate the supply curve when considering the transformer degradation

        Args:
            Prclear (float): retail price overted from wholesale price obtained from trial wholesale node clearing, in $/kWh
            FeederCongCapacity (float): feeder congestion capacity, in kWh
            FeederPkDemandCapacity (float): feeder peak demand, in kWh
            num_samples (int): number of sampling points
            Q_max (float): substation limit, in kWh
            maxPuLoading (float): maximum pu loading factor
            TOC_dict (dict): configuration parameters for transformer

        Variables:
            FeederCongPrice (float): feeder congestion price, in $/kWh
            FeederPkDemandPrice (float): feeder peak demand price, in $/kWh

        Return:
            SupplyQuantities (list): quantity sampling of the supply curve, in kWh
            SupplyPrices (list): prices sampling of the supply curve, in $/kWh
        """
        FeederCongPrice = Prclear
        FeederPkDemandPrice = Prclear
        SupplyQuantities = np.linspace(0, Q_max * maxPuLoading, num_samples)
        SupplyPrices = [0 for _ in range(0, num_samples)]
        for i in range(0, len(SupplyQuantities)):
            if FeederPkDemandCapacity <= FeederCongCapacity:
                if SupplyQuantities[i] < FeederPkDemandCapacity:
                    SupplyPrices[i] = Prclear
                elif (SupplyQuantities[i] > FeederPkDemandCapacity) and (SupplyQuantities[i] < FeederCongCapacity):
                    SupplyPrices[i] = FeederPkDemandPrice
                else:
                    SupplyPrices[i] = FeederCongPrice
            if FeederPkDemandCapacity > FeederCongCapacity:
                if SupplyQuantities[i] < FeederCongCapacity:
                    SupplyPrices[i] = Prclear
                else:
                    SupplyPrices[i] = FeederCongPrice

        dollars, pu_loading = self.generate_TOC(60, maxPuLoading, num_samples,
                                                TOC_dict)  # cost per 60 minutes (so kW is same as kWh)

        self.dollarsPerKW = [0 for _ in range(0, len(SupplyQuantities))]
        for i in range(0, len(pu_loading)):
            if pu_loading[i] != 0:
                self.dollarsPerKW[i] = dollars[i] / (pu_loading[i] * Q_max)

        for i in range(0, len(SupplyQuantities)):
            SupplyPrices[i] = SupplyPrices[i] + self.dollarsPerKW[i]

        return SupplyQuantities, SupplyPrices

    def generate_TOC(self, costInterval, maxPuLoad, num_samples, TOC_dict):
        """ Function used to calculate the total owning cost of transformer

        Args:
            costInterval (int): interval for calculating the cost, in minutes
            maxPuLoad (float): maximum pu loading factor
            num_samples (int): number of sampling points
            TOC_dict (dict): configuration parameters for transformer

        Return:
            DollarsForPlot (list): price axis of unit owning cost, in $/kWh
            LoadsForPlot (list): quantity axis of unit owing cost, in kWh
        """
        # Import TOC dictionary
        OperatingPeriod = TOC_dict['OperatingPeriod']
        timeStep = TOC_dict['timeStep']
        Tamb = TOC_dict['Tamb']
        delta_T_TO_init = TOC_dict['delta_T_TO_init']
        delta_T_W_init = TOC_dict['delta_T_W_init']
        BP = TOC_dict['BP']
        toc_A = TOC_dict['toc_A']
        toc_B = TOC_dict['toc_B']
        Base_Year = TOC_dict['Base_Year']
        P_Rated = TOC_dict['P_Rated']
        NLL_rate = TOC_dict['NLL_rate']
        LL_rate = TOC_dict['LL_rate']
        Sec_V = TOC_dict['Sec_V']
        TOU_TOR = TOC_dict['TOU_TOR']
        TOU_GR = TOC_dict['TOU_GR']
        Oil_n = TOC_dict['Oil_n']
        Wind_m = TOC_dict['Wind_m']
        delta_T_TOR = TOC_dict['delta_T_TOR']
        delta_T_ave_wind_R = TOC_dict['delta_T_ave_wind_R']

        plotLoadDelta = maxPuLoad / num_samples
        T_amb = [Tamb for _ in range(0, OperatingPeriod)]
        F_AA = [0 for _ in range(0, OperatingPeriod)]
        P_NLL = P_Rated * NLL_rate / 100
        P_LL = P_Rated * LL_rate / 100
        R_ratio = P_LL / P_NLL
        delta_T_hotspot_R = delta_T_ave_wind_R + 15
        delta_T_WR = delta_T_hotspot_R - delta_T_TOR

        # Variable Initialization
        delta_T_TO = [0 for _ in range(0, OperatingPeriod)]
        delta_T_W = [0 for _ in range(0, OperatingPeriod)]
        T_HS = [0 for _ in range(0, OperatingPeriod)]

        # Computing TOC
        TOC = BP + toc_A * P_NLL + toc_B * P_LL
        I_rated = P_Rated / Sec_V

        plotLoadlevel = 0  # pu load level initialized to zero
        DollarsForPlot = [0 for _ in range(0, num_samples)]
        self.Feqa_T = [0 for _ in range(0, num_samples)]
        for Iterator in range(0, num_samples):
            plotLoadlevel = plotLoadlevel + plotLoadDelta
            I_load = [I_rated * plotLoadlevel for _ in range(0, OperatingPeriod)]
            for t in range(0, OperatingPeriod):
                # Computing hot-spot temperature
                K_U = I_load[t] / I_rated
                delta_T_TO_SS = delta_T_TOR * ((((K_U ** 2) * R_ratio + 1) / (R_ratio + 1)) ** Oil_n)
                delta_T_W_SS = delta_T_WR * (K_U ** (2 * Wind_m))
                delta_T_TO[t] = (delta_T_TO_SS - delta_T_TO_init) * (1 - math.exp(-t / TOU_TOR)) + delta_T_TO_init
                delta_T_W[t] = (delta_T_W_SS - delta_T_W_init) * (1 - math.exp(-t / TOU_GR)) + delta_T_W_init
                T_HS[t] = T_amb[t] + delta_T_TO[t] + delta_T_W[t]

                # Computing aging acceleration factor F_AA
                F_AA[t] = math.exp((15000 / (110 + 273)) - (15000 / (T_HS[t] + 273)))

            # Computing equivalent aging acceleration factor F_AA over operating interval
            F_EQA_num = 0
            F_EQA_den = 0
            for t in range(0, OperatingPeriod):
                F_EQA_num = F_EQA_num + F_AA[t] * timeStep
                F_EQA_den = F_EQA_den + timeStep
            F_EQA = F_EQA_num / F_EQA_den  # unit per day

            # to include loss of life as FEQA per hour in metrics colector
            self.Feqa_T[Iterator] = F_EQA / 24  # unit per hour

            # Computing Projected lifetime L in years
            L = Base_Year / F_EQA

            # Computing $ per operating period
            dollars_per_period = (TOC / (L * 365 * 24 * 60)) * costInterval
            DollarsForPlot[Iterator] = dollars_per_period
            LoadsForPlot = [plotLoadDelta * i for i in range(0, num_samples)]

        return DollarsForPlot, LoadsForPlot

    def set_ref_load(self, ref_load):
        """ Set the reference (ercot) load based on provided load by a csv file after base-case, complex number

            Args:
                ref_load (str): total load of substation
        """
        val = parse_kw(ref_load)
        self.total_load = val

    def set_total_load(self, total_load):
        """ Set the residential load based on provided load by GLD, complex number

            Args:
                total_load (str): total load of substation
        """
        val = parse_kw(total_load)
        self.total_load = val

    def set_ind_load(self, industrial_load):
        """ Set the industrial load based on provided load by a csv file after base-case, complex number

        Args:
            industrial_load (str): industrial load of substation
        """
        val = parse_kw(industrial_load)
        self.ind_load = val

    def set_ind_load_da(self, industrial_load_da):
        """ Set the ercot ind load for the next 24-hours provided load by a csv file after base-case, complex number

            Args:
                industrial_load_da (24 x 1 array of double): ercot ind load values for the next day ahead are given in MW and the json.loads function don't know that.
        """
        temp = json.loads(industrial_load_da)
        self.ind_load_da = np.array(temp) * 1000.0

    def set_ref_load_da(self, ref_load_da):
        """ Set the ercot load for the next 24-hours provided load by a csv file after base-case, complex number

            Args:
                ref_load_da (24 x 1 array of double): ercot load values for the next day ahead
        """
        self.ref_load_da = json.loads(ref_load_da)

    def set_lmp_da(self, val):
        """ Set the lmp for day ahead

            Args:
                val (array of double): lmp for the day ahead
        """
        self.lmp_da = json.loads(val)

    def set_lmp_rt(self, val):
        """ Set the lmp for real time

        Args:
            val (double): lmp for the bus/substation
        """
        self.lmp_rt = json.loads(val)

    def set_cleared_q_da(self, val):
        """ Set the clear quantity for day ahead

            Args:
                val (double): lmp for the bus/substation
        """
        self.cleared_q_da = json.loads(val)

    def set_cleared_q_rt(self, val):
        """ Set the clear quantity for real time

            Args:
                val (double): lmp for the bus/substation
        """
        self.cleared_q_rt = json.loads(val)

    def test_function(self):
        """ Test function with the only purpose of returning the name of the object

        """
        return self.name


def test():
    import matplotlib.pyplot as plt
    from .retail_market_dsot import RetailMarketDSOT

    def test_dso_clearing_RT():
        # Dictionary for DSO, Retail agent and TOC calculation
        dso_dict = {
            'windowLength': 48,
            'pricecap': 0.3,
            'num_samples': 1000,
            'DSO_Q_max': 14875000,
            'transformer_degradation': False,
            'distribution_charge_rate': 0.04,
            'dso_retail_scaling': 1.25,
            "number_of_customers": 3680144,
            "number_of_gld_homes": 306,
            "RCI_customer_count_mix": {
                "residential": 0.8357,
                "commercial": 0.1265,
                "industrial": 0.0379
            },
        }

        retail_dict = {
            "num_samples": 1000,
            "pricecap": 1 * 1.25,
            # price cap of the retail agent has to be price cap of the DSO agent multiplies retail rate
            "Q_max": 14875000,
            "maxPuLoading": 1.5,
            "windowLength": 48,
            'OperatingPeriod': 24 * 60,
            'timeStep': 1,
            'Tamb': 30,
            'delta_T_TO_init': 25,
            'delta_T_W_init': 25,
            'BP': 100000,
            'toc_A': 1,
            'toc_B': 1,
            'Base_Year': 180000 / 8760,
            'P_Rated': 2.5e6,
            'NLL_rate': 0.3,
            'LL_rate': 1.0,
            'Sec_V': 69000,
            'TOU_TOR': 1.25 * 60,
            'TOU_GR': 5,
            'Oil_n': 0.8,
            'Wind_m': 0.8,
            'delta_T_TOR': 55,
            'delta_T_ave_wind_R': 65,
            'distribution_charge_rate': 0.04
        }

        # Instantiate DSO agent
        DSO = DSOMarketDSOT(dso_dict, 'www')

        # Instantiate Retail agent
        market = RetailMarketDSOT(retail_dict, "retail_1")

        # Retail agent initializes the RT retail market
        market.clean_bids_RT()

        # Retail agent collects RT bids from DERs
        buyer_bid_1 = [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                       [50.0, 0.06622106443620661]]
        market.curve_aggregator_RT('Buyer', buyer_bid_1, 'abc')

        buyer_bid_2 = [[-5.0, 0.18590669596595727], [0, 0.14961564637563854], [0, 0.11412489053123773],
                       [50.0, 0.077833840940919]]
        market.curve_aggregator_RT('Buyer', buyer_bid_2, 'def')

        buyer_bid_3 = [[-5.0, 0.17548732414146312], [0, 0.13500968174215666], [0, 0.1287308551647196],
                       [50.0, 0.08825321276541313]]
        market.curve_aggregator_RT('Buyer', buyer_bid_3, 'ghi')

        buyer_bid_4 = [[-5.0, 0.18667559364692246], [0, 0.1507218182969266], [0, 0.11301871860994966],
                       [50.0, 0.0770649432599538]]
        market.curve_aggregator_RT('Buyer', buyer_bid_4, 'jkl')

        buyer_bid_5 = [[-5.0, 0.17887117592152127], [0, 0.1373476742467282], [0, 0.12639286266014807],
                       [50.0, 0.08486936098535501]]
        market.curve_aggregator_RT('Buyer', buyer_bid_5, 'mno')

        buyer_bid_6 = [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]]
        market.curve_aggregator_RT('Buyer', buyer_bid_6, 'xsf')

        buyer_bid_7 = [[900, 0.25], [900, 0.1]]
        market.curve_aggregator_RT('Buyer', buyer_bid_7, 'sdf')

        # unscaled_quantities = market.curve_buyer_RT
        # market.curve_buyer_RT.quantities
        market.curve_buyer_RT.quantities = market.curve_buyer_RT.quantities * (
                (DSO.num_of_customers + 2150000.0) * DSO.customer_count_mix_residential / DSO.number_of_gld_homes)
        # market.curve_buyer_RT.prices = market.curve_buyer_RT.prices/1e3
        # DSO agent initializes the RT trial wholesale clearing
        DSO.clean_bids_RT()
        DSO.update_wholesale_node_curve()

        # Current time
        hour_of_day = 8
        day_of_week = 4

        # Retail agent send aggregated RT substation demand curve to DSO agent
        DSO.curve_aggregator_DSO_RT(market.curve_buyer_RT, DSO.DSO_Q_max)
        plt.title('DSO Clearing')
        plt.plot(market.curve_buyer_RT.quantities, market.curve_buyer_RT.prices,
                 label='Aggregated demand curve before preprocessing')
        plt.plot(DSO.curve_DSO_RT.quantities, DSO.curve_DSO_RT.prices, label='Aggregated demand curve at DSO level')
        plt.plot(DSO.curve_ws_node[day_of_week][hour_of_day].quantities,
                 DSO.curve_ws_node[day_of_week][hour_of_day].prices, label='wholesale node supply curve')
        plt.axvline(dso_dict['DSO_Q_max'], label='Original Q max', linewidth=2.0, color='r')
        plt.axvline(max(DSO.curve_ws_node[day_of_week][hour_of_day].quantities), label='Adjusted Q max', linewidth=2.0,
                    color='g')

        plt.xlabel('Quantity (kW)')
        plt.ylabel('Price ($/kWh)')
        plt.legend(loc='best')
        plt.show()

        # DSO agent conducts RT trial wholesale node clearing to determine the RT wholesale cleared price
        DSO.set_Pwclear_RT(hour_of_day, day_of_week)

        # Wholesale RT cleared results
        print("Wholesale trial cleared price: ", str(DSO.Pwclear_RT))
        print("Wholesale trial cleared quantity: ", str(DSO.trial_cleared_quantity_RT))
        # print("Wholesale trial clear type: ", str(DSO.trial_clear_type_RT))

        # DSO agent generate the RT substation supply curve and passed it to retail marekt agent
        market.curve_seller_RT = DSO.substation_supply_curve_RT(market)

        plt.plot(market.curve_seller_RT.quantities, market.curve_seller_RT.prices, label='Substation supply curve',
                 linewidth=2.0)
        plt.title('Retail Clearing')
        plt.plot(market.curve_buyer_RT.quantities, market.curve_buyer_RT.prices, label='Aggregated curve',
                 linewidth=2.0)
        plt.axvline(retail_dict['Q_max'], label='Original Q max', linewidth=2.0, color='r')
        plt.axvline(max(DSO.curve_ws_node[day_of_week][hour_of_day].quantities), label='Adjusted Q max', linewidth=2.0,
                    color='g')

        plt.xlabel('Quantity kW')
        plt.ylabel('Price ($/kWh)')
        plt.legend(loc='best')
        plt.show()

        # Retail agent clear the RT market
        market.clear_market_RT(DSO.transformer_degradation, market.Q_max)

        # Retail RT cleared results
        print("Retail cleared price:", market.cleared_price_RT)
        print("Retail cleared quantity:", market.cleared_quantity_RT)
        print("Retail clear type:", market.clear_type_RT)
        print("Retail congestion surcharge:", market.congestion_surcharge_RT)

    # dollars, pu_loading = DSO.generate_TOC(60, retail_dict['maxPuLoading'], retail_dict['num_samples'],
    #                                        retail_dict)  # cost per 60 minutes (so kW is same as kWh)
    #
    # plt.plot(pu_loading, np.array(dollars)/1000.0,
    #          label='Aggregated demand curve before preprocessing')
    # plt.xlabel('Quantity (p.u)')
    # plt.ylabel('Cost ($)')
    # plt.legend(loc='best')
    # plt.title('TOC')
    # plt.show()

    def test_dso_clearing_DA():
        # Dictionary for DSO, Retail agent and TOC calculation

        dso_dict = {
            'windowLength': 48,
            'pricecap': 0.3,
            'num_samples': 1000,
            'DSO_Q_max': 14875000,
            'transformer_degradation': False,
            'distribution_charge_rate': 0.04,
            'dso_retail_scaling': 1.25,
            "number_of_customers": 3680144,
            "number_of_gld_homes": 306,
            "RCI_customer_count_mix": {
                "residential": 0.8357,
                "commercial": 0.1265,
                "industrial": 0.0379
            },
        }

        retail_dict = {
            "num_samples": 1000,
            "pricecap": 1 * 1.25,
            # price cap of the retail agent has to be price cap of the DSO agent multiplies retail rate
            "Q_max": 14875000,
            "maxPuLoading": 1.5,
            "windowLength": 48,
            'OperatingPeriod': 24 * 60,
            'timeStep': 1,
            'Tamb': 30,
            'delta_T_TO_init': 25,
            'delta_T_W_init': 25,
            'BP': 100000,
            'toc_A': 1,
            'toc_B': 1,
            'Base_Year': 180000 / 8760,
            'P_Rated': 2.5e6,
            'NLL_rate': 0.3,
            'LL_rate': 1.0,
            'Sec_V': 69000,
            'TOU_TOR': 1.25 * 60,
            'TOU_GR': 5,
            'Oil_n': 0.8,
            'Wind_m': 0.8,
            'delta_T_TOR': 55,
            'delta_T_ave_wind_R': 65,
            'distribution_charge_rate': 0.04
        }
        # instantiate DSO agent
        DSO = DSOMarketDSOT(dso_dict, 'www')

        # instantiate Retail agent
        market = RetailMarketDSOT(retail_dict, "retail_1")

        # Retail agent initializes the DA retail market
        market.clean_bids_DA()

        # Retail agent collects DA bids from DERs
        buyer_bid_1 = [[[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]]]
        market.curve_aggregator_DA('Buyer', buyer_bid_1, 'abc')

        buyer_bid_2 = [[[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]]]
        market.curve_aggregator_DA('Buyer', buyer_bid_2, 'def')

        buyer_bid_3 = [[[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]]]
        market.curve_aggregator_DA('Buyer', buyer_bid_3, 'ghi')

        buyer_bid_4 = [[[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]]]
        market.curve_aggregator_DA('Buyer', buyer_bid_4, 'jkl')

        buyer_bid_5 = [[[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]],
                       [[-5.0, 0.19751947247066967], [0, 0.1505365976142517], [0, 0.11320393929262458],
                        [50.0, 0.06622106443620661]]]
        market.curve_aggregator_DA('Buyer', buyer_bid_5, 'mno')

        buyer_bid_6 = [[[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]],
                       [[40.8586259999999984, 0.0841402434079265], [50.0, 0.056556325208806844]]]
        market.curve_aggregator_DA('Buyer', buyer_bid_6, 'xsf')

        buyer_bid_7 = [[[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[500, 0.25], [500, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[800, 0.25], [800, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]],
                       [[900, 0.25], [900, 0.1]]]
        market.curve_aggregator_DA('Buyer', buyer_bid_7, 'sdf')

        # DSO agent initializes the DA trial wholesale clearing
        DSO.clean_bids_DA()
        DSO.update_wholesale_node_curve()

        # Current time
        hour_of_day = 8
        day_of_week = 4

        # Retail agent send aggregated DA substation demand curve to DSO agent

        market.curve_buyer_DA[8].quantities = market.curve_buyer_DA[8].quantities * (
                DSO.num_of_customers * DSO.customer_count_mix_residential / DSO.number_of_gld_homes) + 4552612.0
        market.curve_buyer_DA[0].quantities = market.curve_buyer_DA[0].quantities * (
                DSO.num_of_customers * DSO.customer_count_mix_residential / DSO.number_of_gld_homes) + 9552612.0

        DSO.curve_aggregator_DSO_DA(market.curve_buyer_DA, DSO.DSO_Q_max)

        plt.plot(market.curve_buyer_DA[0].quantities, market.curve_buyer_DA[0].prices,
                 label='Aggregated demand curve before preprocessing')
        plt.plot(DSO.curve_DSO_DA[0].quantities, DSO.curve_DSO_DA[0].prices,
                 label='Aggregated demand curve at DSO level')
        plt.plot(DSO.curve_ws_node[day_of_week][hour_of_day].quantities,
                 DSO.curve_ws_node[day_of_week][hour_of_day].prices, label='wholesale node supply curve')
        plt.xlabel('Quantity')
        plt.ylabel('Price')
        plt.legend(loc='best')
        plt.title('DSO DA Market hour 8 week 4')
        plt.show()

        # DSO agent conducts DA trial wholesale node clearing to determine the RT wholesale cleared price
        DSO.set_Pwclear_DA(hour_of_day, day_of_week)

        # Wholesale DA cleared results
        print("Wholesale trial cleared price: ", str(DSO.Pwclear_DA))
        print("Wholesale trial cleared quantity: ", str(DSO.trial_cleared_quantity_DA))
        print("Wholesale trial clear type: ", str(DSO.trial_clear_type_DA))

        # DSO agent generate the DA substation supply curve and passed it to retail market agent
        market.curve_seller_DA = DSO.substation_supply_curve_DA(market)

        # Retail agent clear the DA market
        market.clear_market_DA(DSO.transformer_degradation, market.Q_max)

        # Retail DA cleared results
        print("Retail cleared price:", market.cleared_price_DA)
        print("Retail cleared quantity:", market.cleared_quantity_DA)
        print("Retail clear type:", market.clear_type_DA)

    # test real-time portion
    test_dso_clearing_RT()
    # test day-ahead portion
    # test_dso_clearing_DA()


if __name__ == "__main__":
    test()
