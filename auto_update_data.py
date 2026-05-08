"""
Auto-Update Script — Fetch latest matches & rebuild standings.
==============================================================
Fetches new match results from TheSportsDB API and rebuilds
full standings tables for all 15 leagues.

Can be run:
  - Manually:  python auto_update_data.py
  - Scheduled: via Windows Task Scheduler or cron
  - From the dashboard: triggered by a button in the sidebar

Usage:
    python auto_update_data.py          # update all leagues
    python auto_update_data.py 4328     # update only EPL
"""

import math
import requests
import json
import os
import sys
import time
import urllib3
from collections import defaultdict
from datetime import datetime

urllib3.disable_warnings()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.thesportsdb.com/api/v1/json/3"
SEASON = "2025-2026"

LEAGUES = {
    4328: ("English Premier League", 38),
    4335: ("La Liga", 38),
    4332: ("Serie A", 38),
    4331: ("Bundesliga", 34),
    4334: ("Ligue 1", 34),
    4337: ("Eredivisie", 34),
    4344: ("Primeira Liga", 34),
    4339: ("Turkish Super Lig", 38),
    4338: ("Belgian Pro League", 40),
    4355: ("Russian Premier League", 30),
    4330: ("Scottish Premiership", 38),
    4340: ("Danish Superliga", 32),
    4336: ("Greek Super League", 36),
    4691: ("Romanian Liga I", 40),
    4665: ("Romanian Liga II", 38),
}

session = requests.Session()
session.verify = False
session.headers.update({"User-Agent": "FootballAnalyticsDashboard/1.0"})


def build_table_from_events(events):
    """Build a full standings table from match events."""
    teams = {}
    form_tracker = {}  # team -> list of recent results (W/D/L)
    for e in events:
        hs = e.get("intHomeScore")
        aws = e.get("intAwayScore")
        if hs is None or aws is None:
            continue
        try:
            hs, aws = int(hs), int(aws)
        except (ValueError, TypeError):
            continue
        ht = e.get("strHomeTeam", "")
        at = e.get("strAwayTeam", "")
        if not ht or not at:
            continue
        for t in [ht, at]:
            if t not in teams:
                teams[t] = {
                    "strTeam": t, "intPlayed": 0, "intWin": 0, "intDraw": 0,
                    "intLoss": 0, "intGoalsFor": 0, "intGoalsAgainst": 0,
                    "intGoalDifference": 0, "intPoints": 0,
                }
                form_tracker[t] = []
        # Home team
        teams[ht]["intPlayed"] += 1
        teams[ht]["intGoalsFor"] += hs
        teams[ht]["intGoalsAgainst"] += aws
        # Away team
        teams[at]["intPlayed"] += 1
        teams[at]["intGoalsFor"] += aws
        teams[at]["intGoalsAgainst"] += hs

        if hs > aws:
            teams[ht]["intWin"] += 1
            teams[ht]["intPoints"] += 3
            teams[at]["intLoss"] += 1
            form_tracker[ht].append("W")
            form_tracker[at].append("L")
        elif hs < aws:
            teams[at]["intWin"] += 1
            teams[at]["intPoints"] += 3
            teams[ht]["intLoss"] += 1
            form_tracker[ht].append("L")
            form_tracker[at].append("W")
        else:
            teams[ht]["intDraw"] += 1
            teams[ht]["intPoints"] += 1
            teams[at]["intDraw"] += 1
            teams[at]["intPoints"] += 1
            form_tracker[ht].append("D")
            form_tracker[at].append("D")

    for t in teams.values():
        t["intGoalDifference"] = t["intGoalsFor"] - t["intGoalsAgainst"]
        # Last 5 results as form string
        t["strForm"] = "".join(form_tracker.get(t["strTeam"], [])[-5:])

    table = sorted(
        teams.values(),
        key=lambda x: (-x["intPoints"], -x["intGoalDifference"], -x["intGoalsFor"]),
    )
    for i, t in enumerate(table):
        t["intRank"] = i + 1
    return table


# ── Split-league rules: point halving after regular season ────────────
SPLIT_RULES = {
    4691: {  # Romanian Liga I
        "regular_matches_per_team": 30,
        "groups": [
            {"name": "Playoff", "positions": (1, 6), "halve": True},
            {"name": "Playout", "positions": (7, 16), "halve": True},
        ],
    },
    4338: {  # Belgian Pro League
        "regular_matches_per_team": 30,
        "groups": [
            {"name": "Championship Playoff", "positions": (1, 6), "halve": True},
            {"name": "Europa Playoff", "positions": (7, 12), "halve": True},
            {"name": "Relegation", "positions": (13, 16), "halve": False},
        ],
    },
    4336: {  # Greek Super League
        "regular_matches_per_team": 26,
        "groups": [
            {"name": "Championship", "positions": (1, 4), "halve": False},
            {"name": "Europa Playoff", "positions": (5, 8), "halve": True},
            {"name": "Relegation", "positions": (9, 14), "halve": False},
        ],
    },
}


def build_split_table(events, league_id):
    """Build standings with point halving for split leagues (Romania, Belgium, Greece)."""
    rules = SPLIT_RULES.get(league_id)
    if not rules:
        return build_table_from_events(events)

    regular_n = rules["regular_matches_per_team"]

    # Filter to played events with valid scores
    played = []
    for e in events:
        hs = e.get("intHomeScore")
        aws = e.get("intAwayScore")
        if hs is None or aws is None:
            continue
        try:
            int(hs); int(aws)
        except (ValueError, TypeError):
            continue
        if e.get("strHomeTeam") and e.get("strAwayTeam"):
            played.append(e)

    # Sort by date + time to get chronological order
    played.sort(key=lambda x: (x.get("dateEvent", ""), x.get("strTime", "")))

    # Check if regular season is complete (all teams have >= regular_n matches)
    team_total = defaultdict(int)
    for e in played:
        team_total[e["strHomeTeam"]] += 1
        team_total[e["strAwayTeam"]] += 1

    if not team_total:
        return build_table_from_events(events)

    # If no team has exceeded regular season matches, the split hasn't started
    if all(cnt <= regular_n for cnt in team_total.values()):
        return build_table_from_events(events)

    # Separate regular season from post-split using per-team match count
    team_match_count = defaultdict(int)
    regular_events = []
    post_split_events = []

    for e in played:
        ht = e["strHomeTeam"]
        at = e["strAwayTeam"]

        if team_match_count[ht] < regular_n and team_match_count[at] < regular_n:
            regular_events.append(e)
        else:
            post_split_events.append(e)

        team_match_count[ht] += 1
        team_match_count[at] += 1

    # Build regular season standings → determines group placement
    reg_table = build_table_from_events(regular_events)
    reg_by_team = {t["strTeam"]: t for t in reg_table}

    # Assign groups & halving flags based on regular season rank
    team_group = {}
    team_halve = {}
    for group in rules["groups"]:
        pos_start, pos_end = group["positions"]
        for t in reg_table:
            if pos_start <= t["intRank"] <= pos_end:
                team_group[t["strTeam"]] = group["name"]
                team_halve[t["strTeam"]] = group["halve"]

    # Build final standings: halved regular pts + post-split pts
    final = {}
    for team_name, reg in reg_by_team.items():
        reg_pts = reg["intPoints"]
        halve = team_halve.get(team_name, False)
        halved_pts = math.ceil(reg_pts / 2) if halve else reg_pts

        final[team_name] = {
            "strTeam": team_name,
            "intPlayed": reg["intPlayed"],
            "intWin": reg["intWin"],
            "intDraw": reg["intDraw"],
            "intLoss": reg["intLoss"],
            "intGoalsFor": reg["intGoalsFor"],
            "intGoalsAgainst": reg["intGoalsAgainst"],
            "intGoalDifference": reg["intGoalDifference"],
            "intPoints": halved_pts,
            "intRegSeasonPts": reg_pts,
            "intHalvedPts": halved_pts,
            "intPostSplitPts": 0,
            "strGroup": team_group.get(team_name, ""),
            "strForm": "",
        }

    # Add post-split results
    form_tracker = defaultdict(list)
    for e in post_split_events:
        hs = int(e["intHomeScore"])
        aws = int(e["intAwayScore"])
        ht = e["strHomeTeam"]
        at = e["strAwayTeam"]

        for t in [ht, at]:
            if t not in final:
                continue
            final[t]["intPlayed"] += 1

        if ht in final:
            final[ht]["intGoalsFor"] += hs
            final[ht]["intGoalsAgainst"] += aws
        if at in final:
            final[at]["intGoalsFor"] += aws
            final[at]["intGoalsAgainst"] += hs

        if hs > aws:
            if ht in final:
                final[ht]["intWin"] += 1
                final[ht]["intPoints"] += 3
                final[ht]["intPostSplitPts"] += 3
            if at in final:
                final[at]["intLoss"] += 1
            form_tracker[ht].append("W")
            form_tracker[at].append("L")
        elif hs < aws:
            if at in final:
                final[at]["intWin"] += 1
                final[at]["intPoints"] += 3
                final[at]["intPostSplitPts"] += 3
            if ht in final:
                final[ht]["intLoss"] += 1
            form_tracker[ht].append("L")
            form_tracker[at].append("W")
        else:
            if ht in final:
                final[ht]["intDraw"] += 1
                final[ht]["intPoints"] += 1
                final[ht]["intPostSplitPts"] += 1
            if at in final:
                final[at]["intDraw"] += 1
                final[at]["intPoints"] += 1
                final[at]["intPostSplitPts"] += 1
            form_tracker[ht].append("D")
            form_tracker[at].append("D")

    # Update GD & form
    for t in final.values():
        t["intGoalDifference"] = t["intGoalsFor"] - t["intGoalsAgainst"]
        t["strForm"] = "".join(form_tracker.get(t["strTeam"], [])[-5:])

    # Sort: by group order first, then by points within group
    group_order = {g["name"]: i for i, g in enumerate(rules["groups"])}
    table = sorted(
        final.values(),
        key=lambda x: (
            group_order.get(x.get("strGroup", ""), 99),
            -x["intPoints"],
            -x["intGoalDifference"],
            -x["intGoalsFor"],
        ),
    )
    for i, t in enumerate(table):
        t["intRank"] = i + 1

    return table


def fetch_league_events(lid, name, max_rounds):
    """Fetch all rounds for a league, merging with existing data. Returns (events, new_count)."""
    out_path = os.path.join(DATA_DIR, f"all_events_2526_{lid}.json")

    # Load existing events
    existing_events = []
    existing_ids = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        existing_events = data.get("events", [])
        for e in existing_events:
            eid = e.get("idEvent")
            if eid:
                existing_ids.add(str(eid))

    # Find which rounds already have complete data (all events have scores)
    rounds_with_data = set()
    for e in existing_events:
        r = e.get("intRound")
        if r and e.get("intHomeScore") is not None:
            rounds_with_data.add(str(r))

    # Also track rounds that have events but no scores yet (need re-fetch)
    rounds_pending = set()
    for e in existing_events:
        r = e.get("intRound")
        if r and e.get("intHomeScore") is None:
            rounds_pending.add(str(r))

    new_count = 0
    updated_count = 0

    for rnd in range(1, max_rounds + 1):
        rnd_str = str(rnd)
        # Skip rounds where we have all scored results, unless they have pending matches
        if rnd_str in rounds_with_data and rnd_str not in rounds_pending:
            continue

        url = f"{BASE}/eventsround.php?id={lid}&r={rnd}&s={SEASON}"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 429:
                time.sleep(3)
                resp = session.get(url, timeout=15)

            if resp.status_code == 200:
                api_data = resp.json()
                events = api_data.get("events") or []
                for evt in events:
                    eid = str(evt.get("idEvent", ""))
                    if eid in existing_ids:
                        # Update existing event (may now have scores)
                        for i, ex in enumerate(existing_events):
                            if str(ex.get("idEvent", "")) == eid:
                                if evt.get("intHomeScore") is not None and ex.get("intHomeScore") is None:
                                    existing_events[i] = evt
                                    updated_count += 1
                                break
                    else:
                        existing_events.append(evt)
                        existing_ids.add(eid)
                        new_count += 1
            time.sleep(0.8)  # Rate limit courtesy
        except Exception as e:
            print(f"  Round {rnd}: ERROR {e}")

    return existing_events, new_count, updated_count


def update_league(lid, name, max_rounds):
    """Fetch new events and rebuild standings for one league."""
    print(f"\n{'='*50}")
    print(f"  {name} (ID {lid})")
    print(f"{'='*50}")

    # 1. Fetch latest events
    events, new_count, updated_count = fetch_league_events(lid, name, max_rounds)
    played = [e for e in events if e.get("intHomeScore") is not None]
    print(f"  Events: {len(events)} total, {len(played)} played")
    print(f"  New events: {new_count}, Updated scores: {updated_count}")

    # 2. Save updated events
    events_path = os.path.join(DATA_DIR, f"all_events_2526_{lid}.json")
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump({"events": events}, f, ensure_ascii=False, indent=2)

    # 3. Rebuild standings from events
    if len(played) >= 2:
        # Use split-table logic for leagues with point halving (Romania, Belgium, Greece)
        if lid in SPLIT_RULES:
            table = build_split_table(played, lid)
            is_split = any(t.get("strGroup") for t in table)
        else:
            table = build_table_from_events(played)
            is_split = False

        standings_path = os.path.join(DATA_DIR, f"full_standings_2526_{lid}.json")
        with open(standings_path, "w", encoding="utf-8") as f:
            json.dump({
                "table": table,
                "league_id": lid,
                "league_name": name,
                "no_resort": True,
                "is_split_active": is_split,
                "updated_at": datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)

        if is_split:
            groups = set(t.get("strGroup", "") for t in table if t.get("strGroup"))
            grp_info = ", ".join(f"{g}: {sum(1 for t in table if t.get('strGroup')==g)}" for g in sorted(groups))
            print(f"  Standings (split): {len(table)} teams — {grp_info}")
            print(f"  Leader: {table[0]['strTeam']} ({table[0]['intPoints']} pts, "
                  f"reg {table[0].get('intRegSeasonPts','?')} → halved {table[0].get('intHalvedPts','?')} "
                  f"+ post {table[0].get('intPostSplitPts','?')})")
        else:
            print(f"  Standings: {len(table)} teams, leader: {table[0]['strTeam']} ({table[0]['intPoints']} pts)")
    else:
        print(f"  Not enough played matches to build standings")

    # 4. Also fetch API standings for form data
    try:
        url = f"{BASE}/lookuptable.php?l={lid}&s={SEASON}"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            api_table = resp.json().get("table") or []
            if api_table:
                api_path = os.path.join(DATA_DIR, f"standings_2526_{lid}.json")
                with open(api_path, "w", encoding="utf-8") as f:
                    json.dump({"table": api_table}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return new_count + updated_count


def save_update_log(results):
    """Save a log of when data was last updated."""
    log_path = os.path.join(DATA_DIR, "last_update.json")
    log = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "leagues_updated": results,
        "total_changes": sum(r.get("changes", 0) for r in results),
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    return log


def run_update(league_ids=None):
    """Run the full update. Pass league_ids to update specific leagues only."""
    print(f"\n{'#'*60}")
    print(f"  Football Analytics — Data Update")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    os.makedirs(DATA_DIR, exist_ok=True)

    results = []
    leagues_to_update = league_ids or list(LEAGUES.keys())

    for lid in leagues_to_update:
        if lid not in LEAGUES:
            print(f"  Unknown league ID: {lid}")
            continue
        name, max_rounds = LEAGUES[lid]
        changes = update_league(lid, name, max_rounds)
        results.append({"league_id": lid, "league": name, "changes": changes})

    log = save_update_log(results)
    print(f"\n{'='*60}")
    print(f"  UPDATE COMPLETE — {log['total_changes']} total changes")
    print(f"  Timestamp: {log['date']}")
    print(f"{'='*60}\n")

    return log


if __name__ == "__main__":
    # Allow passing specific league IDs as arguments
    if len(sys.argv) > 1:
        ids = [int(x) for x in sys.argv[1:]]
        run_update(ids)
    else:
        run_update()
