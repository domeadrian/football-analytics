import json

# Check events for player-level data (goals, assists, cards, lineups etc.)
with open("data/all_events_2526_4328.json", encoding="utf-8") as f:
    events = json.load(f)

ev = events["events"][0]
# Print ALL keys
print("ALL EVENT KEYS:")
for k in sorted(ev.keys()):
    v = ev[k]
    if v and str(v).strip() and str(v) != "None":
        print(f"  {k}: {str(v)[:200]}")

print("\n---\nChecking a few more events for player data...")
for ev in events["events"][:5]:
    for key in ["strHomeLineupGoalkeeper", "strHomeLineupDefense", "strHomeLineupMidfield", 
                "strHomeLineupForward", "strHomeLineupSubstitutes",
                "strAwayLineupGoalkeeper", "strAwayLineupDefense", "strAwayLineupMidfield",
                "strAwayLineupForward", "strAwayLineupSubstitutes",
                "strHomeGoalDetails", "strAwayGoalDetails", 
                "strHomeRedCards", "strAwayRedCards",
                "strHomeYellowCards", "strAwayYellowCards",
                "intHomeShots", "intAwayShots",
                "intHomeShotsOnTarget", "intAwayShotsOnTarget",
                "strStatistics", "strResult"]:
        val = ev.get(key)
        if val and str(val).strip() and str(val) != "None":
            print(f"  {key}: {str(val)[:300]}")
    print("---")

# Check player data for any performance fields
with open("data/all_players_2526.json", encoding="utf-8") as f:
    players = json.load(f)

print("\n\nALL PLAYER KEYS:")
for k in sorted(players[0].keys()):
    v = players[0][k]
    if v and str(v).strip() and str(v) != "None":
        print(f"  {k}: {str(v)[:200]}")

# Check if any player has stats
print("\n\nChecking for stats-like fields across multiple players...")
stat_keys = set()
for p in players[:100]:
    for k, v in p.items():
        if v and str(v).strip() and str(v) != "None":
            stat_keys.add(k)
print("Non-null fields found:", sorted(stat_keys))
