"""
Football Analytics Pro Dashboard  2025-2026 Season
=====================================================
Professional football club analytics platform with scouting,
tactical analysis, opponent reports, financial analysis, and more.

Run: python -m streamlit run football_dashboard_v3.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json, os, glob, re, math
from datetime import datetime, timedelta
from scipy.stats import poisson, percentileofscore
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Football Analytics Pro 2025-2026", page_icon="", layout="wide", initial_sidebar_state="expanded")

#  Custom CSS
st.markdown("""<style>
.stMetric {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 10px; border-radius: 10px; color: white;}
.stMetric label {color: white !important;}
div[data-testid="stMetricValue"] {color: white !important;}
.big-font {font-size:20px !important; font-weight: bold;}
section[data-testid="stSidebar"] {background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); color: white;}
section[data-testid="stSidebar"] .stSelectbox label, section[data-testid="stSidebar"] .stMultiSelect label {color: white !important;}
</style>""", unsafe_allow_html=True)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

LEAGUE_ID_TO_NAME = {
    4328: "English Premier League", 4335: "La Liga", 4332: "Serie A",
    4331: "Bundesliga", 4334: "Ligue 1", 4337: "Eredivisie",
    4344: "Primeira Liga", 4339: "Turkish Super Lig", 4338: "Belgian Pro League",
    4355: "Russian Premier League", 4330: "Scottish Premiership",
    4340: "Danish Superliga", 4336: "Greek Super League",
    4691: "Romanian Liga I", 4665: "Romanian Liga II",
}

LEAGUE_FORMAT = {
    "Romanian Liga I": {"type": "playoff_playout", "regular_season": 30,
        "description": "16 teams play 30 rounds. Top 6  Championship Playoff (10 extra rounds, points halved). Bottom 10  Relegation Playout (18 extra rounds). Last 2 relegated directly. 13th & 14th play promotion/relegation vs Liga II.",
        "playoff_teams": 6, "playout_teams": 10, "halve_points": True, "ucl_spots": 1, "uel_spots": 1, "uecl_spots": 1, "relegation": 2, "relegation_playoff": 2},
    "Romanian Liga II": {"type": "liga2_ro", "regular_season": 21,
        "description": "22 teams play 21 rounds. Top 6  Promotion Playoff. 1st & 2nd auto-promote; 3rd & 4th play Liga I 13th & 14th. Remaining 16 split into Group A/B (8 each). Last 2 of each group relegated.",
        "playoff_teams": 6, "playout_group_size": 8, "auto_promotion": 2, "relegation_per_group": 2, "playout_relegation": 1},
    "Belgian Pro League": {"type": "belgian", "regular_season": 30,
        "description": "16 teams play 30 rounds. Top 6  Championship Playoff (points halved + 10 rounds). 7th-12th  Europa Playoff. 13th-16th  Relegation Playoff.",
        "playoff_teams": 6, "europa_playoff_teams": 6, "relegation_playoff_teams": 4, "halve_points": True, "ucl_spots": 1, "uel_spots": 1, "relegation": 1},
    "Scottish Premiership": {"type": "split", "regular_season": 33,
        "description": "12 teams play 33 rounds. Top 6  Championship Split (5 more rounds). Bottom 6  Relegation Split (5 more rounds). 12th relegated; 11th plays playoff.",
        "split_at": 6, "relegation": 1, "relegation_playoff": 1},
    "Danish Superliga": {"type": "playoff_playout", "regular_season": 22,
        "description": "12 teams play 22 rounds. Top 6  Championship Group (10 more rounds). Bottom 6  Relegation Group (10 more rounds). 11th & 12th relegated.",
        "playoff_teams": 6, "playout_teams": 6, "relegation": 2},
}

LEAGUE_MARKET = {
    "English Premier League": 500, "La Liga": 350, "Serie A": 280, "Bundesliga": 280,
    "Ligue 1": 200, "Eredivisie": 60, "Primeira Liga": 70, "Turkish Super Lig": 40,
    "Belgian Pro League": 30, "Scottish Premiership": 15, "Greek Super League": 20,
    "Danish Superliga": 15, "Russian Premier League": 30, "Romanian Liga I": 8, "Romanian Liga II": 2,
}

LEAGUE_STRENGTH = {
    "English Premier League": 1.00, "La Liga": 0.95, "Serie A": 0.90, "Bundesliga": 0.88,
    "Ligue 1": 0.80, "Eredivisie": 0.65, "Primeira Liga": 0.70, "Turkish Super Lig": 0.55,
    "Belgian Pro League": 0.55, "Scottish Premiership": 0.45, "Greek Super League": 0.45,
    "Danish Superliga": 0.40, "Russian Premier League": 0.50, "Romanian Liga I": 0.35, "Romanian Liga II": 0.20,
}

POS_GROUPS = {"GK": ["Goalkeeper"], "DEF": ["Defender","Centre-Back","Left-Back","Right-Back","Wing-Back"],
    "MID": ["Midfielder","Central Midfield","Defensive Midfield","Attacking Midfield","Left Midfield","Right Midfield"],
    "ATT": ["Forward","Attacker","Striker","Centre-Forward","Left Winger","Right Winger","Left Wing","Right Wing","Second Striker"]}
_pos_lookup = {}
for grp, positions in POS_GROUPS.items():
    for p in positions:
        _pos_lookup[p.lower()] = grp

def _pos_group(pos_str):
    if not pos_str or not isinstance(pos_str, str): return None
    return _pos_lookup.get(pos_str.strip().lower())

def _parse_money_eur(raw):
    if not raw or not isinstance(raw, str): return None
    s = raw.strip()
    if s.lower() in ("youth","free","on loan","loan",""): return None
    s = s.replace("\u00c2\u00a3","").replace("\u00c2","").replace("\u00a3","")
    s = s.replace("\u00e2\u0082\u00ac","").replace("","")
    m = re.search(r"([\d.,]+)\s*(m(?:ill)?\.?|k)?", s, re.IGNORECASE)
    if not m: return None
    num_str = m.group(1).replace(",",".")
    try: val = float(num_str)
    except ValueError: return None
    suffix = (m.group(2) or "").lower()
    if suffix.startswith("k"): val /= 1000.0
    elif not suffix and val > 500: val /= 1_000_000.0
    if "" in s: val *= 1.17
    return round(val, 2) if val > 0 else None

_STRIP_PRE = re.compile(r'^(FC|AFC|SC|CS|CSC|CSM|ACS|ACSM|ACSC|ASC|FK|SK|KV|KRC|KAA|RSC|SV|TSV|VfB|VfL|1\.\s*)\s+', re.IGNORECASE)
_STRIP_SUF = re.compile(r'\s+(FC|FK|SK|SC|CF|1923|1948|1947|2022|1902|04)\s*$', re.IGNORECASE)
def _normalize_team(name):
    if not name: return ""
    n = _STRIP_PRE.sub("", name.strip())
    return _STRIP_SUF.sub("", n).lower().strip()

def _find_squad(team_name, player_df, league_filter=None):
    if player_df.empty: return pd.DataFrame()
    df = player_df
    if league_filter and "league" in df.columns: df = df[df["league"] == league_filter]
    for col in ["_teamName","strTeam"]:
        if col in df.columns:
            match = df[df[col] == team_name]
            if not match.empty: return match.copy()
    norm = _normalize_team(team_name)
    for col in ["_teamName","strTeam"]:
        if col in df.columns:
            df_norm = df[col].apply(_normalize_team)
            match = df[df_norm == norm]
            if not match.empty: return match.copy()
            match = df[df_norm.str.contains(norm, na=False)]
            if not match.empty: return match.copy()
    return pd.DataFrame()

def _estimate_value(row, league_mkt):
    tm_val = row.get("market_value_eur_m")
    if tm_val is not None and not pd.isna(tm_val) and float(tm_val) > 0: return round(float(tm_val), 2)
    parsed = _parse_money_eur(row.get("strSigning"))
    age = row.get("age", 27)
    if pd.isna(age): age = 27
    grp = _pos_group(row.get("strPosition",""))
    age_mult = {True: 0.6}.get(age < 21, {True: 1.1}.get(age < 24, {True: 1.0}.get(age <= 28, {True: 0.7}.get(age <= 30, {True: 0.4}.get(age <= 33, 0.15)))))
    pos_mult = {"ATT":1.3,"MID":1.0,"DEF":0.85,"GK":0.6}.get(grp, 0.8)
    if parsed and parsed > 0.01: return round(parsed * age_mult, 2)
    return round(league_mkt * 0.004 * age_mult * pos_mult, 2)

# 
# DATA LOADING
# 
@st.cache_data
def load_all_standings():
    frames, loaded, no_resort = [], set(), set()
    for fpath in glob.glob(os.path.join(DATA_DIR, "full_standings_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f: data = json.load(f)
            table = data.get("table", [])
            if not table: continue
            df = pd.DataFrame(table)
            for c in ["intRank","intPlayed","intWin","intLoss","intDraw","intGoalsFor","intGoalsAgainst","intGoalDifference","intPoints"]:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
            lid = data.get("league_id")
            if lid:
                lid = int(lid); df["league"] = LEAGUE_ID_TO_NAME.get(lid,"Unknown"); df["league_id"] = lid; loaded.add(lid)
            elif "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0]); df["league"] = LEAGUE_ID_TO_NAME.get(lid,"Unknown"); df["league_id"] = lid; loaded.add(lid)
            if data.get("no_resort"):
                ln = df["league"].iloc[0] if "league" in df.columns and len(df)>0 else None
                if ln: no_resort.add(ln)
            frames.append(df)
        except Exception: continue
    for fpath in glob.glob(os.path.join(DATA_DIR, "standings_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f: data = json.load(f)
            table = data.get("table",[])
            if not table: continue
            df = pd.DataFrame(table)
            if "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0])
                if lid in loaded: continue
                df["league"] = LEAGUE_ID_TO_NAME.get(lid,"Unknown"); df["league_id"] = lid
            for c in ["intRank","intPlayed","intWin","intLoss","intDraw","intGoalsFor","intGoalsAgainst","intGoalDifference","intPoints"]:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
            frames.append(df)
        except Exception: continue
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        resorted = []
        for ln in combined["league"].unique():
            ldf = combined[combined["league"]==ln].copy()
            if ln not in no_resort:
                ldf = ldf.sort_values(["intPoints","intGoalDifference","intGoalsFor"], ascending=[False,False,False]).reset_index(drop=True)
                ldf["intRank"] = range(1, len(ldf)+1)
            resorted.append(ldf)
        return pd.concat(resorted, ignore_index=True)
    return pd.DataFrame()

@st.cache_data
def load_all_events():
    frames, loaded = [], set()
    for fpath in glob.glob(os.path.join(DATA_DIR, "all_events_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f: data = json.load(f)
            events = data.get("events",[])
            if not events: continue
            df = pd.DataFrame(events)
            for c in ["intHomeScore","intAwayScore","intRound"]:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
            if "dateEvent" in df.columns: df["dateEvent"] = pd.to_datetime(df["dateEvent"], errors="coerce")
            if "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0]); df["league"] = LEAGUE_ID_TO_NAME.get(lid,""); loaded.add(lid)
            frames.append(df)
        except Exception: continue
    for fpath in glob.glob(os.path.join(DATA_DIR, "events_2526_*.json")):
        try:
            with open(fpath, encoding="utf-8") as f: data = json.load(f)
            events = data.get("events",[])
            if not events: continue
            df = pd.DataFrame(events)
            if "idLeague" in df.columns:
                lid = int(df["idLeague"].iloc[0])
                if lid in loaded: continue
                df["league"] = LEAGUE_ID_TO_NAME.get(lid,"")
            for c in ["intHomeScore","intAwayScore","intRound"]:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
            if "dateEvent" in df.columns: df["dateEvent"] = pd.to_datetime(df["dateEvent"], errors="coerce")
            frames.append(df)
        except Exception: continue
    if frames:
        result = pd.concat(frames, ignore_index=True)
        if "idEvent" in result.columns: result = result.drop_duplicates(subset=["idEvent"])
        return result
    return pd.DataFrame()

@st.cache_data
def load_all_teams():
    path = os.path.join(DATA_DIR, "all_teams_2526.json")
    if not os.path.exists(path): return pd.DataFrame()
    with open(path, encoding="utf-8") as f: data = json.load(f)
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)
        if "_leagueName" in df.columns: df.rename(columns={"_leagueName":"league"}, inplace=True)
        return df
    return pd.DataFrame()

@st.cache_data
def load_all_players():
    path = os.path.join(DATA_DIR, "all_players_2526.json")
    if not os.path.exists(path): return pd.DataFrame()
    with open(path, encoding="utf-8") as f: data = json.load(f)
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)
        if "_leagueName" in df.columns: df.rename(columns={"_leagueName":"league"}, inplace=True)
        if "dateBorn" in df.columns:
            df["birth_date"] = pd.to_datetime(df["dateBorn"], dayfirst=True, errors="coerce")
            if "age" in df.columns:
                df["age"] = pd.to_numeric(df["age"], errors="coerce")
                mask = df["age"].isna() & df["birth_date"].notna()
                df.loc[mask,"age"] = ((pd.Timestamp.now()-df.loc[mask,"birth_date"]).dt.days/365.25).round(1)
            else:
                df["age"] = ((pd.Timestamp.now()-df["birth_date"]).dt.days/365.25).round(1)
        return df
    return pd.DataFrame()

# Load all data
all_standings = load_all_standings()
all_events = load_all_events()
all_teams = load_all_teams()
all_players = load_all_players()

# Prepare player data with position groups and values
_ap = pd.DataFrame()
if not all_players.empty and "strPosition" in all_players.columns:
    _ap = all_players.copy()
    _ap = _ap[~_ap["strPosition"].str.contains("Coach|Manager|Director|Physio|Analyst|Scout", case=False, na=True)]
    _ap["pos_group"] = _ap["strPosition"].apply(_pos_group)
    _ap = _ap[_ap["pos_group"].notna()].copy()
    _ap["est_value"] = _ap.apply(lambda r: _estimate_value(r, LEAGUE_MARKET.get(r.get("league",""), 20)), axis=1)
    _ap["market_value_eur_m"] = pd.to_numeric(_ap.get("market_value_eur_m", pd.Series(dtype=float)), errors="coerce")


# 
# SIDEBAR & FILTERS
# 
st.sidebar.title(" Football Analytics Pro")
st.sidebar.caption("Season 2025-2026  Professional Club Platform")
st.sidebar.markdown("---")

available_leagues = sorted(all_standings["league"].unique().tolist()) if not all_standings.empty else []
selected_leagues = st.sidebar.multiselect(" Leagues", options=available_leagues, default=available_leagues)

league_teams = sorted(all_standings[all_standings["league"].isin(selected_leagues)]["strTeam"].unique().tolist()) if not all_standings.empty and selected_leagues else []
selected_teams = st.sidebar.multiselect(" Teams", options=league_teams, default=[])
player_search = st.sidebar.text_input(" Search Player", "")
st.sidebar.markdown("---")

def filter_standings(df):
    if df.empty: return df
    f = df[df["league"].isin(selected_leagues)] if selected_leagues else df
    if selected_teams: f = f[f["strTeam"].isin(selected_teams)]
    return f
def filter_events(df):
    if df.empty: return df
    f = df[df["league"].isin(selected_leagues)] if selected_leagues else df
    if selected_teams: f = f[(f["strHomeTeam"].isin(selected_teams))|(f["strAwayTeam"].isin(selected_teams))]
    return f
def filter_players(df):
    if df.empty: return df
    f = df
    if selected_leagues and "league" in df.columns: f = f[f["league"].isin(selected_leagues)]
    if selected_teams and "_teamName" in df.columns: f = f[f["_teamName"].isin(selected_teams)]
    if player_search: f = f[f["strPlayer"].str.contains(player_search, case=False, na=False)]
    return f

f_standings = filter_standings(all_standings)
f_events = filter_events(all_events)
f_players = filter_players(all_players)

pages = [
    " Overview & Standings",
    " Match Analysis",
    " Championship Probability",
    " European Comparison",
    " Player Analysis",
    " Scouting Intelligence",
    " Tactical Analysis",
    " Opponent Report",
    " Transfer Recommendations",
    " Physical & Medical",
    " Youth Academy",
    " Financial Analysis",
    " Season Projections",
    " ML Prediction Models",
    " Advanced Statistics",
    " League Management",
    " Video Analysis Hub",
    " Data Sources",
    " Documentation",
]
page = st.sidebar.radio("Section", pages)
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Data:** {len(all_standings)} standings  {len(all_events)} events  {len(all_players)} players")

# Helper for standings tables
def _make_table(df):
    cols = ["intRank","strTeam","intPlayed","intWin","intDraw","intLoss","intGoalsFor","intGoalsAgainst","intGoalDifference","intPoints"]
    cols = [c for c in cols if c in df.columns]
    d = df[cols].copy()
    d.columns = ["Pos","Team","P","W","D","L","GF","GA","GD","Pts"][:len(cols)]
    return d

ideal_comp = {"GK":(2,3),"DEF":(6,9),"MID":(6,9),"ATT":(4,7)}

# 
# PAGE: Overview & Standings
# 
if page == " Overview & Standings":
    st.title(" Football Analytics Pro  2025-2026")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Overview & Standings** shows the current league tables for all selected leagues.

- Use the **Leagues** filter in the sidebar to select which leagues to display
- Tables are split into playoff/playout zones where applicable (Romania, Belgium, Scotland, etc.)
- **Recent Form** shows each team's last 5 results (W=Win, D=Draw, L=Loss)
- **Points Distribution** at the bottom compares the top teams across all selected leagues
- Use the slider to control how many teams per league appear in the comparison chart
""")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Leagues", len(selected_leagues))
    c2.metric("Teams", len(f_standings["strTeam"].unique()) if not f_standings.empty else 0)
    c3.metric("Matches", len(f_events))
    c4.metric("Players", len(f_players))
    total_val = _ap["est_value"].sum() if not _ap.empty else 0
    c5.metric("Total Value", f"{total_val:.0f}M")

    if f_standings.empty:
        st.warning("No standings data.")
    else:
        for league_name in sorted(f_standings["league"].unique()):
            league_df = f_standings[f_standings["league"]==league_name].sort_values("intRank")
            st.subheader(f" {league_name}")
            fmt = LEAGUE_FORMAT.get(league_name)

            if fmt:
                st.info(f"**Format:** {fmt['description']}")
                ftype = fmt["type"]
                if ftype == "liga2_ro":
                    n_po = fmt.get("playoff_teams",6); n_total = len(league_df)
                    po_df = league_df[league_df["intRank"]<=min(n_po,n_total)].copy()
                    rest_df = league_df[league_df["intRank"]>min(n_po,n_total)].copy()
                    if not po_df.empty:
                        st.markdown(f"** Promotion Playoff** (Top {min(n_po,n_total)})")
                        po_d = _make_table(po_df); zones = []
                        for _,r in po_df.iterrows():
                            zones.append(" Auto-Promotion" if r["intRank"]<=2 else " Promotion Playoff" if r["intRank"]<=4 else "")
                        po_d["Zone"] = zones; st.dataframe(po_d, use_container_width=True, hide_index=True)
                    if not rest_df.empty:
                        half = (len(rest_df)+1)//2
                        for label,grp in [("A",rest_df.iloc[:half]),("B",rest_df.iloc[half:])]:
                            if grp.empty: continue
                            st.markdown(f"** Playout Group {label}**")
                            d = _make_table(grp); zn = []
                            for idx in range(len(grp)):
                                pos = idx+1
                                if pos > len(grp)-fmt.get("relegation_per_group",2): zn.append(" Relegated")
                                elif pos == len(grp)-fmt.get("relegation_per_group",2): zn.append(" Playout")
                                else: zn.append("")
                            d["Zone"] = zn; st.dataframe(d, use_container_width=True, hide_index=True)
                elif ftype == "belgian":
                    n_po,n_eu,n_rel = fmt.get("playoff_teams",6),fmt.get("europa_playoff_teams",6),fmt.get("relegation_playoff_teams",4)
                    po = league_df[league_df["intRank"]<=n_po]; eu = league_df[(league_df["intRank"]>n_po)&(league_df["intRank"]<=n_po+n_eu)]; rl = league_df[league_df["intRank"]>n_po+n_eu]
                    if not po.empty: st.markdown("** Championship Playoff**"); st.dataframe(_make_table(po), use_container_width=True, hide_index=True)
                    if not eu.empty: st.markdown("** Europa Playoff**"); st.dataframe(_make_table(eu), use_container_width=True, hide_index=True)
                    if not rl.empty: st.markdown("** Relegation Playoff**"); st.dataframe(_make_table(rl), use_container_width=True, hide_index=True)
                elif ftype == "playoff_playout":
                    n_po = min(fmt.get("playoff_teams",6), len(league_df)); n_total = len(league_df)
                    po = league_df[league_df["intRank"]<=n_po]; pl = league_df[league_df["intRank"]>n_po]
                    if not po.empty:
                        hn = " (points halved)" if fmt.get("halve_points") else ""
                        st.markdown(f"** Championship Playoff** (Top {n_po}{hn})"); st.dataframe(_make_table(po), use_container_width=True, hide_index=True)
                    if not pl.empty:
                        n_rel,n_rp = fmt.get("relegation",0),fmt.get("relegation_playoff",0)
                        st.markdown(f"** Relegation Playout**"); d = _make_table(pl); zn = []
                        for _,r in pl.iterrows():
                            if n_rel>0 and r["intRank"]>n_total-n_rel: zn.append(" Relegated")
                            elif n_rp>0 and r["intRank"]>n_total-n_rel-n_rp: zn.append(" Prom./Rel. Playoff")
                            else: zn.append("")
                        d["Zone"] = zn; st.dataframe(d, use_container_width=True, hide_index=True)
                elif ftype == "split":
                    sa = min(fmt.get("split_at",6), len(league_df)); n_total = len(league_df)
                    top = league_df[league_df["intRank"]<=sa]; bot = league_df[league_df["intRank"]>sa]
                    hn = " (points halved)" if fmt.get("halve_points") else ""
                    if not top.empty: st.markdown(f"** Championship Group**{hn}"); st.dataframe(_make_table(top), use_container_width=True, hide_index=True)
                    if not bot.empty:
                        n_rel,n_rp = fmt.get("relegation",0),fmt.get("relegation_playoff",0)
                        st.markdown("** Relegation Group**"); d = _make_table(bot); zn = []
                        for _,r in bot.iterrows():
                            if n_rel>0 and r["intRank"]>n_total-n_rel: zn.append(" Relegation")
                            elif n_rp>0 and r["intRank"]>n_total-n_rel-n_rp: zn.append(" Rel. Playoff")
                            else: zn.append("")
                        d["Zone"] = zn; st.dataframe(d, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(_make_table(league_df), use_container_width=True, hide_index=True)
            else:
                st.dataframe(_make_table(league_df), use_container_width=True, hide_index=True)

            if "strForm" in league_df.columns:
                form_data = league_df[["strTeam","strForm"]].dropna()
                if not form_data.empty:
                    txt = ""
                    for _,r in form_data.iterrows():
                        icons = {"W":"","D":"","L":""}
                        txt += f"**{r['strTeam']}**: {''.join(icons.get(c,'') for c in str(r['strForm']))}  \n"
                    with st.expander("Recent Form"): st.markdown(txt)

        if len(f_standings["league"].unique()) > 1:
            st.subheader("Points Distribution  All Leagues")
            top_n = st.slider("Top N per league", 3, 10, 5)
            top_teams = pd.concat([g.nlargest(min(top_n, len(g)), "intPoints") for _, g in f_standings.groupby("league")], ignore_index=True)
            if not top_teams.empty:
                fig = px.bar(top_teams.sort_values(["league","intPoints"]), x="intPoints", y="strTeam", color="league", orientation="h", text="intPoints", height=max(400,len(top_teams)*25))
                fig.update_traces(textposition="outside"); fig.update_layout(template="plotly_white", yaxis={"categoryorder":"total ascending"})
                st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Match Analysis
# 
elif page == " Match Analysis":
    st.title(" Match Analysis")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Match Analysis** lets you explore match results and head-to-head statistics.

- **Date Range**: Filter matches by date using the date picker
- **Head-to-Head**: Select two teams to compare their history
- **Outcome Distribution**: See the proportion of home wins, draws, and away wins
- **Goal Timing**: Discover when goals tend to be scored
- **Home Advantage**: Compare home vs away performance across teams
- **Records**: Find the biggest wins and highest-scoring matches
""")
    if f_events.empty:
        st.warning("No match events.")
    else:
        if "dateEvent" in f_events.columns:
            mn,mx = f_events["dateEvent"].dropna().min(), f_events["dateEvent"].dropna().max()
            if pd.notna(mn) and pd.notna(mx):
                dr = st.date_input("Date Range", value=(mn.date(),mx.date()), min_value=mn.date(), max_value=mx.date(), key="ma_dr")
                fe = f_events[(f_events["dateEvent"].dt.date>=dr[0])&(f_events["dateEvent"].dt.date<=dr[1])] if len(dr)==2 else f_events
            else: fe = f_events
        else: fe = f_events

        completed = fe.dropna(subset=["intHomeScore","intAwayScore"]).copy()
        if completed.empty:
            st.info("No completed matches yet.")
        else:
            completed["intHomeScore"] = completed["intHomeScore"].astype(int)
            completed["intAwayScore"] = completed["intAwayScore"].astype(int)
            completed["total_goals"] = completed["intHomeScore"]+completed["intAwayScore"]
            completed["result"] = np.where(completed["intHomeScore"]>completed["intAwayScore"],"Home Win", np.where(completed["intHomeScore"]<completed["intAwayScore"],"Away Win","Draw"))

            # Head-to-Head tool
            st.subheader(" Head-to-Head Analyzer")
            all_t = sorted(set(completed["strHomeTeam"].tolist()+completed["strAwayTeam"].tolist()))
            if len(all_t)>=2:
                hc1,hc2 = st.columns(2)
                with hc1: h2h_t1 = st.selectbox("Team A", all_t, key="h2h1")
                with hc2: h2h_t2 = st.selectbox("Team B", [t for t in all_t if t!=h2h_t1], key="h2h2")
                h2h = completed[((completed["strHomeTeam"]==h2h_t1)&(completed["strAwayTeam"]==h2h_t2))|((completed["strHomeTeam"]==h2h_t2)&(completed["strAwayTeam"]==h2h_t1))]
                if h2h.empty:
                    st.info("No head-to-head matches found this season.")
                else:
                    t1w = len(h2h[((h2h["strHomeTeam"]==h2h_t1)&(h2h["intHomeScore"]>h2h["intAwayScore"]))|((h2h["strAwayTeam"]==h2h_t1)&(h2h["intAwayScore"]>h2h["intHomeScore"]))])
                    t2w = len(h2h[((h2h["strHomeTeam"]==h2h_t2)&(h2h["intHomeScore"]>h2h["intAwayScore"]))|((h2h["strAwayTeam"]==h2h_t2)&(h2h["intAwayScore"]>h2h["intHomeScore"]))])
                    draws = len(h2h)-t1w-t2w
                    mc1,mc2,mc3 = st.columns(3)
                    mc1.metric(f"{h2h_t1} Wins", t1w); mc2.metric("Draws", draws); mc3.metric(f"{h2h_t2} Wins", t2w)
                    h2h_disp = h2h[["dateEvent","strHomeTeam","intHomeScore","intAwayScore","strAwayTeam"]].copy()
                    h2h_disp.columns = ["Date","Home","HG","AG","Away"]
                    st.dataframe(h2h_disp.sort_values("Date",ascending=False), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader(f"All Completed Matches ({len(completed)})")
            mc = ["dateEvent","strHomeTeam","intHomeScore","intAwayScore","strAwayTeam"]
            if "league" in completed.columns: mc.append("league")
            if "intRound" in completed.columns: mc.append("intRound")
            md = completed[mc].copy()
            md.rename(columns={"dateEvent":"Date","strHomeTeam":"Home","intHomeScore":"HG","intAwayScore":"AG","strAwayTeam":"Away","league":"League","intRound":"Rd"}, inplace=True)
            st.dataframe(md.sort_values("Date",ascending=False), use_container_width=True, hide_index=True)

            c1,c2 = st.columns(2)
            with c1:
                rc = completed["result"].value_counts().reset_index(); rc.columns = ["Result","Count"]
                fig = px.pie(rc, names="Result", values="Count", title="Outcome Distribution", color="Result",
                    color_discrete_map={"Home Win":"#2ca02c","Away Win":"#d62728","Draw":"#ff7f0e"}, hole=0.4)
                fig.update_layout(template="plotly_white", height=350); st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig = px.histogram(completed, x="total_goals", nbins=10, title="Goals per Match", color_discrete_sequence=["#1f77b4"])
                avg = completed["total_goals"].mean()
                fig.add_vline(x=avg, line_dash="dash", line_color="red", annotation_text=f"Avg: {avg:.2f}")
                fig.update_layout(template="plotly_white", height=350); st.plotly_chart(fig, use_container_width=True)

            # Goal timing analysis
            st.subheader(" Goal Timing Analysis")
            if "strResult" in completed.columns:
                st.caption("Goal timing extracted from match result descriptions where available.")
            # Home advantage by league
            if "league" in completed.columns and completed["league"].nunique()>1:
                st.subheader(" Home Advantage by League")
                ha_data = []
                for lg in completed["league"].unique():
                    lgdf = completed[completed["league"]==lg]
                    hw = (lgdf["result"]=="Home Win").mean()*100
                    ha_data.append({"League":lg,"Home Win %":round(hw,1),"Draw %":round((lgdf["result"]=="Draw").mean()*100,1),"Away Win %":round((lgdf["result"]=="Away Win").mean()*100,1)})
                ha_df = pd.DataFrame(ha_data).sort_values("Home Win %",ascending=True)
                fig = px.bar(ha_df, x=["Home Win %","Draw %","Away Win %"], y="League", orientation="h", title="Home Advantage Comparison", barmode="stack", color_discrete_sequence=["#2ca02c","#ff7f0e","#d62728"])
                fig.update_layout(template="plotly_white", height=400); st.plotly_chart(fig, use_container_width=True)

            # Biggest wins
            st.subheader(" Biggest Wins This Season")
            completed["goal_diff"] = abs(completed["intHomeScore"]-completed["intAwayScore"])
            big = completed.nlargest(10,"goal_diff")[["dateEvent","strHomeTeam","intHomeScore","intAwayScore","strAwayTeam","league"]].copy()
            big.columns = ["Date","Home","HG","AG","Away","League"]
            st.dataframe(big, use_container_width=True, hide_index=True)

            # Highest scoring
            st.subheader(" Highest Scoring Matches")
            high = completed.nlargest(10,"total_goals")[["dateEvent","strHomeTeam","intHomeScore","intAwayScore","strAwayTeam","total_goals","league"]].copy()
            high.columns = ["Date","Home","HG","AG","Away","Total","League"]
            st.dataframe(high, use_container_width=True, hide_index=True)


# 
# PAGE: Championship Probability
# 
elif page == " Championship Probability":
    st.title(" Championship Probability  Monte Carlo")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Championship Probability** simulates the rest of the season 10,000+ times.

- Select a **league** to simulate
- The model uses each team's current win/draw/loss rates
- It simulates all remaining matches and counts how often each team finishes in each position
- **Title %**: probability of winning the league
- **Top N %**: probability of finishing in playoff/Champions League spots
- **Relegation %**: probability of finishing in the relegation zone
- Results change as more real matches are played during the season
""")
    if f_standings.empty:
        st.warning("No standings data.")
    else:
        lo = sorted(f_standings["league"].unique())
        sim_lg = st.selectbox("League", lo)
        st_df = f_standings[f_standings["league"]==sim_lg].copy().sort_values("intRank")
        fmt = LEAGUE_FORMAT.get(sim_lg)
        if fmt: st.info(f"**{sim_lg} Format:** {fmt['description']}")

        if len(st_df)<2: st.warning("Need 2 teams.")
        else:
            # For split leagues, separate playoff from playout
            is_split_league = fmt and fmt["type"] in ("playoff_playout", "split", "belgian", "liga2_ro")
            split_active = False
            if is_split_league and sim_lg in ("Romanian Liga I", "Belgian Pro League", "Greek Super League", "Scottish Premiership"):
                # Check if split is active by looking at raw data
                for fp in glob.glob(os.path.join(DATA_DIR, "full_standings_2526_*.json")):
                    try:
                        with open(fp, encoding="utf-8") as _f:
                            _d = json.load(_f)
                        if LEAGUE_ID_TO_NAME.get(_d.get("league_id")) == sim_lg and _d.get("is_split_active"):
                            split_active = True
                            break
                    except Exception:
                        continue

            if split_active:
                sim_group = st.radio("Simulate Group", ["Championship Playoff", "Relegation Playout"], horizontal=True)
                # Get group data from raw standings
                raw_path = None
                for fp in glob.glob(os.path.join(DATA_DIR, "full_standings_2526_*.json")):
                    try:
                        with open(fp, encoding="utf-8") as _f:
                            _d = json.load(_f)
                        if LEAGUE_ID_TO_NAME.get(_d.get("league_id")) == sim_lg:
                            raw_path = _d["table"]
                            break
                    except Exception:
                        continue

                if raw_path:
                    if sim_group == "Championship Playoff":
                        group_key = {"Romanian Liga I": "Playoff", "Belgian Pro League": "Championship Playoff", "Greek Super League": "Championship", "Scottish Premiership": "Championship Group"}.get(sim_lg, "Playoff")
                    else:
                        group_key = {"Romanian Liga I": "Playout", "Belgian Pro League": "Relegation", "Greek Super League": "Relegation", "Scottish Premiership": "Relegation Group"}.get(sim_lg, "Playout")
                    group_teams = [t for t in raw_path if t.get("strGroup", "").startswith(group_key.split()[0])]
                    if group_teams:
                        st_df = pd.DataFrame(group_teams)
                        for c in ["intRank","intPlayed","intWin","intDraw","intLoss","intGoalsFor","intGoalsAgainst","intGoalDifference","intPoints"]:
                            if c in st_df.columns: st_df[c] = pd.to_numeric(st_df[c], errors="coerce").fillna(0).astype(int)
                        st.success(f"Simulating **{sim_group}** group only ({len(st_df)} teams)")

            n_sim = st.slider("Simulations", 1000, 50000, 10000, 1000)
            rem = st.slider("Remaining Matches/Team", 0, 30, 4 if split_active else 10)
            halve = False  # Points are already halved in split standings

            st_df["wr"] = st_df["intWin"]/st_df["intPlayed"].clip(lower=1)
            st_df["dr"] = st_df["intDraw"]/st_df["intPlayed"].clip(lower=1)
            np.random.seed(42)
            names = st_df["strTeam"].values; pts = st_df["intPoints"].values.astype(float)
            if halve: pts = np.ceil(pts/2)
            nt = len(names); fc = np.zeros((nt,nt))

            for _ in range(n_sim):
                sp = pts.copy()
                for i in range(nt):
                    r = np.random.random(rem)
                    sp[i] += np.sum(r<st_df.iloc[i]["wr"])*3 + np.sum((r>=st_df.iloc[i]["wr"])&(r<st_df.iloc[i]["wr"]+st_df.iloc[i]["dr"]))
                order = np.argsort(-sp)
                for pos,idx in enumerate(order): fc[idx][pos]+=1

            champ_pct = fc[:,0]/n_sim*100
            n_po = fmt.get("playoff_teams",fmt.get("split_at",3)) if fmt else 3
            po_pct = fc[:,:min(n_po,nt)].sum(axis=1)/n_sim*100
            n_rel = fmt.get("relegation",3) if fmt else min(3,nt)
            rel_pct = fc[:,-n_rel:].sum(axis=1)/n_sim*100 if nt>n_rel else np.zeros(nt)
            po_lab = "Playoff %" if fmt and fmt["type"] in ("playoff_playout","split","belgian","liga2_ro") else "Top 3 %"

            res_df = pd.DataFrame({"Team":names,"Current Pts":pts.astype(int),"Champion %":champ_pct.round(1),po_lab:po_pct.round(1),"Relegation %":rel_pct.round(1)}).sort_values("Champion %",ascending=False)

            fig = px.bar(res_df.sort_values("Champion %",ascending=True), x="Champion %", y="Team", orientation="h",
                title=f"{sim_lg}  Championship ({n_sim:,} sims, {rem} remaining)", color="Champion %", color_continuous_scale="YlOrRd", text="Champion %")
            fig.update_traces(texttemplate="%{text:.1f}%",textposition="outside"); fig.update_layout(template="plotly_white",height=max(300,nt*40),showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            c1,c2 = st.columns(2)
            with c1:
                fig = px.bar(res_df.sort_values(po_lab,ascending=True), x=po_lab, y="Team", orientation="h", color=po_lab, color_continuous_scale="Greens", text=po_lab, title=f"{po_lab.replace(' %','')} Probability")
                fig.update_traces(texttemplate="%{text:.1f}%",textposition="outside"); fig.update_layout(template="plotly_white",height=max(300,nt*35),showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                if (res_df["Relegation %"]>0).any():
                    rdf = res_df[res_df["Relegation %"]>0]
                    fig = px.bar(rdf.sort_values("Relegation %",ascending=True), x="Relegation %", y="Team", orientation="h", color="Relegation %", color_continuous_scale="Reds", text="Relegation %", title="Relegation Probability")
                    fig.update_traces(texttemplate="%{text:.1f}%",textposition="outside"); fig.update_layout(template="plotly_white",height=max(300,len(rdf)*35),showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

            st.subheader("Position Probability Matrix")
            hm = fc/n_sim*100
            fig = px.imshow(hm, x=[f"#{i+1}" for i in range(nt)], y=names.tolist(), color_continuous_scale="YlOrRd", text_auto=".1f", aspect="auto", title="Finish Position Heatmap")
            fig.update_layout(template="plotly_white",height=max(300,nt*40)); st.plotly_chart(fig, use_container_width=True)
            st.dataframe(res_df, use_container_width=True, hide_index=True)


# 
# PAGE: European Comparison
# 
elif page == " European Comparison":
    st.title(" European League Comparison")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**European Comparison** benchmarks all 15 leagues against each other.

- **Competitiveness**: How close is the points spread? A tighter spread = more competitive league
- **Scoring Trends**: Average goals per match across leagues
- **League Coefficient**: A UEFA-style strength rating based on team performance
- **Squad Valuations**: Total estimated market value per league
- **Radar Charts**: Visual comparison of multiple league metrics at once
""")
    if all_standings.empty: st.warning("No data.")
    else:
        lm = []
        for ln in all_standings["league"].unique():
            ldf = all_standings[all_standings["league"]==ln]
            if ldf.empty or "intGoalsFor" not in ldf.columns: continue
            lm.append({"League":ln,"Teams":len(ldf),"Avg Points":ldf["intPoints"].mean(),"Max Points":ldf["intPoints"].max(),
                "Avg GF":ldf["intGoalsFor"].mean(),"Avg GA":ldf["intGoalsAgainst"].mean(),"Points Spread":ldf["intPoints"].max()-ldf["intPoints"].min(),
                "Leader":ldf.sort_values("intRank").iloc[0]["strTeam"],"Coeff":LEAGUE_STRENGTH.get(ln,0.5)})
        mdf = pd.DataFrame(lm)
        if mdf.empty: st.info("Not enough data.")
        else:
            fig = px.bar(mdf.sort_values("Points Spread"), x="Points Spread", y="League", orientation="h", title="Competitiveness (Lower = Better)", color="Points Spread", color_continuous_scale="RdYlGn_r", text="Points Spread")
            fig.update_traces(texttemplate="%{text:.0f}",textposition="outside"); fig.update_layout(template="plotly_white",height=450,showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            c1,c2 = st.columns(2)
            with c1:
                fig = px.bar(mdf.sort_values("Avg GF",ascending=True), x="Avg GF", y="League", orientation="h", title="Avg Goals Scored/Team", color="Avg GF", color_continuous_scale="Blues", text="Avg GF")
                fig.update_traces(texttemplate="%{text:.1f}",textposition="outside"); fig.update_layout(template="plotly_white",height=400,showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig = px.bar(mdf.sort_values("Coeff",ascending=True), x="Coeff", y="League", orientation="h", title="UEFA-style League Coefficient", color="Coeff", color_continuous_scale="Oranges", text="Coeff")
                fig.update_traces(texttemplate="%{text:.2f}",textposition="outside"); fig.update_layout(template="plotly_white",height=400,showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("League Leaders")
            st.dataframe(mdf[["League","Leader","Max Points","Teams","Coeff"]].sort_values("Max Points",ascending=False), use_container_width=True, hide_index=True)

            st.subheader("League Radar")
            sel = st.multiselect("Compare", mdf["League"].tolist(), default=mdf["League"].tolist()[:4])
            if sel:
                rdf = mdf[mdf["League"].isin(sel)]; cats = ["Avg Points","Avg GF","Avg GA","Points Spread","Coeff"]
                fig = go.Figure()
                for _,r in rdf.iterrows():
                    fig.add_trace(go.Scatterpolar(r=[r[c] for c in cats]+[r[cats[0]]], theta=cats+[cats[0]], name=r["League"], fill="toself", opacity=0.5))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_white", height=500)
                st.plotly_chart(fig, use_container_width=True)

            # Cross-league value comparison
            if not _ap.empty:
                st.subheader(" Squad Value by League")
                val_by = _ap.groupby("league")["est_value"].agg(["sum","mean","count"]).reset_index()
                val_by.columns = ["League","Total Value (M)","Avg Player Value (M)","Players"]
                val_by = val_by.sort_values("Total Value (M)",ascending=True)
                fig = px.bar(val_by, x="Total Value (M)", y="League", orientation="h", color="Avg Player Value (M)", color_continuous_scale="Viridis", text="Total Value (M)", title="Total Squad Value by League")
                fig.update_traces(texttemplate="%{text:.0f}M",textposition="outside"); fig.update_layout(template="plotly_white",height=450,showlegend=False)
                st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Player Analysis
# 
elif page == " Player Analysis":
    st.title(" Player Analysis")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Player Analysis** explores the full player database.

- Use the **Search Player** box in the sidebar to find specific players
- **Position Distribution**: See how many goalkeepers, defenders, midfielders, and forwards exist
- **Nationality**: Discover which countries produce the most players in these leagues
- **Age Distribution**: Histogram of player ages across the dataset
- **Player Comparison**: Select two players side-by-side to compare attributes
- **Team Scatter**: See each team's attacking vs defensive player balance
""")
    if f_players.empty:
        st.warning("No player data. Run fetch_teams_players.py to download.")
    else:
        st.markdown(f"**{len(f_players)} players** matching filters")
        c1,c2 = st.columns(2)
        if "strPosition" in f_players.columns:
            with c1:
                pc = f_players["strPosition"].value_counts().reset_index(); pc.columns=["Position","Count"]
                fig = px.pie(pc, names="Position", values="Count", title="Position Distribution", hole=0.4)
                fig.update_layout(template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)
        if "strNationality" in f_players.columns:
            with c2:
                nc = f_players["strNationality"].value_counts().head(20).reset_index(); nc.columns=["Nationality","Count"]
                fig = px.bar(nc, x="Count", y="Nationality", orientation="h", title="Top 20 Nationalities", color="Count", color_continuous_scale="Blues")
                fig.update_layout(template="plotly_white",height=400,showlegend=False); st.plotly_chart(fig, use_container_width=True)

        if "age" in f_players.columns:
            va = f_players[f_players["age"].between(15,50)]
            if not va.empty:
                fig = px.histogram(va, x="age", nbins=25, title="Age Distribution", color_discrete_sequence=["#1f77b4"])
                avg = va["age"].mean()
                fig.add_vline(x=avg, line_dash="dash", line_color="red", annotation_text=f"Avg: {avg:.1f}")
                fig.update_layout(template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)

        # Player comparison tool
        st.subheader(" Player Comparison Tool")
        if not _ap.empty:
            all_p = sorted(_ap["strPlayer"].dropna().unique().tolist())
            if len(all_p)>=2:
                pc1,pc2 = st.columns(2)
                with pc1: p1 = st.selectbox("Player 1", all_p, key="cmp1")
                with pc2: p2 = st.selectbox("Player 2", [p for p in all_p if p!=p1][:500], key="cmp2")
                r1 = _ap[_ap["strPlayer"]==p1].iloc[0] if len(_ap[_ap["strPlayer"]==p1])>0 else None
                r2 = _ap[_ap["strPlayer"]==p2].iloc[0] if len(_ap[_ap["strPlayer"]==p2])>0 else None
                if r1 is not None and r2 is not None:
                    comp_data = []
                    for attr,label in [("age","Age"),("est_value","Value (M)"),("market_value_eur_m","Market Value (M)")]:
                        v1 = r1.get(attr); v2 = r2.get(attr)
                        if pd.notna(v1) or pd.notna(v2):
                            comp_data.append({"Attribute":label, p1:round(float(v1),1) if pd.notna(v1) else "-", p2:round(float(v2),1) if pd.notna(v2) else "-"})
                    for attr,label in [("strPosition","Position"),("strNationality","Nationality"),("strFoot","Preferred Foot"),("_teamName","Club"),("league","League")]:
                        comp_data.append({"Attribute":label, p1:str(r1.get(attr,"-")), p2:str(r2.get(attr,"-"))})
                    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

        # Player database
        st.subheader(" Player Database")
        dcols = ["strPlayer","strPosition","strNationality","_teamName","league","age","strHeight","strWeight","strNumber"]
        dcols = [c for c in dcols if c in f_players.columns]
        rn = {"strPlayer":"Player","strPosition":"Position","strNationality":"Nationality","_teamName":"Team","league":"League","age":"Age","strHeight":"Height","strWeight":"Weight","strNumber":"#"}
        st.dataframe(f_players[dcols].rename(columns=rn), use_container_width=True, hide_index=True, height=500)

        # Attack vs Defense scatter
        st.subheader("Team Attack vs Defense")
        if not f_standings.empty:
            sd = f_standings.copy()
            sd["gf_pm"] = sd["intGoalsFor"]/sd["intPlayed"].clip(lower=1)
            sd["ga_pm"] = sd["intGoalsAgainst"]/sd["intPlayed"].clip(lower=1)
            fig = px.scatter(sd, x="gf_pm", y="ga_pm", size="intPoints", color="league", hover_name="strTeam", text="strTeam",
                title="Goals Scored vs Conceded per Match", labels={"gf_pm":"GF/Match","ga_pm":"GA/Match"}, size_max=30)
            fig.update_traces(textposition="top center",textfont_size=7)
            fig.add_hline(y=sd["ga_pm"].median(),line_dash="dash",line_color="gray",opacity=0.4)
            fig.add_vline(x=sd["gf_pm"].median(),line_dash="dash",line_color="gray",opacity=0.4)
            fig.update_layout(template="plotly_white",height=600); st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Scouting Intelligence
# 
elif page == " Scouting Intelligence":
    st.title(" Scouting Intelligence Platform")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Scouting Intelligence** is the talent identification hub.

- **Wonderkid Radar**: Finds the best U21 players ranked by a potential score (age + value)
- **Smart Scout**: Build custom filters -- set age range, position, league, and value to find targets
- **Similar Players**: Enter a player and the system finds players with a similar profile
- **Best XI Generator**: Pick a formation and the system builds the optimal team from all available players
- **Value Trends**: See how market values are distributed by position across all leagues

Tip: Use Smart Scout to narrow down transfer targets for specific positions and budget ranges.
""")
    if _ap.empty:
        st.warning("No player data available.")
    else:
        sc_tabs = st.tabs([" Wonderkid Radar"," Smart Scout"," Similar Players"," Best XI Generator"," Value Trends"])

        with sc_tabs[0]:
            st.subheader(" Wonderkid Radar  High Potential U21 Players")
            max_age_wk = st.slider("Max Age", 16, 23, 21, key="wk_age")
            min_val = st.slider("Min Market Value (M)", 0.0, 50.0, 0.5, 0.5, key="wk_val")
            wk = _ap[(_ap["age"]<=max_age_wk)&(_ap["est_value"]>=min_val)].copy()
            wk["potential_score"] = (wk["est_value"]*2/(wk["age"]-15).clip(lower=1) + (max_age_wk+1-wk["age"])*0.5).round(2)
            wk_lg = st.multiselect("Filter Leagues", sorted(wk["league"].unique().tolist()), default=[], key="wk_lg")
            if wk_lg: wk = wk[wk["league"].isin(wk_lg)]
            wk = wk.sort_values("potential_score",ascending=False)
            top_wk = wk.head(30)
            if top_wk.empty: st.info("No wonderkids match criteria.")
            else:
                fig = px.scatter(top_wk, x="age", y="est_value", color="pos_group", hover_name="strPlayer",
                    hover_data=["_teamName","league","strNationality"], size="potential_score", size_max=25,
                    title=f"Wonderkid Radar  U{max_age_wk} (min {min_val}M)", labels={"age":"Age","est_value":"Value (M)"})
                fig.update_layout(template="plotly_white",height=500); st.plotly_chart(fig, use_container_width=True)
                disp = top_wk[["strPlayer","strPosition","age","strNationality","_teamName","league","est_value","potential_score"]].copy()
                disp.columns = ["Player","Position","Age","Nationality","Club","League","Value (M)","Potential Score"]
                st.dataframe(disp, use_container_width=True, hide_index=True)

                # Nationality hotspots
                st.markdown("** Talent Hotspots by Nationality**")
                nat_wk = top_wk["strNationality"].value_counts().head(15).reset_index()
                nat_wk.columns = ["Nationality","Wonderkids"]
                fig = px.bar(nat_wk, x="Wonderkids", y="Nationality", orientation="h", color="Wonderkids", color_continuous_scale="Purples")
                fig.update_layout(template="plotly_white",height=350,showlegend=False); st.plotly_chart(fig, use_container_width=True)

        with sc_tabs[1]:
            st.subheader(" Smart Scout  Custom Filters")
            fc1,fc2,fc3,fc4 = st.columns(4)
            with fc1: s_pos = st.selectbox("Position", ["All","GK","DEF","MID","ATT"], key="ss_pos")
            with fc2: s_age = st.slider("Age Range", 16, 40, (18,30), key="ss_age")
            with fc3: s_val = st.slider("Value Range (M)", 0.0, 200.0, (0.5,50.0), 0.5, key="ss_val")
            with fc4: s_foot = st.selectbox("Preferred Foot", ["Any","Left","Right","Both"], key="ss_foot")
            s_nat = st.multiselect("Nationalities", sorted(_ap["strNationality"].dropna().unique().tolist()), default=[], key="ss_nat")
            s_lg = st.multiselect("Leagues", sorted(_ap["league"].dropna().unique().tolist()), default=[], key="ss_lg")

            sdf = _ap.copy()
            if s_pos!="All": sdf = sdf[sdf["pos_group"]==s_pos]
            sdf = sdf[(sdf["age"]>=s_age[0])&(sdf["age"]<=s_age[1])&(sdf["est_value"]>=s_val[0])&(sdf["est_value"]<=s_val[1])]
            if s_foot!="Any" and "strFoot" in sdf.columns: sdf = sdf[sdf["strFoot"].str.lower().str.contains(s_foot.lower(), na=False)]
            if s_nat: sdf = sdf[sdf["strNationality"].isin(s_nat)]
            if s_lg: sdf = sdf[sdf["league"].isin(s_lg)]
            sdf["scout_rating"] = ((sdf["est_value"]*10)/(sdf["age"]-14).clip(lower=1)).round(1)
            sdf = sdf.sort_values("scout_rating",ascending=False)
            st.markdown(f"**{len(sdf)} players found**")
            disp = sdf.head(50)[["strPlayer","strPosition","age","strNationality","strFoot","_teamName","league","est_value","scout_rating"]].copy()
            disp.columns = ["Player","Position","Age","Nationality","Foot","Club","League","Value (M)","Scout Rating"]
            st.dataframe(disp, use_container_width=True, hide_index=True, height=600)

        with sc_tabs[2]:
            st.subheader(" Find Similar Players")
            ref_player = st.selectbox("Reference Player", sorted(_ap["strPlayer"].dropna().unique().tolist())[:1000], key="sim_ref")
            ref = _ap[_ap["strPlayer"]==ref_player]
            if ref.empty: st.warning("Player not found.")
            else:
                ref_r = ref.iloc[0]
                st.markdown(f"**{ref_player}**  {ref_r.get('strPosition','?')}  Age {ref_r.get('age','?')}  {ref_r.get('_teamName','?')}  {ref_r.get('est_value',0):.1f}M")
                ref_pos = ref_r.get("pos_group")
                ref_age = ref_r.get("age",25)
                ref_val = ref_r.get("est_value",1)
                sim = _ap[(_ap["pos_group"]==ref_pos)&(_ap["strPlayer"]!=ref_player)].copy()
                sim["age_sim"] = 1-abs(sim["age"]-ref_age)/10
                sim["val_sim"] = 1-abs(sim["est_value"]-ref_val)/max(ref_val*3,1)
                sim["similarity"] = (sim["age_sim"]*0.4+sim["val_sim"]*0.6).clip(lower=0).round(2)
                sim = sim.sort_values("similarity",ascending=False).head(20)
                disp = sim[["strPlayer","strPosition","age","strNationality","_teamName","league","est_value","similarity"]].copy()
                disp.columns = ["Player","Position","Age","Nationality","Club","League","Value (M)","Similarity"]
                st.dataframe(disp, use_container_width=True, hide_index=True)

                if len(sim)>2:
                    fig = px.scatter(sim, x="age", y="est_value", color="similarity", hover_name="strPlayer",
                        hover_data=["_teamName","league"], size="similarity", size_max=20, color_continuous_scale="YlOrRd",
                        title=f"Players Similar to {ref_player}")
                    fig.add_trace(go.Scatter(x=[ref_age],y=[ref_val],mode="markers+text",text=[ref_player],
                        marker=dict(size=15,color="red",symbol="star"),name="Reference",textposition="top center"))
                    fig.update_layout(template="plotly_white",height=450); st.plotly_chart(fig, use_container_width=True)

        with sc_tabs[3]:
            st.subheader(" Best XI Generator")
            bxi_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="bxi_lg")
            bxi_mode = st.radio("Criteria", ["Market Value","Age (Youngest)","Scout Rating"], horizontal=True, key="bxi_mode")
            bxi = _ap[_ap["league"]==bxi_lg].copy()
            if bxi_mode=="Market Value": bxi["rank_val"] = bxi["est_value"]
            elif bxi_mode=="Age (Youngest)": bxi["rank_val"] = -bxi["age"]
            else: bxi["rank_val"] = bxi["est_value"]/(bxi["age"]-14).clip(lower=1)

            formation = {"GK":1,"DEF":4,"MID":3,"ATT":3}
            xi_rows = []
            for grp,cnt in formation.items():
                grp_df = bxi[bxi["pos_group"]==grp].nlargest(cnt,"rank_val")
                for _,r in grp_df.iterrows():
                    xi_rows.append({"Position":grp,"Player":r["strPlayer"],"Detailed Pos":r.get("strPosition",""),"Age":r.get("age",""),"Club":r.get("_teamName",""),"Value (M)":r.get("est_value",0),"Nationality":r.get("strNationality","")})
            if xi_rows:
                xi_df = pd.DataFrame(xi_rows)
                total_v = xi_df["Value (M)"].sum()
                avg_a = xi_df["Age"].mean() if "Age" in xi_df.columns else 0
                st.markdown(f"**Best XI** ({bxi_mode})  Total Value: **{total_v:.1f}M**  Avg Age: **{avg_a:.1f}**")
                st.dataframe(xi_df, use_container_width=True, hide_index=True)

        with sc_tabs[4]:
            st.subheader(" Market Value Distribution")
            val_pos = _ap.groupby("pos_group")["est_value"].agg(["mean","median","max","sum"]).reset_index()
            val_pos.columns = ["Position","Mean (M)","Median (M)","Max (M)","Total (M)"]
            st.dataframe(val_pos, use_container_width=True, hide_index=True)
            fig = px.box(_ap[_ap["est_value"]>0], x="pos_group", y="est_value", color="pos_group", title="Value Distribution by Position", labels={"pos_group":"Position","est_value":"Value (M)"})
            fig.update_layout(template="plotly_white",height=400,showlegend=False); st.plotly_chart(fig, use_container_width=True)

            # Value vs Age curve
            st.subheader("Age-Value Curve")
            age_val = _ap[_ap["est_value"]>0].groupby(_ap["age"].round())["est_value"].mean().reset_index()
            age_val.columns = ["Age","Avg Value (M)"]
            fig = px.line(age_val, x="Age", y="Avg Value (M)", title="Average Player Value by Age", markers=True)
            fig.add_vline(x=27, line_dash="dash", annotation_text="Peak Value Age")
            fig.update_layout(template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Tactical Analysis
# 
elif page == " Tactical Analysis":
    st.title(" Tactical Analysis Board")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Tactical Analysis** provides insights into how teams play.

- **Home/Away Split**: Compare points-per-game at home vs away for each team
- **Scoring Patterns**: See goals scored across different matchdays/rounds
- **xG Analysis**: Expected goals calculated using a Poisson model -- shows if teams are over/underperforming
- **Formation Estimator**: Estimates likely formations from squad composition (GK/DEF/MID/ATT ratios)
- **Momentum Tracker**: Cumulative points chart showing each team's form trajectory over the season

Tip: Teams with high xG but low actual goals are "unlucky" -- they may improve. The opposite means regression is likely.
""")
    if f_standings.empty: st.warning("No data.")
    else:
        tac_tabs = st.tabs([" Home/Away Split"," Scoring Patterns"," xG Analysis"," Formation Estimator"," Momentum Tracker"])

        with tac_tabs[0]:
            st.subheader(" Home vs Away Performance")
            if not f_events.empty:
                comp = f_events.dropna(subset=["intHomeScore","intAwayScore"]).copy()
                comp["intHomeScore"] = comp["intHomeScore"].astype(int); comp["intAwayScore"] = comp["intAwayScore"].astype(int)
                teams = sorted(set(comp["strHomeTeam"].tolist()+comp["strAwayTeam"].tolist()))
                ha_data = []
                for t in teams:
                    hm = comp[comp["strHomeTeam"]==t]; am = comp[comp["strAwayTeam"]==t]
                    if len(hm)==0 and len(am)==0: continue
                    h_pts = sum(3 if r["intHomeScore"]>r["intAwayScore"] else 1 if r["intHomeScore"]==r["intAwayScore"] else 0 for _,r in hm.iterrows())
                    a_pts = sum(3 if r["intAwayScore"]>r["intHomeScore"] else 1 if r["intAwayScore"]==r["intHomeScore"] else 0 for _,r in am.iterrows())
                    ha_data.append({"Team":t,"Home Pts":h_pts,"Away Pts":a_pts,"Home Played":len(hm),"Away Played":len(am),
                        "Home PPG":round(h_pts/max(len(hm),1),2),"Away PPG":round(a_pts/max(len(am),1),2),
                        "Home GF":hm["intHomeScore"].sum(),"Home GA":hm["intAwayScore"].sum(),
                        "Away GF":am["intAwayScore"].sum(),"Away GA":am["intHomeScore"].sum(),
                        "HA Diff":round(h_pts/max(len(hm),1)-a_pts/max(len(am),1),2)})
                if ha_data:
                    ha_df = pd.DataFrame(ha_data).sort_values("HA Diff",ascending=False)
                    fig = px.bar(ha_df.head(20), x=["Home PPG","Away PPG"], y="Team", barmode="group", orientation="h",
                        title="Home vs Away PPG (Top 20 Home Advantage)", color_discrete_sequence=["#2ca02c","#d62728"])
                    fig.update_layout(template="plotly_white",height=600); st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(ha_df[["Team","Home PPG","Away PPG","HA Diff","Home GF","Home GA","Away GF","Away GA"]].head(30), use_container_width=True, hide_index=True)

        with tac_tabs[1]:
            st.subheader(" Scoring Patterns by Round")
            if not f_events.empty and "intRound" in f_events.columns:
                comp = f_events.dropna(subset=["intHomeScore","intAwayScore","intRound"]).copy()
                comp["total"] = comp["intHomeScore"].astype(int)+comp["intAwayScore"].astype(int)
                by_rd = comp.groupby("intRound")["total"].mean().reset_index()
                by_rd.columns = ["Round","Avg Goals"]
                fig = px.line(by_rd, x="Round", y="Avg Goals", title="Average Goals per Round", markers=True)
                fig.update_layout(template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)

                # Team goals by round
                tac_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="tac_lg")
                tac_team = st.selectbox("Team", f_standings[f_standings["league"]==tac_lg]["strTeam"].tolist(), key="tac_team")
                tm = comp[(comp["strHomeTeam"]==tac_team)|(comp["strAwayTeam"]==tac_team)].copy()
                tm["gf"] = np.where(tm["strHomeTeam"]==tac_team, tm["intHomeScore"], tm["intAwayScore"]).astype(int)
                tm["ga"] = np.where(tm["strHomeTeam"]==tac_team, tm["intAwayScore"], tm["intHomeScore"]).astype(int)
                if not tm.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=tm["intRound"],y=tm["gf"],name="Goals Scored",marker_color="#2ca02c"))
                    fig.add_trace(go.Bar(x=tm["intRound"],y=-tm["ga"],name="Goals Conceded",marker_color="#d62728"))
                    fig.update_layout(title=f"{tac_team}  Goals by Round",barmode="relative",template="plotly_white",height=400)
                    st.plotly_chart(fig, use_container_width=True)

        with tac_tabs[2]:
            st.subheader(" Expected Goals (xG) Model")
            if not f_standings.empty:
                xg_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="xg_lg")
                xg_df = f_standings[f_standings["league"]==xg_lg].copy()
                xg_df["gf_rate"] = xg_df["intGoalsFor"]/xg_df["intPlayed"].clip(lower=1)
                xg_df["ga_rate"] = xg_df["intGoalsAgainst"]/xg_df["intPlayed"].clip(lower=1)
                avg_gf = xg_df["gf_rate"].mean()
                xg_df["atk_str"] = (xg_df["gf_rate"]/max(avg_gf,0.01)).round(2)
                xg_df["def_str"] = (xg_df["ga_rate"]/max(avg_gf,0.01)).round(2)

                xpts_data = []
                for _,r in xg_df.iterrows():
                    gf,ga = r["gf_rate"],r["ga_rate"]
                    pw = sum(poisson.pmf(g1,gf)*sum(poisson.pmf(g2,ga) for g2 in range(g1)) for g1 in range(8))
                    pd_p = sum(poisson.pmf(g,gf)*poisson.pmf(g,ga) for g in range(8))
                    xpts = (pw*3+pd_p)*r["intPlayed"]
                    xpts_data.append({"Team":r["strTeam"],"Atk Str":r["atk_str"],"Def Str":r["def_str"],
                        "Actual":int(r["intPoints"]),"xPts":round(xpts,1),"Over/Under":round(r["intPoints"]-xpts,1)})
                xpt_df = pd.DataFrame(xpts_data).sort_values("Over/Under",ascending=False)

                fig = px.scatter(xpt_df, x="Atk Str", y="Def Str", color="Over/Under", hover_name="Team",
                    size="Actual", size_max=25, color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                    title=f"{xg_lg}  Attack vs Defense Strength (bubble = points)")
                fig.add_hline(y=1,line_dash="dash",opacity=0.3); fig.add_vline(x=1,line_dash="dash",opacity=0.3)
                fig.update_layout(template="plotly_white",height=500); st.plotly_chart(fig, use_container_width=True)
                st.dataframe(xpt_df, use_container_width=True, hide_index=True)

        with tac_tabs[3]:
            st.subheader(" Squad Formation Estimator")
            st.caption("Estimates likely formation from squad composition and position distribution")
            if not _ap.empty:
                fe_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="fe_lg")
                fe_teams = sorted(_ap[_ap["league"]==fe_lg]["_teamName"].dropna().unique().tolist())
                fe_team = st.selectbox("Team", fe_teams, key="fe_team") if fe_teams else None
                if fe_team:
                    sq = _ap[(_ap["_teamName"]==fe_team)&(_ap["league"]==fe_lg)]
                    pc = sq["pos_group"].value_counts()
                    d_cnt = pc.get("DEF",0); m_cnt = pc.get("MID",0); a_cnt = pc.get("ATT",0)
                    formations = {"4-3-3":(4,3,3),"4-4-2":(4,4,2),"3-5-2":(3,5,2),"4-2-3-1":(4,5,1),"3-4-3":(3,4,3),"5-3-2":(5,3,2),"4-1-4-1":(4,5,1)}
                    best_f, best_s = "4-4-2", 999
                    for f,(d,m,a) in formations.items():
                        score = abs(d-d_cnt)+abs(m-m_cnt)+abs(a-a_cnt)
                        if score < best_s: best_f, best_s = f, score
                    st.markdown(f"**Estimated Primary Formation: {best_f}**")
                    st.markdown(f"Squad: {pc.get('GK',0)} GK  {d_cnt} DEF  {m_cnt} MID  {a_cnt} ATT")
                    fig = px.bar(x=["GK","DEF","MID","ATT"], y=[pc.get("GK",0),d_cnt,m_cnt,a_cnt],
                        color=["GK","DEF","MID","ATT"], title=f"{fe_team} Squad Composition")
                    fig.update_layout(template="plotly_white",height=350,showlegend=False); st.plotly_chart(fig, use_container_width=True)

        with tac_tabs[4]:
            st.subheader(" Momentum Tracker")
            if not f_events.empty and "intRound" in f_events.columns:
                mo_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="mo_lg")
                mo_teams = f_standings[f_standings["league"]==mo_lg]["strTeam"].tolist()
                mo_sel = st.multiselect("Teams", mo_teams, default=mo_teams[:3], key="mo_sel")
                comp = f_events.dropna(subset=["intHomeScore","intAwayScore","intRound"]).copy()
                comp["intHomeScore"]=comp["intHomeScore"].astype(int); comp["intAwayScore"]=comp["intAwayScore"].astype(int)
                if mo_sel:
                    fig = go.Figure()
                    for t in mo_sel:
                        tm = comp[(comp["strHomeTeam"]==t)|(comp["strAwayTeam"]==t)].sort_values("intRound")
                        pts_list = []
                        for _,r in tm.iterrows():
                            if r["strHomeTeam"]==t: p = 3 if r["intHomeScore"]>r["intAwayScore"] else 1 if r["intHomeScore"]==r["intAwayScore"] else 0
                            else: p = 3 if r["intAwayScore"]>r["intHomeScore"] else 1 if r["intAwayScore"]==r["intHomeScore"] else 0
                            pts_list.append(p)
                        cum = np.cumsum(pts_list)
                        fig.add_trace(go.Scatter(x=list(range(1,len(cum)+1)),y=cum,name=t,mode="lines+markers"))
                    fig.update_layout(title="Cumulative Points Over Season",xaxis_title="Match",yaxis_title="Points",template="plotly_white",height=500)
                    st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Opponent Report
# 
elif page == " Opponent Report":
    st.title(" Pre-Match Opponent Report")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Opponent Report** generates pre-match intelligence.

1. Select the **league**, then pick **Your Team** and the **Opponent**
2. The system generates:
   - A **radar chart** comparing both teams' strengths (attack, defense, form, etc.)
   - **Identified weaknesses** of the opponent you can exploit
   - A **match prediction** with win/draw/loss probabilities
   - **Squad comparison** metrics (average age, depth, value)

Tip: Use this before every match to prepare a tactical briefing.
""")
    if f_standings.empty or f_events.empty: st.warning("No data.")
    else:
        opp_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="opp_lg")
        lg_teams = f_standings[f_standings["league"]==opp_lg]["strTeam"].tolist()
        oc1,oc2 = st.columns(2)
        with oc1: your_team = st.selectbox("Your Team", lg_teams, key="opp_your")
        with oc2: opp_team = st.selectbox("Opponent", [t for t in lg_teams if t!=your_team], key="opp_opp")

        yr = f_standings[f_standings["strTeam"]==your_team].iloc[0]
        opr = f_standings[f_standings["strTeam"]==opp_team].iloc[0]

        st.subheader(f" {your_team} vs {opp_team}")
        mc = st.columns(6)
        mc[0].metric("Your Rank", f"#{int(yr['intRank'])}")
        mc[1].metric("Your Points", int(yr["intPoints"]))
        mc[2].metric("Your GD", int(yr["intGoalDifference"]))
        mc[3].metric("Opp Rank", f"#{int(opr['intRank'])}")
        mc[4].metric("Opp Points", int(opr["intPoints"]))
        mc[5].metric("Opp GD", int(opr["intGoalDifference"]))

        # Strength comparison radar
        y_played = max(int(yr["intPlayed"]),1); o_played = max(int(opr["intPlayed"]),1)
        cats = ["PPG","GF/M","GA/M","Win %","Clean Sheet Rate"]
        comp = f_events.dropna(subset=["intHomeScore","intAwayScore"]).copy()
        comp["intHomeScore"]=comp["intHomeScore"].astype(int); comp["intAwayScore"]=comp["intAwayScore"].astype(int)

        def _team_stats(team, standings_row, events_df):
            played = max(int(standings_row["intPlayed"]),1)
            ppg = standings_row["intPoints"]/played
            gf_m = standings_row["intGoalsFor"]/played
            ga_m = standings_row["intGoalsAgainst"]/played
            win_pct = standings_row["intWin"]/played*100
            tm = events_df[(events_df["strHomeTeam"]==team)|(events_df["strAwayTeam"]==team)]
            cs = 0
            for _,r in tm.iterrows():
                if r["strHomeTeam"]==team and r["intAwayScore"]==0: cs+=1
                elif r["strAwayTeam"]==team and r["intHomeScore"]==0: cs+=1
            cs_rate = cs/max(len(tm),1)*100
            return [ppg, gf_m, ga_m, win_pct, cs_rate]

        y_vals = _team_stats(your_team, yr, comp)
        o_vals = _team_stats(opp_team, opr, comp)

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=y_vals+[y_vals[0]], theta=cats+[cats[0]], name=your_team, fill="toself"))
        fig.add_trace(go.Scatterpolar(r=o_vals+[o_vals[0]], theta=cats+[cats[0]], name=opp_team, fill="toself"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True)),template="plotly_white",height=450,title="Strength Comparison")
        st.plotly_chart(fig, use_container_width=True)

        # Opponent weaknesses
        st.subheader(" Opponent Analysis")
        weaknesses = []
        if o_vals[2] > 1.5: weaknesses.append(" **Defensive vulnerability**  conceding {:.2f} goals/match".format(o_vals[2]))
        if o_vals[4] < 20: weaknesses.append(" **Rarely keeps clean sheets**  {:.0f}% rate".format(o_vals[4]))
        if o_vals[1] < 1.0: weaknesses.append(" **Low scoring threat**  only {:.2f} goals/match".format(o_vals[1]))
        opp_away = comp[comp["strAwayTeam"]==opp_team]
        if len(opp_away)>0:
            away_ppg = sum(3 if r["intAwayScore"]>r["intHomeScore"] else 1 if r["intAwayScore"]==r["intHomeScore"] else 0 for _,r in opp_away.iterrows())/len(opp_away)
            if away_ppg < 1.0: weaknesses.append(f" **Poor away form**  {away_ppg:.2f} PPG on the road")
        if not weaknesses: weaknesses.append(" No significant weaknesses identified  strong opponent!")
        for w in weaknesses: st.markdown(w)

        # Match prediction
        st.subheader(" Match Prediction")
        h_xg = y_vals[1]*(o_vals[2]/max(o_vals[1],0.01))*1.1
        a_xg = o_vals[1]*(y_vals[2]/max(y_vals[1],0.01))*0.9
        h_xg = max(0.1,min(h_xg,5)); a_xg = max(0.1,min(a_xg,5))
        p_hw = sum(poisson.pmf(g1,h_xg)*sum(poisson.pmf(g2,a_xg) for g2 in range(g1)) for g1 in range(1,8))
        p_d = sum(poisson.pmf(g,h_xg)*poisson.pmf(g,a_xg) for g in range(8))
        p_aw = max(0,1-p_hw-p_d)
        tp = p_hw+p_d+p_aw; p_hw/=tp; p_d/=tp; p_aw/=tp
        pc1,pc2,pc3 = st.columns(3)
        pc1.metric(f"{your_team} Win", f"{p_hw*100:.1f}%")
        pc2.metric("Draw", f"{p_d*100:.1f}%")
        pc3.metric(f"{opp_team} Win", f"{p_aw*100:.1f}%")
        st.caption(f"xG: {your_team} {h_xg:.2f}  {opp_team} {a_xg:.2f}")

        # Squad comparison
        if not _ap.empty:
            st.subheader(" Squad Comparison")
            sq_y = _find_squad(your_team, _ap, opp_lg)
            sq_o = _find_squad(opp_team, _ap, opp_lg)
            if not sq_y.empty and not sq_o.empty:
                comp_data = {"Metric":[your_team, opp_team],
                    "Squad Size":[len(sq_y),len(sq_o)],
                    "Avg Age":[round(sq_y["age"].mean(),1),round(sq_o["age"].mean(),1)],
                    "Total Value (M)":[round(sq_y["est_value"].sum(),1),round(sq_o["est_value"].sum(),1)],
                    "Avg Value (M)":[round(sq_y["est_value"].mean(),1),round(sq_o["est_value"].mean(),1)]}
                st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)


# 
# PAGE: Transfer Recommendations
# 
elif page == " Transfer Recommendations":
    st.title(" Transfer Recommendation Engine")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Transfer Recommendations** helps plan your transfer window.

- **Squad Audit**: See your current squad composition, average age, and total value
- **Transfer Needs**: The system identifies weak positions and suggests targets from other leagues
- **Players to Sell**: Flags aging or surplus players that could be sold to free budget
- **Cross-League Scout**: Finds the best value-for-money players across all 15 leagues for each position

Tip: Compare Transfer Needs with Cross-League Scout to find affordable solutions for your weak spots.
""")
    if f_standings.empty: st.warning("No data.")
    else:
        tr_tabs = st.tabs([" Squad Audit"," Transfer Needs"," Players to Sell"," Cross-League Scout"])
        with tr_tabs[0]:
            st.subheader(" Club Squad Audit")
            tr_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="aud_lg")
            lg_st = f_standings[f_standings["league"]==tr_lg].sort_values("intRank")
            sel_t = st.selectbox("Team", lg_st["strTeam"].tolist(), key="aud_t")
            tr = lg_st[lg_st["strTeam"]==sel_t].iloc[0]
            tp = max(int(tr["intPlayed"]),1)
            m1,m2,m3,m4,m5 = st.columns(5)
            m1.metric("Rank",f"#{int(tr['intRank'])}"); m2.metric("Points",int(tr["intPoints"])); m3.metric("PPG",f"{tr['intPoints']/tp:.2f}")
            m4.metric("GF/M",f"{tr['intGoalsFor']/tp:.2f}"); m5.metric("GA/M",f"{tr['intGoalsAgainst']/tp:.2f}")
            squad = _find_squad(sel_t, _ap, tr_lg)
            if squad.empty: st.info(f"No player data for {sel_t}.")
            else:
                tv = squad["est_value"].sum(); aa = squad["age"].mean()
                st.markdown(f"**Squad:** {len(squad)} players  **Value:** {tv:.1f}M  **Avg Age:** {aa:.1f}")
                sc1,sc2 = st.columns(2)
                with sc1:
                    pc = squad.groupby("pos_group").agg(Count=("strPlayer","count"),Avg_Age=("age","mean"),Value=("est_value","sum")).reindex(["GK","DEF","MID","ATT"]).fillna(0)
                    pc["Avg_Age"]=pc["Avg_Age"].round(1); pc["Value"]=pc["Value"].round(1)
                    pc.columns=["Players","Avg Age","Value (M)"]; st.dataframe(pc, use_container_width=True)
                with sc2:
                    fig = px.pie(names=["GK","DEF","MID","ATT"],values=[pc.loc[g,"Players"] if g in pc.index else 0 for g in ["GK","DEF","MID","ATT"]],title="Composition")
                    fig.update_layout(height=300,margin=dict(t=40,b=10)); st.plotly_chart(fig, use_container_width=True)
                squad["age_bucket"] = pd.cut(squad["age"],[15,21,24,28,31,40],labels=["U21","21-24","25-28","29-31","32+"])
                ad = squad["age_bucket"].value_counts().reindex(["U21","21-24","25-28","29-31","32+"]).fillna(0)
                fig = px.bar(x=ad.index,y=ad.values,color=ad.index,title="Age Profile")
                fig.update_layout(template="plotly_white",height=300,showlegend=False); st.plotly_chart(fig, use_container_width=True)

        with tr_tabs[1]:
            st.subheader(" Transfer Needs & Targets")
            tr2_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="n_lg")
            lg2 = f_standings[f_standings["league"]==tr2_lg].sort_values("intRank")
            sel2 = st.selectbox("Team", lg2["strTeam"].tolist(), key="n_t")
            t2 = lg2[lg2["strTeam"]==sel2].iloc[0]
            lm2 = LEAGUE_MARKET.get(tr2_lg,20)
            budget = st.slider(" Budget (M)", 0.5, float(max(lm2*5,1)), float(min(lm2*0.75,10)), 0.5, key="n_b")
            lg2["gf_pm"]=lg2["intGoalsFor"]/lg2["intPlayed"].clip(lower=1); lg2["ga_pm"]=lg2["intGoalsAgainst"]/lg2["intPlayed"].clip(lower=1)
            t2_gf=t2["intGoalsFor"]/max(t2["intPlayed"],1); t2_ga=t2["intGoalsAgainst"]/max(t2["intPlayed"],1)
            top3=lg2.head(3); atk_gap=t2_gf-top3["gf_pm"].mean(); def_gap=top3["ga_pm"].mean()-t2_ga
            needs = []
            if atk_gap<-0.3: needs.append({"Position":"Striker/Forward","Priority":" HIGH","Reason":f"Scoring gap: {abs(atk_gap):.2f}","pos_targets":["ATT"]})
            elif atk_gap<-0.1: needs.append({"Position":"Winger/AM","Priority":" MED","Reason":f"Attack gap: {abs(atk_gap):.2f}","pos_targets":["ATT","MID"]})
            if def_gap<-0.3: needs.append({"Position":"CB/DM","Priority":" HIGH","Reason":f"Defense gap: {abs(def_gap):.2f}","pos_targets":["DEF"]})
            elif def_gap<-0.1: needs.append({"Position":"FB/DM","Priority":" MED","Reason":f"Def gap: {abs(def_gap):.2f}","pos_targets":["DEF","MID"]})
            sq2 = _find_squad(sel2, _ap, tr2_lg)
            if not sq2.empty:
                for grp,(lo,hi) in ideal_comp.items():
                    cnt = len(sq2[sq2["pos_group"]==grp]); ga = sq2[sq2["pos_group"]==grp]["age"].mean() if cnt>0 else 0
                    if cnt<lo: needs.append({"Position":f"{grp} player","Priority":" HIGH","Reason":f"Only {cnt} (need {lo}-{hi})","pos_targets":[grp]})
                    elif ga>30: needs.append({"Position":f"Young {grp}","Priority":" MED","Reason":f"Avg age {ga:.1f}","pos_targets":[grp]})
            if not needs: needs.append({"Position":"Depth","Priority":" LOW","Reason":"Team OK","pos_targets":["ATT","MID","DEF"]})
            st.dataframe(pd.DataFrame(needs)[["Priority","Position","Reason"]], use_container_width=True, hide_index=True)
            if not _ap.empty:
                st.markdown("---"); st.subheader(" Recommended Targets")
                tgt_lgs = [lg for lg,v in LEAGUE_MARKET.items() if v<=lm2*1.2]
                if tr2_lg not in tgt_lgs: tgt_lgs.append(tr2_lg)
                all_tgt = []
                for n in needs:
                    c = _ap[(_ap["pos_group"].isin(n["pos_targets"]))&(_ap["league"].isin(tgt_lgs))&(_ap["est_value"]<=budget)&(_ap["est_value"]>0.01)].copy()
                    c = c[(c["_teamName"]!=sel2)&(c.get("strTeam","")!=sel2)]
                    if "age" in c.columns: c["_p"]=c["age"].between(21,29).astype(int)
                    else: c["_p"]=0
                    c = c.sort_values(["_p","est_value"],ascending=[False,False]).head(5)
                    for _,r in c.iterrows():
                        all_tgt.append({"Need":n["Position"],"Player":r.get("strPlayer","?"),"Position":r.get("strPosition","?"),"Age":r.get("age","?"),"Club":r.get("_teamName","?"),"League":r.get("league","?"),"Value (M)":r.get("est_value",0)})
                if all_tgt:
                    tdf = pd.DataFrame(all_tgt); st.dataframe(tdf, use_container_width=True, hide_index=True)

        with tr_tabs[2]:
            st.subheader(" Players to Sell")
            tr3_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="s_lg")
            lg3 = f_standings[f_standings["league"]==tr3_lg].sort_values("intRank")
            sel3 = st.selectbox("Team", lg3["strTeam"].tolist(), key="s_t")
            sq3 = _find_squad(sel3, _ap, tr3_lg)
            if sq3.empty: st.info(f"No data for {sel3}.")
            else:
                pc3 = sq3["pos_group"].value_counts()
                sq3["_surplus"] = sq3["pos_group"].map(lambda g: 1 if pc3.get(g,0)>ideal_comp.get(g,(0,99))[1] else 0)
                sq3["_aging"] = (sq3["age"]>30).astype(int)
                sq3["sell_score"] = sq3["_aging"]*2+sq3["_surplus"]*1.5+(sq3["est_value"]>sq3["est_value"].quantile(0.7)).astype(int)
                sell = sq3.sort_values("sell_score",ascending=False).head(8)
                sd = sell[["strPlayer","strPosition","age","strNationality","est_value"]].copy()
                sd.columns = ["Player","Position","Age","Nationality","Value (M)"]
                st.dataframe(sd, use_container_width=True, hide_index=True)
                st.success(f"**Potential revenue:** {sd['Value (M)'].sum():.1f}M")

        with tr_tabs[3]:
            st.subheader(" Cross-League Scout")
            if _ap.empty: st.info("No player data.")
            else:
                sc1,sc2,sc3 = st.columns(3)
                with sc1: sp = st.selectbox("Position", ["All","GK","DEF","MID","ATT"], key="cls_p")
                with sc2: sa = st.slider("Max Age", 18, 40, 29, key="cls_a")
                with sc3: sb = st.slider("Max Value (M)", 0.5, 200.0, 20.0, 0.5, key="cls_v")
                sd = _ap.copy()
                if sp!="All": sd = sd[sd["pos_group"]==sp]
                sd = sd[(sd["age"]<=sa)&(sd["est_value"]<=sb)]
                sd["vs"] = sd["est_value"]/(sd["age"]-16).clip(lower=1)*10
                sd = sd.sort_values("vs",ascending=False)
                disp = sd.head(30)[["strPlayer","strPosition","age","strNationality","_teamName","league","est_value"]].copy()
                disp.columns = ["Player","Position","Age","Nationality","Club","League","Value (M)"]
                st.dataframe(disp, use_container_width=True, hide_index=True)
                if len(sd)>0:
                    fig = px.scatter(disp, x="Age", y="Value (M)", color="League", hover_name="Player", size="Value (M)", size_max=25, title="Scouting Map")
                    fig.update_layout(template="plotly_white",height=500); st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Physical & Medical
# 
elif page == " Physical & Medical":
    st.title(" Physical & Medical Dashboard")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Physical & Medical** monitors fitness risk and workload.

- **Squad Fitness Profile**: Maps players by age vs position to estimate physical risk zones
- **Injury Risk Assessment**: Scores each squad position based on age, depth, and workload factors
- **Fixture Congestion**: Analyzes spacing between matches -- flags periods where fatigue risk is highest
- **Rotation Planner**: Recommends positions that need more squad depth for safe rotation

Tip: Check Fixture Congestion before busy periods (cup + league matches) to plan rotation ahead.
""")
    if _ap.empty: st.warning("No player data.")
    else:
        pm_tabs = st.tabs([" Squad Fitness Profile"," Injury Risk Assessment"," Fixture Congestion"," Rotation Planner"])

        with pm_tabs[0]:
            st.subheader(" Squad Fitness Profile")
            pm_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="pm_lg")
            pm_teams = sorted(_ap[_ap["league"]==pm_lg]["_teamName"].dropna().unique().tolist())
            pm_team = st.selectbox("Team", pm_teams, key="pm_t") if pm_teams else None
            if pm_team:
                sq = _ap[(_ap["_teamName"]==pm_team)&(_ap["league"]==pm_lg)].copy()
                sq["fitness_risk"] = np.where(sq["age"]>32, " High", np.where(sq["age"]>29, " Medium", " Low"))
                c1,c2,c3 = st.columns(3)
                c1.metric("Squad Size", len(sq))
                c2.metric("Avg Age", f"{sq['age'].mean():.1f}")
                c3.metric("Over 30", len(sq[sq["age"]>30]))

                fig = px.scatter(sq, x="age", y="est_value", color="fitness_risk", hover_name="strPlayer",
                    hover_data=["strPosition","strNationality"], size="est_value", size_max=20,
                    title=f"{pm_team}  Squad Fitness Risk Map", color_discrete_map={" High":"red"," Medium":"orange"," Low":"green"})
                fig.update_layout(template="plotly_white",height=450); st.plotly_chart(fig, use_container_width=True)

                st.markdown("**Squad by Fitness Risk Category**")
                for risk in [" High"," Medium"," Low"]:
                    rdf = sq[sq["fitness_risk"]==risk]
                    if not rdf.empty:
                        st.markdown(f"**{risk}** ({len(rdf)} players)")
                        disp = rdf[["strPlayer","strPosition","age","est_value"]].copy()
                        disp.columns = ["Player","Position","Age","Value (M)"]
                        st.dataframe(disp.sort_values("Age",ascending=False), use_container_width=True, hide_index=True)

        with pm_tabs[1]:
            st.subheader(" Injury Risk Assessment")
            st.caption("Based on age profile, position demands, and squad depth")
            ir_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="ir_lg")
            ir_teams = sorted(_ap[_ap["league"]==ir_lg]["_teamName"].dropna().unique().tolist())
            ir_team = st.selectbox("Team", ir_teams, key="ir_t") if ir_teams else None
            if ir_team:
                sq = _ap[(_ap["_teamName"]==ir_team)&(_ap["league"]==ir_lg)].copy()
                # Risk factors: age>30 (1.5x), ATT/MID (1.3x vs DEF/GK), thin position depth
                pc = sq["pos_group"].value_counts()
                sq["age_risk"] = np.where(sq["age"]>32,3, np.where(sq["age"]>29,2, np.where(sq["age"]>27,1,0.5)))
                sq["pos_risk"] = sq["pos_group"].map({"ATT":1.3,"MID":1.2,"DEF":1.0,"GK":0.8})
                sq["depth_risk"] = sq["pos_group"].map(lambda g: 2 if pc.get(g,0)<ideal_comp.get(g,(0,99))[0] else 0.5)
                sq["injury_risk_score"] = (sq["age_risk"]*sq["pos_risk"]*sq["depth_risk"]).round(1)
                sq = sq.sort_values("injury_risk_score",ascending=False)
                disp = sq[["strPlayer","strPosition","age","pos_group","injury_risk_score"]].head(15).copy()
                disp.columns = ["Player","Position","Age","Group","Risk Score"]
                fig = px.bar(disp, x="Risk Score", y="Player", orientation="h", color="Risk Score", color_continuous_scale="YlOrRd", title=f"{ir_team}  Injury Risk Ranking")
                fig.update_layout(template="plotly_white",height=max(300,len(disp)*35),showlegend=False); st.plotly_chart(fig, use_container_width=True)
                st.dataframe(disp, use_container_width=True, hide_index=True)

        with pm_tabs[2]:
            st.subheader(" Fixture Congestion Analysis")
            if not f_events.empty and "dateEvent" in f_events.columns:
                fc_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="fc_lg")
                fc_teams = f_standings[f_standings["league"]==fc_lg]["strTeam"].tolist()
                fc_team = st.selectbox("Team", fc_teams, key="fc_t")
                tm_ev = f_events[(f_events["strHomeTeam"]==fc_team)|(f_events["strAwayTeam"]==fc_team)].copy()
                tm_ev = tm_ev.dropna(subset=["dateEvent"]).sort_values("dateEvent")
                if len(tm_ev)>1:
                    tm_ev["days_between"] = tm_ev["dateEvent"].diff().dt.days
                    avg_gap = tm_ev["days_between"].mean()
                    min_gap = tm_ev["days_between"].min()
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Total Matches", len(tm_ev))
                    c2.metric("Avg Days Between", f"{avg_gap:.1f}")
                    c3.metric("Min Gap (days)", f"{min_gap:.0f}" if pd.notna(min_gap) else "N/A")
                    fig = px.line(tm_ev.iloc[1:], x="dateEvent", y="days_between", title=f"{fc_team}  Days Between Matches", markers=True)
                    fig.add_hline(y=3,line_dash="dash",line_color="red",annotation_text="High Risk (<3 days)")
                    fig.add_hline(y=7,line_dash="dash",line_color="green",annotation_text="Optimal (7+ days)")
                    fig.update_layout(template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)
                else: st.info("Not enough matches for analysis.")
            else: st.info("No event data with dates.")

        with pm_tabs[3]:
            st.subheader(" Squad Rotation Planner")
            st.caption("Recommended rotation based on squad depth and fixture density")
            if not _ap.empty:
                rp_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="rp_lg")
                rp_teams = sorted(_ap[_ap["league"]==rp_lg]["_teamName"].dropna().unique().tolist())
                rp_team = st.selectbox("Team", rp_teams, key="rp_t") if rp_teams else None
                if rp_team:
                    sq = _ap[(_ap["_teamName"]==rp_team)&(_ap["league"]==rp_lg)].copy()
                    for grp in ["GK","DEF","MID","ATT"]:
                        grp_df = sq[sq["pos_group"]==grp].sort_values("est_value",ascending=False)
                        cnt = len(grp_df)
                        lo,hi = ideal_comp[grp]
                        status = " OK" if lo<=cnt<=hi else " Thin" if cnt<lo else " Can rotate"
                        st.markdown(f"**{grp}**: {cnt} players ({status})")
                        if not grp_df.empty:
                            disp = grp_df[["strPlayer","strPosition","age","est_value"]].copy()
                            disp.columns = ["Player","Position","Age","Value (M)"]
                            st.dataframe(disp, use_container_width=True, hide_index=True)


# 
# PAGE: Youth Academy
# 
elif page == " Youth Academy":
    st.title(" Youth Academy & Development Pipeline")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Youth Academy** tracks young talent development.

- **U21 Tracker**: Lists all players under 21 by club -- see which teams invest in youth
- **Development Potential**: Scores young players on a growth ceiling metric (younger + higher value = more potential)
- **Academy Comparison**: Compares youth squad strength across all clubs
- **Youth Nationality Map**: Shows where young talent originates geographically

Tip: Use Development Potential to identify which youngsters deserve first-team opportunities.
""")
    if _ap.empty: st.warning("No player data.")
    else:
        ya_tabs = st.tabs([" U21 Tracker"," Development Potential"," Academy Comparison"," Youth Nationality Map"])

        with ya_tabs[0]:
            st.subheader(" U21 Player Tracker")
            ya_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="ya_lg")
            u21 = _ap[(_ap["league"]==ya_lg)&(_ap["age"]<=21)].copy()
            st.markdown(f"**{len(u21)} U21 players** in {ya_lg}")
            if not u21.empty:
                c1,c2 = st.columns(2)
                with c1:
                    by_team = u21.groupby("_teamName").size().sort_values(ascending=True).tail(15).reset_index()
                    by_team.columns = ["Team","U21 Players"]
                    fig = px.bar(by_team, x="U21 Players", y="Team", orientation="h", title="U21 Players by Team", color="U21 Players", color_continuous_scale="Greens")
                    fig.update_layout(template="plotly_white",height=400,showlegend=False); st.plotly_chart(fig, use_container_width=True)
                with c2:
                    by_pos = u21["pos_group"].value_counts().reset_index(); by_pos.columns=["Position","Count"]
                    fig = px.pie(by_pos, names="Position", values="Count", title="U21 by Position", hole=0.4)
                    fig.update_layout(template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)
                disp = u21[["strPlayer","strPosition","age","strNationality","_teamName","est_value"]].sort_values("est_value",ascending=False).head(30).copy()
                disp.columns = ["Player","Position","Age","Nationality","Club","Value (M)"]
                st.dataframe(disp, use_container_width=True, hide_index=True)

        with ya_tabs[1]:
            st.subheader(" Development Potential Score")
            st.caption("Higher score = greater development ceiling based on age, current value, and position scarcity")
            dp_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="dp_lg")
            young = _ap[(_ap["league"]==dp_lg)&(_ap["age"]<=23)].copy()
            if young.empty: st.info("No young players found.")
            else:
                young["potential"] = ((25-young["age"])*young["est_value"]*2/(young["age"]-15).clip(lower=1)).round(1)
                young = young.sort_values("potential",ascending=False)
                top = young.head(20)
                fig = px.bar(top, x="potential", y="strPlayer", orientation="h", color="pos_group", title=f"Top Development Potential  {dp_lg}",
                    hover_data=["_teamName","age","est_value"], labels={"potential":"Potential Score","strPlayer":"Player"})
                fig.update_layout(template="plotly_white",height=max(400,len(top)*35),showlegend=True); st.plotly_chart(fig, use_container_width=True)

        with ya_tabs[2]:
            st.subheader(" Academy Strength Comparison")
            ac_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="ac_lg")
            u23 = _ap[(_ap["league"]==ac_lg)&(_ap["age"]<=23)].copy()
            if not u23.empty:
                ac_data = u23.groupby("_teamName").agg(U23_Count=("strPlayer","count"),Avg_Age=("age","mean"),Total_Value=("est_value","sum"),Avg_Value=("est_value","mean")).reset_index()
                ac_data.columns = ["Team","U23 Players","Avg Age","Total Value (M)","Avg Value (M)"]
                ac_data = ac_data.round(1).sort_values("Total Value (M)",ascending=False)
                fig = px.scatter(ac_data, x="U23 Players", y="Total Value (M)", size="Avg Value (M)", color="Avg Age",
                    hover_name="Team", size_max=25, color_continuous_scale="RdYlGn_r", title="Academy Strength  Youth Players vs Value")
                fig.update_layout(template="plotly_white",height=450); st.plotly_chart(fig, use_container_width=True)
                st.dataframe(ac_data, use_container_width=True, hide_index=True)

        with ya_tabs[3]:
            st.subheader(" Youth Nationality Distribution")
            u21_all = _ap[_ap["age"]<=21].copy()
            if not u21_all.empty:
                nat = u21_all["strNationality"].value_counts().head(25).reset_index(); nat.columns=["Nationality","U21 Players"]
                fig = px.bar(nat, x="U21 Players", y="Nationality", orientation="h", color="U21 Players", color_continuous_scale="Viridis", title="Top 25 Youth Talent Nationalities")
                fig.update_layout(template="plotly_white",height=600,showlegend=False); st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Financial Analysis
# 
elif page == " Financial Analysis":
    st.title(" Financial Analysis & FFP Monitor")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Financial Analysis** covers squad economics and fair play compliance.

- **Squad Valuation**: Total estimated market value for each club
- **Wage Analysis**: How value is distributed across positions (GK, DEF, MID, ATT)
- **Transfer ROI**: Points earned per million in squad value -- measures efficiency
- **FFP Compliance**: Flags clubs with risky value concentration (too much investment in one area)

Tip: Clubs with high Transfer ROI are getting more from less -- study their approach.
""")
    if _ap.empty and f_standings.empty: st.warning("No data.")
    else:
        fin_tabs = st.tabs([" Squad Valuation"," Wage Analysis"," Transfer ROI"," FFP Compliance"])

        with fin_tabs[0]:
            st.subheader(" Squad Valuation by Club")
            if not _ap.empty:
                fin_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="fin_lg")
                lg_pl = _ap[_ap["league"]==fin_lg].copy()
                val_by_team = lg_pl.groupby("_teamName").agg(Squad_Value=("est_value","sum"),Squad_Size=("strPlayer","count"),Avg_Value=("est_value","mean"),Max_Value=("est_value","max"),Avg_Age=("age","mean")).reset_index()
                val_by_team.columns = ["Team","Squad Value (M)","Players","Avg Value (M)","Star Player (M)","Avg Age"]
                val_by_team = val_by_team.round(1).sort_values("Squad Value (M)",ascending=False)
                fig = px.bar(val_by_team, x="Squad Value (M)", y="Team", orientation="h", color="Avg Age", color_continuous_scale="RdYlGn_r", text="Squad Value (M)", title=f"{fin_lg}  Squad Values")
                fig.update_traces(texttemplate="%{text:.0f}M",textposition="outside"); fig.update_layout(template="plotly_white",height=max(400,len(val_by_team)*35),showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(val_by_team, use_container_width=True, hide_index=True)

                # Value vs Performance
                if not f_standings.empty:
                    st.subheader(" Value vs Performance")
                    merged = val_by_team.merge(f_standings[f_standings["league"]==fin_lg][["strTeam","intPoints","intRank"]].rename(columns={"strTeam":"Team"}), on="Team", how="left")
                    if not merged.empty:
                        fig = px.scatter(merged, x="Squad Value (M)", y="intPoints", hover_name="Team", size="Players",
                            color="intRank", color_continuous_scale="RdYlGn_r", title="Squad Value vs Points", text="Team")
                        fig.update_traces(textposition="top center",textfont_size=8)
                        fig.update_layout(template="plotly_white",height=500); st.plotly_chart(fig, use_container_width=True)

        with fin_tabs[1]:
            st.subheader(" Squad Value Distribution by Position")
            if not _ap.empty:
                wg_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="wg_lg")
                wg_teams = sorted(_ap[_ap["league"]==wg_lg]["_teamName"].dropna().unique().tolist())
                wg_team = st.selectbox("Team", wg_teams, key="wg_t") if wg_teams else None
                if wg_team:
                    sq = _ap[(_ap["_teamName"]==wg_team)&(_ap["league"]==wg_lg)].copy()
                    by_pos = sq.groupby("pos_group")["est_value"].agg(["sum","mean","count"]).reset_index()
                    by_pos.columns = ["Position","Total (M)","Avg (M)","Count"]
                    by_pos = by_pos.round(1)
                    fig = px.bar(by_pos, x="Position", y="Total (M)", color="Position", text="Total (M)", title=f"{wg_team}  Value by Position")
                    fig.update_traces(texttemplate="%{text:.1f}M"); fig.update_layout(template="plotly_white",height=350,showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                    # Top earners
                    top_val = sq.sort_values("est_value",ascending=False).head(10)
                    fig = px.bar(top_val, x="est_value", y="strPlayer", orientation="h", color="pos_group", title="Top 10 Most Valuable Players", text="est_value")
                    fig.update_traces(texttemplate="%{text:.1f}M",textposition="outside"); fig.update_layout(template="plotly_white",height=400)
                    st.plotly_chart(fig, use_container_width=True)

        with fin_tabs[2]:
            st.subheader(" Transfer Value vs Points Efficiency")
            if not _ap.empty and not f_standings.empty:
                roi_data = []
                for lg in _ap["league"].unique():
                    lg_p = _ap[_ap["league"]==lg].groupby("_teamName")["est_value"].sum().reset_index()
                    lg_p.columns = ["Team","Squad Value"]
                    lg_s = f_standings[f_standings["league"]==lg][["strTeam","intPoints"]].rename(columns={"strTeam":"Team"})
                    merged = lg_p.merge(lg_s, on="Team", how="inner")
                    merged["Pts per M"] = (merged["intPoints"]/merged["Squad Value"].clip(lower=0.1)).round(2)
                    merged["League"] = lg
                    roi_data.append(merged)
                if roi_data:
                    roi_df = pd.concat(roi_data)
                    top_roi = roi_df.sort_values("Pts per M",ascending=False).head(20)
                    fig = px.bar(top_roi, x="Pts per M", y="Team", orientation="h", color="League", title="Best Value  Points per M Squad Value", text="Pts per M")
                    fig.update_traces(texttemplate="%{text:.1f}",textposition="outside"); fig.update_layout(template="plotly_white",height=600)
                    st.plotly_chart(fig, use_container_width=True)

        with fin_tabs[3]:
            st.subheader(" FFP Compliance Estimator")
            st.caption("Simplified FFP check based on squad value, age profile, and league norms")
            if not _ap.empty:
                ffp_lg = st.selectbox("League", sorted(_ap["league"].dropna().unique().tolist()), key="ffp_lg")
                ffp_teams = sorted(_ap[_ap["league"]==ffp_lg]["_teamName"].dropna().unique().tolist())
                ffp_data = []
                for t in ffp_teams:
                    sq = _ap[(_ap["_teamName"]==t)&(_ap["league"]==ffp_lg)]
                    tv = sq["est_value"].sum(); aa = sq["age"].mean(); cnt = len(sq)
                    lm = LEAGUE_MARKET.get(ffp_lg,20)
                    ratio = tv/max(lm,1)*100
                    risk = " Low" if ratio<150 else " Medium" if ratio<250 else " High"
                    ffp_data.append({"Team":t,"Squad Value (M)":round(tv,1),"League Avg (M)":lm,"Value Ratio %":round(ratio,1),"FFP Risk":risk,"Avg Age":round(aa,1),"Squad Size":cnt})
                ffp_df = pd.DataFrame(ffp_data).sort_values("Value Ratio %",ascending=False)
                fig = px.bar(ffp_df, x="Value Ratio %", y="Team", orientation="h", color="FFP Risk", title=f"{ffp_lg}  FFP Risk Assessment",
                    color_discrete_map={" Low":"green"," Medium":"orange"," High":"red"})
                fig.update_layout(template="plotly_white",height=max(400,len(ffp_df)*30)); st.plotly_chart(fig, use_container_width=True)
                st.dataframe(ffp_df, use_container_width=True, hide_index=True)


# 
# PAGE: Season Projections
# 
elif page == " Season Projections":
    st.title(" Season Projections & ELO Ratings")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Season Projections** predicts how the season will end.

- **ELO Ratings**: A chess-style rating system applied to football -- higher = stronger team
- **Final Table Projection**: Extrapolates current points-per-game to predict the final standings
- **Points Trajectory**: Plots cumulative points throughout the season for all teams
- **Race Tracker**: Monitors the title race and relegation battle with projected thresholds

Tip: ELO ratings update after every match -- teams on winning streaks climb quickly.
""")
    if f_standings.empty: st.warning("No data.")
    else:
        proj_tabs = st.tabs([" ELO Ratings"," Final Table Projection"," Points Trajectory"," Race Tracker"])

        with proj_tabs[0]:
            st.subheader(" ELO Rating System")
            elo_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="elo_lg")
            lg_df = f_standings[f_standings["league"]==elo_lg].copy()
            # Compute ELO from results
            if not f_events.empty:
                lg_ev = f_events[f_events["league"]==elo_lg].dropna(subset=["intHomeScore","intAwayScore"]).sort_values("dateEvent") if "dateEvent" in f_events.columns else f_events[f_events["league"]==elo_lg].dropna(subset=["intHomeScore","intAwayScore"])
                elo = {t:1500 for t in lg_df["strTeam"]}
                K = 32
                for _,m in lg_ev.iterrows():
                    ht,at = m["strHomeTeam"],m["strAwayTeam"]
                    if ht not in elo: elo[ht]=1500
                    if at not in elo: elo[at]=1500
                    eh = 1/(1+10**((elo[at]-elo[ht])/400))
                    hs,as_ = int(m["intHomeScore"]),int(m["intAwayScore"])
                    sh = 1 if hs>as_ else 0.5 if hs==as_ else 0
                    elo[ht] += K*(sh-eh); elo[at] += K*((1-sh)-(1-eh))
                elo_df = pd.DataFrame(sorted(elo.items(), key=lambda x:-x[1]), columns=["Team","ELO"])
                elo_df["ELO"] = elo_df["ELO"].round(0).astype(int)
                fig = px.bar(elo_df, x="ELO", y="Team", orientation="h", color="ELO", color_continuous_scale="YlOrRd", text="ELO", title=f"{elo_lg}  ELO Ratings")
                fig.update_traces(textposition="outside"); fig.update_layout(template="plotly_white",height=max(400,len(elo_df)*35),showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(elo_df, use_container_width=True, hide_index=True)
            else: st.info("No match data for ELO calculation.")

        with proj_tabs[1]:
            st.subheader(" Projected Final Table")
            fp_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="fp_lg")
            fp_df = f_standings[f_standings["league"]==fp_lg].copy()
            rem_matches = st.slider("Remaining Matches", 0, 20, 8, key="fp_rem")
            fp_df["ppg"] = fp_df["intPoints"]/fp_df["intPlayed"].clip(lower=1)
            fp_df["projected_pts"] = (fp_df["intPoints"]+fp_df["ppg"]*rem_matches).round(0).astype(int)
            fp_df = fp_df.sort_values("projected_pts",ascending=False)
            fp_df["proj_rank"] = range(1,len(fp_df)+1)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=fp_df["strTeam"],y=fp_df["intPoints"],name="Current",marker_color="#1f77b4"))
            fig.add_trace(go.Bar(x=fp_df["strTeam"],y=fp_df["projected_pts"]-fp_df["intPoints"],name="Projected Gain",marker_color="#ff7f0e"))
            fig.update_layout(barmode="stack",title=f"Projected Final Points ({rem_matches} remaining)",template="plotly_white",height=450,xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            disp = fp_df[["proj_rank","strTeam","intPoints","ppg","projected_pts"]].copy()
            disp.columns = ["Proj Rank","Team","Current Pts","PPG","Projected Pts"]
            disp["PPG"] = disp["PPG"].round(2)
            st.dataframe(disp, use_container_width=True, hide_index=True)

        with proj_tabs[2]:
            st.subheader(" Points Trajectory Over Season")
            if not f_events.empty and "intRound" in f_events.columns:
                pt_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="pt_lg")
                pt_teams = f_standings[f_standings["league"]==pt_lg]["strTeam"].tolist()
                pt_sel = st.multiselect("Teams", pt_teams, default=pt_teams[:5], key="pt_sel")
                comp = f_events[(f_events["league"]==pt_lg)].dropna(subset=["intHomeScore","intAwayScore","intRound"]).copy()
                comp["intHomeScore"]=comp["intHomeScore"].astype(int); comp["intAwayScore"]=comp["intAwayScore"].astype(int)
                if pt_sel:
                    fig = go.Figure()
                    for t in pt_sel:
                        tm = comp[(comp["strHomeTeam"]==t)|(comp["strAwayTeam"]==t)].sort_values("intRound")
                        pts = []
                        for _,r in tm.iterrows():
                            if r["strHomeTeam"]==t: p = 3 if r["intHomeScore"]>r["intAwayScore"] else 1 if r["intHomeScore"]==r["intAwayScore"] else 0
                            else: p = 3 if r["intAwayScore"]>r["intHomeScore"] else 1 if r["intAwayScore"]==r["intHomeScore"] else 0
                            pts.append(p)
                        fig.add_trace(go.Scatter(x=list(range(1,len(pts)+1)),y=np.cumsum(pts),name=t,mode="lines+markers"))
                    fig.update_layout(title="Points Trajectory",xaxis_title="Match",yaxis_title="Cumulative Points",template="plotly_white",height=500)
                    st.plotly_chart(fig, use_container_width=True)

        with proj_tabs[3]:
            st.subheader(" Title / Relegation Race Tracker")
            rc_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="rc_lg")
            rc_df = f_standings[f_standings["league"]==rc_lg].sort_values("intRank")
            if len(rc_df)>=3:
                leader_pts = rc_df.iloc[0]["intPoints"]
                rc_df["gap_to_leader"] = leader_pts-rc_df["intPoints"]
                rc_df["ppg"] = (rc_df["intPoints"]/rc_df["intPlayed"].clip(lower=1)).round(2)

                # Title race (top 5)
                st.markdown("** Title Race**")
                top5 = rc_df.head(5)[["intRank","strTeam","intPoints","gap_to_leader","ppg"]].copy()
                top5.columns = ["Rank","Team","Points","Gap to Leader","PPG"]
                st.dataframe(top5, use_container_width=True, hide_index=True)

                # Relegation battle (bottom 5)
                st.markdown("** Relegation Battle**")
                safe_line = rc_df.iloc[max(0,len(rc_df)-4)]["intPoints"] if len(rc_df)>4 else 0
                bot5 = rc_df.tail(5).copy()
                bot5["gap_to_safety"] = safe_line-bot5["intPoints"]
                b5d = bot5[["intRank","strTeam","intPoints","gap_to_safety","ppg"]].copy()
                b5d.columns = ["Rank","Team","Points","Gap to Safety","PPG"]
                st.dataframe(b5d, use_container_width=True, hide_index=True)


# 
# PAGE: ML Prediction Models
# 
elif page == " ML Prediction Models":
    st.title(" Machine Learning Models")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**ML Prediction Models** uses machine learning algorithms on real match data.

- **Team Clustering (K-Means)**: Groups teams into performance tiers (elite, strong, mid-table, weak)
- **Points Predictor (Linear Regression)**: Predicts final points from current stats -- shows over/underperformers
- **Match Predictor (Poisson)**: Calculates exact probabilities for any match outcome
- **Random Forest Classifier**: Identifies which stats matter most for winning matches

Tip: If a team's predicted points are higher than actual, they may be due for a strong finish.
""")
    if f_standings.empty: st.warning("No data.")
    else:
        ml_tabs = st.tabs([" Team Clustering"," Points Predictor"," Match Predictor"," Random Forest Classifier"])

        with ml_tabs[0]:
            st.subheader("Team Clustering (K-Means)")
            feats = ["intWin","intDraw","intLoss","intGoalsFor","intGoalsAgainst","intPoints"]
            feats = [f for f in feats if f in f_standings.columns]
            if len(feats)>=3 and len(f_standings)>=4:
                X = f_standings[feats].values; scaler = StandardScaler(); X_s = scaler.fit_transform(X)
                nc = st.slider("Clusters", 2, min(6,len(f_standings)-1), 3)
                km = KMeans(n_clusters=nc, random_state=42, n_init=10); cl = km.fit_predict(X_s)
                pdf = f_standings.copy(); pdf["Cluster"] = cl
                co = pdf.groupby("Cluster")["intPoints"].mean().sort_values(ascending=False)
                tiers = ["Elite","Strong","Mid Table","Lower","Bottom","Relegation"]
                lm = {c:tiers[i] for i,c in enumerate(co.index)}; pdf["Tier"] = pdf["Cluster"].map(lm)
                fig = px.scatter(pdf, x="intGoalsFor", y="intGoalsAgainst", color="Tier", hover_name="strTeam", size="intPoints", size_max=25, title="Team Clustering")
                fig.update_layout(template="plotly_white",height=550); st.plotly_chart(fig, use_container_width=True)
                cs = pdf.groupby("Tier").agg(Teams=("strTeam","count"),Avg_Pts=("intPoints","mean"),Avg_GF=("intGoalsFor","mean")).round(1).sort_values("Avg_Pts",ascending=False)
                st.dataframe(cs, use_container_width=True)

        with ml_tabs[1]:
            st.subheader("Points Prediction (Linear Regression)")
            if len(f_standings)>=4:
                rd = f_standings.copy()
                rd["win_pct"]=rd["intWin"]/rd["intPlayed"].clip(lower=1); rd["gf_pm"]=rd["intGoalsFor"]/rd["intPlayed"].clip(lower=1); rd["ga_pm"]=rd["intGoalsAgainst"]/rd["intPlayed"].clip(lower=1)
                pf = ["win_pct","gf_pm","ga_pm"]; X=rd[pf].values; y=rd["intPoints"].values
                lr = LinearRegression(); lr.fit(X,y); rd["pred_pts"]=lr.predict(X).round(1)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=rd["strTeam"],y=rd["intPoints"],name="Actual",marker_color="#1f77b4"))
                fig.add_trace(go.Scatter(x=rd["strTeam"],y=rd["pred_pts"],name="Predicted",mode="markers+lines",marker=dict(size=8,color="#d62728")))
                fig.update_layout(title="Actual vs Predicted Points",template="plotly_white",height=400,xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(pd.DataFrame({"Feature":pf,"Coefficient":lr.coef_.round(2)}), use_container_width=True, hide_index=True)

        with ml_tabs[2]:
            st.subheader("Match Outcome Predictor (Poisson + League Strength)")
            if not all_standings.empty:
                tlm = {r["strTeam"]:r.get("league","Unknown") for _,r in all_standings.iterrows()}
                apt = sorted(tlm.keys())
                if len(apt)>=2:
                    c1,c2 = st.columns(2)
                    with c1: ht = st.selectbox("Home", apt, key="ml_h")
                    with c2: at = st.selectbox("Away", [t for t in apt if t!=ht], key="ml_a")
                    hr = all_standings[all_standings["strTeam"]==ht]
                    ar = all_standings[all_standings["strTeam"]==at]
                    if not hr.empty and not ar.empty:
                        h,a = hr.iloc[0],ar.iloc[0]
                        hp,ap_ = max(int(h["intPlayed"]),1),max(int(a["intPlayed"]),1)
                        hls = LEAGUE_STRENGTH.get(tlm.get(ht,""),0.5); als = LEAGUE_STRENGTH.get(tlm.get(at,""),0.5)
                        lr_ = hls/max(als,0.01); ir = als/max(hls,0.01)
                        h_xg = h["intGoalsFor"]/hp*(a["intGoalsAgainst"]/ap_)/(a["intGoalsFor"]/ap_+0.01)*lr_*1.1
                        a_xg = a["intGoalsFor"]/ap_*(h["intGoalsAgainst"]/hp)/(h["intGoalsFor"]/hp+0.01)*ir*0.9
                        h_xg=max(0.1,min(h_xg,5)); a_xg=max(0.1,min(a_xg,5))
                        phw = sum(poisson.pmf(g1,h_xg)*sum(poisson.pmf(g2,a_xg) for g2 in range(g1)) for g1 in range(1,8))
                        pd_ = sum(poisson.pmf(g,h_xg)*poisson.pmf(g,a_xg) for g in range(8))
                        paw = max(0,1-phw-pd_); tp=phw+pd_+paw; phw/=tp; pd_/=tp; paw/=tp
                        st.markdown(f"**{ht}** ({tlm.get(ht,'')}, {hls:.2f}) vs **{at}** ({tlm.get(at,'')}, {als:.2f})")
                        mc1,mc2,mc3 = st.columns(3)
                        mc1.metric(f"{ht} Win",f"{phw*100:.1f}%"); mc2.metric("Draw",f"{pd_*100:.1f}%"); mc3.metric(f"{at} Win",f"{paw*100:.1f}%")
                        st.caption(f"xG: {ht} {h_xg:.2f}  {at} {a_xg:.2f}")

        with ml_tabs[3]:
            st.subheader(" Random Forest Match Classifier")
            if not f_events.empty:
                comp = f_events.dropna(subset=["intHomeScore","intAwayScore"]).copy()
                comp["intHomeScore"]=comp["intHomeScore"].astype(int); comp["intAwayScore"]=comp["intAwayScore"].astype(int)
                # Build features from standings
                team_stats = {}
                for _,r in all_standings.iterrows():
                    p = max(int(r["intPlayed"]),1)
                    team_stats[r["strTeam"]] = {"ppg":r["intPoints"]/p,"gf":r["intGoalsFor"]/p,"ga":r["intGoalsAgainst"]/p,"wr":r["intWin"]/p}
                rows = []
                for _,m in comp.iterrows():
                    hs = team_stats.get(m["strHomeTeam"]); aw = team_stats.get(m["strAwayTeam"])
                    if hs and aw:
                        label = 1 if m["intHomeScore"]>m["intAwayScore"] else 0 if m["intHomeScore"]==m["intAwayScore"] else 2
                        rows.append({"h_ppg":hs["ppg"],"h_gf":hs["gf"],"h_ga":hs["ga"],"h_wr":hs["wr"],
                            "a_ppg":aw["ppg"],"a_gf":aw["gf"],"a_ga":aw["ga"],"a_wr":aw["wr"],"result":label})
                if len(rows)>50:
                    rf_df = pd.DataFrame(rows); X = rf_df.drop("result",axis=1).values; y = rf_df["result"].values
                    split = int(len(X)*0.8)
                    rf = RandomForestClassifier(n_estimators=100,random_state=42); rf.fit(X[:split],y[:split])
                    pred = rf.predict(X[split:]); acc = accuracy_score(y[split:],pred)
                    st.metric("Model Accuracy (Test Set)", f"{acc*100:.1f}%")
                    fi = pd.DataFrame({"Feature":rf_df.columns[:-1],"Importance":rf.feature_importances_}).sort_values("Importance",ascending=False)
                    fig = px.bar(fi, x="Importance", y="Feature", orientation="h", title="Feature Importance", color="Importance", color_continuous_scale="Blues")
                    fig.update_layout(template="plotly_white",height=350,showlegend=False); st.plotly_chart(fig, use_container_width=True)
                else: st.info("Not enough match data for Random Forest (need 50+).")


# 
# PAGE: Advanced Statistics
# 
elif page == " Advanced Statistics":
    st.title(" Advanced Statistics")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Advanced Statistics** applies statistical models to the data.

- **Poisson Model**: Calculates goal probability distributions for each team (chance of scoring 0, 1, 2, 3+ goals)
- **Expected Points (xPts)**: Compares actual points earned to what was statistically expected based on match difficulty
- **Form Analysis**: Compares recent form (last 5 matches) vs season average
- **Consistency Index**: Measures result variability -- low index = consistent team, high index = unpredictable

Tip: Teams with actual points above xPts may be "lucky" and due for regression. Below xPts = unlucky.
""")
    if f_standings.empty: st.warning("No data.")
    else:
        adv_tabs = st.tabs([" Poisson Model"," Expected Points"," Form Analysis"," Consistency Index"])

        with adv_tabs[0]:
            st.subheader("Poisson Goal Model")
            pl = st.selectbox("League", sorted(f_standings["league"].unique()), key="poi_l")
            pd_ = f_standings[f_standings["league"]==pl].copy()
            pd_["gf_rate"]=pd_["intGoalsFor"]/pd_["intPlayed"].clip(lower=1); pd_["ga_rate"]=pd_["intGoalsAgainst"]/pd_["intPlayed"].clip(lower=1)
            avg = pd_["gf_rate"].mean()
            st_ = st.selectbox("Team", pd_["strTeam"].tolist(), key="poi_t")
            tr = pd_[pd_["strTeam"]==st_].iloc[0]
            atk = tr["gf_rate"]/max(avg,0.01); def_ = tr["ga_rate"]/max(avg,0.01)
            st.markdown(f"**{st_}**: Attack **{atk:.2f}**  Defense **{def_:.2f}**   = **{tr['gf_rate']:.2f}**")
            gr = list(range(7)); probs = [poisson.pmf(g,tr["gf_rate"])*100 for g in gr]
            fig = px.bar(x=gr, y=probs, text=[f"{p:.1f}%" for p in probs], title=f"Goal Probability  {st_}")
            fig.update_traces(textposition="outside"); fig.update_layout(template="plotly_white",height=400)
            st.plotly_chart(fig, use_container_width=True)

        with adv_tabs[1]:
            st.subheader("Expected Points (xPts)")
            xl = st.selectbox("League", sorted(f_standings["league"].unique()), key="xp_l")
            xdf = f_standings[f_standings["league"]==xl].copy()
            xdf["gf_rate"]=xdf["intGoalsFor"]/xdf["intPlayed"].clip(lower=1); xdf["ga_rate"]=xdf["intGoalsAgainst"]/xdf["intPlayed"].clip(lower=1)
            xp_data = []
            for _,r in xdf.iterrows():
                gf,ga = r["gf_rate"],r["ga_rate"]
                pw = sum(poisson.pmf(g1,gf)*sum(poisson.pmf(g2,ga) for g2 in range(g1)) for g1 in range(8))
                pd_p = sum(poisson.pmf(g,gf)*poisson.pmf(g,ga) for g in range(8))
                xpts = (pw*3+pd_p)*r["intPlayed"]
                xp_data.append({"Team":r["strTeam"],"Actual":int(r["intPoints"]),"xPts":round(xpts,1),"Diff":round(r["intPoints"]-xpts,1)})
            xpdf = pd.DataFrame(xp_data).sort_values("Actual",ascending=False)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=xpdf["Team"],y=xpdf["Actual"],name="Actual",marker_color="#1f77b4"))
            fig.add_trace(go.Scatter(x=xpdf["Team"],y=xpdf["xPts"],name="xPts",mode="markers+lines",marker=dict(size=10,color="#d62728")))
            fig.update_layout(title="Actual vs Expected Points",template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)
            fig = px.bar(xpdf.sort_values("Diff"), x="Diff", y="Team", orientation="h", color="Diff", color_continuous_scale="RdYlGn", color_continuous_midpoint=0, title="Over/Under Performance", text="Diff")
            fig.update_traces(texttemplate="%{text:+.1f}",textposition="outside"); fig.update_layout(template="plotly_white",height=350,showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with adv_tabs[2]:
            st.subheader("Form Analysis")
            fl = st.selectbox("League", sorted(f_standings["league"].unique()), key="fm_l")
            fdf = f_standings[f_standings["league"]==fl].copy()
            if "strForm" in fdf.columns:
                fa = []
                for _,r in fdf.iterrows():
                    form = str(r.get("strForm",""))
                    if form:
                        fp = sum(3 if c=="W" else 1 if c=="D" else 0 for c in form)
                        fppg = fp/max(len(form),1); sppg = r["intPoints"]/max(r["intPlayed"],1)
                        fa.append({"Team":r["strTeam"],"Form PPG":round(fppg,2),"Season PPG":round(sppg,2),"Trend":" Rising" if fppg>sppg else " Declining"})
                if fa:
                    fadf = pd.DataFrame(fa).sort_values("Form PPG",ascending=False)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=fadf["Team"],y=fadf["Season PPG"],name="Season",marker_color="#1f77b4"))
                    fig.add_trace(go.Bar(x=fadf["Team"],y=fadf["Form PPG"],name="Recent Form",marker_color="#ff7f0e"))
                    fig.update_layout(title="Season vs Form PPG",barmode="group",template="plotly_white",height=400); st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(fadf, use_container_width=True, hide_index=True)

        with adv_tabs[3]:
            st.subheader("Consistency Index")
            if not f_events.empty:
                ci_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="ci_l")
                comp = f_events[f_events["league"]==ci_lg].dropna(subset=["intHomeScore","intAwayScore"]).copy()
                comp["intHomeScore"]=comp["intHomeScore"].astype(int); comp["intAwayScore"]=comp["intAwayScore"].astype(int)
                ci_data = []
                for t in f_standings[f_standings["league"]==ci_lg]["strTeam"]:
                    tm = comp[(comp["strHomeTeam"]==t)|(comp["strAwayTeam"]==t)]
                    pts = []
                    for _,r in tm.iterrows():
                        if r["strHomeTeam"]==t: p=3 if r["intHomeScore"]>r["intAwayScore"] else 1 if r["intHomeScore"]==r["intAwayScore"] else 0
                        else: p=3 if r["intAwayScore"]>r["intHomeScore"] else 1 if r["intAwayScore"]==r["intHomeScore"] else 0
                        pts.append(p)
                    if pts:
                        ci_data.append({"Team":t,"Avg PPG":round(np.mean(pts),2),"Std Dev":round(np.std(pts),2),"Consistency":round(1-np.std(pts)/max(np.mean(pts),0.01),2)})
                if ci_data:
                    ci_df = pd.DataFrame(ci_data).sort_values("Consistency",ascending=False)
                    fig = px.bar(ci_df, x="Consistency", y="Team", orientation="h", color="Consistency", color_continuous_scale="RdYlGn", title="Consistency Index (1.0 = perfectly consistent)")
                    fig.update_layout(template="plotly_white",height=max(400,len(ci_df)*30),showlegend=False); st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(ci_df, use_container_width=True, hide_index=True)


# 
# PAGE: League Management
# 
elif page == " League Management":
    st.title(" League Management Tools")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**League Management** provides administrative and scheduling insights.

- **Referee Stats**: Average goals per match by referee -- some referees oversee more open games
- **Venue Analysis**: Identifies which stadiums produce the most goals
- **Fixture Schedule**: Calendar view of matches by month + upcoming fixture list
- **Attendance Tracker**: Estimated average home attendance for each club

Tip: Use Fixture Schedule to plan scouting trips or identify fixture congestion periods.
""")
    if f_standings.empty and f_events.empty: st.warning("No data.")
    else:
        lm_tabs = st.tabs([" Referee Stats"," Venue Analysis"," Fixture Schedule"," Attendance Tracker"])

        with lm_tabs[0]:
            st.subheader(" Referee Statistics")
            if not f_events.empty and "strOfficial" in f_events.columns:
                refs = f_events.dropna(subset=["strOfficial","intHomeScore","intAwayScore"]).copy()
                refs["intHomeScore"]=refs["intHomeScore"].astype(int); refs["intAwayScore"]=refs["intAwayScore"].astype(int)
                refs["total_goals"]=refs["intHomeScore"]+refs["intAwayScore"]
                ref_stats = refs.groupby("strOfficial").agg(Matches=("strOfficial","count"),Avg_Goals=("total_goals","mean"),Total_Goals=("total_goals","sum")).reset_index()
                ref_stats.columns = ["Referee","Matches","Avg Goals/Match","Total Goals"]
                ref_stats["Avg Goals/Match"]=ref_stats["Avg Goals/Match"].round(2)
                ref_stats = ref_stats[ref_stats["Matches"]>=3].sort_values("Matches",ascending=False)
                if not ref_stats.empty:
                    fig = px.bar(ref_stats.head(20), x="Avg Goals/Match", y="Referee", orientation="h", color="Matches", title="Referee Stats (min 3 matches)", text="Avg Goals/Match")
                    fig.update_traces(texttemplate="%{text:.2f}",textposition="outside"); fig.update_layout(template="plotly_white",height=500,showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(ref_stats, use_container_width=True, hide_index=True)
                else: st.info("No referee data with sufficient matches.")
            else: st.info("No referee data available.")

        with lm_tabs[1]:
            st.subheader(" Venue Analysis")
            if not f_events.empty and "strVenue" in f_events.columns:
                venues = f_events.dropna(subset=["strVenue","intHomeScore","intAwayScore"]).copy()
                venues["intHomeScore"]=venues["intHomeScore"].astype(int); venues["intAwayScore"]=venues["intAwayScore"].astype(int)
                venues["total"]=venues["intHomeScore"]+venues["intAwayScore"]
                v_stats = venues.groupby("strVenue").agg(Matches=("strVenue","count"),Avg_Goals=("total","mean"),Home_Team=("strHomeTeam","first")).reset_index()
                v_stats.columns = ["Venue","Matches","Avg Goals","Home Team"]
                v_stats["Avg Goals"]=v_stats["Avg Goals"].round(2)
                v_stats = v_stats[v_stats["Matches"]>=2].sort_values("Avg Goals",ascending=False)
                st.dataframe(v_stats.head(30), use_container_width=True, hide_index=True)

                # Highest scoring venues
                fig = px.bar(v_stats.head(15), x="Avg Goals", y="Venue", orientation="h", color="Matches", title="Highest Scoring Venues", text="Avg Goals")
                fig.update_traces(texttemplate="%{text:.2f}",textposition="outside"); fig.update_layout(template="plotly_white",height=450,showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No venue data available.")

        with lm_tabs[2]:
            st.subheader(" Fixture Schedule Overview")
            if not f_events.empty and "dateEvent" in f_events.columns:
                sch = f_events.copy()
                sch["month"] = sch["dateEvent"].dt.to_period("M").astype(str)
                by_month = sch.groupby("month").size().reset_index(); by_month.columns=["Month","Matches"]
                fig = px.bar(by_month, x="Month", y="Matches", title="Matches by Month", color="Matches", color_continuous_scale="Blues")
                fig.update_layout(template="plotly_white",height=400,showlegend=False); st.plotly_chart(fig, use_container_width=True)

                # Upcoming (unplayed)
                upcoming = f_events[f_events["intHomeScore"].isna()].copy()
                if not upcoming.empty:
                    st.subheader(" Upcoming Fixtures")
                    ud = upcoming[["dateEvent","strHomeTeam","strAwayTeam","league"]].sort_values("dateEvent").head(30).copy()
                    ud.columns = ["Date","Home","Away","League"]
                    st.dataframe(ud, use_container_width=True, hide_index=True)
            else: st.info("No fixture date data.")

        with lm_tabs[3]:
            st.subheader(" Spectator / Attendance Tracker")
            if not f_events.empty and "intSpectators" in f_events.columns:
                att = f_events.dropna(subset=["intSpectators"]).copy()
                att["intSpectators"] = pd.to_numeric(att["intSpectators"], errors="coerce")
                att = att[att["intSpectators"]>0]
                if not att.empty:
                    by_team = att.groupby("strHomeTeam")["intSpectators"].mean().sort_values(ascending=False).head(20).reset_index()
                    by_team.columns = ["Team","Avg Attendance"]
                    by_team["Avg Attendance"]=by_team["Avg Attendance"].round(0).astype(int)
                    fig = px.bar(by_team, x="Avg Attendance", y="Team", orientation="h", color="Avg Attendance", color_continuous_scale="Oranges", title="Average Home Attendance (Top 20)", text="Avg Attendance")
                    fig.update_traces(texttemplate="%{text:,}",textposition="outside"); fig.update_layout(template="plotly_white",height=500,showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("No attendance data with values.")
            else: st.info("No attendance data available.")


# 
# PAGE: Video Analysis Hub
# 
elif page == " Video Analysis Hub":
    st.title(" Video Analysis Hub")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Video Analysis Hub** links match footage with statistical context.

- **Match Highlights**: Browse available video links for completed matches
- **Key Moments**: Identifies the closest, most dramatic matches with key stats
- **Set Piece Analysis**: Flags teams scoring below the league average as candidates for set piece improvement

Tip: Combine Key Moments data with video to study decisive phases of important matches.
""")
    st.caption("Match highlights and video content linked from available data sources")
    if f_events.empty: st.warning("No events data.")
    else:
        va_tabs = st.tabs([" Match Highlights"," Key Moments"," Set Piece Analysis"])

        with va_tabs[0]:
            st.subheader(" Match Highlights Library")
            has_video = f_events.dropna(subset=["intHomeScore","intAwayScore"]).copy()
            if "strVideo" in has_video.columns:
                with_vid = has_video[has_video["strVideo"].notna()&(has_video["strVideo"]!="")]
                if not with_vid.empty:
                    st.markdown(f"**{len(with_vid)} matches with video highlights**")
                    for _,m in with_vid.sort_values("dateEvent",ascending=False).head(20).iterrows():
                        with st.expander(f" {m['strHomeTeam']} {int(m['intHomeScore'])}-{int(m['intAwayScore'])} {m['strAwayTeam']} ({str(m.get('dateEvent',''))[:10]})"):
                            st.video(m["strVideo"])
                else:
                    st.info("No video highlights available in current data. Video links appear when provided by TheSportsDB.")
            else:
                st.info("Video field not present in events data.")

            # Show recent results without video as reference
            st.subheader(" Recent Results (for video review)")
            recent = has_video.sort_values("dateEvent",ascending=False).head(20)
            rd = recent[["dateEvent","strHomeTeam","intHomeScore","intAwayScore","strAwayTeam","league"]].copy()
            rd["intHomeScore"]=rd["intHomeScore"].astype(int); rd["intAwayScore"]=rd["intAwayScore"].astype(int)
            rd.columns = ["Date","Home","HG","AG","Away","League"]
            st.dataframe(rd, use_container_width=True, hide_index=True)

        with va_tabs[1]:
            st.subheader(" Key Moments Analysis")
            st.caption("Statistical breakdown of decisive match moments")
            if not f_events.empty:
                comp = f_events.dropna(subset=["intHomeScore","intAwayScore"]).copy()
                comp["intHomeScore"]=comp["intHomeScore"].astype(int); comp["intAwayScore"]=comp["intAwayScore"].astype(int)
                comp["margin"] = abs(comp["intHomeScore"]-comp["intAwayScore"])

                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Total Matches", len(comp))
                c2.metric("1-Goal Games", len(comp[comp["margin"]==1]))
                c3.metric("Draws", len(comp[comp["margin"]==0]))
                c4.metric("Blowouts (4+)", len(comp[comp["margin"]>=4]))

                # Close games analysis
                st.markdown("** Close Games (1-goal margin)**")
                close = comp[comp["margin"]==1].sort_values("dateEvent",ascending=False).head(15)
                cd = close[["dateEvent","strHomeTeam","intHomeScore","intAwayScore","strAwayTeam","league"]].copy()
                cd.columns = ["Date","Home","HG","AG","Away","League"]
                st.dataframe(cd, use_container_width=True, hide_index=True)

        with va_tabs[2]:
            st.subheader(" Set Piece Potential Analysis")
            st.caption("Teams with highest goal tallies may benefit from set piece coaching")
            if not f_standings.empty:
                sp_lg = st.selectbox("League", sorted(f_standings["league"].unique()), key="sp_lg")
                sp_df = f_standings[f_standings["league"]==sp_lg].copy()
                sp_df["gf_pm"]=sp_df["intGoalsFor"]/sp_df["intPlayed"].clip(lower=1)
                sp_df["ga_pm"]=sp_df["intGoalsAgainst"]/sp_df["intPlayed"].clip(lower=1)
                # Identify teams with low scoring (might need set piece improvement)
                sp_df["set_piece_need"] = np.where(sp_df["gf_pm"]<sp_df["gf_pm"].median(),"High","Low")
                fig = px.scatter(sp_df, x="gf_pm", y="ga_pm", color="set_piece_need", hover_name="strTeam",
                    size="intPoints", size_max=20, title="Set Piece Coaching Need (teams below median GF/M)",
                    labels={"gf_pm":"Goals For/Match","ga_pm":"Goals Against/Match"},
                    color_discrete_map={"High":"red","Low":"green"})
                fig.add_vline(x=sp_df["gf_pm"].median(),line_dash="dash",annotation_text="Median GF/M")
                fig.update_layout(template="plotly_white",height=450); st.plotly_chart(fig, use_container_width=True)


# 
# PAGE: Data Sources
# 
elif page == " Data Sources":
    st.title(" Data Sources & Methods")
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Data Sources** documents where the data comes from and what is covered.

- View the **data providers** and their licenses
- See which **leagues** are included and how many teams each has
- Review all **platform modules** with their purpose and methodology
- Check **academic references** for the statistical models used
""")
    st.subheader("Data Sources")
    st.markdown("""
| Source | Data | Season | License |
|--------|------|--------|---------|
| [TheSportsDB](https://www.thesportsdb.com) | Standings, events, teams, players | 2025-2026 | CC BY-NC-SA 4.0 |
| [Football-Data.org](https://www.football-data.org) | Competition metadata | 2025-2026 | Free tier |
| [Transfermarkt](https://www.transfermarkt.com) | Player market values, ages | 2025-2026 | Scraped |
""")
    st.subheader("Leagues Covered (2025-2026)")
    if not all_standings.empty:
        ls = all_standings.groupby("league").agg(Teams=("strTeam","nunique"),Avg_Pts=("intPoints","mean")).round(1).sort_values("Teams",ascending=False)
        st.dataframe(ls, use_container_width=True)
    st.subheader("Platform Modules")
    st.markdown("""
| Module | Purpose | Method |
|---|---|---|
| Overview & Standings | League tables with playoff/playout zones | API data + format rules |
| Match Analysis | Head-to-head, results, goal patterns | Event data analysis |
| Championship Probability | Monte Carlo finish simulation | 10K+ simulations |
| European Comparison | Cross-league benchmarking | Normalized metrics |
| Player Analysis | Player database with comparison tools | Profile matching |
| Scouting Intelligence | Wonderkid radar, smart scout, similar players, Best XI | Custom scoring algorithms |
| Tactical Analysis | Home/away splits, xG, formations, momentum | Poisson + squad analysis |
| Opponent Report | Pre-match intelligence with predictions | Composite model |
| Transfer Recommendations | Squad audit, needs analysis, targets, sell list | Gap analysis + player DB |
| Physical & Medical | Fitness profiles, injury risk, fixture congestion | Age/workload modeling |
| Youth Academy | U21 tracker, development potential, academy comparison | Potential scoring |
| Financial Analysis | Squad valuation, FFP compliance, transfer ROI | Market value analysis |
| Season Projections | ELO ratings, final table projection, race tracker | ELO + linear projection |
| ML Models | K-Means clustering, Random Forest, Poisson predictor | scikit-learn |
| Advanced Statistics | xPts, form trends, consistency index | Statistical models |
| League Management | Referee stats, venues, fixtures, attendance | Event metadata |
| Video Analysis Hub | Match highlights, key moments, set piece analysis | Video links + stats |
""")
    st.subheader("Academic References")
    st.markdown("""
1. Dixon, M. & Coles, S. (1997). "Modelling association football scores." *Applied Statistics*, 46(2), 265-280.
2. Maher, M. (1982). "Modelling association football scores." *Statistica Neerlandica*, 36(3), 109-118.
3. Hvattum, L. & Arntzen, H. (2010). "Using ELO ratings for match result prediction." *IJF*, 26(3), 460-470.
4. Elo, A. (1978). "The Rating of Chessplayers, Past and Present." Arco Publishing.
5. MacQueen, J. (1967). "Some methods for classification and analysis of multivariate observations." *Berkeley Symposium*.
""")

# =====================================================
# PAGE: Documentation / Documentatie
# =====================================================
elif page == " Documentation":
    with st.expander("How to use this page", expanded=False):
        st.markdown("""
**Documentation** provides a full guide to the platform in English and Romanian.

- Toggle between **English** and **Romana** at the top
- Each section explains what the page does and how to interpret the data
- Use this as a reference when you are unsure about a feature
""")
    lang = st.radio("Language / Limba", ["English", "Romana"], horizontal=True)

    if lang == "English":
        st.title("Documentation")
        st.markdown("""---""")

        st.header("About This Platform")
        st.markdown("""
**Football Analytics Pro** is a professional-grade analytics dashboard for the **2025-2026 season**, 
covering **15 European leagues**. It was built as an all-in-one tool that a football club's 
analysis department could use for scouting, match preparation, transfer planning, and strategic decisions.

The platform pulls data from three sources:
- **TheSportsDB** -- standings, match events, team and player profiles
- **Football-Data.org** -- competition metadata
- **Transfermarkt** -- player market values and ages (scraped)
""")

        st.header("Pages & Features")

        st.subheader("1. Overview & Standings")
        st.markdown("""
Displays the full league table for each of the 15 leagues. Includes playoff/playout zone highlighting 
(where applicable), recent form indicators, points distribution charts, and a description of each 
league's format (e.g. Romania's championship round, Belgian playoff system).
""")

        st.subheader("2. Match Analysis")
        st.markdown("""
A head-to-head comparison tool. Select two teams and see their full match history, outcome distributions 
(pie charts), goal timing analysis (which half the goals happen in), home advantage statistics, 
biggest wins, and highest-scoring matches.
""")

        st.subheader("3. Championship Probability")
        st.markdown("""
Runs a **Monte Carlo simulation** (10,000+ iterations) for each league. Based on each team's current 
win/draw/loss rates and remaining matches, it simulates how the season could end. Shows probabilities 
for winning the title, finishing in playoff positions, or being relegated.
""")

        st.subheader("4. European Comparison")
        st.markdown("""
Compares all 15 leagues against each other. Includes competitiveness analysis (how close the league 
table is), scoring trends, a UEFA-style league coefficient estimate, squad valuations, and 
radar charts for cross-league benchmarking.
""")

        st.subheader("5. Player Analysis")
        st.markdown("""
A full player database with filters by position and nationality. Shows age distributions, 
position breakdowns, a player-vs-player comparison tool, and a scatter plot of each team's 
attacking vs defensive player count.
""")

        st.subheader("6. Scouting Intelligence")
        st.markdown("""
Five tabs for talent identification:
- **Wonderkid Radar** -- finds the best U21 players with a potential score
- **Smart Scout** -- custom filters (age range, position, league, value)
- **Similar Players** -- input a player and find comparable profiles
- **Best XI Generator** -- builds an optimal team in a chosen formation from available players
- **Value Trends** -- market value distribution by position across leagues
""")

        st.subheader("7. Tactical Analysis")
        st.markdown("""
Five tabs covering:
- **Home/Away Split** -- points-per-game at home vs away
- **Scoring Patterns** -- goals scored by matchday/round
- **xG Analysis** -- expected goals calculated using a Poisson model
- **Formation Estimator** -- estimates each team's likely formation from squad composition
- **Momentum Tracker** -- cumulative points chart showing each team's trajectory through the season
""")

        st.subheader("8. Opponent Report")
        st.markdown("""
Pre-match intelligence tool. Select your team and the opponent, and the system generates:
- A strength comparison radar chart
- Identified opponent weaknesses
- A match prediction using the xG model
- Full squad comparison metrics
""")

        st.subheader("9. Transfer Recommendations")
        st.markdown("""
Four tabs:
- **Squad Audit** -- current squad composition and statistics
- **Transfer Needs** -- identifies gaps in the squad and suggests targets from other leagues
- **Players to Sell** -- flags aging or surplus players for potential sales
- **Cross-League Scout** -- finds the best value-for-money players across all 15 leagues
""")

        st.subheader("10. Physical & Medical")
        st.markdown("""
Four tabs:
- **Squad Fitness Profile** -- maps players by age and position to estimate fitness risk
- **Injury Risk Assessment** -- scores each position's injury risk based on age, squad depth, and workload
- **Fixture Congestion** -- analyzes the spacing between matches to flag fatigue risk periods
- **Rotation Planner** -- recommends which positions need more depth for rotation
""")

        st.subheader("11. Youth Academy")
        st.markdown("""
Four tabs:
- **U21 Tracker** -- counts and lists all players under 21 by club
- **Development Potential** -- scores young players on a growth ceiling metric
- **Academy Comparison** -- compares youth squad strength across clubs
- **Youth Nationality Map** -- shows where young talent comes from geographically
""")

        st.subheader("12. Financial Analysis")
        st.markdown("""
Four tabs:
- **Squad Valuation** -- total market value by club
- **Wage Analysis** -- market value distribution broken down by position
- **Transfer ROI** -- how efficiently a club converts squad value into league points
- **FFP Compliance** -- a Financial Fair Play risk assessment based on squad value concentration
""")

        st.subheader("13. Season Projections")
        st.markdown("""
Four tabs:
- **ELO Ratings** -- calculates an Elo-based team strength rating from match results
- **Final Table Projection** -- extrapolates the current points-per-game to predict final standings
- **Points Trajectory** -- plots cumulative points over the season for all teams
- **Race Tracker** -- monitors the title race and relegation battle with projected safe/danger thresholds
""")

        st.subheader("14. ML Prediction Models")
        st.markdown("""
Four machine learning models:
- **Team Clustering (K-Means)** -- groups teams into performance tiers
- **Points Predictor (Linear Regression)** -- predicts final points from current stats
- **Match Predictor (Poisson + League Strength)** -- calculates match outcome probabilities
- **Random Forest Classifier** -- identifies the most important features for predicting match results
""")

        st.subheader("15. Advanced Statistics")
        st.markdown("""
Four tabs:
- **Poisson Model** -- goal probability distributions for each team
- **Expected Points (xPts)** -- compares actual points earned to what was statistically expected
- **Form Analysis** -- compares recent form to season-long average
- **Consistency Index** -- measures how consistent each team's results are (low standard deviation = consistent)
""")

        st.subheader("16. League Management")
        st.markdown("""
Four tabs:
- **Referee Statistics** -- average goals per match by referee
- **Venue Analysis** -- identifies the highest-scoring stadiums
- **Fixture Schedule** -- matches played by month and upcoming fixture list
- **Attendance Tracker** -- average home attendance estimates
""")

        st.subheader("17. Video Analysis Hub")
        st.markdown("""
Three tabs:
- **Match Highlights** -- video library with links to match footage
- **Key Moments** -- identifies the closest matches and key statistical breakdowns
- **Set Piece Analysis** -- flags teams scoring below the median as candidates for set piece coaching improvement
""")

        st.subheader("18. Data Sources")
        st.markdown("""
Lists all data sources used, the leagues covered, a summary table of all platform modules, 
and academic references for the statistical methods (Poisson, Elo, K-Means, etc.).
""")

        st.header("Technical Details")
        st.markdown("""
- **Framework:** Streamlit (Python)
- **Visualization:** Plotly (interactive charts)
- **Machine Learning:** scikit-learn (K-Means, Random Forest, Linear Regression)
- **Statistics:** SciPy (Poisson distributions, percentile calculations)
- **Data format:** JSON files stored in the `data/` folder
- **Season:** 2025-2026
- **Leagues:** 15 European leagues (EPL, La Liga, Bundesliga, Serie A, Ligue 1, Primeira Liga, Eredivisie, Belgian Pro League, Super Lig, and 6 more)
""")

    else:
        st.title("Documentatie")
        st.markdown("""---""")

        st.header("Despre Platforma")
        st.markdown("""
**Football Analytics Pro** este un dashboard profesional de analiza fotbalistica pentru **sezonul 2025-2026**, 
acoperind **15 ligi europene**. A fost construit ca un instrument complet pe care departamentul de analiza 
al unui club de fotbal l-ar putea folosi pentru scouting, pregatirea meciurilor, planificarea transferurilor 
si decizii strategice.

Platforma preia date din trei surse:
- **TheSportsDB** -- clasamente, evenimente de meci, profiluri de echipe si jucatori
- **Football-Data.org** -- metadate despre competitii
- **Transfermarkt** -- valori de piata si varste ale jucatorilor (preluate automat)
""")

        st.header("Pagini si Functionalitati")

        st.subheader("1. Overview & Standings (Clasamente)")
        st.markdown("""
Afiseaza clasamentul complet pentru fiecare din cele 15 ligi. Include evidentierea zonelor de playoff/playout 
(unde este cazul), indicatori de forma recenta, grafice de distributie a punctelor si o descriere a 
formatului fiecarei ligi (ex: turneul campionatului din Romania, sistemul de playoff belgian).
""")

        st.subheader("2. Match Analysis (Analiza Meciurilor)")
        st.markdown("""
Instrument de comparare directa. Selecteaza doua echipe si vezi istoricul complet al meciurilor, 
distributia rezultatelor (grafice pie), analiza timpului golurilor (in ce repriza se marcheaza), 
statistici de avantaj al gazdei, cele mai mari victorii si meciurile cu cele mai multe goluri.
""")

        st.subheader("3. Championship Probability (Probabilitate Campionat)")
        st.markdown("""
Ruleaza o **simulare Monte Carlo** (10.000+ iteratii) pentru fiecare liga. Pe baza ratelor actuale de 
victorii/egaluri/infrangeri si a meciurilor ramase, simuleaza cum s-ar putea termina sezonul. Arata 
probabilitatile de castigare a titlului, calificare in playoff sau retrogradare.
""")

        st.subheader("4. European Comparison (Comparatie Europeana)")
        st.markdown("""
Compara toate cele 15 ligi intre ele. Include analiza competitivitatii (cat de strans este clasamentul), 
tendinte de goluri marcate, un coeficient de liga in stil UEFA, valorile loturilor si grafice radar 
pentru comparatii intre ligi.
""")

        st.subheader("5. Player Analysis (Analiza Jucatorilor)")
        st.markdown("""
Baza de date completa a jucatorilor cu filtre dupa pozitie si nationalitate. Afiseaza distributia 
varselor, distributia pe pozitii, un instrument de comparare jucator-vs-jucator si un grafic scatter 
al numarului de jucatori ofensivi vs defensivi per echipa.
""")

        st.subheader("6. Scouting Intelligence (Scouting Inteligent)")
        st.markdown("""
Cinci tab-uri pentru identificarea talentului:
- **Wonderkid Radar** -- gaseste cei mai buni jucatori U21 cu un scor de potential
- **Smart Scout** -- filtre personalizate (interval de varsta, pozitie, liga, valoare)
- **Similar Players** -- introdu un jucator si gaseste profiluri comparabile
- **Best XI Generator** -- construieste echipa optima intr-o formatie aleasa din jucatorii disponibili
- **Value Trends** -- distributia valorii de piata pe pozitii in toate ligile
""")

        st.subheader("7. Tactical Analysis (Analiza Tactica)")
        st.markdown("""
Cinci tab-uri:
- **Home/Away Split** -- puncte pe meci acasa vs deplasare
- **Scoring Patterns** -- goluri marcate pe etapa
- **xG Analysis** -- goluri asteptate calculate cu un model Poisson
- **Formation Estimator** -- estimeaza formatia probabila a fiecarei echipe din compozitia lotului
- **Momentum Tracker** -- grafic de puncte cumulate aratand traiectoria fiecarei echipe pe parcursul sezonului
""")

        st.subheader("8. Opponent Report (Raport Adversar)")
        st.markdown("""
Instrument de informatii pre-meci. Selecteaza echipa ta si adversarul, iar sistemul genereaza:
- Un grafic radar de comparare a punctelor forte
- Punctele slabe identificate ale adversarului
- O predictie a meciului folosind modelul xG
- Metrici complete de comparare a loturilor
""")

        st.subheader("9. Transfer Recommendations (Recomandari Transferuri)")
        st.markdown("""
Patru tab-uri:
- **Squad Audit** -- compozitia si statisticile lotului curent
- **Transfer Needs** -- identifica lacunele din lot si sugereaza tinte din alte ligi
- **Players to Sell** -- semnaleaza jucatorii in varsta sau in surplus pentru vanzari potentiale
- **Cross-League Scout** -- gaseste jucatorii cu cel mai bun raport calitate-pret din toate cele 15 ligi
""")

        st.subheader("10. Physical & Medical (Fizic si Medical)")
        st.markdown("""
Patru tab-uri:
- **Squad Fitness Profile** -- harta jucatorilor dupa varsta si pozitie pentru estimarea riscului de fitness
- **Injury Risk Assessment** -- scor de risc de accidentare bazat pe varsta, adancimea lotului si efort
- **Fixture Congestion** -- analizeaza spatiul dintre meciuri pentru a semnala perioadele de risc de oboseala
- **Rotation Planner** -- recomanda pozitiile care au nevoie de mai multa adancime pentru rotatie
""")

        st.subheader("11. Youth Academy (Academia de Juniori)")
        st.markdown("""
Patru tab-uri:
- **U21 Tracker** -- numara si listeaza toti jucatorii sub 21 de ani pe club
- **Development Potential** -- scor de potential de crestere pentru jucatorii tineri
- **Academy Comparison** -- compara puterea loturilor de tineret intre cluburi
- **Youth Nationality Map** -- arata de unde provin tinerii talentati din punct de vedere geografic
""")

        st.subheader("12. Financial Analysis (Analiza Financiara)")
        st.markdown("""
Patru tab-uri:
- **Squad Valuation** -- valoarea totala de piata pe club
- **Wage Analysis** -- distributia valorii de piata pe pozitii
- **Transfer ROI** -- cat de eficient converteste un club valoarea lotului in puncte
- **FFP Compliance** -- evaluare de risc Financial Fair Play bazata pe concentrarea valorii lotului
""")

        st.subheader("13. Season Projections (Proiectii Sezon)")
        st.markdown("""
Patru tab-uri:
- **ELO Ratings** -- calculeaza un rating de putere al echipei in stil Elo din rezultatele meciurilor
- **Final Table Projection** -- extrapoleaza punctele actuale per meci pentru a prezice clasamentul final
- **Points Trajectory** -- grafic de puncte cumulate pe parcursul sezonului pentru toate echipele
- **Race Tracker** -- monitorizeaza cursa pentru titlu si lupta pentru evitarea retrogradarii
""")

        st.subheader("14. ML Prediction Models (Modele ML de Predictie)")
        st.markdown("""
Patru modele de machine learning:
- **Team Clustering (K-Means)** -- grupeaza echipele in niveluri de performanta
- **Points Predictor (Linear Regression)** -- prezice punctele finale din statisticile curente
- **Match Predictor (Poisson + League Strength)** -- calculeaza probabilitatile rezultatelor meciurilor
- **Random Forest Classifier** -- identifica cele mai importante caracteristici pentru prezicerea rezultatelor
""")

        st.subheader("15. Advanced Statistics (Statistici Avansate)")
        st.markdown("""
Patru tab-uri:
- **Poisson Model** -- distributii de probabilitate a golurilor pentru fiecare echipa
- **Expected Points (xPts)** -- compara punctele reale cu cele asteptate statistic
- **Form Analysis** -- compara forma recenta cu media sezonului
- **Consistency Index** -- masoara cat de consistente sunt rezultatele fiecarei echipe
""")

        st.subheader("16. League Management (Managementul Ligii)")
        st.markdown("""
Patru tab-uri:
- **Referee Statistics** -- media golurilor pe meci per arbitru
- **Venue Analysis** -- identifica stadioanele cu cele mai multe goluri
- **Fixture Schedule** -- meciuri jucate pe luna si lista urmatoarelor meciuri
- **Attendance Tracker** -- estimari de audienta medie acasa
""")

        st.subheader("17. Video Analysis Hub (Centru Analiza Video)")
        st.markdown("""
Trei tab-uri:
- **Match Highlights** -- biblioteca video cu linkuri catre filmari de meci
- **Key Moments** -- identifica cele mai stranse meciuri si detalii statistice cheie
- **Set Piece Analysis** -- semnaleaza echipele care marcheaza sub medie ca fiind candidate 
  pentru imbunatatirea jocului la fazele fixe
""")

        st.subheader("18. Data Sources (Surse de Date)")
        st.markdown("""
Listeaza toate sursele de date folosite, ligile acoperite, un tabel rezumat al tuturor modulelor 
platformei si referinte academice pentru metodele statistice (Poisson, Elo, K-Means etc.).
""")

        st.header("Detalii Tehnice")
        st.markdown("""
- **Framework:** Streamlit (Python)
- **Vizualizare:** Plotly (grafice interactive)
- **Machine Learning:** scikit-learn (K-Means, Random Forest, Linear Regression)
- **Statistici:** SciPy (distributii Poisson, calcule de percentile)
- **Format date:** Fisiere JSON stocate in folderul `data/`
- **Sezon:** 2025-2026
- **Ligi:** 15 ligi europene (EPL, La Liga, Bundesliga, Serie A, Ligue 1, Primeira Liga, Eredivisie, Belgian Pro League, Super Lig si altele)
""")
