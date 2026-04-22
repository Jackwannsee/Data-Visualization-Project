#!/usr/bin/env python3
"""
Main script to run tournament analysis.
Extracts comprehensive player performance metrics from all demo files.
"""

import os
import sys
import pandas as pd
from tournament_analyzer import TournamentAnalyzer

def main():
    """Main function to run the analysis."""
    
    # Set up paths
    json_path = "src/budapest_major.json"
    output_dir = "analysis_results"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("🎮 CS:GO Budapest Major 2025 - Player Performance Analysis")
    print("=" * 60)
    
    try:
        # Initialize analyzer
        analyzer = TournamentAnalyzer(json_path)
        
        # Run comprehensive analysis
        print("\n📊 Running tournament analysis...")
        player_stats_df = analyzer.analyze_tournament()
        
        if player_stats_df.empty:
            print("❌ No data extracted. Exiting.")
            sys.exit(1)
        
        # Save results
        output_path = os.path.join(output_dir, "budapest_major_player_stats.csv")
        analyzer.save_results(output_path)
        
        # Display aggregate statistics
        print("\n📈 Tournament Aggregate Statistics:")
        print("-" * 40)
        agg_stats = analyzer.get_aggregate_stats()
        for key, value in agg_stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Display top performers
        print("\n🏆 Top 10 Players by K/D Ratio:")
        print("-" * 50)
        top_players = analyzer.get_top_performers(10, 'kd_ratio')
        print(top_players[['player_name', 'team', 'opponent_team', 'map_name', 'kd_ratio', 'adr', 'hs_percentage']].to_string(index=False))
        
        # Display top ADR players
        print("\n🔥 Top 5 Players by ADR:")
        print("-" * 40)
        top_adr = analyzer.get_top_performers(5, 'adr')
        print(top_adr[['player_name', 'team', 'adr', 'kills', 'map_name']].to_string(index=False))
        
        # Team performance examples
        teams = ['Team Spirit', 'Team Vitality', 'FaZe Clan', 'Natus Vincere']
        
        for team in teams:
            print(f"\n📋 {team} Performance Summary:")
            print("-" * 40)
            team_data = analyzer.get_team_performance(team)
            if not team_data.empty:
                team_agg = team_data.agg({
                    'kd_ratio': ['mean', 'max'],
                    'adr': 'mean',
                    'hs_percentage': 'mean',
                    'kills': 'sum',
                    'deaths': 'sum'
                })
                print(f"Matches played: {len(team_data)}")
                print(f"Avg K/D Ratio: {team_agg['kd_ratio']['mean']:.2f} (Max: {team_agg['kd_ratio']['max']:.2f})")
                print(f"Avg ADR: {team_agg['adr']['mean']:.1f}")
                print(f"Avg HS%: {team_agg['hs_percentage']['mean']:.1f}%")
                print(f"Total Kills: {team_agg['kills']['sum']}")
                print(f"Total Deaths: {team_agg['deaths']['sum']}")
            else:
                print(f"No data found for {team}")
        
        # Save additional analysis files
        print("\n💾 Saving additional analysis files...")
        
        # Save top performers
        top_performers = analyzer.get_top_performers(20)
        top_performers.to_csv(os.path.join(output_dir, "top_20_players.csv"), index=False)
        
        # Save team summaries
        for team in teams:
            team_data = analyzer.get_team_performance(team)
            if not team_data.empty:
                team_data.to_csv(os.path.join(output_dir, f"{team.replace(' ', '_')}_performance.csv"), index=False)
        
        print("\n✅ Analysis complete!")
        print(f"📁 Results saved in: {os.path.abspath(output_dir)}")
        print(f"📊 Main dataset: {output_path}")
        print(f"📊 Match data: {output_path.replace('.csv', '_matches.csv')}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
