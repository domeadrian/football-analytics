"""Quick test: fetch just Romanian Liga I to validate parsing."""
import requests, re, json, os, time
import urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.transfermarkt.com/',
}

def parse_market_value(mv_str):
    if not mv_str or mv_str.strip() in ('-', ''):
        return 0.0
    s = mv_str.strip().replace('€', '').replace(',', '.')
    m = re.match(r'([\d.]+)\s*(m|k)?', s, re.IGNORECASE)
    if not m:
        return 0.0
    val = float(m.group(1))
    suffix = (m.group(2) or '').lower()
    if suffix == 'k':
        val /= 1000.0
    return round(val, 3)


def fetch_team_squad(tm_id, slug, season=2025):
    url = f"https://www.transfermarkt.com/{slug}/kader/verein/{tm_id}/saison_id/{season}/plus/1"
    r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
    if r.status_code != 200:
        return []
    
    soup = BeautifulSoup(r.text, 'html.parser')
    tables = soup.select('table.items')
    if not tables:
        return []
    
    players = []
    rows = tables[0].select('tbody > tr')
    
    for row in rows:
        tds = row.select('td')
        if len(tds) < 3:
            continue
        
        name_link = row.select_one('td.hauptlink a[href*="spielprofil/spieler"]')
        if not name_link:
            continue
        
        name = name_link.get('title', '') or name_link.get_text(strip=True)
        
        # Position
        pos_tds = row.select('td.posrela table.inline-table tr')
        position = ""
        if len(pos_tds) >= 2:
            position = pos_tds[-1].get_text(strip=True)
        
        # Skip duplicate sub-rows (name == position means it's the sub-row)
        if not position or position == name:
            continue
        
        # Birth date & age
        dob = ""
        age = ""
        for z in row.select('td.zentriert'):
            txt = z.get_text(strip=True)
            if re.match(r'[A-Z][a-z]{2}\s+\d', txt):
                m_age = re.search(r'\((\d+)\)', txt)
                if m_age:
                    age = int(m_age.group(1))
                dob = re.sub(r'\s*\(\d+\)\s*', '', txt).strip()
                break
        
        # Nationality
        nat_imgs = row.select('td.zentriert img.flaggenrahmen')
        nationality = nat_imgs[0].get('title', '') if nat_imgs else ""
        
        # Market value
        mv_cell = row.select_one('td.rechts.hauptlink a')
        if not mv_cell:
            mv_cell = row.select_one('td.rechts.hauptlink')
        mv_str = mv_cell.get_text(strip=True) if mv_cell else ""
        mv = parse_market_value(mv_str)
        
        # Number
        nr = row.select_one('div.rn_nummer')
        number = nr.get_text(strip=True) if nr else ""
        
        players.append({
            'name': name, 'position': position, 'dob': dob, 'age': age,
            'nationality': nationality, 'market_value_str': mv_str,
            'market_value_eur_m': mv, 'number': number,
        })
    
    return players


# Fetch league page for team list
print("Fetching Romanian Liga I teams...")
r = requests.get("https://www.transfermarkt.com/superliga/startseite/wettbewerb/RO1", headers=HEADERS, timeout=20, verify=False)
print(f"Status: {r.status_code}")
soup = BeautifulSoup(r.text, 'html.parser')

teams = []
seen = set()
for a in soup.select('a[href*="/startseite/verein/"]'):
    href = a.get('href', '')
    m = re.search(r'/verein/(\d+)', href)
    title = a.get('title', '') or a.get_text(strip=True)
    if m and title and len(title) > 2 and m.group(1) not in seen:
        tid = m.group(1)
        seen.add(tid)
        slug_m = re.match(r'/([^/]+)/', href)
        slug = slug_m.group(1) if slug_m else ''
        if slug and slug not in ('x', 'superliga'):
            teams.append({'tm_id': tid, 'name': title, 'slug': slug})

print(f"Found {len(teams)} teams:")
for t in teams:
    print(f"  {t['tm_id']:6s} | {t['name']:35s} | slug={t['slug']}")

# Fetch first 3 teams as test
all_players = []
for team in teams[:3]:
    print(f"\nFetching {team['name']}...", flush=True)
    time.sleep(1.5)
    squad = fetch_team_squad(team['tm_id'], team['slug'])
    for p in squad:
        p['team'] = team['name']
    all_players.extend(squad)
    print(f"  → {len(squad)} players")
    for p in squad[:5]:
        print(f"    {p['name']:25s} {p['position']:20s} Age:{p['age']:<3} {p['nationality']:15s} {p['market_value_str']}")

print(f"\nTotal test players: {len(all_players)}")
