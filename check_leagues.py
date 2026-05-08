"""Check what TheSportsDB actually returns for league 4691 teams."""
import json

with open(r"C:\Users\adomente\football_analytics\data\ro1_teams.json", encoding="utf-8") as f:
    data = json.load(f)

teams = data.get("teams", [])
print(f"Teams returned for league 4691: {len(teams)}")
for t in teams:
    print(f"  ID:{t['idTeam']} {t['strTeam']} — Country: {t.get('strCountry')} — League: {t.get('strLeague')} (LeagueID: {t.get('idLeague')})")

print("\n\nChecking standings...")
with open(r"C:\Users\adomente\football_analytics\data\ro1_standings_20242025.json", encoding="utf-8") as f:
    data = json.load(f)
table = data.get("table", [])
print(f"Standings entries: {len(table)}")
for t in table:
    print(f"  {t.get('intRank')}. {t.get('strTeam')} — Pts:{t.get('intPoints')} GF:{t.get('intGoalsFor')} GA:{t.get('intGoalsAgainst')}")

print("\n\nChecking events...")
with open(r"C:\Users\adomente\football_analytics\data\ro1_events_20242025.json", encoding="utf-8") as f:
    data = json.load(f)
events = data.get("events", [])
print(f"Events: {len(events)}")
for e in events[:5]:
    print(f"  {e.get('dateEvent')} {e.get('strHomeTeam')} {e.get('intHomeScore')}-{e.get('intAwayScore')} {e.get('strAwayTeam')} (Round {e.get('intRound')})")
