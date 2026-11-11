# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: hvac_agent_stub.py
"""HVAC device agent: Observe and Define Flexibility.

The agent performs only two tasks:

1. Observe - retrieve the current physical state of the HVAC system.
   Interchangeable observers provide the state:

   - ``GridLABDHVACObserver``: reads the GridLAB-D house object
     (physics-based, full).
   - ``PhysicsStubHVACObserver``: evolves a light two-node ETP house model
     with thermostat deadband cycling (stub, agent-based approximation).
   - ``StatisticalStubHVACObserver``: placeholder for a statistical
     approximation built from large datasets such as ResStock (stub).

2. Define Flexibility - ``HVACFlexibilityModel`` takes the observation, the
   fixed device definition, and separate weather and house forecasts, and
   returns for every interval of a market horizon:

   - the feasible quantity range [Q_min, Q_max] in kW,
   - an amenity mapping from feasible power levels to a user-selectable
     amenity metric, and
   - the baseline operating point (power used when simply tracking the
     customer setpoint with no price consideration).

   The flexibility model always uses its own light physics model, regardless
   of which observer produced the state.

Market horizons: the day-ahead case is 48 hourly intervals, re-forecast every
hour with the latest observation (``MarketHorizon.day_ahead``). The same code
handles a single 5-minute real-time interval (``MarketHorizon.real_time``).

Not part of the agent: customer preference curves and bid curves (formed by
device-agnostic scripts from ``HVACFlexibility``), and control translation
from a cleared quantity back to a thermostat setpoint.

Physics are ported from the original DSO+T agent (``dsot/hvac_agent.py``),
including air infiltration in UA and the original design-capacity formula.

---
Unit conventions (matching DSO+T):

Temperature - Fahrenheit [F]
Heat flow - [Btu/h]
Electric power - [kW]
Thermal capacitance - [Btu/F]
Thermal conductance - [Btu/(F*h)]
Area - [sqft]
Solar flux - [Btu/(h*sqft)]
---
"""

import datetime as dt
import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from typing import Any, Protocol

import numpy as np
from scipy.linalg import expm

from tesp_support.api.parse_helpers import parse_number

logger = logging.getLogger(__name__)

KW_TO_BTU_PER_HR = 3412.1416331279

# Temperature-dependent equipment performance curves from DSO+T. COP curves
# are energy-input-ratio multipliers (COP = rated_COP / curve); capacity curves
# are capacity multipliers. All equal 1.0 at the rating conditions (95 F
# cooling, 47 F heating).
COOLING_COP_K = (-0.01363961, 0.01066989)
COOLING_COP_LIMIT = 40.0  # curve held constant below this outdoor temperature
HEATING_COP_K = (2.03914613, -0.03906753, 0.00045617, -0.00000203)
HEATING_COP_LIMIT = 80.0  # curve held constant above this outdoor temperature
COOLING_CAPACITY_K = (1.48924533, -0.00514995)
HEATING_CAPACITY_K = (0.34148808, 0.00894102, 0.00010787)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class HVACMode(Enum):
    OFF = "off"
    COOLING = "cooling"
    HEATING = "heating"


class HeatingFuel(Enum):
    NONE = "NONE"
    GAS = "GAS"
    RESISTANCE = "RESISTANCE"
    HEAT_PUMP = "HEAT_PUMP"

    @classmethod
    def from_string(cls, value: str) -> 'HeatingFuel':
        """Maps DSO+T and GridLAB-D heating system names to a HeatingFuel.

        DSO+T uses "ELECTRIC" for resistance heating; GridLAB-D uses
        "RESISTANCE".
        """
        value = value.strip().upper()
        if value == "ELECTRIC":
            return cls.RESISTANCE
        return cls(value)


class ObservationMode(Enum):
    GRIDLABD = "gridlabd"
    PHYSICS_STUB = "physics_stub"
    STATISTICAL_STUB = "statistical_stub"


# ---------------------------------------------------------------------------
# Task 1 output: observation
# ---------------------------------------------------------------------------

@dataclass
class HVACObservation:
    """Current physical state of the HVAC system (Task 1 output).

    Only device state is held here; weather and house conditions live in
    WeatherForecast and HouseForecast.

    Attributes:
        timestamp: Simulation time of the observation.
        indoor_air_temp: Indoor air temperature [F].
        hvac_mode: Mode the system is operating in or would serve next.
        hvac_on: Whether the compressor/element/burner is running.
        cooling_setpoint: Thermostat cooling setpoint [F].
        heating_setpoint: Thermostat heating setpoint [F].
        hvac_kw: Real power consumption of the HVAC system [kW].
        mass_temp: Structure mass temperature [F]. GridLAB-D and the physics
            stub provide it; a statistical stub may not, in which case the
            flexibility model assumes it equals the indoor air temperature.
        source: Which observer produced this observation.
        uncertainty: Per-field standard deviations, keyed by attribute name.
            Only populated by statistical observers.
    """
    timestamp: dt.datetime
    indoor_air_temp: float
    hvac_mode: HVACMode
    hvac_on: bool
    cooling_setpoint: float
    heating_setpoint: float
    hvac_kw: float
    mass_temp: float | None = None
    source: ObservationMode = ObservationMode.GRIDLABD
    uncertainty: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Task 2 constraints: device definition
# ---------------------------------------------------------------------------

@dataclass
class HVACDefinition:
    """Fixed definition of the HVAC system and the structure it conditions.

    Attributes:
        slider: Customer flexibility setting, 0 (none) to 1 (most). Scales
            the comfort band around the setpoint.
        deadband: Thermostat deadband [F].
        range_high_limit: Comfort band width above the setpoint at slider=1 [F].
        range_low_limit: Comfort band width below the setpoint at slider=1 [F].
        heating_fuel: Heating system type. Only electric heating has
            electrical flexibility.
        has_cooling: Whether the house has electric cooling.
        design_cooling_capacity: Rated cooling capacity [Btu/h].
        design_heating_capacity: Rated heating capacity [Btu/h].
        cooling_COP: Rated cooling COP.
        heating_COP: Rated heat pump COP. Resistance heating always uses 1.
        UA: Envelope conductance including air infiltration [Btu/(F*h)].
        CA: Indoor air heat capacity [Btu/F].
        CM: Structure mass heat capacity [Btu/F].
        HM: Air-to-mass conductance [Btu/(F*h)].
        solar_heatgain_factor: Effective solar aperture (window area times
            transmission coefficients) [sqft]. Solar heat gain is the solar
            flux times this factor.
        mass_internal_gain_fraction: Fraction of internal gains into the mass.
        mass_solar_gain_fraction: Fraction of solar gains into the mass.
        latent_load_fraction: Latent cooling load fraction.
        fan_heat_fraction: Fraction of capacity added to the air as fan heat.
        cooling_participating: Whether cooling offers flexibility.
        heating_participating: Whether heating offers flexibility.
    """
    slider: float
    deadband: float
    range_high_limit: float
    range_low_limit: float
    heating_fuel: HeatingFuel
    has_cooling: bool
    design_cooling_capacity: float
    design_heating_capacity: float
    cooling_COP: float
    heating_COP: float
    UA: float
    CA: float
    CM: float
    HM: float
    solar_heatgain_factor: float
    mass_internal_gain_fraction: float = 0.5
    mass_solar_gain_fraction: float = 0.5
    latent_load_fraction: float = 0.3
    fan_heat_fraction: float = 0.02
    cooling_participating: bool = True
    heating_participating: bool = True

    @classmethod
    def config(cls, house_config: dict, hvac_config: dict, **overrides) -> 'HVACDefinition':
        """Builds a definition from house and HVAC agent configuration.

        Args:
            house_config (dict): defined house properties (sqft, R values,
                window description, airchange_per_hour, cooling_COP, heating,
                cooling, over_sizing_factor, ...).
            hvac_config (dict): HVAC agent configuration (slider_setting, 
                deadband, range_high_limit, range_low_limit,
                cooling_participating, heating_participating).
            **overrides: Any HVACDefinition field to set directly, or any
                design condition accepted by calc_design_capacities().

        Returns:
            HVACDefinition: definition with the structure ETP parameters and
                design capacities calculated as in DSO+T.
        """
        design_keys = ("cooling_design_temperature", "design_cooling_setpoint",
                       "design_heating_setpoint", "heating_design_temperature",
                       "design_peak_solar")
        design_conditions = {k: overrides.pop(k) for k in design_keys if k in overrides}

        heating_fuel = HeatingFuel.from_string(house_config["heating"])
        latent_load_fraction = overrides.get("latent_load_fraction", 0.3)
        etp = calc_structure_etp(house_config)
        design_cooling, design_heating = calc_design_capacities(
            UA=etp["UA"],
            solar_heatgain_factor=etp["solar_heatgain_factor"],
            sqft=float(house_config["sqft"]),
            over_sizing_factor=float(house_config["over_sizing_factor"]),
            latent_load_fraction=latent_load_fraction,
            heating_fuel=heating_fuel,
            **design_conditions)
        cooling_COP = float(house_config["cooling_COP"])

        params = dict(
            slider=float(hvac_config["slider_setting"]),
            deadband=float(hvac_config["deadband"]),
            range_high_limit=float(hvac_config["range_high_limit"]),
            range_low_limit=float(hvac_config["range_low_limit"]),
            heating_fuel=heating_fuel,
            has_cooling=str(house_config["cooling"]).strip().upper() != "NONE",
            design_cooling_capacity=design_cooling,
            design_heating_capacity=design_heating,
            cooling_COP=cooling_COP,
            # DSO+T derives the heat pump COP from the cooling COP
            heating_COP=cooling_COP - 1.0,
            cooling_participating=bool(hvac_config.get("cooling_participating", True)),
            heating_participating=bool(hvac_config.get("heating_participating", True)),
            **etp)
        params.update(overrides)
        return cls(**params)


# Window U-values [Btu/(F*h*sqft)] keyed by (glass_type, glazing_layers);
# one value per window frame type (0 none, 1 aluminum, 2 thermal break,
# 3 wood, 4 insulated). glass_type: 0 other, 1 normal, 2 low-e.
_WINDOW_U = {
    (1, 1): (1.04, 1.27, 1.08, 0.90, 0.81),
    (1, 2): (0.48, 0.81, 0.60, 0.53, 0.44),
    (1, 3): (0.31, 0.67, 0.46, 0.40, 0.34),
    (2, 2): (0.30, 0.67, 0.47, 0.41, 0.33),
    (2, 3): (0.27, 0.64, 0.43, 0.37, 0.31),
}
_OTHER_GLASS_R = 2.0

# Window solar transmission keyed by (glazing_layers, glazing_treatment); one
# value per frame group (none; aluminum or thermal break; wood or insulated).
# glazing_treatment: 1 clear, 2 absorbing, 3 reflective, 4 low-S, 5 high-S.
_WINDOW_TRANSMISSION = {
    (1, 1): (0.86, 0.75, 0.64),
    (1, 2): (0.73, 0.64, 0.54),
    (1, 3): (0.31, 0.28, 0.24),
    (2, 1): (0.76, 0.67, 0.57),
    (2, 2): (0.62, 0.55, 0.46),
    (2, 3): (0.29, 0.27, 0.22),
    (2, 4): (0.41, 0.37, 0.31),
    (2, 5): (0.70, 0.62, 0.52),
    (3, 1): (0.68, 0.60, 0.51),
    (3, 2): (0.34, 0.31, 0.26),
    (3, 3): (0.34, 0.31, 0.26),
    (3, 4): (0.27, 0.25, 0.21),
    (3, 5): (0.62, 0.55, 0.46),
}
_FRAME_GROUP = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2}


def calc_structure_etp(house_config: dict) -> dict:
    """Calculates the structure ETP parameters as in DSO+T calc_etp_model().

    References:
        `Thermal Integrity Table Inputs and Defaults <https://gridlab-d.readthedocs.io/en/docs/docs/3.0%20-%20Modeling%20Reference/Modules/Residential/2.0%20-%20house-e/#thermal-integrity-table-inputs-and-defaults>`_

    Args:
        house_config (dict): defined house properties.

    Raises:
        ValueError: The window description has no entry in the lookup tables.

    Returns:
        dict: UA, CA, CM, HM, solar_heatgain_factor,
            mass_internal_gain_fraction, mass_solar_gain_fraction
    """
    hp = house_config
    sqft = float(hp["sqft"])
    stories = float(hp["stories"])
    glass_type = int(hp["glass_type"])
    glazing_layers = int(hp["glazing_layers"])
    window_frame = int(hp["window_frame"])
    glazing_treatment = int(hp["glazing_treatment"])

    if glass_type == 0:
        R_window = _OTHER_GLASS_R
    elif (glass_type, glazing_layers) in _WINDOW_U and window_frame in _FRAME_GROUP:
        R_window = 1.0 / _WINDOW_U[(glass_type, glazing_layers)][window_frame]
    else:
        raise ValueError(f"No window U-value for glass_type={glass_type}, "
                         f"glazing_layers={glazing_layers}, window_frame={window_frame}")
    if (glazing_layers, glazing_treatment) in _WINDOW_TRANSMISSION and window_frame in _FRAME_GROUP:
        Wg = _WINDOW_TRANSMISSION[(glazing_layers, glazing_treatment)][_FRAME_GROUP[window_frame]]
    else:
        raise ValueError(f"No window transmission for glazing_layers={glazing_layers}, "
                         f"glazing_treatment={glazing_treatment}, window_frame={window_frame}")

    # Hard-coded GridLAB-D defaults, as in DSO+T
    single_door_area = 19.5
    window_wall_ratio = 0.15
    interior_exterior_wall_ratio = 1.5
    interior_heat_transfer_coeff = 1.46
    air_density_times_heat_capacity = 0.0735 * 0.2402
    aspect = float(hp["aspect_ratio"]) or 1.5
    ECR = float(hp["exterior_ceiling_fraction"]) or 1.0
    EFR = float(hp["exterior_floor_fraction"]) or 1.0
    EWR = float(hp["exterior_wall_fraction"]) or 1.0
    WETC = float(hp["window_exterior_transmission_coefficient"])
    if WETC <= 0.0:
        WETC = 0.6
    h = float(hp["ceiling_height"])

    ceiling_area = (sqft / stories) * ECR
    floor_area = (sqft / stories) * EFR
    perimeter = 2 * (1 + aspect) * math.sqrt(ceiling_area / aspect)
    gross_wall_area = stories * h * perimeter
    window_area = window_wall_ratio * gross_wall_area * EWR
    door_area = float(hp["doors"]) * single_door_area
    net_wall_area = (gross_wall_area - window_area - door_area) * EWR
    air_heat_capacity = sqft * h * air_density_times_heat_capacity

    def div(x, y):
        # Some DSO+T houses have zero R values; treat as no conduction path
        return x / y if y != 0 else 0.0

    UA = (div(ceiling_area, float(hp["Rroof"]))
          + div(floor_area, float(hp["Rfloor"]))
          + div(net_wall_area, float(hp["Rwall"]))
          + div(window_area, R_window)
          + div(door_area, float(hp["Rdoors"]))
          + air_heat_capacity * float(hp["airchange_per_hour"]))
    return {
        "UA": UA,
        "CA": 3 * air_heat_capacity,
        "HM": interior_heat_transfer_coeff * (net_wall_area / EWR
                                              + gross_wall_area * interior_exterior_wall_ratio
                                              + ceiling_area * stories / ECR),
        "CM": sqft * float(hp["thermal_mass_per_floor_area"]) - 2 * air_heat_capacity,
        "solar_heatgain_factor": window_area * Wg * WETC,
        "mass_internal_gain_fraction": 0.5,
        "mass_solar_gain_fraction": 0.5,
    }


def calc_design_capacities(UA: float,
                           solar_heatgain_factor: float,
                           sqft: float,
                           over_sizing_factor: float,
                           latent_load_fraction: float,
                           heating_fuel: HeatingFuel,
                           cooling_design_temperature: float = 95.0,
                           design_cooling_setpoint: float = 75.0,
                           design_heating_setpoint: float = 70.0,
                           heating_design_temperature: float = 0.0,
                           design_peak_solar: float = 195.0) -> tuple[float, float]:
    """Sizes the HVAC system as in DSO+T calc_etp_model().

    Cooling is rounded up to a multiple of 6000 Btu/h and heating to a multiple
    of 10000 Btu/h. Heat pumps use the cooling capacity for heating.

    Returns:
        tuple: design cooling capacity, design heating capacity [Btu/h]
    """
    design_internal_gains = 167.09 * sqft ** 0.442
    cooling = ((1.0 + over_sizing_factor) * (1.0 + latent_load_fraction)
               * (UA * (cooling_design_temperature - design_cooling_setpoint)
                  + design_internal_gains
                  + design_peak_solar * solar_heatgain_factor))
    cooling = math.ceil(cooling / 6000.0) * 6000.0
    if heating_fuel == HeatingFuel.HEAT_PUMP:
        heating = cooling
    else:
        heating = (1.0 + over_sizing_factor) * UA * (design_heating_setpoint - heating_design_temperature)
        heating = math.ceil(heating / 10000.0) * 10000.0
    return cooling, heating


@dataclass
class ThermostatSchedule:
    """DSO+T thermostat schedule: four weekday periods and two weekend periods.

    Start times are decimal hours in [0, 24). Each period runs from its start
    to the next period's start; "night" wraps past midnight.
    """
    wakeup_start: float
    daylight_start: float
    evening_start: float
    night_start: float
    weekend_day_start: float
    weekend_night_start: float
    wakeup_set_cool: float
    daylight_set_cool: float
    evening_set_cool: float
    night_set_cool: float
    weekend_day_set_cool: float
    weekend_night_set_cool: float
    wakeup_set_heat: float
    daylight_set_heat: float
    evening_set_heat: float
    night_set_heat: float
    weekend_day_set_heat: float
    weekend_night_set_heat: float

    @classmethod
    def config(cls, hvac_config: dict) -> 'ThermostatSchedule':
        return cls(**{f.name: float(hvac_config[f.name]) for f in fields(cls)})

    def setpoints(self, time: dt.datetime) -> tuple[float, float]:
        """Returns the scheduled (cooling, heating) setpoints at a time."""
        hour = time.hour + time.minute / 60.0 + time.second / 3600.0
        if time.weekday() > 4:  # weekend
            if self.weekend_day_start <= hour < self.weekend_night_start:
                return self.weekend_day_set_cool, self.weekend_day_set_heat
            return self.weekend_night_set_cool, self.weekend_night_set_heat
        if self.wakeup_start <= hour < self.daylight_start:
            return self.wakeup_set_cool, self.wakeup_set_heat
        if self.daylight_start <= hour < self.evening_start:
            return self.daylight_set_cool, self.daylight_set_heat
        if self.evening_start <= hour < self.night_start:
            return self.evening_set_cool, self.evening_set_heat
        return self.night_set_cool, self.night_set_heat


# ---------------------------------------------------------------------------
# Exogenous inputs: weather and house forecasts
# ---------------------------------------------------------------------------

class _StepForecast:
    """Shared behavior for step-wise forecasts.

    Value i of each series is the average over
    [start + i * step, start + (i + 1) * step).
    """
    _series: tuple[str, ...] = ()
    _point_type: type = object

    def _validate(self) -> None:
        if self.step <= dt.timedelta(0):
            raise ValueError(f"{type(self).__name__}: step must be positive")
        lengths = {name: len(getattr(self, name)) for name in self._series}
        if len(set(lengths.values())) != 1 or 0 in lengths.values():
            raise ValueError(f"{type(self).__name__}: series must be non-empty and "
                             f"equal length, got {lengths}")

    @property
    def end(self) -> dt.datetime:
        return self.start + self.step * len(getattr(self, self._series[0]))

    def at(self, time: dt.datetime):
        """Returns the forecast values for the step containing a time."""
        if not self.start <= time < self.end:
            raise ValueError(f"{type(self).__name__}: {time} is outside forecast "
                             f"coverage [{self.start}, {self.end})")
        i = (time - self.start) // self.step
        return self._point_type(**{name: getattr(self, name)[i] for name in self._series})

    def mean_over(self, t0: dt.datetime, t1: dt.datetime):
        """Returns time-weighted average forecast values over [t0, t1)."""
        if not (self.start <= t0 < t1 <= self.end):
            raise ValueError(f"{type(self).__name__}: interval [{t0}, {t1}) is outside "
                             f"forecast coverage [{self.start}, {self.end})")
        weights = []
        i = (t0 - self.start) // self.step
        while self.start + i * self.step < t1:
            seg_start = max(t0, self.start + i * self.step)
            seg_end = min(t1, self.start + (i + 1) * self.step)
            weights.append((i, (seg_end - seg_start) / (t1 - t0)))
            i += 1
        return self._point_type(**{
            name: sum(w * getattr(self, name)[i] for i, w in weights)
            for name in self._series})


@dataclass
class WeatherPoint:
    outdoor_air_temp: float
    humidity: float
    solar_flux: float


@dataclass
class WeatherForecast(_StepForecast):
    """Weather over the forecast horizon, shared by all devices at a location.

    Attributes:
        start: Time of the first forecast step.
        step: Forecast step length (e.g. one hour).
        outdoor_air_temp: Outdoor air temperature [F].
        humidity: Outdoor relative humidity as a fraction [0-1].
        solar_flux: Average incident solar radiation on the house
            [Btu/(h*sqft)], equivalent to GridLAB-D's incident_solar_radiation.
    """
    start: dt.datetime
    step: dt.timedelta
    outdoor_air_temp: list[float]
    humidity: list[float]
    solar_flux: list[float]
    _series = ("outdoor_air_temp", "humidity", "solar_flux")
    _point_type = WeatherPoint

    def __post_init__(self):
        self._validate()


@dataclass
class HousePoint:
    internal_gain: float
    cooling_setpoint: float
    heating_setpoint: float


@dataclass
class HouseForecast(_StepForecast):
    """House conditions over the forecast horizon, specific to one house.

    Attributes:
        start: Time of the first forecast step.
        step: Forecast step length (e.g. one hour).
        internal_gain: Internal heat gains from occupants, appliances, and
            other loads [Btu/h].
        cooling_setpoint: Customer's desired cooling setpoint [F].
        heating_setpoint: Customer's desired heating setpoint [F].
    """
    start: dt.datetime
    step: dt.timedelta
    internal_gain: list[float]
    cooling_setpoint: list[float]
    heating_setpoint: list[float]
    _series = ("internal_gain", "cooling_setpoint", "heating_setpoint")
    _point_type = HousePoint

    def __post_init__(self):
        self._validate()

    @classmethod
    def from_schedule(cls,
                      schedule: ThermostatSchedule,
                      internal_gain: list[float],
                      start: dt.datetime,
                      step: dt.timedelta) -> 'HouseForecast':
        """Builds a house forecast whose setpoints follow a thermostat schedule.

        Each step uses the scheduled setpoints at the start of the step.
        """
        setpoints = [schedule.setpoints(start + i * step) for i in range(len(internal_gain))]
        return cls(start=start,
                   step=step,
                   internal_gain=list(internal_gain),
                   cooling_setpoint=[cool for cool, _ in setpoints],
                   heating_setpoint=[heat for _, heat in setpoints])


@dataclass(frozen=True)
class MarketHorizon:
    """Sequence of market intervals for which flexibility is defined."""
    start: dt.datetime
    interval: dt.timedelta
    n_intervals: int

    @classmethod
    def day_ahead(cls, start: dt.datetime, hours: int = 48) -> 'MarketHorizon':
        return cls(start, dt.timedelta(hours=1), hours)

    @classmethod
    def real_time(cls, start: dt.datetime, minutes: int = 5) -> 'MarketHorizon':
        return cls(start, dt.timedelta(minutes=minutes), 1)

    def intervals(self) -> list[tuple[dt.datetime, dt.datetime]]:
        return [(self.start + i * self.interval, self.start + (i + 1) * self.interval)
                for i in range(self.n_intervals)]


# ---------------------------------------------------------------------------
# Physics: ETP structure model and equipment performance
# ---------------------------------------------------------------------------

class ETPModel:
    """Two-node equivalent thermal parameter (ETP) model of a house.

    State x = [indoor air temperature, mass temperature] evolves as
    x' = A x + b, where

        A = [[-(UA + HM) / CA,  HM / CA],
             [  HM / CM,       -HM / CM]]
        b = [(UA * T_out + Q_air + Q_hvac) / CA,
             Q_mass / CM]

    and internal and solar gains are split between the air (Q_air) and the
    mass (Q_mass). With b held constant over a step, the exact discrete update
    is x(t + dt) = Ad x(t) + Gd b, with Ad = expm(A dt) and
    Gd = A^-1 (Ad - I). The model is linear, so a trajectory under any HVAC
    heat input is the free trajectory plus a multiple of the unit response.
    """

    def __init__(self, definition: HVACDefinition):
        d = definition
        if min(d.UA, d.CA, d.CM, d.HM) <= 0:
            raise ValueError(f"ETP parameters must be positive: UA={d.UA}, CA={d.CA}, "
                             f"CM={d.CM}, HM={d.HM}")
        self.definition = d
        self.A = np.array([[-(d.UA + d.HM) / d.CA, d.HM / d.CA],
                           [d.HM / d.CM, -d.HM / d.CM]])
        self._discretizations: dict[float, tuple[np.ndarray, np.ndarray]] = {}

    def _discretize(self, dt_h: float) -> tuple[np.ndarray, np.ndarray]:
        key = round(dt_h, 12)
        if key not in self._discretizations:
            Ad = expm(self.A * dt_h)
            Gd = np.linalg.solve(self.A, Ad - np.eye(2))
            self._discretizations[key] = (Ad, Gd)
        return self._discretizations[key]

    def forcing(self, outdoor_air_temp: float, internal_gain: float, solar_flux: float) -> np.ndarray:
        """Returns b for the given conditions with the HVAC off."""
        d = self.definition
        solar_gain = solar_flux * d.solar_heatgain_factor
        q_air = (1 - d.mass_internal_gain_fraction) * internal_gain + (1 - d.mass_solar_gain_fraction) * solar_gain
        q_mass = d.mass_internal_gain_fraction * internal_gain + d.mass_solar_gain_fraction * solar_gain
        return np.array([(d.UA * outdoor_air_temp + q_air) / d.CA, q_mass / d.CM])

    def hvac_forcing(self, heat_to_air: float) -> np.ndarray:
        """Returns the contribution to b of HVAC heat added to the air [Btu/h]."""
        return np.array([heat_to_air / self.definition.CA, 0.0])

    def simulate(self, x0: np.ndarray, b: np.ndarray, dt_h: float, n_steps: int) -> np.ndarray:
        """Simulates n_steps steps of dt_h hours with constant forcing.

        Returns:
            np.ndarray: (n_steps + 1, 2) trajectory; row 0 is x0.
        """
        Ad, Gd = self._discretize(dt_h)
        increment = Gd @ b
        trajectory = np.empty((n_steps + 1, 2))
        trajectory[0] = x0
        for k in range(n_steps):
            trajectory[k + 1] = Ad @ trajectory[k] + increment
        return trajectory


def cooling_cop(rated_cop: float, outdoor_air_temp: float) -> float:
    t = max(outdoor_air_temp, COOLING_COP_LIMIT)
    return rated_cop / (COOLING_COP_K[0] + COOLING_COP_K[1] * t)


def heating_cop(rated_cop: float, outdoor_air_temp: float) -> float:
    """Heat pump COP. Uses the actual outdoor temperature below the limit;
    DSO+T instead held the curve at the limit for all colder temperatures,
    which left the heating COP constant."""
    t = min(outdoor_air_temp, HEATING_COP_LIMIT)
    k0, k1, k2, k3 = HEATING_COP_K
    return rated_cop / (k0 + k1 * t + k2 * t ** 2 + k3 * t ** 3)


def cooling_capacity(design_capacity: float, outdoor_air_temp: float) -> float:
    k0, k1 = COOLING_CAPACITY_K
    return max(design_capacity * (k0 + k1 * outdoor_air_temp), 0.0)


def heat_pump_capacity(design_capacity: float, outdoor_air_temp: float) -> float:
    k0, k1, k2 = HEATING_CAPACITY_K
    return max(design_capacity * (k0 + k1 * outdoor_air_temp + k2 * outdoor_air_temp ** 2), 0.0)


def latent_factor(latent_load_fraction: float, humidity: float) -> float:
    """Ratio of total to sensible cooling load, from DSO+T."""
    return 1.0 + 0.1 + latent_load_fraction / (1.0 + math.exp(4.0 - 10.0 * humidity))


@dataclass(frozen=True)
class EquipmentPerformance:
    """HVAC performance at a given outdoor condition.

    Attributes:
        q_capacity_kw: Electric power at full output [kW]. Zero for gas.
        heat_per_kw: Sensible heat added to the indoor air per kW of electric
            power [Btu/h per kW]; negative when cooling.
        thermal_capacity: Sensible heat delivered at full output [Btu/h],
            signed like heat_per_kw.
        electric: Whether the equipment draws electric power.
    """
    q_capacity_kw: float
    heat_per_kw: float
    thermal_capacity: float
    electric: bool


def equipment_performance(definition: HVACDefinition,
                          mode: HVACMode,
                          outdoor_air_temp: float,
                          humidity: float) -> EquipmentPerformance | None:
    """Returns the equipment performance for a mode, or None if the house has
    no equipment for that mode."""
    d = definition
    if mode == HVACMode.COOLING:
        if not d.has_cooling:
            return None
        cop = cooling_cop(d.cooling_COP, outdoor_air_temp)
        capacity = cooling_capacity(d.design_cooling_capacity, outdoor_air_temp)
        sensible_per_thermal = -1.0 / latent_factor(d.latent_load_fraction, humidity) + d.fan_heat_fraction
        q_capacity_kw = capacity / (cop * KW_TO_BTU_PER_HR)
        return EquipmentPerformance(q_capacity_kw=q_capacity_kw,
                                    heat_per_kw=cop * KW_TO_BTU_PER_HR * sensible_per_thermal,
                                    thermal_capacity=capacity * sensible_per_thermal,
                                    electric=True)
    if mode == HVACMode.HEATING:
        if d.heating_fuel == HeatingFuel.NONE:
            return None
        if d.heating_fuel == HeatingFuel.GAS:
            return EquipmentPerformance(q_capacity_kw=0.0,
                                        heat_per_kw=0.0,
                                        thermal_capacity=d.design_heating_capacity * (1 + d.fan_heat_fraction),
                                        electric=False)
        if d.heating_fuel == HeatingFuel.HEAT_PUMP:
            cop = heating_cop(d.heating_COP, outdoor_air_temp)
            capacity = heat_pump_capacity(d.design_heating_capacity, outdoor_air_temp)
        else:
            cop = 1.0
            capacity = d.design_heating_capacity
        return EquipmentPerformance(q_capacity_kw=capacity / (cop * KW_TO_BTU_PER_HR),
                                    heat_per_kw=cop * KW_TO_BTU_PER_HR * (1 + d.fan_heat_fraction),
                                    thermal_capacity=capacity * (1 + d.fan_heat_fraction),
                                    electric=True)
    return None


def infer_mode(indoor_air_temp: float, cooling_setpoint: float, heating_setpoint: float) -> HVACMode:
    """Infers the thermostat mode when the system is idle, as in DSO+T: cooling
    above the midpoint of the setpoints, heating below."""
    midpoint = (cooling_setpoint + heating_setpoint) / 2.0
    if indoor_air_temp > midpoint:
        return HVACMode.COOLING
    if indoor_air_temp < midpoint:
        return HVACMode.HEATING
    return HVACMode.OFF


# ---------------------------------------------------------------------------
# Amenity metrics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComfortBand:
    """Customer comfort band around a setpoint [F]."""
    setpoint: float
    lower: float
    upper: float

    def excursion(self, temps: np.ndarray) -> np.ndarray:
        """Distance outside the band, zero inside it [F]."""
        return np.maximum(temps - self.upper, 0.0) + np.maximum(self.lower - temps, 0.0)


def comfort_bands(cooling_setpoint: float,
                  heating_setpoint: float,
                  definition: HVACDefinition) -> dict[HVACMode, ComfortBand]:
    """Builds the cooling and heating comfort bands as DSO+T does in
    calc_thermostat_settings(): the band half-widths are range limits scaled
    by the slider, and setpoints and band edges are pushed apart so the
    cooling and heating bands do not overlap.
    """
    d = definition
    gap = d.deadband / 2.0 + 0.5
    cool, heat = cooling_setpoint, heating_setpoint
    if cool - gap < heat + gap:
        mid = (cool + heat) / 2.0
        cool, heat = mid + gap, mid - gap
    cool_lower = cool - d.range_low_limit * d.slider
    cool_upper = cool + d.range_high_limit * d.slider
    heat_lower = heat - d.range_low_limit * d.slider
    heat_upper = heat + d.range_high_limit * d.slider
    if heat_upper + gap > cool_lower - gap:
        mid = (cool_lower + heat_upper) / 2.0
        cool_lower = min(mid + gap, cool)
        heat_upper = max(mid - gap, heat)
    return {HVACMode.COOLING: ComfortBand(cool, cool_lower, cool_upper),
            HVACMode.HEATING: ComfortBand(heat, heat_lower, heat_upper)}


class AmenityMetric(ABC):
    """Maps an indoor temperature trajectory to an amenity value.

    Subclass to define a custom metric for a research design. Both methods
    receive ``temps`` of shape (n_candidates, n_substeps + 1): one row of
    indoor air temperatures per candidate power level, with column 0 at the
    start of the interval.

    The feasible quantity range is every power level whose violation is
    within ``tolerance`` of the smallest achievable violation. For the range
    to be an interval, ``violation`` should be convex in the power level; the
    built-in metrics are, because temperatures are affine in power.
    """
    name: str = ""
    unit: str = ""

    def __init__(self, tolerance: float = 0.0):
        self.tolerance = tolerance

    @abstractmethod
    def evaluate(self, temps: np.ndarray, band: ComfortBand, substep_minutes: float) -> np.ndarray:
        """Returns the amenity value of each candidate."""

    @abstractmethod
    def violation(self, temps: np.ndarray, band: ComfortBand, substep_minutes: float) -> np.ndarray:
        """Returns a non-negative comfort violation of each candidate; zero
        means the candidate is fully acceptable."""


class EndOfIntervalDeviation(AmenityMetric):
    """Indoor air temperature at the end of the interval minus the setpoint
    [F]. Signed: positive is warmer than the setpoint."""
    name = "end_of_interval_deviation"
    unit = "degF"

    def evaluate(self, temps, band, substep_minutes):
        return temps[:, -1] - band.setpoint

    def violation(self, temps, band, substep_minutes):
        return band.excursion(temps[:, -1])


class DegreeMinutesOutsideBand(AmenityMetric):
    """Time-integrated temperature excursion outside the comfort band over the
    interval [F*min]. Zero whenever the house stays inside the band."""
    name = "degree_minutes_outside_band"
    unit = "degF*min"

    def evaluate(self, temps, band, substep_minutes):
        excursion = band.excursion(temps)
        # trapezoidal integration over the substeps
        return substep_minutes * (excursion.sum(axis=1) - 0.5 * (excursion[:, 0] + excursion[:, -1]))

    def violation(self, temps, band, substep_minutes):
        return self.evaluate(temps, band, substep_minutes)


AMENITY_METRICS = {metric.name: metric for metric in (EndOfIntervalDeviation, DegreeMinutesOutsideBand)}


def resolve_amenity_metric(metric: str | AmenityMetric) -> AmenityMetric:
    if isinstance(metric, AmenityMetric):
        return metric
    if metric in AMENITY_METRICS:
        return AMENITY_METRICS[metric]()
    raise ValueError(f"Unknown amenity metric '{metric}'; choose one of "
                     f"{sorted(AMENITY_METRICS)} or pass an AmenityMetric instance")


# ---------------------------------------------------------------------------
# Task 2 output: flexibility
# ---------------------------------------------------------------------------

@dataclass
class AmenityPoint:
    """One feasible power level and its amenity value."""
    q_kw: float
    amenity: float


@dataclass
class IntervalFlexibility:
    """Flexibility of the HVAC system over one market interval.

    Attributes:
        start: Interval start.
        end: Interval end.
        mode: Mode serving the interval. OFF when the house has no equipment
            for the needed mode.
        q_min_kw: Minimum feasible average power [kW].
        q_max_kw: Maximum feasible average power [kW].
        q_baseline_kw: Average power when tracking the customer setpoint with
            no price consideration [kW].
        q_capacity_kw: Electric power at full output [kW].
        comfort_band: Comfort band used for the interval.
        amenity_map: Amenity value at power levels spanning the physical
            range [0, q_capacity], in increasing order of power, always
            including q_min, q_baseline, and q_max. Points outside
            [q_min, q_max] show the amenity cost of leaving the comfort band.
        baseline_amenity: Amenity value at the baseline power.
        baseline_end_temp: Indoor air temperature at the end of the interval
            at the baseline power [F].
        comfort_feasible: Whether some power level keeps the comfort
            violation at zero. When False, the range collapses onto the power
            levels that minimize the violation.
    """
    start: dt.datetime
    end: dt.datetime
    mode: HVACMode
    q_min_kw: float
    q_max_kw: float
    q_baseline_kw: float
    q_capacity_kw: float
    comfort_band: ComfortBand
    amenity_map: list[AmenityPoint]
    baseline_amenity: float
    baseline_end_temp: float
    comfort_feasible: bool


@dataclass
class HVACFlexibility:
    """Flexibility of the HVAC system over a market horizon (Task 2 output)."""
    observation: HVACObservation
    horizon: MarketHorizon
    amenity_metric: str
    amenity_unit: str
    intervals: list[IntervalFlexibility]

    @property
    def q_min_kw(self) -> list[float]:
        return [i.q_min_kw for i in self.intervals]

    @property
    def q_max_kw(self) -> list[float]:
        return [i.q_max_kw for i in self.intervals]

    @property
    def q_baseline_kw(self) -> list[float]:
        return [i.q_baseline_kw for i in self.intervals]


# ---------------------------------------------------------------------------
# Task 2: define flexibility
# ---------------------------------------------------------------------------

class HVACFlexibilityModel:
    """Defines HVAC flexibility over a market horizon from an observation.

    For each interval, the model:

    1. Simulates the house with the HVAC off and picks the mode (cooling if
       the free-floating temperature ends above the midpoint between the
       cooling and heating bands, heating otherwise).
    2. Exploits linearity: holding an average HVAC power q over the interval,
       the temperature trajectory is the free trajectory plus q times the unit
       response, so any candidate q is evaluated without re-simulating.
    3. Finds the feasible range [Q_min, Q_max] within [0, capacity] using the
       amenity metric's violation, the baseline as the power that ends the
       interval at the setpoint, and samples the amenity map over
       [0, capacity].
    4. Carries the state at the end of the interval under the baseline power
       into the next interval.

    Each interval's flexibility is therefore conditional on all earlier
    intervals following the baseline; coupling between intervals (e.g.
    pre-cooling followed by coasting) is not represented.

    Args:
        amenity_metric: Name of a built-in metric ("end_of_interval_deviation"
            or "degree_minutes_outside_band") or an AmenityMetric instance.
        substep: Simulation step within an interval. Only affects metrics
            that look inside the interval; the end state is exact.
        n_map_points: Number of evenly spaced points in each interval's
            amenity map, before adding q_min, q_baseline, and q_max.
        n_search_points: Grid size for locating the feasible range before
            refining its edges by bisection.
    """

    def __init__(self,
                 amenity_metric: str | AmenityMetric = EndOfIntervalDeviation.name,
                 substep: dt.timedelta = dt.timedelta(minutes=1),
                 n_map_points: int = 11,
                 n_search_points: int = 101):
        self.metric = resolve_amenity_metric(amenity_metric)
        self.substep = substep
        self.n_map_points = n_map_points
        self.n_search_points = n_search_points

    def define_flexibility(self,
                           observation: HVACObservation,
                           definition: HVACDefinition,
                           weather: WeatherForecast,
                           house: HouseForecast,
                           horizon: MarketHorizon) -> HVACFlexibility:
        """Defines flexibility for every interval of the horizon.

        Args:
            observation (HVACObservation): Current state from an observer.
            definition (HVACDefinition): Fixed device definition.
            weather (WeatherForecast): Weather covering the horizon.
            house (HouseForecast): House conditions covering the horizon.
            horizon (MarketHorizon): Market intervals to define flexibility for.

        Returns:
            HVACFlexibility: one IntervalFlexibility per market interval
        """
        etp = ETPModel(definition)
        n_substeps = max(1, round(horizon.interval / self.substep))
        dt_h = horizon.interval.total_seconds() / 3600.0 / n_substeps
        mass_temp = observation.mass_temp
        if mass_temp is None:
            mass_temp = observation.indoor_air_temp
        x = np.array([observation.indoor_air_temp, mass_temp], dtype=float)

        intervals = []
        for t0, t1 in horizon.intervals():
            interval, x = self._define_interval(etp, definition, x,
                                                weather.mean_over(t0, t1),
                                                house.mean_over(t0, t1),
                                                t0, t1, dt_h, n_substeps)
            intervals.append(interval)
        return HVACFlexibility(observation=observation,
                               horizon=horizon,
                               amenity_metric=self.metric.name,
                               amenity_unit=self.metric.unit,
                               intervals=intervals)

    def _define_interval(self, etp, definition, x, weather, house, t0, t1, dt_h, n_substeps):
        substep_minutes = dt_h * 60.0
        free = etp.simulate(x, etp.forcing(weather.outdoor_air_temp, house.internal_gain, weather.solar_flux),
                            dt_h, n_substeps)
        bands = comfort_bands(house.cooling_setpoint, house.heating_setpoint, definition)
        midpoint = (bands[HVACMode.COOLING].lower + bands[HVACMode.HEATING].upper) / 2.0
        mode = HVACMode.COOLING if free[-1, 0] >= midpoint else HVACMode.HEATING
        band = bands[mode]
        equipment = equipment_performance(definition, mode, weather.outdoor_air_temp, weather.humidity)

        if equipment is None:
            return self._fixed_interval(t0, t1, HVACMode.OFF, band, free, 0.0, 0.0, substep_minutes), free[-1]

        if not equipment.electric:
            # Gas heat tracks the setpoint but offers no electric flexibility
            unit = etp.simulate(np.zeros(2), etp.hvac_forcing(1.0), dt_h, n_substeps)
            heat = _track(band.setpoint, free[-1, 0], unit[-1, 0], 0.0, equipment.thermal_capacity)
            trajectory = free + heat * unit
            return self._fixed_interval(t0, t1, mode, band, trajectory, 0.0, 0.0, substep_minutes), trajectory[-1]

        unit = etp.simulate(np.zeros(2), etp.hvac_forcing(equipment.heat_per_kw), dt_h, n_substeps)
        q_cap = equipment.q_capacity_kw
        q_track = _track(band.setpoint, free[-1, 0], unit[-1, 0], 0.0, q_cap)
        participating = (definition.cooling_participating if mode == HVACMode.COOLING
                         else definition.heating_participating)

        def temps(q):
            return free[None, :, 0] + np.atleast_1d(q)[:, None] * unit[None, :, 0]

        if participating:
            q_min, q_max, feasible = self._feasible_range(temps, q_cap, band, substep_minutes)
            q_base = min(max(q_track, q_min), q_max)
        else:
            q_min = q_max = q_base = q_track
            feasible = self.metric.violation(temps(q_base), band, substep_minutes)[0] <= 0.0

        q_map = np.unique(np.concatenate([np.linspace(0.0, q_cap, self.n_map_points), [q_min, q_base, q_max]]))
        amenity = self.metric.evaluate(temps(q_map), band, substep_minutes)
        end_state = free[-1] + q_base * unit[-1]
        interval = IntervalFlexibility(
            start=t0, end=t1, mode=mode,
            q_min_kw=float(q_min), q_max_kw=float(q_max), q_baseline_kw=float(q_base),
            q_capacity_kw=float(q_cap), comfort_band=band,
            amenity_map=[AmenityPoint(float(q), float(a)) for q, a in zip(q_map, amenity)],
            baseline_amenity=float(self.metric.evaluate(temps(q_base), band, substep_minutes)[0]),
            baseline_end_temp=float(end_state[0]),
            comfort_feasible=bool(feasible))
        return interval, end_state

    def _feasible_range(self, temps, q_cap, band, substep_minutes) -> tuple[float, float, bool]:
        """Returns (q_min, q_max, comfort_feasible) within [0, q_cap].

        The feasible range is every power level whose violation is within the
        metric's tolerance of the minimum violation. The minimum is located on
        a grid and refined by golden-section search; each edge is found by
        walking outward along the grid and bisecting the first unacceptable
        step.
        """
        def violation(q):
            return self.metric.violation(temps(q), band, substep_minutes)

        grid = np.linspace(0.0, q_cap, self.n_search_points)
        v = violation(grid)
        i = int(np.argmin(v))
        q_best = _golden_section_min(lambda q: violation(q)[0],
                                     grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)])
        v_best = float(violation(q_best)[0])
        if v[i] < v_best:
            q_best, v_best = float(grid[i]), float(v[i])
        threshold = v_best + self.metric.tolerance + 1e-9 * (1.0 + abs(v_best))
        acceptable_grid = v <= threshold

        def acceptable(q):
            return violation(q)[0] <= threshold

        def edge(outward_indices):
            good = q_best
            for j in outward_indices:
                if not acceptable_grid[j]:
                    return _bisect(acceptable, bad=grid[j], good=good)
                good = grid[j]
            return good

        q_min = edge(np.flatnonzero(grid < q_best)[::-1])
        q_max = edge(np.flatnonzero(grid > q_best))
        return float(q_min), float(q_max), v_best <= 1e-9

    def _fixed_interval(self, t0, t1, mode, band, trajectory, q, q_cap, substep_minutes) -> IntervalFlexibility:
        """Interval with no electrical flexibility: one operating point."""
        temps = trajectory[None, :, 0]
        amenity = float(self.metric.evaluate(temps, band, substep_minutes)[0])
        return IntervalFlexibility(
            start=t0, end=t1, mode=mode,
            q_min_kw=q, q_max_kw=q, q_baseline_kw=q, q_capacity_kw=q_cap,
            comfort_band=band,
            amenity_map=[AmenityPoint(q, amenity)],
            baseline_amenity=amenity,
            baseline_end_temp=float(trajectory[-1, 0]),
            comfort_feasible=bool(self.metric.violation(temps, band, substep_minutes)[0] <= 0.0))


def _track(target: float, free_end: float, unit_end: float, low: float, high: float) -> float:
    """Returns the input, clamped to [low, high], that ends the interval at the
    target temperature."""
    if abs(unit_end) < 1e-12:
        return low
    return min(max((target - free_end) / unit_end, low), high)


def _bisect(acceptable, bad: float, good: float, iterations: int = 40) -> float:
    """Narrows the boundary between an unacceptable and an acceptable value,
    returning the acceptable side."""
    for _ in range(iterations):
        mid = (bad + good) / 2.0
        if acceptable(mid):
            good = mid
        else:
            bad = mid
    return good


def _golden_section_min(f, low: float, high: float, iterations: int = 60) -> float:
    """Returns the minimizer of a convex function on [low, high]."""
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = low, high
    c, d = b - ratio * (b - a), a + ratio * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(iterations):
        if fc <= fd:
            b, d, fd = d, c, fc
            c = b - ratio * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + ratio * (b - a)
            fd = f(d)
    return (a + b) / 2.0


# ---------------------------------------------------------------------------
# Task 1: observers
# ---------------------------------------------------------------------------

class HVACObserver(ABC):
    """Produces HVACObservations from some source of device state."""
    source: ObservationMode

    @abstractmethod
    def observe(self, sim_time: dt.datetime) -> HVACObservation:
        """Returns the device state at the simulation time."""


class GridLABDConnection(Protocol):
    """Co-simulation connection (HELICS, FNCS, or direct API adapter).

    Keys use the TESP "object#property" convention.
    """
    def get_value(self, key: str) -> Any: ...


class GridLABDHVACObserver(HVACObserver):
    """Physics-based (full) observation: reads the GridLAB-D house object.

    GridLAB-D house properties read:
        air_temperature [degF], mass_temperature [degF],
        cooling_setpoint [degF], heating_setpoint [degF], hvac_load [kW],
        system_mode {COOL, HEAT, AUX, OFF}, power_state {ON, OFF},
        thermostat_mode {AUTO, COOL, HEAT, OFF}

    The mode comes from system_mode while the system runs. When it is idle,
    thermostat_mode is used if it restricts the system to one mode; otherwise
    the mode is inferred from the indoor temperature relative to the setpoint
    midpoint, as in DSO+T. power_state is only used when system_mode is
    unavailable.

    Args:
        connection (GridLABDConnection): Co-simulation connection.
        house_name (str): Name of the GridLAB-D house object.
    """
    source = ObservationMode.GRIDLABD

    def __init__(self, connection: GridLABDConnection, house_name: str):
        self.connection = connection
        self.house_name = house_name

    def _raw(self, prop: str) -> Any:
        raw = self.connection.get_value(f"{self.house_name}#{prop}")
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            return None
        return raw

    def _float(self, prop: str, required: bool = True) -> float | None:
        raw = self._raw(prop)
        if raw is None:
            if required:
                raise ValueError(f"GridLAB-D property {self.house_name}#{prop} has no value")
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        return parse_number(str(raw).strip())

    def _str(self, prop: str) -> str | None:
        raw = self._raw(prop)
        return None if raw is None else str(raw).strip().upper()

    def observe(self, sim_time: dt.datetime) -> HVACObservation:
        air_temp = self._float("air_temperature")
        cooling_setpoint = self._float("cooling_setpoint")
        heating_setpoint = self._float("heating_setpoint")

        system_mode = self._str("system_mode")
        if system_mode == "COOL":
            mode, hvac_on = HVACMode.COOLING, True
        elif system_mode in ("HEAT", "AUX"):
            mode, hvac_on = HVACMode.HEATING, True
        else:
            if system_mode == "OFF":
                hvac_on = False
            else:
                hvac_on = self._str("power_state") == "ON"
            thermostat_mode = self._str("thermostat_mode")
            if thermostat_mode == "COOL":
                mode = HVACMode.COOLING
            elif thermostat_mode == "HEAT":
                mode = HVACMode.HEATING
            elif thermostat_mode == "OFF":
                mode = HVACMode.OFF
            else:
                mode = infer_mode(air_temp, cooling_setpoint, heating_setpoint)

        return HVACObservation(timestamp=sim_time,
                               indoor_air_temp=air_temp,
                               hvac_mode=mode,
                               hvac_on=hvac_on,
                               cooling_setpoint=cooling_setpoint,
                               heating_setpoint=heating_setpoint,
                               hvac_kw=self._float("hvac_load"),
                               mass_temp=self._float("mass_temperature", required=False),
                               source=self.source)


class PhysicsStubHVACObserver(HVACObserver):
    """Stub observation from a light physics model (agent-based approximation).

    Stands in for a GridLAB-D house: evolves its own two-node ETP model with
    thermostat deadband cycling, driven by weather and house forecasts that are
    treated as ground truth. The thermostat follows the house forecast
    setpoints.

    By default the stub house is identical to the agent's definition, which
    gives the flexibility model a perfect model of the device. Use
    parameter_scaling to make the stub house differ, e.g.
    ``{"UA": 1.1, "CM": 0.9}``.

    Args:
        definition (HVACDefinition): The agent's definition of the device.
        weather (WeatherForecast): Weather driving the stub house.
        house (HouseForecast): Internal gains and setpoints driving it.
        start_time (dt.datetime): Time of the initial state.
        initial_air_temp (float): Initial indoor air temperature [F].
        initial_mass_temp (float, optional): Initial mass temperature [F].
            Defaults to the air temperature.
        substep (dt.timedelta): Thermostat and integration step.
        parameter_scaling (dict, optional): Multipliers for numeric
            HVACDefinition fields of the stub house.
    """
    source = ObservationMode.PHYSICS_STUB

    def __init__(self,
                 definition: HVACDefinition,
                 weather: WeatherForecast,
                 house: HouseForecast,
                 start_time: dt.datetime,
                 initial_air_temp: float,
                 initial_mass_temp: float | None = None,
                 substep: dt.timedelta = dt.timedelta(minutes=1),
                 parameter_scaling: dict[str, float] | None = None):
        scaled = {}
        for name, factor in (parameter_scaling or {}).items():
            value = getattr(definition, name)  # raises AttributeError for unknown names
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"Cannot scale non-numeric HVACDefinition field '{name}'")
            scaled[name] = value * factor
        self.definition = replace(definition, **scaled)
        self.weather = weather
        self.house = house
        self.substep = substep
        self._etp = ETPModel(self.definition)
        self._time = start_time
        mass_temp = initial_air_temp if initial_mass_temp is None else initial_mass_temp
        self._x = np.array([initial_air_temp, mass_temp], dtype=float)
        self._hvac_on = False
        self._mode = HVACMode.OFF
        self._hvac_kw = 0.0

    def observe(self, sim_time: dt.datetime) -> HVACObservation:
        self.advance_to(sim_time)
        house = self.house.at(sim_time)
        mode = self._mode if self._hvac_on else infer_mode(self._x[0], house.cooling_setpoint,
                                                            house.heating_setpoint)
        return HVACObservation(timestamp=sim_time,
                               indoor_air_temp=float(self._x[0]),
                               hvac_mode=mode,
                               hvac_on=self._hvac_on,
                               cooling_setpoint=house.cooling_setpoint,
                               heating_setpoint=house.heating_setpoint,
                               hvac_kw=self._hvac_kw,
                               mass_temp=float(self._x[1]),
                               source=self.source)

    def advance_to(self, sim_time: dt.datetime) -> None:
        """Evolves the stub house up to the simulation time."""
        if sim_time < self._time:
            raise ValueError(f"Cannot move the stub backward from {self._time} to {sim_time}")
        while self._time < sim_time:
            step = min(self.substep, sim_time - self._time)
            self._step(step)
            self._time += step

    def _step(self, step: dt.timedelta) -> None:
        d = self.definition
        weather = self.weather.at(self._time)
        house = self.house.at(self._time)
        air_temp = self._x[0]
        half_band = d.deadband / 2.0

        if self._hvac_on and (
                (self._mode == HVACMode.COOLING and air_temp < house.cooling_setpoint - half_band)
                or (self._mode == HVACMode.HEATING and air_temp > house.heating_setpoint + half_band)):
            self._hvac_on = False
        if not self._hvac_on:
            if d.has_cooling and air_temp > house.cooling_setpoint + half_band:
                self._hvac_on, self._mode = True, HVACMode.COOLING
            elif d.heating_fuel != HeatingFuel.NONE and air_temp < house.heating_setpoint - half_band:
                self._hvac_on, self._mode = True, HVACMode.HEATING

        heat, self._hvac_kw = 0.0, 0.0
        if self._hvac_on:
            equipment = equipment_performance(d, self._mode, weather.outdoor_air_temp, weather.humidity)
            if equipment.electric:
                self._hvac_kw = equipment.q_capacity_kw
                heat = equipment.q_capacity_kw * equipment.heat_per_kw
            else:
                heat = equipment.thermal_capacity

        b = (self._etp.forcing(weather.outdoor_air_temp, house.internal_gain, weather.solar_flux)
             + self._etp.hvac_forcing(heat))
        self._x = self._etp.simulate(self._x, b, step.total_seconds() / 3600.0, 1)[-1]


class StatisticalStubHVACObserver(HVACObserver):
    """Stub observation from a statistical approximation (placeholder).

    Intended to estimate the indoor air temperature, HVAC state, and HVAC
    power from large datasets such as ResStock, conditioned on time, weather,
    and building archetype, and to report per-field standard deviations in
    HVACObservation.uncertainty. Not implemented until the dataset is
    imported.

    Args:
        dataset (Any, optional): Source dataset or path.
        archetype (dict, optional): Building archetype descriptors used to
            select or condition the statistical model.
    """
    source = ObservationMode.STATISTICAL_STUB

    def __init__(self, dataset: Any = None, archetype: dict | None = None):
        self.dataset = dataset
        self.archetype = archetype

    def observe(self, sim_time: dt.datetime) -> HVACObservation:
        raise NotImplementedError("Statistical HVAC observation is pending import of the "
                                  "ResStock-derived dataset")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class HVACAgentStub:
    """HVAC agent performing only Observe and Define Flexibility.

    For the day-ahead market, call update() every hour with refreshed
    forecasts covering the next 48 hours; for a real-time market, pass
    MarketHorizon.real_time(sim_time).

    Args:
        name (str): Agent name.
        definition (HVACDefinition): Fixed device definition.
        observer (HVACObserver): Source of device state (GridLAB-D or stub).
        flexibility_model (HVACFlexibilityModel, optional): Defaults to the
            end-of-interval deviation metric.
    """

    def __init__(self,
                 name: str,
                 definition: HVACDefinition,
                 observer: HVACObserver,
                 flexibility_model: HVACFlexibilityModel | None = None):
        self.name = name
        self.definition = definition
        self.observer = observer
        self.flexibility_model = flexibility_model or HVACFlexibilityModel()
        self.observation: HVACObservation | None = None
        self.flexibility: HVACFlexibility | None = None

    def observe(self, sim_time: dt.datetime) -> HVACObservation:
        """Task 1: retrieves the current device state."""
        self.observation = self.observer.observe(sim_time)
        return self.observation

    def define_flexibility(self,
                           weather: WeatherForecast,
                           house: HouseForecast,
                           horizon: MarketHorizon) -> HVACFlexibility:
        """Task 2: defines flexibility from the latest observation."""
        if self.observation is None:
            raise RuntimeError(f"{self.name}: observe() must be called before define_flexibility()")
        self.flexibility = self.flexibility_model.define_flexibility(
            self.observation, self.definition, weather, house, horizon)
        return self.flexibility

    def update(self,
               sim_time: dt.datetime,
               weather: WeatherForecast,
               house: HouseForecast,
               horizon: MarketHorizon | None = None) -> HVACFlexibility:
        """Observes, then defines flexibility over the horizon (default: the
        48-hour day-ahead horizon starting at sim_time)."""
        self.observe(sim_time)
        return self.define_flexibility(weather, house, horizon or MarketHorizon.day_ahead(sim_time))
