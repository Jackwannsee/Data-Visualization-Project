"""
Demo file parser using AWPY library.
Handles extraction of match data from .dem files.
"""

import os
from awpy.demo import DemoParser
from awpy import Demo

class DemoAnalyzer:
    """Class to handle parsing and analysis of CS:GO demo files."""
    
    def __init__(self, demo_path: str):
        """Initialize with path to demo file.
        
        Args:
            demo_path: Path to the .dem file
        """
        self.demo_path = demo_path
        self.demo = None
        self.match_data = None
        
    def parse_demo(self) -> Demo:
        """Parse the demo file using AWPY.
        
        Returns:
            Parsed Demo object from AWPY
        """
        if not os.path.exists(self.demo_path):
            raise FileNotFoundError(f"Demo file not found: {self.demo_path}")
        
        self.demo = DemoParser(demo_file=self.demo_path, parse_rate=128)
        self.demo.parse()
        return self.demo
    
    def extract_match_data(self):
        """Extract key match data from parsed demo.
        
        Returns:
            Dictionary containing match metadata and statistics
        """
        if not self.demo:
            self.parse_demo()
        
        # Extract basic match information
        match_data = {
            'map_name': self.demo.game_info.map_name,
            'match_id': getattr(self.demo, 'match_id', 'unknown'),
            'date': self.demo.game_info.date,
            'duration': self.demo.game_info.game_length_seconds,
            't_score': self.demo.game_info.team_T_score,
            'ct_score': self.demo.game_info.team_CT_score,
            'players': []
        }
        
        # Extract player statistics
        for player in self.demo.players():
            player_data = {
                'steam_id': player.steam_id,
                'name': player.name,
                'team': player.team,
                'kills': player.kills,
                'deaths': player.deaths,
                'assists': player.assists,
                'hs_percentage': player.hsp,
                'adr': player.adr
            }
            match_data['players'].append(player_data)
        
        self.match_data = match_data
        return match_data
    
    def get_player_stats(self, steam_id: str = None, player_name: str = None):
        """Get statistics for a specific player.
        
        Args:
            steam_id: Steam ID of the player
            player_name: Name of the player
            
        Returns:
            Dictionary with player statistics
        """
        if not self.match_data:
            self.extract_match_data()
        
        for player in self.match_data['players']:
            if (steam_id and player['steam_id'] == steam_id) or \
               (player_name and player['name'] == player_name):
                return player
        
        return None
