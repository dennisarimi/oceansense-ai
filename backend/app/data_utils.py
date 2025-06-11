# File: app/data_utils.py
import os
from typing import Dict, List
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import re

# Setup geolocator for reverse geocoding with caching
geolocator = Nominatim(user_agent="onc_rag_pipeline")
geocode = RateLimiter(geolocator.reverse, min_delay_seconds=1)
location_cache = {}

def extract_metadata_from_file(file_path):
    metadata = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith("#"):
                    break
                if ":" in line:
                    key, value = line.lstrip("#").split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    value = value.strip().strip('"')
                    metadata[key] = value
    except Exception as e:
        print(f"Failed to extract metadata from {file_path}: {e}")
    return metadata

def extract_lat_lon_from_metadata(metadata):
    lat, lon = None, None
    if "latitude" in metadata:
        match = re.search(r'([-+]?\d*\.\d+)', metadata["latitude"])
        if match:
            lat = float(match.group(1))
    if "longitude" in metadata:
        match = re.search(r'([-+]?\d*\.\d+)', metadata["longitude"])
        if match:
            lon = float(match.group(1))
    return lat, lon

def load_all_csvs(dataset_dir: str, metadata: Dict) -> List[str]:
    import pandas as pd

    # 🔍 Detect header row dynamically
    with open(dataset_dir, 'r') as f:
        lines = f.readlines()
        header_line_idx = next(i for i, line in enumerate(lines) if "yyyy-mm-dd" in line)

    df = pd.read_csv(dataset_dir, skiprows=header_line_idx)
    df = df.dropna(subset=[df.columns[1]])
    chunk_size = 20
    documents = []

    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i + chunk_size]
        if chunk.empty:
            continue
        start_time = chunk.iloc[0, 0]
        end_time = chunk.iloc[-1, 0]
        values = chunk.iloc[:, 1].tolist()
        values_str = ", ".join([str(v) for v in values[:5]]) + ("..." if len(values) > 5 else "")
        doc = (
            f"{metadata.get('parameter', 'Measurement')} readings from {start_time} to {end_time} "
            f"at station {metadata.get('station', 'Unknown')} using device {metadata.get('device', '')}. "
            f"Depth: {metadata.get('depth', 'N/A')}m. Units: {metadata.get('units', '')}. "
            f"Sample values: {values_str}."
        )
        documents.append(doc)

    return documents



def convert_rows_to_text(df, source_name="unknown", lat=None, lon=None, metadata=None):
    texts = []
    instrument = source_name.replace(".csv", "").split("_")[0]
    parameter = source_name.replace(".csv", "").split("_")[1] if len(source_name.split("_")) > 1 else "unknown"
    timestamp_range = " to ".join(source_name.replace(".csv", "").split("_")[2:4]) if len(source_name.split("_")) > 3 else ""

    location_name = "Unknown location"
    if pd.notnull(lat) and pd.notnull(lon):
        coord_key = (round(lat, 5), round(lon, 5))
        if coord_key in location_cache:
            location_name = location_cache[coord_key]
        else:
            try:
                location = geocode((lat, lon))
                if location:
                    location_name = location.address
                    location_cache[coord_key] = location_name
            except Exception as e:
                print(f"Geocoding error: {e}")

    for _, row in df.iterrows():
        timestamp = row.get("timestamp") or row.get("date [UTC]", "")
        readings = []
        for col in df.columns:
            if col.lower() not in ["timestamp", "date [utc]", "datetime", "latitude", "longitude", "lat", "lon"]:
                readings.append(f"{col}: {row[col]}")

        metadata_desc = ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in metadata.items())
        text = (
            f"[SOURCE: {source_name}] "
            f"At {timestamp}, instrument {instrument} measuring {parameter} recorded the following at {location_name}: "
            + "; ".join(readings)
            + f". Time range: {timestamp_range}. Metadata: {metadata_desc}"
        )

        texts.append(text)
    return texts