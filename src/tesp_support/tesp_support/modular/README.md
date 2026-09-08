# TESP Modular Market Protocol

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

Separates market design, clearing logic, and device physics into four independent abstractions so different market structures can be evaluated without touching device code or the HELICS federation layer.

See [ARCHITECTURE.md](ARCHITECTURE.md) for design rationale and extension examples.

---

## Package Contents

| File | Purpose |
|------|---------|
| `market_protocol.py` | ABCs: `Bid`, `MarketWindow`, `ClearingMechanism`, `MarketProtocol`, `DeviceStrategy`, `PriceSignal` |
| `price_signal.py` | `PriceSignal` dataclass — clearing results fed back to device agents |
| `dsot_market_protocol.py` | `DSOTMarketProtocol` (DA/RT settlement windows) + `DSOTCurveIntersectionClearing` (delegates to `RetailMarket.clear_market()`) |
| `dsot_device_strategies.py` | Native `DeviceStrategy` subclasses for HVAC, Battery, EV, WaterHeater, PV |
| `phase1_parallel_setup.py` | `initialize_market_protocol_phase1()` — window generation and timing validation |
| `hybrid_loop_runner.py` | `HybridLoopRunner` — runs hybrid path alongside legacy, compares clearing results |
| `battery_adapter_example.py` | `BatteryDSOTStrategyAdapter` — wraps `BatteryDSOT` as `DeviceStrategy` |
| `hvac_adapter.py` | `HVACDSOTStrategyAdapter` |
| `ev_adapter.py` | `EVDSOTStrategyAdapter` |
| `water_heater_adapter.py` | `WaterHeaterDSOTStrategyAdapter` |
| `pv_adapter.py` | `PVDSOTStrategyAdapter` (passive supply — zero-price offer) |
| `example_usage.py` | End-to-end proof-of-concept: market protocol + adapters + clearing |

---

## Quick Start

```python
from tesp_support.modular import (
    DSOTMarketProtocol,
    BatteryDSOTStrategyAdapter, HVACDSOTStrategyAdapter,
    EVDSOTStrategyAdapter, WaterHeaterDSOTStrategyAdapter,
)

# Generate all market windows for the simulation period
protocol = DSOTMarketProtocol(
    da_period_seconds=3600,
    rt_period_seconds=300,
    da_bid_lead_time_seconds=60,
    rt_bid_lead_time_seconds=30,
    retail_market=retail_market_obj,   # wires DSOTCurveIntersectionClearing to RetailMarket
)
market_windows = protocol.settlement_structure(0, simulation_duration)

# Wrap existing legacy agents as DeviceStrategy
adapter = BatteryDSOTStrategyAdapter(key, config, legacy_agent=battery_agent_obj)

# At each bid deadline:
bid = adapter.formulate_bid(window)

# After clearing, feed price signal back to device:
adapter.observe_prices(price_signal)
```

---

## Integration in `substation.py`

All retail and DSO/wholesale market timers have been replaced with pre-computed event time sets:

```python
# Retail windows (DA + RT) from MarketProtocol
market_windows = protocol.settlement_structure(0, simulation_duration)

# DSO/wholesale events as frozen sets (no mutable counters)
_dso_bid_rt_times = set(range(rt - 30 + da, sim_end + 1, rt))
_wholesale_clear_da_times = set(range(50400, sim_end + 1, 86400))
# ... (8 sets total)

# Unified next_time calculation
_window_times = [w.bid_submission_deadline for w in market_windows if w.bid_submission_deadline > t] + \
                [w.clearing_time for w in market_windows if w.clearing_time > t]
_dso_ws_next  = [x for x in (_dso_bid_rt_times | ... | _wholesale_clear_da_times) if x > t]
next_time = int(min([tnext_historic_load_da, tnext_water_heater_update,
                     tnext_write_metrics, simulation_duration] + _window_times + _dso_ws_next))
```

Remaining system timers (not market events): `tnext_historic_load_da`, `tnext_water_heater_update`, `tnext_write_metrics`.

---

## Validation

The `HybridLoopRunner` runs the new path in parallel with legacy code and compares results at each clearing:

```
✓ ALL COMPARISONS PASSED — Legacy and hybrid paths produce identical results!
```

Tolerances: price $0.01/MWh, quantity 0.001 MWh/device. Inspect `hybrid_runner.state.mismatches` for per-window diffs on failure.

---

## Unit Bridge

`DSOTCurveIntersectionClearing` operates in MWh / $/MWh but `RetailMarket.clear_market()` expects kWh / $/kWh. Conversions are applied at the boundary only:

| Direction | Quantity | Price |
|-----------|----------|-------|
| Into `clear_market()` | × 1000 (MWh → kWh) | ÷ 1000 ($/MWh → $/kWh) |
| Out of `clear_market()` | ÷ 1000 (kWh → MWh) | × 1000 ($/kWh → $/MWh) |
