import requests, urllib3, json, time
urllib3.disable_warnings()
s = requests.Session()
s.verify = False

for country in ['Austria', 'Switzerland']:
    print(f"\n=== {country} ===")
    time.sleep(2)
    r = s.get(f'https://www.thesportsdb.com/api/v1/json/3/search_all_leagues.php?c={country}&s=Soccer', timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        leagues = d.get('countries') or d.get('leagues') or []
        for l in leagues:
            print(f"  {l.get('idLeague','?')}: {l.get('strLeague','?')}")
    time.sleep(3)
