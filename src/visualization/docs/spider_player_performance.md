# spider_player_performance.py — Player Performance Spider/Radar Chart

## Purpose

Creates interactive Plotly radar (spider) charts for comparing CS2 player performance across multiple metrics. Designed for 1-2 player comparisons with support for side-specific analysis (CT, T, or Both) and flexible scoping (all data, specific stage, specific map, or stage+map combination).

## Visualization Technique

**Radar Chart (Spider Chart)** - A circular chart that displays multivariate data as a polygon, with each axis representing a different metric. This allows for:
- Quick visual comparison of player performance profiles
- Identification of strengths and weaknesses across multiple dimensions
- Easy spotting of performance imbalances

The chart uses Plotly's `go.Scatterpolar` with the following features:
- Polar coordinates (r, theta) where r = normalized metric value (0-100 scale)
- Multiple traces for different players and/or sides
- Semi-transparent fill areas (for single-player, single-side visualizations)
- Custom hover text showing raw metric values, totals, and context

## Data Flow

```
budapest_major_stats.csv → filter → aggregate → calculate derived metrics → normalize → Plotly Scatterpolar
```

## Input Data

**Source:** `analysis_results/budapest_major_stats.csv`

### Primary Data Schema:
| Column | Type | Description |
|--------|------|-------------|
| `stages` | string | Tournament stage (Final, Semifinals, Quarterfinals) |
| `map` | string | Map name (Dust2, Nuke, Mirage, etc.) |
| `team` | string | Team name |
| `player_name` | string | Player nickname |
| `player_steamid` | string | Steam ID for player identification |
| `side` | string | Side played (Counter Terrorist, Terrorist, Both) |
| `Kills` | float | Total kills |
| `Assists` | float | Total assists |
| `Deaths` | float | Total deaths |
| `Smokes Thrown` | float | Total smoke grenades thrown |
| `Molotovs Thrown` | float | Total molotovs/incendiary grenades thrown |
| `Grenades` | float | Total HE grenades thrown |
| `Headshots` | float | Total headshot kills |
| `Rounds Played` | float | Total rounds played |
| `Headshot %` | float | Pre-calculated headshot percentage |

## Data Processing

### Step 1: Filtering
Data is filtered based on user parameters:
- Player names (1-2 players supported)
- Side (Counter Terrorist, Terrorist, or Both)
- Scope (all, stage, map, stage_map) with corresponding stage/map filters

### Step 2: Derived Metric Calculation
The `calculate_metrics()` function computes several derived metrics:

| Derived Metric | Formula | Notes |
|---------------|---------|-------|
| **K/D Ratio** | `total_kills / total_deaths` | Returns 0 if no deaths |
| **Headshot %** | `(total_headshots / total_kills) * 100` | Calculated from raw counts, not from the CSV column |
| **Deaths** | `-(total_deaths / total_rounds)` | Negated for inversion (lower deaths = better, displayed as higher value) |
| **Other metrics** | `sum(metric) / total_rounds` | Per-round averages |

### Step 3: Normalization
All metric values are normalized to a 0-100 scale for consistent radar chart display:
- Normalization values are computed from the **entire dataset** (not just filtered data) for consistency
- For Deaths: Special inversion logic ensures lower death rates appear as higher values
- Formula: `(metric_value / max_possible_value) * 100`

### Step 4: Polygon Construction
- Values are closed by appending the first value at the end
- Theta (angle) positions correspond to metric names
- Multiple traces are created for each player-side combination

## Interesting Code Aspects

### Dynamic Normalization
```python
# Normalization values come from ALL data, not filtered subset
kd_ratios = df_all.apply(
    lambda row: row['Kills'] / row['Deaths'] if row['Deaths'] > 0 else 0.0, axis=1
)
norm_values[metric] = kd_ratios.max()
```
This ensures consistent scaling across different filter combinations, making charts comparable.

### Death Inversion Logic
```python
# For Deaths metric: lower is better, so we invert
if metric == "Deaths":
    actual_val = -metric_values[metric]  # metric_values has negative value
    normalized_values.append((1.0 - (actual_val / max_val)) * 100.0)
```
Deaths are stored as negative per-round rates, then inverted during normalization to appear as "good" (high) values on the radar chart.

### Multi-Trace Handling
- **Single player, multiple sides**: Each side gets its own trace with side-specific colors (CT blue, T gold)
- **Multiple players**: Each player gets their own color from `PLAYER_COLORS` palette
- **Fill strategy**: `fill='none'` for multiple traces to prevent hover interference; `fill='toself'` for single trace

### Color System
| Element | Color Source |
|---------|--------------|
| CT Side | `CT_COLOR` (#0091D4 - blue) from config.py |
| T Side | `T_COLOR` (#FAB200 - gold) from config.py |
| Both Sides | `BOTH_COLOR` (#AFAFAF - gray) from config.py |
| Player 1 | `PLAYER_COLORS[0]` (#1f77b4 - blue) |
| Player 2 | `PLAYER_COLORS[1]` (#ff7f0e - orange) |

### Custom Hover Text
Each point on the radar chart has rich hover information:
```
K/D Ratio: 1.45
Total Kills: 145
Total Deaths: 100
```
Contextual information varies by metric type (K/D Ratio shows kills/deaths, Headshot % shows headshots/kills, etc.)

### Segmented Display
- **Radial axis**: Custom tick values at 0, 25, 50, 75, 100% with 10% padding
- **Angular axis**: Metric names as category labels
- **Title**: Dynamically generated with player names, stage, map, and side information

## API

```python
create_spider_chart(
    player_names=None,      # List of player names, default: ["ZywOo"]
    metrics=None,           # List of metrics, default: standard CS2 metrics
    side=None,              # "Counter Terrorist", "Terrorist", "Both", or None
    stage=None,             # Stage name (required if scope="stage")
    map_name=None,          # Map name (required if scope="map")
    scope="all",            # "all", "stage", "map", "stage_map"
    show=True               # Show figure or return it
) -> go.Figure | None
```

### Available Helper Functions
```python
get_available_columns()    # Returns list of metric columns
get_available_players()    # Returns list of player names
get_available_stages()     # Returns list of stages
get_available_maps()       # Returns list of maps
get_scope_options()        # Returns dict of all scope options
```

## CLI Usage

```bash
# Single player, all data
python src/visualization/spider_player_performance.py

# Two players comparison
python -c "from spider_player_performance import create_spider_chart; \
create_spider_chart(['ZywOo', 'broky'], scope='stage', stage='Final')"
```

## Example Outputs

1. **Single player analysis**: Compare ZywOo's performance on CT vs T side
2. **Duel comparison**: Compare two star players head-to-head
3. **Stage-specific**: Analyze performance in Final vs earlier stages
4. **Metric-focused**: Custom metric selection (e.g., focus on utility usage)

## Limitations

- Maximum 2 players can be compared simultaneously (design choice for readability)
- Metrics must be present in the dataset or be derived metrics (K/D Ratio, Headshot %)
- Normalization uses global maxima, which may make some charts appear compressed if filtered data has much lower values
