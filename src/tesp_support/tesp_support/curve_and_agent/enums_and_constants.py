# ============================================================================
# FILE: enums_and_constants.py
# PURPOSE: Shared enumerations and constants used across all modules
# ============================================================================

from enum import Enum, auto


class MarketType(Enum):
    """Classification of market products the agent can participate in."""
    RT_ENERGY = auto()          # Real-time energy (e.g., 5-minute intervals)
    DA_ENERGY = auto()          # Day-ahead energy (e.g., hourly intervals)
    REGULATION = auto()         # Frequency regulation (fast signal-following)
    SPINNING_RESERVE = auto()   # Spinning reserve (capacity held for contingency)


class MarketPhase(Enum):
    """States of the market object state machine.
    
    Lifecycle: INACTIVE -> ACTIVE -> NEGOTIATION -> MARKET_LEAD -> 
               ASSESSMENT -> (loop back to ACTIVE if informational, 
               or forward to DELIVERY_LEAD if binding) ->
               DELIVERY_LEAD -> DELIVERY -> RECONCILE -> EXPIRED
    """
    INACTIVE = auto()
    ACTIVE = auto()
    NEGOTIATION = auto()
    MARKET_LEAD = auto()
    ASSESSMENT = auto()         # Decision point: informational vs binding
    DELIVERY_LEAD = auto()
    DELIVERY = auto()
    RECONCILE = auto()
    EXPIRED = auto()


class OperatingMode(Enum):
    """How the device agent interacts with a given market product.
    
    BIDDING: Full participation — formulates and submits bid curves,
             responds to cleared price consistent with submitted bid.
    PRICE_RESPONSIVE: No bid submission — responds to cleared/observed
                      prices using the preference curve directly.
    OVERRIDE: Ignores market signals — tracks customer amenity setpoint.
    """
    BIDDING = auto()
    PRICE_RESPONSIVE = auto()
    OVERRIDE = auto()


class IterationType(Enum):
    """Classification of a market clearing iteration.
    
    INFORMATIONAL: Price discovery only. No delivery obligation.
                   Results stored as advisory data.
    BINDING: Final iteration. Creates firm delivery obligation.
    """
    INFORMATIONAL = auto()
    BINDING = auto()


class CommitmentStatus(Enum):
    """Lifecycle status of a capacity commitment on the flexibility ledger.
    
    TENTATIVE: Bid submitted but market not yet cleared.
    ADVISORY: Informational clear received; commitment is probabilistic.
    FIRM: Binding clear received; commitment is obligatory.
    RELEASED: Delivery complete and reconciled; capacity freed.
    """
    TENTATIVE = auto()
    ADVISORY = auto()
    FIRM = auto()
    RELEASED = auto()


class DeviceType(Enum):
    """Types of physical devices the agent can manage."""
    HVAC_HEAT_PUMP = auto()
    HVAC_AC_ONLY = auto()
    WATER_HEATER = auto()
    EV_CHARGER = auto()
    BATTERY = auto()


class ProductType(Enum):
    """Classification of what a commitment represents."""
    ENERGY_BASE = auto()        # Base energy consumption/production
    REGULATION_UP = auto()      # Upward regulation capacity
    REGULATION_DOWN = auto()    # Downward regulation capacity
    RESERVE_UP = auto()         # Upward reserve capacity
    RESERVE_DOWN = auto()       # Downward reserve capacity


class ForecastParadigm(Enum):
    """How a data stream represents forward-looking information."""
    CONTINUOUS = auto()         # Smoothly varying physical quantity
    EVENT = auto()              # Discrete occurrences at random times
    HYBRID = auto()             # Combination (e.g., occupancy)


class StreamType(Enum):
    """Classification of exogenous data streams."""
    FORECAST = auto()           # Best estimate of uncontrollable variable
    SCHEDULE = auto()           # Customer-declared intent/preference
    CONSTRAINT = auto()         # Hard boundary that must not be violated


class PenaltyStructureType(Enum):
    """How non-delivery penalties are calculated."""
    PROPORTIONAL = auto()       # Linear penalty per unit shortfall
    TIERED = auto()             # Different rates for different shortfall bands
    SCORED = auto()             # Performance score degrades payment
    COMPOUND = auto()           # Fixed + proportional