"""
Report Charts Part 4 - Romanian Liga I Deep Dive (8 charts):
  RO1. Squad Age Profile per Club (grouped bar)
  RO2. Position Gaps Heatmap (team x position)
  RO3. Foreign vs Domestic Players per Team
  RO4. Top 20 Most Valuable Players in Liga I
  RO5. Home vs Away Goal Efficiency Butterfly
  RO6. Club Market Value Composition (stacked bar)
  RO7. Form Momentum - Rolling Results Heatmap
  RO8. Transfer Need Score per Club (radar)
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from report_data import IMG_DIR

# Short names for Romanian teams (reused across all Romanian charts)
SHORT_NAMES = {
    "Universitatea Craiova": "U. Craiova", "Universitatea Cluj": "U. Cluj",
    "CFR Cluj": "CFR", "Dinamo Bucure\u0219ti": "Dinamo",
    "Rapid Bucure\u0219ti": "Rapid", "Arge\u0219 Pite\u0219ti": "Arge\u0219",
    "FCSB": "FCSB", "UTA Arad": "UTA", "Boto\u0219ani": "Boto\u0219ani",
    "Cs\u00edkszereda Miercurea Ciuc": "Cs\u00edkszereda",
    "O\u021belul Gala\u021bi": "O\u021belul", "Farul Constan\u021ba": "Farul",
    "Petrolul Ploie\u0219ti": "Petrolul", "Unirea Slobozia": "Unirea",
    "Hermannstadt": "Hermannstadt", "Metaloglobus Bucure\u0219ti": "Metaloglobus",
    # Player-data team names
    "ACSC FC Arges": "Arge\u0219", "FC Botosani": "Boto\u0219ani",
    "FC Hermannstadt": "Hermannstadt", "FC Metaloglobus Bucharest": "Metaloglobus",
    "FC Universitatea Cluj": "U. Cluj", "FCV Farul Constanta": "Farul",
    "FK Csikszereda Miercurea Ciuc": "Cs\u00edkszereda",
    "Petrolul Ploiesti": "Petrolul", "SC Otelul Galati": "O\u021belul",
}

# Canonical position groups
POS_GROUPS = {
    "Goalkeeper": "GK",
    "Centre-Back": "CB", "Left-Back": "LB", "Right-Back": "RB",
    "Defensive Midfield": "DM", "Central Midfield": "CM",
    "Attacking Midfield": "AM", "Left Midfield": "LM", "Right Midfield": "RM",
    "Left Winger": "LW", "Right Winger": "RW",
    "Centre-Forward": "CF", "Second Striker": "SS",
}

# Ideal minimum counts per position group
IDEAL_SQUAD = {"GK": 3, "CB": 4, "LB": 2, "RB": 2, "DM": 2, "CM": 3, "AM": 2,
               "LW": 2, "RW": 2, "CF": 3}


def _get_ro_players(players):
    """Filter players belonging to Romanian Liga I teams."""
    if players.empty:
        return pd.DataFrame()
    ro_keys = list(SHORT_NAMES.keys())
    ro = players[players["strTeam"].apply(
        lambda x: any(k in str(x) for k in ro_keys)
    )].copy()
    ro["short_team"] = ro["strTeam"].map(SHORT_NAMES).fillna(ro["strTeam"])
    ro["age"] = pd.to_numeric(ro.get("age", pd.Series(dtype=float)), errors="coerce")
    ro["market_value_eur_m"] = pd.to_numeric(
        ro.get("market_value_eur_m", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0)
    ro["pos_group"] = ro["strPosition"].map(POS_GROUPS).fillna("Other")
    return ro


def generate_charts_part4(data):
    """Generate Romanian Liga I deep-dive charts."""
    ro_standings = data["ro_standings"]
    ro_events = data["ro_events"]
    players = data["players"]
    charts = []

    ro_players = _get_ro_players(players)

    print("  Generating Romanian Deep-Dive charts...")

    # ---- RO1: Squad Age Profile per Club ----
    if not ro_players.empty:
        age_bins = pd.cut(ro_players["age"], bins=[15, 21, 25, 29, 33, 45],
                          labels=["U21", "22-25", "26-29", "30-33", "34+"])
        age_team = ro_players.assign(age_group=age_bins).groupby(
            ["short_team", "age_group"], observed=True
        ).size().reset_index(name="count")
        fig = px.bar(
            age_team, x="short_team", y="count", color="age_group",
            barmode="stack",
            color_discrete_sequence=["#2ecc71", "#3498db", "#f39c12", "#e74c3c", "#8e44ad"],
            title="Romanian Liga I - Squad Age Profile per Club",
            labels={"short_team": "Club", "count": "Players", "age_group": "Age Group"}
        )
        fig.update_layout(template="plotly_white", height=550, xaxis_tickangle=-40)
        fig.write_image(f"{IMG_DIR}/ro1_squad_age_profile.png", width=1100, height=550, scale=2)
        charts.append("ro1_squad_age_profile")

    # ---- RO2: Position Gaps Heatmap ----
    if not ro_players.empty:
        pos_team = ro_players.groupby(["short_team", "pos_group"]).size().unstack(fill_value=0)
        key_pos = [p for p in IDEAL_SQUAD if p in pos_team.columns]
        pos_team = pos_team[key_pos] if key_pos else pos_team
        fig = px.imshow(
            pos_team.T, text_auto=True,
            color_continuous_scale="YlOrRd",
            title="Position Coverage Heatmap (Players per Position per Club)",
            labels={"x": "Club", "y": "Position", "color": "Count"},
            aspect="auto"
        )
        fig.update_layout(template="plotly_white", height=500)
        fig.write_image(f"{IMG_DIR}/ro2_position_heatmap.png", width=1100, height=550, scale=2)
        charts.append("ro2_position_heatmap")

    # ---- RO3: Foreign vs Domestic ----
    if not ro_players.empty and "strNationality" in ro_players.columns:
        ro_players["is_romanian"] = ro_players["strNationality"].str.contains("Romania", case=False, na=False)
        nat_team = ro_players.groupby("short_team")["is_romanian"].agg(
            Romanian="sum", Foreign=lambda x: (~x).sum()
        ).reset_index()
        nat_melt = nat_team.melt(id_vars="short_team", var_name="Origin", value_name="Count")
        fig = px.bar(
            nat_melt, x="short_team", y="Count", color="Origin", barmode="group",
            color_discrete_map={"Romanian": "#f1c40f", "Foreign": "#2c3e50"},
            title="Romanian vs Foreign Players per Club",
            labels={"short_team": "Club"}
        )
        fig.update_layout(template="plotly_white", height=500, xaxis_tickangle=-40)
        fig.write_image(f"{IMG_DIR}/ro3_foreign_domestic.png", width=1100, height=550, scale=2)
        charts.append("ro3_foreign_domestic")

    # ---- RO4: Top 20 Most Valuable Players ----
    if not ro_players.empty:
        top_val = ro_players.nlargest(20, "market_value_eur_m")
        if not top_val.empty and top_val["market_value_eur_m"].sum() > 0:
            top_val["label"] = top_val["strPlayer"].str.split().apply(
                lambda parts: parts[0][0] + ". " + parts[-1] if len(parts) >= 2 else " ".join(parts)
            ) + " (" + top_val["short_team"] + ")"
            fig = px.bar(
                top_val.sort_values("market_value_eur_m"),
                x="market_value_eur_m", y="label", orientation="h",
                color="strPosition",
                title="Top 20 Most Valuable Players in Romanian Liga I",
                labels={"market_value_eur_m": "Market Value (€M)", "label": "Player"},
                text="market_value_eur_m"
            )
            fig.update_traces(texttemplate="%{text:.2f}M", textposition="outside")
            fig.update_layout(template="plotly_white", height=700,
                              yaxis={"categoryorder": "total ascending"}, showlegend=True)
            fig.write_image(f"{IMG_DIR}/ro4_top_value_players.png", width=1100, height=700, scale=2)
            charts.append("ro4_top_value_players")

    # ---- RO5: Home vs Away Goal Efficiency Butterfly ----
    if not ro_events.empty and not ro_standings.empty:
        completed = ro_events.dropna(subset=["intHomeScore", "intAwayScore"]).copy()
        if not completed.empty:
            home_gf = completed.groupby("strHomeTeam")["intHomeScore"].sum()
            away_gf = completed.groupby("strAwayTeam")["intAwayScore"].sum()
            teams = sorted(set(home_gf.index) | set(away_gf.index))
            butterfly = pd.DataFrame({
                "Team": teams,
                "Home Goals": [home_gf.get(t, 0) for t in teams],
                "Away Goals": [away_gf.get(t, 0) for t in teams],
            })
            butterfly["short"] = butterfly["Team"].map(SHORT_NAMES).fillna(butterfly["Team"])
            butterfly = butterfly.sort_values("Home Goals", ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(y=butterfly["short"], x=-butterfly["Home Goals"],
                                 orientation="h", name="Home Goals", marker_color="#2ecc71",
                                 text=butterfly["Home Goals"].astype(int), textposition="inside"))
            fig.add_trace(go.Bar(y=butterfly["short"], x=butterfly["Away Goals"],
                                 orientation="h", name="Away Goals", marker_color="#3498db",
                                 text=butterfly["Away Goals"].astype(int), textposition="inside"))
            fig.update_layout(
                barmode="overlay", template="plotly_white", height=600,
                title="Home vs Away Goal Scoring - Butterfly Chart",
                xaxis_title="Goals (← Home | Away →)",
                xaxis=dict(tickvals=[-40, -30, -20, -10, 0, 10, 20, 30, 40],
                           ticktext=["40", "30", "20", "10", "0", "10", "20", "30", "40"])
            )
            fig.write_image(f"{IMG_DIR}/ro5_home_away_butterfly.png", width=1100, height=600, scale=2)
            charts.append("ro5_home_away_butterfly")

    # ---- RO6: Club Market Value Composition ----
    if not ro_players.empty:
        val_by_pos = ro_players.groupby(["short_team", "pos_group"])["market_value_eur_m"].sum().reset_index()
        if val_by_pos["market_value_eur_m"].sum() > 0:
            fig = px.bar(
                val_by_pos, x="short_team", y="market_value_eur_m", color="pos_group",
                barmode="stack",
                title="Club Squad Value Composition by Position",
                labels={"short_team": "Club", "market_value_eur_m": "Value (€M)", "pos_group": "Position"},
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(template="plotly_white", height=550, xaxis_tickangle=-40)
            fig.write_image(f"{IMG_DIR}/ro6_squad_value_composition.png", width=1100, height=550, scale=2)
            charts.append("ro6_squad_value_composition")

    # ---- RO7: Form Momentum Heatmap ----
    if not ro_events.empty:
        completed = ro_events.dropna(subset=["intHomeScore", "intAwayScore"]).copy()
        if not completed.empty and "intRound" in completed.columns:
            completed["intRound"] = pd.to_numeric(completed["intRound"], errors="coerce")
            completed = completed.dropna(subset=["intRound"])
            rows = []
            for _, m in completed.iterrows():
                hs, aws = int(m["intHomeScore"]), int(m["intAwayScore"])
                rd = int(m["intRound"])
                if hs > aws:
                    rows.append({"Team": m["strHomeTeam"], "Round": rd, "Result": 3})
                    rows.append({"Team": m["strAwayTeam"], "Round": rd, "Result": 0})
                elif hs == aws:
                    rows.append({"Team": m["strHomeTeam"], "Round": rd, "Result": 1})
                    rows.append({"Team": m["strAwayTeam"], "Round": rd, "Result": 1})
                else:
                    rows.append({"Team": m["strHomeTeam"], "Round": rd, "Result": 0})
                    rows.append({"Team": m["strAwayTeam"], "Round": rd, "Result": 3})
            if rows:
                rdf = pd.DataFrame(rows)
                rdf["short"] = rdf["Team"].map(SHORT_NAMES).fillna(rdf["Team"])
                pivot = rdf.pivot_table(index="short", columns="Round", values="Result", aggfunc="first")
                pivot = pivot.reindex(columns=sorted(pivot.columns))
                fig = px.imshow(
                    pivot, text_auto=True,
                    color_continuous_scale=[[0, "#e74c3c"], [0.33, "#e74c3c"],
                                            [0.33, "#f39c12"], [0.67, "#f39c12"],
                                            [0.67, "#2ecc71"], [1.0, "#2ecc71"]],
                    title="Season Form Heatmap (0=Loss, 1=Draw, 3=Win)",
                    labels={"x": "Round", "y": "Team", "color": "Points"},
                    aspect="auto"
                )
                fig.update_layout(template="plotly_white", height=600)
                fig.write_image(f"{IMG_DIR}/ro7_form_heatmap.png", width=1400, height=600, scale=2)
                charts.append("ro7_form_heatmap")

    # ---- RO8: Transfer Need Radar (top 6 clubs) ----
    if not ro_players.empty and not ro_standings.empty:
        top6_full = ro_standings.nlargest(6, "intPoints")["strTeam"].tolist()
        top6_short = [SHORT_NAMES.get(t, t) for t in top6_full]
        need_rows = []
        for full_t, short_t in zip(top6_full, top6_short):
            tp = ro_players[ro_players["short_team"] == short_t]
            if tp.empty:
                # Try matching by full team name
                tp = ro_players[ro_players["strTeam"].str.contains(full_t.split()[0], case=False, na=False)]
            avg_age = tp["age"].mean() if not tp.empty else 28
            total_val = tp["market_value_eur_m"].sum()
            depth = len(tp)
            foreigners = (~tp["strNationality"].str.contains("Romania", case=False, na=False)).sum() if not tp.empty else 0
            youth = (tp["age"] <= 21).sum() if not tp.empty else 0
            st_row = ro_standings[ro_standings["strTeam"] == full_t]
            gd = int(st_row["intGoalDifference"].iloc[0]) if not st_row.empty else 0
            need_rows.append({
                "Club": short_t,
                "Squad Depth": min(depth / 30 * 10, 10),
                "Youth Pipeline": min(youth / 5 * 10, 10),
                "Goal Diff Strength": min(max(gd + 30, 0) / 60 * 10, 10),
                "Market Value": min(total_val / 20 * 10, 10),
                "Foreign Talent": min(foreigners / 10 * 10, 10),
            })
        if need_rows:
            categories = ["Squad Depth", "Youth Pipeline", "Goal Diff Strength", "Market Value", "Foreign Talent"]
            fig = go.Figure()
            colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
            for i, row in enumerate(need_rows):
                vals = [row[c] for c in categories] + [row[categories[0]]]
                fig.add_trace(go.Scatterpolar(
                    r=vals, theta=categories + [categories[0]],
                    fill="toself", name=row["Club"],
                    line_color=colors[i % len(colors)], opacity=0.6
                ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                template="plotly_white", height=600,
                title="Top 6 Clubs - Strength Radar Comparison"
            )
            fig.write_image(f"{IMG_DIR}/ro8_club_radar.png", width=900, height=600, scale=2)
            charts.append("ro8_club_radar")

    print(f"    Romanian deep-dive charts: {len(charts)}")
    return charts
