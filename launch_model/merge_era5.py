"""
merge_era5.py — Unzip and merge all downloaded ERA5 yearly ZIP archives.
Run from launch_model/ directory.
"""
import glob
import os
import zipfile
import xarray as xr
import shutil

DATA_DIR = 'data'

def unzip_and_merge(pattern, output_name, time_dim='valid_time'):
    files = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
    if not files:
        print(f"No files matching {pattern} — skipping.")
        return
    
    final_output = os.path.join(DATA_DIR, output_name)
    if os.path.exists(final_output):
        print(f"{final_output} already exists — skipping.")
        return

    print(f"Processing {len(files)} files...")
    
    extracted_nc = []
    tmp_dir = os.path.join(DATA_DIR, '_tmp_extract')
    os.makedirs(tmp_dir, exist_ok=True)
    
    for i, zf in enumerate(files):
        with zipfile.ZipFile(zf, 'r') as z:
            names = z.namelist()
            # The instant stream contains main variables (t2m, u10, v10, tcc, sp)
            # The accum stream contains precipitation (tp)
            for n in names:
                outpath = os.path.join(tmp_dir, f'{i:04d}_{n.replace("/", "_")}')
                with z.open(n) as src, open(outpath, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                extracted_nc.append(outpath)
        print(f"  Extracted {os.path.basename(zf)}")
    
    print(f"\nMerging {len(extracted_nc)} NetCDF files...")
    
    # Load them all and merge
    datasets = []
    for nc in sorted(extracted_nc):
        try:
            ds = xr.open_dataset(nc, engine='netcdf4')
            datasets.append(ds)
        except Exception as e:
            print(f"  Skip {nc}: {e}")
    
    if not datasets:
        print("No valid datasets to merge!")
        return
    
    # Find the time dimension
    for ds in datasets:
        if 'valid_time' in ds.dims:
            time_dim = 'valid_time'
            break
        elif 'time' in ds.dims:
            time_dim = 'time'
            break
    
    print(f"Concatenating on dim '{time_dim}'...")
    merged = xr.concat(datasets, dim=time_dim)
    merged = merged.sortby(time_dim)
    merged.to_netcdf(final_output)
    
    # Cleanup
    shutil.rmtree(tmp_dir)
    print(f"Saved: {final_output}")
    print(f"Shape: {dict(merged.dims)}")
    print(f"Variables: {list(merged.data_vars)}")


print("=== Merging Sriharikota ===")
unzip_and_merge('era5_sriharikota_????.nc', 'era5_sriharikota.nc')

print("\n=== Merging Cape Canaveral ===")
unzip_and_merge('era5_cape_canaveral_part*.nc', 'era5_cape_canaveral_partial.nc')

print("\nDone! Check data/ for .nc files.")
