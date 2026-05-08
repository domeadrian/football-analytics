import requests, urllib3, json, time
urllib3.disable_warnings()
s = requests.Session()
s.verify = False

# Wait a bit for rate limit to cool
time.sleep(5)

# Try known IDs for Austrian Bundesliga and Swiss Super League
targets = [
    (4422, "maybe Austrian?"),
    (4423, "maybe Austrian?"),
    (4424, "maybe Swiss?"),
    (4425, "maybe Swiss?"),
    (4395, "maybe?"),
    (4396, "maybe?"),
    (4397, "maybe?"),
    (4398, "maybe?"),
    (4399, "maybe?"),
    (4400, "maybe?"),
]

for lid, label in targets:
    try:
        r = s.get(f'https://www.thesportsdb.com/api/v1/json/3/lookupleague.php?id={lid}', timeout=10)
        if r.status_code == 200:
            d = r.json()
            leagues = d.get('leagues') or []
            if leagues:
                l = leagues[0]
                name = l.get('strLeague', '?')
                country = l.get('strCountry', '?')
                sport = l.get('strSport', '?')
                print(f"{lid}: {name} ({country}) [{sport}]")
        elif r.status_code == 429:
            print(f"{lid}: Rate limited")
            time.sleep(10)
        time.sleep(1.5)
    except Exception as e:
        print(f"{lid}: Error: {e}")
