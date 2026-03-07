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
from typing import Dict, List, Optional, Tuple
from data_types import (
    HVACState, WaterHeaterState, EVChargerState, BatteryState,
    FlexibilityEnvelope, DeviceCommand, ContinuousDataPoint,
    QuantilePoint
)
from enums_and_constants import DeviceType

# Unit conversion
_KW_TO_BTU_HR = 3412.14
_WATER_LB_PER_GAL = 8.34  # lb/gal, specific heat ≈ 1 Btu/(lb·°F)


def _interp_forecast(forecast: Optional[List[ContinuousDataPoint]],
                     time_offset: float,
                     default: float = 0.0) -> float:
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
    """Simplified thermal model of a building with HVAC system.
    
    Implements a 2-node (air + thermal mass) equivalent thermal
    parameter (ETP) model. This is the agent's internal belief
    about how the building responds to HVAC operation and weather.
    
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

    def __init__(self, device_type: DeviceType):
        self._device_type = device_type

    def predict_temperature(
        self,
        state: HVACState,
        hvac_power_kw: float,
        outdoor_temp_forecast: List[ContinuousDataPoint],
        solar_gain_forecast: Optional[List[ContinuousDataPoint]],
        internal_gain_forecast: Optional[List[ContinuousDataPoint]],
        duration_seconds: float,
        timestep_seconds: float = 60.0
    ) -> List[Tuple[float, float]]:
        """Predict indoor air temperature trajectory given HVAC power input.
        
        Integrates the ETP model forward in time from the current state,
        assuming a constant or scheduled HVAC power input and the
        provided weather forecasts.
        
        Args:
            state: Current HVAC state from GridLAB-D (F1 output).
                INTERNAL: Provided by the agent's state observation.
            hvac_power_kw: HVAC electrical power consumption (kW).
                The thermal output is power × COP.
            outdoor_temp_forecast: Outdoor temperature over the
                prediction horizon.
                INTERNAL: From DataStreamManager.
            solar_gain_forecast: Solar heat gain forecast (Btu/hr).
                INTERNAL: From DataStreamManager. Optional.
            internal_gain_forecast: Internal heat gain forecast (Btu/hr).
                INTERNAL: From DataStreamManager. Optional.
            duration_seconds: How far ahead to predict.
            timestep_seconds: Integration timestep.
        
        Returns:
            List of (time_offset_seconds, predicted_indoor_temp_F).
        """
        Ca = state.air_mass
        Cm = state.thermal_mass
        UA_env = state.UA_envelope
        UA_mass = state.UA_mass

        if state.hvac_mode == "cooling":
            Qhvac = -hvac_power_kw * state.cooling_COP * _KW_TO_BTU_HR
        elif state.hvac_mode == "heating":
            Qhvac = hvac_power_kw * state.heating_COP * _KW_TO_BTU_HR
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

            dTa_dt = (UA_env * (To - Ta) + UA_mass * (Tm - Ta)
                      + Qhvac + Qsolar + Qint) / Ca
            dTm_dt = UA_mass * (Ta - Tm) / Cm

            Ta += dTa_dt * dt_hr
            Tm += dTm_dt * dt_hr
            trajectory.append((t, Ta))

        return trajectory

    def estimate_flexibility(
        self,
        state: HVACState,
        outdoor_temp_forecast: List[ContinuousDataPoint],
        solar_gain_forecast: Optional[List[ContinuousDataPoint]],
        internal_gain_forecast: Optional[List[ContinuousDataPoint]],
        setpoint_schedule: List[ContinuousDataPoint],
        interval_duration: float,
        comfort_band: float = 2.0
    ) -> FlexibilityEnvelope:
        """Estimate the feasible power range for the upcoming interval.
        
        Determines Q_min, Q_max, and Q_baseline by evaluating what
        power levels keep the indoor temperature within the comfort
        band around the setpoint over the interval.
        
        Args:
            state: Current HVAC state.
                INTERNAL: From agent's state observation (F1).
            outdoor_temp_forecast: Outdoor temp over interval.
                INTERNAL: From DataStreamManager.
            solar_gain_forecast: Solar gain over interval.
                INTERNAL: From DataStreamManager.
            internal_gain_forecast: Internal gain over interval.
                INTERNAL: From DataStreamManager.
            setpoint_schedule: Customer's desired setpoint over interval.
                INTERNAL: From DataStreamManager schedule stream.
            interval_duration: Length of the market interval (seconds).
            comfort_band: Acceptable deviation from setpoint (°F).
                INTERNAL: Derived from customer preference k.
        
        Returns:
            FlexibilityEnvelope with Q_min, Q_max, Q_baseline, and
            confidence-level variants.
        """
        setpoint = setpoint_schedule[0].value if setpoint_schedule else state.thermostat_setpoint
        is_cooling = state.hvac_mode == "cooling"
        COP = state.cooling_COP if is_cooling else state.heating_COP
        rated_cap = state.rated_cooling_capacity if is_cooling else state.rated_heating_capacity

        Q_max_kw = rated_cap / COP / _KW_TO_BTU_HR
        Q_min = 0.0

        To = state.outdoor_air_temp
        if outdoor_temp_forecast:
            To = outdoor_temp_forecast[0].value

        Q_baseline = self.setpoint_to_power(setpoint, state, To, interval_duration)

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max_kw,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    def power_to_setpoint(
        self,
        target_power_kw: float,
        state: HVACState,
        outdoor_temp: float,
        interval_duration: float
    ) -> float:
        """Convert a target power consumption to a thermostat setpoint.
        
        This is the inverse of the flexibility model: given that we
        want the HVAC to consume target_power_kw over the interval,
        what thermostat setpoint achieves that?
        
        Used by F8 (control signal translation).
        
        Args:
            target_power_kw: Desired electrical power (kW).
                INTERNAL: From F7 (price response evaluation).
            state: Current HVAC state.
                INTERNAL: From F1.
            outdoor_temp: Current outdoor temperature (°F).
                INTERNAL: From state or forecast.
            interval_duration: Market interval length (seconds).
        
        Returns:
            Thermostat setpoint (°F) that would result in approximately
            the target power consumption over the interval.
        """
        is_cooling = state.hvac_mode == "cooling"
        COP = state.cooling_COP if is_cooling else state.heating_COP
        Ca = state.air_mass
        UA_env = state.UA_envelope
        ih = interval_duration / 3600.0  # interval in hours
        Ta = state.indoor_air_temp
        To = outdoor_temp

        denom = UA_env + Ca / ih
        if is_cooling:
            sp = (UA_env * To + Ca * Ta / ih
                  - target_power_kw * COP * _KW_TO_BTU_HR) / denom
        else:
            sp = (target_power_kw * COP * _KW_TO_BTU_HR
                  + UA_env * To + Ca * Ta / ih) / denom
        return sp

    def setpoint_to_power(
        self,
        setpoint: float,
        state: HVACState,
        outdoor_temp: float,
        interval_duration: float
    ) -> float:
        """Convert a thermostat setpoint to expected power consumption.
        
        Given a setpoint, predict the average power the HVAC will
        consume over the interval. This is the forward model that
        power_to_setpoint inverts.
        
        Args:
            setpoint: Thermostat setpoint (°F).
            state: Current HVAC state.
            outdoor_temp: Outdoor temperature (°F).
            interval_duration: Market interval (seconds).
        
        Returns:
            Expected average power consumption (kW).
        """
        is_cooling = state.hvac_mode == "cooling"
        COP = state.cooling_COP if is_cooling else state.heating_COP
        Ca = state.air_mass
        UA_env = state.UA_envelope
        ih = interval_duration / 3600.0
        Ta = state.indoor_air_temp

        if is_cooling:
            Q_total = UA_env * (outdoor_temp - setpoint) + Ca * (Ta - setpoint) / ih
        else:
            Q_total = UA_env * (setpoint - outdoor_temp) + Ca * (setpoint - Ta) / ih

        rated_cap = state.rated_cooling_capacity if is_cooling else state.rated_heating_capacity
        P = max(0.0, Q_total) / (COP * _KW_TO_BTU_HR)
        P = min(P, rated_cap / COP / _KW_TO_BTU_HR)
        return P


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
        timestep_seconds: float = 60.0
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
        interval_duration: float
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
        Q_min = 0.0
        max_temp = state.thermostat_setpoint + 10.0
        Q_max = 0.0 if state.tank_temp_upper >= max_temp else state.element_power

        avg_temp = (state.tank_temp_upper + state.tank_temp_lower) / 2.0
        standby_loss = state.tank_UA * (avg_temp - ambient_temp)
        Q_baseline = max(0.0, min(standby_loss / _KW_TO_BTU_HR, Q_max))

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    def power_to_setpoint(
        self,
        target_power_kw: float,
        state: WaterHeaterState,
        interval_duration: float
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
        timestep_seconds: float = 60.0
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
        time_until_departure: Optional[float] = None
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
                Q_min=0.0, Q_max=0.0, Q_baseline=0.0,
                interval_start=0.0, interval_end=interval_duration)

        max_rate = state.max_charge_rate
        if state.soc >= state.soc_at_max_taper:
            taper = max(0.0, (1.0 - state.soc) / (1.0 - state.soc_at_max_taper))
            Q_max = max_rate * taper
        else:
            Q_max = max_rate

        Q_min = 0.0
        if (departure_constraint is not None
                and time_until_departure is not None
                and time_until_departure > 0):
            _, target_soc = departure_constraint
            soc_needed = target_soc - state.soc
            if soc_needed > 0:
                energy_needed = soc_needed * state.battery_capacity / state.charger_efficiency
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
            Q_min=Q_min, Q_max=Q_max, Q_baseline=Q_baseline,
            interval_start=0.0, interval_end=interval_duration)

    def power_to_command(
        self,
        target_power_kw: float,
        state: EVChargerState
    ) -> float:
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
        wohler_exponent: float = 1.5
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
        timestep_seconds: float = 60.0
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
        interval_duration: float
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
            max_discharge = min(state.max_discharge_rate,
                                dischargeable / ih * eta)
        else:
            max_discharge = 0.0
        Q_min = -max_discharge

        chargeable = (state.soc_max_bms - state.soc) * capacity
        if chargeable > 0:
            max_charge = min(state.max_charge_rate,
                             chargeable / (ih * eta))
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
            Q_min=Q_min, Q_max=Q_max, Q_baseline=Q_baseline,
            interval_start=0.0, interval_end=interval_duration)

    def marginal_degradation_cost(
        self,
        state: BatteryState,
        power_kw: float
    ) -> float:
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
        self,
        state: BatteryState,
        V_stored: float,
        degradation_cost: float
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
        duration_seconds: float
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

        cost = base_cost_per_kwh * soc_stress * crate_stress * temp_stress * throughput_kwh

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
        actual_rate = self._cumulative_degradation_cost / self._cumulative_throughput_kwh
        return actual_rate / base_cost_per_kwh