"""app.py - Curatr Streamlit Application.

Interactive dashboard providing:
1. Fairer movie and TV rankings using Bayesian shrinkage and genre-adjusted scoring.
2. 10-year (2014-2023) genre quality trend analysis with Matplotlib visualization.
3. Live TMDb title lookup and interactive title scoring calculator.
4. Comprehensive methodology and mathematical explanations.

Team rei-nexus (Ratan, Lochan, Vivek, Nagendra) | Aditya University DAE Capstone
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Import team modules
from scoring import global_score, genre_score, score_title
from trends import plot_genre_trend, REFERENCE_YEARS
from tmdb_client import search_titles, fetch_title

# Set Streamlit page configuration
st.set_page_config(
    page_title="Curatr — Fair Movie & TV Rating Analysis",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (dark theme, badges, cards)
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #58a6ff, #bc8cff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #8b949e;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8b949e;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #f0f6fc;
    }
    .status-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .badge-rise { background-color: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid #2ea043; }
    .badge-fall { background-color: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #da3633; }
    .badge-unchanged { background-color: rgba(110, 118, 129, 0.2); color: #8b949e; border: 1px solid #6e7681; }
    .badge-insufficient { background-color: rgba(210, 153, 34, 0.2); color: #d29922; border: 1px solid #bb8009; }
    .badge-none { background-color: rgba(88, 166, 255, 0.2); color: #58a6ff; border: 1px solid #388bfd; }
    .formula-box {
        background-color: #0d1117;
        border-left: 4px solid #58a6ff;
        padding: 12px 16px;
        border-radius: 4px;
        font-family: monospace;
        color: #e6edf3;
        margin: 8px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading scored titles...")
def load_scored_data(path: str = "data/scored_titles.csv") -> pd.DataFrame:
    """Load and cache scored titles CSV."""
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner="Loading genre trends...")
def load_trends_data(path: str = "data/genre_year.csv") -> pd.DataFrame:
    """Load and cache genre trends CSV."""
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner="Loading statistical baselines...")
def load_baselines(path: str = "data/baselines.json") -> dict:
    """Load and cache baseline parameters JSON."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Data existence check
scored_df = load_scored_data()
trends_df = load_trends_data()
baselines = load_baselines()

data_ready = not scored_df.empty and not trends_df.empty and bool(baselines)


# Sidebar controls
st.sidebar.markdown("### 🎬 Curatr Navigation")
media_type_choice = st.sidebar.radio(
    "Select Catalog:",
    options=["Movies", "TV Shows"],
    index=0,
    help="Keep movie and TV baselines strictly separate per project specification.",
)
media_type = "movie" if media_type_choice == "Movies" else "tv"

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Reference Parameters")
if data_ready and media_type in baselines:
    b_info = baselines[media_type]
    st.sidebar.metric(
        label=f"Global Prior C (Mean)",
        value=f"{b_info['C']:.3f}",
        help="Unweighted mean rating across all unique eligible titles in the 2014-2023 reference window.",
    )
    st.sidebar.metric(
        label=f"Shrinkage Parameter m (p25)",
        value=f"{b_info['m']:.1f} votes",
        help="25th-percentile vote count used for Bayesian shrinkage.",
    )
    st.sidebar.metric(
        label="Eligible Titles in Window",
        value=f"{b_info['title_count']:,}",
        help="10-year audited sample from asaniczka dataset (2014-2023).",
    )
    st.sidebar.metric(
        label="Observed Genres",
        value=f"{len(b_info['genres'])}",
    )
else:
    st.sidebar.warning("Reference baselines not loaded yet.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 TMDb API Settings")
user_tmdb_cred = st.sidebar.text_input(
    "API Key or Read Token",
    type="password",
    value=os.environ.get("TMDB_TOKEN", "") or os.environ.get("TMDB_API_KEY", ""),
    help="Enter your TMDb v3 API Key (32 hex characters) or v4 Read Access Token (starts with eyJ).",
)
if user_tmdb_cred:
    cleaned = user_tmdb_cred.strip().strip('"').strip("'")
    if cleaned.startswith("eyJ"):
        os.environ["TMDB_TOKEN"] = cleaned
        os.environ["TMDB_API_KEY"] = ""
    else:
        os.environ["TMDB_API_KEY"] = cleaned
        os.environ["TMDB_TOKEN"] = ""

from tmdb_client import validate_tmdb_connection
if st.sidebar.button("🔌 Test API Connection"):
    is_ok, conn_msg = validate_tmdb_connection()
    if is_ok:
        st.sidebar.success("✅ " + conn_msg)
    else:
        st.sidebar.error("❌ " + conn_msg)

st.sidebar.caption("[Get TMDb API Key](https://www.themoviedb.org/settings/api)")

st.sidebar.markdown("---")
st.sidebar.caption("Curatr · rei-nexus · DAE Capstone 2026")


# Header
st.markdown('<div class="main-header">Curatr — Fairer Movie & TV Rating Analysis</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Evaluating titles fairly with Bayesian shrinkage and genre baselines, tracking quality trends across 2014–2023.</div>',
    unsafe_allow_html=True,
)

if not data_ready:
    st.error(
        "⚠️ Reference data artifacts missing! Run the pipeline steps from terminal:\n\n"
        "```bash\n"
        "python prepare_data.py\n"
        "python scoring.py\n"
        "python trends.py\n"
        "```"
    )
    st.stop()


# Main Application Tabs
tab_rankings, tab_trends, tab_scorer, tab_about = st.tabs([
    "🏆 Fair Rankings & Explorer",
    "📈 Genre Quality Trends (2014–2023)",
    "🔍 Live Title Scorer & Lookup",
    "📚 Methodology & Maths",
])


# ==============================================================================
# TAB 1: RANKINGS & EXPLORER
# ==============================================================================
with tab_rankings:
    st.markdown(f"### 🏆 Fair Catalog Rankings ({media_type_choice})")
    st.caption("Compare how raw average ratings distort rankings compared to Bayesian Global Score and Genre-Adjusted Score.")

    # Filter row
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 2])

    type_scored = scored_df[scored_df["media_type"] == media_type].copy()

    # Get list of unique genres for this media type
    all_genres = sorted(list(baselines[media_type]["genres"].keys()))

    with f_col1:
        search_query = st.text_input("🔍 Filter by Title", placeholder="e.g. Interstellar, Dark...").strip().lower()

    with f_col2:
        selected_genres = st.multiselect("Genre Filter", options=all_genres, default=[])

    with f_col3:
        year_range = st.slider("Release Year Range", min_value=2014, max_value=2023, value=(2014, 2023))

    with f_col4:
        min_votes = st.number_input("Minimum Votes (v)", min_value=1, max_value=50000, value=25, step=25)

    # Apply filters
    filtered_df = type_scored[
        (type_scored["release_year"] >= year_range[0])
        & (type_scored["release_year"] <= year_range[1])
        & (type_scored["vote_count"] >= min_votes)
    ]

    if search_query:
        filtered_df = filtered_df[filtered_df["title"].str.lower().str.contains(search_query, na=False)]

    if selected_genres:
        # Match if title contains any selected genre
        pattern = "|".join([re_escape for re_escape in selected_genres])
        filtered_df = filtered_df[filtered_df["genres"].str.contains(pattern, na=False)]

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Matching Titles</div><div class="metric-value">{len(filtered_df):,}</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        mean_adj = filtered_df["genre_score"].mean() if not filtered_df.empty else 0.0
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Avg Genre-Adjusted Score</div><div class="metric-value">{mean_adj:.2f}</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        mean_raw = filtered_df["rating"].mean() if not filtered_df.empty else 0.0
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Avg Raw Rating</div><div class="metric-value">{mean_raw:.2f}</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        top_genre = selected_genres[0] if len(selected_genres) == 1 else "All Genres"
        g_baseline_val = baselines[media_type]["genres"].get(top_genre, {}).get("baseline", baselines[media_type]["C"])
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Effective Baseline G</div><div class="metric-value">{g_baseline_val:.2f}</div></div>',
            unsafe_allow_html=True,
        )

    # Sort option
    sort_choice = st.radio(
        "Sort Catalog By:",
        options=[
            "Genre-Adjusted Score (S_genre) — Fairer against genre standards",
            "Global Bayesian Score (S_global) — Shrunk toward catalog average",
            "Raw TMDb Rating (R) — Unweighted platform average",
            "Vote Count (v) — Most popular",
        ],
        horizontal=True,
    )

    sort_map = {
        "Genre-Adjusted Score (S_genre) — Fairer against genre standards": ("genre_score", False),
        "Global Bayesian Score (S_global) — Shrunk toward catalog average": ("global_score", False),
        "Raw TMDb Rating (R) — Unweighted platform average": ("rating", False),
        "Vote Count (v) — Most popular": ("vote_count", False),
    }
    sort_col, sort_asc = sort_map[sort_choice]
    display_df = filtered_df.sort_values(by=sort_col, ascending=sort_asc).reset_index(drop=True)

    # Display Table
    table_cols = [
        "title",
        "release_year",
        "genre_score",
        "global_score",
        "rating",
        "vote_count",
        "genres",
        "original_language",
    ]
    renamed_df = display_df[table_cols].rename(
        columns={
            "title": "Title",
            "release_year": "Year",
            "genre_score": "Genre-Adjusted (S_genre)",
            "global_score": "Global Score (S_global)",
            "rating": "Raw Rating (R)",
            "vote_count": "Votes (v)",
            "genres": "Genres",
            "original_language": "Lang",
        }
    )

    st.dataframe(
        renamed_df.head(100).style.format(
            {
                "Genre-Adjusted (S_genre)": "{:.3f}",
                "Global Score (S_global)": "{:.3f}",
                "Raw Rating (R)": "{:.2f}",
                "Votes (v)": "{:,}",
            }
        ),
        use_container_width=True,
        height=450,
    )

    # Title Mathematical Inspector
    st.markdown("---")
    st.markdown("#### 🔬 Title Mathematical Breakdown")
    st.caption("Select any title from the filtered list to view its step-by-step mathematical score composition.")

    if not display_df.empty:
        candidate_titles = display_df["title"].head(50).tolist()
        inspect_title_name = st.selectbox("Inspect Title:", options=candidate_titles, index=0)
        selected_row = display_df[display_df["title"] == inspect_title_name].iloc[0]

        b_c1, b_c2, b_c3 = st.columns([1, 1, 1])
        c_prior = baselines[media_type]["C"]
        m_prior = baselines[media_type]["m"]
        r_val = selected_row["rating"]
        v_val = selected_row["vote_count"]
        g_val = selected_row["genre_baseline"]
        s_glob_val = selected_row["global_score"]
        s_gen_val = selected_row["genre_score"]

        with b_c1:
            st.markdown("**1. Raw Input**")
            st.write(f"- Title: **{selected_row['title']}**")
            st.write(f"- Year: **{selected_row['release_year']}**")
            st.write(f"- Raw Rating ($R$): **{r_val:.2f}**")
            st.write(f"- Vote Count ($v$): **{v_val:,}**")
            st.write(f"- Genres: `{selected_row['genres']}`")

        with b_c2:
            st.markdown("**2. Prior Reference Parameters**")
            st.write(f"- Global Prior ($C$): **{c_prior:.3f}**")
            st.write(f"- Shrinkage Parameter ($m$): **{m_prior:.1f}**")
            st.write(f"- Genre Baseline ($G$): **{g_val:.3f}**")
            st.write(f"- Shrinkage Weight $v/(v+m)$: **{(v_val / (v_val + m_prior)):.4f}**")

        with b_c3:
            st.markdown("**3. Calculated Outputs**")
            st.metric("Genre-Adjusted Score (S_genre)", f"{s_gen_val:.3f}", delta=f"{s_gen_val - r_val:+.3f} vs Raw")
            st.metric("Global Bayesian Score (S_global)", f"{s_glob_val:.3f}", delta=f"{s_glob_val - r_val:+.3f} vs Raw")


# ==============================================================================
# TAB 2: GENRE TRENDS
# ==============================================================================
with tab_trends:
    st.markdown(f"### 📈 Genre Quality Trends (2014–2023) · {media_type_choice}")
    st.caption("Tracking how genre quality rises and falls over a ten-year reference snapshot using fair genre scores.")

    trend_genres = sorted(trends_df[trends_df["media_type"] == media_type]["genre"].unique())

    t_col1, t_col2 = st.columns([1, 3])

    with t_col1:
        chosen_genre = st.selectbox(
            "Select Genre to Analyze:",
            options=trend_genres,
            index=0 if "Drama" not in trend_genres else trend_genres.index("Drama"),
        )
        st.info(
            f"**Evaluation Rule:**\n\n"
            f"Every title is evaluated with $S_{{genre}}$. Points require $\\ge 5$ titles per year. "
            f"Years with $< 5$ titles are treated as insufficient data."
        )

    with t_col2:
        # Generate plot via Nagendra's trends module
        trend_fig = plot_genre_trend(trends_df, media_type=media_type, genre=chosen_genre)
        st.pyplot(trend_fig, use_container_width=True)

    # 10-year grid table
    genre_data = trends_df[
        (trends_df["media_type"] == media_type) & (trends_df["genre"] == chosen_genre)
    ].sort_values("release_year")

    st.markdown("#### 📊 Complete 10-Year Trajectory Grid")

    # Format badges for status
    def format_status(status: str) -> str:
        if status == "rise":
            return "🟢 Rise"
        elif status == "fall":
            return "🔴 Fall"
        elif status == "unchanged":
            return "⚪ Unchanged"
        elif status == "insufficient_data":
            return "🟡 Insufficient Data"
        elif status == "no_previous_year":
            return "🔵 2014 Baseline"
        return status

    display_trends = genre_data.copy()
    display_trends["Status"] = display_trends["comparison_status"].apply(format_status)
    display_trends = display_trends[[
        "release_year",
        "title_count",
        "mean_genre_score",
        "mean_raw_rating",
        "yoy_change",
        "Status",
    ]].rename(
        columns={
            "release_year": "Release Year",
            "title_count": "Title Count (N)",
            "mean_genre_score": "Mean Genre Score (S_genre)",
            "mean_raw_rating": "Mean Raw Rating (R)",
            "yoy_change": "YoY Change (Points)",
        }
    )

    st.dataframe(
        display_trends.style.format(
            {
                "Title Count (N)": "{:,}",
                "Mean Genre Score (S_genre)": "{:.3f}",
                "Mean Raw Rating (R)": "{:.3f}",
                "YoY Change (Points)": "{:+.3f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
    )

    # Analytical highlights
    valid_points = genre_data[genre_data["title_count"] >= 5]
    if not valid_points.empty:
        best_yr = valid_points.loc[valid_points["mean_genre_score"].idxmax()]
        worst_yr = valid_points.loc[valid_points["mean_genre_score"].idxmin()]
        h1, h2, h3 = st.columns(3)
        with h1:
            st.success(f"🏆 **Peak Quality Year:** {int(best_yr['release_year'])} ({best_yr['mean_genre_score']:.2f} pts, {int(best_yr['title_count']):,} titles)")
        with h2:
            st.error(f"📉 **Lowest Quality Year:** {int(worst_yr['release_year'])} ({worst_yr['mean_genre_score']:.2f} pts, {int(worst_yr['title_count']):,} titles)")
        with h3:
            total_titles = int(genre_data['title_count'].sum())
            st.info(f"📦 **Decade Total:** {total_titles:,} titles in {chosen_genre}")


# ==============================================================================
# TAB 3: LIVE TITLE SCORER & LOOKUP
# ==============================================================================
with tab_scorer:
    st.markdown("### 🔍 Live Title Scorer & Online Lookup")
    st.caption("Evaluate any live title from TMDb or test custom values against the Curatr reference baselines.")

    sub_tab_search, sub_tab_manual = st.tabs(["🌐 Search Live TMDb API", "🧮 Interactive Custom Title Calculator"])

    with sub_tab_search:
        st.markdown("#### Search TMDb Catalog")
        s_col1, s_col2 = st.columns([3, 1])
        with s_col1:
            api_query = st.text_input("Enter Title Name to Search Live on TMDb:", placeholder="e.g. Oppenheimer, Succession, Shogun...")
        with s_col2:
            st.write("")
            st.write("")
            execute_search = st.button("🚀 Search TMDb", use_container_width=True)

        if "tmdb_search_results" not in st.session_state:
            st.session_state["tmdb_search_results"] = None

        if execute_search and api_query.strip():
            with st.spinner(f"Searching TMDb for '{api_query}'..."):
                try:
                    search_res = search_titles(api_query.strip(), media_type=media_type)
                    st.session_state["tmdb_search_results"] = search_res.get("results", [])
                except Exception as exc:
                    st.error(f"TMDb Search Error: {exc}")
                    st.info("💡 Tip: You can supply a TMDb Read Token in the sidebar, or use the interactive calculator tab without a token.")

        results = st.session_state.get("tmdb_search_results")
        if results is not None:
            if not results:
                st.warning("No matching titles found on TMDb.")
            else:
                st.success(f"Found {len(results)} titles on TMDb:")
                for item in results[:10]:
                    scored_item = score_title(item, baselines)
                    with st.expander(f"🎬 {scored_item['title']} ({scored_item.get('release_year', 'Unknown Year')})"):
                        c1, c2, c3 = st.columns([1, 2, 2])
                        with c1:
                            if item.get("poster_path"):
                                poster_url = f"https://image.tmdb.org/t/p/w200{item['poster_path']}"
                                st.image(poster_url, width=130)
                            else:
                                st.write("*(No poster)*")
                        with c2:
                            st.write(f"**TMDb ID:** `{item['tmdb_id']}`")
                            st.write(f"**Genres:** `{item['genres'] or 'None'}`")
                            st.write(f"**Raw Rating:** {item['rating']:.2f}")
                            st.write(f"**Vote Count:** {item['vote_count']:,}")
                            st.caption(item.get("overview", "No synopsis available."))
                        with c3:
                            st.write("**Curatr Fair Evaluation:**")
                            st.metric("Genre-Adjusted Score", f"{scored_item['genre_score']:.3f}" if scored_item['genre_score'] is not None else "N/A")
                            st.metric("Global Bayesian Score", f"{scored_item['global_score']:.3f}" if scored_item['global_score'] is not None else "N/A")
                            if scored_item.get("genre_fallback"):
                                st.caption("⚠️ Genre fallback to catalog prior C applied.")

    with sub_tab_manual:
        st.markdown("#### Test the Scoring Algorithm with Custom Values")
        st.caption("Adjust sliders to observe how Bayesian shrinkage adjusts scores dynamically based on vote count and genre baseline.")

        man_col1, man_col2 = st.columns(2)
        with man_col1:
            custom_title = st.text_input("Title", value="My Indie Film / Pilot")
            custom_rating = st.slider("Raw Rating (0.0 to 10.0)", min_value=0.0, max_value=10.0, value=8.5, step=0.1)
            custom_votes = st.slider("Vote Count (v)", min_value=0, max_value=10000, value=25, step=5)
            custom_genre = st.selectbox("Genre", options=all_genres, index=0)

        custom_dict = {
            "media_type": media_type,
            "tmdb_id": 999999,
            "title": custom_title,
            "release_year": 2023,
            "rating": custom_rating,
            "vote_count": custom_votes,
            "genres": custom_genre,
        }
        res_calc = score_title(custom_dict, baselines)

        with man_col2:
            st.markdown("**Calculated Fair Scores:**")
            r1, r2 = st.columns(2)
            with r1:
                st.metric("Raw Rating (R)", f"{custom_rating:.2f}")
                st.metric("Genre Baseline (G)", f"{res_calc['genre_baseline']:.2f}" if res_calc['genre_baseline'] else "—")
            with r2:
                st.metric("Global Score (S_global)", f"{res_calc['global_score']:.3f}" if res_calc['global_score'] else "—")
                st.metric("Genre-Adjusted (S_genre)", f"{res_calc['genre_score']:.3f}" if res_calc['genre_score'] else "—")

            st.markdown("**Shrinkage Effect:**")
            if custom_votes == 0:
                st.info("With 0 votes, status is `unrated`.")
            else:
                c_val = baselines[media_type]["C"]
                m_val = baselines[media_type]["m"]
                w = custom_votes / (custom_votes + m_val)
                st.write(f"- Credibility Weight $w = v / (v + m) = {w:.3f}$")
                if custom_rating > c_val:
                    st.write(f"- Score is shrunk downward toward global prior $C = {c_val:.2f}$ to protect against small-sample hype.")
                else:
                    st.write(f"- Score is pulled upward toward global prior $C = {c_val:.2f}$.")

        # Dynamic sensitivity curve plot
        st.markdown("##### 📈 Vote Count Sensitivity Curve")
        vote_points = np.logspace(0, 4, 100)  # 1 to 10,000
        g_baseline = baselines[media_type]["genres"].get(custom_genre, {}).get("baseline", baselines[media_type]["C"])
        c_prior = baselines[media_type]["C"]
        m_prior = baselines[media_type]["m"]

        s_glob_curve = [global_score(custom_rating, int(v), c_prior, m_prior) for v in vote_points]
        s_gen_curve = [genre_score(custom_rating, int(v), c_prior, m_prior, g_baseline) for v in vote_points]

        fig_sens, ax_sens = plt.subplots(figsize=(8, 3.2), dpi=100)
        fig_sens.patch.set_facecolor("#0e1117")
        ax_sens.set_facecolor("#161b22")
        ax_sens.plot(vote_points, s_glob_curve, label="Global Score (S_global)", color="#58a6ff", linewidth=2)
        ax_sens.plot(vote_points, s_gen_curve, label="Genre-Adjusted Score (S_genre)", color="#bc8cff", linewidth=2)
        ax_sens.axhline(custom_rating, color="#f85149", linestyle="--", label=f"Raw Rating ({custom_rating:.1f})", alpha=0.8)
        ax_sens.axhline(c_prior, color="#8b949e", linestyle=":", label=f"Global Prior C ({c_prior:.2f})", alpha=0.7)
        ax_sens.set_xscale("log")
        ax_sens.set_xlabel("Vote Count (log scale)", color="#8b949e")
        ax_sens.set_ylabel("Score", color="#8b949e")
        ax_sens.tick_params(colors="#8b949e")
        for s in ax_sens.spines.values():
            s.set_color("#30363d")
        ax_sens.grid(True, linestyle="--", alpha=0.3, color="#30363d")
        ax_sens.legend(loc="best", facecolor="#161b22", edgecolor="#30363d", labelcolor="#e6edf3", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig_sens)


# ==============================================================================
# TAB 4: METHODOLOGY & MATHS
# ==============================================================================
with tab_about:
    st.markdown("### 📚 Project Methodology & Mathematical Foundations")
    st.markdown(
        """
        **Curatr** was conceived to solve a fundamental data distortion in entertainment analytics: **raw arithmetic averages systematically lie.**
        """
    )

    st.markdown("#### 1. The Core Problem: Volume Hype vs Indie Neglect")
    st.write(
        """
        A raw average treats an 8.2 rating with 40 votes and an 8.2 rating with 500,000 votes as identical signals of quality.
        - High-visibility commercial blockbusters gather hundreds of thousands of votes, where even modest ratings dominate search results.
        - High-quality indie, international, or documentary titles with 40–100 votes are vulnerable: a few passionate reviewers or family members can push an unearned 9.5, or a single negative review can tank a masterpiece.
        - Furthermore, **genres are evaluated on different psychological scales.** A 6.0 in Horror is historically difficult to achieve, whereas Animation and Documentaries routinely average well over 7.0.
        """
    )

    st.markdown("#### 2. The Mathematical Solution")
    col_math1, col_math2 = st.columns(2)

    with col_math1:
        st.markdown("**Bayesian Global Weighted Score:**")
        st.markdown('<div class="formula-box">S_global = (v · R + m · C) / (v + m)</div>', unsafe_allow_html=True)
        st.write(
            """
            Where:
            - **$v$**: Vote count for the title.
            - **$R$**: Raw average rating from the platform ($0$ to $10$).
            - **$C$**: Global prior mean across all eligible catalog titles in the reference window.
            - **$m$**: Shrinkage parameter, pinned to the 25th-percentile vote count.
            """
        )

    with col_math2:
        st.markdown("**Genre-Adjusted Score:**")
        st.markdown('<div class="formula-box">S_genre = C + (v / (v + m)) · (R - G)</div>', unsafe_allow_html=True)
        st.write(
            """
            Where:
            - **$G$**: Effective baseline of the title's genres (equal-weight mean of distinct genre priors).
            - **$R - G$**: How much the title outperforms its specific genre expectation.
            - Evaluates whether a title is exceptional *relative to its genre standards*, preventing genre bias.
            """
        )

    st.markdown("---")
    st.markdown("#### 3. Dataset Audit & Provenance")
    st.write(
        """
        - **Source:** asaniczka Full TMDb Movies & TV Datasets 2024.
        - **Locked Reference Window:** 2014–2023 (10 complete calendar years).
        - **Audited Eligible Titles:** 101,023 movies and 26,172 TV shows.
        - **TV Year Definition:** TV shows use the series **first-air year**, not individual season dates.
        - **Strict Separation:** Movie and TV taxonomies and statistics are kept completely independent.
        """
    )

    st.markdown("---")
    st.markdown("#### 4. Team rei-nexus")
    st.write(
        """
        - **G. Ratan:** UI, Integration & Streamlit Application (`app.py`)
        - **Y. Lochan:** Mathematics, Baselines & Bayesian Scoring (`scoring.py`)
        - **P. Vivek:** Data Engineering, Cleaning & TMDb Client (`prepare_data.py`, `tmdb_client.py`)
        - **K. Nagendra:** Genre Trends, Temporal Aggregations & Testing (`trends.py`, `tests/`)
        
        *Aditya University — Data Analysis Essentials (DAE) Capstone 2026*
        """
    )
