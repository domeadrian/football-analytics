import json

def show_league(filepath, name):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    table = data["table"]
    for t in table:
        for k in ["intPoints", "intGoalDifference", "intGoalsFor", "intPlayed", "intRank"]:
            t[k] = int(t.get(k, 0))
    table.sort(key=lambda x: (-x["intPoints"], -x["intGoalDifference"], -x["intGoalsFor"]))
    print(f"=== {name} ({len(table)} teams) ===")
    for i, t in enumerate(table, 1):
        team = t["strTeam"]
        print(f"  {i:2d}. {team:25s}  P={t['intPlayed']:2d}  Pts={t['intPoints']:2d}  GD={t['intGoalDifference']:+3d}")
    print()

show_league("data/full_standings_2526_4691.json", "Romanian Liga I")
show_league("data/full_standings_2526_4665.json", "Romanian Liga II")
show_league("data/full_standings_2526_4340.json", "Danish Superliga")
