# ============================================================================
# FILE: abstractions/__init__.py
# PURPOSE: Package-level re-exports for all abstract base classes.
#
# This is the public API of the abstractions package.  Consumers may
# import individual ABCs from their defining module for minimal coupling:
#
#     from abstractions.device_model import AbstractDeviceModel
#
# Or use the package-level convenience import for brevity:
#
#     from abstractions import AbstractDeviceModel
#
# Both resolve to the same class.  The per-module form is preferred
# inside the framework (minimizes transitive imports).  The package
# form is convenient in top-level scripts such as main.py.
#
# DEPENDENCY RULE:
#     This package has ZERO dependencies on any concrete implementation.
#     Every module in this package imports only from:
#       - Python standard library (abc, typing)
#       - enums_and_constants (shared enumerations)
#       - data_types (shared dataclasses)
#       - Other modules within this same abstractions/ package
#     No module here imports from devices/, simulators/, markets/,
#     economics/, forecasting/, or agent.py.
# ============================================================================

"""Abstractions package — pure interface contracts for the agent framework.

This package defines the abstract base classes (ABCs) that formalize the
contracts between all major components of the device agent system.  Every
concrete class in the framework inherits from exactly one ABC defined here.

The package is organized by architectural role:

    device_state.py           Physical state observed from the simulator.
    simulator_interface.py    Boundary between the agent and the physics
                              simulator (the only read/write point).
    device_model.py           Agent's internal belief about device physics.
    preference_curve.py       Price-to-quantity mapping (demand or offer).
    penalty_model.py          Non-delivery penalty economics.
    flexibility_ledger.py     Capacity commitment tracking (three-tier).
    market_communication.py   Agent ↔ Market Operator messaging.
    dispatch_optimizer.py     Per-timestep economic dispatch (F15 + F16).
    command_arbiter.py        Multi-market delivery merge and actuation.
    planning_optimizer.py     Multi-interval schedule optimization.
    price_forecast_service.py Evolving price estimates from info clears.
    data_streams.py           Forecasts, uncertainty models, constraints,
                              and the data stream manager.
    market_object.py          Per-market-cycle state machine.
    market_operator.py        Market clearing and DSO load estimation.
    device_agent.py           Top-level agent orchestrator.
"""

from abstractions.device_state import AbstractDeviceState
from abstractions.simulator_interface import AbstractSimulatorInterface
from abstractions.device_model import AbstractDeviceModel
from abstractions.preference_curve import AbstractPreferenceCurve
from abstractions.penalty_model import AbstractPenaltyModel
from abstractions.flexibility_ledger import AbstractFlexibilityLedger
from abstractions.market_communication import AbstractMarketCommunication
from abstractions.dispatch_optimizer import (
    AbstractDispatchOptimizer,
    AbstractDeliveryValueCalculator,
)
from abstractions.command_arbiter import AbstractCommandArbiter
from abstractions.planning_optimizer import AbstractPlanningOptimizer
from abstractions.price_forecast_service import AbstractPriceForecastService
from abstractions.data_streams import (
    AbstractForecast,
    AbstractContinuousForecast,
    AbstractEventForecast,
    AbstractUncertaintyModel,
    AbstractConstraintStream,
    AbstractDataStreamManager,
)
from abstractions.market_object import AbstractMarketObject
from abstractions.market_operator import (
    AbstractMarketOperator,
    AbstractDSOLoadEstimationEngine,
)
from abstractions.device_agent import AbstractDeviceAgent

__all__ = [
    "AbstractDeviceState",
    "AbstractSimulatorInterface",
    "AbstractDeviceModel",
    "AbstractPreferenceCurve",
    "AbstractPenaltyModel",
    "AbstractFlexibilityLedger",
    "AbstractMarketCommunication",
    "AbstractDispatchOptimizer",
    "AbstractDeliveryValueCalculator",
    "AbstractCommandArbiter",
    "AbstractPlanningOptimizer",
    "AbstractPriceForecastService",
    "AbstractForecast",
    "AbstractContinuousForecast",
    "AbstractEventForecast",
    "AbstractUncertaintyModel",
    "AbstractConstraintStream",
    "AbstractDataStreamManager",
    "AbstractMarketObject",
    "AbstractMarketOperator",
    "AbstractDSOLoadEstimationEngine",
    "AbstractDeviceAgent",
]