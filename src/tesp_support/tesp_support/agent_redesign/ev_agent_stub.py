# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: ev_agent_stub.py
"""EV device agent: Observe, Define Flexibility, and Control.

1. Observe - retrieve the current state of the vehicle and charger.
   Interchangeable observers provide the state:

   - ``GridLABDEVObserver``: reads the GridLAB-D evcharger_det object
     (physics-based, full).
   - ``PhysicsStubEVObserver``: evolves a light battery model driven by the
     travel schedule (stub, agent-based approximation).
   - ``StatisticalStubEVObserver``: placeholder for an approximation built
     from travel and charging datasets (stub).

2. Define Flexibility - ``EVFlexibilityModel`` takes the observation and the
   fixed device definition (including the travel schedule) and returns for
   every interval of a market horizon:

   - the feasible quantity range [Q_min, Q_max] in kW,
   - an amenity mapping from power levels to a user-selectable amenity
     metric, and
   - the baseline operating point (uncontrolled charging: full rate from
     plug-in until full, as in DSO+T get_uncntrl_ev_load).

   Q_min follows the lowest feasible state-of-charge trajectory: charge as
   late as possible (and, for V2G, discharge as early as possible) while
   still meeting every departure target. Any schedule with Q >= Q_min in
   every interval therefore meets every departure target. Q_max is charging
   at the maximum rate from that lowest state; Q_max is not jointly
   achievable in every interval (the vehicle stops charging when full).

Control translation (after market clearing) - ``EVChargeController``
converts a cleared quantity (average power over a market interval) into a
charger setpoint, and an ``EVActuator`` writes it:

   - ``GridLABDEVActuator``: writes the evcharger_det charge rate.
   - ``PhysicsStubEVObserver``: also acts as the actuator for the stub vehicle.

Not part of the agent: customer preference curves (``preference_curve.py``)
and bid curves (``bid_formulation.py``) are device-agnostic and formed from
``EVFlexibility.market_flexibility()``.
---
Implementation: 

from tesp_support.dsot import bid_formulation as bidding
from tesp_support.dsot import preference_curve as pc

definition = EVDefinition.config(ev_config)          # same dict as the DSO+T agent
NEW! DSOT EV agent assumed constant charge rate not reflective of real ev charge curves
    charge_curve : generic_taper, constant, or from file
    examples: 
        # Vehicle-specific curve in kW (vehicle limit, combined with charger rating)
        {"charge_curve": [[0, 11.0], [0.7, 11.0], [0.9, 5.0], [1.0, 1.5]], "charge_curve_units": "kw"}

        # From a file (CSV columns: soc,value; SoC in percent is converted)
        {"charge_curve": "curves/model_y.csv"}

bidder = bidding.PreferenceBidder(
    pc.PreferenceParameters.from_config(ev_config, default_k=definition.slider),
    bidding.BidConfig.from_config(ev_config))

# Stub (closes the loop by itself)
stub = PhysicsStubEVObserver(definition, start_time, initial_soc=0.4)
agent = EVAgentStub("ev_1", definition, stub, bidder=bidder)

# GridLAB-D
agent = EVAgentStub(name, definition,
                    GridLABDEVObserver(conn, charger_name, definition),
                    bidder=bidder, actuator=GridLABDEVActuator(conn, charger_name))

agent.formulate_bid_da(t, price_forecast)        # hourly
bid = agent.formulate_bid_rt(t)                   # every 5 min
command = agent.clear_rt(cleared_price)

---
Unit conventions:

Energy - [kWh]
Power - [kW], consumption positive (V2G discharge negative)
State of charge - fraction [0-1] unless noted (GridLAB-D reports percent)
Times of day - HHMM, as in DSO+T configuration
---
"""

import datetime as dt
import logging
import math
import bisect
import csv
import functools
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from typing import Any, Protocol

import numpy as np

from tesp_support.api.parse_helpers import parse_number
from tesp_support.agent_redesign import bid_formulation as bidding  

logger = logging.getLogger(__name__)

_TOL = 1e-9


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ChargingMode(Enum):
    V1G = "V1G"  # managed charging only
    V2G = "V2G"  # charging and discharging


class BoundaryCondition(Enum):
    """Customer's departure requirement, as in DSO+T."""
    FULL = "full"
    JUST_ENOUGH = "just_enough"
    SLIDER_BASED = "slider_based"


class ObservationMode(Enum):
    GRIDLABD = "gridlabd"
    PHYSICS_STUB = "physics_stub"
    STATISTICAL_STUB = "statistical_stub"


# ---------------------------------------------------------------------------
# Travel schedule
# ---------------------------------------------------------------------------

def _hhmm_to_timedelta(hhmm: float) -> dt.timedelta:
    value = int(round(hhmm))
    hours, minutes = divmod(value, 100)
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"invalid HHMM time {hhmm}")
    return dt.timedelta(hours=hours, minutes=minutes)

# ---------------------------------------------------------------------------
# Charge curves
# ---------------------------------------------------------------------------

class CurveUnits(Enum):
    FRACTION = "fraction"  # fraction of the charger rating
    KW = "kw"              # vehicle acceptance limit [kW]; effective limit is min(curve, charger rating)


@dataclass(frozen=True)
class ChargeCurve:
    """Maximum grid-side charging power as a piecewise-linear function of
    state of charge, constant beyond the first and last points.

    Attributes:
        soc: Breakpoints [fraction], strictly increasing, within [0, 1].
        value: Limit at each breakpoint, in `units`.
        units: FRACTION of the charger rating (0 to 1), or KW: the vehicle's
            own acceptance limit, combined with the charger rating as
            min(curve, rating).
        name: Optional label.
    """
    soc: tuple[float, ...]
    value: tuple[float, ...]
    units: CurveUnits = CurveUnits.FRACTION
    name: str = ""

    def __post_init__(self):
        soc = tuple(float(s) for s in self.soc)
        value = tuple(float(v) for v in self.value)
        units = CurveUnits(self.units)
        if len(soc) < 2 or len(soc) != len(value):
            raise ValueError(f"charge curve needs >= 2 matching soc/value points, got {len(soc)}/{len(value)}")
        if any(b <= a for a, b in zip(soc, soc[1:])) or soc[0] < 0.0 or soc[-1] > 1.0:
            raise ValueError(f"charge curve soc must be strictly increasing within [0, 1], got {soc}")
        if any(v < 0.0 for v in value):
            raise ValueError(f"charge curve values must be >= 0, got {value}")
        if units == CurveUnits.FRACTION and any(v > 1.0 for v in value):
            raise ValueError(f"FRACTION charge curve values must be <= 1, got {value}")
        object.__setattr__(self, "soc", soc)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "units", units)

    def raw_kw(self, soc: float, rating_kw: float) -> float:
        """Curve value at a state of charge in kW, before applying the charger rating."""
        v = float(np.interp(soc, self.soc, self.value))
        return v * rating_kw if self.units == CurveUnits.FRACTION else v

    def limit_kw(self, soc: float, rating_kw: float) -> float:
        """Maximum grid-side charging power at a state of charge [kW]."""
        return min(self.raw_kw(soc, rating_kw), rating_kw)

    @classmethod
    def from_points(cls, points, units: CurveUnits | str = CurveUnits.FRACTION, name: str = "") -> 'ChargeCurve':
        """From (soc, value) pairs, in any order."""
        pts = sorted((float(s), float(v)) for s, v in points)
        return cls(tuple(s for s, _ in pts), tuple(v for _, v in pts), CurveUnits(units), name)

    @classmethod
    def from_dict(cls, data: dict, units: CurveUnits | str | None = None) -> 'ChargeCurve':
        """From {"soc": [...], "value": [...]} or {"points": [[soc, value], ...]},
        with optional "units" and "name"."""
        pts = data["points"] if "points" in data else list(zip(data["soc"], data["value"]))
        return cls.from_points(_soc_fraction(pts), units or data.get("units", "fraction"), data.get("name", ""))

    @classmethod
    def from_file(cls, path: str | Path, units: CurveUnits | str | None = None) -> 'ChargeCurve':
        """From a .json file (dict as in from_dict, or a list of [soc, value]
        pairs) or a .csv file with 'soc' and 'value' columns (optional
        'units' column). SoC given in percent is converted."""
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return cls.from_points(_soc_fraction(data), units or "fraction", path.stem)
            return cls.from_dict({"name": path.stem, **data}, units)
        if suffix == ".csv":
            with path.open(newline="") as fh:
                rows = list(csv.DictReader(fh))
            if not rows or not {"soc", "value"} <= set(rows[0]):
                raise ValueError(f"{path}: CSV charge curve needs 'soc' and 'value' columns")
            pts = [(r["soc"], r["value"]) for r in rows]
            return cls.from_points(_soc_fraction(pts), units or rows[0].get("units") or "fraction", path.stem)
        raise ValueError(f"{path}: charge curve files must be .json or .csv")


def _soc_fraction(points) -> list[tuple[float, float]]:
    """Converts SoC to fractions if the points are given in percent."""
    pts = [(float(s), float(v)) for s, v in points]
    top = max(s for s, _ in pts)
    if top > 1.0:
        if top > 100.0:
            raise ValueError(f"charge curve SoC above 100: {top}")
        logger.info("Charge curve SoC appears to be in percent; converting to fractions")
        pts = [(s / 100.0, v) for s, v in pts]
    return pts


# Generic default: full power to 80% SoC, then a linear taper to 20% of full
# power at 100%. Illustrative, not calibrated; prefer measured curves.
GENERIC_TAPER = ChargeCurve((0.0, 0.8, 1.0), (1.0, 1.0, 0.2), name="generic_taper")
CONSTANT = ChargeCurve((0.0, 1.0), (1.0, 1.0), name="constant")  # previous behavior
CHARGE_CURVES: dict[str, ChargeCurve] = {c.name: c for c in (GENERIC_TAPER, CONSTANT)}


def register_charge_curve(curve: ChargeCurve, name: str | None = None) -> ChargeCurve:
    """Adds a curve to CHARGE_CURVES so configurations can refer to it by name."""
    name = name or curve.name
    if not name:
        raise ValueError("a registered charge curve needs a name")
    curve = curve if curve.name == name else replace(curve, name=name)
    CHARGE_CURVES[name] = curve
    return curve


def resolve_charge_curve(spec: Any = None, units: CurveUnits | str | None = None) -> ChargeCurve:
    """Turns a configuration value into a ChargeCurve.

    None -> GENERIC_TAPER; ChargeCurve -> itself; str -> registered name or a
    .json/.csv path; dict -> ChargeCurve.from_dict; list of (soc, value) pairs
    -> ChargeCurve.from_points.
    """
    if spec is None:
        return GENERIC_TAPER
    if isinstance(spec, ChargeCurve):
        return spec
    if isinstance(spec, str):
        if spec in CHARGE_CURVES:
            return CHARGE_CURVES[spec]
        if Path(spec).suffix.lower() in (".json", ".csv"):
            return ChargeCurve.from_file(spec, units)
        raise ValueError(f"Unknown charge curve '{spec}'; registered: {sorted(CHARGE_CURVES)}, "
                         f"or give a .json/.csv path")
    if isinstance(spec, dict):
        return ChargeCurve.from_dict(spec, units)
    return ChargeCurve.from_points(_soc_fraction(spec), units or "fraction")


class ChargeProfile:
    """Charging dynamics in stored energy E [kWh] for one vehicle and charger:

        dE/dt = efficiency * min(curve(E / capacity), setpoint)

    The effective power is piecewise linear in E, so time and energy along a
    charging path have closed forms within each segment:
        constant power f:      t = dE / (eta f)
        f(E) = a + b E:        t = ln(f(E2) / f(E1)) / (eta b)
    """

    def __init__(self, curve: ChargeCurve, rating_kw: float, efficiency: float, capacity_kwh: float):
        self.curve = curve
        self.rating_kw = rating_kw
        self.eta = efficiency
        self.capacity_kwh = capacity_kwh
        self._full = self._build(rating_kw)

    def _build(self, limit_kw: float) -> tuple[list[float], list[float]]:
        """Breakpoints (E, kW) of min(curve, limit), with crossings inserted."""
        socs = sorted({0.0, 1.0, *self.curve.soc})
        E = [s * self.capacity_kwh for s in socs]
        v = [self.curve.raw_kw(s, self.rating_kw) for s in socs]
        pts_E, pts_v = [E[0]], [min(v[0], limit_kw)]
        for (e1, v1), (e2, v2) in zip(zip(E, v), zip(E[1:], v[1:])):
            if (v1 - limit_kw) * (v2 - limit_kw) < 0.0:
                pts_E.append(e1 + (limit_kw - v1) * (e2 - e1) / (v2 - v1))
                pts_v.append(limit_kw)
            pts_E.append(e2)
            pts_v.append(min(v2, limit_kw))
        return pts_E, pts_v

    def _points(self, cap_kw: float | None) -> tuple[list[float], list[float]]:
        if cap_kw is None or cap_kw >= self.rating_kw:
            return self._full
        return self._build(max(cap_kw, 0.0))

    @staticmethod
    def _line(Es, vs, i) -> tuple[float, float]:
        b = (vs[i + 1] - vs[i]) / (Es[i + 1] - Es[i])
        return vs[i] - b * Es[i], b

    def _time(self, a: float, b: float, x: float, y: float) -> float:
        fx, fy = a + b * x, a + b * y
        if fx <= _TOL or fy <= _TOL:
            return math.inf
        if abs(b) < 1e-12:
            return (y - x) / (self.eta * fx)
        return math.log(fy / fx) / (self.eta * b)

    def _advance(self, a: float, b: float, x: float, t: float) -> float:
        """Energy after charging for t hours from x within one segment (t < 0 runs backward)."""
        if abs(b) < 1e-12:
            return x + self.eta * (a + b * x) * t
        return ((a + b * x) * math.exp(self.eta * b * t) - a) / b

    def power(self, e_kwh: float, cap_kw: float | None = None) -> float:
        """Grid-side charging power at a stored energy [kW]."""
        Es, vs = self._points(cap_kw)
        return float(np.interp(e_kwh, Es, vs))

    def energy_after(self, e_start: float, hours: float, cap_kw: float | None = None) -> float:
        """Stored energy after charging at the maximum allowed rate for some hours [kWh].
        Not limited by soc_max; callers apply their own stop level."""
        Es, vs = self._points(cap_kw)
        e, t = min(max(e_start, 0.0), Es[-1]), max(hours, 0.0)
        i = min(bisect.bisect_right(Es, e) - 1, len(Es) - 2)
        while t > 0.0 and e < Es[-1]:
            a, b = self._line(Es, vs, i)
            if a + b * e <= _TOL:
                return e  # no charging power left
            end = Es[i + 1]
            t_seg = self._time(a, b, e, end)
            if t_seg >= t:
                return min(self._advance(a, b, e, t), end)
            t -= t_seg
            e = end
            i += 1
        return e

    def energy_before(self, target: float, hours: float, cap_kw: float | None = None) -> float:
        """Lowest stored energy from which charging at the maximum allowed rate
        reaches `target` within `hours` [kWh]. -inf if any energy suffices."""
        Es, vs = self._points(cap_kw)
        e, t = min(max(target, 0.0), Es[-1]), max(hours, 0.0)
        if t == 0.0:
            return e
        i = max(bisect.bisect_left(Es, e) - 1, 0)
        while True:
            a, b = self._line(Es, vs, i)
            start = Es[i]
            t_seg = self._time(a, b, start, e)
            if t_seg >= t:
                return max(self._advance(a, b, e, -t), start)
            t -= t_seg
            e = start
            if i == 0:
                return -math.inf
            i -= 1
        
                             
@dataclass(frozen=True)
class EVTravelSchedule:
    """Daily home-charging schedule as in DSO+T: the vehicle arrives home at
    arrival_home and stays home_duration seconds. Only home charging is
    modeled (the DSO+T EV agent did not model work charging either). The
    daily trip energy is drained at departure.

    Attributes:
        arrival_home: Home arrival time of day [HHMM].
        home_duration: Time at home [s]; must be under 24 hours.
        daily_miles: Miles driven between leaving home and returning.
    """
    arrival_home: float
    home_duration: float
    daily_miles: float

    def __post_init__(self):
        _hhmm_to_timedelta(self.arrival_home)
        if not 0.0 < self.home_duration < 86400.0:
            raise ValueError(f"home_duration must be in (0, 86400) s, got {self.home_duration}")
        if self.daily_miles < 0.0:
            raise ValueError(f"daily_miles must be >= 0, got {self.daily_miles}")

    def home_windows(self, start: dt.datetime, end: dt.datetime) -> list[tuple[dt.datetime, dt.datetime]]:
        """Scheduled (arrival, departure) windows overlapping [start, end), in order."""
        offset = _hhmm_to_timedelta(self.arrival_home)
        stay = dt.timedelta(seconds=self.home_duration)
        day = dt.datetime.combine(start.date(), dt.time(), tzinfo=start.tzinfo) - dt.timedelta(days=1)
        windows = []
        while day < end:
            arrive = day + offset
            depart = arrive + stay
            if depart > start and arrive < end:
                windows.append((arrive, depart))
            day += dt.timedelta(days=1)
        return windows

    def window_at(self, time: dt.datetime) -> tuple[dt.datetime, dt.datetime] | None:
        """The scheduled home window containing a time, or None if away."""
        return next((w for w in self.home_windows(time, time + dt.timedelta(seconds=1))
                     if w[0] <= time < w[1]), None)


# ---------------------------------------------------------------------------
# Task 2 constraints: device definition
# ---------------------------------------------------------------------------

@dataclass
class EVDefinition:
    """Fixed definition of the vehicle, charger, and customer requirement.

    Attributes:
        capacity_kwh: Battery capacity [kWh].
        max_charge_kw: Charger rating, grid side [kW].
        max_discharge_kw: Maximum discharging power, grid side [kW]; 0 for V1G.
        charge_efficiency: Stored energy per unit of grid energy when charging.
        discharge_efficiency: Grid energy per unit of stored energy when
            discharging (DSO+T used 1.0).
        miles_per_kwh: Vehicle efficiency.
        schedule: Home arrival and departure schedule.
        mode: V1G or V2G.
        boundary_condition: Departure requirement.
        slider: Customer flexibility setting, 0 to 1 (slider_based requirement).
        soc_min: Reserve state of charge the agent never plans below.
        soc_max: Highest state of charge the agent plans to; charging stops here.
        departure_margin: Extra trip energy required by just_enough (0.2 = 20%).
        participating: Whether the vehicle offers flexibility.
        charge_curve: Maximum charging power vs. SoC. Accepts anything
            resolve_charge_curve() accepts; defaults to GENERIC_TAPER.
        min_charge_kw: Smallest nonzero charger setpoint [kW] (e.g. ~1.4 kW
            for a 6 A J1772 minimum at 240 V). 0 = continuous.
        charge_levels: Allowed nonzero setpoints [kW] for chargers with fixed
            levels; None = continuous above min_charge_kw.
    """
    capacity_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    charge_efficiency: float
    discharge_efficiency: float
    miles_per_kwh: float
    schedule: EVTravelSchedule
    mode: ChargingMode = ChargingMode.V1G
    boundary_condition: BoundaryCondition = BoundaryCondition.FULL
    slider: float = 0.0
    soc_min: float = 0.2
    soc_max: float = 0.99
    departure_margin: float = 0.2
    participating: bool = True
    charge_curve: Any = None
    min_charge_kw: float = 0.0
    charge_levels: tuple[float, ...] | None = None

    def __post_init__(self):
        self.charge_curve = resolve_charge_curve(self.charge_curve)
        if self.capacity_kwh <= 0.0 or self.max_charge_kw <= 0.0 or self.miles_per_kwh <= 0.0:
            raise ValueError("capacity_kwh, max_charge_kw and miles_per_kwh must be > 0")
        if self.max_discharge_kw < 0.0:
            raise ValueError(f"max_discharge_kw must be >= 0, got {self.max_discharge_kw}")
        if self.mode == ChargingMode.V1G and self.max_discharge_kw > 0.0:
            raise ValueError("V1G vehicles cannot discharge; set max_discharge_kw = 0")
        for name in ("charge_efficiency", "discharge_efficiency"):
            if not 0.0 < getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in (0, 1], got {getattr(self, name)}")
        if not 0.0 <= self.soc_min < self.soc_max <= 1.0:
            raise ValueError(f"need 0 <= soc_min < soc_max <= 1, got {self.soc_min}, {self.soc_max}")
        if not 0.0 <= self.slider <= 1.0:
            raise ValueError(f"slider must be in [0, 1], got {self.slider}")
        if not 0.0 <= self.min_charge_kw <= self.max_charge_kw:
            raise ValueError(f"min_charge_kw must be in [0, max_charge_kw], got {self.min_charge_kw}")
        if self.charge_levels is not None:
            levels = tuple(sorted(float(l) for l in self.charge_levels))
            if not levels or levels[0] <= 0.0:
                raise ValueError(f"charge_levels must be positive, got {self.charge_levels}")
            self.charge_levels = levels
        # The curve must allow charging all the way to soc_max, or targets up to it are unreachable
        for s in [x for x in self.charge_curve.soc if x < self.soc_max] + [self.soc_max]:
            if self.charge_curve.limit_kw(s, self.max_charge_kw) <= _TOL:
                raise ValueError(f"charge curve '{self.charge_curve.name}' reaches zero power at "
                                 f"SoC {s:.3f}, below soc_max {self.soc_max}")
        if self.e_min + self.trip_kwh > self.e_max + _TOL:
            logger.warning("Daily trip (%.1f kWh) exceeds usable capacity (%.1f kWh); "
                           "departure target capped at soc_max", self.trip_kwh, self.e_max - self.e_min)

    @functools.cached_property
    def charge_profile(self) -> ChargeProfile:
        return ChargeProfile(self.charge_curve, self.max_charge_kw, self.charge_efficiency, self.capacity_kwh)

    @property
    def e_min(self) -> float:
        return self.soc_min * self.capacity_kwh

    @property
    def e_max(self) -> float:
        return self.soc_max * self.capacity_kwh

    @property
    def trip_kwh(self) -> float:
        return self.schedule.daily_miles / self.miles_per_kwh

    @property
    def departure_target_kwh(self) -> float:
        """Stored energy required at each home departure [kWh].

        just_enough is the reserve plus the trip with a margin; slider_based
        moves from full (slider 0) to just_enough (slider 1), as in DSO+T.
        """
        just_enough = min(self.e_min + self.trip_kwh * (1.0 + self.departure_margin), self.e_max)
        if self.boundary_condition == BoundaryCondition.FULL:
            target = self.e_max
        elif self.boundary_condition == BoundaryCondition.JUST_ENOUGH:
            target = just_enough
        else:
            target = self.e_max + (just_enough - self.e_max) * self.slider
        return min(max(target, self.e_min + self.trip_kwh), self.e_max)

    @classmethod
    def config(cls, ev_config: dict, **overrides) -> 'EVDefinition':
        """Builds a definition from a DSO+T EV agent configuration.

        Keys: max_charge [W], ev_mode, efficiency, range_miles, miles_per_kWh,
        daily_miles, arrival_home [HHMM], home_duration [s], slider_setting,
        boundary_cond, participating; optional reserved_soc,
        discharge_efficiency, charge_curve (name, .json/.csv path, dict, or
        [[soc, value], ...]), charge_curve_units, min_charge_kw,
        charge_levels_kw.
        """
        mode = ChargingMode(str(ev_config.get("ev_mode", "V1G")).strip().upper())
        max_charge_kw = float(ev_config["max_charge"]) * 0.001
        miles_per_kwh = float(ev_config["miles_per_kWh"])
        levels = ev_config.get("charge_levels_kw")
        params = dict(
            capacity_kwh=float(ev_config["range_miles"]) / miles_per_kwh,
            max_charge_kw=max_charge_kw,
            max_discharge_kw=max_charge_kw if mode == ChargingMode.V2G else 0.0,
            charge_efficiency=float(ev_config["efficiency"]),
            discharge_efficiency=float(ev_config.get("discharge_efficiency", 1.0)),
            miles_per_kwh=miles_per_kwh,
            schedule=EVTravelSchedule(arrival_home=float(ev_config["arrival_home"]),
                                      home_duration=float(ev_config["home_duration"]),
                                      daily_miles=float(ev_config["daily_miles"])),
            mode=mode,
            boundary_condition=BoundaryCondition(ev_config.get("boundary_cond", "full")),
            slider=float(ev_config.get("slider_setting", 0.0)),
            soc_min=float(ev_config.get("reserved_soc", 0.2)),
            participating=bool(ev_config.get("participating", True)),
            charge_curve=resolve_charge_curve(ev_config.get("charge_curve"),
                                              ev_config.get("charge_curve_units")),
            min_charge_kw=float(ev_config.get("min_charge_kw", 0.0)),
            charge_levels=tuple(float(l) for l in levels) if levels else None)
        params.update(overrides)
        return cls(**params)


def stored_change(definition: EVDefinition, grid_kw: float, hours: float) -> float:
    """Change in stored energy [kWh] from a grid power held for some hours."""
    if grid_kw >= 0.0:
        return grid_kw * definition.charge_efficiency * hours
    return grid_kw / definition.discharge_efficiency * hours

def grid_energy(definition: EVDefinition, stored_kwh: float) -> float:
    """Grid energy [kWh] that changes stored energy by stored_kwh."""
    if stored_kwh >= 0.0:
        return stored_kwh / definition.charge_efficiency
    return stored_kwh * definition.discharge_efficiency

def grid_power(definition: EVDefinition, stored_kwh: float, hours: float) -> float:
    """Average grid power [kW] that changes stored energy by stored_kwh over some hours."""
    return grid_energy(definition, stored_kwh) / hours if hours > 0.0 else 0.0

def _hours(delta: dt.timedelta) -> float:
    return delta.total_seconds() / 3600.0

# ---------------------------------------------------------------------------
# Task 1 output: observation
# ---------------------------------------------------------------------------

@dataclass
class EVObservation:
    """Current state of the vehicle and charger (Task 1 output).

    Attributes:
        timestamp: Simulation time of the observation.
        soc: State of charge [fraction].
        plugged_in: Whether the vehicle is at home and connected.
        charge_rate_kw: Charger setpoint, grid side [kW].
        power_kw: Measured charger power draw [kW]; negative when discharging.
        arrival_time: When the vehicle plugged in, if known.
        departure_time: Expected departure, if known. Overrides the schedule.
        source: Which observer produced this observation.
        uncertainty: Per-field standard deviations (statistical observers only).
    """
    timestamp: dt.datetime
    soc: float
    plugged_in: bool
    charge_rate_kw: float
    power_kw: float
    arrival_time: dt.datetime | None = None
    departure_time: dt.datetime | None = None
    source: ObservationMode = ObservationMode.GRIDLABD
    uncertainty: dict[str, float] = field(default_factory=dict)


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

    @property
    def end(self) -> dt.datetime:
        return self.start + self.interval * self.n_intervals

    def intervals(self) -> list[tuple[dt.datetime, dt.datetime]]:
        return [(self.start + i * self.interval, self.start + (i + 1) * self.interval)
                for i in range(self.n_intervals)]


# ---------------------------------------------------------------------------
# Amenity metrics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EVAmenityContext:
    """What an amenity metric needs about one interval.

    Attributes:
        definition: Device definition.
        e_end_low: Lowest-trajectory stored energy at the end of the
            interval's home time [kWh].
        remaining_home_h: Home time after the interval until departure [h].
        target_kwh: Departure target [kWh].
    """
    definition: EVDefinition
    e_end_low: float
    remaining_home_h: float
    target_kwh: float


class AmenityMetric(ABC):
    """Maps stored energy at the end of an interval's home time to an amenity
    value. Subclass for a custom metric."""
    name: str = ""
    unit: str = ""

    @abstractmethod
    def evaluate(self, e_end: np.ndarray, ctx: EVAmenityContext) -> np.ndarray:
        """Returns the amenity value for each candidate end energy [kWh]."""


class DepartureSOC(AmenityMetric):
    """Best achievable state of charge at the next departure, charging at the
    maximum rate (along the charge curve) after this interval [fraction].
    Below the departure target when the interval runs below Q_min."""
    name = "departure_soc"
    unit = "fraction"

    def evaluate(self, e_end, ctx):
        d = ctx.definition
        profile = d.charge_profile
        return np.array([min(profile.energy_after(float(e), ctx.remaining_home_h), max(float(e), d.e_max))
                         for e in np.atleast_1d(e_end)]) / d.capacity_kwh


class EnergyBuffer(AmenityMetric):
    """Stored energy above the lowest feasible trajectory at the end of the
    interval [kWh]: the slack left for later intervals. Negative below Q_min."""
    name = "energy_buffer"
    unit = "kWh"

    def evaluate(self, e_end, ctx):
        return e_end - ctx.e_end_low


AMENITY_METRICS = {m.name: m for m in (DepartureSOC, EnergyBuffer)}


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
    """One power level and its amenity value."""
    q_kw: float
    amenity: float


@dataclass(frozen=True)
class EVIntervalResponse:
    """What control needs to turn a cleared quantity into a charge rate.

    Attributes:
        interval_h: Interval length [h].
        home_h: Plugged-in time within the interval [h].
        home_start: Start of the first plugged-in period in the interval.
        home_end: End of the first plugged-in period in the interval.
        e_start: Stored energy at home_start on the lowest trajectory [kWh].
            For the first interval of a horizon observed while plugged in,
            this is the observed energy.
    """
    interval_h: float
    home_h: float
    home_start: dt.datetime | None
    home_end: dt.datetime | None
    e_start: float


@dataclass
class IntervalFlexibility:
    """Flexibility of the EV over one market interval.

    Attributes:
        start, end: Interval times.
        plugged_hours: Expected plugged-in time within the interval [h].
        q_min_kw: Minimum average power that keeps every departure target
            reachable [kW]; negative when V2G discharge is possible.
        q_max_kw: Maximum average power from the lowest feasible state [kW].
        q_baseline_kw: Average power under uncontrolled charging [kW].
        q_capacity_kw: Rated charging power [kW].
        amenity_map: Amenity value at power levels across the physical range,
            increasing in power, always including q_min, q_baseline, q_max.
        baseline_amenity: Amenity value at the baseline power.
        next_departure: Next departure at or after the interval end, if any.
        departure_target_kwh: Stored energy required at that departure [kWh].
        target_feasible: Whether the departure target can be met at all.
            When False, Q_min is full-rate charging.
        participating: Whether the customer offers this interval to the market.
        response: Data for control translation.
    """
    start: dt.datetime
    end: dt.datetime
    plugged_hours: float
    q_min_kw: float
    q_max_kw: float
    q_baseline_kw: float
    q_capacity_kw: float
    amenity_map: list[AmenityPoint]
    baseline_amenity: float
    next_departure: dt.datetime | None
    departure_target_kwh: float
    target_feasible: bool
    participating: bool
    response: EVIntervalResponse

    def is_transactive(self, tol: float = 1e-9) -> bool:
        return (self.participating and self.plugged_hours > 0.0
                and self.q_max_kw - self.q_min_kw > tol)

    def amenity_at(self, q_kw: float) -> float:
        """Amenity at any power level (exact for the built-in metrics, which
        are piecewise linear in power)."""
        return float(np.interp(q_kw, [p.q_kw for p in self.amenity_map],
                               [p.amenity for p in self.amenity_map]))


@dataclass
class EVFlexibility:
    """Flexibility of the EV over a market horizon (Task 2 output)."""
    observation: EVObservation
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

    def market_flexibility(self, tol: float = 1e-9) -> list[bidding.Flexibility]:
        """Device-agnostic view for preference and bid formulation."""
        return [bidding.Flexibility(q_min=i.q_min_kw, q_max=i.q_max_kw, q_base=i.q_baseline_kw,
                                    transactive=i.is_transactive(tol),
                                    q_capacity=i.q_capacity_kw, start=i.start, end=i.end)
                for i in self.intervals]


# ---------------------------------------------------------------------------
# Task 2: define flexibility
# ---------------------------------------------------------------------------

@dataclass
class _WindowPlan:
    """Lowest feasible and baseline stored-energy trajectories over one
    plugged-in window, following the charge curve.

    Lowest trajectory: discharge at the maximum rate (V2G only, not below the
    reserve) until maximum-rate charging along the curve is just enough to
    reach the departure target, then charge at the maximum rate. If the target
    is out of reach, charge at the maximum rate from arrival.
    Baseline trajectory: maximum-rate charging from arrival, stopping at soc_max.
    """
    definition: EVDefinition
    arrive: dt.datetime
    depart: dt.datetime
    e0_low: float
    e0_base: float

    def __post_init__(self):
        d = self.definition
        self.profile = d.charge_profile
        self.r = d.max_discharge_kw / d.discharge_efficiency  # stored kWh per hour, discharging
        self.target = d.departure_target_kwh
        window_h = _hours(self.depart - self.arrive)
        self.feasible = self.profile.energy_after(self.e0_low, window_h) >= self.target - 1e-6

    def _clip(self, t: dt.datetime) -> dt.datetime:
        return min(max(t, self.arrive), self.depart)

    def reach(self, e: float, hours: float) -> float:
        """Energy after maximum-rate charging for some hours, stopping at soc_max."""
        return min(self.profile.energy_after(e, hours), max(e, self.definition.e_max))

    def low(self, t: dt.datetime) -> float:
        t = self._clip(t)
        h, rem = _hours(t - self.arrive), _hours(self.depart - t)
        d = self.definition
        e_discharge = max(self.e0_low - self.r * h, min(self.e0_low, d.e_min))
        e_needed = self.profile.energy_before(self.target, rem)
        e_full = self.profile.energy_after(self.e0_low, h)
        return min(max(e_discharge, e_needed), e_full)

    def base(self, t: dt.datetime) -> float:
        return self.reach(self.e0_base, _hours(self._clip(t) - self.arrive))


class EVFlexibilityModel:
    """Defines EV flexibility over a market horizon from an observation.

    1. Builds the plugged-in windows over the horizon from the observation
       (current plug state and departure) and the travel schedule. The trip
       energy is drained at each departure.
    2. For each window, builds the lowest feasible trajectory and the
       uncontrolled-charging baseline (see _WindowPlan), carrying both
       across windows.
    3. Per interval: Q_min is the grid energy of the lowest trajectory,
       Q_max is full-rate charging from the lowest state (to soc_max), and
       the baseline is uncontrolled charging clamped into [Q_min, Q_max].
       All are averages over the whole interval.

    Args:
        amenity_metric: "departure_soc", "energy_buffer", or an AmenityMetric.
        substep: Integration step for trajectory grid energy.
        n_map_points: Evenly spaced points in each amenity map, before adding
            q_min, q_baseline and q_max.
    """

    def __init__(self,
                 amenity_metric: str | AmenityMetric = DepartureSOC.name,
                 substep: dt.timedelta = dt.timedelta(minutes=1),
                 n_map_points: int = 11):
        self.metric = resolve_amenity_metric(amenity_metric)
        self.substep = substep
        self.n_map_points = n_map_points

    def define_flexibility(self,
                           observation: EVObservation,
                           definition: EVDefinition,
                           horizon: MarketHorizon) -> EVFlexibility:
        d = definition
        e_low = e_base = observation.soc * d.capacity_kwh
        plans = []
        for arrive, depart in self._windows(observation, d, horizon):
            plan = _WindowPlan(d, arrive, depart, e_low, e_base)
            if not plan.feasible:
                logger.warning("EV departure target %.2f kWh at %s is unreachable from %.2f kWh",
                               plan.target, depart, e_low)
            plans.append(plan)
            e_low = max(plan.low(depart) - d.trip_kwh, 0.0)
            e_base = max(plan.base(depart) - d.trip_kwh, 0.0)
        intervals = [self._define_interval(d, plans, t0, t1) for t0, t1 in horizon.intervals()]
        return EVFlexibility(observation=observation, horizon=horizon,
                             amenity_metric=self.metric.name, amenity_unit=self.metric.unit,
                             intervals=intervals)

    def _windows(self, obs: EVObservation, d: EVDefinition,
                 horizon: MarketHorizon) -> list[tuple[dt.datetime, dt.datetime]]:
        start, end = horizon.start, horizon.end
        sched = d.schedule
        scheduled = sched.home_windows(start, end)
        if not obs.plugged_in:
            # Away now (or late): skip any scheduled window in progress
            return [w for w in scheduled if w[0] > start]
        if obs.departure_time is not None and obs.departure_time > start:
            depart = obs.departure_time
        else:
            current = sched.window_at(start)
            if current is not None:
                depart = current[1]
            else:
                later = [w for w in sched.home_windows(start, end + dt.timedelta(days=1)) if w[0] > start]
                depart = later[0][1]
                logger.warning("EV plugged in outside its schedule at %s; assuming it stays until %s",
                               start, depart)
        return [(start, depart)] + [w for w in scheduled if w[0] >= depart]

    def _grid_kwh(self, d: EVDefinition, trajectory, a: dt.datetime, b: dt.datetime) -> float:
        if b <= a:
            return 0.0
        n = max(1, math.ceil((b - a) / self.substep))
        energies = [trajectory(a + (b - a) * i / n) for i in range(n + 1)]
        return sum(grid_energy(d, e2 - e1) for e1, e2 in zip(energies, energies[1:]))

    def _define_interval(self, d: EVDefinition, plans: list[_WindowPlan],
                         t0: dt.datetime, t1: dt.datetime) -> IntervalFlexibility:
        interval_h = _hours(t1 - t0)
        overlaps = [(p, max(t0, p.arrive), min(t1, p.depart))
                    for p in plans if p.arrive < t1 and p.depart > t0]
        home_h = sum(_hours(b - a) for _, a, b in overlaps)
        upcoming = next((p for p in plans if p.depart >= t1), None)
        target = d.departure_target_kwh

        q_min = sum(self._grid_kwh(d, p.low, a, b) for p, a, b in overlaps) / interval_h
        q_base_raw = sum(self._grid_kwh(d, p.base, a, b) for p, a, b in overlaps) / interval_h
        q_max = sum(grid_energy(d, p.reach(p.low(a), _hours(b - a)) - p.low(a))
                    for p, a, b in overlaps) / interval_h
        q_max = max(q_max, q_min)
        if d.participating:
            q_base = min(max(q_base_raw, q_min), q_max)
        else:
            q_min = q_max = q_base = q_base_raw

        if overlaps:
            p, a, b = overlaps[0]
            e_a, h1 = p.low(a), _hours(b - a)
            response = EVIntervalResponse(interval_h, home_h, a, b, e_a)
            ctx = EVAmenityContext(d, p.low(b), _hours(p.depart - b), target)
            e_lo = max(e_a - p.r * h1, min(e_a, d.e_min))  # most discharge possible
            e_hi = p.reach(e_a, h1)                        # most charge possible, along the curve
            q_lo_phys = grid_power(d, e_lo - e_a, interval_h)
            q_hi_phys = grid_power(d, e_hi - e_a, interval_h)
            q_map = np.unique(np.concatenate([np.linspace(q_lo_phys, q_hi_phys, self.n_map_points),
                                              [q_min, q_base, q_max]]))

            def e_end(q: float) -> float:
                return float(np.clip(e_a + stored_change(d, q, interval_h), e_lo, e_hi))

            amenity = self.metric.evaluate(np.array([e_end(q) for q in q_map]), ctx)
            baseline_amenity = float(self.metric.evaluate(np.array([e_end(q_base)]), ctx)[0])
            amenity_map = [AmenityPoint(float(q), float(v)) for q, v in zip(q_map, amenity)]
            feasible = p.feasible
        else:
            # Away for the whole interval: nothing to control
            e_now = upcoming.e0_low if upcoming is not None else 0.0
            response = EVIntervalResponse(interval_h, 0.0, None, None, e_now)
            ctx = EVAmenityContext(d, e_now, 0.0, target)
            baseline_amenity = float(self.metric.evaluate(np.array([e_now]), ctx)[0])
            amenity_map = [AmenityPoint(0.0, baseline_amenity)]
            feasible = upcoming.feasible if upcoming is not None else True

        return IntervalFlexibility(
            start=t0, end=t1, plugged_hours=home_h,
            q_min_kw=float(q_min), q_max_kw=float(q_max), q_baseline_kw=float(q_base),
            q_capacity_kw=d.max_charge_kw, amenity_map=amenity_map,
            baseline_amenity=baseline_amenity,
            next_departure=upcoming.depart if upcoming is not None else None,
            departure_target_kwh=target, target_feasible=bool(feasible),
            participating=d.participating, response=response)


# ---------------------------------------------------------------------------
# Control translation: cleared quantity -> charge rate
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EVChargeCommand:
    """Charger setpoint for one market interval.

    Attributes:
        start, end: Interval times.
        charge_rate_kw: Grid-side setpoint while plugged in [kW]; negative
            discharges (V2G).
        cleared_kw: Cleared average power over the interval [kW].
        expected_kw: Average power the model expects at this setpoint [kW].
        expected_end_soc: Expected state of charge at the end of the
            interval's plugged-in time [fraction].
        override: False for uncontrolled charging (no market control).
    """
    start: dt.datetime
    end: dt.datetime
    charge_rate_kw: float
    cleared_kw: float
    expected_kw: float
    expected_end_soc: float
    override: bool


class EVChargeController:
    """Converts a cleared average power into a charger setpoint.

    The cleared quantity is grid energy over the whole interval; the vehicle
    can only take it while plugged in. The setpoint is a cap: in the taper
    region the vehicle draws less than the cap, so the controller finds the
    setpoint whose delivered energy (along the charge curve, stopping at
    soc_max) matches the cleared energy. With charger limits (min_charge_kw,
    charge_levels) the setpoint is rounded to an allowed value, never below
    the energy needed to stay on the interval's Q_min path. V2G discharge is
    at a constant rate.

    Args:
        definition: Device definition.
        plant_follows_curve: True if the charging device tapers along the
            charge curve (physics stub, real vehicles). False if it draws the
            commanded rate until soc_max (e.g. a GridLAB-D charger without a
            taper model); the setpoint is then the plain average rate.
        tolerance_kw: Setpoint search tolerance [kW].
    """

    def __init__(self, definition: EVDefinition, plant_follows_curve: bool = True,
                 tolerance_kw: float = 1e-3):
        self.definition = definition
        self.plant_follows_curve = plant_follows_curve
        self.tolerance_kw = tolerance_kw

    def delivered_kwh(self, e_start: float, hours: float, rate_kw: float,
                      enforce_min: bool = True) -> float:
        """Stored energy added over `hours` at a setpoint [kWh]; negative when discharging."""
        d = self.definition
        if hours <= 0.0 or rate_kw == 0.0:
            return 0.0
        if rate_kw < 0.0:
            return -min(-rate_kw / d.discharge_efficiency * hours, max(e_start - d.e_min, 0.0))
        if enforce_min and rate_kw < d.min_charge_kw - _TOL:
            return 0.0  # below the charger minimum the vehicle does not charge
        if self.plant_follows_curve:
            e_end = d.charge_profile.energy_after(e_start, hours, cap_kw=rate_kw)
        else:
            e_end = e_start + rate_kw * d.charge_efficiency * hours
        return min(e_end, max(e_start, d.e_max)) - e_start

    def setpoint(self, interval: IntervalFlexibility, cleared_kw: float) -> EVChargeCommand:
        d, resp = self.definition, interval.response
        if resp.home_h <= 0.0:
            return self.uncontrolled(interval, cleared_kw)
        grid_target = float(cleared_kw) * resp.interval_h
        if grid_target < 0.0:  # V2G discharge at a constant rate
            rate = max(grid_target / resp.home_h, -d.max_discharge_kw)
            return self._command(interval, cleared_kw, rate, override=True)
        stored_target = grid_target * d.charge_efficiency
        stored_floor = max(interval.q_min_kw, 0.0) * resp.interval_h * d.charge_efficiency
        rate = self._solve_rate(resp, stored_target)
        rate = self._quantize(resp, rate, stored_target, stored_floor)
        return self._command(interval, cleared_kw, rate, override=True)

    def uncontrolled(self, interval: IntervalFlexibility, cleared_kw: float | None = None) -> EVChargeCommand:
        """Charging at the charger rating (the default); applies only while plugged in."""
        cleared = interval.q_baseline_kw if cleared_kw is None else cleared_kw
        return self._command(interval, cleared, self.definition.max_charge_kw, override=False)

    def _solve_rate(self, resp: EVIntervalResponse, stored_target: float) -> float:
        """Smallest continuous setpoint delivering at least stored_target."""
        d = self.definition
        if stored_target <= 0.0:
            return 0.0
        hi = d.max_charge_kw
        if self.delivered_kwh(resp.e_start, resp.home_h, hi, enforce_min=False) <= stored_target:
            return hi
        lo = 0.0
        while hi - lo > self.tolerance_kw:
            mid = 0.5 * (lo + hi)
            if self.delivered_kwh(resp.e_start, resp.home_h, mid, enforce_min=False) >= stored_target:
                hi = mid
            else:
                lo = mid
        return hi

    def _allowed(self, rate: float) -> tuple[float, float]:
        """Nearest allowed setpoints at or below, and at or above, a rate."""
        d = self.definition
        if d.charge_levels:
            levels = sorted({0.0, *(min(l, d.max_charge_kw) for l in d.charge_levels)})
            lower = max(l for l in levels if l <= rate + _TOL)
            upper = min((l for l in levels if l >= rate - _TOL), default=levels[-1])
            return lower, upper
        if rate <= _TOL:
            return 0.0, 0.0
        if rate >= d.min_charge_kw:
            return rate, rate
        return 0.0, d.min_charge_kw

    def _quantize(self, resp: EVIntervalResponse, rate: float, target: float, floor: float) -> float:
        lower, upper = self._allowed(rate)
        if lower == upper:
            return lower
        d_lower = self.delivered_kwh(resp.e_start, resp.home_h, lower)
        d_upper = self.delivered_kwh(resp.e_start, resp.home_h, upper)
        if d_lower < floor - 1e-9:
            return upper  # rounding down would fall below the Q_min path
        return lower if abs(d_lower - target) <= abs(d_upper - target) else upper

    def _command(self, interval: IntervalFlexibility, cleared_kw: float, rate: float,
                 override: bool) -> EVChargeCommand:
        d, resp = self.definition, interval.response
        stored = self.delivered_kwh(resp.e_start, resp.home_h, rate)
        return EVChargeCommand(interval.start, interval.end, float(rate), float(cleared_kw),
                               expected_kw=grid_power(d, stored, resp.interval_h),
                               expected_end_soc=(resp.e_start + stored) / d.capacity_kwh,
                               override=override)


class EVActuator(ABC):
    """Writes charger setpoints to a device."""

    @abstractmethod
    def apply(self, command: EVChargeCommand) -> None:
        """Writes the command's charge rate."""


# ---------------------------------------------------------------------------
# Task 1: observers (and actuators)
# ---------------------------------------------------------------------------

class EVObserver(ABC):
    """Produces EVObservations from some source of device state."""
    source: ObservationMode

    @abstractmethod
    def observe(self, sim_time: dt.datetime) -> EVObservation:
        """Returns the device state at the simulation time."""


class GridLABDConnection(Protocol):
    """Co-simulation connection; keys use the TESP "object#property" convention."""
    def get_value(self, key: str) -> Any: ...


class GridLABDWriter(Protocol):
    """Co-simulation connection that can write GridLAB-D properties."""
    def set_value(self, key: str, value: Any) -> None: ...


# GridLAB-D evcharger_det property names. Verify against your GridLAB-D build;
# override with the `properties` argument if they differ.
EVCHARGER_PROPERTIES = {
    "soc": "battery_SOC",           # percent
    "location": "vehicle_location",  # HOME, WORK, DRIVING_HOME, DRIVING_WORK, UNKNOWN
    "charge_rate": "charge_rate",    # W
    "power": "actual_power",         # kW, optional
}


class GridLABDEVObserver(EVObserver):
    """Physics-based (full) observation: reads the GridLAB-D evcharger_det.

    Plug state comes from vehicle_location == HOME; if the property is not
    available, from the travel schedule. Departure comes from the schedule.

    Args:
        connection (GridLABDConnection): Co-simulation connection.
        charger_name (str): Name of the evcharger_det object.
        definition (EVDefinition): Supplies the schedule.
        properties (dict, optional): Overrides for EVCHARGER_PROPERTIES.
    """
    source = ObservationMode.GRIDLABD

    def __init__(self, connection: GridLABDConnection, charger_name: str,
                 definition: EVDefinition, properties: dict[str, str] | None = None):
        self.connection = connection
        self.charger_name = charger_name
        self.definition = definition
        self.properties = {**EVCHARGER_PROPERTIES, **(properties or {})}

    def _raw(self, key: str) -> Any:
        raw = self.connection.get_value(f"{self.charger_name}#{self.properties[key]}")
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            return None
        return raw

    def _float(self, key: str, required: bool = True) -> float | None:
        raw = self._raw(key)
        if raw is None:
            if required:
                raise ValueError(f"GridLAB-D property {self.charger_name}#{self.properties[key]} has no value")
            return None
        return float(raw) if isinstance(raw, (int, float)) else parse_number(str(raw).strip())

    def observe(self, sim_time: dt.datetime) -> EVObservation:
        soc = self._float("soc") / 100.0
        location = self._raw("location")
        window = self.definition.schedule.window_at(sim_time)
        plugged = (str(location).strip().upper() == "HOME") if location is not None else window is not None
        rate_kw = (self._float("charge_rate", required=False) or 0.0) * 0.001
        power = self._float("power", required=False)
        return EVObservation(timestamp=sim_time, soc=soc, plugged_in=plugged,
                             charge_rate_kw=rate_kw,
                             power_kw=power if power is not None else (rate_kw if plugged else 0.0),
                             arrival_time=window[0] if plugged and window else None,
                             departure_time=window[1] if plugged and window else None,
                             source=self.source)


class GridLABDEVActuator(EVActuator):
    """Writes the evcharger_det charge rate [W] every interval.

    The rate is always written: DSO+T found that if nothing is sent, the
    charger reverts to its default rate. evcharger_det may not support
    discharge; negative rates are clipped to 0 unless allow_negative is True.

    Args:
        connection (GridLABDWriter): Co-simulation connection.
        charger_name (str): Name of the evcharger_det object.
        property_name (str): Charge-rate property.
        allow_negative (bool): Pass negative (V2G) rates through.
    """

    def __init__(self, connection: GridLABDWriter, charger_name: str,
                 property_name: str = EVCHARGER_PROPERTIES["charge_rate"], allow_negative: bool = False):
        self.connection = connection
        self.charger_name = charger_name
        self.property_name = property_name
        self.allow_negative = allow_negative

    def apply(self, command: EVChargeCommand) -> None:
        rate_kw = command.charge_rate_kw
        if rate_kw < 0.0 and not self.allow_negative:
            logger.warning("%s: clipping V2G rate %.2f kW to 0 (allow_negative=False)",
                           self.charger_name, rate_kw)
            rate_kw = 0.0
        self.connection.set_value(f"{self.charger_name}#{self.property_name}", rate_kw * 1000.0)


class PhysicsStubEVObserver(EVObserver, EVActuator):
    """Stub observation from a light battery model (agent-based approximation).

    Stands in for a GridLAB-D evcharger_det: plugs in and out on the travel
    schedule, drains the trip energy at departure, and charges at the active
    command's rate (or full rate when no command is active, like an
    uncontrolled charger). Charging stops at full; discharging stops at the
    reserve.

    By default the stub vehicle is identical to the agent's definition. Use
    parameter_scaling (e.g. ``{"capacity_kwh": 0.95}``) or a different
    schedule to make them differ.

    Args:
        definition (EVDefinition): The agent's definition of the device.
        start_time (dt.datetime): Time of the initial state.
        initial_soc (float): Initial state of charge [fraction].
        substep (dt.timedelta): Integration step.
        parameter_scaling (dict, optional): Multipliers for numeric
            EVDefinition fields of the stub vehicle.
        schedule (EVTravelSchedule, optional): Actual schedule of the stub
            vehicle, if different from the agent's.
        hold_commands (bool): Keep a command after its interval ends, until
            the next command (GridLAB-D behavior).
    """
    source = ObservationMode.PHYSICS_STUB

    def __init__(self,
                 definition: EVDefinition,
                 start_time: dt.datetime,
                 initial_soc: float,
                 substep: dt.timedelta = dt.timedelta(minutes=1),
                 parameter_scaling: dict[str, float] | None = None,
                 schedule: EVTravelSchedule | None = None,
                 hold_commands: bool = False,
                 charge_curve: Any = None):
        """charge_curve: the stub vehicle's actual curve, if different from the
        agent's (anything resolve_charge_curve() accepts)."""
        scaled = {}
        for name, factor in (parameter_scaling or {}).items():
            value = getattr(definition, name)  # raises AttributeError for unknown names
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"Cannot scale non-numeric EVDefinition field '{name}'")
            scaled[name] = value * factor
        if schedule is not None:
            scaled["schedule"] = schedule
        if charge_curve is not None:
            scaled["charge_curve"] = resolve_charge_curve(charge_curve)
        self.definition = replace(definition, **scaled)
        self.substep = substep
        self.hold_commands = hold_commands
        self._time = start_time
        self._e = initial_soc * self.definition.capacity_kwh
        window = self.definition.schedule.window_at(start_time)
        self._plugged = window is not None
        self._arrival = window[0] if window else None
        self._rate_kw = 0.0
        self._power_kw = 0.0
        self._command: EVChargeCommand | None = None

    # ---- actuator ---------------------------------------------------------
    def apply(self, command: EVChargeCommand) -> None:
        self._command = command

    def _active_rate(self, time: dt.datetime) -> float:
        c = self._command
        if c is not None and c.start <= time and (self.hold_commands or time < c.end):
            return c.charge_rate_kw
        return self.definition.max_charge_kw

    # ---- observer ---------------------------------------------------------
    def observe(self, sim_time: dt.datetime) -> EVObservation:
        self.advance_to(sim_time)
        self._update_location(sim_time)
        window = self.definition.schedule.window_at(sim_time) if self._plugged else None
        return EVObservation(timestamp=sim_time, soc=self._e / self.definition.capacity_kwh,
                             plugged_in=self._plugged,
                             charge_rate_kw=self._active_rate(sim_time) if self._plugged else 0.0,
                             power_kw=self._power_kw if self._plugged else 0.0,
                             arrival_time=self._arrival if self._plugged else None,
                             departure_time=window[1] if window else None,
                             source=self.source)

    def advance_to(self, sim_time: dt.datetime) -> None:
        if sim_time < self._time:
            raise ValueError(f"Cannot move the stub backward from {self._time} to {sim_time}")
        while self._time < sim_time:
            step = min(self.substep, sim_time - self._time)
            self._step(step)
            self._time += step

    def _update_location(self, time: dt.datetime) -> None:
        home = self.definition.schedule.window_at(time) is not None
        if self._plugged and not home:     # departure: drain the trip
            self._e = max(self._e - self.definition.trip_kwh, 0.0)
            self._arrival = None
        elif home and not self._plugged:   # arrival
            self._arrival = time
        self._plugged = home

    def _step(self, step: dt.timedelta) -> None:
        d = self.definition
        self._update_location(self._time)
        self._power_kw = 0.0
        if not self._plugged:
            return
        h = _hours(step)
        rate = self._active_rate(self._time)
        if 0.0 < rate < d.min_charge_kw:
            rate = 0.0  # below the charger minimum the vehicle does not charge
        if rate > 0.0:
            stop = max(self._e, d.e_max)  # charging ends at soc_max, matching the model
            stored = min(d.charge_profile.energy_after(self._e, h, cap_kw=rate), stop) - self._e
        elif rate < 0.0:
            stored = -min(-rate / d.discharge_efficiency * h, max(self._e - d.e_min, 0.0))
        else:
            stored = 0.0
        self._e += stored
        self._power_kw = grid_power(d, stored, h)


class StatisticalStubEVObserver(EVObserver):
    """Stub observation from a statistical approximation (placeholder).

    Intended to estimate plug state, state of charge and charging power from
    travel and charging datasets (e.g. NHTS-based arrival/departure and
    mileage distributions), reporting per-field standard deviations in
    EVObservation.uncertainty. Not implemented until the dataset is imported.
    """
    source = ObservationMode.STATISTICAL_STUB

    def __init__(self, dataset: Any = None, archetype: dict | None = None):
        self.dataset = dataset
        self.archetype = archetype

    def observe(self, sim_time: dt.datetime) -> EVObservation:
        raise NotImplementedError("Statistical EV observation is pending import of the dataset")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClearedInterval:
    """Day-ahead cleared quantity for one interval."""
    start: dt.datetime
    end: dt.datetime
    cleared_kw: float


class EVAgentStub:
    """EV agent: Observe (Task 1), Define Flexibility (Task 2), and control.

    Customer preference and bid formulation are device-agnostic and done by a
    bidding.PreferenceBidder; this agent only passes it market_flexibility().
    After clearing, the cleared quantity (average kW over the interval)
    becomes a charge-rate setpoint written through an EVActuator.

    Market cycles (same as HVACAgentStub):
        Real-time:      formulate_bid_rt() -> clear_rt(price), every interval.
        Day-ahead only: formulate_bid_da() hourly -> clear_da(prices) ->
                        dispatch_da() every control step.
        Quantity-only:  apply_cleared_quantity(interval, kW) directly.

    Args:
        name (str): Agent name.
        definition (EVDefinition): Fixed device definition.
        observer (EVObserver): Source of device state (GridLAB-D or stub).
        flexibility_model (EVFlexibilityModel, optional): Defaults to the
            departure-SOC metric.
        bidder (bidding.PreferenceBidder, optional): Required for bidding.
        controller (EVChargeController, optional).
        actuator (EVActuator, optional): Defaults to the observer if it can
            act (PhysicsStubEVObserver). Required to apply commands.
    """

    def __init__(self,
                 name: str,
                 definition: EVDefinition,
                 observer: EVObserver,
                 flexibility_model: EVFlexibilityModel | None = None,
                 bidder: bidding.PreferenceBidder | None = None,
                 controller: EVChargeController | None = None,
                 actuator: EVActuator | None = None):
        self.name = name
        self.definition = definition
        self.observer = observer
        self.flexibility_model = flexibility_model or EVFlexibilityModel()
        self.bidder = bidder
        self.controller = controller or EVChargeController(definition)
        if actuator is None and isinstance(observer, EVActuator):
            actuator = observer
        self.actuator = actuator

        self.observation: EVObservation | None = None
        self.flexibility: EVFlexibility | None = None
        self.da_flexibility: EVFlexibility | None = None
        self.da_bids: list[bidding.Bid] | None = None
        self.da_schedule: list[ClearedInterval] = []
        self.rt_flexibility: EVFlexibility | None = None
        self.rt_bid: bidding.Bid | None = None
        self.last_command: EVChargeCommand | None = None

    # ---- Task 1 -----------------------------------------------------------
    def observe(self, sim_time: dt.datetime) -> EVObservation:
        self.observation = self.observer.observe(sim_time)
        return self.observation

    # ---- Task 2 -----------------------------------------------------------
    def define_flexibility(self, horizon: MarketHorizon) -> EVFlexibility:
        if self.observation is None:
            raise RuntimeError(f"{self.name}: observe() must be called before define_flexibility()")
        self.flexibility = self.flexibility_model.define_flexibility(
            self.observation, self.definition, horizon)
        return self.flexibility

    def update(self, sim_time: dt.datetime, horizon: MarketHorizon | None = None) -> EVFlexibility:
        """Observes, then defines flexibility (default: 48-hour day-ahead horizon)."""
        self.observe(sim_time)
        return self.define_flexibility(horizon or MarketHorizon.day_ahead(sim_time))

    # ---- Bidding (hand-off to preference_curve + bid_formulation) --------
    def formulate_bid_da(self, sim_time: dt.datetime, price_forecast: Sequence[float],
                         hours: int = 48) -> list[bidding.Bid]:
        flexibility = self.update(sim_time, MarketHorizon.day_ahead(sim_time, hours))
        self.da_flexibility = flexibility
        self.da_bids = self._require_bidder().bid_da(flexibility.market_flexibility(), price_forecast)
        return self.da_bids

    def formulate_bid_rt(self, sim_time: dt.datetime, minutes: int = 5,
                         price_forecast: Sequence[float] | None = None) -> bidding.Bid:
        flexibility = self.update(sim_time, MarketHorizon.real_time(sim_time, minutes))
        self.rt_flexibility = flexibility
        self.rt_bid = self._require_bidder().bid_rt(flexibility.market_flexibility()[0], price_forecast)
        return self.rt_bid

    @staticmethod
    def quantity_at(bid: bidding.Bid, price: float) -> float:
        """Cleared quantity of a bid at a price [kW]; any number of points."""
        return bidding.bid_to_quantity(bid, price)

    def bid_amenity(self, bid: bidding.Bid, interval: IntervalFlexibility) -> list[float]:
        return [interval.amenity_at(point[bidding.Q]) for point in bid]

    # ---- Clearing -> charge rate ------------------------------------------
    def clear_rt(self, price: float, apply: bool = True) -> EVChargeCommand:
        if self.rt_bid is None or self.rt_flexibility is None:
            raise RuntimeError(f"{self.name}: formulate_bid_rt() must be called before clear_rt()")
        cleared_kw = self.quantity_at(self.rt_bid, price)
        return self.apply_cleared_quantity(self.rt_flexibility.intervals[0], cleared_kw, apply=apply)

    def clear_da(self, prices: Sequence[float]) -> list[ClearedInterval]:
        if self.da_bids is None or self.da_flexibility is None:
            raise RuntimeError(f"{self.name}: formulate_bid_da() must be called before clear_da()")
        if len(prices) != len(self.da_bids):
            raise ValueError(f"{self.name}: {len(prices)} prices for {len(self.da_bids)} DA bids")
        self.da_schedule = [ClearedInterval(iv.start, iv.end, self.quantity_at(bid, p))
                            for iv, bid, p in zip(self.da_flexibility.intervals, self.da_bids, prices)]
        return self.da_schedule

    def dispatch_da(self, sim_time: dt.datetime, control_interval: dt.timedelta | None = None,
                    apply: bool = True) -> EVChargeCommand:
        """Applies the cleared DA quantity for the hour containing sim_time,
        re-observing so the setpoint uses the current state of charge."""
        entry = next((c for c in self.da_schedule if c.start <= sim_time < c.end), None)
        if entry is None:
            raise RuntimeError(f"{self.name}: no cleared DA quantity covers {sim_time}")
        remaining = entry.end - sim_time
        length = remaining if control_interval is None else min(control_interval, remaining)
        flexibility = self.update(sim_time, MarketHorizon(sim_time, length, 1))
        interval = flexibility.intervals[0]
        # Never go below the current Q_min: protects the departure target if
        # the vehicle fell behind the DA plan
        cleared_kw = max(entry.cleared_kw, interval.q_min_kw)
        return self.apply_cleared_quantity(interval, cleared_kw, apply=apply)

    def apply_cleared_quantity(self, interval: IntervalFlexibility, cleared_kw: float,
                               apply: bool = True) -> EVChargeCommand:
        if interval.is_transactive():
            command = self.controller.setpoint(interval, cleared_kw)
        else:
            command = self.controller.uncontrolled(interval, cleared_kw)
            if abs(cleared_kw - interval.q_baseline_kw) > 1e-6:
                logger.warning("%s: cleared %.3f kW in a non-transactive interval (baseline %.3f kW); "
                               "charging uncontrolled", self.name, cleared_kw, interval.q_baseline_kw)
        return self._send(command, apply)

    def release(self, apply: bool = True) -> EVChargeCommand:
        """Returns the charger to uncontrolled (full-rate) charging."""
        if self.flexibility is None:
            raise RuntimeError(f"{self.name}: define_flexibility() must be called before release()")
        return self._send(self.controller.uncontrolled(self.flexibility.intervals[0]), apply)

    def cleared_quantity(self, price: float, interval: int = 0) -> float:
        return self._require_bidder().cleared_quantity(price, interval)

    # ---- helpers ----------------------------------------------------------
    def _send(self, command: EVChargeCommand, apply: bool) -> EVChargeCommand:
        if apply:
            if self.actuator is None:
                raise RuntimeError(f"{self.name}: no actuator configured; pass apply=False to only "
                                   f"compute the command")
            self.actuator.apply(command)
        self.last_command = command
        return command

    def _require_bidder(self) -> bidding.PreferenceBidder:
        if self.bidder is None:
            raise RuntimeError(f"{self.name}: no bidder configured")
        return self.bidder