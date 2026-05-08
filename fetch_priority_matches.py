"""Quick fetch for priority leagues that need more match data."""
import requests, json, os, time, urllib3
urllib3.disable_warnings()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"
SEASON = "2025-2026"
session = requests.Session()
session.verify = False

PRIORITY = {
    4691: ("Romanian Liga I", 30),
    4665: ("Romanian Liga II", 38),
    4338: ("Belgian Pro League", 30),
    4340: ("Danish Superliga", 32),
    4331: ("Bundesliga", 34),
    4334: ("Ligue 1", 34),
    4337: ("Eredivisie", 34),
    4339: ("Turkish Super Lig", 38),
    4344: ("Primeira Liga", 34),
    4336: ("Greek Super League", 30),
}

for lid, (name, max_rounds) in PRIORITY.items():
    print(f"\n=== {name} (ID {lid}) ===")
    out_path = os.path.join(DATA_DIR, f"all_events_2526_{lid}.json")
    
    league_events = []
    existing_rounds = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
        league_events = existing.get("events", [])
        for e in league_events:
            r = e.get("intRound")
            if r: existing_rounds.add(str(r))
        print(f"  Loaded {len(league_events)} events, {len(existing_rounds)} rounds done")
    
    new_count = 0
    consecutive_fail = 0
    for rnd in range(1, max_rounds + 1):
        if str(rnd) in existing_rounds:
            continue
        
        if consecutive_fail >= 5:
            print(f"  Too many failures, stopping this league. Saving checkpoint.")
            break
        
        url = f"{BASE}/eventsround.php?id={lid}&r={rnd}&s={SEASON}"
        ok = False
        for attempt in range(4):
            try:
                resp = session.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    events = data.get("events") or []
                    if events:
                        league_events.extend(events)
                        new_count += len(events)
                        print(f"  Round {rnd}: {len(events)} matches")
                    else:
                        print(f"  Round {rnd}: no data")
                    consecutive_fail = 0
                    ok = True
                    break
                elif resp.status_code == 429:
                    consecutive_fail += 1
                    wait = 15 * (attempt + 1)
                    print(f"  Round {rnd}: 429 (attempt {attempt+1}), wait {wait}s")
                    time.sleep(wait)
            except Exception as e:
                print(f"  Round {rnd}: Error {e}")
                time.sleep(5)
        
        if not ok:
            consecutive_fail += 1
        
        time.sleep(2.0)
    
    # Dedupe and save
    seen = set()
    unique = []
    for e in league_events:
        eid = e.get("idEvent")
        if eid and eid not in seen:
            seen.add(eid)
            unique.append(e)
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"league_id": lid, "league_name": name, "season": SEASON,
                    "events": unique}, f, ensure_ascii=False, indent=1)
    print(f"  SAVED: {len(unique)} total events ({new_count} new)")
    time.sleep(5)  # cooldown between leagues

print("\nDONE")
