# diverging_bar.py — Side-by-Side Diverging Bar Chart

## Purpose

Creates interactive Plotly diverging bar charts for comparing CS2 player or team performance metrics between Counter Terrorist (CT) and Terrorist (T) sides. Designed to visually highlight side-specific strengths or imbalances across multiple metrics on a normalized scale.

## Visualization Technique

**Diverging Bar Chart**

- **Y-axis**: Performance metrics (Kills, Assists, K/D Ratio, etc.) listed vertically
- **X-axis**: Normalized Performance (0-100%). Terrorist metrics are plotted on the negative (left) side, and Counter Terrorist metrics on the positive (right) side.
- **Bars**: Horizontal bars originating from a central zero axis.
- **Theme**: Clean white background with custom hover tooltips showing actual raw values rather than just the normalized percentages.

## Data Flow

```text
budapest_major_stats.csv + budapest_major_team_outcomes.csv 
→ filter by scope (game/map/player) → aggregate side metrics 
→ normalize against global maximums → Plotly Bar (relative barmode)
```

## Input Data

### Primary Source: `analysis_results/budapest_major_stats.csv`

Same schema as documented in `spider_player_performance.md`. Used for extracting performance statistics.

### Secondary Source: `analysis_results/budapest_major_team_outcomes.csv`

Used primarily to extract unique matches (`get_unique_games()`) by pairing teams against their opponents for a given map and stage.

## Data Processing

### Step 1: Filtering & Scope
Data is filtered based on the requested scope:
- **Game**: Specific match between two teams on a specific map and stage.
- **Map**: Aggregated statistics across all matches on a particular map.
- **Player**: Individual player statistics (can be scoped to a specific stage, game, or entire tournament).

### Step 2: Metric Aggregation
The `calculate_aggregated_metrics()` function splits data into CT and T subsets. For each side:
- **Rate Metrics**: Calculated by summing the total value and dividing by actual rounds played.
- **K/D Ratio & Headshot %**: Recalculated correctly from the raw sum of Kills, Deaths, and Headshots (rather than averaging existing averages).

### Step 3: Global Normalization
To ensure charts are visually comparable across different scopes, all metrics are normalized against global maximums found in the entire dataset (`get_global_max_norms()`). 
```python
res['norm'][metric] = (raw / GLOBAL_NORMS[metric]) * 100.0
```

### Step 4: Diverging Setup
For the Terrorist side, the normalized values are negated (`-t_data['norm'][m]`) before plotting. The Plotly layout uses `barmode='relative'` to place CT and T bars on opposite sides of the center zero axis. Custom tick text ensures the negative X-axis labels display as positive percentages (e.g., "-100" displays as "100%").

## Interesting Code Aspects

### Global Normalization Cache
```python
# Global cache for norms to speed up plot rendering
GLOBAL_NORMS = get_global_max_norms()
```
Normalization values are computed once at module load time to improve rendering performance, especially when generating multiple charts.

### Reversed Y-Axis Ordering
```python
# We will plot metrics on the Y axis in reverse order so they read top-to-bottom
y_metrics = list(reversed(METRICS))
```
By reversing the order of metrics before plotting, the chart displays the first metric in the `METRICS` list at the top, matching the user's natural reading order.

### Custom Hover Data Displaying Real Values
Since the physical bars represent normalized percentages, the hover templates are heavily customized to display the true, context-aware statistics rather than the scaled numbers.
```python
res['hover'][metric] = (
    f"K/D Ratio (Overall): {raw:.2f}<br>"
    f"Total Kills: {total_kills:.0f}<br>"
    f"Total Deaths: {total_deaths:.0f}<br>"
    f"Actual Rounds: {actual_rounds:.0f}"
)
```

## API

```python
get_game_charts(
    stage,        # Tournament stage
    map_name,     # Map name
    team1,        # First team
    team2         # Second team
) -> (go.Figure, go.Figure) # Returns two charts (Team 1 and Team 2)

get_map_chart(
    map_name      # Map name to aggregate
) -> go.Figure

get_player_chart(
    player_name,  # Player to analyze
    scope="Tournament", # "Tournament", "Stage", or "Game"
    stage=None,   # Required if scope is "Stage"
    game_label=None # Required if scope is "Game"
) -> go.Figure
```

## Limitations

- Normalization uses absolute global maximums. If the global maximum is an extreme outlier, it may visually compress the bars for average or below-average performances.
- Requires both `budapest_major_stats.csv` and `budapest_major_team_outcomes.csv` to function.
