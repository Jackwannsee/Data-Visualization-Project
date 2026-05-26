"""Parse CS2 .dem files for the Budapest Major and produce a team-level round outcome CSV."""

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
MATCH_DETAILS_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_match_details.csv"
OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_team_outcomes.csv"

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
    team_tokens = [tok for t in teams for tok in _team_tokens(t)]

    for dem in stage_dir.glob("*.dem"):
        stem = dem.stem.lower()
        if target_m not in stem or target_map not in stem:
            continue
        team1_match = any(tok in stem for tok in _team_tokens(teams[0]))
        team2_match = any(tok in stem for tok in _team_tokens(teams[1]))
        if team1_match and team2_match:
            return dem
        if any(tok in stem for tok in team_tokens):
            return dem
    return None


def load_match_details() -> dict:
    """Load match details CSV and create a lookup for starting sides and total rounds.
    
    Returns dict: (stage, map_name, team) -> {"starting_side": "CT"|"T", "total_rounds": int}
    """
    if not MATCH_DETAILS_CSV.exists():
        return {}
    
    df = pd.read_csv(MATCH_DETAILS_CSV)
    lookup = {}
    
    for _, row in df.iterrows():
        stage = row["stages"]
        map_name = row["map"]
        team = row["team"]
        side = row["side"]
        rounds_played = row["rounds_played"]
        
        key = (stage, map_name, team)
        
        if key not in lookup:
            lookup[key] = {"starting_side": None, "total_rounds": 0}
        
        # Determine starting side from which side has rounds_played data
        if pd.notna(rounds_played) and rounds_played > 0:
            if side == "Counter Terrorist":
                lookup[key]["starting_side"] = "CT"
                lookup[key]["total_rounds"] = int(rounds_played)
            elif side == "Terrorist" and lookup[key]["starting_side"] is None:
                lookup[key]["starting_side"] = "T"
                lookup[key]["total_rounds"] = int(rounds_played)
        
        # Also check "Both" side for total rounds
        if side == "Both" and pd.notna(rounds_played):
            lookup[key]["total_rounds"] = int(rounds_played)
    
    # For entries with no side determined, default to CT for first team
    for key in lookup:
        if lookup[key]["starting_side"] is None:
            lookup[key]["starting_side"] = "CT"
    
    return lookup


def get_round_winners(demo: Demo) -> pd.DataFrame:
    """Extract round winner side from a demo.
    
    Returns DataFrame with columns: round_num, winner_side ("CT" or "T")
    """
    rounds = demo.rounds.to_pandas()
    
    if rounds.empty:
        return pd.DataFrame(columns=["round_num", "winner_side"])
    
    # awpy rounds columns - winner is the side that won ("CT" or "T")
    available_cols = [c.lower() for c in rounds.columns.tolist()]
    
    round_num_col = None
    if "roundnum" in available_cols:
        round_num_col = rounds.columns[available_cols.index("roundnum")]
    elif "round_num" in available_cols:
        round_num_col = "round_num"
    
    winner_side_col = None
    # Try various possible column names for winner
    for col_name in ["winner", "winnerside", "winner_side", "winnername", "winner_name"]:
        if col_name in available_cols:
            idx = available_cols.index(col_name)
            winner_side_col = rounds.columns[idx]
            break
    
    if round_num_col is None or winner_side_col is None:
        print(f"  WARNING: Could not find round columns. Available: {rounds.columns.tolist()}")
        return pd.DataFrame(columns=["round_num", "winner_side"])
    
    result = rounds[[round_num_col, winner_side_col]].copy()
    
    # Rename to consistent names
    result = result.rename(columns={round_num_col: "round_num", winner_side_col: "winner_side"})
    
    # Clean up winner_side values (ensure they're "CT" or "T")
    result["winner_side"] = result["winner_side"].astype(str)
    
    # Normalize to uppercase and handle various formats
    def normalize_side(s):
        s = s.upper().strip()
        if s in ["CT", "COUNTER", "COUNTERTERROIST", "COUNTER TERRORIST", "COUNTER-TERRORIST"]:
            return "CT"
        elif s in ["T", "TERROIST", "TERRORIST"]:
            return "T"
        return s
    
    result["winner_side"] = result["winner_side"].apply(normalize_side)
    
    result["round_num"] = result["round_num"].astype(int)
    
    return result


def get_team_sides(demo: Demo, teams: list[str]) -> dict[str, str]:
    """Get the starting side (CT or T) for each team from demo ticks.
    
    Only looks at round 1 ticks to reliably determine starting sides,
    since sides swap at halftime (round 13).
    
    Returns dict: {team_name: "CT"|"T"}
    """
    ticks = demo.ticks.select(["steamid", "team_clan_name", "side", "round_num"]).to_pandas()
    if ticks.empty:
        # Fallback: return default CT for first team
        return {teams[0]: "CT", teams[1]: "T"} if len(teams) >= 2 else {}
    
    # Filter to round 1 only for reliable starting-side detection
    ticks = ticks[ticks["round_num"] == 1]
    if ticks.empty:
        return {teams[0]: "CT", teams[1]: "T"} if len(teams) >= 2 else {}
    
    # Convert steamid to string
    ticks["steamid"] = ticks["steamid"].astype(str)
    
    # Map clan name to JSON team name
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
    
    # Get the side for each team
    team_sides = {}
    
    # Normalize side values
    def normalize_side(s):
        if pd.isna(s):
            return None
        s = str(s).upper().strip()
        if s in ["CT", "COUNTER", "COUNTERTERROIST", "COUNTER TERRORIST", "COUNTER-TERRORIST"]:
            return "CT"
        elif s in ["T", "TERROIST", "TERRORIST"]:
            return "T"
        return None
    
    ticks["side_norm"] = ticks["side"].apply(normalize_side)
    
    for team in teams:
        team_ticks = ticks[ticks["team"] == team]
        if not team_ticks.empty:
            # Get the most common normalized side for this team in round 1
            side_counts = team_ticks["side_norm"].value_counts()
            if len(side_counts) > 0:
                side = side_counts.idxmax()
                team_sides[team] = side if side in ["CT", "T"] else "CT"
    
    # If we couldn't determine for all teams, use defaults
    for team in teams:
        if team not in team_sides:
            team_sides[team] = "CT"
    
    return team_sides


def get_side_for_round(starting_side: str, r: int) -> str:
    """Determine the side (CT or T) for a team in a given round.
    
    Halftime switch at round 12.
    First overtime starts at round 25, side switch every 3 rounds.
    Teams swap starting overtime sides each overtime (OT1 starts on same side as 2nd half).
    """
    if r <= 12:
        return starting_side
    elif r <= 24:
        return "T" if starting_side == "CT" else "CT"
    else:  # Overtime (r >= 25)
        side_before_ot = "T" if starting_side == "CT" else "CT"
        ot_round = r - 25
        ot_num = ot_round // 6
        ot_half_round = ot_round % 6
        
        # If even OT number (OT1, OT3, ...), first half is side_before_ot, second half is opposite
        # If odd OT number (OT2, OT4, ...), first half is opposite, second half is side_before_ot
        is_opposite = (ot_half_round >= 3) ^ (ot_num % 2 == 1)
        
        if is_opposite:
            return "CT" if side_before_ot == "T" else "T"
        else:
            return side_before_ot


def format_ranges(rounds: list[int]) -> str:
    """Format a list of sorted integers into a comma-separated list of ranges (e.g. '1-12,28-30')."""
    if not rounds:
        return ""
    ranges = []
    start = rounds[0]
    prev = rounds[0]
    
    for r in rounds[1:]:
        if r == prev + 1:
            prev = r
        else:
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{prev}")
            start = r
            prev = r
            
    if start == prev:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{prev}")
        
    return ",".join(ranges)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Load tournament structure
    with open(JSON_PATH, encoding="utf-8") as f:
        tournament = json.load(f)

    # Load match details for side determination
    match_details_lookup = load_match_details()

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

                # Parse the demo with player properties
                demo = Demo(path=dem_path)
                demo.parse(player_props=["team_clan_name", "side"])

                # Get round winners
                winners_df = get_round_winners(demo)
                
                # Get total rounds from demo
                rounds_pd = demo.rounds.to_pandas()
                total_rounds = len(rounds_pd)
                

                
                if total_rounds == 0:
                    print(f"  WARNING: No rounds found in demo")
                    continue
                
                # Get starting sides for each team
                # First try from match details lookup for all teams at once
                team_sides = {}
                sides_from_lookup = {}
                sides_from_demo = None
                
                for team in teams:
                    lookup_key = (stage_label, map_name, team)
                    if lookup_key in match_details_lookup:
                        side_info = match_details_lookup[lookup_key]
                        side = side_info.get("starting_side")
                        if side == "Counter Terrorist":
                            sides_from_lookup[team] = "CT"
                        elif side == "Terrorist":
                            sides_from_lookup[team] = "T"
                        elif side in ["CT", "T"]:
                            sides_from_lookup[team] = side
                
                # Get sides from demo if any team is missing from lookup
                if len(sides_from_lookup) < len(teams):
                    sides_from_demo = get_team_sides(demo, teams)
                
                # Build final team_sides dict
                for team in teams:
                    if team in sides_from_lookup:
                        team_sides[team] = sides_from_lookup[team]
                    elif sides_from_demo and team in sides_from_demo:
                        team_sides[team] = sides_from_demo[team]
                    else:
                        # Default: first team is CT, second is T
                        team_sides[team] = "CT" if teams.index(team) == 0 else "T"
                
                # Ensure both teams have different sides
                all_sides = list(team_sides.values())
                if len(set(all_sides)) < len(all_sides):
                    # If both teams have same side, force first to CT, second to T
                    for i, team in enumerate(teams):
                        team_sides[team] = "CT" if i == 0 else "T"
                
                # For each team, build their round outcomes
                for team in teams:
                    opponent = [t for t in teams if t != team][0] if len(teams) == 2 else "Unknown"
                    starting_side = team_sides.get(team, "CT")
                    
                    # Build row
                    row = {
                        "stage": stage_label,
                        "map": map_name,
                        "team": team,
                        "opponent": opponent,
                    }
                    
                    # Add CT_rounds and T_rounds
                    ct_rounds_list = []
                    t_rounds_list = []
                    for r in range(1, total_rounds + 1):
                        side = get_side_for_round(starting_side, r)
                        if side == "CT":
                            ct_rounds_list.append(r)
                        elif side == "T":
                            t_rounds_list.append(r)
                    
                    row["CT_rounds"] = format_ranges(ct_rounds_list)
                    row["T_rounds"] = format_ranges(t_rounds_list)

                    # Add round outcome columns
                    for r in range(1, MAX_ROUNDS + 1):
                        if r <= total_rounds:
                            round_winner = winners_df[winners_df["round_num"] == r]
                            if not round_winner.empty:
                                winner_side = round_winner["winner_side"].iloc[0]
                                team_side = get_side_for_round(starting_side, r)
                                row[f"r_{r}_outcome"] = (winner_side == team_side)
                            else:
                                row[f"r_{r}_outcome"] = float("nan")
                        else:
                            row[f"r_{r}_outcome"] = float("nan")
                    
                    all_rows.append(row)

    # ---- Build and sort DataFrame ----------------------------------------
    df = pd.DataFrame(all_rows)

    if df.empty:
        print("No data to write")
        return

    # Sort: stage (alphabetical) → map → team
    df["_stage_sort"] = df["stage"].map(STAGE_SORT)
    df = (
        df.sort_values(by=["_stage_sort", "map", "team"])
        .drop(columns=["_stage_sort"])
        .reset_index(drop=True)
    )

    # Boolean columns for all round outcome columns
    for r in range(1, MAX_ROUNDS + 1):
        col_name = f"r_{r}_outcome"
        if col_name in df.columns:
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce").fillna(False).astype(bool)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nCSV written to: {OUTPUT_CSV}")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)[:10]}... (total {len(df.columns)} columns)")
    print(df.head().to_string())


if __name__ == "__main__":
    main()
