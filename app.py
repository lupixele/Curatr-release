import json
import os
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scoring import score_title
from trends import plot_genre_trend
from tmdb_client import search_titles, fetch_title

# Page config
st.set_page_config(page_title="Curatr", layout="wide")
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

try:
    scored_df, trend_df, baselines = load_data()
except FileNotFoundError as e:
    st.error(f"Missing data file: {e}. Run prepare_data.py → scoring.py → trends.py first.")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("Control Panel")
    media_type    = st.radio("Media Type", ["movie", "tv"], horizontal=True)
    overview_year = st.selectbox("Overview Year", list(range(2014, 2024)), index=9)
    genre_list    = sorted(trend_df[trend_df["media_type"] == media_type]["genre"].unique())
    selected_genre = st.selectbox("Genre (Trends tab)", genre_list)

tab1, tab2, tab3 = st.tabs(["Overview", "Trends", "Search"])

# Tab 1: Overview
with tab1:
    st.subheader(f"Top titles · {media_type} · {overview_year}")
    filtered = (
        scored_df[
            (scored_df["media_type"] == media_type) &
            (scored_df["release_year"] == overview_year)
        ]
        .sort_values("global_score", ascending=False)
        .head(50)
        .reset_index(drop=True)
    )
    if filtered.empty:
        st.info("No titles found for this selection.")
    else:
        st.dataframe(
            filtered[["title", "release_year", "rating", "vote_count", "global_score", "genre_score", "genres"]],
            use_container_width=True,
            hide_index=True,
        )

# Tab 2: Trends
with tab2:
    st.subheader(f"Genre trend · {selected_genre} · {media_type}")
    genre_data = trend_df[
        (trend_df["media_type"] == media_type) &
        (trend_df["genre"] == selected_genre)
    ].sort_values("release_year")

    if genre_data.empty:
        st.info("No trend data for this genre/media type.")
    else:
        fig = plot_genre_trend(genre_data, selected_genre, media_type)
        st.pyplot(fig)
        plt.close(fig)

# Tab 3: Search
with tab3:
    st.subheader("Live TMDb Search")
    query       = st.text_input("Search for a title", placeholder="e.g. Inception")
    search_type = st.radio("Type", ["movie", "tv"], horizontal=True, key="search_type")

    if query.strip():
        with st.spinner("Searching TMDb..."):
            try:
                results = search_titles(query.strip(), media_type=search_type)
            except Exception as e:
                st.error(f"Search failed: {e}")
                results = []

        if not results:
            st.info("No results found.")
        else:
            bl = baselines.get(search_type, {})
            for r in results[:10]:
                scored = score_title(r, bl)
                with st.expander(f"{r.get('title') or r.get('name', '—')}  ({r.get('release_year', '?')})"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("TMDb Rating", f"{r.get('rating', 0):.1f}")
                    col2.metric("Global Score", f"{scored.get('global_score', 0):.2f}")
                    col3.metric("Genre Score",  f"{scored.get('genre_score', 0):.2f}")
                    st.caption(f"Votes: {r.get('vote_count', 0):,}  ·  Genres: {r.get('genres', '—')}")
