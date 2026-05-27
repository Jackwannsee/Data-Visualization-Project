"""
Headshot Analysis — CS2 Budapest Major Dashboard
=================================================
Interactive scatter plot comparing headshot percentage against kills/KPR.
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
if "headshot_scatter" in sys.modules:
    importlib.reload(sys.modules["headshot_scatter"])

from headshot_scatter import (
    create_headshot_scatter,
    get_available_stages,
    get_available_maps,
    get_available_sides,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Headshot Analysis — CS2 Dashboard",
    page_icon="🎯",
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
def cached_sides():
    return get_available_sides()

# ── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">🎯 Headshot Analysis</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("##### 📊 Pages")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_💰_Economy_Analysis.py", label="Economy Analysis", icon="💰")
    st.page_link("pages/2_🕷️_Player_Performance.py", label="Player Performance", icon="🕷️")
    st.page_link("pages/3_🎯_Headshot_Analysis.py", label="Headshot Analysis", icon="🎯")
    st.page_link("pages/4_🗺️_Position_Heatmap.py", label="Position Heatmap", icon="🗺️")
    st.markdown("---")

    # ── Metric Selection (X-Axis) ──
    # Allow switching between x_metric='KPR' and x_metric='Kills'. Default to KPR!
    selected_metric = st.selectbox(
        "X-Axis Metric",
        options=["KPR", "Kills"],
        index=0,
        help="Choose the metric to plot on the X-axis: Kills Per Round (KPR) or Total Kills.",
    )

    # ── Side Filter ──
    sides = cached_sides()
    selected_side = st.selectbox(
        "Side Filter",
        options=sides,
        index=0,
        help="Filter player stats by the side played (Both, Terrorist, or Counter-Terrorist)",
    )

    # ── Stage Filter ──
    stages = ["All"] + cached_stages()
    selected_stage = st.selectbox(
        "Tournament Stage",
        options=stages,
        index=0,
    )

    # ── Map Filter ──
    maps = ["All"] + cached_maps()
    selected_map = st.selectbox(
        "Map",
        options=maps,
        index=0,
    )



# ── Page Content ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>🎯 Headshot Analysis</h1>
        <p>
            Interactive scatter plot mapping player headshot percentage against kills or Kills Per Round (KPR).
            The size of points represents total rounds played. Toggle teams in the legend to filter dynamically,
            and view the tournament averages or trendline.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Scope Info Box ───────────────────────────────────────────────────────────
scope_parts = [f"Metric: **{selected_metric}**"]
if selected_side != "Both":
    scope_parts.append(f"Side: **{selected_side}**")
if selected_stage != "All":
    scope_parts.append(f"Stage: **{selected_stage}**")
if selected_map != "All":
    scope_parts.append(f"Map: **{selected_map}**")
scope_text = " · ".join(scope_parts)

st.markdown(
    f'<div class="info-box">🔍 {scope_text}</div>',
    unsafe_allow_html=True,
)

# ── Accuracy Scatter Chart ───────────────────────────────────────────────────
try:
    fig = create_headshot_scatter(
        side=selected_side,
        stage=selected_stage if selected_stage != "All" else None,
        map_name=selected_map if selected_map != "All" else None,
        x_metric=selected_metric,
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
        )
        st.plotly_chart(fig, use_container_width=True, key="headshot_scatter_chart")
    else:
        st.warning("No data returned for the selected parameters.")

except ValueError as e:
    st.error(f"⚠️ {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
