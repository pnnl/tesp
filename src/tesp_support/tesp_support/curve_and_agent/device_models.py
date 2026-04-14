# ============================================================================
# FILE: device_models.py
# PURPOSE: Internal physics models used by device agents for flexibility
#          estimation and control translation. These are simplified models
#          representing the agent's BELIEF about device physics. The ground
#          truth lives in GridLAB-D; these models need not be high fidelity.
#
# INTERNAL: These models are used by agent functions F2 (flexibility
#           estimation) and F8 (control signal translation). They do NOT
#           read from or write to GridLAB-D.
# ============================================================================

import math
from typing import List, Optional, Tuple
from data_types import (
    HVACState,
    WaterHeaterState,
    EVChargerState,
    BatteryState,
    FlexibilityEnvelope,
    ContinuousDataPoint,
    QuantilePoint,
)
from enums_and_constants import DeviceType

# Unit conversion
_KW_TO_BTU_HR = 3412.14
_WATER_LB_PER_GAL = 8.34  # lb/gal, specific heat ≈ 1 Btu/(lb·°F)


def _interp_forecast(
    forecast: Optional[List[ContinuousDataPoint]],
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


class HVACModel:
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
        self._air_temp_agent: Optional[float] = None
        self._mass_temp_agent: Optional[float] = None

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
    ) -> Tuple:
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
    ) -> Tuple[float, float, float]:
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
                if is_cooling and Ta < target_setpoint - deadband / 2.0:
                    hvac_on = False
                elif not is_cooling and Ta > target_setpoint + deadband / 2.0:
                    hvac_on = False
            else:
                # Check if HVAC should turn on
                if is_cooling and Ta > target_setpoint + deadband / 2.0:
                    hvac_on = True
                elif not is_cooling and Ta < target_setpoint - deadband / 2.0:
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
        outdoor_temp_forecast: List[ContinuousDataPoint],
        solar_gain_forecast: Optional[List[ContinuousDataPoint]],
        internal_gain_forecast: Optional[List[ContinuousDataPoint]],
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> List[Tuple[float, float]]:
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
        trajectory: List[Tuple[float, float]] = []

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
        outdoor_temp_forecast: List[ContinuousDataPoint],
        solar_gain_forecast: Optional[List[ContinuousDataPoint]],
        internal_gain_forecast: Optional[List[ContinuousDataPoint]],
        setpoint_schedule: List[ContinuousDataPoint],
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
    ) -> Tuple[float, float]:
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
        inlet_temp_forecast: Optional[ContinuousDataPoint],
        ambient_temp: float,
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> List[Tuple[float, float, float]]:
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

        trajectory: List[Tuple[float, float, float]] = []
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
        inlet_temp_forecast: Optional[ContinuousDataPoint],
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


class EVChargerModel:
    """Model of EV charging behavior including SOC-dependent taper.

    Models the charging process as constant-power up to the taper
    SOC, then linearly decreasing power above the taper point
    (CCCV charging profile approximation).
    """

    def predict_soc(
        self,
        state: EVChargerState,
        charge_power_kw: float,
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> List[Tuple[float, float]]:
        """Predict SOC trajectory at a given charge power.

        Args:
            state: Current EV charger state from GridLAB-D.
                INTERNAL: From F1.
            charge_power_kw: Target charging power (kW).
                Applied as min(charge_power_kw, BMS-limited max at
                current SOC).
            duration_seconds: Prediction horizon.
            timestep_seconds: Integration timestep.

        Returns:
            List of (time_offset_seconds, predicted_soc).
        """
        if not state.vehicle_plugged_in:
            return [(0.0, state.soc)]

        soc = state.soc
        capacity = state.battery_capacity
        efficiency = state.charger_efficiency
        max_rate = state.max_charge_rate
        taper_soc = state.soc_at_max_taper

        trajectory: List[Tuple[float, float]] = []
        n_steps = int(duration_seconds / timestep_seconds)
        dt_hr = timestep_seconds / 3600.0

        for i in range(n_steps):
            t = (i + 1) * timestep_seconds
            if soc >= taper_soc:
                taper_factor = max(0.0, (1.0 - soc) / (1.0 - taper_soc))
                effective_max = max_rate * taper_factor
            else:
                effective_max = max_rate

            actual_power = max(0.0, min(charge_power_kw, effective_max))
            dc_power = actual_power * efficiency
            delta_soc = dc_power * dt_hr / capacity
            soc = min(1.0, soc + delta_soc)
            trajectory.append((t, soc))

        return trajectory

    def estimate_flexibility(
        self,
        state: EVChargerState,
        departure_constraint: Optional[Tuple[float, float]],
        preferred_soc: float,
        interval_duration: float,
        time_until_departure: Optional[float] = None,
    ) -> FlexibilityEnvelope:
        """Estimate feasible charging power range.

        Q_min: minimum charge rate to meet departure SOC constraint
            in the remaining time (may be > 0 if deadline is close).
        Q_max: maximum charge rate allowed by EVSE and BMS.
        Q_baseline: charge rate to reach preferred SOC by departure.

        Args:
            state: Current EV charger state.
                INTERNAL: From F1.
            departure_constraint: (departure_time, min_soc) tuple.
                INTERNAL: From DataStreamManager constraint stream.
                EXTERNAL origin: Customer EV app input.
            preferred_soc: Customer's desired SOC (fraction).
                INTERNAL: From DataStreamManager schedule stream.
                EXTERNAL origin: Customer setting.
            interval_duration: Market interval (seconds).
            time_until_departure: Seconds until departure. If None,
                no departure constraint is applied.

        Returns:
            FlexibilityEnvelope. Q_min = 0 if no vehicle plugged in.
        """
        if not state.vehicle_plugged_in:
            return FlexibilityEnvelope(
                Q_min=0.0,
                Q_max=0.0,
                Q_baseline=0.0,
                interval_start=0.0,
                interval_end=interval_duration,
            )

        max_rate = state.max_charge_rate
        if state.soc >= state.soc_at_max_taper:
            taper = max(0.0, (1.0 - state.soc) / (1.0 - state.soc_at_max_taper))
            Q_max = max_rate * taper
        else:
            Q_max = max_rate

        Q_min = 0.0
        if (
            departure_constraint is not None
            and time_until_departure is not None
            and time_until_departure > 0
        ):
            _, target_soc = departure_constraint
            soc_needed = target_soc - state.soc
            if soc_needed > 0:
                energy_needed = (
                    soc_needed * state.battery_capacity / state.charger_efficiency
                )
                min_power = energy_needed / (time_until_departure / 3600.0)
                Q_min = min(min_power, Q_max)

        soc_gap = preferred_soc - state.soc
        if soc_gap > 0:
            energy = soc_gap * state.battery_capacity / state.charger_efficiency
            if time_until_departure and time_until_departure > 0:
                Q_baseline = min(energy / (time_until_departure / 3600.0), Q_max)
            else:
                Q_baseline = min(energy / (interval_duration / 3600.0), Q_max)
        else:
            Q_baseline = 0.0
        Q_baseline = max(Q_baseline, Q_min)

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    def power_to_command(self, target_power_kw: float, state: EVChargerState) -> float:
        """Convert target power to actual charge rate command.

        Applies BMS taper limits and EVSE min/max constraints.

        Args:
            target_power_kw: Desired power (kW).
                INTERNAL: From F7.
            state: Current state.
                INTERNAL: From F1.

        Returns:
            Actual charge rate to command (kW). May differ from
            target due to BMS limits.
        """
        if not state.vehicle_plugged_in:
            return 0.0

        if state.soc >= state.soc_at_max_taper:
            taper = max(0.0, (1.0 - state.soc) / (1.0 - state.soc_at_max_taper))
            effective_max = state.max_charge_rate * taper
        else:
            effective_max = state.max_charge_rate

        command = max(0.0, min(target_power_kw, effective_max))
        if 0 < command < state.min_charge_rate:
            command = 0.0
        return command


class BatteryModel:
    """Model of a home battery storage system with degradation tracking.

    Handles:
    - SOC dynamics with charge/discharge efficiency
    - SOC-dependent power limits (BMS taper)
    - Degradation cost calculation (throughput-based with stress factors)
    - Marginal value of stored energy (from planning optimizer)
    """

    def __init__(
        self,
        replacement_cost: float = 10000.0,
        rated_cycles: int = 5000,
        rated_dod: float = 0.80,
        wohler_exponent: float = 1.5,
    ):
        """Initialize battery model with degradation parameters.

        Args:
            replacement_cost: Cost to replace the battery ($).
                EXTERNAL: From battery specifications / installer quote.
            rated_cycles: Cycle life at rated DoD.
                EXTERNAL: From manufacturer datasheet.
            rated_dod: Depth of discharge for rated cycle life (fraction).
                EXTERNAL: From manufacturer datasheet.
            wohler_exponent: Fatigue curve exponent for cycle depth
                adjustment. Higher values mean shallow cycles are
                disproportionately cheaper.
                EXTERNAL: From battery characterization data.
        """
        self._replacement_cost = replacement_cost
        self._rated_cycles = rated_cycles
        self._rated_dod = rated_dod
        self._wohler_exponent = wohler_exponent
        self._cumulative_throughput_kwh: float = 0.0
        self._cumulative_degradation_cost: float = 0.0
        self._energy_capacity: float = 13.5  # default; updated from state

    def predict_soc(
        self,
        state: BatteryState,
        power_kw: float,
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> List[Tuple[float, float]]:
        """Predict SOC trajectory at a given power level.

        Args:
            state: Current battery state from GridLAB-D.
                INTERNAL: From F1.
            power_kw: Power flow (kW). Positive = charging,
                negative = discharging.
            duration_seconds: Prediction horizon.
            timestep_seconds: Integration timestep.

        Returns:
            List of (time_offset_seconds, predicted_soc).
        """
        self._energy_capacity = state.energy_capacity
        soc = state.soc
        capacity = state.energy_capacity
        eta = math.sqrt(state.round_trip_efficiency)

        trajectory: List[Tuple[float, float]] = []
        n_steps = int(duration_seconds / timestep_seconds)
        dt_hr = timestep_seconds / 3600.0

        for i in range(n_steps):
            t = (i + 1) * timestep_seconds
            if power_kw >= 0:
                energy_stored = power_kw * eta * dt_hr
            else:
                energy_stored = power_kw / eta * dt_hr
            soc += energy_stored / capacity
            soc = max(state.soc_min_bms, min(state.soc_max_bms, soc))
            trajectory.append((t, soc))

        return trajectory

    def estimate_flexibility(
        self,
        state: BatteryState,
        soc_reserve: float,
        soc_preferred: float,
        interval_duration: float,
    ) -> FlexibilityEnvelope:
        """Estimate feasible charge/discharge power range.

        Returns a bidirectional envelope where Q_min is negative
        (maximum discharge) and Q_max is positive (maximum charge).

        Args:
            state: Current battery state.
                INTERNAL: From F1.
            soc_reserve: Hard minimum SOC (backup reserve).
                INTERNAL: From DataStreamManager constraint stream.
                EXTERNAL origin: Customer setting, dynamic outage risk.
            soc_preferred: Customer's comfortable SOC level.
                INTERNAL: From DataStreamManager schedule stream.
                EXTERNAL origin: Customer setting.
            interval_duration: Market interval (seconds).

        Returns:
            FlexibilityEnvelope. Q_min < 0 (discharge), Q_max > 0 (charge).
        """
        self._energy_capacity = state.energy_capacity
        eta = math.sqrt(state.round_trip_efficiency)
        ih = interval_duration / 3600.0
        capacity = state.energy_capacity

        dischargeable = (state.soc - soc_reserve) * capacity
        if dischargeable > 0:
            max_discharge = min(state.max_discharge_rate, dischargeable / ih * eta)
        else:
            max_discharge = 0.0
        Q_min = -max_discharge

        chargeable = (state.soc_max_bms - state.soc) * capacity
        if chargeable > 0:
            max_charge = min(state.max_charge_rate, chargeable / (ih * eta))
        else:
            max_charge = 0.0
        Q_max = max_charge

        if abs(state.soc - soc_preferred) < 0.01:
            Q_baseline = 0.0
        elif state.soc < soc_preferred:
            needed = (soc_preferred - state.soc) * capacity
            Q_baseline = min(Q_max, needed / (ih * eta))
        else:
            excess = (state.soc - soc_preferred) * capacity
            Q_baseline = max(Q_min, -(excess * eta / ih))

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    def marginal_degradation_cost(self, state: BatteryState, power_kw: float) -> float:
        """Compute the marginal degradation cost of cycling at given power.

        Accounts for:
        - Base throughput cost (replacement_cost / lifetime_throughput)
        - SOC stress factor (elevated at extreme SOC)
        - C-rate stress factor (elevated at high power)
        - Temperature stress factor (elevated at temperature extremes)

        Args:
            state: Current battery state (SOC, temperature).
                INTERNAL: From F1.
            power_kw: Absolute power magnitude (kW).

        Returns:
            Marginal degradation cost ($/kWh of throughput).
        """
        self._energy_capacity = state.energy_capacity
        capacity = state.energy_capacity
        lifetime_throughput = self._rated_cycles * self._rated_dod * capacity * 2.0
        base_cost = self._replacement_cost / lifetime_throughput

        soc_stress = 1.0 + 2.0 * (state.soc - 0.5) ** 2
        c_rate = abs(power_kw) / capacity
        crate_stress = 1.0 + 0.5 * c_rate
        temp_stress = 1.0 + 0.05 * abs(state.cell_temperature - 25.0)

        return base_cost * soc_stress * crate_stress * temp_stress

    def compute_charge_discharge_thresholds(
        self, state: BatteryState, V_stored: float, degradation_cost: float
    ) -> Tuple[float, float]:
        """Compute the price thresholds for charging and discharging.

        Charge threshold: price below which charging is profitable.
        Discharge threshold: price above which discharging is profitable.
        The gap between them is the degradation-driven dead band.

        Args:
            state: Current battery state.
                INTERNAL: From F1.
            V_stored: Marginal value of stored energy ($/kWh).
                INTERNAL: From PlanningOptimizer output.
            degradation_cost: Current marginal degradation cost ($/kWh).
                INTERNAL: From self.marginal_degradation_cost().

        Returns:
            (charge_threshold, discharge_threshold) in $/kWh.
        """
        charge_threshold = V_stored - degradation_cost
        discharge_threshold = V_stored + degradation_cost
        return (charge_threshold, discharge_threshold)

    def update_degradation_tracking(
        self,
        throughput_kwh: float,
        avg_soc: float,
        avg_power_kw: float,
        avg_temperature: float,
        duration_seconds: float,
    ) -> float:
        """Update cumulative degradation tracking after delivery.

        Called during reconciliation (F13) to track actual battery
        life consumption.

        Args:
            throughput_kwh: Total energy throughput in the period.
            avg_soc: Average SOC during the period.
            avg_power_kw: Average absolute power during the period.
            avg_temperature: Average cell temperature (°C).
            duration_seconds: Length of the period.

        Returns:
            Degradation cost incurred in this period ($).
        """
        capacity = self._energy_capacity
        lifetime_throughput = self._rated_cycles * self._rated_dod * capacity * 2.0
        base_cost_per_kwh = self._replacement_cost / lifetime_throughput

        soc_stress = 1.0 + 2.0 * (avg_soc - 0.5) ** 2
        c_rate = avg_power_kw / capacity
        crate_stress = 1.0 + 0.5 * c_rate
        temp_stress = 1.0 + 0.05 * abs(avg_temperature - 25.0)

        cost = (
            base_cost_per_kwh * soc_stress * crate_stress * temp_stress * throughput_kwh
        )

        self._cumulative_throughput_kwh += throughput_kwh
        self._cumulative_degradation_cost += cost
        return cost

    @property
    def budget_utilization_rate(self) -> float:
        """Ratio of actual degradation rate to planned rate.

        > 1.0 means cycling faster than expected (raise costs).
        < 1.0 means cycling slower than expected (could lower costs).

        Returns:
            Budget utilization ratio.
        """
        if self._cumulative_throughput_kwh == 0.0:
            return 0.0
        capacity = self._energy_capacity
        lifetime_throughput = self._rated_cycles * self._rated_dod * capacity * 2.0
        base_cost_per_kwh = self._replacement_cost / lifetime_throughput
        actual_rate = (
            self._cumulative_degradation_cost / self._cumulative_throughput_kwh
        )
        return actual_rate / base_cost_per_kwh
