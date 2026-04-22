"""
Streamlit dashboard for CS:GO demo analysis.
Interactive visualization and exploration of match data.
"""

import streamlit as st
import pandas as pd
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_processing.demo_parser import DemoAnalyzer
from visualization.match_visualizer import MatchVisualizer

def main():
    """Main function for the Streamlit dashboard."""
    
    # Page configuration
    st.set_page_config(
        page_title="CS:GO Demo Analyzer",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .team-t {
            color: #FF4500;
            font-weight: bold;
        }
        .team-ct {
            color: #0066CC;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="main-header">🎮 CS:GO Demo Analyzer</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Demo File")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Upload a .dem file",
            type=["dem"],
            help="Upload a CS:GO demo file to analyze"
        )
        
        st.divider()
        st.header("⚙️ Settings")
        
        # Analysis options
        show_player_stats = st.checkbox("Show Player Statistics", value=True)
        show_team_comparison = st.checkbox("Show Team Comparison", value=True)
        show_performance_plots = st.checkbox("Show Performance Plots", value=True)
    
    # Main content
    if uploaded_file is not None:
        # Save uploaded file temporarily
        demo_path = f"temp_demo.dem"
        with open(demo_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Parse and analyze the demo
        with st.spinner("🔍 Analyzing demo file..."):
            try:
                analyzer = DemoAnalyzer(demo_path)
                match_data = analyzer.extract_match_data()
                
                # Create visualizer
                visualizer = MatchVisualizer(match_data)
                
                # Display match overview
                st.header("📊 Match Overview")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Map", match_data['map_name'])
                with col2:
                    st.metric("Duration", f"{match_data['duration']//60}:{match_data['duration']%60:02d}")
                with col3:
                    st.metric("T Score", match_data['t_score'], delta_color="off")
                with col4:
                    st.metric("CT Score", match_data['ct_score'], delta_color="off")
                
                st.divider()
                
                # Team scores visualization
                if show_team_comparison:
                    st.header("🏆 Team Performance")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        team_fig = visualizer.plot_team_scores()
                        st.pyplot(team_fig)
                    
                    with col2:
                        st.subheader("Team Statistics")
                        st.write(f"**<span class='team-t'>Terrorists</span>**: {match_data['t_score']} rounds", unsafe_allow_html=True)
                        st.write(f"**<span class='team-ct'>Counter-Terrorists</span>**: {match_data['ct_score']} rounds", unsafe_allow_html=True)
                        
                        winner = "Terrorists" if match_data['t_score'] > match_data['ct_score'] else "Counter-Terrorists"
                        st.success(f"🏆 **{winner} win the match!**")
                
                st.divider()
                
                # Player statistics
                if show_player_stats:
                    st.header("👥 Player Statistics")
                    
                    # Player data table
                    players_df = pd.DataFrame(match_data['players'])
                    players_df['kd_ratio'] = players_df['kills'] / players_df['deaths'].replace(0, 1)
                    players_df['kd_ratio'] = players_df['kd_ratio'].round(2)
                    
                    # Reorder and rename columns
                    display_cols = ['name', 'team', 'kills', 'deaths', 'assists', 'kd_ratio', 'hs_percentage', 'adr']
                    players_df = players_df[display_cols]
                    players_df.columns = ['Name', 'Team', 'Kills', 'Deaths', 'Assists', 'K/D', 'HS%', 'ADR']
                    
                    st.dataframe(players_df, use_container_width=True)
                    
                    # Player kills chart
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        kills_fig = visualizer.plot_player_kills()
                        st.pyplot(kills_fig)
                    
                    with col2:
                        if show_performance_plots:
                            kd_fig = visualizer.plot_kd_ratio()
                            st.pyplot(kd_fig)
                
                st.divider()
                
                # Interactive visualization
                if show_performance_plots:
                    st.header("🔥 Interactive Visualization")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Player Performance Heatmap")
                        heatmap_fig = visualizer.create_interactive_heatmap()
                        st.plotly_chart(heatmap_fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Top Performers")
                        top_players = players_df.nlargest(3, 'K/D')
                        for i, row in top_players.iterrows():
                            team_class = 'team-t' if row['Team'] == 'T' else 'team-ct'
                            st.markdown(f"""
                                <div style='padding: 10px; margin: 5px 0; border-radius: 5px; background-color: #f0f2f6;'>
                                    <strong><span class='{team_class}'>{row['Name']}</span></strong> - 
                                    K/D: {row['K/D']}, ADR: {row['ADR']:.0f}
                                </div>
                            """.format(team_class=team_class), unsafe_allow_html=True)
                
                # Clean up temporary file
                os.remove(demo_path)
                
            except Exception as e:
                st.error(f"❌ Error analyzing demo file: {str(e)}")
                if os.path.exists(demo_path):
                    os.remove(demo_path)
    else:
        # Welcome screen
        st.info("👆 Please upload a .dem file to begin analysis")
        
        st.markdown("""
        ### 📚 About
        This dashboard analyzes CS:GO demo files to provide:
        
        - **Match Overview**: Map, duration, and final scores
        - **Team Performance**: Visual comparison of team results
        - **Player Statistics**: Detailed stats for all players
        - **Performance Analysis**: K/D ratios, ADR, and headshot percentages
        - **Interactive Visualizations**: Explore data with interactive charts
        
        ### 🎯 Features
        - Upload any CS:GO .dem file
        - Comprehensive match analysis
        - Player performance metrics
        - Interactive data exploration
        - Exportable visualizations
        """)

if __name__ == "__main__":
    main()
