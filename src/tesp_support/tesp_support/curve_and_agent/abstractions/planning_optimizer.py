# ============================================================================
# FILE: abstractions/planning_optimizer.py
# PURPOSE: Abstract base class for multi-interval schedule optimization.
#
# The planning optimizer computes an optimal device operating schedule
# over a planning horizon (e.g., 24 hours for a day-ahead market).
#
# For different device types:
#     Battery:     Produces V_stored (marginal value of stored energy)
#                  at each interval — essential for arbitrage decisions.
#     HVAC:        Produces a pre-conditioning plan (pre-cool before
#                  expensive hours).
#     Water heater: Pre-heat before expected draw events.
#     EV:          Charge scheduling to meet departure constraint at
#                  minimum cost.
#     Generator:   Unit commitment schedule with startup/shutdown timing.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Uses: AbstractDeviceModel (trajectory prediction)
#             AbstractDeviceState (initial conditions)
#             AbstractConstraintStream (hard limits over horizon)
#     - Used by: AbstractDeviceAgent._handle_active() (DA planning)
#                AbstractDeviceAgent._handle_assessment() (re-plan after
#                    informational clear)
#                AbstractDeviceAgent.formulate_bid() (V_stored for
#                    battery charge/discharge thresholds)
#
# IMPORTS FROM:
#     - typing: Any, Dict, List, Tuple
#     - abstractions.device_model: AbstractDeviceModel
#     - abstractions.device_state: AbstractDeviceState
#     - abstractions.data_streams: AbstractConstraintStream
#     - data_types: PlanningResult
#     - enums_and_constants: DeviceType
# ============================================================================

"""Abstract planning optimizer — multi-interval schedule optimization.

The planning optimizer is essential for batteries (where V_stored
drives all charge/discharge threshold decisions) and beneficial for
all other device types (pre-conditioning, charge scheduling, etc.).
Informational market iterations provide the price trajectory that
makes planning meaningful.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from abstractions.data_streams import AbstractConstraintStream
from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from data_types import PlanningResult
from enums_and_constants import DeviceType

class AbstractPlanningOptimizer(ABC):
    """Abstract base for multi-interval schedule optimization.

    Computes an optimal device operating schedule over a planning
    horizon.  For batteries this produces the marginal value of stored
    energy (V_stored) at each interval.  For generators this produces a
    unit commitment schedule.  For thermal loads it produces a
    pre-conditioning plan.

    Args:
        device_model: Device physics model.
        device_type: Type of device.
    """

    def __init__(
        self,
        device_model: AbstractDeviceModel,
        device_type: DeviceType,
    ):
        self._device_model = device_model
        self._device_type = device_type

    @abstractmethod
    def solve(
        self,
        current_state: AbstractDeviceState,
        price_trajectory: List[Tuple[Tuple[float, float], float]],
        forecasts: Dict[str, Any],
        constraints: List[AbstractConstraintStream],
        interval_duration: float,
        planning_horizon: float,
        customer_preference_k: float,
        **kwargs: Any,
    ) -> PlanningResult:
        """Solve the multi-interval planning optimization.

        Args:
            current_state: Current device state from F1.
            price_trajectory: List of ((t_start, t_end), price) tuples.
                INTERNAL: From ``PriceForecastService.get_trajectory()``.
            forecasts: Forecast bundle from ``DataStreamManager``.
            constraints: Active constraints over the horizon.
            interval_duration: Planning interval length (seconds).
            planning_horizon: Total horizon length (seconds).
            customer_preference_k: Customer preference factor (0–1).
                EXTERNAL: Customer setting.
            **kwargs: Device-specific parameters (e.g., degradation model
                for batteries, startup costs for generators).

        Returns:
            ``PlanningResult`` with optimal schedule, V_stored (if
            applicable), expected costs, and expected revenues.
        """
        ...