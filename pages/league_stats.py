"""
League Stats page — league-wide and cross-league analytics.
"""

import sys
from pathlib import Path


import pandas as pd
import streamlit as st

import charts
import db


def render():
    """Render the League Stats page."""

    st.header("League Stats")

    # ── Load data ────────────────────────────────────────────────
    cross_stats = db.get_cross_league_stats()
    biggest_fans = db.get_biggest_fans_all()
    submissions = db.get_submission_details()
    all_votes = db.get_all_votes()
    contrarian = db.get_contrarian_scores()
    users = db.get_all_users()

    # ── 2A: Leaderboard ─────────────────────────────────────────
    st.subheader("All-Time Leaderboard")
    if not cross_stats.empty:
        lb = cross_stats[[
            "user_name", "leagues_played", "total_rounds",
            "total_points_all_time", "avg_points_per_round",
            "avg_finish", "first_place_count"
        ]].copy()
        lb.columns = ["Player", "Leagues", "Rounds", "Total Pts",
                       "Avg Pts/Round", "Avg Finish", "1st Places"]
        # Round decimals
        lb["Avg Pts/Round"] = lb["Avg Pts/Round"].round(2)
        lb["Avg Finish"] = lb["Avg Finish"].round(2)
        lb = lb.reset_index(drop=True)
        lb.index = lb.index + 1
        st.dataframe(lb, use_container_width=True)

    st.divider()

    # ── 2B & 2C: Fan Pairs + Mutual Fans ────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Biggest Fan Pairs")
        st.caption("One-directional: who over-votes for whom the most")
        if not biggest_fans.empty:
            top_fans = biggest_fans.nlargest(15, "total_adjusted_surplus").copy()
            top_fans["surplus_per_round"] = (
                top_fans["total_adjusted_surplus"] / top_fans["rounds_together"]
            ).round(2)
            top_fans = (top_fans
                        [["voter_name", "submitter_name",
                          "total_adjusted_surplus", "rounds_together",
                          "surplus_per_round"]]
                        .reset_index(drop=True))
            top_fans["total_adjusted_surplus"] = top_fans["total_adjusted_surplus"].round(2)
            top_fans.columns = ["Voter", "Submitter", "Total Surplus",
                                "Rounds", "Surplus/Round"]
            top_fans.index = top_fans.index + 1
            st.dataframe(top_fans, use_container_width=True)

    with col_right:
        st.subheader("Biggest Mutual Fans")
        st.caption("Pairs who both over-vote for each other")
        try:
            mutual = db.get_mutual_fans()
            if not mutual.empty:
                top_mutual = mutual.head(15).copy()
                top_mutual["surplus_per_round"] = (
                    top_mutual["mutual_surplus"] / top_mutual["rounds_together"]
                ).round(2)
                top_mutual = (top_mutual
                              [["player_a", "player_b", "a_to_b_surplus",
                                "b_to_a_surplus", "mutual_surplus",
                                "rounds_together", "surplus_per_round"]]
                              .reset_index(drop=True))
                for col in ["a_to_b_surplus", "b_to_a_surplus", "mutual_surplus"]:
                    top_mutual[col] = top_mutual[col].round(2)
                top_mutual.columns = ["Player A", "Player B",
                                       "A→B", "B→A", "Combined",
                                       "Rounds", "Surplus/Round"]
                top_mutual.index = top_mutual.index + 1
                st.dataframe(top_mutual, use_container_width=True)
            else:
                st.info("No mutual fan data available.")
        except Exception:
            st.info("Mutual fans view not yet created. Re-run schema migration.")

    st.divider()

    # ── 2B2 & 2C2: Hater Pairs + Mutual Haters ──────────────────
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("Biggest Hater Pairs")
        st.caption("One-directional: who under-votes for whom the most")
        if not biggest_fans.empty:
            top_haters = biggest_fans.nsmallest(15, "total_adjusted_surplus").copy()
            top_haters["surplus_per_round"] = (
                top_haters["total_adjusted_surplus"] / top_haters["rounds_together"]
            ).round(2)
            top_haters = (top_haters
                          [["voter_name", "submitter_name",
                            "total_adjusted_surplus", "rounds_together",
                            "surplus_per_round"]]
                          .reset_index(drop=True))
            top_haters["total_adjusted_surplus"] = top_haters["total_adjusted_surplus"].round(2)
            top_haters.columns = ["Voter", "Submitter", "Total Surplus",
                                  "Rounds", "Surplus/Round"]
            top_haters.index = top_haters.index + 1
            st.dataframe(top_haters, use_container_width=True)

    with col_right2:
        st.subheader("Biggest Mutual Haters")
        st.caption("Pairs who both under-vote for each other")
        try:
            mutual = db.get_mutual_fans()
            if not mutual.empty:
                # Mutual haters: lowest mutual_surplus (most negative)
                bottom_mutual = mutual.nsmallest(15, "mutual_surplus").copy()
                bottom_mutual["surplus_per_round"] = (
                    bottom_mutual["mutual_surplus"] / bottom_mutual["rounds_together"]
                ).round(2)
                bottom_mutual = (bottom_mutual
                                 [["player_a", "player_b", "a_to_b_surplus",
                                   "b_to_a_surplus", "mutual_surplus",
                                   "rounds_together", "surplus_per_round"]]
                                 .reset_index(drop=True))
                for col in ["a_to_b_surplus", "b_to_a_surplus", "mutual_surplus"]:
                    bottom_mutual[col] = bottom_mutual[col].round(2)
                bottom_mutual.columns = ["Player A", "Player B",
                                          "A→B", "B→A", "Combined",
                                          "Rounds", "Surplus/Round"]
                bottom_mutual.index = bottom_mutual.index + 1
                st.dataframe(bottom_mutual, use_container_width=True)
            else:
                st.info("No mutual hater data available.")
        except Exception:
            st.info("Mutual fans/haters view not yet created. Re-run schema migration.")

    st.divider()

    # ── 2D: Top Artists ─────────────────────────────────────────
    st.subheader("Top Artists")
    try:
        artist_stats = db.get_artist_stats()
        user_artist_stats = db.get_user_artist_stats()
        if not artist_stats.empty and not user_artist_stats.empty:
            # Shared color map so both charts use identical user colors
            uc = charts.make_user_color_map(user_artist_stats, "user_name")

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                fig = charts.stacked_bar(
                    user_artist_stats, "artist_name", "times_submitted",
                    "user_name", title="Most Submitted Artists", n=20,
                    user_colors=uc,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_a2:
                fig = charts.stacked_bar(
                    user_artist_stats, "artist_name", "total_points",
                    "user_name", title="Highest Total Points", n=20,
                    user_colors=uc,
                )
                st.plotly_chart(fig, use_container_width=True)

            # Avg points (non-stacked — avg doesn't decompose by user)
            qualified = artist_stats[artist_stats["submission_count"] >= 2]
            if not qualified.empty:
                fig = charts.ranked_bar(
                    qualified, "artist_name", "avg_points",
                    title="Highest Avg Points (min 2 submissions)",
                    color=charts.POSITIVE_COLOR, n=20
                )
                st.plotly_chart(fig, use_container_width=True)

            # Full table
            with st.expander("Full Artist Table"):
                at = artist_stats[["artist_name", "submission_count",
                                   "unique_submitters", "total_points",
                                   "avg_points"]].copy()
                at["avg_points"] = at["avg_points"].round(2)
                at.columns = ["Artist", "Submissions", "Submitters",
                              "Total Pts", "Avg Pts"]
                st.dataframe(at, use_container_width=True)
        elif not artist_stats.empty:
            # Fallback if user_artist_stats unavailable
            fig = charts.ranked_bar(
                artist_stats, "artist_name", "submission_count",
                title="Most Submitted Artists", color=charts.ACCENT_COLOR, n=20
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Artist data not yet available. Run Spotify enrichment.")
    except Exception:
        st.info("Artist data not yet available. Run Spotify enrichment.")

    st.divider()

    # ── 2E: Head-to-Head ────────────────────────────────────────
    st.subheader("Head-to-Head Comparison")
    if not users.empty:
        users = users.sort_values("user_name", key=lambda s: s.str.lower())
        user_names = users["user_name"].tolist()
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            p1_name = st.selectbox("Player A", user_names, key="h2h_p1")
        with col_h2:
            p2_default = 1 if len(user_names) > 1 else 0
            p2_name = st.selectbox("Player B", user_names, index=p2_default, key="h2h_p2")

        if p1_name and p2_name and p1_name != p2_name:
            p1_id = users[users["user_name"] == p1_name].iloc[0]["user_id"]
            p2_id = users[users["user_name"] == p2_name].iloc[0]["user_id"]

            p1_stats = cross_stats[cross_stats["user_id"] == p1_id]
            p2_stats = cross_stats[cross_stats["user_id"] == p2_id]

            if not p1_stats.empty and not p2_stats.empty:
                r1, r2 = p1_stats.iloc[0], p2_stats.iloc[0]
                metrics = [
                    ("Total Points", "total_points_all_time", "d"),
                    ("Avg Pts/Round", "avg_points_per_round", ".2f"),
                    ("Avg Finish", "avg_finish", ".2f"),
                    ("1st Places", "first_place_count", "d"),
                    ("Rounds Played", "total_rounds", "d"),
                ]
                mc1, mc2 = st.columns(2)
                with mc1:
                    st.markdown(f"**{p1_name}**")
                    for label, key, fmt in metrics:
                        st.metric(label, f"{r1[key]:{fmt}}")
                with mc2:
                    st.markdown(f"**{p2_name}**")
                    for label, key, fmt in metrics:
                        st.metric(label, f"{r2[key]:{fmt}}")

                # Mutual voting
                p1_to_p2 = biggest_fans[
                    (biggest_fans["voting_user_id"] == p1_id) &
                    (biggest_fans["submission_user_id"] == p2_id)
                ]
                p2_to_p1 = biggest_fans[
                    (biggest_fans["voting_user_id"] == p2_id) &
                    (biggest_fans["submission_user_id"] == p1_id)
                ]

                vc1, vc2 = st.columns(2)
                with vc1:
                    if not p1_to_p2.empty:
                        surplus = p1_to_p2.iloc[0]["total_adjusted_surplus"]
                        st.metric(f"{p1_name} → {p2_name} surplus", f"{surplus:+.2f}")
                    else:
                        st.metric(f"{p1_name} → {p2_name} surplus", "N/A")
                with vc2:
                    if not p2_to_p1.empty:
                        surplus = p2_to_p1.iloc[0]["total_adjusted_surplus"]
                        st.metric(f"{p2_name} → {p1_name} surplus", f"{surplus:+.2f}")
                    else:
                        st.metric(f"{p2_name} → {p1_name} surplus", "N/A")

                # Round-by-round comparison
                p1_subs = submissions[submissions["user_id"] == p1_id]
                p2_subs = submissions[submissions["user_id"] == p2_id]
                shared_rounds = set(p1_subs["round_id"]) & set(p2_subs["round_id"])
                if shared_rounds:
                    p1_shared = p1_subs[p1_subs["round_id"].isin(shared_rounds)].set_index("round_id")
                    p2_shared = p2_subs[p2_subs["round_id"].isin(shared_rounds)].set_index("round_id")
                    p1_wins = sum(p1_shared.loc[r, "total_points"] > p2_shared.loc[r, "total_points"]
                                  for r in shared_rounds if r in p1_shared.index and r in p2_shared.index)
                    p2_wins = sum(p2_shared.loc[r, "total_points"] > p1_shared.loc[r, "total_points"]
                                  for r in shared_rounds if r in p1_shared.index and r in p2_shared.index)
                    ties = len(shared_rounds) - p1_wins - p2_wins
                    st.markdown(f"**Head-to-head record** ({len(shared_rounds)} shared rounds): "
                                f"{p1_name} {p1_wins}W - {ties}T - {p2_wins}W {p2_name}")
        elif p1_name == p2_name:
            st.info("Select two different players.")

    st.divider()

    # ── 2F: Round Highlights ────────────────────────────────────
    st.subheader("Round Highlights")
    if not submissions.empty:
        c1, c2, c3 = st.columns(3)
        # Highest-scoring submission ever
        best = submissions.nlargest(1, "total_points").iloc[0]
        c1.metric("Highest Score Ever",
                   f"{int(best['total_points'])} pts",
                   delta=f"{best['song_title']} — {best['user_name']}")

        # Most competitive round
        round_spreads = submissions.groupby("round_id").agg(
            spread=("total_points", lambda x: x.max() - x.min()),
            round_name=("round_name", "first"),
        )
        if not round_spreads.empty:
            tightest = round_spreads.nsmallest(1, "spread").iloc[0]
            c2.metric("Tightest Round",
                       f"{int(tightest['spread'])} pt spread",
                       delta=tightest["round_name"])

            widest = round_spreads.nlargest(1, "spread").iloc[0]
            c3.metric("Biggest Blowout",
                       f"{int(widest['spread'])} pt spread",
                       delta=widest["round_name"])

    st.divider()

    # ── 2G: Contrarian Rankings ─────────────────────────────────
    st.subheader("Contrarian Rankings")
    st.caption("How much each voter's points diverge from the group's final scores. "
               "High score = votes often go against the crowd.")
    if not contrarian.empty:
        fig = charts.ranked_bar(
            contrarian, "voter_name", "contrarian_score",
            title="", color=charts.ACCENT_COLOR, n=25
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 2H: Voting Behavior ────────────────────────────────────
    st.subheader("Voting Behavior")
    if not all_votes.empty:
        own_votes = all_votes[all_votes["voting_user_id"] != all_votes["submission_user_id"]]

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            fig = charts.histogram(own_votes["points"], "Distribution of All Votes")
            st.plotly_chart(fig, use_container_width=True)

        with col_v2:
            avg_given = (own_votes
                         .groupby("voter_name")["points"]
                         .mean()
                         .reset_index()
                         .rename(columns={"points": "avg_points_given"})
                         .sort_values("avg_points_given", ascending=False))
            avg_given["avg_points_given"] = avg_given["avg_points_given"].round(2)
            fig = charts.ranked_bar(
                avg_given, "voter_name", "avg_points_given",
                title="Avg Points Given Per Vote", color=charts.NEUTRAL_COLOR, n=25
            )
            st.plotly_chart(fig, use_container_width=True)
