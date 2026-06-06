"""
Side Comparison — CS2 Budapest Major Dashboard
=================================================
Interactive diverging bar chart comparing CT vs T side performance across Game, Map, and Player scopes.
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
VIZ_DIR = os.path.join(SRC_DIR, "visualization")

if VIZ_DIR not in sys.path:
    sys.path.insert(0, VIZ_DIR)

import importlib
if "diverging_bar" in sys.modules:
    importlib.reload(sys.modules["diverging_bar"])

from diverging_bar import (
    get_unique_games,
    get_available_maps,
    get_available_players,
    get_available_stages,
    get_game_charts,
    get_map_chart,
    get_player_chart,
    METRICS,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Side Comparison — CS2 Dashboard",
    page_icon="📊",
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
        max-width: 800px;
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

    /* Player Card / Info Card Styles */
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
    
    /* Map Info Card overrides */
    .map-card-header {
        color: #FAB200;
    }
    .map-match-row {
        padding: 0.5rem 0;
        border-bottom: 1px solid #2a2d35;
    }
    .map-match-row:last-child {
        border-bottom: none;
    }
    .map-match-stage {
        font-size: 0.8rem;
        color: #888;
        text-transform: uppercase;
    }
    .map-match-teams {
        font-weight: 600;
        font-size: 1rem;
        margin-top: 0.2rem;
    }
    .map-match-score {
        color: #FAB200;
        font-weight: 700;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# ── Cached Data Helpers ──────────────────────────────────────────────────────
@st.cache_data
def cached_games():
    return get_unique_games()

@st.cache_data
def cached_maps():
    return get_available_maps()

@st.cache_data
def cached_players():
    return get_available_players()

@st.cache_data
def cached_stages():
    return get_available_stages()

@st.cache_data
def get_map_match_info(map_name):
    """Retrieve all matches played on a specific map from the tournament JSON."""
    json_path = os.path.join(SRC_DIR, "budapest_major.json")
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    matches_on_map = []
    for stage, matches in data.get("stages", {}).items():
        for match in matches:
            teams = match["teams_played"]
            for m in match["maps_played"]:
                if m["map_name"] == map_name:
                    matches_on_map.append({
                        "stage": stage,
                        "team1": teams[0],
                        "team2": teams[1],
                        "winner": m["winner"],
                        "score": m["score"]
                    })
    return matches_on_map

def get_player_info(player_name, context, stage=None, game_label=None):
    """Retrieve player info formatted for the info card."""
    csv_path = os.path.join(SRC_DIR, "../analysis_results/budapest_major_stats.csv")
    df_all = load_csv(csv_path)
    
    player_rows = df_all[df_all['player_name'] == player_name]
    if len(player_rows) == 0:
        return None
    
    steam_id = str(player_rows['player_steamid'].iloc[0])
    team_name = str(player_rows['team'].iloc[0])
    
    overall_both = player_rows[player_rows['side'] == 'Both']
    overall_games = len(overall_both)
    overall_rounds = int(overall_both['Rounds Played'].sum())
    
    filtered_both = overall_both.copy()
    if context == "Specific Stage" and stage:
        filtered_both = filtered_both[filtered_both['stages'] == stage]
    elif context == "Specific Game" and game_label:
        games = cached_games()
        target_game = next((g for g in games if g['label'] == game_label), None)
        if target_game:
            filtered_both = filtered_both[(filtered_both['stages'] == target_game['stage']) & (filtered_both['map'] == target_game['map'])]
            
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
        '<div class="sidebar-brand">📊 Side Comparison</div>',
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

    analysis_scope = st.radio(
        "Analysis Scope",
        options=["Game Matchup", "Map Analytics", "Player Performance"],
        help="Select the level of aggregation for the diverging bar charts."
    )
    
    st.markdown("---")
    
    games_list = cached_games()
    game_labels = [g['label'] for g in games_list] if games_list else []
    
    selected_game_label = None
    selected_map = None
    selected_player = None
    player_context = None
    selected_stage = None
    
    if analysis_scope == "Game Matchup":
        pass
        
    elif analysis_scope == "Map Analytics":
        maps_list = cached_maps()
        default_map_idx = maps_list.index("Mirage") if "Mirage" in maps_list else 0
        selected_map = st.selectbox("Select Map", options=maps_list, index=default_map_idx)
        
    elif analysis_scope == "Player Performance":
        players_list = cached_players()
        default_player_idx = players_list.index("ZywOo") if "ZywOo" in players_list else 0
        selected_player = st.selectbox("Select Player", options=players_list, index=default_player_idx)
        
        csv_path = os.path.join(SRC_DIR, "../analysis_results/budapest_major_stats.csv")
        df_all = load_csv(csv_path)
        p_stats = df_all[df_all['player_name'] == selected_player]
        
        valid_stages = sorted(p_stats['stages'].unique().tolist())
        p_team = p_stats['team'].iloc[0] if not p_stats.empty else None
        valid_games = [g for g in games_list if g['team1'] == p_team or g['team2'] == p_team]
        valid_game_labels = [g['label'] for g in valid_games]
        
        player_context = st.radio("Context Filter", ["Entire Tournament", "Specific Stage", "Specific Game"])
        
        if player_context == "Specific Stage":
            selected_stage = st.selectbox("Select Stage", options=valid_stages, index=0) if valid_stages else None
            if not valid_stages:
                st.warning("No stages found for this player.")
        elif player_context == "Specific Game":
            selected_game_label = st.selectbox("Select Game", options=valid_game_labels, index=0) if valid_game_labels else None
            if not valid_game_labels:
                st.warning("No games found for this player.")


# ── Page Content ─────────────────────────────────────────────────────────────
if analysis_scope == "Game Matchup":
    desc_text = "Compare team performances head-to-head for a specific match. The diverging bar charts display Counter-Terrorist (CT) and Terrorist (T) side metrics simultaneously, normalized per-round against the tournament maximums. This provides a holistic view of which team dominated each side during the matchup."
elif analysis_scope == "Map Analytics":
    desc_text = "Evaluate structural map biases across the entire tournament. By aggregating all matches played on a specific map, this chart reveals whether a map heavily favored the Counter-Terrorist (CT) or Terrorist (T) side overall across all professional teams."
else:
    desc_text = "Drill down into individual player impact and side-bias. Track a specific player's Counter-Terrorist (CT) versus Terrorist (T) lethality across the entire tournament, isolated stages, or specific games to uncover their consistency and playstyle."

st.markdown(
    f"""
    <div class="page-header">
        <h1>📊 Side Comparison</h1>
        <p>
            {desc_text} Hover over the bars to see exact raw stats and round counts.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

def format_plot(fig):
    if fig:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc",
            title_font_color="#FAB200",
            legend=dict(font=dict(color="#ccc")),
        )
    return fig

try:
    if analysis_scope == "Game Matchup":
        if 'selected_game_label' not in st.session_state:
            st.session_state.selected_game_label = game_labels[0] if game_labels else None
                            
        selected_game = next((g for g in games_list if g['label'] == st.session_state.selected_game_label), None)
        
        if selected_game:
            scope_text = f"Scope: **Game Matchup** · Match: **{selected_game['team1']} vs {selected_game['team2']}** · Map: **{selected_game['map']}**"
            st.markdown(f'<div class="info-box">🔍 {scope_text}</div>', unsafe_allow_html=True)
            
            fig1, fig2 = get_game_charts(selected_game['stage'], selected_game['map'], selected_game['team1'], selected_game['team2'])
            
            if fig1:
                st.plotly_chart(format_plot(fig1), use_container_width=True, key="team1_chart")
            else:
                st.warning("No data available for Team 1 in this matchup.")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            if fig2:
                st.plotly_chart(format_plot(fig2), use_container_width=True, key="team2_chart")
            else:
                st.warning("No data available for Team 2 in this matchup.")
                
            try:
                map_matches = get_map_match_info(selected_game['map'])
                match_info = next((m for m in map_matches if m['stage'] == selected_game['stage'] and 
                                 ((m['team1'] == selected_game['team1'] and m['team2'] == selected_game['team2']) or
                                  (m['team1'] == selected_game['team2'] and m['team2'] == selected_game['team1']))), None)
                
                if match_info:
                    csv_path = os.path.join(SRC_DIR, "../analysis_results/budapest_major_stats.csv")
                    df_all = load_csv(csv_path)
                    df_match = df_all[(df_all['stages'] == selected_game['stage']) & (df_all['map'] == selected_game['map'])]
                    
                    def get_rounds(team_name, side):
                        side_df = df_match[(df_match['team'] == team_name) & (df_match['side'] == side)]
                        return int(side_df['Rounds Played'].iloc[0]) if not side_df.empty else 0
                        
                    t1_ct = get_rounds(selected_game['team1'], 'Counter Terrorist')
                    t1_t = get_rounds(selected_game['team1'], 'Terrorist')
                    t2_ct = get_rounds(selected_game['team2'], 'Counter Terrorist')
                    t2_t = get_rounds(selected_game['team2'], 'Terrorist')
                    
                    # Calculate rounds won
                    outcomes_path = os.path.join(SRC_DIR, "../analysis_results/budapest_major_team_outcomes.csv")
                    df_outcomes = load_csv(outcomes_path)
                    
                    def parse_rounds(r_str):
                        if pd.isna(r_str) or not str(r_str).strip(): return []
                        r_list = []
                        for part in str(r_str).split(','):
                            if '-' in part:
                                s, e = part.split('-')
                                r_list.extend(range(int(s), int(e) + 1))
                            else:
                                r_list.append(int(part))
                        return r_list
                        
                    def get_won_rounds(team_name, side_col):
                        out_df = df_outcomes[(df_outcomes['stage'] == selected_game['stage']) & 
                                             (df_outcomes['map'] == selected_game['map']) & 
                                             (df_outcomes['team'] == team_name)]
                        if out_df.empty: return 0
                        row = out_df.iloc[0]
                        r_list = parse_rounds(row[side_col])
                        won = 0
                        for r in r_list:
                            col = f"r_{r}_outcome"
                            if col in row and row[col] == True:
                                won += 1
                        return won

                    t1_ct_won = get_won_rounds(selected_game['team1'], 'CT_rounds')
                    t1_t_won = get_won_rounds(selected_game['team1'], 'T_rounds')
                    t2_ct_won = get_won_rounds(selected_game['team2'], 'CT_rounds')
                    t2_t_won = get_won_rounds(selected_game['team2'], 'T_rounds')
                    
                    winner = match_info['winner']
                    score = match_info['score']
                    
                    st.markdown(
                        f'''
                        <div class="player-card" style="border-left: 5px solid #FAB200; max-width: 800px; margin: 2rem auto;">
                            <div class="player-card-header" style="justify-content: center; border-bottom: none; color: #FAB200;">
                                🏆 Winner: {winner} ({score})
                            </div>
                            <div style="display: flex; justify-content: space-around; padding-top: 1rem; border-top: 1px solid #2a2d35;">
                                <div style="text-align: center;">
                                    <h4 style="color: #fff; margin-bottom: 0.5rem;">{selected_game['team1']}</h4>
                                    <div style="color: #888; font-size: 0.95rem;">CT Rounds: <span style="color: #fff; font-family: monospace;">{t1_ct} <span style="color: #aaa; font-size: 0.85rem;">(Won {t1_ct_won})</span></span></div>
                                    <div style="color: #888; font-size: 0.95rem;">T Rounds: <span style="color: #fff; font-family: monospace;">{t1_t} <span style="color: #aaa; font-size: 0.85rem;">(Won {t1_t_won})</span></span></div>
                                </div>
                                <div style="text-align: center;">
                                    <h4 style="color: #fff; margin-bottom: 0.5rem;">{selected_game['team2']}</h4>
                                    <div style="color: #888; font-size: 0.95rem;">CT Rounds: <span style="color: #fff; font-family: monospace;">{t2_ct} <span style="color: #aaa; font-size: 0.85rem;">(Won {t2_ct_won})</span></span></div>
                                    <div style="color: #888; font-size: 0.95rem;">T Rounds: <span style="color: #fff; font-family: monospace;">{t2_t} <span style="color: #aaa; font-size: 0.85rem;">(Won {t2_t_won})</span></span></div>
                                </div>
                            </div>
                        </div>
                        ''', 
                        unsafe_allow_html=True
                    )
            except Exception as e:
                pass
                
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.markdown("### 🏆 Select Matchup")
        
        stages = ["Quarterfinals", "Semifinals", "Final"]
        for stage in stages:
            stage_games = [g for g in games_list if g['stage'] == stage]
            if stage_games:
                st.markdown(f"<h4 style='color: #888; margin-top: 1rem;'>{stage}</h4>", unsafe_allow_html=True)
                
                # Iterate in chunks of 2
                for i in range(0, len(stage_games), 2):
                    chunk = stage_games[i:i+2]
                    
                    if len(chunk) == 2:
                        cols = st.columns(2)
                        for j, g in enumerate(chunk):
                            is_selected = (st.session_state.selected_game_label == g['label'])
                            btn_type = "primary" if is_selected else "secondary"
                            with cols[j]:
                                if st.button(f"{g['team1']} vs {g['team2']}\n({g['map']})", key=f"btn_{g['label']}", use_container_width=True, type=btn_type):
                                    st.session_state.selected_game_label = g['label']
                                    st.rerun()
                    else:
                        # Uneven last item: Center it using a [1, 2, 1] column layout
                        cols = st.columns([1, 2, 1])
                        g = chunk[0]
                        is_selected = (st.session_state.selected_game_label == g['label'])
                        btn_type = "primary" if is_selected else "secondary"
                        with cols[1]:
                            if st.button(f"{g['team1']} vs {g['team2']}\n({g['map']})", key=f"btn_{g['label']}", use_container_width=True, type=btn_type):
                                st.session_state.selected_game_label = g['label']
                                st.rerun()
                            
    elif analysis_scope == "Map Analytics":
        scope_text = f"Scope: **Map Analytics** · Map: **{selected_map}** · Aggregation: **Global Average (All Teams)**"
        st.markdown(f'<div class="info-box">🔍 {scope_text}</div>', unsafe_allow_html=True)
        
        fig = get_map_chart(selected_map)
        if fig:
            st.plotly_chart(format_plot(fig), use_container_width=True, key="map_chart")
        else:
            st.warning("No data available for this map.")
            
        map_matches = get_map_match_info(selected_map)
        if map_matches:
            matches_html = ""
            for m in map_matches:
                t1, t2 = m['team1'], m['team2']
                winner = m['winner']
                t1_style = "color: #FAB200;" if winner == t1 else "color: #aaa;"
                t2_style = "color: #FAB200;" if winner == t2 else "color: #aaa;"
                
                # Flattened HTML to prevent Streamlit Markdown bugs
                matches_html += f'<div class="map-match-row"><div class="map-match-stage" style="text-align: center; margin-bottom: 0.25rem;">{m["stage"]}</div><div class="map-match-teams" style="display: flex; justify-content: center; align-items: center; gap: 1rem;"><span style="{t1_style}; flex: 1; text-align: right;">{t1}</span><span class="map-match-score" style="white-space: nowrap;"> [ {m["score"]} ] </span><span style="{t2_style}; flex: 1; text-align: left;">{t2}</span></div></div>'
                
            st.markdown(f'<div class="player-card" style="border-left: 5px solid #FAB200; max-width: 800px; margin: 2rem auto 0 auto;"><div class="player-card-header map-card-header">🗺️ {selected_map} - Tournament History</div><div class="player-card-body"><div class="player-card-row" style="margin-bottom: 0.5rem; border-bottom: 1px solid #2a2d35; padding-bottom: 0.5rem;"><span class="player-card-label">Total Games Played</span><span class="player-card-value">{len(map_matches)}</span></div>{matches_html}</div></div>', unsafe_allow_html=True)
            
    elif analysis_scope == "Player Performance":
        scope_text = f"Scope: **Player Performance** · Player: **{selected_player}** · Context: **{player_context}**"
        st.markdown(f'<div class="info-box">🔍 {scope_text}</div>', unsafe_allow_html=True)
        
        if player_context == "Entire Tournament":
            fig = get_player_chart(selected_player, scope="Tournament")
        elif player_context == "Specific Stage" and selected_stage:
            fig = get_player_chart(selected_player, scope="Stage", stage=selected_stage)
        elif player_context == "Specific Game" and selected_game_label:
            fig = get_player_chart(selected_player, scope="Game", game_label=selected_game_label)
        else:
            fig = None
            
        if fig:
            st.plotly_chart(format_plot(fig), use_container_width=True, key="player_chart")
        else:
            st.warning("No data available for this player in the selected context.")
            
        info = get_player_info(selected_player, player_context, selected_stage, selected_game_label)
        if info:
            color = "#1f77b4"
            if player_context != "Entire Tournament":
                games_str = f"{info['filtered_games']} (Tournament: {info['overall_games']})"
                rounds_str = f"{info['filtered_rounds']} (Tournament: {info['overall_rounds']})"
            else:
                games_str = f"{info['overall_games']}"
                rounds_str = f"{info['overall_rounds']}"
                
            # Flattened HTML to prevent Streamlit Markdown bugs
            st.markdown(f'<div class="player-card" style="border-left: 5px solid {color}; max-width: 600px; margin: 2rem auto 0 auto;"><div class="player-card-header" style="color: {color};">👤 {info["player_name"]}</div><div class="player-card-body"><div class="player-card-row"><span class="player-card-label">SteamID</span><span class="player-card-value">{info["steam_id"]}</span></div><div class="player-card-row"><span class="player-card-label">Team</span><span class="player-card-value">{info["team_name"]}</span></div><div class="player-card-row"><span class="player-card-label">Games Played</span><span class="player-card-value">{games_str}</span></div><div class="player-card-row"><span class="player-card-label">Rounds Played</span><span class="player-card-value">{rounds_str}</span></div></div></div>', unsafe_allow_html=True)

except ValueError as e:
    st.error(f"⚠️ {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
