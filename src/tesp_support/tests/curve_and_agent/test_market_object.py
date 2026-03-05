# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for market_object.py — Market state machine.

Ground truth for the 9-phase market lifecycle:
  INACTIVE → ACTIVE → NEGOTIATION → INFORMATIONAL_CLEAR →
  ASSESSMENT → [loop back to NEGOTIATION or forward to] →
  BINDING_CLEAR → DELIVERY_LEAD → DELIVERY → RECONCILE → EXPIRED

Key properties:
  - Only legal transitions are allowed
  - Informational loop: ASSESSMENT → NEGOTIATION (iterates)
  - Binding cuts the loop: ASSESSMENT → BINDING_CLEAR
  - Terminal state: EXPIRED (no transitions out)
"""

import pytest

from enums_and_constants import (
    MarketType,
    MarketPhase,
    OperatingMode,
    IterationType,
)
from data_types import (
    BidCurve,
    ClearingResult,
    MarketTimingParams,
    BidPoint,
)
from market_object import MarketObject

RT = MarketType.RT_ENERGY
DA = MarketType.DA_ENERGY


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def rt_timing():
    """Real-time market: 5-minute cycle."""
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
def rt_market(rt_timing):
    """A real-time energy market object."""
    return MarketObject(
        market_id="RT_1000",
        market_type=RT,
        timing_params=rt_timing,
        operating_mode=OperatingMode.BIDDING,
        iteration_protocol="mo_signaled",
    )


@pytest.fixture
def da_market_fixed_count(rt_timing):
    """DA market with fixed 3 informational iterations."""
    return MarketObject(
        market_id="DA_0",
        market_type=DA,
        timing_params=rt_timing,
        operating_mode=OperatingMode.BIDDING,
        iteration_protocol="fixed_count",
        n_informational_planned=3,
    )


# ===================================================================
# Constructor Tests
# ===================================================================


class TestMarketObjectConstructor:
    def test_initial_phase(self, rt_market):
        assert rt_market.current_phase == MarketPhase.INACTIVE

    def test_attributes(self, rt_market):
        assert rt_market.market_id == "RT_1000"
        assert rt_market.market_type == RT
        assert rt_market.operating_mode == OperatingMode.BIDDING
        assert rt_market.current_iteration == 0

    def test_empty_history(self, rt_market):
        assert rt_market.submitted_bid is None
        assert len(rt_market.advisory_history) == 0
        assert len(rt_market.performance_log) == 0


# ===================================================================
# State Machine Transition Tests
# ===================================================================


class TestLegalTransitions:
    """The canonical forward path through the state machine."""

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_inactive_to_active(self, rt_market):
        rt_market.transition_to(MarketPhase.ACTIVE)
        assert rt_market.current_phase == MarketPhase.ACTIVE

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_active_to_negotiation(self, rt_market):
        rt_market.transition_to(MarketPhase.ACTIVE)
        rt_market.transition_to(MarketPhase.NEGOTIATION)
        assert rt_market.current_phase == MarketPhase.NEGOTIATION

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_full_forward_path(self, rt_market):
        """Walk the entire non-looping path to EXPIRED."""
        phases = [
            MarketPhase.ACTIVE,
            MarketPhase.NEGOTIATION,
            MarketPhase.MARKET_LEAD,
            MarketPhase.ASSESSMENT,
            MarketPhase.DELIVERY_LEAD,
            MarketPhase.DELIVERY,
            MarketPhase.RECONCILE,
            MarketPhase.EXPIRED,
        ]
        for phase in phases:
            rt_market.transition_to(phase)
        assert rt_market.current_phase == MarketPhase.EXPIRED


class TestInformationalLoop:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_assessment_loops_to_negotiation(self, rt_market):
        """ASSESSMENT → NEGOTIATION is the informational loop-back."""
        rt_market.transition_to(MarketPhase.ACTIVE)
        rt_market.transition_to(MarketPhase.NEGOTIATION)
        rt_market.transition_to(MarketPhase.MARKET_LEAD)
        rt_market.transition_to(MarketPhase.ASSESSMENT)
        # Loop back for another informational round
        rt_market.transition_to(MarketPhase.NEGOTIATION)
        assert rt_market.current_phase == MarketPhase.NEGOTIATION


class TestIllegalTransitions:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_inactive_to_delivery(self, rt_market):
        """Cannot jump from INACTIVE to DELIVERY."""
        with pytest.raises(ValueError):
            rt_market.transition_to(MarketPhase.DELIVERY)

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_expired_to_anything(self, rt_market):
        """EXPIRED is terminal — no transitions out."""
        for phase in [
            MarketPhase.ACTIVE,
            MarketPhase.NEGOTIATION,
            MarketPhase.MARKET_LEAD,
            MarketPhase.ASSESSMENT,
            MarketPhase.DELIVERY_LEAD,
            MarketPhase.DELIVERY,
            MarketPhase.RECONCILE,
            MarketPhase.EXPIRED,
        ]:
            rt_market.transition_to(phase)

        with pytest.raises(ValueError):
            rt_market.transition_to(MarketPhase.ACTIVE)

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_active_to_delivery_lead(self, rt_market):
        """Cannot skip NEGOTIATION → MARKET_LEAD → ASSESSMENT."""
        rt_market.transition_to(MarketPhase.ACTIVE)
        with pytest.raises(ValueError):
            rt_market.transition_to(MarketPhase.DELIVERY_LEAD)


# ===================================================================
# Timing Tests
# ===================================================================


class TestGetNextEventTime:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_inactive_next_event(self, rt_market):
        """INACTIVE → next event is the market open time."""
        t = rt_market.get_next_event_time(current_time=900.0)
        assert t is not None
        assert isinstance(t, float)

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_expired_no_next(self, rt_market):
        """EXPIRED → returns None."""
        for phase in [
            MarketPhase.ACTIVE,
            MarketPhase.NEGOTIATION,
            MarketPhase.MARKET_LEAD,
            MarketPhase.ASSESSMENT,
            MarketPhase.DELIVERY_LEAD,
            MarketPhase.DELIVERY,
            MarketPhase.RECONCILE,
            MarketPhase.EXPIRED,
        ]:
            rt_market.transition_to(phase)
        assert rt_market.get_next_event_time(0.0) is None


# ===================================================================
# Iteration Protocol Tests
# ===================================================================


class TestIterationProtocol:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_mo_signaled_informational(self, rt_market):
        """MO-signaled: ClearingResult with INFORMATIONAL → is_informational=True."""
        result = ClearingResult(
            cleared_price=0.10,
            cleared_quantity=5.0,
            iteration_type=IterationType.INFORMATIONAL,
        )
        assert rt_market.is_informational_iteration(result) is True

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_mo_signaled_binding(self, rt_market):
        result = ClearingResult(
            cleared_price=0.12,
            cleared_quantity=5.0,
            iteration_type=IterationType.BINDING,
        )
        assert rt_market.is_informational_iteration(result) is False

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_fixed_count_first_n_informational(self, da_market_fixed_count):
        """Fixed count (n=3): iterations 1-3 are informational."""
        da_market_fixed_count.current_iteration = 2
        result = ClearingResult(
            cleared_price=0.10,
            cleared_quantity=5.0,
            iteration_type=IterationType.INFORMATIONAL,  # ignored for fixed_count
        )
        assert da_market_fixed_count.is_informational_iteration(result) is True

    @pytest.mark.xfail(raises=NotImplementedError)
    def test_fixed_count_last_is_binding(self, da_market_fixed_count):
        """Fixed count (n=3): iteration 4 is binding."""
        da_market_fixed_count.current_iteration = 4
        result = ClearingResult(
            cleared_price=0.10,
            cleared_quantity=5.0,
            iteration_type=IterationType.INFORMATIONAL,
        )
        assert da_market_fixed_count.is_informational_iteration(result) is False
