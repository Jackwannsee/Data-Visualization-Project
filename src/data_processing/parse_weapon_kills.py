"""Parse CS2 .dem files for the Budapest Major and produce a player weapon kills CSV."""

import json
from pathlib import Path

import pandas as pd
import polars as pl
from awpy import Demo

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEM_DIR = PROJECT_ROOT / "dem_files"
JSON_PATH = PROJECT_ROOT / "src" / "budapest_major.json"
OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_weapon_kills.csv"

# ---------------------------------------------------------------------------
# Stage label normalisation
# ---------------------------------------------------------------------------
STAGE_LABEL = {
    "Quarterfinals": "Quarterfinals",
    "Semifinals": "Semifinals",
    "Final": "Final",
}

STAGE_SORT = {"Final": 0, "Quarterfinals": 1, "Semifinals": 2}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


# Weapons that should be excluded (did not directly result in a kill)
NON_KILL_WEAPONS = {
    "world",           # World/spawn kills
    "planted_c4",      # C4 explosion
    "hegrenade",       # HE grenade (indirect)
    "inferno",         # Fire damage
    "molotov",         # Molotov fire
    "incendiary",      # Incendiary grenade
    "smokegrenade",    # Smoke
    "flashbang",       # Flashbang
    "decoy",           # Decoy
}


def normalize_weapon_name(weapon: str) -> str:
    """Normalize weapon names by removing _silencer suffix.
    
    Examples:
        m4a1_silencer -> m4a1
        usp_silencer -> usp
        m4a1 -> m4a1
        awp -> awp
    """
    if weapon.endswith("_silencer"):
        return weapon[:-9]  # Remove '_silencer' (9 characters)
    return weapon


def _team_tokens(team_name: str) -> list[str]:
    """Return filename slug tokens for a team name."""
    if team_name in TEAM_SLUG_TOKENS:
        return TEAM_SLUG_TOKENS[team_name]
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

    for dem in stage_dir.glob("*.dem"):
        stem = dem.stem.lower()
        if target_m not in stem or target_map not in stem:
            continue
        team1_match = any(tok in stem for tok in _team_tokens(teams[0]))
        team2_match = any(tok in stem for tok in _team_tokens(teams[1]))
        if team1_match and team2_match:
            return dem
        if any(tok in stem for tok in [tok for t in teams for tok in _team_tokens(t)]):
            return dem
    return None


def get_player_team_map(dem_path: Path, teams_in_match: list[str]) -> dict[str, str]:
    """Return {steamid_str: team_name} by parsing team_clan_name from the demo."""
    demo_tmp = Demo(path=dem_path)
    ticks_raw = demo_tmp.parse_ticks(player_props=["team_clan_name"])
    if ticks_raw.is_empty():
        return {}

    ticks_pd = ticks_raw.select(["steamid", "team_clan_name"]).to_pandas()
    player_clan = (
        ticks_pd.groupby("steamid")["team_clan_name"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "")
        .reset_index()
    )
    player_clan["steamid"] = player_clan["steamid"].astype("int64")

    def match_team(clan: str) -> str:
        clan_lower = clan.lower().strip()
        for team in teams_in_match:
            if clan_lower == team.lower().strip():
                return team
        for team in teams_in_match:
            team_lower = team.lower()
            if clan_lower in team_lower or team_lower in clan_lower:
                return team
        return clan

    player_clan["team"] = player_clan["team_clan_name"].apply(match_team)
    return {str(row["steamid"]): row["team"] for _, row in player_clan.iterrows()}


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

                # Get team mapping
                player_team_map = get_player_team_map(dem_path, teams)

                # Parse the demo
                demo = Demo(path=dem_path)
                demo.parse()

                # Extract weapon kills
                # Filter to valid weapon kills in Polars first to avoid precision loss on steamids
                kills_pl = demo.kills.drop_nulls(subset=["attacker_steamid", "attacker_name", "attacker_side", "weapon"])
                valid_kills = kills_pl.to_pandas()
                valid_kills = valid_kills[~valid_kills["weapon"].isin(NON_KILL_WEAPONS)]

                if valid_kills.empty:
                    print(f"    No valid weapon kills found")
                    continue

                # Count kills by player, weapon, and side
                weapon_kills = (
                    valid_kills.groupby(["attacker_steamid", "attacker_name", "attacker_side", "weapon"])
                    .size()
                    .reset_index(name="kill_count")
                )

                for _, row in weapon_kills.iterrows():
                    steamid = str(row["attacker_steamid"])
                    team_name = player_team_map.get(steamid, "Unknown")
                    normalized_weapon = normalize_weapon_name(row["weapon"])

                    all_rows.append({
                        "stage": stage_label,
                        "map": map_name,
                        "team": team_name,
                        "player_name": row["attacker_name"],
                        "player_steamid": steamid,
                        "side": row["attacker_side"],
                        "weapon": normalized_weapon,
                        "kill_count": int(row["kill_count"]),
                    })

    # ---- Build and aggregate DataFrame ----------------------------------
    df = pd.DataFrame(all_rows)

    # Aggregate across all games and rounds
    aggregated_df = (
        df.groupby(["team", "player_name", "player_steamid", "weapon"])
        .agg({"kill_count": "sum"})
        .reset_index()
    )

    # Sort by team, player_name, kill_count (descending), weapon
    aggregated_df = (
        aggregated_df.sort_values(
            by=["team", "player_name", "kill_count", "weapon"],
            ascending=[True, True, False, True]
        )
        .reset_index(drop=True)
    )

    aggregated_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nCSV written to: {OUTPUT_CSV}")
    print(f"Total rows: {len(aggregated_df)}")
    print(f"Total unique players: {aggregated_df['player_name'].nunique()}")
    print(f"Total unique weapons: {aggregated_df['weapon'].nunique()}")
    print(aggregated_df.head(20).to_string())


if __name__ == "__main__":
    main()
