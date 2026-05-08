import json
d = json.load(open('C:/Users/adomente/football_analytics/data/full_standings_2526_4691.json', encoding='utf-8'))
table = d['table']
print(f"Romanian Liga I: {len(table)} teams")
for r in table:
    name = r["strTeam"].ljust(30)
    print(f"  #{r['intRank']:2d} {name} P:{r['intPlayed']:2d} W:{r['intWin']:2d} D:{r['intDraw']:2d} L:{r['intLoss']:2d} GD:{r['intGoalDifference']:+3d} Pts:{r['intPoints']:2d}")
