# ============================================================================
# FILE: device_agent.py
# PURPOSE: Main device agent class. Orchestrates all agent functions and
#          manages the collection of MarketObjects. This is the top-level
#          class that external code interacts with.
# ============================================================================

from typing import Dict, List, Optional, Any
from .enums_and_constants import (
    DeviceType,
    MarketType,
    MarketPhase,
    OperatingMode,
    IterationType,
    ProductType,
)
from .data_types import (
    BidCurve,
    ClearingResult,
    DeviceCommand,
    FlexibilityEnvelope,
    FulfillmentRecord,
    SettlementRecord,
    AdvisoryRecord,
    MarketTimingParams,
    PerformanceEntry,
    ContinuousDataPoint,
    QuantilePoint,
)
from .gridlabd_interface import GridLABDInterface
from .data_streams import DataStreamManager
from .preference_curve import PreferenceCurve
from .penalty_model import PenaltyModel
from .flexibility_ledger import FlexibilityLedger
from .market_object import MarketObject
from .market_agent import MarketCommunicationInterface
from .command_arbiter import CommandArbiter
from .dispatch_optimizer import DispatchOptimizer, DeliveryValueCalculator
from .planning_optimizer import PlanningOptimizer
from .price_forecast_service import PriceForecastService
from .device_models import HVACModel, WaterHeaterModel, EVChargerModel, BatteryModel


class DeviceAgent:
    """Top-level device agent that orchestrates market participation.

    This class owns all sub-components and implements the main
    simulation loop. It manages multiple MarketObjects (one per
    market product per cycle) and coordinates their progression
    through the market state machine.

    The agent follows a sense-decide-act loop each simulation timestep:
    1. Observe device state from GridLAB-D (F1)
    2. Check each MarketObject for state transitions
    3. Execute phase-appropriate functions for each transitioning market
    4. Resolve all active deliveries into a single device command
    5. Actuate the device via GridLAB-D (F9)

    Args:
        agent_id: Unique identifier for this agent.
        device_type: Type of physical device to manage.
        gridlabd: GridLAB-D interface for device state and control.
            EXTERNAL: Provided by the simulation harness. Must be
            connected to the appropriate GridLAB-D object.
        customer_preference_k: Customer preference factor (0=amenity,
            1=financial).
            EXTERNAL: Provided as customer input/configuration.
        data_stream_manager: Manager for all forecast/schedule/constraint
            data streams.
            EXTERNAL: Must be populated with forecast data from external
            sources (weather, customer schedules, etc.).
    """

    def __init__(
        self,
        agent_id: str,
        device_type: DeviceType,
        gridlabd: GridLABDInterface,
        customer_preference_k: float,
        data_stream_manager: DataStreamManager,
    ):
        self._agent_id = agent_id
        self._device_type = device_type
        self._gridlabd = gridlabd
        self._k = customer_preference_k
        self._data_streams = data_stream_manager

        # Device-specific model
        self._device_model = self._create_device_model()

        # Market infrastructure
        self._market_objects: Dict[str, MarketObject] = {}
        self._market_comms: Dict[MarketType, MarketCommunicationInterface] = {}
        self._penalty_models: Dict[MarketType, PenaltyModel] = {}

        # Shared components
        self._flexibility_ledger: Optional[FlexibilityLedger] = None
        self._command_arbiter: Optional[CommandArbiter] = None
        self._planning_optimizer: Optional[PlanningOptimizer] = None
        self._price_forecast_service = PriceForecastService()

        # Current state cache
        self._current_state: Optional[Any] = None
        self._current_flexibility: Optional[FlexibilityEnvelope] = None
        self._current_preference_curve: Optional[PreferenceCurve] = None

    def _create_device_model(self) -> Any:
        """Instantiate the appropriate device physics model.

        Returns:
            Device-specific model instance (HVACModel, WaterHeaterModel,
            EVChargerModel, or BatteryModel).
        """
        if self._device_type in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
            return HVACModel(device_type=self._device_type)
        elif self._device_type == DeviceType.WATER_HEATER:
            return WaterHeaterModel()
        elif self._device_type == DeviceType.EV_CHARGER:
            return EVChargerModel()
        elif self._device_type == DeviceType.BATTERY:
            return BatteryModel()
        raise ValueError(f"Unsupported device type: {self._device_type}")

    # ------------------------------------------------------------------
    # Initialization and Registration
    # ------------------------------------------------------------------

    def initialize(self, device_params: Dict[str, Any]) -> None:
        """Initialize the agent with device parameters and create
        shared components.

        Must be called before the simulation loop starts.

        Args:
            device_params: Device-specific parameters.
                For HVAC: {} (parameters come from GridLAB-D state)
                For Battery: {'replacement_cost': float,
                              'rated_cycles': int,
                              'rated_dod': float}
                EXTERNAL: From device specifications.
        """
        self._flexibility_ledger = FlexibilityLedger(
            Q_min_device=0.0, Q_max_device=10.0
        )
        self._command_arbiter = CommandArbiter(
            device_type=self._device_type,
            gridlabd=self._gridlabd,
            device_model=self._device_model,
            optimizer=DispatchOptimizer(),
            value_calculator=DeliveryValueCalculator(),
        )
        self._planning_optimizer = PlanningOptimizer(
            device_model=self._device_model,
            device_type=str(self._device_type),
        )

    def register_market(
        self,
        market_type: MarketType,
        timing_params: MarketTimingParams,
        operating_mode: OperatingMode,
        penalty_model: PenaltyModel,
        communication: MarketCommunicationInterface,
        iteration_protocol: str = "mo_signaled",
        n_informational: Optional[int] = None,
    ) -> None:
        """Register participation in a market product.

        Creates the market communication interface and penalty model
        entries. Does NOT create the MarketObject yet — that happens
        when the first market cycle is spawned.

        Args:
            market_type: Type of market to participate in.
            timing_params: Timing for market phases.
                EXTERNAL: Defined by market rules from MO.
            operating_mode: How to participate (bidding, price-responsive).
                EXTERNAL: Configuration setting.
            penalty_model: Penalty structure for non-delivery.
                EXTERNAL: Defined by market rules from MO.
            communication: Communication interface to the MO.
                EXTERNAL: Provided by simulation harness.
            iteration_protocol: How informational iterations work.
                EXTERNAL: From market rules.
            n_informational: Number of informational iterations (if fixed).
                EXTERNAL: From market rules.
        """
        self._market_comms[market_type] = communication
        self._penalty_models[market_type] = penalty_model
        self._market_configs = getattr(self, "_market_configs", {})
        self._market_configs[market_type] = {
            "timing_params": timing_params,
            "operating_mode": operating_mode,
            "iteration_protocol": iteration_protocol,
            "n_informational": n_informational,
        }

    def spawn_market_cycle(self, market_type: MarketType, clearing_time: float) -> str:
        """Create a new MarketObject for an upcoming market cycle.

        Args:
            market_type: Type of market.
            clearing_time: When this cycle will clear (simulation time).

        Returns:
            market_id of the newly created MarketObject.
        """
        config = getattr(self, "_market_configs", {}).get(market_type, {})
        timing = config.get("timing_params", MarketTimingParams())
        mode = config.get("operating_mode", OperatingMode.BIDDING)
        protocol = config.get("iteration_protocol", "mo_signaled")
        n_info = config.get("n_informational", None)

        market_id = f"{market_type.name}_{int(clearing_time)}"
        mo = MarketObject(
            market_id=market_id,
            market_type=market_type,
            timing_params=timing,
            clearing_time=clearing_time,
            operating_mode=mode,
            iteration_protocol=protocol,
            n_informational_planned=n_info,
        )
        self._market_objects[market_id] = mo
        return market_id

    # ------------------------------------------------------------------
    # F1: Device State Observation
    # ------------------------------------------------------------------

    def observe_device_state(self) -> Any:
        """Read current device state from GridLAB-D.

        Dispatches to the appropriate GridLAB-D read method based on
        device_type.

        Returns:
            Device-specific state dataclass (HVACState, WaterHeaterState,
            EVChargerState, or BatteryState).

        Note: This is the ONLY function that reads from GridLAB-D.
        """
        if self._device_type in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
            state = self._gridlabd.read_hvac_state()
            # Sync internal temperature tracking from GridLAB-D ground truth
            self._device_model.sync_from_gridlabd(state)
        elif self._device_type == DeviceType.WATER_HEATER:
            state = self._gridlabd.read_water_heater_state()
        elif self._device_type == DeviceType.EV_CHARGER:
            state = self._gridlabd.read_ev_charger_state()
        elif self._device_type == DeviceType.BATTERY:
            state = self._gridlabd.read_battery_state()
        else:
            raise ValueError(f"Unsupported device type: {self._device_type}")
        self._current_state = state
        return state

    # ------------------------------------------------------------------
    # F2: Flexibility Estimation
    # ------------------------------------------------------------------

    def estimate_flexibility(
        self, state: Any, interval_duration: float
    ) -> FlexibilityEnvelope:
        """Estimate the feasible operating range for the upcoming interval.

        Delegates to the device-specific model, providing it with
        relevant forecasts from the DataStreamManager.

        Args:
            state: Current device state from F1.
                INTERNAL: From self.observe_device_state().
            interval_duration: Market interval length (seconds).

        Returns:
            FlexibilityEnvelope with feasible power range and
            confidence-level variants.
        """
        if self._device_type in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
            # Gather forecasts from DataStreamManager; fall back to
            # current state values when streams aren't registered.
            outdoor_stream = self._data_streams.get_continuous("outdoor_air_temp")
            if outdoor_stream:
                outdoor_forecast = outdoor_stream.get_series(0.0, interval_duration)
            else:
                outdoor_forecast = [
                    ContinuousDataPoint(
                        value=state.outdoor_air_temp,
                    )
                ]

            solar_stream = self._data_streams.get_continuous("solar_gain")
            if solar_stream:
                solar_forecast = solar_stream.get_series(0.0, interval_duration)
            else:
                solar_forecast = [
                    ContinuousDataPoint(
                        value=getattr(state, "solar_gain", 0.0),
                    )
                ]

            internal_stream = self._data_streams.get_continuous("internal_gain")
            if internal_stream:
                internal_forecast = internal_stream.get_series(0.0, interval_duration)
            else:
                internal_forecast = [
                    ContinuousDataPoint(
                        value=getattr(state, "internal_gain", 0.0),
                    )
                ]

            setpoint_sched = self._data_streams.get_schedule("hvac_setpoint_schedule")
            if setpoint_sched:
                setpoint_schedule = setpoint_sched.get_series(0.0, interval_duration)
            else:
                setpoint_schedule = [
                    ContinuousDataPoint(
                        value=state.thermostat_setpoint,
                    )
                ]

            envelope = self._device_model.estimate_flexibility(
                state=state,
                outdoor_temp_forecast=outdoor_forecast,
                solar_gain_forecast=solar_forecast,
                internal_gain_forecast=internal_forecast,
                setpoint_schedule=setpoint_schedule,
                interval_duration=interval_duration,
            )

        elif self._device_type == DeviceType.WATER_HEATER:
            # Gather water heater-specific data from DataStreamManager
            draw_stream = self._data_streams.get_event("hot_water_draw")
            if draw_stream:
                draw_forecast = draw_stream.get_cumulative_energy_distribution(
                    0.0, interval_duration
                )
            else:
                draw_forecast = QuantilePoint(expected=0.0, variance=0.0)

            inlet_stream = self._data_streams.get_continuous("inlet_water_temp")
            if inlet_stream:
                inlet_temp_forecast = inlet_stream.get_at(0.0)
            else:
                inlet_temp_forecast = None

            # Ambient temperature around the tank (typically indoor temp)
            ambient_temp = getattr(state, "ambient_temp", 70.0)

            # Minimum tank temperature from constraint stream
            tank_constraint = self._data_streams.get_constraint("tank_temp_minimum")
            if tank_constraint:
                min_tank_temp = tank_constraint._required_value
            else:
                min_tank_temp = 120.0  # default Legionella prevention

            envelope = self._device_model.estimate_flexibility(
                state=state,
                draw_forecast=draw_forecast,
                inlet_temp_forecast=inlet_temp_forecast,
                ambient_temp=ambient_temp,
                min_tank_temp=min_tank_temp,
                interval_duration=interval_duration,
            )

        elif self._device_type == DeviceType.EV_CHARGER:
            # Gather EV-specific data from DataStreamManager
            dep_constraint = self._data_streams.get_constraint("ev_departure_soc")
            if dep_constraint and dep_constraint._deadline is not None:
                departure_constraint = (
                    dep_constraint._deadline,
                    dep_constraint._required_value,
                )
                time_until_departure = dep_constraint._deadline  # relative to now
            else:
                departure_constraint = None
                time_until_departure = None

            pref_sched = self._data_streams.get_schedule("ev_preferred_soc")
            if pref_sched:
                preferred_soc = pref_sched.get_at(0.0).value
            else:
                preferred_soc = 0.90  # default

            envelope = self._device_model.estimate_flexibility(
                state=state,
                departure_constraint=departure_constraint,
                preferred_soc=preferred_soc,
                interval_duration=interval_duration,
                time_until_departure=time_until_departure,
            )

        elif self._device_type == DeviceType.BATTERY:
            # Gather battery-specific data from DataStreamManager
            reserve_constraint = self._data_streams.get_constraint("soc_reserve")
            if reserve_constraint:
                soc_reserve = reserve_constraint._required_value
            else:
                soc_reserve = 0.20  # default

            pref_sched = self._data_streams.get_schedule("battery_preferred_soc")
            if pref_sched:
                soc_preferred = pref_sched.get_at(0.0).value
            else:
                soc_preferred = 0.80  # default

            envelope = self._device_model.estimate_flexibility(
                state=state,
                soc_reserve=soc_reserve,
                soc_preferred=soc_preferred,
                interval_duration=interval_duration,
            )

        else:
            raise ValueError(f"Unsupported device type: {self._device_type}")

        self._current_flexibility = envelope
        return envelope

    # ------------------------------------------------------------------
    # F3: Preference Curve Generation
    # ------------------------------------------------------------------

    def generate_preference_curve(
        self, flexibility: FlexibilityEnvelope
    ) -> PreferenceCurve:
        """Generate the customer preference curve.

        Creates a PreferenceCurve anchored to the baseline operating
        point from the flexibility envelope and the reference price
        from the price forecast.

        Args:
            flexibility: Flexibility envelope from F2.
                INTERNAL: From self.estimate_flexibility().

        Returns:
            PreferenceCurve instance.
        """
        P_0 = self._price_forecast_service.get_price(
            MarketType.RT_ENERGY,
            (flexibility.interval_start, flexibility.interval_end),
            default=0.10,
        )
        curve = PreferenceCurve(
            device_type=self._device_type,
            Q_0=flexibility.Q_baseline,
            P_0=P_0,
            k=self._k,
        )
        self._current_preference_curve = curve
        return curve

    # ------------------------------------------------------------------
    # F4: Bid Formulation
    # ------------------------------------------------------------------

    def formulate_bid(
        self,
        market_obj: MarketObject,
        flexibility: FlexibilityEnvelope,
        preference_curve: PreferenceCurve,
    ) -> BidCurve:
        """Formulate a price-quantity bid curve for a specific market.

        Combines the operating envelope with the preference curve,
        applies risk adjustment based on concurrent commitments and
        displacement economics, and produces a discretized bid curve.

        For batteries, includes degradation cost in the dead band.

        Args:
            market_obj: The MarketObject being bid for.
                INTERNAL: From self._market_objects.
            flexibility: Available flexibility for this market.
                INTERNAL: From F2, adjusted by FlexibilityLedger.
            preference_curve: Customer preference curve.
                INTERNAL: From F3.

        Returns:
            BidCurve with price-quantity points.
        """
        bid_points = preference_curve.sample_bid_curve(
            price_min=0.01,
            price_max=1.0,
            n_points=11,
            Q_min=flexibility.Q_min,
            Q_max=flexibility.Q_max,
        )
        return BidCurve(
            points=bid_points,
            market_id=market_obj.market_id,
            interval_id=f"int_{market_obj.market_id}",
            timestamp=0.0,  # TODO: Set actual timestamp when bid is generated
        )

    # ------------------------------------------------------------------
    # F7: Price-to-Operating-Point Response
    # ------------------------------------------------------------------

    def evaluate_price_response(self, price: float, curve: Any) -> float:
        """Determine desired operating point from a price signal.

        Evaluates either the submitted bid curve (bidding mode) or
        the preference curve (price-responsive mode) at the given price.

        Args:
            price: Cleared or observed price ($/kWh).
                INTERNAL: From ClearingResult.cleared_price.
            curve: Either a BidCurve (bidding mode) or PreferenceCurve
                (price-responsive mode).
                INTERNAL: From MarketObject or F3.

        Returns:
            Desired power quantity (kW).
        """
        if isinstance(curve, PreferenceCurve):
            return curve.evaluate(price)
        elif isinstance(curve, BidCurve):
            # Interpolate from bid curve points (descending price order)
            if not curve.points:
                return 0.0
            if price >= curve.points[0].price:
                return curve.points[0].quantity
            if price <= curve.points[-1].price:
                return curve.points[-1].quantity
            for i in range(len(curve.points) - 1):
                p_hi = curve.points[i].price
                p_lo = curve.points[i + 1].price
                if p_lo <= price <= p_hi:
                    frac = (price - p_lo) / (p_hi - p_lo) if p_hi != p_lo else 0.5
                    q_hi = curve.points[i].quantity
                    q_lo = curve.points[i + 1].quantity
                    return q_lo + frac * (q_hi - q_lo)
            return curve.points[-1].quantity
        return 0.0

    # ------------------------------------------------------------------
    # F8: Control Signal Translation
    # ------------------------------------------------------------------

    def translate_to_control(self, target_power: float, state: Any) -> DeviceCommand:
        """Convert target power to device-specific control command.

        Uses the device model's inverse function to map power to setpoint.

        Args:
            target_power: Desired power (kW).
                INTERNAL: From F7 or dispatch optimizer.
            state: Current device state.
                INTERNAL: From F1.

        Returns:
            DeviceCommand ready to be sent to GridLAB-D.
        """
        if self._device_type in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
            try:
                setpoint = self._device_model.power_to_setpoint(
                    target_power_kw=target_power,
                    state=state,
                    outdoor_temp=getattr(state, "outdoor_air_temp", 85.0),
                    interval_duration=300.0,
                )
            except (AttributeError, NotImplementedError):
                setpoint = 72.0
            mode = getattr(state, "hvac_mode", "cooling")
            return DeviceCommand(
                device_type=self._device_type,
                setpoint=setpoint,
                mode=mode,
                power_target=target_power,
            )
        elif self._device_type == DeviceType.WATER_HEATER:
            try:
                setpoint = self._device_model.power_to_setpoint(
                    target_power_kw=target_power,
                    state=state,
                    interval_duration=300.0,
                )
            except (AttributeError, NotImplementedError):
                setpoint = 130.0
            return DeviceCommand(
                device_type=self._device_type,
                setpoint=setpoint,
                power_target=target_power,
            )
        elif self._device_type == DeviceType.EV_CHARGER:
            return DeviceCommand(
                device_type=self._device_type,
                power_target=target_power,
            )
        else:
            # Battery or unknown: power_target directly
            return DeviceCommand(
                device_type=self._device_type,
                power_target=target_power,
            )

    # ------------------------------------------------------------------
    # F12: Performance Monitoring
    # ------------------------------------------------------------------

    def log_performance(
        self, market_obj: MarketObject, fulfillment: FulfillmentRecord, timestamp: float
    ) -> None:
        """Log delivery performance for a market.

        Called every timestep during delivery for each active market.

        Args:
            market_obj: The market being delivered.
                INTERNAL: From self._market_objects.
            fulfillment: Fulfillment record from Command Arbiter.
                INTERNAL: From CommandArbiter.resolve_and_actuate().
            timestamp: Current simulation time.
        """
        entry = PerformanceEntry(
            timestamp=timestamp,
            committed=fulfillment.committed,
            actual=fulfillment.actual,
            shortfall=fulfillment.shortfall,
            revenue=fulfillment.revenue,
            penalty=fulfillment.penalty,
            net_value=fulfillment.net_value,
            was_displaced=fulfillment.displaced_by is not None,
            displaced_by=fulfillment.displaced_by,
        )
        market_obj.performance_log.append(entry)

    # ------------------------------------------------------------------
    # F13: Reconciliation
    # ------------------------------------------------------------------

    def reconcile(self, market_obj: MarketObject) -> SettlementRecord:
        """Compute settlement for a completed delivery.

        Compares actual performance against commitment, computes
        penalties (including any deliberate displacement), and
        generates the settlement record.

        For batteries, includes degradation cost accounting.

        Args:
            market_obj: The market to reconcile.
                INTERNAL: From self._market_objects.

        Returns:
            SettlementRecord with financial outcomes.
        """
        total_revenue = 0.0
        total_penalty = 0.0
        total_committed = 0.0
        total_delivered = 0.0
        total_shortfall = 0.0
        displacement_count = 0

        for entry in market_obj.performance_log:
            total_revenue += entry.revenue
            total_penalty += entry.penalty
            total_committed += entry.committed
            total_delivered += entry.actual
            total_shortfall += entry.shortfall
            if entry.was_displaced:
                displacement_count += 1

        return SettlementRecord(
            market_id=market_obj.market_id,
            total_revenue=total_revenue,
            total_penalty=total_penalty,
            net_settlement=total_revenue - total_penalty,
            total_energy_committed=total_committed,
            total_energy_delivered=total_delivered,
            total_shortfall=total_shortfall,
            displacement_count=displacement_count,
        )

    # ------------------------------------------------------------------
    # Phase Handlers
    # ------------------------------------------------------------------

    def _handle_active(self, market_obj: MarketObject) -> None:
        """Execute Active phase logic for a market.

        Steps:
        1. Observe device state (F1)
        2. Estimate flexibility (F2)
        3. Generate preference curve (F3)
        4. Query flexibility ledger for available capacity (F6)
        5. Store results on MarketObject
        """
        state = self.observe_device_state()
        timing = market_obj.timing_params
        interval_duration = timing.t_delivery_end - timing.t_delivery_start
        flexibility = self.estimate_flexibility(state, interval_duration)
        preference = self.generate_preference_curve(flexibility)
        market_obj.available_flexibility = flexibility
        market_obj.preference_curve = preference

    def _handle_negotiation(self, market_obj: MarketObject) -> None:
        """Execute Negotiation phase logic.

        If BIDDING mode:
            1. Formulate bid (F4)
            2. Submit bid to MO (F5)
            3. Record tentative commitment on ledger (F6)
        If PRICE_RESPONSIVE mode:
            No-op (preference curve IS the response function)
        """
        if market_obj.operating_mode != OperatingMode.BIDDING:
            return
        flexibility = self._current_flexibility or FlexibilityEnvelope()
        preference = self._current_preference_curve
        if preference is None:
            preference = PreferenceCurve(
                device_type=self._device_type, Q_0=3.0, P_0=0.10, k=self._k
            )
        bid = self.formulate_bid(market_obj, flexibility, preference)
        market_obj.submitted_bid = bid
        comm = self._market_comms.get(market_obj.market_type)
        if comm is not None:
            comm.submit_bid(
                bid=bid,
                market_id=market_obj.market_id,
                interval_id=f"int_{market_obj.market_id}",
            )

        # F6: record tentative commitment for this negotiation round.
        if self._flexibility_ledger is not None:
            timing = market_obj.timing_params
            qty = 0.0
            if bid.points:
                qty = max(pt.quantity for pt in bid.points)
            self._flexibility_ledger.hold_tentative(
                market_id=market_obj.market_id,
                market_type=market_obj.market_type,
                product_type=ProductType.ENERGY_BASE,
                quantity=qty,
                interval=(timing.t_delivery_start, timing.t_delivery_end),
            )

    def _handle_market_lead(self, market_obj: MarketObject) -> None:
        """Execute Market Lead phase logic.

        No agent operations. MO is processing.
        """
        pass

    def _handle_assessment(
        self, market_obj: MarketObject, clearing_result: ClearingResult
    ) -> None:
        """Execute Assessment phase logic.

        Determines if clearing is informational or binding.

        If INFORMATIONAL:
            1. Evaluate projected response (F7, F8 — but don't actuate)
            2. Store AdvisoryRecord
            3. Update advisory commitment on ledger
            4. Update price forecast service
            5. Optionally re-run planning optimizer
            6. Transition back to Active for next iteration

        If BINDING:
            Transition to Delivery Lead.

        Args:
            market_obj: The market being assessed.
            clearing_result: The clearing result from MO.
                INTERNAL: From market communication (F5).
        """
        if clearing_result.iteration_type == IterationType.INFORMATIONAL:
            # Evaluate projected response without actuating
            curve = market_obj.preference_curve or self._current_preference_curve
            if curve is not None:
                Q_proj = self.evaluate_price_response(
                    clearing_result.cleared_price, curve
                )
            else:
                Q_proj = clearing_result.cleared_quantity

            advisory = AdvisoryRecord(
                iteration=clearing_result.iteration,
                timestamp=clearing_result.timestamp,
                cleared_price=clearing_result.cleared_price,
                cleared_quantity=clearing_result.cleared_quantity,
                projected_op_point=Q_proj,
            )
            market_obj.advisory_history.append(advisory)
            market_obj.latest_advisory = advisory

            # F6: update advisory commitment on the flexibility ledger.
            if self._flexibility_ledger is not None:
                timing = market_obj.timing_params
                confidence = self._compute_confidence(market_obj.advisory_history)
                self._flexibility_ledger.update_advisory(
                    market_id=market_obj.market_id,
                    quantity=Q_proj,
                    interval=(timing.t_delivery_start, timing.t_delivery_end),
                    confidence=confidence,
                    cleared_price=clearing_result.cleared_price,
                    penalty_model_id="",
                    iteration=clearing_result.iteration,
                )

            # Update price forecast
            timing = market_obj.timing_params
            self._price_forecast_service.update(
                market_type=market_obj.market_type,
                interval=(timing.t_delivery_start, timing.t_delivery_end),
                price=clearing_result.cleared_price,
                confidence=self._compute_confidence(market_obj.advisory_history),
                source="informational",
                iteration=clearing_result.iteration,
            )

            # Transition back to ACTIVE for next iteration
            market_obj.transition_to(MarketPhase.ACTIVE)
        else:
            # Binding — transition to DELIVERY_LEAD
            market_obj.cleared_price = clearing_result.cleared_price
            market_obj.cleared_quantity = clearing_result.cleared_quantity
            market_obj.transition_to(MarketPhase.DELIVERY_LEAD)

    def _handle_delivery_lead(
        self, market_obj: MarketObject, clearing_result: ClearingResult
    ) -> None:
        """Execute Delivery Lead phase logic.

        Steps:
        1. Receive binding clearing result (F5)
        2. Evaluate response — determine target operating point (F7)
        3. Translate to control command (F8)
        4. Book firm commitment on ledger (F6)
        5. Prepare command for Command Arbiter (but don't actuate yet)

        Args:
            market_obj: The market entering delivery lead.
            clearing_result: Binding clearing result.
                INTERNAL: From market communication (F5).
        """
        market_obj.cleared_price = clearing_result.cleared_price
        market_obj.cleared_quantity = clearing_result.cleared_quantity

        curve = market_obj.preference_curve or self._current_preference_curve
        if curve is not None:
            Q_target = self.evaluate_price_response(
                clearing_result.cleared_price, curve
            )
        else:
            Q_target = clearing_result.cleared_quantity
        market_obj.target_operating_point = Q_target

        state = self._current_state
        if state is not None:
            command = self.translate_to_control(Q_target, state)
            market_obj.control_command = command

            # Update internal temperature prediction for HVAC devices
            if self._device_type in (
                DeviceType.HVAC_AC_ONLY,
                DeviceType.HVAC_HEAT_PUMP,
            ):
                timing = market_obj.timing_params
                interval_dur = timing.t_delivery_end - timing.t_delivery_start
                self._device_model.update_internal_state(
                    state=state,
                    target_setpoint=command.setpoint,
                    outdoor_temp=getattr(state, "outdoor_air_temp", 85.0),
                    duration_seconds=interval_dur,
                )

        # F6: book firm commitment for delivery interval.
        if self._flexibility_ledger is not None:
            timing = market_obj.timing_params
            self._flexibility_ledger.book_firm(
                market_id=market_obj.market_id,
                quantity=Q_target,
                interval=(timing.t_delivery_start, timing.t_delivery_end),
                cleared_price=clearing_result.cleared_price,
                penalty_model_id="",
            )

    def _handle_delivery_start(self, market_obj: MarketObject) -> None:
        """Execute logic when a market first enters Delivery.

        Registers the delivery with the Command Arbiter.
        """
        penalty = self._penalty_models.get(market_obj.market_type)
        if self._command_arbiter is not None and penalty is not None:
            timing = market_obj.timing_params
            self._command_arbiter.register_delivery(
                market_id=market_obj.market_id,
                market_type=str(market_obj.market_type),
                product_type="ENERGY_BASE",
                committed_qty=market_obj.cleared_quantity,
                cleared_price=market_obj.cleared_price,
                penalty_model=penalty,
                interval=(timing.t_delivery_start, timing.t_delivery_end),
            )

    def _handle_delivery_tick(self, timestamp: float) -> None:
        """Execute per-timestep logic during any active delivery.

        This is called every simulation timestep when at least one
        market is in the Delivery phase. It:
        1. Observes device state (F1)
        2. Recomputes delivery economics for all active deliveries (F15)
        3. Runs dispatch optimization via Command Arbiter
        4. Logs per-market fulfillment (F12)

        Args:
            timestamp: Current simulation time.
        """
        state = self.observe_device_state()
        preference = self._current_preference_curve
        if preference is None:
            preference = PreferenceCurve(
                device_type=self._device_type, Q_0=3.0, P_0=0.10, k=self._k
            )

        if self._command_arbiter is not None:
            fulfillments = self._command_arbiter.resolve_and_actuate(
                device_state=state,
                preference_curve=preference,
                amenity_weight=self._k,
                current_time=timestamp,
            )
            # Log per-market fulfillment
            for mid, fr in fulfillments.items():
                if mid in self._market_objects:
                    self.log_performance(self._market_objects[mid], fr, timestamp)

    def _handle_reconcile(self, market_obj: MarketObject) -> None:
        """Execute Reconcile phase logic.

        Steps:
        1. Compute settlement (F13)
        2. Release commitment from ledger (F6)
        3. Report to MO (F5)
        4. For batteries, update degradation tracking
        """
        settlement = self.reconcile(market_obj)
        market_obj.settlement_record = settlement

        # Release from ledger
        if self._flexibility_ledger is not None:
            self._flexibility_ledger.release(market_obj.market_id)

        # Deregister from command arbiter
        if self._command_arbiter is not None:
            self._command_arbiter.deregister_delivery(market_obj.market_id)

        # Report to MO
        comm = self._market_comms.get(market_obj.market_type)
        if comm is not None:
            comm.submit_reconciliation(
                market_id=market_obj.market_id,
                settlement=settlement,
            )

    def _handle_expired(self, market_obj: MarketObject) -> None:
        """Execute Expired phase logic.

        1. Archive market object data
        2. If cyclic market, spawn next cycle's MarketObject
        3. Remove from active markets
        """
        self._market_objects.pop(market_obj.market_id, None)

    # ------------------------------------------------------------------
    # F11: Main Orchestration Loop
    # ------------------------------------------------------------------

    def step(self, current_time: float) -> None:
        """Execute one simulation timestep.

        This is the main entry point called by the simulation harness
        every timestep. It:

        1. Checks all MarketObjects for state transitions
        2. Executes phase handlers for any transitions
        3. If any deliveries are active, runs delivery tick

        Args:
            current_time: Current simulation time.
                EXTERNAL: From simulation harness / GridLAB-D.
        """
        has_delivery = False
        for mid in list(self._market_objects.keys()):
            mo = self._market_objects.get(mid)
            if mo is None:
                continue
            # Check for phase transition
            new_phase = mo.should_transition(current_time)
            if new_phase is not None:
                mo.transition_to(new_phase)
                if new_phase == MarketPhase.ACTIVE:
                    self._handle_active(mo)
                elif new_phase == MarketPhase.NEGOTIATION:
                    self._handle_negotiation(mo)
                elif new_phase == MarketPhase.MARKET_LEAD:
                    self._handle_market_lead(mo)
                elif new_phase == MarketPhase.ASSESSMENT:
                    comm = self._market_comms.get(mo.market_type)
                    if comm is not None:
                        result = comm.receive_clear(market_id=mo.market_id)
                    else:
                        result = None
                    if result is None:
                        result = ClearingResult(market_id=mo.market_id)
                    self._handle_assessment(mo, result)
                elif new_phase == MarketPhase.DELIVERY_LEAD:
                    comm = self._market_comms.get(mo.market_type)
                    if comm is not None:
                        result = comm.receive_clear(market_id=mo.market_id)
                    else:
                        result = None
                    if result is None:
                        result = ClearingResult(
                            market_id=mo.market_id,
                            cleared_price=mo.cleared_price,
                            cleared_quantity=mo.cleared_quantity,
                        )
                    self._handle_delivery_lead(mo, result)
                elif new_phase == MarketPhase.DELIVERY:
                    self._handle_delivery_start(mo)
                elif new_phase == MarketPhase.RECONCILE:
                    self._handle_reconcile(mo)
                elif new_phase == MarketPhase.EXPIRED:
                    self._handle_expired(mo)

            if mo.current_phase == MarketPhase.DELIVERY:
                has_delivery = True

        if has_delivery:
            self._handle_delivery_tick(current_time)

    # ------------------------------------------------------------------
    # Convergence and Confidence (for informational iterations)
    # ------------------------------------------------------------------

    def _compute_convergence(self, advisory_history: List[AdvisoryRecord]) -> float:
        """Compute convergence metric from advisory history.

        Uses exponentially-weighted price volatility across iterations.

        Args:
            advisory_history: List of AdvisoryRecords from previous
                informational iterations.
                INTERNAL: From MarketObject.advisory_history.

        Returns:
            Convergence metric (0=no convergence, 1=fully converged).
        """
        if len(advisory_history) < 2:
            return 0.0
        # Exponentially-weighted price delta
        alpha = 0.5
        weighted_delta = 0.0
        weight_sum = 0.0
        for i in range(1, len(advisory_history)):
            w = alpha ** (len(advisory_history) - 1 - i)
            delta = abs(
                advisory_history[i].cleared_price
                - advisory_history[i - 1].cleared_price
            )
            weighted_delta += w * delta
            weight_sum += w
        avg_delta = weighted_delta / weight_sum if weight_sum > 0 else 0.0
        # Map to 0-1 range: convergence = 1 / (1 + 10 * avg_delta)
        return 1.0 / (1.0 + 10.0 * avg_delta)

    def _compute_confidence(self, advisory_history: List[AdvisoryRecord]) -> float:
        """Compute advisory confidence from iteration count and convergence.

        Args:
            advisory_history: From MarketObject.advisory_history.
                INTERNAL.

        Returns:
            Confidence level (0–1).
        """
        if not advisory_history:
            return 0.0
        n = len(advisory_history)
        convergence = self._compute_convergence(advisory_history)
        # Confidence grows with iterations and convergence
        iteration_factor = min(1.0, n / 5.0)
        return iteration_factor * (0.3 + 0.7 * convergence)
