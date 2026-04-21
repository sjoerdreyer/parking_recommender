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
    return dt.strftime("%d %B %Y · %H:%M:%S")


def recommend_top3(df: pd.DataFrame, office: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    office_df = df[df["matched_office"] == office].copy()
    office_df = office_df[office_df["distance_km"].notna() & office_df["occupancy_pct"].notna()].copy()

    under50 = (
        office_df[office_df["occupancy_pct"] < 50]
        .sort_values(["distance_km", "occupancy_pct"], ascending=[True, True])
        .head(3)
    )

    over50 = (
        office_df[office_df["occupancy_pct"] >= 50]
        .sort_values(["distance_km", "occupancy_pct"], ascending=[True, True])
        .head(3)
    )

    return under50, over50


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


def occupancy_badge_color(occupancy):
    if pd.isna(occupancy):
        return "#9CA3AF"
    if occupancy > 95:
        return "#EF4444"
    if occupancy >= 50:
        return "#F97316"
    if occupancy >= 40:
        return "#EAB308"
    return "#22C55E"


def build_mailto_link(email: str, subject: str, body: str) -> str:
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"


def build_email_content(office: str, under50: pd.DataFrame, over50: pd.DataFrame) -> str:
    now = datetime.now(TIMEZONE)
    date_str = now.strftime("%d %B %Y")
    time_str = now.strftime("%H:%M")

    lines = [
        "Hi,",
        "",
        f"Here are the best parking options for {office} today ({date_str}) at {time_str}.",
        "",
        "Top 3 under 50% occupancy:",
    ]

    if under50.empty:
        lines.append("- No good options found")
    else:
        for i, (_, row) in enumerate(under50.iterrows(), 1):
            lines.extend([
                f"{i}. {row['facility_name']}",
                f"Distance: {fmt(row['distance_km'], 2)} km",
                f"Free parking: {fmt(row['free_pct'])}%",
                f"Occupancy: {fmt(row['occupancy_pct'])}%",
                f"Available spots: {fmt(row['available_spaces'], 0)}",
                f"Maps: {google_maps_url(row)}",
                "",
            ])

    lines.append("Top 3 closest busy options:")

    if over50.empty:
        lines.append("- No options found")
    else:
        for i, (_, row) in enumerate(over50.iterrows(), 1):
            lines.extend([
                f"{i}. {row['facility_name']}",
                f"Distance: {fmt(row['distance_km'], 2)} km",
                f"Free parking: {fmt(row['free_pct'])}%",
                f"Occupancy: {fmt(row['occupancy_pct'])}%",
                f"Available spots: {fmt(row['available_spaces'], 0)}",
                f"Maps: {google_maps_url(row)}",
                "",
            ])

    lines.extend([
        "Best regards,",
        "Parking App 🚗",
    ])

    return "\n".join(lines)


# =========================
# STYLING
# =========================
def inject_mobile_css():
    st.markdown(
        """
        <style>
        header[data-testid="stHeader"] {
            display: none;
        }
        
        .stLinkButton a {
    background-color: #16A34A !important;
    color: white !important;
    border-radius: 12px !important;
    font-weight: 699 !important;
    border: none !important;
}

        .stLinkButton a:hover {
            background-color: #15803D !important;
            color: white !important;
        }
        .stApp {
            background: #DDE3EA;
        }

        .block-container {
            max-width: 430px;
            padding-top: 0.8rem;
            padding-bottom: 4rem;
        }

        .mobile-shell {
            background: white;
            border-radius: 28px;
            padding: 18px 16px 22px 16px;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.12);
            border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .app-title {
            font-size: 1.7rem;
            font-weight: 800;
            line-height: 1.1;
            color: #0F172A;
            margin-bottom: 0.25rem;
        }

        .app-subtitle {
            color: #64748B;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }

       .small-pill {
            display: inline-block;
            background: #EEF2FF;
            color: #3730A3;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin-bottom: 0.45rem;
        }

        .section-title {
            font-size: 1rem;
            font-weight: 800;
            color: #0F172A;
            margin: 1rem 0 0.7rem 0;
        }

        .parking-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 20px;
            padding: 16px;
            margin-bottom: 14px;

            box-shadow: 
                0 2px 6px rgba(0,0,0,0.04),
                0 10px 24px rgba(0,0,0,0.06);
        }

        .parking-name {
            font-weight: 800;
            font-size: 1rem;
            color: #0F172A;
            margin-bottom: 8px;
        }

            .badge {
                display: inline-block;
                color: white;
                font-weight: 800;
                font-size: 1rem;
                padding: 10px 16px;
                border-radius: 999px;
                margin-bottom: 18px;
            }

        .mini-text {
            color: #64748B;
            font-size: 0.8rem;
            margin-top: 8px;
        }

        .nav-btn a, .email-btn a {
            text-decoration: none !important;
        }

        .nav-btn button, .email-btn button {
            width: 100%;
            border: none;
            border-radius: 14px;
            padding: 12px 14px;
            font-weight: 699;
            cursor: pointer;
        }

        .nav-btn button {
            background: #16A34A;
            color: white;
            margin-top: 10px;
        }

        .email-btn button {
            background: #2563EB;
            color: white;
            margin-top: 8px;
        }

        div[data-testid="stSelectbox"] > label,
        div[data-testid="stTextInput"] > label {
            font-weight: 699;
            color: #0F172A;
        }


        .stButton > button {
    width: auto;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.78rem;
    padding: 0.45rem 0.9rem;
}

        </style>
        """,
        unsafe_allow_html=True,
    )
    
    
    
# =========================
# UI
# =========================


def render_card(row: pd.Series, rank: int):
    badge_color = occupancy_badge_color(row.get("occupancy_pct"))
    maps_url = google_maps_url(row)

    with st.container(border=True):
        st.markdown(
            f'<div class="parking-name">{rank}. {row["facility_name"]}</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style="
                display:inline-block;
                background:{badge_color};
                color:white;
                font-weight:800;
                font-size:1rem;
                padding:8px 14px;
                border-radius:999px;
                margin-bottom:14px;
            ">
                {fmt(row["occupancy_pct"])}% full
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.markdown(
                f"""
                <div style="color:#374151; font-size:0.95rem; font-weight:600;">
                    Available spots
                </div>
                <div style="color:#111827; font-size:2.8rem; font-weight:800; line-height:1;">
                    {fmt(row["available_spaces"], 0)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.write("")
            st.write("")
            st.link_button("🌍 Navigate", maps_url, use_container_width=True)
    


def show_cards(title: str, df: pd.DataFrame):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No options found.")
        return

    for i, (_, row) in enumerate(df.iterrows(), 1):
        render_card(row, i)


# =========================
# APP
# =========================

def main():
    st.set_page_config(page_title="Parking App", page_icon="🅿️", layout="centered")
    inject_mobile_css()

    st.markdown('<div class="app-title">🅿️ Smart Parking Finder</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Live recommendations for office parking.</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="small-pill">Last updated: {get_last_updated_text()}</div>',
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh to latest live data"):
        with st.spinner("Fetching latest parking data..."):
            try:
                refresh_live_data()
                load_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Refresh failed: {e}")

    file_mtime = get_file_mtime()
    if file_mtime == 0:
        st.warning("No data file found yet. Click Refresh first.")
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

    office = st.selectbox("Choose office", offices)

    under50, over50 = recommend_top3(df, office)

    show_cards("Best options under 50%", under50)
    show_cards("Closest busy options", over50)

    # st.markdown('<div class="section-title">📧 Share recommendation</div>', unsafe_allow_html=True)
    # email = st.text_input("", placeholder="example@company.com")

    # if st.button("Generate email"):
    #     if not email:
    #         st.warning("Enter an email first.")
    #     else:
    #         subject = f"Parking recommendation for {office}"
    #         body = build_email_content(office, under50, over50)
    #         mailto_link = build_mailto_link(email, subject, body)

    #         st.markdown(
    #             f"""
    #             <a href="{mailto_link}">
    #                 <button style="background-color:#2563EB;color:white;border:none;padding:12px 14px;border-radius:14px;font-weight:500;width:100%;cursor:pointer;">
    #                     📨 Open email
    #                 </button>
    #             </a>
    #             """,
    #             unsafe_allow_html=True,
    #         )



if __name__ == "__main__":
    main()