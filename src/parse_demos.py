"""Parse CS2 .dem files for the Budapest Major and produce a player stats CSV."""

import json
from pathlib import Path

import pandas as pd
import polars as pl
from awpy import Demo

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEM_DIR = PROJECT_ROOT / "dem_files"
JSON_PATH = PROJECT_ROOT / "src" / "budapest_major.json"
OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_stats.csv"

# ---------------------------------------------------------------------------
# Stage label normalisation: JSON key → CSV label
# ---------------------------------------------------------------------------
STAGE_LABEL = {
    "Quarterfinals": "Quarterfinals",
    "Semifinals": "Semifinals",
    "Final": "Final",
}

# Sort order for stages (alphabetical: Final < Quarterfinals < Semifinals)
STAGE_SORT = {"Final": 0, "Quarterfinals": 1, "Semifinals": 2}

# Grenade class name → CSV column.
# awpy returns C++ class names from the demo.
# We use ONLY projectile/inferno types to avoid double-counting
# (each throw produces both a held-item entity and a projectile entity).
# CIncendiaryGrenade is the CT incendiary inferno entity (no separate projectile).
GRENADE_COL: dict[str, str] = {
    "CSmokeGrenadeProjectile": "Smokes Thrown",
    "CMolotovProjectile": "Molotovs Thrown",
    "CIncendiaryGrenade": "Molotovs Thrown",   # CT incendiary (no projectile class)
    "CHEGrenadeProjectile": "Grenades",
}

STAT_COLS = ["Kills", "Assists", "Deaths", "Smokes Thrown", "Molotovs Thrown", "Grenades"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# Slug tokens extracted from team names for filename matching.
# Maps JSON team name → list of tokens that appear in dem filenames.
TEAM_SLUG_TOKENS: dict[str, list[str]] = {
    "Team Spirit":    ["spirit"],
    "Team Falcons":   ["falcons"],
    "The MongolZ":    ["mongolz"],
    "Team Vitality":  ["vitality"],
    "MOUZ":           ["mouz"],
    "FaZe Clan":      ["faze"],
    "Natus Vincere":  ["natus", "vincere", "navi"],
    "FURIA Esports":  ["furia"],
}


def _team_tokens(team_name: str) -> list[str]:
    """Return filename slug tokens for a team name."""
    if team_name in TEAM_SLUG_TOKENS:
        return TEAM_SLUG_TOKENS[team_name]
    # Fallback: lowercase words of length > 2
    return [w.lower() for w in team_name.split() if len(w) > 2]


def find_dem_file(stage_key: str, map_num: int, map_name: str, teams: list[str]) -> Path | None:
    """Locate the .dem file for a given stage/map/teams combination."""
    stage_dir = DEM_DIR / stage_key
    if not stage_dir.exists():
        for d in DEM_DIR.iterdir():
            if d.is_dir() and d.name.lower() == stage_key.lower():
                stage_dir = d
                break
        else:
            return None

    target_map = map_name.lower()
    target_m = f"m{map_num}"
    # All slug tokens for both teams in this match
    team_tokens = [tok for t in teams for tok in _team_tokens(t)]

    for dem in stage_dir.glob("*.dem"):
        stem = dem.stem.lower()
        if target_m not in stem or target_map not in stem:
            continue
        # At least one token from each team must appear in the filename
        team1_match = any(tok in stem for tok in _team_tokens(teams[0]))
        team2_match = any(tok in stem for tok in _team_tokens(teams[1]))
        if team1_match and team2_match:
            return dem
        # Fallback: any team token present (handles edge cases)
        if any(tok in stem for tok in team_tokens):
            return dem
    return None


def get_player_team_map(dem_path: Path, teams_in_match: list[str]) -> dict[str, str]:
    """Return {steamid_str: team_name} by parsing team_clan_name from the demo."""
    # Parse a minimal set of ticks just for team_clan_name
    demo_tmp = Demo(path=dem_path)
    ticks_raw = demo_tmp.parse_ticks(player_props=["team_clan_name"])
    if ticks_raw.is_empty():
        return {}

    ticks_pd = ticks_raw.select(["steamid", "team_clan_name"]).to_pandas()
    # Most common clan name per steamid
    player_clan = (
        ticks_pd.groupby("steamid")["team_clan_name"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "")
        .reset_index()
    )

    def match_team(clan: str) -> str:
        """Match a clan name to the JSON team name."""
        clan_lower = clan.lower().strip()
        for team in teams_in_match:
            if clan_lower == team.lower().strip():
                return team
        # Partial match fallback
        for team in teams_in_match:
            team_lower = team.lower()
            if clan_lower in team_lower or team_lower in clan_lower:
                return team
        return clan  # fallback: raw clan name

    player_clan["team"] = player_clan["team_clan_name"].apply(match_team)
    return {str(row["steamid"]): row["team"] for _, row in player_clan.iterrows()}


def parse_demo_stats(demo: Demo) -> pd.DataFrame:
    """Return per-player per-side stats DataFrame from a parsed Demo object.

    Columns: steamid, name, side (ct|t), Kills, Assists, Deaths,
             Smokes Thrown, Molotovs Thrown, Grenades
    """
    kills_df = demo.kills.to_pandas()

    # ---- Kills (attacker_side is the killer's side) ----------------------
    if "attacker_steamid" in kills_df.columns and "attacker_side" in kills_df.columns:
        kill_counts = (
            kills_df.dropna(subset=["attacker_steamid", "attacker_side"])
            .groupby(["attacker_steamid", "attacker_name", "attacker_side"])
            .size()
            .reset_index(name="Kills")
            .rename(columns={"attacker_steamid": "steamid", "attacker_name": "name", "attacker_side": "side"})
        )
    else:
        kill_counts = pd.DataFrame(columns=["steamid", "name", "side", "Kills"])

    # ---- Assists (assister_side) -----------------------------------------
    if "assister_steamid" in kills_df.columns and "assister_side" in kills_df.columns:
        assist_df = kills_df.dropna(subset=["assister_steamid", "assister_side"])
        if not assist_df.empty:
            assist_counts = (
                assist_df.groupby(["assister_steamid", "assister_name", "assister_side"])
                .size()
                .reset_index(name="Assists")
                .rename(columns={"assister_steamid": "steamid", "assister_name": "name", "assister_side": "side"})
            )
        else:
            assist_counts = pd.DataFrame(columns=["steamid", "name", "side", "Assists"])
    else:
        assist_counts = pd.DataFrame(columns=["steamid", "name", "side", "Assists"])

    # ---- Deaths (victim_side is the side the victim was playing) ---------
    if "victim_steamid" in kills_df.columns and "victim_side" in kills_df.columns:
        death_counts = (
            kills_df.dropna(subset=["victim_steamid", "victim_side"])
            .groupby(["victim_steamid", "victim_name", "victim_side"])
            .size()
            .reset_index(name="Deaths")
            .rename(columns={"victim_steamid": "steamid", "victim_name": "name", "victim_side": "side"})
        )
    else:
        death_counts = pd.DataFrame(columns=["steamid", "name", "side", "Deaths"])

    # ---- Grenades --------------------------------------------------------
    # grenades DataFrame has: thrower_steamid, thrower, grenade_type, tick, round_num
    # We join with ticks on (thrower_steamid=steamid, tick) to get the thrower's side.
    grenades_df = demo.grenades.to_pandas()
    grenade_stats = pd.DataFrame(columns=["steamid", "name", "side", "Smokes Thrown", "Molotovs Thrown", "Grenades"])

    if not grenades_df.empty and not demo.ticks.is_empty():
        ticks_pd = demo.ticks.select(["steamid", "tick", "side"]).to_pandas()

        # Join grenades with ticks to get side at throw tick
        grenades_with_side = grenades_df.merge(
            ticks_pd.rename(columns={"steamid": "thrower_steamid"}),
            on=["thrower_steamid", "tick"],
            how="left",
        )
        # Each grenade entity appears once per tick while in flight — keep only first tick per entity
        grenades_with_side = grenades_with_side.drop_duplicates(subset=["entity_id"])

        # Map grenade class names to CSV columns (case-sensitive keys)
        grenades_with_side["gren_col"] = grenades_with_side["grenade_type"].map(GRENADE_COL)
        grenades_with_side = grenades_with_side.dropna(subset=["gren_col", "side"])

        if not grenades_with_side.empty:
            pivot = (
                grenades_with_side.groupby(["thrower_steamid", "thrower", "side", "gren_col"])
                .size()
                .reset_index(name="count")
                .pivot_table(
                    index=["thrower_steamid", "thrower", "side"],
                    columns="gren_col",
                    values="count",
                    fill_value=0,
                )
                .reset_index()
            )
            pivot.columns.name = None
            pivot = pivot.rename(columns={"thrower_steamid": "steamid", "thrower": "name"})
            for col in ["Smokes Thrown", "Molotovs Thrown", "Grenades"]:
                if col not in pivot.columns:
                    pivot[col] = 0
            grenade_stats = pivot

    # ---- Master player list from ticks (all steamids that played) --------
    ticks_pd = demo.ticks.select(["steamid", "name", "side"]).to_pandas()
    player_sides = (
        ticks_pd.drop_duplicates(subset=["steamid", "side"])[["steamid", "name", "side"]]
        .copy()
    )

    # ---- Merge all stats into player_sides -------------------------------
    stats = player_sides.copy()

    for merge_df, col in [
        (kill_counts, "Kills"),
        (assist_counts, "Assists"),
        (death_counts, "Deaths"),
    ]:
        if not merge_df.empty and col in merge_df.columns:
            stats = stats.merge(
                merge_df[["steamid", "side", col]], on=["steamid", "side"], how="left"
            )
        else:
            stats[col] = float("nan")

    if not grenade_stats.empty and "steamid" in grenade_stats.columns:
        g_cols = ["steamid", "side"] + [
            c for c in ["Smokes Thrown", "Molotovs Thrown", "Grenades"] if c in grenade_stats.columns
        ]
        stats = stats.merge(grenade_stats[g_cols], on=["steamid", "side"], how="left")

    # Fill 0 for all stat columns (player played this side → 0 is correct for missing stats)
    for col in STAT_COLS:
        if col not in stats.columns:
            stats[col] = 0.0
        stats[col] = stats[col].fillna(0)

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(JSON_PATH, encoding="utf-8") as f:
        tournament = json.load(f)

    all_rows: list[dict] = []

    for stage_key, matches in tournament["stages"].items():
        stage_label = STAGE_LABEL[stage_key]
        print(f"\n=== {stage_label} ===")

        for match in matches:
            teams = match["teams_played"]
            for map_info in match["maps_played"]:
                map_num = map_info["map_number"]
                map_name = map_info["map_name"]

                dem_path = find_dem_file(stage_key, map_num, map_name, teams)
                if dem_path is None:
                    print(f"  WARNING: No .dem found for {stage_key} m{map_num} {map_name}")
                    continue

                print(f"  Parsing: {dem_path.name}")

                # Get team mapping (requires separate tick parse for team_clan_name)
                player_team_map = get_player_team_map(dem_path, teams)

                # Parse the demo fully
                demo = Demo(path=dem_path)
                demo.parse()

                # Get per-side stats
                per_side_stats = parse_demo_stats(demo)

                # Build 3 rows per player: CT, T, Both
                for steamid in per_side_stats["steamid"].unique():
                    player_rows = per_side_stats[per_side_stats["steamid"] == steamid]
                    player_name = player_rows["name"].iloc[0]
                    team_name = player_team_map.get(str(steamid), "Unknown")

                    ct_row = player_rows[player_rows["side"] == "ct"]
                    t_row = player_rows[player_rows["side"] == "t"]

                    def side_stats(row_df: pd.DataFrame) -> dict | None:
                        if row_df.empty:
                            return None
                        r = row_df.iloc[0]
                        return {col: r[col] for col in STAT_COLS}

                    ct_stats = side_stats(ct_row)
                    t_stats = side_stats(t_row)

                    base = {
                        "stages": stage_label,
                        "map": map_name,
                        "team": team_name,
                        "player_name": player_name,
                        "player_steamid": str(steamid),
                    }

                    # CT row
                    ct_entry = {**base, "side": "Counter Terrorist"}
                    ct_entry.update(ct_stats if ct_stats else {col: float("nan") for col in STAT_COLS})
                    all_rows.append(ct_entry)

                    # T row
                    t_entry = {**base, "side": "Terrorist"}
                    t_entry.update(t_stats if t_stats else {col: float("nan") for col in STAT_COLS})
                    all_rows.append(t_entry)

                    # Both row — sum CT + T; NaN only if both sides are NaN
                    both_entry = {**base, "side": "Both"}
                    for col in STAT_COLS:
                        cv = ct_stats[col] if ct_stats else float("nan")
                        tv = t_stats[col] if t_stats else float("nan")
                        if pd.isna(cv) and pd.isna(tv):
                            both_entry[col] = float("nan")
                        else:
                            both_entry[col] = (0.0 if pd.isna(cv) else cv) + (0.0 if pd.isna(tv) else tv)
                    all_rows.append(both_entry)

    # ---- Build and sort DataFrame ----------------------------------------
    df = pd.DataFrame(all_rows)

    # Sort: stage (alphabetical) → map → team → player_name → side order
    side_order = {"Counter Terrorist": 0, "Terrorist": 1, "Both": 2}
    df["_stage_sort"] = df["stages"].map(STAGE_SORT)
    df["_side_sort"] = df["side"].map(side_order)
    df = (
        df.sort_values(by=["_stage_sort", "map", "team", "player_name", "_side_sort"])
        .drop(columns=["_stage_sort", "_side_sort"])
        .reset_index(drop=True)
    )

    # Numeric columns
    for col in STAT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nCSV written to: {OUTPUT_CSV}")
    print(f"Total rows: {len(df)}")
    print(df.head(15).to_string())


if __name__ == "__main__":
    main()
