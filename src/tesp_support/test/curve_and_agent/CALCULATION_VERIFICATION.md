# Hand Calculation Verification Report

**Date:** March 5, 2026
**Method:** Every docstring with a numerical hand calculation was independently
recomputed using Python (`math` library) as a calculator.
**Scope:** All 13 test files in `src/tesp_support/tests/curve_and_agent/`

---

## Summary

| File | Calculations Checked | Errors Found |
|---|---|---|
| test_enums_and_constants.py | 0 (enum counts only) | 0 |
| test_data_types.py | 0 (defaults/construction only) | 0 |
| test_data_streams.py | 10 | **1** |
| test_preference_curve.py | 8 | 0 |
| test_device_models.py | 12 | 0 |
| test_market_object.py | 0 (logic tests only) | 0 |
| test_market_operator.py | 4 | 0 |
| test_penalty_model.py | 10 | 0 |
| test_dispatch_optimizer.py | 1 | 0 |
| test_planning_optimizer.py | 1 (approximate) | 0 |
| test_flexibility_ledger.py | 4 | 0 |
| test_price_forecast_service.py | 0 (CRUD tests only) | 0 |
| conftest.py | 0 (fixture construction) | 0 |
| **TOTAL** | **50** | **1** |

---

## Error Found

### test_data_streams.py — `TestUncertaintyModelPowerLaw.test_mid_lead_time`

**Location:** [test_data_streams.py](test_data_streams.py), lines 96–99

**Docstring claims:**
```
At τ=3600: σ = min(6.0, 0.5 + 0.001·3600^0.7).
3600^0.7 ≈ 389.15 → σ ≈ 0.5 + 0.389 = 0.889.
```

**Correct values (computed with Python):**
```python
>>> 3600.0 ** 0.7
308.6134856267128
>>> 0.5 + 0.001 * 308.613
0.8086134856267128
```

| Quantity | Docstring | Correct | Error |
|---|---|---|---|
| 3600^0.7 | 389.15 | 308.61 | +26.1% |
| σ(3600) | 0.889 | 0.809 | +9.9% |

**Test code impact: NONE.** The assertion computes the expected value correctly
in Python rather than using the docstring constant:
```python
raw = 0.5 + 0.001 * (3600.0**0.7)   # correctly evaluates to ~0.809
expected = min(6.0, raw)
assert power_law_model.sigma_at(3600.0) == pytest.approx(expected, rel=0.02)
```
The test would pass correctly once `sigma_at()` is implemented. Only the
docstring's explanatory intermediate values were wrong.

**Root cause:** Likely a mental arithmetic or calculator error when writing the
docstring. The value 389.15 does not correspond to any obvious unit conversion
or exponent variation of 3600.

**Resolution:** Docstring corrected on March 5, 2026. Changed `3600^0.7 ≈ 389.15
→ σ ≈ 0.5 + 0.389 = 0.889` to `3600^0.7 ≈ 308.61 → σ ≈ 0.5 + 0.309 = 0.809`.

---

## All Verified Calculations (No Errors)

### test_penalty_model.py

| Test | Docstring Value | Recomputed | Match |
|---|---|---|---|
| `test_full_shortfall` | energy=0.8333 kWh, penalty=$0.4167 | 10×(300/3600)=0.8333, 0.50×0.8333=$0.4167 | ✅ |
| `test_partial_shortfall` | energy=0.25 kWh, penalty=$0.125 | 3×(300/3600)=0.25, 0.50×0.25=$0.125 | ✅ |
| `test_multiplier_mode` | energy=0.41667 kWh, penalty=$0.08333 | 5×(300/3600)=0.41667, 0.20×0.41667=$0.08333 | ✅ |
| `test_small_shortfall_tier1` | energy=0.04167, penalty=$0.01042 | 0.5×(300/3600)=0.04167, 0.25×0.04167=$0.01042 | ✅ |
| `test_medium_shortfall_two_tiers` | penalty=$0.0625 | (1×0.25+1×0.50)×(300/3600)=$0.0625 | ✅ |
| `test_large_shortfall_all_tiers` | penalty=$0.2708 | (1×0.25+2×0.50+2×1.00)×(300/3600)=$0.2708 | ✅ |
| `test_compound_with_shortfall` | total=$10.125 | 10.0+0.30×0.4167=$10.125 | ✅ |
| `test_marginal_proportional_fixed` | $0.04167 | 0.50×(300/3600)=$0.04167 | ✅ |
| `test_marginal_tiered_first_tier` | $0.02083 | 0.25×(300/3600)=$0.02083 | ✅ |

### test_preference_curve.py

| Test | Docstring Value | Recomputed | Match |
|---|---|---|---|
| `test_evaluate_at_reference` | Q=5.0 | 5.0×(1.0)^{-2.5}=5.0 | ✅ |
| `test_evaluate_high_price_elastic` | 5.0/32=0.15625 | 5.0×2^{-5}=0.15625 | ✅ |
| `test_evaluate_low_price_elastic` | 160.0 | 5.0×(0.5)^{-5}=160.0 | ✅ |
| `test_evaluate_inelastic` | ≈5.0 | 5.0×2^0=5.0 | ✅ |
| `test_evaluate_mid_elasticity` | ≈0.8839 | 5.0×2^{-2.5}=0.8839 | ✅ |
| `test_clamps_to_Q_max` | raw=500000 | 5.0×10^5=500000 | ✅ |
| `test_clamps_to_Q_min` | raw=5e-5 | 5.0×10^{-5}=5e-5 | ✅ |

### test_device_models.py

| Test | Docstring Value | Recomputed | Match |
|---|---|---|---|
| `test_free_floating_temp_rise` | dT/dt=7.667°F/hr, ΔT(5min)=0.639°F | 11500/1500=7.667, ×(5/60)=0.639 | ✅ |
| `test_cooling_holds_temp` | load≈3286 W | 500×23/3.5=3285.7 | ✅ |
| `test_standby_temperature_drop` | Q_loss=116, ΔT=-0.278, T=129.72 | 2×58=116, 116/417=0.278, 130-0.278=129.72 | ✅ |
| `test_predict_soc_charging` | ΔSOC=0.108, final=0.408 | (7.2×0.90)/60=0.108, 0.30+0.108=0.408 | ✅ |
| `test_flexibility_must_depart` | AC=8.33 kW | 30/(4×0.90)=8.33 | ✅ |
| `test_charging_soc_increases` | stored=4.744, ΔSOC=0.3514, final=0.8514 | 5×√0.90×1/13.5 recomputed | ✅ |
| `test_discharging_soc_decreases` | energy=5.270, ΔSOC=-0.3904, final=0.1096 | 5/√0.90/13.5 recomputed | ✅ |
| `test_base_degradation_cost` | $0.0926/kWh | 10000/(5000×0.80×13.5×2)=$0.0926 | ✅ |

### test_data_streams.py (excluding error above)

| Test | Docstring Value | Recomputed | Match |
|---|---|---|---|
| `test_zero_lead_time` (sat exp) | σ=0.0 | 5×(1-e^0)=0.0 | ✅ |
| `test_one_time_constant` | σ≈3.161 | 5×(1-e^{-1})=3.1606 | ✅ |
| `test_large_lead_time_saturates` | σ≈5.0 | 5×(1-e^{-13.9})≈5.0 | ✅ |
| `test_zero_lead_time` (power law) | σ=0.5 | min(6, 0.5+0)=0.5 | ✅ |
| `test_interpolation_midpoint` | σ=2.75 | 2.0+1.5×0.5=2.75 | ✅ |
| `test_interpolated_timestamp` | 73.5 | (72+75)/2=73.5 | ✅ |
| `test_morning_window` | ≈1.5 kWh | 0.25×2×3.0=1.5 | ✅ |

### test_market_operator.py

| Test | Docstring Value | Recomputed | Match |
|---|---|---|---|
| `test_inflexible_load_calculation` | Q=892.5 | 1000-100+42.5-50=892.5 | ✅ |
| `test_interpolated` (supply) | 25.0 kW | linear interp at $0.075 | ✅ |
| `test_interpolated_quantity` | $0.15 | linear interp at 75 kW | ✅ |

### test_flexibility_ledger.py

| Test | Docstring Value | Recomputed | Match |
|---|---|---|---|
| `test_advisory_weighted_by_confidence` | Q_max=7.2 | 10-0.7×4=7.2 | ✅ |
| `test_tentative_at_baseline_weight` | Q_max=8.0 | 10-0.4×5=8.0 | ✅ |
| `test_battery_bidirectional` (hard) | Q_min=-5, Q_max=2 | -5 unchanged, 5-3=2 | ✅ |

### test_dispatch_optimizer.py

| Test | Docstring Value | Recomputed | Match |
|---|---|---|---|
| `test_energy_product` (value calc) | revenue=$0.05 | 0.12×5×(300/3600)=$0.05 | ✅ |
