"""
Example: Using the modular market protocol and device strategy abstractions.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This example demonstrates:
  1. Instantiating a DSOTMarketProtocol with DSOT timing parameters
  2. Creating device strategies (HVAC, Battery, EV)
  3. Generating market windows for a time period
  4. Devices formulating bids for each window
  5. Clearing results being published to participants

This is a proof-of-concept showing how the abstractions decouple market design,
clearing logic, and device optimization.

Run this to verify that all interfaces work together:
    cd C:\Users\kerb930\Documents\Transactive Energy\Community Engagement\tesp\tesp
    python src/tesp_support/tesp_support/modular/example_usage.py
"""

from datetime import datetime
from src.tesp_support.tesp_support.modular import (
    DSOTMarketProtocol,
    HVACDSOTStrategy,
    BatteryDSOTStrategy,
    EVDSOTStrategy,
    PriceSignal,
)


def main():
    """Demonstrate the modular abstractions in action."""
    
    print("=" * 70)
    print("TESP Modular Market Protocol - Example Usage")
    print("=" * 70)
    
    # =========================================================================
    # Step 1: Define the market protocol (DSOT: DA + RT)
    # =========================================================================
    print("\n[Step 1] Instantiate DSOT Market Protocol")
    print("-" * 70)
    
    market_protocol = DSOTMarketProtocol(
        da_period_seconds=3600,           # 1 hour
        rt_period_seconds=300,            # 5 minutes
        da_bid_lead_time_seconds=60,      # DA bids due 60 sec before clearing
        rt_bid_lead_time_seconds=30,      # RT bids due 30 sec before clearing
        simulation_start_time=datetime.now(),
    )
    print(f"Market protocol: {market_protocol.__class__.__name__}")
    print(f"  - DA period: {market_protocol.da_period_seconds} sec (hourly)")
    print(f"  - RT period: {market_protocol.rt_period_seconds} sec (5-min)")
    print(f"  - DA bid deadline: {market_protocol.da_bid_lead_time_seconds} sec before clearing")
    print(f"  - RT bid deadline: {market_protocol.rt_bid_lead_time_seconds} sec before clearing")
    
    # =========================================================================
    # Step 2: Create device strategies
    # =========================================================================
    print("\n[Step 2] Create Device Strategies")
    print("-" * 70)
    
    hvac_config = {
        "price_cap": 100.0,
        "quantity_max": 5.0,
        "setpoint_heating": 70.0,
        "setpoint_cooling": 75.0,
        "deadband": 2.0,
        "ramp_limit": 2.0,
    }
    hvac = HVACDSOTStrategy("HVAC_001", hvac_config)
    print(f"Created: {hvac}")
    
    battery_config = {
        "capacity_mwh": 10.0,
        "power_rating_mw": 5.0,
        "efficiency": 0.90,
        "soc_min": 0.2,
        "soc_max": 0.95,
        "price_cap": 100.0,
    }
    battery = BatteryDSOTStrategy("BATT_001", battery_config)
    print(f"Created: {battery}")
    
    ev_config = {
        "battery_capacity_kwh": 60.0,
        "charger_rating_kw": 7.0,
        "efficiency": 0.85,
        "arrival_time_sec": 14400,        # 4 PM
        "departure_time_sec": 28800,      # 8 AM next day
        "current_soc": 0.3,
        "price_cap": 50.0,
    }
    ev = EVDSOTStrategy("EV_001", ev_config)
    print(f"Created: {ev}")
    
    devices = [hvac, battery, ev]
    
    # =========================================================================
    # Step 3: Generate market windows for a 24-hour period
    # =========================================================================
    print("\n[Step 3] Generate Market Windows")
    print("-" * 70)
    
    period_start = 0
    period_end = 86400  # 24 hours in seconds
    
    windows = market_protocol.settlement_structure(period_start, period_end)
    print(f"Generated {len(windows)} market windows for 24 hours:")
    print(f"  - DA windows: {sum(1 for w in windows if w.market_id == 'DA')}")
    print(f"  - RT windows: {sum(1 for w in windows if w.market_id == 'RT')}")
    
    # Show first 5 windows
    print("\nFirst 5 market windows:")
    for i, window in enumerate(windows[:5]):
        print(
            f"  [{i}] {window.market_id} window #{window.window_number}: "
            f"clear @ {window.clearing_time}s, bid deadline @ {window.bid_submission_deadline}s"
        )
    
    # =========================================================================
    # Step 4: Devices formulate bids for first DA window
    # =========================================================================
    print("\n[Step 4] Devices Formulate Bids")
    print("-" * 70)
    
    da_windows = [w for w in windows if w.market_id == "DA"]
    if da_windows:
        first_da_window = da_windows[0]
        print(f"First DA market window:")
        print(f"  Settlement period: {first_da_window.settlement_period_start}s - {first_da_window.settlement_period_end}s")
        print(f"  Bid deadline: {first_da_window.bid_submission_deadline}s")
        print(f"  Clearing time: {first_da_window.clearing_time}s")
        print(f"\nDevice bids for this DA window:")
        
        for device in devices:
            try:
                bid = device.formulate_bid(first_da_window)
                print(
                    f"  - {device.device_id:12s}: Q_range=[{bid.quantity_min:.3f}, {bid.quantity_max:.3f}] MWh, "
                    f"valid {bid.valid_from}s-{bid.valid_to}s, type={bid.bid_type}"
                )
                
                # Show value function at a few quantities
                q_test = bid.quantity_max / 2.0
                value = bid.value_function(q_test)
                print(f"                 Value @ Q={q_test:.3f}: ${value:.2f}/MWh")
            except ValueError as e:
                print(f"  - {device.device_id:12s}: {e}")
    
    # =========================================================================
    # Step 5: Simulate price feedback (clearing results)
    # =========================================================================
    print("\n[Step 5] Clearing Results and Price Feedback")
    print("-" * 70)
    
    # Simulate clearing results (in real system, these come from retail_market.clear_market_*)
    clearing_result = {
        "HVAC_001": (2.0, 45.0),       # (cleared_qty_MWh, price_$/MWh)
        "BATT_001": (3.5, 45.0),
        "EV_001": (1.5, 45.0),
    }
    
    # Convert to PriceSignal for feedback
    price_signal = market_protocol.publish_results(first_da_window, clearing_result)
    print(f"Price signal from market clearing:")
    print(f"  Market: {price_signal.market_id}")
    print(f"  Clearing price: ${price_signal.clearing_price:.2f}/MWh")
    print(f"  Period: {price_signal.period_start}s - {price_signal.period_end}s")
    print(f"  Cleared quantities:")
    for participant_id, qty in price_signal.cleared_quantities.items():
        price = price_signal.participant_prices.get(participant_id, price_signal.clearing_price)
        print(f"    {participant_id}: {qty:.3f} MWh @ ${price:.2f}/MWh")
    
    # =========================================================================
    # Step 6: Devices observe prices and update state
    # =========================================================================
    print("\n[Step 6] Devices Observe Prices")
    print("-" * 70)
    
    for device in devices:
        device.observe_prices(price_signal)
    
    print("Devices have updated their price expectations and state.")
    print(f"  HVAC price history: {hvac.price_history['DA']}")
    print(f"  Battery state: {battery.state}")
    print(f"  EV state: {ev.state}")
    
    # =========================================================================
    # Step 7: Demonstrate clearing mechanism selection
    # =========================================================================
    print("\n[Step 7] Clearing Mechanism Selection")
    print("-" * 70)
    
    da_window = da_windows[0] if da_windows else None
    if da_window:
        clearing_mech = market_protocol.get_clearing_mechanism(da_window)
        print(f"Clearing mechanism for {da_window.market_id} window: {clearing_mech.__class__.__name__}")
        print(f"  (Currently a placeholder; will integrate retail_market.clear_market_*() logic)")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
The modular architecture achieves separation of concerns:

1. Market Protocol (DSOTMarketProtocol)
   - Defines settlement structure and timing
   - Is data-driven (list of MarketWindow), not hardcoded flow control
   - Clearing mechanism is pluggable

2. Device Strategies (HVACDSOTStrategy, BatteryDSOTStrategy, etc.)
   - Encapsulate device physics and optimization logic
   - Independent of market protocol details
   - Each device formulates its own bid for a given market window

3. Clearing Mechanisms (DSOTCurveIntersectionClearing, etc.)
   - Implements a specific clearing algorithm
   - Takes a list of Bid objects
   - Returns cleared quantities and prices per participant

4. Price Signals (PriceSignal dataclass)
   - Feedback from market to devices
   - Contains clearing results, prices, and metadata
   - Devices use this to update state and refine future bids

Benefits for market design experimentation:
  ✓ New market structure = new MarketProtocol subclass (e.g., ThreeSettlementMarketProtocol)
  ✓ New bidding curve = new value_function (e.g., piecewise linear, step function)
  ✓ New clearing algorithm = new ClearingMechanism subclass (e.g., DoubleAuctionClearing)
  ✓ Device physics never changes; optimization logic is decoupled
  ✓ HELICS federation structure (player, TSO, substation) is independent of market design

Next steps:
  1. Extract retail_market.clear_market_DA/RT() into DSOTCurveIntersectionClearing.clear()
  2. Adapt existing device agents to inherit from DSOTDeviceStrategy
  3. Refactor substation.py to use MarketProtocol.settlement_structure()
  4. Add HELICS transport layer for Bid and PriceSignal serialization
    """)


if __name__ == "__main__":
    main()
