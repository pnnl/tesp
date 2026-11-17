# ============================================================================
# FILE: forecasting/constraint_stream.py
# PURPOSE: Concrete implementation of hard constraint streams that the
#          agent must not violate under any circumstances.
#
# Constraints are fundamentally different from forecasts and schedules:
#
#     FORECAST:   "What will happen?"   (uncertain, probabilistic)
#     SCHEDULE:   "What does the customer want?"  (declared intent, soft)
#     CONSTRAINT: "What must not be violated?"  (hard boundary, binary)
#
# A constraint violation means the agent has failed its fundamental
# obligation — the EV owner can't drive to work, the water is unsafe
# to drink, or the battery can't power the house during an outage.
# No amount of financial compensation makes these acceptable.  The
# dispatch optimizer treats constraints as inviolable bounds on the
# feasible set, never as soft penalties to be traded off.
#
# CONSTRAINT TYPES:
#
#     MINIMUM (continuous):
#         "Variable must be at or above this value at ALL times."
#
#         Examples:
#             tank_temp_minimum: T_tank ≥ 120°F always.
#                 Source: Building code (Legionella prevention).
#                 Device: Water heater.
#
#             battery_soc_reserve: SOC ≥ 0.60 always.
#                 Source: Customer setting (backup resilience).
#                 Device: Battery.
#                 May be dynamic — higher during severe weather.
#
#             bms_soc_floor: SOC ≥ 0.10 always.
#                 Source: Battery management system (cell protection).
#                 Device: Battery, EV charger.
#
#     MAXIMUM (continuous):
#         "Variable must be at or below this value at ALL times."
#
#         Examples:
#             bms_soc_ceiling: SOC ≤ 0.95 always.
#                 Source: Battery management system (cell protection).
#                 Device: Battery, EV charger.
#
#             network_power_limit: P_device ≤ P_max_feeder always.
#                 Source: DSO network constraint signal.
#                 Device: Any (especially battery, EV charger).
#
#     BY_TIME (deadline):
#         "Variable must reach this value by a specific time."
#
#         Examples:
#             ev_departure_soc: SOC ≥ 0.50 by 7:00 AM.
#                 Source: Customer EV app (departure time + min SOC).
#                 Device: EV charger.
#                 This is the canonical deadline constraint.  As the
#                 deadline approaches, the feasible set shrinks — the
#                 charger becomes increasingly must-run.
#
#     EQUALITY (point):
#         "Variable must equal this value at a specific time."
#         Rare in practice.  Included for completeness.
#
# HOW CONSTRAINTS ARE CONSUMED:
#
#     F2 (Flexibility Estimation):
#         The device model receives a list of active constraints and
#         uses them to compute Q_min and Q_max.  For example:
#
#             Water heater: The minimum tank temperature constraint
#                 sets Q_min — the minimum heating power needed to
#                 keep the tank above 120°F given worst-case draws.
#
#             EV charger: The departure SOC constraint sets Q_min —
#                 the minimum charge rate needed to reach the required
#                 SOC by the deadline.  This Q_min increases as the
#                 deadline approaches (flexibility shrinks to zero).
#
#             Battery: The SOC reserve constraint sets the discharge
#                 floor — the battery cannot discharge below the
#                 reserve level, limiting Q_min (max discharge).
#
#     Planning Optimizer:
#         Constraints become inequality constraints in the multi-
#         interval optimization:
#             state[t] ≥ constraint.required_value    ∀t (continuous)
#             state[t_deadline] ≥ constraint.required_value (by_time)
#
#     Dispatch Optimizer:
#         Constraints appear as bounds on the feasible set:
#             Q_min ≤ Q ≤ Q_max
#         where Q_min and Q_max already incorporate constraint effects
#         (they were computed by F2 with constraints applied).
#
# FEASIBILITY CHECKING:
#
#     Two methods support constraint verification:
#
#         is_feasible(value, time) → bool
#             "Does this value satisfy the constraint at this time?"
#             Used for quick pass/fail checks.
#
#         feasibility_margin(value, time) → float
#             "How much slack exists?"
#             Positive = feasible with room (e.g., tank is 5°F above min).
#             Negative = violated (e.g., SOC is 2% below reserve).
#             Zero = exactly at the boundary.
#
#             Used by the device model to compute confidence-level
#             flexibility: Q_min_p90 is the power that keeps the
#             feasibility margin positive with 90% probability given
#             forecast uncertainty.
#
# DYNAMIC CONSTRAINTS:
#
#     Some constraints change over time:
#
#         battery_soc_reserve:
#             Normally 60%.  During a severe weather warning, the
#             customer or an automated system may raise it to 90%
#             (hold more reserve).  After the event passes, it
#             returns to 60%.  The constraint is updated via the
#             DataStreamManager.update_stream() mechanism.
#
#         network_power_limit:
#             The DSO may issue and revoke feeder capacity constraints
#             in real time based on transformer loading and voltage
#             conditions.  The constraint value changes when the DSO
#             sends an updated signal.
#
#         ev_departure_soc:
#             Set when the customer plugs in the vehicle and enters
#             departure time + minimum SOC in the EV app.  Changes
#             if the customer updates their plans.  Cleared when the
#             vehicle departs.
#
#     The ConstraintStream's required_value and deadline can be updated
#     at any time via the DataStreamManager.  The next time the device
#     model queries constraints, it sees the updated values.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from:
#         abstractions.data_streams.AbstractConstraintStream
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - forecasting/data_stream_manager.py:
#         The DataStreamManager holds ConstraintStream instances in its
#         constraint_streams dictionary.  Agents access them via
#         get_constraint(stream_id) and get_all_constraints(t_start, t_end).
#
#     - devices/water_heater_model.py:
#         WaterHeaterModel.estimate_flexibility() receives the
#         tank_temp_minimum constraint and uses it to compute Q_min:
#         the minimum element power needed to keep the tank above
#         120°F given the draw forecast and standby losses.
#
#     - devices/ev_charger_model.py:
#         EVChargerModel.estimate_flexibility() receives the
#         ev_departure_soc constraint and uses it to compute Q_min:
#         the minimum charge rate needed to reach the required SOC
#         by the deadline.  As time_until_departure shrinks, Q_min
#         approaches Q_max (must-run behavior).
#
#     - devices/battery_model.py:
#         BatteryModel.estimate_flexibility() receives the soc_reserve
#         and bms_limits constraints and uses them to bound the
#         discharge range: the battery cannot discharge below
#         max(soc_reserve, soc_min_bms).
#
#     - devices/hvac_model.py:
#         HVACModel normally does not have hard constraints (comfort
#         is soft, managed through the amenity cost function).  However,
#         if a hard temperature bound is configured (e.g., "never below
#         65°F for freeze protection"), it would appear as a constraint.
#
#     - economics/planning_optimizer.py:
#         The planning optimizer receives a list of constraints and
#         translates them into optimization inequality constraints
#         over the planning horizon.
#
#     - agent.py (DeviceAgent):
#         _handle_active() calls DataStreamManager.get_all_constraints()
#         and passes the results to estimate_flexibility().
#
#     - main.py:
#         The simulation harness constructs ConstraintStream objects
#         with customer-provided values and registers them with the
#         DataStreamManager.  Dynamic updates (weather alerts, DSO
#         signals, customer schedule changes) are pushed via
#         DataStreamManager.update_stream().
#
# DATA TYPES USED:
#     From abstractions/:
#         AbstractConstraintStream — the contract being implemented.
#
# EXTERNAL INPUTS:
#     All constraint values are EXTERNAL — provided by:
#
#         Customer input:
#             EV departure time and minimum SOC (from EV app).
#             Battery backup reserve SOC (from battery app/settings).
#             Preferred temperature floors (from thermostat program).
#
#         Building codes / regulations:
#             Minimum tank temperature (120°F for Legionella).
#             May vary by jurisdiction.
#
#         Device specifications:
#             BMS SOC floor and ceiling (from battery/EV manufacturer).
#             BMS charge rate limits as function of SOC and temperature.
#
#         DSO / grid operator:
#             Network power limits (from DSO constraint signals).
#             Updated dynamically based on grid conditions.
#
#         Automated systems:
#             Dynamic backup reserve (from outage probability model,
#             weather alert service, or customer-configured rules).
# ============================================================================

"""Concrete constraint stream — hard boundaries the agent must not violate.

Constraints are the non-negotiable boundaries of the agent's decision
space.  Unlike forecasts (uncertain) and schedules (soft preferences),
constraints are binary: satisfied or violated.  The dispatch optimizer
treats them as inviolable bounds, never as penalties to be traded off
against revenue.

Two key methods:
    is_feasible(value, time)       — Binary check: satisfied or not.
    feasibility_margin(value, time) — Continuous measure of slack.
                                      Positive = safe.  Negative = violated.

Supports four constraint types:
    MINIMUM (continuous)  — variable ≥ value at all times.
    MAXIMUM (continuous)  — variable ≤ value at all times.
    BY_TIME (deadline)    — variable ≥ value by a specific time.
    EQUALITY (point)      — variable = value at a specific time.
"""

from typing import Optional

from abstractions.data_streams import AbstractConstraintStream


from tesp_support.tesp_support.curve_and_agent.abstractions import AbstractConstraintStream
from tesp_support.tesp_support.curve_and_agent.enums_and_constants import DeviceType    


class ConstraintStream(AbstractConstraintStream):
    """A hard constraint that the agent must not violate.

    Constraints may be continuous (apply at all times) or deadline-based
    (must be satisfied by a specific time).

    Args:
        constraint_id: Unique identifier for this constraint.
        variable: What variable is constrained (e.g., 'soc', 'tank_temp').
        constraint_type: 'minimum', 'maximum', 'equality', 'by_time'.
        continuous: Whether the constraint applies at all times.
        deadline: For by_time constraints, the time by which the
            constraint must be satisfied.
            EXTERNAL: From customer input (e.g., EV departure time).
        required_value: The threshold or target value.
            EXTERNAL: From customer input (e.g., minimum SOC at departure).
    """

    def __init__(
        self,
        constraint_id: str,
        variable: str,
        constraint_type: str,
        continuous: bool = False,
        deadline: float | None = None,
        required_value: float = 0.0,
    ):
        self._constraint_id = constraint_id
        self._variable = variable
        self._constraint_type = constraint_type
        self._continuous = continuous
        self._deadline = deadline
        self._required_value = required_value

    def is_feasible(self, value_at_time: float, timestamp: float) -> bool:
        """Check if a given value satisfies this constraint at a given time.

        Args:
            value_at_time: The current or projected value of the
                constrained variable.
            timestamp: The time at which to check.

        Returns:
            True if the constraint is satisfied.
        """
        if self._constraint_type == "by_time":
            if self._deadline is not None and timestamp < self._deadline:
                return True
            return value_at_time >= self._required_value
        elif self._constraint_type == "minimum":
            return value_at_time >= self._required_value
        elif self._constraint_type == "maximum":
            return value_at_time <= self._required_value
        elif self._constraint_type == "equality":
            return abs(value_at_time - self._required_value) < 1e-9
        return True

    def feasibility_margin(self, value_at_time: float, timestamp: float) -> float:
        """How much slack exists at a given time.

        Args:
            value_at_time: Current or projected value.
            timestamp: Time of evaluation.

        Returns:
            Positive = feasible with room. Negative = violated.
        """
        if self._constraint_type in ("minimum", "by_time"):
            return value_at_time - self._required_value
        elif self._constraint_type == "maximum":
            return self._required_value - value_at_time
        elif self._constraint_type == "equality":
            return -abs(value_at_time - self._required_value)
        return 0.0