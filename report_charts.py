"""Optional report charts from the existing 2014–2023 data snapshot."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CHART_NAMES = (
    "Genre counts", "Movies and TV", "Raw ratings and global scores",
    "Ratings by genre", "Votes and ratings", "Genre-year heatmap",
)


def genre_memberships(titles):
    """Count exact genre memberships, once per title and genre."""
    genres = titles["genres"].fillna("").map(
        lambda value: sorted({g.strip() for g in value.split("|") if g.strip()})
    )
    result = titles.assign(genre=genres).explode("genre")
    return result[result["genre"].notna() & result["genre"].ne("")]


def heatmap_values(trends, media_type):
    """Leave missing or low-count release-year cohorts blank."""
    selected = trends[
        trends["media_type"].eq(media_type)
        & trends["release_year"].between(2014, 2023)
    ].copy()
    if selected.empty:
        return pd.DataFrame()
    selected.loc[selected["title_count"] < 5, "mean_genre_score"] = np.nan
    top = selected.groupby("genre")["title_count"].sum().nlargest(12).index
    return selected.pivot(
        index="genre", columns="release_year", values="mean_genre_score"
    ).reindex(index=top, columns=range(2014, 2024))


def build_report_chart(name, titles, trends, baselines, media_type="movie"):
    """Return a Figure, or None when there are no eligible values to plot."""
    if name not in CHART_NAMES:
        raise ValueError(f"Unknown chart: {name}")
    titles = titles[titles["release_year"].between(2014, 2023)]
    if name == "Genre-year heatmap":
        values = heatmap_values(trends, media_type)
        if values.empty or not values.notna().any().any():
            return None
        fig, ax = plt.subplots(figsize=(8, 5))
        image = ax.imshow(np.ma.masked_invalid(values.to_numpy()),
                          aspect="auto", cmap="Blues")
        ax.set_xticks(range(len(values.columns)), values.columns)
        ax.set_yticks(range(len(values.index)), values.index)
        ax.set_xlabel("Release / first-air year")
        ax.set_title(f"Mean genre-adjusted score · {media_type}")
        fig.colorbar(image, ax=ax, label="Mean genre-adjusted score")
    elif titles.empty:
        return None
    elif name == "Genre counts":
        counts = genre_memberships(titles)["genre"].value_counts().head(12)
        if counts.empty:
            return None
        fig, ax = plt.subplots(figsize=(8, 4.5))
        counts.sort_values().plot.barh(ax=ax, color="#2b5c8f")
        ax.set_xlabel("Titles (genre memberships overlap)")
        ax.set_ylabel("")
    elif name == "Movies and TV":
        counts = titles["media_type"].value_counts().reindex(["movie", "tv"]).fillna(0)
        counts = counts[counts > 0]
        if counts.empty:
            return None
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.pie(counts, labels=["Movies" if m == "movie" else "TV" for m in counts.index],
               autopct="%1.1f%%", colors=["#2b5c8f", "#39958d"], startangle=90)
        ax.axis("equal")
    elif name == "Raw ratings and global scores":
        values = titles[["rating", "global_score"]].dropna()
        if values.empty:
            return None
        fig, ax = plt.subplots(figsize=(8, 4))
        bins = np.linspace(0, 10, 31)
        ax.hist(values["rating"], bins=bins, alpha=.5, label="Raw rating", color="#d79843")
        ax.hist(values["global_score"], bins=bins, alpha=.5, label="Global score", color="#2b5c8f")
        for medium, style in [("movie", "--"), ("tv", ":")]:
            if medium in baselines:
                ax.axvline(baselines[medium]["C"], linestyle=style, color="#39434d",
                           label=f"{medium.title()} prior C = {baselines[medium]['C']:.2f}")
        ax.set_xlabel("Rating / global score")
        ax.set_ylabel("Titles")
        ax.legend(fontsize=8)
    elif name == "Ratings by genre":
        members = genre_memberships(titles).dropna(subset=["rating"])
        top = members["genre"].value_counts().head(8).index
        if top.empty:
            return None
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.boxplot([members.loc[members["genre"].eq(g), "rating"] for g in top],
                   showfliers=False)
        ax.set_xticks(range(1, len(top) + 1), top, rotation=25, ha="right")
        ax.set_ylabel("Raw rating")
    elif name == "Votes and ratings":
        sample = titles.dropna(subset=["vote_count", "rating", "global_score"])
        sample = sample[sample["vote_count"] > 0]
        if sample.empty:
            return None
        sample = sample.sample(n=min(len(sample), 3000), random_state=42)
        fig, ax = plt.subplots(figsize=(8, 4))
        dots = ax.scatter(sample["vote_count"], sample["rating"],
                          c=sample["global_score"], cmap="viridis", s=10, alpha=.6)
        ax.set_xscale("log")
        ax.set_xlabel("Votes (log scale)")
        ax.set_ylabel("Raw rating")
        fig.colorbar(dots, ax=ax, label="Global score")
    fig.tight_layout()
    return fig
