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
            team = str(r['strTeam']).ljust(30)
            rank = int(r.get('intRank', 0))
            played = int(r.get('intPlayed', 0))
            pts = int(r.get('intPoints', 0))
            w = int(r.get('intWin', 0))
            d2 = int(r.get('intDraw', 0))
            lo = int(r.get('intLoss', 0))
            gd = int(r.get('intGoalDifference', 0))
            print(f"  #{rank:2d} {team} P:{played:2d} W:{w:2d} D:{d2:2d} L:{lo:2d} GD:{gd:+3d} Pts:{pts:2d}")
