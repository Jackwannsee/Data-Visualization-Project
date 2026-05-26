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
    """Extract round winner side from a demo.
    
    Returns DataFrame with columns: round_num, winner_side ("CT" or "T")
    """
    rounds = demo.rounds.to_pandas()
    
    if rounds.empty:
        return pd.DataFrame(columns=["round_num", "winner_side"])
    
    available_cols = rounds.columns.tolist()
    available_cols_lower = [c.lower() for c in available_cols]
    
    # Find round_num column
    round_num_col = None
    for candidate in ["round_num", "roundNum", "roundnum"]:
        if candidate in available_cols:
            round_num_col = candidate
            break
        if candidate.lower() in available_cols_lower:
            round_num_col = available_cols[available_cols_lower.index(candidate.lower())]
            break
    
    # Find winner column — prefer "winner" which contains "ct"/"t" side strings
    winner_col = None
    for candidate in ["winner", "winnerSide", "winnerside", "winner_side"]:
        if candidate in available_cols:
            winner_col = candidate
            break
        if candidate.lower() in available_cols_lower:
            winner_col = available_cols[available_cols_lower.index(candidate.lower())]
            break
    
    if round_num_col is None or winner_col is None:
        print(f"  WARNING: Could not find round columns. Available: {available_cols}")
        return pd.DataFrame(columns=["round_num", "winner_side"])
    
    result = rounds[[round_num_col, winner_col]].copy()
    result = result.rename(columns={round_num_col: "round_num", winner_col: "winner_side"})
    
    # Normalize winner_side to uppercase "CT" or "T"
    def normalize_side(s):
        if pd.isna(s):
            return "Unknown"
        s = str(s).upper().strip()
        if s in ["CT", "COUNTER", "COUNTERTERRORIST", "COUNTER TERRORIST", "COUNTER-TERRORIST"]:
            return "CT"
        elif s in ["T", "TERRORIST"]:
            return "T"
        return s
    
    result["winner_side"] = result["winner_side"].apply(normalize_side)
    result["round_num"] = result["round_num"].astype(int)
    
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

                # Parse the demo with team_clan_name and side
                demo = Demo(path=dem_path)
                demo.parse(player_props=["team_clan_name", "side"])

                # Get round winners (now returns winner_side: "CT" or "T")
                winners_df = get_round_winners(demo)
                
                # Get player to team mapping
                player_team_map = get_player_team_map(demo, teams)
                
                # Get total rounds in this map
                rounds_pd = demo.rounds.to_pandas()
                total_rounds = len(rounds_pd)
                
                # Get all ticks data once for name lookup
                ticks_data = demo.ticks.select(["steamid", "name"]).to_pandas()
                ticks_data["steamid"] = ticks_data["steamid"].astype(str)
                
                # Determine starting sides from round 1 ticks
                round1_ticks = demo.ticks.select(
                    ["steamid", "team_clan_name", "side"]
                ).to_pandas()
                round1_ticks = round1_ticks[
                    round1_ticks.get("round_num", pd.Series([1] * len(round1_ticks))) == 1
                ] if "round_num" not in round1_ticks.columns else round1_ticks
                
                # Try to get round_num for filtering
                try:
                    r1_ticks = demo.ticks.select(
                        ["steamid", "team_clan_name", "side", "round_num"]
                    ).to_pandas()
                    r1_ticks = r1_ticks[r1_ticks["round_num"] == 1]
                except Exception:
                    r1_ticks = demo.ticks.select(
                        ["steamid", "team_clan_name", "side"]
                    ).to_pandas()
                
                # Build team to starting side mapping
                def match_team_name(clan):
                    if pd.isna(clan):
                        return "Unknown"
                    clan_lower = str(clan).lower().strip()
                    for t in teams:
                        if clan_lower == t.lower().strip():
                            return t
                    for t in teams:
                        if clan_lower in t.lower() or t.lower() in clan_lower:
                            return t
                    return str(clan)
                
                def normalize_side(s):
                    if pd.isna(s):
                        return None
                    s = str(s).upper().strip()
                    if s in ["CT", "COUNTER", "COUNTERTERRORIST", "COUNTER TERRORIST"]:
                        return "CT"
                    elif s in ["T", "TERRORIST"]:
                        return "T"
                    return None
                
                team_starting_sides = {}
                if not r1_ticks.empty:
                    r1_ticks["_team"] = r1_ticks["team_clan_name"].apply(match_team_name)
                    r1_ticks["_side"] = r1_ticks["side"].apply(normalize_side)
                    for t in teams:
                        t_ticks = r1_ticks[r1_ticks["_team"] == t]
                        if not t_ticks.empty:
                            side_counts = t_ticks["_side"].value_counts()
                            if len(side_counts) > 0:
                                team_starting_sides[t] = side_counts.idxmax()
                
                # Default fallback
                for t in teams:
                    if t not in team_starting_sides:
                        team_starting_sides[t] = "CT" if teams.index(t) == 0 else "T"
                
                # Ensure both teams have different sides
                all_sides = list(team_starting_sides.values())
                if len(set(all_sides)) < len(all_sides):
                    for i, t in enumerate(teams):
                        team_starting_sides[t] = "CT" if i == 0 else "T"
                
                # Build per-half side-to-team mappings
                first_half_side_to_team = {side: t for t, side in team_starting_sides.items()}
                second_half_side_to_team = {
                    ("T" if side == "CT" else "CT"): t
                    for t, side in team_starting_sides.items()
                }
                
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
                                winner_side = round_winner["winner_side"].iloc[0]
                                # Use the correct mapping depending on half
                                if r <= 12:
                                    mapping = first_half_side_to_team
                                else:
                                    mapping = second_half_side_to_team
                                winning_team = mapping.get(winner_side, "")
                                # Player wins if their team won the round
                                row[f"r_{r}_outcome"] = (winning_team == team)
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
