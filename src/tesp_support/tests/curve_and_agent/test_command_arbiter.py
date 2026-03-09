# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for command_arbiter.py — Multi-market delivery resolution.

Ground truth:
  - DeliveryRecord is a data holder for active delivery obligations
  - CommandArbiter merges simultaneous deliveries into one device command
  - register_delivery / deregister_delivery manage the active set
  - update_signals feeds real-time market signals (reg, reserve)
  - resolve_and_actuate is the core method:
      1. Build DeliveryEconomics for each active delivery
      2. Run DispatchOptimizer → single optimal Q
      3. Translate Q to DeviceCommand via device model
      4. Actuate via GridLABDInterface
      5. Return per-market FulfillmentRecords

Testing strategy:
  GridLABDInterface and device_model are injected — mock them.
  DispatchOptimizer and DeliveryValueCalculator are already implemented
  and tested, so we can use real instances or mocks depending on the test.
"""

import pytest
from unittest.mock import MagicMock, patch

from command_arbiter import CommandArbiter, DeliveryRecord
from data_types import (
    DeviceCommand,
    DispatchSolution,
    FulfillmentRecord,
    DeliveryEconomics,
    FlexibilityEnvelope,
    HVACState,
)
from dispatch_optimizer import DispatchOptimizer, DeliveryValueCalculator
from preference_curve import PreferenceCurve
from penalty_model import PenaltyModel
from enums_and_constants import (
    DeviceType,
    MarketType,
    ProductType,
    PenaltyStructureType,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def mock_gridlabd():
    """Mock GridLABDInterface — the single point of device actuation."""
    gld = MagicMock()
    gld.write_hvac_command = MagicMock(return_value=True)
    gld.write_water_heater_command = MagicMock(return_value=True)
    gld.write_ev_charger_command = MagicMock(return_value=True)
    gld.write_battery_command = MagicMock(return_value=True)
    return gld


@pytest.fixture
def mock_device_model():
    """Mock device model for control translation (F8)."""
    model = MagicMock()
    model.power_to_setpoint = MagicMock(return_value=74.0)
    envelope = FlexibilityEnvelope(Q_min=0.0, Q_max=10.0, Q_baseline=3.0)
    model.estimate_flexibility = MagicMock(return_value=envelope)
    return model


@pytest.fixture
def optimizer():
    return DispatchOptimizer()


@pytest.fixture
def value_calculator():
    return DeliveryValueCalculator()


@pytest.fixture
def arbiter(mock_gridlabd, mock_device_model, optimizer, value_calculator):
    """CommandArbiter wired up with mocks for HVAC."""
    return CommandArbiter(
        device_type=DeviceType.HVAC_AC_ONLY,
        gridlabd=mock_gridlabd,
        device_model=mock_device_model,
        optimizer=optimizer,
        value_calculator=value_calculator,
    )


@pytest.fixture
def proportional_penalty():
    return PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate": 0.05},
    )


@pytest.fixture
def comfort_curve():
    return PreferenceCurve(
        device_type=DeviceType.HVAC_AC_ONLY,
        Q_0=3.0,
        P_0=0.10,
        k=0.3,
    )


# ===================================================================
# DeliveryRecord Tests
# ===================================================================


class TestDeliveryRecord:
    """DeliveryRecord is a plain data holder — test construction."""

    def test_construction(self, proportional_penalty):
        rec = DeliveryRecord(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=5.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        assert rec.market_id == "RT_1000"
        assert rec.committed_qty == 5.0
        assert rec.cleared_price == 0.10
        assert rec.interval == (0.0, 300.0)

    def test_performance_log_initially_empty(self, proportional_penalty):
        rec = DeliveryRecord(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=5.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        assert rec.performance_log == []

    def test_penalty_model_reference(self, proportional_penalty):
        rec = DeliveryRecord(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=5.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        assert rec.penalty_model is proportional_penalty


# ===================================================================
# CommandArbiter Construction
# ===================================================================


class TestCommandArbiterConstruction:
    """Verify the arbiter stores injected dependencies."""

    def test_stores_device_type(self, arbiter):
        assert arbiter._device_type == DeviceType.HVAC_AC_ONLY

    def test_stores_gridlabd(self, arbiter, mock_gridlabd):
        assert arbiter._gridlabd is mock_gridlabd

    def test_stores_optimizer(self, arbiter, optimizer):
        assert arbiter._optimizer is optimizer

    def test_stores_value_calculator(self, arbiter, value_calculator):
        assert arbiter._value_calculator is value_calculator

    def test_active_deliveries_empty(self, arbiter):
        assert arbiter._active_deliveries == {}


# ===================================================================
# register_delivery
# ===================================================================


class TestRegisterDelivery:
    """CommandArbiter.register_delivery() adds a DeliveryRecord."""

    def test_adds_to_active_deliveries(self, arbiter, proportional_penalty):
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=5.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        assert "RT_1000" in arbiter._active_deliveries

    def test_delivery_record_fields(self, arbiter, proportional_penalty):
        arbiter.register_delivery(
            market_id="RT_2000",
            market_type="DA_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=3.0,
            cleared_price=0.08,
            penalty_model=proportional_penalty,
            interval=(100.0, 400.0),
        )
        rec = arbiter._active_deliveries["RT_2000"]
        assert rec.committed_qty == 3.0
        assert rec.cleared_price == 0.08
        assert rec.interval == (100.0, 400.0)

    def test_multiple_deliveries(self, arbiter, proportional_penalty):
        """Can register deliveries from multiple concurrent markets."""
        for i in range(3):
            arbiter.register_delivery(
                market_id=f"MKT_{i}",
                market_type="RT_ENERGY",
                product_type="ENERGY_BASE",
                committed_qty=2.0 + i,
                cleared_price=0.10,
                penalty_model=proportional_penalty,
                interval=(0.0, 300.0),
            )
        assert len(arbiter._active_deliveries) == 3

    def test_overwrite_existing_market_id(self, arbiter, proportional_penalty):
        """Re-registering the same market_id should overwrite."""
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=5.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=7.0,
            cleared_price=0.12,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        assert arbiter._active_deliveries["RT_1000"].committed_qty == 7.0


# ===================================================================
# deregister_delivery
# ===================================================================


class TestDeregisterDelivery:
    """CommandArbiter.deregister_delivery() removes a delivery."""

    def test_removes_from_active(self, arbiter, proportional_penalty):
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=5.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        arbiter.deregister_delivery("RT_1000")
        assert "RT_1000" not in arbiter._active_deliveries

    def test_deregister_nonexistent_is_safe(self, arbiter):
        """Deregistering a market_id that doesn't exist should not raise."""
        before = dict(arbiter._active_deliveries)
        arbiter.deregister_delivery("NONEXISTENT")
        assert arbiter._active_deliveries == before

    def test_only_removes_target(self, arbiter, proportional_penalty):
        """Deregistering one market should not affect others."""
        for mid in ["MKT_A", "MKT_B", "MKT_C"]:
            arbiter.register_delivery(
                market_id=mid,
                market_type="RT_ENERGY",
                product_type="ENERGY_BASE",
                committed_qty=3.0,
                cleared_price=0.10,
                penalty_model=proportional_penalty,
                interval=(0.0, 300.0),
            )
        arbiter.deregister_delivery("MKT_B")
        assert "MKT_A" in arbiter._active_deliveries
        assert "MKT_B" not in arbiter._active_deliveries
        assert "MKT_C" in arbiter._active_deliveries


# ===================================================================
# update_signals
# ===================================================================


class TestUpdateSignals:
    """CommandArbiter.update_signals() feeds real-time signals."""

    def test_accepts_regulation_signal(self, arbiter):
        result = arbiter.update_signals({"regulation_signal": 0.5})
        assert result is None

    def test_accepts_reserve_activation(self, arbiter):
        result = arbiter.update_signals({"reserve_activated": 1.0})
        assert result is None

    def test_accepts_multiple_signals(self, arbiter):
        result = arbiter.update_signals(
            {
                "regulation_signal": -0.3,
                "reserve_activated": 0.0,
            }
        )
        assert result is None

    def test_empty_signals_accepted(self, arbiter):
        """Empty dict should be a valid no-op."""
        result = arbiter.update_signals({})
        assert result is None


# ===================================================================
# resolve_and_actuate
# ===================================================================


class TestResolveAndActuate:
    """CommandArbiter.resolve_and_actuate() — the core dispatch path."""

    def test_returns_fulfillment_dict(
        self, arbiter, proportional_penalty, comfort_curve
    ):
        """Should return Dict[str, FulfillmentRecord]."""
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=3.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        result = arbiter.resolve_and_actuate(
            device_state=HVACState(),
            preference_curve=comfort_curve,
            amenity_weight=0.3,
            current_time=150.0,
        )
        assert isinstance(result, dict)
        assert "RT_1000" in result
        assert isinstance(result["RT_1000"], FulfillmentRecord)

    def test_single_delivery_full_fulfill(
        self, arbiter, proportional_penalty, comfort_curve
    ):
        """With only one active delivery, should fully fulfill it."""
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=3.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        result = arbiter.resolve_and_actuate(
            device_state=HVACState(),
            preference_curve=comfort_curve,
            amenity_weight=0.3,
            current_time=150.0,
        )
        rec = result["RT_1000"]
        assert rec.shortfall == pytest.approx(0.0, abs=0.5)

    def test_actuates_device(
        self, arbiter, mock_gridlabd, proportional_penalty, comfort_curve
    ):
        """resolve_and_actuate must call the GridLAB-D write method."""
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=3.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        arbiter.resolve_and_actuate(
            device_state=HVACState(),
            preference_curve=comfort_curve,
            amenity_weight=0.3,
            current_time=150.0,
        )
        assert mock_gridlabd.write_hvac_command.called

    def test_no_active_deliveries(self, arbiter, comfort_curve):
        """With no active deliveries, should return empty dict or
        device-only command based on preference curve."""
        result = arbiter.resolve_and_actuate(
            device_state=HVACState(),
            preference_curve=comfort_curve,
            amenity_weight=1.0,
            current_time=0.0,
        )
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_multiple_deliveries_allocation(
        self, arbiter, proportional_penalty, comfort_curve
    ):
        """With two concurrent deliveries, both get fulfillment records."""
        for mid, qty, price in [("MKT_A", 2.0, 0.10), ("MKT_B", 3.0, 0.15)]:
            arbiter.register_delivery(
                market_id=mid,
                market_type="RT_ENERGY",
                product_type="ENERGY_BASE",
                committed_qty=qty,
                cleared_price=price,
                penalty_model=proportional_penalty,
                interval=(0.0, 300.0),
            )
        result = arbiter.resolve_and_actuate(
            device_state=HVACState(),
            preference_curve=comfort_curve,
            amenity_weight=0.3,
            current_time=150.0,
        )
        assert "MKT_A" in result
        assert "MKT_B" in result

    def test_fulfillment_revenue_nonnegative(
        self, arbiter, proportional_penalty, comfort_curve
    ):
        """Revenue in each FulfillmentRecord should be >= 0."""
        arbiter.register_delivery(
            market_id="RT_1000",
            market_type="RT_ENERGY",
            product_type="ENERGY_BASE",
            committed_qty=3.0,
            cleared_price=0.10,
            penalty_model=proportional_penalty,
            interval=(0.0, 300.0),
        )
        result = arbiter.resolve_and_actuate(
            device_state=HVACState(),
            preference_curve=comfort_curve,
            amenity_weight=0.3,
            current_time=150.0,
        )
        assert result["RT_1000"].revenue >= 0
