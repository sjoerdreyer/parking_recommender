import json
from pathlib import Path

import pandas as pd

from config import OVERVIEW_FILE, PROCESSED_DIR

OUTPUT_HTML = PROCESSED_DIR / "parking_map_leaflet.html"


def fmt_num(value, decimals=1, fallback="No data"):
    if pd.isna(value):
        return fallback
    try:
        return round(float(value), decimals)
    except Exception:
        return fallback


def fmt_bool(value):
    if pd.isna(value):
        return "Unknown"
    return "Yes" if bool(value) else "No"


def get_color(occupancy_pct):
    if pd.isna(occupancy_pct):
        return "gray"
    if occupancy_pct > 95:
        return "red"
    if occupancy_pct >= 70:
        return "orange"
    if occupancy_pct >= 40:
        return "gold"
    return "green"


def build_records(df: pd.DataFrame):
    records = []

    for _, row in df.iterrows():
        available = pd.to_numeric(row.get("available_spaces"), errors="coerce")
        capacity = pd.to_numeric(row.get("parking_capacity"), errors="coerce")
        occupancy = pd.to_numeric(row.get("occupancy_pct"), errors="coerce")

        free_pct = None
        if pd.notna(available) and pd.notna(capacity) and capacity > 0:
            free_pct = round((available / capacity) * 100, 1)

        record = {
            "facility_name": row.get("facility_name", "Unknown parking"),
            "city": row.get("city", "Unknown"),
            "matched_office": row.get("matched_office", "Unknown"),
            "office_address": row.get("office_address", "Unknown"),
            "latitude": pd.to_numeric(row.get("latitude"), errors="coerce"),
            "longitude": pd.to_numeric(row.get("longitude"), errors="coerce"),
            "distance_km": fmt_num(row.get("distance_km"), 3),
            "open_24_7": fmt_bool(row.get("open_24_7")),
            "open_weekend": fmt_bool(row.get("open_weekend")),
            "open_late": fmt_bool(row.get("open_late")),
            "available_spaces": fmt_num(available, 0),
            "parking_capacity": fmt_num(capacity, 0),
            "occupancy_pct": fmt_num(occupancy, 1),
            "free_pct": free_pct if free_pct is not None else "No data",
            "opening_hours_summary": row.get("opening_hours_summary", "Opening hours not available"),
            "marker_color": get_color(occupancy),
        }
        records.append(record)

    return records


def main():
    df = pd.read_csv(OVERVIEW_FILE)

    if df.empty:
        print("Overview file is empty.")
        return

    for col in ["latitude", "longitude", "available_spaces", "parking_capacity", "occupancy_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    map_df = df[df["latitude"].notna() & df["longitude"].notna()].copy()

    if map_df.empty:
        print("No rows with valid coordinates found in parking_facilities_overview.csv.")
        return

    records = build_records(map_df)
    center_lat = map_df["latitude"].mean()
    center_lon = map_df["longitude"].mean()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Parking Map Leaflet</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  />
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"
  />
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"
  />

  <style>
    html, body {{
      margin: 0;
      padding: 0;
      height: 100%;
      font-family: Arial, sans-serif;
    }}

    #map {{
      width: 100%;
      height: 100vh;
    }}

    .parking-icon {{
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 0 4px rgba(0,0,0,0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 16px;
      color: white;
      text-align: center;
    }}

    .legend {{
      background: white;
      padding: 12px;
      border: 2px solid grey;
      border-radius: 8px;
      line-height: 1.5;
      font-size: 14px;
      box-shadow: 0 1px 5px rgba(0,0,0,0.3);
    }}
  </style>
</head>
<body>
  <div id="map"></div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

  <script>
    const parkingData = {json.dumps(records, ensure_ascii=False)};
    const officeData = {json.dumps([
        {
            "office_name": "Gemeente Breda",
            "address": "Claudius Prinsenlaan 10, 4811 DJ Breda",
            "lat": 51.5719,
            "lon": 4.7683
        },
        {
            "office_name": "Gemeente Utrecht",
            "address": "Stadsplateau 1, 3521 AZ Utrecht",
            "lat": 52.0907,
            "lon": 5.1214
        },
        {
            "office_name": "TenneT",
            "address": "Utrechtseweg 310, 6812 AR Arnhem",
            "lat": 51.9851,
            "lon": 5.8987
        },
        {
            "office_name": "Gemeente Zwolle",
            "address": "Grote Kerkplein 15, 8011 PK Zwolle",
            "lat": 52.5168,
            "lon": 6.0830
        }
    ], ensure_ascii=False)};

    const map = L.map('map').setView([{center_lat}, {center_lon}], 8);

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const clusterGroup = L.markerClusterGroup();

    function buildParkingIcon(color) {{
      return L.divIcon({{
        className: '',
        html: `<div class="parking-icon" style="background:${{color}};">P</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -12]
      }});
    }}

    function buildPopup(row) {{
      return `
        <div style="width: 300px;">
          <h3 style="margin:0 0 8px 0;">${{row.facility_name}}</h3>
          <p><b>City:</b> ${{row.city}}</p>
          <p><b>Office:</b> ${{row.matched_office}}</p>
          <p><b>Distance to office (km):</b> ${{row.distance_km}}</p>
          <hr>
          <p><b>Free parking %:</b> ${{row.free_pct}}</p>
          <p><b>Occupancy %:</b> ${{row.occupancy_pct}}</p>
          <p><b>Available spaces:</b> ${{row.available_spaces}}</p>
          <p><b>Parking capacity:</b> ${{row.parking_capacity}}</p>
          <hr>
          <p><b>Open 24/7:</b> ${{row.open_24_7}}</p>
          <p><b>Open weekend:</b> ${{row.open_weekend}}</p>
          <p><b>Open late:</b> ${{row.open_late}}</p>
          <p><b>Opening summary:</b> ${{row.opening_hours_summary || "Opening hours not available"}}</p>
        </div>
      `;
    }}

    parkingData.forEach(row => {{
      const marker = L.marker(
        [row.latitude, row.longitude],
        {{ icon: buildParkingIcon(row.marker_color) }}
      ).bindPopup(buildPopup(row));

      marker.bindTooltip(row.facility_name);
      clusterGroup.addLayer(marker);
    }});

    map.addLayer(clusterGroup);

    officeData.forEach(office => {{
      const marker = L.marker([office.lat, office.lon]).bindPopup(
        `<b>${{office.office_name}}</b><br>${{office.address}}`
      );
      marker.bindTooltip(office.office_name);
      marker.addTo(map);
    }});

    const legend = L.control({{position: 'bottomleft'}});
    legend.onAdd = function() {{
      const div = L.DomUtil.create('div', 'legend');
      div.innerHTML = `
        <b>Parking Occupancy Legend</b><br><br>
        <span style="color:red;">●</span> Above 95% full<br>
        <span style="color:orange;">●</span> 70% to 95% full<br>
        <span style="color:gold;">●</span> 40% to 70% full<br>
        <span style="color:green;">●</span> Below 40% full<br>
        <span style="color:gray;">●</span> No occupancy data<br><br>
        <b>P icon color</b> shows occupancy level
      `;
      return div;
    }};
    legend.addTo(map);
  </script>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Leaflet map saved to: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()