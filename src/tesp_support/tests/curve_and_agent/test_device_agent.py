# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for device_agent.py — Top-level device agent orchestrator.

Ground truth:
  - DeviceAgent owns all sub-components and runs the sense-decide-act loop
  - _create_device_model dispatches to HVACModel / WaterHeaterModel / etc.
  - initialize() sets up FlexibilityLedger, CommandArbiter, PlanningOptimizer
  - register_market() stores market type config + comm interface
  - spawn_market_cycle() creates a new MarketObject
  - F1 (observe) → F2 (flexibility) → F3 (preference) → F4 (bid) → F5 (submit)
  - F7 (price response) → F8 (control translation) → F9 (actuation via arbiter)
  - F12 (performance logging) → F13 (reconciliation)
  - Phase handlers drive the state machine per-MarketObject
  - step() is the main entry point from the simulation harness

Testing strategy:
  GridLABDInterface and MarketCommunicationInterface are injected — mock them.
  Internal components (device models, optimizer, etc.) are already tested;
  we use real instances where cheap, mocks where the component is heavy.
  All stub methods are xfail until implemented.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from device_agent import DeviceAgent
from data_types import (
    HVACState,
    WaterHeaterState,
    EVChargerState,
    BatteryState,
    BidCurve,
    BidPoint,
    ClearingResult,
    FlexibilityEnvelope,
    DeviceCommand,
    MarketTimingParams,
    FulfillmentRecord,
    SettlementRecord,
    AdvisoryRecord,
)
from enums_and_constants import (
    DeviceType,
    MarketType,
    MarketPhase,
    OperatingMode,
    IterationType,
)
from market_object import MarketObject
from penalty_model import PenaltyModel
from enums_and_constants import PenaltyStructureType
from preference_curve import PreferenceCurve
from data_streams import DataStreamManager


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def mock_gridlabd():
    """Mock GridLABDInterface for all device types."""
    gld = MagicMock()
    gld.read_hvac_state = MagicMock(return_value=HVACState())
    gld.read_water_heater_state = MagicMock(return_value=WaterHeaterState())
    gld.read_ev_charger_state = MagicMock(return_value=EVChargerState())
    gld.read_battery_state = MagicMock(return_value=BatteryState())
    gld.read_simulation_time = MagicMock(return_value=1000.0)
    gld.write_hvac_command = MagicMock(return_value=True)
    gld.write_water_heater_command = MagicMock(return_value=True)
    gld.write_ev_charger_command = MagicMock(return_value=True)
    gld.write_battery_command = MagicMock(return_value=True)
    return gld


@pytest.fixture
def mock_data_streams():
    """Mock DataStreamManager — provides forecasts and constraints."""
    dsm = MagicMock(spec=DataStreamManager)
    return dsm


@pytest.fixture
def mock_market_comm():
    """Mock MarketCommunicationInterface."""
    comm = MagicMock()
    comm.submit_bid = MagicMock(return_value=True)
    comm.receive_clear = MagicMock(return_value=None)
    comm.submit_reconciliation = MagicMock(return_value=True)
    return comm


@pytest.fixture
def mock_device_model():
    """Mock device model that stands in until _create_device_model is implemented."""
    model = MagicMock()
    model.estimate_flexibility = MagicMock(
        return_value=FlexibilityEnvelope(Q_min=0.0, Q_max=5.0, Q_baseline=3.0)
    )
    model.power_to_setpoint = MagicMock(return_value=74.0)
    return model


def _make_agent(agent_id, device_type, gridlabd, k, dsm, mock_model):
    """Create a DeviceAgent with _create_device_model patched."""
    with patch.object(DeviceAgent, "_create_device_model", return_value=mock_model):
        return DeviceAgent(
            agent_id=agent_id,
            device_type=device_type,
            gridlabd=gridlabd,
            customer_preference_k=k,
            data_stream_manager=dsm,
        )


@pytest.fixture
def hvac_agent(mock_gridlabd, mock_data_streams, mock_device_model):
    """DeviceAgent configured for HVAC."""
    return _make_agent(
        "agent_house_1",
        DeviceType.HVAC_AC_ONLY,
        mock_gridlabd,
        0.3,
        mock_data_streams,
        mock_device_model,
    )


@pytest.fixture
def battery_agent(mock_gridlabd, mock_data_streams, mock_device_model):
    """DeviceAgent configured for battery."""
    return _make_agent(
        "agent_battery_1",
        DeviceType.BATTERY,
        mock_gridlabd,
        0.5,
        mock_data_streams,
        mock_device_model,
    )


@pytest.fixture
def wh_agent(mock_gridlabd, mock_data_streams, mock_device_model):
    """DeviceAgent configured for water heater."""
    return _make_agent(
        "agent_wh_1",
        DeviceType.WATER_HEATER,
        mock_gridlabd,
        0.4,
        mock_data_streams,
        mock_device_model,
    )


@pytest.fixture
def ev_agent(mock_gridlabd, mock_data_streams, mock_device_model):
    """DeviceAgent configured for EV charger."""
    return _make_agent(
        "agent_ev_1",
        DeviceType.EV_CHARGER,
        mock_gridlabd,
        0.5,
        mock_data_streams,
        mock_device_model,
    )


@pytest.fixture
def rt_timing():
    return MarketTimingParams(
        t_activate=-600.0,
        t_negotiate=-420.0,
        t_market_lead=-60.0,
        t_clear=0.0,
        t_delivery_start=0.0,
        t_delivery_end=300.0,
        t_reconcile_end=600.0,
    )


def _make_market_object(market_id="RT_1000", **kwargs):
    """Helper to create a MarketObject with sensible defaults."""
    defaults = dict(
        market_type=MarketType.RT_ENERGY,
        timing_params=MarketTimingParams(),
        operating_mode=OperatingMode.BIDDING,
    )
    defaults.update(kwargs)
    return MarketObject(market_id=market_id, **defaults)


@pytest.fixture
def proportional_penalty():
    return PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate": 0.05},
    )


@pytest.fixture
def binding_clearing():
    return ClearingResult(
        market_id="RT_1000",
        interval_id="int_1000_1300",
        cleared_price=0.10,
        cleared_quantity=3.0,
        iteration=1,
        iteration_type=IterationType.BINDING,
        timestamp=1000.0,
    )


@pytest.fixture
def informational_clearing():
    return ClearingResult(
        market_id="RT_1000",
        interval_id="int_1000_1300",
        cleared_price=0.12,
        cleared_quantity=2.5,
        iteration=1,
        iteration_type=IterationType.INFORMATIONAL,
        timestamp=900.0,
    )


# ===================================================================
# Construction Tests
# ===================================================================


class TestDeviceAgentConstruction:
    """Verify construction stores all dependencies and creates placeholders."""

    def test_stores_agent_id(self, hvac_agent):
        assert hvac_agent._agent_id == "agent_house_1"

    def test_stores_device_type(self, hvac_agent):
        assert hvac_agent._device_type == DeviceType.HVAC_AC_ONLY

    def test_stores_gridlabd(self, hvac_agent, mock_gridlabd):
        assert hvac_agent._gridlabd is mock_gridlabd

    def test_stores_preference_k(self, hvac_agent):
        assert hvac_agent._k == 0.3

    def test_stores_data_streams(self, hvac_agent, mock_data_streams):
        assert hvac_agent._data_streams is mock_data_streams

    def test_market_objects_empty(self, hvac_agent):
        assert hvac_agent._market_objects == {}

    def test_market_comms_empty(self, hvac_agent):
        assert hvac_agent._market_comms == {}

    def test_current_state_none(self, hvac_agent):
        assert hvac_agent._current_state is None


# ===================================================================
# _create_device_model
# ===================================================================


class TestCreateDeviceModel:
    """DeviceAgent._create_device_model() — factory by DeviceType.

    These tests construct DeviceAgent WITHOUT patching _create_device_model,
    so they exercise the real factory method.
    """

    def test_hvac_creates_hvac_model(self, mock_gridlabd, mock_data_streams):
        from device_models import HVACModel

        agent = DeviceAgent(
            agent_id="test",
            device_type=DeviceType.HVAC_AC_ONLY,
            gridlabd=mock_gridlabd,
            customer_preference_k=0.3,
            data_stream_manager=mock_data_streams,
        )
        assert isinstance(agent._device_model, HVACModel)

    def test_battery_creates_battery_model(self, mock_gridlabd, mock_data_streams):
        from device_models import BatteryModel

        agent = DeviceAgent(
            agent_id="test",
            device_type=DeviceType.BATTERY,
            gridlabd=mock_gridlabd,
            customer_preference_k=0.5,
            data_stream_manager=mock_data_streams,
        )
        assert isinstance(agent._device_model, BatteryModel)

    def test_wh_creates_wh_model(self, mock_gridlabd, mock_data_streams):
        from device_models import WaterHeaterModel

        agent = DeviceAgent(
            agent_id="test",
            device_type=DeviceType.WATER_HEATER,
            gridlabd=mock_gridlabd,
            customer_preference_k=0.4,
            data_stream_manager=mock_data_streams,
        )
        assert isinstance(agent._device_model, WaterHeaterModel)

    def test_ev_creates_ev_model(self, mock_gridlabd, mock_data_streams):
        from device_models import EVChargerModel

        agent = DeviceAgent(
            agent_id="test",
            device_type=DeviceType.EV_CHARGER,
            gridlabd=mock_gridlabd,
            customer_preference_k=0.5,
            data_stream_manager=mock_data_streams,
        )
        assert isinstance(agent._device_model, EVChargerModel)


# ===================================================================
# initialize
# ===================================================================


class TestInitialize:
    """DeviceAgent.initialize() — set up shared components."""

    def test_creates_flexibility_ledger(self, hvac_agent):
        hvac_agent.initialize(device_params={})
        assert hvac_agent._flexibility_ledger is not None

    def test_creates_command_arbiter(self, hvac_agent):
        hvac_agent.initialize(device_params={})
        assert hvac_agent._command_arbiter is not None

    def test_creates_planning_optimizer(self, hvac_agent):
        hvac_agent.initialize(device_params={})
        assert hvac_agent._planning_optimizer is not None

    def test_battery_with_params(self, battery_agent):
        battery_agent.initialize(
            device_params={
                "replacement_cost": 5000.0,
                "rated_cycles": 4000,
                "rated_dod": 0.80,
            }
        )
        assert battery_agent._flexibility_ledger is not None


# ===================================================================
# register_market
# ===================================================================


class TestRegisterMarket:
    """DeviceAgent.register_market() — store market config."""

    def test_stores_communication(
        self, hvac_agent, mock_market_comm, rt_timing, proportional_penalty
    ):
        hvac_agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=proportional_penalty,
            communication=mock_market_comm,
        )
        assert MarketType.RT_ENERGY in hvac_agent._market_comms

    def test_stores_penalty_model(
        self, hvac_agent, mock_market_comm, rt_timing, proportional_penalty
    ):
        hvac_agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=proportional_penalty,
            communication=mock_market_comm,
        )
        assert MarketType.RT_ENERGY in hvac_agent._penalty_models

    def test_multiple_market_types(
        self, hvac_agent, mock_market_comm, rt_timing, proportional_penalty
    ):
        for mt in [MarketType.RT_ENERGY, MarketType.DA_ENERGY]:
            hvac_agent.register_market(
                market_type=mt,
                timing_params=rt_timing,
                operating_mode=OperatingMode.BIDDING,
                penalty_model=proportional_penalty,
                communication=mock_market_comm,
            )
        assert len(hvac_agent._market_comms) == 2


# ===================================================================
# spawn_market_cycle
# ===================================================================


class TestSpawnMarketCycle:
    """DeviceAgent.spawn_market_cycle() — create new MarketObject."""

    def test_returns_market_id(
        self, hvac_agent, mock_market_comm, rt_timing, proportional_penalty
    ):
        hvac_agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=proportional_penalty,
            communication=mock_market_comm,
        )
        mid = hvac_agent.spawn_market_cycle(
            market_type=MarketType.RT_ENERGY,
            clearing_time=1000.0,
        )
        assert isinstance(mid, str)
        assert mid in hvac_agent._market_objects


# ===================================================================
# F1: observe_device_state
# ===================================================================


class TestObserveDeviceState:
    """DeviceAgent.observe_device_state() — dispatch by device type."""

    def test_hvac_returns_hvac_state(self, hvac_agent):
        state = hvac_agent.observe_device_state()
        assert isinstance(state, HVACState)

    def test_battery_returns_battery_state(self, battery_agent):
        state = battery_agent.observe_device_state()
        assert isinstance(state, BatteryState)

    def test_wh_returns_wh_state(self, wh_agent):
        state = wh_agent.observe_device_state()
        assert isinstance(state, WaterHeaterState)

    def test_caches_state(self, hvac_agent):
        """The observed state should be cached for later use."""
        state = hvac_agent.observe_device_state()
        assert hvac_agent._current_state is state

    def test_calls_gridlabd(self, hvac_agent, mock_gridlabd):
        """Must delegate to the appropriate GridLAB-D read method."""
        hvac_agent.observe_device_state()
        assert mock_gridlabd.read_hvac_state.called


# ===================================================================
# F2: estimate_flexibility
# ===================================================================


class TestEstimateFlexibility:
    """DeviceAgent.estimate_flexibility() — feasible operating range."""

    def test_returns_flexibility_envelope(self, hvac_agent):
        result = hvac_agent.estimate_flexibility(
            state=HVACState(),
            interval_duration=300.0,
        )
        assert isinstance(result, FlexibilityEnvelope)

    def test_q_min_le_q_max(self, hvac_agent):
        result = hvac_agent.estimate_flexibility(
            state=HVACState(),
            interval_duration=300.0,
        )
        assert result.Q_min <= result.Q_max

    def test_baseline_in_range(self, hvac_agent):
        result = hvac_agent.estimate_flexibility(
            state=HVACState(),
            interval_duration=300.0,
        )
        assert result.Q_min <= result.Q_baseline <= result.Q_max

    def test_battery_bidirectional(self, battery_agent, mock_device_model):
        """Battery flexibility should include negative Q (discharge)."""
        mock_device_model.estimate_flexibility.return_value = FlexibilityEnvelope(
            Q_min=-5.0, Q_max=5.0, Q_baseline=0.0
        )
        result = battery_agent.estimate_flexibility(
            state=BatteryState(soc=0.5),
            interval_duration=300.0,
        )
        assert result.Q_min < 0


# ===================================================================
# F3: generate_preference_curve
# ===================================================================


class TestGeneratePreferenceCurve:
    """DeviceAgent.generate_preference_curve() — preference from flexibility."""

    def test_returns_preference_curve(self, hvac_agent):
        flex = FlexibilityEnvelope(Q_min=0.0, Q_max=5.0, Q_baseline=3.0)
        result = hvac_agent.generate_preference_curve(flexibility=flex)
        assert isinstance(result, PreferenceCurve)

    def test_anchored_to_baseline(self, hvac_agent):
        """Preference curve Q_0 should match flexibility baseline."""
        flex = FlexibilityEnvelope(Q_min=0.0, Q_max=5.0, Q_baseline=3.0)
        curve = hvac_agent.generate_preference_curve(flexibility=flex)
        assert curve._Q_0 == pytest.approx(3.0, abs=0.1)

    def test_caches_curve(self, hvac_agent):
        flex = FlexibilityEnvelope(Q_min=0.0, Q_max=5.0, Q_baseline=3.0)
        curve = hvac_agent.generate_preference_curve(flexibility=flex)
        assert hvac_agent._current_preference_curve is curve


# ===================================================================
# F4: formulate_bid
# ===================================================================


class TestFormulateBid:
    """DeviceAgent.formulate_bid() — price-quantity bid curve."""

    def test_returns_bid_curve(self, hvac_agent):
        mo = _make_market_object()
        flex = FlexibilityEnvelope(Q_min=0.0, Q_max=5.0, Q_baseline=3.0)
        pref = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        bid = hvac_agent.formulate_bid(
            market_obj=mo,
            flexibility=flex,
            preference_curve=pref,
        )
        assert isinstance(bid, BidCurve)

    def test_bid_has_points(self, hvac_agent):
        mo = _make_market_object()
        flex = FlexibilityEnvelope(Q_min=0.0, Q_max=5.0, Q_baseline=3.0)
        pref = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        bid = hvac_agent.formulate_bid(
            market_obj=mo,
            flexibility=flex,
            preference_curve=pref,
        )
        assert len(bid.points) > 0

    def test_bid_prices_descending(self, hvac_agent):
        """Bid curve points should be in descending price order."""
        mo = _make_market_object()
        flex = FlexibilityEnvelope(Q_min=0.0, Q_max=5.0, Q_baseline=3.0)
        pref = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        bid = hvac_agent.formulate_bid(
            market_obj=mo,
            flexibility=flex,
            preference_curve=pref,
        )
        prices = [p.price for p in bid.points]
        assert prices == sorted(prices, reverse=True)


# ===================================================================
# F7: evaluate_price_response
# ===================================================================


class TestEvaluatePriceResponse:
    """DeviceAgent.evaluate_price_response() — price → operating point."""

    def test_returns_float(self, hvac_agent):
        curve = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        result = hvac_agent.evaluate_price_response(price=0.10, curve=curve)
        assert isinstance(result, float)

    def test_higher_price_less_consumption(self, hvac_agent):
        """Higher prices should reduce consumption (demand slopes down)."""
        curve = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        q_low = hvac_agent.evaluate_price_response(price=0.05, curve=curve)
        q_high = hvac_agent.evaluate_price_response(price=0.20, curve=curve)
        assert q_high <= q_low

    def test_at_reference_price(self, hvac_agent):
        """At P_0, response should be near Q_0."""
        curve = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        result = hvac_agent.evaluate_price_response(price=0.10, curve=curve)
        assert result == pytest.approx(3.0, abs=0.5)

    def test_with_bid_curve(self, hvac_agent):
        """Should also work with a BidCurve (bidding mode)."""
        bid = BidCurve(
            points=[
                BidPoint(price=0.20, quantity=1.0),
                BidPoint(price=0.10, quantity=3.0),
                BidPoint(price=0.05, quantity=5.0),
            ],
            market_id="RT_1000",
        )
        result = hvac_agent.evaluate_price_response(price=0.10, curve=bid)
        assert isinstance(result, float)


# ===================================================================
# F8: translate_to_control
# ===================================================================


class TestTranslateToControl:
    """DeviceAgent.translate_to_control() — power → DeviceCommand."""

    def test_returns_device_command(self, hvac_agent):
        result = hvac_agent.translate_to_control(
            target_power=3.0,
            state=HVACState(),
        )
        assert isinstance(result, DeviceCommand)

    def test_command_has_correct_device_type(self, hvac_agent):
        result = hvac_agent.translate_to_control(
            target_power=3.0,
            state=HVACState(),
        )
        assert result.device_type == DeviceType.HVAC_AC_ONLY

    def test_battery_discharge_negative_target(self, battery_agent):
        """Negative target power → discharge command."""
        result = battery_agent.translate_to_control(
            target_power=-3.0,
            state=BatteryState(soc=0.5),
        )
        assert isinstance(result, DeviceCommand)


# ===================================================================
# F12: log_performance
# ===================================================================


class TestLogPerformance:
    """DeviceAgent.log_performance() — record delivery performance."""

    def test_records_entry(self, hvac_agent):
        mo = _make_market_object()
        fulfillment = FulfillmentRecord(
            market_id="RT_1000",
            committed=3.0,
            actual=2.8,
            shortfall=0.2,
            revenue=0.28,
            penalty=0.01,
            net_value=0.27,
        )
        hvac_agent.log_performance(
            market_obj=mo,
            fulfillment=fulfillment,
            timestamp=1000.0,
        )
        assert len(mo.performance_log) >= 1


# ===================================================================
# F13: reconcile
# ===================================================================


class TestReconcile:
    """DeviceAgent.reconcile() — compute settlement."""

    def test_returns_settlement_record(self, hvac_agent):
        mo = _make_market_object()
        result = hvac_agent.reconcile(market_obj=mo)
        assert isinstance(result, SettlementRecord)

    def test_settlement_market_id(self, hvac_agent):
        mo = _make_market_object()
        result = hvac_agent.reconcile(market_obj=mo)
        assert isinstance(result.market_id, str)


# ===================================================================
# Phase Handlers
# ===================================================================


class TestHandleActive:
    """DeviceAgent._handle_active() — Active phase: observe + flex + pref."""

    def test_sets_current_state(self, hvac_agent):
        mo = _make_market_object()
        hvac_agent._handle_active(mo)
        assert hvac_agent._current_state is not None

    def test_sets_current_flexibility(self, hvac_agent):
        mo = _make_market_object()
        hvac_agent._handle_active(mo)
        assert hvac_agent._current_flexibility is not None


class TestHandleNegotiation:
    """DeviceAgent._handle_negotiation() — bid formulation + submission."""

    def test_bidding_mode_submits_bid(
        self, hvac_agent, mock_market_comm, rt_timing, proportional_penalty
    ):
        hvac_agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=proportional_penalty,
            communication=mock_market_comm,
        )
        mo = _make_market_object(timing_params=rt_timing)
        # Provide state so bid can be made
        hvac_agent._current_state = HVACState()
        hvac_agent._current_flexibility = FlexibilityEnvelope(
            Q_min=0.0,
            Q_max=5.0,
            Q_baseline=3.0,
        )
        hvac_agent._current_preference_curve = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        hvac_agent._handle_negotiation(mo)
        assert mock_market_comm.submit_bid.called


class TestHandleMarketLead:
    """DeviceAgent._handle_market_lead() — MO processing, no-op."""

    def test_is_noop(self, hvac_agent):
        mo = _make_market_object()
        before = hvac_agent._current_state
        hvac_agent._handle_market_lead(mo)
        assert hvac_agent._current_state is before


class TestHandleAssessment:
    """DeviceAgent._handle_assessment() — process informational or binding."""

    def test_informational_stores_advisory(self, hvac_agent, informational_clearing):
        mo = _make_market_object()
        mo.current_phase = MarketPhase.ASSESSMENT
        hvac_agent._current_state = HVACState()
        hvac_agent._handle_assessment(mo, informational_clearing)
        # Informational clear should loop back to ACTIVE.
        assert mo.current_phase == MarketPhase.ACTIVE
        assert len(mo.advisory_history) >= 1

    def test_binding_transitions_to_delivery_lead(self, hvac_agent, binding_clearing):
        mo = _make_market_object()
        mo.current_phase = MarketPhase.ASSESSMENT
        hvac_agent._current_state = HVACState()
        hvac_agent._handle_assessment(mo, binding_clearing)
        # Binding clear should transition to DELIVERY_LEAD.
        assert mo.current_phase == MarketPhase.DELIVERY_LEAD


class TestHandleDeliveryLead:
    """DeviceAgent._handle_delivery_lead() — prepare for delivery."""

    def test_evaluates_response(self, hvac_agent, binding_clearing):
        mo = _make_market_object()
        hvac_agent._current_state = HVACState()
        hvac_agent._current_preference_curve = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        hvac_agent._handle_delivery_lead(mo, binding_clearing)


class TestHandleDeliveryStart:
    """DeviceAgent._handle_delivery_start() — register with arbiter."""

    def test_registers_delivery(self, hvac_agent, proportional_penalty):
        mo = _make_market_object()
        mo.cleared_quantity = 3.0
        mo.cleared_price = 0.10
        hvac_agent._command_arbiter = MagicMock()
        hvac_agent._penalty_models[mo.market_type] = proportional_penalty
        hvac_agent._handle_delivery_start(mo)
        hvac_agent._command_arbiter.register_delivery.assert_called_once()


class TestHandleDeliveryTick:
    """DeviceAgent._handle_delivery_tick() — per-timestep delivery logic."""

    def test_observes_and_dispatches(self, hvac_agent):
        hvac_agent.observe_device_state = MagicMock(return_value=HVACState())
        hvac_agent._current_preference_curve = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=3.0,
            P_0=0.10,
            k=0.3,
        )
        hvac_agent._command_arbiter = MagicMock()
        hvac_agent._command_arbiter.resolve_and_actuate.return_value = {}
        hvac_agent._handle_delivery_tick(timestamp=1000.0)
        hvac_agent.observe_device_state.assert_called_once()
        hvac_agent._command_arbiter.resolve_and_actuate.assert_called()


class TestHandleReconcile:
    """DeviceAgent._handle_reconcile() — compute settlement + report."""

    def test_computes_settlement(self, hvac_agent):
        mo = _make_market_object()
        mock_comm = MagicMock()
        hvac_agent._market_comms[mo.market_type] = mock_comm
        hvac_agent.reconcile = MagicMock(
            return_value=SettlementRecord(market_id=mo.market_id)
        )
        hvac_agent._handle_reconcile(mo)
        mock_comm.submit_reconciliation.assert_called_once()


class TestHandleExpired:
    """DeviceAgent._handle_expired() — cleanup + possible respawn."""

    def test_removes_from_active(self, hvac_agent):
        mo = _make_market_object()
        hvac_agent._handle_expired(mo)


# ===================================================================
# F11: step (main loop)
# ===================================================================


class TestStep:
    """DeviceAgent.step() — the main simulation timestep entry point."""

    def test_runs_without_markets(self, hvac_agent):
        """step() with no registered markets should be a safe no-op."""
        hvac_agent.step(current_time=1000.0)

    def test_processes_market_transitions(
        self, hvac_agent, mock_market_comm, rt_timing, proportional_penalty
    ):
        """With a registered market, step should check for transitions."""
        hvac_agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=proportional_penalty,
            communication=mock_market_comm,
        )
        hvac_agent.step(current_time=1000.0)


# ===================================================================
# Convergence / Confidence Helpers
# ===================================================================


class TestConvergenceAndConfidence:
    """DeviceAgent._compute_convergence() and _compute_confidence()."""

    def test_convergence_empty_history(self, hvac_agent):
        result = hvac_agent._compute_convergence([])
        assert 0.0 <= result <= 1.0

    def test_convergence_single_advisory(self, hvac_agent):
        history = [AdvisoryRecord(iteration=1, cleared_price=0.10)]
        result = hvac_agent._compute_convergence(history)
        assert 0.0 <= result <= 1.0

    def test_convergence_stable_prices(self, hvac_agent):
        """Stable prices → convergence near 1.0."""
        history = [
            AdvisoryRecord(iteration=i, cleared_price=0.10, price_delta=0.001)
            for i in range(5)
        ]
        result = hvac_agent._compute_convergence(history)
        assert result > 0.5

    def test_confidence_empty_history(self, hvac_agent):
        result = hvac_agent._compute_confidence([])
        assert 0.0 <= result <= 1.0

    def test_confidence_increases_with_iterations(self, hvac_agent):
        """More converging iterations → higher confidence."""
        short = [AdvisoryRecord(iteration=1, cleared_price=0.10)]
        long = [
            AdvisoryRecord(iteration=i, cleared_price=0.10, price_delta=0.001)
            for i in range(10)
        ]
        c_short = hvac_agent._compute_confidence(short)
        c_long = hvac_agent._compute_confidence(long)
        assert c_long >= c_short
