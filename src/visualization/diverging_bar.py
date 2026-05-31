import os
import sys
import pandas as pd
import plotly.graph_objects as go
import importlib.util

# Get script directory and resolve paths relative to it
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_stats.csv")
OUTCOMES_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_team_outcomes.csv")

# Import config colors
try:
    config_path = os.path.join(SCRIPT_DIR, "config.py")
    spec = importlib.util.spec_from_file_location("viz_config", config_path)
    viz_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(viz_config)
    T_COLOR = viz_config.T_COLOR
    CT_COLOR = viz_config.CT_COLOR
except Exception:
    try:
        from config import T_COLOR, CT_COLOR
    except (ModuleNotFoundError, ImportError):
        sys.path.append(SCRIPT_DIR)
        from config import T_COLOR, CT_COLOR

# Metrics exactly as they appear in spider chart
METRICS = [
    "Kills", "Assists", "K/D Ratio", "Smokes Thrown", 
    "Molotovs Thrown", "Grenades", "Deaths", "Headshot %"
]

def get_unique_games():
    """Return a sorted list of unique games with labels."""
    df = pd.read_csv(OUTCOMES_PATH)
    games = []
    seen = set()
    for _, row in df.iterrows():
        stage = row['stage']
        map_name = row['map']
        t_a, t_b = sorted([row['team'], row['opponent']])
        game_key = f"{stage}|{map_name}|{t_a}|{t_b}"
        if game_key not in seen:
            seen.add(game_key)
            games.append({
                'label': f"{stage} - {map_name}: {t_a} vs {t_b}",
                'stage': stage, 'map': map_name, 'team1': t_a, 'team2': t_b
            })
    stage_order = {"Quarterfinals": 1, "Semifinals": 2, "Final": 3}
    games.sort(key=lambda x: (stage_order.get(x['stage'], 99), x['map']))
    return games

def get_available_maps():
    df = pd.read_csv(STATS_PATH)
    return sorted(df['map'].unique().tolist())

def get_available_players():
    df = pd.read_csv(STATS_PATH)
    return sorted(df['player_name'].unique().tolist())

def get_available_stages():
    df = pd.read_csv(STATS_PATH)
    return sorted(df['stages'].unique().tolist())

def get_global_max_norms():
    """Calculate the global maximum per-round values for normalization (like spider chart)."""
    df_all = pd.read_csv(STATS_PATH)
    norm_values = {}
    for metric in METRICS:
        if metric == "K/D Ratio":
            kd_ratios = df_all.apply(lambda r: r['Kills']/r['Deaths'] if r['Deaths'] > 0 else 0.0, axis=1)
            norm_values[metric] = kd_ratios.max()
        elif metric == "Headshot %":
            norm_values[metric] = df_all['Headshot %'].max() if 'Headshot %' in df_all.columns else 100.0
        else:
            # Everything else is normalized per round
            norm_values[metric] = (df_all[metric] / df_all['Rounds Played']).max()
    return norm_values

# Global cache for norms to speed up plot rendering
GLOBAL_NORMS = get_global_max_norms()

def calculate_aggregated_metrics(df):
    """
    Given a filtered DataFrame, calculate the CT and T aggregated per-round metrics 
    and normalize them. Returns two dicts (ct_data, t_data).
    """
    ct_df = df[df['side'] == 'Counter Terrorist']
    t_df = df[df['side'] == 'Terrorist']
    
    def process_side(side_df):
        if side_df.empty:
            return None
            
        total_rounds = side_df['Rounds Played'].sum()
        if total_rounds == 0:
            return None
            
        res = {'Rounds': total_rounds, 'raw': {}, 'norm': {}, 'hover': {}}
        
        total_kills = side_df['Kills'].sum()
        total_deaths = side_df['Deaths'].sum()
        total_headshots = side_df['Headshots'].sum() if 'Headshots' in side_df.columns else 0.0
        
        for metric in METRICS:
            if metric == "K/D Ratio":
                raw = total_kills / total_deaths if total_deaths > 0 else 0.0
                res['raw'][metric] = raw
                res['norm'][metric] = (raw / GLOBAL_NORMS[metric]) * 100.0 if GLOBAL_NORMS[metric] > 0 else 0
                res['hover'][metric] = (
                    f"K/D Ratio: {raw:.2f}<br>"
                    f"Total Kills: {total_kills:.0f}<br>"
                    f"Total Deaths: {total_deaths:.0f}<br>"
                    f"Rounds: {total_rounds:.0f}"
                )
            elif metric == "Headshot %":
                raw = (total_headshots / total_kills) * 100.0 if total_kills > 0 else 0.0
                res['raw'][metric] = raw
                res['norm'][metric] = (raw / GLOBAL_NORMS[metric]) * 100.0 if GLOBAL_NORMS[metric] > 0 else 0
                res['hover'][metric] = (
                    f"Headshot %: {raw:.2f}%<br>"
                    f"Total Headshots: {total_headshots:.0f}<br>"
                    f"Total Kills: {total_kills:.0f}<br>"
                    f"Rounds: {total_rounds:.0f}"
                )
            else:
                total_metric = side_df[metric].sum()
                per_round = total_metric / total_rounds
                res['raw'][metric] = per_round
                res['norm'][metric] = (per_round / GLOBAL_NORMS[metric]) * 100.0 if GLOBAL_NORMS[metric] > 0 else 0
                res['hover'][metric] = (
                    f"{metric}/round: {per_round:.2f}<br>"
                    f"Total {metric}: {total_metric:.0f}<br>"
                    f"Rounds: {total_rounds:.0f}"
                )
        return res

    return process_side(ct_df), process_side(t_df)

def create_diverging_plot(ct_data, t_data, title):
    """Create the diverging bar chart based on calculated side data."""
    if not ct_data and not t_data:
        return None
        
    fig = go.Figure()
    
    # We will plot metrics on the Y axis in reverse order so they read top-to-bottom
    y_metrics = list(reversed(METRICS))
    
    # Process T Side (Negative)
    if t_data:
        t_norms = [-t_data['norm'][m] for m in y_metrics]
        t_hovers = [t_data['hover'][m] for m in y_metrics]
        
        fig.add_trace(go.Bar(
            y=y_metrics,
            x=t_norms,
            name='Terrorist',
            orientation='h',
            marker_color=T_COLOR,
            customdata=t_hovers,
            hovertemplate="<b>Terrorist Side</b><br>%{customdata}<extra></extra>"
        ))
        
    # Process CT Side (Positive)
    if ct_data:
        ct_norms = [ct_data['norm'][m] for m in y_metrics]
        ct_hovers = [ct_data['hover'][m] for m in y_metrics]
        
        fig.add_trace(go.Bar(
            y=y_metrics,
            x=ct_norms,
            name='Counter Terrorist',
            orientation='h',
            marker_color=CT_COLOR,
            customdata=ct_hovers,
            hovertemplate="<b>Counter Terrorist Side</b><br>%{customdata}<extra></extra>"
        ))
        
    fig.update_layout(
        title=title,
        barmode='relative',
        yaxis_title="Statistics",
        xaxis_title="Normalized Performance (0-100%)",
        legend_title="Side",
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        font=dict(family="Inter, Roboto, Arial", size=14),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # Set X axis range to strictly -100 to 100 for normalization clarity
    fig.update_xaxes(
        range=[-100, 100],
        showgrid=True, 
        gridwidth=1, 
        gridcolor='rgba(211, 211, 211, 0.5)',
        tickvals=[-100, -75, -50, -25, 0, 25, 50, 75, 100],
        ticktext=["100%", "75%", "50%", "25%", "0%", "25%", "50%", "75%", "100%"]
    )
    
    return fig

def get_game_charts(stage, map_name, team1, team2):
    """Returns two charts for the specific game (Team 1 and Team 2)."""
    df = pd.read_csv(STATS_PATH)
    
    # Filter to specific match
    df_match = df[(df['stages'] == stage) & (df['map'] == map_name)]
    
    # Process Team 1
    t1_df = df_match[df_match['team'] == team1]
    ct1, t1 = calculate_aggregated_metrics(t1_df)
    fig1 = create_diverging_plot(ct1, t1, f"{team1}")
    
    # Process Team 2
    t2_df = df_match[df_match['team'] == team2]
    ct2, t2 = calculate_aggregated_metrics(t2_df)
    fig2 = create_diverging_plot(ct2, t2, f"{team2}")
    
    return fig1, fig2

def get_map_chart(map_name):
    """Returns one chart aggregating all games for a specific map."""
    df = pd.read_csv(STATS_PATH)
    df_map = df[df['map'] == map_name]
    
    ct_data, t_data = calculate_aggregated_metrics(df_map)
    fig = create_diverging_plot(ct_data, t_data, f"Global Analytics: {map_name}")
    return fig

def get_player_chart(player_name, scope="Tournament", stage=None, game_label=None):
    """Returns one chart for a player based on a specific scope context."""
    df = pd.read_csv(STATS_PATH)
    df_player = df[df['player_name'] == player_name]
    
    if scope == "Stage" and stage:
        df_player = df_player[df_player['stages'] == stage]
        title = f"{player_name} - {stage}"
    elif scope == "Game" and game_label:
        games = get_unique_games()
        target_game = next((g for g in games if g['label'] == game_label), None)
        if target_game:
            df_player = df_player[(df_player['stages'] == target_game['stage']) & (df_player['map'] == target_game['map'])]
        title = f"{player_name} - {game_label}"
    else:
        title = f"{player_name} - Entire Tournament"
        
    ct_data, t_data = calculate_aggregated_metrics(df_player)
    fig = create_diverging_plot(ct_data, t_data, title)
    return fig
