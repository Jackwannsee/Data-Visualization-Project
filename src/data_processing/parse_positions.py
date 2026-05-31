"""Parse CS2 .dem files for the Budapest Major and extract player position data.

Produces analysis_results/budapest_major_positions.csv with binned position counts
for heatmap visualization.
"""

import json
from pathlib import Path

import pandas as pd
from awpy import Demo
from awpy.data.map_data import MAP_DATA

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEM_DIR = PROJECT_ROOT / "dem_files"
JSON_PATH = PROJECT_ROOT / "src" / "budapest_major.json"
OUTPUT_CSV = PROJECT_ROOT / "analysis_results" / "budapest_major_positions.csv"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DOWNSAMPLE_FACTOR = 16  # 128 ticks/s -> 8 samples/s
BASE_GRANULARITY = 25   # Finest bin size in game units

# ---------------------------------------------------------------------------
# Stage label normalisation: JSON key -> CSV label
# ---------------------------------------------------------------------------
STAGE_LABEL = {
    "Quarterfinals": "Quarterfinals",
    "Semifinals": "Semifinals",
    "Final": "Final",
}

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


# ---------------------------------------------------------------------------
# Position extraction
# ---------------------------------------------------------------------------
def parse_positions_from_demo(
    dem_path: Path,
    map_display_name: str,
    granularity: int = BASE_GRANULARITY,
) -> pd.DataFrame:
    """Extract and bin player positions from a single demo file.

    Returns an aggregated DataFrame with columns:
        side, level, x_bin, y_bin, count
    """
    demo = Demo(path=dem_path)
    demo.parse()

    # Convert Polars -> pandas
    ticks = demo.ticks.to_pandas()

    # Downsample
    ticks = ticks.iloc[::DOWNSAMPLE_FACTOR].reset_index(drop=True)

    # Filter: alive, known side
    ticks = ticks[ticks['health'] > 0]
    ticks = ticks[ticks['side'].notna()]

    # Exclude buy period (freeze time) using round freeze_end timestamps
    # freeze_end is the tick when players can move freely after buy
    if demo.rounds is not None:
        rounds = demo.rounds.to_pandas()
        # Build a mapping: round_num -> freeze_end tick
        freeze_map = dict(zip(rounds['round_num'], rounds['freeze_end']))
        # Keep only ticks after freeze_end for their round
        ticks['freeze_end'] = ticks['round_num'].map(freeze_map)
        ticks = ticks[ticks['tick'] > ticks['freeze_end']]
        ticks = ticks.drop(columns=['freeze_end'])

    # Determine map key (e.g. "Nuke" -> "de_nuke")
    map_key = f"de_{map_display_name.lower()}"
    meta = MAP_DATA[map_key]
    z_threshold = meta['lower_level_max_units']

    # Assign level
    ticks['level'] = ticks['Z'].apply(
        lambda z: 'lower' if z <= z_threshold else 'upper'
    )

    # Bin coordinates
    ticks['x_bin'] = (ticks['X'] // granularity * granularity).astype(int)
    ticks['y_bin'] = (ticks['Y'] // granularity * granularity).astype(int)

    # Aggregate
    result = ticks.groupby(['side', 'level', 'x_bin', 'y_bin']).size().reset_index(name='count')
    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main():
    """Parse all demos and produce the positions CSV."""
    # Load tournament data
    with open(JSON_PATH, 'r') as f:
        tournament = json.load(f)

    all_frames = []

    for stage_key, stage_data in tournament['stages'].items():
        for match in stage_data:
            teams = match['teams_played']
            teams_str = f"{teams[0]} vs {teams[1]}"

            for map_num, map_entry in enumerate(match['maps_played'], start=1):
                map_name = map_entry['map_name']  # display name: "Nuke", "Dust2", etc.

                dem_path = find_dem_file(stage_key, map_num, map_name, teams)
                if dem_path is None:
                    print(f"  SKIP: {stage_key} {map_name} ({teams_str}) — no demo found")
                    continue

                print(f"  Parsing: {stage_key} {map_name} ({teams_str}) -> {dem_path.name}")

                df = parse_positions_from_demo(dem_path, map_name)

                # Add metadata
                df['stages'] = STAGE_LABEL.get(stage_key, stage_key)
                df['map'] = map_name
                df['teams'] = teams_str

                all_frames.append(df)

    if not all_frames:
        print("No data extracted. Check demo file paths.")
        return

    result = pd.concat(all_frames, ignore_index=True)

    # Ensure column order
    result = result[[
        'stages', 'map', 'teams', 'side', 'level',
        'x_bin', 'y_bin', 'count'
    ]]

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(result)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
