"""
Economy Analysis — CS2 Budapest Major Dashboard
================================================
Interactive economy line chart with cascading parameter selectors.
"""

import os
import sys
import pandas as pd
import streamlit as st

# ── Path Setup ───────────────────────────────────────────────────────────────
PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.dirname(PAGES_DIR)
SRC_DIR = os.path.dirname(DASHBOARD_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)
VIZ_DIR = os.path.join(SRC_DIR, "visualization")
ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis_results")

if VIZ_DIR not in sys.path:
    sys.path.insert(0, VIZ_DIR)

import importlib
if "economy_viz" in sys.modules:
    importlib.reload(sys.modules["economy_viz"])

from economy_viz import (
    combined_economy_line_plot,
    get_available_stages,
    get_available_maps,
    get_available_teams,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Economy Analysis — CS2 Dashboard",
    page_icon="💰",
    layout="wide",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .stApp, .stMarkdown, p, span, li { font-family: 'Inter', sans-serif !important; }

    .page-header {
        padding: 1rem 0 0.5rem 0;
    }
    .page-header h1 {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FAB200 0%, #FF8C00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .page-header p {
        color: #888;
        font-size: 0.95rem;
        line-height: 1.6;
        max-width: 700px;
    }

    .match-info-bar {
        background: linear-gradient(145deg, #1a1d23 0%, #22262e 100%);
        border: 1px solid #2a2d35;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1.5rem;
        flex-wrap: wrap;
    }
    .match-info-bar .team {
        font-size: 1.1rem;
        font-weight: 600;
    }
    .match-info-bar .winner { color: #FAB200; }
    .match-info-bar .loser  { color: #888; }
    .match-info-bar .score  {
        background: linear-gradient(135deg, #FAB200, #FF8C00);
        color: #000;
        padding: 0.3rem 0.8rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .match-info-bar .map-badge {
        color: #aaa;
        font-size: 0.85rem;
        background: #2a2d35;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }

    .legend-bar {
        display: flex;
        gap: 1.5rem;
        justify-content: center;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.8rem;
        color: #888;
    }
    .legend-bar .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 0.3rem;
        vertical-align: middle;
    }

    .sidebar-brand { font-size: 1.1rem; font-weight: 700; color: #FAB200; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Data Loading Helpers ─────────────────────────────────────────────────────
MATCH_DETAILS_PATH = os.path.join(ANALYSIS_DIR, "budapest_major_match_details.csv")


@st.cache_data
def cached_stages():
    return get_available_stages()


@st.cache_data
def cached_maps(stage):
    return get_available_maps(stage=stage)


@st.cache_data
def cached_teams(stage, map_name):
    return get_available_teams(stage=stage, map_name=map_name)


@st.cache_data
def load_match_details():
    return pd.read_csv(MATCH_DETAILS_PATH)


def get_match_info(stage, map_name, team):
    """Look up match info from match_details.csv."""
    df = load_match_details()
    # match_details uses 'stages' column (plural)
    match = df[
        (df["stages"] == stage)
        & (df["map"] == map_name)
        & (df["team"] == team)
        & (df["side"] == "Both")
    ]
    if len(match) > 0:
        return match.iloc[0].to_dict()
    return None


# ── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">💰 Economy Analysis</div>', unsafe_allow_html=True)
    st.markdown("---")

    stages = cached_stages()
    selected_stage = st.selectbox(
        "Tournament Stage",
        stages,
        index=stages.index("Final") if "Final" in stages else 0,
        help="Select the tournament stage to analyze",
    )

    maps = cached_maps(selected_stage)
    selected_map = st.selectbox(
        "Map",
        maps,
        help="Select the map played in this stage",
    )

    teams = cached_teams(selected_stage, selected_map)
    selected_team = st.selectbox(
        "Team (Focus)",
        teams,
        help="The primary team whose economy is highlighted",
    )

    st.markdown("---")
    st.page_link("app.py", label="← Back to Home", icon="🏠")


# ── Page Content ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>💰 Economy Analysis</h1>
        <p>
            Interactive line chart comparing <strong>total team economies</strong>
            across all rounds of a CS2 map.
            The primary team's economy is shown in blue, and the opponent team's in orange.
            Each round marker shows the team's side
            (<span style="color:#0091D4;font-weight:600;">CT</span> or
             <span style="color:#FAB200;font-weight:600;">T</span>),
            which is grayed out if the round was lost.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Match Info Banner ────────────────────────────────────────────────────────
match_info = get_match_info(selected_stage, selected_map, selected_team)
if match_info:
    opponent = match_info.get("opponent", "Unknown")
    final_score = match_info.get("final_score", "?-?")
    map_won = str(match_info.get("map_won", "")).lower() == "true"
    team_cls = "winner" if map_won else "loser"
    opp_cls = "loser" if map_won else "winner"

    st.markdown(
        f"""
        <div class="match-info-bar">
            <span class="team {team_cls}">{selected_team}</span>
            <span class="score">{final_score}</span>
            <span class="team {opp_cls}">{opponent}</span>
            <span class="map-badge">📍 {selected_map}</span>
            <span class="map-badge">🏟️ {selected_stage}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Legend ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="legend-bar">
        <span><span class="dot" style="background:#0077bb;"></span> Primary Team Line</span>
        <span><span class="dot" style="background:#ee7733;"></span> Opponent Team Line</span>
        <span><span class="dot" style="background:#0091D4;"></span> CT Side (Won)</span>
        <span><span class="dot" style="background:#FAB200;"></span> T Side (Won)</span>
        <span><span class="dot" style="background:#AFAFAF;"></span> Lost Round (Grayed Out)</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Chart ────────────────────────────────────────────────────────────────────
try:
    fig = combined_economy_line_plot(
        selected_stage, selected_map, selected_team, show=False
    )
    if fig is not None:
        # Apply dark-themed layout overrides for the dashboard
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc",
            title_font_color="#FAB200",
            xaxis=dict(gridcolor="#2a2d35", zerolinecolor="#2a2d35"),
            yaxis=dict(gridcolor="#2a2d35", zerolinecolor="#2a2d35"),
        )
        st.plotly_chart(fig, use_container_width=True, key="economy_chart")
    else:
        st.warning("No data available for the selected combination.")
except Exception as e:
    st.error(f"Error generating visualization: {e}")
