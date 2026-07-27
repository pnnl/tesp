## How Q-bid Calibration Works

*A summary of the (reverse-engineered) Q-bid forecast-correction calibration
workflow, updated after debugging the temperature-unit, data-window, caching,
and validation issues described at the end of this document.*

### The Model Being Fitted

The calibration fits this correction model from
`tesp_support.dsot.forecasting.Forecasting.correcting_Q_forecast_10_AM`:

```
new_Q = Q_10_AM * Q_gain
      + t_65    * t_65_gain
      + t_65²   * t_65_2_gain
      + DC_change_Q_DA
```

where `t_65 = |temperature_F - 65|`, coefficients are fit **separately for
weekdays and weekends**, and each coefficient is stored as a two-element list
`[weekday, weekend]` to match the runtime indexing.

#### What this calibration corrects

`Q_10_AM` — the uncorrected day-ahead quantity — is produced from a **fixed,
normalized daily load shape scaled by peak load** (`base_run_load` in
`forecasting.py`). **It contains no temperature dependence whatsoever.**

That has direct consequences for what "good" coefficients look like:

- `Q_gain` and `DC_change_Q_DA` absorb the **level/scale** difference between
  the flat base shape and realized load.
- `t_65` and `t_65_2` inject the **entire temperature sensitivity** that the
  base forecast lacks.

Therefore, **weather-sensitive or high-load DSOs are expected to have large `t_65` and `DC_change_Q_DA` values** as part of this calibration. The legacy
hand-calibrated values were smaller largely because they appear to have been
produced on a different (likely per-unit / normalized) scale — do **not** treat
those old magnitudes as physical bounds.

---

### Prerequisites

Calibration must be run from a **base case with the correction disabled**, so
that `DA_Q_forecast.csv` is the genuinely *uncorrected* `Q_10_AM`. For the Flat
case this is guaranteed by case preparation, which collapses
`Q_bid_forecast_correction` to `{'default': {'correct': False}}` when the `fl`
correction flag is off. If you calibrate from a run that already applied a
correction, you are fitting a correction-on-a-correction and the coefficients
would be invalid.

Required annual inputs (assembled automatically from the 12 monthly case
folders — see below):

- `DA_Q_forecast.csv` — uncorrected DA quantity per DSO (baseline / `Q_10_AM`)
- `DA_Q_error.csv` — used to reconstruct realized quantity
- `weather.dat` per substation for entire year — hourly temperature, **already in °F**

---

### run_annual_postprocessing.py — the calibration block

Calibration is driven by `base_params_process()` (or any run with
`integrate_q_bid_calibration = True`). The block does the following:

#### 1. Assemble annual inputs from 12 monthly runs
The monthly post-processing produces per-month `DA_Q_forecast.csv` /
`DA_Q_error.csv`. The annual script concatenates all 12 months into a single
full-year series (`_ensure_annual_da_q_inputs` / `_build_annual_da_q_file`),
de-duplicating and sorting on the datetime column.

!! warning
    
    The post-processing script skips rebuilding if the annual file already exists. A stale annual file left over from a previous (broken) run will be silently reused. If you change inputs or logic, delete the stale `DA_Q_forecast.csv`, `DA_Q_error.csv`, `actual_da_q.csv`, and the `annual_weather/` folder in the case directory before re-running. Better yet, delete the entire post-processing folder and then re-run.

#### 2. Assemble an annual weather series

Weather is discovered per substation and stitched into a **full-year** per-DSO

### calibrate_config.py — Step by Step

This script does **no fitting** — it merges calibration results into a new, calibrated config file updated from the case config used for the base run.

#### 1. Locate the block to replace
```python
key_match = re.search(r'"Q_bid_forecast_correction"\s*:\s*', config_text)
open_brace = config_text.find("{", key_match.end())
close_brace = _find_matching_brace(config_text, open_brace)
```
It finds the exact character range of the existing `Q_bid_forecast_correction` JSON object using a brace-depth counter (handles nested braces correctly).

#### 2. Parse the existing block
Because the source file is JSON5 (allows comments, trailing commas), two cleanup passes run before `json.loads()`:
```python
text = re.sub(r"/\*.*?\*/", "", text)       # strip block comments
# + character-by-character // comment stripping
text = re.sub(r",\s*([}\]])", r"\1", text)  # strip trailing commas
```

#### 3. Merge — only DSO keys are overwritten
```python
def merge_qbid(old_block, new_block):
    merged = dict(old_block)          # start from existing config
    for key, value in new_block.items():
        if key.startswith("DSO_"):    # only replace DSO_N entries
            merged[key] = value       # "default" block is preserved
    return merged
```
The `"default": {"correct": False}` entry and any non-DSO keys survive unchanged.

#### 4. Splice back into the original text
```python
updated_config_text = (
    config_text[:start]          # everything before the old block
    + merged_block_text          # new JSON-serialized block
    + config_text[end + 1:]      # everything after the old block
)
```
This preserves all JSON5 comments and structure **outside** the `Q_bid_forecast_correction` block.

#### 5. Diff report
For each DSO and each of the four parameters, it computes:
```python
"old":   [weekday_old,   weekend_old]
"new":   [weekday_new,   weekend_new]
"delta": [new[0]-old[0], new[1]-old[1]]
```
This lets you audit exactly what the calibration changed before using the new config in a simulation.

---

### Summary of Data Flow

```
DA_Q_forecast.csv  ──┐
actual_da_q.csv    ──┼──► lstsq per DSO ──► calibrated JSON ──┐
weather.dat        ──┘    (weekday/weekend)                    │
                                                               ▼
rates_config.json5 ───────────────────────────────────► rates_config_calibrated.json5
                                                        + diff_report.json
```



#### Files produced by calibration that feed back into simulations

1. `rates_config_calibrated.json5` ✅
    
    * Example: Replace `rates_config.json5` in `metadata_path` (`glm_dsot/data/`). This carries the updated `Q_bid_forecast_correction` block with the new per-DSO weekday/weekend coefficients.

2. `DSO_quadratic_curves.json` ✅

    * This maps quantity bids (MW) to day-ahead prices per DSO. It is written to `case_path` but needs to be placed where the **DSO bidding model** can find it at runtime. I.e., rename this file to `8_hi_quadratic_curves.json` or similar and place in `../dsot/data`. If changing the name to something else, update the call in the config or prepare case.

3. `actual_da_q.csv` ⚠️ intermediate only

    * This is an intermediate artifact used only during calibration. It does **not** need to be copied anywhere for the next simulation.

---

### What you should verify before the next simulation run

| Question | Where to check |
|---|---|
| Does the DSO agent read `Q_bid_forecast_correction` from `rates_config.json5` at startup? | `tesp_support.dsot.forecasting` → `correcting_Q_forecast_10_AM` |
| Does `dso_quadratic_curves` read from `metadata_path`, `case_path`, or a per-DSO subfolder? | `tesp_support.dsot.dso_quadratic_curves` → file open calls |
| Does `run_case_postprocessing.py` reference `rates_config.json5` by name or by a config key? | It reads `generate_case_config.json` → `data_path`; the rates config path flows from there |

### Replace or Rename Post-Processing Call 

The run_annual_postprocessing.py config section hardcodes:
```python
case = "rates_config.json5"
config_path = os.path.join(metadata_path, case)
```
So if you rename the calibrated file rather than replacing the original, you'll also need to update this line (and the equivalent reference in `run_case_postprocessing.py`) before the next monthly run picks up the new coefficients.

### Summary checklist

- [ ] Replace `glm_dsot/data/rates_config.json5` with `rates_config_calibrated.json5` (or update the filename reference in both postprocessing scripts)
- [ ] Confirm `DSO_quadratic_curves.json` destination matches where the DSO agent reads it at runtime
- [ ] Verify `generate_case_config.json` for the next simulation year still points to the correct `data_path`
- [ ] Keep `rates_config_calibration_diff_report.json` as an audit record of what changed