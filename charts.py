"""
Reusable Plotly chart builders for the Music League dashboard.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# ── Color palette ────────────────────────────────────────────────

POSITIVE_COLOR = "#2ecc71"   # green — fans, high scores
NEGATIVE_COLOR = "#e74c3c"   # red — critics, low scores
NEUTRAL_COLOR = "#3498db"    # blue — default
ACCENT_COLOR = "#9b59b6"     # purple — highlights
MUTED_COLOR = "#95a5a6"      # gray — reference lines


def fan_critic_bar(df: pd.DataFrame, name_col: str, value_col: str,
                   title: str, orientation: str = "h") -> go.Figure:
    """Horizontal bar chart with green (positive) and red (negative) bars.

    Used for biggest fans/critics views.
    """
    df = df.copy().sort_values(value_col, ascending=True)
    colors = [POSITIVE_COLOR if v >= 0 else NEGATIVE_COLOR for v in df[value_col]]

    fig = go.Figure(go.Bar(
        x=df[value_col],
        y=df[name_col],
        orientation="h",
        marker_color=colors,
        text=df[value_col].round(2),
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Adjusted Surplus",
        yaxis_title="",
        height=max(300, len(df) * 32 + 100),
        margin=dict(l=10, r=30, t=50, b=30),
        template="plotly_white",
    )
    return fig


def score_line(df: pd.DataFrame, x_col: str, y_col: str,
               label_col: str | None = None, title: str = "",
               avg_line: float | None = None) -> go.Figure:
    """Line chart for round-by-round scoring."""
    fig = go.Figure()

    hover_text = df[label_col] if label_col else None
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y_col],
        mode="lines+markers",
        marker=dict(color=NEUTRAL_COLOR, size=8),
        line=dict(color=NEUTRAL_COLOR, width=2),
        text=hover_text,
        hovertemplate="%{text}<br>Points: %{y}<extra></extra>" if hover_text is not None else None,
    ))

    if avg_line is not None:
        fig.add_hline(y=avg_line, line_dash="dash", line_color=MUTED_COLOR,
                      annotation_text=f"Avg: {avg_line:.1f}")

    fig.update_layout(
        title=title,
        xaxis_title="Round",
        yaxis_title="Points",
        template="plotly_white",
        margin=dict(l=10, r=30, t=50, b=30),
    )
    return fig


def ranked_bar(df: pd.DataFrame, name_col: str, value_col: str,
               title: str, color: str = NEUTRAL_COLOR,
               n: int = 20) -> go.Figure:
    """Simple horizontal bar chart, top N, sorted descending."""
    df = df.nlargest(n, value_col).sort_values(value_col, ascending=True)

    fig = go.Figure(go.Bar(
        x=df[value_col],
        y=df[name_col],
        orientation="h",
        marker_color=color,
        text=df[value_col].round(2),
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        height=max(300, len(df) * 28 + 100),
        margin=dict(l=10, r=30, t=50, b=30),
        template="plotly_white",
    )
    return fig


def histogram(series: pd.Series, title: str, nbins: int = 20,
              color: str = NEUTRAL_COLOR) -> go.Figure:
    """Simple histogram."""
    fig = go.Figure(go.Histogram(
        x=series, nbinsx=nbins, marker_color=color,
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Points",
        yaxis_title="Count",
        template="plotly_white",
        margin=dict(l=10, r=30, t=50, b=30),
    )
    return fig


def placement_line(df: pd.DataFrame, x_col: str, y_col: str,
                   label_col: str | None = None, title: str = "") -> go.Figure:
    """Line chart for finishing place (inverted y-axis: 1st at top)."""
    fig = go.Figure()

    hover_text = df[label_col] if label_col else None
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y_col],
        mode="lines+markers",
        marker=dict(color=ACCENT_COLOR, size=8),
        line=dict(color=ACCENT_COLOR, width=2),
        text=hover_text,
        hovertemplate="%{text}<br>Place: %{y}<extra></extra>" if hover_text is not None else None,
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Round",
        yaxis_title="Place",
        yaxis=dict(autorange="reversed"),  # 1st place at top
        template="plotly_white",
        margin=dict(l=10, r=30, t=50, b=30),
    )
    return fig


def make_user_color_map(df: pd.DataFrame, user_col: str) -> dict[str, str]:
    """Build a stable user → color mapping from all users in *df*.

    Call once and pass the result to both stacked_bar() calls so the
    same person always gets the same color across charts.
    """
    users = sorted(df[user_col].unique(), key=str.lower)
    palette = px.colors.qualitative.Set2 + px.colors.qualitative.Set3
    return {u: palette[i % len(palette)] for i, u in enumerate(users)}


def stacked_bar(df: pd.DataFrame, artist_col: str, value_col: str,
                user_col: str, title: str, n: int = 20,
                user_colors: dict[str, str] | None = None) -> go.Figure:
    """Horizontal stacked bar chart — one bar per artist, segments per user.

    df should have one row per (artist, user) with a value column.
    Top N artists by total value are shown, sorted descending.

    Parameters
    ----------
    user_colors : dict, optional
        Pre-built user→color map (from ``make_user_color_map``).
        If *None*, colours are assigned from the users present in *df*.
    """
    # Get top N artists by total value
    artist_totals = (df.groupby(artist_col)[value_col].sum()
                     .nlargest(n).reset_index())
    top_artists = artist_totals[artist_col].tolist()

    # Filter and order
    plot_df = df[df[artist_col].isin(top_artists)].copy()

    # Sort artists by total (ascending for plotly horizontal layout)
    artist_order = artist_totals.sort_values(value_col, ascending=True)[artist_col].tolist()

    # Compute the max segment width (for hiding text in tiny segments)
    max_total = artist_totals[value_col].max() if not artist_totals.empty else 1

    # Assign consistent colors per user
    if user_colors is None:
        user_colors = make_user_color_map(plot_df, user_col)
    users = sorted(plot_df[user_col].unique(), key=str.lower)

    fig = go.Figure()
    for user in users:
        user_data = plot_df[plot_df[user_col] == user]
        vals = {row[artist_col]: row[value_col] for _, row in user_data.iterrows()}
        x_vals = [vals.get(a, 0) for a in artist_order]
        # Only show text when segment is ≥8% of the largest bar total
        threshold = max_total * 0.08
        text_vals = [str(int(v)) if v >= threshold else "" for v in x_vals]
        fig.add_trace(go.Bar(
            y=[a for a in artist_order],
            x=x_vals,
            name=user,
            orientation="h",
            marker_color=user_colors.get(user, NEUTRAL_COLOR),
            text=text_vals,
            textposition="inside",
            insidetextanchor="middle",
            textangle=0,
            hovertemplate="%{y}<br><b>" + user + "</b>: %{x}<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        title=title,
        height=max(350, len(artist_order) * 28 + 120),
        margin=dict(l=10, r=30, t=50, b=30),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15,
                    xanchor="center", x=0.5, font=dict(size=10)),
    )
    return fig


def scatter_artists(df: pd.DataFrame, title: str,
                    avg_line: float | None = None) -> go.Figure:
    """Scatter plot of artist submission count vs avg points."""
    fig = px.scatter(
        df, x="times_submitted", y="avg_points",
        text="artist_name", size="total_points",
        title=title,
        labels={"times_submitted": "Times Submitted", "avg_points": "Avg Points"},
        template="plotly_white",
    )
    fig.update_traces(textposition="top center", marker=dict(color=ACCENT_COLOR))
    fig.update_layout(margin=dict(l=10, r=30, t=50, b=30))

    if avg_line is not None:
        fig.add_hline(y=avg_line, line_dash="dash", line_color=MUTED_COLOR,
                      annotation_text=f"Overall Avg: {avg_line:.2f}")

    return fig
