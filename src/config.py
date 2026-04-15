from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

INDEX_URL = "https://npropendata.rdw.nl/parkingdata/v2/"

STATIC_FILE = RAW_DIR / "static_parking.csv"
DYNAMIC_FILE = RAW_DIR / "dynamic_parking.csv"
COMBINED_FILE = PROCESSED_DIR / "parking_combined.csv"
OVERVIEW_FILE = PROCESSED_DIR / "parking_facilities_overview.csv"

OFFICES = [
    {
        "office_name": "Gemeente Breda",
        "city": "Breda",
        "address": "Claudius Prinsenlaan 10, 4811 DJ Breda",
        "lat": 51.5719,
        "lon": 4.7683,
    },
    {
        "office_name": "Gemeente Utrecht",
        "city": "Utrecht",
        "address": "Stadsplateau 1, 3521 AZ Utrecht",
        "lat": 52.0907,
        "lon": 5.1214,
    },
    {
        "office_name": "TenneT",
        "city": "Arnhem",
        "address": "Utrechtseweg 310, 6812 AR Arnhem",
        "lat": 51.9851,
        "lon": 5.8987,
    },
    {
        "office_name": "Gemeente Zwolle",
        "city": "Zwolle",
        "address": "Grote Kerkplein 15, 8011 PK Zwolle",
        "lat": 52.5168,
        "lon": 6.0830,
    },
]

TARGET_CITIES = [office["city"] for office in OFFICES]