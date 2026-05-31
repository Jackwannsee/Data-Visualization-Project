import pandas as pd

try:
    import streamlit as st
    
    @st.cache_data
    def load_csv(path: str) -> pd.DataFrame:
        """
        Load a CSV file and cache it using Streamlit's caching mechanism.
        This prevents redundant disk reads and on-the-fly re-computation
        when interacting with dashboard widgets.
        """
        return pd.read_csv(path)
        
except ImportError:
    def load_csv(path: str) -> pd.DataFrame:
        """
        Fallback for loading CSV when Streamlit is not available
        (e.g. running visualization scripts standalone).
        """
        return pd.read_csv(path)
