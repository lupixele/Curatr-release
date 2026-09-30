import pandas as pd

# 1. Load the original raw files
mv_df = pd.read_csv(r"data\raw\TMDB_MV.csv")
tv_df = pd.read_csv(r"data\raw\TMDB_TV.csv")


def clean_genres(text):
    if not isinstance(text, str) or not text.strip():
        return ""

    # Split by comma, trim whitespace off each genre
    parts = [g.strip() for g in text.split(",") if g.strip()]

    # Deduplicate, sort alphabetically, and join with |
    return "|".join(sorted(set(parts)))


# Genre cleaning
mv_df["genres"] = mv_df["genres"].apply(clean_genres)
tv_df["genres"] = tv_df["genres"].apply(clean_genres)


# Create new column media_type
mv_df["media_type"] = "movie"
tv_df["media_type"] = "tv"


# Rename to make consistent
tv_df = tv_df.rename(columns={
    "id": "tmdb_id",
    "name": "title",
    "first_air_date": "release_year",
    "vote_average": "rating"
})

tv_df["release_year"] = pd.to_datetime(
    tv_df["release_year"],
    errors="coerce"
).dt.year


mv_df = mv_df.rename(columns={
    "id": "tmdb_id",
    "vote_average": "rating"
})

mv_df["release_year"] = pd.to_datetime(
    mv_df["release_date"],
    errors="coerce"
).dt.year


# Filtering adult content and vote_count > 0
mv_df = mv_df[
    (mv_df["adult"] == False) &
    (mv_df["vote_count"] > 0)
]

tv_df = tv_df[
    (tv_df["adult"] == False) &
    (tv_df["vote_count"] > 0)
]


# Remove missing IDs and titles
mv_df = mv_df.dropna(subset=["tmdb_id", "title"])
tv_df = tv_df.dropna(subset=["tmdb_id", "title"])

# Remove empty/space-only titles
mv_df = mv_df[mv_df["title"].str.strip() != ""]
tv_df = tv_df[tv_df["title"].str.strip() != ""]


# Make sure IDs are valid positive integers
mv_df["tmdb_id"] = mv_df["tmdb_id"].astype(int)
mv_df = mv_df[mv_df["tmdb_id"] > 0]

tv_df["tmdb_id"] = tv_df["tmdb_id"].astype(int)
tv_df = tv_df[tv_df["tmdb_id"] > 0]


# Deduplicate IDs, keep first
mv_df = mv_df.drop_duplicates(subset=["tmdb_id"], keep="first")
tv_df = tv_df.drop_duplicates(subset=["tmdb_id"], keep="first")


# Keep only required columns
columns = [
    "media_type",
    "tmdb_id",
    "title",
    "release_year",
    "rating",
    "vote_count",
    "genres",
    "original_language"
]

mv_df = mv_df[columns]
tv_df = tv_df[columns]


# Combine movie + TV
clean_df = pd.concat(
    [mv_df, tv_df],
    ignore_index=True
)


# Drop unparseable/missing dates
clean_df = clean_df.dropna(subset=["release_year"])


# Keep only 2014-2023
clean_df = clean_df[
    clean_df["release_year"].between(2014, 2023)
]

# Convert year to integer
clean_df["release_year"] = clean_df["release_year"].astype(int)


# Keep ratings between 0 and 10
clean_df = clean_df[
    clean_df["rating"].between(0, 10)
]


# Drop empty genres
clean_df = clean_df[
    clean_df["genres"].str.strip() != ""
]


# Save
clean_df.to_csv(
    r"data\raw\clean_titles.csv",
    index=False
)