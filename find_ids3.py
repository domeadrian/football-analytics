import requests, json, time
import urllib3
urllib3.disable_warnings()
s = requests.Session()
s.verify = False

# Check IDs systematically near known soccer leagues (4328-4400 range)
# Already know: 4328=EPL, 4330=Scottish, 4331=BuLi, 4332=SerieA, 4334=L1, 4335=LaLiga
# 4336=Greek, 4337=Eredivisie, 4338=Belgian, 4339=TurkishSuperLig, 4340=Danish
# Need to find: Austrian Bundesliga, Swiss Super League, Polish Ekstraklasa
# Try 4345, 4344=Portuguese
ids_to_check = [4329, 4333, 4341, 4342, 4343, 4344, 4345, 4348, 4349, 4352, 4353, 4354, 4357, 4358, 4359, 4360]
for lid in ids_to_check:
    url = f"https://www.thesportsdb.com/api/v1/json/3/lookupleague.php?id={lid}"
    try:
        r = s.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            leagues = data.get("leagues", [])
            if leagues:
                lg = leagues[0]
                sport = lg.get("strSport", "?")
                name = lg.get("strLeague", "?")
                country = lg.get("strCountry", "?")
                if sport == "Soccer":
                    print(f"  ID {lid}: {name} ({country}) [SOCCER]")
                else:
                    print(f"  ID {lid}: {name} ({country}) [{sport}]")
            else:
                print(f"  ID {lid}: no data")
        elif r.status_code == 429:
            print(f"  ID {lid}: RATE LIMITED")
            time.sleep(5)
        else:
            print(f"  ID {lid}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ID {lid}: {e}")
    time.sleep(3)
