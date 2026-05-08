"""
Fetch ALL 2025-2026 matches — with aggressive retry and long cooldowns.
Resumes from previously saved files.
"""
import requests, json, os, time, urllib3
urllib3.disable_warnings()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"

LEAGUES = {
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

consecutive_429 = 0

for lid, (name, max_rounds) in LEAGUES.items():
    print(f"\n=== {name} (ID {lid}) ===")
    out_path = os.path.join(DATA_DIR, f"all_events_2526_{lid}.json")
    
    # Load existing
    league_events = []
    existing_rounds = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
        league_events = existing.get("events", [])
        for e in league_events:
            r = e.get("intRound")
            if r:
                existing_rounds.add(str(r))
        print(f"  Loaded {len(league_events)} existing events, {len(existing_rounds)} rounds done")
    
    new_this_league = 0
    for rnd in range(1, max_rounds + 1):
        if str(rnd) in existing_rounds:
            continue
        
        # If we hit too many 429s, do a long cooldown
        if consecutive_429 >= 3:
            print(f"  === Long cooldown (30s) after {consecutive_429} consecutive 429s ===")
            time.sleep(30)
            consecutive_429 = 0
        
        url = f"{BASE}/eventsround.php?id={lid}&r={rnd}&s={SEASON}"
        success = False
        for attempt in range(3):
            try:
                resp = session.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    events = data.get("events") or []
                    if events:
                        league_events.extend(events)
                        new_this_league += len(events)
                        print(f"  Round {rnd}: {len(events)} matches")
                    else:
                        print(f"  Round {rnd}: no data")
                    consecutive_429 = 0
                    success = True
                    break
                elif resp.status_code == 429:
                    consecutive_429 += 1
                    wait = 10 * (attempt + 1)
                    print(f"  Round {rnd}: 429, waiting {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                else:
                    print(f"  Round {rnd}: HTTP {resp.status_code}")
                    break
            except Exception as e:
                print(f"  Round {rnd}: ERROR {e}")
                time.sleep(5)
        
        if not success:
            print(f"  Round {rnd}: SKIPPED after retries")
        
        time.sleep(1.5)
    
    # Deduplicate
    seen = set()
    unique_events = []
    for e in league_events:
        eid = e.get("idEvent")
        if eid and eid not in seen:
            seen.add(eid)
            unique_events.append(e)
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"league_id": lid, "league_name": name, "season": SEASON,
                    "events": unique_events}, f, ensure_ascii=False, indent=1)
    print(f"  SAVED: {len(unique_events)} total events ({new_this_league} new)")
    time.sleep(3)

print("\n=== SUMMARY ===")
for lid, (name, _) in list({4328: ("English Premier League", 38), **LEAGUES}.items()):
    out_path = os.path.join(DATA_DIR, f"all_events_2526_{lid}.json")
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            d = json.load(f)
        evts = d.get("events", [])
        dates = [e.get("dateEvent","") for e in evts]
        played = sum(1 for e in evts if e.get("intHomeScore") is not None)
        print(f"  {name}: {len(evts)} events ({played} with scores), {min(dates) if dates else '?'} to {max(dates) if dates else '?'}")
