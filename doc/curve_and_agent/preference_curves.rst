.. _preference_curves:

Preference Curves
=================

The ``PreferenceCurve`` class (``preference_curve.py``) encodes the
customer's willingness to trade amenity (comfort, convenience) for
financial benefit. It is device-type-agnostic — the same curve
formulation applies to all load-only devices, while batteries use a
specialized bidirectional form.

Customer Preference Factor *k*
------------------------------

Every device agent is configured with a customer preference factor
*k* ∈ [0, 1]:

- **k = 0** — Pure amenity: the customer prioritizes comfort/convenience
  above all. The preference curve is perfectly inelastic (the agent
  consumes at baseline regardless of price).
- **k = 1** — Pure financial: the customer maximizes savings by
  aggressively responding to price signals, even at the expense of
  comfort.
- **0 < k < 1** — Blended: intermediate responsiveness.

Standard Isoelastic Curve
--------------------------

For load-only devices (HVAC, water heater, EV charger), the preference
curve is an **isoelastic demand function**:

.. math::

   Q(P) = Q_0 \cdot \left(\frac{P}{P_0}\right)^{-\varepsilon}

Where:

- :math:`Q_0` = baseline power consumption (kW), from the flexibility
  envelope's ``Q_baseline``
- :math:`P_0` = reference price ($/kWh), typically the expected average
  retail rate
- :math:`\varepsilon` = price elasticity of demand, derived from *k*

The elasticity maps linearly from the customer preference:

.. math::

   \varepsilon = k \cdot \varepsilon_{max}

Where :math:`\varepsilon_{max}` is a system design parameter (default 5.0)
that sets the maximum responsiveness of the most financially-motivated
customer.

**Curve behavior:**

- At :math:`P = P_0`: :math:`Q = Q_0` (baseline consumption at the
  reference price).
- At :math:`P > P_0`: :math:`Q < Q_0` (reduce consumption when price
  is above average).
- At :math:`P < P_0`: :math:`Q > Q_0` (increase consumption when price
  is below average, e.g., pre-cooling or pre-heating).
- When bounded: the ``evaluate_with_bounds()`` method clamps the result
  to :math:`[Q_{min}, Q_{max}]` from the flexibility envelope.

Battery Sigmoid Curve
---------------------

For bidirectional devices (``BATTERY``), the preference curve is a
**sigmoid** that crosses zero:

.. math::

   Q(P) = Q_{charge,max} \cdot \frac{1 - (P / P_{threshold})^\varepsilon}{1 + (P / P_{threshold})^\varepsilon}

**Curve behavior:**

- At low prices (:math:`P \ll P_{threshold}`): :math:`Q \rightarrow
  Q_{charge,max}` (charge aggressively).
- At :math:`P = P_{threshold}`: :math:`Q = 0` (idle).
- At high prices (:math:`P \gg P_{threshold}`): :math:`Q \rightarrow
  -Q_{discharge,max}` (discharge to sell).

The threshold price :math:`P_{threshold}` is the reference price
:math:`P_0`. The degradation cost creates a *dead band* around this
threshold — the battery will not transition between charge and
discharge unless the price spread exceeds the marginal degradation
cost, preventing uneconomic cycling.

Amenity Cost
------------

The ``get_amenity_cost()`` method computes the "discomfort cost"
of operating at a point :math:`Q_{actual}` instead of the customer's
preferred point :math:`Q_{preferred}`:

.. math::

   C_{amenity} = (1 - k) \cdot P_0 \cdot (Q_{actual} - Q_{preferred})^2

This quadratic cost enters the dispatch optimizer's objective function.
Customers with low *k* (amenity-focused) impose a high penalty on
deviations from their preferred operating point, while customers with
high *k* (financially-focused) tolerate larger deviations.

Bid Curve Sampling
------------------

The ``sample_bid_curve()`` method converts the continuous preference
curve into a discrete bid curve suitable for market submission:

1. Sample *N* price points evenly spaced between ``price_min`` and
   ``price_max``.
2. Evaluate the preference curve at each price, clamped to the
   flexibility bounds.
3. Return a list of ``BidPoint(price, quantity)`` pairs ordered by
   decreasing price.

If an advisory price from a prior informational iteration is available,
it can be passed as ``price_focus`` to concentrate more sample points
near the expected clearing price for better resolution.

Curve Update Cycle
------------------

The preference curve is rebuilt each market cycle during bid
formulation (F3/F4):

1. **P₀ update** — The reference price is updated from the
   ``PriceForecastService``, which tracks price estimates across
   informational iterations.
2. **Q₀ update** — The baseline quantity comes from the latest
   flexibility envelope (F2).
3. **Degradation cost update** (battery only) — The dead band width
   is refreshed from ``BatteryModel.marginal_degradation_cost()``.
4. **Curve instantiation** — A new ``PreferenceCurve`` is created
   with the updated parameters.
5. **Sampling** — The curve is sampled into a ``BidCurve`` for
   submission.
