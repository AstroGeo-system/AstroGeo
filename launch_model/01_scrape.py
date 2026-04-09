import pandas as pd
import requests
from bs4 import BeautifulSoup
import os

# Create data directory
os.makedirs("data", exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

def get_wiki_tables(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "lxml")
    tables = pd.read_html(str(soup))
    return tables

print("Fetching ISRO...")
isro_tables = get_wiki_tables("https://en.wikipedia.org/wiki/List_of_ISRO_missions")
for i, t in enumerate(isro_tables):
    if len(t) > 5: print(f"ISRO Table {i}: {t.shape} cols: {list(t.columns)[:3]}")

print("\nFetching NASA...")
nasa_tables = get_wiki_tables("https://en.wikipedia.org/wiki/List_of_United_States_government_rocket_launches")
for i, t in enumerate(nasa_tables):
    if len(t) > 5: print(f"NASA Table {i}: {t.shape} cols: {list(t.columns)[:3]}")

print("\nFetching SpaceX...")
spacex_tables = get_wiki_tables("https://en.wikipedia.org/wiki/List_of_Falcon_9_and_Falcon_Heavy_launches")
for i, t in enumerate(spacex_tables):
    if len(t) > 5: print(f"SpaceX Table {i}: {t.shape} cols: {list(t.columns)[:3]}")
