"""
Fetch Romanian and European football data with CORRECT league IDs.
"""
import requests
import json
import os
import time

DATA = r"C:\Users\adomente\football_analytics\data"
os.makedirs(DATA, exist_ok=True)

session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

import urllib3
urllib3.disable_warnings()

SDB = "https://www.thesportsdb.com/api/v1/json/3"

def fetch_sdb(endpoint, filename, desc):
    url = f"{SDB}/{endpoint}"
    print(f"  {desc}...", end=" ")
    try:
        r = session.get(url, timeout=20)
        data = r.json()
        with open(os.path.join(DATA, filename), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Count meaningful data
        for key in ["table", "events", "teams", "players", "countrys", "leagues"]:
            if key in data and data[key]:
                print(f"OK — {len(data[key])} {key}")
                return data
        if data:
            print(f"OK — keys: {list(data.keys())}")
        else:
            print("Empty response")
        return data
    except Exception as e:
        print(f"FAILED: {e}")
        return None

# =====================================================================
# ROMANIAN LIGA I (ID=4691) & LIGA II (ID=4665)
# =====================================================================
print("=" * 70)
print("ROMANIAN LIGA I (SuperLiga) — TheSportsDB ID: 4691")
print("=" * 70)

# Teams
fetch_sdb("lookup_all_teams.php?id=4691", "ro1_teams.json", "Liga I Teams")
time.sleep(1)

# Standings (try current + past season)
for season in ["2025-2026", "2024-2025", "2023-2024", "2022-2023"]:
    fetch_sdb(f"lookuptable.php?l=4691&s={season}", f"ro1_standings_{season.replace('-','')}.json", f"Liga I Standings {season}")
    time.sleep(1)

# Past events
fetch_sdb("eventspastleague.php?id=4691", "ro1_past_events.json", "Liga I Recent Matches")
time.sleep(1)

# Next events
fetch_sdb("eventsnextleague.php?id=4691", "ro1_next_events.json", "Liga I Upcoming Matches")
time.sleep(1)

# Season events
for season in ["2024-2025", "2023-2024"]:
    fetch_sdb(f"eventsseason.php?id=4691&s={season}", f"ro1_events_{season.replace('-','')}.json", f"Liga I All Matches {season}")
    time.sleep(1)

print("\n" + "=" * 70)
print("ROMANIAN LIGA II — TheSportsDB ID: 4665")
print("=" * 70)

fetch_sdb("lookup_all_teams.php?id=4665", "ro2_teams.json", "Liga II Teams")
time.sleep(1)

for season in ["2024-2025", "2023-2024"]:
    fetch_sdb(f"lookuptable.php?l=4665&s={season}", f"ro2_standings_{season.replace('-','')}.json", f"Liga II Standings {season}")
    time.sleep(1)

fetch_sdb("eventspastleague.php?id=4665", "ro2_past_events.json", "Liga II Recent Matches")
time.sleep(1)

fetch_sdb("eventsnextleague.php?id=4665", "ro2_next_events.json", "Liga II Upcoming Matches")
time.sleep(1)

for season in ["2024-2025", "2023-2024"]:
    fetch_sdb(f"eventsseason.php?id=4665&s={season}", f"ro2_events_{season.replace('-','')}.json", f"Liga II All Matches {season}")
    time.sleep(1)

# =====================================================================
# Get player data for Romanian teams
# =====================================================================
print("\n" + "=" * 70)
print("PLAYER DATA — Key Romanian Teams")
print("=" * 70)

# First load team IDs
try:
    with open(os.path.join(DATA, "ro1_teams.json")) as f:
        teams_data = json.load(f)
    teams = teams_data.get("teams", [])
    if teams:
        for team in teams:
            tid = team["idTeam"]
            tname = team["strTeam"]
            fetch_sdb(f"lookup_all_players.php?id={tid}", f"players_{tid}_{tname.replace(' ','_')[:20]}.json", f"Players: {tname}")
            time.sleep(1.2)
except Exception as e:
    print(f"  Could not load teams: {e}")

# =====================================================================
# Also get Liga II team players
# =====================================================================
print("\n" + "=" * 70)
print("LIGA II PLAYER DATA")
print("=" * 70)

try:
    with open(os.path.join(DATA, "ro2_teams.json")) as f:
        teams_data = json.load(f)
    teams = teams_data.get("teams", [])
    if teams:
        for team in teams[:20]:  # Limit to 20 teams
            tid = team["idTeam"]
            tname = team["strTeam"]
            fetch_sdb(f"lookup_all_players.php?id={tid}", f"players_{tid}_{tname.replace(' ','_')[:20]}.json", f"Players: {tname}")
            time.sleep(1.2)
except Exception as e:
    print(f"  Could not load Liga II teams: {e}")

# =====================================================================
# EUROPEAN LEAGUE STANDINGS (for comparison)
# =====================================================================
print("\n" + "=" * 70)
print("EUROPEAN LEAGUE STANDINGS (for comparison)")
print("=" * 70)

euro_leagues = {
    4328: "EPL",
    4335: "La Liga",
    4332: "Serie A",
    4331: "Bundesliga",
    4334: "Ligue 1",
    4337: "Eredivisie",
    4344: "Primeira Liga",
    4339: "Super Lig",
    4355: "Belgian Pro League",
}

for lid, name in euro_leagues.items():
    fetch_sdb(f"lookuptable.php?l={lid}&s=2024-2025", f"euro_{name.lower().replace(' ','_')}_standings.json", f"{name} Standings")
    time.sleep(1)


# =====================================================================
# FOOTBALL-DATA.ORG — Romanian Liga I & II
# =====================================================================
print("\n" + "=" * 70)
print("FOOTBALL-DATA.ORG API — Romanian Leagues")
print("=" * 70)

fdorg_base = "https://api.football-data.org/v4"

def fetch_fdorg(endpoint, filename, desc):
    url = f"{fdorg_base}/{endpoint}"
    print(f"  {desc}...", end=" ")
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            with open(os.path.join(DATA, filename), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"OK ({len(r.content):,} bytes)")
            return data
        else:
            print(f"HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"FAILED: {e}")
        return None

# Romanian Liga I
fetch_fdorg("competitions/RL1/standings", "fdorg_ro1_standings.json", "Liga I Standings")
time.sleep(1)
fetch_fdorg("competitions/RL1/matches", "fdorg_ro1_matches.json", "Liga I All Matches")
time.sleep(1)
fetch_fdorg("competitions/RL1/scorers", "fdorg_ro1_scorers.json", "Liga I Top Scorers")
time.sleep(1)
fetch_fdorg("competitions/RL1/teams", "fdorg_ro1_teams.json", "Liga I Teams Detail")
time.sleep(1)

# Major leagues (free tier)
for code, name in [("PL", "EPL"), ("PD", "La Liga"), ("SA", "Serie A"), ("BL1", "Bundesliga"), ("FL1", "Ligue 1")]:
    fetch_fdorg(f"competitions/{code}/standings", f"fdorg_{name.lower().replace(' ','_')}_standings.json", f"{name} Standings")
    time.sleep(1.5)
    fetch_fdorg(f"competitions/{code}/scorers", f"fdorg_{name.lower().replace(' ','_')}_scorers.json", f"{name} Top Scorers")
    time.sleep(1.5)


# =====================================================================
# SUMMARY
# =====================================================================
print("\n" + "=" * 70)
print("DOWNLOAD COMPLETE")
print("=" * 70)
total = 0
good = 0
for f in sorted(os.listdir(DATA)):
    size = os.path.getsize(os.path.join(DATA, f))
    total += size
    if size > 100:
        good += 1
    marker = "✓" if size > 100 else "✗"
    print(f"  {marker} {f:55s} {size:>10,} bytes")
print(f"\n  Files with data: {good}, Total size: {total/1024:.1f} KB")
