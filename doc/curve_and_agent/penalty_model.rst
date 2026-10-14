.. _penalty_model:

Penalty Model
=============

The ``PenaltyModel`` class (``penalty_model.py``) computes the cost
of non-delivery — the financial penalty when the agent's actual power
consumption differs from its committed quantity during a delivery
interval.

Purpose
-------

Penalties serve two roles:

1. **Incentive alignment** — Ensure agents deliver on their
   commitments. Without penalties, agents could bid speculatively
   and ignore clearing results.
2. **Dispatch input** — The marginal penalty gradient feeds into
   the dispatch optimizer's objective function, influencing the
   optimal operating point.

Penalty Structures
------------------

Four penalty structures are supported, selected per market:

Proportional
~~~~~~~~~~~~

Linear penalty proportional to the shortfall:

.. math::

   \text{penalty} = r \cdot |C - A|

Where :math:`C` = committed quantity, :math:`A` = actual delivery,
and :math:`r` = penalty rate ($/kW or $/kWh).

This is the simplest structure. The marginal penalty is constant at
:math:`r` regardless of shortfall magnitude.

Tiered
~~~~~~

Different penalty rates apply to different shortfall bands:

.. math::

   \text{penalty} = \sum_i r_i \cdot \min(\Delta_i, \max(0, |C - A| - T_i))

Where each tier *i* has a rate :math:`r_i` and a threshold :math:`T_i`
defining the start of that band. Rates typically increase with
shortfall magnitude — a small deviation incurs a mild rate, while
a large shortfall incurs progressively harsher rates.

Scored
~~~~~~

A performance score scales the payment rather than imposing a
separate penalty charge. The score degrades with increasing
shortfall:

.. math::

   \text{score} = \max(0, 1 - \beta \cdot |C - A| / C)

   \text{net\_payment} = \text{score} \cdot \text{gross\_revenue}

If the agent delivers perfectly, the score is 1.0 and full revenue
is received. As shortfall increases, the score decreases and revenue
is proportionally reduced. This structure is common in regulation
markets.

Compound
~~~~~~~~

A fixed fee plus a proportional component:

.. math::

   \text{penalty} = F + r \cdot |C - A|

Where :math:`F` = fixed non-performance fee (charged if any shortfall
exists) and :math:`r` = proportional rate. This creates a stronger
deterrent against even small shortfalls due to the discontinuous
fixed fee.

Penalty Evaluation
------------------

The ``compute_penalty()`` method takes a committed quantity and an
actual delivered quantity and returns the penalty cost in dollars.
It dispatches to the appropriate calculation based on the configured
``PenaltyStructureType``.

The ``marginal_penalty()`` method returns the penalty gradient at
a given delivery level — how much the penalty would change per
additional kW of delivery. This is the key input to the dispatch
optimizer.

Integration with Dispatch
-------------------------

The penalty model's outputs feed into the dispatch optimizer in
two ways:

1. **DeliveryValueCalculator** (F15) calls ``marginal_penalty()``
   to compute the ``marginal_penalty_zero`` (penalty rate at zero
   delivery) and penalty gradient for each active market delivery.
   These become part of the ``DeliveryEconomics`` structure.

2. **DispatchOptimizer** uses the marginal penalty values to balance
   delivery against amenity cost. Higher penalty rates pull the optimal
   point toward the committed quantity; lower rates allow the amenity
   cost to pull it toward the customer's preferred setpoint.

Configuration
-------------

Penalty models are configured per market when registering a market
with the device agent:

.. code-block:: python

   penalty = PenaltyModel(
       structure_type=PenaltyStructureType.TIERED,
       params={
           "tiers": [
               {"threshold": 0.0, "rate": 0.5},   # $/kW for first band
               {"threshold": 2.0, "rate": 1.5},    # $/kW above 2 kW shortfall
               {"threshold": 5.0, "rate": 5.0},    # $/kW above 5 kW shortfall
           ]
       }
   )

   agent.register_market(
       market_type=MarketType.RT_ENERGY,
       mode=OperatingMode.BIDDING,
       timing=timing_params,
       comm_interface=comm,
       penalty_model=penalty
   )
