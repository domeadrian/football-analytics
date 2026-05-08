import requests, json, time
import urllib3
urllib3.disable_warnings()
s = requests.Session()
s.verify = False

test_ids = [4351, 4355, 4340, 4401, 4347, 4346, 4532, 4350, 4356, 4338, 4336, 4341, 4342, 4343, 4348, 4349, 4352, 4353, 4354]
for lid in test_ids:
    url = f"https://www.thesportsdb.com/api/v1/json/3/lookupleague.php?id={lid}"
    try:
        r = s.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            leagues = data.get("leagues", [])
            if leagues:
                lg = leagues[0]
                name = lg.get("strLeague", "?")
                country = lg.get("strCountry", "?")
                alt = lg.get("strLeagueAlternate", "")
                print(f"  ID {lid}: {name} ({country}) alt={alt}")
            else:
                print(f"  ID {lid}: no data")
        else:
            print(f"  ID {lid}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ID {lid}: {e}")
    time.sleep(2)
