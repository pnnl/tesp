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
        n_intervals = int(planning_horizon / interval_duration)
        ih = interval_duration / 3600.0  # interval in hours

        if self._device_type == "battery" and degradation_model is not None:
            return self._solve_battery(
                current_state, price_trajectory, n_intervals, ih,
                degradation_model, soc_reserve, customer_preference_k,
            )
        else:
            return self._solve_generic(
                current_state, price_trajectory, weather_forecasts,
                n_intervals, ih, interval_duration, customer_preference_k,
            )

    def _solve_battery(
        self,
        state, price_trajectory, n_intervals, ih,
        degradation_model, soc_reserve, k,
    ) -> PlanningResult:
        """Greedy forward-pass battery scheduling with V_stored."""
        import math

        capacity = state.energy_capacity
        eta = math.sqrt(state.round_trip_efficiency)
        soc = state.soc
        soc_min = max(state.soc_min_bms, soc_reserve)
        soc_max = state.soc_max_bms
        max_charge = state.max_charge_rate
        max_discharge = state.max_discharge_rate

        # Sort intervals by price to find charge/discharge opportunities
        prices = []
        for i in range(min(n_intervals, len(price_trajectory))):
            interval, price = price_trajectory[i]
            prices.append(price)

        if not prices:
            return PlanningResult()

        avg_price = sum(prices) / len(prices)
        price_range = max(prices) - min(prices)

        # Compute marginal degradation at current state
        deg_cost = degradation_model.marginal_degradation_cost(state, max_charge)
        # Round-trip loss cost
        loss_cost = (1.0 - state.round_trip_efficiency) * avg_price

        intervals = []
        v_stored_list = []
        total_cost = 0.0
        total_revenue = 0.0
        cycles_consumed = 0.0

        for i in range(min(n_intervals, len(price_trajectory))):
            t_interval, price = price_trajectory[i]
            t_start, t_end = t_interval

            # Decision: charge if price < avg - threshold, discharge if > avg + threshold
            threshold = (deg_cost + loss_cost) / 2.0  # break-even spread
            if price_range < threshold * 2:
                # No profitable arbitrage
                power = 0.0
            elif price < avg_price - threshold:
                # Charge: limited by max rate and SOC headroom
                soc_room = (soc_max - soc) * capacity
                max_energy = soc_room / eta
                power = min(max_charge, max_energy / ih) if max_energy > 0 else 0.0
            elif price > avg_price + threshold:
                # Discharge: limited by max rate and available SOC
                soc_avail = (soc - soc_min) * capacity
                max_energy = soc_avail * eta
                power = -min(max_discharge, max_energy / ih) if max_energy > 0 else 0.0
            else:
                power = 0.0

            # Update SOC
            if power >= 0:
                energy_stored = power * eta * ih
            else:
                energy_stored = power / eta * ih
            new_soc = soc + energy_stored / capacity
            new_soc = max(soc_min, min(soc_max, new_soc))
            actual_delta = (new_soc - soc) * capacity
            soc = new_soc

            # Track costs/revenue
            if power > 0:
                cost = price * power * ih
                total_cost += cost
            elif power < 0:
                rev = price * abs(power) * ih
                total_revenue += rev

            # Cycles consumed
            cycles_consumed += abs(actual_delta) / (capacity * 2.0)

            # V_stored: shadow price of SOC ~ expected future price benefit
            # Simple heuristic: V_stored = future max price × η - deg_cost
            future_prices = prices[i + 1:] if i + 1 < len(prices) else [avg_price]
            v_stored = max(future_prices) * eta - deg_cost if future_prices else 0.0
            v_stored_list.append((soc, v_stored))

            intervals.append((t_start, t_end, power, 0.0))

        return PlanningResult(
            intervals=intervals,
            V_stored=v_stored_list,
            total_cost=total_cost,
            total_revenue=total_revenue,
            cycles_consumed=cycles_consumed,
        )

    def _solve_generic(
        self,
        state, price_trajectory, weather_forecasts,
        n_intervals, ih, interval_duration, k,
    ) -> PlanningResult:
        """Generic (HVAC/WH) planning: shift load away from high-price intervals."""
        prices = []
        for i in range(min(n_intervals, len(price_trajectory))):
            _, price = price_trajectory[i]
            prices.append(price)

        if not prices:
            return PlanningResult()

        avg_price = sum(prices) / len(prices)

        intervals = []
        total_cost = 0.0
        total_revenue = 0.0

        for i in range(min(n_intervals, len(price_trajectory))):
            t_interval, price = price_trajectory[i]
            t_start, t_end = t_interval

            # Pre-condition: run more when price is low, less when high
            # Base load = 1.0 (normalized), adjust by price ratio
            if avg_price > 0:
                ratio = price / avg_price
                # Low price → power > base, high price → power < base
                power = max(0.0, 1.0 + (1.0 - k) * (1.0 - ratio))
            else:
                power = 1.0

            cost = price * power * ih
            total_cost += cost
            intervals.append((t_start, t_end, power, 0.0))

        return PlanningResult(
            intervals=intervals,
            V_stored=[],
            total_cost=total_cost,
            total_revenue=total_revenue,
            cycles_consumed=0.0,
        )