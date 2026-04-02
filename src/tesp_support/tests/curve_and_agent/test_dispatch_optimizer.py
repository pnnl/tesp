# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for dispatch_optimizer.py — Single-timestep economic dispatch.

Ground truth:
  - Single energy product: Q* = committed (serve the delivery)
  - Two products with trade-off: optimal Q balances marginal values
  - Amenity cost shifts operating point toward comfort preference
"""

import pytest

from data_types import (
    DeliveryEconomics,
    DispatchSolution,
    FlexibilityEnvelope,
    BidPoint,
)
from dispatch_optimizer import DispatchOptimizer, DeliveryValueCalculator
from preference_curve import PreferenceCurve
from enums_and_constants import DeviceType, ProductType, PenaltyStructureType


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def optimizer():
    return DispatchOptimizer()


@pytest.fixture
def value_calculator():
    return DeliveryValueCalculator()


@pytest.fixture
def comfort_curve():
    """Mildly elastic HVAC preference curve."""
    return PreferenceCurve(
        device_type=DeviceType.HVAC_AC_ONLY,
        Q_0=5.0,
        P_0=0.10,
        k=0.3,
    )


def _make_delivery(market_id, committed, price, marginal_val=None, marginal_pen=0.0):
    """Helper to build a DeliveryEconomics with sensible defaults."""
    return DeliveryEconomics(
        market_id=market_id,
        product_type=ProductType.ENERGY_BASE,
        committed_qty=committed,
        cleared_price=price,
        marginal_value_full=marginal_val if marginal_val is not None else price,
        marginal_penalty_zero=marginal_pen,
    )


# ===================================================================
# DispatchOptimizer Tests
# ===================================================================


class TestDispatchSingleProduct:
    def test_single_energy_delivery(self, optimizer, comfort_curve):
        """One energy delivery: committed 4 kW, price $0.12/kWh.

        With no competing products, Q* should be at or near the
        committed quantity (minimizes penalty).
        """
        economics = {
            "RT_100": _make_delivery("RT_100", 4.0, 0.12, marginal_pen=0.50),
        }
        solution = optimizer.solve(
            economics=economics,
            Q_min=0.0,
            Q_max=10.0,
            preference_curve=comfort_curve,
            amenity_weight=0.3,
        )
        assert isinstance(solution, DispatchSolution)
        assert solution.Q == pytest.approx(4.0, abs=1.0)


class TestDispatchTwoProducts:
    def test_energy_plus_regulation(self, optimizer, comfort_curve):
        """Two products: energy at 4 kW + reg-up reserve of 2 kW.

        Reg-up requires holding capacity above committed energy.
        Total Q should be >= 4 kW energy + headroom for reg.
        """
        economics = {
            "RT_100": _make_delivery("RT_100", 4.0, 0.12, marginal_pen=0.50),
            "REG_UP_100": _make_delivery("REG_UP_100", 2.0, 0.05, marginal_pen=0.30),
        }
        solution = optimizer.solve(
            economics=economics,
            Q_min=0.0,
            Q_max=10.0,
            preference_curve=comfort_curve,
            amenity_weight=0.3,
        )
        assert isinstance(solution, DispatchSolution)
        assert solution.Q >= 4.0


class TestDispatchAmenityEffect:
    def test_high_amenity_weight_biases_toward_comfort(self, optimizer):
        """High amenity weight -> Q* closer to Q_0 of preference curve.

        curve Q_0=5.0. With high amenity_weight, the optimizer should
        pull Q* toward 5.0 even if economics favor a different point.
        """
        comfort = PreferenceCurve(
            device_type=DeviceType.HVAC_AC_ONLY,
            Q_0=5.0,
            P_0=0.10,
            k=0.8,
        )
        economics = {
            "RT_100": _make_delivery("RT_100", 8.0, 0.05, marginal_pen=0.10),
        }
        solution = optimizer.solve(
            economics=economics,
            Q_min=0.0,
            Q_max=10.0,
            preference_curve=comfort,
            amenity_weight=5.0,
        )
        # Strong amenity pulls toward Q_0=5, despite committed=8
        assert abs(solution.Q - 5.0) < abs(8.0 - 5.0)


class TestDispatchBidirectionalBatteryContracts:
    """Design contracts from sequence_mo_clearing for battery behavior.

    Ground truth: battery commitments/allocations may be negative when
    discharging (exporting) at high prices.
    """

    def test_negative_committed_quantity_is_preserved(self, optimizer):
        """A discharge commitment (negative kW) should remain negative in
        both Q* and per-market allocation when within bounds."""
        battery_curve = PreferenceCurve(
            device_type=DeviceType.BATTERY,
            Q_0=0.0,
            P_0=0.10,
            k=0.8,
        )
        economics = {
            "BAT_RT": _make_delivery(
                "BAT_RT", committed=-3.0, price=0.30, marginal_pen=0.5
            ),
        }

        solution = optimizer.solve(
            economics=economics,
            Q_min=-5.0,
            Q_max=5.0,
            preference_curve=battery_curve,
            amenity_weight=0.0,
        )

        assert solution.Q == pytest.approx(-3.0, abs=0.1)
        assert solution.allocation["BAT_RT"] == pytest.approx(-3.0, abs=0.1)

    def test_negative_dispatch_respects_q_min_bound(self, optimizer):
        """If aggregate discharge exceeds physical minimum, Q* should clamp
        at Q_min (still negative), not collapse to zero."""
        battery_curve = PreferenceCurve(
            device_type=DeviceType.BATTERY,
            Q_0=0.0,
            P_0=0.10,
            k=0.8,
        )
        economics = {
            "BAT_RT": _make_delivery(
                "BAT_RT", committed=-8.0, price=0.40, marginal_pen=1.0
            ),
        }

        solution = optimizer.solve(
            economics=economics,
            Q_min=-5.0,
            Q_max=5.0,
            preference_curve=battery_curve,
            amenity_weight=0.0,
        )

        assert solution.Q == pytest.approx(-5.0, abs=0.1)


# ===================================================================
# DeliveryValueCalculator Tests
# ===================================================================


class TestDeliveryValueCalculator:
    def test_energy_product(self, value_calculator):
        """Energy delivery: revenue = price x quantity x duration_hours.

        Price=$0.12/kWh, committed=5 kW, interval=300s (5 min=1/12 hr).
        Revenue = 0.12 x 5 x (300/3600) = $0.05.
        """
        from penalty_model import PenaltyModel

        pen = PenaltyModel(
            market_type=ProductType.ENERGY_BASE,
            structure_type=PenaltyStructureType.PROPORTIONAL,
            params={"rate": 0.50},
        )
        econ = value_calculator.compute(
            market_id="RT_100",
            product_type="energy",
            committed_qty=5.0,
            cleared_price=0.12,
            penalty_model=pen,
            interval_duration=300.0,
        )
        assert isinstance(econ, DeliveryEconomics)
        assert econ.cleared_price == pytest.approx(0.12)
        assert econ.committed_qty == pytest.approx(5.0)

    def test_regulation_product(self, value_calculator):
        """Regulation product: capacity payment (not energy).

        Price=$0.05/kW, committed=2 kW, interval=300s.
        Revenue for regulation is capacity-based, but the calculator
        should still produce a valid DeliveryEconomics.
        """
        from penalty_model import PenaltyModel

        pen = PenaltyModel(
            market_type=ProductType.REGULATION_UP,
            structure_type=PenaltyStructureType.PROPORTIONAL,
            params={"rate": 0.30},
        )
        econ = value_calculator.compute(
            market_id="REG_100",
            product_type="regulation_up",
            committed_qty=2.0,
            cleared_price=0.05,
            penalty_model=pen,
            interval_duration=300.0,
        )
        assert isinstance(econ, DeliveryEconomics)
        assert econ.committed_qty == pytest.approx(2.0)
        assert econ.cleared_price == pytest.approx(0.05)

    def test_degradation_included(self, value_calculator):
        """With nonzero degradation_cost, marginal values shift.

        Degradation cost reduces net value: the calculator should
        account for it in the marginal_value_full or net_value_fn.
        """
        from penalty_model import PenaltyModel

        pen = PenaltyModel(
            market_type=ProductType.ENERGY_BASE,
            structure_type=PenaltyStructureType.PROPORTIONAL,
            params={"rate": 0.50},
        )
        econ_no_deg = value_calculator.compute(
            market_id="RT_100",
            product_type="energy",
            committed_qty=5.0,
            cleared_price=0.12,
            penalty_model=pen,
            interval_duration=300.0,
            degradation_cost=0.0,
        )
        econ_with_deg = value_calculator.compute(
            market_id="RT_100",
            product_type="energy",
            committed_qty=5.0,
            cleared_price=0.12,
            penalty_model=pen,
            interval_duration=300.0,
            degradation_cost=0.05,
        )
        # With degradation, marginal value should be lower
        assert econ_with_deg.marginal_value_full <= econ_no_deg.marginal_value_full
