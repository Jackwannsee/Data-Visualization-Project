"""
Tournament-wide player performance analyzer using AWPY.
Extracts and aggregates comprehensive player metrics across all matches.
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from awpy.demo import DemoParser
from awpy import Demo

class TournamentAnalyzer:
    """Analyzes player performance across an entire tournament using AWPY."""
    
    def __init__(self, tournament_json_path: str, demos_base_path: str = "dem_files"):
        self.tournament_data = self._load_tournament_data(tournament_json_path)
        self.demos_base_path = demos_base_path
        self.all_player_stats = []
        self.all_match_data = []
        
    def _load_tournament_data(self, json_path: str) -> Dict:
        """Load tournament structure from JSON file."""
        with open(json_path, 'r') as f:
            return json.load(f)
    
    def _find_demo_file(self, stage: str, teams: List[str], map_name: str, map_number: int = 1) -> Optional[str]:
        """Find the corresponding demo file for a match."""
        # Create search pattern based on team names and map
        team_names = [team.lower().replace(" ", "-") for team in teams]
        
        # Handle team name variations
        team_name_map = {
            'team-spirit': 'spirit',
            'team-vitality': 'vitality',
            'team-falcons': 'falcons',
            'the-mongolz': 'mongolz',
            'faze-clan': 'faze',
            'natus-vincere': 'natus-vincere',
            'mouz': 'mouz',
            'furia-esports': 'furia'
        }
        
        # Map team names to their short forms
        short_team_names = []
        for team in team_names:
            short_name = team_name_map.get(team, team)
            short_team_names.append(short_name)
        
        # Generate search patterns - the demos use format like "spirit-vs-vitality-m1-mirage.dem"
        # Try both team orders and specific map numbers
        search_patterns = []
        
        # Pattern 1: team1-vs-team2-mX-mapname.dem
        search_patterns.append(f"{short_team_names[0]}-vs-{short_team_names[1]}-m{map_number}-{map_name.lower()}")
        
        # Pattern 2: team2-vs-team1-mX-mapname.dem (reverse order)
        search_patterns.append(f"{short_team_names[1]}-vs-{short_team_names[0]}-m{map_number}-{map_name.lower()}")
        
        # Pattern 3: team1-vs-team2-mX.dem (any map)
        search_patterns.append(f"{short_team_names[0]}-vs-{short_team_names[1]}-m{map_number}")
        
        # Pattern 4: team2-vs-team1-mX.dem (reverse order, any map)
        search_patterns.append(f"{short_team_names[1]}-vs-{short_team_names[0]}-m{map_number}")

        stage_path = os.path.join(self.demos_base_path, stage)
        if not os.path.exists(stage_path):
            print(f"⚠️ Stage directory not found: {stage_path}")
            return None

        # Look for exact matches first
        for pattern in search_patterns:
            for filename in os.listdir(stage_path):
                if filename.lower().endswith('.dem') and pattern in filename.lower():
                    return os.path.join(stage_path, filename)

        # If no exact match, try more flexible matching
        for filename in os.listdir(stage_path):
            if filename.lower().endswith('.dem'):
                # Check if both team names are in the filename (in any order)
                if (short_team_names[0] in filename.lower() and 
                    short_team_names[1] in filename.lower()):
                    return os.path.join(stage_path, filename)

        return None
    
    def _parse_demo_with_awpy(self, demo_path: str) -> Optional[Demo]:
        """Parse demo file using AWPY."""
        try:
            if not os.path.exists(demo_path):
                print(f"❌ Demo file not found: {demo_path}")
                return None
            
            # Use the new AWPY API
            from pathlib import Path
            demo = Demo(Path(demo_path), tickrate=128)
            demo.parse()
            return demo
        except Exception as e:
            print(f"❌ Error parsing {demo_path}: {str(e)}")
            return None
    
    def _extract_player_stats(self, demo: Demo, match_context: Dict) -> List[Dict]:
        """Extract comprehensive player statistics from parsed demo using new AWPY API."""
        player_stats = []
        
        # Get player round totals (contains basic player info)
        player_round_totals = demo.player_round_totals
        
        # Get kills data
        kills_df = demo.kills
        
        # Get damages data
        damages_df = demo.damages
        
        # Calculate statistics for each player
        for row in player_round_totals.iter_rows(named=True):
            player_name = row['name']
            steamid = row['steamid']
            side = row['side']
            
            # Get team name based on side
            team_name = match_context['teams'][0] if side == 't' else match_context['teams'][1]
            opponent_team = self._get_opponent_team(team_name, match_context['teams'])
            
            # Calculate basic statistics from kills data
            player_kills = kills_df.filter(kills_df['attacker_name'] == player_name)
            player_deaths = kills_df.filter(kills_df['victim_name'] == player_name)
            
            kills = len(player_kills)
            deaths = len(player_deaths)
            
            # Calculate assists (count unique rounds where player assisted)
            assists = len(player_kills.filter(player_kills['assistedflash'] == True).unique('round_num'))
            
            # Calculate headshot percentage
            hs_kills = len(player_kills.filter(player_kills['headshot'] == True))
            hs_percentage = round((hs_kills / kills * 100) if kills > 0 else 0, 1)
            
            # Calculate ADR (average damage per round)
            player_damage = damages_df.filter(damages_df['attacker_name'] == player_name)
            total_damage = player_damage['dmg_health'].sum() if len(player_damage) > 0 else 0
            adr = round(total_damage / row['n_rounds'] if row['n_rounds'] > 0 else 0, 1)
            
            # Calculate K/D ratio
            kd_ratio = round(kills / deaths, 2) if deaths > 0 else kills
            kd_diff = kills - deaths
            
            player_data = {
                # Match context
                'stage': match_context['stage'],
                'match_type': self._get_match_type(match_context['stage']),
                'player_name': player_name,
                'player_steamid': steamid,
                'team': team_name,
                'opponent_team': opponent_team,
                'map_name': match_context['map_name'],
                'match_result': match_context['result'],
                'demo_file': match_context['demo_file'],
                
                # Basic performance metrics
                'kills': kills,
                'deaths': deaths,
                'assists': assists,
                'hs_percentage': hs_percentage,
                'adr': adr,
                'kast': 0,  # Would need round-by-round data to calculate properly
                'rating_2': 0,  # Would need more complex calculation
                
                # Calculated metrics
                'kd_ratio': kd_ratio,
                'kd_diff': kd_diff,
                
                # Utility statistics (simplified for now)
                'total_utility_damage': 0,
                'flashbang_damage': 0,
                'he_grenade_damage': 0,
                'smoke_grenade_damage': 0,
                'molotov_fire_damage': 0,
                'decoy_damage': 0,
                'total_enemies_flashed': 0,
                
                # Economy metrics
                'money_spent': 0,
                'bomb_plants': 0,
                'bomb_defuses': 0,
                
                # Weapon statistics (simplified)
                'pistol_kills': len(player_kills.filter(player_kills['weapon'].str.contains('Pistol'))),
                'rifle_kills': len(player_kills.filter(player_kills['weapon'].str.contains('Rifle'))),
                'sniper_kills': len(player_kills.filter(player_kills['weapon'].str.contains('Sniper'))),
                'smg_kills': len(player_kills.filter(player_kills['weapon'].str.contains('SMG'))),
                'shotgun_kills': len(player_kills.filter(player_kills['weapon'].str.contains('Shotgun'))),
                'knife_kills': len(player_kills.filter(player_kills['weapon'].str.contains('Knife'))),
                'grenade_kills': len(player_kills.filter(player_kills['weapon'].str.contains('Grenade'))),
                
                # Weapon accuracy (simplified)
                'rifle_accuracy': 0,
                'pistol_accuracy': 0,
                'awp_accuracy': 0,
                
                # Round impact metrics
                'first_kills': 0,
                'first_deaths': 0,
                'clutch_attempts': 0,
                'clutch_wins': 0,
                
                # Additional metrics
                'trade_kills': 0,
                'trade_deaths': 0,
                'enemies_flashed': 0,
                'team_mates_flashed': 0
            }
            
            player_stats.append(player_data)
        
        return player_stats
    
    def _get_match_type(self, stage: str) -> str:
        """Get match type based on tournament stage."""
        stage_map = {
            'Quarterfinals': 'quarterfinal',
            'Semifinals': 'semifinal',
            'Final': 'final'
        }
        return stage_map.get(stage, stage.lower())
    
    def _get_opponent_team(self, player_team: str, teams: List[str]) -> str:
        """Get the opponent team name."""
        return teams[1] if player_team == teams[0] else teams[0]
    
    def analyze_tournament(self) -> pd.DataFrame:
        """Analyze all matches in the tournament and return comprehensive player stats."""
        print("🔍 Starting comprehensive tournament analysis...")
        
        # Process each stage
        for stage_name, matches in self.tournament_data['stages'].items():
            print(f"📁 Processing {stage_name}...")
            
            for match in matches:
                teams = match['teams_played']
                
                # Process each map in the match
                for map_info in match['maps_played']:
                    map_name = map_info['map_name']
                    result = map_info['score']
                    map_number = map_info['map_number']
                    
                    # Find the demo file
                    demo_path = self._find_demo_file(stage_name, teams, map_name, map_number)
                    if not demo_path:
                        print(f"⚠️ Demo not found for {teams[0]} vs {teams[1]} on {map_name} (map {map_number})")
                        continue
                    
                    print(f"🎮 Processing: {teams[0]} vs {teams[1]} on {map_name} ({os.path.basename(demo_path)})")
                    
                    # Parse demo with AWPY
                    demo = self._parse_demo_with_awpy(demo_path)
                    if not demo:
                        continue
                    
                    # Extract player stats with full context
                    player_stats = self._extract_player_stats(demo, {
                        'stage': stage_name,
                        'teams': teams,
                        'map_name': map_name,
                        'result': result,
                        'demo_file': os.path.basename(demo_path)
                    })
                    
                    if player_stats:
                        self.all_player_stats.extend(player_stats)
                        
                        # Store match-level data
                        # Calculate scores from rounds data
                        t_wins = len(demo.rounds.filter(demo.rounds['winner'] == 't'))
                        ct_wins = len(demo.rounds.filter(demo.rounds['winner'] == 'ct'))
                        
                        # Get duration from rounds
                        if len(demo.rounds) > 0:
                            duration_seconds = demo.rounds['end'].max() / demo.tickrate
                        else:
                            duration_seconds = 0
                        
                        match_data = {
                            'stage': stage_name,
                            'match_type': self._get_match_type(stage_name),
                            'teams': f"{teams[0]} vs {teams[1]}",
                            'map_name': map_name,
                            'result': result,
                            'demo_file': os.path.basename(demo_path),
                            't_score': t_wins,
                            'ct_score': ct_wins,
                            'duration_seconds': duration_seconds,
                            'date': demo.header.get('demo_file_stamp', 'unknown')
                        }
                        self.all_match_data.append(match_data)
        
        # Convert to DataFrame
        if self.all_player_stats:
            df = pd.DataFrame(self.all_player_stats)
            
            # Clean up data types
            df['kd_ratio'] = pd.to_numeric(df['kd_ratio'], errors='coerce')
            df['hs_percentage'] = pd.to_numeric(df['hs_percentage'], errors='coerce')
            df['adr'] = pd.to_numeric(df['adr'], errors='coerce')
            
            print(f"✅ Successfully analyzed {len(df)} player performances across {len(self.all_match_data)} matches")
            return df
        else:
            print("❌ No player data extracted. Check demo files and paths.")
            return pd.DataFrame()
    
    def save_results(self, output_path: str = "tournament_analysis.csv"):
        """Save analysis results to CSV."""
        if not self.all_player_stats:
            print("❌ No data to save. Run analyze_tournament() first.")
            return
        
        df = pd.DataFrame(self.all_player_stats)
        df.to_csv(output_path, index=False)
        print(f"✅ Results saved to {output_path}")
        
        # Also save match data
        if self.all_match_data:
            match_df = pd.DataFrame(self.all_match_data)
            match_output = output_path.replace('.csv', '_matches.csv')
            match_df.to_csv(match_output, index=False)
            print(f"✅ Match data saved to {match_output}")
    
    def get_top_performers(self, n: int = 10, metric: str = 'kd_ratio') -> pd.DataFrame:
        """Get top performers by specified metric."""
        if not self.all_player_stats:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.all_player_stats)
        valid_metrics = ['kd_ratio', 'adr', 'hs_percentage', 'rating_2', 'kills']
        
        if metric not in valid_metrics:
            print(f"⚠️ Invalid metric. Using 'kd_ratio'. Valid options: {valid_metrics}")
            metric = 'kd_ratio'
        
        return df.nlargest(n, metric)
    
    def get_team_performance(self, team_name: str) -> pd.DataFrame:
        """Get performance metrics for a specific team."""
        if not self.all_player_stats:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.all_player_stats)
        # Filter by team name (case insensitive)
        return df[df['team'].str.contains(team_name, case=False, na=False)]
    
    def get_player_career_stats(self, player_name: str) -> pd.DataFrame:
        """Get all performances for a specific player."""
        if not self.all_player_stats:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.all_player_stats)
        # Filter by player name (case insensitive)
        return df[df['player_name'].str.contains(player_name, case=False, na=False)]
    
    def get_aggregate_stats(self) -> Dict:
        """Get aggregate statistics across the tournament."""
        if not self.all_player_stats:
            return {}
        
        df = pd.DataFrame(self.all_player_stats)
        
        return {
            'total_matches': len(self.all_match_data),
            'total_player_performances': len(df),
            'unique_players': df['player_name'].nunique(),
            'unique_teams': df['team'].nunique(),
            'avg_kd_ratio': df['kd_ratio'].mean(),
            'avg_adr': df['adr'].mean(),
            'avg_hs_percentage': df['hs_percentage'].mean(),
            'total_kills': df['kills'].sum(),
            'total_deaths': df['deaths'].sum(),
            'maps_played': df['map_name'].nunique()
        }
