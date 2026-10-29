# PySO and curve_and_agent: Comparison and Architecture Options

**Status:** Discussion draft for the FY27 System Operator work (Nathan).

**Sources and caveats:** The `curve_and_agent` observations come from reading `src/tesp_support/tesp_support/curve_and_agent/` (notably `market_operator.py` and `market_object.py`). The PySO observations come from reading the `main` branch of https://github.com/pnnl/pyso online (`engine.py`, `marketmodels/market.py`, `marketmodels/run_tso.py`, README). The PySO code has **not** been run, and the file listing was partial, so PySO claims should be verified before decisions are final.

## Context

- The FY27 plan expects PySO (Egret-based) to be the foundation of the TSO stub and, ideally, the DSO stub.
- `curve_and_agent` has never been used. It is a work in progress and can be changed freely; this is where the FY27 work will happen.
- Lab-level goal: consolidate parallel efforts and collaborate more. Working closely with the PySO developers, and feeding our input into PySO, is a benefit of adopting it.
- FY27 scope is a real-time energy market only, with no power flow, so PySO's strongest feature (network-aware optimization) is not needed this year.

## What PySO provides

- **`EnergyMarket` (`engine.py`)**: runs sequential Egret unit-commitment windows, carries initial conditions forward, monitors binding branch constraints, and computes LMPs by re-solving with commitments fixed and binaries relaxed.
- **`DataProvider.get_model(daterange)`**: the single input path. It returns an Egret `ModelData`.
- **`AbstractMarket` / `BasicMarket` (`marketmodels/market.py`)**: a state machine built on the `transitions` package.
  - States: `initialization`, user-defined timing states (expected to include `bidding` and `clearing`), `finalization`.
  - `MarketTiming` assigns each state a start offset within a `market_interval`.
  - Callbacks: `collect_bids`, `clear_market`, `publish_results`.
  - Setting `current_time` advances the machine.
- **`TSO` driver (`marketmodels/run_tso.py`)**: runs several markets (e.g. day-ahead and real-time) and always steps the market whose next state is earliest.

## What curve_and_agent provides

- **`MarketOperator`**: sums agent `BidCurve`s and inelastic DSO bids into aggregate demand, intersects it with a `SupplyCurve`, and interpolates the clearing price. It also supports informational versus binding iterations and returns per-agent results.
- **`MarketObject`**: a nine-phase state machine per market cycle (INACTIVE, ACTIVE, NEGOTIATION, MARKET_LEAD, ASSESSMENT, DELIVERY_LEAD, DELIVERY, RECONCILE, EXPIRED). It supports overlapping cycles, advisory history, settlement, and reconciliation.
- Curve and bid data types, device agents and models, forecasting, and optimizer components.

## Gap analysis

### PySO is missing (relative to our needs)

- Ingestion of live Curve/bid objects. Its bid collection reads Egret model data through a `DataProvider`.
- Any participant-side concept: agents, per-agent clearing results, settlement, reconcile.
- Informational (non-binding) iterations and overlapping market cycles.
- A lightweight clearing path. Every interval is an Egret solve.

### curve_and_agent is missing (relative to PySO)

- Network-aware optimization: unit commitment, economic dispatch, ramping and reserve constraints, LMPs.
- Multi-market sequencing (day-ahead plus real-time).
- A generic system-operator base class. `MarketOperator` is documented as the DSO's retail-market operator, and `tso.py` is an empty file.
- A unified Curve type. `SupplyCurve` is separate from `BidCurve` (there is an existing TODO at `market_operator.py:19`).

## Pros and cons of adopting PySO as the SO foundation

**Pros**

- Supports lab consolidation and gives TESP influence over PySO's direction.
- PySO is expected to become the preferred TSO tool, so experience with it has value beyond FY27.
- Egret optimization is available later without re-architecting (reserves, ramping, network constraints, a day-ahead market).
- Reuses a maintained state-machine library and timing model.

**Cons and risks**

- Egret and solver dependencies, and a per-interval solve, work against the "computationally light, annual run" goal of the stubs.
- A Curve-to-Egret translation layer is needed (generator supply curves as piecewise cost curves, demand as price-sensitive load).
- Two state-machine definitions (PySO's and `MarketObject`) must be reconciled, since the plan requires one definition shared by operators and participants.
- `run_tso.py` appears to have bugs as read: `TSO` is abstract yet instantiated, `find_next_market` iterates `.keys()` but unpacks pairs, and it looks up `market_order` by market object rather than by name. These need confirmation by running it.
- PySO changes depend on the developers' schedule.

## Architecture options

- **A. PySO as the engine only.** The TSO stub's `DataProvider` builds an Egret single-bus dispatch from received Curves. Simple to describe, but every step pays for an optimization.
- **B. Shared state machine only.** Adopt PySO's `MarketTiming`/state definitions for operators and participants and keep `MarketOperator`'s clearing. Cheap, but leaves PySO's optimization unused and does not exercise it.
- **C. Pluggable clearing engine (recommended).** Define a system-operator base class with a `ClearingEngine` interface.
  - `CurveIntersectionEngine`: extracted from `MarketOperator.clear_market`; fast, no dependencies.
  - `PySOEngine`: wraps `EnergyMarket` via a Curve-ingesting `DataProvider`.
  - TSO and DSO stubs choose an engine through configuration.
- **D. Replace `MarketOperator`/`MarketObject` with PySO.** Rejected: PySO has no participant-side concepts.

## Recommendation

Pursue option C.

1. Make `curve_and_agent` the home of the SO base class and engine interface. Reconcile with `design/so/class_so.plantuml`.
2. Implement the TSO stub first with the curve-intersection engine so the closed loop works early, then add the PySO engine behind the same interface.
3. Treat the Curve-ingesting `DataProvider` and a more generic state-machine definition as the contributions to PySO, and raise them with the developers early.
4. Decide whether `MarketObject`'s phases can be expressed in PySO's state machine. If yes, share one definition. If not, propose the generalization upstream.
5. Unify `SupplyCurve` and `BidCurve` into one generic Curve, which the TSO needs anyway because generators and DSOs both submit curves.

## Proposed sequence

1. Contact the PySO developers and agree on what "more generic" means for FY27.
2. Run a benchmark spike: single-bus dispatch from Curves via Egret versus curve intersection, over roughly 8,760 intervals.
3. Define the SO base class and `ClearingEngine` interface.
4. Implement the TSO stub in `curve_and_agent/tso.py` and DSO aggregation.
5. Run a small closed loop (1 TSO, 2 DSOs, mock device and generator agents) before the 8-node ERCOT demonstration.
6. Agree Curve units and the generator-agent bid format with Jessica.

## Open questions

- Real-time interval length: 5 minutes or hourly? (The plan says time steps of no more than one hour for the annual run.)
- Is there a single clearing per interval, or iterative TSO-DSO price exchange? This affects the state machine.
- Does the DSO stub need a clearing engine, or only aggregation?
- Who owns PySO, and what is their schedule and appetite for changes?
- Are Egret/solver availability and licensing a deployment constraint for TESP users?
