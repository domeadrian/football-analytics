"""
Fetch 2025-2026 season data for all major European leagues.
TheSportsDB free API (key=3).
- Standings per league
- All teams per league
- Players per team (top players)
- Match events per league
"""

import json
import os
import time
import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"
SEASON = "2025-2026"

LEAGUES = {
    "English Premier League":  4328,
    "La Liga":                 4335,
    "Serie A":                 4332,
    "Bundesliga":              4331,
    "Ligue 1":                 4334,
    "Eredivisie":              4337,
    "Primeira Liga":           4344,
    "Turkish Super Lig":       4339,
    "Belgian Pro League":      4355,
    "Scottish Premiership":    4330,
    "Swiss Super League":      4532,
    "Austrian Bundesliga":     4340,
    "Greek Super League":      4344,  # may overlap, will de-dup
    "Romanian Liga I":         4691,
    "Romanian Liga II":        4665,
}

# De-dup IDs
seen_ids = set()
deduped = {}
for name, lid in LEAGUES.items():
    if lid not in seen_ids:
        deduped[name] = lid
        seen_ids.add(lid)
LEAGUES = deduped

session = requests.Session()
session.headers["User-Agent"] = "FootballAnalytics/1.0"
session.verify = False

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def safe_get(url, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            print(f"  HTTP {r.status_code} for {url}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1.5 * (attempt + 1))
    return None


def save(data, filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  -> Saved {filename}")


# ── 1. STANDINGS ─────────────────────────────────────────────────────────
print("=" * 60)
print("FETCHING STANDINGS (2025-2026)")
print("=" * 60)
all_standings = {}
for league_name, league_id in LEAGUES.items():
    print(f"\n[Standings] {league_name} (ID {league_id})...")
    url = f"{BASE}/lookuptable.php?l={league_id}&s={SEASON}"
    data = safe_get(url)
    if data and data.get("table"):
        n = len(data["table"])
        print(f"  Got {n} teams in standings")
        fname = f"standings_2526_{league_id}.json"
        save(data, fname)
        all_standings[league_name] = {
            "league_id": league_id,
            "file": fname,
            "count": n,
            "table": data["table"],
        }
    else:
        # Try current season format "2025" instead of "2025-2026"
        url2 = f"{BASE}/lookuptable.php?l={league_id}&s=2025"
        data2 = safe_get(url2)
        if data2 and data2.get("table"):
            n = len(data2["table"])
            print(f"  Got {n} teams (season='2025')")
            fname = f"standings_2526_{league_id}.json"
            save(data2, fname)
            all_standings[league_name] = {
                "league_id": league_id,
                "file": fname,
                "count": n,
                "table": data2["table"],
            }
        else:
            print(f"  No standings data yet for {SEASON}")
    time.sleep(0.8)

print(f"\n>>> Standings fetched for {len(all_standings)} leagues")

# ── 2. TEAMS ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FETCHING TEAMS PER LEAGUE")
print("=" * 60)
all_teams = {}
team_id_map = {}  # team_id -> {name, league}
for league_name, league_id in LEAGUES.items():
    print(f"\n[Teams] {league_name} (ID {league_id})...")
    url = f"{BASE}/lookup_all_teams.php?id={league_id}"
    data = safe_get(url)
    if data and data.get("teams"):
        teams = data["teams"]
        n = len(teams)
        print(f"  Got {n} teams")
        fname = f"teams_2526_{league_id}.json"
        save({"teams": teams}, fname)
        all_teams[league_name] = {
            "league_id": league_id,
            "file": fname,
            "count": n,
        }
        for t in teams:
            tid = t.get("idTeam")
            if tid:
                team_id_map[tid] = {
                    "name": t.get("strTeam", ""),
                    "league": league_name,
                    "league_id": league_id,
                }
    else:
        print(f"  No teams data")
    time.sleep(0.8)

print(f"\n>>> Teams fetched for {len(all_teams)} leagues, {len(team_id_map)} total teams")

# ── 3. EVENTS (2025-2026) ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FETCHING MATCH EVENTS (2025-2026)")
print("=" * 60)
all_events = {}
for league_name, league_id in LEAGUES.items():
    print(f"\n[Events] {league_name} (ID {league_id})...")
    url = f"{BASE}/eventsseason.php?id={league_id}&s={SEASON}"
    data = safe_get(url)
    if data and data.get("events"):
        n = len(data["events"])
        print(f"  Got {n} events")
        fname = f"events_2526_{league_id}.json"
        save(data, fname)
        all_events[league_name] = {"file": fname, "count": n}
    else:
        # Try "2025"
        url2 = f"{BASE}/eventsseason.php?id={league_id}&s=2025"
        data2 = safe_get(url2)
        if data2 and data2.get("events"):
            n = len(data2["events"])
            print(f"  Got {n} events (season='2025')")
            fname = f"events_2526_{league_id}.json"
            save(data2, fname)
            all_events[league_name] = {"file": fname, "count": n}
        else:
            print(f"  No events yet")
    time.sleep(0.8)

print(f"\n>>> Events fetched for {len(all_events)} leagues")

# ── 4. PLAYERS ────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FETCHING PLAYERS PER TEAM")
print("=" * 60)
all_players = []
player_count = 0
failed_teams = 0
for i, (tid, tinfo) in enumerate(team_id_map.items()):
    tname = tinfo["name"]
    league = tinfo["league"]
    print(f"  [{i+1}/{len(team_id_map)}] {tname} ({league})...", end="")
    url = f"{BASE}/lookup_all_players.php?id={tid}"
    data = safe_get(url)
    if data and data.get("player"):
        players = data["player"]
        for p in players:
            p["_teamName"] = tname
            p["_teamId"] = tid
            p["_leagueName"] = league
        all_players.extend(players)
        player_count += len(players)
        print(f" {len(players)} players")
    else:
        failed_teams += 1
        print(" no data")
    # Rate limit: ~1 request per second
    time.sleep(1.0)

    # Save checkpoint every 20 teams
    if (i + 1) % 20 == 0:
        save(all_players, "players_2526_checkpoint.json")
        print(f"  --- Checkpoint: {player_count} players from {i+1} teams ---")

# Final save
save(all_players, "all_players_2526.json")
print(f"\n>>> Total players: {player_count} from {len(team_id_map) - failed_teams} teams")
print(f">>> Failed teams: {failed_teams}")

# ── 5. SAVE LEAGUE INDEX ─────────────────────────────────────────────────
index = {
    "season": SEASON,
    "leagues": {},
}
for league_name, league_id in LEAGUES.items():
    entry = {"league_id": league_id}
    if league_name in all_standings:
        entry["standings_file"] = all_standings[league_name]["file"]
        entry["standings_count"] = all_standings[league_name]["count"]
    if league_name in all_teams:
        entry["teams_file"] = all_teams[league_name]["file"]
        entry["teams_count"] = all_teams[league_name]["count"]
    if league_name in all_events:
        entry["events_file"] = all_events[league_name]["file"]
        entry["events_count"] = all_events[league_name]["count"]
    index["leagues"][league_name] = entry

save(index, "league_index_2526.json")
print("\n" + "=" * 60)
print("DONE! All data saved to data/ directory")
print("=" * 60)
