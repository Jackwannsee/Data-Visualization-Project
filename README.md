# CS:GO Demo Analyzer

A comprehensive data visualization project for analyzing professional CS:GO demo files. This project provides tools for parsing, processing, visualizing, and creating interactive dashboards from .dem files.

## 🗂️ Project Structure

```
CS-GO-Demo-Analyzer/
├── dem_files/                  # Store your .dem files here
├── src/
│   ├── data_processing/       # Data parsing and cleaning modules
│   │   ├── __init__.py
│   │   └── demo_parser.py      # AWPY-based demo file parser
│   │
│   ├── visualization/          # Visualization modules
│   │   ├── __init__.py
│   │   └── match_visualizer.py # Matplotlib/Plotly visualizations
│   │
│   └── dashboard/              # Streamlit dashboard
│       ├── __init__.py
│       └── streamlit_app.py     # Main dashboard application
│
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/CS-GO-Demo-Analyzer.git
   cd CS-GO-Demo-Analyzer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Dashboard

Start the Streamlit dashboard:
```bash
streamlit run src/dashboard/streamlit_app.py
```

Then upload a .dem file through the web interface to begin analysis.

## 📦 Key Features

### Data Processing
- **AWPY Integration**: Uses the AWPY library for comprehensive demo parsing
- **Match Data Extraction**: Extracts match metadata, team scores, and player statistics
- **Player Performance Metrics**: Kills, deaths, assists, HS%, ADR, and K/D ratios

### Visualization
- **Team Performance Charts**: Bar charts showing final scores
- **Player Kills Visualization**: Horizontal bar charts ranked by kills
- **Performance Scatter Plots**: K/D ratio vs ADR analysis
- **Interactive Heatmaps**: Plotly-based interactive visualizations

### Dashboard
- **Streamlit Interface**: Modern, responsive web interface
- **Real-time Analysis**: Upload and analyze .dem files instantly
- **Customizable Views**: Toggle different analysis sections
- **Interactive Exploration**: Drill down into player and team performance

## 📊 Example Visualizations

The dashboard provides several key visualizations:

1. **Match Overview**: Basic match information (map, duration, scores)
2. **Team Performance**: Side-by-side comparison with visual charts
3. **Player Statistics**: Comprehensive table with all player metrics
4. **Performance Analysis**: K/D ratio vs ADR scatter plot
5. **Interactive Heatmap**: Explore player performance by team

## 🔧 Configuration

### Adding Demo Files

Place your .dem files in the `dem_files/` directory. The dashboard accepts file uploads through the interface.

### Customizing Analysis

Modify the analysis parameters in `src/data_processing/demo_parser.py`:
- Adjust parse rate for different levels of detail
- Add custom statistics extraction
- Modify data cleaning logic

### Extending Visualizations

Add new visualization types in `src/visualization/match_visualizer.py`:
- Create new plot methods
- Add interactive Plotly charts
- Customize color schemes and styling

## 📈 Data Fields Extracted

### Match Metadata
- Map name
- Match duration
- Team scores (T and CT)
- Date and timestamp

### Player Statistics
- Steam ID
- Player name
- Team (T/CT)
- Kills, deaths, assists
- Headshot percentage
- Average damage per round (ADR)
- Kill/Death ratio (calculated)

## 🎯 Future Enhancements

- **Advanced Analytics**: Add machine learning for performance prediction
- **Map Visualization**: Show player positions and movements on map
- **Comparison Tools**: Compare multiple matches side-by-side
- **Export Features**: Export data to CSV/Excel
- **Batch Processing**: Analyze multiple demos at once

## 🤝 Contributing

Contributions are welcome! Please open issues or submit pull requests for:
- Bug fixes
- New features
- Documentation improvements
- Performance optimizations

## 📜 License

This project is open source and available under the MIT License.

## 📚 Resources

- [AWPY Documentation](https://github.com/pnxenopoulos/awpy)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [CS:GO Demo File Format](https://developer.valvesoftware.com/wiki/Demo_File_Format)

---

🎮 Happy analyzing! May your K/D ratios always be positive!
