"""
Report Charts Part 1 - Charts for pages 1-6:
  1. Overview & Standings (4 charts)
  2. Match Analysis (4 charts)
  3. Championship Probability (3 charts)
  4. European Comparison (3 charts)
  5. Player Analysis (3 charts)
  6. Scouting Intelligence (3 charts)
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import poisson
from report_data import IMG_DIR, LEAGUE_STRENGTH, LEAGUE_MARKET

REGULAR_SEASON_ROUNDS = 30
PLAYOFF_TOTAL_ROUNDS = 10


def generate_charts_part1(data):
    """Generate all charts for pages 1-6."""
    standings = data["standings"]
    events = data["events"]
    players = data["players"]
    ro_standings = data["ro_standings"]
    ro_events = data["ro_events"]
    playoff_teams_data = data["playoff_teams_data"]
    playout_teams_data = data["playout_teams_data"]

    charts_generated = []

    # ================================================================
    # PAGE 1: OVERVIEW & STANDINGS (4 charts)
    # ================================================================
    print("  Generating Page 1: Overview & Standings charts...")

    # Chart 1.1: Full League Table Bar Chart
    if not ro_standings.empty:
        fig = px.bar(
            ro_standings.sort_values("intPoints"),
            x="intPoints", y="strTeam", orientation="h",
            color="intPoints", color_continuous_scale="YlOrRd",
            text="intPoints",
            title="Romanian Liga I 2025-2026 - Full Points Distribution"
        )
        fig.update_layout(template="plotly_white", height=600, showlegend=False,
                          yaxis={"categoryorder": "total ascending"})
        fig.update_traces(textposition="outside")
        fig.write_image(f"{IMG_DIR}/01_standings_full.png", width=900, height=600, scale=2)
        charts_generated.append("01_standings_full")

    # Chart 1.2: Playoff Standings
    if playoff_teams_data:
        po_df = pd.DataFrame(playoff_teams_data).sort_values("intPoints", ascending=False)
        fig = px.bar(
            po_df, x="strTeam", y="intPoints", color="intPoints",
            color_continuous_scale="Greens",
            title="Championship Playoff - Current Standings (Halved + Playoff Points)",
            text="intPoints"
        )
        fig.update_layout(template="plotly_white", height=400, xaxis_tickangle=-20)
        fig.update_traces(textposition="outside")
        fig.write_image(f"{IMG_DIR}/01_playoff_standings.png", width=900, height=450, scale=2)
        charts_generated.append("01_playoff_standings")

    # Chart 1.3: Playout Standings with Relegation Zones
    if playout_teams_data:
        pl_df = pd.DataFrame(playout_teams_data).sort_values("intPoints", ascending=False)
        n_playout = len(pl_df)
        zone_list = []
        for idx in range(n_playout):
            if idx >= n_playout - 2:
                zone_list.append("Direct Relegation")
            elif idx >= n_playout - 4:
                zone_list.append("Relegation Playoff")
            else:
                zone_list.append("Safe")
        pl_df = pl_df.reset_index(drop=True)
        pl_df["Zone"] = zone_list
        fig = px.bar(
            pl_df, x="strTeam", y="intPoints", color="Zone",
            color_discrete_map={"Safe": "#2ecc71", "Relegation Playoff": "#f39c12", "Direct Relegation": "#e74c3c"},
            title="Relegation Playout - Standings & Danger Zones",
            text="intPoints"
        )
        fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-35)
        fig.update_traces(textposition="outside")
        fig.write_image(f"{IMG_DIR}/01_playout_standings.png", width=900, height=500, scale=2)
        charts_generated.append("01_playout_standings")

    # Chart 1.4: Points Distribution - All Leagues Top 3
    if not standings.empty:
        top_teams = pd.concat([
            g.nlargest(min(3, len(g)), "intPoints")
            for _, g in standings.groupby("league")
        ], ignore_index=True)
        if not top_teams.empty:
            fig = px.bar(
                top_teams.sort_values(["league", "intPoints"]),
                x="intPoints", y="strTeam", color="league", orientation="h",
                text="intPoints", height=max(500, len(top_teams) * 28),
                title="Points Distribution - Top 3 Teams per League (All 15 Leagues)"
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(template="plotly_white", yaxis={"categoryorder": "total ascending"},
                              legend=dict(orientation="h", yanchor="bottom", y=-0.3))
            fig.write_image(f"{IMG_DIR}/01_all_leagues_top3.png", width=1000, height=900, scale=2)
            charts_generated.append("01_all_leagues_top3")

    # ================================================================
    # PAGE 2: MATCH ANALYSIS (4 charts)
    # ================================================================
    print("  Generating Page 2: Match Analysis charts...")

    if not ro_events.empty and "intHomeScore" in ro_events.columns:
        completed = ro_events.dropna(subset=["intHomeScore", "intAwayScore"]).copy()
        if not completed.empty:
            completed["intHomeScore"] = completed["intHomeScore"].astype(int)
            completed["intAwayScore"] = completed["intAwayScore"].astype(int)
            completed["total_goals"] = completed["intHomeScore"] + completed["intAwayScore"]

            # Chart 2.1: Match Outcome Distribution (Home/Draw/Away)
            completed["result"] = np.where(
                completed["intHomeScore"] > completed["intAwayScore"], "Home Win",
                np.where(completed["intHomeScore"] < completed["intAwayScore"], "Away Win", "Draw")
            )
            result_counts = completed["result"].value_counts()
            fig = px.pie(
                values=result_counts.values, names=result_counts.index,
                color=result_counts.index,
                color_discrete_map={"Home Win": "#2ecc71", "Draw": "#f39c12", "Away Win": "#e74c3c"},
                title="Match Outcome Distribution - Home Advantage Analysis"
            )
            fig.update_traces(textinfo="percent+label+value")
            fig.update_layout(height=450)
            fig.write_image(f"{IMG_DIR}/02_outcome_distribution.png", width=700, height=450, scale=2)
            charts_generated.append("02_outcome_distribution")

            # Chart 2.2: Goals per Match Distribution
            goals_dist = completed["total_goals"].value_counts().sort_index()
            fig = px.bar(
                x=goals_dist.index, y=goals_dist.values,
                labels={"x": "Total Goals in Match", "y": "Number of Matches"},
                title="Goals per Match Distribution - Romanian Liga I",
                color=goals_dist.values, color_continuous_scale="Blues"
            )
            fig.update_layout(template="plotly_white", height=400, showlegend=False)
            fig.add_vline(x=completed["total_goals"].mean(), line_dash="dash", line_color="red",
                          annotation_text=f"Avg: {completed['total_goals'].mean():.2f}")
            fig.write_image(f"{IMG_DIR}/02_goals_distribution.png", width=800, height=450, scale=2)
            charts_generated.append("02_goals_distribution")

            # Chart 2.3: Score Heatmap
            max_goals = min(int(completed["intHomeScore"].max()), 6)
            heatmap_data = np.zeros((max_goals + 1, max_goals + 1))
            for _, row in completed.iterrows():
                h, a = int(row["intHomeScore"]), int(row["intAwayScore"])
                if h <= max_goals and a <= max_goals:
                    heatmap_data[h][a] += 1
            fig = px.imshow(
                heatmap_data, labels=dict(x="Away Goals", y="Home Goals", color="Frequency"),
                x=[str(i) for i in range(max_goals + 1)],
                y=[str(i) for i in range(max_goals + 1)],
                color_continuous_scale="YlOrRd",
                title="Scoreline Heatmap - Most Common Results"
            )
            fig.update_layout(height=450)
            fig.write_image(f"{IMG_DIR}/02_score_heatmap.png", width=600, height=500, scale=2)
            charts_generated.append("02_score_heatmap")

            # Chart 2.4: Monthly Goals Trend
            if "dateEvent" in completed.columns:
                completed_dated = completed.dropna(subset=["dateEvent"])
                if not completed_dated.empty:
                    completed_dated["month"] = completed_dated["dateEvent"].dt.to_period("M").astype(str)
                    monthly = completed_dated.groupby("month").agg(
                        matches=("total_goals", "count"),
                        avg_goals=("total_goals", "mean"),
                        total_goals=("total_goals", "sum")
                    ).reset_index()
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(go.Bar(x=monthly["month"], y=monthly["matches"], name="Matches", marker_color="#3498db"), secondary_y=False)
                    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["avg_goals"], name="Avg Goals/Match",
                                            mode="lines+markers", line=dict(color="#e74c3c", width=3)), secondary_y=True)
                    fig.update_layout(title="Monthly Match Volume & Average Goals", template="plotly_white", height=400)
                    fig.update_yaxes(title_text="Number of Matches", secondary_y=False)
                    fig.update_yaxes(title_text="Avg Goals per Match", secondary_y=True)
                    fig.write_image(f"{IMG_DIR}/02_monthly_trend.png", width=900, height=450, scale=2)
                    charts_generated.append("02_monthly_trend")

    # ================================================================
    # PAGE 3: CHAMPIONSHIP PROBABILITY (3 charts)
    # ================================================================
    print("  Generating Page 3: Championship Probability charts...")

    np.random.seed(42)
    n_sims = 10000

    if playoff_teams_data:
        # Calculate remaining playoff rounds
        playoff_rounds_played = min(t["intPlayed"] for t in playoff_teams_data) - REGULAR_SEASON_ROUNDS
        remaining_playoff = max(PLAYOFF_TOTAL_ROUNDS - playoff_rounds_played, 0)

        # Run Monte Carlo
        results = {}
        for team in playoff_teams_data:
            played = max(team["intPlayed"], 1)
            w_rate = team["intWin"] / played
            d_rate = team["intDraw"] / played
            sim_points = []
            for _ in range(n_sims):
                extra = 0
                for _ in range(remaining_playoff):
                    r = np.random.random()
                    if r < w_rate:
                        extra += 3
                    elif r < w_rate + d_rate:
                        extra += 1
                sim_points.append(team["intPoints"] + extra)
            results[team["strTeam"]] = sim_points

        # Title probability
        title_wins = {team: 0 for team in results}
        teams_list = list(results.keys())
        for i in range(n_sims):
            max_pts = max(results[t][i] for t in teams_list)
            tied_teams = [t for t in teams_list if results[t][i] == max_pts]
            winner = tied_teams[np.random.randint(len(tied_teams))]
            title_wins[winner] += 1

        title_probs = {team: title_wins[team] / n_sims * 100 for team in teams_list}

        # Chart 3.1: Championship Probability Bar
        prob_df = pd.DataFrame({"Team": list(title_probs.keys()), "Title %": list(title_probs.values())})
        prob_df = prob_df.sort_values("Title %", ascending=False)
        fig = px.bar(
            prob_df, x="Team", y="Title %", color="Title %",
            color_continuous_scale="YlOrRd",
            title=f"Championship Probability - Playoff ({n_sims:,} simulations, {remaining_playoff} rounds left)",
            text="Title %"
        )
        fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-20)
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.write_image(f"{IMG_DIR}/03_monte_carlo.png", width=900, height=500, scale=2)
        charts_generated.append("03_monte_carlo")

        # Chart 3.2: Points Distribution Violin/Box per Team
        sim_df_list = []
        for team, pts in results.items():
            for p in pts[:500]:  # sample for visualization
                sim_df_list.append({"Team": team, "Simulated Points": p})
        sim_df = pd.DataFrame(sim_df_list)
        fig = px.box(
            sim_df, x="Team", y="Simulated Points", color="Team",
            title="Points Distribution Range - Monte Carlo Simulation (500 sample per team)"
        )
        fig.update_layout(template="plotly_white", height=450, showlegend=False, xaxis_tickangle=-20)
        fig.write_image(f"{IMG_DIR}/03_points_range.png", width=900, height=500, scale=2)
        charts_generated.append("03_points_range")

        # Chart 3.3: Top 3 Probability Gauge
        top3 = prob_df.head(3)
        fig = make_subplots(rows=1, cols=3, specs=[[{"type": "indicator"}]*3],
                            subplot_titles=top3["Team"].tolist())
        for i, (_, row) in enumerate(top3.iterrows()):
            fig.add_trace(go.Indicator(
                mode="gauge+number", value=row["Title %"],
                number={"suffix": "%"},
                gauge={"axis": {"range": [0, 100]},
                       "bar": {"color": ["#e74c3c", "#f39c12", "#3498db"][i]},
                       "steps": [{"range": [0, 50], "color": "#ecf0f1"}, {"range": [50, 100], "color": "#d5f5e3"}]}
            ), row=1, col=i+1)
        fig.update_layout(height=300, title_text="Top 3 Championship Contenders - Win Probability")
        fig.write_image(f"{IMG_DIR}/03_gauges.png", width=900, height=350, scale=2)
        charts_generated.append("03_gauges")

    # ================================================================
    # PAGE 4: EUROPEAN COMPARISON (3 charts)
    # ================================================================
    print("  Generating Page 4: European Comparison charts...")

    if not standings.empty:
        # Chart 4.1: Average Goals per Team by League
        league_stats = []
        for lg in standings["league"].unique():
            ldf = standings[standings["league"] == lg]
            league_stats.append({
                "League": lg,
                "Avg Points": round(ldf["intPoints"].mean(), 1),
                "Avg GF": round(ldf["intGoalsFor"].mean(), 1),
                "Avg GA": round(ldf["intGoalsAgainst"].mean(), 1),
                "Points Std": round(ldf["intPoints"].std(), 1),
                "Teams": len(ldf),
                "Total Goals": ldf["intGoalsFor"].sum(),
                "Strength": LEAGUE_STRENGTH.get(lg, 0.3),
                "Market (M€)": LEAGUE_MARKET.get(lg, 5),
            })
        ls_df = pd.DataFrame(league_stats).sort_values("Avg GF", ascending=False)

        fig = px.bar(
            ls_df, x="League", y="Avg GF", color="Strength",
            color_continuous_scale="RdYlGn",
            title="European Comparison - Avg Goals Scored per Team (colored by League Strength)",
            text="Avg GF"
        )
        fig.update_layout(template="plotly_white", height=500, xaxis_tickangle=-40)
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.write_image(f"{IMG_DIR}/04_euro_goals.png", width=1000, height=550, scale=2)
        charts_generated.append("04_euro_goals")

        # Chart 4.2: Competitiveness Index (Points Std - lower = more competitive)
        fig = px.bar(
            ls_df.sort_values("Points Std"),
            x="Points Std", y="League", orientation="h",
            color="Points Std", color_continuous_scale="RdYlGn_r",
            title="League Competitiveness Index (Lower Std Dev = More Competitive)",
            text="Points Std"
        )
        fig.update_layout(template="plotly_white", height=500)
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.write_image(f"{IMG_DIR}/04_competitiveness.png", width=900, height=550, scale=2)
        charts_generated.append("04_competitiveness")

        # Chart 4.3: League Strength vs Market Value bubble
        fig = px.scatter(
            ls_df, x="Strength", y="Market (M€)", size="Total Goals",
            color="League", text="League",
            title="League Strength vs Market Value (bubble = total goals)",
            size_max=50
        )
        fig.update_traces(textposition="top center", textfont_size=8)
        fig.update_layout(template="plotly_white", height=500, showlegend=False)
        fig.write_image(f"{IMG_DIR}/04_strength_market.png", width=900, height=550, scale=2)
        charts_generated.append("04_strength_market")

    # ================================================================
    # PAGE 5: PLAYER ANALYSIS (3 charts)
    # ================================================================
    print("  Generating Page 5: Player Analysis charts...")

    if not players.empty:
        # Chart 5.1: Age Distribution
        if "age" in players.columns:
            valid_ages = players[(players["age"] > 15) & (players["age"] < 45)]
            if not valid_ages.empty:
                fig = px.histogram(
                    valid_ages, x="age", nbins=30, color_discrete_sequence=["#3498db"],
                    title="Player Age Distribution - All Leagues (2025-2026 Season)",
                    labels={"age": "Age", "count": "Number of Players"}
                )
                fig.add_vline(x=valid_ages["age"].mean(), line_dash="dash", line_color="red",
                              annotation_text=f"Mean: {valid_ages['age'].mean():.1f}")
                fig.add_vline(x=valid_ages["age"].median(), line_dash="dot", line_color="green",
                              annotation_text=f"Median: {valid_ages['age'].median():.1f}")
                fig.update_layout(template="plotly_white", height=400)
                fig.write_image(f"{IMG_DIR}/05_age_distribution.png", width=800, height=450, scale=2)
                charts_generated.append("05_age_distribution")

        # Chart 5.2: Position Distribution
        if "strPosition" in players.columns:
            pos_counts = players["strPosition"].dropna().value_counts().head(15)
            fig = px.bar(
                x=pos_counts.index, y=pos_counts.values,
                labels={"x": "Position", "y": "Count"},
                title="Player Position Distribution - Top 15 Positions",
                color=pos_counts.values, color_continuous_scale="Viridis"
            )
            fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-45, showlegend=False)
            fig.write_image(f"{IMG_DIR}/05_position_distribution.png", width=900, height=500, scale=2)
            charts_generated.append("05_position_distribution")

        # Chart 5.3: Nationality Distribution (Top 20)
        if "strNationality" in players.columns:
            nat_counts = players["strNationality"].dropna().value_counts().head(20)
            fig = px.bar(
                x=nat_counts.values, y=nat_counts.index, orientation="h",
                labels={"x": "Number of Players", "y": "Nationality"},
                title="Player Nationality Distribution - Top 20 Nationalities",
                color=nat_counts.values, color_continuous_scale="Plasma"
            )
            fig.update_layout(template="plotly_white", height=600, showlegend=False,
                              yaxis={"categoryorder": "total ascending"})
            fig.write_image(f"{IMG_DIR}/05_nationality.png", width=900, height=600, scale=2)
            charts_generated.append("05_nationality")

    # ================================================================
    # PAGE 6: SCOUTING INTELLIGENCE (3 charts)
    # ================================================================
    print("  Generating Page 6: Scouting Intelligence charts...")

    if not players.empty and "age" in players.columns:
        # Chart 6.1: Wonderkid Radar - Best U21 players
        u21 = players[(players["age"] <= 21) & (players["age"] > 16)].copy()
        if not u21.empty and "strPosition" in u21.columns:
            # Score based on age (younger = higher potential)
            u21["potential_score"] = (22 - u21["age"]) * 10  # Simple potential metric
            top_wonderkids = u21.nlargest(min(20, len(u21)), "potential_score")

            if not top_wonderkids.empty:
                fig = px.scatter(
                    top_wonderkids, x="age", y="potential_score",
                    color="strPosition", text="strPlayer" if "strPlayer" in top_wonderkids.columns else None,
                    title="Wonderkid Radar - Top U21 Prospects (Higher = More Potential)",
                    size="potential_score", size_max=20
                )
                fig.update_traces(textposition="top center", textfont_size=7)
                fig.update_layout(template="plotly_white", height=500)
                fig.write_image(f"{IMG_DIR}/06_wonderkids.png", width=900, height=500, scale=2)
                charts_generated.append("06_wonderkids")

        # Chart 6.2: Age vs Position Heatmap
        if "strPosition" in players.columns:
            pos_age = players.dropna(subset=["age", "strPosition"])
            if not pos_age.empty:
                top_pos = pos_age["strPosition"].value_counts().head(8).index.tolist()
                pos_age_filtered = pos_age[pos_age["strPosition"].isin(top_pos)]
                fig = px.violin(
                    pos_age_filtered, x="strPosition", y="age", color="strPosition",
                    title="Age Distribution by Position - Squad Planning Insight",
                    box=True, points=False
                )
                fig.update_layout(template="plotly_white", height=450, showlegend=False, xaxis_tickangle=-30)
                fig.write_image(f"{IMG_DIR}/06_age_position.png", width=900, height=500, scale=2)
                charts_generated.append("06_age_position")

        # Chart 6.3: Scouting Coverage Map (players per league)
        if "strTeam" in players.columns:
            # Map players to leagues through team matching with standings
            player_league_counts = []
            for lg in standings["league"].unique() if not standings.empty else []:
                lg_teams = standings[standings["league"] == lg]["strTeam"].unique()
                count = players[players["strTeam"].isin(lg_teams)].shape[0] if "strTeam" in players.columns else 0
                if count > 0:
                    player_league_counts.append({"League": lg, "Players Scouted": count})
            if player_league_counts:
                plc_df = pd.DataFrame(player_league_counts).sort_values("Players Scouted", ascending=False)
                fig = px.bar(
                    plc_df, x="League", y="Players Scouted", color="Players Scouted",
                    color_continuous_scale="Turbo",
                    title="Scouting Database Coverage - Players per League",
                    text="Players Scouted"
                )
                fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-40, showlegend=False)
                fig.update_traces(textposition="outside")
                fig.write_image(f"{IMG_DIR}/06_scouting_coverage.png", width=900, height=500, scale=2)
                charts_generated.append("06_scouting_coverage")

    print(f"  Part 1 complete: {len(charts_generated)} charts generated")
    return charts_generated
