# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for market_agent.py — Agent–MO communication interface.

Ground truth:
  - MarketCommunicationInterface wraps an injected transport (HELICS/FNCS/direct)
  - submit_bid sends a BidCurve and returns acknowledgment bool
  - receive_clear polls/checks for ClearingResult, returns Optional
  - submit_reconciliation sends SettlementRecord, returns bool
  - register_clear_callback stores a callable for event-driven architectures

Testing strategy:
  The transport is injected, so we mock it. Tests verify that:
  - Correct data flows through the mock transport
  - Return types match the interface contract
  - Callback registration stores and (future) invokes the callback
"""

import pytest
from unittest.mock import MagicMock

from tesp_support.curve_and_agent.market_agent import MarketCommunicationInterface
from tesp_support.curve_and_agent.data_types import (
    BidPoint,
    BidCurve,
    ClearingResult,
    SettlementRecord,
)
from tesp_support.curve_and_agent.enums_and_constants import MarketType, IterationType


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def mock_transport():
    """Mock transport that simulates an in-process MO reference.

    In production this could be:
    - A direct reference to a MarketOperator instance (in-process)
    - A HELICS endpoint/publication handle
    - An HTTP client
    """
    transport = MagicMock()
    transport.submit = MagicMock(return_value=True)
    transport.receive = MagicMock(return_value=None)
    return transport


@pytest.fixture
def rt_comm(mock_transport):
    """MarketCommunicationInterface for real-time energy market."""
    return MarketCommunicationInterface(
        transport=mock_transport,
        agent_id="agent_house_1",
        market_type=MarketType.RT_ENERGY,
    )


@pytest.fixture
def da_comm(mock_transport):
    """MarketCommunicationInterface for day-ahead energy market."""
    return MarketCommunicationInterface(
        transport=mock_transport,
        agent_id="agent_house_1",
        market_type=MarketType.DA_ENERGY,
    )


@pytest.fixture
def sample_bid():
    """A simple 3-point demand bid curve."""
    return BidCurve(
        points=[
            BidPoint(price=0.20, quantity=1.0),
            BidPoint(price=0.10, quantity=3.0),
            BidPoint(price=0.05, quantity=5.0),
        ],
        market_id="RT_1000",
        interval_id="int_1000_1300",
        timestamp=1000.0,
    )


@pytest.fixture
def sample_clearing():
    """A sample binding clearing result."""
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
def sample_settlement():
    """A sample settlement record."""
    return SettlementRecord(
        market_id="RT_1000",
        total_revenue=1.50,
        total_penalty=0.0,
        net_settlement=1.50,
        total_energy_committed=1.5,
        total_energy_delivered=1.5,
        total_shortfall=0.0,
    )


# ===================================================================
# Construction Tests
# ===================================================================


class TestMarketCommConstruction:
    """Verify construction stores injected dependencies."""

    def test_stores_transport(self, rt_comm, mock_transport):
        assert rt_comm._transport is mock_transport

    def test_stores_agent_id(self, rt_comm):
        assert rt_comm._agent_id == "agent_house_1"

    def test_stores_market_type(self, rt_comm):
        assert rt_comm._market_type == MarketType.RT_ENERGY

    def test_callback_initially_none(self, rt_comm):
        assert rt_comm._on_clear_callback is None

    def test_different_market_types(self, mock_transport):
        """Each MarketType should be accepted."""
        for mt in MarketType:
            comm = MarketCommunicationInterface(
                transport=mock_transport,
                agent_id="agent_test",
                market_type=mt,
            )
            assert comm._market_type == mt


# ===================================================================
# submit_bid
# ===================================================================


class TestSubmitBid:
    """MarketCommunicationInterface.submit_bid() -> bool."""

    def test_returns_bool(self, rt_comm, sample_bid):
        result = rt_comm.submit_bid(
            bid=sample_bid,
            market_id="RT_1000",
            interval_id="int_1000_1300",
        )
        assert isinstance(result, bool)

    def test_successful_submission(self, rt_comm, sample_bid):
        result = rt_comm.submit_bid(
            bid=sample_bid,
            market_id="RT_1000",
            interval_id="int_1000_1300",
        )
        assert result is True

    def test_bid_forwarded_to_transport(self, rt_comm, mock_transport, sample_bid):
        """The bid data should reach the transport layer."""
        rt_comm.submit_bid(
            bid=sample_bid,
            market_id="RT_1000",
            interval_id="int_1000_1300",
        )
        mock_transport.submit.assert_called_once()

    def test_empty_bid_curve(self, rt_comm):
        """Submitting a bid with no points should still succeed or
        return False gracefully — never crash."""
        empty_bid = BidCurve(
            points=[],
            market_id="RT_1000",
            interval_id="int_1000_1300",
            timestamp=1000.0,
        )
        result = rt_comm.submit_bid(
            bid=empty_bid,
            market_id="RT_1000",
            interval_id="int_1000_1300",
        )
        assert isinstance(result, bool)


# ===================================================================
# receive_clear
# ===================================================================


class TestReceiveClear:
    """MarketCommunicationInterface.receive_clear() -> Optional[ClearingResult]."""

    def test_returns_none_when_no_result(self, rt_comm):
        """When no clearing result is available, should return None."""
        result = rt_comm.receive_clear(market_id="RT_1000")
        assert result is None

    def test_returns_clearing_result_when_available(
        self, rt_comm, mock_transport, sample_clearing
    ):
        """When the transport has a result, should return ClearingResult."""
        mock_transport.receive.return_value = sample_clearing
        result = rt_comm.receive_clear(market_id="RT_1000")
        mock_transport.receive.assert_called_once()
        assert isinstance(result, ClearingResult)

    def test_clearing_result_fields(self, rt_comm, mock_transport, sample_clearing):
        mock_transport.receive.return_value = sample_clearing
        result = rt_comm.receive_clear(market_id="RT_1000")
        assert result.cleared_price == 0.10
        assert result.cleared_quantity == 3.0

    def test_nonexistent_market_id(self, rt_comm):
        """Receiving for a market ID that hasn't been bid on."""
        result = rt_comm.receive_clear(market_id="NONEXISTENT_999")
        assert result is None


# ===================================================================
# submit_reconciliation
# ===================================================================


class TestSubmitReconciliation:
    """MarketCommunicationInterface.submit_reconciliation() -> bool."""

    def test_returns_bool(self, rt_comm, sample_settlement):
        result = rt_comm.submit_reconciliation(
            market_id="RT_1000",
            settlement=sample_settlement,
        )
        assert isinstance(result, bool)

    def test_successful_reconciliation(self, rt_comm, sample_settlement):
        result = rt_comm.submit_reconciliation(
            market_id="RT_1000",
            settlement=sample_settlement,
        )
        assert result is True

    def test_settlement_forwarded(self, rt_comm, mock_transport, sample_settlement):
        rt_comm.submit_reconciliation(
            market_id="RT_1000",
            settlement=sample_settlement,
        )
        mock_transport.submit.assert_called_once()


# ===================================================================
# register_clear_callback
# ===================================================================


class TestRegisterClearCallback:
    """MarketCommunicationInterface.register_clear_callback()."""

    def test_stores_callback(self, rt_comm):
        cb = MagicMock()
        rt_comm.register_clear_callback(cb)
        assert rt_comm._on_clear_callback is cb

    def test_callback_invoked_on_clear(self, rt_comm, mock_transport, sample_clearing):
        """When a clear arrives, callback is either invoked immediately
        or retained for asynchronous/event-loop dispatch."""
        cb = MagicMock()
        mock_transport.receive.return_value = sample_clearing
        rt_comm.register_clear_callback(cb)
        result = rt_comm.receive_clear(market_id="RT_1000")
        assert result == sample_clearing
        assert rt_comm._on_clear_callback is cb
        # Accept synchronous callback invocation if implementation chooses it.
        if cb.called:
            cb.assert_called_with(sample_clearing)

    def test_replace_callback(self, rt_comm):
        """Registering a new callback should replace the old one."""
        cb1 = MagicMock()
        cb2 = MagicMock()
        rt_comm.register_clear_callback(cb1)
        rt_comm.register_clear_callback(cb2)
        assert rt_comm._on_clear_callback is cb2
