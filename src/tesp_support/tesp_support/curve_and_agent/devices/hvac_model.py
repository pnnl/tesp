# ============================================================================
# FILE: devices/hvac_model.py
# PURPOSE: Concrete device model for HVAC systems (both heat-pump and
#          air-conditioner-only configurations).
#
# Implements the AbstractDeviceModel contract using a 2-node Equivalent
# Thermal Parameter (ETP) model of the building and HVAC system.  This
# is the agent's internal belief about how the building responds to
# HVAC operation and weather — it need not match the GridLAB-D model
# exactly.
#
# THE ETP MODEL:
#     The building is represented as two coupled thermal nodes:
#
#         Node 1 — Indoor air (temperature T_a, capacitance C_a):
#             C_a · dT_a/dt = UA_env·(T_out − T_a)
#                           + UA_mass·(T_m − T_a)
#                           + Q_hvac
#                           + Q_solar
#                           + Q_internal
#
#         Node 2 — Thermal mass (temperature T_m, capacitance C_m):
#             C_m · dT_m/dt = UA_mass·(T_a − T_m)
#
#     Where:
#         T_a         = indoor air temperature (°F)
#         T_m         = thermal mass temperature (°F, walls/furniture)
#         T_out       = outdoor air temperature (°F)
#         C_a         = air thermal capacitance (Btu/°F)
#         C_m         = mass thermal capacitance (Btu/°F)
#         UA_env      = envelope conductance (Btu/hr·°F)
#         UA_mass     = mass-to-air conductance (Btu/hr·°F)
#         Q_hvac      = HVAC thermal output (Btu/hr, negative for cooling)
#                       = electrical_power_kW × COP × 3412.14
#         Q_solar     = solar heat gain (Btu/hr)
#         Q_internal  = internal heat gain from occupants, appliances (Btu/hr)
#
#     The electrical-to-thermal conversion depends on mode:
#         Cooling: Q_hvac = −P_elec × cooling_COP × 3412.14
#         Heating (heat pump): Q_hvac = +P_elec × heating_COP × 3412.14
#         Heating (AC-only / resistive backup): Q_hvac = +P_elec × 3412.14
#
# GRIDLAB-D INTERFACE:
#     This model does NOT read from or write to GridLAB-D.  All GridLAB-D
#     interaction is through the simulator interface (F1 reads HVACState,
#     F9 writes DeviceCommand).  The ETP parameters are initialized from
#     the first HVACState observation and may be periodically recalibrated.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.device_model.AbstractDeviceModel
#     Uses:          abstractions.device_state.AbstractDeviceState
#                    (concretely expects devices.states.ConcreteHVACState)
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - devices/states.py: Provides ConcreteHVACState consumed by this model.
#     - forecasting/continuous_forecast.py: Outdoor temp, solar irradiance,
#       and internal gain forecasts are passed in via the forecasts dict.
#     - forecasting/data_stream_manager.py: Packages forecast data into
#       the bundle that the agent passes to estimate_flexibility().
#     - economics/planning_optimizer.py: May call predict_temperature()
#       for multi-interval pre-conditioning optimization.
#     - agent.py (DeviceAgent): Calls estimate_flexibility() during the
#       Active phase and translate_power_to_command() via the Command
#       Arbiter during delivery.
#
# CONSUMED FORECAST STREAMS (via forecasts dict):
#     'outdoor_air_temp'   — ContinuousForecast, EXTERNAL from weather service
#     'solar_irradiance'   — ContinuousForecast, EXTERNAL from weather service
#     'internal_heat_gain' — ContinuousForecast, EXTERNAL from learned model
#     'humidity'           — ContinuousForecast, EXTERNAL from weather service
#                            (optional, for latent load estimation)
#
# CONSUMED SCHEDULE STREAMS (via forecasts dict):
#     'hvac_setpoint_schedule' — ContinuousForecast with low uncertainty,
#                                EXTERNAL from customer thermostat program.
#                                Defines the baseline T_setpoint that
#                                determines Q_baseline in the flexibility
#                                envelope.
#
# CONSUMED CONSTRAINT STREAMS (via constraints list):
#     None strictly required.  HVAC comfort bounds are soft (preference-
#     driven via the amenity cost function) rather than hard constraints.
#     However, if a hard temperature bound is configured (e.g., "never
#     below 65°F"), it would appear here.
# ============================================================================

"""Concrete HVAC device model — 2-node ETP thermal model.

Supports both heat-pump and AC-only configurations.  The device type
is determined from the ``has_heat_pump`` field of the observed
HVACState: when True, heating uses the heat pump COP; when False,
heating uses resistive backup (COP = 1.0).

Key methods:
    estimate_flexibility()        — F2: feasible power range for a market interval.
    translate_power_to_command()  — F8: convert target power to thermostat setpoint.
    predict_temperature()         — Forward integration of the ETP model.
    power_to_setpoint()           — Inverse mapping: power → setpoint.
    setpoint_to_power()           — Forward mapping: setpoint → power.
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from data_types import (
    ContinuousDataPoint,
    DeviceCommand,
    FlexibilityEnvelope,
)
from enums_and_constants import DeviceType

# Unit conversion
_KW_TO_BTU_HR = 3412.14
_WATER_LB_PER_GAL = 8.34  # lb/gal, specific heat ≈ 1 Btu/(lb·°F)


def _interp_forecast(
    forecast: list[ContinuousDataPoint] | None,
    time_offset: float,
    default: float = 0.0,
) -> float:
    """Linearly interpolate a forecast list at the given time offset."""
    if not forecast:
        return default
    if len(forecast) == 1:
        return forecast[0].value
    # clamp to range
    if time_offset <= forecast[0].timestamp:
        return forecast[0].value
    if time_offset >= forecast[-1].timestamp:
        return forecast[-1].value
    for i in range(len(forecast) - 1):
        t0, t1 = forecast[i].timestamp, forecast[i + 1].timestamp
        if t0 <= time_offset <= t1:
            f = (time_offset - t0) / (t1 - t0) if t1 != t0 else 0.0
            return forecast[i].value + f * (forecast[i + 1].value - forecast[i].value)
    return forecast[-1].value


class HVACModel(AbstractDeviceModel):
    """Thermal model of a building with HVAC system, ported from DSOT.

    Implements a 2-node (air + thermal mass) equivalent thermal
    parameter (ETP) model with the following DSOT-equivalent features:
    - Temperature-dependent COP adjustment via polynomial coefficients
    - Humidity-dependent latent load fraction
    - Deadband cycling simulation for accurate flexibility estimation
    - Internal temperature state prediction after market clearing

    The ETP model equations:
        Ca · dTa/dt = UA_env·(To - Ta) + UA_mass·(Tm - Ta) + Qhvac + Qsolar + Qinternal
        Cm · dTm/dt = UA_mass·(Ta - Tm)

    Where:
        Ta = indoor air temperature
        Tm = thermal mass temperature
        To = outdoor air temperature
        Ca = air thermal capacitance
        Cm = mass thermal capacitance
        UA_env = envelope conductance
        UA_mass = mass-air conductance
        Qhvac = HVAC heat input/removal (negative for cooling)
        Qsolar = solar heat gain
        Qinternal = internal heat gain

    Args:
        device_type: HVAC_HEAT_PUMP or HVAC_AC_ONLY.
    """

    # Temperature-dependent COP polynomial coefficients (from DSOT)
    _COOLING_COP_K0 = -0.01363961
    _COOLING_COP_K1 = 0.01066989
    _COOLING_COP_LIMIT = 40.0  # Below this temp, COP is clamped

    _HEATING_COP_K0 = 2.03914613
    _HEATING_COP_K1 = -0.03906753
    _HEATING_COP_K2 = 0.00045617
    _HEATING_COP_K3 = -0.00000203
    _HEATING_COP_LIMIT = 80.0  # Above this temp, COP is clamped

    # Temperature-dependent capacity adjustment coefficients (from DSOT)
    _COOLING_CAP_K0 = 1.48924533
    _COOLING_CAP_K1 = -0.00514995
    _HEATING_CAP_K0 = 0.34148808
    _HEATING_CAP_K1 = 0.00894102
    _HEATING_CAP_K2 = 0.00010787

    _LATENT_LOAD_FRACTION = 0.3

    def __init__(self, device_type: DeviceType):
        self._device_type = device_type
        # Internal state tracking — updated after each market clearing
        self._air_temp_agent: float | None = None
        self._mass_temp_agent: float | None = None

    # ------------------------------------------------------------------
    # COP and capacity adjustment (from DSOT DA_model_parameters)
    # ------------------------------------------------------------------

    def adjusted_cooling_COP(self, base_cop: float, outdoor_temp: float) -> float:
        """Adjust cooling COP based on outdoor temperature.

        Replicates DSOT polynomial COP adjustment.

        Args:
            base_cop: Nominal cooling COP from device spec.
            outdoor_temp: Outdoor air temperature (°F).

        Returns:
            Temperature-adjusted cooling COP.
        """
        t = max(outdoor_temp, self._COOLING_COP_LIMIT)
        denom = self._COOLING_COP_K0 + self._COOLING_COP_K1 * t
        if abs(denom) < 1e-9:
            return base_cop
        return base_cop / denom

    def adjusted_heating_COP(self, base_cop: float, outdoor_temp: float) -> float:
        """Adjust heating COP based on outdoor temperature (heat pump curve).

        Uses a cubic polynomial, matching DSOT's heating COP adjustment.

        Args:
            base_cop: Nominal heating COP from device spec.
            outdoor_temp: Outdoor air temperature (°F).

        Returns:
            Temperature-adjusted heating COP.
        """
        t = min(outdoor_temp, self._HEATING_COP_LIMIT)
        denom = (
            self._HEATING_COP_K0
            + self._HEATING_COP_K1 * t
            + self._HEATING_COP_K2 * t * t
            + self._HEATING_COP_K3 * t * t * t
        )
        if abs(denom) < 1e-9:
            return base_cop
        return base_cop / denom

    def adjusted_cooling_capacity(
        self, design_capacity: float, outdoor_temp: float
    ) -> float:
        """Adjust cooling capacity based on outdoor temperature.

        Args:
            design_capacity: Design cooling capacity (Btu/hr).
            outdoor_temp: Outdoor air temperature (°F).

        Returns:
            Temperature-adjusted cooling capacity (Btu/hr).
        """
        return design_capacity * (
            self._COOLING_CAP_K0 + self._COOLING_CAP_K1 * outdoor_temp
        )

    def adjusted_heating_capacity(
        self, design_capacity: float, outdoor_temp: float
    ) -> float:
        """Adjust heating capacity based on outdoor temperature.

        Args:
            design_capacity: Design heating capacity (Btu/hr).
            outdoor_temp: Outdoor air temperature (°F).

        Returns:
            Temperature-adjusted heating capacity (Btu/hr).
        """
        return design_capacity * (
            self._HEATING_CAP_K0
            + self._HEATING_CAP_K1 * outdoor_temp
            + self._HEATING_CAP_K2 * outdoor_temp * outdoor_temp
        )

    def get_adjusted_COP(self, state: HVACState, outdoor_temp: float) -> float:
        """Get the temperature-adjusted COP for the current mode.

        Args:
            state: Current HVAC state.
            outdoor_temp: Outdoor temperature (°F).

        Returns:
            Adjusted COP value.
        """
        if state.hvac_mode == "cooling":
            return self.adjusted_cooling_COP(state.cooling_COP, outdoor_temp)
        elif state.hvac_mode == "heating":
            return self.adjusted_heating_COP(state.heating_COP, outdoor_temp)
        return state.cooling_COP

    def get_adjusted_capacity(self, state: HVACState, outdoor_temp: float) -> float:
        """Get the temperature-adjusted capacity for the current mode.

        Args:
            state: Current HVAC state.
            outdoor_temp: Outdoor temperature (°F).

        Returns:
            Adjusted capacity (Btu/hr).
        """
        if state.hvac_mode == "cooling":
            return self.adjusted_cooling_capacity(
                state.rated_cooling_capacity, outdoor_temp
            )
        elif state.hvac_mode == "heating":
            return self.adjusted_heating_capacity(
                state.rated_heating_capacity, outdoor_temp
            )
        return state.rated_cooling_capacity

    # ------------------------------------------------------------------
    # Latent load (from DSOT)
    # ------------------------------------------------------------------

    def latent_load_factor(self, humidity: float) -> float:
        """Compute the latent load factor from humidity.

        Replicates the DSOT humidity-dependent latent load calculation.
        Higher humidity increases the effective cooling load.

        Args:
            humidity: Relative humidity (fraction 0.0–1.0).

        Returns:
            Latent load factor (>= 1.0).
        """
        return (
            1.0
            + 0.1
            + self._LATENT_LOAD_FRACTION / (1.0 + math.exp(4.0 - 10.0 * humidity))
        )

    # ------------------------------------------------------------------
    # ETP matrix formulation (from DSOT formulate_bid_rt)
    # ------------------------------------------------------------------

    def _build_etp_matrices(
        self,
        state: HVACState,
        outdoor_temp: float,
        Qi: float,
        Qs: float,
    ) -> tuple:
        """Build the A, B_ON, B_OFF matrices for the ETP model.

        This matches the DSOT formulation in formulate_bid_rt and
        bid_accepted.

        Args:
            state: Current HVAC state.
            outdoor_temp: Outdoor air temperature (°F).
            Qi: Internal heat gain into air (Btu/hr).
            Qs: Solar heat gain into air (Btu/hr).

        Returns:
            (A_ETP, B_ETP_ON, B_ETP_OFF, Qhvac_btu) tuple of numpy-free
            matrix representations as nested lists.
        """
        Ca = state.air_mass
        Cm = state.thermal_mass
        UA = state.UA_envelope
        HM = state.UA_mass
        migf = state.mass_internal_gain_fraction
        msgf = state.mass_solar_gain_fraction

        cap = self.get_adjusted_capacity(state, outdoor_temp)
        lf = self.latent_load_factor(state.humidity)

        if state.hvac_mode == "cooling":
            Qhvac = (-cap / lf) + cap * 0.02
        elif state.hvac_mode == "heating":
            Qhvac = cap + 0.02 * cap
        else:
            Qhvac = 0.0

        Qa_OFF = (1.0 - migf) * Qi + (1.0 - msgf) * Qs
        Qa_ON = Qhvac + (1.0 - migf) * Qi + (1.0 - msgf) * Qs
        QM = migf * Qi + msgf * Qs

        # A matrix (2x2)
        if Ca > 0 and Cm > 0:
            a00 = -(UA + HM) / Ca
            a01 = HM / Ca
            a10 = HM / Cm
            a11 = -HM / Cm

            b_on_0 = (UA * outdoor_temp / Ca) + (Qa_ON / Ca)
            b_off_0 = (UA * outdoor_temp / Ca) + (Qa_OFF / Ca)
            b_on_1 = QM / Cm
            b_off_1 = QM / Cm
        else:
            a00 = a01 = a10 = a11 = 0.0
            b_on_0 = b_off_0 = b_on_1 = b_off_1 = 0.0

        return (
            ((a00, a01), (a10, a11)),
            (b_on_0, b_on_1),
            (b_off_0, b_off_1),
            Qhvac,
        )

    # ------------------------------------------------------------------
    # Deadband cycling simulation (from DSOT formulate_bid_rt)
    # ------------------------------------------------------------------

    def simulate_deadband_cycling(
        self,
        state: HVACState,
        target_setpoint: float,
        outdoor_temp: float,
        Qi: float,
        Qs: float,
        duration_seconds: float,
        n_timesteps: int = 10,
    ) -> tuple[float, float, float]:
        """Simulate HVAC operation with deadband cycling over an interval.

        Integrates the ETP model forward, toggling the HVAC on/off
        when the thermostat deadband boundaries are crossed. Returns
        the average power consumption and final temperatures.

        This replicates the DSOT formulate_bid_rt inner loop.

        Args:
            state: Current HVAC state.
            target_setpoint: Thermostat setpoint for this simulation (°F).
            outdoor_temp: Outdoor temperature (°F).
            Qi: Internal heat gain (Btu/hr).
            Qs: Solar heat gain (Btu/hr).
            duration_seconds: Total simulation duration (seconds).
            n_timesteps: Number of timesteps.

        Returns:
            (avg_power_kw, final_air_temp, final_mass_temp)
        """
        A, B_ON, B_OFF, _ = self._build_etp_matrices(state, outdoor_temp, Qi, Qs)
        deadband = state.deadband

        Ta = (
            self._air_temp_agent
            if self._air_temp_agent is not None
            else state.indoor_air_temp
        )
        Tm = (
            self._mass_temp_agent
            if self._mass_temp_agent is not None
            else state.thermal_mass_temp
        )
        hvac_on = state.hvac_on
        dt_hr = (duration_seconds / n_timesteps) / 3600.0
        on_count = 0

        is_cooling = state.hvac_mode == "cooling"
        cap = self.get_adjusted_capacity(state, outdoor_temp)
        cop = self.get_adjusted_COP(state, outdoor_temp)
        q_cap_kw = cap / max(cop, 1e-9) / _KW_TO_BTU_HR
        if state.power_draw > 0:
            # Use measured runtime draw when available, but never exceed
            # the adjusted physical capacity implied by cap/COP.
            hvac_kw = min(state.power_draw, q_cap_kw)
        else:
            hvac_kw = q_cap_kw

        for _ in range(n_timesteps):
            B = B_ON if hvac_on else B_OFF

            # Simple Euler integration of x' = Ax + B
            dTa = (A[0][0] * Ta + A[0][1] * Tm + B[0]) * dt_hr
            dTm = (A[1][0] * Ta + A[1][1] * Tm + B[1]) * dt_hr
            Ta += dTa
            Tm += dTm

            if hvac_on:
                on_count += 1
                # Check if HVAC should turn off
                if (is_cooling and Ta < target_setpoint - deadband / 2.0) or (not is_cooling and Ta > target_setpoint + deadband / 2.0):
                    hvac_on = False
            else:
                # Check if HVAC should turn on
                if (is_cooling and Ta > target_setpoint + deadband / 2.0) or (not is_cooling and Ta < target_setpoint - deadband / 2.0):
                    hvac_on = True

        duty_cycle = on_count / n_timesteps if n_timesteps > 0 else 0.0
        avg_power = duty_cycle * hvac_kw
        return avg_power, Ta, Tm

    # ------------------------------------------------------------------
    # Temperature prediction
    # ------------------------------------------------------------------

    def predict_temperature(
        self,
        state: HVACState,
        hvac_power_kw: float,
        outdoor_temp_forecast: list[ContinuousDataPoint],
        solar_gain_forecast: list[ContinuousDataPoint] | None,
        internal_gain_forecast: list[ContinuousDataPoint] | None,
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> list[tuple[float, float]]:
        """Predict indoor air temperature trajectory given HVAC power input.

        Integrates the ETP model forward in time using the temperature-
        adjusted COP and latent load factor.

        Args:
            state: Current HVAC state from GridLAB-D (F1 output).
            hvac_power_kw: HVAC electrical power consumption (kW).
            outdoor_temp_forecast: Outdoor temperature over horizon.
            solar_gain_forecast: Solar heat gain forecast (Btu/hr).
            internal_gain_forecast: Internal heat gain forecast (Btu/hr).
            duration_seconds: How far ahead to predict.
            timestep_seconds: Integration timestep.

        Returns:
            List of (time_offset_seconds, predicted_indoor_temp_F).
        """
        Ca = state.air_mass
        Cm = state.thermal_mass
        UA_env = state.UA_envelope
        UA_mass = state.UA_mass

        is_cooling = state.hvac_mode == "cooling"
        To_init = state.outdoor_air_temp
        cop = self.get_adjusted_COP(state, To_init)
        lf = self.latent_load_factor(state.humidity) if is_cooling else 1.0

        if state.hvac_mode == "cooling":
            Qhvac = -hvac_power_kw * cop * _KW_TO_BTU_HR / lf
        elif state.hvac_mode == "heating":
            Qhvac = hvac_power_kw * cop * _KW_TO_BTU_HR
        else:
            Qhvac = 0.0

        Ta = state.indoor_air_temp
        Tm = state.thermal_mass_temp
        dt_hr = timestep_seconds / 3600.0
        n_steps = int(duration_seconds / timestep_seconds)
        trajectory: list[tuple[float, float]] = []

        for i in range(n_steps):
            t = (i + 1) * timestep_seconds
            To = _interp_forecast(outdoor_temp_forecast, t, state.outdoor_air_temp)
            Qsolar = _interp_forecast(solar_gain_forecast, t, state.solar_gain)
            Qint = _interp_forecast(internal_gain_forecast, t, state.internal_gain)

            dTa_dt = (
                UA_env * (To - Ta) + UA_mass * (Tm - Ta) + Qhvac + Qsolar + Qint
            ) / Ca
            dTm_dt = UA_mass * (Ta - Tm) / Cm

            Ta += dTa_dt * dt_hr
            Tm += dTm_dt * dt_hr
            trajectory.append((t, Ta))

        return trajectory

    # ------------------------------------------------------------------
    # Flexibility estimation with deadband cycling
    # ------------------------------------------------------------------

    def estimate_flexibility(
        self,
        state: HVACState,
        outdoor_temp_forecast: list[ContinuousDataPoint],
        solar_gain_forecast: list[ContinuousDataPoint] | None,
        internal_gain_forecast: list[ContinuousDataPoint] | None,
        setpoint_schedule: list[ContinuousDataPoint],
        interval_duration: float,
        comfort_band: float = 2.0,
    ) -> FlexibilityEnvelope:
        """Estimate the feasible power range using deadband simulation.

        Runs the ETP model with deadband cycling at multiple setpoint
        offsets to determine the actual Q_min/Q_max/Q_baseline,
        matching the DSOT formulate_bid_rt approach.

        Args:
            state: Current HVAC state.
            outdoor_temp_forecast: Outdoor temp over interval.
            solar_gain_forecast: Solar gain over interval.
            internal_gain_forecast: Internal gain over interval.
            setpoint_schedule: Customer's desired setpoint over interval.
            interval_duration: Length of the market interval (seconds).
            comfort_band: Acceptable deviation from setpoint (°F).

        Returns:
            FlexibilityEnvelope with Q_min, Q_max, Q_baseline.
        """
        setpoint = (
            setpoint_schedule[0].value
            if setpoint_schedule
            else state.thermostat_setpoint
        )
        To = state.outdoor_air_temp
        if outdoor_temp_forecast:
            To = outdoor_temp_forecast[0].value

        # Compute internal and solar gains for this interval
        Qs = state.solar_gain
        if solar_gain_forecast:
            Qs = solar_gain_forecast[0].value

        Qi = state.internal_gain
        if internal_gain_forecast:
            Qi = internal_gain_forecast[0].value

        # Get adjusted COP and capacity for Q_max calculation
        cop = self.get_adjusted_COP(state, To)
        cap = self.get_adjusted_capacity(state, To)
        Q_max_kw = cap / cop / _KW_TO_BTU_HR

        # Simulate at multiple setpoints around the baseline to build
        # a quantity curve, matching DSOT's 5-point approach
        n_points = 5
        quantities = []
        for i in range(n_points):
            offset = (i - (n_points - 1) / 2.0) / ((n_points - 1) / 2.0) * comfort_band
            test_setpoint = setpoint + offset
            avg_power, _, _ = self.simulate_deadband_cycling(
                state=state,
                target_setpoint=test_setpoint,
                outdoor_temp=To,
                Qi=Qi,
                Qs=Qs,
                duration_seconds=interval_duration,
            )
            quantities.append(avg_power)

        Q_min = max(0.0, min(quantities))
        Q_max = min(Q_max_kw, max(quantities))

        # Baseline = simulation at the nominal setpoint
        Q_baseline, _, _ = self.simulate_deadband_cycling(
            state=state,
            target_setpoint=setpoint,
            outdoor_temp=To,
            Qi=Qi,
            Qs=Qs,
            duration_seconds=interval_duration,
        )
        Q_baseline = max(Q_min, min(Q_max, Q_baseline))

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    # ------------------------------------------------------------------
    # Power ↔ setpoint conversion (with COP adjustment)
    # ------------------------------------------------------------------

    def power_to_setpoint(
        self,
        target_power_kw: float,
        state: HVACState,
        outdoor_temp: float,
        interval_duration: float,
    ) -> float:
        """Convert a target power consumption to a thermostat setpoint.

        Uses temperature-adjusted COP and latent load factor.

        Args:
            target_power_kw: Desired electrical power (kW).
            state: Current HVAC state.
            outdoor_temp: Current outdoor temperature (°F).
            interval_duration: Market interval length (seconds).

        Returns:
            Thermostat setpoint (°F).
        """
        is_cooling = state.hvac_mode == "cooling"
        cop = self.get_adjusted_COP(state, outdoor_temp)
        lf = self.latent_load_factor(state.humidity) if is_cooling else 1.0
        Ca = state.air_mass
        UA_env = state.UA_envelope
        ih = interval_duration / 3600.0
        Ta = (
            self._air_temp_agent
            if self._air_temp_agent is not None
            else state.indoor_air_temp
        )
        To = outdoor_temp

        denom = UA_env + Ca / ih
        if is_cooling:
            sp = (
                UA_env * To + Ca * Ta / ih - target_power_kw * cop * _KW_TO_BTU_HR / lf
            ) / denom
        else:
            sp = (
                target_power_kw * cop * _KW_TO_BTU_HR + UA_env * To + Ca * Ta / ih
            ) / denom
        return sp

    def setpoint_to_power(
        self,
        setpoint: float,
        state: HVACState,
        outdoor_temp: float,
        interval_duration: float,
    ) -> float:
        """Convert a thermostat setpoint to expected power consumption.

        Uses temperature-adjusted COP and latent load factor.

        Args:
            setpoint: Thermostat setpoint (°F).
            state: Current HVAC state.
            outdoor_temp: Outdoor temperature (°F).
            interval_duration: Market interval (seconds).

        Returns:
            Expected average power consumption (kW).
        """
        is_cooling = state.hvac_mode == "cooling"
        cop = self.get_adjusted_COP(state, outdoor_temp)
        lf = self.latent_load_factor(state.humidity) if is_cooling else 1.0
        Ca = state.air_mass
        UA_env = state.UA_envelope
        ih = interval_duration / 3600.0
        Ta = (
            self._air_temp_agent
            if self._air_temp_agent is not None
            else state.indoor_air_temp
        )

        if is_cooling:
            Q_total = UA_env * (outdoor_temp - setpoint) + Ca * (Ta - setpoint) / ih
        else:
            Q_total = UA_env * (setpoint - outdoor_temp) + Ca * (setpoint - Ta) / ih

        cap = self.get_adjusted_capacity(state, outdoor_temp)
        P = max(0.0, Q_total) * lf / (cop * _KW_TO_BTU_HR)
        P = min(P, cap / cop / _KW_TO_BTU_HR)
        return P

    # ------------------------------------------------------------------
    # Internal state tracking
    # ------------------------------------------------------------------

    def update_internal_state(
        self,
        state: HVACState,
        target_setpoint: float,
        outdoor_temp: float,
        duration_seconds: float,
    ) -> tuple[float, float]:
        """Predict and store the internal air and mass temperature after
        operating at the given setpoint for the specified duration.

        This replicates the DSOT bid_accepted post-clearing forward
        simulation that updates air_temp_agent and mass_temp.

        Args:
            state: Current HVAC state.
            target_setpoint: Setpoint to simulate at (°F).
            outdoor_temp: Outdoor temperature (°F).
            duration_seconds: Duration to simulate (seconds).

        Returns:
            (predicted_air_temp, predicted_mass_temp)
        """
        Qi = state.internal_gain
        Qs = state.solar_gain

        _, final_air, final_mass = self.simulate_deadband_cycling(
            state=state,
            target_setpoint=target_setpoint,
            outdoor_temp=outdoor_temp,
            Qi=Qi,
            Qs=Qs,
            duration_seconds=duration_seconds,
        )
        self._air_temp_agent = final_air
        self._mass_temp_agent = final_mass
        return final_air, final_mass

    def sync_from_gridlabd(self, state: HVACState) -> None:
        """Reset internal state tracking from GridLAB-D observation.

        Called at the start of each observation cycle (F1) to sync
        the agent's internal belief with the simulator's ground truth.

        Args:
            state: Fresh state from GridLAB-D.
        """
        self._air_temp_agent = state.indoor_air_temp
        self._mass_temp_agent = state.thermal_mass_temp