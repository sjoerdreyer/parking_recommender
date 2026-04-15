import pandas as pd

from config import COMBINED_FILE, OVERVIEW_FILE


def has_weekend_hours(row):
    sat = row.get("opening_sat")
    sun = row.get("opening_sun")
    return bool((isinstance(sat, str) and sat.strip()) or (isinstance(sun, str) and sun.strip()))


def is_open_late(summary):
    if not isinstance(summary, str):
        return False

    if summary == "Open 24/7":
        return True

    return any(marker in summary for marker in ["22:", "23:"])


def main():
    print("Running analysis...")

    try:
        df = pd.read_csv(COMBINED_FILE)
    except FileNotFoundError:
        print("Combined file not found.")
        return

    if df.empty:
        print("Combined dataset is empty.")
        return

    capacity_col = "parkingfacilitydynamicinformation.facilityactualstatus.parkingcapacity"
    available_col = "parkingfacilitydynamicinformation.facilityactualstatus.vacantspaces"

    if capacity_col not in df.columns or available_col not in df.columns:
        print("Required dynamic columns not found.")
        print(df.columns.tolist())
        return

    # numeric conversions
    df[capacity_col] = pd.to_numeric(df[capacity_col], errors="coerce")
    df[available_col] = pd.to_numeric(df[available_col], errors="coerce")
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    df["office_lat"] = pd.to_numeric(df.get("office_lat"), errors="coerce")
    df["office_lon"] = pd.to_numeric(df.get("office_lon"), errors="coerce")
    df["distance_km"] = pd.to_numeric(df.get("distance_km"), errors="coerce")

    df = df[df[capacity_col].notna()]
    df = df[df[capacity_col] > 0]

    if df.empty:
        print("No valid rows with parking capacity found.")
        return

    df["occupancy_pct"] = ((df[capacity_col] - df[available_col]) / df[capacity_col]) * 100
    df["open_weekend"] = df.apply(has_weekend_hours, axis=1)

    if "opening_hours_summary" in df.columns:
        df["open_late"] = df["opening_hours_summary"].apply(is_open_late)
    else:
        df["open_late"] = False

    overview_cols = [
        "parking_id",
        "facility_name_static",
        "matched_city_static",
        "matched_office",
        "office_address",
        "latitude",
        "longitude",
        "office_lat",
        "office_lon",
        "distance_km",
        "opening_hours_summary",
        "opening_mon",
        "opening_tue",
        "opening_wed",
        "opening_thu",
        "opening_fri",
        "opening_sat",
        "opening_sun",
        "open_all_year",
        "exit_possible_all_day",
        "open_24_7",
        "open_weekend",
        "open_late",
        available_col,
        capacity_col,
        "occupancy_pct",
        "timestamp",
    ]

    existing_cols = [col for col in overview_cols if col in df.columns]
    overview_df = df[existing_cols].copy()

    overview_df = overview_df.rename(
        columns={
            "facility_name_static": "facility_name",
            "matched_city_static": "city",
            available_col: "available_spaces",
            capacity_col: "parking_capacity",
        }
    )

    overview_df = overview_df.sort_values("occupancy_pct", ascending=False, na_position="last")
    overview_df.to_csv(OVERVIEW_FILE, index=False)

    print(f"Saved ordered overview to: {OVERVIEW_FILE}")
    print(f"Rows: {len(overview_df)}")
    print(f"Rows with latitude: {overview_df['latitude'].notna().sum() if 'latitude' in overview_df.columns else 0}")
    print(f"Rows with longitude: {overview_df['longitude'].notna().sum() if 'longitude' in overview_df.columns else 0}")
    print(overview_df.head())


if __name__ == "__main__":
    main()