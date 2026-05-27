import numpy as np
import os
import pandas as pd
import plotly.graph_objects as go
from config import T_COLOR, CT_COLOR, BOTH_COLOR, WIN_COLOR, LOSS_COLOR, LINE_ALPHA

# Get script directory and resolve paths relative to it
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_economy.csv")
OUTCOMES_PATH = os.path.join(SCRIPT_DIR, "../../analysis_results/budapest_major_team_outcomes.csv")


def parse_round_range(range_str):
    """Parse '1-12, 28-30' or '13-24, 25-27' into list of round numbers."""
    if pd.isna(range_str) or not range_str or str(range_str).strip() == "":
        return []
    rounds = []
    parts = str(range_str).split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            rounds.extend(range(start, end + 1))
        elif part:
            rounds.append(int(part))
    return rounds


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


def hex_to_rgba(hex_color, alpha):
    """Convert hex color to rgba string with alpha."""
    hex_color = hex_color.lstrip('#')
    return f'rgba({int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}, {alpha})'


def combined_economy_line_plot(stage, map_name, team, show=True):
    """
    Plot combined economy for both teams with CT/T markers and round outcomes.
    Interactive Plotly version.

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

    fig = go.Figure()

    # Add team line with segmented win/loss colors (skip round 12-13 for halftime)
    for i in range(len(rounds) - 1):
        # Skip halftime and overtime start segments
        if (rounds[i] == 12 and rounds[i + 1] == 13) or (rounds[i] == 24 and rounds[i + 1] == 25) or (rounds[i] == 30 and rounds[i + 1] == 31):
            continue
        won_round = team_outcomes[f'r_{rounds[i]}_outcome'] if team_outcomes is not None else True
        segment_color = hex_to_rgba(WIN_COLOR if won_round else LOSS_COLOR, LINE_ALPHA)
        fig.add_trace(go.Scatter(
            x=[rounds[i], rounds[i + 1]],
            y=[team_cash[i], team_cash[i + 1]],
            mode='lines',
            line=dict(color=segment_color, width=2),
            hoverinfo='skip'
        ))

    # Add opponent line with segmented win/loss colors (skip round 12-13)
    for i in range(len(rounds) - 1):
        # Skip halftime and overtime start segments
        if (rounds[i] == 12 and rounds[i + 1] == 13) or (rounds[i] == 24 and rounds[i + 1] == 25) or (rounds[i] == 30 and rounds[i + 1] == 31):
            continue
        won_round = opponent_outcomes[f'r_{rounds[i]}_outcome'] if opponent_outcomes is not None else True
        segment_color = hex_to_rgba(WIN_COLOR if won_round else LOSS_COLOR, LINE_ALPHA)
        fig.add_trace(go.Scatter(
            x=[rounds[i], rounds[i + 1]],
            y=[opponent_cash[i], opponent_cash[i + 1]],
            mode='lines',
            line=dict(color=segment_color, width=2),
            hoverinfo='skip'
        ))

    # Add team markers with CT/T text and hover info
    team_marker_colors = []
    team_marker_text = []
    team_marker_hover = []
    for i, r in enumerate(rounds):
        side = get_side_for_round(team_outcomes['CT_rounds'], team_outcomes['T_rounds'], r) if team_outcomes is not None else None
        won = team_outcomes[f'r_{r}_outcome'] if team_outcomes is not None else True
        color = CT_COLOR if side == 'CT' else T_COLOR if side == 'T' else BOTH_COLOR
        team_marker_colors.append(color)
        team_marker_text.append(side if side else '')
        team_marker_hover.append(f'{team}<br>Round: {r}<br>Economy: ${team_cash[i]:,.0f}<br>Side: {side}<br>Result: {"Won" if won else "Lost"}')

    fig.add_trace(go.Scatter(
        x=rounds,
        y=team_cash,
        mode='markers+text',
        marker=dict(size=20, color=team_marker_colors, line=dict(width=2, color='white')),
        text=team_marker_text,
        textposition='middle center',
        textfont=dict(size=12, color='white', family='Arial Black'),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=team_marker_hover,
        showlegend=False,
        name=team
    ))

    # Add opponent markers with CT/T text and hover info
    opp_marker_colors = []
    opp_marker_text = []
    opp_marker_hover = []
    for i, r in enumerate(rounds):
        side = get_side_for_round(opponent_outcomes['CT_rounds'], opponent_outcomes['T_rounds'], r) if opponent_outcomes is not None else None
        won = opponent_outcomes[f'r_{r}_outcome'] if opponent_outcomes is not None else True
        color = CT_COLOR if side == 'CT' else T_COLOR if side == 'T' else BOTH_COLOR
        opp_marker_colors.append(color)
        opp_marker_text.append(side if side else '')
        opp_marker_hover.append(f'{opponent}<br>Round: {r}<br>Economy: ${opponent_cash[i]:,.0f}<br>Side: {side}<br>Result: {"Won" if won else "Lost"}')

    fig.add_trace(go.Scatter(
        x=rounds,
        y=opponent_cash,
        mode='markers+text',
        marker=dict(size=20, color=opp_marker_colors, line=dict(width=2, color='white')),
        text=opp_marker_text,
        textposition='middle center',
        textfont=dict(size=12, color='white', family='Arial Black'),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=opp_marker_hover,
        showlegend=False,
        name=opponent
    ))

    # Add vertical line at half time and overtime starts
    fig.add_vline(x=12.5, line_dash="dot", line_color="gray", line_width=2, opacity=0.7)
    if max(rounds) >= 25:
        fig.add_vline(x=24.5, line_dash="dot", line_color="gray", line_width=2, opacity=0.7)
    if max(rounds) >= 31:
        fig.add_vline(x=30.5, line_dash="dot", line_color="gray", line_width=2, opacity=0.7)

    # Update layout with proper axis ranges
    max_economy = max(max(team_cash), max(opponent_cash)) * 1.1 if team_cash and opponent_cash else 100000
    fig.update_layout(
        title=f'Economy Comparison: {team} vs {opponent} - {stage} on {map_name}',
        xaxis_title='Round',
        yaxis_title='Total Team Economy ($)',
        hovermode='closest',
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(range=[0.5, max(rounds) + 1.5]),
        yaxis=dict(range=[0, max_economy])
    )

    if show:
        fig.show()
    return fig


def main():
    """Main function to demonstrate the visualization."""
    combined_economy_line_plot("Final", "Dust2", "FaZe Clan")


if __name__ == "__main__":
    main()


def get_available_stages():
    """Return sorted list of available stages from the economy data."""
    df = pd.read_csv(DATA_PATH)
    return sorted(df['stage'].unique().tolist())


def get_available_maps(stage=None):
    """Return sorted list of available maps, optionally filtered by stage."""
    df = pd.read_csv(DATA_PATH)
    if stage is not None:
        df = df[df['stage'] == stage]
    return sorted(df['map'].unique().tolist())


def get_available_teams(stage=None, map_name=None):
    """Return sorted list of available teams, optionally filtered by stage and/or map."""
    df = pd.read_csv(DATA_PATH)
    if stage is not None:
        df = df[df['stage'] == stage]
    if map_name is not None:
        df = df[df['map'] == map_name]
    return sorted(df['team'].unique().tolist())
