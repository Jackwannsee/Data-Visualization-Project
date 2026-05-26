# Player Position Heatmap Visualization Approach

## Overview

This document describes the approach for creating interactive heatmap visualizations of player positioning data from CS2 demo files, overlaid on actual map images with configurable granularity.

## Data Source

The **awpy** library parses CS2 `.dem` files and provides access to player positions through the `Demo.ticks` DataFrame.

### Available Position Data

| Column | Type | Description |
|--------|------|-------------|
| `X` | float32 | X coordinate in game units |
| `Y` | float32 | Y coordinate in game units |
| `Z` | float32 | Z coordinate (elevation) in game units |
| `steamid` | uint64 | Unique player identifier |
| `name` | str | Player name |
| `side` | str | Team side (`"ct"` or `"t"`) |
| `round_num` | uint32 | Current round number |
| `tick` | int32 | Game tick (128 ticks/second by default) |
| `health` | float64 | Current player health |
| `place` | str | Spawn location identifier |

### Map Information

Map name is available from `Demo.header['map_name']` (e.g., `"de_nuke"`, `"de_dust2"`).

## Coordinate System

Each CS2 map has its own coordinate system with different ranges:

| Map | X Range | Y Range | Z Range |
|-----|---------|---------|---------|
| de_nuke | -2005 to 3346 | -2480 to 935 | -776 to 11 |
| de_dust2 | -2186 to 1788 | -1164 to 3045 | varies |
| de_inferno | varies | varies | varies |

## Approach

### 1. Position Extraction

Extract player positions from demo files:

```python
from awpy import Demo
from pathlib import Path

demo = Demo(path=Path("dem_files/Final/vitality-vs-faze-m1-nuke.dem"))
demo.parse()

# Get all player positions
ticks = demo.ticks.to_pandas()
```

### 2. Data Filtering

Filter positions to include only valid in-game locations:
- Remove spawn positions (`place` contains "Spawn")
- Filter by reasonable Z values (typically -500 to 500 for playable areas)
- Optionally filter by specific round, player, or side

### 3. Spatial Binning (Granularity)

The core of the approach is **binning** the continuous position data into discrete grid cells. This allows us to aggregate position counts and create a heatmap.

**Binning formula:**
```python
x_bin = (x // granularity) * granularity
y_bin = (y // granularity) * granularity
```

Where `granularity` is the cell size in game units.

### 4. Aggregation

Count the number of player positions in each bin:

```python
# Group by bin and side
heatmap_data = positions.groupby(['map_name', 'x_bin', 'y_bin', 'side']).size()
```

This produces a sparse matrix of (x_bin, y_bin) coordinates with counts.

## Granularity Levels

The granularity parameter controls the detail level of the heatmap:

| Granularity | Cell Size | Detail Level | Use Case |
|-------------|-----------|---------------|----------|
| 25 | 25x25 units | Very High | Individual player movement, precise path analysis |
| 50 | 50x50 units | High | Team positioning, common paths |
| 100 | 100x100 units | Medium | Area control, general positioning patterns |
| 200 | 200x200 units | Low | Map area dominance, high-level overview |

**Trade-offs:**
- **Lower granularity (smaller cells):** More detail, larger data size, longer computation, may show noise
- **Higher granularity (larger cells):** Less detail, smaller data size, faster, shows general patterns

### Recommended Granularity by Analysis Type

| Analysis Type | Recommended Granularity |
|---------------|------------------------|
| Individual player analysis | 25-50 |
| Team positioning patterns | 50-100 |
| Map control visualization | 100-200 |
| Comparative analysis (CT vs T) | 100 |
| Tournament overview | 200 |

## Visualization Implementation

### Map Image Overlay

The heatmap is overlaid on the actual map image (radar/minimap) for context:

1. **Load map image** from `assets/maps/{map_name}.jpg`
2. **Create background layer** using the map image
3. **Create heatmap layer** with the binned position data
4. **Blend layers** with configurable opacity

### Plotly Implementation

```python
import plotly.graph_objects as go
from PIL import Image

# Add map background
fig.add_layout_image(
    dict(
        source=map_image,
        xref="x", yref="y",
        x=map_config['x_range'][0],
        y=map_config['y_range'][0],
        sizex=map_config['x_range'][1] - map_config['x_range'][0],
        sizey=map_config['y_range'][1] - map_config['y_range'][0],
        sizing="stretch",
        opacity=1.0,
        layer="below"
    )
)

# Add heatmap
fig.add_trace(go.Densitymapbox(
    x=x_bins,
    y=y_bins,
    z=counts,
    colorscale='Hot',
    opacity=0.7,
    zmin=0,
    zmax=max_count
))
```

### Color Scales

Different color scales can emphasize different aspects:

| Color Scale | Best For |
|-------------|----------|
| `Hot` | High-intensity areas (default) |
| `Viridis` | Perceptually uniform |
| `Plasma` | High contrast |
| `Reds` | Single-team focus |
| `Blues` | CT side visualization |
| `Oranges` | T side visualization |

## Implementation Files

### 1. Data Processing: `src/data_processing/parse_positions.py`

```python
"""Extract player positions from demo files for heatmap visualization."""

import json
from pathlib import Path
import pandas as pd
from awpy import Demo

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEM_DIR = PROJECT_ROOT / "dem_files"
JSON_PATH = PROJECT_ROOT / "src" / "budapest_major.json"


def parse_player_positions(
    dem_path: Path,
    map_name: str,
    granularity: int = 100,
    filter_spawns: bool = True,
    filter_z: bool = True
) -> pd.DataFrame:
    """
    Extract player positions binned into a grid.
    
    Args:
        dem_path: Path to .dem file
        map_name: Map name (e.g., 'de_nuke')
        granularity: Grid cell size in game units (lower = more detailed)
        filter_spawns: Remove spawn positions
        filter_z: Filter by reasonable Z values
        
    Returns:
        DataFrame with columns: map_name, side, x_bin, y_bin, count
    """
    demo = Demo(path=dem_path)
    demo.parse()
    
    # Extract positions
    ticks = demo.ticks.to_pandas()
    
    # Apply filters
    if filter_spawns:
        ticks = ticks[~ticks['place'].str.contains('Spawn', case=False, na=False)]
    
    if filter_z:
        ticks = ticks[(ticks['Z'] > -500) & (ticks['Z'] < 500)]
    
    # Bin coordinates
    ticks['x_bin'] = (ticks['X'] // granularity) * granularity
    ticks['y_bin'] = (ticks['Y'] // granularity) * granularity
    
    # Count positions per bin per side
    heatmap_data = ticks.groupby(['x_bin', 'y_bin', 'side']).size().reset_index(name='count')
    heatmap_data['map_name'] = map_name
    
    return heatmap_data[['map_name', 'side', 'x_bin', 'y_bin', 'count']]


def parse_tournament_positions(
    tournament_json: dict,
    granularity: int = 100
) -> pd.DataFrame:
    """
    Parse positions for all demos in a tournament.
    
    Args:
        tournament_json: Loaded tournament JSON
        granularity: Grid cell size
        
    Returns:
        Combined DataFrame for all matches
    """
    from src.data_processing.parse_demos import find_dem_file
    
    all_positions = []
    
    for stage_key, matches in tournament_json["stages"].items():
        for match in matches:
            teams = match["teams_played"]
            for map_info in match["maps_played"]:
                map_num = map_info["map_number"]
                map_name = map_info["map_name"].lower().replace("de_", "")
                
                dem_path = find_dem_file(stage_key, map_num, map_name, teams)
                if dem_path is None:
                    continue
                
                df = parse_player_positions(
                    dem_path, 
                    f"de_{map_name}",
                    granularity=granularity
                )
                all_positions.append(df)
    
    return pd.concat(all_positions, ignore_index=True)
```

### 2. Visualization: `src/visualization/position_heatmap.py`

```python
"""Create interactive position heatmaps overlaid on map images."""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# Map configurations
MAP_CONFIG = {
    'de_nuke': {
        'x_range': (-2005, 3346),
        'y_range': (-2480, 935),
        'image_path': 'assets/maps/nuke.jpg',
        'display_name': 'Nuke'
    },
    'de_dust2': {
        'x_range': (-2186, 1788),
        'y_range': (-1164, 3045),
        'image_path': 'assets/maps/dust2.jpg',
        'display_name': 'Dust 2'
    },
    'de_inferno': {
        'x_range': (-1690, 2700),
        'y_range': (-2000, 2000),
        'image_path': 'assets/maps/inferno.jpg',
        'display_name': 'Inferno'
    },
}


def create_position_heatmap(
    heatmap_data: pd.DataFrame,
    map_name: str,
    side: str = 'Both',
    granularity: int = 100,
    colorscale: str = 'Hot',
    opacity: float = 0.7,
    show_legend: bool = True
) -> go.Figure:
    """
    Create heatmap overlay on map image.
    
    Args:
        heatmap_data: DataFrame from parse_player_positions()
        map_name: Map identifier (e.g., 'de_nuke')
        side: 'CT', 'T', or 'Both'
        granularity: Grid size used in data
        colorscale: Plotly color scale name
        opacity: Heatmap opacity (0-1)
        show_legend: Whether to show color scale legend
        
    Returns:
        Plotly Figure object
    """
    if map_name not in MAP_CONFIG:
        raise ValueError(f"Unknown map: {map_name}. Available: {list(MAP_CONFIG.keys())}")
    
    config = MAP_CONFIG[map_name]
    
    # Filter data
    if side != 'Both':
        side_lower = 'ct' if side == 'CT' else 't'
        df = heatmap_data[(heatmap_data['map_name'] == map_name) & (heatmap_data['side'] == side_lower)]
    else:
        df = heatmap_data[heatmap_data['map_name'] == map_name]
    
    if df.empty:
        raise ValueError(f"No data for map {map_name}, side {side}")
    
    # Create pivot table for heatmap
    pivot = df.pivot_table(
        index='y_bin',
        columns='x_bin',
        values='count',
        aggfunc='sum',
        fill_value=0
    )
    
    x_bins = pivot.columns.values
    y_bins = pivot.index.values
    z_values = pivot.values.T
    
    # Load map image
    script_dir = Path(__file__).parent
    img_path = script_dir / config['image_path']
    
    if not img_path.exists():
        raise FileNotFoundError(f"Map image not found: {img_path}")
    
    img = Image.open(img_path)
    
    # Create figure
    fig = go.Figure()
    
    # Add map background
    fig.add_layout_image(
        dict(
            source=img,
            xref="x",
            yref="y",
            x=config['x_range'][0],
            y=config['y_range'][0],
            sizex=config['x_range'][1] - config['x_range'][0],
            sizey=config['y_range'][1] - config['y_range'][0],
            sizing="stretch",
            opacity=1.0,
            layer="below"
        )
    )
    
    # Add heatmap
    fig.add_trace(go.Densitymapbox(
        x=x_bins,
        y=y_bins,
        z=z_values,
        colorscale=colorscale,
        opacity=opacity,
        zmin=0,
        zmax=z_values.max() if z_values.max() > 0 else 1,
        showscale=show_legend,
        colorbar=dict(title="Position Count")
    ))
    
    # Configure axes
    fig.update_xaxes(
        range=config['x_range'],
        showgrid=False,
        zeroline=False,
        visible=False
    )
    fig.update_yaxes(
        range=config['y_range'],
        showgrid=False,
        zeroline=False,
        scaleanchor="x",
        visible=False
    )
    
    # Determine side label for title
    side_label = "All" if side == "Both" else side
    
    fig.update_layout(
        title=dict(
            text=f"Player Position Heatmap - {config['display_name']} ({side_label})<br><sub>Granularity: {granularity} units</sub>",
            x=0.5,
            y=0.98,
            font=dict(size=18, color="white")
        ),
        width=1000,
        height=800,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white", family="Arial, sans-serif"),
        margin=dict(t=80, b=20, l=20, r=20),
        hovermode="closest"
    )
    
    return fig


def create_comparative_heatmap(
    heatmap_data: pd.DataFrame,
    map_name: str,
    granularity: int = 100
) -> go.Figure:
    """
    Create side-by-side comparison of CT vs T positioning.
    
    Args:
        heatmap_data: DataFrame from parse_player_positions()
        map_name: Map identifier
        granularity: Grid size used in data
        
    Returns:
        Plotly Figure with two subplots
    """
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f"{MAP_CONFIG[map_name]['display_name']} - CT Side", 
                       f"{MAP_CONFIG[map_name]['display_name']} - T Side"),
        horizontal_spacing=0.1
    )
    
    for idx, side in enumerate(['CT', 'T']):
        sub_fig = create_position_heatmap(
            heatmap_data,
            map_name,
            side=side,
            granularity=granularity,
            colorscale='Blues' if side == 'CT' else 'Oranges',
            show_legend=(idx == 1)  # Only show legend on right
        )
        
        for trace in sub_fig.data:
            fig.add_trace(trace, row=1, col=idx+1)
    
    fig.update_layout(
        height=600,
        width=1200,
        title_text=f"CT vs T Positioning Comparison - {MAP_CONFIG[map_name]['display_name']} (Granularity: {granularity})",
        showlegend=False
    )
    
    return fig
```

## Usage Examples

### Basic Usage

```python
from pathlib import Path
from src.data_processing.parse_positions import parse_player_positions
from src.visualization.position_heatmap import create_position_heatmap

# Process a single demo
dem_path = Path("dem_files/Final/vitality-vs-faze-m1-nuke.dem")
positions = parse_player_positions(dem_path, "de_nuke", granularity=100)

# Create and display visualization
fig = create_position_heatmap(positions, "de_nuke", side="Both")
fig.show()

# Save to HTML
fig.write_html("heatmap_nuke.html")
```

### Multi-Granularity Analysis

```python
# Generate heatmaps at different granularities
for granularity in [25, 50, 100, 200]:
    positions = parse_player_positions(dem_path, "de_nuke", granularity=granularity)
    fig = create_position_heatmap(
        positions, 
        "de_nuke", 
        side="CT",
        granularity=granularity
    )
    fig.write_html(f"heatmap_nuke_ct_gran{granularity}.html")
```

### Comparative Analysis

```python
from src.visualization.position_heatmap import create_comparative_heatmap

# Compare CT vs T positioning
positions = parse_player_positions(dem_path, "de_nuke", granularity=75)
fig = create_comparative_heatmap(positions, "de_nuke")
fig.show()
```

### Tournament-Wide Analysis

```python
import json

# Load tournament data
with open("src/budapest_major.json") as f:
    tournament = json.load(f)

# Process all demos at medium granularity
all_positions = parse_tournament_positions(tournament, granularity=100)

# Create heatmaps for each map
for map_name in all_positions['map_name'].unique():
    fig = create_position_heatmap(
        all_positions,
        map_name,
        side="Both",
        granularity=100
    )
    fig.write_html(f"heatmap_{map_name.replace('de_', '')}_all.html")
```

## Map Images

### Required Map Images

Create a directory structure:
```
src/visualization/assets/maps/
├── nuke.jpg
├── dust2.jpg
├── inferno.jpg
├── mirage.jpg
├── ancient.jpg
├── vertigo.jpg
└── anubis.jpg
```

### Image Sources

1. **Extract from CS2 Game Files:**
   - Navigate to: `cs2/game/csgo/maps/workshop/`
   - Copy radar/minimap images
   - Rename to match map configuration keys

2. **Download from Community Resources:**
   - [CS2 Map Radar Images GitHub](https://github.com/pnxenopoulos/cs2-radar)
   - [CS:GO Map Overviews](https://github.com/SteamDatabase/GameTracking-CSGO/tree/master/game/csgo/maps)

3. **Create Custom Radars:**
   - Use in-game console: `cl_drawhud 0` then take screenshot
   - Process to remove HUD elements
   - Crop to standard radar view

### Image Requirements

- **Format:** JPG or PNG
- **Resolution:** Minimum 1024x1024 recommended
- **Orientation:** Standard CS2 radar orientation (T spawn at top/left, CT spawn at bottom/right for most maps)
- **Background:** Transparent or black preferred for overlay

## Performance Considerations

### Memory Optimization

For large datasets (many demos, fine granularity):

1. **Process in batches:**
   ```python
   # Process one match at a time
   for match in matches:
       positions = parse_player_positions(dem_path, map_name, granularity=100)
       # Save or visualize immediately
       positions.to_csv(f"positions_{match_id}.csv")
   ```

2. **Downsample before processing:**
   ```python
   # Only keep every Nth tick
   ticks = demo.ticks.to_pandas()
   ticks = ticks[::10]  # Keep every 10th tick (12.8 samples/second instead of 128)
   ```

3. **Use efficient data types:**
   ```python
   # Convert to categorical
   ticks['side'] = ticks['side'].astype('category')
   ```

### Processing Time Estimates

| Granularity | Players | Demo Length | Est. Processing Time |
|-------------|---------|-------------|---------------------|
| 25 | 10 | 30 min | 2-3 minutes |
| 50 | 10 | 30 min | 1-2 minutes |
| 100 | 10 | 30 min | 30-60 seconds |
| 200 | 10 | 30 min | 15-30 seconds |

*Based on modern CPU (Intel i7 / Ryzen 7 class)*

## Future Enhancements

1. **3D Heatmaps:** Use Z coordinate for elevation visualization
2. **Temporal Heatmaps:** Animate position changes over time
3. **Player-Specific Heatmaps:** Filter by individual players
4. **Team Comparison:** Overlay multiple teams' heatmaps with different colors
5. **Round-Specific Analysis:** Filter by round number or round outcome
6. **Automated Map Image Download:** Script to fetch map images automatically
7. **Interactive Filtering:** Dashboard controls for side, player, round range
8. **Density Contours:** Add contour lines to highlight concentration levels
9. **Path Visualization:** Show movement paths between positions
10. **Heatmap Differencing:** Compare heatmaps between halves or teams

## Dependencies

- `awpy>=0.10.0` - CS2 demo parsing
- `pandas>=2.0` - Data manipulation
- `plotly>=5.0` - Interactive visualizations
- `Pillow>=9.0` - Image handling
- `numpy>=1.24` - Numerical operations

## References

- [awpy Documentation](https://github.com/pnxenopoulos/awpy)
- [CS2 Demo Format](https://developer.valvesoftware.com/wiki/Source_Demo_Format)
- [Plotly Heatmaps](https://plotly.com/python/heatmaps/)
- [CS2 Map Coordinates](https://github.com/SteamDatabase/GameTracking-CSGO)
