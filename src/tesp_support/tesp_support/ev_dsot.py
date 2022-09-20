# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: ev_dsot.py
"""Class that controls the Electric Vehicle

Implements the optimum schedule of charging and discharging DA; generate the bids
for DA and RT; monitor and supervisory control of GridLAB-D environment element.

The function call order for this agent is:
    initialize
    
    set_price_forecast(forecasted_price)
    
    Repeats at every hour:
        formulate_bid_da(){return BID}
        set_price_forecast(forecasted_price)
        Repeats at every 5 min:
            set_battery_SOC(msg_str){updates C_init}
            formulate_bid_rt(){return BID}
            inform_bid(price){update RTprice}
            bid_accepted(){update inv_P_setpoint and GridLAB-D P_out if needed}

"""
import logging as log
from copy import deepcopy
from datetime import datetime, timedelta
from math import isnan

import numpy as np
import pyomo.environ as pyo

import tesp_support.feederGenerator_dsot as fg
from .helpers import parse_number
from .helpers_dsot import get_run_solver

logger = log.getLogger()


class EVDSOT:
    """This agent manages the electric vehicle (ev)

    Args:
        TODO: update inputs for this agent

        model_diag_level (int): Specific level for logging errors; set it to 11
        sim_time (str): Current time in the simulation; should be human-readable

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
        evCapacity (float): battery capacity in kWh
        batteryLifeDegFactor (float): constant to model battery degradation
        windowLength (int): length of day ahead optimization period in hours (e.g. 48-hours)
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
        RT_state_maintain (boolean): true if battery must maintain charging or discharging state for 1 hour
        RT_state_maintain_flag (int): (0) not define at current hour (-1) charging (+1) discharging
        RT_flag (boolean): if True, has to update GridLAB-D
        inv_P_setpoint (float): next GridLAB-D inverter power output
        optimized_Quantity (float) (1 X Window Length): Optimized quantity
        #not used if not biding DA
        prev_clr_Quantity (float) (1 X Window Length): cleared quantities (kWh) from previous market iteration for all hours
        prev_clr_Price (float) (1 X windowLength): cleared prices ($/kWh) from previous market iteration
        BindingObjFunc (boolean): if True, then optimization considers cleared price, quantities from previous iteration in the objective function


    """

    def __init__(self, ev_dict, inv_properties, key, model_diag_level, sim_time, solver):
        # TODO: update inputs for class
        """Initializes the class
        """
        # TODO: update attributes of class
        # initialize from Args:
        self.name = key
        self.houseName = ev_dict['houseName']
        self.solver = solver
        self.participating = ev_dict['participating']
        self.Rc = float(ev_dict['max_charge']) * 0.001  # kW
        self.ev_mode = ev_dict['ev_mode']
        if self.ev_mode == 'V1G':
            self.Rd = 0
        elif self.ev_mode == 'V2G':
            self.Rd = float(ev_dict['max_charge']) * 0.001  # kW
        self.soc_upper_res = 0.99  # maximum soc
        self.Lin = float(ev_dict['efficiency'])  # charging efficiency in pu
        self.Lout = 1.0  # discharging has no efficiency factor
        self.reserved_soc = 0.2  # float(ev_dict['reserved_soc'])
        self.range = float(ev_dict['range_miles'])
        self.mileage = float(ev_dict['miles_per_kwh'])
        self.evCapacity = self.range / self.mileage
        self.Cmin = self.evCapacity * self.reserved_soc
        self.Cmax = self.evCapacity * self.soc_upper_res
        self.Cinit = float(ev_dict['initial_soc']) / 100 * self.evCapacity
        self.travel_miles = float(ev_dict['daily_miles'])
        self.arrival_work = float(ev_dict['arrival_work'])  # HHMM
        self.arrival_home = float(ev_dict['arrival_home'])  # HHMM
        self.work_duration = float(ev_dict['work_duration'])  # seconds
        self.home_duration = float(ev_dict['home_duration'])  # seconds
        self.leaving_home = fg.add_hhmm_secs(self.arrival_home, self.home_duration)  # HHMM
        self.slider = float(ev_dict['slider_setting'])
        self.boundary_cond = ev_dict['boundary_cond']
        # calculate boundary condition for minimum charge before leaving home
        if self.boundary_cond == 'full':
            self.home_depart_soc = self.Cmax
        elif self.boundary_cond == 'just_enough':
            self.home_depart_soc = (self.travel_miles / self.mileage) * (1 + 0.2)  # 20% margin
        elif self.boundary_cond == 'slider_based':
            just_enough_soc = (self.travel_miles / self.mileage)
            just_enough_soc = min(just_enough_soc * (1 + 0.2), self.Cmax)
            self.home_depart_soc = self.Cmax + (just_enough_soc - self.Cmax) * self.slider

        self.period = 300
        # made constant
        self.new_opt = True
        if self.new_opt:
            self.batteryLifeDegFactor = float(0.008)
        else:
            self.batteryLifeDegFactor = float(0.025) * 0.001  # float(0.002)#float(0.025)

        self.windowLength = int(48)
        self.dayAheadCapacity = float(100)
        self.non_trans_hours = []  # collecting non transactive hours for an ev with respect to the current hour
        self.trans_hours = []  # # collecting transactive hours for an ev with respect to the current hour
        self.home_depart_hours = []  # collecting home departure hours with respect to current hour
        self.home_arrival_hours = []  # collecting home arrival hours with respect to current hour
        # no initialization required
        self.bidSpread = int(1)
        self.quad_fac = 0.0001  # quadratic term coefficient in optimizaion objective
        self.P = int(1)
        self.Q = int(0)
        self.f_DA = [0.06] * self.windowLength

        # interpolation
        self.interpolation = bool(True)
        self.RT_minute_count_interpolation = float(0.0)
        self.previous_Q_RT = float(0.0)
        self.delta_Q = float(0.0)
        # self.previous_Q_DA = float(0.0)

        # price vector to initialize and to be used in the first optimization
        self.RTprice = 0.0
        self.profit_margin = float(ev_dict['profit_margin']) / 100
        self.RT_state_maintain = bool(False)
        self.RT_state_maintain_flag = int(0)
        self.RT_flag = bool(False)
        self.inv_P_setpoint = float(0.0)
        self.inv_Q_setpoint = float(0.0)
        self.optimized_Quantity = [[]] * self.windowLength
        # not used if not biding DA
        self.prev_clr_Quantity = list()
        self.prev_clr_Price = list()
        self.BindingObjFunc = bool(False)

        self.bid_rt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
        self.bid_da = [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]] for _ in range(self.windowLength)]

        # optimization
        self.TIME = range(0, self.windowLength)

        # Sanity checks:
        if self.Cmin <= self.evCapacity <= self.Cmax:
            # log.info('Cmin < evCapacity < Cmax.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- evCapacity is {}, not between Cmin ({}) and Cmax ({})'.
                    format(self.name, 'init', self.evCapacity, self.Cmin, self.Cmax))

        Lin_lower = 0
        Lin_upper = 1
        if 0 < self.Lin < 1:
            # log.info('Lin is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Lin is {}, outside of nominal range of {} to {}'.
                    format(self.name, 'init', self.Lin, Lin_lower, Lin_upper))

        Lout_lower = 0
        Lout_upper = 1
        if 0 < self.Lout < 1:
            # log.info('Lout is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Lout is {}, outside of nominal range of {} to {}'.
                    format(self.name, 'init', self.Lout, Lout_lower, Lout_upper))

        reserved_soc_lower = 0
        reserved_soc_upper = 1
        if reserved_soc_lower < self.reserved_soc < reserved_soc_upper:
            # log.info('reserved_soc is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- reserved_soc is {}, outside of nominal range of {} to {}'.
                    format(self.name, 'init', self.reserved_soc, reserved_soc_lower, reserved_soc_upper))

        # if 0 < self.batteryLifeDegFactor < 1:
        #     # log.info('batteryLifeDegFactor is within the bounds.')
        #     pass
        # else:
        #     log.log(model_diag_level, '{} {} -- batteryLifeDegFactor is out of bounds.'.
        #             format(self.name, 'init'))

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
        return self.RT_flag

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
            self.prev_clr_Quantity.append(self.from_P_to_Q_ev(self.bid_da[i], self.prev_clr_Price[i]))
        self.prev_clr_Price.pop(0)
        self.prev_clr_Quantity.pop(0)
        self.prev_clr_Price.append(0.0)
        self.prev_clr_Quantity.append(0.0)

    def formulate_bid_da(self):
        """ Formulate 4 points of P and Q bids for the DA market

        Function calls "DA_optimal_quantities" to obtain the optimal quantities
        for the DA market. With the quantities, the 4 point bids are formulated.

        Before returning the BID the function resets "RT_state_maintain_flag"
        wich if RT_state_maintain is TRUE the battery will be forced to keep its
        state (i.e., charging or discharging).

        Returns:
            BID (float) (((1,2)X4) X windowLength): store last DA market bids
        """
        #        Quantity = self.DA_optimal_quantities()
        Quantity = deepcopy(self.optimized_Quantity)

        P = self.P
        Q = self.Q
        # previous hour quantity
        # self.previous_Q = self.bid_da[0][1][Q]

        TIME = range(0, self.windowLength)
        CurveSlope = [0] * len(TIME)
        yIntercept = [-1] * len(TIME)
        BID = [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]] for _ in TIME]
        deltaf_DA = max(self.f_DA) - min(self.f_DA)

        for t in TIME:
            # CurveSlope[t] = ((max(self.f_DA)-min(self.f_DA))/(-self.Rd-self.Rc))*(1 + self.ProfitMargin_slope/100)   #Remains same in all hours of the window
            if self.slider != 0:
                # check if non transactive hours: make an inflexible straight verticle line bid
                if t in self.non_trans_hours:
                    BID[t][0][Q] = Quantity[t]
                    BID[t][1][Q] = Quantity[t]
                    BID[t][2][Q] = Quantity[t]
                    BID[t][3][Q] = Quantity[t]

                    BID[t][0][P] = max(self.f_DA)
                    BID[t][1][P] = self.f_DA[t]
                    BID[t][2][P] = self.f_DA[t]
                    BID[t][3][P] = min(self.f_DA)
                else:
                    # Remains same in all hours of the window
                    CurveSlope[t] = ((max(self.f_DA) - min(self.f_DA)) / (-self.Rd - self.Rc)) / self.slider
                    # print(CurveSlope[t])
                    # print(Quantity[t])
                    # Is different for each hour of the window
                    yIntercept[t] = self.f_DA[t] - CurveSlope[t] * Quantity[t]

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
            else:
                # if slider is 0: inflexible straight vertical bid
                BID[t][0][Q] = Quantity[t]
                BID[t][1][Q] = Quantity[t]
                BID[t][2][Q] = Quantity[t]
                BID[t][3][Q] = Quantity[t]

                BID[t][0][P] = max(self.f_DA)
                BID[t][1][P] = self.f_DA[t]
                BID[t][2][P] = self.f_DA[t]
                BID[t][3][P] = min(self.f_DA)

        self.bid_da = deepcopy(BID)

        self.RT_state_maintain_flag = 0
        self.RT_minute_count_interpolation = float(0.0)

        return self.bid_da

    def obj_rule(self, m):
        if self.new_opt:
            return sum(
                self.slider * self.f_DA[i] * (m.E_DA_out[i] - m.E_DA_in[i])
                - self.slider * self.batteryLifeDegFactor * (1 + self.profit_margin) * (m.E_DA_out[i] + m.E_DA_in[i])
                - self.quad_fac * (m.E_DA_out[i] + m.E_DA_in[i]) ** 2 for i in self.TIME) \
                   - sum((1 - self.slider) * 0.001 * (self.home_depart_soc - m.C[i]) for i in self.trans_hours)
            # - sum(100000 * (self.Cmax - m.C[i]) for i in range(self.TIME.stop - 24, self.TIME.stop))
            # The last line is to enforce 100% charging during the last day of the simulation and should be removed in 48-hour windowlength optimization
        return sum(
            self.f_DA[i] * (m.E_DA_out[i] - m.E_DA_in[i]) - 0 * self.batteryLifeDegFactor * (1 + self.profit_margin)
            * (m.E_DA_out[i] + m.E_DA_in[i]) - 0.001 * (m.E_DA_out[i] + m.E_DA_in[i]) ** 2 for i in self.TIME)
        # - 0.0000003*(m.E_DA_out[i]+m.E_DA_in[i])**2

    def con_rule_ine1(self, m, i):
        if i in self.trans_hours:
            return m.E_stor_out[i] <= (self.dayAheadCapacity / 100) * self.Rd / self.bidSpread
        else:
            return m.E_stor_out[i] == 0

    def con_rule_ine2(self, m, i):
        if i in self.trans_hours:
            return m.E_stor_in[i] <= (self.dayAheadCapacity / 100) * self.Rc / self.bidSpread
        else:
            return m.E_stor_in[i] == 0

    def con_rule_eq1(self, m, i):
        return m.E_DA_out[i] == m.E_stor_out[i] * (1 - (self.Lout / 100))

    def con_rule_eq2(self, m, i):
        return m.E_DA_in[i] == m.E_stor_in[i] * (1 / (1 - (self.Lin / 100)))

    def con_rule_eq3(self, m, i):
        # let's just drain the driving soc only at the departure from home hour
        if i in self.home_depart_hours:
            if i == 0:
                return m.C[i] == self.Cinit - self.travel_miles / self.mileage
            else:
                return m.C[i] == m.C[i - 1] - self.travel_miles / self.mileage
        else:
            if i == 0:
                return m.C[i] == self.Cinit - m.E_stor_out[i] + m.E_stor_in[i]
            else:
                return m.C[i] == m.C[i - 1] - m.E_stor_out[i] + m.E_stor_in[i]

    def con_rule_eq4(self, m, i):
        # boundary condition: 100% soc before leaving house
        return m.C[i - 1] >= self.home_depart_soc

    def DA_model_parameters(self, sim_time):
        sim_time = sim_time + timedelta(0, 60)  # adjust for 60 seconds
        # objective is to collect transactive hours when car is at home. If car is at home for a partial hour, that is
        # not counted as transactive
        self.trans_hours = []
        self.non_trans_hours = []
        for i in self.TIME:
            cur_hour = sim_time.hour + i
            # let's get seconds from midnight
            cur_secs = fg.get_secs_from_HHMM(round((cur_hour % 24) * 100))
            # if the car is at home for full hour (3600 seconds), then consider it a transactive hour, otherwise not
            if self.get_car_home_duration(cur_secs, 3600) == 3600:
                self.trans_hours.append(i)
            else:
                self.non_trans_hours.append(i)

        # home departure hours: hours just after transactive full hours ends at home departure
        self.home_depart_hours = [self.non_trans_hours[0], self.non_trans_hours[0] + 24]
        # home arrival hours: hours just before transactive full hour starts on home arrival
        self.home_arrival_hours = [self.non_trans_hours[-1] - 24, self.non_trans_hours[-1]]
        # print('updating home depart hours:', self.home_depart_hours)

    def DA_optimal_quantities(self):
        """ Generates Day Ahead optimized quantities for EV

        Returns:
            Quantity (float) (1 x windowLength): Optimal quantity from optimization for all hours of the window specified by windowLength
        """
        if self.Cinit > self.Cmax:
            self.Cinit = self.Cmax
        if self.Cinit < self.Cmin:
            self.Cinit = self.Cmin

        model = pyo.ConcreteModel()
        model.E_DA_out = pyo.Var(self.TIME, bounds=(0, self.Rd * 2))
        model.E_DA_in = pyo.Var(self.TIME, bounds=(0, self.Rc * 2))
        model.E_stor_out = pyo.Var(self.TIME, bounds=(0, self.Rd))
        model.E_stor_in = pyo.Var(self.TIME, bounds=(0, self.Rc))
        model.C = pyo.Var(self.TIME, bounds=(self.Cmin, self.Cmax))

        model.obj = pyo.Objective(rule=self.obj_rule, sense=pyo.maximize)
        model.con1 = pyo.Constraint(self.TIME, rule=self.con_rule_ine1)
        model.con2 = pyo.Constraint(self.TIME, rule=self.con_rule_ine2)
        model.con3 = pyo.Constraint(self.TIME, rule=self.con_rule_eq1)
        model.con4 = pyo.Constraint(self.TIME, rule=self.con_rule_eq2)
        model.con5 = pyo.Constraint(self.TIME, rule=self.con_rule_eq3)
        # do not create following constraint (boundary condition) when departing hour is 0th. In this case, Cinit should take care of it.
        # get non-zero values
        nz_home_depart = [val for idx, val in enumerate(self.home_depart_hours) if val != 0]
        model.con6 = pyo.Constraint(nz_home_depart, rule=self.con_rule_eq4)

        # print('home depart hours: ', self.home_depart_hours)
        # print('day_ahead_price_forcast...', self.f_DA)
        results = get_run_solver('ev_' + self.name, pyo, model, self.solver)
        # print('*** optimization model ***:')
        # print(model.pprint())
        # print('ev objective function is ', pyo.value(model.obj))

        soc = [0] * len(self.TIME)
        Quantity = [0] * len(self.TIME)
        TOL = 0.00001  # Tolerance for checking bid
        for t in self.TIME:
            # if pyo.value(model.E_DA_in[t]) > TOL:
            #     Quantity[t] = pyo.value(model.E_DA_in[t])  # For logging
            # if pyo.value(model.E_DA_out[t]) > TOL:
            #     Quantity[t] = pyo.value(-model.E_DA_out[t])

            # following is a better implementation as the above implementation create issues and stores
            # wrong value
            Quantity[t] = pyo.value(model.E_DA_in[t] - model.E_DA_out[t])
            soc[t] = pyo.value(model.C[t]) / self.evCapacity

        # fig, (ax1, ax2, ax3) = plt.subplots(3,1, sharex=True)
        # ax1.plot(Quantity)
        # ax1.set_ylabel('kW')
        # ax2.plot(soc)
        # ax2.set_ylabel('SOC')
        # ax3.plot(self.f_DA)
        # ax3.set_ylabel('$/kWh')
        return Quantity  # , soc

    def formulate_bid_rt(self):
        """ Formulates RT bid

        Uses the last 4 point bid from DA market and consider current state
        of charge of the ev. Will change points to change points for feasible
        range of Qmin Qmax points if necessary. Furthermore, allows a maximum
        deviation of +/-100% from the DA plan.

        Returns:
            realTimeBid (float) ((1,2) x 4):  bid in Real Time market
        """
        P = self.P
        Q = self.Q
        BID = deepcopy(self.bid_da[0])

        # First thing first:
        # make sure that the real time bid has exact same quantity as day ahead bid during
        # non-transactional hours for EV i.e. 0 quantity
        if 0 in self.non_trans_hours:
            self.bid_rt = BID
            self.previous_Q_RT = 0.0
            return self.bid_rt

        # start interpolation
        if self.interpolation:
            CurveSlope = ((max(self.f_DA) - min(self.f_DA)) / (-self.Rd - self.Rc)) / self.slider
            yIntercept = self.f_DA[0] - CurveSlope * BID[1][Q]
            if self.RT_minute_count_interpolation == 0.0:
                self.delta_Q = deepcopy((self.bid_da[0][1][Q] - self.previous_Q_RT))
            if self.RT_minute_count_interpolation == 30.0:
                self.delta_Q = deepcopy((self.bid_da[1][1][Q] - self.previous_Q_RT) * 0.5)
            Qopt_DA = self.previous_Q_RT + self.delta_Q * (5.0 / 30.0)
            # Qopt_DA = self.bid_da[0][1][Q]*(self.RT_minute_count_interpolation/60.0) + self.previous_Q*(1-self.RT_minute_count_interpolation/60.0)
            self.previous_Q_RT = Qopt_DA
            BID[1][Q] = Qopt_DA
            BID[2][Q] = Qopt_DA
            BID[0][P] = -self.Rd * CurveSlope + yIntercept + self.batteryLifeDegFactor * (1 + self.profit_margin)
            BID[1][P] = Qopt_DA * CurveSlope + yIntercept + self.batteryLifeDegFactor * (1 + self.profit_margin)
            BID[2][P] = Qopt_DA * CurveSlope + yIntercept - self.batteryLifeDegFactor * (1 + self.profit_margin)
            BID[3][P] = self.Rc * CurveSlope + yIntercept - self.batteryLifeDegFactor * (1 + self.profit_margin)
        # end interpolation
        # identify error start
        state = 0
        t = self.period
        t = t / (60 * 60)  # hour
        if (self.Cinit + BID[3][Q] * t) > self.Cmax:
            state = state + 1
        if (self.Cinit + BID[0][Q] * t) < self.Cmin:
            state = state + 2
        # identify error end

        # fix 4 point error if exixtent start
        if state >= 3:
            print("EV Error --> Verify EV battery RC, RD, and evCapacity")
            print(self.Rc)
            print(self.Rd)
            print(self.evCapacity)

        if state == 0:  # no error
            realTimeBid = BID
        else:  # fixing error
            if state == 1:  # fixing error type 1
                x = max(0.0, self.Cmax - self.Cinit)
                x = x / t  # to W
                realTimeBid = self.RT_fix_four_points_range(BID, BID[0][Q], x)
            if state == 2:  # fixing error type 2
                x = min(0.0, self.Cmin - self.Cinit)
                x = x / t  # to W
                realTimeBid = self.RT_fix_four_points_range(BID, x, BID[3][Q])
        # fix 4 point error if exixtent end

        # force charging or discharging for the hour start
        if self.RT_state_maintain and self.RT_state_maintain_flag != 0:
            if self.RT_state_maintain_flag < 0:
                realTimeBid = self.RT_fix_four_points_range(realTimeBid, 0.0, float('inf'))
            else:
                realTimeBid = self.RT_fix_four_points_range(realTimeBid, -float('inf'), 0.0)
        # force charging or discharging for the hour end

        excursion = self.Rd * 1.0  # 100% of all excursion
        E_realTimeBid = self.RT_fix_four_points_range(realTimeBid, realTimeBid[1][Q] - excursion,
                                                      realTimeBid[1][Q] + excursion)
        self.bid_rt = deepcopy(E_realTimeBid)

        self.RT_minute_count_interpolation = self.RT_minute_count_interpolation + 5.0
        return self.bid_rt

    def RT_fix_four_points_range(self, BID, Ql, Qu):
        """ Verify feasible range of RT bid

        Args:
            BID (float) ((1,2)X4): 4 point bid
            Ql: 
            Qu: 

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

        if isnan(m) and temp == 0:
            try:
                m = (BID[2][P] - BID[3][P]) / (BID[2][Q] - BID[3][Q])  # y = m*x + b
            except:
                temp = 1

        if isnan(m):
            temp = 1

        if temp == 0:
            b0 = BID[0][P] - BID[0][Q] * m
            b1 = BID[3][P] - BID[3][Q] * m

            BIDr = deepcopy(BID)

            flag = [1] * len(BID)
            for n in range(0, len(BID)):
                if Ql <= BID[n][Q] <= Qu:
                    flag[n] = 0
                else:
                    if BID[n][Q] > Qu:
                        BIDr[n][Q] = Qu
                    elif BID[n][Q] < Ql:
                        BIDr[n][Q] = Ql
            if sum(flag) == 0:
                # when flags are set to zero the fix function has passed the test
                pass
            else:
                BIDr[0][P] = m * BIDr[0][Q] + b0
                BIDr[1][P] = m * BIDr[1][Q] + b0
                BIDr[2][P] = m * BIDr[2][Q] + b1
                BIDr[3][P] = m * BIDr[3][Q] + b1
        else:
            BIDr = BID

        return BIDr

    def RT_gridlabd_set_P(self, model_diag_level, sim_time):
        """ Update variables for ev output "inverter"

        Args:
            model_diag_level (int): Specific level for logging errors; set it to 11
            sim_time (str): Current time in the simulation; should be human-readable

        inv_P_setpoint is a float in W
        """
        realTimeBid = deepcopy(self.bid_rt)
        invPower = self.from_P_to_Q_ev(realTimeBid, self.RTprice)

        if invPower < 0:
            self.RT_state_maintain_flag = -1
        elif invPower > 0:
            self.RT_state_maintain_flag = 1

        # always dispatch ev charge set-point even if there is no change from previous set-point
        # because if nothing is sent, ev starts charging with its default value
        self.inv_P_setpoint = invPower * 1000.0
        self.RT_flag = True
        # if (invPower - self.inv_P_setpoint) != 0.0:
        #     self.inv_P_setpoint = invPower * 1000.0
        #     self.RT_flag = True
        # else:
        #     self.RT_flag = False

        # Sanity checks
        # self.Rd seems to be 0
        # if self.inv_P_setpoint <= self.Rd * 1000:
        #     pass
        # else:
        #     log.log(model_diag_level, '{} {} -- output power ({}) is not <= rated output power ({}).'.
        #             format(self.name, sim_time, self.inv_P_setpoint, self.Rd))

        if self.inv_P_setpoint >= -self.Rc * 1000:
            pass
        else:
            log.log(model_diag_level, '{} {} -- input power ({}) is not <= rated input power ({}).'.
                    format(self.name, sim_time, -self.inv_P_setpoint, self.Rc))

    def set_ev_SOC(self, msg_str, model_diag_level, sim_time):
        """ Set the ev state of charge

        Updates the self.Cinit of the battery

        Args:
             msg_str (str): message with ev SOC in percentage
             model_diag_level (int): Specific level for logging errors; set it to 11
             sim_time (str): Current time in the simulation; should be human-readable

        """
        val = parse_number(msg_str)
        self.Cinit = self.evCapacity / 100 * val

        if self.Cmin < self.Cinit < self.Cmax:
            pass
        else:
            log.log(model_diag_level, '{} {} -- SOC ({}) is not between Cmin ({}) and Cmax ({}).'.
                    format(self.name, sim_time, self.Cinit, self.Cmin, self.Cmax))

    def is_car_home(self, cur_secs):
        """
        return boolean if car is at home at cur_secs
        :param cur_secs: current time in seconds
        :return: True or False
        """
        arr_sec = fg.get_secs_from_HHMM(self.arrival_home)
        leav_sec = fg.get_secs_from_HHMM(self.leaving_home)
        if arr_sec > leav_sec:  # overnight at home (midnight crossing)
            if cur_secs >= arr_sec or cur_secs < leav_sec:
                return True
            else:
                return False
        elif arr_sec < leav_sec:
            if arr_sec <= cur_secs < leav_sec:
                return True
            else:
                return False
        else:
            raise UserWarning('Something is wrong! home arrival and leaving time are same')

    def is_car_leaving_home(self, cur_secs, interval):
        """
        tells if car is leaving from home during the given 'interval' seconds starting from cur_secs
        :param cur_secs: (seconds) current (starting) time with reference of midnight as 0
        :param interval: (seconds) duration in which status needs to be estimated
        :return: True or False
        """
        interval_beg_hhmm = fg.get_HHMM_from_secs(cur_secs)
        interval_end_hhmm = fg.add_hhmm_secs(interval_beg_hhmm, interval)
        if interval_beg_hhmm < interval_end_hhmm:
            if interval_beg_hhmm <= self.leaving_home < interval_end_hhmm:
                return True
        else:
            if interval_beg_hhmm <= self.leaving_home or self.leaving_home < interval_end_hhmm:
                return True
        return False

    def get_car_home_duration(self, cur_secs, interval):
        """
        return the duration of car at home during the given 'interval' seconds starting from cur_secs
        :param cur_secs: (seconds) current (starting) time with reference of midnight as 0
        :param interval: (seconds) duration in which status needs to be estimated
        :return: duration in seconds for which car is at home in given interval
        """
        interval_beg_hhmm = fg.get_HHMM_from_secs(cur_secs)
        interval_end_hhmm = fg.add_hhmm_secs(interval_beg_hhmm, interval)
        arr_sec = fg.get_secs_from_HHMM(self.arrival_home)
        leav_sec = fg.get_secs_from_HHMM(self.leaving_home)
        if self.is_car_home(cur_secs):  # car at home in the beginning of interval
            rem_home_sec = fg.get_duration(interval_beg_hhmm,
                                           self.leaving_home)  # how long car will be home
            duration = min(interval, rem_home_sec)  # if remaining duration is more than interval, return interval
        elif cur_secs + interval > arr_sec:  # if car is coming home during this interval
            rem_home_sec = fg.get_duration(self.arrival_home, interval_end_hhmm)  # how long car will be home
            duration = min(self.home_duration, rem_home_sec)
        else:  # car is not home at all during this interval
            duration = 0
        return duration

    def get_uncntrl_ev_load(self, sim_time):
        """
        returns 48-hour forecast of ev load in base case w/o optimization
        :return:
        """
        sim_time = sim_time + timedelta(0, 60)  # adjust for 60 seconds shift
        # let's get seconds from midnight
        cur_secs = fg.get_secs_from_HHMM(round(sim_time.hour * 100 + sim_time.minute))
        Quantity = []
        dt = 1  # delta time is 1 hour here
        cur_cap_pr = self.Cinit
        for _ in self.TIME:
            car_home_dur = self.get_car_home_duration(cur_secs, dt * 3600)  # car at home duration
            cur_cap = cur_cap_pr + self.Rc * car_home_dur / 3600 * self.Lin  # increment in soc
            if cur_cap > self.evCapacity:  # if soc >100%
                cur_cap = self.evCapacity
            avg_kw = (cur_cap - cur_cap_pr) / self.Lin / dt  # average kW consumption during dt interval
            # now lets check if car is leaving home during this interval
            if self.is_car_leaving_home(cur_secs, dt * 3600):
                cur_cap = cur_cap - self.travel_miles / self.mileage
                # no impact on avg_kw, discharging only impacts soc
            cur_cap_pr = cur_cap
            cur_secs = (cur_secs + dt * 3600) % (24 * 3600)
            Quantity.append(avg_kw)
        return Quantity

    def from_P_to_Q_ev(self, BID, PRICE):
        """ Convert the 4 point bids to a quantity with the known price

        Args:
            BID (float) ((1,2)X4): 4 point bid
            PRICE (float): cleared price in $/kWh

        Returns:
            _quantity (float): active power (-) charging (+) discharging
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

        if isnan(m) and temp == 0:
            try:
                m = (BID[2][P] - BID[3][P]) / (BID[2][Q] - BID[3][Q])  # y = m*x + b
            except:
                temp = 1

        if isnan(m):
            temp = 1

        if temp == 0:
            if PRICE >= BID[0][P]:  # battery at maximum discharge
                _quantity = -BID[0][Q]
            elif PRICE <= BID[3][P]:  # battery at maximum charging
                _quantity = -BID[3][Q]
            elif BID[2][P] <= PRICE <= BID[1][P]:  # battery at deadband
                _quantity = -BID[2][Q]
            elif BID[1][P] <= PRICE <= BID[0][P]:  # first curve
                b = BID[1][P] - BID[1][Q] * m
                _quantity = -1 * ((PRICE - b) / m)
            else:
                b = BID[3][P] - BID[3][Q] * m
                _quantity = -1 * ((PRICE - b) / m)
        else:
            _quantity = -BID[1][Q]

        return -_quantity


def test():
    """Testing
    
    Makes a single battery agent and run DA 
    """
    import time
    import matplotlib.pyplot as plt

    start_time = time.time()
    price_DA = np.array([0.43, 0.41, 0.40, 0.39, 0.39, 0.40, 0.45, 0.45, 0.55, 0.80, 0.90, 0.98,
                         0.99, 1.00, 1.00, 0.99, 0.98, 0.97, 0.97, 0.90, 0.70, 0.60, 0.55, 0.45,
                         0.43, 0.41, 0.40, 0.39, 0.39, 0.40, 0.45, 0.45, 0.55, 0.80, 0.90, 0.98,
                         0.99, 1.00, 1.00, 0.99, 0.98, 0.97, 0.97, 0.90, 0.70, 0.60, 0.55, 0.45]) * 10

    price_DA = np.array(
        [0.06897900863505242, 0.06899625979446107, 0.06910247955200355, 0.0704370951988276, 0.07129477973762785,
         0.07575951709047649, 0.07867076652772478, 0.08500110468217234, 0.08605250995052553, 0.08739160065839066,
         0.08570718464173825, 0.08851981199574613, 0.08863781631784831, 0.09447350866370237, 0.08962951492105627,
         0.09368121477049049, 0.0946303143215198, 0.08701268341596821, 0.08329811267952396, 0.07972225236970293,
         0.07386294250071271, 0.07114607005236842, 0.07040294355115773, 0.06911552928900337, 0.06913064241856061,
         0.06924874047665536, 0.06958132018224389, 0.07106888284617383, 0.07183627174401977, 0.07606953642048492,
         0.07906218312697474, 0.08447094680504955, 0.08397642193853444, 0.08388811476864988, 0.08419683094662397,
         0.08398391354258788, 0.08449706519737217, 0.0886170498098241, 0.08939221214102161, 0.09403379325036935,
         0.09530432239251008, 0.08745550629354258, 0.0826892710140738, 0.07890014700979571, 0.07347431077469634,
         0.071103484293844, 0.07037724443846943, 0.12074403324144026])

    glm = {
        "name": "R5_12_47_2_tn_1_ev_1",
        "feeder_id": "R5_12.47_2",
        "billingmeter_id": "R5_12_47_2_tn_1_mtr_1",
        "parent": "R5_12_47_2_tn_1_hse_1",
        "work_charging": "FALSE",
        "battery_SOC": "100",
        "max_charge": 3300.0,
        "daily_miles": 40.527,
        "arrival_work": 1400,
        "arrival_home": 1840,
        "work_duration": 15000.0,
        "home_duration": 67800.0,
        "miles_per_kwh": 3.333,
        "range_miles": 151.0,
        "efficiency": 0.9
    }
    agent = {"evName": "R5_12_47_2_tn_1_ev_1",
             "meterName": "R5_12_47_2_tn_1_mtr_1",
             "work_charging": "FALSE",
             "boundary_cond": 'just_enough',
             "initial_soc": "100",
             "max_charge": 3300.0,
             "daily_miles": 40.527,
             "arrival_work": 1400,
             "arrival_home": 1840,
             "work_duration": 15000.0,
             "home_duration": 67800.0,
             "miles_per_kwh": 3.333,
             "range_miles": 151.0,
             "efficiency": 0.9,
             "slider_setting": 0.5119,
             "profit_margin": 12.321,
             "participating": True
             }
    agent = {
        "evName": "R5_12_47_2_tn_38_ev_1",
        "meterName": "R5_12_47_2_tn_38_mtr_1",
        "work_charging": "FALSE",
        "boundary_cond": "full",
        "initial_soc": 40.0,
        "max_charge": 11500.0,
        "daily_miles": 0.111,
        "arrival_work": 730,
        "arrival_home": 800,
        "work_duration": 1.0,
        "home_duration": 82799.0,
        "miles_per_kwh": 3.333,
        "range_miles": 285.0,
        "efficiency": 0.9,
        "slider_setting": 0.5395,
        "profit_margin": 10.0,
        "degrad_factor": 0.0227,
        "participating": True,
        "ev_mode": "V1G"
    }
    agent = {"evName": "R5_12_47_2_tn_67_ev_1", "meterName": "R5_12_47_2_tn_67_mtr_1", "work_charging": "FALSE",
             "boundary_cond": "full", "ev_mode": "V1G", "initial_soc": 99.0, "max_charge": 11500.0,
             "daily_miles": 212.444, "arrival_work": 1303, "arrival_home": 1936, "work_duration": 21780.0,
             "home_duration": 61020.0, "miles_per_kwh": 3.846, "range_miles": 220.0, "efficiency": 0.9,
             "slider_setting": 0.6271, "profit_margin": 10.5928, "degrad_factor": 0.0227, "participating": True}

    # checking uncontrollable load forecast for EV
    start_time = '2016-07-05 00:59:00'
    time_format = '%Y-%m-%d %H:%M:%S'
    sim_time = datetime.strptime(start_time, time_format)
    B_obj1 = EVDSOT(agent, glm, 'test', 11, sim_time, 'ipopt')  # make object; add model_diag_level and sim_time
    # quant = B_obj1.get_uncntrl_ev_load(sim_time)
    # ---------------------------------------

    B_obj1.RTprice = 0.09173832932121798
    B_obj1.bid_rt = [
        [
            -11.5,
            0.12306011120028475
        ],
        [
            -8.7623912741047,
            0.09548232146757012
        ],
        [
            -8.7623912741047,
            0.0948369664675701
        ],
        [
            0.047200720071884916,
            0.006091970388207173
        ]
    ]
    B_obj1.RT_gridlabd_set_P(11, sim_time)
    # checking optimization
    opt = []
    soc_opt = []
    # B_obj1.f_DA = np.array([0.06897900863505242, 0.06899625979446107, 0.06910247955200355, 0.0704370951988276, 0.07129477973762785, 0.07575951709047649, 0.07867076652772478, 0.08500110468217234, 0.08605250995052553, 0.08739160065839066, 0.08570718464173825, 0.08851981199574613, 0.08863781631784831, 0.09447350866370237, 0.08962951492105627, 0.09368121477049049, 0.0946303143215198, 0.08701268341596821, 0.08329811267952396, 0.07972225236970293, 0.07386294250071271, 0.07114607005236842, 0.07040294355115773, 0.06911552928900337, 0.06913064241856061, 0.06924874047665536, 0.06958132018224389, 0.07106888284617383, 0.07183627174401977, 0.07606953642048492, 0.07906218312697474, 0.08447094680504955, 0.08397642193853444, 0.08388811476864988, 0.08419683094662397, 0.08398391354258788, 0.08449706519737217, 0.0886170498098241, 0.08939221214102161, 0.09403379325036935, 0.09530432239251008, 0.08745550629354258, 0.0826892710140738, 0.07890014700979571, 0.07347431077469634, 0.071103484293844, 0.07037724443846943, 0.12074403324144026])
    # B_obj1.Cinit = 57.2
    # B_obj1.DA_model_parameters(sim_time)
    # quantity = B_obj1.DA_optimal_quantities()
    for t in range(1):
        sim_time = sim_time + timedelta(0, 3600)
        B_obj1.set_price_forecast(np.roll(price_DA, -t).tolist())
        B_obj1.DA_model_parameters(sim_time)
        # quantity, soc = B_obj1.DA_optimal_quantities()
        quantity = B_obj1.DA_optimal_quantities()
        opt.append(quantity[0])
        # soc_opt.append(soc[0])
        B_obj1.optimized_Quantity = quantity
        # B_obj1.set_ev_SOC(str(soc[0]*100),11,sim_time)
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True)
    ax1.plot(quantity)
    ax1.set_ylabel('kW')
    # ax2.plot(soc)
    ax2.set_ylabel('SOC')
    ax3.plot(price_DA)
    plt.show()
    B_obj1.optimized_Quantity = quantity
    BIDS = B_obj1.formulate_bid_da()
    rtbid1 = B_obj1.formulate_bid_rt()
    rtbid2 = [
        [
            -11.5,
            0.12306011120028475
        ],
        [
            -8.7623912741047,
            0.09548232146757012
        ],
        [
            -8.7623912741047,
            0.0948369664675701
        ],
        [
            0.047200720071884916,
            0.006091970388207173
        ]
    ]
    rtbid3 = [
        [
            -8.762,
            0.12306011120028475
        ],
        [
            -8.762,
            0.09548232146757012
        ],
        [
            -8.762,
            0.0948369664675701
        ],
        [
            -8.762,
            0.006091970388207173
        ]
    ]
    getQ = B_obj1.from_P_to_Q_ev(rtbid2, 0.09)
    print(getQ)

    B_obj1.bid_da = [
        [
            0,
            0.0743013676189316
        ],
        [
            0.06734323132493447,
            0.07370466477512573
        ],
        [
            0.06734323132493447,
            0.07364650382512573
        ],
        [
            11.5,
            -0.02765393382700894
        ]
    ]

    # interpolation test
    Q = B_obj1.Q
    Q_true_time_RT = list()
    Q_true_time_DA = list()
    first_run = True
    B_obj1.Cinit = 20.0
    # B_obj1.Cmax
    # B_obj1.Cmin
    for hour in range(24):
        print('')
        if first_run:
            first_run = False
            B_obj1.set_price_forecast(price_DA.tolist())
            quantity = B_obj1.DA_optimal_quantities()
        else:
            price_DA = np.roll(price_DA, -1)
            quantity = np.roll(quantity, -1)
            sim_time = sim_time + timedelta(0, 3600)
            B_obj1.DA_model_parameters(sim_time)

        B_obj1.set_price_forecast(price_DA.tolist())
        B_obj1.optimized_Quantity = quantity

        bid_DA = B_obj1.formulate_bid_da()
        print(bid_DA[0][1][Q])
        print('')

        for i in range(12):
            bid_RT = B_obj1.formulate_bid_rt()
            # print(B_obj1.non_trans_hours)
            print(bid_RT[1][Q])
            Q_true_time_RT.append(bid_RT[1][Q])
            Q_true_time_DA.append(bid_DA[0][1][Q])

    plt.rcParams['figure.figsize'] = (8, 5)
    plt.rcParams['figure.dpi'] = 500
    plt.rcParams['axes.grid'] = True
    plt.plot(Q_true_time_RT, label='RT')
    plt.plot(Q_true_time_DA, label='DA')
    for i in range(0, 25 * 12, 12):
        plt.axvline(i, color='red', linewidth=0.3)
    plt.legend()
    plt.ylabel('Quantity (kW)')
    plt.xlabel('Time (minuts)')
    plt.show()

    # BID = [[-5.0, 0.42129778616103297], [-0.39676675, 0.30192681471917215], [-0.39676675, 0.17229206883635942],
    #        [5.0, 0.03234319929066909]]
    #
    # B_obj1.set_price_forecast(price_DA.tolist())
    # # quantity = B_obj1.DA_optimal_quantities()
    # # B_obj1.optimized_Quantity = quantity
    # # BIDS = B_obj1.formulate_bid_da()
    # # print("--- %s seconds ---" % (time.time() - start_time))
    # # #    B = B_obj1.RT_fix_four_points_range(BID,0.2920860000000012,5.0)
    # # #    A = B_obj1.RT_fix_four_points_range(B,0.2920860000000012,0.2920860000000012)
    # # #    B_obj2 = BatteryDSOT(agent,glm,'test')# make object
    # #
    # # B_obj1.Cinit = agent['capacity'] / 1000 * 0.99
    # # rtbid = B_obj1.formulate_bid_rt()
    # # price_forecast = B_obj1.f_DA
    # # BIDS_of_agent = B_obj1.bid_da
    # # # B_obj.Cinit = B_obj.evCapacity * 0.5#B_obj.set_battery_SOC()
    # # BID = [[-5.0, 6.0], [0.0, 5.0], [0.0, 4.0], [5.0, 3.0]]
    # # fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, 10.0)
    # # print(fixed)
    # # fixed = B_obj1.RT_fix_four_points_range(BID, -float('inf'), 0.0)
    # # print(fixed)
    # # fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, float('inf'))
    # # print(fixed)
    # # fixed = B_obj1.RT_fix_four_points_range(BID, 0.5, 0.5)
    # # print(fixed)
    # # getQ = B_obj1.from_P_to_Q_battery(BID, 10)
    # # print(getQ)
    # # getQ = B_obj1.from_P_to_Q_battery(fixed, 10)
    # # print(getQ)


if __name__ == "__main__":
    test()
