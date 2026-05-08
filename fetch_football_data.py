"""
Fetch real football data from multiple free sources:
1. Football-Data.co.uk — Romanian Liga 1 match results + betting odds (CSV)
2. Football-Data.co.uk — Multiple European leagues for comparison
3. FBref/Wikipedia — Player stats via public tables
"""

import urllib.request
import os
import ssl
import json
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Disable SSL verification for corporate proxies
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def download(url, filename, desc=""):
    path = os.path.join(DATA_DIR, filename)
    print(f"Downloading {desc or filename}...")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = resp.read()
            with open(path, "wb") as f:
                f.write(data)
            print(f"  OK — {len(data):,} bytes → {filename}")
            return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


# =========================================================================
# 1. Football-Data.co.uk — Romanian Liga 1 (multiple seasons)
# =========================================================================
print("=" * 60)
print("FOOTBALL-DATA.CO.UK — Romanian Liga 1 + European Leagues")
print("=" * 60)

# Romanian Liga 1 — seasons 2018-2025
ro_seasons = {
    "RO1_2425.csv": "https://www.football-data.co.uk/mmz4281/2425/RO1.csv",
    "RO1_2324.csv": "https://www.football-data.co.uk/mmz4281/2324/RO1.csv",
    "RO1_2223.csv": "https://www.football-data.co.uk/mmz4281/2223/RO1.csv",
    "RO1_2122.csv": "https://www.football-data.co.uk/mmz4281/2122/RO1.csv",
    "RO1_2021.csv": "https://www.football-data.co.uk/mmz4281/2021/RO1.csv",
    "RO1_1920.csv": "https://www.football-data.co.uk/mmz4281/1920/RO1.csv",
    "RO1_1819.csv": "https://www.football-data.co.uk/mmz4281/1819/RO1.csv",
}

for fname, url in ro_seasons.items():
    download(url, fname, f"Romania Liga 1 {fname[:10]}")
    time.sleep(0.5)

# Major European leagues — 2024-25 for comparison
euro_leagues = {
    "EPL_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/E0.csv", "England Premier League 24-25"),
    "LaLiga_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/SP1.csv", "Spain La Liga 24-25"),
    "SerieA_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/I1.csv", "Italy Serie A 24-25"),
    "Bundesliga_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/D1.csv", "Germany Bundesliga 24-25"),
    "Ligue1_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/F1.csv", "France Ligue 1 24-25"),
    "Eredivisie_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/N1.csv", "Netherlands Eredivisie 24-25"),
    "PortugalLiga_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/P1.csv", "Portugal Liga 24-25"),
    "TurkeySuperLig_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/T1.csv", "Turkey Super Lig 24-25"),
    "Belgium_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/B1.csv", "Belgium Jupiler 24-25"),
    "Greece_2425.csv": ("https://www.football-data.co.uk/mmz4281/2425/G1.csv", "Greece Super League 24-25"),
}

for fname, (url, desc) in euro_leagues.items():
    download(url, fname, desc)
    time.sleep(0.5)


# =========================================================================
# 2. API-Football (free tier via RapidAPI) — Romanian Superliga standings
#    We'll try the free football-api alternatives
# =========================================================================
print("\n" + "=" * 60)
print("OPEN FOOTBALL DATA — Additional sources")
print("=" * 60)

# Try OpenLigaDB for additional data
# Try free football APIs
apis_to_try = [
    # Football-data.org (free tier, 10 requests/min)
    {
        "url": "https://api.football-data.org/v4/competitions/PPL/standings",
        "headers": {"X-Auth-Token": "test"},
        "filename": "fdorg_standings.json",
        "desc": "Football-data.org standings",
    },
]

for api in apis_to_try:
    try:
        req = urllib.request.Request(api["url"], headers={
            **api.get("headers", {}),
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = resp.read()
            with open(os.path.join(DATA_DIR, api["filename"]), "wb") as f:
                f.write(data)
            print(f"  OK — {api['desc']}: {len(data):,} bytes")
    except Exception as e:
        print(f"  {api['desc']}: {e}")


# =========================================================================
# 3. Transfermarkt-style data via free sources
# =========================================================================
print("\n" + "=" * 60)
print("ATTEMPTING ADDITIONAL FREE API DATA")
print("=" * 60)

# Try to get Romanian league data from TheSportsDB (free API)
sportsdb_urls = [
    ("https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=Romanian%20First%20Division", "sportsdb_ro_teams.json", "Romanian teams"),
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4728&s=2024-2025", "sportsdb_ro_standings_2425.json", "RO Liga 1 standings 24-25"),
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4728&s=2023-2024", "sportsdb_ro_standings_2324.json", "RO Liga 1 standings 23-24"),
    ("https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4728&s=2024-2025", "sportsdb_ro_matches_2425.json", "RO Liga 1 matches 24-25"),
    ("https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4728&s=2023-2024", "sportsdb_ro_matches_2324.json", "RO Liga 1 matches 23-24"),
    # Romanian Liga 2
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4729&s=2024-2025", "sportsdb_ro2_standings_2425.json", "RO Liga 2 standings 24-25"),
    ("https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4729&s=2024-2025", "sportsdb_ro2_matches_2425.json", "RO Liga 2 matches 24-25"),
    # Top 5 league standings
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4328&s=2024-2025", "sportsdb_epl_standings.json", "EPL standings"),
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4335&s=2024-2025", "sportsdb_laliga_standings.json", "La Liga standings"),
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4332&s=2024-2025", "sportsdb_seriea_standings.json", "Serie A standings"),
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4331&s=2024-2025", "sportsdb_bundesliga_standings.json", "Bundesliga standings"),
]

for url, fname, desc in sportsdb_urls:
    download(url, fname, desc)
    time.sleep(1)


# =========================================================================
# 4. Try to get Romanian Liga 2 from football-data.co.uk
# =========================================================================
print("\n" + "=" * 60)
print("ROMANIAN LIGA 2")
print("=" * 60)

# Football-data.co.uk doesn't have Liga 2, so we rely on TheSportsDB above
# Also try alternative league IDs for Liga 2 on TheSportsDB
liga2_extras = [
    ("https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=Romanian%20Second%20Division", "sportsdb_ro2_teams.json", "Romanian Liga 2 teams"),
    ("https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4729&s=2023-2024", "sportsdb_ro2_standings_2324.json", "RO Liga 2 standings 23-24"),
]

for url, fname, desc in liga2_extras:
    download(url, fname, desc)
    time.sleep(1)


# =========================================================================
# SUMMARY
# =========================================================================
print("\n" + "=" * 60)
print("DOWNLOAD COMPLETE — Files in:", DATA_DIR)
print("=" * 60)
for f in sorted(os.listdir(DATA_DIR)):
    size = os.path.getsize(os.path.join(DATA_DIR, f))
    print(f"  {f:45s} {size:>10,} bytes")
