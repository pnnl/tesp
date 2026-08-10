# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for price_forecast_service.py — Price trajectory management.

Ground truth:
  - CRUD: update creates/overwrites, get_forecast retrieves, get_price returns estimate
  - Trajectory: consecutive intervals returned in order
  - History: multiple updates tracked with iteration provenance
"""

import pytest

from tesp_support.curve_and_agent.enums_and_constants import MarketType
from tesp_support.curve_and_agent.price_forecast_service import PriceForecastService, PriceForecast

RT = MarketType.RT_ENERGY
DA = MarketType.DA_ENERGY


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def service():
    return PriceForecastService()


# ===================================================================
# Constructor
# ===================================================================


class TestPriceForecastServiceConstructor:
    def test_empty(self, service):
        assert len(service._forecasts) == 0


# ===================================================================
# Update & Retrieve
# ===================================================================


class TestUpdateAndRetrieve:
    def test_update_creates_entry(self, service):
        service.update(
            market_type=RT,
            interval=(0.0, 300.0),
            price=0.10,
            confidence=0.5,
            source="informational_clear",
            iteration=1,
        )
        fc = service.get_forecast(RT, (0.0, 300.0))
        assert fc is not None
        assert fc.price_estimate == pytest.approx(0.10)
        assert fc.confidence == pytest.approx(0.5)

    def test_update_overwrites(self, service):
        """Second update for same market/interval overwrites price."""
        service.update(
            market_type=RT,
            interval=(0.0, 300.0),
            price=0.10,
            confidence=0.5,
            source="informational_clear",
            iteration=1,
        )
        service.update(
            market_type=RT,
            interval=(0.0, 300.0),
            price=0.12,
            confidence=0.8,
            source="informational_clear",
            iteration=2,
        )
        fc = service.get_forecast(RT, (0.0, 300.0))
        assert fc.price_estimate == pytest.approx(0.12)
        assert fc.confidence == pytest.approx(0.8)

    def test_get_nonexistent_returns_none(self, service):
        assert service.get_forecast(DA, (0.0, 3600.0)) is None


class TestGetPrice:
    def test_returns_estimate(self, service):
        service.update(
            market_type=RT,
            interval=(0.0, 300.0),
            price=0.10,
            confidence=0.5,
            source="external",
            iteration=0,
        )
        p = service.get_price(RT, (0.0, 300.0))
        assert p == pytest.approx(0.10)

    def test_returns_default_when_missing(self, service):
        p = service.get_price(RT, (0.0, 300.0), default=0.05)
        assert p == pytest.approx(0.05)


# ===================================================================
# Trajectory
# ===================================================================


class TestGetTrajectory:
    def test_hourly_trajectory(self, service):
        """Load 4 hours of hourly prices, retrieve trajectory.

        Intervals: [0,3600), [3600,7200), [7200,10800), [10800,14400)
        Prices:    $0.08,    $0.10,       $0.15,        $0.12
        """
        prices = [0.08, 0.10, 0.15, 0.12]
        for i, p in enumerate(prices):
            service.update(
                market_type=DA,
                interval=(i * 3600.0, (i + 1) * 3600.0),
                price=p,
                confidence=0.9,
                source="external",
                iteration=0,
            )
        traj = service.get_trajectory(
            DA,
            0.0,
            14400.0,
            resolution=3600.0,
        )
        assert len(traj) == 4
        # Check ordering and values
        for i, (interval, price) in enumerate(traj):
            assert price == pytest.approx(prices[i])

    def test_partial_trajectory(self, service):
        """Query a sub-range returns only overlapping intervals."""
        for i in range(4):
            service.update(
                market_type=DA,
                interval=(i * 3600.0, (i + 1) * 3600.0),
                price=0.10 + i * 0.01,
                confidence=0.9,
                source="external",
                iteration=0,
            )
        traj = service.get_trajectory(
            DA,
            3600.0,
            10800.0,
            resolution=3600.0,
        )
        assert len(traj) == 2  # only hours 1 and 2


# ===================================================================
# History Tracking
# ===================================================================


class TestHistoryTracking:
    def test_history_accumulates(self, service):
        """Multiple updates → history shows convergence."""
        for i in range(3):
            service.update(
                market_type=RT,
                interval=(0.0, 300.0),
                price=0.10 + i * 0.01,
                confidence=0.3 + i * 0.2,
                source="informational_clear",
                iteration=i + 1,
            )
        fc = service.get_forecast(RT, (0.0, 300.0))
        assert len(fc.history) == 3
        # Most recent price should be the current estimate
        assert fc.price_estimate == pytest.approx(0.12)
