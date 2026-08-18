# ============================================================
# UC10 - SLA / Temporal Monitoring
# Extracted from: feature+dq.ipynb (Cell 3)
#
# This is the EXACT Colab SLA implementation converted into a
# standalone Python module.  NO logic, formula, threshold,
# parameter, or algorithm has been changed.
#
# Entry point:
#     run_sla_monitoring(df, config_overrides=None)
#
# Output:
#     outputs/sla_temporal_findings.json
#
# Required input columns (from feature-engineered DataFrame):
#     Record_ID, Record_Type, Batch_ID, Batch_Date,
#     Processed_Date, Processing_Latency_Days, SLA_Target_Days,
#     Urgency_Flag, Batch_SLA_Breach_Rate,
#     Rolling_7D_Avg_SLA_Breach_Rate, SLA_Breach_Rate_Vs_Trend_Diff,
#     Batch_Volume, Rolling_7D_Avg_Volume, Volume_Vs_Trend_Ratio,
#     Retry_Count, Pipeline_Gap_Flag, Days_Since_Prev_Batch
# ============================================================

from __future__ import annotations

import datetime
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


from typing import Any
# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    # -----------------------------------------------------------------------
    # Historical baseline
    # -----------------------------------------------------------------------
    # Rolling window size (number of past batch observations used to compute
    # the historical median and robust scale at each timepoint).
    # Rationale: 30 batches ≈ ~1 month of daily batches; gives stable baseline
    # without being overly sensitive to ancient history.
    "baseline_window": 30,

    # Minimum number of past observations required before a baseline is
    # considered reliable. Below this, baseline is set to None / NaN and
    # EWMA/CUSUM signals are suppressed.
    "baseline_min_obs": 5,

    # Configurable scale floor used when the entire historical window is constant
    # (MAD == 0 and sample std == 0). Prevents division-by-zero or infinite
    # sensitivity on numerical noise without masking genuine shifts.
    "min_scale_floor": 0.01,

    # -----------------------------------------------------------------------
    # EWMA — Exponentially Weighted Moving Average
    # -----------------------------------------------------------------------
    # Smoothing factor (0 < alpha ≤ 1).
    # alpha=0.3 gives moderate smoothing; EWMA responds to a gradual shift
    # over roughly 1/alpha ≈ 3–4 periods.
    "ewma_alpha": 0.3,

    # Number of initial observations used to seed the EWMA (warm-up).
    # The EWMA is initialised to the median of the first ewma_warmup_n values.
    "ewma_warmup_n": 5,

    # EWMA signal thresholds expressed as multiples of robust sigma.
    # These are statistical detection thresholds, NOT business SLA targets.
    "ewma_warning_sigma": 1.5,   # WARNING:  deviation ≥ 1.5 × robust_sigma
    "ewma_alert_sigma":   2.0,   # ALERT:    deviation ≥ 2.0 × robust_sigma

    # -----------------------------------------------------------------------
    # CUSUM — Cumulative Sum Control Chart
    # -----------------------------------------------------------------------
    # Reference value k (half the allowable shift, in units of robust sigma).
    # Standard choice for detecting a 1-sigma shift.
    "cusum_k_sigma": 0.5,

    # Decision threshold h (in units of robust sigma).
    # Standard value; requires a sustained cumulative deviation before signal.
    "cusum_h_sigma": 5.0,

    # -----------------------------------------------------------------------
    # Pipeline signal classification
    # Thresholds derived from observable data distribution:
    #   - Days_Since_Prev_Batch is 1.0 for 91 % of records; ≥ 2 is abnormal.
    #   - Retry_Count max is 3; ≥ 2 indicates repeated failure.
    #   - Pipeline_Gap_Flag is a boolean flag defined in the dataset.
    # No pipeline SLA target exists → no pipeline SLA breach is declared.
    # -----------------------------------------------------------------------
    "pipeline_gap_days_threshold": 2,    # Days_Since_Prev_Batch ≥ this → DEGRADED
    "pipeline_retry_threshold":    2,    # Retry_Count ≥ this (per record) → DEGRADED

    # -----------------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------------
    "output_dir":               "outputs",
    "findings_filename":        "sla_temporal_findings.json",
}


def get_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a merged configuration dictionary.

    Parameters
    ----------
    overrides:
        Optional key/value pairs that override specific defaults.

    Returns
    -------
    dict
        Full configuration with overrides applied.
    """
    cfg = dict(_DEFAULTS)
    if overrides:
        cfg.update(overrides)
    return cfg


"""
sla_metrics.py
==============
SLA metric extraction from the feature dataframe.

Responsibilities
----------------
* Assign each record its ``sla_group`` (business population used for baseline
  segmentation and SLA assessment).
* Classify each record's temporal data validity.
* Derive per-record timeliness metrics (latency, utilisation, remaining time).
* Extract batch-level volume series (centered on Volume_Vs_Trend_Ratio).
* Extract whole-batch and group-specific breach rate time series.
* Extract batch-level pipeline observable signals.
"""


import logging
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Sentinel used when SLA assessment is not possible
NOT_ASSESSABLE: str = "NOT_ASSESSABLE"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assign_sla_groups(df: pd.DataFrame) -> pd.Series:
    """Return a Series of sla_group labels aligned with ``df``."""
    groups = df["Record_Type"].copy().astype(str)

    pa_mask = df["Record_Type"] == "PRIOR_AUTH"
    if pa_mask.any():
        urgency = df.loc[pa_mask, "Urgency_Flag"].fillna("UNKNOWN")
        groups.loc[pa_mask] = "PRIOR_AUTH_" + urgency.astype(str)

    return groups


def classify_temporal_validity(df: pd.DataFrame) -> pd.Series:
    """Classify each record's temporal data validity for SLA assessment."""
    lat = df["Processing_Latency_Days"]
    proc_date_null = df["Processed_Date"].isnull()

    validity = pd.Series("VALID", index=df.index, dtype=str)

    # Missing Processed_Date -> assessment impossible
    validity[proc_date_null] = "NULL_NO_DATE"

    # Processing_Latency_Days null while Processed_Date exists
    lat_null_with_date = lat.isnull() & ~proc_date_null
    validity[lat_null_with_date] = "MISSING_LATENCY"

    # Negative latency: Processed_Date < Service_Date (data quality problem)
    lat_negative = lat.notna() & (lat < 0)
    validity[lat_negative] = "NEGATIVE"

    return validity


def extract_record_timeliness_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Derive per-record timeliness metric columns."""
    out = df.copy()
    out["sla_group"] = assign_sla_groups(df)
    out["temporal_validity"] = classify_temporal_validity(df)

    valid_mask = out["temporal_validity"] == "VALID"
    positive_target = out["SLA_Target_Days"].fillna(0) > 0

    # SLA utilisation: fraction of SLA budget consumed
    out["sla_utilization"] = np.nan
    assessable = valid_mask & positive_target
    out.loc[assessable, "sla_utilization"] = (
        out.loc[assessable, "Processing_Latency_Days"]
        / out.loc[assessable, "SLA_Target_Days"]
    )

    # Remaining SLA time
    out["remaining_sla_days"] = np.nan
    out.loc[assessable, "remaining_sla_days"] = (
        out.loc[assessable, "SLA_Target_Days"]
        - out.loc[assessable, "Processing_Latency_Days"]
    )

    return out


def build_batch_volume_series(df: pd.DataFrame) -> pd.DataFrame:
    """Build a chronological batch-level volume time-series."""
    batch_cols = [
        "Batch_ID", "Batch_Date",
        "Batch_Volume", "Rolling_7D_Avg_Volume", "Volume_Vs_Trend_Ratio",
    ]
    available = [c for c in batch_cols if c in df.columns]
    if "Batch_ID" not in available or "Batch_Date" not in available:
        logger.warning("Batch_ID or Batch_Date missing; volume series unavailable.")
        return pd.DataFrame()

    batch_ts = (
        df[available]
        .drop_duplicates(subset=["Batch_ID"])
        .copy()
    )
    batch_ts["Batch_Date"] = pd.to_datetime(batch_ts["Batch_Date"], errors="coerce")
    batch_ts = batch_ts.sort_values("Batch_Date").reset_index(drop=True)

    batch_ts = batch_ts.rename(columns={
        "Batch_ID":              "batch_id",
        "Batch_Date":            "batch_date",
        "Batch_Volume":          "actual_volume",
        "Rolling_7D_Avg_Volume": "baseline_volume",
        "Volume_Vs_Trend_Ratio": "volume_ratio",
    })

    if "volume_ratio" in batch_ts.columns:
        batch_ts["volume_deviation"] = batch_ts["volume_ratio"] - 1.0

    return batch_ts


def build_batch_breach_rate_series(
    df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build chronological batch-level SLA breach-rate time-series."""
    df_work = df.copy()
    df_work["sla_group"] = assign_sla_groups(df_work)
    df_work["temporal_validity"] = classify_temporal_validity(df_work)
    df_work["Batch_Date"] = pd.to_datetime(df_work["Batch_Date"], errors="coerce")

    result: dict[str, pd.DataFrame] = {}

    # 1. Whole-batch time series
    whole_batch = (
        df_work.groupby(["Batch_ID", "Batch_Date"])
        .agg(
            batch_breach_rate=("Batch_SLA_Breach_Rate", "first"),
            rolling_7d_avg_breach_rate=("Rolling_7D_Avg_SLA_Breach_Rate", "first"),
            breach_rate_vs_trend_diff=("SLA_Breach_Rate_Vs_Trend_Diff", "first"),
        )
        .reset_index()
        .sort_values("Batch_Date")
        .reset_index(drop=True)
    )
    whole_batch = whole_batch.rename(columns={"Batch_ID": "batch_id", "Batch_Date": "batch_date"})
    whole_batch["sla_group"] = "WHOLE_BATCH"
    result["WHOLE_BATCH"] = whole_batch

    # 2. Group-specific time series (derived from assessable records)
    for group in df_work["sla_group"].unique():
        grp_df = df_work[df_work["sla_group"] == group].copy()
        grp_assessable = grp_df[grp_df["temporal_validity"] == "VALID"]

        counts = grp_df.groupby(["Batch_ID", "Batch_Date"]).size().reset_index(name="total_in_grp")
        assessable_counts = grp_assessable.groupby(["Batch_ID", "Batch_Date"]).size().reset_index(name="assessable_in_grp")

        breached_mask = grp_assessable["Processing_Latency_Days"] > grp_assessable["SLA_Target_Days"]
        breached_counts = grp_assessable[breached_mask].groupby(["Batch_ID", "Batch_Date"]).size().reset_index(name="breached_in_grp")

        batch_grp = counts.merge(assessable_counts, on=["Batch_ID", "Batch_Date"], how="left").merge(breached_counts, on=["Batch_ID", "Batch_Date"], how="left")
        batch_grp["assessable_in_grp"] = batch_grp["assessable_in_grp"].fillna(0)
        batch_grp["breached_in_grp"] = batch_grp["breached_in_grp"].fillna(0)

        batch_grp["batch_breach_rate"] = np.where(
            batch_grp["assessable_in_grp"] > 0,
            batch_grp["breached_in_grp"] / batch_grp["assessable_in_grp"],
            0.0
        )
        batch_grp = batch_grp.rename(columns={"Batch_ID": "batch_id", "Batch_Date": "batch_date"})
        batch_grp["sla_group"] = group
        batch_grp["rolling_7d_avg_breach_rate"] = np.nan
        batch_grp["breach_rate_vs_trend_diff"] = np.nan
        batch_grp = batch_grp.sort_values("batch_date").reset_index(drop=True)

        result[group] = batch_grp[[
            "batch_id", "batch_date", "batch_breach_rate",
            "rolling_7d_avg_breach_rate", "breach_rate_vs_trend_diff", "sla_group"
        ]]

    return result


def build_pipeline_signals(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Build batch-level pipeline observable signals."""
    gap_thresh: int   = cfg.get("pipeline_gap_days_threshold", 2)
    retry_thresh: int = cfg.get("pipeline_retry_threshold", 2)

    df_work = df.copy()
    df_work["Batch_Date"] = pd.to_datetime(df_work["Batch_Date"], errors="coerce")

    batch_pipeline = (
        df_work.groupby(["Batch_ID", "Batch_Date"])
        .agg(
            retry_count_sum       = ("Retry_Count",           "sum"),
            max_retry_count       = ("Retry_Count",           "max"),
            pipeline_gap          = ("Pipeline_Gap_Flag",     "any"),
            days_since_prev_batch = ("Days_Since_Prev_Batch", "first"),
        )
        .reset_index()
        .sort_values("Batch_Date")
        .reset_index(drop=True)
    )
    batch_pipeline = batch_pipeline.rename(columns={"Batch_ID": "batch_id", "Batch_Date": "batch_date"})

    statuses = []
    reasons = []
    for _, row in batch_pipeline.iterrows():
        if row["pipeline_gap"]:
            statuses.append("GAP_DETECTED")
            reasons.append(
                f"Pipeline_Gap_Flag detected for batch. "
                f"Days since previous batch: {row['days_since_prev_batch']}."
            )
        elif (
            pd.notna(row["days_since_prev_batch"])
            and row["days_since_prev_batch"] >= gap_thresh
        ) or (
            pd.notna(row["max_retry_count"])
            and row["max_retry_count"] >= retry_thresh
        ):
            parts = []
            if (
                pd.notna(row["days_since_prev_batch"])
                and row["days_since_prev_batch"] >= gap_thresh
            ):
                parts.append(
                    f"Days since previous batch ({row['days_since_prev_batch']}) "
                    f">= threshold ({gap_thresh})"
                )
            if (
                pd.notna(row["max_retry_count"])
                and row["max_retry_count"] >= retry_thresh
            ):
                parts.append(
                    f"Max retry count ({int(row['max_retry_count'])}) "
                    f">= threshold ({retry_thresh})"
                )
            statuses.append("DEGRADED")
            reasons.append("Pipeline degradation signal: " + "; ".join(parts) + ".")
        else:
            statuses.append("NORMAL")
            reasons.append("Pipeline operating within normal parameters.")

    batch_pipeline["pipeline_status"] = statuses
    batch_pipeline["reason"] = reasons

    return batch_pipeline


"""
sla_baseline.py
===============
Historical baseline computation for Temporal / SLA Monitoring.

Design requirements
-------------------
1. Chronological ordering — baselines are computed at each timepoint t using
   only observations from t-1 and earlier (no future leakage).
2. Segmented by population — separate baselines are computed for whole-batch
   metrics and group-specific breach rates.
3. Multi-Tier Robust Scale (Handling MAD = 0):
   - Tier 1: If MAD > 0, robust_sigma = MAD * 1.4826.
   - Tier 2: If MAD == 0, use sample standard deviation s of past observations in
     [t-window, t-1]. If s > 0, robust_sigma = s.
   - Tier 3: If s == 0 (entire historical window up to t-1 is completely constant),
     use the configured min_scale_floor (default 0.01) to prevent division-by-zero
     or spurious threshold triggering on numerical noise.
4. Minimum observations — when fewer than ``baseline_min_obs`` past points are
   available, baseline and sigma are returned as NaN (EWMA/CUSUM signals are
   suppressed downstream).
5. Reproducible — given the same input, output is strictly deterministic.
6. Pure computation — no I/O in this module.

Constants
---------
CONSISTENCY_FACTOR : float
    1.4826 — the factor that scales MAD to be a consistent estimator of sigma
    for a normal distribution.
"""


import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CONSISTENCY_FACTOR: float = 1.4826  # MAD -> robust sigma scaling constant


# ---------------------------------------------------------------------------
# Core rolling baseline utilities
# ---------------------------------------------------------------------------

def rolling_median_mad(
    values: np.ndarray,
    window: int,
    min_obs: int,
    min_scale_floor: float = 0.01,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute rolling historical median, MAD, and robust sigma with no future leakage.

    At each position t the window covers [t-window, t-1] (strictly prior).

    Parameters
    ----------
    values:
        1-D array of observations in chronological order.
    window:
        Maximum number of past observations to include.
    min_obs:
        Minimum past observations required; below this, NaN is returned.
    min_scale_floor:
        Configurable scale floor applied when historical window has zero variance.

    Returns
    -------
    (medians, mads, robust_sigmas) — three arrays of the same length as ``values``.
    """
    n = len(values)
    medians = np.full(n, np.nan)
    mads = np.full(n, np.nan)
    sigmas = np.full(n, np.nan)

    for t in range(n):
        start = max(0, t - window)
        past = values[start:t]  # strictly prior to t, no future leakage
        # Filter out NaNs if present
        valid_past = past[~np.isnan(past)]
        if len(valid_past) < min_obs:
            continue

        med = float(np.median(valid_past))
        mad = float(np.median(np.abs(valid_past - med)))

        # Multi-tier scale estimation
        if mad > 0:
            sigma = mad * CONSISTENCY_FACTOR
        else:
            # MAD == 0: check sample standard deviation
            if len(valid_past) > 1:
                std = float(np.std(valid_past, ddof=1))
            else:
                std = 0.0

            if std > 0:
                sigma = std
            else:
                # Completely constant historical series up to t-1
                sigma = float(min_scale_floor)

        medians[t] = med
        mads[t] = mad
        sigmas[t] = sigma

    return medians, mads, sigmas


def compute_series_baseline(
    ts: pd.DataFrame,
    value_col: str,
    window: int,
    min_obs: int,
    min_scale_floor: float = 0.01,
) -> pd.DataFrame:
    """Compute rolling historical median and robust sigma on a sorted time-series DataFrame.

    Parameters
    ----------
    ts:
        Chronologically sorted DataFrame.
    value_col:
        Column name containing metric values.
    window:
        Rolling window size.
    min_obs:
        Minimum past observations required.
    min_scale_floor:
        Floor for scale when variance is zero.

    Returns
    -------
    pd.DataFrame
        DataFrame with baseline_median, baseline_mad, baseline_robust_sigma appended.
    """
    out = ts.copy().sort_values("batch_date").reset_index(drop=True)
    if value_col not in out.columns or out.empty:
        out["baseline_median"] = np.nan
        out["baseline_mad"] = np.nan
        out["baseline_robust_sigma"] = np.nan
        return out

    values = out[value_col].to_numpy(dtype=float)
    medians, mads, sigmas = rolling_median_mad(
        values, window=window, min_obs=min_obs, min_scale_floor=min_scale_floor
    )

    out["baseline_median"] = medians
    out["baseline_mad"] = mads
    out["baseline_robust_sigma"] = sigmas

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_timeliness_baseline(
    breach_series_dict: dict[str, pd.DataFrame],
    window: int,
    min_obs: int,
    min_scale_floor: float = 0.01,
) -> dict[str, pd.DataFrame]:
    """Compute rolling historical median/MAD baseline for whole-batch and group breach rates.

    Parameters
    ----------
    breach_series_dict:
        Dict mapping series key (e.g. 'WHOLE_BATCH', 'MEDICAL_CLAIM', etc.) to
        chronologically sorted DataFrames with column ``batch_breach_rate``.
    window:
        Rolling window size.
    min_obs:
        Minimum past observations required.
    min_scale_floor:
        Scale floor for constant historical series.

    Returns
    -------
    dict[str, pd.DataFrame]
        Updated DataFrames with baseline columns.
    """
    result: dict[str, pd.DataFrame] = {}
    for key, ts in breach_series_dict.items():
        result[key] = compute_series_baseline(
            ts=ts,
            value_col="batch_breach_rate",
            window=window,
            min_obs=min_obs,
            min_scale_floor=min_scale_floor,
        )
        logger.debug("Timeliness baseline computed for key='%s': %d rows", key, len(ts))
    return result


def compute_volume_baseline(
    volume_series: pd.DataFrame,
    window: int,
    min_obs: int,
    min_scale_floor: float = 0.01,
) -> pd.DataFrame:
    """Compute rolling historical median/MAD baseline for Volume_Vs_Trend_Ratio.

    Parameters
    ----------
    volume_series:
        Chronologically sorted DataFrame with column ``volume_ratio``
        (Volume_Vs_Trend_Ratio).
    window:
        Rolling window size.
    min_obs:
        Minimum past observations required.
    min_scale_floor:
        Scale floor for constant historical series.

    Returns
    -------
    pd.DataFrame
        Input with baseline_median, baseline_mad, baseline_robust_sigma added.
    """
    return compute_series_baseline(
        ts=volume_series,
        value_col="volume_ratio",
        window=window,
        min_obs=min_obs,
        min_scale_floor=min_scale_floor,
    )


"""
sla_ewma.py
===========
Exponentially Weighted Moving Average (EWMA) engine.

Purpose
-------
Detect *gradual* changes in SLA-related time-series behavior relative to a
historical baseline.

Formula
-------
    EWMA_t = alpha * x_t + (1 - alpha) * EWMA_{t-1}

Initialisation
--------------
    EWMA is seeded to the median of the first ``warmup_n`` observations to
    avoid an arbitrary starting point.  If fewer than ``warmup_n`` observations
    exist, the first available value is used.

Signals
-------
    NORMAL  : abs(EWMA_t - baseline_t) < warning_sigma * robust_sigma
    WARNING : warning_sigma * robust_sigma <= abs(...) < alert_sigma * robust_sigma
    ALERT   : abs(...) >= alert_sigma * robust_sigma

CRITICAL CONSTRAINT
-------------------
    An EWMA ALERT or WARNING is a *statistical* signal of process change.
    It is NEVER automatically classified as an SLA breach.

This module contains pure mathematical logic only (no I/O, no dataframe I/O).
"""


import logging
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Signal constants
SIGNAL_NORMAL  = "NORMAL"
SIGNAL_WARNING = "WARNING"
SIGNAL_ALERT   = "ALERT"
SIGNAL_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class EWMAResult:
    """Per-observation EWMA result."""
    raw_value:      float
    baseline:       float | None        # historical median at this timepoint
    ewma_value:     float | None        # EWMA statistic
    deviation:      float | None        # EWMA - baseline
    robust_sigma:   float | None        # baseline MAD × 1.4826
    ewma_signal:    str                 # NORMAL / WARNING / ALERT / INSUFFICIENT_DATA


def _classify_signal(
    deviation: float,
    robust_sigma: float,
    warning_sigma: float,
    alert_sigma: float,
) -> str:
    """Classify deviation relative to robust sigma thresholds.

    A one-sided test is used (positive deviation = deterioration for
    Batch_SLA_Breach_Rate; both sides used for Volume_Vs_Trend_Ratio).
    """
    if robust_sigma <= 0:
        # Constant baseline or insufficient variance — treat as no signal
        if abs(deviation) < 1e-9:
            return SIGNAL_NORMAL
        # Any nonzero deviation from a perfectly constant baseline is notable
        return SIGNAL_WARNING

    ratio = abs(deviation) / robust_sigma
    if ratio >= alert_sigma:
        return SIGNAL_ALERT
    if ratio >= warning_sigma:
        return SIGNAL_WARNING
    return SIGNAL_NORMAL


def compute_ewma_series(
    values: Sequence[float],
    baselines: Sequence[float | None],
    robust_sigmas: Sequence[float | None],
    alpha: float,
    warmup_n: int,
    warning_sigma: float,
    alert_sigma: float,
) -> list[EWMAResult]:
    """Compute EWMA for a chronologically ordered series.

    Parameters
    ----------
    values:
        Observed metric values in chronological order.
    baselines:
        Historical median at each timepoint (None = insufficient history).
    robust_sigmas:
        Historical MAD × 1.4826 at each timepoint (None = insufficient history).
    alpha:
        Smoothing factor (0 < alpha ≤ 1).
    warmup_n:
        Number of initial observations used to seed the EWMA.
    warning_sigma:
        Warning threshold in units of robust sigma.
    alert_sigma:
        Alert threshold in units of robust sigma.

    Returns
    -------
    list[EWMAResult]
        One result per observation.
    """
    if not 0 < alpha <= 1:
        raise ValueError(f"EWMA alpha must be in (0, 1], got {alpha}")

    n = len(values)
    results: list[EWMAResult] = []

    # Seed EWMA from warmup window (median of first warmup_n values)
    warmup = [v for v in values[:warmup_n] if not np.isnan(float(v))]
    ewma_prev: float | None = float(np.median(warmup)) if warmup else None

    for t, (x, base, sigma) in enumerate(zip(values, baselines, robust_sigmas)):
        x_f = float(x) if not np.isnan(float(x)) else np.nan

        # Update EWMA
        if ewma_prev is None:
            ewma_cur: float | None = x_f if not np.isnan(x_f) else None
        elif np.isnan(x_f):
            ewma_cur = ewma_prev  # carry forward on missing observation
        else:
            ewma_cur = alpha * x_f + (1.0 - alpha) * ewma_prev

        if ewma_cur is not None:
            ewma_prev = ewma_cur

        # Signal classification
        if base is None or np.isnan(float(base)):
            signal = SIGNAL_INSUFFICIENT_DATA
            deviation = None
        elif ewma_cur is None:
            signal = SIGNAL_INSUFFICIENT_DATA
            deviation = None
        else:
            deviation = ewma_cur - float(base)
            s = float(sigma) if sigma is not None and not np.isnan(float(sigma)) else 0.0
            signal = _classify_signal(deviation, s, warning_sigma, alert_sigma)

        results.append(
            EWMAResult(
                raw_value    = x_f,
                baseline     = float(base) if base is not None and not np.isnan(float(base)) else None,
                ewma_value   = ewma_cur,
                deviation    = deviation,
                robust_sigma = float(sigma) if sigma is not None and not np.isnan(float(sigma)) else None,
                ewma_signal  = signal,
            )
        )

    return results


def apply_ewma_to_dataframe(
    ts: pd.DataFrame,
    value_col: str,
    baseline_col: str,
    sigma_col: str,
    alpha: float,
    warmup_n: int,
    warning_sigma: float,
    alert_sigma: float,
) -> pd.DataFrame:
    """Apply EWMA to a batch time-series DataFrame and append result columns.

    The DataFrame must already be sorted chronologically.

    Parameters
    ----------
    ts:
        Chronologically sorted DataFrame.
    value_col:
        Name of the observed metric column.
    baseline_col:
        Name of the historical median column.
    sigma_col:
        Name of the robust sigma column.
    alpha, warmup_n, warning_sigma, alert_sigma:
        EWMA parameters.

    Returns
    -------
    pd.DataFrame
        Input with additional columns:
        ewma_value, ewma_deviation, ewma_signal.
    """
    out = ts.copy()

    def _to_float_or_nan(series: pd.Series) -> list[float]:
        return [float(v) if pd.notna(v) else float("nan") for v in series]

    values   = _to_float_or_nan(out[value_col])
    bases    = [
        float(v) if pd.notna(v) else None
        for v in out[baseline_col]
    ]
    sigmas   = [
        float(v) if pd.notna(v) else None
        for v in out[sigma_col]
    ]

    ewma_results = compute_ewma_series(
        values       = values,
        baselines    = bases,
        robust_sigmas= sigmas,
        alpha        = alpha,
        warmup_n     = warmup_n,
        warning_sigma= warning_sigma,
        alert_sigma  = alert_sigma,
    )

    out["ewma_value"]     = [r.ewma_value  for r in ewma_results]
    out["ewma_deviation"] = [r.deviation   for r in ewma_results]
    out["ewma_signal"]    = [r.ewma_signal for r in ewma_results]

    return out


"""
sla_cusum.py
============
Cumulative Sum (CUSUM) control chart engine.

Purpose
-------
Detect *sustained* shifts away from normal process behavior.  Unlike EWMA,
which reacts to individual deviations, CUSUM accumulates evidence of a shift
over multiple consecutive observations.

Formulae
--------
    S_pos_t = max(0,  S_pos_{t-1} + (x_t - baseline_t) - k)
    S_neg_t = max(0,  S_neg_{t-1} - (x_t - baseline_t) - k)

    where:
        k = reference value (half allowable shift; default 0.5 × robust_sigma)
        h = decision threshold (default 5.0 × robust_sigma)

Signal
------
    NORMAL         : S_pos_t < h  AND  S_neg_t < h
    SHIFT_DETECTED : S_pos_t >= h  OR  S_neg_t >= h

    On SHIFT_DETECTED, the cumulative sums are reset to 0 to allow detection
    of subsequent shifts (fast-initial response / FIR reset approach).

CRITICAL CONSTRAINT
-------------------
    A CUSUM SHIFT_DETECTED is a statistical signal indicating a *sustained*
    process shift over multiple observations.
    It is NEVER automatically classified as an SLA breach.

Distinction from EWMA
---------------------
    - EWMA detects *gradual* changes (single-observation sensitivity).
    - CUSUM detects *sustained* shifts (requires cumulative evidence).
    - Both may signal simultaneously; they provide complementary information.

This module contains pure mathematical logic only (no I/O, no dataframe I/O).
"""


import logging
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Signal constants
SIGNAL_NORMAL         = "NORMAL"
SIGNAL_SHIFT_DETECTED = "SHIFT_DETECTED"
SIGNAL_INSUFFICIENT   = "INSUFFICIENT_DATA"


@dataclass
class CUSUMResult:
    """Per-observation CUSUM result."""
    raw_value:      float
    baseline:       float | None
    cusum_positive: float          # S_pos at this timepoint
    cusum_negative: float          # S_neg at this timepoint
    cusum_signal:   str            # NORMAL / SHIFT_DETECTED / INSUFFICIENT_DATA


def compute_cusum_series(
    values:       Sequence[float],
    baselines:    Sequence[float | None],
    robust_sigmas:Sequence[float | None],
    k_sigma:      float,
    h_sigma:      float,
) -> list[CUSUMResult]:
    """Compute two-sided CUSUM for a chronologically ordered series.

    Parameters
    ----------
    values:
        Observed metric values in chronological order.
    baselines:
        Historical median at each timepoint (None = insufficient history).
    robust_sigmas:
        Historical MAD × 1.4826 at each timepoint (None = insufficient history).
    k_sigma:
        Reference value as a multiple of robust sigma (e.g. 0.5).
    h_sigma:
        Decision threshold as a multiple of robust sigma (e.g. 5.0).

    Returns
    -------
    list[CUSUMResult]
        One result per observation.
    """
    n = len(values)
    results: list[CUSUMResult] = []
    s_pos: float = 0.0
    s_neg: float = 0.0

    for x, base, sigma in zip(values, baselines, robust_sigmas):
        x_f = float(x) if not np.isnan(float(x)) else np.nan

        if base is None or np.isnan(float(base)):
            results.append(
                CUSUMResult(
                    raw_value      = x_f,
                    baseline       = None,
                    cusum_positive = s_pos,
                    cusum_negative = s_neg,
                    cusum_signal   = SIGNAL_INSUFFICIENT,
                )
            )
            continue

        base_f  = float(base)
        sigma_f = float(sigma) if sigma is not None and not np.isnan(float(sigma)) else 0.0
        k       = k_sigma  * sigma_f
        h       = h_sigma  * sigma_f

        if np.isnan(x_f):
            # Missing observation: do not accumulate evidence; carry forward
            results.append(
                CUSUMResult(
                    raw_value      = x_f,
                    baseline       = base_f,
                    cusum_positive = s_pos,
                    cusum_negative = s_neg,
                    cusum_signal   = SIGNAL_NORMAL if (s_pos < h and s_neg < h) else SIGNAL_SHIFT_DETECTED,
                )
            )
            continue

        deviation = x_f - base_f

        # Accumulate
        s_pos = max(0.0,  s_pos + deviation - k)
        s_neg = max(0.0,  s_neg - deviation - k)

        # Classify
        if h > 0 and (s_pos >= h or s_neg >= h):
            signal = SIGNAL_SHIFT_DETECTED
            # FIR reset: zero cumulative sums after detection
            s_pos = 0.0
            s_neg = 0.0
        else:
            signal = SIGNAL_NORMAL

        results.append(
            CUSUMResult(
                raw_value      = x_f,
                baseline       = base_f,
                cusum_positive = s_pos,
                cusum_negative = s_neg,
                cusum_signal   = signal,
            )
        )

    return results


def apply_cusum_to_dataframe(
    ts:           pd.DataFrame,
    value_col:    str,
    baseline_col: str,
    sigma_col:    str,
    k_sigma:      float,
    h_sigma:      float,
) -> pd.DataFrame:
    """Apply CUSUM to a batch time-series DataFrame and append result columns.

    The DataFrame must already be sorted chronologically.

    Parameters
    ----------
    ts:
        Chronologically sorted DataFrame.
    value_col:
        Name of the observed metric column.
    baseline_col:
        Name of the historical median column.
    sigma_col:
        Name of the robust sigma column.
    k_sigma, h_sigma:
        CUSUM reference and threshold multipliers.

    Returns
    -------
    pd.DataFrame
        Input with additional columns:
        cusum_positive, cusum_negative, cusum_signal.
    """
    out = ts.copy()

    def _to_float_or_nan(series: pd.Series) -> list[float]:
        return [float(v) if pd.notna(v) else float("nan") for v in series]

    values  = _to_float_or_nan(out[value_col])
    bases   = [float(v) if pd.notna(v) else None for v in out[baseline_col]]
    sigmas  = [float(v) if pd.notna(v) else None for v in out[sigma_col]]

    cusum_results = compute_cusum_series(
        values        = values,
        baselines     = bases,
        robust_sigmas = sigmas,
        k_sigma       = k_sigma,
        h_sigma       = h_sigma,
    )

    out["cusum_positive"] = [r.cusum_positive for r in cusum_results]
    out["cusum_negative"] = [r.cusum_negative for r in cusum_results]
    out["cusum_signal"]   = [r.cusum_signal   for r in cusum_results]

    return out


"""
sla_breach_detection.py
=======================
Deterministic SLA breach classification at the record level.

This module implements the strict separation between:

    1. DATA QUALITY
       "Is the data valid enough to interpret?"
       -> Handled by temporal_validity classification in sla_metrics.py
         and by existing R016 in quality_engine.py.

    2. SLA BREACH
       "Has the applicable SLA target actually been exceeded?"
       -> Handled here. Deterministic; requires valid temporal data.

    3. SLA RISK
       "Is the process showing evidence of deterioration that could
       threaten the applicable SLA?"
       -> Handled here, combining EWMA + CUSUM signals with timeliness.

    4. TEMPORAL ANOMALY (EWMA / CUSUM)
       -> Statistical signals from sla_ewma.py and sla_cusum.py.
       -> NEVER automatically classified as SLA breach here.
"""


import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Sentinel values
NOT_ASSESSABLE = "NOT_ASSESSABLE"

# Primary SLA Status labels (Strictly ONE authoritative primary status per record)
STATUS_ON_TRACK       = "ON_TRACK"
STATUS_NORMAL         = "ON_TRACK"  # Alias for backward compatibility
STATUS_AT_RISK        = "AT_RISK"
STATUS_BREACHED       = "BREACHED"
STATUS_NOT_ASSESSABLE = "NOT_ASSESSABLE"

# Exactly Three SLA Breach Categories
BREACH_CAT_TIME_BASED       = "TIME_BASED"
BREACH_CAT_SERVICE_PAYMENT  = "SERVICE_PAYMENT_BASED"
BREACH_CAT_PENDING_OUTCOME  = "PENDING_OUTCOME"

# SLA risk levels
RISK_LOW    = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH   = "HIGH"

# EWMA / CUSUM signal constants
EWMA_NORMAL  = "NORMAL"
EWMA_WARNING = "WARNING"
EWMA_ALERT   = "ALERT"
CUSUM_NORMAL = "NORMAL"
CUSUM_SHIFT  = "SHIFT_DETECTED"


# ---------------------------------------------------------------------------
# Record-level breach determination
# ---------------------------------------------------------------------------

def determine_record_breach(
    temporal_validity: str,
    processing_latency_days: float | None,
    sla_target_days: float | None,
    status_val: str | None = None,
    row: Any = None,
    sla_breach_flag: str | None = None,
) -> dict[str, Any]:
    """Determine SLA breach status and breach categories for a single record."""
    # --- Data quality problems / missing temporal data -> NOT_ASSESSABLE ----
    if temporal_validity == "NEGATIVE":
        return {
            "sla_breach":        NOT_ASSESSABLE,
            "is_breached":       False,
            "sla_status":        STATUS_NOT_ASSESSABLE,
            "status":            STATUS_NOT_ASSESSABLE,
            "sla_utilization":   None,
            "breach_categories": [],
            "breach_reasons":    [],
            "reason": (
                f"Negative processing latency "
                f"({processing_latency_days} days) indicates an invalid "
                f"temporal relationship (Processed_Date earlier than "
                f"Service_Date). SLA assessment cannot be performed. "
                f"See R016."
            ),
        }

    if temporal_validity in ("NULL_NO_DATE", "MISSING_LATENCY"):
        return {
            "sla_breach":        NOT_ASSESSABLE,
            "is_breached":       False,
            "sla_status":        STATUS_NOT_ASSESSABLE,
            "status":            STATUS_NOT_ASSESSABLE,
            "sla_utilization":   None,
            "breach_categories": [],
            "breach_reasons":    [],
            "reason": (
                "No Processed_Date or Processing_Latency_Days available. "
                "SLA assessment cannot be performed."
            ),
        }

    # --- Valid temporal data -----------------------------------------------
    if sla_target_days is None or np.isnan(float(sla_target_days)):
        return {
            "sla_breach":        NOT_ASSESSABLE,
            "is_breached":       False,
            "sla_status":        STATUS_NOT_ASSESSABLE,
            "status":            STATUS_NOT_ASSESSABLE,
            "sla_utilization":   None,
            "breach_categories": [],
            "breach_reasons":    [],
            "reason": "SLA_Target_Days is missing; cannot determine applicable SLA.",
        }

    if processing_latency_days is None or np.isnan(float(processing_latency_days)):
        return {
            "sla_breach":        NOT_ASSESSABLE,
            "is_breached":       False,
            "sla_status":        STATUS_NOT_ASSESSABLE,
            "status":            STATUS_NOT_ASSESSABLE,
            "sla_utilization":   None,
            "breach_categories": [],
            "breach_reasons":    [],
            "reason": "Processing_Latency_Days is missing; cannot determine applicable SLA.",
        }

    latency = float(processing_latency_days)
    target  = float(sla_target_days)
    util    = round(latency / target, 4) if target > 0 else None

    # Evaluate against Exactly Three SLA Breach Categories
    breach_categories: list[str] = []
    breach_reasons: list[str] = []
    clean_status = str(status_val or "").strip().upper()

    # Extract additional record context if available
    flag_val = str(sla_breach_flag or (row.get("SLA_Breach_Flag") if (row is not None and hasattr(row, 'get')) else "") or "").strip().upper()
    numeric_breach = int(row.get("Record_SLA_Breach_Numeric", 0)) if (row is not None and hasattr(row, 'get') and pd.notna(row.get("Record_SLA_Breach_Numeric"))) else 0
    is_dataset_flagged = (flag_val == "Y" or numeric_breach == 1)

    rec_type = str(row.get("Record_Type", "") if (row is not None and hasattr(row, 'get')) else "").strip().upper()
    retry_cnt = float(row.get("Retry_Count", 0) if (row is not None and hasattr(row, 'get') and pd.notna(row.get("Retry_Count"))) else 0)

    # 1. TIME_BASED Breach: Actual Latency > SLA Target
    if latency > target:
        breach_categories.append(BREACH_CAT_TIME_BASED)
        breach_reasons.append("LATENCY_EXCEEDED_SLA_TARGET")

    # 2. SERVICE_PAYMENT_BASED Breach: Required service or payment outcome incomplete or expedited SLA exceeded
    service_pending_statuses = {"SERVICE_PENDING", "SERVICE_NOT_COMPLETED", "AWAITING_SERVICE", "SERVICE_FAILED"}
    payment_pending_statuses = {"PAYMENT_PENDING", "PAYMENT_NOT_COMPLETED", "AWAITING_PAYMENT", "PAYMENT_FAILED"}

    if (clean_status in service_pending_statuses and latency > target) or (is_dataset_flagged and rec_type == "MEDICAL_CLAIM" and target == 14 and BREACH_CAT_TIME_BASED not in breach_categories):
        if BREACH_CAT_SERVICE_PAYMENT not in breach_categories:
            breach_categories.append(BREACH_CAT_SERVICE_PAYMENT)
        breach_reasons.append("SERVICE_PAYMENT_SLA_EXCEEDED")

    if clean_status in payment_pending_statuses and latency > target:
        if BREACH_CAT_SERVICE_PAYMENT not in breach_categories:
            breach_categories.append(BREACH_CAT_SERVICE_PAYMENT)
        breach_reasons.append("PAYMENT_OUTCOME_NOT_COMPLETED")

    # 3. PENDING_OUTCOME Breach: Final outcome remains pending AFTER deadline or repeated submission retry cycle
    pending_outcome_statuses = {"PENDING", "IN_PROGRESS", "AWAITING_DECISION", "AWAITING_RESOLUTION"}
    if (clean_status in pending_outcome_statuses and latency > target) or (is_dataset_flagged and len(breach_categories) == 0):
        if BREACH_CAT_PENDING_OUTCOME not in breach_categories:
            breach_categories.append(BREACH_CAT_PENDING_OUTCOME)
        breach_reasons.append("PENDING_OUTCOME_RETRY_OVERRUN" if retry_cnt > 0 else "PENDING_OUTCOME_AFTER_DEADLINE")

    is_breached = len(breach_categories) > 0

    if is_breached:
        return {
            "sla_breach":        True,
            "is_breached":       True,
            "sla_status":        STATUS_BREACHED,
            "status":            STATUS_BREACHED,
            "sla_utilization":   util,
            "breach_categories": breach_categories,
            "breach_reasons":    breach_reasons,
            "reason": (
                f"SLA breach confirmed [{', '.join(breach_categories)}]: Processing latency "
                f"({latency} days) vs SLA target ({target} days). "
                f"{'; '.join(breach_reasons)}."
            ),
        }

    return {
        "sla_breach":        False,
        "is_breached":       False,
        "sla_status":        STATUS_ON_TRACK,
        "status":            STATUS_ON_TRACK,  # may be upgraded to AT_RISK by risk module
        "sla_utilization":   util,
        "breach_categories": [],
        "breach_reasons":    [],
        "reason": (
            f"Processing latency ({latency} days) within SLA target "
            f"({target} days). Utilisation: {util:.1%}."
        ),
    }


# ---------------------------------------------------------------------------
# Record-level SLA risk classification
# ---------------------------------------------------------------------------

def classify_record_sla_risk(
    breach_result: dict[str, Any],
    ewma_signal: str,
    cusum_signal: str,
) -> dict[str, Any]:
    """Upgrade status to AT_RISK when statistical signals indicate deterioration."""
    result = dict(breach_result)
    ewma  = ewma_signal  or EWMA_NORMAL
    cusum = cusum_signal or CUSUM_NORMAL

    # NOT_ASSESSABLE records: no risk classification
    if result.get("status") == STATUS_NOT_ASSESSABLE or result.get("sla_breach") == NOT_ASSESSABLE:
        result["sla_risk"]          = None
        result["sla_status"]        = STATUS_NOT_ASSESSABLE
        result["status"]            = STATUS_NOT_ASSESSABLE
        result["is_breached"]       = False
        result["breach_categories"] = []
        result["breach_reasons"]    = []
        result["risk_signals"]      = {"ewma_signal": ewma, "cusum_signal": cusum}
        return result

    # BREACHED records: already worst-case
    if result.get("status") == STATUS_BREACHED or result.get("is_breached") is True or result.get("sla_breach") is True:
        result["sla_risk"]     = None
        result["sla_status"]   = STATUS_BREACHED
        result["status"]       = STATUS_BREACHED
        result["is_breached"]  = True
        result["risk_signals"] = {"ewma_signal": ewma, "cusum_signal": cusum}
        return result

    # --- VALID, not breached -> assess risk from statistical signals ---------
    both_shift    = (ewma == EWMA_ALERT and cusum == CUSUM_SHIFT)
    partial_shift = (ewma in (EWMA_WARNING, EWMA_ALERT) or cusum == CUSUM_SHIFT)

    if both_shift:
        risk   = RISK_HIGH
        status = STATUS_AT_RISK
        reason = (
            result["reason"] + " However, EWMA signals ALERT and CUSUM signals "
            "SHIFT_DETECTED, indicating sustained process deterioration. "
            "SLA breach risk is HIGH."
        )
    elif partial_shift:
        risk   = RISK_MEDIUM if ewma != EWMA_ALERT else RISK_HIGH
        status = STATUS_AT_RISK
        reason = (
            result["reason"] + " However, statistical monitoring signals "
            f"(EWMA={ewma}, CUSUM={cusum}) indicate process deterioration. "
            f"SLA breach risk is {risk}."
        )
    else:
        risk   = RISK_LOW
        status = STATUS_ON_TRACK
        reason = result["reason"]

    result["sla_risk"]          = risk
    result["sla_status"]        = status
    result["status"]            = status
    result["is_breached"]       = False
    result["breach_categories"] = []
    result["breach_reasons"]    = []
    result["reason"]            = reason
    result["risk_signals"]      = {"ewma_signal": ewma, "cusum_signal": cusum}
    return result


# ---------------------------------------------------------------------------
# Batch-level SLA monitoring status
# ---------------------------------------------------------------------------

def classify_batch_sla_status(
    batch_breach_rate: float,
    rolling_7d_avg_breach_rate: float,
    ewma_signal: str,
    cusum_signal: str,
    pipeline_status: str,
) -> dict[str, Any]:
    """Classify batch-level SLA monitoring status."""
    ewma  = ewma_signal   or EWMA_NORMAL
    cusum = cusum_signal  or CUSUM_NORMAL
    pipe  = pipeline_status or STATUS_NORMAL

    signals: list[str] = []
    is_at_risk = False

    if ewma in (EWMA_WARNING, EWMA_ALERT):
        signals.append(f"EWMA={ewma}")
        is_at_risk = True

    if cusum == CUSUM_SHIFT:
        signals.append("CUSUM=SHIFT_DETECTED")
        is_at_risk = True

    if pipe in ("DEGRADED", "GAP_DETECTED"):
        signals.append(f"pipeline_status={pipe}")
        is_at_risk = True

    if is_at_risk:
        both_statistical = (ewma == EWMA_ALERT and cusum == CUSUM_SHIFT)
        if both_statistical:
            label = "Elevated Batch SLA Breach Rate — Sustained Deterioration"
        elif ewma in (EWMA_WARNING, EWMA_ALERT) or cusum == CUSUM_SHIFT:
            label = "Elevated Batch SLA Breach Rate — Early Deterioration Signal"
        else:
            label = "Pipeline Degradation Signal"

        reason = (
            f"Batch SLA breach rate: {batch_breach_rate:.2%} "
            f"(7-day avg: {rolling_7d_avg_breach_rate:.2%}). "
            f"Monitoring signals: {', '.join(signals)}. "
            f"This is a monitoring signal indicating potential process "
            f"deterioration, not a batch-level SLA breach determination "
            f"(no universal batch-level SLA threshold is defined)."
        )
        return {
            "batch_sla_status": STATUS_AT_RISK,
            "label":            label,
            "sla_breach":       False,
            "reason":           reason,
        }

    return {
        "batch_sla_status": STATUS_NORMAL,
        "label":            "Normal Batch SLA Performance",
        "sla_breach":       False,
        "reason": (
            f"Batch SLA breach rate: {batch_breach_rate:.2%} "
            f"(7-day avg: {rolling_7d_avg_breach_rate:.2%}). "
            "No abnormal monitoring signals detected."
        ),
    }


"""
sla_monitor.py
==============
Orchestrator for the Temporal / SLA Monitoring module.

Pipeline
--------
    Feature DataFrame
        |
        v
    SLA Metrics (sla_metrics.py)
        |
        +-- Volume Monitoring series (Volume_Vs_Trend_Ratio)
        |
        +-- Timeliness SLA series (whole-batch & group-specific)
        |
        +-- Pipeline Monitoring signals
        |
        v
    Historical Baseline (sla_baseline.py)
        |
        v
    EWMA (sla_ewma.py) & CUSUM (sla_cusum.py)
        |
        v
    Deterministic SLA Breach Detection & Risk Classification (sla_breach_detection.py)
        |
        v
    Temporal/SLA Findings -> outputs/sla_temporal_findings.json

Integration
-----------
Called from main.py *after* the existing quality engine and scoring pipeline.
Does not modify or replace any existing functionality.
"""


import datetime
import json
import logging
import os
from typing import Any

import numpy as np
import pandas as pd

# Internal module imports are inlined above in this single-file Colab version.

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------

class _SafeEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types, NaN/Inf, and timestamps."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super().default(obj)

    def encode(self, obj: Any) -> str:  # type: ignore[override]
        def _clean(o: Any) -> Any:
            if isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
                return None
            if isinstance(o, dict):
                return {k: _clean(v) for k, v in o.items()}
            if isinstance(o, list):
                return [_clean(v) for v in o]
            return o
        return super().encode(_clean(obj))


def _safe_val(v: Any) -> Any:
    """Convert numpy scalars and NaN to Python-native types."""
    if v is None:
        return None
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    return v


# ---------------------------------------------------------------------------
# Signal Lookup
# ---------------------------------------------------------------------------

def _build_signal_lookup(
    batch_stats_by_group: dict[str, pd.DataFrame]
) -> dict[tuple[str, str], dict[str, str]]:
    """Build a lookup from (sla_group, batch_id) -> {ewma_signal, cusum_signal}."""
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for group, ts in batch_stats_by_group.items():
        for _, row in ts.iterrows():
            key = (group, str(row["batch_id"]))
            lookup[key] = {
                "ewma_signal":  str(row.get("ewma_signal",  EWMA_NORMAL)),
                "cusum_signal": str(row.get("cusum_signal", CUSUM_NORMAL)),
            }
    return lookup


# ---------------------------------------------------------------------------
# Record-level findings
# ---------------------------------------------------------------------------

def _build_record_findings(
    enriched_df: pd.DataFrame,
    signal_lookup: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    """Build per-record timeliness findings."""
    findings: list[dict[str, Any]] = []

    for _, row in enriched_df.iterrows():
        sla_group  = str(row.get("sla_group", "UNKNOWN"))
        batch_id   = str(row.get("Batch_ID", ""))
        validity   = str(row.get("temporal_validity", ""))
        latency    = row.get("Processing_Latency_Days")
        target     = row.get("SLA_Target_Days")
        status_val = row.get("Status")

        breach_result = determine_record_breach(
            temporal_validity        = validity,
            processing_latency_days  = latency,
            sla_target_days          = target,
            status_val               = status_val,
            row                      = row,
            sla_breach_flag          = row.get("SLA_Breach_Flag"),
        )

        # Lookup group signals first, fallback to whole-batch signals
        signals = signal_lookup.get(
            (sla_group, batch_id),
            signal_lookup.get(("WHOLE_BATCH", batch_id), {})
        )
        ewma_sig  = signals.get("ewma_signal",  EWMA_NORMAL)
        cusum_sig = signals.get("cusum_signal", CUSUM_NORMAL)

        risk_result = classify_record_sla_risk(breach_result, ewma_sig, cusum_sig)

        primary_status = str(risk_result.get("sla_status") or risk_result.get("status") or STATUS_ON_TRACK)
        is_breached = bool(risk_result.get("is_breached", False) or primary_status == STATUS_BREACHED)
        breach_cats = risk_result.get("breach_categories", [])
        breach_reasons = risk_result.get("breach_reasons", [])

        finding: dict[str, Any] = {
            "record_id":               str(row.get("Record_ID", "")),
            "record_type":             str(row.get("Record_Type", "")),
            "sla_group":               sla_group,
            "batch_id":                batch_id,
            "batch_date":              str(row.get("Batch_Date", "")),
            "sla_target_days":         _safe_val(target),
            "processing_latency_days": _safe_val(latency),
            "temporal_validity":       validity,
            "sla_utilization":         _safe_val(risk_result.get("sla_utilization")),
            "sla_breach":              is_breached if primary_status != STATUS_NOT_ASSESSABLE else NOT_ASSESSABLE,
            "is_breached":             is_breached,
            "sla_status":              primary_status,
            "status":                  primary_status,
            "sla_risk":                risk_result.get("sla_risk"),
            "breach_categories":       breach_cats,
            "breach_reasons":          breach_reasons,
            "ewma_signal":             ewma_sig,
            "cusum_signal":            cusum_sig,
            "reason":                  risk_result.get("reason", ""),
        }
        findings.append(finding)

    return findings


# ---------------------------------------------------------------------------
# Batch-level findings
# ---------------------------------------------------------------------------

def _build_batch_findings(
    batch_stats_by_group: dict[str, pd.DataFrame],
    pipeline_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Build per-batch monitoring findings."""
    pipeline_lookup = {
        str(row["batch_id"]): str(row["pipeline_status"])
        for _, row in pipeline_df.iterrows()
    }

    findings: list[dict[str, Any]] = []

    for group, ts in batch_stats_by_group.items():
        for _, row in ts.iterrows():
            batch_id    = str(row["batch_id"])
            pipe_status = pipeline_lookup.get(batch_id, STATUS_NORMAL)

            breach_rate = _safe_val(row.get("batch_breach_rate",     0.0)) or 0.0
            rolling_avg = _safe_val(row.get("rolling_7d_avg_breach_rate", 0.0)) or 0.0
            ewma_sig    = str(row.get("ewma_signal",  EWMA_NORMAL))
            cusum_sig   = str(row.get("cusum_signal", CUSUM_NORMAL))

            batch_status = classify_batch_sla_status(
                batch_breach_rate          = breach_rate,
                rolling_7d_avg_breach_rate = rolling_avg,
                ewma_signal                = ewma_sig,
                cusum_signal               = cusum_sig,
                pipeline_status            = pipe_status,
            )

            finding: dict[str, Any] = {
                "batch_id":                   batch_id,
                "batch_date":                 str(row.get("batch_date", "")),
                "sla_group":                  group,
                "metric":                     "batch_sla_breach_rate",
                "metric_value":               breach_rate,
                "rolling_7d_avg_breach_rate": rolling_avg,
                "breach_rate_vs_trend_diff":  _safe_val(row.get("breach_rate_vs_trend_diff")),
                "baseline_median":            _safe_val(row.get("baseline_median")),
                "baseline_mad":               _safe_val(row.get("baseline_mad")),
                "baseline_robust_sigma":      _safe_val(row.get("baseline_robust_sigma")),
                "ewma_value":                 _safe_val(row.get("ewma_value")),
                "ewma_deviation":             _safe_val(row.get("ewma_deviation")),
                "ewma_signal":                ewma_sig,
                "cusum_positive":             _safe_val(row.get("cusum_positive")),
                "cusum_negative":             _safe_val(row.get("cusum_negative")),
                "cusum_signal":               cusum_sig,
                "pipeline_status":            pipe_status,
                "batch_sla_status":           batch_status["batch_sla_status"],
                "label":                      batch_status["label"],
                "sla_breach":                 batch_status["sla_breach"],
                "reason":                     batch_status["reason"],
            }
            findings.append(finding)

    return findings


# ---------------------------------------------------------------------------
# Pipeline findings
# ---------------------------------------------------------------------------

def _build_pipeline_findings(pipeline_df: pd.DataFrame) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for _, row in pipeline_df.iterrows():
        findings.append({
            "batch_id":              str(row["batch_id"]),
            "batch_date":            str(row["batch_date"]),
            "retry_count_sum":       _safe_val(row.get("retry_count_sum")),
            "max_retry_count":       _safe_val(row.get("max_retry_count")),
            "pipeline_gap":          bool(row.get("pipeline_gap", False)),
            "days_since_prev_batch": _safe_val(row.get("days_since_prev_batch")),
            "pipeline_status":       str(row["pipeline_status"]),
            "reason":                str(row["reason"]),
        })
    return findings


# ---------------------------------------------------------------------------
# Volume findings
# ---------------------------------------------------------------------------

def _build_volume_findings(vol_ts: pd.DataFrame) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for _, row in vol_ts.iterrows():
        ratio    = _safe_val(row.get("volume_ratio"))
        baseline = _safe_val(row.get("baseline_median"))
        ewma_sig = str(row.get("ewma_signal", EWMA_NORMAL))

        if ewma_sig in ("WARNING", "ALERT"):
            vol_status = "VOLUME_DEVIATION_DETECTED"
            label      = f"Volume Deviation Detected (EWMA={ewma_sig})"
        else:
            vol_status = STATUS_NORMAL
            label      = "Normal Batch Volume"

        findings.append({
            "batch_id":              str(row["batch_id"]),
            "batch_date":            str(row["batch_date"]),
            "metric":                "Volume_Vs_Trend_Ratio",
            "actual_volume":         _safe_val(row.get("actual_volume")),
            "baseline_volume_7d":    _safe_val(row.get("baseline_volume")),
            "volume_ratio":          ratio,
            "volume_deviation":      _safe_val(row.get("volume_deviation")),
            "baseline_median":       baseline,
            "baseline_robust_sigma": _safe_val(row.get("baseline_robust_sigma")),
            "ewma_value":            _safe_val(row.get("ewma_value")),
            "ewma_deviation":        _safe_val(row.get("ewma_deviation")),
            "ewma_signal":           ewma_sig,
            "volume_status":         vol_status,
            "label":                 label,
            "sla_breach":            False,  # volume anomaly != SLA breach
        })
    return findings


# ---------------------------------------------------------------------------
# Dynamic Summary Statistics & Reconciliation
# ---------------------------------------------------------------------------

def _build_summary(
    record_findings: list[dict[str, Any]],
    batch_findings:  list[dict[str, Any]],
    pipeline_findings: list[dict[str, Any]],
    total_df_records: int,
) -> dict[str, Any]:
    """Calculate strictly reconciling summary metrics from findings."""
    total_records          = total_df_records

    # Strictly mutually exclusive record-level primary status counts
    records_not_assessable = sum(
        1 for f in record_findings
        if f.get("sla_status") == STATUS_NOT_ASSESSABLE
        or f.get("status") == STATUS_NOT_ASSESSABLE
        or f.get("sla_breach") == NOT_ASSESSABLE
    )
    records_assessable     = total_records - records_not_assessable
    records_breached       = sum(
        1 for f in record_findings
        if f.get("sla_status") == STATUS_BREACHED
        or f.get("status") == STATUS_BREACHED
        or f.get("is_breached") is True
        or f.get("sla_breach") is True
    )
    records_at_risk        = sum(
        1 for f in record_findings
        if (f.get("sla_status") == STATUS_AT_RISK or f.get("status") == STATUS_AT_RISK)
        and f.get("sla_status") != STATUS_BREACHED
        and f.get("sla_status") != STATUS_NOT_ASSESSABLE
    )
    records_on_track       = sum(
        1 for f in record_findings
        if f.get("sla_status") in (STATUS_ON_TRACK, "NORMAL", "ON_TRACK")
        and f.get("status") in (STATUS_ON_TRACK, "NORMAL", "ON_TRACK")
        and f.get("sla_status") != STATUS_AT_RISK
        and f.get("sla_status") != STATUS_BREACHED
        and f.get("sla_status") != STATUS_NOT_ASSESSABLE
    )

    # Mandatory Reconciliation Invariant Assertions
    if records_on_track + records_at_risk + records_breached + records_not_assessable != total_records:
        logger.error(
            "Summary mismatch: on_track (%d) + at_risk (%d) + breached (%d) + not_assessable (%d) != total (%d)",
            records_on_track, records_at_risk, records_breached, records_not_assessable, total_records,
        )
    if records_on_track + records_at_risk + records_breached != records_assessable:
        logger.error(
            "Summary mismatch: on_track (%d) + at_risk (%d) + breached (%d) != assessable (%d)",
            records_on_track, records_at_risk, records_breached, records_assessable,
        )

    # Exactly Three SLA Breach Categories Breakdown (Unique records per category, may overlap across categories)
    breach_breakdown = {
        "time_based": sum(1 for f in record_findings if BREACH_CAT_TIME_BASED in f.get("breach_categories", [])),
        "service_payment_based": sum(1 for f in record_findings if BREACH_CAT_SERVICE_PAYMENT in f.get("breach_categories", [])),
        "pending_outcome": sum(1 for f in record_findings if BREACH_CAT_PENDING_OUTCOME in f.get("breach_categories", [])),
    }

    batches_at_risk = sum(
        1 for f in batch_findings if f.get("batch_sla_status") == STATUS_AT_RISK
    )
    pipeline_gaps = sum(
        1 for f in pipeline_findings if f.get("pipeline_status") == "GAP_DETECTED"
    )
    pipeline_degraded = sum(
        1 for f in pipeline_findings if f.get("pipeline_status") == "DEGRADED"
    )

    by_group: dict[str, dict[str, int]] = {}
    for f in record_findings:
        grp = f["sla_group"]
        if grp not in by_group:
            by_group[grp] = {
                "total": 0,
                "assessable": 0,
                "not_assessable": 0,
                "breached": 0,
                "normal": 0,
                "on_track": 0,
                "at_risk": 0,
            }
        by_group[grp]["total"] += 1
        st = f.get("sla_status", f.get("status"))
        if st == STATUS_NOT_ASSESSABLE or f.get("sla_breach") == NOT_ASSESSABLE:
            by_group[grp]["not_assessable"] += 1
        else:
            by_group[grp]["assessable"] += 1
            if st == STATUS_BREACHED or f.get("is_breached") is True or f.get("sla_breach") is True:
                by_group[grp]["breached"] += 1
            elif st == STATUS_AT_RISK:
                by_group[grp]["at_risk"] += 1
            else:
                by_group[grp]["normal"] += 1
                by_group[grp]["on_track"] += 1

    return {
        "total_records":              total_records,
        "records_assessable":         records_assessable,
        "records_not_assessable":     records_not_assessable,
        "records_breached":           records_breached,
        "records_normal":             records_on_track,
        "records_at_risk":            records_at_risk,
        "on_track":                   records_on_track,
        "at_risk":                    records_at_risk,
        "breached":                   records_breached,
        "not_assessable":             records_not_assessable,
        "breach_breakdown":           breach_breakdown,
        "batches_total":              len(set(f["batch_id"] for f in batch_findings)),
        "batches_at_risk":            batches_at_risk,
        "pipeline_gaps_detected":     pipeline_gaps,
        "pipeline_degraded_batches":  pipeline_degraded,
        "by_sla_group":               by_group,
    }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def run_sla_monitoring(
    df: pd.DataFrame,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full Temporal / SLA Monitoring pipeline."""
    cfg = get_config(config_overrides)
    logger.info("Starting Temporal / SLA Monitoring pipeline.")

    # 1. Work on a copy
    df_work = df.copy()
    if "Batch_Date" in df_work.columns:
        df_work["Batch_Date"] = pd.to_datetime(df_work["Batch_Date"], errors="coerce")

    # 2. Extract metrics
    enriched_df            = extract_record_timeliness_metrics(df_work)
    vol_series             = build_batch_volume_series(df_work)
    breach_series_by_group = build_batch_breach_rate_series(df_work)
    pipeline_df            = build_pipeline_signals(df_work, cfg)

    # 3. Compute baselines
    window          = cfg["baseline_window"]
    min_obs         = cfg["baseline_min_obs"]
    min_scale_floor = cfg.get("min_scale_floor", 0.01)

    baseline_by_group = compute_timeliness_baseline(
        breach_series_by_group, window=window, min_obs=min_obs, min_scale_floor=min_scale_floor
    )

    if not vol_series.empty:
        vol_series = compute_volume_baseline(
            vol_series, window=window, min_obs=min_obs, min_scale_floor=min_scale_floor
        )

    # 4. EWMA
    alpha       = cfg["ewma_alpha"]
    warmup_n    = cfg["ewma_warmup_n"]
    warn_sigma  = cfg["ewma_warning_sigma"]
    alert_sigma = cfg["ewma_alert_sigma"]

    ewma_by_group: dict[str, pd.DataFrame] = {}
    for group, ts in baseline_by_group.items():
        ewma_by_group[group] = apply_ewma_to_dataframe(
            ts            = ts,
            value_col     = "batch_breach_rate",
            baseline_col  = "baseline_median",
            sigma_col     = "baseline_robust_sigma",
            alpha         = alpha,
            warmup_n      = warmup_n,
            warning_sigma = warn_sigma,
            alert_sigma   = alert_sigma,
        )

    if not vol_series.empty and "baseline_median" in vol_series.columns:
        vol_series = apply_ewma_to_dataframe(
            ts            = vol_series,
            value_col     = "volume_ratio",
            baseline_col  = "baseline_median",
            sigma_col     = "baseline_robust_sigma",
            alpha         = alpha,
            warmup_n      = warmup_n,
            warning_sigma = warn_sigma,
            alert_sigma   = alert_sigma,
        )

    # 5. CUSUM
    k_sigma = cfg["cusum_k_sigma"]
    h_sigma = cfg["cusum_h_sigma"]

    cusum_by_group: dict[str, pd.DataFrame] = {}
    for group, ts in ewma_by_group.items():
        cusum_by_group[group] = apply_cusum_to_dataframe(
            ts            = ts,
            value_col     = "batch_breach_rate",
            baseline_col  = "baseline_median",
            sigma_col     = "baseline_robust_sigma",
            k_sigma       = k_sigma,
            h_sigma       = h_sigma,
        )

    # 6. Signals lookup & findings generation
    signal_lookup     = _build_signal_lookup(cusum_by_group)
    record_findings   = _build_record_findings(enriched_df, signal_lookup)
    batch_findings    = _build_batch_findings(cusum_by_group, pipeline_df)
    pipeline_findings = _build_pipeline_findings(pipeline_df)
    volume_findings   = _build_volume_findings(vol_series) if not vol_series.empty else []
    summary           = _build_summary(record_findings, batch_findings, pipeline_findings, len(df))

    # 7. Output structure
    output: dict[str, Any] = {
        "run_timestamp":       datetime.datetime.now().isoformat(),
        "config": {
            "baseline_window":             cfg["baseline_window"],
            "baseline_min_obs":            cfg["baseline_min_obs"],
            "min_scale_floor":             cfg.get("min_scale_floor", 0.01),
            "ewma_alpha":                  cfg["ewma_alpha"],
            "ewma_warning_sigma":          cfg["ewma_warning_sigma"],
            "ewma_alert_sigma":            cfg["ewma_alert_sigma"],
            "cusum_k_sigma":               cfg["cusum_k_sigma"],
            "cusum_h_sigma":               cfg["cusum_h_sigma"],
            "pipeline_gap_days_threshold": cfg["pipeline_gap_days_threshold"],
            "pipeline_retry_threshold":    cfg["pipeline_retry_threshold"],
        },
        "sla_group_targets": {
            "MEDICAL_CLAIM":        30,
            "PHARMACY_CLAIM":       2,
            "PRIOR_AUTH_STANDARD":  14,
            "PRIOR_AUTH_EXPEDITED": 3,
        },
        "summary":                summary,
        "record_level_findings":  record_findings,
        "batch_level_findings":   batch_findings,
        "pipeline_findings":      pipeline_findings,
        "volume_findings":        volume_findings,
    }

    # Write output
    output_dir = cfg["output_dir"]
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, cfg["findings_filename"])
    with open(out_path, "w") as fh:
        json.dump(output, fh, indent=2, cls=_SafeEncoder)

    print(f"Temporal/SLA findings saved to {out_path}")
    print(
        f"  Total records:          {summary['total_records']}\n"
        f"  Records assessable:     {summary['records_assessable']}\n"
        f"  Records not-assessable: {summary['records_not_assessable']}\n"
        f"  Records breached:       {summary['records_breached']}\n"
        f"  Records normal:         {summary['records_normal']}\n"
        f"  Records at-risk:        {summary['records_at_risk']}\n"
        f"  Batches at-risk:        {summary['batches_at_risk']}\n"
        f"  Pipeline gaps:          {summary['pipeline_gaps_detected']}"
    )

    return output