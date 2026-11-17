# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: preference_curve.py
"""Device-agnostic customer preference curves.

Turns a device's flexibility (defined in ..._agent.py) and the customer's 
preference factor k into one demand curve per market interval. This module has 
no device code and doesn't import bid_formulation; 
    bid_formulation samples the curves into bids.

Curve (shifted isoelastic):
    Q(P) = (Q0 + s) * (P / P0) ** -epsilon - s
    epsilon = epsilon_max * f(k),  f increasing with f(0) = 0, f(1) = 1
    s = 0 gives the pure isoelastic curve Q0 (P/P0)^-epsilon. s > 0 keeps the
    curve responsive when Q0 is at or near zero, and allows feasible ranges
    that include negative quantities (e.g. battery discharge).
    The curve always passes through (P0, Q0).

Units: Q in kW (consumption positive), P in $/kWh (must be > 0).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Sequence

__all__ = [
    "ElasticityShape", "ReferencePrice",
    "shape_factor", "k_to_epsilon",
    "PreferenceParameters",
    "DemandCurve", "IsoelasticCurve",
    "FlexibilityLike", "IntervalPreference", "Preference",
    "choose_reference_prices", "build_curve", "define_preference",
]

_TOL = 1e-9


# ============================================================== k -> epsilon
class ElasticityShape(Enum):
    """Shape of f in epsilon = epsilon_max * f(k)."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGISTIC = "logistic"


class ReferencePrice(Enum):
    """How the reference price P0 is chosen for each interval."""
    FORECAST_MEAN = "forecast_mean"  # mean of the price forecast
    PER_INTERVAL = "per_interval"    # each interval's own forecast price
    FIXED = "fixed"                  # a configured constant


def shape_factor(k: float, shape: ElasticityShape, steepness: float = 5.0) -> float:
    """Returns f(k), increasing on [0, 1] with f(0) = 0 and f(1) = 1."""
    if not 0.0 <= k <= 1.0:
        raise ValueError(f"k must be in [0, 1], got {k}")
    if steepness <= 0.0:
        raise ValueError(f"steepness must be > 0, got {steepness}")
    if shape == ElasticityShape.LINEAR:
        return k
    if shape == ElasticityShape.EXPONENTIAL:
        return math.expm1(steepness * k) / math.expm1(steepness)
    if shape == ElasticityShape.LOGISTIC:
        def g(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-steepness * (x - 0.5)))
        return (g(k) - g(0.0)) / (g(1.0) - g(0.0))
    raise ValueError(f"Unknown elasticity shape {shape}")


def k_to_epsilon(k: float, epsilon_max: float,
                 shape: ElasticityShape = ElasticityShape.LINEAR,
                 steepness: float = 5.0) -> float:
    """epsilon = epsilon_max * f(k)."""
    if epsilon_max < 0.0:
        raise ValueError(f"epsilon_max must be >= 0, got {epsilon_max}")
    return epsilon_max * shape_factor(k, shape, steepness)


@dataclass
class PreferenceParameters:
    """Customer preference definition (Preference Curve inputs).

    Attributes:
        k: Preference factor, 0 (full amenity preference) to 1 (full
            financial preference).
        epsilon_max: Elasticity at k = 1.
        shape: Shape of f(k).
        steepness: Steepness of the exponential and logistic shapes.
        reference_price: How P0 is chosen.
        fixed_reference_price: P0 [$/kWh] when reference_price is FIXED.
        min_reference_fraction: Lower limit on Q0 + s as a fraction of the
            device capacity. 0 = pure isoelastic (no shift unless the feasible
            range includes negative quantities).
    """
    k: float
    epsilon_max: float = 1.0
    shape: ElasticityShape = ElasticityShape.LINEAR
    steepness: float = 5.0
    reference_price: ReferencePrice = ReferencePrice.FORECAST_MEAN
    fixed_reference_price: Optional[float] = None
    min_reference_fraction: float = 0.1

    def __post_init__(self):
        if not 0.0 <= self.k <= 1.0:
            raise ValueError(f"k must be in [0, 1], got {self.k}")
        if self.epsilon_max < 0.0:
            raise ValueError(f"epsilon_max must be >= 0, got {self.epsilon_max}")
        if self.steepness <= 0.0:
            raise ValueError(f"steepness must be > 0, got {self.steepness}")
        if not 0.0 <= self.min_reference_fraction <= 1.0:
            raise ValueError(f"min_reference_fraction must be in [0, 1], got {self.min_reference_fraction}")
        if self.reference_price == ReferencePrice.FIXED and not (self.fixed_reference_price or 0.0) > 0.0:
            raise ValueError("FIXED reference price needs fixed_reference_price > 0")

    @property
    def epsilon(self) -> float:
        return k_to_epsilon(self.k, self.epsilon_max, self.shape, self.steepness)

    @classmethod
    def from_config(cls, config: Dict[str, Any], default_k: Optional[float] = None,
                    **overrides) -> "PreferenceParameters":
        """Builds parameters from an agent configuration dict.

        Keys (all optional except k): preference_k, epsilon_max, elasticity_shape,
        steepness, reference_price, fixed_reference_price, min_reference_fraction.
        default_k is used when preference_k is absent (e.g. the device slider).
        """
        if "preference_k" in config:
            k = float(config["preference_k"])
        elif default_k is not None:
            k = float(default_k)
        else:
            raise KeyError("config has no 'preference_k' and no default_k was given")
        params: Dict[str, Any] = dict(k=k)
        for key in ("epsilon_max", "steepness", "fixed_reference_price", "min_reference_fraction"):
            if key in config:
                params[key] = float(config[key])
        if "elasticity_shape" in config:
            params["shape"] = ElasticityShape(config["elasticity_shape"])
        if "reference_price" in config:
            params["reference_price"] = ReferencePrice(config["reference_price"])
        params.update(overrides)
        return cls(**params)


# ============================================================== curves
class DemandCurve(Protocol):
    """Any decreasing demand curve. bid_formulation.curve_bid samples these."""

    def quantity(self, price: float) -> float: ...

    def price(self, quantity: float) -> float: ...


@dataclass(frozen=True)
class IsoelasticCurve:
    """Q(P) = (q0 + q_shift) * (P / p0) ** -epsilon - q_shift.

    epsilon = 0 is vertical at q0. Quantities are not clamped here; the bid
    builder clamps them to the feasible range.
    """
    p0: float
    q0: float
    epsilon: float
    q_shift: float = 0.0

    def __post_init__(self):
        if self.p0 <= 0.0:
            raise ValueError(f"reference price must be > 0, got {self.p0}")
        if self.epsilon < 0.0 or self.q_shift < 0.0:
            raise ValueError("epsilon and q_shift must be >= 0")
        if self.epsilon > 0.0 and self.q0 + self.q_shift <= 0.0:
            raise ValueError("q0 + q_shift must be > 0 for an elastic curve")

    def quantity(self, price: float) -> float:
        """Desired average power at a price [kW]."""
        if self.epsilon == 0.0:
            return self.q0
        if price <= 0.0:
            return math.inf
        return (self.q0 + self.q_shift) * (price / self.p0) ** -self.epsilon - self.q_shift

    def price(self, quantity: float) -> float:
        """Inverse of quantity(): price at which this power is desired [$/kWh]."""
        if self.epsilon == 0.0:
            if quantity < self.q0:
                return math.inf
            return 0.0 if quantity > self.q0 else self.p0
        x = quantity + self.q_shift
        if x <= 0.0:
            return math.inf
        return self.p0 * (x / (self.q0 + self.q_shift)) ** (-1.0 / self.epsilon)


# ============================================================== horizon
class FlexibilityLike(Protocol):
    """Fields read from a device's flexibility (bid_formulation.Flexibility
    satisfies this)."""
    q_min: float
    q_max: float
    q_base: float
    q_capacity: Optional[float]
    transactive: bool


@dataclass
class IntervalPreference:
    """Customer preference over one market interval."""
    curve: IsoelasticCurve
    flexible: bool  # False -> inflexible (vertical) bid at the baseline


@dataclass
class Preference:
    """Customer preference over a market horizon (Preference Curve output)."""
    k: float
    epsilon: float
    reference_price_method: ReferencePrice
    intervals: List[IntervalPreference]

    @property
    def reference_prices(self) -> List[float]:
        return [i.curve.p0 for i in self.intervals]


def choose_reference_prices(params: PreferenceParameters, n: int,
                            price_forecast: Optional[Sequence[float]] = None) -> List[float]:
    """Returns one P0 per interval using the configured method."""
    method = params.reference_price
    if method == ReferencePrice.FIXED:
        p0s = [float(params.fixed_reference_price)] * n
    else:
        if price_forecast is None or len(price_forecast) == 0:
            raise ValueError(f"reference price method '{method.value}' needs a price forecast")
        if method == ReferencePrice.FORECAST_MEAN:
            p0s = [math.fsum(price_forecast) / len(price_forecast)] * n
        else:
            if len(price_forecast) < n:
                raise ValueError(f"price forecast has {len(price_forecast)} values for {n} intervals")
            p0s = [float(p) for p in price_forecast[:n]]
    if any(p <= 0.0 for p in p0s):
        raise ValueError(f"reference prices must be > 0 for isoelastic curves, got {p0s}")
    return p0s


def build_curve(flex: FlexibilityLike, p0: float, params: PreferenceParameters,
                tol: float = _TOL) -> IntervalPreference:
    """Builds the demand curve for one interval.

    The shift s is the smallest value that (a) keeps Q0 + s at or above
    min_reference_fraction * capacity, and (b) keeps every feasible quantity
    at or above -s. Capacity defaults to q_max.
    """
    epsilon = params.epsilon
    flexible = flex.transactive and epsilon > 0.0 and flex.q_max - flex.q_min > tol
    shift = 0.0
    if flexible:
        capacity = flex.q_capacity if flex.q_capacity is not None else flex.q_max
        shift = max(0.0, params.min_reference_fraction * capacity - flex.q_base, -flex.q_min)
        if flex.q_base + shift <= tol:  # pure isoelastic with Q0 = 0 is degenerate
            flexible, shift = False, 0.0
    curve = IsoelasticCurve(p0=float(p0), q0=float(flex.q_base),
                            epsilon=epsilon if flexible else 0.0,
                            q_shift=shift)
    return IntervalPreference(curve=curve, flexible=flexible)


def define_preference(flex: Sequence[FlexibilityLike], params: PreferenceParameters,
                      price_forecast: Optional[Sequence[float]] = None,
                      reference_prices: Optional[Sequence[float]] = None) -> Preference:
    """Defines a demand curve for every interval.

    Args:
        flex: One flexibility per interval (Function 2 output).
        params: Customer preference definition.
        price_forecast: Forecast prices [$/kWh]; needed for FORECAST_MEAN and PER_INTERVAL.
        reference_prices: One P0 per interval; overrides the configured method
            (e.g. to carry the DA P0 into RT).
    """
    n = len(flex)
    p0s = (list(reference_prices) if reference_prices is not None
           else choose_reference_prices(params, n, price_forecast))
    if len(p0s) != n:
        raise ValueError(f"{len(p0s)} reference prices for {n} intervals")
    return Preference(k=params.k, epsilon=params.epsilon,
                      reference_price_method=params.reference_price,
                      intervals=[build_curve(f, p0, params) for f, p0 in zip(flex, p0s)])