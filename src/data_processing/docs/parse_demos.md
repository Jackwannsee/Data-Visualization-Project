# `parse_demos.py` — Player Stats

## Purpose

Parses CS2 demo replay files to extract per-player, per-side combat and utility statistics. Produces `budapest_major_stats.csv`.

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| CS2 Demo files (`.dem`) | `dem_files/{stage}/` | Raw match replays via `awpy.Demo` |
| Tournament bracket | `src/budapest_major.json` | Stages → matches → maps structure |

## awpy DataFrames Used

| DataFrame | Key Columns |
|-----------|-------------|
| `demo.ticks` | `steamid`, `name`, `side`, `round_num` |
| `demo.kills` | `attacker_steamid`, `attacker_name`, `attacker_side`, `assister_steamid`, `assister_name`, `assister_side`, `victim_steamid`, `victim_name`, `victim_side`, `weapon`, `headshot` |
| `demo.grenades` | `thrower_steamid`, `thrower`, `grenade_type`, `tick`, `round_num`, `entity_id` |

## Processing Steps

### 1. Team Mapping

A separate minimal tick parse extracts `team_clan_name` per `steamid`. The most common clan name is matched against the JSON team names (exact match first, then partial match).

### 2. Kills

Group `demo.kills` by `(attacker_steamid, attacker_name, attacker_side)` → count.

### 3. Assists

Group `demo.kills` by `(assister_steamid, assister_name, assister_side)` → count.

### 4. Deaths

Group `demo.kills` by `(victim_steamid, victim_name, victim_side)` → count.

### 5. Headshots

Filter `headshot == True`, then group by `(attacker_steamid, attacker_side)` → count.

### 6. Grenades

1. Join `demo.grenades` with `demo.ticks` on `(thrower_steamid, tick)` to resolve the thrower's side.
2. Deduplicate by `entity_id` (each grenade entity appears once per tick while in flight).
3. Map `grenade_type` (C++ class names) to CSV columns:

| Grenade Type (awpy) | CSV Column |
|---------------------|------------|
| `CSmokeGrenadeProjectile` | Smokes Thrown |
| `CMolotovProjectile` | Molotovs Thrown |
| `CIncendiaryGrenade` | Molotovs Thrown |
| `CHEGrenadeProjectile` | Grenades |

4. Pivot to wide format: `(thrower_steamid, thrower, side, gren_col)` → count.

### 7. Rounds Played

Count unique `(steamid, side, round_num)` combinations from `demo.ticks`.

### 8. Merge & Expand

1. Merge all stat DataFrames into a master player-side table.
2. Fill missing stats with 0 (player played that side → 0 is correct).
3. Expand to 3 rows per player: **Counter Terrorist**, **Terrorist**, **Both** (Both = CT + T sum; NaN only if both sides are NaN).

### 9. Headshot %

`Headshot % = Headshots / Kills × 100`, rounded to 2 decimals.

## Output

| File | Path |
|------|------|
| `budapest_major_stats.csv` | `analysis_results/budapest_major_stats.csv` |

## CSV Schema

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

## Sorting

By stage (Final → Quarterfinals → Semifinals), map, team, player_name, side (CT → T → Both).

## Dependencies

None. Standalone script.
