"""
CS2 Budapest Major Dashboard — Home Page
=========================================
Main entry point for the Streamlit dashboard.
Run with: streamlit run src/dashboard/app.py
"""

import os
import sys
import json
import streamlit as st

# ── Path Setup ───────────────────────────────────────────────────────────────
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(DASHBOARD_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)
VIZ_DIR = os.path.join(SRC_DIR, "visualization")

if VIZ_DIR not in sys.path:
    sys.path.insert(0, VIZ_DIR)

TOURNAMENT_DATA_PATH = os.path.join(SRC_DIR, "budapest_major.json")

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CS2 Budapest Major Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global typography */
    .stApp, .stMarkdown, p, span, li {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── Hero Header ── */
    .hero {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem 1rem;
    }
    .hero h1 {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FAB200 0%, #FF8C00 50%, #FAB200 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -0.02em;
    }
    .hero .subtitle {
        font-size: 1.15rem;
        color: #888;
        font-weight: 300;
        letter-spacing: 0.04em;
    }

    /* ── Description ── */
    .description {
        text-align: center;
        max-width: 780px;
        margin: 0 auto 2rem auto;
        color: #999;
        font-size: 1rem;
        line-height: 1.7;
    }

    /* ── Navigation Cards ── */
    .nav-card {
        background: linear-gradient(145deg, #1a1d23 0%, #22262e 100%);
        border: 1px solid #333;
        border-radius: 16px;
        padding: 2rem 1.5rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .nav-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(250, 178, 0, 0.12);
        border-color: #FAB200;
    }
    .nav-card .icon { font-size: 3rem; margin-bottom: 0.8rem; }
    .nav-card h3 {
        color: #FAB200;
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }
    .nav-card p {
        color: #888;
        font-size: 0.95rem;
        line-height: 1.55;
        margin: 0;
    }

    /* ── Section Divider ── */
    .section-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, #333 50%, transparent 100%);
        margin: 2.5rem 0;
    }

    /* ── Stage Header ── */
    .stage-header {
        color: #FAB200;
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #2a2d35;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Match Card ── */
    .match-card {
        background: linear-gradient(145deg, #1a1d23 0%, #22262e 100%);
        border: 1px solid #2a2d35;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .match-card:hover {
        border-color: #FAB20060;
        box-shadow: 0 4px 20px rgba(250, 178, 0, 0.08);
    }

    /* Match header: teams + score */
    .match-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.7rem;
    }
    .team-name {
        font-size: 1rem;
        font-weight: 600;
        min-width: 0;
        flex: 1;
    }
    .team-name.left { text-align: left; }
    .team-name.right { text-align: right; }
    .team-winner { color: #FAB200; }
    .team-loser  { color: #666; }
    .score-badge {
        background: linear-gradient(135deg, #FAB200, #FF8C00);
        color: #000;
        padding: 0.25rem 0.75rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.85rem;
        flex-shrink: 0;
        margin: 0 0.8rem;
    }

    /* Map tags under each match */
    .map-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
    }
    .map-tag {
        background: #2a2d35;
        padding: 0.2rem 0.55rem;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.02em;
    }
    .map-tag.won  { color: #4CAF50; border: 1px solid #4CAF5030; }
    .map-tag.lost { color: #777;    border: 1px solid #33333360; }

    /* ── Sidebar ── */
    .sidebar-brand {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FAB200;
        margin-bottom: 0.2rem;
    }

    /* Hide default footer */
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Data Loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_tournament_data():
    with open(TOURNAMENT_DATA_PATH, "r") as f:
        return json.load(f)


tournament = load_tournament_data()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🎮 CS2 Dashboard</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**StarLadder Budapest Major 2025**")
    st.markdown(
        "Interactive analysis of professional CS2 "
        "matches from the Budapest Major tournament."
    )
    st.markdown("---")
    st.markdown("##### 📊 Pages")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_💰_Economy_Analysis.py", label="Economy Analysis", icon="💰")
    st.page_link("pages/2_🕷️_Player_Performance.py", label="Player Performance", icon="🕷️")


# ── Hero Section ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <h1>🏆 StarLadder Budapest Major 2025</h1>
        <p class="subtitle">Interactive CS2 Match Analysis Dashboard</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="description">
        Explore interactive visualizations of professional Counter-Strike 2 matches
        from the StarLadder Budapest Major 2025. Analyze team economies round by round,
        compare player performance with radar charts, and dive deep into match statistics
        across all tournament stages.
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Navigation Cards ─────────────────────────────────────────────────────────
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(
        """
        <div class="nav-card">
            <div class="icon">💰</div>
            <h3>Economy Analysis</h3>
            <p>
                Explore round-by-round team economy comparisons with
                win/loss indicators and CT/T side markers. See how money
                management shapes the outcome of each map.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/1_💰_Economy_Analysis.py",
        label="Open Economy Analysis  →",
        icon="💰",
    )

with col2:
    st.markdown(
        """
        <div class="nav-card">
            <div class="icon">🕷️</div>
            <h3>Player Performance</h3>
            <p>
                Compare player statistics with interactive radar charts.
                Analyze kills, assists, utility usage, and more across
                different maps and tournament stages.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "pages/2_🕷️_Player_Performance.py",
        label="Open Player Performance  →",
        icon="🕷️",
    )

# ── Tournament Bracket ───────────────────────────────────────────────────────
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

st.markdown(
    """
    <div style="text-align:center; margin-bottom:2rem;">
        <h2 style="color:#FAB200; font-weight:700;">Tournament Bracket</h2>
        <p style="color:#666; font-size:0.95rem;">
            Results from all stages of the Budapest Major 2025
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_match_card(match: dict) -> str:
    """Return HTML for a single match card."""
    teams = match["teams_played"]
    winner = match["overall_winner"]
    score = match["overall_score"]
    maps_played = match["maps_played"]

    # Build map tags
    maps_html = ""
    for m in maps_played:
        css = "won" if m["winner"] == winner else "lost"
        # Show the winning team's perspective score tag
        maps_html += f'<span class="map-tag {css}">{m["map_name"]} {m["score"]}</span>'

    t1_cls = "team-winner" if teams[0] == winner else "team-loser"
    t2_cls = "team-winner" if teams[1] == winner else "team-loser"

    return f"""
    <div class="match-card">
        <div class="match-header">
            <span class="team-name left {t1_cls}">{teams[0]}</span>
            <span class="score-badge">{score}</span>
            <span class="team-name right {t2_cls}">{teams[1]}</span>
        </div>
        <div class="map-list">{maps_html}</div>
    </div>
    """


STAGE_ORDER = ["Quarterfinals", "Semifinals", "Final"]

for stage_name in STAGE_ORDER:
    matches = tournament["stages"].get(stage_name, [])
    if not matches:
        continue

    st.markdown(
        f'<div class="stage-header">🎯 {stage_name}</div>',
        unsafe_allow_html=True,
    )

    # Use two columns for stages with multiple matches
    if len(matches) >= 2:
        cols = st.columns(2, gap="medium")
        for i, match in enumerate(matches):
            with cols[i % 2]:
                st.markdown(render_match_card(match), unsafe_allow_html=True)
    else:
        # Single match (e.g. Final) — render centered
        _, center, _ = st.columns([1, 2, 1])
        with center:
            st.markdown(render_match_card(matches[0]), unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center; color:#555; font-size:0.8rem; padding:1rem 0;">
        CS2 Budapest Major Dashboard · Data Visualization Project · 2025
    </div>
    """,
    unsafe_allow_html=True,
)
