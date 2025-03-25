# Copyright (C) 2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: hvac_new_agent.py
"""HVAC agent is responsible for coordinating the activity of a single-zone
HVAC system in a transactive system. See the class docstring for further
details.

---
A Note on Units:
Unless otherwise stated, TESP and DSO+T maintain the following unit conventions:

Temperature - Fahrenheit [F]
Time - Seconds [s]
Price/Bids - []
Heatgain - [Btu/h]
Heating/Cooling Capacity - [Btu/h]
R values - [F*sqft*hr/Btu]
Length/Distance - [ft]
Area - [sqft]

Where units may be non-obvious, the choice of unit will be specified in the 
variable name, i.e., variable_unit. This is of particular note for units of 
power and energy, to keep track of kW(h) vs. MW(h).
---

@author: Trevor Hardy
"""

from enum import Enum
import logging
import datetime as dt
import math
from math import cos as cos
from math import sin as sin
import numpy as np
from scipy import linalg
import pyomo.environ as pyo
from dataclasses import dataclass
from tesp_support.api.helpers import get_run_solver
from tesp_support.api.parse_helpers import parse_number, parse_magnitude #TODO unused


# TODO: solar_heatgain_factor was moved to the strucutral model and 
# the move needs to be cleaned up.

# Setting up logging
logger = logging.getLogger(__name__)

# Constants
KW_TO_BTU_PER_HR = 3412.1416331279

def init_class_attributes(obj: object, attr: dict):
    """Function to define values for an object's attributes

    Attribute names and values are defined in a dictionary that is passed in.

    Any key in the dictionary that matches an object attribute posts an "info"
    message.
    Any key in the dictionary that is not an object attribute throws an error.
    Any object attribute that is not defined in the dictionary posts a
    warning.

    Args:
        obj (object): Object whose attributes are being defined
        attr (dict): Dictionary used to define the attributes of the object
    """
    # Getting class name to make logging more specific
    class_str = str(obj.__class__)
    class_str_parts = class_str.split(".")
    class_name = class_str_parts[-1].split("'")[0]

    for key, value in attr.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
            logger.info(f"{class_name}: set {key} to {value}")
        else:
            raise KeyError((f"{class_name} doesn't have attribute '{key}' stored in attribute dictionary"))

    for obj_key, obj_val in obj.__dict__.items():
        if obj_val == None:
            logger.warning(f"{class_name}: attribute '{obj_key}' in object '{obj.name}' was not defined in attribute dictionary")
    
class HVACDSOTAgent:
    def __init__(self, attributes: dict):
        self.name: str = None
        self.house_name: str = None
        self.meter_name: str = None
        self.period: int = None
        self.sim_time: dt.datetime = None
        init_class_attributes(self, attributes["agent"])
        
        self.temp = HVACTemperatures(attributes["temperature"])
        self.schedule = HVACSchedule(attributes["schedule"])
        self.da_market_interface = DSOTDAMarketInterface()
        self.forecasts = DSOTForecasts(attributes["forecasts"])
        self.asset = HVACDSOTAsset(attributes["asset"])
        self.asset_state = HVACDSOTAssetState()
        self.structure_model = HVACDSOTStructureModel(attributes["structure_model"])
        self.etp_structure_params = self.structure_model.ETPStructureParams()
        self.thermostat_mode = ThermostatMode()
        self.asset_model = HVACDSOTAssetModel()
        self.env_model = self.asset_model.HVACDSOTEnvironmentModel()
        self.system_model = HVACDSOTSystemModel(attributes["system_model"])
        self.flexibility = HVACDSOTPriceFlexibilityCurve()
        self.da_bidding_strategy = HVACDSOTDABiddingStrategy(
            attributes["da_bidding_strategy"],
            self.schedule,
            self.flexibility,
            self.forecasts,
            self.temp, 
            self.system_model,
            self.asset_state,
            self.structure_model,
            self.structure_model.etp_structure_params,
            self.asset_model
            )
        self.rt_bidding_strategy = HVACDSOTRTBiddingStrategy(attributes["rt_bidding_strategy"],
                                                            self.period,
                                                            self.schedule,
                                                            self.flexibility,
                                                            self.asset_model,
                                                            self.asset_state,
                                                            self.temp,
                                                            self.system_model,
                                                            self.da_bidding_strategy,
                                                            self.forecasts)
        self.rt_market_interface = DSOTRTMarketInterface()
        self.helics_topic_map = {} # TODO: unused

    def calc_capacites_and_all_heat_flows(self):
        """ Easiest way to ensure that the capacities are calculated before the
        heat flows. These capacities are a function of the outdoor air 
        temperature and thus need to be updated regularly.
        """
        HVACDSOTSystemModel.calc_cooling_capacity()
        HVACDSOTSystemModel.calc_heating_capacity()
        HVACDSOTAssetModel.HVACDSOTEnvironmentModel.calc_all_heat_flows(self.asset_state.house_kW,
                                                               self.asset_state.wh_kW,
                                                               self.asset_state.thermostat_mode,
                                                               self.asset_state.hvac_on,
                                                               self.system_model.heating_capacity,
                                                               self.system_model.cooling_capacity,
                                                               self.asset_state.hvac_kW) 
        
class HVACTemperatures:
    """Sets attributes for object
    
    """
    def __init__(self, attributes: dict):
        """Sets attributes for object

        Args:
            name (str): object name
            attributes (dict): attributes dictionary, externally defined. These
                are generally not fixed throughout the simulation.
        """
        self.name: str = None
        self.T_lower_limit: float = None
        self.T_upper_limit: float = None
        self.cooling_setpoint_lower: float = None
        self.cooling_setpoint_upper: float = None
        self.heating_setpoint_lower: float = None
        self.heating_setpoint_upper: float = None
        self.basepoint_cooling: float = None
        self.basepoint_heating: float = None
        self.cooling_setpoint: float = None
        self.heating_setpoint: float = None
        self.wakeup_set_cool: float = None
        self.daylight_set_cool: float = None
        self.evening_set_cool: float = None
        self.night_set_cool: float = None
        self.weekend_day_set_cool: float = None
        self.weekend_night_set_cool: float = None
        self.wakeup_set_heat: float = None
        self.daylight_set_heat: float = None
        self.evening_set_heat: float = None
        self.night_set_heat: float = None
        self.weekend_day_set_heat: float = None
        self.weekend_night_set_heat: float = None
        self.deadband: float = None
        self.temp_max_cool: float = 0
        self.temp_min_cool: float = 0
        self.temp_max_heat: float = 0
        self.temp_min_heat: float = 0
        init_class_attributes(self, attributes)

    def validate_inputs(self) -> None:
        if self.daylight_set_heat > self.night_set_heat:
            logger.debug('{} {} -- daylight_set_heat ({}) is not <= night_set_heat ({}).'
                    .format(self.name, 'init', self.daylight_set_heat, self.night_set_heat))
        if self.daylight_set_heat > self.wakeup_set_heat:
            logger.debug('{} {} -- daylight_set_heat ({}) is not <= wakeup_set_heat ({}).'
                    .format(self.name, 'init', self.daylight_set_heat, self.wakeup_set_heat))

class HVACSchedule:
    def __init__(self, attributes: dict, agent: HVACDSOTAgent):
        """Sets attributes for object

        Args:
            name (str): object name
            attributes (dict): attributes dictionary, externally defined. These
                are generally not fixed throughout the simulation.
        """
        self.agent = agent
        self.name: str = None
        self.wakeup_start_hr: float = None
        self.daylight_start_hr: float = None
        self.evening_start_hr: float = None 
        self.night_start_hr: float = None 
        self.weekend_day_start_hr: float = None
        self.weekend_night_start_hr: float = None
        self.ramp_high_limit: float = None
        self.ramp_low_limit: float = None
        self.ramp_low_cool: float = 0
        self.ramp_high_cool: float = 0
        self.ramp_low_heat: float = 0
        self.ramp_high_heat: float = 0
        self.range_high_limit: float = 0
        self.range_low_limit: float = 0
        self.range_low_cool: float = 0
        self.range_high_cool: float = 0
        self.range_low_heat: float = 0
        self.range_high_heat: float = 0
        init_class_attributes(self, attributes)
        
    def validate_inputs(self):
        if self.wakeup_start_hr > self.daylight_start_hr:
            logger.debug('{} {} -- wakeup_start_hr ({}) is not < daylight_start_hr ({}).'
                    .format(self.name, 'init', self.wakeup_start_hr, self.daylight_start_hr))
        if self.daylight_start_hr > self.evening_start_hr:
            logger.debug('{} {} -- daylight_start_hr ({}) is not < evening_start_hr ({}).'
                    .format(self.name, 'init', self.daylight_start_hr, self.evening_start_hr))
        if self.evening_start_hr > self.night_start_hr:    
            logger.debug('{} {} -- evening_start_hr ({}) is not < night_start_hr ({}).'
                    .format(self.name, 'init', self.evening_start_hr, self.night_start_hr))
        if self.weekend_day_start_hr > self.weekend_night_start_hr:
            logger.debug('{} {} -- weekend_day_start_hr ({}) is not < weekend_night_start_hr ({}).'
                    .format(self.name, 'init', self.weekend_day_start_hr, self.weekend_night_start_hr))

    def get_scheduled_setpoint(self, hour_of_day: int, day_of_week: int) -> tuple:
        if 23 < hour_of_day < 48:
            hour_of_day = hour_of_day - 24
            day_of_week = day_of_week + 1
        elif hour_of_day > 47:
            hour_of_day = hour_of_day - 48
            day_of_week = day_of_week + 2
        else:
            hour_of_day = hour_of_day
            day_of_week = day_of_week
        if day_of_week > 6:
            day_of_week = day_of_week - 7
        if day_of_week > 4:  # a weekend
            val_cool = self.agent.temp.weekend_night_set_cool
            val_heat = self.agent.temp.weekend_night_set_heat
            if self.weekend_day_start_hr <= day_of_week < self.weekend_night_start_hr:
                val_cool = self.agent.temp.weekend_day_set_cool
                val_heat = self.agent.temp.weekend_day_set_heat
        else:  # a weekday
            val_cool = self.agent.temp.night_set_cool
            val_heat = self.agent.temp.night_set_heat
            if self.wakeup_start_hr <= day_of_week < self.daylight_start_hr:
                val_cool = self.agent.temp.wakeup_set_cool
                val_heat = self.agent.temp.wakeup_set_heat
            elif self.daylight_start_hr <= day_of_week < self.evening_start_hr:
                val_cool = self.agent.temp.daylight_set_cool
                val_heat = self.agent.temp.daylight_set_heat
            elif self.evening_start_hr <= day_of_week < self.night_start_hr:
                val_cool = self.agent.temp.evening_set_cool
                val_heat = self.agent.temp.evening_set_heat
        return val_cool, val_heat
    
    def change_basepoint(self, 
                         sim_time: dt.datetime,
                         model_diag_level: int = 0) -> bool:
        """ Updates the time-scheduled thermostat setting

        Args:
            sim_time (datetime): Current simulation time
            model_diag_level (int): Specific level for logging errors. Defaults 
                to whatever level the parent defines.
            
        Returns:
            bool: True if the setting changed, False if not
        """
        if sim_time.weekday() > 4:  # a weekend
            val_cool = self.agent.temp.weekend_night_set_cool
            val_heat = self.agent.temp.weekend_night_set_heat
            if self.weekend_day_start_hr <= sim_time.hour < self.weekend_night_start_hr:
                val_cool = self.agent.temp.weekend_day_set_cool
                val_heat = self.agent.temp.weekend_day_set_heat
        else:  # a weekday
            val_cool = self.agent.temp.night_set_cool
            val_heat = self.agent.temp.night_set_heat
            if self.wakeup_start_hr <= sim_time.hour < self.daylight_start_hr:
                val_cool = self.agent.temp.wakeup_set_cool
                val_heat = self.agent.temp.wakeup_set_heat
            elif self.daylight_start_hr <= sim_time.hour < self.evening_start_hr:
                val_cool = self.agent.temp.daylight_set_cool
                val_heat = self.agent.temp.daylight_set_heat
            elif self.evening_start_hr <= sim_time.hour < self.night_start_hr:
                val_cool = self.agent.temp.evening_set_cool
                val_heat = self.agent.temp.evening_set_heat
        if abs(self.agent.temp.basepoint_cooling - val_cool) > 0.1 or \
              abs(self.agent.temp.basepoint_heating - val_heat) > 0.1:
            self.agent.temp.basepoint_cooling = val_cool
            if self.agent.temp.basepoint_cooling < 65 or self.agent.temp.basepoint_cooling > 85:
                # TODO reimpliment this with the TBD standard TESP logging
                logger.debug('{} {} -- basepoint_cooling ({}) is out of bounds.'
                        .format(self.name, sim_time, self.agent.temp.basepoint_cooling))
            self.agent.temp.basepoint_heating = val_heat
            if self.agent.temp.basepoint_heating < 60 or self.agent.temp.basepoint_heating > 85:
                logger.debug('{} {} -- basepoint_heating ({}) is out of bounds.'
                        .format(self.name, sim_time, self.agent.temp.basepoint_heating))
            self.calc_thermostat_settings(model_diag_level, sim_time)  # update thermostat settings
            return True
        return False
    
    def calc_thermostat_settings(self, 
                                 slider: float,
                                 model_diag_level: int = 0) -> None:
        """ Sets the ETP parameters from configuration data

        Args:
            sim_time (datetime): Current simulation time
            many thermostat values
            model_diag_level (int): Specific level for logging errors. TODO:unused
            Defaults to whatever level the parent defines.

        References:
            `Table 3 -  Easy to use slider settings <http://gridlab-d.shoutwiki.com/wiki/Transactive_controls>`_
        """
        self.range_high_cool = self.range_high_limit * slider 
        self.range_low_cool = self.range_low_limit * slider  
        self.range_high_heat = self.range_high_limit * slider  
        self.range_low_heat = self.range_low_limit * slider

        if slider != 0:
            # cooling
            self.ramp_high_cool = self.ramp_high_limit * (1 - slider) 
            self.ramp_low_cool = self.ramp_low_limit * (1 - slider) 
            # heating
            self.ramp_high_heat = self.ramp_low_limit * (1 - slider) 
            self.ramp_low_heat = self.ramp_high_limit * (1 - slider)
        else:
            # cooling
            self.ramp_high_cool = 0.0
            self.ramp_low_cool = 0.0
            # heating
            self.ramp_high_heat = 0.0
            self.ramp_low_heat = 0.0

        # we need to check if heating and cooling bid curves overlap
        if self.agent.temp.basepoint_cooling - self.agent.temp.deadband / 2.0 - 0.5 < self.agent.temp.basepoint_heating + self.agent.temp.deadband / 2.0 + 0.5:
            # update minimum cooling and maximum heating temp
            mid_point = (self.agent.temp.basepoint_cooling + self.agent.temp.basepoint_heating) / 2.0
            self.agent.temp.basepoint_cooling = mid_point + self.agent.temp.deadband / 2.0 + 0.5
            self.agent.temp.basepoint_heating = mid_point - self.agent.temp.deadband / 2.0 - 0.5

        # def update_temp_limits(self, cooling_setpt, heating_setpt):
        self.temp_max_cool = self.agent.temp.basepoint_cooling + self.range_high_cool  
        self.temp_min_cool = self.agent.temp.basepoint_cooling - self.range_low_cool  
        self.temp_max_heat = self.agent.temp.basepoint_heating + self.range_high_heat 
        self.temp_min_heat = self.agent.temp.basepoint_heating - self.range_low_heat 
        max_plus_deadband = self.temp_max_heat + self.agent.temp.deadband / 2.0 + 0.5
        min_less_deadband = self.temp_min_cool - self.agent.temp.deadband / 2.0 - 0.5
        if max_plus_deadband > min_less_deadband:
            mid_point = (self.temp_min_cool + self.temp_max_heat) / 2.0
            self.temp_min_cool = mid_point + self.agent.temp.deadband / 2.0 + 0.5
            self.temp_max_heat = mid_point - self.agent.temp.deadband / 2.0 - 0.5
            if self.temp_min_cool > self.agent.temp.basepoint_cooling:
                self.temp_min_cool = self.agent.temp.basepoint_cooling
            if self.temp_max_heat < self.agent.temp.basepoint_heating:
                self.temp_max_heat = self.agent.temp.basepoint_heating
        
class DSOTDAMarketInterface:
    def __init__(self):
        self.clearing_price:float = 0
        self.clearing_quantities:float = 0
class DSOTForecasts:
    def __init__(self, attributes: dict):
        """TODO

        Args:
            attributes (dict): attributes dictionary, externally defined. These
                are generally not fixed throughout the simulation.
        """
        self.name: str = None
        self.price: list = None
        self.outside_air_temperature: list = None
        self.humidity: list = None
        self.solar_direct: list = None
        self.solar_diffuse: list  = None
        self.solar_gain = []
        self.forecast_ziploads: list = None
        self.full_forecast_zipload = [0]
        self.internal_gain: list = None
        self.zipload = []
        self.inside_air_temperature = []
        init_class_attributes(self, attributes)

        self.price_std_dev: float = None
        self.price_delta: float = None
        self.price_mean: float = None
        self.price_forecast_0: float = None
        self.price_forecast_0_new: float = 50
        self.outside_air_temp_min_48hour: float = None
        self.outside_air_temp_max_48hour: float = None
        self.calc_forecast_stats()

    def calc_forecast_stats(self) -> None:
        self.price_std_dev = np.std(self.price)
        self.price_delta = max(self.price) - min(self.price)
        self.price_mean = np.mean(self.price)
        self.outside_air_temp_min_48hour= min(self.outside_air_temperature)
        self.outside_air_temp_min_48hour= max(self.outside_air_temperature)
        self.price_forecast_0 = self.price[0]
        
    def generate_forecast_times(self, sim_time: dt.datetime, da_period: dt.timedelta, windowLength_hr: int):
        """Creates the list of simulation times of length windowLength_hr. Note
        windowLength_hr is unitless and simply the number of periods that 
        need to be forecasted

        Args:
            sim_time (dt.datetime): _description_
            da_period (dt.timedelta): _description_
            windowLength_hr (int): _description_

        Returns:
            _type_: _description_
        """
        forecast_times = []
        for _ in range(windowLength_hr):
            forecast_times.append(sim_time + da_period)
        return forecast_times

    def calc_solar_gain_forecast(self, times: list, 
                                 solar_direct: list = None,
                                 solar_diffuse: list = None) -> list:

        if len(times) != len(solar_direct) and len(times) != len(solar_diffuse) and len(solar_direct) != len(solar_diffuse):
            raise RuntimeError(f"Lengths need to be equal: len(times) = {len(times)}, \
                                                            len(solar_direct) = {len(solar_direct)}, \
                                                            len(solar_diffuse) = {len(solar_diffuse)}")
 
        # Have to do this because Python won't allow object attributes as
        # optional parameters in a method signature. Sigh.
        if solar_direct == None:
            solar_direct = self.solar_direct
        if solar_diffuse == None:
            solar_diffuse = self.solar_diffuse
        # times = list of DateTimes
        for idx, time in enumerate(times):
            self.solar_gain.append(
                HVACDSOTAssetModel.HVACDSOTEnvironmentModel.calc_solargain(time, solar_direct[idx], solar_diffuse[idx]))
        return self.solar_gain
    
class HVACDSOTAsset:
    def __init__(self, attributes: dict, agent: HVACDSOTAgent):
        """TODO

        Args:
            attributes (dict): attributes dictionary, externally defined. These
                are generally not fixed throughout the simulation.
        """
        self.agent = agent
        self.asset_state = HVACDSOTAssetState(attributes["asset_state"])
        self.asset_model = HVACDSOTAssetModel(attributes["asset_model"],
                                                self.agent.temp,
                                                self.asset_state,
                                                self.agent.forecasts,
                                                self.asset_state.thermostat_mode)    

class HVACDSOTAssetState:
    def __init__(self, source_obj: object = None):
        """ Creates new object with same attribute values as the source object
            passed-in.

        Args:
            source_obj (object, optional): TODO. Defaults to None.
        """
        self.indoor_air_temp: float = 0
        self.mass_temp: float  = 0
        self.hvac_kW: float  = 0
        self.wh_kW: float  = 0
        self.house_kW: float  = 0
        self.mtr_v: float  = 0
        self.hvac_on: bool = False
        self.thermostat_mode = ThermostatMode.UNDEFINED #TODO this is unused here
        if source_obj is not None:
            self.copy_attributes_from(source_obj)

    def copy_attributes_from(self, other_obj: object) -> None:
        """Takes attributes from one object and copies the values into the
        attributes of another objects of the same type.

        Allows the quick creation 

        Args:
            other_obj (HVACDSOTAgent): Object whose attributes are the source
            of the data being copied into the target object's attributes.
        """
        if isinstance(other_obj, HVACDSOTAssetState):
            self.__dict__.update(other_obj.__dict__)

    def update_asset_state(self, new_state: dict):
        """It's not clear if this is needed during normal operations where the
        HELICS connection is managed elsewhere. For testing purposes, having
        a way to change the current condition of the HVAC and house objects
        seems like a good idea. TODO: confirm and update docstring

        Args:
            new_state (dict): _description_
        """
        init_class_attributes(self, new_state)    
        
class HVACDSOTStructureModel:
    def __init__(self, attributes: dict):
        """Sets attributes for object

        Args:
            name (str): object name
            attributes (dict): attributes dictionary, externally defined. These
                are generally fixed throughout the simulation.
        """
        self.name: str = None
        self.sqft: float = None
        self.stories: int = None
        self.doors: int = None
        self.Rroof: float = None
        self.Rwall: float = None
        self.Rfloor: float = None
        self.Rdoors: float = None
        self.window_transmission_coefficient: float = None
        self.airchange_per_hour: float = None
        self.ceiling_height: float = None
        self.thermal_mass_per_floor_area: float = None
        self.aspect_ratio: float = None
        self.exterior_ceiling_fraction: float = None
        self.exterior_floor_fraction: float = None
        self.exterior_wall_fraction: float = None
        self.interior_exterior_wall_ratio: float = None
        self.WETC: float = None
        self.glazing_layers: int = None
        self.window_wall_ratio: float = None
        self.gross_air_heat_capacity: float = None
        self.interior_heat_transfer_coefficient: float = None
        self.Rroof_lower_limit: float = None
        self.Rroof_upper_limit: float = None
        self.Rwall_lower_limit: float = None
        self.Rwall_upper_limit: float = None
        self.Rfloor_lower_limit: float = None
        self.Rfloor_upper_limit: float = None
        self.Rdoor_lower_limit: float = None
        self.Rdoor_upper_limit: float = None
        self.airchange_per_hour_lower_limit: float = None
        self.airchange_per_hour_upper_limit: float = None
        self.glazing_layers_lower_limit: float = None
        self.glazing_layers_upper_limit: float = None

        # Manually load in the enumeration definitions
        self.glass_type = self.WindowGlassType[attributes["glass_type"]]
        self.window_frame_type  = self.WindowFrameType[attributes["window_frame_type"]]
        self.glazing_treatment = self.WindowGlazingTreatment[attributes["glazing_treatment"]]

        # Internally calculated attributes
        # These are updated throughout the simulation
        self.interior_air_heat_capacity: float = 0
        self.ceiling_area: float = 0
        self.gross_exterior_wall_area: float = 0
        self.gross_window_area: float = 0
        self.net_wall_area: float = 0
        self.floor_area: float = 0
        self.total_door_are: float = 0
        self.perimeter: float = 0
        self.etp_structure_params = self.ETPStructureParams()
        self.single_door_area: float = 0
        self.solar_heatgain_factor: float = 0
        self.Rg: float = 0
        init_class_attributes(self, attributes)

        # Initialization of model
        # All of these should only need to be calculated once as they 
        # represent physical parameters of the strucuture that we don't
        # expect to change in time.
        self.validate_attributes()
        self.calc_structure_areas()
        self.lookup_Rwindow()
        self.lookup_window_transmission_coefficient()
        self.calc_structure_ETP_parameters()
        
    class ETPStructureParams:
        """Data class for holding the ETP model structure parameters.

        Makes it easier to pass it around since they will always be used as a 
        unit.
        """
        def __init__(self):
            self.UA: float = 0
            self.CA: float  = 0
            self.HM: float  = 0
            self.CM: float  = 0
    @dataclass(frozen=True)
    class WindowFrameType(Enum):
        UNDEFINED = None
        NONE = 0
        ALUMINUM = 1
        THERMAL_BREAK = 2
        WOOD = 3
        INSULATED = 4

    @dataclass(frozen=True)
    class WindowGlazingTreatment(Enum):
        UNDEFINED = None
        CLEAR = 1
        ABS = 2
        REFLECTIVE = 3

    @dataclass(frozen=True)
    class WindowGlassType(Enum):
        UNDEFINED = None
        OTHER = 0
        NORMAL = 1
        LOW_E = 2

    def validate_attributes(self) -> None:
        """Evaluate values in attribute dictionary and correct as possible
        """
        if self.aspect_ratio == 0.0:
            self.aspect_ratio = 1.5
        if self.exterior_ceiling_fraction == 0.0:
            self.exterior_ceiling_fraction = 1
        if self.exterior_floor_fraction == 0.0:
            self.exterior_floor_fraction = 1
        if self.exterior_wall_fraction == 0.0:
            self.exterior_wall_fraction
        if self.window_exterior_transmission_coefficient <= 0.0:
            self.window_exterior_transmission_coefficient = 0.6
        # TODO update to raising exceptions
        if self.sqft <= 0:
            logger.debug('{} {} -- number of sqft ({}) is non-positive'
                    .format(self.name, 'init', self.sqft))
        if self.stories <= 0:
            logger.debug('{} {} -- number of stories ({}) is non-positive'
                    .format(self.name, 'init', self.stories))
        if self.doors < 0:
            logger.debug('{} {} -- number of doors ({}) is negative'
                                .format(self.name, 'init', self.doors))
        if self.Rroof_lower_limit > self.Rroof >= self.Rroof_upper_limit:
            logger.debug('{} {} --  Rroof is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rroof, self.Rroof_lower_limit, self.Rroof_upper_limit))
        if self.Rwall_lower_limit > self.Rwall >= self.Rwall_upper_limit:
            logger.debug('{} {} -- Rwall is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rwall, self.Rwall_lower_limit, self.Rwall_upper_limit))
        if self.Rfloor_lower_limit > self.Rfloor >= self.Rfloor_upper_limit:
            logger.debug('{} {} -- Rfloor is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rfloor, self.Rfloor_lower_limit, self.Rfloor_upper_limit))
        if self.Rdoor_lower_limit > self.Rdoors >= self.Rdoor_upper_limit:
            logger.debug('{} {} -- Rdoors is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.Rdoors, self.Rdoor_lower_limit, self.Rdoor_upper_limit))
        if self.glazing_layers_lower_limit > self.glazing_layers>= self.airchange_per_hour_upper_limit:
            logger.debug('{} {} -- airchange_per_hour is {}, outside of nominal range of {} to {}.'
                    .format(self.name, 'init', self.airchange_per_hour, 
                            self.airchange_per_hour_lower_limit, 
                            self.airchange_per_hour_upper_limit))
        
    def lookup_window_transmission_coefficient(self) -> float:
        """Calculates the window transmission coefficient for solar radiation
        based on the properties of the windows

        Returns:
            float: window tranmission coefficient
        """
        if self.glazing_layers == 1:
            if self.glazing_treatment == self.WindowGlazingTreatment.CLEAR:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.86
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.75
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.64
            elif self.glazing_treatment == self.WindowGlazingTreatment.ABS:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.73
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.64
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.54
            elif self.glazing_treatment == self.WindowGlazingTreatment.REFLECTIVE:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.31
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.28
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.24
        elif self.glazing_layers == 2:
            if self.glazing_treatment == self.WindowGlazingTreatment.CLEAR:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.76
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.67
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.57
            elif self.glazing_treatment == self.WindowGlazingTreatment.ABS:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.62
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.55
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.46
            elif self.glazing_treatment == self.WindowGlazingTreatment.REFLECTIVE:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.29
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.27
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.22
        elif self.glazing_layers == 3:
            if self.glazing_treatment == self.WindowGlazingTreatment.CLEAR:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.68
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.60
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.51
            elif self.glazing_treatment == self.WindowGlazingTreatment.ABS:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.34
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.31
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.26
            elif self.glazing_treatment == self.WindowGlazingTreatment.REFLECTIVE:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.window_transmission_coefficient = 0.34
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM or \
                    self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.window_transmission_coefficient = 0.31
                elif self.window_frame_type == self.WindowFrameType.WOOD or \
                    self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.window_transmission_coefficient = 0.26
        return self.window_transmission_coefficient

    def lookup_Rwindow(self) -> float:
        """Calculates the thermal resistance of the window based on the number
        of panes (glazing layers) and the window frame material

        Returns:
            float: thermal resistance of the structures windows
        """
        if self.glass_type == self.WindowGlassType.LOW_E:
            if self.glazing_layers == 1:
                print("error: no value for one pane of low-e glass")
            elif self.glazing_layers == 2:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.Rwindows = 1.0 / 0.30
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM:
                    self.Rwindows = 1.0 / 0.67
                elif self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.Rwindows = 1.0 / 0.47
                elif self.window_frame_type == self.WindowFrameType.WOOD:
                    self.Rwindows = 1.0 / 0.41
                elif self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.Rwindows = 1.0 / 0.33
            elif self.glazing_layers == 3:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.Rwindows = 1.0 / 0.27
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM:
                    self.Rwindows = 1.0 / 0.64
                elif self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.Rwindows = 1.0 / 0.43
                elif self.window_frame_type == self.WindowFrameType.WOOD:
                    self.Rwindows = 1.0 / 0.37
                elif self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.Rwindows = 1.0 / 0.31
        elif self.glass_type == self.WindowGlassType.NORMAL:
            if self.glazing_layers == 1:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.Rwindows = 1.0 / 1.04
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM:
                    self.Rwindows = 1.0 / 1.27
                elif self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.Rwindows = 1.0 / 1.08
                elif self.window_frame_type == self.WindowFrameType.WOOD:
                    self.Rwindows = 1.0 / 0.90
                elif self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.Rwindows = 1.0 / 0.81
            elif self.glazing_layers == 2:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.Rwindows = 1.0 / 0.48
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM:
                    self.Rwindows = 1.0 / 0.81
                elif self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.Rwindows = 1.0 / 0.60
                elif self.window_frame_type == self.WindowFrameType.WOOD:
                    self.Rwindows = 1.0 / 0.53
                elif self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.Rwindows = 1.0 / 0.44
            elif self.glazing_layers == 3:
                if self.window_frame_type == self.WindowFrameType.NONE:
                    self.Rwindows = 1.0 / 0.31
                elif self.window_frame_type == self.WindowFrameType.ALUMINUM:
                    self.Rwindows = 1.0 / 0.67
                elif self.window_frame_type == self.WindowFrameType.THERMAL_BREAK:
                    self.Rwindows = 1.0 / 0.46
                elif self.window_frame_type == self.WindowFrameType.WOOD:
                    self.Rwindows = 1.0 / 0.40
                elif self.window_frame_type == self.WindowFrameType.INSULATED:
                    self.Rwindows = 1.0 / 0.34
        elif self.glass_type == self.WindowGlassType.OTHER:
            self.Rwindows = 2.0

        return self.Rwindows

    def calc_structure_areas(self) -> None:
        """Calculates various areas of the structure based on object
        parameter values.

        Generally, this only needs to be done once when the structure
        model is initialized. 
        """
        self.ceiling_area = (self.sqft / self.stories) * self.exterior_ceiling_fraction
        self.floor_area = (self.sqft / self.stories) * self.exterior_floor_fraction
        self.perimeter = 2 * (1 + self.aspect_ratio) * math.sqrt(self.ceiling_area/self.aspect_ratio)
        self.gross_exterior_wall_area = self.stories * self.ceiling_height * self.perimeter
        self.gross_window_area = self.window_wall_ratio * self.gross_exterior_wall_area * self.exterior_wall_fraction
        self.total_door_area = self.doors * self.single_door_area
        self.net_wall_area = (self.gross_exterior_wall_area - self.gross_window_area - self.total_door_area) \
                                * self.exterior_wall_fraction
        self.interior_air_heat_capacity = self.sqft * self.ceiling_height * self.gross_air_heat_capacity

    def calc_solar_heatgain_factor(self) -> float:
        """Calculates the solar heatgain factor

        Solar heatgain factor indicates how much of the incident solar
        radiation makes it directly into the inside air.

        Returns:
            float: solar heatgain factor
        """
        self.solar_heatgain_factor = self.gross_window_area * self.window_transmission_coefficient * self.window_exterior_transmission_coefficient
        return self.solar_heatgain_factor
    
    def div(self, numerator: float, denominator: float, def_val_if_zero_denom: float=0) -> float:
        """Division operator designed to gracefully handle potential division-
        by-zero problems.

        This exists to handle cases when some of the thermal resistance values
        in the model have not been defined.

        Args:
            numerator (float): Numerator of division operation
            denominator (float): Denominator of division operation
            def_val_if_zero_denom (float, optional): Standard division
            operation allowing for a custom value when the denominator is zero;
                defaults response in that case is zero.

        Returns:
            float: result of the division operation or specified value if
                denominator was zero.
        """
        return numerator / denominator if denominator != 0 else def_val_if_zero_denom

    def calc_UA(self) -> float:
        """Calculates the UA (total thermal conductance) of the specified
        structure, in Btu/degF*h.

        Returns:
            float: UA of structure
        """

        self.etp_structure_params.UA = \
            self.div(self.ceiling_area, self.Rroof) \
            + self.div(self.floor_area, self.Rfloor) \
            + self.div(self.net_wall_area, self.Rwall) \
            + self.div(self.gross_window_area, self.Rwindows) \
            + self.div(self.total_door_area, self.Rdoors)
        return self.etp_structure_params.UA
        
    def calc_CA(self) -> float:
        """Calculation of indoor air heat capacity, or air thermal mass, in Btu/F
        
        Note that the *3 multiplier is to reflect that the air mass includes
        surface effects from the mass as well

        Returns:
            float: Thermal capacity of indoor air
        """
        self.etp_structure_params.CA = 3 * self.interior_air_heat_capacity
        return self.etp_structure_params.CA

    def calc_HM(self) -> float:
        """Calculation of thermal resistivity between the indoor air and the
        structure mass. Short-form variable assignments employed for human-
        readability.

        Returns:
            float: thermal resistivity between the indoor air and the structure
                mass.
        """
        h_i = self.interior_heat_transfer_coefficient 
        A_net = self.net_wall_area
        wall_f = self.exterior_wall_fraction
        A_gross = self.gross_exterior_wall_area
        wall_r = self.interior_exterior_wall_ratio
        A_ceil = self.ceiling_area
        stories = self.stories
        ceil_f = self.exterior_ceiling_fraction

        self.etp_structure_params.HM = \
            h_i * ((A_net / wall_f) + (A_gross * wall_r) + A_ceil * (stories / ceil_f))
        
        return self.etp_structure_params.HM

    def calc_CM(self) -> float:
        """Calculation of structural mass thermal capacity

        Returns:
            float: Thermal capacity of structural mass
        """
        self.etp_structure_params.CM = \
            self.sqft * self.thermal_mass_per_floor_area - 2 * self.interior_air_heat_capacity
        return self.etp_structure_params.CM

    def calc_structure_ETP_parameters(self) -> 'HVACDSOTStructureModel.ETPStructureParams':
        """Calcuate the structural ETP parameters

        As the fine ASCII art below shows, several of the ETP model parameters
        are purely a function of the structure, specifically UA, CA, HM and
        CM. These values are generally fixed and don't need to be updated 
        throughout the simulation run. Qa and Qm are a function of the 
        environment and will generally change throughout the run. Solving the
        entire ETP model is not handled here. 

            heat flows into   heat flows into
            indoor air          structure mass
                    Qa                Qm
                    |                |
                    |  thermal       |         
                    |  resistance    |
        thermal        |  between       |
        resistance     |  indoor        |
        between        |  air and       |
        indoor and     |  structure     |      
        outdoor air    |  mass          | 
            UA         |      CA        |
        To /\/\/\/\/\/ Ta \/\/\/\/\/\/\ Tm structure
        outside air    | indoor air     |   temperature
        temperature    | temperature    |
                    |                |
                    ======= HM       ======= CM  
                air heat          structure     
                capacitance      heat capacitance                             

        
        Returns:       
            ETPStructureParams: Data object for holding the ETP structure
                parameters
        """
        self.calc_UA()
        self.calc_CA()
        self.calc_HM()
        self.calc_CM()
        return (self.etp_structure_params)
    
@dataclass(frozen=True)
class ThermostatMode(Enum):
    UNDEFINED = None
    OFF = 0
    COOLING = 1
    HEATING = 2
class HVACDSOTAssetModel:
    def __init__(self, attributes: dict, agent: HVACDSOTAgent):
        """TODO

        Args:
            attributes (dict): Dictionary of attributes, externally defined. 
                These are generally fixed throughout the simulation.
        """
        
        self.agent = agent
        self.etp_params = self.agent.structure_model.ETPStructureParams()
        self.heating_system_type = HVACDSOTAssetModel.HeatingSystemType()
        self.cooling_system_type = HVACDSOTAssetModel.CoolingSystemType()
        self.env_model = HVACDSOTAssetModel.HVACDSOTEnvironmentModel()
        self.A_ETP: np.ndarray = np.zeros([2, 2])
        self.B_ETP_ON: np.ndarray = np.zeros([2, 1])
        self.B_ETP_OFF: np.ndarray = np.zeros([2, 1])
        self.AEI: np.ndarray = np.zeros([2, 2])

        self.CA = self.etp_params.CA
        self.UA = self.etp_params.UA
        self.CM = self.etp_params.CM
        self.HM = self.etp_params.HM
        self.Qa_On = self.agent.env_model.Qa_ON
        self.Qa_Off = self.agent.env_model.Qa_OFF
        self.Qm = self.agent.env_model.Qm

        HVACDSOTSystemModel.calc_design_capacities(self.etp_params,
                                                    self.heating_system_type,
                                                    self.env_model,
                                                    self.agent.structure_model)

    def calc_AEI(self, env_model: 'HVACDSOTAssetModel.HVACDSOTEnvironmentModel' = None):
        if env_model == None:
            env_model = env_model
        if self.CA != 0.0:
            self.A_ETP[0][0] = -1.0 * (self.UA + self.HM) / self.CA
            self.A_ETP[0][1] = self.HM / self.CA # 
            self.B_ETP_ON[0] = (self.UA * env_model.outside_air_temperature / self.CA) + (self.Qa_On / self.CA)
            self.B_ETP_OFF[0] = (self.UA * env_model.outside_air_temperature / self.CA) + (self.Qa_Off / self.CA)
        if self.CM != 0.0:
            self.A_ETP[1][0] = self.HM / self.CM
            self.A_ETP[1][1] = -1.0 * self.HM / self.CM
            self.B_ETP_ON[1] = self.Qm / self.CM
            self.B_ETP_OFF[1] = self.Qm / self.CM
        self.AEI = np.linalg.inv(self.A_ETP)
        return self.AEI
        
    def simulate_time_step(self, env_model: 'HVACDSOTAssetModel.HVACDSOTEnvironmentModel', 
                           time_step_size: dt.timedelta) -> tuple:
        """Given an asset and environment state, simulates the HVAC system 
        for the duration of a time_step_size.

        Generally, it is expected that the asset state and environment model
        passed in here will be copies of other objects that can be altered
        over the run of the simulation (say, for example, in evaluating the
        state of the system to form a bid). In the DSOT analysis, the actual
        system was evolved in the GridLAB-D model and this model of the HVAC
        system was used as part of the controller in a model-based-control
        manner.

        Note, just in like GridLAB-D, the model simulates one future state
        from the current state. If you take a time step size of, say, one
        day and start with the HVAC system off, the indoor air temperature 
        will change dramatically as no intermediate states have been
        calculated that would allow the HVAC to change state. Evolving the
        system with finer time steps will produce more accurate results at the
        cost of greater computation time. Consider the trade-off between
        fidelity and computation time when choosing the time step size.

        Args:
            env_model (HVACDSOTEnvironmentModel): defined environmental state of
                the object (including heat flows) based on the results of the 
                simulated system
            time_step_size (dt.timedelta): time from the model's current 
                state to evolve the simulated system.

        Returns:
            tuple: asset state and environment state objects. If attempting
                to simulate multiple time steps in a row these objects become 
                the inputs on subsequent calls to this method.
        """
    
        state_vars = np.zeros([2, 1])
        state_vars[0] = self.agent.asset_state.indoor_air_temp
        state_vars[1] = self.agent.asset_state.mass_temp
        Q_max = self.agent.asset_state.hvac_kW #TODO:unused
        Q_min = 0.0 #TODO:unused
        time_step_s = time_step_size.total_seconds()

        # TODO understand why the time_step_s is T/10 in original code
        eAET = linalg.expm(self.A_ETP * time_step_s)
        AIET = np.dot(self.AEI, eAET) #TODO: DO we want AIET and AIB to be constants?
        AEx = np.dot(self.A_ETP, state_vars)
        if self.agent.asset_state.hvac_on == True:
            AxB = AEx + self.B_ETP_ON
            AIB = np.dot(self.AEI, self.B_ETP_ON)
            AExB = np.dot(AIET, AxB)
            state_vars = AExB - AIB 
            if (((state_vars[0][0] < self.agent.temp.cooling_setpoint - self.agent.temp.deadband / 2.0)
                    and self.agent.thermostat_mode == ThermostatMode.COOLING) 
                or
                ((state_vars[0][0] > self.agent.temp.heating_setpoint + self.agent.temp.deadband / 2.0) 
                    and self.agent.thermostat_mode == ThermostatMode.HEATING)):
                self.agent.asset_state.hvac_on = False 
            # TODO: Do we need an else?
        else:
            AxB = AEx + self.B_ETP_OFF
            AIB = np.dot(self.AEI, self.B_ETP_OFF)
            AExB = np.dot(AIET, AxB)
            state_vars = AExB - AIB 
            if (((state_vars[0][0] > self.agent.temp.cooling_setpoint + self.agent.temp.deadband / 2.0)
                    and self.agent.thermostat_mode == ThermostatMode.COOLING) 
                or
                ((state_vars[0][0] < self.agent.temp.heating_setpoint - self.agent.temp.deadband / 2.0) 
                    and self.agent.thermostat_mode == ThermostatMode.HEATING)):
                self.agent.asset_state.hvac_on = True
            # TODO: Do we need an else?
        # Update the state varibles after solving the above linear system so
        # that the returned state object has the results of this simulated 
        # time step and can be used for any subsequent time steps.
        self.agent.asset_state.indoor_air_temp = state_vars[0]     
        self.agent.asset_state.mass_temp = state_vars[1]
        return self.agent.asset_state, env_model, self.agent.temp
    
    @dataclass(frozen=True)
    class HeatingSystemType(Enum):
        UNDEFINED = None
        NONE = 0
        GAS = 1
        ELECTRIC = 2
        HEAT_PUMP = 3

    @dataclass(frozen=True)
    class CoolingSystemType(Enum):
        UNDEFINED = None
        NONE = 0
        ELECTRIC = 1

    class HVACDSOTEnvironmentModel:
        """
        Tracks environmental parameter values necessary for simulating the HVAC +
        thermostat + structure system. Calculates the heat flows between modeled
        elements. 
        
        Part of maintaining the environment model is calculating the heat flows.
        The fine ASCII art below shows the dependencies between the calculated
        heat flows. If, say, a call is made to calculate a new value of Qm, 
        calls will be made to recalculate Qs and Qi. 


        Qs---------------------------------->Qa   
                        |                    ^^
                        v                    ||
                    Qm                    ||
                        ^                   Qh|
                        |                     |
        Qh_org----->Qi------------------------|     



        This introduces the possibility of the same foundational heat flows 
        (_e.g._ Qs) being calculated multiple times when trying to update a single
        value. There are two work-arounds to avoid this:

        1. There's an `update_all_heat_flows()` that calculates all the heat
        flows ensuring there's no redundant calculations.
        2. Any of the methods used to update a heat flow dependent on another
        heat flow have optional arguments to accept previously cacluated values 
        of those flows. If a value is passed in, it is used instead of 
        recalculating. If no value is passed it, the dependent heat flow is 
        recalculated.

        """
        def __init__(self, attributes: dict, agent: HVACDSOTAgent, source_obj: object = None, ):
            """Sets attributes for object

            Args:
                name (str): object name
                attributes (dict): attributes dictionary, externally defined. 
                    These are generally fixed throughout the simulation.
                source_obj (obj): TODO
            """
            self.agent = agent
            self.name: str = None
            self.surface_angles: list = None
            self.mass_internal_gain_fraction: float = None
            self.mass_solar_gain_fraction: float = None
            self.lat: float = None
            self.long: float = None
            
            # Internally calculated attributes. 
            # These are updated throughout the simulation
            self.humidity: float = 0
            self.latent_load_fraction: float = 0
            self.outside_air_temperature: float = 0
            self.solar_direct: float = 0
            self.solar_diffuse: float = 0
            self.solar_gain: float = 0
            self.temperature_forecast: list = []
            self.humidity_forecast = []
            self.internal_gain_forecast = []
            self.solar_gain_forecast = []
            self.Qi: float = 0
            self.Qh: float = 0
            self.Qh_org: float = 0
            self.Qa_ON: float = 0
            self.Qa_OFF: float = 0
            self.Qm: float = 0
            self.Qs: float = 0
            init_class_attributes(self, attributes)
            self.structure_model: HVACDSOTStructureModel = None
            if source_obj is not None:
                self.copy_attributes_from(source_obj)

        def copy_attributes_from(self, other_obj: object):
            """Takes attributes from one object and copies the values into the
            attributes of another objects of the same type.

            Allows the quick creation of a new object in the same state as another
            object.

            Args:
                other_obj (HVACDSOTAgent): Object whose attributes are the source
                    of the data being copied into the target object's attributes.
            """
            if isinstance(other_obj, HVACDSOTAssetModel.HVACDSOTEnvironmentModel):
                self.__dict__.update(other_obj.__dict__)
        
        def calc_Qh(self, 
                    hvac_on: bool,
                    heating_capacity: float,
                    cooling_capacity: float,
                    hvac_kW: float) -> tuple:
            """Calculates Qh, the heat flow into the indoor air due to HVAC
            operation.

            Args:
                thermostat_mode (ThermostatMode): Indicates thermostat mode; from
                    HVACDSOTAssetstate
                hvac_on (bool): Indicates current state of HVAC; from 
                    HVACDSOTAssetstate
                heating_capacity (float): Heating capacity from 
                    HVACDSOTSystemModel
                cooling_capacity (float): Cooling capacity from 
                    HVACDSOTSystemModel
                hvac_kW (float): Indicates current real power consumption of HVAC;
                    from HVACDSOTAssetstate

            Returns:
                tuple: Qh and Qh_org TODO: what is Qh_org?
            """
        
            if self.agent.thermostat_mode == ThermostatMode.HEATING:
                self.Qh = heating_capacity + 0.02 * heating_capacity
                self.Qh_org = hvac_kW
            elif self.agent.thermostat_mode == ThermostatMode.COOLING:
                # Short-form variable assignments employed for human-readability.
                cool = cooling_capacity
                load_f = self.latent_load_fraction
                hum = self.humidity
                self.Qh = \
                    -cool / (1.01 + load_f / (1 + math.exp(4 - 10 * hum))) + cool * 0.02
                self.Qh_org = -hvac_kW
            else:
                self.Qh = 0
                self.Qh_org = 0
            if not hvac_on:
                self.Qh_org = 0
            return self.Qh, self.Qh_org

        def calc_Qi(self, 
                    house_kW: float,
                    wh_kW: float,
                    thermostat_mode: ThermostatMode,
                    hvac_on: bool,
                    heating_capacity: float,
                    cooling_capacity: float,
                    hvac_kW: float,
                    Qh_org: float = None) -> float:
            """Calculates Qi, the heat flow into indoor residential air due to 
            other electrical energy consumpation (e.g. appliances).

            Args:
                house_kW (float): Current total house real power load (TODO?) as
                    simulated in GridLAB-D
                wh_kW (float): Current real power consumption of the water heater as
                    simulated in GridLAB-D
                thermostat_mode (ThermostatMode): Indicates thermostat mode; from
                    HVACDSOTAssetstate
                hvac_on (bool): Indicates current state of HVAC; from 
                    HVACDSOTAssetstate
                heating_capacity (float): Heating capacity from 
                    HVACDSOTSystemModel
                cooling_capacity (float): Cooling capacity from 
                    HVACDSOTSystemModel
                hvac_kW (float): Indicates current real power consumption of HVAC;
                    from HVACDSOTAssetstate
                Qh_org (float): TODO

            Returns:
                float: Qi
            """
            if Qh_org == None:
                self.calc_Qh(thermostat_mode, hvac_on, heating_capacity, cooling_capacity, hvac_kW)
            else:
                self.Qh_org = Qh_org
            self.Qi = (house_kW - abs(self.Qh_org) - wh_kW) * KW_TO_BTU_PER_HR
            if self.Qi <= 0.0:
                self.Qi = 0.0
            return self.Qi
        
        def calc_Qs(self, solar_heatgain_factor: float, solar_gain: float) -> float:
            """Calculates heat flows into the structure mass due to solar 
            radiation

            Args:
                solar_heatgain_factor (float): Portion of solar radiation that
                    heats the structure mass
                solar_gain (float): Energy from solar radiation

            Returns:
                float: Qs
            """
            self.Qs = solar_gain * solar_heatgain_factor
            return self.Qs

        def calc_Qa(self,
                    house_kW: float,
                    wh_kW: float,
                    thermostat_mode: ThermostatMode,
                    hvac_on: bool,
                    heating_capacity: float,
                    cooling_capacity: float,
                    hvac_kW: float,
                    Qs: float = None,
                    Qi: float = None,
                    Qh: float = None,
                    Qh_org: float = None) -> tuple:
            """Calculates the heat flows into the indoor air.

            Two values are returned: one representing the heat flows if the HVAC
            system is running and one if it is not. These values are used to allow
            later estimations of the whole system (HVAC + thermostat + structure)
            for arbitrary points of time in the future. So rather than just using 
            the acutal current state of the HVAC system, we calculate two values 
            and use whichever one is applicable in the future state we're modeling.

            Args:
                house_kW (float): Current total house real power load (TODO?) as
                    simulated in GridLAB-D
                wh_kW (float): Current real power consumption of the water heater as
                    simulated in GridLAB-D
                thermostat_mode (ThermostatMode): Indicates thermostat mode; from
                    HVACDSOTAssetstate
                hvac_on (bool): Indicates current state of HVAC; from 
                    HVACDSOTAssetstate
                heating_capacity (float): Heating capacity from 
                    HVACDSOTSystemModel
                cooling_capacity (float): Cooling capacity from 
                    HVACDSOTSystemModel
                hvac_kW (float): Indicates current real power consumption of HVAC;
                    from HVACDSOTAssetstate
                Qs (float): (optional) Heat flows from solar radiation. If 
                    previously calculated, it can be passed in. Otherwise, it will
                    be calculated for use in this method.
                Qi (float): (optional) Heat flows into the indoor air. If 
                    previously calculated, it can be passed in. Otherwise, it will
                    be calculated for use in this method.
                Qh (float): (optional) Heat flows into the indoor air due to HVAC
                    operation. If previously calculated, it can be passed in. 
                    Otherwise, it will be calculated for use in this method.
                Qh_org (float): TODO - this is the same as Qh. What is Qh_org?
                    (optional) Heat flows into the indoor air due to HVAC operation. 
                    If previously calculated, it can be passed in. Otherwise, it 
                    will be calculated for use in this method.

            Returns:
                tuple: Qa_OFF, Qa_ON
            """
            if Qi == None:
                self.calc_Qi(house_kW,
                            wh_kW,
                            thermostat_mode,
                            hvac_on,
                            heating_capacity,
                            cooling_capacity,
                            hvac_kW)
            else:
                self.Qi = Qi
            if Qs == None:
                self.calc_Qs()
            else:
                self.Qs = Qs
            if Qh == None or Qh_org == None:
                self.calc_Qh(thermostat_mode,
                                hvac_on,
                                heating_capacity,
                                cooling_capacity,
                                hvac_kW)
            else:
                self.Qh = Qh
                self.Qh_org = Qh_org
            self.Qa_OFF = ((1 - self.mass_internal_gain_fraction) * self.Qi) \
                + ((1 - self.mass_solar_gain_fraction) * self.Qs)
            self.Qa_ON = self.Qh + ((1 - self.mass_internal_gain_fraction) * self.Qi) \
                    + ((1 - self.mass_solar_gain_fraction) * self.Qs)
            return self.Qa_OFF, self.Qa_ON

        def calc_Qm(self,
                    house_kW: float,
                    wh_kW: float,
                    thermostat_mode: ThermostatMode,
                    hvac_on: bool,
                    heating_capacity: float,
                    cooling_capacity: float,
                    hvac_kW: float,
                    Qs: float = None,
                    Qi: float = None) -> tuple:
            """Calculates the heat flows into the structural mass.

            Args:
                house_kW (float): Current total house real power load (TODO?) as
                    simulated in GridLAB-D
                wh_kW (float): Current real power consumption of the water heater as
                    simulated in GridLAB-D
                thermostat_mode (ThermostatMode): Indicates thermostat mode; from
                    HVACDSOTAssetstate
                hvac_on (bool): Indicates current state of HVAC; from 
                    HVACDSOTAssetstate
                heating_capacity (float): Heating capacity from 
                    HVACDSOTSystemModel
                cooling_capacity (float): Cooling capacity from 
                    HVACDSOTSystemModel
                hvac_kW (float): Indicates current real power consumption of HVAC;
                    from HVACDSOTAssetstate
                Qs (float): (optional) Heat flows from solar radiation. If 
                    previously calculated, it can be passed in. Otherwise, it will
                    be calculated for use in this method.
                Qi (float): (optional) Heat flows into the indoor air. If 
                    previously calculated, it can be passed in. Otherwise, it will
                    be calculated for use in this method.

            Returns:
                float: Qm
            """
            if Qi == None:
                self.calc_Qi(house_kW,
                            wh_kW,
                            thermostat_mode,
                            hvac_on,
                            heating_capacity,
                            cooling_capacity,
                            hvac_kW)
            else:
                self.Qi = Qi
            if Qs == None:
                self.calc_Qs()
            else:
                self.Qs = Qs
            self.Qm = (self.mass_internal_gain_fraction * self.Qi) + (self.mass_solar_gain_fraction * self.Qs)

        def calc_all_heat_flows(self,
                    house_kW: float,
                    wh_kW: float,
                    thermostat_mode: ThermostatMode,
                    hvac_on: bool,
                    heating_capacity: float,
                    cooling_capacity: float,
                    hvac_kW: float) -> tuple:
            """Calculates all heat flows in the correct order such that no 
            duplicate calculations take place.

            Args:
                house_kW (float): Current total house real power load (TODO?) as
                    simulated in GridLAB-D
                wh_kW (float): Current real power consumption of the water heater as
                    simulated in GridLAB-D
                thermostat_mode (ThermostatMode): Indicates thermostat mode; from
                    HVACDSOTAssetstate
                hvac_on (bool): Indicates current state of HVAC; from 
                    HVACDSOTAssetstate
                heating_capacity (float): Heating capacity from 
                    HVACDSOTSystemModel
                cooling_capacity (float): Cooling capacity from 
                    HVACDSOTSystemModel
                hvac_kW (float): Indicates current real power consumption of HVAC;
                    from HVACDSOTAssetstate

            Returns:
                tuple: All heat flows (Qi, Qs, Qh, Qh_org, Qm)
            """
    
            self.calc_Qs(self.structure_model.solar_heatgain_factor, self.solar_gain)
            self.calc_Qh(thermostat_mode, 
                        hvac_on, 
                        heating_capacity, 
                        cooling_capacity, 
                        hvac_kW)
            self.calc_Qi(house_kW,
                        wh_kW,
                        thermostat_mode,
                        hvac_on,
                        heating_capacity,
                        cooling_capacity,
                        hvac_kW,
                        Qh_org=self.Qh_org)
            self.calc_Qm(house_kW,
                        wh_kW,
                        thermostat_mode,
                        hvac_on,
                        heating_capacity,
                        cooling_capacity,
                        hvac_kW,
                        Qs = self.Qs,
                        Qi = self.Qi)
            self.calc_Qa(house_kW,
                        wh_kW,
                        thermostat_mode,
                        hvac_on,
                        heating_capacity,
                        cooling_capacity,
                        hvac_kW,
                        Qs = self.Qs,
                        Qi = self.Qi,
                        Qh = self.Qh,
                        Qh_org = self.Qh_org)
            return self.Qi, self. Qs, self.Qh, self.Qh_org, self.Qm

        def calc_solar_flux(self, 
                            cpt: str, 
                            day_of_yr: int, 
                            lat: float, 
                            sol_time: float, 
                            dnr_i: float, 
                            dhr_i: float, 
                            vertical_angle: float) -> float:
            """Calculates solar flux based on passed-in, time, location, and
            orientation.

            This implements similar functionality in GridLAB-D

            Args:
                cpt (str): Orientation as compass direction
                day_of_yr (int): Ordinal day of the year
                lat (float): Latitude where solar flux is being calculated
                sol_time (float): Solar time
                dnr_i (float): Solar direct normal radiance
                dhr_i (float): Solar diffuse horizontal radiance
                vertical_angle (float): Angle of plane absorbing the solar radiation
                
            Returns:
                float: Total solar flux
            """
                                    
            az = math.radians(self.surface_angles[cpt])
            if cpt == 'H':
                az = math.radians(self.surface_angles['E'])
            hr_ang = -(15.0 * math.pi / 180) * (sol_time - 12.0)
            decl = 0.409280 * sin(2.0 * math.pi * (284 + day_of_yr) / 365)
            slope = vertical_angle
            cos_incident = (sin(decl) * sin(lat) * cos(slope) -
                            sin(decl) * cos(lat) * sin(slope) * cos(az) +
                            cos(decl) * cos(lat) * cos(slope) * cos(hr_ang) +
                            cos(decl) * sin(lat) * sin(slope) * cos(az) * cos(hr_ang) +
                            cos(decl) * sin(slope) * sin(az) * sin(hr_ang))
            if cos_incident < 0:
                cos_incident = 0
            return dnr_i * cos_incident + dhr_i
        
        def calc_solargain(self, sim_time: dt.datetime,
                        solar_direct: float = None,
                        solar_diffuse: float = None) -> float:
            """TODO
                sim_time (dt.datetime): Current simulation time

            Returns:
                float: solar_gain
            """
            if solar_direct == None:
                solar_direct = self.solar_direct
            if solar_diffuse == None:
                solar_diffuse = self.solar_diffuse

            self.solar_gain = 0
            day_of_yr = sim_time.timetuple().tm_yday
            rad = (2.0 * math.pi * day_of_yr) / 365.0
            eq_time = (0.5501 * cos(rad)
                        - 3.0195 * cos(2 * rad)
                        - 0.0771 * cos(3 * rad)
                        - 7.3403 * sin(rad)
                        - 9.4583 * sin(2 * rad)
                        - 0.3284 * sin(3 * rad)) / 60.0
            tz_meridian = 15 * sim_time.utcoffset()
            # tz_meridian = 15 * tz_offset - old method that I'm not sure I fully understand
            std_meridian = tz_meridian * math.pi / 180
            sol_time = sim_time.hour() + eq_time + 12.0 / math.pi * (self.long - std_meridian)
            solar_flux = []
            for cpt in self.surface_angles.keys():
                vertical_angle = math.radians(90)
                if cpt == 'H':
                    vertical_angle = math.radians(0)
                solar_flux.append(self.calc_solar_flux(cpt, 
                                                    day_of_yr, 
                                                    self.lat, 
                                                    sol_time, 
                                                    self.solar_direct, 
                                                    self.solar_diffuse, 
                                                    vertical_angle))
            avg_solar_flux = sum(solar_flux[1:9]) / 8
            self.solar_gain = avg_solar_flux * 3.412  # incident_solar_radiation is now in Btu/(h*sf)
            return self.solar_gain
class HVACDSOTSystemModel:
    """Calculates and updates the perfomance of the HVAC system in response to
    the changing thermal environment.
    """
    def __init__(self, attributes: dict, agent: HVACDSOTAgent):
        """Sets attributes for object

        Args:
            name (str): object name
            attributes (dict): attributes dictionary, externally defined. These
                are generally fixed throughout the simulation.
        """
        self.agent = agent
        self.name: str = None
        self.heating_capacity_K0: float = None
        self.heating_capacity_K1: float = None
        self.heating_capacity_K2: float = None
        self.design_cooling_capacity: float = None
        self.cooling_capacity_K0: float = None
        self.cooling_capacity_K1: float = None
        self.heating_COP: float = None
        self.heating_COP_limit: float = None
        self.heating_COP_K0: float = None
        self.heating_COP_K1: float = None
        self.heating_COP_K2: float = None
        self.heating_COP_K3: float = None
        self.cooling_COP: float = None
        self.cooling_COP_limit: float = None
        self.cooling_COP_K0: float = None
        self.cooling_COP_K1: float = None
        self.over_sizing_factor: float = None
        self.cooling_design_temperature: float = None
        self.design_cooling_setpoint: float = None
        self.design_heating_setpoint: float = None
        self.heating_design_temperature: float = None
        self.design_internal_gains: float = None
        self.design_peak_solar: float = None
        self.cooling_COP_lower_limit: float = None
        self.cooling_COP_upper_limit: float = None
        self.model_diag_level: int = None
        init_class_attributes(self, attributes)

        # Internally calculated attributes. These are updated throughout the simulation
        self.heating_cop_adj_da = []
        self.cooling_cop_adj_da = []
        self.heating_capacity: float = None
        self.design_heating_capacity: float = None
        self.design_cooling_capacity: float = None

        self.validate_attributes()
        
    def validate_attributes(self) -> None:
        if self.cooling_COP_lower_limit > self.cooling_COP >= self.cooling_COP_upper_limit:
            logger.debug('{} {} -- cooling_COP is {}, outside of nominal range of {} to {}'
                    .format(self.name, 'init', self.cooling_COP, 
                            self.cooling_COP_lower_limit, 
                            self.cooling_COP_upper_limit))

    def calc_heating_capacity(self) -> float:
        """Calculates the true heating capacity of the HVAC system based on
        the design capacity, correction coefficients, and the outside air
        temperature.

        For DSOT this is only used in the real-time market and thus uses the
        current outside air temperture as a parameter. 

        TODO: Should this be updated to support working with a list of 
        temp? That is, I don't know why it isn't being used for 
        estimating loads in the day-ahead market.

        Returns:
            float: temperature-corrected heating capacity
        """
        # Short-form variable assignments employed for human-readability.
        h_d = self.design_heating_capacity
        h_KO = self.heating_capacity_K0
        h_K1 = self.heating_capacity_K1
        air_temp = self.agent.env_model.outside_air_temperature
        h_K2 = self.heating_capacity_K2

        self.heating_capacity = \
            h_d * (h_KO + h_K1 * air_temp + h_K2 * air_temp ** 2)
        
        return self.heating_capacity
    
    def calc_cooling_capacity(self) -> float:
        """Calculates the true cooling capacity of the HVAC system based on
        the design capacity, correction coefficients, and the outside air
        temperature.

        For DSOT this is only used in the real-time market and thus uses the
        current outside air temperture as a parameter. 

        TODO: Should this be updated to support working with a list of 
        temp? That is, I don't know why it isn't being used for 
        estimating loads in the day-ahead market.

        Returns:
            float: temperature-corrected cooling capacity
        """
        # Short-form variable assignments employed for human-readability.
        c_d = self.design_cooling_capacity
        c_K0 = self.cooling_capacity_K0
        c_K1 = self.cooling_capacity_K1
        air_temp = self.agent.env_model.outside_air_temperature

        self.cooling_capacity = c_d * (c_K0 + c_K1 * air_temp)
        return self.cooling_capacity
    
    def calc_heating_COP(self) -> list:
        """Calculates the adjusted heating COP for use in the day-ahead market
        based on the temperature forecast and correction curve co-efficients.

        Returns:
            list: Adjusted heating COP values in a list the same length as the 
            temperature forecast used in calculating the values.
        """
        # Short-form variable assignments employed for human-readability.
        cop = self.heating_COP
        cop_K0 = self.heating_COP_K0
        cop_K1 = self.heating_COP_K1
        cop_limit = self.heating_COP_limit
        cop_K2 = self.heating_COP_K2
        cop_K3 = self.heating_COP_K3
        for idx, temperature in enumerate(self.agent.forecasts.outside_air_temperature):
            if temperature < self.heating_COP_limit:
                self.heating_cop_adj_da[idx] = \
                    cop / (cop_K0 + cop_K1 * cop_limit + 
                           cop_K2 * cop_limit ** 2 +
                           cop_K3 * cop_limit ** 3)
            else:
                self.heating_cop_adj_da[idx] = \
                    cop / (cop_K0 + cop_K1 * temperature +
                        cop_K2 * temperature ** 2 +
                        cop_K3 * temperature ** 3)
        return self.heating_cop_adj_da
    
    def calc_cooling_COP(self) -> list:
        """Calculates the adjusted cooling COP for use in the day-ahead market
        based on the temperature forecast and correction curve co-efficients.

        Returns:
            list: Adjusted cooling COP values in a list the same length as the 
                temperature forecast used in calculating the values.
        """
        for idx, temperature in enumerate(self.agent.forecasts.outside_air_temperature):
            if temperature < self.cooling_COP_limit:
                self.cooling_cop_adj_da[idx] = self.cooling_COP / (
                        self.cooling_COP_K0 + self.cooling_COP_K1 * self.cooling_COP_limit)
            else:
                self.cooling_cop_adj_da[idx] = self.cooling_COP / (
                        self.cooling_COP_K0 + self.cooling_COP_K1 * temperature)
        return self.cooling_cop_adj_da

    def calc_design_capacities(self) -> tuple:
        """Calculates the design cooling capacity

        Entirely a function of fixed attributes

        Args:
            etp_structure_params (ETPStructureParams): Structure parameters
                used in solving the ETP model

        Returns:
            tuple: design_cooling_capacity, design_heating_capacity
        """
        # Short-form variable assignments employed for human-readability.
        ovr_sz = self.over_sizing_factor
        load_f = self.agent.env_model.latent_load_fraction
        ua = self.agent.etp_structure_params.UA
        cool_temp = self.cooling_design_temperature
        cool_set = self.design_cooling_setpoint
        int_gain = self.design_internal_gains
        pk_sol = self.design_peak_solar
        heatgain = self.agent.structure_model.solar_heatgain_factor
        heat_set = self.design_heating_setpoint
        heat_temp = self.heating_design_temperature

        design_cooling_capacity = ((1.0 + ovr_sz) * (1.0 + load_f) *
                                   (ua * (cool_temp - cool_set)) 
                                   + int_gain + (pk_sol * heatgain))
        # Rounding design cooling capacity to the nearest multiple of 6000
        # TODO: figure out why 6000?
        self.design_cooling_capacity = math.ceil(design_cooling_capacity/6000) * 6000

        if self.agent.asset_model.heating_system_type == HVACDSOTAssetModel.HeatingSystemType.HEAT_PUMP:
            self.design_heating_capacity = design_cooling_capacity
        else:
            design_heating_capacity = ((1.0 + ovr_sz) * ua * (heat_set - heat_temp))
            self.design_heating_capacity = math.ceil(design_heating_capacity/10000.0) * 10000.0
        # TODO why 10,0000?
        return self.design_cooling_capacity, self.design_heating_capacity
        

class HVACDSOTPriceFlexibilityCurve:
    def __init__(self):
        """Class used to evaluate the 4-point bid and TODO
        """
        self.ProfitMargin_intercept: float
        self.ProfitMargin_slope: float
        self.price_cap: float 

    def get_flexible_price(self, 
                        quantity: float, 
                        DA_price_delta: float,
                        hvac_kW: float,
                        price_forecast: float) -> float:
        """TODO

        Args:
            quantity (float): _description_
            DA_price_delta (float): _description_
            hvac_kW (float): _description_
            price_forecast (float): _description_

        Returns:
            float: _description_
        """
        
        CurveSlope = (DA_price_delta / (0 - hvac_kW) * (1 + self.ProfitMargin_slope / 100))
        yIntercept = (price_forecast - CurveSlope * quantity) 
        return CurveSlope, yIntercept
    
class HVACDSOTBiddingStrategy:
    def __init__(self, attributes: dict):
        """Contains the bidding strategy for the HVAC agent.

        Args:
            attributes (dict): Externally defined attributes, generally fixed
                throughout the simulation. TODO - not initialized?
        """
        self.name: str = None
        self.price_cap: float = None
        self.bid_delay: float = None
        self.slider: float = None
        self.cooling_participating: bool = None
        self.heating_participating: bool = None
        self.windowLength_hr: int = None
        self.interpolation: bool = None
        self.ProfitMargin_intercept: float = None
        self.ProfitMargin_slope: float = None

        # Internally calculated simulation parameters or variables
        # Generally not-fixed throughout simulation
        self.bid = DSOT4pointBid()

class DSOT4pointBid:
    """Data structure to hold DSOT 4-point bid"""
    def __init__(self):
        self.cumulative_curve = []
        self.P: int = 1
        self.Q: int = 0
        self.points = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]

    def make_marginal_price_curve(self, price_direction: 'DSOT4pointBid.SortDirection') -> list:
        """TODO

        Returns:
            list: _description_
        """
        # Sort by quantity
        if price_direction == self.SortDirection.ASCENDING:
            sorted_points = sorted(self.points, key=lambda x: x[1], reverse=False)
        else:
            sorted_points = sorted(self.points, key=lambda x: x[1], reverse=True)
        cumulative = 0
        for point in sorted_points:
            cumulative += point[self.Q]
            self.cumulative_curve.append([cumulative, point[self.P]])
        return self.cumulative_curve

    @dataclass(frozen=True)
    class SortDirection(Enum):
        ASCENDING = 0
        DESCENDING = 1
        
class HVACDSOTDABiddingStrategy(HVACDSOTBiddingStrategy):
    
    def __init__(self, attributes: dict, agent: HVACDSOTAgent):
        """TODO

        Args:
            attributes (dict): Externally defined attributes, generally fixed
                throughout the simulation
            schedule (HVACSchedule): TODO
            flexibility (HVACDSOTPriceFlexibilityCurve): Used to evaluate the 
                4-point bid and TODO
        """
        super().__init__(attributes, self.agent.schedule, self.agent.flexibility)
        self.RT_test_support: bool = None
        init_class_attributes(self, attributes)

        # Internally calculated simulation parameters or variables
        # Generally not-fixed throughout simulation
        self.agent = agent
        self.temp_max_cool_da: float = 0
        self.temp_min_cool_da: float = 0
        self.temp_max_heat_da: float = 0
        self.temp_min_heat_da: float = 0
        self.forecast_temperature_min: float = 0
        self.forecast_temperature_max: float = 0
        self.forecast_temperature_delta: float = 0
        self.ramp_high_limit: float = 0
        self.ramp_low_limit: float = 0
        self.TIME: list = []
        self.optimized_Quantity = []
        self.price_forecast_0_new: float = 0
        self.price_delta: float = 0
        self.price_mean: float = 0
        self.air_temp_agent: float = 0 # May not be needed as AssetModel is holding the estimated value
        self.Qopt_da_prev: float = 0
        self.temp_da_prev: float = 0
        self.previous_Q_DA: float = 0
        self.previous_T_DA: float = 0
        self.delta_Q: float = 0
        self.delta_T: float = 0
        self.bid_da = []
        self.opt_indoor_air_temperature = []
        self.temp_desired_48hour_cool = []
        self.temp_desired_48hour_heat = []
        self.latent_factor = []
        self.temp_room_previous_cool: float = 0
        self.temp_room_previous_heat: float = 0
        self.temp_outside_init: float = 0
        self.ProfitMargin_intercept: float = 0
        self.temp_room_init: float = 0
        self.eps: float = 0
        self.FirstTime: bool = False

        self.bid = DSOT4pointBid()
        #TODO: self.bid same as self.bid_rt from create_bid?

        if "RT_test_support" in attributes.keys():
            self.bid_da = attributes["RT_test_support"]["bid_da"]
            self.previous_Q_DA = attributes["RT_test_support"]["previous_Q_DA"]
            self.previous_T_DA = attributes["RT_test_support"]["previous_T_DA"]
            self.opt_indoor_air_temperature = [attributes["RT_test_support"]["temp_room_value"] for _ in range(self.windowLength_hr)]

    def update_forecast_temperature_limits(self) -> tuple:
        """Updates min and max forecasted temperature

        Args:
            forecasts (DSOTForecasts): Object holding all the forecasted values

        Returns:
            tuple: 48 hour min and max (in that order) price forecast
                followed by the delta between the two.
        """
        self.forecast_temperature_min = min(self.agent.forecasts.outside_air_temperature)
        self.forecast_temperature_max = max(self.agent.forecasts.outside_air_temperature)
        self.forecast_temperature_delta
        return self.forecast_temperature_min, self.forecast_temperature_max, self.forecast_temperature_delta
    
    def update_da_indoor_temperature_limits(self, cooling_setpt: float,
                                            heating_setpt: float) -> None:
        """Update indoor temperature limits based on current cooling and
        heating setpoints

        Args:
            cooling_setpt (float): Scheduled cooling setpoint
            heating_setpt (float): Scheduled heating setpoint
        """
        self.temp_max_cool_da = cooling_setpt + self.agent.schedule.range_high_cool 
        self.temp_min_cool_da = cooling_setpt - self.agent.schedule.range_low_cool  
        self.temp_max_heat_da = heating_setpt + self.agent.schedule.range_high_heat  
        self.temp_min_heat_da = heating_setpt - self.agent.schedule.range_low_heat  
        if ((self.temp_max_heat_da + self.agent.temp.deadband / 2.0 + 0.5)
            > (self.temp_min_cool_da - self.agent.temp.deadband / 2.0 - 0.5)):
            mid_point = (self.temp_min_cool_da + self.temp_max_heat_da) / 2.0
            self.temp_min_cool_da = mid_point + self.agent.temp.deadband / 2.0 + 0.5
            self.temp_max_heat_da = mid_point - self.agent.temp.deadband / 2.0 - 0.5
            if self.temp_min_cool_da > cooling_setpt:
                self.temp_min_cool_da = cooling_setpt
            if self.temp_max_heat_da < heating_setpt:
                self.temp_max_heat_da = heating_setpt
        
    def initialize_inside_air_temperature(self) -> None:
        """TODO
        """
        self.temp_da_prev = self.agent.forecasts.inside_air_temperature
        # TODO - What do we need to do when the thermostat is "OFF"
        if self.agent.thermostat_mode == ThermostatMode.COOLING:
            self.temp_room_init = self.agent.temp.cooling_setpoint
        else:
            self.temp_room_init = self.agent.temp.heating_setpoint
        
    def update_da_temperature_limits(self, sim_time: dt.datetime) -> None:
        """Updates the desired temperature limits, making sure the desired 
        temperature falls between min and max temp values, which are then used 
        to adjust the basepoint and vice-versa.

        Args:
            sim_time (dt.datetime): TODO
        """
        self.update_forecast_temperature_limits()
        for time_idx in range(self.windowLength_hr):
            hour = sim_time.hour + sim_time.minute / 60 + time_idx + 1 / 60 # hours
            scheduled_cooling_setpoint, scheduled_heating_setpoint = HVACSchedule.get_scheduled_setpoint(hour, 
                                                                                                         sim_time.weekday())
            # update temp limits
            self.update_da_indoor_temperature_limits(scheduled_cooling_setpoint, scheduled_heating_setpoint)

            if scheduled_cooling_setpoint > self.temp_max_cool_da:
                scheduled_cooling_setpoint = self.temp_max_cool_da
            if scheduled_cooling_setpoint < self.temp_min_cool_da:
                scheduled_cooling_setpoint = self.temp_min_cool_da
            if scheduled_heating_setpoint > self.temp_max_heat_da:
                scheduled_heating_setpoint = self.temp_max_heat_da
            if scheduled_heating_setpoint < self.temp_min_heat_da:
                scheduled_heating_setpoint = self.temp_min_heat_da
            self.temp_desired_48hour_cool[time_idx] = scheduled_cooling_setpoint
            self.temp_desired_48hour_heat[time_idx] = scheduled_heating_setpoint
        
    def setup_da_temperature_parameters(self, sim_time: dt.datetime) -> None:
        """TODO

        Args:
            sim_time (dt.datetime): _description_
        """
        self.update_da_temperature_limits(sim_time)
        HVACDSOTSystemModel.calc_cooling_COP()
        HVACDSOTSystemModel.calc_heating_COP()
        self.initialize_inside_air_temperature()
        
    def estimate_required_cooling_quantity(self, time_idx: int) -> float:
        """TODO

        Args:
            time_idx (int): _description_

        Returns:
            float: _description_
        """
        temp_room = self.temp_desired_48hour_cool
        cop_adj = (-np.array(self.agent.system_model.cooling_cop_adj_da)).tolist()
        if time_idx == 0:
            t_pre = self.temp_room_previous_cool
        else:
            t_pre = temp_room[time_idx - 1]
        temp1 = (((temp_room[time_idx] - self.eps * t_pre) / (1 - self.eps)) 
                - self.agent.forecasts.outside_air_temperature[time_idx])
        temp2 = (temp1 * self.agent.structure_model.etp_structure_params.UA - self.agent.forecasts.internal_gain[time_idx] -
                    self.agent.forecasts.solar_gain[time_idx] * self.agent.structure_model.solar_heatgain_factor)
        quant = temp2 / (cop_adj[time_idx] * KW_TO_BTU_PER_HR / self.latent_factor[time_idx])
        quant_cool = max(quant, 0)
        return quant_cool
    
    def estimate_required_heating_quantity(self, time_idx: int) -> float:
        """TODO

        Args:
            time_idx (int): _description_

        Returns:
            float: _description_
        """
        temp_room = self.temp_desired_48hour_heat
        cop_adj = self.agent.system_model.heating_cop_adj_da
        if time_idx == 0:
            t_pre = self.temp_room_previous_heat
        else:
            t_pre = temp_room[time_idx - 1]
        temp1 = (((temp_room[time_idx] - self.eps * t_pre) / (1 - self.eps)) 
            - self.agent.forecasts.outside_air_temperature[time_idx])
        temp2 = (temp1 * self.agent.structure_model.etp_structure_params.UA - self.agent.forecasts.internal_gain[time_idx] -
                    self.agent.forecasts.solar_gain[time_idx] * self.agent.structure_model.solar_heatgain_factor)
        quant = temp2 / (cop_adj[time_idx] * KW_TO_BTU_PER_HR / self.latent_factor[time_idx])
        quant_heat = max(quant, 0)
        return quant_heat

    def get_uncntrl_hvac_load(self, sim_time: dt.datetime) -> float:
        """TODO

        Args:
            sim_time (dt.datetime): _description_

        Returns:
            float: _description_
        """
        self.update_da_temperature_limits(sim_time)
        quantity = []
        for time_idx in range(self.windowLength_hr):
            quant_cool = self.estimate_required_cooling_quantity(time_idx)
            quant_heat = self.estimate_required_heating_quantity(time_idx)

            # Both quant_cool and quant_heat can not be positive simultaneously.
            # So whichever is positive, that mode is active
            quant = max(quant_cool, quant_heat)
            quantity.append(abs(quant))

            # Storing the real-time (current hour) temp to be used in next hour initialization
            self.temp_room_previous_cool = self.temp_desired_48hour_cool[0]
            self.temp_room_previous_heat = self.temp_desired_48hour_heat[0]
        return quantity

    def temperature_bound_rule(self, m: pyo.ConcreteModel, t: int) -> tuple:
        """Defines the temperature limits for the Pyomo optimization

        Args:
            m (ConcreteModel): Pyomo ConcreteModel model object
            t (int): Index for time vector

        Returns:
            tuple: Lower and upper temperature limit
        """
        if self.agent.thermostat_mode ==  ThermostatMode.COOLING:
            return (self.temp_desired_48hour_cool[t] - self.agent.schedule.range_low_cool,
                    self.temp_desired_48hour_cool[t] + self.agent.schedule.range_high_cool)
        else:
            return (self.temp_desired_48hour_heat[t] - self.agent.schedule.range_low_heat,
                    self.temp_desired_48hour_heat[t] + self.agent.schedule.range_high_heat)

    def obj_rule(self, m: pyo.ConcreteModel) -> float:
        """Defines the Pyomo object function based on HVAC mode

        Args:
            m (ConcreteModel): Pyomo ConcreteModel model object

        Returns:
            float: objective function value
        """
        if self.agent.asset_state.thermostat_mode == 'Cooling':
            temp = self.temp_desired_48hour_cool
        else:
            temp = self.temp_desired_48hour_heat
        # TODO - Add something for when thermostat is in OFF mode?
        # Short-form variable assignments employed for human-readability.
        sld = self.slider
        frcst = self.agent.forecasts.price
        price_delt = self.price_delta
        hvac_q = m.quan_hvac
        hvac_kW = self.agent.asset_state.hvac_kW
        air_temp_i = m.inside_air_temperature #TODO check that this correction is accurate. 
        # This was: m.opt_indoor_air_temperature, which is part of the DA bidding strategy
        rng_low = self.agent.schedule.range_low_limit
        rng_hi = self.agent.schedule.range_high_limit

        if hvac_kW != 0 and price_delt != 0 and (rng_low + rng_hi) != 0:
            return sum(sld * (frcst[t] - np.min(frcst)) / price_delt * hvac_q[t] / hvac_kW
                    + 0.1 * ((air_temp_i[t] - temp[t]) / (rng_low + rng_hi)) ** 2
                    + 0.001 * sld * (hvac_q[t] / hvac_kW * hvac_q[t] / hvac_kW)
                    for t in self.TIME)
        else:
            return 0
    
    def con_rule_eq1(self, m: pyo.ConcreteModel, t: int) -> None:  # initialize SOHC state
        """Constraint equation for Pyomo optimzation formulation based on the
        HVAC mode and the index in the list of times being estimated

        Args:
            m (ConcreteModel): Pyomo ConcreteModel model object
            t (int): Index for time vector

        Returns:
            _type_: _description_
        """
        # Short-form variable assignments employed for human-readability.
        temp_in = m.inside_air_temperature
        eps = self.eps
        temp_init = self.temp_room_init
        temp_out = self.agent.forecasts.outside_air_temperature
        cop_cool_da = self.agent.system_model.cooling_cop_adj_da
        cop_heat_da = self.agent.system_model.heating_cop_adj_da
        hvac_q = m.hvac_quant
        lat_f = self.latent_factor
        int_gain = self.agent.forecasts.internal_gain
        sol_gain = self.agent.forecasts.solar_gain
        sol_heatgain = self.agent.structure_model.solar_heatgain_factor
        ua = self.agent.structure_model.etp_structure_params.UA

        if self.agent.thermostat_mode == ThermostatMode.COOLING:
            if t == 0:
                # Initial SOHC state
                return temp_in[0] == (eps * temp_init + (1 - eps) 
                                    * (temp_out[0] + ((-cop_cool_da[0] * 0.98 * hvac_q[0] 
                                    * KW_TO_BTU_PER_HR / lat_f[0] + int_gain[0] 
                                    + sol_gain[0] * sol_heatgain) / ua)))
            else:
                # update SOHC
                return temp_in[t] == (eps * temp_in[t - 1] + (1 - eps)
                                    * (temp_out[t] + ((-cop_cool_da[t] * 0.98 * hvac_q[t] 
                                    * KW_TO_BTU_PER_HR / lat_f[t] + int_gain[t] 
                                    + sol_gain[t] * sol_heatgain) / ua)))
        else:
            if t == 0:
                # Initial SOHC state
                return temp_in[0] == (eps * temp_init + (1 - eps) 
                                * (temp_out[0] + ((cop_heat_da[0] * 1.02 * hvac_q[0] 
                                * KW_TO_BTU_PER_HR / lat_f[0] + int_gain[0] 
                                + sol_gain[0] * sol_heatgain) / ua)))
            else:
                # update SOHC
                return temp_in[t] == (eps * temp_in[t - 1] + (1 - eps) 
                                * (temp_out[t] + ((cop_heat_da[t] * 1.02 * hvac_q[t] 
                                * KW_TO_BTU_PER_HR / lat_f[t] + int_gain[t] 
                                + sol_gain[t] * sol_heatgain) / ua)))
        

    def solve_for_da_optimal_quantities(self) -> tuple:
        """TODO

        Returns:
            tuple: _description_
        """
        # Create model
        model = pyo.ConcreteModel()
        # Decision variables
        model.hvac_quant= pyo.Var(range(self.windowLength_hr), bounds=(0.0, self.agent.asset_state.hvac_kW))
        model.inside_air_temperature = pyo.Var(range(self.windowLength_hr), bounds=self.temperature_bound_rule)
        # Objective of the problem
        model.obj = pyo.Objective(rule=self.obj_rule, sense=pyo.minimize)
        # Constraints
        model.con1 = pyo.Constraint(range(self.windowLength_hr), rule=self.con_rule_eq1)
        # Solve
        results = get_run_solver("hvac_" + self.name, pyo, model, self.solver) #TODO: no self.solver
        hvac_quantity = [0 for _ in range(self.windowLength_hr)]
        indoor_room_temperature = [0 for _ in range(self.windowLength_hr)]
        for t in range(self.windowLength_hr):
            indoor_room_temperature[t] = pyo.value(model.inside_air_temperature[t])
            hvac_quantity[t] = pyo.value(model.quan_hvac[t])
        return hvac_quantity, indoor_room_temperature
    
    def formulate_da_bid(self) -> list:
        """TODO

        Returns:
            list: TODO
        """
        self.Qopt_da_prev = self.bid_da[0][1][0]
        self.price_forecast_0 = self.agent.forecasts.price[0]
        BID = []
        for _ in self.TIME:
            BID.append([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
        if self.agent.asset_model.heating_system_type != 'HEAT_PUMP' and self.agent.asset_state.thermostat_mode == 'Heating':
            self.bid_da = BID
            return self.bid_da
        
        Quantity = self.optimized_Quantity
        self.FirstTime = False
        P = 1  
        Q = 0
        CurveSlope = []
        yIntercept = []
        for _ in self.TIME:
            CurveSlope.append(0.0)
            yIntercept.append(-1.0)
        #TODO: There is no price_forecast, there is price_forecast_0 or price_forecast_0_new
        delta_DA_price = max(self.agent.forecasts.price_forecast) - min(self.agent.forecasts.price_forecast)
        for t in self.TIME:
            CurveSlope[t] = (delta_DA_price / (0 - self.agent.asset_state.hvac_kW) * (1 + self.ProfitMargin_slope / 100))
            yIntercept[t] = (self.agent.forecasts.price_forecast[t] - CurveSlope[t] * Quantity[t])
            BID[t][0][Q] = 0
            BID[t][1][Q] = Quantity[t]
            BID[t][2][Q] = Quantity[t]
            BID[t][3][Q] = self.agent.asset_state.hvac_kW

            BID[t][0][P] = 0 * CurveSlope[t] + yIntercept[t] + (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[t][1][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] + (
                    self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[t][2][P] = Quantity[t] * CurveSlope[t] + yIntercept[t] - (
                    self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[t][3][P] = self.agent.asset_state.hvac_kW * CurveSlope[t] + yIntercept[t] - (
                    self.ProfitMargin_intercept / 100) * delta_DA_price

            for i in range(4):
                if BID[t][i][Q] > self.agent.asset_state.hvac_kW:
                    BID[t][i][Q] = self.agent.asset_state.hvac_kW
                if BID[t][i][Q] < 0:
                    BID[t][i][Q] = 0
                if BID[t][i][P] > self.price_cap:
                    BID[t][i][P] = self.price_cap
                if BID[t][i][P] < 0:
                    BID[t][i][P] = 0

        self.bid_da = BID
        self.RT_minute_count_interpolation = float(0.0)
        return self.bid_da
        
class HVACDSOTRTBiddingStrategy(HVACDSOTBiddingStrategy):
    def __init__(self, attributes: dict, period: int, agent: HVACDSOTAgent):
        """TODO
        
        Args:
            attributes (dict): dictionary of attributes, internally calculated 
                simulation parameters or variables, generally not-fixed 
                throughout simulation.
            period (int): _description_
            schedule (HVACSchedule): _description_
            flexibility (HVACDSOTPriceFlexibilityCurve): _description_
        """
        super().__init__(attributes, self.agent.schedule, self.agent.flexibility)
        self.period = period
        self.agent = agent
        init_class_attributes(self, attributes)
        self.RT_minute_count_interpolation: int = 0
        self.bid_quantity: float = 0
        self.bid_quantity_rt: float = 0
        self.cleared_price: float = 0
        self.quantity_curve = [0 for _ in range(10)]
        self.temp_curve = [0]
        self.Qopt_DA: float = 0
        self.Topt_DA: float = 0
    
    def interpolate_DA_quantities_into_RT(self) -> tuple:
        """TODO

        Args:
            da_bidding_strategy (HVACDSOTDABiddingStrategy): TODO

        Returns:
            tuple: _description_
        """
        if self.interpolation:
            if self.RT_minute_count_interpolation == 0.0:
                self.delta_Q = (self.agent.da_bidding_strategy.bid_da[0][1][0] - self.agent.da_bidding_strategy.previous_Q_DA)
                self.delta_T = (self.agent.da_bidding_strategy.opt_indoor_air_temperature[0] - self.agent.da_bidding_strategy.previous_T_DA)
            if self.RT_minute_count_interpolation == 30.0:
                self.delta_Q = (self.agent.da_bidding_strategy.bid_da[1][1][0] - self.agent.da_bidding_strategy.previous_Q_DA) * 0.5
                self.delta_T = (self.agent.da_bidding_strategy.opt_indoor_air_temperature[1] - self.agent.da_bidding_strategy.previous_T_DA) * 0.5
            self.Qopt_DA = self.agent.da_bidding_strategy.previous_Q_DA + self.delta_Q * (5.0 / 30.0)
            self.Topt_DA = self.agent.da_bidding_strategy.previous_T_DA + self.delta_T * (5.0 / 30.0)
            self.agent.da_bidding_strategy.previous_Q_DA = self.Qopt_DA
            self.agent.da_bidding_strategy.previous_T_DA = self.Topt_DA
        else:
            self.Qopt_DA = self.agent.da_bidding_strategy.bid_da[0][1][0]
            self.Topt_DA = self.agent.da_bidding_strategy.opt_indoor_air_temperature[0]
        
        return self.Qopt_DA, self.Topt_DA

    def estimate_hvac_energy_in_rt_period(self) -> list:
        """TODO

        Returns:
            list: TODO
        """
        T = (self.bid_delay + self.period) / 3600.0  # 300
        time = np.linspace(0, T, num=10)  # [0,topt-dt, topt, topt+dt]
        # TODO: this needs to be more generic, like a function of slider
        npt = 5
        self.temp_curve = []
        self.quantity_curve = []
        for i in range(npt):
            self.temp_curve.append(self.Topt_DA + (i - 2) / 4.0 * self.slider)
            self.quantity_curve.append(0.0)

        for itemp in range(npt):
            x = np.zeros([2, 1])
            x[0] = self.agent.asset_state.indoor_air_temp
            x[1] = self.agent.asset_state.mass_temp
            Q_max = self.agent.asset_state.hvac_kW #TODO:unused
            Q_min = 0.0 #TODO:unused

            # self.temp_curve[0] = self.air_temp
            if ((self.agent.thermostat_mode == ThermostatMode.COOLING and self.agent.asset_state.hvac_on) or
                    (self.agent.thermostat_mode != ThermostatMode.COOLING and not self.agent.asset_state.hvac_on)):
                self.temp_curve[0] = self.agent.asset_state.indoor_air_temp + self.agent.temp.deadband / 2.0
            elif ((self.agent.thermostat_mode != ThermostatMode.COOLING and self.agent.asset_state.hvac_on) or
                (self.agent.thermostat_mode == ThermostatMode.COOLING and not self.agent.asset_state.hvac_on)):
                self.temp_curve[0] = self.agent.asset_state.indoor_air_temp - self.agent.temp.deadband / 2.0
            hvac_on_tmp = self.agent.asset_state.hvac_on
            Q_total = 0
            for _ in range(1, len(time)):
                # this is based on the assumption that only one status change happens in 5-min period
                eAET = linalg.expm(self.agent.asset_model.A_ETP * T / 10.0)
                AIET = np.dot(self.agent.asset_model.AEI, eAET)
                AEx = np.dot(self.agent.asset_model.A_ETP, x)
                if hvac_on_tmp:
                    AxB = AEx + self.agent.asset_model.B_ETP_ON
                    AIB = np.dot(self.agent.asset_model.AEI, self.agent.asset_model.B_ETP_ON)
                    AExB = np.dot(AIET, AxB)
                    x = AExB - AIB
                    Q_total += 1 / 10 * self.agent.asset_state.hvac_kW
                    if ((x[0][0] < self.temp_curve[itemp] - self.agent.temp.deadband / 2.0 and
                        self.agent.thermostat_mode == ThermostatMode.COOLING) or
                            (x[0][0] > self.temp_curve[itemp] + self.agent.temp.deadband / 2.0 and
                            self.agent.thermostat_mode == ThermostatMode.HEATING)):
                        hvac_on_tmp = False
                else:
                    AxB = AEx + self.agent.asset_model.B_ETP_OFF
                    AIB = np.dot(self.agent.asset_model.AEI, self.agent.asset_model.B_ETP_OFF)
                    AExB = np.dot(AIET, AxB)
                    x = AExB - AIB
                    if ((x[0][0] > self.temp_curve[itemp] + self.agent.temp.deadband / 2.0 and
                        self.agent.thermostat_mode == ThermostatMode.COOLING) or
                            (x[0][0] < self.temp_curve[itemp] - self.agent.temp.deadband / 2.0 and
                            self.agent.thermostat_mode == ThermostatMode.HEATING)):
                        hvac_on_tmp = True

            self.quantity_curve[itemp] = Q_total
        return self.quantity_curve

    def create_bid(self) -> DSOT4pointBid:
        """TODO

        Returns:
            DSOT4pointBid: TODO
        """
        Q_min = min(self.quantity_curve)
        Q_max = max(self.quantity_curve)
        delta_DA_price = max(self.agent.forecasts.price) - min(self.agent.forecasts.price)
        self.agent.forecasts.price_forecast_0_new = self.agent.forecasts.price[0]
        BID = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        P = 1
        Q = 0
        if Q_min != Q_max:
            CurveSlope = (delta_DA_price / (0 - self.agent.asset_state.hvac_kW) * (1 + self.ProfitMargin_slope / 100))
            yIntercept = self.agent.forecasts.price_forecast_0 - CurveSlope * self.Qopt_DA
            if Q_max > self.Qopt_DA > Q_min:
                BID[0][Q] = Q_min
                BID[1][Q] = self.Qopt_DA
                BID[2][Q] = self.Qopt_DA
                BID[3][Q] = Q_max

                BID[0][P] = Q_min * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[1][P] = self.Qopt_DA * CurveSlope + yIntercept + (self.ProfitMargin_intercept / 100) * delta_DA_price
                BID[2][P] = self.Qopt_DA * CurveSlope + yIntercept - (self.ProfitMargin_intercept / 100) * delta_DA_price
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

            BID[0][P] = max(self.agent.forecasts.price) + (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[1][P] = max(self.agent.forecasts.price) + (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[2][P] = min(self.agent.forecasts.price) - (self.ProfitMargin_intercept / 100) * delta_DA_price
            BID[3][P] = min(self.agent.forecasts.price) - (self.ProfitMargin_intercept / 100) * delta_DA_price

        for i in range(4):
            if BID[i][Q] > self.agent.asset_state.hvac_kW:
                BID[i][Q] = self.agent.asset_state.hvac_kW
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

    def form_rt_bid(self):
        """TODO

        Returns:
            _type_: _description_
        """
        # If asset type or state doesn't allow participation in market
        if self.agent.asset_model.heating_system_type != 'HEAT_PUMP' and self.agent.asset_state.thermostat_mode == 'Heating':
            self.cooling_setpoint = self.agent.temp.temp_min_cool
            self.bid_rt = [[0, 0], [0, 0], [0, 0], [0, 0]]
            return self.bid_rt

        self.interpolate_DA_quantities_into_RT()
        self.estimate_hvac_energy_in_rt_period()
        self.create_bid()
        return self.bid_rt          

class DSOTRTMarketInterface:
    
    def __init__(self):
        self.clearing_price = []
        self.clearing_quantities = []

