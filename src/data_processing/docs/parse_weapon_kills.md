# `parse_weapon_kills.py` — Weapon Kill Counts

## Purpose

Parses CS2 demo replay files to extract per-player weapon kill counts aggregated across all maps. Produces `budapest_major_weapon_kills.csv`.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps structure |

## awpy DataFrames Used

| DataFrame | Key Columns |
|-----------|-------------|
| `demo.ticks` | `steamid`, `team_clan_name` |
| `demo.kills` | `attacker_steamid`, `attacker_name`, `attacker_side`, `weapon` |

## Processing Steps

### 1. Team Mapping

A separate minimal tick parse extracts `team_clan_name` per `steamid`. Most common clan name matched to JSON team names (exact then partial).

### 2. Kill Filtering

From `demo.kills`:
1. Drop rows with nulls in `(attacker_steamid, attacker_name, attacker_side, weapon)`
2. Exclude non-kill weapons:

| Excluded Weapon | Reason |
|-----------------|--------|
| `world` | World/spawn kills |
| `planted_c4` | C4 explosion |
| `hegrenade` | HE grenade (indirect) |
| `inferno` | Fire damage |
| `molotov` | Molotov fire |
| `incendiary` | Incendiary grenade |
| `smokegrenade` | Smoke |
| `flashbang` | Flashbang |
| `decoy` | Decoy |

### 3. Weapon Name Normalization

Strip `_silencer` suffix (9 characters):
- `m4a1_silencer` → `m4a1`
- `usp_silencer` → `usp`
- `awp` → `awp` (unchanged)

### 4. Per-Map Kill Counts

Group by `(attacker_steamid, attacker_name, attacker_side, weapon)` → count.

### 5. Cross-Map Aggregation

Group by `(team, player_name, player_steamid, weapon)` → sum `kill_count`.

### 6. Sorting

By team, player_name, kill_count (descending), weapon.

## Output

| File | Path |
|------|------|
| `budapest_major_weapon_kills.csv` | `analysis_results/budapest_major_weapon_kills.csv` |

## CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `team` | string | Team name |
| `player_name` | string | Player name |
| `player_steamid` | string | Steam ID |
| `weapon` | string | Normalized weapon name (no `_silencer` suffix) |
| `kill_count` | int | Total kills with this weapon across all maps |

## Sorting

By team, player_name, kill_count (descending), weapon.

## Dependencies

None. Standalone script.
