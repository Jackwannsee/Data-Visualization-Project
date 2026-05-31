# `parse_positions.py` — Position Heatmap Data

## Purpose

Parses CS2 demo replay files to extract binned player position data for heatmap visualization. Produces `budapest_major_positions.csv`.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps structure |
| Map metadata | `awpy.data.map_data.MAP_DATA` | Map coordinate metadata (level thresholds) |

## awpy DataFrames Used

| DataFrame | Key Columns |
|-----------|-------------|
| `demo.ticks` | `steamid`, `name`, `side`, `team_clan_name`, `X`, `Y`, `Z`, `health`, `tick`, `round_num` |
| `demo.rounds` | `round_num`, `freeze_end` |

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DOWNSAMPLE_FACTOR` | 16 | 128 ticks/s → 8 samples/s |
| `BASE_GRANULARITY` | 25 | Finest bin size in game units |

## Processing Steps

### 1. Demo Parsing

Parse demo fully (no `player_props` needed — side is included by default).

### 2. Downsampling

Keep every 16th tick: `ticks.iloc[::16]`. Reduces 128 ticks/s to 8 samples/s.

### 3. Filtering

- `health > 0` — only alive players
- `side` not null — only players with known side

### 4. Buy Period Exclusion

1. Build `round_num → freeze_end` mapping from `demo.rounds`.
2. `freeze_end` is the tick when players can move freely after buy time.
3. Keep only ticks where `tick > freeze_end` for their round.

### 5. Map Level Classification

1. Determine map key: `f"de_{map_display_name.lower()}"` (e.g., `"de_nuke"`).
2. Lookup `MAP_DATA[map_key]['lower_level_max_units']` for Z threshold.
3. Assign level: `Z ≤ threshold` → `"lower"`, else → `"upper"`.

### 6. Coordinate Binning

Floor-divide X and Y by `BASE_GRANULARITY` (25 game units):
```python
x_bin = (X // 25 * 25).astype(int)
y_bin = (Y // 25 * 25).astype(int)
```

### 7. Aggregation

Group by `(side, level, x_bin, y_bin)` → count samples per bin.

## Output

| File | Path |
|------|------|
| `budapest_major_positions.csv` | `analysis_results/budapest_major_positions.csv` |

## CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `stages` | string | Tournament stage |
| `map` | string | Map display name |
| `teams` | string | Match pairing (e.g., `"Team Spirit vs Team Falcons"`) |
| `side` | string | Team side (`ct` or `t`) |
| `level` | string | Map level (`upper` or `lower`) |
| `x_bin` | int | Binned X coordinate (25-unit granularity) |
| `y_bin` | int | Binned Y coordinate (25-unit granularity) |
| `count` | int | Number of tick samples in this bin |

## Sorting

No explicit sorting — rows are in iteration order (stage → match → map).

## Dependencies

None. Standalone script.
