from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from static_data import main as run_static_data
from dynamic_data import main as run_dynamic_data
from prepare_data import main as run_prepare_data
from analysis import main as run_analysis

# =========================
# CONFIG
# =========================

DATA_FILE = Path("data/processed/parking_facilities_overview.csv")
TIMEZONE = ZoneInfo("Europe/Amsterdam")


# =========================
# PIPELINE
# =========================

def refresh_live_data():
    # run_static_data()
    run_dynamic_data()
    run_prepare_data()
    run_analysis()


# =========================
# DATA
# =========================

@st.cache_data(show_spinner=False)
def load_data(file_mtime: float) -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)

    numeric_cols = [
        "distance_km",
        "available_spaces",
        "parking_capacity",
        "occupancy_pct",
        "latitude",
        "longitude",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "free_pct" not in df.columns:
        df["free_pct"] = (df["available_spaces"] / df["parking_capacity"]) * 100

    return df


def get_file_mtime() -> float:
    if DATA_FILE.exists():
        return DATA_FILE.stat().st_mtime
    return 0.0


def get_last_updated_text() -> str:
    if not DATA_FILE.exists():
        return "No data file found yet."

    ts = DATA_FILE.stat().st_mtime
    dt = datetime.fromtimestamp(ts, tz=TIMEZONE)
    return dt.strftime("%d %B %Y at %H:%M:%S")


def recommend_top3(df: pd.DataFrame, office: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    office_df = df[df["matched_office"] == office].copy()
    office_df = office_df[office_df["distance_km"].notna() & office_df["occupancy_pct"].notna()].copy()

    under70 = (
        office_df[office_df["occupancy_pct"] < 70]
        .sort_values(["distance_km", "occupancy_pct"], ascending=[True, True])
        .head(3)
    )

    over70 = (
        office_df[office_df["occupancy_pct"] >= 70]
        .sort_values(["distance_km", "occupancy_pct"], ascending=[True, True])
        .head(3)
    )

    return under70, over70


# =========================
# HELPERS
# =========================

def fmt(x, d=1, fallback="N/A"):
    if pd.isna(x):
        return fallback
    try:
        return f"{float(x):.{d}f}"
    except Exception:
        return fallback


def google_maps_url(row: pd.Series) -> str:
    if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
        return f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"

    if pd.notna(row.get("office_lat")) and pd.notna(row.get("office_lon")):
        return f"https://www.google.com/maps/search/?api=1&query={row['office_lat']},{row['office_lon']}"

    query = quote(str(row.get("facility_name", "")))
    return f"https://www.google.com/maps/search/?api=1&query={query}"


# =========================
# EMAIL
# =========================

def build_email_content(office: str, under70: pd.DataFrame, over70: pd.DataFrame) -> str:
    now = datetime.now(TIMEZONE)
    date_str = now.strftime("%d %B %Y")
    time_str = now.strftime("%H:%M")

    lines = [
        "Hi,",
        "",
        f"Here are the best parking options for {office} today ({date_str}) at {time_str}.",
        "",
        "Top 3 under 70% occupancy:",
    ]

    if under70.empty:
        lines.append("- No good options found")
    else:
        for i, (_, row) in enumerate(under70.iterrows(), 1):
            lines.extend([
                f"{i}. {row['facility_name']}",
                f"Distance: {fmt(row['distance_km'], 2)} km",
                f"Free spaces: {fmt(row['free_pct'])}%",
                f"Occupancy: {fmt(row['occupancy_pct'])}%",
                f"Available spots: {fmt(row['available_spaces'], 0)}",
                f"Maps: {google_maps_url(row)}",
                "",
            ])

    lines.append("Top 3 closest (busy options):")

    if over70.empty:
        lines.append("- No options found")
    else:
        for i, (_, row) in enumerate(over70.iterrows(), 1):
            lines.extend([
                f"{i}. {row['facility_name']}",
                f"Distance: {fmt(row['distance_km'], 2)} km",
                f"Free spaces: {fmt(row['free_pct'])}%",
                f"Occupancy: {fmt(row['occupancy_pct'])}%",
                f"Available spots: {fmt(row['available_spaces'], 0)}",
                f"Maps: {google_maps_url(row)}",
                "",
            ])

    lines.append("Best regards,")
    lines.append("Parking App 🚗")

    return "\n".join(lines)


def build_mailto_link(email: str, subject: str, body: str) -> str:
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"


# =========================
# UI
# =========================

def show_table(title: str, df: pd.DataFrame):
    st.subheader(title)

    if df.empty:
        st.info("No options found.")
        return

    for i, (_, row) in enumerate(df.iterrows(), 1):
        st.markdown(f"### {i}. {row['facility_name']}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Distance", f"{fmt(row['distance_km'], 2)} km")
        c2.metric("Free %", f"{fmt(row['free_pct'])}%")
        c3.metric("Occupancy", f"{fmt(row['occupancy_pct'])}%")

        c4, c5 = st.columns(2)
        c4.metric("Available", fmt(row["available_spaces"], 0))
        c5.metric("Capacity", fmt(row["parking_capacity"], 0))

        maps_url = google_maps_url(row)
        st.markdown(
            f'<a href="{maps_url}" target="_blank">'
            f'<button style="background-color:#4CAF50;color:white;padding:8px 16px;border:none;border-radius:5px;cursor:pointer;">'
            f'🧭 Navigate now</button></a>',
            unsafe_allow_html=True,
        )

        st.divider()


# =========================
# APP
# =========================

def main():
    st.set_page_config(page_title="Parking App", page_icon="🅿️", layout="centered")
    st.title("🅿️ Smart Parking Finder")

    top1, top2 = st.columns([2, 1])

    with top1:
        st.caption(f"Last updated: {get_last_updated_text()}")

    with top2:
        if st.button("🔄 Refresh live data"):
            with st.spinner("Fetching latest parking data..."):
                try:
                    refresh_live_data()
                    load_data.clear()
                    st.success("Live data refreshed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Refresh failed: {e}")

    file_mtime = get_file_mtime()

    if file_mtime == 0:
        st.warning("No data file found yet. Click 'Refresh live data' first.")
        return

    try:
        df = load_data(file_mtime)
    except Exception as e:
        st.error(f"Could not load data: {e}")
        return

    if df.empty:
        st.warning("The parking dataset is empty.")
        return

    offices = sorted(df["matched_office"].dropna().unique().tolist())
    if not offices:
        st.warning("No offices found in dataset.")
        return

    office = st.selectbox("Select office", offices)

    under70, over70 = recommend_top3(df, office)

    st.divider()
    show_table("Top 3 best options (<70%)", under70)

    st.divider()
    show_table("Top 3 closest busy options (>=70%)", over70)

    st.divider()
    st.subheader("📧 Send recommendation")

    email = st.text_input("Client email")

    if st.button("Generate email"):
        if not email:
            st.warning("Enter an email first.")
            return

        subject = f"Parking recommendation for {office}"
        body = build_email_content(office, under70, over70)
        mailto_link = build_mailto_link(email, subject, body)

        st.success("Click below to open your email client:")
        st.markdown(f"[📨 Open email]({mailto_link})")


if __name__ == "__main__":
    main()