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

from typing import Dict, List, Optional, Tuple
from data_types import (
    HVACState, WaterHeaterState, EVChargerState, BatteryState,
    FlexibilityEnvelope, DeviceCommand, ContinuousDataPoint,
    QuantilePoint
)
from enums_and_constants import DeviceType


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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError


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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError


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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError


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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

    @property
    def budget_utilization_rate(self) -> float:
        """Ratio of actual degradation rate to planned rate.
        
        > 1.0 means cycling faster than expected (raise costs).
        < 1.0 means cycling slower than expected (could lower costs).
        
        Returns:
            Budget utilization ratio.
        """
        raise NotImplementedError