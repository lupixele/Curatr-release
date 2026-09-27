import json
import os
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Prevents display errors on servers

from scoring import score_title
from trends import plot_genre_trend
from tmdb_client import search_titles, fetch_title

# Page config
st.set_page_config(page_title="Curatr",layout="wide")
st.title("Curatr")
st.caption("Movie & TV Rating Analysis · DAE Capstone · Team rei-nexus")

# Load Data
@st.cache_data
def load_data():
    scored_df = pd.read_csv("data/scored_titles.csv")
    trend_df  = pd.read_csv("data/genre_year.csv")
    with open("data/baselines.json", "r", encoding="utf-8") as f:
        baselines = json.load(f)
    return scored_df, trend_df, baselines


# Errors and calling load_data()
try:
    scored_df, trend_df, baselines = load_data()
except FileNotFoundError as e:
    st.error(f"Missing data file: {e}. Run prepare_data.py → scoring.py → trends.py first.")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("Control Panel")
    media_type = st.radio("Media Type",["movie","tv"],horizontal=True)
    overview_year = st.selectbox("Overview Year",list(range(2014,2024)),index=9)
    