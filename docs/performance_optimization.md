# Dashboard Performance Optimization

## Overview
The CS2 Budapest Major Dashboard originally fetched data directly from the disk using `pandas.read_csv()` on every single UI interaction. Streamlit’s execution model reruns the entire script from top to bottom whenever an input changes, meaning simple interactions (like toggling a radio button or selecting a player) triggered multiple redundant read operations and on-the-fly Pandas filtering. This caused noticeable lag and suboptimal performance.

To resolve this, we introduced a centralized caching strategy using Streamlit's built-in memory caching capabilities (`@st.cache_data`).

## Implementation Details

### Centralized Data Loader
A new utility module was created at `src/visualization/data_loader.py`.
This module defines a `load_csv()` function that conditionally imports Streamlit and wraps `pd.read_csv()` with `@st.cache_data`.

```python
import pandas as pd

try:
    import streamlit as st
    
    @st.cache_data
    def load_csv(path: str) -> pd.DataFrame:
        return pd.read_csv(path)
        
except ImportError:
    def load_csv(path: str) -> pd.DataFrame:
        return pd.read_csv(path)
```

By conditionally importing Streamlit, the visualization scripts can continue to function as standalone scripts in isolated environments without failing, while automatically leveraging Streamlit's fast memory cache when running within the dashboard.

### Dashboard and Visualization Integration
We replaced all raw `pd.read_csv()` operations with the cached `load_csv()` function across both the frontend pages and backend visualization components:

**Refactored Visualization Scripts:**
- `ct_t_stacked_bar.py`
- `diverging_bar.py`
- `economy_viz.py`
- `headshot_scatter.py`
- `position_heatmap.py`
- `spider_player_performance.py`

**Refactored Dashboard Pages:**
- `1_💰_Economy_Analysis.py`
- `2_🕷️_Player_Performance.py`
- `5_📊_Side_Comparison.py`

## Benefits
1. **Zero Redundant Disk I/O:** The CSV datasets (which can be several megabytes in size) are loaded from the disk exactly once per session.
2. **Lightning-Fast Filtering:** Since the dataframes are cached in RAM, the on-the-fly filtering operations during UI interactions execute instantly.
3. **Seamless Backward Compatibility:** The core filtering logic and visualization APIs remain identical, ensuring no regressions while massively improving speed.
