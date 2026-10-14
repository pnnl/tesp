.. _device_agent:

Device Agent
============

The ``DeviceAgent`` class (``device_agent.py``) is the top-level orchestrator.
It owns every sub-component and implements the main simulation loop. Each
``DeviceAgent`` manages a single physical device and participates in one or
more retail market products simultaneously.

Construction
------------

A DeviceAgent is created with:

- **agent_id** — Unique string identifier.
- **device_type** — One of the ``DeviceType`` enumeration values
  (``HVAC_HEAT_PUMP``, ``HVAC_AC_ONLY``, ``WATER_HEATER``,
  ``EV_CHARGER``, ``BATTERY``).
- **gridlabd** — A ``GridLABDInterface`` instance connected to
  the appropriate GridLAB-D object.
- **customer_preference_k** — A float in [0, 1] encoding the
  customer's willingness to trade amenity for financial benefit.
- **data_stream_manager** — A ``DataStreamManager`` pre-populated
  with forecast and schedule streams for this device.

Internally, the constructor creates:

- The appropriate device-specific physics model (``HVACModel``,
  ``WaterHeaterModel``, ``EVChargerModel``, or ``BatteryModel``).
- Empty dictionaries for market objects, communication interfaces,
  and penalty models.
- Shared components: ``FlexibilityLedger``, ``CommandArbiter``,
  ``PlanningOptimizer``, and ``PriceForecastService``.

Market Registration
-------------------

Before the simulation loop begins, markets must be registered using
``register_market()``:

.. code-block:: python

   agent.register_market(
       market_type=MarketType.RT_ENERGY,
       mode=OperatingMode.BIDDING,
       timing=MarketTimingParams(
           t_activate=-600, t_negotiate=-420,
           t_market_lead=-60, t_delivery_end=300,
           t_reconcile_end=600
       ),
       comm_interface=rt_comm,
       penalty_model=rt_penalty
   )

Each call creates a ``MarketObject`` and associates it with a
``MarketCommunicationInterface`` and ``PenaltyModel``.

The Step Loop (F11)
-------------------

The main simulation entry point is ``step(current_time)``. Each
invocation performs:

1. **State Observation (F1)** — Reads the device's current physical
   state from GridLAB-D.

2. **Market Object Iteration** — For every registered ``MarketObject``:

   a. Check whether the current simulation time triggers a phase
      transition in the market state machine.
   b. Execute the handler for the new phase.

3. **Delivery Resolution** — If any markets are in the DELIVERY phase,
   the ``CommandArbiter`` invokes the ``DispatchOptimizer`` to merge
   all active delivery obligations into a single operating point.

4. **Actuation (F9)** — The resolved command is written to GridLAB-D.

Phase Handlers
--------------

Each market phase transition triggers a specific handler inside
``DeviceAgent``:

**ACTIVE → NEGOTIATION**
   - Run F2 (flexibility estimation) to compute the
     ``FlexibilityEnvelope``.
   - Run F3/F4 (preference curve and bid formulation).
   - Run F5 (submit bid via communication interface).
   - Hold tentative commitment on the ``FlexibilityLedger``.

**NEGOTIATION → MARKET_LEAD**
   - Wait for clearing. No agent action.

**MARKET_LEAD → ASSESSMENT**
   - Receive ``ClearingResult`` from the Market Operator.
   - Determine iteration type (INFORMATIONAL vs. BINDING).

**ASSESSMENT (Informational)**
   - Record as ``AdvisoryRecord``; update ``PriceForecastService``.
   - Update ledger commitment to ADVISORY with convergence confidence.
   - Compute convergence metric and decide whether to request
     another iteration.
   - Transition back to ACTIVE if more iterations needed.

**ASSESSMENT (Binding)**
   - Promote ledger commitment to FIRM.
   - Evaluate preference curve at cleared price (F7) to determine
     target operating point.
   - Transition to DELIVERY_LEAD.

**DELIVERY_LEAD → DELIVERY**
   - Calculate delivery economics via ``DeliveryValueCalculator`` (F15).
   - Activate the dispatch optimizer for this delivery.

**DELIVERY**
   - Each timestep: record actual power (F12), compare to commitment.
   - ``CommandArbiter`` resolves all active deliveries.

**DELIVERY → RECONCILE**
   - Compute ``FulfillmentRecord``: integrated energy, shortfall,
     performance score.
   - Compute ``SettlementRecord``: revenue, penalties, net payment.
   - Submit reconciliation via communication interface (F13).
   - Release commitment from the ledger.

**RECONCILE → EXPIRED**
   - Market cycle complete. Object can be garbage collected or
     recycled for the next cycle.

Convergence and Confidence
--------------------------

When processing informational iterations, the agent computes two
metrics:

**Convergence** — Measures how much the cleared price changed between
successive informational iterations. A small change indicates the
iterative process is settling.

**Confidence** — An estimate of the probability that the advisory
price is close to the final binding price. Used to weight advisory
commitments on the flexibility ledger. Confidence is a function of
convergence and iteration count — more iterations with small changes
produce higher confidence.

GridLAB-D Interface
-------------------

The ``GridLABDInterface`` class (``gridlabd_interface.py``) provides
read and write methods for each device type, using TESP's ``#``-prefixed
property name convention over FNCS or HELICS:

- ``read_hvac_state()`` / ``write_hvac_setpoint()``
- ``read_water_heater_state()`` / ``write_water_heater_setpoint()``
- ``read_ev_charger_state()`` / ``write_ev_charge_rate()``
- ``read_battery_state()`` / ``write_battery_power()``

Read methods return the appropriate state dataclass (``HVACState``,
``WaterHeaterState``, etc.). Write methods accept a ``DeviceCommand``
and translate it to GridLAB-D property assignments.
