import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go

try:
    from data_loader import load_csv
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import load_csv

# Resolve script paths relative to it
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_stats.csv")
DETAILS_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_match_details.csv")

# Import config colors - handle absolute path import to prevent collisions with other 'config' modules
try:
    import importlib.util
    config_path = os.path.join(SCRIPT_DIR, "config.py")
    spec = importlib.util.spec_from_file_location("viz_config", config_path)
    viz_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(viz_config)
    TEAM_COLORS = viz_config.TEAM_COLORS
    DEFAULT_COLORS = viz_config.DEFAULT_COLORS
except Exception:
    # Fallback to standard imports if path-based import fails
    try:
        from config import TEAM_COLORS, DEFAULT_COLORS
    except (ModuleNotFoundError, ImportError):
        # Add visualization directory to path and retry
        sys.path.append(SCRIPT_DIR)
        from config import TEAM_COLORS, DEFAULT_COLORS


def get_available_stages():
    """Return list of available stages."""
    df = load_csv(STATS_PATH)
    return sorted(df['stages'].unique().tolist())


def get_available_maps():
    """Return list of available maps."""
    df = load_csv(STATS_PATH)
    return sorted(df['map'].unique().tolist())


def get_available_sides():
    """Return list of available sides."""
    return ["Both", "Counter Terrorist", "Terrorist"]


def create_headshot_scatter(side='Both', stage=None, map_name=None, x_metric='KPR', show=True):
    """
    Create a scatter plot plotting overall headshot percentage against kills/KPR,
    taking into account how many rounds players played in total.

    Args:
        side (str): Side filter ('Counter Terrorist', 'Terrorist', 'Both')
        stage (str): Tournament stage filter (e.g. 'Final', 'Semifinals', 'Quarterfinals', 'All' or None)
        map_name (str): Map name filter (e.g. 'Dust2', 'All' or None)
        x_metric (str): X-axis metric to plot ('KPR' for Kills Per Round, or 'Kills' for Total Kills)
        show (bool): Whether to display the plot directly using fig.show()

    Returns:
        go.Figure: The Plotly figure object
    """
    # Load dataset files
    df_stats = load_csv(STATS_PATH)
    df_details = load_csv(DETAILS_PATH)

    # Filter stats and details by side
    if side is not None and side != 'All':
        df_stats = df_stats[df_stats['side'] == side]
        df_details = df_details[df_details['side'] == side]

    # Join stats with details to connect exact rounds played to stats
    # Merge on stages, map, team, side
    merged = pd.merge(
        df_stats,
        df_details[['stages', 'map', 'team', 'side', 'rounds_played']],
        on=['stages', 'map', 'team', 'side'],
        how='inner'
    )

    # Apply stage and map filters
    if stage is not None and stage != "All":
        merged = merged[merged['stages'] == stage]
    if map_name is not None and map_name != "All":
        merged = merged[merged['map'] == map_name]

    if len(merged) == 0:
        raise ValueError(f"No data found matching current filters: side={side}, stage={stage}, map={map_name}")

    # Aggregate stats per player
    # Using true aggregates over the filtered scope rather than averages to ensure statistical accuracy
    player_stats = merged.groupby(['player_name', 'team']).agg(
        total_kills=('Kills', 'sum'),
        total_headshots=('Headshots', 'sum'),
        total_rounds=('rounds_played', 'sum')
    ).reset_index()

    # Calculate metrics
    player_stats['KPR'] = player_stats.apply(
        lambda r: r['total_kills'] / r['total_rounds'] if r['total_rounds'] > 0 else 0,
        axis=1
    )
    player_stats['Headshot %'] = player_stats.apply(
        lambda r: (r['total_headshots'] / r['total_kills'] * 100) if r['total_kills'] > 0 else 0,
        axis=1
    ).round(2)

    # Setup selected X-axis metric
    if x_metric == 'KPR':
        x_col = 'KPR'
        x_label = 'Kills Per Round (KPR)'
        x_format = '.3f'
    elif x_metric == 'Kills':
        x_col = 'total_kills'
        x_label = 'Total Kills'
        x_format = '.0f'
    else:
        raise ValueError(f"Invalid x_metric '{x_metric}'. Expected 'KPR' or 'Kills'.")

    # Generate custom hover tooltip HTML for a premium feeling
    hover_texts = []
    for _, row in player_stats.iterrows():
        hover_html = (
            f"<b>{row['player_name']}</b> ({row['team']})<br><br>"
            f"🎯 Headshot %: <b>{row['Headshot %']:.1f}%</b><br>"
            f"⚔️ Kills Per Round (KPR): <b>{row['KPR']:.3f}</b><br>"
            f"💀 Total Kills: {row['total_kills']:.0f}<br>"
            f"🔴 Total Headshots: {row['total_headshots']:.0f}<br>"
            f"⏳ Rounds Played: {row['total_rounds']:.0f}"
        )
        hover_texts.append(hover_html)
    player_stats['hover_text'] = hover_texts

    # Create figure
    fig = go.Figure()

    # Get unique teams to trace separately (provides perfect legend toggle interactions)
    unique_teams = sorted(player_stats['team'].unique())
    
    # Scaling parameter for scatter marker sizes
    # We want max rounds to map to size 30, and min size to be 8
    max_rounds = max(player_stats['total_rounds']) if len(player_stats) > 0 else 1
    
    for idx, team in enumerate(unique_teams):
        team_df = player_stats[player_stats['team'] == team]
        
        # Get centralized team colors
        color = TEAM_COLORS.get(team, DEFAULT_COLORS[idx % len(DEFAULT_COLORS)])
        
        fig.add_trace(go.Scatter(
            x=team_df[x_col],
            y=team_df['Headshot %'],
            mode='markers',
            name=team,
            marker=dict(
                size=12,
                color=color,
                line=dict(width=1.5, color='rgba(255,255,255,0.8)')
            ),
            text=team_df['hover_text'],
            hoverinfo='text',
        ))

    # Add trendline across all plotted data points
    if len(player_stats) > 1:
        x_vals = player_stats[x_col].values
        y_vals = player_stats['Headshot %'].values
        
        # Calculate regression slope and intercept
        m, c = np.polyfit(x_vals, y_vals, 1)
        
        # Define line endpoints
        x_trend = np.linspace(min(x_vals) * 0.95, max(x_vals) * 1.05, 100)
        y_trend = m * x_trend + c
        
        # Calculate R-squared metric
        y_pred = m * x_vals + c
        ss_res = np.sum((y_vals - y_pred) ** 2)
        ss_tot = np.sum((y_vals - np.mean(y_vals)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        trend_name = f"Trendline (R² = {r_squared:.2f})"
        trend_hover = f"Trendline Fit:<br>y = {m:.3f}x + {c:.2f}<br>R² = {r_squared:.2f}"
        
        fig.add_trace(go.Scatter(
            x=x_trend,
            y=y_trend,
            mode='lines',
            name=trend_name,
            line=dict(color='rgba(255,255,255,0.3)', width=2, dash='dash'),
            hoverinfo='text',
            hovertext=trend_hover
        ))

    # Add tournament-wide average reference lines
    avg_x = player_stats[x_col].mean()
    avg_y = player_stats['Headshot %'].mean()

    # Horizontal Avg Headshot % Line
    fig.add_hline(
        y=avg_y,
        line_dash="dot",
        line_color="rgba(255,255,255,0.25)",
        annotation_text=f"Tournament Avg HS%: {avg_y:.1f}%",
        annotation_position="bottom left",
        annotation_font=dict(color="rgba(255,255,255,0.5)", size=10)
    )

    # Vertical Avg KPR / Kills Line
    fig.add_vline(
        x=avg_x,
        line_dash="dot",
        line_color="rgba(255,255,255,0.25)",
        annotation_text=f"Tournament Avg: {avg_x:.3f}" if x_metric == 'KPR' else f"Tournament Avg: {avg_x:.1f}",
        annotation_position="top right",
        annotation_font=dict(color="rgba(255,255,255,0.5)", size=10)
    )

    # Determine dynamic subtitle based on selections
    filters = []
    if stage and stage != "All":
        filters.append(stage)
    if map_name and map_name != "All":
        filters.append(map_name)
    if side and side != "Both":
        filters.append(side)
    
    subtitle = f" ({', '.join(filters)})" if filters else ""
    title_text = f"Player Headshot % vs. {x_label}{subtitle}"

    # Style layout with a highly-polished premium dark theme
    fig.update_layout(
        title=dict(
            text=title_text,
            x=0.5,
            y=0.96,
            font=dict(size=18, color="#FAB200", family="Inter, sans-serif")
        ),
        xaxis=dict(
            title=dict(
                text=x_label,
                font=dict(color="#ccc")
            ),
            gridcolor="rgba(42, 45, 53, 0.4)",
            linecolor="#2a2d35",
            tickfont=dict(color="#aaa"),
            zeroline=False
        ),
        yaxis=dict(
            title=dict(
                text="Overall Headshot Percentage (%)",
                font=dict(color="#ccc")
            ),
            gridcolor="rgba(42, 45, 53, 0.4)",
            linecolor="#2a2d35",
            tickfont=dict(color="#aaa"),
            zeroline=False
        ),
        paper_bgcolor="#1a1d23",
        plot_bgcolor="#1a1d23",
        font=dict(color="#ccc", family="Inter, sans-serif"),
        legend=dict(
            font=dict(color="#ccc", size=11),
            bgcolor="rgba(26, 29, 35, 0.85)",
            bordercolor="#2a2d35",
            borderwidth=1,
            title=dict(text="Teams (Click to Toggle)", font=dict(color="#FAB200", size=11))
        ),
        hovermode="closest",
        margin=dict(t=70, b=50, l=60, r=40)
    )

    if show:
        fig.show()

    return fig


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate CS2 Headshot vs Kills Scatter Plot.")
    parser.add_argument("--side", type=str, default="Both", choices=["Both", "Counter Terrorist", "Terrorist"])
    parser.add_argument("--stage", type=str, default="All", choices=["All", "Final", "Semifinals", "Quarterfinals"])
    parser.add_argument("--map", type=str, default="All")
    parser.add_argument("--metric", type=str, default="KPR", choices=["KPR", "Kills"])
    parser.add_argument("--output", type=str, default="headshot_scatter.html")
    args = parser.parse_args()

    # Generate the visualization
    print(f"Generating Headshot Scatter Plot (Side: {args.side}, Stage: {args.stage}, Map: {args.map}, Metric: {args.metric})...")
    figure = create_headshot_scatter(
        side=args.side,
        stage=args.stage,
        map_name=args.map,
        x_metric=args.metric,
        show=False
    )

    # Save to file
    out_path = os.path.join(SCRIPT_DIR, args.output)
    figure.write_html(out_path)
    print(f"Successfully saved interactive plot to: {out_path}")
