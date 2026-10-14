.. _Curve and Agent Framework:

..
    Copyright (c) 2021-2026 Battelle Memorial Institute
    file: curve_and_agent/index.rst

Curve and Agent Framework
*************************

The Curve and Agent framework implements a transactive energy agent architecture
for residential and small-commercial devices participating in distribution-level
retail markets. Each customer device is managed by a **DeviceAgent** that
observes device physics, estimates flexibility, formulates preference-based bids,
participates in multiple market products, resolves overlapping delivery
obligations, and actuates the physical device through GridLAB-D.

This manual covers the full framework: architecture, device-specific physics
models, market mechanisms, and the mathematical formulations underlying
bidding, dispatch, and planning.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   architecture
   device_agent
   hvac
   water_heater
   ev_charger
   battery
   preference_curves
   markets
   flexibility_ledger
   dispatch_optimizer
   planning
   data_streams
   penalty_model
   examples
