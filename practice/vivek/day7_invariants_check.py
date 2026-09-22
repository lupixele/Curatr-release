# PRACTICE — NOT REFERENCE DATA
# Day 7: Invariants Verification, Test Suite, and Viva Voce Prep
# Goal: Run all Section 9 invariants on practice data and confirm they pass.

import pandas as pd

# Verification of Section 9 invariants on practice data
practice_records = [
    {"media_type": "movie", "tmdb_id": 1, "title": "Film A", "release_year": 2015, "rating": 7.5, "vote_count": 100, "genres": "Action|Drama", "original_language": "en"},
    {"media_type": "tv",    "tmdb_id": 1, "title": "Series A", "release_year": 2018, "rating": 8.0, "vote_count": 250, "genres": "Drama",        "original_language": "en"}
]
df = pd.DataFrame(practice_records)

# Check 1: Composite key uniqueness
dup_count = df.duplicated(subset=["media_type", "tmdb_id"]).sum()
assert dup_count == 0, "Duplicate composite keys found!"
print("Check 1 passed: Composite key (media_type, tmdb_id) is unique.")

# Check 2: Bounds
assert df["release_year"].between(2014, 2023).all(), "Year outside reference window!"
assert df["rating"].between(0.0, 10.0).all(), "Rating out of bounds!"
assert (df["vote_count"] > 0).all(), "Zero vote count in reference data!"
print("Check 2 passed: release_year, rating, and vote_count all within bounds.")

# Check 3: Genre formatting (no spaces around delimiter)
assert all(" " not in g for g in df["genres"] if "|" in g), "Improper genre formatting!"
print("Check 3 passed: Genre formatting is correct (pipe-delimited, no spaces).")

# Check 4: media_type values
assert set(df["media_type"].unique()).issubset({"movie", "tv"}), "Invalid media_type!"
print("Check 4 passed: media_type values are valid ('movie' or 'tv').")

# Check 5: No missing titles
assert df["title"].notna().all() and (df["title"].str.strip() != "").all(), "Missing title!"
print("Check 5 passed: All titles are non-empty strings.")

print("\nAll Section 9 offline data invariants verified successfully.")
print("\n--- Viva Voce Quick Reference ---")
print("Q1: Why pd.to_datetime errors='coerce'?")
print("    -> Safely handles corrupt dates as NaT; string slicing crashes on nulls.")
print("Q2: Why not eval() for genre parsing?")
print("    -> eval() runs arbitrary code; ast.literal_eval() only parses literals.")
print("Q3: Why composite key (media_type, tmdb_id)?")
print("    -> TMDb reuses integer IDs across movies and TV independently.")
print("Q4: Why env variables for tokens?")
print("    -> Hardcoded tokens can be scraped from code/Git; URL params leak in logs.")
print("Q5: Can we compare ratings across years from this dataset?")
print("    -> No: survivorship bias and snapshot timing (2026) affect historical data.")
