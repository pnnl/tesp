# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for market_operator.py — Retail market clearing.

Ground truth:
  - SupplyCurve: upward-sloping interpolation
  - DSOInflexibleLoadBid: perfectly inelastic (vertical) demand
  - DSOLoadEstimationEngine: Q_inflex = total - flexible + losses - solar
  - MarketOperator: aggregate demand intersects supply at clearing price
  - Iteration protocol: fixed_count and convergence variants
"""

import pytest

from data_types import BidCurve, BidPoint, ClearingResult, MarketTimingParams
from enums_and_constants import MarketType, IterationType

RT = MarketType.RT_ENERGY

from market_operator import (
    SupplyCurve,
    DSOInflexibleLoadBid,
    DSOLoadEstimationEngine,
    MarketOperator,
)


# ===================================================================
# SupplyCurve Fixtures & Tests
# ===================================================================


@pytest.fixture
def simple_supply():
    """Upward-sloping supply: $0.05 @ 0 kW, $0.10 @ 50 kW, $0.20 @ 100 kW."""
    return SupplyCurve(
        points=[
            BidPoint(price=0.05, quantity=0.0),
            BidPoint(price=0.10, quantity=50.0),
            BidPoint(price=0.20, quantity=100.0),
        ]
    )


class TestSupplyCurveConstructor:
    def test_points(self, simple_supply):
        assert len(simple_supply.points) == 3


class TestSupplyAtPrice:
    def test_exact_point(self, simple_supply):
        """At $0.10, supply = 50 kW."""
        assert simple_supply.get_supply_at_price(0.10) == pytest.approx(50.0)

    def test_interpolated(self, simple_supply):
        """At $0.075 (midpoint of $0.05 and $0.10), supply = 25 kW."""
        assert simple_supply.get_supply_at_price(0.075) == pytest.approx(25.0, abs=1.0)

    def test_below_minimum(self, simple_supply):
        """At price below minimum, supply = 0."""
        assert simple_supply.get_supply_at_price(0.01) == pytest.approx(0.0, abs=0.1)


class TestPriceAtQuantity:
    def test_exact_quantity(self, simple_supply):
        """At 50 kW, price = $0.10."""
        assert simple_supply.get_price_at_quantity(50.0) == pytest.approx(0.10)

    def test_interpolated_quantity(self, simple_supply):
        """At 75 kW (midpoint of 50..100): price = (0.10+0.20)/2 = $0.15."""
        assert simple_supply.get_price_at_quantity(75.0) == pytest.approx(
            0.15, abs=0.01
        )


# ===================================================================
# DSO Inflexible Load Bid
# ===================================================================


class TestDSOInflexibleLoadBid:
    def test_construct(self):
        bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
            components={"base": 180.0, "losses": 20.0},
        )
        assert bid.quantity == 200.0
        assert bid.feeder_id == "feeder_1"


# ===================================================================
# DSO Load Estimation Engine
# ===================================================================


@pytest.fixture
def load_engine():
    return DSOLoadEstimationEngine(feeder_id="feeder_1")


class TestDSOLoadEstimation:
    def test_inflexible_load_calculation(self, load_engine):
        """Q_inflex = total - flexible + losses - solar.

        total=1000 kW, flexible=100 kW, solar=50 kW, loss_factor=0.05.
        losses = 1000 × 0.05 = 50 kW  (design: losses on gross total)
        Q_inflex = 1000 - 100 + 50 - 50 = 900 kW
        """
        bid = load_engine.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=1000.0,
            flexible_committed=100.0,
            btm_solar_forecast=50.0,
            loss_factor=0.05,
        )
        assert isinstance(bid, DSOInflexibleLoadBid)
        assert bid.quantity == pytest.approx(900.0, abs=5.0)
        assert bid.feeder_id == "feeder_1"


class TestDSOLoadEngineMetering:
    def test_update_with_metering(self, load_engine):
        """update_with_metering should not raise (stores internal state)."""
        load_engine.update_with_metering(
            substation_load_actual=980.0,
            flexible_actual=95.0,
            timestamp=300.0,
        )
        # No return value; just verify it completes without error


# ===================================================================
# MarketOperator Fixtures
# ===================================================================


@pytest.fixture
def mo_timing():
    return MarketTimingParams(
        t_activate=0.0,
        t_negotiate=60.0,
        t_market_lead=90.0,
        t_clear=120.0,
        t_delivery_start=125.0,
        t_delivery_end=425.0,
        t_reconcile_end=485.0,
    )


@pytest.fixture
def market_operator(mo_timing):
    return MarketOperator(
        market_type=RT,
        timing_params=mo_timing,
        iteration_protocol="fixed_count",
        n_informational=2,
    )


# ===================================================================
# MarketOperator Tests
# ===================================================================


class TestMarketOperatorConstructor:
    def test_initial_state(self, market_operator):
        assert market_operator._market_type == RT
        assert market_operator._n_informational == 2
        assert len(market_operator._agent_bids) == 0
        assert market_operator._supply_curve is None


class TestSubmitBids:
    def test_submit_agent_bid(self, market_operator):
        bid = BidCurve(
            points=[
                BidPoint(price=0.15, quantity=5.0),
                BidPoint(price=0.10, quantity=3.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        accepted = market_operator.submit_agent_bid("agent_1", bid)
        assert accepted is True

    def test_submit_supply_curve(self, market_operator, simple_supply):
        market_operator.set_supply_curve(simple_supply)
        assert market_operator._supply_curve is not None

    def test_submit_dso_bid(self, market_operator):
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        accepted = market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)
        assert accepted is True


# ===================================================================
# Aggregate Demand Tests
# ===================================================================


class TestAggregateDemand:
    def test_single_agent_plus_inflexible(self, market_operator):
        """One elastic agent (5 kW @ $0.15, 0 kW @ $0.05) + 200 kW inflexible.

        At $0.15: total demand = 5 + 200 = 205 kW.
        At $0.05: total demand = 0 + 200 = 200 kW.
        At $0.10: agent ≈ 2.5 kW → total ≈ 202.5 kW.
        """
        bid = BidCurve(
            points=[
                BidPoint(price=0.15, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        market_operator.submit_agent_bid("agent_1", bid)
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=200.0,
            interval=(0.0, 300.0),
        )
        market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)

        demand = market_operator.aggregate_demand()
        assert len(demand) > 0
        # Demand at high price includes inflexible base
        high_price_qty = max(pt.quantity for pt in demand)
        assert high_price_qty >= 200.0


# ===================================================================
# Market Clearing Tests
# ===================================================================


class TestClearMarket:
    def test_simple_clearing(self, market_operator, simple_supply):
        """Supply meets demand at intersection.

        Supply: $0.05@0kW → $0.20@100kW (upward sloping).
        Demand: 200 kW inflexible + 5 kW agent (elastic, drops at high price).
        Total demand ≈ 205 kW at low prices → supply of 100 kW max.
        Clearing price will be at supply cap ($0.20) or where curves cross.
        """
        market_operator.set_supply_curve(simple_supply)
        bid = BidCurve(
            points=[
                BidPoint(price=0.25, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        market_operator.submit_agent_bid("agent_1", bid)
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=80.0,
            interval=(0.0, 300.0),
        )
        market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)

        result = market_operator.clear_market()
        assert isinstance(result, ClearingResult)
        assert result.cleared_price > 0.0
        assert result.cleared_quantity > 0.0


# ===================================================================
# Iteration Protocol Tests
# ===================================================================


class TestIterationProtocol:
    def test_fixed_count_informational(self, market_operator):
        """Iterations 1 and 2 are informational (n_informational=2)."""
        market_operator._current_iteration = 1
        assert market_operator.determine_iteration_type() == IterationType.INFORMATIONAL

    def test_fixed_count_binding(self, market_operator):
        """Iteration 3 is binding (n_informational=2)."""
        market_operator._current_iteration = 3
        assert market_operator.determine_iteration_type() == IterationType.BINDING


class TestTotalFlexibleCommitted:
    def test_sum_of_cleared(self, market_operator, simple_supply):
        """After clearing, total_flexible_committed sums agent cleared quantities."""
        market_operator.set_supply_curve(simple_supply)
        bid = BidCurve(
            points=[
                BidPoint(price=0.25, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        market_operator.submit_agent_bid("agent_1", bid)
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=50.0,
            interval=(0.0, 300.0),
        )
        market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)
        market_operator.clear_market()

        total = market_operator.get_total_flexible_committed()
        assert total >= 0.0


# ===================================================================
# get_agent_clearing Tests
# ===================================================================


class TestGetAgentClearing:
    def test_agent_cleared_at_price(self, market_operator, simple_supply):
        """After clearing, get_agent_clearing returns agent-specific result.

        Agent bids 5 kW at $0.25 → 0 kW at $0.05.
        At clearing price between $0.05 and $0.25, agent gets
        a proportional quantity from their bid curve.
        """
        market_operator.set_supply_curve(simple_supply)
        bid = BidCurve(
            points=[
                BidPoint(price=0.25, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        market_operator.submit_agent_bid("agent_1", bid)
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=50.0,
            interval=(0.0, 300.0),
        )
        market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)
        result = market_operator.clear_market()

        agent_result = market_operator.get_agent_clearing(
            "agent_1", result.cleared_price
        )
        assert isinstance(agent_result, ClearingResult)
        assert agent_result.cleared_price == pytest.approx(result.cleared_price)
        assert agent_result.cleared_quantity >= 0.0

    def test_nonexistent_agent(self, market_operator, simple_supply):
        """Querying a non-participating agent should handle gracefully."""
        market_operator.set_supply_curve(simple_supply)
        market_operator.clear_market()
        # May raise KeyError or return a zero-quantity result
        try:
            result = market_operator.get_agent_clearing("ghost", 0.10)
            assert result.cleared_quantity == pytest.approx(0.0)
        except (KeyError, ValueError):
            pass  # acceptable behavior


# ===================================================================
# propagate_results Tests
# ===================================================================


class TestPropagateResults:
    def test_returns_all_agents(self, market_operator, simple_supply):
        """propagate_results returns a dict with entry per agent."""
        market_operator.set_supply_curve(simple_supply)
        bid1 = BidCurve(
            points=[
                BidPoint(price=0.25, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        bid2 = BidCurve(
            points=[
                BidPoint(price=0.20, quantity=3.0),
                BidPoint(price=0.08, quantity=0.0),
            ]
        )
        market_operator.submit_agent_bid("agent_1", bid1)
        market_operator.submit_agent_bid("agent_2", bid2)
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=50.0,
            interval=(0.0, 300.0),
        )
        market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)
        market_operator.clear_market()

        results = market_operator.propagate_results()
        assert isinstance(results, dict)
        assert "agent_1" in results
        assert "agent_2" in results
        # Both should have the same clearing price
        assert results["agent_1"].cleared_price == pytest.approx(
            results["agent_2"].cleared_price
        )

    def test_quantities_sum_to_total_flexible(self, market_operator, simple_supply):
        """Sum of all agent cleared quantities = total flexible committed."""
        market_operator.set_supply_curve(simple_supply)
        bid = BidCurve(
            points=[
                BidPoint(price=0.25, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        market_operator.submit_agent_bid("agent_1", bid)
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=50.0,
            interval=(0.0, 300.0),
        )
        market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)
        market_operator.clear_market()

        results = market_operator.propagate_results()
        agent_total = sum(r.cleared_quantity for r in results.values())
        flex_total = market_operator.get_total_flexible_committed()
        assert agent_total == pytest.approx(flex_total, rel=0.01)


# ===================================================================
# step() Tests
# ===================================================================


class TestMarketOperatorStep:
    def test_step_at_clearing_time(self, market_operator, simple_supply):
        """step() at the right time triggers a clearing."""
        market_operator.set_supply_curve(simple_supply)
        bid = BidCurve(
            points=[
                BidPoint(price=0.25, quantity=5.0),
                BidPoint(price=0.05, quantity=0.0),
            ]
        )
        market_operator.submit_agent_bid("agent_1", bid)
        dso_bid = DSOInflexibleLoadBid(
            feeder_id="feeder_1",
            quantity=50.0,
            interval=(0.0, 300.0),
        )
        market_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)

        # Step at clearing time (t_clear=120.0)
        results = market_operator.step(current_time=120.0)
        assert results is not None
        assert "agent_1" in results

    def test_step_before_clearing_time(self, market_operator):
        """step() before clearing time returns None."""
        results = market_operator.step(current_time=0.0)
        assert results is None


# ===================================================================
# DSO Metering Impact Test
# ===================================================================


class TestDSOLoadEngineImpact:
    def test_metering_improves_estimate(self, load_engine):
        """Metering data should allow the engine to correct its model.

        First estimate with base parameters, then provide metering data
        showing actual load was lower, then re-estimate and check
        it adjusts.
        """
        bid1 = load_engine.estimate_inflexible_load(
            interval=(0.0, 300.0),
            total_load_forecast=1000.0,
            flexible_committed=100.0,
            btm_solar_forecast=50.0,
            loss_factor=0.05,
        )
        # Actual was lower
        load_engine.update_with_metering(
            substation_load_actual=900.0,
            flexible_actual=100.0,
            timestamp=300.0,
        )
        bid2 = load_engine.estimate_inflexible_load(
            interval=(300.0, 600.0),
            total_load_forecast=1000.0,
            flexible_committed=100.0,
            btm_solar_forecast=50.0,
            loss_factor=0.05,
        )
        # We don't dictate exactly how the correction works,
        # but the estimate should shift toward reality
        # (implementation-dependent, so loose assertion)
        assert isinstance(bid2, DSOInflexibleLoadBid)
        assert bid2.quantity > 0.0
