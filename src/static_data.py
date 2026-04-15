import math
from typing import Any

import pandas as pd
import requests

from config import INDEX_URL, OFFICES, STATIC_FILE, TARGET_CITIES


def fetch_index():
    response = requests.get(INDEX_URL, timeout=30)
    response.raise_for_status()
    return response.json()


def get_facilities_from_index(data):
    return pd.DataFrame(data.get("ParkingFacilities", []))


def fetch_static_details(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def flatten_json(data: Any) -> dict:
    if isinstance(data, dict):
        records = pd.json_normalize(data, sep=".").to_dict(orient="records")
        return records[0] if records else {}
    if isinstance(data, list) and len(data) > 0:
        records = pd.json_normalize(data[0], sep=".").to_dict(orient="records")
        return records[0] if records else {}
    return {}


def find_first_value(record, keywords):
    for key, value in record.items():
        key_lower = key.lower()
        if any(keyword in key_lower for keyword in keywords):
            if value is not None and str(value).strip() != "":
                return value
    return None


def find_city_in_text(text):
    if not isinstance(text, str):
        return None

    text_lower = text.lower()
    for city in TARGET_CITIES:
        if city.lower() in text_lower:
            return city
    return None


def get_office_for_city(city):
    for office in OFFICES:
        if office["city"] == city:
            return office
    return None


def calculate_distance(lat1, lon1, lat2, lon2):
    r = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def format_time_block(time_obj):
    if not isinstance(time_obj, dict):
        return None

    h = str(time_obj.get("h", 0)).zfill(2)
    m = str(time_obj.get("m", 0)).zfill(2)
    return f"{h}:{m}"


def parse_opening_times(static_json):
    result = {
        "opening_hours_summary": None,
        "opening_mon": None,
        "opening_tue": None,
        "opening_wed": None,
        "opening_thu": None,
        "opening_fri": None,
        "opening_sat": None,
        "opening_sun": None,
        "open_all_year": False,
        "exit_possible_all_day": False,
        "open_24_7": False,
    }

    parking_info = static_json.get("parkingFacilityInformation", {})
    opening_times = parking_info.get("openingTimes", [])

    if not opening_times:
        return result

    day_map = {
        "Mon": "opening_mon",
        "Tue": "opening_tue",
        "Wed": "opening_wed",
        "Thu": "opening_thu",
        "Fri": "opening_fri",
        "Sat": "opening_sat",
        "Sun": "opening_sun",
    }

    day_ranges = {value: [] for value in day_map.values()}

    for period in opening_times:
        open_all_year = period.get("openAllYear", False)
        exit_possible_all_day = period.get("exitPossibleAllDay", False)

        if open_all_year:
            result["open_all_year"] = True
        if exit_possible_all_day:
            result["exit_possible_all_day"] = True

        # If both are true, treat as 24/7
        if open_all_year and exit_possible_all_day:
            result["open_24_7"] = True

        entry_times = period.get("entryTimes", [])

        for entry in entry_times:
            enter_from = format_time_block(entry.get("enterFrom"))
            enter_until = format_time_block(entry.get("enterUntil"))

            if enter_from is None or enter_until is None:
                continue

            time_range = f"{enter_from}-{enter_until}"
            day_names = entry.get("dayNames", [])

            for day in day_names:
                column_name = day_map.get(day)
                if column_name:
                    day_ranges[column_name].append(time_range)

    # If 24/7, override all days
    if result["open_24_7"]:
        for column_name in day_ranges.keys():
            result[column_name] = "00:00-23:59"
        result["opening_hours_summary"] = "Open 24/7"
        return result

    for column_name, ranges in day_ranges.items():
        if ranges:
            result[column_name] = "; ".join(ranges)

    summary_parts = []
    pretty_names = {
        "opening_mon": "Mon",
        "opening_tue": "Tue",
        "opening_wed": "Wed",
        "opening_thu": "Thu",
        "opening_fri": "Fri",
        "opening_sat": "Sat",
        "opening_sun": "Sun",
    }

    for column_name in [
        "opening_mon",
        "opening_tue",
        "opening_wed",
        "opening_thu",
        "opening_fri",
        "opening_sat",
        "opening_sun",
    ]:
        value = result[column_name]
        if value:
            summary_parts.append(f"{pretty_names[column_name]} {value}")

    if summary_parts:
        result["opening_hours_summary"] = " | ".join(summary_parts)

    return result


def extract_static_fields(static_json):

    details = {
        "address": None,
        "latitude": None,
        "longitude": None,
        "capacity_static": None,
        "opening_hours_summary": None,
        "opening_mon": None,
        "opening_tue": None,
        "opening_wed": None,
        "opening_thu": None,
        "opening_fri": None,
        "opening_sat": None,
        "opening_sun": None,
        "open_all_year": False,
        "exit_possible_all_day": False,
        "open_24_7": False,
    }

    info = static_json.get("parkingFacilityInformation", {})

    # ✅ ADD THIS LINE
    lat, lon = extract_coordinates(static_json)
    details["latitude"] = lat
    details["longitude"] = lon

    # (keep your existing logic below)

    # capacity example
    specs = info.get("specifications", [])
    if specs:
        details["capacity_static"] = specs[0].get("capacity")

    # opening times (you already have this)
    # keep your existing logic here

    return details


def add_city_match(row):
    possible_texts = [
        row.get("facility_name"),
        row.get("locationForDisplay"),
        row.get("address"),
    ]

    for text in possible_texts:
        city = find_city_in_text(text)
        if city is not None:
            return city

    return None


def add_office_info_and_distance(row):
    city = row.get("matched_city")
    office = get_office_for_city(city)

    if office is None:
        return pd.Series(
            {
                "matched_office": None,
                "office_address": None,
                "office_lat": None,
                "office_lon": None,
                "distance_km": None,
            }
        )

    lat = row.get("latitude")
    lon = row.get("longitude")

    distance_km = None
    if pd.notna(lat) and pd.notna(lon):
        distance_km = round(calculate_distance(office["lat"], office["lon"], lat, lon), 3)

    return pd.Series(
        {
            "matched_office": office["office_name"],
            "office_address": office["address"],
            "office_lat": office["lat"],
            "office_lon": office["lon"],
            "distance_km": distance_km,
        }
    )
    
def extract_coordinates(static_json):
    """
    Extract first valid lat/lon from accessPoints
    """
    try:
        access_points = static_json.get("parkingFacilityInformation", {}).get("accessPoints", [])

        for ap in access_points:
            locations = ap.get("accessPointLocation", [])

            for loc in locations:
                lat = loc.get("latitude")
                lon = loc.get("longitude")

                if lat is not None and lon is not None:
                    return lat, lon

    except Exception:
        pass

    return None, None


def main():
    print("Fetching parking index...")

    data = fetch_index()
    df = get_facilities_from_index(data)

    if df.empty:
        print("No parking facilities found.")
        df.to_csv(STATIC_FILE, index=False)
        return

    print(f"Index fetched. Total facilities found: {len(df)}")

    df = df.rename(
        columns={
            "identifier": "parking_id",
            "name": "facility_name",
            "staticDataUrl": "static_data_url",
            "dynamicDataUrl": "dynamic_data_url",
            "limitedAccess": "limited_access",
            "staticDataLastUpdated": "static_data_last_updated",
        }
    )

    if "locationForDisplay" not in df.columns:
        df["locationForDisplay"] = None

    df["matched_city"] = df["facility_name"].apply(find_city_in_text)

    missing_city_mask = df["matched_city"].isna()
    df.loc[missing_city_mask, "matched_city"] = df.loc[missing_city_mask, "locationForDisplay"].apply(find_city_in_text)

    city_df = df[df["matched_city"].notna()].copy()

    print(f"Facilities matched by city from index fields: {len(city_df)}")

    if city_df.empty:
        print("No city matches found.")
        city_df.to_csv(STATIC_FILE, index=False)
        return

    details_rows = []

    for i, (_, row) in enumerate(city_df.iterrows(), start=1):
        facility_name = row.get("facility_name")
        static_url = row.get("static_data_url")

        print(f"[{i}/{len(city_df)}] Fetching static details for: {facility_name}")

        details = {
            "address": None,
            "latitude": None,
            "longitude": None,
            "capacity_static": None,
            "opening_hours_summary": None,
            "opening_mon": None,
            "opening_tue": None,
            "opening_wed": None,
            "opening_thu": None,
            "opening_fri": None,
            "opening_sat": None,
            "opening_sun": None,
            "open_all_year": False,
            "exit_possible_all_day": False,
            "open_24_7": False,
            }

        if pd.notna(static_url):
            try:
                static_json = fetch_static_details(static_url)
                details = extract_static_fields(static_json)
            except Exception as e:
                print(f"Could not fetch static details for {facility_name}: {e}")

        details_rows.append(details)

    details_df = pd.DataFrame(details_rows)
    city_df = pd.concat([city_df.reset_index(drop=True), details_df], axis=1)

    city_df["latitude"] = pd.to_numeric(city_df["latitude"], errors="coerce")
    city_df["longitude"] = pd.to_numeric(city_df["longitude"], errors="coerce")
    city_df["capacity_static"] = pd.to_numeric(city_df["capacity_static"], errors="coerce")

    city_df["matched_city"] = city_df.apply(add_city_match, axis=1)
    city_df = city_df[city_df["matched_city"].notna()].copy()

    office_info_df = city_df.apply(add_office_info_and_distance, axis=1)
    city_df = pd.concat([city_df, office_info_df], axis=1)

    city_df.to_csv(STATIC_FILE, index=False)

    print(f"Saved static data to: {STATIC_FILE}")
    print(f"Rows saved: {len(city_df)}")
    print(f"Rows with dynamic_data_url: {city_df['dynamic_data_url'].notna().sum()}")
    print(city_df.head())


if __name__ == "__main__":
    main()