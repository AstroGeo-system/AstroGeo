
import os
import requests
import sys

# Add project root to Python path to allow importing backend
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

try:
    from backend.config import settings
    api_key = settings.N2YO_API_KEY
    print(f"✅ Loaded API Key from settings.")
except Exception as e:
    print(f"❌ Failed to load settings: {e}")
    # Fallback to manual .env reading if needed (simple parse)
    try:
        env_path = os.path.join(current_dir, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('N2YO_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        print("✅ Loaded API Key from .env manually.")
                        break
    except Exception as e2:
         print(f"❌ Failed manual .env load: {e2}")
         sys.exit(1)

if not api_key:
    print("❌ N2YO_API_KEY is missing.")
    sys.exit(1)

# Test with ISS (25544) at New York (40.7128, -74.0060) for 10 days
url = f"https://api.n2yo.com/rest/v1/satellite/visualpasses/25544/40.7128/-74.0060/0/10/300/"
params = {'apiKey': api_key}

print(f"📡 Connecting to N2YO API: {url}")

try:
    response = requests.get(url, params=params, timeout=15)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'passes' in data:
            print(f"✅ Success! Received {data['info']['passescount']} passes.")
            print("Sample pass data:", data['passes'][0] if data['passes'] else "No passes found (but API worked)")
        elif 'error' in data:
            print(f"❌ API returned error: {data['error']}")
        else:
            print(f"⚠️ Unexpected response format: {data.keys()}")
            print(data)
    else:
        print(f"❌ HTTP Error: {response.text}")

except Exception as e:
    print(f"❌ Exception during request: {e}")
