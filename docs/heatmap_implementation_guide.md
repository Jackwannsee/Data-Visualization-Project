# AI Implementation Guide: CS2 Player Position Heatmap

## Objective

Create a heatmap visualization of player positions across CS2 maps, overlaid on radar images, with special handling for multi-level maps (Nuke, Train). This involves 3 new files and 1 modification:

1. **[NEW]** `src/data_processing/parse_positions.py` — extract & bin positions from demos
2. **[NEW]** `src/visualization/position_heatmap.py` — Plotly heatmap overlaid on radar image
3. **[NEW]** `src/dashboard/pages/4_🗺️_Position_Heatmap.py` — Streamlit dashboard page
4. **[MODIFY]** `src/dashboard/app.py` — add navigation link & card

---

## Critical Technical Constraints (Verified)

These are **verified facts** from running code against the actual project. Do NOT assume otherwise.

### awpy 2.0.2 API

The project uses **awpy 2.0.2**. DataFrames are **Polars**, converted via `.to_pandas()`.

```python
from awpy import Demo

demo = Demo(path=dem_path)
demo.parse()

# demo.ticks is a Polars DataFrame with these EXACT columns:
# health (f64), place (str), side (str), Y (f32), X (f32), Z (f32),
# tick (i32), steamid (u64), name (str), round_num (u32)

ticks = demo.ticks.to_pandas()
```

**Key column facts:**
- `place`: EXISTS. Values include `"TSpawn"`, `"CTSpawn"`, and map callout names
- `side`: Values are `"ct"`, `"t"`, or `null` (must filter out nulls)
- `round_num`: EXISTS as a direct column (no need to join with rounds)
- `health`: 0.0 for dead players, up to 100.0
- `demo.header['map_name']`: Returns `"de_nuke"`, `"de_dust2"`, etc.

**Performance:** ~1.5M rows per demo, ~5.5 seconds to parse one demo, 18 demos total.

### awpy MAP_DATA (Coordinate Metadata)

```python
from awpy.data.map_data import MAP_DATA
```

This provides the **exact** values needed for game-to-pixel coordinate conversion:

| Map | pos_x | pos_y | scale | lower_level_max_units |
|-----|-------|-------|-------|-----------------------|
| de_nuke | -3453 | 2887 | 7.0 | **-495.0** |
| de_dust2 | -2476 | 3239 | 4.4 | -1000000.0 |
| de_inferno | -2087 | 3870 | 4.9 | -1000000.0 |
| de_mirage | -3230 | 1713 | 5.0 | -1000000.0 |
| de_ancient | -2953 | 2164 | 5.0 | -1000000.0 |
| de_overpass | -4831 | 1781 | 5.2 | -1000000.0 |
| de_train | -2308 | 2078 | 4.082077 | **-50.0** |

- `lower_level_max_units` is the Z threshold: if `Z <= threshold`, the position is on the **lower level**
- Only Nuke (-495) and Train (-50) have meaningful thresholds; all others are -1000000 (no lower level)

### Coordinate Conversion Formula

All radar images are **1024x1024 pixels**. The conversion from game coordinates to pixel coordinates:

```python
pixel_x = (game_x - pos_x) / scale
pixel_y = (pos_y - game_y) / scale   # Y-axis is inverted (image: y increases downward)
```

For **Plotly** (where y=0 is at the bottom, y=1024 at top):
```python
plotly_x = (game_x - pos_x) / scale
plotly_y = 1024 - (pos_y - game_y) / scale
```

### Radar Images Available

Located at `src/visualization/assets/Maps/`:

| File | Map | Level |
|------|-----|-------|
| `de_nuke_radar_psd.png` | Nuke | Upper |
| `de_nuke_lower_radar_psd.png` | Nuke | Lower |
| `de_dust2_radar_psd.png` | Dust2 | — |
| `de_inferno_radar_psd.png` | Inferno | — |
| `de_mirage_radar_psd.png` | Mirage | — |
| `de_ancient_radar_psd.png` | Ancient | — |
| `de_overpass_radar_psd.png` | Overpass | — |
| `de_train_radar_psd.png` | Train | Upper |
| `de_train_lower_radar_psd.png` | Train | Lower |

All are 1024x1024 RGBA PNGs.

### Plotly Approach — Use `go.Heatmap`, NOT `go.Densitymapbox`

`go.Densitymapbox` requires lat/lon and renders on geographic tiles. CS2 game coordinates are arbitrary units. Use:

- `go.Heatmap` for the density overlay (Cartesian axes, supports `zsmooth`)
- `fig.add_layout_image()` for the radar image background
- Set NaN or 0 for empty cells (transparent in the colorscale)
- `zsmooth='best'` for smooth interpolation between grid cells

### Tournament Data

`src/budapest_major.json` structure:
```json
{
  "tournament": "StarLadder Budapest Major 2025",
  "stages": {
    "Quarterfinals": [{ "teams_played": [...], "maps_played": [...] }],
    "Semifinals": [...],
    "Final": [...]
  }
}
```

Map names in JSON are **display names**: `"Nuke"`, `"Dust2"`, `"Mirage"`, `"Inferno"`, `"Train"`, `"Ancient"`, `"Overpass"`.

### Nuke Z-Value Distribution (Verified)

From the Nuke demo: Z ranges from **-776 to +11**, mean **-425**.
- Upper level: Z > -495 (outdoor, A site, heaven, hell, ramp top)
- Lower level: Z <= -495 (B site, ramp bottom, vents, secret)

---

## File 1: `src/data_processing/parse_positions.py`

### Purpose
Parse all 18 demo files, extract player positions, filter, downsample, bin into a grid, and save as a CSV.

### Output
`analysis_results/budapest_major_positions.csv` with columns:
```
stages, map, teams, side, level, x_bin, y_bin, count
```

Example row: `Quarterfinals, Nuke, Team Spirit vs Team Falcons, ct, upper, -400, 200, 147`

### Implementation Steps

1. **Copy `find_dem_file` and supporting constants** from `src/data_processing/parse_demos.py` (lines 21-99). These include:
   - `STAGE_LABEL` dict
   - `TEAM_SLUG_TOKENS` dict
   - `_team_tokens()` function
   - `find_dem_file()` function
   - Path constants: `PROJECT_ROOT`, `DEM_DIR`, `JSON_PATH`

2. **Define constants:**
   ```python
   DOWNSAMPLE_FACTOR = 16   # 128 ticks/s -> 8 samples/s
   BASE_GRANULARITY = 25    # Finest bin size in game units
   OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_positions.csv"
   ```

3. **Import MAP_DATA:**
   ```python
   from awpy.data.map_data import MAP_DATA
   ```

4. **Position extraction function** `parse_positions_from_demo(dem_path, map_display_name, granularity=25)`:
   - Parse demo: `Demo(path=dem_path).parse()`
   - Convert to pandas: `demo.ticks.to_pandas()`
   - **Downsample**: `ticks = ticks.iloc[::DOWNSAMPLE_FACTOR]`
   - **Filter dead**: `ticks = ticks[ticks['health'] > 0]`
   - **Filter null side**: `ticks = ticks[ticks['side'].notna()]`
   - **Filter spawns**: `ticks = ticks[~ticks['place'].str.contains('Spawn', case=False, na=False)]`
   - **Determine map key**: Convert display name to `de_` format (e.g., `"Nuke"` -> `"de_nuke"`)
   - **Assign level**: Look up `MAP_DATA[map_key]['lower_level_max_units']`. Apply: `'lower' if Z <= threshold else 'upper'`
   - **Bin coordinates**: `x_bin = (X // granularity) * granularity`, same for y_bin. Cast to int.
   - **Aggregate**: `groupby(['side', 'level', 'x_bin', 'y_bin']).size().reset_index(name='count')`
   - Return the aggregated DataFrame

5. **Main function:**
   - Load `budapest_major.json`
   - Iterate `stages -> matches -> maps_played` (same pattern as `parse_demos.py` lines 310-320)
   - Call `find_dem_file(stage_key, map_num, map_name, teams)`
   - Call `parse_positions_from_demo()`
   - Add metadata columns: `stages` (from `STAGE_LABEL[stage_key]`), `map` (display name from JSON), `teams` (formatted as `"Team A vs Team B"`)
   - Concatenate all DataFrames
   - Save to CSV

6. **Add `if __name__ == "__main__": main()`**

### To run
```bash
pyenv activate 3.12.4/envs/InfoVis_Awpy
cd /home/jack/02.SS26/Data-Visualization-Project
python src/data_processing/parse_positions.py
```

Expected runtime: ~2 minutes for all 18 demos.

---

## File 2: `src/visualization/position_heatmap.py`

### Purpose
Load the pre-computed positions CSV, create a Plotly figure with the radar image as background and a heatmap overlay.

### Follow Existing Patterns
Mirror the structure of `src/visualization/headshot_scatter.py`:
- Same path resolution pattern (`SCRIPT_DIR`, relative paths to CSVs)
- Same config import pattern (importlib.util with fallback)
- Same function signature style: `create_...(filters, show=True) -> go.Figure`
- Same helper functions: `get_available_maps()`, `get_available_stages()`, etc.
- Same dark theme styling (`paper_bgcolor="#1a1d23"`, `#FAB200` accent, Inter font)

### MAP_CONFIG Dictionary

```python
MAP_CONFIG = {
    'Nuke': {
        'key': 'de_nuke',
        'has_levels': True,
        'images': {
            'upper': 'de_nuke_radar_psd.png',
            'lower': 'de_nuke_lower_radar_psd.png',
        }
    },
    'Dust2': {
        'key': 'de_dust2',
        'has_levels': False,
        'images': {'upper': 'de_dust2_radar_psd.png'}
    },
    'Inferno': {
        'key': 'de_inferno',
        'has_levels': False,
        'images': {'upper': 'de_inferno_radar_psd.png'}
    },
    'Mirage': {
        'key': 'de_mirage',
        'has_levels': False,
        'images': {'upper': 'de_mirage_radar_psd.png'}
    },
    'Ancient': {
        'key': 'de_ancient',
        'has_levels': False,
        'images': {'upper': 'de_ancient_radar_psd.png'}
    },
    'Overpass': {
        'key': 'de_overpass',
        'has_levels': False,
        'images': {'upper': 'de_overpass_radar_psd.png'}
    },
    'Train': {
        'key': 'de_train',
        'has_levels': True,
        'images': {
            'upper': 'de_train_radar_psd.png',
            'lower': 'de_train_lower_radar_psd.png',
        }
    },
}

IMG_SIZE = 1024
```

### Core Function: `create_position_heatmap()`

```python
def create_position_heatmap(
    map_name: str,           # Display name: "Nuke", "Dust2", etc.
    side: str = 'Both',      # "Both", "CT", "T"
    level: str = 'upper',    # "upper" or "lower"
    granularity: int = 50,   # Game units: 25, 50, 100, 200
    stage: str = None,       # "Quarterfinals", "Semifinals", "Final", "All", or None
    match: str = None,       # "Team A vs Team B", "All", or None
    opacity: float = 0.65,
    show: bool = True,
) -> go.Figure:
```

### Implementation Steps

1. **Load & filter CSV data:**
   - Read `budapest_major_positions.csv`
   - Filter by `map`, `side` (convert "CT"->"ct", "T"->"t"), `level`, `stage`, `match`
   - If `side == "Both"`, don't filter by side (aggregate both)

2. **Re-bin to requested granularity** (base CSV is at granularity 25):
   ```python
   if granularity > 25:
       df['x_bin'] = (df['x_bin'] // granularity) * granularity
       df['y_bin'] = (df['y_bin'] // granularity) * granularity
       df = df.groupby(['x_bin', 'y_bin']).agg({'count': 'sum'}).reset_index()
   ```

3. **Build the pixel grid:**
   ```python
   meta = MAP_DATA[config['key']]
   pos_x, pos_y, scale = meta['pos_x'], meta['pos_y'], meta['scale']

   pixel_cell = granularity / scale  # pixel size of each grid cell
   n_cells = max(1, int(IMG_SIZE / pixel_cell))
   grid = np.zeros((n_cells, n_cells), dtype=float)

   for _, row in df.iterrows():
       # Bin center in game coordinates
       cx = row['x_bin'] + granularity / 2
       cy = row['y_bin'] + granularity / 2
       # Convert to Plotly pixel coordinates
       px = (cx - pos_x) / scale
       py = IMG_SIZE - (pos_y - cy) / scale  # flip y for Plotly
       # Map to grid cell
       gx = int(px / pixel_cell)
       gy = int(py / pixel_cell)
       if 0 <= gx < n_cells and 0 <= gy < n_cells:
           grid[gy, gx] += row['count']
   ```

4. **Create Plotly figure with radar background:**
   ```python
   img = Image.open(img_path)
   fig = go.Figure()

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
   ```

5. **Add heatmap trace:**
   ```python
   x_centers = [(i + 0.5) * pixel_cell for i in range(n_cells)]
   y_centers = [(i + 0.5) * pixel_cell for i in range(n_cells)]

   fig.add_trace(go.Heatmap(
       x=x_centers,
       y=y_centers,
       z=grid,
       colorscale=colorscale,   # see colorscale section below
       zmin=0,
       zmax=np.max(grid) if np.max(grid) > 0 else 1,
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
   ```

6. **Configure axes (hide them, fix aspect ratio):**
   ```python
   fig.update_xaxes(range=[0, IMG_SIZE], visible=False, showgrid=False)
   fig.update_yaxes(range=[0, IMG_SIZE], visible=False, showgrid=False, scaleanchor="x")
   ```

7. **Style layout** (match existing dark theme):
   ```python
   fig.update_layout(
       title=dict(text=title_text, x=0.5, y=0.97, font=dict(size=18, color="#FAB200", family="Inter, sans-serif")),
       paper_bgcolor="#1a1d23",
       plot_bgcolor="rgba(0,0,0,0)",
       font=dict(color="#ccc", family="Inter, sans-serif"),
       margin=dict(t=70, b=20, l=20, r=20),
       width=900, height=900,
   )
   ```

### Colorscales

Use custom RGBA colorscales so zero-density areas are transparent (map shows through):

```python
# CT side — blues
CT_COLORSCALE = [
    [0.0,  'rgba(0,0,0,0)'],
    [0.01, 'rgba(0,70,160,0.2)'],
    [0.15, 'rgba(0,100,200,0.4)'],
    [0.4,  'rgba(0,140,220,0.55)'],
    [0.7,  'rgba(30,180,255,0.7)'],
    [1.0,  'rgba(120,215,255,0.85)'],
]

# T side — oranges/golds
T_COLORSCALE = [
    [0.0,  'rgba(0,0,0,0)'],
    [0.01, 'rgba(160,80,0,0.2)'],
    [0.15, 'rgba(200,120,0,0.4)'],
    [0.4,  'rgba(240,160,0,0.55)'],
    [0.7,  'rgba(250,190,0,0.7)'],
    [1.0,  'rgba(255,220,60,0.85)'],
]

# Both sides — hot/plasma
BOTH_COLORSCALE = [
    [0.0,  'rgba(0,0,0,0)'],
    [0.01, 'rgba(80,0,120,0.2)'],
    [0.15, 'rgba(160,0,80,0.35)'],
    [0.35, 'rgba(220,50,0,0.5)'],
    [0.6,  'rgba(250,140,0,0.65)'],
    [0.85, 'rgba(255,210,0,0.75)'],
    [1.0,  'rgba(255,255,80,0.9)'],
]
```

Select based on `side` parameter.

### Helper Functions

```python
def get_available_maps() -> list[str]:
    """Return list of map display names from the positions CSV."""

def get_available_stages() -> list[str]:
    """Return sorted list of tournament stages from the positions CSV."""

def get_available_matches(map_name: str = None) -> list[str]:
    """Return list of 'Team A vs Team B' strings, optionally filtered by map."""

def has_levels(map_name: str) -> bool:
    """Return whether the map has upper/lower levels."""
```

### `__main__` Block

Add argparse CLI like `headshot_scatter.py` for standalone testing:
```python
if __name__ == "__main__":
    # Parse args: --map, --side, --level, --granularity, --stage, --output
    # Generate and save to HTML
```

---

## File 3: `src/dashboard/pages/4_🗺️_Position_Heatmap.py`

### Purpose
Streamlit page with sidebar controls to interactively explore the heatmap.

### Follow the Pattern From `pages/3_🎯_Headshot_Analysis.py` Exactly

The structure should be:

1. **Path setup** (lines 11-18 of headshot page):
   ```python
   PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
   DASHBOARD_DIR = os.path.dirname(PAGES_DIR)
   SRC_DIR = os.path.dirname(DASHBOARD_DIR)
   VIZ_DIR = os.path.join(SRC_DIR, "visualization")
   if VIZ_DIR not in sys.path:
       sys.path.insert(0, VIZ_DIR)
   ```

2. **Import with reload guard** (lines 20-28):
   ```python
   import importlib
   if "position_heatmap" in sys.modules:
       importlib.reload(sys.modules["position_heatmap"])
   from position_heatmap import (
       create_position_heatmap,
       get_available_maps,
       get_available_stages,
       get_available_matches,
       has_levels,
   )
   ```

3. **Page config**: `st.set_page_config(page_title="Position Heatmap — CS2 Dashboard", page_icon="🗺️", layout="wide")`

4. **Custom CSS**: Copy the exact CSS block from the headshot page (`.page-header`, `.info-box`, `.sidebar-brand`, etc.)

5. **Sidebar controls:**
   - **Page navigation links** (same as all other pages — links to Home, Economy, Player Performance, Headshot, Position Heatmap)
   - **Map selector**: `st.selectbox("Map", options=cached_maps())`
   - **Side selector**: `st.selectbox("Side", options=["Both", "CT", "T"])`
   - **Level selector**: Only show if `has_levels(selected_map)` is True. `st.selectbox("Level", options=["upper", "lower"])`
   - **Granularity slider**: `st.select_slider("Detail Level", options=[25, 50, 100, 200], value=50)` with help text explaining trade-offs
   - **Stage filter**: `st.selectbox("Stage", options=["All"] + cached_stages())`
   - **Match filter**: `st.selectbox("Match", options=["All"] + cached_matches(selected_map))` — filtered by selected map

6. **Page header**: Gradient gold title "Position Heatmap" with description

7. **Scope info box**: Show active filters (map, side, level, granularity, stage, match)

8. **Chart rendering:**
   ```python
   try:
       fig = create_position_heatmap(
           map_name=selected_map,
           side=selected_side,
           level=selected_level,
           granularity=selected_granularity,
           stage=selected_stage if selected_stage != "All" else None,
           match=selected_match if selected_match != "All" else None,
           show=False,
       )
       fig.update_layout(
           paper_bgcolor="rgba(0,0,0,0)",
           plot_bgcolor="rgba(0,0,0,0)",
           font_color="#ccc",
           title_font_color="#FAB200",
       )
       st.plotly_chart(fig, use_container_width=True, key="position_heatmap_chart")
   except ValueError as e:
       st.error(f"⚠️ {e}")
   except Exception as e:
       st.error(f"Unexpected error: {e}")
   ```

---

## File 4: Modify `src/dashboard/app.py`

### Two Changes

#### 1. Add sidebar page link (around line 169, after the Headshot link)
```python
st.page_link("pages/4_🗺️_Position_Heatmap.py", label="Position Heatmap", icon="🗺️")
```

#### 2. Add navigation card (after the existing 3-column card section, around line 360)

Change the existing 3-column layout to 4 columns (or add a new row below). The simplest approach is adding a second row:

```python
# After the existing col1, col2, col3 block, add:
st.markdown("")  # spacing
col4, col5, col6 = st.columns(3, gap="medium")

with col4:
    st.markdown(
        """
        <a href="/Position_Heatmap" target="_self" class="nav-card-link">
            <div class="nav-card">
                <h3>Position Heatmap</h3>
                <p>
                    Visualize player positioning patterns overlaid on map radar images.
                    Compare CT vs T positioning, explore Nuke's upper and lower levels,
                    and adjust detail granularity.
                </p>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )
```

---

## Running Order

1. **Create** `src/data_processing/parse_positions.py`
2. **Run it** to generate `analysis_results/budapest_major_positions.csv`:
   ```bash
   pyenv activate 3.12.4/envs/InfoVis_Awpy
   cd /home/jack/02.SS26/Data-Visualization-Project
   python src/data_processing/parse_positions.py
   ```
   Expected: ~2 minutes, prints progress per demo file.

3. **Create** `src/visualization/position_heatmap.py`
4. **Test standalone**:
   ```bash
   python src/visualization/position_heatmap.py --map Nuke --side Both --level upper --granularity 50
   ```
   Should produce an HTML file.

5. **Create** `src/dashboard/pages/4_🗺️_Position_Heatmap.py`
6. **Modify** `src/dashboard/app.py`
7. **Test dashboard**:
   ```bash
   streamlit run src/dashboard/app.py
   ```
   Navigate to the Position Heatmap page and verify:
   - Map image renders correctly as background
   - Heatmap positions align with map features (corridors, bombsites)
   - Nuke upper shows outdoor/A site; lower shows B site/ramp
   - CT and T heatmaps show different positioning patterns
   - Granularity slider changes detail level
   - Stage/match filters work

---

## Common Pitfalls to Avoid

1. **Do NOT use `go.Densitymapbox`** — it requires lat/lon coordinates and will not work with game units
2. **Do NOT hardcode Z-filter ranges** — use `MAP_DATA[map_key]['lower_level_max_units']` from awpy
3. **Do NOT forget to flip the Y-axis** — game Y increases upward, image Y increases downward. The formula `plotly_y = 1024 - (pos_y - game_y) / scale` handles this
4. **Do NOT forget to filter `side == null`** — the ticks data contains null side values that must be excluded
5. **Do NOT forget `health > 0`** — dead players still have tick entries at their death position
6. **Do NOT assume the `place` column is absent** — it EXISTS in awpy 2.0.2 with values like `"TSpawn"`, `"CTSpawn"`
7. **The CSV map names are display names** (e.g., `"Nuke"`, not `"de_nuke"`) — convert to `de_` format only when looking up `MAP_DATA`
8. **The layout_image needs `xanchor="left", yanchor="top"`** with `x=0, y=1024` to position correctly in Plotly's coordinate system
