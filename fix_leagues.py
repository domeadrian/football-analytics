"""Fix wrong league data: fetch Belgian Pro League (4338) standings + events."""
import requests, json, os, time
import urllib3
urllib3.disable_warnings()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"

s = requests.Session()
s.verify = False
s.headers["User-Agent"] = "FootballAnalytics/1.0"

def fetch_and_save(url, filename, delay=3):
    for attempt in range(5):
        try:
            r = s.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                path = os.path.join(DATA_DIR, filename)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return data
            elif r.status_code == 429:
                print(f"  Rate limited, waiting {delay * (attempt + 1)}s...")
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  HTTP {r.status_code}")
                return None
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(delay)
    return None

# Fix 1: Belgian Pro League (correct ID = 4338)
print("=== Belgian Pro League (4338) ===")
data = fetch_and_save(
    f"{BASE}/lookuptable.php?l=4338&s=2025-2026",
    "standings_2526_4338.json"
)
if data and data.get("table"):
    teams = [t["strTeam"] for t in data["table"]]
    print(f"  Standings: {teams}")
else:
    print("  No data, trying season=2025")
    data = fetch_and_save(
        f"{BASE}/lookuptable.php?l=4338&s=2025",
        "standings_2526_4338.json"
    )
    if data and data.get("table"):
        teams = [t["strTeam"] for t in data["table"]]
        print(f"  Standings: {teams}")

time.sleep(3)

# Events for Belgian Pro League
print("\n=== Belgian Pro League Events ===")
data = fetch_and_save(
    f"{BASE}/eventsseason.php?id=4338&s=2025-2026",
    "events_2526_4338.json"
)
if data and data.get("events"):
    print(f"  Events: {len(data['events'])}")

time.sleep(3)

# Fix 2: Greek Super League (4336) — already have the ID
print("\n=== Greek Super League (4336) ===")
data = fetch_and_save(
    f"{BASE}/lookuptable.php?l=4336&s=2025-2026",
    "standings_2526_4336.json"
)
if data and data.get("table"):
    teams = [t["strTeam"] for t in data["table"]]
    print(f"  Standings: {teams}")

time.sleep(3)

# Fix 3: Remove the wrong files (4355=Russian, 4340=Danish — label them correctly)
# We don't delete them, just make the dashboard map them correctly

# Fix 4: Try to get remaining events for leagues that 429'd
for lid, name in [(4344, "Primeira Liga"), (4339, "Turkish Super Lig"),
                  (4330, "Scottish Premiership"), (4691, "Romanian Liga I")]:
    evf = f"events_2526_{lid}.json"
    if os.path.exists(os.path.join(DATA_DIR, evf)):
        continue
    print(f"\n=== {name} Events ({lid}) ===")
    data = fetch_and_save(
        f"{BASE}/eventsseason.php?id={lid}&s=2025-2026",
        evf
    )
    if data and data.get("events"):
        print(f"  Events: {len(data['events'])}")
    time.sleep(3)

print("\n=== DONE ===")
