"""Deep audit of age data in all_players_2526.json"""
import json
from collections import Counter

with open('data/all_players_2526.json', encoding='utf-8') as f:
    players = json.load(f)

print(f"Total players: {len(players)}")
print()

# Check all age-related fields
age_none = [p for p in players if p.get('age') is None]
age_zero = [p for p in players if p.get('age') == 0]
age_nan = [p for p in players if str(p.get('age', '')).lower() == 'nan']
dob_empty = [p for p in players if not p.get('dateBorn') or not str(p.get('dateBorn', '')).strip()]
dob_dash = [p for p in players if str(p.get('dateBorn', '')).strip() in ('-', 'N/A', '')]

print(f"age is None:     {len(age_none)}")
print(f"age is 0:        {len(age_zero)}")
print(f"age is 'nan':    {len(age_nan)}")
print(f"dateBorn empty:  {len(dob_empty)}")
print(f"dateBorn is dash: {len(dob_dash)}")

# Check what age values look like
age_types = Counter(type(p.get('age')).__name__ for p in players)
print(f"\nage field types: {dict(age_types)}")

# Sample problematic
problems = [p for p in players if p.get('age') is None or p.get('age') == 0 
            or not p.get('dateBorn') or str(p.get('dateBorn', '')).strip() in ('-', 'N/A', '')]
print(f"\nTotal problematic (age=None/0 OR dob empty): {len(problems)}")
if problems:
    # Show by league
    league_counts = Counter(p.get('_leagueName', '?') for p in problems)
    print("By league:")
    for lg, cnt in league_counts.most_common():
        print(f"  {lg:35s} {cnt}")
    print("\nSample problematic players:")
    for p in problems[:20]:
        print(f"  {p['strPlayer']:30s} age={p.get('age')!r:>6}  dob={p.get('dateBorn')!r:>15}  team={p.get('strTeam')}")

# Now check what the dashboard does - it recalculates age from dateBorn
import pandas as pd
df = pd.DataFrame(players)
if 'dateBorn' in df.columns:
    df['birth_date'] = pd.to_datetime(df['dateBorn'], errors='coerce')
    df['calc_age'] = ((pd.Timestamp.now() - df['birth_date']).dt.days / 365.25).round(1)
    bad_calc = df[df['calc_age'].isna()]
    print(f"\nDashboard recalculated age NaN: {len(bad_calc)}")
    if not bad_calc.empty:
        print("Sample where dashboard would show NaN age:")
        for _, r in bad_calc.head(20).iterrows():
            print(f"  {r['strPlayer']:30s} raw_age={r.get('age')!r:>6}  dob={r['dateBorn']!r:>15}  birth_date={r['birth_date']}")
