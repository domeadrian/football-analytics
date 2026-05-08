"""
Fetch ALL players with real market values from Transfermarkt.
Fetches each team's squad page across all 15 leagues.
Rate-limited to avoid blocks. Saves checkpoints per league.

Run:  python fetch_tm_squads.py
"""
import requests, re, json, os, time
import urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

session = requests.Session()
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.transfermarkt.com/',
})

# (dashboard_name, tm_code, tm_slug_for_league_page)
LEAGUES = [
    ("Romanian Liga I",         "RO1", "superliga"),
    ("Romanian Liga II",        "RO2", "liga-ii"),
    ("Belgian Pro League",      "BE1", "jupiler-pro-league"),
    ("Danish Superliga",        "DK1", "superligaen"),
    ("Scottish Premiership",    "SC1", "scottish-premiership"),
    ("English Premier League",  "GB1", "premier-league"),
    ("La Liga",                 "ES1", "laliga"),
    ("Serie A",                 "IT1", "serie-a"),
    ("Bundesliga",              "L1",  "1-bundesliga"),
    ("Ligue 1",                 "FR1", "ligue-1"),
    ("Eredivisie",              "NL1", "eredivisie"),
    ("Primeira Liga",           "PO1", "liga-portugal"),
    ("Turkish Super Lig",       "TR1", "super-lig"),
    ("Greek Super League",      "GR1", "super-league-1"),
    ("Russian Premier League",  "RU1", "premier-liga"),
]

SEASON = 2025


def parse_market_value(mv_str):
    if not mv_str or mv_str.strip() in ('-', '', 'N/A'):
        return 0.0
    s = mv_str.strip().replace('€', '').replace(',', '.')
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


def fetch(url, retries=3, delay=3):
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                wait = delay * (attempt + 2)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                return r
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"    Timeout/Conn err (attempt {attempt+1})")
            time.sleep(delay * (attempt + 1))
    return None


def get_league_teams(tm_code, tm_slug):
    """Get team list from league overview page."""
    url = f"https://www.transfermarkt.com/{tm_slug}/startseite/wettbewerb/{tm_code}"
    r = fetch(url)
    if not r or r.status_code != 200:
        return []
    
    soup = BeautifulSoup(r.text, 'html.parser')
    teams = []
    seen = set()
    
    # Primary: hauptlink cells
    for a in soup.select('td.hauptlink.no-border-links a[href*="/startseite/verein/"]'):
        href = a.get('href', '')
        m = re.search(r'/verein/(\d+)', href)
        if m and m.group(1) not in seen:
            tid = m.group(1)
            seen.add(tid)
            name = a.get_text(strip=True)
            slug_m = re.match(r'/([^/]+)/', href)
            slug = slug_m.group(1) if slug_m else 'x'
            teams.append({'id': tid, 'name': name, 'slug': slug})
    
    # Fallback: broader search
    if not teams:
        for a in soup.select('a[href*="/startseite/verein/"]'):
            href = a.get('href', '')
            m = re.search(r'/verein/(\d+)', href)
            title = a.get('title', '') or a.get_text(strip=True)
            if m and title and len(title) > 2 and m.group(1) not in seen:
                tid = m.group(1)
                seen.add(tid)
                slug_m = re.match(r'/([^/]+)/', href)
                slug = slug_m.group(1) if slug_m else 'x'
                if slug not in (tm_slug, 'x', 'statistik', 'spieler-statistik'):
                    teams.append({'id': tid, 'name': title, 'slug': slug})
    
    # Filter out historical/dissolved teams (very high IDs with "(year)" in name)
    teams = [t for t in teams if not re.search(r'\(\d{4}', t['name'])]
    
    return teams


def parse_squad_page(html, team_name, league_name):
    """Parse a team kader page HTML → list of player dicts."""
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.select('table.items')
    if not tables:
        return []
    
    players = []
    for row in tables[0].select('tbody > tr'):
        tds = row.select('td')
        if len(tds) < 10:
            continue

        # Player name from td.hauptlink (td[3]) or profile link
        name_link = row.select_one('a[href*="profil/spieler"]')
        if not name_link:
            continue

        name = name_link.get('title', '') or name_link.get_text(strip=True)
        if not name:
            continue

        # Position from td[4] (direct text) or inline-table last row
        position = tds[4].get_text(strip=True) if len(tds) > 4 else ""
        if not position:
            pos_rows = row.select('table.inline-table tr')
            if len(pos_rows) >= 2:
                position = pos_rows[-1].get_text(strip=True)

        # Skip sub-rows (position == player name)
        if not position or position == name:
            continue

        # Age & DOB from td[5]
        dob, age = "", None
        dob_text = tds[5].get_text(strip=True) if len(tds) > 5 else ""
        m_age = re.search(r'\((\d+)\)', dob_text)
        if m_age:
            age = int(m_age.group(1))
        dob = re.sub(r'\s*\(\d+\)\s*', '', dob_text).strip()

        # Nationality
        nat_imgs = row.select('td.zentriert img.flaggenrahmen')
        nationality = nat_imgs[0].get('title', '') if nat_imgs else ""

        # Market value from last td (td[12])
        mv_el = row.select_one('td.rechts.hauptlink a') or row.select_one('td.rechts.hauptlink')
        mv_str = mv_el.get_text(strip=True) if mv_el else ""
        mv = parse_market_value(mv_str)

        # Jersey number from td[0]
        number = tds[0].get_text(strip=True) if tds else ""

        # Height from td[7], foot from td[8]
        height = tds[7].get_text(strip=True) if len(tds) > 7 else ""
        foot = tds[8].get_text(strip=True) if len(tds) > 8 else ""

        # Contract until from td[11]
        contract = tds[11].get_text(strip=True) if len(tds) > 11 else ""

        players.append({
            "strPlayer": name,
            "strPosition": position,
            "dateBorn": dob,
            "age": age,
            "strNationality": nationality,
            "strNumber": number,
            "strHeight": height,
            "strFoot": foot,
            "strContract": contract,
            "strTeam": team_name,
            "_teamName": team_name,
            "_leagueName": league_name,
            "market_value_eur_m": mv,
            "market_value_str": mv_str,
            "strSigning": mv_str,
            "strWage": "",
            "strStatus": "Active",
            "source": "transfermarkt_apr2026",
        })
    
    return players


def fetch_league(league_name, tm_code, tm_slug):
    """Fetch all squads for one league."""
    print(f"\n{'='*60}")
    print(f"LEAGUE: {league_name} ({tm_code})")
    print(f"{'='*60}")
    
    # Check for existing checkpoint
    cp_path = os.path.join(DATA_DIR, f"tm_players_{tm_code}.json")
    if os.path.exists(cp_path):
        with open(cp_path, encoding="utf-8") as f:
            existing = json.load(f)
        if len(existing) > 50:
            print(f"  Checkpoint found: {len(existing)} players — SKIPPING")
            return existing
    
    teams = get_league_teams(tm_code, tm_slug)
    if not teams:
        print(f"  Failed to get teams")
        return []
    
    print(f"  Found {len(teams)} teams")
    all_players = []
    
    for i, team in enumerate(teams):
        print(f"  [{i+1}/{len(teams)}] {team['name']:35s}", end=" ", flush=True)
        time.sleep(2.5)  # 2.5s between team requests
        
        url = f"https://www.transfermarkt.com/{team['slug']}/kader/verein/{team['id']}/saison_id/{SEASON}/plus/1"
        r = fetch(url, retries=2, delay=4)
        
        if not r or r.status_code != 200:
            print(f"FAILED ({r.status_code if r else 'timeout'})")
            continue
        
        players = parse_squad_page(r.text, team['name'], league_name)
        all_players.extend(players)
        print(f"→ {len(players)} players")
    
    # Save checkpoint
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(all_players, f, ensure_ascii=False, indent=2)
    print(f"  → Total: {len(all_players)} players saved to {cp_path}")
    
    return all_players


def main():
    all_players = []
    failed = []
    
    for league_name, tm_code, tm_slug in LEAGUES:
        players = fetch_league(league_name, tm_code, tm_slug)
        if players:
            all_players.extend(players)
        else:
            failed.append(league_name)
        time.sleep(3)
    
    # Save consolidated
    output = os.path.join(DATA_DIR, "all_players_2526.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_players, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {len(all_players)} players")
    print(f"Saved: {output}")
    if failed:
        print(f"Failed: {failed}")
    
    from collections import Counter
    lc = Counter(p["_leagueName"] for p in all_players)
    print(f"\nBreakdown:")
    for lg, cnt in lc.most_common():
        print(f"  {lg:35s} {cnt:5d}")


if __name__ == "__main__":
    main()
