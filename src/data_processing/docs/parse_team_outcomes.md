# `parse_team_outcomes.py` — Per-Team Round Outcomes

## Purpose

Parses CS2 demo replay files to determine, for each team on each map, whether they won each round. Produces `budapest_major_team_outcomes.csv`.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps structure |
| Match details CSV | `analysis_results/budapest_major_match_details.csv` | Starting side lookup (fallback to demo) |

## awpy DataFrames Used

| DataFrame | Key Columns |
|-----------|-------------|
| `demo.ticks` | `steamid`, `team_clan_name`, `side`, `round_num` |
| `demo.rounds` | `round_num`, `winner` ("ct" or "t") |

## Processing Steps

### 1. Match Details Lookup

Load `budapest_major_match_details.csv` to build a lookup: `(stage, map, team) → {starting_side, total_rounds}`. This is the primary source for starting sides.

### 2. Round Winners Extraction

From `demo.rounds`, extract `(round_num, winner_side)`. Normalize to "CT" or "T" (same normalization as `parse_outcomes.py`).

### 3. Starting Side Resolution

Priority order:
1. **Match details CSV** — lookup by `(stage, map, team)`
2. **Demo round 1 ticks** — most common side per team in round 1
3. **Default** — first team = CT, second = T

If both teams resolve to the same side, force first = CT, second = T.

### 4. Side-for-Round Logic

`get_side_for_round(starting_side, r)` determines which side a team plays in round `r`:

| Round Range | Side |
|-------------|------|
| 1–12 | `starting_side` |
| 13–24 | Opposite of `starting_side` (halftime swap) |
| 25+ (overtime) | Complex alternating logic: |
| | - `ot_round = r - 25` |
| | - `ot_num = ot_round // 6` (which overtime) |
| | - `ot_half = ot_round % 6` (first or second half of OT) |
| | - Even OTs: first half = side_before_ot, second half = opposite |
| | - Odd OTs: first half = opposite, second half = side_before_ot |

### 5. Round Range Formatting

`format_ranges(rounds_list)` converts a sorted list of round numbers into comma-separated ranges:
- `[1, 2, 3, 7, 8]` → `"1-3,7-8"`
- `[5]` → `"5"`

### 6. Per-Team Round Outcomes

For each team:
1. Build `CT_rounds` and `T_rounds` columns using `get_side_for_round` + `format_ranges`
2. For each round 1–36: `r_N_outcome = (winner_side == team_side)`

## Output

| File | Path |
|------|------|
| `budapest_major_team_outcomes.csv` | `analysis_results/budapest_major_team_outcomes.csv` |

## CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `opponent` | string | Opposing team |
| `CT_rounds` | string | Comma-separated CT round ranges (e.g., `"1-12,28-30"`) |
| `T_rounds` | string | Comma-separated T round ranges |
| `r_1_outcome` … `r_36_outcome` | bool | True if team won the round |

## Sorting

By stage (Final → Quarterfinals → Semifinals), map, team.

## Dependencies

**Reads** `budapest_major_match_details.csv` (output of `parse_match_details.py`). Must be run after `parse_match_details.py`.
