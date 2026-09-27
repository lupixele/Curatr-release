"""trends.py - Multi-genre temporal aggregation and visualization for Curatr.

Aggregates scored titles across a ten-year reference window (2014-2023), computes
exact year-over-year changes with strict data sufficiency checks, and produces
publication-quality Matplotlib figures.
Adheres strictly to Curatr-dev/docs/03-data-and-function-contracts.md.
"""

from __future__ import annotations

import argparse
import os
import time
from typing import List, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REFERENCE_YEARS = list(range(2014, 2024))  # 2014 through 2023


def build_trends(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate scored titles into a complete 10-year grid per (media_type, genre).

    Applies strict data sufficiency rules:
    - Current title count < 5 -> comparison_status = 'insufficient_data', yoy_change = NaN
    - Release year == 2014 -> comparison_status = 'no_previous_year', yoy_change = NaN
    - Preceding year title count < 5 -> comparison_status = 'insufficient_data', yoy_change = NaN
    - Otherwise -> exact delta (current - previous) and 'rise' / 'fall' / 'unchanged'
    """
    valid = scored_df[scored_df["score_status"] == "ok"].copy()

    # Explode canonical genres per title (each title counted once per applicable genre)
    exploded = (
        valid.assign(genre=valid["genres"].astype(str).str.split("|"))
        .explode("genre")
    )
    exploded["genre"] = exploded["genre"].astype(str).str.strip()
    exploded = exploded[exploded["genre"] != ""]

    # Grouped aggregation
    agg = (
        exploded.groupby(["media_type", "genre", "release_year"])
        .agg(
            title_count=("tmdb_id", "count"),
            mean_genre_score=("genre_score", "mean"),
            mean_raw_rating=("rating", "mean"),
        )
        .reset_index()
    )

    # Build complete 10-year grid for every observed (media_type, genre)
    all_rows: List[dict] = []
    observed_types = sorted(agg["media_type"].unique())

    for m_type in observed_types:
        sub_type = agg[agg["media_type"] == m_type]
        observed_genres = sorted(sub_type["genre"].unique())

        for g_name in observed_genres:
            g_data = sub_type[sub_type["genre"] == g_name].set_index("release_year")

            prev_count = 0
            prev_score = np.nan

            for yr in REFERENCE_YEARS:
                if yr in g_data.index:
                    row = g_data.loc[yr]
                    count = int(row["title_count"])
                    m_score = float(row["mean_genre_score"])
                    m_raw = float(row["mean_raw_rating"])
                else:
                    count = 0
                    m_score = np.nan
                    m_raw = np.nan

                # Status logic
                if count < 5:
                    status = "insufficient_data"
                    yoy = np.nan
                elif yr == 2014:
                    status = "no_previous_year"
                    yoy = np.nan
                elif prev_count < 5 or np.isnan(prev_score):
                    status = "insufficient_data"
                    yoy = np.nan
                else:
                    delta = m_score - prev_score
                    yoy = float(delta)
                    if delta > 0:
                        status = "rise"
                    elif delta < 0:
                        status = "fall"
                    else:
                        status = "unchanged"

                all_rows.append({
                    "media_type": m_type,
                    "genre": g_name,
                    "release_year": int(yr),
                    "title_count": count,
                    "mean_genre_score": m_score if count > 0 else np.nan,
                    "mean_raw_rating": m_raw if count > 0 else np.nan,
                    "yoy_change": yoy,
                    "comparison_status": status,
                })

                prev_count = count
                prev_score = m_score

    res_df = pd.DataFrame(all_rows)
    cols = [
        "media_type",
        "genre",
        "release_year",
        "title_count",
        "mean_genre_score",
        "mean_raw_rating",
        "yoy_change",
        "comparison_status",
    ]
    return res_df[cols]


def plot_genre_trend(
    trend_df: pd.DataFrame,
    media_type: str,
    genre: str,
) -> matplotlib.figure.Figure:
    """Generate clean, publication-ready Matplotlib trend figure for a genre.

    Plots mean genre-adjusted score with masked gaps where title_count < 5.
    Also plots diagnostic mean raw rating for comparison.
    Does NOT clamp Y-axis to 0-10.
    Returns the Figure object without calling plt.show() or Streamlit.
    """
    m_type = str(media_type).lower().strip()
    sub = trend_df[(trend_df["media_type"] == m_type) & (trend_df["genre"] == genre)].copy()
    sub = sub.sort_values("release_year")

    fig, ax = plt.subplots(figsize=(9, 5), dpi=120)

    # Figure dark background theme matching Curatr aesthetic
    bg_color = "#0e1117"
    panel_color = "#161b22"
    text_color = "#e6edf3"
    grid_color = "#30363d"
    accent_score = "#58a6ff"      # Curatr bright blue
    accent_raw = "#8b949e"        # Muted gray for raw rating
    warning_color = "#d29922"

    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(panel_color)

    if sub.empty:
        ax.text(
            0.5, 0.5,
            f"No data available for {m_type.upper()} genre '{genre}'",
            ha="center", va="center", color=text_color, fontsize=12
        )
        return fig

    years = sub["release_year"].values
    counts = sub["title_count"].values
    genre_scores = sub["mean_genre_score"].values
    raw_ratings = sub["mean_raw_rating"].values

    # Mask points where title_count < 5 (leaves gaps in line)
    masked_genre_scores = np.where(counts >= 5, genre_scores, np.nan)
    masked_raw_ratings = np.where(counts >= 5, raw_ratings, np.nan)

    # Plot lines
    ax.plot(
        years,
        masked_genre_scores,
        marker="o",
        markersize=6,
        linewidth=2.4,
        color=accent_score,
        label="Genre-Adjusted Score (S_genre)",
        zorder=4,
    )

    ax.plot(
        years,
        masked_raw_ratings,
        marker="s",
        markersize=4,
        linewidth=1.5,
        linestyle="--",
        color=accent_raw,
        label="Diagnostic Raw Rating (Mean)",
        zorder=3,
        alpha=0.85,
    )

    # Highlight points with annotations for count and value
    for y_val, s_val, c_val in zip(years, masked_genre_scores, counts):
        if not np.isnan(s_val):
            ax.annotate(
                f"{s_val:.2f}",
                xy=(y_val, s_val),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=accent_score,
                weight="bold",
            )

    # Highlight insufficient data years
    low_data_years = years[counts < 5]
    if len(low_data_years) > 0:
        for low_yr in low_data_years:
            ax.axvline(
                x=low_yr,
                color=warning_color,
                linestyle=":",
                alpha=0.4,
                zorder=2,
            )

    # Labels and titles
    type_display = "Movies" if m_type == "movie" else "TV Shows"
    ax.set_title(
        f"{type_display} · {genre} Quality Trend (2014–2023)",
        fontsize=14,
        fontweight="bold",
        color=text_color,
        pad=14,
    )

    x_label = "Release Year (2014–2023)"
    if m_type == "tv":
        x_label += " · TV series first-air year"
    ax.set_xlabel(x_label, fontsize=10, color="#8b949e", labelpad=8)
    ax.set_ylabel("Score / Rating (Points)", fontsize=10, color="#8b949e", labelpad=8)

    ax.set_xticks(REFERENCE_YEARS)
    ax.tick_params(colors="#8b949e", labelsize=9)
    ax.grid(True, linestyle="--", alpha=0.35, color=grid_color)

    # Spines styling
    for spine in ax.spines.values():
        spine.set_color(grid_color)

    # Caption explaining reference snapshot basis
    fig.text(
        0.5,
        0.01,
        "Release-year comparison using frozen 2014–2023 snapshot; points require ≥ 5 titles. Not longitudinal audience ratings.",
        ha="center",
        fontsize=7.5,
        color="#8b949e",
        style="italic",
    )

    ax.legend(
        loc="upper left",
        frameon=True,
        facecolor=panel_color,
        edgecolor=grid_color,
        fontsize=9,
        labelcolor=text_color,
    )

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    return fig


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate genre trends for Curatr.")
    parser.add_argument("--scored-csv", default="data/scored_titles.csv", help="Path to scored CSV")
    parser.add_argument("--output-csv", default="data/genre_year.csv", help="Path to output trends CSV")
    args = parser.parse_args()

    t0 = time.time()
    print(f"Loading scored titles from {args.scored_csv}...")
    df_scored = pd.read_csv(args.scored_csv)
    print(f"Loaded {len(df_scored):,} rows.")

    print("Building 10-year trends grid...")
    df_trends = build_trends(df_scored)

    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    df_trends.to_csv(args.output_csv, index=False, encoding="utf-8")
    elapsed = round(time.time() - t0, 2)

    groups_count = len(df_trends)
    print(f"Aggregated {groups_count} genre-year records in {elapsed}s and saved to {args.output_csv}.")
