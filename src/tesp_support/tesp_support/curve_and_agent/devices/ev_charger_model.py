# ============================================================================
# FILE: devices/ev_charger_model.py
# PURPOSE: Concrete device model for EV chargers (Level 2 AC EVSE with
#          managed charging).
#
# Implements the AbstractDeviceModel contract using a SOC dynamics model
# with BMS-imposed charge rate taper at high state of charge.
#
# THE CHARGING MODEL:
#     SOC dynamics:
#         dSOC/dt = (P_charge × η_charger) / E_capacity
#
#     Where:
#         P_charge   = AC charging power at the EVSE (kW)
#         η_charger  = charger AC-to-DC efficiency (typically 0.88–0.92)
#         E_capacity = EV battery nameplate capacity (kWh)
#
#     BMS charge rate taper:
#         The battery management system limits charge rate at high SOC
#         to protect cell longevity (CCCV charging profile):
#
#         P_max_effective(SOC) =
#             P_max_evse                          if SOC ≤ SOC_taper
#             P_max_evse × (1 − SOC)/(1 − SOC_taper)  if SOC > SOC_taper
#
#         Where SOC_taper is typically 0.80 (80%).
#
#     Minimum charge rate:
#         Many EVSEs cannot modulate below a minimum non-zero rate.
#         The charger is either OFF (0 kW) or at/above P_min (e.g., 1.4 kW).
#         This creates a discrete step in the feasibility envelope.
#
# GRIDLAB-D INTERFACE:
#     This model does NOT read from or write to GridLAB-D directly.
#     Note: GridLAB-D may not have a native EV charger model.  The
#     simulator interface may use a custom GridLAB-D object or a
#     co-simulated external EV model (via FNCS/HELICS).
#         F1 reads EVChargerState (SOC, charge rate, plug status)
#         F9 writes DeviceCommand (target charge rate)
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.device_model.AbstractDeviceModel
#     Uses:          abstractions.device_state.AbstractDeviceState
#                    (concretely expects devices.states.ConcreteEVChargerState)
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - devices/states.py: Provides ConcreteEVChargerState.
#     - forecasting/event_forecast.py: EV arrival forecast provides the
#       probability distribution of when the vehicle will arrive home
#       and at what SOC.  Consumed during DA planning when the vehicle
#       is not yet plugged in.
#     - forecasting/constraint_stream.py: Departure constraint
#       (deadline + minimum SOC) is the primary hard constraint.
#       Preferred SOC schedule defines the soft target.
#     - economics/planning_optimizer.py: Uses predict_soc() for
#       charge scheduling over the planning horizon.
#     - agent.py (DeviceAgent): Calls estimate_flexibility() during the
#       Active phase and translate_power_to_command() via the Command
#       Arbiter during delivery.
#
# CONSUMED FORECAST STREAMS (via forecasts dict):
#     'ev_arrival' — EventForecast, EXTERNAL from learned model.
#                    Provides arrival time distribution and arrival SOC
#                    distribution.  Only relevant when vehicle is not
#                    plugged in (for DA planning).  Once the vehicle
#                    arrives, the forecast is conditioned on the
#                    observation and uncertainty collapses.
#
# CONSUMED SCHEDULE STREAMS (via forecasts dict):
#     'ev_preferred_soc' — ContinuousForecast (effectively a constant),
#                          EXTERNAL from customer EV app.
#                          Defines the SOC the customer would like at
#                          departure (e.g., 90%).  The elastic range
#                          between the hard constraint (50%) and this
#                          preference (90%) is where the agent trades
#                          off charging cost against readiness.
#
# CONSUMED CONSTRAINT STREAMS (via constraints list):
#     'ev_departure_soc' — ConstraintStream, constraint_type='by_time',
#                          EXTERNAL from customer EV app.
#                          deadline = departure time (e.g., 7:00 AM)
#                          required_value = minimum SOC (e.g., 0.50)
#                          This is a HARD constraint.  The optimizer
#                          must guarantee SOC ≥ required_value at the
#                          deadline.  As the deadline approaches, Q_min
#                          in the flexibility envelope increases (the
#                          charger becomes increasingly must-run).
#     'ev_charge_rate_limits' — ConstraintStream, continuous=True,
#                               EXTERNAL from vehicle BMS specifications.
#                               SOC-dependent max charge rate.  Encoded
#                               as the taper curve described above.
# ============================================================================

"""Concrete EV charger device model — SOC dynamics with BMS taper.

The EV charger model has two distinctive characteristics:

1. **Deadline-driven flexibility:** Unlike HVAC or water heaters where
   flexibility is primarily weather-driven, the EV's flexibility is
   dominated by the time remaining until departure and the gap between
   current SOC and the departure constraint.  As the deadline approaches,
   Q_min increases and flexibility shrinks to zero (must-run).

2. **Discrete minimum charge rate:** The EVSE's inability to modulate
   below a minimum rate creates a step in the flexibility envelope:
   the device is either OFF or at/above P_min.  There is no feasible
   operating point between 0 and P_min.

Key methods:
    estimate_flexibility()        — F2: feasible charge rate range.
    translate_power_to_command()  — F8: convert target power to charge rate command.
    predict_soc()                 — Forward SOC trajectory at a given charge rate.
    power_to_command()            — Apply BMS taper and EVSE limits.
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from data_types import (
    DeviceCommand,
    FlexibilityEnvelope,
)
from enums_and_constants import DeviceType

class EVChargerModel:
    """Model of EV charging behavior including SOC-dependent taper.

    Models the charging process as constant-power up to the taper
    SOC, then linearly decreasing power above the taper point
    (CCCV charging profile approximation).
    """

    def predict_soc(
        self,
        state: EVChargerState,
        charge_power_kw: float,
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> list[tuple[float, float]]:
        """Predict SOC trajectory at a given charge power.

        Args:
            state: Current EV charger state from GridLAB-D.
                INTERNAL: From F1.
            charge_power_kw: Target charging power (kW).
                Applied as min(charge_power_kw, BMS-limited max at
                current SOC).
            duration_seconds: Prediction horizon.
            timestep_seconds: Integration timestep.

        Returns:
            List of (time_offset_seconds, predicted_soc).
        """
        if not state.vehicle_plugged_in:
            return [(0.0, state.soc)]

        soc = state.soc
        capacity = state.battery_capacity
        efficiency = state.charger_efficiency
        max_rate = state.max_charge_rate
        taper_soc = state.soc_at_max_taper

        trajectory: list[tuple[float, float]] = []
        n_steps = int(duration_seconds / timestep_seconds)
        dt_hr = timestep_seconds / 3600.0

        for i in range(n_steps):
            t = (i + 1) * timestep_seconds
            if soc >= taper_soc:
                taper_factor = max(0.0, (1.0 - soc) / (1.0 - taper_soc))
                effective_max = max_rate * taper_factor
            else:
                effective_max = max_rate

            actual_power = max(0.0, min(charge_power_kw, effective_max))
            dc_power = actual_power * efficiency
            delta_soc = dc_power * dt_hr / capacity
            soc = min(1.0, soc + delta_soc)
            trajectory.append((t, soc))

        return trajectory

    def estimate_flexibility(
        self,
        state: EVChargerState,
        departure_constraint: tuple[float, float] | None,
        preferred_soc: float,
        interval_duration: float,
        time_until_departure: float | None = None,
    ) -> FlexibilityEnvelope:
        """Estimate feasible charging power range.

        Q_min: minimum charge rate to meet departure SOC constraint
            in the remaining time (may be > 0 if deadline is close).
        Q_max: maximum charge rate allowed by EVSE and BMS.
        Q_baseline: charge rate to reach preferred SOC by departure.

        Args:
            state: Current EV charger state.
                INTERNAL: From F1.
            departure_constraint: (departure_time, min_soc) tuple.
                INTERNAL: From DataStreamManager constraint stream.
                EXTERNAL origin: Customer EV app input.
            preferred_soc: Customer's desired SOC (fraction).
                INTERNAL: From DataStreamManager schedule stream.
                EXTERNAL origin: Customer setting.
            interval_duration: Market interval (seconds).
            time_until_departure: Seconds until departure. If None,
                no departure constraint is applied.

        Returns:
            FlexibilityEnvelope. Q_min = 0 if no vehicle plugged in.
        """
        if not state.vehicle_plugged_in:
            return FlexibilityEnvelope(
                Q_min=0.0,
                Q_max=0.0,
                Q_baseline=0.0,
                interval_start=0.0,
                interval_end=interval_duration,
            )

        max_rate = state.max_charge_rate
        if state.soc >= state.soc_at_max_taper:
            taper = max(0.0, (1.0 - state.soc) / (1.0 - state.soc_at_max_taper))
            Q_max = max_rate * taper
        else:
            Q_max = max_rate

        Q_min = 0.0
        if (
            departure_constraint is not None
            and time_until_departure is not None
            and time_until_departure > 0
        ):
            _, target_soc = departure_constraint
            soc_needed = target_soc - state.soc
            if soc_needed > 0:
                energy_needed = (
                    soc_needed * state.battery_capacity / state.charger_efficiency
                )
                min_power = energy_needed / (time_until_departure / 3600.0)
                Q_min = min(min_power, Q_max)

        soc_gap = preferred_soc - state.soc
        if soc_gap > 0:
            energy = soc_gap * state.battery_capacity / state.charger_efficiency
            if time_until_departure and time_until_departure > 0:
                Q_baseline = min(energy / (time_until_departure / 3600.0), Q_max)
            else:
                Q_baseline = min(energy / (interval_duration / 3600.0), Q_max)
        else:
            Q_baseline = 0.0
        Q_baseline = max(Q_baseline, Q_min)

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    def power_to_command(self, target_power_kw: float, state: EVChargerState) -> float:
        """Convert target power to actual charge rate command.

        Applies BMS taper limits and EVSE min/max constraints.

        Args:
            target_power_kw: Desired power (kW).
                INTERNAL: From F7.
            state: Current state.
                INTERNAL: From F1.

        Returns:
            Actual charge rate to command (kW). May differ from
            target due to BMS limits.
        """
        if not state.vehicle_plugged_in:
            return 0.0

        if state.soc >= state.soc_at_max_taper:
            taper = max(0.0, (1.0 - state.soc) / (1.0 - state.soc_at_max_taper))
            effective_max = state.max_charge_rate * taper
        else:
            effective_max = state.max_charge_rate

        command = max(0.0, min(target_power_kw, effective_max))
        if 0 < command < state.min_charge_rate:
            command = 0.0
        return command