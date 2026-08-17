# File: app/data_utils.py
"""
ONC CSV ingestion with:
  - Full header metadata extraction (all #KEY: value fields)
  - QC-aware filtering (drops flags 3, 4; annotates 2, 6, 8)
  - Daily chunking with statistical summaries (mean, min, max, std, trend)
  - Anomaly detection via z-score
  - Multi-parameter linking for same-device/same-timespan files
"""

import os
import re
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# QC flag semantics (ONC standard)
# ---------------------------------------------------------------------------
QC_LABELS = {
    0: "no QC applied",
    1: "good",
    2: "probably good (use with caution)",
    3: "probably bad",        # treat as bad → exclude
    4: "bad",                 # exclude
    6: "bad down-sampling",   # exclude
    7: "averaged",
    8: "interpolated (use with caution)",
    9: "missing",             # NaN anyway
}
BAD_FLAGS = {3, 4, 6, 9}
CAUTION_FLAGS = {2, 8}


# ---------------------------------------------------------------------------
# Header / metadata extraction
# ---------------------------------------------------------------------------

# Maps raw header keys (lowercased, stripped) → clean field names
_HEADER_KEY_MAP = {
    "stnname":  "station_name",
    "stncode":  "station_code",
    "latitude": "latitude",
    "longitude": "longitude",
    "depth":    "depth_m",
    "devcat":   "device_category",
    "devname":  "device_name",
    "devcode":  "device_code",
    "devid":    "device_id",
    "datefrom": "data_start",
    "dateto":   "data_end",
    "resampprd":"resample_period_s",
    "resamptyp":"resample_type",
    "citation": "citation",
    "searchid": "search_id",
}


def extract_metadata_from_file(file_path: str) -> Dict:
    """
    Parse all #KEY: value comment lines from an ONC CSV header.
    Returns a clean dict with human-readable field names.
    """
    raw = {}
    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("#"):
                    break
                if ":" not in line:
                    continue
                # Strip leading #/## and split on first colon
                content = line.lstrip("#").strip()
                key, value = content.split(":", 1)
                key = key.strip().upper()
                value = value.split("/")[0].strip().strip('"')  # drop inline comments
                raw[key] = value
    except Exception as e:
        print(f"[metadata] Failed to parse {file_path}: {e}")
        return {}

    metadata = {}
    for raw_key, clean_key in _HEADER_KEY_MAP.items():
        if raw_key.upper() in raw:
            metadata[clean_key] = raw[raw_key.upper()]

    # Infer parameter name from filename
    fname = os.path.basename(file_path)
    parts = fname.replace(".csv", "").split("_")
    metadata["parameter"] = parts[1] if len(parts) > 1 else "Unknown"
    metadata["device_code_from_filename"] = parts[0] if parts else "Unknown"

    return metadata


def _parse_lat_lon(metadata: Dict) -> Tuple[Optional[float], Optional[float]]:
    """Extract numeric lat/lon from metadata, handling range strings like '48.69 to 49.00'."""
    lat, lon = None, None
    for field, target in [("latitude", "lat"), ("longitude", "lon")]:
        raw = metadata.get(field, "")
        nums = re.findall(r"[-+]?\d+\.\d+", raw)
        if nums:
            # For ranges (mobile sensors), take the midpoint
            vals = [float(n) for n in nums]
            result = sum(vals) / len(vals)
            if target == "lat":
                lat = result
            else:
                lon = result
    return lat, lon


# ---------------------------------------------------------------------------
# CSV loading + QC filtering
# ---------------------------------------------------------------------------

def _find_header_row(file_path: str) -> int:
    """Find the index of the actual column-header line (contains 'Time UTC')."""
    with open(file_path, "r") as f:
        for i, line in enumerate(f):
            if "Time UTC" in line or "yyyy-mm-dd" in line.lower():
                return i
    raise ValueError(f"Could not find header row in {file_path}")


def load_csv_dataframe(file_path: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Load an ONC CSV into a clean DataFrame with:
      - Parsed timestamps (UTC)
      - Numeric value column
      - QC flag column
      - Bad rows removed (flags 3, 4, 6, 9)
    Also returns the full metadata dict.
    """
    metadata = extract_metadata_from_file(file_path)
    header_row = _find_header_row(file_path)

    df = pd.read_csv(
        file_path,
        skiprows=header_row,
        comment="#",
        skipinitialspace=True,
    )

    # Standardise column names
    df.columns = [c.strip().strip('"') for c in df.columns]

    # Identify timestamp, value, and QC columns
    time_col = df.columns[0]
    df["timestamp"] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Find the primary value column (first non-timestamp, non-QC, non-Count col)
    value_col = None
    qc_col = None
    for col in df.columns[1:]:
        col_upper = col.upper()
        if "QC FLAG" in col_upper or "QC_FLAG" in col_upper:
            if qc_col is None:
                qc_col = col
        elif "COUNT" not in col_upper and col != "timestamp":
            if value_col is None:
                value_col = col

    if value_col is None:
        # fallback: second column
        value_col = df.columns[1]
    if qc_col is None:
        # try to find any QC column
        qc_cols = [c for c in df.columns if "QC" in c or "Flag" in c]
        qc_col = qc_cols[0] if qc_cols else None

    df["value"] = pd.to_numeric(df[value_col], errors="coerce")
    df["qc_flag"] = pd.to_numeric(df[qc_col], errors="coerce").fillna(0).astype(int) if qc_col else 0

    # Parse units from the original column header line in the file
    original_value_col = value_col or ""
    try:
        with open(file_path, "r") as _f:
            for _line in _f:
                if "Time UTC" in _line:
                    raw_cols = [c.strip().strip('"') for c in _line.lstrip("#").split(",")]
                    non_time = [c for c in raw_cols[1:] if "QC" not in c and "Count" not in c]
                    if non_time:
                        original_value_col = non_time[0]
                    break
    except Exception:
        pass

    unit_match = re.search(r"\(([^)]+)\)", original_value_col)
    metadata["units"] = unit_match.group(1) if unit_match else ""
    metadata["value_column"] = original_value_col

    # Remove bad-flagged rows
    df = df[~df["qc_flag"].isin(BAD_FLAGS)].copy()
    df = df.dropna(subset=["value"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df, metadata


# ---------------------------------------------------------------------------
# Statistical chunking
# ---------------------------------------------------------------------------

def _compute_trend(values: np.ndarray) -> str:
    """Simple linear trend direction over a chunk."""
    if len(values) < 3:
        return "stable"
    x = np.arange(len(values))
    slope = np.polyfit(x, values, 1)[0]
    rel = abs(slope) / (np.mean(np.abs(values)) + 1e-9)
    if rel < 0.001:
        return "stable"
    return "increasing" if slope > 0 else "decreasing"


def _detect_anomalies(values: np.ndarray, threshold: float = 2.5) -> List[float]:
    """Return values that are more than `threshold` std deviations from the mean."""
    if len(values) < 5:
        return []
    mean, std = np.mean(values), np.std(values)
    if std < 1e-9:
        return []
    return [float(v) for v in values if abs(v - mean) / std > threshold]


def _caution_note(qc_flags: pd.Series) -> str:
    """Return a note if any caution-level flags are present in this chunk."""
    caution = qc_flags.isin(CAUTION_FLAGS).sum()
    if caution > 0:
        pct = int(100 * caution / len(qc_flags))
        return f" Note: {pct}% of readings are interpolated or flagged as probably good."
    return ""


def chunk_dataframe_daily(
    df: pd.DataFrame,
    metadata: Dict,
) -> List[str]:
    """
    Group by calendar day (UTC) and produce one rich text summary per day.
    Each summary includes: station, parameter, units, depth, date,
    mean/min/max/std, sample count, trend direction, anomaly flags,
    and QC data quality note.
    """
    if df.empty:
        return []

    station = metadata.get("station_name", metadata.get("station_code", "Unknown station"))
    # Shorten long station names
    if len(station) > 60:
        parts = station.split("-")
        station = parts[-1] if parts else station[:60]

    parameter = metadata.get("parameter", "measurement")
    units = metadata.get("units", "")
    depth = metadata.get("depth_m", "N/A")
    lat, lon = _parse_lat_lon(metadata)
    location_str = f"lat {lat:.4f}, lon {lon:.4f}" if lat and lon else "location unknown"

    documents = []
    df["date"] = df["timestamp"].dt.date

    for date, group in df.groupby("date"):
        values = group["value"].dropna().values
        if len(values) == 0:
            continue

        mean_v = float(np.mean(values))
        min_v  = float(np.min(values))
        max_v  = float(np.max(values))
        std_v  = float(np.std(values))
        trend  = _compute_trend(values)
        anomalies = _detect_anomalies(values)
        caution = _caution_note(group["qc_flag"])

        anomaly_str = ""
        if anomalies:
            anomaly_str = (
                f" ANOMALY DETECTED: {len(anomalies)} reading(s) deviated significantly "
                f"from the daily mean (e.g. {anomalies[0]:.4f} {units})."
            )

        doc = (
            f"On {date}, {parameter} at {station} ({location_str}, depth {depth}m): "
            f"mean={mean_v:.4f} {units}, min={min_v:.4f}, max={max_v:.4f}, "
            f"std={std_v:.4f}, trend={trend}, n={len(values)} samples."
            f"{anomaly_str}{caution}"
        )
        documents.append(doc)

    return documents


# ---------------------------------------------------------------------------
# Multi-parameter linking
# ---------------------------------------------------------------------------

def group_files_by_device_and_timespan(dataset_dir: str) -> Dict[str, List[str]]:
    """
    Group CSV files that share the same device code AND overlapping time span.
    Key = "<device_code>_<date_from>_<date_to>", value = list of file paths.

    This enables co-located, co-temporal parameters to be merged into
    richer multi-parameter chunks.
    """
    groups: Dict[str, List[str]] = {}
    for fname in os.listdir(dataset_dir):
        if not fname.endswith(".csv"):
            continue
        parts = fname.replace(".csv", "").split("_")
        if len(parts) < 4:
            continue
        device = parts[0]
        date_from = parts[2] if len(parts) > 2 else "unknown"
        date_to   = parts[3] if len(parts) > 3 else "unknown"
        key = f"{device}_{date_from}_{date_to}"
        groups.setdefault(key, []).append(os.path.join(dataset_dir, fname))
    return groups


def chunk_multi_parameter_group(file_paths: List[str]) -> List[str]:
    """
    Load multiple CSV files for the same device/timespan and produce
    daily chunks that combine all parameters into a single document.
    """
    all_dfs = {}
    shared_metadata = {}

    for fp in file_paths:
        try:
            df, meta = load_csv_dataframe(fp)
            param = meta.get("parameter", os.path.basename(fp))
            all_dfs[param] = (df, meta)
            if not shared_metadata:
                shared_metadata = meta
        except Exception as e:
            print(f"[multi-param] Failed to load {fp}: {e}")

    if not all_dfs:
        return []

    station = shared_metadata.get("station_name", shared_metadata.get("station_code", "Unknown"))
    if len(station) > 60:
        parts = station.split("-")
        station = parts[-1] if parts else station[:60]

    depth = shared_metadata.get("depth_m", "N/A")
    lat, lon = _parse_lat_lon(shared_metadata)
    location_str = f"lat {lat:.4f}, lon {lon:.4f}" if lat and lon else "location unknown"

    # Collect all unique dates across all parameters
    all_dates = set()
    for param, (df, _) in all_dfs.items():
        if not df.empty:
            all_dates.update(df["timestamp"].dt.date.unique())

    documents = []
    for date in sorted(all_dates):
        param_summaries = []
        anomaly_notes = []

        for param, (df, meta) in all_dfs.items():
            units = meta.get("units", "")
            day_data = df[df["timestamp"].dt.date == date]["value"].dropna().values
            if len(day_data) == 0:
                continue

            mean_v = float(np.mean(day_data))
            min_v  = float(np.min(day_data))
            max_v  = float(np.max(day_data))
            trend  = _compute_trend(day_data)
            anomalies = _detect_anomalies(day_data)

            param_summaries.append(
                f"{param}: mean={mean_v:.4f} {units}, min={min_v:.4f}, max={max_v:.4f}, trend={trend}"
            )
            if anomalies:
                anomaly_notes.append(
                    f"{param} had {len(anomalies)} anomalous reading(s) around {anomalies[0]:.4f} {units}"
                )

        if not param_summaries:
            continue

        anomaly_str = f" ANOMALIES: {'; '.join(anomaly_notes)}." if anomaly_notes else ""
        doc = (
            f"On {date}, multi-parameter readings at {station} "
            f"({location_str}, depth {depth}m): "
            + "; ".join(param_summaries)
            + f".{anomaly_str}"
        )
        documents.append(doc)

    return documents


# ---------------------------------------------------------------------------
# Top-level loader (called by rag_pipeline.py)
# ---------------------------------------------------------------------------

def load_all_csvs(dataset_dir: str, metadata: Dict) -> List[str]:
    """
    Single-file entry point (called per-file by RAGPipeline.initialize_dataset).
    Returns daily summary chunks with QC filtering and anomaly detection.
    """
    try:
        df, enriched_meta = load_csv_dataframe(dataset_dir)
        # Merge any metadata passed in from the pipeline
        enriched_meta.update({k: v for k, v in metadata.items() if v})
        return chunk_dataframe_daily(df, enriched_meta)
    except Exception as e:
        print(f"[load_all_csvs] Error processing {dataset_dir}: {e}")
        return []


def load_all_csvs_multiparams(dataset_dir: str) -> List[str]:
    """
    Directory-level entry point that groups files by device+timespan
    and produces multi-parameter daily chunks where possible.
    Single-parameter files that have no group partners are chunked individually.
    """
    groups = group_files_by_device_and_timespan(dataset_dir)
    documents = []

    for group_key, file_paths in groups.items():
        if len(file_paths) > 1:
            print(f"[multi-param] Grouping {len(file_paths)} files: {group_key}")
            docs = chunk_multi_parameter_group(file_paths)
        else:
            meta = extract_metadata_from_file(file_paths[0])
            docs = load_all_csvs(file_paths[0], meta)
        documents.extend(docs)

    return documents
