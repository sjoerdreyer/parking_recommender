import pandas as pd

from config import COMBINED_FILE, DYNAMIC_FILE, STATIC_FILE


def clean_columns(df):
    df.columns = [col.strip().lower() for col in df.columns]
    return df


def main():
    print("Preparing and merging data...")

    try:
        static_df = pd.read_csv(STATIC_FILE)
    except FileNotFoundError:
        print("Static file not found.")
        return

    try:
        dynamic_df = pd.read_csv(DYNAMIC_FILE)
    except FileNotFoundError:
        print("Dynamic file not found.")
        return

    if static_df.empty:
        print("Static dataset is empty.")
        return

    if dynamic_df.empty:
        print("Dynamic dataset is empty.")
        return

    static_df = clean_columns(static_df)
    dynamic_df = clean_columns(dynamic_df)

    if "parking_id" not in static_df.columns or "parking_id" not in dynamic_df.columns:
        print("parking_id column missing in one of the files.")
        return

    # Keep only parking garages that have dynamic data
    combined_df = pd.merge(
        static_df,
        dynamic_df,
        on="parking_id",
        how="inner",
        suffixes=("_static", "_dynamic"),
    )

    # Keep clean coordinate columns for downstream files
    if "latitude" not in combined_df.columns and "latitude_static" in combined_df.columns:
        combined_df["latitude"] = combined_df["latitude_static"]

    if "longitude" not in combined_df.columns and "longitude_static" in combined_df.columns:
        combined_df["longitude"] = combined_df["longitude_static"]

    combined_df["latitude"] = pd.to_numeric(combined_df.get("latitude"), errors="coerce")
    combined_df["longitude"] = pd.to_numeric(combined_df.get("longitude"), errors="coerce")

    combined_df = combined_df.drop_duplicates()

    combined_df.to_csv(COMBINED_FILE, index=False)

    print(f"Saved combined data to: {COMBINED_FILE}")
    print(f"Rows saved: {len(combined_df)}")
    print(f"Rows with latitude: {combined_df['latitude'].notna().sum()}")
    print(f"Rows with longitude: {combined_df['longitude'].notna().sum()}")
    print(combined_df.head())


if __name__ == "__main__":
    main()