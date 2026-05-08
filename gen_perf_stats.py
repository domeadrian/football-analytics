"""Quick script to generate performance stats from current lineup data."""
import json, sys
sys.path.insert(0, '.')
from fetch_lineups import load_all_events, compute_player_stats

events = load_all_events()
lineups = json.load(open('data/all_lineups_2526.json', encoding='utf-8'))
has = {k: v for k, v in lineups.items() if v}
print(f'Computing stats from {len(has)} matches with lineups...')

stats = compute_player_stats(lineups, events)
print(f'Got stats for {len(stats)} player-team records')

# Save
export = {k: {kk: vv for kk, vv in v.items() if kk != 'matches_played'} for k, v in stats.items()}
with open('data/player_performance_2526.json', 'w', encoding='utf-8') as f:
    json.dump(export, f, ensure_ascii=False, indent=2)
print('Saved!')

# Top 10 by appearances
top = sorted(stats.values(), key=lambda x: x['appearances'], reverse=True)[:10]
for p in top:
    print(f"  {p['strPlayer']} ({p['strTeam']}) - Apps: {p['appearances']}, Starts: {p['starts']}, Win%: {p['win_rate']}, PPG: {p['ppg']}")
