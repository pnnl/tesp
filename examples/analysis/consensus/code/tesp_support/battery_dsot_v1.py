# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: battery_dsot_v1.py # TODO: update
"""Class that controls the Battery DER

Implements the optimum schedule of charging and discharging DA; generate the bids
for DA and RT; monitor and supervisory control of GridLAB-D environment element.

The function call order for this agent is:
    initialize
    
    set_price_forecast(forecasted_price)
    
    Repeats at every hour:
        formulate_bid_da(){return BID}
        
        set_price_forecast(forecasted_price)
               
        Repeats at every 5 min:
            set_battery_SOC(fncs_str){updates C_init}
            
            formulate_bid_rt(){return BID}
            
            inform_bid(price){update RTprice}
            
            bid_accepted(){update inv_P_setpoint and GridLAB-D P_out if needed}
           

"""
import logging as log
import math
from copy import deepcopy

import numpy as np
import pyomo.environ as pyo

import tesp_support.helpers as helpers

logger = log.getLogger()


class BatteryDSOT:
    """This agent manages the battery/inverter

    Args:
        TODO: update inputs for this agent
        model_diag_level (int): Specific level for logging errors; set it to 11
        sim_time (str): Current time in the simulation; should be human readable

    Attributes: #TODO: update attributes for this agent
        #initialize from Args:
        name (str): name of this agent
        Rc (float): rated charging power in kW for the battery
        Rd (float): rated discharging power in kW for the battery
        Lin (float): battery charging loss in %
        Lout (float): battery discharging loss in %
        Cmin (float): minimum allowable stored energy in kWh (state of charge lower limit)
        Cmax (float): maximum allowable stored energy in kWh (state of charge upper limit)
        Cinit (float): initial stored energy in the battery in kWh
        batteryCapacity (float): battery capacity in kWh
        batteryLifeDegFactor (float): constant to model battery degradation
        windowLength (int): length of day ahead optimization period in hours (e.g. 48 hours)
        dayAheadCapacity (float): % of battery capacity reserved for day ahead bidding
        
        #no initialization required
        bidSpread (int): this can be used to spread out bids in multiple hours. When set to 1 hour (recommended), it’s effect is none 
        P (int): location of P in bids
        Q (int): location of Q in bids
        f_DA (float) (1 X windowLength): forecasted prices in $/kWh for all the hours in the duration of windowLength
        ProfitMargin_slope (float): specified in % and used to modify slope of bid curve. Set to 0 to disable
        ProfitMargin_intercept (float): specified in % to generate a small dead band (i.e., change in price does not affect quantity). Set to 0 to disable
        pm_hi (float): Highest possible profit margin in %
        pm_lo (float): Lowest possible profit margin in %
        RT_state_maintaing (boolean): true if battery must maintain charging or discharging state for 1 hour
        RT_state_maintaing_flag (int): (0) not define at current hour (-1) charging (+1) discharging
        RT_FNCS_flag (boolean): if True, FNCS has to update Gridlab-D 
        inv_P_setpoint (float): next Gridlab-D inverter power output 
        optimized_Quantity (float) (1 X Window Length): Optimized quantity 
        #not used if not biding DA
        prev_clr_Quantity (float) (1 X Window Length): cleared quantities (kWh) from previous market iteration for all hours 
        prev_clr_Price (float) (1 X windowLength): cleared prices ($/kWh) from previous market iteration
        BindingObjFunc (boolean): if True, then optimization considers cleared price, quantities from previous iteration in the objective function


    """

    def __init__(self, battery_dict, inv_properties, key, model_diag_level, sim_time,
                 solver):  # TODO: update inputs for class
        """Initializes the class
        """
        # TODO: update attributes of class
        # initialize from Args:
        self.name = key
        self.solver = solver
        self.participating = battery_dict['participating']
        self.Rc = float(battery_dict['rating']) * 0.001
        self.Rd = float(battery_dict['rating']) * 0.001
        self.Lin = float(battery_dict['efficiency'])  # this includes both inverter and single trip battery efficiency
        self.Lout = float(battery_dict['efficiency'])
        self.reserved_soc = float(battery_dict['reserved_soc'])
        self.Cmin = float(battery_dict['capacity'] * self.reserved_soc) * 0.001
        self.Cmax = float(battery_dict['capacity']) * 0.001
        self.Cinit = float(battery_dict['charge']) * 0.001
        self.batteryCapacity = float(battery_dict['capacity']) * 0.001
        self.period = 300
        self.soc_upper_res = 0.99  # maximum soc
        # made constant
        self.batteryLifeDegFactor = float(
            battery_dict['degrad_factor']) * 0.001  # float(0.025)#float(0.002)#float(0.025)
        self.windowLength = int(48)
        self.dayAheadCapacity = float(80)
        # no initialization required
        self.bidSpread = int(1)
        self.P = int(1)
        self.Q = int(0)
        self.f_DA = [0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20, 0.20,
                     0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30,
                     0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20, 0.20,
                     0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32,
                     0.30]  # price vector to initialize and to be used in the first optimization
        self.RTprice = 0.0
        self.slider = float(battery_dict['slider_setting'])
        self.profit_margin = float(battery_dict['profit_margin'])
        self.RT_state_maintaing = bool(False)
        self.RT_state_maintaing_flag = int(0)
        self.RT_FNCS_flag = bool(False)
        self.inv_P_setpoint = float(0.0)
        self.inv_Q_setpoint = float(0.0)
        self.optimized_Quantity = [[]] * self.windowLength
        # not used if not biding DA
        self.prev_clr_Quantity = list()
        self.prev_clr_Price = list()
        self.BindingObjFunc = bool(False)

        self.bid_rt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
        self.bid_da = [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]] for i in
                       range(self.windowLength)]  # [[[0., 0.], [0., 0.], [0., 0.], [0., 0.]]] * self.windowLength

        # optimization
        self.TIME = range(0, self.windowLength)

        ### Sanity checks:
        if self.Cmin <= self.batteryCapacity and self.Cmax >= self.batteryCapacity:
            # log.info('Cmin < batteryCapacity < Cmax.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- batteryCapacity is {}, not between Cmin ({}) and Cmax ({})'.format(self.name, 'init',
                                                                                                 self.batteryCapacity,
                                                                                                 self.Cmin, self.Cmax))

        Lin_lower = 0
        Lin_upper = 1
        if 0 < self.Lin and 1 > self.Lin:
            # log.info('Lin is within the bounds.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- Lin is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.Lin,
                                                                                      Lin_lower, Lin_upper))

        Lout_lower = 0
        Lout_upper = 1
        if 0 < self.Lout and 1 > self.Lout:
            # log.info('Lout is within the bounds.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- Lout is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.Lout,
                                                                                       Lout_lower, Lout_upper))

        reserved_soc_lower = 0
        reserved_soc_upper = 1
        if reserved_soc_lower < self.reserved_soc and reserved_soc_upper > self.reserved_soc:
            # log.info('reserved_soc is within the bounds.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- reserved_soc is {}, outside of nominal range of {} to {}'.format(self.name, 'init',
                                                                                               self.reserved_soc,
                                                                                               reserved_soc_lower,
                                                                                               reserved_soc_upper))

        if 0 < self.batteryLifeDegFactor and 1 > self.batteryLifeDegFactor:
            # log.info('batteryLifeDegFactor is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- batteryLifeDegFactor is out of bounds.'.format(self.name, 'init'))

    def test_function(self):
        """ Test function with the only purpose of returning the name of the object

        """
        return self.name

    def inform_bid(self, price):
        """ Set the cleared_price attribute

        Args:
            price (float): cleared price in $/kWh
        """
        self.RTprice = price

    def bid_accepted(self, current_time):
        """ Update the P and Q settings if the last bid was accepted

        Returns:
            Boolean: True if the inverter settings changed, False if not.
        """
        self.RT_gridlabd_set_P(11, current_time)
        return self.RT_FNCS_flag

    def set_price_forecast(self, forecasted_price):
        """ Set the f_DA attribute

        Args:
            forecasted_price (float x 48): cleared price in $/kWh
        """
        self.f_DA = deepcopy(forecasted_price)

    def DA_cleared_price(self, price):
        """ Set the DA_cleared_price attribute

        Args:
            price (float): cleared price in $/kWh
        """
        # TODO: THis is not used, do we need it?
        self.prev_clr_Quantity = list()
        self.prev_clr_Price = list()
        self.prev_clr_Price = deepcopy(price)
        self.BindingObjFunc = bool(True)
        for i in range(len(self.prev_clr_Price)):
            self.prev_clr_Quantity.append(self.from_P_to_Q_battery(self.bid_da[i], self.prev_clr_Price[i]))
        self.prev_clr_Price.pop(0)
        self.prev_clr_Quantity.pop(0)
        self.prev_clr_Price.append(0.0)
        self.prev_clr_Quantity.append(0.0)

    def formulate_bid_da(self):
        """ Formulate 4 points of P and Q bids for the DA market
        
        Function calls "DA_optimal_quantities" to obtain the optimal quantities 
        for the DA market. With the quantities, the 4 point bids are formulated.
        
        Before returning the BID the function resets "RT_state_maintaing_flag" 
        wich if RT_state_maintaing is TRUE the battery will be forced to keep its
        state (i.e., charging or discharging).
        
        Returns:
            BID (float) (((1,2)X4) X windowLength): store last DA market bids
        """
        #        Quantity = self.DA_optimal_quantities()
        Quantity = deepcopy(self.optimized_Quantity)

        P = self.P
        Q = self.Q
        TIME = range(0, self.windowLength)
        CurveSlope = [0] * len(TIME)
        yIntercept = [-1] * len(TIME)
        BID = [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]] for i in TIME]
        deltaf_DA = max(self.f_DA) - min(self.f_DA)

        for t in TIME:
            # CurveSlope[t] = ((max(self.f_DA)-min(self.f_DA))/(-self.Rd-self.Rc))*(1 + self.ProfitMargin_slope/100)   #Remains same in all hours of the window
            if self.slider != 0:
                CurveSlope[t] = ((max(self.f_DA) - min(self.f_DA)) / (
                            -self.Rd - self.Rc)) / self.slider  # Remains same in all hours of the window
                yIntercept[t] = self.f_DA[t] - CurveSlope[t] * Quantity[t]  # Is different for each hour of the window

                BID[t][0][Q] = -self.Rd
                BID[t][1][Q] = Quantity[t]
                BID[t][2][Q] = Quantity[t]
                BID[t][3][Q] = self.Rc

                # BID[t][0][P] =    -self.Rd*CurveSlope[t]+yIntercept[t]+(self.ProfitMargin_intercept/100)*deltaf_DA
                # BID[t][1][P] = Quantity[t]*CurveSlope[t]+yIntercept[t]+(self.ProfitMargin_intercept/100)*deltaf_DA
                # BID[t][2][P] = Quantity[t]*CurveSlope[t]+yIntercept[t]-(self.ProfitMargin_intercept/100)*deltaf_DA
                # BID[t][3][P] = self.Rc * CurveSlope[t] + yIntercept[t] - (self.ProfitMargin_intercept / 100) * deltaf_DA
                BID[t][0][P] = -self.Rd * CurveSlope[t] + yIntercept[t] + self.batteryLifeDegFactor * (
                            1 + self.profit_margin)
                BID[t][1][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] + self.batteryLifeDegFactor * (
                            1 + self.profit_margin)
                BID[t][2][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] - self.batteryLifeDegFactor * (
                            1 + self.profit_margin)
                BID[t][3][P] = self.Rc * CurveSlope[t] + yIntercept[t] - self.batteryLifeDegFactor * (
                            1 + self.profit_margin)
            else:  # if slider is 0: inflexible straight vertical bid
                BID[t][0][Q] = Quantity[t]
                BID[t][1][Q] = Quantity[t]
                BID[t][2][Q] = Quantity[t]
                BID[t][3][Q] = Quantity[t]

                BID[t][0][P] = max(self.f_DA)
                BID[t][1][P] = self.f_DA[t]
                BID[t][2][P] = self.f_DA[t]
                BID[t][3][P] = min(self.f_DA)

        self.bid_da = deepcopy(BID)

        self.RT_state_maintaing_flag = 0

        return self.bid_da

    def obj_rule(self, m):
        return sum(
            self.f_DA[i] * (m.E_DA_out[i] - m.E_DA_in[i]) - self.batteryLifeDegFactor * (1 + self.profit_margin) * (
                        m.E_DA_out[i] + m.E_DA_in[i]) - 0.001 * (
                        m.E_DA_out[i] * m.E_DA_out[i] + 2 * m.E_DA_out[i] * m.E_DA_in[i] + m.E_DA_in[i] * m.E_DA_in[i])
            for i in self.TIME)  # - 0.0000003*(m.E_DA_out[i]+m.E_DA_in[i])**2

    def con_rule_ine1(self, m, i):
        return m.E_stor_out[i] <= (self.dayAheadCapacity / 100) * self.Rd / self.bidSpread

    def con_rule_ine2(self, m, i):
        return m.E_stor_in[i] <= (self.dayAheadCapacity / 100) * self.Rc / self.bidSpread

    def con_rule_eq1(self, m, i):
        return m.E_DA_out[i] == m.E_stor_out[i] * (1 - (self.Lout / 100))

    def con_rule_eq2(self, m, i):
        return m.E_DA_in[i] == m.E_stor_in[i] * (1 / (1 - (self.Lin / 100)))

    def con_rule_eq3(self, m, i):
        if i == 0:
            return m.C[i] == self.Cinit - m.E_stor_out[i] + m.E_stor_in[i]
        else:
            return m.C[i] == m.C[i - 1] - m.E_stor_out[i] + m.E_stor_in[i]

    def DA_optimal_quantities(self):
        """ Generates Day Ahead optimized quantities for Battery
          
        Returns:
            Quantity (float) (1 x windowLength): Optimal quantity from optimization for all hours of the window specified by windowLength
        """
        if self.Cinit > self.Cmax:
            self.Cinit = self.Cmax
        if self.Cinit < self.Cmin:
            self.Cinit = self.Cmin

        model = pyo.ConcreteModel()
        model.E_DA_out = pyo.Var(self.TIME, bounds=(0, self.Rd * 2))  # , initialize=self.Rd*2)
        model.E_DA_in = pyo.Var(self.TIME, bounds=(0, self.Rc * 2))  # , initialize=self.Rc*2)
        model.E_stor_out = pyo.Var(self.TIME, bounds=(0, self.Rd))  # , initialize=self.Rd)
        model.E_stor_in = pyo.Var(self.TIME, bounds=(0, self.Rc))  # , initialize=self.Rc)
        model.C = pyo.Var(self.TIME, bounds=(self.Cmin, self.Cmax))  # , initialize=self.Cmax)

        model.obj = pyo.Objective(rule=self.obj_rule, sense=pyo.maximize)
        model.con1 = pyo.Constraint(self.TIME, rule=self.con_rule_ine1)
        model.con2 = pyo.Constraint(self.TIME, rule=self.con_rule_ine2)
        model.con3 = pyo.Constraint(self.TIME, rule=self.con_rule_eq1)
        model.con4 = pyo.Constraint(self.TIME, rule=self.con_rule_eq2)
        model.con5 = pyo.Constraint(self.TIME, rule=self.con_rule_eq3)

        # print('day_ahead_price_forcast...', self.f_DA)

        results = helpers.get_run_solver("bt_" + self.name, pyo, model, self.solver)

        Quantity = [0] * len(model.E_DA_in)
        TOL = 0.00001  # Tolerance for checking bid
        for t in model.E_DA_in:
            if pyo.value(model.E_DA_in[t]) > TOL:
                Quantity[t] = pyo.value(model.E_DA_in[t])  # For logging
            if pyo.value(model.E_DA_out[t]) > TOL:
                Quantity[t] = pyo.value(-model.E_DA_out[t])

        #        self.optimized_Quantity = deepcopy(Quantity)
        return Quantity

    def formulate_bid_rt(self):
        """ Formulates RT bid
        
        Uses the last 4 point bid from DA market and consider current state
        of charge of the battery. Will change points to change points for feasible
        range of Qmin Qmax points if necessary. Furthermore, allows a maximum 
        deviation of +/-100% from the DA plan.
        
        Returns:
            realTimeBid (float) ((1,2) x 4):  bid in Real Time market 
        """
        P = self.P
        Q = self.Q
        BID = deepcopy(self.bid_da[0])
        ## identify error start
        state = 0
        t = self.period
        t = t / (60 * 60)  # hour
        if (self.Cinit + BID[3][Q] * t) > self.Cmax * self.soc_upper_res:
            state = state + 1
        if (self.Cinit + BID[0][Q] * t) < self.Cmin:
            state = state + 2
        ##identify error end
        ##fix 4 point error if exixtent start
        if state >= 3:
            print("Battery Error --> Verify Battery RC, RD, and batteryCapacity")
            print(self.Rc);
            print(self.Rd);
            print(self.batteryCapacity)

        if state == 0:  # no error
            realTimeBid = BID
        else:  # fixing error
            if state == 1:  # fixing error type 1
                x = self.Cmax * self.soc_upper_res - self.Cinit
                x = x / t  # to W
                realTimeBid = self.RT_fix_four_points_range(BID, BID[0][Q], x)
            if state == 2:  # fixing error type 2
                x = self.Cmin - self.Cinit
                x = x / t  # to W
                realTimeBid = self.RT_fix_four_points_range(BID, x, BID[3][Q])
        ##fix 4 point error if exixtent end
        ##force charging or discharging for the hour start
        if self.RT_state_maintaing and self.RT_state_maintaing_flag != 0:
            if self.RT_state_maintaing_flag < 0:
                realTimeBid = self.RT_fix_four_points_range(realTimeBid, 0.0, float('inf'))
            else:
                realTimeBid = self.RT_fix_four_points_range(realTimeBid, -float('inf'), 0.0)
        ##force charging or discharging for the hour end

        excursion = self.Rd * 1.0  # 100% of all excursion
        E_realTimeBid = self.RT_fix_four_points_range(realTimeBid, realTimeBid[1][Q] - excursion,
                                                      realTimeBid[1][Q] + excursion)
        self.bid_rt = deepcopy(E_realTimeBid)

        return self.bid_rt

    def RT_fix_four_points_range(self, BID, Ql, Qu):
        """ Verify feasible range of RT bid
        
        Args:
            BID (float) ((1,2)X4): 4 point bid
          
        Returns:
            BIDr (float) ((1,2)X4): 4 point bid only the feasible range
        """
        P = self.P
        Q = self.Q
        temp = 0
        m = float('nan')
        try:
            m = (BID[0][P] - BID[1][P]) / (BID[0][Q] - BID[1][Q])  # y = m*x + b
        except:
            try:
                m = (BID[2][P] - BID[3][P]) / (BID[2][Q] - BID[3][Q])  # y = m*x + b
            except:
                temp = 1

        if math.isnan(m) and temp == 0:
            try:
                m = (BID[2][P] - BID[3][P]) / (BID[2][Q] - BID[3][Q])  # y = m*x + b
            except:
                temp = 1

        if math.isnan(m):
            temp = 1

        if temp == 0:
            b0 = BID[0][P] - BID[0][Q] * m
            b1 = BID[3][P] - BID[3][Q] * m

            BIDr = deepcopy(BID)

            flag = [1] * len(BID)
            for n in range(0, len(BID)):
                if Ql <= BID[n][Q] and BID[n][Q] <= Qu:
                    flag[n] = 0
                else:
                    if BID[n][Q] > Qu:
                        BIDr[n][Q] = Qu
                    elif BID[n][Q] < Ql:
                        BIDr[n][Q] = Ql
            if sum(flag) == 0:
                print('Battery Error --> RT_fix_four_points_range function should not have been called')
                print(Ql)
                print(Qu)
            else:
                BIDr[0][P] = m * BIDr[0][Q] + b0
                BIDr[1][P] = m * BIDr[1][Q] + b0
                BIDr[2][P] = m * BIDr[2][Q] + b1
                BIDr[3][P] = m * BIDr[3][Q] + b1
        else:
            BIDr = BID

        return BIDr

    def RT_gridlabd_set_P(self, model_diag_level, sim_time):
        """ Update variables for battery output "inverter"
        
        Args:
            model_diag_level (int): Specific level for logging errors; set it to 11
            sim_time (str): Current time in the simulation; should be human readable
        
        inv_P_setpoint is a float in W
        """
        realTimeBid = deepcopy(self.bid_rt)
        invPower = self.from_P_to_Q_battery(realTimeBid, self.RTprice)

        if invPower < 0:
            self.RT_state_maintaing_flag = -1
        elif invPower > 0:
            self.RT_state_maintaing_flag = 1

        if (invPower - self.inv_P_setpoint) != 0.0:
            self.inv_P_setpoint = invPower * 1000.0
            self.RT_FNCS_flag = True
        else:
            self.RT_FNCS_flag = False

        ### Sanity checks
        if self.inv_P_setpoint <= self.Rd * 1000:
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- output power ({}) is not <= rated output power ({}).'.format(self.name, sim_time,
                                                                                           self.inv_P_setpoint,
                                                                                           self.Rd))
        if self.inv_P_setpoint >= -self.Rc * 1000:
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- input power ({}) is not <= rated input power ({}).'.format(self.name, sim_time,
                                                                                         -self.inv_P_setpoint, self.Rc))

    def set_battery_SOC(self, fncs_str, model_diag_level, sim_time):
        """ Set the battery state of charge
        
        Updates the self.Cinit of the battery
        
        Args:
             fncs_str (str): FNCS message with battery SOC in pu
             model_diag_level (int): Specific level for logging errors; set it to 11
             sim_time (str): Current time in the simulation; should be human readable
             
        """
        val = helpers.parse_fncs_number(fncs_str)
        self.Cinit = self.batteryCapacity * val

        ### Sanity checks #TODO: following sanity check is wrong. should be reomved
        # assert 0 <= self.Cmin
        # assert 1 >= self.Cmax

        if self.Cmin < self.Cinit and self.Cmax > self.Cinit:
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- SOC ({}) is not between Cmin ({}) and Cmax ({}).'.format(self.name, sim_time, self.Cinit,
                                                                                       self.Cmin, self.Cmax))

    def from_P_to_Q_battery(self, BID, PRICE):
        """ Convert the 4 point bids to a quantity with the known price
        
        Args:
            BID (float) ((1,2)X4): 4 point bid
            PRICE (float): cleared price in $/kWh
          
        Returns:
            quantity (float): active power (-) charging (+) discharging
        """
        P = self.P
        Q = self.Q
        temp = 0
        m = float('nan')
        try:
            m = (BID[0][P] - BID[1][P]) / (BID[0][Q] - BID[1][Q])  # y = m*x + b
        except:
            try:
                m = (BID[2][P] - BID[3][P]) / (BID[2][Q] - BID[3][Q])  # y = m*x + b
            except:
                temp = 1

        if math.isnan(m) and temp == 0:
            try:
                m = (BID[2][P] - BID[3][P]) / (BID[2][Q] - BID[3][Q])  # y = m*x + b
            except:
                temp = 1

        if math.isnan(m):
            temp = 1

        if temp == 0:
            if PRICE >= BID[0][P]:  # battery at maximun discharg
                quantity = -BID[0][Q]
            elif PRICE <= BID[3][P]:  # battery at maximun charging
                quantity = -BID[3][Q]
            elif BID[2][P] <= PRICE <= BID[1][P]:  # battery at deadband
                quantity = -BID[2][Q]
            elif BID[1][P] <= PRICE <= BID[0][P]:  # frist curve
                b = BID[1][P] - BID[1][Q] * m
                quantity = -1 * ((PRICE - b) / m)
            else:
                b = BID[3][P] - BID[3][Q] * m
                quantity = -1 * ((PRICE - b) / m)
        else:
            quantity = -BID[1][Q]

        return quantity


if __name__ == "__main__":
    """Testing
    
    Makes a single battery agent and run DA 
    """
    import time

    start_time = time.time()
    price_DA = np.array([0.43, 0.41, 0.40, 0.39, 0.39, 0.40, 0.45, 0.45, 0.55, 0.80, 0.90, 0.98,
                         0.99, 1.00, 1.00, 0.99, 0.98, 0.97, 0.97, 0.90, 0.70, 0.60, 0.55, 0.45,
                         0.43, 0.41, 0.40, 0.39, 0.39, 0.40, 0.45, 0.45, 0.55, 0.80, 0.90, 0.98,
                         0.99, 1.00, 1.00, 0.99, 0.98, 0.97, 0.97, 0.90, 0.70, 0.60, 0.55, 0.45]) * 10

    price_DA = np.array(
        [0.03993261478420569, 0.039215450079458584, 0.038270843288647, 0.038270843288647, 0.039678908753851404,
         0.04952765679409438, 0.04952765679409438, 0.07374258138131866, 0.1552344563077759, 0.19623572319075658,
         0.2324796528836079, 0.2365042650796865, 0.2396704917979635, 0.2396704917979635, 0.23486256440069483,
         0.23017281170082035, 0.22548608875298554, 0.22548326238474659, 0.19411158298892114, 0.11736390212355825,
         0.08761614700773397, 0.07373201423859767, 0.049516022710832344, 0.045233513929478525, 0.041185875046800276,
         0.039215450079458584, 0.03733247031743611, 0.03733247031743611, 0.039231007094646435, 0.049533555448962346,
         0.049533555448962346, 0.07374822335359382, 0.15528210258746128, 0.19623572319075658, 0.2324796528836079,
         0.23656113011771765, 0.2396704917979635, 0.2396704917979635, 0.23486256440069483, 0.23017281170082035,
         0.22548884386312235, 0.22548326238474659, 0.19411167146483035, 0.1173639125710286, 0.08761616056951234,
         0.07373202984378939, 0.049516022710832344, 0.045233513929478525])

    glm = {"feeder_id": "network_node", "billingmeter_id": "Houses_A_mtr_1", "rated_W": 5000.0, "resource": "battery",
           "inv_eta": 0.97, "bat_eta": 0.86, "bat_capacity": 13500.0, "bat_soc": 0.5}
    agent = {"batteryName": "Houses_A_bat_1", "meterName": "Houses_A_mtr_1", "capacity": 16187.31, "rating": 5657.93,
             "charge": 8093.655, "efficiency": 0.9552, "slider_setting": 0.8501, "reserved_soc": 0.2,
             "profit_margin": 7.2485, "degrad_factor": 0.0227, "participating": True}

    BID = [[-5.0, 0.42129778616103297], [-0.39676675, 0.30192681471917215], [-0.39676675, 0.17229206883635942],
           [5.0, 0.03234319929066909]]

    ### Uncomment for testing logging functionality.
    ### Supply these values when using the battery agent in the
    ### simulation.
    # model_diag_level = 11
    # hlprs.enable_logging('DEBUG', model_diag_level)
    sim_time = '2019-11-20 07:47:00'

    B_obj1 = BatteryDSOT(agent, glm, 'test', 11, sim_time)  # make object; add model_diag_level and sim_time
    B_obj1.set_price_forecast(price_DA.tolist())
    quantity = B_obj1.DA_optimal_quantities()
    B_obj1.optimized_Quantity = quantity
    BIDS = B_obj1.formulate_bid_da()
    print("--- %s seconds ---" % (time.time() - start_time))
    #    B = B_obj1.RT_fix_four_points_range(BID,0.2920860000000012,5.0)
    #    A = B_obj1.RT_fix_four_points_range(B,0.2920860000000012,0.2920860000000012)
    #    B_obj2 = BatteryDSOT(agent,glm,'test')# make object

    B_obj1.Cinit = agent['capacity'] / 1000 * 0.99
    rtbid = B_obj1.formulate_bid_rt()
    price_forecast = B_obj1.f_DA
    BIDS_of_agent = B_obj1.bid_da
    # B_obj.Cinit = B_obj.batteryCapacity * 0.5#B_obj.set_battery_SOC()
    BID = [[-5.0, 6.0], [0.0, 5.0], [0.0, 4.0], [5.0, 3.0]]
    fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, 10.0)
    print(fixed)
    fixed = B_obj1.RT_fix_four_points_range(BID, -float('inf'), 0.0)
    print(fixed)
    fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, float('inf'))
    print(fixed)
    fixed = B_obj1.RT_fix_four_points_range(BID, 0.5, 0.5)
    print(fixed)
    getQ = B_obj1.from_P_to_Q_battery(BID, 10)
    print(getQ)
    getQ = B_obj1.from_P_to_Q_battery(fixed, 10)
    print(getQ)
