"""Quick test: fetch FCSB squad with the fixed parsing logic."""
import requests, urllib3, re, json
urllib3.disable_warnings()
from bs4 import BeautifulSoup

session = requests.Session()
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})


def parse_market_value(mv_str):
    if not mv_str or mv_str.strip() in ('-', '', 'N/A'):
        return 0.0
    s = mv_str.strip().replace('\u20ac', '').replace(',', '.')
    m = re.match(r'([\d.]+)\s*(m|k|bn)?', s, re.IGNORECASE)
    if not m:
        return 0.0
    val = float(m.group(1))
    suffix = (m.group(2) or '').lower()
    if suffix == 'k':
        val /= 1000.0
    elif suffix == 'bn':
        val *= 1000.0
    return round(val, 3)


url = 'https://www.transfermarkt.com/fcsb/kader/verein/301/saison_id/2025/plus/1'
r = session.get(url, timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')
tables = soup.select('table.items')
print(f"table.items: {len(tables)}")

players = []
for row in tables[0].select('tbody > tr'):
    tds = row.select('td')
    if len(tds) < 10:
        continue
    name_link = row.select_one('a[href*="profil/spieler"]')
    if not name_link:
        continue
    name = name_link.get('title', '') or name_link.get_text(strip=True)
    if not name:
        continue
    position = tds[4].get_text(strip=True) if len(tds) > 4 else ""
    if not position or position == name:
        continue
    dob_text = tds[5].get_text(strip=True) if len(tds) > 5 else ""
    m_age = re.search(r'\((\d+)\)', dob_text)
    age = int(m_age.group(1)) if m_age else None
    mv_el = row.select_one('td.rechts.hauptlink a') or row.select_one('td.rechts.hauptlink')
    mv_str = mv_el.get_text(strip=True) if mv_el else ""
    mv = parse_market_value(mv_str)
    players.append({"name": name, "position": position, "age": age, "mv": mv, "mv_str": mv_str})

print(f"Players found: {len(players)}")
for p in players:
    print(f"  {p['name']:30s} | {p['position']:20s} | {p['age']} | {p['mv_str']:>10s} | {p['mv']}")
