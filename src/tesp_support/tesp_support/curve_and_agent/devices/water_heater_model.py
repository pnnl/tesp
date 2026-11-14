# ============================================================================
# FILE: devices/water_heater_model.py
# PURPOSE: Concrete device model for electric resistance water heaters.
#
# Implements the AbstractDeviceModel contract using a simplified
# stratified tank thermal model.  The tank is divided into two zones
# (upper and lower) to capture the vertical temperature gradient that
# develops during draw events and heating cycles.
#
# THE TANK MODEL:
#     Zone 1 — Upper tank (temperature T_upper, volume V_upper):
#         Heat balance includes:
#         - Standing heat loss through insulation: UA_tank·(T_upper − T_ambient)
#         - Mixing from hot-water draws: cold inlet water entering bottom
#           pushes hot water out the top, lowering T_upper over time.
#         - Element heating (if element is in upper zone or single-element).
#         - Natural convection between zones.
#
#     Zone 2 — Lower tank (temperature T_lower, volume V_lower):
#         Heat balance includes:
#         - Standing heat loss: UA_tank·(T_lower − T_ambient)
#         - Cold inlet water injection during draws (directly cools
#           lower zone).
#         - Element heating (if lower element, or single-element in
#           lower position).
#         - Natural convection between zones.
#
#     Simplified single-zone mode:
#         For quick estimation, the model can treat the tank as a
#         single well-mixed volume at (T_upper + T_lower) / 2.
#
#     Key relationships:
#         Energy stored = ρ·c_p·V·(T_avg − T_inlet)
#         Energy per draw = ρ·c_p·flow_rate·(T_delivery − T_inlet)·duration
#         Element input = P_element × 3412.14 Btu/hr per kW
#
# GRIDLAB-D INTERFACE:
#     This model does NOT read from or write to GridLAB-D directly.
#     GridLAB-D interaction occurs only through the simulator interface:
#         F1 reads WaterHeaterState (tank temps, draw rate, element status)
#         F9 writes DeviceCommand (tank thermostat setpoint)
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.device_model.AbstractDeviceModel
#     Uses:          abstractions.device_state.AbstractDeviceState
#                    (concretely expects devices.states.ConcreteWaterHeaterState)
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - devices/states.py: Provides ConcreteWaterHeaterState.
#     - forecasting/event_forecast.py: Hot water draw event forecast
#       provides the cumulative energy distribution consumed by
#       estimate_flexibility() and predict_tank_temperature().  This is
#       the primary source of uncertainty for this device.
#     - forecasting/continuous_forecast.py: Inlet water temperature
#       (seasonal) and electricity price forecasts.
#     - forecasting/constraint_stream.py: Minimum tank temperature
#       constraint (120°F for Legionella prevention) appears in the
#       constraints list.
#     - economics/planning_optimizer.py: May call predict_tank_temperature()
#       for multi-interval pre-heating optimization.
#     - agent.py (DeviceAgent): Calls estimate_flexibility() during the
#       Active phase and translate_power_to_command() via the Command
#       Arbiter during delivery.
#
# CONSUMED FORECAST STREAMS (via forecasts dict):
#     'hot_water_draw' — EventForecast, EXTERNAL from learned model.
#                        Provides cumulative energy draw distribution.
#                        This is the dominant source of flexibility
#                        uncertainty — shower timing drives bimodal
#                        tank state distributions.
#     'inlet_water_temp' — ContinuousForecast, EXTERNAL from seasonal
#                          ground temperature model.  Slow-moving but
#                          affects energy-per-draw calculations.
#
# CONSUMED CONSTRAINT STREAMS (via constraints list):
#     'tank_temp_minimum' — ConstraintStream, continuous=True,
#                           required_value=120.0°F (typical).
#                           EXTERNAL from building code / customer setting.
#                           This is a HARD constraint: the optimizer must
#                           guarantee the tank never drops below this value,
#                           which sets Q_min in the flexibility envelope.
# ============================================================================

"""Concrete water heater device model — stratified tank thermal model.

The water heater is unique among the device types in that its primary
source of uncertainty is an EVENT process (hot water draws) rather than
a continuous process (weather).  The flexibility estimation therefore
propagates the cumulative draw energy distribution through the tank
model to produce a distribution of tank states, then derives the
flexibility envelope from quantiles of that distribution.

Key methods:
    estimate_flexibility()        — F2: feasible power range, draw-uncertainty-aware.
    translate_power_to_command()  — F8: convert target power to tank thermostat setpoint.
    predict_tank_temperature()    — Forward integration of the tank thermal model.
    power_to_setpoint()           — Inverse mapping: power → tank setpoint.
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from data_types import (
    DeviceCommand,
    FlexibilityEnvelope,
    QuantilePoint,
)
from enums_and_constants import DeviceType

class WaterHeaterModel:
    """Simplified thermal model of a stratified electric water heater.

    Models the tank as two thermal zones (upper and lower) with:
    - Heat loss to ambient through tank insulation
    - Cold water inlet mixing during draws
    - Electric element heating
    - Natural convection between zones

    Args:
        None. Physical parameters come from WaterHeaterState.
    """

    def predict_tank_temperature(
        self,
        state: WaterHeaterState,
        element_power_kw: float,
        draw_forecast: QuantilePoint,
        inlet_temp_forecast: ContinuousDataPoint | None,
        ambient_temp: float,
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> list[tuple[float, float, float]]:
        """Predict tank temperature trajectory given element power.

        Args:
            state: Current water heater state from GridLAB-D.
                INTERNAL: From F1.
            element_power_kw: Heating element electrical power (kW).
                0 = element off, element_power = element at rated capacity.
            draw_forecast: Cumulative hot water draw distribution.
                INTERNAL: From DataStreamManager event forecast.
            inlet_temp_forecast: Inlet cold water temperature.
                INTERNAL: From DataStreamManager.
            ambient_temp: Ambient temperature around the tank (°F).
            duration_seconds: Prediction horizon.
            timestep_seconds: Integration timestep.

        Returns:
            List of (time_offset, upper_temp, lower_temp) tuples.
        """
        vol_upper = state.tank_volume / 2.0
        vol_lower = state.tank_volume / 2.0
        mass_upper = vol_upper * _WATER_LB_PER_GAL  # Btu/°F
        mass_lower = vol_lower * _WATER_LB_PER_GAL
        UA_mixing = 10.0  # Btu/hr·°F between zones

        T_upper = state.tank_temp_upper
        T_lower = state.tank_temp_lower
        T_inlet = state.inlet_water_temp
        if inlet_temp_forecast is not None:
            T_inlet = inlet_temp_forecast.value

        total_draw_gal = draw_forecast.expected if draw_forecast else 0.0
        draw_rate_gph = total_draw_gal / (duration_seconds / 3600.0)

        Q_element = element_power_kw * _KW_TO_BTU_HR

        trajectory: list[tuple[float, float, float]] = []
        n_steps = int(duration_seconds / timestep_seconds)
        dt_hr = timestep_seconds / 3600.0

        for i in range(n_steps):
            t = (i + 1) * timestep_seconds

            Q_loss_upper = state.tank_UA * 0.5 * (T_upper - ambient_temp)
            Q_loss_lower = state.tank_UA * 0.5 * (T_lower - ambient_temp)
            Q_mixing = UA_mixing * (T_upper - T_lower)

            gal_this_step = draw_rate_gph * dt_hr
            if gal_this_step > 0 and vol_lower > 0:
                draw_frac = min(gal_this_step / vol_lower, 1.0)
                T_lower = T_lower * (1.0 - draw_frac) + T_inlet * draw_frac

            dT_upper = (Q_element - Q_loss_upper - Q_mixing) / mass_upper * dt_hr
            dT_lower = (Q_mixing - Q_loss_lower) / mass_lower * dt_hr

            T_upper += dT_upper
            T_lower += dT_lower
            trajectory.append((t, T_upper, T_lower))

        return trajectory

    def estimate_flexibility(
        self,
        state: WaterHeaterState,
        draw_forecast: QuantilePoint,
        inlet_temp_forecast: ContinuousDataPoint | None,
        ambient_temp: float,
        min_tank_temp: float,
        interval_duration: float,
    ) -> FlexibilityEnvelope:
        """Estimate feasible power range for the upcoming interval.

        Q_min: minimum power to keep tank above min_tank_temp given
            worst-case draws (high quantile of draw forecast).
        Q_max: element rated power (or 0 if tank is already at max).
        Q_baseline: power needed to maintain current setpoint temp.

        Args:
            state: Current water heater state.
                INTERNAL: From F1.
            draw_forecast: Hot water draw energy distribution.
                INTERNAL: From DataStreamManager event forecast.
            inlet_temp_forecast: Inlet water temperature.
                INTERNAL: From DataStreamManager.
            ambient_temp: Ambient air temperature around tank (°F).
            min_tank_temp: Hard minimum tank temperature constraint (°F).
                INTERNAL: From DataStreamManager constraint stream.
            interval_duration: Market interval length (seconds).

        Returns:
            FlexibilityEnvelope.
        """
        max_temp = state.thermostat_setpoint + 10.0
        Q_max = 0.0 if state.tank_temp_upper >= max_temp else state.element_power

        avg_temp = (state.tank_temp_upper + state.tank_temp_lower) / 2.0
        standby_loss = state.tank_UA * (avg_temp - ambient_temp)
        Q_standby = standby_loss / _KW_TO_BTU_HR

        # --- Draw-forecast contribution (design: draws parameter) ---
        interval_hr = max(interval_duration / 3600.0, 1e-6)

        # Q_baseline: standby losses + expected draw power
        draw_kw = 0.0
        if draw_forecast is not None and draw_forecast.expected > 0:
            draw_kw = draw_forecast.expected / interval_hr
        Q_baseline = max(0.0, min(Q_standby + draw_kw, Q_max))

        # Q_min: thermal energy balance — minimum power to keep the
        # average tank temperature above min_tank_temp at end of
        # interval, accounting for draws + standby losses offset by
        # the tank's stored thermal energy above the minimum.
        tank_mass_btu_f = state.tank_volume * _WATER_LB_PER_GAL
        thermal_buffer_btu = tank_mass_btu_f * max(avg_temp - min_tank_temp, 0.0)
        loss_btu = standby_loss * interval_hr

        draw_safety_btu = 0.0
        if draw_forecast is not None and draw_forecast.expected > 0:
            sigma = math.sqrt(max(draw_forecast.variance, 0.0))
            draw_safety_btu = (draw_forecast.expected + sigma) * _KW_TO_BTU_HR

        shortfall_btu = draw_safety_btu + loss_btu - thermal_buffer_btu
        Q_min = max(0.0, min(shortfall_btu / (interval_hr * _KW_TO_BTU_HR), Q_max))

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    def power_to_setpoint(
        self, target_power_kw: float, state: WaterHeaterState, interval_duration: float
    ) -> float:
        """Convert target power to tank thermostat setpoint.

        Args:
            target_power_kw: Desired power (kW). 0 = off,
                state.element_power = full on.
                INTERNAL: From F7.
            state: Current water heater state.
                INTERNAL: From F1.
            interval_duration: Market interval (seconds).

        Returns:
            Tank thermostat setpoint (°F).
        """
        if target_power_kw >= state.element_power * 0.95:
            return state.tank_temp_upper + 5.0
        elif target_power_kw <= 0:
            return state.tank_temp_lower - 30.0
        else:
            frac = target_power_kw / state.element_power
            low_sp = state.tank_temp_lower - 30.0
            high_sp = state.tank_temp_upper + 5.0
            return low_sp + frac * (high_sp - low_sp)