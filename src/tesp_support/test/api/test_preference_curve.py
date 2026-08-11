# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for preference_curve.py — Level 2 leaf logic.

Defines hand-calculated ground truth for the isoelastic demand curve.
All method tests are xfail(raises=NotImplementedError) until
PreferenceCurve methods are implemented.

Mathematics reference
---------------------
Standard devices (load-only):
    Q(P) = Q_0 · (P / P_0)^{-ε}
    where ε = k · ε_max  (linear mapping assumed)

Battery (bidirectional sigmoid):
    Q(P) = Q_charge_max · (1 - (P/P_threshold)^ε) / (1 + (P/P_threshold)^ε)
    crosses Q=0 at P = P_threshold
    P_threshold ≈ P_0 + degradation_cost (charge side)
                ≈ P_0 - degradation_cost (discharge side)

Amenity cost:
    Proportional to (Q_actual - Q_preferred)^2, scaled inversely by k.
"""

import pytest

from tesp_support.api.preference_curve import PreferenceCurve, DeviceType


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def inelastic_curve():
    """k=0: perfectly inelastic customer (ε ≈ 0). Tracks amenity."""
    return PreferenceCurve(
        k=0.0,
        P_0=0.10,
        Q_0=5.0,
        epsilon_max=5.0,
        device_type=DeviceType.HVAC_AC_ONLY,
    )


@pytest.fixture
def elastic_curve():
    """k=1: maximally elastic customer (ε = ε_max = 5). Aggressive price response."""
    return PreferenceCurve(
        k=1.0,
        P_0=0.10,
        Q_0=5.0,
        epsilon_max=5.0,
        device_type=DeviceType.HVAC_AC_ONLY,
    )


@pytest.fixture
def mid_curve():
    """k=0.5: middle-of-the-road customer (ε = 2.5)."""
    return PreferenceCurve(
        k=0.5,
        P_0=0.10,
        Q_0=5.0,
        epsilon_max=5.0,
        device_type=DeviceType.HVAC_AC_ONLY,
    )


@pytest.fixture
def battery_curve():
    """Battery curve with charge/discharge capability."""
    return PreferenceCurve(
        k=0.5,
        P_0=0.10,
        Q_0=5.0,
        epsilon_max=5.0,
        device_type=DeviceType.BATTERY,
        Q_discharge_max=-5.0,
        degradation_cost=0.02,
    )


# ===================================================================
# Constructor Tests (should pass — constructors work)
# ===================================================================


class TestPreferenceCurveConstructor:
    def test_construct_standard(self, inelastic_curve):
        assert inelastic_curve._k == 0.0
        assert inelastic_curve._P_0 == 0.10
        assert inelastic_curve._Q_0 == 5.0

    def test_construct_battery(self, battery_curve):
        assert battery_curve._device_type == DeviceType.BATTERY
        assert battery_curve._Q_discharge_max == -5.0
        assert battery_curve._degradation_cost == 0.02


# ===================================================================
# Elasticity ε(k) Tests
# ===================================================================


class TestEpsilon:
    def test_epsilon_at_k0(self, inelastic_curve):
        """k=0 → ε ≈ 0 (perfectly inelastic)."""
        assert inelastic_curve.epsilon == pytest.approx(0.0, abs=0.01)

    def test_epsilon_at_k1(self, elastic_curve):
        """k=1 → ε = ε_max = 5.0."""
        assert elastic_curve.epsilon == pytest.approx(5.0)

    def test_epsilon_at_k05(self, mid_curve):
        """k=0.5 → ε = 2.5 (assuming linear mapping k·ε_max)."""
        assert mid_curve.epsilon == pytest.approx(2.5)


# ===================================================================
# evaluate() Tests — Isoelastic Demand Curve
# ===================================================================


class TestEvaluate:
    def test_evaluate_at_reference_price(self, mid_curve):
        """Q(P_0) = Q_0 for any k (anchor property).

        Ground truth: Q(0.10) = 5.0 · (0.10/0.10)^{-2.5} = 5.0 · 1 = 5.0
        """
        result = mid_curve.evaluate(price=0.10)
        assert result == pytest.approx(5.0)

    def test_evaluate_high_price_elastic(self, elastic_curve):
        """At 2× reference price, elastic customer consumes much less.

        Ground truth: Q(0.20) = 5.0 · (0.20/0.10)^{-5} = 5.0 · 2^{-5} = 5.0/32 ≈ 0.15625
        """
        result = elastic_curve.evaluate(price=0.20)
        assert result == pytest.approx(5.0 / 32.0, rel=1e-3)

    def test_evaluate_low_price_elastic(self, elastic_curve):
        """At half reference price, elastic customer wants much more.

        Ground truth: Q(0.05) = 5.0 · (0.05/0.10)^{-5} = 5.0 · 2^5 = 160.0
        """
        result = elastic_curve.evaluate(price=0.05)
        assert result == pytest.approx(160.0, rel=1e-3)

    def test_evaluate_inelastic_ignores_price(self, inelastic_curve):
        """k=0, ε≈0 → Q(P) ≈ Q_0 regardless of price.

        Ground truth: Q(0.20) = 5.0 · (2)^{-0} = 5.0 · 1 = 5.0
        """
        result = inelastic_curve.evaluate(price=0.20)
        assert result == pytest.approx(5.0, abs=0.1)

    def test_evaluate_mid_elasticity(self, mid_curve):
        """k=0.5, ε=2.5 → moderate response.

        Ground truth: Q(0.20) = 5.0 · (2)^{-2.5} = 5.0 · (1/√32) ≈ 5.0 · 0.17678 ≈ 0.8839
        """
        expected = 5.0 * (2**-2.5)  # ≈ 0.8839
        result = mid_curve.evaluate(price=0.20)
        assert result == pytest.approx(expected, rel=1e-3)


# ===================================================================
# evaluate_with_bounds() Tests
# ===================================================================


class TestEvaluateWithBounds:
    def test_clamps_to_Q_max(self, elastic_curve):
        """Very low price → huge demand, should be clamped to Q_max.

        Raw Q(0.01) = 5.0 · (0.01/0.10)^{-5} = 5.0 · 10^5 = 500000
        Clamped to Q_max = 10.0
        """
        result = elastic_curve.evaluate_with_bounds(price=0.01, Q_min=0.0, Q_max=10.0)
        assert result == pytest.approx(10.0)

    def test_clamps_to_Q_min(self, elastic_curve):
        """Very high price → near-zero demand, clamped to Q_min.

        Raw Q(1.0) = 5.0 · (10)^{-5} = 5.0e-5 ≈ 0
        Clamped to Q_min = 1.0
        """
        result = elastic_curve.evaluate_with_bounds(price=1.0, Q_min=1.0, Q_max=10.0)
        assert result == pytest.approx(1.0)

    def test_within_bounds_unchanged(self, mid_curve):
        """When raw Q is within bounds, no clamping.

        Q(0.10) = 5.0, bounds [0, 10] → returns 5.0
        """
        result = mid_curve.evaluate_with_bounds(price=0.10, Q_min=0.0, Q_max=10.0)
        assert result == pytest.approx(5.0)


# ===================================================================
# Amenity Cost Tests
# ===================================================================


class TestAmenityCost:
    def test_zero_at_preferred(self, mid_curve):
        """No cost when operating at preferred point."""
        cost = mid_curve.get_amenity_cost(Q_actual=5.0, Q_preferred=5.0)
        assert cost == pytest.approx(0.0)

    def test_positive_when_deviating(self, mid_curve):
        """Deviation from preferred → positive cost."""
        cost = mid_curve.get_amenity_cost(Q_actual=3.0, Q_preferred=5.0)
        assert cost > 0.0

    def test_increases_with_deviation(self, mid_curve):
        """Larger deviation → higher cost."""
        cost_small = mid_curve.get_amenity_cost(Q_actual=4.0, Q_preferred=5.0)
        cost_large = mid_curve.get_amenity_cost(Q_actual=2.0, Q_preferred=5.0)
        assert cost_large > cost_small

    def test_inelastic_customer_higher_cost(self, inelastic_curve, elastic_curve):
        """k=0 (comfort-focused) → higher amenity cost than k=1 (financial)."""
        cost_inelastic = inelastic_curve.get_amenity_cost(Q_actual=3.0, Q_preferred=5.0)
        cost_elastic = elastic_curve.get_amenity_cost(Q_actual=3.0, Q_preferred=5.0)
        assert cost_inelastic > cost_elastic


# ===================================================================
# Battery Curve Tests (Sigmoid)
# ===================================================================


class TestBatteryCurve:
    def test_charges_at_low_price(self, battery_curve):
        """Low price → positive Q (charge)."""
        result = battery_curve.evaluate(price=0.05)
        assert result > 0.0

    def test_discharges_at_high_price(self, battery_curve):
        """High price → negative Q (discharge)."""
        result = battery_curve.evaluate(price=0.25)
        assert result < 0.0

    def test_near_zero_at_threshold(self, battery_curve):
        """Near the degradation-adjusted threshold, Q ≈ 0.

        Threshold ≈ P_0 ± degradation_cost = 0.10 ± 0.02
        At P = 0.10 (midpoint), Q should be near zero.
        """
        result = battery_curve.evaluate(price=0.10)
        assert abs(result) < 1.0  # close to zero, not exactly


# ===================================================================
# sample_bid_curve() Tests
# ===================================================================


class TestSampleBidCurve:
    def test_returns_correct_count(self, mid_curve):
        points = mid_curve.sample_bid_curve(
            price_min=0.01,
            price_max=0.50,
            n_points=10,
            Q_min=0.0,
            Q_max=10.0,
        )
        assert len(points) == 10

    def test_monotonic_decreasing(self, mid_curve):
        """Higher price → lower quantity (demand law)."""
        points = mid_curve.sample_bid_curve(
            price_min=0.01,
            price_max=0.50,
            n_points=20,
            Q_min=0.0,
            Q_max=10.0,
        )
        for i in range(len(points) - 1):
            if points[i].price > points[i + 1].price:
                assert points[i].quantity <= points[i + 1].quantity

    def test_within_bounds(self, mid_curve):
        """All quantities within [Q_min, Q_max]."""
        points = mid_curve.sample_bid_curve(
            price_min=0.01,
            price_max=0.50,
            n_points=20,
            Q_min=1.0,
            Q_max=8.0,
        )
        for pt in points:
            assert 1.0 <= pt.quantity <= 8.0

    def test_returns_bid_points(self, mid_curve):
        """Each element should be a BidPoint."""
        from tesp_support.curve_and_agent.data_types import BidPoint

        points = mid_curve.sample_bid_curve(
            price_min=0.01,
            price_max=0.50,
            n_points=5,
            Q_min=0.0,
            Q_max=10.0,
        )
        assert all(isinstance(pt, BidPoint) for pt in points)
