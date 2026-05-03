"""Parse CS2 .dem files for the Budapest Major and produce a match details CSV."""

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
OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_match_details.csv"

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


def parse_match_details(demo: Demo, teams: list[str]) -> pd.DataFrame:
    """Return per-team per-side details DataFrame from a parsed Demo object.

    Columns: team, side, rounds_played, rounds_won
    
    For each team on each map:
    - CT row: stats when team was on CT side (or NaN if team was T)
    - T row: stats when team was on T side (or NaN if team was CT)
    - Both row: combined stats for the team on this map
    """
    # Get team to side mapping from demo
    ticks_with_team = demo.ticks.select(["steamid", "team_clan_name", "side"]).to_pandas()
    
    # Build team_clan_name to side mapping
    team_clan_to_side = {}
    if not ticks_with_team.empty:
        team_side = (
            ticks_with_team.groupby("team_clan_name")["side"]
            .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "")
            .reset_index()
        )
        team_clan_to_side = {row["team_clan_name"]: row["side"] for _, row in team_side.iterrows()}
    
    # Match JSON team names to clan names from demo
    def match_team(demo_team: str) -> str:
        """Match demo team clan name to JSON team name."""
        demo_lower = demo_team.lower().strip()
        for team in teams:
            if demo_lower == team.lower().strip():
                return team
        # Partial match fallback
        for team in teams:
            team_lower = team.lower()
            if demo_lower in team_lower or team_lower in demo_lower:
                return team
        return demo_team
    
    # Build JSON team name to side mapping
    json_team_to_side = {}
    for demo_team, side in team_clan_to_side.items():
        json_team = match_team(demo_team)
        json_team_to_side[json_team] = side
    
    # Get rounds data
    rounds_pd = demo.rounds.to_pandas()
    total_rounds = len(rounds_pd)
    
    # Count rounds won per side
    rounds_won_by_side = rounds_pd["winner"].value_counts().to_dict()
    ct_won = rounds_won_by_side.get("ct", 0)
    t_won = rounds_won_by_side.get("t", 0)
    
    # Build result rows
    rows = []
    for team in teams:
        # Determine which side this team was on in the demo
        team_side = json_team_to_side.get(team)
        
        # CT row: only has data if team was CT
        if team_side == "ct":
            ct_rounds_played = total_rounds
            ct_rounds_won = ct_won
        else:
            ct_rounds_played = float("nan")
            ct_rounds_won = float("nan")
        
        # T row: only has data if team was T
        if team_side == "t":
            t_rounds_played = total_rounds
            t_rounds_won = t_won
        else:
            t_rounds_played = float("nan")
            t_rounds_won = float("nan")
        
        # Both row: team's total on this map (whichever side they were on)
        if team_side == "ct":
            both_rounds_played = total_rounds
            both_rounds_won = ct_won
        elif team_side == "t":
            both_rounds_played = total_rounds
            both_rounds_won = t_won
        else:
            both_rounds_played = float("nan")
            both_rounds_won = float("nan")
        
        rows.append({
            "team": team,
            "side": "Counter Terrorist",
            "rounds_played": ct_rounds_played,
            "rounds_won": ct_rounds_won,
        })
        
        rows.append({
            "team": team,
            "side": "Terrorist",
            "rounds_played": t_rounds_played,
            "rounds_won": t_rounds_won,
        })
        
        rows.append({
            "team": team,
            "side": "Both",
            "rounds_played": both_rounds_played,
            "rounds_won": both_rounds_won,
        })
    
    return pd.DataFrame(rows)


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
            total_maps_played = match.get("total_maps_played", 0)
            overall_winner = match.get("overall_winner", "")
            overall_score = match.get("overall_score", "")

            for map_info in match["maps_played"]:
                map_num = map_info["map_number"]
                map_name = map_info["map_name"]
                map_winner = map_info.get("winner", "")
                map_score = map_info.get("score", "")

                dem_path = find_dem_file(stage_key, map_num, map_name, teams)
                if dem_path is None:
                    print(f"  WARNING: No .dem found for {stage_key} m{map_num} {map_name}")
                    continue

                print(f"  Parsing: {dem_path.name}")

                # Parse the demo fully with team_clan_name
                demo = Demo(path=dem_path)
                demo.parse(player_props=["team_clan_name"])

                # Get per-team per-side details
                details_df = parse_match_details(demo, teams)

                # Build rows for each team/side combination
                for _, row in details_df.iterrows():
                    team = row["team"]
                    side = row["side"]
                    rounds_played = row["rounds_played"]
                    rounds_won = row["rounds_won"]

                    # Determine opponent
                    opponent = [t for t in teams if t != team][0] if len(teams) == 2 else "Unknown"

                    # Determine if team won the game (match)
                    game_won = (team == overall_winner)

                    # Determine if team won this map
                    map_won = (team == map_winner)

                    all_rows.append({
                        "stages": stage_label,
                        "map": map_name,
                        "team": team,
                        "opponent": opponent,
                        "side": side,
                        "rounds_played": rounds_played,
                        "rounds_won": rounds_won,
                        "game_won": game_won,
                        "map_won": map_won,
                        "map_number": map_num,
                        "final_score": map_score,
                        "total_maps_played": total_maps_played,
                    })

    # ---- Build and sort DataFrame ----------------------------------------
    df = pd.DataFrame(all_rows)

    # Sort: stage (alphabetical) → map → team → side order
    side_order = {"Counter Terrorist": 0, "Terrorist": 1, "Both": 2}
    df["_stage_sort"] = df["stages"].map(STAGE_SORT)
    df["_side_sort"] = df["side"].map(side_order)
    df = (
        df.sort_values(by=["_stage_sort", "map", "team", "_side_sort"])
        .drop(columns=["_stage_sort", "_side_sort"])
        .reset_index(drop=True)
    )

    # Numeric columns
    df["rounds_played"] = pd.to_numeric(df["rounds_played"], errors="coerce")
    df["rounds_won"] = pd.to_numeric(df["rounds_won"], errors="coerce")
    df["map_number"] = pd.to_numeric(df["map_number"], errors="coerce")
    df["total_maps_played"] = pd.to_numeric(df["total_maps_played"], errors="coerce")

    # Boolean column
    df["game_won"] = df["game_won"].astype(bool)
    df["map_won"] = df["map_won"].astype(bool)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nCSV written to: {OUTPUT_CSV}")
    print(f"Total rows: {len(df)}")
    print(df.head(20).to_string())


if __name__ == "__main__":
    main()
