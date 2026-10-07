# Reusable Model Layer

This document is the plain-language version. It answers one question:

> There are five repositories here. How can TENT use them, and how can we build
> something that also helps TESP when TESP gets rewritten?

## 1. The One Idea

Right now each repository answers a different question. That is easy to miss
because they all talk about "models."

| Repository | The question it actually answers |
|---|---|
| GridLAB-D | If this much power flows on this feeder, what happens to voltage? |
| OCHRE | If I control this house's equipment, what happens to temperature and power? |
| pvlib | Given weather and this PV hardware, how much power comes out? |
| TENT | Given flexible resources and prices, what schedule should each one accept? |
| TESP | How do I run all of the above together in one simulated world? |

None of them are competitors. They are different layers of the same stack.

The reusable thing is **not** a shared battery class or a shared HVAC class.
The reusable thing is a **shared vocabulary** that all five can speak.

```text
                     shared vocabulary
                            |
  +----------+----------+---+------+----------+----------+
  |          |          |          |          |          |
GridLAB-D  OCHRE     pvlib      TENT       TESP     real hardware
```

If they all speak the same vocabulary, TENT can plug into any of them without
knowing which one it is talking to. That is the entire goal.

## 2. Why This Matters Right Now

Two facts make this the right time:

1. TENT already has the market machinery (state machine, bid curves,
   upstream/downstream hierarchy).
2. TESP is being rewritten with a framework that looks a lot like TENT's.

The risk is obvious. If nobody builds a shared layer, TESP v2 will write its own
`HVACModel`, its own `BatteryModel`, its own `BidCurve`, its own state machine —
and then there are two nearly-identical frameworks that cannot share a single
device model. That is the outcome to avoid.

The comparison table in `ai_conversation/` already shows the overlap:

| Concept | TENT has it | TESP v2 plans it |
|---|---|---|
| Market state machine | Yes | Yes, plus ASSESSMENT |
| Price-quantity curve | `SDCurve` / `Vertex` | `BidCurve` / `BidPoint` |
| Flexibility envelope | `apply_constraints_and_bounds` | `FlexibilityEnvelope` |
| Sense-decide-act loop | `_state_machine_iteration` | F11 orchestrator |
| Up/downstream topology | `Neighbor.up_or_down` | DSO seam |

That is not two systems. That is one system described twice.

## 3. The Five Layers

Before designing anything, separate the word "model" into five distinct jobs.
Most of the confusion comes from using one word for all five.

```text
Layer 5   ORCHESTRATION    Who runs, in what order, exchanging what?      TESP
Layer 4   MARKET           How do many resources agree on a schedule?     TENT
Layer 3   FLEXIBILITY      How much can this one resource move?           SHARED
Layer 2   FORECAST         What will happen later?                        SHARED
Layer 1   PHYSICS          What happens if I do X right now?              OCHRE, GLD, pvlib
```

The important claim of this document:

- Layers 1, 4, and 5 should stay where they are. They are each somebody's
  specialty and rewriting them is wasted effort.
- Layers 2 and 3 are where TENT and TESP currently duplicate each other, and
  they are the layers worth extracting into shared code.

Layer 3 is the keystone. It is the translator between physics and markets.
A market cannot use a thermal circuit model. Physics does not understand a bid
curve. Layer 3 turns one into the other.

## 4. What Layer 3 Actually Does

Concretely, Layer 3 takes physics and produces three numbers per time interval:

```text
For interval 14:00-14:15
  Q_min      = 0.0 kW    lowest power this resource can draw
  Q_max      = 4.2 kW    highest power this resource can draw
  Q_baseline = 2.8 kW    what it would draw if nobody intervened
```

That is it. Three numbers, per interval, per resource.

Once you have those three numbers, everything downstream works:

- TENT builds `Vertex` objects and bids from them.
- TESP builds a `BidCurve` from them.
- A market clears using them.
- A cleared price maps back to a chosen power.
- That power maps back to a device setpoint.

And every physical simulator can produce those three numbers:

| Resource | Q_min | Q_max | Q_baseline |
|---|---|---|---|
| HVAC | power at highest tolerable temp | power at lowest tolerable temp | power at thermostat setpoint |
| Water heater | power at min safe tank temp | full element power | power to hold current setpoint |
| Battery | max discharge (negative) | max charge | 0 or scheduled |
| EV charger | 0, or min needed for departure | max charge rate | preferred charge profile |
| PV | curtailed output | full available output | full available output |

Notice that PV has `Q_min = Q_max` in the common case. A must-take resource is
just a zero-width envelope. That is a feature: the same interface handles both
flexible and inflexible resources without special cases.

## 5. Where pvlib Fits

pvlib is the clearest example of the whole argument, so it is worth walking
through.

TENT currently models solar like this, in
`TENT/tent/local_asset/solar_pv_resource_model.py:89`:

```python
clear_sky_power = 0.5 * (1 + math.cos((hour_of_day - 12) * 2.0 * math.pi / 12))
power = self.maximum_power * clear_sky_power * self.cloudFactor
```

That is a cosine bump between 5:30 and 17:30, scaled by a single hand-set cloud
factor. It has no concept of latitude, day of year, panel tilt, azimuth, module
temperature, inverter clipping, shading, soiling, or actual weather.

pvlib does all of that, and it is the reference implementation the PV industry
already uses. It has:

- `pvlib.location.Location` — latitude, longitude, altitude, timezone
- `pvlib.solarposition` — where the sun actually is
- `pvlib.clearsky` — clear-sky irradiance baseline
- `pvlib.irradiance` — plane-of-array irradiance from tilt and azimuth
- `pvlib.temperature` — cell temperature from irradiance, wind, ambient
- `pvlib.pvsystem.PVSystem` — module and inverter hardware
- `pvlib.modelchain.ModelChain` — the whole chain in one call
- `pvlib.iotools` — TMY, PVGIS, NSRDB, ERA5, SolarAnywhere, and more readers

So the swap is:

```text
Before:  TENT cosine curve  ->  scheduled_powers
After:   weather + pvlib ModelChain  ->  Q_min/Q_max/Q_baseline  ->  scheduled_powers
```

And critically, that same pvlib-backed forecast is useful to:

- TENT, for PV asset scheduling
- TESP, for the `btm_solar_generation` and `solar_irradiance` forecast streams
  that the TESP v2 design explicitly lists as external inputs
- OCHRE, which already has PV equipment that needs irradiance
- GridLAB-D, whose solar objects need the same irradiance data

One pvlib-backed forecast provider. Four consumers. That is the pattern the
whole shared layer is built on.

pvlib is also the least risky place to start, because:

- It is pure Python with no co-simulation dependency.
- It needs no actuation, so there are no control or safety concerns.
- It replaces TENT code that is obviously a placeholder.
- Its output is a forecast, which is the simplest contract to define.

## 6. The Shared Vocabulary

Six data objects. They are deliberately boring and simulator-agnostic.

### `ResourceState` — what is true right now

```python
ResourceState(
    resource_id="house_12_hvac",
    timestamp=t,
    values={
        "power_kw": 2.8,
        "indoor_temp_c": 22.4,
        "setpoint_c": 22.0,
        "mode": "cooling",
    },
    quality="valid",
)
```

Filled by: OCHRE, GridLAB-D, a real meter, a replay file.

### `Forecast` — what will be true later

```python
Forecast(
    variable="solar_power_kw",
    points=[
        ForecastPoint(start=t, duration_s=900, value=3.1, sigma=0.4),
        ForecastPoint(start=t2, duration_s=900, value=3.4, sigma=0.5),
    ],
)
```

Filled by: pvlib, a weather API, a price forecast service, a learned load model.

The `sigma` field matters. TESP v2's design is built around forecast uncertainty
propagation, and TENT's information services currently carry point values only.
Putting uncertainty in the shared object from day one avoids a painful retrofit.

### `Limits` — hard physical boundaries

```python
Limits(
    min_power_kw=0.0,
    max_power_kw=4.2,
    ramp_kw_per_min=None,
    available=True,
    constraints={"min_indoor_temp_c": 20.0, "max_indoor_temp_c": 24.0},
)
```

These are physics and safety. They are never negotiable by a market.

### `FlexibilityEnvelope` — the keystone object

```python
FlexibilityEnvelope(
    resource_id="house_12_hvac",
    intervals=[
        EnvelopePoint(start=t, duration_s=900,
                      q_min=0.0, q_max=4.2, q_baseline=2.8),
    ],
)
```

This is Layer 3's output and the single most important object in the design.
TENT already computes this concept inside `SDCurve.apply_constraints_and_bounds`.
TESP v2 names it `FlexibilityEnvelope`. Same thing, two names, no shared code.

### `DispatchCommand` — what we want to happen

```python
DispatchCommand(
    resource_id="house_12_hvac",
    start=t, end=t2,
    target={"power_kw": 3.5},      # or {"setpoint_c": 21.0}
    source="tent_market_clear",
)
```

Note it can carry either a power target or a setpoint. Some simulators accept
power directly; others only accept setpoints. The translation belongs in the
adapter, not in TENT.

### `DispatchResponse` — what actually happened

```python
DispatchResponse(
    resource_id="house_12_hvac",
    accepted=True,
    actual={"power_kw": 3.3},
    state=new_state,
    violations=[],
)
```

This closes the loop. TENT's `ReconciliationMarket` needs exactly this and
currently has `get_actual_power()` as an empty stub. TESP v2's F12 performance
monitor and F13 settlement need the same thing.

## 7. The Four Protocols

Small interfaces. A resource implements only what it can honestly support.

```python
class StateProvider(Protocol):
    def get_state(self, timestamp=None) -> ResourceState: ...

class ForecastProvider(Protocol):
    def get_forecast(self, variable, start, end, resolution) -> Forecast: ...

class FlexibilityProvider(Protocol):
    def get_envelope(self, intervals, context) -> FlexibilityEnvelope: ...

class DispatchTarget(Protocol):
    def dispatch(self, command: DispatchCommand) -> DispatchResponse: ...
```

Who implements what:

| Implementer | State | Forecast | Flexibility | Dispatch |
|---|---|---|---|---|
| pvlib adapter | no | yes | yes | no |
| OCHRE adapter | yes | partly | yes | yes |
| GridLAB-D adapter | yes | via players | yes | yes |
| Weather API adapter | no | yes | no | no |
| Real BMS adapter | yes | no | yes | yes |
| Replay/mock adapter | yes | yes | yes | yes |

The gaps are informative. pvlib cannot be dispatched, so it never pretends to
be. A weather service has no flexibility. The protocols make those facts
explicit rather than hiding them behind unimplemented methods.

## 8. How TENT Uses It

TENT gains one new generic asset class instead of one class per simulator.

```python
class AdaptedAsset(LocalAsset):
    """A LocalAsset backed by any external physical model."""

    def __init__(self, flexibility, dispatch=None, state=None, *a, **kw):
        super().__init__(*a, **kw)
        self.flexibility = flexibility
        self.dispatch_target = dispatch
        self.state_provider = state

    def schedule_power(self, market):
        envelope = self.flexibility.get_envelope(market.time_intervals, ...)
        for point in envelope.intervals:
            self.scheduled_powers.update(point.interval, point.q_baseline)
        self.schedule_calculated = True

    def update_vertices(self, market):
        # q_min/q_max become the two ends of the flexibility range,
        # priced using cost_parameters or a preference curve.
        ...

    def actuate(self, market):
        if self.dispatch_target:
            self.dispatch_target.dispatch(command_from(market, self))
```

The three hooks it uses (`schedule_power`, `update_vertices`, `actuate`) already
exist in `TENT/tent/local_asset/__init__.py`. `actuate()` at line 426 is
literally an empty `pass` waiting for this.

The payoff: one class, and then PV, HVAC, water heaters, batteries, EVs, and
whole buildings are configuration differences rather than new subclasses.

```text
AdaptedAsset + pvlib adapter        = PV asset
AdaptedAsset + OCHRE HVAC adapter   = HVAC asset
AdaptedAsset + OCHRE battery        = battery asset
AdaptedAsset + GridLAB-D house      = house asset
AdaptedAsset + real BMS adapter     = deployed asset
```

Compare to today: `SolarPvResource`, `OpenLoopLoadPredictor`, `SimpleBuilding`,
and `ModelFrameAsset` are each a bespoke subclass with its own physics baked in.

## 9. How TESP v2 Uses It

TESP's rewrite maps onto the shared layer cleanly, because the TESP v2 design
already isolates its simulator I/O to two functions.

| TESP v2 function | Shared layer equivalent |
|---|---|
| F1 device state observation | `StateProvider.get_state()` |
| F2 flexibility envelope | `FlexibilityProvider.get_envelope()` |
| F8 control signal translation | inside the adapter's `dispatch()` |
| F9 device actuation | `DispatchTarget.dispatch()` |
| F12 performance monitor | `DispatchResponse.actual` |
| data stream catalog (§11) | `ForecastProvider.get_forecast()` |

The TESP v2 design says GridLAB-D is touched only in F1 and F9. That is exactly
the boundary the shared layer draws. So the shared `GridLABDAdapter` is a drop-in
replacement for TESP v2's planned `GridLABDInterface`.

What stays TESP-specific and should not be shared:

- HELICS/FNCS federate setup and time advancement
- Process launching and case generation
- Bulk-system coupling (PYPOWER)
- ns-3 communication modeling
- Cross-simulator metrics collection

What TESP v2 should get from the shared layer instead of rewriting:

- Device state dataclasses
- Flexibility envelope computation
- Forecast objects with uncertainty
- Adapters for GridLAB-D, OCHRE, and pvlib
- Dispatch command and response types

That is roughly the `data_types.py`, `data_streams.py`, `device_models.py`, and
`gridlabd_interface.py` modules from the TESP v2 plan — about four of nineteen
planned modules that would not need to be written at all.

## 10. What Should NOT Be Shared

This list matters as much as the design. Overreach kills projects like this.

| Keep private to | What |
|---|---|
| TENT | Auctions, consensus, neighbor negotiation, market state machine |
| TESP | HELICS/FNCS, process orchestration, case generation, ns-3 |
| GridLAB-D | `.glm` parsing, powerflow solver, protection logic |
| OCHRE | HPXML parsing, envelope RC network, equipment physics |
| pvlib | Solar position algorithms, single-diode models, IAM |
| Hardware | BACnet, Modbus, vendor APIs, authentication, safety interlocks |

Two specific temptations to resist:

1. **Do not try to merge TENT's market with TESP's market.** They serve
   different purposes. TENT is a deployable transactive agent framework; TESP is
   a research co-simulation platform. They can share device models without
   sharing market logic.
2. **Do not put economics in the physical layer.** A battery reports SOC and
   power limits. It does not report degradation cost. Degradation cost is a
   policy calculation that belongs above Layer 3.

## 11. Sequence Diagram

```text
 pvlib / weather      OCHRE / GridLAB-D        TENT              TESP
      |                      |                  |                 |
      |                      |                  |   advance time  |
      |                      |<-----------------|-----------------|
      |                      |                  |                 |
      |                      |--ResourceState-->|                 |
      |---Forecast---------->|                  |                 |
      |---Forecast-----------|----------------->|                 |
      |                      |                  |                 |
      |                      |<-get_envelope()--|                 |
      |                      |--Envelope------->|                 |
      |                      |                  |                 |
      |                      |            [market clears]         |
      |                      |                  |                 |
      |                      |<-DispatchCommand-|                 |
      |                      |--DispatchResp--->|                 |
      |                      |                  |                 |
      |                      |            [reconcile: actual vs committed]
```

In a local TENT deployment, drop the TESP column and call the adapters directly.
In a co-simulation, TESP carries the same messages over HELICS. The message
types do not change. That is what makes the layer worth building.

## 12. Build Order

Ordered by risk. Each step is independently useful, so it is safe to stop early.

**Step 1 — Conventions.** Write down and freeze:
sign convention for power, units, timezone-aware timestamps, interval semantics
(start-inclusive, end-exclusive), and how missing data is represented.
This is the highest-leverage step and it costs a day.

TENT's convention needs verifying first. `LocalAsset.cost()` says
"imported and generated power is positive, exported or consumed power is
negative," which is the opposite of GridLAB-D and OCHRE where load is positive.
Every adapter must normalize this explicitly or the numbers will silently be
backwards.

**Step 2 — Data objects.** The six dataclasses from §6, immutable, validated,
no simulator imports. Under 500 lines total.

**Step 3 — pvlib forecast provider.** Wrap `ModelChain` behind
`ForecastProvider` and `FlexibilityProvider`. This is the low-risk proof that the
contract works.

**Step 4 — `AdaptedAsset` in TENT.** Wire the pvlib provider into a real TENT
market run. At this point TENT has physically credible solar. That is a genuine
improvement independent of everything else.

**Step 5 — Mock adapter.** CSV or JSON driven. Needed for tests and for
reproducing cases without running a simulator.

**Step 6 — OCHRE adapter.** Start with one equipment type, ideally HVAC or a
water heater rather than a battery, because they have no SOC or degradation
economics to confuse the interface.

**Step 7 — GridLAB-D adapter.** Same envelope contract, property read/write
underneath.

**Step 8 — TESP transport.** Carry the six object types over HELICS. Verify the
same scenario gives the same result locally and co-simulated.

**Step 9 — Reconciliation.** Use `DispatchResponse` to fill in TENT's empty
`get_actual_power()` and price-correction stubs.

**Step 10 — Hardware adapters.** Only after the simulated path is stable. Safety
and fail-safe behavior live entirely in this layer.

Deliberately last: battery. It combines bidirectional power, SOC coupling across
intervals, degradation cost, and reserve constraints. Every one of those is a
chance to accidentally bake a battery assumption into a general interface. Get
the interface right on simpler resources first.

## 13. Where the Code Goes

Start inside TENT, extract later. Creating a fourth repository before the schema
is proven adds coordination cost with no benefit.

Phase 1, inside TENT:

```text
TENT/tent/resource_interface/
  schema.py            # the six dataclasses
  protocols.py         # the four protocols
  conventions.py       # units, signs, time
  adapters/
    pvlib_pv.py
    ochre.py
    gridlabd.py
    replay.py
TENT/tent/local_asset/adapted_asset.py
```

Phase 2, once TESP v2 wants it, extract to a standalone package:

```text
der-interface/            # pip-installable, depends on nothing heavy
  der_interface/
    schema.py
    protocols.py
    conventions.py
    adapters/
```

Then TENT and TESP both depend on it, and OCHRE, GridLAB-D, or pvlib adapters
can live either in the package or in optional extras.

## 14. Rules

- One documented power sign convention, normalized at every adapter boundary.
- Units in field names (`power_kw`, not `power`).
- Timezone-aware timestamps, always.
- Physical limits and economic costs are separate objects.
- Flexibility is per-interval, never a single scalar.
- Always return what actually happened, not just command acceptance.
- Represent stale, missing, and unavailable states explicitly.
- A market result can never widen a physical limit.
- Adapters stay thin; physics stays in the physics repository.
- If a field only makes sense for one device type, it does not belong in the
  shared schema.

## 15. Summary

```text
pvlib      -> credible solar forecasts
OCHRE      -> credible building and equipment physics
GridLAB-D  -> credible feeder and network limits
                      |
                      v
        shared layer: state, forecast, envelope, dispatch
                      |
        +-------------+-------------+
        |                           |
      TENT                        TESP v2
   markets, bids,             co-simulation,
   negotiation,               orchestration,
   deployment                 research studies
```

TENT stops writing placeholder physics. TESP v2 skips writing device models it
would otherwise duplicate. OCHRE, GridLAB-D, and pvlib get used for what they
are actually good at. And the same asset code that runs in simulation can run
against real hardware, because the adapter is the only thing that changes.

The single highest-value first move is the pvlib PV forecast provider. It is
small, it is low-risk, it replaces code that is visibly a stand-in, and it
produces an artifact that both TENT and TESP v2 need.

## 16. Source References

- `TENT/tent/local_asset/__init__.py:426` — empty `actuate()` hook
- `TENT/tent/local_asset/__init__.py:105` — `cost()` and its sign convention
- `TENT/tent/local_asset/solar_pv_resource_model.py:89` — cosine PV placeholder
- `TENT/tent/local_asset/model_frame/models/base.py:77` — existing flexibility idea
- `TENT/tent/local_asset/actuation_manager/base.py:44` — actuation boundary
- `TENT/tent/information_service_model/__init__.py:80` — forecast interface
- `TENT/tent/containers/sd_curve.py` — `SDCurve` and `Vertex`
- `TENT/tent/enumerations/market_state.py` — market state machine
- `OCHRE/ochre/Equipment/Equipment.py:177` — `update_external_control()`
- `OCHRE/ochre/Dwelling.py:246` — `update_model(control_signal)`
- `pvlib-python/pvlib/modelchain.py:1608` — `ModelChain.run_model()`
- `pvlib-python/pvlib/iotools/` — weather and TMY readers
- `ai_conversation/digest/01_architecture.md` — TESP v2 F1-F16 design
- `ai_conversation/tent_tesp_commonalities.md` — TENT/TESP overlap analysis
