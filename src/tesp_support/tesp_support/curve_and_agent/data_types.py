# ============================================================================
# FILE: data_types.py
# PURPOSE: Shared data structures used across all modules.
#          These are plain data containers (dataclasses) with no business logic.
# ============================================================================

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple, Any
from enums_and_constants import (
    MarketType, MarketPhase, OperatingMode, IterationType,
    CommitmentStatus, DeviceType, ProductType, ForecastParadigm,
    StreamType, PenaltyStructureType
)


# ---------------------------------------------------------------------------
# Device State Structures
# ---------------------------------------------------------------------------

@dataclass
class HVACState:
    """Current physical state of an HVAC system, read from GridLAB-D.
    
    GridLAB-D Interface:
        All fields are read from the GridLAB-D house/HVAC object properties.
        Specific property names depend on the GridLAB-D model version.
    
    Attributes:
        indoor_air_temp: Current indoor air temperature (°F).
        outdoor_air_temp: Current outdoor air temperature (°F).
            SOURCE: GridLAB-D climate object.
        thermostat_setpoint: Current thermostat setpoint (°F).
        hvac_mode: Current operating mode ('heating', 'cooling', 'off').
        power_draw: Current electrical power consumption (kW).
        hvac_on: Whether the HVAC unit is currently running.
        thermal_mass_temp: Temperature of the building thermal mass (°F).
            Represents the effective temperature of walls, furniture, etc.
        air_mass: Thermal capacitance of the indoor air (Btu/°F).
        thermal_mass: Thermal capacitance of the building mass (Btu/°F).
        UA_envelope: Overall heat transfer coefficient of the building
            envelope (Btu/hr·°F). Determines heat loss/gain rate.
        UA_mass: Heat transfer coefficient between air and thermal mass
            (Btu/hr·°F).
        cooling_COP: Coefficient of performance in cooling mode.
        heating_COP: Coefficient of performance in heating mode.
        rated_cooling_capacity: Maximum cooling output (Btu/hr).
        rated_heating_capacity: Maximum heating output (Btu/hr).
        has_heat_pump: Whether heating is provided by heat pump (True)
            or resistive/gas backup only (False).
        solar_gain: Current solar heat gain into the building (Btu/hr).
            SOURCE: GridLAB-D house object, derived from climate.
        internal_gain: Current internal heat gain from occupants,
            appliances, etc. (Btu/hr).
        humidity: Current relative humidity (fraction 0.0–1.0).
            Used for latent load fraction calculation.
        deadband: Thermostat deadband width (°F). Temperature must
            deviate this far from setpoint before toggling HVAC on/off.
        heating_system_type: Type of heating system ('HEAT_PUMP' or
            'ELECTRIC'). Determines whether heating participates in
            market bidding.
        mass_internal_gain_fraction: Fraction of internal gains
            absorbed by thermal mass (dimensionless, typically 0.5).
        mass_solar_gain_fraction: Fraction of solar gains absorbed
            by thermal mass (dimensionless, typically 0.5).
        solar_heatgain_factor: Product of window area, glazing
            transmittance, and exterior transmission coefficient
            (sq ft, dimensionless combined). Converts incident solar
            flux density to total solar heat gain.
    """
    indoor_air_temp: float = 72.0
    outdoor_air_temp: float = 85.0
    thermostat_setpoint: float = 72.0
    hvac_mode: str = "cooling"
    power_draw: float = 0.0
    hvac_on: bool = False
    thermal_mass_temp: float = 72.0
    air_mass: float = 1500.0
    thermal_mass: float = 5000.0
    UA_envelope: float = 500.0
    UA_mass: float = 1500.0
    cooling_COP: float = 3.5
    heating_COP: float = 3.0
    rated_cooling_capacity: float = 36000.0
    rated_heating_capacity: float = 36000.0
    has_heat_pump: bool = False
    solar_gain: float = 0.0
    internal_gain: float = 0.0
    humidity: float = 0.5
    deadband: float = 2.0
    heating_system_type: str = "HEAT_PUMP"
    mass_internal_gain_fraction: float = 0.5
    mass_solar_gain_fraction: float = 0.5
    solar_heatgain_factor: float = 40.0


@dataclass
class WaterHeaterState:
    """Current physical state of an electric water heater, read from GridLAB-D.
    
    GridLAB-D Interface:
        Read from the GridLAB-D waterheater object properties.
    
    Attributes:
        tank_temp_upper: Temperature of upper tank zone (°F).
        tank_temp_lower: Temperature of lower tank zone (°F).
        thermostat_setpoint: Current tank thermostat setpoint (°F).
        element_on: Whether the heating element is currently active.
        power_draw: Current electrical power consumption (kW).
        tank_volume: Tank volume (gallons).
        tank_UA: Tank heat loss coefficient (Btu/hr·°F).
        element_power: Rated power of heating element (kW).
        inlet_water_temp: Temperature of incoming cold water (°F).
            SOURCE: GridLAB-D waterheater object or climate-derived.
        current_draw_rate: Current hot water draw rate (gallons/min).
            SOURCE: GridLAB-D waterheater demand schedule.
        tank_height: Height of tank (ft). Used for stratification model.
    """
    tank_temp_upper: float = 130.0
    tank_temp_lower: float = 125.0
    thermostat_setpoint: float = 130.0
    element_on: bool = False
    power_draw: float = 0.0
    tank_volume: float = 50.0
    tank_UA: float = 2.0
    element_power: float = 4.5
    inlet_water_temp: float = 60.0
    current_draw_rate: float = 0.0
    tank_height: float = 4.0


@dataclass
class EVChargerState:
    """Current physical state of an EV charger, read from GridLAB-D.
    
    GridLAB-D Interface:
        Read from a GridLAB-D EV charger object. Note that GridLAB-D's
        native EV models may require custom objects or FNCS/HELICS
        co-simulation to represent the vehicle battery state.
    
    Attributes:
        soc: Current state of charge (fraction 0.0–1.0).
        charge_rate: Current charging power (kW). Always >= 0.
        battery_capacity: Total EV battery capacity (kWh).
        max_charge_rate: Maximum charge rate allowed by EVSE (kW).
        charger_efficiency: Charger AC-to-DC efficiency (fraction).
        vehicle_plugged_in: Whether a vehicle is currently connected.
        min_charge_rate: Minimum non-zero charge rate if charging (kW).
            Many EVSEs cannot modulate below a threshold; they are
            either off or at/above this minimum.
        soc_at_max_taper: SOC above which charge rate tapers (fraction).
            BMS-imposed taper to protect battery at high SOC.
    """
    soc: float = 0.5
    charge_rate: float = 0.0
    battery_capacity: float = 60.0
    max_charge_rate: float = 7.2
    charger_efficiency: float = 0.90
    vehicle_plugged_in: bool = False
    min_charge_rate: float = 1.0
    soc_at_max_taper: float = 0.80


@dataclass
class BatteryState:
    """Current physical state of a home battery system, read from GridLAB-D.
    
    GridLAB-D Interface:
        Read from GridLAB-D battery or inverter object. GridLAB-D's
        battery model tracks SOC, charge/discharge rates, and
        inverter behavior. Some fields may come from the inverter
        object rather than the battery directly.
    
    Attributes:
        soc: Current state of charge (fraction 0.0–1.0).
        power: Current power flow (kW). Positive = charging (consuming
            from grid), negative = discharging (exporting to grid).
        energy_capacity: Total usable energy capacity (kWh).
        max_charge_rate: Maximum charging power (kW).
        max_discharge_rate: Maximum discharging power (kW).
        round_trip_efficiency: Round-trip AC-AC efficiency (fraction).
        cell_temperature: Battery cell temperature (°C).
        soc_min_bms: BMS hard minimum SOC (fraction). Below this
            the BMS will not allow discharge.
        soc_max_bms: BMS hard maximum SOC (fraction). Above this
            the BMS will not allow charge.
        inverter_rated_power: Inverter continuous power rating (kW).
        state_of_health: Remaining capacity fraction (1.0 = new).
    """
    soc: float = 0.50
    power: float = 0.0
    energy_capacity: float = 13.5
    max_charge_rate: float = 5.0
    max_discharge_rate: float = 5.0
    round_trip_efficiency: float = 0.90
    cell_temperature: float = 25.0
    soc_min_bms: float = 0.10
    soc_max_bms: float = 0.95
    inverter_rated_power: float = 5.0
    state_of_health: float = 1.0


# ---------------------------------------------------------------------------
# Market and Bidding Structures
# ---------------------------------------------------------------------------

@dataclass
class BidPoint:
    """A single point on a price-quantity bid curve.
    
    Attributes:
        price: Price in $/kWh (or $/kW for capacity products).
        quantity: Power quantity in kW. Positive = consumption (demand),
            negative = production/export (supply, for battery discharge).
    """
    price: float
    quantity: float


@dataclass
class BidCurve:
    """A complete price-quantity bid curve as an ordered list of points.
    
    The points must be ordered by decreasing price (highest price first).
    At higher prices, the agent consumes less (demand curve slopes down).
    For batteries, quantity may be negative at high prices (discharge/sell).
    
    Attributes:
        points: Ordered list of (price, quantity) points.
        market_id: ID of the market this bid is intended for.
        interval_id: ID of the delivery interval this bid covers.
        timestamp: Time the bid was formulated.
    """
    points: List[BidPoint] = field(default_factory=list)
    market_id: str = ""
    interval_id: str = ""
    timestamp: float = 0.0


@dataclass
class ClearingResult:
    """Result of a market clearing, received from the Market Operator.
    
    Attributes:
        market_id: ID of the market that cleared.
        interval_id: ID of the delivery interval.
        cleared_price: Clearing price ($/kWh or $/kW).
        cleared_quantity: Quantity cleared for this agent (kW).
        iteration: Which iteration of the market cycle this is.
        iteration_type: INFORMATIONAL or BINDING.
        timestamp: Time of clearing.
        aggregate_demand: Total demand at cleared price (kW).
            SOURCE: Provided by MO. Optional.
        aggregate_supply: Total supply at cleared price (kW).
            SOURCE: Provided by MO. Optional.
    """
    market_id: str = ""
    interval_id: str = ""
    cleared_price: float = 0.0
    cleared_quantity: float = 0.0
    iteration: int = 0
    iteration_type: IterationType = IterationType.BINDING
    timestamp: float = 0.0
    aggregate_demand: Optional[float] = None
    aggregate_supply: Optional[float] = None


@dataclass
class MarketTimingParams:
    """Timing parameters defining when each market phase begins.
    
    All times are expressed as offsets (in seconds) relative to
    the market clearing time t_clear. Negative values mean 
    "before clearing." Positive values mean "after clearing."
    
    Attributes:
        t_activate: Seconds before clearing to enter Active phase.
        t_negotiate: Seconds before clearing to enter Negotiation.
        t_market_lead: Seconds before clearing to enter Market Lead.
        t_clear: The clearing time (reference point, always 0 offset).
        t_delivery_start: Seconds after clearing when delivery begins.
        t_delivery_end: Seconds after clearing when delivery ends.
        t_reconcile_end: Seconds after clearing when reconciliation ends.
    """
    t_activate: float = -600.0
    t_negotiate: float = -420.0
    t_market_lead: float = -60.0
    t_clear: float = 0.0
    t_delivery_start: float = 0.0
    t_delivery_end: float = 300.0
    t_reconcile_end: float = 600.0


# ---------------------------------------------------------------------------
# Flexibility and Commitment Structures
# ---------------------------------------------------------------------------

@dataclass
class FlexibilityEnvelope:
    """Feasible operating range for a device over a time interval.
    
    Attributes:
        Q_min: Minimum feasible power consumption (kW).
            For loads, this is the power if the device is off or at
            minimum operating point. For batteries, may be negative
            (discharge).
        Q_max: Maximum feasible power consumption (kW).
        Q_baseline: Power consumption if tracking customer amenity
            setpoint with no price consideration (kW).
        Q_min_p50: Minimum power with 50% confidence of maintaining
            amenity constraints. Used for aggressive bidding.
        Q_min_p90: Minimum power with 90% confidence. Balanced.
        Q_min_p99: Minimum power with 99% confidence. Conservative.
        interval_start: Start time of the interval this envelope covers.
        interval_end: End time of the interval.
    """
    Q_min: float = 0.0
    Q_max: float = 5.0
    Q_baseline: float = 3.0
    Q_min_p50: float = 0.0
    Q_min_p90: float = 0.5
    Q_min_p99: float = 1.0
    interval_start: float = 0.0
    interval_end: float = 300.0


@dataclass
class EconomicCommitment:
    """A capacity commitment recorded on the flexibility ledger.
    
    Attributes:
        market_id: ID of the market this commitment is for.
        market_type: Type of market product.
        product_type: What the commitment represents (energy, reg, etc.).
        quantity: Committed power (kW) or capacity band (kW).
        interval: (start_time, end_time) of the delivery interval.
        status: Current lifecycle status of the commitment.
        cleared_price: Price at which the commitment was cleared ($/kWh).
        penalty_model_id: Reference to the applicable penalty model.
        marginal_nv: Marginal net value per kW of delivery ($/kW).
        marginal_pen: Marginal penalty per kW of non-delivery ($/kW).
        confidence: For ADVISORY status, the convergence confidence.
        iteration: Iteration number that produced this commitment.
        displacement_plan: Markets that may be displaced by this
            commitment, with expected displacement costs.
    """
    market_id: str = ""
    market_type: MarketType = MarketType.RT_ENERGY
    product_type: ProductType = ProductType.ENERGY_BASE
    quantity: float = 0.0
    interval: Tuple[float, float] = (0.0, 300.0)
    status: CommitmentStatus = CommitmentStatus.TENTATIVE
    cleared_price: float = 0.0
    penalty_model_id: str = ""
    marginal_nv: float = 0.0
    marginal_pen: float = 0.0
    confidence: float = 0.0
    iteration: int = 0
    displacement_plan: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Forecast and Data Stream Structures
# ---------------------------------------------------------------------------

@dataclass
class ContinuousDataPoint:
    """A single point in a continuous-process forecast.
    
    Attributes:
        timestamp: Time this point refers to (seconds, simulation time).
        lead_time: How far ahead of current time this point is (seconds).
        value: Point forecast value.
        sigma: Standard deviation from the uncertainty model.
        quantiles: Mapping of quantile level to value. 
            E.g., {0.05: 78.2, 0.50: 83.5, 0.95: 88.8}.
    """
    timestamp: float = 0.0
    lead_time: float = 0.0
    value: float = 0.0
    sigma: float = 0.0
    quantiles: Dict[float, float] = field(default_factory=dict)


@dataclass
class EventDefinition:
    """Definition of a discrete event type for event-process forecasting.
    
    Attributes:
        event_type: Name of the event type (e.g., 'shower', 'dishwash').
        duration_mean: Mean event duration (minutes).
        duration_std: Standard deviation of event duration (minutes).
        magnitude_mean: Mean event magnitude (flow rate in GPM, or kW).
        magnitude_std: Standard deviation of event magnitude.
        energy_mean: Mean energy per event (kWh). Derived from duration
            and magnitude if not set directly.
        energy_std: Standard deviation of energy per event.
    """
    event_type: str = ""
    duration_mean: float = 0.0
    duration_std: float = 0.0
    magnitude_mean: float = 0.0
    magnitude_std: float = 0.0
    energy_mean: float = 0.0
    energy_std: float = 0.0


@dataclass
class QuantilePoint:
    """Quantile representation of a random variable at a specific time.
    
    Attributes:
        timestamp: Time this refers to.
        lead_time: Lead time from current time (seconds).
        quantiles: Mapping of quantile level to value.
        expected: Expected (mean) value.
        variance: Variance of the distribution.
    """
    timestamp: float = 0.0
    lead_time: float = 0.0
    quantiles: Dict[float, float] = field(default_factory=dict)
    expected: float = 0.0
    variance: float = 0.0


@dataclass
class UncertaintyEnvelope:
    """Full distributional information at a point in time.
    
    Attributes:
        expected: Expected (mean) value.
        sigma: Standard deviation.
        quantiles: Quantile mapping.
        distribution_type: Description of distribution shape.
    """
    expected: float = 0.0
    sigma: float = 0.0
    quantiles: Dict[float, float] = field(default_factory=dict)
    distribution_type: str = "gaussian"


# ---------------------------------------------------------------------------
# Delivery and Settlement Structures
# ---------------------------------------------------------------------------

@dataclass
class FulfillmentRecord:
    """Per-market delivery performance at a single timestep.
    
    Attributes:
        market_id: Which market this fulfillment is for.
        committed: Committed power (kW).
        actual: Actual delivered power (kW).
        shortfall: max(0, committed - actual) in kW.
        revenue: Revenue earned this timestep ($).
        penalty: Penalty incurred this timestep ($).
        net_value: revenue - penalty ($).
        displaced_by: Market ID that displaced this delivery, if any.
    """
    market_id: str = ""
    committed: float = 0.0
    actual: float = 0.0
    shortfall: float = 0.0
    revenue: float = 0.0
    penalty: float = 0.0
    net_value: float = 0.0
    displaced_by: Optional[str] = None


@dataclass
class PerformanceEntry:
    """Timestamped performance log entry during delivery.
    
    Attributes:
        timestamp: Simulation time of this entry.
        committed: Committed power (kW).
        actual: Actual power (kW).
        shortfall: kW shortfall.
        revenue: $ revenue.
        penalty: $ penalty.
        net_value: $ net.
        was_displaced: Whether this market's delivery was curtailed.
        displaced_by: ID of the displacing market, if any.
    """
    timestamp: float = 0.0
    committed: float = 0.0
    actual: float = 0.0
    shortfall: float = 0.0
    revenue: float = 0.0
    penalty: float = 0.0
    net_value: float = 0.0
    was_displaced: bool = False
    displaced_by: Optional[str] = None


@dataclass
class SettlementRecord:
    """Final settlement for a completed market delivery.
    
    Attributes:
        market_id: Which market this settlement is for.
        total_revenue: Total revenue earned during delivery ($).
        total_penalty: Total penalty incurred ($).
        net_settlement: revenue - penalty ($).
        total_energy_committed: kWh committed over delivery window.
        total_energy_delivered: kWh actually delivered.
        total_shortfall: kWh shortfall.
        displacement_count: Number of timesteps where this market
            was displaced by a higher-value market.
        degradation_cost: For batteries, the degradation cost incurred
            during this delivery ($).
    """
    market_id: str = ""
    total_revenue: float = 0.0
    total_penalty: float = 0.0
    net_settlement: float = 0.0
    total_energy_committed: float = 0.0
    total_energy_delivered: float = 0.0
    total_shortfall: float = 0.0
    displacement_count: int = 0
    degradation_cost: float = 0.0


@dataclass
class AdvisoryRecord:
    """Record of one informational market clearing iteration.
    
    Attributes:
        iteration: Iteration number.
        timestamp: Time of the informational clear.
        cleared_price: Informational clearing price ($/kWh).
        cleared_quantity: Cleared quantity for this agent (kW).
        submitted_bid: The bid curve that was submitted for this iteration.
        projected_op_point: What the operating point would be if binding.
        projected_command: What control command would have been issued.
        price_delta: |price - previous iteration price|.
        quantity_delta: |quantity - previous iteration quantity|.
        convergence_metric: Convergence quality metric (0–1).
    """
    iteration: int = 0
    timestamp: float = 0.0
    cleared_price: float = 0.0
    cleared_quantity: float = 0.0
    submitted_bid: Optional[BidCurve] = None
    projected_op_point: float = 0.0
    projected_command: Optional[Any] = None
    price_delta: float = float('inf')
    quantity_delta: float = float('inf')
    convergence_metric: float = 0.0


@dataclass
class DeliveryEconomics:
    """Economic profile of an active delivery for the dispatch optimizer.
    
    Attributes:
        market_id: Which market.
        product_type: Energy, regulation, or reserve.
        committed_qty: Committed kW or kW-band.
        cleared_price: $/kWh or $/kW.
        revenue_fn: Callable mapping actual_qty -> revenue ($).
        penalty_fn: Callable mapping actual_qty -> penalty ($).
        net_value_fn: Callable mapping actual_qty -> net value ($).
        marginal_value_full: $/kW at full delivery.
        marginal_penalty_zero: $/kW at zero delivery.
    """
    market_id: str = ""
    product_type: ProductType = ProductType.ENERGY_BASE
    committed_qty: float = 0.0
    cleared_price: float = 0.0
    revenue_fn: Optional[Callable[[float], float]] = None
    penalty_fn: Optional[Callable[[float], float]] = None
    net_value_fn: Optional[Callable[[float], float]] = None
    marginal_value_full: float = 0.0
    marginal_penalty_zero: float = 0.0


@dataclass
class DispatchSolution:
    """Output of the dispatch optimizer.
    
    Attributes:
        Q: Optimal device operating point (kW). For batteries,
            negative means discharging.
        allocation: Per-market actual delivered quantity.
        displacement_chain: Which market displaced which.
        total_net_value: Total objective function value ($).
        binding_constraints: List of constraints that are binding.
    """
    Q: float = 0.0
    allocation: Dict[str, float] = field(default_factory=dict)
    displacement_chain: Dict[str, str] = field(default_factory=dict)
    total_net_value: float = 0.0
    binding_constraints: List[str] = field(default_factory=list)


@dataclass
class DeviceCommand:
    """A device-specific control command to be sent to GridLAB-D.
    
    GridLAB-D Interface:
        This structure is translated into GridLAB-D property writes.
        The specific properties depend on the device type.
    
    Attributes:
        device_type: Which kind of device this command targets.
        setpoint: New setpoint value (°F for HVAC/WH, fraction for 
            SOC targets, kW for charge/discharge rates).
        mode: Operating mode to set (e.g., 'cooling', 'heating', 'off').
        power_target: Target power consumption/production (kW).
        auxiliary: Any device-specific additional parameters.
    """
    device_type: DeviceType = DeviceType.HVAC_AC_ONLY
    setpoint: float = 72.0
    mode: str = ""
    power_target: float = 0.0
    auxiliary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningResult:
    """Output of the multi-interval planning optimizer.
    
    Attributes:
        intervals: List of (t_start, t_end, target_Q, target_amenity).
        V_stored: For batteries, marginal value of stored energy at
            each interval ($/kWh). Shadow price of SOC constraint.
        total_cost: Expected total cost over planning horizon ($).
        total_revenue: Expected total revenue ($).
        cycles_consumed: For batteries, equivalent full cycles used.
    """
    intervals: List[Tuple[float, float, float, float]] = field(
        default_factory=list)
    V_stored: List[float] = field(default_factory=list)
    total_cost: float = 0.0
    total_revenue: float = 0.0
    cycles_consumed: float = 0.0