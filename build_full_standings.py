"""Build full standings from match events + API standings. Also fetch all remaining matches."""
import requests, json, os, time, urllib3, glob
urllib3.disable_warnings()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"
SEASON = "2025-2026"

session = requests.Session()
session.verify = False

LEAGUES = {
    4328: ("English Premier League", 38, 20),
    4335: ("La Liga", 38, 20),
    4332: ("Serie A", 38, 20),
    4331: ("Bundesliga", 34, 18),
    4334: ("Ligue 1", 34, 18),
    4337: ("Eredivisie", 34, 18),
    4344: ("Primeira Liga", 34, 18),
    4339: ("Turkish Super Lig", 38, 19),
    4338: ("Belgian Pro League", 30, 16),
    4355: ("Russian Premier League", 30, 16),
    4330: ("Scottish Premiership", 38, 12),
    4340: ("Danish Superliga", 32, 12),
    4336: ("Greek Super League", 30, 14),
    4691: ("Romanian Liga I", 30, 16),
    4665: ("Romanian Liga II", 38, 20),
}

def build_table_from_events(events):
    """Build a full standings table from match events."""
    teams = {}
    for e in events:
        hs = e.get("intHomeScore")
        aws = e.get("intAwayScore")
        if hs is None or aws is None:
            continue
        hs, aws = int(hs), int(aws)
        ht = e.get("strHomeTeam", "")
        at = e.get("strAwayTeam", "")
        if not ht or not at:
            continue
        for t in [ht, at]:
            if t not in teams:
                teams[t] = {"strTeam": t, "intPlayed": 0, "intWin": 0, "intDraw": 0,
                            "intLoss": 0, "intGoalsFor": 0, "intGoalsAgainst": 0,
                            "intGoalDifference": 0, "intPoints": 0}
        # Home
        teams[ht]["intPlayed"] += 1
        teams[ht]["intGoalsFor"] += hs
        teams[ht]["intGoalsAgainst"] += aws
        # Away
        teams[at]["intPlayed"] += 1
        teams[at]["intGoalsFor"] += aws
        teams[at]["intGoalsAgainst"] += hs
        if hs > aws:
            teams[ht]["intWin"] += 1; teams[ht]["intPoints"] += 3
            teams[at]["intLoss"] += 1
        elif hs < aws:
            teams[at]["intWin"] += 1; teams[at]["intPoints"] += 3
            teams[ht]["intLoss"] += 1
        else:
            teams[ht]["intDraw"] += 1; teams[ht]["intPoints"] += 1
            teams[at]["intDraw"] += 1; teams[at]["intPoints"] += 1
    for t in teams.values():
        t["intGoalDifference"] = t["intGoalsFor"] - t["intGoalsAgainst"]
    table = sorted(teams.values(), key=lambda x: (-x["intPoints"], -x["intGoalDifference"], -x["intGoalsFor"]))
    for i, t in enumerate(table):
        t["intRank"] = i + 1
    return table

# For each league, try to build full table
for lid, (name, max_rounds, n_teams) in LEAGUES.items():
    print(f"\n=== {name} ({lid}) ===")
    
    # Load all available events for this league
    all_events = []
    for pattern in [f"all_events_2526_{lid}.json", f"events_2526_{lid}.json"]:
        fpath = os.path.join(DATA_DIR, pattern)
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                d = json.load(f)
            evts = d.get("events", [])
            all_events.extend(evts)
    
    # Dedupe
    seen = set()
    unique = []
    for e in all_events:
        eid = e.get("idEvent")
        if eid and eid not in seen:
            seen.add(eid)
            unique.append(e)
    
    played = [e for e in unique if e.get("intHomeScore") is not None]
    event_teams = set()
    for e in unique:
        event_teams.add(e.get("strHomeTeam",""))
        event_teams.add(e.get("strAwayTeam",""))
    event_teams.discard("")
    
    print(f"  Events: {len(unique)} total, {len(played)} played, {len(event_teams)} teams")
    
    # Build standings from events
    if len(played) >= n_teams:
        table = build_table_from_events(played)
        print(f"  Built table: {len(table)} teams")
        
        # Also load API standings to get strForm and other metadata
        api_path = os.path.join(DATA_DIR, f"standings_2526_{lid}.json")
        api_data = {}
        if os.path.exists(api_path):
            with open(api_path, encoding="utf-8") as f:
                api_raw = json.load(f)
            for row in api_raw.get("table", []):
                api_data[row.get("strTeam","")] = row
        
        # Merge: use computed stats but add form/badge from API
        for t in table:
            api_row = api_data.get(t["strTeam"], {})
            t["strForm"] = api_row.get("strForm", "")
            t["strTeamBadge"] = api_row.get("strTeamBadge", "")
            t["idTeam"] = api_row.get("idTeam", "")
            t["idLeague"] = str(lid)
            t["strLeague"] = name
        
        # Save as full standings
        out_path = os.path.join(DATA_DIR, f"full_standings_2526_{lid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"table": table, "league_id": lid, "league_name": name,
                        "source": "computed_from_events", "played_matches": len(played)}, 
                       f, ensure_ascii=False, indent=1)
        print(f"  SAVED full standings: {len(table)} teams -> {out_path}")
    else:
        # Fall back to API standings (only 5 teams)
        api_path = os.path.join(DATA_DIR, f"standings_2526_{lid}.json")
        if os.path.exists(api_path):
            with open(api_path, encoding="utf-8") as f:
                api_raw = json.load(f)
            table = api_raw.get("table", [])
            print(f"  Using API standings: {len(table)} teams (insufficient events)")
            
            # If we have event teams not in standings, add them with minimal data
            existing_teams = {r["strTeam"] for r in table}
            extra = event_teams - existing_teams
            if extra:
                # Build partial from events
                event_table = build_table_from_events(played)
                event_lookup = {t["strTeam"]: t for t in event_table}
                for team_name in extra:
                    if team_name in event_lookup:
                        row = event_lookup[team_name]
                        row["idLeague"] = str(lid)
                        row["strLeague"] = name
                        table.append(row)
                # Re-sort
                for i, row in enumerate(sorted(table, key=lambda x: (-int(x.get("intPoints",0)), -int(x.get("intGoalDifference",0))))):
                    row["intRank"] = i + 1
                print(f"  Augmented with event teams: {len(table)} teams total")
            
            out_path = os.path.join(DATA_DIR, f"full_standings_2526_{lid}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"table": table, "league_id": lid, "league_name": name,
                            "source": "api_plus_events"}, f, ensure_ascii=False, indent=1)
            print(f"  SAVED augmented standings -> {out_path}")

print("\n=== DONE ===")
for lid, (name, _, _) in LEAGUES.items():
    out_path = os.path.join(DATA_DIR, f"full_standings_2526_{lid}.json")
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            d = json.load(f)
        print(f"  {name}: {len(d.get('table',[]))} teams ({d.get('source','?')})")
