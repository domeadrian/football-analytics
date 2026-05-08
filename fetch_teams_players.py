"""
Fetch team details and players using CORRECT team IDs from standings.
The lookup_all_teams endpoint is broken on free tier (returns wrong teams).
Instead we use idTeam from standings + searchteams for additional teams from events.
"""

import json
import os
import time
import glob
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"

session = requests.Session()
session.headers["User-Agent"] = "FootballAnalytics/1.0"
session.verify = False

LEAGUE_NAMES = {
    4328: "English Premier League",
    4335: "La Liga",
    4332: "Serie A",
    4331: "Bundesliga",
    4334: "Ligue 1",
    4337: "Eredivisie",
    4344: "Primeira Liga",
    4339: "Turkish Super Lig",
    4355: "Belgian Pro League",
    4330: "Scottish Premiership",
    4340: "Austrian Bundesliga",
    4691: "Romanian Liga I",
    4665: "Romanian Liga II",
}


def safe_get(url, retries=2):
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                print(f" [429 rate limit]", end="", flush=True)
                time.sleep(5)
                continue
            print(f" [HTTP {r.status_code}]", end="", flush=True)
        except Exception as e:
            print(f" [err]", end="", flush=True)
        time.sleep(2 * (attempt + 1))
    return None


def save(data, filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 1. COLLECT TEAM IDs FROM STANDINGS ─────────────────────────────────
print("=" * 60)
print("STEP 1: Collecting team IDs from standings files")
print("=" * 60)

team_ids = {}  # team_id -> {name, league, league_id, standings_data}

for fname in glob.glob(os.path.join(DATA_DIR, "standings_2526_*.json")):
    with open(fname, encoding="utf-8") as f:
        data = json.load(f)
    table = data.get("table", [])
    for entry in table:
        tid = entry.get("idTeam")
        lid = entry.get("idLeague")
        if tid and lid:
            lid_int = int(lid)
            team_ids[tid] = {
                "name": entry.get("strTeam", ""),
                "league": LEAGUE_NAMES.get(lid_int, entry.get("strLeague", "")),
                "league_id": lid_int,
                "rank": int(entry.get("intRank", 0)),
                "points": int(entry.get("intPoints", 0)),
                "badge": entry.get("strBadge", ""),
            }

# Also collect teams from events
for fname in glob.glob(os.path.join(DATA_DIR, "events_2526_*.json")):
    with open(fname, encoding="utf-8") as f:
        data = json.load(f)
    events = data.get("events", [])
    for ev in events:
        lid = ev.get("idLeague")
        if not lid:
            continue
        lid_int = int(lid)
        league_name = LEAGUE_NAMES.get(lid_int, "")
        for side in [("idHomeTeam", "strHomeTeam"), ("idAwayTeam", "strAwayTeam")]:
            tid = ev.get(side[0])
            tname = ev.get(side[1])
            if tid and tid not in team_ids:
                team_ids[tid] = {
                    "name": tname or "",
                    "league": league_name,
                    "league_id": lid_int,
                    "rank": 0,
                    "points": 0,
                    "badge": "",
                }

print(f"Found {len(team_ids)} unique teams across all standings & events")
for lid_int in sorted(set(t["league_id"] for t in team_ids.values())):
    league_teams = [t for t in team_ids.values() if t["league_id"] == lid_int]
    name = league_teams[0]["league"] if league_teams else str(lid_int)
    print(f"  {name}: {len(league_teams)} teams")

# ── 2. FETCH TEAM DETAILS ─────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 2: Fetching team details via lookupteam.php")
print("=" * 60)

all_teams_details = []
for i, (tid, info) in enumerate(team_ids.items()):
    print(f"  [{i+1}/{len(team_ids)}] {info['name']}", end="", flush=True)
    url = f"{BASE}/lookupteam.php?id={tid}"
    data = safe_get(url)
    if data and data.get("teams"):
        team = data["teams"][0]
        team["_leagueName"] = info["league"]
        team["_leagueId"] = info["league_id"]
        team["_standingsRank"] = info["rank"]
        team["_standingsPoints"] = info["points"]
        all_teams_details.append(team)
        print(f" OK ({team.get('strStadium', 'N/A')})")
    else:
        # Fallback: create from standings data
        all_teams_details.append({
            "idTeam": tid,
            "strTeam": info["name"],
            "_leagueName": info["league"],
            "_leagueId": info["league_id"],
            "_standingsRank": info["rank"],
            "_standingsPoints": info["points"],
            "strBadge": info["badge"],
        })
        print(" (from standings)")
    time.sleep(1.2)  # respect rate limit

save(all_teams_details, "all_teams_2526.json")
print(f"\n-> Saved {len(all_teams_details)} team details to all_teams_2526.json")

# ── 3. FETCH PLAYERS ──────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 3: Fetching players for each team")
print("=" * 60)

all_players = []
success = 0
failed = 0

for i, (tid, info) in enumerate(team_ids.items()):
    print(f"  [{i+1}/{len(team_ids)}] {info['name']} ({info['league']})", end="", flush=True)
    url = f"{BASE}/lookup_all_players.php?id={tid}"
    data = safe_get(url)
    if data and data.get("player"):
        players = data["player"]
        for p in players:
            p["_teamName"] = info["name"]
            p["_teamId"] = tid
            p["_leagueName"] = info["league"]
            p["_leagueId"] = info["league_id"]
        all_players.extend(players)
        success += 1
        print(f" -> {len(players)} players")
    else:
        failed += 1
        print(" -> no data")
    time.sleep(1.5)  # slightly longer pause for player queries

    # Checkpoint every 15 teams
    if (i + 1) % 15 == 0:
        save(all_players, "all_players_2526.json")
        print(f"  --- Checkpoint: {len(all_players)} players from {success} teams ---")

# Final save
save(all_players, "all_players_2526.json")
print(f"\n-> Saved {len(all_players)} players to all_players_2526.json")
print(f"   Success: {success} teams | Failed: {failed} teams")

# ── 4. BUILD LEAGUE INDEX ─────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 4: Building league index")
print("=" * 60)

index = {"season": "2025-2026", "leagues": {}}
for lid_int, lname in LEAGUE_NAMES.items():
    league_teams = [t for t in all_teams_details if t.get("_leagueId") == lid_int]
    league_players = [p for p in all_players if p.get("_leagueId") == lid_int]
    standings_file = f"standings_2526_{lid_int}.json"
    events_file = f"events_2526_{lid_int}.json"
    index["leagues"][lname] = {
        "league_id": lid_int,
        "teams_count": len(league_teams),
        "players_count": len(league_players),
        "standings_file": standings_file if os.path.exists(os.path.join(DATA_DIR, standings_file)) else None,
        "events_file": events_file if os.path.exists(os.path.join(DATA_DIR, events_file)) else None,
    }
    print(f"  {lname}: {len(league_teams)} teams, {len(league_players)} players")

save(index, "league_index_2526.json")
print(f"\n{'=' * 60}")
print("DONE!")
print("=" * 60)
