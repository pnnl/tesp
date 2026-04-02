# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for flexibility_ledger.py — Capacity commitment tracking.

Ground truth for three-tier availability queries:
  - HARD: Q_device minus ALL commitments (tentative+advisory+firm)
  - EXPECTED: firm at 100%, advisory at confidence weight, tentative at 0.4
  - ECONOMIC: hard availability + displaceable blocks sorted by cost
"""

import pytest

from enums_and_constants import CommitmentStatus, MarketType, ProductType
from data_types import EconomicCommitment, FlexibilityEnvelope
from flexibility_ledger import FlexibilityLedger, EconomicEnvelope

RT = MarketType.RT_ENERGY


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def load_ledger():
    """A ledger for a load-only device: Q_min=0, Q_max=10 kW."""
    return FlexibilityLedger(Q_min_device=0.0, Q_max_device=10.0)


@pytest.fixture
def battery_ledger():
    """A ledger for a battery: Q_min=-5 kW, Q_max=5 kW."""
    return FlexibilityLedger(Q_min_device=-5.0, Q_max_device=5.0)


# ===================================================================
# Constructor Tests
# ===================================================================


class TestFlexibilityLedgerConstructor:
    def test_load_device(self, load_ledger):
        assert load_ledger._Q_min == 0.0
        assert load_ledger._Q_max == 10.0
        assert len(load_ledger._commitments) == 0

    def test_battery_device(self, battery_ledger):
        assert battery_ledger._Q_min == -5.0
        assert battery_ledger._Q_max == 5.0


# ===================================================================
# Commitment Lifecycle Tests
# ===================================================================


class TestHoldTentative:
    def test_tentative_recorded(self, load_ledger):
        """Tentative hold should appear in commitments list."""
        load_ledger.hold_tentative(
            market_id="RT_100",
            market_type=RT,
            product_type=ProductType.ENERGY_BASE,
            quantity=3.0,
            interval=(100.0, 400.0),
        )
        overlapping = load_ledger.get_commitments_overlapping((100.0, 400.0))
        assert len(overlapping) == 1
        assert overlapping[0].quantity == 3.0

    def test_tentative_replaces_same_market(self, load_ledger):
        """Second tentative for same market_id replaces the first."""
        load_ledger.hold_tentative(
            market_id="RT_100",
            market_type=RT,
            product_type=ProductType.ENERGY_BASE,
            quantity=3.0,
            interval=(100.0, 400.0),
        )
        load_ledger.hold_tentative(
            market_id="RT_100",
            market_type=RT,
            product_type=ProductType.ENERGY_BASE,
            quantity=5.0,
            interval=(100.0, 400.0),
        )
        overlapping = load_ledger.get_commitments_overlapping((100.0, 400.0))
        assert len(overlapping) == 1
        assert overlapping[0].quantity == 5.0


class TestUpdateAdvisory:
    def test_advisory_recorded(self, load_ledger):
        load_ledger.hold_tentative(
            market_id="RT_100",
            market_type=RT,
            product_type=ProductType.ENERGY_BASE,
            quantity=3.0,
            interval=(100.0, 400.0),
        )
        load_ledger.update_advisory(
            market_id="RT_100",
            quantity=4.0,
            interval=(100.0, 400.0),
            confidence=0.7,
            cleared_price=0.10,
            penalty_model_id="pen_1",
            iteration=1,
        )
        overlapping = load_ledger.get_commitments_overlapping((100.0, 400.0))
        assert len(overlapping) == 1
        assert overlapping[0].quantity == 4.0


class TestBookFirmAndRelease:
    def test_firm_then_release(self, load_ledger):
        load_ledger.book_firm(
            market_id="RT_100",
            quantity=6.0,
            interval=(100.0, 400.0),
            cleared_price=0.12,
            penalty_model_id="pen_1",
        )
        overlapping = load_ledger.get_commitments_overlapping((100.0, 400.0))
        assert len(overlapping) == 1

        load_ledger.release("RT_100")
        overlapping = load_ledger.get_commitments_overlapping((100.0, 400.0))
        assert len(overlapping) == 0


# ===================================================================
# TIER 1: Hard Availability Tests
# ===================================================================


class TestHardAvailable:
    def test_empty_ledger(self, load_ledger):
        """No commitments → full device range available."""
        q_min, q_max = load_ledger.hard_available((0.0, 300.0))
        assert q_min == 0.0
        assert q_max == 10.0

    def test_single_firm_commitment(self, load_ledger):
        """Firm 6 kW commitment → only 4 kW available.

        hard_Q_max = Q_max_device - Σ committed = 10 - 6 = 4 kW.
        """
        load_ledger.book_firm(
            market_id="RT_100",
            quantity=6.0,
            interval=(100.0, 400.0),
            cleared_price=0.12,
            penalty_model_id="pen_1",
        )
        q_min, q_max = load_ledger.hard_available((100.0, 400.0))
        assert q_max == pytest.approx(4.0, abs=0.1)

    def test_excluding_market(self, load_ledger):
        """Excluding own market restores its capacity.

        Firm 6 kW from RT_100, but querying excluding="RT_100"
        → 10 kW available again.
        """
        load_ledger.book_firm(
            market_id="RT_100",
            quantity=6.0,
            interval=(100.0, 400.0),
            cleared_price=0.12,
            penalty_model_id="pen_1",
        )
        q_min, q_max = load_ledger.hard_available((100.0, 400.0), excluding="RT_100")
        assert q_max == pytest.approx(10.0, abs=0.1)

    def test_battery_bidirectional(self, battery_ledger):
        """Battery with firm 3 kW charge → discharge still available.

        hard_Q_min = Q_min_device = -5 kW (discharge unaffected by charge commitment).
        hard_Q_max = Q_max_device - 3 = 5 - 3 = 2 kW.
        """
        battery_ledger.book_firm(
            market_id="DA_1",
            quantity=3.0,
            interval=(0.0, 3600.0),
            cleared_price=0.08,
            penalty_model_id="pen_da",
        )
        q_min, q_max = battery_ledger.hard_available((0.0, 3600.0))
        assert q_min == pytest.approx(-5.0, abs=0.1)
        assert q_max == pytest.approx(2.0, abs=0.1)


# ===================================================================
# TIER 2: Expected Availability Tests
# ===================================================================


class TestExpectedAvailable:
    def test_firm_fully_deducted(self, load_ledger):
        """Firm commitments count at 100%."""
        load_ledger.book_firm(
            market_id="RT_100",
            quantity=6.0,
            interval=(100.0, 400.0),
            cleared_price=0.12,
            penalty_model_id="pen_1",
        )
        q_min, q_max = load_ledger.expected_available((100.0, 400.0))
        assert q_max == pytest.approx(4.0, abs=0.1)

    def test_advisory_weighted_by_confidence(self, load_ledger):
        """Advisory at confidence=0.7, 4 kW → deducts 0.7×4 = 2.8 kW.

        expected_Q_max = 10 - 2.8 = 7.2 kW.
        """
        load_ledger.update_advisory(
            market_id="DA_1",
            quantity=4.0,
            interval=(0.0, 3600.0),
            confidence=0.7,
            cleared_price=0.10,
            penalty_model_id="pen_da",
            iteration=1,
        )
        q_min, q_max = load_ledger.expected_available((0.0, 3600.0))
        assert q_max == pytest.approx(7.2, abs=0.3)

    def test_tentative_at_baseline_weight(self, load_ledger):
        """Tentative 5 kW at baseline weight 0.4 → deducts 2.0 kW.

        expected_Q_max = 10 - 2.0 = 8.0 kW.
        """
        load_ledger.hold_tentative(
            market_id="RT_200",
            market_type=RT,
            product_type=ProductType.ENERGY_BASE,
            quantity=5.0,
            interval=(300.0, 600.0),
        )
        q_min, q_max = load_ledger.expected_available((300.0, 600.0))
        assert q_max == pytest.approx(8.0, abs=0.3)


# ===================================================================
# TIER 3: Economic Availability Tests
# ===================================================================


class TestEconomicAvailable:
    def test_displaceable_block(self, load_ledger):
        """Advisory commitment is displaceable if candidate value > displacement cost.

        Setup: advisory 4 kW at cleared_price=$0.10, marginal_pen=$0.05.
        Candidate value = $0.20/kW, candidate penalty = $0.03/kW.
        Displacement cost = pen - net_value of advisory.
        """
        load_ledger.update_advisory(
            market_id="DA_1",
            quantity=4.0,
            interval=(0.0, 3600.0),
            confidence=0.8,
            cleared_price=0.10,
            penalty_model_id="pen_da",
            iteration=2,
            marginal_nv=0.10,
            marginal_pen=0.05,
        )
        envelope = load_ledger.economic_available(
            (0.0, 3600.0),
            candidate_value=0.20,
            candidate_penalty=0.03,
        )
        assert isinstance(envelope, EconomicEnvelope)
        assert envelope.total_displaceable > 0.0
        assert envelope.soft_Q_max_avail > envelope.hard_Q_max_avail

    def test_no_displacement_when_too_expensive(self, load_ledger):
        """If candidate value < displacement cost, no blocks offered."""
        load_ledger.book_firm(
            market_id="RT_100",
            quantity=8.0,
            interval=(100.0, 400.0),
            cleared_price=0.50,
            penalty_model_id="pen_1",
            marginal_nv=0.50,
            marginal_pen=1.00,
        )
        envelope = load_ledger.economic_available(
            (100.0, 400.0),
            candidate_value=0.01,
            candidate_penalty=0.00,
        )
        assert envelope.total_displaceable == 0.0


# ===================================================================
# Non-overlapping intervals
# ===================================================================


class TestNonOverlappingIntervals:
    def test_commitment_outside_query(self, load_ledger):
        """Commitment for [100,400] doesn't affect query for [500,800]."""
        load_ledger.book_firm(
            market_id="RT_100",
            quantity=6.0,
            interval=(100.0, 400.0),
            cleared_price=0.12,
            penalty_model_id="pen_1",
        )
        q_min, q_max = load_ledger.hard_available((500.0, 800.0))
        assert q_max == pytest.approx(10.0, abs=0.1)
