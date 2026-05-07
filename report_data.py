"""
Report Data Module - Loads and prepares all data for the report.
"""

import json, glob, os, re
import pandas as pd
import numpy as np

DATA_DIR = "data"
IMG_DIR = "report_images"
os.makedirs(IMG_DIR, exist_ok=True)

LEAGUE_ID_TO_NAME = {
    4328: "English Premier League", 4335: "La Liga", 4332: "Serie A",
    4331: "Bundesliga", 4334: "Ligue 1", 4337: "Eredivisie",
    4344: "Primeira Liga", 4339: "Turkish Super Lig", 4338: "Belgian Pro League",
    4355: "Russian Premier League", 4330: "Scottish Premiership",
    4340: "Danish Superliga", 4336: "Greek Super League",
    4691: "Romanian Liga I", 4665: "Romanian Liga II",
}

LEAGUE_STRENGTH = {
    "English Premier League": 1.00, "La Liga": 0.95, "Serie A": 0.90, "Bundesliga": 0.88,
    "Ligue 1": 0.80, "Eredivisie": 0.65, "Primeira Liga": 0.70, "Turkish Super Lig": 0.55,
    "Belgian Pro League": 0.55, "Scottish Premiership": 0.45, "Greek Super League": 0.45,
    "Danish Superliga": 0.40, "Russian Premier League": 0.50, "Romanian Liga I": 0.35, "Romanian Liga II": 0.20,
}

LEAGUE_MARKET = {
    "English Premier League": 500, "La Liga": 350, "Serie A": 280, "Bundesliga": 280,
    "Ligue 1": 200, "Eredivisie": 60, "Primeira Liga": 70, "Turkish Super Lig": 40,
    "Belgian Pro League": 30, "Scottish Premiership": 15, "Greek Super League": 20,
    "Danish Superliga": 15, "Russian Premier League": 30, "Romanian Liga I": 8, "Romanian Liga II": 2,
}


def load_standings():
    frames = []
    for fpath in glob.glob(os.path.join(DATA_DIR, "full_standings_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            table = data.get("table", [])
            if not table:
                continue
            df = pd.DataFrame(table)
            for c in ["intRank","intPlayed","intWin","intLoss","intDraw","intGoalsFor","intGoalsAgainst","intGoalDifference","intPoints"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
            lid = data.get("league_id")
            if lid:
                lid = int(lid)
                df["league"] = LEAGUE_ID_TO_NAME.get(lid, "Unknown")
                df["league_id"] = lid
            frames.append(df)
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_events():
    frames = []
    for fpath in glob.glob(os.path.join(DATA_DIR, "all_events_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            events = data.get("events", [])
            if not events:
                continue
            df = pd.DataFrame(events)
            lid = data.get("league_id")
            if lid:
                df["league"] = LEAGUE_ID_TO_NAME.get(int(lid), "Unknown")
            elif "strLeague" in df.columns:
                df["league"] = df["strLeague"]
            else:
                m = re.search(r"_(\d+)\.json$", fpath)
                if m:
                    lid = int(m.group(1))
                    df["league"] = LEAGUE_ID_TO_NAME.get(lid, "Unknown")
            frames.append(df)
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_players():
    fpath = os.path.join(DATA_DIR, "all_players_2526.json")
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    return pd.DataFrame()


def load_raw_romania():
    """Load raw Romanian Liga I JSON for group info."""
    fpath = os.path.join(DATA_DIR, "full_standings_2526_4691.json")
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("table", [])
    return []


def prepare_data():
    """Load and prepare all datasets. Returns a dict with all prepared data."""
    print("Loading data...")
    standings = load_standings()
    events = load_events()
    players = load_players()

    # Romanian Liga I
    ro_standings = standings[standings["league"] == "Romanian Liga I"].copy() if not standings.empty else pd.DataFrame()
    if not ro_standings.empty:
        ro_standings = ro_standings.sort_values("intPoints", ascending=False).reset_index(drop=True)
        ro_standings["intRank"] = range(1, len(ro_standings) + 1)

    ro_events = events[events["league"] == "Romanian Liga I"].copy() if not events.empty and "league" in events.columns else pd.DataFrame()
    if not ro_events.empty:
        for col in ["intHomeScore", "intAwayScore"]:
            if col in ro_events.columns:
                ro_events[col] = pd.to_numeric(ro_events[col], errors="coerce")
        if "dateEvent" in ro_events.columns:
            ro_events["dateEvent"] = pd.to_datetime(ro_events["dateEvent"], errors="coerce")

    # Raw group data
    raw_romania = load_raw_romania()
    playoff_teams_data = [t for t in raw_romania if t.get("strGroup") == "Playoff"]
    playout_teams_data = [t for t in raw_romania if t.get("strGroup") == "Playout"]

    # Process events for all leagues
    if not events.empty:
        for col in ["intHomeScore", "intAwayScore"]:
            if col in events.columns:
                events[col] = pd.to_numeric(events[col], errors="coerce")
        if "dateEvent" in events.columns:
            events["dateEvent"] = pd.to_datetime(events["dateEvent"], errors="coerce")

    # Player processing
    if not players.empty and "dateBorn" in players.columns:
        players["dateBorn"] = pd.to_datetime(players["dateBorn"], errors="coerce")
        players["age"] = ((pd.Timestamp.now() - players["dateBorn"]).dt.days / 365.25).round(1)

    print(f"Romanian Liga I: {len(ro_standings)} teams, {len(ro_events)} events")
    print(f"Total data: {len(standings)} standings rows, {len(events)} events, {len(players)} players")

    return {
        "standings": standings,
        "events": events,
        "players": players,
        "ro_standings": ro_standings,
        "ro_events": ro_events,
        "playoff_teams_data": playoff_teams_data,
        "playout_teams_data": playout_teams_data,
        "raw_romania": raw_romania,
    }
