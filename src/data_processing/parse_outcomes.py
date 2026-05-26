"""Parse CS2 .dem files for the Budapest Major and produce a player round outcome CSV."""

import json
from pathlib import Path

import pandas as pd
from awpy import Demo

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEM_DIR = PROJECT_ROOT / "dem_files"
JSON_PATH = PROJECT_ROOT / "src" / "budapest_major.json"
OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_outcomes.csv"

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

# Maximum number of rounds to create columns for
MAX_ROUNDS = 36

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


def get_round_winners(demo: Demo) -> pd.DataFrame:
    """Extract round winner information from a demo.
    
    Returns DataFrame with columns: round_num, winner_team
    """
    rounds = demo.rounds.to_pandas()
    
    if rounds.empty:
        return pd.DataFrame(columns=["round_num", "winner_team"])
    
    # awpy uses camelCase column names: roundNum, winnerSide, winnerName
    # Check available columns and use the right ones
    available_cols = rounds.columns.tolist()
    
    # Map possible column name variants
    round_num_col = "roundNum" if "roundNum" in available_cols else "round_num"
    winner_side_col = "winnerSide" if "winnerSide" in available_cols else ("winner_side" if "winner_side" in available_cols else None)
    winner_name_col = "winnerName" if "winnerName" in available_cols else ("winner_name" if "winner_name" in available_cols else None)
    
    cols_to_select = [round_num_col]
    if winner_side_col:
        cols_to_select.append(winner_side_col)
    if winner_name_col:
        cols_to_select.append(winner_name_col)
    
    result = rounds[cols_to_select].copy()
    
    # Rename to consistent names
    result = result.rename(columns={
        round_num_col: "round_num",
        winner_side_col: "winner_side" if winner_side_col else None,
        winner_name_col: "winner_name" if winner_name_col else None
    })
    
    # Filter to keep only round_num and winner columns
    winner_cols = [c for c in ["winner_side", "winner_name"] if c in result.columns]
    result = result[["round_num"] + winner_cols]
    
    # Use winner_name if available, otherwise use winner_side
    if "winner_name" in result.columns:
        result["winner_team"] = result["winner_name"].fillna(result.get("winner_side", "Unknown"))
    elif "winner_side" in result.columns:
        result["winner_team"] = result["winner_side"]
    else:
        result["winner_team"] = "Unknown"
    
    result = result[["round_num", "winner_team"]]
    
    return result


def get_player_team_map(demo: Demo, teams: list[str]) -> dict[str, str]:
    """Return {steamid: team_name} mapping from demo."""
    ticks = demo.ticks.select(["steamid", "name", "team_clan_name"]).to_pandas()
    if ticks.empty:
        return {}
    
    # Convert steamid to string for consistency
    ticks["steamid"] = ticks["steamid"].astype(str)
    
    # Match clan name to JSON team name
    def match_team(clan) -> str:
        if pd.isna(clan):
            return "Unknown"
        clan_lower = str(clan).lower().strip()
        for team in teams:
            if clan_lower == team.lower().strip():
                return team
        for team in teams:
            team_lower = team.lower()
            if clan_lower in team_lower or team_lower in clan_lower:
                return team
        return str(clan)
    
    ticks["team"] = ticks["team_clan_name"].apply(match_team)
    return {str(row["steamid"]): row["team"] for _, row in ticks.iterrows()}


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

                # Parse the demo with team_clan_name
                demo = Demo(path=dem_path)
                demo.parse(player_props=["team_clan_name"])

                # Get round winners
                winners_df = get_round_winners(demo)
                
                # Get player to team mapping
                player_team_map = get_player_team_map(demo, teams)
                
                # Get total rounds in this map
                rounds_pd = demo.rounds.to_pandas()
                total_rounds = len(rounds_pd)
                
                # Get all ticks data once for name lookup
                ticks_data = demo.ticks.select(["steamid", "name"]).to_pandas()
                ticks_data["steamid"] = ticks_data["steamid"].astype(str)
                
                # For each player, build their round outcomes
                for steamid, team in player_team_map.items():
                    # Ensure steamid is string for comparison
                    steamid = str(steamid)
                    
                    # Get player name from ticks data
                    player_match = ticks_data[ticks_data["steamid"] == steamid]
                    player_name = player_match["name"].iloc[0] if not player_match.empty else "Unknown"
                    
                    # Determine opponent
                    opponent = [t for t in teams if t != team][0] if len(teams) == 2 else "Unknown"
                    
                    # Build row with round outcome columns
                    row = {
                        "stage": stage_label,
                        "map": map_name,
                        "team": team,
                        "player_name": player_name,
                        "player_steam_id": steamid,
                        "opponent": opponent,
                    }
                    
                    # Add round outcome columns (r_1_outcome, r_2_outcome, ..., r_MAX_ROUNDS_outcome)
                    for r in range(1, MAX_ROUNDS + 1):
                        if r <= total_rounds:
                            round_winner = winners_df[winners_df["round_num"] == r]
                            if not round_winner.empty:
                                winner_team = round_winner["winner_team"].iloc[0]
                                # Player wins if their team won the round
                                row[f"r_{r}_outcome"] = (winner_team == team)
                            else:
                                row[f"r_{r}_outcome"] = float("nan")
                        else:
                            row[f"r_{r}_outcome"] = float("nan")
                    
                    all_rows.append(row)

    # ---- Build and sort DataFrame ----------------------------------------
    df = pd.DataFrame(all_rows)

    # Sort: stage (alphabetical) → map → team → player_name
    df["_stage_sort"] = df["stage"].map(STAGE_SORT)
    df = (
        df.sort_values(by=["_stage_sort", "map", "team", "player_name"])
        .drop(columns=["_stage_sort"])
        .reset_index(drop=True)
    )

    # Boolean columns for all round outcome columns
    for r in range(1, MAX_ROUNDS + 1):
        col_name = f"r_{r}_outcome"
        if col_name in df.columns:
            df[col_name] = df[col_name].astype(bool)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nCSV written to: {OUTPUT_CSV}")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)[:10]}... (total {len(df.columns)} columns)")
    print(df.head().to_string())


if __name__ == "__main__":
    main()
