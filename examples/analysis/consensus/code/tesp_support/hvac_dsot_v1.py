# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: hvac_dsot_v1.py
"""Class that ...

TODO: update the purpose of this Agent

"""
import math
import numpy as np
import tesp_support.helpers as helpers
import logging as log
from scipy import linalg
import pulp
from math import cos as cos
from math import sin as sin
import pytz
import pyomo.environ as pyo
import pyomo.opt as opt
from datetime import datetime, timedelta

logger = log.getLogger()

log.getLogger('pyomo.core').setLevel(log.ERROR)


class HVACDSOT:  # TODO: update class name
    """This agent ...

    TODO: update the purpose of this Agent

    Args:
        TODO: update inputs for this agent
        model_diag_level (int): Specific level for logging errors; set it to 11
        sim_time (str): Current time in the simulation; should be human readable

    Attributes:
        TODO: update attributes for this agent

    """

    def __init__(self, hvac_dict, house_properties, key, model_diag_level, sim_time, solver):  # TODO: update inputs for class
        """Initializes the class
        """
        # TODO: update attributes of class
        self.name = key
        self.solver = solver
        self.houseName = hvac_dict['houseName']
        self.meterName = hvac_dict['meterName']
        self.period = float(hvac_dict['period'])
        self.wakeup_start = float(hvac_dict['wakeup_start'])
        self.daylight_start = float(hvac_dict['daylight_start'])
        self.evening_start = float(hvac_dict['evening_start'])
        self.night_start = float(hvac_dict['night_start'])
        self.weekend_day_start = float(hvac_dict['weekend_day_start'])
        self.weekend_night_start = float(hvac_dict['weekend_night_start'])
        self.wakeup_set_cool = float(hvac_dict['wakeup_set_cool'])
        self.daylight_set_cool = float(hvac_dict['daylight_set_cool'])
        self.evening_set_cool = float(hvac_dict['evening_set_cool'])
        self.night_set_cool = float(hvac_dict['night_set_cool'])
        self.weekend_day_set_cool = float(hvac_dict['weekend_day_set_cool'])
        self.weekend_night_set_cool = float(hvac_dict['weekend_night_set_cool'])
        self.wakeup_set_heat = float(hvac_dict['wakeup_set_heat'])
        self.daylight_set_heat = float(hvac_dict['daylight_set_heat'])
        self.evening_set_heat = float(hvac_dict['evening_set_heat'])
        self.night_set_heat = float(hvac_dict['night_set_heat'])
        self.weekend_day_set_heat = float(hvac_dict['weekend_day_set_heat'])
        self.weekend_night_set_heat = float(hvac_dict['weekend_night_set_heat'])
        self.deadband = float(hvac_dict['deadband'])
        self.price_cap = float(hvac_dict['price_cap'])
        self.bid_delay = float(hvac_dict['bid_delay'])
        self.ramp_high_limit = float(hvac_dict['ramp_high_limit'])
        self.ramp_low_limit = float(hvac_dict['ramp_low_limit'])
        self.range_high_limit = float(hvac_dict['range_high_limit'])
        self.range_low_limit = float(hvac_dict['range_low_limit'])
        self.slider = float(hvac_dict['slider_setting'])
        # self.participating = hvac_dict['house_participating']
        self.cooling_participating = hvac_dict['cooling_participating']
        self.heating_participating = hvac_dict['heating_participating']
        self.participating = self.cooling_participating or self.heating_participating
        self.windowLength = 48
        self.TIME = range(self.windowLength)
        self.optimized_Quantity = [[]] * self.windowLength
        #  calculated in calc_thermostat_settings
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

        self.price_forecast = [0 for i in range(48)]  # np.random.rand(1)[0]
        self.price_forecast_0 = 0
        self.price_std_dev = 0.0
        self.price_delta = 0.0
        self.price_mean = 0.0

        self.temperature_forecast = [75.0 for i in range(48)]  # np.random.rand(1)[0]
        self.temp_min_48hour = 74.0
        self.temp_max_48hour = 76.0
        self.temp_delta = self.temp_max_48hour - self.temp_min_48hour

        self.humidity_forecast = [0.5 for i in range(48)]
        self.solargain_forecast = [0.0 for i in range(48)]
        self.internalgain_forecast = [0.0 for i in range(48)]

        self.air_temp = 72.0
        self.mass_temp = 72.0
        self.hvac_kw = 100.0
        self.wh_kw = 1.0
        self.house_kw = 5.0
        self.mtr_v = 120.0
        self.hvac_on = False
        # self.hvac_demand = 1.0
        self.minute = 0
        self.hour = 0
        self.day = 0
        self.DA_once_flag = False
        self.air_temp_agent = 72.0
        self.bid_rt_price = 0.0
        self.Qi = 0.0
        self.Qh = 0.0
        self.Qa_ON = 0.0
        self.Qa_OFF = 0.0
        self.Qm = 0.0
        self.Qs = 0.0
        self.bid_quantity = 0.0
        self.basepoint_cooling = 75.0
        self.basepoint_heating = 65.0
        self.cooling_setpoint = 75.0
        self.heating_setpoint = 65.0
        self.thermostat_mode = 'OFF'  # can be 'Cooling' or 'Heating'
        self.cleared_price = 0.0
        self.bid_rt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
        self.bid_da = [[[0., 0.], [0., 0.], [0., 0.], [0., 0.]]] * 48

        # ETP model parameters
        self.sqft = float(house_properties['sqft'])
        self.stories = float(house_properties['stories'])
        self.doors = float(house_properties['doors'])
        self.thermal_integrity = house_properties['thermal_integrity']
        self.Rroof = float(house_properties['Rroof'])
        self.Rwall = float(house_properties['Rwall'])
        self.Rfloor = float(house_properties['Rfloor'])
        self.Rdoors = float(house_properties['Rdoors'])
        self.airchange_per_hour = float(house_properties['airchange_per_hour'])
        self.ceiling_height = int(house_properties['ceiling_height'])
        self.thermal_mass_per_floor_area = float(house_properties['thermal_mass_per_floor_area'])
        self.aspect_ratio = float(house_properties['aspect_ratio'])
        self.exterior_ceiling_fraction = float(house_properties['exterior_ceiling_fraction'])
        self.exterior_floor_fraction = float(house_properties['exterior_floor_fraction'])
        self.exterior_wall_fraction = float(house_properties['exterior_wall_fraction'])
        self.WETC = float(house_properties['window_exterior_transmission_coefficient'])
        self.glazing_layers = int(house_properties['glazing_layers'])
        self.glass_type = int(house_properties['glass_type'])
        self.window_frame = int(house_properties['window_frame'])
        self.glazing_treatment = int(house_properties['glazing_treatment'])
        self.cooling_COP = 3.5  # float(house_properties['cooling_COP'])
        self.heating_COP = 2.5
        self.cooling_cop_adj_rt = 3.5
        self.heating_cop_adj_rt = 2.5
        self.cooling_cop_adj = [self.cooling_COP for t in range(self.windowLength)]
        self.heating_cop_adj = [self.heating_COP for t in range(self.windowLength)]
        # Coefficients to adjust COP and capacity
        self.cooling_COP_K0 = -0.01363961
        self.cooling_COP_K1 = 0.01066989
        self.cooling_COP_limit = 40

        self.heating_COP_K0 = 2.03914613
        self.heating_COP_K1 = -0.03906753
        self.heating_COP_K2 = 0.00045617
        self.heating_COP_K3 = -0.00000203
        self.heating_COP_limit = 80
        self.heating_COP = float(house_properties['cooling_COP']) - 1
        # TODO: need to know source of cooling COP and why not heating
        self.cooling_capacity_K0 = 1.48924533
        self.cooling_capacity_K1 = -0.00514995
        self.cooling_COP = float(house_properties['cooling_COP'])

        self.latent_load_fraction = 0.3
        self.latent_factor = [self.latent_load_fraction for t in self.TIME]
        self.cooling_design_temperature = 95.0
        self.design_cooling_setpoint = 75.0
        self.design_internal_gains = 167.09 * self.sqft ** 0.442
        self.design_peak_solar = 195.0
        self.over_sizing_factor = float(house_properties['over_sizing_factor'])
        self.heating_system_type = (house_properties['heating'])
        self.cooling_system_type = (house_properties['cooling'])
        self.design_heating_setpoint = 70.0
        self.heating_design_temperature = 0.0  # TODO: not sure where to get this (guess for now)

        self.heating_capacity_K0 = 0.34148808
        self.heating_capacity_K1 = 0.00894102
        self.heating_capacity_K2 = 0.00010787

        self.design_heating_capacity = 0.0
        self.design_cooling_capacity = 0.0

        # weather variables
        self.solar_direct = 0.0
        self.solar_diffuse = 0.0
        self.outside_air_temperature = 80.0
        self.humidity = 0.8

        # TODO: for debugging only
        self.moh = 0
        self.hod = 0
        self.dow = 0
        self.FirstTime = True
        # variables to be used in solargain calculation
        self.surface_angles = {
            'H': 360,
            'N': 180,
            'NE': 135,
            'E': 90,
            'SE': 45,
            'S': 0,
            'SW': -45,
            'W': -90,
            'NW': -135
        }

        # calculated in calc_etp_model
        self.UA = 0.
        self.CA = 0.
        self.HM = 0.
        self.CM = 0.
        self.mass_internal_gain_fraction = 0.
        self.mass_solar_gain_fraction = 0.
        self.solar_heatgain_factor = 0.
        self.solar_heatgain = 0.0
        self.solar_gain = 0.0

        self.calc_thermostat_settings(model_diag_level, sim_time)
        self.calc_etp_model()

        self.temp_room = [78.0 for i in range(48)]
        # self.temp_out_48hour = [90.0 for i in range(48)]
        self.temp_desired_48hour_cool = [75.0 for i in range(self.windowLength)]
        self.temp_desired_48hour_heat = [70.0 for i in range(self.windowLength)]
        self.temp_room_init = 78.0
        self.temp_room_previous_cool = 68.0
        self.temp_room_previous_heat = 65.0
        self.temp_outside_init = 80.0
        self.eps = 0.
        self.COP = 0.
        self.K1 = 0.
        self.K2 = 0.
        #self.calc_1st_etp_model()  # approximate etp model to 1st order for DA
        self.eps = math.exp(-self.UA / (self.CM + self.CA) * 1.0)  # using 1 fixed for time constant

        self.ProfitMargin_intercept = 10  # hvac_dict['ProfitMargin_intercept']

        # using the initial hvac kW - will update before every use
        Qmin = 0
        Qmax = self.hvac_kw
        delta_DA_price = max(self.price_forecast) - min(self.price_forecast)
        if self.slider!=0:
            self.ProfitMargin_slope = delta_DA_price/(Qmin-Qmax)/self.slider # 0  # hvac_dict['ProfitMargin_slope']
        else:
            self.ProfitMargin_slope = 9999 # just a large value to prevent errors when slider=0

        ### Sanity checks:
        if self.wakeup_start <= self.daylight_start:
            # log.info('wakeup_start is < daylight_start.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- wakeup_start ({}) is not < daylight_start ({}).'
                    .format(self.name, 'init', self.wakeup_start, self.daylight_start))
        if self.daylight_start <= self.evening_start:
            # log.info('daylight_start is < evening_start.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- daylight_start ({}) is not < evening_start ({}).'
                    .format(self.name, 'init', self.daylight_start, self.evening_start))
        if self.evening_start <= self.night_start:
            # log.info('evening_start is < night_start.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- evening_start ({}) is not < night_start ({}).'
                    .format(self.name, 'init', self.evening_start, self.night_start))
        if self.weekend_day_start <= self.weekend_night_start:
            # log.info('weekend_day_start is < weekend_night_start.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- weekend_day_start ({}) is not < weekend_night_start ({}).'
                    .format(self.name, 'init', self.weekend_day_start, self.weekend_night_start))
        # if self.wakeup_set_heat >= self.night_set_heat:
        #     # log.info('wakeup_set_heat is >= night_set_heat.')
        #     pass
        # else:
        #     log.log(model_diag_level, '{} {} -- wakeup_set_heat ({}) is not >= night_set_heat ({}) .'.format(self.name, 'init', self.wakeup_set_heat, self.night_set_heat))
        if self.daylight_set_heat <= self.night_set_heat:
            # log.info('daylight_set_heat is >= night_set_heat.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- daylight_set_heat ({}) is not <= night_set_heat ({}).'
                    .format(self.name, 'init', self.daylight_set_heat, self.night_set_heat))
        if self.daylight_set_heat <= self.wakeup_set_heat:
            # log.info('daylight_set_heat is <= wakeup_set_heat.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- daylight_set_heat ({}) is not <= wakeup_set_heat ({}).'
                    .format(self.name, 'init', self.daylight_set_heat, self.wakeup_set_heat))
        if "zone" not in self.name:
            if self.daylight_set_cool >= self.night_set_cool:
                # log.info('daylight_set_cool is >= night_set_cool.')
                pass
            else:
                log.log(model_diag_level,
                        '{} {} -- daylight_set_cool ({}) is not >= night_set_cool ({}).'
                        .format(self.name, 'init', self.daylight_set_cool, self.night_set_cool))
            if self.daylight_set_cool >= self.wakeup_set_cool:
                # log.info('daylight_set_cool is >= wakeup_set_cool.')
                pass
            else:
                log.log(model_diag_level,
                        '{} {} -- daylight_set_cool ({}) is not >= wakeup_set_cool ({}).'
                        .format(self.name, 'init', self.daylight_set_cool, self.wakeup_set_cool))
        # if self.evening_set_heat >= self.night_set_heat:
        #     # log.info('evening_set_heat is >= night_set_heat.')
        #     pass
        # else:
        #     log.log(model_diag_level, '{} {} -- evening_set_heat ({}) is not >= night_set_heat ({}).'.format(self.name, 'init', self.evening_set_heat, self.night_set_heat))
        # if self.weekend_day_set_heat >= self.weekend_night_set_heat:
        #     # log.info('weekend_day_set_heat is >= weekend_night_set_heat.')
        #     pass
        # else:
        #     log.log(model_diag_level, '{} {} -- weekend_day_set_heat ({}) is not >= weekend_night_set_heat ({}).'.format(self.name, 'init', self.weekend_day_set_heat, self.weekend_night_set_heat))
        if self.sqft > 0:
            # log.info('number of sqft is > 0.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- number of sqft ({}) is negative value'
                    .format(self.name, 'init', self.sqft))
        if self.stories > 0:
            # log.info('number of stories is > 0.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- number of stories ({}) is negative'
                    .format(self.name, 'init', self.stories))
        if self.doors >= 0:
            # log.info('number of doors is > 0.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- number of doors ({}) is negative'
                    .format(self.name, 'init', self.doors))

        Rroof_lower = 2
        Rroof_upper = 60
        if Rroof_lower <= self.Rroof < Rroof_upper:
            # log.info('Rroof is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} --  Rroof is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rroof, Rroof_lower, Rroof_upper))

        Rwall_lower = 2
        Rwall_upper = 40
        if Rwall_lower <= self.Rwall < Rwall_upper:
            # log.info('Rwall is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Rwall is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rwall, Rwall_lower, Rwall_upper))

        Rfloor_lower = 2
        Rfloor_upper = 40
        if Rfloor_lower <= self.Rfloor < Rfloor_upper:
            # log.info('Rfloor is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Rfloor is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rfloor, Rfloor_lower, Rfloor_upper))

        Rdoor_lower = 1
        Rdoor_upper = 20
        if Rdoor_lower <= self.Rdoors < Rdoor_upper:
            # log.info('Rdoors is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- Rdoors is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rdoors, Rdoor_lower, Rdoor_upper))

        airchange_per_hour_lower = 0.1
        airchange_per_hour_upper = 6.5
        if airchange_per_hour_lower <= self.airchange_per_hour < airchange_per_hour_upper:
            # log.info('airchange_per_hour is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- airchange_per_hour is {}, outside of nominal range of {} to {}.'
                    .format(self.name, 'init', self.airchange_per_hour, airchange_per_hour_lower, airchange_per_hour_upper))

        glazing_layers_lower = 1
        glazing_layers_upper = 3
        if glazing_layers_lower <= self.glazing_layers <= glazing_layers_upper:
            # log.info('glazing_layers is (are) within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- glazing_layers is (are) {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.glazing_layers, glazing_layers_lower, glazing_layers_upper))

        cooling_COP_lower = 1
        cooling_COP_upper = 10
        if cooling_COP_lower <= self.cooling_COP <= cooling_COP_upper:
            # log.info('cooling_COP is within the bounds.')
            pass
        else:
            log.log(model_diag_level, '{} {} -- cooling_COP is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.cooling_COP, cooling_COP_lower, cooling_COP_upper))

    def calc_thermostat_settings(self, model_diag_level, sim_time):
        """ Sets the ETP parameters from configuration data

        Args:
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human readable

        References:
            `Table 3 -  Easy to use slider settings <http://gridlab-d.shoutwiki.com/wiki/Transactive_controls>`_
        """

        self.range_high_cool = self.range_high_limit*self.slider # - self.ramp_high_limit * (1 - self.slider)
        self.range_low_cool = self.range_low_limit*self.slider # - self.ramp_low_limit * (1 - self.slider)
        self.range_high_heat = self.range_high_limit * self.slider  # - self.ramp_high_limit * (1 - self.slider)
        self.range_low_heat = self.range_low_limit * self.slider  # - self.ramp_low_limit * (1 - self.slider)

        if self.slider != 0:
            # cooling
            self.ramp_high_cool = self.ramp_high_limit *(1 - self.slider) #1+2*(1-self.slider) # TODO: /slider
            self.ramp_low_cool = self.ramp_low_limit *(1 - self.slider) #1+2*(1-self.slider) #
            # heating
            self.ramp_high_heat = self.ramp_low_limit *(1 - self.slider) #1+2*(1-self.slider) #
            self.ramp_low_heat = self.ramp_high_limit *(1 - self.slider) #1+2*(1-self.slider) #
        else:
            # cooling
            self.ramp_high_cool = 0.0
            self.ramp_low_cool = 0.0
            # heating
            self.ramp_high_heat = 0.0
            self.ramp_low_heat = 0.0

        # we need to check if heating and cooling bid curves overlap
        # print("self.basepoint_cooling before " + str(self.basepoint_cooling))
        # print("self.basepoint_heating before" + str(self.basepoint_heating))
        if self.basepoint_cooling - self.deadband / 2.0 - 0.5 < self.basepoint_heating + self.deadband / 2.0 + 0.5:
            # log.warning("Bid curves overlap, adjusting")
            # update minimum cooling and maximum heating temperatures
            mid_point = (self.basepoint_cooling + self.basepoint_heating) / 2.0
            self.basepoint_cooling = mid_point + self.deadband / 2.0 + 0.5
            basepoint_cooling_lower = 65
            basepoint_cooling_upper = 85
            if basepoint_cooling_lower < self.basepoint_cooling < basepoint_cooling_upper:
                # log.info('basepoint_cooling is within the bounds.')
                pass
            else:
                log.log(model_diag_level,
                        '{} {} -- basepoint_cooling is {}, outside of nominal range of {} to {}'
                        .format(self.name, sim_time, self.basepoint_cooling, basepoint_cooling_lower, basepoint_cooling_upper))

            self.basepoint_heating = mid_point - self.deadband / 2.0 - 0.5
            basepoint_heating_lower = 60
            basepoint_heating_upper = 85
            if basepoint_heating_lower < self.basepoint_heating < basepoint_heating_upper:
                # log.info('basepoint_heating is within the bounds.')
                pass
            else:
                log.log(model_diag_level,
                        '{} {} -- basepoint_heating is {}, outside of nominal range of {} to {}'
                        .format(self.name, sim_time, self.basepoint_heating, basepoint_heating_lower, basepoint_heating_upper))
        # print("self.basepoint_cooling "+str(self.basepoint_cooling))
        # print("self.basepoint_heating "+str(self.basepoint_heating))

        # forming two PT curves # T - this should be after adjusting basepoints for overlap
        # self.update_temp_limits(self.basepoint_cooling, self.basepoint_heating)

        # print("house "+str(self.name))
        # print("min and max for cooling/heating")
        # print("max heating " + str(self.temp_max_heat))
        # print("min cooling "+str(self.temp_min_cool))
        # self.temp_desired_48hour_cool = (self.temp_max_cool + self.temp_min_cool) / 2.0
        # self.temp_desired_48hour_heat = (self.temp_max_heat + self.temp_min_heat) / 2.0

        cooling_setpt = self.basepoint_cooling
        heating_setpt = self.basepoint_heating
        #def update_temp_limits(self, cooling_setpt, heating_setpt):
        self.temp_max_cool = cooling_setpt + self.range_high_cool #- self.ramp_high_limit * (1 - self.slider)
        self.temp_min_cool = cooling_setpt - self.range_low_cool #+ self.ramp_low_limit * (1 - self.slider)
        self.temp_max_heat = heating_setpt + self.range_high_heat #- self.ramp_high_limit * (1 - self.slider)
        self.temp_min_heat = heating_setpt - self.range_low_heat #+ self.ramp_low_limit * (1 - self.slider)
        if self.temp_max_heat + self.deadband / 2.0 + 0.5 > self.temp_min_cool - self.deadband / 2.0 - 0.5:
            mid_point = (self.temp_min_cool + self.temp_max_heat) / 2.0
            self.temp_min_cool = mid_point + self.deadband / 2.0 + 0.5
            self.temp_max_heat = mid_point - self.deadband / 2.0 - 0.5
            if self.temp_min_cool > cooling_setpt:
                self.temp_min_cool = cooling_setpt
            if self.temp_max_heat < heating_setpt:
                self.temp_max_heat = heating_setpt

    def update_temp_limits_da(self, cooling_setpt, heating_setpt):
        self.temp_max_cool_da = cooling_setpt + self.range_high_cool #- self.ramp_high_limit * (1 - self.slider)
        self.temp_min_cool_da = cooling_setpt - self.range_low_cool #+ self.ramp_low_limit * (1 - self.slider)
        self.temp_max_heat_da = heating_setpt + self.range_high_heat #- self.ramp_high_limit * (1 - self.slider)
        self.temp_min_heat_da = heating_setpt - self.range_low_heat #+ self.ramp_low_limit * (1 - self.slider)
        if self.temp_max_heat_da + self.deadband / 2.0 + 0.5 > self.temp_min_cool_da - self.deadband / 2.0 - 0.5:
            mid_point = (self.temp_min_cool_da + self.temp_max_heat_da) / 2.0
            self.temp_min_cool_da = mid_point + self.deadband / 2.0 + 0.5
            self.temp_max_heat_da = mid_point - self.deadband / 2.0 - 0.5
            if self.temp_min_cool_da > cooling_setpt:
                self.temp_min_cool_da = cooling_setpt
            if self.temp_max_heat_da < heating_setpt:
                self.temp_max_heat_da = heating_setpt

    def calc_etp_model(self):
        """ Sets the ETP parameters from configuration data

        References:
            `Thermal Integrity Table Inputs and Defaults <http://gridlab-d.shoutwiki.com/wiki/Residential_module_user%27s_guide#Thermal_Integrity_Table_Inputs_and_Defaults>`_
        """
        Rc = self.Rroof
        Rw = self.Rwall
        Rf = self.Rfloor

        # self.Rwindows  # g for glazing
        if self.glass_type == 2:
            if self.glazing_layers == 1:
                print("error: no value for one pane of low-e glass")
            elif self.glazing_layers == 2:
                if self.window_frame == 0:
                    Rg = 1.0/0.30
                elif self.window_frame == 1:
                    Rg = 1.0/0.67
                elif self.window_frame == 2:
                    Rg = 1.0/0.47
                elif self.window_frame == 3:
                    Rg = 1.0/0.41
                elif self.window_frame == 4:
                    Rg = 1.0/0.33
            elif self.glazing_layers == 3:
                if self.window_frame == 0:
                    Rg = 1.0/0.27
                elif self.window_frame == 1:
                    Rg = 1.0/0.64
                elif self.window_frame == 2:
                    Rg = 1.0/0.43
                elif self.window_frame == 3:
                    Rg = 1.0/0.37
                elif self.window_frame == 4:
                    Rg = 1.0/0.31
        elif self.glass_type == 1:
            if self.glazing_layers == 1:
                if self.window_frame == 0:
                    Rg = 1.0/1.04
                elif self.window_frame == 1:
                    Rg = 1.0/1.27
                elif self.window_frame == 2:
                    Rg = 1.0/1.08
                elif self.window_frame == 3:
                    Rg = 1.0/0.90
                elif self.window_frame == 4:
                    Rg = 1.0/0.81
            elif self.glazing_layers == 2:
                if self.window_frame == 0:
                    Rg = 1.0/0.48
                elif self.window_frame == 1:
                    Rg = 1.0/0.81
                elif self.window_frame == 2:
                    Rg = 1.0/0.60
                elif self.window_frame == 3:
                    Rg = 1.0/0.53
                elif self.window_frame == 4:
                    Rg = 1.0/0.44
            elif self.glazing_layers == 3:
                if self.window_frame == 0:
                    Rg = 1.0 / 0.31
                elif self.window_frame == 1:
                    Rg = 1.0 / 0.67
                elif self.window_frame == 2:
                    Rg = 1.0 / 0.46
                elif self.window_frame == 3:
                    Rg = 1.0 / 0.40
                elif self.window_frame == 4:
                    Rg = 1.0 / 0.34
        elif self.glass_type == 0:
            Rg = 2.0

        # transmission coefficient through window due to glazing
        if self.glazing_layers == 1:
            if self.glazing_treatment == 1:
                if self.window_frame == 0:
                    Wg = 0.86
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.75
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.64
            elif self.glazing_treatment == 2:
                if self.window_frame == 0:
                    Wg = 0.73
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.64
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.54
            elif self.glazing_treatment == 3:
                if self.window_frame == 0:
                    Wg = 0.31
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.28
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.24
        elif self.glazing_layers == 2:
            if self.glazing_treatment == 1:
                if self.window_frame == 0:
                    Wg = 0.76
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.67
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.57
            elif self.glazing_treatment == 2:
                if self.window_frame == 0:
                    Wg = 0.62
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.55
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.46
            elif self.glazing_treatment == 3:
                if self.window_frame == 0:
                    Wg = 0.29
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.27
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.22
        elif self.glazing_layers == 3:
            if self.glazing_treatment == 1:
                if self.window_frame == 0:
                    Wg = 0.68
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.60
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.51
            elif self.glazing_treatment == 2:
                if self.window_frame == 0:
                    Wg = 0.34
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.31
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.26
            elif self.glazing_treatment == 3:
                if self.window_frame == 0:
                    Wg = 0.34
                elif self.window_frame == 1 or self.window_frame==2:
                    Wg = 0.31
                elif self.window_frame == 3 or self.window_frame==4:
                    Wg = 0.26

        Rd = self.Rdoors
        I = self.airchange_per_hour
        mf = self.thermal_mass_per_floor_area
        # some hard-coded GridLAB-D defaults
        aspect = self.aspect_ratio  # footprint x/y ratio
        if aspect == 0.0:
            aspect = 1.5
        A1d = 19.5  # area of one door
        h = self.ceiling_height  # ceiling height
        ECR = self.exterior_ceiling_fraction  # exterior ceiling fraction
        if ECR == 0.0:
            ECR = 1.0
        EFR = self.exterior_floor_fraction  # exterior floor fraction
        if EFR == 0.0:
            EFR = 1.0
        EWR = self.exterior_wall_fraction  # exterior wall fraction
        if EWR == 0.0:
            EWR = 1.0
        WWR = 0.15  # window to exterior wall ratio, 0.07 in the Wiki and 0.15 in GLD
        IWR = 1.5  # interior to exterior wall ratio
        hs = 1.46  # interior heat transfer coefficient
        MIGF = 0.5  # mass internal gain fraction
        MSGF = 0.5  # mass solar gain fraction
        VHa = 0.0735 * 0.2402  # air_density*air_heat_capacity
        WETC = self.WETC #0.6  # coefficient for the amount of energy that passes through window
        if WETC <= 0.0:
            WETC = 0.6

        Ac = (self.sqft / self.stories) * ECR  # ceiling area
        Af = (self.sqft / self.stories) * EFR  # floor area
        perimeter = 2 * (1 + aspect) * math.sqrt(Ac / aspect)  # exterior perimeter
        # perimeter = 2 * (1 + aspect) * math.sqrt(Af / aspect / self.stories)  # exterior perimeter
        Awt = self.stories * h * perimeter  # gross exterior wall area
        Ag = WWR * Awt * EWR  # gross window area
        Ad = self.doors * A1d  # total door area
        Aw = (Awt - Ag - Ad) * EWR  # net exterior wall area, taking EWR as 1s
        Vterm = self.sqft * h * VHa

        # airchange_per_hour = I
        # volume = ceiling_height*floor_area = 8.0*2500.0
        # air_density = 0.0735
        # air_heat_capacity = 0.2402
        # airchange_UA = airchange_per_hour * volume * air_density * air_heat_capacity = I*;

        # floor_area= 2500.0
        # exterior_ceiling_fraction = 1.0
        # number_of_stories = 1.0
        # exterior_ceiling_area = floor_area * exterior_ceiling_fraction / number_of_stories = Ac
        # Rroof = Rc
        # exterior_floor_area = floor_area * exterior_floor_fraction / number_of_stories = Af
        # Rfloor = Rf
        # exterior_wall_fraction = 1.0
        # gross_wall_area = 2.0 * number_of_stories * (aspect_ratio + 1.0) * ceiling_height * sqrt(floor_area/aspect_ratio/number_of_stories) = Awt
        # window_area = gross_wall_area * window_wall_ratio * exterior_wall_fraction = Ag =  Awt * WWR *EWR
        # door_area = number_of_doors * 3.0 * 78.0 / 12.0 = Ad = self.doors * A1d
        # net_exterior_wall_area = exterior_wall_fraction * gross_wall_area - window_area - door_area = Aw
        # window_area = Ag
        # envelope_UA = exterior_ceiling_area/Rroof + exterior_floor_area/Rfloor + net_exterior_wall_area/Rwall + window_area/Rwindows + door_area/Rdoors;
        # airchange_UA
        # UA = envelope_UA + airchange_UA

        # TODO: handle dividing by zero differently? Only adding this since Rc, Rf, Rw, Rg, or Rd turned out to be zero for a substation in dsot_v3
        def div(x, y, def_val_if_zero_denom=0):
            return x / y if y != 0 else def_val_if_zero_denom

        self.UA = div(Ac, Rc) + div(Af, Rf) + div(Aw, Rw) + div(Ag, Rg) + div(Ad, Rd) + Vterm * I
        self.CA = 3 * Vterm
        self.HM = hs * (Aw / EWR + Awt * IWR + Ac * self.stories / ECR)
        self.CM = self.sqft * mf - 2 * Vterm

        self.solar_heatgain_factor = Ag * Wg * WETC

        self.mass_internal_gain_fraction = MIGF
        self.mass_solar_gain_fraction = MSGF

        self.design_cooling_capacity = (1.0 + self.over_sizing_factor) * (1.0 + self.latent_load_fraction) * (
                self.UA * (
                    self.cooling_design_temperature - self.design_cooling_setpoint) + self.design_internal_gains + (
                        self.design_peak_solar * self.solar_heatgain_factor))
        round_value = self.design_cooling_capacity / 6000.0
        self.design_cooling_capacity = math.ceil(round_value) * 6000.0

        if self.heating_system_type == 'HEAT_PUMP':
            self.design_heating_capacity = self.design_cooling_capacity
        else:
            self.design_heating_capacity = (1.0 + self.over_sizing_factor) * (self.UA) * (
                    self.design_heating_setpoint - self.heating_design_temperature)
            round_value = self.design_heating_capacity / 10000.0
            self.design_heating_capacity = math.ceil(round_value) * 10000.0

        log.debug('ETP model ' + self.name)
        log.debug('  UA -> {:.2f}'.format(self.UA))
        # print('  UA -> {:.2f}'.format(self.UA))
        log.debug('  CA -> {:.2f}'.format(self.CA))
        # print('  CA -> {:.2f}'.format(self.CA))
        log.debug('  HM -> {:.2f}'.format(self.HM))
        log.debug('  CM -> {:.2f}'.format(self.CM))
        # print('  CM -> {:.2f}'.format(self.CM))

    def set_price_forecast(self, price_forecast):
        """ Set the 24 hour price forecast and calculate mean and std

        Args:
            price_forecast ([float x 24]): predicted price in $/kwh
        """
        self.price_forecast = price_forecast[:]
        #print("self.price_forecast")
        #print(self.price_forecast)
        self.price_mean = np.mean(self.price_forecast)
        self.price_std_dev = np.std(self.price_forecast)
        self.price_delta = np.max(self.price_forecast) - np.min(self.price_forecast)

    def set_temperature_forecast(self, fncs_str):
        """ Set the 48 hour price forecast and calculate min and max

        Args:
            temperature_forecast ([float x 48]): predicted temperature in F
        """

        temperature_forecast = eval(fncs_str)
        self.temperature_forecast = [float(temperature_forecast[key]) for key in temperature_forecast.keys()]
        # print ("temperature forecast inside function")
        # print(self)
        # print (self.temperature_forecast)
        self.temp_min_48hour = min(self.temperature_forecast)
        self.temp_max_48hour = max(self.temperature_forecast)

    def set_humidity_forecast(self, fncs_str):
        """ Set the 48 hour price forecast and calculate min and max

        Args:
            temperature_forecast ([float x 48]): predicted temperature in F
        """

        humidity_forecast = eval(fncs_str)
        self.humidity_forecast = [float(humidity_forecast[key]) for key in humidity_forecast.keys()]

    def set_solargain_forecast(self, solargain_array):
        """ Set the 48 hour solargain forecast

        Args:
            solargain_forecast ([float x 48]): forecasted solargain in BTu/(h*sf)
        """
        # bringing solar gain to nominal for the use in different homes
        # home A3 has solargain_factor of 40.548
        self.solargain_forecast = solargain_array

    def set_internalgain_forecast(self, internalgain_array):
        """ Set the 48 hour internalgain forecast
        Args:
            internalgain_forecast ([float x 48]): forecasted internalgain in BTu/h
        """
        # if self.name == 'Houses_A_hse_13':
        #     self.internalgain_forecast = internalgain_array[1]
        # elif self.name == 'Houses_A_hse_15':
        #     self.internalgain_forecast = internalgain_array[2]
        # elif self.name == 'Houses_A_hse_49':
        #     self.internalgain_forecast = internalgain_array[3]
        # else:
        #     self.internalgain_forecast = internalgain_array[0]
        self.internalgain_forecast = internalgain_array

    def set_temperature(self, fncs_str):
        """ Sets the outside temperature attribute

        Args:
            fncs_str (str): FNCS message with outdoor temperature in F
        """
        val = helpers.parse_fncs_number(fncs_str)
        self.outside_air_temperature = val

    def set_humidity(self, fncs_str):
        """ Sets the humidity attribute

        Args:
            fncs_str (str): FNCS message with humidity
        """
        val = helpers.parse_fncs_number(fncs_str)
        if val > 0.0:
            self.humidity = val

    def set_solar_direct(self, fncs_str):
        """ Sets the solar irradiance attribute, if greater than zero

        Args:
            fncs_str (str): FNCS message with solar irradiance
        """
        val = helpers.parse_fncs_number(fncs_str)
        if val >= 0.0:
            self.solar_direct = val

    def set_solar_diffuse(self, fncs_str):
        """ Sets the solar diffuse attribute, if greater than zero

        Args:
            fncs_str (str): FNCS message with solar irradiance
        """
        val = helpers.parse_fncs_number(fncs_str)
        if val >= 0.0:
            self.solar_diffuse = val

    def get_solargain(self, climate_conf, current_time):
        """ estimates the nominal solargain without solargain_factor

        Args:
            climate_conf: latitude and longitude info in a dict
            current_time: the time for which solargain needs to be estiamted
        """
        lat = math.radians(float(climate_conf['latitude']))  # converting to radians
        lon = math.radians(float(climate_conf['longitude']))
        tz = pytz.timezone("US/Central")  # TODO: should pull from somewhere rather than hardcoding
        dst = tz.localize(current_time).dst()  # to get if daylight saving is On or not
        if dst:
            tz_offset = -5  # when daylight saving is on, offset for central time zone is UTC-5
        else:
            tz_offset = -6  # other wise UTC-6
        day_of_yr = current_time.timetuple().tm_yday  # get day of year from datetime
        dnr = self.solar_direct
        dhr = self.solar_diffuse
        # start_hour = math.ceil(current_time.hour + current_time.minute/60)
        start_hour = current_time.hour
        # time = (np.array(range(start_hour, start_hour + 48)) % 24).tolist()

        self.solar_gain = self.calc_solargain(day_of_yr, start_hour, dnr, dhr, lat, lon, tz_offset)
        return self.solar_gain

    def calc_solargain(self, day_of_yr, start_hour, dnr, dhr, lat, lon, tz_offset):
        # implementing gridlabd solargain calculation from climate.cpp and house_e.cpp
        rad = (2.0 * math.pi * day_of_yr) / 365.0
        eq_time = (0.5501 * cos(rad) - 3.0195 * cos(2 * rad) - 0.0771 * cos(3 * rad)
                   - 7.3403 * sin(rad) - 9.4583 * sin(2 * rad) - 0.3284 * sin(3 * rad)) / 60.0
        tz_meridian = 15 * tz_offset
        std_meridian = tz_meridian * math.pi / 180
        solar_gain = []
        std_time = start_hour
        sol_time = std_time + eq_time + 12.0 / math.pi * (lon - std_meridian)
        solar_flux = []
        for cpt in self.surface_angles.keys():
            vertical_angle = math.radians(90)
            if cpt == 'H':
                vertical_angle = math.radians(0)
            solar_flux.append(self.calc_solar_flux(cpt, day_of_yr, lat, sol_time, dnr, dhr, vertical_angle))
        avg_solar_flux = sum(solar_flux[1:9]) / 8
        solar_gain = avg_solar_flux * 3.412  # incident_solar_radiation is now in Btu/(h*sf)
        return solar_gain

    def calc_solar_flux(self, cpt, day_of_yr, lat, sol_time, dnr_i, dhr_i, vertical_angle):
        az = math.radians(self.surface_angles[cpt])
        if cpt == 'H':
            az = math.radians(self.surface_angles['E'])
        # based on GLD calculations
        # cos_incident(lat,RAD(vert_angle),RAD(surface_angle),sol_time,doy)
        hr_ang = -(15.0 * math.pi / 180) * (sol_time - 12.0)
        decl = 0.409280 * sin(2.0 * math.pi * (284 + day_of_yr) / 365)
        slope = vertical_angle
        sindecl = sin(decl)
        cosdecl = cos(decl)
        sinlat = sin(lat)
        coslat = cos(lat)
        sinslope = sin(slope)
        cosslope = cos(slope)
        sinaz = sin(az)
        cosaz = cos(az)
        sinhr = sin(hr_ang)
        coshr = cos(hr_ang)
        cos_incident = sindecl * sinlat * cosslope \
                       - sindecl * coslat * sinslope * cosaz \
                       + cosdecl * coslat * cosslope * coshr \
                       + cosdecl * sinlat * sinslope * cosaz * coshr \
                       + cosdecl * sinslope * sinaz * sinhr
        if cos_incident < 0:
            cos_incident = 0
        return dnr_i * cos_incident + dhr_i

    def inform_bid(self, price):
        """ Set the cleared_price attribute

        Args:
            price (float): cleared price in $/kwh
        """
        self.cleared_price = price

    def bid_accepted(self, model_diag_level, sim_time):
        """ Update the thermostat setting if the last bid was accepted

        The last bid is always "accepted". If it wasn't high enough,
        then the thermostat could be turned up.

        Args:
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human readable

        Returns:
            Boolean: True if the thermostat setting changes, False if not.
        """
        cooling_setpoint_lower = 65
        cooling_setpoint_upper = 85
        heating_setpoint_lower = 60
        heating_setpoint_upper = 85
        if self.thermostat_mode == 'Cooling':
            basepoint_tmp = self.basepoint_cooling
        elif self.thermostat_mode == 'Heating':
            basepoint_tmp = self.basepoint_heating
        else:
            basepoint_tmp = 70.0  # default value that is ok for both operating points
        # using price forecast [0] instead of mean
        if self.price_std_dev > 0.0:
            if self.thermostat_mode == 'Cooling':
                ramp_high_tmp = self.ramp_high_cool
                ramp_low_tmp = self.ramp_low_cool
            elif self.thermostat_mode == 'Heating':
                ramp_high_tmp = self.ramp_high_heat
                ramp_low_tmp = self.ramp_low_heat
            else:
                ramp_high_tmp = 10000000000000.0
                ramp_low_tmp = 10000000000000.0
                log.log(model_diag_level, '{} {} -- thermostat mode not defined.'.format(self.name, sim_time))
            # TODO: this is the debate whether to use priceforecast (self.price_forecast[0]) of price mean (self.price_mean)
            use_DA_curve = True
            if use_DA_curve:
                if self.thermostat_mode == "Cooling":
                    if self.cleared_price > self.price_forecast_0:
                        # setpoint_tmp = self.temp_room[0] + (self.cleared_price - self.price_forecast_0) * self.range_high_cool / \
                        #               (ramp_high_tmp * self.price_std_dev)
                        setpoint_tmp = self.temp_room[0] + (self.cleared_price - self.price_forecast_0) * (self.range_high_cool) / \
                                       (self.price_delta)
                    elif self.cleared_price < self.price_forecast_0:
                        setpoint_tmp = self.temp_room[0] + (self.cleared_price - self.price_forecast_0) * self.range_low_cool / \
                                      (ramp_low_tmp * self.price_std_dev)
                        # setpoint_tmp = self.temp_room[0] + (self.cleared_price - self.price_forecast_0) * (self.range_low_cool) / \
                        #                (self.price_delta)
                    else:
                        # self.setpoint = self.basepoint_cooling
                        setpoint_tmp = self.temp_room[0]
                else:
                    if self.cleared_price > self.price_forecast_0:
                        setpoint_tmp = self.temp_room[0] + (self.cleared_price - self.price_forecast_0) \
                                       * self.range_high_heat / self.price_delta
                    elif self.cleared_price < self.price_forecast_0:
                        setpoint_tmp = self.temp_room[0] + (self.cleared_price - self.price_forecast_0) \
                                       * self.range_low_heat / self.price_delta
                    else:
                        # self.setpoint = self.basepoint_cooling
                        setpoint_tmp = self.temp_room[0]
            else:
                if self.cleared_price > self.price_mean:
                    setpoint_tmp = basepoint_tmp + (self.cleared_price - self.price_mean) * self.range_high_cool / \
                                   (ramp_high_tmp * self.price_std_dev)
                elif self.cleared_price < self.price_mean:
                    setpoint_tmp = basepoint_tmp + (self.cleared_price - self.price_mean) * self.range_low_cool / \
                                   (ramp_low_tmp * self.price_std_dev)
                else:
                    # self.setpoint = self.basepoint_cooling
                    setpoint_tmp = basepoint_tmp
                #log.log(model_diag_level, '{} {} -- thermostat mode not defined.'.format(self.name, sim_time))
            # if self.cleared_price > self.price_forecast[0]:
            #     setpoint_tmp = basepoint_tmp + (self.cleared_price - self.price_forecast[0]) * self.range_high / \
            #                    (ramp_high_tmp * self.price_std_dev)
            # elif self.cleared_price < self.price_forecast[0]:
            #     setpoint_tmp = basepoint_tmp + (self.cleared_price - self.price_forecast[0]) * self.range_low / \
            #                    (ramp_low_tmp * self.price_std_dev)
            # else:
            #     # self.setpoint = self.basepoint_cooling
            #     setpoint_tmp = basepoint_tmp

            setpoint_rt = setpoint_tmp
            use_DA_temp = False
            if use_DA_temp:
                setpoint_tmp = self.temp_room[0]  # self.temp_room_previous#
                if self.thermostat_mode == 'Cooling':
                    self.cooling_setpoint = setpoint_tmp
                else:
                    self.heating_setpoint = setpoint_tmp
                if 65 < self.cooling_setpoint < 85:
                    # log.info('cooling_setpoint is within the bounds.')
                    pass
                else:
                    log.log(model_diag_level, '{} {} -- cooling_setpoint ({}) is out of bounds.'
                            .format(self.name, sim_time, self.cooling_setpoint ))
                if self.heating_setpoint + self.deadband / 2.0 >= self.cooling_setpoint - self.deadband / 2.0:
                    # push heating_setpoint down
                    self.heating_setpoint = self.cooling_setpoint - self.deadband - 0.5  # for safety
                    if 60 < self.heating_setpoint < 85:
                        # log.info('heating_setpoint is within the bounds.')
                        pass
                    else:
                        log.log(model_diag_level, '{} {} -- heating_setpoint ({}) is out of bounds.'
                                .format(self.name, sim_time, self.heating_setpoint))

            # ensure that setpoint is within user comfort band
            # if self.setpoint > self.basepoint_cooling + abs(self.range_high):
            #    self.setpoint = self.basepoint_cooling + abs(self.range_high)
            # elif self.setpoint < self.basepoint_cooling - abs(self.range_low):
            #    self.setpoint = self.basepoint_cooling - abs(self.range_low)
            if self.thermostat_mode == "Cooling":
                if setpoint_tmp > basepoint_tmp + abs(self.range_high_cool):
                    setpoint_tmp = basepoint_tmp + abs(self.range_high_cool)
                elif setpoint_tmp < basepoint_tmp - abs(self.range_low_cool):
                    setpoint_tmp = basepoint_tmp - abs(self.range_low_cool)
            else:
                if setpoint_tmp > basepoint_tmp + abs(self.range_high_heat):
                    setpoint_tmp = basepoint_tmp + abs(self.range_high_heat)
                elif setpoint_tmp < basepoint_tmp - abs(self.range_low_heat):
                    setpoint_tmp = basepoint_tmp - abs(self.range_low_heat)

            # else:
            #    "Do nothing"
            # return True
            returnflag = True
        else:
            # self.setpoint = self.basepoint_cooling
            setpoint_tmp = basepoint_tmp
            setpoint_rt = setpoint_tmp
            ramp_high_tmp = 0.0
            ramp_low_tmp = 0.0
            # return False
            returnflag = False

        if self.thermostat_mode == 'Cooling':
            # print("temp mod: " + str(self.basepoint_cooling) + " -> " + str(self.cooling_setpoint))
            self.cooling_setpoint = setpoint_tmp
            if cooling_setpoint_lower < self.cooling_setpoint < cooling_setpoint_upper:
                # log.info('cooling_setpoint is within the bounds.')
                pass
            else:
                log.log(model_diag_level,
                        '{} {} -- cooling_setpoint ({}), outside of nominal range {} to {}'
                        .format(self.name, sim_time, self.cooling_setpoint, cooling_setpoint_lower, cooling_setpoint_upper))
        elif self.thermostat_mode == 'Heating':
            # print("temp mod: " + str(self.basepoint_heating) + " -> " + str(self.heating_setpoint))
            self.heating_setpoint = setpoint_tmp
            if heating_setpoint_lower < self.heating_setpoint < heating_setpoint_upper:
                # log.info('heating_setpoint is within the bounds.')
                pass
            else:
                log.log(model_diag_level,
                        '{} {} -- heating_setpoint ({}), outside of nominal range of {} to {}'
                        .format(self.name, sim_time, self.heating_setpoint, heating_setpoint_lower, heating_setpoint_upper))

        price_curve = [self.bid_rt[0][1], self.bid_rt[1][1], self.bid_rt[2][1], self.bid_rt[3][1]]
        quantity_curve = [self.bid_rt[0][0], self.bid_rt[1][0], self.bid_rt[2][0], self.bid_rt[3][0]]
        if price_curve[1] <= self.cleared_price <= price_curve[0]:
            a = (quantity_curve[1] - quantity_curve[0])/(price_curve[1] - price_curve[0])
            b = quantity_curve[1] - a * price_curve[1]
            self.bid_quantity = a * self.cleared_price + b
        elif price_curve[1] >= self.cleared_price >= price_curve[2]:
            #a = (quantity_curve[2] - quantity_curve[1]) / (price_curve[2] - price_curve[1])
            #b = quantity_curve[1] - a * price_curve[1]
            #self.bid_quantity = a * self.cleared_price + b
            self.bid_quantity = quantity_curve[1]
        elif price_curve[2] >= self.cleared_price >= price_curve[3]:
            a = (quantity_curve[3] - quantity_curve[2]) /(price_curve[3] - price_curve[2])
            b = quantity_curve[2] - a * price_curve[2]
            self.bid_quantity = a * self.cleared_price + b
        elif self.cleared_price > price_curve[0]:
            self.bid_quantity = 0  # assuming this is minimum
        elif self.cleared_price < price_curve[3]:
            self.bid_quantity = self.hvac_kw  # assuming this is maximum
        else:
            self.bid_quantity = 0
            print("something went wrong with clear price")

        if self.heating_setpoint + self.deadband / 2.0 >= self.cooling_setpoint - self.deadband / 2.0:
            if self.thermostat_mode == 'Heating':
                # push cooling_setpoint up
                self.cooling_setpoint = self.heating_setpoint + self.deadband
            else:  # self.thermostat_mode == 'Cooling' or 'OFF':
                # push heating_setpoint down
                self.heating_setpoint = self.cooling_setpoint - self.deadband

        # print("RT quantities",self.name,sim_time)
        # print("setpoint_rt,self.temp_room[0],self.cleared_price,self.price_forecast[0],self.price_forecast_0,self.price_std_dev")
        # print(setpoint_rt,self.temp_room[0],self.cleared_price,self.price_forecast[0],self.price_forecast_0,self.price_std_dev,self.price_delta)
        # print("self.ramp_high_cool,self.ramp_low_cool,self.range_high_cool,self.range_low_cool")
        # print(ramp_high_tmp,ramp_low_tmp,self.range_high_cool,self.range_low_cool)
        # print("Thermostat mode ", "cooling_setpoint","heating_setpoint")
        # print(self.thermostat_mode,self.cooling_setpoint,self.heating_setpoint)


        return returnflag

    def change_solargain(self, moh, hod, dow):
        """ Updates the pre-recorder solar gain

        Args:
            moh (int): the minute of the hour from 0 to 59
            hod (int): the hour of the day, from 0 to 23
            dow (int): the day of the week, zero being Monday

        Updates:
            solar_gain
        """
        # we will use this function to update time
        # will be removed later
        self.minute = moh
        self.hour = hod
        self.day = dow

        self.solar_heatgain = 0.0  # we need to record the value first without error here
        # self.solar_heatgain = solar_gain[int(hod)*60+int(moh)] / 40.548 # bringing solar gain to nominal for the use in different homes

    def change_basepoint(self, moh, hod, dow, model_diag_level, sim_time):
        """ Updates the time-scheduled thermostat setting

        Args:
            moh (int): the minute of the hour from 0 to 59
            hod (int): the hour of the day, from 0 to 23
            dow (int): the day of the week, zero being Monday
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human readable

        Returns:
            Boolean: True if the setting changed, False if not
        """
        hod = hod + moh / 60

        if dow > 4:  # a weekend
            val_cool = self.weekend_night_set_cool
            val_heat = self.weekend_night_set_heat
            if self.weekend_day_start <= hod < self.weekend_night_start:
                val_cool = self.weekend_day_set_cool
                val_heat = self.weekend_day_set_heat
        else:  # a weekday
            val_cool = self.night_set_cool
            val_heat = self.night_set_heat
            if self.wakeup_start <= hod < self.daylight_start:
                val_cool = self.wakeup_set_cool
                val_heat = self.wakeup_set_heat
            elif self.daylight_start <= hod < self.evening_start:
                val_cool = self.daylight_set_cool
                val_heat = self.daylight_set_heat
            elif self.evening_start <= hod < self.night_start:
                val_cool = self.evening_set_cool
                val_heat = self.evening_set_heat
        if abs(self.basepoint_cooling - val_cool) > 0.1 or abs(self.basepoint_heating - val_heat) > 0.1:
            self.basepoint_cooling = val_cool
            if 65 < self.basepoint_cooling < 85:
                # log.info('basepoint_cooling is within the bounds.')
                pass
            else:
                log.log(model_diag_level, '{} {} -- basepoint_cooling ({}) is out of bounds.'
                        .format(self.name, sim_time, self.basepoint_cooling))
            self.basepoint_heating = val_heat
            if 60 < self.basepoint_heating < 85:
                # log.info('basepoint_heating is within the bounds.')
                pass
            else:
                log.log(model_diag_level, '{} {} -- basepoint_heating ({}) is out of bounds.'
                        .format(self.name, sim_time, self.basepoint_heating))
            self.calc_thermostat_settings(model_diag_level, sim_time)  # update thermostat settings
            return True
        return False

    def set_house_load(self, fncs_str):
        """ Sets the hvac_load attribute, if greater than zero

        Args:
            fncs_str (str): FNCS message with load in kW
        """
        val = helpers.parse_fncs_number(fncs_str)
        if val > 0.0:
            self.house_kw = val

    def set_hvac_load(self, fncs_str):
        """ Sets the hvac_load attribute, if greater than zero

        Args:
            fncs_str (str): FNCS message with load in kW
        """
        val = helpers.parse_fncs_number(fncs_str)
        if val > 0.0:
            self.hvac_kw = val

    def set_wh_load(self, fncs_str):
        """ Sets the wh_load attribute, if greater than zero

        Args:
            fncs_str (str): FNCS message with load in kW
        """
        val = helpers.parse_fncs_number(fncs_str)
        if val >= 0.0:
            self.wh_kw = val

    def set_hvac_state(self, fncs_str):
        """ Sets the hvac_on attribute

        Args:
            fncs_str (str): FNCS message with state, ON or OFF
        """
        if fncs_str == 'OFF':
            self.hvac_on = False
        else:
            self.hvac_on = True

    def set_air_temp(self, fncs_str, model_diag_level, sim_time):
        """ Sets the air_temp attribute

        Args:
            fncs_str (str): FNCS message with temperature in degrees Fahrenheit
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human readable
        """
        self.air_temp = helpers.parse_fncs_number(fncs_str)
        if 60 < self.air_temp < 90:
            # log.info('air_temp is within the bounds.')
            pass
        else:
            log.log(model_diag_level,
                    '{} {} -- air_temp ({}) is out of bounds.'
                    .format(self.name, sim_time, self.air_temp))
        # TODO: This is a correction within the hour for the DA prediction of thermostat mode - hard-coded for testing
        # using heating as default
        if self.air_temp >= (self.temp_min_cool + self.temp_max_heat)/2.0:  # self.deadband / 2.0:
            self.thermostat_mode = 'Cooling'
        else:  # self.air_temp <= self.temp_max_heat + self.deadband / 2.0:
            self.thermostat_mode = 'Heating'
        #else:
        #    self.thermostat_mode = 'OFF'

    def set_voltage(self, fncs_str):
        """ Sets the mtr_v attribute

        Args:
            fncs_str (str): FNCS message with meter line-neutral voltage
        """
        self.mtr_v = helpers.parse_fncs_magnitude(fncs_str)

    def formulate_bid_rt(self, model_diag_level, sim_time):
        """ Bid to run the air conditioner through the next period for real-time

        Args:
            model_diag_level (int): Specific level for logging errors; set to 11
            sim_time (str): Current time in the simulation; should be human readable

        Returns:
            [[float, float], [float, float], [float, float], [float, float]]: [bid price $/kwh, bid quantity kW] x 4
        """
        # print("heat_type " + str(self.heating_system_type))
        # print("Heating " + str(self.thermostat_mode))
        if self.heating_system_type != 'HEAT_PUMP' and self.thermostat_mode == 'Heating':
            self.bid_rt = [[0, 0], [0, 0], [0, 0], [0, 0]]
            return self.bid_rt

        # adjust capacity and COP based on outdoor temperature
        cooling_capacity_adj = self.design_cooling_capacity * (
                    self.cooling_capacity_K0 + self.cooling_capacity_K1 * self.outside_air_temperature)

        heating_capacity_adj = self.design_heating_capacity * (
                    self.heating_capacity_K0 + self.heating_capacity_K1 * self.outside_air_temperature
                    + self.heating_capacity_K2 * self.outside_air_temperature * self.outside_air_temperature)

        # TODO: I don't think this is needed
        if self.outside_air_temperature < self.cooling_COP_limit:
            self.cooling_cop_adj_rt = self.cooling_COP / (
                        self.cooling_COP_K0 + self.cooling_COP_K1 * self.cooling_COP_limit)
        else:
            self.cooling_cop_adj_rt = self.cooling_COP / (
                        self.cooling_COP_K0 + self.cooling_COP_K1 * self.outside_air_temperature)

        if self.outside_air_temperature > self.heating_COP_limit:
            self.heating_cop_adj_rt = self.heating_COP / (
                        self.heating_COP_K0 + self.heating_COP_K1 * self.heating_COP_limit)
        else:
            self.heating_cop_adj_rt = self.heating_COP / (self.heating_COP_K0
                                                       + self.heating_COP_K1 * self.outside_air_temperature
                                                       + self.heating_COP_K2 * self.outside_air_temperature * self.outside_air_temperature
                                                       + self.heating_COP_K3 * self.outside_air_temperature * self.outside_air_temperature * self.outside_air_temperature)

        # TODO: need to check if this is needed anymore
        if self.thermostat_mode == 'Heating':
            Qh = heating_capacity_adj + 0.02 * heating_capacity_adj
            Qh_org = self.hvac_kw
        elif self.thermostat_mode == 'Cooling':
            Qh = -cooling_capacity_adj / (1 + 0.1 + self.latent_load_fraction / (1 + math.exp(4 - 10 * self.humidity))) \
                 + cooling_capacity_adj * 0.02
            Qh_org = -self.hvac_kw
        else:
            Qh = 0.0
            Qh_org = 0.0

        if not self.hvac_on:
            Qh_org = 0.0

        # estimating the HVAC consumption based on the last reported from GLD
        Qi = (self.house_kw - abs(Qh_org) - self.wh_kw) * 3412.1416331279

        # Qi = kW_meter_GLD - Qh - Qwh
        # Qi = Qi(t-1) + (Qi(t-1)-Qi(t-2))*dt

        # Qs = self.solar_heatgain_factor * (self.solar_direct + self.solar_diffuse)
        # Qs = sum( (Aw_o*SHGF_o) * Solar_Irradiance_o)

        #Qs = self.solar_heatgain * self.solar_heatgain_factor
        Qs = self.solar_gain * self.solar_heatgain_factor

        T = (self.bid_delay + self.period) / 3600.0  # 300
        Qa_OFF = ((1 - self.mass_internal_gain_fraction) * Qi) + ((1 - self.mass_solar_gain_fraction) * Qs)
        Qa_ON = Qh + ((1 - self.mass_internal_gain_fraction) * Qi) + (
                (1 - self.mass_solar_gain_fraction) * Qs)

        QM = (self.mass_internal_gain_fraction * Qi) + (self.mass_solar_gain_fraction * Qs)
        self.Qh = Qh
        self.Qi = Qi
        self.Qa_ON = Qa_ON
        self.Qa_OFF = Qa_OFF
        self.Qm = QM
        self.Qs = Qs
        x = np.zeros([2, 1])
        x[0] = self.air_temp
        x[1] = self.mass_temp
        A_ETP = np.zeros([2, 2])
        B_ETP_ON = np.zeros([2, 1])
        B_ETP_OFF = np.zeros([2, 1])

        if self.CA != 0.0:
            A_ETP[0][0] = -1.0 * (self.UA + self.HM) / self.CA
            A_ETP[0][1] = self.HM / self.CA
            B_ETP_ON[0] = (self.UA * self.outside_air_temperature / self.CA) + (Qa_ON / self.CA)
            B_ETP_OFF[0] = (self.UA * self.outside_air_temperature / self.CA) + (Qa_OFF / self.CA)

        if self.CM != 0.0:
            A_ETP[1][0] = self.HM / self.CM
            A_ETP[1][1] = -1.0 * self.HM / self.CM
            B_ETP_ON[1] = QM / self.CM
            B_ETP_OFF[1] = QM / self.CM


        AEI = np.linalg.inv(A_ETP)
        # if self.name == "R5_12_47_2_tn_2_hse_1":
        #     print(self.name)
        #     print("HVAC STAT " + str(self.hvac_on))
        #     print("Ther mode ",self.thermostat_mode)
        # log.debug("outdoor temp " + str(self.outside_air_temperature))

        # if we are enforcing DA bid, use DA bid quantity and temperature (in price clear)
        Qopt_DA = self.bid_da[0][1][0]
        topt = self.temp_room[0]
        #Q1 = Qopt_DA - 0.2/2.0 * Qopt_DA#self.hvac_kw
        #Q2 = Qopt_DA + 0.2/2.0 * Qopt_DA#self.hvac_kw
        #topt = Qopt_DA / self.hvac_kw * T
        #t1 = Q1 / self.hvac_kw * T
        #t2 = Q2 / self.hvac_kw * T
        #dt = (t2-t1)/2.0

        time = np.linspace(0,T,num=10) #[0,topt-dt, topt, topt+dt]
        # temp_curve_tmp = [0 for i in range(len(time))]
        # quan_curve_tmp = [0 for i in range(len(time))]
        # temp = [0 for i in range(len(time))]
        # temp_mass = [0 for i in range(len(time))]

        x = np.zeros([2, 1])
        x[0] = self.air_temp
        x[1] = self.mass_temp
        Q_max = self.hvac_kw
        Q_min = 0.0
        # TODO: I need to have 3 runs for the model
        # 1 - find the projection of the temperatures for the next 5 minutes - temp mass
        # 2 - find the bid when HVAC is ON
        # 3 - find the bid when HVAC is OFF
        RT_debug = True
        if RT_debug:
            for itime in range(0, len(time)):
                eAET = linalg.expm(A_ETP * T / 10.0)
                AIET = np.dot(AEI, eAET)
                AEx = np.dot(A_ETP, x)
                if self.hvac_on:
                    AxB = AEx + B_ETP_ON
                    AIB = np.dot(AEI, B_ETP_ON)
                    AExB = np.dot(AIET, AxB)
                    x = AExB - AIB
                    # temp[itime] = xn[0]
                    # self.mass_temp = xn[1]
                    # check if HVAC changes status
                    # temp_curve_tmp[itime] = x[0][0]
                    # quan_curve_tmp[itime] = time[itime] * self.hvac_kw / T
                    #Q_max = time[itime] * self.hvac_kw / T
                    if (x[0][0] < self.cooling_setpoint - self.deadband / 2.0 and self.thermostat_mode == 'Cooling') or \
                            (x[0][0] > self.heating_setpoint + self.deadband / 2.0 and self.thermostat_mode == 'Heating'):
                        self.hvac_on = False
                else:
                    AxB = AEx + B_ETP_OFF
                    AIB = np.dot(AEI, B_ETP_OFF)
                    AExB = np.dot(AIET, AxB)
                    x = AExB - AIB  # + self.deadband/2.0
                    # temp[itime] = x[0]
                    # self.mass_temp = x[1]
                    # temp_curve_tmp[itime] = x[0][0]
                    # quan_curve_tmp[itime] = 0
                    #Q_min = (T - time[itime]) * self.hvac_kw / T
                    if (x[0][0] > self.cooling_setpoint + self.deadband / 2.0 and self.thermostat_mode == 'Cooling') or \
                            (x[0][
                                 0] < self.heating_setpoint - self.deadband / 2.0 and self.thermostat_mode == 'Heating'):
                        self.hvac_on = True

                # temp[itime] = x[0][0]  # this should be updated for each itime
                # temp_mass[itime] = x[1][0]
            self.air_temp_agent = x[0][0] # this gets updated at the end
            self.mass_temp = x[1][0] # this gets updated at the end
            # if self.name == "R5_12_47_2_tn_2_hse_1":
            #     print(self.name)
            #     print("HVAC STAT " + str(self.hvac_on))
            #     print("GLD temp ", self.air_temp)
            #     print("agent temp ", self.air_temp_agent)
            #     print("agent mass ",self.mass_temp)
        elif True:
            # for self.hvac_on==True
            x = np.zeros([2, 1])
            x[0] = self.air_temp
            x[1] = self.mass_temp
            for itime in range(0,len(time)):
                # eAET = np.exp(A_ETP*itime)
                # find the trajectory of each point from x_org
                #eAET = linalg.expm(A_ETP * time[itime])  # T/ 100.0)
                eAET = linalg.expm(A_ETP * T/ len(time))
                AIET = np.dot(AEI, eAET)
                AEx = np.dot(A_ETP, x)

                #if self.hvac_on:
                AxB = AEx + B_ETP_ON
                AIB = np.dot(AEI, B_ETP_ON)
                AExB = np.dot(AIET, AxB)
                x = AExB - AIB  # - self.deadband/2.0
                # temp[itime] = xn[0]
                # self.mass_temp = xn[1]
                # check if HVAC changes status
                # temp_curve_tmp[itime] = x[0][0]
                # quan_curve_tmp[itime] = time[itime] * self.hvac_kw / T
                Q_max = time[itime] * self.hvac_kw / T
                if (x[0][0] < self.temp_min_cool - self.deadband / 2.0 and self.thermostat_mode == 'Cooling') or \
                        (x[0][0] > self.temp_max_heat + self.deadband / 2.0 and self.thermostat_mode == 'Heating'):
                    #self.hvac_on = False
                    break

                # temp[itime] = x[0][0]  # this should be updated for each itime
                # temp_mass[itime] = x[1][0]

            # for self.hvac_on==False
            x = np.zeros([2, 1])
            x[0] = self.air_temp
            x[1] = self.mass_temp
            for itime in range(0, len(time)):
                # eAET = np.exp(A_ETP*itime)
                # find the trajectory of each point from x_org
                # eAET = linalg.expm(A_ETP * time[itime])  # T/ 100.0)
                eAET = linalg.expm(A_ETP * T / len(time))
                AIET = np.dot(AEI, eAET)
                AEx = np.dot(A_ETP, x)

                #else:
                AxB = AEx + B_ETP_OFF
                AIB = np.dot(AEI, B_ETP_OFF)
                AExB = np.dot(AIET, AxB)
                x = AExB - AIB  # + self.deadband/2.0
                # temp[itime] = x[0]
                # self.mass_temp = x[1]
                # temp_curve_tmp[itime] = x[0][0]
                # quan_curve_tmp[itime] = 0
                Q_min = (T-time[itime])*self.hvac_kw / T

                if (x[0][0] > self.temp_max_cool + self.deadband / 2.0 and self.thermostat_mode == 'Cooling') or \
                        (x[0][0] < self.temp_min_heat - self.deadband / 2.0 and self.thermostat_mode == 'Heating'):
                    #self.hvac_on = True
                    break

                # self.air_temp_agent = x[0][0]
                # self.mass_temp = x[1][0]  # this should be updated at T only

        delta_DA_price = max(self.price_forecast) - min(self.price_forecast)
        BID = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        P = 1
        Q = 0
        if Q_min != Q_max:
            CurveSlope = delta_DA_price / (Q_min - Q_max) * (1 + self.ProfitMargin_slope / 100)
            yIntercept = self.price_forecast[0] - CurveSlope * self.bid_da[0][1][0]# / 12
            if self.bid_da[0][1][0] < Q_max and self.bid_da[0][1][0] > Q_min:
                BID[0][Q] = Q_min
                BID[1][Q] = self.bid_da[0][1][0]
                BID[2][Q] = self.bid_da[0][1][0]
                BID[3][Q] = Q_max

                BID[0][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[1][P] = self.bid_da[0][1][0] * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[2][P] = self.bid_da[0][1][0] * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[3][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
            else:
                BID[0][Q] = Q_min
                BID[1][Q] = Q_min
                BID[2][Q] = Q_max
                BID[3][Q] = Q_max

                BID[0][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[1][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[2][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[3][P] = Q_max * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
        else:
            BID[0][Q] = Q_min
            BID[1][Q] = Q_min
            BID[2][Q] = Q_max
            BID[3][Q] = Q_max

            BID[0][P] = max(self.price_forecast) + (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[1][P] = max(self.price_forecast) + (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[2][P] = min(self.price_forecast) - (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[3][P] = min(self.price_forecast) - (self.ProfitMargin_intercept / 100) * delta_DA_price

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

        return self.bid_rt

    def get_uncntrl_hvac_load(self,moh, hod, dow):
        self.DA_model_parameters(moh, hod, dow)
        if self.thermostat_mode == 'Cooling':
            temp_room = self.temp_desired_48hour_cool
            cop_adj = (-np.array(self.cooling_cop_adj)).tolist()
        else:
            cop_adj = self.heating_cop_adj
            temp_room = self.temp_desired_48hour_heat
        # else:
        #     raise ValueError("thermostate mode must be set to either Cooling or Heating")
        Quantity = []
        # print(self.name, "******")
        # print("mode: ",self.thermostat_mode)
        # print("temp_room: ", temp_room)
        # print("temperature_forecast: ", self.temperature_forecast)
        # print("eps: ", self.eps)
        # print("internalgain_forecast: ", self.internalgain_forecast)
        # print("solargain_forecast: ", self.solargain_forecast)
        # print("solar_heatgain_factor: ", self.solar_heatgain_factor)
        # print("latent_factor: ", self.latent_factor)
        # print("cop_adj: ", cop_adj)
        # print("temp_room_init: ", self.temp_room_init)
        for t in self.TIME:
            # estimate required quantity for cooling
            temp_room = self.temp_desired_48hour_cool
            cop_adj = (-np.array(self.cooling_cop_adj)).tolist()
            if t == 0:
                t_pre = self.temp_room_previous_cool
            else:
                t_pre = temp_room[t-1]
            temp1 = ((temp_room[t] - self.eps*t_pre)/(1-self.eps))-self.temperature_forecast[t]
            temp2 = temp1*self.UA - self.internalgain_forecast[t] - self.solargain_forecast[t] * self.solar_heatgain_factor
            quant = temp2/(cop_adj[t] * 3412.1416331279 / self.latent_factor[t])
            # quant = min(quant, self.hvac_kw)
            quant_cool = max(quant, 0)

            # estimate required quantity for heating
            cop_adj = self.heating_cop_adj
            temp_room = self.temp_desired_48hour_heat
            if t == 0:
                t_pre = self.temp_room_previous_heat
            else:
                t_pre = temp_room[t-1]
            temp1 = ((temp_room[t] - self.eps*t_pre)/(1-self.eps))-self.temperature_forecast[t]
            temp2 = temp1*self.UA - self.internalgain_forecast[t] - self.solargain_forecast[t] * self.solar_heatgain_factor
            quant = temp2/(cop_adj[t] * 3412.1416331279 / self.latent_factor[t])
            # quant = min(quant, self.hvac_kw)
            quant_heat = max(quant, 0)

            # Both quant_cool and quant_heat can not be positive simultaneously. So whichever is positive, that mode
            # is active
            quant = max(quant_cool, quant_heat)
            Quantity.append(abs(quant))
            # print("quant: ", quant)

            # Storing the real-time (current hour) temp to be used in next hour initialization
            self.temp_room_previous_cool = self.temp_desired_48hour_cool[0]
            self.temp_room_previous_heat = self.temp_desired_48hour_heat[0]

        return Quantity

    def formulate_bid_da(self):#, moh2, hod2, dow2):
        """ Formulate windowLength hours 4 points PQ bid curves for the DA market

        Function calls DA_optimal_quantities to obtain the optimal quantities for the DA market. With the quantities, a 4 point bids are formulated for each hour.

        Returns
            BID (float) (windowLength X 4 X 2): DA bids to be send to the retail DA market
        """

        BID = [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]] for i in self.TIME]
        if self.heating_system_type != 'HEAT_PUMP' and self.thermostat_mode == 'Heating':
            self.bid_da = BID
            return self.bid_da

        # TODO: skip the following statement if using parallel optimization
        # update model parameters
        # self.DA_model_parameters(moh2, hod2, dow2)

        # optimize quantity and temperature
        # Quantity = self.DA_optimal_quantities()
        Quantity =self.optimized_Quantity
        #print("agent: "+self.name + "Quantity: " + str(Quantity))

        self.FirstTime = False
        P = 1  # self.P
        P = 1  # self.P
        Q = 0  # self.Q

        CurveSlope = [0 for i in self.TIME]
        yIntercept = [-1 for i in self.TIME]

        delta_DA_price = max(self.price_forecast) - min(self.price_forecast)
        for t in self.TIME:
            CurveSlope[t] = (delta_DA_price / (0 - self.hvac_kw) * (1 + self.ProfitMargin_slope / 100))
            yIntercept[t] = (self.price_forecast[t] - CurveSlope[t] * Quantity[t])
            BID[t][0][Q] = 0
            BID[t][1][Q] = Quantity[t]
            BID[t][2][Q] = Quantity[t]
            BID[t][3][Q] = self.hvac_kw

            BID[t][0][P] = 0 * CurveSlope[t] + yIntercept[t] + (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[t][1][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] + (
                        self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[t][2][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] - (
                        self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[t][3][P] = self.hvac_kw * CurveSlope[t] + yIntercept[t] - (
                        self.ProfitMargin_intercept / 100) * delta_DA_price

            for i in range(4):
                if BID[t][i][Q] > self.hvac_kw:
                    BID[t][i][Q] = self.hvac_kw
                if BID[t][i][Q] < 0:
                    BID[t][i][Q] = 0
                if BID[t][i][P] > self.price_cap:
                    BID[t][i][P] = self.price_cap
                if BID[t][i][P] < 0:
                    BID[t][i][P] = 0

        self.bid_da = BID

        return self.bid_da

    def get_scheduled_setpt(self, moh3, hod4, dow3):
        """
        :param moh3: (int): the minute of the hour from 0 to 59
        :param hod4: (int): the hour of the day, from 0 to 23
        :param dow3: (int): the day of the week, zero being Monday
        """

        if 23 < hod4 < 48:
            hod5 = hod4 - 24
            dow4 = dow3 + 1
        elif hod4 > 47:
            hod5 = hod4 - 48
            dow4 = dow3 + 2
        else:
            hod5 = hod4
            dow4 = dow3
        if dow4 > 6:
            dow4 = dow4 - 7
        # print(itime,hod4)
        if dow4 > 4:  # a weekend
            val_cool = self.weekend_night_set_cool
            val_heat = self.weekend_night_set_heat
            if self.weekend_day_start <= hod5 < self.weekend_night_start:
                val_cool = self.weekend_day_set_cool
                val_heat = self.weekend_day_set_heat
        else:  # a weekday
            val_cool = self.night_set_cool
            val_heat = self.night_set_heat
            if self.wakeup_start <= hod5 < self.daylight_start:
                val_cool = self.wakeup_set_cool
                val_heat = self.wakeup_set_heat
            elif self.daylight_start <= hod5 < self.evening_start:
                val_cool = self.daylight_set_cool
                val_heat = self.daylight_set_heat
            elif self.evening_start <= hod5 < self.night_start:
                val_cool = self.evening_set_cool
                val_heat = self.evening_set_heat
        return val_cool, val_heat

    def DA_model_parameters(self,moh3, hod3, dow3):
        '''
        self.basepoint_cooling = 73.278
        self.temp_min_cool = self.temp_min_cool + self.basepoint_cooling
        self.temp_max_cool = self.temp_max_cool + self.basepoint_cooling
        self.thermostat_mode = 'Cooling'

        if self.thermostat_mode == 'Cooling':
            temp_min_48hour = self.temp_min_cool
            temp_max_48hour = self.temp_max_cool
        else:
            temp_min_48hour = self.temp_min_heat
            temp_max_48hour = self.temp_max_heat
        '''

        self.moh = moh3
        self.hod = hod3
        self.dow = dow3
        # temp_desired_48hour
        self.temp_delta = self.temp_max_48hour - self.temp_min_48hour
        self.price_forecast_0 = self.price_forecast[0] # to be used in RT clearing
        # using DA parameters to figure out the schedule forecast
        for itime in range(self.windowLength):
            hod4 = hod3 + moh3 / 60 + itime + 1 / 60  # to take into account the 60 sec shift
            val_cool, val_heat = self.get_scheduled_setpt(moh3, hod4, dow3)
            # update temp limits
            self.update_temp_limits_da(val_cool, val_heat)

            # self.basepoint_cooling = val_cool
            # making sure the desired temperature falls between min and max temp values
            # these values are used to adjust the basepoint and vice-versa
            if val_cool > self.temp_max_cool_da:
                val_cool = self.temp_max_cool_da
            if val_cool < self.temp_min_cool_da:
                val_cool = self.temp_min_cool_da
            if val_heat > self.temp_max_heat_da:
                val_heat = self.temp_max_heat_da
            if val_heat < self.temp_min_heat_da:
                val_heat = self.temp_min_heat_da
            self.temp_desired_48hour_cool[itime] = val_cool
            # # self.basepoint_heating = val_heat
            self.temp_desired_48hour_heat[itime] = val_heat
            # # print("new DA schedule")
        # print (self.temp_desired_48hour_heat)

        #TODO: might need to look ahead at the temperature forecast and decide a mode of operation
        #print("temperature forecast average ", np.mean(self.temperature_forecast))
        '''
        if np.mean(self.temperature_forecast) >= 72.5:
            self.thermostat_mode = 'Cooling'
        else:
            self.thermostat_mode = 'Heating'
        '''

        voltage_adj = 1  # voltage adjustment factor due to voltage dependent ZIP load

        for t in range(self.windowLength):
            self.latent_factor[t] = ((1 + 0.1 + self.latent_load_fraction / (
                    1 + math.exp(4 - 10 * self.humidity_forecast[t]))) * voltage_adj)

            if self.thermostat_mode =='Cooling':
                # use adjusted COP for each step
                if self.temperature_forecast[t] < self.cooling_COP_limit:
                    self.cooling_cop_adj[t] = self.cooling_COP / (
                            self.cooling_COP_K0 + self.cooling_COP_K1 * self.cooling_COP_limit)
                else:
                    self.cooling_cop_adj[t] = self.cooling_COP / (
                            self.cooling_COP_K0 + self.cooling_COP_K1 * self.temperature_forecast[t])
            else:  # if self.thermostat_mode == 'Heating':
                # use adjusted COP for each step
                if self.temperature_forecast[t] < self.heating_COP_limit:
                    # self.heating_cop_adj[t] = self.heating_COP / (
                    #         self.heating_COP_K0 + self.heating_COP_K1 * self.heating_COP_limit)
                    self.heating_cop_adj[t] = self.heating_COP / (
                                self.heating_COP_K0 + self.heating_COP_K1 * self.heating_COP_limit +
                                self.heating_COP_K2 * self.heating_COP_limit**2 +
                                self.heating_COP_K3 * self.heating_COP_limit**3)
                else:
                    # self.heating_cop_adj[t] = self.heating_COP / (
                    #         self.heating_COP_K0 + self.heating_COP_K1 * self.temperature_forecast[t])
                    self.heating_cop_adj[t] = self.heating_COP / (
                            self.heating_COP_K0 + self.heating_COP_K1 * self.temperature_forecast[t] +
                            self.heating_COP_K2 * self.temperature_forecast[t] ** 2 +
                            self.heating_COP_K3 * self.temperature_forecast[t] ** 3)

        self.temp_room_init = self.air_temp
        # if self.thermostat_mode == 'Cooling':
        #     self.temp_room_init = self.temp_desired_48hour_cool[0]
        # else:
        #     self.temp_room_init = self.temp_desired_48hour_heat[0]
        # self.temp_outside_init = self.outside_air_temperature

        return True

    def obj_rule(self, m):
        # 15 - x (50*4^2+50*7^2+50*10^2) -> x = 0.002
        if self.thermostat_mode == 'Cooling':
            # Alternative-5: Bishnu
            # if self.hvac_kw != 0 and self.price_delta!=0 and (self.range_low_limit+self.range_high_limit)!=0:
            #     return sum(self.slider*(self.price_forecast[t]-np.min(self.price_forecast))/self.price_delta * m.quan_hvac[t]/self.hvac_kw
            #                + (1-self.slider)* ((m.temp_room[t] - self.temp_desired_48hour_cool[t])/(self.range_low_limit+self.range_high_limit))**2
            #                + 0.01 * self.slider * (m.quan_hvac[t] / self.hvac_kw * m.quan_hvac[t] / self.hvac_kw)
            #                                    for t in self.TIME)
            # ALternative - 6
            # if self.hvac_kw != 0 and self.ramp_high_cool!=0 and (self.range_low_limit+self.range_high_limit)!=0 and self.price_std_dev!=0:
            #     return sum(self.slider * (self.price_forecast[t] - np.min(self.price_forecast)) / (self.price_std_dev) * m.quan_hvac[t] / self.hvac_kw
            #                + (1 - self.slider) * ((self.temp_desired_48hour_cool[t] - m.temp_room[t]) / (self.range_high_limit+self.range_low_limit)) ** 2 /self.ramp_high_limit
            #                + 0.001 * self.slider * (m.quan_hvac[t] / self.hvac_kw * m.quan_hvac[t] / self.hvac_kw)
            #                for t in self.TIME)
            # Alternative-7: Bishnu-mod
            if self.hvac_kw != 0 and self.price_delta!=0 and (self.range_low_limit+self.range_high_limit)!=0:
                return sum(self.slider*(self.price_forecast[t]-np.min(self.price_forecast))/self.price_delta * m.quan_hvac[t]/self.hvac_kw
                           + 0.1* ((m.temp_room[t] - self.temp_desired_48hour_cool[t])/(self.range_low_limit+self.range_high_limit))**2
                           + 0.001 * self.slider * (m.quan_hvac[t] / self.hvac_kw * m.quan_hvac[t] / self.hvac_kw)
                                               for t in self.TIME)
                # if self.hvac_kw != 0 and self.price_mean!=0 and self.range_low!=0 and self.range_high!=0 and self.price_delta!=0:
                #     return sum((self.price_forecast[t]/self.price_mean * m.quan_hvac[t]/self.hvac_kw*self.slider) + (
                #             (1-self.slider) * (m.temp_room[t] - self.temp_desired_48hour_cool[t]) / self.range_high) +
                #             (3/5*(1-self.slider) * (self.temp_desired_48hour_cool[t] - m.temp_room[t]) / self.range_low )
                #                         + 0.01*self.slider*(m.quan_hvac[t]/self.hvac_kw * m.quan_hvac[t]/self.hvac_kw)# obj = 10-20
                #                for t in self.TIME)
                # return sum((self.price_forecast[t] * m.quan_hvac[t] / self.hvac_kw * self.slider) + (
                #         (1 - self.slider) * (
                #             m.temp_room[t] - self.temp_desired_48hour_cool[t]) / self.range_high * self.price_std_dev) +
                #            (3 / 5 * (1 - self.slider) * (self.temp_desired_48hour_cool[t] - m.temp_room[
                #                t]) / self.range_low * self.price_std_dev)
                #            + 0.001 * self.slider * (m.quan_hvac[t] / self.hvac_kw * m.quan_hvac[t] / self.hvac_kw)
                #            # obj = 10-20
                #            for t in self.TIME)
            else:
                return 0
        else:  # self.thermostat_mode == 'Heating':
            if self.hvac_kw != 0 and self.price_delta != 0 and (self.range_low_limit + self.range_high_limit) != 0:
                return sum(self.slider * (self.price_forecast[t] - np.min(self.price_forecast)) / self.price_delta *
                           m.quan_hvac[t] / self.hvac_kw
                           + 0.1 * ((m.temp_room[t] - self.temp_desired_48hour_heat[t]) / (
                            self.range_low_limit + self.range_high_limit)) ** 2
                           + 0.001 * self.slider * (m.quan_hvac[t] / self.hvac_kw * m.quan_hvac[t] / self.hvac_kw)
                           for t in self.TIME)
            # return sum((self.price_forecast[t] * m.quan_hvac[t] * self.slider)*20 + (
            #         ((-2 * self.range_high * (1 - self.slider) * self.price_std_dev) / self.temp_delta) * (
            #         m.temp_room[t] - self.temp_desired_48hour_heat[t])) + (
            #                    ((-2 * self.range_low * (1 - self.slider) * self.price_std_dev) / self.temp_delta) * (
            #                    self.temp_desired_48hour_heat[t] - m.temp_room[t])) + 0.001 *self.slider* (m.quan_hvac[t] * m.quan_hvac[t])
            #            # obj = 10-20
            #            for t in self.TIME)
            else:
                return 0
        #else:
        #    log.log('Thermostat mode is not defined.')

    def con_rule_eq1(self, m, t):  # initialize SOHC state
        if self.thermostat_mode == 'Cooling':
            if t == 0:
                return m.temp_room[0] == self.eps * self.temp_room_init + (1 - self.eps) * (
                        self.temp_outside_init + (
                        (-self.cooling_cop_adj[0] * 0.98 * m.quan_hvac[0] * 3412.1416331279 / self.latent_factor[0] +
                         self.internalgain_forecast[0]
                         + self.solargain_forecast[
                             0] * self.solar_heatgain_factor) / self.UA))  # Initial SOHC state
            else:
                # update SOHC
                return m.temp_room[t] == self.eps * m.temp_room[t - 1] + (1 - self.eps) * (
                        self.temperature_forecast[t] + (
                        (-self.cooling_cop_adj[t] * 0.98 * m.quan_hvac[t] * 3412.1416331279 / self.latent_factor[t] +
                         self.internalgain_forecast[t] +
                         self.solargain_forecast[t] * self.solar_heatgain_factor) / self.UA))
        else:# self.thermostat_mode == 'Heating':
            if t == 0:
                return m.temp_room[0] == self.eps * self.temp_room_init + (1 - self.eps) * (
                        self.temp_outside_init + (
                        (self.heating_cop_adj[0] * 1.02 * m.quan_hvac[0] * 3412.1416331279 / self.latent_factor[0] +
                         self.internalgain_forecast[0]
                         + self.solargain_forecast[
                             0] * self.solar_heatgain_factor) / self.UA))  # Initial SOHC state
            else:
                # update SOHC
                return m.temp_room[t] == self.eps * m.temp_room[t - 1] + (1 - self.eps) * (
                        self.temperature_forecast[t] + (
                        (self.heating_cop_adj[t] * 1.02 * m.quan_hvac[t] * 3412.1416331279 / self.latent_factor[t] +
                         self.internalgain_forecast[t] +
                         self.solargain_forecast[t] * self.solar_heatgain_factor) / self.UA))
        #else:
        #    log.log('Thermostat mode is not defined.')

    # def temp_bound_rule(self, m, t):
    #     if self.thermostat_mode == 'Cooling':
    #         return (self.temp_desired_48hour_cool[t] - self.range_low_cool,
    #                 self.temp_desired_48hour_cool[t] + self.range_high_cool)
    #     else:
    #         return (self.temp_desired_48hour_heat[t] - self.range_low_heat,
    #                 self.temp_desired_48hour_heat[t] + self.range_high_heat)

    def temp_bound_rule(self,m, t):
        if self.thermostat_mode == 'Cooling':
            return (self.temp_desired_48hour_cool[t] - self.range_low_cool,
                    self.temp_desired_48hour_cool[t] + self.range_high_cool)
        else:
            return (self.temp_desired_48hour_heat[t] - self.range_low_heat,
                    self.temp_desired_48hour_heat[t] + self.range_high_heat)

    def DA_optimal_quantities(self):
        """ Generates Day Ahead optimized quantities for Water Heater according to the forecasted prices and water draw schedule, called by DA_formulate_bid function

        Returns:
            Quantity (list) (1 x windowLength): Optimized quantities for each hour in the DA bidding horizon, in kWh
        """

        # TODO: this is for model validation only
        if False:#self.hod != 0.0 and not self.FirstTime:
            # roll the values to the next hour
            Quantity = self.optimized_Quantity
            Quantity.insert(len(Quantity), Quantity.pop(0))
            temp_room = self.temp_room
            temp_room.insert(len(self.temp_room), temp_room.pop(0))
            return [Quantity, temp_room]
        # else:
        #     print("optimizing quantities")

        nonlinear = True
        # Initialize the problem

        if nonlinear:
            # Decision variables
            model = pyo.ConcreteModel()
            model.quan_hvac = pyo.Var(self.TIME, bounds=(0.0, self.hvac_kw))

            model.temp_room = pyo.Var(self.TIME, bounds=self.temp_bound_rule)

            # if self.thermostat_mode == 'Cooling':
            #     model.temp_room = pyo.Var(self.TIME, bounds=temp_bound_rule)
            #     # model.temp_room = pyo.Var(self.TIME)#, bounds=(self.temp_min_cool, self.temp_max_cool))
            # else:  # self.thermostat_mode == 'Heating':
            #     # model.temp_room = pyo.Var(self.TIME)#, bounds=(self.temp_min_heat, self.temp_max_heat))
            #     model.temp_room = pyo.Var(self.TIME, bounds=temp_bound_rule())
            # model.x = pyo.Var(self.TIME, within=NonNegativeReals)
            # model.y = pyo.Var(self.TIME, within=NonNegativeReals)

            # Objective of the problem
            model.obj = pyo.Objective(rule=self.obj_rule, sense=pyo.minimize)
            # Constraints
            model.con1 = pyo.Constraint(self.TIME, rule=self.con_rule_eq1)

            results = helpers.get_run_solver("hvac_"+self.name, pyo, model, self.solver)

            if False:#self.hvac_kw != 0 and self.price_mean != 0 and self.range_low_cool != 0 and self.range_high != 0 and self.price_delta != 0:
                print("optimization quantities", self.name)
                print(sum((self.price_forecast[t]/self.price_mean * pyo.value(model.quan_hvac[t])/self.hvac_kw * self.slider) * 20 for t in self.TIME))
                print(sum((1 * (1 - self.slider)*(pyo.value(model.temp_room[t]) - self.temp_desired_48hour_cool[t])/ self.range_high_cool) for t in self.TIME))
                print(sum((3/5 * (1 - self.slider) *(self.temp_desired_48hour_cool[t] - pyo.value(model.temp_room[t])) / self.range_low_cool) for t in self.TIME))
                print(sum(0.01 * self.slider * (pyo.value(model.quan_hvac[t])/self.hvac_kw * pyo.value(model.quan_hvac[t])/self.hvac_kw) for t in self.TIME))

            Quantity = [0 for i in self.TIME]
            temp_room = [0 for i in self.TIME]
            TOL = 0.00001 # Tolerance for checking bid
            for t in self.TIME:
                temp_room[t] = pyo.value(model.temp_room[t])
                #if self.temp_room[t] > TOL:
                Quantity[t] = pyo.value(model.quan_hvac[t])

            if False:#False and self.name == "R5_12_47_2_tn_3_hse_5":
                print(self.name)#"R5_12_47_2_tn_3_hse_5")
                print("DA Quantity")
                print(Quantity)
                print("room_temp")
                print(self.temp_room)
                print("self.temperature_forecast")
                print(self.temperature_forecast)
                print("self.price_forecast")
                print(self.price_forecast)
                print("self.internalgain_forecast")
                print(self.internalgain_forecast)
                print("self.solargain_forecast")
                print(self.solargain_forecast)
                print("self.slider,self.range_high_cool,self.range_low_cool,self.temp_delta,self.price_std_dev")
                print(self.slider, self.range_high_cool,self.range_low_cool,self.temp_delta,self.price_std_dev)
                print("self.temp_desired_48hour_cool")
                print(self.temp_desired_48hour_cool)
                print("self.eps,self.temp_room_init,self.temp_outside_init,self.solar_heatgain_factor,self.UA")
                print(self.eps,self.temp_room_init,self.temp_outside_init,self.solar_heatgain_factor,self.UA,self.CA,self.CM,self.HM)
                print("self.cooling_cop_adj")
                print(self.cooling_cop_adj)
                print("self.latent_factor")
                print(self.latent_factor)

        else: # for linear optimizer
            prob = pulp.LpProblem("QuantityBid", pulp.LpMinimize)
            # Decsicion variables
            # classmethod dicts(name, indexs, lowBound=None, upBound=None, cat=0, indexStart=[])

            if self.thermostat_mode == 'Cooling':
                # to avoid problem while warming up and gridlabd is heating instead of cooling
                if self.hvac_kw < 3.0:
                    self.hvac_kw = 3.0
                # if self.hvac_kw>6.0:
                #    self.hvac_kw = 6.0
                quan_hvac = pulp.LpVariable.dicts("hvac_quantity", self.TIME, 0, self.hvac_kw)
                temp_room = pulp.LpVariable.dicts("Temparature_room", self.TIME, self.temp_min_cool,
                                                  self.temp_max_cool)
                # temp_desired_48hour_tmp = temp_desired_48hour_cool[:]#self.temp_desired_48hour_cool
                # temp_desired_48hour_tmp = self.temp_desired_48hour_cool
                # Objective
                # pulp.lpSum(vector) --> Calculate the sum of a list of linear expressions
                prob += pulp.lpSum((self.price_forecast[t] * quan_hvac[t] * self.slider) + (
                        ((2 * self.range_high_cool * self.price_std_dev) / self.temp_delta) * (
                        temp_room[t] - self.temp_desired_48hour_cool[t])) + (
                                           ((2 * self.range_low_cool * self.price_std_dev) / self.temp_delta) * (
                                           self.temp_desired_48hour_cool[t] - temp_room[t]))
                                   for t in self.TIME)
            else: # for heating
                quan_hvac = pulp.LpVariable.dicts("hvac_quantity", self.TIME, -self.hvac_kw, 0)
                temp_room = pulp.LpVariable.dicts("Temparature_room", self.TIME, self.temp_min_heat,
                                                  self.temp_max_heat)
                # temp_desired_48hour_tmp = temp_desired_48hour_heat[:]#self.temp_desired_48hour_heat
                # temp_desired_48hour_tmp = self.temp_desired_48hour_heat
                # Objective
                # pulp.lpSum(vector) --> Calculate the sum of a list of linear expressions
                ##prob += pulp.lpSum(self.f_DA_price[t]*(E_upper[t] + E_bottom[t])+self.weight_comfort*(self.SOHC_desired-SOHC[t]) for t in TIME)
                prob += pulp.lpSum((self.price_forecast[t] * quan_hvac[t]) + (
                        ((-2 * self.range_high_heat * self.price_std_dev) / self.temp_delta) * (
                            temp_room[t] - self.temp_desired_48hour_heat[t])) + (
                                           ((-2 * self.range_low_heat * self.price_std_dev) / self.temp_delta) * (
                                           self.temp_desired_48hour_heat[t] - temp_room[t])) for t in self.TIME)

            # Constraints
            prob += temp_room[0] == self.eps * self.temp_room_init + (1 - self.eps) * (
                    self.temp_outside_init + (
                    (-self.cooling_cop_adj[0] * quan_hvac[0] * 3412.1416331279 / self.latent_factor[0] + self.internalgain_forecast[0]
                     + self.solargain_forecast[0] * self.solar_heatgain_factor) / self.UA))  # Initial SOHC state

            for t in range(1, self.windowLength):  # Update SOHC

                prob += temp_room[t] == self.eps * temp_room[t - 1] + (1 - self.eps) * (
                        self.temperature_forecast[t] + (
                        (-self.cooling_cop_adj[t] * quan_hvac[t] * 3412.1416331279 / self.latent_factor[t] +
                         self.internalgain_forecast[t] +
                         self.solargain_forecast[t] * self.solar_heatgain_factor) / self.UA))

            prob.solve()  # Solve optimization for one HVAC

            # approach 1
            # 0 is init
            # DA for 1 - 47

            # final DA = [init,1-47]

            # Approach 2
            # 0 init - 1am
            # DA 1 - 48 = 2am->  - forecast
            # final DA = [1 - 48]
            # send DA[1]
            Quantity = [0 for i in self.TIME]
            TOL = 0.00001  # Tolerance for checking bid
            for t in self.TIME:
                self.temp_room[t] = temp_room[t].varValue
                if temp_room[t].varValue > TOL:
                    Quantity[t] = quan_hvac[t].varValue

        return [Quantity, temp_room]

    def test_function(self):
        """ Test function with the only purpose of returning the name of the object

        """
        return self.name

    def calc_1st_etp_model(self):
        """ Uses ETP second order model to obtain a first order model

        """
        T = (self.bid_delay + self.period) / 3600.0  # 300
        # self.eps = math.exp(-self.UA/(self.CM+self.CA)*T*12.0) # CM might be the correct one
        self.eps = math.exp(-self.UA / (self.CM + self.CA) * 1.0)  # using 1 fixed for time constant
        self.COP = 3.0
        self.K1 = 5.0
        self.K2 = 3.0
        # print("eps "+str(self.eps))
        # print("UA - func"+str(self.UA))

    def set_da_cleared_quantity(self, BID, PRICE):
        """ Convert the 4 point bids to a quantity with the known price

        Args:
            BID (float) ((1,2)X4): 4 point bid
            PRICE (float): cleared price in $/kWh

        Returns:
            quantity (float): cleared quantity
        """
        P = 1
        Q = 0
        # TODO: these equations might need revising
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
    """Testing

    Makes a single hvac agent and run DA 
    """
    hvac_properties = \
    {"feeder_id": "R5_12.47_2",
      "billingmeter_id": "R5_12_47_2_tn_3_mtr_1",
      "sqft": 3977.0,
      "stories": 1,
      "doors": 4,
      "thermal_integrity": "ABOVE_NORMAL",
      "cooling": "ELECTRIC",
      "heating": "GAS",
      "wh_gallons": 0,
      "house_class": "SINGLE_FAMILY",
      "Rroof": 45.95,
      "Rwall": 25.24,
      "Rfloor": 33.73,
      "Rdoors": 12.19,
      "airchange_per_hour": 0.28,
      "ceiling_height": 9,
      "thermal_mass_per_floor_area": 3.406,
      "glazing_layers": 3,
      "glass_type": 2,
      "window_frame": 4,
      "glazing_treatment": 2,
      "cooling_COP": 3.8,
      "over_sizing_factor": 0.3038,
      "fuel_type": "gas",
      "zip_skew": 1076.0,
      "zip_heatgain_fraction": {
        "constant": 1.0,
        "responsive_loads": 0.9,
        "unresponsive_loads": 0.9
      },
      "zip_scalar": {
        "constant": 0.0,
        "responsive_loads": 1.43,
        "unresponsive_loads": 1.32
      }
    }
    hvac_dict = {
        "houseName": "R5_12_47_2_tn_3_hse_1",
        "meterName": "R5_12_47_2_tn_3_mtr_1",
        "houseClass": "SINGLE_FAMILY",
        "period": 300,
        "wakeup_start": 6.807,
        "daylight_start": 9.178,
        "evening_start": 18.96,
        "night_start": 23.9,
        "weekend_day_start": 9.362,
        "weekend_night_start": 23.749,
        "wakeup_set_cool": 74.0,
        "daylight_set_cool": 74.0,
        "evening_set_cool": 74.0,
        "night_set_cool": 72.0,
        "weekend_day_set_cool": 74.0,
        "weekend_night_set_cool": 72.0,
        "wakeup_set_heat": 69.0,
        "daylight_set_heat": 69.0,
        "evening_set_heat": 69.0,
        "night_set_heat": 69.0,
        "weekend_day_set_heat": 69.0,
        "weekend_night_set_heat": 69.0,
        "deadband": 2.892,
        "ramp_high_limit": 2.0,
        "ramp_low_limit": 2.0,
        "range_high_limit": 5.0,
        "range_low_limit": 3.0,
        "slider_setting": 0.3105,
        "price_cap": 1.0,
        "bid_delay": 45,
        "house_participating": False,
        "cooling_participating": False,
        "heating_participating": False
    }

    ### Uncomment for testing logging functionality.
    ### Supply these values (into WaterHeaterDSOT) when using the water
    ### heater agent in the simulation.
    # model_diag_level = 11
    # hlprs.enable_logging('DEBUG', model_diag_level)
    start_time = '2016-08-12 05:59:00'
    time_format = '%Y-%m-%d %H:%M:%S'
    sim_time = datetime.strptime(start_time, time_format)
    obj = HVACDSOT(hvac_dict, hvac_properties, 'abc', 11, sim_time, 'ipopt')
    # obj.set_solargain_forecast(forecast_solargain)
    # if obj.change_basepoint(sim_time.minute, sim_time.hour, sim_time.weekday(), 11, start_time):
    #     pass
    obj.DA_model_parameters(sim_time.minute, sim_time.hour, sim_time.weekday())

    obj.optimized_Quantity, obj.temp_room = obj.DA_optimal_quantities()


    # print(obj.temp_desired_48hour_cool)
    for i in range(10):
        sim_time = sim_time + timedelta(hours=1)
        obj.get_uncntrl_hvac_load(sim_time.minute, sim_time.hour, sim_time.weekday())

        # B_obj.Cinit = B_obj.batteryCapacity * 0.5#B_obj.set_battery_SOC()

    # BID = [[-5.0, 6.0], [0.0, 5.0], [0.0, 4.0], [5.0, 3.0]]
    # fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, 10.0)
    # print(fixed)
    # fixed = B_obj1.RT_fix_four_points_range(BID, -float('inf'), 0.0)
    # print(fixed)
    # fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, float('inf'))
    # print(fixed)
    # fixed = B_obj1.RT_fix_four_points_range(BID, 0.5, 0.5)
    # print(fixed)
    # getQ = B_obj1.from_P_to_Q_battery(BID, 10)
    # print(getQ)
    # getQ = B_obj1.from_P_to_Q_battery(fixed, 10)
    # print(getQ)
