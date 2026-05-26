import os
import sys
import pandas as pd
import plotly.graph_objects as go

# Get script directory and resolve paths relative to it
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_stats.csv")

# Import config colors - handle absolute path import to prevent collisions with other 'config' modules
try:
    import importlib.util
    config_path = os.path.join(SCRIPT_DIR, "config.py")
    spec = importlib.util.spec_from_file_location("viz_config", config_path)
    viz_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(viz_config)
    T_COLOR = viz_config.T_COLOR
    CT_COLOR = viz_config.CT_COLOR
    BOTH_COLOR = viz_config.BOTH_COLOR
    WIN_COLOR = viz_config.WIN_COLOR
    LOSS_COLOR = viz_config.LOSS_COLOR
    LINE_ALPHA = viz_config.LINE_ALPHA
except Exception:
    # Fallback to standard imports if path-based import fails
    try:
        from config import T_COLOR, CT_COLOR, BOTH_COLOR, WIN_COLOR, LOSS_COLOR, LINE_ALPHA
    except (ModuleNotFoundError, ImportError):
        # Add visualization directory to path and retry
        sys.path.append(SCRIPT_DIR)
        from config import T_COLOR, CT_COLOR, BOTH_COLOR, WIN_COLOR, LOSS_COLOR, LINE_ALPHA

# Player colors for multi-player comparison
PLAYER_COLORS = [
    "#1f77b4",  # Blue
    "#ff7f0e",  # Orange
    "#2ca02c",  # Green
    "#d62728",  # Red
]


def get_available_columns():
    """Return list of available metric columns from the dataset."""
    df = pd.read_csv(DATA_PATH)
    # Exclude non-metric columns
    exclude = ['stages', 'map', 'team', 'player_name', 'player_steamid', 'side']
    return [col for col in df.columns if col not in exclude]


def get_available_players():
    """Return list of available player names."""
    df = pd.read_csv(DATA_PATH)
    return sorted(df['player_name'].unique().tolist())


def get_available_stages():
    """Return list of available stages."""
    df = pd.read_csv(DATA_PATH)
    return sorted(df['stages'].unique().tolist())


def get_available_maps():
    """Return list of available maps."""
    df = pd.read_csv(DATA_PATH)
    return sorted(df['map'].unique().tolist())


def get_scope_options():
    """
    Return a dictionary of all available scope options.
    
    Returns:
        dict: Keys are scope types ('stages', 'maps', 'stage_map'), 
              values are lists of available options
    """
    df = pd.read_csv(DATA_PATH)
    return {
        'stages': sorted(df['stages'].unique().tolist()),
        'maps': sorted(df['map'].unique().tolist()),
        'stage_map': {
            'stages': sorted(df['stages'].unique().tolist()),
            'maps': sorted(df['map'].unique().tolist())
        }
    }


def filter_data(df, player_names, side=None, stage=None, map_name=None, scope="all"):
    """
    Filter the dataframe based on scope and parameters.
    
    Args:
        df: Full dataframe
        player_names: List of player names to include
        side: Filter by side ('Counter Terrorist', 'Terrorist', 'Both')
        stage: Filter by stage
        map_name: Filter by map name
        scope: Data scope - 'all', 'stage', 'map', 'stage_map'
    
    Returns:
        Filtered dataframe
    """
    mask = df['player_name'].isin(player_names)
    
    if side is not None:
        mask &= (df['side'] == side)
    
    if scope == "stage" and stage is not None:
        mask &= (df['stages'] == stage)
    elif scope == "map" and map_name is not None:
        mask &= (df['map'] == map_name)
    elif scope == "stage_map":
        if stage is not None:
            mask &= (df['stages'] == stage)
        if map_name is not None:
            mask &= (df['map'] == map_name)
    # scope == "all" uses no additional filtering
    
    return df[mask].copy()


def calculate_metrics(df, metrics):
    """
    Calculate derived metrics (like K/D Ratio) and return a dict of metric values and total rounds played.
    
    Args:
        df: Dataframe with player data
        metrics: List of metric names to compute (may include calculated ones)
    
    Returns:
        tuple: (dict mapping metric names to their round-weighted values, float total rounds)
    """
    result = {}
    total_rounds = float(df['Rounds Played'].sum())
    
    # Calculate global sums for ratio metrics
    total_kills = df['Kills'].sum()
    total_deaths = df['Deaths'].sum()
    total_headshots = df['Headshots'].sum() if 'Headshots' in df.columns else 0.0
    
    for metric in metrics:
        if metric == "K/D Ratio":
            result[metric] = total_kills / total_deaths if total_deaths > 0 else 0.0
        elif metric == "Headshot %":
            result[metric] = (total_headshots / total_kills) * 100.0 if total_kills > 0 else 0.0
        elif metric == "Deaths":
            # For deaths, we want to invert (lower is better)
            # Return negative so it can be inverted during normalization
            # We calculate deaths per round
            result[metric] = -(total_deaths / total_rounds) if total_rounds > 0 else 0.0
        elif metric == "Rounds Played":
            result[metric] = total_rounds
        else:
            # Absolute metric per round
            result[metric] = df[metric].sum() / total_rounds if total_rounds > 0 else 0.0
            
    return result, total_rounds


def hex_to_rgba(hex_color, alpha=0.25):
    """Convert hex color to rgba string."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'


def create_spider_chart(
    player_names=None,
    metrics=None,
    side=None,
    stage=None,
    map_name=None,
    scope="all",
    show=True
):
    """
    Create a spider/radar chart for player performance comparison.
    
    Args:
        player_names (list): List of player names (1 or 2 players). 
                            If None, defaults to ["ZywOo"]
        metrics (list): List of metric columns to include. 
                       If None, defaults to standard CS2 metrics.
        side (str): Filter by side - 'Counter Terrorist', 'Terrorist', or 'Both'
        stage (str): Filter by stage when scope is 'stage' or 'stage_map'
        map_name (str): Filter by map when scope is 'map' or 'stage_map'
        scope (str): Data scope - 'all', 'stage', 'map', 'stage_map'. Default 'all'
        show (bool): Whether to display the chart. Default True. 
                    Set to False for Streamlit/Notebook integration to avoid duplicate display.
    
    Returns:
        go.Figure: The Plotly figure object when show=False
        None: When show=True (plot is displayed directly)
    """
    # Load data
    df_all = pd.read_csv(DATA_PATH)
    
    # Default values
    if player_names is None:
        player_names = ["ZywOo"]
    
    if metrics is None:
        metrics = ["Kills", "Assists", "K/D Ratio", "Smokes Thrown", "Molotovs Thrown", "Grenades"]
    
    # Validate inputs
    available_players = get_available_players()
    for player in player_names:
        if player not in available_players:
            raise ValueError(f"Player '{player}' not found. Available players: {available_players}")
    
    if len(player_names) > 2:
        raise ValueError("Maximum 2 players can be compared at once")
    
    available_metrics = get_available_columns() + ["K/D Ratio"]
    for metric in metrics:
        if metric not in available_metrics:
            raise ValueError(f"Metric '{metric}' not found. Available: {available_metrics}")
    
    if scope == "stage" and stage is None:
        raise ValueError("scope='stage' requires stage parameter")
    if scope == "map" and map_name is None:
        raise ValueError("scope='map' requires map_name parameter")
    
    # Filter data for all requested players
    df = filter_data(df_all, player_names, side=side, stage=stage, map_name=map_name, scope=scope)
    
    if len(df) == 0:
        raise ValueError(f"No data found for players {player_names} with the specified filters")
    
    # Get normalization values from ALL data (for consistency)
    norm_values = {}
    for metric in metrics:
        if metric == "K/D Ratio":
            kd_ratios = df_all.apply(
                lambda row: row['Kills'] / row['Deaths'] if row['Deaths'] > 0 else 0.0, axis=1
            )
            norm_values[metric] = kd_ratios.max()
        elif metric == "Headshot %":
            norm_values[metric] = df_all['Headshot %'].max() if 'Headshot %' in df_all.columns else 100.0
        elif metric == "Deaths":
            # Normalize against max per-round death rate
            norm_values[metric] = (df_all['Deaths'] / df_all['Rounds Played']).max()
        else:
            # Normalize against max per-round rate
            norm_values[metric] = (df_all[metric] / df_all['Rounds Played']).max()
    
    # Create figure
    fig = go.Figure()
    
    # Get unique sides in the filtered data
    unique_sides = df['side'].unique()
    
    # If no side filter, use all available sides
    if side is None:
        sides_to_plot = list(unique_sides)
    else:
        sides_to_plot = [side]
    
    # Process each player and side combination
    for player_idx, player in enumerate(player_names):
        for current_side in sides_to_plot:
            player_df = df[(df['player_name'] == player) & (df['side'] == current_side)]
            
            if len(player_df) == 0:
                continue
            
            # Calculate metric values and rounds count
            metric_values, total_rounds = calculate_metrics(player_df, metrics)
            
            # Normalize values to 0-100 scale
            normalized_values = []
            for metric in metrics:
                max_val = norm_values[metric]
                if max_val == 0:
                    normalized_values.append(0)
                else:
                    if metric == "Deaths":
                        # Invert deaths (lower is better, so 0 is 100%, max_val is 0%)
                        # metric_values[metric] is negative, so -metric_values[metric] is positive
                        actual_val = -metric_values[metric]
                        normalized_values.append((1.0 - (actual_val / max_val)) * 100.0)
                    else:
                        normalized_values.append((metric_values[metric] / max_val) * 100.0)
            
            # Determine color
            if len(player_names) == 1:
                # Single player - use side colors
                side_colors = {
                    'Counter Terrorist': CT_COLOR,
                    'Terrorist': T_COLOR,
                    'Both': BOTH_COLOR
                }
                line_color = side_colors.get(current_side, BOTH_COLOR)
            else:
                # Multiple players - use player colors
                line_color = PLAYER_COLORS[player_idx]
            
            rgba_color = hex_to_rgba(line_color, 0.15)
            
            # Create display name
            if len(player_names) == 1 and len(sides_to_plot) > 1:
                display_name = current_side.replace(' Counter Terrorist', ' CT').replace('Terrorist', 'T')
            elif len(player_names) > 1 and len(sides_to_plot) > 1:
                display_name = f"{player} ({current_side.replace(' Counter Terrorist', 'CT').replace('Terrorist', 'T')})"
            elif len(player_names) > 1:
                display_name = player
            else:
                display_name = current_side.replace(' Counter Terrorist', ' CT').replace('Terrorist', 'T')
            
            # Add display name with round count
            display_name_with_count = f"{display_name} ({total_rounds:.0f} rounds)"
            
            # Build custom hover text that shows the actual average value for each metric
            custom_hover_texts = []
            for metric, norm_val in zip(metrics, normalized_values):
                raw_value = metric_values[metric]
                if metric == "Deaths":
                    raw_value = -raw_value  # Invert back for display
                
                if metric == "K/D Ratio":
                    total_kills = player_df['Kills'].sum()
                    total_deaths = player_df['Deaths'].sum()
                    custom_hover_texts.append(
                        f"K/D Ratio: {raw_value:.2f}<br>"
                        f"Total Kills: {total_kills:.0f}<br>"
                        f"Total Deaths: {total_deaths:.0f}"
                    )
                elif metric == "Headshot %":
                    total_headshots = player_df['Headshots'].sum() if 'Headshots' in player_df.columns else 0.0
                    total_kills = player_df['Kills'].sum()
                    custom_hover_texts.append(
                        f"Headshot %: {raw_value:.1f}%<br>"
                        f"Total Headshots: {total_headshots:.0f}<br>"
                        f"Total Kills: {total_kills:.0f}"
                    )
                elif metric == "Deaths":
                    deaths_per_round = -raw_value
                    total_deaths = player_df['Deaths'].sum()
                    custom_hover_texts.append(
                        f"Deaths/round: {deaths_per_round:.2f}<br>"
                        f"Total Deaths: {total_deaths:.0f}<br>"
                        f"Rounds: {total_rounds:.0f}"
                    )
                else:
                    total_val = player_df[metric].sum()
                    custom_hover_texts.append(
                        f"{metric}/round: {raw_value:.2f}<br>"
                        f"Total {metric}: {total_val:.0f}<br>"
                        f"Rounds: {total_rounds:.0f}"
                    )
            
            # Create the radar trace with custom hover text per point
            # For multiple traces, use fill='none' to prevent fill areas from blocking hover
            # For single trace, use fill for better visualization
            trace_count = len(player_names) * len(sides_to_plot)
            has_multiple_traces = trace_count > 1
            
            # Close the polygon by appending the first value at the end
            r_values = normalized_values + [normalized_values[0]]
            theta_values = list(metrics) + [metrics[0]]
            hover_values = list(custom_hover_texts) + [custom_hover_texts[0]]
            
            fig.add_trace(go.Scatterpolar(
                r=r_values,
                theta=theta_values,
                fill='none' if has_multiple_traces else 'toself',
                name=display_name_with_count,
                line_color=line_color,
                fillcolor=rgba_color,
                marker=dict(size=10, color=line_color, line=dict(width=2, color='white')),
                hoverinfo='text',
                hovertext=hover_values,
                text=hover_values
            ))
    
    # Calculate max value for radial axis
    all_normalized_values = []
    for trace in fig.data:
        all_normalized_values.extend(trace.r)
    max_r_value = max(all_normalized_values) if all_normalized_values else 100
    # Add 10% padding
    radial_max = max_r_value * 1.1
    
    # Generate appropriate tick values
    tick_count = 5
    tick_step = radial_max / (tick_count - 1)
    tickvals = [i * tick_step for i in range(tick_count)]
    ticktext = [f"{int(v)}" for v in tickvals]
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, radial_max],
                tickvals=tickvals,
                ticktext=ticktext,
                tickangle=45
            )
        ),
        showlegend=True,
        title=f"Player Performance Comparison - {', '.join(player_names)}"
        + (f" ({stage})" if stage else "")
        + (f" - {map_name}" if map_name else "")
        + (f" - {side}" if side else ""),
        title_x=0.5,
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    # Show if requested
    if show:
        fig.show()
        return None
    
    return fig


def main():
    """Main function to demonstrate the visualization."""
    # Example 1: Single player with all data
    print("Example 1: Single player (ZywOo) - All data")
    create_spider_chart(
        player_names=["ZywOo"],
        side="Both",
        scope="all"
    )
    
    # Example 2: Two players comparison
    print("\nExample 2: Two players (ZywOo vs broky) - Final stage")
    create_spider_chart(
        player_names=["ZywOo", "broky"],
        side="Both",
        scope="stage",
        stage="Final"
    )
    
    # Example 3: Single player with custom metrics
    print("\nExample 3: Single player with custom metrics")
    create_spider_chart(
        player_names=["ZywOo"],
        metrics=["Kills", "Assists", "K/D Ratio", "Deaths"],
        side="Both",
        scope="all"
    )


if __name__ == "__main__":
    # main()
    ...
