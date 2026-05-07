"""
Report Charts Part 3 - Charts for pages 14-16:
  14. ML Prediction Models (3 charts)
  15. Advanced Statistics (3 charts)
  16. League Management (2 charts)
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import poisson
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from report_data import IMG_DIR, LEAGUE_STRENGTH


def generate_charts_part3(data):
    """Generate all charts for pages 14-16."""
    standings = data["standings"]
    events = data["events"]
    players = data["players"]
    ro_standings = data["ro_standings"]
    ro_events = data["ro_events"]

    charts_generated = []

    # ================================================================
    # PAGE 14: ML PREDICTION MODELS (3 charts)
    # ================================================================
    print("  Generating Page 14: ML Prediction Models charts...")

    if not ro_standings.empty and len(ro_standings) >= 6:
        # Chart 14.1: K-Means Clustering of Teams
        features = ["intWin", "intDraw", "intLoss", "intGoalsFor", "intGoalsAgainst", "intPoints"]
        available_features = [f for f in features if f in ro_standings.columns]
        if len(available_features) >= 4:
            X = ro_standings[available_features].values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            n_clusters = min(4, len(ro_standings))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            ro_standings["cluster"] = kmeans.fit_predict(X_scaled)

            # Map clusters to performance tiers
            cluster_pts = ro_standings.groupby("cluster")["intPoints"].mean().sort_values(ascending=False)
            tier_map = {c: f"Tier {i+1}" for i, c in enumerate(cluster_pts.index)}
            ro_standings["tier"] = ro_standings["cluster"].map(tier_map)

            fig = px.scatter(
                ro_standings, x="intGoalsFor", y="intGoalsAgainst",
                color="tier", text="strTeam", size="intPoints",
                title="K-Means Clustering - Team Performance Tiers (4 clusters)",
                labels={"intGoalsFor": "Goals Scored", "intGoalsAgainst": "Goals Conceded"},
                color_discrete_sequence=["#2ecc71", "#3498db", "#f39c12", "#e74c3c"]
            )
            fig.update_traces(textposition="top center", textfont_size=8)
            fig.update_layout(template="plotly_white", height=550)
            fig.write_image(f"{IMG_DIR}/14_kmeans.png", width=900, height=550, scale=2)
            charts_generated.append("14_kmeans")

            # Chart 14.2: Feature Importance (simulated Random Forest)
            # Create match outcome classification based on GD
            ro_standings["outcome_class"] = np.where(ro_standings["intGoalDifference"] > 5, "Strong",
                                             np.where(ro_standings["intGoalDifference"] > 0, "Average", "Weak"))
            class_map = {"Strong": 2, "Average": 1, "Weak": 0}
            y = ro_standings["outcome_class"].map(class_map).values

            if len(np.unique(y)) > 1:
                rf = RandomForestClassifier(n_estimators=100, random_state=42)
                rf.fit(X_scaled, y)
                importances = rf.feature_importances_
                imp_df = pd.DataFrame({"Feature": available_features, "Importance": importances})
                imp_df["Feature"] = imp_df["Feature"].str.replace("int", "")
                imp_df = imp_df.sort_values("Importance", ascending=False)

                fig = px.bar(
                    imp_df, x="Feature", y="Importance", color="Importance",
                    color_continuous_scale="Viridis",
                    title="Random Forest - Feature Importance for Team Classification",
                    text="Importance"
                )
                fig.update_layout(template="plotly_white", height=400)
                fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
                fig.write_image(f"{IMG_DIR}/14_feature_importance.png", width=800, height=450, scale=2)
                charts_generated.append("14_feature_importance")

            # Chart 14.3: Prediction Accuracy - Actual vs Predicted Points
            from sklearn.linear_model import LinearRegression
            X_pred = ro_standings[["intWin", "intDraw", "intGoalsFor", "intGoalDifference"]].values
            y_pts = ro_standings["intPoints"].values
            lr = LinearRegression()
            lr.fit(X_pred, y_pts)
            predicted_pts = lr.predict(X_pred)
            ro_standings["predicted_pts"] = predicted_pts.round(1)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ro_standings["intPoints"], y=ro_standings["predicted_pts"],
                mode="markers+text", text=ro_standings["strTeam"],
                textposition="top center", textfont_size=7,
                marker=dict(size=10, color=ro_standings["intPoints"], colorscale="Viridis"),
                name="Teams"
            ))
            # Perfect prediction line
            min_pts, max_pts = ro_standings["intPoints"].min(), ro_standings["intPoints"].max()
            fig.add_trace(go.Scatter(
                x=[min_pts, max_pts], y=[min_pts, max_pts],
                mode="lines", line=dict(dash="dash", color="red"), name="Perfect Prediction"
            ))
            r2 = lr.score(X_pred, y_pts)
            fig.update_layout(
                title=f"Linear Regression - Actual vs Predicted Points (R² = {r2:.4f})",
                xaxis_title="Actual Points", yaxis_title="Predicted Points",
                template="plotly_white", height=500
            )
            fig.write_image(f"{IMG_DIR}/14_regression.png", width=800, height=500, scale=2)
            charts_generated.append("14_regression")

    # ================================================================
    # PAGE 15: ADVANCED STATISTICS (3 charts)
    # ================================================================
    print("  Generating Page 15: Advanced Statistics charts...")

    if not ro_standings.empty:
        # Chart 15.1: Expected Goals (Poisson Model) - Top 6
        top6 = ro_standings.head(6)
        league_avg_gf = ro_standings["intGoalsFor"].sum() / max(ro_standings["intPlayed"].sum(), 1)

        poisson_data = []
        for _, team in top6.iterrows():
            played = max(team["intPlayed"], 1)
            attack_strength = (team["intGoalsFor"] / played) / max(league_avg_gf, 0.01)
            xg = attack_strength * league_avg_gf
            for goals in range(7):
                prob = poisson.pmf(goals, max(xg, 0.1))
                poisson_data.append({"Team": team["strTeam"], "Goals": goals, "Probability": round(prob, 4)})

        poi_df = pd.DataFrame(poisson_data)
        fig = px.bar(
            poi_df, x="Goals", y="Probability", color="Team",
            barmode="group", title="Expected Goals Distribution (Poisson Model) - Playoff Teams"
        )
        fig.update_layout(template="plotly_white", height=500)
        fig.write_image(f"{IMG_DIR}/15_xg_poisson.png", width=900, height=500, scale=2)
        charts_generated.append("15_xg_poisson")

        # Chart 15.2: xPoints vs Actual Points
        # Calculate expected points based on goal scoring/conceding rates
        xpts_data = []
        for _, team in ro_standings.iterrows():
            played = max(team["intPlayed"], 1)
            gf_per_game = team["intGoalsFor"] / played
            ga_per_game = team["intGoalsAgainst"] / played

            # Simulate xPts using Poisson probabilities for each match
            xpts = 0
            for _ in range(played):
                p_win = sum(poisson.pmf(g, gf_per_game) * sum(poisson.pmf(a, ga_per_game) for a in range(g)) for g in range(1, 8))
                p_draw = sum(poisson.pmf(g, gf_per_game) * poisson.pmf(g, ga_per_game) for g in range(8))
                xpts += p_win * 3 + p_draw * 1

            xpts_data.append({
                "Team": team["strTeam"],
                "Actual Points": team["intPoints"],
                "Expected Points": round(xpts, 1),
                "Overperformance": round(team["intPoints"] - xpts, 1)
            })

        xpts_df = pd.DataFrame(xpts_data).sort_values("Overperformance", ascending=False)
        fig = px.bar(
            xpts_df, x="Team", y="Overperformance",
            color="Overperformance", color_continuous_scale="RdYlGn",
            title="xPoints Overperformance (Actual - Expected): Luck vs Skill Analysis",
            text="Overperformance"
        )
        fig.update_layout(template="plotly_white", height=500, xaxis_tickangle=-45)
        fig.update_traces(texttemplate="%{text:+.1f}", textposition="outside")
        fig.add_hline(y=0, line_dash="solid", line_color="black")
        fig.write_image(f"{IMG_DIR}/15_xpoints.png", width=900, height=500, scale=2)
        charts_generated.append("15_xpoints")

        # Chart 15.3: Consistency Index (Points StdDev in rolling form)
        # Approximate with Win%, Draw%, Loss% variance
        consistency = []
        for _, team in ro_standings.iterrows():
            played = max(team["intPlayed"], 1)
            w_pct = team["intWin"] / played
            d_pct = team["intDraw"] / played
            l_pct = team["intLoss"] / played
            # Shannon entropy as consistency measure (higher = more unpredictable)
            probs = [p for p in [w_pct, d_pct, l_pct] if p > 0]
            entropy = -sum(p * np.log2(p) for p in probs) if probs else 0
            consistency.append({
                "Team": team["strTeam"],
                "Consistency (Entropy)": round(entropy, 3),
                "Points": team["intPoints"]
            })

        cons_df = pd.DataFrame(consistency).sort_values("Consistency (Entropy)")
        fig = px.scatter(
            cons_df, x="Consistency (Entropy)", y="Points", text="Team",
            color="Points", color_continuous_scale="Viridis",
            title="Consistency vs Points - Low Entropy = More Predictable Results",
            size="Points", size_max=20
        )
        fig.update_traces(textposition="top center", textfont_size=8)
        fig.update_layout(template="plotly_white", height=500)
        fig.write_image(f"{IMG_DIR}/15_consistency.png", width=900, height=500, scale=2)
        charts_generated.append("15_consistency")

    # ================================================================
    # PAGE 16: LEAGUE MANAGEMENT (2 charts)
    # ================================================================
    print("  Generating Page 16: League Management charts...")

    if not ro_events.empty:
        completed = ro_events.dropna(subset=["intHomeScore", "intAwayScore"]).copy()
        if not completed.empty:
            completed["intHomeScore"] = completed["intHomeScore"].astype(int)
            completed["intAwayScore"] = completed["intAwayScore"].astype(int)
            completed["total_goals"] = completed["intHomeScore"] + completed["intAwayScore"]

            # Chart 16.1: Venue Analysis - Goals per Venue
            if "strVenue" in completed.columns:
                venue_stats = completed.groupby("strVenue").agg(
                    matches=("total_goals", "count"),
                    avg_goals=("total_goals", "mean"),
                    total_goals=("total_goals", "sum")
                ).reset_index()
                venue_stats = venue_stats[venue_stats["matches"] >= 3].sort_values("avg_goals", ascending=False).head(15)

                if not venue_stats.empty:
                    fig = px.bar(
                        venue_stats, x="strVenue", y="avg_goals", color="matches",
                        color_continuous_scale="Blues",
                        title="Venue Analysis - Average Goals per Match (min. 3 matches)",
                        text="avg_goals"
                    )
                    fig.update_layout(template="plotly_white", height=450, xaxis_tickangle=-45)
                    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                    fig.write_image(f"{IMG_DIR}/16_venues.png", width=1000, height=500, scale=2)
                    charts_generated.append("16_venues")

            # Chart 16.2: Round-by-Round Goals Analysis
            if "intRound" in completed.columns:
                completed["intRound"] = pd.to_numeric(completed["intRound"], errors="coerce")
                round_stats = completed.groupby("intRound").agg(
                    avg_goals=("total_goals", "mean"),
                    matches=("total_goals", "count")
                ).reset_index().dropna()
                round_stats = round_stats[round_stats["matches"] >= 2]

                if not round_stats.empty:
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(go.Scatter(
                        x=round_stats["intRound"], y=round_stats["avg_goals"],
                        mode="lines+markers", name="Avg Goals/Match",
                        line=dict(color="#e74c3c", width=2)
                    ), secondary_y=False)
                    fig.add_trace(go.Bar(
                        x=round_stats["intRound"], y=round_stats["matches"],
                        name="Matches Played", marker_color="#3498db", opacity=0.4
                    ), secondary_y=True)
                    fig.update_layout(
                        title="Round-by-Round Analysis - Goals Trend & Match Volume",
                        template="plotly_white", height=450
                    )
                    fig.update_yaxes(title_text="Avg Goals", secondary_y=False)
                    fig.update_yaxes(title_text="Matches", secondary_y=True)
                    fig.write_image(f"{IMG_DIR}/16_rounds.png", width=900, height=450, scale=2)
                    charts_generated.append("16_rounds")

    print(f"  Part 3 complete: {len(charts_generated)} charts generated")
    return charts_generated
