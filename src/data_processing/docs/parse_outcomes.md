# `parse_outcomes.py` — Per-Player Round Outcomes

## Purpose

Parses CS2 demo replay files to determine, for each player on each map, whether their team won each round. Produces `budapest_major_outcomes.csv`.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps structure |

## awpy DataFrames Used

| DataFrame | Key Columns |
|-----------|-------------|
| `demo.ticks` | `steamid`, `name`, `team_clan_name`, `side`, `round_num` |
| `demo.rounds` | `round_num`, `winner` ("ct" or "t") |

## Processing Steps

### 1. Round Winners Extraction

From `demo.rounds`, extract `(round_num, winner_side)`. Normalize `winner` column values:

| Input Values | Normalized |
|-------------|------------|
| "CT", "COUNTER", "COUNTERTERRORIST", "COUNTER TERRORIST", "COUNTER-TERRORIST" | "CT" |
| "T", "TERRORIST" | "T" |

### 2. Team Mapping

Parse `demo.ticks` for `team_clan_name` per `steamid`. Match to JSON team names (exact then partial).

### 3. Starting Side Detection

From round 1 ticks, determine each team's starting side (CT or T). Use most common side per team. If ambiguous, default: first team = CT, second = T.

### 4. Side-to-Team Mappings

Build two mappings:

| Half | Mapping |
|------|---------|
| First (r1–12) | `side → team` from starting sides |
| Second (r13+) | `opposite_side → team` (halftime swap) |

### 5. Per-Player Round Outcomes

For each player, for each round 1–36:
1. Look up the round winner's side
2. Use the correct half's side-to-team mapping to find the winning team
3. Set `r_N_outcome = True` if the winning team matches the player's team

### 6. Missing Rounds

Rounds beyond the actual map length or with no winner data → `NaN`.

## Output

| File | Path |
|------|------|
| `budapest_major_outcomes.csv` | `analysis_results/budapest_major_outcomes.csv` |

## CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `player_name` | string | Player name |
| `player_steam_id` | string | Steam ID |
| `opponent` | string | Opposing team |
| `r_1_outcome` … `r_36_outcome` | bool | True if player's team won the round |

## Sorting

By stage (Final → Quarterfinals → Semifinals), map, team, player_name.

## Dependencies

None. Standalone script.
