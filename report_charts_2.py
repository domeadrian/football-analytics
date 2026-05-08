"""
Report Charts Part 2 - Charts for pages 7-13:
  7. Tactical Analysis (3 charts)
  8. Opponent Report (2 charts)
  9. Transfer Recommendations (2 charts)
  10. Physical & Medical (2 charts)
  11. Youth Academy (2 charts)
  12. Financial Analysis (3 charts)
  13. Season Projections (3 charts)
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from report_data import IMG_DIR, LEAGUE_STRENGTH, LEAGUE_MARKET


def generate_charts_part2(data):
    """Generate all charts for pages 7-13."""
    standings = data["standings"]
    events = data["events"]
    players = data["players"]
    ro_standings = data["ro_standings"]
    ro_events = data["ro_events"]
    playoff_teams_data = data["playoff_teams_data"]
    playout_teams_data = data["playout_teams_data"]

    charts_generated = []

    # ================================================================
    # PAGE 7: TACTICAL ANALYSIS (3 charts)
    # ================================================================
    print("  Generating Page 7: Tactical Analysis charts...")

    if not ro_standings.empty:
        # Chart 7.1: Attack vs Defense Quadrant
        # Use short team names to avoid label overlap
        _SHORT_NAMES = {
            "Universitatea Craiova": "U. Craiova", "Universitatea Cluj": "U. Cluj",
            "CFR Cluj": "CFR", "Dinamo Bucure\u0219ti": "Dinamo",
            "Rapid Bucure\u0219ti": "Rapid", "Arge\u0219 Pite\u0219ti": "Arge\u0219",
            "FCSB": "FCSB", "UTA Arad": "UTA", "Boto\u0219ani": "Boto\u0219ani",
            "Cs\u00edkszereda Miercurea Ciuc": "Cs\u00edkszereda",
            "O\u021belul Gala\u021bi": "O\u021belul", "Farul Constan\u021ba": "Farul",
            "Petrolul Ploie\u0219ti": "Petrolul", "Unirea Slobozia": "Unirea",
            "Hermannstadt": "Hermannstadt", "Metaloglobus Bucure\u0219ti": "Metaloglobus"
        }
        ro_plot = ro_standings.copy()
        ro_plot["short_name"] = ro_plot["strTeam"].map(_SHORT_NAMES).fillna(ro_plot["strTeam"])
        fig = px.scatter(
            ro_plot, x="intGoalsFor", y="intGoalsAgainst",
            text="short_name", size="intPoints", color="intPoints",
            color_continuous_scale="RdYlGn",
            title="Attack vs Defense Quadrant Analysis",
            labels={"intGoalsFor": "Goals Scored", "intGoalsAgainst": "Goals Conceded"}
        )
        # Spread labels with alternating positions to avoid overlap
        positions = ["top center", "bottom center", "top right", "bottom left",
                     "top left", "bottom right", "middle right", "middle left"]
        for i, trace in enumerate(fig.data):
            if hasattr(trace, 'textposition'):
                trace.textposition = [positions[j % len(positions)] for j in range(len(trace.x))]
        fig.update_traces(textfont_size=9)
        fig.update_layout(template="plotly_white", height=650,
                          xaxis=dict(range=[ro_plot['intGoalsFor'].min()-4, ro_plot['intGoalsFor'].max()+4]),
                          yaxis=dict(range=[ro_plot['intGoalsAgainst'].min()-4, ro_plot['intGoalsAgainst'].max()+8]))
        avg_gf = ro_standings["intGoalsFor"].mean()
        avg_ga = ro_standings["intGoalsAgainst"].mean()
        fig.add_hline(y=avg_ga, line_dash="dash", line_color="gray", annotation_text="Avg GA")
        fig.add_vline(x=avg_gf, line_dash="dash", line_color="gray", annotation_text="Avg GF")
        # Add quadrant labels
        fig.add_annotation(x=ro_plot["intGoalsFor"].max(), y=ro_plot["intGoalsAgainst"].min(),
                           text="ELITE", showarrow=False, font=dict(size=10, color="green"))
        fig.add_annotation(x=ro_plot["intGoalsFor"].min(), y=ro_plot["intGoalsAgainst"].max(),
                           text="STRUGGLING", showarrow=False, font=dict(size=10, color="red"))
        fig.write_image(f"{IMG_DIR}/07_attack_defense_quad.png", width=1100, height=650, scale=2)
        charts_generated.append("07_attack_defense_quad")

        # Chart 7.2: Win/Draw/Loss Stacked Bar
        wdl_data = ro_standings[["strTeam", "intWin", "intDraw", "intLoss"]].melt(
            id_vars="strTeam", var_name="Result", value_name="Count"
        )
        wdl_data["Result"] = wdl_data["Result"].map({"intWin": "Wins", "intDraw": "Draws", "intLoss": "Losses"})
        fig = px.bar(
            wdl_data, x="strTeam", y="Count", color="Result",
            color_discrete_map={"Wins": "#2ecc71", "Draws": "#f39c12", "Losses": "#e74c3c"},
            title="Tactical Profile: Win/Draw/Loss Composition per Team",
            barmode="stack"
        )
        fig.update_layout(template="plotly_white", height=500, xaxis_tickangle=-45)
        fig.write_image(f"{IMG_DIR}/07_wdl_stack.png", width=1000, height=550, scale=2)
        charts_generated.append("07_wdl_stack")

        # Chart 7.3: Points Per Game Efficiency with Trendline
        ro_standings["ppg"] = (ro_standings["intPoints"] / ro_standings["intPlayed"].replace(0, 1)).round(2)
        ro_standings["gd_per_game"] = (ro_standings["intGoalDifference"] / ro_standings["intPlayed"].replace(0, 1)).round(2)
        eff_plot = ro_standings.copy()
        eff_plot["short_name"] = eff_plot["strTeam"].map(_SHORT_NAMES).fillna(eff_plot["strTeam"])
        fig = px.scatter(
            eff_plot, x="ppg", y="gd_per_game", text="short_name",
            size="intPlayed", color="intPoints",
            color_continuous_scale="Viridis",
            title="Efficiency Matrix: Points Per Game vs Goal Difference Per Game",
            labels={"ppg": "Points Per Game", "gd_per_game": "GD Per Game"},
            trendline="ols"
        )
        positions = ["top right", "bottom left", "top left", "bottom right",
                     "top center", "bottom center", "middle right", "middle left"]
        for trace in fig.data:
            if hasattr(trace, 'textposition') and trace.text is not None:
                trace.textposition = [positions[j % len(positions)] for j in range(len(trace.x))]
        fig.update_traces(textfont_size=9)
        fig.update_layout(template="plotly_white", height=600)
        fig.write_image(f"{IMG_DIR}/07_efficiency_matrix.png", width=1100, height=600, scale=2)
        charts_generated.append("07_efficiency_matrix")

    # ================================================================
    # PAGE 8: OPPONENT REPORT (2 charts)
    # ================================================================
    print("  Generating Page 8: Opponent Report charts...")

    if not ro_standings.empty and len(ro_standings) >= 6:
        # Chart 8.1: Radar Chart - Top 6 Teams Comparison
        top6 = ro_standings.head(6).copy()
        metrics = ["intWin", "intDraw", "intGoalsFor", "intGoalDifference", "intPoints"]
        metric_labels = ["Wins", "Draws", "Goals Scored", "Goal Diff", "Points"]

        fig = go.Figure()
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
        for i, (_, team) in enumerate(top6.iterrows()):
            values = [team[m] for m in metrics]
            # Normalize to 0-100 for radar
            max_vals = [ro_standings[m].max() for m in metrics]
            norm_values = [v / mx * 100 if mx > 0 else 0 for v, mx in zip(values, max_vals)]
            norm_values.append(norm_values[0])  # close the polygon
            fig.add_trace(go.Scatterpolar(
                r=norm_values, theta=metric_labels + [metric_labels[0]],
                fill="toself", name=team["strTeam"],
                line=dict(color=colors[i % len(colors)])
            ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="Opponent Intelligence: Top 6 Teams Radar Comparison",
            height=550, template="plotly_white"
        )
        fig.write_image(f"{IMG_DIR}/08_radar_top6.png", width=900, height=550, scale=2)
        charts_generated.append("08_radar_top6")

        # Chart 8.2: Goal Difference Waterfall
        gd_sorted = ro_standings.sort_values("intGoalDifference", ascending=False)
        fig = px.bar(
            gd_sorted, x="strTeam", y="intGoalDifference",
            color="intGoalDifference", color_continuous_scale="RdYlGn",
            title="Goal Difference Ranking - Net Strength Indicator",
            text="intGoalDifference"
        )
        fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-45)
        fig.update_traces(textposition="outside")
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
        fig.write_image(f"{IMG_DIR}/08_goal_diff.png", width=900, height=500, scale=2)
        charts_generated.append("08_goal_diff")

    # ================================================================
    # PAGE 9: TRANSFER RECOMMENDATIONS (2 charts)
    # ================================================================
    print("  Generating Page 9: Transfer Recommendations charts...")

    if not players.empty and "age" in players.columns and "strPosition" in players.columns:
        # Chart 9.1: Transfer Market - Age vs Position Availability
        valid_players = players[(players["age"] > 16) & (players["age"] < 38)].dropna(subset=["strPosition"])
        if not valid_players.empty:
            top_positions = valid_players["strPosition"].value_counts().head(8).index.tolist()
            transfer_pool = valid_players[valid_players["strPosition"].isin(top_positions)]
            age_pos = transfer_pool.groupby(["strPosition", pd.cut(transfer_pool["age"], bins=[16,21,25,29,33,38])]).size().reset_index(name="Count")
            age_pos["Age Group"] = age_pos["age"].astype(str)
            fig = px.bar(
                age_pos, x="strPosition", y="Count", color="Age Group",
                title="Transfer Pool Analysis - Player Availability by Age & Position",
                barmode="stack"
            )
            fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-30)
            fig.write_image(f"{IMG_DIR}/09_transfer_pool.png", width=900, height=500, scale=2)
            charts_generated.append("09_transfer_pool")

        # Chart 9.2: Young Talent Pipeline (U23 by position)
        u23 = valid_players[valid_players["age"] <= 23]
        if not u23.empty:
            u23_pos = u23["strPosition"].value_counts().head(10)
            fig = px.pie(
                values=u23_pos.values, names=u23_pos.index,
                title="Young Talent Pipeline (U23) - Position Breakdown",
                hole=0.3
            )
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(height=450)
            fig.write_image(f"{IMG_DIR}/09_young_pipeline.png", width=700, height=450, scale=2)
            charts_generated.append("09_young_pipeline")

    # ================================================================
    # PAGE 10: PHYSICAL & MEDICAL (2 charts)
    # ================================================================
    print("  Generating Page 10: Physical & Medical charts...")

    if not players.empty and "age" in players.columns:
        # Chart 10.1: Squad Age Profile by Team (Romanian Liga I teams)
        if not ro_standings.empty and "strTeam" in players.columns:
            ro_team_names = ro_standings["strTeam"].tolist()
            ro_players = players[players["strTeam"].isin(ro_team_names)].copy()
            if not ro_players.empty and len(ro_players) > 10:
                team_age = ro_players.groupby("strTeam")["age"].agg(["mean", "std", "count"]).reset_index()
                team_age.columns = ["Team", "Avg Age", "Age Std", "Squad Size"]
                team_age = team_age[team_age["Squad Size"] >= 5].sort_values("Avg Age")

                if not team_age.empty:
                    fig = px.bar(
                        team_age, x="Team", y="Avg Age", color="Avg Age",
                        color_continuous_scale="RdYlGn_r",
                        title="Squad Age Profile - Romanian Liga I (Lower = Younger Squad)",
                        text="Avg Age", error_y="Age Std"
                    )
                    fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-45)
                    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                    fig.write_image(f"{IMG_DIR}/10_squad_age.png", width=900, height=500, scale=2)
                    charts_generated.append("10_squad_age")

        # Chart 10.2: Injury Risk Zone (players over 30 by position)
        over_30 = players[(players["age"] >= 30) & (players["age"] < 40)]
        if not over_30.empty and "strPosition" in over_30.columns:
            risk_pos = over_30["strPosition"].value_counts().head(8)
            fig = px.bar(
                x=risk_pos.index, y=risk_pos.values,
                labels={"x": "Position", "y": "Players 30+"},
                title="Injury Risk Zone - Players Over 30 by Position (Higher Physical Demand = Higher Risk)",
                color=risk_pos.values, color_continuous_scale="Reds"
            )
            fig.update_layout(template="plotly_white", height=400, xaxis_tickangle=-30, showlegend=False)
            fig.write_image(f"{IMG_DIR}/10_injury_risk.png", width=800, height=450, scale=2)
            charts_generated.append("10_injury_risk")

    # ================================================================
    # PAGE 11: YOUTH ACADEMY (2 charts)
    # ================================================================
    print("  Generating Page 11: Youth Academy charts...")

    if not players.empty and "age" in players.columns:
        # Chart 11.1: U21 Players per Team (Romanian Liga I)
        if not ro_standings.empty and "strTeam" in players.columns:
            ro_team_names = ro_standings["strTeam"].tolist()
            ro_players = players[players["strTeam"].isin(ro_team_names)].copy()
            if not ro_players.empty:
                u21_count = ro_players[ro_players["age"] <= 21].groupby("strTeam").size().reset_index(name="U21 Players")
                total_count = ro_players.groupby("strTeam").size().reset_index(name="Total")
                youth_df = u21_count.merge(total_count, on="strTeam", how="right").fillna(0)
                youth_df["U21 %"] = (youth_df["U21 Players"] / youth_df["Total"] * 100).round(1)
                youth_df = youth_df.sort_values("U21 %", ascending=False)

                if not youth_df.empty:
                    fig = px.bar(
                        youth_df, x="strTeam", y="U21 %", color="U21 %",
                        color_continuous_scale="Greens",
                        title="Youth Academy Investment - U21 Players % per Squad (Romanian Liga I)",
                        text="U21 %"
                    )
                    fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-45)
                    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                    fig.write_image(f"{IMG_DIR}/11_youth_pct.png", width=900, height=500, scale=2)
                    charts_generated.append("11_youth_pct")

        # Chart 11.2: Development Curve - Age Bands Distribution
        age_bands = pd.cut(players["age"].dropna(), bins=[15, 18, 21, 24, 27, 30, 33, 40],
                           labels=["15-18", "18-21", "21-24", "24-27", "27-30", "30-33", "33+"])
        band_counts = age_bands.value_counts().sort_index()
        fig = px.area(
            x=band_counts.index.astype(str), y=band_counts.values,
            labels={"x": "Age Band", "y": "Number of Players"},
            title="Player Development Curve - Age Band Distribution (Peak: 24-27)"
        )
        fig.update_layout(template="plotly_white", height=400)
        fig.update_traces(fill="tozeroy", line_color="#3498db")
        fig.write_image(f"{IMG_DIR}/11_dev_curve.png", width=800, height=450, scale=2)
        charts_generated.append("11_dev_curve")

    # ================================================================
    # PAGE 12: FINANCIAL ANALYSIS (3 charts)
    # ================================================================
    print("  Generating Page 12: Financial Analysis charts...")

    if not standings.empty:
        # Chart 12.1: Points Efficiency by League Market Value
        fin_data = []
        for lg in standings["league"].unique():
            ldf = standings[standings["league"] == lg]
            market = LEAGUE_MARKET.get(lg, 5)
            avg_pts = ldf["intPoints"].mean()
            fin_data.append({
                "League": lg,
                "Market Value (M€)": market,
                "Avg Points": avg_pts,
                "Points per M€": round(avg_pts / max(market, 1), 2),
                "Teams": len(ldf)
            })
        fin_df = pd.DataFrame(fin_data).sort_values("Points per M€", ascending=False)

        fig = px.bar(
            fin_df, x="League", y="Points per M€", color="Market Value (M€)",
            color_continuous_scale="YlOrRd",
            title="Financial Efficiency - Points per Market Value (M€)",
            text="Points per M€"
        )
        fig.update_layout(template="plotly_white", height=500, xaxis_tickangle=-40)
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.write_image(f"{IMG_DIR}/12_financial_efficiency.png", width=1000, height=550, scale=2)
        charts_generated.append("12_financial_efficiency")

        # Chart 12.2: Market Value vs Performance (scatter)
        fig = px.scatter(
            fin_df, x="Market Value (M€)", y="Avg Points", size="Teams",
            color="League", text="League",
            title="Market Value vs Average Points - Does Money Buy Success?",
            trendline="ols"
        )
        fig.update_traces(textposition="top center", textfont_size=7)
        fig.update_layout(template="plotly_white", height=500, showlegend=False)
        fig.write_image(f"{IMG_DIR}/12_money_performance.png", width=900, height=500, scale=2)
        charts_generated.append("12_money_performance")

        # Chart 12.3: League Budget Tiers
        fin_df["Tier"] = pd.cut(fin_df["Market Value (M€)"], bins=[0, 20, 80, 200, 600],
                                labels=["Tier 4 (< 20M)", "Tier 3 (20-80M)", "Tier 2 (80-200M)", "Tier 1 (200M+)"])
        tier_stats = fin_df.groupby("Tier", observed=True).agg(
            Leagues=("League", "count"),
            Avg_Market=("Market Value (M€)", "mean"),
            Avg_Points=("Avg Points", "mean")
        ).reset_index()
        fig = px.bar(
            tier_stats, x="Tier", y="Avg_Market", color="Avg_Points",
            color_continuous_scale="RdYlGn",
            title="League Financial Tiers - Budget Classification",
            text="Leagues"
        )
        fig.update_layout(template="plotly_white", height=400)
        fig.update_traces(texttemplate="<b>%{text} leagues</b>", textposition="outside")
        fig.write_image(f"{IMG_DIR}/12_budget_tiers.png", width=800, height=450, scale=2)
        charts_generated.append("12_budget_tiers")

    # ================================================================
    # PAGE 13: SEASON PROJECTIONS (3 charts)
    # ================================================================
    print("  Generating Page 13: Season Projections charts...")

    if not ro_standings.empty:
        # Chart 13.1: ELO-style Rating
        ro_standings["elo"] = 1500 + (ro_standings["intGoalDifference"] * 5) + (ro_standings["intPoints"] * 2)
        elo_sorted = ro_standings.sort_values("elo", ascending=False)
        fig = px.bar(
            elo_sorted, x="strTeam", y="elo", color="elo",
            color_continuous_scale="Spectral",
            title="ELO Power Rating - Combined Metric (Base 1500 + GD×5 + Pts×2)",
            text="elo"
        )
        fig.update_layout(template="plotly_white", height=500, xaxis_tickangle=-45)
        fig.update_traces(textposition="outside")
        fig.add_hline(y=1500, line_dash="dash", line_color="gray", annotation_text="Average (1500)")
        fig.write_image(f"{IMG_DIR}/13_elo_rating.png", width=900, height=500, scale=2)
        charts_generated.append("13_elo_rating")

        # Chart 13.2: Points Projection (linear extrapolation)
        if "intPlayed" in ro_standings.columns:
            max_matches = 40  # total possible matches
            ro_standings["projected_pts"] = (ro_standings["intPoints"] / ro_standings["intPlayed"].replace(0, 1) * max_matches).round(0)
            proj_sorted = ro_standings.sort_values("projected_pts", ascending=False)

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(
                x=proj_sorted["strTeam"], y=proj_sorted["intPoints"],
                name="Current Points", marker_color="#3498db"
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=proj_sorted["strTeam"], y=proj_sorted["projected_pts"],
                name="Projected (40 matches)", mode="lines+markers",
                line=dict(color="#e74c3c", width=2, dash="dash")
            ), secondary_y=False)
            fig.update_layout(title="Season Points Projection (Linear Extrapolation to 40 Matches)",
                              template="plotly_white", height=500, xaxis_tickangle=-45)
            fig.write_image(f"{IMG_DIR}/13_projection.png", width=900, height=500, scale=2)
            charts_generated.append("13_projection")

        # Chart 13.3: Form Indicator (Points accumulation ranking)
        # Use win rate as form proxy
        ro_standings["win_rate"] = (ro_standings["intWin"] / ro_standings["intPlayed"].replace(0, 1) * 100).round(1)
        form_sorted = ro_standings.sort_values("win_rate", ascending=False)
        fig = px.bar(
            form_sorted, x="strTeam", y="win_rate", color="win_rate",
            color_continuous_scale="RdYlGn",
            title="Win Rate % - Current Form Indicator (Higher = Better Form)",
            text="win_rate"
        )
        fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-45)
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.write_image(f"{IMG_DIR}/13_win_rate.png", width=900, height=500, scale=2)
        charts_generated.append("13_win_rate")

    print(f"  Part 2 complete: {len(charts_generated)} charts generated")
    return charts_generated
