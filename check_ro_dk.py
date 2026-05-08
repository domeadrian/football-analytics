import json, os

DATA = 'C:/Users/adomente/football_analytics/data'
for lid in [4691, 4665, 4340]:
    f = os.path.join(DATA, f'full_standings_2526_{lid}.json')
    if os.path.exists(f):
        d = json.load(open(f, encoding='utf-8'))
        name = d.get('league_name', '?')
        src = d.get('source', '?')
        table = d['table']
        print(f"\n=== {name} ({lid}) === source: {src}, {len(table)} teams")
        for r in table:
            team = r['strTeam'].ljust(30)
            print(f"  #{r['intRank']:2d} {team} P:{r['intPlayed']:2d} W:{r['intWin']:2d} D:{r['intDraw']:2d} L:{r['intLoss']:2d} GD:{r['intGoalDifference']:+3d} Pts:{r['intPoints']:2d}")
