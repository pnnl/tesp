# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for penalty_model.py — Level 2 leaf logic.

Defines hand-calculated ground truth for each penalty structure type.
All method tests are xfail(raises=NotImplementedError) until
PenaltyModel methods are implemented.

Penalty calculation conventions
-------------------------------
- Shortfall = max(0, committed - actual)  [kW]
- Energy shortfall = shortfall × (interval_duration / 3600)  [kWh]
- Revenue and penalty are both in $.
"""

import pytest

from tesp_support.curve_and_agent.enums_and_constants import MarketType, PenaltyStructureType
from tesp_support.curve_and_agent.penalty_model import PenaltyModel


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def proportional_fixed():
    """PROPORTIONAL penalty: fixed rate of $0.50/kWh shortfall."""
    return PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"base_rate": 0.50, "rate_reference": "fixed"},
    )


@pytest.fixture
def proportional_multiplier():
    """PROPORTIONAL penalty: 2× cleared price per kWh shortfall."""
    return PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )


@pytest.fixture
def tiered_penalty():
    """TIERED penalty: increasing rates at higher shortfall fractions.

    Tiers (shortfall_fraction_threshold, rate $/kWh):
        0.00 — 0.10:  $0.25/kWh
        0.10 — 0.30:  $0.50/kWh
        0.30 — 1.00:  $1.00/kWh
    """
    return PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.TIERED,
        params={
            "tiers": [(0.0, 0.25), (0.10, 0.50), (0.30, 1.00)],
        },
    )


@pytest.fixture
def compound_penalty():
    """COMPOUND penalty: $10 fixed + $0.30/kWh proportional."""
    return PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.COMPOUND,
        params={"fixed_penalty": 10.0, "proportional_rate": 0.30},
    )


# ===================================================================
# Constructor Tests (should pass)
# ===================================================================


class TestPenaltyModelConstructor:
    def test_construct_proportional(self, proportional_fixed):
        assert proportional_fixed._structure_type == PenaltyStructureType.PROPORTIONAL
        assert proportional_fixed._params["base_rate"] == 0.50

    def test_construct_tiered(self, tiered_penalty):
        assert tiered_penalty._structure_type == PenaltyStructureType.TIERED
        assert len(tiered_penalty._params["tiers"]) == 3

    def test_construct_compound(self, compound_penalty):
        assert compound_penalty._structure_type == PenaltyStructureType.COMPOUND


# ===================================================================
# compute_penalty() — PROPORTIONAL (Fixed Rate)
# ===================================================================


class TestProportionalFixed:
    def test_no_shortfall(self, proportional_fixed):
        """Full delivery → zero penalty.

        committed=10, actual=10, shortfall=0 → penalty = 0
        """
        penalty = proportional_fixed.compute_penalty(
            committed_qty=10.0,
            actual_qty=10.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        assert penalty == pytest.approx(0.0)

    def test_full_shortfall(self, proportional_fixed):
        """Zero delivery → maximum penalty.

        committed=10 kW, actual=0, shortfall=10 kW
        interval = 300 s  → energy_shortfall = 10 × (300/3600) = 0.8333 kWh
        penalty = 0.50 × 0.8333 = $0.4167
        """
        penalty = proportional_fixed.compute_penalty(
            committed_qty=10.0,
            actual_qty=0.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        expected = 0.50 * 10.0 * (300.0 / 3600.0)  # $0.4167
        assert penalty == pytest.approx(expected, rel=1e-3)

    def test_partial_shortfall(self, proportional_fixed):
        """Partial delivery.

        committed=10, actual=7, shortfall=3 kW
        energy_shortfall = 3 × (300/3600) = 0.25 kWh
        penalty = 0.50 × 0.25 = $0.125
        """
        penalty = proportional_fixed.compute_penalty(
            committed_qty=10.0,
            actual_qty=7.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        expected = 0.50 * 3.0 * (300.0 / 3600.0)
        assert penalty == pytest.approx(expected, rel=1e-3)

    def test_over_delivery_no_penalty(self, proportional_fixed):
        """Actual > committed → no penalty (no negative penalty)."""
        penalty = proportional_fixed.compute_penalty(
            committed_qty=5.0,
            actual_qty=7.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        assert penalty == pytest.approx(0.0)


# ===================================================================
# compute_penalty() — PROPORTIONAL (Multiplier)
# ===================================================================


class TestProportionalMultiplier:
    def test_multiplier_mode(self, proportional_multiplier):
        """Penalty rate = multiplier × cleared_price = 2 × 0.10 = $0.20/kWh.

        committed=10, actual=5, shortfall=5 kW
        energy_shortfall = 5 × (300/3600) = 0.41667 kWh
        penalty = 0.20 × 0.41667 = $0.08333
        """
        penalty = proportional_multiplier.compute_penalty(
            committed_qty=10.0,
            actual_qty=5.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        rate = 2.0 * 0.10  # $0.20/kWh
        shortfall_kwh = 5.0 * (300.0 / 3600.0)
        expected = rate * shortfall_kwh  # $0.08333
        assert penalty == pytest.approx(expected, rel=1e-3)


# ===================================================================
# compute_penalty() — TIERED
# ===================================================================


class TestTiered:
    def test_small_shortfall_tier1(self, tiered_penalty):
        """5% shortfall → entirely in tier 1 (rate $0.25/kWh).

        committed=10, actual=9.5, shortfall=0.5 kW (5%)
        energy = 0.5 × (300/3600) = 0.04167 kWh
        penalty = 0.25 × 0.04167 = $0.01042
        """
        penalty = tiered_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=9.5,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        expected = 0.25 * 0.5 * (300.0 / 3600.0)
        assert penalty == pytest.approx(expected, rel=1e-2)

    def test_medium_shortfall_two_tiers(self, tiered_penalty):
        """20% shortfall → spans tier 1 (0–10%) and tier 2 (10–30%).

        committed=10, actual=8, shortfall=2 kW (20%)
        Tier 1: first 10% = 1.0 kW at $0.25
        Tier 2: next 10% = 1.0 kW at $0.50
        Total penalty_power = 1.0*0.25 + 1.0*0.50 = $0.75/kW
        × (300/3600) = $0.0625
        """
        penalty = tiered_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=8.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        tier1_kwh = 1.0 * (300.0 / 3600.0)
        tier2_kwh = 1.0 * (300.0 / 3600.0)
        expected = 0.25 * tier1_kwh + 0.50 * tier2_kwh
        assert penalty == pytest.approx(expected, rel=1e-2)

    def test_large_shortfall_all_tiers(self, tiered_penalty):
        """50% shortfall → spans all 3 tiers.

        committed=10, actual=5, shortfall=5 kW (50%)
        Tier 1: 0–10%  = 1.0 kW at $0.25
        Tier 2: 10–30% = 2.0 kW at $0.50
        Tier 3: 30–50% = 2.0 kW at $1.00
        Cost per kW = 0.25 + 1.00 + 2.00 = $3.25
        × (300/3600) = $0.2708
        """
        penalty = tiered_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=5.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        dt = 300.0 / 3600.0
        expected = (1.0 * 0.25 + 2.0 * 0.50 + 2.0 * 1.00) * dt
        assert penalty == pytest.approx(expected, rel=1e-2)


# ===================================================================
# compute_penalty() — COMPOUND
# ===================================================================


class TestCompound:
    def test_compound_with_shortfall(self, compound_penalty):
        """COMPOUND: fixed $10 + proportional.

        committed=10, actual=5, shortfall=5 kW
        energy = 5 × (300/3600) = 0.4167 kWh
        proportional = 0.30 × 0.4167 = $0.125
        total = 10.0 + 0.125 = $10.125
        """
        penalty = compound_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=5.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        shortfall_kwh = 5.0 * (300.0 / 3600.0)
        expected = 10.0 + 0.30 * shortfall_kwh
        assert penalty == pytest.approx(expected, rel=1e-2)

    def test_compound_no_shortfall(self, compound_penalty):
        """No shortfall → no penalty (fixed only applies when there IS shortfall)."""
        penalty = compound_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=10.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        assert penalty == pytest.approx(0.0)


# ===================================================================
# marginal_penalty() Tests
# ===================================================================


class TestMarginalPenalty:
    def test_marginal_proportional_fixed(self, proportional_fixed):
        """Marginal penalty at first kW = base_rate × (interval/3600).

        rate = $0.50/kWh, interval = 300 s
        marginal per kW = 0.50 × (300/3600) = $0.04167
        """
        m = proportional_fixed.marginal_penalty(
            committed_qty=10.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        expected = 0.50 * (300.0 / 3600.0)
        assert m == pytest.approx(expected, rel=1e-3)

    def test_marginal_tiered_first_tier(self, tiered_penalty):
        """First kW of shortfall hits tier 1 rate ($0.25/kWh).

        marginal = 0.25 × (300/3600) = $0.02083
        """
        m = tiered_penalty.marginal_penalty(
            committed_qty=10.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        expected = 0.25 * (300.0 / 3600.0)
        assert m == pytest.approx(expected, rel=1e-3)

    def test_marginal_compound(self, compound_penalty):
        """COMPOUND marginal = proportional rate per kWh of shortfall.

        The fixed component doesn't affect marginal (it's constant w.r.t. shortfall).
        marginal ≈ proportional_rate × (interval/3600) = 0.30 × (300/3600) = $0.025.
        """
        m = compound_penalty.marginal_penalty(
            committed_qty=10.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        expected = 0.30 * (300.0 / 3600.0)
        assert m == pytest.approx(expected, rel=0.1)


# ===================================================================
# compute_penalty() — SCORED
# ===================================================================


@pytest.fixture
def scored_penalty():
    """SCORED penalty: performance-score-based penalty model.

    Score from 0 (total failure) to 1 (perfect delivery).
    Penalty = max_penalty × (1 - score)^exponent × (interval/3600).
    max_penalty = $5.00/kWh, exponent = 2.0 (quadratic).
    """
    return PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.SCORED,
        params={"max_penalty": 5.00, "exponent": 2.0},
    )


class TestScored:
    def test_perfect_delivery(self, scored_penalty):
        """Score=1.0 (perfect) → penalty = 0."""
        penalty = scored_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=10.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        assert penalty == pytest.approx(0.0)

    def test_total_failure(self, scored_penalty):
        """Score=0 (zero delivery) → maximum penalty.

        score = actual/committed = 0/10 = 0.
        penalty = max_penalty × (1-0)^2 × energy = 5.0 × 1.0 × (10 × 300/3600)
               = 5.0 × 0.8333 = $4.167.
        """
        penalty = scored_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=0.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        energy = 10.0 * (300.0 / 3600.0)
        expected = 5.00 * (1.0**2) * energy  # $4.167
        assert penalty == pytest.approx(expected, rel=0.05)

    def test_half_delivery_quadratic(self, scored_penalty):
        """Score=0.5 → penalty = max × (0.5)^2 × energy.

        committed=10, actual=5 → score = 0.5.
        penalty = 5.00 × 0.25 × (10 × 300/3600) = 1.25 × 0.8333 = $1.042.
        """
        penalty = scored_penalty.compute_penalty(
            committed_qty=10.0,
            actual_qty=5.0,
            cleared_price=0.10,
            interval_duration=300.0,
        )
        energy = 10.0 * (300.0 / 3600.0)
        expected = 5.00 * (0.5**2) * energy
        assert penalty == pytest.approx(expected, rel=0.05)
