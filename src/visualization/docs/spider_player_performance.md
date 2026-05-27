# Spider Player Performance Visualization

## Overview
Generates interactive Plotly spider/radar charts for CS2 player performance comparison.

## Input Data
- **Source:** `../../analysis_results/budapest_major_stats.csv`
- **Required columns:** `player_name`, `stages`, `map`, `side`, `Kills`, `Deaths`, `Assists`, `Smokes Thrown`, `Moloveds Thrown`, `Grenades`

## Output
- Interactive Plotly radar chart (`.show()` or returns `go.Figure`)

## Customization Options

| Parameter | Description | Example |
|-----------|-------------|---------|
| `player_names` | 1-2 players to compare | `["ZywOo", "broky"]` |
| `metrics` | Metrics to display | `["Kills", "K/D Ratio", "Assists"]` |
| `side` | Filter by side | `"Counter Terrorist"`, `"Terrorist"`, `"Both"` |
| `scope` | Data scope | `"all"`, `"stage"`, `"map"`, `"stage_map"` |
| `stage` | Filter by stage (requires scope=stage or stage_map) | `"Final"`, `"Quarterfinals"`, `"Semifinals"` |
| `map_name` | Filter by map (requires scope=map or stage_map) | `"Ancient"`, `"Dust2"`, `"Inferno"`, `"Mirage"`, `"Nuke"`, `"Overpass"`, `"Train"` |

## Default Metrics
`Kills`, `Assists`, `K/D Ratio`, `Smokes Thrown`, `Moloveds Thrown`, `Grenades`
