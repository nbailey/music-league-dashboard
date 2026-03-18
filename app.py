"""
GGG Music League Stats Dashboard
Entry point — sidebar navigation, page routing.

Deployed on Streamlit Community Cloud.
"""

import streamlit as st

from pages import league_stats, individual_stats

# ── Page config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="GGG Music League Stats",
    page_icon="\U0001f3b5",
    layout="wide",
)

# ── Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("GGG Music League Stats")
    st.divider()

    page = st.radio("View", ["Individual Stats", "League Stats"],
                     label_visibility="collapsed")

    st.divider()
    st.caption("Built with Streamlit + Plotly")

# ── Page routing ────────────────────────────────────────────────
if page == "Individual Stats":
    individual_stats.render()
else:
    league_stats.render()
