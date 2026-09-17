# File: app/onc_client.py
"""
ONC (Ocean Networks Canada) API client for OceanSense AI.

Wraps the Oceans 3.0 Data API v3 endpoints:
  - /locations           → discover stations
  - /dataProducts        → discover available parameters at a station
  - /scalardata/location → fetch scalar time-series data

Docs: https://wiki.oceannetworks.ca/display/O2A/API+v3+documentation

Usage:
    client = ONCClient(token="YOUR_TOKEN")
    df = client.get_scalar_data(
        location_code="BACAX",
        device_category_code="CTD",
        data_product_code="TSSD",  # Temperature & Salinity
        date_from="2024-01-01T00:00:00.000Z",
        date_to="2024-01-02T00:00:00.000Z",
    )
"""

import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import requests
import pandas as pd

logger = logging.getLogger(__name__)

ONC_BASE_URL = "https://data.oceannetworks.ca/api"

# How far back "recent" queries look when no date range is specified
DEFAULT_LOOKBACK_HOURS = 48

# Common device category codes used in queries
DEVICE_CATEGORY_ALIASES = {
    "temperature":    "CTD",
    "salinity":       "CTD",
    "conductivity":   "CTD",
    "oxygen":         "DO",
    "dissolved oxygen": "DO",
    "chlorophyll":    "FLUOROMETER",
    "fluorescence":   "FLUOROMETER",
    "turbidity":      "TURBIDITYMETER",
    "pressure":       "CTD",
    "current":        "ADCP",
    "wave":           "WAVESENSOR",
}

# Common location code keywords for fuzzy matching
LOCATION_KEYWORDS = {
    "cambridge bay":  "CBCS",
    "saanich":        "SAAN",
    "bamfield":       "BACAX",
    "barkley":        "BACAX",
    "folger":         "FGPD",
    "victoria":       "TWDP",
    "fraser":         "LSFD",
    "delta":          "LSFD",
    "tsawwassen":     "TWSB",
    "swartz bay":     "TWSB",
    "jupiter":        "JPLSS",
    "strait":         "TWDP",
}


class ONCAPIError(Exception):
    pass


class ONCClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("ONC_TOKEN")
        if not self.token:
            logger.warning(
                "ONC_TOKEN not set. API calls will fail. "
                "Get a free token at https://data.oceannetworks.ca/Profile"
            )
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Low-level request helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: Dict) -> Dict:
        params["token"] = self.token
        url = f"{ONC_BASE_URL}/{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            body = ""
            try:
                body = e.response.json()
            except Exception:
                pass
            raise ONCAPIError(f"HTTP {e.response.status_code} from ONC API: {body}") from e
        except requests.exceptions.RequestException as e:
            raise ONCAPIError(f"Request failed: {e}") from e

    # ------------------------------------------------------------------
    # Discovery endpoints
    # ------------------------------------------------------------------

    def get_locations(self, location_name: Optional[str] = None) -> List[Dict]:
        """
        List available monitoring locations.
        Optionally filter by a partial name string.
        """
        params = {}
        if location_name:
            params["locationName"] = location_name
        data = self._get("locations", params)
        return data if isinstance(data, list) else data.get("locations", [])

    def get_device_categories(self, location_code: str) -> List[Dict]:
        """List device categories available at a given location."""
        data = self._get("deviceCategories", {"locationCode": location_code})
        return data if isinstance(data, list) else data.get("deviceCategories", [])

    def get_data_products(self, location_code: str, device_category_code: str) -> List[Dict]:
        """List data products (parameters) for a location+device."""
        data = self._get("dataProducts", {
            "locationCode": location_code,
            "deviceCategoryCode": device_category_code,
        })
        return data if isinstance(data, list) else data.get("dataProducts", [])

    # ------------------------------------------------------------------
    # Scalar data fetch
    # ------------------------------------------------------------------

    def get_scalar_data(
        self,
        location_code: str,
        device_category_code: str,
        property_code: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        resample_period: int = 900,        # 15 minutes in seconds
    ) -> pd.DataFrame:
        """
        Fetch scalar time-series data from the ONC API.

        Returns a DataFrame with columns:
            timestamp (UTC), value, qc_flag, units, location_code,
            device_category, property_code

        Args:
            location_code:          ONC location code (e.g. "BACAX")
            device_category_code:   e.g. "CTD", "DO", "FLUOROMETER"
            property_code:          optional scalar property (e.g. "temperature")
            date_from:              ISO 8601 UTC string; defaults to 48h ago
            date_to:                ISO 8601 UTC string; defaults to now
            resample_period:        aggregation window in seconds (default 900 = 15min)
        """
        now = datetime.now(timezone.utc)
        if date_from is None:
            date_from = (now - timedelta(hours=DEFAULT_LOOKBACK_HOURS)).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        if date_to is None:
            date_to = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        params = {
            "locationCode":        location_code,
            "deviceCategoryCode":  device_category_code,
            "dateFrom":            date_from,
            "dateTo":              date_to,
            "resampleType":        "average",
            "resamplePeriod":      resample_period,
            "outputFormat":        "Array",
            "fillGaps":            True,
        }
        if property_code:
            params["propertyCode"] = property_code

        data = self._get("scalardata/location", params)
        return self._parse_scalar_response(data, location_code, device_category_code)

    def _parse_scalar_response(
        self,
        data: Dict,
        location_code: str,
        device_category_code: str,
    ) -> pd.DataFrame:
        """Parse the ONC scalardata/location JSON response into a DataFrame."""
        rows = []
        sensor_data = data.get("sensorData", [])

        for sensor in sensor_data:
            prop_code = sensor.get("actualSamples", {}).get("propertyCode", "unknown")
            units = sensor.get("actualSamples", {}).get("unitOfMeasure", "")
            times = sensor.get("actualSamples", {}).get("sampleTimes", [])
            values = sensor.get("actualSamples", {}).get("values", [])
            qc_flags = sensor.get("actualSamples", {}).get("qaqcFlags", [])

            # Pad qc_flags if missing
            if not qc_flags:
                qc_flags = [1] * len(values)

            for t, v, q in zip(times, values, qc_flags):
                rows.append({
                    "timestamp":       pd.to_datetime(t, utc=True),
                    "value":           v,
                    "qc_flag":         q,
                    "units":           units,
                    "location_code":   location_code,
                    "device_category": device_category_code,
                    "property_code":   prop_code,
                })

        if not rows:
            return pd.DataFrame(columns=[
                "timestamp", "value", "qc_flag", "units",
                "location_code", "device_category", "property_code"
            ])

        df = pd.DataFrame(rows)
        df = df[~df["qc_flag"].isin({3, 4, 6, 9})]   # remove bad QC
        df = df.dropna(subset=["value"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # Higher-level: natural-language-friendly fetch
    # ------------------------------------------------------------------

    def fetch_recent_for_query(
        self,
        parameter: str,
        location_hint: str,
        hours_back: int = 48,
    ) -> Tuple[pd.DataFrame, str]:
        """
        Given a plain-language parameter (e.g. "temperature") and a location
        hint (e.g. "Saanich Inlet"), attempt to fetch recent data.

        Returns (DataFrame, status_message).
        """
        # Resolve device category
        param_lower = parameter.lower()
        device_cat = DEVICE_CATEGORY_ALIASES.get(param_lower)
        if not device_cat:
            # try partial match
            for key, val in DEVICE_CATEGORY_ALIASES.items():
                if key in param_lower or param_lower in key:
                    device_cat = val
                    break
        if not device_cat:
            return pd.DataFrame(), f"Unknown parameter '{parameter}'. Cannot map to ONC device category."

        # Resolve location code
        location_lower = location_hint.lower()
        location_code = None
        for keyword, code in LOCATION_KEYWORDS.items():
            if keyword in location_lower:
                location_code = code
                break

        if not location_code:
            # Try the discovery API
            try:
                locations = self.get_locations(location_name=location_hint)
                if locations:
                    location_code = locations[0].get("locationCode")
            except ONCAPIError:
                pass

        if not location_code:
            return pd.DataFrame(), (
                f"Could not resolve location '{location_hint}' to an ONC station code. "
                "Try a known location like 'Saanich Inlet', 'Cambridge Bay', or 'Bamfield'."
            )

        now = datetime.now(timezone.utc)
        date_from = (now - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        date_to   = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        try:
            df = self.get_scalar_data(
                location_code=location_code,
                device_category_code=device_cat,
                property_code=param_lower,
                date_from=date_from,
                date_to=date_to,
            )
            if df.empty:
                return df, (
                    f"No recent {parameter} data found at {location_hint} "
                    f"(station {location_code}) for the past {hours_back} hours."
                )
            return df, f"Fetched {len(df)} readings of {parameter} from {location_hint} ({location_code})."
        except ONCAPIError as e:
            return pd.DataFrame(), f"ONC API error: {e}"

    # ------------------------------------------------------------------
    # Summarise a live DataFrame into a RAG-style text chunk
    # ------------------------------------------------------------------

    @staticmethod
    def dataframe_to_summary(df: pd.DataFrame, parameter: str, location: str) -> str:
        """
        Convert a live-data DataFrame into a rich text summary suitable
        for inclusion in the LLM prompt context.
        """
        if df.empty:
            return f"No {parameter} data available for {location}."

        import numpy as np

        values = df["value"].dropna().values
        units  = df["units"].iloc[0] if "units" in df.columns else ""
        t_start = df["timestamp"].min().strftime("%Y-%m-%d %H:%M UTC")
        t_end   = df["timestamp"].max().strftime("%Y-%m-%d %H:%M UTC")

        mean_v  = float(np.mean(values))
        min_v   = float(np.min(values))
        max_v   = float(np.max(values))
        std_v   = float(np.std(values))

        # Trend
        if len(values) >= 3:
            slope = np.polyfit(np.arange(len(values)), values, 1)[0]
            rel   = abs(slope) / (abs(mean_v) + 1e-9)
            trend = "stable" if rel < 0.001 else ("increasing" if slope > 0 else "decreasing")
        else:
            trend = "insufficient data for trend"

        # Latest reading
        latest_row = df.iloc[-1]
        latest_val = latest_row["value"]
        latest_time = latest_row["timestamp"].strftime("%Y-%m-%d %H:%M UTC")

        return (
            f"[LIVE DATA] {parameter.title()} at {location} "
            f"from {t_start} to {t_end}: "
            f"latest={latest_val:.4f} {units} (at {latest_time}), "
            f"mean={mean_v:.4f}, min={min_v:.4f}, max={max_v:.4f}, "
            f"std={std_v:.4f}, trend={trend}, n={len(values)} readings."
        )
