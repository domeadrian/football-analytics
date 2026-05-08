import requests, re, json
import urllib3
urllib3.disable_warnings()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml',
}

url = 'https://www.transfermarkt.com/fcsb/kader/verein/8552/saison_id/2025/plus/1'
print(f"Fetching {url}...")
r = requests.get(url, headers=headers, timeout=20, verify=False)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

# Save raw HTML for inspection
with open("data/_test_tm.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("Saved to data/_test_tm.html")

# Try to find player data
from bs4 import BeautifulSoup
try:
    soup = BeautifulSoup(r.text, 'html.parser')
    # Find player links
    player_links = soup.select('a[href*="spielprofil/spieler"]')
    names = set()
    for a in player_links:
        title = a.get('title', '')
        if title and len(title) > 2:
            names.add(title)
    print(f"\nFound {len(names)} unique player names:")
    for n in sorted(names)[:15]:
        print(f"  {n}")
    
    # Find market values
    mv_cells = soup.select('td.rechts.hauptlink')
    print(f"\nMarket value cells: {len(mv_cells)}")
    for td in mv_cells[:10]:
        print(f"  {td.get_text(strip=True)}")
except ImportError:
    print("bs4 not available, trying regex")
    names = re.findall(r'title="([^"]{3,40})"[^>]*href="[^"]*spielprofil/spieler', r.text)
    print(f"Names via regex: {names[:10]}")
