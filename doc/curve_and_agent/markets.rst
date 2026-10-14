.. _markets:

Market Mechanism
================

The framework implements a distribution-level retail market operated
by a Distribution System Operator (DSO). The market supports multiple
product types and uses an iterative clearing process to discover
prices.

Market Types
------------

Four market products are defined:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Market Type
     - Interval
     - Description
   * - ``RT_ENERGY``
     - 5 min
     - Real-time energy. Agents bid demand curves; clearing
       determines the retail price and each agent's consumption.
   * - ``DA_ENERGY``
     - 1 hour
     - Day-ahead energy. Agents commit to hourly average consumption
       levels. Typically cleared 12–24 hours before delivery.
   * - ``REGULATION``
     - 5 min
     - Frequency regulation. Agents commit a capacity band (±kW)
       and follow a real-time regulation signal during delivery.
   * - ``SPINNING_RESERVE``
     - 5 min
     - Spinning reserve. Agents hold capacity that can be activated
       within seconds if a contingency occurs.

Market Object State Machine
----------------------------

Each market cycle is managed by a ``MarketObject`` instance that
progresses through a well-defined state machine:

::

   INACTIVE ──► ACTIVE ──► NEGOTIATION ──► MARKET_LEAD ──► ASSESSMENT
                  ▲                                            │
                  │            (informational)                 │
                  └────────────────────────────────────────────┘
                                                               │
                              (binding)                        ▼
                                                        DELIVERY_LEAD
                                                               │
                                                               ▼
                                                          DELIVERY
                                                               │
                                                               ▼
                                                          RECONCILE
                                                               │
                                                               ▼
                                                           EXPIRED

**Phase descriptions:**

INACTIVE
   The market cycle has not yet started. Transitions to ACTIVE when
   the simulation time reaches ``t_activate``.

ACTIVE
   Data collection and preparation. The agent begins gathering
   forecasts and estimating flexibility.

NEGOTIATION
   The agent formulates and submits bids. This is the window in
   which the preference curve is sampled and the ``BidCurve`` is
   sent to the Market Operator.

MARKET_LEAD
   The Market Operator is processing bids. No agent action.

ASSESSMENT
   The Market Operator has cleared the market. The agent receives
   a ``ClearingResult`` and determines whether this iteration is
   **informational** (advisory) or **binding** (final).

   - If informational: the agent records an ``AdvisoryRecord``,
     updates the price forecast, and transitions back to ACTIVE
     for another iteration.
   - If binding: the agent promotes the commitment to FIRM and
     transitions to DELIVERY_LEAD.

DELIVERY_LEAD
   Preparation for delivery. The agent computes delivery economics
   and activates the dispatch optimizer.

DELIVERY
   Active delivery interval. Each timestep, the agent records
   actual power consumption and the dispatch optimizer resolves
   the operating point.

RECONCILE
   Post-delivery settlement. The agent computes fulfillment
   metrics and submits reconciliation data.

EXPIRED
   Terminal state. The market cycle is complete.

**Timing:** Phase transitions are driven by the ``MarketTimingParams``
structure, which specifies each transition as a time offset (in
seconds) relative to the market clearing time.

Market Operator
---------------

The ``MarketOperator`` class (``market_operator.py``) implements the
DSO's retail market clearing:

1. **Bid Collection** — Receives bid curves from all participating
   device agents and the ``DSOInflexibleLoadBid``.

2. **Demand Aggregation** — The ``aggregate_demand()`` method sums
   all individual demand curves point-by-point (at each price level,
   sum the quantities) to produce an aggregate demand curve.

3. **Supply-Demand Intersection** — The ``clear_market()`` method
   intersects the aggregate demand curve with the ``SupplyCurve``
   to find the equilibrium price and quantity.

4. **Result Propagation** — The ``propagate_results()`` method sends
   ``ClearingResult`` objects back to each agent and DSO bid
   component.

Clearing Algorithm
~~~~~~~~~~~~~~~~~~

The clearing algorithm iterates through price levels on the aggregate
demand curve and the supply curve, searching for the intersection
point where supply equals demand:

- Demand is a downward-sloping curve (lower quantity at higher prices).
- Supply is an upward-sloping curve (more supply available at higher
  prices).
- The intersection determines the clearing price and total quantity.

If no intersection is found (demand exceeds supply at all prices),
the clearing price is set to the supply curve's maximum price.

Informational Iteration
-----------------------

For day-ahead and other forward markets, the framework supports an
iterative price discovery process:

1. The Market Operator clears the market with initial bids and sends
   results as **INFORMATIONAL** (advisory only).
2. Each agent receives the advisory price, updates its forecast, and
   re-estimates flexibility with the new price information.
3. The agent submits an updated bid for the next iteration.
4. The Market Operator re-clears and sends new advisory prices.
5. This repeats until convergence or a fixed iteration count is reached.
6. The final iteration is marked as **BINDING**, creating firm
   delivery obligations.

**Iteration Type Determination:**

The Market Operator uses one of two protocols:

- **Fixed count** — Run a pre-specified number of informational
  iterations, then issue a binding clear.
- **Convergence** — Monitor the change in cleared price between
  iterations. When the price change falls below a tolerance threshold,
  issue a binding clear.

DSO Load Estimation
-------------------

The ``DSOLoadEstimationEngine`` constructs the ``DSOInflexibleLoadBid``
by estimating the aggregate inflexible load on the feeder:

.. math::

   Q_{inflexible} = Q_{gross} - Q_{flexible} + Q_{losses} - Q_{solar}

Where:

- :math:`Q_{gross}` = forecast total feeder gross load
- :math:`Q_{flexible}` = expected aggregate flexible device consumption
  (from advisory commitments and bids)
- :math:`Q_{losses}` = estimated distribution losses
- :math:`Q_{solar}` = aggregate behind-the-meter solar export

**Double-Counting Correction:**

A key challenge is that the flexible device consumption used to compute
the inflexible bid depends on the cleared price, which in turn depends
on the inflexible bid. The engine addresses this through an iterative
correction:

1. Initial estimate uses the previous clearing's flexible consumption.
2. After each informational iteration, update ``Q_{flexible}`` using
   the advisory commitments.
3. Re-compute the inflexible bid with the updated flexible estimate.
4. The convergence of the informational iteration process also
   converges the inflexible load estimate.

Supply Curve
------------

The ``SupplyCurve`` class represents the DSO's cost of wholesale
energy procurement. It is an upward-sloping price-quantity curve
where each point represents the marginal cost of procuring additional
energy from the wholesale market.

The supply curve is constructed externally by the DSO from:

- Wholesale market prices and procurement contracts
- Transmission charges
- Capacity allocations
- Distribution system costs

The ``MarketOperator`` uses the supply curve to find the clearing
price through supply-demand intersection.
