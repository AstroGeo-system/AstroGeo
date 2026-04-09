import pandas as pd
import requests

urls = {
    "ISRO": "https://en.wikipedia.org/wiki/List_of_ISRO_missions",
    "NASA": "https://en.wikipedia.org/wiki/List_of_United_States_government_rocket_launches",
    "SpaceX": "https://en.wikipedia.org/wiki/List_of_Falcon_9_and_Falcon_Heavy_launches"
}

for name, url in urls.items():
    print(f"\n=== {name} ({url}) ===")
    try:
        tables = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0'})
        for i, t in enumerate(tables):
            if t.shape[0] > 10 and t.shape[1] >= 4:
                cols = [c[-1] if isinstance(c, tuple) else c for c in t.columns]
                print(f"Index [{i}] | Shape: {t.shape} | Cols: {cols[:6]}")
    except Exception as e:
        print(f"Error: {e}")
