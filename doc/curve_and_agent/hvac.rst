.. _hvac:

HVAC Systems
============

The framework supports two HVAC device types: **HVAC_HEAT_PUMP** (heating
and cooling) and **HVAC_AC_ONLY** (cooling only). Both use the same
underlying physics model but differ in which operating modes produce
flexibility.

Physics Model
-------------

The ``HVACModel`` implements a two-node Equivalent Thermal Parameter (ETP)
model of a building. The two nodes represent:

- **Air mass** — Indoor air with thermal capacitance *Cₐ*.
- **Thermal mass** — Walls, furniture, and structure with capacitance *Cₘ*.

The governing differential equations are:

.. math::

   C_a \frac{dT_a}{dt} = UA_{env}(T_o - T_a) + UA_{mass}(T_m - T_a) + Q_{hvac} + Q_{solar} + Q_{internal}

   C_m \frac{dT_m}{dt} = UA_{mass}(T_a - T_m)

Where:

- :math:`T_a` = indoor air temperature (°F)
- :math:`T_m` = thermal mass temperature (°F)
- :math:`T_o` = outdoor air temperature (°F)
- :math:`UA_{env}` = envelope conductance (Btu/hr·°F)
- :math:`UA_{mass}` = mass-air conductance (Btu/hr·°F)
- :math:`Q_{hvac}` = HVAC thermal output (Btu/hr), negative for cooling
- :math:`Q_{solar}` = solar gain (Btu/hr)
- :math:`Q_{internal}` = internal gain (Btu/hr)

The model integrates these equations forward in time using Euler steps
to predict indoor temperature trajectories under different power inputs.

HVAC State
----------

The agent reads the following state from GridLAB-D via ``read_hvac_state()``:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Units
     - Description
   * - ``indoor_air_temp``
     - °F
     - Current indoor air temperature
   * - ``outdoor_air_temp``
     - °F
     - Current outdoor temperature (from climate object)
   * - ``thermostat_setpoint``
     - °F
     - Current thermostat setpoint
   * - ``hvac_mode``
     - —
     - Operating mode: 'heating', 'cooling', or 'off'
   * - ``power_draw``
     - kW
     - Current electrical consumption
   * - ``hvac_on``
     - bool
     - Whether the unit is actively running
   * - ``thermal_mass_temp``
     - °F
     - Temperature of the building thermal mass
   * - ``air_mass``
     - Btu/°F
     - Air thermal capacitance
   * - ``thermal_mass``
     - Btu/°F
     - Building mass thermal capacitance
   * - ``UA_envelope``
     - Btu/hr·°F
     - Envelope heat transfer coefficient
   * - ``UA_mass``
     - Btu/hr·°F
     - Mass-air heat transfer coefficient
   * - ``cooling_COP``
     - —
     - Coefficient of performance in cooling
   * - ``heating_COP``
     - —
     - Coefficient of performance in heating
   * - ``rated_cooling_capacity``
     - Btu/hr
     - Maximum cooling output
   * - ``rated_heating_capacity``
     - Btu/hr
     - Maximum heating output
   * - ``has_heat_pump``
     - bool
     - Whether heating is heat-pump or resistive
   * - ``solar_gain``
     - Btu/hr
     - Current solar heat gain
   * - ``internal_gain``
     - Btu/hr
     - Occupant and appliance heat gain

Flexibility Estimation (F2)
---------------------------

The HVAC model estimates flexibility by predicting the temperature
trajectory under two extreme scenarios:

**Q_max (maximum consumption)**
   Run the HVAC at full rated power. Predict the temperature trajectory
   and verify it stays within the customer's comfort band. Q_max equals
   the rated electrical power when the unit can run continuously without
   violating the upper comfort bound.

**Q_min (minimum consumption)**
   Turn the HVAC off entirely. Predict how quickly the indoor temperature
   drifts toward the outdoor temperature. Q_min is 0 kW as long as the
   predicted temperature at the end of the delivery interval remains within
   the comfort dead band.

**Q_baseline**
   The power consumption when tracking the customer's thermostat setpoint
   with no market consideration. This is the "normal" operating point.

The flexibility envelope for HVAC is asymmetric. In cooling mode during
summer, there is substantial room between Q_min (off) and Q_max (full
cooling), modulated by the building's thermal inertia. In mild weather,
flexibility shrinks because the unit barely runs at baseline.

The comfort band (dead band) around the thermostat setpoint defines the
hard constraint. Flexibility estimation uses forecast outdoor temperature,
solar gain, and internal gain to predict how long the building can coast
without HVAC input before hitting the dead band edge.

Probabilistic envelopes (``Q_min_p50``, ``Q_min_p90``, ``Q_min_p99``)
account for uncertainty in the weather forecast and internal gain
predictions at different confidence levels.

Control Translation (F8)
-------------------------

The HVAC is controlled via its thermostat setpoint. When the agent
determines a target power consumption :math:`Q^*` from the preference
curve:

1. **Power to setpoint mapping** — The model uses
   ``power_to_setpoint()`` to convert the power-domain operating point
   to a thermostat setpoint. In cooling mode, lower power means a higher
   setpoint (allow the building to warm up). Higher power means a lower
   setpoint (aggressive cooling).

2. **Dead band enforcement** — The resulting setpoint is clamped to the
   customer's comfort band (typically ±3–5°F around the programmed setpoint).

3. **Pre-cooling / pre-heating** — When the agent anticipates a
   period of high prices (from day-ahead advisory prices or price
   forecasts), it may shift the setpoint in the opposite direction
   during low-price periods: pre-cooling the building before an
   afternoon peak, or pre-heating before a morning peak.

The relationship between power and setpoint is non-linear because
the HVAC system cycles on and off; the ETP model captures this through
the effective average power at a given setpoint.

Market Participation
--------------------

HVAC systems most commonly participate in:

- **RT Energy** — 5-minute real-time energy market. The agent modulates
  power consumption within the thermal dead band.
- **DA Energy** — Hour-ahead or day-ahead energy. The agent commits to
  average consumption levels for hourly intervals.
- **Regulation** — Fast-response signal following. Limited by the
  thermal time constant of the building (typically 10–60 minutes),
  HVAC can provide short bursts of load increase or decrease.

The building's thermal inertia acts as inherent energy storage, enabling
the HVAC to shift consumption in time without violating comfort
constraints.

Heat Pump vs. AC-Only
---------------------

The ``HVAC_HEAT_PUMP`` type can provide flexibility in both heating and
cooling seasons. In heating mode, the heat pump's COP determines how
much electrical power is needed per unit of heating output. Flexibility
works in the reverse direction: reducing power means allowing the
building to cool slightly, while increasing power pre-heats.

The ``HVAC_AC_ONLY`` type provides flexibility only during cooling
season. When the system is in heating mode (if resistive backup exists),
the agent treats it as a non-flexible load since resistive heating has
COP ≈ 1 and no thermal storage benefit.
