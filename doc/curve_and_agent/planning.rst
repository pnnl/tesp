.. _planning:

Planning Optimizer
==================

The ``PlanningOptimizer`` class (``planning_optimizer.py``) handles
multi-interval scheduling — looking ahead over many delivery intervals
(e.g., 24 hours of hourly intervals) to optimize the device's
operating plan.

Purpose
-------

While the ``DispatchOptimizer`` handles single-timestep decisions, the
planning optimizer addresses inter-temporal dependencies:

- **Batteries** need to schedule charge and discharge across multiple
  intervals to maximize arbitrage revenue while respecting the SOC
  trajectory constraint.
- **Shiftable loads** (water heaters, EV chargers) benefit from
  shifting consumption from high-price to low-price intervals, subject
  to their respective constraints (tank temperature, departure SOC).

The planning optimizer produces a scheduled baseline that the real-time
agent tracks, with deviations allowed when real-time conditions differ
from the plan.

Battery Scheduling
------------------

The battery scheduling algorithm uses a **greedy value-ranking**
approach:

1. **Price forecast** — Obtain expected prices for each interval from
   the ``PriceForecastService`` or day-ahead advisory prices.

2. **Net value computation** — For each interval, compute the net value
   of charging and discharging:

   - Charge value: :math:`-(P_i + c_{deg}) \cdot \sqrt{\eta}` (cost of
     buying energy plus degradation, reduced by charge efficiency).
   - Discharge value: :math:`P_i \cdot \sqrt{\eta} - c_{deg}` (revenue
     from selling energy, reduced by discharge efficiency and degradation).

3. **Interval ranking** — Rank intervals by net value. The best
   intervals for charging have the lowest net charge cost; the best
   for discharging have the highest net discharge value.

4. **Greedy assignment** — Starting from the current SOC:

   a. Assign maximum discharge to the highest-value intervals.
   b. Assign maximum charge to the lowest-cost intervals.
   c. After each assignment, propagate the SOC trajectory forward
      to verify that BMS limits (``soc_min_bms``, ``soc_max_bms``)
      are never violated.
   d. If an assignment would cause SOC to go out of bounds at any
      future interval, reduce the assignment quantity.

5. **SOC trajectory validation** — The ``V_stored`` (stored energy)
   trajectory is tracked across all intervals. At every interval
   boundary, the SOC must remain within [``soc_min_bms``,
   ``soc_max_bms``].

**Output:** A ``PlanningResult`` containing:

- Per-interval scheduled power (kW, positive = charge, negative =
  discharge).
- Expected SOC trajectory.
- Total expected revenue, degradation cost, and net value.

Generic Load Shifting
---------------------

For non-battery shiftable loads, the planning optimizer provides a
simpler algorithm:

1. **Identify shiftable energy** — The total energy that must be
   consumed over the planning horizon but can be allocated flexibly
   across intervals. For example, an EV charger has a fixed energy
   requirement (kWh to reach target SOC) that can be spread across
   the plug-in window.

2. **Price-rank intervals** — Sort intervals by expected price
   (lowest first).

3. **Fill from cheapest** — Assign consumption to the cheapest
   intervals first, up to the device's maximum power and subject to
   any time-varying constraints (departure deadline for EVs, minimum
   temperature for water heaters).

4. **Constraint propagation** — Verify that the assigned schedule
   satisfies all hard constraints (e.g., target SOC by departure,
   minimum tank temperature at all times).

Integration with Real-Time Agent
--------------------------------

The planning optimizer's output serves as a **baseline schedule**
for the real-time agent:

- During NEGOTIATION phase, the agent uses the planned baseline when
  formulating bids for forward intervals.
- During DELIVERY phase, the dispatch optimizer uses the planned
  baseline as the starting point, adjusting for real-time price
  deviations.
- After each delivery, the plan can be re-optimized with updated
  forecasts and actual SOC/temperature state.

The relationship between planning and real-time is hierarchical:

::

   Planning Optimizer (hours-ahead)
       │
       └──► Baseline schedule for each interval
               │
               └──► Dispatch Optimizer (per-timestep)
                       │
                       └──► Adjusted setpoint for current interval
