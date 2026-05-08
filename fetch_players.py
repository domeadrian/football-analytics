"""Fetch player data for all Romanian Liga I and Liga II teams."""
import requests
import json
import os
import time

DATA = r"C:\Users\adomente\football_analytics\data"
session = requests.Session()
session.verify = False
session.headers.update({"User-Agent": "Mozilla/5.0"})
import urllib3
urllib3.disable_warnings()

SDB = "https://www.thesportsdb.com/api/v1/json/3"

# Load teams
with open(os.path.join(DATA, "ro1_teams.json"), encoding="utf-8") as f:
    ro1_teams = json.load(f).get("teams", [])

with open(os.path.join(DATA, "ro2_teams.json"), encoding="utf-8") as f:
    ro2_teams = json.load(f).get("teams", [])

print(f"Liga I teams: {len(ro1_teams)}")
print(f"Liga II teams: {len(ro2_teams)}")

all_teams = []
for t in ro1_teams:
    all_teams.append((t["idTeam"], t["strTeam"], "Liga I"))
for t in ro2_teams:
    all_teams.append((t["idTeam"], t["strTeam"], "Liga II"))

# Deduplicate by id
seen = set()
unique_teams = []
for tid, tname, league in all_teams:
    if tid not in seen:
        seen.add(tid)
        unique_teams.append((tid, tname, league))

print(f"Unique teams to fetch players for: {len(unique_teams)}")

all_players = []
for tid, tname, league in unique_teams:
    print(f"  Fetching players: {tname} ({league})...", end=" ")
    try:
        r = session.get(f"{SDB}/lookup_all_players.php?id={tid}", timeout=15)
        data = r.json()
        players = data.get("player", [])
        if players:
            for p in players:
                p["_team"] = tname
                p["_league"] = league
                p["_teamId"] = tid
            all_players.extend(players)
            print(f"{len(players)} players")
        else:
            print("No players")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1.2)

print(f"\nTotal players: {len(all_players)}")

# Save all players
with open(os.path.join(DATA, "all_ro_players.json"), "w", encoding="utf-8") as f:
    json.dump(all_players, f, indent=2, ensure_ascii=False)

print(f"Saved to all_ro_players.json ({os.path.getsize(os.path.join(DATA, 'all_ro_players.json')):,} bytes)")

# Print sample
if all_players:
    print("\nSample player keys:", list(all_players[0].keys())[:20])
    for p in all_players[:5]:
        print(f"  {p.get('strPlayer')} — {p.get('strPosition')} — {p.get('_team')} — Born: {p.get('dateBorn')} — Nationality: {p.get('strNationality')}")
