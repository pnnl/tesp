# ============================================================================
# FILE: preference_curve.py
# PURPOSE: Customer preference curve generation (Agent Function F3).
#          Translates the customer preference factor k into a parameterized
#          isoelastic demand curve. This module is device-type-agnostic.
# ============================================================================

from typing import Optional, Tuple
from data_types import BidPoint, FlexibilityEnvelope
from enums_and_constants import DeviceType


class PreferenceCurve:
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
        degradation_cost: float = 0.0
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
        raise NotImplementedError

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
        raise NotImplementedError

    def evaluate_with_bounds(
        self,
        price: float,
        Q_min: float,
        Q_max: float
    ) -> float:
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
        raise NotImplementedError

    def get_amenity_cost(
        self,
        Q_actual: float,
        Q_preferred: float
    ) -> float:
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
        raise NotImplementedError

    def sample_bid_curve(
        self,
        price_min: float,
        price_max: float,
        n_points: int,
        Q_min: float,
        Q_max: float,
        price_focus: Optional[float] = None
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
        raise NotImplementedError