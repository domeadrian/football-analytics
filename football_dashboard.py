"""
Football Analytics Dashboard — 2025-2026 Season
=================================================
All European leagues, teams, and players with full filtering.
Real data from TheSportsDB API.

Run: python -m streamlit run football_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import glob
from scipy.stats import poisson
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Football Analytics 2025-2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

LEAGUE_ID_TO_NAME = {
    4328: "English Premier League",
    4335: "La Liga",
    4332: "Serie A",
    4331: "Bundesliga",
    4334: "Ligue 1",
    4337: "Eredivisie",
    4344: "Primeira Liga",
    4339: "Turkish Super Lig",
    4338: "Belgian Pro League",
    4355: "Russian Premier League",
    4330: "Scottish Premiership",
    4340: "Danish Superliga",
    4336: "Greek Super League",
    4691: "Romanian Liga I",
    4665: "Romanian Liga II",
}

# Leagues with playoff / playout phases
LEAGUE_FORMAT = {
    "Romanian Liga I": {
        "type": "playoff_playout",
        "regular_season": 30,
        "description": "16 teams play 30 rounds (regular season). "
                       "Top 6 → **Championship Playoff** (10 extra rounds, points halved). "
                       "1st = Champion + UCL. 2nd–3rd: Europa / Conference League spots. "
                       "Bottom 10 → **Relegation Playout** (18 extra rounds). "
                       "Last 2 (15th & 16th overall) directly relegated. "
                       "13th & 14th overall (playout 7th & 8th) play promotion/relegation "
                       "vs Liga II playoff 3rd & 4th.",
        "playoff_teams": 6,
        "playout_teams": 10,
        "halve_points": True,
        "ucl_spots": 1,
        "uel_spots": 1,
        "uecl_spots": 1,
        "relegation": 2,
        "relegation_playoff": 2,
    },
    "Romanian Liga II": {
        "type": "liga2_ro",
        "regular_season": 21,
        "description": "22 teams play 21 rounds (single round-robin). "
                       "Top 6 → **Promotion Playoff** (keep all RS points + 10 rounds). "
                       "1st & 2nd auto-promote to Liga I; 3rd & 4th play "
                       "promotion/relegation vs Liga I 13th & 14th. "
                       "Remaining 16 split into **Group A** (8 teams) and **Group B** (8 teams). "
                       "Last 2 of each group relegated directly. "
                       "Both 6th-placed teams play a **playout**; the loser also relegated (5 total relegations).",
        "playoff_teams": 6,
        "playout_group_size": 8,
        "auto_promotion": 2,
        "relegation_per_group": 2,
        "playout_relegation": 1,
    },
    "Belgian Pro League": {
        "type": "belgian",
        "regular_season": 30,
        "description": "16 teams play 30 rounds. "
                       "Top 6 → **Championship Playoff** (points halved + 10 rounds). "
                       "1st = Champion + UCL. Top 2–4: European spots. "
                       "7th–12th → **Europa Playoff** (compete for Conference League via extra playoff). "
                       "13th–16th → **Relegation Playoff** (last relegated; others fight for survival).",
        "playoff_teams": 6,
        "europa_playoff_teams": 6,
        "relegation_playoff_teams": 4,
        "halve_points": True,
        "ucl_spots": 1,
        "uel_spots": 1,
        "relegation": 1,
    },
    "Scottish Premiership": {
        "type": "split",
        "regular_season": 33,
        "description": "12 teams play 33 rounds (3 full rounds). "
                       "Top 6 → **Championship Split** (5 more rounds — decide champion + Europe). "
                       "Bottom 6 → **Relegation Split** (5 more rounds — "
                       "12th relegated; 11th plays relegation playoff vs Championship winner).",
        "split_at": 6,
        "relegation": 1,
        "relegation_playoff": 1,
    },
    "Danish Superliga": {
        "type": "playoff_playout",
        "regular_season": 22,
        "description": "12 teams play 22 rounds (each team plays every other twice). "
                       "Top 6 → **Championship Group** (10 more rounds, points carry over — "
                       "1st = Champion + UCL; 2nd = Conference League). "
                       "Bottom 6 → **Relegation Group** (10 more rounds, points carry over — "
                       "11th & 12th relegated to 1st Division).",
        "playoff_teams": 6,
        "playout_teams": 6,
        "relegation": 2,
    },
    "Austrian Bundesliga": {
        "type": "split",
        "regular_season": 22,
        "description": "12 teams play 22 rounds (each team plays every other twice). "
                       "Top 6 → **Meistergruppe** (Championship group, 10 more rounds, points halved). "
                       "1st = Champion + UCL. 2nd–3rd: CL/Europa spots. 4th–5th: European playoff. "
                       "Bottom 6 → **Qualifikationsgruppe** (10 more rounds, points halved). "
                       "12th overall: direct relegation. "
                       "Winner of bottom group → European playoff vs 4th/5th from top group for Conference League.",
        "split_at": 6,
        "halve_points": True,
        "ucl_spots": 1,
        "uel_spots": 1,
        "relegation": 1,
    },
    "Swiss Super League": {
        "type": "split",
        "regular_season": 33,
        "description": "12 teams play 33 rounds (3 full rounds). "
                       "Top 6 → **Championship Round** (decide title + European places). "
                       "Bottom 6 → **Relegation Round** (bottom relegated; second-bottom → playoff). "
                       "Points carry over fully (NOT halved).",
        "split_at": 6,
        "halve_points": False,
        "relegation": 1,
        "relegation_playoff": 1,
    },
}

# =========================================================================
# DATA LOADING
# =========================================================================

@st.cache_data
def load_all_standings():
    """Load all 2025-2026 standings — prefer full_standings (all teams) over standings (top 5 only)."""
    frames = []
    loaded_leagues = set()
    no_resort_leagues = set()  # leagues where we trust the stored rank order
    # First: full standings (computed from events, all teams)
    for fpath in glob.glob(os.path.join(DATA_DIR, "full_standings_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            table = data.get("table", [])
            if not table:
                continue
            df = pd.DataFrame(table)
            int_cols = ["intRank", "intPlayed", "intWin", "intLoss", "intDraw",
                        "intGoalsFor", "intGoalsAgainst", "intGoalDifference", "intPoints"]
            for c in int_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
            lid = data.get("league_id")
            if lid:
                lid = int(lid)
                df["league"] = LEAGUE_ID_TO_NAME.get(lid, data.get("league_name", "Unknown"))
                df["league_id"] = lid
                loaded_leagues.add(lid)
            elif "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0])
                df["league"] = LEAGUE_ID_TO_NAME.get(lid, "Unknown")
                df["league_id"] = lid
                loaded_leagues.add(lid)
            # Track leagues that should NOT be re-sorted (active playoff/playout phase)
            if data.get("no_resort"):
                league_name = df["league"].iloc[0] if "league" in df.columns and len(df) > 0 else None
                if league_name:
                    no_resort_leagues.add(league_name)
            # Carry the group column through if present (playoff / playout_a / playout_b etc.)
            frames.append(df)
        except Exception:
            continue
    # Fallback: API standings for leagues not yet in full_standings
    for fpath in glob.glob(os.path.join(DATA_DIR, "standings_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            table = data.get("table", [])
            if not table:
                continue
            df = pd.DataFrame(table)
            if "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0])
                if lid in loaded_leagues:
                    continue  # already have full version
                df["league"] = LEAGUE_ID_TO_NAME.get(lid, "Unknown")
                df["league_id"] = lid
            int_cols = ["intRank", "intPlayed", "intWin", "intLoss", "intDraw",
                        "intGoalsFor", "intGoalsAgainst", "intGoalDifference", "intPoints"]
            for c in int_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
            frames.append(df)
        except Exception:
            continue
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        # Re-sort each league by points/GD/GF and re-assign ranks
        # SKIP re-sort for leagues in active playoff/playout phase (no_resort flag)
        resorted = []
        for league_name in combined["league"].unique():
            ldf = combined[combined["league"] == league_name].copy()
            if league_name not in no_resort_leagues:
                ldf = ldf.sort_values(
                    ["intPoints", "intGoalDifference", "intGoalsFor"],
                    ascending=[False, False, False],
                ).reset_index(drop=True)
                ldf["intRank"] = range(1, len(ldf) + 1)
            resorted.append(ldf)
        return pd.concat(resorted, ignore_index=True)
    return pd.DataFrame()


@st.cache_data
def load_all_events():
    """Load all 2025-2026 events — prefer all_events_2526_* (full season), fall back to events_2526_*."""
    frames = []
    loaded_leagues = set()
    # First: load full-season files (all_events_2526_*)
    for fpath in glob.glob(os.path.join(DATA_DIR, "all_events_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            events = data.get("events", [])
            if not events:
                continue
            df = pd.DataFrame(events)
            for c in ["intHomeScore", "intAwayScore", "intRound"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            if "dateEvent" in df.columns:
                df["dateEvent"] = pd.to_datetime(df["dateEvent"], errors="coerce")
            if "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0])
                df["league"] = LEAGUE_ID_TO_NAME.get(lid, "")
                loaded_leagues.add(lid)
            frames.append(df)
        except Exception:
            continue
    # Fallback: old files for leagues not yet fully fetched
    for fpath in glob.glob(os.path.join(DATA_DIR, "events_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            events = data.get("events", [])
            if not events:
                continue
            df = pd.DataFrame(events)
            if "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0])
                if lid in loaded_leagues:
                    continue  # already loaded full version
                df["league"] = LEAGUE_ID_TO_NAME.get(lid, "")
            for c in ["intHomeScore", "intAwayScore", "intRound"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            if "dateEvent" in df.columns:
                df["dateEvent"] = pd.to_datetime(df["dateEvent"], errors="coerce")
            frames.append(df)
        except Exception:
            continue
    if frames:
        result = pd.concat(frames, ignore_index=True)
        if "idEvent" in result.columns:
            result = result.drop_duplicates(subset=["idEvent"])
        return result
    return pd.DataFrame()


@st.cache_data
def load_all_teams():
    """Load all teams from the consolidated file."""
    path = os.path.join(DATA_DIR, "all_teams_2526.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)
        if "_leagueName" in df.columns:
            df.rename(columns={"_leagueName": "league"}, inplace=True)
        return df
    return pd.DataFrame()


@st.cache_data
def load_all_players():
    """Load all players from the consolidated file."""
    path = os.path.join(DATA_DIR, "all_players_2526.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)
        if "_leagueName" in df.columns:
            df.rename(columns={"_leagueName": "league"}, inplace=True)
        if "dateBorn" in df.columns:
            df["birth_date"] = pd.to_datetime(df["dateBorn"], dayfirst=True, errors="coerce")
            # Use pre-scraped age from Transfermarkt if available, else calculate from DOB
            if "age" in df.columns:
                df["age"] = pd.to_numeric(df["age"], errors="coerce")
                # Fill any remaining NaN from birth_date
                mask = df["age"].isna() & df["birth_date"].notna()
                df.loc[mask, "age"] = ((pd.Timestamp.now() - df.loc[mask, "birth_date"]).dt.days / 365.25).round(1)
            else:
                df["age"] = ((pd.Timestamp.now() - df["birth_date"]).dt.days / 365.25).round(1)
        return df
    return pd.DataFrame()


# Load data
all_standings = load_all_standings()
all_events = load_all_events()
all_teams = load_all_teams()
all_players = load_all_players()

# =========================================================================
# SIDEBAR — FILTERS
# =========================================================================
st.sidebar.title("⚽ Football Analytics")
st.sidebar.caption("Season 2025-2026 · All European Leagues")
st.sidebar.markdown("---")

# League filter
available_leagues = sorted(all_standings["league"].unique().tolist()) if not all_standings.empty else []
selected_leagues = st.sidebar.multiselect(
    "🏟️ Filter by League",
    options=available_leagues,
    default=available_leagues,
    help="Select one or more leagues",
)

# Team filter (depends on league selection)
if not all_standings.empty and selected_leagues:
    league_teams = sorted(
        all_standings[all_standings["league"].isin(selected_leagues)]["strTeam"].unique().tolist()
    )
else:
    league_teams = []

selected_teams = st.sidebar.multiselect(
    "👕 Filter by Team",
    options=league_teams,
    default=[],
    help="Leave empty to show all teams in selected leagues",
)

# Player search
player_search = st.sidebar.text_input("🔍 Search Player", "", help="Type player name to search")

st.sidebar.markdown("---")

# Apply filters to data
def filter_standings(df):
    if df.empty:
        return df
    filtered = df[df["league"].isin(selected_leagues)] if selected_leagues else df
    if selected_teams:
        filtered = filtered[filtered["strTeam"].isin(selected_teams)]
    return filtered

def filter_events(df):
    if df.empty:
        return df
    filtered = df[df["league"].isin(selected_leagues)] if selected_leagues else df
    if selected_teams:
        filtered = filtered[
            (filtered["strHomeTeam"].isin(selected_teams)) |
            (filtered["strAwayTeam"].isin(selected_teams))
        ]
    return filtered

def filter_players(df):
    if df.empty:
        return df
    filtered = df
    if selected_leagues and "league" in df.columns:
        filtered = filtered[filtered["league"].isin(selected_leagues)]
    if selected_teams and "_teamName" in df.columns:
        filtered = filtered[filtered["_teamName"].isin(selected_teams)]
    if player_search:
        mask = filtered["strPlayer"].str.contains(player_search, case=False, na=False)
        filtered = filtered[mask]
    return filtered

f_standings = filter_standings(all_standings)
f_events = filter_events(all_events)
f_players = filter_players(all_players)

# Page navigation
pages = [
    "🏠 Overview & Standings",
    "📊 Match Analysis",
    "🎯 Championship Probability",
    "🌍 European Comparison",
    "👤 Player Analysis",
    "💰 Transfer Recommendations",
    "🤖 ML Prediction Models",
    "📈 Advanced Statistics",
    "📋 Data Sources",
]
page = st.sidebar.radio("Section", pages)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Data loaded:** {len(all_standings)} team-standings · "
    f"{len(all_events)} events · "
    f"{len(all_players)} players"
)


# =========================================================================
# PAGE: Overview & Standings
# =========================================================================
if page == "🏠 Overview & Standings":
    st.title("⚽ Football Analytics Dashboard — 2025-2026")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Leagues", len(selected_leagues))
    col2.metric("Teams", len(f_standings["strTeam"].unique()) if not f_standings.empty else 0)
    col3.metric("Matches", len(f_events))
    col4.metric("Players", len(f_players))

    if f_standings.empty:
        st.warning("No standings data. Adjust your league filter.")
    else:
        # Helper to create a styled standings table
        def _make_table(df, show_pos=True):
            """Return a display DataFrame from standings rows."""
            display_cols = ["intRank", "strTeam", "intPlayed", "intWin", "intDraw", "intLoss",
                            "intGoalsFor", "intGoalsAgainst", "intGoalDifference", "intPoints"]
            display_cols = [c for c in display_cols if c in df.columns]
            disp = df[display_cols].copy()
            col_names = ["Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]
            disp.columns = col_names[:len(display_cols)]
            return disp

        # Show standings per league
        for league_name in sorted(f_standings["league"].unique()):
            league_df = f_standings[f_standings["league"] == league_name].sort_values("intRank")
            st.subheader(f"🏆 {league_name}")

            fmt = LEAGUE_FORMAT.get(league_name)

            # === PLAYOFF / PLAYOUT LEAGUES ===
            if fmt:
                st.info(f"**Format:** {fmt['description']}")
                ftype = fmt["type"]

                # ── Romanian Liga II: playoff + 2 playout groups ──
                if ftype == "liga2_ro":
                    n_po = fmt.get("playoff_teams", 6)
                    n_total = len(league_df)
                    n_po_actual = min(n_po, n_total)

                    po_df = league_df[league_df["intRank"] <= n_po_actual].copy()
                    rest_df = league_df[league_df["intRank"] > n_po_actual].copy()

                    if not po_df.empty:
                        st.markdown(f"**🟢 Promotion Playoff** (Top {n_po_actual} — "
                                    "1st & 2nd auto-promote; 3rd & 4th play Liga I 13th & 14th)")
                        po_disp = _make_table(po_df)
                        zones_po = []
                        for _, row in po_df.iterrows():
                            if row["intRank"] <= 2:
                                zones_po.append("🟢 Auto-Promotion")
                            elif row["intRank"] <= 4:
                                zones_po.append("🟡 Promotion Playoff")
                            else:
                                zones_po.append("")
                        po_disp["Zone"] = zones_po
                        st.dataframe(po_disp, use_container_width=True, hide_index=True)

                    if not rest_df.empty:
                        n_rest = len(rest_df)
                        half = (n_rest + 1) // 2  # split evenly, first group gets extra if odd
                        grp_a = rest_df.iloc[:half].copy()
                        grp_b = rest_df.iloc[half:].copy()

                        rel_per = fmt.get("relegation_per_group", 2)

                        for label, grp, start_pos in [
                            ("A", grp_a, n_po_actual + 1),
                            ("B", grp_b, n_po_actual + half + 1),
                        ]:
                            if grp.empty:
                                continue
                            grp_size = len(grp)
                            end_pos = start_pos + grp_size - 1
                            st.markdown(f"**🟠 Playout Group {label}** "
                                        f"(Positions {start_pos}–{end_pos})")
                            disp = _make_table(grp)
                            zones = []
                            for idx in range(grp_size):
                                pos_in_grp = idx + 1
                                if pos_in_grp > grp_size - rel_per:
                                    zones.append("🔴 Relegated")
                                elif pos_in_grp == grp_size - rel_per:
                                    zones.append("🟡 Playout (loser relegated)")
                                else:
                                    zones.append("")
                            disp["Zone"] = zones
                            st.dataframe(disp, use_container_width=True, hide_index=True)
                    elif n_total <= n_po:
                        st.caption(f"Only {n_total} teams available (not enough for playout groups).")

                # ── Belgian Pro League: 3-way split ──
                elif ftype == "belgian":
                    n_po = fmt.get("playoff_teams", 6)
                    n_europa = fmt.get("europa_playoff_teams", 6)
                    n_rel = fmt.get("relegation_playoff_teams", 4)
                    n_total = len(league_df)

                    po_df = league_df[league_df["intRank"] <= n_po].copy()
                    europa_df = league_df[(league_df["intRank"] > n_po) &
                                          (league_df["intRank"] <= n_po + n_europa)].copy()
                    rel_df = league_df[league_df["intRank"] > n_po + n_europa].copy()

                    if not po_df.empty:
                        st.markdown(f"**🟢 Championship Playoff** (Top {n_po} — points halved + 10 rounds)")
                        st.dataframe(_make_table(po_df), use_container_width=True, hide_index=True)
                    if not europa_df.empty:
                        st.markdown(f"**🟡 Europa Playoff** (Positions {n_po+1}–{n_po+n_europa})")
                        st.dataframe(_make_table(europa_df), use_container_width=True, hide_index=True)
                    if not rel_df.empty:
                        st.markdown(f"**🔴 Relegation Playoff** (Positions {n_po+n_europa+1}–{n_total} — last relegated)")
                        st.dataframe(_make_table(rel_df), use_container_width=True, hide_index=True)

                # ── Standard playoff/playout (Romania Liga I, Denmark) ──
                elif ftype == "playoff_playout":
                    n_po = fmt.get("playoff_teams", 6)
                    n_total = len(league_df)
                    # If fewer teams than split, show all in one table
                    n_po_actual = min(n_po, n_total)

                    po_df = league_df[league_df["intRank"] <= n_po_actual].copy()
                    playout_df = league_df[league_df["intRank"] > n_po_actual].copy()

                    if not po_df.empty:
                        halve_note = " (points halved)" if fmt.get("halve_points") else ""
                        st.markdown(f"**🟢 Championship Playoff** (Top {n_po_actual}{halve_note})")
                        st.dataframe(_make_table(po_df), use_container_width=True, hide_index=True)

                    if not playout_df.empty:
                        n_rel = fmt.get("relegation", 0)
                        n_rel_po = fmt.get("relegation_playoff", 0)
                        st.markdown(f"**🟠 Relegation Playout** (Positions {n_po_actual+1}–{n_total})")
                        playout_disp = _make_table(playout_df)
                        if n_rel > 0 or n_rel_po > 0:
                            zones = []
                            for _, row in playout_df.iterrows():
                                if n_rel > 0 and row["intRank"] > n_total - n_rel:
                                    zones.append("🔴 Relegated")
                                elif n_rel_po > 0 and row["intRank"] > n_total - n_rel - n_rel_po:
                                    zones.append("🟡 Prom./Rel. Playoff")
                                else:
                                    zones.append("")
                            playout_disp["Zone"] = zones
                        st.dataframe(playout_disp, use_container_width=True, hide_index=True)
                    elif n_total <= n_po:
                        st.caption(f"Only {n_total} teams available (need more data for playout table).")

                # ── Split leagues (Scotland, Austria, Switzerland) ──
                elif ftype == "split":
                    split_at = fmt.get("split_at", 6)
                    n_total = len(league_df)
                    split_at_actual = min(split_at, n_total)

                    top_df = league_df[league_df["intRank"] <= split_at_actual].copy()
                    bottom_df = league_df[league_df["intRank"] > split_at_actual].copy()

                    if not top_df.empty:
                        halve_note = " (points halved)" if fmt.get("halve_points") else ""
                        st.markdown(f"**🟢 Championship Group / Top Split** (Top {split_at_actual}{halve_note})")
                        st.dataframe(_make_table(top_df), use_container_width=True, hide_index=True)

                    if not bottom_df.empty:
                        n_rel = fmt.get("relegation", 0)
                        n_rel_po = fmt.get("relegation_playoff", 0)
                        st.markdown(f"**🟠 Relegation Group / Bottom Split** (Positions {split_at_actual+1}–{n_total})")
                        bottom_disp = _make_table(bottom_df)
                        if n_rel > 0 or n_rel_po > 0:
                            zones = []
                            for _, row in bottom_df.iterrows():
                                if n_rel > 0 and row["intRank"] > n_total - n_rel:
                                    zones.append("🔴 Relegation")
                                elif n_rel_po > 0 and row["intRank"] > n_total - n_rel - n_rel_po:
                                    zones.append("🟡 Rel. Playoff")
                                else:
                                    zones.append("")
                            bottom_disp["Zone"] = zones
                        st.dataframe(bottom_disp, use_container_width=True, hide_index=True)
                    elif n_total <= split_at:
                        st.caption(f"Only {n_total} teams available (need more data for relegation group).")

                # ── Fallback for any other format type ──
                else:
                    disp = _make_table(league_df)
                    st.dataframe(disp, use_container_width=True, hide_index=True)
            else:
                # === STANDARD LEAGUES: single table with position column ===
                if fmt:
                    st.info(f"**Format:** {fmt['description']}")
                disp = _make_table(league_df)
                st.dataframe(disp, use_container_width=True, hide_index=True)

            # Form visualization
            if "strForm" in league_df.columns:
                form_data = league_df[["strTeam", "strForm"]].dropna()
                if not form_data.empty:
                    form_text = ""
                    for _, row in form_data.iterrows():
                        form_str = str(row["strForm"])
                        icons = {"W": "🟢", "D": "🟡", "L": "🔴"}
                        colored = "".join(icons.get(c, "") for c in form_str)
                        form_text += f"**{row['strTeam']}**: {colored}  \n"
                    with st.expander("Recent Form (Last 5)"):
                        st.markdown(form_text)

        # Cross-league points chart (if multiple leagues)
        if len(f_standings["league"].unique()) > 1:
            st.subheader("Points Distribution — All Selected Leagues")
            top_n = st.slider("Top N teams per league", 3, 10, 5)
            top_teams = (
                f_standings.groupby("league", group_keys=False)
                .apply(lambda g: g.nlargest(top_n, "intPoints"))
                .reset_index(drop=True)
            )
            fig = px.bar(
                top_teams.sort_values(["league", "intPoints"], ascending=[True, True]),
                x="intPoints", y="strTeam", color="league", orientation="h",
                title=f"Top {top_n} Teams per League — Points",
                text="intPoints",
                height=max(400, len(top_teams) * 25),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(template="plotly_white", showlegend=True,
                              yaxis={"categoryorder": "total ascending"},
                              legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)


# =========================================================================
# PAGE: Match Analysis
# =========================================================================
elif page == "📊 Match Analysis":
    st.title("📊 Match Analysis — 2025-2026 Season")

    if f_events.empty:
        st.warning("No match events for selected filters. Try selecting more leagues.")
    else:
        # Date range filter
        if "dateEvent" in f_events.columns:
            min_date = f_events["dateEvent"].dropna().min()
            max_date = f_events["dateEvent"].dropna().max()
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "Date Range",
                    value=(min_date.date(), max_date.date()),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                    key="match_dates",
                )
                if len(date_range) == 2:
                    f_events_filtered = f_events[
                        (f_events["dateEvent"].dt.date >= date_range[0]) &
                        (f_events["dateEvent"].dt.date <= date_range[1])
                    ]
                else:
                    f_events_filtered = f_events
            else:
                f_events_filtered = f_events
        else:
            f_events_filtered = f_events

        completed = f_events_filtered.dropna(subset=["intHomeScore", "intAwayScore"]).copy()
        if completed.empty:
            st.info("No completed matches yet (scores pending).")
            # Show upcoming
            upcoming = f_events[f_events["intHomeScore"].isna()].copy()
            if not upcoming.empty:
                st.subheader("Upcoming Matches")
                upcoming_disp = upcoming[["dateEvent", "strHomeTeam", "strAwayTeam", "league"]].copy()
                upcoming_disp.columns = ["Date", "Home", "Away", "League"]
                st.dataframe(upcoming_disp.sort_values("Date"), use_container_width=True, hide_index=True)
        else:
            completed["intHomeScore"] = completed["intHomeScore"].astype(int)
            completed["intAwayScore"] = completed["intAwayScore"].astype(int)
            completed["total_goals"] = completed["intHomeScore"] + completed["intAwayScore"]
            completed["result"] = np.where(
                completed["intHomeScore"] > completed["intAwayScore"], "Home Win",
                np.where(completed["intHomeScore"] < completed["intAwayScore"], "Away Win", "Draw")
            )

            st.subheader(f"Completed Matches ({len(completed)})")
            match_cols = ["dateEvent", "strHomeTeam", "intHomeScore", "intAwayScore", "strAwayTeam"]
            if "league" in completed.columns:
                match_cols.append("league")
            if "intRound" in completed.columns:
                match_cols.append("intRound")
            match_display = completed[match_cols].copy()
            rename_map = {"dateEvent": "Date", "strHomeTeam": "Home", "intHomeScore": "HG",
                         "intAwayScore": "AG", "strAwayTeam": "Away", "league": "League", "intRound": "Rd"}
            match_display.rename(columns=rename_map, inplace=True)
            st.dataframe(match_display.sort_values("Date", ascending=False),
                        use_container_width=True, hide_index=True)

            # Stats
            col1, col2 = st.columns(2)
            with col1:
                result_counts = completed["result"].value_counts().reset_index()
                result_counts.columns = ["Result", "Count"]
                fig_res = px.pie(
                    result_counts, names="Result", values="Count",
                    title="Outcome Distribution",
                    color="Result",
                    color_discrete_map={"Home Win": "#2ca02c", "Away Win": "#d62728", "Draw": "#ff7f0e"},
                    hole=0.4,
                )
                fig_res.update_layout(template="plotly_white", height=350)
                st.plotly_chart(fig_res, use_container_width=True)

            with col2:
                fig_goals = px.histogram(
                    completed, x="total_goals", nbins=10,
                    title="Goals per Match Distribution",
                    labels={"total_goals": "Total Goals"},
                    color_discrete_sequence=["#1f77b4"],
                )
                avg_g = completed["total_goals"].mean()
                fig_goals.add_vline(x=avg_g, line_dash="dash", line_color="red",
                                    annotation_text=f"Avg: {avg_g:.2f}")
                fig_goals.update_layout(template="plotly_white", height=350)
                st.plotly_chart(fig_goals, use_container_width=True)

            # Home vs Away
            col_h, col_d, col_a = st.columns(3)
            col_h.metric("Home Win %", f"{(completed['result'] == 'Home Win').mean()*100:.1f}%")
            col_d.metric("Draw %", f"{(completed['result'] == 'Draw').mean()*100:.1f}%")
            col_a.metric("Away Win %", f"{(completed['result'] == 'Away Win').mean()*100:.1f}%")

            # By league breakdown
            if "league" in completed.columns and completed["league"].nunique() > 1:
                st.subheader("Goals per Match by League")
                league_goals = completed.groupby("league")["total_goals"].mean().sort_values(ascending=True).reset_index()
                league_goals.columns = ["League", "Avg Goals/Match"]
                fig_lg = px.bar(league_goals, x="Avg Goals/Match", y="League", orientation="h",
                                color="Avg Goals/Match", color_continuous_scale="YlOrRd",
                                text="Avg Goals/Match")
                fig_lg.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig_lg.update_layout(template="plotly_white", height=400, showlegend=False)
                st.plotly_chart(fig_lg, use_container_width=True)


# =========================================================================
# PAGE: Championship Probability
# =========================================================================
elif page == "🎯 Championship Probability":
    st.title("🎯 Championship Probability — Monte Carlo Simulation")

    if f_standings.empty:
        st.warning("No standings data.")
    else:
        # Let user pick ONE league
        league_options = sorted(f_standings["league"].unique())
        sim_league = st.selectbox("Select League for Simulation", league_options)
        standings = f_standings[f_standings["league"] == sim_league].copy().sort_values("intRank")

        # Show format info
        fmt = LEAGUE_FORMAT.get(sim_league)
        if fmt:
            st.info(f"**{sim_league} Format:** {fmt['description']}")

        if len(standings) < 2:
            st.warning("Need at least 2 teams for simulation.")
        else:
            n_simulations = st.slider("Simulations", 1000, 50000, 10000, 1000)
            remaining_matches = st.slider("Remaining Matches per Team", 0, 30, 10, 1)
            if fmt and fmt.get("halve_points"):
                halve_points = st.checkbox(
                    "Halve points for playoff phase (as per league rules)", value=True
                )
            elif fmt and fmt["type"] in ("playoff_playout", "split", "belgian", "liga2_ro"):
                halve_points = st.checkbox("Halve points for playoff phase", value=False)
            else:
                halve_points = False

            standings["win_rate"] = standings["intWin"] / standings["intPlayed"].clip(lower=1)
            standings["draw_rate"] = standings["intDraw"] / standings["intPlayed"].clip(lower=1)

            np.random.seed(42)
            team_names = standings["strTeam"].values
            current_points = standings["intPoints"].values.astype(float)
            if halve_points:
                current_points = np.ceil(current_points / 2)
            n_teams = len(team_names)

            finish_counts = np.zeros((n_teams, n_teams))

            for _ in range(n_simulations):
                sim_points = current_points.copy()
                for i in range(n_teams):
                    wr = standings.iloc[i]["win_rate"]
                    dr = standings.iloc[i]["draw_rate"]
                    results = np.random.random(remaining_matches)
                    sim_points[i] += np.sum(results < wr) * 3 + np.sum((results >= wr) & (results < wr + dr))
                order = np.argsort(-sim_points)
                for pos, idx in enumerate(order):
                    finish_counts[idx][pos] += 1

            # Results
            champ_pct = finish_counts[:, 0] / n_simulations * 100
            n_po = fmt.get("playoff_teams", fmt.get("split_at", 3)) if fmt else 3
            playoff_pct = finish_counts[:, :min(n_po, n_teams)].sum(axis=1) / n_simulations * 100
            n_rel = fmt.get("relegation", 3) if fmt else min(3, n_teams)
            rel_pct = finish_counts[:, -n_rel:].sum(axis=1) / n_simulations * 100 if n_teams > n_rel else np.zeros(n_teams)

            has_split = fmt and fmt["type"] in ("playoff_playout", "split", "belgian", "liga2_ro")
            po_label = "Playoff %" if has_split else "Top 3 %"
            rel_label = "Relegation %"

            results_df = pd.DataFrame({
                "Team": team_names,
                "Current Pts": current_points.astype(int),
                "Champion %": champ_pct.round(1),
                po_label: playoff_pct.round(1),
                rel_label: rel_pct.round(1),
            }).sort_values("Champion %", ascending=False)

            # Championship bar
            fig_champ = px.bar(
                results_df.sort_values("Champion %", ascending=True),
                x="Champion %", y="Team", orientation="h",
                title=f"{sim_league} — Championship Probability ({n_simulations:,} sims, {remaining_matches} remaining)",
                color="Champion %", color_continuous_scale="YlOrRd",
                text="Champion %",
            )
            fig_champ.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_champ.update_layout(template="plotly_white", height=max(300, n_teams * 40), showlegend=False)
            st.plotly_chart(fig_champ, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                fig_t3 = px.bar(
                    results_df.sort_values(po_label, ascending=True),
                    x=po_label, y="Team", orientation="h",
                    title=f"{po_label.replace(' %','')} Probability",
                    color=po_label, color_continuous_scale="Greens", text=po_label,
                )
                fig_t3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig_t3.update_layout(template="plotly_white", height=max(300, n_teams * 35), showlegend=False)
                st.plotly_chart(fig_t3, use_container_width=True)
            with col2:
                if (results_df[rel_label] > 0).any():
                    fig_rel = px.bar(
                        results_df[results_df[rel_label] > 0].sort_values(rel_label, ascending=True),
                        x=rel_label, y="Team", orientation="h",
                        title="Relegation Probability",
                        color=rel_label, color_continuous_scale="Reds", text=rel_label,
                    )
                    fig_rel.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                    fig_rel.update_layout(template="plotly_white", height=max(300, n_teams * 35), showlegend=False)
                    st.plotly_chart(fig_rel, use_container_width=True)

            # Heatmap
            st.subheader("Position Probability Matrix")
            heatmap_data = finish_counts / n_simulations * 100
            fig_hm = px.imshow(
                heatmap_data,
                x=[f"#{i+1}" for i in range(n_teams)],
                y=team_names.tolist(),
                color_continuous_scale="YlOrRd",
                labels={"color": "Probability %"},
                text_auto=".1f", aspect="auto",
                title="Finish Position Heatmap",
            )
            fig_hm.update_layout(template="plotly_white", height=max(300, n_teams * 40))
            st.plotly_chart(fig_hm, use_container_width=True)

            st.dataframe(results_df, use_container_width=True, hide_index=True)


# =========================================================================
# PAGE: European Comparison
# =========================================================================
elif page == "🌍 European Comparison":
    st.title("🌍 European League Comparison — 2025-2026")

    if all_standings.empty:
        st.warning("No standings data.")
    else:
        league_metrics = []
        for league_name in all_standings["league"].unique():
            ldf = all_standings[all_standings["league"] == league_name]
            if ldf.empty or "intGoalsFor" not in ldf.columns:
                continue
            league_metrics.append({
                "League": league_name,
                "Teams": len(ldf),
                "Avg Points": ldf["intPoints"].mean(),
                "Max Points": ldf["intPoints"].max(),
                "Avg GF": ldf["intGoalsFor"].mean(),
                "Avg GA": ldf["intGoalsAgainst"].mean(),
                "Points Spread": ldf["intPoints"].max() - ldf["intPoints"].min(),
                "Leader": ldf.sort_values("intRank").iloc[0]["strTeam"],
            })
        metrics_df = pd.DataFrame(league_metrics)

        if metrics_df.empty:
            st.info("Not enough data for comparison.")
        else:
            # Competitiveness
            fig_comp = px.bar(
                metrics_df.sort_values("Points Spread"),
                x="Points Spread", y="League", orientation="h",
                title="Competitiveness (Lower Spread = More Competitive)",
                color="Points Spread", color_continuous_scale="RdYlGn_r",
                text="Points Spread",
            )
            fig_comp.update_traces(texttemplate="%{text:.0f}", textposition="outside")
            fig_comp.update_layout(template="plotly_white", height=450, showlegend=False)
            st.plotly_chart(fig_comp, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                fig_gf = px.bar(
                    metrics_df.sort_values("Avg GF", ascending=True),
                    x="Avg GF", y="League", orientation="h",
                    title="Avg Goals Scored per Team",
                    color="Avg GF", color_continuous_scale="Blues", text="Avg GF",
                )
                fig_gf.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                fig_gf.update_layout(template="plotly_white", height=400, showlegend=False)
                st.plotly_chart(fig_gf, use_container_width=True)
            with col2:
                fig_pts = px.bar(
                    metrics_df.sort_values("Avg Points", ascending=True),
                    x="Avg Points", y="League", orientation="h",
                    title="Avg Points per Team",
                    color="Avg Points", color_continuous_scale="Oranges", text="Avg Points",
                )
                fig_pts.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                fig_pts.update_layout(template="plotly_white", height=400, showlegend=False)
                st.plotly_chart(fig_pts, use_container_width=True)

            # Leaders table
            st.subheader("League Leaders")
            st.dataframe(
                metrics_df[["League", "Leader", "Max Points", "Teams"]].sort_values("Max Points", ascending=False),
                use_container_width=True, hide_index=True,
            )

            # Radar comparison
            st.subheader("League Radar Comparison")
            sel_leagues = st.multiselect(
                "Compare leagues", metrics_df["League"].tolist(),
                default=metrics_df["League"].tolist()[:4],
            )
            if sel_leagues:
                radar_df = metrics_df[metrics_df["League"].isin(sel_leagues)]
                cats = ["Avg Points", "Avg GF", "Avg GA", "Points Spread"]
                fig_radar = go.Figure()
                for _, row in radar_df.iterrows():
                    vals = [row[c] for c in cats]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=cats + [cats[0]],
                        name=row["League"], fill="toself", opacity=0.5,
                    ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    template="plotly_white", height=500,
                )
                st.plotly_chart(fig_radar, use_container_width=True)


# =========================================================================
# PAGE: Player Analysis
# =========================================================================
elif page == "👤 Player Analysis":
    st.title("👤 Player Analysis — 2025-2026")

    if f_players.empty:
        if all_players.empty:
            st.warning("Player data not available yet. Run `fetch_teams_players.py` to download.")
        else:
            st.info("No players match your current filters. Try adjusting league/team selection.")
    else:
        st.markdown(f"**{len(f_players)} players** matching current filters")

        # Position distribution
        col1, col2 = st.columns(2)
        if "strPosition" in f_players.columns:
            with col1:
                pos_counts = f_players["strPosition"].value_counts().reset_index()
                pos_counts.columns = ["Position", "Count"]
                fig_pos = px.pie(pos_counts, names="Position", values="Count",
                                 title="Position Distribution", hole=0.4)
                fig_pos.update_layout(template="plotly_white", height=400)
                st.plotly_chart(fig_pos, use_container_width=True)

        if "strNationality" in f_players.columns:
            with col2:
                nat_counts = f_players["strNationality"].value_counts().head(20).reset_index()
                nat_counts.columns = ["Nationality", "Count"]
                fig_nat = px.bar(nat_counts, x="Count", y="Nationality", orientation="h",
                                 title="Top 20 Nationalities",
                                 color="Count", color_continuous_scale="Blues")
                fig_nat.update_layout(template="plotly_white", height=400, showlegend=False)
                st.plotly_chart(fig_nat, use_container_width=True)

        # Age distribution
        if "age" in f_players.columns:
            valid_ages = f_players[f_players["age"].between(15, 50)]
            if not valid_ages.empty:
                fig_age = px.histogram(valid_ages, x="age", nbins=25,
                                       title="Age Distribution", color_discrete_sequence=["#1f77b4"])
                avg_age = valid_ages["age"].mean()
                fig_age.add_vline(x=avg_age, line_dash="dash", line_color="red",
                                  annotation_text=f"Avg: {avg_age:.1f}")
                fig_age.update_layout(template="plotly_white", height=400)
                st.plotly_chart(fig_age, use_container_width=True)

                # Age by league
                if "league" in valid_ages.columns and valid_ages["league"].nunique() > 1:
                    age_by_league = valid_ages.groupby("league")["age"].mean().sort_values().reset_index()
                    age_by_league.columns = ["League", "Avg Age"]
                    fig_al = px.bar(age_by_league, x="Avg Age", y="League", orientation="h",
                                    title="Average Player Age by League",
                                    color="Avg Age", color_continuous_scale="RdYlGn_r",
                                    text="Avg Age")
                    fig_al.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                    fig_al.update_layout(template="plotly_white", height=400, showlegend=False)
                    st.plotly_chart(fig_al, use_container_width=True)

        # Player table with search
        st.subheader("Player Database")
        display_cols = ["strPlayer", "strPosition", "strNationality", "_teamName", "league",
                        "age", "strHeight", "strWeight", "strNumber"]
        display_cols = [c for c in display_cols if c in f_players.columns]
        rename = {"strPlayer": "Player", "strPosition": "Position", "strNationality": "Nationality",
                  "_teamName": "Team", "league": "League", "age": "Age",
                  "strHeight": "Height", "strWeight": "Weight", "strNumber": "#"}
        show_df = f_players[display_cols].rename(columns=rename)
        st.dataframe(show_df, use_container_width=True, hide_index=True, height=500)

    # Team-level attack vs defense
    st.subheader("Team Attack vs Defense")
    if not f_standings.empty:
        st_data = f_standings.copy()
        st_data["gf_pm"] = st_data["intGoalsFor"] / st_data["intPlayed"].clip(lower=1)
        st_data["ga_pm"] = st_data["intGoalsAgainst"] / st_data["intPlayed"].clip(lower=1)
        fig_scatter = px.scatter(
            st_data, x="gf_pm", y="ga_pm",
            size="intPoints", color="league",
            hover_name="strTeam", text="strTeam",
            title="Goals Scored vs Conceded per Match (bubble = points)",
            labels={"gf_pm": "Goals Scored / Match", "ga_pm": "Goals Conceded / Match"},
            size_max=30,
        )
        fig_scatter.update_traces(textposition="top center", textfont_size=7)
        fig_scatter.add_hline(y=st_data["ga_pm"].median(), line_dash="dash", line_color="gray", opacity=0.4)
        fig_scatter.add_vline(x=st_data["gf_pm"].median(), line_dash="dash", line_color="gray", opacity=0.4)
        fig_scatter.update_layout(template="plotly_white", height=600,
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_scatter, use_container_width=True)


# =========================================================================
# PAGE: Transfer Recommendations
# =========================================================================
elif page == "💰 Transfer Recommendations":
    st.title("💰 Transfer Recommendation Engine")

    if f_standings.empty:
        st.warning("No standings data.")
    else:
        # ── Helper: Parse monetary values from strSigning / strWage strings ──
        import re as _re

        def _parse_money_eur(raw):
            """Parse a money string like '£25.20m', '€88.5M', '50,00 Mill. €' → float in €M."""
            if not raw or not isinstance(raw, str):
                return None
            s = raw.strip()
            if s.lower() in ("youth", "free", "on loan", "loan", ""):
                return None
            # Normalize encoding artefacts (Â£ → £, â‚¬ → €)
            s = s.replace("\u00c2\u00a3", "£").replace("\u00c2", "").replace("\u00a3", "£")
            s = s.replace("\u00e2\u0082\u00ac", "€").replace("â‚¬", "€")
            gbp_to_eur = 1.17
            # Pattern: number with optional decimals + optional M/m/Mill suffix
            m = _re.search(r"([\d.,]+)\s*(m(?:ill)?\.?|k)?", s, _re.IGNORECASE)
            if not m:
                return None
            num_str = m.group(1).replace(",", ".")
            # Handle European notation like "50.00" that's already millions
            try:
                val = float(num_str)
            except ValueError:
                return None
            suffix = (m.group(2) or "").lower()
            if suffix.startswith("k"):
                val /= 1000.0
            elif not suffix and val > 500:
                val /= 1_000_000.0  # raw number like 6240000
            # All values should be in millions at this point
            if "£" in s:
                val *= gbp_to_eur
            return round(val, 2) if val > 0 else None

        # ── League market value benchmarks (€M, approximate average squad value) ──
        LEAGUE_MARKET = {
            "English Premier League": 500, "La Liga": 350, "Serie A": 280,
            "Bundesliga": 280, "Ligue 1": 200, "Eredivisie": 60,
            "Primeira Liga": 70, "Turkish Super Lig": 40, "Belgian Pro League": 30,
            "Scottish Premiership": 15, "Greek Super League": 20,
            "Danish Superliga": 15, "Russian Premier League": 30,
            "Romanian Liga I": 8, "Romanian Liga II": 2,
        }

        # ── Position grouping helper ──
        POS_GROUPS = {
            "GK": ["Goalkeeper"],
            "DEF": ["Defender", "Centre-Back", "Left-Back", "Right-Back", "Wing-Back"],
            "MID": ["Midfielder", "Central Midfield", "Defensive Midfield",
                     "Attacking Midfield", "Left Midfield", "Right Midfield"],
            "ATT": ["Forward", "Attacker", "Striker", "Centre-Forward",
                     "Left Winger", "Right Winger", "Left Wing", "Right Wing", "Second Striker"],
        }
        _pos_lookup = {}
        for grp, positions in POS_GROUPS.items():
            for p in positions:
                _pos_lookup[p.lower()] = grp

        def _pos_group(pos_str):
            if not pos_str or not isinstance(pos_str, str):
                return None
            return _pos_lookup.get(pos_str.strip().lower())

        # ── Estimate market value for a player based on age, position, league ──
        def _estimate_value(row, league_mkt):
            """Market value in €M — uses Transfermarkt value if available, else heuristic."""
            # Prefer real Transfermarkt market value
            tm_val = row.get("market_value_eur_m")
            if tm_val is not None and not pd.isna(tm_val) and float(tm_val) > 0:
                return round(float(tm_val), 2)
            # Fallback: heuristic based on signing fee, age, position, league
            parsed = _parse_money_eur(row.get("strSigning"))
            age = row.get("age", 27)
            if pd.isna(age):
                age = 27
            grp = _pos_group(row.get("strPosition", ""))
            if age < 21:
                age_mult = 0.6
            elif age < 24:
                age_mult = 1.1
            elif age <= 28:
                age_mult = 1.0
            elif age <= 30:
                age_mult = 0.7
            elif age <= 33:
                age_mult = 0.4
            else:
                age_mult = 0.15
            pos_mult = {"ATT": 1.3, "MID": 1.0, "DEF": 0.85, "GK": 0.6}.get(grp, 0.8)
            if parsed and parsed > 0.01:
                return round(parsed * age_mult, 2)
            base = league_mkt * 0.004
            return round(base * age_mult * pos_mult, 2)

        # ── Prepare player data with estimated values ──
        has_players = not all_players.empty and "league" in all_players.columns
        if has_players:
            _ap = all_players.copy()
            # Filter out coaches, managers, inactive
            _ap = _ap[~_ap["strPosition"].str.contains("Coach|Manager|Director|Physio|Analyst|Scout", case=False, na=True)]
            _ap["pos_group"] = _ap["strPosition"].apply(_pos_group)
            _ap = _ap[_ap["pos_group"].notna()].copy()
            _ap["est_value"] = _ap.apply(
                lambda r: _estimate_value(r, LEAGUE_MARKET.get(r.get("league", ""), 20)), axis=1
            )
            _ap["wage_eur"] = _ap["strWage"].apply(_parse_money_eur)
        else:
            _ap = pd.DataFrame()

        # ── Fuzzy team name matching ──
        import re as _re
        _STRIP_PREFIXES = _re.compile(r'^(FC|AFC|SC|CS|CSC|CSM|ACS|ACSM|ACSC|ASC|FK|SK|KV|KRC|KAA|RSC|SV|TSV|VfB|VfL|1\.\s*)\s+', _re.IGNORECASE)
        _STRIP_SUFFIXES = _re.compile(r'\s+(FC|FK|SK|SC|CF|1923|1948|1947|2022|1902|04)\s*$', _re.IGNORECASE)

        def _normalize_team(name):
            if not name:
                return ""
            n = name.strip()
            n = _STRIP_PREFIXES.sub("", n)
            n = _STRIP_SUFFIXES.sub("", n)
            return n.lower().strip()

        def _find_squad(team_name, player_df, league_filter=None):
            """Find squad for a team using exact then fuzzy matching."""
            if player_df.empty:
                return pd.DataFrame()
            df = player_df
            if league_filter and "league" in df.columns:
                df = df[df["league"] == league_filter]
            # Exact match
            for col in ["_teamName", "strTeam"]:
                if col in df.columns:
                    match = df[df[col] == team_name]
                    if not match.empty:
                        return match.copy()
            # Normalized match
            norm = _normalize_team(team_name)
            for col in ["_teamName", "strTeam"]:
                if col in df.columns:
                    df_norm = df[col].apply(_normalize_team)
                    match = df[df_norm == norm]
                    if not match.empty:
                        return match.copy()
            # Substring match
            for col in ["_teamName", "strTeam"]:
                if col in df.columns:
                    df_norm = df[col].apply(_normalize_team)
                    match = df[df_norm.str.contains(norm, na=False) | pd.Series([norm in x for x in df_norm], index=df.index)]
                    if not match.empty:
                        return match.copy()
                    # Reverse: check if player team contains standings team
                    match = df[pd.Series([x in norm for x in df_norm], index=df.index)]
                    if not match.empty:
                        return match.copy()
            return pd.DataFrame()

        # ======================================================================
        # TAB LAYOUT
        # ======================================================================
        tr_tab1, tr_tab2, tr_tab3, tr_tab4 = st.tabs([
            "🔍 Club Squad Audit",
            "🎯 Transfer Needs & Targets",
            "💸 Players to Sell",
            "🌍 Cross-League Scout",
        ])

        # ══════════════════════════════════════════════════════════════════════
        # TAB 1 — CLUB SQUAD AUDIT
        # ══════════════════════════════════════════════════════════════════════
        with tr_tab1:
            st.subheader("🔍 Club Squad Audit")
            tr_league = st.selectbox("League", sorted(f_standings["league"].unique()), key="audit_league")
            league_st = f_standings[f_standings["league"] == tr_league].sort_values("intRank")
            selected_team = st.selectbox("Team", league_st["strTeam"].tolist(), key="audit_team")
            team_row = league_st[league_st["strTeam"] == selected_team].iloc[0]

            # Team performance metrics
            t_played = max(int(team_row["intPlayed"]), 1)
            t_ppg = team_row["intPoints"] / t_played
            t_gf = team_row["intGoalsFor"] / t_played
            t_ga = team_row["intGoalsAgainst"] / t_played
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Rank", f"#{int(team_row['intRank'])}")
            m2.metric("Points", int(team_row["intPoints"]))
            m3.metric("PPG", f"{t_ppg:.2f}")
            m4.metric("Goals/Match", f"{t_gf:.2f}")
            m5.metric("Conceded/Match", f"{t_ga:.2f}")

            # Squad roster from player data
            squad = _find_squad(selected_team, _ap, tr_league)

            league_mkt = LEAGUE_MARKET.get(tr_league, 20)

            if squad.empty:
                st.info(f"No player data available for {selected_team}. Showing team-level analysis only.")
            else:
                total_est_value = squad["est_value"].sum()
                avg_age = squad["age"].mean()
                st.markdown(f"**Squad size:** {len(squad)} players · **Est. squad value:** €{total_est_value:.1f}M · **Average age:** {avg_age:.1f}")

                # ── Position breakdown ──
                scol1, scol2 = st.columns(2)
                with scol1:
                    pos_counts = squad.groupby("pos_group").agg(
                        Count=("strPlayer", "count"),
                        Avg_Age=("age", "mean"),
                        Total_Value=("est_value", "sum"),
                    ).reindex(["GK", "DEF", "MID", "ATT"]).fillna(0)
                    pos_counts["Avg_Age"] = pos_counts["Avg_Age"].round(1)
                    pos_counts["Total_Value"] = pos_counts["Total_Value"].round(1)
                    pos_counts.columns = ["Players", "Avg Age", "Value (€M)"]
                    st.markdown("**Position Breakdown**")
                    st.dataframe(pos_counts, use_container_width=True)

                with scol2:
                    fig_pos = px.pie(
                        names=["GK", "DEF", "MID", "ATT"],
                        values=[pos_counts.loc[g, "Players"] if g in pos_counts.index else 0 for g in ["GK", "DEF", "MID", "ATT"]],
                        title="Squad Composition",
                        color_discrete_sequence=["#636EFA", "#00CC96", "#EF553B", "#FFA15A"],
                    )
                    fig_pos.update_layout(height=300, margin=dict(t=40, b=10))
                    st.plotly_chart(fig_pos, use_container_width=True)

                # ── Age profile ──
                st.markdown("**Age Profile**")
                squad["age_bucket"] = pd.cut(
                    squad["age"], bins=[15, 21, 24, 28, 31, 40],
                    labels=["U21 (Prospect)", "21-24 (Developing)", "25-28 (Peak)", "29-31 (Experienced)", "32+ (Veteran)"],
                )
                age_dist = squad["age_bucket"].value_counts().reindex(
                    ["U21 (Prospect)", "21-24 (Developing)", "25-28 (Peak)", "29-31 (Experienced)", "32+ (Veteran)"]
                ).fillna(0)
                fig_age = px.bar(
                    x=age_dist.index, y=age_dist.values,
                    color=age_dist.index,
                    color_discrete_map={
                        "U21 (Prospect)": "#AB63FA", "21-24 (Developing)": "#19D3F3",
                        "25-28 (Peak)": "#00CC96", "29-31 (Experienced)": "#FFA15A", "32+ (Veteran)": "#EF553B",
                    },
                    title="Age Distribution", labels={"x": "", "y": "Players"},
                )
                fig_age.update_layout(template="plotly_white", height=300, showlegend=False)
                st.plotly_chart(fig_age, use_container_width=True)

                # ── Full squad table ──
                with st.expander("📋 Full Squad List", expanded=False):
                    show_cols = ["strNumber", "strPlayer", "strPosition", "pos_group", "age", "strNationality", "strFoot", "strContract", "est_value"]
                    show_cols = [c for c in show_cols if c in squad.columns]
                    disp = squad[show_cols].sort_values(["pos_group", "est_value"], ascending=[True, False])
                    _col_map = {"strNumber": "#", "strPlayer": "Player", "strPosition": "Position",
                                "pos_group": "Group", "age": "Age", "strNationality": "Nationality",
                                "strFoot": "Foot", "strContract": "Contract", "est_value": "Value (€M)"}
                    disp.columns = [_col_map.get(c, c) for c in disp.columns]
                    st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

        # ══════════════════════════════════════════════════════════════════════
        # TAB 2 — TRANSFER NEEDS & TARGETS
        # ══════════════════════════════════════════════════════════════════════
        with tr_tab2:
            st.subheader("🎯 Transfer Needs & Recommended Targets")
            tr2_league = st.selectbox("League", sorted(f_standings["league"].unique()), key="needs_league")
            league_st2 = f_standings[f_standings["league"] == tr2_league].sort_values("intRank")
            sel_team2 = st.selectbox("Team", league_st2["strTeam"].tolist(), key="needs_team")
            team2 = league_st2[league_st2["strTeam"] == sel_team2].iloc[0]
            league_mkt2 = LEAGUE_MARKET.get(tr2_league, 20)

            # Budget input
            max_budget = float(max(league_mkt2 * 5, 1.0))
            default_budget = float(min(max_budget * 0.15, 10.0))
            budget = st.slider("💶 Transfer Budget (€M)", 0.5, max_budget, default_budget, 0.5, key="needs_budget")

            # Performance gaps
            league_st2["gf_pm"] = league_st2["intGoalsFor"] / league_st2["intPlayed"].clip(lower=1)
            league_st2["ga_pm"] = league_st2["intGoalsAgainst"] / league_st2["intPlayed"].clip(lower=1)
            t2_gf = team2["intGoalsFor"] / max(team2["intPlayed"], 1)
            t2_ga = team2["intGoalsAgainst"] / max(team2["intPlayed"], 1)
            top3 = league_st2.head(3)
            top3_gf = top3["gf_pm"].mean()
            top3_ga = top3["ga_pm"].mean()
            avg_gf = league_st2["gf_pm"].mean()
            avg_ga = league_st2["ga_pm"].mean()
            atk_gap = t2_gf - top3_gf
            def_gap = top3_ga - t2_ga  # positive = team concedes MORE than top3

            # Squad analysis
            squad2 = _find_squad(sel_team2, _ap, tr2_league)

            # ── Identify needs ──
            needs = []
            # 1. Performance-based needs
            if atk_gap < -0.3:
                needs.append({"Position": "Striker / Forward", "Priority": "🔴 HIGH",
                              "Reason": f"Scoring {abs(atk_gap):.2f} fewer goals/match than top 3",
                              "pos_targets": ["ATT"]})
            elif atk_gap < -0.1:
                needs.append({"Position": "Winger / Attacking Mid", "Priority": "🟡 MEDIUM",
                              "Reason": f"Attack gap of {abs(atk_gap):.2f} vs top 3",
                              "pos_targets": ["ATT", "MID"]})
            if def_gap < -0.3:
                needs.append({"Position": "Centre-Back / Def. Mid", "Priority": "🔴 HIGH",
                              "Reason": f"Conceding {abs(def_gap):.2f} more goals/match than top 3",
                              "pos_targets": ["DEF"]})
            elif def_gap < -0.1:
                needs.append({"Position": "Full-Back / Defensive Mid", "Priority": "🟡 MEDIUM",
                              "Reason": f"Defensive gap of {abs(def_gap):.2f} vs top 3",
                              "pos_targets": ["DEF", "MID"]})

            # 2. Squad composition needs (if player data available)
            ideal_comp = {"GK": (2, 3), "DEF": (6, 9), "MID": (6, 9), "ATT": (4, 7)}
            if not squad2.empty:
                for grp, (lo, hi) in ideal_comp.items():
                    cnt = len(squad2[squad2["pos_group"] == grp])
                    grp_age = squad2[squad2["pos_group"] == grp]["age"].mean() if cnt > 0 else 0
                    if cnt < lo:
                        label = {"GK": "Goalkeeper", "DEF": "Centre-Back / Full-Back",
                                 "MID": "Midfielder", "ATT": "Forward / Winger"}[grp]
                        needs.append({"Position": label, "Priority": "🔴 HIGH",
                                      "Reason": f"Only {cnt} {grp}s in squad (need {lo}-{hi})",
                                      "pos_targets": [grp]})
                    elif cnt > 0 and grp_age > 30:
                        label = {"GK": "Young Goalkeeper", "DEF": "Young Defender",
                                 "MID": "Young Midfielder", "ATT": "Young Attacker"}[grp]
                        needs.append({"Position": label, "Priority": "🟡 MEDIUM",
                                      "Reason": f"{grp} avg age {grp_age:.1f} — need younger options",
                                      "pos_targets": [grp]})

            if not needs:
                needs.append({"Position": "Squad Depth (any)", "Priority": "🟢 LOW",
                              "Reason": "Team performing well. Consider depth signings.",
                              "pos_targets": ["ATT", "MID", "DEF"]})

            # Display needs
            needs_df = pd.DataFrame(needs)[["Priority", "Position", "Reason"]]
            st.dataframe(needs_df, use_container_width=True, hide_index=True)

            # ── Find transfer targets from the database ──
            st.markdown("---")
            st.subheader("🛒 Recommended Transfer Targets")
            st.caption(f"Budget: **€{budget:.1f}M** · Searching players from other teams within financial reach")

            if _ap.empty:
                st.info("No player database available for target recommendations.")
            else:
                # Target leagues: same league + leagues at similar or lower market level
                target_leagues = []
                for lg, val in LEAGUE_MARKET.items():
                    if val <= league_mkt2 * 1.2:
                        target_leagues.append(lg)
                if tr2_league not in target_leagues:
                    target_leagues.append(tr2_league)

                all_targets = []
                for need in needs:
                    pos_grps = need.get("pos_targets", [])
                    cands = _ap[
                        (_ap["pos_group"].isin(pos_grps)) &
                        (_ap["league"].isin(target_leagues)) &
                        (_ap["est_value"] <= budget) &
                        (_ap["est_value"] > 0.01)
                    ].copy()
                    # Exclude own team
                    cands = cands[(cands["_teamName"] != sel_team2) & (cands["strTeam"] != sel_team2)]
                    # Prefer age 21-29 (prime)
                    if "age" in cands.columns:
                        cands["_prime"] = cands["age"].between(21, 29).astype(int)
                    else:
                        cands["_prime"] = 0
                    # Rank: from higher-ranked teams + prime age + higher value = better
                    cands = cands.sort_values(["_prime", "est_value"], ascending=[False, False])
                    top_cands = cands.head(5)
                    for _, c in top_cands.iterrows():
                        all_targets.append({
                            "Need": need["Position"],
                            "Player": c.get("strPlayer", "?"),
                            "Position": c.get("strPosition", "?"),
                            "Age": c.get("age", "?"),
                            "Club": c.get("_teamName", c.get("strTeam", "?")),
                            "League": c.get("league", "?"),
                            "Value (€M)": c.get("est_value", 0),
                            "Nationality": c.get("strNationality", ""),
                        })

                if all_targets:
                    tgt_df = pd.DataFrame(all_targets)
                    st.dataframe(tgt_df, use_container_width=True, hide_index=True, height=min(len(tgt_df) * 38 + 40, 600))
                    # Visual: value vs age scatter
                    fig_tgt = px.scatter(
                        tgt_df, x="Age", y="Value (€M)",
                        color="Need", hover_name="Player",
                        hover_data=["Club", "League", "Position"],
                        size="Value (€M)", size_max=20,
                        title=f"Transfer Targets for {sel_team2} (Budget: €{budget:.1f}M)",
                    )
                    fig_tgt.update_layout(template="plotly_white", height=400)
                    st.plotly_chart(fig_tgt, use_container_width=True)
                else:
                    st.info("No matching targets found within the budget.")

                # ── Budget allocation suggestion ──
                st.markdown("---")
                st.subheader("💶 Budget Allocation Plan")
                n_needs = len(needs)
                alloc_rows = []
                remaining = budget
                for i, need in enumerate(needs):
                    if need["Priority"].startswith("🔴"):
                        share = 0.45  # High priority gets 45%
                    elif need["Priority"].startswith("🟡"):
                        share = 0.30
                    else:
                        share = 0.25
                    amount = round(budget * share, 1)
                    if i == len(needs) - 1:
                        amount = round(remaining, 1)
                    remaining -= amount
                    alloc_rows.append({
                        "Priority": need["Priority"],
                        "Position": need["Position"],
                        "Allocated (€M)": amount,
                    })
                alloc_df = pd.DataFrame(alloc_rows)
                st.dataframe(alloc_df, use_container_width=True, hide_index=True)

                fig_alloc = px.pie(
                    alloc_df, values="Allocated (€M)", names="Position",
                    title="Budget Allocation", hole=0.4,
                )
                fig_alloc.update_layout(height=350)
                st.plotly_chart(fig_alloc, use_container_width=True)

        # ══════════════════════════════════════════════════════════════════════
        # TAB 3 — PLAYERS TO SELL
        # ══════════════════════════════════════════════════════════════════════
        with tr_tab3:
            st.subheader("💸 Players to Sell / Transfer Out")
            st.caption("Identify players whose sale could fund incoming transfers")
            tr3_league = st.selectbox("League", sorted(f_standings["league"].unique()), key="sell_league")
            league_st3 = f_standings[f_standings["league"] == tr3_league].sort_values("intRank")
            sel_team3 = st.selectbox("Team", league_st3["strTeam"].tolist(), key="sell_team")
            league_mkt3 = LEAGUE_MARKET.get(tr3_league, 20)

            squad3 = _find_squad(sel_team3, _ap, tr3_league)

            if squad3.empty:
                st.info(f"No player data for {sel_team3}.")
            else:
                # Score each player on "sell attractiveness"
                # High sell score = high value + aging + surplus position
                pos_counts3 = squad3["pos_group"].value_counts()
                squad3["_surplus"] = squad3["pos_group"].map(
                    lambda g: 1 if pos_counts3.get(g, 0) > ideal_comp.get(g, (0, 99))[1] else 0
                )
                squad3["_aging"] = (squad3["age"] > 30).astype(int)
                squad3["_high_val"] = (squad3["est_value"] > squad3["est_value"].quantile(0.7)).astype(int)
                squad3["sell_score"] = squad3["_aging"] * 2 + squad3["_surplus"] * 1.5 + squad3["_high_val"] * 1
                # High value + aging + surplus → good sell candidates
                # Also: players with highest value who are 30+ are prime sell candidates
                sell_candidates = squad3.sort_values("sell_score", ascending=False).head(8)

                sell_display = sell_candidates[["strPlayer", "strPosition", "age", "strNationality",
                                                 "pos_group", "est_value", "sell_score"]].copy()
                sell_display.columns = ["Player", "Position", "Age", "Nationality", "Group", "Value (€M)", "Sell Score"]

                sell_reason = []
                for _, r in sell_display.iterrows():
                    reasons = []
                    if r["Age"] and r["Age"] > 30:
                        reasons.append("Aging (30+)")
                    if r["Sell Score"] >= 3:
                        reasons.append("High value + sell opportunity")
                    g = r["Group"]
                    if pos_counts3.get(g, 0) > ideal_comp.get(g, (0, 99))[1]:
                        reasons.append(f"Surplus {g}")
                    if not reasons:
                        reasons.append("Depth player / rotation option")
                    sell_reason.append(", ".join(reasons))
                sell_display["Reason"] = sell_reason
                sell_display = sell_display.drop(columns=["Sell Score", "Group"])

                st.dataframe(sell_display, use_container_width=True, hide_index=True)

                total_sell = sell_display["Value (€M)"].sum()
                st.success(f"**Potential revenue from sales:** €{total_sell:.1f}M")

                # Visual
                fig_sell = px.bar(
                    sell_display.sort_values("Value (€M)", ascending=True),
                    x="Value (€M)", y="Player", orientation="h",
                    color="Age", color_continuous_scale="RdYlGn_r",
                    title=f"Sell Candidates — {sel_team3}",
                    hover_data=["Position", "Reason"],
                )
                fig_sell.update_layout(template="plotly_white", height=max(len(sell_display) * 45, 300), showlegend=False)
                st.plotly_chart(fig_sell, use_container_width=True)

        # ══════════════════════════════════════════════════════════════════════
        # TAB 4 — CROSS-LEAGUE SCOUT
        # ══════════════════════════════════════════════════════════════════════
        with tr_tab4:
            st.subheader("🌍 Cross-League Transfer Scout")
            st.caption("Browse the best value players across all leagues by position and budget")

            if _ap.empty:
                st.info("No player data available for cross-league scouting.")
            else:
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    scout_pos = st.selectbox("Position Group", ["All", "GK", "DEF", "MID", "ATT"], key="scout_pos")
                with sc2:
                    scout_max_age = st.slider("Max Age", 18, 40, 29, key="scout_age")
                with sc3:
                    scout_budget = st.slider("Max Value (€M)", 0.5, 200.0, 20.0, 0.5, key="scout_budget")

                scout_df = _ap.copy()
                if scout_pos != "All":
                    scout_df = scout_df[scout_df["pos_group"] == scout_pos]
                scout_df = scout_df[(scout_df["age"] <= scout_max_age) & (scout_df["est_value"] <= scout_budget)]
                # Value-for-age score: younger + higher value = better prospect
                scout_df["value_score"] = scout_df["est_value"] / (scout_df["age"] - 16).clip(lower=1) * 10
                scout_df = scout_df.sort_values("value_score", ascending=False)

                show_scout = scout_df.head(30)[["strPlayer", "strPosition", "age", "strNationality",
                                                  "_teamName", "league", "est_value"]].copy()
                show_scout.columns = ["Player", "Position", "Age", "Nationality", "Club", "League", "Value (€M)"]
                st.dataframe(show_scout, use_container_width=True, hide_index=True, height=min(len(show_scout) * 38 + 40, 700))

                if len(scout_df) > 0:
                    fig_scout = px.scatter(
                        show_scout, x="Age", y="Value (€M)",
                        color="League", hover_name="Player",
                        hover_data=["Club", "Position", "Nationality"],
                        size="Value (€M)", size_max=25,
                        title=f"Scouting Map — {scout_pos} players under {scout_max_age} (max €{scout_budget:.1f}M)",
                    )
                    fig_scout.update_layout(template="plotly_white", height=500)
                    st.plotly_chart(fig_scout, use_container_width=True)

                    # Best value by league
                    best_by_league = scout_df.sort_values("value_score", ascending=False).groupby("league").first().reset_index()
                    bbl = best_by_league[["league", "strPlayer", "strPosition", "age", "est_value"]].copy()
                    bbl.columns = ["League", "Best Value Player", "Position", "Age", "Value (€M)"]
                    bbl = bbl.sort_values("Value (€M)", ascending=False)
                    st.markdown("**Best Value Player per League**")
                    st.dataframe(bbl, use_container_width=True, hide_index=True)


# =========================================================================
# PAGE: ML Prediction Models
# =========================================================================
elif page == "🤖 ML Prediction Models":
    st.title("🤖 Machine Learning Models")

    if f_standings.empty:
        st.warning("No data for ML models.")
    else:
        # ── 1. Team Clustering ──
        st.subheader("1. Team Clustering (K-Means)")
        features = ["intWin", "intDraw", "intLoss", "intGoalsFor", "intGoalsAgainst", "intPoints"]
        features = [f for f in features if f in f_standings.columns]

        if len(features) >= 3 and len(f_standings) >= 4:
            X = f_standings[features].values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            n_clusters = st.slider("Number of Clusters", 2, min(6, len(f_standings) - 1), 3)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)

            plot_df = f_standings.copy()
            plot_df["Cluster"] = clusters

            # Label clusters by average points
            cluster_order = plot_df.groupby("Cluster")["intPoints"].mean().sort_values(ascending=False)
            tier_names = ["Elite", "Strong", "Mid Table", "Lower", "Bottom", "Relegation"]
            label_map = {c: tier_names[i] for i, c in enumerate(cluster_order.index)}
            plot_df["Tier"] = plot_df["Cluster"].map(label_map)

            fig_cl = px.scatter(
                plot_df, x="intGoalsFor", y="intGoalsAgainst",
                color="Tier", symbol="league" if plot_df["league"].nunique() <= 10 else None,
                hover_name="strTeam", size="intPoints", size_max=25,
                title="Team Clustering — Goals Scored vs Conceded",
                labels={"intGoalsFor": "Goals Scored", "intGoalsAgainst": "Goals Conceded"},
            )
            fig_cl.update_layout(template="plotly_white", height=550)
            st.plotly_chart(fig_cl, use_container_width=True)

            # Cluster summary
            cluster_summary = plot_df.groupby("Tier").agg(
                Teams=("strTeam", "count"),
                Avg_Pts=("intPoints", "mean"),
                Avg_GF=("intGoalsFor", "mean"),
                Avg_GA=("intGoalsAgainst", "mean"),
            ).round(1).sort_values("Avg_Pts", ascending=False)
            st.dataframe(cluster_summary, use_container_width=True)

        # ── 2. Points Predictor ──
        st.subheader("2. Points Prediction (Linear Regression)")
        if len(f_standings) >= 4:
            reg_df = f_standings.copy()
            reg_df["win_pct"] = reg_df["intWin"] / reg_df["intPlayed"].clip(lower=1)
            reg_df["gf_pm"] = reg_df["intGoalsFor"] / reg_df["intPlayed"].clip(lower=1)
            reg_df["ga_pm"] = reg_df["intGoalsAgainst"] / reg_df["intPlayed"].clip(lower=1)

            pred_feats = ["win_pct", "gf_pm", "ga_pm"]
            X = reg_df[pred_feats].values
            y = reg_df["intPoints"].values

            lr = LinearRegression()
            lr.fit(X, y)
            reg_df["predicted_pts"] = lr.predict(X).round(1)

            fig_pred = go.Figure()
            fig_pred.add_trace(go.Bar(
                x=reg_df["strTeam"], y=reg_df["intPoints"], name="Actual", marker_color="#1f77b4",
            ))
            fig_pred.add_trace(go.Scatter(
                x=reg_df["strTeam"], y=reg_df["predicted_pts"], name="Predicted",
                mode="markers+lines", marker=dict(size=8, color="#d62728"),
            ))
            fig_pred.update_layout(title="Actual vs Predicted Points", template="plotly_white",
                                   height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_pred, use_container_width=True)

            st.markdown("**Feature Coefficients:**")
            coef_df = pd.DataFrame({"Feature": pred_feats, "Coefficient": lr.coef_.round(2)})
            st.dataframe(coef_df, use_container_width=True, hide_index=True)

        # ── 3. Match Outcome Predictor ──
        st.subheader("3. Match Outcome Predictor (League-Strength Adjusted)")

        # League strength coefficients (UEFA country coefficient style, approximate)
        LEAGUE_STRENGTH = {
            "English Premier League": 1.00, "La Liga": 0.95, "Serie A": 0.90,
            "Bundesliga": 0.88, "Ligue 1": 0.80, "Eredivisie": 0.65,
            "Primeira Liga": 0.70, "Turkish Super Lig": 0.55, "Belgian Pro League": 0.55,
            "Scottish Premiership": 0.45, "Greek Super League": 0.45,
            "Danish Superliga": 0.40, "Russian Premier League": 0.50,
            "Romanian Liga I": 0.35, "Romanian Liga II": 0.20,
        }

        if not all_standings.empty:
            # Build team list with league info
            team_league_map = {}
            for _, row in all_standings.iterrows():
                team_league_map[row["strTeam"]] = row.get("league", "Unknown")

            all_pred_teams = sorted(team_league_map.keys())
            if len(all_pred_teams) >= 2:
                c1, c2 = st.columns(2)
                with c1:
                    home_t = st.selectbox("Home Team", all_pred_teams, key="ml_home")
                with c2:
                    away_t = st.selectbox("Away Team",
                                          [t for t in all_pred_teams if t != home_t], key="ml_away")

                home_league = team_league_map.get(home_t, "Unknown")
                away_league = team_league_map.get(away_t, "Unknown")

                # Get team stats
                home_row = all_standings[all_standings["strTeam"] == home_t]
                away_row = all_standings[all_standings["strTeam"] == away_t]

                if not home_row.empty and not away_row.empty:
                    hr = home_row.iloc[0]
                    ar = away_row.iloc[0]
                    h_played = max(int(hr["intPlayed"]), 1)
                    a_played = max(int(ar["intPlayed"]), 1)

                    # Team quality within their league
                    h_ppg = hr["intPoints"] / h_played
                    a_ppg = ar["intPoints"] / a_played
                    h_gf = hr["intGoalsFor"] / h_played
                    a_gf = ar["intGoalsFor"] / a_played
                    h_ga = hr["intGoalsAgainst"] / h_played
                    a_ga = ar["intGoalsAgainst"] / a_played

                    # League strength adjustment
                    h_lstr = LEAGUE_STRENGTH.get(home_league, 0.50)
                    a_lstr = LEAGUE_STRENGTH.get(away_league, 0.50)

                    # Expected goals using Poisson: attack * opponent_defense_weakness * league_ratio
                    league_ratio = h_lstr / max(a_lstr, 0.01)
                    inv_ratio = a_lstr / max(h_lstr, 0.01)

                    # Home expected goals = home_attack * (away_defense_weakness) * league_advantage * home_bonus
                    h_xg = h_gf * (a_ga / max(a_gf, 0.01)) * league_ratio * 1.1  # 10% home advantage
                    a_xg = a_gf * (h_ga / max(h_gf, 0.01)) * inv_ratio * 0.9

                    # Clamp
                    h_xg = max(0.1, min(h_xg, 5.0))
                    a_xg = max(0.1, min(a_xg, 5.0))

                    # Poisson probabilities
                    max_goals = 8
                    p_home_win = sum(
                        poisson.pmf(g1, h_xg) * sum(poisson.pmf(g2, a_xg) for g2 in range(g1))
                        for g1 in range(1, max_goals)
                    )
                    p_draw = sum(
                        poisson.pmf(g, h_xg) * poisson.pmf(g, a_xg) for g in range(max_goals)
                    )
                    p_away_win = 1 - p_home_win - p_draw

                    # Ensure valid probabilities
                    total_p = p_home_win + p_draw + p_away_win
                    p_home_win /= total_p
                    p_draw /= total_p
                    p_away_win /= total_p

                    st.markdown(f"**{home_t}** ({home_league}, coeff: {h_lstr:.2f}) vs "
                                f"**{away_t}** ({away_league}, coeff: {a_lstr:.2f})")

                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric(f"{home_t} Win", f"{p_home_win*100:.1f}%")
                    mc2.metric("Draw", f"{p_draw*100:.1f}%")
                    mc3.metric(f"{away_t} Win", f"{p_away_win*100:.1f}%")

                    st.caption(f"xG: {home_t} {h_xg:.2f} — {away_t} {a_xg:.2f} "
                               f"(Poisson model with UEFA-like league strength coefficients)")


# =========================================================================
# PAGE: Advanced Statistics
# =========================================================================
elif page == "📈 Advanced Statistics":
    st.title("📈 Advanced Statistics")

    if f_standings.empty:
        st.warning("No standings data.")
    else:
        # ── Poisson ──
        st.subheader("1. Poisson Goal Model")
        poisson_league = st.selectbox("League", sorted(f_standings["league"].unique()), key="poi_league")
        poi_df = f_standings[f_standings["league"] == poisson_league].copy()
        poi_df["gf_rate"] = poi_df["intGoalsFor"] / poi_df["intPlayed"].clip(lower=1)
        poi_df["ga_rate"] = poi_df["intGoalsAgainst"] / poi_df["intPlayed"].clip(lower=1)
        avg_gf = poi_df["gf_rate"].mean()

        sel_team = st.selectbox("Team", poi_df["strTeam"].tolist(), key="poi_team")
        team_row = poi_df[poi_df["strTeam"] == sel_team].iloc[0]

        atk_str = team_row["gf_rate"] / max(avg_gf, 0.01)
        def_str = team_row["ga_rate"] / max(avg_gf, 0.01)
        st.markdown(f"**{sel_team}**: Attack Strength **{atk_str:.2f}** · Defense Strength **{def_str:.2f}** · λ = **{team_row['gf_rate']:.2f}**")

        goals_range = list(range(7))
        probs = [poisson.pmf(g, team_row["gf_rate"]) * 100 for g in goals_range]
        fig_poi = px.bar(x=goals_range, y=probs, text=[f"{p:.1f}%" for p in probs],
                         title=f"Poisson Goal Probability — {sel_team}",
                         labels={"x": "Goals", "y": "Probability %"})
        fig_poi.update_traces(textposition="outside")
        fig_poi.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig_poi, use_container_width=True)

        # ── Expected Points ──
        st.subheader("2. Expected Points (xPts)")
        xpts_data = []
        for _, row in poi_df.iterrows():
            gf_r = row["gf_rate"]
            ga_r = row["ga_rate"]
            pw = sum(poisson.pmf(g1, gf_r) * sum(poisson.pmf(g2, ga_r) for g2 in range(g1)) for g1 in range(8))
            pd_p = sum(poisson.pmf(g, gf_r) * poisson.pmf(g, ga_r) for g in range(8))
            xpts = (pw * 3 + pd_p * 1) * row["intPlayed"]
            xpts_data.append({
                "Team": row["strTeam"], "Actual": int(row["intPoints"]),
                "xPts": round(xpts, 1), "Diff": round(row["intPoints"] - xpts, 1),
            })
        xpts_df = pd.DataFrame(xpts_data).sort_values("Actual", ascending=False)

        fig_xpts = go.Figure()
        fig_xpts.add_trace(go.Bar(x=xpts_df["Team"], y=xpts_df["Actual"], name="Actual", marker_color="#1f77b4"))
        fig_xpts.add_trace(go.Scatter(x=xpts_df["Team"], y=xpts_df["xPts"], name="xPts",
                                       mode="markers+lines", marker=dict(size=10, color="#d62728")))
        fig_xpts.update_layout(title="Actual vs Expected Points (Poisson)", template="plotly_white", height=400)
        st.plotly_chart(fig_xpts, use_container_width=True)

        # Over/under
        fig_diff = px.bar(xpts_df.sort_values("Diff"), x="Diff", y="Team", orientation="h",
                          color="Diff", color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                          title="Over/Under Performance", text="Diff")
        fig_diff.update_traces(texttemplate="%{text:+.1f}", textposition="outside")
        fig_diff.update_layout(template="plotly_white", height=350, showlegend=False)
        st.plotly_chart(fig_diff, use_container_width=True)

        # ── Form Trend ──
        if "strForm" in poi_df.columns:
            st.subheader("3. Form Trend Analysis")
            form_analysis = []
            for _, row in poi_df.iterrows():
                form = str(row.get("strForm", ""))
                if form:
                    form_pts = sum(3 if c == "W" else 1 if c == "D" else 0 for c in form)
                    form_ppg = form_pts / max(len(form), 1)
                    season_ppg = row["intPoints"] / max(row["intPlayed"], 1)
                    form_analysis.append({
                        "Team": row["strTeam"],
                        "Form PPG": round(form_ppg, 2),
                        "Season PPG": round(season_ppg, 2),
                        "Trend": "↗️ Rising" if form_ppg > season_ppg else "↘️ Declining",
                    })
            if form_analysis:
                form_df = pd.DataFrame(form_analysis).sort_values("Form PPG", ascending=False)
                fig_form = go.Figure()
                fig_form.add_trace(go.Bar(x=form_df["Team"], y=form_df["Season PPG"],
                                          name="Season PPG", marker_color="#1f77b4"))
                fig_form.add_trace(go.Bar(x=form_df["Team"], y=form_df["Form PPG"],
                                          name="Recent Form PPG", marker_color="#ff7f0e"))
                fig_form.update_layout(title="Season PPG vs Recent Form", template="plotly_white",
                                       barmode="group", height=400)
                st.plotly_chart(fig_form, use_container_width=True)
                st.dataframe(form_df, use_container_width=True, hide_index=True)


# =========================================================================
# PAGE: Data Sources
# =========================================================================
elif page == "📋 Data Sources":
    st.title("📋 Data Sources & Methods")

    st.subheader("Data Sources")
    st.markdown("""
    | Source | Data | Season | License |
    |--------|------|--------|---------|
    | [TheSportsDB](https://www.thesportsdb.com) | Standings, events, teams, players | 2025-2026 | CC BY-NC-SA 4.0 |
    | [Football-Data.org](https://www.football-data.org) | Competition metadata | 2025-2026 | Free tier |
    """)

    st.subheader("Leagues Covered (2025-2026)")
    if not all_standings.empty:
        league_summary = all_standings.groupby("league").agg(
            Teams=("strTeam", "nunique"),
            Avg_Pts=("intPoints", "mean"),
        ).round(1).sort_values("Teams", ascending=False)
        st.dataframe(league_summary, use_container_width=True)

    st.subheader("Models & References")
    st.markdown("""
    | Model | Purpose | Reference |
    |---|---|---|
    | Monte Carlo Simulation | Championship finish probability | Simulation-based inference |
    | K-Means Clustering | Team performance tiers | MacQueen (1967) |
    | Linear Regression | Points prediction | OLS |
    | Poisson Distribution | Goal probability | Dixon & Coles (1997) |
    | Expected Points (xPts) | Over/under performance | Understat methodology |

    **Academic References:**
    1. Dixon, M. & Coles, S. (1997). "Modelling association football scores." *Applied Statistics*, 46(2), 265-280.
    2. Maher, M. (1982). "Modelling association football scores." *Statistica Neerlandica*, 36(3), 109-118.
    3. Hvattum, L. & Arntzen, H. (2010). "Using ELO ratings for match result prediction." *IJF*, 26(3), 460-470.
    """)
