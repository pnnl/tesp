.. _examples:

Examples and Getting Started
============================

The ``examples/curve_and_agent/`` directory contains runnable demo
scripts that exercise the full framework pipeline without requiring
GridLAB-D or HELICS. All external dependencies are replaced by
lightweight mocks.

Available Examples
------------------

demo.py — Single Agent, Single Market
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A minimal end-to-end example:

- One HVAC agent on a 95°F summer afternoon.
- A 5-minute real-time energy market with a simple supply curve.
- The DSO submits an inflexible load bid for other customers.
- Walks through the complete pipeline: observe (F1) → estimate
  flexibility (F2) → preference curve (F3) → formulate bid (F4) →
  submit (F5) → market clearing → price response (F7) → control
  translation (F8) → actuate (F9) → deliver → reconcile (F13).

Run:

.. code-block:: bash

   cd examples/curve_and_agent
   python demo.py

demo_multi.py — 50 Agents, Single Market
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scales the demo to 50 HVAC agents with heterogeneous building
parameters and customer preferences:

- 50 houses with randomly varied thermal parameters, setpoints,
  and preference factors *k*.
- All participate in the same 5-minute RT energy market.
- The Market Operator aggregates all bids and clears against a
  supply curve.
- House_1 is traced step-by-step; the other 49 run in the background
  to produce a realistic aggregate demand curve.

Run:

.. code-block:: bash

   cd examples/curve_and_agent
   python demo_multi.py

demo_main_scenario.py — Multi-Device, Multi-Market
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A comprehensive scenario exercising the full framework:

- Multiple device types: HVAC, water heater, EV charger, battery.
- Both real-time and day-ahead energy markets.
- DSO inflexible load estimation with iterative correction.
- Market clearing and propagation.
- Settlement and reconciliation.

Uses ``MockGridLABDConnection`` for in-memory device state, and a
transport adapter that maps ``MarketCommunicationInterface`` calls
to the in-process ``MarketOperator`` API.

Run:

.. code-block:: bash

   cd examples/curve_and_agent
   python demo_main_scenario.py

main.py — Reference Wiring
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A reference implementation showing how to wire the framework
components together for a production simulation:

- Device agent creation and configuration for each device type.
- Data stream factory functions for creating device-specific
  forecast and constraint streams.
- Market registration with timing parameters.
- The main simulation loop calling ``agent.step(t)`` and
  ``market_operator.step(t)`` at each timestep.

This file serves as both a template and a documentation of the
intended wiring pattern.

Dashboard Visualizations
~~~~~~~~~~~~~~~~~~~~~~~~

Two HTML dashboards with Python data generators:

- ``dashboard.py`` / ``dashboard.html`` — Interactive visualization
  of a single market cycle (bid curves, clearing point, flexibility
  envelope).
- ``dashboard_scenario.py`` / ``dashboard_scenario.html`` — Multi-device
  scenario visualization showing how different device types respond.

Quick Start
-----------

1. **Ensure the package is importable.** The examples manipulate
   ``sys.path`` to import from the source tree directly. Alternatively,
   install the package:

   .. code-block:: bash

      cd src/tesp_support
      pip install -e .

2. **Run the minimal demo:**

   .. code-block:: bash

      python examples/curve_and_agent/demo.py

3. **Examine the output.** The demo prints each stage of the pipeline
   with labeled sections showing the agent's state, flexibility
   envelope, bid curve, clearing result, delivery performance, and
   settlement.

4. **Explore further.** Start with ``demo.py`` to understand the
   single-agent flow, then move to ``demo_multi.py`` for the
   multi-agent market, then ``demo_main_scenario.py`` for the full
   multi-device system.

Creating a New Device Agent
---------------------------

To set up a new device agent programmatically:

.. code-block:: python

   from enums_and_constants import DeviceType, MarketType, OperatingMode
   from data_types import MarketTimingParams
   from device_agent import DeviceAgent
   from data_streams import DataStreamManager, ContinuousForecast
   from gridlabd_interface import GridLABDInterface
   from market_agent import MarketCommunicationInterface
   from penalty_model import PenaltyModel

   # 1. Create the GridLAB-D interface
   gld = GridLABDInterface(connection=my_helics_or_fncs_handle)

   # 2. Set up data streams
   ds = DataStreamManager()
   ds.register("outdoor_temp", ContinuousForecast(...))
   ds.register("price_forecast", ContinuousForecast(...))

   # 3. Create the agent
   agent = DeviceAgent(
       agent_id="house_42_hvac",
       device_type=DeviceType.HVAC_AC_ONLY,
       gridlabd=gld,
       customer_preference_k=0.6,
       data_stream_manager=ds,
   )

   # 4. Register markets
   agent.register_market(
       market_type=MarketType.RT_ENERGY,
       mode=OperatingMode.BIDDING,
       timing=MarketTimingParams(
           t_activate=-600, t_negotiate=-420,
           t_market_lead=-60, t_delivery_end=300,
           t_reconcile_end=600
       ),
       comm_interface=MarketCommunicationInterface(...),
       penalty_model=PenaltyModel(...)
   )

   # 5. Run the simulation loop
   for t in range(t_start, t_end, dt):
       agent.step(t)
