"""
Parallel Market Protocol Implementation for Substation.py

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This module demonstrates Phase 1 of the substation.py refactoring:
  - Initialize DSOTMarketProtocol alongside existing timers
  - Generate settlement_structure for entire simulation
  - Validate timing matches legacy timers
  - No changes to existing event handlers or clearing logic

Usage:
  1. Add this code to substation.py after line ~620 (after market initialization)
  2. Run substation with both legacy timers and market protocol
  3. Verify legacy test suite still passes
  4. Compare window timing with legacy timer constants
  5. Once validated, proceed to Phase 2 (hybrid loop) and Phase 3 (full refactoring)
"""

from typing import List, Optional, Tuple
from datetime import datetime

# Import the market protocol (assuming it's already in tesp_support.modular)
# from tesp_support.modular import DSOTMarketProtocol, MarketWindow


def initialize_market_protocol_phase1(
    retail_period_da: int,
    retail_period_rt: int,
    simulation_duration: int,
    log: object = None
) -> Tuple[object, List[object]]:
    """Phase 1: Initialize DSOTMarketProtocol and generate settlement structure.
    
    This function runs alongside existing timer logic with NO modifications.
    It's a dry-run to validate the new architecture before full refactoring.
    
    Args:
        retail_period_da: Day-ahead period in seconds (default: 3600 = 1 hour)
        retail_period_rt: Real-time period in seconds (default: 300 = 5 minutes)
        simulation_duration: Total simulation duration in seconds
        log: Logger object (optional, for debug output)
    
    Returns:
        Tuple of:
            - market_protocol: DSOTMarketProtocol instance
            - market_windows: List of MarketWindow objects for entire simulation
    
    Example (insert after line ~620 in substation.py):
        # Initialize legacy timers (UNCHANGED)
        tnext_retail_bid_rt = retail_period_rt - 30 + retail_period_da * 1
        tnext_retail_bid_da = retail_period_da - 60
        # ... (all other timers as before) ...
        
        # NEW: Initialize market protocol (Phase 1)
        market_protocol, market_windows = initialize_market_protocol_phase1(
            retail_period_da, retail_period_rt, simulation_duration, log
        )
    """
    # Import here to avoid circular dependencies
    try:
        from tesp_support.modular import DSOTMarketProtocol
    except ImportError:
        if log:
            log.warning("Could not import DSOTMarketProtocol; Phase 1 setup skipped")
        return None, []
    
    if log:
        log.info("=== PHASE 1: MARKET PROTOCOL INITIALIZATION ===")
        log.info(f"  DA period: {retail_period_da} sec ({retail_period_da/3600:.1f} hours)")
        log.info(f"  RT period: {retail_period_rt} sec ({retail_period_rt/60:.1f} minutes)")
        log.info(f"  Simulation duration: {simulation_duration} sec ({simulation_duration/3600:.1f} hours)")
    
    # Create market protocol with DSOT timing
    market_protocol = DSOTMarketProtocol(
        da_period_seconds=retail_period_da,
        rt_period_seconds=retail_period_rt,
        da_bid_lead_time_seconds=60,  # Bid 60 sec before DA clearing
        rt_bid_lead_time_seconds=30,  # Bid 30 sec before RT clearing
    )
    
    # Generate all market windows for entire simulation
    market_windows = market_protocol.settlement_structure(0, simulation_duration)
    
    if log:
        log.info(f"Generated {len(market_windows)} market windows:")
        
        # Count by market type
        da_windows = [w for w in market_windows if w.market_id == 'DA']
        rt_windows = [w for w in market_windows if w.market_id == 'RT']
        log.info(f"  - Day-Ahead (DA): {len(da_windows)} windows")
        log.info(f"  - Real-Time (RT): {len(rt_windows)} windows")
        
        # Show first few windows
        log.info(f"  First 5 windows:")
        for i, w in enumerate(market_windows[:5]):
            log.info(f"    [{i}] {w.market_id} window {w.window_number}:")
            log.info(f"        Settlement: {w.settlement_period_start}s → {w.settlement_period_end}s")
            log.info(f"        Bid deadline: {w.bid_submission_deadline}s")
            log.info(f"        Clearing time: {w.clearing_time}s")
    
    return market_protocol, market_windows


def validate_market_windows_against_legacy_timers(
    market_windows: List[object],
    retail_period_da: int,
    retail_period_rt: int,
    log: object = None
) -> bool:
    """Phase 1: Validate that market windows match legacy timer timing.
    
    Compares the generated market windows against the expected legacy timer
    relationships to ensure architectural equivalence.
    
    Args:
        market_windows: List of MarketWindow objects from settlement_structure()
        retail_period_da: DA period from legacy config
        retail_period_rt: RT period from legacy config
        log: Logger object (optional)
    
    Returns:
        bool: True if all validations pass, False otherwise
    
    Example (insert in main loop after Phase 1 setup):
        if not validate_market_windows_against_legacy_timers(market_windows, retail_period_da, retail_period_rt, log):
            log.error("Market window validation failed; aborting")
            return
    """
    if log:
        log.info("=== PHASE 1: MARKET WINDOW VALIDATION ===")
    
    all_valid = True
    
    # Separate by market type
    da_windows = [w for w in market_windows if w.market_id == 'DA']
    rt_windows = [w for w in market_windows if w.market_id == 'RT']
    
    # Validation 1: DA window count
    # Legacy: One DA window per hour
    expected_da_count = 24  # First 24 hours
    actual_da_24h = len([w for w in da_windows if w.clearing_time < 86400])
    if actual_da_24h != expected_da_count:
        if log:
            log.error(f"DA window count mismatch: expected {expected_da_count}, got {actual_da_24h}")
        all_valid = False
    else:
        if log:
            log.info(f"✓ DA window count (24h): {actual_da_24h} (expected {expected_da_count})")
    
    # Validation 2: DA bid deadline
    # Legacy: tnext_retail_bid_da = retail_period_da - 60
    # First DA window at time 3600 (1 hour), bid deadline at 3540 (3600 - 60)
    if len(da_windows) > 0:
        first_da = da_windows[0]
        expected_bid_deadline = retail_period_da - 60
        if first_da.bid_submission_deadline != expected_bid_deadline:
            if log:
                log.error(f"DA bid deadline mismatch: expected {expected_bid_deadline}s, got {first_da.bid_submission_deadline}s")
            all_valid = False
        else:
            if log:
                log.info(f"✓ DA bid deadline: {first_da.bid_submission_deadline}s (expected {expected_bid_deadline}s)")
    
    # Validation 3: DA clearing time
    # Legacy: tnext_retail_clear_da = retail_period_da (at 1 hour boundary)
    if len(da_windows) > 0:
        first_da = da_windows[0]
        expected_clearing = retail_period_da
        if first_da.clearing_time != expected_clearing:
            if log:
                log.error(f"DA clearing time mismatch: expected {expected_clearing}s, got {first_da.clearing_time}s")
            all_valid = False
        else:
            if log:
                log.info(f"✓ DA clearing time: {first_da.clearing_time}s (expected {expected_clearing}s)")
    
    # Validation 4: RT window count (24 hours)
    # Legacy: One RT window every 5 minutes = 24*60/5 = 288 windows per 24 hours
    expected_rt_count_24h = (24 * 60) // 5  # = 288
    actual_rt_24h = len([w for w in rt_windows if w.clearing_time < 86400])
    if actual_rt_24h != expected_rt_count_24h:
        if log:
            log.error(f"RT window count mismatch (24h): expected {expected_rt_count_24h}, got {actual_rt_24h}")
        all_valid = False
    else:
        if log:
            log.info(f"✓ RT window count (24h): {actual_rt_24h} (expected {expected_rt_count_24h})")
    
    # Validation 5: RT bid deadline
    # Legacy: tnext_retail_bid_rt = retail_period_rt - 30 + retail_period_da * 1
    # First RT window at 300s (5 min), bid deadline at 270 (300 - 30)
    if len(rt_windows) > 0:
        first_rt = rt_windows[0]
        expected_bid_deadline = retail_period_rt - 30
        if first_rt.bid_submission_deadline != expected_bid_deadline:
            if log:
                log.error(f"RT bid deadline mismatch: expected {expected_bid_deadline}s, got {first_rt.bid_submission_deadline}s")
            all_valid = False
        else:
            if log:
                log.info(f"✓ RT bid deadline: {first_rt.bid_submission_deadline}s (expected {expected_bid_deadline}s)")
    
    # Validation 6: RT clearing time
    # Legacy: tnext_retail_clear_rt = retail_period_rt + retail_period_da * 1 (at 1h + 5min = 3900s)
    if len(rt_windows) > 0:
        first_rt = rt_windows[0]
        expected_clearing = retail_period_rt + retail_period_da
        if first_rt.clearing_time != expected_clearing:
            if log:
                log.error(f"RT clearing time mismatch: expected {expected_clearing}s, got {first_rt.clearing_time}s")
            all_valid = False
        else:
            if log:
                log.info(f"✓ RT clearing time: {first_rt.clearing_time}s (expected {expected_clearing}s)")
    
    if log:
        if all_valid:
            log.info("✓ ALL VALIDATIONS PASSED — Market windows match legacy timing!")
        else:
            log.error("✗ VALIDATION FAILED — Review market window configuration")
    
    return all_valid


def find_next_market_event(
    market_windows: List[object],
    time_granted: int,
    window_type: Optional[str] = None
) -> Tuple[Optional[object], Optional[int]]:
    """Phase 1: Find next market window event after current time.
    
    This helper function finds the next market window that needs event handling
    (either bid submission deadline or clearing time).
    
    Args:
        market_windows: List of MarketWindow objects
        time_granted: Current simulation time in seconds
        window_type: Optional filter ('DA', 'RT', or None for all types)
    
    Returns:
        Tuple of:
            - next_window: The next MarketWindow object (or None if no more windows)
            - next_event_time: Time of next event (deadline or clearing_time)
    
    Example (for Phase 2 hybrid loop):
        for window in market_windows:
            if window.bid_submission_deadline <= time_granted < (window.bid_submission_deadline + 1):
                # Handle bid submission for this window
                pass
    """
    if not market_windows:
        return None, None
    
    # Filter by type if specified
    candidate_windows = market_windows
    if window_type:
        candidate_windows = [w for w in market_windows if w.market_id == window_type]
    
    # Find windows with events in the future
    next_window = None
    next_event_time = None
    
    for window in candidate_windows:
        # Check bid submission deadline
        if window.bid_submission_deadline > time_granted:
            if next_event_time is None or window.bid_submission_deadline < next_event_time:
                next_event_time = window.bid_submission_deadline
                next_window = window
        # Check clearing time
        elif window.clearing_time > time_granted:
            if next_event_time is None or window.clearing_time < next_event_time:
                next_event_time = window.clearing_time
                next_window = window
    
    return next_window, next_event_time


# ============================================================================
# INSERTION POINT FOR SUBSTATION.PY (After Market Initialization, Line ~620)
# ============================================================================

"""
# Add to substation.py after market initialization (around line 620):

# Legacy timer constants (UNCHANGED)
tnext_retail_bid_rt = retail_period_rt - 30 + retail_period_da * 1
tnext_retail_bid_da = retail_period_da - 60
tnext_dso_bid_rt = retail_period_rt - 30 + retail_period_da * 1
tnext_dso_bid_da = retail_period_da - 30
tnext_dso_clear_rt = retail_period_rt + retail_period_da * 1
tnext_dso_clear_da = retail_period_da
tnext_retail_clear_da = retail_period_da
tnext_retail_clear_rt = retail_period_rt + retail_period_da * 1
tnext_retail_adjust_rt = retail_period_rt + retail_period_da * 1
tnext_write_metrics = metrics_record_interval + 1800
tnext_historic_load_da = 1
tnext_water_heater_update = 75

# [PHASE 1 NEW CODE - START]
# Initialize market protocol in parallel with legacy timers
market_protocol, market_windows = initialize_market_protocol_phase1(
    retail_period_da, retail_period_rt, simulation_duration, log
)

# Validate that market windows match legacy timer timing
if market_windows:
    if not validate_market_windows_against_legacy_timers(
        market_windows, retail_period_da, retail_period_rt, log
    ):
        log.error("Market protocol validation failed; proceeding with legacy code only")
        market_windows = []  # Disable market protocol
# [PHASE 1 NEW CODE - END]

time_granted = 0
time_last = 0

# Main loop (UNCHANGED - legacy event handlers continue to work)
while time_granted < simulation_duration:
    # existing code...
"""


# ============================================================================
# TESTING / VALIDATION SCRIPT (Run independently to verify Phase 1)
# ============================================================================

def test_phase1_parallel_setup():
    """Unit test for Phase 1 parallel setup - can run independently."""
    print("\n" + "="*80)
    print("PHASE 1 VALIDATION TEST")
    print("="*80)
    
    # Test parameters (matching DSOT defaults)
    retail_period_da = 3600  # 1 hour
    retail_period_rt = 300   # 5 minutes
    simulation_duration = 86400  # 24 hours
    
    # Initialize market protocol
    print("\n1. Initializing market protocol...")
    market_protocol, market_windows = initialize_market_protocol_phase1(
        retail_period_da, retail_period_rt, simulation_duration, log=None
    )
    
    if not market_windows:
        print("✗ Failed to initialize market protocol")
        return False
    
    print(f"✓ Generated {len(market_windows)} market windows")
    
    # Validate timing
    print("\n2. Validating market window timing...")
    is_valid = validate_market_windows_against_legacy_timers(
        market_windows, retail_period_da, retail_period_rt, log=None
    )
    
    if not is_valid:
        print("✗ Market window validation failed")
        return False
    
    print("✓ All validations passed")
    
    # Test helper function
    print("\n3. Testing find_next_market_event() helper...")
    
    time_test = 0
    next_window, next_time = find_next_market_event(market_windows, time_test, 'DA')
    print(f"  At t=0: Next DA event at {next_time}s (type: {next_window.market_id} window {next_window.window_number})")
    
    time_test = 3600
    next_window, next_time = find_next_market_event(market_windows, time_test, 'RT')
    print(f"  At t=3600: Next RT event at {next_time}s (type: {next_window.market_id} window {next_window.window_number})")
    
    # Show distribution of events
    print("\n4. Event time distribution (first 24 hours):")
    da_windows_24h = [w for w in market_windows if w.market_id == 'DA' and w.clearing_time < 86400]
    rt_windows_24h = [w for w in market_windows if w.market_id == 'RT' and w.clearing_time < 86400]
    print(f"  DA windows: {len(da_windows_24h)} (hourly)")
    print(f"  RT windows: {len(rt_windows_24h)} (every 5 minutes)")
    
    print("\n" + "="*80)
    print("✓ PHASE 1 VALIDATION PASSED — Ready for Phase 2 (Hybrid Loop)")
    print("="*80 + "\n")
    
    return True


if __name__ == '__main__':
    # Run validation test
    success = test_phase1_parallel_setup()
    exit(0 if success else 1)
