"""
Position Heatmap — CS2 Budapest Major Dashboard
=================================================
Interactive heatmap of player positions overlaid on map radar images.
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

import importlib
if "position_heatmap" in sys.modules:
    importlib.reload(sys.modules["position_heatmap"])

from position_heatmap import (
    create_position_heatmap,
    get_available_maps,
    get_available_stages,
    get_available_matches,
    has_levels,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Position Heatmap — CS2 Dashboard",
    page_icon="🗺️",
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
@st.cache_data
def cached_stages():
    return get_available_stages()

@st.cache_data
def cached_maps():
    return get_available_maps()

@st.cache_data
def cached_matches(map_name):
    return get_available_matches(map_name)

# ── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">🗺️ Position Heatmap</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("##### 📊 Pages")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_🕷️_Player_Performance.py", label="Player Performance", icon="🕷️")
    st.page_link("pages/2_🗺️_Position_Heatmap.py", label="Position Heatmap", icon="🗺️")
    st.page_link("pages/3_🎯_Headshot_Analysis.py", label="Headshot Analysis", icon="🎯")
    st.page_link("pages/4_📊_Side_Comparison.py", label="Side Comparison", icon="📊")
    st.page_link("pages/5_💰_Economy_Analysis.py", label="Economy Analysis", icon="💰")
    st.markdown("---")

    # ── Map Selector ──
    maps = cached_maps()
    selected_map = st.selectbox(
        "Map",
        options=maps,
        index=0,
        help="Select the map to visualize player positions on.",
    )

    # ── Side Selector ──
    selected_side = st.selectbox(
        "Side",
        options=["Both", "CT", "T"],
        index=0,
        help="Filter by team side: Both (all players), CT (Counter-Terrorist), or T (Terrorist).",
    )

    # ── Level Selector (only for Nuke and Train) ──
    if has_levels(selected_map):
        selected_level = st.selectbox(
            "Level",
            options=["upper", "lower"],
            index=0,
            help="Select the map level. Nuke and Train have upper and lower levels.",
        )
    else:
        selected_level = "upper"

    # ── Granularity Slider ──
    selected_granularity = st.select_slider(
        "Detail Level",
        options=[25, 50, 100, 200],
        value=50,
        help="Grid bin size in game units. Lower = more detail but slower rendering.",
    )

    # ── Stage Filter ──
    stages = ["All"] + cached_stages()
    selected_stage = st.selectbox(
        "Tournament Stage",
        options=stages,
        index=0,
    )

    # ── Match Filter ──
    matches = ["All"] + cached_matches(selected_map)
    selected_match = st.selectbox(
        "Match",
        options=matches,
        index=0,
    )

    # ── Color Palette Selector ──
    selected_palette = st.selectbox(
        "Color Palette",
        options=["Blues", "Oranges/Golds", "Hot/Plasma"],
        index=2,
        help="Heatmap color palette: Blues (CT), Oranges/Golds (T), or Hot/Plasma (Both sides).",
    )

# ── Page Content ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>🗺️ Position Heatmap</h1>
        <p>
            Visualize player positioning patterns overlaid on map radar images.
            Compare CT vs T positioning, explore multi-level maps, and adjust detail granularity.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Scope Info Box ───────────────────────────────────────────────────────────
scope_parts = [f"Map: **{selected_map}**", f"Side: **{selected_side}**", f"Level: **{selected_level}**", f"Detail: **{selected_granularity}** units"]
if selected_stage != "All":
    scope_parts.append(f"Stage: **{selected_stage}**")
if selected_match != "All":
    scope_parts.append(f"Match: **{selected_match}**")
scope_text = " · ".join(scope_parts)

st.markdown(
    f'<div class="info-box">🔍 {scope_text}</div>',
    unsafe_allow_html=True,
)

# ── Heatmap Chart ────────────────────────────────────────────────────────────
try:
    fig = create_position_heatmap(
        map_name=selected_map,
        side=selected_side,
        level=selected_level,
        granularity=selected_granularity,
        stage=selected_stage if selected_stage != "All" else None,
        match=selected_match if selected_match != "All" else None,
        show=False,
        colorscale_name=selected_palette,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#ccc",
        title_font_color="#FAB200",
    )
    st.plotly_chart(fig, use_container_width=True, key="position_heatmap_chart")

except ValueError as e:
    st.error(f"⚠️ {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
