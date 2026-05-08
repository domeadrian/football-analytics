"""Test extracting FCSB squad from Transfermarkt to verify parsing works."""
import requests, re, json
import urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

url = 'https://www.transfermarkt.com/fcsb/kader/verein/301/saison_id/2025/plus/1'
print(f"Fetching {url}...")
r = requests.get(url, headers=headers, timeout=20, verify=False)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

soup = BeautifulSoup(r.text, 'html.parser')

# The squad table has class "items"
tables = soup.select('table.items')
print(f"Tables found: {len(tables)}")

players = []
for table in tables:
    rows = table.select('tbody tr')
    for row in rows:
        # Skip separator rows
        if 'bg_blau_20' in row.get('class', []):
            continue
        
        # Player name - in hauptlink cells
        name_cell = row.select_one('td.hauptlink a')
        if not name_cell:
            continue
        name = name_cell.get_text(strip=True)
        
        # Position
        pos_cells = row.select('td.posrela table td')
        position = ""
        if len(pos_cells) >= 2:
            position = pos_cells[-1].get_text(strip=True)
        
        # All td cells
        tds = row.select('td')
        
        # Date of birth & age - in zentriert class cells
        dob = ""
        age = ""
        zentrier = row.select('td.zentriert')
        for z in zentrier:
            txt = z.get_text(strip=True)
            # Date pattern like "Apr 30, 1999 (26)"  or "Jun 2, 1993"
            if re.match(r'[A-Z][a-z]{2}\s+\d', txt):
                m = re.search(r'\((\d+)\)', txt)
                if m:
                    age = m.group(1)
                dob = re.sub(r'\s*\(\d+\)\s*', '', txt).strip()
        
        # Nationality - flag images
        nat_imgs = row.select('td.zentriert img.flaggenrahmen')
        nationality = ""
        if nat_imgs:
            nationality = nat_imgs[0].get('title', '')
        
        # Market value - in the last rechts hauptlink cell
        mv_cell = row.select_one('td.rechts.hauptlink')
        market_value = ""
        if mv_cell:
            market_value = mv_cell.get_text(strip=True)
        
        if name and len(name) > 1:
            players.append({
                'name': name,
                'position': position,
                'dob': dob,
                'age': age,
                'nationality': nationality,
                'market_value': market_value,
            })

print(f"\nExtracted {len(players)} players:")
for p in players:
    print(f"  {p['name']:30s} | {p['position']:25s} | Age {p['age']:3s} | {p['nationality']:15s} | {p['market_value']}")

# Save test output
with open("data/_test_fcsb_squad.json", "w", encoding="utf-8") as f:
    json.dump(players, f, ensure_ascii=False, indent=2)
print(f"\nSaved to data/_test_fcsb_squad.json")
