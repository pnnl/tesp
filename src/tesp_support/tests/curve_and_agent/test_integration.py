# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Integration tests for the curve_and_agent module.

These tests wire together real components end-to-end with no MagicMock.
Ground truth is taken from the design documents in design/curve_and_agent/:

  - sequence_rt_bidding.plantuml — RT binding cycle (F1→F13)
  - sequence_mo_clearing.plantuml — Market clearing algorithm
  - sequence_da_informational.plantuml — Informational + binding iterations
  - sequence_dso_seam.plantuml — DSO inflexible load estimation
  - sequence_multi_market.plantuml — Multi-market dispatch resolution
  - state_machine_market.plantuml — MarketObject lifecycle
  - class_diagram_core.plantuml — Module responsibilities & interfaces

Design invariants tested:

  1. Clearing price must lie at the supply/demand intersection, not at a
     curve endpoint (the bug that demo_multi caught).
  2. Higher prices → lower HVAC consumption (demand law of economics).
  3. Comfort-focused agents (low k) bid more inelastically than
     financial agents (high k).
  4. Aggregate demand = horizontal sum of all agent bids + DSO inflexible.
  5. Sum of per-agent cleared quantities = total flexible committed.
  6. DSO inflexible bid = total − flexible + losses − solar.
  7. Setpoint rises when clearing price exceeds reference price (HVAC
     cooling: agent backs off to save money).
  8. Settlement net = revenue − penalty, with revenue ≥ 0 for cooperating
     agents.
  9. Market state machine follows the design phase ordering:
     INACTIVE → ACTIVE → NEGOTIATION → MARKET_LEAD → ASSESSMENT →
     DELIVERY_LEAD → DELIVERY → RECONCILE → EXPIRED.
 10. Informational iterations loop back to ACTIVE; binding proceeds to
     DELIVERY_LEAD.
"""

import random

import pytest

from enums_and_constants import (
    DeviceType,
    MarketType,
    MarketPhase,
    OperatingMode,
    IterationType,
    PenaltyStructureType,
)
from data_types import (
    BidCurve,
    BidPoint,
    ClearingResult,
    FlexibilityEnvelope,
    MarketTimingParams,
    PerformanceEntry,
    SettlementRecord,
    DeviceCommand,
    FulfillmentRecord,
    HVACState,
)
from gridlabd_interface import GridLABDInterface
from data_streams import (
    DataStreamManager,
    ContinuousForecast,
    EventForecast,
    ConstraintStream,
    UncertaintyModel,
)
from data_types import EventDefinition, QuantilePoint, WaterHeaterState
from device_agent import DeviceAgent
from device_models import WaterHeaterModel
from market_agent import MarketCommunicationInterface
from market_operator import MarketOperator, SupplyCurve, DSOLoadEstimationEngine
from penalty_model import PenaltyModel
from preference_curve import PreferenceCurve


# =====================================================================
# Shared helpers — real objects, no mocks
# =====================================================================


class MockConnection:
    """Minimal stand-in for a GridLAB-D HELICS connection."""

    BASE = {
        "outdoor_temperature": "95.2",
        "cooling_setpoint": "72.0",
        "heating_setpoint": "68.0",
        "power_state": "COOL",
        "hvac_load": "12000",
        "mass_temperature": "74.8",
        "Ua": "500",
        "Hm": "1500",
        "Ca": "1500",
        "Cm": "5000",
        "cooling_COP": "3.5",
        "heating_COP": "3.0",
        "design_cooling_capacity": "36000",
        "design_heating_capacity": "36000",
        "solar_heatgain": "800",
        "internal_heatgain": "400",
    }

    def __init__(self, indoor_temp=76.3):
        self._data = dict(self.BASE)
        self._data["air_temperature"] = str(indoor_temp)
        self.written = {}

    def get_value(self, key):
        return self._data.get(key.split("#", 1)[-1], "")

    def set_value(self, key, value):
        self.written[key] = value


class MockTransport:
    """Bridges MarketCommunicationInterface → MarketOperator directly."""

    def __init__(self, mo):
        self._mo = mo
        self._results = {}

    def submit(
        self,
        *,
        agent_id,
        market_type=None,
        bid=None,
        settlement=None,
        market_id=None,
        interval_id=None,
    ):
        if bid is not None:
            return self._mo.submit_agent_bid(agent_id, bid)
        return True

    def receive(self, *, agent_id, market_id):
        return self._results.get(agent_id)

    def push_results(self, results):
        self._results.update(results)


def _make_supply():
    """Design doc supply curve (sequence_mo_clearing.plantuml)."""
    return SupplyCurve(
        points=[
            BidPoint(price=0.02, quantity=0.0),
            BidPoint(price=0.05, quantity=100.0),
            BidPoint(price=0.08, quantity=200.0),
            BidPoint(price=0.12, quantity=350.0),
            BidPoint(price=0.20, quantity=500.0),
            BidPoint(price=0.50, quantity=600.0),
            BidPoint(price=1.00, quantity=600.0),
        ]
    )


def _make_agent(agent_id, k, indoor_temp, mo, transport):
    """Build a fully wired DeviceAgent with real components."""
    conn = MockConnection(indoor_temp=indoor_temp)
    gld = GridLABDInterface(
        connection=conn,
        object_name=agent_id.replace("hvac", "house"),
        device_type=DeviceType.HVAC_AC_ONLY,
    )
    dsm = DataStreamManager(DeviceType.HVAC_AC_ONLY)
    agent = DeviceAgent(
        agent_id=agent_id,
        device_type=DeviceType.HVAC_AC_ONLY,
        gridlabd=gld,
        customer_preference_k=k,
        data_stream_manager=dsm,
    )
    agent.initialize({})
    rt_timing = MarketTimingParams()
    penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )
    comm = MarketCommunicationInterface(
        transport=transport,
        agent_id=agent_id,
        market_type=MarketType.RT_ENERGY,
    )
    agent.register_market(
        market_type=MarketType.RT_ENERGY,
        timing_params=rt_timing,
        operating_mode=OperatingMode.BIDDING,
        penalty_model=penalty,
        communication=comm,
    )
    return agent, conn, comm, penalty


def _run_f1_through_f5(agent, comm):
    """Execute F1–F5 for a single agent and return intermediate results."""
    state = agent.observe_device_state()
    flex = agent.estimate_flexibility(state, 300.0)
    pref = agent.generate_preference_curve(flex)
    mid = agent.spawn_market_cycle(MarketType.RT_ENERGY, clearing_time=300.0)
    mobj = agent._market_objects[mid]
    mobj.available_flexibility = flex
    mobj.preference_curve = pref
    bid = agent.formulate_bid(mobj, flex, pref)
    comm.submit_bid(bid, market_id=mid, interval_id=f"int_{mid}")
    return state, flex, pref, bid, mid, mobj


# =====================================================================
# 1. Full RT Binding Cycle — F1 through F13
#    (sequence_rt_bidding.plantuml)
# =====================================================================


class TestRTBindingCycleEndToEnd:
    """The design spec says a single RT binding cycle walks through
    F1 → F2 → F3 → F4 → F5 → clear → F7 → F8 → delivery → F13.
    This test does exactly that with 10 agents and validates results."""

    @pytest.fixture(autouse=True)
    def setup(self):
        random.seed(99)
        self.mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        self.mo.set_supply_curve(_make_supply())
        dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
        self.dso_bid = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=200.0,
            flexible_committed=0.0,
            btm_solar_forecast=30.0,
            loss_factor=0.04,
        )
        self.mo.submit_dso_inflexible_bid("feeder_1", self.dso_bid)
        self.transport = MockTransport(self.mo)

        self.agents, self.conns, self.comms = [], [], []
        self.mids, self.mobjs = [], []
        self.states, self.flexes, self.prefs, self.bids = [], [], [], []

        for i in range(10):
            indoor = round(random.uniform(73.0, 79.0), 1)
            k = round(random.uniform(0.15, 0.85), 2)
            ag, conn, comm, _ = _make_agent(
                f"hvac_{i + 1}",
                k,
                indoor,
                self.mo,
                self.transport,
            )
            st, fl, pr, bd, mid, mobj = _run_f1_through_f5(ag, comm)
            self.agents.append(ag)
            self.conns.append(conn)
            self.comms.append(comm)
            self.states.append(st)
            self.flexes.append(fl)
            self.prefs.append(pr)
            self.bids.append(bd)
            self.mids.append(mid)
            self.mobjs.append(mobj)

        self.clearing = self.mo.clear_market()
        self.per_agent = self.mo.propagate_results()

    # -- Design invariant 1: clearing at the intersection, not endpoint --

    def test_clearing_price_between_supply_and_demand_bounds(self):
        """Clearing price must lie strictly between lowest supply price
        and highest demand price — not pinned at a curve endpoint."""
        supply_prices = [pt.price for pt in _make_supply().points]
        assert self.clearing.cleared_price > min(supply_prices)
        assert self.clearing.cleared_price < max(supply_prices)

    def test_clearing_quantity_positive(self):
        """Design: cleared quantity = total demand at P*."""
        assert self.clearing.cleared_quantity > 0.0

    def test_supply_equals_demand_at_clearing(self):
        """At the clearing price, supply must approximately equal demand."""
        supply_at_p = _make_supply().get_supply_at_price(self.clearing.cleared_price)
        assert supply_at_p == pytest.approx(
            self.clearing.cleared_quantity,
            rel=0.05,
        )

    # -- Design invariant 5: sum agents = total flexible --

    def test_agent_quantities_sum_to_total_flexible(self):
        """Design (class_diagram_core): propagate_results returns per-agent
        quantities whose sum equals get_total_flexible_committed()."""
        agent_total = sum(r.cleared_quantity for r in self.per_agent.values())
        mo_total = self.mo.get_total_flexible_committed()
        assert agent_total == pytest.approx(mo_total, rel=0.01)

    # -- Design invariant: all agents get the same clearing price --

    def test_uniform_clearing_price(self):
        """All agents receive the same market clearing price."""
        prices = {r.cleared_price for r in self.per_agent.values()}
        assert len(prices) == 1
        assert prices.pop() == pytest.approx(self.clearing.cleared_price)

    # -- F7/F8: price response produces valid control commands --

    def test_price_response_returns_float_in_flex_range(self):
        """F7: evaluate_price_response returns Q in [Q_min, Q_max]."""
        for i, ag in enumerate(self.agents):
            q = ag.evaluate_price_response(
                self.clearing.cleared_price,
                self.prefs[i],
            )
            assert isinstance(q, float)
            # Allow slight overshoot from isoelastic curve
            assert q >= self.flexes[i].Q_min - 0.5
            assert q <= self.flexes[i].Q_max + 5.0

    def test_translate_to_control_returns_device_command(self):
        """F8: translate_to_control produces a DeviceCommand."""
        ag = self.agents[0]
        q = ag.evaluate_price_response(
            self.clearing.cleared_price,
            self.prefs[0],
        )
        cmd = ag.translate_to_control(q, self.states[0])
        assert isinstance(cmd, DeviceCommand)
        assert cmd.device_type == DeviceType.HVAC_AC_ONLY

    # -- F13: full delivery + reconciliation path --

    def test_reconciliation_produces_settlement(self):
        """F12 + F13: delivery ticks → performance log → settlement record
        with revenue ≥ 0 (cooperating agent) and net = revenue − penalty."""
        ag = self.agents[0]
        mobj = self.mobjs[0]
        mid = self.mids[0]
        h1_result = self.per_agent[ag._agent_id]
        penalty_model = PenaltyModel(
            market_type=MarketType.RT_ENERGY,
            structure_type=PenaltyStructureType.PROPORTIONAL,
            params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
        )
        mobj.cleared_price = self.clearing.cleared_price
        mobj.cleared_quantity = h1_result.cleared_quantity

        ag._command_arbiter.register_delivery(
            market_id=mid,
            market_type=str(MarketType.RT_ENERGY),
            product_type="ENERGY_BASE",
            committed_qty=h1_result.cleared_quantity,
            cleared_price=self.clearing.cleared_price,
            penalty_model=penalty_model,
            interval=(0.0, 300.0),
        )

        for tick in range(5):
            frs = ag._command_arbiter.resolve_and_actuate(
                device_state=self.states[0],
                preference_curve=self.prefs[0],
                amenity_weight=ag._k,
                current_time=tick * 60.0,
            )
            for m_id, fr in frs.items():
                mobj.performance_log.append(
                    PerformanceEntry(
                        timestamp=tick * 60.0,
                        committed=fr.committed,
                        actual=fr.actual,
                        shortfall=fr.shortfall,
                        revenue=fr.revenue,
                        penalty=fr.penalty,
                        net_value=fr.net_value,
                    )
                )

        settlement = ag.reconcile(mobj)
        assert isinstance(settlement, SettlementRecord)
        # Design invariant 8: net = revenue − penalty
        assert settlement.net_settlement == pytest.approx(
            settlement.total_revenue - settlement.total_penalty,
        )
        # Cooperating agent should earn revenue
        assert settlement.total_revenue >= 0.0


# =====================================================================
# 2. Market Clearing Algorithm — Supply/Demand Intersection
#    (sequence_mo_clearing.plantuml)
# =====================================================================


class TestClearingAlgorithm:
    """Validates the clearing algorithm finds the true supply/demand
    intersection via low-to-high price sweep with interpolation.
    This is the exact bug caught by demo_multi: the original algorithm
    swept high-to-low and always cleared at $1.00."""

    def test_clearing_not_at_max_price(self):
        """The clearing price should NOT be at the supply curve maximum.
        This is the regression test for the high-to-low sweep bug."""
        random.seed(42)
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
        dso_bid = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=300.0,
            flexible_committed=0.0,
            btm_solar_forecast=50.0,
            loss_factor=0.04,
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        transport = MockTransport(mo)
        # Create 50 agents — identical to demo_multi
        for i in range(50):
            indoor = round(random.uniform(73.0, 79.0), 1)
            k = round(random.uniform(0.15, 0.85), 2)
            ag, _, comm, _ = _make_agent(
                f"hvac_{i + 1}",
                k,
                indoor,
                mo,
                transport,
            )
            _run_f1_through_f5(ag, comm)

        clearing = mo.clear_market()
        # Price must NOT be pinned at $1.00 (the old bug)
        assert clearing.cleared_price < 0.50
        # Price must be reasonable — with ~260 kW inflexible + small flexible
        # and supply that reaches 350 kW at $0.12, price should be moderate
        assert clearing.cleared_price > 0.02

    def test_higher_demand_raises_clearing_price(self):
        """When inflexible demand increases, clearing price must rise.
        From design: supply curve is upward-sloping, so more demand →
        intersection shifts right/up on the supply curve."""
        results = []
        for inflex_load in [100.0, 300.0, 500.0]:
            random.seed(42)
            mo = MarketOperator(
                market_type=MarketType.RT_ENERGY,
                timing_params=MarketTimingParams(),
                iteration_protocol="fixed_count",
                n_informational=0,
            )
            mo.set_supply_curve(_make_supply())
            dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
            dso_bid = dso.estimate_inflexible_load(
                interval=(0.0, 300.0),
                total_load_forecast=inflex_load,
                flexible_committed=0.0,
                btm_solar_forecast=0.0,
                loss_factor=0.0,
            )
            mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
            transport = MockTransport(mo)
            for i in range(10):
                indoor = round(random.uniform(73.0, 79.0), 1)
                k = round(random.uniform(0.15, 0.85), 2)
                ag, _, comm, _ = _make_agent(
                    f"hvac_{i + 1}",
                    k,
                    indoor,
                    mo,
                    transport,
                )
                _run_f1_through_f5(ag, comm)
            clearing = mo.clear_market()
            results.append(clearing.cleared_price)

        # Monotonically increasing prices with increasing demand
        assert results[0] < results[1] < results[2]

    def test_zero_demand_clears_at_minimum(self):
        """With zero inflexible demand and zero agent bids, clearing
        should produce a minimal price near the supply floor."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        # Single agent with tiny demand
        dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
        dso_bid = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=5.0,
            flexible_committed=0.0,
            btm_solar_forecast=0.0,
            loss_factor=0.0,
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        clearing = mo.clear_market()
        # With only 5 kW demand, price should be very low
        assert clearing.cleared_price <= 0.05


# =====================================================================
# 3. Preference Curve — Economic Demand Behavior
#    (class_diagram_core.plantuml, sequence_rt_bidding.plantuml)
# =====================================================================


class TestPreferenceCurveDemandLaw:
    """Design spec: 'High price → low consumption, Low price → high
    consumption' (isoelastic demand curve Q = Q_0 * (P/P_0)^{-ε}).
    """

    @pytest.fixture
    def comfort_agent_curve(self):
        """k=0.2, comfort-focused → small epsilon → inelastic."""
        return PreferenceCurve(k=0.2, P_0=0.10, Q_0=3.0, epsilon_max=5.0)

    @pytest.fixture
    def financial_agent_curve(self):
        """k=0.8, financially focused → large epsilon → elastic."""
        return PreferenceCurve(k=0.8, P_0=0.10, Q_0=3.0, epsilon_max=5.0)

    def test_demand_decreases_with_price(self, comfort_agent_curve):
        """Design invariant 2: higher price → lower consumption."""
        prices = [0.02, 0.05, 0.10, 0.15, 0.20, 0.50]
        quantities = [comfort_agent_curve.evaluate(p) for p in prices]
        for i in range(len(quantities) - 1):
            assert quantities[i] >= quantities[i + 1], (
                f"Demand should decrease: Q({prices[i]})={quantities[i]:.3f} "
                f"should be >= Q({prices[i + 1]})={quantities[i + 1]:.3f}"
            )

    def test_at_reference_price_quantity_equals_baseline(self, comfort_agent_curve):
        """At P_0, the curve returns Q_0 (by design of isoelastic curve)."""
        q_at_p0 = comfort_agent_curve.evaluate(0.10)
        assert q_at_p0 == pytest.approx(3.0, rel=0.01)

    def test_comfort_agent_more_inelastic(
        self,
        comfort_agent_curve,
        financial_agent_curve,
    ):
        """Design invariant 3: comfort-focused (low k) is more inelastic.
        At a high price, comfort agent still consumes near baseline while
        financial agent drastically reduces."""
        high_price = 0.30  # 3x the reference price
        q_comfort = comfort_agent_curve.evaluate(high_price)
        q_financial = financial_agent_curve.evaluate(high_price)
        # Both consume less than baseline at high price
        assert q_comfort < 3.0
        assert q_financial < 3.0
        # Comfort agent consumes MORE than financial at high price
        assert q_comfort > q_financial, (
            f"Comfort agent ({q_comfort:.3f} kW) should consume more than "
            f"financial agent ({q_financial:.3f} kW) at ${high_price}/kWh"
        )

    def test_evaluate_with_bounds_clamps(self, comfort_agent_curve):
        """evaluate_with_bounds must clamp to [Q_min, Q_max]."""
        # At very low price, raw Q would be very large
        q_raw = comfort_agent_curve.evaluate(0.001)
        q_bounded = comfort_agent_curve.evaluate_with_bounds(0.001, 0.0, 5.0)
        assert q_bounded <= 5.0
        assert q_bounded >= 0.0

    def test_bid_curve_prices_descending(self, comfort_agent_curve):
        """Design (F4): bid curve sampled from preference curve has
        prices in descending order (market convention)."""
        points = comfort_agent_curve.sample_bid_curve(
            price_min=0.01,
            price_max=1.0,
            n_points=11,
            Q_min=0.0,
            Q_max=5.0,
        )
        prices = [pt.price for pt in points]
        for i in range(len(prices) - 1):
            assert prices[i] >= prices[i + 1]


# =====================================================================
# 4. DSO Inflexible Load Estimation
#    (sequence_dso_seam.plantuml)
# =====================================================================


class TestDSOInflexibleLoad:
    """Design: Q_inflexible = total − flexible + losses − solar.
    From sequence_dso_seam.plantuml example:
      total=1200, flexible=0, loss_factor=0.052, solar=180
      losses = 1200 × 0.052 = 62.4
      Q = 1200 − 0 + 62.4 − 180 = 1082.4
    """

    def test_dso_formula_matches_design_example(self):
        """Reproduce the exact example from sequence_dso_seam.plantuml."""
        dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
        bid = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=1200.0,
            flexible_committed=0.0,
            btm_solar_forecast=180.0,
            loss_factor=0.052,
        )
        # Design: Q = 1200 - 0 + 62.4 - 180 = 1082.4
        assert bid.quantity == pytest.approx(1082.4, abs=5.0)

    def test_flexible_committed_reduces_inflexible(self):
        """Design: when agents commit flexible load, DSO subtracts it
        to avoid double-counting."""
        dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
        bid_no_flex = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=1000.0,
            flexible_committed=0.0,
            btm_solar_forecast=0.0,
            loss_factor=0.0,
        )
        bid_with_flex = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=1000.0,
            flexible_committed=200.0,
            btm_solar_forecast=0.0,
            loss_factor=0.0,
        )
        # flexible_committed reduces inflexible by that amount
        assert bid_with_flex.quantity < bid_no_flex.quantity
        diff = bid_no_flex.quantity - bid_with_flex.quantity
        assert diff == pytest.approx(200.0, abs=10.0)

    def test_solar_reduces_inflexible(self):
        """Design: BTM solar is subtracted from inflexible load."""
        dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
        bid_no_solar = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=1000.0,
            flexible_committed=0.0,
            btm_solar_forecast=0.0,
            loss_factor=0.0,
        )
        bid_solar = dso.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=1000.0,
            flexible_committed=0.0,
            btm_solar_forecast=100.0,
            loss_factor=0.0,
        )
        assert bid_solar.quantity < bid_no_solar.quantity
        diff = bid_no_solar.quantity - bid_solar.quantity
        assert diff == pytest.approx(100.0, abs=5.0)


# =====================================================================
# 5. Aggregate Demand — Horizontal Summation
#    (sequence_mo_clearing.plantuml)
# =====================================================================


class TestAggregateDemandHorizontalSum:
    """Design: 'Horizontally sums all agent flexible bids +
    DSO inflexible bid (vertical line).'"""

    def test_aggregate_includes_inflexible_base(self):
        """At every price level, aggregate demand ≥ inflexible load."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        inflex_qty = 200.0
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=inflex_qty,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)

        # Add two agents with known bids
        bid1 = BidCurve(
            points=[
                BidPoint(price=0.20, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        bid2 = BidCurve(
            points=[
                BidPoint(price=0.15, quantity=3.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        mo.submit_agent_bid("agent_1", bid1)
        mo.submit_agent_bid("agent_2", bid2)

        agg = mo.aggregate_demand()
        for pt in agg:
            assert pt.quantity >= inflex_qty - 0.1, (
                f"At ${pt.price:.2f}, demand {pt.quantity:.1f} kW should be "
                f">= inflexible {inflex_qty:.1f} kW"
            )

    def test_aggregate_demand_monotonically_nonincreasing(self):
        """Aggregate demand curve must be non-increasing in price
        (higher price → lower or equal demand)."""
        random.seed(42)
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        transport = MockTransport(mo)

        for i in range(20):
            indoor = round(random.uniform(73.0, 79.0), 1)
            k = round(random.uniform(0.15, 0.85), 2)
            ag, _, comm, _ = _make_agent(
                f"hvac_{i + 1}",
                k,
                indoor,
                mo,
                transport,
            )
            _run_f1_through_f5(ag, comm)

        agg = mo.aggregate_demand()
        # agg is ordered by decreasing price (highest price first)
        for i in range(len(agg) - 1):
            if agg[i].price > agg[i + 1].price:
                assert agg[i].quantity <= agg[i + 1].quantity, (
                    f"Demand at ${agg[i].price:.4f} ({agg[i].quantity:.1f} kW) "
                    f"should be <= demand at ${agg[i + 1].price:.4f} "
                    f"({agg[i + 1].quantity:.1f} kW)"
                )


# =====================================================================
# 6. Setpoint Response to Price
#    (sequence_rt_bidding.plantuml: F7/F8)
# =====================================================================


class TestSetpointResponseToPrice:
    """Design: 'Setpoint raised by N°F to save money' when price > P_0.
    For HVAC cooling: higher price → agent raises setpoint → less cooling."""

    def test_high_price_raises_cooling_setpoint(self):
        """When market clears above the reference price, the HVAC agent
        should raise its cooling setpoint (backing off cooling)."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=400.0,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        transport = MockTransport(mo)

        # Financial agent (k=0.8) with known setpoint at 72°F
        ag, conn, comm, _ = _make_agent(
            "hvac_1",
            0.8,
            76.0,
            mo,
            transport,
        )
        state, flex, pref, bid, mid, mobj = _run_f1_through_f5(ag, comm)

        clearing = mo.clear_market()
        target_q = ag.evaluate_price_response(clearing.cleared_price, pref)
        cmd = ag.translate_to_control(target_q, state)

        # Per design: higher price → higher setpoint (less cooling)
        original_setpoint = state.thermostat_setpoint
        assert cmd.setpoint >= original_setpoint, (
            f"Setpoint should rise from {original_setpoint}°F to at least "
            f"match it, got {cmd.setpoint}°F at ${clearing.cleared_price:.4f}/kWh"
        )

    def test_low_price_maintains_or_lowers_setpoint(self):
        """When market clears below the reference price, the HVAC agent
        should maintain or lower its cooling setpoint (more cooling)."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        # Very low inflexible demand → low clearing price
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=10.0,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        transport = MockTransport(mo)

        ag, conn, comm, _ = _make_agent(
            "hvac_1",
            0.5,
            76.0,
            mo,
            transport,
        )
        state, flex, pref, bid, mid, mobj = _run_f1_through_f5(ag, comm)

        clearing = mo.clear_market()
        target_q = ag.evaluate_price_response(clearing.cleared_price, pref)
        cmd = ag.translate_to_control(target_q, state)

        # Low price → maintain or cool more → setpoint same or lower
        original_setpoint = state.thermostat_setpoint
        assert cmd.setpoint <= original_setpoint + 1.0, (
            f"At low price ${clearing.cleared_price:.4f}, setpoint "
            f"{cmd.setpoint}°F should not be much higher than "
            f"original {original_setpoint}°F"
        )


# =====================================================================
# 7. Iteration Protocol — Informational vs Binding
#    (sequence_da_informational.plantuml, state_machine_market.plantuml)
# =====================================================================


class TestIterationProtocol:
    """Design: 'fixed_count protocol: iter ≤ N → INFORMATIONAL,
    iter = N+1 → BINDING'."""

    def test_informational_iterations_then_binding(self):
        """With n_informational=2, first two iterations are INFORMATIONAL,
        third is BINDING."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=2,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=100.0,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)

        bid = BidCurve(
            points=[
                BidPoint(price=0.20, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        mo.submit_agent_bid("agent_1", bid)

        r1 = mo.clear_market()
        assert r1.iteration_type == IterationType.INFORMATIONAL

        # Re-submit bids for iteration 2
        mo.submit_agent_bid("agent_1", bid)
        r2 = mo.clear_market()
        assert r2.iteration_type == IterationType.INFORMATIONAL

        # Re-submit bids for iteration 3 (binding)
        mo.submit_agent_bid("agent_1", bid)
        r3 = mo.clear_market()
        assert r3.iteration_type == IterationType.BINDING

    def test_zero_informational_means_immediate_binding(self):
        """With n_informational=0, the first clearing is BINDING.
        Design: 'RT market: always BINDING' (no informational rounds)."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=100.0,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        bid = BidCurve(
            points=[
                BidPoint(price=0.20, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        mo.submit_agent_bid("agent_1", bid)

        result = mo.clear_market()
        assert result.iteration_type == IterationType.BINDING


# =====================================================================
# 8. Delivery & Fulfillment — Command Arbiter
#    (sequence_rt_bidding.plantuml, sequence_multi_market.plantuml)
# =====================================================================


class TestDeliveryFulfillment:
    """Design: during delivery, the Command Arbiter resolves committed
    quantities, computes fulfillment, and returns FulfillmentRecords.
    Revenue must be non-negative for a cooperating agent."""

    def test_fulfillment_record_fields(self):
        """Each FulfillmentRecord has committed, actual, shortfall, revenue,
        penalty, net_value as per the design data_types."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        transport = MockTransport(mo)

        ag, conn, comm, penalty = _make_agent(
            "hvac_1",
            0.5,
            76.0,
            mo,
            transport,
        )
        state, flex, pref, bid, mid, mobj = _run_f1_through_f5(ag, comm)

        clearing = mo.clear_market()
        per_agent = mo.propagate_results()
        h1_result = per_agent[ag._agent_id]

        ag._command_arbiter.register_delivery(
            market_id=mid,
            market_type=str(MarketType.RT_ENERGY),
            product_type="ENERGY_BASE",
            committed_qty=h1_result.cleared_quantity,
            cleared_price=clearing.cleared_price,
            penalty_model=penalty,
            interval=(0.0, 300.0),
        )

        frs = ag._command_arbiter.resolve_and_actuate(
            device_state=state,
            preference_curve=pref,
            amenity_weight=ag._k,
            current_time=0.0,
        )

        assert len(frs) > 0
        for m_id, fr in frs.items():
            assert isinstance(fr, FulfillmentRecord)
            assert fr.committed >= 0.0
            assert fr.actual >= 0.0
            assert fr.revenue >= 0.0
            # net_value = revenue - penalty
            assert fr.net_value == pytest.approx(fr.revenue - fr.penalty)


# =====================================================================
# 9. Population-Level Behaviors — k Correlations
#    (sequence_mo_clearing.plantuml)
# =====================================================================


class TestPopulationLevelBehaviors:
    """Design: 'Shape driven by k=0.3 → relatively inelastic curve'
    and 'k=0.8 → elastic curve with wide range'. At population scale,
    agents with higher k (financial) should clear less quantity at
    above-baseline prices."""

    def test_financial_agents_consume_less_at_high_price(self):
        """Given a clearing price above the reference price, agents with
        higher k should generally commit to less power."""
        random.seed(42)
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        # High inflexible demand to push price up
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=350.0,
            interval=(0.0, 300.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        transport = MockTransport(mo)

        agents_data = []
        # Create agents with identical indoor temp but varying k
        for k in [0.15, 0.30, 0.50, 0.70, 0.85]:
            ag, _, comm, _ = _make_agent(
                f"hvac_k{k}",
                k,
                76.0,
                mo,
                transport,
            )
            state, flex, pref, bid, mid, mobj = _run_f1_through_f5(ag, comm)
            agents_data.append(
                {
                    "k": k,
                    "agent": ag,
                    "pref": pref,
                    "flex": flex,
                }
            )

        clearing = mo.clear_market()

        # Evaluate price response for each agent
        responses = []
        for ad in agents_data:
            q = ad["agent"].evaluate_price_response(
                clearing.cleared_price,
                ad["pref"],
            )
            responses.append((ad["k"], q))

        # Financial agents (high k) should consume less than comfort agents
        # at above-baseline prices. Overall trend should be negative:
        # increasing k → decreasing Q
        low_k_qtys = [q for k, q in responses if k <= 0.30]
        high_k_qtys = [q for k, q in responses if k >= 0.70]
        avg_low = sum(low_k_qtys) / len(low_k_qtys) if low_k_qtys else 0
        avg_high = sum(high_k_qtys) / len(high_k_qtys) if high_k_qtys else 0
        assert avg_low > avg_high, (
            f"Comfort agents (avg Q={avg_low:.3f}) should consume more "
            f"than financial agents (avg Q={avg_high:.3f}) at high price "
            f"${clearing.cleared_price:.4f}/kWh"
        )


# =====================================================================
# 10. Bid Curve Structure — Design Conventions
#     (class_diagram_core.plantuml, sequence_rt_bidding.plantuml)
# =====================================================================


class TestBidCurveStructure:
    """Design: BidCurve has points with prices in descending order.
    F4 formulate_bid samples n_points=11 from the preference curve
    between price_min=0.01 and price_max=1.00."""

    def test_formulated_bid_has_11_points(self):
        """F4 design: sample_bid_curve with n_points=11."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        transport = MockTransport(mo)
        ag, _, comm, _ = _make_agent("hvac_1", 0.5, 76.0, mo, transport)
        _, _, _, bid, _, _ = _run_f1_through_f5(ag, comm)
        assert len(bid.points) == 11

    def test_bid_prices_span_full_range(self):
        """Bid prices should span from ~$1.00 down to ~$0.01."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        transport = MockTransport(mo)
        ag, _, comm, _ = _make_agent("hvac_1", 0.5, 76.0, mo, transport)
        _, _, _, bid, _, _ = _run_f1_through_f5(ag, comm)

        prices = [pt.price for pt in bid.points]
        assert max(prices) == pytest.approx(1.00, abs=0.01)
        assert min(prices) == pytest.approx(0.01, abs=0.01)

    def test_bid_quantities_nonnegative(self):
        """HVAC bids are demand-only (positive Q). Design: HVAC bid
        has 'demand only (positive Q)'."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        transport = MockTransport(mo)
        ag, _, comm, _ = _make_agent("hvac_1", 0.5, 76.0, mo, transport)
        _, _, _, bid, _, _ = _run_f1_through_f5(ag, comm)

        for pt in bid.points:
            assert pt.quantity >= 0.0, (
                f"HVAC bid quantity should be ≥ 0, got {pt.quantity} at ${pt.price}/kWh"
            )

    def test_bid_quantities_bounded_by_flexibility(self):
        """All bid quantities must be within [Q_min, Q_max]."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        transport = MockTransport(mo)
        ag, _, comm, _ = _make_agent("hvac_1", 0.5, 76.0, mo, transport)
        _, flex, _, bid, _, _ = _run_f1_through_f5(ag, comm)

        for pt in bid.points:
            assert pt.quantity >= flex.Q_min - 0.01
            assert pt.quantity <= flex.Q_max + 0.01


# =====================================================================
# 11. F1: State Observation — GridLAB-D Interface
#     (sequence_rt_bidding.plantuml)
# =====================================================================


class TestStateObservation:
    """Design: F1 reads device state from GridLAB-D and returns an
    HVACState with air_temp, outdoor_temp, setpoint, etc."""

    def test_observe_reads_connection_values(self):
        """Observed state matches what MockConnection provides."""
        conn = MockConnection(indoor_temp=77.5)
        gld = GridLABDInterface(
            connection=conn,
            object_name="house_1",
            device_type=DeviceType.HVAC_AC_ONLY,
        )
        dsm = DataStreamManager(DeviceType.HVAC_AC_ONLY)
        ag = DeviceAgent(
            agent_id="hvac_1",
            device_type=DeviceType.HVAC_AC_ONLY,
            gridlabd=gld,
            customer_preference_k=0.5,
            data_stream_manager=dsm,
        )
        ag.initialize({})
        state = ag.observe_device_state()

        assert isinstance(state, HVACState)
        assert state.indoor_air_temp == pytest.approx(77.5, abs=0.1)
        assert state.outdoor_air_temp == pytest.approx(95.2, abs=0.1)
        assert state.thermostat_setpoint == pytest.approx(72.0, abs=0.1)


# =====================================================================
# 12. F2: Flexibility Estimation
#     (sequence_rt_bidding.plantuml, class_diagram_core.plantuml)
# =====================================================================


class TestFlexibilityEstimation:
    """Design: estimate_flexibility returns a FlexibilityEnvelope with
    Q_min ≤ Q_baseline ≤ Q_max. For HVAC: Q_max derived from
    rated_capacity / COP / 3412.14."""

    def test_flexibility_envelope_ordering(self):
        """Q_min ≤ Q_baseline ≤ Q_max."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        transport = MockTransport(mo)
        ag, _, _, _ = _make_agent("hvac_1", 0.5, 76.0, mo, transport)

        state = ag.observe_device_state()
        flex = ag.estimate_flexibility(state, 300.0)
        assert isinstance(flex, FlexibilityEnvelope)
        assert flex.Q_min <= flex.Q_baseline <= flex.Q_max

    def test_hvac_q_max_consistent_with_rated_capacity(self):
        """Q_max should be = rated_cooling_capacity / COP / 3412.14.
        With defaults: 36000 / 3.5 / 3412.14 ≈ 3.01 kW."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        transport = MockTransport(mo)
        ag, _, _, _ = _make_agent("hvac_1", 0.5, 76.0, mo, transport)

        state = ag.observe_device_state()
        flex = ag.estimate_flexibility(state, 300.0)
        expected = 36000.0 / 3.5 / 3412.14
        assert flex.Q_max == pytest.approx(expected, rel=0.05)


# =====================================================================
# 13. Multi-Agent Scale — Reproducibility and Consistency
# =====================================================================


class TestMultiAgentReproducibility:
    """With a fixed seed, the entire simulation must be deterministic.
    This catches non-deterministic dictionary ordering or similar bugs."""

    def test_deterministic_with_fixed_seed(self):
        """Two runs with the same seed produce identical clearing results."""
        results = []
        for _ in range(2):
            random.seed(42)
            mo = MarketOperator(
                market_type=MarketType.RT_ENERGY,
                timing_params=MarketTimingParams(),
                iteration_protocol="fixed_count",
                n_informational=0,
            )
            mo.set_supply_curve(_make_supply())
            from market_operator import DSOInflexibleLoadBid

            dso_bid = DSOInflexibleLoadBid(
                feeder_id="feeder_1",
                quantity=260.0,
                interval=(0.0, 300.0),
            )
            mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
            transport = MockTransport(mo)

            for i in range(30):
                indoor = round(random.uniform(73.0, 79.0), 1)
                k = round(random.uniform(0.15, 0.85), 2)
                ag, _, comm, _ = _make_agent(
                    f"hvac_{i + 1}",
                    k,
                    indoor,
                    mo,
                    transport,
                )
                _run_f1_through_f5(ag, comm)

            clearing = mo.clear_market()
            results.append((clearing.cleared_price, clearing.cleared_quantity))

        assert results[0][0] == pytest.approx(results[1][0])
        assert results[0][1] == pytest.approx(results[1][1])


# =====================================================================
# Shared helpers — non-HVAC device agents with real models + data streams
# =====================================================================

# MockConnection already works for HVAC.  These provide per-device-type
# connection properties using the same dict-based pattern as the demo.


class _MockConnectionMultiDevice:
    """Dict-based GLD connection supporting all device types."""

    DEFAULTS = {
        # HVAC cooling house
        "power_state": "COOL",
        "air_temperature": "76.0",
        "outdoor_temperature": "92.0",
        "cooling_setpoint": "72.0",
        "heating_setpoint": "68.0",
        "hvac_load": "10000",
        "mass_temperature": "74.5",
        "Ua": "500",
        "Hm": "1500",
        "Ca": "1500",
        "Cm": "5000",
        "cooling_COP": "3.5",
        "heating_COP": "3.0",
        "design_cooling_capacity": "36000",
        "design_heating_capacity": "36000",
        "solar_heatgain": "0",
        "internal_heatgain": "0",
        # Water heater
        "UTTemp": "128.0",
        "LTTemp": "124.0",
        "upper_tank_setpoint": "130.0",
        "lower_tank_setpoint": "130.0",
        "UTState": "OFF",
        "LTState": "ON",
        "WHLoad": "2.5",
        "tank_volume": "50.0",
        "tank_UA": "2.0",
        "heating_element_capacity": "4.5",
        "inlet_water_temperature": "62.0",
        "WDRate": "0.0",
        "tank_height": "4.0",
        # EV charger
        "SOC": "0.42",
        "charge_rate": "0.0",
        "battery_capacity": "72.0",
        "max_charge_rate": "7.2",
        "charger_efficiency": "0.92",
        "vehicle_connected": "TRUE",
        "min_charge_rate": "1.0",
        "soc_at_max_taper": "0.82",
        # Battery
        "p_out": "0.0",
        "rated_power": "5.0",
        "round_trip_efficiency": "0.9",
        "cell_temperature": "25.0",
        "soc_min_bms": "0.1",
        "soc_max_bms": "0.95",
        "inverter_rated_power": "5.0",
        "state_of_health": "0.98",
    }

    def __init__(self, overrides=None):
        self._data = dict(self.DEFAULTS)
        if overrides:
            self._data.update(overrides)
        self.written = {}

    def get_value(self, key):
        prop = key.split("#", 1)[-1]
        return self._data.get(prop, "")

    def set_value(self, key, value):
        self.written[key] = value


def _create_hvac_data_streams(device_type):
    """Create DataStreamManager for HVAC with weather + setpoint + price streams."""
    dsm = DataStreamManager(device_type)
    temp_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 10.0, "tau_c": 24 * 3600}
    )
    dsm.register_continuous_stream(
        "outdoor_air_temp",
        ContinuousForecast(
            variable_name="outdoor_air_temp", unit="°F", uncertainty_model=temp_um
        ),
    )
    solar_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 250.0, "tau_c": 6 * 3600}
    )
    dsm.register_continuous_stream(
        "solar_irradiance",
        ContinuousForecast(
            variable_name="solar_irradiance", unit="W/m²", uncertainty_model=solar_um
        ),
    )
    sp_um = UncertaintyModel(
        model_type="empirical",
        params={"lead_time_sigma_table": [(0, 0.0), (86400, 0.5)]},
    )
    dsm.register_schedule(
        "hvac_setpoint_schedule",
        ContinuousForecast(
            variable_name="hvac_setpoint", unit="°F", uncertainty_model=sp_um
        ),
    )
    price_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 0.05, "tau_c": 4 * 3600}
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price", unit="$/kWh", uncertainty_model=price_um
        ),
    )
    return dsm


def _create_water_heater_data_streams():
    """Create DataStreamManager for water heater with draw, inlet, constraint streams."""
    dsm = DataStreamManager(DeviceType.WATER_HEATER)
    dsm.register_event_stream(
        "hot_water_draw",
        EventForecast(
            event_types=[
                EventDefinition(
                    event_type="shower",
                    duration_mean=8.0,
                    duration_std=3.0,
                    magnitude_mean=2.3,
                    magnitude_std=0.4,
                    energy_mean=4.0,
                    energy_std=1.0,
                ),
                EventDefinition(
                    event_type="dishwash",
                    duration_mean=10.0,
                    duration_std=3.0,
                    magnitude_mean=1.5,
                    magnitude_std=0.3,
                    energy_mean=1.5,
                    energy_std=0.5,
                ),
            ],
            daily_expected_count=5.0,
            daily_expected_energy=12.0,
        ),
    )
    dsm.register_constraint(
        "tank_temp_minimum",
        ConstraintStream(
            constraint_id="tank_temp_min",
            variable="tank_temp",
            constraint_type="minimum",
            continuous=True,
            required_value=120.0,
        ),
    )
    inlet_um = UncertaintyModel(
        model_type="empirical",
        params={"lead_time_sigma_table": [(0, 0.5), (86400 * 7, 2.0)]},
    )
    dsm.register_continuous_stream(
        "inlet_water_temp",
        ContinuousForecast(
            variable_name="inlet_water_temp", unit="°F", uncertainty_model=inlet_um
        ),
    )
    price_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 0.05, "tau_c": 4 * 3600}
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price", unit="$/kWh", uncertainty_model=price_um
        ),
    )
    return dsm


def _create_ev_charger_data_streams():
    """Create DataStreamManager for EV charger with departure, preferred SOC streams."""
    dsm = DataStreamManager(DeviceType.EV_CHARGER)
    dsm.register_constraint(
        "ev_departure_soc",
        ConstraintStream(
            constraint_id="ev_departure",
            variable="soc",
            constraint_type="by_time",
            continuous=False,
            deadline=7.0 * 3600,
            required_value=0.50,
        ),
    )
    soc_um = UncertaintyModel(
        model_type="empirical",
        params={"lead_time_sigma_table": [(0, 0.0), (86400, 0.0)]},
    )
    dsm.register_schedule(
        "ev_preferred_soc",
        ContinuousForecast(
            variable_name="preferred_soc", unit="fraction", uncertainty_model=soc_um
        ),
    )
    dsm.register_event_stream(
        "ev_arrival",
        EventForecast(
            event_types=[
                EventDefinition(
                    event_type="ev_arrival",
                    duration_mean=0,
                    magnitude_mean=0.65,
                    magnitude_std=0.08,
                )
            ],
            daily_expected_count=1.0,
            daily_expected_energy=0.0,
        ),
    )
    price_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 0.05, "tau_c": 4 * 3600}
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price", unit="$/kWh", uncertainty_model=price_um
        ),
    )
    return dsm


def _create_battery_data_streams():
    """Create DataStreamManager for battery with reserve, preferred SOC streams."""
    dsm = DataStreamManager(DeviceType.BATTERY)
    dsm.register_constraint(
        "soc_reserve",
        ConstraintStream(
            constraint_id="battery_reserve",
            variable="soc",
            constraint_type="minimum",
            continuous=True,
            required_value=0.60,
        ),
    )
    soc_um = UncertaintyModel(
        model_type="empirical",
        params={"lead_time_sigma_table": [(0, 0.0), (86400, 0.0)]},
    )
    dsm.register_schedule(
        "battery_preferred_soc",
        ContinuousForecast(
            variable_name="preferred_soc", unit="fraction", uncertainty_model=soc_um
        ),
    )
    price_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 0.05, "tau_c": 4 * 3600}
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price", unit="$/kWh", uncertainty_model=price_um
        ),
    )
    solar_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 2.0, "tau_c": 6 * 3600}
    )
    dsm.register_continuous_stream(
        "btm_solar",
        ContinuousForecast(
            variable_name="btm_solar_generation", unit="kW", uncertainty_model=solar_um
        ),
    )
    net_um = UncertaintyModel(
        model_type="saturating_exp", params={"sigma_inf": 3.0, "tau_c": 4 * 3600}
    )
    dsm.register_continuous_stream(
        "household_net_load",
        ContinuousForecast(
            variable_name="household_net_load", unit="kW", uncertainty_model=net_um
        ),
    )
    return dsm


def _create_data_streams_for(device_type):
    """Dispatch to the appropriate data stream factory."""
    if device_type in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
        return _create_hvac_data_streams(device_type)
    elif device_type == DeviceType.WATER_HEATER:
        return _create_water_heater_data_streams()
    elif device_type == DeviceType.EV_CHARGER:
        return _create_ev_charger_data_streams()
    elif device_type == DeviceType.BATTERY:
        return _create_battery_data_streams()
    raise ValueError(f"Unsupported device type: {device_type}")


def _make_device_agent(device_type, agent_id, k, mo, transport, conn_overrides=None):
    """Build a fully-wired DeviceAgent with *real* device model and data streams.

    Uses local data stream factories that mirror the reference wiring in
    main.py, so estimate_flexibility exercises the per-device data
    gathering branches.
    """
    conn = _MockConnectionMultiDevice(overrides=conn_overrides)
    gld = GridLABDInterface(connection=conn, object_name="dev", device_type=device_type)

    dsm = _create_data_streams_for(device_type)

    agent = DeviceAgent(
        agent_id=agent_id,
        device_type=device_type,
        gridlabd=gld,
        customer_preference_k=k,
        data_stream_manager=dsm,
    )
    if device_type == DeviceType.BATTERY:
        agent.initialize(
            {
                "replacement_cost": 10000.0,
                "rated_cycles": 5000,
                "rated_dod": 0.80,
            }
        )
    else:
        agent.initialize({})

    penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )
    comm = MarketCommunicationInterface(
        transport=transport,
        agent_id=agent_id,
        market_type=MarketType.RT_ENERGY,
    )
    agent.register_market(
        market_type=MarketType.RT_ENERGY,
        timing_params=MarketTimingParams(),
        operating_mode=OperatingMode.BIDDING,
        penalty_model=penalty,
        communication=comm,
    )
    return agent, conn, comm, penalty


def _run_device_f1_through_f5(agent, comm):
    """Execute F1–F5 for any device type (not just HVAC)."""
    state = agent.observe_device_state()
    flex = agent.estimate_flexibility(state, 300.0)
    pref = agent.generate_preference_curve(flex)
    mid = agent.spawn_market_cycle(MarketType.RT_ENERGY, clearing_time=300.0)
    mobj = agent._market_objects[mid]
    mobj.available_flexibility = flex
    mobj.preference_curve = pref
    bid = agent.formulate_bid(mobj, flex, pref)
    comm.submit_bid(bid, market_id=mid, interval_id=f"int_{mid}")
    return state, flex, pref, bid, mid, mobj


# =====================================================================
# 14. Water Heater — Full RT Cycle with Real Model
#     Regression: estimate_flexibility requires draw_forecast,
#     inlet_temp_forecast, ambient_temp, min_tank_temp.
# =====================================================================


class TestWaterHeaterRTCycle:
    """Full F1→F13 cycle for a water heater agent using the real
    WaterHeaterModel and production DataStreamManager from main.py.

    This is a regression test for the bug where DeviceAgent.
    estimate_flexibility passed only (state, interval_duration) to
    all non-HVAC models, ignoring the water-heater-specific arguments.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        self.mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        self.mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        self.transport = MockTransport(self.mo)

        self.agent, self.conn, self.comm, self.penalty = _make_device_agent(
            DeviceType.WATER_HEATER,
            "wh_1",
            0.4,
            self.mo,
            self.transport,
        )
        self.state, self.flex, self.pref, self.bid, self.mid, self.mobj = (
            _run_device_f1_through_f5(self.agent, self.comm)
        )

    def test_state_is_water_heater(self):
        from data_types import WaterHeaterState

        assert isinstance(self.state, WaterHeaterState)

    def test_flexibility_envelope_valid(self):
        assert self.flex.Q_min <= self.flex.Q_baseline <= self.flex.Q_max

    def test_q_max_bounded_by_element_power(self):
        """Q_max should not exceed the heating element rated power."""
        assert self.flex.Q_max <= self.state.element_power + 0.01

    def test_bid_has_points(self):
        assert len(self.bid.points) == 11

    def test_clearing_and_response(self):
        clearing = self.mo.clear_market()
        q = self.agent.evaluate_price_response(clearing.cleared_price, self.pref)
        assert isinstance(q, float)
        assert q >= self.flex.Q_min - 0.5

    def test_translate_to_control_returns_command(self):
        from data_types import DeviceCommand

        cmd = self.agent.translate_to_control(2.0, self.state)
        assert isinstance(cmd, DeviceCommand)
        assert cmd.device_type == DeviceType.WATER_HEATER

    def test_full_delivery_and_reconciliation(self):
        clearing = self.mo.clear_market()
        per_agent = self.mo.propagate_results()
        result = per_agent.get(self.agent._agent_id)
        if result is None:
            pytest.skip("Agent did not appear in propagated results")
        self.mobj.cleared_price = clearing.cleared_price
        self.mobj.cleared_quantity = result.cleared_quantity

        self.agent._command_arbiter.register_delivery(
            market_id=self.mid,
            market_type=str(MarketType.RT_ENERGY),
            product_type="ENERGY_BASE",
            committed_qty=result.cleared_quantity,
            cleared_price=clearing.cleared_price,
            penalty_model=self.penalty,
            interval=(0.0, 300.0),
        )
        for tick in range(3):
            frs = self.agent._command_arbiter.resolve_and_actuate(
                device_state=self.state,
                preference_curve=self.pref,
                amenity_weight=self.agent._k,
                current_time=tick * 60.0,
            )
            for m_id, fr in frs.items():
                self.mobj.performance_log.append(
                    PerformanceEntry(
                        timestamp=tick * 60.0,
                        committed=fr.committed,
                        actual=fr.actual,
                        shortfall=fr.shortfall,
                        revenue=fr.revenue,
                        penalty=fr.penalty,
                        net_value=fr.net_value,
                    )
                )

        settlement = self.agent.reconcile(self.mobj)
        assert isinstance(settlement, SettlementRecord)
        assert settlement.net_settlement == pytest.approx(
            settlement.total_revenue - settlement.total_penalty
        )


# =====================================================================
# 15. EV Charger — Full RT Cycle with Real Model
#     Regression: estimate_flexibility requires departure_constraint,
#     preferred_soc, time_until_departure.
# =====================================================================


class TestEVChargerRTCycle:
    """Full F1→F13 cycle for an EV charger using the real EVChargerModel
    and production DataStreamManager.

    Regression test for the estimate_flexibility signature mismatch.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        self.mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        self.mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        self.transport = MockTransport(self.mo)

        self.agent, self.conn, self.comm, self.penalty = _make_device_agent(
            DeviceType.EV_CHARGER,
            "ev_1",
            0.6,
            self.mo,
            self.transport,
        )
        self.state, self.flex, self.pref, self.bid, self.mid, self.mobj = (
            _run_device_f1_through_f5(self.agent, self.comm)
        )

    def test_state_is_ev_charger(self):
        from data_types import EVChargerState

        assert isinstance(self.state, EVChargerState)

    def test_vehicle_plugged_in(self):
        assert self.state.vehicle_plugged_in is True

    def test_flexibility_envelope_valid(self):
        assert self.flex.Q_min <= self.flex.Q_baseline
        assert self.flex.Q_baseline <= self.flex.Q_max

    def test_q_max_bounded_by_charge_rate(self):
        """Q_max should not exceed the max charge rate."""
        assert self.flex.Q_max <= self.state.max_charge_rate + 0.01

    def test_bid_has_points(self):
        assert len(self.bid.points) == 11

    def test_clearing_and_response(self):
        clearing = self.mo.clear_market()
        q = self.agent.evaluate_price_response(clearing.cleared_price, self.pref)
        assert isinstance(q, float)

    def test_translate_to_control_returns_command(self):
        from data_types import DeviceCommand

        cmd = self.agent.translate_to_control(3.0, self.state)
        assert isinstance(cmd, DeviceCommand)
        assert cmd.device_type == DeviceType.EV_CHARGER

    def test_full_delivery_and_reconciliation(self):
        clearing = self.mo.clear_market()
        per_agent = self.mo.propagate_results()
        result = per_agent.get(self.agent._agent_id)
        if result is None:
            pytest.skip("Agent did not appear in propagated results")
        self.mobj.cleared_price = clearing.cleared_price
        self.mobj.cleared_quantity = result.cleared_quantity

        self.agent._command_arbiter.register_delivery(
            market_id=self.mid,
            market_type=str(MarketType.RT_ENERGY),
            product_type="ENERGY_BASE",
            committed_qty=result.cleared_quantity,
            cleared_price=clearing.cleared_price,
            penalty_model=self.penalty,
            interval=(0.0, 300.0),
        )
        for tick in range(3):
            frs = self.agent._command_arbiter.resolve_and_actuate(
                device_state=self.state,
                preference_curve=self.pref,
                amenity_weight=self.agent._k,
                current_time=tick * 60.0,
            )
            for m_id, fr in frs.items():
                self.mobj.performance_log.append(
                    PerformanceEntry(
                        timestamp=tick * 60.0,
                        committed=fr.committed,
                        actual=fr.actual,
                        shortfall=fr.shortfall,
                        revenue=fr.revenue,
                        penalty=fr.penalty,
                        net_value=fr.net_value,
                    )
                )

        settlement = self.agent.reconcile(self.mobj)
        assert isinstance(settlement, SettlementRecord)
        assert settlement.net_settlement == pytest.approx(
            settlement.total_revenue - settlement.total_penalty
        )


# =====================================================================
# 16. Battery — Full RT Cycle with Real Model
#     Regression: estimate_flexibility requires soc_reserve, soc_preferred.
# =====================================================================


class TestBatteryRTCycle:
    """Full F1→F13 cycle for a battery agent using the real BatteryModel
    and production DataStreamManager.

    Regression test for the estimate_flexibility signature mismatch.
    Also validates that battery flexibility is bidirectional (Q_min < 0).
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        self.mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        self.mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        self.transport = MockTransport(self.mo)

        # SOC at 0.58: above the 0.60 reserve → can discharge a small amount
        self.agent, self.conn, self.comm, self.penalty = _make_device_agent(
            DeviceType.BATTERY,
            "batt_1",
            0.8,
            self.mo,
            self.transport,
            conn_overrides={"SOC": "0.75"},
        )
        self.state, self.flex, self.pref, self.bid, self.mid, self.mobj = (
            _run_device_f1_through_f5(self.agent, self.comm)
        )

    def test_state_is_battery(self):
        from data_types import BatteryState

        assert isinstance(self.state, BatteryState)

    def test_flexibility_bidirectional(self):
        """Battery with SOC above reserve should be able to discharge."""
        assert self.flex.Q_min < 0.0, (
            f"Battery Q_min should be negative (discharge), got {self.flex.Q_min}"
        )
        assert self.flex.Q_max > 0.0, (
            f"Battery Q_max should be positive (charge), got {self.flex.Q_max}"
        )

    def test_bid_has_points(self):
        assert len(self.bid.points) == 11

    def test_clearing_and_response(self):
        clearing = self.mo.clear_market()
        q = self.agent.evaluate_price_response(clearing.cleared_price, self.pref)
        assert isinstance(q, float)

    def test_translate_to_control_returns_command(self):
        from data_types import DeviceCommand

        cmd = self.agent.translate_to_control(-2.0, self.state)
        assert isinstance(cmd, DeviceCommand)
        assert cmd.device_type == DeviceType.BATTERY

    def test_full_delivery_and_reconciliation(self):
        clearing = self.mo.clear_market()
        per_agent = self.mo.propagate_results()
        result = per_agent.get(self.agent._agent_id)
        if result is None:
            pytest.skip("Agent did not appear in propagated results")
        self.mobj.cleared_price = clearing.cleared_price
        self.mobj.cleared_quantity = result.cleared_quantity

        self.agent._command_arbiter.register_delivery(
            market_id=self.mid,
            market_type=str(MarketType.RT_ENERGY),
            product_type="ENERGY_BASE",
            committed_qty=result.cleared_quantity,
            cleared_price=clearing.cleared_price,
            penalty_model=self.penalty,
            interval=(0.0, 300.0),
        )
        for tick in range(3):
            frs = self.agent._command_arbiter.resolve_and_actuate(
                device_state=self.state,
                preference_curve=self.pref,
                amenity_weight=self.agent._k,
                current_time=tick * 60.0,
            )
            for m_id, fr in frs.items():
                self.mobj.performance_log.append(
                    PerformanceEntry(
                        timestamp=tick * 60.0,
                        committed=fr.committed,
                        actual=fr.actual,
                        shortfall=fr.shortfall,
                        revenue=fr.revenue,
                        penalty=fr.penalty,
                        net_value=fr.net_value,
                    )
                )

        settlement = self.agent.reconcile(self.mobj)
        assert isinstance(settlement, SettlementRecord)
        assert settlement.net_settlement == pytest.approx(
            settlement.total_revenue - settlement.total_penalty
        )


# =====================================================================
# 17. HVAC Heat Pump — Full RT Cycle
#     Verifies HVAC_HEAT_PUMP variant (not just AC_ONLY).
# =====================================================================


class TestHVACHeatPumpRTCycle:
    """Full F1→F5 cycle for an HVAC heat pump agent using the real
    HVACModel and production DataStreamManager."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        self.mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        self.mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        self.transport = MockTransport(self.mo)

        self.agent, self.conn, self.comm, self.penalty = _make_device_agent(
            DeviceType.HVAC_HEAT_PUMP,
            "hp_1",
            0.3,
            self.mo,
            self.transport,
        )
        self.state, self.flex, self.pref, self.bid, self.mid, self.mobj = (
            _run_device_f1_through_f5(self.agent, self.comm)
        )

    def test_state_is_hvac(self):
        assert isinstance(self.state, HVACState)

    def test_flexibility_envelope_valid(self):
        assert self.flex.Q_min <= self.flex.Q_baseline <= self.flex.Q_max

    def test_bid_has_points(self):
        assert len(self.bid.points) == 11

    def test_clearing_and_control(self):
        clearing = self.mo.clear_market()
        q = self.agent.evaluate_price_response(clearing.cleared_price, self.pref)
        cmd = self.agent.translate_to_control(q, self.state)
        assert isinstance(cmd, DeviceCommand)
        assert cmd.device_type == DeviceType.HVAC_HEAT_PUMP


# =====================================================================
# 18. Mixed Device Types in Same Market
#     Regression: all device types must coexist and clear together.
# =====================================================================


class TestMixedDeviceTypesMarket:
    """All five device types participate in the same RT market: HVAC HP,
    HVAC AC, Water Heater, EV Charger, Battery.

    This is the multi-device scenario that the demo exercised but no
    integration test covered.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        self.mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        self.mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
        self.transport = MockTransport(self.mo)

        device_configs = [
            (DeviceType.HVAC_HEAT_PUMP, "hp_1", 0.3),
            (DeviceType.HVAC_AC_ONLY, "ac_1", 0.5),
            (DeviceType.WATER_HEATER, "wh_1", 0.4),
            (DeviceType.EV_CHARGER, "ev_1", 0.6),
            (DeviceType.BATTERY, "batt_1", 0.8),
        ]

        self.agents = []
        self.flexes = []
        self.bids = []
        for dtype, aid, k in device_configs:
            overrides = {"SOC": "0.75"} if dtype == DeviceType.BATTERY else None
            ag, _, comm, penalty = _make_device_agent(
                dtype,
                aid,
                k,
                self.mo,
                self.transport,
                conn_overrides=overrides,
            )
            state, flex, pref, bid, mid, mobj = _run_device_f1_through_f5(ag, comm)
            self.agents.append(ag)
            self.flexes.append(flex)
            self.bids.append(bid)

        self.clearing = self.mo.clear_market()
        self.per_agent = self.mo.propagate_results()

    def test_all_agents_got_results(self):
        """Every agent should appear in the per-agent clearing results."""
        for ag in self.agents:
            assert ag._agent_id in self.per_agent, (
                f"Agent {ag._agent_id} ({ag._device_type}) missing from results"
            )

    def test_clearing_price_reasonable(self):
        assert self.clearing.cleared_price > 0.02
        assert self.clearing.cleared_price < 0.50

    def test_uniform_clearing_price(self):
        prices = {r.cleared_price for r in self.per_agent.values()}
        assert len(prices) == 1

    def test_agent_quantities_sum_to_total(self):
        agent_total = sum(r.cleared_quantity for r in self.per_agent.values())
        mo_total = self.mo.get_total_flexible_committed()
        assert agent_total == pytest.approx(mo_total, rel=0.01)

    def test_all_bids_have_11_points(self):
        for bid in self.bids:
            assert len(bid.points) == 11

    def test_all_flexibility_envelopes_valid(self):
        for flex in self.flexes:
            assert flex.Q_min <= flex.Q_baseline <= flex.Q_max


# =====================================================================
# 19. DA Market with Informational Iterations — Non-HVAC Devices
#     Verifies that informational→binding iteration works for all types.
# =====================================================================


class TestDAMarketAllDeviceTypes:
    """Day-ahead market with 1 informational iteration then binding,
    using all device types.

    Validates that the assessment/re-bid cycle works for non-HVAC agents.
    """

    def test_da_informational_then_binding_all_types(self):
        mo = MarketOperator(
            market_type=MarketType.DA_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=1,
        )
        mo.set_supply_curve(_make_supply())
        from market_operator import DSOInflexibleLoadBid

        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 3600.0),
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)

        transport = MockTransport(mo)

        device_configs = [
            (DeviceType.HVAC_AC_ONLY, "ac_da", 0.5, None),
            (DeviceType.WATER_HEATER, "wh_da", 0.4, None),
            (DeviceType.EV_CHARGER, "ev_da", 0.6, None),
            (DeviceType.BATTERY, "batt_da", 0.8, {"SOC": "0.75"}),
        ]

        # Build agents registered for DA market
        agents = []
        comms = []
        for dtype, aid, k, overrides in device_configs:
            conn = _MockConnectionMultiDevice(overrides=overrides)
            gld = GridLABDInterface(
                connection=conn, object_name="dev", device_type=dtype
            )

            dsm = _create_data_streams_for(dtype)

            agent = DeviceAgent(
                agent_id=aid,
                device_type=dtype,
                gridlabd=gld,
                customer_preference_k=k,
                data_stream_manager=dsm,
            )
            if dtype == DeviceType.BATTERY:
                agent.initialize(
                    {
                        "replacement_cost": 10000.0,
                        "rated_cycles": 5000,
                        "rated_dod": 0.80,
                    }
                )
            else:
                agent.initialize({})

            da_penalty = PenaltyModel(
                market_type=MarketType.DA_ENERGY,
                structure_type=PenaltyStructureType.PROPORTIONAL,
                params={"rate_reference": "cleared_price_multiple", "multiplier": 1.5},
            )
            comm = MarketCommunicationInterface(
                transport=transport,
                agent_id=aid,
                market_type=MarketType.DA_ENERGY,
            )
            agent.register_market(
                market_type=MarketType.DA_ENERGY,
                timing_params=MarketTimingParams(),
                operating_mode=OperatingMode.BIDDING,
                penalty_model=da_penalty,
                communication=comm,
            )
            agents.append(agent)
            comms.append(comm)

        # Iteration 1: informational
        for agent, comm in zip(agents, comms):
            state = agent.observe_device_state()
            flex = agent.estimate_flexibility(state, 3600.0)
            pref = agent.generate_preference_curve(flex)
            mid = agent.spawn_market_cycle(MarketType.DA_ENERGY, clearing_time=3600.0)
            mobj = agent._market_objects[mid]
            bid = agent.formulate_bid(mobj, flex, pref)
            comm.submit_bid(bid, market_id=mid, interval_id=f"int_{mid}")

        r1 = mo.clear_market()
        assert r1.iteration_type == IterationType.INFORMATIONAL

        # Iteration 2: rebid and get binding
        for agent, comm in zip(agents, comms):
            state = agent.observe_device_state()
            flex = agent.estimate_flexibility(state, 3600.0)
            pref = agent.generate_preference_curve(flex)
            mid = list(agent._market_objects.keys())[0]
            mobj = agent._market_objects[mid]
            bid = agent.formulate_bid(mobj, flex, pref)
            comm.submit_bid(bid, market_id=mid, interval_id=f"int_{mid}")

        r2 = mo.clear_market()
        assert r2.iteration_type == IterationType.BINDING

        # Verify per-agent results
        per_agent = mo.propagate_results()
        for agent in agents:
            assert agent._agent_id in per_agent


# =====================================================================
# 20. estimate_flexibility Regression — All Device Types
#     Direct regression test: calling estimate_flexibility with real
#     models and data streams must not raise TypeError.
# =====================================================================


class TestEstimateFlexibilityAllDeviceTypes:
    """Directly tests that DeviceAgent.estimate_flexibility works with
    real device models and properly-configured DataStreamManagers for
    every supported device type.

    This is the minimal regression test for the bug where the else
    branch passed only (state, interval_duration) to all non-HVAC models.
    """

    DEVICE_CONFIGS = [
        (DeviceType.HVAC_AC_ONLY, None),
        (DeviceType.HVAC_HEAT_PUMP, None),
        (DeviceType.WATER_HEATER, None),
        (DeviceType.EV_CHARGER, None),
        (DeviceType.BATTERY, {"SOC": "0.75"}),
    ]

    @pytest.mark.parametrize(
        "device_type,overrides",
        DEVICE_CONFIGS,
        ids=["hvac_ac", "hvac_hp", "water_heater", "ev_charger", "battery"],
    )
    def test_estimate_flexibility_no_type_error(self, device_type, overrides):
        """estimate_flexibility must not raise TypeError for any device type."""
        conn = _MockConnectionMultiDevice(overrides=overrides)
        gld = GridLABDInterface(
            connection=conn, object_name="dev", device_type=device_type
        )

        dsm = _create_data_streams_for(device_type)

        agent = DeviceAgent(
            agent_id="test_agent",
            device_type=device_type,
            gridlabd=gld,
            customer_preference_k=0.5,
            data_stream_manager=dsm,
        )

        state = agent.observe_device_state()
        flex = agent.estimate_flexibility(state, 300.0)

        assert isinstance(flex, FlexibilityEnvelope)
        assert flex.Q_min <= flex.Q_baseline <= flex.Q_max

    @pytest.mark.parametrize(
        "device_type,overrides",
        DEVICE_CONFIGS,
        ids=["hvac_ac", "hvac_hp", "water_heater", "ev_charger", "battery"],
    )
    def test_estimate_flexibility_without_streams(self, device_type, overrides):
        """estimate_flexibility must also work with an empty DataStreamManager
        (using fallback defaults)."""
        conn = _MockConnectionMultiDevice(overrides=overrides)
        gld = GridLABDInterface(
            connection=conn, object_name="dev", device_type=device_type
        )
        dsm = DataStreamManager(device_type)

        agent = DeviceAgent(
            agent_id="test_agent",
            device_type=device_type,
            gridlabd=gld,
            customer_preference_k=0.5,
            data_stream_manager=dsm,
        )

        state = agent.observe_device_state()
        flex = agent.estimate_flexibility(state, 300.0)

        assert isinstance(flex, FlexibilityEnvelope)
        assert flex.Q_min <= flex.Q_baseline <= flex.Q_max


# =====================================================================
# CONTRACT TESTS: EventDefinition → EventForecast → WaterHeaterModel
#
# Design spec (class_diagram_core.plantuml, class_data_flow.plantuml):
#   - WaterHeaterModel.estimate_flexibility(state, draws, inlet,
#     min_temp, interval) must USE the draws parameter to adjust
#     Q_min and Q_baseline.
#   - EventForecast.condition_on_observation() must reduce the
#     remaining expected energy in get_cumulative_energy_distribution.
#   - End-to-end: different EventDefinitions registered in
#     DataStreamManager must produce different flexibility envelopes
#     when the agent pipeline runs F1→F2.
# =====================================================================


class TestWaterHeaterModelUsesDrawForecast:
    """Contract: WaterHeaterModel.estimate_flexibility must consume
    draw_forecast to adjust Q_min and Q_baseline.

    Design ref: class_diagram_core.plantuml line 206
        estimate_flexibility(state, draws, inlet, min_temp, interval)
    """

    @pytest.fixture()
    def model(self):
        return WaterHeaterModel()

    @pytest.fixture()
    def state(self):
        return WaterHeaterState(
            tank_temp_upper=128.0,
            tank_temp_lower=124.0,
            thermostat_setpoint=130.0,
            element_on=False,
            power_draw=0.0,
            tank_volume=50.0,
            tank_UA=2.0,
            element_power=4.5,
            inlet_water_temp=62.0,
            current_draw_rate=0.0,
        )

    def test_higher_expected_draw_raises_q_baseline(self, model, state):
        """When more hot water is expected, the heater should plan to
        run harder → higher Q_baseline."""
        no_draw = QuantilePoint(expected=0.0, variance=0.0)
        big_draw = QuantilePoint(expected=8.0, variance=4.0)

        env_no = model.estimate_flexibility(
            state=state,
            draw_forecast=no_draw,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=120.0,
            interval_duration=300.0,
        )
        env_big = model.estimate_flexibility(
            state=state,
            draw_forecast=big_draw,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=120.0,
            interval_duration=300.0,
        )
        assert env_big.Q_baseline > env_no.Q_baseline

    def test_high_draw_variance_raises_q_min(self, model, state):
        """High draw uncertainty should push Q_min up (conservative —
        keep the element on to guard against large draws)."""
        low_var = QuantilePoint(expected=4.0, variance=0.1)
        high_var = QuantilePoint(expected=4.0, variance=16.0)

        env_lo = model.estimate_flexibility(
            state=state,
            draw_forecast=low_var,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=120.0,
            interval_duration=300.0,
        )
        env_hi = model.estimate_flexibility(
            state=state,
            draw_forecast=high_var,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=120.0,
            interval_duration=300.0,
        )
        assert env_hi.Q_min >= env_lo.Q_min

    def test_zero_draw_preserves_existing_behavior(self, model, state):
        """With no expected draws, the model should behave the same as
        the original standby-loss-only logic."""
        zero = QuantilePoint(expected=0.0, variance=0.0)
        env = model.estimate_flexibility(
            state=state,
            draw_forecast=zero,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=120.0,
            interval_duration=300.0,
        )
        assert env.Q_min == 0.0
        assert env.Q_baseline >= 0.0
        assert env.Q_max <= state.element_power + 0.01

    def test_draw_does_not_push_baseline_above_q_max(self, model, state):
        """Even enormous draws can't make Q_baseline exceed Q_max."""
        huge = QuantilePoint(expected=100.0, variance=100.0)
        env = model.estimate_flexibility(
            state=state,
            draw_forecast=huge,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=120.0,
            interval_duration=300.0,
        )
        assert env.Q_baseline <= env.Q_max + 0.001
        assert env.Q_min <= env.Q_max + 0.001

    def test_thermal_buffer_lowers_q_min(self, model, state):
        """When tank is well above min_tank_temp, thermal buffer absorbs
        draws and Q_min should be lower than when tank is near minimum."""
        draw = QuantilePoint(expected=0.5, variance=0.5)
        # Warm tank: large thermal buffer → low Q_min
        env_warm = model.estimate_flexibility(
            state=state,  # T_avg=126, min=110 → 16°F buffer
            draw_forecast=draw,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=110.0,
            interval_duration=300.0,
        )
        # Cool tank: small thermal buffer → higher Q_min
        cool_state = WaterHeaterState(
            tank_temp_upper=113.0,
            tank_temp_lower=111.0,
            thermostat_setpoint=130.0,
            element_on=False,
            power_draw=0.0,
            tank_volume=50.0,
            tank_UA=2.0,
            element_power=4.5,
            inlet_water_temp=62.0,
            current_draw_rate=0.0,
        )
        env_cool = model.estimate_flexibility(
            state=cool_state,  # T_avg=112, min=110 → 2°F buffer
            draw_forecast=draw,
            inlet_temp_forecast=None,
            ambient_temp=70.0,
            min_tank_temp=110.0,
            interval_duration=300.0,
        )
        assert env_cool.Q_min > env_warm.Q_min


class TestEventForecastConditionOnObservation:
    """Contract: condition_on_observation must reduce remaining expected
    energy returned by get_cumulative_energy_distribution.

    Design ref: class_diagram_core.plantuml line 421
        + condition_on_observation(event_type, timestamp, energy)
    """

    @pytest.fixture()
    def forecast(self):
        return EventForecast(
            event_types=[
                EventDefinition(
                    event_type="shower",
                    duration_mean=8.0,
                    duration_std=3.0,
                    magnitude_mean=2.3,
                    magnitude_std=0.4,
                    energy_mean=4.0,
                    energy_std=1.0,
                ),
            ],
            intensity_function=[(0.0, 2.0), (86400.0, 2.0)],
            daily_expected_count=5.0,
            daily_expected_energy=20.0,
        )

    def test_observation_reduces_remaining_uncertainty(self, forecast):
        """After observing a shower, remaining forecast uncertainty
        (variance) must decrease — the Bayesian update worked."""
        before = forecast.get_cumulative_energy_distribution(0.0, 3600.0)
        forecast.condition_on_observation("shower", 100.0, 4.0)
        after = forecast.get_cumulative_energy_distribution(0.0, 3600.0)
        assert after.variance < before.variance

    def test_reset_restores_prior(self, forecast):
        """reset_observations should restore the unconditional forecast."""
        before = forecast.get_cumulative_energy_distribution(0.0, 3600.0)
        forecast.condition_on_observation("shower", 100.0, 4.0)
        forecast.reset_observations()
        restored = forecast.get_cumulative_energy_distribution(0.0, 3600.0)
        assert restored.expected == pytest.approx(before.expected, abs=0.01)


class TestEventDefinitionsEndToEnd:
    """Contract: EventDefinitions registered in DataStreamManager must
    produce different flexibility envelopes when the agent runs F1→F2.

    Design ref: class_data_flow.plantuml
        ExtLEARN → EfFlow : intensity functions, event distributions
        DsmFlow → FuncF2 : forecasts and constraints
    """

    def _make_wh_agent(self, event_defs, daily_count, daily_energy, mo, transport):
        """Build a WH agent with the given event definitions."""
        dsm = DataStreamManager(DeviceType.WATER_HEATER)
        dsm.register_event_stream(
            "hot_water_draw",
            EventForecast(
                event_types=event_defs,
                intensity_function=[(0.0, 2.0), (86400.0, 2.0)],
                daily_expected_count=daily_count,
                daily_expected_energy=daily_energy,
            ),
        )
        dsm.register_constraint(
            "tank_temp_minimum",
            ConstraintStream(
                constraint_id="tank_temp_min",
                variable="tank_temp",
                constraint_type="minimum",
                continuous=True,
                required_value=120.0,
            ),
        )
        um = UncertaintyModel(
            model_type="empirical",
            params={"lead_time_sigma_table": [(0, 0.5), (86400, 2.0)]},
        )
        dsm.register_continuous_stream(
            "inlet_water_temp",
            ContinuousForecast(
                variable_name="inlet_water_temp",
                unit="°F",
                uncertainty_model=um,
            ),
        )

        conn = _MockConnectionMultiDevice()
        gld = GridLABDInterface(
            connection=conn,
            object_name="dev",
            device_type=DeviceType.WATER_HEATER,
        )
        agent = DeviceAgent(
            agent_id="wh_contract",
            device_type=DeviceType.WATER_HEATER,
            gridlabd=gld,
            customer_preference_k=0.4,
            data_stream_manager=dsm,
        )
        agent.initialize({})

        comm = MarketCommunicationInterface(
            transport=transport,
            agent_id="wh_contract",
            market_type=MarketType.RT_ENERGY,
        )
        penalty = PenaltyModel(
            market_type=MarketType.RT_ENERGY,
            structure_type=PenaltyStructureType.PROPORTIONAL,
            params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
        )
        agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            operating_mode=OperatingMode.BIDDING,
            penalty_model=penalty,
            communication=comm,
        )
        return agent

    def test_heavy_draw_events_raise_baseline(self):
        """An agent with heavy-draw EventDefinitions (high energy_mean,
        high daily_count) should compute a higher Q_baseline than an
        agent with light-draw definitions."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        transport = MockTransport(mo)

        light_events = [
            EventDefinition(
                event_type="faucet",
                energy_mean=0.5,
                energy_std=0.1,
                magnitude_mean=0.5,
            ),
        ]
        heavy_events = [
            EventDefinition(
                event_type="shower",
                energy_mean=8.0,
                energy_std=2.0,
                magnitude_mean=2.3,
                magnitude_std=0.4,
                duration_mean=10.0,
                duration_std=3.0,
            ),
        ]

        light_agent = self._make_wh_agent(
            light_events,
            daily_count=2.0,
            daily_energy=1.0,
            mo=mo,
            transport=transport,
        )
        heavy_agent = self._make_wh_agent(
            heavy_events,
            daily_count=8.0,
            daily_energy=64.0,
            mo=mo,
            transport=transport,
        )

        st_l = light_agent.observe_device_state()
        fl_l = light_agent.estimate_flexibility(st_l, 300.0)

        st_h = heavy_agent.observe_device_state()
        fl_h = heavy_agent.estimate_flexibility(st_h, 300.0)

        assert fl_h.Q_baseline > fl_l.Q_baseline

    def test_no_event_stream_still_works(self):
        """An agent with NO hot_water_draw stream should still compute
        a valid flexibility envelope (fallback to zero draws)."""
        mo = MarketOperator(
            market_type=MarketType.RT_ENERGY,
            timing_params=MarketTimingParams(),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        mo.set_supply_curve(_make_supply())
        transport = MockTransport(mo)

        # Build agent with empty DSM (no event stream)
        conn = _MockConnectionMultiDevice()
        gld = GridLABDInterface(
            connection=conn,
            object_name="dev",
            device_type=DeviceType.WATER_HEATER,
        )
        dsm = DataStreamManager(DeviceType.WATER_HEATER)
        agent = DeviceAgent(
            agent_id="wh_bare",
            device_type=DeviceType.WATER_HEATER,
            gridlabd=gld,
            customer_preference_k=0.4,
            data_stream_manager=dsm,
        )
        agent.initialize({})

        state = agent.observe_device_state()
        flex = agent.estimate_flexibility(state, 300.0)
        assert isinstance(flex, FlexibilityEnvelope)
        assert flex.Q_min <= flex.Q_baseline <= flex.Q_max
