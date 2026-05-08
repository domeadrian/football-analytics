import requests, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

s = requests.Session()
s.verify = False
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})

url = 'https://www.transfermarkt.com/fcsb/kader/verein/301/saison_id/2025/plus/1'
r = s.get(url, timeout=30)
print(f"Status: {r.status_code}, Length: {len(r.text)}")
soup = BeautifulSoup(r.text, 'html.parser')

# Debug: what tables exist?
tables = soup.select('table')
print(f"All tables: {len(tables)}")
for i, t in enumerate(tables[:8]):
    classes = t.get('class', [])
    rows = len(t.select('tr'))
    print(f"  Table {i}: classes={classes}, rows={rows}")

items = soup.select('table.items')
print(f"\ntable.items count: {len(items)}")
if items:
    tbl = items[0]
    tbody = tbl.select('tbody > tr')
    print(f"tbody > tr: {len(tbody)}")
    tbody2 = tbl.select('tbody tr')
    print(f"tbody tr: {len(tbody2)}")
    for row in tbody[:3]:
        tds = row.select('td')
        print(f"  Row tds: {len(tds)}")
        for j, td in enumerate(tds):
            txt = td.get_text(strip=True)[:40]
            print(f"    td[{j}]: {txt}")

# Try inline-table
it = soup.select('table.inline-table')
print(f"\ninline-table count: {len(it)}")
if it:
    for row in it[0].select('tr'):
        print(f"  row: {row.get_text(strip=True)[:60]}")

# Player profile links
links = soup.select('a[href*="profil/spieler"]')
print(f"\nPlayer profile links: {len(links)}")
for a in links[:5]:
    title = a.get('title', '')
    text = a.get_text(strip=True)
    print(f"  {title} | {text}")

# Check for even/odd rows (common TM pattern)
even_rows = soup.select('tr.even, tr.odd')
print(f"\neven/odd rows: {len(even_rows)}")
if even_rows:
    row = even_rows[0]
    tds = row.select('td')
    print(f"First row tds: {len(tds)}")
    for j, td in enumerate(tds):
        print(f"  td[{j}]: cls={td.get('class',[])} text={td.get_text(strip=True)[:50]}")
