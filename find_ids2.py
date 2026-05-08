import requests, json, time
import urllib3
urllib3.disable_warnings()
s = requests.Session()
s.verify = False

# Search by country for Austria
url = "https://www.thesportsdb.com/api/v1/json/3/search_all_leagues.php?c=Austria&s=Soccer"
try:
    r = s.get(url, timeout=10)
    if r.status_code == 200:
        data = r.json()
        leagues = data.get("countries") or data.get("leagues") or []
        for lg in leagues:
            print(f"  Austria: {lg.get('strLeague')} (ID={lg.get('idLeague')})")
    else:
        print(f"HTTP {r.status_code}")
except Exception as e:
    print(e)

time.sleep(3)

# Also check Belgium
url2 = "https://www.thesportsdb.com/api/v1/json/3/search_all_leagues.php?c=Belgium&s=Soccer"
try:
    r = s.get(url2, timeout=10)
    if r.status_code == 200:
        data = r.json()
        leagues = data.get("countries") or data.get("leagues") or []
        for lg in leagues:
            print(f"  Belgium: {lg.get('strLeague')} (ID={lg.get('idLeague')})")
    else:
        print(f"HTTP {r.status_code}")
except Exception as e:
    print(e)

time.sleep(3)

# Also Switzerland
url3 = "https://www.thesportsdb.com/api/v1/json/3/search_all_leagues.php?c=Switzerland&s=Soccer"
try:
    r = s.get(url3, timeout=10)
    if r.status_code == 200:
        data = r.json()
        leagues = data.get("countries") or data.get("leagues") or []
        for lg in leagues:
            print(f"  Switzerland: {lg.get('strLeague')} (ID={lg.get('idLeague')})")
    else:
        print(f"HTTP {r.status_code}")
except Exception as e:
    print(e)
