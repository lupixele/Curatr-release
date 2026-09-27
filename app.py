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
    has_data = not trend_df[
        (trend_df["media_type"] == media_type) &
        (trend_df["genre"] == selected_genre)
    ].empty
    if not has_data:
        st.info("No trend data for this genre/media type.")
    else:
        fig = plot_genre_trend(trend_df, media_type, selected_genre)
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
                response = search_titles(query.strip(), media_type=search_type)
                results = response.get("results", [])
            except Exception as e:
                st.error(f"Search failed: {e}")
                results = []

        if not results:
            st.info("No results found.")
        else:
            for r in results[:10]:
                scored = score_title(r, baselines)
                title_name = r.get("title") or r.get("name", "—")
                year_val = r.get("release_year") or "—"
                with st.expander(f"{title_name} ({year_val})"):
                    img_col, info_col = st.columns([1, 4])
                    with img_col:
                        poster = r.get("poster_path")
                        if poster:
                            st.image(f"https://image.tmdb.org/t/p/w185{poster}", use_container_width=True)
                        else:
                            st.caption("🎬 *No image*")
                    with info_col:
                        col1, col2, col3 = st.columns(3)
                        rating_val = r.get("rating")
                        col1.metric("TMDb Rating", f"{rating_val:.1f}" if rating_val is not None else "N/A")

                        g_score = scored.get("global_score")
                        col2.metric("Global Score", f"{g_score:.2f}" if g_score is not None else "N/A")

                        gn_score = scored.get("genre_score")
                        col3.metric("Genre Score", f"{gn_score:.2f}" if gn_score is not None else "N/A")

                        votes = r.get("vote_count", 0) or 0
                        genres = scored.get("genres") or r.get("genres") or "—"
                        st.caption(f"Votes: {votes:,}  ·  Genres: {genres}")
