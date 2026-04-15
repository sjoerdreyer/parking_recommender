from datetime import datetime
from zoneinfo import ZoneInfo
import math

import folium
import pandas as pd
from folium.plugins import MarkerCluster

from config import COMBINED_FILE, OFFICES, OVERVIEW_FILE, PROCESSED_DIR


MAP_FILE = PROCESSED_DIR / "parking_map.html"

def fmt(value, decimals=1):
    if pd.isna(value):
        return "No data"
    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return str(value)


def fmt_bool(value):
    if pd.isna(value):
        return "Unknown"
    return "Yes" if bool(value) else "No"

def parse_time_ranges(text):
    if not isinstance(text, str) or not text.strip():
        return []

    parts = [part.strip() for part in text.split(";")]
    ranges = []

    for part in parts:
        if "-" in part:
            start, end = part.split("-", 1)
            ranges.append((start.strip(), end.strip()))

    return ranges


def is_open_now(row):

    # 1. Always open
    if pd.notna(row.get("open_24_7")) and bool(row.get("open_24_7")):
        return True

    # 2. Strong signal from API
    if (
        pd.notna(row.get("open_all_year"))
        and pd.notna(row.get("exit_possible_all_day"))
        and row.get("open_all_year")
        and row.get("exit_possible_all_day")
    ):
        return True

    now = datetime.now(ZoneInfo("Europe/Amsterdam"))

    weekday_map = {
        0: "opening_mon",
        1: "opening_tue",
        2: "opening_wed",
        3: "opening_thu",
        4: "opening_fri",
        5: "opening_sat",
        6: "opening_sun",
    }

    hours_text = row.get(weekday_map[now.weekday()])

    # 3. If no info → assume open (better UX)
    if not isinstance(hours_text, str) or not hours_text.strip():
        return True

    current_minutes = now.hour * 60 + now.minute

    for start_str, end_str in parse_time_ranges(hours_text):
        try:
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
        except:
            continue

        if sh * 60 + sm <= current_minutes <= eh * 60 + em:
            return True

    return False


def get_occupancy_color(occupancy_pct):
    if pd.isna(occupancy_pct):
        return "gray"
    if occupancy_pct > 95:
        return "red"
    if occupancy_pct >= 70:
        return "orange"
    if occupancy_pct >= 40:
        return "gold"
    return "green"


def build_parking_icon(color):
    html = f"""
    <div style="
        background-color:{color};
        width:28px;
        height:28px;
        border-radius:50%;
        border:2px solid white;
        box-shadow:0 0 4px rgba(0,0,0,0.35);
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:bold;
        font-size:16px;
        color:white;
    ">P</div>
    """
    return folium.DivIcon(html=html)


def fmt_bool(value):
    if pd.isna(value):
        return "Unknown"
    return "Yes" if bool(value) else "No"


def fmt_num(value, decimals=1, fallback="No data"):
    if pd.isna(value):
        return fallback
    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return str(value)


def opening_summary(row):
    summary = row.get("opening_hours_summary")
    if isinstance(summary, str) and summary.strip():
        return summary
    if pd.notna(row.get("open_24_7")) and bool(row.get("open_24_7")):
        return "Open 24/7"
    return "Opening hours not available"


def build_popup_html(row):

    status = "🟢 Open now" if is_open_now(row) else "🔴 Closed now"

    available = row.get("available_spaces")
    capacity = row.get("parking_capacity")
    occupancy = row.get("occupancy_pct")

    # ✅ New metric: FREE %
    if pd.notna(available) and pd.notna(capacity) and capacity > 0:
        free_pct = (available / capacity) * 100
    else:
        free_pct = None

    return f"""
    <div style="width: 310px;">
        <h4 style="margin-bottom:8px;">{row.get('facility_name')}</h4>

        <p><b>Status:</b> {status}</p>
        <p><b>City:</b> {row.get('city')}</p>
        <p><b>Office:</b> {row.get('matched_office')}</p>
        <p><b>Distance:</b> {fmt(row.get('distance_km'),2)} km</p>

        <hr>

        <p><b>🟢 Free spaces %:</b> {fmt(free_pct)}%</p>
        <p><b>🔴 Occupancy %:</b> {fmt(occupancy)}%</p>

        <p><b>Available spaces:</b> {fmt(available,0)}</p>
        <p><b>Capacity:</b> {fmt(capacity,0)}</p>

        <hr>

        <p><b>24/7:</b> {fmt_bool(row.get('open_24_7'))}</p>
        <p><b>Weekend:</b> {fmt_bool(row.get('open_weekend'))}</p>
        <p><b>Late:</b> {fmt_bool(row.get('open_late'))}</p>
    </div>
    """


def add_jitter_for_duplicate_coordinates(df):
    df = df.copy()
    df["plot_lat"] = df["latitude"]
    df["plot_lon"] = df["longitude"]

    grouped = df.groupby(["latitude", "longitude"], dropna=False)

    for _, idx in grouped.groups.items():
        idx = list(idx)
        n = len(idx)

        if n <= 1:
            continue

        radius = 0.00025
        for k, row_idx in enumerate(idx):
            angle = 2 * math.pi * (k / n)
            df.at[row_idx, "plot_lat"] = df.at[row_idx, "latitude"] + radius * math.sin(angle)
            df.at[row_idx, "plot_lon"] = df.at[row_idx, "longitude"] + radius * math.cos(angle)

    return df


def load_map_data():
    print("Loading parking overview...")
    overview_df = pd.read_csv(OVERVIEW_FILE)

    # make sure numeric
    for col in ["latitude", "longitude", "available_spaces", "parking_capacity", "occupancy_pct", "distance_km"]:
        if col in overview_df.columns:
            overview_df[col] = pd.to_numeric(overview_df[col], errors="coerce")

    # if lat/lon already present, great
    if "latitude" in overview_df.columns and "longitude" in overview_df.columns:
        if overview_df["latitude"].notna().sum() > 0 and overview_df["longitude"].notna().sum() > 0:
            return overview_df

    print("Overview file has no usable coordinates. Falling back to parking_combined.csv...")

    combined_df = pd.read_csv(COMBINED_FILE)

    # normalize combined cols
    combined_df = combined_df.rename(
        columns={
            "facility_name_static": "facility_name",
            "matched_city_static": "city",
            "parkingfacilitydynamicinformation.facilityactualstatus.vacantspaces": "available_spaces",
            "parkingfacilitydynamicinformation.facilityactualstatus.parkingcapacity": "parking_capacity",
        }
    )

    for col in ["latitude", "longitude", "available_spaces", "parking_capacity", "distance_km"]:
        if col in combined_df.columns:
            combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce")

    if "occupancy_pct" not in combined_df.columns and "available_spaces" in combined_df.columns and "parking_capacity" in combined_df.columns:
        combined_df["occupancy_pct"] = ((combined_df["parking_capacity"] - combined_df["available_spaces"]) / combined_df["parking_capacity"]) * 100

    # if overview has parking_id, merge coordinates back
    if "parking_id" in overview_df.columns and "parking_id" in combined_df.columns:
        coord_cols = ["parking_id", "latitude", "longitude"]
        coord_df = combined_df[coord_cols].drop_duplicates()

        merged = overview_df.drop(columns=[c for c in ["latitude", "longitude"] if c in overview_df.columns], errors="ignore")
        merged = merged.merge(coord_df, on="parking_id", how="left")
        return merged

    # final fallback: just use combined directly
    return combined_df


def main():
    df = load_map_data()

    if df.empty:
        print("Map dataset is empty.")
        return

    if "latitude" not in df.columns or "longitude" not in df.columns:
        print("No latitude/longitude columns found.")
        print(df.columns.tolist())
        return

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    map_df = df[df["latitude"].notna() & df["longitude"].notna()].copy()

    if map_df.empty:
        print("No rows with valid coordinates found.")
        return

    print(f"Rows loaded for map: {len(map_df)}")

    map_df = add_jitter_for_duplicate_coordinates(map_df)

    center_lat = map_df["latitude"].mean()
    center_lon = map_df["longitude"].mean()

    parking_map = folium.Map(location=[center_lat, center_lon], zoom_start=8)

    for office in OFFICES:
        folium.Marker(
            location=[office["lat"], office["lon"]],
            popup=f"{office['office_name']}<br>{office['address']}",
            tooltip=office["office_name"],
            icon=folium.Icon(color="blue", icon="building", prefix="fa"),
        ).add_to(parking_map)

    cluster = MarkerCluster(name="Parking garages").add_to(parking_map)

    for _, row in map_df.iterrows():
        icon_color = get_occupancy_color(pd.to_numeric(row.get("occupancy_pct"), errors="coerce"))
        popup_html = build_popup_html(row)

        folium.Marker(
            location=[row["plot_lat"], row["plot_lon"]],
            popup=folium.Popup(popup_html, max_width=340),
            tooltip=row.get("facility_name", "Parking"),
            icon=build_parking_icon(icon_color),
        ).add_to(cluster)

    legend_html = """
    <div style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 260px;
        z-index: 9999;
        background-color: white;
        border: 2px solid grey;
        border-radius: 8px;
        padding: 12px;
        font-size: 14px;
    ">
        <b>Parking Occupancy Legend</b><br><br>
        <span style="color:red;">●</span> Above 95% full<br>
        <span style="color:orange;">●</span> 70% to 95% full<br>
        <span style="color:gold;">●</span> 40% to 70% full<br>
        <span style="color:green;">●</span> Below 40% full<br>
        <span style="color:gray;">●</span> No occupancy data<br><br>
        <b>P icon color</b> shows occupancy level<br>
        <b>Popup</b> shows status and live data
    </div>
    """
    parking_map.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(parking_map)

    parking_map.save(MAP_FILE)
    print(f"Map saved to: {MAP_FILE}")


if __name__ == "__main__":
    main()