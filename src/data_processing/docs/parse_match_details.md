# `parse_match_details.py` — Match Details

## Purpose

Parses CS2 demo replay files to extract per-team, per-side round win/loss details for each map. Produces `budapest_major_match_details.csv`.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps, match winners, scores |

## awpy DataFrames Used

| DataFrame | Key Columns |
|-----------|-------------|
| `demo.ticks` | `steamid`, `team_clan_name`, `side`, `round_num` |
| `demo.rounds` | `round_num`, `winner` ("ct" or "t") |

## Processing Steps

### 1. Starting Side Detection

From round 1 ticks only, group by `team_clan_name` → most common `side` value. Match demo clan names to JSON team names (exact match first, then partial match).

### 2. Round Splitting

Split `demo.rounds` into two halves:
- **First half**: rounds 1–12
- **Second half**: rounds 13+

Count `winner == "ct"` and `winner == "t"` in each half.

### 3. Halftime Side Swap

Apply the standard CS2 halftime swap:

| Starting Side | CT Rounds Won | T Rounds Won |
|---------------|---------------|--------------|
| CT | First half CT wins | Second half T wins |
| T | Second half CT wins | First half T wins |

### 4. Rows Per Team

For each team, produce 3 rows:

| side | rounds_played | rounds_won |
|------|---------------|------------|
| Counter Terrorist | `min(12, total_rounds)` | CT rounds won (per swap logic) |
| Terrorist | `max(0, total_rounds - 12)` | T rounds won (per swap logic) |
| Both | `total_rounds` | CT + T sum |

### 5. Match Metadata

Enrich each row with:
- `opponent`: the other team in the match
- `game_won`: `team == overall_winner` from JSON
- `map_won`: `team == map_winner` from JSON
- `map_number`, `final_score`, `total_maps_played` from JSON

## Output

| File | Path |
|------|------|
| `budapest_major_match_details.csv` | `analysis_results/budapest_major_match_details.csv` |

## CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `stages` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `opponent` | string | Opposing team |
| `side` | string | Counter Terrorist / Terrorist / Both |
| `rounds_played` | float | Rounds played on this side |
| `rounds_won` | float | Rounds won on this side |
| `game_won` | bool | Team won the match |
| `map_won` | bool | Team won this map |
| `map_number` | float | Map number in match (1, 2, 3) |
| `final_score` | string | Map score |
| `total_maps_played` | float | Total maps in match |

## Sorting

By stage (Final → Quarterfinals → Semifinals), map, team, side (CT → T → Both).

## Dependencies

None. Standalone script.
