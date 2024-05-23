# Copyright (C) 2024 Battelle Memorial Institute
# file: hvac_agent_standalone_demo.py
"""
This is a simplified version of the DSO+T HVAC agent intended to demonstrate
how a real-time bid is formed and how a cleared bid is translated into a 
thermostat setpoint. It is intended to reflect the core logic from 
hvac_agent.py without requiring a co-simulation to run. It provides a place to 
play  around with the agent parameters and market operations to see how the 
agent responds.

This agent only implements the real-time bidding and thermostat adjustment. The
day-ahead market bidding is more complex and involves an internal model of the
structure along with an optimization formulation; this functionality is not
included in this version. Where results for that model are needed they are 
treated as hard-coded parameters. Similarly, market-clearing results are
hard-coded as well.

Author: trevor.hardy@pnnl.gov
(virutally all code lifted from hvac_agent.py with modest simplification)

"""
import logging as log
from math import cos as cos
from math import sin as sin
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import plotly.graph_objects as go

logger = log.getLogger()


# Key parameters for investigating the controller performance

ProfitMargin_intercept = 10
price_std_dev = 10 # Assumed value; just has to be > 0
hvac_kw = 5
Topt_DA = 72
my_quantity_curve = [0, 1.25, 2.5, 3.75, 5] # simplified vector showing the sensitivity of the HVAC load to air temperature

class HVACDSOT: 
    def __init__(self):
        # TODO: update inputs for class
        """ Initializes the class
        """

        self.setpoint_curve_x = []
        self.setpoint_curve_y = []

        # default temperatures in Fahrenheit
        self.T_lower_limit = 50
        self.T_upper_limit = 100

        self.cooling_setpoint_lower = 65
        self.cooling_setpoint_upper = 85
        self.heating_setpoint_lower = 60
        self.heating_setpoint_upper = 85

        self.basepoint_cooling = 85.0
        self.basepoint_heating = 55.0
        self.cooling_setpoint = 85.0
        self.heating_setpoint = 55.0

        self.deadband = 2

        # bid variables
        self.price_cap = 100

        self.ramp_high_limit = 5
        self.ramp_low_limit = 5
        self.range_high_limit = 5
        self.range_low_limit = 3

        self.slider = 0.5

        self.price_std_dev = price_std_dev

        # calculated in calc_thermostat_settings
        self.range_low_cool = 0.0
        self.range_high_cool = 0.0
        self.range_low_heat = 0.0
        self.range_high_heat = 0.0
        self.ramp_low_cool = 0.0
        self.ramp_high_cool = 0.0
        self.ramp_low_heat = 0.0
        self.ramp_high_heat = 0.0
        self.temp_max_cool = 0.0
        self.temp_min_cool = 0.0
        self.temp_max_heat = 0.0
        self.temp_min_heat = 0.0
        self.temp_max_cool_da = 0.0
        self.temp_min_cool_da = 0.0
        self.temp_max_heat_da = 0.0
        self.temp_min_heat_da = 0.0

        self.air_temp = 72.0
        self.mass_temp = 72.0
        self.hvac_kw = hvac_kw
        self.wh_kw = 0.0
        self.house_kw = 5.0
        self.mtr_v = 120.0
        self.hvac_on = False
        self.minute = 0
        self.hour = 0
        self.day = 0
        self.Qopt_da_prev = 0
        self.temp_da_prev = 75.0
        self.DA_once_flag = False
        self.air_temp_agent = 72.0
        self.bid_rt_price = 0.0
        self.Qi = 0.0
        self.Qh = 0.0
        self.Qa_ON = 0.0
        self.Qa_OFF = 0.0
        self.Qm = 0.0
        self.Qs = 0.0

        # interpolation
        self.interpolation = bool(True)
        self.RT_minute_count_interpolation = float(0.0)
        self.previous_Q_DA = float(0.0)
        self.previous_T_DA = float(0.0)
        self.delta_Q = float(0.0)
        self.delta_T = float(0.0)
        self.delta_DA_price = 0

        self.max_price_forecast = 50
        self.price_forecast_0 = 50

        self.bid_quantity = 0.0
        self.bid_quantity_rt = 0.0

        self.thermostat_mode = 'Cooling'  # can be 'Cooling' or 'Heating'
        self.cleared_price = 50
        self.bid_rt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
        self.bid_da = [[[0., 0.], [0., 0.], [0., 0.], [0., 0.]]] * 48
        self.quantity_curve = [0 for _ in range(10)]
        self.temp_curve = [0]

        self.moh = 0
        self.hod = 0
        self.dow = 0

        self.T = 1

        self.calc_thermostat_settings()

        self.ProfitMargin_intercept = ProfitMargin_intercept 


        # using the initial hvac kW - will update before every use
        Qmin = 0
        Qmax = self.hvac_kw
        
        self.plotting_data = {"bid_curve": {
                "bid_x": [],
                "bid_y": [],
                "clearing_price_x": [],
                "clearing_price_y": [],
                "clearing_quantity_x": [],
                "clearing_quantity_y": []
                },
            "thermostat_curve": {
                "thermostat_x": [],
                "thermostat_y": [],
                "setpoint_x": [],
                "setpoint_y": [],
                "clearing_quantity_x": [],
                "clearing_quantity_y": []
                }
            }


    def calc_thermostat_settings(self):
        """ Sets the ETP parameters from configuration data

        Args:
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human-readable

        References:
            `Table 3 -  Easy to use slider settings <http://gridlab-d.shoutwiki.com/wiki/Transactive_controls>`_
        """

        self.range_high_cool = self.range_high_limit * self.slider  
        self.range_low_cool = self.range_low_limit * self.slider  
        self.range_high_heat = self.range_high_limit * self.slider  
        self.range_low_heat = self.range_low_limit * self.slider  

        if self.slider != 0:
            # cooling
            self.ramp_high_cool = self.ramp_high_limit * (1 - self.slider) 
            self.ramp_low_cool = self.ramp_low_limit * (1 - self.slider)  
            # heating
            self.ramp_high_heat = self.ramp_low_limit * (1 - self.slider)  
            self.ramp_low_heat = self.ramp_high_limit * (1 - self.slider)  
        else:
            # cooling
            self.ramp_high_cool = 0.0
            self.ramp_low_cool = 0.0
            # heating
            self.ramp_high_heat = 0.0
            self.ramp_low_heat = 0.0

        if self.basepoint_cooling - self.deadband / 2.0 - 0.5 < self.basepoint_heating + self.deadband / 2.0 + 0.5:
            # update minimum cooling and maximum heating temperatures
            mid_point = (self.basepoint_cooling + self.basepoint_heating) / 2.0
            self.basepoint_cooling = mid_point + self.deadband / 2.0 + 0.5

            self.basepoint_heating = mid_point - self.deadband / 2.0 - 0.5

        cooling_setpt = self.basepoint_cooling
        heating_setpt = self.basepoint_heating
        self.temp_max_cool = cooling_setpt + self.range_high_cool  
        self.temp_min_cool = cooling_setpt - self.range_low_cool  
        self.temp_max_heat = heating_setpt + self.range_high_heat  
        self.temp_min_heat = heating_setpt - self.range_low_heat  
        if self.temp_max_heat + self.deadband / 2.0 + 0.5 > self.temp_min_cool - self.deadband / 2.0 - 0.5:
            mid_point = (self.temp_min_cool + self.temp_max_heat) / 2.0
            self.temp_min_cool = mid_point + self.deadband / 2.0 + 0.5
            self.temp_max_heat = mid_point - self.deadband / 2.0 - 0.5
            if self.temp_min_cool > cooling_setpt:
                self.temp_min_cool = cooling_setpt
            if self.temp_max_heat < heating_setpt:
                self.temp_max_heat = heating_setpt

    def bid_accepted(self):
        """ Update the thermostat setting if the last bid was accepted

        The last bid is always "accepted". If it wasn't high enough,
        then the thermostat could be turned up.

        Args:
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human-readable

        Returns:
            bool: True if the thermostat setting changes, False if not.
        """
        self.setpoint_curve_x = []
        self.setpoint_curve_y = []

        if self.thermostat_mode == 'Cooling':
            setpoint_tmp = self.basepoint_cooling
        elif self.thermostat_mode == 'Heating':
            basepoint_tmp = self.basepoint_heating
        else:
            basepoint_tmp = 70.0  # default value that is ok for both operating points
        # using price forecast [0] instead of mean
        price_curve = [self.bid_rt[0][1], self.bid_rt[1][1], self.bid_rt[2][1], self.bid_rt[3][1]]
        quantity_curve = [self.bid_rt[0][0], self.bid_rt[1][0], self.bid_rt[2][0], self.bid_rt[3][0]]

        if price_curve[1] <= self.cleared_price <= price_curve[0]:
            if price_curve[1] != price_curve[0]:
                a = (quantity_curve[1] - quantity_curve[0]) / (price_curve[1] - price_curve[0])
            else:
                a = 0
            b = quantity_curve[0] - a * price_curve[0]
            self.bid_quantity = a * self.cleared_price + b
        elif price_curve[1] >= self.cleared_price >= price_curve[2]:
            if price_curve[2] != price_curve[1]:
                a = (quantity_curve[2] - quantity_curve[1]) / (price_curve[2] - price_curve[1])
            else:
                a = 0
            b = quantity_curve[1] - a * price_curve[1]
            self.bid_quantity = a * self.cleared_price + b
        elif price_curve[2] >= self.cleared_price >= price_curve[3]:
            if price_curve[3] != price_curve[2]:
                a = (quantity_curve[3] - quantity_curve[2]) / (price_curve[3] - price_curve[2])
            else:
                a = 0
            b = quantity_curve[2] - a * price_curve[2]
            self.bid_quantity = a * self.cleared_price + b
        elif self.cleared_price > price_curve[0]:
            self.bid_quantity = quantity_curve[0]  # assuming this is minimum
        elif self.cleared_price < price_curve[3]:
            self.bid_quantity = quantity_curve[3]  # assuming this is maximum
        else:
            self.bid_quantity = 0
            print("something went wrong with clear price")

        if self.price_std_dev > 0.0:
            if self.thermostat_mode == 'Cooling':
                ramp_high_tmp = self.ramp_high_cool
                ramp_low_tmp = self.ramp_low_cool
                setpoint_tmp = self.cooling_setpoint
            else: # "Heating"
                ramp_high_tmp = self.ramp_high_heat
                ramp_low_tmp = self.ramp_low_heat
                setpoint_tmp = self.heating_setpoint
            use_RT_curve = True
            if use_RT_curve:
                if max(self.quantity_curve) == 0:
                    self.bid_quantity = 0.0
                    if self.thermostat_mode == "Cooling":
                        setpoint_tmp = self.temp_max_cool  # self.cooling_setpoint
                    else:
                        setpoint_tmp = self.temp_min_heat
                elif self.bid_quantity >= max(self.quantity_curve):
                    if self.thermostat_mode == "Cooling":
                        setpoint_tmp = min(self.temp_curve)
                    else:
                        setpoint_tmp = max(self.temp_curve)
                else:
                    for ipt in range(len(self.temp_curve) - 1):
                        if self.quantity_curve[ipt + 1] != self.quantity_curve[ipt]:
                            a = (self.temp_curve[ipt + 1] - self.temp_curve[ipt]) / \
                                (self.quantity_curve[ipt + 1] - self.quantity_curve[ipt])
                        else:
                            a = 0
                        b = self.temp_curve[ipt] - a * self.quantity_curve[ipt]
                        self.setpoint_curve_x.append(self.quantity_curve[ipt])
                        self.setpoint_curve_y.append(a * self.bid_quantity + b)
                        if self.quantity_curve[ipt] <= self.bid_quantity <= self.quantity_curve[ipt + 1]:
                            setpoint_tmp = a * self.bid_quantity + b
            returnflag = True
        else:
            setpoint_tmp = basepoint_tmp
            returnflag = False

        if self.thermostat_mode == 'Cooling':
            self.cooling_setpoint = setpoint_tmp
        else:
            self.heating_setpoint = setpoint_tmp
        if self.heating_setpoint + self.deadband / 2.0 >= self.cooling_setpoint - self.deadband / 2.0:
            if self.thermostat_mode == 'Heating':
                # push cooling_setpoint up
                self.cooling_setpoint = self.heating_setpoint + self.deadband
            else:
                # push heating_setpoint down
                self.heating_setpoint = self.cooling_setpoint - self.deadband
        return returnflag, setpoint_tmp
    
    
    def formulate_bid_rt(self):
        """ (Simplified) Bid to run the air conditioner through the next period for real-time

        Returns:
            [[float, float], [float, float], [float, float], [float, float]]: [bid price $/kwh, bid quantity kW] x 4
        """
        T = self.T
        time = np.linspace(0, T, num=10)  # [0,topt-dt, topt, topt+dt]
        # TODO: this needs to be more generic, like a function of slider
        npt = 5
        self.temp_curve = []
        self.quantity_curve = []
        for i in range(npt):
            self.temp_curve.append(Topt_DA + (i - 2) / 4.0 * self.slider)
            self.quantity_curve.append(0.0)


        for itemp in range(npt):
            x = np.zeros([2, 1])
            x[0] = self.air_temp
            x[1] = self.mass_temp
            Q_max = self.hvac_kw
            Q_min = 0.0

            # self.temp_curve[0] = self.air_temp
            if ((self.thermostat_mode == "Cooling" and self.hvac_on) or
                    (self.thermostat_mode != "Cooling" and not self.hvac_on)):
                self.temp_curve[0] = self.air_temp + self.deadband / 2.0
            elif ((self.thermostat_mode != "Cooling" and self.hvac_on) or
                  (self.thermostat_mode == "Cooling" and not self.hvac_on)):
                self.temp_curve[0] = self.air_temp - self.deadband / 2.0
        
        self.quantity_curve = my_quantity_curve 
        Qopt_DA = self.hvac_kw/2 # simplified value, assumes operating at 50% of the time
        Qmin = 0
        Qmax = self.hvac_kw
        if self.slider != 0:
            self.ProfitMargin_slope = self.delta_DA_price / (Qmin - Qmax) / self.slider
        else:
            self.ProfitMargin_slope = 9999  # just a large value to prevent errors when slider=0


        BID = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        P = 1
        Q = 0
        if Q_min != Q_max:
            CurveSlope = (self.delta_DA_price / (0 - self.hvac_kw) * (1 + self.ProfitMargin_slope / 100))
            yIntercept = self.price_forecast_0 - CurveSlope * Qopt_DA
            if Q_max > Qopt_DA > Q_min:
                BID[0][Q] = Q_min
                BID[1][Q] = Qopt_DA
                BID[2][Q] = Qopt_DA
                BID[3][Q] = Q_max

                BID[0][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * self.delta_DA_price
                BID[1][P] = Qopt_DA * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * self.delta_DA_price
                BID[2][P] = Qopt_DA * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * self.delta_DA_price
                BID[3][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * self.delta_DA_price
            else:
                BID[0][Q] = Q_min
                BID[1][Q] = Q_min
                BID[2][Q] = Q_max
                BID[3][Q] = Q_max

                BID[0][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * self.delta_DA_price
                BID[1][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * self.delta_DA_price
                BID[2][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * self.delta_DA_price
                BID[3][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * self.delta_DA_price
        else:
            BID[0][Q] = Q_min
            BID[1][Q] = Q_min
            BID[2][Q] = Q_max
            BID[3][Q] = Q_max

            # Modified defition to make max(price_forecast) now a single parameter "max_price_forecast"
            BID[0][P] = self.max_price_forecast + (self.ProfitMargin_intercept / 100) * self.delta_DA_price
            BID[1][P] = self.max_price_forecast + (self.ProfitMargin_intercept / 100) * self.delta_DA_price
            BID[2][P] = self.max_price_forecast - (self.ProfitMargin_intercept / 100) * self.delta_DA_price
            BID[3][P] = self.max_price_forecast - (self.ProfitMargin_intercept / 100) * self.delta_DA_price

        for i in range(4):
            if BID[i][Q] > self.hvac_kw:
                BID[i][Q] = self.hvac_kw
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
        self.RT_minute_count_interpolation = self.RT_minute_count_interpolation + 5.0
        return self.bid_rt
    
    def plot_curves(self):
        """
        Stand-alone, non-interactive graph of the bid curve and thermostat
        curve
        """
        clearing_quantity_x = [self.bid_quantity, self.bid_quantity]
        fig, axs = plt.subplots(2)
        axs[0].set_title("Bid Curve")
        axs[0].set_xlabel(f"Bid Quantity (kW) - Cleared Quantity = {self.bid_quantity:0.2f}")
        axs[0].set_ylabel(f"Bid Price ($/kW) - Cleared Price = {self.cleared_price:0.2f}")
        q = []
        p = []
        for point in self.bid_rt:
            q.append(point[0])
            p.append(point[1])
        axs[0].plot(q,p)
        clearing_quantity_y = [0, self.cleared_price]
        axs[0].plot(clearing_quantity_x, clearing_quantity_y)
        clearing_price_x = [0, self.bid_quantity]
        clearing_price_y = [self.cleared_price, self.cleared_price]
        axs[0].plot(clearing_price_x, clearing_price_y)

        axs[1].set_title("Thermostat Curve")
        axs[1].set_xlabel(f"Bid Quantity (kW) - Cleared Quantity = {self.bid_quantity:0.2f}")
        axs[1].set_ylabel(f"Thermostat Setpoint ('F) - Cleared Sepoint = {self.cooling_setpoint:.2f}")
        axs[1].plot(self.setpoint_curve_x, self.setpoint_curve_y)
        clearing_quantity_y = [self.cooling_setpoint_lower, self.cooling_setpoint_upper]
        axs[1].plot(clearing_quantity_x, clearing_quantity_y)
        clearing_setpoint_x = [0, self.bid_quantity]
        clearing_setpoint_y = [self.cooling_setpoint, self.cooling_setpoint]
        axs[1].plot(clearing_setpoint_x, clearing_setpoint_y)
        plt.show()
        dummy = 0

    def collect_bid_curve_data(self):
        """
        Pulls data from the hvac_agent object and restructures it for easier
        plotting
        """
        q = []
        p = []
        for point in self.bid_rt:
            q.append(point[0])
            p.append(point[1])
        self.plotting_data["bid_curve"]["bid_x"] = q
        self.plotting_data["bid_curve"]["bid_y"] = p
        self.plotting_data["bid_curve"]["clearing_price_x"] = [0, self.bid_quantity]
        self.plotting_data["bid_curve"]["clearing_price_y"] = [self.cleared_price, self.cleared_price]
        self.plotting_data["bid_curve"]["clearing_quantity_x"] = [self.bid_quantity, self.bid_quantity]
        self.plotting_data["bid_curve"]["clearing_quantity_y"] = [0, self.cleared_price]


if __name__ == "__main__":
    """
    Creates an interactive plot showing the sensitivity of the hvac_agent to
    various parameters.
    """
    hvac_agent = HVACDSOT()
    init_slider = 0.5
    init_cleared_price = 50
    init_delta_DA_price = 20
    init_ProfitMargin_intercept = 10

    def run_model(slider, cleared_price, delta_DA_price, ProfitMargin_intercept):
        hvac_agent.slider = slider
        hvac_agent.cleared_price = cleared_price
        hvac_agent.delta_DA_price = delta_DA_price
        hvac_agent.ProfitMargin_intercept = ProfitMargin_intercept
        rt_bid = hvac_agent.formulate_bid_rt()
        setpoint_change, setpoint_tmp = hvac_agent.bid_accepted()
        hvac_agent.collect_bid_curve_data()
        return setpoint_tmp

    # The function to be called anytime a slider's value changes
    def update(val):
        setpoint = run_model(slider_setting.val, 
                             cleared_price_setting.val, 
                             delta_DA_price_setting.val,
                             ProfitMargin_intercept_setting.val)
        bid_line.set_ydata(hvac_agent.plotting_data["bid_curve"]["bid_y"])
        clear_q_line_bid.set_xdata(hvac_agent.plotting_data["bid_curve"]["clearing_quantity_x"])
        clear_q_line_bid.set_ydata(hvac_agent.plotting_data["bid_curve"]["clearing_quantity_y"])
        clear_p_line_bid.set_xdata(hvac_agent.plotting_data["bid_curve"]["clearing_price_x"])
        clear_p_line_bid.set_ydata(hvac_agent.plotting_data["bid_curve"]["clearing_price_y"])
        thermostat_line.set_ydata(hvac_agent.setpoint_curve_y)
        clear_q_line_thermostat.set_xdata(hvac_agent.plotting_data["bid_curve"]["clearing_quantity_x"])
        clear_q_line_thermostat.set_ydata([0, setpoint])
        clear_t_line_thermostat.set_ydata([setpoint, setpoint])
        clear_t_line_thermostat.set_xdata([0, hvac_agent.bid_quantity])
        fig.canvas.draw_idle()
    

    fig, ax = plt.subplots(2)
    fig.subplots_adjust(bottom=0.55) # making room for sliders
    fig.suptitle("DSO+T HVAC Agent Behavior in Cooling Mode")
    ax[0].set_xlabel('Quantity (kW)')
    ax[0].set_ylabel('Cleared Price ($/kW)')
    ax[0].set_xlim([0, hvac_agent.hvac_kw])
    ax[0].set_ylim([0, hvac_agent.price_cap])
    ax[1].set_xlabel('Quantity (kW)')
    ax[1].set_ylabel('Thermostat Setpoint (\u00B0F)')
    ax[1].set_xlim([0, hvac_agent.hvac_kw])
    ax[1].set_ylim([55, 85])

    # Calculating model to create data for initial plots
    setpoint = run_model(init_slider, init_cleared_price, init_delta_DA_price, init_ProfitMargin_intercept)

    # Add lines for the bid curve, thermostat curve.
    # Also add lines that show where the clearing quantity, price and thermostat
    #  setpoint are on these two curves
    bid_line, = ax[0].plot(hvac_agent.plotting_data["bid_curve"]["bid_x"], 
                           hvac_agent.plotting_data["bid_curve"]["bid_y"], 
                           lw=2)
    clear_q_line_bid, = ax[0].plot(hvac_agent.plotting_data["bid_curve"]["clearing_quantity_x"], 
                                   hvac_agent.plotting_data["bid_curve"]["clearing_quantity_y"], 
                                   lw=2)
    clear_p_line_bid, = ax[0].plot(hvac_agent.plotting_data["bid_curve"]["clearing_price_x"], 
                                   hvac_agent.plotting_data["bid_curve"]["clearing_price_y"], 
                                   lw=2)

    thermostat_line, = ax[1].plot(hvac_agent.setpoint_curve_x, hvac_agent.setpoint_curve_y, lw=2)
    clear_q_line_thermostat, = ax[1].plot(hvac_agent.plotting_data["bid_curve"]["clearing_quantity_x"], 
                                          [0, setpoint],
                                          lw=2)
    clear_t_line_thermostat, = ax[1].plot([0, hvac_agent.bid_quantity], 
                                          [setpoint, setpoint], 
                                          lw=2)

   
    

    # Add sliders for the parameters we want to adjust
    ax_slider_setting = fig.add_axes([0.25, 0.4, 0.65, 0.03]) #axis box dimensions and location
    slider_setting = Slider(
        ax=ax_slider_setting,
        label='Slider Setting',
        valmin=0.1,
        valmax=1,
        valinit=init_slider,
    )    
    ax_cleared_price = fig.add_axes([0.25, 0.3, 0.65, 0.03]) #axis box dimensions and location
    cleared_price_setting = Slider(
        ax=ax_cleared_price,
        label='Cleared Price',
        valmin=1,
        valmax=100,
        valinit=init_cleared_price,
    ) 
    ax_delta_DA_price = fig.add_axes([0.25, 0.2, 0.65, 0.03]) #axis box dimensions and location
    delta_DA_price_setting = Slider(
        ax=ax_delta_DA_price,
        label='Delta DA price',
        valmin=1,
        valmax=100,
        valinit=init_delta_DA_price,
    )  
    ax_ProfitMargin_intercept = fig.add_axes([0.25, 0.1, 0.65, 0.03]) #axis box dimensions and location
    ProfitMargin_intercept_setting = Slider(
        ax=ax_ProfitMargin_intercept,
        label='Profit Margin Intercept',
        valmin=1,
        valmax=100,
        valinit=init_ProfitMargin_intercept,
    )
    
    # Register the update function for each slider; whenever the slider position
    #  is changed, the methods defned below change
    slider_setting.on_changed(update)
    delta_DA_price_setting.on_changed(update)
    cleared_price_setting.on_changed(update)
    ProfitMargin_intercept_setting.on_changed(update)
    
    plt.show()
    

    