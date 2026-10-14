.. _battery:

Battery Storage
===============

The ``BATTERY`` device type models a behind-the-meter home battery
system (e.g., Tesla Powerwall, Enphase Encharge). Batteries are unique
in the framework because they are **bidirectional**: they can both
consume power (charge from the grid) and produce power (discharge to
the grid or local loads).

Physics Model
-------------

The ``BatteryModel`` tracks state of charge (SOC), enforces BMS limits,
and accounts for degradation costs.

**SOC Evolution:**

.. math::

   SOC(t + \Delta t) = SOC(t) + \frac{P \cdot \eta_{dir} \cdot \Delta t}{E_{capacity}}

Where:

- :math:`P` = power (kW), positive = charging, negative = discharging
- :math:`\eta_{dir}` = directional efficiency:
  :math:`\sqrt{\eta_{RT}}` for charge, :math:`1/\sqrt{\eta_{RT}}` for
  discharge
- :math:`E_{capacity}` = usable energy capacity (kWh)

**BMS Hard Limits:**
The Battery Management System enforces minimum and maximum SOC bounds
(``soc_min_bms``, ``soc_max_bms``) and limits charge/discharge power
to within the inverter's rated capacity.

Battery State
-------------

The agent reads the following state from GridLAB-D:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Units
     - Description
   * - ``soc``
     - fraction
     - Current state of charge (0.0–1.0)
   * - ``power``
     - kW
     - Current power, positive = charge, negative = discharge
   * - ``energy_capacity``
     - kWh
     - Total usable energy capacity
   * - ``max_charge_rate``
     - kW
     - Maximum charge power
   * - ``max_discharge_rate``
     - kW
     - Maximum discharge power
   * - ``round_trip_efficiency``
     - fraction
     - AC-to-AC round-trip efficiency
   * - ``cell_temperature``
     - °C
     - Battery cell temperature
   * - ``soc_min_bms``
     - fraction
     - BMS minimum SOC (hard floor)
   * - ``soc_max_bms``
     - fraction
     - BMS maximum SOC (hard ceiling)
   * - ``inverter_rated_power``
     - kW
     - Inverter continuous power rating
   * - ``state_of_health``
     - fraction
     - Remaining capacity fraction (1.0 = new)

Flexibility Estimation (F2)
---------------------------

Battery flexibility estimation produces a **bidirectional envelope**:

**Q_max (maximum consumption / charge)**
   The maximum charge power, limited by:

   - ``max_charge_rate``
   - ``inverter_rated_power``
   - Remaining SOC headroom: if SOC is near ``soc_max_bms``, the
     available charging energy (and thus power for the interval)
     is limited.

**Q_min (maximum export / discharge)**
   A *negative* value representing the maximum power the battery can
   export. Limited by:

   - ``max_discharge_rate``
   - ``inverter_rated_power``
   - Remaining SOC depth: if SOC is near ``soc_min_bms``, discharge
     is limited.

**Q_baseline**
   For batteries, the baseline is typically 0 kW (idle) unless a
   planning schedule dictates otherwise.

The method ``estimate_flexibility()`` accounts for the energy
constraint — the battery may not have enough stored energy to sustain
maximum discharge for the full delivery interval, or enough headroom
to sustain maximum charge. In these cases, the effective power bound
is the energy-limited rate:

.. math::

   P_{max,charge} = \min\left(P_{rated}, \frac{(SOC_{max} - SOC) \cdot E}{\sqrt{\eta} \cdot \Delta t}\right)

   P_{max,discharge} = \min\left(P_{rated}, \frac{(SOC - SOC_{min}) \cdot E}{\Delta t / \sqrt{\eta}}\right)

Degradation Model
-----------------

The ``BatteryModel`` includes a degradation tracking system that
estimates the cost of battery wear from cycling. This cost is
embedded in the preference curve's dead band to prevent uneconomic
cycling.

**Degradation Stress Factors:**

The marginal degradation cost is computed from three stress factors:

1. **SOC stress** — Higher when the battery operates at extreme SOC
   (near 0% or 100%). Modeled as a quadratic function centered at 50%
   SOC.

2. **C-rate stress** — Higher at faster charge/discharge rates.
   A linear function of the C-rate (power / capacity).

3. **Temperature stress** — Higher at extreme temperatures. An
   Arrhenius-derived factor that increases above ~35°C and below ~10°C.

The combined marginal degradation cost is:

.. math::

   c_{deg} = \frac{C_{replacement}}{2 \cdot N_{cycles} \cdot E_{capacity}}
   \cdot f_{SOC}(SOC) \cdot f_{Crate}(C) \cdot f_{temp}(T)

Where :math:`C_{replacement}` is the battery replacement cost,
:math:`N_{cycles}` is the rated cycle life, and the :math:`f` functions
are the stress multipliers.

**Budget Utilization:**

The model tracks cumulative degradation and compares it to a
degradation budget. The ``budget_utilization_rate()`` method reports
whether the battery is being cycled faster or slower than the budget
allows, enabling the agent to adjust bidding aggressiveness.

Preference Curve — Bidirectional Sigmoid
----------------------------------------

Batteries use a different preference curve form than load-only devices.
Instead of the isoelastic curve, the battery uses a **sigmoid**:

.. math::

   Q(P) = Q_{charge,max} \cdot \frac{1 - (P / P_{threshold})^\varepsilon}{1 + (P / P_{threshold})^\varepsilon}

This curve:

- At low prices: :math:`Q \rightarrow Q_{charge,max}` (charge from
  cheap grid power)
- At the threshold price: :math:`Q = 0` (idle)
- At high prices: :math:`Q \rightarrow -Q_{discharge,max}` (discharge
  to sell at high prices)

The **dead band** around the threshold price is controlled by the
degradation cost. The agent will not cycle the battery unless the
price spread exceeds the marginal degradation cost, preventing
wear from small price fluctuations.

The threshold price (:math:`P_{threshold}`) is the reference price
:math:`P_0`, typically the expected average retail rate. The elasticity
:math:`\varepsilon` is derived from the customer preference factor *k*
just as for load devices.

Control Translation (F8)
-------------------------

Battery control is direct: the ``DeviceCommand`` specifies a power
setpoint (kW) that is written to the GridLAB-D battery/inverter object.
Positive values command charging; negative values command discharging.

The ``power_to_battery_command()`` method clamps the commanded power to
the inverter rating and BMS SOC limits.

Market Participation
--------------------

Batteries are the most versatile device type:

- **RT Energy** — Arbitrage: charge during low-price intervals,
  discharge during high-price intervals.
- **DA Energy** — Schedule charge/discharge across 24 hours using the
  planning optimizer.
- **Regulation** — Fast signal following: the inverter can modulate
  power output within milliseconds, making batteries ideal for
  frequency regulation. The agent commits a capacity band (±kW) around
  a baseline operating point.
- **Spinning Reserve** — Hold discharge capacity in reserve. If
  activated, ramp to full discharge.

Batteries frequently participate in multiple products simultaneously.
The dispatch optimizer resolves conflicts when regulation and energy
deliveries overlap.

Planning Optimizer
------------------

The ``PlanningOptimizer`` includes battery-specific multi-interval
scheduling. It uses a **greedy algorithm** that:

1. Evaluates each future interval's expected net value of
   charge or discharge (price forecast minus degradation cost minus
   efficiency losses).
2. Ranks intervals by net value.
3. Assigns charge to the lowest-price intervals, discharge to the
   highest-price intervals, subject to the SOC trajectory constraint
   (``V_stored`` must remain within BMS limits at all times).

The resulting schedule is stored as a planned baseline that the
real-time agent tracks, with deviations allowed when real-time prices
diverge from forecasts.

Key Characteristics
-------------------

- **Bidirectional** — The only device type that can both consume and
  produce, enabling arbitrage and supply-side market participation.
- **Degradation-aware** — Every cycle has a non-zero marginal cost.
  The dead band in the preference curve ensures the battery only cycles
  when the price spread justifies the wear.
- **Multi-market** — Batteries are natural candidates for simultaneous
  participation in energy, regulation, and reserve markets.
- **SOC trajectory constraint** — Unlike thermal storage (HVAC, water
  heater) where the "stored energy" is implicit in temperature, battery
  SOC is tracked explicitly and constrains future flexibility.
- **Efficiency losses** — The round-trip efficiency (typically 85–93%)
  means that for every kWh stored, only :math:`\eta` kWh can be
  recovered. The agent accounts for this in bid formulation and
  planning.
