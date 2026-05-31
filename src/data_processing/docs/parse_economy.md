# `parse_economy.py` — Starting Cash Per Round

## Purpose

Parses CS2 demo replay files to extract each player's starting cash balance at the beginning of every round. Produces `budapest_major_economy.csv`.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps structure |

## awpy DataFrames Used

| DataFrame | Key Columns |
|-----------|-------------|
| `demo.ticks` | `steamid`, `name`, `balance`, `team_clan_name`, `tick`, `round_num` |
| `demo.rounds` | `round_num`, `start` (round start tick) |

## Processing Steps

### 1. Demo Parsing

Parse demo with `player_props=["balance", "team_clan_name"]` to include economy and team data.

### 2. Starting Cash Extraction

1. Merge `demo.ticks` with `demo.rounds` on `round_num` to get each tick's round start tick.
2. Calculate `diff = abs(tick - round_start_tick)` for each tick.
3. For each `(steamid, name, round_num)`, select the tick with minimum `diff` → this is the balance closest to round start.
4. Result: `(steamid, name, round_num, starting_cash)`.

### 3. Team Mapping

Parse `demo.ticks` for `team_clan_name` per `steamid`. Match to JSON team names (exact then partial).

### 4. Round Cash Columns

For each player:
- Build columns `r_1_cash`, `r_2_cash`, …, `r_36_cash`
- If the round exists in the map → starting cash value
- If the round doesn't exist (map ended early) → `NaN`

### 5. Sorting

By stage (Final → Quarterfinals → Semifinals), map, team, player_name.

## Output

| File | Path |
|------|------|
| `budapest_major_economy.csv` | `analysis_results/budapest_major_economy.csv` |

## CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `player_name` | string | Player name |
| `player_steam_id` | string | Steam ID |
| `opponent` | string | Opposing team |
| `r_1_cash` … `r_36_cash` | float | Starting cash at beginning of each round |

## Sorting

By stage (Final → Quarterfinals → Semifinals), map, team, player_name.

## Dependencies

None. Standalone script.
