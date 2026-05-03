"""Parse CS2 .dem files for the Budapest Major and produce a player economy CSV."""

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
OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_economy.csv"

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


def get_player_starting_cash(demo: Demo) -> pd.DataFrame:
    """Extract starting cash per round for each player from a demo.
    
    Returns DataFrame with columns: steamid, name, round_num, starting_cash
    """
    # Parse with balance and team_clan_name
    ticks = demo.ticks.to_pandas()
    rounds = demo.rounds.to_pandas()
    
    if ticks.empty or rounds.empty:
        return pd.DataFrame(columns=["steamid", "name", "round_num", "starting_cash"])
    
    # Convert steamid to string for consistency
    ticks["steamid"] = ticks["steamid"].astype(str)
    
    # Merge ticks with rounds to get start tick for each round
    merged = ticks.merge(rounds[["round_num", "start"]], on="round_num", how="left")
    
    if merged.empty:
        return pd.DataFrame(columns=["steamid", "name", "round_num", "starting_cash"])
    
    # Calculate difference between tick and round start
    merged["diff"] = abs(merged["tick"] - merged["start"])
    
    # For each player and round, get the balance at the tick closest to round start
    idx = merged.groupby(["steamid", "name", "round_num"])["diff"].idxmin()
    start_balances = merged.loc[idx]
    
    result = start_balances[["steamid", "name", "round_num", "balance"]].rename(
        columns={"balance": "starting_cash"}
    )
    
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

                # Parse the demo with balance and team_clan_name
                demo = Demo(path=dem_path)
                demo.parse(player_props=["balance", "team_clan_name"])

                # Get starting cash per player per round
                cash_df = get_player_starting_cash(demo)
                
                # Get player to team mapping
                player_team_map = get_player_team_map(demo, teams)
                
                # Get total rounds in this map
                rounds_pd = demo.rounds.to_pandas()
                total_rounds = len(rounds_pd)
                
                # For each player, build their round cash
                for steamid, team in player_team_map.items():
                    # Ensure steamid is string for comparison
                    steamid = str(steamid)
                    # Get this player's cash data
                    player_cash = cash_df[cash_df["steamid"] == steamid]
                    
                    # Determine opponent
                    opponent = [t for t in teams if t != team][0] if len(teams) == 2 else "Unknown"
                    
                    # Build row with round cash columns
                    row = {
                        "stage": stage_label,
                        "map": map_name,
                        "team": team,
                        "player_name": player_cash["name"].iloc[0] if not player_cash.empty else "Unknown",
                        "player_steam_id": steamid,
                        "opponent": opponent,
                    }
                    
                    # Add round cash columns (r_1_cash, r_2_cash, ..., r_MAX_ROUNDS_cash)
                    for r in range(1, MAX_ROUNDS + 1):
                        if r <= total_rounds:
                            round_cash = player_cash[player_cash["round_num"] == r]
                            if not round_cash.empty:
                                row[f"r_{r}_cash"] = round_cash["starting_cash"].iloc[0]
                            else:
                                row[f"r_{r}_cash"] = float("nan")
                        else:
                            row[f"r_{r}_cash"] = float("nan")
                    
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

    # Numeric columns for all round cash columns
    for r in range(1, MAX_ROUNDS + 1):
        col_name = f"r_{r}_cash"
        if col_name in df.columns:
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nCSV written to: {OUTPUT_CSV}")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)[:10]}... (total {len(df.columns)} columns)")
    print(df.head().to_string())


if __name__ == "__main__":
    main()
