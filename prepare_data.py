"""
prepare_data.py — Offline data cleaning pipeline for Curatr.
Owner: Vivek
Consumer: Lochan (scoring.py)

Reads raw movie and TV CSV files from data/raw/, applies schema normalization,
date filtering, deduplication, and exclusion tracking, then exports the clean
reference table to data/clean_titles.csv.

Usage:
    python prepare_data.py

Output:
    data/clean_titles.csv
"""

import ast
import os
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Column definitions
# ---------------------------------------------------------------------------

MOVIE_COLS = [
    "id", "title", "release_date",
    "vote_average", "vote_count", "genres",
    "original_language", "adult",
]

TV_COLS = [
    "id", "name", "first_air_date",
    "vote_average", "vote_count", "genres",
    "original_language", "adult",
]

OUTPUT_COLS = [
    "media_type", "tmdb_id", "title",
    "release_year", "rating", "vote_count",
    "genres", "original_language",
]

YEAR_MIN = 2014
YEAR_MAX = 2023

RAW_DIR = os.path.join("data", "raw")
OUTPUT_PATH = os.path.join("data", "clean_titles.csv")


# ---------------------------------------------------------------------------
# 2. Safe genre parser (never uses eval())
# ---------------------------------------------------------------------------

def parse_genres_safely(raw_val) -> str:
    """
    Safely extract genre names from a serialized list string.
    Handles both JSON-style double-quoted and Python-literal single-quoted
    representations, as well as plain comma-separated genre strings.
    Never calls eval().
    """
    if not isinstance(raw_val, str) or not raw_val.strip():
        return ""

    # Try ast.literal_eval for Python-literal list format e.g. "[{'name': 'Action'}]"
    try:
        parsed = ast.literal_eval(raw_val)
        if isinstance(parsed, list):
            names = [
                item["name"].strip() if isinstance(item, dict) and "name" in item
                else str(item).strip()
                for item in parsed
            ]
            clean = sorted(set(n for n in names if n))
            return "|".join(clean)
    except (ValueError, SyntaxError):
        pass

    # Fallback: plain comma-separated string (e.g. "Action, Drama")
    parts = [g.strip() for g in raw_val.split(",") if g.strip()]
    if parts:
        return "|".join(sorted(set(parts)))

    return ""


# ---------------------------------------------------------------------------
# 3. Load raw files
# ---------------------------------------------------------------------------

def load_raw(filename: str, usecols: list, media_type: str) -> pd.DataFrame:
    """Load a raw CSV, only reading the columns we need."""
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        print(f"  [WARN] Raw file not found: {path}  — skipping.")
        return pd.DataFrame(columns=usecols)

    # Only read columns that actually exist in the file
    available = pd.read_csv(path, nrows=0).columns.tolist()
    cols_to_load = [c for c in usecols if c in available]
    df = pd.read_csv(path, usecols=cols_to_load)
    df["_source_media_type"] = media_type
    return df


# Candidate filenames — update to confirmed names after audit decision
MOVIE_FILE = "candidate_movies_raw.csv"   # placeholder filename — pending audit decision
TV_FILE    = "candidate_tv_raw.csv"       # placeholder filename — pending audit decision

print("=" * 60)
print("Curatr — prepare_data.py")
print("=" * 60)

df_movies_raw = load_raw(MOVIE_FILE, MOVIE_COLS, "movie")
df_tv_raw     = load_raw(TV_FILE,    TV_COLS,    "tv")


# ---------------------------------------------------------------------------
# 4. Schema normalization: unify column names
# ---------------------------------------------------------------------------

def normalize_movies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={"id": "tmdb_id", "vote_average": "rating"})
    df["media_type"]   = "movie"
    df["release_year"] = pd.to_datetime(df.get("release_date", pd.Series(dtype=str)), errors="coerce").dt.year
    return df


def normalize_tv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={
        "id":            "tmdb_id",
        "name":          "title",
        "first_air_date": "release_year_raw",
        "vote_average":  "rating",
    })
    df["media_type"]   = "tv"
    df["release_year"] = pd.to_datetime(df.get("release_year_raw", pd.Series(dtype=str)), errors="coerce").dt.year
    return df


df_movies = normalize_movies(df_movies_raw) if not df_movies_raw.empty else pd.DataFrame()
df_tv     = normalize_tv(df_tv_raw)         if not df_tv_raw.empty     else pd.DataFrame()

# Combine
df = pd.concat([df_movies, df_tv], ignore_index=True)

if df.empty:
    print("\n[ERROR] No raw data loaded. Place raw CSV files in data/raw/ and rerun.")
    raise SystemExit(1)

total_raw = len(df)
print(f"\nRaw records loaded: {total_raw:,}")


# ---------------------------------------------------------------------------
# 5. Exclusion tracking
# ---------------------------------------------------------------------------

exclusions = {
    "missing_title":                    0,
    "unparseable_or_out_of_range_year": 0,
    "unrated_or_zero_votes":            0,
    "adult_content":                    0,
    "missing_genres":                   0,
    "duplicate_records":                0,
}


# 5a. Missing or blank title
missing_title_mask = df["title"].isna() | (df["title"].astype(str).str.strip() == "")
exclusions["missing_title"] = int(missing_title_mask.sum())
df = df[~missing_title_mask].copy()

# 5b. Adult content
if "adult" in df.columns:
    adult_mask = df["adult"].astype(str).str.lower().isin(["true", "1"])
    exclusions["adult_content"] = int(adult_mask.sum())
    df = df[~adult_mask].copy()

# 5c. Unparseable or out-of-range release year
year_mask = df["release_year"].between(YEAR_MIN, YEAR_MAX)
exclusions["unparseable_or_out_of_range_year"] = int((~year_mask).sum())
df = df[year_mask].copy()
df["release_year"] = df["release_year"].astype(int)

# 5d. Zero vote count or unrated (vote_count == 0)
zero_votes_mask = df["vote_count"] <= 0
exclusions["unrated_or_zero_votes"] = int(zero_votes_mask.sum())
df = df[~zero_votes_mask].copy()

# 5e. Ensure tmdb_id is positive integer
df["tmdb_id"] = pd.to_numeric(df["tmdb_id"], errors="coerce")
df = df[df["tmdb_id"].notna() & (df["tmdb_id"] > 0)].copy()
df["tmdb_id"] = df["tmdb_id"].astype(int)

# 5f. Safe genre parsing
df["genres"] = df["genres"].apply(parse_genres_safely)
missing_genres_mask = df["genres"].str.strip() == ""
exclusions["missing_genres"] = int(missing_genres_mask.sum())
df = df[~missing_genres_mask].copy()

# 5g. Rating bounds (0.0–10.0)
df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0.0).clip(0.0, 10.0)

# 5h. Deduplicate on composite key (media_type, tmdb_id)
#     NOTE: Never deduplicate on tmdb_id alone — movies and TV share integer IDs in TMDb.
dup_mask = df.duplicated(subset=["media_type", "tmdb_id"], keep="first")
exclusions["duplicate_records"] = int(dup_mask.sum())
df = df[~dup_mask].copy()

# Fill missing original_language with empty string (informational — never filter out)
df["original_language"] = df.get("original_language", pd.Series(dtype=str)).fillna("").astype(str)


# ---------------------------------------------------------------------------
# 6. Select and export output columns
# ---------------------------------------------------------------------------

clean_df = df[OUTPUT_COLS].reset_index(drop=True)

os.makedirs("data", exist_ok=True)
clean_df.to_csv(OUTPUT_PATH, index=False)


# ---------------------------------------------------------------------------
# 7. Summary report
# ---------------------------------------------------------------------------

movie_count = int((clean_df["media_type"] == "movie").sum())
tv_count    = int((clean_df["media_type"] == "tv").sum())

print("\n--- Exclusion Log ---")
for reason, count in exclusions.items():
    print(f"  {reason}: {count:,}")

print(f"\n--- Output Summary ---")
print(f"  Total input records : {total_raw:,}")
print(f"  Total excluded      : {sum(exclusions.values()):,}")
print(f"  Clean movies        : {movie_count:,}")
print(f"  Clean TV titles     : {tv_count:,}")
print(f"  Total clean rows    : {len(clean_df):,}")
print(f"\nOutput written to: {OUTPUT_PATH}")
print("=" * 60)
print("Clean Data Handoff Gate — ready for Lochan (scoring.py)")
print("=" * 60)