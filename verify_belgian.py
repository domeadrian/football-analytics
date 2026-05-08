import json

with open("data/full_standings_2526_4338.json", encoding="utf-8") as f:
    data = json.load(f)
table = data["table"]
for t in table:
    for k in ["intPoints", "intGoalDifference", "intGoalsFor", "intPlayed", "intRank"]:
        t[k] = int(t.get(k, 0))
table.sort(key=lambda x: (-x["intPoints"], -x["intGoalDifference"], -x["intGoalsFor"]))
print(f"=== Belgian Pro League ({len(table)} teams) ===")
for i, t in enumerate(table, 1):
    team = t["strTeam"]
    print(f"  {i:2d}. {team:20s}  P={t['intPlayed']:2d}  Pts={t['intPoints']:2d}  GD={t['intGoalDifference']:+3d}")
