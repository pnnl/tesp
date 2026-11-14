# ============================================================================
# FILE: devices/battery_model.py
# PURPOSE: Concrete device model for home battery storage systems with
#          bidirectional operation and cycle-based degradation tracking.
#
# Implements the AbstractDeviceModel contract and adds battery-specific
# methods for degradation cost calculation, charge/discharge threshold
# computation, and degradation budget tracking.
#
# THE BATTERY MODEL:
#     SOC dynamics:
#         Charging:    dSOC/dt = +(P_charge × √η_rt) / E_capacity
#         Discharging: dSOC/dt = −(P_discharge / √η_rt) / E_capacity
#
#     Where:
#         P_charge, P_discharge = AC power at the inverter (kW)
#         η_rt      = round-trip AC-AC efficiency (split symmetrically
#                     between charge and discharge legs)
#         E_capacity = usable energy capacity (kWh), which degrades
#                     over time: E_usable = E_nameplate × SOH
#
#     BMS constraints:
#         SOC_min_bms ≤ SOC ≤ SOC_max_bms    (hard, always enforced)
#         |P| ≤ P_max_charge or P_max_discharge (rating limit)
#         |P| may taper at SOC extremes (similar to EV taper)
#
# DEGRADATION MODEL:
#     Three levels of fidelity are supported:
#
#     1. Throughput-based (default):
#         C_deg = C_replacement / (2 × E_lifetime)
#         per kWh of throughput (charge or discharge).
#
#     2. Stress-factor enhanced:
#         C_deg(SOC, P, T) = C_deg_base × f_soc(SOC) × f_rate(C_rate) × f_temp(T)
#         Where f_soc, f_rate, f_temp are multiplicative stress factors
#         that increase degradation cost at extreme SOC, high power,
#         and temperature extremes.
#
#     3. Full cycle-depth (Wöhler curve) with retrospective correction:
#         N(DoD) = N_ref × (DoD_ref / DoD)^κ
#         Shallow cycles are disproportionately cheaper than deep cycles.
#         Actual cycle depth is computed retrospectively using rainflow
#         counting, and C_deg_base is adjusted via feedback.
#
# GRIDLAB-D INTERFACE:
#     This model does NOT read from or write to GridLAB-D directly.
#         F1 reads BatteryState (SOC, power, cell_temp, SOH)
#         F9 writes DeviceCommand (inverter power setpoint)
#     Sign convention note: the agent uses positive = charging (consuming
#     from grid), negative = discharging (exporting).  GridLAB-D's inverter
#     may use the opposite convention (positive = export).  The simulator
#     interface handles the conversion.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.device_model.AbstractDeviceModel
#     Uses:          abstractions.device_state.AbstractDeviceState
#                    (concretely expects devices.states.ConcreteBatteryState)
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - devices/states.py: Provides ConcreteBatteryState.
#     - economics/preference_curves.py: BidirectionalPreferenceCurve
#       consumes degradation_cost from marginal_degradation_cost() to
#       set the dead-band width in the preference curve.
#     - economics/planning_optimizer.py: The planning optimizer is
#       ESSENTIAL for batteries — it produces V_stored (marginal value
#       of stored energy) at each interval, which drives the charge/
#       discharge thresholds in every bid and dispatch decision.
#       Uses predict_soc() for trajectory optimization.
#     - economics/dispatch_optimizer.py: The delivery value calculator
#       (F15) consumes marginal_degradation_cost() to include degradation
#       in the objective function.
#     - agent.py (DeviceAgent): Calls estimate_flexibility() during the
#       Active phase and translate_power_to_command() via the Command
#       Arbiter during delivery.  Also calls update_degradation_tracking()
#       during reconciliation (F13).
#
# CONSUMED FORECAST STREAMS (via forecasts dict):
#     'electricity_price' — ContinuousForecast, EXTERNAL from price
#                           forecast service (informational clears or
#                           historical data).  Fed to the planning
#                           optimizer to produce V_stored.
#     'btm_solar'         — ContinuousForecast, EXTERNAL from solar
#                           irradiance forecast + PV system specs.
#                           Determines when self-consumption charging
#                           is available.
#     'household_net_load'— ContinuousForecast, EXTERNAL from learned
#                           household load model.  Determines background
#                           load for demand charge management.
#
# CONSUMED SCHEDULE STREAMS (via forecasts dict):
#     'battery_preferred_soc' — ContinuousForecast (effectively a
#                               constant), EXTERNAL from customer setting.
#                               Defines the SOC the customer considers
#                               "comfortable" (e.g., 80%).  Deviations
#                               below this level incur amenity cost.
#
# CONSUMED CONSTRAINT STREAMS (via constraints list):
#     'soc_reserve'       — ConstraintStream, continuous=True,
#                           EXTERNAL from customer setting + dynamic
#                           outage risk.  Minimum SOC maintained at all
#                           times for backup resilience.  Default ≈ 60%.
#                           May increase during severe weather events.
#     'bms_limits'        — ConstraintStream, continuous=True,
#                           EXTERNAL from battery BMS specifications.
#                           SOC floor (e.g., 10%), SOC ceiling (e.g., 95%),
#                           and SOC/temperature-dependent power limits.
#
# DEVICE-SPECIFIC INITIALIZATION PARAMETERS:
#     replacement_cost  : float — Full battery replacement cost ($).
#     rated_cycles      : int   — Cycle life at rated DoD.
#     rated_dod         : float — Reference depth of discharge (fraction).
#     wohler_exponent   : float — Fatigue curve exponent (1.1–2.0 typical).
#     These are EXTERNAL from the battery manufacturer datasheet and/or
#     installer documentation.
# ============================================================================

"""Concrete battery device model — bidirectional SOC dynamics with degradation.

The battery model is unique among the device types in several ways:

1. **Bidirectional:** It can both consume (charge) and produce (discharge),
   requiring a flexibility envelope that spans negative to positive power.

2. **Degradation as operational cost:** Each kWh of throughput consumes
   battery life.  This cost (~$0.05–0.15/kWh depending on chemistry and
   conditions) is often comparable to arbitrage revenue and creates a
   natural dead band where the battery idles because cycling isn't
   profitable.

3. **Planning-dependent:** Unlike HVAC or water heaters where single-
   interval decisions are mostly self-contained, a battery's value
   depends entirely on future prices.  Charging 1 kWh now only has value
   if it can be discharged later at a higher price.  The planning
   optimizer (producing V_stored) is therefore essential, not optional.

4. **State-dependent stress:** Degradation cost varies with SOC, C-rate,
   and temperature.  The model tracks these stress factors to provide
   accurate marginal costs that shift the dead band dynamically.

Key methods:
    estimate_flexibility()                — F2: bidirectional power range.
    translate_power_to_command()           — F8: target power → inverter command.
    predict_soc()                          — Forward SOC trajectory.
    marginal_degradation_cost()            — Degradation $/kWh at current conditions.
    compute_charge_discharge_thresholds()  — Price thresholds from V_stored + degradation.
    update_degradation_tracking()          — Accumulate lifecycle consumption (for F13).
    budget_utilization_rate                — Actual vs planned life consumption ratio.
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from data_types import (
    DeviceCommand,
    FlexibilityEnvelope,
)
from enums_and_constants import DeviceType

class BatteryModel:
    """Model of a home battery storage system with degradation tracking.

    Handles:
    - SOC dynamics with charge/discharge efficiency
    - SOC-dependent power limits (BMS taper)
    - Degradation cost calculation (throughput-based with stress factors)
    - Marginal value of stored energy (from planning optimizer)
    """

    def __init__(
        self,
        replacement_cost: float = 10000.0,
        rated_cycles: int = 5000,
        rated_dod: float = 0.80,
        wohler_exponent: float = 1.5,
    ):
        """Initialize battery model with degradation parameters.

        Args:
            replacement_cost: Cost to replace the battery ($).
                EXTERNAL: From battery specifications / installer quote.
            rated_cycles: Cycle life at rated DoD.
                EXTERNAL: From manufacturer datasheet.
            rated_dod: Depth of discharge for rated cycle life (fraction).
                EXTERNAL: From manufacturer datasheet.
            wohler_exponent: Fatigue curve exponent for cycle depth
                adjustment. Higher values mean shallow cycles are
                disproportionately cheaper.
                EXTERNAL: From battery characterization data.
        """
        self._replacement_cost = replacement_cost
        self._rated_cycles = rated_cycles
        self._rated_dod = rated_dod
        self._wohler_exponent = wohler_exponent
        self._cumulative_throughput_kwh: float = 0.0
        self._cumulative_degradation_cost: float = 0.0
        self._energy_capacity: float = 13.5  # default; updated from state

    def predict_soc(
        self,
        state: BatteryState,
        power_kw: float,
        duration_seconds: float,
        timestep_seconds: float = 60.0,
    ) -> list[tuple[float, float]]:
        """Predict SOC trajectory at a given power level.

        Args:
            state: Current battery state from GridLAB-D.
                INTERNAL: From F1.
            power_kw: Power flow (kW). Positive = charging,
                negative = discharging.
            duration_seconds: Prediction horizon.
            timestep_seconds: Integration timestep.

        Returns:
            List of (time_offset_seconds, predicted_soc).
        """
        self._energy_capacity = state.energy_capacity
        soc = state.soc
        capacity = state.energy_capacity
        eta = math.sqrt(state.round_trip_efficiency)

        trajectory: list[tuple[float, float]] = []
        n_steps = int(duration_seconds / timestep_seconds)
        dt_hr = timestep_seconds / 3600.0

        for i in range(n_steps):
            t = (i + 1) * timestep_seconds
            if power_kw >= 0:
                energy_stored = power_kw * eta * dt_hr
            else:
                energy_stored = power_kw / eta * dt_hr
            soc += energy_stored / capacity
            soc = max(state.soc_min_bms, min(state.soc_max_bms, soc))
            trajectory.append((t, soc))

        return trajectory

    def estimate_flexibility(
        self,
        state: BatteryState,
        soc_reserve: float,
        soc_preferred: float,
        interval_duration: float,
    ) -> FlexibilityEnvelope:
        """Estimate feasible charge/discharge power range.

        Returns a bidirectional envelope where Q_min is negative
        (maximum discharge) and Q_max is positive (maximum charge).

        Args:
            state: Current battery state.
                INTERNAL: From F1.
            soc_reserve: Hard minimum SOC (backup reserve).
                INTERNAL: From DataStreamManager constraint stream.
                EXTERNAL origin: Customer setting, dynamic outage risk.
            soc_preferred: Customer's comfortable SOC level.
                INTERNAL: From DataStreamManager schedule stream.
                EXTERNAL origin: Customer setting.
            interval_duration: Market interval (seconds).

        Returns:
            FlexibilityEnvelope. Q_min < 0 (discharge), Q_max > 0 (charge).
        """
        self._energy_capacity = state.energy_capacity
        eta = math.sqrt(state.round_trip_efficiency)
        ih = interval_duration / 3600.0
        capacity = state.energy_capacity

        dischargeable = (state.soc - soc_reserve) * capacity
        if dischargeable > 0:
            max_discharge = min(state.max_discharge_rate, dischargeable / ih * eta)
        else:
            max_discharge = 0.0
        Q_min = -max_discharge

        chargeable = (state.soc_max_bms - state.soc) * capacity
        if chargeable > 0:
            max_charge = min(state.max_charge_rate, chargeable / (ih * eta))
        else:
            max_charge = 0.0
        Q_max = max_charge

        if abs(state.soc - soc_preferred) < 0.01:
            Q_baseline = 0.0
        elif state.soc < soc_preferred:
            needed = (soc_preferred - state.soc) * capacity
            Q_baseline = min(Q_max, needed / (ih * eta))
        else:
            excess = (state.soc - soc_preferred) * capacity
            Q_baseline = max(Q_min, -(excess * eta / ih))

        return FlexibilityEnvelope(
            Q_min=Q_min,
            Q_max=Q_max,
            Q_baseline=Q_baseline,
            interval_start=0.0,
            interval_end=interval_duration,
        )

    def marginal_degradation_cost(self, state: BatteryState, power_kw: float) -> float:
        """Compute the marginal degradation cost of cycling at given power.

        Accounts for:
        - Base throughput cost (replacement_cost / lifetime_throughput)
        - SOC stress factor (elevated at extreme SOC)
        - C-rate stress factor (elevated at high power)
        - Temperature stress factor (elevated at temperature extremes)

        Args:
            state: Current battery state (SOC, temperature).
                INTERNAL: From F1.
            power_kw: Absolute power magnitude (kW).

        Returns:
            Marginal degradation cost ($/kWh of throughput).
        """
        self._energy_capacity = state.energy_capacity
        capacity = state.energy_capacity
        lifetime_throughput = self._rated_cycles * self._rated_dod * capacity * 2.0
        base_cost = self._replacement_cost / lifetime_throughput

        soc_stress = 1.0 + 2.0 * (state.soc - 0.5) ** 2
        c_rate = abs(power_kw) / capacity
        crate_stress = 1.0 + 0.5 * c_rate
        temp_stress = 1.0 + 0.05 * abs(state.cell_temperature - 25.0)

        return base_cost * soc_stress * crate_stress * temp_stress

    def compute_charge_discharge_thresholds(
        self, state: BatteryState, V_stored: float, degradation_cost: float
    ) -> tuple[float, float]:
        """Compute the price thresholds for charging and discharging.

        Charge threshold: price below which charging is profitable.
        Discharge threshold: price above which discharging is profitable.
        The gap between them is the degradation-driven dead band.

        Args:
            state: Current battery state.
                INTERNAL: From F1.
            V_stored: Marginal value of stored energy ($/kWh).
                INTERNAL: From PlanningOptimizer output.
            degradation_cost: Current marginal degradation cost ($/kWh).
                INTERNAL: From self.marginal_degradation_cost().

        Returns:
            (charge_threshold, discharge_threshold) in $/kWh.
        """
        charge_threshold = V_stored - degradation_cost
        discharge_threshold = V_stored + degradation_cost
        return (charge_threshold, discharge_threshold)

    def update_degradation_tracking(
        self,
        throughput_kwh: float,
        avg_soc: float,
        avg_power_kw: float,
        avg_temperature: float,
        duration_seconds: float,
    ) -> float:
        """Update cumulative degradation tracking after delivery.

        Called during reconciliation (F13) to track actual battery
        life consumption.

        Args:
            throughput_kwh: Total energy throughput in the period.
            avg_soc: Average SOC during the period.
            avg_power_kw: Average absolute power during the period.
            avg_temperature: Average cell temperature (°C).
            duration_seconds: Length of the period.

        Returns:
            Degradation cost incurred in this period ($).
        """
        capacity = self._energy_capacity
        lifetime_throughput = self._rated_cycles * self._rated_dod * capacity * 2.0
        base_cost_per_kwh = self._replacement_cost / lifetime_throughput

        soc_stress = 1.0 + 2.0 * (avg_soc - 0.5) ** 2
        c_rate = avg_power_kw / capacity
        crate_stress = 1.0 + 0.5 * c_rate
        temp_stress = 1.0 + 0.05 * abs(avg_temperature - 25.0)

        cost = (
            base_cost_per_kwh * soc_stress * crate_stress * temp_stress * throughput_kwh
        )

        self._cumulative_throughput_kwh += throughput_kwh
        self._cumulative_degradation_cost += cost
        return cost

    @property
    def budget_utilization_rate(self) -> float:
        """Ratio of actual degradation rate to planned rate.

        > 1.0 means cycling faster than expected (raise costs).
        < 1.0 means cycling slower than expected (could lower costs).

        Returns:
            Budget utilization ratio.
        """
        if self._cumulative_throughput_kwh == 0.0:
            return 0.0
        capacity = self._energy_capacity
        lifetime_throughput = self._rated_cycles * self._rated_dod * capacity * 2.0
        base_cost_per_kwh = self._replacement_cost / lifetime_throughput
        actual_rate = (
            self._cumulative_degradation_cost / self._cumulative_throughput_kwh
        )
        return actual_rate / base_cost_per_kwh
