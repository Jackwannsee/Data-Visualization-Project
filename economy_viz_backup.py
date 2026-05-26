import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from config import T_COLOR, CT_COLOR, BOTH_COLOR, CT_LOGO_PATH, T_LOGO_PATH, LINE_COLOR_1, LINE_COLOR_2, WIN_COLOR, LOSS_COLOR

DATA_PATH = "../../analysis_results/budapest_major_economy.csv"
OUTCOMES_PATH = "../../analysis_results/budapest_major_team_outcomes.csv"


def parse_round_range(range_str):
    """Parse '1-12' or '13-24' into list of round numbers."""
    if pd.isna(range_str):
        return []
    start, end = map(int, range_str.split('-'))
    return list(range(start, end + 1))


def get_side_for_round(ct_rounds_str, t_rounds_str, round_num):
    """Return 'CT' or 'T' based on which range the round falls into."""
    ct_rounds = parse_round_range(ct_rounds_str)
    t_rounds = parse_round_range(t_rounds_str)
    if round_num in ct_rounds:
        return 'CT'
    elif round_num in t_rounds:
        return 'T'
    return None


def get_outcomes_row(outcomes_df, stage, map_name, team):
    """Get the outcomes row for a specific team, stage, and map."""
    matches = outcomes_df[(outcomes_df['stage'] == stage) & 
                         (outcomes_df['map'] == map_name) & 
                         (outcomes_df['team'] == team)]
    if len(matches) == 0:
        return None
    return matches.iloc[0]


def grayscale_logo(logo):
    """Convert RGBA logo to grayscale by averaging RGB channels."""
    # logo shape is (height, width, 4) for RGBA
    grayscale = np.mean(logo[:, :, :3], axis=2, keepdims=True)
    # Keep alpha channel
    result = np.dstack([grayscale, grayscale, grayscale, logo[:, :, 3]])
    return result


def add_logo_markers(ax, rounds, cash_values, outcomes_row, logo_zoom=0.08):
    """Add CT/T logo markers for a team's data points."""
    ct_logo = plt.imread(CT_LOGO_PATH)
    t_logo = plt.imread(T_LOGO_PATH)

    for i, round_num in enumerate(rounds):
        cash = cash_values[i]
        outcome_col = f'r_{round_num}_outcome'
        won_round = outcomes_row[outcome_col]

        side = get_side_for_round(outcomes_row['CT_rounds'], outcomes_row['T_rounds'], round_num)

        if side == 'CT':
            logo = ct_logo
        elif side == 'T':
            logo = t_logo
        else:
            continue

        # Gray out logo if team lost the round
        if not won_round:
            logo = grayscale_logo(logo)

        imagebox = OffsetImage(logo, zoom=logo_zoom)
        ab = AnnotationBbox(imagebox, (round_num, cash),
                           frameon=False,
                           box_alignment=(0.5, 0.5),
                           pad=0)
        ax.add_artist(ab)


def combined_economy_line_plot(stage, map_name, team):
    """
    Plot combined economy for both teams with logo markers and round outcomes.

    Args:
        stage (str): Match stage (e.g., "Final")
        map_name (str): Map name (e.g., "Dust2")
        team (str): Team name to focus on
    """
    economy_df = pd.read_csv(DATA_PATH)
    outcomes_df = pd.read_csv(OUTCOMES_PATH)

    team_data = economy_df[(economy_df['stage'] == stage) & 
                           (economy_df['map'] == map_name) & 
                           (economy_df['team'] == team)]
    if len(team_data) == 0:
        print(f"No data found for {team} on {map_name} at {stage}")
        return

    opponent = team_data.iloc[0]['opponent']
    opponent_data = economy_df[(economy_df['stage'] == stage) & 
                               (economy_df['map'] == map_name) & 
                               (economy_df['team'] == opponent)]

    team_outcomes = get_outcomes_row(outcomes_df, stage, map_name, team)
    opponent_outcomes = get_outcomes_row(outcomes_df, stage, map_name, opponent)

    round_cols = [col for col in economy_df.columns if col.startswith('r_') and col.endswith('_cash')]
    round_cols_sorted = sorted(round_cols, key=lambda x: int(x.split('_')[1]))

    max_round = 0
    for col in round_cols_sorted:
        round_num = int(col.split('_')[1])
        team_has_data = team_data[col].notna().any()
        opponent_has_data = opponent_data[col].notna().any()
        if team_has_data or opponent_has_data:
            max_round = round_num

    valid_round_cols = [col for col in round_cols_sorted if int(col.split('_')[1]) <= max_round]
    rounds = [int(col.split('_')[1]) for col in valid_round_cols]

    team_cash = [float(team_data[col].sum()) for col in valid_round_cols]
    opponent_cash = [float(opponent_data[col].sum()) for col in valid_round_cols]

    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot segmented lines with win/loss colors for team
    if team_outcomes is not None:
        for i in range(len(rounds) - 1):
            r1, r2 = rounds[i], rounds[i + 1]
            c1, c2 = team_cash[i], team_cash[i + 1]
            outcome_col = f'r_{r1}_outcome'
            won_round = team_outcomes[outcome_col]
            segment_color = WIN_COLOR if won_round else LOSS_COLOR
            ax.plot([r1, r2], [c1, c2], color=segment_color, linewidth=2)
        # Add to legend with first segment color
        ax.plot([], [], label=team, color=LINE_COLOR_1, linewidth=2)
    else:
        ax.plot(rounds, team_cash, label=team, color=LINE_COLOR_1, linewidth=2)

    # Plot segmented lines with win/loss colors for opponent
    if opponent_outcomes is not None:
        for i in range(len(rounds) - 1):
            r1, r2 = rounds[i], rounds[i + 1]
            c1, c2 = opponent_cash[i], opponent_cash[i + 1]
            outcome_col = f'r_{r1}_outcome'
            won_round = opponent_outcomes[outcome_col]
            segment_color = WIN_COLOR if won_round else LOSS_COLOR
            ax.plot([r1, r2], [c1, c2], color=segment_color, linewidth=2)
        # Add to legend with first segment color
        ax.plot([], [], label=opponent, color=LINE_COLOR_2, linewidth=2)
    else:
        ax.plot(rounds, opponent_cash, label=opponent, color=LINE_COLOR_2, linewidth=2)

    # Add logo markers for both teams
    if team_outcomes is not None:
        add_logo_markers(ax, rounds, team_cash, team_outcomes)
    if opponent_outcomes is not None:
        add_logo_markers(ax, rounds, opponent_cash, opponent_outcomes)

    ax.axvline(x=12.5, linestyle=':', color='gray', linewidth=2, alpha=0.7)

    ax.set_xlabel('Round')
    ax.set_ylabel('Total Team Economy ($)')
    ax.set_title(f'Economy Comparison: {team} vs {opponent} - {stage} on {map_name}')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def main():
    """Main function to demonstrate the visualization."""
    combined_economy_line_plot("Final", "Dust2", "FaZe Clan")


if __name__ == "__main__":
    main()
