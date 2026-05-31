# headshot_scatter.py — Headshot Percentage vs KPR/Kills Scatter Plot

## Purpose

Creates an interactive Plotly scatter plot analyzing the relationship between player headshot percentage and offensive performance (Kills Per Round or Total Kills). Designed to reveal correlations, outliers, and team patterns in a tournament-wide or filtered context.

## Visualization Technique

**Bubble Scatter Plot with Trendline**

- **X-axis**: Kills Per Round (KPR) or Total Kills (user-selectable)
- **Y-axis**: Headshot Percentage (%)
- **Markers**: Players as circular points, colored by team
- **Trendline**: Linear regression line with R² statistic
- **Reference lines**: Tournament-wide averages for both axes
- **Theme**: Premium dark theme (#1a1d23 background)

## Data Flow

```
budapest_major_stats.csv + budapest_major_match_details.csv 
→ merge on stage/map/team/side → aggregate per player → calculate KPR/Headshot % 
→ apply trendline regression → Plotly Scatter
```

## Input Data

### Primary Source: `analysis_results/budapest_major_stats.csv`
Same schema as documented in `spider_player_performance.md`.

### Secondary Source: `analysis_results/budapest_major_match_details.csv`

**Schema:**
| Column | Type | Description |
|--------|------|-------------|
| `stages` | string | Tournament stage |
| `map` | string | Map name |
| `team` | string | Team name |
| `side` | string | Side played |
| `rounds_played` | int | Number of rounds played in this specific context |

**Purpose**: Provides accurate round counts for aggregation, as the stats file contains pre-aggregated data that needs proper weighting.

## Data Processing

### Step 1: Data Merging
```python
merged = pd.merge(
    df_stats,
    df_details[['stages', 'map', 'team', 'side', 'rounds_played']],
    on=['stages', 'map', 'team', 'side'],
    how='inner'
)
```
Joins player statistics with precise round counts to ensure accurate per-round calculations.

### Step 2: Filtering
Applies user-specified filters:
- `side`: Counter Terrorist, Terrorist, or Both
- `stage`: Tournament stage (Final, Semifinals, etc.)
- `map_name`: Specific map

### Step 3: Aggregation
```python
player_stats = merged.groupby(['player_name', 'team']).agg(
    total_kills=('Kills', 'sum'),
    total_headshots=('Headshots', 'sum'),
    total_rounds=('rounds_played', 'sum')
).reset_index()
```
Aggregates statistics **per player across all matching contexts**, using the actual rounds played from the details file rather than the pre-aggregated "Rounds Played" from stats.

### Step 4: Metric Calculation
```python
player_stats['KPR'] = player_stats.apply(
    lambda r: r['total_kills'] / r['total_rounds'] if r['total_rounds'] > 0 else 0,
    axis=1
)
player_stats['Headshot %'] = player_stats.apply(
    lambda r: (r['total_headshots'] / r['total_kills'] * 100) if r['total_kills'] > 0 else 0,
    axis=1
).round(2)
```
- **KPR**: Total kills divided by total rounds played
- **Headshot %**: (Total headshots / Total kills) × 100, recalculated from raw counts

### Step 5: Linear Regression Trendline
```python
# Calculate regression
m, c = np.polyfit(x_vals, y_vals, 1)

# R-squared calculation
y_pred = m * x_vals + c
ss_res = np.sum((y_vals - y_pred) ** 2)
ss_tot = np.sum((y_vals - np.mean(y_vals)) ** 2)
r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
```
Computes the best-fit line and correlation strength (R²) to quantify the relationship between the selected X metric and headshot percentage.

### Step 6: Tournament Averages
```python
avg_x = player_stats[x_col].mean()
avg_y = player_stats['Headshot %'].mean()
```
Calculates mean values across all displayed players for reference lines.

## Interesting Code Aspects

### Dynamic Hover Text with Emojis
```python
hover_html = (
    f"<b>{row['player_name']}</b> ({row['team']})<br><br>"
    f"🎯 Headshot %: <b>{row['Headshot %']:.1f}%</b><br>"
    f"⚔️ Kills Per Round (KPR): <b>{row['KPR']:.3f}</b><br>"
    f"💀 Total Kills: {row['total_kills']:.0f}<br>"
    f"🔴 Total Headshots: {row['total_headshots']:.0f}<br>"
    f"⏳ Rounds Played: {row['total_rounds']:.0f}"
)
```
Rich HTML hover text with emoji icons for enhanced readability and visual appeal.

### Team-Based Coloring
```python
unique_teams = sorted(player_stats['team'].unique())
for idx, team in enumerate(unique_teams):
    team_df = player_stats[player_stats['team'] == team]
    color = TEAM_COLORS.get(team, DEFAULT_COLORS[idx % len(DEFAULT_COLORS)])
```
Uses a centralized color palette from `config.py` with team-specific colors:

| Team | Color | Hex Code |
|------|-------|----------|
| FaZe Clan | Orange | #E69F00 |
| Team Vitality | Sky Blue | #56B4E9 |
| Natus Vincere | Yellow | #F0E442 |
| Team Spirit | Blue | #0072B2 |
| MOUZ | Vermillion | #D55E00 |
| FURIA Esports | Bluish Green | #009E73 |
| Team Falcons | Reddish Purple | #CC79A7 |
| The MongolZ | Black | #000000 |

Fallback to `DEFAULT_COLORS` (Okabe-Ito colorblind-friendly palette) for unknown teams.

### Marker Styling
```python
marker=dict(
    size=12,
    color=color,
    line=dict(width=1.5, color='rgba(255,255,255,0.8)')
)
```
- Fixed size of 12px
- Team color fill
- White border with 80% opacity for contrast against dark background

### Premium Dark Theme
```python
fig.update_layout(
    paper_bgcolor="#1a1d23",
    plot_bgcolor="#1a1d23",
    font=dict(color="#ccc", family="Inter, sans-serif"),
    ...
)
```
Complete dark theme with:
- Background: #1a1d23 (very dark blue-gray)
- Text: #ccc (light gray)
- Grid lines: rgba(42, 45, 53, 0.4) (semi-transparent dark gray)
- Accent color: #FAB200 (gold) for title
- Inter font family for modern look

### Dynamic Title Generation
```python
filters = []
if stage and stage != "All": filters.append(stage)
if map_name and map_name != "All": filters.append(map_name)
if side and side != "Both": filters.append(side)
subtitle = f" ({', '.join(filters)})" if filters else ""
title_text = f"Player Headshot % vs. {x_label}{subtitle}"
```
Automatically constructs descriptive titles based on active filters.

### Reference Lines
Horizontal and vertical dashed lines show tournament averages:
- **Horizontal**: Average Headshot % with annotation at bottom left
- **Vertical**: Average KPR/Kills with annotation at top right
- Color: rgba(255,255,255,0.25) (semi-transparent white)
- Line style: dotted

## API

```python
create_headshot_scatter(
    side='Both',           # "Both", "Counter Terrorist", "Terrorist"
    stage=None,            # Stage filter or None for all
    map_name=None,         # Map filter or None for all
    x_metric='KPR',        # "KPR" or "Kills"
    show=True              # Show figure or return it
) -> go.Figure
```

## CLI Usage

```bash
# Basic usage
python src/visualization/headshot_scatter.py

# With filters
python src/visualization/headshot_scatter.py \
    --side "Counter Terrorist" \
    --stage "Final" \
    --map "Dust2" \
    --metric "Kills"

# Output to file
python src/visualization/headshot_scatter.py \
    --output "custom_headshot_scatter.html"
```

## Interpretation Guide

### Understanding the Correlation
- **Positive slope (R² > 0)**: Higher KPR/Total Kills correlates with higher headshot percentage
  - Interpretation: More accurate players (higher HS%) tend to get more kills
- **Negative slope (R² > 0)**: Higher KPR/Total Kills correlates with lower headshot percentage
  - Interpretation: Players with more kills may be spraying more (lower HS%)
- **R² near 0**: No strong correlation between the metrics

### Typical Patterns
1. **Top-right quadrant**: Elite players - high KPR and high HS%
2. **Top-left quadrant**: Accurate but low-impact players - high HS% but low KPR
3. **Bottom-right quadrant**: High volume, lower accuracy - high KPR but lower HS%
4. **Bottom-left quadrant**: Supporting players - lower in both metrics

### Team Clustering
- Players from the same team share the same color
- Click team name in legend to show/hide all players from that team
- Look for team patterns: do certain teams have consistently higher HS%?

## Statistical Notes

### R-squared (R²) Interpretation
| R² Value | Correlation Strength |
|----------|---------------------|
| 0.00 - 0.19 | Very weak or no correlation |
| 0.20 - 0.39 | Weak correlation |
| 0.40 - 0.59 | Moderate correlation |
| 0.60 - 0.79 | Strong correlation |
| 0.80 - 1.00 | Very strong correlation |

### KPR vs Total Kills
- **KPR**: Normalizes kills by rounds played, better for comparing players with different playtime
- **Total Kills**: Raw kill count, can be biased by more rounds played
- KPR is generally preferred for fair comparisons

## Limitations

- Only shows correlation, not causation
- Does not account for opponent strength
- Team coloring may be hard to distinguish for users with color vision deficiencies (though Okabe-Ito palette is colorblind-friendly)
- Small sample sizes (few players) may result in unreliable R² values
- No statistical significance testing included
