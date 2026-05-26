"""
Player Performance — CS2 Budapest Major Dashboard
==================================================
Interactive spider / radar chart with player, metric, and scope selectors.
"""

import os
import sys
import streamlit as st

# ── Path Setup ───────────────────────────────────────────────────────────────
PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.dirname(PAGES_DIR)
SRC_DIR = os.path.dirname(DASHBOARD_DIR)
VIZ_DIR = os.path.join(SRC_DIR, "visualization")

if VIZ_DIR not in sys.path:
    sys.path.insert(0, VIZ_DIR)

from spider_player_performance import (
    create_spider_chart,
    get_available_players,
    get_available_columns,
    get_available_stages,
    get_available_maps,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Player Performance — CS2 Dashboard",
    page_icon="🕷️",
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

    .player-chips {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }
    .player-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: linear-gradient(145deg, #1a1d23, #22262e);
        border: 1px solid #333;
        border-radius: 20px;
        padding: 0.4rem 1rem;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .player-chip .color-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }

    .info-box {
        background: linear-gradient(145deg, #1a1d23 0%, #22262e 100%);
        border: 1px solid #2a2d35;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        color: #aaa;
        font-size: 0.85rem;
    }

    .sidebar-brand { font-size: 1.1rem; font-weight: 700; color: #FAB200; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Cached Data Helpers ──────────────────────────────────────────────────────
PLAYER_COLORS = ["#1f77b4", "#ff7f0e"]


@st.cache_data
def cached_players():
    return get_available_players()


@st.cache_data
def cached_columns():
    return get_available_columns()


@st.cache_data
def cached_stages():
    return get_available_stages()


@st.cache_data
def cached_maps():
    return get_available_maps()


# ── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">🕷️ Player Performance</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("##### 📊 Pages")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_💰_Economy_Analysis.py", label="Economy Analysis", icon="💰")
    st.page_link("pages/2_🕷️_Player_Performance.py", label="Player Performance", icon="🕷️")
    st.page_link("pages/3_🎯_Headshot_Analysis.py", label="Headshot Analysis", icon="🎯")
    st.markdown("---")

    # ── Player Selection ──
    all_players = cached_players()
    default_player = ["ZywOo"] if "ZywOo" in all_players else [all_players[0]]

    selected_players = st.multiselect(
        "Players (max 2)",
        all_players,
        default=default_player,
        help="Select up to 2 players to compare",
    )

    if len(selected_players) > 2:
        st.warning("⚠️ Maximum 2 players — only the first two will be used.")
        selected_players = selected_players[:2]

    # ── Metric Selection ──
    all_metrics = cached_columns() + ["K/D Ratio"]
    default_metrics = [
        m
        for m in ["Kills", "Assists", "K/D Ratio", "Smokes Thrown", "Molotovs Thrown", "Grenades"]
        if m in all_metrics
    ]

    selected_metrics = st.multiselect(
        "Metrics",
        all_metrics,
        default=default_metrics,
        help="Choose performance metrics to display on the radar chart",
    )

    st.markdown("---")

    # ── Side Filter ──
    side_options = {
        "All Sides": None,
        "Counter Terrorist": "Counter Terrorist",
        "Terrorist": "Terrorist",
        "Both (Aggregate)": "Both",
    }
    selected_side_label = st.selectbox("Side", list(side_options.keys()))
    selected_side = side_options[selected_side_label]

    # ── Scope Filter ──
    scope_labels = {
        "all": "🌐  All Data",
        "stage": "🏟️  By Stage",
        "map": "🗺️  By Map",
        "stage_map": "🎯  By Stage + Map",
    }
    selected_scope = st.selectbox(
        "Data Scope",
        list(scope_labels.keys()),
        format_func=lambda k: scope_labels[k],
    )

    # ── Conditional Stage / Map selectors ──
    selected_stage = None
    selected_map = None

    if selected_scope in ("stage", "stage_map"):
        stages = cached_stages()
        selected_stage = st.selectbox("Stage", stages)

    if selected_scope in ("map", "stage_map"):
        maps = cached_maps()
        selected_map = st.selectbox("Map", maps)




# ── Page Content ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>🕷️ Player Performance</h1>
        <p>
            Interactive radar chart comparing player performance metrics.
            Values are normalized against the <em>tournament-wide maximum</em> so
            players can be fairly compared. Select up to
            <strong>2 players</strong>, pick the metrics that matter,
            and filter by side, stage, or map.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Validation ───────────────────────────────────────────────────────────────
if len(selected_players) == 0:
    st.info("👈 Select at least one player from the sidebar to get started.")
    st.stop()

if len(selected_metrics) < 3:
    st.warning("📐 Select at least **3 metrics** for a meaningful radar chart.")
    st.stop()

# ── Player Chips ─────────────────────────────────────────────────────────────
chips_html = '<div class="player-chips">'
for idx, player in enumerate(selected_players):
    color = PLAYER_COLORS[idx] if idx < len(PLAYER_COLORS) else "#888"
    chips_html += (
        f'<span class="player-chip">'
        f'<span class="color-dot" style="background:{color};"></span>'
        f"{player}"
        f"</span>"
    )
chips_html += "</div>"
st.markdown(chips_html, unsafe_allow_html=True)

# ── Scope Info Box ───────────────────────────────────────────────────────────
scope_parts = []
if selected_side:
    scope_parts.append(f"Side: **{selected_side}**")
if selected_stage:
    scope_parts.append(f"Stage: **{selected_stage}**")
if selected_map:
    scope_parts.append(f"Map: **{selected_map}**")
scope_text = " · ".join(scope_parts) if scope_parts else "Showing **all data** across the tournament"

st.markdown(
    f'<div class="info-box">🔍 {scope_text}</div>',
    unsafe_allow_html=True,
)

# ── Spider Chart ─────────────────────────────────────────────────────────────
try:
    fig = create_spider_chart(
        player_names=selected_players,
        metrics=selected_metrics,
        side=selected_side,
        stage=selected_stage,
        map_name=selected_map,
        scope=selected_scope,
        show=False,
    )

    if fig is not None:
        # Apply dark-themed layout overrides for the dashboard
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc",
            title_font_color="#FAB200",
            legend=dict(font=dict(color="#ccc")),
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    gridcolor="rgba(42,45,53,0.5)",
                    linecolor="#2a2d35",
                    tickfont=dict(color="#666"),
                ),
                angularaxis=dict(
                    gridcolor="rgba(42,45,53,0.5)",
                    linecolor="#2a2d35",
                    tickfont=dict(color="#aaa", size=12),
                ),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, key="spider_chart")
    else:
        st.warning("No data returned for the selected parameters.")

except ValueError as e:
    st.error(f"⚠️ {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
