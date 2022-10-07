# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: water_heater_dsot.py
"""Class that controls the Water Heater DER

Implements the optimum schedule of heating element operation given DA price forecast; generate the bids
for DA and RT; monitor and supervisory control of GridLAB-D environment element.
 with the implementation of new SOHC model and new delta_SOHC model
The function call order for this agent is:
    initialize

    Repeats at every hour:
        DA_forecasted_price(forecasted_price)
        DA_forecasted_schedule(forecasted_schedule)
        formulate_bid_da()

        Repeats at every 5 min:
            formulate_bid_rt()
            bid_accepted()

"""
import math
import numpy as np
from copy import deepcopy
import pyomo.environ as pyo
import pyomo.opt as opt
import logging as log

from .helpers import parse_number
from .helpers_dsot import get_run_solver

logger = log.getLogger()
log.getLogger('pyomo.core').setLevel(log.ERROR)


class WaterHeaterDSOT:
    """This agent manage the operation of water heater

    Args:
        volume (float): volume of the tank, in gal
        diameter (float): diameter of the tank layer, in ft
        Phw (float): rated power of the heating elements, in kW
        Tcold (float): temperature of the inlet cold water, in degF
        Tambient (float): ambient temperature, in degF
        Tdesired (float): setpoint value with highest user comfort, in degF
        Tmax (float): highest tolerant temperature of the water, in degF
        Tmin (float): lowest tolerant temperature of the water, in degF
        windowLength (int): length of DA bidding timeframe
        weight_SOHC (float): weight of the upper temperature measure when estimating the SOHC, falls into range [0, 1]
        weight_comfort (float): weight of the user comfort in the DA quantity optimization objective, falls into range [0, 1]
        ProfitMargin_intercept (float): specified in % and used to modify slope of bid curve. Set to 0 to disable
        ProfitMargin_slope (float): specified in % to generate a small dead band (i.e., change in price does not affect quantity). Set to 0 to disable
        Participating (boolean): equals to 1 when participate in the price-responsive biddings
        price_cap (float): the maximum price that is allowed in the retail market, in $/kWh
        model_diag_level (int): Specific level for logging errors; set it to 11
        sim_time (str): Current time in the simulation; should be human-readable

    Attributes:
        H_tank (float): height of the water tank, in ft
        A_tank (float): area of the layer of tank, in ft2
        A_wall (float): area of the water tank wall, in ft2
        R_tank (float): tank insulation, in ft2*hr*degF/Btu
        Cp (float): specific heat of water, in Btu/lbm*degF
        Rho (float): density of the water, in lbm/ft3
        BTUperkWh (float): unit conversion from kWh to BTU, in BTU/kWh
        GALperFt3 (float): unit conversion from ft3 to gallon, in ga/ft3
        T_upper (float): current set point of the upper heating element, in degF
        T_bottom (float): current set point of the bottom heating element, in degF
        SOHC (float): statue of heat charge, in %
        SOHC_desired (float): desired SOHC, in %
        SOHC_max (float): maximum SOHC, in %
        SOHC_min (float): minimum SOHC, in %
        states_upper (list): list of states and time in 5-min of upper element
        states_bottom (list): list of states and time in 5-min of bottom element
        runtime_upper (float): runtime of the upper element during 5-min
        runtime_bottom (float): runtime of the lower element during 5-min
        E_upper (float): energy consumed by the upper element in 5min, in kWh
        E_bottom (float): energy consumed by the bottom elemnt in 5min, in kWh
        wd_rate (float): averaged water draw flow rate in the 5min, in gal/min
        Setpoint_upper (float): setpoint to be set for the upper element, in degF
        Setpoint_bottom (float): setpoint to be set for the bottom element, in degF
        length_memory (int): length of memory for the historical data
        his_T_upper (list): historical time series data of the temperature measurement at the upper position
        his_T_bottom (list): historical time series data of the temperature measurement at the bottom position
        his_SOHC (list): historical time series data of the SOHC
        his_E_upper (list): historical time series power consumption of upper element
        his_E_bottom (list): historical time series power consumption of bottom element
        his_wd_rate (list): historical time series water draw flow rate data
        f_DA_price (list): forecasted DA price
        f_DA_schedule (list): forecasted DA water draw schedule
        P (int): index of price in the bid curve matrix
        Q (int): index of quantity in the bid curve matrix
        DA_cleared_prices (list): list of 48-hours day-ahead cleared prices
        DA_cleared_quantities (list): list of 48-hours day-ahead cleared quantities
        RT_cleared_price (float): cleared price for the next 5min
        RT_cleared_quantity (float): cleared quantity for the next 5min
        hourto5min (int): conversion from hour to 5min, equals to 12
        hour (int): current hour
        minute (int): current minute
        co0_hour (float): intercept of the hourly delta SOHC model
        co1_hour (float): coefficient of the water draw flow rate in the hourly delta SOHC model
        co2_hour (float): coefficient of the upper element consumption in the hourly delta SOHC model
        co3_hour (float): coefficient of the bottom element consumption in the hourly delta SOHC model
        co0_5min (float): intercept of the 5min delta SOHC model
        co1_5min (float): coefficient of the water draw flow rate in the 5min delta SOHC model
        co2_5min (float): coefficient of the upper element consumption in the 5min delta SOHC model
        co3_5min (float): coefficient of the bottom element consumption in the 5min delta SOHC model
        RT_SOHC_max (float): the maximum SOHC the water heater can achieve in the next 5min, in %
        RT_SOHC_min (float): the minimum SOHC the water heater can achieve in the next 5min, in %
        RT_Q_max (float): higher quantity boundary of the RT bid curve, in kWh
        RT_Q_min (float): lower quantity boundary of the RT bid curve, in kWh
    """

    def __init__(self, wh_dict, wh_properties, key, model_diag_level, sim_time, solver):
        """Initializes the class
        """
        self.name = key
        self.solver = solver
        self.volume = wh_properties['wh_gallons']
        self.diameter = 1.5  # wh_properties['wh_diameter'] Fixed value for all waterheaters in glm file
        self.Phw = 4.5  # Comes dynamically throughout simulation # this part is achieved through FNCS
        self.Tcold = wh_dict['Tcold']
        self.Tambient = wh_dict['Tambient']
        self.Tdesired = wh_dict['Tdesired']
        self.Tmax = wh_dict['Tmax']
        self.Tmin = wh_dict['Tmin']
        self.windowLength = wh_dict['windowLength']
        self.weight_SOHC = wh_dict['weight_SOHC']
        self.slider = wh_dict['slider_setting']
#        self.weight_comfort = wh_dict['weight_comfort']
        self.weight_comfort = 1 - self.slider

        self.ProfitMargin_intercept = wh_dict['ProfitMargin_intercept']
        self.ProfitMargin_slope = wh_dict['ProfitMargin_slope']
        self.price_cap = wh_dict['PriceCap']
        self.participating = wh_dict['participating']
        # Physical properties of water heater model
        self.BTUperkWh = 3413
        self.GALperFt3 = 7.481
        self.A_tank = math.pi * (self.diameter / 2) ** 2
        self.H_tank = self.volume / self.GALperFt3 * self.A_tank
        self.A_wall = math.pi * self.diameter * self.H_tank
        self.R_tank = 14
        self.UA = 1 / self.R_tank * (self.A_wall + 2 * self.A_tank)  ## NEW unit BTU/hr.degF  added for new model
        self.Cp = 1
        self.Rho = 62.3
        self.T_upper = 140
        self.T_bottom = 110
        self.Setpoint_upper = 0.0
        self.Setpoint_bottom = 0.0
        self.SOHC = 100
        self.SOHC_desired = 100
        self.SOHC_max = (self.Tmax -self.Tcold) / (self.Tdesired -self.Tcold) * 100
        self.SOHC_min = (self.Tmin -self.Tcold) / (self.Tdesired -self.Tcold) * 100
        self.SOHC_ambient = (self.Tambient - self.Tcold) / (self.Tdesired - self.Tcold) * 100  ## NEW unitless
        self.hour = 0
        self.minute = 0
        # initialization and collection of values from GLD
        self.states_upper = [[self.hour, self.minute % 60, 0],
                             [self.hour + (self.minute + 1) // 60, (self.minute + 1) % 60, 0],
                             [self.hour + (self.minute + 2) // 60, (self.minute + 2) % 60, 0],
                             [self.hour + (self.minute + 3) // 60, (self.minute + 3) % 60, 0],
                             [self.hour + (self.minute + 4) // 60, (self.minute + 4) % 60, 0]]
        self.states_bottom = [[self.hour, self.minute % 60, 0],
                              [self.hour + (self.minute + 1) // 60, (self.minute + 1) % 60, 0],
                              [self.hour + (self.minute + 2) // 60, (self.minute + 2) % 60, 0],
                              [self.hour + (self.minute + 3) // 60, (self.minute + 3) % 60, 0],
                              [self.hour + (self.minute + 4) // 60, (self.minute + 4) % 60, 0]]

        self.wd_rate_val = [[self.hour, self.minute % 60, 0],
                            [self.hour + (self.minute + 1) // 60, (self.minute + 1) % 60, 0],
                            [self.hour + (self.minute + 2) // 60, (self.minute + 2) % 60, 0],
                            [self.hour + (self.minute + 3) // 60, (self.minute + 3) % 60, 0],
                            [self.hour + (self.minute + 4) // 60, (self.minute + 4) % 60, 0]]

        self.runtime_wdrate = 0.0
        self.runtime_upper = 0.0
        self.runtime_bottom = 0.0
        self.E_upper = 0.0
        self.E_bottom = 0.0
        self.E_gld = 0.0
        self.wd_rate = 0.0
        self.length_memory = 288  ##change this to start the regression ##NOT in use anymore
        self.his_T_upper = []
        self.his_T_bottom = []
        self.his_SOHC = []
        self.his_E_upper = []
        self.his_E_bottom = []
        self.his_wd_rate = []
        self.f_DA_price = [0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20, 0.20,
                           0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30,
                           0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20, 0.20,
                           0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30]
        self.price_std_dev = 0.0

        # provide initial water draw schedule, will be updated after agent gaining enough memory of the water draw ##NOT in use anymore
        self.f_DA_schedule = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 0.8, 0.8, 1.5, 1, 0.0, 0.2, 0.8, 0.0, 1.2, 1, 0.8, 2.5,
                              0, 0, 0, 0.0, 0.0,
                              0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.9, 1.8, 0.8, 1, 0.0, 0.4, 0.7, 0.0, 1, 1.5, 1.2, 2.6,
                              0, 0, 0, 0.0, 0.0]
        self.P = 1
        self.Q = 0

        self.bid_rt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
        self.bid_da = [[[0., 0.], [0., 0.], [0., 0.], [0., 0.]]] * 48

        # provide initial DA cleared results, in case agent needs submit its first RT bid without knowledge of cleared DA results
        self.DA_cleared_prices = [0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20,
                                  0.20, 0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30,
                                  0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20,
                                  0.20, 0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30]
        self.DA_cleared_quantities = [4.2, 0.0, 0.0, 4.1, 0.0, 0.0, 2.5, 3, 2.5, 4.5, 1, 0.0, 3, 1, 0.0, 1, 1, 3.5, 0,
                                      0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.7, 2.5, 2.5, 3.5, 1, 0.0, 2, 1, 0.0, 1, 1, 3, 4,
                                      0, 0, 0, 0.0, 0.0]

        self.RT_cleared_price = 0.0
        self.RT_cleared_quantity = 0.0

        self.DA_opt_upper_temp = 0.0
        self.DA_opt_lower_temp = 0.0

        self.hourto5min = 12

        # provide initial delta sohc model coefficients, will be updated after agent gaining enough memory of historical data ##NOT in use anymore
        self.co0_hour = -0.654
        self.co1_hour = -28.224
        self.co2_hour = 9.061
        self.co3_hour = 3.693
        self.co0_5min = 0.009
        self.co1_5min = -2.572
        self.co2_5min = 7.611
        self.co3_5min = 3.832
        ## Real-time arguments
        self.RT_SOHC_max = self.SOHC_max
        self.RT_SOHC_min = self.SOHC_min
        self.RT_Q_max = self.Phw / self.hourto5min
        self.RT_Q_min = 0.0

        #interpolation
        self.interpolation = bool(True)
        self.RT_minute_count_interpolation = float(0.0)
        self.previous_Q_RT = float(0.0)
        self.delta_Q = float(0.0)
        # self.previous_Q_DA = float(0.0)

        # optimization
        self.TIME = range(self.windowLength)

        # Multiple cores
        self.optimized_Quantity = [[]] * self.windowLength
        self.QTY_agent = []
        self.SOHC_agent = [0 for i in range(self.windowLength)]
        
        ### Sanity checks:
        Tcold_lower = 40
        Tcold_upper = 80
        if Tcold_lower <= self.Tcold and Tcold_upper >= self.Tcold:
            # log.info('Tcold is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Tcold is {}, outside of nominal range of {} to {.'.format(self.name, 'init', self.Tcold, Tcold_lower, Tcold_upper))
        
        Tambient_lower = 60
        Tambient_upper = 85
        if Tambient_lower <= self.Tambient and Tambient_upper >= self.Tambient:
            # log.info('Tambient is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Tambient is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.Tambient, Tambient_lower, Tambient_upper))
        
        Tdesired_lower = 105
        Tdesired_upper = 120
        if Tdesired_lower <= self.Tdesired and Tdesired_upper >= self.Tdesired:
            # log.info('Tdesired is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Tdesired is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.Tdesired, Tdesired_lower, Tdesired_upper))
        
        Tmax_lower = 110
        Tmax_upper = 140
        if Tmax_lower <= self.Tmax and Tmax_upper >= self.Tmax:
            # log.info('Tmax is withint the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Tmax is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.Tmax, Tmax_lower, Tmax_upper))
        
        Tmin_lower = 100
        Tmin_upper = 120
        if Tmin_lower <= self.Tmin and Tmin_upper >= self.Tmin:
            # log.info('Tmin is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Tmin is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.Tmin, Tmin_lower, Tmin_upper))
        
        SOHC_lower = 0
        SOHC_upper = 100
        if SOHC_lower <= self.SOHC_desired and SOHC_upper >= self.SOHC_desired:
            # log.info('SOHC_desired is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- SOHC_desired is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.SOHC_desired, SOHC_lower, SOHC_upper))
        
        volume_lower = 0
        volume_upper = 100
        if volume_lower < self.volume and volume_upper > self.volume:
            # log.info('volume is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- volume is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.volume, volume_lower, volume_upper))
        
        diameter_lower = 0  # TODO: update with better/feasible bounds
        diameter_upper = 100  # TODO: update with better/feasible bounds
        if diameter_lower < self.diameter and diameter_upper > self.diameter:
            # log.info('diameter is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- diameter is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.diameter, diameter_lower, diameter_upper))
        
        Phw_lower = 1.5
        Phw_upper = 10
        if Phw_lower < self.Phw and Phw_upper > self.Phw:
            # log.info('Phw is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Phw is {}, outside of nominal range of {} to {}'.format(self.name, 'init', self.Phw, Phw_lower, Phw_upper))
        
        if 0 <= self.ProfitMargin_intercept:
            # log.info('ProfitMargin_intercept is greater than or equal to 0.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- ProfitMargin_intercept is {}, negative value'.format(self.name, 'init', self.ProfitMargin_intercept))
        
        
        if 0 <= self.ProfitMargin_slope:
            # log.info('ProfitMargin_slope is greater than or equal to 0.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- ProfitMargin_slope is {}, negative value'.format(self.name, 'init', self.ProfitMargin_slope))

    def update_WH_his(self, model_diag_level, sim_time):
        """ Update the historical memory of water heater based on updated readings, called by formulate_bid_rt every 5 mins

        Args:
            model_diag_level (int): Specific level for logging errors; set it to 11
            sim_time (str): Current time in the simulation; should be human-readable

        """
        # Update the runtime variables of each element
        self.runtime_upper = np.sum(np.array(self.states_upper), axis=0)[2]
        runtime_upper_lower = 0
        runtime_upper_upper = 5
        if runtime_upper_lower <= self.runtime_upper <= runtime_upper_upper:
            # log.info('runtime_upper is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- runtime_upper is {}, outside of nominal range of {} to {}'.format(self.name, sim_time, self.runtime_upper, runtime_upper_lower, runtime_upper_upper))
        
        self.runtime_bottom = np.sum(np.array(self.states_bottom), axis=0)[2]
        runtime_bottom_lower = 0
        runtime_bottom_upper = 5
        if runtime_bottom_lower <= self.runtime_bottom <= runtime_bottom_upper:
            # log.info('runtime_bottom is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- runtime_bottom is {}, outside of nominal range of {} to {}'.format(self.name, sim_time, self.runtime_bottom, runtime_bottom_lower, runtime_bottom_upper))
        
        self.runtime_wdrate = np.sum(np.array(self.wd_rate_val), axis=0)[2]
        # =============================================================================
        # #        print("values used for sum for wdrate", self.wd_rate_val)
        # #        print("sum of wdrate from GLD for wdrate", self.runtime_wdrate)
        # =============================================================================
        # Update the current status
        self.E_upper = self.runtime_upper / 5 * self.Phw / self.hourto5min
        E_upper_lower = 0
        E_upper_upper = 0.8
        if 0 <= self.E_upper <= 0.8:
            # log.info('E_upper is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- E_upper is {}, outside of nominal range of {} to {}'.format(self.name, sim_time, self.E_upper, E_upper_lower, E_upper_upper))
        
        self.E_bottom = self.runtime_bottom / 5 * self.Phw / self.hourto5min
        E_bottom_lower = 0
        E_bottom_upper = 0.8
        if E_bottom_lower <= self.E_bottom <= E_bottom_upper:
            # log.info('E_bottom is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- E_bottom is {}, outside of nominal range of {} to {}'.format(self.name, sim_time, self.E_bottom, E_bottom_lower, E_bottom_upper))
        self.E_gld = self.E_upper + self.E_bottom

        SOHC_lower = 0
        SOHC_upper = 140
        self.SOHC = (self.weight_SOHC*self.T_upper+(1-self.weight_SOHC)*self.T_bottom -self.Tcold)/(self.Tdesired- self.Tcold)*100  ###changed this for new model
        if SOHC_lower <= self.SOHC <= SOHC_upper:
            # log.info('SOHC is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- SOHC is {}, outside of nominal range of {} to {}'.format(self.name, sim_time, self.SOHC, SOHC_lower, SOHC_upper))
        
        self.wd_rate = self.runtime_wdrate / 5
#        if 0 <= self.wd_rate and 'something' >= self.wd_rate:
#            # log.info('wd_rate is within the bounds.')
#            pass
#        else:
#            log.log(model_diag_level, '{} wd_rate is out of bounds.'.format(sim_time))
        # =============================================================================
        # #        print("wdrate for 5 mins", self.wd_rate)
        # #        print("the states and rating", self.states_upper,self.states_bottom ,self.Phw)
        # #        print("the states that update Ebottom n Eupper",self.runtime_upper,self.runtime_bottom )
        # #        print("the data being updated in his-Eupper,E-bottom",self.E_upper,self.E_bottom)
        # #        print("Tupper,Tlower",self.T_upper,self.T_bottom)
        # #        print("current SOHC",self.SOHC)
        # =============================================================================
        # Update the historical status
        # if len(self.his_SOHC) < self.length_memory:
        #     pass
        # else:
        #     self.his_T_upper.pop(0)
        #     self.his_T_bottom.pop(0)
        #     self.his_SOHC.pop(0)
        #     self.his_E_upper.pop(0)
        #     self.his_E_bottom.pop(0)
        #     self.his_wd_rate.pop(0)
        self.his_T_upper.append(self.T_upper)
        self.his_T_bottom.append(self.T_bottom)
        self.his_SOHC.append(self.SOHC)
        self.his_E_upper.append(self.E_upper)
        self.his_E_bottom.append(self.E_bottom)
        self.his_wd_rate.append(self.wd_rate)
        # update the estimated values for waterdraw schedule
    # =============================================================================
    #         if len(self.his_SOHC) >= 2:
    #             self.his_wd_rate[-2] = self.estimate_wd_rate_5min()
    # =============================================================================

    def estimate_wd_rate_5min(self):  ##this function is not being used in new water heater model
        """ Function used to estimate the water_draw flow rate in the previous 5 mins, called by update_WH_his every 5 mins

        """
        Delta_T_average = (self.weight_SOHC * self.his_T_upper[-1] + (1 - self.weight_SOHC) * self.his_T_bottom[
            -1]) / 2 - \
                          (self.weight_SOHC * self.his_T_upper[-2] + (1 - self.weight_SOHC) * self.his_T_bottom[-2]) / 2
        T_average = (self.weight_SOHC * self.his_T_upper[-1] + (1 - self.weight_SOHC) * self.his_T_bottom[-1] +
                     self.weight_SOHC * self.his_T_upper[-2] + (1 - self.weight_SOHC) * self.his_T_bottom[-2]) / 2

        Delta_heat = self.A_tank * self.H_tank * self.Cp * self.Rho * Delta_T_average
        Heat_loss_ambient = 1 / self.R_tank * (self.A_wall + 2 * self.A_tank) * T_average * (1 / self.hourto5min)
        Heat_gain = self.BTUperkWh * (self.his_E_upper[-1] + self.his_E_bottom[-1])
        Heat_loss_waterdraw = Heat_gain - Heat_loss_ambient + Delta_heat  ##changed recently
        estimated_wd_rate = Heat_loss_waterdraw / (((self.his_T_upper[-1] + self.his_T_upper[
            -2]) / 2 - self.Tcold) * self.Cp * self.Rho * 5 / self.GALperFt3)
        if (estimated_wd_rate < 0):  ### changed to cap water draw
            estimated_wd_rate = 0
        if (estimated_wd_rate > 6):  # changed to cap water draw
            estimated_wd_rate = 6

        return estimated_wd_rate

    def set_price_forecast(self, forecasted_price):
        """ Set the f_DA_price attribute

        Args:
            forecasted_price (list): forecasted DA prices in $/kwh, provided by retail market agent
        """
        self.f_DA_price = deepcopy(forecasted_price)
        self.price_std_dev = np.std(self.f_DA_price)

    def set_forecasted_schedule(self, forecasted_waterdraw_array):
        """ Set the f_DA_schedule attribute

        Args:
            forecasted_waterdraw_schedule (list): forecasted waterdraw flow rate schedule in gallons/min, provided by forecast agent
        """
        # only update the schedule forecast when there are enough memory of water draw
        # if len(self.his_wd_rate) < self.length_memory:
        #     pass
        # else:
        #     schedule_5min = np.array(self.his_wd_rate).reshape(
        #         (int(self.length_memory / self.hourto5min), self.hourto5min))
        #     schedule_hour = np.mean(schedule_5min, axis=1).tolist()
        #     self.f_DA_schedule = deepcopy(schedule_hour)
        #self.f_DA_schedule = np.array(deepcopy(forecasted_waterdraw_array['data']))
        self.f_DA_schedule = np.array(deepcopy(forecasted_waterdraw_array))
        # print(self.name)
        # print(list(self.f_DA_schedule))

    def formulate_bid_da(self):
        """ Formulate windowLength hours 4 points PQ bid curves for the DA market

        Function calls DA_optimal_quantities to obtain the optimal quantities for the DA market. With the quantities, a 4 point bids are formulated for each hour.

        Returns
        BID (float) (windowLength X 4 X 2): DA bids to be send to the retail DA market
        """
        #this part runs optimization without multiprocessing
        # Quantity = self.DA_optimal_quantities()

        Quantity = deepcopy(self.optimized_Quantity)

        P = self.P
        Q = self.Q
        #previous hour quantity
        # self.previous_Q=self.bid_da[0][1][Q]

        TIME = range(self.windowLength)

        CurveSlope = [0 for i in TIME]
        yIntercept = [-1 for i in TIME]
        BID = [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]] for i in TIME]
        delta_DA_price = max(self.f_DA_price) - min(self.f_DA_price)

        for t in TIME:

            # CurveSlope[t] = delta_DA_price / (0 - self.Phw) * (1 + self.ProfitMargin_slope / 100)
            if self.slider != 0.0:
                CurveSlope[t] = delta_DA_price / ((0 - self.Phw) * self.slider)
            else:
                CurveSlope[t] = delta_DA_price / ((0 - self.Phw) * 0.001)

            yIntercept[t] = self.f_DA_price[t] - CurveSlope[t] * Quantity[t]

            BID[t][0][Q] = 0
            BID[t][1][Q] = Quantity[t]
            BID[t][2][Q] = Quantity[t]
            BID[t][3][Q] = self.Phw

            # BID[t][0][P] = 0 * CurveSlope[t] + yIntercept[t] + (self.ProfitMargin_intercept / 100) * delta_DA_price
            # BID[t][1][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] + (
            #         self.ProfitMargin_intercept / 100) * delta_DA_price
            # BID[t][2][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] - (
            #         self.ProfitMargin_intercept / 100) * delta_DA_price
            # BID[t][3][P] = self.Phw * CurveSlope[t] + yIntercept[t] - (
            #         self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[t][0][P] = 0 * CurveSlope[t] + yIntercept[t]
            BID[t][1][P] = Quantity[t] * CurveSlope[t] + yIntercept[t]
            BID[t][2][P] = Quantity[t] * CurveSlope[t] + yIntercept[t]
            BID[t][3][P] = self.Phw * CurveSlope[t] + yIntercept[t]

            for i in range(4):
                if BID[t][i][Q] > self.Phw:
                    BID[t][i][Q] = self.Phw
                if BID[t][i][Q] < 0:
                    BID[t][i][Q] = 0
                if BID[t][i][P] > self.price_cap:
                    BID[t][i][P] = self.price_cap
                if BID[t][i][P] < 0:
                    BID[t][i][P] = 0

        self.bid_da = deepcopy(BID)
        #print("DA ahead first bid", self.bid_da[0])
        self.DA_cleared_prices = deepcopy(self.f_DA_price)  ## to be used in formulating real-time bid

        self.RT_minute_count_interpolation = float(0.0)
        return self.bid_da
    def get_uncntrl_wh_load(self):
        """
        This simulates the waterheater model without
        :return: 48-hours forecast of non transactive waterheater kw consumption without optimization (agent participation)
        """
        self.delta_SOHC_model_hour()
        Q = []
        for t in self.TIME:
            # if t == 0:
            #     if self.SOHC > self.SOHC_max:
            #         return m.SOHC[0] == self.SOHC_max
            #     else:
            #         return m.SOHC[0] == self.SOHC
            Qdraw = self.Rho * self.Cp * self.f_DA_schedule[t - 1] * 60 * (self.Tdesired - self.Tcold) / (
                    self.GALperFt3 * self.BTUperkWh)  ##60 is for converting gpm into gphr as Qdraw for an hour is being calculated
            temp = Qdraw - ((self.co2_hour * (self.SOHC_desired / 100) + self.co0_hour)/self.co1_hour)
            if temp > self.Phw:
                temp = self.Phw
            Q.append(temp)
        return Q
            # 0 = (self.co0_hour + self.co1_hour * (m.E_upper[t - 1] + m.E_bottom[t - 1] - Qdraw) + self.co2_hour * (
            #         self.SOHC_desired / 100)) * 100
    def obj_rule(self, m):
        #return sum(
        #    (1 - self.weight_comfort) * (self.f_DA_price[t]) * (m.E_upper[t] + m.E_bottom[t]) + (self.weight_comfort) *
        #    (( self.SOHC_desired -  m.SOHC[t]) /100) - 0.001 * ((m.E_upper[t] + m.E_bottom[t]) ** 2) for t in self.TIME)
        # TODO: SOHC_min still doesn't make the units of the second term to be $
        # 0.04 is the fixed connection charges added to the agent optimization problem.
        return sum(
            ((1 - self.weight_comfort) * (self.f_DA_price[t]-np.min(self.f_DA_price))/(np.max(self.f_DA_price)-np.min(self.f_DA_price)) *
             (m.E_upper[t] + m.E_bottom[t])/self.Phw)
            + (0.3*(self.SOHC_desired - m.SOHC[t])/100 * (self.SOHC_desired - m.SOHC[t])/100)
            + (0.001 * ((m.E_upper[t] + m.E_bottom[t])/self.Phw * (m.E_upper[t] + m.E_bottom[t])/self.Phw)) for t in self.TIME)
        # there was a minus sign in the last term, it should be positive and the SOHC was only enter once, which was making the Agents consume to get SOHC_max
    def con_rule_ine1(self, m, t):
        # for t in self.TIME:
        return (m.E_bottom[t] + m.E_upper[t]) <= self.Phw

    def con_rule_eq1(self, m, t):  # initialize SOHC state
        # if t == 0:
        #     if self.SOHC > self.SOHC_max:
        #         return m.SOHC[0] == self.SOHC_max
        #     else:
        #         return m.SOHC[0] == self.SOHC
        # else:
        #     Qdraw = self.Rho * self.Cp * self.f_DA_schedule[t-1] * 60 * (self.Tdesired - self.Tcold) / (
        #             self.GALperFt3 * self.BTUperkWh)  ##60 is for converting gpm into gphr as Qdraw for an hour is being calculated
        #
        #     delta_SOHC = (self.co0_hour + self.co1_hour * (m.E_upper[t] + m.E_bottom[t] - Qdraw) + self.co2_hour * (
        #             m.SOHC[t - 1] / 100)) * 100
        #     return m.SOHC[t] == m.SOHC[t-1] + delta_SOHC

        if t == 0:
            Qdraw = self.Rho * self.Cp * self.f_DA_schedule[0] * 60 * (self.Tdesired - self.Tcold) / (
                    self.GALperFt3 * self.BTUperkWh)
            delta_SOHC = (self.co0_hour + self.co1_hour * (m.E_upper[0] + m.E_bottom[0] - Qdraw) + self.co2_hour * (
                self.SOHC / 100)) * 100
            return m.SOHC[0] == self.SOHC + delta_SOHC

        else:
            Qdraw = self.Rho * self.Cp * self.f_DA_schedule[t] * 60 * (self.Tdesired - self.Tcold) / (
                    self.GALperFt3 * self.BTUperkWh)  ##60 is for converting gpm into gphr as Qdraw for an hour is being calculated

            delta_SOHC = (self.co0_hour + self.co1_hour * (m.E_upper[t] + m.E_bottom[t] - Qdraw) + self.co2_hour * (
                    m.SOHC[t - 1] / 100)) * 100
            return m.SOHC[t] == m.SOHC[t - 1] + delta_SOHC

            # return m.SOHC[t] == m.SOHC[t - 1] + (
            #         self.co0_hour + self.co1_hour * self.f_DA_schedule[t - 1] + self.co2_hour * m.E_upper[
            #     t - 1] + self.co3_hour * m.E_bottom[t - 1])

    def DA_optimal_quantities(self):
        """ Generates Day Ahead optimized quantities for Water Heater according to the forecasted prices and water draw schedule, called by DA_formulate_bid function

        Returns:
            Quantity (list) (1 x windowLength): Optimized quantities for each hour in the DA bidding horizon, in kWh
        """

        #       update the hourly delta SOHC model when there is enough memory in historical data
        # =============================================================================
        #         if len(self.his_SOHC) < self.length_memory:
        #             pass
        #         else:
        #             self.delta_SOHC_model_hour()
        # =============================================================================
        self.delta_SOHC_model_hour()

        # Decision variables
        # wh_R5_12_47_3_tn_1008_hse_1
        model = pyo.ConcreteModel()
        model.E_bottom = pyo.Var(self.TIME, bounds=(0, self.Phw))#, initialize=self.Phw)
        model.E_upper = pyo.Var(self.TIME, bounds=(0, self.Phw))#, initialize=self.Phw)
        model.SOHC = pyo.Var(self.TIME, bounds=(self.SOHC_min, self.SOHC_max))#, initialize=self.SOHC_max)

        # Objective of the problem
        model.obj = pyo.Objective(rule=self.obj_rule, sense=pyo.minimize)
        # Constraints
        model.con1 = pyo.Constraint(self.TIME, rule=self.con_rule_ine1)
        model.con2 = pyo.Constraint(self.TIME, rule=self.con_rule_eq1)

        results = get_run_solver("wh_" + self.name, pyo, model, self.solver)

        Quantity = [0 for i in self.TIME]
        SC = [0 for i in self.TIME]
        E_u = [0 for i in self.TIME]
        E_b = [0 for i in self.TIME]

        # TOL = 0.00001 # Tolerance for checking bid
        for t in self.TIME:
            # if (pyo.value(model.E_upper[t])) + (pyo.value(model.E_bottom[t])) > TOL:
            Quantity[t] = (pyo.value(model.E_upper[t])) + (pyo.value(model.E_bottom[t]))
            SC[t] = (pyo.value(model.SOHC[t]))
            E_u[t] = (pyo.value(model.E_upper[t]))
            E_b[t] = (pyo.value(model.E_bottom[t]))

        # =============================================================================
        # print(self.name)
        # print("Coefficients of delta_SOHC", self.co0_hour, self.co1_hour, self.co2_hour)
        # print("hourly water draw", self.f_DA_schedule)
        # print("hourly forecasted price", self.f_DA_price)
        # print("Price std deviation", self.price_std_dev)
        # print("Output E_upper", E_u)
        # print("Output E_bottom", E_b)
        # print("Output E_upper + E_bottom",Quantity)
        # print("Rated Power", self.Phw)
        # print("Output SOHC value", SC)
        # print("SOHC_max_min", self.SOHC_max, self.SOHC_min)
        # print("SOHC_Current",self.SOHC)
        # print("Name: "+str(self.name) + "Day-Ahead Quantity: " + str(Quantity))
        # =============================================================================
        return Quantity

    def delta_SOHC_model_hour(self):
        """Function used to fit the hourly delta_SOHC estimation model, where hourly delta_SOHC is assumed to be a function of wd_rate E_upper and E_bottom values with one-hour interval

        """
        # his_SOHC_hour = np.mean(np.array(self.his_SOHC).reshape(-1, self.hourto5min), axis=1).tolist()
        # his_wd_rate_hour = np.mean(np.array(self.his_wd_rate).reshape(-1, self.hourto5min), axis=1).tolist()
        # his_E_upper_hour = np.sum(np.array(self.his_E_upper).reshape(-1, self.hourto5min), axis=1).tolist()
        # his_E_bottom_hour = np.sum(np.array(self.his_E_bottom).reshape(-1, self.hourto5min), axis=1).tolist()
        # X = np.column_stack((his_wd_rate_hour, his_E_upper_hour, his_E_bottom_hour))
        # y = np.array(
        #     [self.his_SOHC[12 * i + self.hourto5min - 1] - self.his_SOHC[12 * i] for i in range(len(his_SOHC_hour))])
        # reg = LinearRegression(fit_intercept=True, normalize=False).fit(X, y)
        # self.co0_hour = reg.intercept_
        # self.co1_hour = reg.coef_[0]
        # self.co2_hour = reg.coef_[1]
        # self.co3_hour = reg.coef_[2]
        delta_t = 1  ##one hour interval
        a = (self.UA * delta_t / 2) / (self.BTUperkWh)
        b = (self.Rho * self.Cp * self.volume) / (self.GALperFt3 * self.BTUperkWh)
        self.co0_hour = (2 * a * self.SOHC_ambient / 100) / (a + b)
        self.co1_hour = 1 / ((a + b) * (self.Tdesired - self.Tcold))
        self.co2_hour = -1 - ((a - b) / (a + b))
        # print(self.name)
        # print(self.co0_hour, "Co0h")
        # print(self.co1_hour, "Co1h")
        # print(self.co2_hour, "Co2h")

    def delta_SOHC_model_5min(self):
        """Function used to fit the 5min delta_SOHC estimation model, where 5min delta_SOHC is assumed to be a function of wd_rate E_upper and E_bottom values with 5min interval

        """

        # X = np.column_stack((self.his_wd_rate[:-1], self.his_E_upper[:-1], self.his_E_bottom[:-1]))
        # y = np.array([self.his_SOHC[i + 1] - self.his_SOHC[i] for i in range(len(self.his_SOHC) - 1)])
        # reg = LinearRegression(fit_intercept=True, normalize=False).fit(X, y)
        # self.co0_5min = reg.intercept_
        # self.co1_5min = reg.coef_[0]
        # self.co2_5min = reg.coef_[1]
        # self.co3_5min = reg.coef_[2]
        ###Equation 22
        delta_t = 1  ##one 5-min  interval
        a = (self.UA * delta_t / 2) / (self.hourto5min * self.BTUperkWh)
        b = (self.Rho * self.Cp * self.volume) / (self.GALperFt3 * self.BTUperkWh)
        self.co0_5min = (2 * a * self.SOHC_ambient / 100) / (a + b)
        self.co1_5min = 1 / ((a + b) * (self.Tdesired - self.Tcold))
        self.co2_5min = -1 - ((a - b) / (a + b))
        # print("Co0_5min", self.co0_5min)
        # print("Co1_5min", self.co1_5min)
        # print("Co2_5min", self.co2_5min)

    def formulate_bid_rt(self, model_diag_level, sim_time):
        """ Formulate 4 points PQ bid curve for the RT market

        Given the physical and operational constraints of the water heater and the current water heater status, 4 points RT bid curve is formulated for the next 5min.
        
        Args:
            model_diag_level (int): Specific level for logging errors: set it to 11
            sim_time (str): Current time in the simulation; should be human-readable

        Returns:
            BID (float) (4 X 2): RT bid to be send to the retail RT market
        """

        P = self.P
        Q = self.Q

        CurveSlope = 0
        yIntercept = 0

        BID = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        #        BID = deepcopy(self.bid_da[0])
        # =============================================================================
        # update the water heater history database
        self.update_WH_his(model_diag_level, sim_time)

        # update the 5min delta SOHC model when there is enough memory in historical data
        # if len(self.his_SOHC) < self.length_memory:
        #     pass
        # else:
        self.delta_SOHC_model_5min()

        delta_DA_price = max(self.f_DA_price) - min(self.f_DA_price)
        # Updating the upper and lower bounds of bidding quantity based on the current status of water tanker

        if self.SOHC < self.SOHC_min:  ##checks if the temperature is below what AGENT has minimum
            Q_max = self.Phw #/ self.hourto5min
            Q_min = self.Phw #/ self.hourto5min
            self.RT_SOHC_max = self.SOHC_max
            self.RT_SOHC_min = self.SOHC_max
#            print("##############Water heater temperature below SOHC minimum")
        elif  self.SOHC > self.SOHC_max: ##checks if the temperature is above what AGENT has maximum
            Q_max = 0
            Q_min = 0
            self.RT_SOHC_max = self.SOHC_min
            self.RT_SOHC_min = self.SOHC_min
#            print("##############Water heater temperature above SOHC maximum") ## happens often as upper temp in EWH goes higher than expected
        else:
            # Decides maximum  bidding quantity
            Qdraw_5min = self.Rho * self.Cp * self.f_DA_schedule[0] * 5 * (self.Tdesired - self.Tcold) / (
                self.GALperFt3 * self.BTUperkWh)  ###5 is for converting gpm into gallon/5min  as Qdraw for 5min is calculated
            delta_SOHC_max = (self.co0_5min + self.co1_5min * ((self.Phw / self.hourto5min) - Qdraw_5min) + self.co2_5min * (
                self.SOHC / 100))*100

            if (self.SOHC + delta_SOHC_max < self.SOHC_max)  :    ##scenario 3 coded
                Q_max = self.Phw #/ self.hourto5min
                self.RT_SOHC_max = self.SOHC + delta_SOHC_max
            else:
                # temp_Qmax = (((self.SOHC_max - self.SOHC)/100 - self.co0_5min + self.co1_5min *Qdraw_5min -self.co2_5min * (self.SOHC/100)) / self.co1_5min)
                # if this is the inverse of the above equation of delta_SOHC, then self.hourto5min is missing in it.
                temp_Qmax = self.hourto5min*(((self.SOHC_max - self.SOHC)/100 - self.co0_5min + self.co1_5min *Qdraw_5min -self.co2_5min * (self.SOHC/100)) / self.co1_5min)

                if  temp_Qmax < (self.Phw):# / self.hourto5min): #scenario 2 where max of two is taken
                    Q_max = temp_Qmax
#                    print("@@@@@@@@@@@@@@@@@@@@@@ RT Q_max is changed other than rating", Q_max)
                else:
                    Q_max = self.Phw #/ self.hourto5min
                self.RT_SOHC_max = self.SOHC_max

            #Decides minimum bidding quantity
            delta_SOHC_min = (self.co0_5min + self.co1_5min * (-Qdraw_5min) + self.co2_5min * (self.SOHC / 100))*100
            #print("Qdraw_5min, SOHC at that 5min , delta_SOHC_max ,delta_SOHC_min ", Qdraw_5min, self.SOHC, delta_SOHC_max, delta_SOHC_min)
            if self.SOHC + delta_SOHC_min > self.SOHC_min:  #scenario 5 coded
                Q_min = 0
                self.RT_SOHC_min = self.SOHC + delta_SOHC_min
            else:
                # temp_Qmin = (((self.SOHC_min - self.SOHC)/100 - self.co0_5min + self.co1_5min *Qdraw_5min -self.co2_5min * (self.SOHC/100)) / self.co1_5min)
                # if this is the inverse of the above equation of delta_SOHC, then self.hourto5min is missing in it.
                temp_Qmin = self.hourto5min*(((self.SOHC_min - self.SOHC)/100 - self.co0_5min + self.co1_5min *Qdraw_5min -self.co2_5min * (self.SOHC/100)) / self.co1_5min)

                if  temp_Qmin < (self.Phw):#) / self.hourto5min): #scenario 4
                    Q_min = temp_Qmin
                    print("@@@@@@@@@@@@@@@@@@@@@@RT Q_min is changed other than rating", Q_min)
                else:
                    Q_min = self.Phw #/ self.hourto5min
                self.RT_SOHC_min = self.SOHC_min
        # print(self.name)
        # print("*********************DA QUANTITY USED", self.bid_da[0][1][0])
        # print("DA bid ", self.bid_da[0])
        # print("RT Qmax and Qmin", Q_max, Q_min)
        # print("RT SOHC max and min", self.RT_SOHC_max, self.RT_SOHC_min)
        # print("Price forecast for RT",self.DA_cleared_prices[0])
        # Constructing the 4 point bid curve
        if Q_min != Q_max:

            CurveSlope = (delta_DA_price / (0 - self.Phw) * (1 + self.ProfitMargin_slope / 100))
            yIntercept = self.DA_cleared_prices[0] - CurveSlope * self.bid_da[0][1][0] #/ 12   ## DA quantity and forecasted DA price used for Real-time
            #print("RT y-intercept", yIntercept )
            # print("RT curveslope", CurveSlope)
            if (self.bid_da[0][1][0] <= Q_max) and (self.bid_da[0][1][0] > Q_min):
                ##start interpolation
                if self.interpolation:
                    if self.RT_minute_count_interpolation == 0.0:
                        self.delta_Q = deepcopy((self.bid_da[0][1][Q]-self.previous_Q_RT))
                    if self.RT_minute_count_interpolation == 30.0:
                        self.delta_Q = deepcopy((self.bid_da[1][1][Q]-self.previous_Q_RT)*0.5)
                    Qopt_DA=self.previous_Q_RT+self.delta_Q*(5.0/30.0)
                    # Qopt_DA = self.bid_da[0][1][Q]*(self.RT_minute_count_interpolation/60.0) + self.previous_Q*(1-self.RT_minute_count_interpolation/60.0)
                    self.previous_Q_RT=Qopt_DA
                    BID[0][Q] = Q_min
                    BID[1][Q] = Qopt_DA
                    BID[2][Q] = Qopt_DA
                    BID[3][Q] = Q_max

                    BID[0][P] = Q_min * CurveSlope + yIntercept
                    BID[1][P] = Qopt_DA * CurveSlope + yIntercept
                    BID[2][P] = Qopt_DA * CurveSlope + yIntercept
                    BID[3][P] = Q_max * CurveSlope + yIntercept
                ##end interpolation
                else:
                    BID[0][Q] = Q_min
                    BID[1][Q] = self.bid_da[0][1][0]
                    BID[2][Q] = self.bid_da[0][1][0]
                    BID[3][Q] = Q_max

                    # BID[0][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                    # BID[1][P] = self.bid_da[0][1][0] * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                    # BID[2][P] = self.bid_da[0][1][0] * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
                    # BID[3][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
                    BID[0][P] = Q_min * CurveSlope + yIntercept
                    BID[1][P] = self.bid_da[0][1][0] * CurveSlope + yIntercept
                    BID[2][P] = self.bid_da[0][1][0] * CurveSlope + yIntercept
                    BID[3][P] = Q_max * CurveSlope + yIntercept
            else:
                BID[0][Q] = Q_min
                BID[1][Q] = Q_min
                BID[2][Q] = Q_max
                BID[3][Q] = Q_max

                # BID[0][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                # BID[1][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                # BID[2][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
                # BID[3][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[0][P] = Q_min * CurveSlope + yIntercept
                BID[1][P] = Q_min * CurveSlope + yIntercept
                BID[2][P] = Q_max * CurveSlope + yIntercept
                BID[3][P] = Q_max * CurveSlope + yIntercept
        else:
            BID[0][Q] = Q_min
            BID[1][Q] = Q_min
            BID[2][Q] = Q_max
            BID[3][Q] = Q_max

            # BID[0][P] = max(self.f_DA_price) + (self.ProfitMargin_intercept / 100) * delta_DA_price
            # BID[1][P] = max(self.f_DA_price) + (self.ProfitMargin_intercept / 100) * delta_DA_price
            # BID[2][P] = min(self.f_DA_price) - (self.ProfitMargin_intercept / 100) * delta_DA_price
            # BID[3][P] = min(self.f_DA_price) - (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[0][P] = max(self.f_DA_price)
            BID[1][P] = max(self.f_DA_price)
            BID[2][P] = min(self.f_DA_price)
            BID[3][P] = min(self.f_DA_price)


        for i in range(4):
            if BID[i][Q] > self.Phw:
                BID[i][Q] = self.Phw
            if BID[i][Q] < 0:
                BID[i][Q] = 0
            if BID[i][P] > self.price_cap:
                BID[i][P] = self.price_cap
            if BID[i][P] < 0:
                BID[i][P] = 0

        self.RT_Q_max = Q_max
        self.RT_Q_min = Q_min
        if Q_max < 0:
            print("Error in calculation of Q_max", Q_max)

        self.bid_rt = BID
        # print("=====================RT bid quantity",self.bid_rt)
        # reinitialize the states matrices
        state_upper_pre = self.states_upper[-1][2]
        self.states_upper = [[self.hour, self.minute % 60, state_upper_pre],
                             [self.hour + (self.minute + 1) // 60, (self.minute + 1) % 60, state_upper_pre],
                             [self.hour + (self.minute + 2) // 60, (self.minute + 2) % 60, state_upper_pre],
                             [self.hour + (self.minute + 3) // 60, (self.minute + 3) % 60, state_upper_pre],
                             [self.hour + (self.minute + 4) // 60, (self.minute + 4) % 60, state_upper_pre]]
        state_bottom_pre = self.states_bottom[-1][2]
        self.states_bottom = [[self.hour, self.minute % 60, state_bottom_pre],
                              [self.hour + (self.minute + 1) // 60, (self.minute + 1) % 60, state_bottom_pre],
                              [self.hour + (self.minute + 2) // 60, (self.minute + 2) % 60, state_bottom_pre],
                              [self.hour + (self.minute + 3) // 60, (self.minute + 3) % 60, state_bottom_pre],
                              [self.hour + (self.minute + 4) // 60, (self.minute + 4) % 60, state_bottom_pre]]
        wd_rate_val_pre = self.wd_rate_val[-1][2]
        self.wd_rate_val = [[self.hour, self.minute % 60, wd_rate_val_pre],
                            [self.hour + (self.minute + 1) // 60, (self.minute + 1) % 60, wd_rate_val_pre],
                            [self.hour + (self.minute + 2) // 60, (self.minute + 2) % 60, wd_rate_val_pre],
                            [self.hour + (self.minute + 3) // 60, (self.minute + 3) % 60, wd_rate_val_pre],
                            [self.hour + (self.minute + 4) // 60, (self.minute + 4) % 60, wd_rate_val_pre]]

        self.RT_minute_count_interpolation = self.RT_minute_count_interpolation + 5.0
        return self.bid_rt

    def inform_bid_da(self, DAprices): ##this object is never called
        """ Updated the DA_cleared_prices and DA_cleared_quantities attributes when informed by retail market agent

        Args:
            DAquantities (list): cleared quantities from the last DA market clearing, in kWh, provided by retail market agent
            DAprices (list): cleared prices from the last DA market clearing, in $/kWh, provided by retail market agent
        """
        self.DA_cleared_prices = DAprices
        for idx in range(self.windowLength):
            self.DA_cleared_quantities[idx] = self.from_P_to_Q_WH(self.bid_da[idx], DAprices[idx])

    def inform_bid_rt(self, RTprice):
        """ Updated the RT_cleared_prices and RT_cleared_quantities attributes when informed by retail market agent

        Args:
            RTquantity (float): cleared quantity from the last RT market clearing, in kWh, provided by retail market agent
            RTprice (float): cleared price from the last RT market clearing, in $/kWh, provided by retail market agent
        """
        self.RT_cleared_price = RTprice
        self.RT_cleared_quantity = self.from_P_to_Q_WH(self.bid_rt, RTprice)

    def bid_accepted(self, model_diag_level, sim_time):
        """ Update the thermostat setting if the last bid was accepted

           The last bid is always "accepted". If it wasn't high enough,
           then the thermostat could be turned up.
        
        Args:
            model_diag_level (int): Specific level for logging errors; set it to 11
            sim_time (str): Current time in the simulation; should be human-readable

        Returns:
           Boolean: True if the thermostat setting changes, False if not.
        """
        upper_previous = deepcopy(self.Setpoint_upper)
        bottom_previous = deepcopy(self.Setpoint_bottom)
        ###########for old SOHC model and delta SOHC model
        # if (self.RT_SOHC_max == self.RT_SOHC_min) or (self.RT_Q_max == self.RT_Q_min):
        #     self.Setpoint_upper = self.RT_SOHC_max / 100 * self.Tdesired
        #     self.Setpoint_bottom = self.RT_SOHC_max / 100 * self.Tdesired
        # else:
        #     self.Setpoint_upper = (self.RT_SOHC_min + (self.RT_cleared_quantity- self.RT_Q_min) * (
        #             self.RT_SOHC_max - self.RT_SOHC_min) / (self.RT_Q_max - self.RT_Q_min)) / 100 * (self.Tdesired )
        #     self.Setpoint_bottom = (self.RT_SOHC_min + (self.RT_cleared_quantity  - self.RT_Q_min) * (
        #             self.RT_SOHC_max - self.RT_SOHC_min) / (self.RT_Q_max - self.RT_Q_min)) / 100 * (self.Tdesired )
        ###########for new SOHC model

        if (self.RT_SOHC_max == self.RT_SOHC_min) or (self.RT_Q_max == self.RT_Q_min): ##scenario for SOHC < SOHC_min
            Setpoint_upper_SOHC = self.RT_SOHC_max
            Setpoint_bottom_SOHC = self.RT_SOHC_max
            self.Setpoint_upper = (Setpoint_upper_SOHC / 100 * (self.Tdesired - self.Tcold)) + self.Tcold
            self.Setpoint_bottom = (Setpoint_bottom_SOHC / 100 * (self.Tdesired - self.Tcold)) + self.Tcold
        elif (self.RT_Q_max == self.RT_Q_min) and  (self.RT_Q_max == 0):  ##scenario for SOHC > SOHC_max
            Setpoint_upper_SOHC = self.RT_SOHC_min
            Setpoint_bottom_SOHC = self.RT_SOHC_min
            self.Setpoint_upper = (Setpoint_upper_SOHC / 100 * (self.Tdesired - self.Tcold)) + self.Tcold
            self.Setpoint_bottom = (Setpoint_bottom_SOHC / 100 * (self.Tdesired - self.Tcold)) + self.Tcold
        else: ## scenario for all other cases and converts bid directly to temperature setpoints for GLD
            Setpoint_upper_SOHC = (self.RT_SOHC_min + (self.RT_cleared_quantity- self.RT_Q_min) * (
                    self.RT_SOHC_max - self.RT_SOHC_min) / (self.RT_Q_max - self.RT_Q_min))
            Setpoint_bottom_SOHC = (self.RT_SOHC_min + (self.RT_cleared_quantity  - self.RT_Q_min) * (
                    self.RT_SOHC_max - self.RT_SOHC_min) / (self.RT_Q_max - self.RT_Q_min))
            self.Setpoint_upper = (Setpoint_upper_SOHC / 100 * (self.Tdesired - self.Tcold)) + self.Tcold
            self.Setpoint_bottom = (Setpoint_bottom_SOHC / 100 * (self.Tdesired - self.Tcold)) + self.Tcold

        # # ##########3for validation purpose , forcing the DA value in RT.
        # Setpoint_upper_SOHC = (self.SOHC_min + ((self.bid_da[0][1][0]) - 0) * (
        #         (self.SOHC_max - self.SOHC_min) / (self.Phw- 0)))
        # Setpoint_bottom_SOHC = (self.SOHC_min + ((self.bid_da[0][1][0]) - 0) * (
        #         (self.SOHC_max - self.SOHC_min) / (self.Phw- 0)))
        # print("Calculated SOHC setpoints", Setpoint_upper_SOHC)
        # # self.Setpoint_upper = ((Setpoint_upper_SOHC /(100))* (self.Tdesired - self.Tcold)) + self.Tcold
        # # self.Setpoint_bottom =  ((Setpoint_bottom_SOHC /(100))* (self.Tdesired - self.Tcold)) + self.Tcold
        # considering the optimized SOHC directly
        # self.Setpoint_upper = ((self.SOHC_agent[0]/100) * (self.Tdesired - self.Tcold) ) + self.Tcold
        # self.Setpoint_bottom = ((self.SOHC_agent[0]/100) * (self.Tdesired - self.Tcold)) + self.Tcold
        # print("Calculated temp setpoints", self.Setpoint_upper, self.Setpoint_bottom)

        if (self.Setpoint_upper >= self.Tmax): #check of Maximum temperature from agent
            self.Setpoint_upper = self.Tmax
            self.Setpoint_bottom = self.Tmax
        else:
            pass

        if (self.Setpoint_upper <= self.Tmin): #check of Minimum temperature from the Agent
            self.Setpoint_upper = self.Tmin
            self.Setpoint_bottom = self.Tmin
        else:
            pass

        # print("Actual temp of GLD", self.T_bottom, self.T_upper)
        # print("Real time Quantity used", self.RT_cleared_quantity)
        # print("Calculated SOHC setpoints", Setpoint_upper_SOHC, Setpoint_bottom_SOHC)
        # print("Calculated temp SETPOINT_LOWER and UPPER",self.Setpoint_bottom, self.Setpoint_upper)

        if self.Setpoint_upper == upper_previous and self.Setpoint_bottom == bottom_previous:
            return False
        else:
            return True

    def set_time(self, hour, minute):
        """ Sets the current hour and minute

        Args:
            hour (int): current hour
            minute (int): current minute
        """
        self.hour = hour
        self.minute = minute

    def set_wh_lower_temperature(self, fncs_str, model_diag_level, sim_time):
        """ Sets the lower tank temperature attribute

        Args:
            fncs_str (str): FNCS message with temperature in degrees Fahrenheit
            model_diag_level (int): Specific level for logging errors; set it to 11
            sim_time (str): Current time in the simulation; should be human-readable
        """
        try:
            _tmp = parse_number(fncs_str)
        except:
            _tmp = self.T_bottom
            print("Error wh lower temp:", fncs_str, self.name)
        self.T_bottom = _tmp

        T_bottom_lower = 60
        T_bottom_upper = 150  #140
        if T_bottom_lower <= self.T_bottom <= T_bottom_upper:
            # log.info('T_bottom is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- T_bottom is {}, outside of nominal range of {} to {}'
                    .format(self.name, sim_time, self.T_bottom, T_bottom_lower, T_bottom_upper))

    def set_wh_upper_temperature(self, fncs_str, model_diag_level, sim_time):
        """ Sets the upper tank temperature attribute

        Args:
            fncs_str (str): FNCS message with temperature in degrees Fahrenheit
            model_diag_level (int): Specific level for logging errors; set it to 11
            sim_time (str): Current time in the simulation; should be human-readable
        """
        try:
            _tmp = parse_number(fncs_str)
        except:
            _tmp = self.T_upper
            print("Error wh upper temp:", fncs_str, self.name)
        self.T_upper = _tmp

        T_upper_lower = 60
        T_upper_upper = 150  #140
        if T_upper_lower <= self.T_upper <= T_upper_upper:
            # log.info('T_upper is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- T_upper is {}, outside of nominal range of {} to {}'
                    .format(self.name, sim_time, self.T_upper, T_upper_lower, T_upper_upper))

    def set_wh_lower_state(self, fncs_str):
        """ Sets the lower element state attribute

        Args:
            fncs_str (str): FNCS message with ON/OFF status
        """
        if fncs_str == 'OFF':
            state = 0
        else:
            state = 1

        for i in range(len(self.states_bottom)):
            if self.states_bottom[i][0] == self.hour and self.states_bottom[i][1] == self.minute:
                self.states_bottom[i][2] = state
                for j in range(i + 1, len(self.states_bottom)):
                    self.states_bottom[j][2] = state
                break
            else:
                pass

    def set_wh_upper_state(self, fncs_str):
        """ Sets the upper element state attribute

        Args:
            fncs_str (str): FNCS message with ON/OFF status
        """
        if fncs_str == 'OFF':
            state = 0
        else:
            state = 1

        for i in range(len(self.states_upper)):
            if self.states_upper[i][0] == self.hour and self.states_upper[i][1] == self.minute:
                self.states_upper[i][2] = state
                for j in range(i + 1, len(self.states_upper)):
                    self.states_upper[j][2] = state
                break
            else:
                pass

    def set_wh_wd_rate_val(self, fncs_str):
        """ Sets the water draw rate attribute

        Args:
            fncs_str (str): FNCS message with wdrate value in gpm
        """
        val = parse_number(fncs_str)

        for i in range(len(self.wd_rate_val)):
            if self.wd_rate_val[i][0] == self.hour and self.wd_rate_val[i][1] == self.minute:
                self.wd_rate_val[i][2] = val
                for j in range(i + 1, len(self.wd_rate_val)):
                    self.wd_rate_val[j][2] = val
                break
            else:
                pass

    def set_wh_load(self, fncs_str):
        """ Sets the water heater load attribute, if greater than zero

        Args:
            fncs_str (str): FNCS message with load in kW
        """
        val = parse_number(fncs_str)
        if val > 0.0:
            self.Phw = val
        else:
            pass

    def from_P_to_Q_WH(self, BID, PRICE):
        """ Convert the 4 point bids to a quantity with the known price

        Args:
            BID (float) ((1,2)X4): 4 point bid
            PRICE (float): cleared price in $/kWh

        Returns:
            quantity (float): quantity to be consumed in the next 5-min
        """
        P = self.P
        Q = self.Q
        quantity = 0
        if PRICE >= BID[0][P]:
            quantity = BID[0][Q]
        elif PRICE <= BID[-1][P]:
            quantity = BID[-1][Q]
        else:
            for idx in range(1, len(BID)):
                if BID[idx][P] > PRICE > BID[idx + 1][P]:
                    quantity = (BID[idx + 1][Q] - BID[idx][Q]) * (BID[idx][P] - PRICE) / (BID[idx][P] - BID[idx + 1][P])
                    break
        return quantity

    def set_air_temp(self, fncs_str, model_diag_level, sim_time):
        """ Sets the air_temp attribute

        Args:
            fncs_str (str): FNCS message with temperature in degrees Fahrenheit
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human-readable
        """
        self.Tambient = parse_number(fncs_str)
    def test_function(self):
        """ Test function with the only purpose of returning the name of the object

        """
        return self.name

    def set_da_cleared_quantity(self, BID, PRICE):
        """ Convert the 4 point bids to a quantity with the known price

        Args:
            BID (float) ((1,2)X4): 4 point bid
            PRICE (float): cleared price in $/kWh

        Returns:
            quantity (float): cleared quantity
        """
        P = self.P
        Q = self.Q
        if PRICE >= BID[1][P]:
            if BID[0][P] == BID[1][P]:
                m = 0
            else:
                m = (BID[0][Q] - BID[1][Q]) / (BID[0][P] - BID[1][P])
            cleared_da_quantity = BID[1][Q] + m * (PRICE - BID[1][P])
        elif PRICE >= BID[2][P]:
            m = 0
            cleared_da_quantity = BID[2][Q]
        else:  # PRICE <= BID[2][P]
            if BID[2][P] == BID[3][P]:
                m = 0
            else:
                m = (BID[2][Q] - BID[3][Q]) / (BID[2][P] - BID[3][P])
            cleared_da_quantity = BID[2][Q] + m * (PRICE - BID[2][P])
        if cleared_da_quantity >= BID[3][Q]:
            cleared_da_quantity = BID[3][Q]
        elif cleared_da_quantity <= BID[0][Q]:
            cleared_da_quantity = BID[0][Q]

        return cleared_da_quantity

if __name__ == "__main__":
    def testing():
        wh_properties = {
            'wh_gallons': 54.99  # gal
        }
        wh_dict = {
            'Tcold': 70,  # degF
            'Tambient': 50,  # degF
            'Tdesired': 130,  # degF
            'Tmax': 160,  # degF
            'Tmin': 70,  # degF
            'windowLength': 48,
            'weight_SOHC': 0.66,
            'weight_comfort': 1,
            'ProfitMargin_intercept': 10,
            'ProfitMargin_slope': 0,
            'participating': True,
            'PriceCap': 1.0,
            'slider_setting': 0.0
        }
        
        ### Uncomment for testing logging functionality.
        ### Supply these values (into WaterHeaterDSOT) when using the water
        ### heater agent in the simulation.
        # model_diag_level = 11
        # hlprs.enable_logging('DEBUG', model_diag_level)
        sim_time = '2019-11-20 07:47:00'
        
        EWH = WaterHeaterDSOT(wh_dict, wh_properties, 'abc', 11, sim_time,'ipopt') # add model_diag_level, and sim_time
        his_data = np.genfromtxt('mocked_historical_data_WH.csv', delimiter=',', skip_header=1)
        T_bottom = his_data[:, 0]
        T_upper = his_data[:, 1]
        EWH.his_T_upper = T_upper.tolist()
        EWH.his_T_bottom = T_bottom.tolist()
        EWH.his_SOHC = ((T_bottom * (1 - EWH.weight_SOHC) + T_upper * EWH.weight_SOHC) / EWH.Tdesired * 100).tolist()
        EWH.his_wd_rate = (his_data[:, 4]).tolist()
        EWH.his_E_upper = (his_data[:, 3] / (15 * 12)).tolist()
        EWH.his_E_bottom = (his_data[:, 2] / (15 * 12)).tolist()
        #        EWH.set_wh_lower_temperature('130')
        #        EWH.set_wh_upper_temperature('130')
        #        EWH.update_WH_his()

        EWH.f_DA_price = [0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20, 0.20,
                          0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30,
                          0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20, 0.20,
                          0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30]
        EWH.f_DA_schedule = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 0.8, 0.8, 1.5, 1, 0.0, 0.2, 0.8, 0.0, 1.2, 1, 0.8, 2.5,
                             0, 0, 0, 0.0, 0.0,
                             0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.9, 1.8, 0.8, 1, 0.0, 0.4, 0.7, 0.0, 1, 1.5, 1.2, 2.6,
                             0, 0, 0, 0.0, 0.0]
        EWH.DA_cleared_prices = [0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20,
                                 0.20, 0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30,
                                 0.12, 0.13, 0.12, 0.11, 0.105, 0.14, 0.15, 0.16, 0.13, 0.15, 0.17, 0.18, 0.19, 0.20,
                                 0.20, 0.20, 0.19, 0.18, 0.16, 0.12, 0.15, 0.16, 0.32, 0.30]
        EWH.DA_cleared_quantities = [4.2, 0.0, 0.0, 4.1, 0.0, 0.0, 2.5, 3, 2.5, 4.5, 1, 0.0, 3, 1, 0.0, 1, 1, 3.5, 0, 0,
                                     0, 0, 0.0, 0.0,
                                     0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.7, 2.5, 2.5, 3.5, 1, 0.0, 2, 1, 0.0, 1, 1, 3, 4, 0,
                                     0, 0, 0.0, 0.0]

        #        print(EWH.formulate_bid_da())
        EWH.states_upper = [[1, 2, 1],
                            [1, 3, 1],
                            [1, 4, 0],
                            [1, 5, 0],
                            [1, 6, 1]]
        EWH.states_bottom = [[1, 2, 1],
                             [1, 3, 1],
                             [1, 4, 1],
                             [1, 5, 1],
                             [1, 6, 0]]
        print(EWH.formulate_bid_rt())


    testing()
