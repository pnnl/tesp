# ============================================================================
# FILE: economics/planning_optimizer.py
# PURPOSE: Concrete implementation of the multi-interval schedule
#          optimization (used during ACTIVE and ASSESSMENT phases).
#
# The planning optimizer looks across a full planning horizon (e.g.,
# 24 hours for a day-ahead market) and determines the optimal device
# operating schedule that minimizes cost or maximizes revenue while
# respecting all constraints.  Unlike the dispatch optimizer (F16),
# which makes a single-timestep decision, the planning optimizer
# makes coupled decisions across many intervals where actions in one
# interval affect the feasibility and value of actions in later
# intervals.
#
# WHY SOME DEVICES NEED MULTI-INTERVAL PLANNING:
#
#     The per-timestep dispatch optimizer (F16) is myopic — it
#     maximizes net value for the current timestep without considering
#     future consequences.  For devices with significant energy
#     storage or thermal inertia, this myopia leaves money on the
#     table:
#
#     Battery:  Charging now only has value if the energy can be
#               discharged later at a higher price.  Without knowing
#               future prices, the dispatch optimizer cannot make
#               rational charge/discharge decisions.  The planning
#               optimizer produces V_stored — the marginal value of
#               stored energy at each interval — which the dispatch
#               optimizer uses as the reference price for real-time
#               charge/discharge threshold decisions.
#               Planning is ESSENTIAL for batteries.
#
#     HVAC:     Pre-cooling the building during cheap morning hours
#               creates thermal "headroom" that can be exploited
#               during expensive afternoon hours (letting the
#               temperature drift up without discomfort).  Without
#               planning, the HVAC reacts to each interval's price
#               independently and misses this arbitrage opportunity.
#               Planning is BENEFICIAL for HVAC.
#
#     Water Heater:  Pre-heating the tank during cheap overnight hours
#               ensures hot water is available during the morning
#               draw peak without running the element at expensive
#               morning prices.  The event-process nature of draws
#               (showers are probabilistic) makes this planning
#               inherently stochastic.
#               Planning is BENEFICIAL for water heaters.
#
#     EV Charger:  Given a departure deadline and minimum SOC
#               constraint, the planner determines which intervals
#               to charge in to minimize total cost.  The constraint
#               turns this into a deadline-constrained scheduling
#               problem.
#               Planning is IMPORTANT for EV chargers.
#
# THE OPTIMIZATION PROBLEM:
#
#     Decision variables:
#         Q[t] for each interval t in the planning horizon.
#         For batteries: P_charge[t], P_discharge[t] (split variables
#             to enforce non-simultaneity).
#
#     State dynamics (device-type-dependent):
#         Battery:
#             SOC[t+1] = SOC[t] + (P_charge[t]×η − P_discharge[t]/η) × Δt / E_cap
#         HVAC:
#             T_indoor[t+1] = f(T_indoor[t], T_outdoor[t], Q_hvac[t], solar[t], ...)
#             (ETP model forward integration)
#         Water Heater:
#             T_tank[t+1] = f(T_tank[t], Q_element[t], draws[t], inlet_temp[t], ...)
#         EV:
#             SOC[t+1] = SOC[t] + P_charge[t] × η × Δt / E_cap
#
#     Objective:
#         Maximize: Σ_t [
#             revenue(P_market[t], Q[t]) × Δt
#           − cost(Q[t]) × Δt
#           − C_degradation(Q[t], state[t]) × Δt       [battery only]
#           − C_amenity(state[t], schedule[t])
#         ]
#
#     Constraints:
#         Physical limits:    Q_min ≤ Q[t] ≤ Q_max    ∀t
#         State bounds:       state_min ≤ state[t] ≤ state_max    ∀t
#             Battery:        SOC_reserve ≤ SOC[t] ≤ SOC_max_bms
#             HVAC:           T_setpoint − band ≤ T[t] ≤ T_setpoint + band
#             Water Heater:   T_tank[t] ≥ T_min_constraint (120°F)
#             EV:             SOC[t_departure] ≥ SOC_min_required
#         Non-simultaneity:   P_charge[t] × P_discharge[t] = 0   [battery]
#         Ramp limits:        |Q[t+1] − Q[t]| ≤ ramp_max        [if applicable]
#
# SOLUTION APPROACH:
#
#     For batteries (LP or QP):
#         If degradation cost is linear in throughput and penalties
#         are piecewise linear, the problem is a linear program.
#         For 24 hourly intervals: ~48 decision variables
#         (P_charge + P_discharge per hour), ~120 constraints.
#         Solves in milliseconds with any LP solver.
#         If degradation has quadratic stress factors, it becomes a
#         QP — still millisecond-scale.
#
#     For HVAC (LP after linearization):
#         The ETP model is linear in Q_hvac, so the temperature
#         trajectory is a linear function of the decision variables.
#         The comfort constraint (temperature within band) is linear.
#         Cost minimization subject to linear dynamics and constraints
#         → LP.
#
#     For EV (LP):
#         SOC dynamics are linear.  Departure constraint is a single
#         linear inequality.  Trivially an LP.
#
#     For Water Heater (stochastic LP or scenario-based):
#         The draw forecast is a probability distribution (event
#         process), not a point forecast.  The planner can either:
#         a) Use the expected draw profile (deterministic LP, simpler).
#         b) Sample scenarios from the draw distribution and solve a
#            stochastic program (more accurate, more expensive).
#         c) Use a robust approach with worst-case draws from a high
#            quantile (conservative but safe).
#         The choice is governed by the customer preference k:
#             k → 0 (comfort): robust approach (never run out of hot water)
#             k → 1 (financial): expected-value approach (cheaper but riskier)
#
# V_STORED — MARGINAL VALUE OF STORED ENERGY (BATTERY):
#
#     The most important output of the planning optimizer for batteries
#     is V_stored[t] — the shadow price (dual variable) of the SOC
#     constraint at each interval.  It represents:
#
#         "If I had one more kWh stored in the battery at time t,
#          how much additional profit could I extract over the
#          remaining planning horizon?"
#
#     V_stored drives all real-time battery decisions:
#         Charge threshold:    P_market < V_stored × η − C_degradation
#         Discharge threshold: P_market > V_stored + C_degradation
#         Dead band:           between these two thresholds
#
#     V_stored varies throughout the day:
#         High before a price peak (energy stored now is very valuable)
#         Low after a peak (peak has passed, less future value)
#         Low overnight (cheap to refill, not much upcoming value)
#
#     Without V_stored, the battery has no basis for intertemporal
#     arbitrage.  The dispatch optimizer would treat each timestep
#     independently, missing the fundamental value proposition of
#     energy storage.
#
# INTERACTION WITH INFORMATIONAL MARKET ITERATIONS:
#
#     The planning optimizer is re-run after each informational
#     market iteration because the advisory price trajectory improves
#     with each iteration:
#
#         Informational iteration 1:
#             Price trajectory = initial prior (historical averages).
#             V_stored = rough estimate.
#             Battery bids based on rough thresholds.
#
#         Informational iteration 2:
#             Price trajectory = advisory prices from iteration 1.
#             V_stored = better estimate (reflects market feedback).
#             Battery bids tighten around likely clearing prices.
#
#         Informational iteration N:
#             Price trajectory = near-converged advisory prices.
#             V_stored = high-confidence estimate.
#             Battery bids are well-calibrated.
#
#         Binding iteration:
#             Final V_stored used for delivery-time decisions.
#
#     For non-battery devices, the planning optimizer benefits
#     similarly: the pre-conditioning schedule (HVAC) or charge
#     schedule (EV) improves as advisory prices converge.
#
# CLASSES IN THIS FILE:
#
#     PlanningOptimizer(AbstractPlanningOptimizer)
#         The concrete planning optimizer.  Implements solve() which:
#
#         1. Constructs the optimization problem from the current
#            device state, price trajectory, weather forecasts,
#            and constraints.
#         2. Selects the appropriate solver based on problem structure
#            (LP, QP, or scenario-based).
#         3. Extracts the optimal schedule, V_stored (for batteries),
#            expected costs, expected revenues, and cycles consumed.
#         4. Returns a PlanningResult.
#
#         The method dispatches internally based on device_type to
#         construct device-specific state dynamics and constraints.
#         The solver itself is device-agnostic — it operates on the
#         generic optimization formulation.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from:
#         abstractions.planning_optimizer.AbstractPlanningOptimizer
#
#     AbstractPlanningOptimizer's constructor receives:
#         AbstractDeviceModel — for state dynamics and trajectory prediction
#         DeviceType          — to select the appropriate formulation
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - agent.py (DeviceAgent):
#         _handle_active():     Calls solve() during the ACTIVE phase
#                               of DA markets (or any market with a
#                               planning horizon longer than a single
#                               interval).  Provides the price trajectory,
#                               weather forecasts, and constraints.
#
#         _handle_assessment(): Re-calls solve() after each informational
#                               iteration with the updated advisory price
#                               trajectory.  The improved V_stored feeds
#                               into the next iteration's bid formulation.
#
#         formulate_bid() (F4): For batteries, uses V_stored from the
#                               latest PlanningResult to set the charge/
#                               discharge thresholds in the bid curve.
#                               For HVAC, uses the pre-conditioning
#                               schedule to inform the baseline Q[t].
#
#     - devices/*_model.py:
#         The planning optimizer holds a reference to the device model
#         and calls device-specific prediction methods:
#             HVACModel.predict_temperature() — for thermal trajectory
#             WaterHeaterModel.predict_tank_temperature() — for tank trajectory
#             EVChargerModel.predict_soc() — for SOC trajectory
#             BatteryModel.predict_soc() — for SOC trajectory
#             BatteryModel.marginal_degradation_cost() — for cycle cost
#
#     - economics/preference_curves.py:
#         The planning optimizer may use the preference curve's
#         get_amenity_cost() to include amenity penalties in the
#         objective for intervals where the schedule deviates from
#         the customer's preferred state.
#
#     - economics/dispatch_optimizer.py:
#         The dispatch optimizer consumes V_stored (for batteries) as
#         the reference value in DeliveryEconomics.  The planning
#         optimizer produces V_stored; the dispatch optimizer uses it.
#         They do not call each other directly — the agent passes
#         V_stored through as a parameter.
#
#     - forecasting/price_forecast_service.py:
#         The price trajectory input to solve() comes from:
#             PriceForecastService.get_trajectory() — which aggregates
#             advisory prices from informational clears, external
#             wholesale price forecasts, and historical priors.
#
#     - forecasting/data_stream_manager.py:
#         The weather forecasts (outdoor temp, solar, humidity) and
#         event forecasts (hot water draws, EV arrival) are packaged
#         by the DataStreamManager.get_forecast_bundle() and passed
#         to solve() via the forecasts dictionary.
#
#     - forecasting/constraint_stream.py:
#         Hard constraints (tank temp minimum, EV departure SOC,
#         battery SOC reserve, BMS limits) are passed as a list of
#         AbstractConstraintStream objects.  The planner translates
#         them into inequality constraints in the optimization.
#
# DATA TYPES USED:
#     From data_types.py:
#         PlanningResult     — output structure (schedule, V_stored,
#                              costs, revenues, cycles)
#     From abstractions/:
#         AbstractPlanningOptimizer — the contract being implemented
#         AbstractDeviceModel       — for state dynamics
#         AbstractDeviceState       — initial conditions
#         AbstractConstraintStream  — hard limits over horizon
#     From enums_and_constants.py:
#         DeviceType         — selects problem formulation
#
# EXTERNAL INPUTS:
#     price_trajectory:
#         List of ((t_start, t_end), price_$/kWh) tuples over the
#         planning horizon.
#         INTERNAL: From PriceForecastService.get_trajectory().
#         EXTERNAL origin: Informational market clears, wholesale
#             market data, historical price patterns.
#
#     weather forecasts:
#         Outdoor temperature, solar irradiance, humidity over the
#         planning horizon.
#         INTERNAL: From DataStreamManager.get_forecast_bundle().
#         EXTERNAL origin: Weather service API.
#
#     constraints:
#         Hard constraints (tank temp minimum, EV departure SOC,
#         battery SOC reserve, BMS limits).
#         INTERNAL: From DataStreamManager.get_all_constraints().
#         EXTERNAL origin: Customer input, building codes, BMS specs.
#
#     customer_preference_k:
#         Customer preference factor (0–1).
#         EXTERNAL: Customer configuration setting.
#         Used to weight the amenity cost term in the objective and
#         to select the robustness level for stochastic problems
#         (water heater draw uncertainty).
#
#     degradation_model (battery only):
#         BatteryModel instance providing marginal_degradation_cost().
#         INTERNAL: From the agent's device model.
#         Degradation parameters (replacement cost, rated cycles, etc.)
#         are EXTERNAL from manufacturer datasheets.
#
#     soc_reserve (battery only):
#         Minimum SOC maintained at all times for backup resilience.
#         INTERNAL: From DataStreamManager constraint stream.
#         EXTERNAL origin: Customer setting + dynamic outage risk.
# ============================================================================

"""Concrete multi-interval planning optimizer.

The planning optimizer bridges the gap between the agent's single-timestep
dispatch decisions and the multi-interval reality of energy storage,
thermal inertia, and deadline constraints.  It answers the question:
"given everything I know about future prices, weather, and customer
needs, what is the optimal schedule for this device over the next
N hours?"

For batteries, the planning optimizer is essential — it produces V_stored,
the marginal value of stored energy, without which the battery has no
basis for deciding whether to charge, discharge, or idle.  For other
devices, it enables pre-conditioning strategies (pre-cool, pre-heat,
front-load charging) that reduce cost by shifting consumption to
cheaper intervals.

The optimizer is re-run after each informational market iteration,
producing increasingly accurate schedules as advisory prices converge
toward the binding clearing outcome.

Classes:
    PlanningOptimizer — Solves the multi-interval constrained optimization,
                        dispatching internally to device-type-specific
                        formulations (LP for batteries and EV, linearized
                        LP for HVAC, scenario-based for water heaters).
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.data_streams import AbstractConstraintStream
from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from abstractions.planning_optimizer import AbstractPlanningOptimizer
from data_types import PlanningResult
from enums_and_constants import DeviceType


from tesp_support.tesp_support.curve_and_agent.abstractions import AbstractPlanningOptimizer

from ..data_streams import ConstraintStream
from ..data_types import (
    ContinuousDataPoint,
    HVACState,
    PlanningResult,
)
from tesp_support.tesp_support.curve_and_agent.devices.battery_model import BatteryModel, 
from tesp_support.tesp_support.curve_and_agent.devices.hvac_model import _KW_TO_BTU_HR,  HVACModel, 

_interp_forecast



class PlanningOptimizer(AbstractPlanningOptimizer):
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
        price_trajectory: list[tuple[tuple[float, float], float]],
        weather_forecasts: dict[str, list[ContinuousDataPoint]] | None,
        constraints: list[ConstraintStream],
        interval_duration: float,
        planning_horizon: float,
        customer_preference_k: float,
        degradation_model: BatteryModel | None = None,
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
            _interval, price = price_trajectory[i]
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
        price_trajectory: list[tuple[tuple[float, float], float]],
        weather_forecasts: dict[str, list[ContinuousDataPoint]] | None,
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
        price_delta = max(price_delta, 1e-9)

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
        # T_room = state.indoor_air_temp if is_cooling else state.indoor_air_temp
        T_room = state.indoor_air_temp

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
                    if T_next < T_desired - temp_range or T_next > T_desired + temp_range:
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
