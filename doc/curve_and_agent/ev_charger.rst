.. _ev_charger:

EV Chargers
===========

The ``EV_CHARGER`` device type models a residential Level 2 Electric
Vehicle Supply Equipment (EVSE) with a connected vehicle battery. Unlike
the other device types, the EV charger has a hard departure constraint:
the vehicle must reach a target state of charge (SOC) by the customer's
declared departure time.

Physics Model
-------------

The ``EVChargerModel`` implements a **Constant Current / Constant
Voltage (CCCV)** charging profile. The model captures two key physical
effects:

1. **Constant-current region** (SOC < ``soc_at_max_taper``) — The EVSE
   delivers at the commanded charge rate up to ``max_charge_rate``.
2. **BMS taper region** (SOC ≥ ``soc_at_max_taper``) — The vehicle's
   Battery Management System (BMS) reduces the charge rate to protect
   the battery at high SOC. The effective charge rate tapers linearly
   from ``max_charge_rate`` at the taper point to a small fraction at
   SOC = 1.0.

The SOC evolution equation is:

.. math::

   SOC(t + \Delta t) = SOC(t) + \frac{P_{charge} \cdot \eta \cdot \Delta t}{E_{battery}}

Where:

- :math:`P_{charge}` = charge power (kW), subject to taper
- :math:`\eta` = charger AC-to-DC efficiency
- :math:`E_{battery}` = vehicle battery capacity (kWh)

The effective charge rate in the taper region is:

.. math::

   P_{eff} = P_{max} \cdot \frac{1.0 - SOC}{1.0 - SOC_{taper}}

This models the BMS reduction that is outside the agent's control —
even if the agent commands ``max_charge_rate``, the actual delivered
power decreases as SOC rises above the taper threshold.

EV Charger State
----------------

The agent reads the following state from GridLAB-D via
``read_ev_charger_state()``:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Units
     - Description
   * - ``soc``
     - fraction
     - Current state of charge (0.0–1.0)
   * - ``charge_rate``
     - kW
     - Current charge power
   * - ``battery_capacity``
     - kWh
     - Total vehicle battery capacity
   * - ``max_charge_rate``
     - kW
     - Maximum EVSE charge rate (e.g., 7.2 kW for Level 2)
   * - ``charger_efficiency``
     - fraction
     - AC-to-DC conversion efficiency
   * - ``vehicle_plugged_in``
     - bool
     - Whether a vehicle is connected
   * - ``min_charge_rate``
     - kW
     - Minimum non-zero charge rate (EVSE hardware limit)
   * - ``soc_at_max_taper``
     - fraction
     - SOC above which BMS taper begins

Flexibility Estimation (F2)
---------------------------

EV charger flexibility is bounded by two constraints: the hardware
limits and the departure requirement.

**Q_max (maximum consumption)**
   Charge at ``max_charge_rate``, subject to BMS taper if SOC is above
   the taper threshold. This is the maximum the EVSE can deliver at the
   current SOC.

**Q_min (minimum consumption) — departure-constrained**
   The minimum charge rate that ensures the vehicle reaches
   ``soc_target`` by ``departure_time``. This is computed by:

   1. Reading the departure constraint from the ``ConstraintStream``
      (customer input via an EV app or schedule).
   2. Computing the remaining energy needed:
      :math:`E_{remaining} = (SOC_{target} - SOC_{current}) \times E_{battery}`.
   3. Computing the remaining time: :math:`t_{remaining} = t_{departure} - t_{now}`.
   4. Back-calculating the minimum average charge rate:
      :math:`P_{min} = E_{remaining} / (\eta \cdot t_{remaining})`.
   5. Accounting for BMS taper: if the SOC will cross the taper
      threshold during the remaining period, the effective average
      rate is lower, so the minimum commanded rate must be higher.

   Q_min is also floored at ``min_charge_rate`` — the EVSE hardware
   cannot modulate below this threshold (it is either off or at
   ``min_charge_rate`` or above). If the vehicle is not plugged in,
   Q_min = Q_max = 0.

**Q_baseline**
   The charge rate that would reach the target SOC by departure if
   charging at a constant rate — essentially spreading the remaining
   energy need uniformly over the remaining time.

The critical characteristic of EV flexibility is that it is
**time-dependent**: flexibility is initially wide (especially if the
vehicle is plugged in early with a late departure) and progressively
narrows as the departure deadline approaches. If the agent has delayed
charging to exploit low prices but prices remain high, Q_min will
eventually rise to Q_max as the hard departure constraint takes over.

Probabilistic envelopes use uncertainty in the departure time (from the
``ConstraintStream``'s uncertainty model) to compute ``Q_min_p50``,
``Q_min_p90``, and ``Q_min_p99``. Earlier departure quantiles require
higher minimum charge rates.

Control Translation (F8)
-------------------------

The EV charger is controlled directly via the charging power setpoint.
The ``power_to_charge_rate()`` method handles:

1. **Power to charge rate** — The mapping is nearly direct (kW → kW),
   but two physical constraints must be enforced:

   - **BMS taper** — If the current SOC is above ``soc_at_max_taper``,
     the effective maximum charge rate is reduced regardless of the
     commanded value.
   - **Minimum charge rate floor** — If the target power falls between
     0 and ``min_charge_rate``, the command snaps to either 0 or
     ``min_charge_rate`` (whichever is closer to the target).

2. **Zero-command** — Setting the charge rate to 0 kW pauses charging.
   This is always available unless the departure constraint requires
   immediate charging.

Market Participation
--------------------

EV chargers are well-suited for:

- **RT Energy** — Modulating charge rate or pausing charging in response
  to 5-minute price signals. The vehicle battery's large capacity
  relative to the charge rate gives hours of flexibility.
- **DA Energy** — Committing to hourly charge profiles that exploit
  off-peak pricing. The planning optimizer can schedule charge across
  24 hours.
- **Spinning Reserve** — Pausing charging instantly to provide reserve
  capacity, then resuming once the contingency clears.

Key Characteristics
-------------------

- **Departure constraint** — The hard requirement to reach target SOC
  by departure time distinguishes EV charging from other flexible loads.
  The agent must balance price optimization against the risk of failing
  to meet this constraint.
- **CCCV taper** — The BMS-imposed taper above ~80% SOC reduces the
  agent's control authority at high SOC, making the last 20% of charge
  slower and less flexible.
- **Minimum charge rate** — The EVSE hardware cannot continuously
  modulate power; it operates in a region [``min_charge_rate``,
  ``max_charge_rate``] or is off. This creates a discontinuity in the
  flexibility envelope.
- **Session-based availability** — The charger is only flexible when a
  vehicle is plugged in. The ``EventForecast`` for plug-in/plug-out
  events drives availability predictions.
- **Unidirectional** — Standard Level 2 chargers can only consume
  power (charge), not export (V2G is not modeled in this framework).
  The flexibility envelope always has Q_min ≥ 0.
