Here is your updated **README.md** with the dynamic-data focus clearly explained and ready to copy:

# 🚗 Parking Data Pipeline

## 📌 Objective

This project builds a **reliable and reusable dataset** for parking facilities near selected office locations in the Netherlands.
It combines **static information** (e.g. location, capacity) with **near real-time availability data**.

---

## ⚙️ Project Structure

```
parking-project/
│
├── data/
│   ├── raw/              # Raw static & dynamic data
│   └── processed/        # Cleaned & merged dataset + outputs
│
├── src/
│   ├── static_data.py    # Collect static parking data
│   ├── dynamic_data.py   # Fetch live availability (RDW API)
│   ├── prepare_data.py   # Clean & merge datasets
│   ├── analysis.py       # Generate insights
│   ├── folium_map.py     # Interactive parking map (Folium)
│   └── main.py           # Run full pipeline
│
├── notebooks/            # Optional exploration
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

Run the full pipeline:

```bash
python src/main.py
```

Then generate the interactive map:

```bash
python src/folium_map.py
```

---

## ▶️ What does this do?

The command:

```bash
python src/main.py
```

runs the **entire data pipeline end-to-end**:

### 1. Collect static data

Retrieves parking facility details:

* name
* address
* coordinates
* capacity
* opening hours

### 2. Fetch dynamic data

Pulls near real-time parking availability:

* available spaces
* total capacity
* occupancy percentage

### 3. Prepare data

* cleans inconsistent values
* standardizes column names
* merges static + dynamic datasets

### 4. Run analysis

Generates insights such as:

* average available spaces
* occupancy percentage
* open late / weekend availability
* distance to office

---

## ⚠️ Important Note on Dynamic Data

Not all parking facilities provide real-time availability data.

👉 Only a subset (±23 parking garages) exposes **dynamic data via the RDW API**.

### How this project handles it:

* `static_data.py` → collects **all parking facilities in target cities**
* `dynamic_data.py` → retrieves **only available real-time data**
* `prepare_data.py` → keeps **only parking garages with dynamic data** (inner join)

✅ This means:

* Final dataset focuses on **reliable, real-time data**
* Analysis and visualizations are based on **actual live availability**

---

## 🗺️ Interactive Parking Map

Generate the map:

```bash
python src/folium_map.py
```

### 📍 Output:

* `data/processed/parking_map.html`

Open this file in your browser.

---

## 🧠 What the map shows

The map displays **all parking garages with dynamic data (≈23 locations)**.

### 🅿️ Parking icons

Each parking facility is shown as a **“P” icon**, where:

#### 🎨 Icon color = Occupancy level

* 🔴 **Red** → more than 95% full
* 🟠 **Orange** → 70% – 95% full
* 🟡 **Yellow** → 40% – 70% full
* 🟢 **Green** → less than 40% full
* ⚪ **Gray** → no occupancy data

### 📊 Popup information

Click a parking location to see:

* 🟢 / 🔴 Open now / Closed now
* available spaces
* parking capacity
* occupancy percentage
* opening hours
* open on weekends
* open late
* distance to office

### 🏢 Office locations

* Displayed as **blue markers**
* Used to calculate distance from parking facilities

---

## 📦 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

Make sure `folium` is included:

```
folium
```

---

## 🎯 Output

The pipeline generates:

* `data/raw/static_parking.csv`
* `data/raw/dynamic_parking.csv`
* `data/processed/parking_combined.csv` *(only dynamic garages)*
* `data/processed/parking_facilities_overview.csv`
* `data/processed/parking_map.html` ⭐

---

## 💡 Key Idea

The pipeline is **modular and reusable**:

* new cities can be added easily
* additional APIs can be integrated
* outputs can be reused for dashboards or apps

It combines:

* data engineering (pipeline)
* API integration
* data analysis
* interactive visualization

