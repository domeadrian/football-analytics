import json
with open('data/all_players_2526.json', encoding='utf-8') as f:
    players = json.load(f)
print(f"Total players: {len(players)}")

has_age = sum(1 for p in players if p.get('age') is not None)
no_age = sum(1 for p in players if p.get('age') is None)
print(f"Has age: {has_age}, Missing age: {no_age}")

has_dob = sum(1 for p in players if p.get('dateBorn') and p['dateBorn'].strip())
print(f"Has dateBorn: {has_dob}")

# Sample with ages
print("\nSample players with age:")
for p in players[:5]:
    print(f"  {p['strPlayer']:30s} age={p.get('age'):>4}  dob={p.get('dateBorn'):>12}  team={p.get('strTeam')}")

# Sample missing age
nones = [p for p in players if p.get('age') is None]
if nones:
    print(f"\nMissing age ({len(nones)} players):")
    for p in nones[:10]:
        print(f"  {p['strPlayer']:30s} dob='{p.get('dateBorn')}'  team={p.get('strTeam')}")

# Age distribution
from collections import Counter
ages = [p['age'] for p in players if p.get('age') is not None]
bins = Counter()
for a in ages:
    if a < 18: bins['<18'] += 1
    elif a <= 21: bins['18-21'] += 1
    elif a <= 25: bins['22-25'] += 1
    elif a <= 29: bins['26-29'] += 1
    elif a <= 33: bins['30-33'] += 1
    else: bins['34+'] += 1
print("\nAge distribution:")
for k in ['<18', '18-21', '22-25', '26-29', '30-33', '34+']:
    print(f"  {k:>6}: {bins.get(k, 0):>5}")
print(f"  Total: {len(ages)}")

# Check DOB format
dobs = [p['dateBorn'] for p in players if p.get('dateBorn') and p['dateBorn'].strip()]
if dobs:
    print(f"\nDOB format samples: {dobs[:5]}")
