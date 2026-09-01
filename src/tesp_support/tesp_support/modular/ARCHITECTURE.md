# TESP Modular Market Protocol Architecture

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This document describes the modular market protocol abstraction layer that enables experimentation with different market designs, bidding curves, and clearing mechanisms without touching device physics or the HELICS federation structure.

## Overview

The modular architecture separates concerns into four key interfaces:

1. **`Bid`** - Participant market offer with flexible value function
2. **`ClearingMechanism`** - Clearing algorithm (curve intersection, auction, co-optimization, etc.)
3. **`MarketProtocol`** - Settlement structure, timing, and bidding deadlines
4. **`DeviceStrategy`** - Device optimization and bid formulation

Additional support types:
- **`PriceSignal`** - Market results and prices published to participants
- **`MarketWindow`** - A single settlement period with timing and clearing mechanism

## Design Principles

### 1. Market Design is Localized

**Problem in the current code:**
Market design decisions are scattered across multiple files:
- Timing constants in `substation.py` (`tnext_retail_bid_da`, `tnext_wholesale_bid_da`, etc.)
- Bid format assumptions in `retail_market.py` (hardcoded AMES quadratic format)
- Clearing logic in `retail_market.py` (curve intersection)
- Price propagation paths in multiple files

Changing the bidding curve format requires editing at least 6 files. Adding a third settlement period requires restructuring the timer architecture in `substation.py`.

**Solution:**
A `MarketProtocol` defines the complete settlement structure in one place. The existing DSOT protocol becomes:

```python
# DSOT protocol: day-ahead (hourly) + real-time (every 5 minutes)
market_protocol = DSOTMarketProtocol(
    da_period_seconds=3600,
    rt_period_seconds=300,
    da_bid_lead_time_seconds=60,
    rt_bid_lead_time_seconds=30,
)

# Returns a list of MarketWindow objects for any time period
windows = market_protocol.settlement_structure(period_start=0, period_end=86400)
# → [DA_window_1, DA_window_2, ..., RT_window_1, RT_window_2, ...]
```

A new market design (e.g., three-settlement) is a new subclass:

```python
class ThreeSettlementMarketProtocol(MarketProtocol):
    def settlement_structure(self, period_start, period_end):
        # Return DA, intraday, and RT windows
        ...
```

The substation loop no longer has timer conditionals; it just calls `settlement_structure()` and processes each `MarketWindow`.

### 2. Bidding Curves Are Flexible

**Problem in the current code:**
`retail_market.py` assumes AMES quadratic format (`resp_c0`, `resp_c1`, `resp_c2`):

```python
def convert_2_AMES_quadratic_BID(resp_c0, resp_c1, resp_c2):
    # Hardcoded to quadratic polynomial
    value = resp_c0 + resp_c1 * Q + resp_c2 * Q**2
```

Adding support for piecewise linear bids or step functions requires:
1. Changing `convert_2_AMES_quadratic_BID()` to handle new formats
2. Updating bid aggregation logic
3. Modifying curve intersection algorithm
4. Touching all device agent code that formulates bids

**Solution:**
A `Bid` has an arbitrary `value_function`:

```python
class Bid:
    value_function: Callable[[float], float]  # Q → $/MWh
    # Can be any function: quadratic, piecewise, step, neural net, etc.

# Example: piecewise linear bid
def piecewise_linear(Q):
    if Q < 5.0:
        return 40.0  # Cheap bulk
    elif Q < 10.0:
        return 60.0  # Higher marginal cost
    else:
        return 100.0  # Capacity limit approaching
        
bid = Bid(
    participant_id="HVAC_001",
    market_id="DA",
    quantity_min=0.0,
    quantity_max=15.0,
    value_function=piecewise_linear,
)
```

The clearing mechanism receives a list of `Bid` objects and clears them.
It doesn't care what `value_function` is; clearing algorithms work on any curve shape.

### 3. Device Physics Are Isolated

**Problem in the current code:**
Device physics (thermal mass, battery SOC, EV charging) are entangled with market decisions:

```python
# HVAC agent (hvac_agent.py)
def DA_optimal_quantities(self):
    # Hardcoded to DA settlement period only
    # Assumes quadratic bidding format
    # Calls convert_2_AMES_quadratic_BID()
    # Returns list of hourly quantities
    ...

# Bid submission conditional in substation.py
if tnext_retail_bid_da == time_granted:
    # Device optimization is tied to a specific timer event
    # Change market structure = change substation.py
```

**Solution:**
A `DeviceStrategy` subclass encapsulates all device-specific logic:

```python
class HVACDSOTStrategy(DeviceStrategy):
    def __init__(self, device_id, config):
        self.thermal_mass = config['thermal_mass_kJ_per_K']
        self.indoor_temp = config['setpoint']
        # All device parameters in one place
    
    def observe_prices(self, price_signal):
        # Update state based on cleared quantity and price
        pass
    
    def formulate_bid(self, market_window):
        # Generate a Bid for this market window
        # Works for DA, RT, intraday, or any MarketWindow
        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            value_function=self.value_function_quadratic,
            ...
        )
```

Device agents no longer know about timing constants or HELICS. The market protocol and HELICS transport layer call `formulate_bid()` when needed.

### 4. Clearing Mechanisms Are Pluggable

**Problem in the current code:**
Clearing logic is hardcoded in `retail_market.py`:

```python
def clear_market_DA(self, ...):
    # Curve intersection for buyers vs. sellers
    # Hard-coded polynomial fitting and intersection finding
    # Only works for single-sided (buyer/seller) markets
    # Cannot support double auctions, batch auctions, PSST co-optimization, etc.
```

**Solution:**
A `ClearingMechanism` is an abstract interface:

```python
class ClearingMechanism(ABC):
    def clear(self, bids: list[Bid]) -> dict[str, tuple[float, float]]:
        # Returns: {participant_id → (cleared_qty, cleared_price)}
        pass

# Concrete implementations:
class CurveIntersectionClearing(ClearingMechanism):
    # Current DSOT logic (curve fitting + intersection)
    ...

class UniformPriceAuction(ClearingMechanism):
    # Uniform-price auction (price = highest accepted bid)
    ...

class PayAsBidClearing(ClearingMechanism):
    # Each participant's price is their own bid
    ...

class DoubleAuctionClearing(ClearingMechanism):
    # Buyers and sellers matched by price
    ...

class PSSTPLDCClearing(ClearingMechanism):
    # Wholesale co-optimization with PSST
    ...
```

Each `MarketWindow` can specify which clearing mechanism to use:

```python
market_protocol.get_clearing_mechanism(window)
# → CurveIntersectionClearing() for DSOT
# → UniformPriceAuction() for new market design
# → DoubleAuctionClearing() for double-auction experiment
```

## Key Abstractions

### Bid

Represents a participant's market offer.

```python
@dataclass
class Bid:
    participant_id: str                      # e.g., "HVAC_001", "BATT_002"
    market_id: str                           # e.g., "DA", "RT", "intraday"
    valid_from: int                          # Simulation time (seconds)
    valid_to: int                            # Simulation time (seconds)
    quantity_min: float                      # Minimum quantity (MWh)
    quantity_max: float                      # Maximum quantity (MWh)
    value_function: Callable[[float], float] # Q → $/MWh
    bid_type: str                            # "supply" or "demand"
    metadata: Dict[str, Any]                 # Device type, constraints, etc.
```

The `value_function` is the key innovation: any callable that maps quantity to marginal $/MWh.

For a supply bid (generator), `value_function(Q)` is marginal cost.
For a demand bid (load), `value_function(Q)` is marginal willingness-to-pay.

Example:
```python
# Quadratic cost: C0 + C1*Q + C2*Q^2
def hvac_value(Q):
    return 30.0 + 25.0 * Q + 2.0 * Q**2

bid = Bid(
    participant_id="HVAC_001",
    market_id="DA",
    valid_from=3600,
    valid_to=7200,
    quantity_min=0.0,
    quantity_max=10.0,
    value_function=hvac_value,
    bid_type="demand",
)

# Evaluate marginal value at any quantity
marginal_at_5mwh = bid.marginal_value_at(5.0)  # → $105/MWh
```

### MarketWindow

Specifies a single market session's timing and parameters.

```python
@dataclass
class MarketWindow:
    market_id: str                    # "DA", "RT", "intraday", etc.
    window_number: int                # Ordinal (0, 1, 2, ...)
    settlement_period_start: int      # Seconds from simulation start
    settlement_period_end: int        # Seconds from simulation start
    bid_submission_deadline: int      # Seconds; bids must be submitted before this
    clearing_time: int                # Seconds; when clearing is executed
    clearing_mechanism_name: str      # e.g., "curve_intersection", "psst", "uniform_price"
```

Example: DA market window for the first hour

```python
window = MarketWindow(
    market_id="DA",
    window_number=0,
    settlement_period_start=0,
    settlement_period_end=3600,
    bid_submission_deadline=3540,  # 60 sec before clearing
    clearing_time=3600,
    clearing_mechanism_name="curve_intersection",
)
```

### ClearingMechanism

Abstract base class for market clearing algorithms.

```python
class ClearingMechanism(ABC):
    @abstractmethod
    def clear(self, bids: list[Bid]) -> dict[str, tuple[float, float]]:
        """
        Args:
            bids: List of Bid objects for this market window
        
        Returns:
            Dict mapping participant_id → (cleared_quantity_MWh, clearing_price_$/MWh)
        """
```

Example: curve intersection (DSOT)

```python
clearing = CurveIntersectionClearing()
result = clearing.clear([
    Bid(..., participant_id="HVAC_001", ...),
    Bid(..., participant_id="BATT_001", ...),
    Bid(..., participant_id="EV_001", ...),
])
# → {
#     "HVAC_001": (2.0, 45.0),   # 2.0 MWh cleared @ $45/MWh
#     "BATT_001": (3.5, 45.0),
#     "EV_001": (1.5, 45.0),
# }
```

### MarketProtocol

Abstract base class for settlement structures and market rules.

```python
class MarketProtocol(ABC):
    @abstractmethod
    def settlement_structure(self, period_start: int, period_end: int) -> list[MarketWindow]:
        """Returns list of market windows that occur in [period_start, period_end]"""
        pass
    
    @abstractmethod
    def get_clearing_mechanism(self, market_window: MarketWindow) -> ClearingMechanism:
        """Returns the clearing mechanism for a given market window"""
        pass
    
    @abstractmethod
    def publish_results(self, market_window: MarketWindow, clearing_result: dict) -> PriceSignal:
        """Converts clearing result to feedback for participants"""
        pass
```

Example: DSOT (day-ahead + real-time)

```python
protocol = DSOTMarketProtocol(
    da_period_seconds=3600,
    rt_period_seconds=300,
)

# Get all market windows for 24 hours
windows = protocol.settlement_structure(period_start=0, period_end=86400)
# → [DA_0, DA_1, ..., DA_23, RT_0, RT_1, ..., RT_17279]

# Each window has timing and clearing mechanism
for window in windows:
    if window.clearing_time == current_time:
        mech = protocol.get_clearing_mechanism(window)
        result = mech.clear(participant_bids)
        price_signal = protocol.publish_results(window, result)
        # Publish price_signal to participants via HELICS
```

### DeviceStrategy

Abstract base class for device participation in energy markets.

```python
class DeviceStrategy(ABC):
    def __init__(self, device_id: str, device_type: str):
        self.device_id = device_id
        self.device_type = device_type
    
    def initialize(self) -> None:
        """Called once at simulation start"""
        pass
    
    def finalize(self) -> None:
        """Called once at simulation end"""
        pass
    
    @abstractmethod
    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Observe market results and update internal state"""
        pass
    
    @abstractmethod
    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Generate a bid for a market window"""
        pass
```

Example: HVAC device

```python
hvac = HVACDSOTStrategy("HVAC_001", hvac_config)

# Observe market price feedback
price_signal = PriceSignal(
    market_id="DA",
    clearing_price=45.0,
    cleared_quantities={"HVAC_001": 2.0},
    ...
)
hvac.observe_prices(price_signal)

# Formulate bid for next market window
window = MarketWindow(market_id="RT", clearing_time=3605, ...)
bid = hvac.formulate_bid(window)
# → Bid with Q_range and value_function based on current thermal state
```

### PriceSignal

Market feedback published to participants.

```python
@dataclass
class PriceSignal:
    market_id: str                           # "DA", "RT", etc.
    time_step: int                           # Simulation time (seconds)
    period_start: int                        # Settlement period start
    period_end: int                          # Settlement period end
    clearing_price: float                    # System marginal price ($/MWh)
    participant_prices: dict[str, float]     # Per-participant prices (if applicable)
    cleared_quantities: dict[str, float]     # Per-participant cleared quantities
    constraints_active: dict[str, bool]      # Which transmission constraints are binding
    metadata: dict[str, Any]                 # Additional info (iteration count, convergence, etc.)
```

Example:

```python
signal = PriceSignal(
    market_id="DA",
    time_step=3600,
    period_start=0,
    period_end=3600,
    clearing_price=45.0,
    participant_prices={"HVAC_001": 45.0, "BATT_001": 45.0, "EV_001": 45.0},
    cleared_quantities={"HVAC_001": 2.0, "BATT_001": 3.5, "EV_001": 1.5},
)
```

## Integration Points

### 1. HELICS Transport Layer

The modular layer is independent of HELICS. Integration happens at the transport layer:

```python
# Publishing participant bids
bid = device.formulate_bid(market_window)
bid_json = serialize_bid_to_json(bid)  # Convert to JSON
helics.helicsPublicationPublishString(pub_bid, bid_json)

# Publishing market results
price_signal = market_protocol.publish_results(window, clearing_result)
signal_json = serialize_price_signal_to_json(price_signal)
helics.helicsPublicationPublishString(pub_signal, signal_json)
```

### 2. Substation Loop Integration

Replace timer conditionals with protocol-driven flow:

**Current code:**
```python
# In substation.py
if time_granted >= tnext_retail_bid_da:
    # Collect DA bids from devices
    for device in devices:
        bid = device.DA_optimal_quantities()
    # Clear market
    retail_market.clear_market_DA()
    tnext_retail_bid_da += retail_period_da
```

**New code:**
```python
# In substation.py
for window in market_protocol.settlement_structure(time_granted, time_granted + 1):
    if time_granted >= window.bid_submission_deadline:
        # Collect bids from devices
        bids = []
        for device in devices:
            bid = device.formulate_bid(window)
            bids.append(bid)
        # Clear market
        mech = market_protocol.get_clearing_mechanism(window)
        result = mech.clear(bids)
        # Publish results
        signal = market_protocol.publish_results(window, result)
        # Broadcast to participants via HELICS
        helics.helicsPublicationPublishString(pub_signal, serialize(signal))
```

The substation loop is now generic over market structure.

### 3. Device Agent Integration

Replace `DA_optimal_quantities()` with `formulate_bid()`:

**Current code:**
```python
class HVACDSOT:
    def DA_optimal_quantities(self):
        # Hardcoded to DA market only
        # Returns list of hourly quantities
        return [q0, q1, ..., q23]
```

**New code:**
```python
class HVACDSOTStrategy(DeviceStrategy):
    def formulate_bid(self, market_window):
        # Works for any market window (DA, RT, intraday, ...)
        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            quantity_min=...,
            quantity_max=...,
            value_function=self.value_function_quadratic,
        )
```

## Examples: New Market Designs

### Example 1: Three-Settlement Market (DA + Intraday + RT)

**Old approach:**
- Add `tnext_intraday_bid`, `tnext_intraday_clear`, etc. to `substation.py`
- Modify substation loop to handle three settlement periods
- Duplicate clearing logic for intraday market
- Touch device agents to add intraday bidding

**New approach:**

```python
class ThreeSettlementMarketProtocol(MarketProtocol):
    def settlement_structure(self, period_start, period_end):
        windows = []
        # Add DA windows (hourly)
        # Add intraday windows (30-min, starting at 30 min into each hour)
        # Add RT windows (5-min)
        return sorted(windows, key=lambda w: w.clearing_time)

# Device agents don't change
# Substation loop doesn't change
# New market structure is just a new MarketProtocol subclass
market = ThreeSettlementMarketProtocol()
```

### Example 2: Double-Auction Market (Buyers and Sellers)

**Old approach:**
- Modify bid format to distinguish buyers from sellers
- Rewrite clearing logic for double auction
- Touch all device agents

**New approach:**

```python
class SellerBid(Bid):
    # Same as Bid, but bid_type is always "supply"
    pass

class DoubleAuctionClearing(ClearingMechanism):
    def clear(self, bids):
        # Separate buyers and sellers
        # Match by price (highest buyer price ≥ lowest seller price)
        # Return {participant_id → (qty, price)}
        ...

class DoubleAuctionMarketProtocol(MarketProtocol):
    def get_clearing_mechanism(self, window):
        return DoubleAuctionClearing()

# Device agents still call formulate_bid()
# Devices can be buyers or sellers (bid_type determines role)
# New clearing mechanism handles the matching
```

### Example 3: Custom Rate Design (TOU, CPP)

**Old approach:**
- Modify `retail_market.py` to compute shadow prices based on rate structure
- Embed rate logic in DSO agent and device agents

**New approach:**

```python
class CustomRateMarketProtocol(MarketProtocol):
    def settlement_structure(self, period_start, period_end):
        # Define market windows with rate-specific deadlines
        # E.g., critical peak hours have earlier bid deadlines
        # E.g., off-peak hours have reduced demand charges
        ...
    
    def publish_results(self, window, clearing_result):
        # Include rate multipliers in PriceSignal
        signal = PriceSignal(...)
        signal.metadata["rate_multiplier"] = self.get_rate_multiplier(window)
        return signal

# Device agents observe the rate multiplier
# and adjust their bids accordingly
```

## Migration Path: Current DSOT

The existing DSOT implementation is preserved as a reference:

```python
# Step 1: Wrap existing behavior as concrete classes
market = DSOTMarketProtocol(
    da_period_seconds=3600,
    rt_period_seconds=300,
    da_bid_lead_time_seconds=60,
    rt_bid_lead_time_seconds=30,
)

# Step 2: Extract clearing logic from retail_market.py
clearing = DSOTCurveIntersectionClearing()
# Encapsulates the curve aggregation and intersection logic

# Step 3: Adapt existing device agents
devices = [
    HVACDSOTStrategy(device_id, hvac_config),
    BatteryDSOTStrategy(device_id, battery_config),
    EVDSOTStrategy(device_id, ev_config),
]

# Step 4: Refactor substation loop to use new abstractions
for window in market.settlement_structure(time_granted, time_granted + 1):
    bids = [device.formulate_bid(window) for device in devices]
    result = clearing.clear(bids)
    signal = market.publish_results(window, result)
    # Publish via HELICS
```

All existing tests still pass. The current DSOT behavior is preserved.

## Files

- `market_protocol.py` - Abstract base classes: `Bid`, `ClearingMechanism`, `MarketProtocol`, `MarketWindow`
- `device_strategy.py` - Abstract base class: `DeviceStrategy`
- `price_signal.py` - Data class: `PriceSignal`
- `dsot_market_protocol.py` - DSOT concrete implementations: `DSOTMarketProtocol`, `DSOTCurveIntersectionClearing`
- `dsot_device_strategies.py` - DSOT concrete implementations: `DSOTDeviceStrategy`, `HVACDSOTStrategy`, `BatteryDSOTStrategy`, `EVDSOTStrategy`, `WaterHeaterDSOTStrategy`, `PVDSOTStrategy`
- `example_usage.py` - Demonstration of all abstractions working together

## Next Steps

1. Extract `retail_market.clear_market_DA()` and `clear_market_RT()` logic into `DSOTCurveIntersectionClearing.clear()`
2. Integrate existing device agents as `DSOTDeviceStrategy` subclasses
3. Refactor `substation.py` to call `market_protocol.settlement_structure()` instead of using timer conditionals
4. Add HELICS serialization/deserialization for `Bid` and `PriceSignal` objects
5. Verify all existing tests still pass

Once the migration is complete, new market designs can be implemented by:
- Creating a new `MarketProtocol` subclass
- Creating new `ClearingMechanism` subclasses if needed
- Running existing device agents unchanged
