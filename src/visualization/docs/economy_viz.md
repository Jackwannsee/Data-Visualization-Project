# economy_viz.py — Team Economy Timeline Visualization

## Purpose

Creates interactive Plotly line plots showing team economy progression across rounds in CS2 matches. Displays both teams' economy simultaneously with CT/T side indicators, round outcomes (win/loss), and match phase markers (half-time, overtime).

## Visualization Technique

**Multi-Series Line Chart with Segmented Data**

- **Line segments**: Economy values connected as line segments, broken at match phase boundaries
- **Marker points**: Individual round markers with CT/T side labels and color-coded by outcome
- **Dual team display**: Both teams' economies on the same axes for direct comparison
- **Phase separators**: Vertical dashed lines at round 12.5 (half-time), 24.5 (OT1 start), 30.5 (OT2 start)

## Data Flow

```
budapest_major_economy.csv + budapest_major_team_outcomes.csv 
→ parse round ranges → extract economy values → segment by match phase → Plotly Scatter/Line
```

## Input Data

### Primary Source: `analysis_results/budapest_major_economy.csv`

**Schema:**
| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage (Final, Semifinals, Quarterfinals) |
| `map` | string | Map name |
| `team` | string | Team name |
| `player_name` | string | Player name (repeated for all team members) |
| `player_steam_id` | string | Steam ID |
| `opponent` | string | Opponent team name |
| `r_1_cash` to `r_36_cash` | float | Team's total cash at the start of each round |

**Note:** Economy data is stored per-round as column names (`r_1_cash`, `r_2_cash`, etc.) with cash amounts as values. Empty cells indicate the round was not played.

### Secondary Source: `analysis_results/budapest_major_team_outcomes.csv`

**Schema:**
| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage |
| `map` | string | Map name |
| `team` | string | Team name |
| `CT_rounds` | string | Round ranges when team was CT (e.g., "1-12, 25-27") |
| `T_rounds` | string | Round ranges when team was T (e.g., "13-24, 28-30") |
| `r_1_outcome` to `r_36_outcome` | bool | True if team won the round, False if lost |

## Data Processing

### Step 1: Round Range Parsing
The `parse_round_range()` function converts string representations of round ranges into integer lists:
```python
"1-12, 28-30" → [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 28, 29, 30]
```

### Step 2: Side Determination
The `get_side_for_round()` function determines which side a team was on for a specific round:
```python
def get_side_for_round(ct_rounds_str, t_rounds_str, round_num):
    ct_rounds = parse_round_range(ct_rounds_str)
    t_rounds = parse_round_range(t_rounds_str)
    if round_num in ct_rounds: return 'CT'
    elif round_num in t_rounds: return 'T'
    return None
```

### Step 3: Economy Extraction
- Column names are parsed to extract round numbers: `r_1_cash` → round 1
- Cash values are summed across all players on a team for each round
- Only rounds with data for either team are included

### Step 4: Match Phase Segmentation
To prevent misleading connections across match phases, rounds are divided into segments:

| Segment | Rounds | Phase |
|---------|--------|-------|
| 1 | 1-12 | Regulation First Half (CT side for team1) |
| 2 | 13-24 | Regulation Second Half (T side for team1) |
| 3 | 25-30 | Overtime 1 |
| 4 | 31-36 | Overtime 2 |

Lines are drawn separately for each segment to avoid connecting round 12 to round 13 (which crosses the halftime side swap).

### Step 5: Outcome Color Coding
Marker colors encode both side and win/loss information:
- **Win + CT side**: CT_COLOR (#0091D4 - blue)
- **Win + T side**: T_COLOR (#FAB200 - gold)
- **Loss**: BOTH_COLOR (#AFAFAF - gray), regardless of side

## Interesting Code Aspects

### Dynamic Column Discovery
```python
round_cols = [col for col in economy_df.columns if col.startswith('r_') and col.endswith('_cash')]
round_cols_sorted = sorted(round_cols, key=lambda x: int(x.split('_')[1]))
```
Automatically discovers all round columns, making the code adaptable to matches of any length.

### Segment-Based Line Drawing
```python
segments = []
# Segment 1: Rounds 1-12
s1 = [idx for idx, r in enumerate(rounds) if r <= 12]
if s1: segments.append(s1)
# Segment 2: Rounds 13-24
s2 = [idx for idx, r in enumerate(rounds) if 13 <= r <= 24]
if s2: segments.append(s2)
# ... etc.

for seg in segments:
    fig.add_trace(go.Scatter(
        x=[rounds[idx] for idx in seg],
        y=[team_cash[idx] for idx in seg],
        mode='lines',
        ...
    ))
```
Prevents visual distortion from connecting across halftime when sides switch.

### Rich Marker Information
Each marker displays:
- **Text label**: "CT" or "T" (side played)
- **Color**: Win/loss + side encoded
- **Hover text**: Team name, round number, economy value, side, and outcome

```python
team_marker_hover.append(
    f'{team}<br>Round: {r}<br>Economy: ${team_cash[i]:,.0f}<br>'
    f'Side: {side}<br>Result: {"Won" if won else "Lost"}'
)
```

### Automatic Axis Scaling
```python
max_economy = max(max(team_cash), max(opponent_cash)) * 1.1
fig.update_layout(
    xaxis=dict(range=[0.5, max(rounds) + 1.5]),
    yaxis=dict(range=[0, max_economy])
)
```
Adapts to the actual data range with 10% padding.

### Color System from config.py
| Element | Color | Usage |
|---------|-------|-------|
| `LINE_COLOR_1` | #0077bb (blue) | Team 1 line color |
| `LINE_COLOR_2` | #ee7733 (orange) | Team 2 line color |
| `CT_COLOR` | #0091D4 (blue) | CT side win marker |
| `T_COLOR` | #FAB200 (gold) | T side win marker |
| `BOTH_COLOR` | #AFAFAF (gray) | Loss marker (any side) |

## API

```python
combined_economy_line_plot(
    stage,          # Required: Tournament stage (e.g., "Final")
    map_name,       # Required: Map name (e.g., "Dust2")
    team,           # Required: Team name to focus on
    show=True       # Show figure or return it
) -> go.Figure | None
```

### Helper Functions
```python
get_available_stages()              # Returns sorted list of stages
get_available_maps(stage=None)     # Returns sorted list of maps
get_available_teams(stage=None, map_name=None)  # Returns sorted list of teams
```

## CLI Usage

```bash
python src/visualization/economy_viz.py
```

This runs the main demonstration:
```python
combined_economy_line_plot("Final", "Dust2", "FaZe Clan")
```

## Visual Elements

### Lines
- Two teams' economy trends as semi-transparent lines (alpha = `LINE_ALPHA` = 0.8)
- Line width: 2px
- Color: Team-specific from config

### Markers
- Size: 20px
- White border (2px) for visibility
- Side label ("CT" or "T") centered on marker
- Color-coded by side and outcome

### Phase Separators
- Vertical dashed gray lines at:
  - Round 12.5: Half-time (end of first half)
  - Round 24.5: Overtime 1 start
  - Round 30.5: Overtime 2 start
- Only displayed if the match reached those rounds

### Axes
- **X-axis**: Round numbers (1, 2, 3, ...)
- **Y-axis**: Total team economy in dollars ($)
- Both axes have automatic scaling with padding

## Economic Insights Revealed

1. **Eco rounds**: Visible as dips in economy, typically after loss streaks
2. **Force buys**: Economy drops but not to minimal levels
3. **Full buys**: Economy peaks, usually around $15,000-$20,000
4. **Side advantage**: CT side typically has more stable economy due to round win bonuses
5. **Comeback patterns**: Steep economy recovery after winning rounds
6. **Overtime dynamics**: Economy resets and rapid rebuilding

## Limitations

- Requires both economy and outcomes data for the specified stage/map/team
- Only displays one map at a time
- Marker text (CT/T) may overlap at high zoom levels
- Does not show individual player economies, only team totals
