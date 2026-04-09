import pandas as pd
import requests

urls = {
    "ISRO": "https://en.wikipedia.org/wiki/List_of_ISRO_missions",
    "NASA": "https://en.wikipedia.org/wiki/List_of_United_States_government_rocket_launches",
    "SpaceX": "https://en.wikipedia.org/wiki/List_of_Falcon_9_and_Falcon_Heavy_launches"
}

headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

for name, url in urls.items():
    print(f"\n=== {name} ===")
    try:
        req = requests.get(url, headers=headers)
        # Using StringIO to avoid pandas warning
        from io import StringIO
        tables = pd.read_html(StringIO(req.text))
        for i, t in enumerate(tables):
            # Only print tables that look like data (more than 10 rows and 4+ columns)
            if t.shape[0] > 10 and t.shape[1] >= 4:
                # Flatten multiindex columns just for printing
                cols = [c[-1] if isinstance(c, tuple) else c for c in t.columns]
                print(f"Table [{i}] | Shape: {t.shape} | Cols: {cols[:5]}")
    except Exception as e:
        print(f"Error reading {name}: {e}")
