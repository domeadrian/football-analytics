"""
Fetch Romanian team data by searching for each team individually,
and get all match events with full detail.
"""
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

# Romanian SuperLiga teams (from standings/events we already know)
RO_TEAMS = [
    "FCSB", "CFR Cluj", "Universitatea Craiova", "Universitatea Cluj",
    "Dinamo Bucuresti", "Rapid Bucuresti", "Petrolul Ploiesti",
    "Sepsi OSK", "FC Hermannstadt", "Farul Constanta",
    "FC Botosani", "Politehnica Iasi", "Uta Arad",
    "Otelul Galati", "Unirea Slobozia", "Gloria Buzau",
]

# Liga II teams (common ones)
RO2_TEAMS = [
    "Steaua Bucuresti", "Corvinul Hunedoara", "Csikszereda",
    "Metaloglobus Bucuresti", "ASU Politehnica Timisoara",
    "Concordia Chiajna", "Poli Timisoara", "Juventus Bucuresti",
    "FC Arges", "Progresul Spartac", "Ceahlaul Piatra Neamt",
    "FC Brasov", "FK Miercurea Ciuc", "Recea",
    "Viitorul Pandurii", "Chindia Targoviste",
]

print("=" * 70)
print("SEARCHING FOR ROMANIAN TEAMS")
print("=" * 70)

all_team_data = []

for team_name in RO_TEAMS + RO2_TEAMS:
    print(f"  Searching: {team_name}...", end=" ")
    try:
        r = session.get(f"{SDB}/searchteams.php?t={team_name.replace(' ', '%20')}", timeout=15)
        data = r.json()
        teams = data.get("teams")
        if teams:
            # Find the Romanian one
            for t in teams:
                if t.get("strCountry") in ["Romania", "România"]:
                    all_team_data.append(t)
                    print(f"Found! ID:{t['idTeam']} {t['strTeam']} ({t.get('strLeague')})")
                    break
            else:
                # Take first result
                t = teams[0]
                all_team_data.append(t)
                print(f"Found (best match): {t['strTeam']} ({t.get('strCountry')}) ({t.get('strLeague')})")
        else:
            print("Not found")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1)

print(f"\nTotal teams found: {len(all_team_data)}")

# Save team data
with open(os.path.join(DATA, "ro_all_teams_searched.json"), "w", encoding="utf-8") as f:
    json.dump(all_team_data, f, indent=2, ensure_ascii=False)

# Now fetch players for each found team
print("\n" + "=" * 70)
print("FETCHING PLAYERS FOR FOUND TEAMS")
print("=" * 70)

all_players = []
for team in all_team_data:
    tid = team["idTeam"]
    tname = team["strTeam"]
    tleague = team.get("strLeague", "Unknown")
    print(f"  Players: {tname} ({tleague})...", end=" ")
    try:
        r = session.get(f"{SDB}/lookup_all_players.php?id={tid}", timeout=15)
        data = r.json()
        players = data.get("player", [])
        if players:
            for p in players:
                p["_teamName"] = tname
                p["_teamLeague"] = tleague
                p["_teamId"] = tid
            all_players.extend(players)
            print(f"{len(players)} players")
        else:
            print("No player data")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1.2)

print(f"\nTotal players found: {len(all_players)}")

with open(os.path.join(DATA, "ro_all_players.json"), "w", encoding="utf-8") as f:
    json.dump(all_players, f, indent=2, ensure_ascii=False)

# =====================================================================
# GET MORE MATCH DATA — try all rounds
# =====================================================================
print("\n" + "=" * 70)
print("FETCHING ALL ROUNDS FOR LIGA I 2024-2025")
print("=" * 70)

all_matches = []
for rnd in range(1, 40):
    print(f"  Round {rnd}...", end=" ")
    try:
        r = session.get(f"{SDB}/eventsround.php?id=4691&r={rnd}&s=2024-2025", timeout=15)
        data = r.json()
        events = data.get("events")
        if events:
            all_matches.extend(events)
            print(f"{len(events)} matches")
        else:
            print("No matches")
            if rnd > 5:  # Stop if we've passed the first rounds with no data
                empty_count = sum(1 for m in range(rnd-3, rnd+1))
                break
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(0.8)

print(f"\nTotal Liga I matches: {len(all_matches)}")

with open(os.path.join(DATA, "ro1_all_matches_2425.json"), "w", encoding="utf-8") as f:
    json.dump(all_matches, f, indent=2, ensure_ascii=False)

# Liga II rounds
print("\n" + "=" * 70)
print("FETCHING ALL ROUNDS FOR LIGA II 2024-2025")
print("=" * 70)

all_matches_l2 = []
for rnd in range(1, 40):
    print(f"  Round {rnd}...", end=" ")
    try:
        r = session.get(f"{SDB}/eventsround.php?id=4665&r={rnd}&s=2024-2025", timeout=15)
        data = r.json()
        events = data.get("events")
        if events:
            all_matches_l2.extend(events)
            print(f"{len(events)} matches")
        else:
            print("No matches")
            if rnd > 5:
                break
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(0.8)

print(f"\nTotal Liga II matches: {len(all_matches_l2)}")

with open(os.path.join(DATA, "ro2_all_matches_2425.json"), "w", encoding="utf-8") as f:
    json.dump(all_matches_l2, f, indent=2, ensure_ascii=False)


# =====================================================================
# SUMMARY
# =====================================================================
print("\n" + "=" * 70)
print("FINAL DATA SUMMARY")
print("=" * 70)
print(f"  Romanian teams found: {len(all_team_data)}")
print(f"  Total players: {len(all_players)}")
print(f"  Liga I matches 24-25: {len(all_matches)}")
print(f"  Liga II matches 24-25: {len(all_matches_l2)}")
total = 0
for f in sorted(os.listdir(DATA)):
    size = os.path.getsize(os.path.join(DATA, f))
    total += size
print(f"  Total data size: {total/1024:.1f} KB")
