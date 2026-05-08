import json, glob, os

# Check ALL event fields including potential goal/card details across multiple leagues
for fpath in glob.glob("data/all_events_2526_*.json")[:3]:
    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)
    events = data.get("events", [])
    print(f"\n=== {fpath} ({len(events)} events) ===")
    
    # Check which fields have non-null data
    found = {}
    for ev in events:
        for k, v in ev.items():
            if v and str(v).strip() and str(v) not in ("None", "null", ""):
                if k not in found:
                    found[k] = str(v)[:200]
    
    # Print goal/lineup/stats fields
    interesting = [k for k in found if any(x in k.lower() for x in ["goal", "card", "lineup", "shot", "stat", "substitut", "possession", "foul", "corner", "assist"])]
    print("Interesting fields with data:", interesting)
    for k in interesting:
        print(f"  {k}: {found[k]}")
    
    # Also check all non-null fields
    print(f"All non-null fields ({len(found)}):", sorted(found.keys()))

# Also check if there"s team-level stats in standings
standings_path = "data/full_standings_2526_4328.json"
if os.path.exists(standings_path):
    with open(standings_path, encoding="utf-8") as f:
        st = json.load(f)
    if "table" in st and st["table"]:
        row = st["table"][0]
        print("\n\nSTANDINGS all fields:")
        for k in sorted(row.keys()):
            v = row[k]
            if v and str(v).strip() and str(v) != "None":
                print(f"  {k}: {v}")

# Check if there"s a team stats/players file with performance data
for f in os.listdir("data"):
    if "stat" in f.lower() or "perf" in f.lower() or "goal" in f.lower():
        print(f"\nFound stats file: {f}")
