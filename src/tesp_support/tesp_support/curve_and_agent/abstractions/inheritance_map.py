# ============================================================================
# FILE: inheritance_map.py
# PURPOSE: Quick-reference showing the complete inheritance hierarchy.
#          This file is documentation only — it is not imported by any
#          production code.
# ============================================================================

"""
INHERITANCE HIERARCHY
=====================

AbstractDeviceState
├── ConcreteHVACState           (HVACState dataclass + ABC contract)
├── ConcreteWaterHeaterState    (WaterHeaterState dataclass + ABC contract)
├── ConcreteEVChargerState      (EVChargerState dataclass + ABC contract)
└── ConcreteBatteryState        (BatteryState dataclass + ABC contract)

AbstractSimulatorInterface
└── GridLABDInterface           (GridLAB-D via FNCS/HELICS/direct API)

AbstractDeviceModel
├── HVACModel                   (2-node ETP thermal model)
├── WaterHeaterModel            (stratified tank model)
├── EVChargerModel              (SOC + BMS taper model)
└── BatteryModel                (SOC + bidirectional + degradation)

AbstractPreferenceCurve
├── IsoelasticPreferenceCurve   (Q = Q₀·(P/P₀)^{-ε} — for loads)
└── BidirectionalPreferenceCurve (sigmoid with dead band — for batteries)

AbstractPenaltyModel
├── ProportionalPenaltyModel    (rate × shortfall — RT/DA energy)
├── TieredPenaltyModel          (band-dependent rates)
├── ScoredPenaltyModel          (performance score — regulation)
└── CompoundPenaltyModel        (fixed + proportional — reserves)

AbstractUncertaintyModel
├── SaturatingExpUncertaintyModel   (σ(τ) = σ_∞·(1−e^{−τ/τ_c}))
├── PowerLawUncertaintyModel        (σ(τ) = min(σ_∞, σ₀ + α·τ^β))
└── EmpiricalUncertaintyModel       (lookup table interpolation)

AbstractForecast
├── AbstractContinuousForecast
│   └── ContinuousForecast      (temperature, price, solar, etc.)
└── AbstractEventForecast
    └── EventForecast            (showers, EV arrival, occupancy)

AbstractConstraintStream
└── ConstraintStream             (tank temp min, EV departure, SOC reserve)

AbstractDataStreamManager
└── DataStreamManager            (registry of all streams)

AbstractFlexibilityLedger
└── FlexibilityLedger            (three-tier: hard/expected/economic)

AbstractMarketCommunication
└── MarketCommunicationInterface (in-process or message-bus transport)

AbstractDispatchOptimizer
└── DispatchOptimizer            (analytical / LP / QP solver)

AbstractDeliveryValueCalculator
└── DeliveryValueCalculator      (energy, regulation, reserve economics)

AbstractCommandArbiter
└── CommandArbiter               (multi-market merge + single actuation)

AbstractPlanningOptimizer
└── PlanningOptimizer            (multi-interval LP/QP schedule)

AbstractPriceForecastService
└── PriceForecastService         (price store updated by info clears)

AbstractMarketObject
└── MarketObject                 (state machine + per-cycle data)

AbstractMarketOperator
└── MarketOperator               (retail market clearing)

AbstractDSOLoadEstimationEngine
└── DSOLoadEstimationEngine      (inflexible load estimation)

AbstractDeviceAgent
└── DeviceAgent                  (DER agent: HVAC, WH, EV, Battery)
"""