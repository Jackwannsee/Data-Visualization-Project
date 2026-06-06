"""
Player Performance — CS2 Budapest Major Dashboard
==================================================
Interactive spider / radar chart with player, metric, and scope selectors.
"""

import os
import sys
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
VIZ_DIR = os.path.join(SRC_DIR, "visualization")

if VIZ_DIR not in sys.path:
    sys.path.insert(0, VIZ_DIR)

import importlib
if "spider_player_performance" in sys.modules:
    importlib.reload(sys.modules["spider_player_performance"])

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

    .player-card {
        background: linear-gradient(145deg, #161920 0%, #20242f 100%);
        border: 1px solid #2a2d35;
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
        transition: all 0.3s ease;
    }
    .player-card:hover {
        transform: translateY(-2px);
        border-color: #FAB200 !important;
    }
    .player-card-header {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 1rem;
        border-bottom: 1px solid #2a2d35;
        padding-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .player-card-body {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    .player-card-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.95rem;
    }
    .player-card-label {
        color: #888;
        font-weight: 500;
    }
    .player-card-value {
        color: #ffffff;
        font-weight: 600;
        font-family: monospace;
    }
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


def get_player_info(player_name, selected_stage=None, selected_map=None, selected_scope="all"):
    """
    Retrieve player name, steam ID, games played, and rounds played.
    We return both overall tournament stats and filtered stats.
    """
    csv_path = os.path.join(SRC_DIR, "../analysis_results/budapest_major_stats.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(DASHBOARD_DIR, "../analysis_results/budapest_major_stats.csv")
        
    df_all = load_csv(csv_path)
    
    # Get SteamID (constant across all rows for this player)
    player_rows = df_all[df_all['player_name'] == player_name]
    if len(player_rows) == 0:
        return None
    
    steam_id = str(player_rows['player_steamid'].iloc[0])
    team_name = str(player_rows['team'].iloc[0])
    
    # Calculate overall tournament stats (using side == 'Both' to get actual unique games/rounds)
    overall_both = player_rows[player_rows['side'] == 'Both']
    overall_games = len(overall_both)
    overall_rounds = int(overall_both['Rounds Played'].sum())
    
    # Calculate filtered stats based on active scope
    filtered_both = overall_both.copy()
    if selected_scope in ("stage", "stage_map") and selected_stage is not None:
        filtered_both = filtered_both[filtered_both['stages'] == selected_stage]
    if selected_scope in ("map", "stage_map") and selected_map is not None:
        filtered_both = filtered_both[filtered_both['map'] == selected_map]
        
    filtered_games = len(filtered_both)
    filtered_rounds = int(filtered_both['Rounds Played'].sum())
    
    return {
        "player_name": player_name,
        "steam_id": steam_id,
        "team_name": team_name,
        "overall_games": overall_games,
        "overall_rounds": overall_rounds,
        "filtered_games": filtered_games,
        "filtered_rounds": filtered_rounds,
    }


# ── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">🕷️ Player Performance</div>',
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

    # ── Player Selection ──
    all_players = cached_players()
    default_players = [p for p in ["ZywOo", "broky"] if p in all_players]
    if not default_players and all_players:
        default_players = [all_players[0]]

    selected_players = st.multiselect(
        "Players (max 2)",
        all_players,
        default=default_players,
        help="Select up to 2 players to compare",
    )

    if len(selected_players) > 2:
        st.warning("⚠️ Maximum 2 players — only the first two will be used.")
        selected_players = selected_players[:2]

    # ── Metric Selection ──
    all_metrics = cached_columns() + ["K/D Ratio"]
    default_metrics = [
        m
        for m in ["Assists", "Smokes Thrown", "Molotovs Thrown", "Grenades", "Kills", "Deaths"]
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
    side_keys = list(side_options.keys())
    default_side_idx = side_keys.index("Both (Aggregate)")
    selected_side_label = st.selectbox("Side", side_keys, index=default_side_idx)
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

    # ── Conditional Stage / Map selectors with commonalities auto-filtering ──
    selected_stage = None
    selected_map = None

    if selected_scope != "all" and selected_players:
        csv_path = os.path.join(SRC_DIR, "../analysis_results/budapest_major_stats.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(DASHBOARD_DIR, "../analysis_results/budapest_major_stats.csv")
        
        df_all = load_csv(csv_path)
        df_both = df_all[df_all['side'] == 'Both']
        
        # Get stages and maps played by each selected player
        player_stages = []
        player_maps = []
        for player in selected_players:
            p_stats = df_both[df_both['player_name'] == player]
            player_stages.append(set(p_stats['stages'].unique()))
            player_maps.append(set(p_stats['map'].unique()))
            
        # Compute intersection/commonalities
        if len(selected_players) == 1:
            stages_options = sorted(list(player_stages[0]))
            maps_options = sorted(list(player_maps[0]))
        else: # 2 players
            common_stages = sorted(list(player_stages[0].intersection(player_stages[1])))
            common_maps = sorted(list(player_maps[0].intersection(player_maps[1])))
            
            if common_stages:
                stages_options = common_stages
            else:
                stages_options = sorted(list(player_stages[0].union(player_stages[1])))
                st.sidebar.caption("ℹ️ No common stages. Showing all played stages.")
                
            if common_maps:
                maps_options = common_maps
            else:
                maps_options = sorted(list(player_maps[0].union(player_maps[1])))
                st.sidebar.caption("ℹ️ No common maps. Showing all played maps.")
    else:
        stages_options = cached_stages()
        maps_options = cached_maps()

    if selected_scope in ("stage", "stage_map"):
        if stages_options:
            selected_stage = st.selectbox("Stage", stages_options)
        else:
            st.sidebar.warning("⚠️ No stages available.")

    if selected_scope in ("map", "stage_map"):
        if maps_options:
            selected_map = st.selectbox("Map", maps_options)
        else:
            st.sidebar.warning("⚠️ No maps available.")




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

# ── Player Details Section ───────────────────────────────────────────────────
st.markdown("---")

# Render columns depending on selected players count
if len(selected_players) == 1:
    player = selected_players[0]
    info = get_player_info(player, selected_stage, selected_map, selected_scope)
    if info:
        color = PLAYER_COLORS[0]
        if selected_scope != "all":
            games_str = f"{info['filtered_games']} (Tournament: {info['overall_games']})"
            rounds_str = f"{info['filtered_rounds']} (Tournament: {info['overall_rounds']})"
        else:
            games_str = f"{info['overall_games']}"
            rounds_str = f"{info['overall_rounds']}"
            
        st.markdown(
            f"""
            <div class="player-card" style="border-left: 5px solid {color}; max-width: 600px; margin: 0 auto;">
                <div class="player-card-header" style="color: {color};">
                    👤 {info['player_name']}
                </div>
                <div class="player-card-body">
                    <div class="player-card-row">
                        <span class="player-card-label">SteamID</span>
                        <span class="player-card-value">{info['steam_id']}</span>
                    </div>
                    <div class="player-card-row">
                        <span class="player-card-label">Team</span>
                        <span class="player-card-value">{info['team_name']}</span>
                    </div>
                    <div class="player-card-row">
                        <span class="player-card-label">Games Played</span>
                        <span class="player-card-value">{games_str}</span>
                    </div>
                    <div class="player-card-row">
                        <span class="player-card-label">Rounds Played</span>
                        <span class="player-card-value">{rounds_str}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

elif len(selected_players) == 2:
    cols = st.columns(2)
    for idx, player in enumerate(selected_players):
        info = get_player_info(player, selected_stage, selected_map, selected_scope)
        if info:
            color = PLAYER_COLORS[idx]
            if selected_scope != "all":
                games_str = f"{info['filtered_games']} (Tournament: {info['overall_games']})"
                rounds_str = f"{info['filtered_rounds']} (Tournament: {info['overall_rounds']})"
            else:
                games_str = f"{info['overall_games']}"
                rounds_str = f"{info['overall_rounds']}"
                
            with cols[idx]:
                st.markdown(
                    f"""
                    <div class="player-card" style="border-left: 5px solid {color};">
                        <div class="player-card-header" style="color: {color};">
                            👤 {info['player_name']}
                        </div>
                        <div class="player-card-body">
                            <div class="player-card-row">
                                <span class="player-card-label">SteamID</span>
                                <span class="player-card-value">{info['steam_id']}</span>
                            </div>
                            <div class="player-card-row">
                                <span class="player-card-label">Team</span>
                                <span class="player-card-value">{info['team_name']}</span>
                            </div>
                            <div class="player-card-row">
                                <span class="player-card-label">Games Played</span>
                                <span class="player-card-value">{games_str}</span>
                            </div>
                            <div class="player-card-row">
                                <span class="player-card-label">Rounds Played</span>
                                <span class="player-card-value">{rounds_str}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
