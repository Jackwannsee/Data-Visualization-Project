# parse_positions.py — Position Data Extraction

## Purpose

Extracts player position data from CS2 demo files and produces a binned position count CSV for heatmap visualization.

## Pipeline

```
.dem files -> awpy Demo.parse() -> tick data -> filter/downsample -> bin coordinates -> aggregate -> CSV
```

## Processing Steps (per demo)

1. **Parse** demo via `awpy.Demo.parse()` — returns Polars DataFrame of tick data
2. **Downsample** 16:1 (128 ticks/s -> 8 samples/s)
3. **Filter** — alive (`health > 0`), known side (`side` not null), exclude buy period (see below)
4. **Assign level** — uses `MAP_DATA[map_key]['lower_level_max_units']` as Z threshold (Nuke: -495, Train: -50)
5. **Bin coordinates** — floor-divide X/Y by granularity (default 25 game units)
6. **Aggregate** — `groupby(['side', 'level', 'x_bin', 'y_bin']).size()`

## Buy Period Exclusion

Buy period (freeze time) ticks are excluded using `demo.rounds.freeze_end` timestamps rather than filtering by `place` name. This avoids the inconsistency where CT spawn is labeled as map locations (e.g., `BombsiteA` on Overpass) while T spawn is labeled `TSpawn`.

For each round, only ticks with `tick > freeze_end` are kept. This uniformly excludes buy period data across all maps regardless of how awpy labels spawn areas.

## Demo Discovery

The `find_dem_file()` helper locates `.dem` files by matching stage directory, map number (`m1`, `m2`, etc.), map name, and both team slug tokens in the filename. Returns `None` if no match found (demo skipped).

## Tournament Iteration

`main()` reads `budapest_major.json` and iterates `stages -> matches -> maps_played`. For each map, it resolves the demo file, extracts positions, and attaches metadata (`stages`, `map`, `teams`). All per-demo DataFrames are concatenated into one CSV.

## Output

`analysis_results/budapest_major_positions.csv`

| Column | Description |
|--------|-------------|
| `stages` | Tournament stage (Quarterfinals, Semifinals, Final) |
| `map` | Map display name (Nuke, Dust2, etc.) |
| `teams` | Match pairing (e.g. "Team Spirit vs Team Falcons") |
| `side` | Team side (`ct` or `t`) |
| `level` | Map level (`upper` or `lower`) |
| `x_bin` | Binned X coordinate (game units) |
| `y_bin` | Binned Y coordinate (game units) |
| `count` | Number of tick samples in this bin |

## Key Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `DOWNSAMPLE_FACTOR` | 16 | Tick rate reduction |
| `BASE_GRANULARITY` | 25 | Finest bin size in game units |

## Dependencies

- `awpy` — demo parsing and `MAP_DATA` coordinate metadata
- `pandas` — DataFrame operations
- `budapest_major.json` — tournament bracket (maps per match)

## Usage

```bash
python src/data_processing/parse_positions.py
```

Processes all 18 demos in ~2 minutes.
