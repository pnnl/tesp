.. _dispatch_optimizer:

Dispatch Optimizer
==================

The ``DispatchOptimizer`` and ``DeliveryValueCalculator`` classes
(``dispatch_optimizer.py``) handle the real-time economic dispatch
problem: given multiple active delivery obligations, determine the
single optimal operating point for the device each timestep.

Problem Statement
-----------------

When a device has simultaneous deliveries across multiple market
products (e.g., RT energy and regulation), the agent must determine
a single power setpoint :math:`Q^*` that maximizes total net value:

.. math::

   \max_{Q} \; \sum_m \text{revenue}_m(Q_m) - \sum_m \text{penalty}_m(C_m, A_m) - C_{amenity}(Q)

Subject to:

.. math::

   Q_{min} \leq Q \leq Q_{max}

Where:

- :math:`Q_m` = power allocated to market *m*
- :math:`C_m` = committed quantity for market *m*
- :math:`A_m` = actual delivered quantity for market *m*
- :math:`C_{amenity}(Q)` = customer amenity cost from the preference curve
- :math:`Q_{min}, Q_{max}` = physical device limits

Delivery Economics (F15)
------------------------

The ``DeliveryValueCalculator`` computes the ``DeliveryEconomics``
for each active market delivery:

**Marginal Revenue**
   Revenue earned per kW of delivery. For energy: the cleared price
   times the interval duration. For regulation or reserve: the
   capacity payment rate.

**Marginal Penalty at Zero Delivery**
   The penalty rate if the agent delivers nothing. This quantifies
   the worst-case cost of non-delivery and helps the dispatch
   optimizer prioritize among competing obligations.

**Marginal Penalty Gradient**
   How the penalty changes with each additional kW of delivery.
   Used by the optimizer to find the point where marginal penalty
   reduction equals marginal amenity cost.

**Marginal Net Value**
   Revenue minus penalty gradient. Positive means delivering more
   increases net value; negative means delivering more is wasteful.

**Displacement Cost**
   If delivering to this market requires displacing another
   commitment, the net cost of that displacement.

Solution Methods
----------------

The optimizer uses different strategies depending on the number of
simultaneous products:

**Single Product (Analytical)**
   The optimal :math:`Q^*` balances the penalty gradient against the
   amenity cost gradient:

   .. math::

      Q^* = \frac{w_{pen} \cdot C + w_{amenity} \cdot Q_0}{w_{pen} + w_{amenity}}

   Where :math:`C` = committed quantity, :math:`Q_0` = baseline
   (preferred) quantity, and the weights are the penalty rate and
   amenity weight respectively. Clamped to :math:`[Q_{min}, Q_{max}]`.

**Two Products (Analytical)**
   Same weighted-average approach but with the sum of committed
   quantities and penalty weights across both products.

**Three or More Products (LP/QP)**
   Formulated as a quadratic program with linear constraints. The
   objective is the sum of linear revenue terms, piecewise-linear
   penalty terms, and a quadratic amenity term. Solved using
   standard QP solvers.

Dispatch Solution
-----------------

The ``DispatchSolution`` returned by the optimizer contains:

- ``Q_star`` — Optimal total power setpoint (kW).
- ``per_market_Q`` — Allocation of power across markets.
- ``displacement_chain`` — If any markets were displaced, the chain
  of displaced commitments.
- ``total_net_value`` — Objective function value at the optimum.

**Allocation logic:** Markets are prioritized by marginal net value
(highest first). The optimizer allocates power to each market in
priority order, stopping when the total power reaches :math:`Q^*`.

Command Arbiter
---------------

The ``CommandArbiter`` class (``command_arbiter.py``) sits between the
dispatch optimizer and the GridLAB-D interface. It provides a single
point of actuation by:

1. Receiving the ``DispatchSolution`` from the optimizer.
2. Handling signal-following for fast-response products (regulation).
   If a regulation signal is active, the commanded power is adjusted
   within the committed regulation band.
3. Invoking the device model's control translation (F8) to convert
   the power-domain setpoint to a device-specific command.
4. Writing the command to GridLAB-D via the ``GridLABDInterface`` (F9).

If no markets are in the DELIVERY phase, the command arbiter falls
back to the customer's amenity setpoint (override mode).
