"""
Economy Analysis — CS2 Budapest Major Dashboard
================================================
Interactive economy line chart with cascading parameter selectors.
"""

import os
import sys
import json
import pandas as pd
import streamlit as st

try:
    from data_loader import load_csv
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../visualization"))
    from data_loader import load_csv

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

from economy_viz import combined_economy_line_plot

TOURNAMENT_DATA_PATH = os.path.join(SRC_DIR, "budapest_major.json")

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
    .stApp, .stMarkdown, p, li { font-family: 'Inter', sans-serif !important; }

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
    
    /* ── Stage Header ── */
    .stage-header {
        color: #FAB200;
        font-size: 1.1rem;
        font-weight: 700;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.2rem;
        border-bottom: 2px solid #2a2d35;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Data Loading Helpers ─────────────────────────────────────────────────────
MATCH_DETAILS_PATH = os.path.join(ANALYSIS_DIR, "budapest_major_match_details.csv")

@st.cache_data
def load_tournament_data():
    with open(TOURNAMENT_DATA_PATH, "r") as f:
        return json.load(f)

@st.cache_data
def load_match_details():
    return load_csv(MATCH_DETAILS_PATH)

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

tournament = load_tournament_data()

# ── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">💰 Economy Analysis</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("##### 📊 Pages")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_💰_Economy_Analysis.py", label="Economy Analysis", icon="💰")
    st.page_link("pages/2_🕷️_Player_Performance.py", label="Player Performance", icon="🕷️")
    st.page_link("pages/3_🎯_Headshot_Analysis.py", label="Headshot Analysis", icon="🎯")
    st.page_link("pages/4_🗺️_Position_Heatmap.py", label="Position Heatmap", icon="🗺️")
    st.page_link("pages/5_📊_Side_Comparison.py", label="Side Comparison", icon="📊")
    st.markdown("---")
    st.markdown("Select a game from the tournament bracket in the main view to analyze its economy.")

# ── Page Content ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>💰 Economy Analysis</h1>
        <p>
            Select a match from the bracket below to view its round-by-round economy analysis.
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

# ── Tournament Bracket Selection ──────────────────────────────────────────────
st.markdown("### Tournament Bracket")

STAGE_ORDER = ["Quarterfinals", "Semifinals", "Final"]


def reorder_score(score: str, winner: str, team1: str, team2: str) -> str:
    """Reorder score so the winner's score always appears first."""
    parts = score.split("-")
    if len(parts) != 2:
        return score
    if team1 == winner:
        return f"{parts[0]}-{parts[1]}"
    else:
        return f"{parts[1]}-{parts[0]}"


# Default match selection
if "selected_eco_match" not in st.session_state:
    st.session_state.selected_eco_match = tournament["stages"]["Final"][0]
    st.session_state.selected_eco_stage = "Final"

for stage_name in STAGE_ORDER:
    matches = tournament["stages"].get(stage_name, [])
    if not matches:
        continue

    st.markdown(
        f'<div class="stage-header">🎯 {stage_name}</div>',
        unsafe_allow_html=True,
    )

    if len(matches) >= 2:
        cols = st.columns(2, gap="medium")
        for i, match in enumerate(matches):
            with cols[i % 2]:
                t1, t2 = match["teams_played"]
                winner = match["overall_winner"]
                score = reorder_score(match["overall_score"], winner, t1, t2)
                btn_label = f"{t1} {score} {t2}"
                # Use primary style for selected
                is_selected = (match == st.session_state.selected_eco_match)
                if st.button(btn_label, key=f"eco_btn_{stage_name}_{i}", use_container_width=True, type="primary" if is_selected else "secondary"):
                    st.session_state.selected_eco_match = match
                    st.session_state.selected_eco_stage = stage_name
                    st.rerun()
    else:
        _, center, _ = st.columns([1, 2, 1])
        with center:
            match = matches[0]
            t1, t2 = match["teams_played"]
            winner = match["overall_winner"]
            score = reorder_score(match["overall_score"], winner, t1, t2)
            btn_label = f"{t1} {score} {t2}"
            is_selected = (match == st.session_state.selected_eco_match)
            if st.button(btn_label, key=f"eco_btn_{stage_name}_0", use_container_width=True, type="primary" if is_selected else "secondary"):
                st.session_state.selected_eco_match = match
                st.session_state.selected_eco_stage = stage_name
                st.rerun()

st.markdown("---")

# ── Analysis for Selected Match ──────────────────────────────────────────────
sel_match = st.session_state.selected_eco_match
sel_stage = st.session_state.selected_eco_stage
t1, t2 = sel_match["teams_played"]

st.markdown(f"<h3 style='text-align: center;'>Analysis: {t1} vs {t2}</h3>", unsafe_allow_html=True)

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

maps_played = sel_match.get("maps_played", [])
if maps_played:
    tabs = st.tabs([f"{m['map_name']} ({reorder_score(m['score'], m['winner'], t1, t2)})" for m in maps_played])
    
    for i, m in enumerate(maps_played):
        map_name = m["map_name"]
        with tabs[i]:
            # Show Match Info Banner for this specific map
            match_info = get_match_info(sel_stage, map_name, t1)
            if match_info:
                opponent = match_info.get("opponent", "Unknown")
                final_score = match_info.get("final_score", "?-?")
                map_won = str(match_info.get("map_won", "")).lower() == "true"
                team_cls = "winner" if map_won else "loser"
                opp_cls = "loser" if map_won else "winner"

                st.markdown(
                    f"""
                    <div class="match-info-bar">
                        <span class="team {team_cls}">{t1}</span>
                        <span class="score">{final_score}</span>
                        <span class="team {opp_cls}">{opponent}</span>
                        <span class="map-badge">📍 {map_name}</span>
                        <span class="map-badge">🏟️ {sel_stage}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            
            # Chart
            try:
                fig = combined_economy_line_plot(
                    sel_stage, map_name, t1, show=False
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
                        margin=dict(t=30, b=10, l=10, r=10)
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"eco_chart_{sel_stage}_{i}")
                else:
                    st.warning(f"No economy data available for {map_name}.")
            except Exception as e:
                st.error(f"Error generating visualization: {e}")
else:
    st.info("No maps played in this match.")
