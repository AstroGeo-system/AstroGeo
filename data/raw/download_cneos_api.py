import requests
import pandas as pd
import os
from datetime import datetime

def download_cneos_close_approaches(max_distance_au=0.2):
    """
    Download asteroid close approaches from NASA CNEOS API
    
    Args:
        max_distance_au: Maximum distance in AU (default 0.2)
    """
    
    print("="*70)
    print("DOWNLOADING ASTEROID DATA FROM NASA CNEOS API")
    print("="*70)
    
    # CNEOS Close Approach API endpoint
    base_url = "https://ssd-api.jpl.nasa.gov/cad.api"
    
    # Parameters for the API
    params = {
        'dist-max': max_distance_au,  # Max distance in AU
        'sort': 'date',                # Sort by date
        'fullname': 'true',            # Get full asteroid names
    }
    
    print(f"\nFetching approaches with distance <= {max_distance_au} AU...")
    print(f"API URL: {base_url}")
    print(f"Parameters: {params}\n")
    
    try:
        # Make API request
        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Extract data
        if 'data' not in data:
            print("❌ No data returned from API")
            return None
        
        # Get column names and data
        columns = data['fields']
        rows = data['data']
        
        print(f"✅ Received {len(rows):,} approaches")
        print(f"✅ Columns: {len(columns)}")
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=columns)
        
        # Show info
        print(f"\nData columns:")
        for i, col in enumerate(columns, 1):
            print(f"  {i}. {col}")
        
        print(f"\nDate range:")
        print(f"  Earliest: {df['cd'].min()}")
        print(f"  Latest: {df['cd'].max()}")
        
        print(f"\nDistance range:")
        print(f"  Closest: {df['dist'].min()} AU")
        print(f"  Farthest: {df['dist'].max()} AU")
        
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading data: {e}")
        return None

def split_past_and_future(df):
    """Split data into past (historical) and future (predictions)"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Convert date column to datetime
    df['cd'] = pd.to_datetime(df['cd'])
    
    # Split
    df_past = df[df['cd'] < today].copy()
    df_future = df[df['cd'] >= today].copy()
    
    print(f"\n{'='*70}")
    print("SPLITTING DATA")
    print('='*70)
    print(f"Past approaches: {len(df_past):,}")
    print(f"Future approaches: {len(df_future):,}")
    
    return df_past, df_future

def save_raw_data(df_past, df_future):
    """Save raw data to CSV files"""
    
    # Create directories
    os.makedirs('data/raw', exist_ok=True)
    
    # Save past approaches
    past_file = 'data/raw/cneos_past_approaches.csv'
    df_past.to_csv(past_file, index=False)
    print(f"\n✅ Saved past approaches: {past_file}")
    print(f"   Rows: {len(df_past):,}")
    print(f"   Size: {os.path.getsize(past_file) / 1024 / 1024:.2f} MB")
    
    # Save future approaches
    future_file = 'data/raw/cneos_future_approaches.csv'
    df_future.to_csv(future_file, index=False)
    print(f"\n✅ Saved future approaches: {future_file}")
    print(f"   Rows: {len(df_future):,}")
    print(f"   Size: {os.path.getsize(future_file) / 1024 / 1024:.2f} MB")
    
    # Show sample
    print(f"\n{'='*70}")
    print("SAMPLE DATA (first 5 rows):")
    print('='*70)
    print(df_past.head())

if __name__ == '__main__':
    # Download all approaches within 0.2 AU
    df = download_cneos_close_approaches(max_distance_au=0.2)
    
    if df is not None:
        # Split into past and future
        df_past, df_future = split_past_and_future(df)
        
        # Save to files
        save_raw_data(df_past, df_future)
        
        print(f"\n{'='*70}")
        print("✅ DOWNLOAD COMPLETE!")
        print('='*70)
        print("\nNext steps:")
        print("1. Run: python clean_asteroid_data.py")
        print("2. Run: python load_asteroid_data.py")
    else:
        print("\n❌ Download failed. Please check your internet connection.")