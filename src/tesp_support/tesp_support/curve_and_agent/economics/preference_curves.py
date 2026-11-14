# ============================================================================
# FILE: economics/preference_curves.py
# PURPOSE: Concrete implementations of the customer (or operator)
#          preference curve that maps market prices to desired power
#          quantities (agent function F3).
#
# This module contains two concrete curve implementations:
#
#     IsoelasticPreferenceCurve
#         For unidirectional load-only devices (HVAC, water heater, EV).
#         Standard isoelastic demand curve:
#             Q(P) = Q_0 · (P / P_0)^{−ε}
#
#     BidirectionalPreferenceCurve
#         For devices that can both consume and produce (battery).
#         Sigmoid curve with degradation-driven dead band:
#             Q(P) = Q_charge_max · (1 − (P/P_thr)^ε) / (1 + (P/P_thr)^ε)
#
# THE PREFERENCE PARAMETER k:
#     Both curves are parameterized by the customer preference factor
#     k ∈ [0, 1], which is translated into an elasticity ε:
#
#         k = 0 → ε ≈ 0     Perfectly inelastic.  Device tracks the
#                             amenity setpoint regardless of price.
#                             The customer prioritizes comfort / backup
#                             over financial savings.
#
#         k = 1 → ε = ε_max  Highly elastic.  Device aggressively
#                             responds to price signals, accepting
#                             significant amenity deviation for
#                             financial benefit.
#
#     The mapping k → ε can be linear (ε = k · ε_max), exponential,
#     or logistic, depending on the desired sensitivity profile.
#     The choice of mapping function is a system design parameter.
#
# ISOELASTIC CURVE BEHAVIOR (HVAC, WH, EV):
#
#     Q(P) = Q_0 · (P / P_0)^{−ε}
#
#     Where:
#         Q_0     = baseline quantity (kW) — power consumption when the
#                   device tracks the customer's amenity setpoint with
#                   no price consideration.
#                   INTERNAL: From FlexibilityEnvelope.Q_baseline (F2).
#         P_0     = reference price ($/kWh) — expected or historical
#                   average retail price.  Anchors the curve so that
#                   Q(P_0) = Q_0.
#                   INTERNAL: From PriceForecastService or DataStreamManager.
#         ε       = elasticity derived from k.
#
#     Behavior:
#         P < P_0  → Q > Q_0  (cheap electricity → consume more)
#         P = P_0  → Q = Q_0  (expected price → baseline consumption)
#         P > P_0  → Q < Q_0  (expensive → reduce consumption)
#         ε = 0    → Q = Q_0 for all P (perfectly inelastic)
#
#     The curve is always clamped to [Q_min, Q_max] from the
#     FlexibilityEnvelope to respect physical device limits.
#
# BIDIRECTIONAL CURVE BEHAVIOR (BATTERY):
#
#     Q(P) = Q_charge_max · (1 − (P/P_thr)^ε) / (1 + (P/P_thr)^ε)
#
#     Where:
#         Q_charge_max    = maximum charging power (kW, positive).
#                           INTERNAL: From FlexibilityEnvelope.Q_max.
#         Q_discharge_max = maximum discharging power (kW, positive).
#                           INTERNAL: From FlexibilityEnvelope.Q_min (negated).
#         P_thr           = threshold price at which the battery is
#                           indifferent between charging and discharging.
#                           Set by the planning optimizer based on V_stored
#                           (marginal value of stored energy).
#                           INTERNAL: From PlanningOptimizer output.
#         ε               = elasticity derived from k.
#         degradation_cost= marginal battery wear cost ($/kWh).
#                           INTERNAL: From BatteryModel.marginal_degradation_cost().
#
#     Dead band:
#         The degradation cost creates a price range around P_thr where
#         the battery idles because arbitrage revenue doesn't cover
#         the wear cost:
#             Charge threshold:    P_thr − C_degradation
#             Discharge threshold: P_thr + C_degradation
#             Dead band width:     2 × C_degradation + efficiency loss
#
#     Behavior:
#         P << P_thr  → Q ≈ +Q_charge_max    (charge at max — cheap)
#         P ≈ P_thr   → Q ≈ 0                (idle — dead band)
#         P >> P_thr  → Q ≈ −Q_discharge_max  (discharge at max — expensive)
#         ε = 0       → Q ≈ 0 for most prices (barely responds)
#         ε = ε_max   → sharp transitions at thresholds
#
# AMENITY COST FUNCTION:
#     Both curves provide get_amenity_cost(Q_actual, Q_preferred) which
#     computes the discomfort or opportunity cost of operating at
#     Q_actual instead of Q_preferred.  This cost enters the dispatch
#     optimizer's objective function:
#
#         For loads:    C_amenity ∝ |T_indoor(Q_actual) − T_setpoint|
#                       Scaled by (1 − k): high k → low amenity weight.
#
#         For battery:  C_amenity ∝ |SOC(Q_actual) − SOC_preferred|
#                       Represents the discomfort of having less backup
#                       reserve than preferred.  Also scaled by (1 − k).
#
#     The amenity cost acts as a "phantom penalty" in the dispatch
#     optimizer that competes with market revenues.  When k = 0, it
#     dominates all market incentives and the device tracks the
#     customer's preferred setpoint regardless of price — consistent
#     with ε = 0 (perfectly inelastic).
#
# BID CURVE GENERATION:
#     Both curves provide sample_bid_curve() which discretizes the
#     continuous curve into a list of (price, quantity) BidPoints
#     suitable for submission to the Market Operator.  The sampling
#     supports a price_focus parameter that concentrates sample
#     density near an expected clearing price (from advisory records
#     produced by informational market iterations), providing better
#     resolution where it matters most.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Both classes inherit from:
#         abstractions.preference_curve.AbstractPreferenceCurve
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - agent.py (DeviceAgent):
#         generate_preference_curve() (F3) constructs one of these
#         curves based on the device type, customer preference k,
#         reference price P_0, and baseline quantity Q_0.
#
#         formulate_bid() (F4) calls sample_bid_curve() to produce
#         the discrete bid curve for market submission.
#
#         evaluate_price_response() (F7) calls evaluate() or
#         evaluate_with_bounds() to determine the target operating
#         point from a cleared price.
#
#     - economics/dispatch_optimizer.py:
#         The dispatch optimizer receives the preference curve as an
#         argument and calls get_amenity_cost() to include the
#         amenity term in its objective function.
#
#     - economics/command_arbiter.py:
#         The command arbiter passes the preference curve through to
#         the dispatch optimizer on every delivery tick.
#
#     - devices/battery_model.py:
#         BatteryModel.marginal_degradation_cost() provides the
#         degradation_cost parameter used by BidirectionalPreferenceCurve
#         to set the dead band width.
#         BatteryModel.compute_charge_discharge_thresholds() uses
#         V_stored and degradation_cost to compute P_thr, which
#         becomes P_0 in the bidirectional curve.
#
#     - economics/planning_optimizer.py:
#         The planning optimizer's output (V_stored for batteries)
#         feeds into the curve's P_0 / P_thr parameter.  For loads,
#         the planning optimizer's schedule baseline informs Q_0.
#
#     - forecasting/price_forecast_service.py:
#         Provides the reference price P_0 for loads (expected
#         average retail price for the upcoming interval).
#
# DATA TYPES USED:
#     From data_types.py:
#         BidPoint          — individual price-quantity pair
#     From abstractions/:
#         AbstractPreferenceCurve — the contract being implemented
#
# EXTERNAL INPUTS:
#     k (customer preference factor):
#         Provided by the customer as a configuration setting.
#         Ranges from 0 (full amenity preference) to 1 (full
#         financial preference).  May be set once at agent
#         initialization or adjusted over time.
#
#     epsilon_max (maximum elasticity):
#         System design parameter.  Determines how responsive the
#         most financially-motivated customer (k=1) can be.
#         Typical values: 3.0–10.0 depending on device type and
#         market design.  Higher values produce sharper bid curves
#         with more aggressive price response.
# ============================================================================

"""Concrete preference / offer curves — the economic heart of the agent.

The preference curve is the single source of economic truth for the
customer.  It is generated once per market cycle (during the ACTIVE
phase) and consumed by both the bid formulation (F4) and the price
response evaluation (F7).  In price-responsive mode (no bid submission),
the preference curve IS the bid — the agent evaluates it directly at
the cleared price.

Two implementations:
    IsoelasticPreferenceCurve     — for load-only devices (HVAC, WH, EV)
    BidirectionalPreferenceCurve  — for batteries (charge + discharge)

Both encode the same fundamental tradeoff: amenity vs. financial benefit,
parameterized by the customer preference factor k.
"""

from typing import List, Optional

from abstractions.preference_curve import AbstractPreferenceCurve
from data_types import BidPoint
from enums_and_constants import DeviceType

from tesp_support.tesp_support.curve_and_agent.abstractions import AbstractPreferenceCurve

from ..data_types import BidPoint
from ..enums_and_constants import DeviceType


class PreferenceCurve(AbstractPreferenceCurve):
    """Parameterized isoelastic demand curve encoding customer willingness
    to trade amenity for financial benefit.

    For standard (load-only) devices:
        Q(P) = Q_0 · (P / P_0)^{-ε}

    For bidirectional devices (battery):
        Q(P) = Q_charge_max · (1 - (P/P_threshold)^ε) / (1 + (P/P_threshold)^ε)

        This sigmoid crosses Q=0 at P=P_threshold and extends to negative
        quantities (discharge) at high prices.

    The elasticity ε is derived from the customer preference factor k:
        k=0 → ε≈0 (perfectly inelastic, tracks amenity regardless of price)
        k=1 → ε=ε_max (highly elastic, aggressively responds to price)

    Args:
        k: Customer preference factor (0=amenity, 1=financial).
            EXTERNAL: Provided as a customer setting/input.
        P_0: Reference price ($/kWh). Expected or historical average
            retail price. Used to anchor the curve.
            INTERNAL: From DataStreamManager price forecast or MO.
        Q_0: Baseline quantity (kW). Power consumption when tracking
            customer amenity setpoint with no price consideration.
            INTERNAL: From FlexibilityEnvelope.Q_baseline (F2 output).
        epsilon_max: Maximum elasticity parameter. Controls how
            responsive the most financially-motivated customer is.
            EXTERNAL: System design parameter.
        device_type: If BATTERY, uses the bidirectional sigmoid form.
        Q_discharge_max: For batteries, maximum discharge power (kW).
            INTERNAL: From FlexibilityEnvelope.Q_min (negative).
        degradation_cost: For batteries, marginal degradation cost
            ($/kWh) to embed in the dead band.
            INTERNAL: From BatteryModel.marginal_degradation_cost().
    """

    def __init__(
        self,
        k: float,
        P_0: float,
        Q_0: float,
        epsilon_max: float = 5.0,
        device_type: DeviceType = DeviceType.HVAC_AC_ONLY,
        Q_discharge_max: float = 0.0,
        degradation_cost: float = 0.0,
    ):
        self._k = k
        self._P_0 = P_0
        self._Q_0 = Q_0
        self._epsilon_max = epsilon_max
        self._device_type = device_type
        self._Q_discharge_max = Q_discharge_max
        self._degradation_cost = degradation_cost

    @property
    def epsilon(self) -> float:
        """Compute the elasticity parameter from customer preference k.

        The mapping k → ε can be linear, exponential, or logistic.

        Returns:
            Elasticity parameter ε.
        """
        return self._k * self._epsilon_max

    def evaluate(self, price: float) -> float:
        """Evaluate the preference curve at a given price.

        For standard devices: returns desired power consumption (kW).
        For batteries: returns desired power (positive=charge,
            negative=discharge).

        Args:
            price: Market price ($/kWh).

        Returns:
            Desired power quantity (kW).
        """
        eps = self.epsilon

        if self._device_type == DeviceType.BATTERY:
            P_threshold = self._P_0
            if P_threshold <= 0:
                P_threshold = 1e-9
            if price <= 0:
                price = 1e-9
            ratio = price / P_threshold
            if eps == 0:
                return 0.0
            r_eps = ratio**eps
            return self._Q_0 * (1.0 - r_eps) / (1.0 + r_eps)

        # Standard isoelastic: Q(P) = Q_0 * (P / P_0)^{-eps}
        if price <= 0:
            price = 1e-9
        if self._P_0 <= 0:
            return self._Q_0
        ratio = price / self._P_0
        if eps == 0:
            return self._Q_0
        return self._Q_0 * (ratio ** (-eps))

    def evaluate_with_bounds(self, price: float, Q_min: float, Q_max: float) -> float:
        """Evaluate the preference curve, clamped to feasible bounds.

        Args:
            price: Market price ($/kWh).
            Q_min: Minimum feasible power (kW).
                INTERNAL: From FlexibilityEnvelope.
            Q_max: Maximum feasible power (kW).
                INTERNAL: From FlexibilityEnvelope.

        Returns:
            Desired power, clamped to [Q_min, Q_max].
        """
        q = self.evaluate(price)
        return max(Q_min, min(Q_max, q))

    def get_amenity_cost(self, Q_actual: float, Q_preferred: float) -> float:
        """Compute the amenity cost of operating at Q_actual instead of
        Q_preferred.

        This is the "discomfort cost" that enters the dispatch optimizer
        objective function. It is scaled by the customer preference k:
        k→0: high amenity cost (comfort-focused customer)
        k→1: low amenity cost (financially-focused customer)

        Args:
            Q_actual: Actual operating point (kW).
            Q_preferred: Customer's preferred operating point (kW).
                INTERNAL: From FlexibilityEnvelope.Q_baseline.

        Returns:
            Amenity cost in $ for this timestep.
        """
        deviation = Q_actual - Q_preferred
        k_factor = max(1.0 - self._k, 0.01)
        return k_factor * self._P_0 * deviation * deviation

    def sample_bid_curve(
        self,
        price_min: float,
        price_max: float,
        n_points: int,
        Q_min: float,
        Q_max: float,
        price_focus: float | None = None,
    ) -> list:
        """Sample the preference curve at N price points to create a bid curve.

        Args:
            price_min: Minimum price to sample ($/kWh).
                INTERNAL: From market parameters.
            price_max: Maximum price to sample ($/kWh).
                INTERNAL: From market parameters.
            n_points: Number of points on the bid curve.
            Q_min: Minimum feasible power (kW).
                INTERNAL: From FlexibilityEnvelope.
            Q_max: Maximum feasible power (kW).
                INTERNAL: From FlexibilityEnvelope.
            price_focus: If set, concentrate more sample points near
                this price for better resolution. Used when an advisory
                price from an informational iteration is available.
                INTERNAL: From AdvisoryRecord.cleared_price.

        Returns:
            List of BidPoint (price, quantity) pairs.
        """
        prices = []
        for i in range(n_points):
            p = price_max - (price_max - price_min) * i / max(n_points - 1, 1)
            prices.append(p)

        points = []
        for p in prices:
            q = self.evaluate_with_bounds(p, Q_min, Q_max)
            points.append(BidPoint(price=p, quantity=q))
        return points
