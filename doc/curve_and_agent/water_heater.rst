.. _water_heater:

Water Heaters
=============

The ``WATER_HEATER`` device type models a residential electric resistance
water heater. The agent exploits the tank's thermal storage capacity to
shift electricity consumption in response to market prices while
maintaining adequate hot water delivery.

Physics Model
-------------

The ``WaterHeaterModel`` implements a **two-zone stratified tank** model.
The tank is divided into upper and lower zones, reflecting the natural
thermal stratification in a vertical tank (hot water rises, cold water
settles at the bottom).

The model tracks two temperatures:

- :math:`T_{upper}` — Upper zone temperature (°F). Hot water is drawn
  from this zone.
- :math:`T_{lower}` — Lower zone temperature (°F). Cold inlet water
  enters here.

The temperature dynamics for each zone are:

.. math::

   C_{zone} \frac{dT}{dt} = -UA_{tank} \cdot (T - T_{ambient})
   - \dot{m}_{draw} \cdot c_p \cdot (T - T_{inlet})
   + Q_{element}

Where:

- :math:`C_{zone}` = thermal capacity of the zone (Btu/°F), derived
  from tank volume and zone height fraction
- :math:`UA_{tank}` = tank heat loss coefficient (Btu/hr·°F) to ambient
- :math:`\dot{m}_{draw}` = hot water draw rate (lb/hr), from draw forecast
- :math:`c_p` = specific heat of water (1 Btu/lb·°F)
- :math:`T_{inlet}` = cold water inlet temperature (°F)
- :math:`Q_{element}` = heating element output (Btu/hr)

The heating element converts electrical power to thermal energy at
100% efficiency:

.. math::

   Q_{element} = P_{element} \times 3412.14 \; \text{Btu/hr per kW}

Water Heater State
------------------

The agent reads the following state from GridLAB-D via
``read_water_heater_state()``:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Units
     - Description
   * - ``tank_temp_upper``
     - °F
     - Upper zone temperature
   * - ``tank_temp_lower``
     - °F
     - Lower zone temperature
   * - ``thermostat_setpoint``
     - °F
     - Tank thermostat setpoint
   * - ``element_on``
     - bool
     - Whether the heating element is active
   * - ``power_draw``
     - kW
     - Current electrical consumption
   * - ``tank_volume``
     - gal
     - Total tank volume
   * - ``tank_UA``
     - Btu/hr·°F
     - Tank heat loss coefficient
   * - ``element_power``
     - kW
     - Rated element power (typically 4.5 kW)
   * - ``inlet_water_temp``
     - °F
     - Incoming cold water temperature
   * - ``current_draw_rate``
     - gal/min
     - Current hot water demand
   * - ``tank_height``
     - ft
     - Tank height (for stratification geometry)

Flexibility Estimation (F2)
---------------------------

Water heater flexibility arises from the tank's ability to store
thermal energy. The agent estimates flexibility by simulating the
tank temperature trajectory under extreme operations:

**Q_max (maximum consumption)**
   Run the heating element at full power (``element_power``) continuously.
   Q_max is the element's rated power, subject to the upper temperature
   limit of the tank (typically 150–160°F for safety).

**Q_min (minimum consumption)**
   Turn the element off entirely and let the tank cool through standby
   losses and hot water draws. The model forecasts:

   1. Expected draw demand over the delivery interval (from the draw
      forecast — an ``EventForecast`` using a compound Poisson process).
   2. Standby heat loss through the tank walls.
   3. The resulting temperature trajectory.

   Q_min is 0 kW as long as the predicted upper zone temperature at
   the end of the interval remains above the minimum acceptable
   temperature (e.g., the setpoint minus the dead band).

**Q_baseline**
   The power consumption when the tank thermostat operates normally —
   cycling the element on and off to maintain the setpoint. This depends
   on the current tank temperature, draw forecast, and standby losses.

The draw forecast is the most significant driver of water heater
flexibility. During periods of expected low demand (e.g., overnight),
the tank can coast for hours without the element. During morning and
evening shower peaks, the flexibility window shrinks rapidly.

Probabilistic flexibility bounds use uncertainty in the draw forecast
— the compound Poisson event model provides quantiles of expected hot
water demand, and the temperature trajectory is simulated at each
quantile to produce ``Q_min_p50``, ``Q_min_p90``, and ``Q_min_p99``.

Control Translation (F8)
-------------------------

The water heater is controlled via its thermostat setpoint. The
``power_to_setpoint()`` method on the ``WaterHeaterModel`` implements:

1. **Target power → setpoint mapping** — If the target power is near
   ``element_power``, raise the setpoint above the current tank
   temperature (forces the element on). If the target power is near
   0 kW, lower the setpoint below the current tank temperature (forces
   the element off). Intermediate values map to setpoints that produce
   the desired duty cycle.

2. **Comfort bound enforcement** — The setpoint is constrained to a
   customer-specified range (e.g., 120–140°F) to prevent scalding or
   inadequate hot water.

3. **Pre-heating** — When the agent anticipates high prices during an
   upcoming peak draw period, it can raise the setpoint during a
   preceding low-price period to "charge" the tank with extra thermal
   energy. The pre-heated tank then coasts through the expensive period
   without needing the element.

Market Participation
--------------------

Water heaters are well-suited for:

- **RT Energy** — The element's binary on/off cycling makes it a
  natural fit for short-interval demand response. The tank's ~1–4 hour
  thermal time constant provides ample flexibility for 5-minute markets.
- **DA Energy** — Committing to average consumption levels across
  hourly intervals works naturally with the tank's thermal storage.
- **Spinning Reserve** — The element can be interrupted instantly
  (turned off) to provide reserve capacity. Restoration timing depends
  on how much thermal energy remains in the tank.

Key Characteristics
-------------------

- **Binary element** — The heating element is either on at full power
  or off. The agent's setpoint manipulation controls the *duty cycle*
  (fraction of time the element runs in a given interval) rather than
  continuous power modulation.
- **Asymmetric flexibility** — Turning the element off is always
  available (Q_min ≈ 0) until the tank cools to the comfort limit.
  Turning the element on requires the tank to be below the upper
  temperature limit.
- **Draw-driven dynamics** — Unlike HVAC where weather is the primary
  driver, water heater dynamics are dominated by the stochastic hot
  water draw pattern. The compound Poisson event forecast is the key
  data stream.
- **No export capability** — Water heaters can only consume or not
  consume. They cannot export power to the grid, so the flexibility
  envelope always has Q_min ≥ 0.
