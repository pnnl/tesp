.. _data_streams:

Data Streams
============

The ``DataStreamManager`` and associated classes (``data_streams.py``)
provide the exogenous information that device agents need for
flexibility estimation, bid formulation, and planning. All forecast
and schedule content comes from external sources — the data stream
system provides the structure and uncertainty quantification.

Data Stream Types
-----------------

Each data stream is classified by its ``StreamType``:

**FORECAST**
   Best estimate of an uncontrollable variable (weather, solar
   generation, wholesale price).

**SCHEDULE**
   Customer-declared intent or preference (thermostat program,
   occupancy schedule, EV departure plan).

**CONSTRAINT**
   A hard boundary that the agent must not violate (minimum tank
   temperature, target SOC at departure, customer comfort band).

Forecast Paradigms
------------------

The framework models two paradigms for how quantities evolve:

Continuous Forecasts
~~~~~~~~~~~~~~~~~~~~

The ``ContinuousForecast`` class represents smoothly-varying
quantities: outdoor temperature, solar irradiance, electricity price,
internal gain, etc.

Each forecast provides:

- **Point forecast** — A time series of ``ContinuousDataPoint``
  objects, each with a timestamp, value, and lead time.
- **Uncertainty quantification** — An ``UncertaintyModel`` that
  computes the forecast standard deviation at each lead time.
- **Quantile retrieval** — Methods to get the forecast value at any
  quantile (e.g., p05, p50, p95) at any future time.

The ``get_point_forecast()`` method returns the time series. The
``get_quantile_forecast()`` method applies the uncertainty model to
produce quantile envelopes.

Event Forecasts
~~~~~~~~~~~~~~~

The ``EventForecast`` class represents discrete events that occur
at random times with random magnitudes: hot water draw events (shower,
dishwash, laundry), EV plug-in/plug-out events, occupancy transitions.

The event model uses a **compound Poisson process**:

- Events arrive at an average rate :math:`\lambda(t)` (events/hour),
  which may vary by time of day and day of week.
- Each event has a random duration and magnitude drawn from the
  ``EventDefinition`` parameters.
- The aggregate demand over an interval is the sum of all events'
  energy contributions.

Key methods:

- ``expected_demand()`` — Expected aggregate demand (kWh) over a
  given interval.
- ``demand_quantiles()`` — Quantile distribution of aggregate demand,
  accounting for Poisson count uncertainty and per-event magnitude
  uncertainty.
- ``sample_events()`` — Monte Carlo sampling of individual events for
  scenario analysis.

Constraint Streams
~~~~~~~~~~~~~~~~~~

The ``ConstraintStream`` class provides hard constraints with optional
uncertainty:

- **Expected value** — The most likely constraint value
  (e.g., departure time = 7:30 AM).
- **Quantiles** — If the constraint has uncertainty (customer may
  leave early or late), quantiles at configurable confidence levels.
- **Hard limit** — A floor/ceiling that must never be violated,
  regardless of uncertainty.

Common constraint streams:

- EV departure time and target SOC
- Water heater minimum delivery temperature
- HVAC comfort band boundaries
- Battery SOC reserve requirements

Uncertainty Model
-----------------

The ``UncertaintyModel`` class models how forecast uncertainty
(standard deviation) grows with lead time. Three functional forms
are supported:

**Saturating Exponential**

.. math::

   \sigma(\tau) = \sigma_\infty \cdot (1 - e^{-\tau / \tau_c})

Starts at zero uncertainty for current time and saturates at the
climatological standard deviation :math:`\sigma_\infty` over a
correlation time :math:`\tau_c`. Suitable for weather variables.

**Power Law**

.. math::

   \sigma(\tau) = \min(\sigma_\infty, \; \sigma_0 + \alpha \cdot \tau^\beta)

Starts at measurement uncertainty :math:`\sigma_0` and grows as a
power of lead time. The exponent :math:`\beta` typically ranges from
0.5 to 1.0. Suitable for price forecasts.

**Empirical**

A lookup table of (lead_time, sigma) pairs with linear interpolation.
Suitable when analytical forms do not fit the error characteristics.

Data Stream Manager
-------------------

The ``DataStreamManager`` is a registry that holds all data streams
for a device agent. It provides a unified interface for the agent to
query any stream by name:

.. code-block:: python

   ds = DataStreamManager()
   ds.register("outdoor_temp", ContinuousForecast(
       forecast_data=temp_forecast,
       uncertainty=UncertaintyModel("saturating_exp", {
           "sigma_inf": 5.0, "tau_c": 14400.0
       })
   ))
   ds.register("hot_water_draws", EventForecast(
       event_types=[shower_def, dishwash_def],
       rate_schedule=draw_rate_by_hour
   ))
   ds.register("ev_departure", ConstraintStream(
       expected=departure_time,
       quantiles={0.05: early_departure, 0.95: late_departure}
   ))

The agent's flexibility estimation (F2) and planning functions query
the manager for the streams they need, using the stream name as a key.

Device-Specific Streams
-----------------------

Each device type requires different data streams:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Device
     - Required Streams
   * - HVAC
     - Outdoor temperature forecast, solar gain forecast, internal gain
       forecast, thermostat schedule (customer setpoints by time of day),
       price forecast
   * - Water Heater
     - Hot water draw event forecast (compound Poisson), inlet water
       temperature, thermostat setpoint schedule, price forecast
   * - EV Charger
     - Departure time constraint, target SOC constraint, plug-in event
       forecast, price forecast
   * - Battery
     - Price forecast (most critical), solar generation forecast
       (if paired with PV), household load forecast, cell temperature
       forecast
