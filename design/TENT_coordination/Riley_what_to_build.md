# What We Actually Build

The other documents explain *why*. This one answers only:

> What files do we write, in what order, and what does each one give us?

## The Short Answer

We build **one small Python package** — about 6 files, ~800 lines — plus **one new
class in TENT**.

That package is a *translator*. It has no physics of its own. Its entire job is:

```text
"Here is what this resource can do between 2:00 and 2:15 PM."
```

Everything else follows from that one sentence.

## Why We Need It (The Actual Problem)

Here is real TENT code, `tent/local_asset/solar_pv_resource_model.py:85`:

```python
if hour_of_day < 5.5 or hour_of_day > 17.5:
    power = 0.0
else:
    clear_sky_power = 0.5 * (1 + math.cos((hour_of_day - 12) * 2.0 * math.pi / 12))
    power = self.maximum_power * clear_sky_power * self.cloudFactor
```

And here is its configuration, `sample_configs/tn.campus.json:231`:

```json
{
  "class_name": "SolarPvResource",
  "cloud_factor": 1.0,
  "maximum_power": 120.0
}
```

A 120 kW solar site. Sunrise hardcoded to 5:30, sunset to 17:30, every day of the
year. No latitude. No panel tilt. No weather. `cloud_factor` is a single number
someone types in by hand.

Meanwhile `pvlib-python` sits in the same parent directory. Verified working:

```python
>>> mc.run_model(weather)
>>> mc.results.ac
06:00      0.000000
07:00    177.400050
08:00   1005.135903
09:00   2048.214682
10:00   2934.385105
11:00   3578.466774
```

Real solar position, real tilt, real module temperature, real inverter.

**Problem 1:** TENT cannot use pvlib. There is no seam. The physics is welded
inside `schedule_power()`.

**Problem 2:** TESP v2 is about to write its own version of that same seam
(their `device_models.py` + `data_streams.py`). Then there will be two.

So what we build is the seam. Once.

## The Deliverable

```text
der-interface/                       <- new, standalone, tiny
  der_interface/
    __init__.py
    conventions.py     ~80 lines     units, signs, time
    schema.py         ~250 lines     the data objects
    protocols.py       ~60 lines     the interfaces
    adapters/
      __init__.py
      pvlib_pv.py     ~200 lines     pvlib  -> envelope
      replay.py       ~120 lines     CSV    -> envelope
      ochre.py        ~250 lines     OCHRE  -> envelope   (phase 2)
      gridlabd.py     ~250 lines     GLD    -> envelope   (phase 2)
  tests/
  pyproject.toml

TENT/tent/local_asset/
  adapted_asset.py    ~150 lines     LocalAsset that consumes the above
```

Dependencies of `der-interface`: none for the core. pvlib only for the pvlib
adapter. It must never import TENT, TESP, HELICS, or GridLAB-D.

## The One Object That Matters

Everything hinges on this:

```python
@dataclass(frozen=True)
class EnvelopePoint:
    start: datetime          # timezone-aware, always
    duration_s: int
    q_min_kw: float          # least power this resource can draw
    q_max_kw: float          # most power this resource can draw
    q_baseline_kw: float     # what it draws if nobody intervenes
    sigma_kw: float = 0.0    # forecast uncertainty


@dataclass(frozen=True)
class FlexibilityEnvelope:
    resource_id: str
    points: tuple[EnvelopePoint, ...]
```

Three numbers per interval. That is the whole contract.

Why three numbers is enough:

```text
q_min == q_max            -> inflexible. PV, fixed load. One vertex.
q_min <  q_max            -> flexible. Bid curve spans the range.
q_min <  0 <  q_max       -> bidirectional. Battery.
q_baseline                -> the "do nothing" reference for settlement
```

Solar becomes `q_min == q_max == q_baseline == pvlib output`. A battery becomes
`q_min = -5.0, q_max = +5.0`. An HVAC becomes `q_min = 0.0, q_max = 4.2`. Same
object, no special cases.

## The Supporting Objects

Five more, all boring:

```python
@dataclass(frozen=True)
class ResourceState:      # what is true now
    resource_id: str
    timestamp: datetime
    values: Mapping[str, float | bool | str]
    quality: Quality = Quality.VALID

@dataclass(frozen=True)
class Forecast:           # what will be true later
    variable: str
    points: tuple[ForecastPoint, ...]

@dataclass(frozen=True)
class Limits:             # hard physical bounds, never negotiable
    min_power_kw: float
    max_power_kw: float
    available: bool = True
    constraints: Mapping[str, float] = field(default_factory=dict)

@dataclass(frozen=True)
class DispatchCommand:    # what we want
    resource_id: str
    start: datetime
    end: datetime
    target: Mapping[str, float]     # {"power_kw": 3.5} or {"setpoint_c": 21.0}

@dataclass(frozen=True)
class DispatchResponse:   # what actually happened
    resource_id: str
    accepted: bool
    actual: Mapping[str, float]
    violations: tuple[str, ...] = ()
```

`DispatchResponse` is not optional decoration. TENT's `ReconciliationMarket` has
`get_actual_power()` as an **empty stub** today. This object is what fills it.

## The Interfaces

```python
class FlexibilityProvider(Protocol):
    def get_envelope(self, intervals, context=None) -> FlexibilityEnvelope: ...

class StateProvider(Protocol):
    def get_state(self, timestamp=None) -> ResourceState: ...

class ForecastProvider(Protocol):
    def get_forecast(self, variable, start, end, resolution) -> Forecast: ...

class DispatchTarget(Protocol):
    def dispatch(self, command: DispatchCommand) -> DispatchResponse: ...
```

A resource implements only what it honestly supports. pvlib implements
`FlexibilityProvider` and `ForecastProvider` — and *not* `DispatchTarget`,
because you cannot command the sun.

## Adapter 1: pvlib

```python
class PvlibPvAdapter:
    """Turns pvlib into a TENT-consumable flexible resource."""

    def __init__(self, location, system, weather_source,
                 curtailable=False, sign=Sign.LOAD_POSITIVE):
        self._mc = ModelChain(system, location,
                              aoi_model='physical', spectral_model='no_loss')
        self._weather = weather_source
        self._curtailable = curtailable
        self._sign = sign

    def get_envelope(self, intervals, context=None):
        times = to_index(intervals)
        weather = self._weather.get(times)         # measured, TMY, or clearsky
        self._mc.run_model(weather)
        ac_kw = self._mc.results.ac / 1000.0

        points = []
        for interval, p in zip(intervals, ac_kw):
            gen = self._sign.generation(p)         # normalize once, here
            points.append(EnvelopePoint(
                start=interval.start_time,
                duration_s=int(interval.duration.total_seconds()),
                q_min_kw=0.0 if self._curtailable else gen,
                q_max_kw=gen,
                q_baseline_kw=gen,
            ))
        return FlexibilityEnvelope(self.resource_id, tuple(points))
```

Note `curtailable`. Flip it to `True` and the same PV array becomes a flexible
resource that can bid curtailment. That is a one-line config change, not a new
class.

Weather sources, in increasing order of realism:

| Source | Use |
|---|---|
| `location.get_clearsky()` | works offline today, no data needed |
| `pvlib.iotools.read_tmy3` | typical-year studies |
| `pvlib.iotools.get_pvgis_hourly` | real historical data |
| a live weather API | deployment |

All four hide behind `weather_source`. TENT never knows which one is in use.

## Adapter 2: Replay

Reads a CSV. Needed for tests, for reproducing cases, and for running without
any simulator installed.

```csv
start,duration_s,q_min_kw,q_max_kw,q_baseline_kw
2026-08-05T14:00:00-07:00,900,0.0,4.2,2.8
2026-08-05T14:15:00-07:00,900,0.0,4.2,2.9
```

Twenty lines of code. Makes the whole package testable in CI with no
dependencies.

## The TENT Side

One class. It replaces the per-simulator subclass pattern entirely.

```python
class AdaptedAsset(LocalAsset):
    def __init__(self, flexibility, dispatch=None, state=None, *a, **kw):
        super().__init__(*a, **kw)
        self.flexibility = flexibility
        self.dispatch_target = dispatch
        self.state_provider = state
        self._envelope = None

    def schedule_power(self, market):
        self._envelope = self.flexibility.get_envelope(market.time_intervals)
        for interval, point in zip(market.time_intervals, self._envelope.points):
            self.scheduled_powers.update(interval, point.q_baseline_kw)
        self.schedule_calculated = True

    def update_vertices(self, market):
        for interval, point in zip(market.time_intervals, self._envelope.points):
            if point.q_min_kw == point.q_max_kw:
                self.active_vertices.update(
                    interval, Vertex(float("inf"), 0.0, point.q_max_kw, True))
            else:
                lo, hi = self.price_range(interval)
                self.active_vertices.update(interval, Vertex(lo, 0.0, point.q_min_kw, True))
                self.active_vertices.update(interval, Vertex(hi, 0.0, point.q_max_kw, True))

    def actuate(self, market):
        if self.dispatch_target:
            self.dispatch_target.dispatch(self.command_for(market))
```

All three hooks already exist in `tent/local_asset/__init__.py`.
`actuate()` at line 426 is currently an empty `pass`. We are filling in a seam
TENT already left open, not bolting something on.

And then the campus config becomes:

```json
{
  "class_name": "AdaptedAsset",
  "module_name": "tent.local_asset.adapted_asset",
  "name": "SolarPv",
  "maximum_power": 120.0,
  "flexibility": {
    "adapter": "der_interface.adapters.pvlib_pv.PvlibPvAdapter",
    "location": {"latitude": 46.28, "longitude": -119.28, "tz": "US/Pacific"},
    "system": {"surface_tilt": 30, "surface_azimuth": 180, "pdc0": 120000},
    "weather_source": {"kind": "clearsky"},
    "curtailable": false
  }
}
```

`cloud_factor: 1.0` becomes real solar geometry and real weather. Nothing else in
TENT changes.

## Fix This First

`LocalAsset.cost()` documents:

```text
imported and generated power is positive
exported or consumed power is negative
```

GridLAB-D, OCHRE, and pvlib all treat **load as positive**. TENT is the
opposite. If we do not pin this down in `conventions.py` before writing a single
adapter, every number will silently come out backwards and it will be very hard
to notice in aggregate results.

```python
class Sign(Enum):
    LOAD_POSITIVE = auto()        # GridLAB-D, OCHRE, pvlib, most of the world
    GENERATION_POSITIVE = auto()  # TENT
```

Every adapter declares its native convention and normalizes at the boundary.
This is one day of work and it prevents the worst class of bug in the project.

## Order of Work

| # | Deliverable | Effort | What it unlocks |
|---|---|---|---|
| 1 | `conventions.py` | 1 day | Signs pinned. Prevents silent sign bugs. |
| 2 | `schema.py` + `protocols.py` | 2 days | The vocabulary exists. |
| 3 | `adapters/replay.py` + tests | 1 day | CI green, no deps. |
| 4 | `adapters/pvlib_pv.py` | 3 days | Real solar physics available. |
| 5 | `TENT/adapted_asset.py` | 3 days | **TENT runs a market on real solar.** |
| 6 | Swap campus config, compare | 1 day | Before/after evidence. |
| 7 | `adapters/ochre.py` (HVAC) | 1-2 wks | First dispatchable resource. |
| 8 | `adapters/gridlabd.py` | 1-2 wks | Feeder-connected resources. |
| 9 | HELICS transport for the 6 types | 1-2 wks | TESP v2 can consume it. |
| 10 | Wire `DispatchResponse` into reconciliation | 1 wk | Fills TENT's empty stubs. |

**Steps 1-6 are about two weeks and produce something demonstrable on their own.**
That is the whole first milestone: TENT clearing a market against real
pvlib-computed solar instead of a cosine curve.

Steps 7-10 are where TESP benefits directly, but they are only worth doing after
1-6 proves the contract holds.

## Battery Comes Last, On Purpose

Battery needs bidirectional power, SOC coupling *across* intervals, degradation
cost, and a reserve floor. Every one of those is an opportunity to accidentally
bake a battery-shaped assumption into a general interface.

HVAC and water heaters have none of that. Get the contract right on them first.
The battery adapter written in month three will be better than the one written
in week one, and the interface will survive it.

## What TESP Gets, Concretely

TESP v2's plan has 19 modules. These four overlap almost entirely with what we
are building:

| TESP v2 module | Replaced by |
|---|---|
| `data_types.py` (state + envelope + bid types) | `der_interface.schema` |
| `data_streams.py` (forecasts w/ uncertainty) | `der_interface.schema.Forecast` |
| `device_models.py` (HVAC/WH/EV/battery physics) | `der_interface.adapters.ochre` |
| `gridlabd_interface.py` (sole GLD read/write) | `der_interface.adapters.gridlabd` |

TESP v2's own design says GridLAB-D is touched **only** in F1 (read) and F9
(write). That is precisely the boundary our adapters draw. Their F1/F2/F8/F9/F12
map one-to-one onto our four protocols.

What TESP keeps and we do not touch: HELICS federates, process orchestration,
case generation, PYPOWER coupling, ns-3, metrics collection.

## What This Is Not

To keep scope from drifting:

- Not a market. TENT's markets stay in TENT.
- Not an optimizer. No LP, no QP, no dispatch solver.
- Not a physics engine. Zero equations of our own.
- Not an orchestrator. No time advancement, no process management.
- Not a message bus. HELICS stays in TESP.
- Not economics. No degradation cost, no penalty models, no prices.

If a proposed addition falls into any of those six categories, it belongs
somewhere else.

## The One-Sentence Version

We build a small translator package whose only job is to answer *"what can this
resource do in this time interval"* in a way that OCHRE, GridLAB-D, pvlib, and
real hardware can all answer, and that TENT and TESP can both consume — starting
with pvlib solar, because it replaces code that is visibly a placeholder and
carries almost no risk.

## References

- `TENT/tent/local_asset/solar_pv_resource_model.py:85` — the cosine placeholder
- `TENT/sample_configs/tn.campus.json:231` — `cloud_factor: 1.0`
- `TENT/tent/local_asset/__init__.py:426` — empty `actuate()` hook
- `TENT/tent/local_asset/__init__.py:105` — `cost()` sign convention
- `TENT/tent/containers/vertex.py:55` — `Vertex(price, cost, quantity, continuity)`
- `TENT/reconciliation_market.py` — the empty `get_actual_power()` stub
- `OCHRE/ochre/Equipment/Equipment.py:177` — `update_external_control()`
- `OCHRE/ochre/Dwelling.py:246` — `update_model(control_signal)`
- `pvlib-python/pvlib/modelchain.py:1608` — `ModelChain.run_model()`
- `pvlib-python/pvlib/location.py:261` — `Location.get_clearsky()`
- `ai_conversation/digest/01_architecture.md` — TESP v2 module catalog (§12)
