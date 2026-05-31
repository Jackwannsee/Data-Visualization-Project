import os
import pandas as pd
import plotly.graph_objects as go
import importlib.util
import sys

# Get script directory and resolve paths relative to it
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_stats.csv")

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

# List of available metrics to plot
METRICS = ["Kills", "Assists", "Deaths", "Headshots", "Smokes Thrown", "Molotovs Thrown", "Grenades", "Rounds Played"]

def get_data(stage=None, map_name=None, team=None):
    """Load and filter stats data."""
    df = pd.read_csv(DATA_PATH)
    
    # Filter out 'Both' to only get CT and T
    df = df[df['side'] != 'Both']
    
    if stage:
        df = df[df['stages'] == stage]
    if map_name:
        df = df[df['map'] == map_name]
    if team:
        df = df[df['team'] == team]
        
    return df

def plot_team_comparison(stage=None, map_name=None, metric="Kills", normalize=False):
    """Plot stacked bar chart comparing teams CT vs T."""
    df = get_data(stage, map_name)
    if df.empty:
        return go.Figure()
    
    # Aggregate by team and side
    agg_df = df.groupby(['team', 'side'])[metric].sum().reset_index()
    
    return _create_stacked_bar(
        df=agg_df, 
        entity_col='team', 
        metric=metric, 
        normalize=normalize, 
        title=f"Team {metric} by Side (CT vs T)"
    )

def plot_player_comparison(team, stage=None, map_name=None, metric="Kills", normalize=False):
    """Plot stacked bar chart comparing players CT vs T for a specific team."""
    df = get_data(stage, map_name, team)
    if df.empty:
        return go.Figure()
        
    # Aggregate by player and side
    agg_df = df.groupby(['player_name', 'side'])[metric].sum().reset_index()
    
    return _create_stacked_bar(
        df=agg_df, 
        entity_col='player_name', 
        metric=metric, 
        normalize=normalize, 
        title=f"{team} Players {metric} by Side (CT vs T)"
    )

def _create_stacked_bar(df, entity_col, metric, normalize, title):
    """Helper to generate the Plotly figure."""
    # Pivot to get CT and T columns
    pivot_df = df.pivot(index=entity_col, columns='side', values=metric).fillna(0)
    
    # Ensure both sides exist in data
    if 'Counter Terrorist' not in pivot_df.columns:
        pivot_df['Counter Terrorist'] = 0
    if 'Terrorist' not in pivot_df.columns:
        pivot_df['Terrorist'] = 0
        
    pivot_df['Total'] = pivot_df['Counter Terrorist'] + pivot_df['Terrorist']
    pivot_df = pivot_df.sort_values('Total', ascending=True) # Sort ascending for horizontal bar chart
    
    entities = pivot_df.index.tolist()
    ct_values = pivot_df['Counter Terrorist'].tolist()
    t_values = pivot_df['Terrorist'].tolist()
    totals = pivot_df['Total'].tolist()
    
    if normalize:
        # Avoid division by zero
        safe_totals = [t if t > 0 else 1 for t in totals]
        ct_plot = [ct / t * 100 for ct, t in zip(ct_values, safe_totals)]
        t_plot = [t_val / t * 100 for t_val, t in zip(t_values, safe_totals)]
        hover_template_ct = "<b>%{y}</b><br>CT: %{customdata[0]:.1f} (%{x:.1f}%)<br>Total: %{customdata[1]:.1f}<extra></extra>"
        hover_template_t = "<b>%{y}</b><br>T: %{customdata[0]:.1f} (%{x:.1f}%)<br>Total: %{customdata[1]:.1f}<extra></extra>"
        xaxis_title = f'Percentage of {metric} (%)'
        barmode = 'stack'
    else:
        ct_plot = ct_values
        t_plot = t_values
        hover_template_ct = "<b>%{y}</b><br>CT: %{x:.1f}<br>Total: %{customdata[1]:.1f}<extra></extra>"
        hover_template_t = "<b>%{y}</b><br>T: %{x:.1f}<br>Total: %{customdata[1]:.1f}<extra></extra>"
        xaxis_title = metric
        barmode = 'stack'

    fig = go.Figure()

    # Counter Terrorist Bar
    fig.add_trace(go.Bar(
        y=entities,
        x=ct_plot,
        name='Counter Terrorist',
        orientation='h',
        marker_color=CT_COLOR,
        customdata=list(zip(ct_values, totals)),
        hovertemplate=hover_template_ct
    ))

    # Terrorist Bar
    fig.add_trace(go.Bar(
        y=entities,
        x=t_plot,
        name='Terrorist',
        orientation='h',
        marker_color=T_COLOR,
        customdata=list(zip(t_values, totals)),
        hovertemplate=hover_template_t
    ))

    fig.update_layout(
        title=title,
        barmode=barmode,
        yaxis_title=entity_col.replace('_', ' ').title(),
        xaxis_title=xaxis_title,
        legend_title="Side",
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        font=dict(family="Inter, Roboto, Arial", size=14)
    )
    
    # Add subtle grid lines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(211, 211, 211, 0.5)')

    return fig

# Helper functions for UI dropdowns
def get_available_stages():
    df = pd.read_csv(DATA_PATH)
    return sorted(df['stages'].dropna().unique().tolist())

def get_available_maps(stage=None):
    df = pd.read_csv(DATA_PATH)
    if stage:
        df = df[df['stages'] == stage]
    return sorted(df['map'].dropna().unique().tolist())

def get_available_teams(stage=None, map_name=None):
    df = pd.read_csv(DATA_PATH)
    if stage:
        df = df[df['stages'] == stage]
    if map_name:
        df = df[df['map'] == map_name]
    return sorted(df['team'].dropna().unique().tolist())

if __name__ == "__main__":
    # Test execution
    print("Testing Team Plot")
    fig_team = plot_team_comparison(metric="Kills", normalize=False)
    # fig_team.show() # Uncomment to view
    
    print("Testing Player Plot")
    fig_player = plot_player_comparison(team="FaZe Clan", metric="Kills", normalize=True)
    # fig_player.show() # Uncomment to view
    print("Tests completed successfully.")
