# ============================================================================
# FILE: planning_optimizer.py
# PURPOSE: Multi-interval planning optimization.
#          Computes optimal device operating schedule over a planning horizon
#          (e.g., 24 hours for DA market). Essential for batteries (provides
#          V_stored) and beneficial for all devices (pre-conditioning).
#
# INTERNAL: Called during Active and Assessment phases.
# ============================================================================

from typing import Dict, List, Optional, Tuple
from data_types import PlanningResult, FlexibilityEnvelope, ContinuousDataPoint
from data_streams import ConstraintStream
from device_models import BatteryModel


class PlanningOptimizer:
    """Multi-interval schedule optimization for a planning horizon.
    
    Solves a trajectory optimization that determines when the device
    should consume more or less power based on forecasted prices,
    weather, and constraints. For batteries, produces the marginal
    value of stored energy (V_stored) at each interval.
    
    The optimization:
        Maximize: Σ_t [revenue(P_market[t], Q[t]) 
                       - cost(Q[t]) 
                       - degradation(Q[t]) 
                       - amenity_penalty(state[t])]
        Subject to: state dynamics, physical limits, constraints
    
    Args:
        device_model: Device-specific physics model.
            INTERNAL: One of HVACModel, WaterHeaterModel, etc.
        device_type: Type of device.
    """

    def __init__(self, device_model: any, device_type: str):
        self._device_model = device_model
        self._device_type = device_type

    def solve(
        self,
        current_state: any,
        price_trajectory: List[Tuple[Tuple[float, float], float]],
        weather_forecasts: Optional[Dict[str, List[ContinuousDataPoint]]],
        constraints: List[ConstraintStream],
        interval_duration: float,
        planning_horizon: float,
        customer_preference_k: float,
        degradation_model: Optional[BatteryModel] = None,
        soc_reserve: float = 0.0
    ) -> PlanningResult:
        """Solve the multi-interval planning optimization.
        
        Args:
            current_state: Current device state.
                INTERNAL: From F1 (state observation).
            price_trajectory: List of (interval, price) tuples over
                the planning horizon.
                INTERNAL: From PriceForecastService.get_trajectory().
                Initially from external/historical price data; updated
                by informational market clears.
            weather_forecasts: Dictionary of forecast streams needed
                by the device model (outdoor temp, solar, etc.).
                INTERNAL: From DataStreamManager.get_forecast_bundle().
                EXTERNAL origin: Weather service.
            constraints: List of active constraints over the horizon.
                INTERNAL: From DataStreamManager.get_all_constraints().
                EXTERNAL origin: Customer input (departure SOC, etc.).
            interval_duration: Length of each planning interval (seconds).
            planning_horizon: Total horizon length (seconds).
            customer_preference_k: Customer preference factor (0–1).
                EXTERNAL: Customer setting.
            degradation_model: For batteries, the degradation model.
                INTERNAL: From BatteryModel.
            soc_reserve: For batteries, minimum SOC reserve (fraction).
                INTERNAL: From constraint stream.
                EXTERNAL origin: Customer setting + dynamic outage risk.
        
        Returns:
            PlanningResult with optimal schedule, V_stored (for batteries),
            expected costs and revenues.
        """
        raise NotImplementedError