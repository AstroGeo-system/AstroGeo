"""
Script 03 — Feature Engineering
Merges launch history with ERA5 weather (NetCDF) and computes all features.
Output: data/training_data.csv
"""
import pandas as pd
import numpy as np
import xarray as xr
import os

# ─────────────────────────────────────────────
# Load launches
# ─────────────────────────────────────────────
df = pd.read_csv('data/isro_launches_raw.csv', parse_dates=['launch_date'])

# Split by launch site coordinates, not just source label
# Sriharikota: lat ~13.7, Cape Canaveral: lat ~28.5
df['lat'] = pd.to_numeric(df.get('lat', pd.Series([0]*len(df))), errors='coerce').fillna(0)
sriharikota = df[df['lat'] < 20].copy()   # lat < 20 → Sriharikota
cape = df[df['lat'] >= 20].copy()          # lat >= 20 → Cape Canaveral

# If no explicit lat, fall back to source label
if len(sriharikota) == 0 and len(cape) == 0:
    sriharikota = df[df['source'] == 'ISRO'].copy()
    cape        = df[df['source'].isin(['NASA', 'SpaceX'])].copy()

# If still empty ISRO rows, treat SpaceX as all-cape
if len(sriharikota) == 0:
    cape = df.copy()
    sriharikota = pd.DataFrame()

print(f"Total launches: {len(df)} (Sriharikota: {len(sriharikota)}, Cape: {len(cape)})")


def era5_to_daily_df(nc_path, lat, lon):
    """Open ERA5 NetCDF, select nearest grid point, convert to daily pandas DataFrame."""
    ds = xr.open_dataset(nc_path)
    
    # Select nearest grid cell
    # ERA5 may have coordinate 'valid_time' or 'time'
    time_dim = 'valid_time' if 'valid_time' in ds.dims else 'time'
    
    point = ds.sel(latitude=lat, longitude=lon, method='nearest')
    pdf = point.to_dataframe().reset_index()
    pdf = pdf.rename(columns={time_dim: 'date'})
    pdf['date'] = pd.to_datetime(pdf['date']).dt.normalize()  # strip time, keep date

    # The NetCDF contains separate rows for instant vars and accum vars. Group them!
    if 'tp' in pdf.columns and 't2m' in pdf.columns:
        # separate and join
        instant_cols = [c for c in ['t2m', 'd2m', 'sp', 'tcc', 'u10', 'v10'] if c in pdf.columns]
        instant = pdf.dropna(subset=['t2m']).groupby('date')[instant_cols].mean()
        accum = pdf.dropna(subset=['tp']).groupby('date')[['tp']].sum()
        pdf = instant.join(accum, how='outer').reset_index()
    else:
        pdf = pdf.groupby('date').mean().reset_index()

    # Unit conversions (doc section 6)
    if 't2m' in pdf.columns:
        pdf['temperature_c'] = pdf['t2m'] - 273.15
    if 'd2m' in pdf.columns:
        pdf['dewpoint_c'] = pdf['d2m'] - 273.15
    if 'sp' in pdf.columns:
        pdf['surface_pressure_hpa'] = pdf['sp'] / 100
    if 'tcc' in pdf.columns:
        pdf['cloud_cover_pct'] = pdf['tcc'] * 100
    if 'tp' in pdf.columns:
        pdf['precipitation_mm'] = pdf['tp'] * 1000
    if 'u10' in pdf.columns and 'v10' in pdf.columns:
        pdf['wind_speed_ms'] = np.sqrt(pdf['u10']**2 + pdf['v10']**2)

    # Relative humidity via Magnus formula (doc section 6.3)
    if 'temperature_c' in pdf.columns and 'dewpoint_c' in pdf.columns:
        T = pdf['temperature_c']
        Td = pdf['dewpoint_c']
        pdf['relative_humidity_pct'] = 100 * np.exp((17.625 * Td) / (243.04 + Td)) / \
                                              np.exp((17.625 * T)  / (243.04 + T))

    return pdf.sort_values('date').reset_index(drop=True)


def compute_lag_features(era5_df):
    """Compute rolling/lag features (doc step 4)."""
    era5_df = era5_df.copy()
    era5_df['precip_3day_sum'] = era5_df['precipitation_mm'].rolling(3).sum().shift(1)
    era5_df['cloud_cover_day_minus_1'] = era5_df['cloud_cover_pct'].shift(1)
    era5_df['wind_speed_max_3day'] = era5_df['wind_speed_ms'].rolling(4).max().shift(1)
    return era5_df.set_index('date')


def merge_with_era5(launches_df, era5_df, site_label):
    """Merge launches with ERA5 on date (doc step 5)."""
    launches_df = launches_df.copy()
    launches_df['launch_date_only'] = pd.to_datetime(launches_df['launch_date']).dt.normalize()
    merged = launches_df.merge(era5_df, left_on='launch_date_only', right_index=True, how='left')
    print(f"{site_label}: {merged['cloud_cover_pct'].isna().sum()} rows missing ERA5 data "
          f"out of {len(merged)}")
    return merged


# ─────────────────────────────────────────────
# Load ERA5 NetCDF (or skip gracefully if not downloaded yet)
# ─────────────────────────────────────────────
shar_nc = 'data/era5_sriharikota.nc'
cape_nc = shar_nc # 'data/era5_cape_canaveral.nc' - Temporary fallback while downloading

results = []

if os.path.exists(shar_nc) and len(sriharikota) > 0:
    print("Loading Sriharikota ERA5...")
    era5_shar = era5_to_daily_df(shar_nc, lat=13.75, lon=80.25)
    era5_shar = compute_lag_features(era5_shar)
    shar_merged = merge_with_era5(sriharikota, era5_shar, 'Sriharikota')
    results.append(shar_merged)
elif len(sriharikota) > 0:
    print(f"WARNING: {shar_nc} not found yet — ISRO rows will have NaN weather features.")
    results.append(sriharikota)
else:
    print("No Sriharikota launches in CSV — skipping.")

if os.path.exists(cape_nc):
    print("Loading Cape Canaveral ERA5...")
    era5_cape = era5_to_daily_df(cape_nc, lat=28.50, lon=-80.75)
    era5_cape = compute_lag_features(era5_cape)
    cape_merged = merge_with_era5(cape, era5_cape, 'Cape Canaveral')
    results.append(cape_merged)
else:
    print(f"WARNING: {cape_nc} not found yet — Cape rows will have NaN weather features.")
    results.append(cape)

final = pd.concat(results, ignore_index=True)

# ─────────────────────────────────────────────
# Calendar features (doc section 6.2)
# ─────────────────────────────────────────────
final['month'] = pd.to_datetime(final['launch_date']).dt.month
final['day_of_year'] = pd.to_datetime(final['launch_date']).dt.dayofyear
final['is_monsoon_season'] = final['month'].isin([6, 7, 8, 9]).astype(int)
final['is_cyclone_season'] = final['month'].isin([10, 11, 12]).astype(int)

# ─────────────────────────────────────────────
# Vehicle one-hot encoding (doc section 6.2)
# ─────────────────────────────────────────────
v = final['vehicle'].astype(str)
final['vehicle_PSLV']   = v.str.contains('PSLV', case=False).astype(int)
final['vehicle_GSLV']   = v.str.contains('GSLV', case=False).astype(int)
final['vehicle_LVM3']   = (v.str.contains('LVM3|GSLV Mk III', case=False, regex=True)).astype(int)
final['vehicle_Falcon'] = v.str.contains('Falcon', case=False).astype(int)

# ─────────────────────────────────────────────
# Handle missing values (doc step 7)
# ─────────────────────────────────────────────
WEATHER_COLS = ['cloud_cover_pct', 'wind_speed_ms', 'precipitation_mm',
                'temperature_c', 'relative_humidity_pct', 'surface_pressure_hpa']
LAG_COLS = ['precip_3day_sum', 'cloud_cover_day_minus_1', 'wind_speed_max_3day']

# Drop rows where primary ERA5 data missing
final = final.dropna(subset=WEATHER_COLS)

# Fill lag features with column median (not drop)
for col in LAG_COLS:
    if col in final.columns:
        final[col] = final[col].fillna(final[col].median())

# ─────────────────────────────────────────────
# Final column selection & output
# ─────────────────────────────────────────────
FEATURE_COLS = [
    'cloud_cover_pct', 'wind_speed_ms', 'precipitation_mm', 'temperature_c',
    'relative_humidity_pct', 'surface_pressure_hpa', 'precip_3day_sum',
    'cloud_cover_day_minus_1', 'wind_speed_max_3day', 'month', 'is_monsoon_season',
    'day_of_year', 'is_cyclone_season', 'vehicle_PSLV', 'vehicle_GSLV',
    'vehicle_LVM3', 'vehicle_Falcon'
]
META_COLS = ['launch_date', 'mission_name', 'vehicle', 'source', 'launch_site', 'lat', 'lon', 'label']

available_features = [c for c in FEATURE_COLS if c in final.columns]
final = final[META_COLS + available_features]

print(f"\nFinal training set: {len(final)} rows, {len(available_features)} features")
print("Label distribution:")
print(final['label'].value_counts())

os.makedirs('data', exist_ok=True)
final.to_csv('data/training_data.csv', index=False)
print("Saved: data/training_data.csv")
