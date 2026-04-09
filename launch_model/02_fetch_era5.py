"""
Script 02 — Fetch ERA5 Weather (OPTIMIZED)
Uses the reanalysis-era5-single-levels-timeseries endpoint which is
designed for single-point, long-period time-series and is ~10x faster.
Output: data/era5_sriharikota.nc, data/era5_cape_canaveral.nc
"""
import cdsapi
import os
from datetime import datetime

os.makedirs('data', exist_ok=True)

VARIABLES = [
    '2m_dewpoint_temperature',
    '2m_temperature',
    'surface_pressure',
    'total_cloud_cover',
    'total_precipitation',
    '10m_u_component_of_wind',
    '10m_v_component_of_wind',
]

LOCATIONS = {
    'sriharikota': {
        'location': {'lat': 13.7199, 'lon': 80.2304}
    },
    'cape_canaveral': {
        'location': {'lat': 28.5721, 'lon': -80.6480}
    }
}

def fetch_era5_timeseries(location_name, location_params):
    print(f"\n--- Fetching ERA5 timeseries for {location_name} ---")
    c = cdsapi.Client()
    
    output_file = f"data/era5_{location_name}.nc"
    
    if os.path.exists(output_file):
        print(f"File {output_file} already exists — skipping.")
        return

    current_year = datetime.now().year

    try:
        # Use the ARCO timeseries endpoint — single request for ALL years
        # This is orders of magnitude faster for point queries
        c.retrieve(
            'reanalysis-era5-single-levels-timeseries',
            {
                'product_type': 'reanalysis',
                'variable': VARIABLES,
                'date': f'1990-01-01/to/{current_year}-12-31',
                'time': '12:00',
                **location_params,
                'format': 'netcdf',
            },
            output_file
        )
        print(f"Successfully downloaded {output_file}")
    except Exception as e:
        print(f"Timeseries API failed: {e}")
        print("Falling back to chunked grid download (slow)...")
        _fetch_era5_chunked(location_name, output_file, c, current_year)


def _fetch_era5_chunked(location_name, output_file, c, current_year):
    """Fallback: chunked single-levels download when timeseries API is unavailable."""
    import xarray as xr

    BBOXES = {
        'sriharikota': [13.75, 80.25, 13.75, 80.25],
        'cape_canaveral': [28.50, -80.75, 28.50, -80.75]
    }
    bbox = BBOXES[location_name]

    chunk_files = []
    for year in range(1990, current_year + 1):
        chunk_file = f"data/era5_{location_name}_{year}.nc"
        chunk_files.append(chunk_file)
        if os.path.exists(chunk_file):
            print(f"  {year} — already downloaded")
            continue
        print(f"  Downloading {year}...")
        try:
            c.retrieve(
                'reanalysis-era5-single-levels',
                {
                    'product_type': 'reanalysis',
                    'format': 'netcdf',
                    'variable': VARIABLES,
                    'year': [str(year)],
                    'month': [str(m).zfill(2) for m in range(1, 13)],
                    'day':   [str(d).zfill(2) for d in range(1, 32)],
                    'time':  ['12:00'],
                    'area':  bbox,
                },
                chunk_file
            )
        except Exception as e2:
            print(f"  Year {year} failed: {e2}")
            continue

    existing = [f for f in chunk_files if os.path.exists(f)]
    if existing:
        print(f"Merging {len(existing)} year files...")
        datasets = [xr.open_dataset(f) for f in existing]
        time_dim = 'valid_time' if 'valid_time' in datasets[0].dims else 'time'
        merged = xr.concat(datasets, dim=time_dim)
        merged.to_netcdf(output_file)
        for f in existing:
            os.remove(f)
        print(f"Saved merged: {output_file}")


if __name__ == "__main__":
    for loc_name, params in LOCATIONS.items():
        fetch_era5_timeseries(loc_name, params)
    print("\nDone. Check data/ for the .nc files.")
