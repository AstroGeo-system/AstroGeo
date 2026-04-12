# 02_fetch_era5.py
# Pulls 7 weather variables for Sriharikota + Cape Canaveral
# from 1980 to present via Copernicus CDS API.
# Runtime: 6–12 hours. Run in background.

import cdsapi
import os
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

# ── Config ────────────────────────────────────────────────────
LAUNCH_SITES = {
    'sriharikota': {
        'lat': 13.7199,
        'lon': 80.2304,
        'area': [14.5, 79.5, 13.0, 81.0],  # N, W, S, E
    },
    'cape_canaveral': {
        'lat': 28.3922,
        'lon': -80.6077,
        'area': [29.5, -81.5, 27.5, -79.5],
    },
}

VARIABLES = [
    '2m_temperature',
    'surface_pressure',
    '2m_dewpoint_temperature',      # → relative humidity proxy
    '10m_u_component_of_wind',
    '10m_v_component_of_wind',
    'total_precipitation',
    'total_cloud_cover',
]

START_YEAR = 1980
END_YEAR   = datetime.now().year

OUTPUT_DIR = 'data/era5'
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── CDS Client ────────────────────────────────────────────────
def get_cds_client():
    # Reads from ~/.cdsapirc or CDS_API_KEY env var
    api_key = os.getenv('CDS_API_KEY')
    api_url = os.getenv('CDS_API_URL', 'https://cds.climate.copernicus.eu/api/v2')

    if api_key:
        return cdsapi.Client(url=api_url, key=api_key)
    else:
        return cdsapi.Client()  # falls back to ~/.cdsapirc


# ── Download one site one year ────────────────────────────────
def download_site_year(client, site_name, site_config, year):
    output_file = f"{OUTPUT_DIR}/{site_name}_{year}.nc"

    if os.path.exists(output_file):
        print(f"  [SKIP] {site_name} {year} already downloaded")
        return output_file

    print(f"  [DOWNLOAD] {site_name} {year}...")

    client.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'variable':     VARIABLES,
            'year':         str(year),
            'month':        [f"{m:02d}" for m in range(1, 13)],
            'day':          [f"{d:02d}" for d in range(1, 32)],
            'time':         ['06:00', '12:00', '18:00'],  # 3 snapshots/day
            'area':         site_config['area'],
            'format':       'netcdf',
        },
        output_file
    )
    print(f"  [DONE] {site_name} {year} → {output_file}")
    return output_file


# ── Parse NetCDF → daily DataFrame ───────────────────────────
def parse_netcdf_to_daily(nc_file, site_name, site_config):
    import xarray as xr
    import zipfile
    import shutil
    import os

    if zipfile.is_zipfile(nc_file):
        print(f"  [ZIP] Extracting and merging data from {nc_file}...")
        temp_dir = os.path.join(os.path.dirname(nc_file), f"tmp_{os.path.basename(nc_file)}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        with zipfile.ZipFile(nc_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        nc_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.nc')]
        datasets = []
        for f in nc_files:
            tmp_ds = xr.open_dataset(f)
            # Newer API uses 'valid_time', script expects 'time'
            if 'valid_time' in tmp_ds.coords:
                tmp_ds = tmp_ds.rename({'valid_time': 'time'})
            # Drop 'expver' if present to avoid merge conflicts
            if 'expver' in tmp_ds.coords:
                tmp_ds = tmp_ds.drop_vars('expver')
            datasets.append(tmp_ds)

        ds = xr.merge(datasets)
        ds.load()  # Load into memory before cleaning up files
        shutil.rmtree(temp_dir)
    else:
        ds = xr.open_dataset(nc_file)
        if 'valid_time' in ds.coords:
            ds = ds.rename({'valid_time': 'time'})
        if 'expver' in ds.coords:
            ds = ds.drop_vars('expver')

    lat = site_config['lat']
    lon = site_config['lon']

    # Select nearest grid point to launch site
    ds_point = ds.sel(
        latitude=lat,
        longitude=lon,
        method='nearest'
    )

    df = ds_point.to_dataframe().reset_index()

    # Rename ERA5 variable names
    rename_map = {
        't2m':   'temperature_k',
        'sp':    'pressure_pa',
        'd2m':   'dewpoint_k',
        'u10':   'wind_u',
        'v10':   'wind_v',
        'tp':    'precipitation_m',
        'tcc':   'cloud_cover',
    }
    df = df.rename(columns={
        k: v for k, v in rename_map.items() if k in df.columns
    })

    # Derived features
    if 'temperature_k' in df.columns:
        df['temperature_c'] = df['temperature_k'] - 273.15

    if 'wind_u' in df.columns and 'wind_v' in df.columns:
        df['wind_speed'] = np.sqrt(df['wind_u']**2 + df['wind_v']**2)

    if 'dewpoint_k' in df.columns and 'temperature_k' in df.columns:
        # Magnus formula approximation for relative humidity
        T  = df['temperature_k'] - 273.15
        Td = df['dewpoint_k'] - 273.15
        df['humidity_pct'] = 100 * np.exp(
            (17.625 * Td) / (243.04 + Td) -
            (17.625 * T)  / (243.04 + T)
        )

    if 'precipitation_m' in df.columns:
        df['precipitation_mm'] = df['precipitation_m'] * 1000

    # Aggregate to daily
    df['date'] = pd.to_datetime(df['time']).dt.date
    daily = df.groupby('date').agg({
        'temperature_c':   'mean',
        'pressure_pa':     'mean',
        'humidity_pct':    'mean',
        'wind_speed':      'mean',
        'precipitation_mm': 'sum',
        'cloud_cover':     'mean',
    }).reset_index()

    daily['launch_site'] = site_name
    daily['year']        = pd.to_datetime(daily['date']).dt.year

    # Monsoon flag (June–September)
    daily['month']         = pd.to_datetime(daily['date']).dt.month
    daily['is_monsoon']    = daily['month'].between(6, 9).astype(int)
    daily['is_cyclone']    = daily['month'].isin([10, 11, 4, 5]).astype(int)

    return daily


# ── Save to PostgreSQL ────────────────────────────────────────
def save_to_postgres(df):
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
    )
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS era5_weather (
            id              SERIAL PRIMARY KEY,
            launch_site     TEXT,
            date            DATE,
            year            INTEGER,
            month           INTEGER,
            temperature_c   FLOAT,
            pressure_pa     FLOAT,
            humidity_pct    FLOAT,
            wind_speed      FLOAT,
            precipitation_mm FLOAT,
            cloud_cover     FLOAT,
            is_monsoon      INTEGER,
            is_cyclone      INTEGER,
            UNIQUE(launch_site, date)
        )
    """)

    rows = [
        (
            row['launch_site'], row['date'], row['year'], row['month'],
            row.get('temperature_c'),  row.get('pressure_pa'),
            row.get('humidity_pct'),   row.get('wind_speed'),
            row.get('precipitation_mm'), row.get('cloud_cover'),
            row.get('is_monsoon', 0),  row.get('is_cyclone', 0),
        )
        for _, row in df.iterrows()
    ]

    execute_values(cur, """
        INSERT INTO era5_weather (
            launch_site, date, year, month,
            temperature_c, pressure_pa, humidity_pct,
            wind_speed, precipitation_mm, cloud_cover,
            is_monsoon, is_cyclone
        ) VALUES %s
        ON CONFLICT (launch_site, date) DO NOTHING
    """, rows)

    conn.commit()
    cur.close()
    conn.close()
    print(f"  [DB] Saved {len(rows)} rows to era5_weather")


# ── Main ──────────────────────────────────────────────────────
def main():
    client = get_cds_client()
    total_saved = 0

    for site_name, site_config in LAUNCH_SITES.items():
        print(f"\n{'='*50}")
        print(f"Site: {site_name.upper()}")
        print(f"{'='*50}")

        for year in range(START_YEAR, END_YEAR + 1):
            try:
                nc_file = download_site_year(
                    client, site_name, site_config, year
                )
                daily_df = parse_netcdf_to_daily(
                    nc_file, site_name, site_config
                )
                save_to_postgres(daily_df)
                total_saved += len(daily_df)
                print(f"  [OK] {site_name} {year}: {len(daily_df)} days")

            except Exception as e:
                print(f"  [ERROR] {site_name} {year}: {e}")
                continue

    print(f"\n✅ ERA5 download complete. Total rows saved: {total_saved}")


if __name__ == '__main__':
    # Install deps if needed:
    # pip install cdsapi xarray netCDF4 psycopg2-binary
    main()