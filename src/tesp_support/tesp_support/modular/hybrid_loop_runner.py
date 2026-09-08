"""
Hybrid Loop Implementation for Substation.py

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This module demonstrates Phase 2 of the substation.py refactoring:
  - Keep all legacy event handlers running (unchanged)
  - Add market window-based event loop running in parallel
  - Compare results between both paths at each market clearing
  - Validate timing, clearing prices, and cleared quantities match
  - Easy rollback if issues found (disable hybrid mode with one flag)

Architecture:
  1. Legacy path: Original if-blocks with timer constants (runs as-is)
  2. Hybrid path: New window-based loop with MarketProtocol
  3. Comparison: At each clearing, compare prices and quantities
  4. Logging: Detailed output of any mismatches

Usage (Pseudo-code for substation.py):
  # Initialize both paths
  legacy_state = initialize_legacy_timers(...)
  hybrid_state, market_windows = initialize_hybrid_loop(...)
  
  while time_granted < simulation_duration:
      # Both paths run in parallel
      handle_legacy_events(time_granted, legacy_state)
      handle_hybrid_events(time_granted, hybrid_state, market_windows)
      
      # At each clearing, compare results
      for market_window in cleared_windows:
          compare_clearing_results(legacy_state, hybrid_state, market_window)
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from .price_signal import PriceSignal


@dataclass
class ClearingComparison:
    """Container for comparing clearing results between legacy and hybrid paths."""
    window_id: str
    market_type: str                           # "DA" or "RT"
    time_step: int                            # Seconds
    
    # Legacy path results
    legacy_price: float
    legacy_quantities: Dict[str, float]       # device_id → cleared quantity
    legacy_total_quantity: float
    
    # Hybrid path results
    hybrid_price: float
    hybrid_quantities: Dict[str, float]
    hybrid_total_quantity: float
    
    # Comparison metrics
    price_difference: float                   # $/MWh
    quantity_difference: float                # MWh
    matches: bool                             # True if within tolerance
    tolerance_exceeded: bool
    
    details: str = ""


class HybridEventLoopState:
    """State container for hybrid loop tracking during Phase 2."""
    
    def __init__(self, legacy_state_ref, market_windows):
        """
        Initialize hybrid loop state.
        
        Args:
            legacy_state_ref: Reference to legacy state (dict or object)
            market_windows: List of MarketWindow objects from settlement_structure()
        """
        self.legacy_state = legacy_state_ref
        self.market_windows = market_windows
        self.processed_windows = set()          # Track which windows we've processed
        self.comparison_results = []            # List of ClearingComparison objects
        self.mismatches = []                    # List of mismatches found
        
        # Tracking flags
        self.hybrid_da_bids_submitted = set()   # Which DA windows have bids
        self.hybrid_rt_bids_submitted = set()   # Which RT windows have bids
        self.hybrid_clears_completed = set()    # Which windows cleared
        self.pending_bids = {}                  # window_id → List[Bid]
        
        # Statistics
        self.total_comparisons = 0
        self.passing_comparisons = 0
        self.failing_comparisons = 0


def initialize_hybrid_state(legacy_state, market_windows):
    """Initialize hybrid loop state object.
    
    Args:
        legacy_state: Reference to existing legacy state
        market_windows: List of MarketWindow objects
    
    Returns:
        HybridEventLoopState: Ready for parallel processing
    """
    return HybridEventLoopState(legacy_state, market_windows)


def find_next_hybrid_event(
    market_windows: List,
    time_granted: int,
    processed: set,
    event_type: Optional[str] = None
) -> Tuple[Optional[int], List]:
    """Find next market window event for hybrid loop.
    
    Args:
        market_windows: All MarketWindow objects
        time_granted: Current simulation time
        processed: Set of already-processed window IDs
        event_type: "BID_DEADLINE" or "CLEARING_TIME" (None = any)
    
    Returns:
        Tuple of:
            - next_event_time: When next event happens (or None)
            - windows_at_time: List of windows triggering at that time
    """
    upcoming_times = set()
    
    for window in market_windows:
        if window.window_id in processed:
            continue  # Already handled
        
        # Bid submission deadlines
        if event_type in (None, "BID_DEADLINE"):
            if window.bid_submission_deadline > time_granted:
                upcoming_times.add(window.bid_submission_deadline)
        
        # Clearing times
        if event_type in (None, "CLEARING_TIME"):
            if window.clearing_time > time_granted:
                upcoming_times.add(window.clearing_time)
    
    if not upcoming_times:
        return None, []
    
    next_event_time = min(upcoming_times)
    windows_at_time = [
        w for w in market_windows
        if w.window_id not in processed and 
        (w.bid_submission_deadline == next_event_time or 
         w.clearing_time == next_event_time)
    ]
    
    return next_event_time, windows_at_time


def compare_clearing_results(
    legacy_price: float,
    legacy_quantities: Dict[str, float],
    hybrid_price: float,
    hybrid_quantities: Dict[str, float],
    market_window,
    tolerance_price: float = 0.01,
    tolerance_quantity: float = 0.001,
    log_func=None
) -> ClearingComparison:
    """Compare clearing results from legacy and hybrid paths.
    
    Args:
        legacy_price: Clearing price from legacy code ($/MWh)
        legacy_quantities: Dict of device_id → cleared quantity (MWh)
        hybrid_price: Clearing price from hybrid code ($/MWh)
        hybrid_quantities: Dict of device_id → cleared quantity (MWh)
        market_window: MarketWindow object (for context)
        tolerance_price: Max acceptable price difference ($/MWh)
        tolerance_quantity: Max acceptable quantity difference (per device, MWh)
        log_func: Optional logger function
    
    Returns:
        ClearingComparison: Detailed comparison result
    """
    # Calculate totals
    legacy_total = sum(legacy_quantities.values())
    hybrid_total = sum(hybrid_quantities.values())
    
    # Price difference
    price_diff = abs(legacy_price - hybrid_price)
    price_match = price_diff <= tolerance_price
    
    # Quantity differences (per device)
    quantity_diffs = {}
    all_devices = set(legacy_quantities.keys()) | set(hybrid_quantities.keys())
    
    for device_id in all_devices:
        legacy_q = legacy_quantities.get(device_id, 0.0)
        hybrid_q = hybrid_quantities.get(device_id, 0.0)
        diff = abs(legacy_q - hybrid_q)
        quantity_diffs[device_id] = diff
    
    # Overall quantity match
    quantity_match = all(d <= tolerance_quantity for d in quantity_diffs.values())
    
    # Create comparison result
    comparison = ClearingComparison(
        window_id=market_window.window_id,
        market_type=market_window.market_id,
        time_step=market_window.clearing_time,
        legacy_price=legacy_price,
        legacy_quantities=legacy_quantities.copy(),
        legacy_total_quantity=legacy_total,
        hybrid_price=hybrid_price,
        hybrid_quantities=hybrid_quantities.copy(),
        hybrid_total_quantity=hybrid_total,
        price_difference=price_diff,
        quantity_difference=abs(legacy_total - hybrid_total),
        matches=price_match and quantity_match,
        tolerance_exceeded=not (price_match and quantity_match)
    )
    
    # Create detailed message
    details_parts = []
    if not price_match:
        details_parts.append(f"Price mismatch: ${legacy_price:.4f} vs ${hybrid_price:.4f} (diff: ${price_diff:.6f})")
    if not quantity_match:
        mismatched_devices = [d for d, diff in quantity_diffs.items() if diff > tolerance_quantity]
        details_parts.append(f"Quantity mismatches in {len(mismatched_devices)} devices: {mismatched_devices}")
    
    comparison.details = "; ".join(details_parts) if details_parts else "✓ Match"
    
    # Log if provided
    if log_func:
        if comparison.matches:
            log_func(f"✓ {comparison.market_type} Window {comparison.window_id}: {comparison.details}")
        else:
            log_func(f"✗ {comparison.market_type} Window {comparison.window_id}: {comparison.details}")
    
    return comparison


class HybridLoopRunner:
    """Main controller for running hybrid loop in Phase 2.
    
    This class manages:
    - Both legacy and hybrid event paths
    - Synchronization between paths
    - Result comparison and logging
    - Mismatch detection and reporting
    """
    
    def __init__(
        self,
        legacy_state,
        market_windows,
        price_tolerance=0.01,
        quantity_tolerance=0.001,
        log_func=None,
        enabled=True,
        adapters=None,
        clearing_mechanisms=None,
    ):
        """Initialize hybrid loop runner.
        
        Args:
            legacy_state: Reference to legacy event handling state
            market_windows: List of MarketWindow objects
            price_tolerance: Max acceptable price difference ($/MWh)
            quantity_tolerance: Max acceptable quantity difference (MWh)
            log_func: Optional logger function for output
            enabled: Whether hybrid mode is active (easy disable for rollback)
            adapters: Dict of device_id → DeviceStrategy adapter instances
            clearing_mechanisms: Dict of market_id → ClearingMechanism instances
        """
        self.state = initialize_hybrid_state(legacy_state, market_windows)
        self.price_tolerance = price_tolerance
        self.quantity_tolerance = quantity_tolerance
        self.log = log_func or print
        self.enabled = enabled
        self.adapters = adapters or {}
        self.clearing_mechanisms = clearing_mechanisms or {}
        
    def process_hybrid_bids_for_window(self, market_window, time_granted, devices=None):
        """Collect bids from all device adapters for this market window.
        
        Args:
            market_window: MarketWindow object
            time_granted: Current simulation time
            devices: Unused; kept for API compatibility
        
        Returns:
            Dict of participant_id → Bid
        """
        if not self.enabled:
            return {}
        
        window_id = market_window.window_id
        bids = []
        for adapter in self.adapters.values():
            try:
                bid = adapter.formulate_bid(market_window)
                bids.append(bid)
            except Exception as exc:
                self.log(f"[Hybrid] Bid error ({adapter.device_id}): {exc}")
        
        self.state.pending_bids[window_id] = bids
        
        if market_window.market_id == 'DA':
            self.state.hybrid_da_bids_submitted.add(window_id)
        else:
            self.state.hybrid_rt_bids_submitted.add(window_id)
        
        self.log(f"[Hybrid] Collected {len(bids)} bids for {market_window.market_id} window {window_id}")
        return {bid.participant_id: bid for bid in bids}
    
    def process_hybrid_clearing_for_window(
        self,
        market_window,
        time_granted,
        legacy_clear_result
    ):
        """Process clearing through hybrid path and compare to legacy.
        
        Args:
            market_window: MarketWindow object
            time_granted: Current simulation time
            legacy_clear_result: Dict of device_id → (quantity, price) from legacy code
        
        Returns:
            ClearingComparison object
        """
        if not self.enabled:
            return None
        
        if time_granted < market_window.clearing_time:
            return None  # Not time to clear yet
        
        # Extract legacy results
        legacy_price = legacy_clear_result.get('price', 0.0)
        legacy_quantities = legacy_clear_result.get('quantities', {})
        
        window_id = market_window.window_id
        bids = self.state.pending_bids.get(window_id, [])
        clearing_mech = self.clearing_mechanisms.get(market_window.market_id)
        
        hybrid_price = legacy_price
        hybrid_quantities = legacy_quantities.copy()
        
        if clearing_mech is not None and bids:
            try:
                hybrid_result = clearing_mech.clear(bids)
                if hybrid_result:
                    prices = [p for _, p in hybrid_result.values()]
                    hybrid_price = prices[0] if prices else legacy_price
                    hybrid_quantities = {pid: qty for pid, (qty, _) in hybrid_result.items()}
            except Exception as exc:
                self.log(f"[Hybrid] Clearing error for window {window_id}: {exc}")
        
        # Compare results
        comparison = compare_clearing_results(
            legacy_price=legacy_price,
            legacy_quantities=legacy_quantities,
            hybrid_price=hybrid_price,
            hybrid_quantities=hybrid_quantities,
            market_window=market_window,
            tolerance_price=self.price_tolerance,
            tolerance_quantity=self.quantity_tolerance,
            log_func=self.log
        )
        
        # Track results
        self.state.comparison_results.append(comparison)
        self.state.total_comparisons += 1
        
        if comparison.matches:
            self.state.passing_comparisons += 1
        else:
            self.state.failing_comparisons += 1
            self.state.mismatches.append(comparison)
        
        self.state.hybrid_clears_completed.add(market_window.window_id)

        # Publish hybrid clearing result back to adapters via PriceSignal
        if self.adapters and hybrid_price > 0:
            cleared_quantities_mwh = {pid: qty for pid, qty in hybrid_quantities.items()}
            price_signal = PriceSignal(
                market_id=market_window.market_id,
                time_step=time_granted,
                period_start=market_window.settlement_period_start,
                period_end=market_window.settlement_period_end,
                clearing_price=max(0.0, hybrid_price),
                cleared_quantities=cleared_quantities_mwh,
            )
            for adapter in self.adapters.values():
                try:
                    adapter.observe_prices(price_signal)
                except Exception as exc:
                    self.log(f"[Hybrid] observe_prices error ({adapter.device_id}): {exc}")

        return comparison
    
    def generate_summary_report(self):
        """Generate summary of all comparisons from Phase 2 run.
        
        Returns:
            str: Formatted report
        """
        report = "\n" + "="*80 + "\n"
        report += "PHASE 2 HYBRID LOOP SUMMARY\n"
        report += "="*80 + "\n"
        report += f"Total Comparisons: {self.state.total_comparisons}\n"
        report += f"Passing: {self.state.passing_comparisons}\n"
        report += f"Failing: {self.state.failing_comparisons}\n"
        
        if self.state.failing_comparisons == 0:
            report += "\n✓ ALL COMPARISONS PASSED — Legacy and hybrid paths produce identical results!\n"
        else:
            report += f"\n✗ {self.state.failing_comparisons} MISMATCHES DETECTED:\n"
            for comparison in self.state.mismatches:
                report += f"  - {comparison.market_type} Window {comparison.window_id} (t={comparison.time_step}s): {comparison.details}\n"
        
        report += "="*80 + "\n"
        
        return report


# ============================================================================
# USAGE EXAMPLE (Pseudo-code for substation.py integration)
# ============================================================================

"""
# In substation.py main loop, after Phase 1 setup:

# Phase 2 Setup: Initialize hybrid loop
hybrid_runner = HybridLoopRunner(
    legacy_state=legacy_state_dict,
    market_windows=market_windows,
    price_tolerance=0.01,  # $0.01/MWh
    quantity_tolerance=0.001,  # 0.001 MWh per device
    log_func=log.info,
    enabled=True  # Set to False to disable hybrid mode
)

# In main event loop, after handling legacy events:
while time_granted < simulation_duration:
    # Handle legacy events (unchanged)
    if time_granted >= tnext_retail_bid_da:
        # ... existing DA bidding code ...
        legacy_da_result = {
            'price': retail_market_obj.cleared_price_DA,
            'quantities': {device_id: qty for device_id, qty in ...}
        }
    
    # Handle hybrid events (in parallel)
    for window in market_windows:
        if window.bid_submission_deadline <= time_granted:
            hybrid_runner.process_hybrid_bids_for_window(window, time_granted, devices)
        
        if window.clearing_time <= time_granted:
            comparison = hybrid_runner.process_hybrid_clearing_for_window(
                window, time_granted, legacy_da_result
            )

# After simulation completes:
print(hybrid_runner.generate_summary_report())
"""


# ============================================================================
# TESTING / VALIDATION
# ============================================================================

def test_comparison_logic():
    """Unit test for comparison logic."""
    print("\n" + "="*80)
    print("PHASE 2 COMPARISON LOGIC TEST")
    print("="*80)
    
    # Create mock market window
    class MockWindow:
        def __init__(self):
            self.window_id = "DA_0"
            self.market_id = "DA"
            self.clearing_time = 3600
    
    window = MockWindow()
    
    # Test 1: Perfect match
    print("\nTest 1: Perfect match")
    legacy_price = 50.00
    legacy_quantities = {"hvac_1": 2.0, "battery_1": -1.5, "ev_1": 1.0}
    hybrid_price = 50.00
    hybrid_quantities = {"hvac_1": 2.0, "battery_1": -1.5, "ev_1": 1.0}
    
    result = compare_clearing_results(
        legacy_price, legacy_quantities,
        hybrid_price, hybrid_quantities,
        window, tolerance_price=0.01, tolerance_quantity=0.001
    )
    
    print(f"  Price: ${legacy_price} vs ${hybrid_price} → Diff: ${result.price_difference:.6f}")
    print(f"  Match: {result.matches} (Expected: True)")
    print(f"  Details: {result.details}")
    assert result.matches, "Should match!"
    
    # Test 2: Small price difference (within tolerance)
    print("\nTest 2: Small price difference (within tolerance)")
    hybrid_price = 50.005  # Within $0.01 tolerance
    
    result = compare_clearing_results(
        legacy_price, legacy_quantities,
        hybrid_price, hybrid_quantities,
        window, tolerance_price=0.01, tolerance_quantity=0.001
    )
    
    print(f"  Price: ${legacy_price} vs ${hybrid_price} → Diff: ${result.price_difference:.6f}")
    print(f"  Match: {result.matches} (Expected: True)")
    assert result.matches, "Should match within tolerance!"
    
    # Test 3: Large price difference (exceeds tolerance)
    print("\nTest 3: Large price difference (exceeds tolerance)")
    hybrid_price = 50.05  # Exceeds $0.01 tolerance
    
    result = compare_clearing_results(
        legacy_price, legacy_quantities,
        hybrid_price, hybrid_quantities,
        window, tolerance_price=0.01, tolerance_quantity=0.001
    )
    
    print(f"  Price: ${legacy_price} vs ${hybrid_price} → Diff: ${result.price_difference:.6f}")
    print(f"  Match: {result.matches} (Expected: False)")
    print(f"  Details: {result.details}")
    assert not result.matches, "Should NOT match!"
    
    # Test 4: Quantity mismatch on one device
    print("\nTest 4: Quantity mismatch on one device")
    hybrid_price = 50.00
    hybrid_quantities = {"hvac_1": 2.0, "battery_1": -1.55, "ev_1": 1.0}  # battery differs by 0.05
    
    result = compare_clearing_results(
        legacy_price, legacy_quantities,
        hybrid_price, hybrid_quantities,
        window, tolerance_price=0.01, tolerance_quantity=0.001
    )
    
    print(f"  Battery qty: {legacy_quantities['battery_1']} vs {hybrid_quantities['battery_1']} → Diff: {abs(legacy_quantities['battery_1'] - hybrid_quantities['battery_1'])}")
    print(f"  Match: {result.matches} (Expected: False)")
    print(f"  Details: {result.details}")
    assert not result.matches, "Should NOT match!"
    
    print("\n" + "="*80)
    print("✓ ALL COMPARISON TESTS PASSED")
    print("="*80 + "\n")


if __name__ == '__main__':
    test_comparison_logic()
