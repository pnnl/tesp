#!/usr/bin/env python3
"""Calibrate Q_bid_forecast_correction coefficients per DSO.

This script fits the same model used in
`tesp_support.dsot.forecasting.Forecasting.correcting_Q_forecast_10_AM`:

    new_Q = Q_10_AM * Q_gain + t_65 * t_65_gain + t_65^2 * t_65_2_gain + DC_change_Q_DA

where:
- t_65 = |temperature_F - 65|
- coefficients are fit separately for weekday and weekend

Inputs are hourly time-series CSV files:
1) baseline quantity (proxy for uncorrected Q_10_AM target-hour quantities)
2) actual quantity (target realized quantity)
3) temperature (F by default, optionally C)

By default, all DSOs use the same temperature column. A per-DSO temperature
column template can also be provided.

For DSOT weather.dat inputs:
- weather.dat is a CSV-like file with a `temperature` column.
- if values are in Celsius, set `--temperature-unit C`.

-------------------------------------------------------------------------------
Numerical stability note
-------------------------------------------------------------------------------
The regressors [baseline_q, t65, t65^2, 1] are on very different scales and
t65 / t65^2 are strongly collinear. A raw np.linalg.lstsq on this design is
ill-conditioned and tends to produce large, mutually-offsetting coefficients
(e.g. a huge negative t_65 gain compensated by a huge DC_change intercept).
Those coefficients minimize training RMSE but are non-physical and can inflate
the day-ahead demand offset enough to make the DA SCED infeasible.

This version:
  * standardizes regressors before solving and transforms coefficients back,
  * optionally applies ridge regularization (intercept not penalized),
  * reports the design condition number,
  * validates output coefficients against physical bounds and refuses to
    (or warns before) writing clearly non-physical fits.
-------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("calibrate_q_bid")


DSO_PATTERNS = [
    re.compile(r"^DSO[ _]?(\d+)$", re.IGNORECASE),
    re.compile(r"^da_q(\d+)$", re.IGNORECASE),
    re.compile(r"^Bus[ _]?(\d+)$", re.IGNORECASE),
]


# --------------------------------------------------------------------------- #
# Validation configuration (tunable via CLI)
# --------------------------------------------------------------------------- #
@dataclass
class ValidationConfig:
    # Ridge penalty applied to standardized regressors (0 => plain OLS on
    # standardized features, which is already far better conditioned).
    ridge_lambda: float = 1.0
    # Warn if the (standardized) design condition number exceeds this.
    cond_warn: float = 1.0e6
    # Plausible ranges for the returned coefficients.
    q_gain_range: Tuple[float, float] = (0.0, 1.5)
    # t_65 is bounded by its contribution relative to load
    temp_contrib_frac_of_mean: float = 1.5
    # DC_change is bounded relative to the mean baseline quantity for the DSO.
    # |DC_change| must not exceed dc_change_frac_of_mean * mean(baseline_q).
    dc_change_frac_of_mean: float = 0.5
    # If True, a coefficient set that fails bounds raises instead of warns.
    strict: bool = False


@dataclass
class FitResult:
    gain_q: float
    gain_t65: float
    gain_t65_2: float
    dc_change: float
    rmse: float
    n_samples: int
    cond_number: float = float("nan")
    warnings: List[str] = field(default_factory=list)


def read_timeseries_csv(path: Path) -> pd.DataFrame:
    """Read a CSV with a datetime index in column 0."""
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{path}: index is not datetime after parsing")
    df = df.sort_index()
    # Ensure hourly alignment if source has duplicate timestamps.
    if df.index.has_duplicates:
        df = df.groupby(level=0).mean(numeric_only=True)
    return df


def parse_dso_id(column_name: str) -> Optional[int]:
    for pattern in DSO_PATTERNS:
        match = pattern.match(column_name.strip())
        if match:
            return int(match.group(1))
    return None


def map_dso_columns(df: pd.DataFrame) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for col in df.columns:
        dso = parse_dso_id(str(col))
        if dso is not None:
            mapping[dso] = col
    return mapping


def choose_temperature_series(
    temp_df: pd.DataFrame,
    dso_id: int,
    default_col: Optional[str],
    col_template: Optional[str],
) -> pd.Series:
    if col_template:
        candidate = col_template.format(dso=dso_id)
        if candidate in temp_df.columns:
            return temp_df[candidate]

    if default_col and default_col in temp_df.columns:
        return temp_df[default_col]

    # Fallback to single-column temperature files.
    if len(temp_df.columns) == 1:
        return temp_df.iloc[:, 0]

    raise ValueError(
        f"No temperature column found for DSO {dso_id}. "
        f"Tried template/default and no single-column fallback available."
    )


def to_fahrenheit(series: pd.Series, unit: str) -> pd.Series:
    u = unit.upper()
    if u == "F":
        return series
    if u == "C":
        return series * 9.0 / 5.0 + 32.0
    raise ValueError(f"Unsupported temperature unit: {unit}. Expected 'F' or 'C'.")


# --------------------------------------------------------------------------- #
# NEW: stable solve (standardize -> ridge -> back-transform)
# --------------------------------------------------------------------------- #
def _stable_linear_fit(
    features: np.ndarray,      # (n, 3): [baseline_q, t65, t65_2]
    y: np.ndarray,             # (n,)
    ridge_lambda: float,
) -> Tuple[np.ndarray, float, float]:
    """Fit y ~ a*q + b*t65 + c*t65_2 + d on standardized features.

    Returns:
        (coeffs_original_space, rmse, cond_number)
        coeffs_original_space = [gain_q, gain_t65, gain_t65_2, dc_change]
    """
    n = features.shape[0]

    mu = features.mean(axis=0)
    sigma = features.std(axis=0)
    # Guard against zero-variance columns (e.g. constant temperature window).
    sigma_safe = np.where(sigma > 0, sigma, 1.0)

    xs = (features - mu) / sigma_safe          # standardized regressors
    design = np.column_stack([xs, np.ones(n)])  # + intercept column

    # Condition number on the standardized design (this is the number that
    # actually matters for coefficient stability).
    cond_number = float(np.linalg.cond(design))

    # Ridge on standardized features; do NOT penalize the intercept.
    p = design.shape[1]
    penalty = np.eye(p) * ridge_lambda
    penalty[-1, -1] = 0.0

    xtx = design.T @ design + penalty
    xty = design.T @ y
    beta_std = np.linalg.solve(xtx, xty)  # [b_q, b_t65, b_t65_2, b0] (std space)

    # Back-transform standardized coefficients to original feature space.
    gains_std = beta_std[:3]
    b0_std = beta_std[3]
    gains = gains_std / sigma_safe
    intercept = b0_std - float(np.sum(gains_std * mu / sigma_safe))

    coeffs = np.array([gains[0], gains[1], gains[2], intercept])

    y_hat = features @ gains + intercept
    rmse = float(np.sqrt(np.mean((y - y_hat) ** 2)))

    return coeffs, rmse, cond_number


def _validate_coefficients(
    result: FitResult,
    baseline_mean: float,
    t65_max: float,  
    cfg: ValidationConfig,
    label: str,
    dso: int,
) -> FitResult:
    """Check coefficients against physical bounds; warn or raise."""
    problems: List[str] = []

    lo, hi = cfg.q_gain_range
    if not (lo <= result.gain_q <= hi):
        problems.append(f"Q_gain={result.gain_q:.4f} outside {cfg.q_gain_range}")

    # The uncorrected base forecast (Q_10_AM) is temperature-blind, so a large
    # t_65 is expected for weather-sensitive DSOs. What we actually want to
    # catch is a temperature term whose magnitude is implausible relative to
    # the load it's correcting. Evaluate the term at the largest observed t65.
    temp_contrib = (abs(result.gain_t65) * t65_max
                    + abs(result.gain_t65_2) * t65_max ** 2)
    contrib_limit = cfg.temp_contrib_frac_of_mean * abs(baseline_mean)
    if contrib_limit > 0 and temp_contrib > contrib_limit:
        problems.append(
            f"temperature-term contribution={temp_contrib:.1f} "
            f"(at t65_max={t65_max:.1f}) > "
            f"{cfg.temp_contrib_frac_of_mean:.2f} * mean(baseline_q)"
            f"={contrib_limit:.1f}"
        )

    dc_limit = cfg.dc_change_frac_of_mean * abs(baseline_mean)
    if dc_limit > 0 and abs(result.dc_change) > dc_limit:
        problems.append(
            f"|DC_change_Q_DA|={abs(result.dc_change):.1f} > "
            f"{cfg.dc_change_frac_of_mean:.2f} * mean(baseline_q)"
            f"={dc_limit:.1f}"
        )

    if result.cond_number > cfg.cond_warn:
        problems.append(
            f"ill-conditioned design (cond={result.cond_number:.1e} "
            f"> {cfg.cond_warn:.1e})"
        )

    if problems:
        msg = (
            f"DSO {dso} [{label}] failed coefficient validation: "
            + "; ".join(problems)
        )
        if cfg.strict:
            raise ValueError(msg)
        log.warning(msg)
        result.warnings.extend(problems)

    return result

def _weekend_mask(index: pd.DatetimeIndex) -> pd.Series:
    """Return boolean mask: True where the DELIVERY day is a weekend.

    Runtime correcting_Q_forecast_10_AM buckets Sat/Sun into idx==1 (weekend)
    and Mon-Fri into idx==0 (weekday), keyed on the delivery day. Our
    calibration rows are already timestamped at delivery time, so we bucket
    directly on the calendar weekday -- no bid->delivery shift required.

    pandas dayofweek: Mon=0 ... Sat=5, Sun=6.
    """
    dow = index.dayofweek
    return (dow >= 5)  # Saturday or Sunday

def fit_coefficients(
    baseline_q: pd.Series,
    actual_q: pd.Series,
    temperature_f: pd.Series,
    min_samples: int,
    cfg: ValidationConfig,
    dso: int,
) -> Tuple[FitResult, FitResult]:
    """Fit weekday/weekend coefficients using stabilized least squares."""
    df = pd.DataFrame(
        {
            "baseline_q": baseline_q,
            "actual_q": actual_q,
            "temperature_f": temperature_f,
        }
    ).dropna()

    log.info("DSO %d fit window: %s -> %s (%d rows, %d days), temp %.1f-%.1f F",
         dso, df.index.min(), df.index.max(), len(df),
         (df.index.max()-df.index.min()).days,
         df["temperature_f"].min(), df["temperature_f"].max())

    if df.empty:
        raise ValueError("No overlapping non-null samples after alignment")

    df["t65"] = (df["temperature_f"] - 65.0).abs()
    df["t65_2"] = df["t65"] ** 2
    weekend = _weekend_mask(df.index)
    weekday_mask = ~weekend

    # --- alignment diagnostic: confirm the split matches runtime expectations
    n_wd, n_we = int(weekday_mask.sum()), int(weekend.sum())
    frac_we = n_we / max(len(df), 1)
    log.info("DSO %d day-type split: weekday=%d (%.0f%%), weekend=%d (%.0f%%)",
             dso, n_wd, 100*(1-frac_we), n_we, 100*frac_we)
    # A full year of hourly data is ~28.6%% weekend. Flag gross deviations that
    # would indicate a wrong day-of-week convention or a shifted index.
    if not (0.22 <= frac_we <= 0.35):
        log.warning("DSO %d: weekend fraction %.1f%% is outside the expected "
                    "~28.6%% for a full year. Check the weekday/weekend "
                    "convention -- it may not match correcting_Q_forecast_10_AM.",
                    dso, 100*frac_we)

    # NEW: sanity-check scale consistency between baseline and actual. A large
    # systematic offset here gets absorbed into DC_change_Q_DA and is a common
    # source of non-physical intercepts.
    base_mean = float(df["baseline_q"].mean())
    act_mean = float(df["actual_q"].mean())
    if base_mean != 0 and abs(act_mean - base_mean) / abs(base_mean) > 0.5:
        log.warning(
            "DSO %d: baseline_q mean (%.1f) and actual_q mean (%.1f) differ by "
            ">50%%. Check units/scale; the offset will load into DC_change_Q_DA.",
            dso, base_mean, act_mean,
        )

    def fit_subset(mask: pd.Series, label: str) -> FitResult:
        subset = df.loc[mask]
        n = len(subset)
        if n < min_samples:
            raise ValueError(
                f"Insufficient {label} samples for fit: {n} < {min_samples}. "
                "Provide more data or reduce --min-samples."
            )

        features = np.column_stack(
            [
                subset["baseline_q"].to_numpy(),
                subset["t65"].to_numpy(),
                subset["t65_2"].to_numpy(),
            ]
        )
        y = subset["actual_q"].to_numpy()

        coeffs, rmse, cond_number = _stable_linear_fit(
            features, y, ridge_lambda=cfg.ridge_lambda
        )

        result = FitResult(
            gain_q=float(coeffs[0]),
            gain_t65=float(coeffs[1]),
            gain_t65_2=float(coeffs[2]),
            dc_change=float(coeffs[3]),
            rmse=rmse,
            n_samples=n,
            cond_number=cond_number,
        )

        subset_base_mean = float(subset["baseline_q"].mean())
        subset_t65_max = float(subset["t65"].max())
        return _validate_coefficients(result, subset_base_mean, subset_t65_max, cfg, label, dso)

    weekday_fit = fit_subset(weekday_mask, "weekday")
    weekend_fit = fit_subset(weekend,      "weekend")
    return weekday_fit, weekend_fit


def build_output(
    fits: Dict[int, Tuple[FitResult, FitResult]],
    include_diagnostics: bool,
) -> Dict[str, object]:
    payload: Dict[str, object] = {"default": {"correct": False}}

    for dso in sorted(fits):
        wkday, wkend = fits[dso]
        item: Dict[str, object] = {
            "correct": True,
            "Q_gain": [wkday.gain_q, wkend.gain_q],
            "t_65": [wkday.gain_t65, wkend.gain_t65],
            "t_65_2": [wkday.gain_t65_2, wkend.gain_t65_2],
            "DC_change_Q_DA": [wkday.dc_change, wkend.dc_change],
        }
        if include_diagnostics:
            item["_fit_diagnostics"] = {
                "weekday": {
                    "rmse": wkday.rmse,
                    "n_samples": wkday.n_samples,
                    "cond_number": wkday.cond_number,
                    "warnings": wkday.warnings,
                },
                "weekend": {
                    "rmse": wkend.rmse,
                    "n_samples": wkend.n_samples,
                    "cond_number": wkend.cond_number,
                    "warnings": wkend.warnings,
                },
            }
        payload[f"DSO_{dso}"] = item

    return payload


def parse_dso_list(raw: Optional[str]) -> Optional[List[int]]:
    if raw is None or raw.strip() == "":
        return None
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def calibrate_q_bid_forecast_correction(
    baseline_csv: Path,
    actual_csv: Path,
    temperature_csv: Optional[Path] = None,
    temperature_csv_template: Optional[str] = None,
    temperature_column: Optional[str] = None,
    temperature_column_template: Optional[str] = None,
    temperature_unit: str = "F",
    dsos: Optional[List[int]] = None,
    min_samples: int = 72,
    include_diagnostics: bool = False,
    output: Optional[Path] = None,
    cfg: Optional[ValidationConfig] = None,
) -> Tuple[Dict[str, object], Dict[int, Tuple[FitResult, FitResult]]]:
    """Calibrate DSO forecast-correction coefficients.

    Returns:
        Tuple of (json_payload, fit_results_by_dso).
    """
    if cfg is None:
        cfg = ValidationConfig()

    baseline_df = read_timeseries_csv(baseline_csv)
    actual_df = read_timeseries_csv(actual_csv)
    if temperature_csv is None and not temperature_csv_template:
        raise ValueError("Either temperature_csv or temperature_csv_template must be provided")

    temp_df: Optional[pd.DataFrame] = None
    if temperature_csv is not None:
        temp_df = read_timeseries_csv(temperature_csv)

    baseline_map = map_dso_columns(baseline_df)
    actual_map = map_dso_columns(actual_df)

    common_dsos = sorted(set(baseline_map.keys()) & set(actual_map.keys()))
    if dsos is None:
        dso_ids = common_dsos
    else:
        dso_ids = [d for d in dsos if d in common_dsos]

    if not dso_ids:
        raise ValueError(
            "No DSOs available to calibrate. Check column naming in baseline/actual CSV files. "
            "Expected patterns include DSO_1, DSO 1, da_q1, Bus1."
        )

    fits: Dict[int, Tuple[FitResult, FitResult]] = {}
    for dso in dso_ids:
        baseline_col = baseline_map[dso]
        actual_col = actual_map[dso]

        if temperature_csv_template:
            dso_temp_path = Path(temperature_csv_template.format(dso=dso))
            dso_temp_df = read_timeseries_csv(dso_temp_path)
            temp_series = choose_temperature_series(
                dso_temp_df,
                dso,
                default_col=temperature_column,
                col_template=temperature_column_template,
            )
        else:
            if temp_df is None:
                raise ValueError("Shared temperature dataframe is not available")
            temp_series = choose_temperature_series(
                temp_df,
                dso,
                default_col=temperature_column,
                col_template=temperature_column_template,
            )

        temp_series = to_fahrenheit(temp_series, temperature_unit)

        wkday, wkend = fit_coefficients(
            baseline_df[baseline_col],
            actual_df[actual_col],
            temp_series,
            min_samples=min_samples,
            cfg=cfg,
            dso=dso,
        )
        fits[dso] = (wkday, wkend)

    output_payload = build_output(fits, include_diagnostics=include_diagnostics)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as fp:
            json.dump(output_payload, fp, indent=2)

    return output_payload, fits


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calibrate Q_bid_forecast_correction coefficients per DSO."
    )
    parser.add_argument("--baseline-csv", required=True, help="Hourly baseline Q CSV path")
    parser.add_argument("--actual-csv", required=True, help="Hourly actual Q CSV path")
    parser.add_argument(
        "--temperature-csv",
        required=False,
        default=None,
        help="Shared temperature CSV path (can be weather.dat).",
    )
    parser.add_argument(
        "--temperature-csv-template",
        default=None,
        help="Per-DSO temperature file template, e.g. 'C:/case/DSO_{dso}/weather.dat'.",
    )
    parser.add_argument(
        "--temperature-column",
        default=None,
        help="Temperature column name (shared by all DSOs). If omitted and the CSV has one column, that column is used.",
    )
    parser.add_argument(
        "--temperature-column-template",
        default=None,
        help="Per-DSO temperature column template, e.g. 'DSO_{dso}_temp'.",
    )
    parser.add_argument(
        "--temperature-unit",
        choices=["F", "C", "f", "c"],
        default="F",
        help="Temperature unit of the source file(s).",
    )
    parser.add_argument(
        "--dsos",
        default=None,
        help="Comma-separated DSO IDs to calibrate (default: all DSOs found in both baseline and actual CSVs).",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=72,
        help="Minimum samples required in each day type (weekday and weekend).",
    )
    parser.add_argument(
        "--include-diagnostics",
        action="store_true",
        help="Include fit RMSE, sample counts, condition numbers, and warnings in the output JSON.",
    )

    parser.add_argument(
        "--ridge-lambda",
        type=float,
        default=1.0,
        help="Ridge penalty on standardized regressors (0 => OLS on standardized features).",
    )
    parser.add_argument(
        "--cond-warn",
        type=float,
        default=1.0e6,
        help="Warn if the standardized design condition number exceeds this value.",
    )
    parser.add_argument(
        "--q-gain-min",
        type=float,
        default=0.0,
        help="Lower bound for a plausible Q_gain coefficient.",
    )
    parser.add_argument(
        "--q-gain-max",
        type=float,
        default=1.5,
        help="Upper bound for a plausible Q_gain coefficient.",
    )
    parser.add_argument(
        "--temp-contrib-frac-of-mean",
        type=float,
        default=1.5,
        help=("Max temperature-term contribution (evaluated at the largest "
              "observed |temp-65|) as a fraction of mean baseline load."),
    )
    parser.add_argument(
        "--dc-change-frac-of-mean",
        type=float,
        default=0.5,
        help=(
            "Max |DC_change_Q_DA| as a fraction of the mean baseline quantity "
            "for that DSO/day-type. Guards against a runaway additive offset."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Raise (instead of warn) when a coefficient set fails validation.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path for Q_bid_forecast_correction block.",
    )

    args = parser.parse_args()

    if not args.temperature_csv and not args.temperature_csv_template:
        raise ValueError("Provide --temperature-csv or --temperature-csv-template")

    cfg = ValidationConfig(
        ridge_lambda=args.ridge_lambda,
        cond_warn=args.cond_warn,
        q_gain_range=(args.q_gain_min, args.q_gain_max),
        temp_contrib_frac_of_mean=args.temp_contrib_frac_of_mean,
        t65_abs_max=args.t65_abs_max,
        t65_2_abs_max=args.t65_2_abs_max,
        dc_change_frac_of_mean=args.dc_change_frac_of_mean,
        strict=args.strict,
    )

    requested_dsos = parse_dso_list(args.dsos)
    output_path = Path(args.output)

    try:
        output_payload, fits = calibrate_q_bid_forecast_correction(
            baseline_csv=Path(args.baseline_csv),
            actual_csv=Path(args.actual_csv),
            temperature_csv=Path(args.temperature_csv) if args.temperature_csv else None,
            temperature_csv_template=args.temperature_csv_template,
            temperature_column=args.temperature_column,
            temperature_column_template=args.temperature_column_template,
            temperature_unit=args.temperature_unit,
            dsos=requested_dsos,
            min_samples=args.min_samples,
            include_diagnostics=args.include_diagnostics,
            output=output_path,
            cfg=cfg,
        )
    except ValueError as exc:
        # In --strict mode a failed validation propagates here.
        log.error("Calibration aborted: %s", exc)
        return 1

    print(f"Wrote calibrated coefficients for {len(fits)} DSO(s) -> {output_path}")
    print("DSO fit summary:")

    n_flagged = 0
    for dso in sorted(fits):
        wkday, wkend = fits[dso]
        flags = wkday.warnings + wkend.warnings
        if flags:
            n_flagged += 1
        flag_str = "  [FLAGGED]" if flags else ""
        print(
            f"  DSO_{dso}: "
            f"weekday(n={wkday.n_samples}, rmse={wkday.rmse:.4f}, "
            f"cond={wkday.cond_number:.1e}), "
            f"weekend(n={wkend.n_samples}, rmse={wkend.rmse:.4f}, "
            f"cond={wkend.cond_number:.1e})"
            f"{flag_str}"
        )
        for w in flags:
            print(f"      - {w}")

    if n_flagged:
        log.warning(
            "%d of %d DSO(s) produced coefficients that failed physical-bounds "
            "validation. Review the flags above before using this JSON in a run; "
            "these are the most likely to trigger an infeasible DA solve "
            "('No DA starting point'). Re-run with --strict to hard-fail.",
            n_flagged, len(fits),
        )
        # Non-zero exit so CI / batch pipelines notice, without discarding output.
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())