import sqlite3
import random
from datetime import datetime, timedelta

DB_FILE = "argo_data.db"

def seed_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Drop existing tables if re-seeding
    cursor.execute("DROP VIEW IF EXISTS argo_data_view;")
    cursor.execute("DROP TABLE IF EXISTS measurements;")
    cursor.execute("DROP TABLE IF EXISTS profiles;")
    cursor.execute("DROP TABLE IF EXISTS floats;")

    # 1. Create floats table
    cursor.execute("""
    CREATE TABLE floats (
        wmo_id TEXT PRIMARY KEY,
        region TEXT NOT NULL,
        deployment_date TEXT NOT NULL,
        is_bgc INTEGER DEFAULT 0
    );
    """)

    # 2. Create profiles table
    cursor.execute("""
    CREATE TABLE profiles (
        profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
        wmo_id TEXT NOT NULL,
        cycle_number INTEGER NOT NULL,
        profile_date TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        FOREIGN KEY (wmo_id) REFERENCES floats(wmo_id)
    );
    """)

    # 3. Create measurements table
    cursor.execute("""
    CREATE TABLE measurements (
        measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        depth_m REAL NOT NULL,
        temperature REAL NOT NULL,
        salinity REAL NOT NULL,
        qc_flag INTEGER NOT NULL DEFAULT 1,
        chlorophyll REAL,
        FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
    );
    """)

    # 8 ARGO Floats definition with regions and BGC capabilities
    floats_data = [
        ("2901551", "Arabian Sea", "2024-01-02", 0, 18.5, 64.0),
        ("2901552", "Arabian Sea", "2024-01-05", 1, 12.0, 68.5),  # BGC float
        ("2901553", "Bay of Bengal", "2024-01-03", 0, 17.0, 87.0),
        ("2901554", "Bay of Bengal", "2024-01-08", 1, 10.5, 85.5),  # BGC float
        ("2901555", "Equatorial Indian Ocean", "2024-01-04", 1, 1.2, 72.0), # Equator BGC float
        ("2901556", "Equatorial Indian Ocean", "2024-01-10", 0, -1.5, 88.0), # Equator float
        ("2901557", "Southern Ocean", "2024-01-06", 0, -12.0, 62.5),
        ("2901558", "Southern Ocean", "2024-01-12", 0, -14.5, 82.0),
    ]

    for wmo_id, region, dep_date, is_bgc, base_lat, base_lon in floats_data:
        cursor.execute(
            "INSERT INTO floats (wmo_id, region, deployment_date, is_bgc) VALUES (?, ?, ?, ?)",
            (wmo_id, region, dep_date, is_bgc)
        )

        # Base surface temperature according to region
        if region == "Arabian Sea":
            base_surf_temp = 28.5
            base_salinity = 36.2  # Higher evaporation
        elif region == "Bay of Bengal":
            base_surf_temp = 29.0
            base_salinity = 33.8  # River runoff lowers surface salinity
        elif region == "Equatorial Indian Ocean":
            base_surf_temp = 29.5
            base_salinity = 35.0
        else:  # Southern Ocean (subtropical)
            base_surf_temp = 26.5
            base_salinity = 35.4

        start_date = datetime.strptime(dep_date, "%Y-%m-%d")
        num_cycles = 8  # 8 profiles per float

        for cycle in range(1, num_cycles + 1):
            prof_date = start_date + timedelta(days=(cycle - 1) * 10)
            date_str = prof_date.strftime("%Y-%m-%d %H:%M:%S")

            # Slight drift in location for each cycle
            lat = round(base_lat + (cycle * 0.15) + random.uniform(-0.05, 0.05), 4)
            lon = round(base_lon + (cycle * 0.20) + random.uniform(-0.05, 0.05), 4)

            cursor.execute(
                "INSERT INTO profiles (wmo_id, cycle_number, profile_date, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
                (wmo_id, cycle, date_str, lat, lon)
            )
            profile_id = cursor.lastrowid

            # Standard depth levels (15 levels)
            depth_levels = [0.0, 10.0, 20.0, 50.0, 75.0, 100.0, 150.0, 200.0, 300.0, 400.0, 500.0, 750.0, 1000.0, 1500.0, 2000.0]

            # Seasonal variation for January-June
            month_factor = (prof_date.month - 1) * 0.3
            current_surf_temp = base_surf_temp + month_factor + random.uniform(-0.3, 0.3)

            for depth in depth_levels:
                # Realistic thermocline model: fast drop between 50m and 500m
                if depth == 0:
                    temp = current_surf_temp
                    sal = base_salinity + random.uniform(-0.1, 0.1)
                elif depth <= 50:
                    temp = current_surf_temp - (depth * 0.02) + random.uniform(-0.1, 0.1)
                    sal = base_salinity + random.uniform(-0.1, 0.1)
                elif depth <= 200:
                    # Rapid decrease
                    temp = current_surf_temp - 1.0 - ((depth - 50) * 0.08) + random.uniform(-0.2, 0.2)
                    sal = base_salinity + 0.3 - ((depth - 50) * 0.003)
                elif depth <= 500:
                    temp = 13.0 - ((depth - 200) * 0.02) + random.uniform(-0.1, 0.1)
                    sal = 35.0 - ((depth - 200) * 0.001)
                else: # Deep ocean (500m to 2000m)
                    temp = 7.0 - ((depth - 500) * 0.002) + random.uniform(-0.05, 0.05)
                    sal = 34.8 + random.uniform(-0.05, 0.05)

                temp = round(max(temp, 3.2), 2)
                sal = round(sal, 2)

                # QC Flags: 1 (Good, ~90%), 2 (Probably Good, ~5%), 3 (Bad, ~3%), 4 (Bad/Spike, ~2%)
                qc_rand = random.random()
                if qc_rand < 0.90:
                    qc_flag = 1
                elif qc_rand < 0.95:
                    qc_flag = 2
                elif qc_rand < 0.98:
                    qc_flag = 3
                    temp += random.choice([-5.0, 8.0])  # Anomaly/spike
                else:
                    qc_flag = 4
                    sal += random.choice([-2.0, 3.0])  # Anomaly/spike

                # Chlorophyll (BGC floats only, surface to 150m depth)
                chlorophyll = None
                if is_bgc and depth <= 150:
                    # Maximum near 50m (deep chlorophyll maximum)
                    if depth == 50.0:
                        chlorophyll = round(random.uniform(1.2, 2.4), 3)
                    elif depth in [20.0, 75.0]:
                        chlorophyll = round(random.uniform(0.6, 1.3), 3)
                    elif depth in [0.0, 10.0]:
                        chlorophyll = round(random.uniform(0.3, 0.8), 3)
                    else:
                        chlorophyll = round(random.uniform(0.1, 0.4), 3)

                cursor.execute("""
                INSERT INTO measurements (profile_id, depth_m, temperature, salinity, qc_flag, chlorophyll)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (profile_id, depth, temp, sal, qc_flag, chlorophyll))

    # 4. Create View for convenient flattened queries
    cursor.execute("""
    CREATE VIEW argo_data_view AS
    SELECT 
        f.wmo_id,
        f.region,
        f.is_bgc,
        p.profile_id,
        p.cycle_number,
        p.profile_date,
        p.latitude,
        p.longitude,
        m.measurement_id,
        m.depth_m,
        m.temperature,
        m.salinity,
        m.qc_flag,
        m.chlorophyll
    FROM floats f
    JOIN profiles p ON f.wmo_id = p.wmo_id
    JOIN measurements m ON p.profile_id = m.profile_id;
    """)

    conn.commit()
    
    # Print summary
    cursor.execute("SELECT COUNT(*) FROM floats;")
    float_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM profiles;")
    prof_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM measurements;")
    meas_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM measurements WHERE qc_flag IN (3,4);")
    bad_qc_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM measurements WHERE chlorophyll IS NOT NULL;")
    bgc_count = cursor.fetchone()[0]

    print(f"Successfully seeded {DB_FILE}:")
    print(f"  - Floats: {float_count}")
    print(f"  - Profiles: {prof_count}")
    print(f"  - Measurements: {meas_count} (Good QC 1-2: {meas_count - bad_qc_count}, Questionable/Bad QC 3-4: {bad_qc_count})")
    print(f"  - Chlorophyll measurements: {bgc_count}")

    conn.close()

if __name__ == "__main__":
    seed_database()
