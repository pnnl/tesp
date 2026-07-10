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
from .data_types import (
    PlanningResult,
    FlexibilityEnvelope,
    ContinuousDataPoint,
    HVACState,
)
from .data_streams import ConstraintStream
from .device_models import BatteryModel, HVACModel, _KW_TO_BTU_HR, _interp_forecast


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
        soc_reserve: float = 0.0,
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
                current_state,
                price_trajectory,
                n_intervals,
                ih,
                degradation_model,
                soc_reserve,
                customer_preference_k,
            )
        else:
            return self._solve_generic(
                current_state,
                price_trajectory,
                weather_forecasts,
                n_intervals,
                ih,
                interval_duration,
                customer_preference_k,
            )

    def _solve_battery(
        self,
        state,
        price_trajectory,
        n_intervals,
        ih,
        degradation_model,
        soc_reserve,
        k,
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
            future_prices = prices[i + 1 :] if i + 1 < len(prices) else [avg_price]
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
        state,
        price_trajectory,
        weather_forecasts,
        n_intervals,
        ih,
        interval_duration,
        k,
    ) -> PlanningResult:
        """Planning for HVAC/WH: thermally-constrained schedule optimization.

        For HVAC devices with an HVACModel, this solves a multi-interval
        optimization that minimizes the weighted sum of energy cost and
        comfort deviation, subject to thermal dynamics constraints.
        This replicates the DSOT DA_optimal_quantities approach.

        For other device types, falls back to simple price-ratio heuristic.
        """
        if isinstance(self._device_model, HVACModel) and isinstance(state, HVACState):
            return self._solve_hvac(
                state,
                price_trajectory,
                weather_forecasts,
                n_intervals,
                ih,
                interval_duration,
                k,
            )

        # Fallback: simple price-ratio heuristic for non-HVAC devices
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

            if avg_price > 0:
                ratio = price / avg_price
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

    def _solve_hvac(
        self,
        state: HVACState,
        price_trajectory: List[Tuple[Tuple[float, float], float]],
        weather_forecasts: Optional[Dict[str, List[ContinuousDataPoint]]],
        n_intervals: int,
        ih: float,
        interval_duration: float,
        k: float,
    ) -> PlanningResult:
        """HVAC-specific planning optimizer with thermal dynamics.

        Implements a constrained optimization similar to the DSOT
        DA_optimal_quantities method. Uses the simplified 1-node ETP
        model (exponential decay) to link power consumption to indoor
        temperature across intervals, then minimizes:

            Σ_t [ k · (price_t - price_min) / price_delta · Q_t / Q_max
                  + (1-k) · ((T_room_t - T_desired_t) / temp_range)²
                  + 0.001 · k · (Q_t / Q_max)² ]

        subject to thermal dynamics and temperature bounds.

        This is solved via a forward-pass dynamic programming approach
        (no external solver dependency) that iteratively adjusts power
        to balance cost and comfort.

        Args:
            state: Current HVAC state.
            price_trajectory: List of (interval, price) tuples.
            weather_forecasts: Forecast streams (outdoor temp, etc.).
            n_intervals: Number of planning intervals.
            ih: Interval duration in hours.
            interval_duration: Interval duration in seconds.
            k: Customer preference factor (0=comfort, 1=financial).

        Returns:
            PlanningResult with optimal power schedule.
        """
        import math as _math

        model: HVACModel = self._device_model
        is_cooling = state.hvac_mode == "cooling"

        # Extract prices
        prices = []
        temp_forecasts = []
        humidity_forecasts = []
        for i in range(min(n_intervals, len(price_trajectory))):
            _, price = price_trajectory[i]
            prices.append(price)

        if not prices:
            return PlanningResult()

        price_min = min(prices)
        price_max = max(prices)
        price_delta = price_max - price_min
        if price_delta < 1e-9:
            price_delta = 1e-9

        # Extract temperature forecasts
        outdoor_temps = []
        for i in range(n_intervals):
            t_offset = i * interval_duration
            if weather_forecasts and "outdoor_air_temp" in weather_forecasts:
                To = _interp_forecast(
                    weather_forecasts["outdoor_air_temp"],
                    t_offset,
                    state.outdoor_air_temp,
                )
            else:
                To = state.outdoor_air_temp
            outdoor_temps.append(To)

        # ETP exponential decay constant (from DSOT)
        UA = state.UA_envelope
        CA = state.air_mass
        CM = state.thermal_mass
        eps = _math.exp(-UA / (CM + CA) * 1.0)  # 1-hour time constant

        # Compute adjusted COP per interval
        cop_adj = []
        lf_adj = []
        for i in range(n_intervals):
            To = outdoor_temps[i]
            if is_cooling:
                cop = model.adjusted_cooling_COP(state.cooling_COP, To)
            else:
                cop = model.adjusted_heating_COP(state.heating_COP, To)
            cop_adj.append(cop)
            lf_adj.append(model.latent_load_factor(state.humidity))

        # Get solar and internal gain forecasts
        solar_gains = []
        internal_gains = []
        for i in range(n_intervals):
            t_offset = i * interval_duration
            if weather_forecasts and "solar_irradiance" in weather_forecasts:
                sg = _interp_forecast(
                    weather_forecasts["solar_irradiance"],
                    t_offset,
                    state.solar_gain,
                )
            else:
                sg = state.solar_gain
            solar_gains.append(sg * state.solar_heatgain_factor)
            internal_gains.append(state.internal_gain)

        # Q_max from device capacity
        cap = model.get_adjusted_capacity(state, state.outdoor_air_temp)
        base_cop = cop_adj[0] if cop_adj else state.cooling_COP
        Q_max_kw = cap / base_cop / _KW_TO_BTU_HR
        if Q_max_kw < 0.1:
            Q_max_kw = state.power_draw if state.power_draw > 0.1 else 3.0

        # Desired temperature schedule
        T_desired = state.thermostat_setpoint
        temp_range = 4.0  # comfort band for normalization

        # Forward-pass optimization
        # Start from current setpoint temperature
        T_room = state.indoor_air_temp if is_cooling else state.indoor_air_temp

        intervals = []
        total_cost = 0.0
        quantities = []

        for i in range(min(n_intervals, len(price_trajectory))):
            t_interval, price = price_trajectory[i]
            t_start, t_end = t_interval
            To = outdoor_temps[i]
            cop = cop_adj[i]
            lf = lf_adj[i]
            Qs = solar_gains[i]
            Qi = internal_gains[i]

            # Evaluate candidate powers: search for optimal Q
            best_Q = 0.0
            best_cost = float("inf")

            n_candidates = 11
            for j in range(n_candidates):
                Q_cand = Q_max_kw * j / max(n_candidates - 1, 1)

                # Predict resulting temperature using DSOT simplified ETP
                if is_cooling:
                    Q_thermal = -cop * 0.98 * Q_cand * _KW_TO_BTU_HR / lf
                else:
                    Q_thermal = cop * 1.02 * Q_cand * _KW_TO_BTU_HR / lf

                T_next = eps * T_room + (1.0 - eps) * (To + (Q_thermal + Qi + Qs) / UA)

                # Cost function (from DSOT obj_rule)
                energy_cost = k * (price - price_min) / price_delta * Q_cand / Q_max_kw
                comfort_cost = (
                    (1.0 - k) * 0.1 * ((T_next - T_desired) / temp_range) ** 2
                )
                smoothing = 0.001 * k * (Q_cand / Q_max_kw) ** 2
                total = energy_cost + comfort_cost + smoothing

                # Temperature bounds check
                if is_cooling:
                    if T_next > T_desired + temp_range:
                        total += 10.0  # penalty
                    elif T_next < T_desired - temp_range:
                        total += 10.0
                else:
                    if T_next < T_desired - temp_range:
                        total += 10.0
                    elif T_next > T_desired + temp_range:
                        total += 10.0

                if total < best_cost:
                    best_cost = total
                    best_Q = Q_cand
                    best_T = T_next

            # Update state for next interval
            if is_cooling:
                Q_thermal = -cop * 0.98 * best_Q * _KW_TO_BTU_HR / lf
            else:
                Q_thermal = cop * 1.02 * best_Q * _KW_TO_BTU_HR / lf
            T_room = eps * T_room + (1.0 - eps) * (To + (Q_thermal + Qi + Qs) / UA)

            cost = price * best_Q * ih
            total_cost += cost
            quantities.append(best_Q)
            intervals.append((t_start, t_end, best_Q, T_room))

        return PlanningResult(
            intervals=intervals,
            V_stored=[],
            total_cost=total_cost,
            total_revenue=0.0,
            cycles_consumed=0.0,
        )
