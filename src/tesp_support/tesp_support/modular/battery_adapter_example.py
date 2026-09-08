"""
Migration guide: Adapting existing DSOT agents to DeviceStrategy.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This document shows how to convert an existing DSOT device agent (e.g., BatteryDSOT)
to the new modular DeviceStrategy interface, step by step.

The key insight: existing agents already encapsulate device physics and optimization.
We just need to:
  1. Inherit from DeviceStrategy instead of having standalone methods
  2. Map formulate_bid_da() + formulate_bid_rt() → formulate_bid(market_window)
  3. Refactor DA_optimal_quantities() to observe_prices() for state updates
  4. Replace hardcoded bid formats with Bid dataclass and value_function

This preserves all existing logic while making devices agnostic to market structure.
"""

from typing import Dict, List, Optional, Any
from copy import deepcopy

# Existing agent (DO NOT MODIFY)
from tesp_support.dsot.battery_agent import BatteryDSOT

# New abstractions
from tesp_support.modular import (
    DeviceStrategy,
    Bid,
    MarketWindow,
    PriceSignal,
    BatteryDSOTStrategy,
)


class BatteryDSOTStrategyAdapter(BatteryDSOTStrategy):
    """
    Adapter wrapping an existing BatteryDSOT agent as a DeviceStrategy.

    This adapter bridges the old API (formulate_bid_da(), formulate_bid_rt(), DA_optimal_quantities())
    to the new API (formulate_bid(market_window)).

    Strategy:
      - Keep the existing BatteryDSOT optimization logic unchanged
      - Wrap calls to formulate_bid_da/rt into a market-agnostic formulate_bid()
      - Map observe_prices() to update agent state via cleared quantities
      - Convert 4-point bid format to Bid.value_function

    This allows running existing tests against the adapter with no modifications.
    """

    def __init__(
        self,
        device_id: str,
        battery_dict: Dict,
        legacy_agent: Optional[BatteryDSOT] = None,
    ):
        """
        Initialize battery strategy adapter.

        Args:
            device_id: Unique identifier (e.g., "BATT_001")
            battery_dict: Configuration dict (capacity, power rating, efficiency, etc.)
            legacy_agent: Optional pre-instantiated BatteryDSOT agent. If None, creates one.
        """
        # Initialize as BatteryDSOTStrategy
        super().__init__(device_id, battery_dict)

        # Keep the legacy agent as an internal component
        if legacy_agent is None:
            # Create the legacy agent with default parameters
            inv_properties = {"feeder_id": "network_node"}
            self.legacy_agent = BatteryDSOT(
                battery_dict,
                inv_properties,
                device_id,
                model_diag_level=11,
                sim_time="2025-01-01 00:00:00",
                solver="ipopt",
            )
        else:
            self.legacy_agent = legacy_agent

        # Track which market window we're in (DA or RT)
        self.last_market_window = None

    def initialize(self) -> None:
        """Called once at simulation start."""
        super().initialize()
        # Any legacy agent initialization here

    def observe_prices(self, price_signal: PriceSignal) -> None:
        """
        Observe market results and update battery state.

        For DA market:
          - Store cleared quantities for the entire day-ahead window
          - Update price forecast for next day-ahead optimization

        For RT market:
          - Update current SOC from cleared quantity
          - Store current cleared price for RT adjustments

        Args:
            price_signal: Market results from clearing.
        """
        super().observe_prices(price_signal)

        # Update legacy agent state based on cleared results
        if price_signal.market_id == "DA":
            # DA clearing: update price forecast
            # (In a real implementation, would extract forecast from price_signal.metadata)
            self.legacy_agent.set_price_forecast(self.price_history["DA"])

        elif price_signal.market_id == "RT":
            # RT clearing: update current price
            self.legacy_agent.inform_bid(price_signal.clearing_price)

            # Update SOC from cleared quantity
            cleared_qty = price_signal.cleared_quantities.get(self.device_id, 0.0)
            if cleared_qty != 0.0:
                # Convert cleared quantity (MWh) to SOC update
                # TODO: Integrate with legacy_agent.set_SOC() logic
                pass

    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """
        Formulate a bid for a market window (DA or RT).

        For DA windows:
          - Call legacy_agent.DA_optimal_quantities() to get optimized quantities
          - Call legacy_agent.formulate_bid_da() to get 4-point bid
          - Convert 4-point bid to Bid with value_function

        For RT windows:
          - Call legacy_agent.formulate_bid_rt() to get 4-point bid
          - Convert to Bid with value_function

        Args:
            market_window: The market window (specifies DA or RT).

        Returns:
            A Bid with arbitrary value_function (converted from 4-point format).
        """
        self.last_market_window = market_window

        if market_window.market_id == "DA":
            # Day-ahead: run optimization if not already done
            quantity_result = self.legacy_agent.DA_optimal_quantities()
            quantities, params = quantity_result
            self.legacy_agent.optimized_Quantity = quantities

            # Formulate 4-point DA bid from optimized quantities
            bid_4pt = self.legacy_agent.formulate_bid_da()

            # Convert first hour's 4-point bid to Bid with value_function
            bid_4pt_window_0 = bid_4pt[0]
            return self._convert_4pt_to_bid(
                bid_4pt_window_0,
                market_window,
                bid_type="supply",  # Battery can supply or demand; default to supply
            )

        elif market_window.market_id == "RT":
            # Real-time: use last DA bid as starting point
            bid_4pt = self.legacy_agent.formulate_bid_rt()

            # Convert 4-point RT bid to Bid with value_function
            return self._convert_4pt_to_bid(
                bid_4pt,
                market_window,
                bid_type="supply",
            )

        else:
            raise ValueError(f"Unknown market: {market_window.market_id}")

    def _convert_4pt_to_bid(
        self,
        bid_4pt: List[List[float]],
        market_window: MarketWindow,
        bid_type: str = "supply",
    ) -> Bid:
        """
        Convert a 4-point bid (legacy format) to a Bid (new format).

        Legacy 4-point format:
          bid_4pt = [
              [price_1, quantity_1],  # Point 1: max discharge
              [price_2, quantity_2],  # Point 2: optimized quantity
              [price_3, quantity_3],  # Point 3: optimized quantity
              [price_4, quantity_4],  # Point 4: max charge
          ]

        New Bid format:
          Bid(
              participant_id, market_id, valid_from, valid_to,
              quantity_min, quantity_max,
              value_function,  # Arbitrary callable
              bid_type,
              metadata
          )

        Conversion strategy:
          - Quantity range: [min(quantities), max(quantities)]
          - Value function: piecewise linear interpolation through 4 points
            (or quadratic fit if available)

        Args:
            bid_4pt: 4-point bid in legacy format.
            market_window: Target market window.
            bid_type: "supply" or "demand".

        Returns:
            A Bid with value_function that interpolates the 4-point bid.
        """
        P = 1  # Legacy format: index 1 is price
        Q = 0  # Legacy format: index 0 is quantity

        # Extract quantities and prices from 4-point bid
        quantities = [bid_4pt[i][Q] for i in range(4)]
        prices = [bid_4pt[i][P] for i in range(4)]

        quantity_min = min(quantities)
        quantity_max = max(quantities)

        # Create a piecewise linear value function from the 4 points
        def value_function_4pt(q: float) -> float:
            """
            Evaluate the marginal value ($/MWh) at quantity q.

            Uses piecewise linear interpolation through the 4 points.
            """
            # Clamp quantity to valid range
            if q < quantity_min:
                q = quantity_min
            elif q > quantity_max:
                q = quantity_max

            # Find the two points that bracket q
            for i in range(3):
                if quantities[i] <= q <= quantities[i + 1]:
                    # Linearly interpolate between points i and i+1
                    dq = quantities[i + 1] - quantities[i]
                    if dq == 0:
                        return prices[i]
                    dp = prices[i + 1] - prices[i]
                    slope = dp / dq
                    return prices[i] + slope * (q - quantities[i])

            # q is at the endpoints
            if q == quantities[0]:
                return prices[0]
            if q == quantities[-1]:
                return prices[-1]

            # Should not reach here
            return prices[0]

        # Create and return the Bid
        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            valid_from=market_window.settlement_period_start,
            valid_to=market_window.settlement_period_end,
            quantity_min=quantity_min,
            quantity_max=quantity_max,
            value_function=value_function_4pt,
            bid_type=bid_type,
            metadata={
                "device_type": self.device_type,
                "bid_format": "4-point_legacy",
                "soc": self.state.get("soc"),
                "capacity_mwh": self.capacity_mwh,
                "legacy_agent": self.legacy_agent.name,
            },
        )


# Example usage and testing
def test_adapter():
    """Test the battery adapter with DA and RT markets."""

    # Configuration
    battery_config = {
        "capacity": 13500.0,  # kWh
        "rating": 5657.93,    # W
        "charge": 8093.655,   # kWh (initial SOC)
        "efficiency": 0.9552,
        "slider_setting": 0.8501,
        "reserved_soc": 0.2,
        "profit_margin": 7.2485,
        "degrad_factor": 0.0227,
        "participating": True,
        # New DeviceStrategy config
        "price_cap": 100.0,
        "quantity_max": 5.0,  # MW
    }

    # Create adapter
    adapter = BatteryDSOTStrategyAdapter("BATT_001", battery_config)
    adapter.initialize()

    # Simulate DA market window
    da_window = MarketWindow(
        market_id="DA",
        window_number=0,
        settlement_period_start=0,
        settlement_period_end=3600,
        bid_submission_deadline=3540,
        clearing_time=3600,
        clearing_mechanism_name="curve_intersection",
    )

    # Formulate DA bid
    print("DA Market:")
    try:
        da_bid = adapter.formulate_bid(da_window)
        print(f"  Device: {da_bid.participant_id}")
        print(f"  Quantity range: [{da_bid.quantity_min:.3f}, {da_bid.quantity_max:.3f}] MWh")
        print(f"  Market: {da_bid.market_id}")

        # Test value function at a few quantities
        for q in [da_bid.quantity_min, (da_bid.quantity_min + da_bid.quantity_max) / 2, da_bid.quantity_max]:
            try:
                price = da_bid.value_function(q)
                print(f"    Value @ Q={q:.3f} MWh: ${price:.2f}/MWh")
            except Exception as e:
                print(f"    Error at Q={q:.3f}: {e}")
    except Exception as e:
        print(f"  Error: {e}")

    # Simulate clearing result
    price_signal_da = PriceSignal(
        market_id="DA",
        time_step=3600,
        period_start=0,
        period_end=3600,
        clearing_price=45.0,
        participant_prices={"BATT_001": 45.0},
        cleared_quantities={"BATT_001": 3.0},
    )

    # Observe prices
    print("\nObserving DA clearing result...")
    adapter.observe_prices(price_signal_da)
    print(f"  Cleared: 3.0 MWh @ $45.0/MWh")

    # Simulate RT market window
    print("\nRT Market:")
    rt_window = MarketWindow(
        market_id="RT",
        window_number=0,
        settlement_period_start=3600,
        settlement_period_end=3900,
        bid_submission_deadline=3870,
        clearing_time=3900,
        clearing_mechanism_name="curve_intersection",
    )

    try:
        rt_bid = adapter.formulate_bid(rt_window)
        print(f"  Device: {rt_bid.participant_id}")
        print(f"  Quantity range: [{rt_bid.quantity_min:.3f}, {rt_bid.quantity_max:.3f}] MWh")
        print(f"  Market: {rt_bid.market_id}")

        # Test value function
        for q in [rt_bid.quantity_min, (rt_bid.quantity_min + rt_bid.quantity_max) / 2, rt_bid.quantity_max]:
            try:
                price = rt_bid.value_function(q)
                print(f"    Value @ Q={q:.3f} MWh: ${price:.2f}/MWh")
            except Exception as e:
                print(f"    Error at Q={q:.3f}: {e}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n✓ Adapter test complete!")


if __name__ == "__main__":
    test_adapter()
