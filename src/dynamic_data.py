from datetime import datetime

import pandas as pd
import requests

from config import DYNAMIC_FILE, STATIC_FILE


def fetch_dynamic_json(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def flatten_dynamic_response(data):
    if isinstance(data, list):
        return pd.json_normalize(data, sep=".")
    if isinstance(data, dict):
        return pd.json_normalize(data, sep=".")
    return pd.DataFrame()


def main():
    print("Fetching dynamic parking data...")

    try:
        static_df = pd.read_csv(STATIC_FILE)
    except FileNotFoundError:
        print("Static file not found. Run static_data.py first.")
        pd.DataFrame().to_csv(DYNAMIC_FILE, index=False)
        return

    if static_df.empty:
        print("Static dataset is empty.")
        pd.DataFrame(columns=["parking_id", "facility_name", "matched_city", "timestamp"]).to_csv(DYNAMIC_FILE, index=False)
        return

    if "dynamic_data_url" not in static_df.columns:
        print("No dynamic_data_url column found. Creating empty dynamic file.")
        pd.DataFrame(columns=["parking_id", "facility_name", "matched_city", "timestamp"]).to_csv(DYNAMIC_FILE, index=False)
        return

    usable_df = static_df[static_df["dynamic_data_url"].notna()].copy()

    print(f"Rows in static file: {len(static_df)}")
    print(f"Rows with dynamic_data_url: {len(usable_df)}")

    rows = []

    for i, (_, row) in enumerate(usable_df.iterrows(), start=1):
        dynamic_url = row.get("dynamic_data_url")
        parking_id = row.get("parking_id")
        facility_name = row.get("facility_name")
        matched_city = row.get("matched_city")

        print(f"[{i}/{len(usable_df)}] Fetching dynamic data for: {facility_name}")

        try:
            data = fetch_dynamic_json(dynamic_url)
            temp_df = flatten_dynamic_response(data)

            if temp_df.empty:
                rows.append(
                    {
                        "parking_id": parking_id,
                        "facility_name": facility_name,
                        "matched_city": matched_city,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            else:
                temp_df["parking_id"] = parking_id
                temp_df["facility_name"] = facility_name
                temp_df["matched_city"] = matched_city
                temp_df["timestamp"] = datetime.now().isoformat()
                rows.extend(temp_df.to_dict(orient="records"))

        except Exception as e:
            print(f"Could not fetch dynamic data for {facility_name}: {e}")

    dynamic_df = pd.DataFrame(rows)

    if dynamic_df.empty:
        print("No dynamic data retrieved. Creating empty dynamic file.")
        dynamic_df = pd.DataFrame(columns=["parking_id", "facility_name", "matched_city", "timestamp"])

    dynamic_df.to_csv(DYNAMIC_FILE, index=False)

    print(f"Saved dynamic data to: {DYNAMIC_FILE}")
    print(f"Rows saved: {len(dynamic_df)}")
    print(dynamic_df.head())