import requests, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

s = requests.Session()
s.verify = False
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
r = s.get('https://www.transfermarkt.com/fcsb/kader/verein/301/saison_id/2025/plus/1', timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')

# Check both selectors
sp = soup.select('a[href*="spielprofil/spieler"]')
pr = soup.select('a[href*="profil/spieler"]')
print(f"spielprofil/spieler links: {len(sp)}")
print(f"profil/spieler links: {len(pr)}")

if pr:
    print(f"Sample href: {pr[0]['href']}")
if sp:
    print(f"Sample spielprofil href: {sp[0]['href']}")
