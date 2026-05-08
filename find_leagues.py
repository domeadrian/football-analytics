import requests, json, time
import urllib3
urllib3.disable_warnings()

s = requests.Session()
s.verify = False

countries = ['Austria', 'Belgium', 'Switzerland', 'Greece', 'Croatia',
             'Czech Republic', 'Poland', 'Ukraine', 'Serbia', 'Denmark',
             'Norway', 'Sweden', 'Hungary', 'Bulgaria', 'Cyprus']

for country in countries:
    url = f'https://www.thesportsdb.com/api/v1/json/3/search_all_leagues.php?c={country}&s=Soccer'
    try:
        r = s.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            leagues = data.get('countries') or data.get('leagues') or []
            if leagues:
                for lg in leagues[:3]:
                    lid = lg.get('idLeague', '?')
                    lname = lg.get('strLeague', '?')
                    print(f"  {country}: {lname} (ID={lid})")
            else:
                print(f"  {country}: no leagues")
        else:
            print(f"  {country}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  {country}: error {e}")
    time.sleep(1.2)
