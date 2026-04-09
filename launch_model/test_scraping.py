import urllib.request
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO

urls = {
    "ISRO": "https://en.wikipedia.org/wiki/List_of_Indian_Space_Research_Organisation_missions",
    "NASA": "https://en.wikipedia.org/wiki/List_of_United_States_government_rocket_launches" # Or NASA missions
}

req = urllib.request.Request(urls["ISRO"], headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')
for i, t in enumerate(soup.find_all('table', {'class': 'wikitable'})):
    rows = t.find_all('tr')
    if len(rows) > 5:
        first_row = [td.text.strip() for td in rows[0].find_all(['th', 'td'])]
        print(f"ISRO wikitable {i}: {len(rows)} rows, cols: {first_row}")

req = urllib.request.Request(urls["NASA"], headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')
for i, t in enumerate(soup.find_all('table', {'class': 'wikitable'})):
    rows = t.find_all('tr')
    if len(rows) > 5:
        first_row = [td.text.strip() for td in rows[0].find_all(['th', 'td'])]
        print(f"NASA wikitable {i}: {len(rows)} rows, cols: {first_row}")
