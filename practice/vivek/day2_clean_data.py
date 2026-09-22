# PRACTICE — NOT REFERENCE DATA
# Day 2: Offline Data Cleaning and Clean Data Handoff Gate
# Goal: Normalize schemas, parse dates safely, filter, deduplicate, export.

import pandas as pd
import ast


# Safe genre parser: never uses eval()
def parse_genres_safely(raw_val):
    if not isinstance(raw_val, str) or not raw_val.strip():
        return ""
    try:
        parsed = ast.literal_eval(raw_val)
        if isinstance(parsed, list):
            names = [x["name"] if isinstance(x, dict) else str(x) for x in parsed]
            return "|".join(sorted(set(n.strip() for n in names if n and n.strip())))
    except (ValueError, SyntaxError):
        pass
    return ""


# Fictional raw data representing dirty source rows
raw_data = [
    {"id": 101, "title": "Inception", "release_date": "2010-07-16", "vote_average": 8.4, "vote_count": 35000, "genres": "[{'name': 'Action'}, {'name': 'Sci-Fi'}]", "original_language": "en"},
    {"id": 102, "title": "Interstellar", "release_date": "2014-11-07", "vote_average": 8.7, "vote_count": 34000, "genres": "[{'name': 'Adventure'}, {'name': 'Drama'}]", "original_language": "en"},
    {"id": 102, "title": "Interstellar Duplicate", "release_date": "2014-11-07", "vote_average": 8.7, "vote_count": 34000, "genres": "[{'name': 'Adventure'}]", "original_language": "en"},
    {"id": 103, "title": "Unreleased Film", "release_date": "invalid-date", "vote_average": 0.0, "vote_count": 0, "genres": "[]", "original_language": "en"},
]

df = pd.DataFrame(raw_data)
df["media_type"] = "movie"
df["tmdb_id"] = df["id"]

# Parse dates safely with errors='coerce'
df["release_year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year

# Track exclusions
exclusions = {"out_of_range_or_invalid_year": 0, "zero_votes": 0, "duplicates": 0}

# Filter 2014-2023 window
valid_year_mask = df["release_year"].between(2014, 2023)
exclusions["out_of_range_or_invalid_year"] = int((~valid_year_mask).sum())
df = df[valid_year_mask].copy()
df["release_year"] = df["release_year"].astype(int)

# Filter vote_count > 0
valid_votes_mask = df["vote_count"] > 0
exclusions["zero_votes"] = int((~valid_votes_mask).sum())
df = df[valid_votes_mask].copy()

# Deduplicate on composite key (media_type, tmdb_id)
dup_count = int(df.duplicated(subset=["media_type", "tmdb_id"]).sum())
exclusions["duplicates"] = dup_count
df = df.drop_duplicates(subset=["media_type", "tmdb_id"], keep="first").copy()

# Clean genres and ratings
df["genres"] = df["genres"].apply(parse_genres_safely)
df["rating"] = df["vote_average"].astype(float)

cols = ["media_type", "tmdb_id", "title", "release_year", "rating", "vote_count", "genres", "original_language"]
clean_df = df[cols]
print("Exclusions logged:", exclusions)
print(f"Clean titles produced: {len(clean_df)} rows")
print(clean_df.to_string(index=False))
