"""
Fetch match lineups from TheSportsDB for all played matches.
Derives player appearance stats: starts, subs, positions played, win/draw/loss when playing.
Saves incrementally so it can be resumed if interrupted.
"""

import json, os, time, requests, glob
from datetime import datetime

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "all_lineups_2526.json")
STATS_FILE = os.path.join(DATA_DIR, "player_performance_2526.json")
BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"
DELAY = 0.35  # seconds between requests

# Disable SSL warnings for environments with cert issues
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_all_events():
    """Load all played match events across all leagues."""
    all_events = []
    for f in sorted(glob.glob(os.path.join(DATA_DIR, "all_events_2526_*.json"))):
        data = json.load(open(f, encoding="utf-8"))
        league_name = data.get("league_name", "Unknown")
        league_id = data.get("league_id", "")
        events = data.get("events", [])
        for e in events:
            if e.get("intHomeScore") is not None and str(e.get("intHomeScore", "")) != "":
                e["_league_name"] = league_name
                e["_league_id"] = league_id
                all_events.append(e)
    return all_events


def load_existing_lineups():
    """Load already-fetched lineups to allow resuming."""
    if os.path.exists(OUTPUT_FILE):
        return json.load(open(OUTPUT_FILE, encoding="utf-8"))
    return {}


def fetch_lineup(event_id):
    """Fetch lineup for a single event."""
    url = f"{BASE_URL}/lookuplineup.php?id={event_id}"
    try:
        r = requests.get(url, timeout=15, verify=False)
        if r.status_code == 200:
            data = r.json()
            return data.get("lineup", [])
    except Exception as e:
        print(f"  Error fetching {event_id}: {e}")
    return None


def compute_player_stats(lineups, all_events):
    """Compute per-player performance stats from lineup data."""
    # Build event lookup for results
    event_lookup = {}
    for e in all_events:
        eid = str(e.get("idEvent", ""))
        try:
            home_score = int(e.get("intHomeScore", 0))
            away_score = int(e.get("intAwayScore", 0))
        except (ValueError, TypeError):
            continue
        event_lookup[eid] = {
            "home_team": e.get("strHomeTeam", ""),
            "away_team": e.get("strAwayTeam", ""),
            "home_score": home_score,
            "away_score": away_score,
            "date": e.get("dateEvent", ""),
            "round": e.get("intRound", ""),
            "league": e.get("_league_name", ""),
        }

    # Aggregate per player
    players = {}
    for eid, lineup_list in lineups.items():
        if not lineup_list:
            continue
        match = event_lookup.get(eid, {})
        if not match:
            continue

        for p in lineup_list:
            pid = p.get("idPlayer", "")
            name = p.get("strPlayer", "Unknown")
            team = p.get("strTeam", "")
            tid = p.get("idTeam", "")
            pos = p.get("strPosition", "")
            is_sub = p.get("strSubstitute", "No") == "Yes"
            is_home = p.get("strHome", "No") == "Yes"

            key = f"{pid}_{tid}"  # player + team combo
            if key not in players:
                players[key] = {
                    "idPlayer": pid,
                    "strPlayer": name,
                    "strTeam": team,
                    "idTeam": tid,
                    "league": match.get("league", ""),
                    "appearances": 0,
                    "starts": 0,
                    "sub_appearances": 0,
                    "home_apps": 0,
                    "away_apps": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_when_playing": 0,  # team's goals
                    "conceded_when_playing": 0,  # team's conceded
                    "clean_sheets": 0,
                    "positions_played": [],
                    "matches_played": [],
                }

            rec = players[key]
            rec["appearances"] += 1
            if is_sub:
                rec["sub_appearances"] += 1
            else:
                rec["starts"] += 1
            if is_home:
                rec["home_apps"] += 1
            else:
                rec["away_apps"] += 1

            if pos and pos not in rec["positions_played"]:
                rec["positions_played"].append(pos)

            # Determine result from player's team perspective
            if is_home:
                team_gf = match["home_score"]
                team_ga = match["away_score"]
            else:
                team_gf = match["away_score"]
                team_ga = match["home_score"]

            rec["goals_when_playing"] += team_gf
            rec["conceded_when_playing"] += team_ga
            if team_ga == 0:
                rec["clean_sheets"] += 1
            if team_gf > team_ga:
                rec["wins"] += 1
            elif team_gf == team_ga:
                rec["draws"] += 1
            else:
                rec["losses"] += 1

            rec["matches_played"].append({
                "event_id": eid,
                "date": match.get("date", ""),
                "round": match.get("round", ""),
                "started": not is_sub,
                "position": pos,
                "result": "W" if team_gf > team_ga else ("D" if team_gf == team_ga else "L"),
                "team_gf": team_gf,
                "team_ga": team_ga,
            })

    # Compute derived metrics
    for key, rec in players.items():
        apps = max(rec["appearances"], 1)
        rec["win_rate"] = round(rec["wins"] / apps * 100, 1)
        rec["ppg"] = round((rec["wins"] * 3 + rec["draws"]) / apps, 2)
        rec["goals_per_match"] = round(rec["goals_when_playing"] / apps, 2)
        rec["conceded_per_match"] = round(rec["conceded_when_playing"] / apps, 2)
        rec["clean_sheet_pct"] = round(rec["clean_sheets"] / apps * 100, 1)
        rec["start_pct"] = round(rec["starts"] / apps * 100, 1)
        # Remove detailed match log from summary (keep for deep analysis)
        rec["_match_count"] = len(rec["matches_played"])

    return players


def main():
    print(f"[{datetime.now():%H:%M:%S}] Loading events...")
    all_events = load_all_events()
    print(f"  Found {len(all_events)} played matches")

    existing = load_existing_lineups()
    print(f"  Already fetched: {len(existing)} lineups")

    # Events still to fetch
    to_fetch = [e for e in all_events if str(e.get("idEvent", "")) not in existing]
    print(f"  Remaining: {len(to_fetch)} to fetch")

    if not to_fetch:
        print("All lineups already fetched!")
    else:
        fetched = 0
        errors = 0
        empty = 0
        save_every = 50  # save progress every N fetches

        for i, event in enumerate(to_fetch):
            eid = str(event.get("idEvent", ""))
            league = event.get("_league_name", "")

            lineup = fetch_lineup(eid)
            if lineup is None:
                errors += 1
                existing[eid] = []
            elif len(lineup) == 0:
                empty += 1
                existing[eid] = []
            else:
                fetched += 1
                existing[eid] = lineup

            if (i + 1) % 25 == 0:
                pct = (i + 1) / len(to_fetch) * 100
                print(f"  [{datetime.now():%H:%M:%S}] {i+1}/{len(to_fetch)} ({pct:.0f}%) — "
                      f"fetched: {fetched}, empty: {empty}, errors: {errors} | "
                      f"Last: {event.get('strEvent', '')} ({league})")

            if (i + 1) % save_every == 0:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False)

            time.sleep(DELAY)

        # Final save
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False)
        print(f"\n[{datetime.now():%H:%M:%S}] Lineup fetch complete!")
        print(f"  Total fetched: {fetched}, Empty: {empty}, Errors: {errors}")

    # Compute player stats
    print(f"\n[{datetime.now():%H:%M:%S}] Computing player performance stats...")
    player_stats = compute_player_stats(existing, all_events)
    print(f"  Computed stats for {len(player_stats)} player-team records")

    # Save stats (without match log for smaller file)
    stats_export = {}
    for key, rec in player_stats.items():
        export_rec = {k: v for k, v in rec.items() if k != "matches_played"}
        stats_export[key] = export_rec

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats_export, f, ensure_ascii=False, indent=2)
    print(f"  Saved to {STATS_FILE}")

    # Summary by league
    from collections import Counter
    league_counts = Counter(r["league"] for r in player_stats.values())
    print("\n  Players per league:")
    for lg, cnt in league_counts.most_common():
        print(f"    {lg}: {cnt}")

    # Top performers
    sorted_ppg = sorted(player_stats.values(), key=lambda x: (x["ppg"], x["appearances"]), reverse=True)
    top = [p for p in sorted_ppg if p["appearances"] >= 10][:20]
    print("\n  Top 20 by PPG (min 10 apps):")
    for p in top:
        print(f"    {p['strPlayer']} ({p['strTeam']}) — PPG: {p['ppg']}, "
              f"Apps: {p['appearances']}, Win%: {p['win_rate']}")


if __name__ == "__main__":
    main()
