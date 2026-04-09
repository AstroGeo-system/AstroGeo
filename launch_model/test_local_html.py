import urllib.request
import pandas as pd

urls = {
    "ISRO": "https://en.wikipedia.org/wiki/List_of_ISRO_missions",
    "NASA": "https://en.wikipedia.org/wiki/List_of_United_States_government_rocket_launches"
}

for name, url in urls.items():
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        tables = pd.read_html(html, flavor='lxml')
        for i, t in enumerate(tables):
            if t.shape[0] > 10 and t.shape[1] >= 4:
                print(f"{name} [{i}] {t.shape} - Cols: {list(t.columns)[:4]}")
    except Exception as e:
        print(f"{name} Error: {e}")
