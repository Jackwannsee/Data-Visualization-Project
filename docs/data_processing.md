# Data Processing Pipeline

## Overview

This module parses CS2 demo replay files from the Budapest Major tournament into structured CSV datasets for visualization. Each script targets a specific data dimension (player stats, round outcomes, positions, economy, etc.).

### Pipeline Flow

```
budapest_major.json (tournament bracket)
        │
        ▼
  for each stage (Quarterfinals → Semifinals → Final):
    for each match:
      for each map in maps_played:
        locate .dem file by stage + map_num + team slugs
        Demo(path).parse(...)
          → extract raw data (ticks, kills, rounds, grenades)
          → transform & aggregate
          → attach metadata (stage, map, team)
        append to accumulator
  concat all accumulators → sort → to_csv()
```

**Entry points:** Each `parse_*.py` script is standalone — run individually. No orchestration script exists.

**Inter-script dependency:** `parse_team_outcomes.py` reads `budapest_major_match_details.csv` (output of `parse_match_details.py`) to determine team starting sides. All other scripts are independent.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays parsed via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps structure |
| Match details CSV | `analysis_results/budapest_major_match_details.csv` | Side lookup for `parse_team_outcomes.py` |
| awpy MAP_DATA | `awpy.data.map_data.MAP_DATA` | Map coordinate metadata (level thresholds) |

### awpy.Demo DataFrames

| DataFrame | Key Columns | Used By |
|-----------|-------------|---------|
| `demo.ticks` | `steamid`, `name`, `side`, `team_clan_name`, `X`, `Y`, `Z`, `health`, `tick`, `round_num`, `balance` | All scripts |
| `demo.kills` | `attacker_steamid`, `assister_steamid`, `victim_steamid`, `weapon`, `headshot` | `parse_weapon_kills.py`, `parse_demos.py` |
| `demo.rounds` | `round_num`, `winner`, `freeze_end`, `start` | All outcome/position scripts |
| `demo.grenades` | `thrower_steamid`, `grenade_type`, `tick`, `round_num` | `parse_demos.py` |

## Processing Steps by Script

### 1. `parse_demos.py` — Player Stats

1. Parse demo → extract kills, grenades, ticks DataFrames
2. Group kills by attacker/assister/victim side → Kills, Assists, Deaths
3. Filter `headshot==True` → Headshots
4. Join grenades with ticks on `(thrower_steamid, tick)` → resolve player side at throw
5. Map `grenade_type` → Smokes/Molotovs/Grenades columns
6. Count unique `(steamid, side, round_num)` → Rounds Played
7. Merge all stats per `(steamid, side)`
8. Expand to 3 rows per player: CT, T, Both (Both = CT + T sum)
9. Compute Headshot % = Headshots / Kills × 100

### 2. `parse_match_details.py` — Match Details

1. Parse demo with `player_props=["team_clan_name"]`
2. From round 1 ticks → determine each team's starting side (CT or T)
3. Split rounds into first half (r1–12) and second half (r13+)
4. Count `winner=="ct"` and `winner=="t"` in each half
5. Apply halftime swap: if team started CT, CT wins come from first half, T wins from second half
6. Output 3 rows per team per map: Counter Terrorist, Terrorist, Both

### 3. `parse_outcomes.py` — Per-Player Round Outcomes

1. Parse demo with `player_props=["team_clan_name", "side"]`
2. Get round winners (`round_num` → winner side "CT"/"T")
3. Determine team starting sides from round 1 ticks
4. Build first/second half side-to-team mappings
5. For each player, for each round: check if winner side matches player's team side → boolean outcome
6. Output 1 row per player per map with `r_1_outcome` … `r_36_outcome` columns

### 4. `parse_team_outcomes.py` — Per-Team Round Outcomes

1. Load `budapest_major_match_details.csv` for side lookup
2. Parse demo with `player_props=["team_clan_name", "side"]`
3. Get round winners
4. Determine team starting sides (from CSV lookup, fallback to demo round 1)
5. `get_side_for_round(starting_side, r)` handles:
   - r ≤ 12: starting side
   - r 13–24: swapped side
   - r ≥ 25 (overtime): alternating OT swap logic (every 3 rounds)
6. `format_ranges()` for CT_rounds / T_rounds columns (e.g., `"1-12,28-30"`)
7. Boolean outcome per round per team

### 5. `parse_weapon_kills.py` — Weapon Kill Counts

1. Parse demo
2. Get player team map via separate tick parse for `team_clan_name`
3. Filter kills: drop nulls, exclude `NON_KILL_WEAPONS` (world, planted_c4, hegrenade, inferno, molotov, incendiary, smokegrenade, flashbang, decoy)
4. Group by `(attacker_steamid, attacker_name, attacker_side, weapon)` → kill_count
5. Normalize weapon names (strip `_silencer` suffix)
6. Aggregate across all maps: group by `(team, player_name, player_steamid, weapon)` → sum kill_count
7. Sort by team, player_name, kill_count desc, weapon

### 6. `parse_economy.py` — Starting Cash Per Round

1. Parse demo with `player_props=["balance", "team_clan_name"]`
2. Merge ticks with rounds on `round_num` to get round start tick
3. For each `(steamid, name, round_num)`: find tick closest to round start → get balance
4. Build `r_1_cash` … `r_36_cash` columns per player

### 7. `parse_positions.py` — Position Heatmap Data

1. Parse demo
2. Downsample 16:1 (128 ticks/s → 8 samples/s)
3. Filter: `health > 0`, `side` not null
4. Exclude buy period: `tick > freeze_end` (from rounds data)
5. Determine map key (e.g., `"de_nuke"`) → lookup `MAP_DATA` for `lower_level_max_units`
6. Assign level: `Z ≤ threshold` → `"lower"`, else `"upper"`
7. Bin X/Y coordinates: `floor_divide` by granularity (25 game units)
8. Group by `(side, level, x_bin, y_bin).size()` → count

## Output Locations

All CSVs are written to `analysis_results/` (created via `mkdir -p` if needed).

| Script | Output File |
|--------|-------------|
| `parse_demos.py` | `budapest_major_stats.csv` |
| `parse_match_details.py` | `budapest_major_match_details.csv` |
| `parse_outcomes.py` | `budapest_major_outcomes.csv` |
| `parse_team_outcomes.py` | `budapest_major_team_outcomes.csv` |
| `parse_weapon_kills.py` | `budapest_major_weapon_kills.csv` |
| `parse_economy.py` | `budapest_major_economy.csv` |
| `parse_positions.py` | `budapest_major_positions.csv` |

## Output CSV Schemas

### `budapest_major_stats.csv`

| Column | Type | Description |
|--------|------|-------------|
| `stages` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `player_name` | string | Player name |
| `player_steamid` | string | Steam ID |
| `side` | string | Counter Terrorist / Terrorist / Both |
| `Kills` | float | Total kills |
| `Assists` | float | Total assists |
| `Deaths` | float | Total deaths |
| `Smokes Thrown` | float | Smoke grenades thrown |
| `Molotovs Thrown` | float | Molotov/incendiary thrown |
| `Grenades` | float | HE grenades thrown |
| `Headshots` | float | Headshot kills |
| `Rounds Played` | float | Unique rounds played |
| `Headshot %` | float | Headshots / Kills × 100 |

### `budapest_major_match_details.csv`

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

### `budapest_major_outcomes.csv`

| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `player_name` | string | Player name |
| `player_steam_id` | string | Steam ID |
| `opponent` | string | Opposing team |
| `r_1_outcome` … `r_36_outcome` | bool | True if player's team won the round |

### `budapest_major_team_outcomes.csv`

| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `opponent` | string | Opposing team |
| `CT_rounds` | string | Comma-separated CT round ranges (e.g., `"1-12,28-30"`) |
| `T_rounds` | string | Comma-separated T round ranges |
| `r_1_outcome` … `r_36_outcome` | bool | True if team won the round |

### `budapest_major_weapon_kills.csv`

| Column | Type | Description |
|--------|------|-------------|
| `team` | string | Team name |
| `player_name` | string | Player name |
| `player_steamid` | string | Steam ID |
| `weapon` | string | Normalized weapon name (no `_silencer` suffix) |
| `kill_count` | int | Total kills with this weapon across all maps |

### `budapest_major_economy.csv`

| Column | Type | Description |
|--------|------|-------------|
| `stage` | string | Tournament stage |
| `map` | string | Map display name |
| `team` | string | Team name |
| `player_name` | string | Player name |
| `player_steam_id` | string | Steam ID |
| `opponent` | string | Opposing team |
| `r_1_cash` … `r_36_cash` | float | Starting cash at beginning of each round |

### `budapest_major_positions.csv`

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
