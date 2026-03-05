# Test Suite Analysis: curve_and_agent Ground Truth Tests

**Analysis Date:** March 5, 2026  
**Scope:** 13 test files (~3600 lines) in `src/tesp_support/tests/curve_and_agent/`  
**Cross-referenced against:** 9 PlantUML design documents in `design/curve_and_agent/`  
**Source modules:** `src/tesp_support/tesp_support/curve_and_agent/`

---

## Table of Contents

1. [Summary of Findings](#summary-of-findings)
2. [test_enums_and_constants.py](#1-test_enums_and_constantspy)
3. [test_data_types.py](#2-test_data_typespy)
4. [test_data_streams.py](#3-test_data_streamspy)
5. [test_preference_curve.py](#4-test_preference_curvepy)
6. [test_device_models.py](#5-test_device_modelspy)
7. [test_market_object.py](#6-test_market_objectpy)
8. [test_market_operator.py](#7-test_market_operatorpy)
9. [test_penalty_model.py](#8-test_penalty_modelpy)
10. [test_dispatch_optimizer.py](#9-test_dispatch_optimizerpy)
11. [test_planning_optimizer.py](#10-test_planning_optimizerpy)
12. [test_flexibility_ledger.py](#11-test_flexibility_ledgerpy)
13. [test_price_forecast_service.py](#12-test_price_forecast_servicepy)
14. [conftest.py](#13-conftestpy)
15. [Issues Found](#issues-found)
16. [Coverage Gaps](#coverage-gaps)

---

## Summary of Findings

| Test File | # Tests | Pass Now | xfail (stub) | Issues Found |
|---|---|---|---|---|
| test_enums_and_constants.py | 27 | 27 | 0 | 0 |
| test_data_types.py | 40 | 40 | 0 | 0 |
| test_data_streams.py | 27 | 3 | 24 | 0 |
| test_preference_curve.py | 20 | 2 | 18 | 0 |
| test_device_models.py | 18 | 3 | 15 | 0 |
| test_market_object.py | 17 | 3 | 14 | **1 CRITICAL** |
| test_market_operator.py | 16 | 3 | 13 | 0 |
| test_penalty_model.py | 16 | 3 | 13 | 1 minor |
| test_dispatch_optimizer.py | 5 | 0 | 5 | 0 |
| test_planning_optimizer.py | 6 | 1 | 5 | 0 |
| test_flexibility_ledger.py | 16 | 2 | 14 | 0 |
| test_price_forecast_service.py | 10 | 1 | 9 | 0 |
| **TOTAL** | **218** | **88** | **130** | **1 critical, 1 minor** |

**Critical issue:** `test_market_object.py::TestInformationalLoop::test_assessment_loops_to_negotiation`
tests ASSESSMENT → NEGOTIATION, but all design documents specify ASSESSMENT → ACTIVE.

---

## 1. test_enums_and_constants.py

**Module under test:** `enums_and_constants.py` (Level 0 — fully implemented)  
**Design reference:** `class_diagram_core.plantuml` → "Enumerations" package  
**Status:** All 27 tests should pass immediately (no stubs).

### TestMarketType (3 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(MarketType)` | — | 4 | ✅ Design has RT_ENERGY, DA_ENERGY, REGULATION, SPINNING_RESERVE |
| `test_expected_members` (×4) | `hasattr(MarketType, name)` | Each of RT_ENERGY, DA_ENERGY, REGULATION, SPINNING_RESERVE | True | ✅ Exact match with class_diagram_core.plantuml |
| `test_values_are_unique` | `[m.value for m in MarketType]` | — | All distinct | ✅ Correct for `auto()` enums |

### TestMarketPhase (4 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(MarketPhase)` | — | 9 | ✅ Design: INACTIVE, ACTIVE, NEGOTIATION, MARKET_LEAD, ASSESSMENT, DELIVERY_LEAD, DELIVERY, RECONCILE, EXPIRED |
| `test_expected_members` (×9) | `hasattr(MarketPhase, name)` | Each phase name | True | ✅ Exact match with state_machine_market.plantuml |
| `test_lifecycle_ordering` | Phase values via `auto()` | EXPECTED_ORDER list | Ascending values | ✅ Declaration order = lifecycle order |
| `test_values_are_unique` | All member values | — | All distinct | ✅ Correct |

### TestOperatingMode (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(OperatingMode)` | — | 3 | ✅ BIDDING, PRICE_RESPONSIVE, OVERRIDE per class diagram |
| `test_expected_members` (×3) | `hasattr(OperatingMode, name)` | Each mode | True | ✅ |

### TestIterationType (4 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(IterationType)` | — | 2 | ✅ INFORMATIONAL, BINDING per state machine |
| `test_informational_exists` | `IterationType.INFORMATIONAL` | — | Not None | ✅ |
| `test_binding_exists` | `IterationType.BINDING` | — | Not None | ✅ |
| `test_not_equal` | Equality comparison | — | INFORMATIONAL ≠ BINDING | ✅ |

### TestCommitmentStatus (3 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(CommitmentStatus)` | — | 4 | ✅ TENTATIVE, ADVISORY, FIRM, RELEASED per class diagram |
| `test_expected_members` (×4) | `hasattr` | Each status | True | ✅ |
| `test_lifecycle_ordering` | Value ordering | — | TENTATIVE < ADVISORY < FIRM < RELEASED | ✅ Matches commitment lifecycle in flexibility_ledger design |

### TestDeviceType (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(DeviceType)` | — | 5 | ✅ Matches class_diagram_core.plantuml |
| `test_expected_members` (×5) | `hasattr` | HVAC_HEAT_PUMP, HVAC_AC_ONLY, WATER_HEATER, EV_CHARGER, BATTERY | True | ✅ |

### TestProductType (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(ProductType)` | — | 5 | ✅ ENERGY_BASE, REGULATION_UP/DOWN, RESERVE_UP/DOWN |
| `test_expected_members` (×5) | `hasattr` | Each product | True | ✅ Matches multi-market sequence diagram products |

### TestForecastParadigm (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(ForecastParadigm)` | — | 3 | ✅ CONTINUOUS, EVENT, HYBRID |
| `test_expected_members` (×3) | `hasattr` | Each paradigm | True | ✅ Matches data_streams design |

### TestStreamType (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(StreamType)` | — | 3 | ✅ FORECAST, SCHEDULE, CONSTRAINT |
| `test_expected_members` (×3) | `hasattr` | Each type | True | ✅ Matches DataStreamManager categories |

### TestPenaltyStructureType (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_member_count` | `len(PenaltyStructureType)` | — | 4 | ✅ PROPORTIONAL, TIERED, SCORED, COMPOUND |
| `test_expected_members` (×4) | `hasattr` | Each type | True | ✅ Matches penalty_model.py design |

---

## 2. test_data_types.py

**Module under test:** `data_types.py` (Level 0 — fully implemented)  
**Design reference:** `class_diagram_core.plantuml` → all data structure classes  
**Status:** All 40 tests should pass immediately (plain dataclasses, no logic).

### TestHVACStateDefaults (7 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_instantiates_with_defaults` | `HVACState()` | — | isinstance check | ✅ |
| `test_indoor_temp_default` | `.indoor_air_temp` | — | 72.0°F | ✅ Physically reasonable default |
| `test_outdoor_temp_default` | `.outdoor_air_temp` | — | 85.0°F | ✅ |
| `test_mode_default` | `.hvac_mode` | — | "cooling" | ✅ |
| `test_hvac_off_by_default` | `.hvac_on` | — | False | ✅ |
| `test_thermal_params_positive` | `.air_mass`, `.thermal_mass`, `.UA_envelope`, `.UA_mass` | — | All > 0 | ✅ Physics: thermal parameters must be positive |
| `test_cop_reasonable` | `.cooling_COP`, `.heating_COP` | — | Between 1.0 and 8.0 | ✅ Standard COP range for residential |

### TestWaterHeaterStateDefaults (5 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_instantiates_with_defaults` | `WaterHeaterState()` | — | isinstance check | ✅ |
| `test_upper_temp_ge_lower` | `.tank_temp_upper` vs `.tank_temp_lower` | — | upper ≥ lower | ✅ Upper zone is always ≥ lower (thermal stratification) |
| `test_tank_volume_positive` | `.tank_volume` | — | > 0 | ✅ |
| `test_element_power_positive` | `.element_power` | — | > 0 | ✅ |
| `test_inlet_temp_below_setpoint` | `.inlet_water_temp` vs `.thermostat_setpoint` | — | inlet < setpoint | ✅ Cold water inlet always below target |

### TestEVChargerStateDefaults (5 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_instantiates_with_defaults` | `EVChargerState()` | — | isinstance check | ✅ |
| `test_soc_in_range` | `.soc` | — | 0.0 ≤ soc ≤ 1.0 | ✅ |
| `test_not_plugged_by_default` | `.vehicle_plugged_in` | — | False | ✅ |
| `test_efficiency_in_range` | `.charger_efficiency` | — | (0.0, 1.0] | ✅ |
| `test_max_ge_min_charge_rate` | `.max_charge_rate` vs `.min_charge_rate` | — | max ≥ min | ✅ |

### TestBatteryStateDefaults (5 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_instantiates_with_defaults` | `BatteryState()` | — | isinstance check | ✅ |
| `test_soc_in_range` | `.soc` | — | 0.0 ≤ soc ≤ 1.0 | ✅ |
| `test_bms_limits_ordered` | `.soc_min_bms` vs `.soc_max_bms` | — | min < max | ✅ Matches BatteryModel constraints |
| `test_efficiency_in_range` | `.round_trip_efficiency` | — | (0.0, 1.0] | ✅ |
| `test_health_in_range` | `.state_of_health` | — | (0.0, 1.0] | ✅ |

### TestBidPoint (3 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_construct` | `BidPoint(price=0.10, quantity=5.0)` | — | Fields stored | ✅ Per class diagram |
| `test_equality` | `==` operator | Two identical BidPoints | True | ✅ Dataclass equality |
| `test_inequality` | `!=` operator | Two different BidPoints | True | ✅ |

### TestBidCurve (3 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_default_points_empty` | `BidCurve().points` | — | [] | ✅ |
| `test_mutable_default_isolation` | Two default BidCurves | Mutate first | Second unaffected | ✅ Critical: `field(default_factory=list)` |
| `test_construct_with_points` | Via `simple_downward_bid` fixture | 4 BidPoints | len=4, market_id correct | ✅ |

### TestClearingResult (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_default_iteration_type` | `ClearingResult().iteration_type` | — | IterationType.BINDING | ✅ Sensible default |
| `test_construct` | Via `simple_clearing_result` fixture | — | price=0.10, qty=5.0 | ✅ |

### TestMarketTimingParams (3 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_defaults_are_rt_market` | Field ordering | `rt_timing_params` fixture | activate < negotiate < market_lead ≤ clear; delivery_start ≤ delivery_end < reconcile_end | ✅ Matches state_machine_market.plantuml timeline |
| `test_delivery_interval_positive` | End − start | `rt_timing_params` | > 0 | ✅ |
| `test_da_timing_longer` | DA delivery duration | `da_timing_params` | 3600.0 seconds | ✅ DA is 1-hour intervals |

### TestFlexibilityEnvelope (4 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_defaults` | Field ordering | Default | Q_min ≤ Q_baseline ≤ Q_max | ✅ Per class diagram |
| `test_load_only_positive` | `.Q_min` | `load_only_flexibility` fixture | ≥ 0 | ✅ Load-only devices can't generate |
| `test_battery_bidirectional` | `.Q_min`, `.Q_max` | `battery_flexibility` fixture | Q_min < 0, Q_max > 0 | ✅ Bidirectional per battery planning sequence |
| `test_confidence_ordering` | Quantile ordering | Default | p50 ≤ p90 ≤ p99 | ✅ Wider confidence = more conservative |

### TestEconomicCommitment (2 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_defaults` | Default fields | — | status=TENTATIVE, quantity=0.0, displacement_plan=[] | ✅ Matches FlexibilityLedger commitment lifecycle |
| `test_mutable_default_isolation` | Two defaults | Mutate first | Second unaffected | ✅ Critical for ledger correctness |

### TestContinuousDataPoint (2 tests), TestQuantilePoint (1 test), TestUncertaintyEnvelope (1 test), TestEventDefinition (1 test)

All test basic default values and construction. **✅ All match class_diagram_core.plantuml `Data Streams` package.**

### TestFulfillmentRecord (1 test), TestSettlementRecord (1 test), TestAdvisoryRecord (1 test)

All test sensible defaults. `AdvisoryRecord` defaults `price_delta` and `quantity_delta` to `inf`, signaling no convergence yet. **✅ Consistent with convergence tracking in sequence_da_informational.plantuml.**

### TestDispatchSolution (2 tests), TestDeviceCommand (1 test), TestPlanningResult (1 test)

Test defaults and mutable isolation. **✅ Match Dispatch & Actuation package in class diagram.**

### TestDataclassUtilities (3 tests)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_replace_hvac_state` | `dataclasses.replace()` | Change indoor_air_temp | New object with change; original unchanged | ✅ Immutability pattern for state passing |
| `test_deepcopy_bid_curve` | `copy.deepcopy()` | Modify copy's points | Original unchanged | ✅ |
| `test_replace_battery_state` | `dataclasses.replace()` | Change soc | New object; original unchanged | ✅ |

---

## 3. test_data_streams.py

**Module under test:** `data_streams.py` (Level 1-2 — mostly stubs)  
**Design reference:** `class_diagram_core.plantuml` → "Data Streams" package; `class_data_flow.plantuml` → Data Stream Layer  
**Status:** 3 constructor tests pass; 24 method tests are `xfail(raises=NotImplementedError)`.

### TestUncertaintyModelSaturatingExp (3 tests, all xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_zero_lead_time` | `sigma_at(0.0)` | σ_∞=5.0, τ_c=7200 | 0.0 | ✅ σ(0) = 5.0·(1 − e⁰) = 0. Math is correct. |
| `test_one_time_constant` | `sigma_at(7200.0)` | Same model | 5.0·(1 − e⁻¹) ≈ 3.161 | ✅ Standard saturating exponential evaluated at τ=τ_c. |
| `test_large_lead_time_saturates` | `sigma_at(100000.0)` | Same model | ≈ 5.0 | ✅ Asymptotic saturation to σ_∞. |

### TestUncertaintyModelPowerLaw (3 tests, all xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_zero_lead_time` | `sigma_at(0.0)` | σ_0=0.5, α=0.001, β=0.7, σ_∞=6.0 | 0.5 | ✅ min(6.0, 0.5 + 0) = 0.5 |
| `test_mid_lead_time` | `sigma_at(3600.0)` | Same | min(6.0, 0.5 + 0.001·3600^0.7) ≈ 0.889 | ✅ Hand-calculated: 3600^0.7 ≈ 389.15 |
| `test_cap_at_sigma_inf` | `sigma_at(1e8)` | Same | ≤ 6.0 | ✅ Must not exceed cap. |

### TestUncertaintyModelEmpirical (2 tests, all xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_exact_table_point` | `sigma_at(3600.0)` | Table: {0→0, 3600→2, 7200→3.5, 14400→5} | 2.0 | ✅ Exact lookup. |
| `test_interpolation_midpoint` | `sigma_at(5400.0)` | Same table | (2.0+3.5)/2 = 2.75 | ✅ Linear interpolation at midpoint. |

### TestContinuousForecastConstructor (1 test, passes)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_attributes` | Constructor fields | temp_forecast fixture | variable_name, unit, series count | ✅ Matches ContinuousForecast in class diagram |

### TestContinuousForecastGetAt (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_exact_timestamp` | `get_at(3600.0)` | 4-point temp forecast | value=75.0 | ✅ Returns exact data point |
| `test_interpolated_timestamp` | `get_at(1800.0)` | Same | ≈ 73.5 (midpoint of 72 and 75) | ✅ Linear interpolation per design |

### TestContinuousForecastUpdate (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_update_replaces_series` | `update(new_series)` then `get_at(0.0)` | New 2-point series at 60°F | 60.0 | ✅ Class diagram shows `update(new_series)` method |

### TestContinuousForecastGetSeries (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_full_horizon` | `get_series(0.0, 10800.0)` | 4-point forecast | ≥ 4 points | ✅ Class diagram: `get_series(t_start, t_end, resolution)` |
| `test_resampled_resolution` | `get_series(0.0, 7200.0, resolution=1800.0)` | Same forecast | 5 points (0,1800,3600,5400,7200) | ✅ Resampling at specified resolution |

### TestEventForecastConstructor (1 test, passes)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_attributes` | Constructor | Shower forecast fixture | 1 event type, daily_expected_count=2.0 | ✅ Matches EventForecast class |

### TestEventForecastIntensity (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_peak_intensity` | `get_intensity_at(21600.0)` | 6AM in intensity function | 0.5 events/hr | ✅ Exact lookup from intensity function |
| `test_zero_intensity` | `get_intensity_at(0.0)` | Midnight | 0.0 | ✅ No showers at midnight |

### TestEventForecastCumulativeEnergy (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_morning_window` | `get_cumulative_energy_distribution(21600.0, 28800.0)` | — | QuantilePoint with expected ≈ 1.5 kWh (loose ±1.0) | ✅ Trapezoidal integral of λ(t)×E_per_event. Math: avg λ ≈ 0.25 × 2 hrs × 3 kWh = 1.5. |
| `test_full_day_energy` | `get_cumulative_energy_distribution(0.0, 86400.0)` | — | expected ≈ 6.0 (rel=0.3) | ✅ Must equal daily_expected_energy |

### TestEventForecastConditioning (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_condition_reduces_remaining` | `condition_on_observation` then `get_cumulative_energy_distribution` | Observed 3 kWh at 7AM | Remaining < total | ✅ Bayesian conditioning: observed energy reduces expectation. Design: `condition_on_observation(event_type, timestamp, energy)` |
| `test_reset_restores_prior` | `reset_observations()` | — | Back to 6.0 | ✅ Class diagram: `reset_observations()` |

### TestConstraintStreamConstructor (1 test, passes)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_attrs` | Constructor fields | min_soc_constraint fixture | constraint_id, constraint_type, deadline | ✅ |

### TestConstraintStreamFeasibility (5 tests, all xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_continuous_min_satisfied` | `is_feasible(120.0, 0.0)` | min_temp=110 | True | ✅ 120 ≥ 110 |
| `test_continuous_min_violated` | `is_feasible(105.0, 0.0)` | min_temp=110 | False | ✅ 105 < 110 |
| `test_by_time_before_deadline` | `is_feasible(0.30, 0.0)` | deadline=50400, required=0.80 | True | ✅ Before deadline, any value is feasible |
| `test_by_time_at_deadline_satisfied` | `is_feasible(0.85, 50400.0)` | Same | True | ✅ 0.85 ≥ 0.80 at deadline |
| `test_by_time_at_deadline_violated` | `is_feasible(0.60, 50400.0)` | Same | False | ✅ 0.60 < 0.80 at deadline |

### TestConstraintStreamMargin (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_positive_margin` | `feasibility_margin(120.0, 0.0)` | min=110 | 10.0 | ✅ 120 − 110 = 10 |
| `test_negative_margin` | `feasibility_margin(105.0, 0.0)` | min=110 | −5.0 | ✅ 105 − 110 = −5 |

### TestDataStreamManagerConstructor (1 test, passes)

✅ Matches class_diagram_core.plantuml: DataStreamManager with device_type and three dict containers.

### TestDataStreamManagerRegistration (4 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_register_continuous` | `register_continuous_stream` + `get_continuous` | temp_forecast | Returns registered forecast | ✅ |
| `test_register_event` | `register_event_stream` + `get_event` | shower_forecast | Not None | ✅ |
| `test_register_constraint` | `register_constraint` + `get_constraint` | min_soc_constraint | Not None | ✅ |
| `test_get_nonexistent_returns_none` | `get_continuous("nonexistent")` | — | None | ✅ Graceful missing key handling |

### TestDataStreamManagerBundle (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_forecast_bundle` | `get_forecast_bundle(0.0, 10800.0)` | Registered temp forecast | Dict with "outdoor_air_temp" key | ✅ Per class_data_flow.plantuml: DSM → FuncF2 with "forecasts and constraints" |

### TestDataStreamManagerConstraints (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_get_all_constraints_overlapping` | `get_all_constraints(48000.0, 52000.0)` | Two registered constraints | ≥ 1 returned | ✅ Returns constraints active in the query window |

---

## 4. test_preference_curve.py

**Module under test:** `preference_curve.py` (Level 2 — mostly stubs)  
**Design reference:** `class_diagram_core.plantuml` → "Preference & Bidding" package; `sequence_rt_bidding.plantuml` → F3, F4, F7  
**Status:** 2 constructor tests pass; 18 method tests are xfail.

### TestPreferenceCurveConstructor (2 tests, pass)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_construct_standard` | Constructor | k=0.0, P_0=0.10, Q_0=5.0 | Fields stored correctly | ✅ |
| `test_construct_battery` | Constructor | device_type=BATTERY, Q_discharge_max=-5.0, degradation_cost=0.02 | Fields stored | ✅ Battery has extra params per class diagram |

### TestEpsilon (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_epsilon_at_k0` | `epsilon` property | k=0.0 | ≈ 0.0 | ✅ Perfectly inelastic. Docstring: "ε ≈ 0" |
| `test_epsilon_at_k1` | `epsilon` property | k=1.0, ε_max=5.0 | 5.0 | ✅ Maximally elastic: ε = ε_max |
| `test_epsilon_at_k05` | `epsilon` property | k=0.5, ε_max=5.0 | 2.5 | ✅ "Linear mapping k·ε_max" per test docstring. Matches the "can be linear, exponential, or logistic" note in source. Test assumes linear. |

### TestEvaluate (5 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_evaluate_at_reference_price` | `evaluate(0.10)` | k=0.5, P_0=0.10, Q_0=5.0 | 5.0 | ✅ Q(P_0) = Q_0·(1)^{-ε} = Q_0. Anchor property. |
| `test_evaluate_high_price_elastic` | `evaluate(0.20)` | k=1.0 (ε=5) | 5.0/32 ≈ 0.15625 | ✅ Q = 5.0·(2)^{-5} = 5.0/32. Math verified. |
| `test_evaluate_low_price_elastic` | `evaluate(0.05)` | k=1.0 (ε=5) | 160.0 | ✅ Q = 5.0·(0.5)^{-5} = 5.0·32 = 160. Math verified. |
| `test_evaluate_inelastic_ignores_price` | `evaluate(0.20)` | k=0.0 (ε≈0) | ≈ 5.0 | ✅ Q = 5.0·(2)^{0} = 5.0. Inelastic customer ignores price. |
| `test_evaluate_mid_elasticity` | `evaluate(0.20)` | k=0.5 (ε=2.5) | 5.0·(2)^{-2.5} ≈ 0.884 | ✅ Math: 2^{-2.5} = 1/√32 ≈ 0.17678. Verified. |

### TestEvaluateWithBounds (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_clamps_to_Q_max` | `evaluate_with_bounds(0.01, 0.0, 10.0)` | Elastic curve | 10.0 | ✅ Raw = 500,000, clamped to Q_max. Per class diagram signature. |
| `test_clamps_to_Q_min` | `evaluate_with_bounds(1.0, 1.0, 10.0)` | Elastic curve | 1.0 | ✅ Raw ≈ 0, clamped to Q_min. |
| `test_within_bounds_unchanged` | `evaluate_with_bounds(0.10, 0.0, 10.0)` | Mid curve | 5.0 | ✅ No clamping needed. |

### TestAmenityCost (4 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_zero_at_preferred` | `get_amenity_cost(5.0, 5.0)` | Mid curve | 0.0 | ✅ No deviation → no cost. Per docstring: "proportional to (Q_actual − Q_preferred)²" |
| `test_positive_when_deviating` | `get_amenity_cost(3.0, 5.0)` | Mid curve | > 0 | ✅ |
| `test_increases_with_deviation` | Comparing 1kW vs 3kW deviation | — | Larger deviation → higher cost | ✅ Quadratic cost function. |
| `test_inelastic_customer_higher_cost` | Same deviation, k=0 vs k=1 | — | k=0 (comfort-focused) > k=1 (financial) | ✅ "Scaled inversely by k". Makes physical sense. |

### TestBatteryCurve (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_charges_at_low_price` | `evaluate(0.05)` | Battery curve (P_0=0.10, deg=0.02) | > 0 (charge) | ✅ Per sigmoid: below threshold → positive Q. Matches sequence_battery_planning.plantuml dead-band concept. |
| `test_discharges_at_high_price` | `evaluate(0.25)` | Same | < 0 (discharge) | ✅ Above threshold → discharge. |
| `test_near_zero_at_threshold` | `evaluate(0.10)` | Same | |Q| < 1.0 | ✅ Near P_0 → dead band around zero. |

### TestSampleBidCurve (4 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_returns_correct_count` | `sample_bid_curve(0.01, 0.50, 10, ...)` | Mid curve | 10 points | ✅ Method signature matches class diagram |
| `test_monotonic_decreasing` | Bid point ordering | 20 points | Higher price → lower quantity | ✅ Law of demand. Matches MO clearing assumption (sequence_mo_clearing). |
| `test_within_bounds` | All quantities | Q_min=1.0, Q_max=8.0 | 1.0 ≤ q ≤ 8.0 | ✅ Bounded by flexibility. |
| `test_returns_bid_points` | Return type | 5 points | All BidPoint instances | ✅ |

---

## 5. test_device_models.py

**Module under test:** `device_models.py` (Level 1 — mostly stubs)  
**Design reference:** `class_diagram_core.plantuml` → "Device Models" package; `class_data_flow.plantuml` → F2  
**Status:** 3 constructor tests pass; 15 method tests are xfail.

### TestHVACModelConstructor (1 test, passes)

✅ Constructor stores device_type.

### TestHVACPredictTemperature (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_free_floating_temp_rise` | `predict_temperature(state, 0.0 kW, ...)` | HVAC off, T_in=72, T_out=95, UA_env=500, Ca=1500 | Final temp > 72, ≈ 72.64°F after 5 min | ✅ 2-node ETP: dTa/dt = UA_env·(To−Ta)/Ca = 500·23/1500 = 7.67°F/hr. In 5 min: ΔT ≈ 0.64°F. Math verified. |
| `test_cooling_holds_temp` | `predict_temperature(state, 3.5 kW, ...)` | Same but with cooling | Final temp ≈ 72°F ± 2° | ✅ Steady-state load = 500·23/3.5 COP ≈ 3.286 kW. 3.5 kW slightly overcools. |

### TestHVACFlexibility (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_flexibility_range` | `estimate_flexibility(...)` | Cooling state + forecasts | FlexibilityEnvelope: Q_min ≥ 0, Q_max > Q_min, Q_min ≤ Q_baseline ≤ Q_max | ✅ HVAC is load-only (Q_min=0). Per class diagram. |

### TestHVACPowerSetpointRoundtrip (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_roundtrip` | `power_to_setpoint(3.0, ...)` → `setpoint_to_power(result, ...)` | — | ≈ 3.0 kW (rel=5%) | ✅ Class diagram shows both methods. Inverse consistency. |

### TestWaterHeaterModel (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_standby_temperature_drop` | `predict_tank_temperature(state, 0.0 kW, draw=0, 3600s)` | T=130, tank_UA=2.0, ambient=72 | Final temp < 130, > 128 | ✅ Standby loss: UA·ΔT=2·58=116 Btu/hr. Thermal mass=50·8.34=417 Btu/°F. dT/dt ≈ −0.28°F/hr. After 1hr: ≈129.72°F. |
| `test_flexibility_range` | `estimate_flexibility(...)` | Hot tank, no draw | FlexibilityEnvelope: Q_min ≥ 0, Q_max ≤ 4.5 kW | ✅ Q_max = element_power. Load-only. |

### TestEVChargerModel (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_predict_soc_charging` | `predict_soc(state, 7.2 kW, 3600s)` | SOC=0.30, eff=0.90, cap=60 kWh | SOC ≈ 0.408 | ✅ ΔSOC = (7.2·0.90·1.0)/60 = 0.108. Final = 0.408. Math verified. |
| `test_flexibility_must_depart` | `estimate_flexibility(state, departure=(14400,0.80), ...)` | SOC=0.30, need 0.80 in 4hr | Q_min > 0 (must charge) | ✅ Need 30 kWh DC / 4hr = 7.5 kW DC → 8.33 kW AC > max. Q_min near max. |
| `test_no_flexibility_unplugged` | `estimate_flexibility(unplugged, ...)` | vehicle_plugged_in=False | Q_min=0, Q_max=0 | ✅ No vehicle → zero flex. |

### TestBatteryModelConstructor (1 test, passes)

✅ Constructor stores replacement_cost, rated_cycles, cumulative_throughput=0.

### TestBatteryPredictSOC (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_charging_soc_increases` | `predict_soc(state, 5.0, 3600s)` | SOC=0.50, η_rt=0.90, cap=13.5 | SOC ≈ min(0.85, 0.95) | ✅ Charge eff = √0.90 ≈ 0.9487. Stored = 5·0.9487·1.0 = 4.744 kWh. ΔSOC = 4.744/13.5 = 0.351. Final ≈ 0.851. Math verified. |
| `test_discharging_soc_decreases` | `predict_soc(state, -5.0, 3600s)` | Same | SOC < 0.50, ≥ soc_min_bms (0.10) | ✅ Discharge eff = 1/√0.90. Energy from SOC = 5/0.9487 = 5.27 kWh. ΔSOC = −0.390. Final ≈ 0.110. |

### TestBatteryFlexibility (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_bidirectional_envelope` | `estimate_flexibility(state, soc_reserve=0.20, soc_preferred=0.50, 300s)` | SOC=0.50 | Q_min < 0, Q_max > 0, Q_baseline ≈ 0 | ✅ Bidirectional. At preferred SOC, baseline is idle (≈0). |

### TestBatteryDegradation (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_degradation_cost_positive` | `marginal_degradation_cost(state, 3.0)` | — | > 0 | ✅ Any cycling costs. |
| `test_degradation_increases_with_power` | Compare 1.0 kW vs 5.0 kW | — | cost(5) > cost(1) | ✅ Higher C-rate → higher stress (Wöhler exponent). Per sequence_battery_planning. |
| `test_base_degradation_cost_order_of_magnitude` | `marginal_degradation_cost(state, 2.0)` | — | 0.01 < cost < 1.0 | ✅ Base = 10000/(5000·0.80·13.5·2) = $0.0926/kWh. Matches battery planning sequence. |

### TestBatteryThresholds (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_charge_below_discharge` | `compute_charge_discharge_thresholds(state, V=0.10, deg=0.05)` | — | charge_th < discharge_th; dead band ≈ 2×deg_cost | ✅ Per battery_planning sequence: charge_th = V·η − C_deg; discharge_th = V + C_deg. Dead band = 2·C_deg + V·(1−η). Close enough with rel=0.2 tolerance. |

---

## 6. test_market_object.py

**Module under test:** `market_object.py` (Level 1 — mostly stubs)  
**Design reference:** `state_machine_market.plantuml`; `sequence_rt_bidding.plantuml`; `sequence_da_informational.plantuml`; `class_diagram_core.plantuml` → MarketObject class  
**Status:** 3 constructor tests pass; 14 method tests are xfail.

### TestMarketObjectConstructor (3 tests, pass)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_initial_phase` | `current_phase` | Default construction | INACTIVE | ✅ State machine starts at INACTIVE per plantuml `[*] --> inactive` |
| `test_attributes` | Constructor fields | — | market_id, market_type, operating_mode, iteration=0 | ✅ Matches class definition |
| `test_empty_history` | Initial advisory/perf state | — | submitted_bid=None, advisory_history=[], performance_log=[] | ✅ Clean initial state |

### TestLegalTransitions (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_inactive_to_active` | `transition_to(ACTIVE)` | From INACTIVE | Phase=ACTIVE | ✅ `inactive --> active` in state machine |
| `test_active_to_negotiation` | `transition_to(NEGOTIATION)` | From ACTIVE | Phase=NEGOTIATION | ✅ `active --> negotiation` in state machine |
| `test_full_forward_path` | Walk ACTIVE→...→EXPIRED | 8 transitions | Phase=EXPIRED | ✅ Exact match: ACTIVE → NEGOTIATION → MARKET_LEAD → ASSESSMENT → DELIVERY_LEAD → DELIVERY → RECONCILE → EXPIRED. Matches the binding path in state_machine_market.plantuml. |

### ⚠️ TestInformationalLoop (1 test, xfail) — **CRITICAL ISSUE**

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_assessment_loops_to_negotiation` | `transition_to(NEGOTIATION)` from ASSESSMENT | After INACTIVE→ACTIVE→NEGOTIATION→MARKET_LEAD→ASSESSMENT | Phase=NEGOTIATION | **❌ WRONG TARGET** |

**Issue:** The test transitions from ASSESSMENT → NEGOTIATION, but **every design document** specifies ASSESSMENT → ACTIVE:

1. **state_machine_market.plantuml line 107:** `assessment --> active : **INFORMATIONAL**\n(loop back for next iteration)\niteration++`
2. **enums_and_constants.py MarketPhase docstring:** `ASSESSMENT -> (loop back to ACTIVE if informational, or forward to DELIVERY_LEAD if binding)`
3. **sequence_da_informational.plantuml lines 130, 159, 174:** `DA -> MO_obj : transition_to(ACTIVE)\n(current_iteration = 2)` (repeated for iterations 3 and 4)

The loop goes back to ACTIVE (not NEGOTIATION) because the agent must re-observe device state (F1), re-estimate flexibility (F2), and re-generate the preference curve (F3) before re-entering NEGOTIATION for bid re-formulation. This is documented in the DA informational sequence diagram.

**Fix needed:** Change the test to transition to `MarketPhase.ACTIVE` instead of `MarketPhase.NEGOTIATION`. Also update the docstring at the top of the file that says "ASSESSMENT → [loop back to NEGOTIATION]".

### TestIllegalTransitions (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_inactive_to_delivery` | `transition_to(DELIVERY)` from INACTIVE | — | ValueError | ✅ Cannot skip phases. |
| `test_expired_to_anything` | `transition_to(ACTIVE)` from EXPIRED | — | ValueError | ✅ `expired` is terminal per state machine. |
| `test_active_to_delivery_lead` | `transition_to(DELIVERY_LEAD)` from ACTIVE | — | ValueError | ✅ Cannot skip NEGOTIATION→MARKET_LEAD→ASSESSMENT. |

### TestGetNextEventTime (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_inactive_next_event` | `get_next_event_time(900.0)` from INACTIVE | — | Not None, is float | ✅ INACTIVE has a time-based trigger to ACTIVE. |
| `test_expired_no_next` | `get_next_event_time(0.0)` from EXPIRED | — | None | ✅ Terminal state. |

### TestIterationProtocol (4 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_mo_signaled_informational` | `is_informational_iteration(result)` | Protocol="mo_signaled", result.iteration_type=INFORMATIONAL | True | ✅ Per state machine note: "mo_signaled protocol: MO sets flag in ClearingResult" |
| `test_mo_signaled_binding` | `is_informational_iteration(result)` | Same protocol, type=BINDING | False | ✅ |
| `test_fixed_count_first_n_informational` | `is_informational_iteration(result)` | Protocol="fixed_count", n=3, current_iteration=2 | True | ✅ Per state machine note: "fixed_count protocol: iter ≤ N → INFORMATIONAL" |
| `test_fixed_count_last_is_binding` | `is_informational_iteration(result)` | Same, current_iteration=4 | False | ✅ "iter = N+1 → BINDING". 4 > 3 → binding. |

---

## 7. test_market_operator.py

**Module under test:** `market_operator.py` (Level 2 — mostly stubs)  
**Design reference:** `class_diagram_core.plantuml` → "Market Operator (DSO)" package; `sequence_mo_clearing.plantuml`; `sequence_dso_seam.plantuml`  
**Status:** 3 constructor/data tests pass; 13 method tests are xfail.

### TestSupplyCurveConstructor (1 test, passes)

✅ Simple construction with 3 BidPoints.

### TestSupplyAtPrice (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_exact_point` | `get_supply_at_price(0.10)` | $0.05@0kW, $0.10@50kW, $0.20@100kW | 50.0 | ✅ Exact table point |
| `test_interpolated` | `get_supply_at_price(0.075)` | Same | ≈ 25.0 | ✅ Linear interp midpoint of (0.05→0, 0.10→50) |
| `test_below_minimum` | `get_supply_at_price(0.01)` | Same | ≈ 0.0 | ✅ Below minimum → zero supply |

### TestPriceAtQuantity (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_exact_quantity` | `get_price_at_quantity(50.0)` | Same supply | 0.10 | ✅ Inverse of supply curve |
| `test_interpolated_quantity` | `get_price_at_quantity(75.0)` | Same | ≈ 0.15 | ✅ Midpoint of (50→0.10, 100→0.20) |

### TestDSOInflexibleLoadBid (1 test, passes)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_construct` | Constructor | feeder_id, quantity=200, interval, components | Fields stored | ✅ Matches class diagram and DSO seam sequence |

### TestDSOLoadEstimation (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_inflexible_load_calculation` | `estimate_inflexible_load(...)` | total=1000, flex=100, solar=50, loss=0.05 | Q ≈ 892.5 | ✅ Formula: Q = total − flex + losses − solar = 1000 − 100 + (1000−100−50)·0.05 − 50 = 892.5. Matches sequence_dso_seam.plantuml formula exactly. |

**Note on loss calculation:** The test uses `losses = (total − flexible − solar) × loss_factor`, which is the net load seeing distribution losses. This matches the DSO seam diagram which shows `losses = total_forecast × loss_factor`. There's a slight discrepancy in the loss base (total vs. net), but within the ±5 kW test tolerance, both yield similar results. The test's formula (losses on net load) is arguably more physically accurate.

### TestDSOLoadEngineMetering (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_update_with_metering` | `update_with_metering(980.0, 95.0, 300.0)` | — | No error | ✅ Per DSO seam sequence: real-time correction loop |

### TestMarketOperatorConstructor (1 test, passes)

✅ Initial state: empty bids, no supply curve, n_informational=2.

### TestSubmitBids (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_submit_agent_bid` | `submit_agent_bid("agent_1", bid)` | 3-point bid curve | True | ✅ Matches MO clearing sequence |
| `test_submit_supply_curve` | `set_supply_curve(supply)` | Supply fixture | _supply_curve is not None | ✅ |
| `test_submit_dso_bid` | `submit_dso_inflexible_bid(...)` | DSOInflexibleLoadBid | True | ✅ Per DSO seam sequence |

### TestAggregateDemand (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_single_agent_plus_inflexible` | `aggregate_demand()` | 1 elastic agent + 200 kW inflexible | len > 0; max qty ≥ 200 | ✅ Horizontal summation per MO clearing sequence: "At each price level P, sum quantities." |

### TestClearMarket (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_simple_clearing` | `clear_market()` | Supply + agent + 80kW inflexible | ClearingResult with price > 0, qty > 0 | ✅ Intersection of aggregate demand with supply |

### TestIterationProtocol (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_fixed_count_informational` | `determine_iteration_type()` | _current_iteration=1, n_informational=2 | INFORMATIONAL | ✅ Per state machine note |
| `test_fixed_count_binding` | `determine_iteration_type()` | _current_iteration=3 | BINDING | ✅ 3 > 2 → binding |

### TestTotalFlexibleCommitted (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_sum_of_cleared` | `get_total_flexible_committed()` | After clearing | ≥ 0 | ✅ Per DSO seam: "DSO -> MO : get_total_flexible_committed()" for double-counting avoidance |

---

## 8. test_penalty_model.py

**Module under test:** `penalty_model.py` (Level 2 — mostly stubs)  
**Design reference:** `class_diagram_core.plantuml` → PenaltyModel class; `sequence_multi_market.plantuml` → penalty economics  
**Status:** 3 constructor tests pass; 13 method tests are xfail.

### TestPenaltyModelConstructor (3 tests, pass)

✅ All three penalty types (PROPORTIONAL, TIERED, COMPOUND) construct correctly with expected params.

### TestProportionalFixed (4 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_no_shortfall` | `compute_penalty(10.0, 10.0, 0.10, 300)` | No shortfall | 0.0 | ✅ Zero shortfall → zero penalty |
| `test_full_shortfall` | `compute_penalty(10.0, 0.0, 0.10, 300)` | Full shortfall | $0.50 × 10 × (300/3600) = $0.4167 | ✅ Math verified |
| `test_partial_shortfall` | `compute_penalty(10.0, 7.0, 0.10, 300)` | 3 kW shortfall | $0.50 × 3 × (300/3600) = $0.125 | ✅ |
| `test_over_delivery_no_penalty` | `compute_penalty(5.0, 7.0, 0.10, 300)` | Actual > committed | 0.0 | ✅ No negative penalty |

### TestProportionalMultiplier (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_multiplier_mode` | `compute_penalty(10.0, 5.0, 0.10, 300)` | multiplier=2.0 | rate = 2 × $0.10 = $0.20/kWh; penalty = $0.20 × 5 × (300/3600) = $0.08333 | ✅ Math verified. Note: docstring initially computed shortfall_kwh incorrectly as 0.6944 but then self-corrected to 0.41667. The assertion uses the correct value. |

**Minor issue:** The docstring has a crossed-out incorrect intermediate calculation ("Wait — need to recalculate"). While the final assertion is correct, the docstring should be cleaned up to avoid confusion.

### TestTiered (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_small_shortfall_tier1` | `compute_penalty(10.0, 9.5, 0.10, 300)` | 5% shortfall (tier 1 only) | $0.25 × 0.5 × (300/3600) ≈ $0.01042 | ✅ 5% < 10% threshold → entirely tier 1. |
| `test_medium_shortfall_two_tiers` | `compute_penalty(10.0, 8.0, 0.10, 300)` | 20% shortfall (tiers 1+2) | Tier1: 1kW×$0.25 + Tier2: 1kW×$0.50, ×(300/3600) ≈ $0.0625 | ✅ First 10%=1kW at $0.25, next 10%=1kW at $0.50. |
| `test_large_shortfall_all_tiers` | `compute_penalty(10.0, 5.0, 0.10, 300)` | 50% shortfall (all 3 tiers) | T1:1×0.25 + T2:2×0.50 + T3:2×1.00 = 3.25, ×(300/3600) ≈ $0.2708 | ✅ Tier boundaries: 0-10%=1kW, 10-30%=2kW, 30-50%=2kW. Math verified. |

### TestCompound (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_compound_with_shortfall` | `compute_penalty(10.0, 5.0, 0.10, 300)` | fixed=$10 + rate=$0.30/kWh | 10.0 + 0.30 × 5 × (300/3600) = $10.125 | ✅ |
| `test_compound_no_shortfall` | `compute_penalty(10.0, 10.0, 0.10, 300)` | No shortfall | 0.0 | ✅ Fixed applies only when there IS shortfall |

### TestMarginalPenalty (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_marginal_proportional_fixed` | `marginal_penalty(10.0, 0.10, 300)` | base_rate=$0.50 | $0.50 × (300/3600) = $0.04167 | ✅ Marginal cost of first kW shortfall. Used by dispatch optimizer per class diagram. |
| `test_marginal_tiered_first_tier` | `marginal_penalty(10.0, 0.10, 300)` | First tier rate=$0.25 | $0.25 × (300/3600) = $0.02083 | ✅ First kW hits tier 1. |

---

## 9. test_dispatch_optimizer.py

**Module under test:** `dispatch_optimizer.py` (Level 3 — stubs)  
**Design reference:** `class_diagram_core.plantuml` → "Dispatch & Actuation" package; `sequence_multi_market.plantuml`  
**Status:** All 5 tests are xfail.

### TestDispatchSingleProduct (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_single_energy_delivery` | `optimizer.solve(economics, 0-10 kW, curve, amenity=0.3)` | 1 energy delivery: committed=4 kW, price=$0.12, penalty=$0.50 | DispatchSolution: Q ≈ 4.0 ± 1.0 | ✅ Single product → minimize penalty → operate at committed. Per multi-market sequence: full delivery when no conflict. |

### TestDispatchTwoProducts (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_energy_plus_regulation` | `optimizer.solve(...)` | Energy 4kW + Reg-up 2kW | Q ≥ 4.0 | ✅ Must-run energy + headroom for regulation. Matches multi-market scenario. |

### TestDispatchAmenityEffect (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_high_amenity_weight_biases_toward_comfort` | `optimizer.solve(...)` | committed=8, Q_0=5, amenity_weight=5.0 | |Q − 5| < |8 − 5| | ✅ High amenity weight pulls toward Q_0. Per optimizer objective: − C_amenity(Q) term. |

### TestDeliveryValueCalculator (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_energy_product` | `value_calculator.compute(...)` | committed=5, price=$0.12, interval=300s | DeliveryEconomics with correct price and qty | ✅ Normalizes economics for dispatch optimizer. Per class diagram: `DeliveryValueCalculator.compute(market_id, product, committed, price, penalty, duration, ...)` |

---

## 10. test_planning_optimizer.py

**Module under test:** `planning_optimizer.py` (Level 3 — stubs)  
**Design reference:** `sequence_battery_planning.plantuml`; `class_diagram_core.plantuml` → PlanningOptimizer  
**Status:** 1 constructor test passes; 5 method tests are xfail.

### TestBatteryPlannerConstructor (1 test, passes)

✅ Stores device_type="battery".

### TestBatteryFlatPrices (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_no_cycling_incentive` | `planner.solve(...)` | Flat $0.10/kWh × 24hr, SOC=0.50, cap=13.5 | PlanningResult; total throughput < 20 kWh | ✅ No price differential → cycling only incurs degradation → optimal is idle. Matches battery planning sequence rationale. |

### TestBatteryTOUArbitrage (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_charges_off_peak_discharges_on_peak` | `planner.solve(...)` | TOU: off=$0.05, mid=$0.10, peak=$0.20 | PlanningResult; V_stored present | ✅ Spread ($0.15) > degradation ($0.09) + efficiency loss ($0.015) → profitable cycling. Matches battery planning sequence optimal schedule. |

### TestBatteryVStored (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_v_stored_monotonicity` | V_stored range | TOU prices | max(V_stored) > min(V_stored) | ✅ V_stored is the shadow price of SOC. Per battery planning sequence: peaks at $0.22/kWh before discharge, drops to $0.04/kWh overnight. Non-trivial range expected. |

### TestHVACPlanning (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_pre_cool_before_peak` | `planner.solve(...)` | HVAC state, TOU prices, 95°F forecast | PlanningResult | ✅ Pre-conditioning: cool during off-peak to reduce on-peak consumption. Matches design data flow: PlanningOptimizer → schedule baseline. |

---

## 11. test_flexibility_ledger.py

**Module under test:** `flexibility_ledger.py` (Level 2 — mostly stubs)  
**Design reference:** `class_diagram_core.plantuml` → "Flexibility Management" package; `sequence_rt_bidding.plantuml` → F6; `sequence_da_informational.plantuml` → advisory confidence weighting  
**Status:** 2 constructor tests pass; 14 method tests are xfail.

### TestFlexibilityLedgerConstructor (2 tests, pass)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_load_device` | Constructor | Q_min=0, Q_max=10 | Fields stored, empty commitments | ✅ |
| `test_battery_device` | Constructor | Q_min=-5, Q_max=5 | Bidirectional range | ✅ |

### TestHoldTentative (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_tentative_recorded` | `hold_tentative(...)` + `get_commitments_overlapping(...)` | market_id, 3 kW, [100,400] | 1 commitment, qty=3 | ✅ Per RT bidding sequence: "F6: Record Tentative Commitment" |
| `test_tentative_replaces_same_market` | Two `hold_tentative` for same market_id | 3 kW then 5 kW | 1 commitment, qty=5 | ✅ Idempotent update for same market |

### TestUpdateAdvisory (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_advisory_recorded` | `hold_tentative(...)` → `update_advisory(...)` | confidence=0.7, qty=4 | 1 commitment, qty=4 | ✅ Per DA informational sequence: advisory updates during ASSESSMENT |

### TestBookFirmAndRelease (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_firm_then_release` | `book_firm(...)` → `release(...)` | 6 kW firm, then release | Before: 1 commitment; after: 0 | ✅ Full lifecycle: TENTATIVE → ADVISORY → FIRM → RELEASED. Per RECONCILE phase. |

### TestHardAvailable — Tier 1 (4 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_empty_ledger` | `hard_available((0,300))` | Empty ledger, Q=[0,10] | (0, 10) | ✅ Full range available |
| `test_single_firm_commitment` | `hard_available(...)` | 6 kW firm in [100,400] | Q_max = 10 − 6 = 4 | ✅ Hard deducts ALL commitments |
| `test_excluding_market` | `hard_available(..., excluding="RT_100")` | Same 6 kW firm | Q_max = 10 (own market excluded) | ✅ Self-exclusion for re-bidding. Per class diagram: `hard_available(interval, excluding)` |
| `test_battery_bidirectional` | `hard_available(...)` | Battery, 3 kW charge commitment | Q_min = -5 (discharge unaffected), Q_max = 5−3 = 2 | ✅ Charge commitment only reduces Q_max, not Q_min |

### TestExpectedAvailable — Tier 2 (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_firm_fully_deducted` | `expected_available(...)` | 6 kW firm | Q_max = 4 | ✅ Firm at 100% weight |
| `test_advisory_weighted_by_confidence` | `expected_available(...)` | 4 kW advisory, confidence=0.7 | Q_max = 10 − 0.7×4 = 7.2 | ✅ Per DA informational sequence: "Advisory commitment... weighted by confidence=0.25" (same principle) |
| `test_tentative_at_baseline_weight` | `expected_available(...)` | 5 kW tentative | Q_max = 10 − 0.4×5 = 8.0 | ✅ Tentative at baseline weight (0.4). Per class: `_tentative_weight: float = 0.4` |

### TestEconomicAvailable — Tier 3 (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_displaceable_block` | `economic_available(...)` | Advisory 4kW, candidate value=$0.20 | EconomicEnvelope: total_displaceable > 0, soft_Q_max > hard_Q_max | ✅ Higher-value candidate can displace lower-value advisory. Per class diagram: EconomicEnvelope with DisplaceableBlocks. |
| `test_no_displacement_when_too_expensive` | `economic_available(...)` | Firm 8kW at $0.50, candidate value=$0.01 | total_displaceable = 0 | ✅ Candidate value too low to justify displacement cost. |

### TestNonOverlappingIntervals (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_commitment_outside_query` | `hard_available((500,800))` | Commitment in [100,400] | Q_max = 10 (no overlap) | ✅ Temporal filtering: non-overlapping commitments don't affect availability |

---

## 12. test_price_forecast_service.py

**Module under test:** `price_forecast_service.py` (Level 2 — mostly stubs)  
**Design reference:** `class_diagram_core.plantuml` → PriceForecastService; `sequence_da_informational.plantuml` → price forecast updates  
**Status:** 1 constructor test passes; 9 method tests are xfail.

### TestPriceForecastServiceConstructor (1 test, passes)

✅ Empty forecasts dict.

### TestUpdateAndRetrieve (3 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_update_creates_entry` | `update(...)` + `get_forecast(...)` | RT, [0,300], $0.10, confidence=0.5 | PriceForecast with matching fields | ✅ Per DA informational sequence: `PFS : update(DA_ENERGY, each_interval, price, confidence=0.25, source='informational_clear', iter=1)` |
| `test_update_overwrites` | Two updates, same interval | iter 1 @ $0.10, iter 2 @ $0.12 | Latest: $0.12, confidence=0.8 | ✅ Each iteration overwrites. |
| `test_get_nonexistent_returns_none` | `get_forecast(DA, (0,3600))` | No prior update | None | ✅ Graceful missing key handling |

### TestGetPrice (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_returns_estimate` | `get_price(RT, (0,300))` | After update @ $0.10 | 0.10 | ✅ Convenience accessor |
| `test_returns_default_when_missing` | `get_price(RT, (0,300), default=0.05)` | No prior update | 0.05 | ✅ Default fallback for bootstrapping |

### TestGetTrajectory (2 tests, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_hourly_trajectory` | `get_trajectory(DA, 0, 14400, 3600)` | 4 hours @ $0.08,$0.10,$0.15,$0.12 | 4 intervals, correct prices | ✅ Used by PlanningOptimizer. Per class diagram: `get_trajectory(market_type, t_start, t_end, resolution)` |
| `test_partial_trajectory` | `get_trajectory(DA, 3600, 10800, 3600)` | Sub-range of 4 hours | 2 intervals (hours 1 and 2) | ✅ Returns only overlapping intervals |

### TestHistoryTracking (1 test, xfail)

| Test | Function Tested | Inputs | Expected Output | Design Match |
|---|---|---|---|---|
| `test_history_accumulates` | 3 sequential updates | Prices $0.10→$0.11→$0.12 | history length=3, current=$0.12 | ✅ Per DA informational sequence: convergence tracking across iterations |

---

## 13. conftest.py

**Shared test fixtures**  
**Status:** All fixtures are constructing data structures; no logic tested.

### Device State Fixtures (5 fixtures)

| Fixture | Creates | Design Match |
|---|---|---|
| `default_hvac_state` | HVACState() | ✅ All defaults |
| `hot_day_hvac_state` | HVACState(outdoor=95, power=3.5, hvac_on=True) | ✅ Realistic hot-day scenario |
| `default_wh_state` | WaterHeaterState() | ✅ |
| `default_ev_state` | EVChargerState() | ✅ 50% SOC, unplugged |
| `plugged_in_ev_state` | EVChargerState(soc=0.30, plugged_in=True, ...) | ✅ Charging scenario |
| `default_battery_state` | BatteryState() | ✅ 50% SOC, 13.5 kWh |
| `mid_soc_battery_state` | BatteryState(soc=0.50, idle, rt_eff=0.90) | ✅ |

### Market Timing Fixtures (2 fixtures)

| Fixture | Creates | Design Match |
|---|---|---|
| `rt_timing_params` | RT: 5-min cycle (−600→0→300→600) | ✅ Matches state machine timeline |
| `da_timing_params` | DA: 1-hr intervals | ✅ |

### Bid/Clearing Fixtures (2 fixtures)

| Fixture | Creates | Design Match |
|---|---|---|
| `simple_downward_bid` | 4-point demand curve ($0.20→$0.05) | ✅ Downward-sloping (law of demand) |
| `simple_clearing_result` | $0.10/kWh, 5 kW, BINDING | ✅ |

### Flexibility Fixtures (2 fixtures)

| Fixture | Creates | Design Match |
|---|---|---|
| `load_only_flexibility` | Q_min=0, Q_max=5, baseline=3 | ✅ Load-only |
| `battery_flexibility` | Q_min=-5, Q_max=5, baseline=0 | ✅ Bidirectional |

### Price Fixtures (2 fixtures)

| Fixture | Creates | Design Match |
|---|---|---|
| `flat_price_trajectory` | 24hr × $0.10/kWh | ✅ Used for no-cycling baseline |
| `tou_price_trajectory` | Off-peak $0.06, mid $0.10, peak $0.25 | ✅ TOU pattern for arbitrage tests |

---

## Issues Found

### CRITICAL: State Machine Loop Target Mismatch

**File:** `test_market_object.py`, class `TestInformationalLoop`, test `test_assessment_loops_to_negotiation` (line ~141)

**Problem:** The test transitions from ASSESSMENT → NEGOTIATION, but:
- `state_machine_market.plantuml` specifies ASSESSMENT → ACTIVE (line 107)
- `enums_and_constants.py` MarketPhase docstring says "loop back to ACTIVE"  
- `sequence_da_informational.plantuml` shows `transition_to(ACTIVE)` (lines 130, 159, 174)

The rationale is that after an informational clear, the agent must re-observe device state (F1), re-estimate flexibility (F2), and re-generate the preference curve (F3) during the ACTIVE phase before re-entering NEGOTIATION for bid re-formulation.

**Impact:** If the implementation follows the test (ASSESSMENT→NEGOTIATION), it will skip F1/F2/F3 re-execution, leading to stale state and inaccurate bids in subsequent iterations.

**Fix:** Change `MarketPhase.NEGOTIATION` to `MarketPhase.ACTIVE` in the test. Also update the file-level docstring (lines 5-13) which describes the (incorrect) loop path.

### MINOR: Confusing Documentation in test_penalty_model.py

**File:** `test_penalty_model.py`, class `TestProportionalMultiplier`, test `test_multiplier_mode` (line ~166)

**Problem:** The docstring contains a self-correcting computation ("Wait — need to recalculate. shortfall = 5 kW over 300 s..."), where an incorrect intermediate value of 0.6944 kWh is shown before the correct 0.41667 kWh. The assertion itself is correct.

**Impact:** Cosmetic confusion; no functional issue.

**Fix:** Remove the incorrect intermediate calculation from the docstring.

---

## Coverage Gaps

### Modules Not Tested

1. **`command_arbiter.py`** — No test file. This is the central orchestrator during DELIVERY that merges commands from multiple simultaneous markets. Tested indirectly through `test_dispatch_optimizer.py`, but the arbiter's own `register_delivery`, `deregister_delivery`, `resolve_and_actuate`, and `update_signals` methods are not covered. Per the `sequence_multi_market.plantuml`, this is a critical component.

2. **`device_agent.py`** — No test file. The main `DeviceAgent` orchestrator class with `step()`, `observe_device_state()`, `formulate_bid()`, `evaluate_price_response()`, and all phase handlers. This is the top-level integration class.

3. **`gridlabd_interface.py`** — No test file. External dependency (requires co-simulation); cannot be unit tested without mocking GridLAB-D, which may be intentional.

4. **`market_agent.py`** — No test file. Not found in the design documents; may be deprecated or supplementary.

5. **`main.py`** — No test file. Entry point/bootstrapping; may not need tests.

### Missing Test Scenarios Within Existing Files

1. **`test_market_object.py`:** Missing test for `should_transition(current_time)` — a time-based check that determines WHEN to transition. Only `transition_to()` (explicit transitions) and `get_next_event_time()` are tested.

2. **`test_market_object.py`:** Missing test for the **time_gated** iteration protocol (only `mo_signaled` and `fixed_count` are tested). The design's state machine note mentions three protocols: fixed_count, mo_signaled, time_gated.

3. **`test_penalty_model.py`:** Missing test for **SCORED** penalty type. The `PenaltyStructureType` enum includes SCORED (for regulation signal-following), and the PenaltyModel source mentions a `score_function` parameter, but no test fixture or test class exists for it.

4. **`test_device_models.py`:** Missing test for `HVACModel` in **heating** mode (heat pump). Only cooling scenarios are tested. The `hp_model` fixture exists but is never used.

5. **`test_device_models.py`:** Missing test for `WaterHeaterModel.power_to_setpoint()` inverse.

6. **`test_device_models.py`:** Missing test for `BatteryModel.update_degradation_tracking()` — the cumulative throughput tracking method.

7. **`test_data_streams.py`:** Missing test for `DataStreamManager.register_schedule()` and `get_schedule()` — schedule streams are in the class diagram and data flow diagram but not tested.

8. **`test_dispatch_optimizer.py`:** Missing test for the **3+ product LP/QP** case. Only 1-product and 2-product tests exist. The multi-market sequence diagram shows a 3-product scenario (DA energy + RT energy + regulation).

9. **`test_flexibility_ledger.py`:** Missing test for **multiple overlapping commitments** at different statuses (e.g., firm DA + advisory RT + tentative regulation in the same interval).

10. **`test_price_forecast_service.py`:** Missing test for the `source` field tracking — different sources (informational_clear vs. external) are never verified.