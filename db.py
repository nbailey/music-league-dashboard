"""
Database access layer for the Music League dashboard.
Cached queries via Streamlit's @st.cache_data.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DEFAULT_DB = Path(__file__).parent / "data" / "music_league.db"


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Get a SQLite connection. Not cached — connections aren't picklable."""
    path = db_path or DEFAULT_DB
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def query_df(sql: str, params: tuple = (), db_path: str | Path | None = None) -> pd.DataFrame:
    """Run a query and return a DataFrame. Not cached — callers should cache."""
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


# ── Cached query functions ───────────────────────────────────────


@st.cache_data(ttl=300)
def get_all_users() -> pd.DataFrame:
    return query_df("SELECT user_id, user_name FROM users ORDER BY user_name")


@st.cache_data(ttl=300)
def get_all_leagues() -> pd.DataFrame:
    return query_df(
        "SELECT league_id, league_name, league_order FROM leagues "
        "ORDER BY COALESCE(league_order, 999), league_name"
    )


@st.cache_data(ttl=300)
def get_cross_league_stats() -> pd.DataFrame:
    return query_df("SELECT * FROM v_cross_league_stats")


@st.cache_data(ttl=300)
def get_league_standings() -> pd.DataFrame:
    return query_df("SELECT * FROM v_league_standings")


@st.cache_data(ttl=300)
def get_biggest_fans_all() -> pd.DataFrame:
    return query_df("SELECT * FROM v_biggest_fans_all")


@st.cache_data(ttl=300)
def get_biggest_fans_per_league() -> pd.DataFrame:
    return query_df("SELECT * FROM v_biggest_fans")


@st.cache_data(ttl=300)
def get_mutual_fans() -> pd.DataFrame:
    return query_df("SELECT * FROM v_mutual_fans")


@st.cache_data(ttl=300)
def get_contrarian_scores() -> pd.DataFrame:
    """Compute contrarian scores: how much a voter's points diverge from group consensus.

    For each voter in each round, we compute the Spearman rank correlation
    between their point allocation and the final total scores. A voter who
    gives high points to low-scoring songs (and vice versa) gets a negative
    correlation. We convert to a 0-100 contrarian score:
        contrarian_score = (1 - avg_correlation) * 50
    So: perfect agreement = 0, random = 50, perfect disagreement = 100.
    """
    import numpy as np

    votes = query_df("""
        WITH voter_rounds AS (
            SELECT DISTINCT round_id, league_id, voting_user_id
            FROM votes
        ),
        full_matrix AS (
            SELECT vr.round_id, vr.league_id, vr.voting_user_id,
                   s.user_id AS submission_user_id,
                   COALESCE(v.points, 0) AS points,
                   s.total_points AS song_total
            FROM voter_rounds vr
            JOIN submissions s ON s.round_id = vr.round_id
                AND s.league_id = vr.league_id
                AND s.user_id != vr.voting_user_id
            LEFT JOIN votes v ON v.round_id = vr.round_id
                AND v.league_id = vr.league_id
                AND v.voting_user_id = vr.voting_user_id
                AND v.submission_user_id = s.user_id
        )
        SELECT fm.round_id, fm.voting_user_id, fm.submission_user_id,
               fm.points, fm.song_total,
               voter.user_name AS voter_name
        FROM full_matrix fm
        JOIN users voter ON fm.voting_user_id = voter.user_id
    """)

    if votes.empty:
        return pd.DataFrame(columns=["voting_user_id", "voter_name", "contrarian_score"])

    def _spearman(group):
        """Spearman correlation between voter's points and song totals."""
        if len(group) < 3:
            return np.nan
        voter_rank = group["points"].rank(method="average")
        total_rank = group["song_total"].rank(method="average")
        n = len(group)
        d_sq = ((voter_rank - total_rank) ** 2).sum()
        rho = 1 - (6 * d_sq) / (n * (n**2 - 1))
        return rho

    round_corr = votes.groupby(["voting_user_id", "voter_name", "round_id"]).apply(
        _spearman, include_groups=False
    ).reset_index(name="rho")

    avg = (round_corr
           .groupby(["voting_user_id", "voter_name"])["rho"]
           .mean()
           .reset_index())
    avg["contrarian_score"] = ((1 - avg["rho"]) * 50).round(2)
    avg = avg.sort_values("contrarian_score", ascending=False).reset_index(drop=True)

    return avg[["voting_user_id", "voter_name", "contrarian_score"]]


@st.cache_data(ttl=300)
def get_submission_details() -> pd.DataFrame:
    return query_df("SELECT * FROM v_submission_details")


@st.cache_data(ttl=300)
def get_artist_stats() -> pd.DataFrame:
    return query_df("SELECT * FROM v_artist_stats")


@st.cache_data(ttl=300)
def get_user_artist_stats() -> pd.DataFrame:
    return query_df("SELECT * FROM v_user_artist_stats")


@st.cache_data(ttl=300)
def get_all_votes() -> pd.DataFrame:
    return query_df("""
        SELECT v.*, voter.user_name AS voter_name,
               submitter.user_name AS submitter_name
        FROM votes v
        JOIN users voter ON v.voting_user_id = voter.user_id
        JOIN users submitter ON v.submission_user_id = submitter.user_id
    """)


@st.cache_data(ttl=300)
def get_adjusted_votes() -> pd.DataFrame:
    return query_df("SELECT * FROM v_adjusted_votes")
