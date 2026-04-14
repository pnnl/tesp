# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for enums_and_constants.py — Level 0 foundation.

All enums are fully implemented (no stubs). Every test here should
pass immediately and serves as a regression guard against accidental
enum changes.
"""

import pytest

from tesp_support.curve_and_agent.enums_and_constants import (
    MarketType,
    MarketPhase,
    OperatingMode,
    IterationType,
    CommitmentStatus,
    DeviceType,
    ProductType,
    ForecastParadigm,
    StreamType,
    PenaltyStructureType,
)


# ===================================================================
# Enum Membership Tests
# ===================================================================


class TestMarketType:
    """MarketType should have exactly 4 members."""

    def test_member_count(self):
        assert len(MarketType) == 4

    @pytest.mark.parametrize(
        "name",
        [
            "RT_ENERGY",
            "DA_ENERGY",
            "REGULATION",
            "SPINNING_RESERVE",
        ],
    )
    def test_expected_members(self, name):
        assert hasattr(MarketType, name)

    def test_values_are_unique(self):
        values = [m.value for m in MarketType]
        assert len(values) == len(set(values))


class TestMarketPhase:
    """MarketPhase should have exactly 9 members in lifecycle order."""

    EXPECTED_ORDER = [
        "INACTIVE",
        "ACTIVE",
        "NEGOTIATION",
        "MARKET_LEAD",
        "ASSESSMENT",
        "DELIVERY_LEAD",
        "DELIVERY",
        "RECONCILE",
        "EXPIRED",
    ]

    def test_member_count(self):
        assert len(MarketPhase) == 9

    @pytest.mark.parametrize("name", EXPECTED_ORDER)
    def test_expected_members(self, name):
        assert hasattr(MarketPhase, name)

    def test_lifecycle_ordering(self):
        """auto() assigns increasing ints, so value order = declaration order."""
        ordered_values = [MarketPhase[name].value for name in self.EXPECTED_ORDER]
        assert ordered_values == sorted(ordered_values)

    def test_values_are_unique(self):
        values = [m.value for m in MarketPhase]
        assert len(values) == len(set(values))


class TestOperatingMode:
    def test_member_count(self):
        assert len(OperatingMode) == 3

    @pytest.mark.parametrize("name", ["BIDDING", "PRICE_RESPONSIVE", "OVERRIDE"])
    def test_expected_members(self, name):
        assert hasattr(OperatingMode, name)


class TestIterationType:
    def test_member_count(self):
        assert len(IterationType) == 2

    def test_informational_exists(self):
        assert IterationType.INFORMATIONAL is not None

    def test_binding_exists(self):
        assert IterationType.BINDING is not None

    def test_not_equal(self):
        assert IterationType.INFORMATIONAL != IterationType.BINDING


class TestCommitmentStatus:
    EXPECTED = ["TENTATIVE", "ADVISORY", "FIRM", "RELEASED"]

    def test_member_count(self):
        assert len(CommitmentStatus) == 4

    @pytest.mark.parametrize("name", EXPECTED)
    def test_expected_members(self, name):
        assert hasattr(CommitmentStatus, name)

    def test_lifecycle_ordering(self):
        ordered_values = [CommitmentStatus[n].value for n in self.EXPECTED]
        assert ordered_values == sorted(ordered_values)


class TestDeviceType:
    EXPECTED = [
        "HVAC_HEAT_PUMP",
        "HVAC_AC_ONLY",
        "WATER_HEATER",
        "EV_CHARGER",
        "BATTERY",
    ]

    def test_member_count(self):
        assert len(DeviceType) == 5

    @pytest.mark.parametrize("name", EXPECTED)
    def test_expected_members(self, name):
        assert hasattr(DeviceType, name)


class TestProductType:
    EXPECTED = [
        "ENERGY_BASE",
        "REGULATION_UP",
        "REGULATION_DOWN",
        "RESERVE_UP",
        "RESERVE_DOWN",
    ]

    def test_member_count(self):
        assert len(ProductType) == 5

    @pytest.mark.parametrize("name", EXPECTED)
    def test_expected_members(self, name):
        assert hasattr(ProductType, name)


class TestForecastParadigm:
    def test_member_count(self):
        assert len(ForecastParadigm) == 3

    @pytest.mark.parametrize("name", ["CONTINUOUS", "EVENT", "HYBRID"])
    def test_expected_members(self, name):
        assert hasattr(ForecastParadigm, name)


class TestStreamType:
    def test_member_count(self):
        assert len(StreamType) == 3

    @pytest.mark.parametrize("name", ["FORECAST", "SCHEDULE", "CONSTRAINT"])
    def test_expected_members(self, name):
        assert hasattr(StreamType, name)


class TestPenaltyStructureType:
    def test_member_count(self):
        assert len(PenaltyStructureType) == 4

    @pytest.mark.parametrize("name", ["PROPORTIONAL", "TIERED", "SCORED", "COMPOUND"])
    def test_expected_members(self, name):
        assert hasattr(PenaltyStructureType, name)
