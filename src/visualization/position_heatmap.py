"""Plotly heatmap of CS2 player positions overlaid on map radar images.

Produces interactive figures from analysis_results/budapest_major_positions.csv.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

try:
    from data_loader import load_csv
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from data_loader import load_csv

# Resolve script paths relative to it
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POSITIONS_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_positions.csv")
MAPS_DIR = os.path.join(SCRIPT_DIR, "assets/Maps")

# Import config colors - handle absolute path import to prevent collisions
try:
    import importlib.util
    config_path = os.path.join(SCRIPT_DIR, "config.py")
    spec = importlib.util.spec_from_file_location("viz_config", config_path)
    viz_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(viz_config)
    TEAM_COLORS = viz_config.TEAM_COLORS
    DEFAULT_COLORS = viz_config.DEFAULT_COLORS
except Exception:
    try:
        from config import TEAM_COLORS, DEFAULT_COLORS
    except (ModuleNotFoundError, ImportError):
        sys.path.append(SCRIPT_DIR)
        from config import TEAM_COLORS, DEFAULT_COLORS

# ---------------------------------------------------------------------------
# Map configuration
# ---------------------------------------------------------------------------
MAP_CONFIG = {
    'Nuke': {
        'key': 'de_nuke',
        'has_levels': True,
        'images': {
            'upper': 'de_nuke_radar_psd.png',
            'lower': 'de_nuke_lower_radar_psd.png',
        },
        'pos_x': -3453, 'pos_y': 2887, 'scale': 7.0
    },
    'Dust2': {
        'key': 'de_dust2',
        'has_levels': False,
        'images': {'upper': 'de_dust2_radar_psd.png'},
        'pos_x': -2476, 'pos_y': 3239, 'scale': 4.4
    },
    'Inferno': {
        'key': 'de_inferno',
        'has_levels': False,
        'images': {'upper': 'de_inferno_radar_psd.png'},
        'pos_x': -2087, 'pos_y': 3870, 'scale': 4.9
    },
    'Mirage': {
        'key': 'de_mirage',
        'has_levels': False,
        'images': {'upper': 'de_mirage_radar_psd.png'},
        'pos_x': -3230, 'pos_y': 1713, 'scale': 5.0
    },
    'Ancient': {
        'key': 'de_ancient',
        'has_levels': False,
        'images': {'upper': 'de_ancient_radar_psd.png'},
        'pos_x': -2953, 'pos_y': 2164, 'scale': 5.0
    },
    'Overpass': {
        'key': 'de_overpass',
        'has_levels': False,
        'images': {'upper': 'de_overpass_radar_psd.png'},
        'pos_x': -4831, 'pos_y': 1781, 'scale': 5.2
    },
    'Train': {
        'key': 'de_train',
        'has_levels': True,
        'images': {
            'upper': 'de_train_radar_psd.png',
            'lower': 'de_train_lower_radar_psd.png',
        },
        'pos_x': -2308, 'pos_y': 2078, 'scale': 4.082077
    },
}

IMG_SIZE = 1024

# ---------------------------------------------------------------------------
# Custom colorscales (zero-density areas are transparent)
# ---------------------------------------------------------------------------
CT_COLORSCALE = [
    [0.0,  'rgba(0,0,0,0)'],
    [0.01, 'rgba(0,70,160,0.5)'],
    [0.15, 'rgba(0,100,200,0.65)'],
    [0.4,  'rgba(0,140,220,0.75)'],
    [0.7,  'rgba(30,180,255,0.85)'],
    [1.0,  'rgba(120,215,255,0.95)'],
]

T_COLORSCALE = [
    [0.0,  'rgba(0,0,0,0)'],
    [0.01, 'rgba(160,80,0,0.5)'],
    [0.15, 'rgba(200,120,0,0.65)'],
    [0.4,  'rgba(240,160,0,0.75)'],
    [0.7,  'rgba(250,190,0,0.85)'],
    [1.0,  'rgba(255,220,60,0.95)'],
]

BOTH_COLORSCALE = [
    [0.0,  'rgba(0,0,0,0)'],
    [0.01, 'rgba(80,0,120,0.5)'],
    [0.15, 'rgba(160,0,80,0.6)'],
    [0.35, 'rgba(220,50,0,0.7)'],
    [0.6,  'rgba(250,140,0,0.8)'],
    [0.85, 'rgba(255,210,0,0.88)'],
    [1.0,  'rgba(255,255,80,0.95)'],
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_available_maps() -> list:
    """Return list of map display names from the positions CSV."""
    df = load_csv(POSITIONS_PATH)
    return sorted(df['map'].unique().tolist())


def get_available_stages() -> list:
    """Return sorted list of tournament stages from the positions CSV."""
    df = load_csv(POSITIONS_PATH)
    return sorted(df['stages'].unique().tolist())


def get_available_matches(map_name: str = None) -> list:
    """Return list of 'Team A vs Team B' strings, optionally filtered by map."""
    df = load_csv(POSITIONS_PATH)
    if map_name:
        df = df[df['map'] == map_name]
    return sorted(df['teams'].unique().tolist())


def has_levels(map_name: str) -> bool:
    """Return whether the map has upper/lower levels."""
    return MAP_CONFIG.get(map_name, {}).get('has_levels', False)


# ---------------------------------------------------------------------------
# Core heatmap function
# ---------------------------------------------------------------------------
def create_position_heatmap(
    map_name: str,
    side: str = 'Both',
    level: str = 'upper',
    granularity: int = 50,
    stage: str = None,
    match: str = None,
    opacity: float = 0.65,
    show: bool = True,
    colorscale_name: str = None,
) -> go.Figure:
    """Create a position heatmap overlaid on a map radar image.

    Args:
        map_name: Display name (e.g. "Nuke", "Dust2")
        side: "Both", "CT", or "T"
        level: "upper" or "lower" (only matters for Nuke/Train)
        granularity: Grid bin size in game units (25, 50, 100, 200)
        stage: Tournament stage filter or None
        match: "Team A vs Team B" filter or None
        opacity: Heatmap opacity (0-1)
        show: Whether to display the figure
        colorscale_name: Override side-based palette. One of "CT", "T", "Both",
                         or a Plotly colorscale name (e.g. "Viridis", "Hot").
                         Defaults to side-based selection when None.

    Returns:
        Plotly Figure object
    """
    # Load data
    df = load_csv(POSITIONS_PATH)

    # Filter by map
    df = df[df['map'] == map_name]
    if len(df) == 0:
        raise ValueError(f"No position data found for map '{map_name}'")

    # Filter by side (CSV stores lowercase: "ct", "t")
    if side == 'CT':
        df = df[df['side'] == 'ct']
    elif side == 'T':
        df = df[df['side'] == 't']
    # "Both" — no side filter

    # Filter by level
    df = df[df['level'] == level]
    if len(df) == 0:
        raise ValueError(f"No data for {map_name} {level} level with current filters")

    # Filter by stage
    if stage is not None and stage != "All":
        df = df[df['stages'] == stage]

    # Filter by match
    if match is not None and match != "All":
        df = df[df['teams'] == match]

    if len(df) == 0:
        raise ValueError(f"No data remaining after filters for {map_name}")

    # Re-bin to requested granularity (base CSV is at granularity 25)
    if granularity > 25:
        df = df.copy()
        df['x_bin'] = (df['x_bin'] // granularity) * granularity
        df['y_bin'] = (df['y_bin'] // granularity) * granularity
        df = df.groupby(['x_bin', 'y_bin']).agg({'count': 'sum'}).reset_index()

    # Build the pixel grid
    config = MAP_CONFIG[map_name]
    
    # Use hardcoded awpy map metadata to prevent KeyErrors on Streamlit deployment
    pos_x, pos_y, scale = config.get('pos_x'), config.get('pos_y'), config.get('scale')
    
    # Fallback to awpy MAP_DATA if not found in our hardcoded config
    if pos_x is None:
        from awpy.data.map_data import MAP_DATA
        meta = MAP_DATA[config['key']]
        pos_x, pos_y, scale = meta['pos_x'], meta['pos_y'], meta['scale']

    pixel_cell = granularity / scale  # pixel size of each grid cell
    n_cells = max(1, int(IMG_SIZE / pixel_cell))
    grid = np.zeros((n_cells, n_cells), dtype=float)

    for _, row in df.iterrows():
        cx = row['x_bin'] + granularity / 2
        cy = row['y_bin'] + granularity / 2
        px = (cx - pos_x) / scale
        py = IMG_SIZE - (pos_y - cy) / scale  # flip y for Plotly
        gx = int(px / pixel_cell)
        gy = int(py / pixel_cell)
        if 0 <= gx < n_cells and 0 <= gy < n_cells:
            grid[gy, gx] += row['count']

    # Select colorscale
    if colorscale_name is not None:
        # User provided explicit palette name
        custom_palettes = {
            "Blues": CT_COLORSCALE,
            "Oranges/Golds": T_COLORSCALE,
            "Hot/Plasma": BOTH_COLORSCALE,
        }
        if colorscale_name in custom_palettes:
            colorscale = custom_palettes[colorscale_name]
        else:
            # Treat as a Plotly colorscale name (e.g. "Viridis", "Plasma")
            colorscale = colorscale_name
    elif side == 'CT':
        colorscale = CT_COLORSCALE
    elif side == 'T':
        colorscale = T_COLORSCALE
    else:
        colorscale = BOTH_COLORSCALE

    # Load radar image
    img_name = config['images'].get(level, config['images']['upper'])
    img_path = os.path.join(MAPS_DIR, img_name)
    img = Image.open(img_path)

    # Create figure
    fig = go.Figure()

    # Add radar image background
    fig.add_layout_image(
        dict(
            source=img,
            xref="x", yref="y",
            x=0, y=IMG_SIZE,
            sizex=IMG_SIZE, sizey=IMG_SIZE,
            xanchor="left", yanchor="top",
            sizing="stretch",
            opacity=1.0,
            layer="below"
        )
    )

    # Add heatmap trace
    x_centers = [(i + 0.5) * pixel_cell for i in range(n_cells)]
    y_centers = [(i + 0.5) * pixel_cell for i in range(n_cells)]

    max_val = np.max(grid) if np.max(grid) > 0 else 1

    fig.add_trace(go.Heatmap(
        x=x_centers,
        y=y_centers,
        z=grid,
        colorscale=colorscale,
        zmin=0,
        zmax=max_val,
        opacity=opacity,
        showscale=True,
        zsmooth='best',
        hoverongaps=False,
        colorbar=dict(
            title=dict(text="Position Density", font=dict(color="#ccc")),
            tickfont=dict(color="#aaa"),
            bgcolor="rgba(26,29,35,0.8)",
            bordercolor="#2a2d35",
        )
    ))

    # Configure axes
    fig.update_xaxes(range=[0, IMG_SIZE], visible=False, showgrid=False)
    fig.update_yaxes(range=[0, IMG_SIZE], visible=False, showgrid=False, scaleanchor="x")

    # Build title
    filters = []
    if stage and stage != "All":
        filters.append(stage)
    if match and match != "All":
        filters.append(match)
    if side != "Both":
        filters.append(side)
    subtitle = f" ({', '.join(filters)})" if filters else ""
    title_text = f"{map_name} — {level.title()} Level — Position Heatmap{subtitle}"

    # Style layout
    fig.update_layout(
        title=dict(
            text=title_text,
            x=0.5,
            y=0.97,
            font=dict(size=18, color="#FAB200", family="Inter, sans-serif")
        ),
        paper_bgcolor="#1a1d23",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc", family="Inter, sans-serif"),
        margin=dict(t=70, b=20, l=20, r=20),
        width=900,
        height=900,
    )

    if show:
        fig.show()

    return fig


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate CS2 Position Heatmap.")
    parser.add_argument("--map", type=str, default="Nuke",
                        choices=list(MAP_CONFIG.keys()))
    parser.add_argument("--side", type=str, default="Both",
                        choices=["Both", "CT", "T"])
    parser.add_argument("--level", type=str, default="upper",
                        choices=["upper", "lower"])
    parser.add_argument("--granularity", type=int, default=50,
                        choices=[25, 50, 100, 200])
    parser.add_argument("--stage", type=str, default=None,
                        choices=["All", "Final", "Semifinals", "Quarterfinals"])
    parser.add_argument("--output", type=str, default="position_heatmap.html")
    args = parser.parse_args()

    print(f"Generating Position Heatmap (Map: {args.map}, Side: {args.side}, "
          f"Level: {args.level}, Granularity: {args.granularity})...")

    figure = create_position_heatmap(
        map_name=args.map,
        side=args.side,
        level=args.level,
        granularity=args.granularity,
        stage=args.stage if args.stage != "All" else None,
        show=False,
    )

    out_path = os.path.join(SCRIPT_DIR, args.output)
    figure.write_html(out_path)
    print(f"Saved to: {out_path}")
