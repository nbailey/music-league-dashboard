"""
Individual Stats page — personal analytics for a selected player.
"""

import sys
from pathlib import Path


import plotly.graph_objects as go
import pandas as pd
import streamlit as st

import charts
import db


def render():
    """Render the Individual Stats page with player selector at top."""

    st.header("Individual Stats")

    # ── Player selector at top of page ───────────────────────────
    users = db.get_all_users()
    if users.empty:
        st.warning("No users found in the database.")
        return

    # Case-insensitive sort
    users = users.sort_values("user_name", key=lambda s: s.str.lower())
    user_names = users["user_name"].tolist()
    selected_user_name = st.selectbox("Select player", user_names)

    if not selected_user_name:
        st.info("Select a player above to view stats.")
        return

    user_id = users[users["user_name"] == selected_user_name].iloc[0]["user_id"]
    user_name = selected_user_name

    st.divider()

    # ── Load data ────────────────────────────────────────────────
    cross_stats = db.get_cross_league_stats()
    biggest_fans = db.get_biggest_fans_all()
    submissions = db.get_submission_details()
    all_votes = db.get_all_votes()
    league_standings = db.get_league_standings()

    # Join league_order for chronological sorting
    all_leagues = db.get_all_leagues()
    league_order_map = dict(zip(all_leagues["league_id"], all_leagues["league_order"]))
    if "league_id" in submissions.columns:
        submissions["league_order"] = submissions["league_id"].map(league_order_map)
    if "league_id" in league_standings.columns:
        league_standings["league_order"] = league_standings["league_id"].map(league_order_map)

    my_stats_row = cross_stats[cross_stats["user_id"] == user_id]
    my_subs = submissions[submissions["user_id"] == user_id]

    # ── 1A: Overview Cards ───────────────────────────────────────
    if not my_stats_row.empty:
        row = my_stats_row.iloc[0]
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Leagues", int(row["leagues_played"]))
        c2.metric("Rounds", int(row["total_rounds"]))
        c3.metric("Total Points", int(row["total_points_all_time"]))
        c4.metric("Avg Pts/Round", f"{row['avg_points_per_round']:.2f}")
        c5.metric("1st Places", int(row["first_place_count"]))
        c6.metric("Avg Finish", f"{row['avg_finish']:.2f}")
    else:
        st.warning("No submission data found for this player.")
        return

    st.divider()

    # ── 1B & 1C: Fans / Haters ──────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("My Biggest Fans & Haters")
        st.caption("Who consistently over/under-votes for you (adjusted for their round averages)")
        my_fans = biggest_fans[biggest_fans["submission_user_id"] == user_id].copy()
        my_fans = my_fans[my_fans["voting_user_id"] != user_id]
        if not my_fans.empty:
            my_fans = my_fans.sort_values("total_adjusted_surplus", ascending=False)
            fig = charts.fan_critic_bar(
                my_fans, "voter_name", "total_adjusted_surplus",
                title=""
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No voting data available.")

    with col_right:
        st.subheader("Who I'm a Fan/Hater Of")
        st.caption("Who you consistently over/under-vote for")
        my_votes_for = biggest_fans[biggest_fans["voting_user_id"] == user_id].copy()
        my_votes_for = my_votes_for[my_votes_for["submission_user_id"] != user_id]
        if not my_votes_for.empty:
            my_votes_for = my_votes_for.sort_values("total_adjusted_surplus", ascending=False)
            fig = charts.fan_critic_bar(
                my_votes_for, "submitter_name", "total_adjusted_surplus",
                title=""
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No voting data available.")

    st.divider()

    # ── 1D: Top Submissions ─────────────────────────────────────
    st.subheader("Top Submissions")
    if not my_subs.empty:
        top_subs = (my_subs
                    .sort_values("total_points", ascending=False)
                    .head(20)
                    [["song_title", "artist", "round_name", "league_name",
                      "total_points", "finishing_place"]]
                    .reset_index(drop=True))
        top_subs.index = top_subs.index + 1
        top_subs.columns = ["Song", "Artist", "Round", "League", "Points", "Place"]
        st.dataframe(top_subs, use_container_width=True)

    # ── 1D2: 1st Place Submissions ──────────────────────────────
    st.subheader("1st Place Finishes")
    first_place = my_subs[my_subs["finishing_place"] == 1]
    if not first_place.empty:
        sort_cols = (["league_order", "round_number"]
                     if "league_order" in first_place.columns
                     else ["league_name", "round_number"])
        fp_display = (first_place
                      .sort_values(sort_cols)
                      [["song_title", "artist", "round_name", "league_name",
                        "total_points"]]
                      .reset_index(drop=True))
        fp_display.index = fp_display.index + 1
        fp_display.columns = ["Song", "Artist", "Round", "League", "Points"]
        st.dataframe(fp_display, use_container_width=True)
    else:
        st.info("No 1st place finishes yet.")

    st.divider()

    # ── 1E: Artist Profile ──────────────────────────────────────
    st.subheader("Artist Profile")
    try:
        user_artists = db.get_user_artist_stats()
        my_artists = user_artists[user_artists["user_id"] == user_id]
        if not my_artists.empty and len(my_artists) > 1:
            col_a, col_b = st.columns(2)
            with col_a:
                top_artist_count = my_artists.nlargest(15, "times_submitted")
                fig = charts.ranked_bar(
                    top_artist_count, "artist_name", "times_submitted",
                    title="Most Submitted Artists", color=charts.ACCENT_COLOR
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_b:
                multi_sub = my_artists[my_artists["times_submitted"] >= 2]
                if not multi_sub.empty:
                    overall_avg = my_subs["total_points"].mean() if not my_subs.empty else None
                    fig = charts.scatter_artists(
                        multi_sub, "Submission Count vs Avg Points",
                        avg_line=overall_avg,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Need 2+ submissions per artist for scatter view.")
        else:
            st.info("Artist data not yet available. Run Spotify enrichment to populate.")
    except Exception:
        st.info("Artist data not yet available. Run Spotify enrichment to populate.")

    st.divider()

    # ── 1F: Performance by League ────────────────────────────────
    st.subheader("Performance by League")
    if not my_subs.empty and not league_standings.empty:
        # Compute final placement within each league
        standings_ranked = league_standings.copy()
        standings_ranked["league_place"] = (standings_ranked
                                            .groupby("league_id")["total_points"]
                                            .rank(method="min", ascending=False)
                                            .astype(int))
        my_places = standings_ranked[standings_ranked["user_id"] == user_id].copy()

        if not my_places.empty:
            my_places = my_places.sort_values(
                "league_order" if "league_order" in my_places.columns else "league_name"
            )

            # Two summary bar charts side by side
            col_bar1, col_bar2 = st.columns(2)

            with col_bar1:
                fig = go.Figure(go.Bar(
                    x=my_places["total_points"],
                    y=my_places["league_name"],
                    orientation="h",
                    marker_color=charts.NEUTRAL_COLOR,
                    text=my_places["total_points"],
                    textposition="outside",
                ))
                fig.update_layout(
                    title="Total Points by League",
                    height=max(300, len(my_places) * 32 + 100),
                    margin=dict(l=10, r=50, t=50, b=30),
                    template="plotly_white",
                    xaxis_title="Points",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_bar2:
                # Use same league_order sort as total points chart
                colors = [charts.POSITIVE_COLOR if p <= 3 else charts.NEUTRAL_COLOR
                          for p in my_places["league_place"]]
                fig = go.Figure(go.Bar(
                    x=my_places["league_place"],
                    y=my_places["league_name"],
                    orientation="h",
                    marker_color=colors,
                    text=[_ordinal(p) for p in my_places["league_place"]],
                    textposition="outside",
                ))
                fig.update_layout(
                    title="Final Placement by League",
                    height=max(300, len(my_places) * 32 + 100),
                    margin=dict(l=10, r=50, t=50, b=30),
                    template="plotly_white",
                    xaxis_title="Place",
                    xaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig, use_container_width=True)

        # Per-league round-by-round points charts in 2-column grid
        st.markdown("#### Points per Round")
        if "league_order" in my_subs.columns:
            user_leagues = (my_subs[["league_name", "league_order"]]
                            .drop_duplicates()
                            .sort_values("league_order")["league_name"]
                            .tolist())
        else:
            user_leagues = sorted(my_subs["league_name"].unique())
        cols = st.columns(2)
        for i, league_name in enumerate(user_leagues):
            league_subs = (my_subs[my_subs["league_name"] == league_name]
                           .sort_values("round_number"))
            if league_subs.empty:
                continue

            with cols[i % 2]:
                avg = league_subs["total_points"].mean()
                fig = charts.score_line(
                    league_subs.reset_index(drop=True),
                    "round_number", "total_points",
                    label_col="round_name",
                    title=f"{league_name}",
                    avg_line=avg,
                )
                fig.update_layout(height=280, xaxis_title="Round #")
                st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 1G: Voting Pattern ──────────────────────────────────────
    st.subheader("Voting Pattern")
    my_given_votes = all_votes[
        (all_votes["voting_user_id"] == user_id) &
        (all_votes["submission_user_id"] != user_id)
    ]

    if not my_given_votes.empty:
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            fig = charts.histogram(my_given_votes["points"], "Distribution of Points I Give")
            st.plotly_chart(fig, use_container_width=True)

        with col_v2:
            contrarian = db.get_contrarian_scores()
            my_contrarian = contrarian[contrarian["voting_user_id"] == user_id]
            all_scores = contrarian["contrarian_score"].dropna()
            if not my_contrarian.empty and not all_scores.empty:
                my_score = my_contrarian.iloc[0]["contrarian_score"]
                pct = (all_scores < my_score).sum() / len(all_scores) * 100
                st.metric("Contrarian Score", f"{my_score:.2f}")
                st.caption(
                    f"How much your votes diverge from group consensus. "
                    f"You're more contrarian than {pct:.0f}% of players."
                )
            else:
                st.info("Not enough data for contrarian score.")


def _ordinal(n: int) -> str:
    """Convert integer to ordinal string (1st, 2nd, 3rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
