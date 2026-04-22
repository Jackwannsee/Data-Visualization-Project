"""
Match visualization module for creating plots and charts from CS:GO demo data.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

class MatchVisualizer:
    """Class for creating visualizations from match data."""
    
    def __init__(self, match_data: dict):
        """Initialize with match data.
        
        Args:
            match_data: Dictionary containing match data from DemoAnalyzer
        """
        self.match_data = match_data
        self.players_df = pd.DataFrame(match_data['players'])
        
    def plot_team_scores(self, save_path: str = None):
        """Create a bar plot showing team scores.
        
        Args:
            save_path: Optional path to save the plot image
            
        Returns:
            matplotlib figure object
        """
        teams = ['Terrorists', 'Counter-Terrorists']
        scores = [self.match_data['t_score'], self.match_data['ct_score']]
        
        plt.figure(figsize=(8, 6))
        bars = plt.bar(teams, scores, color=['#FF4500', '#0066CC'])
        plt.title(f"Match Result: {self.match_data['map_name']}")
        plt.ylabel('Score')
        plt.ylim(0, max(scores) + 5)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
        
        return plt.gcf()
    
    def plot_player_kills(self, save_path: str = None):
        """Create a horizontal bar plot of player kills.
        
        Args:
            save_path: Optional path to save the plot image
            
        Returns:
            matplotlib figure object
        """
        plt.figure(figsize=(10, 8))
        
        # Sort players by kills
        sorted_players = self.players_df.sort_values('kills', ascending=False)
        
        # Create color mapping by team
        team_colors = {'T': '#FF4500', 'CT': '#0066CC'}
        colors = [team_colors.get(team, '#888888') for team in sorted_players['team']]
        
        bars = plt.barh(sorted_players['name'], sorted_players['kills'], color=colors)
        plt.title('Player Kills')
        plt.xlabel('Number of Kills')
        plt.gca().invert_yaxis()
        
        # Add kill values on bars
        for i, (bar, kills) in enumerate(zip(bars, sorted_players['kills'])):
            plt.text(kills, i, f' {kills}', va='center')
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
        
        return plt.gcf()
    
    def plot_kd_ratio(self, save_path: str = None):
        """Create a scatter plot of K/D ratio vs ADR.
        
        Args:
            save_path: Optional path to save the plot image
            
        Returns:
            matplotlib figure object
        """
        # Calculate K/D ratio
        self.players_df['kd_ratio'] = self.players_df['kills'] / self.players_df['deaths'].replace(0, 1)
        
        plt.figure(figsize=(10, 6))
        
        # Scatter plot with team colors
        for team in self.players_df['team'].unique():
            team_data = self.players_df[self.players_df['team'] == team]
            color = '#FF4500' if team == 'T' else '#0066CC'
            plt.scatter(team_data['adr'], team_data['kd_ratio'],
                       color=color, label=team, s=100, alpha=0.7)
            
            # Add player names
            for i, row in team_data.iterrows():
                plt.text(row['adr'], row['kd_ratio'], row['name'],
                        fontsize=9, ha='right', va='bottom')
        
        plt.title('Player Performance: K/D Ratio vs ADR')
        plt.xlabel('Average Damage per Round (ADR)')
        plt.ylabel('Kill/Death Ratio')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
        
        return plt.gcf()
    
    def create_interactive_heatmap(self):
        """Create an interactive heatmap of player positions using Plotly.
        
        Returns:
            plotly figure object
        """
        # This would be enhanced with actual position data
        # For now, create a placeholder with player stats
        
        # Create a pivot table for heatmap
        heatmap_data = self.players_df.pivot_table(
            values='adr', 
            index='name', 
            columns='team', 
            aggfunc='first'
        ).fillna(0)
        
        fig = px.imshow(heatmap_data,
                       labels=dict(x="Team", y="Player", color="ADR"),
                       title="Player ADR by Team",
                       color_continuous_scale='Viridis',
                       aspect='auto')
        
        return fig
