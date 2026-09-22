import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def build_trends(scored_df):
    """
    Aggregates scored titles into genre-year averages across 2014-2023.
    Ensures every observed (media_type, genre) has all 10 years represented.
    Computes YoY change and assigns comparison_status.
    """
    # 1. Explode genres
    exploded = scored_df.assign(
        genre=scored_df["genres"].str.split("|")
    ).explode("genre")

    # Clean genre strings and drop empties
    exploded["genre"] = exploded["genre"].str.strip()
    exploded = exploded[exploded["genre"] != ""]

    # 2. Aggregate counts and means
    grouped = (
        exploded.groupby(["media_type", "genre", "release_year"])
        .agg(
            title_count=("genre_score", "count"),
            mean_genre_score=("genre_score", "mean"),
            mean_raw_rating=("rating", "mean"),
        )
        .reset_index()
    )

    # 3. Build a complete 10-year calendar grid
    all_years = list(range(2014, 2024))
    observed_pairs = (
        exploded[["media_type", "genre"]].drop_duplicates().to_dict("records")
    )

    grid_rows = []
    for pair in observed_pairs:
        for year in all_years:
            grid_rows.append({
                "media_type": pair["media_type"],
                "genre": pair["genre"],
                "release_year": year,
            })
    grid_df = pd.DataFrame(grid_rows)

    # Merge aggregated data onto complete grid
    merged = pd.merge(
        grid_df,
        grouped,
        on=["media_type", "genre", "release_year"],
        how="left",
    )

    # Fill missing years: 0 titles, NaN scores
    merged["title_count"] = merged["title_count"].fillna(0).astype(int)
    merged["mean_genre_score"] = merged["mean_genre_score"].round(4)
    merged["mean_raw_rating"] = merged["mean_raw_rating"].round(4)

    # 4. Sort and calculate YoY change
    merged = merged.sort_values(
        by=["media_type", "genre", "release_year"]
    ).reset_index(drop=True)

    yoy_changes = []
    statuses = []

    # Process each media_type and genre sequence
    for (m_type, g_name), sub in merged.groupby(["media_type", "genre"]):
        sub_records = sub.to_dict("records")
        for i, row in enumerate(sub_records):
            count = row["title_count"]
            year = row["release_year"]
            score = row["mean_genre_score"]

            # Rule 1: Current year has < 5 titles
            if count < 5:
                statuses.append("insufficient_data")
                yoy_changes.append(np.nan)
                continue

            # Rule 2: 2014 has no previous reference year
            if year == 2014:
                statuses.append("no_previous_year")
                yoy_changes.append(np.nan)
                continue

            # Check previous calendar year
            prev_row = sub_records[i - 1]
            prev_count = prev_row["title_count"]
            prev_score = prev_row["mean_genre_score"]

            # Rule 3: Previous year had < 5 titles or missing score
            if prev_count < 5 or pd.isna(prev_score):
                statuses.append("insufficient_data")
                yoy_changes.append(np.nan)
            else:
                # Rule 4: Compute YoY diff
                diff = round(score - prev_score, 4)
                yoy_changes.append(diff)
                if diff > 0:
                    statuses.append("rise")
                elif diff < 0:
                    statuses.append("fall")
                else:
                    statuses.append("unchanged")

    merged["yoy_change"] = yoy_changes
    merged["comparison_status"] = statuses

    # Return with exact contract column ordering
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
    return merged[cols]

def plot_genre_trend(trend_df, media_type, genre):
    """
    Generates a Matplotlib Figure showing a genre's 10-year score trajectory.
    Years with insufficient data (< 5 titles) appear as clean gaps.
    """
    sub = trend_df[
        (trend_df["media_type"] == media_type) & (trend_df["genre"] == genre)
    ].sort_values("release_year")

    fig, ax = plt.subplots(figsize=(8, 4.5))

    years = sub["release_year"].values
    scores = sub["mean_genre_score"].copy()

    # Mask scores where title count < 5 with NaN so line breaks
    scores[sub["title_count"] < 5] = np.nan

    ax.plot(years, scores, marker="o", linewidth=2, color="#2b5c8f", label=f"{genre} Trend")

    ax.set_title(f"{genre} ({media_type.title()}) — 10-Year Trajectory (2014–2023)")
    ax.set_xlabel("Release / First-Air Year")
    ax.set_ylabel("Mean Genre-Adjusted Score")
    ax.set_xticks(years)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="best")
    fig.tight_layout()

    return fig

if __name__ == "__main__":
    scored_path = r"data\scored_titles.csv"
    if not os.path.exists(scored_path):
        raise FileNotFoundError(f"Missing {scored_path}. Run scoring.py first!")

    print("Loading scored_titles.csv...")
    scored_df = pd.read_csv(scored_path)

    print("Building genre-year trends...")
    trends_df = build_trends(scored_df)

    out_path = r"data\genre_year.csv"
    trends_df.to_csv(out_path, index=False)
    print(f"Saved trends to {out_path} ({len(trends_df)} rows)")

    print("\nComparison Status Breakdown:")
    print(trends_df["comparison_status"].value_counts())

    print("\nSample Action Movie Trends (2014-2023):")
    sample = trends_df[
        (trends_df["media_type"] == "movie") & (trends_df["genre"] == "Action")
    ]
    print(sample[["release_year", "title_count", "mean_genre_score", "yoy_change", "comparison_status"]])