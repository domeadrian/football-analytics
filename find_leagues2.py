import requests, urllib3, json
urllib3.disable_warnings()
s = requests.Session()
s.verify = False

# Search for Austrian and Swiss leagues
for lid in range(4340, 4360):
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
                if sport == 'Soccer':
                    print(f"{lid}: {name} ({country})")
    except:
        pass

# Also check known Austrian league IDs
for lid in [4532, 4533, 4534, 4535]:
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
                if sport == 'Soccer':
                    print(f"{lid}: {name} ({country})")
    except:
        pass
