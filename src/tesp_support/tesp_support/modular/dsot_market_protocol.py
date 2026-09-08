"""DSOT market protocol implementation wrapping current timing and clearing logic.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This module wraps the existing DSOT retail market structure (day-ahead + real-time
with 1-hour and 5-minute periods) as a concrete instance of the MarketProtocol abstraction.

Key responsibilities:
  - DSOTMarketProtocol: Defines settlement structure (DA + RT windows, timing, deadlines)
  - DSOTCurveIntersectionClearing: Implements the curve intersection clearing algorithm
  - Integration points to existing retail_market.py clearing methods
"""

from typing import Dict, List, Tuple
from datetime import datetime, timedelta

from ..modular.market_protocol import (
    Bid,
    ClearingMechanism,
    MarketProtocol,
    MarketWindow,
)
from ..modular.price_signal import PriceSignal


class DSOTCurveIntersectionClearing(ClearingMechanism):
    """Curve intersection clearing delegating to RetailMarket.clear_market().

    Converts List[Bid] (MWh / $/MWh units) to Curve objects (kWh / $/kWh)
    by sampling each bid's value_function, then delegates to the existing
    RetailMarket curve-intersection algorithm. Unit bridge: ×1000 for quantity,
    ÷1000 for price.

    Attributes:
        clearing_type: Last clearing outcome (MarketClearingType enum value).
        congestion_surcharge (float): Last congestion surcharge in $/MWh.
    """

    def __init__(
        self,
        price_cap: float = 100.0,
        feeder_capacity_mwh: float = 100.0,
        num_samples: int = 100,
        retail_market=None,
        transformer_degradation: bool = False,
    ):
        """Initialize clearing mechanism.

        Args:
            price_cap: Market price cap ($/MWh).
            feeder_capacity_mwh: Feeder capacity constraint (MWh).
            num_samples: Points used when building aggregated Curve objects.
            retail_market: RetailMarket instance whose clear_market() is called.
            transformer_degradation: Passed through to RetailMarket.clear_market().
        """
        self.price_cap = price_cap
        self.feeder_capacity_mwh = feeder_capacity_mwh
        self.num_samples = num_samples
        self.retail_market = retail_market
        self.transformer_degradation = transformer_degradation
        self.clearing_type = None
        self.congestion_surcharge = 0.0

    def _bid_to_curve_points(self, bid: Bid) -> List[List[float]]:
        """Sample value_function at 4 points; convert MWh/$/MWh → kWh/$/kWh."""
        import numpy as np
        quantities_mwh = np.linspace(bid.quantity_min, bid.quantity_max, 4)
        return [
            [float(q) * 1000.0, float(bid.value_function(q)) / 1000.0]
            for q in quantities_mwh
        ]

    def _quantity_at_price(self, bid: Bid, cleared_price_kwh: float) -> float:
        """Scan value_function to find cleared quantity (MWh) at cleared_price."""
        import numpy as np
        cleared_price_mwh = cleared_price_kwh * 1000.0
        quantities = np.linspace(bid.quantity_min, bid.quantity_max, 100)
        accepted = bid.quantity_min
        if bid.bid_type == 'demand':
            # buy up to the last quantity where willingness-to-pay >= clearing price
            for q in quantities:
                if bid.value_function(float(q)) >= cleared_price_mwh:
                    accepted = float(q)
                else:
                    break
        else:
            # supply up to the last quantity where marginal cost <= clearing price
            for q in quantities:
                if bid.value_function(float(q)) <= cleared_price_mwh:
                    accepted = float(q)
                else:
                    break
        return accepted

    def clear(self, bids: List[Bid]) -> Dict[str, Tuple[float, float]]:
        """Clear market via RetailMarket.clear_market() curve intersection.

        Args:
            bids: Bid objects submitted for this market window.

        Returns:
            Dict mapping participant_id → (cleared_quantity_mwh, clearing_price_per_mwh).
        """
        if not bids:
            return {}
        if self.retail_market is None:
            return {bid.participant_id: (0.0, 0.0) for bid in bids}

        from ..dsot.helpers_dsot import Curve

        price_cap_kwh = self.price_cap / 1000.0
        curve_buyer = Curve([price_cap_kwh, 0.0], self.num_samples)
        curve_seller = Curve([price_cap_kwh, 0.0], self.num_samples)

        for bid in bids:
            pts = self._bid_to_curve_points(bid)
            if bid.bid_type == 'demand':
                curve_buyer.curve_aggregator('Buyer', pts)
            else:
                curve_seller.curve_aggregator('Seller', pts)

        clear_type, cleared_price_kwh, _cleared_qty_kwh, congestion_kwh = \
            self.retail_market.clear_market(
                curve_buyer,
                curve_seller,
                self.transformer_degradation,
                self.feeder_capacity_mwh * 1000.0,
            )

        self.clearing_type = clear_type
        self.congestion_surcharge = congestion_kwh * 1000.0

        if cleared_price_kwh == float('inf'):
            return {bid.participant_id: (0.0, 0.0) for bid in bids}

        cleared_price_mwh = cleared_price_kwh * 1000.0
        return {
            bid.participant_id: (
                self._quantity_at_price(bid, cleared_price_kwh),
                cleared_price_mwh,
            )
            for bid in bids
        }


class DSOTMarketProtocol(MarketProtocol):
    """DSOT market protocol: day-ahead (hourly) + real-time (5-min) co-optimization.

    The DSOT protocol consists of:
      1. A repeating day-ahead market (clearing at hourly boundaries, bidding 60 sec before)
      2. A repeating real-time market (clearing every 5 minutes, bidding 30 sec before)

    Wholesale bids go to PSST/AMES at fixed times (10 AM for DA, continuously for RT).
    Retail prices propagate from cleared results back to devices for next-period bids.

    Attributes:
        da_period_seconds (int): Length of DA settlement period (default: 3600 = 1 hour)
        rt_period_seconds (int): Length of RT settlement period (default: 300 = 5 minutes)
        da_bid_lead_time_seconds (int): Time before DA clearing when bids must be submitted (default: 60)
        rt_bid_lead_time_seconds (int): Time before RT clearing when bids must be submitted (default: 30)
        simulation_start_time (datetime): Start of simulation (used to anchor market windows)
        clearing_mechanisms (Dict[str, ClearingMechanism]): Clearing algorithm for each market type
    """

    def __init__(
        self,
        da_period_seconds: int = 3600,
        rt_period_seconds: int = 300,
        da_bid_lead_time_seconds: int = 60,
        rt_bid_lead_time_seconds: int = 30,
        simulation_start_time: datetime = None,
        retail_market=None,
    ):
        """Initialize DSOT market protocol with timing parameters.

        Args:
            da_period_seconds: Length of each DA settlement period (seconds).
            rt_period_seconds: Length of each RT settlement period (seconds).
            da_bid_lead_time_seconds: Time before DA clearing when bids must be submitted.
            rt_bid_lead_time_seconds: Time before RT clearing when bids must be submitted.
            simulation_start_time: Start time of simulation (for anchoring market windows).
            retail_market: RetailMarket instance passed through to clearing mechanisms.
        """
        self.da_period_seconds = da_period_seconds
        self.rt_period_seconds = rt_period_seconds
        self.da_bid_lead_time_seconds = da_bid_lead_time_seconds
        self.rt_bid_lead_time_seconds = rt_bid_lead_time_seconds
        self.simulation_start_time = simulation_start_time or datetime.now()

        self.clearing_mechanisms = {
            "DA": DSOTCurveIntersectionClearing(retail_market=retail_market),
            "RT": DSOTCurveIntersectionClearing(retail_market=retail_market),
        }

    def settlement_structure(
        self, period_start: int, period_end: int
    ) -> List[MarketWindow]:
        """Generate market windows for a time period.

        For the DSOT protocol, this returns all DA and RT market windows that
        occur between period_start and period_end (simulation time in seconds).

        Args:
            period_start: Start of time range (simulation time, seconds since start).
            period_end: End of time range (simulation time, seconds since start).

        Returns:
            List of MarketWindow objects ordered by clearing_time. Each window
            specifies market type, settlement period, bid deadline, and clearing time.
        """
        windows = []
        window_number = 0

        # Generate DA market windows (hourly)
        da_clearing_time = (
            ((period_start // self.da_period_seconds) + 1) * self.da_period_seconds
        )
        while da_clearing_time <= period_end:
            settlement_start = da_clearing_time - self.da_period_seconds
            settlement_end = da_clearing_time
            bid_deadline = da_clearing_time - self.da_bid_lead_time_seconds

            windows.append(
                MarketWindow(
                    market_id="DA",
                    window_number=window_number,
                    settlement_period_start=int(settlement_start),
                    settlement_period_end=int(settlement_end),
                    bid_submission_deadline=int(bid_deadline),
                    clearing_time=int(da_clearing_time),
                    clearing_mechanism_name="curve_intersection",
                )
            )
            window_number += 1
            da_clearing_time += self.da_period_seconds

        # Generate RT market windows (5-minute)
        rt_clearing_time = (
            ((period_start // self.rt_period_seconds) + 1) * self.rt_period_seconds
        )
        while rt_clearing_time <= period_end:
            settlement_start = rt_clearing_time - self.rt_period_seconds
            settlement_end = rt_clearing_time
            bid_deadline = rt_clearing_time - self.rt_bid_lead_time_seconds

            windows.append(
                MarketWindow(
                    market_id="RT",
                    window_number=window_number,
                    settlement_period_start=int(settlement_start),
                    settlement_period_end=int(settlement_end),
                    bid_submission_deadline=int(bid_deadline),
                    clearing_time=int(rt_clearing_time),
                    clearing_mechanism_name="curve_intersection",
                )
            )
            window_number += 1
            rt_clearing_time += self.rt_period_seconds

        # Sort by clearing time
        windows.sort(key=lambda w: w.clearing_time)
        return windows

    def get_clearing_mechanism(self, market_window: MarketWindow) -> ClearingMechanism:
        """Retrieve the clearing mechanism for a market window.

        Args:
            market_window: The MarketWindow to clear.

        Returns:
            A ClearingMechanism instance (currently curve intersection for both DA and RT).
        """
        market_type = market_window.market_id
        if market_type not in self.clearing_mechanisms:
            raise ValueError(f"Unknown market type: {market_type}")
        return self.clearing_mechanisms[market_type]

    def publish_results(self, market_window: MarketWindow, clearing_result: Dict) -> PriceSignal:
        """Convert clearing results to a PriceSignal for participant feedback.

        Args:
            market_window: The cleared market window.
            clearing_result: Dict mapping participant_id → (cleared_Q, clearing_price).

        Returns:
            A PriceSignal object ready for HELICS publication or internal use.
        """
        # Extract clearing outcomes
        participant_prices = {}
        cleared_quantities = {}
        clearing_price = 0.0

        for participant_id, (quantity, price) in clearing_result.items():
            participant_prices[participant_id] = price
            cleared_quantities[participant_id] = quantity
            # System clearing price is the last price in the result
            clearing_price = price

        return PriceSignal(
            market_id=market_window.market_id,
            time_step=market_window.clearing_time,
            period_start=market_window.settlement_period_start,
            period_end=market_window.settlement_period_end,
            clearing_price=clearing_price,
            participant_prices=participant_prices,
            cleared_quantities=cleared_quantities,
            metadata={
                "window_number": market_window.window_number,
                "clearing_mechanism": market_window.clearing_mechanism_name,
            },
        )
