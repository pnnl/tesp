# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: bid_formulation.py
"""Device-agnostic bid curve construction and clearing.

Layering (no device code here or in preference_curve.py):
    device agent (Functions 1-2)  -> list[Flexibility]
    preference_curve (Function 3) -> one demand curve per interval
    bid_formulation               -> bid curves, clearing, market formats
This module imports preference_curve; preference_curve doesn't import this one.

Two bid paths:
    Preference path (PreferenceBidder, curve_bid): samples a preference_curve
        demand curve into whatever bid structure BidConfig describes.
        Used by hvac_agent_stub.
    Linear path (forecast_slope, build_bid, formulate_bid_da): the DSO+T
        slider/slope 4-point curve used by the refactored legacy agents.

Internal bid format (all paths and structures):
    bid = [[Q0, P0], [Q1, P1], ...]    Q index 0, P index 1, any number of points
    Q never decreases and P never increases from the first point to the last.
    Q is consumption-positive kW (batteries/EVs: charging +, discharging -).
    P is $/kWh. The bid is read as a piecewise-linear demand curve: above the
    first price it is the first Q, below the last price the last Q.
    Step (block) bids use the same format as a staircase of vertical and
    horizontal segments, so bid_to_quantity clears every structure.
    Market formats (fixed point counts, blocks) come from to_market().
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

from . import preference_curve as pc  # both modules must live in the same package

__all__ = [
    "Q", "P", "Bid", "Bounds", "UNBOUNDED",
    "Flexibility", "BiddingAgent",
    # linear path
    "forecast_slope", "zero_bid", "vertical_bid", "linear_bid", "clip_bid",
    "build_bid", "formulate_bid_da", "DAtoRTInterpolator",
    # preference path / bid structures
    "BidShape", "PriceSampling", "BidConfig",
    "price_levels", "staircase", "curve_bid", "formulate_preference_bids",
    "PreferenceBidder",
    # format and clearing
    "validate_bid", "simplify_bid", "to_market", "bid_to_blocks", "bid_to_quantity",
]

Q, P = 0, 1
Bid = List[List[float]]
Bounds = Tuple[float, float]
INF = math.inf
UNBOUNDED: Bounds = (-INF, INF)
_TOL = 1e-9


# ============================================================== flexibility
@dataclass
class Flexibility:
    """Device-agnostic flexibility for one market interval (Function 2 output).
    Satisfies preference_curve.FlexibilityLike.

    Attributes:
        q_min, q_max: Feasible average power range [kW].
        q_base: Baseline operating point [kW].
        transactive: False -> inflexible vertical bid at q_base.
        q_capacity: Rated power [kW]; scales the preference curve's minimum
            reference quantity. None -> q_max.
        start, end: Interval times. Only needed to carry DA reference prices into RT.
    """
    q_min: float
    q_max: float
    q_base: float
    transactive: bool = True
    q_capacity: Optional[float] = None
    start: Optional[dt.datetime] = None
    end: Optional[dt.datetime] = None

    def __post_init__(self):
        if self.q_min > self.q_max + _TOL:
            raise ValueError(f"q_min ({self.q_min}) > q_max ({self.q_max})")

    @classmethod
    def inflexible(cls, q: float, **kwargs) -> "Flexibility":
        return cls(q, q, q, transactive=False, **kwargs)

    def clamp(self, q: float) -> float:
        return min(max(q, self.q_min), self.q_max)

    def intersect(self, lo: float, hi: float) -> "Flexibility":
        """Narrow the range to [lo, hi] (replaces RT_fix_four_points_range).
        If the ranges don't overlap, collapse to the end nearest [lo, hi]."""
        new_lo, new_hi = max(self.q_min, lo), min(self.q_max, hi)
        if new_lo > new_hi:
            new_lo = new_hi = self.q_max if lo > self.q_max else self.q_min
        return replace(self, q_min=new_lo, q_max=new_hi)


# ============================================================== legacy agent contract
class BiddingAgent(Protocol):
    """Linear-path contract for the refactored legacy agents. NOT called by
    this module. bid_slope / bid_deadband are Function 3 decisions; to follow
    the Functions-1-2-only rule they should move to preference_curve."""

    def flexibility_da(self) -> List[Flexibility]: ...

    def flexibility_rt(self, q_base: float) -> Flexibility: ...

    def bid_slope(self, prices: Sequence[float]) -> Optional[float]: ...

    def bid_deadband(self, prices: Sequence[float]) -> float: ...


# ============================================================== shared validation
def validate_bid(bid: Bid, tol: float = _TOL) -> None:
    """Raise ValueError if Q decreases or P increases along the curve."""
    if len(bid) < 2:
        raise ValueError("bid needs at least 2 points")
    for i, ((q1, p1), (q2, p2)) in enumerate(zip(bid, bid[1:])):
        if q2 < q1 - tol:
            raise ValueError(f"Q decreases between points {i} and {i+1}: {bid}")
        if p2 > p1 + tol:
            raise ValueError(f"P increases between points {i} and {i+1}: {bid}")


# ============================================================== linear path
def forecast_slope(prices: Sequence[float], q_span: float, scale: float) -> Optional[float]:
    """-(max(prices) - min(prices)) / (q_span * scale), or None (-> vertical bid)
    if q_span * scale <= 0 or the forecast is flat."""
    if not prices:
        raise ValueError("empty price forecast")
    spread = max(prices) - min(prices)
    denom = q_span * scale
    if denom <= 0 or spread <= 0:
        return None
    return -spread / denom


def zero_bid() -> Bid:
    return [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]


def vertical_bid(q: float, p_hi: float, p_ref: float, p_lo: float) -> Bid:
    p_ref = min(max(p_ref, p_lo), p_hi)
    return [[q, p_hi], [q, p_ref], [q, p_ref], [q, p_lo]]


def linear_bid(flex: Flexibility, p_ref: float, slope: float, deadband: float = 0.0,
               q_anchor: Optional[float] = None, step_outside: bool = False) -> Bid:
    """4-point curve: a line with `slope` through (q_anchor, p_ref) and a
    ±deadband split at q_base. q_anchor defaults to q_base. step_outside=True
    moves the split to the range ends when q_base isn't strictly inside."""
    if slope > 0:
        raise ValueError(f"slope must be <= 0, got {slope}")
    if deadband < 0:
        raise ValueError(f"deadband must be >= 0, got {deadband}")
    qa = flex.q_base if q_anchor is None else q_anchor
    b = p_ref - slope * qa

    def line(q: float) -> float:
        return slope * q + b

    lo, hi = flex.q_min, flex.q_max
    if step_outside and not (lo < flex.q_base < hi):
        return [[lo, line(lo) + deadband], [lo, line(lo) + deadband],
                [hi, line(hi) - deadband], [hi, line(hi) - deadband]]
    qb = flex.clamp(flex.q_base)
    return [[lo, line(lo) + deadband], [qb, line(qb) + deadband],
            [qb, line(qb) - deadband], [hi, line(hi) - deadband]]


def clip_bid(bid: Bid, q_bounds: Bounds = UNBOUNDED, p_bounds: Bounds = UNBOUNDED) -> Bid:
    (q_lo, q_hi), (p_lo, p_hi) = q_bounds, p_bounds
    return [[min(max(q, q_lo), q_hi), min(max(p, p_lo), p_hi)] for q, p in bid]


def build_bid(flex: Flexibility, p_ref: float, slope: Optional[float], *,
              deadband: float = 0.0, q_anchor: Optional[float] = None,
              step_outside: bool = False, vertical_prices: Optional[Bounds] = None,
              q_bounds: Bounds = UNBOUNDED, p_bounds: Bounds = UNBOUNDED) -> Bid:
    """Linear path, one interval: linear if flexible, else vertical."""
    if slope is None or not flex.transactive:
        p_hi, p_lo = vertical_prices or (p_ref, p_ref)
        bid = vertical_bid(flex.clamp(flex.q_base), p_hi, p_ref, p_lo)
    else:
        bid = linear_bid(flex, p_ref, slope, deadband, q_anchor, step_outside)
    bid = clip_bid(bid, q_bounds, p_bounds)
    validate_bid(bid)
    return bid


def formulate_bid_da(flex: Sequence[Flexibility], prices: Sequence[float],
                     slope: Optional[float], deadband: float = 0.0,
                     q_bounds: Bounds = UNBOUNDED, p_bounds: Bounds = UNBOUNDED) -> List[Bid]:
    """Linear path, DA window: one bid per hour."""
    if len(flex) != len(prices):
        raise ValueError(f"{len(flex)} flexibility entries vs {len(prices)} prices")
    vp = (max(prices), min(prices))
    return [build_bid(f, p_t, slope, deadband=deadband, vertical_prices=vp,
                      q_bounds=q_bounds, p_bounds=p_bounds)
            for f, p_t in zip(flex, prices)]


class DAtoRTInterpolator:
    """Linear path: ramps the RT operating point from the previous RT value
    toward the DA plan, re-targeting at :00 and :30. initial=None snaps to the
    first DA value."""

    def __init__(self, initial: Optional[float] = 0.0,
                 step_min: float = 5.0, half_period_min: float = 30.0):
        self.prev = initial
        self.delta = 0.0
        self.minute = 0.0
        self.step, self.half = step_min, half_period_min

    def reset(self) -> None:
        self.minute = 0.0

    def force(self, value: float) -> None:
        self.prev = value

    def tick(self) -> None:
        self.minute += self.step

    def next(self, da_now: float, da_next: float) -> float:
        if self.prev is None:
            self.prev = da_now
        if self.minute == 0.0:
            self.delta = da_now - self.prev
        elif self.minute == self.half:
            self.delta = (da_next - self.prev) * 0.5
        self.prev += self.delta * self.step / self.half
        self.tick()
        return self.prev


# ============================================================== bid structures
class BidShape(Enum):
    """How the market reads a bid."""
    PIECEWISE_LINEAR = "piecewise_linear"  # linear interpolation between points
    STEP = "step"                          # price-quantity blocks


class PriceSampling(Enum):
    """How the price levels at which the demand curve is sampled are chosen."""
    GEOMETRIC = "geometric"  # spaced geometrically in price across the curve's active range
    QUANTITY = "quantity"    # spaced evenly in quantity across the feasible range


@dataclass(frozen=True)
class BidConfig:
    """Market limits and bid structure for the preference path.

    Attributes:
        price_cap: Highest bid price [$/kWh].
        price_floor: Lowest bid price [$/kWh]; must be > 0 for isoelastic curves.
        n_points: Number of price levels sampled. For PIECEWISE_LINEAR this is
            the number of bid points; for STEP, the number of blocks.
        shape: How the market reads the bid.
        sampling: How price levels are chosen.
        include_anchor: Make one level the reference price P0, so the bid
            passes exactly through (P0, Q0). Needs n_points >= 3.
        pad_to_n_points: For PIECEWISE_LINEAR, to_market() returns exactly
            n_points points (repeating the last point if needed), as fixed-size
            markets such as the DSO+T 4-point market expect.
    """
    price_cap: float
    price_floor: float = 1e-3
    n_points: int = 4
    shape: BidShape = BidShape.PIECEWISE_LINEAR
    sampling: PriceSampling = PriceSampling.GEOMETRIC
    include_anchor: bool = True
    pad_to_n_points: bool = True

    def __post_init__(self):
        if not 0.0 < self.price_floor < self.price_cap < INF:
            raise ValueError(f"need 0 < price_floor < price_cap < inf, got {self.price_floor}, {self.price_cap}")
        if self.n_points < 2:
            raise ValueError(f"n_points must be >= 2, got {self.n_points}")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "BidConfig":
        """Keys: price_cap (required), price_floor, bid_points, bid_shape
        ('piecewise_linear' | 'step'), bid_sampling ('geometric' | 'quantity'),
        bid_include_anchor, bid_pad_to_n_points."""
        params: Dict[str, Any] = dict(price_cap=float(config["price_cap"]),
                                      price_floor=float(config.get("price_floor", 1e-3)),
                                      n_points=int(config.get("bid_points", 4)))
        if "bid_shape" in config:
            params["shape"] = BidShape(config["bid_shape"])
        if "bid_sampling" in config:
            params["sampling"] = PriceSampling(config["bid_sampling"])
        if "bid_include_anchor" in config:
            params["include_anchor"] = bool(config["bid_include_anchor"])
        if "bid_pad_to_n_points" in config:
            params["pad_to_n_points"] = bool(config["bid_pad_to_n_points"])
        return cls(**params)


# ============================================================== preference path
def price_levels(flex: Flexibility, curve: pc.DemandCurve, config: BidConfig,
                 anchor_price: Optional[float] = None) -> Optional[List[float]]:
    """Price levels (highest first) at which to sample a demand curve.
    Returns None when the bid should be vertical (not transactive, empty
    range, or the curve doesn't cross the range within the price limits)."""
    if not flex.transactive or flex.q_max - flex.q_min <= _TOL:
        return None

    p_lo, p_hi = config.price_floor, config.price_cap
    p_top = min(curve.price(flex.q_min), p_hi)   # high price -> low quantity
    p_bot = max(curve.price(flex.q_max), p_lo)   # low price -> high quantity
    if p_top <= p_bot * (1.0 + 1e-12):
        return None
    n = config.n_points

    if config.sampling == PriceSampling.GEOMETRIC:
        r = (p_bot / p_top) ** (1.0 / (n - 1))
        levels = [p_top * r ** i for i in range(n)]
    elif config.sampling == PriceSampling.QUANTITY:
        q_a = flex.clamp(curve.quantity(p_top))
        q_b = flex.clamp(curve.quantity(p_bot))
        qs = [q_a + (q_b - q_a) * i / (n - 1) for i in range(n)]
        levels = [min(max(curve.price(q), p_bot), p_top) for q in qs]
    else:
        raise ValueError(f"Unknown sampling {config.sampling}")
    levels[0], levels[-1] = p_top, p_bot

    if (config.include_anchor and anchor_price is not None and n >= 3
            and p_bot < anchor_price < p_top):
        j = min(range(1, n - 1), key=lambda i: abs(math.log(levels[i] / anchor_price)))
        levels[j] = anchor_price
    return sorted(set(levels), reverse=True)


def staircase(quantities: Sequence[float], prices: Sequence[float]) -> Bid:
    """Step bid in the internal format. At prices in (prices[k+1], prices[k]]
    the quantity is quantities[k]; block k (quantities[k-1], quantities[k]]
    clears when the price is at or below prices[k]."""
    bid = [[quantities[0], prices[0]]]
    for k in range(1, len(prices)):
        bid.append([quantities[k - 1], prices[k]])
        bid.append([quantities[k], prices[k]])
    return bid


def curve_bid(flex: Flexibility, curve: pc.DemandCurve, config: BidConfig,
              anchor_price: Optional[float] = None) -> Bid:
    """Samples a decreasing demand curve into a bid with the configured
    structure. Quantities are clamped to [q_min, q_max]."""
    p_ref = anchor_price if anchor_price is not None else math.sqrt(config.price_floor * config.price_cap)
    levels = price_levels(flex, curve, config, anchor_price)

    if levels is None:
        if flex.transactive and flex.q_max - flex.q_min > _TOL:
            # curve doesn't cross the range within the price limits
            q = flex.clamp(curve.quantity(min(max(p_ref, config.price_floor), config.price_cap)))
        else:
            q = flex.clamp(flex.q_base)
        bid = vertical_bid(q, config.price_cap, p_ref, config.price_floor)
    else:
        quantities = []
        for p in levels:
            q = flex.clamp(curve.quantity(p))
            quantities.append(max(q, quantities[-1]) if quantities else q)  # guard rounding
        if config.shape == BidShape.STEP:
            bid = staircase(quantities, levels)
        else:
            bid = [[q, p] for q, p in zip(quantities, levels)]
    validate_bid(bid)
    return bid


def formulate_preference_bids(flex: Sequence[Flexibility], preference: pc.Preference,
                              config: BidConfig) -> List[Bid]:
    """One bid per interval from flexibility and its preference curves."""
    if len(flex) != len(preference.intervals):
        raise ValueError(f"{len(flex)} flexibility entries vs {len(preference.intervals)} preference intervals")
    bids = []
    for f, ip in zip(flex, preference.intervals):
        f_bid = f if ip.flexible else replace(f, transactive=False)
        bids.append(curve_bid(f_bid, ip.curve, config, anchor_price=ip.curve.p0))
    return bids


class PreferenceBidder:
    """Runs Function 3 and bid formulation for one device.

    Keeps DA and RT state separate: the DA bids and their reference prices
    stay available while RT bids are formed, so RT bids value amenity the same
    way as the DA bid for the same hour.

    Attributes:
        da_preference, da_bids: Latest DA preference and bids.
        rt_preference, rt_bid: Latest RT preference and bid.
        preference, bids: Latest of either (bids is a one-element list after RT).
    """

    def __init__(self, parameters: pc.PreferenceParameters, config: BidConfig):
        self.parameters = parameters
        self.config = config
        self.da_preference: Optional[pc.Preference] = None
        self.da_bids: Optional[List[Bid]] = None
        self.rt_preference: Optional[pc.Preference] = None
        self.rt_bid: Optional[Bid] = None
        self.preference: Optional[pc.Preference] = None
        self.bids: Optional[List[Bid]] = None
        self._da_reference: List[Tuple[dt.datetime, dt.datetime, float]] = []

    def bid(self, flex: Sequence[Flexibility],
            price_forecast: Optional[Sequence[float]] = None,
            reference_prices: Optional[Sequence[float]] = None) -> List[Bid]:
        """Builds preference curves and bids for any horizon (updates only
        preference/bids, not the DA or RT state)."""
        self.preference = pc.define_preference(flex, self.parameters, price_forecast, reference_prices)
        self.bids = formulate_preference_bids(flex, self.preference, self.config)
        return self.bids

    def bid_da(self, flex: Sequence[Flexibility], price_forecast: Sequence[float]) -> List[Bid]:
        """DA bids; remembers each interval's P0 for later RT bids."""
        bids = self.bid(flex, price_forecast=price_forecast)
        self.da_preference, self.da_bids = self.preference, bids
        self._da_reference = [(f.start, f.end, ip.curve.p0)
                              for f, ip in zip(flex, self.preference.intervals)
                              if f.start is not None and f.end is not None]
        return bids

    def bid_rt(self, flex: Flexibility,
               price_forecast: Optional[Sequence[float]] = None) -> Bid:
        """RT bid. P0 comes from the DA interval containing flex.start if
        available; otherwise from the configured method."""
        p0 = self.da_reference_price(flex.start) if flex.start is not None else None
        if (p0 is None and price_forecast is None
                and self.parameters.reference_price != pc.ReferencePrice.FIXED):
            raise RuntimeError(
                f"No reference price for the RT interval starting {flex.start}: no DA bid covers it "
                f"and no price_forecast was given (method '{self.parameters.reference_price.value}'). "
                f"Form a DA bid first or pass price_forecast.")
        bid = self.bid([flex], price_forecast, None if p0 is None else [p0])[0]
        self.rt_preference, self.rt_bid = self.preference, bid
        return bid

    def da_reference_price(self, time: dt.datetime) -> Optional[float]:
        for start, end, p0 in self._da_reference:
            if start <= time < end:
                return p0
        return None

    def to_market(self, bid: Bid) -> List[List[float]]:
        """The bid in this bidder's market format (see to_market)."""
        return to_market(bid, self.config)

    @staticmethod
    def quantity_at(bid: Bid, price: float) -> float:
        """Cleared quantity of a bid (internal format) at a price [kW]."""
        return bid_to_quantity(bid, price)

    def cleared_quantity(self, price: float, interval: int = 0) -> float:
        """Cleared quantity at a price for the latest bids of either market."""
        if self.bids is None:
            raise RuntimeError("no bids formed")
        return bid_to_quantity(self.bids[interval], price)


# ============================================================== market formats
def simplify_bid(bid: Bid, tol: float = 1e-12) -> Bid:
    """Removes duplicate points and interior points that lie on the line
    through their neighbours. The cleared quantity at every price is unchanged."""
    pts: Bid = []
    for q, p in bid:
        if pts and abs(q - pts[-1][Q]) <= tol and abs(p - pts[-1][P]) <= tol:
            continue
        pts.append([q, p])
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = out[-1], pts[i], pts[i + 1]
        cross = (b[Q] - a[Q]) * (c[P] - a[P]) - (b[P] - a[P]) * (c[Q] - a[Q])
        if abs(cross) > tol:
            out.append(b)
    out.append(pts[-1])
    return out


def bid_to_blocks(bid: Bid, price_cap: float, tol: float = _TOL) -> List[List[float]]:
    """Step bid (internal staircase) -> [[block_kW, price], ...], highest
    price first. The first block is the must-take quantity at price_cap;
    each later block is the width of a horizontal segment at its price."""
    blocks = [[bid[0][Q], price_cap]]
    for (q1, p1), (q2, p2) in zip(bid, bid[1:]):
        if abs(p1 - p2) <= tol and q2 - q1 > tol:
            blocks.append([q2 - q1, p1])
    return blocks


def to_market(bid: Bid, config: BidConfig) -> List[List[float]]:
    """Converts a bid from the internal format to the market format.

    PIECEWISE_LINEAR: [[Q, P], ...], simplified and, if pad_to_n_points,
        padded to exactly n_points by repeating the last point.
    STEP: [[block_kW, price], ...] (see bid_to_blocks).
    """
    if config.shape == BidShape.STEP:
        return bid_to_blocks(bid, config.price_cap)
    pts = simplify_bid(bid)
    if config.pad_to_n_points:
        if len(pts) > config.n_points:
            raise ValueError(f"bid has {len(pts)} points after simplification; market allows {config.n_points}")
        while len(pts) < config.n_points:
            pts.append(list(pts[-1]))
    return pts


# ============================================================== clearing
def bid_to_quantity(bid: Bid, price: float) -> float:
    """Price -> quantity (consumption-positive kW) for a bid in the internal
    format with any number of points and either shape.

    At a price exactly on a horizontal segment (a step-bid block price, or a
    flat stretch of a linear bid) the lower quantity is returned. Markets that
    partly clear such a block should report the cleared quantity directly.
    """
    if price >= bid[0][P]:
        return bid[0][Q]
    if price <= bid[-1][P]:
        return bid[-1][Q]
    for (q1, p1), (q2, p2) in zip(bid, bid[1:]):
        if p1 >= price >= p2:
            if p1 == p2:
                return q1
            return q1 + (q2 - q1) * (p1 - price) / (p1 - p2)
    return bid[-1][Q]  # unreachable for a valid bid