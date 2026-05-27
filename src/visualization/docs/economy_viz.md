# Economy Visualization

## Overview

`economy_viz.py` generates an interactive **combined economy line plot** comparing two teams' total round-by-round cash across a single map. It segments line colors by round outcomes (win/loss) and marks each round with CT/T side indicators.

## Input Data

| File | Key Columns |
|------|-------------|
| `budapest_major_economy.csv` | `stage`, `map`, `team`, `opponent`, `r_N_cash` (per-round economy) |
| `budapest_major_team_outcomes.csv` | `stage`, `map`, `team`, `CT_rounds`, `T_rounds`, `r_N_outcome` |

## Output

Interactive Plotly chart showing:
- **Two lines** (team vs opponent) with color-coded segments: green = round won, red = round lost
- **Markers** labeled "CT" or "T" indicating side per round
- **Hover tooltips** with economy, side, and result per round
- **Vertical divider** at halftime (round 12.5)

## Customization Options

| Parameter | Description | Example |
|-----------|-------------|---------|
| `stage` | Match stage to filter | `"Final"` |
| `map_name` | Map name to filter | `"Dust2"` |
| `team` | Team to focus on (opponent auto-detected) | `"FaZe Clan"` |

## Colors (configurable via `config.py`)

| Variable | Meaning |
|----------|---------|
| `CT_COLOR` | CT side marker |
| `T_COLOR` | T side marker |
| `BOTH_COLOR` | Unknown side |
| `WIN_COLOR` | Round won segment |
| `LOSS_COLOR` | Round lost segment |
| `LINE_ALPHA` | Line transparency |
