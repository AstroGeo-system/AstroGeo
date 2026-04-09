# 05c_download_and_merge.py
# Download all zone CSVs from Google Drive and merge into one training dataset
# Run AFTER 05b_check_status.py shows all zones COMPLETED
#
# Setup (one time):
#   pip install google-auth google-auth-oauthlib google-api-python-client
#   Download credentials.json from Google Cloud Console:
#   console.cloud.google.com → APIs → Credentials → OAuth 2.0 Client ID

import os
import io
import json
import glob
import time
import pandas as pd

TASK_IDS_FILE = '../data/gee_task_ids.json'
DRIVE_FOLDER  = 'AstroGeo_GEE_Exports'
OUTPUT_DIR    = 'gee_exports'
FINAL_CSV     = '../data/ndvi_training_india_combined.csv'

FEATURE_COLS = [
    'ndvi_2018', 'ndvi_2019', 'ndvi_2020',
    'ndvi_2022', 'ndvi_2024',
    'delta_total', 'delta_recent',
]
LABEL_COL = 'change_class'

CHANGE_CLASSES = {
    0: 'stable_vegetation',
    1: 'vegetation_loss',
    2: 'urban_growth',
    3: 'stable_other',
}


# ── Google Drive download ────────────────────────────────────
def get_drive_service():
    """Authenticate and return Google Drive service."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    TOKEN_FILE = 'drive_token.json'

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        if not os.path.exists('../config/credentials.json'):
            raise FileNotFoundError(
                'credentials.json not found.\n'
                'Download from: console.cloud.google.com → '
                'APIs & Services → Credentials → OAuth 2.0 Client IDs'
            )
        flow  = InstalledAppFlow.from_client_secrets_file('../config/credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def download_from_drive():
    """Download all CSV files from Google Drive folder."""
    from googleapiclient.http import MediaIoBaseDownload

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    service = get_drive_service()

    # Find the AstroGeo_GEE_Exports folder
    results = service.files().list(
        q=f"name='{DRIVE_FOLDER}' and "
          f"mimeType='application/vnd.google-apps.folder' and "
          f"trashed=false",
        fields='files(id, name)'
    ).execute()

    if not results['files']:
        raise ValueError(
            f'Folder "{DRIVE_FOLDER}" not found in Google Drive.\n'
            'Make sure GEE tasks completed successfully.'
        )

    folder_id = results['files'][0]['id']
    print(f'Found Drive folder: {DRIVE_FOLDER} (id: {folder_id})')

    # List all CSVs in that folder
    results = service.files().list(
        q=f"'{folder_id}' in parents and "
          f"(mimeType='text/csv' or name contains '.csv') and "
          f"trashed=false",
        fields='files(id, name, size)',
        pageSize=50
    ).execute()

    files = results['files']
    print(f'Found {len(files)} CSV files in Drive\n')

    downloaded = []
    skipped    = []

    for file in files:
        file_name = file['name']
        if not file_name.endswith('.csv'):
            file_name += '.csv'
        file_path = os.path.join(OUTPUT_DIR, file_name)

        if os.path.exists(file_path):
            size_kb = os.path.getsize(file_path) / 1024
            print(f'  Already exists ({size_kb:.0f} KB): {file_name}')
            skipped.append(file_path)
            continue

        print(f'  Downloading: {file_name}', end=' ', flush=True)
        request    = service.files().get_media(fileId=file['id'])
        fh         = io.FileIO(file_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f'{status.progress()*100:.0f}%', end='.. ', flush=True)

        size_kb = os.path.getsize(file_path) / 1024
        print(f'done ({size_kb:.0f} KB)')
        downloaded.append(file_path)

    print(f'\nDownloaded: {len(downloaded)} files')
    print(f'Skipped (already exist): {len(skipped)} files')
    return downloaded + skipped


# ── Merge and validate ───────────────────────────────────────
def merge_and_validate():
    """Merge all zone CSVs, validate, and save final training dataset."""
    # Use only v2 exports (improved vegetation-loss labeling)
    all_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'ndvi_v2_*.csv')))

    if not all_files:
        raise ValueError(
            f'No CSV files found in {OUTPUT_DIR}/\n'
            'Run download_from_drive() first.'
        )

    print(f'\nMerging {len(all_files)} zone CSV files...')
    print('-' * 55)

    dfs        = []
    zone_stats = []

    for f in all_files:
        zone_name = os.path.basename(f).replace('ndvi_v2_', '').replace('.csv', '')
        df        = pd.read_csv(f)

        # Keep only the columns we need
        available_features = [c for c in FEATURE_COLS if c in df.columns]
        if LABEL_COL not in df.columns:
            print(f'  WARNING: {zone_name} missing change_class column — skipping')
            continue
        if len(available_features) < 7:
            missing = set(FEATURE_COLS) - set(available_features)
            print(f'  WARNING: {zone_name} missing bands: {missing} — skipping')
            continue

        df = df[available_features + [LABEL_COL]].copy()
        df['zone'] = zone_name

        # Drop rows with NaN (can happen in high-cloud zones)
        before = len(df)
        df     = df.dropna()
        after  = len(df)
        if before != after:
            print(f'  {zone_name}: dropped {before - after} NaN rows')

        class_dist = df[LABEL_COL].value_counts().sort_index().to_dict()
        print(f'  {zone_name:<35} {len(df):>5} rows  '
              f'classes: {class_dist}')

        zone_stats.append({
            'zone': zone_name,
            'rows': len(df),
            'class_distribution': class_dist,
        })
        dfs.append(df)

    if not dfs:
        raise ValueError('No valid CSV files to merge.')

    # Combine all zones
    combined = pd.concat(dfs, ignore_index=True)

    # Shuffle rows so zones are mixed (important for RF cross-validation)
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

    # Ensure change_class is integer
    combined[LABEL_COL] = combined[LABEL_COL].astype(int)

    print('\n' + '=' * 55)
    print(f'FINAL DATASET SUMMARY')
    print('=' * 55)
    print(f'Total rows:     {len(combined):,}')
    print(f'Total features: {len(FEATURE_COLS)}')
    print(f'Zones included: {combined["zone"].nunique()}')
    print(f'\nClass distribution:')
    for cls_id, cls_name in CHANGE_CLASSES.items():
        count = (combined[LABEL_COL] == cls_id).sum()
        pct   = count / len(combined) * 100
        print(f'  Class {cls_id} ({cls_name:<22}): {count:>5} rows ({pct:.1f}%)')

    print(f'\nNDVI value ranges:')
    for col in FEATURE_COLS:
        print(f'  {col:<15}: '
              f'min={combined[col].min():.3f}  '
              f'max={combined[col].max():.3f}  '
              f'mean={combined[col].mean():.3f}')

    print(f'\nZones contributing:')
    zone_counts = combined['zone'].value_counts()
    for zone, count in zone_counts.items():
        print(f'  {zone:<35}: {count} rows')

    # Save
    combined.to_csv(FINAL_CSV, index=False)
    print(f'\n✅ Saved: {FINAL_CSV}')
    print(f'   Ready for Step 6: RandomForest training')
    print(f'   Load with: df = pd.read_csv("{FINAL_CSV}")')

    # Save zone stats for reference
    with open('../data/zone_sample_stats.json', 'w') as f:
        json.dump(zone_stats, f, indent=2)
    print(f'   Zone stats saved: zone_sample_stats.json')

    return combined


# ── Main ─────────────────────────────────────────────────────
if __name__ == '__main__':
    print('Step 1: Downloading CSVs from Google Drive...')
    try:
        download_from_drive()
    except ImportError:
        print('Google API libraries not installed.')
        print('Run: pip install google-auth google-auth-oauthlib '
              'google-api-python-client')
        print('\nAlternatively, manually download CSVs from Google Drive')
        print(f'into the folder: {OUTPUT_DIR}/')
        print('Then re-run this script — it will skip the download step.')

    print('\nStep 2: Merging and validating...')
    df = merge_and_validate()
    print('\nDone. Proceed to Step 6: python 06_train_rf.py')
