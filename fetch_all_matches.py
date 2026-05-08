"""
Fetch ALL 2025-2026 matches by iterating over rounds.
TheSportsDB free API: eventsround.php?id={league}&r={round}&s=2025-2026
"""
import requests, json, os, time, urllib3
urllib3.disable_warnings()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"

LEAGUES = {
    4328: ("English Premier League", 38),
    4335: ("La Liga", 38),
    4332: ("Serie A", 38),
    4331: ("Bundesliga", 34),
    4334: ("Ligue 1", 34),
    4337: ("Eredivisie", 34),
    4344: ("Primeira Liga", 34),
    4339: ("Turkish Super Lig", 38),
    4338: ("Belgian Pro League", 30),
    4355: ("Russian Premier League", 30),
    4330: ("Scottish Premiership", 38),
    4340: ("Danish Superliga", 32),
    4336: ("Greek Super League", 30),
    4691: ("Romanian Liga I", 30),
    4665: ("Romanian Liga II", 38),
}

SEASON = "2025-2026"

session = requests.Session()
session.verify = False

all_events = {}  # league_id -> list of events

for lid, (name, max_rounds) in LEAGUES.items():
    print(f"\n=== {name} (ID {lid}) ===")
    league_events = []
    out_path = os.path.join(DATA_DIR, f"all_events_2526_{lid}.json")
    
    # Load existing if any (for resume)
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
        existing_events = existing.get("events", [])
        existing_rounds = set()
        for e in existing_events:
            r = e.get("intRound")
            if r:
                existing_rounds.add(str(r))
        league_events = existing_events
        print(f"  Loaded {len(existing_events)} existing events, rounds: {sorted(existing_rounds)}")
    else:
        existing_rounds = set()
    
    for rnd in range(1, max_rounds + 1):
        if str(rnd) in existing_rounds:
            continue
        
        url = f"{BASE}/eventsround.php?id={lid}&r={rnd}&s={SEASON}"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 429:
                print(f"  Round {rnd}: Rate limited, waiting 5s...")
                time.sleep(5)
                resp = session.get(url, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                events = data.get("events") or []
                if events:
                    league_events.extend(events)
                    print(f"  Round {rnd}: {len(events)} matches")
                else:
                    print(f"  Round {rnd}: no data (future round?)")
            else:
                print(f"  Round {rnd}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  Round {rnd}: ERROR {e}")
        
        time.sleep(1.0)  # Rate limit
    
    # Deduplicate by idEvent
    seen = set()
    unique_events = []
    for e in league_events:
        eid = e.get("idEvent")
        if eid and eid not in seen:
            seen.add(eid)
            unique_events.append(e)
    
    # Save
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"league_id": lid, "league_name": name, "season": SEASON,
                    "events": unique_events}, f, ensure_ascii=False, indent=1)
    print(f"  SAVED: {len(unique_events)} unique events -> {out_path}")
    
    # Checkpoint delay between leagues
    time.sleep(2)

print("\n=== DONE ===")
for lid, (name, _) in LEAGUES.items():
    out_path = os.path.join(DATA_DIR, f"all_events_2526_{lid}.json")
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            d = json.load(f)
        print(f"  {name}: {len(d.get('events', []))} events")
