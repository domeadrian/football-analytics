"""
Fetch real football data using requests with proper headers.
Sources:
  1. Football-Data.co.uk — Romanian Liga 1 + Euro leagues (match-by-match CSV)
  2. Football-Data.org API — Free tier (no key needed for some endpoints)
  3. TheSportsDB — Free API for standings/teams
  4. GitHub raw football datasets
"""

import requests
import os
import json
import time
import csv
import io

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/csv,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.football-data.co.uk/romaniab.php",
})

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_file(url, filename, desc=""):
    path = os.path.join(DATA_DIR, filename)
    print(f"  Downloading {desc or filename}...", end=" ")
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
        print(f"OK ({len(resp.content):,} bytes)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


# =========================================================================
# 1. Football-Data.co.uk CSVs
# =========================================================================
print("=" * 70)
print("1. FOOTBALL-DATA.CO.UK — Match Results + Odds (CSV)")
print("=" * 70)

fd_base = "https://www.football-data.co.uk/mmz4281"
leagues = {
    # Romanian Liga 1
    "RO1_2425.csv": f"{fd_base}/2425/RO1.csv",
    "RO1_2324.csv": f"{fd_base}/2324/RO1.csv",
    "RO1_2223.csv": f"{fd_base}/2223/RO1.csv",
    "RO1_2122.csv": f"{fd_base}/2122/RO1.csv",
    "RO1_2021.csv": f"{fd_base}/2021/RO1.csv",
    "RO1_1920.csv": f"{fd_base}/1920/RO1.csv",
    "RO1_1819.csv": f"{fd_base}/1819/RO1.csv",
    # Top European leagues 24-25
    "EPL_2425.csv": f"{fd_base}/2425/E0.csv",
    "LaLiga_2425.csv": f"{fd_base}/2425/SP1.csv",
    "SerieA_2425.csv": f"{fd_base}/2425/I1.csv",
    "Bundesliga_2425.csv": f"{fd_base}/2425/D1.csv",
    "Ligue1_2425.csv": f"{fd_base}/2425/F1.csv",
    "Eredivisie_2425.csv": f"{fd_base}/2425/N1.csv",
    "Portugal_2425.csv": f"{fd_base}/2425/P1.csv",
    "Turkey_2425.csv": f"{fd_base}/2425/T1.csv",
    "Belgium_2425.csv": f"{fd_base}/2425/B1.csv",
    "Greece_2425.csv": f"{fd_base}/2425/G1.csv",
}

for fname, url in leagues.items():
    download_file(url, fname, fname.replace(".csv", ""))
    time.sleep(0.3)


# =========================================================================
# 2. Football-Data.org Free API (no key for competitions list)
# =========================================================================
print("\n" + "=" * 70)
print("2. FOOTBALL-DATA.ORG — Free API")
print("=" * 70)

fd_org_headers = {"X-Auth-Token": ""}  # empty = free tier, limited

# Try without auth key
try:
    resp = session.get(
        "https://api.football-data.org/v4/competitions",
        headers={"X-Auth-Token": ""},
        timeout=15,
    )
    if resp.status_code == 200:
        with open(os.path.join(DATA_DIR, "fdorg_competitions.json"), "w") as f:
            json.dump(resp.json(), f, indent=2)
        print(f"  Competitions list: OK ({len(resp.content):,} bytes)")
    else:
        print(f"  Competitions: HTTP {resp.status_code}")
except Exception as e:
    print(f"  Competitions: {e}")


# =========================================================================
# 3. GitHub open football datasets (openfootball project)
# =========================================================================
print("\n" + "=" * 70)
print("3. GITHUB OPEN FOOTBALL DATA")
print("=" * 70)

github_data = [
    # Historical results dataset by Mart Jürisoo (400k+ matches)
    ("https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
     "intl_results.csv", "International match results (1872-2025)"),
    ("https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv",
     "intl_goalscorers.csv", "International goalscorers"),
]

for url, fname, desc in github_data:
    download_file(url, fname, desc)
    time.sleep(0.5)


# =========================================================================
# 4. TheSportsDB — Try Romanian league with different IDs
# =========================================================================
print("\n" + "=" * 70)
print("4. THESPORTSDB — Romanian & European League Data")
print("=" * 70)

# First find the correct league IDs
sdb_base = "https://www.thesportsdb.com/api/v1/json/3"

# Search for Romanian leagues
sdb_urls = [
    (f"{sdb_base}/search_all_leagues.php?c=Romania", "sportsdb_ro_leagues.json", "Romanian leagues list"),
    (f"{sdb_base}/search_all_leagues.php?c=Romania&s=Soccer", "sportsdb_ro_soccer_leagues.json", "Romanian soccer leagues"),
    # Try different events queries
    (f"{sdb_base}/eventsround.php?id=4728&r=1&s=2024-2025", "sportsdb_ro_round1.json", "RO Liga 1 Round 1"),
    (f"{sdb_base}/eventspastleague.php?id=4728", "sportsdb_ro_past_events.json", "RO Liga 1 past events"),
    # Lookup league details
    (f"{sdb_base}/lookupleague.php?id=4728", "sportsdb_ro_league_detail.json", "RO Liga 1 details"),
    (f"{sdb_base}/lookupleague.php?id=4729", "sportsdb_ro2_league_detail.json", "RO Liga 2 details"),
    # EPL standings (known to work)
    (f"{sdb_base}/lookuptable.php?l=4328&s=2024-2025", "sportsdb_epl_standings.json", "EPL standings 24-25"),
    (f"{sdb_base}/lookuptable.php?l=4335&s=2024-2025", "sportsdb_laliga_standings.json", "La Liga standings 24-25"),
    (f"{sdb_base}/lookuptable.php?l=4332&s=2024-2025", "sportsdb_seriea_standings.json", "Serie A standings 24-25"),
    (f"{sdb_base}/lookuptable.php?l=4331&s=2024-2025", "sportsdb_bundesliga_standings.json", "Bundesliga standings 24-25"),
    (f"{sdb_base}/lookuptable.php?l=4334&s=2024-2025", "sportsdb_ligue1_standings.json", "Ligue 1 standings 24-25"),
]

for url, fname, desc in sdb_urls:
    download_file(url, fname, desc)
    time.sleep(1.0)


# =========================================================================
# 5. Try FBref-style data from alternative sources
# =========================================================================
print("\n" + "=" * 70)
print("5. ADDITIONAL DATA SOURCES")
print("=" * 70)

# Try the free football API from api-football (v3) with demo
# Or use football-web-pages / flashscore data
# Let's try a few more free endpoints

extra_urls = [
    # OpenFootball data (YAML-based, but try JSON endpoints)
    ("https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/en.1.json",
     "openfootball_epl_2425.json", "OpenFootball EPL 24-25"),
    ("https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/de.1.json",
     "openfootball_bundesliga_2425.json", "OpenFootball Bundesliga 24-25"),
    ("https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/es.1.json",
     "openfootball_laliga_2425.json", "OpenFootball La Liga 24-25"),
    ("https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/it.1.json",
     "openfootball_seriea_2425.json", "OpenFootball Serie A 24-25"),
    ("https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/fr.1.json",
     "openfootball_ligue1_2425.json", "OpenFootball Ligue 1 24-25"),
]

for url, fname, desc in extra_urls:
    download_file(url, fname, desc)
    time.sleep(0.5)


# =========================================================================
# SUMMARY
# =========================================================================
print("\n" + "=" * 70)
print("DOWNLOAD COMPLETE — Files in:", DATA_DIR)
print("=" * 70)
total_size = 0
for f in sorted(os.listdir(DATA_DIR)):
    size = os.path.getsize(os.path.join(DATA_DIR, f))
    total_size += size
    marker = "✓" if size > 100 else "✗"
    print(f"  {marker} {f:50s} {size:>12,} bytes")
print(f"\n  Total: {total_size:,} bytes ({total_size/1024:.1f} KB)")
