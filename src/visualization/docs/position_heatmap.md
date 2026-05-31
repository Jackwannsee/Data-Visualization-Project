# position_heatmap.py — Position Heatmap Visualization

## Purpose

Renders interactive Plotly heatmaps of player positions overlaid on 1024x1024 radar images.

## Data Flow

```
budapest_major_positions.csv -> filter -> re-bin -> game coords -> pixel grid -> Plotly figure
```

## Coordinate Conversion

Game coordinates are converted to pixel coordinates using `MAP_DATA` metadata:

```
pixel_x = (game_x - pos_x) / scale
pixel_y = 1024 - (pos_y - game_y) / scale   # Y-axis flipped for Plotly
```

Each radar image is 1024x1024 pixels. The `scale` factor varies per map (4.0-7.0).

## Rendering Pipeline

1. **Load & filter** CSV by map, side, level, stage, match
2. **Re-bin** to requested granularity (25/50/100/200) by coarsening the base 25-unit grid
3. **Build pixel grid** - iterate binned positions, convert to pixel coordinates, accumulate counts into a 2D numpy array
4. **Add radar image** - `fig.add_layout_image()` with the appropriate radar PNG (upper/lower for Nuke/Train)
5. **Add heatmap** - `go.Heatmap` with `zsmooth='best'` for interpolation
6. **Style** - dark theme, hidden axes, 1:1 aspect ratio

## Z-Value (Heatmap Density)

The `z` values in the heatmap represent **position density** - the number of downsampled tick samples accumulated in each grid cell.

- `z = 0` - no player presence (transparent, radar image shows through)
- `z = max` - highest concentration of tick samples across the grid

Each cell's `z` is computed by summing `row['count']` from the CSV, where `count` is the number of tick records that fell into that (x_bin, y_bin) during processing. Higher `z` = more player presence at that location across all filtered demos.

The colorbar is labeled "Position Density" and the scale is normalized 0->max across the grid.

## Colorscales

Three side-specific RGBA colorscales with transparent zero-density areas:

| Side | Colorscale |
|------|-----------|
| CT | Blues (`rgba(0,70,160,...)` -> `rgba(120,215,255,...)`) |
| T | Oranges/Golds (`rgba(160,80,0,...)` -> `rgba(255,220,60,...)`) |
| Both | Hot/Plasma (`rgba(80,0,120,...)` -> `rgba(255,255,80,...)`) |

## Map Configuration

`MAP_CONFIG` maps display names to radar image filenames and level support:

| Map | Levels | Radar Images |
|-----|--------|-------------|
| Nuke | upper/lower | `de_nuke_radar_psd.png`, `de_nuke_lower_radar_psd.png` |
| Train | upper/lower | `de_train_radar_psd.png`, `de_train_lower_radar_psd.png` |
| Dust2, Inferno, Mirage, Ancient, Overpass | single | `de_<map>_radar_psd.png` |

## API

```python
create_position_heatmap(
    map_name="Nuke",       # Display name
    side="Both",           # "Both", "CT", "T"
    level="upper",         # "upper" or "lower"
    granularity=50,        # 25, 50, 100, 200
    stage=None,            # "Final", "Semifinals", "Quarterfinals", or None
    match=None,            # "Team A vs Team B" or None
    opacity=0.65,          # Heatmap opacity
    show=True,             # Show figure or return
) -> go.Figure
```

## CLI

```bash
python src/visualization/position_heatmap.py --map Nuke --side CT --level upper --granularity 50
```

Outputs `position_heatmap.html` in the visualization directory.
