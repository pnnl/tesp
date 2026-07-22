## How Q-bid Calibration Works

*An AI-agent summary of an AI-agent recreated calibration workflow*

### The Model Being Fitted

Both scripts implement calibration for this correction model (from `tesp_support.dsot.forecasting`):

```
new_Q = Q_10_AM * Q_gain
      + t_65 * t_65_gain
      + t_65² * t_65_2_gain
      + DC_change_Q_DA
```

where `t_65 = |temperature_F - 65|`.

This is a **linear regression** with four predictors per DSO, fit separately for weekdays and weekends.

---

### calibrate_q_bid_forecast_correction.py — Step by Step

#### 1. Load inputs
```python
baseline_df = read_timeseries_csv(baseline_csv)    # DA_Q_forecast.csv  → uncorrected Q
actual_df   = read_timeseries_csv(actual_csv)      # actual_da_q.csv    → realized Q
temp_df     = read_timeseries_csv(temperature_csv) # weather.dat        → hourly temperature
```
All three are aligned to a shared hourly `DatetimeIndex`. Duplicates are collapsed by mean.

#### 2. Identify DSO columns
```python
def parse_dso_id(column_name):
    # Matches: "DSO_1", "DSO 1", "da_q1", "Bus_1"
    for pattern in DSO_PATTERNS:
        match = pattern.match(column_name)
        ...
```
This maps column names to integer DSO IDs in both baseline and actual DataFrames. Only DSOs present in **both** files are calibrated.

#### 3. Temperature conversion
```python
def to_fahrenheit(series, unit):
    if unit == "C":
        return series * 9.0 / 5.0 + 32.0
```
Input temperatures are converted to Fahrenheit regardless of source unit, because the model threshold (65°F) is hardcoded.

#### 4. Build the design matrix and fit — `fit_coefficients()`
```python
df["t65"]   = (df["temperature_f"] - 65.0).abs()
df["t65_2"] = df["t65"] ** 2

# Split into weekday (Mon-Fri) and weekend (Sat-Sun)
weekday_mask = df.index.dayofweek <= 4

# For each subset:
x = np.column_stack([
    baseline_q,   # → Q_gain coefficient
    t65,          # → t_65 coefficient
    t65_2,        # → t_65_2 coefficient
    np.ones(n),   # → DC_change_Q_DA (intercept)
])
y = actual_q

coeffs, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
```
`np.linalg.lstsq` solves the **ordinary least squares** problem — it finds the four coefficients that minimize `sum((actual_Q - predicted_Q)²)` across all hours in that day type.

This produces **two `FitResult` objects per DSO** — one weekday, one weekend — each containing:
- `gain_q` → `Q_gain`
- `gain_t65` → `t_65`
- `gain_t65_2` → `t_65_2`
- `dc_change` → `DC_change_Q_DA`
- `rmse` and `n_samples` (diagnostics)

#### 5. Build output JSON
```python
payload[f"DSO_{dso}"] = {
    "correct": True,
    "Q_gain":          [wkday.gain_q,     wkend.gain_q],
    "t_65":            [wkday.gain_t65,   wkend.gain_t65],
    "t_65_2":          [wkday.gain_t65_2, wkend.gain_t65_2],
    "DC_change_Q_DA":  [wkday.dc_change,  wkend.dc_change],
}
```
Each coefficient is a **two-element list: `[weekday_value, weekend_value]`**, matching the runtime forecasting code's indexing convention.

---

### calibrate_config.py — Step by Step

This script does **no fitting** — it merges calibration results into an existing config file.

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

Based on a close read of both scripts, it's slightly more involved than that. Here's the full picture:

### Files produced by calibration that feed back into simulations

#### 1. `rates_config_calibrated.json5` ✅
Replace `rates_config.json5` in `metadata_path` (`glm_dsot/data/`). This carries the updated `Q_bid_forecast_correction` block with the new per-DSO weekday/weekend coefficients.

#### 2. `DSO_quadratic_curves.json` ✅
This maps quantity bids (MW) to day-ahead prices per DSO. It is written to `case_path` but needs to be placed where the **DSO bidding model** can find it at runtime — check where `tesp_support.dsot.dso_quadratic_curves` reads it from, as it may need to go into `metadata_path` or a per-DSO subfolder rather than the annual case folder.

#### 3. `actual_da_q.csv` ⚠️ intermediate only
This is an intermediate artifact used only during calibration. It does **not** need to be copied anywhere for the next simulation.

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