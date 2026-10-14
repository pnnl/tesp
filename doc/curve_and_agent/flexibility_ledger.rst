.. _flexibility_ledger:

Flexibility Ledger
==================

The ``FlexibilityLedger`` class (``flexibility_ledger.py``) is the
single source of truth for how much of a device's operating range
is currently committed to market obligations. It tracks capacity
commitments across all active markets and provides three-tier
availability queries.

Commitment Lifecycle
--------------------

Each capacity commitment passes through the following statuses:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status
     - Description
   * - ``TENTATIVE``
     - Bid submitted but market not yet cleared. A hold is placed
       on the ledger to prevent over-commitment.
   * - ``ADVISORY``
     - Informational clearing received. The commitment is
       probabilistic — weighted by the convergence confidence.
   * - ``FIRM``
     - Binding clearing received. The commitment is obligatory
       and carries penalty risk for non-delivery.
   * - ``RELEASED``
     - Delivery complete and reconciled. Capacity freed.

Three-Tier Availability
-----------------------

The ledger provides three views of available capacity, each with
different risk tolerance:

Tier 1 — Hard Available
~~~~~~~~~~~~~~~~~~~~~~~~

Deducts **all** commitments (tentative, advisory, and firm) at full
quantity from the device's physical range:

.. math::

   Q_{hard,avail} = Q_{max,device} - \sum_{all} Q_{committed}

This is the most conservative view — it guarantees zero conflict with
any existing commitment. Used when the agent wants certainty that a
new commitment will not conflict with anything.

Tier 2 — Expected Available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Deducts each commitment weighted by its probability of being realized:

- FIRM commitments: deducted at 100%.
- ADVISORY commitments: deducted at their convergence confidence
  (e.g., 70% confidence → deduct 70% of the quantity).
- TENTATIVE commitments: deducted at a baseline probability
  (default 40%).

.. math::

   Q_{expected,avail} = Q_{max,device} - \sum_{firm} Q_i
   - \sum_{advisory} c_i \cdot Q_i
   - \sum_{tentative} w_{tent} \cdot Q_i

This represents a realistic planning estimate for "how much
flexibility do I likely have?" Used for bid formulation and planning.

Tier 3 — Economic Available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extends beyond physical availability by identifying **displaceable
blocks** — existing commitments that could be freed if a higher-value
opportunity arises:

.. math::

   Q_{economic,avail} = Q_{hard,avail} + \sum_{displaceable} Q_j

Each displaceable block has a **displacement cost**:

.. math::

   c_{displace} = marginal\_penalty_j - marginal\_net\_value_j

If the new opportunity's marginal value exceeds the displacement cost
of an existing commitment, it is economically rational to displace
the lower-value commitment.

Displaceable blocks are sorted by displacement cost (cheapest first),
creating a supply curve of freeable capacity.

``DisplaceableBlock``
~~~~~~~~~~~~~~~~~~~~~

Each displaceable block records:

- ``source_market`` — The market ID of the commitment that could be
  displaced.
- ``source_status`` — Current status (ADVISORY or FIRM).
- ``quantity`` — How much capacity could be freed (kW).
- ``displacement_cost`` — Net cost per kW of displacing.
- ``net_gain`` — Expected net gain from displacement.

``EconomicEnvelope``
~~~~~~~~~~~~~~~~~~~~

The ``query_economic()`` method returns an ``EconomicEnvelope``
containing:

- ``hard_Q_min_avail``, ``hard_Q_max_avail`` — Tier 1 bounds.
- ``displaceable_blocks`` — Sorted list of freeable blocks.
- ``total_displaceable`` — Sum of displaceable kW.
- ``soft_Q_max_avail`` — Tier 1 max + total displaceable.

Ledger Operations
-----------------

**hold_tentative()**
   Called when submitting a bid. Places a TENTATIVE hold on the
   ledger for the bid quantity. Prevents the same capacity from
   being bid into multiple markets simultaneously.

**update_to_advisory()**
   Called after receiving an informational clearing result. Updates
   the commitment status to ADVISORY with the convergence confidence
   and the advisory cleared price.

**promote_to_firm()**
   Called after receiving a binding clearing result. Promotes the
   commitment to FIRM status. The quantity becomes an obligation
   with penalty risk.

**release()**
   Called after reconciliation. Removes the commitment from the
   ledger, freeing the capacity for future use.

**query_hard()** / **query_expected()** / **query_economic()**
   Return the available capacity at each tier for a given time
   interval.

Integration with Bid Formulation
--------------------------------

During bid formulation (F4), the agent queries the ledger to determine
how much flexibility is available for the new bid:

1. Query ``expected_available`` for realistic capacity bounds.
2. Adjust the flexibility envelope: reduce Q_max by the expected
   committed quantity.
3. If needed, query ``economic_available`` for displacement
   opportunities — the bid curve can include capacity that would
   require displacing a lower-value commitment.
4. Place a ``TENTATIVE`` hold for the bid quantity.

This ensures that each bid reflects the actual remaining flexibility
after accounting for all prior commitments.
