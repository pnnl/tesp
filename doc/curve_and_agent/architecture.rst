.. _architecture:

System Architecture
===================

Overview
--------

The Curve and Agent framework is a modular, layered architecture for
transactive energy participation. At the highest level, a **DeviceAgent**
manages a single physical device and participates in one or more retail
market products through the **Market Operator** (MO).

The framework comprises three principal layers:

1. **Device Layer** — Physics models, state observation, and control
   actuation through GridLAB-D.
2. **Agent Layer** — Flexibility estimation, preference curves,
   bid formulation, commitment tracking, dispatch optimization,
   and multi-interval planning.
3. **Market Layer** — Market object lifecycle, market operator clearing,
   DSO load estimation, and informational iteration convergence.

Module Map
----------

The source code is organized into the following modules under
``src/tesp_support/tesp_support/curve_and_agent/``:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Purpose
   * - ``enums_and_constants.py``
     - Shared enumerations: ``DeviceType``, ``MarketType``, ``MarketPhase``,
       ``OperatingMode``, ``IterationType``, ``CommitmentStatus``,
       ``ProductType``, ``PenaltyStructureType``, etc.
   * - ``data_types.py``
     - Plain dataclass containers — device states, bid structures,
       clearing results, flexibility envelopes, commitments, forecasts,
       delivery economics, settlement records.
   * - ``device_models.py``
     - Internal physics models (HVACModel, WaterHeaterModel,
       EVChargerModel, BatteryModel) for flexibility estimation and
       control translation.
   * - ``device_agent.py``
     - Top-level ``DeviceAgent`` class that orchestrates all agent
       functions and manages ``MarketObject`` instances.
   * - ``preference_curve.py``
     - ``PreferenceCurve`` class: isoelastic demand curve and
       battery sigmoid, driven by customer preference factor *k*.
   * - ``flexibility_ledger.py``
     - ``FlexibilityLedger``: three-tier capacity tracking
       (hard / expected / economic).
   * - ``dispatch_optimizer.py``
     - ``DispatchOptimizer``: single-timestep economic dispatch
       across overlapping deliveries. ``DeliveryValueCalculator``:
       computes per-market delivery economics.
   * - ``command_arbiter.py``
     - ``CommandArbiter``: merges dispatch solution into a single
       device command and actuates via GridLAB-D.
   * - ``market_object.py``
     - ``MarketObject``: per-cycle state machine managing the
       market phase lifecycle.
   * - ``market_operator.py``
     - ``MarketOperator``, ``SupplyCurve``,
       ``DSOLoadEstimationEngine``, ``DSOInflexibleLoadBid``.
   * - ``market_agent.py``
     - ``MarketCommunicationInterface``: bid submission, clearing
       reception, reconciliation.
   * - ``data_streams.py``
     - ``DataStreamManager``, ``ContinuousForecast``,
       ``EventForecast``, ``ConstraintStream``, ``UncertaintyModel``.
   * - ``planning_optimizer.py``
     - ``PlanningOptimizer``: multi-interval scheduling for
       batteries and shiftable loads.
   * - ``price_forecast_service.py``
     - ``PriceForecastService``: tracks price estimates across
       informational iterations.
   * - ``penalty_model.py``
     - ``PenaltyModel``: four penalty structures for non-delivery.
   * - ``gridlabd_interface.py``
     - ``GridLABDInterface``: read/write device state and control
       signals through FNCS/HELICS.

Data Flow
---------

The sense-decide-act loop executed each simulation timestep follows
this data flow:

::

   GridLAB-D ──(F1 observe)──► DeviceAgent
                                   │
                   ┌───────────────┼───────────────┐
                   ▼               ▼               ▼
             DataStreams     DeviceModel     FlexibilityLedger
             (forecasts,    (F2 estimate     (F6 available
              schedules,     flexibility)     capacity)
              constraints)       │               │
                   │             ▼               │
                   └──────► PreferenceCurve ◄────┘
                            (F3 preference)
                                 │
                                 ▼
                            BidCurve
                            (F4 formulate)
                                 │
                                 ▼
                     MarketCommunicationInterface
                     (F5 submit / receive clear)
                                 │
                                 ▼
                        FlexibilityLedger
                        (F6 record commitment)
                                 │
                                 ▼
                     DispatchOptimizer + DeliveryValueCalculator
                     (F7/F15 price response & delivery economics)
                                 │
                                 ▼
                        CommandArbiter
                        (resolve multiple deliveries)
                                 │
                                 ▼
                     DeviceModel (F8 control translation)
                                 │
                                 ▼
                  GridLABDInterface (F9 actuate) ──► GridLAB-D

Agent Function Catalog
----------------------

The DeviceAgent implements the following numbered functions:

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - ID
     - Name
     - Description
   * - F1
     - State Observation
     - Reads device physical state from GridLAB-D via
       ``GridLABDInterface``.
   * - F2
     - Flexibility Estimation
     - Uses the internal ``DeviceModel`` and forecasts to compute a
       ``FlexibilityEnvelope`` (Q_min, Q_max, Q_baseline) for each
       upcoming delivery interval.
   * - F3
     - Preference Curve
     - Instantiates a ``PreferenceCurve`` using the customer preference
       factor *k*, reference price *P₀*, and baseline *Q₀*.
   * - F4
     - Bid Formulation
     - Samples the preference curve at multiple price points, clipped
       to the flexibility envelope. Consults the ledger for available
       capacity and may include displacement bids.
   * - F5
     - Bid Submission / Clear Reception
     - Submits bids through ``MarketCommunicationInterface`` and
       processes ``ClearingResult`` responses.
   * - F6
     - Flexibility Ledger
     - Records new commitments, updates statuses, and queries
       three-tier availability (hard, expected, economic).
   * - F7
     - Price Response
     - Evaluates the preference curve at the cleared price to determine
       the target operating point.
   * - F8
     - Control Translation
     - Converts the power-domain target (kW) to a device-specific
       command (setpoint °F, charge rate kW, etc.).
   * - F9
     - Device Actuation
     - Writes the control command to GridLAB-D via
       ``GridLABDInterface``.
   * - F11
     - Main Loop
     - The ``step()`` method: iterates over all market objects, checks
       for phase transitions, and dispatches to the appropriate handler.
   * - F12
     - Performance Monitoring
     - Tracks actual vs. committed power and logs fulfillment records.
   * - F13
     - Reconciliation
     - At the end of a delivery interval, computes settlement and
       submits reconciliation data.
   * - F14
     - Penalty Model
     - Computes non-delivery penalty costs given the commitment and
       actual delivery.
   * - F15
     - Delivery Economics
     - ``DeliveryValueCalculator`` computes marginal revenue, penalty
       gradients, and net value for each active delivery.

Device Types
------------

The framework supports five device types, each with a specialized
physics model:

- **HVAC Heat Pump** (``HVAC_HEAT_PUMP``) — heating and cooling via
  a 2-node ETP model.
- **HVAC AC-Only** (``HVAC_AC_ONLY``) — cooling only, same ETP model.
- **Water Heater** (``WATER_HEATER``) — electric resistance, 2-zone
  stratified tank model.
- **EV Charger** (``EV_CHARGER``) — CCCV charging with BMS taper.
- **Battery** (``BATTERY``) — bidirectional charge/discharge with
  degradation tracking.

Each device type is documented in its own section of this manual.

Operating Modes
---------------

Each DeviceAgent can operate in one of three modes per market product:

**BIDDING**
   Full market participation. The agent formulates a bid curve (F3/F4),
   submits it through the communication interface (F5), receives a
   clearing result, and responds consistent with its submitted bid (F7).

**PRICE_RESPONSIVE**
   The agent does not submit bids. It observes the cleared or posted
   price and responds using the preference curve directly. This is
   suitable for environments where bid aggregation is not available.

**OVERRIDE**
   The agent ignores market signals and tracks the customer's amenity
   setpoint. This mode is useful for testing or when the customer
   opts out of transactive participation.
